"""Routes for the "Coming Soon" reports we shipped (Feb-2026):

  POST /api/extra-reports/profit-loss
  POST /api/extra-reports/mg-summary
  POST /api/extra-reports/payout-summary
  POST /api/extra-reports/phonepe-recon
  POST /api/extra-reports/gst-paid
  POST /api/extra-reports/missing-bills
  POST /api/extra-reports/expense-attachments-zip

All endpoints return either a PDF or ZIP file ready to download. Each reuses
existing data sources (account summary + db queries) so numbers stay
consistent with Center Accounts / Bundles.
"""
from __future__ import annotations
import io
import logging
import zipfile
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from utils.extra_reports_pdf import (
    build_profit_loss_pdf,
    build_mg_summary_pdf,
    build_payout_summary_pdf,
    build_phonepe_recon_pdf,
    build_gst_paid_pdf,
    build_missing_bills_pdf,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/extra-reports", tags=["Extra Reports"])

_db = None
_verify_token = None
_verify_token_async = None


def set_db(db):
    global _db
    _db = db


def set_verify_token(fn):
    global _verify_token
    _verify_token = fn


def set_verify_token_async(fn):
    global _verify_token_async
    _verify_token_async = fn


class _ReportReq(BaseModel):
    token: str
    center: str
    month: str


async def _auth(token: str) -> None:
    sess = None
    if _verify_token_async:
        sess = await _verify_token_async(token)
    if not sess and _verify_token:
        sess = _verify_token(token)
    if not sess:
        raise HTTPException(401, "Invalid or expired token")


async def _summary_for(token: str, center: str, month: str) -> dict:
    """Fetch the canonical account summary (lazy import to avoid circular deps)."""
    from routes.center_accounts import (
        get_center_account_summary,
        AccountPeriodRequest,
    )
    resp = await get_center_account_summary(
        AccountPeriodRequest(token=token, center=center, month=month)
    )
    return resp.get("summary") or {}


def _mk_month_range(month: str):
    year, m = map(int, month.split("-"))
    start = f"{year}-{m:02d}-01"
    from calendar import monthrange
    last = monthrange(year, m)[1]
    end = f"{year}-{m:02d}-{last:02d}"
    return start, end


def _pdf_response(blob: bytes, filename: str) -> Response:
    return Response(
        content=blob,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── 1. Profit & Loss ───────────────────────────────────────────────────────
@router.post("/profit-loss")
async def profit_loss(req: _ReportReq):
    await _auth(req.token)
    summary = await _summary_for(req.token, req.center, req.month)
    blob = build_profit_loss_pdf(summary)
    return _pdf_response(blob, f"PnL_{req.center}_{req.month}.pdf")


# ── 2. MG Summary ──────────────────────────────────────────────────────────
@router.post("/mg-summary")
async def mg_summary(req: _ReportReq):
    await _auth(req.token)
    # Reuse payout_summary endpoint logic for monthly data
    from routes.center_accounts import get_payout_summary
    try:
        payout = await get_payout_summary({
            "token": req.token, "center": req.center,
            "from_month": req.month, "to_month": req.month,
        })
    except Exception as ex:
        logger.warning(f"MG Summary: payout fetch failed: {ex}")
        payout = {}
    franchise = (payout.get("franchise") or {}) if isinstance(payout, dict) else {}
    ctx = {
        "center": req.center,
        "country": payout.get("country") if isinstance(payout, dict) else None,
        "month": req.month,
        "period_range": req.month,
        "period_label": req.month,
        "monthly_data": payout.get("monthly_data") if isinstance(payout, dict) else [],
        "totals": payout.get("totals") if isinstance(payout, dict) else {},
    }
    # ctx keys must match builder's expected payout dict
    blob = build_mg_summary_pdf(ctx, franchise)
    return _pdf_response(blob, f"MGSummary_{req.center}_{req.month}.pdf")


# ── 3. Payout Summary ──────────────────────────────────────────────────────
@router.post("/payout-summary")
async def payout_summary_pdf(req: _ReportReq):
    await _auth(req.token)
    from routes.center_accounts import get_payout_summary
    try:
        payout = await get_payout_summary({
            "token": req.token, "center": req.center,
            "from_month": req.month, "to_month": req.month,
        })
    except Exception as ex:
        logger.warning(f"Payout Summary: payout fetch failed: {ex}")
        payout = {}
    ctx = {
        "center": req.center,
        "country": payout.get("country") if isinstance(payout, dict) else None,
        "month": req.month,
        "period_range": req.month,
        "period_label": req.month,
        "monthly_data": payout.get("monthly_data") if isinstance(payout, dict) else [],
        "totals": payout.get("totals") if isinstance(payout, dict) else {},
    }
    blob = build_payout_summary_pdf(ctx)
    return _pdf_response(blob, f"PayoutSummary_{req.center}_{req.month}.pdf")


# ── 4. PhonePe Reconciliation ──────────────────────────────────────────────
@router.post("/phonepe-recon")
async def phonepe_recon(req: _ReportReq):
    await _auth(req.token)
    start, end = _mk_month_range(req.month)
    sales_rows = await _db.daily_sales.find(
        {"center": req.center, "date": {"$gte": start, "$lte": end}},
        {"_id": 0},
    ).sort("date", 1).to_list(200)
    center_doc = await _db.centers.find_one({"code": req.center}) or {}
    ctx = {
        "center": req.center,
        "country": center_doc.get("country") or "India",
        "period": req.month,
        "period_label": datetime.strptime(req.month + "-01", "%Y-%m-%d").strftime("%B %Y"),
    }
    blob = build_phonepe_recon_pdf(ctx, sales_rows)
    return _pdf_response(blob, f"PhonePeRecon_{req.center}_{req.month}.pdf")


# ── 5. GST Paid ────────────────────────────────────────────────────────────
@router.post("/gst-paid")
async def gst_paid(req: _ReportReq):
    await _auth(req.token)
    start, end = _mk_month_range(req.month)
    # GST collected (this month) = sum of compute_gst_from_rows on eligible base
    from utils.gst import compute_gst_from_rows
    sales_rows = await _db.daily_sales.find(
        {"center": req.center, "date": {"$gte": start, "$lte": end}}, {"_id": 0},
    ).to_list(500)
    center_doc = await _db.centers.find_one({"code": req.center}) or {}
    country = center_doc.get("country") or "India"
    gst_info = compute_gst_from_rows(sales_rows, country=country, center=req.center)
    gst_collected = float(gst_info.get("gst_amount") or 0)

    # GST Paid this month = expenses with type == "GST PAYMENT"
    gst_payments_rows = await _db.expenses.find(
        {
            "center": req.center,
            "date": {"$gte": start, "$lte": end},
            "expense_type": {"$regex": "^GST PAYMENT$", "$options": "i"},
        },
        {"_id": 0},
    ).sort("date", 1).to_list(50)

    payments = [
        {
            "month": req.month,
            "description": f"GST collected — eligible base {gst_info.get('eligible_base', 0):,.2f}",
            "gst_collected": gst_collected,
            "gst_paid": 0,
        }
    ]
    for p in gst_payments_rows:
        payments.append({
            "month": p.get("date", ""),
            "description": p.get("description") or "GST PAYMENT",
            "gst_collected": 0,
            "gst_paid": float(p.get("amount") or 0),
        })
    ctx = {"center": req.center, "country": country, "period": req.month}
    blob = build_gst_paid_pdf(ctx, payments)
    return _pdf_response(blob, f"GSTPaid_{req.center}_{req.month}.pdf")


# ── 6. Missing Bills ───────────────────────────────────────────────────────
@router.post("/missing-bills")
async def missing_bills(req: _ReportReq):
    await _auth(req.token)
    start, end = _mk_month_range(req.month)
    expenses = await _db.expenses.find(
        {"center": req.center, "date": {"$gte": start, "$lte": end}}, {"_id": 0},
    ).sort("date", 1).to_list(2000)
    # An expense is "missing bill" if it has no attachment AND amount > threshold
    # (Indian Income-Tax Rule 6F mandates a bill for any expense >= Rs. 50; AU
    #  ATO requires receipts for >= AU$82.50 incl GST. We err on the safer side
    #  and flag everything regardless of amount when no attachment is found.)
    missing = []
    for e in expenses:
        if e.get("has_attachment"):
            continue
        # also check expense_attachments collection by expense_id
        exp_id = e.get("expense_id") or e.get("_id")
        att = None
        if exp_id:
            att = await _db.expense_attachments.find_one(
                {"expense_id": str(exp_id), "is_deleted": {"$ne": True}},
                {"_id": 1},
            )
        if not att:
            missing.append(e)
    center_doc = await _db.centers.find_one({"code": req.center}) or {}
    ctx = {
        "center": req.center,
        "country": center_doc.get("country") or "India",
        "period": req.month,
        "period_label": datetime.strptime(req.month + "-01", "%Y-%m-%d").strftime("%B %Y"),
    }
    blob = build_missing_bills_pdf(ctx, missing)
    return _pdf_response(blob, f"MissingBills_{req.center}_{req.month}.pdf")


# ── 7. Expense Attachments ZIP ─────────────────────────────────────────────
@router.post("/expense-attachments-zip")
async def expense_attachments_zip(req: _ReportReq):
    """Bundles every uploaded bill / invoice for the month into a ZIP."""
    await _auth(req.token)
    start, end = _mk_month_range(req.month)
    blob = await build_expense_attachments_zip(_db, req.center, start, end)
    return Response(
        content=blob,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="Expense_Attachments_{req.center}_{req.month}.zip"',
        },
    )


async def build_expense_attachments_zip(
    db, center: str, start_date: str, end_date: str,
) -> bytes:
    """Construct a ZIP containing every bill/attachment for (center, period).

    Folder structure:
      Center_<center>/
        <YYYY-MM-DD>_<description>_<expense_id>.<ext>
        ...
        _missing_bills.csv      ← expense rows that have no attachment
        _attachments_index.csv  ← every file listed + linked expense info

    Designed for offline auditor consumption (one ZIP = one month of CA-ready
    bill evidence).
    """
    from routes.expense_attachments import get_object

    expenses = await db.expenses.find(
        {"center": center, "date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0},
    ).sort("date", 1).to_list(5000)

    buf = io.BytesIO()
    safe_center = (center or "ALL").replace("-", "_")
    base_folder = f"Center_{safe_center}"

    index_rows = [["Filename", "Date", "Description", "Amount", "Payment Mode", "Expense ID"]]
    missing_rows = [["Date", "Description", "Amount", "Payment Mode", "Expense Type"]]

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for exp in expenses:
            exp_id = exp.get("expense_id") or ""
            date_str = exp.get("date", "")
            desc = (exp.get("description") or "expense").strip()[:40]
            amount = float(exp.get("amount") or 0)
            pmode = exp.get("payment_mode") or ""
            etype = exp.get("expense_type") or ""

            # find attachments either by expense_id or has_attachment flag
            atts = []
            if exp_id:
                atts = await db.expense_attachments.find(
                    {"expense_id": str(exp_id), "is_deleted": {"$ne": True}},
                    {"_id": 0},
                ).to_list(20)

            if not atts:
                missing_rows.append([date_str, desc, amount, pmode, etype])
                continue

            for att in atts:
                try:
                    content, _ = get_object(att.get("storage_path"))
                    ext = att.get("file_type") or "pdf"
                    safe_desc = "".join(c for c in desc if c.isalnum() or c in "._- ")[:30].replace(" ", "_")
                    fname = f"{date_str}_{safe_desc}_{exp_id[:8]}.{ext}"
                    zf.writestr(f"{base_folder}/{fname}", content)
                    index_rows.append([fname, date_str, desc, amount, pmode, exp_id])
                except Exception as ex:
                    logger.warning(f"expense-attachments-zip: failed to add {att.get('attachment_id')}: {ex}")

        # CSV index + missing-bills summary
        import csv as _csv
        _idx = io.StringIO()
        _w = _csv.writer(_idx)
        for row in index_rows:
            _w.writerow(row)
        zf.writestr(f"{base_folder}/_attachments_index.csv", _idx.getvalue())

        _mis = io.StringIO()
        _w2 = _csv.writer(_mis)
        for row in missing_rows:
            _w2.writerow(row)
        zf.writestr(f"{base_folder}/_missing_bills.csv", _mis.getvalue())

        # Manifest
        manifest = (
            f"Expense Attachments Bundle\n"
            f"Center: {center}\n"
            f"Period: {start_date} → {end_date}\n"
            f"Total expense rows: {len(expenses)}\n"
            f"Attachments included: {len(index_rows) - 1}\n"
            f"Missing bills (no attachment): {len(missing_rows) - 1}\n"
            f"\nGenerated {datetime.now().isoformat()}\n"
        )
        zf.writestr(f"{base_folder}/manifest.txt", manifest)

    return buf.getvalue()
