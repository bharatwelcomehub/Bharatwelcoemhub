"""Bundle Generator — single, consolidated downloadable artefacts per persona.

Per the Feb-2026 architecture refactor: instead of dozens of overlapping
exports (Revenue Share Report, Profit Share Report, Email Packs, MG Payout
PDF, Owner Reports, etc.), the platform ships only **three bundles**:

  1. CA Bundle           — for the Accounts Team
  2. Franchise Owner Bundle — for the Franchise Owner
  3. Franchisor Bundle   — for the Founder / Director / Super Admin

Every numeric figure in every bundle comes from
`utils/financial_engine.compute_franchise_payout` — the single source of
truth. This guarantees the same payable shown on the dashboard equals the
payable inside the PDF equals the payable inside the Excel sheet.
"""
from __future__ import annotations
import io
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak,
)

from .entity import entity_for_country

# ----------------------------------------------------------------------
# Shared style helpers
# ----------------------------------------------------------------------
_STYLES = getSampleStyleSheet()
_TITLE = ParagraphStyle(
    "BundleTitle", parent=_STYLES["Heading1"],
    fontSize=18, alignment=TA_CENTER, spaceAfter=4, textColor=colors.HexColor("#1a1a1a")
)
_SUBTITLE = ParagraphStyle(
    "BundleSubtitle", parent=_STYLES["Normal"],
    fontSize=10, alignment=TA_CENTER, textColor=colors.gray, spaceAfter=10,
)
_H2 = ParagraphStyle(
    "BundleH2", parent=_STYLES["Heading2"],
    fontSize=13, spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#0c4a6e")
)
_H3 = ParagraphStyle(
    "BundleH3", parent=_STYLES["Heading3"],
    fontSize=11, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#374151")
)
_BODY = ParagraphStyle(
    "BundleBody", parent=_STYLES["Normal"],
    fontSize=9, textColor=colors.HexColor("#1f2937"), leading=12,
)

_BANNER_TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0c4a6e")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 9),
    ("ALIGN", (0, 0), (-1, 0), "LEFT"),
    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("FONTSIZE", (0, 1), (-1, -1), 9),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
])


def _fmt_money(val: Any, currency: str = "Rs.") -> str:
    try:
        return f"{currency} {float(val or 0):,.2f}"
    except (TypeError, ValueError):
        return f"{currency} 0.00"


def _kv_table(rows: List[List[str]], col_widths: Optional[List[float]] = None) -> Table:
    t = Table(rows, colWidths=col_widths or [70 * mm, 70 * mm])
    t.setStyle(_BANNER_TABLE_STYLE)
    return t


def _header(title: str, ctx: Dict[str, Any]) -> List[Any]:
    """Standard header block used by every bundle PDF."""
    legal_entity = entity_for_country(ctx.get("country"))
    return [
        Paragraph(title, _TITLE),
        Paragraph(
            f"{legal_entity} · "
            f"{ctx.get('period_label') or ctx.get('period', '')} · "
            f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')}",
            _SUBTITLE,
        ),
        Spacer(1, 6),
    ]


def _executive_summary(ctx: Dict[str, Any]) -> List[Any]:
    """Common Executive Summary block — same shape across all 3 bundles
    so readers see consistent figures regardless of persona.

    Strictly model-aware: only the active payout model's base is shown
    in the summary table. Both bases are still preserved in the manifest
    for auditors who need to compare alternatives.
    """
    engine = ctx.get("engine", {}) or {}
    fin = ctx.get("financial_summary", {}) or {}
    payout = ctx.get("payout", {}) or {}
    currency = ctx.get("currency", "Rs.")
    model = (engine.get("payout_model") or "revenue_share").lower()
    rows = [
        ["Metric", "Value"],
        ["Total Sales", _fmt_money(fin.get("total_sales"), currency)],
        ["GST on Sales", _fmt_money(fin.get("sales_gst"), currency)],
        ["Total Commissions", _fmt_money(fin.get("total_commissions"), currency)],
    ]
    if model == "profit_share":
        rows.append(["Total Expenses", _fmt_money(fin.get("total_expenses"), currency)])
        rows.append(["Profit Share Base", _fmt_money(engine.get("profit_share_base"), currency)])
    else:
        rows.append(["Revenue Share Base", _fmt_money(engine.get("revenue_share_base"), currency)])
    rows.extend([
        ["Payout Model", str(engine.get("payout_model", "—")).replace("_", " ").title()],
        [f"Owner {('Profit Share' if model == 'profit_share' else 'Revenue Share')} ({engine.get('owner_pct', 0):g}%)", _fmt_money(engine.get("owner_share"), currency)],
        [f"Company {('Profit Share' if model == 'profit_share' else 'Revenue Share')} ({engine.get('company_pct', 0):g}%)", _fmt_money(engine.get("company_share"), currency)],
        ["Final Payable", _fmt_money(payout.get("amount"), currency)],
        ["Payable Reason", str(payout.get("reason", "—"))[:80]],
    ])
    return [
        Paragraph("Executive Summary", _H2),
        _kv_table(rows),
        Spacer(1, 10),
    ]


def _payout_block(ctx: Dict[str, Any]) -> List[Any]:
    """Revenue / Profit Share calculation table — driven by engine.

    Strictly respects `engine.payout_model`: when the franchise is on
    Revenue Share we never surface Profit Share numbers (and vice-versa).
    The non-active base is still available via the manifest for auditors.
    """
    engine = ctx.get("engine", {}) or {}
    currency = ctx.get("currency", "Rs.")
    heading = engine.get("section_heading") or "Share Calculation"
    base_label = engine.get("base_label") or "Base"
    # Engine returns the selected base under `base`; legacy code shipped
    # with `selected_base` which always read as 0. Honour both for safety.
    base_value = engine.get("base", engine.get("selected_base", 0))
    _model = (engine.get("payout_model") or "revenue_share").lower()
    _share_word = "Profit Share" if _model == "profit_share" else "Revenue Share"
    _company_label = engine.get("company_entity_label") or "Company Share"
    # company_entity_label from the engine ends with the model phrase already
    # (e.g. "Manaswini Foods Pvt Ltd Revenue Share"). Legacy callers still
    # emit "<Entity> Share" — append the model word if missing so PDFs
    # never read "<Entity> Share" alone.
    if _share_word.lower() not in _company_label.lower():
        if _company_label.lower().endswith(" share"):
            _company_label = f"{_company_label[:-len(' Share')]} {_share_word}"
        else:
            _company_label = f"{_company_label} ({_share_word})"
    rows = [
        ["Description", "Percentage", "Amount"],
        [base_label, "", _fmt_money(base_value, currency)],
        [f"Franchise Owner {_share_word}", f"{engine.get('owner_pct', 0):g}%", _fmt_money(engine.get("owner_share"), currency)],
        [_company_label, f"{engine.get('company_pct', 0):g}%", _fmt_money(engine.get("company_share"), currency)],
    ]
    t = Table(rows, colWidths=[70 * mm, 40 * mm, 50 * mm])
    t.setStyle(_BANNER_TABLE_STYLE)
    return [Paragraph(heading.title(), _H2), t, Spacer(1, 10)]


def _wc_block(ctx: Dict[str, Any]) -> List[Any]:
    wc = ctx.get("working_capital", {}) or {}
    currency = ctx.get("currency", "Rs.")
    rows = [
        ["Metric", "Value"],
        ["Opening WC", _fmt_money(wc.get("opening_wc"), currency)],
        ["Current WC", _fmt_money(wc.get("current_wc"), currency)],
        ["WC Recovery", _fmt_money(wc.get("recovery_amount"), currency)],
        ["Protection Status", "Active" if wc.get("protection_mode") else "Normal"],
    ]
    return [Paragraph("Working Capital Status", _H2), _kv_table(rows), Spacer(1, 10)]


def _compliance_block(ctx: Dict[str, Any]) -> List[Any]:
    gst = ctx.get("gst", {}) or {}
    fin = ctx.get("financial_summary", {}) or {}
    currency = ctx.get("currency", "Rs.")
    rows = [
        ["Metric", "Value"],
        ["GST Collected (this period)", _fmt_money(fin.get("sales_gst"), currency)],
        ["GST Paid (estimated input credit)", _fmt_money(gst.get("paid", 0), currency)],
        ["GST Outstanding", _fmt_money(gst.get("outstanding", fin.get("sales_gst", 0)), currency)],
    ]
    return [Paragraph("Compliance Snapshot", _H2), _kv_table(rows), Spacer(1, 10)]


def _settlement_block(ctx: Dict[str, Any]) -> List[Any]:
    payout = ctx.get("payout", {}) or {}
    currency = ctx.get("currency", "Rs.")
    rows = [
        ["Metric", "Value"],
        ["Payable", _fmt_money(payout.get("amount"), currency)],
        ["Paid (to date)", _fmt_money(payout.get("paid_amount"), currency)],
        ["Pending", _fmt_money(payout.get("pending_amount"), currency)],
        ["Release Status", str(payout.get("release_status", "Eligible")).title()],
        ["Type", str(payout.get("type", "—")).replace("_", " ").title()],
    ]
    return [Paragraph("Settlement Summary", _H2), _kv_table(rows), Spacer(1, 10)]


def _build_pdf(title: str, sections: List[Any]) -> bytes:
    """Assemble a single ReportLab PDF from a list of Flowable sections."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=title,
    )
    doc.build(sections)
    return buf.getvalue()


# ----------------------------------------------------------------------
# Public API — three bundle builders
# ----------------------------------------------------------------------
def build_ca_bundle_pdf(ctx: Dict[str, Any]) -> bytes:
    """CA Bundle — Accounts Team. Heavy on compliance, cash & banking."""
    title = f"CA Bundle — {ctx.get('center', 'All Centers')} — {ctx.get('period_label') or ctx.get('period', '')}"
    sections: List[Any] = []
    sections += _header("CA Bundle", ctx)
    sections += _executive_summary(ctx)
    sections.append(PageBreak())
    sections += _payout_block(ctx)
    sections += _wc_block(ctx)
    sections += _compliance_block(ctx)
    return _build_pdf(title, sections)


def build_franchise_owner_bundle_pdf(ctx: Dict[str, Any]) -> bytes:
    """Franchise Owner Bundle — settlement-centric."""
    title = f"Franchise Owner Bundle — {ctx.get('center', 'All Centers')} — {ctx.get('period_label') or ctx.get('period', '')}"
    sections: List[Any] = []
    sections += _header("Franchise Owner Bundle", ctx)
    sections += _executive_summary(ctx)
    sections.append(PageBreak())
    sections += _payout_block(ctx)
    sections += _settlement_block(ctx)
    sections += _wc_block(ctx)
    return _build_pdf(title, sections)


def build_franchisor_bundle_pdf(ctx: Dict[str, Any]) -> bytes:
    """Franchisor Bundle — executive overview."""
    title = f"Franchisor Bundle — {ctx.get('center', 'All Centers')} — {ctx.get('period_label') or ctx.get('period', '')}"
    sections: List[Any] = []
    sections += _header("Franchisor Bundle", ctx)
    sections += _executive_summary(ctx)
    sections.append(PageBreak())
    sections += _payout_block(ctx)
    sections += _wc_block(ctx)
    sections += _settlement_block(ctx)
    sections += _compliance_block(ctx)
    return _build_pdf(title, sections)


def build_bundle_zip(bundle_kind: str, ctx: Dict[str, Any]) -> bytes:
    """Bundle the cover-sheet PDF + a manifest into a single .zip download.

    NOTE: For "ca" and "franchisor" bundles, callers should use
    `routes/bundles.py:_build_rich_bundle_zip` which aggregates ALL
    Financial / Settlement / Reconciliation / Compliance reports — PDFs +
    Excels — into one downloadable ZIP. This basic builder remains for
    backward compatibility with the simpler "owner" bundle and tests.

    The manifest is a small text file listing the contents + the engine
    snapshot used to compute every number, so auditors can re-derive
    figures without opening the PDF.
    """
    if bundle_kind == "ca":
        pdf_bytes = build_ca_bundle_pdf(ctx)
    elif bundle_kind in ("owner", "franchise_owner"):
        pdf_bytes = build_franchise_owner_bundle_pdf(ctx)
    elif bundle_kind == "franchisor":
        pdf_bytes = build_franchisor_bundle_pdf(ctx)
    else:
        raise ValueError(f"Unknown bundle kind: {bundle_kind!r}")

    safe_center = (ctx.get("center") or "ALL").upper()
    safe_period = (ctx.get("period") or datetime.now().strftime("%Y-%m"))
    base_name = f"{bundle_kind.upper()}_{safe_center}_{safe_period}"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base_name}.pdf", pdf_bytes)
        # Engine-snapshot manifest for audit trail.
        engine = ctx.get("engine", {}) or {}
        manifest = (
            f"Bundle: {bundle_kind}\n"
            f"Center: {ctx.get('center', 'ALL')}\n"
            f"Period: {ctx.get('period', '')}\n"
            f"Country: {ctx.get('country', 'India')}\n"
            f"Payout Model: {engine.get('payout_model', '—')}\n"
            f"Revenue Share Base: {engine.get('revenue_share_base', 0)}\n"
            f"Profit Share Base:  {engine.get('profit_share_base', 0)}\n"
            f"Selected Base:      {engine.get('base', engine.get('selected_base', 0))}\n"
            f"Owner %:            {engine.get('owner_pct', 0)}\n"
            f"Owner Share:        {engine.get('owner_share', 0)}\n"
            f"Company %:          {engine.get('company_pct', 0)}\n"
            f"Company Share:      {engine.get('company_share', 0)}\n"
            f"Company Entity:     {engine.get('company_entity_label', '—')}\n"
            f"\nGenerated {datetime.now().isoformat()}\n"
            f"Source-of-truth: backend/utils/financial_engine.py\n"
        )
        zf.writestr(f"{base_name}_manifest.txt", manifest)
    return buf.getvalue()


__all__ = [
    "build_ca_bundle_pdf",
    "build_franchise_owner_bundle_pdf",
    "build_franchisor_bundle_pdf",
    "build_bundle_zip",
]
