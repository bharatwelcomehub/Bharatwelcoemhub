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
# International centers are loaded from DB at runtime based on is_india_center field
async def fetch_international_center_codes(db_ref):
    """Fetch international center codes from DB"""
    centers = await db_ref.centers.find({"is_india_center": False, "active": {"$ne": False}}, {"_id": 0, "code": 1}).to_list(100)
    return [c["code"] for c in centers if c.get("code")]

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
    """Normalize center code by stripping trailing hyphens/spaces."""
    return center.upper().rstrip("- ")

def center_code_variants(center: str) -> list:
    """Return both normalized and original variants for querying across collections."""
    original = center.upper().strip()
    normalized = original.rstrip("- ")
    variants = set([normalized])
    if original != normalized:
        variants.add(original)
    if not normalized.endswith("-"):
        variants.add(normalized + "-")
    # Add PB- prefix variant if not present
    if not normalized.startswith("PB-"):
        variants.add("PB-" + normalized)
    # Add variant without PB- prefix
    if normalized.startswith("PB-"):
        variants.add(normalized[3:])
    return list(variants)

async def check_international_access(session: dict, requested_center: str = None) -> dict:
    """Verify user has access to international attendance.
    Returns: {"allowed": bool, "is_admin": bool, "user_center": str, "error": str}
    """
    user_center = normalize_center_code(session.get("center", ""))
    is_super_admin = session.get("is_super_admin", False)
    is_admin = session.get("is_admin", False)
    
    if is_super_admin or is_admin:
        return {"allowed": True, "is_admin": True, "user_center": user_center}
    
    # Check if user's center is international
    user_center_doc = await db.centers.find_one(
        {"code": {"$in": center_code_variants(user_center)}},
        {"_id": 0, "code": 1, "is_india_center": 1}
    )
    
    if not user_center_doc:
        return {"allowed": False, "is_admin": False, "user_center": user_center, "error": "Center not found"}
    
    if user_center_doc.get("is_india_center", True):
        return {"allowed": False, "is_admin": False, "user_center": user_center, "error": "International Attendance not available for India centers"}
    
    # International center manager: can only access own center
    if requested_center:
        req_normalized = normalize_center_code(requested_center)
        if req_normalized != normalize_center_code(user_center_doc.get("code", "")):
            return {"allowed": False, "is_admin": False, "user_center": user_center, "error": "You can only access your own center's attendance"}
    
    return {"allowed": True, "is_admin": False, "user_center": user_center_doc.get("code", user_center)}

def get_week_dates(year: int, month: int, week: int) -> List[str]:
    """Get dates for a specific week of a month (Mon-Sun).
    Week boundaries: Week 1 = 1st-6th, Week 2 = 7th-13th, Week 3 = 14th-20th, etc.
    Each week slot always has 7 entries (Mon-Sun) for the UI grid,
    with None for dates outside the month.
    """
    from calendar import monthrange
    _, last_day = monthrange(year, month)
    
    # Define week boundaries (day ranges)
    week_boundaries = [
        (1, 6),    # Week 1: 1st to 6th
        (7, 13),   # Week 2: 7th to 13th
        (14, 20),  # Week 3: 14th to 20th
        (21, 27),  # Week 4: 21st to 27th
        (28, last_day),  # Week 5: 28th to end
    ]
    
    if week < 1 or week > len(week_boundaries):
        return [None] * 7
    
    start_day, end_day = week_boundaries[week - 1]
    end_day = min(end_day, last_day)
    
    # Find what day of the week the start_day falls on
    start_date = datetime(year, month, start_day)
    start_weekday = start_date.weekday()  # 0=Mon, 6=Sun
    
    # Build 7-slot array aligned to Mon-Sun
    dates = [None] * 7
    for day in range(start_day, end_day + 1):
        dt = datetime(year, month, day)
        weekday_idx = dt.weekday()  # 0=Mon, 6=Sun
        dates[weekday_idx] = dt.strftime("%Y-%m-%d")
    
    return dates

def get_week_number_from_date(date_str: str) -> int:
    """Calculate which week of the month a date belongs to.
    Week 1 = 1st-6th, Week 2 = 7th-13th, etc.
    """
    date = datetime.strptime(date_str, "%Y-%m-%d")
    day = date.day
    if day <= 6:
        return 1
    elif day <= 13:
        return 2
    elif day <= 20:
        return 3
    elif day <= 27:
        return 4
    else:
        return 5

def calculate_weeks_in_month(year: int, month: int) -> int:
    """Calculate number of weeks in a month using our week boundary system."""
    from calendar import monthrange
    _, last_day = monthrange(year, month)
    if last_day <= 6:
        return 1
    elif last_day <= 13:
        return 2
    elif last_day <= 20:
        return 3
    elif last_day <= 27:
        return 4
    else:
        return 5

def get_week_label(year: int, month: int, week: int) -> str:
    """Get a human-readable label for a week, e.g. '1st - 6th Apr'"""
    from calendar import monthrange
    _, last_day = monthrange(year, month)
    boundaries = [(1,6),(7,13),(14,20),(21,27),(28,last_day)]
    if week < 1 or week > len(boundaries):
        return f"Week {week}"
    s, e = boundaries[week - 1]
    e = min(e, last_day)
    month_abbr = datetime(year, month, 1).strftime("%b")
    
    def ordinal(n):
        if 11 <= n <= 13:
            return f"{n}th"
        return f"{n}{['th','st','nd','rd','th','th','th','th','th','th'][n%10]}"
    
    return f"{ordinal(s)} - {ordinal(e)} {month_abbr}"


def get_week_ranges(year: int, month: int) -> dict:
    """Return {week_num: (start_date, end_date)} for each week in the month."""
    from calendar import monthrange
    _, last_day = monthrange(year, month)
    boundaries = [(1,6),(7,13),(14,20),(21,27),(28,last_day)]
    weeks = {}
    for i, (s, e) in enumerate(boundaries, 1):
        if s > last_day:
            break
        e = min(e, last_day)
        weeks[i] = (datetime(year, month, s), datetime(year, month, e))
    return weeks

# =======================================
# AUSTRALIAN PAYROLL CALCULATION ENGINE
# =======================================

# 2025-26 Australian PAYG tax brackets (resident)
PAYG_BRACKETS_2025_26 = [
    (18200, 0, 0),          # 0 – $18,200: Nil
    (45000, 0.16, 0),       # $18,201 – $45,000: 16c for each $1 over $18,200
    (135000, 0.30, 4288),   # $45,001 – $135,000: $4,288 + 30c for each $1 over $45,000
    (190000, 0.37, 31288),  # $135,001 – $190,000: $31,288 + 37c for each $1 over $135,000
    (float('inf'), 0.45, 51638),  # $190,001+: $51,638 + 45c for each $1 over $190,000
]

MEDICARE_LEVY_RATE = 0.02  # 2% Medicare Levy
SUPER_GUARANTEE_RATE = 0.12  # 12% SG for 2025-26
ANNUAL_HOURS = 38 * 52  # 1,976 hours


def calculate_annual_payg_tax(gross_annual: float) -> float:
    """Calculate PAYG tax for a given gross annual income."""
    if gross_annual <= 0:
        return 0
    
    tax = 0
    prev_threshold = 0
    for threshold, rate, base_tax in PAYG_BRACKETS_2025_26:
        if gross_annual <= threshold:
            tax = base_tax + (gross_annual - prev_threshold) * rate if base_tax == 0 and rate > 0 else base_tax + (gross_annual - (prev_threshold)) * rate
            # Correct calculation using bracket base
            if threshold == 18200:
                tax = 0
            elif threshold == 45000:
                tax = (gross_annual - 18200) * 0.16
            elif threshold == 135000:
                tax = 4288 + (gross_annual - 45000) * 0.30
            elif threshold == 190000:
                tax = 31288 + (gross_annual - 135000) * 0.37
            else:
                tax = 51638 + (gross_annual - 190000) * 0.45
            break
        prev_threshold = threshold
    
    return max(0, round(tax, 2))


def calculate_medicare_levy(gross_annual: float) -> float:
    """Calculate Medicare Levy (2% of taxable income above tax-free threshold)."""
    if gross_annual <= 18200:  # No Medicare below tax-free threshold
        return 0
    return round(gross_annual * MEDICARE_LEVY_RATE, 2)


def reverse_calculate_gross_from_net(target_net_annual: float) -> dict:
    """Given a target annual net (take-home), calculate the required gross annual salary.
    Uses iterative bisection to find the gross that yields the desired net.
    
    Net = Gross - PAYG Tax - Medicare Levy
    Super is ON TOP of gross, not deducted from net.
    """
    if target_net_annual <= 0:
        return {
            "gross_annual": 0, "payg_tax_annual": 0, "medicare_levy_annual": 0,
            "net_annual": 0, "super_annual": 0, "employer_cost_annual": 0
        }
    
    # Bisection method: find gross where (gross - tax - medicare) ≈ target_net
    low = target_net_annual
    high = target_net_annual * 2  # Generous upper bound
    
    for _ in range(100):  # Max iterations
        mid = (low + high) / 2
        tax = calculate_annual_payg_tax(mid)
        medicare = calculate_medicare_levy(mid)
        net = mid - tax - medicare
        
        if abs(net - target_net_annual) < 0.01:
            break
        elif net < target_net_annual:
            low = mid
        else:
            high = mid
    
    gross_annual = round(mid, 2)
    payg_tax = calculate_annual_payg_tax(gross_annual)
    medicare = calculate_medicare_levy(gross_annual)
    net_annual = round(gross_annual - payg_tax - medicare, 2)
    super_annual = round(gross_annual * SUPER_GUARANTEE_RATE, 2)
    employer_cost_annual = round(gross_annual + super_annual, 2)
    
    return {
        "gross_annual": gross_annual,
        "payg_tax_annual": payg_tax,
        "medicare_levy_annual": medicare,
        "net_annual": net_annual,
        "super_annual": super_annual,
        "employer_cost_annual": employer_cost_annual,
    }


def calculate_payroll_for_employee(target_takehome_hourly: float, hours_worked: float,
                                     pay_period_start: str = "", pay_period_end: str = "") -> dict:
    """Full reverse payroll calculation for one employee.
    
    Given target take-home hourly rate and hours worked:
    1. Calculate weekly net = rate × hours
    2. Annualize weekly net (× 52) to find tax bracket
    3. Reverse calculate annual gross that yields this annual net
    4. Derive weekly gross = annual gross / 52
    5. Calculate PAYG, Medicare, Super for the period
    
    This matches the Australian payroll template approach where
    actual weekly earnings determine the tax bracket (not full-time equivalent).
    """
    if hours_worked <= 0 or target_takehome_hourly <= 0:
        return {
            "target_takehome_hourly": target_takehome_hourly,
            "hours_worked": hours_worked,
            "pay_period_start": pay_period_start,
            "pay_period_end": pay_period_end,
            "annual_gross_salary": 0, "annual_payg_tax": 0, "annual_medicare_levy": 0,
            "annual_net": 0, "annual_super": 0, "annual_employer_cost": 0,
            "gross_hourly_rate": target_takehome_hourly,  # When no hours, gross = net rate
            "net_hourly_rate": target_takehome_hourly,
            "gross_pay": 0, "payg_tax": 0, "medicare_levy": 0,
            "total_deductions": 0, "net_pay": 0,
            "superannuation": 0, "employer_total_cost": 0,
            "super_rate_pct": round(SUPER_GUARANTEE_RATE * 100, 1),
            "medicare_rate_pct": round(MEDICARE_LEVY_RATE * 100, 1),
        }
    
    # Step 1: Weekly net = rate × hours
    weekly_net = target_takehome_hourly * hours_worked
    
    # Step 2: Annualize weekly net (project as if this is every week)
    target_net_annual = weekly_net * 52
    
    # Step 3: Reverse calculate gross annual
    annual = reverse_calculate_gross_from_net(target_net_annual)
    
    # Step 4: Weekly gross = annual gross / 52
    weekly_gross = round(annual["gross_annual"] / 52, 2)
    
    # Step 5: Derive hourly gross rate
    gross_hourly = round(weekly_gross / hours_worked, 4) if hours_worked > 0 else 0
    
    # Step 6: Weekly tax (PAYG + Medicare combined) = annual total / 52
    weekly_payg = round(annual["payg_tax_annual"] / 52, 2)
    weekly_medicare = round(annual["medicare_levy_annual"] / 52, 2)
    weekly_net_check = round(weekly_gross - weekly_payg - weekly_medicare, 2)
    weekly_super = round(weekly_gross * SUPER_GUARANTEE_RATE, 2)
    employer_total_cost = round(weekly_gross + weekly_super, 2)
    
    return {
        "target_takehome_hourly": target_takehome_hourly,
        "hours_worked": hours_worked,
        "pay_period_start": pay_period_start,
        "pay_period_end": pay_period_end,
        # Annual (annualized from weekly)
        "annual_gross_salary": annual["gross_annual"],
        "annual_payg_tax": annual["payg_tax_annual"],
        "annual_medicare_levy": annual["medicare_levy_annual"],
        "annual_net": annual["net_annual"],
        "annual_super": annual["super_annual"],
        "annual_employer_cost": annual["employer_cost_annual"],
        # Per hour
        "gross_hourly_rate": gross_hourly,
        "net_hourly_rate": target_takehome_hourly,
        # For the period (weekly)
        "gross_pay": weekly_gross,
        "payg_tax": weekly_payg,
        "medicare_levy": weekly_medicare,
        "total_deductions": round(weekly_payg + weekly_medicare, 2),
        "net_pay": weekly_net_check,
        "superannuation": weekly_super,
        "employer_total_cost": employer_total_cost,
        # Rates used
        "super_rate_pct": round(SUPER_GUARANTEE_RATE * 100, 1),
        "medicare_rate_pct": round(MEDICARE_LEVY_RATE * 100, 1),
    }


# =======================================
# ENDPOINTS
# =======================================

@router.get("/centers")
async def get_international_centers(token: str):
    """Get international centers based on user role:
    - Super Admin / Admin: all international centers (is_india_center=false)
    - International center manager: only their own center
    - India center manager: 403 forbidden
    """
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    user_center = normalize_center_code(session.get("center", ""))
    is_super_admin = session.get("is_super_admin", False)
    is_admin = session.get("is_admin", False)
    
    if is_super_admin or is_admin:
        # Admin/Super Admin: return all international centers
        centers = await db.centers.find(
            {"is_india_center": {"$ne": True}},
            {"_id": 0, "code": 1, "name": 1, "country": 1, "city": 1, "is_india_center": 1}
        ).sort("code", 1).to_list(100)
        return {"success": True, "centers": centers, "show_dropdown": True}
    
    # Regular manager: check if their center is international
    user_center_doc = await db.centers.find_one(
        {"code": {"$in": center_code_variants(user_center)}},
        {"_id": 0, "code": 1, "name": 1, "country": 1, "is_india_center": 1}
    )
    
    if not user_center_doc:
        raise HTTPException(404, "Your center not found")
    
    if user_center_doc.get("is_india_center", True):
        raise HTTPException(403, "International Attendance is not available for India centers")
    
    # International center manager: return only their center
    return {
        "success": True, 
        "centers": [user_center_doc],
        "show_dropdown": False  # No dropdown for center managers
    }

@router.post("/employees")
async def get_international_employees(req: CenterRequest):
    """Get all employees for an international center"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Access control
    access = await check_international_access(session, req.center)
    if not access["allowed"]:
        raise HTTPException(403, access.get("error", "Access denied"))
    
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
        
        # Target take-home rate (if set separately, otherwise use hourly_rate)
        target_takehome = emp.get("target_takehome_rate")
        if target_takehome is not None and target_takehome != "":
            target_takehome = float(target_takehome)
        else:
            target_takehome = hourly_rate  # Default: hourly_rate IS the take-home
        
        # Calculate gross hourly rate from the take-home using standard 38hr week
        gross_info = calculate_payroll_for_employee(target_takehome, 38) if target_takehome > 0 else {}
        gross_hourly = gross_info.get("gross_hourly_rate", 0)
        
        # Build clean employee record (exclude _id for JSON serialization)
        clean_emp = {
            "employee_id": emp_id,
            "name": emp.get("name", "Unknown"),
            "center": emp.get("center", ""),
            "category": category,
            "role": emp.get("role") or emp.get("designation") or "",
            "hourly_rate": hourly_rate,
            "target_takehome_rate": target_takehome,
            "gross_hourly_rate": gross_hourly,
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
    
    # Access control
    access = await check_international_access(session, req.center)
    if not access["allowed"]:
        raise HTTPException(403, access.get("error", "Access denied"))
    
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
            "target_takehome_rate": float(emp.get("target_takehome_rate", 0) or 0),
            "gross_hourly_rate": float(emp.get("gross_hourly_rate", 0) or 0),
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
    
    # Access control
    access = await check_international_access(session, req.center)
    if not access["allowed"]:
        raise HTTPException(403, access.get("error", "Access denied"))
    
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
    
    # Access control
    access = await check_international_access(session, req.center)
    if not access["allowed"]:
        raise HTTPException(403, access.get("error", "Access denied"))
    
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
                "hourly_rate": float(emp.get("target_takehome_rate", 0) or emp.get("hourly_rate", 0) or 0),
                "target_takehome_rate": float(emp.get("target_takehome_rate", 0) or emp.get("hourly_rate", 0) or 0),
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
    
    # Access control
    access = await check_international_access(session, req.center)
    if not access["allowed"]:
        raise HTTPException(403, access.get("error", "Access denied"))
    
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
    
    # Access control (checked again inside get_monthly_report, but early exit here)
    access = await check_international_access(session, req.center)
    if not access["allowed"]:
        raise HTTPException(403, access.get("error", "Access denied"))
    
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
    
    # Access control
    access = await check_international_access(session, req.center)
    if not access["allowed"]:
        raise HTTPException(403, access.get("error", "Access denied"))
    
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


@router.post("/export/payroll-summary-csv")
async def export_payroll_summary_csv(req: MonthlyReportRequest):
    """Export full monthly payroll summary with tax breakdown as CSV (matching template format)."""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    access = await check_international_access(session, req.center)
    if not access["allowed"]:
        raise HTTPException(403, access.get("error", "Access denied"))

    # Get full payroll report with reverse calculations
    report = await get_payroll_report(PayrollReportRequest(
        token=req.token, center=req.center, year=req.year, month=req.month
    ))

    output = io.StringIO()
    writer = csv.writer(output)

    month_name = report["month_name"]
    writer.writerow([f"Payroll Summary - {req.center}"])
    writer.writerow([f"Month: {month_name} {report['year']}"])
    writer.writerow([f"Super Rate: {report['rates']['super_rate']} | Medicare: {report['rates']['medicare_rate']}"])
    writer.writerow([])

    # Employee payroll breakdown
    wk_count = report["weeks_in_month"]
    wk_headers = [f"Wk{w} Hrs" for w in range(1, wk_count + 1)]
    headers = (["Employee", "Category"] + wk_headers +
               ["Total Hrs", "Rate/Hr (Net)", "Updated Rate/Hr (Gross)",
                "Net Pay", "Estimated Gross", "PAYG Tax", "Medicare",
                "Super Amount", "Employer Cost"])
    writer.writerow(headers)

    for emp in report["employees"]:
        wk_vals = [emp["weeks"].get(w, 0) for w in range(1, wk_count + 1)]
        row = ([emp["employee_name"], emp["category"]] + wk_vals +
               [emp["total_hours"],
                f"${emp['target_takehome_hourly']:.2f}",
                f"${emp['gross_hourly_rate']:.2f}",
                f"${emp['net_pay']:.2f}",
                f"${emp['gross_pay']:.2f}",
                f"${emp['payg_tax']:.2f}",
                f"${emp['medicare_levy']:.2f}",
                f"${emp['superannuation']:.2f}",
                f"${emp['employer_total_cost']:.2f}"])
        writer.writerow(row)

    # Totals
    t = report["totals"]
    totals_row = (["TOTAL", ""] + [""] * wk_count +
                  [t["total_hours"], "", "",
                   f"${t['total_net']:.2f}",
                   f"${t['total_gross']:.2f}",
                   f"${t['total_payg']:.2f}",
                   f"${t['total_medicare']:.2f}",
                   f"${t['total_super']:.2f}",
                   f"${t['total_employer_cost']:.2f}"])
    writer.writerow(totals_row)

    # Weekly org cost breakdown
    writer.writerow([])
    writer.writerow(["Weekly Organization Cost Breakdown"])
    writer.writerow(["Week", "Period", "Hours", "Gross Pay", "Net Pay", "Super", "Employer Cost"])
    for w in range(1, wk_count + 1):
        wt = report["weekly_totals"].get(str(w)) or report["weekly_totals"].get(w, {})
        label = report["week_labels"].get(str(w)) or report["week_labels"].get(w, "")
        writer.writerow([
            f"Week {w}", label,
            wt.get("hours", 0),
            f"${wt.get('gross', 0):.2f}",
            f"${wt.get('net', 0):.2f}",
            f"${wt.get('super', 0):.2f}",
            f"${wt.get('employer_cost', 0):.2f}",
        ])
    writer.writerow([
        "MONTHLY TOTAL", "",
        t["total_hours"],
        f"${t['total_gross']:.2f}",
        f"${t['total_net']:.2f}",
        f"${t['total_super']:.2f}",
        f"${t['total_employer_cost']:.2f}",
    ])

    output.seek(0)
    filename = f"{req.center}_Payroll_Summary_{month_name}_{report['year']}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("/export/monthly-pdf")
async def export_monthly_pdf(req: MonthlyReportRequest):
    """Export monthly payroll report as PDF"""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    access = await check_international_access(session, req.center)
    if not access["allowed"]:
        raise HTTPException(403, access.get("error", "Access denied"))
    
    # Get monthly data
    monthly_data = await get_monthly_report(req)
    
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch, cm
    from reportlab.lib import colors
    
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    # ---- HEADER ----
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 0.6 * inch, "Purnabramha - International Payroll Report")
    
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 0.85 * inch,
        f"Center: {req.center}  |  Month: {monthly_data['month_name']} {req.year}  |  Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
    
    # ---- SUMMARY BOX ----
    box_y = height - 1.5 * inch
    c.setFillColor(colors.Color(0.95, 0.95, 0.98))
    c.rect(0.5 * inch, box_y - 0.1 * inch, width - 1 * inch, 0.45 * inch, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.7 * inch, box_y + 0.1 * inch,
        f"Total Staff: {monthly_data['summary']['total_staff']}     |     "
        f"Total Hours: {monthly_data['summary']['total_hours']:.1f}     |     "
        f"Total Payroll: ${monthly_data['summary']['total_payroll']:,.2f}")
    
    # ---- TABLE ----
    table_top = box_y - 0.4 * inch
    weeks_count = monthly_data["weeks_in_month"]
    
    # Column widths
    col_name_w = 2.2 * inch
    col_cat_w = 1.2 * inch
    col_week_w = 0.85 * inch
    col_total_w = 0.9 * inch
    col_rate_w = 0.85 * inch
    col_salary_w = 1.1 * inch
    
    x_start = 0.5 * inch
    row_height = 0.28 * inch
    
    # Header row
    y = table_top
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.Color(0.2, 0.2, 0.35))
    header_h = 0.3 * inch
    c.rect(x_start, y - header_h + 0.05 * inch, width - 1 * inch, header_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    
    x = x_start + 0.1 * inch
    c.drawString(x, y - 0.15 * inch, "Employee Name")
    x += col_name_w
    c.drawString(x, y - 0.15 * inch, "Category")
    x += col_cat_w
    for w in range(1, weeks_count + 1):
        c.drawString(x, y - 0.15 * inch, f"Wk {w}")
        x += col_week_w
    c.drawString(x, y - 0.15 * inch, "Total Hrs")
    x += col_total_w
    c.drawString(x, y - 0.15 * inch, "Rate/Hr")
    x += col_rate_w
    c.drawString(x, y - 0.15 * inch, "Total Salary")
    
    # Data rows
    y = table_top - header_h
    c.setFont("Helvetica", 7.5)
    c.setFillColor(colors.black)
    
    for i, emp in enumerate(monthly_data["employees"]):
        if y < 0.8 * inch:
            c.showPage()
            c.setFont("Helvetica", 7.5)
            y = height - 0.6 * inch
        
        # Alternate row shading
        if i % 2 == 0:
            c.setFillColor(colors.Color(0.96, 0.96, 0.96))
            c.rect(x_start, y - row_height + 0.05 * inch, width - 1 * inch, row_height, fill=1, stroke=0)
            c.setFillColor(colors.black)
        
        x = x_start + 0.1 * inch
        c.drawString(x, y - 0.15 * inch, emp["employee_name"][:28])
        x += col_name_w
        c.drawString(x, y - 0.15 * inch, emp["category"][:15])
        x += col_cat_w
        for w in range(1, weeks_count + 1):
            hrs = emp["weeks"].get(w, 0)
            c.drawString(x, y - 0.15 * inch, f"{hrs:.1f}" if hrs else "-")
            x += col_week_w
        c.drawString(x, y - 0.15 * inch, f"{emp['total_hours']:.1f}")
        x += col_total_w
        c.drawString(x, y - 0.15 * inch, f"${emp['hourly_rate']:.2f}")
        x += col_rate_w
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(x, y - 0.15 * inch, f"${emp['total_salary']:,.2f}")
        c.setFont("Helvetica", 7.5)
        
        y -= row_height
    
    # Grand total line
    y -= 0.15 * inch
    c.setLineWidth(1)
    c.line(x_start, y + 0.1 * inch, width - 0.5 * inch, y + 0.1 * inch)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x_start + 0.1 * inch, y - 0.1 * inch,
        f"GRAND TOTAL:  Hours: {monthly_data['summary']['total_hours']:.1f}   |   Payroll: ${monthly_data['summary']['total_payroll']:,.2f}")
    
    # Footer
    c.setFont("Helvetica", 6)
    c.drawString(0.5 * inch, 0.3 * inch, "This is a computer-generated document. Purnabramha - MANASWINI FOODS PVT. LTD.")
    c.drawRightString(width - 0.5 * inch, 0.3 * inch, "Page 1")
    
    c.save()
    pdf_buffer.seek(0)
    
    filename = f"{req.center}_Payroll_{monthly_data['month_name']}_{req.year}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

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
    if not (session.get("is_super_admin") or session.get("is_admin")) and normalized_user_center != normalized_req_center:
        raise HTTPException(403, "Not authorized to update rates for this center")
    
    if req.new_rate < 0:
        raise HTTPException(400, "Hourly rate cannot be negative")
    
    # Try multiple ID fields and center variants since employee docs may use different keys
    variants = center_code_variants(req.center)
    
    update_fields = {"hourly_rate": req.new_rate, "target_takehome_rate": req.new_rate, "updated_at": datetime.now(timezone.utc).isoformat()}
    
    # First try employee_id field
    result = await db.employees.update_one(
        {"employee_id": req.employee_id, "center": {"$in": variants}},
        {"$set": update_fields}
    )
    
    if result.modified_count == 0:
        # Try 'id' field
        result = await db.employees.update_one(
            {"id": req.employee_id, "center": {"$in": variants}},
            {"$set": update_fields}
        )
    
    if result.modified_count == 0:
        # Try MongoDB _id (employee_id might be a stringified ObjectId)
        from bson import ObjectId
        try:
            oid = ObjectId(req.employee_id)
            result = await db.employees.update_one(
                {"_id": oid},
                {"$set": update_fields}
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



# =======================================
# REVERSE PAYROLL ENDPOINTS
# =======================================

class ReversePayrollRequest(BaseModel):
    token: str
    target_takehome_hourly: float
    hours_worked: float = 0  # 0 means use default 38hrs/week
    pay_period_start: str = ""
    pay_period_end: str = ""

@router.post("/reverse-payroll-calculate")
async def reverse_payroll_calculate(req: ReversePayrollRequest):
    """Calculate reverse payroll: given target take-home hourly, compute gross, tax, super, etc."""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    hours = req.hours_worked if req.hours_worked > 0 else 38  # Default one week
    result = calculate_payroll_for_employee(
        req.target_takehome_hourly, hours,
        req.pay_period_start, req.pay_period_end
    )
    return {"success": True, "payroll": result}


class PayrollReportRequest(BaseModel):
    token: str
    center: str
    year: int
    month: int

@router.post("/payroll-report")
async def get_payroll_report(req: PayrollReportRequest):
    """Get full monthly payroll report with Australian tax calculations.
    This uses hourly_rate as the TARGET TAKE-HOME rate and reverse-calculates gross, tax, super.
    """
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    access = await check_international_access(session, req.center)
    if not access["allowed"]:
        raise HTTPException(403, access.get("error", "Access denied"))
    
    # Get the basic monthly data (hours per employee)
    monthly_data = await get_monthly_report(MonthlyReportRequest(
        token=req.token, center=req.center, year=req.year, month=req.month
    ))
    
    from calendar import monthrange
    _, last_day = monthrange(req.year, req.month)
    month_name = datetime(req.year, req.month, 1).strftime("%B")
    pay_period_start = f"{req.year}-{req.month:02d}-01"
    pay_period_end = f"{req.year}-{req.month:02d}-{last_day:02d}"
    
    # Build week labels
    weeks_in_month = monthly_data["weeks_in_month"]
    week_labels = {}
    for w in range(1, weeks_in_month + 1):
        week_labels[w] = get_week_label(req.year, req.month, w)
    
    # Calculate payroll for each employee using reverse calculation
    payroll_employees = []
    totals = {
        "total_hours": 0, "total_gross": 0, "total_payg": 0,
        "total_medicare": 0, "total_net": 0, "total_super": 0,
        "total_employer_cost": 0
    }
    
    # Weekly totals
    weekly_totals = {}
    for w in range(1, weeks_in_month + 1):
        weekly_totals[w] = {"hours": 0, "gross": 0, "net": 0, "super": 0, "employer_cost": 0}
    
    for emp in monthly_data["employees"]:
        target_takehome_hourly = emp["hourly_rate"]
        total_hours = emp["total_hours"]
        
        # Reverse calculate for the full month
        payroll = calculate_payroll_for_employee(
            target_takehome_hourly, total_hours,
            pay_period_start, pay_period_end
        )
        
        # Calculate weekly cost breakdown
        weekly_costs = {}
        for w in range(1, weeks_in_month + 1):
            wk_hours = emp["weeks"].get(w, 0)
            if wk_hours > 0:
                wk_payroll = calculate_payroll_for_employee(target_takehome_hourly, wk_hours)
                weekly_costs[w] = {
                    "hours": wk_hours,
                    "gross": wk_payroll["gross_pay"],
                    "net": wk_payroll["net_pay"],
                    "payg": wk_payroll["payg_tax"],
                    "medicare": wk_payroll["medicare_levy"],
                    "super": wk_payroll["superannuation"],
                    "employer_cost": wk_payroll["employer_total_cost"],
                }
                # Accumulate weekly totals
                weekly_totals[w]["hours"] += wk_hours
                weekly_totals[w]["gross"] += wk_payroll["gross_pay"]
                weekly_totals[w]["net"] += wk_payroll["net_pay"]
                weekly_totals[w]["super"] += wk_payroll["superannuation"]
                weekly_totals[w]["employer_cost"] += wk_payroll["employer_total_cost"]
            else:
                weekly_costs[w] = {"hours": 0, "gross": 0, "net": 0, "payg": 0, "medicare": 0, "super": 0, "employer_cost": 0}
        
        emp_record = {
            **emp,
            "target_takehome_hourly": target_takehome_hourly,
            "gross_hourly_rate": payroll["gross_hourly_rate"],
            "gross_pay": payroll["gross_pay"],
            "payg_tax": payroll["payg_tax"],
            "medicare_levy": payroll["medicare_levy"],
            "total_deductions": payroll["total_deductions"],
            "net_pay": payroll["net_pay"],
            "superannuation": payroll["superannuation"],
            "employer_total_cost": payroll["employer_total_cost"],
            "weekly_costs": weekly_costs,
            # Annualized for reference
            "annual_gross": payroll["annual_gross_salary"],
            "annual_net": payroll["annual_net"],
        }
        payroll_employees.append(emp_record)
        
        totals["total_hours"] += total_hours
        totals["total_gross"] += payroll["gross_pay"]
        totals["total_payg"] += payroll["payg_tax"]
        totals["total_medicare"] += payroll["medicare_levy"]
        totals["total_net"] += payroll["net_pay"]
        totals["total_super"] += payroll["superannuation"]
        totals["total_employer_cost"] += payroll["employer_total_cost"]
    
    # Round totals
    for k in totals:
        totals[k] = round(totals[k], 2)
    
    # Round weekly totals
    for w in weekly_totals:
        for k in weekly_totals[w]:
            weekly_totals[w][k] = round(weekly_totals[w][k], 2)
    
    return {
        "success": True,
        "center": req.center,
        "year": req.year,
        "month": req.month,
        "month_name": month_name,
        "pay_period": f"{pay_period_start} to {pay_period_end}",
        "weeks_in_month": weeks_in_month,
        "week_labels": week_labels,
        "employees": payroll_employees,
        "totals": totals,
        "weekly_totals": weekly_totals,
        "rates": {
            "super_rate": f"{SUPER_GUARANTEE_RATE * 100:.1f}%",
            "medicare_rate": f"{MEDICARE_LEVY_RATE * 100:.1f}%",
            "annual_hours_basis": ANNUAL_HOURS,
        },
        "report_name": f"PB-{req.center}_Payroll_{month_name}_{req.year}"
    }


class PayslipRequest(BaseModel):
    token: str
    center: str
    year: int
    month: int
    employee_id: str

@router.post("/payslip")
async def generate_payslip(req: PayslipRequest):
    """Generate individual employee payslip with full Australian tax breakdown."""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    access = await check_international_access(session, req.center)
    if not access["allowed"]:
        raise HTTPException(403, access.get("error", "Access denied"))
    
    # Get employee details
    variants = center_code_variants(req.center)
    emp = await db.employees.find_one(
        {"$or": [
            {"employee_id": req.employee_id, "center": {"$in": variants}},
            {"id": req.employee_id, "center": {"$in": variants}}
        ]},
        {"_id": 0}
    )
    if not emp:
        raise HTTPException(404, "Employee not found")
    
    # Get attendance for the month
    from calendar import monthrange
    _, last_day = monthrange(req.year, req.month)
    start_date = f"{req.year}-{req.month:02d}-01"
    end_date = f"{req.year}-{req.month:02d}-{last_day:02d}"
    
    records = await db.international_attendance.find({
        "employee_id": req.employee_id,
        "center": {"$in": variants},
        "date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0}).to_list(100)
    
    total_hours = sum(r.get("hours_worked", 0) for r in records)
    days_worked = len([r for r in records if r.get("hours_worked", 0) > 0])
    
    target_takehome_hourly = float(emp.get("hourly_rate", 0) or 0)
    month_name = datetime(req.year, req.month, 1).strftime("%B")
    
    payroll = calculate_payroll_for_employee(
        target_takehome_hourly, total_hours,
        start_date, end_date
    )
    
    # Build weekly breakdown
    weeks_in_month = calculate_weeks_in_month(req.year, req.month)
    weekly_hours = {}
    for r in records:
        wk = get_week_number_from_date(r["date"])
        weekly_hours[wk] = weekly_hours.get(wk, 0) + r.get("hours_worked", 0)
    
    week_breakdown = []
    for w in range(1, weeks_in_month + 1):
        hrs = round(weekly_hours.get(w, 0), 2)
        label = get_week_label(req.year, req.month, w)
        week_breakdown.append({
            "week": w, "label": label, "hours": hrs,
            "gross": round(hrs * payroll["gross_hourly_rate"], 2),
            "net": round(hrs * target_takehome_hourly, 2),
        })
    
    return {
        "success": True,
        "payslip": {
            "employee_name": emp.get("name", "Unknown"),
            "employee_id": req.employee_id,
            "category": emp.get("category", "CASUAL"),
            "role": emp.get("role", ""),
            "center": req.center,
            "pay_period": f"1 {month_name} {req.year} - {last_day} {month_name} {req.year}",
            "month": month_name,
            "year": req.year,
            "days_worked": days_worked,
            "total_hours": round(total_hours, 2),
            "week_breakdown": week_breakdown,
            # Rates
            "target_takehome_hourly": target_takehome_hourly,
            "gross_hourly_rate": payroll["gross_hourly_rate"],
            # Earnings
            "gross_earnings": payroll["gross_pay"],
            # Deductions
            "payg_tax": payroll["payg_tax"],
            "medicare_levy": payroll["medicare_levy"],
            "total_deductions": payroll["total_deductions"],
            # Net
            "net_pay": payroll["net_pay"],
            # Super (on top, not deducted)
            "superannuation": payroll["superannuation"],
            "super_rate": f"{SUPER_GUARANTEE_RATE * 100:.1f}%",
            # Employer cost
            "employer_total_cost": payroll["employer_total_cost"],
            # Annualized reference
            "annualized_gross": payroll["annual_gross_salary"],
            "annualized_net": payroll["annual_net"],
        }
    }


@router.post("/payslip-pdf")
async def generate_payslip_pdf(req: PayslipRequest):
    """Generate payslip as a PDF document."""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    # Get the payslip data
    payslip_data = await generate_payslip(req)
    ps = payslip_data["payslip"]
    
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16*mm, rightMargin=16*mm,
                            topMargin=14*mm, bottomMargin=14*mm)
    
    styles = getSampleStyleSheet()
    DARK_BG = colors.HexColor("#0F172A")
    SAFFRON = colors.HexColor("#D97706")
    GREEN = colors.HexColor("#059669")
    RED = colors.HexColor("#DC2626")
    LIGHT_GRAY = colors.HexColor("#F1F5F9")
    MID_GRAY = colors.HexColor("#94A3B8")
    
    title_style = ParagraphStyle("T", parent=styles["Title"], fontSize=18,
        textColor=colors.white, fontName="Helvetica-Bold")
    section_style = ParagraphStyle("S", parent=styles["Heading2"], fontSize=12,
        textColor=DARK_BG, spaceBefore=12, spaceAfter=4, fontName="Helvetica-Bold")
    normal_style = ParagraphStyle("N", parent=styles["Normal"], fontSize=9,
        textColor=colors.HexColor("#334155"), fontName="Helvetica")
    small_style = ParagraphStyle("Sm", parent=styles["Normal"], fontSize=7.5,
        textColor=MID_GRAY, fontName="Helvetica")
    
    def fmt(val):
        return f"${abs(val):,.2f}" if val >= 0 else f"-${abs(val):,.2f}"
    
    elements = []
    
    # Header banner
    import os
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pb_logo.png")
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=40, height=40)
        header_cells = [[logo, Paragraph("PAYSLIP", title_style), ""]]
    else:
        header_cells = [["", Paragraph("PAYSLIP", title_style), ""]]
    
    ht = Table(header_cells, colWidths=[50, 350, 100])
    ht.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_BG),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    elements.append(ht)
    elements.append(Spacer(1, 8))
    
    # Employee Info
    info_rows = [
        ["Employee", ps["employee_name"], "Pay Period", ps["pay_period"]],
        ["Employee ID", ps["employee_id"], "Center", ps["center"]],
        ["Category", ps["category"], "Days Worked", str(ps["days_worked"])],
    ]
    it = Table(info_rows, colWidths=[80, 180, 80, 150])
    it.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), MID_GRAY),
        ('TEXTCOLOR', (2, 0), (2, -1), MID_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(it)
    elements.append(HRFlowable(width="100%", thickness=1, color=SAFFRON, spaceAfter=6, spaceBefore=6))
    
    # Earnings
    elements.append(Paragraph("Earnings", section_style))
    earn_rows = [
        [Paragraph("<b>Description</b>", normal_style), Paragraph("<b>Rate</b>", normal_style),
         Paragraph("<b>Hours</b>", normal_style), Paragraph("<b>Amount</b>", normal_style)],
        ["Gross Pay (reverse-calculated)", fmt(ps["gross_hourly_rate"]) + "/hr",
         str(ps["total_hours"]), fmt(ps["gross_earnings"])],
    ]
    et = Table(earn_rows, colWidths=[200, 90, 70, 100])
    et.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(et)
    elements.append(Spacer(1, 6))
    
    # Deductions
    elements.append(Paragraph("Deductions", section_style))
    ded_rows = [
        [Paragraph("<b>Description</b>", normal_style), Paragraph("<b>Amount</b>", normal_style)],
        ["PAYG Tax Withholding", fmt(ps["payg_tax"])],
        ["Medicare Levy (2%)", fmt(ps["medicare_levy"])],
        [Paragraph("<b>Total Deductions</b>", normal_style), Paragraph(f"<b>{fmt(ps['total_deductions'])}</b>", normal_style)],
    ]
    dt = Table(ded_rows, colWidths=[300, 160])
    dt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#FEE2E2")),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#FEF3C7")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(dt)
    elements.append(Spacer(1, 6))
    
    # Net Pay
    net_rows = [
        [Paragraph("<b>NET PAY (Take-Home)</b>", ParagraphStyle("NP", parent=normal_style, fontSize=12, fontName="Helvetica-Bold")),
         Paragraph(f"<b>{fmt(ps['net_pay'])}</b>", ParagraphStyle("NPV", parent=normal_style, fontSize=12, textColor=GREEN, fontName="Helvetica-Bold"))],
    ]
    nt = Table(net_rows, colWidths=[300, 160])
    nt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#D1FAE5")),
        ('GRID', (0, 0), (-1, -1), 0.5, GREEN),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    elements.append(nt)
    elements.append(Spacer(1, 6))
    
    # Superannuation (separate section)
    elements.append(Paragraph("Superannuation (Employer Contribution)", section_style))
    super_rows = [
        [f"Super Guarantee ({ps['super_rate']})", fmt(ps["superannuation"])],
        [Paragraph("<b>Employer Total Cost</b>", normal_style), Paragraph(f"<b>{fmt(ps['employer_total_cost'])}</b>", normal_style)],
    ]
    st = Table(super_rows, colWidths=[300, 160])
    st.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#EDE9FE")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(st)
    elements.append(Spacer(1, 8))
    
    # Weekly breakdown
    if ps.get("week_breakdown"):
        elements.append(Paragraph("Weekly Hours Breakdown", section_style))
        wb_rows = [["Week", "Period", "Hours", "Gross", "Net"]]
        for wb in ps["week_breakdown"]:
            wb_rows.append([
                f"Week {wb['week']}", wb["label"],
                f"{wb['hours']:.1f}", fmt(wb["gross"]), fmt(wb["net"])
            ])
        wbt = Table(wb_rows, colWidths=[50, 130, 60, 90, 90])
        wbt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(wbt)
    
    # Formula note
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY, spaceBefore=4))
    elements.append(Paragraph(
        "Formula: Target take-home hourly x 1,976 annual hrs = Target annual net. "
        "Reverse-calculate gross to yield that net after PAYG + Medicare. "
        "Super (12%) is on top of gross, not deducted from net pay.",
        small_style
    ))
    elements.append(Paragraph(
        f"Generated {datetime.now().strftime('%d %b %Y %I:%M %p')} | Purnabramha - MANASWINI FOODS PVT. LTD.",
        small_style
    ))
    
    doc.build(elements)
    buf.seek(0)
    
    filename = f"Payslip_{ps['employee_name'].replace(' ', '_')}_{ps['month']}_{ps['year']}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/payroll-report-pdf")
async def export_payroll_report_pdf(req: PayrollReportRequest):
    """Export full payroll report with tax breakdown as PDF."""
    if not verify_token:
        raise HTTPException(500, "Server configuration error")
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    report = await get_payroll_report(req)
    
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10*mm, rightMargin=10*mm,
                            topMargin=12*mm, bottomMargin=12*mm)
    
    styles = getSampleStyleSheet()
    DARK_BG = colors.HexColor("#0F172A")
    SAFFRON = colors.HexColor("#D97706")
    LIGHT_GRAY = colors.HexColor("#F1F5F9")
    MID_GRAY = colors.HexColor("#94A3B8")
    GREEN = colors.HexColor("#059669")
    
    title_style = ParagraphStyle("T", parent=styles["Title"], fontSize=16,
        textColor=colors.white, fontName="Helvetica-Bold")
    section_style = ParagraphStyle("S", parent=styles["Heading2"], fontSize=11,
        textColor=DARK_BG, spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold")
    normal_style = ParagraphStyle("N", parent=styles["Normal"], fontSize=8,
        textColor=colors.HexColor("#334155"), fontName="Helvetica")
    small_style = ParagraphStyle("Sm", parent=styles["Normal"], fontSize=7,
        textColor=MID_GRAY, fontName="Helvetica")
    
    def fmt(val):
        return f"${abs(val):,.2f}" if val >= 0 else f"-${abs(val):,.2f}"
    
    elements = []
    
    # Header
    import os
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pb_logo.png")
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=36, height=36)
        header_cells = [[logo, Paragraph(f"Payroll Report - {report['center']}", title_style),
                         Paragraph(f"{report['month_name']} {report['year']}", ParagraphStyle("D", textColor=SAFFRON, fontSize=11, fontName="Helvetica-Bold"))]]
    else:
        header_cells = [["", Paragraph(f"Payroll Report - {report['center']}", title_style),
                         Paragraph(f"{report['month_name']} {report['year']}", ParagraphStyle("D", textColor=SAFFRON, fontSize=11, fontName="Helvetica-Bold"))]]
    
    ht = Table(header_cells, colWidths=[45, 500, 200])
    ht.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_BG),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    elements.append(ht)
    elements.append(Spacer(1, 4))
    
    # Summary cards
    t = report["totals"]
    summary_cells = [[
        Paragraph(f"<b>Staff:</b> {len(report['employees'])}", normal_style),
        Paragraph(f"<b>Hours:</b> {t['total_hours']:.1f}", normal_style),
        Paragraph(f"<b>Gross:</b> {fmt(t['total_gross'])}", normal_style),
        Paragraph(f"<b>PAYG:</b> {fmt(t['total_payg'])}", normal_style),
        Paragraph(f"<b>Net:</b> {fmt(t['total_net'])}", normal_style),
        Paragraph(f"<b>Super:</b> {fmt(t['total_super'])}", normal_style),
        Paragraph(f"<b>Employer Cost:</b> {fmt(t['total_employer_cost'])}", normal_style),
    ]]
    st = Table(summary_cells, colWidths=[80, 80, 105, 95, 100, 95, 130])
    st.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
        ('BOX', (0, 0), (-1, -1), 0.5, GREEN),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    elements.append(st)
    elements.append(Spacer(1, 6))
    
    # Employee table
    elements.append(Paragraph("Employee Payroll Breakdown", section_style))
    
    # Build week headers from labels
    week_headers = [f"Wk{w}" for w in range(1, report["weeks_in_month"] + 1)]
    headers = ["Employee", "Category"] + week_headers + [
        "Total Hrs", "Take-Home/Hr", "Gross/Hr", "Gross Pay",
        "PAYG Tax", "Medicare", "Net Pay", "Super", "Employer Cost"
    ]
    
    data_rows = [headers]
    for emp in report["employees"]:
        week_vals = [f"{emp['weeks'].get(w, 0):.1f}" for w in range(1, report["weeks_in_month"] + 1)]
        row = [
            emp["employee_name"][:22],
            emp["category"][:10],
        ] + week_vals + [
            f"{emp['total_hours']:.1f}",
            fmt(emp["target_takehome_hourly"]),
            fmt(emp["gross_hourly_rate"]),
            fmt(emp["gross_pay"]),
            fmt(emp["payg_tax"]),
            fmt(emp["medicare_levy"]),
            fmt(emp["net_pay"]),
            fmt(emp["superannuation"]),
            fmt(emp["employer_total_cost"]),
        ]
        data_rows.append(row)
    
    # Totals row
    week_totals = [f"{sum(e['weeks'].get(w, 0) for e in report['employees']):.1f}" for w in range(1, report["weeks_in_month"] + 1)]
    totals_row = ["TOTAL", ""] + week_totals + [
        f"{t['total_hours']:.1f}", "", "",
        fmt(t["total_gross"]), fmt(t["total_payg"]), fmt(t["total_medicare"]),
        fmt(t["total_net"]), fmt(t["total_super"]), fmt(t["total_employer_cost"]),
    ]
    data_rows.append(totals_row)
    
    # Column widths
    wk_count = report["weeks_in_month"]
    col_widths = [95, 55] + [35] * wk_count + [40, 52, 50, 55, 52, 48, 55, 48, 60]
    
    dt = Table(data_rows, colWidths=col_widths)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 6.5),
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, LIGHT_GRAY]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#FEF3C7")),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
    ]
    dt.setStyle(TableStyle(style_cmds))
    elements.append(dt)
    elements.append(Spacer(1, 8))
    
    # Week labels reference
    if report.get("week_labels"):
        elements.append(Paragraph("Week Date Ranges", section_style))
        wl_text = " &nbsp;|&nbsp; ".join([f"<b>Wk{w}:</b> {lbl}" for w, lbl in report["week_labels"].items()])
        elements.append(Paragraph(wl_text, normal_style))

    elements.append(Spacer(1, 6))

    # ----- WEEKLY ORGANIZATION COST BREAKDOWN -----
    if report.get("weekly_totals"):
        elements.append(Paragraph("Weekly Organization Cost Breakdown", section_style))
        elements.append(Paragraph("What the organization pays each week (all employees combined)", small_style))
        elements.append(Spacer(1, 3))

        wk_headers = ["Week", "Period", "Hours", "Gross Pay", "Net Pay", "Super", "Employer Cost"]
        wk_data = [wk_headers]

        wk_count = report["weeks_in_month"]
        for w in range(1, wk_count + 1):
            wt = report["weekly_totals"].get(w) or report["weekly_totals"].get(str(w), {})
            label = report.get("week_labels", {}).get(w) or report.get("week_labels", {}).get(str(w), "")
            wk_data.append([
                f"Week {w}",
                str(label),
                f"{wt.get('hours', 0):.1f}",
                fmt(wt.get('gross', 0)),
                fmt(wt.get('net', 0)),
                fmt(wt.get('super', 0)),
                fmt(wt.get('employer_cost', 0)),
            ])

        # Monthly total row
        wk_data.append([
            "MONTHLY TOTAL", "",
            f"{t['total_hours']:.1f}",
            fmt(t['total_gross']),
            fmt(t['total_net']),
            fmt(t['total_super']),
            fmt(t['total_employer_cost']),
        ])

        wk_col_widths = [60, 120, 55, 80, 80, 70, 90]
        wk_table = Table(wk_data, colWidths=wk_col_widths)
        wk_style = [
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, LIGHT_GRAY]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#FEF3C7")),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]
        wk_table.setStyle(TableStyle(wk_style))
        elements.append(wk_table)
        elements.append(Spacer(1, 8))

    # ----- PER-PERSON ORGANIZATION COST -----
    if report.get("employees") and len(report["employees"]) > 0:
        elements.append(Paragraph("Per-Person Organization Cost", section_style))
        elements.append(Paragraph("Monthly cost to the organization per employee", small_style))
        elements.append(Spacer(1, 3))

        pp_headers = ["Employee", "Category", "Hours", "Take-Home/Hr", "Gross/Hr",
                       "Net Pay", "Super", "PAYG + Medicare", "Employer Cost"]
        pp_data = [pp_headers]

        for emp in report["employees"]:
            tax_combined = (emp.get("payg_tax", 0) or 0) + (emp.get("medicare_levy", 0) or 0)
            pp_data.append([
                emp["employee_name"][:22],
                emp.get("category", "")[:10],
                f"{emp['total_hours']:.1f}",
                fmt(emp.get("target_takehome_hourly") or emp.get("hourly_rate", 0)),
                fmt(emp.get("gross_hourly_rate", 0)),
                fmt(emp.get("net_pay", 0)),
                fmt(emp.get("superannuation", 0)),
                fmt(tax_combined),
                fmt(emp.get("employer_total_cost", 0)),
            ])

        # Total row
        total_tax = (t.get("total_payg", 0) or 0) + (t.get("total_medicare", 0) or 0)
        pp_data.append([
            f"TOTAL ({len(report['employees'])} staff)", "",
            f"{t['total_hours']:.1f}", "", "",
            fmt(t['total_net']),
            fmt(t['total_super']),
            fmt(total_tax),
            fmt(t['total_employer_cost']),
        ])

        pp_col_widths = [95, 55, 45, 65, 55, 65, 55, 75, 70]
        pp_table = Table(pp_data, colWidths=pp_col_widths)
        pp_style = [
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, LIGHT_GRAY]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#FEF3C7")),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]
        pp_table.setStyle(TableStyle(pp_style))
        elements.append(pp_table)
        elements.append(Spacer(1, 8))
    
    # Footer
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    elements.append(Paragraph(
        f"Super Rate: {report['rates']['super_rate']} | Medicare: {report['rates']['medicare_rate']} | "
        f"Annual Hours Basis: {report['rates']['annual_hours_basis']} | "
        f"Generated {datetime.now().strftime('%d %b %Y %I:%M %p')} | Purnabramha",
        small_style
    ))
    
    doc.build(elements)
    buf.seek(0)
    
    filename = f"{report['center']}_Payroll_{report['month_name']}_{report['year']}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
