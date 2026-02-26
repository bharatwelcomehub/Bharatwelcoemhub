# =======================================
# Sales & Expenses Routes
# Daily Sales and Cash Summary Management
# =======================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sales", tags=["Sales & Expenses"])

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
    cash_receipts: float = 0
    
    # Sales breakdown
    sale_pbm: float = 0  # PBM products
    sale_other: float = 0  # Other products
    total_sale: float = 0
    
    # Online/Card payments
    card_idfc: float = 0
    bharat_pay: float = 0
    swiggy: float = 0
    zomato: float = 0
    online_other: float = 0
    due_amount: float = 0
    total_online_sale: float = 0
    total_cash_sale: float = 0
    
    # Guest & Bill tracking (NEW)
    num_guests: int = 0  # Number of guests (pax)
    num_bills: int = 0   # Number of bills (excluding Swiggy/Zomato)
    avg_per_pax: float = 0  # Average per guest
    avg_per_bill: float = 0  # Average per bill
    
    # GST Calculation (NEW)
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
    cash_receipts: Optional[float] = None
    sale_pbm: Optional[float] = None
    sale_other: Optional[float] = None
    total_sale: Optional[float] = None
    card_idfc: Optional[float] = None
    bharat_pay: Optional[float] = None
    swiggy: Optional[float] = None
    zomato: Optional[float] = None
    online_other: Optional[float] = None
    due_amount: Optional[float] = None
    total_online_sale: Optional[float] = None
    total_cash_sale: Optional[float] = None
    # Guest & Bill tracking (NEW)
    num_guests: Optional[int] = None
    num_bills: Optional[int] = None
    avg_per_pax: Optional[float] = None
    avg_per_bill: Optional[float] = None
    # GST (NEW)
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

class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    expense_type: Optional[str] = None
    payment_mode: Optional[str] = None
    notes: Optional[str] = None

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

def set_verify_token(func):
    global verify_token
    verify_token = func

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
    return False

def has_sales_access(session):
    """Check if user has access to sales & cash features"""
    if not session:
        return False
    if session.get("is_super_admin"):
        return True
    roles = session.get("roles", {})
    return roles.get("sales_cash", False)

# =======================================
# GST & CURRENCY HELPERS
# =======================================

def is_perth_center(center: str) -> bool:
    """Check if center is Perth (Australia) - handles multiple formats"""
    if not center:
        return False
    c = center.upper()
    return c in ["PB-PERTH", "PERTH"]

def get_currency_symbol(center: str) -> str:
    """Get currency symbol based on center"""
    return "$" if is_perth_center(center) else "₹"

def calculate_gst(total_sale: float, swiggy: float, zomato: float, center: str) -> dict:
    """
    Calculate GST based on center location.
    - Perth (Australia): 10% GST INCLUSIVE (extract from total)
    - India: 5% GST EXCLUSIVE (added on top, excl. Swiggy/Zomato)
    """
    # Exclude Swiggy and Zomato from GST calculation
    gst_applicable_sale = max(0, total_sale - swiggy - zomato)
    
    if is_perth_center(center):
        # Australia (Perth): 10% GST is INCLUDED in price
        # Formula: GST = Total / 11
        gst_rate = 10
        gst_amount = gst_applicable_sale / 11
        net_sale = gst_applicable_sale - gst_amount
        is_inclusive = True
    else:
        # India: 5% GST is ADDED to subtotal
        # Formula: GST = Subtotal * 0.05
        gst_rate = 5
        gst_amount = gst_applicable_sale * 0.05
        net_sale = gst_applicable_sale
        is_inclusive = False
    
    return {
        "gst_rate": gst_rate,
        "gst_amount": round(gst_amount, 2),
        "net_sale": round(net_sale, 2),
        "is_inclusive": is_inclusive,
        "currency": get_currency_symbol(center)
    }

# =======================================
# HELPER FUNCTIONS
# =======================================

def calculate_totals(sale: dict) -> dict:
    """Calculate derived fields for a sale record"""
    # Total sale = PBM + Other
    sale["total_sale"] = sale.get("sale_pbm", 0) + sale.get("sale_other", 0)
    
    # Total online sale
    sale["total_online_sale"] = (
        sale.get("card_idfc", 0) + 
        sale.get("bharat_pay", 0) + 
        sale.get("swiggy", 0) + 
        sale.get("zomato", 0) + 
        sale.get("online_other", 0)
    )
    
    # Total cash sale = Total sale - Online sale
    sale["total_cash_sale"] = sale["total_sale"] - sale["total_online_sale"]
    
    # Closing balance calculation
    sale["closing_balance"] = (
        sale.get("opening_balance", 0) + 
        sale.get("total_cash_sale", 0) + 
        sale.get("cash_receipts", 0) - 
        sale.get("deposited_in_bank", 0) - 
        sale.get("cash_expense", 0)
    )
    
    # Petty cash closing
    sale["petty_cash_closing"] = (
        sale.get("petty_cash_opening", 0) + 
        sale.get("cash_receipts", 0) - 
        sale.get("cash_expense", 0)
    )
    
    # To deposit in bank
    sale["to_deposit_in_bank"] = sale["closing_balance"] - sale["petty_cash_closing"]
    
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

async def is_date_unlocked(center: str, date_str: str) -> bool:
    """
    Check if a frozen date has been temporarily unlocked by Super Admin.
    Returns True if unlocked, False if still frozen.
    """
    unlock = await db.unlock_grants.find_one({
        "center": center.upper(),
        "date": date_str,
        "status": "active",
        "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
    })
    return unlock is not None

async def can_edit_date(session: dict, center: str, date_str: str) -> tuple:
    """
    Check if user can edit a specific date's data.
    Returns (can_edit: bool, reason: str)
    """
    # Super Admin can always edit
    if session.get("is_super_admin"):
        return (True, "Super Admin access")
    
    # Check if date is frozen
    if not is_date_frozen(date_str):
        return (True, "Date is not frozen (today)")
    
    # Date is frozen - check if unlocked for this center
    if await is_date_unlocked(center, date_str):
        return (True, "Date temporarily unlocked by Super Admin")
    
    return (False, "Date is frozen. Request unlock from Super Admin.")

# =======================================
# DAILY SALES ENDPOINTS
# =======================================

@router.post("/daily")
async def get_daily_sales(req: SalesQueryRequest):
    """Get daily sales records with filters"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
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
    
    # Check if date is frozen
    can_edit, reason = await can_edit_date(session, req.center, req.date)
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
    if session.get("center") != "PB-MGT" and session.get("center") != center.upper():
        raise HTTPException(403, "Cannot update sales record for another center")
    
    # Check if date is frozen
    can_edit, reason = await can_edit_date(session, center, date)
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
    
    # If approved, create an unlock grant (valid for 24 hours)
    if req.action == "approve":
        from datetime import timedelta
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        
        await db.unlock_grants.insert_one({
            "center": unlock_request["center"],
            "date": unlock_request["date"],
            "status": "active",
            "granted_by": session.get("managerName", "Unknown"),
            "granted_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at,
            "request_id": request_id
        })
        
        logger.info(f"Unlock granted: {unlock_request['center']} - {unlock_request['date']} by {session.get('managerName')} (expires: {expires_at})")
    
    return {
        "success": True, 
        "message": f"Request {req.action}d successfully",
        "status": update_data["status"]
    }

@router.get("/check-frozen/{center}/{date}")
async def check_frozen_status(center: str, date: str, token: str):
    """Check if a specific date is frozen and its unlock status"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    is_frozen = is_date_frozen(date)
    is_unlocked = await is_date_unlocked(center, date) if is_frozen else False
    can_edit, reason = await can_edit_date(session, center, date)
    
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
        "is_unlocked": is_unlocked,
        "can_edit": can_edit,
        "reason": reason,
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
    
    session = verify_token(req.token)
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
    
    expenses = await db.expenses.find(query, {"_id": 0}).sort("date", -1).to_list(5000)
    
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
    if session.get("center") != "PB-MGT" and session.get("center") != req.center.upper():
        raise HTTPException(403, "Cannot create expense for another center")
    
    # Check if date is frozen (only Super Admin can add expenses for frozen dates)
    can_edit, reason = await can_edit_date(session, req.center, req.date)
    if not can_edit:
        raise HTTPException(403, f"Cannot add expense for frozen date. {reason}")
    
    record = req.dict()
    record["center"] = req.center.upper()
    record["created_at"] = datetime.now(timezone.utc).isoformat()
    record["created_by"] = session.get("managerName", "Unknown")
    
    result = await db.expenses.insert_one(record)
    record["expense_id"] = str(result.inserted_id)
    record.pop("_id", None)
    
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
    if session.get("center") != "PB-MGT" and session.get("center") != existing.get("center"):
        raise HTTPException(403, "Cannot update expense for another center")
    
    update_data = {k: v for k, v in req.dict().items() if v is not None}
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        update_data["updated_by"] = session.get("managerName", "Unknown")
        
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
    if session.get("center") != "PB-MGT" and session.get("center") != existing.get("center"):
        raise HTTPException(403, "Cannot delete expense for another center")
    
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
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Build query for sales
    sales_query = {}
    
    if session.get("center") != "PB-MGT":
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
    
    session = verify_token(req.token)
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
    """Get all unique expense types"""
    types = await db.expenses.distinct("expense_type")
    
    # Standard expense types
    standard_types = [
        "GROCERY",
        "DAIRY PRODUCTS",
        "FRUITS & VEGETABLE",
        "WATER CAN/ BOTTLE",
        "CYLINDER",
        "PAV",
        "PACKAGING MATERIAL",
        "CELEBRATION EXPENSES",
        "MEDIA & ADVERTISEMENT",
        "RESTAURANT GENERAL EXPENSES",
        "REPAIR & MAINTENANCE",
        "SALARY",
        "ADVANCE",
        "RENT",
        "ELECTRICITY",
        "OTHER"
    ]
    
    # Merge with existing types
    all_types = list(set(standard_types + types))
    all_types.sort()
    
    return {"expense_types": all_types}

@router.get("/payment-modes")
async def get_payment_modes():
    """Get all payment modes"""
    return {
        "payment_modes": [
            "CASH",
            "ONLINE UPI",
            "ONLINE NEFT/IMPS",
            "CARD",
            "CHEQUE"
        ]
    }

@router.get("/centers-list")
async def get_centers_for_sales():
    """Get list of centers that have sales data"""
    centers = await db.daily_sales.distinct("center")
    return {"centers": sorted(centers)}

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
    
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can manage expense heads")
    
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
    
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can manage expense heads")
    
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
    
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can manage expense heads")
    
    result = await db.expense_heads.delete_one({"name": head_name.upper()})
    
    if result.deleted_count == 0:
        raise HTTPException(404, f"Expense head '{head_name}' not found")
    
    logger.info(f"Expense head deleted: {head_name} by {session.get('managerName')}")
    
    return {"success": True, "message": "Expense head deleted"}


# =======================================
# PERTH EXCEL UPLOAD
# Import Perth Sales Data from Excel without modification
# =======================================

from fastapi import UploadFile, File
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
async def upload_perth_excel(token: str, file: UploadFile = File(...)):
    """
    Upload Perth Sales Excel file and import data WITHOUT modification.
    Preserves original structure, spelling, and currency ($AUD).
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
                    "center": "PB-PERTH",  # Perth center code (standardized)
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
                    {"center": "PB-PERTH", "date": date_str},
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
            "message": f"Perth Excel imported successfully",
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "errors": errors[:10] if errors else [],  # Return first 10 errors
            "center": "PB-PERTH",
            "currency": "AUD ($)",
            "gst_rate": "10% inclusive"
        }
        
    except ImportError:
        raise HTTPException(500, "openpyxl library not installed. Please install it.")
    except Exception as e:
        logger.error(f"Perth Excel upload error: {e}")
        raise HTTPException(500, f"Excel processing error: {str(e)}")

