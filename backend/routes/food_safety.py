# =======================================
# Food Safety Compliance Module
# Template CRUD, Record Submission, Reports
# For Perth / Non-Indian Centers
# =======================================

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/food-safety", tags=["Food Safety"])

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


# =======================================
# CONSTANTS
# =======================================

TEMPLATE_TYPES = [
    {"key": "food_items", "label": "Food Items (Master List)", "order": 0},
    {"key": "supplier_details", "label": "Supplier Details", "order": 1},
    {"key": "food_receipt", "label": "Food Receipt", "order": 2},
    {"key": "cooking_cooling", "label": "Cooking and Cooling Food", "order": 3},
    {"key": "food_temp_record", "label": "Food Temperature Record", "order": 4},
    {"key": "two_four_hour_rule", "label": "2-Hour / 4-Hour Rule Log", "order": 5},
    {"key": "cleaning_procedure", "label": "Cleaning and Sanitising Procedure", "order": 6},
    {"key": "cleaning_record", "label": "Cleaning and Sanitising Record", "order": 7},
    {"key": "general_temp_record", "label": "General Temperature Record", "order": 8},
]

TEMPLATE_COLUMNS = {
    "food_items": [
        {"key": "food_name", "label": "Food Item Name", "type": "text", "required": True},
        {"key": "category", "label": "Category", "type": "select", "options": ["Thali Item", "Bhaji/Sabji", "Dal/Amti", "Rice", "Drink/Beverage", "Chutney/Condiment", "Sweet/Dessert", "Bread/Roti", "Prep Item", "Display/Counter", "Takeaway", "Other"]},
        {"key": "notes", "label": "Notes", "type": "text"},
    ],
    "supplier_details": [
        {"key": "supplier_name", "label": "Supplier Name", "type": "text", "required": True},
        {"key": "contact", "label": "Contact Details", "type": "text"},
        {"key": "address", "label": "Address", "type": "text"},
        {"key": "foods_supplied", "label": "Foods Supplied", "type": "text"},
        {"key": "notes", "label": "Notes", "type": "text"},
    ],
    "food_receipt": [
        {"key": "date", "label": "Date", "type": "date", "required": True},
        {"key": "time", "label": "Time", "type": "time", "required": True},
        {"key": "supplier", "label": "Supplier", "type": "text", "required": True},
        {"key": "product", "label": "Product (Name & Lot)", "type": "text", "required": True},
        {"key": "condition_temp", "label": "Condition / Temp", "type": "text"},
        {"key": "corrective_action", "label": "Corrective Action / Notes", "type": "text"},
        {"key": "checked_by", "label": "Checked By", "type": "text", "required": True},
    ],
    "cooking_cooling": [
        {"key": "date", "label": "Date", "type": "date", "required": True},
        {"key": "food", "label": "Food", "type": "text", "required": True},
        {"key": "core_temp", "label": "Core Temp (>=75C)", "type": "number"},
        {"key": "cooling_start_time", "label": "Cooling Start Time", "type": "time"},
        {"key": "cooling_start_temp", "label": "Cooling Start Temp", "type": "number"},
        {"key": "time_2hr", "label": "Time at 2hr Check", "type": "time"},
        {"key": "temp_2hr", "label": "Temp at 2hr (<=21C?)", "type": "number"},
        {"key": "temp_2hr_ok", "label": "<=21C?", "type": "select", "options": ["Yes", "No"]},
        {"key": "time_4hr", "label": "Time at 4hr Check", "type": "time"},
        {"key": "temp_4hr", "label": "Temp at 4hr (<=5C?)", "type": "number"},
        {"key": "temp_within_4hrs", "label": "5\u00b0C or below within 4 hrs? (6 hrs after start)", "type": "select", "options": ["Yes", "No"]},
        {"key": "corrective_action", "label": "Corrective Action / Note", "type": "text"},
        {"key": "staff_initials", "label": "Staff Initials", "type": "text", "required": True},
    ],
    "food_temp_record": [
        {"key": "date", "label": "Date", "type": "date", "required": True},
        {"key": "time", "label": "Time", "type": "time", "required": True},
        {"key": "cold_unit_1", "label": "Walkin Fridge", "type": "number"},
        {"key": "cold_unit_2", "label": "Cold Bain Marie", "type": "number"},
        {"key": "cold_unit_3", "label": "Prep Fridge", "type": "number"},
        {"key": "hot_unit_1", "label": "Hot Unit 1 (Bain Marie)", "type": "number"},
        {"key": "cold_unit_4", "label": "Deep Fridge", "type": "number"},
        {"key": "cold_unit_5", "label": "Drink Fridge", "type": "number"},
        {"key": "notes", "label": "Notes", "type": "text"},
        {"key": "corrective_action", "label": "Corrective Action", "type": "text"},
        {"key": "staff_initials", "label": "Staff Initials", "type": "text", "required": True},
    ],
    "two_four_hour_rule": [
        {"key": "date", "label": "Date", "type": "date", "required": True},
        {"key": "food", "label": "Food", "type": "text", "required": True},
        {"key": "time_out", "label": "Time Out of Fridge (>5C)", "type": "time", "required": True},
        {"key": "activity", "label": "Activity (prep/display/transport)", "type": "text"},
        {"key": "time_back", "label": "Time Back in Temp Control (<=5C)", "type": "time"},
        {"key": "total_time_out", "label": "Total Time Out", "type": "calculated"},
        {"key": "action", "label": "Action", "type": "select",
         "options": ["Re-refrigerate", "Use immediately", "Discard"]},
        {"key": "remark", "label": "Remark", "type": "text"},
        {"key": "staff_initials", "label": "Staff Initials", "type": "text", "required": True},
    ],
    "cleaning_procedure": [
        {"key": "item_equipment", "label": "Item / Equipment", "type": "text", "required": True},
        {"key": "how_often", "label": "How Often", "type": "select",
         "options": ["After each use", "Daily", "Weekly", "Monthly", "As needed"]},
        {"key": "cleaning_method", "label": "Cleaning Method", "type": "textarea"},
        {"key": "sanitising_method", "label": "Sanitising Method", "type": "textarea"},
        {"key": "responsibility", "label": "Responsibility", "type": "text"},
        {"key": "comments", "label": "Comments", "type": "text"},
    ],
    "cleaning_record": [
        {"key": "area_equipment", "label": "Area / Equipment", "type": "text", "required": True},
        {"key": "frequency", "label": "Frequency", "type": "text"},
        {"key": "person_responsible", "label": "Person Responsible", "type": "text"},
        {"key": "sun", "label": "Sun", "type": "check"},
        {"key": "mon", "label": "Mon", "type": "check"},
        {"key": "tue", "label": "Tue", "type": "check"},
        {"key": "wed", "label": "Wed", "type": "check"},
        {"key": "thu", "label": "Thu", "type": "check"},
        {"key": "fri", "label": "Fri", "type": "check"},
        {"key": "sat", "label": "Sat", "type": "check"},
        {"key": "supervisor_initials", "label": "Supervisor Initials", "type": "text"},
    ],
    "general_temp_record": [
        {"key": "date", "label": "Date", "type": "date", "required": True},
        {"key": "time", "label": "Time", "type": "time", "required": True},
        {"key": "activity_food", "label": "Activity / Food / Appliance", "type": "text", "required": True},
        {"key": "food_temp", "label": "Food Temp (C)", "type": "number"},
        {"key": "corrective_action", "label": "Corrective Action / Notes", "type": "text"},
        {"key": "checked_by", "label": "Checked By", "type": "text", "required": True},
    ],
}

VALID_STATUSES = ["draft", "submitted", "approved", "locked"]


# =======================================
# HELPERS
# =======================================

def _now_iso():
    return datetime.now(timezone.utc).isoformat()


async def _is_non_india_center(center_code: str) -> bool:
    """Check if center is non-Indian (Perth, etc.)."""
    center = await db.centers.find_one({"code": center_code}, {"_id": 0, "country": 1, "is_india_center": 1})
    if not center:
        return False
    if center.get("is_india_center") is False:
        return True
    country = (center.get("country") or "").strip().lower()
    return country not in ("india", "")


def _check_auth(token: str, require_admin: bool = False):
    """Validate token and return session. Raises HTTPException on failure."""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    if require_admin and not has_admin_access(session):
        raise HTTPException(403, "Admin access required")
    return session


# =======================================
# TEMPLATE TYPES & COLUMNS (read-only)
# =======================================

@router.post("/template-types")
async def get_template_types(data: dict):
    """Return the 8 fixed template type definitions with their columns."""
    session = _check_auth(data.get("token"))
    return {
        "types": TEMPLATE_TYPES,
        "columns": TEMPLATE_COLUMNS,
    }


# =======================================
# TEMPLATE ITEMS CRUD (Admin)
# =======================================

@router.post("/template-items/list")
async def list_template_items(data: dict):
    """List all template items for a given template type, optionally filtered by center."""
    session = _check_auth(data.get("token"))
    template_type = data.get("template_type", "")
    center = data.get("center", "")

    query = {}
    if template_type:
        query["template_type"] = template_type
    if center:
        query["center"] = center.upper()

    items = await db.fs_template_items.find(query, {"_id": 0}).sort("order", 1).to_list(5000)
    return {"items": items}


@router.post("/template-items/save")
async def save_template_item(data: dict):
    """Create or update a template item (Admin only)."""
    session = _check_auth(data.get("token"), require_admin=True)

    item_id = data.get("item_id", "")
    template_type = data.get("template_type", "")
    if template_type not in TEMPLATE_COLUMNS:
        raise HTTPException(400, f"Invalid template_type: {template_type}")

    center = data.get("center", "").upper()
    item_data = {
        "template_type": template_type,
        "center": center,
        "name": data.get("name", "").strip(),
        "fields": data.get("fields", {}),
        "active": data.get("active", True),
        "order": int(data.get("order", 0)),
        "updatedAt": _now_iso(),
        "updatedBy": session.get("managerName", session.get("mobile", "")),
    }

    if item_id:
        result = await db.fs_template_items.update_one(
            {"item_id": item_id},
            {"$set": item_data}
        )
        if result.matched_count == 0:
            raise HTTPException(404, "Item not found")
        return {"success": True, "message": "Item updated", "item_id": item_id}
    else:
        import uuid
        item_id = str(uuid.uuid4())[:12]
        item_data["item_id"] = item_id
        item_data["createdAt"] = _now_iso()
        await db.fs_template_items.insert_one(item_data)
        return {"success": True, "message": "Item created", "item_id": item_id}


@router.post("/template-items/delete")
async def delete_template_item(data: dict):
    """Delete a template item (Admin only)."""
    session = _check_auth(data.get("token"), require_admin=True)
    item_id = data.get("item_id")
    if not item_id:
        raise HTTPException(400, "item_id required")
    result = await db.fs_template_items.delete_one({"item_id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Item not found")
    return {"success": True, "message": "Item deleted"}


@router.post("/template-items/toggle")
async def toggle_template_item(data: dict):
    """Activate / deactivate a template item (Admin only)."""
    session = _check_auth(data.get("token"), require_admin=True)
    item_id = data.get("item_id")
    active = data.get("active", True)
    result = await db.fs_template_items.update_one(
        {"item_id": item_id},
        {"$set": {"active": active, "updatedAt": _now_iso()}}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Item not found")
    return {"success": True, "active": active}


# =======================================
# RECORDS CRUD (Chef / Manager / Admin)
# =======================================

@router.post("/records/list")
async def list_records(data: dict):
    """List food safety records, optionally filtered by template_type, center, date range, status."""
    session = _check_auth(data.get("token"))

    query = {}
    if data.get("template_type"):
        query["template_type"] = data["template_type"]
    if data.get("center"):
        query["center"] = data["center"].upper()
    if data.get("status"):
        query["status"] = data["status"]
    if data.get("date_from") or data.get("date_to"):
        date_q = {}
        if data.get("date_from"):
            date_q["$gte"] = data["date_from"]
        if data.get("date_to"):
            date_q["$lte"] = data["date_to"]
        query["record_date"] = date_q

    records = await db.fs_records.find(query, {"_id": 0}).sort("record_date", -1).to_list(5000)
    return {"records": records}


# =======================================
# TEMPLATE APPROVAL SETTINGS
# =======================================

@router.post("/template-settings/get")
async def get_template_settings(data: dict):
    """Get approval settings for all template types."""
    _check_auth(data.get("token"))
    center = data.get("center", "").upper()

    settings = await db.fs_template_settings.find(
        {"center": center} if center else {},
        {"_id": 0}
    ).to_list(100)

    # Build map: template_type -> requires_approval (default False)
    settings_map = {}
    for s in settings:
        settings_map[s["template_type"]] = s.get("requires_approval", False)

    return {"settings": settings_map}


@router.post("/template-settings/save")
async def save_template_settings(data: dict):
    """Update requires_approval toggle for a template type (Admin only)."""
    session = _check_auth(data.get("token"), require_admin=True)
    template_type = data.get("template_type", "")
    if template_type not in TEMPLATE_COLUMNS:
        raise HTTPException(400, f"Invalid template_type: {template_type}")

    center = data.get("center", "").upper()
    requires_approval = data.get("requires_approval", False)

    await db.fs_template_settings.update_one(
        {"template_type": template_type, "center": center},
        {"$set": {
            "template_type": template_type,
            "center": center,
            "requires_approval": requires_approval,
            "updatedAt": _now_iso(),
            "updatedBy": session.get("managerName", session.get("mobile", "")),
        }},
        upsert=True
    )
    return {"success": True, "message": f"{'Approval required' if requires_approval else 'Auto-approve'} for {template_type}"}


# =======================================
# RECORDS CRUD (Chef / Manager / Admin)
# =======================================

@router.post("/records/save")
async def save_record(data: dict):
    """Create or update a food safety record (draft or submit)."""
    session = _check_auth(data.get("token"))
    center = data.get("center", "").upper()

    is_admin = has_admin_access(session)
    if not is_admin:
        if not await _is_non_india_center(center):
            raise HTTPException(403, "Only non-Indian center staff can submit food safety records")

    record_id = data.get("record_id", "")
    template_type = data.get("template_type", "")
    if template_type not in TEMPLATE_COLUMNS:
        raise HTTPException(400, f"Invalid template_type: {template_type}")

    status = data.get("status", "draft")
    if status not in ("draft", "submitted"):
        raise HTTPException(400, "Status must be draft or submitted")

    # Check if this template requires approval
    needs_approval = False
    if status == "submitted":
        setting = await db.fs_template_settings.find_one(
            {"template_type": template_type, "center": center},
            {"_id": 0, "requires_approval": 1}
        )
        needs_approval = setting.get("requires_approval", False) if setting else False

    # Auto-approve if no approval required
    final_status = status
    if status == "submitted" and not needs_approval:
        final_status = "approved"

    record_data = {
        "template_type": template_type,
        "center": center,
        "record_date": data.get("record_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "period": data.get("period", "daily"),
        "week_start": data.get("week_start", ""),
        "entries": data.get("entries", []),
        "status": final_status,
        "notes": data.get("notes", ""),
        "updatedAt": _now_iso(),
        "updatedBy": session.get("managerName", session.get("mobile", "")),
    }

    if status == "submitted":
        record_data["submittedAt"] = _now_iso()
        record_data["submittedBy"] = session.get("managerName", session.get("mobile", ""))
        record_data["submittedByRole"] = "Admin" if is_admin else (session.get("designation", "Manager"))
        if not needs_approval:
            record_data["approvedAt"] = _now_iso()
            record_data["approvedBy"] = "Auto-Approved"
            record_data["auto_approved"] = True

    if record_id:
        existing = await db.fs_records.find_one({"record_id": record_id}, {"_id": 0, "status": 1})
        if existing and existing.get("status") in ("approved", "locked"):
            raise HTTPException(403, "Cannot edit approved/locked records")
        result = await db.fs_records.update_one({"record_id": record_id}, {"$set": record_data})
        if result.matched_count == 0:
            raise HTTPException(404, "Record not found")
        msg = "Record auto-approved" if final_status == "approved" and status == "submitted" else f"Record {final_status}"
        return {"success": True, "message": msg, "record_id": record_id, "auto_approved": final_status == "approved" and status == "submitted" and not needs_approval}
    else:
        import uuid
        record_id = f"FSR-{str(uuid.uuid4())[:8].upper()}"
        record_data["record_id"] = record_id
        record_data["createdAt"] = _now_iso()
        record_data["createdBy"] = session.get("managerName", session.get("mobile", ""))
        await db.fs_records.insert_one(record_data)
        msg = "Record auto-approved" if final_status == "approved" and status == "submitted" else f"Record {final_status}"
        return {"success": True, "message": msg, "record_id": record_id, "auto_approved": final_status == "approved" and status == "submitted" and not needs_approval}


@router.post("/records/approve")
async def approve_record(data: dict):
    """Approve a submitted record (Admin/Manager)."""
    session = _check_auth(data.get("token"))
    record_id = data.get("record_id")

    record = await db.fs_records.find_one({"record_id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Record not found")
    if record.get("status") != "submitted":
        raise HTTPException(400, "Only submitted records can be approved")

    await db.fs_records.update_one(
        {"record_id": record_id},
        {"$set": {
            "status": "approved",
            "approvedAt": _now_iso(),
            "approvedBy": session.get("managerName", session.get("mobile", "")),
            "updatedAt": _now_iso(),
        }}
    )
    return {"success": True, "message": "Record approved"}


@router.post("/records/lock")
async def lock_record(data: dict):
    """Lock an approved record (Admin only). No further edits allowed."""
    session = _check_auth(data.get("token"), require_admin=True)
    record_id = data.get("record_id")

    result = await db.fs_records.update_one(
        {"record_id": record_id, "status": "approved"},
        {"$set": {"status": "locked", "lockedAt": _now_iso(), "updatedAt": _now_iso()}}
    )
    if result.matched_count == 0:
        raise HTTPException(400, "Record must be in approved status to lock")
    return {"success": True, "message": "Record locked"}


@router.post("/records/delete")
async def delete_record(data: dict):
    """Delete a food safety record (Admin only)."""
    session = _check_auth(data.get("token"), require_admin=True)
    record_id = data.get("record_id")
    if not record_id:
        raise HTTPException(400, "record_id required")

    result = await db.fs_records.delete_one({"record_id": record_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Record not found")
    return {"success": True, "message": "Record deleted"}


# =======================================
# DASHBOARD
# =======================================

@router.post("/dashboard")
async def food_safety_dashboard(data: dict):
    """Get dashboard summary with record counts by status, overdue alerts, etc."""
    session = _check_auth(data.get("token"))
    center = data.get("center", "").upper()

    query = {}
    if center:
        query["center"] = center

    # Status counts
    pipeline = [
        {"$match": query},
        {"$group": {"_id": {"template_type": "$template_type", "status": "$status"}, "count": {"$sum": 1}}},
    ]
    agg_results = await db.fs_records.aggregate(pipeline).to_list(500)

    status_map = {}
    for r in agg_results:
        tt = r["_id"]["template_type"]
        st = r["_id"]["status"]
        if tt not in status_map:
            status_map[tt] = {"draft": 0, "submitted": 0, "approved": 0, "locked": 0}
        status_map[tt][st] = r["count"]

    # Recent records
    recent = await db.fs_records.find(query, {"_id": 0}).sort("updatedAt", -1).to_list(20)

    # Check for missing today's records (overdue)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_types = ["food_receipt", "cooking_cooling", "food_temp_record", "two_four_hour_rule", "general_temp_record"]
    overdue = []
    for dt in daily_types:
        q = {**query, "template_type": dt, "record_date": today}
        exists = await db.fs_records.find_one(q, {"_id": 0, "record_id": 1})
        if not exists:
            label = next((t["label"] for t in TEMPLATE_TYPES if t["key"] == dt), dt)
            overdue.append({"template_type": dt, "label": label, "date": today})

    return {
        "status_counts": status_map,
        "recent_records": recent,
        "overdue": overdue,
        "template_types": TEMPLATE_TYPES,
    }


# =======================================
# SEED DATA
# =======================================

@router.post("/seed")
async def seed_template_data(data: dict):
    """Seed default template items for Purnabramha Perth menu. Admin only."""
    session = _check_auth(data.get("token"), require_admin=True)
    center = data.get("center", "PB-PERTH").upper()

    # Check if already seeded
    existing = await db.fs_template_items.count_documents({"center": center})
    food_items_exist = await db.fs_template_items.count_documents({"center": center, "template_type": "food_items"})
    if existing > 0 and food_items_exist > 0:
        return {"success": True, "message": f"Already seeded ({existing} items, {food_items_exist} food items). Use CRUD to manage.", "seeded": 0}
    
    # If other items exist but food_items don't, only seed food_items
    seed_all = existing == 0

    import uuid
    items = []
    now = _now_iso()

    # Supplier Details
    if seed_all:
        suppliers = [
            {"name": "Fresh Produce Supplier", "fields": {"supplier_name": "Fresh Produce WA", "contact": "08-XXXX-XXXX", "foods_supplied": "Vegetables, Herbs, Salad items", "address": "Perth Markets, WA"}},
            {"name": "Dairy & Curd Supplier", "fields": {"supplier_name": "WA Dairy Co", "contact": "08-XXXX-XXXX", "foods_supplied": "Curd, Milk, Paneer, Cream", "address": "Jandakot, WA"}},
            {"name": "Spice & Dry Goods", "fields": {"supplier_name": "Indian Spice House", "contact": "08-XXXX-XXXX", "foods_supplied": "Spices, Dal, Rice, Flour, Oil", "address": "Cannington, WA"}},
            {"name": "Meat & Protein (if applicable)", "fields": {"supplier_name": "WA Meats", "contact": "08-XXXX-XXXX", "foods_supplied": "Chicken, Eggs", "address": "Osborne Park, WA"}},
        ]
        for i, s in enumerate(suppliers):
            items.append({**s, "item_id": str(uuid.uuid4())[:12], "template_type": "supplier_details", "center": center, "active": True, "order": i, "createdAt": now, "updatedAt": now})

    if seed_all:
        # Cleaning Procedures
        cleaning_items = [
            {"name": "Kitchen Benchtops", "fields": {"item_equipment": "Kitchen Benchtops / Prep Tables", "how_often": "After each use", "cleaning_method": "Wipe down with hot soapy water, rinse", "sanitising_method": "Spray food-safe sanitiser, leave 30 sec, wipe", "responsibility": "All kitchen staff"}},
            {"name": "Bain Marie", "fields": {"item_equipment": "Bain Marie / Hot Holding Units", "how_often": "Daily", "cleaning_method": "Drain, scrub with detergent, rinse with hot water", "sanitising_method": "Spray sanitiser on all surfaces, air dry", "responsibility": "Closing chef"}},
            {"name": "Fridges & Cold Units", "fields": {"item_equipment": "Fridges / Walk-in Cooler", "how_often": "Weekly", "cleaning_method": "Remove all items, wipe shelves with warm soapy water, rinse", "sanitising_method": "Apply food-safe sanitiser, wipe down, air dry", "responsibility": "Kitchen manager"}},
            {"name": "Floors & Drains", "fields": {"item_equipment": "Kitchen Floors & Drains", "how_often": "Daily", "cleaning_method": "Sweep, mop with hot detergent solution", "sanitising_method": "Flush drains with sanitiser weekly", "responsibility": "Closing staff"}},
            {"name": "Utensils & Pots", "fields": {"item_equipment": "Cooking Utensils, Pots, Pans", "how_often": "After each use", "cleaning_method": "Scrape, wash in hot soapy water, rinse", "sanitising_method": "Rinse with sanitiser or run through dishwasher", "responsibility": "Dishwasher / Chef"}},
            {"name": "Exhaust & Hood", "fields": {"item_equipment": "Exhaust Hood & Filters", "how_often": "Monthly", "cleaning_method": "Remove filters, soak in degreaser, scrub, rinse", "sanitising_method": "N/A - degrease and dry", "responsibility": "Kitchen manager"}},
        ]
        for i, c in enumerate(cleaning_items):
            items.append({**c, "item_id": str(uuid.uuid4())[:12], "template_type": "cleaning_procedure", "center": center, "active": True, "order": i, "createdAt": now, "updatedAt": now})

        # Cleaning Record items (areas to track weekly)
        cleaning_rec_items = [
            "Kitchen Benchtops", "Bain Marie", "Fridge 1", "Fridge 2", "Walk-in Cooler",
            "Floors", "Drains", "Dishwasher", "Hand Wash Basin", "Exhaust Hood",
            "Storage Shelves", "Waste Bins", "Thali Service Counter",
        ]
        for i, name in enumerate(cleaning_rec_items):
            items.append({
                "name": name, "item_id": str(uuid.uuid4())[:12], "template_type": "cleaning_record",
                "center": center, "active": True, "order": i,
                "fields": {"area_equipment": name, "frequency": "Daily"},
                "createdAt": now, "updatedAt": now,
            })

    # Purnabramha Menu Items — ONE master food list used by all food dropdowns
    menu_items = [
        ("Maharashtrian Thali", "Thali Item"),
        ("Bhaji (Mixed Veg)", "Bhaji/Sabji"),
        ("Amti / Varan (Dal)", "Dal/Amti"),
        ("Steamed Rice", "Rice"),
        ("Solkadhi", "Drink/Beverage"),
        ("Chutney (Coconut/Garlic)", "Chutney/Condiment"),
        ("Curd / Raita", "Chutney/Condiment"),
        ("Shrikhand / Sweet", "Sweet/Dessert"),
        ("Puri / Chapati", "Bread/Roti"),
        ("Papad", "Other"),
        ("Pickle", "Chutney/Condiment"),
        ("Kokum Sarbat", "Drink/Beverage"),
        ("Prep - Onion Masala Base", "Prep Item"),
        ("Prep - Ginger Garlic Paste", "Prep Item"),
        ("Prep - Tadka", "Prep Item"),
        ("Prep - Chopped Vegetables", "Prep Item"),
        ("Prep - Soaked Dal", "Prep Item"),
        ("Display - Thali Counter Hot Items", "Display/Counter"),
        ("Display - Cold Items (Curd/Chutney)", "Display/Counter"),
        ("Takeaway - Packed Thali", "Takeaway"),
        ("Takeaway - Individual Items", "Takeaway"),
    ]
    for i, (name, category) in enumerate(menu_items):
        items.append({
            "name": name, "item_id": str(uuid.uuid4())[:12], "template_type": "food_items",
            "center": center, "active": True, "order": i,
            "fields": {"food_name": name, "category": category},
            "createdAt": now, "updatedAt": now,
        })

    if items:
        await db.fs_template_items.insert_many(items)

    logger.info(f"Food safety seeded {len(items)} items for {center}")
    return {"success": True, "message": f"Seeded {len(items)} template items for {center}", "seeded": len(items)}


# =======================================
# PDF REPORT GENERATION
# =======================================

@router.post("/report/pdf")
async def generate_report_pdf(data: dict):
    """Generate a PDF report for food safety records."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor
    from io import BytesIO
    from fastapi.responses import Response

    session = _check_auth(data.get("token"))
    center = data.get("center", "").upper()
    template_type = data.get("template_type", "")
    date_from = data.get("date_from", "")
    date_to = data.get("date_to", "")

    query = {}
    if center:
        query["center"] = center
    if template_type:
        query["template_type"] = template_type
    if data.get("status"):
        query["status"] = data["status"]
    if date_from or date_to:
        dq = {}
        if date_from:
            dq["$gte"] = date_from
        if date_to:
            dq["$lte"] = date_to
        query["record_date"] = dq

    records = await db.fs_records.find(query, {"_id": 0}).sort("record_date", 1).to_list(5000)

    if not records:
        raise HTTPException(404, "No records found for the given criteria")

    type_label = next((t["label"] for t in TEMPLATE_TYPES if t["key"] == template_type), template_type or "All Templates")
    columns = TEMPLATE_COLUMNS.get(template_type, [])

    pdf_buffer = BytesIO()
    page_size = landscape(A4) if len(columns) > 6 else A4
    c = canvas.Canvas(pdf_buffer, pagesize=page_size)
    w, h = page_size

    def draw_header(y_pos):
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(w / 2, y_pos, "Purnabramha - Food Safety Report")
        y_pos -= 0.2 * inch
        c.setFont("Helvetica", 9)
        period = f"{date_from or 'Start'} to {date_to or 'Now'}"
        c.drawCentredString(w / 2, y_pos, f"{type_label} | Center: {center or 'All'} | Period: {period}")
        y_pos -= 0.15 * inch
        c.drawCentredString(w / 2, y_pos, f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')} | Records: {len(records)}")
        y_pos -= 0.1 * inch
        c.setLineWidth(0.5)
        c.line(0.4 * inch, y_pos, w - 0.4 * inch, y_pos)
        return y_pos - 0.15 * inch

    y = draw_header(h - 0.4 * inch)

    for rec in records:
        entries = rec.get("entries", [])
        if not entries:
            continue

        # Record header
        if y < 1.5 * inch:
            c.showPage()
            y = draw_header(h - 0.4 * inch)

        c.setFont("Helvetica-Bold", 8)
        rec_label = f"Date: {rec.get('record_date', 'N/A')} | Status: {rec.get('status', '').upper()} | By: {rec.get('submittedBy', rec.get('createdBy', 'N/A'))}"
        c.drawString(0.5 * inch, y, rec_label)
        y -= 0.15 * inch

        # Table header
        if columns:
            col_w = (w - 1.0 * inch) / max(len(columns), 1)
            c.setFillColor(HexColor("#E2E8F0"))
            c.rect(0.4 * inch, y - 0.12 * inch, w - 0.8 * inch, 0.18 * inch, fill=1, stroke=0)
            c.setFillColor(HexColor("#000000"))
            c.setFont("Helvetica-Bold", 6)
            for ci, col in enumerate(columns):
                c.drawString(0.5 * inch + ci * col_w, y, col["label"][:16])
            y -= 0.2 * inch

            # Data rows
            c.setFont("Helvetica", 6)
            for entry in entries:
                if y < 0.6 * inch:
                    c.showPage()
                    y = draw_header(h - 0.4 * inch)
                for ci, col in enumerate(columns):
                    val = str(entry.get(col["key"], ""))[:20]
                    c.drawString(0.5 * inch + ci * col_w, y, val)
                y -= 0.14 * inch

        y -= 0.15 * inch

    # Footer
    c.setFont("Helvetica", 6)
    c.drawCentredString(w / 2, 0.3 * inch, "Purnabramha Food Safety Compliance Report | Confidential")
    c.save()
    pdf_buffer.seek(0)

    filename = f"FoodSafety_{type_label.replace(' ', '_')}_{center or 'ALL'}_{date_from or 'all'}.pdf"
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# =======================================
# EXCEL REPORT
# =======================================

@router.post("/report/excel")
async def generate_report_excel(data: dict):
    """Generate an Excel report for food safety records."""
    from openpyxl import Workbook
    from io import BytesIO
    from fastapi.responses import Response

    session = _check_auth(data.get("token"))
    center = data.get("center", "").upper()
    template_type = data.get("template_type", "")
    date_from = data.get("date_from", "")
    date_to = data.get("date_to", "")

    query = {}
    if center:
        query["center"] = center
    if template_type:
        query["template_type"] = template_type
    if data.get("status"):
        query["status"] = data["status"]
    if date_from or date_to:
        dq = {}
        if date_from:
            dq["$gte"] = date_from
        if date_to:
            dq["$lte"] = date_to
        query["record_date"] = dq

    records = await db.fs_records.find(query, {"_id": 0}).sort("record_date", 1).to_list(5000)
    if not records:
        raise HTTPException(404, "No records found")

    type_label = next((t["label"] for t in TEMPLATE_TYPES if t["key"] == template_type), "All")
    columns = TEMPLATE_COLUMNS.get(template_type, [])

    wb = Workbook()
    ws = wb.active
    ws.title = type_label[:30]

    # Header row
    headers = ["Record ID", "Date", "Status", "Submitted By", "Approved By"]
    headers += [col["label"] for col in columns]
    for ci, h in enumerate(headers, 1):
        ws.cell(row=1, column=ci, value=h)

    row = 2
    for rec in records:
        for entry in rec.get("entries", []):
            ws.cell(row=row, column=1, value=rec.get("record_id", ""))
            ws.cell(row=row, column=2, value=rec.get("record_date", ""))
            ws.cell(row=row, column=3, value=rec.get("status", ""))
            ws.cell(row=row, column=4, value=rec.get("submittedBy", rec.get("createdBy", "")))
            ws.cell(row=row, column=5, value=rec.get("approvedBy", ""))
            for ci, col in enumerate(columns):
                ws.cell(row=row, column=6 + ci, value=str(entry.get(col["key"], "")))
            row += 1

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"FoodSafety_{type_label.replace(' ', '_')}_{center or 'ALL'}.xlsx"
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
