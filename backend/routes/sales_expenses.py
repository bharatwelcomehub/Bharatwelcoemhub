# =======================================
# Sales & Expenses Routes
# Daily Sales and Cash Summary Management
# =======================================

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sales", tags=["Sales & Expenses"])


# ---------------------------------------------------------------------------
# Payment-mode normaliser (used by bulk-upload of expenses)
# ---------------------------------------------------------------------------
# System master modes the UI / reports work with: CASH, BANK TRANSFER, CARD,
# NEFT, ONLINE, RTGS, UPI.  Excel files in the wild use a wide variety of
# free-text labels — this helper maps them into one of the 7 canonical values.
def _normalize_payment_mode(raw: str) -> str:
    if raw is None:
        return "CASH"
    v = " ".join(str(raw).strip().split()).upper()
    if not v:
        return "CASH"
    # UPI variants (incl. common "UIP" typo) — must be checked BEFORE NEFT/ONLINE
    if "UPI" in v or "UIP" in v:
        return "UPI"
    if "CARD" in v or v in ("DEBIT", "CREDIT"):
        return "CARD"
    if "RTGS" in v:
        return "RTGS"
    # Anything tagged "ONLINE …" (incl. ONLINE NEFT / IMPS, ONLINE/IMPS, etc.)
    # collapses to canonical ONLINE per business rule.
    if v.startswith("ONLINE") or "IMPS" in v:
        return "ONLINE"
    if "NEFT" in v:
        return "NEFT"
    if "BANK" in v:
        return "BANK TRANSFER"
    if v == "CASH":
        return "CASH"
    # Unknown / unmapped — preserve the user's text in upper-case instead of
    # silently defaulting to CASH.
    return v


# Get DB reference (will be set from main server)
db = None

def set_db(database):
    global db
    db = database

# =======================================
# PYDANTIC MODELS
# =======================================

class DailySaleCreate(BaseModel):
    center: str
    date: str  # YYYY-MM-DD
    opening_balance: float = 0
    petty_cash_opening: float = 0
    deposited_in_bank: float = 0
    cash_receipts: float = 0  # Cash Receipts / Withdrawal from bank
    
    # Sales breakdown
    sale_pbm: float = 0  # PBM products
    sale_other: float = 0  # Other products
    total_sale: float = 0
    
    # Online/Card payments - Non-cash channels
    card_idfc: float = 0       # Credit/Debit Card
    bharat_pay: float = 0      # Bharat Pay / UPI
    swiggy: float = 0          # Swiggy
    zomato: float = 0          # Zomato
    doordash: float = 0        # Doordash (NEW)
    online_other: float = 0    # Other online/Takeaway/Pickups
    due_amount: float = 0      # Due Amount
    total_online_sale: float = 0
    total_cash_sale: float = 0
    
    # Guest & Bill tracking
    num_guests: int = 0  # Number of guests (pax)
    num_bills: int = 0   # Number of bills (excluding Swiggy/Zomato)
    avg_per_pax: float = 0  # Average per guest
    avg_per_bill: float = 0  # Average per bill
    
    # GST Calculation
    gst_amount: float = 0  # Calculated GST amount
    
    # Expenses and closing
    cash_expense: float = 0
    closing_balance: float = 0
    to_deposit_in_bank: float = 0
    difference_for_day: float = 0
    petty_cash_closing: float = 0
    
    notes: Optional[str] = ""

class DailySaleUpdate(BaseModel):
    opening_balance: Optional[float] = None
    petty_cash_opening: Optional[float] = None
    deposited_in_bank: Optional[float] = None
    cash_receipts: Optional[float] = None  # Cash Receipts / Withdrawal
    sale_pbm: Optional[float] = None
    sale_other: Optional[float] = None
    total_sale: Optional[float] = None
    card_idfc: Optional[float] = None
    bharat_pay: Optional[float] = None
    swiggy: Optional[float] = None
    zomato: Optional[float] = None
    doordash: Optional[float] = None  # NEW
    online_other: Optional[float] = None
    due_amount: Optional[float] = None
    total_online_sale: Optional[float] = None
    total_cash_sale: Optional[float] = None
    # Guest & Bill tracking
    num_guests: Optional[int] = None
    num_bills: Optional[int] = None
    avg_per_pax: Optional[float] = None
    avg_per_bill: Optional[float] = None
    # GST
    gst_amount: Optional[float] = None
    cash_expense: Optional[float] = None
    closing_balance: Optional[float] = None
    to_deposit_in_bank: Optional[float] = None
    difference_for_day: Optional[float] = None
    petty_cash_closing: Optional[float] = None
    notes: Optional[str] = None

# =======================================
# UNLOCK REQUEST MODELS
# =======================================

class UnlockRequest(BaseModel):
    center: str
    date: str  # YYYY-MM-DD
    reason: str

class UnlockRequestAction(BaseModel):
    action: str  # "approve" or "reject"
    admin_notes: Optional[str] = None

class ExpenseCreate(BaseModel):
    center: str
    date: str  # YYYY-MM-DD
    description: str
    amount: float
    expense_type: str  # Category
    payment_mode: str  # CASH, ONLINE UPI, ONLINE NEFT/IMPS
    notes: Optional[str] = ""
    # GST / ITC tagging (India centers). Amount is tax-INCLUSIVE.
    # gst_rate one of 0, 5, 12, 18, 28. gst_amount auto-derived if not provided.
    gst_rate: Optional[float] = 0
    gst_amount: Optional[float] = 0
    # NEW: GST Paid as printed on the bill (simple manual entry, no calc). The
    # canonical "Total Expense" displayed/reported is amount + gst_paid.
    gst_paid: Optional[float] = 0
    vendor_name: Optional[str] = ""
    vendor_gstin: Optional[str] = ""

class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    expense_type: Optional[str] = None
    payment_mode: Optional[str] = None
    notes: Optional[str] = None
    gst_rate: Optional[float] = None
    gst_amount: Optional[float] = None
    gst_paid: Optional[float] = None
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None

class TokenRequest(BaseModel):
    token: str

class SalesQueryRequest(BaseModel):
    token: str
    center: Optional[str] = None  # None = all centers
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    month: Optional[str] = None  # YYYY-MM format

class ExpenseQueryRequest(BaseModel):
    token: str
    center: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    month: Optional[str] = None
    expense_type: Optional[str] = None

# Import verify_token from main server (will be set)
verify_token = None
verify_token_async_func = None

def set_verify_token(func):
    global verify_token
    verify_token = func

def set_verify_token_async(func):
    global verify_token_async_func
    verify_token_async_func = func

async def get_session(token: str):
    """Get session using async verification (with MongoDB fallback)"""
    if verify_token_async_func:
        session = await verify_token_async_func(token)
        if session:
            return session
    return verify_token(token)

def has_all_centers_access(session):
    """Check if user has access to view all centers data"""
    if not session:
        return False
    # Super Admin always has access
    if session.get("is_super_admin"):
        return True
    # Admin has access
    if session.get("is_admin"):
        return True
    # Check view_all_centers role specifically assigned
    roles = session.get("roles", {})
    if roles.get("view_all_centers"):
        return True
    # NEW: Accounting role has access to ALL centers
    if roles.get("accounting"):
        return True
    return False

def has_sales_access(session):
    """Check if user has access to sales & cash features"""
    if not session:
        return False
    if session.get("is_super_admin"):
        return True
    # NEW: Accounting role has full sales_cash access
    roles = session.get("roles", {})
    if roles.get("accounting"):
        return True
    return roles.get("sales_cash", False)

def has_accounting_role(session):
    """Check if user has the accounting role (can view ALL centers)"""
    if not session:
        return False
    if session.get("is_super_admin"):
        return True
    roles = session.get("roles", {})
    return roles.get("accounting", False)

# =======================================
# GST & CURRENCY HELPERS
# =======================================

def is_perth_center(center: str) -> bool:
    """Check if center is international (non-India) — uses cached center data"""
    if not center:
        return False
    c = center.upper()
    # Use cached international centers list
    return c in _international_centers_cache

# Cache of international center codes - populated on first API call
_international_centers_cache = set()

async def refresh_international_centers_cache(db_ref):
    """Refresh cache of international center codes from DB"""
    global _international_centers_cache
    centers = await db_ref.centers.find({"is_india_center": False}, {"_id": 0, "code": 1}).to_list(100)
    _international_centers_cache = {c["code"].upper() for c in centers if c.get("code")}

def get_currency_symbol(center: str) -> str:
    """Get currency symbol based on center"""
    return "$" if is_perth_center(center) else "₹"

def calculate_gst(total_sale: float, swiggy: float, zomato: float, center: str, doordash: float = 0) -> dict:
    """
    Calculate GST using shared utility (single source of truth).
        Eligible = Total − Swiggy − Zomato − DoorDash
        GST = Eligible − Eligible / (1 + rate)   [INCLUSIVE]
        rate = 5% India, 10% Perth/Australia
    """
    from utils.gst import compute_gst_from_totals, gst_rate_for
    aggregator = float(swiggy or 0) + float(zomato or 0) + float(doordash or 0)
    calc = compute_gst_from_totals(total_sale, aggregator, country=None, center=center)
    return {
        "gst_rate": int(calc["rate"] * 100),
        "gst_amount": calc["gst_amount"],
        "net_sale": calc["eligible_base"],
        "is_inclusive": True,
        "currency": get_currency_symbol(center)
    }

# =======================================
# HELPER FUNCTIONS
# =======================================

def calculate_totals(sale: dict) -> dict:
    """
    Calculate derived fields for a sale record.
    
    TWO SEPARATE TRACKS:
    
    Track A — To Deposit (Opening/Closing Balance):
      Cash Sale = Total Sale - Total Online Sale
      Closing Balance = Opening Balance + Cash Sale - Deposited in Bank
      To Deposit = Closing Balance
      Next day Opening = Today's Closing
    
    Track B — Petty Cash:
      Petty Cash Closing = Petty Cash Opening + Cash Withdrawal (Cash Receipts) - Cash Expenses
      Next day Petty Opening = Today's Petty Closing
    
    These two tracks are INDEPENDENT and do not mix.
    """
    # Total sale = PBM + Other (or use direct total_sale if provided)
    if sale.get("total_sale", 0) == 0:
        sale["total_sale"] = sale.get("sale_pbm", 0) + sale.get("sale_other", 0)
    
    # Get values
    total_sale = sale.get("total_sale", 0)
    card_idfc = sale.get("card_idfc", 0)
    bharat_pay = sale.get("bharat_pay", 0)
    swiggy = sale.get("swiggy", 0)
    zomato = sale.get("zomato", 0)
    doordash = sale.get("doordash", 0)
    online_other = sale.get("online_other", 0)
    
    opening_balance = sale.get("opening_balance", 0)
    cash_receipts = sale.get("cash_receipts", 0)  # Cash withdrawal from bank (for petty cash track)
    cash_expense = sale.get("cash_expense", 0)
    petty_opening = sale.get("petty_cash_opening", 0)
    deposited_in_bank = sale.get("deposited_in_bank", 0)
    
    # Total Online Sale = Card + UPI + Swiggy + Zomato + Doordash + Other
    sale["total_online_sale"] = card_idfc + bharat_pay + swiggy + zomato + doordash + online_other
    
    # Cash Sale = Total Sale - Total Online Sale
    sale["total_cash_sale"] = max(0, total_sale - sale["total_online_sale"])
    
    # TRACK A: To Deposit
    # Closing Balance = Opening Balance + Cash Sale - Deposited in Bank
    sale["closing_balance"] = opening_balance + sale["total_cash_sale"] - deposited_in_bank
    sale["to_deposit_in_bank"] = sale["closing_balance"]
    
    # TRACK B: Petty Cash
    # Petty Cash Closing = Petty Cash Opening + Cash Withdrawal (Cash Receipts) - Cash Expenses
    sale["petty_cash_closing"] = petty_opening + cash_receipts - cash_expense
    
    return sale

# =======================================
# FREEZE/LOCK HELPER FUNCTIONS
# =======================================

def is_date_frozen(date_str: str) -> bool:
    """
    Check if a date is frozen (locked).
    Previous day and older dates are frozen at midnight.
    Only today's date is editable.
    """
    from datetime import date
    try:
        record_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = date.today()
        return record_date < today
    except:
        return True  # If date is invalid, consider it frozen

async def is_date_unlocked(center: str, date_str: str, record_type: str = None) -> bool:
    """
    Check if a frozen date has been temporarily unlocked by Super Admin.
    Returns True if unlocked, False if still frozen.
    
    record_type: "sales", "expenses", or None (any type)
    """
    query = {
        "center": center.upper(),
        "date": date_str,
        "status": "active",
        "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
    }
    
    # If type specified, check for that specific type
    if record_type:
        query["type"] = record_type
    
    unlock = await db.unlock_grants.find_one(query)
    return unlock is not None

async def is_date_unlocked_for_expenses(center: str, date_str: str) -> bool:
    """Check if date is unlocked specifically for expenses"""
    return await is_date_unlocked(center, date_str, "expenses")

async def is_date_unlocked_for_sales(center: str, date_str: str) -> bool:
    """Check if date is unlocked specifically for sales"""
    return await is_date_unlocked(center, date_str, "sales")

async def is_admin_frozen(center: str, date_str: str) -> bool:
    """
    Check if a date has been manually frozen by Super Admin.
    Admin freezes apply to EVERYONE including Super Admins until explicitly unfrozen.
    """
    # Check for center-specific admin freeze
    center_freeze = await db.admin_freezes.find_one({
        "center": center.upper(),
        "date": date_str,
        "type": "admin_freeze"
    })
    if center_freeze:
        return True
    
    # Check for "ALL" centers admin freeze
    all_freeze = await db.admin_freezes.find_one({
        "center": "ALL",
        "date": date_str,
        "type": "admin_freeze"
    })
    return all_freeze is not None

async def can_edit_date(session: dict, center: str, date_str: str, record_type: str = None) -> tuple:
    """
    Check if user can edit a specific date's data.
    Returns (can_edit: bool, reason: str)
    
    record_type: "sales", "expenses", or None (checks any type)
    
    Priority:
    1. Admin freeze (highest priority - blocks everyone including Super Admin)
    2. Super Admin bypass (if no admin freeze)
    3. Unlock grants (type-specific if record_type provided)
    4. Default freeze for past dates
    """
    # FIRST: Check for admin freeze - this blocks EVERYONE including Super Admin
    if await is_admin_frozen(center, date_str):
        # Even admin freeze can be bypassed if there's an active unlock grant
        if await is_date_unlocked(center, date_str, record_type):
            return (True, "Admin frozen but temporarily unlocked")
        return (False, "Date is ADMIN FROZEN. Use Freeze Control to unfreeze first.")
    
    # Super Admin can edit if no admin freeze
    if session.get("is_super_admin"):
        return (True, "Super Admin access")
    
    # Check if date is frozen (past dates are automatically frozen)
    if not is_date_frozen(date_str):
        return (True, "Date is not frozen (today)")
    
    # Date is frozen - check if unlocked for this center (and type if specified)
    if await is_date_unlocked(center, date_str, record_type):
        return (True, "Date temporarily unlocked by Super Admin")
    
    return (False, "Date is frozen. Request unlock from Super Admin.")

async def update_petty_cash_for_expense(center: str, date: str, amount: float, is_add: bool = True):
    """
    Update cash_expense, petty_cash_closing, closing_balance, and to_deposit_in_bank
    in daily_sales when a CASH expense is added/removed.
    Uses calculate_totals() to ensure all derived fields stay consistent.
    """
    daily_record = await db.daily_sales.find_one({"center": center, "date": date})
    
    if daily_record:
        current_cash_expense = daily_record.get("cash_expense", 0)
        
        if is_add:
            new_cash_expense = current_cash_expense + amount
        else:
            new_cash_expense = max(0, current_cash_expense - amount)
        
        # Update cash_expense and recalculate ALL derived fields consistently
        daily_record["cash_expense"] = new_cash_expense
        daily_record = calculate_totals(daily_record)
        
        await db.daily_sales.update_one(
            {"center": center, "date": date},
            {"$set": {
                "cash_expense": new_cash_expense,
                "petty_cash_closing": daily_record["petty_cash_closing"],
                "closing_balance": daily_record["closing_balance"],
                "to_deposit_in_bank": daily_record.get("to_deposit_in_bank", 0)
            }}
        )
        logger.info(f"Updated petty cash for {center} on {date}: cash_expense={new_cash_expense}, petty_cash_closing={daily_record['petty_cash_closing']}, closing_balance={daily_record['closing_balance']}")


class RecalculateRequest(BaseModel):
    token: str
    center: str
    month: str = ""  # YYYY-MM (optional, kept for backward compat — ignored, full history is always recalculated)

@router.post("/daily/recalculate")
async def recalculate_month_balances(req: RecalculateRequest):
    """
    Recalculate and chain opening/closing balances for ALL days of a center,
    from the very first recorded day to the last.
    This fixes cascading historical balance corruption.
    """
    session = await get_session(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    center = req.center.upper()
    
    # Fetch ALL records with valid YYYY-MM-DD dates for this center, sorted chronologically
    records = await db.daily_sales.find(
        {"center": center, "date": {"$regex": r"^\d{4}-\d{2}-\d{2}$"}},
        {"_id": 0}
    ).sort("date", 1).to_list(None)
    
    if not records:
        return {"success": True, "message": "No records found for this center", "updated": 0}
    
    # For the very first record, preserve its existing opening_balance
    prev_closing = records[0].get("opening_balance", 0)
    prev_petty_closing = records[0].get("petty_cash_opening", 0)
    
    from pymongo import ReplaceOne
    bulk_ops = []
    
    for record in records:
        # Set opening from previous day's closing
        record["opening_balance"] = prev_closing
        record["petty_cash_opening"] = prev_petty_closing
        
        # Recalculate all derived fields
        record = calculate_totals(record)
        
        # Queue bulk update
        bulk_ops.append(
            ReplaceOne(
                {"center": center, "date": record["date"]},
                record,
                upsert=False
            )
        )
        
        # Use this day's closing as next day's opening
        prev_closing = record["closing_balance"]
        prev_petty_closing = record["petty_cash_closing"]
    
    # Execute all updates in one batch
    if bulk_ops:
        result = await db.daily_sales.bulk_write(bulk_ops)
        updated_count = result.modified_count
    else:
        updated_count = 0
    
    first_date = records[0]["date"]
    last_date = records[-1]["date"]
    logger.info(f"Recalculated full history for {center}: {len(records)} records from {first_date} to {last_date}, {updated_count} modified")
    
    return {
        "success": True,
        "message": f"Recalculated {len(records)} records for {center} ({first_date} to {last_date})",
        "updated": updated_count,
        "total_records": len(records),
        "date_range": {"from": first_date, "to": last_date}
    }


class DeleteRangeRequest(BaseModel):
    token: str
    center: str
    from_month: str  # YYYY-MM
    to_month: str = ""  # YYYY-MM (optional, defaults to from_month)

@router.post("/daily/delete-range")
async def delete_daily_sales_range(req: DeleteRangeRequest):
    """
    Delete daily_sales records for a center within a month range.
    Available to managers and super admin.
    """
    session = await get_session(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    center = req.center.upper()
    from_month = req.from_month
    to_month = req.to_month or from_month
    
    # Build date filter
    if from_month == to_month:
        date_filter = {"$regex": f"^{from_month}"}
    else:
        date_filter = {"$gte": f"{from_month}-01", "$lte": f"{to_month}-31"}
    
    # Count before deleting
    sales_count = await db.daily_sales.count_documents({"center": center, "date": date_filter})
    expense_count = await db.expenses.count_documents({"center": center, "date": date_filter})
    
    if sales_count == 0 and expense_count == 0:
        return {"success": True, "message": "No records found in this range", "deleted": 0, "expenses_deleted": 0}
    
    # Delete sales + expenses
    sales_result = await db.daily_sales.delete_many({"center": center, "date": date_filter})
    expense_result = await db.expenses.delete_many({"center": center, "date": date_filter})
    
    logger.info(f"Deleted {sales_result.deleted_count} sales + {expense_result.deleted_count} expenses for {center} from {from_month} to {to_month}")
    
    return {
        "success": True,
        "message": f"Deleted {sales_result.deleted_count} sales + {expense_result.deleted_count} expenses for {center} ({from_month} to {to_month})",
        "deleted": sales_result.deleted_count,
        "expenses_deleted": expense_result.deleted_count
    }



# =======================================
# ADMIN SETTINGS ENDPOINTS
# =======================================

@router.post("/settings/get")
async def get_center_settings(req: dict = Body(...)):
    session = await get_session(req.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")
    center = req.get("center", "").upper()
    settings = await db.center_settings.find_one({"center": center}, {"_id": 0})
    return {"success": True, "settings": settings or {"center": center, "grid_hidden": False}}

@router.post("/settings/update")
async def update_center_settings(req: dict = Body(...)):
    session = await get_session(req.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")
    if not session.get("is_super_admin"):
        raise HTTPException(403, "Super admin only")
    center = req.get("center", "").upper()
    updates = req.get("updates", {})
    await db.center_settings.update_one(
        {"center": center},
        {"$set": {**updates, "center": center, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    return {"success": True, "message": "Settings updated"}



# =======================================
# DAILY SALES ENDPOINTS
# =======================================

@router.post("/daily")
async def get_daily_sales(req: SalesQueryRequest):
    """Get daily sales records with filters"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = await get_session(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    query = {}
    
    # Check if user has access to all centers
    can_view_all = has_all_centers_access(session)
    
    # Center filter - managers can only see their center unless admin/super admin/MGT
    if not can_view_all:
        query["center"] = session.get("center")
    elif req.center and req.center.lower() != "all":
        query["center"] = req.center.upper()
    # else: no center filter = all centers
    
    # Date filters
    if req.month:
        # Filter by month (YYYY-MM)
        query["date"] = {"$regex": f"^{req.month}"}
    elif req.start_date and req.end_date:
        query["date"] = {"$gte": req.start_date, "$lte": req.end_date}
    elif req.start_date:
        query["date"] = {"$gte": req.start_date}
    elif req.end_date:
        query["date"] = {"$lte": req.end_date}
    
    sales = await db.daily_sales.find(query, {"_id": 0}).sort("date", -1).to_list(1000)
    
    return {"sales": sales, "count": len(sales)}


@router.post("/expenses-by-date")
async def get_expenses_by_date(req: dict = Body(...)):
    """Aggregate expense amounts per date for a month, filtered by payment mode.
    Used by the Sales Grid to auto-fill the Cash Exp column from CASH expenses."""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = await get_session(req.get("token"))
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    center = (req.get("center") or "").upper()
    month = req.get("month", "")
    payment_mode = (req.get("payment_mode") or "CASH").upper()
    
    if not center or not month:
        raise HTTPException(400, "center and month required")
    
    # Aggregate expenses by date, filtered by payment mode
    pipeline = [
        {"$match": {
            "center": center,
            "date": {"$regex": f"^{month}"},
            "payment_mode": {"$regex": f"^{payment_mode}$", "$options": "i"}
        }},
        {"$group": {
            "_id": "$date",
            "total": {"$sum": {"$ifNull": ["$amount", 0]}}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    results = await db.expenses.aggregate(pipeline).to_list(100)
    
    expenses_by_date = {}
    for r in results:
        expenses_by_date[r["_id"]] = round(r["total"], 2)
    
    return {"success": True, "expenses_by_date": expenses_by_date, "payment_mode": payment_mode}

@router.post("/daily/create")
async def create_daily_sale(req: DailySaleCreate, token: str):
    """Create a new daily sales record"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Check permission - can only create for own center unless admin/MGT
    can_view_all = has_all_centers_access(session)
    if not can_view_all and session.get("center") != req.center.upper():
        raise HTTPException(403, "Cannot create sales record for another center")
    
    # Check if date is frozen for SALES specifically
    can_edit, reason = await can_edit_date(session, req.center, req.date, "sales")
    if not can_edit:
        raise HTTPException(403, f"Cannot create record for frozen date. {reason}")
    
    # Check if record already exists
    existing = await db.daily_sales.find_one({
        "center": req.center.upper(),
        "date": req.date
    })
    
    if existing:
        raise HTTPException(400, f"Sales record for {req.center} on {req.date} already exists")
    
    # Create record
    record = req.dict()
    record["center"] = req.center.upper()
    record = calculate_totals(record)
    record["created_at"] = datetime.now(timezone.utc).isoformat()
    record["created_by"] = session.get("managerName", "Unknown")
    
    await db.daily_sales.insert_one(record)
    
    # Remove _id before returning
    record.pop("_id", None)
    
    logger.info(f"Daily sale created: {req.center} - {req.date} by {session.get('managerName')}")
    
    return {"success": True, "message": "Daily sales record created", "record": record}

@router.put("/daily/{center}/{date}")
async def update_daily_sale(center: str, date: str, req: DailySaleUpdate, token: str):
    """Update an existing daily sales record"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Check permission
    if not (session.get("is_super_admin") or session.get("is_admin")) and session.get("center") != center.upper():
        raise HTTPException(403, "Cannot update sales record for another center")
    
    # Check if date is frozen for SALES specifically
    can_edit, reason = await can_edit_date(session, center, date, "sales")
    if not can_edit:
        raise HTTPException(403, f"Cannot update frozen date. {reason}")
    
    # Find existing record
    existing = await db.daily_sales.find_one({
        "center": center.upper(),
        "date": date
    })
    
    if not existing:
        raise HTTPException(404, f"Sales record for {center} on {date} not found")
    
    # Update fields
    update_data = {k: v for k, v in req.dict().items() if v is not None}
    
    if update_data:
        # Merge with existing and recalculate
        for key, value in update_data.items():
            existing[key] = value
        
        existing = calculate_totals(existing)
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()
        existing["updated_by"] = session.get("managerName", "Unknown")
        
        await db.daily_sales.update_one(
            {"center": center.upper(), "date": date},
            {"$set": existing}
        )
        
        # If opening_balance or any field affecting closing_balance was changed,
        # cascade recalculate all subsequent days (only for single-save, not bulk)
        # Check if this is a bulk save via query param
        cascade_fields = {"opening_balance", "total_sale", "cash_receipts", "deposited_in_bank",
                          "card_idfc", "bharat_pay", "swiggy", "zomato", "doordash", "online_other",
                          "cash_expense", "petty_cash_opening"}
        if cascade_fields & set(update_data.keys()):
            # Recalculate all records from this date forward
            subsequent = await db.daily_sales.find(
                {"center": center.upper(), "date": {"$gt": date, "$regex": r"^\d{4}-\d{2}-\d{2}$"}},
                {"_id": 0}
            ).sort("date", 1).to_list(None)
            
            if subsequent:
                from pymongo import ReplaceOne
                prev_closing = existing.get("closing_balance", 0)
                prev_petty_closing = existing.get("petty_cash_closing", 0)
                bulk_ops = []
                
                for record in subsequent:
                    record["opening_balance"] = prev_closing
                    record["petty_cash_opening"] = prev_petty_closing
                    record = calculate_totals(record)
                    bulk_ops.append(
                        ReplaceOne(
                            {"center": center.upper(), "date": record["date"]},
                            record, upsert=False
                        )
                    )
                    prev_closing = record["closing_balance"]
                    prev_petty_closing = record["petty_cash_closing"]
                
                if bulk_ops:
                    await db.daily_sales.bulk_write(bulk_ops)
                    logger.info(f"Cascaded balance update from {date}: {len(bulk_ops)} subsequent records recalculated")
    
    existing.pop("_id", None)
    logger.info(f"Daily sale updated: {center} - {date} by {session.get('managerName')}")
    
    return {"success": True, "message": "Daily sales record updated", "record": existing}

@router.delete("/daily/{center}/{date}")
async def delete_daily_sale(center: str, date: str, token: str):
    """Delete a daily sales record (Admin/MGT only)"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    can_view_all = has_all_centers_access(session)
    if not can_view_all:
        raise HTTPException(403, "Only Admin/Super Admin can delete sales records")
    
    result = await db.daily_sales.delete_one({
        "center": center.upper(),
        "date": date
    })
    
    if result.deleted_count == 0:
        raise HTTPException(404, f"Sales record for {center} on {date} not found")
    
    logger.info(f"Daily sale deleted: {center} - {date} by {session.get('managerName')}")
    
    return {"success": True, "message": "Daily sales record deleted"}

# =======================================
# SUPER ADMIN FREEZE CONTROL
# =======================================

class AdminFreezeRequest(BaseModel):
    token: str
    action: str  # "freeze" or "unfreeze"
    scope: str   # "day" or "month"
    date: Optional[str] = None  # YYYY-MM-DD for day, YYYY-MM for month
    center: Optional[str] = None  # specific center or "all"

@router.post("/admin/freeze-control")
async def admin_freeze_control(req: AdminFreezeRequest):
    """
    Super Admin only: Manually freeze or unfreeze sales & expense data.
    - action: "freeze" or "unfreeze"
    - scope: "day" (single date) or "month" (entire month)
    - date: YYYY-MM-DD for day, YYYY-MM for month
    - center: specific center code or "all" for all centers
    """
    session = await get_session(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # SUPER ADMIN ONLY - check by email
    SUPER_ADMIN_EMAILS = ["jayanti.devashree@gmail.com", "sandeep.gadhwal@purnabramha.com"]
    user_email = session.get("email", "").lower()
    is_super_admin = session.get("is_super_admin", False) or user_email in [e.lower() for e in SUPER_ADMIN_EMAILS]
    
    if not is_super_admin:
        raise HTTPException(403, "Only Super Admins can use freeze control")
    
    if req.action not in ["freeze", "unfreeze"]:
        raise HTTPException(400, "Action must be 'freeze' or 'unfreeze'")
    
    if req.scope not in ["day", "month"]:
        raise HTTPException(400, "Scope must be 'day' or 'month'")
    
    if not req.date:
        raise HTTPException(400, "Date is required")
    
    # Build the query for dates to affect
    if req.scope == "day":
        # Single day
        dates_to_affect = [req.date]
    else:
        # Entire month - get all dates in that month
        year, month = req.date.split("-")[:2]
        import calendar
        num_days = calendar.monthrange(int(year), int(month))[1]
        dates_to_affect = [f"{year}-{month}-{str(d).zfill(2)}" for d in range(1, num_days + 1)]
    
    # Build center query
    center_query = {}
    if req.center and req.center.lower() != "all":
        center_query["center"] = req.center.upper()
    
    affected_records = {"sales": 0, "expenses": 0}
    
    if req.action == "freeze":
        # Create freeze records in admin_freezes collection
        for date in dates_to_affect:
            freeze_record = {
                "date": date,
                "center": req.center.upper() if req.center and req.center.lower() != "all" else "ALL",
                "frozen_by": session.get("managerName", user_email),
                "frozen_at": datetime.now(timezone.utc).isoformat(),
                "type": "admin_freeze"
            }
            
            # Upsert to avoid duplicates
            await db.admin_freezes.update_one(
                {"date": date, "center": freeze_record["center"]},
                {"$set": freeze_record},
                upsert=True
            )
        
        # Also remove any active unlock grants for these dates
        for date in dates_to_affect:
            delete_query = {"date": date, "status": "active"}
            if req.center and req.center.lower() != "all":
                delete_query["center"] = req.center.upper()
            result = await db.unlock_grants.delete_many(delete_query)
            affected_records["sales"] += result.deleted_count
        
        logger.info(f"Admin freeze: {req.scope} {req.date} for {req.center or 'ALL'} by {session.get('managerName')}")
        
        return {
            "success": True,
            "message": f"Successfully frozen {req.scope} {req.date} for {req.center or 'all centers'}",
            "dates_affected": len(dates_to_affect),
            "center": req.center or "ALL"
        }
    
    else:  # unfreeze
        # Remove admin freeze records
        for date in dates_to_affect:
            delete_query = {"date": date, "type": "admin_freeze"}
            if req.center and req.center.lower() != "all":
                delete_query["center"] = req.center.upper()
            else:
                delete_query["center"] = "ALL"
            await db.admin_freezes.delete_many(delete_query)
        
        # Create unlock grants for these dates (valid for 30 days for admin unlocks)
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        # Get list of centers to unlock
        if req.center and req.center.lower() != "all":
            centers_to_unlock = [req.center.upper()]
        else:
            # Get all centers from database
            all_centers = await db.centers.distinct("code")
            centers_to_unlock = all_centers if all_centers else []
        
        for date in dates_to_affect:
            for center in centers_to_unlock:
                # Create unlock grant for SALES
                await db.unlock_grants.update_one(
                    {"date": date, "center": center, "type": "sales"},
                    {"$set": {
                        "date": date,
                        "center": center,
                        "type": "sales",
                        "status": "active",
                        "granted_by": f"Admin: {session.get('managerName', user_email)}",
                        "granted_at": datetime.now(timezone.utc).isoformat(),
                        "expires_at": expires_at,
                        "admin_unlock": True
                    }},
                    upsert=True
                )
                
                # Create unlock grant for EXPENSES
                await db.unlock_grants.update_one(
                    {"date": date, "center": center, "type": "expenses"},
                    {"$set": {
                        "date": date,
                        "center": center,
                        "type": "expenses",
                        "status": "active",
                        "granted_by": f"Admin: {session.get('managerName', user_email)}",
                        "granted_at": datetime.now(timezone.utc).isoformat(),
                        "expires_at": expires_at,
                        "admin_unlock": True
                    }},
                    upsert=True
                )
                affected_records["sales"] += 1
                affected_records["expenses"] += 1
        
        logger.info(f"Admin unfreeze: {req.scope} {req.date} for {req.center or 'ALL'} by {session.get('managerName')}")
        
        return {
            "success": True,
            "message": f"Successfully unfrozen {req.scope} {req.date} for {req.center or 'all centers'}",
            "dates_affected": len(dates_to_affect),
            "centers_affected": len(centers_to_unlock),
            "unlock_grants_created": affected_records
        }

@router.get("/admin/freeze-status")
async def get_freeze_status(token: str, month: str, center: Optional[str] = None):
    """Get freeze status for a month - shows which dates are frozen by admin"""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Build query
    query = {"date": {"$regex": f"^{month}"}}
    if center and center.lower() != "all":
        query["$or"] = [{"center": center.upper()}, {"center": "ALL"}]
    
    # Get admin freezes
    admin_freezes = await db.admin_freezes.find(query, {"_id": 0}).to_list(100)
    
    # Get active unlock grants
    unlock_query = {"date": {"$regex": f"^{month}"}, "status": "active"}
    if center and center.lower() != "all":
        unlock_query["center"] = center.upper()
    unlocks = await db.unlock_grants.find(unlock_query, {"_id": 0}).to_list(500)
    
    # Build status map
    frozen_dates = set()
    unlocked_dates = set()
    
    for freeze in admin_freezes:
        frozen_dates.add(freeze["date"])
    
    for unlock in unlocks:
        unlocked_dates.add(unlock["date"])
    
    return {
        "month": month,
        "center": center or "all",
        "admin_frozen_dates": list(frozen_dates),
        "unlocked_dates": list(unlocked_dates),
        "freeze_records": admin_freezes
    }


# =======================================
# UNLOCK REQUEST ENDPOINTS
# =======================================

@router.post("/unlock-request")
async def create_unlock_request(req: UnlockRequest, token: str):
    """Create an unlock request for a frozen date"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Check if date is actually frozen
    if not is_date_frozen(req.date):
        raise HTTPException(400, "This date is not frozen. You can edit it directly.")
    
    # Check if request already exists for this center/date
    existing = await db.unlock_requests.find_one({
        "center": req.center.upper(),
        "date": req.date,
        "status": "pending"
    })
    
    if existing:
        raise HTTPException(400, "An unlock request for this date is already pending")
    
    # Create request
    request_doc = {
        "center": req.center.upper(),
        "date": req.date,
        "reason": req.reason,
        "requested_by": session.get("managerName", "Unknown"),
        "requested_by_email": session.get("email", ""),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.unlock_requests.insert_one(request_doc)
    request_doc["id"] = str(result.inserted_id)
    request_doc.pop("_id", None)
    
    logger.info(f"Unlock request created: {req.center} - {req.date} by {session.get('managerName')}")
    
    return {"success": True, "message": "Unlock request submitted successfully", "request": request_doc}

@router.get("/unlock-requests")
async def get_unlock_requests(token: str, status: str = "all"):
    """Get all unlock requests (Super Admin only) or own requests"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    query = {}
    
    # Super Admin can see all, others see only their center's requests
    if not session.get("is_super_admin"):
        query["center"] = session.get("center")
    
    if status != "all":
        query["status"] = status
    
    requests = await db.unlock_requests.find(query).sort("created_at", -1).to_list(100)
    
    # Convert ObjectId to string
    for req in requests:
        req["id"] = str(req.pop("_id"))
    
    return {"requests": requests, "count": len(requests)}

@router.post("/unlock-request/{request_id}/action")
async def process_unlock_request(request_id: str, req: UnlockRequestAction, token: str):
    """Approve or reject an unlock request (Super Admin only)"""
    from bson import ObjectId
    
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Only Super Admin can process requests
    if not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin can approve/reject unlock requests")
    
    if req.action not in ["approve", "reject"]:
        raise HTTPException(400, "Action must be 'approve' or 'reject'")
    
    # Find the request
    try:
        unlock_request = await db.unlock_requests.find_one({"_id": ObjectId(request_id)})
    except:
        raise HTTPException(400, "Invalid request ID")
    
    if not unlock_request:
        raise HTTPException(404, "Unlock request not found")
    
    if unlock_request.get("status") != "pending":
        raise HTTPException(400, f"Request is already {unlock_request.get('status')}")
    
    # Update request status
    update_data = {
        "status": "approved" if req.action == "approve" else "rejected",
        "processed_by": session.get("managerName", "Unknown"),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "admin_notes": req.admin_notes or ""
    }
    
    await db.unlock_requests.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": update_data}
    )
    
    # If approved, create unlock grants for BOTH sales and expenses (valid for 24 hours)
    if req.action == "approve":
        from datetime import timedelta
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        
        # Create unlock grant for SALES
        await db.unlock_grants.insert_one({
            "center": unlock_request["center"],
            "date": unlock_request["date"],
            "type": "sales",  # Explicit type
            "status": "active",
            "granted_by": session.get("managerName", "Unknown"),
            "granted_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at,
            "request_id": request_id
        })
        
        # SYNCHRONIZED UNLOCK: Also create unlock grant for EXPENSES on the same date
        await db.unlock_grants.insert_one({
            "center": unlock_request["center"],
            "date": unlock_request["date"],
            "type": "expenses",  # Explicit type for expenses
            "status": "active",
            "granted_by": session.get("managerName", "Unknown"),
            "granted_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at,
            "request_id": request_id,
            "synced_with_sales": True  # Flag to indicate this was auto-created
        })
        
        logger.info(f"Unlock granted (SALES + EXPENSES): {unlock_request['center']} - {unlock_request['date']} by {session.get('managerName')} (expires: {expires_at})")
    
    return {
        "success": True, 
        "message": f"Request {req.action}d successfully",
        "status": update_data["status"]
    }

@router.get("/check-frozen/{center}/{date}")
async def check_frozen_status(center: str, date: str, token: str):
    """Check if a specific date is frozen and its unlock status for both sales and expenses"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    is_frozen = is_date_frozen(date)
    admin_frozen = await is_admin_frozen(center, date)
    
    # Check unlock status separately for sales and expenses
    is_sales_unlocked = await is_date_unlocked(center, date, "sales") if is_frozen or admin_frozen else False
    is_expenses_unlocked = await is_date_unlocked(center, date, "expenses") if is_frozen or admin_frozen else False
    
    # Check can_edit separately for sales and expenses
    can_edit_sales, reason_sales = await can_edit_date(session, center, date, "sales")
    can_edit_expenses, reason_expenses = await can_edit_date(session, center, date, "expenses")
    
    # Check for pending unlock request
    pending_request = await db.unlock_requests.find_one({
        "center": center.upper(),
        "date": date,
        "status": "pending"
    })
    
    return {
        "date": date,
        "center": center,
        "is_frozen": is_frozen,
        "is_admin_frozen": admin_frozen,
        # Sales status
        "is_sales_unlocked": is_sales_unlocked,
        "can_edit_sales": can_edit_sales,
        "reason_sales": reason_sales,
        # Expenses status
        "is_expenses_unlocked": is_expenses_unlocked,
        "can_edit_expenses": can_edit_expenses,
        "reason_expenses": reason_expenses,
        # Legacy fields for backwards compatibility
        "is_unlocked": is_sales_unlocked or is_expenses_unlocked,
        "can_edit": can_edit_sales and can_edit_expenses,
        "reason": reason_sales if not can_edit_sales else reason_expenses,
        # Other info
        "has_pending_request": pending_request is not None,
        "is_super_admin": session.get("is_super_admin", False)
    }

# =======================================
# EXPENSES ENDPOINTS
# =======================================

@router.post("/expenses")
async def get_expenses(req: ExpenseQueryRequest):
    """Get expense records with filters"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = await get_session(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    query = {}
    
    # Check if user has access to all centers
    can_view_all = has_all_centers_access(session)
    
    # Center filter
    if not can_view_all:
        query["center"] = session.get("center")
    elif req.center and req.center.lower() != "all":
        query["center"] = req.center.upper()
    
    # Date filters
    if req.month:
        query["date"] = {"$regex": f"^{req.month}"}
    elif req.start_date and req.end_date:
        query["date"] = {"$gte": req.start_date, "$lte": req.end_date}
    elif req.start_date:
        query["date"] = {"$gte": req.start_date}
    elif req.end_date:
        query["date"] = {"$lte": req.end_date}
    
    # Expense type filter
    if req.expense_type:
        query["expense_type"] = req.expense_type
    
    # Fetch expenses - include _id for delete functionality
    expenses_cursor = db.expenses.find(query).sort("date", -1)
    expenses = []
    async for exp in expenses_cursor:
        exp_dict = {k: v for k, v in exp.items() if k != "_id"}
        expense_id_str = str(exp["_id"])
        exp_dict["expense_id"] = expense_id_str  # Convert ObjectId to string
        
        # Build list of identifiers this expense may be referenced by in expense_attachments
        # (legacy expenses may use _id string; newer ones may have expense_id field)
        possible_ids = [expense_id_str]
        if exp.get("expense_id") and exp.get("expense_id") != expense_id_str:
            possible_ids.append(exp.get("expense_id"))
        
        # Source of truth: query expense_attachments collection directly by expense_id.
        # This works regardless of whether the cache field expenses.attachments was populated.
        direct_attachments = []
        async for att in db.expense_attachments.find(
            {"expense_id": {"$in": possible_ids}, "is_deleted": {"$ne": True}},
            {"_id": 0, "attachment_id": 1, "original_filename": 1, "file_size": 1, "content_type": 1, "mime_type": 1, "file_type": 1}
        ):
            direct_attachments.append(att)
        
        has_direct_attachment = len(direct_attachments) > 0
        has_group_attachment = False
        group_info = None
        group_attachments = []
        
        if exp.get("invoice_group_id"):
            group = await db.invoice_groups.find_one(
                {"group_id": exp["invoice_group_id"], "is_deleted": {"$ne": True}},
                {"_id": 0, "vendor_name": 1, "invoice_number": 1, "attachments": 1}
            )
            if group:
                has_group_attachment = bool(group.get("attachments") and len(group.get("attachments", [])) > 0)
                group_info = {
                    "vendor_name": group.get("vendor_name"),
                    "invoice_number": group.get("invoice_number")
                }
                # Also load group-level attachments so user can view them from expense row
                async for att in db.expense_attachments.find(
                    {"invoice_group_id": exp["invoice_group_id"], "is_deleted": {"$ne": True}},
                    {"_id": 0, "attachment_id": 1, "original_filename": 1, "file_size": 1, "content_type": 1}
                ):
                    group_attachments.append(att)
        
        # Determine attachment status
        if has_direct_attachment:
            exp_dict["attachment_status"] = "attached"
            exp_dict["attachment_count"] = len(direct_attachments)
            exp_dict["attachment_source"] = "direct"
        elif has_group_attachment:
            exp_dict["attachment_status"] = "attached_via_group"
            exp_dict["attachment_count"] = len(group_attachments)
            exp_dict["attachment_source"] = "group"
        else:
            exp_dict["attachment_status"] = "missing"
            exp_dict["attachment_count"] = 0
            exp_dict["attachment_source"] = None
        
        exp_dict["direct_attachments"] = direct_attachments
        exp_dict["group_attachments"] = group_attachments
        exp_dict["is_grouped"] = bool(exp.get("invoice_group_id"))
        exp_dict["group_info"] = group_info
        
        expenses.append(exp_dict)
        if len(expenses) >= 5000:
            break
    
    return {"expenses": expenses, "count": len(expenses)}

@router.post("/expenses/create")
async def create_expense(req: ExpenseCreate, token: str):
    """Create a new expense record"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Check permission
    if not (session.get("is_super_admin") or session.get("is_admin")) and session.get("center") != req.center.upper():
        raise HTTPException(403, "Cannot create expense for another center")
    
    # Check if date is frozen for EXPENSES specifically
    can_edit, reason = await can_edit_date(session, req.center, req.date, "expenses")
    if not can_edit:
        raise HTTPException(403, f"Cannot add expense for frozen date. {reason}")
    
    record = req.dict()
    record["center"] = req.center.upper()
    record["created_at"] = datetime.now(timezone.utc).isoformat()
    record["created_by"] = session.get("managerName", "Unknown")
    # Auto-derive gst_amount from rate when not provided (inclusive basis)
    rate = float(record.get("gst_rate") or 0)
    amt = float(record.get("amount") or 0)
    if rate > 0 and not record.get("gst_amount"):
        record["gst_amount"] = round(amt * rate / (100 + rate), 2)
    record["gst_rate"] = rate
    record["gst_amount"] = round(float(record.get("gst_amount") or 0), 2)
    # NEW: GST Paid (printed-on-bill). Default 0. Pure addition — no derive.
    record["gst_paid"] = round(float(record.get("gst_paid") or 0), 2)
    
    result = await db.expenses.insert_one(record)
    expense_id_str = str(result.inserted_id)
    record["expense_id"] = expense_id_str
    record.pop("_id", None)
    
    # Persist expense_id field on the document so attachment uploads (which match by expense_id) work reliably
    await db.expenses.update_one(
        {"_id": result.inserted_id},
        {"$set": {"expense_id": expense_id_str}}
    )
    
    # Update daily_sales petty_cash_closing if expense is CASH
    if req.payment_mode == "CASH":
        await update_petty_cash_for_expense(req.center.upper(), req.date, req.amount)
    
    logger.info(f"Expense created: {req.center} - {req.date} - {req.description} by {session.get('managerName')}")
    
    return {"success": True, "message": "Expense record created", "record": record}

@router.put("/expenses/{expense_id}")
async def update_expense(expense_id: str, req: ExpenseUpdate, token: str):
    """Update an expense record"""
    from bson import ObjectId
    
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    try:
        obj_id = ObjectId(expense_id)
    except Exception:
        raise HTTPException(400, "Invalid expense ID")
    
    # Find existing
    existing = await db.expenses.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(404, "Expense not found")
    
    # Check permission
    if not (session.get("is_super_admin") or session.get("is_admin")) and session.get("center") != existing.get("center"):
        raise HTTPException(403, "Cannot update expense for another center")
    
    # Check if date is frozen for EXPENSES specifically
    expense_date = existing.get("date", "")
    can_edit, reason = await can_edit_date(session, existing.get("center", ""), expense_date, "expenses")
    if not can_edit:
        raise HTTPException(403, f"Cannot update expense for frozen date. {reason}")
    
    update_data = {k: v for k, v in req.dict().items() if v is not None}
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        update_data["updated_by"] = session.get("managerName", "Unknown")
        # Auto-derive gst_amount when rate is set/changed but amount explicitly omitted
        new_rate = update_data.get("gst_rate", existing.get("gst_rate"))
        new_amount_total = update_data.get("amount", existing.get("amount"))
        if new_rate is not None and "gst_amount" not in update_data and new_amount_total:
            try:
                r = float(new_rate); a = float(new_amount_total)
                if r > 0:
                    update_data["gst_amount"] = round(a * r / (100 + r), 2)
            except Exception:
                pass
        
        await db.expenses.update_one(
            {"_id": obj_id},
            {"$set": update_data}
        )
    
    logger.info(f"Expense updated: {expense_id} by {session.get('managerName')}")
    
    return {"success": True, "message": "Expense updated"}

@router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str, token: str):
    """Delete an expense record"""
    from bson import ObjectId
    
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    try:
        obj_id = ObjectId(expense_id)
    except Exception:
        raise HTTPException(400, "Invalid expense ID")
    
    # Find existing
    existing = await db.expenses.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(404, "Expense not found")
    
    # Check permission - MGT can delete any, others only their own center
    if not (session.get("is_super_admin") or session.get("is_admin")) and session.get("center") != existing.get("center"):
        raise HTTPException(403, "Cannot delete expense for another center")
    
    # Check if date is frozen for EXPENSES specifically
    expense_date = existing.get("date", "")
    can_edit, reason = await can_edit_date(session, existing.get("center", ""), expense_date, "expenses")
    if not can_edit:
        raise HTTPException(403, f"Cannot delete expense for frozen date. {reason}")
    
    # If CASH expense, update petty cash (reverse the expense)
    if existing.get("payment_mode") == "CASH":
        await update_petty_cash_for_expense(existing.get("center"), expense_date, existing.get("amount", 0), is_add=False)
    
    await db.expenses.delete_one({"_id": obj_id})
    
    logger.info(f"Expense deleted: {expense_id} by {session.get('managerName')}")
    
    return {"success": True, "message": "Expense deleted"}

# =======================================
# REPORTS ENDPOINTS
# =======================================

@router.post("/reports/daily-summary")
async def get_daily_summary(req: SalesQueryRequest):
    """Get daily summary report for a specific date or date range"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = await get_session(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Build query for sales
    sales_query = {}
    
    if not (session.get("is_super_admin") or session.get("is_admin")):
        sales_query["center"] = session.get("center")
    elif req.center:
        sales_query["center"] = req.center.upper()
    
    if req.start_date and req.end_date:
        sales_query["date"] = {"$gte": req.start_date, "$lte": req.end_date}
    elif req.start_date:
        sales_query["date"] = req.start_date
    
    # Get sales
    sales = await db.daily_sales.find(sales_query, {"_id": 0}).sort("date", 1).to_list(1000)
    
    # Get expenses for same period
    expense_query = dict(sales_query)
    expenses = await db.expenses.find(expense_query, {"_id": 0}).sort("date", 1).to_list(5000)
    
    # Calculate summary
    summary = {
        "total_sale": sum(s.get("total_sale", 0) for s in sales),
        "total_cash_sale": sum(s.get("total_cash_sale", 0) for s in sales),
        "total_online_sale": sum(s.get("total_online_sale", 0) for s in sales),
        "total_card_idfc": sum(s.get("card_idfc", 0) for s in sales),
        "total_bharat_pay": sum(s.get("bharat_pay", 0) for s in sales),
        "total_swiggy": sum(s.get("swiggy", 0) for s in sales),
        "total_zomato": sum(s.get("zomato", 0) for s in sales),
        "total_expenses": sum(e.get("amount", 0) for e in expenses),
        "days_count": len(sales)
    }
    
    # Expense breakdown by type
    expense_by_type = {}
    for exp in expenses:
        exp_type = exp.get("expense_type", "OTHER")
        expense_by_type[exp_type] = expense_by_type.get(exp_type, 0) + exp.get("amount", 0)
    
    # Expense breakdown by payment mode
    expense_by_mode = {}
    for exp in expenses:
        mode = exp.get("payment_mode", "CASH")
        expense_by_mode[mode] = expense_by_mode.get(mode, 0) + exp.get("amount", 0)
    
    return {
        "summary": summary,
        "expense_by_type": expense_by_type,
        "expense_by_mode": expense_by_mode,
        "sales": sales,
        "expenses": expenses
    }

@router.post("/reports/monthly-summary")
async def get_monthly_summary(req: SalesQueryRequest):
    """Get monthly summary report"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = await get_session(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Check if user has sales_cash role
    if not has_sales_access(session):
        raise HTTPException(403, "You don't have access to Sales & Cash features")
    
    if not req.month:
        raise HTTPException(400, "Month is required (YYYY-MM format)")
    
    # Check if user can view all centers
    user_center = session.get("center", "")
    can_view_all = has_all_centers_access(session)
    
    logger.info(f"Monthly summary: user={user_center}, can_view_all={can_view_all}, req.center={req.center}")
    
    # Build query
    query = {"date": {"$regex": f"^{req.month}"}}
    
    # Determine which center(s) to query
    if not can_view_all:
        # Regular user can only see their own center
        query["center"] = user_center
    elif req.center and req.center.lower() != "all":
        # Admin/SuperAdmin filtering by specific center
        query["center"] = req.center.upper()
    # else: no center filter = all centers
    
    logger.info(f"Query: {query}")
    
    # Get all sales for the month
    sales = await db.daily_sales.find(query, {"_id": 0}).sort("date", 1).to_list(1000)
    
    logger.info(f"Found {len(sales)} sales records")
    
    # Get expenses for the month
    expenses = await db.expenses.find(query, {"_id": 0}).sort("date", 1).to_list(5000)
    
    # If querying all centers, group by center
    if can_view_all and (not req.center or req.center.lower() == "all"):
        # Group by center
        centers_data = {}
        total_gst = 0
        total_guests = 0
        total_bills = 0
        
        for sale in sales:
            c = sale.get("center")
            if c not in centers_data:
                centers_data[c] = {
                    "center": c,
                    "currency": get_currency_symbol(c),
                    "total_sale": 0,
                    "total_cash_sale": 0,
                    "total_online_sale": 0,
                    "total_expenses": 0,
                    "total_gst": 0,
                    "total_guests": 0,
                    "total_bills": 0,
                    "days_count": 0
                }
            centers_data[c]["total_sale"] += sale.get("total_sale", 0)
            centers_data[c]["total_cash_sale"] += sale.get("total_cash_sale", 0)
            centers_data[c]["total_online_sale"] += sale.get("total_online_sale", 0)
            centers_data[c]["total_guests"] += sale.get("num_guests", 0)
            centers_data[c]["total_bills"] += sale.get("num_bills", 0)
            centers_data[c]["days_count"] += 1
            
            # Calculate GST for this sale
            gst_info = calculate_gst(
                sale.get("total_sale", 0),
                sale.get("swiggy", 0),
                sale.get("zomato", 0),
                c
            )
            centers_data[c]["total_gst"] += gst_info["gst_amount"]
            total_gst += gst_info["gst_amount"]
            total_guests += sale.get("num_guests", 0)
            total_bills += sale.get("num_bills", 0)
        
        # Add expenses
        for exp in expenses:
            c = exp.get("center")
            if c in centers_data:
                centers_data[c]["total_expenses"] += exp.get("amount", 0)
        
        # Calculate expense by type for all centers
        expense_by_type = {}
        for exp in expenses:
            exp_type = exp.get("expense_type", "OTHER")
            expense_by_type[exp_type] = expense_by_type.get(exp_type, 0) + exp.get("amount", 0)
        
        total_sale = sum(s.get("total_sale", 0) for s in sales)
        
        return {
            "month": req.month,
            "centers": list(centers_data.values()),
            "grand_total": {
                "total_sale": total_sale,
                "total_cash_sale": sum(s.get("total_cash_sale", 0) for s in sales),
                "total_online_sale": sum(s.get("total_online_sale", 0) for s in sales),
                "total_card_idfc": sum(s.get("card_idfc", 0) for s in sales),
                "total_bharat_pay": sum(s.get("bharat_pay", 0) for s in sales),
                "total_swiggy": sum(s.get("swiggy", 0) for s in sales),
                "total_zomato": sum(s.get("zomato", 0) for s in sales),
                "total_expenses": sum(e.get("amount", 0) for e in expenses),
                "total_gst": round(total_gst, 2),
                "total_guests": total_guests,
                "total_bills": total_bills,
                "avg_per_pax": round(total_sale / total_guests, 2) if total_guests > 0 else 0,
                "avg_per_bill": round(total_sale / total_bills, 2) if total_bills > 0 else 0
            },
            "expense_by_type": expense_by_type
        }
    
    # Single center summary
    # For non-admin users or when req.center is "all", use their session center
    center_code = req.center if req.center and req.center.lower() != "all" else session.get("center")
    total_sale = sum(s.get("total_sale", 0) for s in sales)
    total_swiggy = sum(s.get("swiggy", 0) for s in sales)
    total_zomato = sum(s.get("zomato", 0) for s in sales)
    total_guests = sum(s.get("num_guests", 0) for s in sales)
    total_bills = sum(s.get("num_bills", 0) for s in sales)
    
    # Calculate total GST for the month
    gst_info = calculate_gst(total_sale, total_swiggy, total_zomato, center_code)
    
    summary = {
        "month": req.month,
        "center": center_code,
        "currency": get_currency_symbol(center_code),
        "total_sale": total_sale,
        "total_cash_sale": sum(s.get("total_cash_sale", 0) for s in sales),
        "total_online_sale": sum(s.get("total_online_sale", 0) for s in sales),
        "total_card_idfc": sum(s.get("card_idfc", 0) for s in sales),
        "total_bharat_pay": sum(s.get("bharat_pay", 0) for s in sales),
        "total_swiggy": total_swiggy,
        "total_zomato": total_zomato,
        "total_expenses": sum(e.get("amount", 0) for e in expenses),
        "days_count": len(sales),
        # GST information
        "gst_rate": gst_info["gst_rate"],
        "gst_amount": gst_info["gst_amount"],
        "gst_inclusive": gst_info["is_inclusive"],
        "net_sale": gst_info["net_sale"],
        # Guest & Bill stats
        "total_guests": total_guests,
        "total_bills": total_bills,
        "avg_per_pax": round(total_sale / total_guests, 2) if total_guests > 0 else 0,
        "avg_per_bill": round(total_sale / total_bills, 2) if total_bills > 0 else 0
    }
    
    # Day-wise breakdown
    daily_data = []
    for sale in sales:
        day_expenses = sum(e.get("amount", 0) for e in expenses if e.get("date") == sale.get("date"))
        day_gst = calculate_gst(
            sale.get("total_sale", 0),
            sale.get("swiggy", 0),
            sale.get("zomato", 0),
            center_code
        )
        daily_data.append({
            "date": sale.get("date"),
            "total_sale": sale.get("total_sale", 0),
            "cash_sale": sale.get("total_cash_sale", 0),
            "online_sale": sale.get("total_online_sale", 0),
            "expenses": day_expenses,
            "net": sale.get("total_sale", 0) - day_expenses,
            "gst_amount": day_gst["gst_amount"],
            "num_guests": sale.get("num_guests", 0),
            "num_bills": sale.get("num_bills", 0),
            "avg_per_pax": sale.get("avg_per_pax", 0),
            "avg_per_bill": sale.get("avg_per_bill", 0)
        })
    
    # Expense breakdown
    expense_by_type = {}
    for exp in expenses:
        exp_type = exp.get("expense_type", "OTHER")
        expense_by_type[exp_type] = expense_by_type.get(exp_type, 0) + exp.get("amount", 0)
    
    return {
        "summary": summary,
        "daily_data": daily_data,
        "expense_by_type": expense_by_type
    }

@router.get("/expense-types")
async def get_expense_types():
    """Get all expense types from expense_heads master collection"""
    head_docs = await db.expense_heads.find(
        {"is_active": {"$ne": False}}, {"_id": 0, "name": 1}
    ).to_list(500)
    
    if head_docs:
        all_types = sorted(set(h["name"] for h in head_docs if h.get("name")))
        return {"expense_types": all_types, "source": "expense_heads"}
    
    # Fallback: distinct from existing expenses
    types = await db.expenses.distinct("expense_type")
    return {"expense_types": sorted(set(t for t in types if t)), "source": "fallback"}

@router.get("/payment-modes")
async def get_payment_modes():
    """Get all payment modes — pulls from master_payment_modes first"""
    # PRIMARY: Pull from master table
    master_modes = await db.master_payment_modes.find(
        {"is_active": True}, {"_id": 0, "name": 1}
    ).to_list(100)
    
    if master_modes:
        return {"payment_modes": sorted(m["name"] for m in master_modes), "source": "master"}
    
    # FALLBACK: Hardcoded (will be removed after migration)
    return {
        "payment_modes": ["CASH", "ONLINE UPI", "ONLINE NEFT/IMPS", "CARD", "CHEQUE"],
        "source": "legacy"
    }

@router.get("/centers-list")
async def get_centers_for_sales():
    """Get list of ALL centers from centers collection (same source as management).

    Also returns ``country`` and ``is_india_center`` so the frontend can
    correctly choose currency symbol (₹ vs $) and GST rate options.
    """
    centers_info = await db.centers.find(
        {},
        {"_id": 0, "code": 1, "name": 1, "country": 1, "is_india_center": 1}
    ).sort("code", 1).to_list(100)

    # Be defensive: if a legacy doc is missing is_india_center, infer from
    # country (default → India).
    for c in centers_info:
        if "is_india_center" not in c or c.get("is_india_center") is None:
            country = (c.get("country") or "India").strip()
            c["is_india_center"] = country.lower() == "india"
        if not c.get("country"):
            c["country"] = "India" if c["is_india_center"] else "Australia"

    return {"centers": centers_info}

@router.get("/debug-data")
async def debug_sales_data():
    """Debug endpoint to check if sales data exists"""
    try:
        sales_count = await db.daily_sales.count_documents({})
        expenses_count = await db.expenses.count_documents({})
        centers = await db.daily_sales.distinct("center")
        
        # Get date range
        latest = await db.daily_sales.find_one({}, {"date": 1, "_id": 0}, sort=[("date", -1)])
        oldest = await db.daily_sales.find_one({}, {"date": 1, "_id": 0}, sort=[("date", 1)])
        
        return {
            "status": "ok",
            "sales_count": sales_count,
            "expenses_count": expenses_count,
            "centers": centers,
            "date_range": {
                "oldest": oldest.get("date") if oldest else None,
                "latest": latest.get("date") if latest else None
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/seed-production-data")
async def seed_production_data(data: dict = {}):
    """
    ONE-TIME USE: Seed production database with ALL data.
    Loads from production_seed_data.json which contains:
    - 2,238 daily sales records (all 8 centers)
    - 2,819 expense records
    - 12 managers with roles
    - 10 centers
    - 35 expense head categories
    """
    import json
    
    # Simple secret key check (so only you can run this)
    secret = data.get("secret", "")
    force = data.get("force", False)
    
    if secret != "PURNABRAMHA2024SEED":
        # Also allow Super Admin token
        token = data.get("token")
        if token:
            session = verify_token(token) if verify_token else None
            if not session or not session.get("is_super_admin"):
                raise HTTPException(403, "Invalid secret or not Super Admin")
        else:
            raise HTTPException(403, "Secret key required")
    
    try:
        # Check if data already exists (unless force=True)
        existing_sales = await db.daily_sales.count_documents({})
        if existing_sales > 100 and not force:
            return {
                "status": "skipped",
                "message": f"Database already has {existing_sales} sales records. Use force=True to overwrite.",
                "sales_count": existing_sales
            }
        
        # Load comprehensive seed file
        seed_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "production_seed_data.json")
        
        if not os.path.exists(seed_file):
            return {"status": "error", "message": "Seed file not found. Please contact support."}
        
        with open(seed_file, 'r') as f:
            seed_data = json.load(f)
        
        results = {"inserted": {}, "errors": []}
        
        # Import daily_sales
        if seed_data.get("daily_sales"):
            await db.daily_sales.delete_many({})
            result = await db.daily_sales.insert_many(seed_data["daily_sales"])
            results["inserted"]["daily_sales"] = len(result.inserted_ids)
            logger.info(f"Inserted {len(result.inserted_ids)} daily_sales records")
        
        # Import expenses
        if seed_data.get("expenses"):
            await db.expenses.delete_many({})
            result = await db.expenses.insert_many(seed_data["expenses"])
            results["inserted"]["expenses"] = len(result.inserted_ids)
            logger.info(f"Inserted {len(result.inserted_ids)} expense records")
        
        # Import managers (upsert by center+email to preserve existing data)
        if seed_data.get("managers"):
            for mgr in seed_data["managers"]:
                await db.managers.update_one(
                    {"center": mgr.get("center"), "email": mgr.get("email")},
                    {"$set": mgr},
                    upsert=True
                )
            results["inserted"]["managers"] = len(seed_data["managers"])
            logger.info(f"Upserted {len(seed_data['managers'])} manager records")
        
        # Import centers (upsert by code)
        if seed_data.get("centers"):
            for center in seed_data["centers"]:
                await db.centers.update_one(
                    {"code": center.get("code")},
                    {"$set": center},
                    upsert=True
                )
            results["inserted"]["centers"] = len(seed_data["centers"])
            logger.info(f"Upserted {len(seed_data['centers'])} center records")
        
        # Import expense_heads (upsert by name)
        if seed_data.get("expense_heads"):
            for head in seed_data["expense_heads"]:
                await db.expense_heads.update_one(
                    {"name": head.get("name")},
                    {"$set": head},
                    upsert=True
                )
            results["inserted"]["expense_heads"] = len(seed_data["expense_heads"])
            logger.info(f"Upserted {len(seed_data['expense_heads'])} expense_heads records")
        
        return {
            "status": "success",
            "message": "Production database seeded successfully with ALL data!",
            "inserted": results["inserted"],
            "source": seed_data.get("exported_at", "unknown")
        }
        
    except Exception as e:
        logger.error(f"Seed error: {str(e)}")
        return {"status": "error", "message": str(e)}

# =======================================
# EXPENSE HEADS MASTER CRUD
# =======================================

class ExpenseHeadCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    is_active: bool = True

class ExpenseHeadUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("/expense-heads")
async def get_expense_heads():
    """Get all expense heads from master table"""
    heads = await db.expense_heads.find({}, {"_id": 0}).to_list(200)
    
    if not heads:
        # Return standard types if no custom heads exist
        standard_heads = [
            {"name": "GROCERY", "description": "Daily grocery items", "is_active": True},
            {"name": "DAIRY PRODUCTS", "description": "Milk, curd, paneer etc.", "is_active": True},
            {"name": "FRUITS & VEGETABLE", "description": "Fresh fruits and vegetables", "is_active": True},
            {"name": "WATER CAN / BOTTLE", "description": "Drinking water supplies", "is_active": True},
            {"name": "CYLINDER", "description": "Gas cylinders", "is_active": True},
            {"name": "PAV", "description": "Bread/Pav supplies", "is_active": True},
            {"name": "PACKAGING MATERIAL", "description": "Takeaway containers, bags", "is_active": True},
            {"name": "CELEBRATION EXPENSES", "description": "Festival and event expenses", "is_active": True},
            {"name": "MEDIA & ADVERTISEMENT", "description": "Marketing and ads", "is_active": True},
            {"name": "RESTAURANT GENERAL EXPENSES", "description": "Miscellaneous restaurant expenses", "is_active": True},
            {"name": "REPAIR & MAINTENANCE", "description": "Equipment and property repairs", "is_active": True},
            {"name": "SALARY", "description": "Staff salary payments", "is_active": True},
            {"name": "ADVANCE", "description": "Salary advances to staff", "is_active": True},
            {"name": "RENT", "description": "Shop/property rent", "is_active": True},
            {"name": "ELECTRICITY", "description": "Electricity bills", "is_active": True},
            {"name": "STATIONARY & PACKAGING", "description": "Office supplies and packaging", "is_active": True},
            {"name": "OVER TIME", "description": "Staff overtime payments", "is_active": True},
            {"name": "STAFF ROOM RENT", "description": "Staff accommodation rent", "is_active": True},
            {"name": "EMI / LOAN INSTALMENT", "description": "Loan EMI payments", "is_active": True},
            {"name": "RENT PAID SHOP", "description": "Main shop rent", "is_active": True},
        ]
        return {"expense_heads": standard_heads}
    
    return {"expense_heads": heads}

@router.post("/expense-heads")
async def create_expense_head(req: ExpenseHeadCreate, token: str):
    """Create a new expense head"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if not (session.get("is_super_admin") or session.get("is_admin")):
        raise HTTPException(403, "Only Admin can manage expense heads")
    
    # Check if already exists
    existing = await db.expense_heads.find_one({"name": req.name.upper()})
    if existing:
        raise HTTPException(400, f"Expense head '{req.name}' already exists")
    
    record = {
        "name": req.name.upper(),
        "description": req.description,
        "is_active": req.is_active,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": session.get("managerName", "Unknown")
    }
    
    result = await db.expense_heads.insert_one(record)
    record["_id"] = str(result.inserted_id)
    
    logger.info(f"Expense head created: {req.name} by {session.get('managerName')}")
    
    return {"success": True, "message": "Expense head created", "expense_head": record}

@router.put("/expense-heads/{head_name}")
async def update_expense_head(head_name: str, req: ExpenseHeadUpdate, token: str):
    """Update an expense head"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if not (session.get("is_super_admin") or session.get("is_admin")):
        raise HTTPException(403, "Only Admin can manage expense heads")
    
    # Find existing
    existing = await db.expense_heads.find_one({"name": head_name.upper()})
    if not existing:
        raise HTTPException(404, f"Expense head '{head_name}' not found")
    
    update_data = {k: v for k, v in req.dict().items() if v is not None}
    
    if "name" in update_data:
        update_data["name"] = update_data["name"].upper()
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        update_data["updated_by"] = session.get("managerName", "Unknown")
        
        await db.expense_heads.update_one(
            {"name": head_name.upper()},
            {"$set": update_data}
        )
    
    logger.info(f"Expense head updated: {head_name} by {session.get('managerName')}")
    
    return {"success": True, "message": "Expense head updated"}

@router.delete("/expense-heads/{head_name}")
async def delete_expense_head(head_name: str, token: str):
    """Delete an expense head"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if not (session.get("is_super_admin") or session.get("is_admin")):
        raise HTTPException(403, "Only Admin can manage expense heads")
    
    result = await db.expense_heads.delete_one({"name": head_name.upper()})
    
    if result.deleted_count == 0:
        raise HTTPException(404, f"Expense head '{head_name}' not found")
    
    logger.info(f"Expense head deleted: {head_name} by {session.get('managerName')}")
    
    return {"success": True, "message": "Expense head deleted"}


# =======================================
# PERTH EXCEL UPLOAD
# Import Perth Sales Data from Excel without modification
# =======================================

import io

class PerthExcelUploadRequest(BaseModel):
    token: str

# Perth Excel column mapping (based on actual Perth Excel structure)
PERTH_COLUMN_MAP = {
    'A': 'date',
    'B': 'opening_balance',
    'C': 'deposited_in_bank',
    'D': 'petty_cash_opening',
    'E': 'cash_receipts',
    'F': 'sale_of_day',  # Header column
    'G': 'sale_pbm',
    'H': 'sale_other',
    'I': 'total_sale',
    'J': 'card_anz',  # Card ANZ/COMP BANK (equivalent to card_idfc)
    'K': 'takeaway',  # Takeaway (Pickups) - Card/Cash
    'L': 'doordash',  # DoorDash
    'M': 'ubereats',  # UberEats
    'N': 'bharat_pay',
    'O': 'due_amount',
    'P': 'total_online_sale',
    'Q': 'total_cash_sale',
    'R': 'cash_expense',
    'S': 'closing_balance',
    'T': 'cash_in_hand',
    'U': 'to_deposit_in_bank',
    'V': 'difference_for_day',
    'W': 'petty_cash_closing',
}

@router.post("/perth/upload-excel")
async def upload_perth_excel(token: str, center: str = "PB-PERTH", file: UploadFile = File(...)):
    """
    Upload international center Sales Excel file and import data WITHOUT modification.
    Preserves original structure, spelling, and currency.
    """
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Only Super Admin or Admin can upload Excel
    if not (session.get("is_super_admin") or session.get("is_admin")):
        raise HTTPException(403, "Only admins can upload Perth Excel data")
    
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "Only Excel files (.xlsx, .xls) are allowed")
    
    try:
        import openpyxl
        from datetime import datetime as dt
        
        # Read the uploaded file
        contents = await file.read()
        workbook = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
        
        # Look for the daily sales sheet
        target_sheet = None
        for sheet_name in workbook.sheetnames:
            if 'DAILY SALE' in sheet_name.upper():
                target_sheet = workbook[sheet_name]
                break
        
        if not target_sheet:
            # If no specific sheet found, try the active sheet
            target_sheet = workbook.active
        
        logger.info(f"Processing Perth Excel: {file.filename}, Sheet: {target_sheet.title}")
        
        # Parse rows - skip first 2 header rows
        imported_count = 0
        skipped_count = 0
        errors = []
        
        for row_idx, row in enumerate(target_sheet.iter_rows(min_row=4, values_only=True), start=4):
            # Skip if no date
            if not row[0]:
                skipped_count += 1
                continue
            
            try:
                # Parse date (column A)
                date_val = row[0]
                if isinstance(date_val, dt):
                    date_str = date_val.strftime('%Y-%m-%d')
                elif isinstance(date_val, str):
                    # Try to parse common date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d %H:%M:%S']:
                        try:
                            date_str = dt.strptime(date_val.split()[0], fmt).strftime('%Y-%m-%d')
                            break
                        except:
                            continue
                    else:
                        date_str = str(date_val).split()[0]
                else:
                    skipped_count += 1
                    continue
                
                # Helper to safely get numeric values
                def safe_float(val):
                    if val is None:
                        return 0.0
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return 0.0
                
                # Check if row has any actual data (not just a date)
                has_data = any(row[i] for i in range(1, min(len(row), 20)) if row[i])
                if not has_data:
                    skipped_count += 1
                    continue
                
                # Create daily sale record - PRESERVE ALL VALUES EXACTLY AS IS
                sale_record = {
                    "center": center.upper(),  # Center code from request
                    "date": date_str,
                    "opening_balance": safe_float(row[1]),  # B
                    "deposited_in_bank": safe_float(row[2]),  # C
                    "petty_cash_opening": safe_float(row[3]),  # D
                    "cash_receipts": safe_float(row[4]),  # E
                    "sale_pbm": safe_float(row[6]),  # G - PBM
                    "sale_other": safe_float(row[7]),  # H - Other Products
                    "total_sale": safe_float(row[8]),  # I - Total Sale of the Day
                    
                    # Perth-specific online payment columns
                    "card_idfc": safe_float(row[9]),  # J - Card ANZ (mapped to card_idfc)
                    "takeaway": safe_float(row[10]),  # K - Takeaway (Perth-specific)
                    "doordash": safe_float(row[11]),  # L - DoorDash (Perth-specific)
                    "ubereats": safe_float(row[12]),  # M - UberEats (Perth-specific)
                    "bharat_pay": safe_float(row[13]),  # N - BharatPay
                    "due_amount": safe_float(row[14]),  # O
                    "total_online_sale": safe_float(row[15]),  # P
                    "total_cash_sale": safe_float(row[16]),  # Q
                    
                    # Expenses and closing
                    "cash_expense": safe_float(row[17]),  # R
                    "closing_balance": safe_float(row[18]),  # S
                    "cash_in_hand": safe_float(row[19]),  # T - Perth-specific
                    "to_deposit_in_bank": safe_float(row[20]) if len(row) > 20 else 0,  # U
                    "difference_for_day": safe_float(row[21]) if len(row) > 21 else 0,  # V
                    "petty_cash_closing": safe_float(row[22]) if len(row) > 22 else 0,  # W
                    
                    # Metadata
                    "source": "excel_upload",
                    "source_file": file.filename,
                    "currency": "AUD",  # Australian Dollars
                    "gst_rate": 10,  # Perth uses 10% inclusive GST
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    "uploaded_by": session.get("managerName", "Unknown"),
                }
                
                # Calculate GST (10% inclusive for Perth)
                total_sale = sale_record["total_sale"]
                # Exclude DoorDash and UberEats from GST (like Swiggy/Zomato)
                gst_applicable = max(0, total_sale - sale_record.get("doordash", 0) - sale_record.get("ubereats", 0))
                sale_record["gst_amount"] = round(gst_applicable / 11, 2)  # 10% inclusive
                
                # Upsert - update if exists, insert if new
                await db.daily_sales.update_one(
                    {"center": center.upper(), "date": date_str},
                    {"$set": sale_record},
                    upsert=True
                )
                imported_count += 1
                
            except Exception as row_error:
                errors.append(f"Row {row_idx}: {str(row_error)}")
                logger.error(f"Perth Excel row {row_idx} error: {row_error}")
        
        logger.info(f"Perth Excel import complete: {imported_count} records imported, {skipped_count} skipped")
        
        return {
            "success": True,
            "message": "International center Excel imported successfully",
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "errors": errors[:10] if errors else [],
            "center": center.upper(),
            "currency": "AUD ($)" if is_perth_center(center) else "INR (₹)",
            "gst_rate": "10% inclusive" if is_perth_center(center) else "GST as configured"
        }
        
    except ImportError:
        raise HTTPException(500, "openpyxl library not installed. Please install it.")
    except Exception as e:
        logger.error(f"Perth Excel upload error: {e}")
        raise HTTPException(500, f"Excel processing error: {str(e)}")


# =======================================
# SALES UPLOAD FEATURE FOR CENTER MANAGERS
# =======================================

@router.get("/upload-template")
async def download_upload_template(token: str):
    """Download Excel template for bulk sales data upload"""
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from io import BytesIO
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Sales Data"
        
        # Header styling
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True, size=11)
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Define columns with descriptions
        columns = [
            ("Date", "YYYY-MM-DD format (e.g., 2025-01-15)"),
            ("Opening Balance", "Cash opening balance for the day"),
            ("Withdrawal", "Cash receipts / Withdrawal from bank"),
            ("Total Sale", "Total sale amount for the day"),
            ("Card/IDFC", "Card/IDFC payments"),
            ("Bharat Pay/UPI", "Bharat Pay / UPI payments"),
            ("Swiggy", "Swiggy order amounts"),
            ("Zomato", "Zomato order amounts"),
            ("DoorDash", "DoorDash order amounts (if applicable)"),
            ("Other Online/Pickup", "Other online orders / Takeaway / Pickups"),
            ("Number of Guests", "Total guests (pax) for the day"),
            ("Number of Bills", "Total bills (excluding Swiggy/Zomato)"),
            ("Petty Cash Opening", "Petty cash opening balance"),
            ("Notes", "Any notes for the day (optional)")
        ]
        
        # Write headers
        for col_idx, (col_name, _) in enumerate(columns, 1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = thin_border
            ws.column_dimensions[cell.column_letter].width = 18
        
        # Add instruction row
        ws.insert_rows(1)
        ws.merge_cells('A1:N1')
        instruction_cell = ws['A1']
        instruction_cell.value = "SALES DATA UPLOAD TEMPLATE - Fill data starting from row 3. Date column is required. Leave cells empty if no value."
        instruction_cell.font = Font(bold=True, color="FF0000", size=12)
        instruction_cell.alignment = Alignment(horizontal='center')
        
        # Add column descriptions in row 3
        for col_idx, (_, description) in enumerate(columns, 1):
            cell = ws.cell(row=3, column=col_idx, value=description)
            cell.font = Font(italic=True, size=9, color="666666")
            cell.alignment = Alignment(wrap_text=True)
        
        # Add sample data row
        sample_data = [
            "2025-01-15", 5000, 10000, 50000, 8000, 5000, 
            12000, 10000, 0, 3000, 85, 45, 2000, "Sample day"
        ]
        for col_idx, value in enumerate(sample_data, 1):
            cell = ws.cell(row=4, column=col_idx, value=value)
            cell.border = thin_border
        
        # Create Expenses sheet
        ws_exp = wb.create_sheet("Expenses")
        exp_columns = [
            ("Date", "YYYY-MM-DD format"),
            ("Description", "Expense description"),
            ("Amount", "Expense amount"),
            ("Category", "GROCERY, SALARY, MAINTENANCE, UTILITY, MARKETING, MISC, OTHER"),
            ("Payment Mode", "CASH, ONLINE UPI, ONLINE NEFT/IMPS"),
            ("Notes", "Additional notes (optional)")
        ]
        
        for col_idx, (col_name, _) in enumerate(exp_columns, 1):
            cell = ws_exp.cell(row=1, column=col_idx, value=col_name)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
            ws_exp.column_dimensions[cell.column_letter].width = 20
        
        # Add expense descriptions
        for col_idx, (_, description) in enumerate(exp_columns, 1):
            cell = ws_exp.cell(row=2, column=col_idx, value=description)
            cell.font = Font(italic=True, size=9, color="666666")
        
        # Sample expense
        exp_sample = ["2025-01-15", "Vegetables purchase", 5000, "GROCERY", "CASH", "Weekly vegetables"]
        for col_idx, value in enumerate(exp_sample, 1):
            cell = ws_exp.cell(row=3, column=col_idx, value=value)
            cell.border = thin_border
        
        # Save to buffer
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        return Response(
            content=buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="Sales_Upload_Template.xlsx"'}
        )
        
    except Exception as e:
        logger.error(f"Template generation error: {e}")
        raise HTTPException(500, f"Error generating template: {str(e)}")


@router.post("/upload-data")
async def upload_sales_data(
    token: str = Form(...),
    center: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload sales data from Excel file.
    This will DELETE existing data for the dates in the file and INSERT new data.
    """
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Check if user has access to this center
    user_center = session.get("center", "")
    is_super_admin = session.get("is_super_admin", False)
    is_admin = session.get("is_admin", False)
    
    # Center managers can only upload for their own center
    if not is_super_admin and not is_admin and user_center != center:
        raise HTTPException(403, f"You can only upload data for your center: {user_center}")
    
    # Check if upload is enabled for this center
    center_doc = await db.centers.find_one({"code": center}, {"_id": 0})
    if not center_doc:
        raise HTTPException(404, f"Center '{center}' not found")
    
    # Check upload permission (default to False if not set)
    upload_enabled = center_doc.get("sales_upload_enabled", False)
    if not upload_enabled and not is_super_admin:
        raise HTTPException(403, "Sales upload is not enabled for this center. Contact MGT to enable.")
    
    try:
        from openpyxl import load_workbook
        from io import BytesIO
        
        # Read file content
        content = await file.read()
        wb = load_workbook(BytesIO(content))
        
        results = {
            "sales": {"imported": 0, "deleted": 0, "errors": []},
            "expenses": {"imported": 0, "deleted": 0, "errors": []}
        }
        
        # Process Sales Data sheet
        if "Sales Data" in wb.sheetnames:
            ws = wb["Sales Data"]
            dates_to_delete = set()
            sales_records = []
            
            # Find header row (row 2 after instruction row)
            header_row = 2
            headers = [cell.value for cell in ws[header_row]]
            
            # Map column indices
            col_map = {}
            for idx, header in enumerate(headers):
                if header:
                    col_map[header.lower().strip()] = idx
            
            # Process data rows (starting from row 4 - after headers and descriptions)
            for row_idx, row in enumerate(ws.iter_rows(min_row=4, values_only=True), start=4):
                if not row[0]:  # Skip empty rows
                    continue
                
                try:
                    # Parse date
                    date_val = row[0]
                    if isinstance(date_val, datetime):
                        date_str = date_val.strftime("%Y-%m-%d")
                    else:
                        date_str = str(date_val).strip()
                        # Validate date format
                        datetime.strptime(date_str, "%Y-%m-%d")
                    
                    dates_to_delete.add(date_str)
                    
                    # Extract values with defaults
                    def get_float(idx, default=0):
                        try:
                            val = row[idx] if idx < len(row) else None
                            return float(val) if val is not None else default
                        except:
                            return default
                    
                    def get_int(idx, default=0):
                        try:
                            val = row[idx] if idx < len(row) else None
                            return int(val) if val is not None else default
                        except:
                            return default
                    
                    # Build sales record
                    record = {
                        "center": center,
                        "date": date_str,
                        "opening_balance": get_float(1),
                        "cash_receipts": get_float(2),  # Withdrawal
                        "total_sale": get_float(3),
                        "card_idfc": get_float(4),
                        "bharat_pay": get_float(5),
                        "swiggy": get_float(6),
                        "zomato": get_float(7),
                        "doordash": get_float(8),
                        "online_other": get_float(9),
                        "num_guests": get_int(10),
                        "num_bills": get_int(11),
                        "petty_cash_opening": get_float(12),
                        "notes": str(row[13]) if len(row) > 13 and row[13] else "",
                        "uploaded_at": datetime.now(timezone.utc).isoformat(),
                        "uploaded_by": session.get("managerName", "")
                    }
                    
                    # Calculate derived fields
                    total_online = (record["card_idfc"] + record["bharat_pay"] + 
                                  record["swiggy"] + record["zomato"] + 
                                  record["doordash"] + record["online_other"])
                    record["total_online_sale"] = total_online
                    record["total_cash_sale"] = record["total_sale"] - total_online

                    # GST = inclusive 5% (India) / 10% (intl) carved out of
                    # eligible base. Routed through the canonical helper so
                    # this row's `gst_amount` matches what PIB / MIS / Center
                    # Accounts compute on the fly. Previously this stored
                    # ``eligible × rate`` (non-inclusive on-top), giving
                    # ₹48,439.80 vs the correct ₹46,133.14 for PB-DV-style
                    # data — a silent ₹2,306 over-statement per row.
                    from utils.gst import eligible_base_from_daily_row, carve_inclusive_gst, gst_rate_for
                    _rate = gst_rate_for(None, record.get("center"))
                    record["gst_amount"] = carve_inclusive_gst(eligible_base_from_daily_row(record), _rate)
                    
                    # Averages
                    if record["num_guests"] > 0:
                        record["avg_per_pax"] = round(record["total_sale"] / record["num_guests"], 2)
                    if record["num_bills"] > 0:
                        record["avg_per_bill"] = round(record["total_sale"] / record["num_bills"], 2)
                    
                    sales_records.append(record)
                    
                except Exception as e:
                    results["sales"]["errors"].append(f"Row {row_idx}: {str(e)}")
            
            # Delete existing records for those dates
            if dates_to_delete:
                delete_result = await db.daily_sales.delete_many({
                    "center": center,
                    "date": {"$in": list(dates_to_delete)}
                })
                results["sales"]["deleted"] = delete_result.deleted_count
            
            # Insert new records
            if sales_records:
                await db.daily_sales.insert_many(sales_records)
                results["sales"]["imported"] = len(sales_records)
        
        # Process Expenses sheet
        if "Expenses" in wb.sheetnames:
            ws_exp = wb["Expenses"]
            expense_dates = set()
            expense_records = []
            
            for row_idx, row in enumerate(ws_exp.iter_rows(min_row=3, values_only=True), start=3):
                if not row[0]:
                    continue
                
                try:
                    # Parse date
                    date_val = row[0]
                    if isinstance(date_val, datetime):
                        date_str = date_val.strftime("%Y-%m-%d")
                    else:
                        date_str = str(date_val).strip()
                        datetime.strptime(date_str, "%Y-%m-%d")
                    
                    expense_dates.add(date_str)
                    
                    expense_record = {
                        "center": center,
                        "date": date_str,
                        "description": str(row[1]) if row[1] else "",
                        "amount": float(row[2]) if row[2] else 0,
                        "expense_type": str(row[3]).upper() if row[3] else "OTHER",
                        "payment_mode": str(row[4]).upper() if row[4] else "CASH",
                        "notes": str(row[5]) if len(row) > 5 and row[5] else "",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "created_by": session.get("managerName", "")
                    }
                    expense_records.append(expense_record)
                    
                except Exception as e:
                    results["expenses"]["errors"].append(f"Row {row_idx}: {str(e)}")
            
            # Delete existing expenses for those dates
            if expense_dates:
                delete_result = await db.expenses.delete_many({
                    "center": center,
                    "date": {"$in": list(expense_dates)}
                })
                results["expenses"]["deleted"] = delete_result.deleted_count
            
            # Insert new expenses
            if expense_records:
                await db.expenses.insert_many(expense_records)
                results["expenses"]["imported"] = len(expense_records)
        
        # Log the upload
        await db.upload_logs.insert_one({
            "center": center,
            "uploaded_by": session.get("managerName", ""),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "file_name": file.filename,
            "results": results
        })
        
        return {
            "success": True,
            "message": f"Upload completed for center {center}",
            "results": results,
            "warning": "Existing data for uploaded dates has been replaced with new data."
        }
        
    except Exception as e:
        logger.error(f"Sales upload error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Upload error: {str(e)}")


@router.post("/upload-custom-format")
async def upload_custom_format_data(
    token: str = Form(...),
    center: str = Form(...),
    from_year: int = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload sales data from custom Excel format (like SN DAILY-SALE N CASH SUMMERY).
    Looks for 'DAILY SALE' sheet or monthly sheets with sales data.
    """
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    user_center = session.get("center", "")
    is_super_admin = session.get("is_super_admin", False)
    is_admin = session.get("is_admin", False)
    
    if not is_super_admin and not is_admin and user_center != center:
        raise HTTPException(403, f"You can only upload data for your center: {user_center}")
    
    try:
        from openpyxl import load_workbook
        from io import BytesIO
        import re
        import pandas as pd
        
        content = await file.read()
        wb = load_workbook(BytesIO(content), data_only=True)
        
        # Create pandas ExcelFile for expense sheet parsing
        xls = pd.ExcelFile(BytesIO(content))
        
        results = {
            "sales": {"imported": 0, "deleted": 0, "errors": [], "sheets_processed": []},
        }
        
        all_dates_to_delete = set()
        all_sales_records = {}  # Use dict to dedupe by center_date key
        
        # First, try to find a "DAILY SALE" or "CASH SUMMERY" sheet
        daily_sale_sheet = None
        for sheet_name in wb.sheetnames:
            if 'DAILY SALE' in sheet_name.upper() or 'CASH SUMM' in sheet_name.upper():
                daily_sale_sheet = sheet_name
                break
        
        if daily_sale_sheet:
            # Process the DAILY SALE sheet
            logger.info(f"Found daily sale sheet: {daily_sale_sheet}")
            results["sales"]["sheets_processed"].append(daily_sale_sheet)
            
            ws = wb[daily_sale_sheet]
            
            # Find the header rows - this sheet has 2 header rows
            # Row 1: DATE, DEPOSITED IN BANK, CASH RECEIPTS, TOTAL SALE...
            # Row 2: OPENING BALANCE, PETTY CASH, SALE OF THE DAY, CARD IDFC, BHARAT PAY, SWIGGY...
            
            # Combine headers from first 2 rows
            row1 = list(ws.iter_rows(min_row=1, max_row=1, values_only=True))[0]
            row2 = list(ws.iter_rows(min_row=2, max_row=2, values_only=True))[0]
            
            # Build column mapping
            col_map = {}
            for i, (h1, h2) in enumerate(zip(row1, row2)):
                header = str(h2 or h1 or '').upper().strip()
                if header:
                    col_map[header] = i
            
            logger.info(f"Column map: {col_map}")
            
            # Map to our field names
            def find_col(keywords):
                for kw in keywords:
                    for col_name, idx in col_map.items():
                        if kw in col_name:
                            return idx
                return None
            
            # Date is always first column
            date_col = 0
            opening_col = find_col(['OPENING BALANCE', 'OPENING BAL'])
            petty_col = find_col(['PETTY CASH'])
            cash_receipts_col = find_col(['CASH RECEIPTS', 'CASH RECEIPT', 'WITHDRAWAL'])
            deposited_col = find_col(['DEPOSITED IN BANK', 'DEPOSITED', 'DEPOSIT'])
            total_sale_col = find_col(['TOTAL SALE OF THE DAY', 'TOTAL SALE'])
            card_col = find_col(['CARD', 'IDFC', 'EFTPOS'])
            bharat_pay_col = find_col(['BHARAT PAY', 'UPI', 'PAYTM'])
            swiggy_col = find_col(['SWIGGY'])
            zomato_col = find_col(['ZOMATO'])
            doordash_col = find_col(['DOORDASH', 'DOOR DASH'])
            online_col = find_col(['ONLINE', 'TOTAL ONLINE'])
            cash_expense_col = find_col(['CASH EXPAN', 'CASH EXPENSE', 'CASH EXP'])
            due_col = find_col(['DUE AMOUNT', 'DUE'])
            
            # Process data rows (starting from row 4, since row 3 is usually empty)
            for row_idx, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
                if not row or not row[date_col]:
                    continue
                
                try:
                    date_val = row[date_col]
                    if isinstance(date_val, datetime):
                        date_str = date_val.strftime("%Y-%m-%d")
                        date_year = date_val.year
                    else:
                        continue
                    
                    # Filter by from_year
                    if date_year < from_year:
                        continue
                    
                    all_dates_to_delete.add(date_str)
                    
                    def get_val(col_idx, default=0):
                        if col_idx is None:
                            return default
                        try:
                            val = row[col_idx] if col_idx < len(row) else None
                            if val is None or str(val).strip() == '':
                                return default
                            if isinstance(val, str) and (val.startswith('=') or val.startswith('#')):
                                return default
                            return float(val)
                        except:
                            return default
                    
                    total_sale = get_val(total_sale_col)
                    if total_sale <= 0:
                        continue  # Skip rows with no sale
                    
                    record = {
                        "center": center,
                        "date": date_str,
                        "opening_balance": get_val(opening_col),
                        "petty_cash_opening": get_val(petty_col),
                        "deposited_in_bank": get_val(deposited_col),
                        "cash_receipts": get_val(cash_receipts_col),
                        "total_sale": total_sale,
                        "card_idfc": get_val(card_col),
                        "bharat_pay": get_val(bharat_pay_col),
                        "swiggy": get_val(swiggy_col),
                        "zomato": get_val(zomato_col),
                        "doordash": get_val(doordash_col),
                        "online_other": get_val(online_col),
                        "cash_expense": get_val(cash_expense_col),
                        "due_amount": get_val(due_col),
                        "num_guests": 0,
                        "num_bills": 0,
                        "uploaded_at": datetime.now(timezone.utc).isoformat(),
                        "uploaded_by": session.get("managerName", "")
                    }
                    
                    # Calculate derived fields
                    total_online = (record["card_idfc"] + record["bharat_pay"] + 
                                  record["swiggy"] + record["zomato"] + 
                                  record["doordash"] + record["online_other"])
                    record["total_online_sale"] = total_online
                    record["total_cash_sale"] = max(0, record["total_sale"] - total_online)
                    # GST: inclusive carve via canonical helper (single source of truth)
                    from utils.gst import eligible_base_from_daily_row, carve_inclusive_gst, gst_rate_for
                    _rate = gst_rate_for(None, record.get("center"))
                    record["gst_amount"] = carve_inclusive_gst(eligible_base_from_daily_row(record), _rate)
                    
                    # Calculate closing balance + petty cash closing (TWO SEPARATE TRACKS)
                    ob = record["opening_balance"]
                    cr = record["cash_receipts"]
                    dep = record["deposited_in_bank"]
                    ce = record["cash_expense"]
                    cash_sale = record["total_sale"] - total_online
                    # Track A: Closing = Opening + Cash Sale - Deposited
                    record["closing_balance"] = ob + max(0, cash_sale) - dep
                    record["to_deposit_in_bank"] = record["closing_balance"]
                    # Track B: Petty = Petty Opening + Cash Withdrawal - Cash Expenses
                    pco = record["petty_cash_opening"]
                    record["petty_cash_closing"] = pco + cr - ce
                    
                    all_sales_records[f"{center}_{date_str}"] = record
                    
                except Exception as e:
                    results["sales"]["errors"].append(f"Row {row_idx}: {str(e)}")
        
        # If no daily sale sheet was found or processed, try monthly sheets
        if not daily_sale_sheet or len(all_sales_records) == 0:
            # Fall back to looking for monthly sheets with sales data
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
            }
        
            for sheet_name in wb.sheetnames:
                # Try to parse sheet name for month/year (e.g., "FEB 26", "JAN.19", "MAR 2017")
                sheet_lower = sheet_name.lower().strip()
                
                # Pattern: "MMM YY" or "MMM.YY" or "MMM YYYY" or "MMMM.YYYY"
                match = re.match(r'([a-z]+)[\s\.\-]*(\d{2,4})', sheet_lower)
                if not match:
                    continue
                
                month_str = match.group(1)
                year_str = match.group(2)
                
                if month_str not in month_map:
                    continue
                
                month_num = month_map[month_str]
                
                # Convert 2-digit year to 4-digit
                if len(year_str) == 2:
                    year_num = int(year_str)
                    if year_num >= 0 and year_num <= 30:
                        year_num += 2000
                    else:
                        year_num += 1900
                else:
                    year_num = int(year_str)
                
                # Filter by from_year
                if year_num < from_year:
                    continue
                
                logger.info(f"Processing sheet: {sheet_name} -> {month_num}/{year_num}")
                results["sales"]["sheets_processed"].append(sheet_name)
                
                ws = wb[sheet_name]
                
                # Find header row by looking for "DATE" column
                header_row_idx = None
                col_map = {}
                
                for row_idx, row in enumerate(ws.iter_rows(max_row=10, values_only=True), start=1):
                    row_lower = [str(c).lower().strip() if c else "" for c in row]
                    if "date" in row_lower:
                        header_row_idx = row_idx
                        for col_idx, cell in enumerate(row):
                            if cell:
                                col_map[str(cell).lower().strip()] = col_idx
                        break
                
                if header_row_idx is None:
                    results["sales"]["errors"].append(f"Sheet '{sheet_name}': Could not find DATE header")
                    continue
                
                # Map custom columns to standard columns
                def find_col(keywords):
                    for kw in keywords:
                        for col_name, idx in col_map.items():
                            if kw in col_name:
                                return idx
                    return None
                
                date_col = find_col(['date'])
                opening_col = find_col(['opening balance', 'opening bal'])
                petty_col = find_col(['petty cash', 'petty'])
                cash_receipts_col = find_col(['cash receipts', 'cash receipt', 'withdrawal'])
                deposited_col = find_col(['deposited in bank', 'deposited', 'deposit'])
                total_sale_col = find_col(['total sale', 'sale of the day', 'total'])
                card_col = find_col(['card', 'idfc', 'card idfc', 'eftpos'])
                bharat_pay_col = find_col(['bharat pay', 'bharatpay', 'upi'])
                swiggy_col = find_col(['swiggy'])
                zomato_col = find_col(['zomato'])
                doordash_col = find_col(['doordash', 'door dash', 'dd'])
                online_col = find_col(['online', 'other online', 'pickup'])
                guests_col = find_col(['guest', 'pax', 'no of guest', 'number of guest', 'covers'])
                bills_col = find_col(['bill', 'no of bill', 'number of bill', 'transactions'])
                cash_expense_col = find_col(['cash expan', 'cash expense', 'cash exp'])
                due_col = find_col(['due amount', 'due'])
                
                if date_col is None:
                    results["sales"]["errors"].append(f"Sheet '{sheet_name}': No DATE column found")
                    continue
                
                # Process data rows
                for row_idx, row in enumerate(ws.iter_rows(min_row=header_row_idx + 1, values_only=True), start=header_row_idx + 1):
                    if not row or not row[date_col]:
                        continue
                    
                    try:
                        # Parse date
                        date_val = row[date_col]
                        if isinstance(date_val, datetime):
                            date_str = date_val.strftime("%Y-%m-%d")
                        elif isinstance(date_val, (int, float)):
                            # Excel serial date
                            continue
                        else:
                            date_str = str(date_val).strip()
                            if not date_str or date_str.lower() in ['date', 'none', '']:
                                continue
                            try:
                                datetime.strptime(date_str, "%Y-%m-%d")
                            except Exception:
                                continue
                        
                        # Check if date is within year filter
                        date_year = int(date_str[:4])
                        if date_year < from_year:
                            continue
                        
                        all_dates_to_delete.add(date_str)
                        
                        def get_val(col_idx, default=0):
                            if col_idx is None:
                                return default
                            try:
                                val = row[col_idx] if col_idx < len(row) else None
                                if val is None or str(val).strip() == '':
                                    return default
                                # Handle formulas that show as strings
                                if isinstance(val, str) and val.startswith('='):
                                    return default
                                return float(val)
                            except Exception:
                                return default
                        
                        record = {
                            "center": center,
                            "date": date_str,
                            "opening_balance": get_val(opening_col),
                            "petty_cash_opening": get_val(petty_col),
                            "deposited_in_bank": get_val(deposited_col),
                            "cash_receipts": get_val(cash_receipts_col),
                            "total_sale": get_val(total_sale_col),
                            "card_idfc": get_val(card_col),
                            "bharat_pay": get_val(bharat_pay_col),
                            "swiggy": get_val(swiggy_col),
                            "zomato": get_val(zomato_col),
                            "doordash": get_val(doordash_col),
                            "online_other": get_val(online_col),
                            "cash_expense": get_val(cash_expense_col),
                            "due_amount": get_val(due_col),
                            "num_guests": int(get_val(guests_col)),
                            "num_bills": int(get_val(bills_col)),
                            "uploaded_at": datetime.now(timezone.utc).isoformat(),
                            "uploaded_by": session.get("managerName", "")
                        }
                        
                        # Calculate derived fields
                        total_online = (record["card_idfc"] + record["bharat_pay"] + 
                                      record["swiggy"] + record["zomato"] + 
                                      record["doordash"] + record["online_other"])
                        record["total_online_sale"] = total_online
                        record["total_cash_sale"] = max(0, record["total_sale"] - total_online)
                        # GST: inclusive carve via canonical helper (single source of truth)
                        from utils.gst import eligible_base_from_daily_row, carve_inclusive_gst, gst_rate_for
                        _rate = gst_rate_for(None, record.get("center"))
                        record["gst_amount"] = carve_inclusive_gst(eligible_base_from_daily_row(record), _rate)
                        
                        # Calculate closing balance + petty cash closing (TWO SEPARATE TRACKS)
                        ob = record["opening_balance"]
                        cr = record["cash_receipts"]
                        dep = record["deposited_in_bank"]
                        ce = record["cash_expense"]
                        cash_sale = record["total_sale"] - total_online
                        # Track A: Closing = Opening + Cash Sale - Deposited
                        record["closing_balance"] = ob + max(0, cash_sale) - dep
                        record["to_deposit_in_bank"] = record["closing_balance"]
                        # Track B: Petty = Petty Opening + Cash Withdrawal - Cash Expenses
                        pco = record["petty_cash_opening"]
                        record["petty_cash_closing"] = pco + cr - ce
                        
                        if record["num_guests"] > 0:
                            record["avg_per_pax"] = round(record["total_sale"] / record["num_guests"], 2)
                        if record["num_bills"] > 0:
                            record["avg_per_bill"] = round(record["total_sale"] / record["num_bills"], 2)
                        
                        all_sales_records[f"{center}_{date_str}"] = record
                        
                    except Exception as e:
                        results["sales"]["errors"].append(f"Sheet '{sheet_name}' Row {row_idx}: {str(e)}")
        
        # Delete existing records for those dates
        if all_dates_to_delete:
            delete_result = await db.daily_sales.delete_many({
                "center": center,
                "date": {"$in": list(all_dates_to_delete)}
            })
            results["sales"]["deleted"] = delete_result.deleted_count
        
        # Insert new records (use values from dict to avoid duplicates)
        records_to_insert = list(all_sales_records.values())
        if records_to_insert:
            await db.daily_sales.insert_many(records_to_insert)
            results["sales"]["imported"] = len(records_to_insert)
        
        # =======================================
        # PARSE EXPENSE SHEETS
        # =======================================
        expense_records = []
        expense_sheets_processed = 0
        
        for sheet_name in xls.sheet_names:
            try:
                df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                if df.empty or len(df) < 2:
                    continue
                
                # Check if this is an expense sheet by looking for EXPENCE/EXPENSE in header rows
                is_expense_sheet = False
                header_row_idx = 0
                for idx in range(min(3, len(df))):
                    row_vals = [str(v).strip().upper() for v in df.iloc[idx] if pd.notna(v)]
                    if any('EXPENCE' in v or 'EXPENSE' in v for v in row_vals):
                        is_expense_sheet = True
                        header_row_idx = idx
                        break
                
                if not is_expense_sheet:
                    continue
                
                # Find column indices
                headers = [str(v).strip().upper() if pd.notna(v) else '' for v in df.iloc[header_row_idx]]
                
                def find_exp_col(keywords, exclude_keywords=None):
                    """Find first column whose header contains any keyword
                    and does NOT contain any of the exclude_keywords (case-insensitive).
                    """
                    excludes = [e.upper() for e in (exclude_keywords or [])]
                    for kw in keywords:
                        for ci, h in enumerate(headers):
                            if kw.upper() in h and not any(e in h for e in excludes):
                                return ci
                    return None
                
                date_col = find_exp_col(['DATE'])
                # Description column priority:
                #   1) Exact match for EXPENCE/EXPENSE (but NEVER aggregate columns like
                #      EXPENSES HEAD, TOTAL EXPENCE, CASH EXPENCE, ONLINE EXPENCE etc.)
                #   2) Fallback to common alternatives: PARTICULAR, ITEM, DESC, GROCERY, NARRATION
                #   3) Last resort: the column immediately AFTER the DATE column
                desc_col = find_exp_col(
                    ['EXPENCE', 'EXPENSE'],
                    exclude_keywords=['HEAD', 'TOTAL', 'CASH', 'ONLINE', 'TYPE', 'MODE'],
                )
                if desc_col is None:
                    desc_col = find_exp_col(['PARTICULAR', 'ITEM', 'DESC', 'NARRATION', 'GROCERY'])
                # AMOUNT: avoid aggregate columns like TOTAL AMOUNT / GRAND TOTAL
                amount_col = find_exp_col(['AMOUNT'], exclude_keywords=['TOTAL', 'GRAND'])
                type_col = find_exp_col(['EXPANSE TYPE', 'TYPE', 'CATEGORY', 'HEAD'])
                mode_col = find_exp_col(['PAYMENT MODE', 'CASH'], exclude_keywords=['EXPENCE', 'EXPENSE', 'TOTAL'])

                # SMART payment-mode detection — some Excel files have a header
                # called "PAYMENT MODE" that's actually just a 5-row LEGEND
                # (CASH / ONLINE NEFT IMPS / ONLINE UPI / CARD / etc.), while
                # the real per-row payment-mode lives in a differently-named
                # column (e.g. "TYPE"). Pick the column whose cell VALUES most
                # look like payment-mode tokens (CASH / ONLINE / UPI / CARD …)
                # using a simple count-of-matches heuristic.
                def _looks_like_pm(v):
                    if v is None or not pd.notna(v):
                        return False
                    s = str(v).strip().upper()
                    if not s:
                        return False
                    return any(t in s for t in ("CASH", "ONLINE", "UPI", "UIP", "CARD", "NEFT", "RTGS", "IMPS", "BANK"))

                # score every column over the first 200 data rows
                best_col, best_score = None, 0
                sample_rows = min(len(df) - header_row_idx - 1, 200)
                for c in range(df.shape[1]):
                    # skip columns we've already used for other roles
                    if c in (date_col, desc_col, amount_col):
                        continue
                    s = 0
                    for rr in range(header_row_idx + 1, header_row_idx + 1 + sample_rows):
                        try:
                            if _looks_like_pm(df.iloc[rr, c]):
                                s += 1
                        except IndexError:
                            break
                    if s > best_score:
                        best_score = s
                        best_col = c

                # Use value-based detection when it outperforms the header pick
                if best_col is not None:
                    header_score = 0
                    if mode_col is not None:
                        for rr in range(header_row_idx + 1, header_row_idx + 1 + sample_rows):
                            try:
                                if _looks_like_pm(df.iloc[rr, mode_col]):
                                    header_score += 1
                            except IndexError:
                                break
                    # If value-scan finds at least 3 payment-mode-like rows AND
                    # it beats the header pick by a meaningful margin (5+), trust the
                    # value-scan. This protects legitimate sparsely-filled mode cols.
                    if best_score >= 3 and best_score >= header_score + 5:
                        mode_col = best_col
                
                # Final fallback: if we still have date_col and amount_col but no
                # description column, use the cell immediately right of DATE.
                if desc_col is None and date_col is not None:
                    candidate = date_col + 1
                    if candidate != amount_col and candidate < len(headers):
                        desc_col = candidate
                
                if desc_col is None or amount_col is None:
                    continue
                
                # Parse expense rows
                last_date = None
                for row_idx in range(header_row_idx + 1, len(df)):
                    row = df.iloc[row_idx]
                    
                    # Get amount
                    try:
                        amount = float(row.iloc[amount_col]) if pd.notna(row.iloc[amount_col]) else 0
                    except (ValueError, TypeError):
                        continue
                    if amount <= 0:
                        continue
                    
                    # Get description
                    description = str(row.iloc[desc_col]).strip() if pd.notna(row.iloc[desc_col]) else ""
                    if not description or description.lower() in ['nan', '', 'total', 'grand total']:
                        continue
                    
                    # Get date
                    date_val = row.iloc[date_col] if date_col is not None and pd.notna(row.iloc[date_col]) else None
                    if date_val is not None:
                        try:
                            if isinstance(date_val, datetime):
                                date_str = date_val.strftime("%Y-%m-%d")
                            else:
                                date_str_raw = str(date_val).strip()
                                for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d %H:%M:%S']:
                                    try:
                                        date_str = datetime.strptime(date_str_raw.split(' ')[0], fmt).strftime("%Y-%m-%d")
                                        break
                                    except ValueError:
                                        continue
                                else:
                                    date_str = None
                        except Exception:
                            date_str = None
                        if date_str:
                            last_date = date_str
                    else:
                        date_str = last_date
                    
                    if not date_str:
                        continue
                    
                    # Skip if before from_year
                    if date_str < f"{from_year}-01-01":
                        continue
                    # Sanity: ignore implausible future dates (>5 yrs ahead). This
                    # prevents forward-filled junk dates from spurious sheets.
                    try:
                        if int(date_str[:4]) > datetime.now().year + 5:
                            continue
                    except Exception:
                        pass
                    
                    # Get category/type
                    expense_type = ""
                    if type_col is not None and pd.notna(row.iloc[type_col]):
                        expense_type = str(row.iloc[type_col]).strip()
                    
                    # Get payment mode — normalised to one of the system master modes:
                    # CASH, BANK TRANSFER, CARD, NEFT, ONLINE, RTGS, UPI
                    # Default ONLY when the column is truly empty.
                    payment_mode = "CASH"
                    if mode_col is not None and pd.notna(row.iloc[mode_col]):
                        raw_mode = str(row.iloc[mode_col]).strip()
                        if raw_mode:
                            payment_mode = _normalize_payment_mode(raw_mode)
                    
                    expense_records.append({
                        "center": center,
                        "date": date_str,
                        "description": description,
                        "amount": amount,
                        "expense_type": expense_type,
                        "payment_mode": payment_mode,
                        "uploaded_at": datetime.now(timezone.utc).isoformat(),
                        "uploaded_by": session.get("managerName", ""),
                        "source": f"bulk_import:{sheet_name}"
                    })
                
                expense_sheets_processed += 1
                
            except Exception as e:
                logger.warning(f"Error parsing expense sheet '{sheet_name}': {e}")
                continue
        
        # Delete existing expenses for the date range, then insert
        results["expenses"] = {"sheets_processed": expense_sheets_processed, "imported": 0, "deleted": 0}
        if expense_records:
            exp_dates = sorted(set(r["date"] for r in expense_records))
            if exp_dates:
                exp_from = exp_dates[0][:7]
                exp_to = exp_dates[-1][:7]
                if exp_from == exp_to:
                    exp_date_filter = {"$regex": f"^{exp_from}"}
                else:
                    exp_date_filter = {"$gte": f"{exp_from}-01", "$lte": f"{exp_to}-31"}
                exp_del = await db.expenses.delete_many({"center": center, "date": exp_date_filter, "source": {"$regex": "^bulk_import"}})
                results["expenses"]["deleted"] = exp_del.deleted_count
            
            await db.expenses.insert_many(expense_records)
            results["expenses"]["imported"] = len(expense_records)
        
        logger.info(f"Custom upload for {center}: {len(records_to_insert)} sales, {len(expense_records)} expenses from {expense_sheets_processed} expense sheets")
        
        # Log the upload
        await db.upload_logs.insert_one({
            "center": center,
            "uploaded_by": session.get("managerName", ""),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "file_name": file.filename,
            "upload_type": "custom_format",
            "from_year": from_year,
            "results": results
        })
        
        return {
            "success": True,
            "message": f"Custom format upload completed for center {center}",
            "results": results,
            "sheets_processed": results["sales"]["sheets_processed"],
            "expenses_imported": results["expenses"]["imported"],
            "warning": f"Data from {from_year} onwards has been imported. Existing data for those dates was replaced."
        }
        
    except Exception as e:
        logger.error(f"Custom format upload error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Upload error: {str(e)}")


@router.post("/toggle-upload-permission")
async def toggle_upload_permission(data: dict):
    """
    Toggle sales upload permission for a center.
    Only Super Admin can change this setting.
    """
    token = data.get("token")
    center_code = data.get("center")
    enabled = data.get("enabled", False)
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Only Super Admin can toggle
    if not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin can change upload permissions")
    
    # Update center document
    result = await db.centers.update_one(
        {"code": center_code},
        {"$set": {"sales_upload_enabled": enabled}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(404, f"Center '{center_code}' not found")
    
    logger.info(f"Upload permission for {center_code} set to {enabled} by {session.get('managerName')}")
    
    return {
        "success": True,
        "message": f"Upload {'enabled' if enabled else 'disabled'} for center {center_code}"
    }


@router.post("/get-upload-permissions")
async def get_upload_permissions(data: dict):
    """Get upload permission status for all centers"""
    token = data.get("token")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Only Super Admin can view all permissions
    if not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin can view upload permissions")
    
    centers = await db.centers.find(
        {},
        {"_id": 0, "code": 1, "name": 1, "sales_upload_enabled": 1}
    ).to_list(100)
    
    return {
        "centers": centers
    }


@router.post("/upload-logs")
async def get_upload_logs(data: dict):
    """Get upload history logs"""
    token = data.get("token")
    center = data.get("center")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    query = {}
    if center:
        query["center"] = center
    
    # Non-super admin can only see their center's logs
    if not session.get("is_super_admin") and not session.get("is_admin"):
        query["center"] = session.get("center")
    
    logs = await db.upload_logs.find(
        query,
        {"_id": 0}
    ).sort("uploaded_at", -1).limit(50).to_list(50)
    
    return {"logs": logs}


