"""Center Profitability Health Dashboard.

Endpoints (all under /api/health-dashboard):
  - POST /score          → full structured health payload for a center+month
  - POST /pdf            → downloadable PDF report (share with franchisee)
  - POST /centers        → list of centers the requester is allowed to view

Design notes:
  - ALL financial numbers reuse canonical helpers (gst.py, commissions.py, wc_chain.py)
    so they are byte-identical to MIS / Center Accounts / PIB.
  - Leakage + score is rule-based (deterministic). The AI layer (GPT-5.2 via
    Emergent Universal Key) generates ONLY the human narrative on top of the
    structured metrics — never the numbers themselves.
  - India + International both supported via center.country flag.
"""

from __future__ import annotations

import io
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server import db  # type: ignore
from routes.center_accounts import check_access, get_country_from_center, _is_staff
from utils.gst import (
    compute_gst_from_rows,
    gst_rate_for,
    eligible_base_from_daily_row,
)
from utils.commissions import get_total_commissions

load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health-dashboard", tags=["center-health"])

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class HealthRequest(BaseModel):
    token: str
    center: str
    month: str  # YYYY-MM


class CentersRequest(BaseModel):
    token: str


# ---------------------------------------------------------------------------
# Month utilities
# ---------------------------------------------------------------------------

def _months_back(month: str, n: int) -> List[str]:
    """Return ``n`` months ending at ``month`` (inclusive), oldest first."""
    y, m = int(month[:4]), int(month[5:7])
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(out))


def _prev_month(month: str) -> str:
    return _months_back(month, 2)[0]


def _yoy_month(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    return f"{y-1:04d}-{m:02d}"


def _month_label(month: str) -> str:
    try:
        return datetime.strptime(month + "-01", "%Y-%m-%d").strftime("%b %Y")
    except Exception:
        return month


# ---------------------------------------------------------------------------
# Data pull (shared with PDF + JSON)
# ---------------------------------------------------------------------------

async def _fetch_sales(center: str, month: str) -> List[dict]:
    cur = db.daily_sales.find({"center": center, "date": {"$regex": f"^{month}"}}, {"_id": 0})
    return await cur.to_list(None)


async def _fetch_expenses(center: str, month: str) -> List[dict]:
    cur = db.expenses.find({"center": center, "date": {"$regex": f"^{month}"}}, {"_id": 0})
    return await cur.to_list(None)


def _sum_sales(rows: List[dict]) -> Dict[str, float]:
    total = sum(float(r.get("total_sale") or 0) for r in rows)
    swiggy = sum(
        float(r.get("swiggy_sale") or r.get("swiggy") or 0) for r in rows
    )
    zomato = sum(
        float(r.get("zomato_sale") or r.get("zomato") or 0) for r in rows
    )
    doordash = sum(
        float(r.get("doordash_sale") or r.get("doordash") or 0) for r in rows
    )
    aggregator = swiggy + zomato + doordash
    dinein = max(0.0, total - aggregator)
    return {
        "total": round(total, 2),
        "aggregator": round(aggregator, 2),
        "swiggy": round(swiggy, 2),
        "zomato": round(zomato, 2),
        "doordash": round(doordash, 2),
        "dinein": round(dinein, 2),
        "bills_count": len(rows),
    }


def _expense_breakdown(rows: List[dict]) -> Dict[str, float]:
    cats: Dict[str, float] = {}
    for r in rows:
        cat = (r.get("expense_type") or "Other").strip() or "Other"
        cats[cat] = cats.get(cat, 0.0) + float(r.get("amount") or 0)
    return {k: round(v, 2) for k, v in sorted(cats.items(), key=lambda kv: -kv[1])}


async def _month_metrics(center: str, month: str, country: str) -> Dict[str, Any]:
    """Single-month canonical financial metrics for the health dashboard."""
    sales_rows = await _fetch_sales(center, month)
    expense_rows = await _fetch_expenses(center, month)
    sales = _sum_sales(sales_rows)
    expense_total = sum(float(r.get("amount") or 0) for r in expense_rows)
    expense_by_cat = _expense_breakdown(expense_rows)

    # Expense Adjustments (prepaid / advance carve) — subtracted from P/L
    # without modifying the raw expense rows. Single source of truth.
    from utils.adjustments import get_total_adjustments
    _adj_res = await get_total_adjustments(db, center, month)
    total_adjustments = float(_adj_res.get("total") or 0)
    adjusted_expenses = round(expense_total - total_adjustments, 2)

    gst_info = compute_gst_from_rows(sales_rows, country=country, center=center)
    gst_amount = float(gst_info.get("gst_amount") or 0)

    commission_info = await get_total_commissions(db, center, month)
    commission_total = float(commission_info.get("total") or 0)

    # Per-center per-month GST Revenue Treatment flag (Feb-2026 follow-up).
    # When ON, GST is NOT subtracted from Net Revenue / Net P/L so the
    # Center Health Dashboard mirrors the Center Accounts page.
    _gst_doc = await db.gst_treatment_overrides.find_one(
        {"center_code": (center or "").upper(), "month": month}
    )
    _include_gst_in_revenue = bool(_gst_doc and _gst_doc.get("include_gst_in_revenue", False))

    if _include_gst_in_revenue:
        net_revenue = sales["total"] - commission_total
    else:
        net_revenue = sales["total"] - commission_total - gst_amount
    # Net P/L uses ADJUSTED expenses so timing differences (e.g. June rent
    # paid in May) don't depress the wrong month's profitability.
    net_profit = net_revenue - adjusted_expenses

    return {
        "month": month,
        "label": _month_label(month),
        "sales": sales,
        "expenses_total": round(expense_total, 2),
        "expense_adjustments": round(total_adjustments, 2),
        "adjusted_expenses": adjusted_expenses,
        "expense_by_category": expense_by_cat,
        "gst": round(gst_amount, 2),
        "commission": round(commission_total, 2),
        "net_revenue": round(net_revenue, 2),
        "net_profit": round(net_profit, 2),
    }


async def _wc_snapshot(center: str, month: str) -> Dict[str, Any]:
    """Pull the canonical WC standing for the given month (single source)."""
    try:
        from routes.center_accounts import calculate_working_capital_standing

        center_doc = await db.centers.find_one({"code": center}, {"_id": 0}) or {}
        country = get_country_from_center(center_doc)
        wc = await calculate_working_capital_standing(db, center, month, country)
        return {
            "current_wc": float(wc.get("current_wc") or 0),
            "base_wc": float(wc.get("base_wc") or wc.get("initial_wc") or 0),
            "wc_pct": float(wc.get("wc_pct") or 0),
            "status": wc.get("status") or "—",
        }
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning(f"WC snapshot failed for {center} {month}: {exc}")
        return {"current_wc": 0.0, "base_wc": 0.0, "wc_pct": 0.0, "status": "N/A"}


# ---------------------------------------------------------------------------
# Leakage + score detection (rule-based, deterministic)
# ---------------------------------------------------------------------------

# Industry ideal ratios (% of sales) — sourced from internal benchmarking.
IDEAL = {
    "food_cost_pct": 32.0,
    "salary_pct": 22.0,
    "rent_pct": 10.0,
    "utility_pct": 4.0,
    "aggregator_share_pct": 40.0,  # aggregator share of total sales
    "commission_burden_pct": 6.0,  # commission as % of total sales
}

# Map known expense categories to internal buckets.
CATEGORY_BUCKETS = {
    "salary": ["salary", "wages", "staff", "payroll"],
    "rent": ["rent", "lease"],
    "food_cost": ["raw material", "vegetable", "groceries", "kitchen", "provisions", "food", "milk", "meat", "fish", "spice"],
    "utility": ["electricity", "gas", "lpg", "water", "internet", "telephone"],
    "packaging": ["packaging", "container", "disposable"],
    "marketing": ["marketing", "promotion", "advertis"],
    "petty": ["petty"],
    "maintenance": ["repair", "maintenance", "ame", "cleaning"],
}


def _bucketize(expense_by_cat: Dict[str, float]) -> Dict[str, float]:
    buckets = {k: 0.0 for k in CATEGORY_BUCKETS}
    buckets["other"] = 0.0
    for cat, amt in expense_by_cat.items():
        low = cat.lower()
        placed = False
        for bucket, kws in CATEGORY_BUCKETS.items():
            if any(k in low for k in kws):
                buckets[bucket] += amt
                placed = True
                break
        if not placed:
            buckets["other"] += amt
    return {k: round(v, 2) for k, v in buckets.items()}


def _pct(part: float, whole: float) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100.0, 2)


def _detect_leakages(
    current: Dict[str, Any],
    prev: Optional[Dict[str, Any]],
    buckets: Dict[str, float],
    wc: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Return prioritized leakage list with severity + estimated monthly impact."""
    leakages: List[Dict[str, Any]] = []
    sales_total = current["sales"]["total"]
    if sales_total <= 0:
        return leakages

    # 1. Aggregator dependency
    agg_pct = _pct(current["sales"]["aggregator"], sales_total)
    if agg_pct > IDEAL["aggregator_share_pct"]:
        impact = (agg_pct - IDEAL["aggregator_share_pct"]) / 100.0 * sales_total
        leakages.append({
            "category": "Aggregator Dependency",
            "severity": "high" if agg_pct > 60 else "medium",
            "detail": f"Swiggy / Zomato share is {agg_pct:.0f}% of total sales (ideal ≤ {IDEAL['aggregator_share_pct']:.0f}%). High platform commission + discount burden is eating into profitability.",
            "impact": round(impact * 0.18, 2),  # est lost margin = excess share × ~18% commission burden
        })

    # 2. Commission burden
    comm_pct = _pct(current["commission"], sales_total)
    if comm_pct > IDEAL["commission_burden_pct"]:
        leakages.append({
            "category": "Platform Commission Burden",
            "severity": "high" if comm_pct > 10 else "medium",
            "detail": f"Aggregator commissions are {comm_pct:.1f}% of sales (ideal ≤ {IDEAL['commission_burden_pct']:.0f}%). Renegotiate or reduce reliance on heavy-commission platforms.",
            "impact": round((comm_pct - IDEAL["commission_burden_pct"]) / 100.0 * sales_total, 2),
        })

    # 3. Salary ratio
    salary_pct = _pct(buckets.get("salary", 0), sales_total)
    if salary_pct > IDEAL["salary_pct"]:
        leakages.append({
            "category": "Overstaffing / Salary Bloat",
            "severity": "high" if salary_pct > 30 else "medium",
            "detail": f"Salary cost is {salary_pct:.1f}% of sales (ideal ≤ {IDEAL['salary_pct']:.0f}%). Review shift planning and weekday staffing.",
            "impact": round((salary_pct - IDEAL["salary_pct"]) / 100.0 * sales_total, 2),
        })

    # 4. Rent ratio
    rent_pct = _pct(buckets.get("rent", 0), sales_total)
    if rent_pct > IDEAL["rent_pct"]:
        leakages.append({
            "category": "Rent Pressure",
            "severity": "high" if rent_pct > 15 else "medium",
            "detail": f"Rent is {rent_pct:.1f}% of sales (ideal ≤ {IDEAL['rent_pct']:.0f}%). Sales must scale or negotiate the lease.",
            "impact": round((rent_pct - IDEAL["rent_pct"]) / 100.0 * sales_total, 2),
        })

    # 5. Food cost ratio
    food_pct = _pct(buckets.get("food_cost", 0), sales_total)
    if food_pct > IDEAL["food_cost_pct"]:
        leakages.append({
            "category": "Food Cost / Raw Material Leakage",
            "severity": "high" if food_pct > 40 else "medium",
            "detail": f"Raw-material cost is {food_pct:.1f}% of sales (ideal ≤ {IDEAL['food_cost_pct']:.0f}%). Check wastage, portion control, vendor rates.",
            "impact": round((food_pct - IDEAL["food_cost_pct"]) / 100.0 * sales_total, 2),
        })

    # 6. Utility spike
    utility_pct = _pct(buckets.get("utility", 0), sales_total)
    if utility_pct > IDEAL["utility_pct"]:
        leakages.append({
            "category": "High Utility Cost",
            "severity": "medium",
            "detail": f"Electricity / LPG / water is {utility_pct:.1f}% of sales (ideal ≤ {IDEAL['utility_pct']:.0f}%). Audit equipment usage.",
            "impact": round((utility_pct - IDEAL["utility_pct"]) / 100.0 * sales_total, 2),
        })

    # 7. WC depletion
    if wc.get("wc_pct", 100) < 50:
        leakages.append({
            "category": "Working Capital Depletion",
            "severity": "critical" if wc["wc_pct"] < 0 else "high",
            "detail": f"WC at {wc['wc_pct']:.0f}% of base. {'Negative — center is operating on borrowed capital.' if wc['wc_pct'] < 0 else 'Below 50% — replenishment required to avoid liquidity stress.'}",
            "impact": round(max(0.0, wc.get("base_wc", 0) - wc.get("current_wc", 0)), 2),
        })

    # 8. Sales drop vs previous month
    if prev:
        prev_sales = prev["sales"]["total"]
        if prev_sales > 0:
            drop = (sales_total - prev_sales) / prev_sales * 100.0
            if drop < -10:
                leakages.append({
                    "category": "Sales Drop",
                    "severity": "high" if drop < -20 else "medium",
                    "detail": f"Sales dropped {abs(drop):.0f}% vs {prev['label']} (₹{prev_sales:,.0f} → ₹{sales_total:,.0f}).",
                    "impact": round(prev_sales - sales_total, 2),
                })

    # 9. Negative P/L
    if current["net_profit"] < 0:
        leakages.append({
            "category": "Negative Profitability",
            "severity": "critical",
            "detail": f"Center is loss-making this month. Net P/L = ₹{current['net_profit']:,.0f}. Action required immediately.",
            "impact": abs(current["net_profit"]),
        })

    # Sort: critical → high → medium → low; tie-break by impact desc
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    leakages.sort(key=lambda x: (sev_order.get(x.get("severity"), 9), -x.get("impact", 0)))
    return leakages


def _compute_score(
    current: Dict[str, Any],
    buckets: Dict[str, float],
    wc: Dict[str, Any],
    leakages: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Composite 0-100 score → tier mapping. Heuristic but stable."""
    score = 100.0
    sales = current["sales"]["total"]

    # Severity-based deductions from leakages (most impactful single signal).
    for lk in leakages:
        sev = lk.get("severity")
        if sev == "critical":
            score -= 25
        elif sev == "high":
            score -= 12
        elif sev == "medium":
            score -= 5

    # Bonus / penalty on net P/L margin
    if sales > 0:
        margin = current["net_profit"] / sales * 100.0
        if margin >= 15:
            score += 5
        elif margin < 0:
            score -= 5

    # WC bias
    wc_pct = wc.get("wc_pct", 100)
    if wc_pct >= 100:
        score += 3
    elif wc_pct < 0:
        score -= 8

    score = max(0.0, min(100.0, score))

    if score >= 85:
        tier, color = "Excellent", "emerald"
    elif score >= 70:
        tier, color = "Stable", "green"
    elif score >= 50:
        tier, color = "Warning", "amber"
    elif score >= 30:
        tier, color = "Critical", "orange"
    else:
        tier, color = "Dangerous", "red"

    return {"score": round(score, 1), "tier": tier, "color": color}


def _corrective_actions(leakages: List[Dict[str, Any]], current: Dict[str, Any]) -> List[str]:
    """Deterministic baseline action list — AI layer can add nuance later."""
    actions: List[str] = []
    cats = {lk["category"] for lk in leakages}

    if "Aggregator Dependency" in cats or "Platform Commission Burden" in cats:
        actions.append("Launch dine-in only weekly combos and weekday lunch offers to rebalance the channel mix.")
        actions.append("Reduce deep-discount campaigns on Swiggy / Zomato — keep listing but pull discount aggressiveness.")
    if "Overstaffing / Salary Bloat" in cats:
        actions.append("Move to demand-based shift planning; trim 1 weekday lunch shift slot to recover salary ratio.")
    if "Rent Pressure" in cats:
        actions.append("Initiate landlord renegotiation citing the current sales-to-rent ratio.")
    if "Food Cost / Raw Material Leakage" in cats:
        actions.append("Run a 1-week kitchen wastage audit; lock vendor rates for top-5 SKUs.")
    if "High Utility Cost" in cats:
        actions.append("Schedule an equipment usage audit (LPG/AC/exhaust) — flag anything operating outside service hours.")
    if "Sales Drop" in cats:
        actions.append("Activate WhatsApp + Google MyBusiness push for the week; trigger repeat-customer voucher.")
    if "Working Capital Depletion" in cats:
        actions.append("Defer non-critical capex; escalate WC replenishment with the Accounts team.")
    if "Negative Profitability" in cats:
        actions.append("Freeze discretionary spends — escalate to Founder for category-by-category cost approval.")

    if not actions:
        actions.append("Current performance is healthy — focus on consolidation. Re-run after end-of-month close.")
    # Cap to a clean list (no dupes, max 8)
    seen = set()
    deduped = []
    for a in actions:
        if a not in seen:
            deduped.append(a)
            seen.add(a)
        if len(deduped) >= 8:
            break
    return deduped


# ---------------------------------------------------------------------------
# AI narrative (GPT-5.2 via Emergent Universal Key)
# ---------------------------------------------------------------------------

async def _ai_narrative(payload: Dict[str, Any], country: str) -> Dict[str, str]:
    """Returns {founder_summary, predictive_warning, ai_action_addon}.
    Safe-falls back to deterministic text if LLM unavailable.
    """
    fallback = {
        "founder_summary": _fallback_summary(payload, country),
        "predictive_warning": _fallback_predictive(payload),
    }
    if not EMERGENT_LLM_KEY:
        return fallback

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore

        symbol = "AUD" if country == "Australia" else "INR"
        cur = payload["current"]
        prev = payload.get("previous") or {}
        score = payload["score"]
        leak_list = "; ".join(
            f"{lk['category']} ({lk['severity']})" for lk in payload["leakages"][:6]
        ) or "no major leakages"

        system = (
            "You are a sharp, no-nonsense CFO advisor for a multi-center restaurant "
            "franchise. Write in clear, calm executive English as plain prose. "
            "NEVER use markdown headings (##, ###), bullet points, or labels — only flowing paragraphs. "
            "NEVER invent numbers — use only the metrics provided. "
            "Separate the two sections with exactly one blank line, in this order:\n"
            "Paragraph 1: Founder's Reality Check (80-120 words, single paragraph, no heading)\n"
            "Paragraph 2: Predictive 3-Month Warning (60-90 words, single paragraph, no heading)"
        )

        user_text = (
            f"Center: {payload['center']} | Month: {cur['label']} | Country: {country} ({symbol})\n"
            f"Health Score: {score['score']}/100 ({score['tier']})\n"
            f"Sales: {cur['sales']['total']:,.0f} (Dine-in {cur['sales']['dinein']:,.0f} / Aggregator {cur['sales']['aggregator']:,.0f})\n"
            f"Commission: {cur['commission']:,.0f} | GST: {cur['gst']:,.0f}\n"
            f"Net Revenue: {cur['net_revenue']:,.0f} | Expenses: {cur['expenses_total']:,.0f}\n"
            f"Net P/L: {cur['net_profit']:,.0f}\n"
            f"Working Capital: {payload['wc']['current_wc']:,.0f} ({payload['wc']['wc_pct']:.0f}% of base)\n"
            f"Prev Month Sales: {prev.get('sales', {}).get('total', 0):,.0f} | Prev P/L: {prev.get('net_profit', 0):,.0f}\n"
            f"Active leakages: {leak_list}\n\n"
            "Write the two sections now."
        )

        chat = (
            LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"health-{payload['center']}-{cur['month']}",
                system_message=system,
            ).with_model("openai", "gpt-5.2")
        )
        resp = await chat.send_message(UserMessage(text=user_text))
        text = (resp or "").strip()

        # Lightweight parsing — accept various heading conventions.
        summary = predictive = ""
        if "SECTION 2" in text.upper():
            parts = text.split("SECTION 2", 1)
            summary = parts[0].replace("SECTION 1", "").replace("Founder's Reality Check", "").strip(":\n ")
            tail = parts[1].split(":", 1)[-1].strip()
            predictive = tail
        elif "\n\n" in text:
            a, b = text.split("\n\n", 1)
            summary, predictive = a.strip(), b.strip()
        else:
            summary = text
            predictive = fallback["predictive_warning"]

        summary = _clean_narrative(summary)
        predictive = _clean_narrative(predictive)
        return {
            "founder_summary": summary or fallback["founder_summary"],
            "predictive_warning": predictive or fallback["predictive_warning"],
        }
    except Exception as exc:
        logger.warning(f"AI narrative failed: {exc}")
        return fallback


def _clean_narrative(text: str) -> str:
    """Strip markdown headings, stray section labels, and tidy whitespace."""
    if not text:
        return ""
    import re
    lines = []
    for ln in text.splitlines():
        # drop markdown headings (## , ###  etc.) and section label echoes
        stripped = ln.strip()
        if not stripped:
            lines.append("")
            continue
        if re.match(r"^#{1,6}\s*:?\s*$", stripped):
            continue
        # remove leading "## "
        cleaned = re.sub(r"^#{1,6}\s*", "", stripped)
        # drop lines that are just section labels
        if re.match(r"^(SECTION\s*\d|Founder['']?s? Reality Check|Predictive\s*3[- ]Month\s*Warning)\s*:?$", cleaned, re.I):
            continue
        # remove inline section labels at start of paragraph
        cleaned = re.sub(r"^(SECTION\s*\d+\s*:?\s*)", "", cleaned, flags=re.I)
        cleaned = re.sub(r"^(Founder['']?s? Reality Check\s*:?\s*)", "", cleaned, flags=re.I)
        cleaned = re.sub(r"^(Predictive\s*3[- ]Month\s*Warning\s*:?\s*)", "", cleaned, flags=re.I)
        lines.append(cleaned)
    out = "\n".join(lines).strip()
    # collapse 3+ newlines to 2
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out


def _fallback_summary(payload: Dict[str, Any], country: str) -> str:
    cur = payload["current"]
    score = payload["score"]
    tier = score["tier"]
    if cur["sales"]["total"] <= 0:
        return f"No sales recorded for {cur['label']}. Confirm whether the center was operational and uploads are complete."
    profit_line = (
        f"closed with a profit of ₹{cur['net_profit']:,.0f}"
        if cur["net_profit"] > 0
        else f"closed at a loss of ₹{abs(cur['net_profit']):,.0f}"
    )
    return (
        f"{payload['center']} {profit_line} on sales of ₹{cur['sales']['total']:,.0f} in {cur['label']} — "
        f"overall health is rated {tier}. Aggregator share stood at "
        f"{_pct(cur['sales']['aggregator'], cur['sales']['total']):.0f}% with platform commissions of ₹{cur['commission']:,.0f} and GST of ₹{cur['gst']:,.0f}. "
        f"Focus the next 30 days on the highest-severity leakages flagged below."
    )


def _fallback_predictive(payload: Dict[str, Any]) -> str:
    sev = {lk["severity"] for lk in payload["leakages"]}
    if "critical" in sev:
        return "If the current pattern continues, working capital and profitability will deteriorate sharply over the next 3 months. Immediate corrective action is required to avoid a liquidity event."
    if "high" in sev:
        return "Several high-severity signals are active. Without correction, expect margin compression of 5–10% over the next quarter."
    return "Pattern is stable. Maintain current discipline and monitor for any sustained drop in dine-in conversion or sudden cost spikes."


# ---------------------------------------------------------------------------
# Access helpers
# ---------------------------------------------------------------------------

async def _accessible_centers(session: dict) -> List[str]:
    if _is_staff(session):
        cur = db.centers.find({}, {"_id": 0, "code": 1, "name": 1, "country": 1, "is_india_center": 1})
    else:
        owned = session.get("center") or ""
        franchise_code = session.get("franchise_code")
        q = {"$or": []}
        if owned:
            q["$or"].append({"code": owned})
        if franchise_code:
            q["$or"].append({"franchise_code": franchise_code})
        if not q["$or"]:
            return []
        cur = db.centers.find(q, {"_id": 0, "code": 1, "name": 1, "country": 1, "is_india_center": 1})
    out = []
    async for c in cur:
        if c.get("code") == "PB-MGT":
            continue  # management entity, not an operational center
        out.append(c)
    return out


async def _enforce_center_access(session: dict, center: str) -> dict:
    """Ensure the session can view this center. Returns the centers doc."""
    center_doc = await db.centers.find_one({"code": center}, {"_id": 0})
    if not center_doc:
        raise HTTPException(404, f"Center {center} not found")
    if _is_staff(session):
        return center_doc
    # Franchise owner / restricted role
    if session.get("center") == center:
        return center_doc
    if session.get("franchise_code") and center_doc.get("franchise_code") == session.get("franchise_code"):
        return center_doc
    raise HTTPException(403, "You do not have access to this center's health dashboard.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/centers")
async def list_centers(req: CentersRequest):
    session = await check_access(req.token)
    centers = await _accessible_centers(session)
    return {"centers": [{"code": c["code"], "name": c.get("name") or c["code"], "country": c.get("country") or ("Australia" if not c.get("is_india_center", True) else "India")} for c in centers]}


async def _build_health_payload(req: HealthRequest) -> Dict[str, Any]:
    session = await check_access(req.token)
    center_doc = await _enforce_center_access(session, req.center)
    country = get_country_from_center(center_doc)
    currency = "AUD" if country == "Australia" else "INR"

    current = await _month_metrics(req.center, req.month, country)
    prev_month = _prev_month(req.month)
    prev = await _month_metrics(req.center, prev_month, country) if prev_month else None
    yoy_month = _yoy_month(req.month)
    yoy = await _month_metrics(req.center, yoy_month, country) if yoy_month else None

    # Last 12 months trend (sales, net P/L)
    trend_months = _months_back(req.month, 12)
    trend = []
    for m in trend_months:
        mm = await _month_metrics(req.center, m, country)
        trend.append({
            "month": m,
            "label": _month_label(m),
            "sales": mm["sales"]["total"],
            "expenses": mm["expenses_total"],
            "commission": mm["commission"],
            "gst": mm["gst"],
            "net_profit": mm["net_profit"],
            "dinein": mm["sales"]["dinein"],
            "aggregator": mm["sales"]["aggregator"],
        })

    buckets = _bucketize(current["expense_by_category"])
    wc = await _wc_snapshot(req.center, req.month)
    leakages = _detect_leakages(current, prev, buckets, wc)
    score = _compute_score(current, buckets, wc, leakages)
    actions = _corrective_actions(leakages, current)

    sales_total = current["sales"]["total"] or 1
    ratios = {
        "food_cost_pct": _pct(buckets.get("food_cost", 0), sales_total),
        "salary_pct": _pct(buckets.get("salary", 0), sales_total),
        "rent_pct": _pct(buckets.get("rent", 0), sales_total),
        "utility_pct": _pct(buckets.get("utility", 0), sales_total),
        "packaging_pct": _pct(buckets.get("packaging", 0), sales_total),
        "marketing_pct": _pct(buckets.get("marketing", 0), sales_total),
        "commission_pct": _pct(current["commission"], sales_total),
        "gst_pct": _pct(current["gst"], sales_total),
        "aggregator_share_pct": _pct(current["sales"]["aggregator"], sales_total),
        "net_margin_pct": _pct(current["net_profit"], sales_total),
    }

    payload = {
        "center": req.center,
        "center_name": center_doc.get("name") or req.center,
        "country": country,
        "currency": currency,
        "month": req.month,
        "current": current,
        "previous": prev,
        "yoy": yoy,
        "wc": wc,
        "expense_buckets": buckets,
        "ratios": ratios,
        "ideal_ratios": IDEAL,
        "leakages": leakages,
        "actions": actions,
        "score": score,
        "trend": trend,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    narrative = await _ai_narrative(payload, country)
    payload["narrative"] = narrative
    return payload


@router.post("/score")
async def health_score(req: HealthRequest):
    return await _build_health_payload(req)


# ---------------------------------------------------------------------------
# PDF generation (shareable with franchisees)
# ---------------------------------------------------------------------------

def _build_pdf(payload: Dict[str, Any]) -> bytes:
    """Render the health dashboard as a clean PDF using reportlab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    )

    try:
        from utils.signature import signature_block
    except Exception:
        signature_block = None  # type: ignore

    cur = payload["current"]
    score = payload["score"]
    wc = payload["wc"]
    cur_sym = "AUD " if payload["currency"] == "AUD" else "₹"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=0.5 * inch, rightMargin=0.5 * inch,
        topMargin=0.55 * inch, bottomMargin=0.55 * inch,
        title=f"Health Dashboard — {payload['center']} {cur['label']}",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=18, textColor=colors.HexColor("#5C0000"), spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#5C0000"), spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9.5, leading=13)
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8.5, textColor=colors.grey)

    tier_color_map = {
        "Excellent": colors.HexColor("#059669"),
        "Stable": colors.HexColor("#16a34a"),
        "Warning": colors.HexColor("#d97706"),
        "Critical": colors.HexColor("#ea580c"),
        "Dangerous": colors.HexColor("#dc2626"),
    }
    tier_col = tier_color_map.get(score["tier"], colors.grey)

    story = []
    story.append(Paragraph("<b>Center Profitability Health Dashboard</b>", h1))
    story.append(Paragraph(
        f"<b>{payload['center_name']} ({payload['center']})</b> &nbsp;·&nbsp; "
        f"Month: <b>{cur['label']}</b> &nbsp;·&nbsp; Country: {payload['country']}",
        body
    ))
    story.append(Spacer(1, 6))

    # Health Score block
    score_table = Table([[
        Paragraph(f"<b>Health Score</b><br/><font size=22 color='{tier_col.hexval()}'>{score['score']:.0f}</font><br/><font size=10 color='{tier_col.hexval()}'><b>{score['tier']}</b></font>", body),
        Paragraph(
            f"<b>Founder's Reality Check</b><br/><br/>{payload['narrative']['founder_summary']}",
            body
        ),
    ]], colWidths=[1.4 * inch, 5.6 * inch])
    score_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#fef3c7")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#fffbeb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 10))

    # Profitability table (transparently shows expense adjustments)
    story.append(Paragraph("Profitability Formula", h2))
    _adj_amt = cur.get("expense_adjustments", 0) or 0
    _adj_exp = cur.get("adjusted_expenses", cur["expenses_total"])
    pf_data = [
        ["Total Sales", f"{cur_sym}{cur['sales']['total']:,.0f}"],
        ["Less: Platform Commission", f"({cur_sym}{cur['commission']:,.0f})"],
        ["Less: GST (carved inclusive)", f"({cur_sym}{cur['gst']:,.0f})"],
        ["= Net Revenue", f"{cur_sym}{cur['net_revenue']:,.0f}"],
        ["Less: Total Expenses", f"({cur_sym}{cur['expenses_total']:,.0f})"],
    ]
    # Insert adjustment lines only when there are adjustments — keeps the
    # report visually identical for months without any carve.
    bold_idx = 5  # default Net Profit row index
    if _adj_amt > 0:
        pf_data.append(["  Add back: Less Adjustments", f"{cur_sym}{_adj_amt:,.0f}"])
        pf_data.append(["= Adjusted Expenses", f"({cur_sym}{_adj_exp:,.0f})"])
        bold_idx = 7
    pf_data.append(["= Net Profit / (Loss)", f"{cur_sym}{cur['net_profit']:,.0f}"])

    pf_table = Table(pf_data, colWidths=[4.5 * inch, 2.5 * inch])
    pf_table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9.5),
        ("FONT", (0, 3), (-1, 3), "Helvetica-Bold", 9.5),
        ("FONT", (0, bold_idx), (-1, bold_idx), "Helvetica-Bold", 10.5),
        ("BACKGROUND", (0, bold_idx), (-1, bold_idx),
         colors.HexColor("#dcfce7") if cur["net_profit"] >= 0 else colors.HexColor("#fee2e2")),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#f1f5f9")),
        ("LINEBELOW", (0, 2), (-1, 2), 0.5, colors.grey),
        ("LINEBELOW", (0, bold_idx - 1), (-1, bold_idx - 1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(pf_table)

    # WC + Ratios
    story.append(Paragraph("Working Capital Health", h2))
    wc_table = Table([
        ["Current WC", f"{cur_sym}{wc['current_wc']:,.0f}"],
        ["Base WC", f"{cur_sym}{wc['base_wc']:,.0f}"],
        ["WC % of Base", f"{wc['wc_pct']:.0f}%"],
        ["Status", wc["status"]],
    ], colWidths=[4.5 * inch, 2.5 * inch])
    wc_table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9.5),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#e2e8f0")),
    ]))
    story.append(wc_table)

    # Key ratios
    story.append(Paragraph("Operational Ratios (% of Sales)", h2))
    r = payload["ratios"]
    ideal = payload["ideal_ratios"]
    ratio_rows = [["Ratio", "Current", "Ideal ≤", "Status"]]
    def _row(name, key, ideal_key):
        v = r.get(key, 0)
        i = ideal.get(ideal_key, 0)
        status = "✓ OK" if v <= i else ("⚠ High" if v <= i * 1.3 else "✗ Critical")
        return [name, f"{v:.1f}%", f"{i:.0f}%", status]
    ratio_rows.append(_row("Food Cost", "food_cost_pct", "food_cost_pct"))
    ratio_rows.append(_row("Salary", "salary_pct", "salary_pct"))
    ratio_rows.append(_row("Rent", "rent_pct", "rent_pct"))
    ratio_rows.append(_row("Utility", "utility_pct", "utility_pct"))
    ratio_rows.append(_row("Commission Burden", "commission_pct", "commission_burden_pct"))
    ratio_rows.append(_row("Aggregator Share", "aggregator_share_pct", "aggregator_share_pct"))
    ratio_rows.append(["Net Margin", f"{r['net_margin_pct']:.1f}%", "≥ 10%", "✓ OK" if r["net_margin_pct"] >= 10 else "⚠ Watch" if r["net_margin_pct"] >= 0 else "✗ Negative"])
    ratio_t = Table(ratio_rows, colWidths=[2.6 * inch, 1.3 * inch, 1.3 * inch, 1.8 * inch])
    ratio_t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9.5),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fde68a")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
    ]))
    story.append(ratio_t)

    # Leakages
    if payload["leakages"]:
        story.append(Paragraph("Monthly Leakage Analysis", h2))
        leak_rows = [["Category", "Severity", "Detail", "Est. Impact"]]
        for lk in payload["leakages"]:
            leak_rows.append([
                lk["category"],
                lk["severity"].upper(),
                Paragraph(lk["detail"], small),
                f"{cur_sym}{lk['impact']:,.0f}",
            ])
        leak_t = Table(leak_rows, colWidths=[1.7 * inch, 0.8 * inch, 3.3 * inch, 1.2 * inch])
        leak_t.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9.5),
            ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fee2e2")),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#fecaca")),
        ]))
        story.append(leak_t)

    # Actions
    story.append(Paragraph("What Needs Correction", h2))
    for i, a in enumerate(payload["actions"], 1):
        story.append(Paragraph(f"<b>{i}.</b> {a}", body))

    # Predictive
    story.append(Paragraph("Predictive 3-Month Warning", h2))
    story.append(Paragraph(payload["narrative"]["predictive_warning"], body))

    # 12-month trend (compact table)
    story.append(PageBreak())
    story.append(Paragraph("12-Month Trend", h1))
    trend_rows = [["Month", "Sales", "Expenses", "Comm", "GST", "Net P/L", "Dine-in %"]]
    for t in payload["trend"]:
        din_pct = (t["dinein"] / t["sales"] * 100.0) if t["sales"] > 0 else 0
        trend_rows.append([
            t["label"],
            f"{cur_sym}{t['sales']:,.0f}",
            f"{cur_sym}{t['expenses']:,.0f}",
            f"{cur_sym}{t['commission']:,.0f}",
            f"{cur_sym}{t['gst']:,.0f}",
            f"{cur_sym}{t['net_profit']:,.0f}",
            f"{din_pct:.0f}%",
        ])
    trend_t = Table(trend_rows, repeatRows=1, colWidths=[0.9*inch, 1.1*inch, 1.05*inch, 0.9*inch, 0.9*inch, 1.1*inch, 0.8*inch])
    trend_t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9.5),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fde68a")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
    ]))
    story.append(trend_t)

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"Generated by Purnabramha IntraPB · {payload['generated_at'][:19]} UTC · Health score and leakage detection are computed from canonical financial helpers; the narrative paragraphs are AI-assisted (GPT-5.2) and should be reviewed before sharing externally.",
        small,
    ))

    # Signature block (re-uses the standard accounts signature)
    if signature_block is not None:
        try:
            story.append(Spacer(1, 14))
            sig = signature_block(payload["country"], label="Accounts")
            if isinstance(sig, list):
                story.extend(sig)
            else:
                story.append(sig)
        except Exception:
            pass

    doc.build(story)
    return buf.getvalue()


@router.post("/pdf")
async def health_pdf(req: HealthRequest):
    payload = await _build_health_payload(req)
    pdf_bytes = _build_pdf(payload)
    filename = f"health_{req.center}_{req.month}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
