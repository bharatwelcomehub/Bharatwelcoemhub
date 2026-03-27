# =======================================
# ROLE-BASED PERMISSION ENGINE
# DB-driven, no hardcoding
# =======================================

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import logging

router = APIRouter(prefix="/api/permissions", tags=["Permissions"])
logger = logging.getLogger(__name__)

db = None
verify_token = None

def set_db(database):
    global db
    db = database

def set_verify_token(vt):
    global verify_token
    verify_token = vt

# ---- Permission Modules and Actions ----
# This defines WHAT can be controlled. Actual assignments are in DB.
PERMISSION_MODULES = {
    "dashboard":      {"actions": ["view"], "label": "Dashboard"},
    "attendance":     {"actions": ["view", "edit", "lock", "unlock"], "label": "Attendance"},
    "payroll":        {"actions": ["view", "preview", "generate", "lock"], "label": "Payroll"},
    "sales":          {"actions": ["view", "edit", "verify"], "label": "Sales & Cash"},
    "expenses":       {"actions": ["view", "create", "edit", "delete", "attach"], "label": "Expenses"},
    "employees":      {"actions": ["view", "create", "edit", "delete"], "label": "Employees"},
    "masters":        {"actions": ["view", "create", "edit", "delete"], "label": "Master Data"},
    "roles":          {"actions": ["view", "manage"], "label": "Role Management"},
    "centers":        {"actions": ["view", "create", "edit", "delete"], "label": "Centers"},
    "managers":       {"actions": ["view", "create", "edit", "delete"], "label": "Managers"},
    "hr_letters":     {"actions": ["view", "generate", "download"], "label": "HR Letters"},
    "transfers":      {"actions": ["view", "create", "accept", "reject"], "label": "Transfers"},
    "reports":        {"actions": ["view", "download"], "label": "Reports"},
    "mis":            {"actions": ["view", "download"], "label": "MIS Dashboard"},
    "international":  {"actions": ["view", "edit", "export"], "label": "International Attendance"},
    "franchise":      {"actions": ["view", "manage", "download"], "label": "Franchise"},
    "invoices":       {"actions": ["view", "create", "download"], "label": "Invoices"},
    "billing":        {"actions": ["view", "create", "edit", "cancel"], "label": "Billing / POS"},
    "recipes":        {"actions": ["view", "create", "edit"], "label": "Recipes"},
    "bookings":       {"actions": ["view", "create", "edit"], "label": "Bookings"},
    "loans":          {"actions": ["view", "create", "edit"], "label": "Loans"},
    "accounts":       {"actions": ["view", "edit", "download"], "label": "Accounts"},
}

# ---- Default Role Templates ----
DEFAULT_ROLES = {
    "super_admin": {
        "name": "Super Admin",
        "description": "Full system access. Can manage all modules, roles, and centers.",
        "is_system": True,
        "scope": "all_centers",
        "permissions": {mod: actions["actions"] for mod, actions in PERMISSION_MODULES.items()}
    },
    "admin": {
        "name": "Admin",
        "description": "Wide access across modules. Cannot manage Super Admin accounts.",
        "is_system": True,
        "scope": "all_centers",
        "permissions": {mod: actions["actions"] for mod, actions in PERMISSION_MODULES.items() if mod != "roles"}
    },
    "center_manager": {
        "name": "Center Manager",
        "description": "Operational access for their own center only.",
        "is_system": True,
        "scope": "own_center",
        "permissions": {
            "dashboard": ["view"], "attendance": ["view", "edit"], "sales": ["view", "edit"],
            "expenses": ["view", "create", "edit", "attach"], "employees": ["view"],
            "reports": ["view"], "transfers": ["view", "create"], "recipes": ["view"],
            "bookings": ["view", "create", "edit"], "billing": ["view", "create", "edit"],
        }
    },
    "super_manager": {
        "name": "Super Manager",
        "description": "Enhanced manager with multi-center view and reporting access.",
        "is_system": True,
        "scope": "assigned_centers",
        "permissions": {
            "dashboard": ["view"], "attendance": ["view", "edit", "lock"],
            "payroll": ["view", "preview"], "sales": ["view", "edit", "verify"],
            "expenses": ["view", "create", "edit", "delete", "attach"],
            "employees": ["view", "edit"], "reports": ["view", "download"],
            "mis": ["view", "download"], "transfers": ["view", "create", "accept"],
            "billing": ["view", "create", "edit", "cancel"],
        }
    },
    "accountant": {
        "name": "Accountant",
        "description": "Finance and reporting access across centers.",
        "is_system": True,
        "scope": "all_centers",
        "permissions": {
            "dashboard": ["view"], "sales": ["view"], "expenses": ["view", "attach"],
            "payroll": ["view", "preview", "generate"], "reports": ["view", "download"],
            "mis": ["view", "download"], "invoices": ["view", "create", "download"],
            "accounts": ["view", "edit", "download"], "loans": ["view", "create", "edit"],
        }
    },
    "franchise_owner": {
        "name": "Franchise Owner",
        "description": "View-only access to own franchise data. Download reports and documents.",
        "is_system": True,
        "scope": "own_franchise",
        "permissions": {
            "dashboard": ["view"], "sales": ["view"], "expenses": ["view"],
            "reports": ["view", "download"], "mis": ["view", "download"],
            "franchise": ["view", "download"], "invoices": ["view", "download"],
        }
    },
    "staff": {
        "name": "Staff / Restricted",
        "description": "Limited access to assigned features only.",
        "is_system": True,
        "scope": "own_center",
        "permissions": {
            "dashboard": ["view"], "attendance": ["view"],
            "billing": ["view", "create"],
        }
    },
}


# ---- Core Permission Check Function ----

async def check_permission(session: dict, module: str, action: str) -> bool:
    """Check if user has a specific permission. Used by all endpoints."""
    if not session:
        return False
    
    # Super Admin always has full access
    if session.get("is_super_admin"):
        return True
    
    # Admin has wide access (everything except role management)
    if session.get("is_admin"):
        if module == "roles" and action == "manage":
            return False
        return True
    
    # Look up user's role from DB
    email = session.get("email", "")
    if not email:
        # Fallback to old role system
        old_roles = session.get("roles", {})
        module_map = {
            "attendance": "attendance", "sales": "sales_cash", "expenses": "sales_cash",
            "payroll": "hr", "employees": "hr", "hr_letters": "hr",
            "franchise": "franchise", "accounts": "accounting", "mis": "accounting",
            "reports": "accounting", "loans": "accounting",
        }
        mapped = module_map.get(module, module)
        return old_roles.get(mapped, False) or old_roles.get("accounting", False)
    
    manager = await db.managers.find_one({"email": email}, {"_id": 0})
    if not manager:
        return False
    
    role_key = manager.get("role_key", "")
    if not role_key:
        # Fallback: use old roles field
        old_roles = manager.get("roles", {})
        module_map = {
            "attendance": "attendance", "sales": "sales_cash", "expenses": "sales_cash",
            "payroll": "hr", "employees": "hr", "hr_letters": "hr",
            "franchise": "franchise", "accounts": "accounting", "mis": "accounting",
            "reports": "accounting", "loans": "accounting",
        }
        mapped = module_map.get(module, module)
        return old_roles.get(mapped, False) or old_roles.get("accounting", False)
    
    # Look up role permissions from DB
    role = await db.master_roles.find_one({"key": role_key}, {"_id": 0})
    if not role:
        return False
    
    perms = role.get("permissions", {})
    module_perms = perms.get(module, [])
    return action in module_perms


async def get_user_permissions(session: dict) -> dict:
    """Get full permission map for current user"""
    if not session:
        return {}
    
    if session.get("is_super_admin"):
        return {mod: actions["actions"] for mod, actions in PERMISSION_MODULES.items()}
    
    if session.get("is_admin"):
        perms = {mod: actions["actions"] for mod, actions in PERMISSION_MODULES.items()}
        perms["roles"] = ["view"]  # Admin can view but not manage roles
        return perms
    
    email = session.get("email", "")
    if email:
        manager = await db.managers.find_one({"email": email}, {"_id": 0})
        if manager:
            role_key = manager.get("role_key", "")
            if role_key:
                role = await db.master_roles.find_one({"key": role_key}, {"_id": 0})
                if role:
                    return role.get("permissions", {})
    
    # Fallback: map old roles
    old_roles = session.get("roles", {})
    perms = {"dashboard": ["view"]}
    if old_roles.get("attendance"):
        perms["attendance"] = ["view", "edit"]
    if old_roles.get("sales_cash"):
        perms["sales"] = ["view", "edit"]
        perms["expenses"] = ["view", "create", "edit"]
    if old_roles.get("hr"):
        perms["payroll"] = ["view", "preview"]
        perms["employees"] = ["view", "edit"]
        perms["hr_letters"] = ["view", "generate"]
    if old_roles.get("accounting"):
        perms["accounts"] = ["view", "edit", "download"]
        perms["mis"] = ["view", "download"]
        perms["reports"] = ["view", "download"]
    if old_roles.get("franchise"):
        perms["franchise"] = ["view", "manage"]
    return perms


def get_user_scope(session: dict) -> dict:
    """Get user's data scope (which centers they can access)"""
    if not session:
        return {"type": "none", "centers": []}
    
    if session.get("is_super_admin") or session.get("is_admin"):
        return {"type": "all_centers", "centers": []}
    
    center = session.get("center", "")
    return {"type": "own_center", "centers": [center]}


# ---- API ENDPOINTS ----

@router.get("/modules")
async def get_permission_modules(token: str):
    """Get all permission modules and their actions"""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    return {"modules": PERMISSION_MODULES}


@router.get("/my-permissions")
async def get_my_permissions(token: str):
    """Get current user's permissions"""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    
    perms = await get_user_permissions(session)
    scope = get_user_scope(session)
    
    role_key = ""
    role_name = ""
    if session.get("is_super_admin"):
        role_key = "super_admin"
        role_name = "Super Admin"
    elif session.get("is_admin"):
        role_key = "admin"
        role_name = "Admin"
    else:
        email = session.get("email", "")
        if email:
            mgr = await db.managers.find_one({"email": email}, {"_id": 0})
            if mgr:
                role_key = mgr.get("role_key", "center_manager")
                role_doc = await db.master_roles.find_one({"key": role_key}, {"_id": 0})
                role_name = role_doc["name"] if role_doc else role_key
    
    return {
        "permissions": perms,
        "scope": scope,
        "role_key": role_key,
        "role_name": role_name
    }


@router.post("/roles/list")
async def list_roles(data: dict):
    """Get all roles"""
    session = verify_token(data.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")
    
    roles = await db.master_roles.find({}, {"_id": 0}).to_list(100)
    return {"roles": roles}


@router.post("/roles/create")
async def create_role(data: dict):
    """Create a custom role"""
    session = verify_token(data.get("token"))
    if not session or not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin can create roles")
    
    key = data.get("key", "").strip().lower().replace(" ", "_")
    name = data.get("name", "").strip()
    if not key or not name:
        raise HTTPException(400, "key and name are required")
    
    existing = await db.master_roles.find_one({"key": key})
    if existing:
        raise HTTPException(400, f"Role '{key}' already exists")
    
    role = {
        "key": key,
        "name": name,
        "description": data.get("description", ""),
        "is_system": False,
        "scope": data.get("scope", "own_center"),
        "permissions": data.get("permissions", {}),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": session.get("managerName", ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": session.get("managerName", ""),
    }
    
    await db.master_roles.insert_one(role)
    return {"success": True, "message": f"Role '{name}' created"}


@router.post("/roles/update")
async def update_role(data: dict):
    """Update a role's permissions"""
    session = verify_token(data.get("token"))
    if not session or not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin can update roles")
    
    key = data.get("key", "")
    update = {"updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": session.get("managerName", "")}
    
    if "name" in data:
        update["name"] = data["name"]
    if "description" in data:
        update["description"] = data["description"]
    if "scope" in data:
        update["scope"] = data["scope"]
    if "permissions" in data:
        update["permissions"] = data["permissions"]
    if "is_active" in data:
        update["is_active"] = data["is_active"]
    
    result = await db.master_roles.update_one({"key": key}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(404, f"Role '{key}' not found")
    
    return {"success": True, "message": "Role updated"}


@router.post("/roles/assign")
async def assign_role(data: dict):
    """Assign a role to a manager"""
    session = verify_token(data.get("token"))
    if not session or not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin can assign roles")
    
    email = data.get("email", "").strip().lower()
    role_key = data.get("role_key", "").strip()
    assigned_centers = data.get("assigned_centers", [])
    franchise_id = data.get("franchise_id", "")
    
    if not email or not role_key:
        raise HTTPException(400, "email and role_key required")
    
    role = await db.master_roles.find_one({"key": role_key}, {"_id": 0})
    if not role:
        raise HTTPException(404, f"Role '{role_key}' not found")
    
    update = {
        "role_key": role_key,
        "role_name": role["name"],
        "assigned_centers": assigned_centers,
        "franchise_id": franchise_id,
        "role_updated_at": datetime.now(timezone.utc).isoformat(),
        "role_updated_by": session.get("managerName", ""),
    }
    
    result = await db.managers.update_one({"email": email}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(404, f"Manager '{email}' not found")
    
    logger.info(f"Role '{role_key}' assigned to {email}")
    return {"success": True, "message": f"Role '{role['name']}' assigned to {email}"}


@router.post("/roles/seed-defaults")
async def seed_default_roles(data: dict):
    """Seed default roles into master_roles collection"""
    session = verify_token(data.get("token"))
    if not session or not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin")
    
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    
    for key, template in DEFAULT_ROLES.items():
        existing = await db.master_roles.find_one({"key": key})
        if not existing:
            await db.master_roles.insert_one({
                "key": key,
                **template,
                "is_active": True,
                "created_at": now,
                "created_by": "System",
                "updated_at": now,
                "updated_by": "System",
            })
            created += 1
    
    return {"success": True, "created": created, "total_roles": len(DEFAULT_ROLES)}
