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
        "fields": ["name", "category", "base_price", "description", "is_veg", "display_order", "serves", "center_prices"],
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


@router.get("/{master_type}")
async def get_master_items_public(master_type: str, active_only: bool = True):
    """Public GET endpoint for master dropdown data (payment modes, order types, etc.)"""
    cfg = get_master_config(master_type)
    coll = db[cfg["collection"]]
    query = {"is_active": True} if active_only else {}
    items = await coll.find(query, {"_id": 0}).sort("name", 1).to_list(5000)
    return {"items": items, "master_type": master_type, "label": cfg["label"]}



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


# ---- CENTER-SPECIFIC MENU MANAGEMENT ----

@router.post("/menu-items/set-center-price")
async def set_center_price(data: dict):
    """Set or update center-specific price for a menu item"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    
    from routes.permissions import check_permission
    if not await check_permission(session, "masters", "edit"):
        raise HTTPException(403, "No permission to edit menu pricing")
    
    item_name = data.get("item_name", "").strip()
    center_code = data.get("center_code", "").strip().upper()
    price = data.get("price")
    available = data.get("available", True)
    
    if not item_name or not center_code:
        raise HTTPException(400, "item_name and center_code required")
    
    coll = db["master_menu_items"]
    item = await coll.find_one({"name": {"$regex": f"^{item_name}$", "$options": "i"}})
    if not item:
        raise HTTPException(404, f"Menu item '{item_name}' not found")
    
    update_key = f"center_prices.{center_code}"
    await coll.update_one(
        {"name": {"$regex": f"^{item_name}$", "$options": "i"}},
        {"$set": {
            update_key: {"price": price, "available": available},
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": session.get("managerName", "")
        }}
    )
    
    return {"success": True, "message": f"Price set for {item_name} at {center_code}: {price}"}


@router.post("/menu-items/bulk-set-center-prices")
async def bulk_set_center_prices(data: dict):
    """Bulk set center-specific prices for multiple menu items"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    
    from routes.permissions import check_permission
    if not await check_permission(session, "masters", "edit"):
        raise HTTPException(403, "No permission")
    
    items = data.get("items", [])
    center_code = data.get("center_code", "").strip().upper()
    if not center_code:
        raise HTTPException(400, "center_code required")
    
    coll = db["master_menu_items"]
    updated = 0
    
    for entry in items:
        item_name = entry.get("name", "").strip()
        price = entry.get("price")
        available = entry.get("available", True)
        if not item_name:
            continue
        
        update_key = f"center_prices.{center_code}"
        result = await coll.update_one(
            {"name": {"$regex": f"^{item_name}$", "$options": "i"}},
            {"$set": {
                update_key: {"price": price, "available": available},
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": session.get("managerName", "")
            }}
        )
        if result.matched_count > 0:
            updated += 1
    
    return {"success": True, "updated": updated, "center": center_code}


@router.get("/menu-items/by-center/{center_code}")
async def get_menu_by_center(center_code: str, token: str):
    """Get menu items with center-specific pricing"""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    
    center_code = center_code.upper()
    coll = db["master_menu_items"]
    items = await coll.find({"is_active": {"$ne": False}}, {"_id": 0}).sort([("category", 1), ("display_order", 1), ("name", 1)]).to_list(5000)
    
    result = []
    for item in items:
        center_prices = item.get("center_prices", {})
        center_data = center_prices.get(center_code, {})
        
        result.append({
            "name": item.get("name"),
            "category": item.get("category"),
            "description": item.get("description", ""),
            "is_veg": item.get("is_veg", True),
            "serves": item.get("serves", ""),
            "base_price": item.get("base_price", 0),
            "center_price": center_data.get("price", item.get("base_price", 0)),
            "available": center_data.get("available", True),
            "display_order": item.get("display_order", 99),
        })
    
    # Get center currency info
    center_doc = await db.centers.find_one({"code": center_code}, {"_id": 0})
    currency = "AUD" if center_doc and not center_doc.get("is_india_center", True) else "INR"
    symbol = "$" if currency == "AUD" else "₹"
    
    return {
        "items": result,
        "center": center_code,
        "currency": currency,
        "symbol": symbol,
        "center_name": center_doc.get("name", center_code) if center_doc else center_code
    }


@router.post("/seed-menu-data")
async def seed_menu_data(data: dict):
    """Seed actual Purnabramha menu data from both India and Australia menus"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    
    from routes.permissions import check_permission
    if not await check_permission(session, "masters", "create"):
        raise HTTPException(403, "No permission")
    
    now = datetime.now(timezone.utc).isoformat()
    meta = {"created_at": now, "created_by": "Menu Seed", "updated_at": now, "updated_by": "Menu Seed", "is_active": True}
    
    # Step 1: Seed Menu Categories (actual Purnabramha categories)
    categories = [
        {"name": "BALGOPAL (KIDS)", "description": "Kids special menu", "display_order": 1, "icon": ""},
        {"name": "TEA / COFFEE", "description": "Hot beverages", "display_order": 2, "icon": ""},
        {"name": "NON TEA / DRINKS", "description": "Cold beverages and traditional drinks", "display_order": 3, "icon": ""},
        {"name": "SOUP / SAAR", "description": "Traditional soups and saars", "display_order": 4, "icon": ""},
        {"name": "SNACKS", "description": "Appetizers and snacks", "display_order": 5, "icon": ""},
        {"name": "FASTING", "description": "Fasting special items", "display_order": 6, "icon": ""},
        {"name": "HEAVY BRUNCH", "description": "Heavy breakfast items", "display_order": 7, "icon": ""},
        {"name": "BHAKAR COMBO", "description": "Combos with 2 bhakar", "display_order": 8, "icon": ""},
        {"name": "BHAJI", "description": "Vegetable dishes", "display_order": 9, "icon": ""},
        {"name": "VARAN / DAL", "description": "Lentil dishes", "display_order": 10, "icon": ""},
        {"name": "RICE", "description": "Rice preparations", "display_order": 11, "icon": ""},
        {"name": "ROTI", "description": "Bread and rotis", "display_order": 12, "icon": ""},
        {"name": "SWEET", "description": "Desserts and sweets", "display_order": 13, "icon": ""},
        {"name": "MAHARASHTRIAN THALI", "description": "Daily special thalis", "display_order": 14, "icon": ""},
        {"name": "SP. THALI", "description": "Special thalis", "display_order": 15, "icon": ""},
        {"name": "TRAVELERS MENU", "description": "Travel-friendly packed meals", "display_order": 16, "icon": ""},
        {"name": "SIDES", "description": "Side dishes, chutneys, extras", "display_order": 17, "icon": ""},
    ]
    
    cat_created = 0
    for cat in categories:
        exists = await db.master_menu_categories.find_one({"name": cat["name"]})
        if not exists:
            await db.master_menu_categories.insert_one({**meta, **cat})
            cat_created += 1
        else:
            await db.master_menu_categories.update_one({"name": cat["name"]}, {"$set": {**cat, "updated_at": now}})
    
    # Step 2: Seed Menu Items with India + Australia pricing
    # Dynamically fetch center codes from DB instead of hardcoding
    all_centers = await db.centers.find({"active": True}, {"_id": 0, "code": 1, "is_india_center": 1}).to_list(100)
    india_centers = [c["code"] for c in all_centers if c.get("is_india_center", True)]
    aus_centers = [c["code"] for c in all_centers if not c.get("is_india_center", True)]
    
    menu_items = [
        # BALGOPAL (KIDS)
        {"name": "BG Shrikhanda Puri Bhaji", "category": "BALGOPAL (KIDS)", "is_veg": True, "base_price": 219, "serves": "1", "india_price": 219, "aus_price": 15.99},
        {"name": "BG Misal Pav", "category": "BALGOPAL (KIDS)", "is_veg": True, "base_price": 189, "serves": "1", "india_price": 189, "aus_price": 12.99},
        {"name": "BG MungDal Khichadi", "category": "BALGOPAL (KIDS)", "is_veg": True, "base_price": 199, "serves": "1", "india_price": 199, "aus_price": 8.99},
        {"name": "BG Sabudana Khichadi", "category": "BALGOPAL (KIDS)", "is_veg": True, "base_price": 189, "serves": "1", "india_price": 189, "aus_price": 12.99},
        {"name": "BG Aloocha Paratha", "category": "BALGOPAL (KIDS)", "is_veg": True, "base_price": 189, "serves": "1", "india_price": 189, "aus_price": 7.99},
        {"name": "BG Vada Pav", "category": "BALGOPAL (KIDS)", "is_veg": True, "base_price": 45, "serves": "1", "india_price": 45, "aus_price": 4.99},
        {"name": "BG Sabudana Vada (4 pcs)", "category": "BALGOPAL (KIDS)", "is_veg": True, "base_price": 199, "serves": "4 pcs", "india_price": 199, "aus_price": 12.99},
        {"name": "BG Kanda Pohe", "category": "BALGOPAL (KIDS)", "is_veg": True, "base_price": 129, "serves": "1", "india_price": 129, "aus_price": 7.99},
        {"name": "BG Tedamedha Aloo", "category": "BALGOPAL (KIDS)", "is_veg": True, "base_price": 129, "serves": "1", "india_price": 129, "aus_price": 5.99},
        {"name": "Balgopal Thali", "category": "BALGOPAL (KIDS)", "is_veg": True, "base_price": 399, "serves": "1", "india_price": 399, "aus_price": 0, "aus_available": False},
        {"name": "Balgopal Varan Fal", "category": "BALGOPAL (KIDS)", "is_veg": True, "base_price": 199, "serves": "1", "india_price": 199, "aus_price": 13.99},
        {"name": "Balgopal Tup Varan Bhat", "category": "BALGOPAL (KIDS)", "is_veg": True, "base_price": 149, "serves": "1", "india_price": 149, "aus_price": 9.99},
        {"name": "Balgopal Puranpoli", "category": "BALGOPAL (KIDS)", "is_veg": True, "base_price": 149, "serves": "1", "india_price": 149, "aus_price": 9.99},
        {"name": "Balgopal Shrikhanda", "category": "BALGOPAL (KIDS)", "is_veg": True, "base_price": 149, "serves": "1", "india_price": 149, "aus_price": 9.99},
        {"name": "Balgopal Khova Poli", "category": "BALGOPAL (KIDS)", "is_veg": True, "base_price": 149, "serves": "1", "india_price": 149, "aus_price": 10.99},
        # TEA / COFFEE
        {"name": "Simple Tea", "category": "TEA / COFFEE", "is_veg": True, "base_price": 55, "serves": "1 cup", "india_price": 55, "aus_price": 0, "aus_available": False},
        {"name": "Masala Tea", "category": "TEA / COFFEE", "is_veg": True, "base_price": 65, "serves": "1 cup", "india_price": 65, "aus_price": 4.99},
        {"name": "Ginger Tea", "category": "TEA / COFFEE", "is_veg": True, "base_price": 65, "serves": "1 cup", "india_price": 65, "aus_price": 0, "aus_available": False},
        {"name": "Black Tea", "category": "TEA / COFFEE", "is_veg": True, "base_price": 65, "serves": "1 cup", "india_price": 65, "aus_price": 0, "aus_available": False},
        {"name": "Simple Milk Coffee", "category": "TEA / COFFEE", "is_veg": True, "base_price": 75, "serves": "1 cup", "india_price": 75, "aus_price": 4.99},
        {"name": "Black Coffee", "category": "TEA / COFFEE", "is_veg": True, "base_price": 50, "serves": "1 cup", "india_price": 50, "aus_price": 4.99},
        {"name": "Masala Coffee", "category": "TEA / COFFEE", "is_veg": True, "base_price": 95, "serves": "1 cup", "india_price": 95, "aus_price": 0, "aus_available": False},
        # NON TEA / DRINKS
        {"name": "Solkadhi", "category": "NON TEA / DRINKS", "is_veg": True, "base_price": 199, "serves": "1 glass", "india_price": 199, "aus_price": 11.99},
        {"name": "Piyush", "category": "NON TEA / DRINKS", "is_veg": True, "base_price": 199, "serves": "1 glass", "india_price": 199, "aus_price": 11.99},
        {"name": "Mango Piyush", "category": "NON TEA / DRINKS", "is_veg": True, "base_price": 219, "serves": "1 glass", "india_price": 219, "aus_price": 2.99},
        {"name": "Kokum", "category": "NON TEA / DRINKS", "is_veg": True, "base_price": 129, "serves": "1 glass", "india_price": 129, "aus_price": 7.99},
        {"name": "Masala Kokum", "category": "NON TEA / DRINKS", "is_veg": True, "base_price": 149, "serves": "1 glass", "india_price": 149, "aus_price": 8.99},
        {"name": "Butter Milk", "category": "NON TEA / DRINKS", "is_veg": True, "base_price": 129, "serves": "1 glass", "india_price": 129, "aus_price": 7.99},
        {"name": "Masala Butter Milk", "category": "NON TEA / DRINKS", "is_veg": True, "base_price": 149, "serves": "1 glass", "india_price": 149, "aus_price": 8.99},
        {"name": "Lime Juice", "category": "NON TEA / DRINKS", "is_veg": True, "base_price": 129, "serves": "1 glass", "india_price": 129, "aus_price": 6.99},
        {"name": "Masala Lime", "category": "NON TEA / DRINKS", "is_veg": True, "base_price": 149, "serves": "1 glass", "india_price": 149, "aus_price": 7.99},
        # SOUP / SAAR
        {"name": "Tomato Saar", "category": "SOUP / SAAR", "is_veg": True, "base_price": 229, "serves": "1 bowl", "india_price": 229, "aus_price": 0, "aus_available": False},
        {"name": "Vedik Soup", "category": "SOUP / SAAR", "is_veg": True, "base_price": 269, "serves": "1 bowl", "india_price": 269, "aus_price": 12.99},
        {"name": "Pandhara Rassa", "category": "SOUP / SAAR", "is_veg": True, "base_price": 249, "serves": "1 bowl", "india_price": 249, "aus_price": 12.99},
        {"name": "Pumpkin Soup (Sunday Only)", "category": "SOUP / SAAR", "is_veg": True, "base_price": 269, "serves": "1 bowl", "india_price": 269, "aus_price": 12.99},
        {"name": "Daal Soup", "category": "SOUP / SAAR", "is_veg": True, "base_price": 229, "serves": "1 bowl", "india_price": 229, "aus_price": 12.99},
        # SNACKS
        {"name": "Kanda Bhaji (20 pcs)", "category": "SNACKS", "is_veg": True, "base_price": 179, "serves": "20 pcs", "india_price": 179, "aus_price": 12.99},
        {"name": "Maaswadi (4 pcs)", "category": "SNACKS", "is_veg": True, "base_price": 279, "serves": "4 pcs", "india_price": 279, "aus_price": 19.99},
        {"name": "Sabudana Vada (4 pcs)", "category": "SNACKS", "is_veg": True, "base_price": 199, "serves": "4 pcs", "india_price": 199, "aus_price": 13.99},
        {"name": "Snacks Platter", "category": "SNACKS", "is_veg": True, "base_price": 599, "serves": "4-9 pcs", "india_price": 599, "aus_price": 0, "aus_available": False},
        {"name": "Batate Vada (4 pcs)", "category": "SNACKS", "is_veg": True, "base_price": 219, "serves": "4 pcs", "india_price": 219, "aus_price": 15.99},
        {"name": "Kachori (6 pcs)", "category": "SNACKS", "is_veg": True, "base_price": 239, "serves": "6 pcs", "india_price": 239, "aus_price": 16.99},
        {"name": "Vada Pav", "category": "SNACKS", "is_veg": True, "base_price": 55, "serves": "1", "india_price": 55, "aus_price": 6.99},
        {"name": "Kanda Pohe", "category": "SNACKS", "is_veg": True, "base_price": 169, "serves": "1 plate", "india_price": 169, "aus_price": 11.99},
        {"name": "Tarri Pohe", "category": "SNACKS", "is_veg": True, "base_price": 189, "serves": "1 plate", "india_price": 189, "aus_price": 13.99},
        {"name": "Dadpe Pohe", "category": "SNACKS", "is_veg": True, "base_price": 169, "serves": "1 plate", "india_price": 169, "aus_price": 0, "aus_available": False},
        {"name": "Alu Vadi (8 pcs)", "category": "SNACKS", "is_veg": True, "base_price": 239, "serves": "8 pcs", "india_price": 239, "aus_price": 17.99},
        {"name": "Pudachi Vadi (10 pcs)", "category": "SNACKS", "is_veg": True, "base_price": 239, "serves": "10 pcs", "india_price": 239, "aus_price": 17.99},
        {"name": "Kothimbir Vadi (10 pcs)", "category": "SNACKS", "is_veg": True, "base_price": 239, "serves": "10 pcs", "india_price": 239, "aus_price": 17.99},
        {"name": "Vada Sample", "category": "SNACKS", "is_veg": True, "base_price": 149, "serves": "1", "india_price": 149, "aus_price": 12.99},
        {"name": "Bread Pakoda", "category": "SNACKS", "is_veg": True, "base_price": 129, "serves": "1", "india_price": 129, "aus_price": 8.99},
        {"name": "Masala Bread Pakoda", "category": "SNACKS", "is_veg": True, "base_price": 149, "serves": "1", "india_price": 149, "aus_price": 10.99},
        {"name": "Ukad", "category": "SNACKS", "is_veg": True, "base_price": 199, "serves": "1", "india_price": 199, "aus_price": 0, "aus_available": False},
        {"name": "Mataki Bhel", "category": "SNACKS", "is_veg": True, "base_price": 169, "serves": "1", "india_price": 169, "aus_price": 12.99},
        # FASTING
        {"name": "Fasting Sabudana Vada", "category": "FASTING", "is_veg": True, "base_price": 199, "serves": "1", "india_price": 199, "aus_price": 13.99},
        {"name": "Sabudana Khichadi", "category": "FASTING", "is_veg": True, "base_price": 169, "serves": "1", "india_price": 169, "aus_price": 12.99},
        {"name": "Sabudana Thalipith", "category": "FASTING", "is_veg": True, "base_price": 199, "serves": "1", "india_price": 199, "aus_price": 14.99},
        {"name": "Upvas Thalipith", "category": "FASTING", "is_veg": True, "base_price": 199, "serves": "1", "india_price": 199, "aus_price": 14.99},
        {"name": "Rajgeera Thalipith", "category": "FASTING", "is_veg": True, "base_price": 199, "serves": "1", "india_price": 199, "aus_price": 0, "aus_available": False},
        {"name": "Fasting Thali", "category": "FASTING", "is_veg": True, "base_price": 499, "serves": "1", "india_price": 499, "aus_price": 0, "aus_available": False},
        # HEAVY BRUNCH
        {"name": "Thalipith (2 pcs)", "category": "HEAVY BRUNCH", "is_veg": True, "base_price": 199, "serves": "2 pcs", "india_price": 199, "aus_price": 8.99},
        {"name": "Ghavan (3 pcs)", "category": "HEAVY BRUNCH", "is_veg": True, "base_price": 199, "serves": "3 pcs", "india_price": 199, "aus_price": 0, "aus_available": False},
        {"name": "Dhirde (3 pcs)", "category": "HEAVY BRUNCH", "is_veg": True, "base_price": 199, "serves": "3 pcs", "india_price": 199, "aus_price": 0, "aus_available": False},
        {"name": "Misal Pav", "category": "HEAVY BRUNCH", "is_veg": True, "base_price": 199, "serves": "1", "india_price": 199, "aus_price": 14.99},
        {"name": "Ukarpendi", "category": "HEAVY BRUNCH", "is_veg": True, "base_price": 149, "serves": "1", "india_price": 149, "aus_price": 0, "aus_available": False},
        {"name": "Masala Varan Fal", "category": "HEAVY BRUNCH", "is_veg": True, "base_price": 349, "serves": "1", "india_price": 349, "aus_price": 0, "aus_available": False},
        {"name": "Shrikhanada Puri Bhaji", "category": "HEAVY BRUNCH", "is_veg": True, "base_price": 249, "serves": "1", "india_price": 249, "aus_price": 17.99},
        {"name": "Aloocha Paratha", "category": "HEAVY BRUNCH", "is_veg": True, "base_price": 149, "serves": "1 pc", "india_price": 149, "aus_price": 7.99},
        {"name": "Varan Fal", "category": "HEAVY BRUNCH", "is_veg": True, "base_price": 299, "serves": "1", "india_price": 299, "aus_price": 20.99},
        {"name": "Puri Bhaji", "category": "HEAVY BRUNCH", "is_veg": True, "base_price": 199, "serves": "1", "india_price": 199, "aus_price": 13.99},
        {"name": "Shengole", "category": "HEAVY BRUNCH", "is_veg": True, "base_price": 299, "serves": "1", "india_price": 299, "aus_price": 20.99},
        # BHAKAR COMBO
        {"name": "Shev Bhaji Combo", "category": "BHAKAR COMBO", "is_veg": True, "base_price": 349, "serves": "with 2 bhakar", "india_price": 349, "aus_price": 20.99},
        {"name": "Patodi Rassa Combo", "category": "BHAKAR COMBO", "is_veg": True, "base_price": 349, "serves": "with 2 bhakar", "india_price": 349, "aus_price": 20.99},
        {"name": "Maaswadi Rassa Combo", "category": "BHAKAR COMBO", "is_veg": True, "base_price": 349, "serves": "with 2 bhakar", "india_price": 349, "aus_price": 20.99},
        {"name": "Vangyacha Bharit Combo (Saturday)", "category": "BHAKAR COMBO", "is_veg": True, "base_price": 349, "serves": "with 2 bhakar", "india_price": 349, "aus_price": 20.99},
        {"name": "Ravan Pithala Combo", "category": "BHAKAR COMBO", "is_veg": True, "base_price": 349, "serves": "with 2 bhakar", "india_price": 349, "aus_price": 19.99},
        {"name": "Pithala Yellow Combo", "category": "BHAKAR COMBO", "is_veg": True, "base_price": 319, "serves": "with 2 bhakar", "india_price": 319, "aus_price": 19.99},
        {"name": "Zhunka Combo", "category": "BHAKAR COMBO", "is_veg": True, "base_price": 319, "serves": "with 2 bhakar", "india_price": 319, "aus_price": 19.99},
        {"name": "Kaju Curry Combo", "category": "BHAKAR COMBO", "is_veg": True, "base_price": 349, "serves": "with 2 bhakar", "india_price": 349, "aus_price": 21.99},
        # BHAJI
        {"name": "Ravan Pithala", "category": "BHAJI", "is_veg": True, "base_price": 379, "serves": "1", "india_price": 379, "aus_price": 20.99},
        {"name": "Pithala (Yellow)", "category": "BHAJI", "is_veg": True, "base_price": 379, "serves": "1", "india_price": 379, "aus_price": 20.99},
        {"name": "Bharit (Saturdays)", "category": "BHAJI", "is_veg": True, "base_price": 379, "serves": "1", "india_price": 379, "aus_price": 23.99},
        {"name": "Dal Vanga", "category": "BHAJI", "is_veg": True, "base_price": 389, "serves": "1", "india_price": 389, "aus_price": 0, "aus_available": False},
        {"name": "Mix Cauliflower Bhaji", "category": "BHAJI", "is_veg": True, "base_price": 389, "serves": "1", "india_price": 389, "aus_price": 0, "aus_available": False},
        {"name": "Chef Special Bhaji", "category": "BHAJI", "is_veg": True, "base_price": 389, "serves": "1", "india_price": 389, "aus_price": 23.99},
        {"name": "Shev Bhaji", "category": "BHAJI", "is_veg": True, "base_price": 379, "serves": "1", "india_price": 379, "aus_price": 23.99},
        {"name": "Patodi Rassa", "category": "BHAJI", "is_veg": True, "base_price": 399, "serves": "1", "india_price": 399, "aus_price": 24.99},
        {"name": "Maaswadi Rassa", "category": "BHAJI", "is_veg": True, "base_price": 399, "serves": "1", "india_price": 399, "aus_price": 24.99},
        {"name": "Patal Bhaji (Sundays)", "category": "BHAJI", "is_veg": True, "base_price": 379, "serves": "1", "india_price": 379, "aus_price": 23.99},
        {"name": "Bharli Vangi", "category": "BHAJI", "is_veg": True, "base_price": 349, "serves": "1", "india_price": 349, "aus_price": 24.99},
        {"name": "Zhunka", "category": "BHAJI", "is_veg": True, "base_price": 289, "serves": "1", "india_price": 289, "aus_price": 20.99},
        {"name": "Kaju Curry", "category": "BHAJI", "is_veg": True, "base_price": 479, "serves": "1", "india_price": 479, "aus_price": 26.99},
        {"name": "Akkha Masur", "category": "BHAJI", "is_veg": True, "base_price": 379, "serves": "1", "india_price": 379, "aus_price": 22.99},
        {"name": "Kadhi Gole", "category": "BHAJI", "is_veg": True, "base_price": 349, "serves": "1", "india_price": 349, "aus_price": 20.99},
        {"name": "Dry / Jeera Aloo", "category": "BHAJI", "is_veg": True, "base_price": 249, "serves": "1", "india_price": 249, "aus_price": 17.99},
        {"name": "Matki Usal", "category": "BHAJI", "is_veg": True, "base_price": 299, "serves": "1", "india_price": 299, "aus_price": 20.99},
        # VARAN / DAL
        {"name": "Mataki Amti", "category": "VARAN / DAL", "is_veg": True, "base_price": 249, "serves": "1 bowl", "india_price": 249, "aus_price": 15.99},
        {"name": "Lasun Varan", "category": "VARAN / DAL", "is_veg": True, "base_price": 249, "serves": "1 bowl", "india_price": 249, "aus_price": 14.99},
        {"name": "Sadha Varan", "category": "VARAN / DAL", "is_veg": True, "base_price": 199, "serves": "1 bowl", "india_price": 199, "aus_price": 13.99},
        {"name": "Takachi Kadhi", "category": "VARAN / DAL", "is_veg": True, "base_price": 199, "serves": "1 bowl", "india_price": 199, "aus_price": 13.99},
        {"name": "Kataachi Amti", "category": "VARAN / DAL", "is_veg": True, "base_price": 249, "serves": "1 bowl", "india_price": 249, "aus_price": 15.99},
        {"name": "Jeera Varan", "category": "VARAN / DAL", "is_veg": True, "base_price": 249, "serves": "1 bowl", "india_price": 249, "aus_price": 14.99},
        {"name": "Chef Special Dal", "category": "VARAN / DAL", "is_veg": True, "base_price": 289, "serves": "1 bowl", "india_price": 289, "aus_price": 17.99},
        # RICE
        {"name": "Steam Rice", "category": "RICE", "is_veg": True, "base_price": 199, "serves": "1 plate", "india_price": 199, "aus_price": 9.99},
        {"name": "Dahi Bhat", "category": "RICE", "is_veg": True, "base_price": 219, "serves": "1 plate", "india_price": 219, "aus_price": 11.99},
        {"name": "Kanda Rice", "category": "RICE", "is_veg": True, "base_price": 219, "serves": "1 plate", "india_price": 219, "aus_price": 11.99},
        {"name": "Tup Bhat", "category": "RICE", "is_veg": True, "base_price": 249, "serves": "1 plate", "india_price": 249, "aus_price": 17.99},
        {"name": "Bhaji Bhat", "category": "RICE", "is_veg": True, "base_price": 249, "serves": "1 plate", "india_price": 249, "aus_price": 17.99},
        {"name": "Gola Bhat", "category": "RICE", "is_veg": True, "base_price": 249, "serves": "1 plate", "india_price": 249, "aus_price": 17.99},
        {"name": "Masale Bhat", "category": "RICE", "is_veg": True, "base_price": 299, "serves": "1 plate", "india_price": 299, "aus_price": 17.99},
        {"name": "Tup Varan Bhat", "category": "RICE", "is_veg": True, "base_price": 249, "serves": "1 plate", "india_price": 249, "aus_price": 15.99},
        {"name": "Rice Platter", "category": "RICE", "is_veg": True, "base_price": 399, "serves": "1 platter", "india_price": 399, "aus_price": 0, "aus_available": False},
        # ROTI
        {"name": "Fulka", "category": "ROTI", "is_veg": True, "base_price": 29, "serves": "1 pc", "india_price": 29, "aus_price": 2.99},
        {"name": "Dupodi Poli", "category": "ROTI", "is_veg": True, "base_price": 32, "serves": "1 pc", "india_price": 32, "aus_price": 3.99},
        {"name": "Jowar Bhakar", "category": "ROTI", "is_veg": True, "base_price": 59, "serves": "1 pc", "india_price": 59, "aus_price": 4.99},
        {"name": "Rice Bhakar", "category": "ROTI", "is_veg": True, "base_price": 59, "serves": "1 pc", "india_price": 59, "aus_price": 4.99},
        {"name": "Wade (2 pcs)", "category": "ROTI", "is_veg": True, "base_price": 79, "serves": "2 pcs", "india_price": 79, "aus_price": 0, "aus_available": False},
        {"name": "Puri Set (5 pcs)", "category": "ROTI", "is_veg": True, "base_price": 99, "serves": "5 pcs", "india_price": 99, "aus_price": 8.99},
        # SWEET
        {"name": "Modak", "category": "SWEET", "is_veg": True, "base_price": 249, "serves": "1 plate", "india_price": 249, "aus_price": 18.99},
        {"name": "Shrikhanda", "category": "SWEET", "is_veg": True, "base_price": 199, "serves": "1 bowl", "india_price": 199, "aus_price": 12.99},
        {"name": "Shirvale", "category": "SWEET", "is_veg": True, "base_price": 389, "serves": "1 plate", "india_price": 389, "aus_price": 14.99},
        {"name": "Puranpoli", "category": "SWEET", "is_veg": True, "base_price": 119, "serves": "1 pc", "india_price": 119, "aus_price": 10.99},
        {"name": "Khava Poli", "category": "SWEET", "is_veg": True, "base_price": 119, "serves": "1 pc", "india_price": 119, "aus_price": 10.99},
        {"name": "Sheera (Rava)", "category": "SWEET", "is_veg": True, "base_price": 199, "serves": "1 bowl", "india_price": 199, "aus_price": 13.99},
        {"name": "Basundi", "category": "SWEET", "is_veg": True, "base_price": 199, "serves": "1 bowl", "india_price": 199, "aus_price": 14.99},
        {"name": "Amrakhanda", "category": "SWEET", "is_veg": True, "base_price": 219, "serves": "1 bowl", "india_price": 219, "aus_price": 13.99},
        {"name": "Aamras (Seasonal)", "category": "SWEET", "is_veg": True, "base_price": 210, "serves": "1 bowl", "india_price": 210, "aus_price": 11.99},
        # THALIS
        {"name": "Shree Shiv Thali (Monday)", "category": "MAHARASHTRIAN THALI", "is_veg": True, "base_price": 499, "serves": "1 thali", "india_price": 499, "aus_price": 35.99},
        {"name": "Shree Swami Samrath Thali (Tuesday)", "category": "MAHARASHTRIAN THALI", "is_veg": True, "base_price": 499, "serves": "1 thali", "india_price": 499, "aus_price": 35.99},
        {"name": "Shree Vithayee Thali (Wednesday)", "category": "MAHARASHTRIAN THALI", "is_veg": True, "base_price": 499, "serves": "1 thali", "india_price": 499, "aus_price": 35.99},
        {"name": "Shree Duttaguru Thali (Thursday)", "category": "MAHARASHTRIAN THALI", "is_veg": True, "base_price": 499, "serves": "1 thali", "india_price": 499, "aus_price": 35.99},
        {"name": "Shree Balaji Thali (Friday)", "category": "MAHARASHTRIAN THALI", "is_veg": True, "base_price": 549, "serves": "1 thali", "india_price": 549, "aus_price": 35.99},
        {"name": "Shree Gajanan Maharaj Thali (Saturday)", "category": "MAHARASHTRIAN THALI", "is_veg": True, "base_price": 549, "serves": "1 thali", "india_price": 549, "aus_price": 35.99},
        {"name": "Shree Mahalakshmi Thali (Sunday)", "category": "MAHARASHTRIAN THALI", "is_veg": True, "base_price": 549, "serves": "1 thali", "india_price": 549, "aus_price": 35.99},
        # SP. THALI
        {"name": "Varhadi Thali", "category": "SP. THALI", "is_veg": True, "base_price": 549, "serves": "1 thali", "india_price": 549, "aus_price": 0, "aus_available": False},
        {"name": "Misal Thali", "category": "SP. THALI", "is_veg": True, "base_price": 449, "serves": "1 thali", "india_price": 449, "aus_price": 29.99},
        {"name": "Vidharbha Thali", "category": "SP. THALI", "is_veg": True, "base_price": 549, "serves": "1 thali", "india_price": 549, "aus_price": 39.99},
        {"name": "Purankut Thali", "category": "SP. THALI", "is_veg": True, "base_price": 549, "serves": "1 thali", "india_price": 549, "aus_price": 39.99},
        {"name": "Shravan Maas Thali", "category": "SP. THALI", "is_veg": True, "base_price": 549, "serves": "1 thali", "india_price": 549, "aus_price": 39.99},
        {"name": "Meva Thali", "category": "SP. THALI", "is_veg": True, "base_price": 749, "serves": "1 thali", "india_price": 749, "aus_price": 0, "aus_available": False},
        # SIDES (Australia-specific section)
        {"name": "Day Sp. Koshimbeer", "category": "SIDES", "is_veg": True, "base_price": 0, "serves": "1", "india_price": 0, "india_available": False, "aus_price": 4.99},
        {"name": "Green Salad", "category": "SIDES", "is_veg": True, "base_price": 0, "serves": "1", "india_price": 0, "india_available": False, "aus_price": 4.99},
        {"name": "Thecha", "category": "SIDES", "is_veg": True, "base_price": 0, "serves": "1", "india_price": 0, "india_available": False, "aus_price": 1.99},
        {"name": "Curd", "category": "SIDES", "is_veg": True, "base_price": 0, "serves": "1", "india_price": 0, "india_available": False, "aus_price": 2.99},
        {"name": "Papad (2 pcs)", "category": "SIDES", "is_veg": True, "base_price": 0, "serves": "2 pcs", "india_price": 0, "india_available": False, "aus_price": 1.99},
        {"name": "Lasun Chutney", "category": "SIDES", "is_veg": True, "base_price": 0, "serves": "1", "india_price": 0, "india_available": False, "aus_price": 3.99},
    ]
    
    item_created = 0
    item_updated = 0
    coll = db["master_menu_items"]
    
    for item in menu_items:
        name = item["name"]
        india_price = item.get("india_price", item.get("base_price", 0))
        aus_price = item.get("aus_price", 0)
        india_available = item.get("india_available", True)
        aus_available = item.get("aus_available", True)
        
        # Build center_prices
        center_prices = {}
        for ic in india_centers:
            center_prices[ic] = {"price": india_price, "available": india_available}
        for ac in aus_centers:
            center_prices[ac] = {"price": aus_price, "available": aus_available}
        
        doc = {
            "name": name,
            "category": item["category"],
            "description": item.get("description", ""),
            "is_veg": item.get("is_veg", True),
            "base_price": item.get("base_price", 0),
            "serves": item.get("serves", ""),
            "center_prices": center_prices,
            "display_order": item.get("display_order", 99),
            "is_active": True,
            "updated_at": now,
            "updated_by": "Menu Seed",
        }
        
        existing = await coll.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
        if existing:
            await coll.update_one({"name": {"$regex": f"^{name}$", "$options": "i"}}, {"$set": doc})
            item_updated += 1
        else:
            doc["created_at"] = now
            doc["created_by"] = "Menu Seed"
            await coll.insert_one(doc)
            item_created += 1
    
    return {
        "success": True,
        "categories_created": cat_created,
        "items_created": item_created,
        "items_updated": item_updated,
        "total_items": len(menu_items)
    }
