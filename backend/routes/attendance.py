# =======================================
# Attendance Routes
# Attendance & Advances Management
# =======================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import calendar
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Attendance"])

# Database reference (will be set from main server)
db = None

def set_db(database):
    global db
    db = database

# Token verification function (will be set from main server)
verify_token = None

def set_verify_token(func):
    global verify_token
    verify_token = func

# =======================================
# PYDANTIC MODELS
# =======================================

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

# =======================================
# HELPER FUNCTIONS
# =======================================

def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]

async def is_attendance_locked(date: str) -> dict:
    """Check if attendance is locked for a given date's month"""
    month = date[:7]  # Extract YYYY-MM
    lock = await db.attendance_locks.find_one({"month": month}, {"_id": 0})
    if lock and lock.get("locked"):
        return {"locked": True, "month": month, "locked_by": lock.get("locked_by", "Admin")}
    return {"locked": False}

# =======================================
# ATTENDANCE ENDPOINTS
# =======================================

@router.post("/bulk_attendance")
async def bulk_attendance(req: BulkAttendance):
    """Save daily attendance for multiple employees"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Check attendance lock FIRST
    att_lock = await is_attendance_locked(req.date)
    if att_lock["locked"]:
        raise HTTPException(400, f"Attendance is locked for {att_lock['month']}. Contact Admin to unlock.")
    
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

@router.post("/attendance_by_date")
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

@router.post("/attendance_month")
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

@router.post("/bulk_attendance_month")
async def bulk_attendance_month(req: BulkMonthlyAttendance):
    """Save full month attendance"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Check attendance lock FIRST
    att_lock = await db.attendance_locks.find_one({"month": req.month}, {"_id": 0})
    if att_lock and att_lock.get("locked"):
        raise HTTPException(400, f"Attendance is locked for {req.month}. Contact Admin to unlock.")
    
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

@router.post("/bulk_advances")
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

@router.post("/advances_by_date")
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

@router.post("/advances_by_month")
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
