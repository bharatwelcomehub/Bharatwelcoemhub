"""Centralised PDF / Excel generation for the Purnabramha IntraPB app.

Each function in this module accepts already-computed data (plain dicts / lists)
and returns `bytes` ready to stream back to the client. No DB calls, no request
objects — pure rendering so each report can be unit-tested and reused from any
route (web, scheduled email, audit export, etc.).

Shared brand palette lives at module top so all exports stay visually
consistent.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import io

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .entity import entity_for_country, entity_share_label

# -----------------------------------------------------------------------------
# Brand palette — single source of truth for all branded PDFs
# -----------------------------------------------------------------------------
BRAND_MAROON = colors.HexColor("#800020")
BRAND_MAROON_DEEP = colors.HexColor("#8B0000")
BRAND_GOLD = colors.HexColor("#C9A227")
BRAND_NAVY = colors.HexColor("#1a365d")
DARK_GRAY = colors.HexColor("#374151")
LIGHT_GRAY = colors.HexColor("#f3f4f6")

AUSTRALIA_GST_INCLUSIVE = 0.10  # 10% GST already included in AU sale value


# =============================================================================
# Working Capital Statement — PDF
# =============================================================================
def build_wc_table_pdf(
    center: str,
    center_info: Dict[str, Any],
    franchise: Optional[Dict[str, Any]],
    wc_data: Dict[str, Any],
    manager_name: str,
) -> bytes:
    """Landscape PDF of the month-by-month Working Capital breakdown."""
    rows = wc_data.get("rows", [])
    initial_wc = wc_data.get("initial_wc", 0)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        topMargin=15 * mm, bottomMargin=10 * mm,
        leftMargin=10 * mm, rightMargin=10 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Brand", fontSize=20, textColor=BRAND_MAROON_DEEP,
                              fontName="Helvetica-Bold", spaceAfter=2 * mm))
    styles.add(ParagraphStyle(name="Sub", fontSize=10, textColor=colors.gray, spaceAfter=4 * mm))
    styles.add(ParagraphStyle(name="Section", fontSize=12, textColor=BRAND_MAROON_DEEP,
                              fontName="Helvetica-Bold", spaceBefore=4 * mm, spaceAfter=2 * mm))

    story = [
        Paragraph("Purnabramha", styles["Brand"]),
        Paragraph(
            f"Working Capital Statement — {center} ({center_info.get('name', '')})",
            styles["Sub"],
        ),
    ]

    if franchise:
        info_data = [
            ["Franchise Owner", franchise.get("owner_name", "N/A"),
             "Center", f"{center} - {center_info.get('name', '')}"],
            ["City / State", f"{franchise.get('city', '')} / {franchise.get('state', '')}",
             "Base Working Capital", f"Rs. {initial_wc:,.0f}"],
            ["Report Date", datetime.now().strftime("%d %b %Y"),
             "Current WC", f"Rs. {wc_data.get('current_wc', 0):,.0f}"],
        ]
        info_table = Table(info_data, colWidths=[100, 180, 120, 180])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Month-by-Month Working Capital", styles["Section"]))

    headers = ["Month", "Sale", "Expenses", "GST", "Commission", "P/L",
               "Working Capital", "Bal. WC", "Diff of WC", "WC Adj", "Rev Share"]
    table_data = [headers]
    for r in rows:
        month_label = datetime.strptime(r["month"] + "-01", "%Y-%m-%d").strftime("%b %Y")
        table_data.append([
            month_label,
            f"{r['sale']:,.0f}",
            f"{r['expenses']:,.0f}",
            f"{r.get('gst', 0):,.0f}",
            f"{r['commission']:,.0f}",
            f"{r['pnl']:,.0f}",
            f"{r['opening_wc']:,.0f}",
            f"{r['balance_wc']:,.0f}",
            f"{r.get('diff_wc', r['balance_wc']):,.0f}",
            f"{r.get('wc_adjustment', 0):,.0f}" if r.get("wc_adjustment", 0) != 0 else "-",
            r.get("rev_share_status", "active").title(),
        ])

    col_widths = [50, 65, 65, 55, 60, 65, 70, 70, 70, 50, 50]
    wc_table = Table(table_data, colWidths=col_widths)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_MAROON_DEEP),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN", (1, 0), (-2, -1), "RIGHT"),
        ("ALIGN", (-1, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
    ]
    for i, r in enumerate(rows, 1):
        if r["pnl"] < 0:
            style_cmds.append(("TEXTCOLOR", (5, i), (5, i), colors.red))
        else:
            style_cmds.append(("TEXTCOLOR", (5, i), (5, i), colors.HexColor("#15803d")))
    wc_table.setStyle(TableStyle(style_cmds))
    story.append(wc_table)

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %b %Y %H:%M')} by {manager_name}",
        ParagraphStyle(name="Footer", fontSize=7, textColor=colors.gray),
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# =============================================================================
# Working Capital Statement — Excel
# =============================================================================
def build_wc_table_excel(
    center: str,
    franchise: Optional[Dict[str, Any]],
    wc_data: Dict[str, Any],
) -> bytes:
    """xlsx of the month-by-month Working Capital breakdown (openpyxl)."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    rows = wc_data.get("rows", [])
    initial_wc = wc_data.get("initial_wc", 0)

    wb = Workbook()
    ws = wb.active
    ws.title = "WC Statement"

    ws.merge_cells("A1:J1")
    ws["A1"] = "Purnabramha — Working Capital Statement"
    ws["A1"].font = Font(size=16, bold=True, color="8B0000")

    ws["A2"] = f"Center: {center}"
    ws["A2"].font = Font(size=10, bold=True)
    ws["C2"] = f"Owner: {franchise.get('owner_name', 'N/A') if franchise else 'N/A'}"
    ws["F2"] = f"Base WC: {initial_wc:,.0f}"
    ws["I2"] = f"Date: {datetime.now().strftime('%d %b %Y')}"

    headers = ["Month", "Sale", "Expenses", "GST", "Commission", "P/L",
               "Working Capital", "Bal. WC", "Diff of WC", "WC Adj", "Rev Share"]
    header_fill = PatternFill("solid", fgColor="8B0000")
    thin_border = Border(left=Side(style="thin"), right=Side(style="thin"),
                         top=Side(style="thin"), bottom=Side(style="thin"))

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF", size=9)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin_border

    for row_idx, r in enumerate(rows, 5):
        month_label = datetime.strptime(r["month"] + "-01", "%Y-%m-%d").strftime("%b %Y")
        values = [
            month_label, r["sale"], r["expenses"], r.get("gst", 0), r["commission"], r["pnl"],
            r["opening_wc"], r["balance_wc"], r.get("diff_wc", r["balance_wc"]),
            r.get("wc_adjustment", 0), r.get("rev_share_status", "active").title(),
        ]
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.border = thin_border
            cell.font = Font(size=9)
            if 2 <= col <= 10:
                cell.number_format = "#,##0"
                cell.alignment = Alignment(horizontal="right")
            if col == 6 and isinstance(val, (int, float)) and val < 0:
                cell.font = Font(size=9, color="FF0000")
            elif col == 6 and isinstance(val, (int, float)):
                cell.font = Font(size=9, color="15803D")

    for col_idx in range(1, len(headers) + 1):
        ws.column_dimensions[chr(64 + col_idx)].width = 14
    ws.column_dimensions["A"].width = 10

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


# =============================================================================
# PIB (Profit & Income Balance) Report — PDF
# =============================================================================
def _pib_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("PIBTitle", fontSize=18, alignment=TA_CENTER,
                              fontName="Helvetica-Bold", textColor=BRAND_MAROON, spaceAfter=10))
    styles.add(ParagraphStyle("PIBSubtitle", fontSize=12, alignment=TA_CENTER,
                              fontName="Helvetica", textColor=DARK_GRAY, spaceAfter=20))
    styles.add(ParagraphStyle("PIBSection", fontSize=12, fontName="Helvetica-Bold",
                              textColor=BRAND_NAVY, spaceBefore=15, spaceAfter=8))
    styles.add(ParagraphStyle("PIBBody", fontSize=10, fontName="Helvetica",
                              textColor=DARK_GRAY, spaceAfter=4, leading=14))
    return styles



def _append_payout_status_banner(story, status: Optional[Dict[str, Any]]) -> None:
    """Append the Payout Release Status banner to a PDF story.

    Renders a single boxed paragraph at the top of the report. Calculations
    elsewhere in the report are UNCHANGED — this only conveys whether the
    calculated payout is approved for release.

    Color mapping:
        green  → Eligible For Release
        amber  → Management Review Required
        red    → Currently Blocked
    Falls through quietly if status is None.
    """
    if not status:
        return
    color_map = {
        "green": (colors.HexColor("#16a34a"), colors.HexColor("#dcfce7"), colors.HexColor("#14532d"), "[OK]"),
        "amber": (colors.HexColor("#d97706"), colors.HexColor("#fef3c7"), colors.HexColor("#78350f"), "[REVIEW]"),
        "red":   (colors.HexColor("#dc2626"), colors.HexColor("#fee2e2"), colors.HexColor("#7f1d1d"), "[BLOCKED]"),
    }
    border, bg, fg, icon = color_map.get(status.get("color", "green"), color_map["green"])
    label = status.get("label", "Eligible For Release")
    narrative = status.get("narrative", "")
    reason = status.get("reason", "")
    banner_style = ParagraphStyle(
        "PayoutBanner", parent=getSampleStyleSheet()["Normal"],
        fontSize=10, leading=13, textColor=fg, fontName="Helvetica",
        spaceBefore=0, spaceAfter=0,
    )
    title = (
        f"<font name='Helvetica-Bold' size='12'>"
        f"{icon} Payout Status: {label}</font>"
        f"{'<br/><i>(' + reason + ')</i>' if reason else ''}"
    )
    body = f"<br/>{narrative}" if narrative else ""
    banner_para = Paragraph(title + body, banner_style)
    banner_table = Table([[banner_para]], colWidths=[460])
    banner_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 1.8, border),
        ("LINEBEFORE", (0, 0), (0, -1), 5, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 14))




def build_pib_pdf(summary: Dict[str, Any]) -> bytes:
    """Full PIB PDF — 9 sections. Expects the summary dict produced by
    `get_center_account_summary`."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50,
                            topMargin=60, bottomMargin=50)
    styles = _pib_styles()
    story: List[Any] = []

    # --- Title --------------------------------------------------------------
    story.append(Paragraph("PURNABRAMHA", styles["PIBTitle"]))
    story.append(Paragraph("Profit & Income Balance Report", styles["PIBSubtitle"]))
    story.append(Spacer(1, 10))

    info_data = [
        ["Center:", summary["center_name"], "Period:", summary["period"]],
        ["Country:", summary["country"], "Report Date:", datetime.now().strftime("%d-%b-%Y")],
        ["Franchise:", summary["franchise"]["name"] or "N/A",
         "Legal Entity:", summary["franchise"]["legal_entity"] or "N/A"],
    ]
    info_table = Table(info_data, colWidths=[80, 150, 80, 150])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_NAVY),
        ("TEXTCOLOR", (2, 0), (2, -1), BRAND_NAVY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 12))

    # ── 0. Payout Release Status Banner ────────────────────────────────
    # Per Feb-2026 owner directive — informational banner, does NOT change
    # any calculations. Auto-derived from WC Protection Mode + manual override.
    _append_payout_status_banner(story, summary.get("payout_release_status"))

    # --- 1. Sales Summary ---------------------------------------------------
    story.append(Paragraph("1. SALES SUMMARY", styles["PIBSection"]))
    sales = summary["sales"]
    currency = "AUD" if summary["country"] == "Australia" else "Rs."
    sales_data = [
        ["Description", "Amount", "% of Total"],
        ["Total Sales", f"{currency} {sales['total_sale']:,.2f}", "100%"],
        ["Direct Sales", f"{currency} {sales['direct_sale']:,.2f}",
         f"{sales['direct_sale']/max(sales['total_sale'],1)*100:.1f}%"],
        ["Aggregator Sales", f"{currency} {sales['aggregator_sale']:,.2f}",
         f"{sales['aggregator_sale']/max(sales['total_sale'],1)*100:.1f}%"],
        ["  - Swiggy", f"{currency} {sales['swiggy']:,.2f}", ""],
        ["  - Zomato", f"{currency} {sales['zomato']:,.2f}", ""],
        ["  - DoorDash", f"{currency} {sales['doordash']:,.2f}", ""],
        ["Card Sales", f"{currency} {sales['card_sale']:,.2f}",
         f"{sales['card_sale']/max(sales['total_sale'],1)*100:.1f}%"],
        ["PhonePe / UPI", f"{currency} {sales.get('bharat_pay', 0):,.2f}",
         f"{sales.get('bharat_pay', 0)/max(sales['total_sale'],1)*100:.1f}%"],
        ["Online Other", f"{currency} {sales.get('online_other', 0):,.2f}",
         f"{sales.get('online_other', 0)/max(sales['total_sale'],1)*100:.1f}%"],
        ["Cash Sales", f"{currency} {sales['total_cash_sale']:,.2f}",
         f"{sales['total_cash_sale']/max(sales['total_sale'],1)*100:.1f}%"],
    ]
    sales_table = Table(sales_data, colWidths=[200, 150, 100])
    sales_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), LIGHT_GRAY),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(sales_table)
    story.append(Spacer(1, 15))

    # --- 2. Expense Summary -------------------------------------------------
    story.append(Paragraph("2. EXPENSE SUMMARY", styles["PIBSection"]))
    expenses = summary["expenses"]
    expense_rows = [["Category", "Amount"]]
    for cat, amt in expenses["by_category"].items():
        expense_rows.append([cat, f"{currency} {amt:,.2f}"])
    expense_rows.append(["TOTAL EXPENSES", f"{currency} {expenses['total']:,.2f}"])
    expense_table = Table(expense_rows, colWidths=[280, 170])
    expense_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GRAY),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(expense_table)
    story.append(Spacer(1, 15))

    # --- 3. Commission Summary ---------------------------------------------
    story.append(Paragraph("3. COMMISSION SUMMARY", styles["PIBSection"]))
    commissions = summary["commissions"]
    commission_data = [["Platform", "Gross Amount", "Total Deductions", "Net Payout"]]
    for platform, data in commissions["by_platform"].items():
        ded = data.get("deduction", data.get("commission", 0))
        if data["gross"] > 0 or ded > 0:
            commission_data.append([
                platform.title().replace("_", " "),
                f"{currency} {data['gross']:,.2f}",
                f"{currency} {ded:,.2f}",
                f"{currency} {data['net']:,.2f}",
            ])
    commission_data.append(["TOTAL", "", f"{currency} {commissions['total']:,.2f}", ""])
    commission_table = Table(commission_data, colWidths=[120, 110, 110, 110])
    commission_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GRAY),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(commission_table)
    story.append(Spacer(1, 15))

    # --- 4. Financial Summary ----------------------------------------------
    story.append(Paragraph("4. FINANCIAL SUMMARY", styles["PIBSection"]))
    fin = summary["financial_summary"]
    gst_on_sales = fin.get("sales_gst", 0)
    is_australia = summary.get("country") == "Australia"
    fin_data = [
        ["Description", "Amount"],
        ["Total Sales", f"{currency} {fin['total_sales']:,.2f}"],
        ["Less: Total Commissions", f"({currency} {fin['total_commissions']:,.2f})"],
    ]
    # Australia: also show 10% commission GST as a separate deduction line
    if is_australia and float(fin.get("commission_gst", 0) or 0) > 0:
        fin_data.append([
            "Less: Commission GST (10%)",
            f"({currency} {fin['commission_gst']:,.2f})",
        ])
    # GST on Sales — Per Feb-2026 directive, GST is INFORMATIONAL only in
    # management reports and does NOT reduce Net Revenue for India. For
    # Australia/Perth it remains an inclusive carve-out from Net Revenue.
    if gst_on_sales > 0:
        gst_rate_label = "5%" if summary.get("country") == "India" else "10%"
        if is_australia:
            fin_data.append([
                f"Less: GST on Eligible Sales ({gst_rate_label} inclusive)",
                f"({currency} {gst_on_sales:,.2f})",
            ])
        else:
            # India: informational footnote — keeps the math consistent with
            # the Net Revenue UI tile (Total Sales − Commissions, no GST).
            fin_data.append([
                f"GST on Eligible Sales ({gst_rate_label}) — informational",
                f"{currency} {gst_on_sales:,.2f}",
            ])
    # Per Feb-2026 owner directive — Net Revenue is HIDDEN. Revenue Share Base
    # is the canonical primary metric.
    if is_australia:
        # Australia keeps the AU-specific chain (Net Revenue line retained because
        # AU has the comm-GST inclusivity calc that's clearer as a chain)
        fin_data.append(["NET REVENUE", f"{currency} {fin['net_revenue']:,.2f}"])
        rev_share_formula = "⭐ Eligible Rev Share Base (Sales − Comm − Comm GST − GST)"
        rev_share_value = fin['net_revenue']
    else:
        # India: Revenue Share Base = Sales − Comm − GST
        rev_share_formula = "⭐ REVENUE SHARE BASE (Sales − Commissions − GST)"
        rev_share_value = round(fin['net_revenue'] - gst_on_sales, 2)
    fin_data.append([
        rev_share_formula,
        f"{currency} {rev_share_value:,.2f}",
    ])
    if is_australia:
        # Australia: show explicit Profitability chain after Net Revenue
        fin_data.append(["Less: Total Expenses", f"({currency} {fin['total_expenses']:,.2f})"])
        prof_value = fin.get("profitability", fin['net_revenue'] - fin['total_expenses'])
        fin_data.append(["PROFITABILITY (Base for 80/20 Split)", f"{currency} {prof_value:,.2f}"])
    else:
        fin_data.append(["Less: Total Expenses (info)", f"({currency} {fin['total_expenses']:,.2f})"])
    fin_data.append(["", ""])
    fin_data.append(["Working Capital (Security Deposit)", f"{currency} {fin['working_capital']:,.2f}"])
    wc_st = fin.get("wc_standing", {})
    if wc_st:
        fin_data.append(["Opening WC", f"{currency} {wc_st.get('opening_wc', 0):,.2f}"])
        fin_data.append(["This Month P&L", f"{currency} {wc_st.get('this_month_pnl', 0):,.2f}"])
        fin_data.append(["Closing WC (BAL.)", f"{currency} {wc_st.get('closing_wc', 0):,.2f}"])
        fin_data.append(["Diff from Initial", f"{currency} {wc_st.get('diff_from_initial', 0):,.2f}"])
        if wc_st.get("loan_from_wc_deficit", 0) > 0:
            fin_data.append(["Loan from WC Deficit (this month)", f"{currency} {wc_st['loan_from_wc_deficit']:,.2f}"])
        if wc_st.get("loans_outstanding", 0) > 0:
            fin_data.append(["Recorded Loans Outstanding", f"({currency} {wc_st['loans_outstanding']:,.2f})"])
        if wc_st.get("total_effective_loans", 0) > 0:
            fin_data.append(["Total Effective Loans", f"{currency} {wc_st['total_effective_loans']:,.2f}"])
        wc_pct = wc_st.get("wc_percentage", 100)
        wc_status = wc_st.get("wc_status", "healthy")
        # Map status to PIB label. "protection" status fires when WC ≤ 50% of base
        # (which includes the case where WC has gone negative — e.g. base 9L,
        # closing -37L → wc_pct = -413%). Show that as CRITICAL so the franchise
        # owner immediately sees the WC has been wiped out, not "Healthy".
        if wc_status == "healthy":
            status_label = "HEALTHY"
        elif wc_status == "restoring":
            status_label = "RESTORING"
        elif wc_pct < 0:
            status_label = "CRITICAL (WC Depleted)"
        else:
            status_label = "PROTECTION (Below 50%)"
        fin_data.append(["WC Status", f"{wc_pct:.0f}% - {status_label}"])
        if not wc_st.get("revenue_share_active", True) and fin.get("working_capital", 0) > 0:
            fin_data.append(["", ""])
            fin_data.append(["*** REVENUE SHARE & MG: CLOSED ***", "WC below 50% threshold"])

    net_revenue_row_idx = 5 if len(fin_data) > 5 else len(fin_data) - 3
    profitability_row_idx = None
    # Find highlighted row — prefer REVENUE SHARE BASE (India), fall back to
    # NET REVENUE (Australia), then PROFITABILITY (AU additional emphasis).
    for i, r in enumerate(fin_data):
        if r and isinstance(r[0], str) and "REVENUE SHARE BASE" in r[0].upper():
            net_revenue_row_idx = i
        elif r and r[0] == "NET REVENUE":
            # Only used as fallback when REVENUE SHARE BASE isn't present (AU)
            if net_revenue_row_idx == 5:
                net_revenue_row_idx = i
        elif r and isinstance(r[0], str) and r[0].startswith("PROFITABILITY"):
            profitability_row_idx = i
    fin_table = Table(fin_data, colWidths=[280, 170])
    fin_style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, net_revenue_row_idx), (-1, net_revenue_row_idx), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, net_revenue_row_idx), (-1, net_revenue_row_idx), BRAND_GOLD),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if profitability_row_idx is not None:
        fin_style.append(("FONTNAME", (0, profitability_row_idx), (-1, profitability_row_idx), "Helvetica-Bold"))
        fin_style.append(("BACKGROUND", (0, profitability_row_idx), (-1, profitability_row_idx), colors.HexColor("#c8e6c9")))
    fin_table.setStyle(TableStyle(fin_style))
    story.append(fin_table)
    story.append(Spacer(1, 15))

    # --- 4b. Cash Inflows (Non-Operating) + Inter-Center Loans ---------------
    other_income = summary.get("other_income") or {}
    loans_taken = summary.get("loans_taken") or {}
    loans_given = summary.get("loans_given") or {}
    oi_total = float(other_income.get("total", 0) or 0)
    lt_total = float(loans_taken.get("total", 0) or 0)
    lg_total = float(loans_given.get("total", 0) or 0)

    if oi_total > 0 or lt_total > 0 or lg_total > 0:
        story.append(Paragraph("4B. CASH INFLOWS (NON-OPERATING) & INTER-CENTER LOANS",
                               styles["PIBSection"]))
        story.append(Paragraph(
            "<b>Memo only.</b> These rows do NOT affect Sales / P&amp;L / Revenue Share / MG / "
            "Working Capital. Loans taken are liabilities — they do not increase real WC, "
            "even though cash flows in. Repayment is tracked separately on the Loan Ledger.",
            styles["PIBNote"] if "PIBNote" in styles.byName else styles["BodyText"],
        ))
        story.append(Spacer(1, 4))

        inflow_rows = [["Description", "Category / Source", "Amount", "Status"]]

        # Other Income rows
        by_cat = other_income.get("by_category", {}) or {}
        if oi_total > 0:
            for cat, amt in by_cat.items():
                inflow_rows.append([
                    "Other Income",
                    cat.replace("_", " ").title(),
                    f"{currency} {float(amt or 0):,.2f}",
                    "Memo only · does NOT alter WC",
                ])

        # Loans taken (borrower's own PIB — source center SHOWN)
        for r in (loans_taken.get("rows") or []):
            status = (r.get("status") or "active").replace("_", " ").title()
            inflow_rows.append([
                "Loan Taken",
                f"From {r.get('source_center') or 'External'}",
                f"{currency} {float(r.get('amount', 0) or 0):,.2f}",
                f"Repaid: {currency} {float(r.get('repaid', 0) or 0):,.2f} · "
                f"Outstanding: {currency} {float(r.get('outstanding', 0) or 0):,.2f} · {status}",
            ])

        # Loans given (lender's own PIB — destination HIDDEN per policy)
        for r in (loans_given.get("rows") or []):
            status = (r.get("status") or "active").replace("_", " ").title()
            inflow_rows.append([
                "Loan Given",
                "To Other Center",
                f"({currency} {float(r.get('amount', 0) or 0):,.2f})",
                f"Repaid: {currency} {float(r.get('repaid', 0) or 0):,.2f} · "
                f"Outstanding: {currency} {float(r.get('outstanding', 0) or 0):,.2f} · {status}",
            ])

        inflow_tbl = Table(inflow_rows, colWidths=[90, 120, 90, 160])
        inflow_tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(inflow_tbl)
        story.append(Spacer(1, 15))

    # --- 5. Commission Summary (continued) ---------------------------------

    # --- 5. Operational Sustainability + Revenue Share Base ----------------
    # TWO distinct calculations per Feb-2026 user directive:
    #   1. PROFIT / LOSS (Operational Balance) = Sales − Expenses − Commissions
    #      GST is NOT deducted (it's a govt pass-through booked in M+1).
    #   2. REVENUE SHARE BASE = Sales − Commissions − GST
    #      GST IS deducted (franchise owner's entitlement is on ex-GST revenue).
    ops = summary.get("operational_sustainability", {})
    story.append(Paragraph("5. OPERATIONAL SUSTAINABILITY CHECK", styles["PIBSection"]))

    # 5a — Profit / Loss
    ops_data = [
        ["A. Profit / Loss Calculation", "Amount"],
        ["Total Sales", f"{currency} {ops.get('total_sales', 0):,.2f}"],
        ["Less: Total Expenses", f"({currency} {ops.get('total_expenses', 0):,.2f})"],
        ["Less: Total Commissions", f"({currency} {ops.get('total_commissions', 0):,.2f})"],
    ]
    gst_liability = ops.get("gst_on_sales", 0)
    if gst_liability > 0:
        gst_label_rate = "5%" if summary.get("country") == "India" else "10%"
        ops_data.append([
            f"GST on Eligible Sales ({gst_label_rate}) — informational only",
            f"{currency} {gst_liability:,.2f}",
        ])
    ops_data.append(["", ""])
    pl_value = ops.get("profit_loss", ops.get("operational_balance", 0))
    ops_data.append(["PROFIT / LOSS (OPERATIONAL BALANCE)",
                     f"{currency} {pl_value:,.2f}"])
    ops_balance_positive = ops.get("is_positive", True)
    ops_table = Table(ops_data, colWidths=[280, 170])
    ops_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1),
         colors.HexColor("#e8f5e9") if ops_balance_positive else colors.HexColor("#ffcdd2")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(ops_table)
    story.append(Spacer(1, 8))

    # 5b — Revenue Share Base (separate from Profit/Loss above)
    rev_share_base = ops.get("revenue_share_base", 0)
    rev_share_data = [
        ["B. Revenue Share Base (for franchise owner % split)", "Amount"],
        ["Total Sales", f"{currency} {ops.get('total_sales', 0):,.2f}"],
        ["Less: Total Commissions", f"({currency} {ops.get('total_commissions', 0):,.2f})"],
    ]
    if gst_liability > 0:
        rev_share_data.append([
            f"Less: GST on Eligible Sales ({gst_label_rate} inclusive)",
            f"({currency} {gst_liability:,.2f})",
        ])
    rev_share_data.append(["", ""])
    rev_share_data.append(["REVENUE SHARE BASE", f"{currency} {rev_share_base:,.2f}"])
    rev_share_table = Table(rev_share_data, colWidths=[280, 170])
    rev_share_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e3f2fd")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(rev_share_table)
    story.append(Spacer(1, 6))
    note_style = styles.get("Italic", styles["BodyText"])
    story.append(Paragraph(
        "<b>Note:</b> Profit/Loss measures operational health (expenses included, GST excluded). "
        "Revenue Share Base measures the franchise owner's entitlement (commissions &amp; GST excluded, expenses excluded). "
        "Both are computed from the same Total Sales but serve different purposes.",
        note_style,
    ))
    story.append(Spacer(1, 15))

    # --- 6. Working Capital Status -----------------------------------------
    wc_st_info = summary.get("working_capital_status", {})
    story.append(Paragraph("6. WORKING CAPITAL STATUS", styles["PIBSection"]))
    wc_protection = wc_st_info.get("protection_mode", False)
    wc_status_data = [
        ["Description", "Value"],
        ["Base Working Capital", f"{currency} {wc_st_info.get('base_wc', wc_st_info.get('initial_wc', 0)):,.2f}"],
        ["Opening WC (This Month)", f"{currency} {wc_st_info.get('opening_wc', 0):,.2f}"],
        ["WC Used for Operational Loss", f"{currency} {wc_st_info.get('wc_used', 0):,.2f}"],
        ["WC Restored from Profit", f"{currency} {wc_st_info.get('wc_restored', 0):,.2f}"],
        ["Current Working Capital", f"{currency} {wc_st_info.get('current_wc', 0):,.2f}"],
        ["WC % vs Base", f"{wc_st_info.get('wc_percentage', 100):.0f}%"],
        ["Threshold", wc_st_info.get("threshold", "50%")],
        ["Revenue Share Status",
         "BLOCKED" if wc_protection or not wc_st_info.get("revenue_share_active", True) else "Active"],
        ["Status", wc_st_info.get("status", "Healthy")],
    ]
    wc_status_table = Table(wc_status_data, colWidths=[280, 170])
    wc_status_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1),
         colors.HexColor("#ffcdd2") if wc_protection else colors.HexColor("#e8f5e9")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(wc_status_table)
    story.append(Spacer(1, 15))

    # --- 7. Revenue/Profit Share Calculation -------------------------------
    share = summary["share_calculation"]
    # India "revenue_share" uses Revenue Share Base (Sales − Commissions − GST) as the base.
    # Australia "profit_share" uses Profitability (NetRev − Expenses).
    base_label = "Profitability" if share["type"] == "profit_share" else "Revenue Share Base"
    wc_gated = share.get("wc_gated", False)
    section_title = f"7. {share['type'].upper().replace('_', ' ')} CALCULATION"
    if wc_gated:
        section_title += " (*** CLOSED - WC BELOW 50% ***)"
    else:
        split = f"{share['franchise_owner']['percentage']}/{share['purnabramha']['percentage']}"
        section_title += f" ({split} SPLIT)"
    story.append(Paragraph(section_title, styles["PIBSection"]))

    share_data = [
        ["Description", "Percentage", "Amount"],
        [f"{base_label} (Base for Calculation)", "", f"{currency} {share['net_profit_or_sales']:,.2f}"],
        ["", "", ""],
        ["FRANCHISE OWNER SHARE", f"{share['franchise_owner']['percentage']}%", f"{currency} {share['franchise_owner']['amount']:,.2f}"],
        ["", "", ""],
        [entity_share_label(summary.get("country")).upper(), f"{share['purnabramha']['percentage']}%", f"{currency} {share['purnabramha']['base_amount']:,.2f}"],
    ]
    if summary["country"] == "India":
        share_data.append(["  Add: CGST (9%)", "", f"{currency} {share['purnabramha']['cgst']:,.2f}"])
        share_data.append(["  Add: SGST (9%)", "", f"{currency} {share['purnabramha']['sgst']:,.2f}"])
    else:
        share_data.append([f"  Add: GST ({summary['tax_rules']['share_gst_rate']:.0f}%)", "",
                           f"{currency} {share['purnabramha']['gst_amount']:,.2f}"])
    share_data.append([f"{entity_for_country(summary.get('country')).upper()} TOTAL (WITH GST)", "", f"{currency} {share['purnabramha']['total_payable']:,.2f}"])

    share_table = Table(share_data, colWidths=[220, 80, 150])
    share_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
        ("FONTNAME", (0, 5), (-1, 5), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#e8f5e9")),
        ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#fff3e0")),
        ("BACKGROUND", (0, -1), (-1, -1), BRAND_MAROON),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(share_table)
    story.append(Spacer(1, 15))

    # --- 8. Payout Determination -------------------------------------------
    payout = summary.get("payout", {})
    overseas_pdf = (summary.get("country") or "India").lower() != "india"
    overseas_share_pdf = summary.get("overseas_share") or {}
    mfpl_pdf = summary.get("mfpl_royalty") or {}
    if payout:
        story.append(Paragraph("8. PAYOUT DETERMINATION", styles["PIBSection"]))
        payout_data = [
            ["Description", "Amount"],
            ["Operational Balance", f"{currency} {payout.get('operational_balance', 0):,.2f}"],
        ]
        if overseas_pdf:
            payout_data.append(["Eligible Profit (Sales − GST − Comm − CommGST − Exp)",
                                f"{currency} {overseas_share_pdf.get('eligible_profit', 0):,.2f}"])
            payout_data.append(["Franchise Owner Share (80%)",
                                f"{currency} {overseas_share_pdf.get('owner_share', 0):,.2f}"])
            payout_data.append([f"{entity_share_label(summary.get('country'))} (20%)",
                                f"{currency} {overseas_share_pdf.get('franchisor_share', 0):,.2f}"])
            payout_data.append(["MFPL Royalty Accrued (5% Net Sales)",
                                f"{currency} {overseas_share_pdf.get('mfpl_royalty', 0):,.2f}"])
        else:
            payout_data.append(["MG (Minimum Guarantee)", f"{currency} {payout.get('mg_amount', 0):,.2f}"])
            payout_data.append(["Franchise Owner Revenue Share", f"{currency} {payout.get('revenue_share_amount', 0):,.2f}"])
        payout_data.append(["", ""])
        if payout.get("protection_mode"):
            if payout.get("operational_balance", 0) > 0:
                payout_data.append(["PAYABLE (REVENUE SHARE - PROTECTION MODE)", f"{currency} {payout.get('amount', 0):,.2f}"])
                if payout.get("wc_recovery_amount", 0) > 0:
                    payout_data.append(["WC Recovery Amount", f"{currency} {payout.get('wc_recovery_amount', 0):,.2f}"])
                if not overseas_pdf:
                    payout_data.append(["MG Status", "BLOCKED (Protection Mode)"])
            else:
                payout_data.append(["PAYABLE", f"{currency} 0.00"])
                if not overseas_pdf:
                    payout_data.append(["MG Status", "BLOCKED (Protection Mode)"])
            payout_data.append(["Reason", payout.get("reason", "")])
        else:
            payout_data.append([f"PAYABLE ({payout.get('type', 'revenue_share').replace('_', ' ').upper()})",
                                f"{currency} {payout.get('amount', 0):,.2f}"])
            payout_data.append(["Reason", payout.get("reason", "")])
        # Index of the main PAYABLE row (varies depending on overseas vs India / protection mode)
        _payable_idx = next((i for i, r in enumerate(payout_data)
                             if r and isinstance(r[0], str) and r[0].startswith("PAYABLE")), len(payout_data) - 2)
        payout_table = Table(payout_data, colWidths=[280, 170])
        payout_style = [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
        if payout.get("protection_mode"):
            payout_style.append(("BACKGROUND", (0, _payable_idx), (-1, _payable_idx), colors.HexColor("#ffcdd2")))
        else:
            payout_style.append(("BACKGROUND", (0, _payable_idx), (-1, _payable_idx), BRAND_GOLD))
        payout_table.setStyle(TableStyle(payout_style))
        story.append(payout_table)
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "<i>Revenue share distribution follows Operational Sustainability rules. "
            "Operational costs and working capital protection are prioritized before profit distribution.</i>",
            styles["PIBBody"],
        ))
        story.append(Spacer(1, 15))

        # --- 8B. Final Payout (Revenue Share + GST) -------------------------
        # Section 9 already captures the tax rules; users wanted the final
        # invoice-able amount (Revenue Share + CGST 9% + SGST 9% for India,
        # Profit Share + GST for Australia) shown explicitly *before* Section
        # 9 so the franchise owner / CA can see what to invoice / pay in one
        # number.
        try:
            tax_rules_block = summary.get("tax_rules", {}) or {}
            share_gst_rate = float(tax_rules_block.get("share_gst_rate") or 0)
            payable_amount = float(payout.get("amount") or 0)
            if share_gst_rate > 0 and payable_amount > 0:
                country_block = (tax_rules_block.get("country") or "").lower()
                if country_block == "india":
                    half = share_gst_rate / 2.0
                    cgst = round(payable_amount * half / 100.0, 2)
                    sgst = round(payable_amount * half / 100.0, 2)
                    total_gst = round(cgst + sgst, 2)
                    final_total = round(payable_amount + total_gst, 2)
                    final_label = "Total Final Payout (incl. 18% GST)"
                    # Label the base row honestly: if MG > Rev Share, the
                    # payout reflects MG, not the bare revenue share.
                    mg_amount = float(payout.get("mg_amount") or 0)
                    rev_amount = float(payout.get("revenue_share_amount") or 0)
                    base_label = ("Monthly Guarantee Payout (MG > Rev Share)"
                                  if mg_amount > rev_amount and abs(payable_amount - mg_amount) < 0.01
                                  else "Revenue Share Payable")
                    final_data = [
                        ["Description", "Amount"],
                        [base_label,                     f"{currency} {payable_amount:,.2f}"],
                        [f"Add: CGST @ {half:.0f}%",     f"{currency} {cgst:,.2f}"],
                        [f"Add: SGST @ {half:.0f}%",     f"{currency} {sgst:,.2f}"],
                        [final_label,                    f"{currency} {final_total:,.2f}"],
                    ]
                else:
                    # Australia / outside-IN — single-line GST add-on. Overseas
                    # has no MG; always label as Profit Share. MFPL accrued is
                    # added as a separate liability row.
                    gst_amount = round(payable_amount * share_gst_rate / 100.0, 2)
                    final_total = round(payable_amount + gst_amount, 2)
                    final_data = [
                        ["Description", "Amount"],
                        ["Profit Share Payable (80% of Eligible Profit)",     f"{currency} {payable_amount:,.2f}"],
                        [f"Add: GST @ {share_gst_rate:.0f}%",                 f"{currency} {gst_amount:,.2f}"],
                        [f"Total Final Payout (incl. {share_gst_rate:.0f}% GST)", f"{currency} {final_total:,.2f}"],
                    ]
                    _mfpl_outstanding = float(mfpl_pdf.get("outstanding_mfpl") or 0)
                    if _mfpl_outstanding > 0:
                        final_data.append([
                            "MFPL Royalty Liability (cumulative, 5% Net Sales)",
                            f"{currency} {_mfpl_outstanding:,.2f}",
                        ])

                story.append(Paragraph("8B. FINAL PAYOUT (Revenue Share + GST)", styles["PIBSection"]))
                final_table = Table(final_data, colWidths=[280, 170])
                final_table.setStyle(TableStyle([
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, -1), (-1, -1), BRAND_MAROON),
                    ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(final_table)
                story.append(Spacer(1, 6))
                story.append(Paragraph(
                    "<i>This is the gross-of-tax amount to be invoiced / paid to the Franchise Owner. "
                    "The GST split below is reproduced under Section 9 for reference.</i>",
                    styles["PIBBody"],
                ))
                story.append(Spacer(1, 15))
        except Exception:
            # Final-payout block is purely additive; never block PIB rendering
            pass

    # --- 9. Tax Rules -------------------------------------------------------
    story.append(Paragraph("9. TAX RULES APPLIED", styles["PIBSection"]))
    tax_rules = summary["tax_rules"]
    if tax_rules["country"] == "Australia":
        tax_note = (f"<b>Country:</b> {tax_rules['country']}<br/>"
                    f"<b>Sales GST:</b> {tax_rules['sales_gst_rate']:.0f}% (GST Inclusive - already included in sale value)<br/>"
                    f"<b>Profit Share GST:</b> {tax_rules['share_gst_rate']:.0f}%")
    else:
        tax_note = (f"<b>Country:</b> {tax_rules['country']}<br/>"
                    f"<b>Sales GST:</b> {tax_rules['sales_gst_rate']:.0f}%<br/>"
                    f"<b>Revenue Share GST:</b> {tax_rules['share_gst_rate']:.0f}% (CGST 9% + SGST 9%)")
    story.append(Paragraph(tax_note, styles["PIBBody"]))
    story.append(Spacer(1, 30))

    # Authorised signatory block (CFO of Accounts) — keyed off center country
    try:
        from utils.signature import signature_block
        story.extend(signature_block(country=summary.get("country") or "India",
                                     label="Authorised Signatory · Accounts"))
    except Exception:
        pass

    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d-%b-%Y %H:%M')} | Purnabramha - Manaswini Foods Pvt. Ltd.",
        ParagraphStyle("Footer", fontSize=8, alignment=TA_CENTER, textColor=colors.grey),
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# =============================================================================
# GST Summary — PDF
# =============================================================================
def build_gst_summary_pdf(summary: Dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=60, bottomMargin=50)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("GSTTitle", fontSize=16, alignment=TA_CENTER, fontName="Helvetica-Bold",
                              textColor=BRAND_NAVY, spaceAfter=20))
    styles.add(ParagraphStyle("GSTBody", fontSize=10, fontName="Helvetica",
                              textColor=DARK_GRAY, spaceAfter=8))

    story: List[Any] = [
        Paragraph("PURNABRAMHA - GST SUMMARY REPORT", styles["GSTTitle"]),
        Paragraph(
            f"Center: {summary['center_name']} | Period: {summary['period']} | Country: {summary['country']}",
            styles["GSTBody"]),
        Spacer(1, 20),
    ]

    currency = "AUD" if summary["country"] == "Australia" else "Rs."
    tax_rules = summary["tax_rules"]

    # Use the pre-computed GST (from financial_summary.sales_gst) which is
    # already based on ELIGIBLE sales (Total − Swiggy − Zomato − DoorDash)
    # using the INCLUSIVE formula: GST = eligible − eligible / (1 + rate).
    # Fallback uses the same shared utility to stay consistent.
    sales_total = float(summary["sales"].get("total_sale", 0) or 0)
    aggregator_total = float(summary["sales"].get("aggregator_sale", 0) or 0)
    eligible_base = max(0.0, sales_total - aggregator_total)
    sales_gst = float(summary.get("financial_summary", {}).get("sales_gst", 0) or 0)
    if sales_gst == 0:  # fallback — use shared utility (inclusive)
        from utils.gst import carve_inclusive_gst
        rate = (AUSTRALIA_GST_INCLUSIVE if summary["country"] == "Australia"
                else tax_rules["sales_gst_rate"] / 100.0)
        sales_gst = carve_inclusive_gst(eligible_base, rate)

    gst_data = [
        ["Description", "Taxable Amount", "GST Rate", "GST Amount"],
        ["Total Sales (Gross)", f"{currency} {sales_total:,.2f}", "-", "-"],
        ["Less: Aggregator Sales (Swiggy/Zomato/DoorDash)",
         f"({currency} {aggregator_total:,.2f})", "-", "-"],
        ["Eligible Sales (Taxable Base)",
         f"{currency} {eligible_base:,.2f}",
         f"{tax_rules['sales_gst_rate']:.0f}%",
         f"{currency} {sales_gst:,.2f}"],
        ["Revenue/Profit Share",
         f"{currency} {summary['share_calculation']['purnabramha']['base_amount']:,.2f}",
         f"{tax_rules['share_gst_rate']:.0f}%",
         f"{currency} {summary['share_calculation']['purnabramha']['gst_amount']:,.2f}"],
    ]
    if summary["country"] == "India":
        gst_data.append(["  - CGST (9%)", "", "", f"{currency} {summary['share_calculation']['purnabramha']['cgst']:,.2f}"])
        gst_data.append(["  - SGST (9%)", "", "", f"{currency} {summary['share_calculation']['purnabramha']['sgst']:,.2f}"])

    gst_table = Table(gst_data, colWidths=[230, 100, 60, 100])
    gst_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(gst_table)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# =============================================================================
# Commission Summary — PDF
# =============================================================================
def build_commission_summary_pdf(summary: Dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=60, bottomMargin=50)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("CommTitle", fontSize=16, alignment=TA_CENTER, fontName="Helvetica-Bold",
                              textColor=BRAND_NAVY, spaceAfter=20))

    story: List[Any] = [
        Paragraph("PURNABRAMHA - COMMISSION SUMMARY REPORT", styles["CommTitle"]),
        Paragraph(f"Center: {summary['center_name']} | Period: {summary['period']}", styles["Normal"]),
        Spacer(1, 20),
    ]

    currency = "AUD" if summary["country"] == "Australia" else "Rs."
    commissions = summary["commissions"]
    comm_data = [["Platform", "Gross Orders", "Total Deductions", "Net Payout", "Deduction %"]]
    for platform, data in commissions["by_platform"].items():
        ded = data.get("deduction", data.get("commission", 0))
        comm_pct = (ded / data["gross"] * 100) if data["gross"] > 0 else 0
        comm_data.append([
            platform.title().replace("_", " "),
            f"{currency} {data['gross']:,.2f}",
            f"{currency} {ded:,.2f}",
            f"{currency} {data['net']:,.2f}",
            f"{comm_pct:.1f}%",
        ])
    comm_data.append(["TOTAL", "", f"{currency} {commissions['total']:,.2f}", "", ""])

    comm_table = Table(comm_data, colWidths=[100, 100, 100, 100, 70])
    comm_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GRAY),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(comm_table)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# =============================================================================
# MG Payout — Excel + PDF
# =============================================================================
def build_mg_payout_excel(center: str, monthly_data: List[Dict[str, Any]],
                          totals: Dict[str, Any], period: Dict[str, Any],
                          franchise_info: Dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    rs_pct = float(franchise_info.get("revenue_share_percentage", 0) or 0)
    rows = []
    for m in monthly_data:
        month_label = datetime.strptime(m["month"] + "-01", "%Y-%m-%d").strftime("%b %Y")
        # Revenue Share Base = Sales − Comm − GST (Feb-2026 owner directive).
        # Revenue Share Payout = Base × franchise %. Both columns surfaced
        # per Feb-2026 transparency spec.
        sales_m = float(m.get("total_sales", 0) or 0)
        gst_m = float(m.get("gst_on_sales", 0) or 0)
        comm_m = float(m.get("total_commissions", 0) or 0)
        rev_share_base_m = round(sales_m - comm_m - gst_m, 2)
        rev_share_payout_m = float(m.get("revenue_share", round(rev_share_base_m * rs_pct / 100, 2)) or 0)
        rows.append({
            "Month": month_label,
            "Total Sales": sales_m,
            "GST": gst_m,
            "Commissions": comm_m,
            "Revenue Share Base": rev_share_base_m,
            f"Revenue Share Payout ({rs_pct:g}%)": rev_share_payout_m,
            "MG": m.get("mg_amount", 0),
            "Type": "MG" if m.get("payable_type") == "mg" else "Revenue Share",
            "Payable": m.get("payable_amount", 0),
            "Paid": m.get("paid", 0),
            "Pending": m.get("pending", 0),
            "Status": m.get("status", "").capitalize(),
        })
    total_sales = sum(float(m.get("total_sales", 0) or 0) for m in monthly_data)
    total_gst = sum(float(m.get("gst_on_sales", 0) or 0) for m in monthly_data)
    total_comm = sum(float(m.get("total_commissions", 0) or 0) for m in monthly_data)
    total_rev_share_base = round(total_sales - total_comm - total_gst, 2)
    total_rev_share_payout = sum(float(m.get("revenue_share", 0) or 0) for m in monthly_data)
    rows.append({
        "Month": "TOTAL",
        "Total Sales": total_sales,
        "GST": total_gst,
        "Commissions": total_comm,
        "Revenue Share Base": total_rev_share_base,
        f"Revenue Share Payout ({rs_pct:g}%)": total_rev_share_payout,
        "MG": totals.get("mg", 0),
        "Type": "",
        "Payable": totals.get("payable", 0),
        "Paid": totals.get("paid", 0),
        "Pending": totals.get("pending", 0),
        "Status": "",
    })
    # Final Payout grossup
    is_intl = str(center or "").upper().endswith("-PERTH") or (str(franchise_info.get("country", "")).lower() == "australia")
    final_gst_rate = 10 if is_intl else 18
    payable_total = float(totals.get("payable", 0) or 0)
    final_gst_amt = round(payable_total * final_gst_rate / 100.0, 2)
    final_payout_incl_gst = round(payable_total + final_gst_amt, 2)
    blank_cols = {
        "Total Sales": "", "GST": "", "Commissions": "",
        "Revenue Share Base": "",
        f"Revenue Share Payout ({rs_pct:g}%)": "",
        "MG": "", "Type": "",
        "Paid": "", "Pending": "", "Status": "",
    }
    rows.append({
        "Month": f"Add: {final_gst_rate}% GST on Rev Share",
        **blank_cols,
        "Payable": final_gst_amt,
    })
    rows.append({
        "Month": f"Total Final Payout (incl. {final_gst_rate}% GST)",
        **blank_cols,
        "Payable": final_payout_incl_gst,
    })
    df = pd.DataFrame(rows)
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        header_df = pd.DataFrame([
            ["MG Payout Report"],
            [f"Center: {center}"],
            [f"Franchise: {franchise_info.get('name', 'N/A')} ({franchise_info.get('code', 'N/A')})"],
            [f"Monthly MG: {franchise_info.get('mg_amount', 0)}"],
            [f"Period: {period.get('from', '')} to {period.get('to', '')}"],
            [""],
        ])
        header_df.to_excel(writer, sheet_name="MG Payout", index=False, header=False, startrow=0)
        df.to_excel(writer, sheet_name="MG Payout", index=False, startrow=7)
        ws = writer.sheets["MG Payout"]
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 20)
    buf.seek(0)
    return buf.getvalue()


def build_mg_payout_pdf(center: str, monthly_data: List[Dict[str, Any]],
                        totals: Dict[str, Any], period: Dict[str, Any],
                        franchise_info: Dict[str, Any],
                        payout_release_status: Optional[Dict[str, Any]] = None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements: List[Any] = []

    logo_path = Path(__file__).resolve().parent.parent / "assets" / "pb_logo.png"
    if logo_path.exists():
        try:
            elements.append(Image(str(logo_path), width=1.2 * inch, height=0.7 * inch))
        except Exception:
            pass

    # Banner appears at the top, right after the logo
    if payout_release_status:
        _append_payout_status_banner(elements, payout_release_status)

    elements.append(Paragraph("MG Payout Report",
                              ParagraphStyle("MGTitle", parent=styles["Heading1"],
                                             fontSize=16, alignment=TA_CENTER, spaceAfter=6)))
    elements.append(Spacer(1, 6))

    sub_style = ParagraphStyle("MGSub", parent=styles["Normal"], fontSize=9,
                               alignment=TA_CENTER, textColor=colors.gray)
    elements.append(Paragraph(
        f"Center: {center} | Franchise: {franchise_info.get('name', 'N/A')} ({franchise_info.get('code', 'N/A')})",
        sub_style))
    elements.append(Paragraph(
        f"Monthly MG: Rs. {franchise_info.get('mg_amount', 0):,.2f} | Period: {period.get('from', '')} to {period.get('to', '')}",
        sub_style))
    elements.append(Spacer(1, 12))

    # Compute Final Payout (incl. GST) once so summary + footer agree.
    is_intl_summary = str(center or "").upper().endswith("-PERTH") or (str(franchise_info.get("country", "")).lower() == "australia")
    final_gst_rate_summary = 10 if is_intl_summary else 18
    final_payout_summary = round(float(totals.get("payable", 0) or 0) * (1 + final_gst_rate_summary / 100.0), 2)

    summary_data_table = [
        ["Total Revenue Share", "Total MG", "Total Payable", f"Final Payout (incl. {final_gst_rate_summary}% GST)", "Total Pending"],
        [
            f"Rs. {totals.get('revenue_share', 0):,.2f}",
            f"Rs. {totals.get('mg', 0):,.2f}",
            f"Rs. {totals.get('payable', 0):,.2f}",
            f"Rs. {final_payout_summary:,.2f}",
            f"Rs. {totals.get('pending', 0):,.2f}",
        ],
    ]
    summary_table = Table(summary_data_table, colWidths=[105, 95, 95, 110, 80])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, 1), 9),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        # Highlight the Final Payout (incl. GST) cell in emerald to make the
        # invoiceable amount stand out at a glance.
        ("BACKGROUND", (3, 1), (3, 1), colors.HexColor("#dcfce7")),
        ("TEXTCOLOR", (3, 1), (3, 1), colors.HexColor("#166534")),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 16))

    # Per Feb-2026 spec: include Revenue Share Payout column for transparency.
    # Order: Rev Share Base → Rev Share Payout → MG → Type → Payable
    rs_pct = float(franchise_info.get("revenue_share_percentage", 0) or 0)
    table_header = ["Month", "Total Sales", "GST", "Comm", "Rev Share Base",
                    f"Rev Share Payout ({rs_pct:g}%)", "MG", "Type",
                    "Payable", "Paid", "Pending", "Status"]
    table_rows: List[List[Any]] = [table_header]
    for m in monthly_data:
        month_label = datetime.strptime(m["month"] + "-01", "%Y-%m-%d").strftime("%b %Y")
        ptype = "MG" if m.get("payable_type") == "mg" else "RS"
        s_m = float(m.get("total_sales", 0) or 0)
        g_m = float(m.get("gst_on_sales", 0) or 0)
        c_m = float(m.get("total_commissions", 0) or 0)
        rsb_m = round(s_m - c_m - g_m, 2)
        rs_payout_m = float(m.get("revenue_share", round(rsb_m * rs_pct / 100, 2)) or 0)
        table_rows.append([
            month_label,
            f'{s_m:,.0f}',
            f'{g_m:,.0f}',
            f'{c_m:,.0f}',
            f'{rsb_m:,.0f}',
            f'{rs_payout_m:,.0f}',
            f'{m.get("mg_amount", 0):,.0f}',
            ptype,
            f'{m.get("payable_amount", 0):,.0f}',
            f'{m.get("paid", 0):,.0f}',
            f'{m.get("pending", 0):,.0f}',
            m.get("status", "").capitalize(),
        ])
    table_rows.append([
        "TOTAL",
        f'{sum(float(m.get("total_sales", 0) or 0) for m in monthly_data):,.0f}',
        f'{sum(float(m.get("gst_on_sales", 0) or 0) for m in monthly_data):,.0f}',
        f'{sum(float(m.get("total_commissions", 0) or 0) for m in monthly_data):,.0f}',
        f'{(sum(float(m.get("total_sales", 0) or 0) for m in monthly_data) - sum(float(m.get("total_commissions", 0) or 0) for m in monthly_data) - sum(float(m.get("gst_on_sales", 0) or 0) for m in monthly_data)):,.0f}',
        f'{sum(float(m.get("revenue_share", 0) or 0) for m in monthly_data):,.0f}',
        f'{totals.get("mg", 0):,.0f}',
        "",
        f'{totals.get("payable", 0):,.0f}',
        f'{totals.get("paid", 0):,.0f}',
        f'{totals.get("pending", 0):,.0f}',
        "",
    ])
    # Final Payout grossup rows — same logic as the Excel export so PDFs and
    # workbooks agree on the invoiceable amount.
    is_intl_pdf = str(center or "").upper().endswith("-PERTH") or (str(franchise_info.get("country", "")).lower() == "australia")
    final_gst_rate_pdf = 10 if is_intl_pdf else 18
    payable_total_pdf = float(totals.get("payable", 0) or 0)
    final_gst_amt_pdf = round(payable_total_pdf * final_gst_rate_pdf / 100.0, 2)
    final_payout_pdf = round(payable_total_pdf + final_gst_amt_pdf, 2)
    table_rows.append([
        f"Add: {final_gst_rate_pdf}% GST on Rev Share",
        "", "", "", "", "", "", "",
        f'{final_gst_amt_pdf:,.0f}',
        "", "", "",
    ])
    table_rows.append([
        f"Total Final Payout (incl. {final_gst_rate_pdf}% GST)",
        "", "", "", "", "", "", "",
        f'{final_payout_pdf:,.0f}',
        "", "", "",
    ])

    # 12 columns. Compress widths.
    data_table = Table(table_rows, colWidths=[45, 52, 38, 38, 56, 60, 44, 28, 52, 42, 44, 38], repeatRows=1)
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, -1), 6.5),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (7, 0), (7, -1), "CENTER"),
        ("ALIGN", (-1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        # Alternate stripes for data rows only (skip the 3 footer rows: TOTAL, GST grossup, Final Payout).
        ("ROWBACKGROUNDS", (0, 1), (-1, -4), [colors.white, colors.HexColor("#f8fafc")]),
        # TOTAL row (index -3)
        ("BACKGROUND", (0, -3), (-1, -3), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, -3), (-1, -3), "Helvetica-Bold"),
        # "Add: GST" row (index -2)
        ("BACKGROUND", (0, -2), (-1, -2), colors.HexColor("#fef3c7")),
        ("FONTNAME", (0, -2), (-1, -2), "Helvetica-Oblique"),
        ("TEXTCOLOR", (0, -2), (-1, -2), colors.HexColor("#7B1E2A")),
        # "Total Final Payout" row (index -1)
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dcfce7")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#166534")),
    ]
    for i, m in enumerate(monthly_data, start=1):
        status = m.get("status", "")
        if status == "paid":
            table_style.append(("TEXTCOLOR", (-1, i), (-1, i), colors.HexColor("#166534")))
        elif status == "partial":
            table_style.append(("TEXTCOLOR", (-1, i), (-1, i), colors.HexColor("#92400e")))
        elif status == "unpaid":
            table_style.append(("TEXTCOLOR", (-1, i), (-1, i), colors.HexColor("#991b1b")))
    data_table.setStyle(TableStyle(table_style))
    elements.append(data_table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')} | Purnabramha - MANASWINI FOODS PVT. LTD.",
        ParagraphStyle("MGFooter", parent=styles["Normal"], fontSize=7,
                       textColor=colors.gray, alignment=TA_CENTER),
    ))

    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()



# =============================================================================
# Bank Activity / Cash Flow Statement — PDF
# =============================================================================
def build_bank_statement_pdf(data: Dict[str, Any]) -> bytes:
    """Monthly Bank Activity Statement — derived cash-flow view.

    Expected `data` dict:
      center, center_name, month, period_label
      opening_balance, closing_balance
      credits: [{date, description, amount}, ...]
      debits:  [{date, description, amount}, ...]
      totals:  {total_credits, total_debits, net_movement}
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36,
                            topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("BSTitle", fontSize=16, fontName="Helvetica-Bold",
                              textColor=BRAND_MAROON, alignment=TA_CENTER, spaceAfter=4))
    styles.add(ParagraphStyle("BSSub", fontSize=10, textColor=colors.gray,
                              alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle("BSSection", fontSize=11, fontName="Helvetica-Bold",
                              textColor=BRAND_NAVY, spaceBefore=10, spaceAfter=6))

    story: List[Any] = [
        Paragraph("PURNABRAMHA — BANK ACTIVITY STATEMENT", styles["BSTitle"]),
        Paragraph(
            f"{data.get('center_name', data.get('center', ''))} &nbsp; · &nbsp; {data.get('period_label', data.get('month', ''))}",
            styles["BSSub"],
        ),
    ]

    opening = float(data.get("opening_balance", 0) or 0)
    closing = float(data.get("closing_balance", 0) or 0)
    totals = data.get("totals", {}) or {}
    total_credits = float(totals.get("total_credits", 0) or 0)
    total_debits = float(totals.get("total_debits", 0) or 0)
    net = total_credits - total_debits

    # Summary band
    summary_tbl = Table([
        ["Opening Balance", "Credits (Inflows)", "Debits (Outflows)", "Net Movement", "Closing Balance"],
        [
            f"Rs. {opening:,.2f}",
            f"Rs. {total_credits:,.2f}",
            f"(Rs. {total_debits:,.2f})",
            f"{'+' if net >= 0 else '-'} Rs. {abs(net):,.2f}",
            f"Rs. {closing:,.2f}",
        ],
    ], colWidths=[100, 110, 110, 110, 100])
    summary_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, 1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (-1, 1), (-1, 1), BRAND_GOLD),
        ("TEXTCOLOR", (3, 1), (3, 1), colors.HexColor("#15803d") if net >= 0 else colors.red),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_tbl)

    def _section(title: str, rows: List[Dict[str, Any]], color: Any) -> None:
        story.append(Paragraph(title, styles["BSSection"]))
        if not rows:
            story.append(Paragraph("<i>No transactions.</i>",
                                   ParagraphStyle("BSEmpty", fontSize=9, textColor=colors.gray)))
            return
        table_data = [["Date", "Description", "Amount"]]
        for r in rows:
            table_data.append([
                r.get("date", ""),
                r.get("description", ""),
                f"Rs. {float(r.get('amount', 0) or 0):,.2f}",
            ])
        total = sum(float(r.get("amount", 0) or 0) for r in rows)
        table_data.append(["", "TOTAL", f"Rs. {total:,.2f}"])
        tbl = Table(table_data, colWidths=[70, 340, 120])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), color),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GRAY),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#fafafa")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)

    _section("CREDITS (Money In)", data.get("credits", []),
             colors.HexColor("#166534"))
    _section("DEBITS (Money Out)", data.get("debits", []),
             colors.HexColor("#991b1b"))

    story.append(Spacer(1, 18))
    story.append(Paragraph(
        "<i>This is a derived cash-flow statement built from recorded sales, expenses, commissions, "
        "GST liability payments and revenue-share payouts. It is not a bank-feed reconciliation.</i>",
        ParagraphStyle("BSNote", fontSize=7, textColor=colors.gray, alignment=TA_CENTER),
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')} | Purnabramha",
        ParagraphStyle("BSFooter", fontSize=7, textColor=colors.gray, alignment=TA_CENTER),
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()
