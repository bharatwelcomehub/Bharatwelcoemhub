"""PDF builders for the "Coming Soon" reports that we're now shipping
(Feb-2026 user request):

  • Profit & Loss
  • MG Summary
  • Payout Summary
  • PhonePe Reconciliation
  • GST Paid
  • Missing Bills

Each builder accepts already-computed data dicts and returns PDF bytes ready
to stream. Style mirrors `utils/pdf_generator.py` for visual consistency.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .entity import entity_for_country

# Shared brand palette
BRAND_MAROON = colors.HexColor("#800020")
BRAND_NAVY = colors.HexColor("#1a365d")
LIGHT_GRAY = colors.HexColor("#f3f4f6")
DARK_GRAY = colors.HexColor("#374151")

_STYLES = getSampleStyleSheet()
_TITLE = ParagraphStyle(
    "ExtraTitle", parent=_STYLES["Heading1"],
    fontSize=16, alignment=TA_CENTER, spaceAfter=4,
    textColor=BRAND_MAROON,
)
_SUBTITLE = ParagraphStyle(
    "ExtraSubtitle", parent=_STYLES["Normal"],
    fontSize=9, alignment=TA_CENTER, textColor=colors.gray, spaceAfter=10,
)
_H2 = ParagraphStyle(
    "ExtraH2", parent=_STYLES["Heading2"],
    fontSize=12, spaceBefore=12, spaceAfter=6, textColor=BRAND_NAVY,
)
_BODY = ParagraphStyle(
    "ExtraBody", parent=_STYLES["Normal"],
    fontSize=9, textColor=DARK_GRAY, leading=12,
)
_FOOTNOTE = ParagraphStyle(
    "ExtraFoot", parent=_STYLES["Normal"],
    fontSize=7, textColor=colors.gray, alignment=TA_LEFT,
)

_TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 9),
    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("FONTSIZE", (0, 1), (-1, -1), 8),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
])


def _money(amt: Any, cur: str = "Rs.") -> str:
    try:
        return f"{cur} {float(amt or 0):,.2f}"
    except (TypeError, ValueError):
        return f"{cur} 0.00"


def _header(title: str, ctx: Dict[str, Any]) -> List[Any]:
    legal = entity_for_country(ctx.get("country"))
    period_label = ctx.get("period_label") or ctx.get("period", "")
    return [
        Paragraph(title, _TITLE),
        Paragraph(
            f"{legal} · {ctx.get('center', '—')} · {period_label} · "
            f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')}",
            _SUBTITLE,
        ),
        Spacer(1, 4),
    ]


def _build(buf_title: str, sections: List[Any], landscape_mode: bool = False) -> bytes:
    buf = io.BytesIO()
    page = landscape(A4) if landscape_mode else A4
    doc = SimpleDocTemplate(
        buf, pagesize=page,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
        title=buf_title,
    )
    doc.build(sections)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Profit & Loss
# ─────────────────────────────────────────────────────────────────────────────
def build_profit_loss_pdf(summary: Dict[str, Any]) -> bytes:
    """P&L statement derived from the canonical account summary."""
    ctx = {
        "center": summary.get("center", "—"),
        "country": summary.get("country", "India"),
        "period": summary.get("period", ""),
        "period_label": summary.get("period_label", ""),
    }
    currency = "AUD" if (ctx["country"] or "").lower() != "india" else "Rs."
    fin = summary.get("financial_summary", {}) or {}
    sales = summary.get("sales", {}) or {}
    commissions = summary.get("commissions", {}) or {}
    expenses_total = float(fin.get("total_expenses") or 0)
    adjusted_expenses = float(fin.get("adjusted_expenses", expenses_total) or 0)

    total_sales = float(fin.get("total_sales") or sales.get("total_sale") or 0)
    sales_gst = float(fin.get("sales_gst") or 0)
    total_comm = float(fin.get("total_commissions") or commissions.get("total") or 0)
    profit = float(fin.get("profitability") or 0)

    rows = [
        ["LINE ITEM", "AMOUNT"],
        ["REVENUE", ""],
        ["  Gross Sales", _money(total_sales, currency)],
        ["  Less: GST collected (pass-through)", f"({_money(sales_gst, currency)})"],
        ["  Net Sales (ex-GST)", _money(total_sales - sales_gst, currency)],
        ["", ""],
        ["DEDUCTIONS", ""],
        ["  Aggregator / Card Commissions", _money(total_comm, currency)],
        ["  Total Deductions", _money(total_comm, currency)],
        ["", ""],
        ["GROSS MARGIN", _money(total_sales - sales_gst - total_comm, currency)],
        ["", ""],
        ["OPERATING EXPENSES", ""],
        ["  Total Expenses (booked)", _money(expenses_total, currency)],
        ["  Adjustments (advance/prepaid moved out)", _money(expenses_total - adjusted_expenses, currency)],
        ["  Adjusted Operating Expenses", _money(adjusted_expenses, currency)],
        ["", ""],
        ["PROFIT / (LOSS)", _money(profit, currency)],
    ]
    tbl = Table(rows, colWidths=[110 * mm, 60 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTNAME", (0, 6), (-1, 6), "Helvetica-Bold"),
        ("FONTNAME", (0, 10), (-1, 10), "Helvetica-Bold"),
        ("FONTNAME", (0, 12), (-1, 12), "Helvetica-Bold"),
        ("FONTNAME", (0, 17), (-1, 17), "Helvetica-Bold"),
        ("BACKGROUND", (0, 10), (-1, 10), colors.HexColor("#dbeafe")),
        ("BACKGROUND", (0, 17), (-1, 17), colors.HexColor("#dcfce7") if profit >= 0 else colors.HexColor("#fee2e2")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    sections = _header("Profit &amp; Loss Statement", ctx) + [
        Paragraph(
            "P&amp;L is computed on a cash basis: GST is excluded from revenue as it is a "
            "government pass-through. Adjustments shift advance/prepaid items to the months they relate to.",
            _BODY,
        ),
        Spacer(1, 6),
        tbl,
        Spacer(1, 10),
        Paragraph(
            "Generated from the Single Financial Engine. Source-of-truth: backend/utils/financial_engine.py",
            _FOOTNOTE,
        ),
    ]
    return _build(f"P&L_{ctx['center']}_{ctx['period']}", sections)


# ─────────────────────────────────────────────────────────────────────────────
# 2. MG Summary
# ─────────────────────────────────────────────────────────────────────────────
def build_mg_summary_pdf(payout: Dict[str, Any], franchise: Dict[str, Any]) -> bytes:
    """Month-wise MG vs Revenue Share comparison — shows when MG kicked in."""
    ctx = {
        "center": payout.get("center", "—"),
        "country": payout.get("country", "India"),
        "period": payout.get("period_range", payout.get("month", "")),
        "period_label": payout.get("period_label", ""),
    }
    currency = "AUD" if (ctx["country"] or "").lower() != "india" else "Rs."
    monthly = payout.get("monthly_data") or []
    mg_amount_config = float(franchise.get("monthly_mg") or franchise.get("mg") or 0)
    mg_app = bool(franchise.get("mg_calculation_applicable", True))

    if not mg_app or mg_amount_config == 0:
        sections = _header("MG Summary", ctx) + [
            Paragraph(
                "<b>Maintenance Guarantee not applicable</b> for this franchise. "
                "This center operates on a pure Revenue/Profit Share model — there "
                "is no monthly minimum guarantee. See Payout Summary for actual payouts.",
                _BODY,
            ),
        ]
        return _build(f"MGSummary_{ctx['center']}_{ctx['period']}", sections)

    rows: List[List[Any]] = [
        ["Month", "Sales", "Rev Share Payout", "Monthly MG",
         "Payable", "Type", "MG Top-up"],
    ]
    total_topup = 0.0
    for m in monthly:
        rs_payout = float(m.get("revenue_share") or 0)
        mg_for_month = mg_amount_config if m.get("mg_applicable") is not False else 0
        payable = float(m.get("payable_amount") or 0)
        ptype = m.get("payable_type") or ("mg" if mg_for_month > rs_payout else "rs")
        topup = max(0.0, mg_for_month - rs_payout) if ptype == "mg" else 0.0
        total_topup += topup
        rows.append([
            datetime.strptime(m["month"] + "-01", "%Y-%m-%d").strftime("%b %Y"),
            _money(m.get("total_sales"), currency),
            _money(rs_payout, currency),
            _money(mg_for_month, currency) if mg_for_month else "—",
            _money(payable, currency),
            ptype.upper(),
            _money(topup, currency) if topup > 0 else "—",
        ])
    rows.append([
        "TOTAL",
        _money(sum(float(m.get("total_sales") or 0) for m in monthly), currency),
        _money(sum(float(m.get("revenue_share") or 0) for m in monthly), currency),
        "",
        _money(sum(float(m.get("payable_amount") or 0) for m in monthly), currency),
        "",
        _money(total_topup, currency),
    ])
    tbl = Table(rows, colWidths=[22 * mm, 28 * mm, 32 * mm, 26 * mm, 28 * mm, 14 * mm, 26 * mm])
    tbl.setStyle(_TABLE_STYLE)
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fef3c7")),
    ]))
    sections = _header("MG Summary — Month-wise", ctx) + [
        Paragraph(
            f"<b>Monthly MG:</b> {_money(mg_amount_config, currency)} · "
            f"<b>MG-eligible months:</b> Type column = MG.",
            _BODY,
        ),
        Spacer(1, 6),
        tbl,
        Spacer(1, 8),
        Paragraph(
            f"<b>Total MG Top-up:</b> {_money(total_topup, currency)} "
            "(amount paid above what Revenue Share alone would have yielded).",
            _BODY,
        ),
    ]
    return _build(f"MGSummary_{ctx['center']}_{ctx['period']}", sections, landscape_mode=True)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Payout Summary
# ─────────────────────────────────────────────────────────────────────────────
def build_payout_summary_pdf(payout: Dict[str, Any]) -> bytes:
    """Owner Payout summary — Payable, Paid, Pending across months."""
    ctx = {
        "center": payout.get("center", "—"),
        "country": payout.get("country", "India"),
        "period": payout.get("period_range", payout.get("month", "")),
        "period_label": payout.get("period_label", ""),
    }
    currency = "AUD" if (ctx["country"] or "").lower() != "india" else "Rs."
    monthly = payout.get("monthly_data") or []
    totals = payout.get("totals") or {}

    rows: List[List[Any]] = [
        ["Month", "Payable", "Paid", "Pending", "Type", "Status"],
    ]
    for m in monthly:
        rows.append([
            datetime.strptime(m["month"] + "-01", "%Y-%m-%d").strftime("%b %Y"),
            _money(m.get("payable_amount"), currency),
            _money(m.get("paid"), currency),
            _money(m.get("pending"), currency),
            (m.get("payable_type") or "rs").upper(),
            (m.get("status") or "unpaid").title(),
        ])
    rows.append([
        "TOTAL",
        _money(totals.get("payable"), currency),
        _money(totals.get("paid"), currency),
        _money(totals.get("pending"), currency),
        "",
        "",
    ])
    tbl = Table(rows, colWidths=[28 * mm, 32 * mm, 32 * mm, 32 * mm, 18 * mm, 24 * mm])
    tbl.setStyle(_TABLE_STYLE)
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dcfce7")),
    ]))
    sections = _header("Payout Summary", ctx) + [tbl]
    return _build(f"Payout_{ctx['center']}_{ctx['period']}", sections)


# ─────────────────────────────────────────────────────────────────────────────
# 4. PhonePe Reconciliation
# ─────────────────────────────────────────────────────────────────────────────
def build_phonepe_recon_pdf(ctx: Dict[str, Any], txns: List[Dict[str, Any]]) -> bytes:
    """PhonePe / UPI reconciliation — Daily Sale recorded vs PhonePe receipts."""
    currency = "AUD" if (ctx.get("country") or "India").lower() != "india" else "Rs."

    rows: List[List[Any]] = [
        ["Date", "Description", "Total Online Sale", "PhonePe Portion", "Variance"],
    ]
    total_online = 0.0
    total_phonepe = 0.0
    for t in txns:
        online = float(t.get("total_online_sale") or 0)
        phonepe = float(t.get("phonepe") or t.get("upi") or t.get("bharat_pay") or 0)
        variance = online - phonepe
        total_online += online
        total_phonepe += phonepe
        rows.append([
            t.get("date", ""),
            (t.get("description") or "Daily online receipts")[:40],
            _money(online, currency),
            _money(phonepe, currency),
            _money(variance, currency),
        ])
    rows.append([
        "TOTAL", "",
        _money(total_online, currency),
        _money(total_phonepe, currency),
        _money(total_online - total_phonepe, currency),
    ])
    tbl = Table(rows, colWidths=[22 * mm, 60 * mm, 32 * mm, 32 * mm, 28 * mm])
    tbl.setStyle(_TABLE_STYLE)
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fef3c7")),
    ]))
    sections = _header("PhonePe / UPI Reconciliation", ctx) + [
        Paragraph(
            "Daily online sale (UPI / PhonePe / BharatPe) recorded in the system "
            "compared with PhonePe gateway-side receipts. Variance &gt; 0 indicates "
            "a recording mismatch that needs investigation.",
            _BODY,
        ),
        Spacer(1, 6),
        tbl,
    ]
    return _build(f"PhonePeRecon_{ctx['center']}_{ctx['period']}", sections, landscape_mode=True)


# ─────────────────────────────────────────────────────────────────────────────
# 5. GST Paid
# ─────────────────────────────────────────────────────────────────────────────
def build_gst_paid_pdf(ctx: Dict[str, Any], payments: List[Dict[str, Any]]) -> bytes:
    """GST Paid statement — month-wise GST liability vs actual GST paid to government."""
    currency = "AUD" if (ctx.get("country") or "India").lower() != "india" else "Rs."

    rows: List[List[Any]] = [
        ["Month / Date", "Description", "GST Collected", "GST Paid", "Net Liability"],
    ]
    total_collected = 0.0
    total_paid = 0.0
    for p in payments:
        collected = float(p.get("gst_collected") or 0)
        paid = float(p.get("gst_paid") or 0)
        net = collected - paid
        total_collected += collected
        total_paid += paid
        rows.append([
            p.get("month") or p.get("date", ""),
            (p.get("description") or "GST PAYMENT")[:40],
            _money(collected, currency),
            _money(paid, currency),
            _money(net, currency),
        ])
    rows.append([
        "TOTAL", "",
        _money(total_collected, currency),
        _money(total_paid, currency),
        _money(total_collected - total_paid, currency),
    ])
    tbl = Table(rows, colWidths=[28 * mm, 60 * mm, 32 * mm, 32 * mm, 28 * mm])
    tbl.setStyle(_TABLE_STYLE)
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fee2e2")),
    ]))
    sections = _header("GST Paid Statement", ctx) + [
        Paragraph(
            "GST collected from sales is a pass-through liability paid to the "
            "government typically the following month via an expense booked as "
            "<i>GST PAYMENT</i>. Net Liability &gt; 0 means GST still owed; &lt; 0 means "
            "overpayment / credit carried forward.",
            _BODY,
        ),
        Spacer(1, 6),
        tbl,
    ]
    return _build(f"GSTPaid_{ctx['center']}_{ctx['period']}", sections, landscape_mode=True)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Missing Bills
# ─────────────────────────────────────────────────────────────────────────────
def build_missing_bills_pdf(ctx: Dict[str, Any], expenses_without_bills: List[Dict[str, Any]]) -> bytes:
    """Expenses booked but missing attachments — compliance audit list."""
    currency = "AUD" if (ctx.get("country") or "India").lower() != "india" else "Rs."

    if not expenses_without_bills:
        sections = _header("Missing Bills — Compliance Audit", ctx) + [
            Paragraph(
                "<b>All expenses have bill attachments uploaded. </b>"
                "No missing bills for this period.",
                _BODY,
            ),
        ]
        return _build(f"MissingBills_{ctx['center']}_{ctx['period']}", sections)

    rows: List[List[Any]] = [
        ["Date", "Expense Type", "Description", "Payment Mode", "Amount"],
    ]
    total = 0.0
    for e in expenses_without_bills:
        amt = float(e.get("amount") or 0)
        total += amt
        rows.append([
            e.get("date", ""),
            (e.get("expense_type") or "—")[:25],
            (e.get("description") or "—")[:50],
            (e.get("payment_mode") or "—")[:12],
            _money(amt, currency),
        ])
    rows.append(["", "", "", "TOTAL", _money(total, currency)])

    tbl = Table(rows, colWidths=[22 * mm, 40 * mm, 80 * mm, 26 * mm, 32 * mm])
    tbl.setStyle(_TABLE_STYLE)
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fee2e2")),
    ]))
    sections = _header("Missing Bills — Compliance Audit", ctx) + [
        Paragraph(
            f"<b>{len(expenses_without_bills)} expense entries</b> totalling "
            f"<b>{_money(total, currency)}</b> do not have bill / invoice "
            "attachments uploaded. Required by Indian Income Tax Rule 6F / "
            "AU ATO record-keeping. Please upload the missing bills via "
            "<i>Center Accounts → Expense Attachments</i> tab.",
            _BODY,
        ),
        Spacer(1, 6),
        tbl,
    ]
    return _build(f"MissingBills_{ctx['center']}_{ctx['period']}", sections, landscape_mode=True)


__all__ = [
    "build_profit_loss_pdf",
    "build_mg_summary_pdf",
    "build_payout_summary_pdf",
    "build_phonepe_recon_pdf",
    "build_gst_paid_pdf",
    "build_missing_bills_pdf",
]
