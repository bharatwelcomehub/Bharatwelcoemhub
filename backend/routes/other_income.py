# =======================================
# Other Income Routes — memo-only inflows
# (loans taken, vendor refunds, franchisee repayments, etc.)
# =======================================
from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime, timezone
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/other-income", tags=["Other Income"])

# Database & token verification injected from main server
db = None
verify_token_async = None

def set_db(database):
    global db
    db = database

def set_verify_token_async(func):
    global verify_token_async
    verify_token_async = func


# Allowed manual categories (loan_taken is reserved for auto-entries)
MANUAL_CATEGORIES = {"vendor_refund", "franchisee_repayment", "other"}
ALL_CATEGORIES = MANUAL_CATEGORIES | {"loan_taken"}


async def check_access(token):
    if not verify_token_async:
        raise HTTPException(500, "Auth not configured")
    session = await verify_token_async(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    return session


def _can_write(session):
    return (
        session.get("is_super_admin") or session.get("is_admin")
        or session.get("role_key") in ("accountant", "accounts")
        or (session.get("permissions") or {}).get("accounting") is True
    )


def _generate_id() -> str:
    return f"OI-{uuid.uuid4().hex[:10].upper()}"


# =======================================
# CREATE — manual entry by accounts/admin
# =======================================
@router.post("/create")
async def create_other_income(data: dict):
    token = data.get("token")
    session = await check_access(token)
    if not _can_write(session):
        raise HTTPException(403, "Only Admin / Accountant can add Other Income entries")

    center = (data.get("center") or "").upper().strip()
    if not center:
        raise HTTPException(400, "center is required")
    try:
        amount = float(data.get("amount") or 0)
    except (TypeError, ValueError):
        raise HTTPException(400, "amount must be a number")
    if amount <= 0:
        raise HTTPException(400, "amount must be positive")

    date_str = (data.get("date") or "").strip()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD")

    category = (data.get("category") or "other").lower().strip()
    if category not in MANUAL_CATEGORIES:
        raise HTTPException(400, f"category must be one of {sorted(MANUAL_CATEGORIES)}")

    reason = (data.get("reason") or "").strip()
    if not reason:
        raise HTTPException(400, "reason is required")

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "income_id": _generate_id(),
        "center": center,
        "date": date_str,
        "month": date_str[:7],
        "amount": round(amount, 2),
        "category": category,
        "reason": reason,
        "linked_loan_id": None,
        "auto_generated": False,
        "created_at": now,
        "created_by": session.get("managerName") or session.get("mobile", ""),
    }
    await db.other_income.insert_one(doc)
    doc.pop("_id", None)
    return {"success": True, "income": doc}


# =======================================
# LIST — by center, optional month filter
# =======================================
@router.post("/list")
async def list_other_income(data: dict):
    token = data.get("token")
    session = await check_access(token)

    center = (data.get("center") or "").upper().strip()
    month = (data.get("month") or "").strip()  # YYYY-MM optional

    # Franchise Owner / Manager can only see own center
    if not (session.get("is_super_admin") or session.get("is_admin")
            or session.get("role_key") in ("accountant", "accounts")):
        own = (session.get("center") or "").upper()
        if own and center and own != center:
            raise HTTPException(403, "You can only view your own center")
        if not center:
            center = own

    if not center:
        raise HTTPException(400, "center is required")

    query = {"center": {"$regex": f"^{center}$", "$options": "i"}}
    if month:
        query["month"] = month

    rows = await db.other_income.find(query, {"_id": 0}).sort("date", 1).to_list(2000)
    total = round(sum(float(r.get("amount", 0) or 0) for r in rows), 2)

    by_cat: dict = {}
    for r in rows:
        c = r.get("category", "other")
        by_cat[c] = round(by_cat.get(c, 0) + float(r.get("amount", 0) or 0), 2)

    return {
        "success": True,
        "rows": rows,
        "total": total,
        "count": len(rows),
        "by_category": by_cat,
        "center": center,
        "month": month or None,
    }


# =======================================
# DELETE — manual rows only (auto rows must be deleted via the loan)
# =======================================
@router.post("/delete/{income_id}")
async def delete_other_income(income_id: str, data: dict):
    token = data.get("token")
    session = await check_access(token)
    if not _can_write(session):
        raise HTTPException(403, "Only Admin / Accountant can delete Other Income entries")

    doc = await db.other_income.find_one({"income_id": income_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Other Income entry not found")

    if doc.get("auto_generated") and not session.get("is_super_admin"):
        raise HTTPException(
            400,
            "Auto-generated entries (e.g. Loan Taken) can only be removed by deleting the source loan, "
            "or by a Super Admin override."
        )

    await db.other_income.delete_one({"income_id": income_id})
    return {"success": True, "message": "Other Income entry deleted"}


# =======================================
# Internal helpers used by other modules
# =======================================
async def auto_create_loan_taken_income(center: str, amount: float, loan_date: str,
                                         source_center: str, loan_id: str, created_by: str):
    """Called from loan_entries.create_loan_entry when a TAKEN loan is created."""
    if db is None:
        return
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "income_id": _generate_id(),
        "center": center.upper(),
        "date": loan_date,
        "month": (loan_date or "")[:7],
        "amount": round(float(amount), 2),
        "category": "loan_taken",
        "reason": f"Loan taken from {source_center}",
        "linked_loan_id": loan_id,
        "auto_generated": True,
        "created_at": now,
        "created_by": created_by,
    }
    await db.other_income.insert_one(doc)


async def cascade_delete_for_loan(loan_ids: list):
    """Called from loan_entries.delete_loan_entry / bulk_delete to remove auto rows."""
    if db is None or not loan_ids:
        return 0
    result = await db.other_income.delete_many(
        {"linked_loan_id": {"$in": list(loan_ids)}, "auto_generated": True}
    )
    return result.deleted_count


async def get_other_income_summary(center: str, month: Optional[str] = None) -> dict:
    """Used by Sales Breakdown / PIB to render the memo block.
    
    Returns: {
      total: float,
      by_category: {loan_taken, vendor_refund, franchisee_repayment, other}
      rows: [...]
    }
    """
    if db is None:
        return {"total": 0, "by_category": {}, "rows": []}
    query = {"center": {"$regex": f"^{center}$", "$options": "i"}}
    if month:
        query["month"] = month
    rows = await db.other_income.find(query, {"_id": 0}).sort("date", 1).to_list(2000)
    total = round(sum(float(r.get("amount", 0) or 0) for r in rows), 2)
    by_cat: dict = {}
    for r in rows:
        c = r.get("category", "other")
        by_cat[c] = round(by_cat.get(c, 0) + float(r.get("amount", 0) or 0), 2)
    return {"total": total, "by_category": by_cat, "rows": rows}


async def get_loans_given_summary(center: str, month: Optional[str] = None) -> dict:
    """Used by PIB / dashboards to render the 'Loan Given to Other Center'
    memo (no destination name).

    Loans are balance-sheet items (cumulative ledger), NOT period flows. So
    the optional ``month`` argument is interpreted as **"include all loans
    given on or before the last day of this month"** — the same lifetime view
    the Loan Entries page shows. This guarantees Center Accounts, MIS
    Dashboard, Franchise Owner Dashboard and the Loan Entries page all show
    the same Loans Given total / outstanding for any given period.
    """
    if db is None:
        return {"total": 0, "count": 0, "rows": [], "outstanding": 0, "repaid": 0}
    query = {"center": {"$regex": f"^{center}$", "$options": "i"}, "loan_type": "given"}
    if month:
        # cumulative — every loan given on or before YYYY-MM-31
        query["loan_date"] = {"$lte": f"{month}-31"}
    loans = await db.loan_entries.find(query, {"_id": 0}).to_list(2000)
    total = round(sum(float(le.get("amount", 0) or 0) for le in loans), 2)
    repaid_total = round(sum(float(le.get("total_repaid", 0) or 0) for le in loans), 2)
    outstanding_total = round(total - repaid_total, 2)
    sanitized = []
    for le in loans:
        amt = float(le.get("amount", 0) or 0)
        rp = float(le.get("total_repaid", 0) or 0)
        sanitized.append({
            "loan_id": le.get("loan_id"),
            "loan_date": le.get("loan_date"),
            "amount": amt,
            "repaid": round(rp, 2),
            "outstanding": round(amt - rp, 2),
            "reason": "Loan Given to Other Center",
            "status": le.get("status"),
        })
    return {
        "total": total, "count": len(loans), "rows": sanitized,
        "outstanding": outstanding_total, "repaid": repaid_total,
    }


async def get_loans_taken_summary(center: str, month: Optional[str] = None) -> dict:
    """Used by PIB / dashboards to render the 'Loan Taken' memo for the
    borrower center. Includes source center name and outstanding/repaid
    status.

    Same cumulative-up-to-month semantics as ``get_loans_given_summary`` —
    loans are balance-sheet items, not period flows, so the ``month`` arg
    means "include every loan taken on or before YYYY-MM-31". This keeps
    the Loan Entries page, Center Accounts, MIS Dashboard, FO Dashboard and
    PIB all showing the same Loans Taken total / outstanding.
    """
    if db is None:
        return {"total": 0, "count": 0, "rows": [], "outstanding": 0, "repaid": 0}
    query = {"center": {"$regex": f"^{center}$", "$options": "i"}, "loan_type": "taken"}
    if month:
        query["loan_date"] = {"$lte": f"{month}-31"}
    loans = await db.loan_entries.find(query, {"_id": 0}).to_list(2000)
    total = round(sum(float(le.get("amount", 0) or 0) for le in loans), 2)
    repaid_total = round(sum(float(le.get("total_repaid", 0) or 0) for le in loans), 2)
    outstanding_total = round(total - repaid_total, 2)
    rows = []
    for le in loans:
        amt = float(le.get("amount", 0) or 0)
        rp = float(le.get("total_repaid", 0) or 0)
        rows.append({
            "loan_id": le.get("loan_id"),
            "loan_date": le.get("loan_date"),
            "amount": amt,
            "repaid": round(rp, 2),
            "outstanding": round(amt - rp, 2),
            "source_center": le.get("source_center", ""),
            "reason": le.get("reason", "Loan taken"),
            "status": le.get("status"),
        })
    return {
        "total": total, "count": len(loans), "rows": rows,
        "outstanding": outstanding_total, "repaid": repaid_total,
    }


async def get_other_income_by_month(center: str) -> dict:
    """Sum Other Income per month for a center.
    Used by WC chain to treat Other Income as non-operating cash inflow that
    adds to the closing WC (so it flows into next month's Opening WC).
    
    Returns: { 'YYYY-MM': total_amount, ... }
    """
    if db is None:
        return {}
    rows = await db.other_income.find(
        {"center": {"$regex": f"^{center}$", "$options": "i"}},
        {"_id": 0, "month": 1, "amount": 1}
    ).to_list(5000)
    out: dict = {}
    for r in rows:
        m = r.get("month") or ""
        if not m:
            continue
        out[m] = round(out.get(m, 0) + float(r.get("amount", 0) or 0), 2)
    return out
