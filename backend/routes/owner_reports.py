"""Owner Reports — gated reports for franchise owners.

Accounts team must flag a center+month as 'ready_for_owner' before owners
can view PIB/GST/Sales/Expense reports for that month. Unflagged → owner
sees "Current month in progress" message.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Body
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging

from .attendance_dashboard import get_session, check_super_admin, check_admin_access
from utils.gst import compute_gst_from_rows, gst_rate_for

logger = logging.getLogger(__name__)


def check_release_access(session) -> bool:
    """Who can release / revoke a month's visibility to franchise owners?
    Super Admin, Admin (is_admin), Accountant role, or anyone with
    'accounts' or 'reports' action rights.
    """
    if not session:
        return False
    if session.get("is_super_admin") or session.get("is_admin"):
        return True
    role_key = (session.get("role_key") or "").lower()
    if role_key in ("super_admin", "admin", "accountant"):
        return True
    roles = session.get("roles") or {}
    # Accounts-team roles carry an 'accounts' or 'reports' action set
    if roles.get("accounts") or roles.get("reports") or roles.get("mis"):
        return True
    return False

_mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _mongo[os.environ["DB_NAME"]]

router = APIRouter(prefix="/api/owner-reports", tags=["owner-reports"])


def _month_range(month: str) -> tuple[str, str]:
    """YYYY-MM → (YYYY-MM-01, YYYY-MM-lastday)."""
    y, m = int(month[:4]), int(month[5:7])
    start = f"{y:04d}-{m:02d}-01"
    # last day of the month
    if m == 12:
        next_first = datetime(y + 1, 1, 1)
    else:
        next_first = datetime(y, m + 1, 1)
    end_day = (next_first - timedelta(days=1)).day
    return start, f"{y:04d}-{m:02d}-{end_day:02d}"


@router.post("/set-visibility")
async def set_visibility(req: dict = Body(...)):
    """Release / revoke a month for franchise-owner viewing.
    Allowed for Super Admin, Admin, Accountant (and anyone with accounts/reports role).
    Body: {token, center, month, ready: bool, note?}"""
    session = await get_session(req.get("token"))
    if not session or not check_release_access(session):
        raise HTTPException(403, "Only Super Admin, Admin, or Accounts team can release reports to owners")
    center = req["center"]
    month = req["month"]
    ready = bool(req.get("ready", True))
    now = datetime.now(timezone.utc).isoformat()
    await db.owner_report_visibility.update_one(
        {"center": center, "month": month},
        {"$set": {
            "center": center, "month": month, "ready": ready,
            "note": req.get("note", ""),
            "updated_by": session.get("managerName", ""),
            "updated_at": now,
        }, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return {"success": True}


@router.post("/release-all")
async def release_all(req: dict = Body(...)):
    """Bulk release / revoke a month for ALL active centers.
    Body: {token, month, ready: bool, note?, exclude?: [centers]}"""
    session = await get_session(req.get("token"))
    if not session or not check_release_access(session):
        raise HTTPException(403, "Only Super Admin, Admin, or Accounts team can bulk-release reports")
    month = req["month"]
    ready = bool(req.get("ready", True))
    exclude = set(req.get("exclude") or [])
    note = req.get("note") or f"Bulk {'released' if ready else 'revoked'} by {session.get('managerName','admin')} on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    now = datetime.now(timezone.utc).isoformat()

    centers = await db.centers.find(
        {"$or": [{"active": True}, {"active": {"$exists": False}}]},
        {"_id": 0, "code": 1},
    ).to_list(500)
    codes = [c["code"] for c in centers if c.get("code") and c["code"] not in exclude]

    updated = 0
    for code in codes:
        await db.owner_report_visibility.update_one(
            {"center": code, "month": month},
            {"$set": {
                "center": code, "month": month, "ready": ready, "note": note,
                "updated_by": session.get("managerName", ""), "updated_at": now,
            }, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        updated += 1
    return {"success": True, "updated": updated, "month": month, "ready": ready, "centers": codes}



@router.post("/visibility-status")
async def visibility_status(req: dict = Body(...)):
    """List visibility flags (Accounts view). Optional center filter."""
    session = await get_session(req.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")
    q = {}
    if req.get("center") and req["center"] != "all":
        q["center"] = req["center"]
    rows = await db.owner_report_visibility.find(q, {"_id": 0}).sort("month", -1).to_list(5000)
    return {"rows": rows}


async def _compute_monthly_report(center: str, month: str) -> dict:
    """Build a fully-computed monthly report packet for an owner."""
    start_date, end_date = _month_range(month)
    # Sales
    sales = await db.daily_sales.find(
        {"center": center, "date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0}
    ).to_list(1000)
    gst_calc = compute_gst_from_rows(sales, None, center)
    total_sales = round(sum(float(r.get("total_sale", 0) or 0) for r in sales), 2)
    aggregator = gst_calc["aggregator_sale"]
    eligible = gst_calc["eligible_base"]
    gst_amount = gst_calc["gst_amount"]
    cash = round(sum(float(r.get("total_cash_sale", 0) or 0) for r in sales), 2)
    online = round(sum(float(r.get("total_online_sale", 0) or 0) for r in sales), 2)
    
    # Expenses
    expenses = await db.expenses.find(
        {"center": center, "date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0}
    ).to_list(2000)
    total_expenses = round(sum(float(r.get("amount", 0) or 0) for r in expenses), 2)
    # Category breakdown
    by_cat = {}
    for e in expenses:
        k = (e.get("expense_type") or "OTHER").upper()
        by_cat[k] = by_cat.get(k, 0) + float(e.get("amount", 0) or 0)
    expense_breakdown = [{"category": k, "amount": round(v, 2)} for k, v in sorted(by_cat.items(), key=lambda kv: -kv[1])]
    
    # Commissions — sum every commission-related field the same way Center Accounts
    # and the MG Payout report do, so all surfaces show identical figures.
    # Includes platform commission + commission GST + TDS withheld at source.
    comms = await db.monthly_commissions.find(
        {"center": center, "month": month}, {"_id": 0}
    ).to_list(100)
    def _comm_total(c: dict) -> float:
        return (
            float(c.get("commission_amount", 0) or 0)
            + float(c.get("other_deductions", 0) or 0)
            + float(c.get("gst_tax_deductions", 0) or 0)
            + float(c.get("tds", 0) or 0)
        )
    total_commission = round(sum(_comm_total(c) for c in comms), 2)
    # Commission GST component (kept separate so we can show "Eligible Rev Share Base"
    # = Sales − Commission − Commission GST − GST). Prefer the explicit
    # gst_tax_deductions field on the upload; if a row lacks that field, fall back
    # to 18% of the base commission_amount so the rule documented in the UI
    # ("18% GST on commission") is always honoured for India.
    def _comm_gst(c: dict) -> float:
        gtd = float(c.get("gst_tax_deductions", 0) or 0)
        if gtd > 0:
            return gtd
        base = float(c.get("commission_amount", 0) or 0)
        return round(base * 0.18, 2) if base > 0 else 0.0
    commission_gst = round(sum(_comm_gst(c) for c in comms), 2)
    commission_breakdown = [
        {"platform": c.get("platform"),
         "gross": round(float(c.get("gross_amount", 0)), 2),
         "commission": round(float(c.get("other_deductions", 0)), 2),
         "net_payout": round(float(c.get("net_payout", 0)), 2)}
        for c in comms
    ]
    
    # GST liability (for PIB)
    gst_liab = await db.gst_liabilities.find_one(
        {"center": center, "month": month}, {"_id": 0}
    )
    
    # Net Revenue = Total Sales − (Commission incl. comm GST) − GST on Sales
    # GST is removed because it's a govt pass-through. Expenses are NOT subtracted
    # at this level — see net_pl below for actual P/L.
    net_revenue = round(total_sales - total_commission - gst_amount, 2)
    # Backwards-compat alias (existing consumers still read 'pnl' = Net Revenue).
    pnl = net_revenue

    # Country detection — needed to surface Profitability for Australia centers.
    center_doc = await db.centers.find_one({"code": center}, {"_id": 0, "country": 1})
    country = (center_doc or {}).get("country") or ("Australia" if str(center).upper().endswith("-PERTH") else "India")
    # Net P/L = Net Revenue − Expenses (true P/L, what the franchise actually earns)
    net_pl = round(net_revenue - total_expenses, 2)
    # For Australia: Profitability is the 80/20 base (Net Revenue − Expenses) — equivalent to net_pl.
    profitability = net_pl if country == "Australia" else None
    # Eligible Rev Share Base — explicit breakout for the dashboard:
    #   = Sales − Commission − Commission GST − GST on Sales
    # For India this equals net_revenue (since total_commission already includes
    # commission GST via the sum-of-deduction-fields above).
    eligible_rev_share_base = round(total_sales - (total_commission - commission_gst) - commission_gst - gst_amount, 2)

    return {
        "center": center, "month": month,
        "country": country,
        "sales": {
            "total": total_sales, "cash": cash, "online": online,
            "swiggy": round(sum(float(r.get("swiggy_sale", r.get("swiggy", 0)) or 0) for r in sales), 2),
            "zomato": round(sum(float(r.get("zomato_sale", r.get("zomato", 0)) or 0) for r in sales), 2),
            "doordash": round(sum(float(r.get("doordash_sale", r.get("doordash", 0)) or 0) for r in sales), 2),
            "card": round(sum(float(r.get("card_sale", 0) or 0) for r in sales), 2),
            "phone_pe": round(sum(float(r.get("phone_pe_sale", 0) or 0) for r in sales), 2),
            "days": len(sales),
        },
        "gst": {
            "rate_pct": int(gst_calc["rate"] * 100),
            "eligible_base": eligible,
            "aggregator_sale": aggregator,
            "gst_amount": gst_amount,
            "liability_paid": bool(gst_liab.get("paid")) if gst_liab else False,
            "liability_paid_date": gst_liab.get("paid_date") if gst_liab else None,
        },
        "expenses": {
            "total": total_expenses,
            "rows": len(expenses),
            "by_category": expense_breakdown,
        },
        "commissions": {
            "total": total_commission,
            "commission_gst": commission_gst,
            "by_platform": commission_breakdown,
        },
        "pnl": pnl,                                  # = net_revenue (kept for back-compat)
        "net_revenue": net_revenue,
        "net_pl": net_pl,                            # true P/L: net_revenue − expenses
        "eligible_rev_share_base": eligible_rev_share_base,
        "profitability": profitability,
    }


@router.post("/monthly-report")
async def monthly_report(req: dict = Body(...)):
    """Owner-facing monthly report. Blocked unless the center+month is flagged
    ready_for_owner by Accounts/Admin. Admin/SA can always view.
    Body: {token, center, month}"""
    session = await get_session(req.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")
    center = req["center"]
    month = req["month"]
    # Staff = anyone in the release-access bracket (Super Admin, Admin,
    # Accountant, accounts/reports role). They bypass the visibility gate and
    # can view/release ANY center.
    is_staff = check_release_access(session)

    vis = await db.owner_report_visibility.find_one(
        {"center": center, "month": month}, {"_id": 0}
    )
    ready = bool(vis and vis.get("ready"))

    if not is_staff and not ready:
        return {
            "success": True,
            "visibility": {"ready": False, "reason": "Current month in progress. Accounts team has not yet approved visibility."},
            "center": center, "month": month,
        }

    data = await _compute_monthly_report(center, month)
    # Staff always see the report; expose an admin_bypass flag so the UI can
    # render content while still surfacing the "not yet flagged" state.
    effective_ready = ready or is_staff
    return {
        "success": True,
        "visibility": {
            "ready": effective_ready,
            "flagged_ready": ready,
            "admin_bypass": (is_staff and not ready),
            "can_release": is_staff,
            "note": vis.get("note", "") if vis else "",
        },
        **data,
    }
