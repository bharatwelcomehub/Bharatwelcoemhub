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
    cash_expense: Optional[float] = None
    closing_balance: Optional[float] = None
    to_deposit_in_bank: Optional[float] = None
    difference_for_day: Optional[float] = None
    petty_cash_closing: Optional[float] = None
    notes: Optional[str] = None

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
    # PB-MGT center always has access
    if session.get("center") == "PB-MGT":
        return True
    # Super Admin has access
    if session.get("is_super_admin"):
        return True
    # Admin has access
    if session.get("is_admin"):
        return True
    # Check view_all_centers role
    roles = session.get("roles", {})
    if roles.get("view_all_centers"):
        return True
    return False

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
    
    record = req.dict()
    record["center"] = req.center.upper()
    record["created_at"] = datetime.now(timezone.utc).isoformat()
    record["created_by"] = session.get("managerName", "Unknown")
    
    result = await db.expenses.insert_one(record)
    record["expense_id"] = str(result.inserted_id)
    record.pop("_id", None)
    
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
    
    if not req.month:
        raise HTTPException(400, "Month is required (YYYY-MM format)")
    
    # Check if user has access to all centers - PB-MGT ALWAYS has access
    user_center = session.get("center", "")
    can_view_all = user_center == "PB-MGT" or has_all_centers_access(session)
    
    logger.info(f"Monthly summary request: center={user_center}, can_view_all={can_view_all}, req.center={req.center}, month={req.month}")
    
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
        for sale in sales:
            c = sale.get("center")
            if c not in centers_data:
                centers_data[c] = {
                    "center": c,
                    "total_sale": 0,
                    "total_cash_sale": 0,
                    "total_online_sale": 0,
                    "total_expenses": 0,
                    "days_count": 0
                }
            centers_data[c]["total_sale"] += sale.get("total_sale", 0)
            centers_data[c]["total_cash_sale"] += sale.get("total_cash_sale", 0)
            centers_data[c]["total_online_sale"] += sale.get("total_online_sale", 0)
            centers_data[c]["days_count"] += 1
        
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
        
        return {
            "month": req.month,
            "centers": list(centers_data.values()),
            "grand_total": {
                "total_sale": sum(s.get("total_sale", 0) for s in sales),
                "total_cash_sale": sum(s.get("total_cash_sale", 0) for s in sales),
                "total_online_sale": sum(s.get("total_online_sale", 0) for s in sales),
                "total_card_idfc": sum(s.get("card_idfc", 0) for s in sales),
                "total_bharat_pay": sum(s.get("bharat_pay", 0) for s in sales),
                "total_swiggy": sum(s.get("swiggy", 0) for s in sales),
                "total_zomato": sum(s.get("zomato", 0) for s in sales),
                "total_expenses": sum(e.get("amount", 0) for e in expenses)
            },
            "expense_by_type": expense_by_type
        }
    
    # Single center summary
    summary = {
        "month": req.month,
        "center": req.center or session.get("center"),
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
    
    # Day-wise breakdown
    daily_data = []
    for sale in sales:
        day_expenses = sum(e.get("amount", 0) for e in expenses if e.get("date") == sale.get("date"))
        daily_data.append({
            "date": sale.get("date"),
            "total_sale": sale.get("total_sale", 0),
            "cash_sale": sale.get("total_cash_sale", 0),
            "online_sale": sale.get("total_online_sale", 0),
            "expenses": day_expenses,
            "net": sale.get("total_sale", 0) - day_expenses
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

