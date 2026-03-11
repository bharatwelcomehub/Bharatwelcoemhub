# =======================================
# Franchise Management Routes
# CRUD for Franchise records, Documents, Agreements
# =======================================

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Response
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
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
# PYDANTIC MODELS
# =======================================

class DirectorInfo(BaseModel):
    name: str
    email: Optional[str] = ""
    phone: Optional[str] = ""
    designation: Optional[str] = "Director"
    address: Optional[str] = ""

class FranchiseCreate(BaseModel):
    franchise_code: str  # Unique code like "FR-001"
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
    
    # Directors
    directors: List[DirectorInfo] = []
    
    # Agreement details
    agreement_start_date: Optional[str] = ""  # YYYY-MM-DD
    agreement_end_date: Optional[str] = ""    # YYYY-MM-DD
    franchise_fee: Optional[float] = 0
    royalty_percentage: Optional[float] = 0
    
    # Status
    status: str = "Active"  # Active, Inactive, Terminated, Pending
    
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
    agreement_start_date: Optional[str] = None
    agreement_end_date: Optional[str] = None
    franchise_fee: Optional[float] = None
    royalty_percentage: Optional[float] = None
    status: Optional[str] = None
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
    franchise = {
        "franchise_code": franchise_code,
        "franchise_name": data.get("franchise_name", "").strip(),
        "legal_entity_name": data.get("legal_entity_name", "").strip(),
        "country": data.get("country", "India"),
        "state": data.get("state", "").strip(),
        "city": data.get("city", "").strip(),
        "address": data.get("address", "").strip(),
        "pincode": data.get("pincode", "").strip(),
        "primary_contact_name": data.get("primary_contact_name", "").strip(),
        "primary_contact_email": data.get("primary_contact_email", "").strip().lower(),
        "primary_contact_phone": data.get("primary_contact_phone", "").strip(),
        "directors": data.get("directors", []),
        "agreement_start_date": data.get("agreement_start_date", ""),
        "agreement_end_date": data.get("agreement_end_date", ""),
        "franchise_fee": float(data.get("franchise_fee", 0) or 0),
        "royalty_percentage": float(data.get("royalty_percentage", 0) or 0),
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
        "agreement_end_date", "franchise_fee", "royalty_percentage", "status", "notes"
    ]
    
    changes = {}
    for field in updatable_fields:
        if field in data and data[field] is not None:
            new_value = data[field]
            old_value = existing.get(field)
            
            # Handle special types
            if field in ["franchise_fee", "royalty_percentage"]:
                new_value = float(new_value or 0)
            elif field == "primary_contact_email" and isinstance(new_value, str):
                new_value = new_value.strip().lower()
            elif isinstance(new_value, str):
                new_value = new_value.strip()
            
            if new_value != old_value:
                update_fields[field] = new_value
                changes[field] = {"old": old_value, "new": new_value}
    
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
# AGREEMENT GENERATION
# =======================================

@router.post("/generate-agreement/{franchise_code}")
async def generate_agreement(franchise_code: str, req: TokenRequest):
    """Generate a Franchise Agreement PDF"""
    session = await check_access(req.token)
    
    franchise = await db.franchises.find_one(
        {"franchise_code": franchise_code.upper()},
        {"_id": 0}
    )
    
    if not franchise:
        raise HTTPException(404, "Franchise not found")
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch, cm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                               leftMargin=1*inch, rightMargin=1*inch,
                               topMargin=1*inch, bottomMargin=1*inch)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], 
                                     fontSize=18, alignment=1, spaceAfter=20)
        heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], 
                                       fontSize=14, spaceAfter=10, spaceBefore=15)
        normal_style = ParagraphStyle('Normal', parent=styles['Normal'], 
                                      fontSize=11, spaceAfter=8, alignment=4)
        
        story = []
        
        # Title
        story.append(Paragraph("FRANCHISE AGREEMENT", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Parties
        story.append(Paragraph("PARTIES TO THIS AGREEMENT", heading_style))
        
        franchisor_text = """
        <b>FRANCHISOR:</b><br/>
        Manaswini Foods Pvt. Ltd. (Trading as "Purnabramha")<br/>
        17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout<br/>
        Bangalore, Karnataka - 560102, India<br/>
        """
        story.append(Paragraph(franchisor_text, normal_style))
        
        # Franchisee details
        directors_text = ""
        for d in franchise.get("directors", []):
            directors_text += f"{d.get('name', 'N/A')} ({d.get('designation', 'Director')})<br/>"
        if not directors_text:
            directors_text = "N/A"
        
        franchisee_text = f"""
        <b>FRANCHISEE:</b><br/>
        {franchise.get('legal_entity_name', 'N/A')}<br/>
        {franchise.get('address', 'N/A')}<br/>
        {franchise.get('city', '')}, {franchise.get('state', '')} - {franchise.get('pincode', '')}<br/>
        {franchise.get('country', 'India')}<br/>
        <br/>
        <b>Directors:</b><br/>
        {directors_text}
        """
        story.append(Paragraph(franchisee_text, normal_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Agreement Details
        story.append(Paragraph("AGREEMENT DETAILS", heading_style))
        
        details_text = f"""
        <b>Franchise Code:</b> {franchise.get('franchise_code', 'N/A')}<br/>
        <b>Agreement Start Date:</b> {franchise.get('agreement_start_date', 'N/A')}<br/>
        <b>Agreement End Date:</b> {franchise.get('agreement_end_date', 'N/A')}<br/>
        <b>Franchise Fee:</b> {franchise.get('franchise_fee', 0):,.2f}<br/>
        <b>Royalty Percentage:</b> {franchise.get('royalty_percentage', 0)}%<br/>
        """
        story.append(Paragraph(details_text, normal_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Terms and Conditions
        story.append(Paragraph("TERMS AND CONDITIONS", heading_style))
        
        terms = [
            "The Franchisee agrees to operate the franchise in accordance with the operational standards set by Purnabramha.",
            "The Franchisee shall maintain the quality standards as specified in the Operations Manual.",
            "The Franchisee agrees to pay the franchise fee and ongoing royalty as specified above.",
            "The Franchisor shall provide training, support, and brand guidelines to the Franchisee.",
            "This agreement is valid for the term specified above and may be renewed upon mutual consent.",
            "Either party may terminate this agreement with 90 days written notice.",
            "All intellectual property including the Purnabramha brand, recipes, and processes remain the property of the Franchisor.",
            "The Franchisee shall not operate any competing business during the term of this agreement."
        ]
        
        for i, term in enumerate(terms, 1):
            story.append(Paragraph(f"{i}. {term}", normal_style))
        
        story.append(Spacer(1, 0.5*inch))
        
        # Signature Section
        story.append(Paragraph("SIGNATURES", heading_style))
        
        sig_text = """
        <br/><br/>
        _______________________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;_______________________________<br/>
        For Franchisor (Purnabramha)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;For Franchisee<br/>
        <br/>
        Date: _____________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Date: _____________________<br/>
        """
        story.append(Paragraph(sig_text, normal_style))
        
        doc.build(story)
        
        buffer.seek(0)
        filename = f"Franchise_Agreement_{franchise_code.upper()}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # Log audit
        await log_audit(franchise_code.upper(), "AGREEMENT_GENERATED", session, {
            "generated_at": datetime.now(timezone.utc).isoformat()
        })
        
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
        
    except Exception as e:
        logger.error(f"Error generating agreement: {e}")
        raise HTTPException(500, f"Error generating agreement: {str(e)}")

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
