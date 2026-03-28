# =======================================
# Franchise Management Routes
# CRUD for Franchise records, Documents, Agreements
# FOCO Model - Franchise Owned, Company Operated
# =======================================

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Response, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging
import shutil
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/franchises", tags=["Franchise Management"])

# Get DB reference (will be set from main server)
db = None

# Uploads directory
UPLOAD_DIR = Path(__file__).parent.parent / "uploads" / "franchises"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def set_db(database):
    global db
    db = database

# =======================================
# FRANCHISE CONSTANTS
# =======================================

# Franchise Types and Fees (Non-refundable)
FRANCHISE_TYPES = {
    "Sanskriti": {
        "fee": 1100000,  # 11 Lakhs
        "description": "2500+ Sq. Ft., 20-25 staff, 25-30 tables, 100-120 seating",
        "min_investment": 5000000  # 50 Lakhs
    },
    "Maaza": {
        "fee": 900000,   # 9 Lakhs
        "description": "1500-2000 Sq. Ft., 8-9 staff, 6-15 tables, 40-45 seating",
        "min_investment": 3500000  # 35 Lakhs
    },
    "Potoba": {
        "fee": 700000,   # 7 Lakhs
        "description": "Express format, smaller footprint",
        "min_investment": 2500000  # 25 Lakhs
    },
    "Peshwayee": {
        "fee": 2500000,  # 25 Lakhs
        "description": "Premium fine dining concept",
        "min_investment": 10000000  # 1 Crore
    }
}

DEFAULT_WORKING_CAPITAL = 900000  # 9 Lakhs
MONTHLY_SERVICE_CONTRACT = 10000  # Rs 10,000/month
FRANCHISE_TENURE_YEARS = 7  # Fixed 7 years
REVENUE_SHARE_PERCENTAGE = 15  # 15% to franchise owner
WORKING_CAPITAL_THRESHOLD = 50  # 50% threshold for revenue share

# MG (Minimum Guarantee) Calculation Constants
MG_INTEREST_RATE = 15  # 15% annual interest rate
MG_TENURE_YEARS = 7  # 7 years tenure

def calculate_mg(total_investment: float, setup_costs: dict, franchise_fee: float = 0, working_capital: float = 0) -> dict:
    """
    Calculate Minimum Guarantee (MG) based on Net Investment.
    
    Formula:
    - Net Investment = Total Investment - (Shop Rent Deposit + Staff Travel + 1st Salary + 1st Shop Rent + Working Capital + Franchise Fee)
    - MG = Monthly EMI based on Net Investment as loan amount @ 15% interest for 7 years
    
    EMI Formula: E = P × r × (1+r)^n / ((1+r)^n - 1)
    Where: P = Principal, r = monthly rate, n = total months
    """
    if not total_investment or total_investment <= 0:
        return {
            "total_investment": 0,
            "deductions": {},
            "total_deductions": 0,
            "net_investment": 0,
            "monthly_mg": 0,
            "interest_rate": MG_INTEREST_RATE,
            "tenure_years": MG_TENURE_YEARS
        }
    
    # Get deduction components from setup_costs
    shop_rent_deposit = float(setup_costs.get("shop_security_deposit", 0) or 0)
    staff_travel = float(setup_costs.get("staff_traveling_expense", 0) or 0)
    first_salary = float(setup_costs.get("initial_salary_fund", 0) or 0)
    first_shop_rent = float(setup_costs.get("first_month_rent", 0) or 0)
    
    # Include Franchise Fee and Working Capital as deductions
    franchise_fee_deduction = float(franchise_fee or 0)
    working_capital_deduction = float(working_capital or 0)
    
    deductions = {
        "shop_rent_deposit": shop_rent_deposit,
        "staff_traveling_expense": staff_travel,
        "first_salary": first_salary,
        "first_shop_rent": first_shop_rent,
        "working_capital": working_capital_deduction,
        "franchise_fee": franchise_fee_deduction
    }
    
    total_deductions = (shop_rent_deposit + staff_travel + first_salary + first_shop_rent + 
                        working_capital_deduction + franchise_fee_deduction)
    net_investment = max(0, total_investment - total_deductions)
    
    # Calculate EMI
    if net_investment <= 0:
        monthly_mg = 0
    else:
        # EMI calculation
        P = net_investment  # Principal
        annual_rate = MG_INTEREST_RATE / 100
        r = annual_rate / 12  # Monthly interest rate
        n = MG_TENURE_YEARS * 12  # Total months (84 months)
        
        # EMI Formula: E = P × r × (1+r)^n / ((1+r)^n - 1)
        if r > 0:
            monthly_mg = P * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
        else:
            monthly_mg = P / n
    
    return {
        "total_investment": round(total_investment, 2),
        "deductions": deductions,
        "total_deductions": round(total_deductions, 2),
        "net_investment": round(net_investment, 2),
        "monthly_mg": round(monthly_mg, 2),
        "interest_rate": MG_INTEREST_RATE,
        "tenure_years": MG_TENURE_YEARS
    }

# =======================================
# PYDANTIC MODELS
# =======================================

class DirectorInfo(BaseModel):
    name: str
    email: Optional[str] = ""
    phone: Optional[str] = ""
    designation: Optional[str] = "Director"
    address: Optional[str] = ""
    pan: Optional[str] = ""  # PAN number for India

class SetupCosts(BaseModel):
    shop_security_deposit: float = 0
    first_month_rent: float = 0
    initial_salary_fund: float = 0
    initial_grocery_cost: float = 0
    staff_traveling_expense: float = 0  # NEW: Staff Travel Expense for MG calculation

class FranchiseCreate(BaseModel):
    franchise_code: str  # Unique code like "PB-HSR"
    franchise_name: str
    legal_entity_name: str
    country: str  # India, Australia, etc.
    state: Optional[str] = ""
    city: Optional[str] = ""
    address: Optional[str] = ""
    pincode: Optional[str] = ""
    
    # Contact info
    primary_contact_name: Optional[str] = ""
    primary_contact_email: Optional[str] = ""
    primary_contact_phone: Optional[str] = ""
    
    # Directors/Partners
    directors: List[DirectorInfo] = []
    
    # FOCO Model - Franchise Type
    franchise_type: str = "Sanskriti"  # Sanskriti, Maaza, Potoba, Peshwayee
    
    # Financial Details
    franchise_fee: Optional[float] = 0  # Auto-calculated from type if not provided
    working_capital: float = 900000  # Default 9 Lakhs
    total_investment: float = 0  # NEW: Total Investment for MG calculation
    setup_costs: Optional[SetupCosts] = None
    
    # Agreement details
    operations_start_date: Optional[str] = ""  # YYYY-MM-DD
    agreement_start_date: Optional[str] = ""  # YYYY-MM-DD (same as operations_start_date)
    agreement_end_date: Optional[str] = ""    # Auto-calculated: start + 7 years
    revenue_share_start_date: Optional[str] = ""  # YYYY-MM-DD - When revenue share calculation starts
    
    # Revenue Model
    revenue_share_percentage: float = 15  # 15% to franchise owner
    service_contract_fee: float = 10000   # Rs 10,000/month
    
    # Status
    status: str = "Active"  # Active, Inactive, Terminated, Pending
    
    # Nominee Details (for succession)
    nominees: List[Dict] = []
    
    notes: Optional[str] = ""
    
    # GST Settings (for India locations)
    gst_applicable: bool = False  # NEW: Toggle for 18% GST on Revenue Share (India only)

class FranchiseUpdate(BaseModel):
    franchise_name: Optional[str] = None
    legal_entity_name: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_contact_phone: Optional[str] = None
    directors: Optional[List[DirectorInfo]] = None
    franchise_type: Optional[str] = None
    franchise_fee: Optional[float] = None
    working_capital: Optional[float] = None
    total_investment: Optional[float] = None  # NEW: Total Investment for MG
    setup_costs: Optional[SetupCosts] = None
    operations_start_date: Optional[str] = None
    agreement_start_date: Optional[str] = None
    agreement_end_date: Optional[str] = None
    revenue_share_start_date: Optional[str] = None  # NEW: When revenue share calculation starts
    revenue_share_percentage: Optional[float] = None
    service_contract_fee: Optional[float] = None
    status: Optional[str] = None
    nominees: Optional[List[Dict]] = None
    notes: Optional[str] = None
    gst_applicable: Optional[bool] = None  # NEW: GST toggle for India locations

class TokenRequest(BaseModel):
    token: str

class FranchiseQueryRequest(BaseModel):
    token: str
    search: Optional[str] = None
    country: Optional[str] = None
    status: Optional[str] = None

class DocumentUploadRequest(BaseModel):
    franchise_code: str
    document_type: str  # Agreement, Legal, Compliance, Exit
    document_name: str
    notes: Optional[str] = ""

# Import verify_token from main server (will be set)
verify_token = None
verify_token_async_func = None
has_franchise_access = None

def set_verify_token(func):
    global verify_token
    verify_token = func

def set_verify_token_async(func):
    global verify_token_async_func
    verify_token_async_func = func

def set_access_check(func):
    global has_franchise_access
    has_franchise_access = func

# Helper function to serialize MongoDB document
def serialize_doc(doc: dict) -> dict:
    if doc is None:
        return None
    result = {k: v for k, v in doc.items() if k != '_id'}
    if '_id' in doc:
        result['id'] = str(doc['_id'])
    return result

# =======================================
# ACCESS CHECK
# =======================================

async def check_access(token: str) -> dict:
    """Check if user has franchise access (Admin or Accounts role)"""
    # Try async verification first (checks MongoDB)
    session = None
    if verify_token_async_func:
        session = await verify_token_async_func(token)
    if not session:
        session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Check if user has franchise access
    is_super_admin = session.get("is_super_admin", False)
    is_admin = session.get("is_admin", False)
    roles = session.get("roles", {})
    has_accounting = roles.get("accounting", False)
    
    # Only Super Admin, Admin, or Accounting role can access franchises
    if not (is_super_admin or is_admin or has_accounting):
        raise HTTPException(403, "Only Admin or Accounts users can access Franchise Management")
    
    return session

# =======================================
# FRANCHISE CRUD ENDPOINTS
# =======================================

@router.post("/by-center/{center_code}")
async def get_franchise_by_center(center_code: str, data: dict):
    """Get franchise mapped to a specific center.
    Strategy 1: Check centers collection for franchise_code field (set by Center Accounts linking).
    Strategy 2: Check if any franchise has this center directly.
    Strategy 3: Look up via loan_entries.
    Strategy 4: Regex match on franchise_code suffix."""
    token = data.get("token")
    session = await check_access(token)
    
    center_code = center_code.upper()
    franchise = None

    # Strategy 1: Check centers collection for franchise_code (primary linking method)
    center_doc = await db.centers.find_one({"code": center_code}, {"_id": 0, "franchise_code": 1})
    if center_doc and center_doc.get("franchise_code"):
        franchise = await db.franchises.find_one(
            {"franchise_code": center_doc["franchise_code"], "status": {"$ne": "Deleted"}},
            {"_id": 0}
        )

    if not franchise:
        # Strategy 2: Check if any franchise has this center directly
        franchise = await db.franchises.find_one(
            {"center": center_code, "status": {"$ne": "Deleted"}},
            {"_id": 0}
        )
    
    if not franchise:
        # Strategy 3: Look up via loan_entries (center -> franchise_code mapping)
        loan_entry = await db.loan_entries.find_one(
            {"center": center_code},
            {"_id": 0, "franchise_code": 1, "franchise_name": 1}
        )
        if loan_entry:
            fc = loan_entry.get("franchise_code", "")
            franchise = await db.franchises.find_one(
                {"franchise_code": fc, "status": {"$ne": "Deleted"}},
                {"_id": 0}
            )
    
    if not franchise:
        # Strategy 4: Try matching center code to franchise code (e.g., PB-PERTH -> FR-PERTH)
        center_suffix = center_code.replace("PB-", "")
        franchise = await db.franchises.find_one(
            {"franchise_code": {"$regex": center_suffix, "$options": "i"}, "status": {"$ne": "Deleted"}},
            {"_id": 0}
        )
    
    if franchise:
        return {"found": True, "franchise": franchise}
    else:
        return {"found": False, "franchise": None}



@router.post("/list")
async def list_franchises(req: FranchiseQueryRequest):
    """List all franchises with optional filters"""
    session = await check_access(req.token)
    
    query = {}
    
    # Apply filters
    if req.search:
        query["$or"] = [
            {"franchise_code": {"$regex": req.search, "$options": "i"}},
            {"franchise_name": {"$regex": req.search, "$options": "i"}},
            {"legal_entity_name": {"$regex": req.search, "$options": "i"}},
            {"city": {"$regex": req.search, "$options": "i"}}
        ]
    
    if req.country:
        query["country"] = req.country
    
    if req.status:
        query["status"] = req.status
    
    franchises = await db.franchises.find(query, {"_id": 0}).sort("franchise_code", 1).to_list(1000)
    
    # Get counts by status
    total = await db.franchises.count_documents({})
    active = await db.franchises.count_documents({"status": "Active"})
    pending = await db.franchises.count_documents({"status": "Pending"})
    terminated = await db.franchises.count_documents({"status": "Terminated"})
    
    return {
        "franchises": franchises,
        "total": total,
        "counts": {
            "active": active,
            "pending": pending,
            "terminated": terminated,
            "inactive": total - active - pending - terminated
        }
    }

@router.post("/create")
async def create_franchise(data: dict):
    """Create a new franchise"""
    token = data.get("token")
    session = await check_access(token)
    
    # Extract franchise data
    franchise_code = data.get("franchise_code", "").strip().upper()
    
    if not franchise_code:
        raise HTTPException(400, "Franchise code is required")
    
    # Check for duplicate code
    existing = await db.franchises.find_one({"franchise_code": franchise_code})
    if existing:
        raise HTTPException(400, f"Franchise with code '{franchise_code}' already exists")
    
    # Build franchise document
    franchise_type = data.get("franchise_type", "Sanskriti")
    country = data.get("country", "India")
    
    # Get franchise fee from type if not provided
    franchise_fee = data.get("franchise_fee")
    if not franchise_fee and franchise_type in FRANCHISE_TYPES:
        franchise_fee = FRANCHISE_TYPES[franchise_type]["fee"]
    franchise_fee = float(franchise_fee or 0)
    
    # Calculate agreement end date (7 years from start)
    operations_start_date = data.get("operations_start_date", "")
    agreement_start_date = data.get("agreement_start_date", "") or operations_start_date
    agreement_end_date = data.get("agreement_end_date", "")
    
    if agreement_start_date and not agreement_end_date:
        try:
            start_dt = datetime.strptime(agreement_start_date, "%Y-%m-%d")
            end_dt = start_dt + relativedelta(years=FRANCHISE_TENURE_YEARS)
            agreement_end_date = end_dt.strftime("%Y-%m-%d")
        except:
            pass
    
    # Setup costs
    setup_costs = data.get("setup_costs", {})
    if isinstance(setup_costs, dict):
        setup_costs = {
            "shop_security_deposit": float(setup_costs.get("shop_security_deposit", 0) or 0),
            "first_month_rent": float(setup_costs.get("first_month_rent", 0) or 0),
            "initial_salary_fund": float(setup_costs.get("initial_salary_fund", 0) or 0),
            "initial_grocery_cost": float(setup_costs.get("initial_grocery_cost", 0) or 0),
            "staff_traveling_expense": float(setup_costs.get("staff_traveling_expense", 0) or 0)  # NEW
        }
    
    franchise = {
        "franchise_code": franchise_code,
        "franchise_name": data.get("franchise_name", "").strip(),
        "legal_entity_name": data.get("legal_entity_name", "").strip(),
        "country": country,
        "state": data.get("state", "").strip(),
        "city": data.get("city", "").strip(),
        "address": data.get("address", "").strip(),
        "pincode": data.get("pincode", "").strip(),
        "primary_contact_name": data.get("primary_contact_name", "").strip(),
        "primary_contact_email": data.get("primary_contact_email", "").strip().lower(),
        "primary_contact_phone": data.get("primary_contact_phone", "").strip(),
        "directors": data.get("directors", []),
        
        # FOCO Model fields
        "franchise_type": franchise_type,
        "franchise_fee": franchise_fee,
        "working_capital": float(data.get("working_capital", DEFAULT_WORKING_CAPITAL) or DEFAULT_WORKING_CAPITAL),
        "total_investment": float(data.get("total_investment", 0) or 0),  # NEW: Total Investment for MG
        "setup_costs": setup_costs,
        
        # Agreement dates
        "operations_start_date": operations_start_date,
        "agreement_start_date": agreement_start_date,
        "agreement_end_date": agreement_end_date,
        "revenue_share_start_date": data.get("revenue_share_start_date", "") or operations_start_date,  # NEW: Default to operations start
        
        # Revenue model
        "revenue_share_percentage": float(data.get("revenue_share_percentage", REVENUE_SHARE_PERCENTAGE) or REVENUE_SHARE_PERCENTAGE),
        "service_contract_fee": float(data.get("service_contract_fee", MONTHLY_SERVICE_CONTRACT) or MONTHLY_SERVICE_CONTRACT),
        
        # Nominees
        "nominees": data.get("nominees", []),
        
        "status": data.get("status", "Active"),
        "notes": data.get("notes", ""),
        "gst_applicable": data.get("gst_applicable", False),  # NEW: GST toggle for India
        "documents": [],  # Will hold document references
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": session.get("managerName", ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": session.get("managerName", "")
    }
    
    await db.franchises.insert_one(franchise)
    
    # Log audit entry
    await log_audit(franchise_code, "CREATE", session, {"action": "Franchise created"})
    
    logger.info(f"Franchise created: {franchise_code} by {session.get('managerName')}")
    
    return {"success": True, "message": f"Franchise '{franchise_code}' created successfully"}

@router.post("/get/{franchise_code}")
async def get_franchise(franchise_code: str, req: TokenRequest):
    """Get single franchise details"""
    session = await check_access(req.token)
    
    franchise = await db.franchises.find_one(
        {"franchise_code": franchise_code.upper()},
        {"_id": 0}
    )
    
    if not franchise:
        raise HTTPException(404, f"Franchise '{franchise_code}' not found")
    
    # Get audit history
    audit = await db.franchise_audit.find(
        {"franchise_code": franchise_code.upper()},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(50)
    
    return {
        "franchise": franchise,
        "audit_history": audit
    }

@router.post("/update/{franchise_code}")
async def update_franchise(franchise_code: str, data: dict):
    """Update franchise details"""
    token = data.get("token")
    session = await check_access(token)
    
    # Find existing franchise
    existing = await db.franchises.find_one({"franchise_code": franchise_code.upper()})
    if not existing:
        raise HTTPException(404, f"Franchise '{franchise_code}' not found")
    
    # Build update dict (only non-null fields)
    update_fields = {}
    updatable_fields = [
        "franchise_name", "legal_entity_name", "country", "state", "city",
        "address", "pincode", "primary_contact_name", "primary_contact_email",
        "primary_contact_phone", "directors", "agreement_start_date",
        "agreement_end_date", "franchise_fee", "status", "notes",
        # FOCO fields
        "franchise_type", "working_capital", "total_investment", "setup_costs", "operations_start_date",
        "revenue_share_percentage", "service_contract_fee", "nominees",
        # NEW fields for MG, GST, and revenue share start
        "gst_applicable", "revenue_share_start_date"
    ]
    
    changes = {}
    for field in updatable_fields:
        if field in data and data[field] is not None:
            new_value = data[field]
            old_value = existing.get(field)
            
            # Handle special types
            if field in ["franchise_fee", "working_capital", "revenue_share_percentage", "service_contract_fee"]:
                new_value = float(new_value or 0)
            elif field == "primary_contact_email" and isinstance(new_value, str):
                new_value = new_value.strip().lower()
            elif isinstance(new_value, str):
                new_value = new_value.strip()
            
            if new_value != old_value:
                update_fields[field] = new_value
                changes[field] = {"old": old_value, "new": new_value}
    
    # Auto-calculate agreement_end_date if operations_start_date is provided
    if "operations_start_date" in update_fields and update_fields["operations_start_date"]:
        try:
            start_dt = datetime.strptime(update_fields["operations_start_date"], "%Y-%m-%d")
            end_dt = start_dt + relativedelta(years=FRANCHISE_TENURE_YEARS)
            update_fields["agreement_end_date"] = end_dt.strftime("%Y-%m-%d")
            update_fields["agreement_start_date"] = update_fields["operations_start_date"]
        except:
            pass
    
    if not update_fields:
        return {"success": True, "message": "No changes to update"}
    
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_fields["updated_by"] = session.get("managerName", "")
    
    await db.franchises.update_one(
        {"franchise_code": franchise_code.upper()},
        {"$set": update_fields}
    )
    
    # Log audit entry
    await log_audit(franchise_code.upper(), "UPDATE", session, changes)
    
    logger.info(f"Franchise updated: {franchise_code} by {session.get('managerName')}")
    
    return {"success": True, "message": f"Franchise '{franchise_code}' updated successfully"}

@router.post("/delete/{franchise_code}")
async def delete_franchise(franchise_code: str, req: TokenRequest):
    """Delete a franchise (soft delete - set status to Deleted)"""
    session = await check_access(req.token)
    
    # Only Super Admin can delete
    if not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin can delete franchises")
    
    franchise = await db.franchises.find_one({"franchise_code": franchise_code.upper()})
    if not franchise:
        raise HTTPException(404, f"Franchise '{franchise_code}' not found")
    
    # Soft delete - mark as deleted
    await db.franchises.update_one(
        {"franchise_code": franchise_code.upper()},
        {"$set": {
            "status": "Deleted",
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "deleted_by": session.get("managerName", "")
        }}
    )
    
    # Log audit
    await log_audit(franchise_code.upper(), "DELETE", session, {"action": "Franchise deleted"})
    
    logger.info(f"Franchise deleted: {franchise_code} by {session.get('managerName')}")
    
    return {"success": True, "message": f"Franchise '{franchise_code}' deleted"}

# =======================================
# DOCUMENT MANAGEMENT ENDPOINTS
# =======================================

@router.post("/documents/upload")
async def upload_document(
    token: str = Form(...),
    franchise_code: str = Form(...),
    document_type: str = Form(...),
    document_name: str = Form(...),
    notes: str = Form(""),
    file: UploadFile = File(...)
):
    """Upload a document for a franchise"""
    session = await check_access(token)
    
    # Validate franchise exists
    franchise = await db.franchises.find_one({"franchise_code": franchise_code.upper()})
    if not franchise:
        raise HTTPException(404, f"Franchise '{franchise_code}' not found")
    
    # Validate document type
    valid_types = ["Agreement", "Legal", "Compliance", "Exit", "Other"]
    if document_type not in valid_types:
        raise HTTPException(400, f"Invalid document type. Must be one of: {valid_types}")
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower()
    allowed_extensions = [".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".xlsx", ".xls"]
    
    if file_ext not in allowed_extensions:
        raise HTTPException(400, f"File type not allowed. Allowed: {allowed_extensions}")
    
    unique_id = str(uuid.uuid4())[:8]
    safe_name = f"{franchise_code.upper()}_{document_type}_{unique_id}{file_ext}"
    
    # Create franchise directory
    franchise_dir = UPLOAD_DIR / franchise_code.upper()
    franchise_dir.mkdir(exist_ok=True)
    
    # Save file
    file_path = franchise_dir / safe_name
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # Create document record
    doc_record = {
        "document_id": unique_id,
        "document_name": document_name,
        "document_type": document_type,
        "file_name": safe_name,
        "original_name": file.filename,
        "file_size": os.path.getsize(file_path),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "uploaded_by": session.get("managerName", ""),
        "notes": notes
    }
    
    # Add to franchise's documents array
    await db.franchises.update_one(
        {"franchise_code": franchise_code.upper()},
        {"$push": {"documents": doc_record}}
    )
    
    # Log audit
    await log_audit(franchise_code.upper(), "DOCUMENT_UPLOAD", session, {
        "document_name": document_name,
        "document_type": document_type,
        "file": file.filename
    })
    
    logger.info(f"Document uploaded for {franchise_code}: {document_name}")
    
    return {"success": True, "message": "Document uploaded", "document": doc_record}

@router.get("/documents/download/{franchise_code}/{document_id}")
async def download_document(franchise_code: str, document_id: str, token: str):
    """Download a document"""
    session = await check_access(token)
    
    franchise = await db.franchises.find_one(
        {"franchise_code": franchise_code.upper()},
        {"_id": 0, "documents": 1}
    )
    
    if not franchise:
        raise HTTPException(404, "Franchise not found")
    
    # Find document
    doc = None
    for d in franchise.get("documents", []):
        if d.get("document_id") == document_id:
            doc = d
            break
    
    if not doc:
        raise HTTPException(404, "Document not found")
    
    file_path = UPLOAD_DIR / franchise_code.upper() / doc["file_name"]
    
    if not file_path.exists():
        raise HTTPException(404, "File not found on server")
    
    # Return file
    with open(file_path, "rb") as f:
        content = f.read()
    
    # Determine content type
    ext = Path(doc["file_name"]).suffix.lower()
    content_types = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png"
    }
    
    return Response(
        content=content,
        media_type=content_types.get(ext, "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{doc["original_name"]}"'}
    )

@router.post("/documents/delete/{franchise_code}/{document_id}")
async def delete_document(franchise_code: str, document_id: str, req: TokenRequest):
    """Delete a document"""
    session = await check_access(req.token)
    
    franchise = await db.franchises.find_one(
        {"franchise_code": franchise_code.upper()},
        {"_id": 0, "documents": 1}
    )
    
    if not franchise:
        raise HTTPException(404, "Franchise not found")
    
    # Find document
    doc = None
    for d in franchise.get("documents", []):
        if d.get("document_id") == document_id:
            doc = d
            break
    
    if not doc:
        raise HTTPException(404, "Document not found")
    
    # Delete file from disk
    file_path = UPLOAD_DIR / franchise_code.upper() / doc["file_name"]
    if file_path.exists():
        os.remove(file_path)
    
    # Remove from database
    await db.franchises.update_one(
        {"franchise_code": franchise_code.upper()},
        {"$pull": {"documents": {"document_id": document_id}}}
    )
    
    # Log audit
    await log_audit(franchise_code.upper(), "DOCUMENT_DELETE", session, {
        "document_name": doc.get("document_name"),
        "document_type": doc.get("document_type")
    })
    
    logger.info(f"Document deleted for {franchise_code}: {doc.get('document_name')}")
    
    return {"success": True, "message": "Document deleted"}

# =======================================
# AGREEMENT GENERATION - FOCO MODEL
# =======================================

def format_currency(amount, country="India"):
    """Format currency based on country"""
    if country == "India":
        return f"₹{amount:,.0f}"
    else:
        return f"${amount:,.2f}"

def format_currency_words(amount, country="India"):
    """Convert amount to words"""
    def num_to_words(num):
        ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
                "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
                "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
        
        if num < 20:
            return ones[num]
        elif num < 100:
            return tens[num // 10] + (" " + ones[num % 10] if num % 10 else "")
        elif num < 1000:
            return ones[num // 100] + " Hundred" + (" and " + num_to_words(num % 100) if num % 100 else "")
        elif num < 100000:
            return num_to_words(num // 1000) + " Thousand" + (" " + num_to_words(num % 1000) if num % 1000 else "")
        elif num < 10000000:
            return num_to_words(num // 100000) + " Lakh" + (" " + num_to_words(num % 100000) if num % 100000 else "")
        else:
            return num_to_words(num // 10000000) + " Crore" + (" " + num_to_words(num % 10000000) if num % 10000000 else "")
    
    if country == "India":
        return f"{num_to_words(int(amount))} Rupees Only"
    else:
        return f"{num_to_words(int(amount))} Dollars Only"

@router.post("/generate-agreement/{franchise_code}")
async def generate_agreement(franchise_code: str, data: dict):
    """Generate a comprehensive FOCO Franchise Agreement PDF (60+ pages)"""
    token = data.get("token")
    output_format = data.get("format", "pdf")  # pdf or docx
    
    session = await check_access(token)
    
    franchise = await db.franchises.find_one(
        {"franchise_code": franchise_code.upper()},
        {"_id": 0}
    )
    
    if not franchise:
        raise HTTPException(404, "Franchise not found")
    
    try:
        # Import the comprehensive agreement generator
        from utils.agreement_generator import FranchiseAgreementGenerator
        
        # Generate the comprehensive agreement
        generator = FranchiseAgreementGenerator(franchise)
        pdf_content = generator.generate()
        
        filename = f"FOCO_Agreement_{franchise_code.upper()}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # Log audit
        await log_audit(franchise_code.upper(), "AGREEMENT_GENERATED", session, {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "format": output_format,
            "franchise_type": franchise.get("franchise_type", "Sanskriti"),
            "franchise_fee": franchise.get("franchise_fee", 0),
            "version": "comprehensive_v2",
            "country": franchise.get("country", "India")
        })
        
        logger.info(f"Comprehensive agreement generated for {franchise_code} by {session.get('managerName')}")
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        # Fallback to basic generation if new module not available
        raise HTTPException(500, f"Agreement generator module not found: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating agreement: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Error generating agreement: {str(e)}")

@router.get("/franchise-types")
async def get_franchise_types():
    """Get available franchise types and their fees"""
    return {
        "types": FRANCHISE_TYPES,
        "defaults": {
            "working_capital": DEFAULT_WORKING_CAPITAL,
            "service_contract_fee": MONTHLY_SERVICE_CONTRACT,
            "tenure_years": FRANCHISE_TENURE_YEARS,
            "revenue_share_percentage": REVENUE_SHARE_PERCENTAGE
        }
    }

# =======================================
# AUDIT LOGGING
# =======================================

async def log_audit(franchise_code: str, action: str, session: dict, details: dict):
    """Log audit entry for franchise changes"""
    audit_entry = {
        "franchise_code": franchise_code,
        "action": action,
        "performed_by": session.get("managerName", "Unknown"),
        "performed_by_center": session.get("center", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details
    }
    
    await db.franchise_audit.insert_one(audit_entry)

# =======================================
# STATISTICS ENDPOINT
# =======================================

@router.post("/stats")
async def get_franchise_stats(req: TokenRequest):
    """Get franchise statistics"""
    session = await check_access(req.token)
    
    total = await db.franchises.count_documents({})
    by_country = await db.franchises.aggregate([
        {"$group": {"_id": "$country", "count": {"$sum": 1}}}
    ]).to_list(100)
    
    by_status = await db.franchises.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]).to_list(100)
    
    return {
        "total": total,
        "by_country": {item["_id"]: item["count"] for item in by_country if item["_id"]},
        "by_status": {item["_id"]: item["count"] for item in by_status if item["_id"]}
    }

@router.get("/countries")
async def get_countries():
    """Get list of available countries"""
    return {
        "countries": [
            "India",
            "Australia",
            "United States",
            "United Kingdom",
            "Canada",
            "UAE",
            "Singapore",
            "Other"
        ]
    }



@router.post("/mg-calculation/{franchise_code}")
async def get_mg_calculation(franchise_code: str, req: dict = Body(...)):
    """
    Get Minimum Guarantee (MG) calculation for a franchise.
    
    Returns:
    - Total Investment
    - Deductions breakdown
    - Net Investment
    - Monthly MG (EMI)
    """
    # Verify token
    try:
        session = await verify_token_async_func(req.get("token"))
    except:
        raise HTTPException(401, "Invalid token")
    
    # Get franchise details
    franchise = await db.franchises.find_one(
        {"franchise_code": franchise_code.upper()},
        {"_id": 0}
    )
    
    if not franchise:
        raise HTTPException(404, f"Franchise '{franchise_code}' not found")
    
    # Calculate total investment
    franchise_fee = float(franchise.get("franchise_fee", 0) or 0)
    working_capital = float(franchise.get("working_capital", 0) or 0)
    total_investment = franchise_fee + working_capital
    
    # Get setup costs
    setup_costs = franchise.get("setup_costs", {})
    if not isinstance(setup_costs, dict):
        setup_costs = {}
    
    # Calculate MG
    mg_data = calculate_mg(total_investment, setup_costs)
    
    return {
        "success": True,
        "franchise_code": franchise_code.upper(),
        "franchise_name": franchise.get("franchise_name", ""),
        "mg_calculation": mg_data
    }
