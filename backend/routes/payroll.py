# =======================================
# Payroll Routes
# Salary Generation, Payslip Generation, Payroll Lock
# Location-aware: India (monthly salary) vs Australia (hourly/WA payroll)
# =======================================

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime, timezone, timedelta
from io import BytesIO
import calendar
import logging
import zipfile

# Import Australian payroll functions from international_attendance
from routes.international_attendance import (
    calculate_payroll_for_employee,
    center_code_variants,
    get_week_ranges,
    SUPER_GUARANTEE_RATE,
    MEDICARE_LEVY_RATE,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Payroll"])

# Database reference (set from main server)
db = None

def set_db(database):
    global db
    db = database

# Verify token function (set from main server)
verify_token = None

def set_verify_token(func):
    global verify_token
    verify_token = func

# Admin access check (set from main server)
has_admin_access = None

def set_has_admin_access(func):
    global has_admin_access
    has_admin_access = func

# ROOT_DIR for assets
ROOT_DIR = None

def set_root_dir(path):
    global ROOT_DIR
    ROOT_DIR = path

# =======================================
# PYDANTIC MODELS
# =======================================

class MonthRequest(BaseModel):
    token: str
    month: str  # YYYY-MM

class SalaryPreviewRequest(BaseModel):
    token: str
    month: str
    targetCenter: str  # Can be "ALL" for combined view

class SalaryGenRequest(BaseModel):
    token: str
    month: str
    mode: str = "all"  # "single" or "all"
    targetCenter: Optional[str] = None

class PayslipGenRequest(BaseModel):
    token: str
    month: str
    period: str = "1"
    targetCenter: Optional[str] = None
    mode: str = "all"  # "single" or "all"
    employeeName: Optional[str] = None
    fmt: str = "pdf"  # "pdf" or "docx"
    signatory: str = "sandeep"  # "sandeep" or "jayanti"

class PayslipEmployeesRequest(BaseModel):
    token: str
    center: str

# =======================================
# UTILITY FUNCTIONS
# =======================================

def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _draw_employee_photo(c, photo_url: str, x: float, y: float, w: float, h: float):
    """Draw employee photo on the PDF canvas. Falls back to placeholder if URL is empty or fails."""
    import urllib.request
    import tempfile
    from reportlab.lib.colors import HexColor
    from reportlab.lib.units import inch

    if photo_url:
        try:
            req = urllib.request.Request(photo_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                img_data = resp.read()
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(img_data)
                tmp_path = tmp.name
            c.drawImage(tmp_path, x, y, width=w, height=h,
                        preserveAspectRatio=True, mask='auto')
            import os as _os
            _os.unlink(tmp_path)
            return
        except Exception:
            pass
    # Placeholder
    c.setStrokeColor(HexColor("#CBD5E1"))
    c.setFillColor(HexColor("#F1F5F9"))
    c.roundRect(x, y, w, h, 2, fill=1, stroke=1)
    c.setFillColor(HexColor("#94A3B8"))
    c.setFont("Helvetica", 6)
    c.drawCentredString(x + w / 2, y + h / 2, "Photo")
    c.setFillColor(HexColor("#000000"))


async def get_center_country(center_code: str) -> str:
    """Detect center country from the centers collection. Returns 'India' or actual country."""
    center = await db.centers.find_one({"code": center_code}, {"_id": 0, "country": 1, "is_india_center": 1})
    if not center:
        return "India"  # Default
    country = (center.get("country") or "").strip()
    if country and country.lower() not in ("india", ""):
        return country
    if center.get("is_india_center") is False:
        return center.get("country", "International")
    return "India"

# =======================================
# ROUTES
# =======================================

@router.post("/payroll_status")
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

@router.post("/lock_payroll")
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

@router.post("/salary_preview")
async def salary_preview(req: SalaryPreviewRequest):
    """Preview salary data on screen for a specific center or ALL centers (transfer-aware).
    When targetCenter is 'ALL', fetches all employees once to avoid double-counting."""
    session = verify_token(req.token)
    if not session or not has_admin_access(session):
        raise HTTPException(403, "Only Admin/Super Admin can view salary preview")
    
    try:
        year, month = map(int, req.month.split("-"))
        dim = days_in_month(year, month)
        
        start_date = f"{req.month}-01"
        end_date = f"{req.month}-{dim:02d}"
        
        is_all = req.targetCenter.upper() == "ALL"
        
        if is_all:
            # ALL CENTERS mode: fetch every employee exactly once
            employees = await db.employees.find({}, {"_id": 0}).to_list(5000)
            target_center = "ALL CENTERS"
        else:
            target_center = req.targetCenter.upper()
            # Get home employees for selected center
            employees = await db.employees.find(
                {"center": target_center},
                {"_id": 0}
            ).to_list(1000)
            
            # Get transfers affecting this center during this month
            transfers_in = await db.transfer_requests.find({
                "to_center": target_center,
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
                "from_center": target_center,
                "status": {"$in": ["ACCEPTED", "COMPLETED"]},
                "start_date": {"$lte": end_date},
                "$or": [
                    {"end_date": {"$gte": start_date}},
                    {"end_date": None},
                    {"end_date": ""},
                    {"transfer_type": "PERMANENT"}
                ]
            }, {"_id": 0}).to_list(500)
            
            out_map = {}
            for t in transfers_out:
                out_map[t["employee_name"].upper()] = {
                    "to_center": t["to_center"],
                    "start_date": t["start_date"],
                    "end_date": t.get("end_date", ""),
                    "transfer_type": t["transfer_type"]
                }
            
            in_map = {}
            for t in transfers_in:
                name = t["employee_name"].upper()
                in_map[name] = {
                    "from_center": t["from_center"],
                    "start_date": t["start_date"],
                    "end_date": t.get("end_date", ""),
                    "transfer_type": t["transfer_type"]
                }
            
            # For permanently transferred-in employees, add them to the employee list
            for t in transfers_in:
                if t["transfer_type"] == "PERMANENT":
                    emp_name = t["employee_name"].upper()
                    if not any(e.get("name", "").upper() == emp_name for e in employees):
                        emp = await db.employees.find_one({"name": emp_name}, {"_id": 0})
                        if emp:
                            employees.append(emp)
        
        # Deduplicate employees by name (safety net)
        seen_names = set()
        unique_employees = []
        for emp in employees:
            name = emp.get("name", "").upper()
            if name and name not in seen_names:
                seen_names.add(name)
                unique_employees.append(emp)
        employees = unique_employees
        
        # Get ALL attendance across ALL centers for these employees
        emp_names = [e.get("name", "").upper() for e in employees]
        all_attendance = await db.attendance.find(
            {
                "employeeName": {"$in": emp_names},
                "date": {"$gte": start_date, "$lte": end_date}
            },
            {"_id": 0}
        ).to_list(50000)
        
        # Get advances
        advances = await db.advances.find(
            {"date": {"$regex": f"^{req.month}"}},
            {"_id": 0}
        ).to_list(5000)
        
        # Build attendance map
        att_map = {}
        for a in all_attendance:
            key = f"{a['employeeName']}_{a['date']}"
            if key not in att_map:
                att_map[key] = {"status": a.get("status", ""), "center": a.get("center", "")}
            else:
                att_map[key] = {"status": a.get("status", ""), "center": a.get("center", "")}
        
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
            
            transfer_tag = "HOME"
            working_center = emp.get("center", "")
            
            if not is_all:
                if emp_name in out_map:
                    transfer_tag = "TRANSFERRED_OUT"
                    working_center = out_map[emp_name]["to_center"]
                elif emp_name in in_map:
                    transfer_tag = "TRANSFERRED_IN"
                    working_center = target_center
            
            # Calculate working days
            present_days = 0
            for d in range(1, dim + 1):
                date_str = f"{req.month}-{d:02d}"
                key = f"{emp_name}_{date_str}"
                att_entry = att_map.get(key, {})
                status = att_entry.get("status", "")
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
                "workingCenter": working_center,
                "transferTag": transfer_tag,
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
            "center": target_center,
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

@router.post("/generate_salary")
async def generate_salary(req: SalaryGenRequest):
    """Generate salary Excel for ICICI upload (transfer-aware)"""
    session = verify_token(req.token)
    if not session or not has_admin_access(session):
        raise HTTPException(403, "Only Admin can generate salary")
    
    try:
        from openpyxl import Workbook
        
        year, month = map(int, req.month.split("-"))
        dim = days_in_month(year, month)
        start_date = f"{req.month}-01"
        end_date = f"{req.month}-{dim:02d}"
        
        # Get employees
        if req.mode == "single" and req.targetCenter:
            target_center = req.targetCenter.upper()
            employees = await db.employees.find(
                {"center": target_center},
                {"_id": 0}
            ).to_list(1000)
            
            # Add permanently transferred-in employees
            perm_in = await db.transfer_requests.find({
                "to_center": target_center,
                "transfer_type": "PERMANENT",
                "status": {"$in": ["ACCEPTED", "COMPLETED"]},
                "start_date": {"$lte": end_date}
            }, {"_id": 0}).to_list(100)
            
            for t in perm_in:
                emp_name = t["employee_name"].upper()
                if not any(e.get("name", "").upper() == emp_name for e in employees):
                    emp = await db.employees.find_one({"name": emp_name}, {"_id": 0})
                    if emp:
                        employees.append(emp)
        else:
            employees = await db.employees.find({}, {"_id": 0}).to_list(1000)
        
        # Get ALL attendance (not filtered by center - use actual working location)
        emp_names = [e.get("name", "").upper() for e in employees]
        attendance = await db.attendance.find(
            {
                "employeeName": {"$in": emp_names},
                "date": {"$gte": start_date, "$lte": end_date}
            },
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
            emp_remark = emp.get("remark", "").strip()
            credit_narr = emp_remark if emp_remark else f"SALARY {req.month}"
            debit_narr = emp_remark if emp_remark else "SALARY"
            
            # Calculate working days from actual attendance (any center)
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

@router.post("/payslip_employees")
async def payslip_employees(req: PayslipEmployeesRequest):
    """Get sorted employee list for a center (for payslip dropdown).
    Detects center country and queries the appropriate collection."""
    session = verify_token(req.token)
    if not session or not has_admin_access(session):
        raise HTTPException(403, "Only Admin can access payslip employees")

    center = req.center.upper()
    country = await get_center_country(center)

    if country != "India":
        # International center — fetch from employees collection (same as get_international_employees)
        variants = center_code_variants(center)
        employees_raw = await db.employees.find(
            {"center": {"$in": variants}},
        ).sort("name", 1).to_list(1000)

        result_employees = []
        for emp in employees_raw:
            emp_id = emp.get("employee_id") or emp.get("id") or emp.get("emp_id") or str(emp.get("_id", ""))
            target_takehome = float(emp.get("target_takehome_rate", 0) or emp.get("hourly_rate", 0) or 0)
            gross_hourly = float(emp.get("gross_hourly_rate", 0) or 0)
            result_employees.append({
                "name": emp.get("name", ""),
                "employee_id": emp_id,
                "designation": emp.get("category", emp.get("designation", emp.get("role", "CASUAL"))),
                "hourly_rate": float(emp.get("hourly_rate", 0) or 0),
                "target_takehome_rate": target_takehome,
                "gross_hourly_rate": gross_hourly,
            })

        return {
            "employees": result_employees,
            "country": country,
            "payroll_type": "hourly",
        }

    # India center — existing logic
    employees = await db.employees.find(
        {"center": center},
        {"_id": 0, "name": 1, "designation": 1}
    ).sort("name", 1).to_list(1000)

    return {
        "employees": [{"name": e.get("name", ""), "designation": e.get("designation", "")} for e in employees],
        "country": "India",
        "payroll_type": "monthly",
    }


@router.post("/payslips_generate")
async def payslips_generate(req: PayslipGenRequest):
    """Generate payslips (PDF/DOCX) — location-aware.
    India → Indian salary slip format.
    Australia / International → WA hourly payroll format.
    """
    session = verify_token(req.token)
    if not session or not has_admin_access(session):
        raise HTTPException(403, "Only Admin can generate payslips")

    try:
        year, month = map(int, req.month.split("-"))

        # Detect center country
        target_center = (req.targetCenter or "").upper()
        country = await get_center_country(target_center) if target_center else "India"

        if country != "India":
            return await _generate_australian_payslips(req, year, month, target_center, country)
        else:
            return await _generate_indian_payslips(req, year, month, target_center)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Payslip generation error: {e}")
        raise HTTPException(500, str(e))


# =======================================
# AUSTRALIAN PAYSLIP GENERATION
# =======================================

async def _generate_australian_payslips(req: PayslipGenRequest, year: int, month: int,
                                         target_center: str, country: str):
    """Generate payslips for Australian / international centers using hourly payroll."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor

    dim = days_in_month(year, month)
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{dim:02d}"
    month_name = datetime(year, month, 1).strftime("%B")

    # Fetch employees from main employees collection
    variants = center_code_variants(target_center)
    emp_query = {"center": {"$in": variants}}

    if req.mode == "single" and req.employeeName:
        emp_name_upper = req.employeeName.strip().upper()
        emp_query["name"] = {"$regex": f"^{emp_name_upper}$", "$options": "i"}

    employees_raw = await db.employees.find(emp_query).to_list(1000)

    if not employees_raw:
        raise HTTPException(404, f"No employees found for {target_center}")

    # Normalize employee data
    employees = []
    for emp in employees_raw:
        emp_id = emp.get("employee_id") or emp.get("id") or emp.get("emp_id") or str(emp.get("_id", ""))
        employees.append({
            "employee_id": emp_id,
            "name": emp.get("name", "Unknown"),
            "category": emp.get("category", emp.get("designation", "CASUAL")),
            "role": emp.get("role", emp.get("designation", "")),
            "hourly_rate": float(emp.get("hourly_rate", 0) or 0),
            "target_takehome_rate": float(emp.get("target_takehome_rate", 0) or emp.get("hourly_rate", 0) or 0),
        })

    # Fetch ALL attendance for this center+month
    attendance_records = await db.international_attendance.find(
        {"center": {"$in": variants}, "date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0}
    ).to_list(50000)

    # Build attendance map: employee_id -> {date -> hours}
    att_map = {}
    for rec in attendance_records:
        eid = rec.get("employee_id", "")
        date = rec.get("date", "")
        hours = float(rec.get("hours_worked", 0) or 0)
        if eid not in att_map:
            att_map[eid] = {}
        att_map[eid][date] = hours

    # Get week ranges for labelling
    week_ranges = get_week_ranges(year, month)

    file_buffers = []

    for emp in employees:
        emp_id = str(emp.get("employee_id") or emp.get("id") or emp.get("name", ""))
        emp_name = emp.get("name", "Unknown")
        category = emp.get("category", "CASUAL")
        role = emp.get("role", "")
        target_takehome = float(emp.get("target_takehome_rate", 0) or emp.get("hourly_rate", 0) or 0)

        # Fetch full employee record for KYC fields
        emp_full = await db.employees.find_one(
            {"name": {"$regex": f"^{emp_name}$", "$options": "i"}, "center": {"$in": variants}},
            {"_id": 0}
        ) or {}
        emp_tfn = emp_full.get("tfn", "")
        emp_photo_url = emp_full.get("photo_url", "")

        # Sum hours for the month
        emp_hours = att_map.get(emp_id, {})
        total_hours = sum(emp_hours.values())

        # Calculate per-week hours for breakdown
        weekly_hours = {}
        for w, (ws, we) in week_ranges.items():
            wh = 0
            d = ws
            while d <= we:
                ds = d.strftime("%Y-%m-%d")
                wh += emp_hours.get(ds, 0)
                d += timedelta(days=1)
            weekly_hours[w] = round(wh, 2)

        # Reverse payroll calculation
        payroll = calculate_payroll_for_employee(target_takehome, total_hours)

        # Generate PDF
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=A4)
        width, height = A4

        # === HEADER ===
        logo_path = ROOT_DIR / "assets" / "pb_logo.png" if ROOT_DIR else None
        if logo_path and logo_path.exists():
            try:
                c.drawImage(str(logo_path), width / 2 - 0.6 * inch, height - 0.9 * inch,
                            width=1.2 * inch, height=0.7 * inch, preserveAspectRatio=True, mask='auto')
            except Exception:
                c.setFont("Helvetica-Bold", 16)
                c.drawCentredString(width / 2, height - 0.5 * inch, "Purnabramha")
        else:
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width / 2, height - 0.5 * inch, "Purnabramha")

        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(width / 2, height - 1.05 * inch, "PURNABRAMHA HOSPITALITY PTY LTD")

        c.setFont("Helvetica", 7)
        c.drawCentredString(width / 2, height - 1.2 * inch, "Perth, Western Australia")

        # Title
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width / 2, height - 1.45 * inch, "PAYSLIP")

        # Pay period subtitle
        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, height - 1.6 * inch,
                            f"Pay Period: 1st {month_name} {year} to {dim} {month_name} {year}")

        # === EMPLOYEE PHOTO (top-right) ===
        _draw_employee_photo(c, emp_photo_url, width - 1.6 * inch, height - 1.55 * inch, 0.8 * inch, 1.0 * inch)

        # === EMPLOYEE DETAILS ===
        y = height - 1.9 * inch
        left_x = 0.5 * inch
        right_x = 4.2 * inch
        c.setFont("Helvetica", 8)

        c.drawString(left_x, y, f"Employee Name: {emp_name}")
        c.drawString(right_x, y, f"Pay Date: {datetime.now().strftime('%d-%m-%Y')}")
        y -= 0.18 * inch

        c.drawString(left_x, y, f"Category: {category}")
        c.drawString(right_x, y, f"Month: {month_name} {year}")
        y -= 0.18 * inch

        c.drawString(left_x, y, f"Role: {role or 'N/A'}")
        c.drawString(right_x, y, f"Center: {target_center}")
        y -= 0.18 * inch

        c.drawString(left_x, y, "Region: Western Australia")
        c.drawString(right_x, y, f"Country: {country}")
        y -= 0.18 * inch

        # TFN line
        if emp_tfn:
            c.drawString(left_x, y, f"TFN: {emp_tfn}")
        y -= 0.15 * inch

        # === MAIN TABLE ===
        box_top = y
        box_bottom = 2.6 * inch
        box_left = 0.4 * inch
        box_right = width - 0.4 * inch
        mid_col = width / 2

        c.setLineWidth(0.5)
        c.rect(box_left, box_bottom, box_right - box_left, box_top - box_bottom)
        c.line(mid_col, box_top, mid_col, box_bottom)

        # --- Left Column: EARNINGS ---
        y = box_top - 0.2 * inch
        left_label_x = box_left + 0.1 * inch
        left_value_x = mid_col - 0.15 * inch

        c.setFont("Helvetica-Bold", 9)
        c.drawString(left_label_x, y, "EARNINGS")
        y -= 0.25 * inch

        c.setFont("Helvetica", 7)

        # Hours breakdown by week
        for w in sorted(weekly_hours.keys()):
            ws, we = week_ranges[w]
            label = f"Week {w} ({ws.strftime('%d %b')} - {we.strftime('%d %b')})"
            c.drawString(left_label_x, y, label)
            c.drawRightString(left_value_x, y, f"{weekly_hours[w]:.1f} hrs")
            y -= 0.16 * inch

        y -= 0.05 * inch
        c.setFont("Helvetica-Bold", 7)
        c.drawString(left_label_x, y, "Total Hours Worked")
        c.drawRightString(left_value_x, y, f"{total_hours:.1f} hrs")
        y -= 0.22 * inch

        c.setFont("Helvetica", 7)
        c.drawString(left_label_x, y, "Take-Home Hourly Rate")
        c.drawRightString(left_value_x, y, f"${target_takehome:.2f}/hr")
        y -= 0.16 * inch

        c.drawString(left_label_x, y, "Gross Hourly Rate (Calculated)")
        c.drawRightString(left_value_x, y, f"${payroll['gross_hourly_rate']:.2f}/hr")
        y -= 0.22 * inch

        c.setFont("Helvetica-Bold", 8)
        c.drawString(left_label_x, y, "GROSS PAY")
        c.drawRightString(left_value_x, y, f"${payroll['gross_pay']:,.2f}")
        y -= 0.16 * inch

        # --- Right Column: DEDUCTIONS & SUPER ---
        y = box_top - 0.2 * inch
        right_label_x = mid_col + 0.1 * inch
        right_value_x = box_right - 0.15 * inch

        c.setFont("Helvetica-Bold", 9)
        c.drawString(right_label_x, y, "TAX DEDUCTIONS")
        y -= 0.25 * inch

        c.setFont("Helvetica", 7)
        deductions = [
            ("PAYG Withholding Tax", f"${payroll['payg_tax']:,.2f}"),
            ("Medicare Levy (2%)", f"${payroll['medicare_levy']:,.2f}"),
        ]
        for label, value in deductions:
            c.drawString(right_label_x, y, label)
            c.drawRightString(right_value_x, y, value)
            y -= 0.16 * inch

        y -= 0.05 * inch
        c.setFont("Helvetica-Bold", 7)
        c.drawString(right_label_x, y, "Total Deductions")
        c.drawRightString(right_value_x, y, f"${payroll['total_deductions']:,.2f}")
        y -= 0.35 * inch

        # Superannuation section
        c.setFont("Helvetica-Bold", 9)
        c.drawString(right_label_x, y, "SUPERANNUATION")
        y -= 0.25 * inch

        c.setFont("Helvetica", 7)
        c.drawString(right_label_x, y, f"Super Guarantee ({SUPER_GUARANTEE_RATE * 100:.0f}%)")
        c.drawRightString(right_value_x, y, f"${payroll['superannuation']:,.2f}")
        y -= 0.16 * inch

        c.setFont("Helvetica", 6)
        c.drawString(right_label_x, y, "(Paid by employer on top of gross)")
        y -= 0.35 * inch

        # Employer cost
        c.setFont("Helvetica-Bold", 8)
        c.drawString(right_label_x, y, "TOTAL EMPLOYER COST")
        c.drawRightString(right_value_x, y, f"${payroll['employer_total_cost']:,.2f}")

        # === NET PAY SECTION ===
        net_y = box_bottom - 0.6 * inch
        c.setFillColor(HexColor("#1a5632"))
        c.rect(box_left, net_y, box_right - box_left, 0.5 * inch, fill=1)
        c.setFillColor(HexColor("#ffffff"))

        c.setFont("Helvetica-Bold", 12)
        c.drawString(box_left + 0.2 * inch, net_y + 0.17 * inch, "NET PAY (Take-Home)")
        c.drawRightString(box_right - 0.2 * inch, net_y + 0.17 * inch,
                          f"AUD ${payroll['net_pay']:,.2f}")

        c.setFillColor(HexColor("#000000"))

        # === CALCULATION SUMMARY BOX ===
        sum_y = net_y - 0.7 * inch
        c.setFont("Helvetica-Bold", 8)
        c.drawString(box_left, sum_y, "Calculation Summary:")
        sum_y -= 0.18 * inch
        c.setFont("Helvetica", 7)
        summaries = [
            f"Gross Pay = Gross Hourly Rate (${payroll['gross_hourly_rate']:.2f}) x Total Hours ({total_hours:.1f}) = ${payroll['gross_pay']:,.2f}",
            f"PAYG Tax = ${payroll['payg_tax']:,.2f}  |  Medicare Levy = ${payroll['medicare_levy']:,.2f}  |  Total Deductions = ${payroll['total_deductions']:,.2f}",
            f"Net Pay = Gross Pay - Total Deductions = ${payroll['gross_pay']:,.2f} - ${payroll['total_deductions']:,.2f} = ${payroll['net_pay']:,.2f}",
            f"Super ({SUPER_GUARANTEE_RATE * 100:.0f}%) = ${payroll['superannuation']:,.2f} (paid by employer, not deducted from net)",
        ]
        for line in summaries:
            c.drawString(box_left + 0.1 * inch, sum_y, line)
            sum_y -= 0.14 * inch

        # === FOOTER / SIGNATURE ===
        signatory = req.signatory or "sandeep"
        if signatory == "jayanti":
            sign_file = "jayanti_sign.png"
            sign_name = "Mrs. Jayanti Kathale"
        else:
            sign_file = "sandeep_sign.png"
            sign_name = "Mr. Sandeep Gadhwal"

        sign_path = ROOT_DIR / "assets" / "signatures" / sign_file if ROOT_DIR else None
        if sign_path and sign_path.exists():
            try:
                c.drawImage(str(sign_path), width - 2.2 * inch, 0.45 * inch,
                            width=1.4 * inch, height=0.7 * inch, preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(width - 0.5 * inch, 1.25 * inch, "Purnabramha")
        c.setFont("Helvetica", 8)
        c.drawRightString(width - 0.5 * inch, 1.1 * inch, "PURNABRAMHA HOSPITALITY PTY LTD")
        c.drawRightString(width - 0.5 * inch, 0.35 * inch, sign_name)
        c.drawRightString(width - 0.5 * inch, 0.22 * inch, "Director")

        c.setFont("Helvetica", 6)
        c.drawString(0.5 * inch, 0.3 * inch, "This is a computer-generated document and does not require a signature.")

        c.save()
        filename = f"Payslip_{emp_name.replace(' ', '_')}_{req.month}.pdf"
        file_buffers.append((filename, pdf_buffer.getvalue(), "pdf"))

    # Return files
    if len(file_buffers) == 1:
        filename, content, _ = file_buffers[0]
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    else:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename, content, _ in file_buffers:
                zf.writestr(filename, content)
        zip_buffer.seek(0)
        zip_filename = f"Payslips_{target_center}_{req.month}.zip"
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
        )


# =======================================
# INDIAN PAYSLIP GENERATION (existing logic)
# =======================================

async def _generate_indian_payslips(req: PayslipGenRequest, year: int, month: int, target_center: str):
    """Generate payslips for Indian centers using monthly salary format."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch

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

    # Track generated files
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

        # Calculate present days from the primary month
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

        # Calculate salary components
        monthly_salary = float(emp.get("currentSalary", 0) or 0)
        mgross = monthly_salary
        basic = mgross * 0.594
        hra = basic * 0.5
        conveyance = 800
        ea_fixed = 200
        gross_70 = mgross * 0.70
        others = max(0, gross_70 - basic - hra - conveyance - ea_fixed)
        basic_annual = basic * 12
        gross_annual = gross_70 * 12
        medical = 1250
        travelling = 3030
        entertainment = 2020
        reimb_total = medical + travelling + entertainment
        esi_amount = total_gross * 0.0075 if total_gross <= 21000 else 0
        total_liabilities = esi_amount if esi_amount > 0 else 0
        month_parts = req.month.split("-")
        month_display = f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(month_parts[1])-1]}-{month_parts[0][2:]}"

        # PDF GENERATION
        if req.fmt == "pdf":
            filename = f"Payslip_{emp_name.replace(' ', '_')}_{req.month}.pdf"
            pdf_buffer = BytesIO()

            c = canvas.Canvas(pdf_buffer, pagesize=A4)
            width, height = A4

            # Header - Logo
            logo_path = ROOT_DIR / "assets" / "pb_logo.png" if ROOT_DIR else None
            if logo_path and logo_path.exists():
                try:
                    c.drawImage(str(logo_path), width/2 - 0.6*inch, height - 0.9*inch, width=1.2*inch, height=0.7*inch, preserveAspectRatio=True, mask='auto')
                except Exception as e:
                    logger.warning(f"Could not add logo: {e}")
                    c.setFont("Helvetica-Bold", 16)
                    c.drawCentredString(width/2, height - 0.5*inch, "Purnabramha")
            else:
                c.setFont("Helvetica-Bold", 16)
                c.drawCentredString(width/2, height - 0.5*inch, "Purnabramha")

            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(width/2, height - 1.05*inch, "MANASWINI FOODS PVT. LTD.")

            c.setFont("Helvetica", 7)
            c.drawCentredString(width/2, height - 1.2*inch, "17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout, Bangalore, Karnataka-560102")

            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(width/2, height - 1.4*inch, "SALARY SLIP")

            # Employee Photo (top-right)
            _draw_employee_photo(c, emp.get("photo_url", ""), width - 1.6*inch, height - 1.55*inch, 0.8*inch, 1.0*inch)

            # Employee Details
            y = height - 1.65*inch
            c.setFont("Helvetica", 8)

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

            # Aadhaar + PAN for Indian payslips
            emp_aadhaar = emp.get("aadhaar", "")
            emp_pan = emp.get("pan", "")
            if emp_aadhaar or emp_pan:
                y -= 0.18*inch
                if emp_aadhaar:
                    c.drawString(left_x, y, f"Aadhaar: {emp_aadhaar}")
                if emp_pan:
                    c.drawString(right_x, y, f"PAN: {emp_pan}")
            y -= 0.15*inch

            # Main Table
            box_top = height - 2.35*inch
            box_bottom = 2.2*inch
            box_left = 0.4*inch
            box_right = width - 0.4*inch
            mid_col = width / 2

            c.setLineWidth(0.5)
            c.rect(box_left, box_bottom, box_right - box_left, box_top - box_bottom)
            c.line(mid_col, box_top, mid_col, box_bottom)

            # Left Column - Earnings
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

            # Right Column - Deductions
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

            # Net Salary Section
            net_y = box_bottom - 0.55*inch
            c.setFillColorRGB(0.95, 0.95, 0.95)
            c.rect(box_left, net_y, box_right - box_left, 0.45*inch, fill=1)
            c.setFillColorRGB(0, 0, 0)

            c.setFont("Helvetica-Bold", 11)
            c.drawString(box_left + 0.15*inch, net_y + 0.15*inch, "NET SALARY")
            c.drawRightString(box_right - 0.15*inch, net_y + 0.15*inch, f"Rs. {total_net:,.2f}")

            # Footer - Signature based on signatory selection
            signatory = req.signatory or "sandeep"
            if signatory == "jayanti":
                sign_file = "jayanti_sign.png"
                sign_name = "Mrs. Jayanti Kathale"
                sign_title = "Director"
            else:
                sign_file = "sandeep_sign.png"
                sign_name = "Mr. Sandeep Gadhwal"
                sign_title = "Director"

            sign_path = ROOT_DIR / "assets" / "signatures" / sign_file if ROOT_DIR else None
            if sign_path and sign_path.exists():
                try:
                    c.drawImage(str(sign_path), width - 2.2*inch, 0.45*inch, width=1.4*inch, height=0.7*inch, preserveAspectRatio=True, mask='auto')
                except Exception as e:
                    logger.warning(f"Could not add signature: {e}")

            c.setFont("Helvetica-Bold", 10)
            c.drawRightString(width - 0.5*inch, 1.25*inch, "Purnabramha")
            c.setFont("Helvetica", 8)
            c.drawRightString(width - 0.5*inch, 1.1*inch, "MANASWINI FOODS PVT. LTD.")
            c.drawRightString(width - 0.5*inch, 0.35*inch, sign_name)
            c.drawRightString(width - 0.5*inch, 0.22*inch, sign_title)

            c.setFont("Helvetica", 6)
            c.drawString(0.5*inch, 0.3*inch, "This is a computer-generated document and does not require a signature.")

            c.save()
            file_buffers.append((filename, pdf_buffer.getvalue(), "pdf"))

        # DOCX GENERATION
        elif req.fmt == "docx":
            from docx import Document
            from docx.shared import Pt, Cm
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.enum.table import WD_TABLE_ALIGNMENT

            doc = Document()

            for section in doc.sections:
                section.top_margin = Cm(1)
                section.bottom_margin = Cm(1)
                section.left_margin = Cm(1.5)
                section.right_margin = Cm(1.5)

            header = doc.add_paragraph()
            header.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = header.add_run("Purnabramha")
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

            title = doc.add_paragraph()
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = title.add_run("SALARY SLIP")
            run.bold = True
            run.font.size = Pt(12)

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

            net_para = doc.add_paragraph()
            run = net_para.add_run(f"G = C-F  NET TAKE: Rs. {total_net:,.2f}")
            run.bold = True
            run.font.size = Pt(12)

            doc.add_paragraph()

            footer = doc.add_paragraph()
            footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            signatory = req.signatory or "sandeep"
            sign_name = "Mrs. Jayanti Kathale" if signatory == "jayanti" else "Mr. Sandeep Gadhwal"
            run = footer.add_run(f"Purnabramha\nMANASWINI FOODS PVT. LTD.\n\n{sign_name}\nDirector")
            run.font.size = Pt(9)

            docx_buffer = BytesIO()
            doc.save(docx_buffer)
            docx_buffer.seek(0)

            filename = f"Payslip_{emp_name.replace(' ', '_')}_{req.month}.docx"
            file_buffers.append((filename, docx_buffer.getvalue(), "docx"))

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
