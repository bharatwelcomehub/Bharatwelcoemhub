# =======================================
# Document Management Routes
# Franchise & Employee Document Management
# with Approval Hierarchy & Expiry Tracking
# =======================================

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Response, Query, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import os
import logging
import requests

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Document Management"])

db = None
verify_token = None
verify_token_async_func = None

def set_db(database):
    global db
    db = database

def set_verify_token(func):
    global verify_token
    verify_token = func

def set_verify_token_async(func):
    global verify_token_async_func
    verify_token_async_func = func

async def get_session(token: str):
    if verify_token_async_func:
        session = await verify_token_async_func(token)
        if session:
            return session
    return verify_token(token)

def check_admin(session):
    return session and (session.get("is_super_admin") or session.get("is_admin"))

# =======================================
# OBJECT STORAGE HELPERS
# =======================================

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "purnabramha"
storage_key = None

def init_storage():
    global storage_key
    if storage_key:
        return storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    storage_key = resp.json()["storage_key"]
    logger.info("Object storage initialized successfully")
    return storage_key

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120,
    )
    resp.raise_for_status()
    return resp.json()

def get_object(path: str):
    key = init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60,
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "doc", "docx", "xls", "xlsx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# =======================================
# PYDANTIC MODELS
# =======================================

class CategoryCreate(BaseModel):
    token: str
    name: str
    level: str               # "franchise" or "employee"
    requires_expiry: bool = False
    description: Optional[str] = ""

class CategoryUpdate(BaseModel):
    token: str
    category_id: str
    name: Optional[str] = None
    level: Optional[str] = None
    requires_expiry: Optional[bool] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class DocumentListReq(BaseModel):
    token: str
    center: Optional[str] = None
    level: Optional[str] = None          # franchise / employee
    category: Optional[str] = None
    status: Optional[str] = None         # pending / approved / rejected
    employee_name: Optional[str] = None
    franchise_code: Optional[str] = None
    expiring_within_days: Optional[int] = None

class DocumentAction(BaseModel):
    token: str
    document_id: str
    action: str              # approve / reject
    notes: Optional[str] = ""

# =======================================
# CATEGORY ENDPOINTS
# =======================================

@router.post("/categories/create")
async def create_category(req: CategoryCreate):
    session = await get_session(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    if not check_admin(session):
        raise HTTPException(403, "Admin access required")

    if req.level not in ("franchise", "employee"):
        raise HTTPException(400, "Level must be 'franchise' or 'employee'")

    cat_id = str(uuid.uuid4())[:8]
    doc = {
        "category_id": cat_id,
        "name": req.name.strip(),
        "level": req.level,
        "requires_expiry": req.requires_expiry,
        "description": req.description or "",
        "is_active": True,
        "created_by": session.get("managerName", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.document_categories.insert_one(doc)
    return {"success": True, "category_id": cat_id}


@router.post("/categories/update")
async def update_category(req: CategoryUpdate):
    session = await get_session(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    if not check_admin(session):
        raise HTTPException(403, "Admin access required")

    updates = {}
    if req.name is not None:
        updates["name"] = req.name.strip()
    if req.level is not None:
        updates["level"] = req.level
    if req.requires_expiry is not None:
        updates["requires_expiry"] = req.requires_expiry
    if req.description is not None:
        updates["description"] = req.description
    if req.is_active is not None:
        updates["is_active"] = req.is_active

    if not updates:
        raise HTTPException(400, "No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.document_categories.update_one(
        {"category_id": req.category_id}, {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Category not found")
    return {"success": True}


@router.post("/categories/list")
async def list_categories(data: dict):
    token = data.get("token")
    session = await get_session(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    query = {}
    if data.get("level"):
        query["level"] = data["level"]
    if data.get("active_only", True):
        query["is_active"] = True

    cats = await db.document_categories.find(query, {"_id": 0}).sort("name", 1).to_list(200)
    return {"success": True, "categories": cats}


# =======================================
# DOCUMENT UPLOAD
# =======================================

@router.post("/upload")
async def upload_document(
    token: str = Form(...),
    center: str = Form(...),
    category_id: str = Form(...),
    level: str = Form(...),
    expiry_date: Optional[str] = Form(None),
    employee_name: Optional[str] = Form(None),
    franchise_code: Optional[str] = Form(None),
    notes: Optional[str] = Form(""),
    file: UploadFile = File(...),
):
    session = await get_session(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    # Validate file
    if not file.filename:
        raise HTTPException(400, "No file provided")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type .{ext} not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB")

    # Auto-correct center when uploading a franchise-level document. Earlier
    # versions of the franchise mgmt page tagged the uploader's center on the
    # doc (e.g. PB-MGT) instead of the franchise's home center (e.g. PB-DV),
    # which made docs invisible on the Document Management page when filtered
    # by the actual operating center. Resolve via the centers→franchise link.
    if level == "franchise" and franchise_code:
        fc_norm = franchise_code.upper().strip()
        # Look up centers attached to this franchise; skip the MGT pseudo-center.
        linked_centers = await db.centers.find(
            {"franchise_code": fc_norm}, {"_id": 0, "code": 1}
        ).to_list(50)
        codes = [c.get("code", "").upper() for c in linked_centers if c.get("code")]
        codes_non_mgt = [c for c in codes if c and c != "PB-MGT"]
        target = (codes_non_mgt[0] if codes_non_mgt else (codes[0] if codes else None))
        if target:
            center = target

    # Validate category
    category = await db.document_categories.find_one({"category_id": category_id}, {"_id": 0})
    if not category:
        raise HTTPException(404, "Document category not found")

    # Upload to object storage
    file_uuid = str(uuid.uuid4())
    storage_path = f"{APP_NAME}/documents/{center.upper()}/{file_uuid}.{ext}"

    try:
        result = put_object(storage_path, data, file.content_type or "application/octet-stream")
    except Exception as e:
        logger.error(f"Storage upload failed: {e}")
        raise HTTPException(500, "File upload failed. Please try again.")

    # Save document metadata to DB
    doc_id = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "document_id": doc_id,
        "center": center.upper(),
        "category_id": category_id,
        "category_name": category.get("name", ""),
        "level": level,
        "storage_path": result.get("path", storage_path),
        "original_filename": file.filename,
        "file_size": len(data),
        "content_type": file.content_type or "application/octet-stream",
        "employee_name": (employee_name or "").upper().strip() if level == "employee" else "",
        "franchise_code": (franchise_code or "").upper().strip() if level == "franchise" else "",
        "expiry_date": expiry_date or "",
        "notes": notes or "",
        "status": "pending",
        "uploaded_by": session.get("managerName", ""),
        "uploaded_by_center": session.get("center", ""),
        "approved_by": "",
        "approved_at": "",
        "rejection_reason": "",
        "is_deleted": False,
        "reminder_sent": False,
        "created_at": now,
        "updated_at": now,
    }
    await db.documents.insert_one(doc)

    logger.info(f"Document uploaded: {file.filename} for {center} by {session.get('managerName')}")
    return {"success": True, "document_id": doc_id, "message": "Document uploaded successfully"}


# =======================================
# DOCUMENT LIST & SEARCH
# =======================================

@router.post("/list")
async def list_documents(req: DocumentListReq):
    session = await get_session(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    query = {"is_deleted": False}

    # Non-admin can only see their center's docs
    if not check_admin(session):
        query["center"] = session.get("center", "").upper()

    if req.franchise_code:
        # When filtering by franchise, use OR logic for franchise_code + linked centers + explicit center
        franchise = await db.franchises.find_one(
            {"franchise_code": req.franchise_code.upper()}, {"_id": 0, "linked_centers": 1}
        )
        linked_centers = franchise.get("linked_centers", []) if franchise else []
        # Build set of all relevant centers
        all_centers = set(c.upper() for c in linked_centers)
        if req.center:
            all_centers.add(req.center.upper())
        # OR: match franchise_code OR center in linked/requested centers
        franchise_or = [{"franchise_code": req.franchise_code.upper()}]
        if all_centers:
            franchise_or.append({"center": {"$in": list(all_centers)}})
        query["$or"] = franchise_or
    elif req.center:
        query["center"] = req.center.upper()

    if req.level:
        query["level"] = req.level
    if req.category:
        query["category_id"] = req.category
    if req.status:
        query["status"] = req.status
    if req.employee_name:
        query["employee_name"] = req.employee_name.upper()

    # Expiry filter
    if req.expiring_within_days:
        future = (datetime.now(timezone.utc) + timedelta(days=req.expiring_within_days)).strftime("%Y-%m-%d")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        query["expiry_date"] = {"$ne": "", "$lte": future, "$gte": today}

    docs = await db.documents.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"success": True, "documents": docs, "total": len(docs)}


# =======================================
# DOCUMENT APPROVAL
# =======================================

@router.post("/action")
async def document_action(req: DocumentAction):
    session = await get_session(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    if not check_admin(session):
        raise HTTPException(403, "Only Admin/Super Admin can approve or reject documents")

    doc = await db.documents.find_one({"document_id": req.document_id, "is_deleted": False}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Document not found")

    now = datetime.now(timezone.utc).isoformat()

    if req.action == "approve":
        await db.documents.update_one(
            {"document_id": req.document_id},
            {"$set": {
                "status": "approved",
                "approved_by": session.get("managerName", "Admin"),
                "approved_at": now,
                "updated_at": now,
            }},
        )
        logger.info(f"Document {req.document_id} approved by {session.get('managerName')}")
        return {"success": True, "message": "Document approved"}

    elif req.action == "reject":
        await db.documents.update_one(
            {"document_id": req.document_id},
            {"$set": {
                "status": "rejected",
                "approved_by": session.get("managerName", "Admin"),
                "rejection_reason": req.notes or "",
                "updated_at": now,
            }},
        )
        logger.info(f"Document {req.document_id} rejected by {session.get('managerName')}")
        return {"success": True, "message": "Document rejected"}

    raise HTTPException(400, "Action must be 'approve' or 'reject'")


# =======================================
# DOCUMENT DOWNLOAD
# =======================================

@router.get("/file/{document_id}")
async def download_document(
    document_id: str,
    authorization: Optional[str] = Header(None),
    auth: Optional[str] = Query(None),
):
    # Support both header auth and query param auth
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif auth:
        token = auth

    if not token:
        raise HTTPException(401, "Authentication required")

    session = await get_session(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    doc = await db.documents.find_one(
        {"document_id": document_id, "is_deleted": False}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Document not found")

    try:
        data, content_type = get_object(doc["storage_path"])
    except Exception as e:
        logger.error(f"File download failed: {e}")
        raise HTTPException(500, "Failed to retrieve file")

    return Response(
        content=data,
        media_type=doc.get("content_type", content_type),
        headers={"Content-Disposition": f'inline; filename="{doc.get("original_filename", "document")}"'},
    )


# =======================================
# EXPIRY ALERTS
# =======================================

@router.post("/expiring")
async def get_expiring_documents(data: dict):
    """Get documents expiring within N days (default 30)"""
    token = data.get("token")
    session = await get_session(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    days = data.get("days", 30)
    future = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    query = {
        "is_deleted": False,
        "status": "approved",
        "expiry_date": {"$ne": "", "$lte": future},
    }

    # Include already-expired docs
    docs = await db.documents.find(query, {"_id": 0}).sort("expiry_date", 1).to_list(500)

    expiring_soon = [d for d in docs if d.get("expiry_date", "") >= today]
    already_expired = [d for d in docs if d.get("expiry_date", "") < today]

    return {
        "success": True,
        "expiring_soon": expiring_soon,
        "already_expired": already_expired,
        "total_alerts": len(docs),
    }


# =======================================
# DOCUMENT STATS
# =======================================

@router.post("/stats")
async def document_stats(data: dict):
    """Get document statistics"""
    token = data.get("token")
    session = await get_session(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    center = data.get("center")
    query = {"is_deleted": False}
    if center:
        query["center"] = center.upper()

    total = await db.documents.count_documents(query)
    pending = await db.documents.count_documents({**query, "status": "pending"})
    approved = await db.documents.count_documents({**query, "status": "approved"})
    rejected = await db.documents.count_documents({**query, "status": "rejected"})

    # Expiring within 30 days
    future_30 = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    expiring = await db.documents.count_documents({
        **query, "status": "approved",
        "expiry_date": {"$ne": "", "$lte": future_30, "$gte": today},
    })
    expired = await db.documents.count_documents({
        **query, "status": "approved",
        "expiry_date": {"$ne": "", "$lt": today},
    })

    return {
        "success": True,
        "stats": {
            "total": total, "pending": pending, "approved": approved,
            "rejected": rejected, "expiring_soon": expiring, "expired": expired,
        },
    }


# =======================================
# SOFT DELETE
# =======================================

@router.post("/delete")
async def delete_document(data: dict):
    token = data.get("token")
    session = await get_session(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    if not check_admin(session):
        raise HTTPException(403, "Admin access required")

    doc_id = data.get("document_id")
    result = await db.documents.update_one(
        {"document_id": doc_id},
        {"$set": {"is_deleted": True, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Document not found")
    return {"success": True, "message": "Document deleted"}
