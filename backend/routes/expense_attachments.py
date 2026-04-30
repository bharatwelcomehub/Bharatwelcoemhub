# =======================================
# Expense Attachments & Invoice Grouping Routes
# Bill/Invoice Management for CA/Auditor
# =======================================

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Header
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging
import uuid
import requests
import io
import zipfile
import csv

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/expense-attachments", tags=["Expense Attachments"])

# Database and auth references
db = None
verify_token = None

# Object Storage Configuration
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "purnabramha-intrapb"
storage_key = None

# File size limits
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB for images
MAX_PDF_SIZE = 10 * 1024 * 1024   # 10 MB for PDFs
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'webp'}
ALLOWED_MIME_TYPES = {
    'application/pdf': 'pdf',
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp'
}

# Data retention period
RETENTION_YEARS = 7

def set_db(database):
    global db
    db = database

def set_verify_token(func):
    global verify_token
    verify_token = func

# =======================================
# OBJECT STORAGE FUNCTIONS
# =======================================

def init_storage():
    """Initialize storage and get reusable storage key"""
    global storage_key
    if storage_key:
        return storage_key
    
    if not EMERGENT_KEY:
        logger.error("EMERGENT_LLM_KEY not set for object storage")
        raise HTTPException(500, "Storage not configured")
    
    try:
        resp = requests.post(
            f"{STORAGE_URL}/init",
            json={"emergent_key": EMERGENT_KEY},
            timeout=30
        )
        resp.raise_for_status()
        storage_key = resp.json()["storage_key"]
        logger.info("Object storage initialized successfully")
        return storage_key
    except Exception as e:
        logger.error(f"Failed to initialize storage: {e}")
        raise HTTPException(500, f"Storage initialization failed: {str(e)}")

def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Upload file to object storage"""
    key = init_storage()
    try:
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data,
            timeout=120
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(500, f"File upload failed: {str(e)}")

def get_object(path: str) -> tuple:
    """Download file from object storage"""
    key = init_storage()
    try:
        resp = requests.get(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key},
            timeout=60
        )
        resp.raise_for_status()
        return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        raise HTTPException(500, f"File download failed: {str(e)}")

# =======================================
# PYDANTIC MODELS
# =======================================

class InvoiceGroupCreate(BaseModel):
    vendor_name: str
    invoice_number: str
    bill_date: str  # YYYY-MM-DD
    total_bill_amount: float
    notes: Optional[str] = ""
    expense_ids: Optional[List[str]] = []  # Expense IDs to link

class InvoiceGroupUpdate(BaseModel):
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    bill_date: Optional[str] = None
    total_bill_amount: Optional[float] = None
    notes: Optional[str] = None

class LinkExpensesRequest(BaseModel):
    token: str
    invoice_group_id: str
    expense_ids: List[str]

class UnlinkExpenseRequest(BaseModel):
    token: str
    expense_id: str

class ExportRequest(BaseModel):
    token: str
    center: str
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    category: Optional[str] = None
    vendor: Optional[str] = None
    attachment_status: Optional[str] = None  # "attached", "missing", "all"
    grouped_status: Optional[str] = None     # "grouped", "ungrouped", "all"
    payment_mode: Optional[str] = None

# =======================================
# INVOICE GROUP ENDPOINTS
# =======================================

@router.post("/invoice-groups")
async def create_invoice_group(
    token: str = Form(...),
    vendor_name: str = Form(...),
    invoice_number: str = Form(...),
    bill_date: str = Form(...),
    total_bill_amount: float = Form(...),
    notes: str = Form(""),
    expense_ids: str = Form(""),  # Comma-separated expense IDs
    center: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    """Create a new invoice group with optional attachment"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Verify center access
    user_center = session.get("center", "")
    if not (session.get("is_super_admin") or session.get("is_admin")) and user_center != center:
        raise HTTPException(403, "Cannot create invoice group for another center")
    
    # Check for duplicate invoice number from same vendor
    existing = await db.invoice_groups.find_one({
        "center": center,
        "vendor_name": vendor_name,
        "invoice_number": invoice_number,
        "is_deleted": {"$ne": True}
    })
    
    duplicate_warning = None
    if existing:
        duplicate_warning = f"Warning: Invoice #{invoice_number} from {vendor_name} already exists"
    
    # Create invoice group
    group_id = f"INV-{center}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8]}"
    
    group_doc = {
        "group_id": group_id,
        "center": center,
        "vendor_name": vendor_name,
        "invoice_number": invoice_number,
        "bill_date": bill_date,
        "total_bill_amount": total_bill_amount,
        "notes": notes,
        "created_by": session.get("managerName", "Unknown"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "is_deleted": False,
        "attachments": [],
        "linked_expense_count": 0,
        "linked_expense_total": 0
    }
    
    # Handle file upload if provided
    if file:
        file_result = await _upload_attachment_file(file, center, session, group_id=group_id)
        group_doc["attachments"].append(file_result["attachment_id"])
    
    await db.invoice_groups.insert_one(group_doc)
    
    # Link expenses if provided
    expense_id_list = [e.strip() for e in expense_ids.split(",") if e.strip()]
    if expense_id_list:
        await _link_expenses_to_group(group_id, expense_id_list, center)
        # Update linked counts
        await _update_group_totals(group_id)
    
    response = {
        "success": True,
        "group_id": group_id,
        "message": "Invoice group created successfully"
    }
    if duplicate_warning:
        response["warning"] = duplicate_warning
    
    return response

@router.get("/invoice-groups")
async def list_invoice_groups(
    token: str,
    center: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    vendor: Optional[str] = None
):
    """List invoice groups for a center"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    query = {"center": center, "is_deleted": {"$ne": True}}
    
    if start_date and end_date:
        query["bill_date"] = {"$gte": start_date, "$lte": end_date}
    
    if vendor:
        query["vendor_name"] = {"$regex": vendor, "$options": "i"}
    
    groups = await db.invoice_groups.find(query, {"_id": 0}).sort("bill_date", -1).to_list(500)
    
    # Enrich with linked expense details
    for group in groups:
        # Get linked expenses
        linked = await db.expenses.find(
            {"invoice_group_id": group["group_id"], "is_deleted": {"$ne": True}},
            {"_id": 0, "expense_id": 1, "description": 1, "expense_type": 1, "amount": 1, "date": 1}
        ).to_list(100)
        group["linked_expenses"] = linked
        group["linked_expense_count"] = len(linked)
        group["linked_expense_total"] = sum(e.get("amount", 0) for e in linked)
        
        # Check amount match
        if group["linked_expense_total"] > 0:
            diff = abs(group["total_bill_amount"] - group["linked_expense_total"])
            group["amount_match"] = "exact" if diff < 0.01 else "mismatch"
            group["amount_difference"] = round(diff, 2)
        else:
            group["amount_match"] = "no_expenses"
            group["amount_difference"] = 0
    
    return {"success": True, "groups": groups, "count": len(groups)}

@router.get("/invoice-groups/{group_id}")
async def get_invoice_group(group_id: str, token: str):
    """Get detailed invoice group information"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    group = await db.invoice_groups.find_one(
        {"group_id": group_id, "is_deleted": {"$ne": True}},
        {"_id": 0}
    )
    
    if not group:
        raise HTTPException(404, "Invoice group not found")
    
    # Get linked expenses with full details
    linked = await db.expenses.find(
        {"invoice_group_id": group_id, "is_deleted": {"$ne": True}},
        {"_id": 0}
    ).to_list(100)
    
    # Get attachments
    attachments = await db.expense_attachments.find(
        {"invoice_group_id": group_id, "is_deleted": {"$ne": True}},
        {"_id": 0}
    ).to_list(50)
    
    # Calculate totals by category
    category_totals = {}
    for exp in linked:
        cat = exp.get("expense_type", "OTHER")
        category_totals[cat] = category_totals.get(cat, 0) + exp.get("amount", 0)
    
    group["linked_expenses"] = linked
    group["linked_expense_count"] = len(linked)
    group["linked_expense_total"] = sum(e.get("amount", 0) for e in linked)
    group["category_breakdown"] = category_totals
    group["attachment_details"] = attachments
    
    # Amount match check
    diff = abs(group["total_bill_amount"] - group["linked_expense_total"])
    group["amount_match"] = "exact" if diff < 0.01 else "mismatch"
    group["amount_difference"] = round(diff, 2)
    
    return {"success": True, "group": group}

@router.put("/invoice-groups/{group_id}")
async def update_invoice_group(group_id: str, req: InvoiceGroupUpdate, token: str):
    """Update invoice group details"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    group = await db.invoice_groups.find_one({"group_id": group_id, "is_deleted": {"$ne": True}})
    if not group:
        raise HTTPException(404, "Invoice group not found")
    
    # Check permission
    user_center = session.get("center", "")
    if not (session.get("is_super_admin") or session.get("is_admin")) and user_center != group.get("center"):
        raise HTTPException(403, "Cannot update invoice group for another center")
    
    update_data = {k: v for k, v in req.dict().items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        update_data["updated_by"] = session.get("managerName", "Unknown")
        await db.invoice_groups.update_one({"group_id": group_id}, {"$set": update_data})
    
    return {"success": True, "message": "Invoice group updated"}

@router.delete("/invoice-groups/{group_id}")
async def delete_invoice_group(group_id: str, token: str):
    """Delete invoice group (unlinks expenses, doesn't delete them)"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    group = await db.invoice_groups.find_one({"group_id": group_id, "is_deleted": {"$ne": True}})
    if not group:
        raise HTTPException(404, "Invoice group not found")
    
    # Unlink all expenses
    await db.expenses.update_many(
        {"invoice_group_id": group_id},
        {"$unset": {"invoice_group_id": ""}}
    )
    
    # Soft delete group
    await db.invoice_groups.update_one(
        {"group_id": group_id},
        {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Soft delete group attachments
    await db.expense_attachments.update_many(
        {"invoice_group_id": group_id},
        {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"success": True, "message": "Invoice group deleted. Linked expenses have been unlinked."}

# =======================================
# LINK/UNLINK EXPENSES
# =======================================

@router.post("/link-expenses")
async def link_expenses_to_group(req: LinkExpensesRequest):
    """Link multiple expenses to an invoice group"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    group = await db.invoice_groups.find_one(
        {"group_id": req.invoice_group_id, "is_deleted": {"$ne": True}}
    )
    if not group:
        raise HTTPException(404, "Invoice group not found")
    
    center = group.get("center")
    linked_count = await _link_expenses_to_group(req.invoice_group_id, req.expense_ids, center)
    await _update_group_totals(req.invoice_group_id)
    
    return {"success": True, "linked_count": linked_count, "message": f"{linked_count} expenses linked to invoice group"}

@router.post("/unlink-expense")
async def unlink_expense_from_group(req: UnlinkExpenseRequest):
    """Unlink a single expense from its invoice group"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    try:
        expense = await db.expenses.find_one({"expense_id": req.expense_id})
        if not expense:
            # Try with ObjectId
            expense = await db.expenses.find_one({"_id": ObjectId(req.expense_id)})
    except Exception:
        raise HTTPException(404, "Expense not found")
    
    if not expense:
        raise HTTPException(404, "Expense not found")
    
    old_group_id = expense.get("invoice_group_id")
    
    await db.expenses.update_one(
        {"expense_id": req.expense_id} if expense.get("expense_id") else {"_id": expense["_id"]},
        {"$unset": {"invoice_group_id": ""}}
    )
    
    # Update old group totals if it existed
    if old_group_id:
        await _update_group_totals(old_group_id)
    
    return {"success": True, "message": "Expense unlinked from invoice group"}

# =======================================
# ATTACHMENT ENDPOINTS
# =======================================

@router.post("/upload")
async def upload_attachment(
    token: str = Form(...),
    expense_id: Optional[str] = Form(None),
    invoice_group_id: Optional[str] = Form(None),
    center: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload an attachment for an expense or invoice group"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if not expense_id and not invoice_group_id:
        raise HTTPException(400, "Either expense_id or invoice_group_id is required")
    
    result = await _upload_attachment_file(file, center, session, expense_id, invoice_group_id)
    
    # Update expense or group with attachment reference
    if expense_id:
        # Try matching by expense_id field first; fall back to _id ObjectId for legacy records
        update_payload = {
            "$push": {"attachments": result["attachment_id"]},
            "$set": {"has_attachment": True, "expense_id": expense_id, "updated_at": datetime.now(timezone.utc).isoformat()}
        }
        upd = await db.expenses.update_one({"expense_id": expense_id}, update_payload)
        if upd.matched_count == 0:
            try:
                from bson import ObjectId
                await db.expenses.update_one({"_id": ObjectId(expense_id)}, update_payload)
            except Exception:
                logger.warning(f"Could not link attachment {result['attachment_id']} to expense {expense_id} (no match by expense_id or _id)")
    
    if invoice_group_id:
        await db.invoice_groups.update_one(
            {"group_id": invoice_group_id},
            {
                "$push": {"attachments": result["attachment_id"]},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
    
    return result

async def _upload_attachment_file(
    file: UploadFile,
    center: str,
    session: dict,
    expense_id: Optional[str] = None,
    invoice_group_id: Optional[str] = None
) -> dict:
    """Internal function to upload attachment file"""
    # Validate file type
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
    
    content_type = file.content_type or "application/octet-stream"
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Validate file size
    is_pdf = ext == 'pdf' or content_type == 'application/pdf'
    max_size = MAX_PDF_SIZE if is_pdf else MAX_IMAGE_SIZE
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(400, f"File too large. Maximum size: {max_mb} MB")
    
    # Generate storage path
    date_prefix = datetime.now().strftime("%Y/%m")
    file_uuid = str(uuid.uuid4())
    storage_path = f"{APP_NAME}/attachments/{center}/{date_prefix}/{file_uuid}.{ext}"
    
    # Upload to storage
    result = put_object(storage_path, content, content_type)
    
    # Create attachment record
    attachment_id = f"ATT-{str(uuid.uuid4())[:12]}"
    attachment_doc = {
        "attachment_id": attachment_id,
        "expense_id": expense_id,
        "invoice_group_id": invoice_group_id,
        "center": center,
        "storage_path": result["path"],
        "original_filename": file.filename,
        "file_type": ext,
        "mime_type": content_type,
        "file_size": file_size,
        "uploaded_by": session.get("managerName", "Unknown"),
        "uploaded_by_center": session.get("center", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_deleted": False,
        "retention_until": (datetime.now(timezone.utc) + timedelta(days=RETENTION_YEARS * 365)).isoformat()
    }
    
    await db.expense_attachments.insert_one(attachment_doc)
    
    logger.info(f"Attachment uploaded: {attachment_id} by {session.get('managerName')}")
    
    return {
        "success": True,
        "attachment_id": attachment_id,
        "filename": file.filename,
        "file_size": file_size,
        "message": "File uploaded successfully"
    }

@router.get("/download/{attachment_id}")
async def download_attachment(
    attachment_id: str,
    token: Optional[str] = None,
    auth: Optional[str] = Query(None)
):
    """Download an attachment file"""
    # Support both header and query param auth
    auth_token = token or auth
    if not auth_token:
        raise HTTPException(401, "Authentication required")
    
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(auth_token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    attachment = await db.expense_attachments.find_one(
        {"attachment_id": attachment_id, "is_deleted": {"$ne": True}}
    )
    
    if not attachment:
        raise HTTPException(404, "Attachment not found")
    
    # Download from storage
    content, content_type = get_object(attachment["storage_path"])
    
    return Response(
        content=content,
        media_type=attachment.get("mime_type", content_type),
        headers={
            "Content-Disposition": f'attachment; filename="{attachment.get("original_filename", "file")}"'
        }
    )

@router.get("/view/{attachment_id}")
async def view_attachment(
    attachment_id: str,
    token: Optional[str] = None,
    auth: Optional[str] = Query(None)
):
    """View attachment inline (for preview)"""
    auth_token = token or auth
    if not auth_token:
        raise HTTPException(401, "Authentication required")
    
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(auth_token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    attachment = await db.expense_attachments.find_one(
        {"attachment_id": attachment_id, "is_deleted": {"$ne": True}}
    )
    
    if not attachment:
        raise HTTPException(404, "Attachment not found")
    
    content, content_type = get_object(attachment["storage_path"])
    
    return Response(
        content=content,
        media_type=attachment.get("mime_type", content_type),
        headers={
            "Content-Disposition": f'inline; filename="{attachment.get("original_filename", "file")}"'
        }
    )

@router.delete("/attachment/{attachment_id}")
async def delete_attachment(attachment_id: str, token: str):
    """Soft delete an attachment"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    attachment = await db.expense_attachments.find_one(
        {"attachment_id": attachment_id, "is_deleted": {"$ne": True}}
    )
    
    if not attachment:
        raise HTTPException(404, "Attachment not found")
    
    # Soft delete
    await db.expense_attachments.update_one(
        {"attachment_id": attachment_id},
        {
            "$set": {
                "is_deleted": True,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
                "deleted_by": session.get("managerName", "Unknown")
            }
        }
    )
    
    # Remove from expense attachments array
    if attachment.get("expense_id"):
        exp_id = attachment["expense_id"]
        upd = await db.expenses.update_one(
            {"expense_id": exp_id},
            {"$pull": {"attachments": attachment_id}}
        )
        if upd.matched_count == 0:
            try:
                from bson import ObjectId
                await db.expenses.update_one(
                    {"_id": ObjectId(exp_id)},
                    {"$pull": {"attachments": attachment_id}}
                )
            except Exception:
                pass
        # Check if any attachments left (in expense_attachments collection)
        remaining = await db.expense_attachments.count_documents(
            {"expense_id": exp_id, "is_deleted": {"$ne": True}}
        )
        if remaining == 0:
            await db.expenses.update_one(
                {"expense_id": exp_id},
                {"$set": {"has_attachment": False}}
            )
            try:
                from bson import ObjectId
                await db.expenses.update_one(
                    {"_id": ObjectId(exp_id)},
                    {"$set": {"has_attachment": False}}
                )
            except Exception:
                pass
    
    # Remove from group attachments array
    if attachment.get("invoice_group_id"):
        await db.invoice_groups.update_one(
            {"group_id": attachment["invoice_group_id"]},
            {"$pull": {"attachments": attachment_id}}
        )
    
    return {"success": True, "message": "Attachment deleted"}

@router.get("/expense/{expense_id}/attachments")
async def get_expense_attachments(expense_id: str, token: str):
    """Get all attachments for an expense (including from linked group)"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Get direct attachments
    direct_attachments = await db.expense_attachments.find(
        {"expense_id": expense_id, "is_deleted": {"$ne": True}},
        {"_id": 0}
    ).to_list(50)
    
    # Check if expense is linked to a group
    expense = await db.expenses.find_one({"expense_id": expense_id})
    group_attachments = []
    
    if expense and expense.get("invoice_group_id"):
        group_attachments = await db.expense_attachments.find(
            {"invoice_group_id": expense["invoice_group_id"], "is_deleted": {"$ne": True}},
            {"_id": 0}
        ).to_list(50)
        for att in group_attachments:
            att["source"] = "group"
    
    for att in direct_attachments:
        att["source"] = "direct"
    
    return {
        "success": True,
        "direct_attachments": direct_attachments,
        "group_attachments": group_attachments,
        "has_attachment": len(direct_attachments) > 0 or len(group_attachments) > 0
    }

# =======================================
# AUDIT & REPORTING ENDPOINTS
# =======================================

@router.post("/audit-report")
async def get_audit_report(req: ExportRequest):
    """Get audit report with attachment status for all expenses"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Build query
    query = {
        "center": req.center,
        "date": {"$gte": req.start_date, "$lte": req.end_date},
        "is_deleted": {"$ne": True}
    }
    
    if req.category:
        query["expense_type"] = req.category
    if req.payment_mode:
        query["payment_mode"] = req.payment_mode
    
    expenses = await db.expenses.find(query, {"_id": 0}).sort("date", 1).to_list(5000)
    
    # Enrich with attachment and group info
    result = []
    missing_count = 0
    attached_count = 0
    grouped_count = 0
    mismatch_count = 0
    
    for exp in expenses:
        exp_id = exp.get("expense_id", str(exp.get("_id", "")))
        
        # Check direct attachments
        direct_att = await db.expense_attachments.find(
            {"expense_id": exp_id, "is_deleted": {"$ne": True}},
            {"_id": 0, "attachment_id": 1, "original_filename": 1}
        ).to_list(10)
        
        # Check group attachments
        group_att = []
        group_info = None
        if exp.get("invoice_group_id"):
            group = await db.invoice_groups.find_one(
                {"group_id": exp["invoice_group_id"], "is_deleted": {"$ne": True}},
                {"_id": 0}
            )
            if group:
                group_info = {
                    "group_id": group["group_id"],
                    "vendor_name": group["vendor_name"],
                    "invoice_number": group["invoice_number"],
                    "bill_date": group["bill_date"],
                    "total_bill_amount": group["total_bill_amount"]
                }
                group_att = await db.expense_attachments.find(
                    {"invoice_group_id": exp["invoice_group_id"], "is_deleted": {"$ne": True}},
                    {"_id": 0, "attachment_id": 1, "original_filename": 1}
                ).to_list(10)
        
        # Determine attachment status
        has_direct = len(direct_att) > 0
        has_group = len(group_att) > 0
        
        if has_direct:
            attachment_status = "attached"
            attachment_source = "direct"
            attached_count += 1
        elif has_group:
            attachment_status = "attached_via_group"
            attachment_source = "group"
            attached_count += 1
        else:
            attachment_status = "missing"
            attachment_source = None
            missing_count += 1
        
        is_grouped = bool(exp.get("invoice_group_id"))
        if is_grouped:
            grouped_count += 1
        
        # Check for amount mismatch if grouped
        amount_match = None
        if group_info:
            # Get all expenses in this group
            group_expenses = await db.expenses.find(
                {"invoice_group_id": exp["invoice_group_id"], "is_deleted": {"$ne": True}},
                {"amount": 1}
            ).to_list(100)
            group_total = sum(e.get("amount", 0) for e in group_expenses)
            diff = abs(group_info["total_bill_amount"] - group_total)
            amount_match = "exact" if diff < 0.01 else "mismatch"
            if amount_match == "mismatch":
                mismatch_count += 1
        
        # Apply filters
        if req.attachment_status:
            if req.attachment_status == "attached" and attachment_status == "missing":
                continue
            if req.attachment_status == "missing" and attachment_status != "missing":
                continue
        
        if req.grouped_status:
            if req.grouped_status == "grouped" and not is_grouped:
                continue
            if req.grouped_status == "ungrouped" and is_grouped:
                continue
        
        if req.vendor and group_info:
            if req.vendor.lower() not in group_info["vendor_name"].lower():
                continue
        
        result.append({
            **exp,
            "expense_id": exp_id,
            "attachment_status": attachment_status,
            "attachment_source": attachment_source,
            "direct_attachments": direct_att,
            "group_attachments": group_att,
            "is_grouped": is_grouped,
            "group_info": group_info,
            "amount_match": amount_match,
            "uploaded_by": exp.get("created_by", exp.get("updated_by", "Unknown"))
        })
    
    return {
        "success": True,
        "expenses": result,
        "summary": {
            "total_count": len(result),
            "attached_count": attached_count,
            "missing_count": missing_count,
            "grouped_count": grouped_count,
            "mismatch_count": mismatch_count,
            "total_amount": sum(e.get("amount", 0) for e in result)
        }
    }

@router.post("/export-zip")
async def export_invoices_zip(req: ExportRequest):
    """Export invoices and attachments as ZIP with 3-month batching"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    start_date = datetime.strptime(req.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(req.end_date, "%Y-%m-%d")
    
    # Calculate date range in months
    months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    
    if months_diff > 3:
        # Return batch information instead of single ZIP
        batches = []
        current_start = start_date
        while current_start < end_date:
            batch_end = min(
                current_start + timedelta(days=90),  # Approximately 3 months
                end_date
            )
            # Adjust to end of month
            if batch_end.month != current_start.month or batch_end.year != current_start.year:
                # Find end of 3rd month
                batch_end_month = current_start.month + 2
                batch_end_year = current_start.year
                if batch_end_month > 12:
                    batch_end_month -= 12
                    batch_end_year += 1
                # Get last day of that month
                if batch_end_month in [4, 6, 9, 11]:
                    last_day = 30
                elif batch_end_month == 2:
                    last_day = 28
                else:
                    last_day = 31
                batch_end = datetime(batch_end_year, batch_end_month, last_day)
                if batch_end > end_date:
                    batch_end = end_date
            
            batches.append({
                "start_date": current_start.strftime("%Y-%m-%d"),
                "end_date": batch_end.strftime("%Y-%m-%d"),
                "label": f"{current_start.strftime('%b %Y')} - {batch_end.strftime('%b %Y')}"
            })
            current_start = batch_end + timedelta(days=1)
        
        return {
            "success": True,
            "requires_batching": True,
            "message": "Date range exceeds 3 months. Export has been split into 3-month batches for performance and audit convenience.",
            "batches": batches
        }
    
    # Generate single ZIP
    zip_data = await _generate_export_zip(req)
    
    filename = f"{req.center}_Invoices_{req.start_date}_to_{req.end_date}.zip"
    
    return StreamingResponse(
        io.BytesIO(zip_data),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.post("/export-zip-batch")
async def export_single_batch_zip(req: ExportRequest):
    """Export a single batch ZIP (for date ranges within 3 months)"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    zip_data = await _generate_export_zip(req)
    
    filename = f"{req.center}_Invoices_{req.start_date}_to_{req.end_date}.zip"
    
    return StreamingResponse(
        io.BytesIO(zip_data),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

async def _generate_export_zip(req: ExportRequest) -> bytes:
    """Generate ZIP file with invoices and reports"""
    # Get audit report data
    audit_data = await get_audit_report(req)
    expenses = audit_data["expenses"]
    summary = audit_data["summary"]
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Create folder structure
        center_folder = req.center.replace("-", "_")
        
        # Group expenses by month
        by_month = {}
        for exp in expenses:
            month_key = exp.get("date", "")[:7]  # YYYY-MM
            if month_key not in by_month:
                by_month[month_key] = []
            by_month[month_key].append(exp)
        
        # Process each month
        for month_key, month_expenses in sorted(by_month.items()):
            month_folder = f"{center_folder}/{month_key}"
            
            # Download and add attachments
            grouped_folder = f"{month_folder}/Grouped_Invoices"
            individual_folder = f"{month_folder}/Individual_Expenses"
            
            added_group_files = set()  # Track to avoid duplicates
            
            for exp in month_expenses:
                # Individual attachments
                for att in exp.get("direct_attachments", []):
                    try:
                        attachment = await db.expense_attachments.find_one(
                            {"attachment_id": att.get("attachment_id"), "is_deleted": {"$ne": True}}
                        )
                        if attachment:
                            content, _ = get_object(attachment["storage_path"])
                            filename = f"{exp.get('expense_id', 'EXP')}_{exp.get('description', 'expense')[:20]}_{exp.get('date', '')}.{attachment.get('file_type', 'pdf')}"
                            filename = "".join(c for c in filename if c.isalnum() or c in '._-')
                            zf.writestr(f"{individual_folder}/{filename}", content)
                    except Exception as e:
                        logger.error(f"Failed to add attachment: {e}")
                
                # Group attachments (only once per group)
                group_info = exp.get("group_info")
                if group_info and group_info["group_id"] not in added_group_files:
                    for att in exp.get("group_attachments", []):
                        try:
                            attachment = await db.expense_attachments.find_one(
                                {"attachment_id": att.get("attachment_id"), "is_deleted": {"$ne": True}}
                            )
                            if attachment:
                                content, _ = get_object(attachment["storage_path"])
                                vendor = group_info.get("vendor_name", "Vendor")[:20]
                                inv_no = group_info.get("invoice_number", "INV")[:20]
                                bill_date = group_info.get("bill_date", "")
                                filename = f"{vendor}_{inv_no}_{bill_date}.{attachment.get('file_type', 'pdf')}"
                                filename = "".join(c for c in filename if c.isalnum() or c in '._-')
                                zf.writestr(f"{grouped_folder}/{filename}", content)
                        except Exception as e:
                            logger.error(f"Failed to add group attachment: {e}")
                    added_group_files.add(group_info["group_id"])
        
        # Add CSV reports
        # 1. Expense Register
        expense_csv = io.StringIO()
        writer = csv.writer(expense_csv)
        writer.writerow([
            "Date", "Description", "Category", "Payment Mode", "Amount",
            "Vendor", "Invoice #", "Bill Date", "Attachment Status",
            "Grouped", "Uploaded By"
        ])
        for exp in expenses:
            gi = exp.get("group_info") or {}
            writer.writerow([
                exp.get("date", ""),
                exp.get("description", ""),
                exp.get("expense_type", ""),
                exp.get("payment_mode", ""),
                exp.get("amount", 0),
                gi.get("vendor_name", ""),
                gi.get("invoice_number", ""),
                gi.get("bill_date", ""),
                exp.get("attachment_status", ""),
                "Yes" if exp.get("is_grouped") else "No",
                exp.get("uploaded_by", "")
            ])
        zf.writestr(f"{center_folder}/expense_register.csv", expense_csv.getvalue())
        
        # 2. Grouped Invoice Summary
        groups = {}
        for exp in expenses:
            gi = exp.get("group_info")
            if gi:
                gid = gi["group_id"]
                if gid not in groups:
                    groups[gid] = {**gi, "expenses": [], "total": 0}
                groups[gid]["expenses"].append(exp)
                groups[gid]["total"] += exp.get("amount", 0)
        
        group_csv = io.StringIO()
        writer = csv.writer(group_csv)
        writer.writerow([
            "Vendor", "Invoice #", "Bill Date", "Bill Amount",
            "Linked Expense Total", "Difference", "Match Status", "Expense Count"
        ])
        for gid, g in groups.items():
            diff = abs(g["total_bill_amount"] - g["total"])
            match = "Exact" if diff < 0.01 else "Mismatch"
            writer.writerow([
                g["vendor_name"],
                g["invoice_number"],
                g["bill_date"],
                g["total_bill_amount"],
                g["total"],
                round(diff, 2),
                match,
                len(g["expenses"])
            ])
        zf.writestr(f"{center_folder}/grouped_invoice_summary.csv", group_csv.getvalue())
        
        # 3. Missing Attachment Report
        missing_csv = io.StringIO()
        writer = csv.writer(missing_csv)
        writer.writerow(["Date", "Description", "Category", "Amount", "Payment Mode"])
        for exp in expenses:
            if exp.get("attachment_status") == "missing":
                writer.writerow([
                    exp.get("date", ""),
                    exp.get("description", ""),
                    exp.get("expense_type", ""),
                    exp.get("amount", 0),
                    exp.get("payment_mode", "")
                ])
        zf.writestr(f"{center_folder}/missing_attachment_report.csv", missing_csv.getvalue())
        
        # 4. Summary
        summary_txt = f"""
EXPENSE EXPORT SUMMARY
======================
Center: {req.center}
Period: {req.start_date} to {req.end_date}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

COUNTS
------
Total Expenses: {summary['total_count']}
With Attachments: {summary['attached_count']}
Missing Attachments: {summary['missing_count']}
Grouped Expenses: {summary['grouped_count']}
Amount Mismatches: {summary['mismatch_count']}

TOTAL AMOUNT: {summary['total_amount']:,.2f}
"""
        zf.writestr(f"{center_folder}/summary.txt", summary_txt)
    
    zip_buffer.seek(0)
    return zip_buffer.read()

# =======================================
# DATA RETENTION ENDPOINTS
# =======================================

@router.get("/retention-check")
async def check_retention(token: str, center: str):
    """Check for data older than 7 years that can be archived/deleted"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Only allow Admin to check retention
    if not (session.get("is_super_admin") or session.get("is_admin")):
        raise HTTPException(403, "Only Admin can check retention policy")
    
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=RETENTION_YEARS * 365)).strftime("%Y-%m-%d")
    
    # Count old expenses
    old_expenses = await db.expenses.count_documents({
        "center": center,
        "date": {"$lt": cutoff_date},
        "is_deleted": {"$ne": True}
    })
    
    # Count old attachments
    old_attachments = await db.expense_attachments.count_documents({
        "center": center,
        "created_at": {"$lt": cutoff_date},
        "is_deleted": {"$ne": True}
    })
    
    return {
        "success": True,
        "center": center,
        "retention_years": RETENTION_YEARS,
        "cutoff_date": cutoff_date,
        "old_expenses_count": old_expenses,
        "old_attachments_count": old_attachments,
        "message": f"Found {old_expenses} expenses and {old_attachments} attachments older than {RETENTION_YEARS} years"
    }

# =======================================
# HELPER FUNCTIONS
# =======================================

async def _link_expenses_to_group(group_id: str, expense_ids: List[str], center: str) -> int:
    """Link multiple expenses to an invoice group"""
    linked_count = 0
    for exp_id in expense_ids:
        try:
            # Try expense_id first
            result = await db.expenses.update_one(
                {"expense_id": exp_id, "center": center},
                {"$set": {"invoice_group_id": group_id}}
            )
            if result.modified_count == 0:
                # Try ObjectId
                try:
                    result = await db.expenses.update_one(
                        {"_id": ObjectId(exp_id), "center": center},
                        {"$set": {"invoice_group_id": group_id}}
                    )
                except Exception:
                    pass
            if result.modified_count > 0:
                linked_count += 1
        except Exception as e:
            logger.error(f"Failed to link expense {exp_id}: {e}")
    return linked_count

async def _update_group_totals(group_id: str):
    """Update linked expense count and total for a group"""
    linked = await db.expenses.find(
        {"invoice_group_id": group_id, "is_deleted": {"$ne": True}},
        {"amount": 1}
    ).to_list(500)
    
    total = sum(e.get("amount", 0) for e in linked)
    
    await db.invoice_groups.update_one(
        {"group_id": group_id},
        {"$set": {
            "linked_expense_count": len(linked),
            "linked_expense_total": total,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
