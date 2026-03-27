# =======================================
# CENTERS & MANAGERS MANAGEMENT ROUTES (Extracted from server.py)
# =======================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import re
import logging

router = APIRouter(prefix="/api/mgt", tags=["centers_managers"])
logger = logging.getLogger(__name__)

# Dependency injection
db = None
verify_token = None

def set_db(database):
    global db
    db = database

def set_verify_token(vt):
    global verify_token
    verify_token = vt

# =======================================
# CENTERS MANAGEMENT ENDPOINTS
# =======================================

@router.post("/centers")
async def mgt_get_centers(data: dict):
    """Get all centers for management (Super Admin + Admin)"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    centers = await db.centers.find({}, {"_id": 0}).to_list(100)
    if not centers:
        default_centers = [
            {"code": "PB-HSR", "name": "Purnabramha HSR - Bangalore", "phone": "+91 85500 78515", "email": "purnabramha.hsr09@gmail.com", "address": "17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout, Bangalore, Karnataka-560102", "active": True},
            {"code": "PB-TH", "name": "Purnabramha Thane - Mumbai", "phone": "+91 89047 49084", "email": "purnabramha.newthane@gmail.com", "address": "Thane, Mumbai, Maharashtra", "active": True},
            {"code": "PB-SN", "name": "Purnabramha Sambhajinagar", "phone": "+91 89710 49084", "email": "Purnabramha.aurangabad@gmail.com", "address": "Ch. Sambhajinagar, Maharashtra", "active": True},
            {"code": "PB-DV", "name": "Purnabramha Dombivli - Mumbai", "phone": "+91 96064 55433", "email": "purnabramha.dombivli@gmail.com", "address": "Dombivli, Mumbai, Maharashtra", "active": True},
            {"code": "PB-HW", "name": "Purnabramha Hinjawadi - Pune", "phone": "+91 96064 55434", "email": "Purnabramha.hinjawadi@gmail.com", "address": "Hinjawadi, Pune, Maharashtra", "active": True},
            {"code": "PB-KN", "name": "Purnabramha Kharadi Nyati - Pune", "phone": "", "email": "Purnabramha.kharadinyati@gmail.com", "address": "Kharadi Nyati, Pune, Maharashtra", "active": True},
            {"code": "PB-KAL", "name": "Purnabramha Kalyan", "phone": "", "email": "purnabramha.kalyan@gmail.com", "address": "Kalyan, Maharashtra", "active": True},
            {"code": "PB-PERTH", "name": "Purnabramha Perth - Australia", "phone": "0401832922", "email": "Purnabramha.perth@gmail.com", "address": "Perth, Australia", "active": True},
            {"code": "PB-MGT", "name": "Purnabramha Management (HQ)", "phone": "+91 9960886185", "email": "sandeep.gadhwal@purnabramha.com", "address": "HSR Layout, Bangalore", "active": True},
        ]
        for c in default_centers:
            await db.centers.update_one({"code": c["code"]}, {"$set": c}, upsert=True)
        centers = default_centers

    return {"centers": centers}


@router.post("/center_create")
async def mgt_center_create(data: dict):
    """Create a new center (MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can create centers")

    code = data.get("code", "").upper().strip()
    if not code:
        raise HTTPException(400, "Center code is required")

    existing = await db.centers.find_one({"code": code}, {"_id": 0})
    if existing:
        raise HTTPException(400, f"Center with code '{code}' already exists")

    center = {
        "code": code,
        "name": data.get("name", "").strip(),
        "phone": data.get("phone", "").strip(),
        "email": data.get("email", "").strip(),
        "address": data.get("address", "").strip(),
        "active": data.get("active", True),
        "is_india_center": data.get("is_india_center", True),
        "createdAt": datetime.now(timezone.utc).isoformat()
    }

    await db.centers.insert_one(center)
    logger.info(f"Center created: {code} by {session.get('managerName')}")
    return {"success": True, "message": f"Center '{code}' created successfully"}


@router.post("/center_update")
async def mgt_center_update(data: dict):
    """Update an existing center (MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can update centers")

    code = data.get("code", "").upper().strip()
    if not code:
        raise HTTPException(400, "Center code is required")

    update_data = {"updatedAt": datetime.now(timezone.utc).isoformat()}
    for field in ["name", "phone", "email", "address"]:
        if field in data and data[field] is not None:
            update_data[field] = data[field].strip()
    if "active" in data and data["active"] is not None:
        update_data["active"] = data["active"]
    if "is_india_center" in data and data["is_india_center"] is not None:
        update_data["is_india_center"] = data["is_india_center"]

    result = await db.centers.update_one({"code": code}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(404, f"Center '{code}' not found")

    logger.info(f"Center updated: {code} by {session.get('managerName')}")
    return {"success": True, "message": f"Center '{code}' updated successfully"}


@router.post("/center_delete")
async def mgt_center_delete(data: dict):
    """Delete a center (Super Admin + Admin)"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    code = data.get("code", "").upper().strip()
    if not code:
        raise HTTPException(400, "Center code is required")
    if code == "PB-MGT":
        raise HTTPException(400, "Cannot delete the Management HQ center")

    result = await db.centers.delete_one({"code": code})
    if result.deleted_count == 0:
        raise HTTPException(404, f"Center '{code}' not found")

    logger.info(f"Center deleted: {code} by {session.get('managerName')}")
    return {"success": True, "message": f"Center '{code}' deleted successfully"}


@router.post("/center_dedup")
async def mgt_center_dedup(data: dict):
    """Remove duplicate centers, keeping the one with more data (MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can deduplicate centers")

    all_centers = await db.centers.find({}).to_list(500)
    code_map = {}
    for c in all_centers:
        code = c.get("code", "")
        if code not in code_map:
            code_map[code] = []
        code_map[code].append(c)

    removed = []
    for code, entries in code_map.items():
        if len(entries) <= 1:
            continue
        def score(entry):
            s = 0
            for k, v in entry.items():
                if k == "_id":
                    continue
                if v and str(v).strip() and str(v).strip() != ".":
                    s += 1
            return s
        entries.sort(key=score, reverse=True)
        keep = entries[0]
        duplicates = entries[1:]
        for dup in duplicates:
            await db.centers.delete_one({"_id": dup["_id"]})
            removed.append({"code": code, "removed_id": str(dup["_id"]), "kept_id": str(keep["_id"])})
            logger.info(f"Dedup: removed duplicate center {code}")

    return {"success": True, "removed_count": len(removed), "details": removed}


# =======================================
# MANAGERS MANAGEMENT ENDPOINTS
# =======================================

@router.post("/managers")
async def mgt_get_managers(data: dict):
    """Get all managers (Super Admin only)"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    is_super_admin = session.get("is_super_admin", False)
    if not is_super_admin:
        raise HTTPException(403, "Only Super Admin can manage managers")
    managers = await db.managers.find({}, {"_id": 0}).to_list(100)
    return {"managers": managers}


@router.post("/manager_create")
async def mgt_manager_create(data: dict):
    """Create a new manager (Admin/MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    is_super_admin = session.get("is_super_admin", False) if session else False
    is_admin = session.get("is_admin", False) if session else False
    is_mgt = session.get("center") == "PB-MGT" if session else False

    if not session or (not is_super_admin and not is_admin and not is_mgt):
        raise HTTPException(403, "Only Admin or PB-MGT can create managers")

    center = data.get("center", "").upper().strip()
    email = data.get("email", "").strip().lower()
    if not center or not email:
        raise HTTPException(400, "Center and email are required")

    existing = await db.managers.find_one({"email": email}, {"_id": 0})
    if existing:
        raise HTTPException(400, f"Manager with email '{email}' already exists")

    manager = {
        "center": center,
        "managerName": data.get("managerName", "").strip(),
        "mobile": data.get("mobile", "").strip(),
        "email": email,
        "active": data.get("active", True),
        "otpChannel": data.get("otpChannel", "email"),
        "createdAt": datetime.now(timezone.utc).isoformat()
    }

    await db.managers.insert_one(manager)
    logger.info(f"Manager created: {email} for {center}")
    return {"success": True, "message": f"Manager '{manager['managerName']}' created successfully"}


@router.post("/manager_update")
async def mgt_manager_update(data: dict):
    """Update an existing manager (MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can update managers")

    email = data.get("email", "").strip().lower()
    if not email:
        raise HTTPException(400, "Manager email is required for identification")

    update_data = {"updatedAt": datetime.now(timezone.utc).isoformat()}
    if "center" in data and data["center"] is not None:
        update_data["center"] = data["center"].upper().strip()
    if "managerName" in data and data["managerName"] is not None:
        update_data["managerName"] = data["managerName"].strip()
    if "mobile" in data and data["mobile"] is not None:
        update_data["mobile"] = data["mobile"].strip()
    if "active" in data and data["active"] is not None:
        update_data["active"] = data["active"]
    if "otpChannel" in data and data["otpChannel"] is not None:
        update_data["otpChannel"] = data["otpChannel"]

    result = await db.managers.update_one({"email": email}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(404, f"Manager with email '{email}' not found")

    logger.info(f"Manager updated: {email}")
    return {"success": True, "message": "Manager updated successfully"}


@router.post("/manager_delete")
async def mgt_manager_delete(data: dict):
    """Delete a manager (Admin/MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    is_super_admin = session.get("is_super_admin", False) if session else False
    is_admin = session.get("is_admin", False) if session else False
    is_mgt = session.get("center") == "PB-MGT" if session else False
    current_email = session.get("email", "").lower() if session else ""
    jayanti_email = "jayanti.kathale@purnabramha.com"
    is_jayanti = current_email == jayanti_email

    if not session or (not is_super_admin and not is_admin and not is_mgt):
        raise HTTPException(403, "Only Admin or PB-MGT can delete managers")

    email = data.get("email", "").strip().lower()
    if not email:
        raise HTTPException(400, "Manager email is required")

    manager = await db.managers.find_one({"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}})
    if not manager:
        raise HTTPException(404, f"Manager with email '{email}' not found")

    if manager.get("is_super_admin") and not is_jayanti:
        raise HTTPException(403, "Only Jayanti Kathale can delete Super Admin accounts")
    if email == jayanti_email and not is_jayanti:
        raise HTTPException(403, "Cannot delete the master Super Admin account")

    result = await db.managers.delete_one({"email": manager.get("email")})
    if result.deleted_count == 0:
        raise HTTPException(404, f"Manager with email '{email}' not found")

    logger.info(f"Manager deleted: {email}")
    return {"success": True, "message": "Manager deleted successfully"}


@router.post("/manager_roles")
async def mgt_manager_roles(data: dict):
    """Update a manager's role permissions (Super Admin only)"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    is_super_admin = session.get("is_super_admin", False)
    if not is_super_admin:
        raise HTTPException(403, "Only Super Admin can manage roles")

    email = data.get("email", "").strip()
    roles = data.get("roles", {})
    set_is_admin = data.get("is_admin", False)
    if not email:
        raise HTTPException(400, "Manager email is required")

    escaped_email = re.escape(email)
    manager = await db.managers.find_one({"email": {"$regex": f"^{escaped_email}$", "$options": "i"}})
    if not manager:
        raise HTTPException(404, f"Manager with email '{email}' not found")

    await db.managers.update_one(
        {"email": manager.get("email")},
        {"$set": {
            "roles": roles,
            "is_admin": set_is_admin,
            "rolesUpdatedAt": datetime.now(timezone.utc).isoformat(),
            "rolesUpdatedBy": session.get("managerName", "Unknown")
        }}
    )

    logger.info(f"Manager roles updated: {email} (admin={set_is_admin})")
    return {"success": True, "message": "Manager roles updated successfully"}
