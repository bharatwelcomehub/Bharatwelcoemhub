# =======================================
# Employees Routes
# Employee CRUD Operations
# =======================================

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import logging
import os
import requests

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Employees"])

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

# Admin access check function (will be set from main server)
has_admin_access = None

def set_has_admin_access(func):
    global has_admin_access
    has_admin_access = func


# =======================================
# OBJECT STORAGE FOR PHOTOS
# =======================================

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
photo_storage_key = None

def init_photo_storage():
    global photo_storage_key
    if photo_storage_key:
        return photo_storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    photo_storage_key = resp.json()["storage_key"]
    return photo_storage_key

def upload_photo(path: str, data: bytes, content_type: str) -> str:
    key = init_photo_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120,
    )
    resp.raise_for_status()
    result = resp.json()
    return result.get("url", result.get("public_url", ""))

def get_photo_url(path: str) -> str:
    key = init_photo_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}/url",
        headers={"X-Storage-Key": key}, timeout=30,
    )
    if resp.status_code == 200:
        return resp.json().get("url", "")
    return ""

# =======================================
# PYDANTIC MODELS
# =======================================

class TokenRequest(BaseModel):
    token: str
    center: str

# =======================================
# EMPLOYEE ENDPOINTS
# =======================================

@router.post("/employees")
async def get_employees(req: TokenRequest):
    """Get employees for a center"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    query = {"center": req.center.upper()}
    
    employees = await db.employees.find(query, {"_id": 0}).sort("name", 1).to_list(1000)
    return {"employees": employees}

@router.post("/mgt_employees_list")
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

@router.post("/mgt_employee_create")
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
        # Document fields
        "aadhaar": data.get("aadhaar", ""),
        "pan": data.get("pan", ""),
        "tfn": data.get("tfn", ""),
        "passport_number": data.get("passport_number", ""),
        "visa_type": data.get("visa_type", ""),
        "blood_group": data.get("blood_group", ""),
        "photo_url": data.get("photo_url", ""),
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.employees.insert_one(employee)
    return {"success": True, "message": "Employee created"}

@router.post("/mgt_employee_update")
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
        # Document fields
        "aadhaar": data.get("aadhaar", ""),
        "pan": data.get("pan", ""),
        "tfn": data.get("tfn", ""),
        "passport_number": data.get("passport_number", ""),
        "visa_type": data.get("visa_type", ""),
        "blood_group": data.get("blood_group", ""),
        "updatedAt": datetime.now(timezone.utc).isoformat()
    }
    
    # Include photo_url only if provided (don't overwrite with empty)
    if data.get("photo_url"):
        update_data["photo_url"] = data["photo_url"]
    
    # Find by name and center
    result = await db.employees.update_one(
        {"name": data.get("name", "").upper()},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(404, "Employee not found")
    
    return {"success": True, "message": "Employee updated"}

@router.post("/mgt_employee_delete")
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

@router.post("/mgt_employee_bulk_upload")
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

@router.get("/employee_template")
async def get_employee_template():
    """Get the Excel template format for bulk employee upload"""
    # Fetch center codes dynamically from DB
    centers = await db.centers.find({"active": {"$ne": False}}, {"_id": 0, "code": 1}).sort("code", 1).to_list(100)
    center_codes = [c["code"] for c in centers if c.get("code")]
    first_center = center_codes[0] if center_codes else "CENTER-1"
    return {
        "columns": [
            {"field": "center", "header": "Center Code", "required": True, "example": first_center, "description": f"Center code ({', '.join(center_codes[:5])}{'...' if len(center_codes) > 5 else ''})"},
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



@router.post("/employee_upload_photo")
async def employee_upload_photo(
    token: str = Form(...),
    employee_name: str = Form(...),
    center: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload passport-size photo for an employee."""
    session = verify_token(token)
    if not session or not has_admin_access(session):
        raise HTTPException(403, "Only Admin can upload employee photos")

    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Only image files are allowed")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "Photo must be under 5MB")

    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    safe_name = employee_name.strip().upper().replace(" ", "_")
    path = f"purnabramha/employee_photos/{center.upper()}/{safe_name}.{ext}"

    try:
        url = upload_photo(path, content, file.content_type)
    except Exception as e:
        logger.error(f"Photo upload failed: {e}")
        raise HTTPException(500, f"Failed to upload photo: {str(e)}")

    # Update employee record with photo URL
    result = await db.employees.update_one(
        {"name": employee_name.strip().upper(), "center": center.upper()},
        {"$set": {"photo_url": url, "photo_path": path, "updatedAt": datetime.now(timezone.utc).isoformat()}}
    )

    return {
        "success": True,
        "photo_url": url,
        "message": f"Photo uploaded for {employee_name}",
        "matched": result.matched_count > 0
    }


@router.post("/employee_report")
async def generate_employee_report(data: dict):
    """Generate employee report PDF with all details, photos, blood groups."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor
    from io import BytesIO
    import urllib.request

    token = data.get("token")
    session = verify_token(token)
    if not session or not has_admin_access(session):
        raise HTTPException(403, "Only Admin can generate employee reports")

    center = data.get("center", "").upper()
    query = {"center": center} if center else {}

    employees = await db.employees.find(query, {"_id": 0}).sort("name", 1).to_list(1000)
    if not employees:
        raise HTTPException(404, "No employees found")

    # Get center country
    center_doc = await db.centers.find_one({"code": center}, {"_id": 0, "country": 1}) if center else None
    country = (center_doc.get("country") or "India") if center_doc else "India"
    is_india = country.lower() == "india" or not country

    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4

    def draw_header(page_y):
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, page_y, "Purnabramha - Employee Directory")
        page_y -= 0.2 * inch
        c.setFont("Helvetica", 9)
        label = f"Center: {center}" if center else "All Centers"
        c.drawCentredString(width / 2, page_y, f"{label} | Country: {country} | Generated: {datetime.now().strftime('%d-%m-%Y')}")
        page_y -= 0.15 * inch
        c.setLineWidth(0.5)
        c.line(0.4 * inch, page_y, width - 0.4 * inch, page_y)
        return page_y - 0.2 * inch

    y = draw_header(height - 0.4 * inch)

    for idx, emp in enumerate(employees):
        # Check if we need a new page (each employee needs ~2.5 inches)
        if y < 2.5 * inch:
            c.showPage()
            y = draw_header(height - 0.4 * inch)

        # Employee card background
        card_top = y + 0.1 * inch
        card_height = 2.0 * inch
        c.setFillColor(HexColor("#F8FAFC"))
        c.setStrokeColor(HexColor("#E2E8F0"))
        c.roundRect(0.4 * inch, card_top - card_height, width - 0.8 * inch, card_height, 4, fill=1, stroke=1)

        # Photo placeholder (right side)
        photo_x = width - 1.8 * inch
        photo_y = card_top - 1.6 * inch
        photo_w = 1.0 * inch
        photo_h = 1.2 * inch

        photo_url = emp.get("photo_url", "")
        photo_drawn = False
        if photo_url:
            try:
                import tempfile
                req = urllib.request.Request(photo_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    img_data = resp.read()
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    tmp.write(img_data)
                    tmp_path = tmp.name
                c.drawImage(tmp_path, photo_x, photo_y, width=photo_w, height=photo_h,
                            preserveAspectRatio=True, mask='auto')
                photo_drawn = True
                os.unlink(tmp_path)
            except Exception:
                pass

        if not photo_drawn:
            c.setFillColor(HexColor("#CBD5E1"))
            c.roundRect(photo_x, photo_y, photo_w, photo_h, 3, fill=1, stroke=0)
            c.setFillColor(HexColor("#64748B"))
            c.setFont("Helvetica", 7)
            c.drawCentredString(photo_x + photo_w / 2, photo_y + photo_h / 2, "No Photo")

        c.setFillColor(HexColor("#000000"))

        # Employee details (left side)
        left_x = 0.6 * inch
        text_y = card_top - 0.25 * inch
        right_col = 3.5 * inch

        # Name (bold, larger)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left_x, text_y, emp.get("name", ""))
        c.setFont("Helvetica", 7)
        c.setFillColor(HexColor("#64748B"))
        c.drawString(left_x + c.stringWidth(emp.get("name", ""), "Helvetica-Bold", 10) + 8, text_y + 1,
                      emp.get("designation", ""))
        c.setFillColor(HexColor("#000000"))
        text_y -= 0.22 * inch

        c.setFont("Helvetica", 7)
        # Row 1
        c.drawString(left_x, text_y, f"Center: {emp.get('center', 'N/A')}")
        c.drawString(right_col, text_y, f"Gender: {emp.get('gender', 'N/A')}")
        text_y -= 0.16 * inch

        # Row 2
        c.drawString(left_x, text_y, f"DOJ: {emp.get('dateOfJoining', 'N/A')}")
        c.drawString(right_col, text_y, f"Mobile: {emp.get('mobile', 'N/A')}")
        text_y -= 0.16 * inch

        # Row 3 - Country-specific ID fields
        if is_india:
            c.drawString(left_x, text_y, f"Aadhaar: {emp.get('aadhaar', 'N/A')}")
            c.drawString(right_col, text_y, f"PAN: {emp.get('pan', 'N/A')}")
        else:
            c.drawString(left_x, text_y, f"TFN: {emp.get('tfn', 'N/A')}")
            c.drawString(right_col, text_y, f"Passport: {emp.get('passport_number', 'N/A')}")
        text_y -= 0.16 * inch

        # Row 4
        if not is_india:
            c.drawString(left_x, text_y, f"Visa: {emp.get('visa_type', 'N/A')}")
        else:
            c.drawString(left_x, text_y, f"Bank: {emp.get('bankName', 'N/A')} | A/c: {emp.get('beneAccNo', 'N/A')}")
        blood = emp.get("blood_group", "")
        c.drawString(right_col, text_y, f"Blood Group: {blood if blood else 'N/A'}")
        text_y -= 0.16 * inch

        # Row 5
        c.drawString(left_x, text_y, f"Email: {emp.get('email', 'N/A')}")
        text_y -= 0.16 * inch

        y = card_top - card_height - 0.15 * inch

    # Footer
    c.setFont("Helvetica", 6)
    c.drawCentredString(width / 2, 0.3 * inch, f"Purnabramha Employee Report | Total: {len(employees)} employees | Confidential")

    c.save()
    pdf_buffer.seek(0)

    from fastapi.responses import Response
    filename = f"Employee_Report_{center or 'ALL'}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
