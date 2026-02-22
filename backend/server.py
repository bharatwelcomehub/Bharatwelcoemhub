# =======================================
# Purnabramha IntraPB - Backend Server
# MongoDB-based Attendance & Salary System
# =======================================

from fastapi import FastAPI, APIRouter, HTTPException, Response
from fastapi.staticfiles import StaticFiles
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Load config.json for email settings (same as your original server.py)
def load_config() -> dict:
    path = ROOT_DIR / "config.json"
    if not path.exists():
        return {
            "otp": {"length": 6, "ttl_seconds": 300},
            "security": {"session_ttl_seconds": 43200},
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
    for key, data in otp_store.items():
        if data.get("token") == token:
            return data
    return None

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
    otp_store[key] = stored
    
    return {
        "success": True,
        "token": token,
        "center": stored["center"],
        "managerName": stored.get("managerName", "Manager"),
        "mobile": req.mobile
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
    """Get all employees (MGT only) with search"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can access employee management")
    
    employees = await db.employees.find({}, {"_id": 0}).sort("name", 1).to_list(1000)
    
    # Add row index for updates
    for idx, emp in enumerate(employees):
        emp["rowIndex"] = idx
    
    return {"employees": employees}

@api_router.post("/mgt_employee_create")
async def mgt_employee_create(data: dict):
    """Create new employee (MGT only)"""
    token = data.get("token")
    session = verify_token(token)
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can create employees")
    
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
    """Lock payroll for a month (MGT only)"""
    session = verify_token(req.token)
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can lock payroll")
    
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
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can view salary preview")
    
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
            # Try exact match first, then partial match
            emp_name_upper = req.employeeName.strip().upper()
            exact_query = {**query, "name": emp_name_upper}
            employees = await db.employees.find(exact_query, {"_id": 0}).to_list(10)
            
            if not employees:
                # Try partial match (contains)
                partial_query = {**query, "name": {"$regex": emp_name_upper, "$options": "i"}}
                employees = await db.employees.find(partial_query, {"_id": 0}).to_list(10)
        else:
            employees = await db.employees.find(query, {"_id": 0}).to_list(1000)
        
        if not employees:
            raise HTTPException(404, f"No employees found matching '{req.employeeName}'. Check the spelling and use full name in CAPS.")
        
        # Track generated PDFs in memory
        files_created = []
        pdf_buffers = []
        
        # Generate months
        months = []
        for i in range(period):
            m = month - i
            y = year
            while m <= 0:
                m += 12
                y -= 1
            months.append(f"{y}-{m:02d}")
        
        files_created = []
        
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
                
                # Get attendance
                attendance = await db.attendance.find(
                    {"employeeName": emp_name.upper(), "date": {"$regex": f"^{mon}"}},
                    {"_id": 0}
                ).to_list(100)
                
                weights = {"P": 1, "HD": 0.5, "WO": 1, "L": 1, "A": 0}
                present = sum(weights.get(a.get("status", ""), 0) for a in attendance)
                
                # Get advances
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
                present_days = d_primary  # Default to full month if no attendance data
            
            # Create PDF - EXACT format from Purnabramha payslip template
            if req.fmt == "pdf":
                filename = f"Payslip_{emp_name.replace(' ', '_')}_{req.month}.pdf"
                pdf_buffer = BytesIO()
                
                c = canvas.Canvas(pdf_buffer, pagesize=A4)
                width, height = A4
                
                # ============ HEADER ============
                # Try to add logo image
                logo_path = ROOT_DIR / "pb_logo.png"
                if logo_path.exists():
                    try:
                        c.drawImage(str(logo_path), width/2 - 0.75*inch, height - 1.1*inch, width=1.5*inch, height=1.0*inch, preserveAspectRatio=True, mask='auto')
                    except Exception as e:
                        logger.warning(f"Could not add logo: {e}")
                        # Fallback to text
                        c.setFont("Helvetica-Bold", 18)
                        c.drawCentredString(width/2, height - 0.6*inch, "Purnabramha®")
                else:
                    c.setFont("Helvetica-Bold", 18)
                    c.drawCentredString(width/2, height - 0.6*inch, "Purnabramha®")
                
                c.setFont("Helvetica-Bold", 11)
                c.drawCentredString(width/2, height - 1.25*inch, "MANASWINI FOODS PVT. LTD.")
                
                c.setFont("Helvetica", 8)
                c.drawCentredString(width/2, height - 1.4*inch, "17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout, Bangalore, Karnataka-560102")
                
                # ============ SALARY SLIP TITLE ============
                c.setFont("Helvetica-Bold", 12)
                c.drawCentredString(width/2, height - 1.65*inch, "SALARY SLIP")
                
                # ============ EMPLOYEE DETAILS ============
                y = height - 1.5*inch
                c.setFont("Helvetica", 9)
                
                # Left side - Employee info
                c.drawString(0.5*inch, y, f"Name            : {emp_name}")
                # Right side - Pay info
                c.drawString(4.5*inch, y, f"Pay Date          : {datetime.now().strftime('%d-%m-%Y')}")
                y -= 0.2*inch
                
                c.drawString(0.5*inch, y, f"Designation     : {emp.get('designation', 'N/A')}")
                # Format month nicely (e.g., "Oct-25" from "2025-10")
                month_parts = req.month.split("-")
                month_display = f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(month_parts[1])-1]}-{month_parts[0][2:]}"
                c.drawString(4.5*inch, y, f"Month of Salary : {month_display}")
                y -= 0.2*inch
                
                c.drawString(0.5*inch, y, f"Department      : {emp.get('center', 'KITCHEN')}")
                y -= 0.2*inch
                
                c.drawString(0.5*inch, y, f"Date of Birth   : {emp.get('dob', 'N/A')}")
                y -= 0.2*inch
                
                c.drawString(0.5*inch, y, f"Date of Joining : {emp.get('doj', 'N/A')}")
                
                # ============ MAIN TABLE BOX ============
                box_top = height - 2.4*inch
                box_bottom = 1.4*inch
                box_left = 0.4*inch
                box_right = width - 0.4*inch
                mid_col = 4.2*inch  # Divider between left and right sections
                
                c.setLineWidth(0.5)
                c.rect(box_left, box_bottom, box_right - box_left, box_top - box_bottom)
                # Vertical divider
                c.line(mid_col, box_top, mid_col, box_bottom)
                
                # ============ LEFT COLUMN - SALARY BREAKDOWN ============
                y = box_top - 0.2*inch
                
                # Calculate salary components
                monthly_salary = float(emp.get("currentSalary", 0) or 0)
                mgross = monthly_salary
                basic = mgross * 0.594  # 59.40% of Gross
                hra = basic * 0.5  # 50% of basic
                conveyance = 800
                ea_fixed = 200
                gross_70 = mgross * 0.70
                others = gross_70 - basic - hra - conveyance - ea_fixed
                if others < 0:
                    others = 0
                
                # Annual values
                basic_annual = basic * 12
                others_annual = others * 12
                gross_annual = gross_70 * 12
                
                # Reimbursements
                medical = 1250
                travelling = 3030
                entertainment = 2020
                reimb_total = medical + travelling + entertainment
                
                c.setFont("Helvetica-Bold", 8)
                c.drawString(box_left + 0.1*inch, y, "BREAK UP OF THE SALARY")
                c.drawString(mid_col - 1.5*inch, y, ": Break upto Gross of 36-50K")
                
                # Tax computation header on right
                c.drawString(mid_col + 0.1*inch, y, ": Tax Computation")
                y -= 0.25*inch
                
                c.setFont("Helvetica", 7)
                
                # Row 1: Basic
                c.drawString(box_left + 0.1*inch, y, "Basic @ 59.40 of Gross")
                c.drawRightString(2.0*inch, y, f"Rs. {basic:,.2f}")
                c.drawRightString(2.8*inch, y, f"Rs. {basic:,.2f}")
                c.drawRightString(mid_col - 0.1*inch, y, f"Rs. {basic_annual:,.2f}")
                y -= 0.18*inch
                
                # Row 2: HRA
                c.drawString(box_left + 0.1*inch, y, "HRA @ 50% of basic")
                c.drawRightString(2.0*inch, y, f"Rs. {hra:,.2f}")
                y -= 0.18*inch
                
                # Row 3: Conveyance
                c.drawString(box_left + 0.1*inch, y, "Conveyance (Fixed)")
                c.drawRightString(2.0*inch, y, f"Rs. {conveyance:,.2f}")
                y -= 0.18*inch
                
                # Row 4: E.A
                c.drawString(box_left + 0.1*inch, y, "E.A (Fixed)")
                c.drawRightString(2.0*inch, y, f"Rs. {ea_fixed:,.2f}")
                y -= 0.18*inch
                
                # Row 5: Others
                c.drawString(box_left + 0.1*inch, y, "Others (balancing)")
                c.drawRightString(2.0*inch, y, f"Rs. {others:,.2f}")
                c.drawRightString(2.8*inch, y, f"Rs. {others:,.2f}")
                c.drawRightString(mid_col - 0.1*inch, y, f"Rs. {others_annual:,.2f}")
                y -= 0.2*inch
                
                # Row 6: A Gross
                c.setFont("Helvetica-Bold", 7)
                c.drawString(box_left + 0.1*inch, y, "A  Gross (70%of Mgross)")
                c.drawRightString(2.0*inch, y, f"Rs. {gross_70:,.2f}")
                c.drawRightString(2.8*inch, y, f"Rs. {gross_70:,.2f}")
                c.drawRightString(mid_col - 0.1*inch, y, f"Rs. {gross_annual:,.2f}")
                y -= 0.25*inch
                
                # Reimbursements section
                c.setFont("Helvetica-Bold", 8)
                c.drawString(box_left + 0.1*inch, y, "Reimbursements >")
                
                # Tax computation labels on right side
                c.setFont("Helvetica", 7)
                c.drawString(mid_col + 0.1*inch, y, "Medical")
                c.drawRightString(box_right - 0.1*inch, y, "Standard Ded.")
                y -= 0.18*inch
                
                c.setFont("Helvetica", 7)
                c.drawString(box_left + 0.1*inch, y, "Medical")
                c.drawRightString(2.0*inch, y, f"Rs. {medical:,.2f}")
                c.drawString(mid_col + 0.1*inch, y, "")
                c.drawRightString(box_right - 0.1*inch, y, "Investments")
                y -= 0.18*inch
                
                c.drawString(box_left + 0.1*inch, y, "Travelling Expenses")
                c.drawRightString(2.0*inch, y, f"Rs. {travelling:,.2f}")
                y -= 0.18*inch
                
                c.drawString(box_left + 0.1*inch, y, "Entertainment")
                c.drawRightString(2.0*inch, y, f"Rs. {entertainment:,.2f}")
                y -= 0.2*inch
                
                # B Reimbursements total
                c.setFont("Helvetica-Bold", 7)
                c.drawString(box_left + 0.1*inch, y, "B  Reimbursements")
                c.drawRightString(2.0*inch, y, f"Rs. {reimb_total:,.2f}")
                y -= 0.22*inch
                
                # C = A+B Monthly Gross
                c.setFont("Helvetica-Bold", 8)
                c.drawString(box_left + 0.1*inch, y, "C = A+B  Monthly Gross")
                c.drawRightString(2.0*inch, y, f"Rs. {total_gross:,.2f}")
                
                # Taxable Amount on right
                c.drawString(mid_col + 0.1*inch, y, "Taxable Amount")
                c.drawRightString(box_right - 0.1*inch, y, f"Rs. {gross_annual:,.2f}")
                y -= 0.18*inch
                
                # Tax Slab
                c.setFont("Helvetica", 7)
                c.drawString(mid_col + 0.1*inch, y, "Tax Slab")
                c.drawRightString(box_right - 0.1*inch, y, "Rs. 40,000.00")
                y -= 0.18*inch
                
                # Tax Payable
                c.drawString(mid_col + 0.1*inch, y, "Tax Payable")
                c.drawRightString(box_right - 0.1*inch, y, "Rs. 4,000.00")
                y -= 0.25*inch
                
                # NO. OF DAYS WORKING
                c.setFont("Helvetica-Bold", 8)
                c.drawString(box_left + 0.1*inch, y, f"NO. OF DAYS WORKING")
                c.drawRightString(2.0*inch, y, f"{int(present_days)} DAYS")
                y -= 0.25*inch
                
                # ============ LIABILITIES SECTION ============
                c.setFont("Helvetica-Bold", 8)
                c.drawString(box_left + 0.1*inch, y, "Liabilities")
                y -= 0.18*inch
                
                c.setFont("Helvetica", 7)
                # P.F.
                c.drawString(box_left + 0.1*inch, y, "P.F.")
                c.drawRightString(2.0*inch, y, "NA")
                y -= 0.15*inch
                
                # E.S.I.
                esi_amount = total_gross * 0.0075 if total_gross <= 21000 else 0  # 0.75% employee contribution
                c.drawString(box_left + 0.1*inch, y, "E.S.I.")
                c.drawRightString(2.0*inch, y, f"Rs. {esi_amount:,.2f}" if esi_amount > 0 else "NA")
                y -= 0.15*inch
                
                # WF
                c.drawString(box_left + 0.1*inch, y, "WF")
                c.drawRightString(2.0*inch, y, "Rs.")
                y -= 0.15*inch
                
                # Ex-Gratia
                c.drawString(box_left + 0.1*inch, y, "Ex-Gratia")
                c.drawRightString(2.0*inch, y, "Rs.")
                y -= 0.18*inch
                
                # D Liabilities total
                total_liabilities = esi_amount if esi_amount > 0 else 0
                c.setFont("Helvetica-Bold", 7)
                c.drawString(box_left + 0.1*inch, y, "D  Liabilities")
                c.drawRightString(2.0*inch, y, f"Rs. {total_liabilities:,.2f}")
                
                # Total Tax on right
                c.drawString(mid_col + 0.1*inch, y, "Total Tax")
                c.drawRightString(box_right - 0.1*inch, y, "Rs. 18,029.60")
                y -= 0.15*inch
                
                # Ed. Cess
                c.setFont("Helvetica", 7)
                c.drawString(mid_col + 0.1*inch, y, "Ed. Cess@3%")
                c.drawRightString(box_right - 0.1*inch, y, "Rs. 540.89")
                y -= 0.15*inch
                
                # Net Tax
                c.setFont("Helvetica-Bold", 7)
                c.drawString(mid_col + 0.1*inch, y, "Net Tax")
                c.drawRightString(box_right - 0.1*inch, y, "Rs. 18,570.49")
                y -= 0.22*inch
                
                # ============ DEDUCTIONS SECTION ============
                c.setFont("Helvetica-Bold", 8)
                c.drawString(box_left + 0.1*inch, y, "Deductions")
                y -= 0.15*inch
                
                c.setFont("Helvetica", 7)
                c.drawString(box_left + 0.1*inch, y, "P.F.")
                c.drawRightString(2.0*inch, y, "NA")
                y -= 0.15*inch
                
                c.drawString(box_left + 0.1*inch, y, "E.S.I.")
                c.drawRightString(2.0*inch, y, "")
                y -= 0.15*inch
                
                c.drawString(box_left + 0.1*inch, y, "WF")
                c.drawRightString(2.0*inch, y, "")
                y -= 0.15*inch
                
                c.drawString(box_left + 0.1*inch, y, "Income Tax")
                c.drawRightString(2.0*inch, y, "")
                y -= 0.15*inch
                
                # Advance deduction
                c.drawString(box_left + 0.1*inch, y, "Advance")
                c.drawRightString(2.0*inch, y, f"Rs. {total_advance:,.2f}" if total_advance > 0 else "")
                y -= 0.18*inch
                
                # F Deductions total
                c.setFont("Helvetica-Bold", 7)
                c.drawString(box_left + 0.1*inch, y, "F  Deductions")
                c.drawRightString(2.0*inch, y, f"Rs. {total_advance:,.2f}" if total_advance > 0 else "Rs.")
                y -= 0.25*inch
                
                # ============ NET TAKE ============
                c.setFont("Helvetica-Bold", 9)
                c.drawString(box_left + 0.1*inch, y, "G = C-F  NET TAKE")
                c.drawRightString(2.5*inch, y, f"Rs. {total_net:,.2f}")
                y -= 0.22*inch
                
                # Approx Full Package
                approx_package = total_gross + total_liabilities
                c.setFont("Helvetica", 7)
                c.drawString(box_left + 0.1*inch, y, "Approx Full Package")
                c.drawRightString(2.5*inch, y, f"Rs. {approx_package:,.2f}")
                
                # ============ FOOTER ============
                c.setFont("Helvetica", 7)
                c.drawString(0.5*inch, 1.1*inch, "No Signature Section Needed — this file is ready for computer use.")
                
                # Purnabramha branding and Signature
                c.setFont("Helvetica-Bold", 10)
                c.drawRightString(width - 0.5*inch, 1.0*inch, "purnabramha")
                c.setFont("Helvetica-Bold", 9)
                c.drawRightString(width - 0.5*inch, 0.8*inch, "MANASWINI FOODS PVT. LTD.")
                c.setFont("Helvetica", 8)
                c.drawRightString(width - 0.5*inch, 0.6*inch, "Mr. Sandeep Gadhwal")
                c.drawRightString(width - 0.5*inch, 0.45*inch, "Director")
                
                c.save()
                files_created.append(filename)
                pdf_buffers.append((filename, pdf_buffer.getvalue()))
        
        if len(pdf_buffers) == 1:
            # Single PDF - return directly
            filename, content = pdf_buffers[0]
            return Response(
                content=content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
        else:
            # Multiple PDFs - create ZIP and return
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for filename, content in pdf_buffers:
                    zf.writestr(filename, content)
            
            zip_buffer.seek(0)
            zip_filename = f"Payslips_{req.targetCenter or 'ALL'}_{req.month}.zip"
            
            return Response(
                content=zip_buffer.getvalue(),
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{zip_filename}"'
                }
            )
            
    except Exception as e:
        logger.error(f"Payslip generation error: {e}")
        raise HTTPException(500, str(e))

# =======================================
# BHOJAN GURU ENDPOINTS
# =======================================

# Load recipe and description data from JSON files
def load_recipe_data():
    recipe_file = ROOT_DIR / "recipe_data.json"
    if recipe_file.exists():
        with open(recipe_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"recipes": {}, "thalis": {}, "bhojanGuru": {}}

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
        "recipes": data.get("recipes", {}),
        "thalis": data.get("thalis", {}),
        "bhojanGuru": data.get("bhojanGuru", {})
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
    display: str
    ingredients: List[str] = []
    method: List[str] = []
    category: Optional[str] = "mains"

class RecipeUpdate(BaseModel):
    display: Optional[str] = None
    ingredients: Optional[List[str]] = None
    method: Optional[List[str]] = None
    category: Optional[str] = None

def save_recipe_data(data: dict):
    """Save recipe data to JSON file"""
    recipe_file = ROOT_DIR / "recipe_data.json"
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
        "display": req.display,
        "ingredients": req.ingredients,
        "method": req.method,
        "category": req.category
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
    if req.display is not None:
        recipe["display"] = req.display
    if req.ingredients is not None:
        recipe["ingredients"] = req.ingredients
    if req.method is not None:
        recipe["method"] = req.method
    if req.category is not None:
        recipe["category"] = req.category
    
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
    """Get list of all centers"""
    centers = [
        {"code": "PB-HSR", "name": "Purnabramha HSR - Bangalore"},
        {"code": "PB-TH", "name": "Purnabramha Thane - Mumbai"},
        {"code": "PB-SN", "name": "Purnabramha Sambhajinagar"},
        {"code": "PB-DV", "name": "Purnabramha Dombivli - Mumbai"},
        {"code": "PB-HW", "name": "Purnabramha Hinjawadi - Pune"},
        {"code": "PB-KN", "name": "Purnabramha Kharadi Nyati - Pune"},
        {"code": "PB-KAL", "name": "Purnabramha Kalyan"},
        {"code": "PB-PERTH", "name": "Purnabramha Perth - Australia"},
        {"code": "PB-MGT", "name": "Purnabramha Management (HQ)"},
    ]
    return {"centers": centers}

# Include router
app.include_router(api_router)

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
