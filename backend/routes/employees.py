# =======================================
# Employees Routes
# Employee CRUD Operations
# =======================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import logging

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
