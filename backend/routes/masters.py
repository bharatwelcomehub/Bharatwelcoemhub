# =======================================
# MASTER DATA MANAGEMENT - GENERIC CRUD
# All dropdowns, filters, reports pull from these masters
# =======================================

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import logging

router = APIRouter(prefix="/api/masters", tags=["Master Data"])
logger = logging.getLogger(__name__)

db = None
verify_token = None

def set_db(database):
    global db
    db = database

def set_verify_token(vt):
    global verify_token
    verify_token = vt

# ---- Master Type Registry ----
# Maps master type key -> MongoDB collection name + metadata
MASTER_REGISTRY = {
    "expense_categories": {
        "collection": "master_expense_categories",
        "label": "Expense Category",
        "fields": ["name", "description", "code"],
        "unique_key": "name"
    },
    "payment_modes": {
        "collection": "master_payment_modes",
        "label": "Payment Mode",
        "fields": ["name", "description", "code"],
        "unique_key": "name"
    },
    "employee_categories": {
        "collection": "master_employee_categories",
        "label": "Employee Category",
        "fields": ["name", "description", "department"],
        "unique_key": "name"
    },
    "tax_config": {
        "collection": "master_tax",
        "label": "Tax Configuration",
        "fields": ["name", "rate", "description", "applies_to"],
        "unique_key": "name"
    },
    "menu_categories": {
        "collection": "master_menu_categories",
        "label": "Menu Category",
        "fields": ["name", "description", "display_order", "icon"],
        "unique_key": "name"
    },
    "menu_items": {
        "collection": "master_menu_items",
        "label": "Menu Item",
        "fields": ["name", "category", "price", "description", "is_veg", "display_order"],
        "unique_key": "name"
    },
    "tables": {
        "collection": "master_tables",
        "label": "Table",
        "fields": ["name", "center", "capacity", "section", "floor"],
        "unique_key": "name"
    },
    "order_types": {
        "collection": "master_order_types",
        "label": "Order Type",
        "fields": ["name", "description", "code"],
        "unique_key": "name"
    },
    "vendors": {
        "collection": "master_vendors",
        "label": "Vendor",
        "fields": ["name", "contact", "phone", "email", "address", "gst_number", "category"],
        "unique_key": "name"
    },
    "cancellation_reasons": {
        "collection": "master_cancellation_reasons",
        "label": "Cancellation Reason",
        "fields": ["name", "description", "requires_approval"],
        "unique_key": "name"
    },
    "franchises": {
        "collection": "master_franchises",
        "label": "Franchise",
        "fields": ["name", "owner_name", "owner_email", "owner_phone", "center", "agreement_date", "royalty_percent", "address", "city", "state", "documents"],
        "unique_key": "name"
    },
    "licenses": {
        "collection": "master_licenses",
        "label": "License / Document Type",
        "fields": ["name", "description", "validity_months", "reminder_days"],
        "unique_key": "name"
    },
    "sales_channels": {
        "collection": "master_sales_channels",
        "label": "Sales Channel",
        "fields": ["name", "description", "code"],
        "unique_key": "name"
    },
    "discount_types": {
        "collection": "master_discount_types",
        "label": "Discount Type",
        "fields": ["name", "description", "max_percent", "requires_approval"],
        "unique_key": "name"
    },
}


def get_master_config(master_type: str):
    if master_type not in MASTER_REGISTRY:
        raise HTTPException(400, f"Unknown master type: {master_type}. Valid: {list(MASTER_REGISTRY.keys())}")
    return MASTER_REGISTRY[master_type]


# ---- GENERIC CRUD ENDPOINTS ----

@router.get("/types")
async def list_master_types(token: str):
    """List all available master types"""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    
    result = []
    for key, cfg in MASTER_REGISTRY.items():
        coll = db[cfg["collection"]]
        count = await coll.count_documents({})
        active = await coll.count_documents({"is_active": True})
        result.append({
            "key": key,
            "label": cfg["label"],
            "fields": cfg["fields"],
            "total_count": count,
            "active_count": active
        })
    return {"master_types": result}


@router.post("/{master_type}/list")
async def list_master_items(master_type: str, data: dict):
    """Get all items from a master table"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    
    cfg = get_master_config(master_type)
    coll = db[cfg["collection"]]
    
    query = {}
    if data.get("active_only"):
        query["is_active"] = True
    if data.get("center"):
        query["center"] = data["center"]
    
    items = await coll.find(query, {"_id": 0}).sort("name", 1).to_list(5000)
    return {"items": items, "master_type": master_type, "label": cfg["label"]}


@router.post("/{master_type}/create")
async def create_master_item(master_type: str, data: dict):
    """Create a new master item"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    
    # Check permission
    from routes.permissions import check_permission
    if not await check_permission(session, "masters", "create"):
        raise HTTPException(403, "No permission to create master data")
    
    cfg = get_master_config(master_type)
    coll = db[cfg["collection"]]
    
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(400, "Name is required")
    
    # Check uniqueness
    existing = await coll.find_one({cfg["unique_key"]: {"$regex": f"^{name}$", "$options": "i"}})
    if existing:
        raise HTTPException(400, f"{cfg['label']} '{name}' already exists")
    
    doc = {
        "is_active": data.get("is_active", True),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": session.get("managerName", ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": session.get("managerName", ""),
    }
    
    # Copy allowed fields
    for field in cfg["fields"]:
        if field in data and data[field] is not None:
            doc[field] = data[field]
    
    await coll.insert_one(doc)
    logger.info(f"Master {master_type} created: {name} by {session.get('managerName')}")
    return {"success": True, "message": f"{cfg['label']} '{name}' created"}


@router.post("/{master_type}/update")
async def update_master_item(master_type: str, data: dict):
    """Update a master item"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    
    from routes.permissions import check_permission
    if not await check_permission(session, "masters", "edit"):
        raise HTTPException(403, "No permission to edit master data")
    
    cfg = get_master_config(master_type)
    coll = db[cfg["collection"]]
    
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(400, "Name (identifier) is required")
    
    update = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": session.get("managerName", ""),
    }
    
    for field in cfg["fields"]:
        if field in data and data[field] is not None:
            update[field] = data[field]
    
    if "is_active" in data:
        update["is_active"] = data["is_active"]
    
    result = await coll.update_one(
        {cfg["unique_key"]: {"$regex": f"^{name}$", "$options": "i"}},
        {"$set": update}
    )
    
    if result.matched_count == 0:
        raise HTTPException(404, f"{cfg['label']} '{name}' not found")
    
    return {"success": True, "message": f"{cfg['label']} '{name}' updated"}


@router.post("/{master_type}/delete")
async def delete_master_item(master_type: str, data: dict):
    """Soft-delete (deactivate) a master item"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    
    from routes.permissions import check_permission
    if not await check_permission(session, "masters", "delete"):
        raise HTTPException(403, "No permission to delete master data")
    
    cfg = get_master_config(master_type)
    coll = db[cfg["collection"]]
    
    name = data.get("name", "").strip()
    hard_delete = data.get("hard_delete", False)
    
    if hard_delete:
        result = await coll.delete_one({cfg["unique_key"]: {"$regex": f"^{name}$", "$options": "i"}})
        if result.deleted_count == 0:
            raise HTTPException(404, f"{cfg['label']} '{name}' not found")
        return {"success": True, "message": f"{cfg['label']} '{name}' permanently deleted"}
    else:
        result = await coll.update_one(
            {cfg["unique_key"]: {"$regex": f"^{name}$", "$options": "i"}},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": session.get("managerName", "")}}
        )
        if result.matched_count == 0:
            raise HTTPException(404, f"{cfg['label']} '{name}' not found")
        return {"success": True, "message": f"{cfg['label']} '{name}' deactivated"}


# ---- BULK OPERATIONS ----

@router.post("/{master_type}/bulk-create")
async def bulk_create(master_type: str, data: dict):
    """Bulk create master items (for seeding/import)"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    
    from routes.permissions import check_permission
    if not await check_permission(session, "masters", "create"):
        raise HTTPException(403, "No permission")
    
    cfg = get_master_config(master_type)
    coll = db[cfg["collection"]]
    items = data.get("items", [])
    
    created = 0
    skipped = 0
    now = datetime.now(timezone.utc).isoformat()
    
    for item in items:
        name = item.get("name", "").strip()
        if not name:
            skipped += 1
            continue
        
        existing = await coll.find_one({cfg["unique_key"]: {"$regex": f"^{name}$", "$options": "i"}})
        if existing:
            skipped += 1
            continue
        
        doc = {
            "is_active": item.get("is_active", True),
            "created_at": now,
            "created_by": session.get("managerName", "System"),
            "updated_at": now,
            "updated_by": session.get("managerName", "System"),
        }
        for field in cfg["fields"]:
            if field in item:
                doc[field] = item[field]
        
        await coll.insert_one(doc)
        created += 1
    
    return {"success": True, "created": created, "skipped": skipped}


# ---- SEED MASTERS FROM EXISTING DATA ----

@router.post("/seed-from-existing")
async def seed_masters_from_existing(data: dict):
    """Migrate existing hardcoded values into master tables. Safe - won't overwrite."""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    
    from routes.permissions import check_permission
    if not await check_permission(session, "masters", "create"):
        raise HTTPException(403, "No permission")
    
    now = datetime.now(timezone.utc).isoformat()
    meta = {"created_at": now, "created_by": "System Migration", "updated_at": now, "updated_by": "System Migration", "is_active": True}
    results = {}
    
    # 1. Expense Categories - from expense_heads collection
    expense_heads = await db.expense_heads.find({}, {"_id": 0}).to_list(500)
    c = 0
    for h in expense_heads:
        name = h.get("name", "").strip()
        if not name:
            continue
        exists = await db.master_expense_categories.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
        if not exists:
            await db.master_expense_categories.insert_one({**meta, "name": name, "description": h.get("description", ""), "code": ""})
            c += 1
    results["expense_categories"] = c
    
    # 2. Payment Modes
    modes = ["CASH", "UPI", "BANK TRANSFER", "NEFT", "RTGS", "CARD", "CHEQUE", "ONLINE"]
    c = 0
    for m in modes:
        exists = await db.master_payment_modes.find_one({"name": m})
        if not exists:
            await db.master_payment_modes.insert_one({**meta, "name": m, "description": "", "code": m[:4]})
            c += 1
    results["payment_modes"] = c
    
    # 3. Employee Categories - from distinct designations
    designations = await db.employees.distinct("designation")
    c = 0
    for d in designations:
        if not d or not d.strip():
            continue
        d = d.strip().upper()
        exists = await db.master_employee_categories.find_one({"name": {"$regex": f"^{d}$", "$options": "i"}})
        if not exists:
            await db.master_employee_categories.insert_one({**meta, "name": d, "description": "", "department": ""})
            c += 1
    results["employee_categories"] = c
    
    # 4. Tax Config
    taxes = [
        {"name": "GST 5%", "rate": 5.0, "description": "GST on restaurant food", "applies_to": "food"},
        {"name": "GST 18%", "rate": 18.0, "description": "GST on services", "applies_to": "services"},
        {"name": "No Tax", "rate": 0, "description": "Exempt items", "applies_to": "exempt"},
    ]
    c = 0
    for t in taxes:
        exists = await db.master_tax.find_one({"name": t["name"]})
        if not exists:
            await db.master_tax.insert_one({**meta, **t})
            c += 1
    results["tax_config"] = c
    
    # 5. Order Types
    order_types = [
        {"name": "DINE-IN", "description": "Dine-in customers", "code": "DI"},
        {"name": "TAKEAWAY", "description": "Takeaway orders", "code": "TA"},
        {"name": "DELIVERY", "description": "Delivery orders", "code": "DL"},
        {"name": "CATERING", "description": "Catering events", "code": "CT"},
    ]
    c = 0
    for o in order_types:
        exists = await db.master_order_types.find_one({"name": o["name"]})
        if not exists:
            await db.master_order_types.insert_one({**meta, **o})
            c += 1
    results["order_types"] = c
    
    # 6. Cancellation Reasons
    cancel_reasons = [
        {"name": "CUSTOMER REQUEST", "description": "Customer cancelled", "requires_approval": False},
        {"name": "WRONG ORDER", "description": "Wrong item ordered", "requires_approval": False},
        {"name": "QUALITY ISSUE", "description": "Food quality concern", "requires_approval": True},
        {"name": "LONG WAIT", "description": "Customer left due to wait", "requires_approval": False},
        {"name": "DUPLICATE ORDER", "description": "Duplicate entry", "requires_approval": False},
        {"name": "OTHER", "description": "Other reason (specify in notes)", "requires_approval": True},
    ]
    c = 0
    for r in cancel_reasons:
        exists = await db.master_cancellation_reasons.find_one({"name": r["name"]})
        if not exists:
            await db.master_cancellation_reasons.insert_one({**meta, **r})
            c += 1
    results["cancellation_reasons"] = c
    
    # 7. Sales Channels
    channels = [
        {"name": "DINE-IN", "code": "DI", "description": "In-restaurant dining"},
        {"name": "SWIGGY", "code": "SW", "description": "Swiggy delivery"},
        {"name": "ZOMATO", "code": "ZM", "description": "Zomato delivery"},
        {"name": "DIRECT DELIVERY", "code": "DD", "description": "Direct delivery"},
        {"name": "TAKEAWAY", "code": "TA", "description": "Walk-in takeaway"},
        {"name": "CATERING", "code": "CT", "description": "Catering orders"},
    ]
    c = 0
    for ch in channels:
        exists = await db.master_sales_channels.find_one({"name": ch["name"]})
        if not exists:
            await db.master_sales_channels.insert_one({**meta, **ch})
            c += 1
    results["sales_channels"] = c
    
    # 8. License/Document Types
    licenses = [
        {"name": "FSSAI License", "description": "Food Safety License", "validity_months": 60, "reminder_days": 90},
        {"name": "Trade License", "description": "Municipal trade license", "validity_months": 12, "reminder_days": 30},
        {"name": "GST Certificate", "description": "GST registration", "validity_months": 0, "reminder_days": 0},
        {"name": "Fire NOC", "description": "Fire safety certificate", "validity_months": 12, "reminder_days": 30},
        {"name": "Health License", "description": "Health department license", "validity_months": 12, "reminder_days": 30},
        {"name": "Franchise Agreement", "description": "Franchise agreement document", "validity_months": 0, "reminder_days": 90},
    ]
    c = 0
    for lic in licenses:
        exists = await db.master_licenses.find_one({"name": lic["name"]})
        if not exists:
            await db.master_licenses.insert_one({**meta, **lic})
            c += 1
    results["licenses"] = c
    
    # 9. Discount Types
    discounts = [
        {"name": "NO DISCOUNT", "description": "No discount applied", "max_percent": 0, "requires_approval": False},
        {"name": "STAFF DISCOUNT", "description": "Staff meal discount", "max_percent": 50, "requires_approval": False},
        {"name": "LOYALTY DISCOUNT", "description": "Regular customer discount", "max_percent": 15, "requires_approval": False},
        {"name": "COMPLIMENTARY", "description": "Full complimentary", "max_percent": 100, "requires_approval": True},
        {"name": "MANAGER DISCOUNT", "description": "Manager-approved discount", "max_percent": 25, "requires_approval": True},
    ]
    c = 0
    for d in discounts:
        exists = await db.master_discount_types.find_one({"name": d["name"]})
        if not exists:
            await db.master_discount_types.insert_one({**meta, **d})
            c += 1
    results["discount_types"] = c
    
    # 10. Menu Categories (basic defaults)
    menu_cats = [
        {"name": "STARTERS", "description": "Appetizers and starters", "display_order": 1, "icon": ""},
        {"name": "MAIN COURSE", "description": "Main course dishes", "display_order": 2, "icon": ""},
        {"name": "RICE & BIRYANI", "description": "Rice and biryani items", "display_order": 3, "icon": ""},
        {"name": "BREADS", "description": "Roti, naan, paratha", "display_order": 4, "icon": ""},
        {"name": "BEVERAGES", "description": "Drinks and beverages", "display_order": 5, "icon": ""},
        {"name": "DESSERTS", "description": "Sweet dishes and desserts", "display_order": 6, "icon": ""},
        {"name": "THALI", "description": "Full thali combos", "display_order": 7, "icon": ""},
    ]
    c = 0
    for mc in menu_cats:
        exists = await db.master_menu_categories.find_one({"name": mc["name"]})
        if not exists:
            await db.master_menu_categories.insert_one({**meta, **mc})
            c += 1
    results["menu_categories"] = c
    
    # 11. Franchises - from existing franchises collection
    existing_franchises = await db.franchises.find({}, {"_id": 0}).to_list(100)
    c = 0
    for f in existing_franchises:
        name = f.get("franchiseName", f.get("name", "")).strip()
        if not name:
            continue
        exists = await db.master_franchises.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
        if not exists:
            await db.master_franchises.insert_one({
                **meta,
                "name": name,
                "owner_name": f.get("ownerName", ""),
                "owner_email": f.get("ownerEmail", ""),
                "owner_phone": f.get("ownerPhone", ""),
                "center": f.get("center", ""),
                "agreement_date": f.get("agreementDate", ""),
                "royalty_percent": f.get("royaltyPercent", 0),
                "address": f.get("address", ""),
                "city": f.get("city", ""),
                "state": f.get("state", ""),
                "documents": f.get("documents", []),
            })
            c += 1
    results["franchises"] = c
    
    return {"success": True, "migrated": results}
