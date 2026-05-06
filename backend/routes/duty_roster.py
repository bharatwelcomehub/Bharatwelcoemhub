"""Daily Duty Roster — per-center attendance/duty tracker.

Center Managers (and Admin / Super-Admin / Accounts) can:
  - Pull the active employee list for their center on a given date
  - Mark each row with Duty Time, In Time, and a Status code
    (PRESENT / LEAVE / W = Weekly Off / A = Absent)
  - Save the roster — historical days are persisted for audit & payroll tie-in

Roster doc shape (one per center+date):
{
  center, date (YYYY-MM-DD),
  rows: [{ employee_id?, name, designation, group, duty_time, in_time, status }],
  updated_at, updated_by
}
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

router = APIRouter(prefix="/api/duty-roster", tags=["Duty Roster"])

db = None
verify_token = None


def set_db(_db):
    global db
    db = _db


def set_verify_token(func):
    global verify_token
    verify_token = func


# -- Designation → group mapping (drives the section bands in the printed roster)
GROUP_RULES = [
    ("Manager", ["manager", "supervisor", "incharge"]),
    ("Service", ["service", "captain", "waiter", "steward", "barista", "host"]),
    ("Kitchen", ["chef", "cook", "commie", "tr chef", "kitchen"]),
    ("Housekeeping", ["dish", "wash", "clean", "housekeep", "helper", "utility"]),
]


def _group_for(designation: str) -> str:
    d = (designation or "").lower()
    for grp, keywords in GROUP_RULES:
        if any(k in d for k in keywords):
            return grp
    return "Others"


def _check_access(session: dict, center: str) -> None:
    if not session:
        raise HTTPException(401, "Invalid token")
    if session.get("is_super_admin") or session.get("is_admin"):
        return
    roles = session.get("roles") or {}
    if roles.get("accounting"):
        return
    role_key = (session.get("role_key") or "").lower()
    sess_center = (session.get("center") or session.get("franchise_center") or "").upper()
    if role_key in ("center_manager", "manager") and sess_center == (center or "").upper():
        return
    raise HTTPException(403, "Center Manager / Admin / Accounts only")


class GetRosterRequest(BaseModel):
    token: str
    center: str
    date: str  # YYYY-MM-DD


class SaveRosterRequest(BaseModel):
    token: str
    center: str
    date: str
    rows: List[dict]


@router.post("/get")
async def get_roster(req: GetRosterRequest):
    """Return current employee list (grouped) + saved roster for center+date."""
    session = verify_token(req.token)
    _check_access(session, req.center)

    code = req.center.upper()
    # Load all active employees for this center
    employees = await db.employees.find(
        {
            "center": code,
            "$or": [
                {"status": {"$in": ["active", "Active", "ACTIVE"]}},
                {"status": {"$exists": False}},
                {"isActive": {"$ne": False}},
            ],
        },
        {"_id": 0, "name": 1, "designation": 1, "employeeId": 1},
    ).sort("name", 1).to_list(500)

    # Existing saved roster (if any)
    saved = await db.duty_rosters.find_one(
        {"center": code, "date": req.date}, {"_id": 0}
    )
    saved_rows = (saved or {}).get("rows", [])
    saved_by_name = {(r.get("name") or "").upper(): r for r in saved_rows}

    # Compose final rows: every active employee + any ad-hoc rows from saved
    rows: List[dict] = []
    for emp in employees:
        nm = (emp.get("name") or "").upper()
        prev = saved_by_name.pop(nm, None)
        rows.append({
            "employee_id": emp.get("employeeId", ""),
            "name": emp.get("name", "").upper() or "",
            "designation": (emp.get("designation") or "").upper(),
            "group": _group_for(emp.get("designation") or ""),
            "duty_time": (prev or {}).get("duty_time", ""),
            "in_time": (prev or {}).get("in_time", ""),
            "status": (prev or {}).get("status", ""),
        })
    # Carry over any ad-hoc rows that don't match an active employee
    for leftover in saved_by_name.values():
        rows.append({
            "employee_id": leftover.get("employee_id", ""),
            "name": (leftover.get("name") or "").upper(),
            "designation": (leftover.get("designation") or "").upper(),
            "group": leftover.get("group") or _group_for(leftover.get("designation") or ""),
            "duty_time": leftover.get("duty_time", ""),
            "in_time": leftover.get("in_time", ""),
            "status": leftover.get("status", ""),
            "ad_hoc": True,
        })

    return {
        "success": True,
        "center": code,
        "date": req.date,
        "rows": rows,
        "saved": bool(saved),
        "updated_at": (saved or {}).get("updated_at"),
        "updated_by": (saved or {}).get("updated_by"),
    }


@router.post("/save")
async def save_roster(req: SaveRosterRequest):
    """Persist the manager's edits. Replaces the rows array atomically."""
    session = verify_token(req.token)
    _check_access(session, req.center)

    code = req.center.upper()
    actor = session.get("name") or session.get("mobile") or "system"
    now = datetime.now(timezone.utc).isoformat()

    cleaned: List[dict] = []
    for r in req.rows or []:
        nm = (r.get("name") or "").strip().upper()
        if not nm:
            continue
        cleaned.append({
            "employee_id": r.get("employee_id") or "",
            "name": nm,
            "designation": (r.get("designation") or "").upper(),
            "group": r.get("group") or _group_for(r.get("designation") or ""),
            "duty_time": (r.get("duty_time") or "").strip().upper(),
            "in_time": (r.get("in_time") or "").strip().upper(),
            "status": (r.get("status") or "").strip().upper(),
        })

    await db.duty_rosters.update_one(
        {"center": code, "date": req.date},
        {"$set": {
            "center": code, "date": req.date, "rows": cleaned,
            "updated_at": now, "updated_by": actor,
        }},
        upsert=True,
    )
    return {"success": True, "saved": len(cleaned), "updated_at": now, "updated_by": actor}


@router.post("/history")
async def list_history(payload: dict = Body(...)):
    """Return the list of dates that already have a saved roster (for the date-picker chip strip)."""
    session = verify_token(payload.get("token"))
    center = (payload.get("center") or "").upper()
    _check_access(session, center)
    docs = await db.duty_rosters.find(
        {"center": center}, {"_id": 0, "date": 1, "updated_at": 1, "updated_by": 1}
    ).sort("date", -1).limit(60).to_list(60)
    return {"success": True, "history": docs}
