# =======================================
# Restaurant Billing / POS Routes
# Full POS, KOT, Invoice, Cancellation
# =======================================

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import logging
import io

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["Billing & POS"])

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


# =======================================
# BILLING CONFIGURATION
# =======================================

DEFAULT_CONFIGS = {
    "India": {
        "country": "India",
        "gst_percentage": 5,
        "gst_type": "exclusive",
        "service_charge_enabled": False,
        "service_charge_type": "percentage",
        "service_charge_value": 0,
        "currency_symbol": "\u20b9",
        "currency_code": "INR"
    },
    "Australia": {
        "country": "Australia",
        "gst_percentage": 10,
        "gst_type": "inclusive",
        "service_charge_enabled": False,
        "service_charge_type": "percentage",
        "service_charge_value": 0,
        "currency_symbol": "$",
        "currency_code": "AUD"
    }
}


@router.post("/config/get")
async def get_billing_config(data: dict):
    token = data.get("token")
    center = data.get("center")
    session = await check_access(token)

    center_doc = await db.centers.find_one({"code": center}, {"_id": 0})
    if not center_doc:
        raise HTTPException(404, f"Center {center} not found")

    is_india = center_doc.get("is_india_center", True)
    country = "India" if is_india else (center_doc.get("country") or "Australia")

    config = await db.billing_config.find_one({"country": country}, {"_id": 0})
    if not config:
        config = DEFAULT_CONFIGS.get(country, DEFAULT_CONFIGS["India"])

    return {"config": config, "center": center, "country": country}


@router.post("/config/save")
async def save_billing_config(data: dict):
    token = data.get("token")
    session = await check_access(token)
    if not session.get("is_super_admin") and not session.get("is_admin"):
        raise HTTPException(403, "Admin access required")

    country = data.get("country")
    if not country:
        raise HTTPException(400, "Country is required")

    update = {
        "country": country,
        "gst_percentage": float(data.get("gst_percentage", 5)),
        "gst_type": data.get("gst_type", "exclusive"),
        "service_charge_enabled": data.get("service_charge_enabled", False),
        "service_charge_type": data.get("service_charge_type", "percentage"),
        "service_charge_value": float(data.get("service_charge_value", 0)),
        "currency_symbol": data.get("currency_symbol", "\u20b9"),
        "currency_code": data.get("currency_code", "INR"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": session.get("name", "")
    }

    await db.billing_config.update_one(
        {"country": country}, {"$set": update}, upsert=True
    )
    return {"success": True, "config": update}


# =======================================
# MENU ITEMS FOR POS
# =======================================

@router.post("/menu")
async def get_pos_menu(data: dict):
    token = data.get("token")
    center = data.get("center")
    session = await check_access(token)

    items = await db.master_menu_items.find(
        {"is_active": True}, {"_id": 0}
    ).to_list(1000)

    menu = []
    for item in items:
        cp = item.get("center_prices", {}).get(center, {})
        if not cp.get("available", False):
            continue
        price = cp.get("price", item.get("base_price", 0))
        menu.append({
            "name": item["name"],
            "category": item.get("category", "Other"),
            "price": float(price),
            "is_veg": item.get("is_veg", True),
            "serves": item.get("serves", "1"),
        })

    categories = await db.master_menu_categories.find(
        {}, {"_id": 0}
    ).sort("display_order", 1).to_list(100)

    return {
        "items": menu,
        "categories": [c["name"] for c in categories],
        "total": len(menu)
    }


# =======================================
# ORDER MANAGEMENT
# =======================================

async def _next_sequence(center: str, prefix: str) -> str:
    today = datetime.now().strftime("%Y%m%d")
    key = f"{prefix}-{center}-{today}"
    doc = await db.sequences.find_one_and_update(
        {"_id": key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    seq = doc["seq"]
    return f"{prefix}-{center}-{today}-{seq:03d}"


@router.post("/order/create")
async def create_order(data: dict):
    token = data.get("token")
    center = data.get("center")
    table_no = data.get("table_no", "")
    order_type = data.get("order_type", "Dine-In")
    guest_count = data.get("guest_count", 0)
    customer_name = data.get("customer_name", "")
    customer_phone = data.get("customer_phone", "")
    table_id = data.get("table_id", "")
    session = await check_access(token)

    # Validate based on order type
    if order_type == "Dine-In":
        if not table_no and not table_id:
            raise HTTPException(400, "Table selection is mandatory for Dine-In orders")
        if not guest_count or int(guest_count) < 1:
            raise HTTPException(400, "Guest count is mandatory for Dine-In orders")
    elif order_type in ("Takeaway", "Delivery"):
        if not customer_name or not customer_name.strip():
            raise HTTPException(400, "Customer name is mandatory for Takeaway/Delivery orders")
        if not customer_phone or not customer_phone.strip():
            raise HTTPException(400, "Customer phone is mandatory for Takeaway/Delivery orders")

    # If table_id provided, mark table as occupied
    if table_id:
        await db.billing_tables.update_one(
            {"table_id": table_id},
            {"$set": {"status": "occupied", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

    order_id = await _next_sequence(center, "ORD")

    order = {
        "order_id": order_id,
        "center": center,
        "table_no": table_no,
        "table_id": table_id,
        "order_type": order_type,
        "guest_count": int(guest_count) if guest_count else 0,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "items": [],
        "status": "active",
        "kot_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": session.get("name", ""),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    await db.orders.insert_one(order)
    order.pop("_id", None)
    return {"success": True, "order": order}


@router.post("/order/add-items")
async def add_items_to_order(data: dict):
    token = data.get("token")
    order_id = data.get("order_id")
    items = data.get("items", [])
    session = await check_access(token)

    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")
    if order["status"] not in ("active", "kot_printed"):
        raise HTTPException(400, f"Cannot modify order in '{order['status']}' status")

    new_items = []
    for item in items:
        new_items.append({
            "item_name": item["item_name"],
            "category": item.get("category", ""),
            "qty": int(item.get("qty", 1)),
            "unit_price": float(item.get("unit_price", 0)),
            "total": float(item.get("unit_price", 0)) * int(item.get("qty", 1)),
            "notes": item.get("notes", ""),
            "is_veg": item.get("is_veg", True),
            "kot_printed": False,
            "added_at": datetime.now(timezone.utc).isoformat()
        })

    await db.orders.update_one(
        {"order_id": order_id},
        {
            "$push": {"items": {"$each": new_items}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )

    updated = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    return {"success": True, "order": updated}


@router.post("/order/update-item-qty")
async def update_item_qty(data: dict):
    token = data.get("token")
    order_id = data.get("order_id")
    item_index = data.get("item_index")
    new_qty = int(data.get("qty", 1))
    session = await check_access(token)

    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")
    if order["status"] not in ("active", "kot_printed"):
        raise HTTPException(400, "Cannot modify this order")

    items = order.get("items", [])
    if item_index < 0 or item_index >= len(items):
        raise HTTPException(400, "Invalid item index")

    if new_qty <= 0:
        items.pop(item_index)
    else:
        items[item_index]["qty"] = new_qty
        items[item_index]["total"] = items[item_index]["unit_price"] * new_qty

    await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {"items": items, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    updated = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    return {"success": True, "order": updated}


@router.post("/order/cancel")
async def cancel_order(data: dict):
    token = data.get("token")
    order_id = data.get("order_id")
    reason_id = data.get("reason_id", "")
    reason = data.get("reason", "")
    session = await check_access(token)

    if not reason_id and not reason:
        raise HTTPException(400, "Cancellation reason is mandatory")

    # If reason_id provided, validate it exists in master
    reason_text = reason
    if reason_id:
        master_reason = await db.billing_cancel_reasons.find_one(
            {"reason_id": reason_id}, {"_id": 0}
        )
        if master_reason:
            reason_text = master_reason.get("reason", reason)

    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")
    if order["status"] == "billed":
        raise HTTPException(400, "Cannot cancel a billed order. Use void instead.")

    # Free up the table if Dine-In
    if order.get("table_id"):
        await db.billing_tables.update_one(
            {"table_id": order["table_id"]},
            {"$set": {"status": "available", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

    cancel_audit = {
        "action": "order_cancel",
        "order_id": order_id,
        "center": order.get("center", ""),
        "reason_id": reason_id,
        "reason": reason_text,
        "cancelled_by": session.get("name", ""),
        "cancelled_by_role": session.get("role_key", ""),
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
        "order_items": order.get("items", []),
        "order_total": sum(i.get("total", 0) for i in order.get("items", []))
    }

    await db.billing_audit_trail.insert_one(cancel_audit)
    cancel_audit.pop("_id", None)

    await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {
            "status": "cancelled",
            "cancel_reason_id": reason_id,
            "cancel_reason": reason_text,
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
            "cancelled_by": session.get("name", ""),
            "cancelled_by_role": session.get("role_key", ""),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    return {"success": True, "message": "Order cancelled"}


@router.post("/order/get")
async def get_order(data: dict):
    token = data.get("token")
    order_id = data.get("order_id")
    session = await check_access(token)

    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")
    return {"order": order}


@router.post("/orders/active")
async def get_active_orders(data: dict):
    token = data.get("token")
    center = data.get("center")
    session = await check_access(token)

    orders = await db.orders.find(
        {"center": center, "status": {"$in": ["active", "kot_printed"]}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(200)

    return {"orders": orders, "count": len(orders)}


# =======================================
# KOT - KITCHEN ORDER TICKET
# =======================================

@router.post("/kot/generate")
async def generate_kot(data: dict):
    token = data.get("token")
    order_id = data.get("order_id")
    session = await check_access(token)

    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")

    # Get items not yet sent to kitchen
    new_items = [i for i in order.get("items", []) if not i.get("kot_printed")]
    if not new_items:
        raise HTTPException(400, "No new items to send to kitchen")

    kot_no = await _next_sequence(order["center"], "KOT")

    kot = {
        "kot_no": kot_no,
        "order_id": order_id,
        "center": order["center"],
        "table_no": order.get("table_no", ""),
        "order_type": order.get("order_type", "Dine-In"),
        "items": [{"item_name": i["item_name"], "qty": i["qty"], "notes": i.get("notes", ""), "is_veg": i.get("is_veg", True)} for i in new_items],
        "printed_at": datetime.now(timezone.utc).isoformat(),
        "printed_by": session.get("name", "")
    }

    await db.kot_entries.insert_one(kot)
    kot.pop("_id", None)

    # Mark items as kot_printed
    items = order.get("items", [])
    for i in items:
        if not i.get("kot_printed"):
            i["kot_printed"] = True
            i["kot_no"] = kot_no

    await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {
            "items": items,
            "status": "kot_printed",
            "kot_count": order.get("kot_count", 0) + 1,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    return {"success": True, "kot": kot}


@router.post("/kot/print")
async def get_kot_print_data(data: dict):
    """Return KOT data formatted for thermal printer (80mm)."""
    token = data.get("token")
    kot_no = data.get("kot_no")
    session = await check_access(token)

    kot = await db.kot_entries.find_one({"kot_no": kot_no}, {"_id": 0})
    if not kot:
        raise HTTPException(404, "KOT not found")

    return {"kot": kot}


@router.post("/kot/cancel")
async def cancel_kot(data: dict):
    """Cancel a KOT with mandatory reason from master."""
    token = data.get("token")
    kot_no = data.get("kot_no")
    reason_id = data.get("reason_id", "")
    reason = data.get("reason", "")
    session = await check_access(token)

    if not reason_id and not reason:
        raise HTTPException(400, "Cancellation reason is mandatory")

    reason_text = reason
    if reason_id:
        master_reason = await db.billing_cancel_reasons.find_one(
            {"reason_id": reason_id}, {"_id": 0}
        )
        if master_reason:
            reason_text = master_reason.get("reason", reason)

    kot = await db.kot_entries.find_one({"kot_no": kot_no}, {"_id": 0})
    if not kot:
        raise HTTPException(404, "KOT not found")

    cancel_audit = {
        "action": "kot_cancel",
        "kot_no": kot_no,
        "order_id": kot.get("order_id", ""),
        "center": kot.get("center", ""),
        "reason_id": reason_id,
        "reason": reason_text,
        "cancelled_by": session.get("name", ""),
        "cancelled_by_role": session.get("role_key", ""),
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
        "kot_items": kot.get("items", [])
    }

    await db.billing_audit_trail.insert_one(cancel_audit)
    cancel_audit.pop("_id", None)

    await db.kot_entries.update_one(
        {"kot_no": kot_no},
        {"$set": {
            "status": "cancelled",
            "cancel_reason_id": reason_id,
            "cancel_reason": reason_text,
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
            "cancelled_by": session.get("name", "")
        }}
    )

    return {"success": True, "message": "KOT cancelled"}




# =======================================
# BILL GENERATION
# =======================================

def _calculate_bill(items, gst_pct, gst_type, sc_enabled, sc_type, sc_value,
                    disc_type, disc_value):
    """Calculate bill totals with GST (inclusive/exclusive), service charge, discount."""
    item_total = sum(i["total"] for i in items)

    # GST calculation
    if gst_type == "inclusive":
        # Price already includes GST, extract it
        base_amount = round(item_total / (1 + gst_pct / 100), 2)
        gst_amount = round(item_total - base_amount, 2)
        subtotal = base_amount
    else:
        # Exclusive: add GST on top
        subtotal = item_total
        gst_amount = round(subtotal * gst_pct / 100, 2)

    # Service charge (on subtotal before GST)
    service_charge_amount = 0
    if sc_enabled and sc_value > 0:
        if sc_type == "percentage":
            service_charge_amount = round(subtotal * sc_value / 100, 2)
        else:
            service_charge_amount = round(sc_value, 2)

    # Pre-discount total
    pre_discount = subtotal + gst_amount + service_charge_amount

    # Discount
    discount_amount = 0
    if disc_value and disc_value > 0:
        if disc_type == "percentage":
            discount_amount = round(pre_discount * disc_value / 100, 2)
        else:
            discount_amount = round(disc_value, 2)

    grand_total = round(pre_discount - discount_amount, 2)

    return {
        "item_total": round(item_total, 2),
        "subtotal": round(subtotal, 2),
        "gst_percentage": gst_pct,
        "gst_type": gst_type,
        "gst_amount": gst_amount,
        "service_charge_enabled": sc_enabled,
        "service_charge_type": sc_type,
        "service_charge_value": sc_value,
        "service_charge_amount": service_charge_amount,
        "discount_type": disc_type or "none",
        "discount_value": disc_value or 0,
        "discount_amount": discount_amount,
        "grand_total": grand_total
    }


@router.post("/bill/preview")
async def preview_bill(data: dict):
    """Preview bill calculation without saving."""
    token = data.get("token")
    order_id = data.get("order_id")
    center = data.get("center")
    disc_type = data.get("discount_type", "none")
    disc_value = float(data.get("discount_value", 0))
    session = await check_access(token)

    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")

    # Get billing config
    center_doc = await db.centers.find_one({"code": center or order["center"]}, {"_id": 0})
    is_india = center_doc.get("is_india_center", True) if center_doc else True
    country = "India" if is_india else (center_doc.get("country") or "Australia")

    config = await db.billing_config.find_one({"country": country}, {"_id": 0})
    if not config:
        config = DEFAULT_CONFIGS.get(country, DEFAULT_CONFIGS["India"])

    calc = _calculate_bill(
        order["items"],
        config["gst_percentage"],
        config["gst_type"],
        config.get("service_charge_enabled", False),
        config.get("service_charge_type", "percentage"),
        config.get("service_charge_value", 0),
        disc_type, disc_value
    )

    return {
        "order": order,
        "calculation": calc,
        "config": config
    }


@router.post("/bill/generate")
async def generate_bill(data: dict):
    token = data.get("token")
    order_id = data.get("order_id")
    payment_mode = data.get("payment_mode", "Cash")
    disc_type = data.get("discount_type", "none")
    disc_value = float(data.get("discount_value", 0))
    customer_name = data.get("customer_name", "")
    customer_phone = data.get("customer_phone", "")
    session = await check_access(token)

    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")
    if order["status"] == "billed":
        raise HTTPException(400, "Order already billed")
    if order["status"] == "cancelled":
        raise HTTPException(400, "Cannot bill a cancelled order")
    if not order.get("items"):
        raise HTTPException(400, "No items in order")

    center = order["center"]
    center_doc = await db.centers.find_one({"code": center}, {"_id": 0})
    is_india = center_doc.get("is_india_center", True) if center_doc else True
    country = "India" if is_india else (center_doc.get("country") or "Australia")

    config = await db.billing_config.find_one({"country": country}, {"_id": 0})
    if not config:
        config = DEFAULT_CONFIGS.get(country, DEFAULT_CONFIGS["India"])

    calc = _calculate_bill(
        order["items"],
        config["gst_percentage"],
        config["gst_type"],
        config.get("service_charge_enabled", False),
        config.get("service_charge_type", "percentage"),
        config.get("service_charge_value", 0),
        disc_type, disc_value
    )

    bill_no = await _next_sequence(center, "BILL")

    bill = {
        "bill_no": bill_no,
        "order_id": order_id,
        "center": center,
        "table_no": order.get("table_no", ""),
        "order_type": order.get("order_type", "Dine-In"),
        "items": order["items"],
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "payment_mode": payment_mode,
        "status": "paid",
        **calc,
        "currency_symbol": config.get("currency_symbol", "\u20b9"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": session.get("name", ""),
        "date": datetime.now().strftime("%Y-%m-%d")
    }

    await db.bills.insert_one(bill)
    bill.pop("_id", None)

    # Mark order as billed
    await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {
            "status": "billed",
            "bill_no": bill_no,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    # Free up the table after billing
    if order.get("table_id"):
        await db.billing_tables.update_one(
            {"table_id": order["table_id"]},
            {"$set": {"status": "available", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

    return {"success": True, "bill": bill}


@router.post("/bill/void")
async def void_bill(data: dict):
    token = data.get("token")
    bill_no = data.get("bill_no")
    reason_id = data.get("reason_id", "")
    reason = data.get("reason", "")
    session = await check_access(token)

    if not session.get("is_super_admin") and not session.get("is_admin"):
        raise HTTPException(403, "Only Admin can void bills")

    if not reason_id and not reason:
        raise HTTPException(400, "Cancellation reason is mandatory for voiding bills")

    # Validate reason from master
    reason_text = reason
    if reason_id:
        master_reason = await db.billing_cancel_reasons.find_one(
            {"reason_id": reason_id}, {"_id": 0}
        )
        if master_reason:
            reason_text = master_reason.get("reason", reason)

    bill = await db.bills.find_one({"bill_no": bill_no}, {"_id": 0})
    if not bill:
        raise HTTPException(404, "Bill not found")
    if bill["status"] == "void":
        raise HTTPException(400, "Bill already voided")

    void_audit = {
        "action": "bill_void",
        "bill_no": bill_no,
        "order_id": bill.get("order_id", ""),
        "center": bill.get("center", ""),
        "reason_id": reason_id,
        "reason": reason_text,
        "voided_by": session.get("name", ""),
        "voided_by_role": session.get("role_key", ""),
        "voided_at": datetime.now(timezone.utc).isoformat(),
        "bill_total": bill.get("grand_total", 0),
        "payment_mode": bill.get("payment_mode", "")
    }

    await db.billing_audit_trail.insert_one(void_audit)
    void_audit.pop("_id", None)

    await db.bills.update_one(
        {"bill_no": bill_no},
        {"$set": {
            "status": "void",
            "void_reason_id": reason_id,
            "void_reason": reason_text,
            "voided_at": datetime.now(timezone.utc).isoformat(),
            "voided_by": session.get("name", ""),
            "voided_by_role": session.get("role_key", "")
        }}
    )

    # Revert order status and free table
    order = await db.orders.find_one({"order_id": bill["order_id"]}, {"_id": 0})
    await db.orders.update_one(
        {"order_id": bill["order_id"]},
        {"$set": {"status": "void", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    # Free up the table
    if order and order.get("table_id"):
        await db.billing_tables.update_one(
            {"table_id": order["table_id"]},
            {"$set": {"status": "available", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

    return {"success": True, "message": "Bill voided"}


# =======================================
# BILLS LISTING & REPORTS
# =======================================

@router.post("/bills/list")
async def list_bills(data: dict):
    token = data.get("token")
    center = data.get("center")
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    session = await check_access(token)

    query = {"center": center, "date": date}
    bills = await db.bills.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)

    total_sales = sum(b["grand_total"] for b in bills if b["status"] == "paid")
    total_bills = len([b for b in bills if b["status"] == "paid"])
    void_count = len([b for b in bills if b["status"] == "void"])

    # Payment mode breakdown
    by_payment = {}
    for b in bills:
        if b["status"] != "paid":
            continue
        mode = b.get("payment_mode", "Cash")
        by_payment[mode] = by_payment.get(mode, 0) + b["grand_total"]

    return {
        "bills": bills,
        "summary": {
            "total_sales": round(total_sales, 2),
            "total_bills": total_bills,
            "void_count": void_count,
            "by_payment": by_payment
        }
    }


@router.post("/bills/daily-report")
async def daily_report(data: dict):
    token = data.get("token")
    center = data.get("center")
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    session = await check_access(token)

    bills = await db.bills.find(
        {"center": center, "date": date, "status": "paid"}, {"_id": 0}
    ).to_list(500)

    # Item-wise breakdown
    item_sales = {}
    for b in bills:
        for item in b.get("items", []):
            name = item["item_name"]
            if name not in item_sales:
                item_sales[name] = {"item_name": name, "qty": 0, "total": 0, "category": item.get("category", "")}
            item_sales[name]["qty"] += item["qty"]
            item_sales[name]["total"] += item["total"]

    items_list = sorted(item_sales.values(), key=lambda x: x["total"], reverse=True)

    # Category-wise
    cat_sales = {}
    for i in items_list:
        cat = i["category"] or "Other"
        cat_sales[cat] = cat_sales.get(cat, 0) + i["total"]

    total_revenue = sum(b["grand_total"] for b in bills)
    total_gst = sum(b["gst_amount"] for b in bills)
    total_sc = sum(b.get("service_charge_amount", 0) for b in bills)
    total_discount = sum(b.get("discount_amount", 0) for b in bills)

    return {
        "date": date,
        "center": center,
        "total_bills": len(bills),
        "total_revenue": round(total_revenue, 2),
        "total_gst": round(total_gst, 2),
        "total_service_charge": round(total_sc, 2),
        "total_discount": round(total_discount, 2),
        "item_wise": items_list,
        "category_wise": [{"category": k, "total": round(v, 2)} for k, v in sorted(cat_sales.items(), key=lambda x: x[1], reverse=True)],
        "by_payment": {},
    }


@router.post("/bill/get")
async def get_bill(data: dict):
    token = data.get("token")
    bill_no = data.get("bill_no")
    session = await check_access(token)

    bill = await db.bills.find_one({"bill_no": bill_no}, {"_id": 0})
    if not bill:
        raise HTTPException(404, "Bill not found")
    return {"bill": bill}
