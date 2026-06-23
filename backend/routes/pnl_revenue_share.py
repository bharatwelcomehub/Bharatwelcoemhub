"""P&L Revenue Share Overview + Revenue Share Projection.

Two surfaces:
  POST /api/center-accounts/pnl-revenue-share-overview
  POST /api/center-accounts/revenue-share-projection
  POST /api/center-accounts/pnl-revenue-share-overview/export-pdf
  POST /api/center-accounts/pnl-revenue-share-overview/export-excel
  POST /api/center-accounts/revenue-share-projection/export-pdf
  POST /api/center-accounts/revenue-share-projection/export-excel

All endpoints reuse the canonical data sources that already power /payout-summary
(daily_sales, expenses, monthly_commissions, payout_payments) so numbers stay
consistent with the rest of Center Accounts.
"""

from __future__ import annotations

import io
import os
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Body, HTTPException, Response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/center-accounts", tags=["pnl-revenue-share"])

# Globals injected from server.py at startup (mirrors visa.py pattern).
_db = None  # type: ignore
_verify_token = None  # type: ignore
_verify_token_async = None  # type: ignore


def set_db(database):
    global _db
    _db = database


def set_verify_token(fn):
    global _verify_token
    _verify_token = fn


def set_verify_token_async(fn):
    global _verify_token_async
    _verify_token_async = fn


GST_RATE = 18.0  # Indian standard GST on services


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
async def _auth(token: str) -> dict:
    if not token:
        raise HTTPException(401, "Missing token")
    if _verify_token_async:
        sess = await _verify_token_async(token)
    elif _verify_token:
        sess = _verify_token(token)
    else:
        raise HTTPException(500, "Auth verifier not wired")
    if not sess:
        raise HTTPException(401, "Invalid or expired token")
    return sess


def _months_between(from_month: str, to_month: str) -> List[str]:
    """Inclusive list of YYYY-MM between two months."""
    months = []
    current = datetime.strptime(from_month + "-01", "%Y-%m-%d")
    end = datetime.strptime(to_month + "-01", "%Y-%m-%d")
    while current <= end:
        months.append(current.strftime("%Y-%m"))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return months


def _fy_range(fy_label: str) -> tuple[str, str]:
    """Convert "2024-25" → ("2024-04", "2025-03"). Falls back to current FY if invalid."""
    try:
        a, b = fy_label.split("-")
        start_y = int(a)
        # 2-digit end year support ("24-25") and 4-digit ("2024-2025")
        end_y = int(b) if len(b) == 4 else int(f"20{b}") if int(b) < 100 else int(b)
        return f"{start_y}-04", f"{end_y}-03"
    except Exception:
        now = datetime.now()
        if now.month >= 4:
            return f"{now.year}-04", f"{now.year + 1}-03"
        return f"{now.year - 1}-04", f"{now.year}-03"


async def _month_row(center: str, month: str, franchise: dict,
                     revenue_share_pct: float, gst_on: bool) -> dict:
    """Build one row of P&L Revenue Share Overview for (center, month).

    Mirrors the formulas used by /payout-summary so numbers reconcile with the
    rest of Center Accounts.
    """
    year, mon = month.split("-")
    start_date = f"{year}-{mon}-01"
    if int(mon) == 12:
        end_date = f"{int(year) + 1}-01-01"
    else:
        end_date = f"{year}-{int(mon) + 1:02d}-01"

    # — Sale —
    sales_records = await _db.daily_sales.find(
        {"center": center, "date": {"$gte": start_date, "$lt": end_date}},
        {"total_sale": 1, "swiggy_sale": 1, "zomato_sale": 1, "doordash_sale": 1,
         "swiggy": 1, "zomato": 1, "doordash": 1},
    ).to_list(200)
    total_sale = sum(r.get("total_sale", 0) or 0 for r in sales_records)

    # — Expenses (raw) — adjustments applied separately downstream
    expense_records = await _db.expenses.find(
        {"center": center, "date": {"$gte": start_date, "$lt": end_date}},
        {"amount": 1},
    ).to_list(2000)
    total_expenses = sum(e.get("amount", 0) or 0 for e in expense_records)

    # — Commission & GST (canonical helpers) —
    from utils.commissions import get_total_commissions
    from utils.gst import compute_gst_from_rows
    comm = await get_total_commissions(_db, center, month)
    total_commission = comm["total"]
    franchise_country = (franchise or {}).get("country", "India")
    gst_calc = compute_gst_from_rows(sales_records, country=franchise_country, center=center)
    gst_on_sales = gst_calc["gst_amount"]

    # — Revenue Share Base — honour per-month GST treatment toggle
    try:
        from utils.gst_treatment import get_gst_treatment_flag
        include_gst_in_revenue = await get_gst_treatment_flag(center, month)
    except Exception:
        include_gst_in_revenue = False
    if include_gst_in_revenue:
        revenue_share_base = round(total_sale - total_commission, 2)
    else:
        revenue_share_base = round(total_sale - total_commission - gst_on_sales, 2)

    # Clamp for share calc but keep raw signed value for column display
    base_for_share = max(0, revenue_share_base)
    revenue_share_amount = round(base_for_share * (revenue_share_pct / 100.0), 2)
    rs_plus_gst = round(revenue_share_amount * (1 + GST_RATE / 100.0), 2) if gst_on else revenue_share_amount

    # — MG (India only, when applicable) —
    mg_amount = 0.0
    try:
        from utils.mg import calculate_mg  # type: ignore
    except Exception:
        calculate_mg = None  # type: ignore[assignment]
    mg_applicable = bool((franchise or {}).get("mg_calculation_applicable", True))
    if franchise and franchise_country.lower() == "india" and mg_applicable and calculate_mg:
        try:
            total_inv = float(franchise.get("total_investment", 0) or 0)
            ff = float(franchise.get("franchise_fee", 0) or 0)
            wc = float(franchise.get("working_capital", 0) or 0)
            if total_inv <= 0:
                total_inv = ff + wc
            mg_data = calculate_mg(total_inv, franchise.get("setup_costs") or {}, ff, wc)
            mg_amount = float(mg_data.get("monthly_mg", 0) or 0)
        except Exception as ex:
            logger.warning(f"pnl-revenue-share: MG calc failed for {center} {month}: {ex}")
    mg_plus_gst = round(mg_amount * (1 + GST_RATE / 100.0), 2) if gst_on else mg_amount

    # — Amount Paid (actual disbursed) from payout_payments —
    payments = await _db.payout_payments.find(
        {"center": center.upper(), "month": month}, {"_id": 0},
    ).to_list(200)
    amount_paid = round(sum(p.get("amount", 0) or 0 for p in payments), 2)

    # — Eligible Adjustments —
    # Sum of expense_adjustments rows flagged include_in_revenue_share_calculation=True
    # for this center+month. These reduce the Profit Share MFPL (founder spec).
    eligible_adj = await _eligible_adjustments(center, month)

    # — Profit Share MFPL —
    # Per founder spec 2026-02:
    #   Profit Share MFPL = Sale − Expenses − Amount Paid − Eligible Adjustments
    # If no payment was disbursed that month, surface the *theoretical* outflow
    # (max of RS+GST, MG+GST) so the founder still sees true cost.
    pnl = round(total_sale - total_expenses - total_commission - gst_on_sales, 2)
    if amount_paid > 0:
        outflow = amount_paid
    else:
        outflow = max(rs_plus_gst, mg_plus_gst)
    profit_share_mfpl = round(total_sale - total_expenses - outflow - eligible_adj, 2)

    return {
        "month": month,
        "sale": round(total_sale, 2),
        "expenses": round(total_expenses, 2),
        "pnl": pnl,
        "revenue_share_base": revenue_share_base,
        "revenue_share_pct": revenue_share_pct,
        "revenue_share_amount": revenue_share_amount,
        "revenue_share_plus_gst": rs_plus_gst,
        "mg_amount": round(mg_amount, 2),
        "mg_plus_gst": round(mg_plus_gst, 2),
        "amount_paid": amount_paid,
        "eligible_adjustments": round(eligible_adj, 2),
        "profit_share_mfpl": profit_share_mfpl,
        # diagnostics (not shown in grid but useful in PDF footer)
        "_meta": {
            "commission": round(total_commission, 2),
            "gst_on_sales": round(gst_on_sales, 2),
            "include_gst_in_revenue": include_gst_in_revenue,
            "payments_count": len(payments),
        },
    }


async def _eligible_adjustments(center: str, month: str) -> float:
    """Sum of expense adjustments flagged include_in_revenue_share_calculation
    for the given center+month. Default-true so existing adjustments keep
    behaving as before. Returns 0 on any error so the grid never breaks.
    """
    try:
        cur = _db.expense_adjustments.find(
            {
                "center": {"$regex": f"^{center}$", "$options": "i"},
                "month": month,
                "$or": [
                    {"include_in_revenue_share_calculation": True},
                    {"include_in_revenue_share_calculation": {"$exists": False}},
                ],
            },
            {"adjustment_amount": 1},
        )
        rows = await cur.to_list(2000)
        return round(sum(float(r.get("adjustment_amount") or 0) for r in rows), 2)
    except Exception:
        return 0.0


async def _month_row_profit_share(center: str, month: str, franchise: dict,
                                  franchise_share_pct: float) -> dict:
    """Profit-Share model row for overseas / non-India centers.

    Columns: Month · Sale · Expenses · Commissions · Commission GST ·
    Profit Share Base · Franchise Share (X%) · MFPL Share (100-X%) ·
    Amount Paid · Pending · Status.

    Formula:
      Profit Share Base = Sale − Expenses − Commissions
        (+ Commission GST when it is flagged as recoverable in adjustments)
      Franchise Share   = Base × franchise_share_pct
      MFPL Share        = Base × (100 − franchise_share_pct)
      Pending           = max(0, Franchise Share − Amount Paid)
      Status            = Paid / Partial / Pending
    """
    year, mon = month.split("-")
    start_date = f"{year}-{mon}-01"
    if int(mon) == 12:
        end_date = f"{int(year) + 1}-01-01"
    else:
        end_date = f"{year}-{int(mon) + 1:02d}-01"

    sales_records = await _db.daily_sales.find(
        {"center": center, "date": {"$gte": start_date, "$lt": end_date}},
        {"total_sale": 1, "swiggy_sale": 1, "zomato_sale": 1, "doordash_sale": 1,
         "swiggy": 1, "zomato": 1, "doordash": 1},
    ).to_list(200)
    total_sale = sum(r.get("total_sale", 0) or 0 for r in sales_records)

    expense_records = await _db.expenses.find(
        {"center": center, "date": {"$gte": start_date, "$lt": end_date}},
        {"amount": 1},
    ).to_list(2000)
    total_expenses = sum(e.get("amount", 0) or 0 for e in expense_records)

    from utils.commissions import get_total_commissions
    from utils.gst import compute_gst_from_rows
    comm = await get_total_commissions(_db, center, month)
    total_commission = float(comm["total"] or 0)
    franchise_country = (franchise or {}).get("country", "India")
    gst_calc = compute_gst_from_rows(sales_records, country=franchise_country, center=center)
    _ = gst_calc  # noqa: F841 — kept for future commission-GST-on-sales toggle
    # Commission GST = GST portion booked against commission lines (~18%).
    commission_gst = round(float(comm.get("gst") or 0), 2) if comm.get("gst") is not None else 0.0
    if commission_gst <= 0:
        # Fallback estimate: 18% on commissions when sub-amount not tracked.
        commission_gst = round(total_commission * 0.18, 2)

    # If GST is recoverable per adjustments, add Commission GST back to base.
    try:
        gst_flag = await _db.gst_treatment.find_one(
            {"center": {"$regex": f"^{center}$", "$options": "i"}, "month": month},
            {"commission_gst_recoverable": 1},
        )
    except Exception:
        gst_flag = None
    comm_gst_recoverable = bool(gst_flag and gst_flag.get("commission_gst_recoverable"))
    profit_share_base = round(
        total_sale - total_expenses - total_commission
        + (commission_gst if comm_gst_recoverable else 0.0),
        2,
    )

    # Share split (configurable per franchise)
    franchise_share_pct = max(0.0, min(100.0, float(franchise_share_pct or 80)))
    mfpl_share_pct = round(100.0 - franchise_share_pct, 4)
    base_for_split = max(0.0, profit_share_base)
    franchise_share = round(base_for_split * franchise_share_pct / 100.0, 2)
    mfpl_share = round(base_for_split * mfpl_share_pct / 100.0, 2)

    payments = await _db.payout_payments.find(
        {"center": center.upper(), "month": month}, {"_id": 0},
    ).to_list(200)
    amount_paid = round(sum(p.get("amount", 0) or 0 for p in payments), 2)

    pending = round(max(0.0, franchise_share - amount_paid), 2)
    if amount_paid <= 0:
        status = "Pending"
    elif amount_paid + 0.5 < franchise_share:
        status = "Partial"
    else:
        status = "Paid"

    return {
        "month": month,
        "sale": round(total_sale, 2),
        "expenses": round(total_expenses, 2),
        "commissions": round(total_commission, 2),
        "commission_gst": commission_gst,
        "commission_gst_recoverable": comm_gst_recoverable,
        "profit_share_base": profit_share_base,
        "franchise_share_pct": franchise_share_pct,
        "mfpl_share_pct": mfpl_share_pct,
        "franchise_share": franchise_share,
        "mfpl_share": mfpl_share,
        "amount_paid": amount_paid,
        "pending": pending,
        "status": status,
    }


def _totals(rows: List[dict], payout_model: str = "revenue_share") -> dict:
    if payout_model == "profit_share":
        keys = ["sale", "expenses", "commissions", "commission_gst",
                "profit_share_base", "franchise_share", "mfpl_share",
                "amount_paid", "pending"]
    else:
        keys = ["sale", "expenses", "pnl", "revenue_share_base",
                "revenue_share_amount", "revenue_share_plus_gst",
                "mg_amount", "mg_plus_gst", "amount_paid",
                "eligible_adjustments", "profit_share_mfpl"]
    return {k: round(sum(float(r.get(k, 0) or 0) for r in rows), 2) for k in keys}


def _resolve_payout_model(franchise: dict, override: Optional[str] = None) -> str:
    """Resolve canonical payout model from override (super-admin) or franchise
    record. Falls back to country convention if both are missing."""
    if override in ("revenue_share", "profit_share"):
        return override
    pm = (franchise or {}).get("payout_model")
    if pm in ("revenue_share", "profit_share"):
        return pm
    country = ((franchise or {}).get("country") or "India").strip().lower()
    return "revenue_share" if country == "india" else "profit_share"


def _resolve_share_pct(franchise: dict, override: Optional[float] = None) -> float:
    """Owner share % from override → franchise_owner_share_percentage →
    legacy revenue_share_percentage → 15 (India) / 80 (overseas)."""
    if override:
        try:
            return float(override)
        except Exception:
            pass
    f = franchise or {}
    val = f.get("franchise_owner_share_percentage") or f.get("revenue_share_percentage")
    if val is not None:
        try:
            return float(val)
        except Exception:
            pass
    country = (f.get("country") or "India").strip().lower()
    return 80.0 if country != "india" else 15.0


# ─────────────────────────────────────────────────────────────────────────────
# 1. P&L Revenue Share Overview
# ─────────────────────────────────────────────────────────────────────────────
async def _get_franchise(center: str) -> dict:
    """Replicate the canonical centers→franchise lookup used elsewhere."""
    center_doc = await _db.centers.find_one({"code": center}, {"_id": 0})
    if not center_doc:
        return {}
    fc = center_doc.get("franchise_code")
    if fc:
        f = await _db.franchises.find_one({"franchise_code": fc}, {"_id": 0})
        if f:
            return f
    # Fallback by city / code suffix
    city = (center_doc.get("city") or "").lower()
    suffix = center.split("-")[-1].lower() if "-" in center else center.lower()
    for term in [t for t in [city, suffix] if t and len(t) >= 2]:
        f = await _db.franchises.find_one(
            {"city": {"$regex": term, "$options": "i"}, "status": {"$ne": "Deleted"}},
            {"_id": 0},
        )
        if f:
            return f
    return {}


@router.post("/pnl-revenue-share-overview")
async def pnl_revenue_share_overview(req: dict = Body(...)):
    sess = await _auth(req.get("token"))
    center = (req.get("center") or "").upper()
    if not center:
        raise HTTPException(400, "center is required")

    # Filters
    fy = req.get("financial_year")          # e.g. "2024-25"
    from_month = req.get("from_month")
    to_month = req.get("to_month")
    rs_pct_override = req.get("revenue_share_pct")
    gst_on = bool(req.get("gst_applicable", True))
    # payout_model override: only Super Admin can switch the model away from
    # what's stored on the Franchise record. For everyone else, franchise wins.
    is_sa = bool(sess.get("is_super_admin") or sess.get("is_admin"))
    payout_model_override = req.get("payout_model") if is_sa else None

    franchise = await _get_franchise(center)
    payout_model = _resolve_payout_model(franchise, payout_model_override)
    owner_pct = _resolve_share_pct(franchise, rs_pct_override)
    # GST applicability: India franchise's `gst_applicable` field wins unless
    # the request explicitly toggles it (super-admin override). Overseas
    # centers stay GST-off by default.
    franchise_gst = bool((franchise or {}).get("gst_applicable", False))
    franchise_country = ((franchise or {}).get("country") or "India").strip().lower()
    if "gst_applicable" not in req:
        gst_on = franchise_gst if franchise_country == "india" else False

    if fy and not (from_month and to_month):
        from_month, to_month = _fy_range(fy)
    if not from_month:
        from_month = "2024-04"
    if not to_month:
        to_month = datetime.now().strftime("%Y-%m")

    months = _months_between(from_month, to_month)
    if payout_model == "profit_share":
        rows = [await _month_row_profit_share(center, m, franchise, owner_pct) for m in months]
    else:
        rows = [await _month_row(center, m, franchise, owner_pct, gst_on) for m in months]
    return {
        "success": True,
        "center": center,
        "center_name": franchise.get("franchise_name") or franchise.get("name") or center,
        "payout_model": payout_model,
        "payout_model_label": "Profit Share" if payout_model == "profit_share" else "Revenue Share",
        "franchise_owner_share_percentage": owner_pct,
        "mfpl_share_percentage": round(100.0 - owner_pct, 4) if payout_model == "profit_share" else None,
        "country": (franchise or {}).get("country") or "India",
        "filters": {
            "financial_year": fy,
            "from_month": from_month,
            "to_month": to_month,
            "revenue_share_pct": owner_pct,
            "gst_applicable": gst_on,
        },
        "rows": rows,
        "totals": _totals(rows, payout_model),
        "gst_rate": GST_RATE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Revenue Share Projection
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/revenue-share-projection")
async def revenue_share_projection(req: dict = Body(...)):
    sess = await _auth(req.get("token"))
    center = (req.get("center") or "").upper()
    if not center:
        raise HTTPException(400, "center is required")

    years = int(req.get("years") or 1)
    if years not in (1, 2, 3, 4, 5):
        years = 1
    months_count = years * 12
    sales_growth = float(req.get("sales_growth_pct") or 3.0) / 100.0
    expense_growth = float(req.get("expense_growth_pct") or 2.0) / 100.0
    gst_pct = float(req.get("gst_pct") or GST_RATE)
    rs_pct_override = req.get("revenue_share_pct")
    mg_amount_override = req.get("mg_amount")          # optional — else last actual MG
    start_month = req.get("start_month")               # YYYY-MM; defaults to next month after last actual

    franchise = await _get_franchise(center)
    is_sa = bool(sess.get("is_super_admin") or sess.get("is_admin"))
    payout_model_override = req.get("payout_model") if is_sa else None
    payout_model = _resolve_payout_model(franchise, payout_model_override)
    owner_pct = _resolve_share_pct(franchise, rs_pct_override)

    # — Seed baseline = average of last 3 months that had SALES data —
    today = datetime.now()
    actual_to = today.strftime("%Y-%m")
    cur = today
    seeds_with_sales = []
    seeds_fallback = []
    for _ in range(18):
        if cur.month == 1:
            cur = cur.replace(year=cur.year - 1, month=12)
        else:
            cur = cur.replace(month=cur.month - 1)
        try:
            if payout_model == "profit_share":
                row = await _month_row_profit_share(center, cur.strftime("%Y-%m"), franchise, owner_pct)
            else:
                row = await _month_row(center, cur.strftime("%Y-%m"), franchise, owner_pct, True)
        except Exception:
            continue
        if row["sale"] > 0:
            seeds_with_sales.append(row)
        elif row["expenses"] > 0:
            seeds_fallback.append(row)
        if len(seeds_with_sales) >= 3:
            break

    seeds = seeds_with_sales if seeds_with_sales else seeds_fallback[:3]

    if seeds:
        base_sale = sum(s["sale"] for s in seeds) / len(seeds)
        base_expense = sum(s["expenses"] for s in seeds) / len(seeds)
        if payout_model == "profit_share":
            base_commission = sum(s.get("commissions", 0) for s in seeds) / len(seeds)
            base_comm_gst = sum(s.get("commission_gst", 0) for s in seeds) / len(seeds)
            base_mg = 0.0
            rs_base_ratio = 0.0
        else:
            base_mg = sum(s["mg_amount"] for s in seeds) / len(seeds)
            base_commission = 0.0
            base_comm_gst = 0.0
            total_seed_sale = sum(s["sale"] for s in seeds) or 1.0
            total_seed_rs_base = sum(max(0, s["revenue_share_base"]) for s in seeds)
            rs_base_ratio = total_seed_rs_base / total_seed_sale if total_seed_sale else 0.85
        last_actual_month = max(s["month"] for s in seeds)
    else:
        base_sale = base_expense = base_mg = base_commission = base_comm_gst = 0.0
        rs_base_ratio = 0.85
        last_actual_month = actual_to

    if mg_amount_override is not None and payout_model == "revenue_share":
        base_mg = float(mg_amount_override)

    if not start_month:
        candidates = [today, datetime.strptime(last_actual_month + "-01", "%Y-%m-%d")]
        d = max(candidates)
        if d.month == 12:
            d = d.replace(year=d.year + 1, month=1)
        else:
            d = d.replace(month=d.month + 1)
        start_month = d.strftime("%Y-%m")

    rows = []
    cur = datetime.strptime(start_month + "-01", "%Y-%m-%d")
    for i in range(months_count):
        projected_sale = round(base_sale * ((1 + sales_growth) ** i), 2)
        projected_expense = round(base_expense * ((1 + expense_growth) ** i), 2)

        if payout_model == "profit_share":
            # Profit Share projection: commissions grow with sales (ratio fixed).
            comm_ratio = (base_commission / base_sale) if base_sale else 0.0
            comm_gst_ratio = (base_comm_gst / base_sale) if base_sale else 0.0
            projected_comm = round(projected_sale * comm_ratio, 2)
            projected_comm_gst = round(projected_sale * comm_gst_ratio, 2)
            ps_base = round(projected_sale - projected_expense - projected_comm, 2)
            base_for_split = max(0.0, ps_base)
            fr_share = round(base_for_split * owner_pct / 100.0, 2)
            mfpl_share = round(base_for_split * (100.0 - owner_pct) / 100.0, 2)
            rows.append({
                "month": cur.strftime("%Y-%m"),
                "sale": projected_sale,
                "expenses": projected_expense,
                "commissions": projected_comm,
                "commission_gst": projected_comm_gst,
                "profit_share_base": ps_base,
                "franchise_share_pct": owner_pct,
                "mfpl_share_pct": round(100.0 - owner_pct, 4),
                "franchise_share": fr_share,
                "mfpl_share": mfpl_share,
                "amount_paid": 0.0,
                "pending": fr_share,
                "status": "Projected",
            })
        else:
            pnl = round(projected_sale - projected_expense, 2)
            rs_base = round(projected_sale * rs_base_ratio, 2)
            rs_amount = round(max(0, rs_base) * (owner_pct / 100.0), 2)
            rs_plus_gst = round(rs_amount * (1 + gst_pct / 100.0), 2)
            mg_plus_gst = round(base_mg * (1 + gst_pct / 100.0), 2)
            amount_paid = round(max(rs_plus_gst, mg_plus_gst), 2)
            profit_mfpl = round(projected_sale - projected_expense - amount_paid, 2)
            rows.append({
                "month": cur.strftime("%Y-%m"),
                "sale": projected_sale,
                "expenses": projected_expense,
                "pnl": pnl,
                "revenue_share_base": rs_base,
                "revenue_share_pct": owner_pct,
                "revenue_share_amount": rs_amount,
                "revenue_share_plus_gst": rs_plus_gst,
                "mg_amount": round(base_mg, 2),
                "mg_plus_gst": mg_plus_gst,
                "amount_paid": amount_paid,
                "eligible_adjustments": 0.0,
                "profit_share_mfpl": profit_mfpl,
            })
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)

    return {
        "success": True,
        "center": center,
        "center_name": franchise.get("franchise_name") or franchise.get("name") or center,
        "payout_model": payout_model,
        "payout_model_label": "Profit Share" if payout_model == "profit_share" else "Revenue Share",
        "franchise_owner_share_percentage": owner_pct,
        "mfpl_share_percentage": round(100.0 - owner_pct, 4) if payout_model == "profit_share" else None,
        "country": (franchise or {}).get("country") or "India",
        "filters": {
            "years": years,
            "start_month": start_month,
            "sales_growth_pct": sales_growth * 100,
            "expense_growth_pct": expense_growth * 100,
            "gst_pct": gst_pct,
            "revenue_share_pct": owner_pct,
            "mg_amount": round(base_mg, 2),
        },
        "baseline_seed_months": [s["month"] for s in seeds],
        "rows": rows,
        "totals": _totals(rows, payout_model),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Exports — shared PDF & Excel builders
# ─────────────────────────────────────────────────────────────────────────────
COLUMN_DEFS_RS = [
    ("month", "Month"),
    ("sale", "Sale"),
    ("expenses", "Expenses"),
    ("pnl", "P / L"),
    ("revenue_share_base", "Revenue Share Base"),
    ("revenue_share_amount", "Revenue Share"),
    ("revenue_share_plus_gst", "Revenue Share + GST"),
    ("mg_amount", "MG"),
    ("mg_plus_gst", "MG + GST"),
    ("amount_paid", "Amount Paid"),
    ("eligible_adjustments", "Eligible Adj."),
    ("profit_share_mfpl", "Profit Share MFPL"),
]

COLUMN_DEFS_PS = [
    ("month", "Month"),
    ("sale", "Sale"),
    ("expenses", "Expenses"),
    ("commissions", "Commissions"),
    ("commission_gst", "Commission GST"),
    ("profit_share_base", "Profit Share Base"),
    ("franchise_share", "Franchise Share"),
    ("mfpl_share", "MFPL Share"),
    ("amount_paid", "Amount Paid"),
    ("pending", "Pending"),
    ("status", "Status"),
]


def _columns_for(data: dict) -> list:
    return COLUMN_DEFS_PS if data.get("payout_model") == "profit_share" else COLUMN_DEFS_RS


def _fmt_money(v) -> str:
    try:
        return f"{float(v or 0):,.2f}"
    except Exception:
        return str(v)


def _build_excel(title: str, data: dict, account_manager: str = "—") -> bytes:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    cols = _columns_for(data)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = (title[:28] or "Report")

    # Title block
    ws.append([title])
    ws.append([f"Center: {data.get('center_name', '—')} ({data.get('center', '')})"])
    ws.append([f"Business Model: {data.get('payout_model_label', '—')}"
               + (f"  ·  Country: {data.get('country', '—')}")])
    f = data.get("filters", {}) or {}
    period = f.get("financial_year") or (f"{f.get('from_month', '—')} → {f.get('to_month', '—')}")
    if f.get("start_month"):
        period = f"{f.get('years')} year(s) from {f.get('start_month')}"
    ws.append([f"Period: {period}"])
    if data.get("payout_model") == "profit_share":
        ws.append([f"Franchise Share %: {data.get('franchise_owner_share_percentage', '—')}"
                   f"  ·  MFPL Share %: {data.get('mfpl_share_percentage', '—')}"])
    else:
        ws.append([f"Revenue Share %: {f.get('revenue_share_pct', '—')}  ·  GST: "
                   + ("Yes (18%)" if f.get('gst_applicable', True) else "No")])
    ws.append([f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}"])
    ws.append([])

    header_row_idx = ws.max_row + 1
    headers = [c[1] for c in cols]
    ws.append(headers)
    header_fill = PatternFill("solid", fgColor="1f4e79")
    bold_white = Font(bold=True, color="FFFFFF")
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=header_row_idx, column=c)
        cell.font = bold_white
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Total row at the TOP (per spec)
    totals = data.get("totals", {})
    total_row = ["TOTAL"]
    for key, _ in cols[1:]:
        total_row.append(totals.get(key, "") if key != "status" else "")
    ws.append(total_row)
    total_idx = ws.max_row
    total_fill = PatternFill("solid", fgColor="ffe1a4")
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=total_idx, column=c)
        cell.font = Font(bold=True)
        cell.fill = total_fill
        if c > 1 and cols[c - 1][0] != "status":
            cell.number_format = "#,##0.00"

    # Data rows
    for r in data.get("rows", []):
        row_values = [r.get("month", "")]
        for key, _ in cols[1:]:
            row_values.append(r.get(key, "" if key == "status" else 0))
        ws.append(row_values)
        idx = ws.max_row
        for c in range(2, len(headers) + 1):
            if cols[c - 1][0] != "status":
                ws.cell(row=idx, column=c).number_format = "#,##0.00"

    # Column widths
    for i in range(1, len(cols) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 16

    # Footer signatures
    ws.append([])
    ws.append([f"Prepared by: System ({title})"])
    ws.append([f"Account Manager: {account_manager}"])
    ws.append([f"Download Date: {datetime.now().strftime('%d %b %Y, %H:%M')}"])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _build_pdf(title: str, data: dict, account_manager: str = "—") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.units import mm

    cols = _columns_for(data)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("T", parent=styles["Heading1"], fontSize=14,
                                 textColor=colors.HexColor("#800020"))
    sub = ParagraphStyle("S", parent=styles["Normal"], fontSize=9)
    small = ParagraphStyle("Sm", parent=styles["Normal"], fontSize=8,
                           textColor=colors.grey)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=10 * mm, bottomMargin=10 * mm)
    story = []

    logo_path = None
    for p in (
        "/app/backend/assets/logo.png",
        "/app/backend/assets/purnabramha_logo.png",
        "/app/frontend/public/logo.png",
        "/app/frontend/public/purnabramha_logo.png",
    ):
        if os.path.exists(p):
            logo_path = p
            break
    if logo_path:
        try:
            story.append(Image(logo_path, width=22 * mm, height=22 * mm))
        except Exception:
            pass

    story.append(Paragraph(title, title_style))
    story.append(Paragraph(f"<b>Center:</b> {data.get('center_name', '—')} ({data.get('center', '')})", sub))
    story.append(Paragraph(
        f"<b>Business Model:</b> {data.get('payout_model_label', '—')}  &nbsp; "
        f"<b>Country:</b> {data.get('country', '—')}", sub))
    f = data.get("filters", {}) or {}
    period = f.get("financial_year") or f"{f.get('from_month', '—')} → {f.get('to_month', '—')}"
    if f.get("start_month"):
        period = f"{f.get('years')} year(s) starting {f.get('start_month')}"
    story.append(Paragraph(f"<b>Period:</b> {period}", sub))
    if data.get("payout_model") == "profit_share":
        story.append(Paragraph(
            f"<b>Franchise Share %:</b> {data.get('franchise_owner_share_percentage', '—')}"
            f" &nbsp; <b>MFPL Share %:</b> {data.get('mfpl_share_percentage', '—')}", sub))
    else:
        story.append(Paragraph(
            f"<b>Revenue Share %:</b> {f.get('revenue_share_pct', '—')}  &nbsp; "
            f"<b>GST:</b> {'Yes (18%)' if f.get('gst_applicable', True) else 'No'}", sub))
    story.append(Spacer(1, 6))

    headers = [c[1] for c in cols]
    totals = data.get("totals", {})
    total_row = ["TOTAL"]
    for k, _ in cols[1:]:
        total_row.append("" if k == "status" else _fmt_money(totals.get(k, 0)))
    table_data = [headers, total_row]
    for r in data.get("rows", []):
        row = [r.get("month", "")]
        for k, _ in cols[1:]:
            v = r.get(k, "" if k == "status" else 0)
            row.append(v if k == "status" else _fmt_money(v))
        table_data.append(row)

    page_w = 277 * mm  # A4 landscape printable width approx
    col_w = page_w / len(cols)
    col_widths = [col_w] * len(cols)
    table = Table(table_data, colWidths=col_widths, repeatRows=2)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ffe1a4")),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 2), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
    ]))
    story.append(table)
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<b>Prepared by:</b> System ({title})", sub))
    story.append(Paragraph(f"<b>Account Manager:</b> {account_manager}", sub))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Download Date: {datetime.now().strftime('%d %b %Y, %H:%M')}", small))
    doc.build(story)
    return buf.getvalue()


def _export_response(payload: bytes, kind: str, filename: str) -> Response:
    media = "application/pdf" if kind == "pdf" else (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return Response(content=payload, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/pnl-revenue-share-overview/export-pdf")
async def export_overview_pdf(req: dict = Body(...)):
    data = await pnl_revenue_share_overview(req)
    pdf = _build_pdf("P&L Revenue Share Overview", data,
                     account_manager=req.get("account_manager", "—"))
    fname = f"PnL_RevenueShare_{data['center']}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return _export_response(pdf, "pdf", fname)


@router.post("/pnl-revenue-share-overview/export-excel")
async def export_overview_excel(req: dict = Body(...)):
    data = await pnl_revenue_share_overview(req)
    xlsx = _build_excel("P&L Revenue Share Overview", data,
                        account_manager=req.get("account_manager", "—"))
    fname = f"PnL_RevenueShare_{data['center']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return _export_response(xlsx, "xlsx", fname)


@router.post("/revenue-share-projection/export-pdf")
async def export_projection_pdf(req: dict = Body(...)):
    data = await revenue_share_projection(req)
    pdf = _build_pdf("Revenue Share Projection", data,
                     account_manager=req.get("account_manager", "—"))
    fname = f"RevenueShareProjection_{data['center']}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return _export_response(pdf, "pdf", fname)


@router.post("/revenue-share-projection/export-excel")
async def export_projection_excel(req: dict = Body(...)):
    data = await revenue_share_projection(req)
    xlsx = _build_excel("Revenue Share Projection", data,
                        account_manager=req.get("account_manager", "—"))
    fname = f"RevenueShareProjection_{data['center']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return _export_response(xlsx, "xlsx", fname)
