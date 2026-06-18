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

    # — Profit Share MFPL — user-specified formula
    pnl = round(total_sale - total_expenses - total_commission - gst_on_sales, 2)
    profit_share_mfpl = round(total_sale - total_expenses - amount_paid, 2)

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
        "profit_share_mfpl": profit_share_mfpl,
        # diagnostics (not shown in grid but useful in PDF footer)
        "_meta": {
            "commission": round(total_commission, 2),
            "gst_on_sales": round(gst_on_sales, 2),
            "include_gst_in_revenue": include_gst_in_revenue,
            "payments_count": len(payments),
        },
    }


def _totals(rows: List[dict]) -> dict:
    keys = ["sale", "expenses", "pnl", "revenue_share_base", "revenue_share_amount",
            "revenue_share_plus_gst", "mg_amount", "mg_plus_gst", "amount_paid",
            "profit_share_mfpl"]
    return {k: round(sum(float(r.get(k, 0) or 0) for r in rows), 2) for k in keys}


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
    await _auth(req.get("token"))
    center = (req.get("center") or "").upper()
    if not center:
        raise HTTPException(400, "center is required")

    # Filters
    fy = req.get("financial_year")          # e.g. "2024-25"
    from_month = req.get("from_month")
    to_month = req.get("to_month")
    rs_pct = float(req.get("revenue_share_pct") or 0)
    gst_on = bool(req.get("gst_applicable", True))

    franchise = await _get_franchise(center)
    if not rs_pct:
        rs_pct = float(franchise.get("franchise_owner_share_percentage")
                       or franchise.get("revenue_share_percentage") or 15)

    if fy and not (from_month and to_month):
        from_month, to_month = _fy_range(fy)
    if not from_month:
        from_month = "2024-04"
    if not to_month:
        to_month = datetime.now().strftime("%Y-%m")

    months = _months_between(from_month, to_month)
    rows = [await _month_row(center, m, franchise, rs_pct, gst_on) for m in months]
    return {
        "success": True,
        "center": center,
        "center_name": franchise.get("franchise_name") or franchise.get("name") or center,
        "filters": {
            "financial_year": fy,
            "from_month": from_month,
            "to_month": to_month,
            "revenue_share_pct": rs_pct,
            "gst_applicable": gst_on,
        },
        "rows": rows,
        "totals": _totals(rows),
        "gst_rate": GST_RATE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Revenue Share Projection
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/revenue-share-projection")
async def revenue_share_projection(req: dict = Body(...)):
    await _auth(req.get("token"))
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
    rs_pct = float(req.get("revenue_share_pct") or 0)
    mg_amount_override = req.get("mg_amount")          # optional — else last actual MG
    start_month = req.get("start_month")               # YYYY-MM; defaults to next month after last actual

    franchise = await _get_franchise(center)
    if not rs_pct:
        rs_pct = float(franchise.get("franchise_owner_share_percentage")
                       or franchise.get("revenue_share_percentage") or 15)

    # — Seed baseline = average of last 3 months that had SALES data —
    # We scan up to 18 months back so we don't get stuck if the current FY
    # is empty (e.g. PB-HSR data ends 2026-03, current month is 2026-06).
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
            row = await _month_row(center, cur.strftime("%Y-%m"), franchise, rs_pct, True)
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
        base_mg = sum(s["mg_amount"] for s in seeds) / len(seeds)
        last_actual_month = max(s["month"] for s in seeds)
    else:
        base_sale = 0.0
        base_expense = 0.0
        base_mg = 0.0
        last_actual_month = actual_to

    if mg_amount_override is not None:
        base_mg = float(mg_amount_override)

    if not start_month:
        # next month after last_actual_month
        y, m = last_actual_month.split("-")
        d = datetime(int(y), int(m), 1)
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
        # Use a simplified P/L = Sale − Expense for projection (no commission/GST modelling).
        pnl = round(projected_sale - projected_expense, 2)
        # Revenue share base for projection mirrors P/L (assumption: GST + commissions
        # already considered in expense growth band). Founder spec says "use the
        # same columns" so we expose all 11.
        rs_base = pnl
        rs_amount = round(max(0, rs_base) * (rs_pct / 100.0), 2)
        rs_plus_gst = round(rs_amount * (1 + gst_pct / 100.0), 2)
        mg_plus_gst = round(base_mg * (1 + gst_pct / 100.0), 2)
        amount_paid = round(max(base_mg, rs_amount), 2)   # projected payout = max(MG, RS)
        profit_mfpl = round(projected_sale - projected_expense - amount_paid, 2)
        rows.append({
            "month": cur.strftime("%Y-%m"),
            "sale": projected_sale,
            "expenses": projected_expense,
            "pnl": pnl,
            "revenue_share_base": rs_base,
            "revenue_share_pct": rs_pct,
            "revenue_share_amount": rs_amount,
            "revenue_share_plus_gst": rs_plus_gst,
            "mg_amount": round(base_mg, 2),
            "mg_plus_gst": mg_plus_gst,
            "amount_paid": amount_paid,
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
        "filters": {
            "years": years,
            "start_month": start_month,
            "sales_growth_pct": sales_growth * 100,
            "expense_growth_pct": expense_growth * 100,
            "gst_pct": gst_pct,
            "revenue_share_pct": rs_pct,
            "mg_amount": round(base_mg, 2),
        },
        "baseline_seed_months": [s["month"] for s in seeds],
        "rows": rows,
        "totals": _totals(rows),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Exports — shared PDF & Excel builders
# ─────────────────────────────────────────────────────────────────────────────
COLUMN_DEFS = [
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
    ("profit_share_mfpl", "Profit Share MFPL"),
]


def _fmt_money(v) -> str:
    try:
        return f"{float(v or 0):,.2f}"
    except Exception:
        return str(v)


def _build_excel(title: str, data: dict, account_manager: str = "—") -> bytes:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = (title[:28] or "Report")

    # Title block
    ws.append([title])
    ws.append([f"Center: {data.get('center_name', '—')} ({data.get('center', '')})"])
    f = data.get("filters", {}) or {}
    period = f.get("financial_year") or (f"{f.get('from_month', '—')} → {f.get('to_month', '—')}")
    if f.get("start_month"):
        period = f"{f.get('years')} year(s) from {f.get('start_month')}"
    ws.append([f"Period: {period}"])
    ws.append([f"Revenue Share %: {f.get('revenue_share_pct', '—')}  ·  GST: "
               + ("Yes (18%)" if f.get('gst_applicable', True) else "No")])
    ws.append([f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}"])
    ws.append([])

    header_row_idx = ws.max_row + 1
    headers = [c[1] for c in COLUMN_DEFS]
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
    for key, _ in COLUMN_DEFS[1:]:
        total_row.append(totals.get(key, 0))
    ws.append(total_row)
    total_idx = ws.max_row
    total_fill = PatternFill("solid", fgColor="ffe1a4")
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=total_idx, column=c)
        cell.font = Font(bold=True)
        cell.fill = total_fill
        if c > 1:
            cell.number_format = "#,##0.00"

    # Data rows
    for r in data.get("rows", []):
        row_values = [r.get("month", "")]
        for key, _ in COLUMN_DEFS[1:]:
            row_values.append(r.get(key, 0))
        ws.append(row_values)
        idx = ws.max_row
        for c in range(2, len(headers) + 1):
            ws.cell(row=idx, column=c).number_format = "#,##0.00"

    # Column widths
    widths = [12, 14, 14, 14, 18, 14, 18, 14, 14, 14, 18]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

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

    # Logo (optional — look up known logo paths used elsewhere)
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
    f = data.get("filters", {}) or {}
    period = f.get("financial_year") or f"{f.get('from_month', '—')} → {f.get('to_month', '—')}"
    if f.get("start_month"):
        period = f"{f.get('years')} year(s) starting {f.get('start_month')}"
    story.append(Paragraph(f"<b>Period:</b> {period}", sub))
    story.append(Paragraph(
        f"<b>Revenue Share %:</b> {f.get('revenue_share_pct', '—')}  &nbsp; "
        f"<b>GST:</b> {'Yes (18%)' if f.get('gst_applicable', True) else 'No'}", sub))
    story.append(Spacer(1, 6))

    # Headers
    headers = [c[1] for c in COLUMN_DEFS]
    totals = data.get("totals", {})
    total_row = ["TOTAL"] + [_fmt_money(totals.get(k, 0)) for k, _ in COLUMN_DEFS[1:]]
    table_data = [headers, total_row]
    for r in data.get("rows", []):
        row = [r.get("month", "")] + [_fmt_money(r.get(k, 0)) for k, _ in COLUMN_DEFS[1:]]
        table_data.append(row)

    col_widths = [20, 24, 24, 24, 30, 24, 30, 24, 24, 24, 30]
    col_widths = [w * mm for w in col_widths]
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
