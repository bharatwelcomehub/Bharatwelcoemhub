# =======================================
# Bill Download Access Module
# Multi-download, ZIP, for franchise owners
# =======================================

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from datetime import datetime, timezone
import logging
import io
import zipfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bill-download", tags=["Bill Download"])

db = None
verify_token = None
has_admin_access = None

def set_db(database):
    global db
    db = database

def set_verify_token(func):
    global verify_token
    verify_token = func

def set_has_admin_access(func):
    global has_admin_access
    has_admin_access = func


DOC_TYPES = ["Sales Bill", "Expense Bill", "Expense Attachment", "Invoice", "Purchase Bill", "Platform Settlement", "Supporting Document", "Account Document", "Other"]


@router.post("/list")
async def list_bills(data: dict):
    """List bills/documents for a center with filters."""
    session = verify_token(data.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")

    is_admin = has_admin_access(session)
    query = {}

    # Role-based center access
    if not is_admin:
        user_center = session.get("center", "")
        # Check franchise ownership
        franchise = await db.franchises.find_one(
            {"$or": [{"owners": session.get("mobile")}, {"center_code": user_center}]},
            {"_id": 0, "center_code": 1}
        )
        if franchise:
            query["center"] = franchise.get("center_code", user_center)
        else:
            query["center"] = user_center
    elif data.get("center"):
        query["center"] = data["center"].upper()

    # Filters
    if data.get("doc_type"):
        query["doc_type"] = data["doc_type"]
    if data.get("expense_head"):
        query["expense_head"] = data["expense_head"]
    if data.get("uploaded_by"):
        query["uploaded_by"] = data["uploaded_by"]
    if data.get("month"):
        query["date"] = {"$regex": f"^{data['month']}"}
    elif data.get("date_from") or data.get("date_to"):
        dq = {}
        if data.get("date_from"):
            dq["$gte"] = data["date_from"]
        if data.get("date_to"):
            dq["$lte"] = data["date_to"]
        query["date"] = dq
    elif data.get("year"):
        query["date"] = {"$regex": f"^{data['year']}"}

    raw_bills = await db.bills.find(query, {"_id": 0}).sort("date", -1).to_list(5000)
    
    # Normalize POS bills to standard format
    bills = []
    for rb in raw_bills:
        bills.append({
            "bill_id": rb.get("bill_id") or rb.get("bill_no", ""),
            "center": rb.get("center", ""),
            "date": rb.get("date", ""),
            "doc_type": rb.get("doc_type", "Sales Bill"),
            "description": rb.get("description") or f"{rb.get('order_type', '')} - Table {rb.get('table_no', '')}",
            "amount": rb.get("amount") or rb.get("grand_total", 0),
            "file_url": rb.get("file_url", ""),
            "file_name": rb.get("file_name", ""),
            "expense_head": rb.get("expense_head", ""),
            "uploaded_by": rb.get("uploaded_by") or rb.get("created_by", ""),
            "uploaded_at": rb.get("uploaded_at") or rb.get("created_at", ""),
        })

    # Search expense_attachments for uploaded bills (this is where actual uploads go)
    att_query = {"is_deleted": {"$ne": True}}
    if query.get("center"):
        att_query["center"] = query["center"]
    if data.get("month"):
        att_query["created_at"] = {"$regex": f"^{data['month']}"}
    elif data.get("date_from") or data.get("date_to"):
        dq = {}
        if data.get("date_from"):
            dq["$gte"] = data["date_from"]
        if data.get("date_to"):
            dq["$lte"] = data["date_to"] + "T23:59:59"
        if dq:
            att_query["created_at"] = dq

    attachments = await db.expense_attachments.find(att_query, {"_id": 0}).sort("created_at", -1).to_list(5000)

    for att in attachments:
        # Build download URL for the attachment
        att_id = att.get("attachment_id", "")
        file_url = f"/api/expense-attachments/download/{att_id}"
        
        # Try to get related expense info
        expense_info = ""
        expense_amount = 0
        exp_id = att.get("expense_id")
        if exp_id:
            from bson import ObjectId
            try:
                exp = await db.expenses.find_one({"_id": ObjectId(exp_id)}, {"_id": 0, "description": 1, "amount": 1, "expense_type": 1, "date": 1})
                if exp:
                    expense_info = exp.get("description", exp.get("expense_type", ""))
                    expense_amount = exp.get("amount", 0)
            except Exception:
                pass
        
        # Get group info if linked via group
        group_id = att.get("invoice_group_id")
        if group_id and not expense_info:
            grp = await db.expense_groups.find_one({"group_id": group_id}, {"_id": 0, "vendor_name": 1, "invoice_number": 1})
            if grp:
                expense_info = f"{grp.get('vendor_name', '')} - {grp.get('invoice_number', '')}"

        att_date = att.get("created_at", "")[:10]
        bills.append({
            "bill_id": att_id,
            "center": att.get("center", ""),
            "date": att_date,
            "doc_type": "Expense Attachment",
            "description": expense_info or att.get("original_filename", ""),
            "amount": expense_amount,
            "file_url": file_url,
            "file_name": att.get("original_filename", "attachment"),
            "expense_head": "",
            "uploaded_by": att.get("uploaded_by", ""),
            "uploaded_at": att.get("created_at", ""),
            "storage_path": att.get("storage_path", ""),
        })

    return {
        "bills": bills,
        "count": len(bills),
        "doc_types": DOC_TYPES,
    }


@router.post("/upload")
async def upload_bill(data: dict):
    """Upload a bill document (Admin / Manager)."""
    session = verify_token(data.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")

    import uuid
    bill_id = f"BILL-{str(uuid.uuid4())[:8].upper()}"
    bill = {
        "bill_id": bill_id,
        "center": (data.get("center") or session.get("center", "")).upper(),
        "date": data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "doc_type": data.get("doc_type", "Other"),
        "description": data.get("description", ""),
        "amount": float(data.get("amount", 0)),
        "file_url": data.get("file_url", ""),
        "file_name": data.get("file_name", ""),
        "expense_head": data.get("expense_head", ""),
        "uploaded_by": session.get("managerName", session.get("mobile", "")),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.bills.insert_one(bill)
    return {"success": True, "bill_id": bill_id, "message": "Bill uploaded"}


@router.post("/download-zip")
async def download_zip(data: dict):
    """Download multiple bills as a ZIP file."""
    import urllib.request

    session = verify_token(data.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")

    is_admin = has_admin_access(session)
    center = (data.get("center") or session.get("center", "")).upper()

    # Franchise owner access check
    if not is_admin:
        user_center = session.get("center", "")
        franchise = await db.franchises.find_one(
            {"$or": [{"owners": session.get("mobile")}, {"center_code": user_center}]},
            {"_id": 0, "center_code": 1}
        )
        allowed_center = franchise.get("center_code", user_center) if franchise else user_center
        if center != allowed_center:
            raise HTTPException(403, "Access denied to this center's bills")

    # Get bill IDs or query
    bill_ids = data.get("bill_ids", [])
    query = {"center": center}

    if bill_ids:
        query["$or"] = [{"bill_id": {"$in": bill_ids}}, {"bill_id": {"$in": bill_ids}}]
    else:
        if data.get("month"):
            query["date"] = {"$regex": f"^{data['month']}"}
        elif data.get("date_from") and data.get("date_to"):
            query["date"] = {"$gte": data["date_from"], "$lte": data["date_to"]}
        if data.get("doc_type"):
            query["doc_type"] = data["doc_type"]

    bills = await db.bills.find(query, {"_id": 0}).to_list(5000)

    # Also check expense_attachments
    if not bill_ids:
        att_q = {"center": center, "is_deleted": {"$ne": True}}
        if data.get("month"):
            att_q["created_at"] = {"$regex": f"^{data['month']}"}
        elif data.get("date_from") and data.get("date_to"):
            att_q["created_at"] = {"$gte": data["date_from"], "$lte": data["date_to"] + "T23:59:59"}
        attachments = await db.expense_attachments.find(att_q, {"_id": 0}).to_list(5000)
        for att in attachments:
            att_id = att.get("attachment_id", "")
            bills.append({
                "bill_id": att_id,
                "date": att.get("created_at", "")[:10],
                "doc_type": "Expense_Attachment",
                "file_url": "",  # Will use storage_path instead
                "file_name": att.get("original_filename", "attachment"),
                "storage_path": att.get("storage_path", ""),
            })
    else:
        # Check if any bill_ids are attachment IDs
        att_ids = [bid for bid in bill_ids if bid.startswith("ATT-")]
        if att_ids:
            att_docs = await db.expense_attachments.find(
                {"attachment_id": {"$in": att_ids}, "is_deleted": {"$ne": True}},
                {"_id": 0}
            ).to_list(500)
            for att in att_docs:
                bills.append({
                    "bill_id": att.get("attachment_id", ""),
                    "date": att.get("created_at", "")[:10],
                    "doc_type": "Expense_Attachment",
                    "file_url": "",
                    "file_name": att.get("original_filename", "attachment"),
                    "storage_path": att.get("storage_path", ""),
                })

    if not bills:
        raise HTTPException(404, "No bills found for the given criteria")

    # Create ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for bill in bills:
            file_url = bill.get("file_url", "")
            storage_path = bill.get("storage_path", "")
            
            file_data = None
            
            # Try storage_path first (for expense_attachments)
            if storage_path:
                try:
                    from emergentintegrations.object_storage import get_object
                    result = get_object(storage_path)
                    if result and result.get("data"):
                        file_data = result["data"]
                except Exception as e:
                    logger.error(f"Failed to fetch from storage {storage_path}: {e}")
            
            # Fallback to URL download
            if not file_data and file_url and file_url.startswith("http"):
                try:
                    req = urllib.request.Request(file_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        file_data = resp.read()
                except Exception as e:
                    logger.error(f"Failed to download bill {bill.get('bill_id')}: {e}")
            
            if not file_data:
                continue
                
            # Build neat filename
            doc_type = bill.get("doc_type", "Other").replace(" ", "_")
            date_str = bill.get("date", "unknown")
            bill_id = bill.get("bill_id", "")
            orig_name = bill.get("file_name", "")
            ext = orig_name.rsplit(".", 1)[-1][:5] if "." in orig_name else (
                file_url.rsplit(".", 1)[-1][:5] if file_url and "." in file_url else "pdf"
            )
            filename = f"{center}/{doc_type}/{date_str}_{bill_id}.{ext}"
            zf.writestr(filename, file_data)

    zip_buffer.seek(0)
    zip_data = zip_buffer.getvalue()

    if len(zip_data) < 50:
        raise HTTPException(404, "No downloadable files found")

    period = data.get("month") or f"{data.get('date_from', '')}_{data.get('date_to', '')}" or "all"
    filename = f"Bills_{center}_{period}.zip"

    return Response(
        content=zip_data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
