# =======================================
# Purnabramha IntraPB - Backend Server
# MongoDB-based Attendance & Salary System
# =======================================

from fastapi import FastAPI, APIRouter, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import random
import string
import secrets
import smtplib
from email.message import EmailMessage
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from io import BytesIO
import calendar
import json
import re

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Load config.json for email settings (same as your original server.py)
def load_config() -> dict:
    path = ROOT_DIR / "config.json"
    if not path.exists():
        return {
            "otp": {"length": 6, "ttl_seconds": 300},
            "security": {"session_ttl_seconds": 7200},  # 2 hours minimum as requested
            "email": {
                "enabled": False,
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_user": "",
                "smtp_pass": "",
                "from_name": "Purnabramha Attendance",
                "from_email": ""
            }
        }
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

CFG = load_config()
OTP_LEN = int((CFG.get("otp") or {}).get("length", 6))
OTP_TTL = int((CFG.get("otp") or {}).get("ttl_seconds", 300))

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="Purnabramha IntraPB API")
api_router = APIRouter(prefix="/api")

# Static files
static_path = ROOT_DIR / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# OTP Storage - Now using MongoDB for persistence across server restarts
# The otp_store dict is kept for backward compatibility with existing code
# but all data is now persisted to MongoDB 'sessions' collection
otp_store: Dict[str, Dict] = {}

# =======================================
# SESSION PERSISTENCE HELPERS (MongoDB)
# =======================================

async def save_session_to_db(key: str, session_data: dict):
    """Save session to MongoDB for persistence"""
    try:
        session_doc = {
            "key": key,
            **session_data,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.sessions.update_one(
            {"key": key},
            {"$set": session_doc},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error saving session to DB: {e}")

async def get_session_from_db(key: str) -> Optional[dict]:
    """Get session from MongoDB"""
    try:
        session = await db.sessions.find_one({"key": key}, {"_id": 0})
        return session
    except Exception as e:
        logger.error(f"Error getting session from DB: {e}")
        return None

async def get_session_by_token(token: str) -> Optional[dict]:
    """Get session by token from MongoDB"""
    try:
        session = await db.sessions.find_one({"token": token}, {"_id": 0})
        return session
    except Exception as e:
        logger.error(f"Error getting session by token from DB: {e}")
        return None

async def delete_session_from_db(key: str):
    """Delete session from MongoDB"""
    try:
        await db.sessions.delete_one({"key": key})
    except Exception as e:
        logger.error(f"Error deleting session from DB: {e}")

async def delete_session_by_token(token: str):
    """Delete session by token from MongoDB"""
    try:
        await db.sessions.delete_one({"token": token})
    except Exception as e:
        logger.error(f"Error deleting session by token from DB: {e}")

# =======================================
# PYDANTIC MODELS
# =======================================

class OTPRequest(BaseModel):
    center: str
    mobile: str

class OTPVerify(BaseModel):
    center: str
    mobile: str
    otp: str

class EmployeeCreate(BaseModel):
    center: str
    name: str
    gender: Optional[str] = ""
    designation: Optional[str] = ""
    salaryBase: Optional[float] = 0
    dateOfJoining: Optional[str] = ""
    currentSalary: Optional[float] = 0
    bankName: Optional[str] = ""
    beneAccNo: Optional[str] = ""
    ifsc: Optional[str] = ""
    mobile: Optional[str] = ""
    email: Optional[str] = ""
    remark: Optional[str] = ""

class AttendanceRecord(BaseModel):
    employeeName: str
    designation: Optional[str] = ""
    status: str  # P, A, HD, WO, L
    notes: Optional[str] = ""

class BulkAttendance(BaseModel):
    token: str
    center: str
    date: str
    submittedBy: Optional[str] = ""
    rows: List[AttendanceRecord]

class AdvanceRecord(BaseModel):
    employeeName: str
    advanceAmount: float
    mode: str  # CASH, GPAY, NEFT, ONLINE
    notes: Optional[str] = ""

class BulkAdvances(BaseModel):
    token: str
    center: str
    date: str
    submittedBy: Optional[str] = ""
    rows: List[AdvanceRecord]

class MonthlyCell(BaseModel):
    employeeName: str
    day: int
    status: str
    notes: Optional[str] = ""

class BulkMonthlyAttendance(BaseModel):
    token: str
    center: str
    month: str  # YYYY-MM
    submittedBy: Optional[str] = ""
    cells: List[MonthlyCell]

class TokenRequest(BaseModel):
    token: str
    center: str

class MonthRequest(BaseModel):
    token: str
    center: str
    month: str

class DateRequest(BaseModel):
    token: str
    center: str
    date: str

class SalaryGenRequest(BaseModel):
    token: str
    center: str
    month: str
    mode: str  # single or all
    targetCenter: Optional[str] = None

class SalaryPreviewRequest(BaseModel):
    token: str
    month: str
    targetCenter: str

class PayslipGenRequest(BaseModel):
    token: str
    center: str
    month: str
    period: str  # 1, 3, 6
    fmt: str  # pdf or docx
    mode: str  # bulk or single
    targetCenter: Optional[str] = None
    employeeName: Optional[str] = None

# =======================================
# HELPER FUNCTIONS
# =======================================

def generate_otp():
    lo = 10 ** (OTP_LEN - 1)
    hi = (10 ** OTP_LEN) - 1
    return str(random.randint(lo, hi))

def generate_token():
    return secrets.token_urlsafe(32)

def verify_token_sync(token: str) -> Optional[Dict]:
    """
    Synchronous token verification (for backward compatibility).
    Checks in-memory store first, then falls back to DB check via async.
    This is a fallback - prefer verify_token_async when possible.
    """
    session_ttl = int((CFG.get("security") or {}).get("session_ttl_seconds", 7200))
    
    # Check in-memory store first
    for key, data in otp_store.items():
        if data.get("token") == token:
            token_created = data.get("token_created_at")
            if token_created:
                try:
                    created_time = datetime.fromisoformat(token_created.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    elapsed = (now - created_time).total_seconds()
                    
                    if elapsed > session_ttl:
                        logger.info(f"Token expired for {data.get('center')} - elapsed {elapsed}s > TTL {session_ttl}s")
                        del otp_store[key]
                        return None
                except Exception as e:
                    logger.warning(f"Error checking token expiry: {e}")
            return data
    return None

async def verify_token_async(token: str) -> Optional[Dict]:
    """
    Async token verification using MongoDB for persistence.
    This is the preferred method - tokens survive server restarts.
    """
    session_ttl = int((CFG.get("security") or {}).get("session_ttl_seconds", 7200))
    
    # First check in-memory for speed
    for key, data in otp_store.items():
        if data.get("token") == token:
            token_created = data.get("token_created_at")
            if token_created:
                try:
                    created_time = datetime.fromisoformat(token_created.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    elapsed = (now - created_time).total_seconds()
                    
                    if elapsed > session_ttl:
                        logger.info(f"Token expired for {data.get('center')} - elapsed {elapsed}s > TTL {session_ttl}s")
                        del otp_store[key]
                        await delete_session_by_token(token)
                        return None
                except Exception as e:
                    logger.warning(f"Error checking token expiry: {e}")
            return data
    
    # If not in memory, check MongoDB (handles server restart case)
    try:
        session = await get_session_by_token(token)
        if session:
            token_created = session.get("token_created_at")
            if token_created:
                try:
                    created_time = datetime.fromisoformat(token_created.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    elapsed = (now - created_time).total_seconds()
                    
                    if elapsed > session_ttl:
                        logger.info(f"Token expired (from DB) for {session.get('center')} - elapsed {elapsed}s > TTL {session_ttl}s")
                        await delete_session_by_token(token)
                        return None
                except Exception as e:
                    logger.warning(f"Error checking token expiry from DB: {e}")
            
            # Restore to in-memory cache
            key = session.get("key")
            if key:
                otp_store[key] = session
            return session
    except Exception as e:
        logger.error(f"Error verifying token from DB: {e}")
    
    return None

def verify_token(token: str) -> Optional[Dict]:
    """
    Backward compatible verify_token function.
    Note: This is sync but the async version is preferred for persistence.
    """
    return verify_token_sync(token)

def has_admin_access(session) -> bool:
    """Check if user has admin/super admin access (RBAC-driven, no center hardcoding)"""
    if not session:
        return False
    if session.get("is_super_admin"):
        return True
    if session.get("is_admin"):
        return True
    return False

def has_all_centers_access(session) -> bool:
    """Check if user can view all centers data"""
    if has_admin_access(session):
        return True
    roles = session.get("roles", {})
    return roles.get("view_all_centers", False)

def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]

def send_otp_email(to_email: str, otp: str, manager_name: str, center: str) -> bool:
    """Send OTP via SMTP email - EXACT method from your original server.py"""
    email_cfg = CFG.get("email", {}) or {}
    
    if not email_cfg.get("enabled"):
        logger.warning("Email is disabled in config.json. OTP will be logged only.")
        return False
    
    smtp_host = email_cfg.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(email_cfg.get("smtp_port", 587))
    smtp_user = email_cfg.get("smtp_user", "")
    smtp_pass = email_cfg.get("smtp_pass", "")
    from_name = email_cfg.get("from_name", "Purnabramha Attendance")
    from_email = email_cfg.get("from_email", smtp_user)
    
    if not smtp_user or not smtp_pass:
        logger.warning("SMTP credentials not configured in config.json. OTP will be logged only.")
        return False
    
    try:
        msg = EmailMessage()
        msg["Subject"] = "Your PB Attendance Login OTP"
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email
        msg.set_content(
            f"Dear {manager_name},\n\n"
            f"Your OTP is: {otp}\n\n"
            f"Center: {center}\n"
            f"Valid for {OTP_TTL//60} minutes.\n\n"
            "– Purnabramha Team\n"
        )
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        
        logger.info(f"OTP email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"[OTP-EMAIL-FAIL] {e}")
        return False

# =======================================
# AUTH ENDPOINTS
# =======================================

@api_router.post("/send_otp")
async def send_otp(req: OTPRequest):
    """Send OTP to manager's email"""
    # Find manager in database
    manager = await db.managers.find_one({
        "center": req.center.upper(),
        "$or": [
            {"mobile": req.mobile},
            {"mobile": req.mobile.lstrip("0")},  # Handle leading zeros
        ]
    }, {"_id": 0})
    
    if not manager:
        # For demo, allow any center-mobile combo
        manager = await db.managers.find_one({"center": req.center.upper()}, {"_id": 0})
        if not manager:
            raise HTTPException(400, "Center not found or mobile not registered")
    
    otp = generate_otp()
    key = f"{req.center}_{req.mobile}"
    manager_email = manager.get("email", "")
    manager_name = manager.get("managerName", "Manager")
    
    session_data = {
        "otp": otp,
        "center": req.center.upper(),
        "mobile": req.mobile,
        "managerName": manager_name,
        "email": manager_email,
        "created": datetime.now(timezone.utc).isoformat()
    }
    
    # Save to both in-memory and MongoDB for persistence
    otp_store[key] = session_data
    await save_session_to_db(key, session_data)
    
    # Always log OTP for development/debugging
    logger.info(f"OTP for {req.center}/{req.mobile}: {otp}")
    
    # Try to send email if configured
    email_sent = False
    if manager_email:
        email_sent = send_otp_email(manager_email, otp, manager_name, req.center.upper())
    
    if email_sent:
        # Mask email for response
        email_parts = manager_email.split("@")
        masked_email = email_parts[0][:3] + "***@" + email_parts[1] if len(email_parts) == 2 else "***"
        return {"success": True, "message": f"OTP sent to {masked_email}"}
    else:
        return {"success": True, "message": "OTP generated (check server console for dev mode)"}

@api_router.post("/verify_otp")
async def verify_otp(req: OTPVerify):
    """Verify OTP and return session token"""
    key = f"{req.center}_{req.mobile}"
    
    # Check in-memory first, then MongoDB
    stored = otp_store.get(key)
    if not stored:
        # Try to get from MongoDB (handles server restart case)
        stored = await get_session_from_db(key)
        if stored:
            otp_store[key] = stored  # Restore to memory
    
    if not stored:
        raise HTTPException(400, "OTP expired or not requested")
    
    # For development, accept "123456" as master OTP
    if req.otp != stored["otp"] and req.otp != "123456":
        raise HTTPException(400, "Invalid OTP")
    
    token = generate_token()
    stored["token"] = token
    stored["token_created_at"] = datetime.now(timezone.utc).isoformat()  # Track when token was created for expiry
    
    # SUPER ADMIN - Only these two people (by mobile number)
    SUPER_ADMIN_MOBILES = ["9741399190", "9960886185"]  # Jayanti and Sandeep
    is_super_admin = req.mobile in SUPER_ADMIN_MOBILES
    
    # Fetch manager's profile and roles from database
    manager = await db.managers.find_one({
        "center": stored["center"],
        "$or": [
            {"mobile": req.mobile},
            {"mobile": req.mobile.lstrip("0")},
        ]
    }, {"_id": 0, "roles": 1, "is_admin": 1, "email": 1, "role_key": 1, "franchise_center": 1, "franchise_id": 1})
    
    # Fallback: If no manager found by mobile, try to find by center alone
    # This handles cases where managers don't have mobile numbers registered
    if not manager:
        manager = await db.managers.find_one(
            {"center": stored["center"]},
            {"_id": 0, "roles": 1, "is_admin": 1, "email": 1, "role_key": 1, "franchise_center": 1, "franchise_id": 1}
        )
    
    # Get roles from DB - these are assigned by super admin
    db_roles = manager.get("roles", {}) if manager else {}
    is_admin = manager.get("is_admin", False) if manager else False
    
    # Super admins get all access automatically
    if is_super_admin:
        roles = {
            "attendance": True,
            "sales_cash": True,
            "hr": True,
            "mgt": True,
            "operations": True,
            "view_all_centers": True
        }
        is_admin = True
    else:
        # Regular users get their assigned roles from database
        roles = db_roles
    
    stored["roles"] = roles
    stored["is_super_admin"] = is_super_admin
    stored["is_admin"] = is_admin
    stored["email"] = manager.get("email", "") if manager else ""
    stored["role_key"] = manager.get("role_key", "") if manager else ""
    stored["franchise_center"] = manager.get("franchise_center", "") if manager else ""
    stored["franchise_id"] = manager.get("franchise_id", "") if manager else ""
    
    # ── RESOLVE FRANCHISE CENTER FROM DB MAPPING ──
    # If role_key is "franchise_owner" and franchise_center is empty, resolve from DB
    if stored["role_key"] == "franchise_owner" and not stored["franchise_center"]:
        resolved_center = ""
        resolved_franchise_code = ""
        login_center = stored.get("center", "")
        
        # Method 1: Check if the login center has a franchise_code in the centers collection
        center_doc = await db.centers.find_one(
            {"code": login_center, "franchise_code": {"$exists": True, "$ne": ""}},
            {"_id": 0, "franchise_code": 1}
        )
        if center_doc:
            resolved_center = login_center
            resolved_franchise_code = center_doc["franchise_code"]
        
        # Method 2: Check franchise_id → franchise → center mapping
        if not resolved_center and stored.get("franchise_id"):
            franchise_doc = await db.franchises.find_one(
                {"franchise_code": stored["franchise_id"]},
                {"_id": 0, "center": 1, "centers_mapped": 1}
            )
            if franchise_doc:
                resolved_franchise_code = stored["franchise_id"]
                resolved_center = franchise_doc.get("center", "")
                if not resolved_center and franchise_doc.get("centers_mapped"):
                    resolved_center = franchise_doc["centers_mapped"][0]
        
        # Method 3: Find franchise that maps to the login center
        if not resolved_center:
            franchise_doc = await db.franchises.find_one(
                {"$or": [{"center": login_center}, {"centers_mapped": login_center}]},
                {"_id": 0, "franchise_code": 1, "center": 1}
            )
            if franchise_doc:
                resolved_center = login_center
                resolved_franchise_code = franchise_doc.get("franchise_code", "")
        
        if resolved_center:
            stored["franchise_center"] = resolved_center
            stored["franchise_code"] = resolved_franchise_code
            logger.info(f"Resolved franchise center for owner: {resolved_center} (franchise: {resolved_franchise_code})")
        else:
            # Fallback: use login center
            stored["franchise_center"] = login_center
            logger.warning(f"Could not resolve franchise center for {login_center}, using login center")
    
    # Also store franchise_code if resolved
    if not stored.get("franchise_code"):
        stored["franchise_code"] = ""
    stored["key"] = key  # Add key for MongoDB lookup
    
    # Save to both in-memory and MongoDB for persistence
    otp_store[key] = stored
    await save_session_to_db(key, stored)
    
    # Log session creation with expiry info
    session_ttl = int((CFG.get("security") or {}).get("session_ttl_seconds", 7200))
    logger.info(f"Session created for {req.center}/{req.mobile} - valid for {session_ttl}s ({session_ttl//3600}h {(session_ttl%3600)//60}m) - persisted to MongoDB")
    
    return {
        "success": True,
        "token": token,
        "center": stored["center"],
        "managerName": stored.get("managerName", "Manager"),
        "mobile": req.mobile,
        "roles": roles,
        "is_super_admin": is_super_admin,
        "is_admin": is_admin,
        "role_key": stored.get("role_key", ""),
        "franchise_center": stored.get("franchise_center", ""),
        "franchise_id": stored.get("franchise_id", ""),
        "franchise_code": stored.get("franchise_code", ""),
        "session_expires_in_seconds": session_ttl
    }

# =======================================
# EMPLOYEE ENDPOINTS
# =======================================

@api_router.post("/employees")
async def get_employees(req: TokenRequest):
    """Get employees for a center (transfer-aware)"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    center = req.center.upper()
    date = getattr(req, 'date', None) or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Home employees
    employees = await db.employees.find({"center": center}, {"_id": 0}).sort("name", 1).to_list(1000)
    
    # Get transfer context for today
    # Transferred IN to this center
    transferred_in = await db.transfer_requests.find({
        "to_center": center,
        "status": "ACCEPTED",
        "start_date": {"$lte": date},
        "$or": [
            {"end_date": {"$gte": date}},
            {"end_date": None},
            {"end_date": ""},
            {"transfer_type": "PERMANENT"}
        ]
    }, {"_id": 0}).to_list(500)
    
    # Transferred OUT of this center
    transferred_out = await db.transfer_requests.find({
        "from_center": center,
        "status": "ACCEPTED",
        "start_date": {"$lte": date},
        "$or": [
            {"end_date": {"$gte": date}},
            {"end_date": None},
            {"end_date": ""},
            {"transfer_type": "PERMANENT"}
        ]
    }, {"_id": 0}).to_list(500)
    
    out_names = {t["employee_name"].upper() for t in transferred_out}
    in_names = {t["employee_name"].upper() for t in transferred_in}
    in_details = {}
    for t in transferred_in:
        in_details[t["employee_name"].upper()] = t["from_center"]
    out_details = {}
    for t in transferred_out:
        out_details[t["employee_name"].upper()] = t["to_center"]
    
    # Tag home employees
    for emp in employees:
        name = emp.get("name", "").upper()
        if name in out_names:
            emp["transfer_tag"] = "TRANSFERRED_OUT"
            emp["transfer_to"] = out_details.get(name, "")
        else:
            emp["transfer_tag"] = "HOME"
    
    # Add transferred-in employees
    for t in transferred_in:
        emp_name = t["employee_name"].upper()
        if not any(e.get("name", "").upper() == emp_name for e in employees):
            emp = await db.employees.find_one({"name": emp_name}, {"_id": 0})
            if emp:
                emp["transfer_tag"] = "TRANSFERRED_IN"
                emp["transfer_from"] = t["from_center"]
                employees.append(emp)
    
    return {"employees": employees}

@api_router.post("/mgt_employees_list")
async def mgt_employees_list(req: TokenRequest):
    """Get all employees (Admin/MGT only) with search"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if not has_admin_access(session):
        raise HTTPException(403, "Only Admin/Super Admin can access employee management")
    
    employees = await db.employees.find({}, {"_id": 0}).sort("name", 1).to_list(1000)
    
    # Add row index for updates
    for idx, emp in enumerate(employees):
        emp["rowIndex"] = idx
    
    return {"employees": employees}

@api_router.post("/mgt_employee_create")
async def mgt_employee_create(data: dict):
    """Create new employee (Admin/MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    if not session or not has_admin_access(session):
        raise HTTPException(403, "Only Admin/Super Admin can create employees")
    
    employee = {
        "center": data.get("empCenter", "").upper(),
        "name": data.get("name", "").upper(),
        "gender": data.get("gender", ""),
        "designation": data.get("designation", ""),
        "salaryBase": float(data.get("salaryBase", 0) or 0),
        "currentSalary": float(data.get("currentSalary", 0) or 0),
        "dateOfJoining": data.get("dateOfJoining", ""),
        "bankName": data.get("bankName", ""),
        "beneAccNo": data.get("beneAccNo", ""),
        "ifsc": data.get("ifsc", ""),
        "mobile": data.get("mobile", ""),
        "email": data.get("email", ""),
        "remark": data.get("remark", ""),
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.employees.insert_one(employee)
    return {"success": True, "message": "Employee created"}

@api_router.post("/mgt_employee_update")
async def mgt_employee_update(data: dict):
    """Update employee (MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    if not session or not has_admin_access(session):
        raise HTTPException(403, "Only Admin can update employees")
    
    update_data = {
        "center": data.get("empCenter", "").upper(),
        "name": data.get("name", "").upper(),
        "designation": data.get("designation", ""),
        "gender": data.get("gender", ""),
        "currentSalary": float(data.get("currentSalary", 0) or 0),
        "salaryBase": float(data.get("salaryBase", 0) or 0),
        "dateOfJoining": data.get("dateOfJoining", ""),
        "bankName": data.get("bankName", ""),
        "beneAccNo": data.get("beneAccNo", ""),
        "ifsc": data.get("ifsc", ""),
        "mobile": data.get("mobile", ""),
        "email": data.get("email", ""),
        "remark": data.get("remark", ""),
        "updatedAt": datetime.now(timezone.utc).isoformat()
    }
    
    # Find by name and center
    result = await db.employees.update_one(
        {"name": data.get("name", "").upper()},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(404, "Employee not found")
    
    return {"success": True, "message": "Employee updated"}

@api_router.post("/mgt_employee_delete")
async def mgt_employee_delete(data: dict):
    """Delete employee (MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    if not session or not has_admin_access(session):
        raise HTTPException(403, "Only Admin can delete employees")
    
    # Delete by rowIndex is tricky - need to find by name
    employees = await db.employees.find({}, {"_id": 0}).sort("name", 1).to_list(1000)
    row_index = data.get("rowIndex", -1)
    
    if 0 <= row_index < len(employees):
        emp = employees[row_index]
        await db.employees.delete_one({"name": emp["name"]})
        return {"success": True, "message": "Employee deleted"}
    
    raise HTTPException(404, "Employee not found")

@api_router.post("/mgt_employee_bulk_upload")
async def mgt_employee_bulk_upload(data: dict):
    """
    Bulk upload employees from Excel data.
    Expected format: List of employee objects with fields:
    - center, name, gender, designation, salaryBase, currentSalary, 
    - dateOfJoining, bankName, beneAccNo, ifsc, mobile, email, remark
    """
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Only Super Admin or Admin can bulk upload
    is_super_admin = session.get("is_super_admin", False)
    is_admin = session.get("is_admin", False)
    if not is_super_admin and not is_admin:
        raise HTTPException(403, "Only Admin/Super Admin can bulk upload employees")
    
    employees_data = data.get("employees", [])
    if not employees_data:
        raise HTTPException(400, "No employee data provided")
    
    created = 0
    updated = 0
    errors = []
    
    for idx, emp_data in enumerate(employees_data):
        try:
            # Validate required fields
            name = str(emp_data.get("name", "")).strip().upper()
            center = str(emp_data.get("center", "")).strip().upper()
            
            if not name:
                errors.append(f"Row {idx + 1}: Name is required")
                continue
            if not center:
                errors.append(f"Row {idx + 1}: Center is required")
                continue
            
            employee = {
                "center": center,
                "name": name,
                "gender": str(emp_data.get("gender", "")).strip(),
                "designation": str(emp_data.get("designation", "")).strip(),
                "salaryBase": float(emp_data.get("salaryBase", 0) or 0),
                "currentSalary": float(emp_data.get("currentSalary", 0) or 0),
                "dateOfJoining": str(emp_data.get("dateOfJoining", "")).strip(),
                "bankName": str(emp_data.get("bankName", "")).strip(),
                "beneAccNo": str(emp_data.get("beneAccNo", "")).strip(),
                "ifsc": str(emp_data.get("ifsc", "")).strip().upper(),
                "mobile": str(emp_data.get("mobile", "")).strip(),
                "email": str(emp_data.get("email", "")).strip().lower(),
                "remark": str(emp_data.get("remark", "")).strip(),
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }
            
            # Check if employee exists (by name and center)
            existing = await db.employees.find_one({"name": name, "center": center})
            
            if existing:
                # Update existing employee
                await db.employees.update_one(
                    {"name": name, "center": center},
                    {"$set": employee}
                )
                updated += 1
            else:
                # Create new employee
                employee["createdAt"] = datetime.now(timezone.utc).isoformat()
                await db.employees.insert_one(employee)
                created += 1
                
        except Exception as e:
            errors.append(f"Row {idx + 1}: {str(e)}")
    
    logger.info(f"Bulk employee upload: created={created}, updated={updated}, errors={len(errors)} by {session.get('managerName')}")
    
    return {
        "success": True,
        "message": f"Bulk upload complete: {created} created, {updated} updated",
        "created": created,
        "updated": updated,
        "errors": errors[:20] if errors else []  # Return first 20 errors
    }

@api_router.get("/employee_template")
async def get_employee_template():
    """Get the Excel template format for bulk employee upload"""
    # Fetch center codes dynamically from DB
    centers = await db.centers.find({"active": {"$ne": False}}, {"_id": 0, "code": 1}).sort("code", 1).to_list(100)
    center_codes = [c["code"] for c in centers if c.get("code")]
    return {
        "columns": [
            {"field": "center", "header": "Center Code", "required": True, "example": center_codes[0] if center_codes else "PB-HSR", "description": f"Center code ({', '.join(center_codes[:5])}{'...' if len(center_codes) > 5 else ''})"},
            {"field": "name", "header": "Employee Name", "required": True, "example": "JOHN DOE", "description": "Full name in UPPERCASE"},
            {"field": "gender", "header": "Gender", "required": False, "example": "Male", "description": "Male/Female"},
            {"field": "designation", "header": "Designation", "required": False, "example": "Chef", "description": "Job title"},
            {"field": "salaryBase", "header": "Base Salary", "required": False, "example": "15000", "description": "Base salary amount"},
            {"field": "currentSalary", "header": "Current Salary", "required": False, "example": "18000", "description": "Current salary amount"},
            {"field": "dateOfJoining", "header": "Date of Joining", "required": False, "example": "2024-01-15", "description": "YYYY-MM-DD format"},
            {"field": "bankName", "header": "Bank Name", "required": False, "example": "HDFC Bank", "description": "Bank name for salary"},
            {"field": "beneAccNo", "header": "Account Number", "required": False, "example": "1234567890", "description": "Bank account number"},
            {"field": "ifsc", "header": "IFSC Code", "required": False, "example": "HDFC0001234", "description": "Bank IFSC code"},
            {"field": "mobile", "header": "Mobile", "required": False, "example": "9876543210", "description": "Mobile number"},
            {"field": "email", "header": "Email", "required": False, "example": "john@email.com", "description": "Email address"},
            {"field": "remark", "header": "Remarks", "required": False, "example": "Full time", "description": "Any additional notes"}
        ],
        "centers": center_codes
    }

# =======================================
# ATTENDANCE ENDPOINTS
# =======================================

async def is_attendance_locked(date: str) -> dict:
    """Check if attendance is locked for a given date's month"""
    month = date[:7]  # Extract YYYY-MM
    lock = await db.attendance_locks.find_one({"month": month}, {"_id": 0})
    if lock and lock.get("locked"):
        return {"locked": True, "month": month, "locked_by": lock.get("locked_by", "Admin")}
    return {"locked": False}

# Attendance endpoints MOVED to routes/attendance.py (transfer-aware)

# =======================================
# ADVANCES ENDPOINTS
# =======================================

@api_router.post("/bulk_advances")
async def bulk_advances(req: BulkAdvances):
    """Save advances for a date"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    inserted = 0
    updated = 0
    timestamp = datetime.now(timezone.utc).isoformat()
    
    for row in req.rows:
        if row.advanceAmount <= 0:
            continue
            
        doc = {
            "date": req.date,
            "center": req.center.upper(),
            "employeeName": row.employeeName.upper(),
            "advanceAmount": row.advanceAmount,
            "mode": row.mode.upper(),
            "notes": row.notes or "",
            "submittedByMobile": req.submittedBy or session.get("mobile", ""),
            "timestamp": timestamp
        }
        
        result = await db.advances.update_one(
            {"date": req.date, "center": req.center.upper(), "employeeName": row.employeeName.upper()},
            {"$set": doc},
            upsert=True
        )
        
        if result.upserted_id:
            inserted += 1
        else:
            updated += 1
    
    return {"success": True, "inserted": inserted, "updated": updated}

@api_router.post("/advances_by_date")
async def advances_by_date(req: DateRequest):
    """Get advances for a specific date"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    rows = await db.advances.find(
        {"date": req.date, "center": req.center.upper()},
        {"_id": 0}
    ).to_list(1000)
    
    return {"rows": rows}

@api_router.post("/advances_by_month")
async def advances_by_month(req: MonthRequest):
    """Get all advances for a month"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    rows = await db.advances.find(
        {
            "center": req.center.upper(),
            "date": {"$regex": f"^{req.month}"}
        },
        {"_id": 0}
    ).sort("date", 1).to_list(1000)
    
    return {"rows": rows}

# =======================================
# GUEST RESPONSE AI ENDPOINTS
# =======================================

# Center information for AI context - loaded from DB at runtime
# Fallback dict used only if DB has no centers
async def get_center_info_from_db():
    """Fetch center info from DB for AI context"""
    centers = await db.centers.find({}, {"_id": 0}).to_list(100)
    info = {}
    for c in centers:
        code = c.get("code", "")
        info[code] = {
            "name": c.get("name", code),
            "address": c.get("address", ""),
            "phone": c.get("phone", ""),
            "timings": c.get("timings", "12:00 PM - 10:30 PM"),
            "country": c.get("country", "India")
        }
    return info

# System prompt for Guest AI
GUEST_AI_SYSTEM_PROMPT = """You are the Guest Response AI for Purnabramha - The Largest Maharashtrian Restaurant chain.

Jai Hind! Namaskar! Welcome to Purnabramha!

About Purnabramha:
- Authentic Maharashtrian Thali restaurant serving traditional cuisine
- Locations in India (Bangalore, Mumbai, Pune) and Australia (Perth)
- Famous for: Puranpoli, Misal Pav, Vada Pav, Kothimbir Vadi, Bharli Vangi, Sol Kadhi
- Thali-style dining with unlimited servings
- Vegetarian restaurant
- Price range: ₹400-600 per person (India), AUD for Australia
- Online Menu: https://online.fliphtml5.com/mgldc/umnq/

Center Contact Information:
INDIA 🇮🇳
- HSR Bangalore: +91 85500 78515 (Bhagyalakshmi Square, 17/N, 18th Cross Rd, HSR Layout)
- Ch. Sambhajinagar: +91 89710 49084
- Thane Mumbai: +91 89047 49084
- Dombivli Mumbai: +91 96064 55433
- Kharadi Pune: +91 99000 89803
- Hinjawadi Pune: +91 96064 55434
- Kalyan: +91 96064 55433

AUSTRALIA 🇦🇺
- Perth: +61 401 832 922

Timings: 12:00 PM - 10:30 PM (most locations)

Instructions:
1. Answer guest queries politely and professionally
2. Use Marathi phrases like "Namaskar", "Dhanyawad" when appropriate
3. Provide accurate location, timing, and contact information
4. Recommend popular dishes when asked
5. Handle complaints professionally and suggest contacting the center manager
6. If unsure, direct guests to call the nearest center

Remember: You represent Purnabramha's legendary hospitality!"""

class GuestAIRequest(BaseModel):
    token: str
    center: str
    question: str
    sessionId: Optional[str] = None

class GuestAIResponse(BaseModel):
    answer: str
    sessionId: str

@api_router.post("/guest_ai")
async def guest_ai(req: GuestAIRequest):
    """AI-powered guest response for managers"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(500, "AI service not configured")
        
        # Create session ID if not provided
        session_id = req.sessionId or f"guest_{req.center}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Get center context from DB
        center_info_map = await get_center_info_from_db()
        center_info = center_info_map.get(req.center.upper(), {})
        center_context = f"\n\nCurrent Center: {req.center}\n"
        if center_info:
            center_context += f"Center Name: {center_info.get('name', '')}\n"
            center_context += f"Address: {center_info.get('address', '')}\n"
            center_context += f"Phone: {center_info.get('phone', '')}\n"
            center_context += f"Timings: {center_info.get('timings', '')}\n"
        
        # Initialize chat
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=GUEST_AI_SYSTEM_PROMPT + center_context
        ).with_model("openai", "gpt-5.2")
        
        # Send message
        user_message = UserMessage(text=req.question)
        response = await chat.send_message(user_message)
        
        # Store chat history
        await db.chat_history.insert_one({
            "sessionId": session_id,
            "center": req.center,
            "question": req.question,
            "answer": response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "managerMobile": session.get("mobile", "")
        })
        
        return {"answer": response, "sessionId": session_id}
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(500, "AI library not available. Please install emergentintegrations.")
    except Exception as e:
        logger.error(f"Guest AI error: {e}")
        raise HTTPException(500, f"AI service error: {str(e)}")

@api_router.get("/center_info")
async def get_center_info():
    """Get all center information from DB"""
    center_info = await get_center_info_from_db()
    return {"centers": center_info}

# =======================================
# GUEST BOOKING RESPONSE CONVERTER
# Converts raw booking data to WhatsApp-friendly message
# =======================================

class GuestBookingRequest(BaseModel):
    token: str
    center: str
    raw_booking_text: str  # Raw booking data to convert

GUEST_BOOKING_SYSTEM_PROMPT = """You are a warm, hospitable guest communication assistant for Purnabramha - The Largest Maharashtrian Restaurant Chain, a women-led business rooted in authentic Maharashtrian culture.

Your task is to convert raw booking data into a warm, formatted WhatsApp confirmation message.

CRITICAL RULES:
1. Guest name MUST be properly capitalized (e.g., "SHOBHANA" → "Shobhana")
2. Always add "ji" respectfully after the guest name
3. Use LOTS of warm emoticons 🌸🙏✨🍲👨‍👩‍👧‍👦🌺
4. Text must feel warm, Indian hospitality style
5. Proper spacing between sections
6. WhatsApp friendly format (use * for bold)
7. Center-aligned structure visually

EXACT OUTPUT FORMAT (follow this structure precisely):

🌸 Table Booking Confirmed – Purnabramha 🌸

Namaskar [Guest Name] ji 🙏

✨ Your table booking at Purnabramha is confirmed with the following details:

📅 Date: [Date in DD/MM/YYYY format]
⏰ Time: [Time]
👥 Guests: [Number]
👨‍👩‍👧‍👦 Occasion: [Occasion type - Family dining/Birthday/Anniversary/Corporate/Friends gathering etc.]

🍲 We look forward to welcoming you and your family for a comforting, authentic Maharashtrian meal in a warm and homely setting.

📲 If you would like to pre-order or need any assistance, please feel free to reply to this message.

🙏 See you soon!
🌺 Team Purnabramha

OCCASION DETECTION:
- "Family" → "Family dining" with 👨‍👩‍👧‍👦
- "Birthday" → "Birthday celebration" with 🎂
- "Anniversary" → "Anniversary celebration" with 💕
- "Corporate" → "Corporate dining" with 💼
- "Friends" → "Friends gathering" with 🎉
- "Party" → "Party celebration" with 🎊
- "Festival" → "Festival celebration" with 🪔
- Default → "Special dining" with ✨

RAW INPUT FORMAT EXAMPLES:
- "23/02/2026 SHOBHANA New Entry 474739247 7:00 pm – 8:00 pm 4 Family"
- "Name: Sharma, Date: 25 Dec, Time: 8 PM, Guests: 6, Birthday"
- "AMIT KUMAR 9876543210 4 pax dinner tomorrow 7pm anniversary"

Extract: Date, Time, Guest Name, Number of Guests, Contact (if any), Occasion
Then format into the warm WhatsApp message above.

IMPORTANT: Always capitalize the guest name properly and add "ji" respectfully!"""

@api_router.post("/guest/booking-response")
async def generate_booking_response(req: GuestBookingRequest):
    """Convert raw booking data to WhatsApp-friendly message"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(500, "AI service not configured")
        
        # Get center context from DB
        center_info_map = await get_center_info_from_db()
        center_info = center_info_map.get(req.center.upper(), {})
        center_context = f"\n\nCenter: {req.center}\n"
        if center_info:
            center_context += f"Center Name: {center_info.get('name', 'Purnabramha')}\n"
            center_context += f"Address: {center_info.get('address', '')}\n"
            center_context += f"Phone: {center_info.get('phone', '')}\n"
            center_context += f"Timings: {center_info.get('timings', '12:00 PM - 10:30 PM')}\n"
            center_context += f"Country: {center_info.get('country', 'India')}\n"
        
        # Currency context — use center's country field instead of hardcoded check
        is_international = center_info.get("country", "India") != "India"
        currency_context = f"\nCurrency: {'AUD ($)' if is_international else 'INR (₹)'}\n"
        
        # Initialize chat
        chat = LlmChat(
            api_key=api_key,
            session_id=f"booking_{req.center}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            system_message=GUEST_BOOKING_SYSTEM_PROMPT + center_context + currency_context
        ).with_model("openai", "gpt-5.2")
        
        # Create prompt
        prompt = f"""Convert this raw booking information into a beautiful WhatsApp confirmation message:

RAW BOOKING DATA:
{req.raw_booking_text}

Generate a warm, emoji-rich WhatsApp message following the format guidelines. Make it personal and hospitable!"""
        
        # Send message
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Log the generation
        logger.info(f"Booking response generated for {req.center} by {session.get('managerName', 'Unknown')}")
        
        return {
            "success": True,
            "formatted_message": response,
            "center": req.center,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(500, "AI library not available. Please install emergentintegrations.")
    except Exception as e:
        logger.error(f"Booking response error: {e}")
        raise HTTPException(500, f"AI service error: {str(e)}")

# =======================================
# HR LETTERS - MOVED TO routes/hr_letters.py
# CENTERS & MANAGERS - MOVED TO routes/centers_managers.py
# =======================================

# =======================================
# DATA SEEDING ENDPOINT
# =======================================

@api_router.post("/seed_data")
async def seed_data():
    """Seed initial data into MongoDB from Excel export"""
    
    # Seed managers (including both PB-MGT entries)
    managers = [
        {"center": "PB-HSR", "managerName": "Center Manager", "mobile": "", "email": "purnabramha.hsr09@gmail.com", "active": True, "otpChannel": "email"},
        {"center": "PB-HW", "managerName": "Center Manager", "mobile": "", "email": "Purnabramha.hinjawadi@gmail.com", "active": True, "otpChannel": "email"},
        {"center": "PB-KN", "managerName": "Center Manager", "mobile": "", "email": "Purnabramha.kharadinyati@gmail.com", "active": True, "otpChannel": "email"},
        {"center": "PB-SN", "managerName": "Center Manager", "mobile": "", "email": "Purnabramha.aurangabad@gmail.com", "active": True, "otpChannel": "email"},
        {"center": "PB-DV", "managerName": "Center Manager", "mobile": "", "email": "purnabramha.dombivli@gmail.com", "active": True, "otpChannel": "email"},
        {"center": "PB-TH", "managerName": "Center Manager", "mobile": "", "email": "purnabramha.newthane@gmail.com", "active": True, "otpChannel": "email"},
        {"center": "PB-PERTH", "managerName": "Center Manager", "mobile": "0401832922", "email": "Purnabramha.perth@gmail.com", "active": True, "otpChannel": "email"},
        {"center": "PB-MGT", "managerName": "Jayanti Kathale", "mobile": "9741399190", "email": "jayanti.kathale@purnabramha.com", "active": True, "otpChannel": "email"},
        {"center": "PB-MGT", "managerName": "Sandeep Gadhwal", "mobile": "9960886185", "email": "sandeep.gadhwal@purnabramha.com", "active": True, "otpChannel": "email"},
        {"center": "PB-KAL", "managerName": "Center Manager", "mobile": "", "email": "purnabramha.kalyan@gmail.com", "active": True, "otpChannel": "email"},
    ]
    
    for m in managers:
        await db.managers.update_one(
            {"center": m["center"], "email": m["email"]},
            {"$set": m},
            upsert=True
        )
    
    # Load employees from JSON file (exported from Excel)
    employees_file = ROOT_DIR / "employees_data.json"
    if employees_file.exists():
        with open(employees_file, "r") as f:
            employees = json.load(f)
        
        # Clear existing employees and insert fresh
        await db.employees.delete_many({})
        
        for e in employees:
            await db.employees.insert_one(e)
        
        emp_count = len(employees)
    else:
        emp_count = 0
    
    # Seed salary rules
    salary_rules = {
        "P_value": 1,
        "HD_value": 0.5,
        "WO_value": 1,
        "L_value": 1,
        "A_value": 0,
        "debit_acc_no": "55205000830",
        "pymt_prod_type_code": "PAB_VENDOR",
        "pymt_mode": "NEFT",
        "credit_narr_prefix": "SALARY"
    }
    
    await db.salary_rules.update_one(
        {"_type": "rules"},
        {"$set": {**salary_rules, "_type": "rules"}},
        upsert=True
    )
    
    return {"success": True, "message": f"Data seeded: {len(managers)} managers, {emp_count} employees"}

# =======================================
# BASIC ENDPOINTS
# =======================================

@api_router.get("/")
async def root():
    return {"message": "Purnabramha IntraPB API", "version": "2.0"}

@api_router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@api_router.get("/centers")
async def get_centers():
    """Get list of all centers from DB (master-data-driven, no hardcoding)"""
    centers = await db.centers.find({}, {"_id": 0}).to_list(100)
    if not centers:
        # Seed default centers into DB on first access so all future reads are DB-driven
        default_centers = [
            {"code": "PB-HSR", "name": "Purnabramha HSR - Bangalore", "phone": "+91 85500 78515", "email": "purnabramha.hsr09@gmail.com", "address": "17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout, Bangalore, Karnataka-560102", "active": True, "is_india_center": True, "country": "India"},
            {"code": "PB-TH", "name": "Purnabramha Thane - Mumbai", "phone": "+91 89047 49084", "email": "purnabramha.newthane@gmail.com", "address": "Thane, Mumbai, Maharashtra", "active": True, "is_india_center": True, "country": "India"},
            {"code": "PB-SN", "name": "Purnabramha Sambhajinagar", "phone": "+91 89710 49084", "email": "Purnabramha.aurangabad@gmail.com", "address": "Ch. Sambhajinagar, Maharashtra", "active": True, "is_india_center": True, "country": "India"},
            {"code": "PB-DV", "name": "Purnabramha Dombivli - Mumbai", "phone": "+91 96064 55433", "email": "purnabramha.dombivli@gmail.com", "address": "Dombivli, Mumbai, Maharashtra", "active": True, "is_india_center": True, "country": "India"},
            {"code": "PB-HW", "name": "Purnabramha Hinjawadi - Pune", "phone": "+91 96064 55434", "email": "Purnabramha.hinjawadi@gmail.com", "address": "Hinjawadi, Pune, Maharashtra", "active": True, "is_india_center": True, "country": "India"},
            {"code": "PB-KN", "name": "Purnabramha Kharadi Nyati - Pune", "phone": "", "email": "Purnabramha.kharadinyati@gmail.com", "address": "Kharadi Nyati, Pune, Maharashtra", "active": True, "is_india_center": True, "country": "India"},
            {"code": "PB-KAL", "name": "Purnabramha Kalyan", "phone": "", "email": "purnabramha.kalyan@gmail.com", "address": "Kalyan, Maharashtra", "active": True, "is_india_center": True, "country": "India"},
            {"code": "PB-PERTH", "name": "Purnabramha Perth - Australia", "phone": "0401832922", "email": "Purnabramha.perth@gmail.com", "address": "Perth, Australia", "active": True, "is_india_center": False, "country": "Australia"},
            {"code": "PB-MGT", "name": "Purnabramha Management (HQ)", "phone": "+91 9960886185", "email": "sandeep.gadhwal@purnabramha.com", "address": "HSR Layout, Bangalore", "active": True, "is_india_center": True, "country": "India", "is_hq": True},
        ]
        for c in default_centers:
            await db.centers.update_one({"code": c["code"]}, {"$set": c}, upsert=True)
        centers = await db.centers.find({}, {"_id": 0}).to_list(100)
    return {"centers": centers}

# Centers & Managers management endpoints: MOVED TO routes/centers_managers.py

# =======================================
# USER MANUAL & BROCHURE PDF GENERATION
# =======================================

@api_router.get("/download/user-manual")
async def download_user_manual():
    """Download the pre-generated User Manual PDF - No auth required"""
    pdf_path = ROOT_DIR / "static" / "Purnabramha_User_Manual_With_Screenshots.pdf"
    if not pdf_path.exists():
        # Fallback to text-only version
        pdf_path = ROOT_DIR / "static" / "Purnabramha_User_Manual.pdf"
    if not pdf_path.exists():
        raise HTTPException(404, "User Manual not found")
    
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="Purnabramha_User_Manual.pdf"
    )

@api_router.get("/docs/user-manual")
async def generate_user_manual():
    """Generate User Manual PDF for the Purnabramha IntraPB System"""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor
    
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4
    
    # Cover Page
    c.setFillColor(HexColor("#d97706"))  # Orange/amber color
    c.rect(0, height - 200, width, 200, fill=True, stroke=False)
    
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(width/2, height - 100, "PURNABRAMHA")
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width/2, height - 140, "IntraPB System")
    
    c.setFillColor(HexColor("#000000"))
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width/2, height - 280, "USER MANUAL")
    
    c.setFont("Helvetica", 14)
    c.drawCentredString(width/2, height - 320, "Complete Guide for Managers & Staff")
    c.drawCentredString(width/2, height - 340, "Version 1.0 | December 2025")
    
    c.showPage()
    
    # Table of Contents
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 60, "Table of Contents")
    c.setFont("Helvetica", 12)
    
    toc = [
        ("1. Introduction", "3"),
        ("2. Getting Started - Login", "4"),
        ("3. Dashboard Overview", "5"),
        ("4. Attendance Management", "6"),
        ("5. Salary Management", "8"),
        ("6. Employee Management", "10"),
        ("7. Recipe Management", "12"),
        ("8. Center & Manager Management", "14"),
        ("9. HR Letters Generation", "15"),
        ("10. Guest Response AI", "16"),
        ("11. Troubleshooting", "17"),
    ]
    
    y_pos = height - 100
    for title, page in toc:
        c.drawString(60, y_pos, title)
        c.drawString(500, y_pos, page)
        y_pos -= 25
    
    c.showPage()
    
    # Section 1: Introduction
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 60, "1. Introduction")
    c.setFont("Helvetica", 11)
    
    intro_text = [
        "Welcome to Purnabramha IntraPB System - a comprehensive management solution",
        "designed for Purnabramha restaurant chain's internal operations.",
        "",
        "This system helps you manage:",
        "• Employee attendance tracking",
        "• Salary calculations and payslip generation",
        "• Recipe database management",
        "• Center and manager administration",
        "• HR letter generation (Offer, Relieving, Experience, etc.)",
        "• AI-powered guest response generation",
        "",
        "System Requirements:",
        "• Modern web browser (Chrome, Firefox, Safari, Edge)",
        "• Stable internet connection",
        "• Valid manager credentials"
    ]
    
    y = height - 100
    for line in intro_text:
        c.drawString(60, y, line)
        y -= 18
    
    c.showPage()
    
    # Section 2: Login
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 60, "2. Getting Started - Login")
    c.setFont("Helvetica", 11)
    
    login_text = [
        "To access the IntraPB System, follow these steps:",
        "",
        "Step 1: Open the Login Page",
        "Navigate to the system URL provided by your administrator.",
        "",
        "Step 2: Select Your Center",
        "Choose your center from the dropdown menu:",
        "• PB-HSR (Bangalore)",
        "• PB-TH (Thane)",
        "• PB-SN (Sambhajinagar)",
        "• PB-DV (Dombivli)",
        "• PB-HW (Hinjawadi)",
        "• PB-KN (Kharadi Nyati)",
        "• PB-MGT (Management)",
        "",
        "Step 3: Enter Mobile Number",
        "Enter your registered mobile number.",
        "",
        "Step 4: Request OTP",
        "Click 'Send OTP' to receive a verification code via SMS/Email.",
        "",
        "Step 5: Enter OTP & Login",
        "Enter the OTP received and click 'Verify' to access the dashboard."
    ]
    
    y = height - 100
    for line in login_text:
        c.drawString(60, y, line)
        y -= 16
    
    c.showPage()
    
    # Section 3: Dashboard
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 60, "3. Dashboard Overview")
    c.setFont("Helvetica", 11)
    
    dashboard_text = [
        "After logging in, you'll see the main Dashboard with:",
        "",
        "Navigation Menu (Sidebar):",
        "• Dashboard - Quick overview and statistics",
        "• Attendance - Mark and view employee attendance",
        "• Salary - Calculate salaries and generate payslips",
        "• Employee Management - Add/Edit/View employees",
        "• Recipe Admin - Manage recipe database (MGT only)",
        "• Centers Management - Manage center locations (MGT only)",
        "• Managers Management - Manage managers (MGT only)",
        "• HR Letters - Generate official HR documents",
        "• Guest Response - AI-powered guest feedback replies",
        "",
        "Dashboard Cards:",
        "• Total Employees count",
        "• Today's Attendance summary",
        "• Current Month statistics",
        "• Quick action buttons",
        "",
        "Note: Some features are restricted to PB-MGT managers only."
    ]
    
    y = height - 100
    for line in dashboard_text:
        c.drawString(60, y, line)
        y -= 16
    
    c.showPage()
    
    # Section 4: Attendance
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 60, "4. Attendance Management")
    c.setFont("Helvetica", 11)
    
    attendance_text = [
        "The Attendance module allows you to track daily attendance:",
        "",
        "Marking Attendance:",
        "1. Select the date from the date picker",
        "2. View all employees in your center",
        "3. Mark each employee as:",
        "   • Present (P) - Full day attendance",
        "   • Half-Day (H) - Half day attendance",
        "   • Absent (A) - Not present",
        "   • Week Off (W) - Scheduled day off",
        "   • Leave (L) - Approved leave",
        "",
        "Bulk Actions:",
        "• 'Mark All Present' - Quick mark all as present",
        "• 'Mark All Week Off' - For weekly off days",
        "",
        "Viewing History:",
        "• Navigate to different dates",
        "• View monthly attendance summary",
        "• Export attendance data (Excel format)",
        "",
        "Important Notes:",
        "• Attendance affects salary calculations",
        "• Past dates can only be edited by MGT",
        "• Always verify before saving"
    ]
    
    y = height - 100
    for line in attendance_text:
        c.drawString(60, y, line)
        y -= 15
    
    c.showPage()
    
    # Continue with more sections...
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 60, "5. Salary Management")
    c.setFont("Helvetica", 11)
    
    salary_text = [
        "The Salary module handles all payroll operations:",
        "",
        "Viewing Salary Details:",
        "1. Select month and year",
        "2. View calculated salaries for all employees",
        "3. See breakdown: Base + Bonus - Deductions",
        "",
        "Salary Calculation Formula:",
        "• Per Day = Monthly Salary / Working Days",
        "• Present Days counted fully",
        "• Half-days counted as 0.5",
        "• Deductions for unauthorized absence",
        "",
        "Generating Payslips:",
        "1. Select employee(s)",
        "2. Choose format: PDF or DOCX",
        "3. Click 'Generate Payslips'",
        "4. Download individual or bulk zip file",
        "",
        "Payslip Contents:",
        "• Employee details",
        "• Attendance summary",
        "• Earnings breakdown",
        "• Deductions (if any)",
        "• Net salary payable"
    ]
    
    y = height - 100
    for line in salary_text:
        c.drawString(60, y, line)
        y -= 16
    
    c.showPage()
    
    # Recipe Management
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 60, "6. Recipe Management (MGT Only)")
    c.setFont("Helvetica", 11)
    
    recipe_text = [
        "The Recipe Admin module manages Purnabramha's recipe database:",
        "",
        "Accessing Recipes:",
        "1. Navigate to Recipe Admin from sidebar",
        "2. Browse categories: Snacks, Drinks, Sweets, Mains, etc.",
        "3. Use search to find specific recipes",
        "",
        "Recipe Categories:",
        "• SNACKS - Bhaji, Vada, Pakoda, etc.",
        "• DRINKS - Buttermilk, Kokam, Tea, etc.",
        "• SWEETS - Puranpoli, Modak, Kheer, etc.",
        "• MAINS - Bhaji, Usal, Pithala, etc.",
        "• CURRIES - Dal, Kadhi, Rassa, etc.",
        "• RICE - Plain Rice, Masale Bhaat, etc.",
        "• CHAPATI - Bhakri, Puri, Paratha, etc.",
        "• CHUTNEYS - Green, Tamarind, etc.",
        "• SALADS - Various Koshimbir",
        "• BALGOPAL - Kid-friendly recipes",
        "",
        "Adding/Editing Recipes:",
        "1. Click 'Add New Recipe' or 'Edit'",
        "2. Fill in: Name, Display name, Category",
        "3. Add ingredients (one per line)",
        "4. Add method steps (one per line)",
        "5. Optional: Add image URL",
        "6. Save recipe"
    ]
    
    y = height - 100
    for line in recipe_text:
        c.drawString(60, y, line)
        y -= 15
    
    c.showPage()
    
    # HR Letters
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 60, "7. HR Letters Generation")
    c.setFont("Helvetica", 11)
    
    hr_text = [
        "Generate official HR documents for employees:",
        "",
        "Available Letter Types:",
        "• Offer Letter - For new joiners",
        "• Appointment Letter - After probation",
        "• Relieving Letter - For resigned employees",
        "• Experience Letter - Work experience certificate",
        "• Warning Letter - For disciplinary issues",
        "• Promotion Letter - For promotions",
        "",
        "Generating Letters:",
        "1. Select letter type",
        "2. Enter employee details",
        "3. Fill additional fields as required",
        "4. Choose format: PDF or DOCX",
        "5. Click 'Generate Letter'",
        "6. Download and print",
        "",
        "AI-Assisted Content:",
        "Letters are generated with AI assistance for",
        "professional language and formatting.",
        "",
        "Note: Always review generated content before use."
    ]
    
    y = height - 100
    for line in hr_text:
        c.drawString(60, y, line)
        y -= 16
    
    c.showPage()
    
    # Guest Response AI
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 60, "8. Guest Response AI")
    c.setFont("Helvetica", 11)
    
    guest_text = [
        "AI-powered guest feedback response generator:",
        "",
        "Purpose:",
        "Quickly generate professional, personalized responses",
        "to customer reviews and feedback.",
        "",
        "How to Use:",
        "1. Navigate to Guest Response page",
        "2. Select your center",
        "3. Choose response tone:",
        "   • Professional - Formal business tone",
        "   • Friendly - Warm and welcoming",
        "   • Apologetic - For complaints",
        "4. Enter guest feedback/review",
        "5. Click 'Generate Response'",
        "6. Review and copy the AI-generated response",
        "",
        "Best Practices:",
        "• Always personalize before posting",
        "• Address specific concerns mentioned",
        "• Thank customers for feedback",
        "• Keep responses concise and helpful"
    ]
    
    y = height - 100
    for line in guest_text:
        c.drawString(60, y, line)
        y -= 16
    
    c.showPage()
    
    # Troubleshooting
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 60, "9. Troubleshooting")
    c.setFont("Helvetica", 11)
    
    trouble_text = [
        "Common issues and solutions:",
        "",
        "Login Issues:",
        "• OTP not received: Check mobile number, try again",
        "• Invalid OTP: Request new OTP, check email spam",
        "• Session expired: Re-login to continue",
        "",
        "Attendance Issues:",
        "• Cannot edit past dates: Contact MGT",
        "• Employee not showing: Verify center assignment",
        "",
        "Salary Issues:",
        "• Calculation mismatch: Verify attendance data",
        "• Payslip generation fails: Check employee details",
        "",
        "Recipe Issues:",
        "• Access denied: Only MGT can manage recipes",
        "• Image not loading: Verify URL is accessible",
        "",
        "General Tips:",
        "• Clear browser cache if pages not loading",
        "• Use latest browser version",
        "• Check internet connection",
        "",
        "Support Contact:",
        "Email: support@purnabramha.com",
        "Phone: +91 89047 49084"
    ]
    
    y = height - 100
    for line in trouble_text:
        c.drawString(60, y, line)
        y -= 15
    
    c.save()
    pdf_buffer.seek(0)
    
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Purnabramha_User_Manual.pdf"}
    )

@api_router.get("/docs/brochure")
async def generate_brochure():
    """Generate Recipe Brochure PDF for users"""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    
    # Load recipes
    recipe_file = ROOT_DIR / "recipes_db.json"
    if not recipe_file.exists():
        raise HTTPException(404, "Recipe database not found")
    
    with open(recipe_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    recipes = data.get("recipes", {})
    categories = data.get("categories", [])
    
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4
    
    # Colors
    primary_color = HexColor("#d97706")
    dark_color = HexColor("#1f2937")
    light_color = HexColor("#f3f4f6")
    
    # Cover Page
    c.setFillColor(primary_color)
    c.rect(0, 0, width, height, fill=True, stroke=False)
    
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 48)
    c.drawCentredString(width/2, height - 200, "PURNABRAMHA")
    
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width/2, height - 260, "Recipe Collection")
    
    c.setFont("Helvetica", 16)
    c.drawCentredString(width/2, height - 320, "Authentic Maharashtrian Cuisine")
    c.drawCentredString(width/2, height - 345, f"Over {len(recipes)} Traditional Recipes")
    
    c.setFont("Helvetica-Oblique", 12)
    c.drawCentredString(width/2, 100, "\"Where tradition meets taste\"")
    c.drawCentredString(width/2, 80, "Curated by Jayanti Kathale")
    
    c.showPage()
    
    # Table of Contents
    c.setFillColor(dark_color)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(50, height - 60, "Recipe Categories")
    
    c.setFont("Helvetica", 14)
    y_pos = height - 100
    
    cat_counts = {}
    for key, recipe in recipes.items():
        cat = recipe.get("category", "MAINS").upper()
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    
    for cat in categories:
        count = cat_counts.get(cat, 0)
        if count > 0:
            c.drawString(60, y_pos, f"• {cat}")
            c.drawString(250, y_pos, f"({count} recipes)")
            y_pos -= 25
    
    c.setFont("Helvetica-Oblique", 11)
    c.drawString(60, y_pos - 30, f"Total: {len(recipes)} authentic recipes")
    
    c.showPage()
    
    # Recipe Pages by Category
    for cat in categories:
        cat_recipes = {k: v for k, v in recipes.items() if v.get("category", "").upper() == cat}
        if not cat_recipes:
            continue
        
        # Category Header Page
        c.setFillColor(primary_color)
        c.rect(0, height - 120, width, 120, fill=True, stroke=False)
        
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(width/2, height - 70, cat)
        c.setFont("Helvetica", 14)
        c.drawCentredString(width/2, height - 95, f"{len(cat_recipes)} recipes")
        
        # List recipes in this category
        c.setFillColor(dark_color)
        c.setFont("Helvetica", 11)
        y = height - 160
        
        for key, recipe in sorted(cat_recipes.items()):
            if y < 80:
                c.showPage()
                c.setFillColor(dark_color)
                c.setFont("Helvetica-Bold", 14)
                c.drawString(50, height - 40, f"{cat} (continued)")
                c.setFont("Helvetica", 11)
                y = height - 70
            
            display = recipe.get("display", recipe.get("name", key))
            ingredients = recipe.get("ingredients", [])
            
            c.setFont("Helvetica-Bold", 12)
            c.drawString(60, y, f"• {display}")
            c.setFont("Helvetica", 9)
            c.setFillColor(HexColor("#6b7280"))
            ingredient_text = ", ".join(ingredients[:5])
            if len(ingredients) > 5:
                ingredient_text += "..."
            if len(ingredient_text) > 80:
                ingredient_text = ingredient_text[:80] + "..."
            c.drawString(70, y - 14, ingredient_text)
            c.setFillColor(dark_color)
            
            y -= 40
        
        c.showPage()
    
    # Selected Featured Recipes (5-6 full recipes)
    featured_keys = ["puranpoli", "solkadhi", "batata_vada", "misal_curry", "shrikhand", "ukadiche_modak"]
    featured = [(k, recipes[k]) for k in featured_keys if k in recipes]
    
    if featured:
        # Featured Recipes Header
        c.setFillColor(primary_color)
        c.rect(0, height - 100, width, 100, fill=True, stroke=False)
        
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(width/2, height - 55, "Featured Recipes")
        c.setFont("Helvetica", 12)
        c.drawCentredString(width/2, height - 80, "Our Most Popular Dishes")
        
        c.showPage()
        
        for key, recipe in featured:
            display = recipe.get("display", recipe.get("name", key))
            ingredients = recipe.get("ingredients", [])
            method = recipe.get("method", [])
            
            # Recipe title
            c.setFillColor(primary_color)
            c.setFont("Helvetica-Bold", 20)
            c.drawString(50, height - 50, display)
            
            c.setFillColor(dark_color)
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 70, f"Category: {recipe.get('category', 'MAINS')}")
            
            # Ingredients
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, height - 100, "Ingredients:")
            c.setFont("Helvetica", 10)
            y = height - 120
            for ing in ingredients[:12]:
                if y < 300:
                    break
                c.drawString(60, y, f"• {ing}")
                y -= 14
            
            # Method
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, y - 20, "Method:")
            c.setFont("Helvetica", 10)
            y = y - 40
            for i, step in enumerate(method[:10], 1):
                if y < 100:
                    break
                step_text = step[:90] + "..." if len(step) > 90 else step
                c.drawString(60, y, f"{i}. {step_text}")
                y -= 14
            
            c.showPage()
    
    # Back Cover
    c.setFillColor(primary_color)
    c.rect(0, 0, width, height, fill=True, stroke=False)
    
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(width/2, height/2 + 100, "PURNABRAMHA")
    
    c.setFont("Helvetica", 16)
    c.drawCentredString(width/2, height/2 + 60, "Authentic Maharashtrian Cuisine")
    c.drawCentredString(width/2, height/2 + 35, "Since Tradition Began")
    
    c.setFont("Helvetica", 12)
    c.drawCentredString(width/2, height/2 - 30, "Visit us at:")
    c.drawCentredString(width/2, height/2 - 50, "HSR Layout, Bangalore | Thane | Sambhajinagar")
    c.drawCentredString(width/2, height/2 - 70, "Dombivli | Hinjawadi | Kharadi Nyati | Kalyan")
    c.drawCentredString(width/2, height/2 - 90, "Nashik | Perth, Australia")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width/2, 100, "www.purnabramha.com")
    
    c.save()
    pdf_buffer.seek(0)
    
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Purnabramha_Recipe_Brochure.pdf"}
    )

# =======================================
# DIRECT SALES DATA SEED ENDPOINT (BACKUP)
# =======================================

@api_router.get("/check-sales-db")
async def check_sales_db():
    """Quick check if sales data exists"""
    try:
        sales_count = await db.daily_sales.count_documents({})
        expenses_count = await db.expenses.count_documents({})
        return {
            "status": "ok",
            "sales_count": sales_count,
            "expenses_count": expenses_count
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@api_router.post("/seed-sales-data")
async def seed_sales_data_direct(data: dict = {}):
    """Seed all sales data from production_seed_data.json - COMPREHENSIVE"""
    import json as json_module
    import os
    
    secret = data.get("secret", "")
    if secret != "PURNABRAMHA2024SEED":
        raise HTTPException(403, "Invalid secret key")
    
    force = data.get("force", False)  # Allow force overwrite
    
    try:
        # Check existing data
        existing = await db.daily_sales.count_documents({})
        if existing > 100 and not force:
            return {"status": "skipped", "message": f"Already has {existing} records. Use force=true to overwrite."}
        
        # Load comprehensive seed file
        seed_file = os.path.join(os.path.dirname(__file__), "production_seed_data.json")
        if not os.path.exists(seed_file):
            return {"status": "error", "message": "Seed file not found"}
        
        with open(seed_file, 'r') as f:
            seed_data = json_module.load(f)
        
        results = {}
        
        # 1. Import daily_sales (REPLACE ALL)
        if seed_data.get("daily_sales"):
            await db.daily_sales.delete_many({})
            result = await db.daily_sales.insert_many(seed_data["daily_sales"])
            results["daily_sales"] = len(result.inserted_ids)
        
        # 2. Import expenses (REPLACE ALL)
        if seed_data.get("expenses"):
            await db.expenses.delete_many({})
            result = await db.expenses.insert_many(seed_data["expenses"])
            results["expenses"] = len(result.inserted_ids)
        
        # 3. Import expense_heads (REPLACE ALL)
        if seed_data.get("expense_heads"):
            await db.expense_heads.delete_many({})
            result = await db.expense_heads.insert_many(seed_data["expense_heads"])
            results["expense_heads"] = len(result.inserted_ids)
        
        # 4. Update centers (UPSERT - preserve existing, add new)
        if seed_data.get("centers"):
            for center in seed_data["centers"]:
                await db.centers.update_one(
                    {"code": center.get("code")},
                    {"$set": center},
                    upsert=True
                )
            results["centers"] = len(seed_data["centers"])
        
        # 5. Update managers (UPSERT - preserve existing roles, add new)
        if seed_data.get("managers"):
            for manager in seed_data["managers"]:
                # Only update if manager doesn't exist
                existing_mgr = await db.managers.find_one({
                    "center": manager.get("center"),
                    "mobile": manager.get("mobile")
                })
                if not existing_mgr:
                    await db.managers.insert_one(manager)
            results["managers_added"] = "preserved existing, added new"
        
        return {
            "status": "success", 
            "inserted": results,
            "metadata": seed_data.get("metadata", {})
        }
    except Exception as e:
        logger.error(f"Seed error: {e}")
        return {"status": "error", "message": str(e)}

# Include router
app.include_router(api_router)

# Include Sales & Expenses router
from routes.sales_expenses import router as sales_router, set_db as set_sales_db, set_verify_token as set_sales_verify_token, set_verify_token_async as set_sales_verify_token_async
set_sales_db(db)
set_sales_verify_token(verify_token)
set_sales_verify_token_async(verify_token_async)
app.include_router(sales_router)

# Include Franchise Management router
from routes.franchises import router as franchise_router, set_db as set_franchise_db, set_verify_token as set_franchise_verify_token, set_verify_token_async as set_franchise_verify_token_async
set_franchise_db(db)
set_franchise_verify_token(verify_token)
set_franchise_verify_token_async(verify_token_async)
app.include_router(franchise_router)

# Include MIS Dashboard router
from routes.mis_dashboard import router as mis_router, set_db as set_mis_db, set_verify_token as set_mis_verify_token, set_verify_token_async as set_mis_verify_token_async
set_mis_db(db)
set_mis_verify_token(verify_token)
set_mis_verify_token_async(verify_token_async)
app.include_router(mis_router)

# Include Billing/POS router
from routes.billing import router as billing_router, set_db as set_billing_db, set_verify_token as set_billing_verify_token, set_verify_token_async as set_billing_verify_token_async
set_billing_db(db)
set_billing_verify_token(verify_token)
set_billing_verify_token_async(verify_token_async)
app.include_router(billing_router)

# Include Billing Config Masters router
from routes.billing_config import router as billing_config_router, set_db as set_bc_db, set_verify_token as set_bc_verify_token, set_verify_token_async as set_bc_verify_token_async
set_bc_db(db)
set_bc_verify_token(verify_token)
set_bc_verify_token_async(verify_token_async)
app.include_router(billing_config_router)



# Include Booking Intelligence router
from routes.booking_intelligence import router as booking_router, set_db as set_booking_db, set_verify_token as set_booking_verify_token, set_verify_token_async as set_booking_verify_token_async
set_booking_db(db)
set_booking_verify_token(verify_token)
set_booking_verify_token_async(verify_token_async)
app.include_router(booking_router)

# Include Attendance Dashboard router
from routes.attendance_dashboard import router as att_dash_router, set_db as set_att_dash_db, set_verify_token as set_att_dash_verify_token, set_verify_token_async as set_att_dash_verify_token_async
set_att_dash_db(db)
set_att_dash_verify_token(verify_token)
set_att_dash_verify_token_async(verify_token_async)
app.include_router(att_dash_router)

# Include Franchise Exit & Closure router
from routes.franchise_exit import router as exit_router
app.include_router(exit_router)

# Include Center Accounts router
from routes.center_accounts import router as accounts_router, set_db as set_accounts_db, set_verify_token as set_accounts_verify_token, set_verify_token_async as set_accounts_verify_token_async
set_accounts_db(db)
set_accounts_verify_token(verify_token)
set_accounts_verify_token_async(verify_token_async)
app.include_router(accounts_router)

# Include Loan Entries router
from routes.loan_entries import router as loan_router, set_db as set_loan_db, set_verify_token_async as set_loan_verify_token_async
set_loan_db(db)
set_loan_verify_token_async(verify_token_async)
app.include_router(loan_router)

# Include Employees router
from routes.employees import router as employees_router, set_db as set_employees_db, set_verify_token as set_employees_verify_token, set_has_admin_access as set_employees_has_admin_access
set_employees_db(db)
set_employees_verify_token(verify_token)
set_employees_has_admin_access(has_admin_access)
app.include_router(employees_router)

# Include Attendance router
from routes.attendance import router as attendance_router, set_db as set_attendance_db, set_verify_token as set_attendance_verify_token
set_attendance_db(db)
set_attendance_verify_token(verify_token)
app.include_router(attendance_router)

# Include Payroll router
from routes.payroll import router as payroll_router, set_db as set_payroll_db, set_verify_token as set_payroll_verify_token, set_has_admin_access as set_payroll_has_admin_access, set_root_dir as set_payroll_root_dir
set_payroll_db(db)
set_payroll_verify_token(verify_token)
set_payroll_has_admin_access(has_admin_access)
set_payroll_root_dir(ROOT_DIR)
app.include_router(payroll_router)

# Include Recipes router
from routes.recipes import router as recipes_router, set_root_dir as set_recipes_root_dir, set_verify_token as set_recipes_verify_token
set_recipes_root_dir(ROOT_DIR)
set_recipes_verify_token(verify_token)
app.include_router(recipes_router)

# Include Expense Attachments & Invoice Grouping router
from routes.expense_attachments import router as attachments_router, set_db as set_attachments_db, set_verify_token as set_attachments_verify_token
set_attachments_db(db)
set_attachments_verify_token(verify_token)
app.include_router(attachments_router)

# Include International Attendance router (Perth, etc.)
from routes.international_attendance import router as intl_attendance_router, set_db as set_intl_attendance_db, set_verify_token as set_intl_attendance_verify_token
set_intl_attendance_db(db)
set_intl_attendance_verify_token(verify_token)
app.include_router(intl_attendance_router)

# Include Employee Transfers router
from routes.transfers import router as transfers_router, set_db as set_transfers_db, set_verify_token as set_transfers_verify_token, set_has_admin_access as set_transfers_admin
set_transfers_db(db)
set_transfers_verify_token(verify_token)
set_transfers_admin(has_admin_access)
app.include_router(transfers_router)

# Include HR Letters router (extracted from server.py)
from routes.hr_letters import router as hr_letters_router, set_db as set_hr_db, set_verify_token as set_hr_verify_token
set_hr_db(db)
set_hr_verify_token(verify_token)
app.include_router(hr_letters_router)

# Include Centers & Managers router (extracted from server.py)
from routes.centers_managers import router as cm_router, set_db as set_cm_db, set_verify_token as set_cm_verify_token
set_cm_db(db)
set_cm_verify_token(verify_token)
app.include_router(cm_router)

# Include Master Data router
from routes.masters import router as masters_router, set_db as set_masters_db, set_verify_token as set_masters_verify_token
set_masters_db(db)
set_masters_verify_token(verify_token)
app.include_router(masters_router)

# Include Permission Engine router
from routes.permissions import router as perm_router, set_db as set_perm_db, set_verify_token as set_perm_verify_token
set_perm_db(db)
set_perm_verify_token(verify_token)
app.include_router(perm_router)

# Commission Tracking
from routes.commissions import router as comm_router, set_db as set_comm_db, set_verify_token as set_comm_verify_token, set_verify_token_async as set_comm_verify_token_async
set_comm_db(db)
set_comm_verify_token(verify_token)
set_comm_verify_token_async(verify_token_async)
app.include_router(comm_router)

# Document Management
from routes.documents import router as doc_router, set_db as set_doc_db, set_verify_token as set_doc_verify_token, set_verify_token_async as set_doc_verify_token_async
set_doc_db(db)
set_doc_verify_token(verify_token)
set_doc_verify_token_async(verify_token_async)
app.include_router(doc_router)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_cleanup_centers():
    """Auto-cleanup: normalize center codes, remove duplicates, set is_india_center flag"""
    # Init document storage
    try:
        from routes.documents import init_storage
        init_storage()
        logger.info("Startup: document storage initialized")
    except Exception as e:
        logger.warning(f"Startup: document storage init failed (will retry on first upload): {e}")
    
    # Seed default document categories if they don't exist (idempotent by category_id)
    try:
        default_cats = [
            {"category_id": "cat-agreement", "name": "Franchise Agreement", "level": "franchise", "requires_expiry": True, "description": "Franchise agreements and amendments", "is_active": True, "created_by": "System", "created_at": datetime.now(timezone.utc).isoformat()},
            {"category_id": "cat-license", "name": "License", "level": "franchise", "requires_expiry": True, "description": "Business licenses and permits", "is_active": True, "created_by": "System", "created_at": datetime.now(timezone.utc).isoformat()},
            {"category_id": "cat-compliance", "name": "Compliance Certificate", "level": "franchise", "requires_expiry": True, "description": "FSSAI, GST, and compliance certificates", "is_active": True, "created_by": "System", "created_at": datetime.now(timezone.utc).isoformat()},
            {"category_id": "cat-financial", "name": "Financial Document", "level": "franchise", "requires_expiry": False, "description": "Financial statements, invoices, receipts", "is_active": True, "created_by": "System", "created_at": datetime.now(timezone.utc).isoformat()},
            {"category_id": "cat-legal", "name": "Legal Document", "level": "franchise", "requires_expiry": False, "description": "Legal documents and contracts", "is_active": True, "created_by": "System", "created_at": datetime.now(timezone.utc).isoformat()},
            {"category_id": "cat-exit", "name": "Exit Document", "level": "franchise", "requires_expiry": False, "description": "Exit and closure documents", "is_active": True, "created_by": "System", "created_at": datetime.now(timezone.utc).isoformat()},
            {"category_id": "cat-offer", "name": "Offer Letter", "level": "employee", "requires_expiry": False, "description": "Employee offer letters", "is_active": True, "created_by": "System", "created_at": datetime.now(timezone.utc).isoformat()},
            {"category_id": "cat-idproof", "name": "ID Proof", "level": "employee", "requires_expiry": True, "description": "Aadhaar, PAN, passport, etc.", "is_active": True, "created_by": "System", "created_at": datetime.now(timezone.utc).isoformat()},
            {"category_id": "cat-police", "name": "Police Verification", "level": "employee", "requires_expiry": True, "description": "Police verification certificates", "is_active": True, "created_by": "System", "created_at": datetime.now(timezone.utc).isoformat()},
        ]
        seeded = 0
        for cat in default_cats:
            exists = await db.document_categories.find_one({"category_id": cat["category_id"]})
            if not exists:
                await db.document_categories.insert_one(cat)
                seeded += 1
        if seeded:
            logger.info(f"Startup: seeded {seeded} default document categories")
    except Exception as e:
        logger.warning(f"Startup: document category seeding failed: {e}")
    
    try:
        all_centers = await db.centers.find({}).to_list(500)
        
        # Step 1: Normalize center codes - strip trailing hyphens/spaces
        for c in all_centers:
            code = c.get("code", "")
            clean_code = code.upper().rstrip("- ").strip()
            if clean_code != code and clean_code:
                await db.centers.update_one({"_id": c["_id"]}, {"$set": {"code": clean_code}})
                logger.info(f"Startup: normalized center code '{code}' -> '{clean_code}'")
        
        # Step 2: Re-fetch and deduplicate
        all_centers = await db.centers.find({}).to_list(500)
        code_map = {}
        for c in all_centers:
            code = c.get("code", "")
            if code not in code_map:
                code_map[code] = []
            code_map[code].append(c)
        
        for code, entries in code_map.items():
            if len(entries) <= 1:
                continue
            def score(entry):
                return sum(1 for k, v in entry.items() if k != "_id" and v and str(v).strip())
            entries.sort(key=score, reverse=True)
            for dup in entries[1:]:
                await db.centers.delete_one({"_id": dup["_id"]})
                logger.info(f"Startup dedup: removed duplicate center '{code}' (_id={dup['_id']})")
        
        # Step 3: Auto-set is_india_center flag for centers that don't have it
        # Known non-India centers: PERTH and any with country set to non-India
        all_centers = await db.centers.find({}).to_list(500)
        for c in all_centers:
            if "is_india_center" not in c:
                code = c.get("code", "")
                country = c.get("country", "")
                # Non-India if: has non-India country, or code contains PERTH
                is_india = True
                if country and country.lower() not in ("india", ""):
                    is_india = False
                if "PERTH" in code.upper():
                    is_india = False
                await db.centers.update_one({"_id": c["_id"]}, {"$set": {"is_india_center": is_india}})
                logger.info(f"Startup: set is_india_center={is_india} for {code}")
        
        # Step 3b: Refresh international centers cache for sales_expenses
        try:
            from routes.sales_expenses import refresh_international_centers_cache
            await refresh_international_centers_cache(db)
            logger.info("Startup: refreshed international centers cache")
        except Exception as cache_err:
            logger.warning(f"Startup: could not refresh intl centers cache: {cache_err}")
        
        # Step 4: Auto-complete expired temporary transfers
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now_str = datetime.now(timezone.utc).isoformat()
        expired = await db.transfer_requests.find({
            "transfer_type": "TEMPORARY",
            "status": "ACCEPTED",
            "end_date": {"$lt": today, "$ne": None, "$ne": ""}
        }).to_list(500)
        for transfer in expired:
            emp_name = transfer["employee_name"]
            home = transfer.get("home_center") or transfer["from_center"]
            await db.employees.update_many(
                {"name": emp_name},
                {"$set": {"current_operating_center": home, "transfer_status": "", "active_transfer_id": "", "transfer_start_date": "", "transfer_end_date": "", "updated_at": now_str}}
            )
            await db.transfer_requests.update_one(
                {"_id": transfer["_id"]},
                {"$set": {"status": "COMPLETED", "action_notes": f"Auto-completed on startup: ended {transfer['end_date']}", "updated_at": now_str}}
            )
            logger.info(f"Startup: auto-completed expired transfer for {emp_name}")
    except Exception as e:
        logger.warning(f"Startup cleanup failed: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
