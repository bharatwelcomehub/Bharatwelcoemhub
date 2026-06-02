"""Expense Adjustment routes — Center Accounts feature.

An adjustment lets Admin / Super Admin / Accountant carve a portion of a
recorded expense out of the current month's profitability without ever
modifying the original `expenses` row. Used for prepaid rent, advance
utilities, security deposits, etc.

Routes (all under /api/center-accounts/adjustments):
  POST /list      → list adjustments for a center+month (or date range)
  POST /create    → create a new adjustment tied to an expense row
  POST /update/{adjustment_id}
  POST /delete/{adjustment_id}
  POST /report    → cross-center / cross-month report for accounting review
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server import db                # type: ignore
from routes.center_accounts import check_access

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/center-accounts/adjustments", tags=["expense-adjustments"])


ADJUSTMENT_TYPES = [
    "Next Month Rent Paid in Advance",
    "Advance Utility Payment",
    "Security Deposit",
    "Future Expense Allocation",
    "Manual Adjustment",
    "Other",
]


def _can_write(session: dict) -> bool:
    """Admin / Super Admin / Accountant only."""
    if session.get("is_super_admin") or session.get("is_admin"):
        return True
    role_key = (session.get("role_key") or "").lower()
    roles = session.get("roles") or {}
    if role_key in {"admin", "super_admin", "accountant"}:
        return True
    return bool(roles.get("admin") or roles.get("accounting") or roles.get("accounts"))


def _ensure_can_view(session: dict, center: str):
    """View permission: SA/Admin = any center; others must match own center."""
    if session.get("is_super_admin") or session.get("is_admin"):
        return
    own = (session.get("center") or "").upper()
    if center.upper() != own:
        raise HTTPException(403, "Cannot view adjustments for another center")


class BaseReq(BaseModel):
    token: str


class CreateReq(BaseReq):
    expense_id: str
    center: str
    month: str                               # YYYY-MM (derived from expense.date)
    adjustment_amount: float
    adjustment_type: str
    adjustment_reason: Optional[str] = ""


class UpdateReq(BaseReq):
    adjustment_amount: Optional[float] = None
    adjustment_type: Optional[str] = None
    adjustment_reason: Optional[str] = None


class ListReq(BaseReq):
    center: Optional[str] = None
    month: Optional[str] = None              # YYYY-MM
    expense_id: Optional[str] = None


class ReportReq(BaseReq):
    centers: Optional[List[str]] = None
    from_month: Optional[str] = None         # YYYY-MM inclusive
    to_month: Optional[str] = None           # YYYY-MM inclusive


@router.post("/types")
async def list_types(req: BaseReq):
    """Static list of allowed adjustment_type values."""
    await check_access(req.token)
    return {"types": ADJUSTMENT_TYPES}


@router.post("/list")
async def list_adjustments(req: ListReq):
    session = await check_access(req.token)
    q: dict = {}
    if req.center:
        _ensure_can_view(session, req.center)
        q["center"] = req.center.upper()
    elif not (session.get("is_super_admin") or session.get("is_admin")):
        own = session.get("center")
        if own:
            q["center"] = own.upper()
    if req.month:
        q["month"] = req.month
    if req.expense_id:
        q["expense_id"] = req.expense_id
    rows = await db.expense_adjustments.find(q, {"_id": 0}).sort("created_at", -1).to_list(2000)
    total = round(sum(float(r.get("adjustment_amount", 0) or 0) for r in rows), 2)
    return {"items": rows, "total_adjustments": total, "count": len(rows)}


@router.post("/create")
async def create_adjustment(req: CreateReq):
    session = await check_access(req.token)
    if not _can_write(session):
        raise HTTPException(403, "Only Admin / Super Admin / Accountant can create adjustments")
    if not req.expense_id or not req.center or not req.month:
        raise HTTPException(400, "expense_id, center and month are required")
    if req.adjustment_amount <= 0:
        raise HTTPException(400, "adjustment_amount must be > 0 — leave the field blank to skip an adjustment")
    if req.adjustment_type not in ADJUSTMENT_TYPES:
        raise HTTPException(400, f"adjustment_type must be one of {ADJUSTMENT_TYPES}")

    # Snapshot the underlying expense row for the report + audit. The
    # adjustment is meaningless if the expense doesn't exist.
    expense = await db.expenses.find_one({"id": req.expense_id}, {"_id": 0})
    if not expense:
        # legacy expenses may use different id field
        expense = await db.expenses.find_one({"expense_id": req.expense_id}, {"_id": 0})
    if not expense:
        # /api/sales/expenses surfaces the Mongo _id as `expense_id` to the
        # frontend, so support lookup-by-ObjectId too.
        try:
            from bson import ObjectId
            expense = await db.expenses.find_one({"_id": ObjectId(req.expense_id)}, {"_id": 0})
        except Exception:
            expense = None
    if not expense:
        raise HTTPException(404, f"Expense {req.expense_id} not found")

    original_amount = float(expense.get("amount", 0) or 0)
    if req.adjustment_amount > original_amount:
        raise HTTPException(400, f"Adjustment ({req.adjustment_amount}) cannot exceed the original expense amount ({original_amount}).")

    # If this expense already has adjustments, ensure cumulative <= original
    existing = await db.expense_adjustments.find(
        {"expense_id": req.expense_id}, {"adjustment_amount": 1, "_id": 0}
    ).to_list(100)
    existing_total = sum(float(r.get("adjustment_amount", 0) or 0) for r in existing)
    if existing_total + req.adjustment_amount > original_amount:
        raise HTTPException(400, f"Cumulative adjustments ({existing_total + req.adjustment_amount}) would exceed the original expense ({original_amount}). Remaining capacity: {round(original_amount - existing_total, 2)}.")

    doc = {
        "adjustment_id": str(uuid.uuid4()),
        "expense_id": req.expense_id,
        "center": req.center.upper(),
        "month": req.month,
        "expense_date": expense.get("date", ""),
        "expense_head": expense.get("expense_type") or expense.get("category") or "Other",
        "original_expense_amount": round(original_amount, 2),
        "adjustment_amount": round(float(req.adjustment_amount), 2),
        "adjustment_type": req.adjustment_type,
        "adjustment_reason": (req.adjustment_reason or "").strip(),
        "created_by": session.get("managerName") or session.get("mobile") or "Unknown",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": None,
        "updated_by": None,
    }
    await db.expense_adjustments.insert_one(doc)
    doc.pop("_id", None)
    return {"success": True, "adjustment": doc}


@router.post("/update/{adjustment_id}")
async def update_adjustment(adjustment_id: str, req: UpdateReq):
    session = await check_access(req.token)
    if not _can_write(session):
        raise HTTPException(403, "Only Admin / Super Admin / Accountant can edit adjustments")
    existing = await db.expense_adjustments.find_one({"adjustment_id": adjustment_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Adjustment not found")

    updates = {}
    if req.adjustment_amount is not None:
        if req.adjustment_amount <= 0:
            raise HTTPException(400, "adjustment_amount must be > 0")
        # Re-check the cumulative cap excluding this row
        siblings = await db.expense_adjustments.find(
            {"expense_id": existing["expense_id"], "adjustment_id": {"$ne": adjustment_id}},
            {"adjustment_amount": 1, "_id": 0},
        ).to_list(100)
        siblings_total = sum(float(r.get("adjustment_amount", 0) or 0) for r in siblings)
        orig = float(existing.get("original_expense_amount") or 0)
        if siblings_total + req.adjustment_amount > orig:
            raise HTTPException(400, f"Cumulative adjustments would exceed the original expense ({orig}).")
        updates["adjustment_amount"] = round(float(req.adjustment_amount), 2)
    if req.adjustment_type is not None:
        if req.adjustment_type not in ADJUSTMENT_TYPES:
            raise HTTPException(400, f"adjustment_type must be one of {ADJUSTMENT_TYPES}")
        updates["adjustment_type"] = req.adjustment_type
    if req.adjustment_reason is not None:
        updates["adjustment_reason"] = req.adjustment_reason.strip()

    if not updates:
        return {"success": True, "adjustment": existing}

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    updates["updated_by"] = session.get("managerName") or session.get("mobile") or "Unknown"
    await db.expense_adjustments.update_one({"adjustment_id": adjustment_id}, {"$set": updates})
    refreshed = await db.expense_adjustments.find_one({"adjustment_id": adjustment_id}, {"_id": 0})
    return {"success": True, "adjustment": refreshed}


@router.post("/delete/{adjustment_id}")
async def delete_adjustment(adjustment_id: str, req: BaseReq):
    session = await check_access(req.token)
    if not _can_write(session):
        raise HTTPException(403, "Only Admin / Super Admin / Accountant can delete adjustments")
    res = await db.expense_adjustments.delete_one({"adjustment_id": adjustment_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Adjustment not found")
    return {"success": True}


@router.post("/report")
async def adjustments_report(req: ReportReq):
    """Cross-center / cross-month report — for the dedicated Expense
    Adjustments Report screen. Returns rows + totals.
    """
    session = await check_access(req.token)
    q: dict = {}
    if req.centers:
        q["center"] = {"$in": [c.upper() for c in req.centers]}
    elif not (session.get("is_super_admin") or session.get("is_admin")):
        own = session.get("center")
        if own:
            q["center"] = own.upper()
    if req.from_month or req.to_month:
        rng: dict = {}
        if req.from_month:
            rng["$gte"] = req.from_month
        if req.to_month:
            rng["$lte"] = req.to_month
        q["month"] = rng

    rows = await db.expense_adjustments.find(q, {"_id": 0}).sort("expense_date", 1).to_list(5000)

    # Pair with raw monthly expense totals so the report can show
    # Total Expenses / Adjustments / Adjusted Expenses side-by-side.
    by_center_month: dict = {}
    for r in rows:
        key = (r["center"], r["month"])
        by_center_month.setdefault(key, []).append(r)

    summary_rows = []
    for (center, month), bucket in by_center_month.items():
        start = f"{month}-01"
        # Cheap last-day-of-month
        y, m = month.split("-")
        nm = int(m) + 1
        ny = int(y) + (1 if nm > 12 else 0)
        nm = 1 if nm > 12 else nm
        end = f"{ny:04d}-{nm:02d}-01"
        exps = await db.expenses.find(
            {"center": center, "date": {"$gte": start, "$lt": end}},
            {"amount": 1, "_id": 0},
        ).to_list(2000)
        total_exp = round(sum(float(e.get("amount", 0) or 0) for e in exps), 2)
        total_adj = round(sum(float(b.get("adjustment_amount", 0) or 0) for b in bucket), 2)
        summary_rows.append({
            "center": center,
            "month": month,
            "total_expenses": total_exp,
            "total_adjustments": total_adj,
            "adjusted_expenses": round(total_exp - total_adj, 2),
            "row_count": len(bucket),
        })

    total_adjustments = round(sum(r["total_adjustments"] for r in summary_rows), 2)
    total_expenses    = round(sum(r["total_expenses"] for r in summary_rows), 2)
    adjusted_expenses = round(total_expenses - total_adjustments, 2)

    return {
        "items": rows,
        "summary_by_center_month": sorted(summary_rows, key=lambda r: (r["center"], r["month"])),
        "totals": {
            "total_expenses": total_expenses,
            "total_adjustments": total_adjustments,
            "adjusted_expenses": adjusted_expenses,
            "count": len(rows),
        },
    }
