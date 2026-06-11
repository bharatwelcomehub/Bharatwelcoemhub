"""Center Financial Health & Profitability Intelligence module.

Produces an executive-grade financial picture per center (and across the
portfolio) using only existing collections — no duplicate data entry:

    • daily_sales         → Total Sales, orders (num_bills), guests
    • expenses            → every expense head (Food / Labor / Rent / …)
    • attendance          → labor hours (Present=full day, Half Day=½)
    • centers             → country (for default Food-Cost targets)

Sections 1, 2, 3, 4, 5, 6, 7, 9, 10, 11 from the product spec are all
implemented here. Section 8 (Menu Profitability) is intentionally deferred
until item-level POS sales are available.
"""
from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from routes.center_accounts import check_access
from server import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/financial-health", tags=["financial-health"])

# ---------------------------------------------------------------------------
# Configuration — expense-head buckets and targets
# ---------------------------------------------------------------------------
FOOD_COST_HEADS = {
    "GROCERY", "DAIRY PRODUCTS", "FRUITS & VEGETABLE", "PAV", "MANGO RASS",
    "CYLINDER",
}
LABOR_COST_HEADS = {
    "SALARY", "OVER TIME", "SALARY ADVANCE", "DIRECTOR FEES",
}

# Buckets surfaced on the Expense-Leakage card (Section 7)
LEAKAGE_BUCKETS: Dict[str, List[str]] = {
    "Rent": ["RENT", "RENT PAID SHOP", "STAFF ROOM RENT"],
    "Electricity": ["ELECTRCITY BILL SHOP", "ELECTRICITY", "STAFF ELECTRICITY BILL",
                     "GENERATOR EXPENSES"],
    "Gas": ["CYLINDER"],
    "Packaging": ["PACKAGING MATERIAL", "STATIONARY & PACKAGING"],
    "Cleaning": ["HOUSEKEEPING MATERIAL"],
    "Maintenance": ["REPAIR & MAINTAINANCE", "REPAIR & MAINTENANCE"],
    "Marketing": ["MEDIA & ADVERTISEMENT"],
    "Repairs": ["ELECTRICAL INSTALLATION"],
    "Revenue Share": ["FRANCHISEE REVENUE SHARE"],
    "Licenses": ["SOFTWARE"],
    "Logistics": ["LOGISTIC SHOP", "POSTAGE & COURIER", "PETROL"],
    "GST Paid": ["GST PAID"],
    "Bank Charges": ["BANK CHARGES"],
    "Other Expenses": ["MISCELLANEOUS", "RESTAURANT GENERAL EXPENSES",
                       "CELEBRATION EXPENSES", "PRINTING & STATIONARY",
                       "MEDICAL EXPENSES"],
}

FOOD_COST_TARGET_PCT = {"India": 28.0, "Australia": 30.0}
PRIME_COST_TARGET_PCT = 55.0   # under = green, 55-60 = yellow, >60 = red
LABOR_COST_TARGET_PCT = 25.0   # standard restaurant target

# Hours-per-attendance-status (Section 4 + 6)
HOURS_FROM_STATUS = {
    "P": 8.0, "PRESENT": 8.0, "H": 4.0, "HALF": 4.0, "HD": 4.0, "HALF DAY": 4.0,
    "WO": 0.0, "OFF": 0.0, "A": 0.0, "ABSENT": 0.0, "L": 0.0, "LEAVE": 0.0,
}


# ---------------------------------------------------------------------------
# Period parsing
# ---------------------------------------------------------------------------
def _parse_period(p: dict) -> Tuple[str, str, str]:
    """Return (label, from_iso, to_iso) inclusive YYYY-MM-DD strings."""
    today = date.today()
    kind = (p.get("type") or "month").lower()

    if kind == "month":
        m = p.get("month") or today.strftime("%Y-%m")
        y, mm = m.split("-")
        first = date(int(y), int(mm), 1)
        nxt = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
        last = nxt - timedelta(days=1)
        return (m, first.isoformat(), last.isoformat())

    if kind == "quarter":
        q = (p.get("quarter") or f"{today.year}-Q{((today.month - 1) // 3) + 1}").upper()
        y_str, qn_str = q.split("-Q")
        y = int(y_str)
        qn = int(qn_str)
        start_m = (qn - 1) * 3 + 1
        first = date(y, start_m, 1)
        end_m = start_m + 2
        end_first = date(y if end_m <= 12 else y + 1, end_m if end_m <= 12 else 1, 1)
        nxt = (end_first.replace(day=28) + timedelta(days=4)).replace(day=1)
        last = nxt - timedelta(days=1)
        return (q, first.isoformat(), last.isoformat())

    if kind == "fy":
        # Indian FY: Apr Y to Mar Y+1. Label e.g. "FY26" = Apr-2025 → Mar-2026
        fy = (p.get("fy") or f"FY{(today.year + (1 if today.month >= 4 else 0)) % 100:02d}")
        # Accept "FY26" or "FY25-26"
        try:
            yy = int(fy.replace("FY", "").split("-")[0]) % 100
        except Exception:
            yy = today.year % 100
        # FY26 → starts Apr 2025
        start_year = 2000 + yy - 1
        first = date(start_year, 4, 1)
        last = date(start_year + 1, 3, 31)
        return (fy, first.isoformat(), last.isoformat())

    if kind == "custom":
        f = p.get("from_date") or today.replace(day=1).isoformat()
        t = p.get("to_date") or today.isoformat()
        return (f"{f} → {t}", f, t)

    # default month
    m = today.strftime("%Y-%m")
    return _parse_period({"type": "month", "month": m})


def _prev_period(p: dict) -> dict:
    """Same kind, one step earlier — used for MoM / QoQ / YoY comparisons."""
    kind = (p.get("type") or "month").lower()
    if kind == "month":
        m = p.get("month") or date.today().strftime("%Y-%m")
        y_str, mm_str = m.split("-")
        y = int(y_str)
        mm = int(mm_str)
        if mm == 1:
            y -= 1
            mm = 12
        else:
            mm -= 1
        return {"type": "month", "month": f"{y:04d}-{mm:02d}"}
    if kind == "quarter":
        q = (p.get("quarter") or "").upper()
        try:
            y_str, qn_str = q.split("-Q")
            y = int(y_str)
            qn = int(qn_str)
            if qn == 1:
                return {"type": "quarter", "quarter": f"{y - 1}-Q4"}
            return {"type": "quarter", "quarter": f"{y}-Q{qn - 1}"}
        except Exception:
            return p
    if kind == "fy":
        fy = (p.get("fy") or "").replace("FY", "").split("-")[0]
        try:
            yy = int(fy)
            return {"type": "fy", "fy": f"FY{(yy - 1) % 100:02d}"}
        except Exception:
            return p
    if kind == "custom":
        f = datetime.fromisoformat(p["from_date"])
        t = datetime.fromisoformat(p["to_date"])
        span = (t - f).days + 1
        new_t = f - timedelta(days=1)
        new_f = new_t - timedelta(days=span - 1)
        return {"type": "custom", "from_date": new_f.date().isoformat(),
                "to_date": new_t.date().isoformat()}
    return p


# ---------------------------------------------------------------------------
# Building blocks — pull data for a center within [from, to]
# ---------------------------------------------------------------------------
async def _commissions_for_period(center: str, df: str, dt: str) -> float:
    """Sum of platform commissions (PhonePe/Razorpay/Swiggy/Zomato/etc.) for
    months that overlap the period. Used by Financial Health to compute the
    canonical Profit/Loss formula (Sales − Expenses − Commissions) per the
    Feb-2026 owner directive."""
    months = set()
    try:
        f = datetime.fromisoformat(df)
        t = datetime.fromisoformat(dt)
        cur_m = f.replace(day=1)
        while cur_m <= t:
            months.add(cur_m.strftime("%Y-%m"))
            # advance one month
            if cur_m.month == 12:
                cur_m = cur_m.replace(year=cur_m.year + 1, month=1)
            else:
                cur_m = cur_m.replace(month=cur_m.month + 1)
    except Exception:
        return 0.0
    if not months:
        return 0.0
    cur = db.monthly_commissions.aggregate([
        {"$match": {"center": center, "month": {"$in": list(months)}}},
        {"$group": {
            "_id": None,
            "total": {
                "$sum": {
                    "$ifNull": [
                        "$total_commission_amount",
                        {"$add": [
                            {"$ifNull": ["$gst_tax_deductions", 0]},
                            {"$ifNull": ["$other_deductions", 0]},
                            {"$ifNull": ["$sundry_debtors", 0]},
                        ]}
                    ]
                }
            },
        }},
    ])
    docs = await cur.to_list(1)
    return float((docs[0]["total"] if docs else 0) or 0)


async def _sales_and_orders(center: str, df: str, dt: str) -> Dict[str, float]:
    cur = db.daily_sales.aggregate([
        {"$match": {"center": center, "date": {"$gte": df, "$lte": dt}}},
        {"$group": {
            "_id": None,
            "sales": {"$sum": {"$ifNull": ["$total_sale", 0]}},
            "orders": {"$sum": {"$ifNull": ["$num_bills", 0]}},
            "guests": {"$sum": {"$ifNull": ["$num_guests", 0]}},
            "gst": {"$sum": {"$ifNull": ["$gst_amount", 0]}},
            "days": {"$sum": 1},
        }}
    ])
    docs = await cur.to_list(1)
    if not docs:
        return {"sales": 0.0, "orders": 0, "guests": 0, "gst": 0.0, "days": 0}
    d = docs[0]
    return {
        "sales": float(d.get("sales") or 0),
        "orders": int(d.get("orders") or 0),
        "guests": int(d.get("guests") or 0),
        "gst": float(d.get("gst") or 0),
        "days": int(d.get("days") or 0),
    }


async def _expenses_by_head(center: str, df: str, dt: str) -> Dict[str, float]:
    cur = db.expenses.aggregate([
        {"$match": {"center": center, "date": {"$gte": df, "$lte": dt}}},
        {"$group": {"_id": "$expense_type", "amt": {"$sum": "$amount"}}},
    ])
    out: Dict[str, float] = {}
    async for d in cur:
        out[d["_id"] or "UNCATEGORIZED"] = float(d.get("amt") or 0)
    return out


async def _adjustments_for_period(center: str, df: str, dt: str) -> float:
    """Sum of expense adjustments that should be subtracted from total
    expenses for this date range — keeps Financial Health in sync with the
    Adjustments tab / P&L / Franchise Ledger."""
    from utils.adjustments import get_adjustments_for_period
    res = await get_adjustments_for_period(db, center, df, dt)
    return float(res.get("total") or 0)


async def _labor_hours(center: str, df: str, dt: str) -> Tuple[float, int]:
    """Total labour hours (Section 4 + 6) + distinct employee headcount."""
    cur = db.attendance.find(
        {"center": center, "date": {"$gte": df, "$lte": dt}},
        {"_id": 0, "status": 1, "employeeName": 1},
    )
    hours = 0.0
    emps = set()
    async for r in cur:
        status = (r.get("status") or "").upper().strip()
        h = HOURS_FROM_STATUS.get(status)
        if h is None:
            # International attendance may use number of hours
            try:
                h = float(status)
            except Exception:
                h = 0.0
        hours += h
        if h > 0 and r.get("employeeName"):
            emps.add(r["employeeName"])
    return hours, len(emps)


async def _center_country(center: str) -> str:
    c = await db.centers.find_one({"code": center}, {"_id": 0, "country": 1})
    if not c:
        return "India"
    return (c.get("country") or "India")


def _safe_pct(num: float, den: float) -> float:
    if not den:
        return 0.0
    return round((num / den) * 100, 2)


# ---------------------------------------------------------------------------
# The big snapshot — one call gathers everything for a center+period
# ---------------------------------------------------------------------------
async def _snapshot(center: str, period: dict) -> Dict[str, Any]:
    label, df, dt = _parse_period(period)
    prev_label, prev_df, prev_dt = _parse_period(_prev_period(period))

    country = await _center_country(center)
    target_food_pct = FOOD_COST_TARGET_PCT.get(country, 28.0)

    # ── Current period ──────────────────────────────────────────────────
    sales = await _sales_and_orders(center, df, dt)
    expenses_by_head = await _expenses_by_head(center, df, dt)
    hours, emp_count = await _labor_hours(center, df, dt)
    adj_total = await _adjustments_for_period(center, df, dt)

    total_expenses_raw = sum(expenses_by_head.values())
    total_expenses = round(total_expenses_raw - adj_total, 2)
    food_cost = sum(amt for h, amt in expenses_by_head.items() if h in FOOD_COST_HEADS)
    labor_cost = sum(amt for h, amt in expenses_by_head.items() if h in LABOR_COST_HEADS)
    prime_cost = food_cost + labor_cost
    gross_profit = sales["sales"] - food_cost
    # ── Profit / Loss (per Feb-2026 owner directive) ────────────────────
    # Net Profit = Sales − Expenses − Commissions (GST excluded — pass-through).
    # Same formula as Operational Balance on Center Accounts so dashboards
    # stay reconciled.
    total_commissions = await _commissions_for_period(center, df, dt)
    net_profit = sales["sales"] - total_expenses - total_commissions
    contribution_margin = gross_profit  # by definition

    food_pct = _safe_pct(food_cost, sales["sales"])
    labor_pct = _safe_pct(labor_cost, sales["sales"])
    prime_pct = _safe_pct(prime_cost, sales["sales"])
    np_pct = _safe_pct(net_profit, sales["sales"])
    cm_pct = _safe_pct(contribution_margin, sales["sales"])

    # ── Previous period (for MoM / trend) ───────────────────────────────
    p_sales = await _sales_and_orders(center, prev_df, prev_dt)
    p_expenses_by_head = await _expenses_by_head(center, prev_df, prev_dt)
    p_hours, _p_emp = await _labor_hours(center, prev_df, prev_dt)
    p_adj_total = await _adjustments_for_period(center, prev_df, prev_dt)

    p_total_expenses_raw = sum(p_expenses_by_head.values())
    p_total_expenses = round(p_total_expenses_raw - p_adj_total, 2)
    p_food_cost = sum(amt for h, amt in p_expenses_by_head.items() if h in FOOD_COST_HEADS)
    p_labor_cost = sum(amt for h, amt in p_expenses_by_head.items() if h in LABOR_COST_HEADS)
    p_prime_cost = p_food_cost + p_labor_cost
    p_total_commissions = await _commissions_for_period(center, prev_df, prev_dt)
    p_net_profit = p_sales["sales"] - p_total_expenses - p_total_commissions

    def _delta_pct(cur: float, prev: float) -> float:
        if not prev:
            return 0.0
        return round(((cur - prev) / abs(prev)) * 100, 2)

    sales_delta_pct = _delta_pct(sales["sales"], p_sales["sales"])
    food_pct_prev = _safe_pct(p_food_cost, p_sales["sales"])
    labor_pct_prev = _safe_pct(p_labor_cost, p_sales["sales"])
    prime_pct_prev = _safe_pct(p_prime_cost, p_sales["sales"])
    np_prev = _safe_pct(p_net_profit, p_sales["sales"])

    # ── Section 7: Expense Leakage by bucket ────────────────────────────
    def _bucket(eb: Dict[str, float]) -> Dict[str, float]:
        out: Dict[str, float] = {b: 0.0 for b in LEAKAGE_BUCKETS}
        for h, amt in eb.items():
            placed = False
            for bucket, heads in LEAKAGE_BUCKETS.items():
                if h in heads:
                    out[bucket] += amt
                    placed = True
                    break
            if not placed and h not in FOOD_COST_HEADS and h not in LABOR_COST_HEADS:
                out["Other Expenses"] += amt
        return out

    cur_buckets = _bucket(expenses_by_head)
    prev_buckets = _bucket(p_expenses_by_head)
    leakage: List[Dict[str, Any]] = []
    for bucket in LEAKAGE_BUCKETS:
        c = cur_buckets.get(bucket, 0.0)
        p = prev_buckets.get(bucket, 0.0)
        delta = _delta_pct(c, p)
        if abs(delta) >= 20 and (c or p):
            severity = "red"
        elif abs(delta) >= 10 and (c or p):
            severity = "yellow"
        else:
            severity = "green"
        leakage.append({
            "bucket": bucket, "current": round(c, 2), "previous": round(p, 2),
            "delta_pct": delta, "severity": severity,
        })
    leakage.sort(key=lambda r: (-{"red": 2, "yellow": 1, "green": 0}[r["severity"]],
                                -r["current"]))

    # ── Section 6: Orders per Labor Hour ────────────────────────────────
    opl_h = round(sales["orders"] / hours, 2) if hours else 0.0
    p_opl_h = round(p_sales["orders"] / p_hours, 2) if p_hours else 0.0

    # ── Section 9: Red Alerts ───────────────────────────────────────────
    alerts: List[Dict[str, str]] = []

    def _add(level: str, code: str, title: str, detail: str):
        alerts.append({"level": level, "code": code, "title": title, "detail": detail})

    if sales["sales"] > 0:
        if food_pct > target_food_pct + 3:
            _add("red", "FOOD_COST_HIGH",
                 "Food Cost above target",
                 f"Food cost {food_pct}% exceeds {country} target {target_food_pct}%.")
        elif food_pct > target_food_pct + 1:
            _add("yellow", "FOOD_COST_WARN",
                 "Food Cost approaching limit",
                 f"Food cost {food_pct}% is creeping over target {target_food_pct}%.")
        if labor_pct > LABOR_COST_TARGET_PCT + 5:
            _add("red", "LABOR_COST_HIGH", "Labor Cost too high",
                 f"Labor cost {labor_pct}% vs typical target {LABOR_COST_TARGET_PCT}%.")
        elif labor_pct > LABOR_COST_TARGET_PCT:
            _add("yellow", "LABOR_COST_WARN", "Labor Cost above target",
                 f"Labor cost {labor_pct}% above {LABOR_COST_TARGET_PCT}%.")
        if prime_pct > 60:
            _add("red", "PRIME_COST_HIGH", "Prime Cost above 60%",
                 f"Prime Cost {prime_pct}% — profitability at risk.")
        elif prime_pct > PRIME_COST_TARGET_PCT:
            _add("yellow", "PRIME_COST_WARN", "Prime Cost above 55%",
                 f"Prime Cost {prime_pct}% — watch.")
        if np_pct < 0:
            _add("red", "NET_LOSS", "Operating at a loss",
                 f"Net Profit {np_pct}% (loss).")
        elif np_pct < 5:
            _add("yellow", "THIN_MARGIN", "Net margin thin",
                 f"Net Profit only {np_pct}% — under 5%.")
    if p_sales["sales"] and sales_delta_pct < -10:
        _add("red", "SALES_DROP", "Sales dropped sharply",
             f"Sales fell {sales_delta_pct}% vs {prev_label}.")
    for row in leakage:
        if row["severity"] == "red":
            _add("red", f"LEAK_{row['bucket'].upper().replace(' ', '_')}",
                 f"{row['bucket']} spiking",
                 f"{row['bucket']} grew {row['delta_pct']}% MoM "
                 f"(₹{row['current']:,.0f} vs ₹{row['previous']:,.0f}).")

    # ── Section 10: AI Recommended Actions (rule-based) ─────────────────
    recommendations: List[Dict[str, Any]] = []
    rec_map = {
        "FOOD_COST_HIGH": ["Review recipe costing for top-selling items",
                            "Audit raw-material wastage for 7 days",
                            "Renegotiate vendor pricing on GROCERY + DAIRY",
                            "Verify inventory closing stock vs sales"],
        "FOOD_COST_WARN": ["Spot-check vendor invoices for hidden hikes",
                            "Track wastage daily for 2 weeks"],
        "LABOR_COST_HIGH": ["Optimise roster — cut idle hours in low-footfall slots",
                             "Cross-train staff so one role covers another",
                             "Review overtime drivers"],
        "LABOR_COST_WARN": ["Audit attendance for misclassified OT",
                             "Cap OT to peak service windows"],
        "PRIME_COST_HIGH": ["Re-engineer menu — push high-margin items",
                             "Lock in 30-day vendor rate cards",
                             "Reduce one shift in lean days"],
        "PRIME_COST_WARN": ["Track Prime Cost weekly until back under 55%"],
        "NET_LOSS": ["Freeze discretionary spend (marketing, repairs)",
                      "Push 7-day catering / corporate bookings drive",
                      "Schedule urgent owner-manager review"],
        "THIN_MARGIN": ["Identify the 3 biggest expense growers and contain",
                         "Run a 10% upsell push on top-margin items"],
        "SALES_DROP": ["Re-activate dormant customers (WhatsApp + Memory Box link)",
                        "Run a 2-week ad campaign on Zomato + Instagram",
                        "Audit recent bad-review patterns"],
        "LEAK_ELECTRICITY": ["Audit AC setpoints + freezer seals",
                              "Check meter reading vs bill",
                              "Switch off display lights past 11 pm"],
        "LEAK_PACKAGING": ["Renegotiate bulk packaging order",
                            "Audit pack size mismatch vs order size"],
        "LEAK_MARKETING": ["Re-validate ROI per campaign before next spend"],
        "LEAK_REPAIRS": ["Approve only repairs >₹5k with manager sign-off"],
        "LEAK_REVENUE_SHARE": ["Reconcile revenue-share %; chase ledger discrepancy"],
        "LEAK_RENT": ["Verify rent invoice; flag any unannounced hike"],
    }
    for a in alerts:
        actions = rec_map.get(a["code"], [])
        if not actions:
            # Generic catch-all for any LEAK_* not explicitly handled
            if a["code"].startswith("LEAK_"):
                actions = [f"Investigate root cause of {a['title'].lower()}",
                           "Compare against last 3-month baseline before approving more spend"]
        if actions:
            recommendations.append({
                "trigger": a["code"], "title": a["title"], "actions": actions,
            })

    # ── Health Score /100 ───────────────────────────────────────────────
    # Net Profit % (40) + Prime Cost (30) + Leakage (20) + Sales trend (10)
    np_band = max(0.0, min(40.0, np_pct / 20.0 * 40)) if np_pct > 0 else 0.0
    if prime_pct == 0:
        pc_band = 0.0
    elif prime_pct <= PRIME_COST_TARGET_PCT:
        pc_band = 30.0
    elif prime_pct <= 60:
        pc_band = 15.0
    else:
        pc_band = 0.0
    red_count = sum(1 for r in leakage if r["severity"] == "red")
    yel_count = sum(1 for r in leakage if r["severity"] == "yellow")
    if red_count == 0 and yel_count == 0:
        leak_band = 20.0
    elif red_count == 0:
        leak_band = max(8.0, 20.0 - yel_count * 2)
    else:
        leak_band = max(0.0, 12.0 - red_count * 3)
    if sales_delta_pct > 5:
        trend_band = 10.0
    elif sales_delta_pct > -2:
        trend_band = 6.0
    elif sales_delta_pct > -10:
        trend_band = 3.0
    else:
        trend_band = 0.0
    health_score = round(np_band + pc_band + leak_band + trend_band, 1)
    if health_score >= 75:
        status = "Healthy"
        status_color = "green"
    elif health_score >= 50:
        status = "Watch"
        status_color = "yellow"
    else:
        status = "Action Required"
        status_color = "red"

    return {
        "center": center,
        "country": country,
        "period": {"label": label, "from": df, "to": dt},
        "prev_period": {"label": prev_label, "from": prev_df, "to": prev_dt},
        # Section 1
        "summary": {
            "total_sales": round(sales["sales"], 2),
            "total_expenses": round(total_expenses, 2),
            "total_expenses_raw": round(total_expenses_raw, 2),
            "adjustments": round(adj_total, 2),
            "food_cost": round(food_cost, 2),
            "labor_cost": round(labor_cost, 2),
            "food_cost_pct": food_pct,
            "labor_cost_pct": labor_pct,
            "prime_cost": round(prime_cost, 2),
            "prime_cost_pct": prime_pct,
            "total_commissions": round(total_commissions, 2),
            "gross_profit": round(gross_profit, 2),
            "net_profit": round(net_profit, 2),
            "net_profit_pct": np_pct,
            "profit_loss_formula": "Sales − Expenses − Commissions (GST excluded)",
            "health_score": health_score,
            "status": status,
            "status_color": status_color,
            "sales_delta_pct": sales_delta_pct,
        },
        # Section 2
        "prime_cost": {
            "current_pct": prime_pct,
            "previous_pct": prime_pct_prev,
            "delta_pct": round(prime_pct - prime_pct_prev, 2),
            "target_pct": PRIME_COST_TARGET_PCT,
            "color": ("red" if prime_pct > 60
                      else ("yellow" if prime_pct > PRIME_COST_TARGET_PCT else "green")),
        },
        # Section 3
        "food_cost": {
            "actual_pct": food_pct,
            "target_pct": target_food_pct,
            "previous_pct": food_pct_prev,
            "delta_pct": round(food_pct - food_pct_prev, 2),
            "amount": round(food_cost, 2),
            "color": ("red" if food_pct > target_food_pct + 3
                      else ("yellow" if food_pct > target_food_pct + 1 else "green")),
        },
        # Section 4
        "labor_cost": {
            "total_employees": emp_count,
            "labor_cost": round(labor_cost, 2),
            "labor_cost_pct": labor_pct,
            "labor_hours": round(hours, 1),
            "cost_per_employee": round(labor_cost / emp_count, 2) if emp_count else 0.0,
            "cost_per_hour": round(labor_cost / hours, 2) if hours else 0.0,
            "previous_pct": labor_pct_prev,
            "delta_pct": round(labor_pct - labor_pct_prev, 2),
            "color": ("red" if labor_pct > LABOR_COST_TARGET_PCT + 5
                      else ("yellow" if labor_pct > LABOR_COST_TARGET_PCT else "green")),
        },
        # Section 5
        "contribution_margin": {
            "sales": round(sales["sales"], 2),
            "food_cost": round(food_cost, 2),
            "margin": round(contribution_margin, 2),
            "margin_pct": cm_pct,
            "previous_pct": _safe_pct(p_sales["sales"] - p_food_cost, p_sales["sales"]),
        },
        # Section 6
        "orders_per_labor_hour": {
            "orders": sales["orders"],
            "labor_hours": round(hours, 1),
            "opl_h": opl_h,
            "previous_opl_h": p_opl_h,
            "delta_pct": _delta_pct(opl_h, p_opl_h),
        },
        # Section 7
        "expense_leakage": leakage,
        # Section 9
        "alerts": alerts,
        # Section 10
        "recommendations": recommendations,
        # Net profit context (for the np_pct comparison card)
        "net_profit_prev_pct": np_prev,
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class PeriodSpec(BaseModel):
    type: str = "month"               # month | quarter | fy | custom
    month: Optional[str] = None
    quarter: Optional[str] = None
    fy: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None


class CenterReq(BaseModel):
    token: str
    center: str
    period: PeriodSpec


class PortfolioReq(BaseModel):
    token: str
    period: PeriodSpec
    centers: Optional[List[str]] = None    # filter to a subset; default = all


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/center")
async def center_health(req: CenterReq):
    session = await check_access(req.token)
    # Manager → can only request own center
    if not (session.get("is_admin") or session.get("is_super_admin")):
        own = (session.get("center") or "").upper()
        if own and req.center.upper() != own:
            raise HTTPException(403, "You can only view your own center")
    snap = await _snapshot(req.center.upper(), req.period.dict())
    return snap


@router.post("/portfolio")
async def portfolio_health(req: PortfolioReq):
    """Section 11 — every center side-by-side with rankings."""
    session = await check_access(req.token)
    if not (session.get("is_admin") or session.get("is_super_admin")):
        raise HTTPException(403, "Portfolio view is admin-only")

    centers_q: Dict[str, Any] = {"code": {"$ne": "PB-DELETE"}}
    if req.centers:
        centers_q["code"] = {"$in": [c.upper() for c in req.centers]}
    cdocs = await db.centers.find(centers_q, {"_id": 0, "code": 1, "name": 1,
                                              "country": 1}).to_list(50)
    # Skip PB-MGT (HQ) which has no operating sales
    cdocs = [c for c in cdocs if c.get("code") and c["code"] != "PB-MGT"]

    rows: List[Dict[str, Any]] = []
    for c in cdocs:
        snap = await _snapshot(c["code"], req.period.dict())
        s = snap["summary"]
        rows.append({
            "center": c["code"],
            "center_name": c.get("name"),
            "country": c.get("country") or "India",
            "sales": s["total_sales"],
            "food_cost_pct": s["food_cost_pct"],
            "labor_cost_pct": s["labor_cost_pct"],
            "prime_cost_pct": s["prime_cost_pct"],
            "net_profit": s["net_profit"],
            "net_profit_pct": s["net_profit_pct"],
            "health_score": s["health_score"],
            "status": s["status"],
            "status_color": s["status_color"],
            "alerts": len(snap["alerts"]),
        })

    # Skip centers with no sales at all in the period (e.g. yet-to-open)
    rows_active = [r for r in rows if r["sales"] > 0]

    def _safe_max(key: str, want_max: bool = True) -> Optional[dict]:
        if not rows_active:
            return None
        return (max if want_max else min)(rows_active, key=lambda r: r[key])

    rankings = {
        "best_performing": _safe_max("health_score", True),
        "worst_performing": _safe_max("health_score", False),
        "highest_food_cost": _safe_max("food_cost_pct", True),
        "highest_labor_cost": _safe_max("labor_cost_pct", True),
        "highest_profit": _safe_max("net_profit", True),
        "lowest_profit": _safe_max("net_profit", False),
    }

    return {
        "period": _parse_period(req.period.dict()),
        "rows": rows,
        "rankings": rankings,
        "total_centers": len(rows),
        "active_centers": len(rows_active),
    }


@router.post("/list-centers")
async def list_centers_for_user(req_body: dict):
    """List centers the caller may query — used by the FE filter dropdown."""
    token = req_body.get("token")
    session = await check_access(token)
    q: Dict[str, Any] = {"code": {"$nin": ["PB-DELETE", "PB-MGT"]}}
    if not (session.get("is_admin") or session.get("is_super_admin")):
        own = (session.get("center") or "").upper()
        if own:
            q["code"] = own
    cdocs = await db.centers.find(q, {"_id": 0, "code": 1, "name": 1,
                                       "country": 1}).to_list(50)
    return {"centers": cdocs}
