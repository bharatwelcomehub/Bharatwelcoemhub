"""Financial Insights — embedded tab under Center Accounts.

Endpoints under /api/financial-insights:
  - POST /summary    → structured analytics for the selected period(s) + centers
  - POST /export     → Excel / CSV / PDF download
  - POST /drill-down → category-level breakdown (expense category, sales channel)

Reuses canonical helpers (gst.py, commissions.py, wc_chain.py) so numbers stay
byte-identical to MIS / Center Accounts / PIB / Health Dashboard.
"""

from __future__ import annotations

import csv
import io
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server import db  # type: ignore
from routes.center_accounts import check_access, get_country_from_center, _is_staff
from routes.center_health import (
    _month_metrics, _months_back, _month_label, CATEGORY_BUCKETS, IDEAL,
    _bucketize, _pct, _wc_snapshot, _ai_narrative,
)

load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/financial-insights", tags=["financial-insights"])

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class InsightsRequest(BaseModel):
    token: str
    centers: List[str]                # one or many; staff can pass multiple, FO single
    period_type: str                  # 'month' | 'month_range' | 'fy' | 'custom'
    month: Optional[str] = None       # YYYY-MM for 'month'
    from_month: Optional[str] = None  # YYYY-MM for 'month_range'
    to_month: Optional[str] = None    # YYYY-MM for 'month_range'
    fy: Optional[str] = None          # 'FY 2025-26' or '2025-26'
    from_date: Optional[str] = None   # YYYY-MM-DD for 'custom'
    to_date: Optional[str] = None     # YYYY-MM-DD for 'custom'
    compare_previous: bool = True


class ExportRequest(InsightsRequest):
    format: str = "excel"             # excel | csv


class DrillRequest(BaseModel):
    token: str
    center: str
    month: str
    dimension: str                    # 'expense_category' | 'sales_channel'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fy_to_months(fy: str) -> List[str]:
    """'FY 2025-26' or '2025-26' → ['2025-04', ..., '2026-03']."""
    raw = fy.replace("FY", "").strip()
    parts = raw.split("-")
    if len(parts) != 2:
        raise HTTPException(400, f"Invalid FY '{fy}'. Expected 'FY 2025-26'.")
    start_year = int(parts[0])
    end_year_short = int(parts[1])
    end_year = start_year + 1 if end_year_short < 100 else end_year_short
    months = []
    y, m = start_year, 4
    for _ in range(12):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            m = 1
            y += 1
        if y == end_year and m == 4:
            break
    return months


def _months_between(start: str, end: str) -> List[str]:
    """Inclusive month list from start (YYYY-MM) to end (YYYY-MM)."""
    if start > end:
        start, end = end, start
    months = []
    sy, sm = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    while (sy, sm) <= (ey, em):
        months.append(f"{sy:04d}-{sm:02d}")
        sm += 1
        if sm == 13:
            sm = 1
            sy += 1
    return months


def _resolve_months(req: InsightsRequest) -> Tuple[List[str], str]:
    """Return (months_list, human_label) for the current period."""
    pt = req.period_type
    if pt == "month":
        if not req.month:
            raise HTTPException(400, "month is required for period_type=month")
        return [req.month], _month_label(req.month)
    if pt == "month_range":
        if not (req.from_month and req.to_month):
            raise HTTPException(400, "from_month and to_month are required")
        months = _months_between(req.from_month, req.to_month)
        return months, f"{_month_label(months[0])} – {_month_label(months[-1])}"
    if pt == "fy":
        if not req.fy:
            raise HTTPException(400, "fy is required for period_type=fy")
        months = _fy_to_months(req.fy)
        return months, req.fy if req.fy.startswith("FY") else f"FY {req.fy}"
    if pt == "custom":
        if not (req.from_date and req.to_date):
            raise HTTPException(400, "from_date and to_date are required")
        # Build month range from custom dates (we still pull per-month data; date
        # boundaries are applied below in _custom_period_metrics).
        months = _months_between(req.from_date[:7], req.to_date[:7])
        return months, f"{req.from_date} → {req.to_date}"
    raise HTTPException(400, f"Unknown period_type {pt}")


def _shift_period_backwards(months: List[str]) -> List[str]:
    """Build the immediately-preceding period of the same length."""
    n = len(months)
    return _months_back(months[0], n + 1)[:n]


async def _accessible_centers_for(session: dict, requested: List[str]) -> List[str]:
    """Validate and return centers the requester can analyse."""
    if not requested:
        raise HTTPException(400, "centers is required")
    if _is_staff(session):
        return [c for c in requested if c != "PB-MGT"] or requested
    # Franchise owner / restricted role: only own center
    owned = session.get("center")
    franchise_code = session.get("franchise_code")
    allowed = set()
    if owned:
        allowed.add(owned)
    if franchise_code:
        cur = db.centers.find({"franchise_code": franchise_code}, {"_id": 0, "code": 1})
        async for c in cur:
            allowed.add(c["code"])
    cleaned = [c for c in requested if c in allowed]
    if not cleaned:
        raise HTTPException(403, "You do not have access to the requested centers.")
    return cleaned


async def _aggregate_period(centers: List[str], months: List[str]) -> Dict[str, Any]:
    """Aggregate metrics across one or many centers over the given month list."""
    country_of: Dict[str, str] = {}
    for code in centers:
        c = await db.centers.find_one({"code": code}, {"_id": 0}) or {}
        country_of[code] = get_country_from_center(c)

    # Build per-month merged metrics (across all centers requested)
    by_month: Dict[str, Dict[str, Any]] = {}
    per_center_total: Dict[str, Dict[str, float]] = {c: {"sales": 0, "expenses": 0, "net_profit": 0, "commission": 0, "gst": 0} for c in centers}

    for m in months:
        agg = {
            "month": m, "label": _month_label(m),
            "sales": 0.0, "swiggy": 0.0, "zomato": 0.0, "doordash": 0.0,
            "aggregator": 0.0, "dinein": 0.0, "bills_count": 0,
            "expenses": 0.0, "expense_by_category": {},
            "expense_adjustments": 0.0, "adjusted_expenses": 0.0,
            "commission": 0.0, "gst": 0.0,
            "net_revenue": 0.0, "net_profit": 0.0,
        }
        for c in centers:
            mm = await _month_metrics(c, m, country_of.get(c, "India"))
            agg["sales"] += mm["sales"]["total"]
            agg["swiggy"] += mm["sales"]["swiggy"]
            agg["zomato"] += mm["sales"]["zomato"]
            agg["doordash"] += mm["sales"]["doordash"]
            agg["aggregator"] += mm["sales"]["aggregator"]
            agg["dinein"] += mm["sales"]["dinein"]
            agg["bills_count"] += mm["sales"]["bills_count"]
            agg["expenses"] += mm["expenses_total"]
            agg["expense_adjustments"] += mm.get("expense_adjustments", 0.0)
            agg["adjusted_expenses"] += mm.get("adjusted_expenses", mm["expenses_total"])
            agg["commission"] += mm["commission"]
            agg["gst"] += mm["gst"]
            agg["net_revenue"] += mm["net_revenue"]
            agg["net_profit"] += mm["net_profit"]
            for k, v in mm["expense_by_category"].items():
                agg["expense_by_category"][k] = agg["expense_by_category"].get(k, 0.0) + v
            # per-center roll-up
            per_center_total[c]["sales"] += mm["sales"]["total"]
            per_center_total[c]["expenses"] += mm["expenses_total"]
            per_center_total[c]["commission"] += mm["commission"]
            per_center_total[c]["gst"] += mm["gst"]
            per_center_total[c]["net_profit"] += mm["net_profit"]
        by_month[m] = agg

    # Period totals
    total = {
        "sales": sum(v["sales"] for v in by_month.values()),
        "swiggy": sum(v["swiggy"] for v in by_month.values()),
        "zomato": sum(v["zomato"] for v in by_month.values()),
        "doordash": sum(v["doordash"] for v in by_month.values()),
        "aggregator": sum(v["aggregator"] for v in by_month.values()),
        "dinein": sum(v["dinein"] for v in by_month.values()),
        "bills_count": sum(v["bills_count"] for v in by_month.values()),
        "expenses": sum(v["expenses"] for v in by_month.values()),
        "expense_adjustments": sum(v.get("expense_adjustments", 0.0) for v in by_month.values()),
        "adjusted_expenses": sum(v.get("adjusted_expenses", v["expenses"]) for v in by_month.values()),
        "commission": sum(v["commission"] for v in by_month.values()),
        "gst": sum(v["gst"] for v in by_month.values()),
        "net_revenue": sum(v["net_revenue"] for v in by_month.values()),
        "net_profit": sum(v["net_profit"] for v in by_month.values()),
        "expense_by_category": {},
    }
    for m in by_month.values():
        for k, v in m["expense_by_category"].items():
            total["expense_by_category"][k] = total["expense_by_category"].get(k, 0.0) + v

    buckets = _bucketize(total["expense_by_category"])
    sales = total["sales"] or 1
    ratios = {
        "food_cost_pct": _pct(buckets.get("food_cost", 0), sales),
        "salary_pct": _pct(buckets.get("salary", 0), sales),
        "rent_pct": _pct(buckets.get("rent", 0), sales),
        "utility_pct": _pct(buckets.get("utility", 0), sales),
        "packaging_pct": _pct(buckets.get("packaging", 0), sales),
        "marketing_pct": _pct(buckets.get("marketing", 0), sales),
        "maintenance_pct": _pct(buckets.get("maintenance", 0), sales),
        "commission_pct": _pct(total["commission"], sales),
        "gst_pct": _pct(total["gst"], sales),
        "aggregator_share_pct": _pct(total["aggregator"], sales),
        "dinein_share_pct": _pct(total["dinein"], sales),
        "net_margin_pct": _pct(total["net_profit"], sales),
        "expense_to_sales_pct": _pct(total["expenses"], sales),
        "operational_cost_pct": _pct(total["expenses"] + total["commission"], sales),
    }

    # Gross profit ≈ Sales − Raw Material − Commission − GST. (Net profit also subtracts all other expenses.)
    gross_profit = sales - buckets.get("food_cost", 0) - total["commission"] - total["gst"]
    if sales <= 1:
        gross_profit = 0.0
    return {
        "total": {**total, "gross_profit": round(gross_profit, 2)},
        "by_month": list(by_month.values()),
        "per_center": {c: {k: round(v, 2) for k, v in d.items()} for c, d in per_center_total.items()},
        "buckets": buckets,
        "ratios": ratios,
        "country_of": country_of,
    }


def _delta_pct(curr: float, prev: float) -> Optional[float]:
    if abs(prev) < 0.01:
        return None
    return round(((curr - prev) / abs(prev)) * 100.0, 1)


def _ratio_status(value: float, ideal: float) -> str:
    if value <= ideal:
        return "good"
    if value <= ideal * 1.3:
        return "warning"
    return "critical"


# ---------------------------------------------------------------------------
# AI summary
# ---------------------------------------------------------------------------

async def _ai_executive_summary(payload: Dict[str, Any]) -> str:
    """Short executive 1-paragraph AI summary using GPT-5.2."""
    fallback = _fallback_executive(payload)
    if not EMERGENT_LLM_KEY:
        return fallback
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        current = payload["current"]["total"]
        prev = (payload.get("previous") or {}).get("total") or {}
        r = payload["current"]["ratios"]
        delta_sales = _delta_pct(current["sales"], prev.get("sales", 0)) if prev else None
        delta_profit = _delta_pct(current["net_profit"], prev.get("net_profit", 0)) if prev else None
        ctx = (
            f"Centers: {', '.join(payload['centers'])}\n"
            f"Period: {payload['period_label']}\n"
            f"Sales: {current['sales']:,.0f} (prev {prev.get('sales', 0):,.0f}, delta {delta_sales}%)\n"
            f"Net P/L: {current['net_profit']:,.0f} (prev {prev.get('net_profit', 0):,.0f}, delta {delta_profit}%)\n"
            f"Margin: {r['net_margin_pct']}% · Salary: {r['salary_pct']}% · Rent: {r['rent_pct']}% · Food: {r['food_cost_pct']}%\n"
            f"Aggregator share: {r['aggregator_share_pct']}% · Commission burden: {r['commission_pct']}%\n"
        )
        system = (
            "You are a calm, experienced CFO summarising a multi-month financial view "
            "for the leadership team. Write ONE plain-prose paragraph of 50-90 words. "
            "Do not use markdown headings, bullets, or labels. Do not invent numbers."
        )
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"insights-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            system_message=system,
        ).with_model("openai", "gpt-5.2")
        from emergentintegrations.llm.chat import UserMessage as UM  # type: ignore
        resp = await chat.send_message(UM(text=ctx))
        text = (resp or "").strip()
        # strip stray markdown
        import re
        text = re.sub(r"^#{1,6}\s*.*?$", "", text, flags=re.M).strip()
        return text or fallback
    except Exception as exc:
        logger.warning(f"AI insights summary failed: {exc}")
        return fallback


def _fallback_executive(payload: Dict[str, Any]) -> str:
    cur = payload["current"]["total"]
    prev = (payload.get("previous") or {}).get("total") or {}
    r = payload["current"]["ratios"]
    if cur["sales"] <= 0:
        return "No sales activity recorded for the selected period across the chosen centers."
    bits = []
    delta = _delta_pct(cur["sales"], prev.get("sales", 0)) if prev else None
    if delta is not None:
        direction = "improved" if delta >= 0 else "declined"
        bits.append(f"Sales {direction} by {abs(delta):.1f}% vs the prior comparable period")
    delta_p = _delta_pct(cur["net_profit"], prev.get("net_profit", 0)) if prev else None
    if delta_p is not None:
        bits.append(f"net P/L moved {delta_p:+.1f}%")
    bits.append(f"net margin stands at {r['net_margin_pct']}%")
    if r["salary_pct"] > IDEAL["salary_pct"]:
        bits.append(f"salary ratio is elevated at {r['salary_pct']}%")
    if r["commission_pct"] > IDEAL["commission_burden_pct"]:
        bits.append(f"commission burden is heavy at {r['commission_pct']}%")
    return ". ".join(bits).capitalize() + "."


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/summary")
async def insights_summary(req: InsightsRequest):
    session = await check_access(req.token)
    centers = await _accessible_centers_for(session, req.centers)
    months, period_label = _resolve_months(req)

    current = await _aggregate_period(centers, months)

    previous = None
    if req.compare_previous:
        prev_months = _shift_period_backwards(months)
        previous = await _aggregate_period(centers, prev_months)

    # Trend strip: always show last 12 months ending at the LAST month of current period
    trend_months = _months_back(months[-1], 12)
    trend = []
    for m in trend_months:
        agg = await _aggregate_period(centers, [m])
        t = agg["total"]
        trend.append({
            "month": m, "label": _month_label(m),
            "sales": t["sales"], "expenses": t["expenses"],
            "commission": t["commission"], "gst": t["gst"],
            "net_profit": t["net_profit"],
            "dinein": t["dinein"], "aggregator": t["aggregator"],
        })

    # Working capital snapshot for the LAST month (only if single center)
    wc = None
    if len(centers) == 1:
        wc = await _wc_snapshot(centers[0], months[-1])

    payload = {
        "centers": centers,
        "months": months,
        "period_label": period_label,
        "current": current,
        "previous": previous,
        "trend": trend,
        "wc": wc,
        "ideal_ratios": IDEAL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    payload["ai_summary"] = await _ai_executive_summary(payload)
    return payload


@router.post("/drill-down")
async def drill_down(req: DrillRequest):
    session = await check_access(req.token)
    await _accessible_centers_for(session, [req.center])
    center_doc = await db.centers.find_one({"code": req.center}, {"_id": 0}) or {}
    country = get_country_from_center(center_doc)
    mm = await _month_metrics(req.center, req.month, country)

    if req.dimension == "expense_category":
        items = [
            {"name": k, "amount": round(v, 2)}
            for k, v in sorted(mm["expense_by_category"].items(), key=lambda kv: -kv[1])
        ]
        return {"dimension": "expense_category", "month": req.month, "items": items, "total": mm["expenses_total"]}

    if req.dimension == "sales_channel":
        s = mm["sales"]
        items = [
            {"name": "Dine-in", "amount": s["dinein"]},
            {"name": "Swiggy", "amount": s["swiggy"]},
            {"name": "Zomato", "amount": s["zomato"]},
            {"name": "DoorDash", "amount": s["doordash"]},
        ]
        return {"dimension": "sales_channel", "month": req.month, "items": items, "total": s["total"]}

    raise HTTPException(400, f"Unknown dimension {req.dimension}")


# ---------------------------------------------------------------------------
# Export (Excel / CSV)
# ---------------------------------------------------------------------------

def _build_excel(payload: Dict[str, Any]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook()

    title_font = Font(bold=True, size=14, color="5C0000")
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="8B0000")
    money_fmt = '#,##0.00'

    # Sheet 1: Summary
    ws = wb.active
    ws.title = "Summary"
    ws["A1"] = f"Financial Insights — {payload['period_label']}"
    ws["A1"].font = title_font
    ws.merge_cells("A1:D1")
    ws["A2"] = f"Centers: {', '.join(payload['centers'])}"
    ws["A2"].font = Font(italic=True, color="666666")
    ws.merge_cells("A2:D2")
    ws["A4"] = "AI Summary"
    ws["A4"].font = Font(bold=True)
    ws["A5"] = payload.get("ai_summary", "")
    ws["A5"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("A5:D5")
    ws.row_dimensions[5].height = 60

    cur = payload["current"]["total"]
    r = payload["current"]["ratios"]
    rows = [
        ["Metric", "Current"],
        ["Total Sales", cur["sales"]],
        ["Aggregator (Swiggy/Zomato/DoorDash)", cur["aggregator"]],
        ["Dine-in", cur["dinein"]],
        ["Total Expenses", cur["expenses"]],
        ["Less Adjustments (prepaid / advance carve)", cur.get("expense_adjustments", 0)],
        ["Adjusted Expenses", cur.get("adjusted_expenses", cur["expenses"])],
        ["Platform Commission", cur["commission"]],
        ["GST (inclusive carve)", cur["gst"]],
        ["Net Revenue (Sales − Comm − GST)", cur["net_revenue"]],
        ["Gross Profit (Sales − RM − Comm − GST)", cur["gross_profit"]],
        ["Net P/L (Net Revenue − Adjusted Expenses)", cur["net_profit"]],
    ]
    for i, row in enumerate(rows, start=7):
        ws.cell(row=i, column=1, value=row[0])
        ws.cell(row=i, column=2, value=row[1])
        if i == 7:
            for c in (1, 2):
                ws.cell(row=i, column=c).font = header_font
                ws.cell(row=i, column=c).fill = header_fill
        else:
            ws.cell(row=i, column=2).number_format = money_fmt

    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 20

    # Sheet 2: Ratios
    ws2 = wb.create_sheet("Ratios")
    ws2.append(["Ratio", "Value (%)", "Ideal (%)", "Status"])
    for c in range(1, 5):
        cell = ws2.cell(row=1, column=c)
        cell.font = header_font
        cell.fill = header_fill
    ideal = payload["ideal_ratios"]
    ratio_rows = [
        ("Food Cost", r["food_cost_pct"], ideal["food_cost_pct"]),
        ("Salary", r["salary_pct"], ideal["salary_pct"]),
        ("Rent", r["rent_pct"], ideal["rent_pct"]),
        ("Utility", r["utility_pct"], ideal["utility_pct"]),
        ("Commission Burden", r["commission_pct"], ideal["commission_burden_pct"]),
        ("Aggregator Share", r["aggregator_share_pct"], ideal["aggregator_share_pct"]),
        ("Net Margin", r["net_margin_pct"], 10.0),
        ("Operational Cost", r["operational_cost_pct"], 70.0),
    ]
    for name, value, ideal_v in ratio_rows:
        status = _ratio_status(value, ideal_v)
        ws2.append([name, value, ideal_v, status.upper()])
    ws2.column_dimensions["A"].width = 30
    ws2.column_dimensions["B"].width = 14
    ws2.column_dimensions["C"].width = 14
    ws2.column_dimensions["D"].width = 14

    # Sheet 3: Trend
    ws3 = wb.create_sheet("12-Month Trend")
    ws3.append(["Month", "Sales", "Expenses", "Commission", "GST", "Net P/L", "Dine-in", "Aggregator"])
    for c in range(1, 9):
        cell = ws3.cell(row=1, column=c)
        cell.font = header_font
        cell.fill = header_fill
    for t in payload["trend"]:
        ws3.append([
            t["label"], t["sales"], t["expenses"], t["commission"],
            t["gst"], t["net_profit"], t["dinein"], t["aggregator"],
        ])
    for col_letter in ("B", "C", "D", "E", "F", "G", "H"):
        for cell in ws3[col_letter]:
            cell.number_format = money_fmt

    # Sheet 4: Per-month breakdown of current period
    ws4 = wb.create_sheet("By Month")
    ws4.append(["Month", "Sales", "Expenses", "Commission", "GST", "Net Revenue", "Net P/L"])
    for c in range(1, 8):
        cell = ws4.cell(row=1, column=c)
        cell.font = header_font
        cell.fill = header_fill
    for m in payload["current"]["by_month"]:
        ws4.append([
            m["label"], m["sales"], m["expenses"], m["commission"],
            m["gst"], m["net_revenue"], m["net_profit"],
        ])

    # Sheet 5: Expense buckets
    ws5 = wb.create_sheet("Expense Categories")
    ws5.append(["Category", "Amount", "% of Sales"])
    for c in range(1, 4):
        cell = ws5.cell(row=1, column=c)
        cell.font = header_font
        cell.fill = header_fill
    sales_total = cur["sales"] or 1
    for cat, amt in sorted(payload["current"]["total"]["expense_by_category"].items(), key=lambda kv: -kv[1]):
        ws5.append([cat, amt, round((amt / sales_total) * 100.0, 2)])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _build_csv(payload: Dict[str, Any]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([f"Financial Insights — {payload['period_label']}"])
    w.writerow([f"Centers: {', '.join(payload['centers'])}"])
    w.writerow([])
    cur = payload["current"]["total"]
    w.writerow(["Metric", "Current"])
    w.writerow(["Total Sales", cur["sales"]])
    w.writerow(["Total Expenses", cur["expenses"]])
    w.writerow(["Less Adjustments", cur.get("expense_adjustments", 0)])
    w.writerow(["Adjusted Expenses", cur.get("adjusted_expenses", cur["expenses"])])
    w.writerow(["Commission", cur["commission"]])
    w.writerow(["GST", cur["gst"]])
    w.writerow(["Net Revenue", cur["net_revenue"]])
    w.writerow(["Gross Profit", cur["gross_profit"]])
    w.writerow(["Net P/L", cur["net_profit"]])
    w.writerow([])
    w.writerow(["12-Month Trend"])
    w.writerow(["Month", "Sales", "Expenses", "Commission", "GST", "Net P/L"])
    for t in payload["trend"]:
        w.writerow([t["label"], t["sales"], t["expenses"], t["commission"], t["gst"], t["net_profit"]])
    return buf.getvalue().encode("utf-8")


@router.post("/export")
async def insights_export(req: ExportRequest):
    payload = await insights_summary(req)  # reuse full computation
    fmt = (req.format or "excel").lower()
    if fmt == "excel":
        data = _build_excel(payload)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    elif fmt == "csv":
        data = _build_csv(payload)
        media = "text/csv"
        ext = "csv"
    else:
        raise HTTPException(400, f"Unsupported format {fmt}")
    fname = f"financial_insights_{'_'.join(req.centers)}_{req.period_type}.{ext}"
    return StreamingResponse(
        io.BytesIO(data),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
