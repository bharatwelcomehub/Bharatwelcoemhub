# =======================================
# Billing Configuration Masters
# Tables, Cancellation Reasons, Categories
# =======================================

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing-config", tags=["Billing Configuration"])

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

async def check_access(token: str) -> dict:
    session = None
    if verify_token_async_func:
        session = await verify_token_async_func(token)
    if not session:
        session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    return session

async def check_admin(token: str) -> dict:
    session = await check_access(token)
    if not session.get("is_super_admin") and not session.get("is_admin"):
        raise HTTPException(403, "Admin access required")
    return session


# =======================================
# TABLE MANAGEMENT
# =======================================

@router.post("/tables/list")
async def list_tables(data: dict):
    token = data.get("token")
    center = data.get("center", "")
    session = await check_access(token)

    query = {}
    if center:
        query["center"] = center

    tables = await db.billing_tables.find(query, {"_id": 0}).sort("table_no", 1).to_list(500)
    return {"tables": tables, "total": len(tables)}


@router.post("/tables/save")
async def save_table(data: dict):
    token = data.get("token")
    session = await check_admin(token)

    table_no = data.get("table_no", "").strip()
    center = data.get("center", "").strip()
    if not table_no or not center:
        raise HTTPException(400, "Table number and center are required")

    capacity = int(data.get("capacity", 4))
    floor = data.get("floor", "Ground")
    section = data.get("section", "")
    is_active = data.get("is_active", True)
    table_id = data.get("table_id", "")

    doc = {
        "table_no": table_no,
        "center": center,
        "capacity": capacity,
        "floor": floor,
        "section": section,
        "is_active": is_active,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": session.get("name", "")
    }

    if table_id:
        # Update
        existing = await db.billing_tables.find_one({"table_id": table_id})
        if not existing:
            raise HTTPException(404, "Table not found")
        await db.billing_tables.update_one({"table_id": table_id}, {"$set": doc})
    else:
        # Check duplicate
        dup = await db.billing_tables.find_one({"table_no": table_no, "center": center})
        if dup:
            raise HTTPException(400, f"Table {table_no} already exists for {center}")
        table_id = f"TBL-{center}-{table_no}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        doc["table_id"] = table_id
        doc["status"] = "available"
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        doc["created_by"] = session.get("name", "")
        await db.billing_tables.insert_one(doc)
        doc.pop("_id", None)

    return {"success": True, "table_id": table_id}


@router.post("/tables/delete")
async def delete_table(data: dict):
    token = data.get("token")
    session = await check_admin(token)
    table_id = data.get("table_id")
    if not table_id:
        raise HTTPException(400, "table_id required")

    result = await db.billing_tables.delete_one({"table_id": table_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Table not found")
    return {"success": True}


@router.post("/tables/update-status")
async def update_table_status(data: dict):
    """Update table status (available/occupied/reserved)."""
    token = data.get("token")
    session = await check_access(token)
    table_id = data.get("table_id")
    status = data.get("status", "available")

    if status not in ("available", "occupied", "reserved", "maintenance"):
        raise HTTPException(400, "Invalid status")

    result = await db.billing_tables.update_one(
        {"table_id": table_id},
        {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Table not found")
    return {"success": True}


# =======================================
# CANCELLATION REASONS
# =======================================

@router.post("/cancel-reasons/list")
async def list_cancel_reasons(data: dict):
    token = data.get("token")
    reason_type = data.get("type", "")  # order, bill, kot, or "" for all
    session = await check_access(token)

    query = {}
    if reason_type:
        query["type"] = reason_type

    reasons = await db.billing_cancel_reasons.find(query, {"_id": 0}).sort("reason", 1).to_list(200)
    return {"reasons": reasons, "total": len(reasons)}


@router.post("/cancel-reasons/save")
async def save_cancel_reason(data: dict):
    token = data.get("token")
    session = await check_admin(token)

    reason = data.get("reason", "").strip()
    reason_type = data.get("type", "order")
    if not reason:
        raise HTTPException(400, "Reason text is required")
    if reason_type not in ("order", "bill", "kot"):
        raise HTTPException(400, "Type must be one of: order, bill, kot")

    is_active = data.get("is_active", True)
    reason_id = data.get("reason_id", "")

    doc = {
        "reason": reason,
        "type": reason_type,
        "is_active": is_active,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": session.get("name", "")
    }

    if reason_id:
        existing = await db.billing_cancel_reasons.find_one({"reason_id": reason_id})
        if not existing:
            raise HTTPException(404, "Reason not found")
        await db.billing_cancel_reasons.update_one({"reason_id": reason_id}, {"$set": doc})
    else:
        dup = await db.billing_cancel_reasons.find_one({"reason": reason, "type": reason_type})
        if dup:
            raise HTTPException(400, f"Reason '{reason}' already exists for type '{reason_type}'")
        reason_id = f"CR-{reason_type.upper()}-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:20]}"
        doc["reason_id"] = reason_id
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        doc["created_by"] = session.get("name", "")
        await db.billing_cancel_reasons.insert_one(doc)
        doc.pop("_id", None)

    return {"success": True, "reason_id": reason_id}


@router.post("/cancel-reasons/delete")
async def delete_cancel_reason(data: dict):
    token = data.get("token")
    session = await check_admin(token)
    reason_id = data.get("reason_id")
    if not reason_id:
        raise HTTPException(400, "reason_id required")

    result = await db.billing_cancel_reasons.delete_one({"reason_id": reason_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Reason not found")
    return {"success": True}


# =======================================
# MENU CATEGORIES CRUD
# =======================================

@router.post("/categories/list")
async def list_categories(data: dict):
    token = data.get("token")
    session = await check_access(token)

    cats = await db.master_menu_categories.find({}, {"_id": 0}).sort("display_order", 1).to_list(200)
    return {"categories": cats, "total": len(cats)}


@router.post("/categories/save")
async def save_category(data: dict):
    token = data.get("token")
    session = await check_admin(token)

    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(400, "Category name is required")

    description = data.get("description", "")
    display_order = int(data.get("display_order", 99))
    is_active = data.get("is_active", True)
    category_id = data.get("category_id", "")

    doc = {
        "name": name,
        "description": description,
        "display_order": display_order,
        "is_active": is_active,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": session.get("name", "")
    }

    if category_id:
        existing = await db.master_menu_categories.find_one({"category_id": category_id})
        if not existing:
            raise HTTPException(404, "Category not found")
        await db.master_menu_categories.update_one({"category_id": category_id}, {"$set": doc})
    else:
        dup = await db.master_menu_categories.find_one({"name": name})
        if dup:
            raise HTTPException(400, f"Category '{name}' already exists")
        category_id = f"CAT-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:20]}"
        doc["category_id"] = category_id
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        doc["created_by"] = session.get("name", "")
        await db.master_menu_categories.insert_one(doc)
        doc.pop("_id", None)

    return {"success": True, "category_id": category_id}


@router.post("/categories/delete")
async def delete_category(data: dict):
    token = data.get("token")
    session = await check_admin(token)
    category_id = data.get("category_id")
    if not category_id:
        raise HTTPException(400, "category_id required")

    result = await db.master_menu_categories.delete_one({"category_id": category_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Category not found")
    return {"success": True}
