# =======================================
# Loan Entry Routes
# Working Capital Loan Tracking
# =======================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/loan-entries", tags=["Loan Entries"])

# Database reference
db = None

def set_db(database):
    global db
    db = database

# Verify token function (will be set from main server)
verify_token_async = None

def set_verify_token_async(func):
    global verify_token_async
    verify_token_async = func

# =======================================
# MODELS
# =======================================

class LoanEntryCreate(BaseModel):
    center: str
    amount: float
    loan_date: str  # YYYY-MM-DD
    reason: str
    notes: Optional[str] = ""

class LoanRepayment(BaseModel):
    amount: float
    repayment_date: str
    notes: Optional[str] = ""

# =======================================
# HELPER FUNCTIONS
# =======================================

async def check_access(token: str):
    """Verify token and return session"""
    if not token:
        raise HTTPException(401, "Authentication required")
    
    session = await db.sessions.find_one({"token": token}, {"_id": 0})
    if not session:
        raise HTTPException(401, "Invalid or expired session")
    
    return session

async def get_center_details(center_code: str):
    """Get center details"""
    center = await db.centers.find_one({"code": center_code}, {"_id": 0})
    if not center:
        raise HTTPException(404, f"Center {center_code} not found")
    return center

async def get_franchise_for_center(center_code: str):
    """Get linked franchise for a center"""
    center = await db.centers.find_one({"code": center_code}, {"_id": 0})
    if not center:
        return None
    
    franchise_code = center.get("franchise_code")
    if franchise_code:
        franchise = await db.franchises.find_one({"franchise_code": franchise_code}, {"_id": 0})
        if franchise:
            return franchise
    
    # Try to match by city for Perth
    if "perth" in center_code.lower():
        franchise = await db.franchises.find_one(
            {"city": {"$regex": "perth", "$options": "i"}, "status": {"$ne": "Deleted"}},
            {"_id": 0}
        )
        if franchise:
            return franchise
    
    return None

def generate_loan_id(center: str) -> str:
    """Generate unique loan ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"LOAN-{center}-{timestamp}"

# =======================================
# LOAN ENTRY ENDPOINTS
# =======================================

@router.post("/create")
async def create_loan_entry(data: dict):
    """Create a new loan entry (using working capital)"""
    token = data.get("token")
    session = await check_access(token)
    
    # Only Super Admin or Admin can create loan entries
    if not session.get("is_super_admin") and not session.get("is_admin"):
        raise HTTPException(403, "Only Admin can create loan entries")
    
    # Validate required fields
    required_fields = ["center", "amount", "loan_date", "reason"]
    missing_fields = [f for f in required_fields if not data.get(f)]
    if missing_fields:
        raise HTTPException(422, f"Missing required fields: {', '.join(missing_fields)}")
    
    center = data.get("center")
    amount = float(data.get("amount", 0))
    
    if amount <= 0:
        raise HTTPException(400, "Loan amount must be positive")
    
    # Get center and franchise info
    center_info = await get_center_details(center)
    franchise = await get_franchise_for_center(center)
    
    # Check if loan exceeds working capital
    working_capital = franchise.get("working_capital", 0) if franchise else 0
    
    # Get existing outstanding loans for this center
    existing_loans = await db.loan_entries.find({
        "center": center,
        "status": {"$ne": "fully_repaid"}
    }).to_list(100)
    
    total_outstanding = sum(
        (loan.get("amount", 0) - loan.get("total_repaid", 0)) 
        for loan in existing_loans
    )
    
    if (total_outstanding + amount) > working_capital:
        raise HTTPException(400, 
            f"Loan amount ({amount}) plus existing outstanding ({total_outstanding}) "
            f"exceeds available working capital ({working_capital})")
    
    # Create loan entry
    loan_id = generate_loan_id(center)
    
    loan_doc = {
        "loan_id": loan_id,
        "center": center,
        "center_name": center_info.get("name", center),
        "franchise_code": franchise.get("franchise_code") if franchise else None,
        "franchise_name": franchise.get("franchise_name") if franchise else None,
        "amount": amount,
        "loan_date": data.get("loan_date"),
        "reason": data.get("reason"),
        "notes": data.get("notes", ""),
        "status": "active",  # active, partially_repaid, fully_repaid
        "total_repaid": 0,
        "repayments": [],
        "working_capital_at_time": working_capital,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": session.get("managerName", "Unknown"),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.loan_entries.insert_one(loan_doc)
    
    return {
        "success": True,
        "message": "Loan entry created successfully",
        "loan_id": loan_id,
        "loan": {
            "loan_id": loan_id,
            "amount": amount,
            "center": center,
            "loan_date": data.get("loan_date"),
            "status": "active"
        }
    }

@router.post("/list")
async def list_loan_entries(data: dict):
    """List loan entries for a center or all centers"""
    token = data.get("token")
    session = await check_access(token)
    
    center = data.get("center")
    status_filter = data.get("status")  # active, partially_repaid, fully_repaid, or None for all
    
    query = {}
    if center:
        query["center"] = center
    if status_filter:
        query["status"] = status_filter
    
    loans = await db.loan_entries.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Calculate summary
    total_loaned = sum(loan.get("amount", 0) for loan in loans)
    total_repaid = sum(loan.get("total_repaid", 0) for loan in loans)
    total_outstanding = total_loaned - total_repaid
    
    active_loans = [l for l in loans if l.get("status") == "active"]
    partially_repaid = [l for l in loans if l.get("status") == "partially_repaid"]
    fully_repaid = [l for l in loans if l.get("status") == "fully_repaid"]
    
    return {
        "success": True,
        "loans": loans,
        "summary": {
            "total_loaned": total_loaned,
            "total_repaid": total_repaid,
            "total_outstanding": total_outstanding,
            "active_count": len(active_loans),
            "partially_repaid_count": len(partially_repaid),
            "fully_repaid_count": len(fully_repaid)
        }
    }

@router.post("/get/{loan_id}")
async def get_loan_entry(loan_id: str, data: dict):
    """Get details of a specific loan entry"""
    token = data.get("token")
    session = await check_access(token)
    
    loan = await db.loan_entries.find_one({"loan_id": loan_id}, {"_id": 0})
    if not loan:
        raise HTTPException(404, "Loan entry not found")
    
    return {"success": True, "loan": loan}

@router.post("/add-repayment/{loan_id}")
async def add_repayment(loan_id: str, data: dict):
    """Add a repayment to a loan entry"""
    token = data.get("token")
    session = await check_access(token)
    
    # Only Super Admin or Admin can add repayments
    if not session.get("is_super_admin") and not session.get("is_admin"):
        raise HTTPException(403, "Only Admin can add repayments")
    
    loan = await db.loan_entries.find_one({"loan_id": loan_id})
    if not loan:
        raise HTTPException(404, "Loan entry not found")
    
    if loan.get("status") == "fully_repaid":
        raise HTTPException(400, "This loan is already fully repaid")
    
    repayment_amount = float(data.get("amount", 0))
    repayment_date = data.get("repayment_date")
    
    if repayment_amount <= 0:
        raise HTTPException(400, "Repayment amount must be positive")
    
    if not repayment_date:
        raise HTTPException(400, "Repayment date is required")
    
    # Calculate outstanding
    outstanding = loan.get("amount", 0) - loan.get("total_repaid", 0)
    
    if repayment_amount > outstanding:
        raise HTTPException(400, f"Repayment amount ({repayment_amount}) exceeds outstanding ({outstanding})")
    
    # Add repayment
    repayment = {
        "amount": repayment_amount,
        "repayment_date": repayment_date,
        "notes": data.get("notes", ""),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "recorded_by": session.get("managerName", "Unknown")
    }
    
    new_total_repaid = loan.get("total_repaid", 0) + repayment_amount
    new_outstanding = loan.get("amount", 0) - new_total_repaid
    
    # Determine new status
    if new_outstanding <= 0:
        new_status = "fully_repaid"
    elif new_total_repaid > 0:
        new_status = "partially_repaid"
    else:
        new_status = "active"
    
    # Update loan
    await db.loan_entries.update_one(
        {"loan_id": loan_id},
        {
            "$push": {"repayments": repayment},
            "$set": {
                "total_repaid": new_total_repaid,
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "success": True,
        "message": f"Repayment of {repayment_amount} recorded",
        "new_total_repaid": new_total_repaid,
        "new_outstanding": new_outstanding,
        "new_status": new_status
    }

@router.post("/summary")
async def get_loan_summary(data: dict):
    """Get loan summary for a center"""
    token = data.get("token")
    session = await check_access(token)
    
    center = data.get("center")
    if not center:
        raise HTTPException(400, "Center is required")
    
    # Get franchise info for working capital
    franchise = await get_franchise_for_center(center)
    working_capital = franchise.get("working_capital", 0) if franchise else 0
    
    # Get all loans for this center
    loans = await db.loan_entries.find({"center": center}, {"_id": 0}).to_list(500)
    
    # Calculate totals
    total_loaned = sum(loan.get("amount", 0) for loan in loans)
    total_repaid = sum(loan.get("total_repaid", 0) for loan in loans)
    total_outstanding = total_loaned - total_repaid
    
    # Available working capital
    available_working_capital = working_capital - total_outstanding
    
    # Recent loans (last 5)
    recent_loans = sorted(loans, key=lambda x: x.get("created_at", ""), reverse=True)[:5]
    
    # Active loans
    active_loans = [l for l in loans if l.get("status") in ["active", "partially_repaid"]]
    
    return {
        "success": True,
        "center": center,
        "working_capital": {
            "total": working_capital,
            "utilized": total_outstanding,
            "available": available_working_capital,
            "utilization_percentage": (total_outstanding / working_capital * 100) if working_capital > 0 else 0
        },
        "loans": {
            "total_loaned": total_loaned,
            "total_repaid": total_repaid,
            "total_outstanding": total_outstanding,
            "active_count": len(active_loans),
            "total_count": len(loans)
        },
        "recent_loans": recent_loans,
        "active_loans": active_loans
    }

@router.post("/delete/{loan_id}")
async def delete_loan_entry(loan_id: str, data: dict):
    """Delete a loan entry (only if no repayments)"""
    token = data.get("token")
    session = await check_access(token)
    
    # Only Super Admin can delete
    if not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin can delete loan entries")
    
    loan = await db.loan_entries.find_one({"loan_id": loan_id})
    if not loan:
        raise HTTPException(404, "Loan entry not found")
    
    if loan.get("total_repaid", 0) > 0:
        raise HTTPException(400, "Cannot delete loan with existing repayments")
    
    await db.loan_entries.delete_one({"loan_id": loan_id})
    
    return {"success": True, "message": "Loan entry deleted"}
