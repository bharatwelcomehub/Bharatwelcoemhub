# =======================================
# Payroll Routes
# Salary Generation, Payslip Generation, Payroll Lock
# =======================================

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime, timezone
from io import BytesIO
import calendar
import logging
import zipfile

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
    targetCenter: str

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

# =======================================
# UTILITY FUNCTIONS
# =======================================

def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]

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

@router.post("/generate_salary")
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

@router.post("/payslips_generate")
async def payslips_generate(req: PayslipGenRequest):
    """Generate payslips (PDF/DOCX)"""
    session = verify_token(req.token)
    if not session or session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can generate payslips")
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        
        year, month = map(int, req.month.split("-"))
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
                
                # Header
                logo_path = ROOT_DIR / "assets" / "purnabramha_logo.png" if ROOT_DIR else None
                if logo_path and logo_path.exists():
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
                
                c.setFont("Helvetica-Bold", 11)
                c.drawCentredString(width/2, height - 1.4*inch, "SALARY SLIP")
                
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
                
                # Footer
                sign_path = ROOT_DIR / "assets" / "sandeep_gadhwal_signature.png" if ROOT_DIR else None
                if sign_path and sign_path.exists():
                    try:
                        c.drawImage(str(sign_path), width - 2*inch, 0.45*inch, width=1.2*inch, height=0.6*inch, preserveAspectRatio=True, mask='auto')
                    except Exception as e:
                        logger.warning(f"Could not add signature: {e}")
                
                c.setFont("Helvetica-Bold", 10)
                c.drawRightString(width - 0.5*inch, 1.15*inch, "Purnabramha")
                c.setFont("Helvetica", 8)
                c.drawRightString(width - 0.5*inch, 1.0*inch, "MANASWINI FOODS PVT. LTD.")
                c.drawRightString(width - 0.5*inch, 0.35*inch, "Mr. Sandeep Gadhwal")
                c.drawRightString(width - 0.5*inch, 0.22*inch, "Director")
                
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
                run = footer.add_run("Purnabramha\nMANASWINI FOODS PVT. LTD.\n\nMr. Sandeep Gadhwal\nDirector")
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
            
    except Exception as e:
        logger.error(f"Payslip generation error: {e}")
        raise HTTPException(500, str(e))
