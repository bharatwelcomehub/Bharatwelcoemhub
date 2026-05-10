# =======================================
# MENU CONFIGURATION (Super Admin sidebar customization)
# =======================================
# Lets Super Admins reorder menu items and adjust which roles can see each one
# without redeploying. The defaults live in the React Dashboard; this collection
# only stores OVERRIDES (delta from defaults), keyed by item_id / category_id.
#
# Schema (single document per scope, default scope = "global"):
# {
#   "_id": "global",
#   "categories": {
#     "<category_id>": {
#       "order": 0,                          # int (smaller = earlier)
#       "visible_roles": ["admin", ...]      # if empty/missing => use code defaults
#     }
#   },
#   "items": {
#     "<item_path>": {
#       "category_id": "mgt",                # optional re-parenting (move item to another category)
#       "order": 3,
#       "visible_roles": ["super_admin", "accounting"]
#     }
#   },
#   "updated_at": "...",
#   "updated_by": "..."
# }
#
# Role identifiers the UI uses (kept stable across sessions):
#   super_admin, admin, accounting, mgt, attendance, sales_cash, hr,
#   operations, franchise, billing, international, center_manager,
#   franchise_owner, staff

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging

router = APIRouter(prefix="/api/menu-config", tags=["MenuConfig"])
logger = logging.getLogger(__name__)

db = None
verify_token = None

VALID_ROLES = {
    "super_admin", "admin", "accounting", "mgt", "attendance", "sales_cash",
    "hr", "operations", "franchise", "billing", "international",
    "center_manager", "franchise_owner", "staff",
}


def set_db(database):
    global db
    db = database


def set_verify_token(vt):
    global verify_token
    verify_token = vt


class CategoryOverride(BaseModel):
    order: Optional[int] = None
    visible_roles: Optional[List[str]] = None


class ItemOverride(BaseModel):
    category_id: Optional[str] = None
    order: Optional[int] = None
    visible_roles: Optional[List[str]] = None


class SaveMenuConfigBody(BaseModel):
    token: str
    categories: Optional[Dict[str, CategoryOverride]] = None
    items: Optional[Dict[str, ItemOverride]] = None


def _empty_config() -> dict:
    return {"_id": "global", "categories": {}, "items": {}}


def _sanitize_roles(roles: Optional[List[str]]) -> Optional[List[str]]:
    if roles is None:
        return None
    cleaned = [r for r in roles if isinstance(r, str) and r in VALID_ROLES]
    # de-dup, preserve order
    seen = set()
    out = []
    for r in cleaned:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


@router.get("")
async def get_menu_config(token: str):
    """Return the current menu override config. Any authenticated user can read."""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    doc = await db.menu_configs.find_one({"_id": "global"}, {"_id": 0})
    if not doc:
        return {"categories": {}, "items": {}, "updated_at": None, "updated_by": None}
    return {
        "categories": doc.get("categories", {}),
        "items": doc.get("items", {}),
        "updated_at": doc.get("updated_at"),
        "updated_by": doc.get("updated_by"),
    }


@router.post("/save")
async def save_menu_config(body: SaveMenuConfigBody):
    """Replace the menu override config. Super Admin only."""
    session = verify_token(body.token)
    if not session or not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin can edit the menu configuration")

    categories_clean: Dict[str, dict] = {}
    if body.categories:
        for cat_id, ov in body.categories.items():
            entry = {}
            if ov.order is not None:
                entry["order"] = int(ov.order)
            roles = _sanitize_roles(ov.visible_roles)
            if roles is not None:
                entry["visible_roles"] = roles
            if entry:
                categories_clean[cat_id] = entry

    items_clean: Dict[str, dict] = {}
    if body.items:
        for item_path, ov in body.items.items():
            entry = {}
            if ov.category_id:
                entry["category_id"] = ov.category_id
            if ov.order is not None:
                entry["order"] = int(ov.order)
            roles = _sanitize_roles(ov.visible_roles)
            if roles is not None:
                entry["visible_roles"] = roles
            if entry:
                items_clean[item_path] = entry

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "_id": "global",
        "categories": categories_clean,
        "items": items_clean,
        "updated_at": now,
        "updated_by": session.get("managerName") or session.get("email") or "Super Admin",
    }
    await db.menu_configs.replace_one({"_id": "global"}, doc, upsert=True)
    logger.info(f"Menu config saved by {doc['updated_by']} ({len(categories_clean)} cats, {len(items_clean)} items)")
    return {"success": True, "categories": categories_clean, "items": items_clean, "updated_at": now}


@router.post("/reset")
async def reset_menu_config(data: dict):
    """Clear all menu overrides (back to code defaults). Super Admin only."""
    session = verify_token(data.get("token", ""))
    if not session or not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin")
    await db.menu_configs.delete_one({"_id": "global"})
    return {"success": True, "message": "Menu config reset to defaults"}


@router.get("/valid-roles")
async def get_valid_roles(token: str):
    """List of role identifiers that the UI can offer in role checkboxes."""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    return {
        "roles": [
            {"key": "super_admin", "label": "Super Admin"},
            {"key": "admin", "label": "Admin"},
            {"key": "mgt", "label": "Management"},
            {"key": "accounting", "label": "Accounts"},
            {"key": "attendance", "label": "Attendance"},
            {"key": "sales_cash", "label": "Sales & Cash"},
            {"key": "hr", "label": "HR"},
            {"key": "operations", "label": "Operations"},
            {"key": "franchise", "label": "Franchise"},
            {"key": "billing", "label": "Billing / POS"},
            {"key": "international", "label": "International"},
            {"key": "center_manager", "label": "Center Manager"},
            {"key": "franchise_owner", "label": "Franchise Owner"},
            {"key": "staff", "label": "Staff"},
        ]
    }
