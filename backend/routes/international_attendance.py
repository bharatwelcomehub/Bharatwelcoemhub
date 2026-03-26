# =======================================
# International Attendance & Payroll Routes
# Perth / International Centers (Hours-based)
# =======================================

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import logging
import io
import csv

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/international-attendance", tags=["International Attendance"])

# Database reference
db = None
verify_token = None

def set_db(database):
    global db
    db = database

def set_verify_token(func):
    global verify_token
    verify_token = func

# =======================================
# CONSTANTS
# =======================================

MAX_HOURS_PER_DAY = 16
INTERNATIONAL_CENTERS = ["PB-PERTH", "PB-SYDNEY", "PB-MELBOURNE", "PB-AUCKLAND", "PB-DUBAI", "PB-LONDON"]
CASUAL_CATEGORIES = ["CASUAL-KITCHEN", "CASUAL-SERVICE", "CASUAL"]

# =======================================
# PYDANTIC MODELS
# =======================================

class TokenRequest(BaseModel):
    token: str

class CenterRequest(BaseModel):
    token: str
    center: str

class WeekAttendanceRequest(BaseModel):
    token: str
    center: str
    year: int
    month: int
    week: int  # 1-5

class AttendanceEntry(BaseModel):
    employee_id: str
    hours: Dict[str, float]  # {"mon": 8, "tue": 7.5, "wed": 0, ...}

class SaveAttendanceRequest(BaseModel):
    token: str
    center: str
    year: int
    month: int
    week: int
    entries: List[AttendanceEntry]

class MonthlyReportRequest(BaseModel):
    token: str
    center: str
    year: int
    month: int

# =======================================
# HELPER FUNCTIONS
# =======================================

def normalize_center_code(center: str) -> str:
    """Normalize center code by stripping trailing hyphens/spaces.
    In production, centers collection may have 'PB-PERTH-' while employees have 'PB-PERTH'."""
    return center.upper().rstrip("- ")

def center_code_variants(center: str) -> list:
    """Return both normalized and original variants for querying across collections."""
    original = center.upper().strip()
    normalized = original.rstrip("- ")
    variants = [normalized]
    if original != normalized:
        variants.append(original)
    # Also try with trailing hyphen in case employees have it
    if not normalized.endswith("-"):
        variants.append(normalized + "-")
    return list(set(variants))

def get_week_dates(year: int, month: int, week: int) -> List[str]:
    """Get dates for a specific week of a month (Mon-Sun)"""
    from calendar import monthrange
    
    # Get first day of month
    first_day = datetime(year, month, 1)
    
    # Find first Monday of the month (or use 1st if it's Mon)
    days_until_monday = (7 - first_day.weekday()) % 7
    if days_until_monday == 0 and first_day.weekday() != 0:
        days_until_monday = 7
    
    first_monday = first_day + timedelta(days=days_until_monday if first_day.weekday() != 0 else 0)
    
    # If week 1 and month doesn't start on Monday, include days from start
    if week == 1 and first_day.weekday() != 0:
        # Week 1 starts from 1st of month
        week_start = first_day
    else:
        # Calculate start of requested week
        week_start = first_monday + timedelta(weeks=week - 1)
    
    # Generate 7 days (Mon-Sun)
    dates = []
    _, last_day = monthrange(year, month)
    
    for i in range(7):
        date = week_start + timedelta(days=i)
        # Only include dates within the month
        if date.month == month and date.day <= last_day:
            dates.append(date.strftime("%Y-%m-%d"))
        else:
            dates.append(None)  # Outside month boundary
    
    return dates

def get_week_number_from_date(date_str: str) -> int:
    """Calculate which week of the month a date belongs to"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    day = date.day
    return (day - 1) // 7 + 1

def calculate_weeks_in_month(year: int, month: int) -> int:
    """Calculate number of weeks in a month"""
    from calendar import monthrange
    _, last_day = monthrange(year, month)
    return (last_day - 1) // 7 + 1

# =======================================
# ENDPOINTS
# =======================================

@router.get("/centers")
async def get_international_centers(token: str):
    """Get list of all centers (consistent with other screens)"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Get ALL centers from DB - same source as management and sales screens
    centers = await db.centers.find(
        {},
        {"_id": 0, "code": 1, "name": 1, "country": 1, "city": 1}
    ).sort("code", 1).to_list(100)
    
    return {"success": True, "centers": centers}

@router.post("/employees")
async def get_international_employees(req: CenterRequest):
    """Get all employees for an international center"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Query ALL employees at the specified center (handle PB-PERTH vs PB-PERTH- mismatch)
    variants = center_code_variants(req.center)
    query = {
        "center": {"$in": variants}
    }
    
    # Include _id so we can generate a unique key for employees without employee_id
    employees_raw = await db.employees.find(query).sort("name", 1).to_list(500)
    
    employees = []
    for emp in employees_raw:
        # Generate a reliable unique ID: prefer employee_id, fallback to _id string
        emp_id = emp.get("employee_id") or emp.get("id") or emp.get("emp_id")
        if not emp_id:
            # Use MongoDB _id as fallback unique identifier
            emp_id = str(emp.get("_id", ""))
        
        # Category: prefer 'category', fallback to 'designation'
        category = emp.get("category") or emp.get("designation") or "STAFF"
        
        # Hourly rate: prefer 'hourly_rate', fallback to 0 (user can set it via edit button)
        hourly_rate = emp.get("hourly_rate")
        if hourly_rate is not None and hourly_rate != "":
            hourly_rate = float(hourly_rate)
        else:
            hourly_rate = 0.0
        
        # Build clean employee record (exclude _id for JSON serialization)
        clean_emp = {
            "employee_id": emp_id,
            "name": emp.get("name", "Unknown"),
            "center": emp.get("center", ""),
            "category": category,
            "role": emp.get("role") or emp.get("designation") or "",
            "hourly_rate": hourly_rate,
            "currentSalary": emp.get("currentSalary", 0),
            "mobile": emp.get("mobile", ""),
        }
        employees.append(clean_emp)
    
    return {"success": True, "employees": employees, "count": len(employees)}

@router.post("/week-data")
async def get_week_attendance(req: WeekAttendanceRequest):
    """Get attendance data for a specific week"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Get week dates
    week_dates = get_week_dates(req.year, req.month, req.week)
    valid_dates = [d for d in week_dates if d is not None]
    
    # Get employees
    employees_result = await get_international_employees(CenterRequest(token=req.token, center=req.center))
    employees = employees_result["employees"]
    
    # Get attendance records for these dates (use variants for center code mismatch)
    variants = center_code_variants(req.center)
    attendance_records = await db.international_attendance.find({
        "center": {"$in": variants},
        "date": {"$in": valid_dates}
    }, {"_id": 0}).to_list(5000)
    
    # Create lookup map
    attendance_map = {}
    for record in attendance_records:
        key = f"{record['employee_id']}_{record['date']}"
        attendance_map[key] = record
    
    # Build response data
    day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    employee_data = []
    
    for emp in employees:
        emp_id = emp.get("employee_id")  # Already guaranteed by get_international_employees
        hourly_rate = float(emp.get("hourly_rate", 0) or 0)
        
        hours = {}
        total_hours = 0
        
        for i, day in enumerate(day_names):
            date = week_dates[i]
            if date:
                key = f"{emp_id}_{date}"
                record = attendance_map.get(key)
                hours[day] = record["hours_worked"] if record else 0
                total_hours += hours[day]
            else:
                hours[day] = None  # Date outside month
        
        weekly_salary = total_hours * hourly_rate
        
        employee_data.append({
            "employee_id": emp_id,
            "employee_name": emp.get("name", "Unknown"),
            "category": emp.get("category", "STAFF"),
            "role": emp.get("role", ""),
            "hourly_rate": hourly_rate,
            "hours": hours,
            "total_hours": round(total_hours, 2),
            "weekly_salary": round(weekly_salary, 2)
        })
    
    # Calculate summary
    total_staff = len(employee_data)
    total_hours = sum(e["total_hours"] for e in employee_data)
    total_payroll = sum(e["weekly_salary"] for e in employee_data)
    
    return {
        "success": True,
        "center": req.center,
        "year": req.year,
        "month": req.month,
        "week": req.week,
        "week_dates": week_dates,
        "day_names": day_names,
        "employees": employee_data,
        "summary": {
            "total_staff": total_staff,
            "total_hours": round(total_hours, 2),
            "total_payroll": round(total_payroll, 2)
        }
    }

@router.post("/save")
async def save_attendance(req: SaveAttendanceRequest):
    """Save attendance entries for a week"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Get week dates
    week_dates = get_week_dates(req.year, req.month, req.week)
    day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    
    # Use normalized center code for saving (strip trailing hyphens)
    save_center = normalize_center_code(req.center)
    search_variants = center_code_variants(req.center)
    
    saved_count = 0
    warnings = []
    
    for entry in req.entries:
        for i, day in enumerate(day_names):
            date = week_dates[i]
            if not date:
                continue
            
            hours = entry.hours.get(day, 0)
            if hours is None:
                continue
            
            hours = float(hours)
            
            # Validation
            if hours < 0:
                warnings.append(f"{entry.employee_id}: Negative hours not allowed for {day}")
                hours = 0
            
            if hours > MAX_HOURS_PER_DAY:
                warnings.append(f"{entry.employee_id}: Hours exceed {MAX_HOURS_PER_DAY} for {day}")
            
            # Upsert record - search with variants, save with normalized code
            await db.international_attendance.update_one(
                {
                    "employee_id": entry.employee_id,
                    "center": {"$in": search_variants},
                    "date": date
                },
                {
                    "$set": {
                        "employee_id": entry.employee_id,
                        "center": save_center,
                        "date": date,
                        "hours_worked": hours,
                        "week_number": req.week,
                        "month": req.month,
                        "year": req.year,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "updated_by": session.get("managerName", "Unknown")
                    },
                    "$setOnInsert": {
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "created_by": session.get("managerName", "Unknown")
                    }
                },
                upsert=True
            )
            saved_count += 1
    
    logger.info(f"International attendance saved: {req.center} Week {req.week}/{req.month}/{req.year} - {saved_count} records by {session.get('managerName')}")
    
    return {
        "success": True,
        "message": "Attendance saved successfully",
        "saved_count": saved_count,
        "warnings": warnings if warnings else None
    }

@router.post("/monthly-report")
async def get_monthly_report(req: MonthlyReportRequest):
    """Get monthly payroll report"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Get all attendance for the month
    from calendar import monthrange
    _, last_day = monthrange(req.year, req.month)
    
    start_date = f"{req.year}-{req.month:02d}-01"
    end_date = f"{req.year}-{req.month:02d}-{last_day:02d}"
    
    variants = center_code_variants(req.center)
    attendance_records = await db.international_attendance.find({
        "center": {"$in": variants},
        "date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0}).to_list(10000)
    
    # Get employees - keyed by employee_id (already guaranteed unique)
    employees_result = await get_international_employees(CenterRequest(token=req.token, center=req.center))
    employees = {
        emp.get("employee_id"): emp 
        for emp in employees_result["employees"]
    }
    
    # Group by employee and week
    weeks_in_month = calculate_weeks_in_month(req.year, req.month)
    employee_data = {}
    
    for record in attendance_records:
        emp_id = record["employee_id"]
        week = record.get("week_number") or get_week_number_from_date(record["date"])
        hours = record.get("hours_worked", 0)
        
        if emp_id not in employee_data:
            emp = employees.get(emp_id, {})
            employee_data[emp_id] = {
                "employee_id": emp_id,
                "employee_name": emp.get("name", "Unknown"),
                "category": emp.get("category", "STAFF"),
                "hourly_rate": float(emp.get("hourly_rate", 0) or 0),
                "weeks": {i: 0 for i in range(1, weeks_in_month + 1)},
                "total_hours": 0,
                "total_salary": 0
            }
        
        if 1 <= week <= weeks_in_month:
            employee_data[emp_id]["weeks"][week] += hours
            employee_data[emp_id]["total_hours"] += hours
    
    # Calculate total salary
    for emp_id, data in employee_data.items():
        data["total_salary"] = round(data["total_hours"] * data["hourly_rate"], 2)
        data["total_hours"] = round(data["total_hours"], 2)
        # Round week hours
        for w in data["weeks"]:
            data["weeks"][w] = round(data["weeks"][w], 2)
    
    # Sort by name
    report_data = sorted(employee_data.values(), key=lambda x: x["employee_name"])
    
    # Summary
    total_staff = len(report_data)
    total_hours = sum(e["total_hours"] for e in report_data)
    total_payroll = sum(e["total_salary"] for e in report_data)
    
    return {
        "success": True,
        "center": req.center,
        "year": req.year,
        "month": req.month,
        "month_name": datetime(req.year, req.month, 1).strftime("%B"),
        "weeks_in_month": weeks_in_month,
        "employees": report_data,
        "summary": {
            "total_staff": total_staff,
            "total_hours": round(total_hours, 2),
            "total_payroll": round(total_payroll, 2)
        }
    }

@router.post("/export/weekly-excel")
async def export_weekly_excel(req: WeekAttendanceRequest):
    """Export weekly payroll as CSV"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Get week data
    week_data = await get_week_attendance(req)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    month_name = datetime(req.year, req.month, 1).strftime("%B")
    writer.writerow([f"Weekly Payroll Report - {req.center}"])
    writer.writerow([f"Month: {month_name} {req.year}, Week {req.week}"])
    writer.writerow([])
    
    # Column headers
    headers = ["Employee Name", "Category", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", 
               "Total Hours", "Hourly Rate", "Weekly Salary"]
    writer.writerow(headers)
    
    # Data rows
    for emp in week_data["employees"]:
        row = [
            emp["employee_name"],
            emp["category"],
            emp["hours"].get("mon", 0),
            emp["hours"].get("tue", 0),
            emp["hours"].get("wed", 0),
            emp["hours"].get("thu", 0),
            emp["hours"].get("fri", 0),
            emp["hours"].get("sat", 0),
            emp["hours"].get("sun", 0),
            emp["total_hours"],
            f"${emp['hourly_rate']:.2f}",
            f"${emp['weekly_salary']:.2f}"
        ]
        writer.writerow(row)
    
    # Summary
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Total Staff", week_data["summary"]["total_staff"]])
    writer.writerow(["Total Hours", week_data["summary"]["total_hours"]])
    writer.writerow(["Total Payroll", f"${week_data['summary']['total_payroll']:.2f}"])
    
    output.seek(0)
    
    filename = f"{req.center}_Weekly_Payroll_Week{req.week}_{month_name}_{req.year}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.post("/export/monthly-excel")
async def export_monthly_excel(req: MonthlyReportRequest):
    """Export monthly payroll as CSV"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Get monthly data
    monthly_data = await get_monthly_report(req)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([f"Monthly Payroll Report - {req.center}"])
    writer.writerow([f"Month: {monthly_data['month_name']} {req.year}"])
    writer.writerow([])
    
    # Column headers
    week_headers = [f"Week {i}" for i in range(1, monthly_data["weeks_in_month"] + 1)]
    headers = ["Employee Name", "Category"] + week_headers + ["Total Hours", "Hourly Rate", "Total Salary"]
    writer.writerow(headers)
    
    # Data rows
    for emp in monthly_data["employees"]:
        row = [emp["employee_name"], emp["category"]]
        for w in range(1, monthly_data["weeks_in_month"] + 1):
            row.append(emp["weeks"].get(w, 0))
        row.extend([emp["total_hours"], f"${emp['hourly_rate']:.2f}", f"${emp['total_salary']:.2f}"])
        writer.writerow(row)
    
    # Summary
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Total Staff", monthly_data["summary"]["total_staff"]])
    writer.writerow(["Total Hours", monthly_data["summary"]["total_hours"]])
    writer.writerow(["Total Payroll", f"${monthly_data['summary']['total_payroll']:.2f}"])
    
    output.seek(0)
    
    filename = f"{req.center}_Monthly_Payroll_{monthly_data['month_name']}_{req.year}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.post("/export/attendance-sheet")
async def export_attendance_sheet(req: MonthlyReportRequest):
    """Export full attendance sheet for the month"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    from calendar import monthrange
    _, last_day = monthrange(req.year, req.month)
    
    # Get all attendance for the month
    start_date = f"{req.year}-{req.month:02d}-01"
    end_date = f"{req.year}-{req.month:02d}-{last_day:02d}"
    
    variants = center_code_variants(req.center)
    attendance_records = await db.international_attendance.find({
        "center": {"$in": variants},
        "date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0}).to_list(10000)
    
    # Get employees
    employees_result = await get_international_employees(CenterRequest(token=req.token, center=req.center))
    employees = employees_result["employees"]
    
    # Create attendance map
    attendance_map = {}
    for record in attendance_records:
        key = f"{record['employee_id']}_{record['date']}"
        attendance_map[key] = record.get("hours_worked", 0)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    month_name = datetime(req.year, req.month, 1).strftime("%B")
    writer.writerow([f"Attendance Sheet - {req.center}"])
    writer.writerow([f"Month: {month_name} {req.year}"])
    writer.writerow([])
    
    # Date headers
    dates = [f"{req.year}-{req.month:02d}-{d:02d}" for d in range(1, last_day + 1)]
    day_headers = [datetime.strptime(d, "%Y-%m-%d").strftime("%d %a") for d in dates]
    headers = ["Employee", "Category", "Rate"] + day_headers + ["Total Hrs", "Total Pay"]
    writer.writerow(headers)
    
    # Data
    for emp in employees:
        emp_id = emp.get("employee_id") or emp.get("id")
        hourly_rate = float(emp.get("hourly_rate", 0) or 0)
        
        row = [emp.get("name", "Unknown"), emp.get("category", "CASUAL"), f"${hourly_rate:.2f}"]
        total_hours = 0
        
        for date in dates:
            key = f"{emp_id}_{date}"
            hours = attendance_map.get(key, 0)
            row.append(hours if hours else "")
            total_hours += hours
        
        row.append(total_hours)
        row.append(f"${total_hours * hourly_rate:.2f}")
        writer.writerow(row)
    
    output.seek(0)
    filename = f"{req.center}_Attendance_{month_name}_{req.year}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

class UpdateRateRequest(BaseModel):
    token: str
    center: str
    employee_id: str
    new_rate: float

@router.post("/update-rate")
async def update_hourly_rate(req: UpdateRateRequest):
    """Update hourly rate for an employee"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Only MGT or same center manager can update rates
    user_center = session.get("center", "")
    normalized_req_center = normalize_center_code(req.center)
    normalized_user_center = normalize_center_code(user_center)
    if normalized_user_center != "PB-MGT" and normalized_user_center != normalized_req_center:
        raise HTTPException(403, "Not authorized to update rates for this center")
    
    if req.new_rate < 0:
        raise HTTPException(400, "Hourly rate cannot be negative")
    
    # Try multiple ID fields and center variants since employee docs may use different keys
    variants = center_code_variants(req.center)
    
    # First try employee_id field
    result = await db.employees.update_one(
        {"employee_id": req.employee_id, "center": {"$in": variants}},
        {"$set": {"hourly_rate": req.new_rate, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        # Try 'id' field
        result = await db.employees.update_one(
            {"id": req.employee_id, "center": {"$in": variants}},
            {"$set": {"hourly_rate": req.new_rate, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    if result.modified_count == 0:
        # Try MongoDB _id (employee_id might be a stringified ObjectId)
        from bson import ObjectId
        try:
            oid = ObjectId(req.employee_id)
            result = await db.employees.update_one(
                {"_id": oid},
                {"$set": {"hourly_rate": req.new_rate, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
        except Exception:
            pass
    
    if result.modified_count == 0:
        # Check if employee exists but rate is same
        from bson import ObjectId as OID2
        or_conditions = [
            {"employee_id": req.employee_id, "center": {"$in": variants}},
            {"id": req.employee_id, "center": {"$in": variants}}
        ]
        try:
            or_conditions.append({"_id": OID2(req.employee_id)})
        except Exception:
            pass
        
        emp = await db.employees.find_one(
            {"$or": or_conditions},
            {"_id": 0, "hourly_rate": 1}
        )
        if emp and float(emp.get("hourly_rate", 0) or 0) == req.new_rate:
            return {"success": True, "message": f"Rate already set to ${req.new_rate:.2f}"}
        if not emp:
            raise HTTPException(404, "Employee not found")
    
    logger.info(f"Hourly rate updated: {req.employee_id} at {req.center} -> ${req.new_rate:.2f} by {session.get('managerName')}")
    
    return {"success": True, "message": f"Hourly rate updated to ${req.new_rate:.2f}"}
