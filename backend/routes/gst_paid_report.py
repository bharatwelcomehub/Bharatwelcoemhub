"""GST Paid Report — vendor / center / category summary of GST printed on bills.

Endpoints (all under /api/gst-paid-report):
  - POST /summary  → JSON for the report screen
  - POST /excel    → downloadable XLSX
  - POST /pdf      → downloadable PDF
  - POST /zip      → ZIP bundle (Excel + bill attachments)

Reads from the `expenses` collection. `gst_paid` defaults to 0 when missing,
so historical entries cleanly show 0 with no migration needed.
"""

from __future__ import annotations

import csv
import io
import logging
import os
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server import db  # type: ignore
from routes.center_accounts import check_access, _is_staff
from routes.financial_insights import _fy_to_months, _months_between
from routes.center_health import _month_label

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/gst-paid-report", tags=["gst-paid-report"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class GstReportRequest(BaseModel):
    token: str
    centers: List[str] = []           # empty = all accessible
    period_type: str = "month"        # 'month' | 'month_range' | 'fy' | 'custom'
    month: Optional[str] = None
    from_month: Optional[str] = None
    to_month: Optional[str] = None
    fy: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    vendor: Optional[str] = None
    category: Optional[str] = None
    currency: Optional[str] = None    # 'INR' | 'AUD' | None for all
    min_gst: Optional[float] = None   # show only rows where gst_paid >= this


# ---------------------------------------------------------------------------
# Access + scope helpers
# ---------------------------------------------------------------------------

async def _resolve_accessible_centers(session: dict, requested: List[str]) -> List[str]:
    """Return centers the requester can view, optionally filtered to ``requested``."""
    accessible: List[str] = []
    if _is_staff(session):
        cur = db.centers.find({}, {"_id": 0, "code": 1})
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
        cur = db.centers.find(q, {"_id": 0, "code": 1})
    async for c in cur:
        if c.get("code") and c["code"] != "PB-MGT":
            accessible.append(c["code"])
    if requested:
        accessible = [c for c in accessible if c in requested]
    return accessible


def _resolve_date_filter(req: GstReportRequest) -> Dict[str, str]:
    """Build a Mongo regex on date for the chosen period."""
    pt = req.period_type or "month"
    if pt == "month":
        if not req.month:
            raise HTTPException(400, "month is required")
        return {"$regex": f"^{req.month}"}
    if pt == "month_range":
        if not (req.from_month and req.to_month):
            raise HTTPException(400, "from_month and to_month are required")
        months = _months_between(req.from_month, req.to_month)
        return {"$in": [m for m in months for _ in (0,)]}
    if pt == "fy":
        if not req.fy:
            raise HTTPException(400, "fy is required")
        months = _fy_to_months(req.fy)
        # date is YYYY-MM-DD, so build $gte/$lte across FY span
        return {"$gte": f"{months[0]}-01", "$lte": f"{months[-1]}-31"}
    if pt == "custom":
        if not (req.from_date and req.to_date):
            raise HTTPException(400, "from_date and to_date are required")
        return {"$gte": req.from_date, "$lte": req.to_date}
    raise HTTPException(400, f"Unknown period_type {pt}")


def _period_label(req: GstReportRequest) -> str:
    pt = req.period_type or "month"
    if pt == "month":
        return _month_label(req.month)
    if pt == "month_range":
        return f"{_month_label(req.from_month)} – {_month_label(req.to_month)}"
    if pt == "fy":
        return req.fy if (req.fy or "").startswith("FY") else f"FY {req.fy}"
    if pt == "custom":
        return f"{req.from_date} → {req.to_date}"
    return ""


async def _fetch_rows(req: GstReportRequest, centers: List[str]) -> List[dict]:
    if not centers:
        return []
    date_filter = _resolve_date_filter(req)
    q: Dict[str, Any] = {"center": {"$in": centers}}
    if isinstance(date_filter, dict) and "$in" in date_filter:
        # build month-prefix OR list
        regs = [{"date": {"$regex": f"^{m}"}} for m in date_filter["$in"]]
        q["$or"] = regs
    else:
        q["date"] = date_filter
    if req.vendor:
        q["vendor_name"] = {"$regex": req.vendor, "$options": "i"}
    if req.category:
        q["expense_type"] = {"$regex": req.category, "$options": "i"}
    if req.min_gst is not None and req.min_gst > 0:
        q["gst_paid"] = {"$gte": req.min_gst}

    cur = db.expenses.find(q, {"_id": 0}).sort([("date", -1), ("center", 1)])
    rows = await cur.to_list(20000)

    # Country / currency tagging via center cache
    centers_map = {}
    async for c in db.centers.find({"code": {"$in": list({r.get("center") for r in rows})}}, {"_id": 0, "code": 1, "name": 1, "country": 1, "is_india_center": 1}):
        centers_map[c["code"]] = c

    cleaned: List[dict] = []
    for r in rows:
        c_meta = centers_map.get(r.get("center"), {})
        country = c_meta.get("country") or ("India" if c_meta.get("is_india_center", True) else "Australia")
        currency = "AUD" if country == "Australia" else "INR"
        if req.currency and req.currency.upper() != currency:
            continue
        base = float(r.get("amount") or 0)
        gst_paid = float(r.get("gst_paid") or 0)
        cleaned.append({
            "date": r.get("date") or "",
            "center": r.get("center") or "",
            "center_name": c_meta.get("name") or r.get("center") or "",
            "country": country,
            "currency": currency,
            "vendor_name": r.get("vendor_name") or "",
            "expense_category": r.get("expense_type") or "",
            "description": r.get("description") or "",
            "base_amount": round(base, 2),
            "gst_paid": round(gst_paid, 2),
            "total_expense": round(base + gst_paid, 2),
            "payment_mode": r.get("payment_mode") or "",
            "bill_attachment_url": r.get("attachment_url") or r.get("bill_url") or "",
            "entered_by": r.get("created_by") or r.get("uploaded_by") or "",
            "approved_by": r.get("approved_by") or "",
            "expense_id": r.get("expense_id") or "",
        })
    return cleaned


def _aggregate(rows: List[dict]) -> Dict[str, Any]:
    by_vendor: Dict[str, Dict[str, float]] = {}
    by_center: Dict[str, Dict[str, float]] = {}
    by_category: Dict[str, Dict[str, float]] = {}
    totals = {"base": 0.0, "gst_paid": 0.0, "total": 0.0}
    for r in rows:
        totals["base"] += r["base_amount"]
        totals["gst_paid"] += r["gst_paid"]
        totals["total"] += r["total_expense"]

        v = r["vendor_name"] or "(Unspecified)"
        d = by_vendor.setdefault(v, {"base": 0, "gst_paid": 0, "total": 0, "rows": 0})
        d["base"] += r["base_amount"]; d["gst_paid"] += r["gst_paid"]
        d["total"] += r["total_expense"]; d["rows"] += 1

        c = r["center"]
        d = by_center.setdefault(c, {"base": 0, "gst_paid": 0, "total": 0, "rows": 0})
        d["base"] += r["base_amount"]; d["gst_paid"] += r["gst_paid"]
        d["total"] += r["total_expense"]; d["rows"] += 1

        cat = r["expense_category"] or "(Uncategorised)"
        d = by_category.setdefault(cat, {"base": 0, "gst_paid": 0, "total": 0, "rows": 0})
        d["base"] += r["base_amount"]; d["gst_paid"] += r["gst_paid"]
        d["total"] += r["total_expense"]; d["rows"] += 1

    def _round(d):
        return {k: round(v, 2) if isinstance(v, float) else v for k, v in d.items()}
    return {
        "totals": _round(totals),
        "by_vendor": {k: _round(v) for k, v in by_vendor.items()},
        "by_center": {k: _round(v) for k, v in by_center.items()},
        "by_category": {k: _round(v) for k, v in by_category.items()},
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/summary")
async def gst_summary(req: GstReportRequest):
    session = await check_access(req.token)
    centers = await _resolve_accessible_centers(session, req.centers)
    if not centers:
        return {
            "period_label": _period_label(req),
            "centers": [],
            "rows": [],
            "aggregations": _aggregate([]),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    rows = await _fetch_rows(req, centers)
    return {
        "period_label": _period_label(req),
        "centers": centers,
        "rows": rows,
        "aggregations": _aggregate(rows),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_excel(payload: Dict[str, Any]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = Workbook()
    bold = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="8B0000")
    money = '#,##0.00'

    ws = wb.active
    ws.title = "Rows"
    headers = ["Date", "Center", "Vendor", "Category", "Description",
               "Base Amount", "GST Paid", "Total Expense",
               "Payment Mode", "Currency", "Entered By", "Approved By",
               "Bill Attachment"]
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        ws.cell(row=1, column=c).font = bold
        ws.cell(row=1, column=c).fill = header_fill

    for r in payload["rows"]:
        ws.append([
            r["date"], f"{r['center']} ({r['center_name']})", r["vendor_name"],
            r["expense_category"], r["description"],
            r["base_amount"], r["gst_paid"], r["total_expense"],
            r["payment_mode"], r["currency"], r["entered_by"], r["approved_by"],
            r["bill_attachment_url"],
        ])
    for col in ("F", "G", "H"):
        for cell in ws[col][1:]:
            cell.number_format = money
    for col, w in (("A", 12), ("B", 24), ("C", 24), ("D", 22), ("E", 30),
                   ("F", 14), ("G", 14), ("H", 14), ("I", 14), ("J", 10),
                   ("K", 18), ("L", 18), ("M", 40)):
        ws.column_dimensions[col].width = w

    # Vendor summary
    ws2 = wb.create_sheet("By Vendor")
    ws2.append(["Vendor", "Rows", "Base Amount", "GST Paid", "Total Expense"])
    for c in range(1, 6):
        ws2.cell(row=1, column=c).font = bold
        ws2.cell(row=1, column=c).fill = header_fill
    for vendor, d in sorted(payload["aggregations"]["by_vendor"].items(), key=lambda kv: -kv[1]["gst_paid"]):
        ws2.append([vendor, d["rows"], d["base"], d["gst_paid"], d["total"]])
    for col in ("C", "D", "E"):
        for cell in ws2[col][1:]:
            cell.number_format = money

    # Center summary
    ws3 = wb.create_sheet("By Center")
    ws3.append(["Center", "Rows", "Base Amount", "GST Paid", "Total Expense"])
    for c in range(1, 6):
        ws3.cell(row=1, column=c).font = bold
        ws3.cell(row=1, column=c).fill = header_fill
    for center, d in sorted(payload["aggregations"]["by_center"].items(), key=lambda kv: -kv[1]["gst_paid"]):
        ws3.append([center, d["rows"], d["base"], d["gst_paid"], d["total"]])
    for col in ("C", "D", "E"):
        for cell in ws3[col][1:]:
            cell.number_format = money

    # Category summary
    ws4 = wb.create_sheet("By Category")
    ws4.append(["Category", "Rows", "Base Amount", "GST Paid", "Total Expense"])
    for c in range(1, 6):
        ws4.cell(row=1, column=c).font = bold
        ws4.cell(row=1, column=c).fill = header_fill
    for cat, d in sorted(payload["aggregations"]["by_category"].items(), key=lambda kv: -kv[1]["gst_paid"]):
        ws4.append([cat, d["rows"], d["base"], d["gst_paid"], d["total"]])
    for col in ("C", "D", "E"):
        for cell in ws4[col][1:]:
            cell.number_format = money

    # Totals page
    ws5 = wb.create_sheet("Totals")
    ws5.append(["Metric", "Value"])
    ws5["A1"].font = bold; ws5["A1"].fill = header_fill
    ws5["B1"].font = bold; ws5["B1"].fill = header_fill
    t = payload["aggregations"]["totals"]
    ws5.append(["Period", payload["period_label"]])
    ws5.append(["Centers", ", ".join(payload["centers"])])
    ws5.append(["Rows", len(payload["rows"])])
    ws5.append(["Base Amount", t["base"]])
    ws5.append(["GST Paid", t["gst_paid"]])
    ws5.append(["Total Expense", t["total"]])
    for r in (5, 6, 7):
        ws5.cell(row=r, column=2).number_format = money
    ws5.column_dimensions["A"].width = 22
    ws5.column_dimensions["B"].width = 26

    buf = io.BytesIO(); wb.save(buf)
    return buf.getvalue()


@router.post("/excel")
async def gst_excel(req: GstReportRequest):
    payload = await gst_summary(req)
    data = _build_excel(payload)
    fname = f"gst_paid_report_{req.period_type}.xlsx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


def _build_pdf(payload: Dict[str, Any]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=0.4 * inch, rightMargin=0.4 * inch, topMargin=0.5 * inch, bottomMargin=0.5 * inch, title="GST Paid Report")
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=16, textColor=colors.HexColor("#5C0000"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11, textColor=colors.HexColor("#5C0000"), spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9, leading=12)
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=7.5, leading=10)

    story = []
    story.append(Paragraph("GST Paid Report", h1))
    story.append(Paragraph(f"Period: <b>{payload['period_label']}</b> · Centers: {', '.join(payload['centers'])}", body))

    t = payload["aggregations"]["totals"]
    story.append(Paragraph("Summary", h2))
    summary = Table([
        ["Rows", len(payload["rows"])],
        ["Base Amount", f"{t['base']:,.2f}"],
        ["GST Paid", f"{t['gst_paid']:,.2f}"],
        ["Total Expense", f"{t['total']:,.2f}"],
    ], colWidths=[2 * inch, 2 * inch])
    summary.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 10),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fef3c7")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
    ]))
    story.append(summary)

    story.append(Paragraph("Vendor-wise summary", h2))
    rows_v = [["Vendor", "Rows", "Base", "GST Paid", "Total"]]
    for v, d in sorted(payload["aggregations"]["by_vendor"].items(), key=lambda kv: -kv[1]["gst_paid"])[:30]:
        rows_v.append([v, str(d["rows"]), f"{d['base']:,.0f}", f"{d['gst_paid']:,.0f}", f"{d['total']:,.0f}"])
    tv = Table(rows_v, repeatRows=1, colWidths=[3.2 * inch, 0.6 * inch, 1.4 * inch, 1.4 * inch, 1.4 * inch])
    tv.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fde68a")),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
    ]))
    story.append(tv)

    story.append(Paragraph("Detail (first 200 rows)", h2))
    detail = [["Date", "Center", "Vendor", "Category", "Base", "GST", "Total"]]
    for r in payload["rows"][:200]:
        detail.append([
            r["date"], r["center"], (r["vendor_name"] or "")[:24],
            (r["expense_category"] or "")[:18],
            f"{r['base_amount']:,.0f}",
            f"{r['gst_paid']:,.0f}",
            f"{r['total_expense']:,.0f}",
        ])
    td = Table(detail, repeatRows=1, colWidths=[0.9 * inch, 1 * inch, 2.4 * inch, 1.7 * inch, 1.2 * inch, 1.2 * inch, 1.3 * inch])
    td.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fde68a")),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8.5),
        ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
    ]))
    story.append(td)
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"Generated by Purnabramha IntraPB · {payload['generated_at'][:19]} UTC · GST Paid values are entered directly from the printed bill — no calculation is applied.",
        small,
    ))
    doc.build(story)
    return buf.getvalue()


@router.post("/pdf")
async def gst_pdf(req: GstReportRequest):
    payload = await gst_summary(req)
    data = _build_pdf(payload)
    fname = f"gst_paid_report_{req.period_type}.pdf"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post("/zip")
async def gst_zip(req: GstReportRequest):
    """Build a ZIP containing the Excel + every available bill attachment.

    Attachments are downloaded best-effort from their URL; failures are listed
    in an `index.csv` so the receiver knows which bills are missing.
    """
    import httpx

    payload = await gst_summary(req)
    excel = _build_excel(payload)
    pdf = _build_pdf(payload)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("GST_Paid_Report.xlsx", excel)
        zf.writestr("GST_Paid_Report.pdf", pdf)

        index_rows = [["row_index", "date", "center", "vendor", "gst_paid", "attachment_url", "saved_as", "status"]]

        async with httpx.AsyncClient(timeout=15) as client:
            for idx, r in enumerate(payload["rows"]):
                url = r.get("bill_attachment_url") or ""
                saved_as = ""
                status = "no_url"
                if url:
                    try:
                        resp = await client.get(url)
                        if resp.status_code == 200:
                            ext = ""
                            ct = (resp.headers.get("content-type") or "").lower()
                            if "pdf" in ct: ext = ".pdf"
                            elif "jpeg" in ct or "jpg" in ct: ext = ".jpg"
                            elif "png" in ct: ext = ".png"
                            elif "/" in ct:
                                ext = "." + ct.split("/")[-1].split(";")[0][:6]
                            safe_vendor = "".join(ch for ch in (r.get("vendor_name") or "vendor") if ch.isalnum() or ch in (" ", "-", "_")).strip()[:30] or "vendor"
                            saved_as = f"bills/{r['date']}_{r['center']}_{safe_vendor}_{idx}{ext}"
                            zf.writestr(saved_as, resp.content)
                            status = "ok"
                        else:
                            status = f"http_{resp.status_code}"
                    except Exception as e:
                        status = f"error:{str(e)[:60]}"
                index_rows.append([idx, r["date"], r["center"], r.get("vendor_name", ""), r["gst_paid"], url, saved_as, status])

        # Append index CSV
        idx_buf = io.StringIO()
        w = csv.writer(idx_buf)
        w.writerows(index_rows)
        zf.writestr("index.csv", idx_buf.getvalue())

    fname = f"gst_paid_report_{req.period_type}.zip"
    return StreamingResponse(
        io.BytesIO(buf.getvalue()),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
