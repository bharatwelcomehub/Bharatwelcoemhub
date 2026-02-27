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

# OTP Storage (in-memory for dev, use Redis in production)
otp_store: Dict[str, Dict] = {}

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

def verify_token(token: str) -> Optional[Dict]:
    """
    Verify token and check session expiry.
    Session expires after 2 hours of inactivity (configurable via config.json).
    """
    session_ttl = int((CFG.get("security") or {}).get("session_ttl_seconds", 7200))  # Default 2 hours
    
    for key, data in otp_store.items():
        if data.get("token") == token:
            # Check if session has expired
            token_created = data.get("token_created_at")
            if token_created:
                try:
                    created_time = datetime.fromisoformat(token_created.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    elapsed = (now - created_time).total_seconds()
                    
                    if elapsed > session_ttl:
                        logger.info(f"Token expired for {data.get('center')} - elapsed {elapsed}s > TTL {session_ttl}s")
                        # Token expired - remove it
                        del otp_store[key]
                        return None
                except Exception as e:
                    logger.warning(f"Error checking token expiry: {e}")
            
            return data
    return None

def has_admin_access(session) -> bool:
    """Check if user has admin/super admin access"""
    if not session:
        return False
    if session.get("center") == "PB-MGT":
        return True
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
    
    otp_store[key] = {
        "otp": otp,
        "center": req.center.upper(),
        "mobile": req.mobile,
        "managerName": manager_name,
        "email": manager_email,
        "created": datetime.now(timezone.utc).isoformat()
    }
    
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
    stored = otp_store.get(key)
    
    if not stored:
        raise HTTPException(400, "OTP expired or not requested")
    
    # For development, accept "123456" as master OTP
    if req.otp != stored["otp"] and req.otp != "123456":
        raise HTTPException(400, "Invalid OTP")
    
    token = generate_token()
    stored["token"] = token
    
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
    }, {"_id": 0, "roles": 1, "is_admin": 1, "email": 1})
    
    # Fallback: If no manager found by mobile, try to find by center alone
    # This handles cases where managers don't have mobile numbers registered
    if not manager:
        manager = await db.managers.find_one(
            {"center": stored["center"]},
            {"_id": 0, "roles": 1, "is_admin": 1, "email": 1}
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
    otp_store[key] = stored
    
    return {
        "success": True,
        "token": token,
        "center": stored["center"],
        "managerName": stored.get("managerName", "Manager"),
        "mobile": req.mobile,
        "roles": roles,
        "is_super_admin": is_super_admin,
        "is_admin": is_admin
    }

# =======================================
# EMPLOYEE ENDPOINTS
# =======================================

@api_router.post("/employees")
async def get_employees(req: TokenRequest):
    """Get employees for a center"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    query = {"center": req.center.upper()}
    if req.center.upper() != "PB-MGT":
        query = {"center": req.center.upper()}
    
    employees = await db.employees.find(query, {"_id": 0}).sort("name", 1).to_list(1000)
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
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can update employees")
    
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
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can delete employees")
    
    # Delete by rowIndex is tricky - need to find by name
    employees = await db.employees.find({}, {"_id": 0}).sort("name", 1).to_list(1000)
    row_index = data.get("rowIndex", -1)
    
    if 0 <= row_index < len(employees):
        emp = employees[row_index]
        await db.employees.delete_one({"name": emp["name"]})
        return {"success": True, "message": "Employee deleted"}
    
    raise HTTPException(404, "Employee not found")

# =======================================
# ATTENDANCE ENDPOINTS
# =======================================

@api_router.post("/bulk_attendance")
async def bulk_attendance(req: BulkAttendance):
    """Save daily attendance for multiple employees"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Check payroll lock
    month = req.date[:7]
    lock = await db.payroll_locks.find_one({"month": month}, {"_id": 0})
    if lock and lock.get("locked"):
        raise HTTPException(400, f"Payroll locked for {month}")
    
    inserted = 0
    updated = 0
    timestamp = datetime.now(timezone.utc).isoformat()
    
    for row in req.rows:
        doc = {
            "date": req.date,
            "center": req.center.upper(),
            "employeeName": row.employeeName.upper(),
            "designation": row.designation,
            "status": row.status.upper(),
            "notes": row.notes or "",
            "submittedByMobile": req.submittedBy or session.get("mobile", ""),
            "timestamp": timestamp
        }
        
        # Upsert
        result = await db.attendance.update_one(
            {"date": req.date, "center": req.center.upper(), "employeeName": row.employeeName.upper()},
            {"$set": doc},
            upsert=True
        )
        
        if result.upserted_id:
            inserted += 1
        else:
            updated += 1
    
    return {"success": True, "inserted": inserted, "updated": updated}

@api_router.post("/attendance_by_date")
async def attendance_by_date(req: DateRequest):
    """Get attendance for a specific date"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    rows = await db.attendance.find(
        {"date": req.date, "center": req.center.upper()},
        {"_id": 0}
    ).to_list(1000)
    
    return {"rows": rows}

@api_router.post("/attendance_month")
async def attendance_month(req: MonthRequest):
    """Get monthly attendance grid"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    year, month = map(int, req.month.split("-"))
    dim = days_in_month(year, month)
    
    # Get employees for center
    employees = await db.employees.find(
        {"center": req.center.upper()},
        {"_id": 0}
    ).sort("name", 1).to_list(1000)
    
    # Get all attendance for month
    start_date = f"{req.month}-01"
    end_date = f"{req.month}-{dim:02d}"
    
    attendance = await db.attendance.find(
        {
            "center": req.center.upper(),
            "date": {"$gte": start_date, "$lte": end_date}
        },
        {"_id": 0}
    ).to_list(10000)
    
    # Build lookup
    att_map = {}
    for a in attendance:
        key = f"{a['employeeName']}_{a['date']}"
        att_map[key] = a.get("status", "")
    
    # Build grid
    grid = []
    for emp in employees:
        emp_name = emp.get("name", "").upper()
        days = []
        for d in range(1, dim + 1):
            date_str = f"{req.month}-{d:02d}"
            key = f"{emp_name}_{date_str}"
            status = att_map.get(key, "")
            days.append({"day": d, "status": status})
        
        grid.append({
            "employeeName": emp_name,
            "designation": emp.get("designation", ""),
            "days": days
        })
    
    return {"grid": grid, "daysInMonth": dim}

@api_router.post("/bulk_attendance_month")
async def bulk_attendance_month(req: BulkMonthlyAttendance):
    """Save full month attendance"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Check payroll lock
    lock = await db.payroll_locks.find_one({"month": req.month}, {"_id": 0})
    if lock and lock.get("locked"):
        raise HTTPException(400, f"Payroll locked for {req.month}")
    
    inserted = 0
    updated = 0
    timestamp = datetime.now(timezone.utc).isoformat()
    
    for cell in req.cells:
        date_str = f"{req.month}-{cell.day:02d}"
        doc = {
            "date": date_str,
            "center": req.center.upper(),
            "employeeName": cell.employeeName.upper(),
            "status": cell.status.upper(),
            "notes": cell.notes or "",
            "submittedByMobile": req.submittedBy or session.get("mobile", ""),
            "timestamp": timestamp
        }
        
        result = await db.attendance.update_one(
            {"date": date_str, "center": req.center.upper(), "employeeName": cell.employeeName.upper()},
            {"$set": doc},
            upsert=True
        )
        
        if result.upserted_id:
            inserted += 1
        else:
            updated += 1
    
    return {"success": True, "inserted": inserted, "updated": updated}

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
# PAYROLL ENDPOINTS
# =======================================

@api_router.post("/payroll_status")
async def payroll_status(req: MonthRequest):
    """Check if payroll is locked for a month"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    lock = await db.payroll_locks.find_one({"month": req.month}, {"_id": 0})
    
    return {
        "locked": lock.get("locked", False) if lock else False,
        "lockedAt": lock.get("lockedAt", "") if lock else "",
        "lockedBy": lock.get("lockedBy", "") if lock else ""
    }

@api_router.post("/lock_payroll")
async def lock_payroll(req: MonthRequest):
    """Lock payroll for a month (Admin/MGT only)"""
    session = verify_token(req.token)
    if not session or not has_admin_access(session):
        raise HTTPException(403, "Only Admin/Super Admin can lock payroll")
    
    doc = {
        "month": req.month,
        "center": "ALL",
        "locked": True,
        "lockedAt": datetime.now(timezone.utc).isoformat(),
        "lockedBy": session.get("mobile", "")
    }
    
    await db.payroll_locks.update_one(
        {"month": req.month},
        {"$set": doc},
        upsert=True
    )
    
    return {"success": True, "message": f"Payroll locked for {req.month}"}

@api_router.post("/salary_preview")
async def salary_preview(req: SalaryPreviewRequest):
    """Preview salary data on screen for a specific center"""
    session = verify_token(req.token)
    if not session or not has_admin_access(session):
        raise HTTPException(403, "Only Admin/Super Admin can view salary preview")
    
    try:
        year, month = map(int, req.month.split("-"))
        dim = days_in_month(year, month)
        
        # Get employees for selected center
        employees = await db.employees.find(
            {"center": req.targetCenter.upper()},
            {"_id": 0}
        ).to_list(1000)
        
        # Get attendance for the month
        start_date = f"{req.month}-01"
        end_date = f"{req.month}-{dim:02d}"
        
        attendance = await db.attendance.find(
            {"date": {"$gte": start_date, "$lte": end_date}},
            {"_id": 0}
        ).to_list(50000)
        
        # Get advances for the month
        advances = await db.advances.find(
            {"date": {"$regex": f"^{req.month}"}},
            {"_id": 0}
        ).to_list(5000)
        
        # Build attendance map
        att_map = {}
        for a in attendance:
            key = f"{a['employeeName']}_{a['date']}"
            att_map[key] = a.get("status", "")
        
        # Build advances map
        adv_map = {}
        for a in advances:
            emp = a.get("employeeName", "")
            adv_map[emp] = adv_map.get(emp, 0) + float(a.get("advanceAmount", 0) or 0)
        
        # Weight rules
        weights = {"P": 1, "HD": 0.5, "WO": 1, "L": 1, "A": 0}
        
        # Calculate salary for each employee
        salary_data = []
        total_gross = 0
        total_advance = 0
        total_net = 0
        
        for emp in employees:
            emp_name = emp.get("name", "").upper()
            salary = float(emp.get("currentSalary", 0) or 0)
            
            # Calculate working days
            present_days = 0
            for d in range(1, dim + 1):
                date_str = f"{req.month}-{d:02d}"
                key = f"{emp_name}_{date_str}"
                status = att_map.get(key, "")
                weight = weights.get(status, 0)
                present_days += weight
            
            # Calculate salary
            daily_rate = salary / dim if dim > 0 else 0
            gross_salary = daily_rate * present_days
            advance = adv_map.get(emp_name, 0)
            net_salary = max(0, gross_salary - advance)
            
            total_gross += gross_salary
            total_advance += advance
            total_net += net_salary
            
            salary_data.append({
                "employeeName": emp_name,
                "designation": emp.get("designation", ""),
                "center": emp.get("center", ""),
                "monthlySalary": salary,
                "daysInMonth": dim,
                "presentDays": round(present_days, 1),
                "grossSalary": round(gross_salary, 2),
                "advance": round(advance, 2),
                "netSalary": round(net_salary, 2),
                "bankAccount": emp.get("beneAccNo", ""),
                "ifsc": emp.get("ifsc", ""),
                "mobile": emp.get("mobile", "")
            })
        
        return {
            "success": True,
            "center": req.targetCenter.upper(),
            "month": req.month,
            "daysInMonth": dim,
            "employeeCount": len(salary_data),
            "totals": {
                "gross": round(total_gross, 2),
                "advance": round(total_advance, 2),
                "net": round(total_net, 2)
            },
            "salaryData": salary_data
        }
        
    except Exception as e:
        logger.error(f"Salary preview error: {e}")
        raise HTTPException(500, str(e))

@api_router.post("/generate_salary")
async def generate_salary(req: SalaryGenRequest):
    """Generate salary Excel for ICICI upload"""
    session = verify_token(req.token)
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can generate salary")
    
    try:
        from openpyxl import Workbook
        
        year, month = map(int, req.month.split("-"))
        dim = days_in_month(year, month)
        
        # Get employees
        if req.mode == "single" and req.targetCenter:
            employees = await db.employees.find(
                {"center": req.targetCenter.upper()},
                {"_id": 0}
            ).to_list(1000)
        else:
            employees = await db.employees.find({}, {"_id": 0}).to_list(1000)
        
        # Get attendance
        start_date = f"{req.month}-01"
        end_date = f"{req.month}-{dim:02d}"
        
        attendance = await db.attendance.find(
            {"date": {"$gte": start_date, "$lte": end_date}},
            {"_id": 0}
        ).to_list(50000)
        
        # Get advances
        advances = await db.advances.find(
            {"date": {"$regex": f"^{req.month}"}},
            {"_id": 0}
        ).to_list(5000)
        
        # Build attendance map
        att_map = {}
        for a in attendance:
            key = f"{a['employeeName']}_{a['date']}"
            att_map[key] = a.get("status", "")
        
        # Build advances map
        adv_map = {}
        for a in advances:
            emp = a.get("employeeName", "")
            adv_map[emp] = adv_map.get(emp, 0) + float(a.get("advanceAmount", 0) or 0)
        
        # Weight rules
        weights = {"P": 1, "HD": 0.5, "WO": 1, "L": 1, "A": 0}
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Salary"
        
        # Headers - ICICI bank format
        headers = [
            "PYMT_PROD_TYPE_CODE", "PYMT_MODE", "DEBIT_ACC_NO", "BNF_NAME",
            "BENE_ACC_NO", "BENE_IFSC", "AMOUNT", "DEBIT_NARR", "CREDIT_NARR",
            "MOBILE_NUM", "EMAIL_ID", "REMARK", "CENTER", "WORKING_DAYS",
            "PRESENT_DAYS", "GROSS_SALARY", "ADVANCE_DEDUCTION", "NET_SALARY"
        ]
        for col, h in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=h)
        
        row = 2
        for emp in employees:
            emp_name = emp.get("name", "").upper()
            salary = float(emp.get("currentSalary", 0) or 0)
            
            # Get remark/notes for CREDIT_NARR and DEBIT_NARR
            # Use remark if filled, otherwise use default values
            emp_remark = emp.get("remark", "").strip()
            credit_narr = emp_remark if emp_remark else f"SALARY {req.month}"
            debit_narr = emp_remark if emp_remark else "SALARY"
            
            # Calculate working days
            present_days = 0
            for d in range(1, dim + 1):
                date_str = f"{req.month}-{d:02d}"
                key = f"{emp_name}_{date_str}"
                status = att_map.get(key, "")
                weight = weights.get(status, 0)
                present_days += weight
            
            # Calculate salary
            daily_rate = salary / dim if dim > 0 else 0
            gross_salary = daily_rate * present_days
            advance = adv_map.get(emp_name, 0)
            net_salary = max(0, gross_salary - advance)
            
            ws.cell(row=row, column=1, value="PAB_VENDOR")
            ws.cell(row=row, column=2, value="NEFT")
            ws.cell(row=row, column=3, value="55205000830")
            ws.cell(row=row, column=4, value=emp_name)
            ws.cell(row=row, column=5, value=emp.get("beneAccNo", ""))
            ws.cell(row=row, column=6, value=emp.get("ifsc", ""))
            ws.cell(row=row, column=7, value=round(net_salary, 2))
            ws.cell(row=row, column=8, value=debit_narr)
            ws.cell(row=row, column=9, value=credit_narr)
            ws.cell(row=row, column=10, value=emp.get("mobile", ""))
            ws.cell(row=row, column=11, value=emp.get("email", ""))
            ws.cell(row=row, column=12, value=emp.get("center", ""))
            ws.cell(row=row, column=13, value=emp.get("center", ""))
            ws.cell(row=row, column=14, value=dim)
            ws.cell(row=row, column=15, value=round(present_days, 1))
            ws.cell(row=row, column=16, value=round(gross_salary, 2))
            ws.cell(row=row, column=17, value=round(advance, 2))
            ws.cell(row=row, column=18, value=round(net_salary, 2))
            row += 1
        
        # Save to bytes
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"Salary_{req.targetCenter or 'ALL'}_{req.month}.xlsx"
        
        # Return file directly as download
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except Exception as e:
        logger.error(f"Salary generation error: {e}")
        raise HTTPException(500, str(e))

@api_router.post("/payslips_generate")
async def payslips_generate(req: PayslipGenRequest):
    """Generate payslips (PDF/DOCX)"""
    session = verify_token(req.token)
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can generate payslips")
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        import zipfile
        
        year, month = map(int, req.month.split("-"))
        dim = days_in_month(year, month)
        period = int(req.period)
        
        # Get employees
        query = {}
        if req.targetCenter:
            query["center"] = req.targetCenter.upper()
        
        if req.mode == "single" and req.employeeName:
            emp_name_upper = req.employeeName.strip().upper()
            exact_query = {**query, "name": emp_name_upper}
            employees = await db.employees.find(exact_query, {"_id": 0}).to_list(10)
            
            if not employees:
                partial_query = {**query, "name": {"$regex": emp_name_upper, "$options": "i"}}
                employees = await db.employees.find(partial_query, {"_id": 0}).to_list(10)
        else:
            employees = await db.employees.find(query, {"_id": 0}).to_list(1000)
        
        if not employees:
            raise HTTPException(404, f"No employees found matching '{req.employeeName}'. Check the spelling and use full name in CAPS.")
        
        # Track generated files in memory
        file_buffers = []
        
        # Generate months
        months = []
        for i in range(period):
            m = month - i
            y = year
            while m <= 0:
                m += 12
                y -= 1
            months.append(f"{y}-{m:02d}")
        
        for emp in employees:
            emp_name = emp.get("name", "")
            
            # Calculate salary for each month
            total_gross = 0
            total_advance = 0
            total_net = 0
            
            for mon in months:
                y2, m2 = map(int, mon.split("-"))
                d2 = days_in_month(y2, m2)
                salary = float(emp.get("currentSalary", 0) or 0)
                
                attendance = await db.attendance.find(
                    {"employeeName": emp_name.upper(), "date": {"$regex": f"^{mon}"}},
                    {"_id": 0}
                ).to_list(100)
                
                weights = {"P": 1, "HD": 0.5, "WO": 1, "L": 1, "A": 0}
                present = sum(weights.get(a.get("status", ""), 0) for a in attendance)
                
                advances = await db.advances.find(
                    {"employeeName": emp_name.upper(), "date": {"$regex": f"^{mon}"}},
                    {"_id": 0}
                ).to_list(100)
                
                adv = sum(float(a.get("advanceAmount", 0) or 0) for a in advances)
                
                daily = salary / d2 if d2 > 0 else 0
                gross = daily * present
                net = max(0, gross - adv)
                
                total_gross += gross
                total_advance += adv
                total_net += net
            
            # Calculate present days from the primary month (for display)
            primary_month = months[-1] if months else req.month
            y_primary, m_primary = map(int, primary_month.split("-"))
            d_primary = days_in_month(y_primary, m_primary)
            primary_attendance = await db.attendance.find(
                {"employeeName": emp_name.upper(), "date": {"$regex": f"^{primary_month}"}},
                {"_id": 0}
            ).to_list(100)
            weights_display = {"P": 1, "HD": 0.5, "WO": 1, "L": 1, "A": 0}
            present_days = sum(weights_display.get(a.get("status", ""), 0) for a in primary_attendance)
            if present_days == 0:
                present_days = d_primary
            
            # Calculate salary components for display
            monthly_salary = float(emp.get("currentSalary", 0) or 0)
            mgross = monthly_salary
            basic = mgross * 0.594
            hra = basic * 0.5
            conveyance = 800
            ea_fixed = 200
            gross_70 = mgross * 0.70
            others = max(0, gross_70 - basic - hra - conveyance - ea_fixed)
            basic_annual = basic * 12
            others_annual = others * 12
            gross_annual = gross_70 * 12
            medical = 1250
            travelling = 3030
            entertainment = 2020
            reimb_total = medical + travelling + entertainment
            esi_amount = total_gross * 0.0075 if total_gross <= 21000 else 0
            total_liabilities = esi_amount if esi_amount > 0 else 0
            approx_package = total_gross + total_liabilities
            month_parts = req.month.split("-")
            month_display = f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(month_parts[1])-1]}-{month_parts[0][2:]}"
            
            # ============ DOCX GENERATION ============
            if req.fmt == "docx":
                from docx import Document
                from docx.shared import Inches, Pt, Cm
                from docx.enum.text import WD_ALIGN_PARAGRAPH
                from docx.enum.table import WD_TABLE_ALIGNMENT
                from docx.oxml.ns import qn
                from docx.oxml import OxmlElement
                
                doc = Document()
                
                # Set margins
                for section in doc.sections:
                    section.top_margin = Cm(1)
                    section.bottom_margin = Cm(1)
                    section.left_margin = Cm(1.5)
                    section.right_margin = Cm(1.5)
                
                # Header - Company Name
                header = doc.add_paragraph()
                header.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = header.add_run("Purnabramha®")
                run.bold = True
                run.font.size = Pt(18)
                
                company = doc.add_paragraph()
                company.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = company.add_run("MANASWINI FOODS PVT. LTD.")
                run.bold = True
                run.font.size = Pt(11)
                
                address = doc.add_paragraph()
                address.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = address.add_run("17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout, Bangalore, Karnataka-560102")
                run.font.size = Pt(8)
                
                # Title
                title = doc.add_paragraph()
                title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = title.add_run("SALARY SLIP")
                run.bold = True
                run.font.size = Pt(12)
                
                # Employee Details Table
                emp_table = doc.add_table(rows=5, cols=2)
                emp_table.alignment = WD_TABLE_ALIGNMENT.CENTER
                
                emp_data = [
                    (f"Name: {emp_name}", f"Pay Date: {datetime.now().strftime('%d-%m-%Y')}"),
                    (f"Designation: {emp.get('designation', 'N/A')}", f"Month of Salary: {month_display}"),
                    (f"Department: {emp.get('center', 'KITCHEN')}", ""),
                    (f"Date of Birth: {emp.get('dob', 'N/A')}", ""),
                    (f"Date of Joining: {emp.get('dateOfJoining', 'N/A')}", ""),
                ]
                for i, (left, right) in enumerate(emp_data):
                    emp_table.rows[i].cells[0].text = left
                    emp_table.rows[i].cells[1].text = right
                
                doc.add_paragraph()
                
                # Salary Breakdown Table
                salary_table = doc.add_table(rows=25, cols=4)
                salary_table.style = 'Table Grid'
                
                salary_rows = [
                    ("SALARY BREAKDOWN", "", "", "TAX COMPUTATION"),
                    ("Basic @ 59.40% of Gross", f"Rs. {basic:,.2f}", f"Rs. {basic:,.2f}", f"Annual: Rs. {basic_annual:,.2f}"),
                    ("HRA @ 50% of basic", f"Rs. {hra:,.2f}", "", ""),
                    ("Conveyance (Fixed)", f"Rs. {conveyance:,.2f}", "", ""),
                    ("E.A (Fixed)", f"Rs. {ea_fixed:,.2f}", "", ""),
                    ("Others (balancing)", f"Rs. {others:,.2f}", f"Rs. {others:,.2f}", f"Annual: Rs. {others_annual:,.2f}"),
                    ("A - Gross (70% of MGross)", f"Rs. {gross_70:,.2f}", f"Rs. {gross_70:,.2f}", f"Annual: Rs. {gross_annual:,.2f}"),
                    ("", "", "", ""),
                    ("REIMBURSEMENTS", "", "", ""),
                    ("Medical", f"Rs. {medical:,.2f}", "", "Standard Ded."),
                    ("Travelling Expenses", f"Rs. {travelling:,.2f}", "", "Investments"),
                    ("Entertainment", f"Rs. {entertainment:,.2f}", "", ""),
                    ("B - Reimbursements", f"Rs. {reimb_total:,.2f}", "", ""),
                    ("", "", "", ""),
                    ("C = A+B Monthly Gross", f"Rs. {total_gross:,.2f}", "", f"Taxable: Rs. {gross_annual:,.2f}"),
                    ("", "", "", ""),
                    (f"NO. OF DAYS WORKING: {int(present_days)} DAYS", "", "", ""),
                    ("", "", "", ""),
                    ("LIABILITIES", "", "", ""),
                    ("P.F.", "NA", "", ""),
                    ("E.S.I.", f"Rs. {esi_amount:,.2f}" if esi_amount > 0 else "NA", "", ""),
                    ("D - Liabilities", f"Rs. {total_liabilities:,.2f}", "", ""),
                    ("", "", "", ""),
                    ("DEDUCTIONS", "", "", ""),
                    ("Advance", f"Rs. {total_advance:,.2f}" if total_advance > 0 else "-", "", ""),
                ]
                
                for i, row_data in enumerate(salary_rows):
                    for j, cell_text in enumerate(row_data):
                        salary_table.rows[i].cells[j].text = cell_text
                
                # Net Take Section
                doc.add_paragraph()
                net_para = doc.add_paragraph()
                run = net_para.add_run(f"G = C-F  NET TAKE: Rs. {total_net:,.2f}")
                run.bold = True
                run.font.size = Pt(12)
                
                package_para = doc.add_paragraph()
                package_para.add_run(f"Approx Full Package: Rs. {approx_package:,.2f}")
                
                doc.add_paragraph()
                
                # Footer
                footer = doc.add_paragraph()
                footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                run = footer.add_run("Purnabramha\nMANASWINI FOODS PVT. LTD.\n\nMr. Sandeep Gadhwal\nDirector")
                run.font.size = Pt(9)
                
                docx_buffer = BytesIO()
                doc.save(docx_buffer)
                docx_buffer.seek(0)
                
                filename = f"Payslip_{emp_name.replace(' ', '_')}_{req.month}.docx"
                file_buffers.append((filename, docx_buffer.getvalue(), "docx"))
            
            # ============ PDF GENERATION ============
            elif req.fmt == "pdf":
                filename = f"Payslip_{emp_name.replace(' ', '_')}_{req.month}.pdf"
                pdf_buffer = BytesIO()
                
                c = canvas.Canvas(pdf_buffer, pagesize=A4)
                width, height = A4
                
                # ============ HEADER ============
                logo_path = ROOT_DIR / "assets" / "purnabramha_logo.png"
                if not logo_path.exists():
                    logo_path = ROOT_DIR / "pb_logo.png"
                if logo_path.exists():
                    try:
                        c.drawImage(str(logo_path), width/2 - 0.6*inch, height - 0.9*inch, width=1.2*inch, height=0.7*inch, preserveAspectRatio=True, mask='auto')
                    except Exception as e:
                        logger.warning(f"Could not add logo: {e}")
                        c.setFont("Helvetica-Bold", 16)
                        c.drawCentredString(width/2, height - 0.5*inch, "Purnabramha®")
                else:
                    c.setFont("Helvetica-Bold", 16)
                    c.drawCentredString(width/2, height - 0.5*inch, "Purnabramha®")
                
                c.setFont("Helvetica-Bold", 10)
                c.drawCentredString(width/2, height - 1.05*inch, "MANASWINI FOODS PVT. LTD.")
                
                c.setFont("Helvetica", 7)
                c.drawCentredString(width/2, height - 1.2*inch, "17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout, Bangalore, Karnataka-560102")
                
                # ============ SALARY SLIP TITLE ============
                c.setFont("Helvetica-Bold", 11)
                c.drawCentredString(width/2, height - 1.4*inch, "SALARY SLIP")
                
                # ============ EMPLOYEE DETAILS - SIMPLIFIED TWO COLUMN ============
                y = height - 1.65*inch
                c.setFont("Helvetica", 8)
                
                # Left column employee info
                left_x = 0.5*inch
                right_x = 4.2*inch
                
                c.drawString(left_x, y, f"Name: {emp_name}")
                c.drawString(right_x, y, f"Pay Date: {datetime.now().strftime('%d-%m-%Y')}")
                y -= 0.18*inch
                
                c.drawString(left_x, y, f"Designation: {emp.get('designation', 'N/A')}")
                c.drawString(right_x, y, f"Month: {month_display}")
                y -= 0.18*inch
                
                c.drawString(left_x, y, f"Department: {emp.get('center', 'KITCHEN')}")
                c.drawString(right_x, y, f"Days Worked: {int(present_days)}/{d_primary}")
                y -= 0.18*inch
                
                c.drawString(left_x, y, f"DOJ: {emp.get('dateOfJoining', 'N/A')}")
                y -= 0.15*inch
                
                # ============ MAIN TABLE - CLEANER LAYOUT ============
                box_top = height - 2.35*inch
                box_bottom = 1.8*inch
                box_left = 0.4*inch
                box_right = width - 0.4*inch
                mid_col = width / 2
                
                c.setLineWidth(0.5)
                c.rect(box_left, box_bottom, box_right - box_left, box_top - box_bottom)
                c.line(mid_col, box_top, mid_col, box_bottom)
                
                # ============ LEFT COLUMN - EARNINGS ============
                y = box_top - 0.2*inch
                left_label_x = box_left + 0.1*inch
                left_value_x = mid_col - 0.15*inch
                
                c.setFont("Helvetica-Bold", 8)
                c.drawString(left_label_x, y, "EARNINGS")
                y -= 0.22*inch
                
                c.setFont("Helvetica", 7)
                earnings_items = [
                    ("Basic @ 59.40%", basic),
                    ("HRA @ 50% of Basic", hra),
                    ("Conveyance (Fixed)", conveyance),
                    ("E.A (Fixed)", ea_fixed),
                    ("Others (Balancing)", others),
                ]
                
                for label, value in earnings_items:
                    c.drawString(left_label_x, y, label)
                    c.drawRightString(left_value_x, y, f"Rs. {value:,.2f}")
                    y -= 0.16*inch
                
                y -= 0.05*inch
                c.setFont("Helvetica-Bold", 7)
                c.drawString(left_label_x, y, "A - Gross (70%)")
                c.drawRightString(left_value_x, y, f"Rs. {gross_70:,.2f}")
                y -= 0.22*inch
                
                c.setFont("Helvetica-Bold", 8)
                c.drawString(left_label_x, y, "REIMBURSEMENTS")
                y -= 0.2*inch
                
                c.setFont("Helvetica", 7)
                reimb_items = [
                    ("Medical", medical),
                    ("Travelling", travelling),
                    ("Entertainment", entertainment),
                ]
                for label, value in reimb_items:
                    c.drawString(left_label_x, y, label)
                    c.drawRightString(left_value_x, y, f"Rs. {value:,.2f}")
                    y -= 0.16*inch
                
                y -= 0.05*inch
                c.setFont("Helvetica-Bold", 7)
                c.drawString(left_label_x, y, "B - Reimbursements")
                c.drawRightString(left_value_x, y, f"Rs. {reimb_total:,.2f}")
                y -= 0.22*inch
                
                c.setFont("Helvetica-Bold", 8)
                c.drawString(left_label_x, y, "GROSS SALARY (A+B)")
                c.drawRightString(left_value_x, y, f"Rs. {total_gross:,.2f}")
                
                # ============ RIGHT COLUMN - DEDUCTIONS ============
                y = box_top - 0.2*inch
                right_label_x = mid_col + 0.1*inch
                right_value_x = box_right - 0.15*inch
                
                c.setFont("Helvetica-Bold", 8)
                c.drawString(right_label_x, y, "DEDUCTIONS")
                y -= 0.22*inch
                
                c.setFont("Helvetica", 7)
                deduction_items = [
                    ("P.F.", "NA"),
                    ("E.S.I.", f"Rs. {esi_amount:,.2f}" if esi_amount > 0 else "NA"),
                    ("Welfare Fund", "-"),
                    ("Income Tax", "-"),
                    ("Advance", f"Rs. {total_advance:,.2f}" if total_advance > 0 else "-"),
                ]
                
                for label, value in deduction_items:
                    c.drawString(right_label_x, y, label)
                    c.drawRightString(right_value_x, y, value)
                    y -= 0.16*inch
                
                y -= 0.05*inch
                c.setFont("Helvetica-Bold", 7)
                c.drawString(right_label_x, y, "Total Deductions")
                c.drawRightString(right_value_x, y, f"Rs. {total_advance + total_liabilities:,.2f}")
                y -= 0.35*inch
                
                # Annual Summary
                c.setFont("Helvetica-Bold", 8)
                c.drawString(right_label_x, y, "ANNUAL SUMMARY")
                y -= 0.2*inch
                
                c.setFont("Helvetica", 7)
                annual_items = [
                    ("Annual Basic", f"Rs. {basic_annual:,.2f}"),
                    ("Annual Gross (70%)", f"Rs. {gross_annual:,.2f}"),
                ]
                for label, value in annual_items:
                    c.drawString(right_label_x, y, label)
                    c.drawRightString(right_value_x, y, value)
                    y -= 0.16*inch
                
                # ============ NET SALARY SECTION ============
                c.setFillColorRGB(0.95, 0.95, 0.95)
                c.rect(box_left, box_bottom - 0.5*inch, box_right - box_left, 0.45*inch, fill=1)
                c.setFillColorRGB(0, 0, 0)
                
                c.setFont("Helvetica-Bold", 11)
                c.drawString(box_left + 0.15*inch, box_bottom - 0.32*inch, "NET SALARY")
                c.drawRightString(box_right - 0.15*inch, box_bottom - 0.32*inch, f"Rs. {total_net:,.2f}")
                
                # ============ FOOTER ============
                sign_path = ROOT_DIR / "assets" / "sandeep_gadhwal_signature.png"
                if not sign_path.exists():
                    sign_path = ROOT_DIR / "sign.png"
                if sign_path.exists():
                    try:
                        c.drawImage(str(sign_path), width - 2*inch, 0.5*inch, width=1.2*inch, height=0.6*inch, preserveAspectRatio=True, mask='auto')
                    except Exception as e:
                        logger.warning(f"Could not add signature: {e}")
                
                c.setFont("Helvetica-Bold", 10)
                c.drawRightString(width - 0.5*inch, 1.3*inch, "Purnabramha")
                c.setFont("Helvetica", 8)
                c.drawRightString(width - 0.5*inch, 1.15*inch, "MANASWINI FOODS PVT. LTD.")
                c.drawRightString(width - 0.5*inch, 0.35*inch, "Mr. Sandeep Gadhwal")
                c.drawRightString(width - 0.5*inch, 0.22*inch, "Director")
                
                c.setFont("Helvetica", 6)
                c.drawString(0.5*inch, 0.3*inch, "This is a computer-generated document and does not require a signature.")
                
                c.save()
                file_buffers.append((filename, pdf_buffer.getvalue(), "pdf"))
        
        # Return files
        if len(file_buffers) == 1:
            filename, content, fmt_type = file_buffers[0]
            media_type = "application/pdf" if fmt_type == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            return Response(
                content=content,
                media_type=media_type,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )
        else:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for filename, content, _ in file_buffers:
                    zf.writestr(filename, content)
            
            zip_buffer.seek(0)
            zip_filename = f"Payslips_{req.targetCenter or 'ALL'}_{req.month}.zip"
            
            return Response(
                content=zip_buffer.getvalue(),
                media_type="application/zip",
                headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
            )
            
    except Exception as e:
        logger.error(f"Payslip generation error: {e}")
        raise HTTPException(500, str(e))

# =======================================
# BHOJAN GURU ENDPOINTS
# =======================================

# Load recipe and description data from JSON files
def load_recipe_data():
    recipe_file = ROOT_DIR / "recipes_db.json"
    if recipe_file.exists():
        with open(recipe_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"categories": [], "recipes": {}}

def load_description_data():
    desc_file = ROOT_DIR / "description_data.json"
    if desc_file.exists():
        with open(desc_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@api_router.get("/recipes")
async def get_recipes():
    """Get all recipes with ingredients and methods"""
    data = load_recipe_data()
    return {
        "categories": data.get("categories", []),
        "recipes": data.get("recipes", {}),
    }

@api_router.get("/descriptions")
async def get_descriptions():
    """Get all menu item descriptions in English and Marathi"""
    return {"descriptions": load_description_data()}

# Load Bhojan Guru data
def load_bhojan_guru_data():
    bhojan_file = ROOT_DIR / "bhojan_guru_data.json"
    if bhojan_file.exists():
        with open(bhojan_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"bhojanGuru": {}, "regionWise": {}, "bodyNeedMatrix": {}}

@api_router.get("/bhojan_guru")
async def get_bhojan_guru():
    """Get Bhojan Guru recommendations data - mood/occasion/season based suggestions"""
    data = load_bhojan_guru_data()
    return {
        "bhojanGuru": data.get("bhojanGuru", {}),
        "regionWise": data.get("regionWise", {}),
        "bodyNeedMatrix": data.get("bodyNeedMatrix", {})
    }

@api_router.post("/bhojan_guru/suggest")
async def suggest_by_filters(
    mood: Optional[str] = None,
    occasion: Optional[str] = None,
    season: Optional[str] = None,
    spice: Optional[str] = None
):
    """Get dish suggestions based on mood, occasion, season, and spice preference"""
    data = load_bhojan_guru_data()
    bhojan_guru = data.get("bhojanGuru", {})
    
    suggestions = []
    for key, item in bhojan_guru.items():
        score = 0
        
        # Check mood match
        if mood and mood.lower() in [m.lower() for m in item.get("mood", [])]:
            score += 2
        
        # Check occasion match
        if occasion and occasion.lower() in [o.lower() for o in item.get("occasion", [])]:
            score += 2
        
        # Check season match
        item_seasons = [s.lower() for s in item.get("season", [])]
        if season and (season.lower() in item_seasons or "all" in item_seasons):
            score += 1
        
        # Check spice match
        if spice and spice.lower() == item.get("spice", "").lower():
            score += 1
        
        if score > 0:
            suggestions.append({
                "key": key,
                "display": item.get("display"),
                "score": score,
                "mood": item.get("mood", []),
                "occasion": item.get("occasion", []),
                "spice": item.get("spice"),
                "tags": item.get("tags", []),
                "best_with": item.get("best_with", []),
                "combo": item.get("combo", []),
                "upsell": item.get("upsell", [])
            })
    
    # Sort by score descending
    suggestions.sort(key=lambda x: x["score"], reverse=True)
    
    return {"suggestions": suggestions[:10]}

@api_router.get("/bhojan_guru/region/{day}")
async def get_region_recommendation(day: str):
    """Get region-wise thali recommendation for a specific day"""
    data = load_bhojan_guru_data()
    region_wise = data.get("regionWise", {})
    
    day_capitalized = day.capitalize()
    if day_capitalized in region_wise:
        return {"day": day_capitalized, "recommendation": region_wise[day_capitalized]}
    
    return {"day": day_capitalized, "recommendation": None, "message": "No recommendation for this day"}

@api_router.post("/bhojan_guru/body_need")
async def body_need_suggestion(
    energy: str = "normal",
    digestion: str = "normal",
    mood: str = "calm",
    spice: str = "mild",
    purpose: str = "family",
    weather: str = "any"
):
    """Generate food recommendation based on body needs (6 questions)"""
    data = load_bhojan_guru_data()
    matrix = data.get("bodyNeedMatrix", {})
    bhojan_guru = data.get("bhojanGuru", {})
    
    # Collect preferences and avoidances
    prefer_tags = set()
    avoid_tags = set()
    
    for category, value in [
        ("energy", energy),
        ("digestion", digestion),
        ("mood", mood),
        ("spice", spice),
        ("purpose", purpose),
        ("weather", weather)
    ]:
        if category in matrix and value in matrix[category]:
            prefer_tags.update(matrix[category][value].get("prefer", []))
            avoid_tags.update(matrix[category][value].get("avoid", []))
    
    # Score items based on preferences
    recommendations = []
    for key, item in bhojan_guru.items():
        item_tags = set([t.lower() for t in item.get("tags", [])])
        item_tags.add(item.get("spice", "").lower())
        
        # Calculate score
        score = 0
        
        # Add points for matching preferences
        for pref in prefer_tags:
            if pref.lower() in item_tags or pref.lower() in key.lower():
                score += 1
        
        # Subtract points for things to avoid
        for avoid in avoid_tags:
            if avoid.lower() in item_tags or avoid.lower() in key.lower():
                score -= 2
        
        # Bonus for mild items if digestion is sensitive
        if digestion == "sensitive" and item.get("spice") in ["mild", "very mild", "sweet"]:
            score += 2
        
        # Bonus for cooling items in hot weather
        if weather == "hot" and "cooling" in [m.lower() for m in item.get("mood", [])]:
            score += 2
        
        # Bonus for comfort food when stressed
        if mood == "stressed" and "comfort" in [m.lower() for m in item.get("mood", [])]:
            score += 2
        
        recommendations.append({
            "key": key,
            "display": item.get("display"),
            "score": score,
            "spice": item.get("spice"),
            "tags": item.get("tags", []),
            "best_with": item.get("best_with", [])
        })
    
    # Sort and return top recommendations
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "recommendations": recommendations[:5],
        "preferences": list(prefer_tags),
        "avoidances": list(avoid_tags)
    }

# Recipe management models
class RecipeCreate(BaseModel):
    key: str
    name: str
    display: str
    ingredients: List[str] = []
    method: List[str] = []
    category: str = "MAINS"
    image: Optional[str] = ""

class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    display: Optional[str] = None
    ingredients: Optional[List[str]] = None
    method: Optional[List[str]] = None
    category: Optional[str] = None
    image: Optional[str] = None

def save_recipe_data(data: dict):
    """Save recipe data to JSON file"""
    recipe_file = ROOT_DIR / "recipes_db.json"
    with open(recipe_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@api_router.post("/recipes")
async def create_recipe(req: RecipeCreate, token: str):
    """Create a new recipe (MGT only)"""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can manage recipes")
    
    data = load_recipe_data()
    
    # Check if key already exists
    if req.key in data.get("recipes", {}):
        raise HTTPException(400, f"Recipe '{req.key}' already exists")
    
    # Add new recipe
    if "recipes" not in data:
        data["recipes"] = {}
    
    data["recipes"][req.key] = {
        "name": req.name,
        "display": req.display,
        "ingredients": req.ingredients,
        "method": req.method,
        "category": req.category.upper(),
        "image": req.image or ""
    }
    
    save_recipe_data(data)
    logger.info(f"Recipe created: {req.key} by {session.get('managerName')}")
    
    return {"success": True, "message": f"Recipe '{req.display}' created successfully"}

@api_router.put("/recipes/{recipe_key}")
async def update_recipe(recipe_key: str, req: RecipeUpdate, token: str):
    """Update an existing recipe (MGT only)"""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can manage recipes")
    
    data = load_recipe_data()
    
    if recipe_key not in data.get("recipes", {}):
        raise HTTPException(404, f"Recipe '{recipe_key}' not found")
    
    # Update fields
    recipe = data["recipes"][recipe_key]
    if req.name is not None:
        recipe["name"] = req.name
    if req.display is not None:
        recipe["display"] = req.display
    if req.ingredients is not None:
        recipe["ingredients"] = req.ingredients
    if req.method is not None:
        recipe["method"] = req.method
    if req.category is not None:
        recipe["category"] = req.category.upper()
    if req.image is not None:
        recipe["image"] = req.image
    
    save_recipe_data(data)
    logger.info(f"Recipe updated: {recipe_key} by {session.get('managerName')}")
    
    return {"success": True, "message": f"Recipe '{recipe_key}' updated successfully"}

@api_router.delete("/recipes/{recipe_key}")
async def delete_recipe(recipe_key: str, token: str):
    """Delete a recipe (MGT only)"""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can manage recipes")
    
    data = load_recipe_data()
    
    if recipe_key not in data.get("recipes", {}):
        raise HTTPException(404, f"Recipe '{recipe_key}' not found")
    
    # Delete recipe
    del data["recipes"][recipe_key]
    save_recipe_data(data)
    logger.info(f"Recipe deleted: {recipe_key} by {session.get('managerName')}")
    
    return {"success": True, "message": f"Recipe '{recipe_key}' deleted successfully"}

@api_router.get("/recipes/categories")
async def get_recipe_categories():
    """Get all recipe categories"""
    data = load_recipe_data()
    return {"categories": data.get("categories", [])}

@api_router.get("/recipes/search")
async def search_recipes(q: str = ""):
    """Search recipes by name or display"""
    data = load_recipe_data()
    recipes = data.get("recipes", {})
    
    if not q:
        return {"recipes": recipes}
    
    q_lower = q.lower()
    filtered = {}
    for key, recipe in recipes.items():
        name = recipe.get("name", "").lower()
        display = recipe.get("display", "").lower()
        category = recipe.get("category", "").lower()
        if q_lower in name or q_lower in display or q_lower in key or q_lower in category:
            filtered[key] = recipe
    
    return {"recipes": filtered}

# =======================================
# GUEST RESPONSE AI ENDPOINTS
# =======================================

# Center information for AI context
CENTER_INFO = {
    "PB-HSR": {
        "name": "Purnabramha HSR - Bangalore",
        "address": "Bhagyalakshmi Square, 17/N, 18th Cross Rd, near Zepto, Sector 3, HSR Layout, Bengaluru, Karnataka 560102",
        "phone": "+91 85500 78515",
        "timings": "12:00 PM - 10:30 PM",
        "country": "India"
    },
    "PB-TH": {
        "name": "Purnabramha Thane - Mumbai",
        "address": "Thane, Mumbai, Maharashtra",
        "phone": "+91 89047 49084",
        "timings": "12:00 PM - 10:30 PM",
        "country": "India"
    },
    "PB-SN": {
        "name": "Purnabramha Sambhajinagar (Aurangabad)",
        "address": "Ch. Sambhajinagar, Maharashtra",
        "phone": "+91 89710 49084",
        "timings": "12:00 PM - 10:30 PM",
        "country": "India"
    },
    "PB-DV": {
        "name": "Purnabramha Dombivli - Mumbai",
        "address": "Dombivli, Mumbai, Maharashtra",
        "phone": "+91 96064 55433",
        "timings": "12:00 PM - 10:30 PM",
        "country": "India"
    },
    "PB-HW": {
        "name": "Purnabramha Hinjawadi - Pune",
        "address": "Hinjawadi, Pune, Maharashtra",
        "phone": "+91 96064 55434",
        "timings": "12:00 PM - 10:30 PM",
        "country": "India"
    },
    "PB-KN": {
        "name": "Purnabramha Kharadi Nyati - Pune",
        "address": "Kharadi Nyati, Pune, Maharashtra",
        "phone": "+91 99000 89803",
        "timings": "12:00 PM - 10:30 PM",
        "country": "India"
    },
    "PB-KAL": {
        "name": "Purnabramha Kalyan",
        "address": "Kalyan, Maharashtra",
        "phone": "+91 96064 55433",
        "timings": "12:00 PM - 10:30 PM",
        "country": "India"
    },
    "PB-PERTH": {
        "name": "Purnabramha Perth - Australia",
        "address": "Perth, Western Australia",
        "phone": "+61 401 832 922",
        "timings": "12:00 PM - 10:00 PM",
        "country": "Australia"
    }
}

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
        
        # Get center context
        center_info = CENTER_INFO.get(req.center.upper(), {})
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
    """Get all center information"""
    return {"centers": CENTER_INFO}

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
        
        # Get center context
        center_info = CENTER_INFO.get(req.center.upper(), {})
        center_context = f"\n\nCenter: {req.center}\n"
        if center_info:
            center_context += f"Center Name: {center_info.get('name', 'Purnabramha')}\n"
            center_context += f"Address: {center_info.get('address', '')}\n"
            center_context += f"Phone: {center_info.get('phone', '')}\n"
            center_context += f"Timings: {center_info.get('timings', '12:00 PM - 10:30 PM')}\n"
            center_context += f"Country: {center_info.get('country', 'India')}\n"
        
        # Currency context
        is_perth = req.center.upper() in ["PB-PERTH", "PERTH"]
        currency_context = f"\nCurrency: {'AUD ($)' if is_perth else 'INR (₹)'}\n"
        
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
# HR LETTERS AI ENDPOINTS (MGT ONLY)
# =======================================

class HRLetterRequest(BaseModel):
    token: str
    employeeName: str
    letterType: str  # offer, exit, experience, visa
    # Additional fields for specific letter types
    joiningDate: Optional[str] = None  # For offer letter
    salary: Optional[str] = None  # For offer letter
    lastWorkingDate: Optional[str] = None  # For exit letter
    exitReason: Optional[str] = None  # For exit letter
    # Visa letter specific fields
    destinationCountry: Optional[str] = None
    visaNumber: Optional[str] = None
    travelPurpose: Optional[str] = None  # business visit, training, project work
    travelDuration: Optional[str] = None  # e.g., "15 days", "3 months"
    travelStartDate: Optional[str] = None
    travelEndDate: Optional[str] = None
    invitingCompany: Optional[str] = None  # For business visits
    projectDetails: Optional[str] = None  # For project-based letters

HR_LETTER_SYSTEM_PROMPT = """You are an expert HR letter writer for Manaswini Foods Pvt. Ltd. (Purnabramha Restaurant Chain).

Company Details:
- Company Name: MANASWINI FOODS PVT. LTD.
- Brand: Purnabramha - The Largest Maharashtrian Restaurant Chain
- Registered Address: 17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout, Bangalore, Karnataka-560102
- Director: Mr. Sandeep Gadhwal
- CIN: (Company Identification Number will be added)

Your task is to generate professional, legally appropriate HR letters. Each letter should:
1. Be formal and professional in tone
2. Include all necessary details provided
3. Follow standard Indian HR letter formats
4. Include appropriate date formatting (DD-MM-YYYY)
5. End with signature block for Mr. Sandeep Gadhwal, Director

Important: Generate ONLY the letter content. Do not include any explanations or notes outside the letter."""

@api_router.post("/hr_letter/generate")
async def generate_hr_letter(req: HRLetterRequest):
    """Generate HR letters using AI (MGT only)"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can generate HR letters")
    
    # Get employee details from database
    emp = await db.employees.find_one(
        {"name": {"$regex": f"^{req.employeeName}$", "$options": "i"}},
        {"_id": 0}
    )
    
    if not emp:
        raise HTTPException(404, f"Employee '{req.employeeName}' not found in database")
    
    # Build the prompt based on letter type
    today = datetime.now().strftime("%d-%m-%Y")
    
    if req.letterType == "offer":
        prompt = f"""Generate a professional OFFER LETTER for the following employee:

Employee Name: {emp.get('name')}
Designation: {emp.get('designation', 'N/A')}
Department: {emp.get('center', 'N/A')}
Date of Joining: {req.joiningDate or emp.get('dateOfJoining', 'N/A')}
Monthly Salary: Rs. {req.salary or emp.get('currentSalary', 'N/A')}
Bank Details: {emp.get('bankName', 'N/A')} - A/C: {emp.get('beneAccNo', 'N/A')}

Today's Date: {today}

The offer letter should include:
1. Welcome and congratulations
2. Position offered and reporting structure
3. Compensation details
4. Terms of employment
5. Joining formalities
6. Company policies overview
7. Acceptance clause"""

    elif req.letterType == "exit":
        prompt = f"""Generate a professional EXIT/RESIGNATION ACCEPTANCE LETTER for the following employee:

Employee Name: {emp.get('name')}
Designation: {emp.get('designation', 'N/A')}
Department: {emp.get('center', 'N/A')}
Date of Joining: {emp.get('dateOfJoining', 'N/A')}
Last Working Date: {req.lastWorkingDate or 'As per notice period'}
Reason for Exit: {req.exitReason or 'Personal reasons'}

Today's Date: {today}

The exit letter should include:
1. Acknowledgment of resignation
2. Acceptance of last working date
3. Handover responsibilities
4. Settlement of dues
5. Return of company property
6. Wishes for future endeavors"""

    elif req.letterType == "experience":
        prompt = f"""Generate a professional EXPERIENCE/SERVICE CERTIFICATE for the following employee:

Employee Name: {emp.get('name')}
Designation: {emp.get('designation', 'N/A')}
Department: {emp.get('center', 'N/A')}
Date of Joining: {emp.get('dateOfJoining', 'N/A')}
Last Working Date: {req.lastWorkingDate or today}
Gender: {emp.get('gender', 'N/A')}

Today's Date: {today}

The experience letter should include:
1. Employment confirmation with dates
2. Designation and responsibilities
3. Performance appreciation
4. Character and conduct certification
5. Best wishes for future"""

    elif req.letterType == "visa":
        prompt = f"""Generate a professional VISA SUPPORT/INVITATION LETTER for immigration purposes:

Employee Name: {emp.get('name')}
Designation: {emp.get('designation', 'N/A')}
Department: {emp.get('center', 'N/A')}
Date of Joining: {emp.get('dateOfJoining', 'N/A')}
Current Salary: Rs. {emp.get('currentSalary', 'N/A')} per month
Gender: {emp.get('gender', 'N/A')}

Travel Details:
- Destination Country: {req.destinationCountry or 'N/A'}
- Visa Number (if available): {req.visaNumber or 'Applied/Pending'}
- Purpose of Travel: {req.travelPurpose or 'Business Visit'}
- Duration of Stay: {req.travelDuration or 'N/A'}
- Travel Start Date: {req.travelStartDate or 'N/A'}
- Travel End Date: {req.travelEndDate or 'N/A'}
- Inviting Company/Organization: {req.invitingCompany or 'N/A'}
- Project/Business Details: {req.projectDetails or 'Business meetings and coordination'}

Today's Date: {today}

The visa support letter should include:
1. Company introduction and legitimacy
2. Employee confirmation and role
3. Purpose of visit clearly stated
4. Travel dates and duration
5. Financial responsibility statement (company will bear expenses OR employee self-funded)
6. Guarantee of return to India after visit
7. Contact details for verification
8. Request for visa approval

This letter is for immigration/visa authorities of {req.destinationCountry or 'the destination country'}."""

    else:
        raise HTTPException(400, f"Invalid letter type: {req.letterType}")
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(500, "AI service not configured")
        
        session_id = f"hr_letter_{req.letterType}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=HR_LETTER_SYSTEM_PROMPT
        ).with_model("openai", "gpt-5.2")
        
        user_message = UserMessage(text=prompt)
        letter_content = await chat.send_message(user_message)
        
        # Log the letter generation
        await db.hr_letters.insert_one({
            "employeeName": emp.get('name'),
            "letterType": req.letterType,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "generatedBy": session.get("managerName", ""),
            "content": letter_content[:500] + "..."  # Store summary only
        })
        
        logger.info(f"HR Letter ({req.letterType}) generated for {emp.get('name')} by {session.get('managerName')}")
        
        return {
            "success": True,
            "letterType": req.letterType,
            "employeeName": emp.get('name'),
            "content": letter_content,
            "generatedAt": today
        }
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(500, "AI library not available")
    except Exception as e:
        logger.error(f"HR Letter generation error: {e}")
        raise HTTPException(500, f"Failed to generate letter: {str(e)}")

@api_router.get("/hr_letter/employees")
async def get_employees_for_hr(token: str):
    """Get list of employees for HR letter generation (MGT only)"""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can access HR features")
    
    employees = await db.employees.find(
        {},
        {"_id": 0, "name": 1, "designation": 1, "center": 1, "dateOfJoining": 1, "currentSalary": 1, "gender": 1}
    ).to_list(1000)
    
    return {"employees": employees}

class HRLetterDownloadRequest(BaseModel):
    token: str
    content: str
    letterType: str
    employeeName: str
    format: str  # pdf or docx

@api_router.post("/hr_letter/download")
async def download_hr_letter(req: HRLetterDownloadRequest):
    """Download HR letter as PDF or Word document"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can download HR letters")
    
    today = datetime.now().strftime("%d-%m-%Y")
    safe_name = req.employeeName.replace(" ", "_")
    
    if req.format == "pdf":
        # Generate PDF
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Image
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
        
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, 
                               leftMargin=0.75*inch, rightMargin=0.75*inch,
                               topMargin=0.5*inch, bottomMargin=0.75*inch)
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=6
        )
        
        company_style = ParagraphStyle(
            'Company',
            parent=styles['Normal'],
            fontSize=11,
            alignment=TA_CENTER,
            spaceAfter=3
        )
        
        address_style = ParagraphStyle(
            'Address',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            spaceAfter=12
        )
        
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            leading=14,
            spaceAfter=8
        )
        
        signature_style = ParagraphStyle(
            'Signature',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT,
            spaceBefore=30
        )
        
        story = []
        
        # Try to add logo
        logo_path = ROOT_DIR / "pb_logo.png"
        if logo_path.exists():
            try:
                img = Image(str(logo_path), width=1.5*inch, height=1*inch)
                img.hAlign = 'CENTER'
                story.append(img)
            except:
                story.append(Paragraph("<b>Purnabramha®</b>", title_style))
        else:
            story.append(Paragraph("<b>Purnabramha®</b>", title_style))
        
        story.append(Paragraph("<b>MANASWINI FOODS PVT. LTD.</b>", company_style))
        story.append(Paragraph("17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout, Bangalore, Karnataka-560102", address_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Letter type title
        letter_titles = {
            "offer": "OFFER LETTER",
            "exit": "EXIT / RESIGNATION ACCEPTANCE LETTER", 
            "experience": "EXPERIENCE CERTIFICATE",
            "visa": "VISA SUPPORT LETTER"
        }
        story.append(Paragraph(f"<b>{letter_titles.get(req.letterType, 'HR LETTER')}</b>", title_style))
        story.append(Paragraph(f"Date: {today}", ParagraphStyle('Date', parent=styles['Normal'], fontSize=10, alignment=TA_LEFT)))
        story.append(Spacer(1, 0.2*inch))
        
        # Process content - convert markdown-like formatting to HTML
        content_lines = req.content.split('\n')
        for line in content_lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 0.1*inch))
                continue
            
            # Convert markdown bold to HTML properly
            # Replace pairs of ** with <b> and </b>
            import re
            line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
            
            # Handle single asterisks for bullet points
            if line.startswith('- '):
                line = f"• {line[2:]}"
            elif line.startswith('* '):
                line = f"• {line[2:]}"
            
            # Escape any remaining problematic characters
            line = line.replace('&', '&amp;')
            
            try:
                story.append(Paragraph(line, body_style))
            except Exception as pe:
                # If paragraph fails, add as plain text without formatting
                clean_line = re.sub(r'<[^>]+>', '', line)  # Remove all HTML tags
                story.append(Paragraph(clean_line, body_style))
        
        # Signature section
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("For <b>MANASWINI FOODS PVT. LTD.</b>", signature_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Try to add signature image
        sign_path = ROOT_DIR / "sign.png"
        if sign_path.exists():
            try:
                sign_img = Image(str(sign_path), width=1.2*inch, height=0.7*inch)
                story.append(sign_img)
            except:
                pass
        
        story.append(Paragraph("<b>Mr. Sandeep Gadhwal</b>", signature_style))
        story.append(Paragraph("Director", signature_style))
        
        doc.build(story)
        pdf_buffer.seek(0)
        
        filename = f"{req.letterType}_letter_{safe_name}_{today.replace('-', '')}.pdf"
        
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    
    elif req.format == "docx":
        # Generate Word document
        from docx import Document
        from docx.shared import Inches, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.style import WD_STYLE_TYPE
        
        doc = Document()
        
        # Set margins
        sections = doc.sections
        for section in sections:
            section.left_margin = Inches(0.75)
            section.right_margin = Inches(0.75)
            section.top_margin = Inches(0.5)
            section.bottom_margin = Inches(0.75)
        
        # Add logo if exists
        logo_path = ROOT_DIR / "pb_logo.png"
        if logo_path.exists():
            try:
                para = doc.add_paragraph()
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = para.add_run()
                run.add_picture(str(logo_path), width=Inches(1.5))
            except:
                title = doc.add_paragraph("Purnabramha®")
                title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                title.runs[0].bold = True
                title.runs[0].font.size = Pt(18)
        else:
            title = doc.add_paragraph("Purnabramha®")
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title.runs[0].bold = True
            title.runs[0].font.size = Pt(18)
        
        # Company name
        company = doc.add_paragraph("MANASWINI FOODS PVT. LTD.")
        company.alignment = WD_ALIGN_PARAGRAPH.CENTER
        company.runs[0].bold = True
        company.runs[0].font.size = Pt(12)
        
        # Address
        address = doc.add_paragraph("17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout, Bangalore, Karnataka-560102")
        address.alignment = WD_ALIGN_PARAGRAPH.CENTER
        address.runs[0].font.size = Pt(8)
        
        doc.add_paragraph()  # Spacer
        
        # Letter title
        letter_titles = {
            "offer": "OFFER LETTER",
            "exit": "EXIT / RESIGNATION ACCEPTANCE LETTER",
            "experience": "EXPERIENCE CERTIFICATE",
            "visa": "VISA SUPPORT LETTER"
        }
        letter_title = doc.add_paragraph(letter_titles.get(req.letterType, "HR LETTER"))
        letter_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        letter_title.runs[0].bold = True
        letter_title.runs[0].font.size = Pt(14)
        
        # Date
        date_para = doc.add_paragraph(f"Date: {today}")
        date_para.runs[0].font.size = Pt(10)
        
        doc.add_paragraph()  # Spacer
        
        # Content
        content_lines = req.content.split('\n')
        for line in content_lines:
            line = line.strip()
            if not line:
                doc.add_paragraph()
                continue
            
            # Remove markdown formatting for Word
            line = line.replace('**', '')
            
            para = doc.add_paragraph(line)
            para.runs[0].font.size = Pt(10)
            
            # Handle bullet points
            if line.startswith('- ') or line.startswith('• '):
                para.paragraph_format.left_indent = Inches(0.25)
        
        # Signature section
        doc.add_paragraph()
        doc.add_paragraph()
        
        sig = doc.add_paragraph("For MANASWINI FOODS PVT. LTD.")
        sig.runs[0].bold = True
        sig.runs[0].font.size = Pt(10)
        
        # Add signature image if exists
        sign_path = ROOT_DIR / "sign.png"
        if sign_path.exists():
            try:
                sig_para = doc.add_paragraph()
                run = sig_para.add_run()
                run.add_picture(str(sign_path), width=Inches(1.2))
            except:
                doc.add_paragraph()
        else:
            doc.add_paragraph()
        
        director = doc.add_paragraph("Mr. Sandeep Gadhwal")
        director.runs[0].bold = True
        director.runs[0].font.size = Pt(10)
        
        title_para = doc.add_paragraph("Director")
        title_para.runs[0].font.size = Pt(10)
        
        # Save to buffer
        docx_buffer = BytesIO()
        doc.save(docx_buffer)
        docx_buffer.seek(0)
        
        filename = f"{req.letterType}_letter_{safe_name}_{today.replace('-', '')}.docx"
        
        return Response(
            content=docx_buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

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
    """Get list of all centers from DB or default"""
    centers = await db.centers.find({}, {"_id": 0}).to_list(100)
    if not centers:
        # Return default centers if none in DB
        centers = [
            {"code": "PB-HSR", "name": "Purnabramha HSR - Bangalore", "phone": "+91 85500 78515", "email": "purnabramha.hsr09@gmail.com", "address": "17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout, Bangalore, Karnataka-560102", "active": True},
            {"code": "PB-TH", "name": "Purnabramha Thane - Mumbai", "phone": "+91 89047 49084", "email": "purnabramha.newthane@gmail.com", "address": "Thane, Mumbai, Maharashtra", "active": True},
            {"code": "PB-SN", "name": "Purnabramha Sambhajinagar", "phone": "+91 89710 49084", "email": "Purnabramha.aurangabad@gmail.com", "address": "Ch. Sambhajinagar, Maharashtra", "active": True},
            {"code": "PB-DV", "name": "Purnabramha Dombivli - Mumbai", "phone": "+91 96064 55433", "email": "purnabramha.dombivli@gmail.com", "address": "Dombivli, Mumbai, Maharashtra", "active": True},
            {"code": "PB-HW", "name": "Purnabramha Hinjawadi - Pune", "phone": "+91 96064 55434", "email": "Purnabramha.hinjawadi@gmail.com", "address": "Hinjawadi, Pune, Maharashtra", "active": True},
            {"code": "PB-KN", "name": "Purnabramha Kharadi Nyati - Pune", "phone": "", "email": "Purnabramha.kharadinyati@gmail.com", "address": "Kharadi Nyati, Pune, Maharashtra", "active": True},
            {"code": "PB-KAL", "name": "Purnabramha Kalyan", "phone": "", "email": "purnabramha.kalyan@gmail.com", "address": "Kalyan, Maharashtra", "active": True},
            {"code": "PB-PERTH", "name": "Purnabramha Perth - Australia", "phone": "0401832922", "email": "Purnabramha.perth@gmail.com", "address": "Perth, Australia", "active": True},
            {"code": "PB-MGT", "name": "Purnabramha Management (HQ)", "phone": "+91 9960886185", "email": "sandeep.gadhwal@purnabramha.com", "address": "HSR Layout, Bangalore", "active": True},
        ]
    return {"centers": centers}

# =======================================
# CENTERS MANAGEMENT ENDPOINTS (MGT Only)
# =======================================

class CenterCreate(BaseModel):
    code: str
    name: str
    phone: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    active: Optional[bool] = True

class CenterUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    active: Optional[bool] = None

@api_router.post("/mgt/centers")
async def mgt_get_centers(data: dict):
    """Get all centers for management (MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can manage centers")
    
    centers = await db.centers.find({}, {"_id": 0}).to_list(100)
    if not centers:
        # Seed default centers if none exist
        default_centers = [
            {"code": "PB-HSR", "name": "Purnabramha HSR - Bangalore", "phone": "+91 85500 78515", "email": "purnabramha.hsr09@gmail.com", "address": "17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout, Bangalore, Karnataka-560102", "active": True},
            {"code": "PB-TH", "name": "Purnabramha Thane - Mumbai", "phone": "+91 89047 49084", "email": "purnabramha.newthane@gmail.com", "address": "Thane, Mumbai, Maharashtra", "active": True},
            {"code": "PB-SN", "name": "Purnabramha Sambhajinagar", "phone": "+91 89710 49084", "email": "Purnabramha.aurangabad@gmail.com", "address": "Ch. Sambhajinagar, Maharashtra", "active": True},
            {"code": "PB-DV", "name": "Purnabramha Dombivli - Mumbai", "phone": "+91 96064 55433", "email": "purnabramha.dombivli@gmail.com", "address": "Dombivli, Mumbai, Maharashtra", "active": True},
            {"code": "PB-HW", "name": "Purnabramha Hinjawadi - Pune", "phone": "+91 96064 55434", "email": "Purnabramha.hinjawadi@gmail.com", "address": "Hinjawadi, Pune, Maharashtra", "active": True},
            {"code": "PB-KN", "name": "Purnabramha Kharadi Nyati - Pune", "phone": "", "email": "Purnabramha.kharadinyati@gmail.com", "address": "Kharadi Nyati, Pune, Maharashtra", "active": True},
            {"code": "PB-KAL", "name": "Purnabramha Kalyan", "phone": "", "email": "purnabramha.kalyan@gmail.com", "address": "Kalyan, Maharashtra", "active": True},
            {"code": "PB-PERTH", "name": "Purnabramha Perth - Australia", "phone": "0401832922", "email": "Purnabramha.perth@gmail.com", "address": "Perth, Australia", "active": True},
            {"code": "PB-MGT", "name": "Purnabramha Management (HQ)", "phone": "+91 9960886185", "email": "sandeep.gadhwal@purnabramha.com", "address": "HSR Layout, Bangalore", "active": True},
        ]
        for c in default_centers:
            await db.centers.update_one({"code": c["code"]}, {"$set": c}, upsert=True)
        centers = default_centers
    
    return {"centers": centers}

@api_router.post("/mgt/center_create")
async def mgt_center_create(data: dict):
    """Create a new center (MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can create centers")
    
    code = data.get("code", "").upper().strip()
    if not code:
        raise HTTPException(400, "Center code is required")
    
    # Check if center code already exists
    existing = await db.centers.find_one({"code": code}, {"_id": 0})
    if existing:
        raise HTTPException(400, f"Center with code '{code}' already exists")
    
    center = {
        "code": code,
        "name": data.get("name", "").strip(),
        "phone": data.get("phone", "").strip(),
        "email": data.get("email", "").strip(),
        "address": data.get("address", "").strip(),
        "active": data.get("active", True),
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.centers.insert_one(center)
    logger.info(f"Center created: {code} by {session.get('managerName')}")
    
    return {"success": True, "message": f"Center '{code}' created successfully"}

@api_router.post("/mgt/center_update")
async def mgt_center_update(data: dict):
    """Update an existing center (MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can update centers")
    
    code = data.get("code", "").upper().strip()
    if not code:
        raise HTTPException(400, "Center code is required")
    
    update_data = {"updatedAt": datetime.now(timezone.utc).isoformat()}
    if "name" in data and data["name"] is not None:
        update_data["name"] = data["name"].strip()
    if "phone" in data and data["phone"] is not None:
        update_data["phone"] = data["phone"].strip()
    if "email" in data and data["email"] is not None:
        update_data["email"] = data["email"].strip()
    if "address" in data and data["address"] is not None:
        update_data["address"] = data["address"].strip()
    if "active" in data and data["active"] is not None:
        update_data["active"] = data["active"]
    
    result = await db.centers.update_one({"code": code}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(404, f"Center '{code}' not found")
    
    logger.info(f"Center updated: {code} by {session.get('managerName')}")
    return {"success": True, "message": f"Center '{code}' updated successfully"}

@api_router.post("/mgt/center_delete")
async def mgt_center_delete(data: dict):
    """Delete a center (MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can delete centers")
    
    code = data.get("code", "").upper().strip()
    if not code:
        raise HTTPException(400, "Center code is required")
    
    if code == "PB-MGT":
        raise HTTPException(400, "Cannot delete the Management HQ center")
    
    result = await db.centers.delete_one({"code": code})
    
    if result.deleted_count == 0:
        raise HTTPException(404, f"Center '{code}' not found")
    
    logger.info(f"Center deleted: {code} by {session.get('managerName')}")
    return {"success": True, "message": f"Center '{code}' deleted successfully"}

# =======================================
# MANAGERS MANAGEMENT ENDPOINTS (MGT Only)
# =======================================

@api_router.post("/mgt/managers")
async def mgt_get_managers(data: dict):
    """Get all managers (Super Admin only)"""
    token = data.get("token")
    session = verify_token(token)
    
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Only Super Admins can see manager list
    is_super_admin = session.get("is_super_admin", False)
    if not is_super_admin:
        raise HTTPException(403, "Only Super Admin can manage managers")
    
    managers = await db.managers.find({}, {"_id": 0}).to_list(100)
    return {"managers": managers}

@api_router.post("/mgt/manager_create")
async def mgt_manager_create(data: dict):
    """Create a new manager (Admin/MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    
    # Check access
    is_super_admin = session.get("is_super_admin", False) if session else False
    is_admin = session.get("is_admin", False) if session else False
    is_mgt = session.get("center") == "PB-MGT" if session else False
    
    if not session or (not is_super_admin and not is_admin and not is_mgt):
        raise HTTPException(403, "Only Admin or PB-MGT can create managers")
    
    center = data.get("center", "").upper().strip()
    email = data.get("email", "").strip().lower()
    
    if not center or not email:
        raise HTTPException(400, "Center and email are required")
    
    # Check if manager with same email already exists
    existing = await db.managers.find_one({"email": email}, {"_id": 0})
    if existing:
        raise HTTPException(400, f"Manager with email '{email}' already exists")
    
    manager = {
        "center": center,
        "managerName": data.get("managerName", "").strip(),
        "mobile": data.get("mobile", "").strip(),
        "email": email,
        "active": data.get("active", True),
        "otpChannel": data.get("otpChannel", "email"),
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.managers.insert_one(manager)
    logger.info(f"Manager created: {email} for {center} by {session.get('managerName')}")
    
    return {"success": True, "message": f"Manager '{manager['managerName']}' created successfully"}

@api_router.post("/mgt/manager_update")
async def mgt_manager_update(data: dict):
    """Update an existing manager (MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can update managers")
    
    email = data.get("email", "").strip().lower()
    if not email:
        raise HTTPException(400, "Manager email is required for identification")
    
    update_data = {"updatedAt": datetime.now(timezone.utc).isoformat()}
    if "center" in data and data["center"] is not None:
        update_data["center"] = data["center"].upper().strip()
    if "managerName" in data and data["managerName"] is not None:
        update_data["managerName"] = data["managerName"].strip()
    if "mobile" in data and data["mobile"] is not None:
        update_data["mobile"] = data["mobile"].strip()
    if "active" in data and data["active"] is not None:
        update_data["active"] = data["active"]
    if "otpChannel" in data and data["otpChannel"] is not None:
        update_data["otpChannel"] = data["otpChannel"]
    
    result = await db.managers.update_one({"email": email}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(404, f"Manager with email '{email}' not found")
    
    logger.info(f"Manager updated: {email} by {session.get('managerName')}")
    return {"success": True, "message": f"Manager updated successfully"}

@api_router.post("/mgt/manager_delete")
async def mgt_manager_delete(data: dict):
    """Delete a manager (Admin/MGT only, Super Admin deletion only by Jayanti)"""
    token = data.get("token")
    session = verify_token(token)
    
    is_super_admin = session.get("is_super_admin", False) if session else False
    is_admin = session.get("is_admin", False) if session else False
    is_mgt = session.get("center") == "PB-MGT" if session else False
    current_email = session.get("email", "").lower() if session else ""
    jayanti_email = "jayanti.kathale@purnabramha.com"
    is_jayanti = current_email == jayanti_email
    
    if not session or (not is_super_admin and not is_admin and not is_mgt):
        raise HTTPException(403, "Only Admin or PB-MGT can delete managers")
    
    email = data.get("email", "").strip().lower()
    if not email:
        raise HTTPException(400, "Manager email is required")
    
    # Find the manager to check their status
    manager = await db.managers.find_one({"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}})
    if not manager:
        raise HTTPException(404, f"Manager with email '{email}' not found")
    
    # Only Jayanti can delete Super Admins
    if manager.get("is_super_admin") and not is_jayanti:
        raise HTTPException(403, "Only Jayanti Kathale can delete Super Admin accounts")
    
    # Prevent deleting Jayanti (master account)
    if email == jayanti_email and not is_jayanti:
        raise HTTPException(403, "Cannot delete the master Super Admin account")
    
    result = await db.managers.delete_one({"email": manager.get("email")})
    
    if result.deleted_count == 0:
        raise HTTPException(404, f"Manager with email '{email}' not found")
    
    logger.info(f"Manager deleted: {email} by {session.get('managerName')}")
    return {"success": True, "message": f"Manager deleted successfully"}

@api_router.post("/mgt/manager_roles")
async def mgt_manager_roles(data: dict):
    """Update a manager's role permissions (Super Admin only)"""
    token = data.get("token")
    session = verify_token(token)
    
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Only Super Admins can manage roles
    is_super_admin = session.get("is_super_admin", False)
    if not is_super_admin:
        raise HTTPException(403, "Only Super Admin can manage roles")
    
    email = data.get("email", "").strip()
    roles = data.get("roles", {})
    set_is_admin = data.get("is_admin", False)
    
    if not email:
        raise HTTPException(400, "Manager email is required")
    
    # Find the manager (case-insensitive email search)
    escaped_email = re.escape(email)
    manager = await db.managers.find_one({"email": {"$regex": f"^{escaped_email}$", "$options": "i"}})
    if not manager:
        raise HTTPException(404, f"Manager with email '{email}' not found")
    
    # Update roles - Super Admin can assign any combination of roles
    await db.managers.update_one(
        {"email": manager.get("email")},
        {"$set": {
            "roles": roles,
            "is_admin": set_is_admin,
            "rolesUpdatedAt": datetime.now(timezone.utc).isoformat(),
            "rolesUpdatedBy": session.get("managerName", "Unknown")
        }}
    )
    
    logger.info(f"Manager roles updated: {email} (admin={set_is_admin}) by {session.get('managerName')}")
    return {"success": True, "message": "Manager roles updated successfully"}

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
    c.drawCentredString(width/2, height - 340, f"Version 1.0 | December 2025")
    
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
from routes.sales_expenses import router as sales_router, set_db as set_sales_db, set_verify_token as set_sales_verify_token
set_sales_db(db)
set_sales_verify_token(verify_token)
app.include_router(sales_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
