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
# TRANSFER-AWARE HELPERS
# =======================================

async def get_transfer_status_for_center(center: str, date: str):
    """Get employees transferred in/out of this center on a given date"""
    center = center.upper()
    
    # Employees transferred INTO this center (active on this date)
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
    
    # Employees transferred OUT of this center (active on this date)
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
    
    in_names = {t["employee_name"].upper() for t in transferred_in}
    out_names = {t["employee_name"].upper() for t in transferred_out}
    
    # Build details map
    in_details = {}
    for t in transferred_in:
        name = t["employee_name"].upper()
        in_details[name] = {
            "from_center": t["from_center"],
            "transfer_type": t["transfer_type"],
            "start_date": t["start_date"],
            "end_date": t.get("end_date", "")
        }
    
    out_details = {}
    for t in transferred_out:
        name = t["employee_name"].upper()
        out_details[name] = {
            "to_center": t["to_center"],
            "transfer_type": t["transfer_type"],
            "start_date": t["start_date"],
            "end_date": t.get("end_date", "")
        }
    
    return in_names, out_names, in_details, out_details

# =======================================
# ATTENDANCE ENDPOINTS
# =======================================

@router.post("/bulk_attendance")
async def bulk_attendance(req: BulkAttendance):
    """Save daily attendance for multiple employees (transfer-aware)"""
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
    
    center = req.center.upper()
    
    # Get transfer context for duplicate prevention
    in_names, out_names, _, _ = await get_transfer_status_for_center(center, req.date)
    
    inserted = 0
    updated = 0
    skipped = 0
    timestamp = datetime.now(timezone.utc).isoformat()
    
    for row in req.rows:
        emp_name = row.employeeName.upper()
        
        # Prevent marking attendance for transferred-out employees at source center
        if emp_name in out_names:
            skipped += 1
            continue
        
        # For transferred-in employees, check they don't already have attendance at source
        # (duplicate prevention - the destination center's attendance takes priority)
        
        doc = {
            "date": req.date,
            "center": center,
            "employeeName": emp_name,
            "designation": row.designation,
            "status": row.status.upper(),
            "notes": row.notes or "",
            "is_transferred_in": emp_name in in_names,
            "submittedByMobile": req.submittedBy or session.get("mobile", ""),
            "timestamp": timestamp
        }
        
        # Upsert
        result = await db.attendance.update_one(
            {"date": req.date, "center": center, "employeeName": emp_name},
            {"$set": doc},
            upsert=True
        )
        
        if result.upserted_id:
            inserted += 1
        else:
            updated += 1
    
    return {"success": True, "inserted": inserted, "updated": updated, "skipped_transferred_out": skipped}

@router.post("/attendance_by_date")
async def attendance_by_date(req: DateRequest):
    """Get attendance for a specific date (transfer-aware)"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    center = req.center.upper()
    
    rows = await db.attendance.find(
        {"date": req.date, "center": center},
        {"_id": 0}
    ).to_list(1000)
    
    # Get transfer info for this date
    in_names, out_names, in_details, out_details = await get_transfer_status_for_center(center, req.date)
    
    # Tag each row with transfer status
    for row in rows:
        emp_name = row.get("employeeName", "").upper()
        if emp_name in in_names:
            row["transfer_tag"] = "TRANSFERRED_IN"
            row["transfer_info"] = in_details.get(emp_name, {})
        elif emp_name in out_names:
            row["transfer_tag"] = "TRANSFERRED_OUT"
            row["transfer_info"] = out_details.get(emp_name, {})
        else:
            row["transfer_tag"] = "HOME"
    
    return {"rows": rows, "transferred_in_names": list(in_names), "transferred_out_names": list(out_names)}

@router.post("/attendance_month")
async def attendance_month(req: MonthRequest):
    """Get monthly attendance grid (transfer-aware)"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    center = req.center.upper()
    year, month = map(int, req.month.split("-"))
    dim = days_in_month(year, month)
    
    # Get home employees for center
    employees = await db.employees.find(
        {"center": center},
        {"_id": 0}
    ).sort("name", 1).to_list(1000)
    
    # Get transfer status for each day of the month to build a comprehensive picture
    # We use the last day of the month as a representative check, but also check first day
    start_date = f"{req.month}-01"
    end_date = f"{req.month}-{dim:02d}"
    
    # Get ALL active transfers overlapping this month for this center
    transfers_in = await db.transfer_requests.find({
        "to_center": center,
        "status": {"$in": ["ACCEPTED", "COMPLETED"]},
        "start_date": {"$lte": end_date},
        "$or": [
            {"end_date": {"$gte": start_date}},
            {"end_date": None},
            {"end_date": ""},
            {"transfer_type": "PERMANENT"}
        ]
    }, {"_id": 0}).to_list(500)
    
    transfers_out = await db.transfer_requests.find({
        "from_center": center,
        "status": {"$in": ["ACCEPTED", "COMPLETED"]},
        "start_date": {"$lte": end_date},
        "$or": [
            {"end_date": {"$gte": start_date}},
            {"end_date": None},
            {"end_date": ""},
            {"transfer_type": "PERMANENT"}
        ]
    }, {"_id": 0}).to_list(500)
    
    # Build transferred-in employee details (we need to fetch their info)
    transferred_in_emps = []
    for t in transfers_in:
        emp_name = t["employee_name"].upper()
        # Check if already in our employee list
        if not any(e.get("name", "").upper() == emp_name for e in employees):
            # Fetch from source center
            emp = await db.employees.find_one(
                {"name": emp_name},
                {"_id": 0}
            )
            if emp:
                transferred_in_emps.append({
                    "name": emp_name,
                    "designation": emp.get("designation", ""),
                    "transfer_tag": "TRANSFERRED_IN",
                    "from_center": t["from_center"],
                    "transfer_type": t["transfer_type"],
                    "transfer_start": t["start_date"],
                    "transfer_end": t.get("end_date", "")
                })
    
    # Build out names set and details
    out_names_set = {t["employee_name"].upper() for t in transfers_out}
    out_details_map = {}
    for t in transfers_out:
        out_details_map[t["employee_name"].upper()] = {
            "to_center": t["to_center"],
            "transfer_type": t["transfer_type"],
            "transfer_start": t["start_date"],
            "transfer_end": t.get("end_date", "")
        }
    
    # Build transferred-out employee details for employees no longer in this center
    # (e.g. PERMANENT transfers change the employee's center field)
    transferred_out_emps = []
    current_emp_names = {e.get("name", "").upper() for e in employees}
    for t in transfers_out:
        emp_name = t["employee_name"].upper()
        if emp_name not in current_emp_names:
            # Employee's center was already changed, fetch their current record
            emp = await db.employees.find_one({"name": emp_name}, {"_id": 0})
            if emp:
                transferred_out_emps.append({
                    "name": emp_name,
                    "designation": emp.get("designation", ""),
                    "transfer_tag": "TRANSFERRED_OUT",
                    "to_center": t["to_center"],
                    "transfer_type": t["transfer_type"],
                    "transfer_start": t["start_date"],
                    "transfer_end": t.get("end_date", "")
                })
    
    # Get all attendance for month (include transferred-in AND transferred-out employees)
    attendance = await db.attendance.find(
        {
            "center": center,
            "date": {"$gte": start_date, "$lte": end_date}
        },
        {"_id": 0}
    ).to_list(10000)
    
    # Build lookup
    att_map = {}
    for a in attendance:
        key = f"{a['employeeName']}_{a['date']}"
        att_map[key] = a.get("status", "")
    
    # Build grid - home employees first
    grid = []
    for emp in employees:
        emp_name = emp.get("name", "").upper()
        
        # Determine transfer tag
        if emp_name in out_names_set:
            tag = "TRANSFERRED_OUT"
            transfer_info = out_details_map.get(emp_name, {})
        else:
            tag = "HOME"
            transfer_info = {}
        
        days = []
        for d in range(1, dim + 1):
            date_str = f"{req.month}-{d:02d}"
            key = f"{emp_name}_{date_str}"
            status = att_map.get(key, "")
            days.append({"day": d, "status": status})
        
        grid.append({
            "employeeName": emp_name,
            "designation": emp.get("designation", ""),
            "transfer_tag": tag,
            "transfer_info": transfer_info,
            "days": days
        })
    
    # Add transferred-out employees who are no longer in this center's employee list
    for t_emp in transferred_out_emps:
        emp_name = t_emp["name"]
        days = []
        for d in range(1, dim + 1):
            date_str = f"{req.month}-{d:02d}"
            key = f"{emp_name}_{date_str}"
            status = att_map.get(key, "")
            days.append({"day": d, "status": status})
        
        grid.append({
            "employeeName": emp_name,
            "designation": t_emp.get("designation", ""),
            "transfer_tag": "TRANSFERRED_OUT",
            "transfer_info": {
                "to_center": t_emp["to_center"],
                "transfer_type": t_emp["transfer_type"],
                "transfer_start": t_emp["transfer_start"],
                "transfer_end": t_emp["transfer_end"]
            },
            "days": days
        })
    
    # Add transferred-in employees
    for t_emp in transferred_in_emps:
        emp_name = t_emp["name"]
        days = []
        for d in range(1, dim + 1):
            date_str = f"{req.month}-{d:02d}"
            key = f"{emp_name}_{date_str}"
            status = att_map.get(key, "")
            days.append({"day": d, "status": status})
        
        grid.append({
            "employeeName": emp_name,
            "designation": t_emp.get("designation", ""),
            "transfer_tag": "TRANSFERRED_IN",
            "transfer_info": {
                "from_center": t_emp["from_center"],
                "transfer_type": t_emp["transfer_type"],
                "transfer_start": t_emp["transfer_start"],
                "transfer_end": t_emp["transfer_end"]
            },
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
