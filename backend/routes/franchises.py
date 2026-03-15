# =======================================
# Franchise Management Routes
# CRUD for Franchise records, Documents, Agreements
# FOCO Model - Franchise Owned, Company Operated
# =======================================

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Response
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
    setup_costs: Optional[SetupCosts] = None
    
    # Agreement details
    operations_start_date: Optional[str] = ""  # YYYY-MM-DD
    agreement_start_date: Optional[str] = ""  # YYYY-MM-DD (same as operations_start_date)
    agreement_end_date: Optional[str] = ""    # Auto-calculated: start + 7 years
    
    # Revenue Model
    revenue_share_percentage: float = 15  # 15% to franchise owner
    service_contract_fee: float = 10000   # Rs 10,000/month
    
    # Status
    status: str = "Active"  # Active, Inactive, Terminated, Pending
    
    # Nominee Details (for succession)
    nominees: List[Dict] = []
    
    notes: Optional[str] = ""

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
    setup_costs: Optional[SetupCosts] = None
    operations_start_date: Optional[str] = None
    agreement_start_date: Optional[str] = None
    agreement_end_date: Optional[str] = None
    revenue_share_percentage: Optional[float] = None
    service_contract_fee: Optional[float] = None
    status: Optional[str] = None
    nominees: Optional[List[Dict]] = None
    notes: Optional[str] = None

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
has_franchise_access = None

def set_verify_token(func):
    global verify_token
    verify_token = func

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
            "initial_grocery_cost": float(setup_costs.get("initial_grocery_cost", 0) or 0)
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
        "setup_costs": setup_costs,
        
        # Agreement dates
        "operations_start_date": operations_start_date,
        "agreement_start_date": agreement_start_date,
        "agreement_end_date": agreement_end_date,
        
        # Revenue model
        "revenue_share_percentage": float(data.get("revenue_share_percentage", REVENUE_SHARE_PERCENTAGE) or REVENUE_SHARE_PERCENTAGE),
        "service_contract_fee": float(data.get("service_contract_fee", MONTHLY_SERVICE_CONTRACT) or MONTHLY_SERVICE_CONTRACT),
        
        # Nominees
        "nominees": data.get("nominees", []),
        
        "status": data.get("status", "Active"),
        "notes": data.get("notes", ""),
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
        "franchise_type", "working_capital", "setup_costs", "operations_start_date",
        "revenue_share_percentage", "service_contract_fee", "nominees"
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
    """Generate a FOCO Franchise Agreement PDF"""
    token = data.get("token")
    output_format = data.get("format", "pdf")  # pdf or docx
    
    session = await check_access(token)
    
    franchise = await db.franchises.find_one(
        {"franchise_code": franchise_code.upper()},
        {"_id": 0}
    )
    
    if not franchise:
        raise HTTPException(404, "Franchise not found")
    
    # Extract all data
    country = franchise.get("country", "India")
    is_india = country == "India"
    
    franchise_type = franchise.get("franchise_type", "Sanskriti")
    franchise_fee = franchise.get("franchise_fee", FRANCHISE_TYPES.get(franchise_type, {}).get("fee", 0))
    working_capital = franchise.get("working_capital", DEFAULT_WORKING_CAPITAL)
    revenue_share = franchise.get("revenue_share_percentage", REVENUE_SHARE_PERCENTAGE)
    service_fee = franchise.get("service_contract_fee", MONTHLY_SERVICE_CONTRACT)
    
    setup_costs = franchise.get("setup_costs", {})
    total_setup = (
        setup_costs.get("shop_security_deposit", 0) +
        setup_costs.get("first_month_rent", 0) +
        setup_costs.get("initial_salary_fund", 0) +
        setup_costs.get("initial_grocery_cost", 0)
    )
    
    # Date formatting
    today = datetime.now()
    agreement_date = today.strftime("%d %B %Y")
    ops_start = franchise.get("operations_start_date", "")
    agreement_start = franchise.get("agreement_start_date", ops_start)
    agreement_end = franchise.get("agreement_end_date", "")
    
    # Directors
    directors = franchise.get("directors", [])
    directors_names = ", ".join([d.get("name", "") for d in directors if d.get("name")])
    
    # Franchisor entity based on country
    if is_india:
        franchisor_name = "MANASWINI FOODS PRIVATE LIMITED"
        franchisor_address = "17/N, Bhagyalakshmi Square, 18th Cross Rd, Sector 3, HSR Layout, Bengaluru, Karnataka 560102"
        franchisor_cin = "CIN No. [To be filled]"
        jurisdiction = franchise.get("city", "Bengaluru")
    else:
        franchisor_name = "PURNABRAMHA LLC"
        franchisor_address = "International Operations Office"
        franchisor_cin = ""
        jurisdiction = franchise.get("city", country)
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch, cm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib import colors
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                               leftMargin=0.75*inch, rightMargin=0.75*inch,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], 
                                     fontSize=16, alignment=TA_CENTER, spaceAfter=20,
                                     fontName='Helvetica-Bold')
        heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], 
                                       fontSize=12, spaceAfter=8, spaceBefore=12,
                                       fontName='Helvetica-Bold')
        subheading_style = ParagraphStyle('SubHeading', parent=styles['Normal'], 
                                          fontSize=11, spaceAfter=6, spaceBefore=8,
                                          fontName='Helvetica-Bold')
        normal_style = ParagraphStyle('Normal', parent=styles['Normal'], 
                                      fontSize=10, spaceAfter=6, alignment=TA_JUSTIFY,
                                      leading=14)
        small_style = ParagraphStyle('Small', parent=styles['Normal'], 
                                     fontSize=9, spaceAfter=4, alignment=TA_JUSTIFY,
                                     leading=12)
        
        story = []
        
        # =======================================
        # AGREEMENT TITLE
        # =======================================
        story.append(Paragraph("FRANCHISE AGREEMENT", title_style))
        story.append(Paragraph("(FOCO Model - Franchise Owned, Company Operated)", 
                              ParagraphStyle('Subtitle', parent=normal_style, alignment=TA_CENTER, fontSize=10)))
        story.append(Spacer(1, 0.2*inch))
        
        # =======================================
        # PARTIES TO THE AGREEMENT
        # =======================================
        story.append(Paragraph(f"THIS AGREEMENT (the \"Agreement\") is made this {agreement_date}, by and between:", normal_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Franchisor
        franchisor_text = f"""
        <b>M/s. {franchisor_name}</b>, a company incorporated under the provisions of the Companies Act, 1956 
        {f'({franchisor_cin})' if franchisor_cin else ''} (which expression shall, unless repugnant to the meaning and context thereof, 
        be deemed to mean and include its successors & assignees), having its registered office at {franchisor_address} 
        through its Directors Mrs. Jayanti Pranav Kathale and Mr. Sandeep Gadhwal (the "<b>FRANCHISOR</b>" or "<b>PURNABRAMHA</b>") 
        of the <b>ONE PART</b>;
        """
        story.append(Paragraph(franchisor_text, normal_style))
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph("<b>AND</b>", ParagraphStyle('And', parent=normal_style, alignment=TA_CENTER)))
        story.append(Spacer(1, 0.1*inch))
        
        # Franchisee
        franchisee_text = f"""
        <b>M/s. {franchise.get('legal_entity_name', '[FRANCHISEE NAME]')}</b>, 
        {'a company incorporated under the provisions of the Companies Act' if is_india else 'a legal entity'}, 
        having its registered office at {franchise.get('address', '[ADDRESS]')}, {franchise.get('city', '')}, 
        {franchise.get('state', '')} - {franchise.get('pincode', '')}, {country}, 
        hereinafter referred to as the "<b>FRANCHISEE</b>" through its Directors/Partners {directors_names or '[DIRECTOR NAMES]'} 
        (which expression shall, unless repugnant to the subject or context thereof, include its successors and assigns) 
        of the <b>OTHER PART</b>.
        """
        story.append(Paragraph(franchisee_text, normal_style))
        story.append(Spacer(1, 0.15*inch))
        
        story.append(Paragraph("The Franchisor and Franchisee herein shall be collectively referred to as \"<b>Parties</b>\" and individually referred to as \"<b>Party</b>\".", normal_style))
        story.append(Spacer(1, 0.2*inch))
        
        # =======================================
        # WHEREAS
        # =======================================
        story.append(Paragraph("<b>WHEREAS:</b>", heading_style))
        
        whereas_points = [
            f"Trade Mark No. 2675785 - \"Purnabramha - The Largest Authentic Maharashtrian Restaurant\" is the trademark registered under Manaswini Foods Pvt Ltd.",
            "The Franchisor Company has developed and owns the Purnabramha brand concept, recipes, operational systems, and intellectual property.",
            f"Purnabramha operates under the FOCO (Franchise Owned - Company Operated) model, offering {franchise_type} format restaurants.",
            f"The Franchisee through its authorized officer approached M/s. {franchisor_name} and requested for a Franchise of 'Purnabramha' brand.",
            f"M/s. {franchisor_name} is permitting the Franchisee to invest in and own a franchise unit while the Franchisor operates and manages the business."
        ]
        
        for point in whereas_points:
            story.append(Paragraph(f"• {point}", small_style))
        
        story.append(Spacer(1, 0.2*inch))
        
        # =======================================
        # DEFINITIONS
        # =======================================
        story.append(Paragraph("<b>1. DEFINITIONS</b>", heading_style))
        
        definitions = [
            ("\"Agreement\"", "means this Agreement, and any amendment/addendum as the same may be supplemented, amended, restated or replaced from time to time."),
            ("\"Effective Date\"", f"shall mean the date of execution of this Agreement, deemed to be {agreement_start or '[DATE]'}."),
            ("\"Franchise Address\"", f"means the only address of the premise to run the awarded Franchise business: {franchise.get('address', '[ADDRESS]')}, {franchise.get('city', '')}."),
            ("\"FOCO Model\"", "means Franchise Owned - Company Operated, wherein the Franchisee invests capital and owns the franchise unit while the Franchisor manages all operations."),
            ("\"Working Capital\"", f"means the operational fund of {format_currency(working_capital, country)} maintained for running the franchise."),
            ("\"Revenue Share\"", f"means {revenue_share}% of Net Revenue payable to the Franchisee."),
            ("\"Term\"", f"means a period of {FRANCHISE_TENURE_YEARS} Years from the Effective Date."),
            ("\"Intellectual Property\"", "means the Trade Marks, Logos, Recipes, Processes, and all proprietary systems of the Franchisor."),
        ]
        
        for term, definition in definitions:
            story.append(Paragraph(f"<b>{term}</b> {definition}", small_style))
        
        story.append(Spacer(1, 0.15*inch))
        
        # =======================================
        # TERM AND TENURE
        # =======================================
        story.append(Paragraph("<b>2. TERM AND TERMINATION</b>", heading_style))
        
        term_text = f"""
        2.1 The term of the Agreement shall be for a fixed period of <b>{FRANCHISE_TENURE_YEARS} (Seven) years</b> 
        starting from {agreement_start or '[OPERATIONS START DATE]'}. The Agreement shall be valid in accordance 
        with the terms and conditions mentioned herein. The tenure is fixed and cannot be automatically extended.
        Any renewal shall require a fresh agreement between the Parties.
        """
        story.append(Paragraph(term_text, normal_style))
        
        story.append(Paragraph("2.2 This Agreement shall be considered terminated immediately on happening of any one of the following:", normal_style))
        
        termination_events = [
            "Either Party enters into liquidation, becomes insolvent, or any statutory licenses are revoked/cancelled/suspended.",
            "Any license or permit required for business is cancelled, revoked, or not renewed.",
            "The Lease/Tenancy Agreement of the Franchise Premises is terminated and business fails to relocate with Franchisor's consent.",
            "Either party fails to procure required government permissions.",
            "Any act that damages the goodwill of the Franchisor.",
            "Franchisee enters into any competitive business in the same vicinity."
        ]
        
        for event in termination_events:
            story.append(Paragraph(f"• {event}", small_style))
        
        story.append(Spacer(1, 0.15*inch))
        
        # =======================================
        # FOCO BUSINESS MODEL
        # =======================================
        story.append(Paragraph("<b>3. FOCO BUSINESS MODEL</b>", heading_style))
        
        foco_text = """
        3.1 Under the FOCO (Franchise Owned - Company Operated) model, the arrangement between the Parties shall be:
        """
        story.append(Paragraph(foco_text, normal_style))
        
        foco_points = [
            "The Franchisee shall invest the capital and own the franchise unit including all physical assets.",
            "The Franchisor shall fully operate and manage the restaurant including all day-to-day operations.",
            "The Franchisor retains full operational authority including menu planning, staff hiring, vendor management, quality control, and brand compliance.",
            "The Franchisee shall not interfere in operational management decisions.",
            "All revenue shall be collected in official company accounts operated by the Franchisor.",
            "Operational expenses (rent, staff salaries, grocery, utilities, marketing, taxes) shall be paid from these accounts.",
        ]
        
        for point in foco_points:
            story.append(Paragraph(f"• {point}", small_style))
        
        story.append(Spacer(1, 0.15*inch))
        
        # =======================================
        # FRANCHISE FEE AND CAPITAL
        # =======================================
        story.append(Paragraph("<b>4. FRANCHISE FEE AND CAPITAL CONTRIBUTION</b>", heading_style))
        
        story.append(Paragraph(f"<b>4.1 Franchise Type:</b> {franchise_type}", normal_style))
        if franchise_type in FRANCHISE_TYPES:
            story.append(Paragraph(f"<i>{FRANCHISE_TYPES[franchise_type]['description']}</i>", small_style))
        
        fee_text = f"""
        <b>4.2 Franchise Fee:</b> The Franchisee shall pay a non-refundable Franchise Fee of 
        <b>{format_currency(franchise_fee, country)}</b> ({format_currency_words(franchise_fee, country)}).
        """
        story.append(Paragraph(fee_text, normal_style))
        
        story.append(Paragraph("The Franchise Fee grants the Franchisee:", normal_style))
        fee_includes = [
            "Brand usage rights for the agreed territory",
            "Access to proprietary recipes and kitchen SOP systems",
            "Training programs for launch",
            "Vendor network access",
            "Launch assistance and operational systems",
        ]
        for item in fee_includes:
            story.append(Paragraph(f"• {item}", small_style))
        
        story.append(Paragraph("<b>The Franchise Fee does NOT include:</b> Interiors, Equipment, Licenses, Rent Deposits, Staff Salary Reserves, or Raw Materials.", small_style))
        
        wc_text = f"""
        <b>4.3 Working Capital:</b> The Franchisee shall maintain Working Capital of 
        <b>{format_currency(working_capital, country)}</b> ({format_currency_words(working_capital, country)}) 
        for operational efficiency during the franchise operations.
        """
        story.append(Paragraph(wc_text, normal_style))
        
        if total_setup > 0:
            story.append(Paragraph("<b>4.4 Setup Costs (to be borne by Franchisee before operations):</b>", normal_style))
            setup_items = [
                ("Shop Security Deposit", setup_costs.get("shop_security_deposit", 0)),
                ("First Month Rent", setup_costs.get("first_month_rent", 0)),
                ("Initial Salary Fund", setup_costs.get("initial_salary_fund", 0)),
                ("Initial Grocery & Raw Materials", setup_costs.get("initial_grocery_cost", 0)),
            ]
            for item, amount in setup_items:
                if amount > 0:
                    story.append(Paragraph(f"• {item}: {format_currency(amount, country)}", small_style))
            story.append(Paragraph(f"<b>Total Setup Costs: {format_currency(total_setup, country)}</b>", small_style))
        
        story.append(Spacer(1, 0.15*inch))
        
        # =======================================
        # REVENUE MODEL (INDIA SPECIFIC)
        # =======================================
        story.append(Paragraph("<b>5. REVENUE MODEL AND FINANCIAL STRUCTURE</b>", heading_style))
        
        if is_india:
            revenue_text = f"""
            5.1 All revenue from the restaurant shall be collected in official company accounts operated by 
            Manaswini Foods Pvt Ltd. After deduction of all operational expenses, the Franchisee shall receive 
            a Revenue Share of <b>{revenue_share}% of Net Revenue</b>.
            """
            story.append(Paragraph(revenue_text, normal_style))
            
            story.append(Paragraph("5.2 Operational expenses paid from revenue include:", normal_style))
            expense_items = ["Rent", "Staff Salaries", "Grocery & Supplies", "Utilities", "Maintenance", "Marketing", "Taxes", "Operations Cost"]
            story.append(Paragraph(f"• {', '.join(expense_items)}", small_style))
            
            story.append(Paragraph(f"""
            5.3 After operational expenses, the remaining balance becomes the profit share of {franchisor_name}.
            """, normal_style))
        else:
            story.append(Paragraph(f"""
            5.1 The revenue model for international franchises shall be determined based on local market conditions 
            and agreed upon separately in the Annexure to this Agreement.
            """, normal_style))
        
        story.append(Spacer(1, 0.15*inch))
        
        # =======================================
        # WORKING CAPITAL PROTECTION
        # =======================================
        story.append(Paragraph("<b>6. WORKING CAPITAL PROTECTION CLAUSE</b>", heading_style))
        
        wc_protection = f"""
        6.1 If the Working Capital of the restaurant falls below <b>50% (Fifty Percent)</b> of the originally 
        committed Working Capital amount of {format_currency(working_capital, country)}, the following shall apply:
        """
        story.append(Paragraph(wc_protection, normal_style))
        
        story.append(Paragraph("• Franchisee Revenue Share becomes <b>0% (Zero Percent)</b>", small_style))
        story.append(Paragraph("• Profit Distribution becomes <b>0% (Zero Percent)</b>", small_style))
        story.append(Paragraph(f"""
        6.2 This condition shall remain active until the Working Capital is restored to its original committed 
        level of {format_currency(working_capital, country)}. Once restored, the normal revenue sharing structure shall resume.
        """, normal_style))
        
        story.append(Spacer(1, 0.15*inch))
        
        # =======================================
        # SERVICE CONTRACT FEE
        # =======================================
        story.append(Paragraph("<b>7. SERVICE CONTRACT FEE</b>", heading_style))
        
        service_text = f"""
        7.1 Every franchise center shall pay a monthly Service Contract Fee of 
        <b>{format_currency(service_fee, country)} per month</b>.
        """
        story.append(Paragraph(service_text, normal_style))
        
        story.append(Paragraph("7.2 This fee covers:", normal_style))
        service_covers = [
            "Brand management and quality monitoring",
            "Menu updates and kitchen SOP systems",
            "Vendor coordination and operations guidance",
            "Marketing support and technology systems"
        ]
        for item in service_covers:
            story.append(Paragraph(f"• {item}", small_style))
        
        story.append(Paragraph("""
        7.3 The central management salary pool of the Purnabramha leadership team shall be distributed 
        proportionately across all operating franchise centers. Each center contributes a proportional operational share.
        """, normal_style))
        
        story.append(Spacer(1, 0.15*inch))
        
        # =======================================
        # OPERATIONAL CONTROL
        # =======================================
        story.append(Paragraph("<b>8. OPERATIONAL CONTROL AND RESPONSIBILITIES</b>", heading_style))
        
        story.append(Paragraph("8.1 Under the FOCO model, the Franchisor retains full operational authority including:", normal_style))
        
        ops_authority = [
            "Menu and food quality standards",
            "Hiring, training, and staff structure",
            "Vendor approvals and procurement",
            "Accounting systems and financial management",
            "Marketing strategy and brand compliance",
            "Technology and POS systems"
        ]
        for item in ops_authority:
            story.append(Paragraph(f"• {item}", small_style))
        
        story.append(Paragraph("""
        8.2 The Franchisor shall provide daily updates to the Franchisee ensuring transparency and 
        collaborative relationship throughout the tenure of the agreement.
        """, normal_style))
        
        # Page break for remaining sections
        story.append(PageBreak())
        
        # =======================================
        # INTELLECTUAL PROPERTY
        # =======================================
        story.append(Paragraph("<b>9. INTELLECTUAL PROPERTY RIGHTS</b>", heading_style))
        
        ip_text = """
        9.1 The brand name Purnabramha is registered in the name of Manaswini Foods Private Limited and is 
        not transferred to any Party by virtue of this or any other Agreement. None of the Parties hereto 
        shall acquire or claim any right, title or interest in the intellectual property owned by the Franchisor.
        
        9.2 The Franchisee shall not use any intellectual property except as approved by the Franchisor in writing 
        for performance of obligations under this Agreement. The provisions of this Clause shall survive termination.
        """
        story.append(Paragraph(ip_text, normal_style))
        
        story.append(Spacer(1, 0.15*inch))
        
        # =======================================
        # CONFIDENTIALITY
        # =======================================
        story.append(Paragraph("<b>10. CONFIDENTIALITY</b>", heading_style))
        
        conf_text = """
        10.1 The Parties agree to maintain strict confidence and secrecy in respect of the terms and conditions 
        of this Agreement and all information of a secret, proprietary and confidential nature received pursuant 
        to this Agreement. This Confidentiality provision shall survive for a period of two (2) years from 
        the expiry or termination of this Agreement.
        """
        story.append(Paragraph(conf_text, normal_style))
        
        story.append(Spacer(1, 0.15*inch))
        
        # =======================================
        # GOVERNING LAW
        # =======================================
        story.append(Paragraph("<b>11. GOVERNING LAW AND JURISDICTION</b>", heading_style))
        
        if is_india:
            law_text = f"""
            11.1 This Agreement shall be governed by and subject to the laws of India. This Agreement shall be 
            subject to the exclusive jurisdiction of the courts of {jurisdiction}.
            
            11.2 In case of disputes or differences arising between the Parties, unless settled amicably, 
            shall be referred to arbitration under the Arbitration and Conciliation Act 1996 by a sole arbitrator 
            appointed by mutual consent. The venue of arbitration shall be {jurisdiction}, India.
            """
        else:
            law_text = f"""
            11.1 This Agreement shall be governed by the applicable laws of {country}. Disputes shall be 
            subject to the jurisdiction of competent courts in {jurisdiction}.
            """
        story.append(Paragraph(law_text, normal_style))
        
        story.append(Spacer(1, 0.3*inch))
        
        # =======================================
        # SIGNATURE SECTION
        # =======================================
        story.append(Paragraph("<b>12. SIGNATURES</b>", heading_style))
        
        story.append(Paragraph("""
        IN WITNESS WHEREOF, the parties hereto have executed this Franchise Agreement as of the date first above written.
        """, normal_style))
        
        story.append(Spacer(1, 0.4*inch))
        
        # Signature table
        sig_data = [
            ["<b>FOR FRANCHISOR</b>", "<b>FOR FRANCHISEE</b>"],
            [f"{franchisor_name}", f"{franchise.get('legal_entity_name', '[FRANCHISEE NAME]')}"],
            ["", ""],
            ["_______________________________", "_______________________________"],
            ["Mrs. Jayanti Kathale", directors_names.split(',')[0] if directors_names else "[DIRECTOR NAME]"],
            ["Director", "Director/Partner"],
            ["", ""],
            ["_______________________________", ""],
            ["Mr. Sandeep Gadhwal", ""],
            ["Director", ""],
            ["", ""],
            ["Date: _______________________", "Date: _______________________"],
        ]
        
        sig_table = Table(sig_data, colWidths=[3*inch, 3*inch])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(sig_table)
        
        # Build PDF
        doc.build(story)
        
        buffer.seek(0)
        filename = f"FOCO_Agreement_{franchise_code.upper()}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # Log audit
        await log_audit(franchise_code.upper(), "AGREEMENT_GENERATED", session, {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "format": output_format,
            "franchise_type": franchise_type,
            "franchise_fee": franchise_fee
        })
        
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
        
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
