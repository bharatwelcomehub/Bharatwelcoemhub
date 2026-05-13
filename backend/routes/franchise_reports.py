"""Franchise Owner Reports — read-only endpoints for the Franchise Owner Dashboard.

Provides:
  - Sales/Expense Excel generator with flexible date filters
    POST /api/franchise-reports/sales-expense-excel
  - List of raw uploaded files for a month
    POST /api/franchise-reports/raw-files
  - Download a specific raw uploaded file
    POST /api/franchise-reports/raw-file/download

Permissions:
  - Super Admin / Admin / Manager: any center
  - Franchise Owner: ONLY the center(s) their session/franchise gives access to
  - All endpoints are view + download only — no edit/delete.
"""

from datetime import datetime, timedelta, timezone
import os
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from server import db  # type: ignore
from routes.center_accounts import check_access, enforce_owner_visibility
from utils.sales_expense_excel import build_sales_expense_excel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/franchise-reports", tags=["franchise-reports"])


def _month_bounds(month: str) -> tuple[str, str]:
    y, m = month.split("-")
    start = f"{y}-{m}-01"
    end_first = (datetime(int(y), int(m), 28) + timedelta(days=4)).replace(day=1)
    end = (end_first - timedelta(days=1)).strftime("%Y-%m-%d")
    return start, end


class SalesExpenseRequest(BaseModel):
    token: str
    center: str
    mode: str = "month"  # 'month' | 'range' | 'date'
    month: Optional[str] = None        # required for mode='month'
    start_date: Optional[str] = None   # for mode='range' / 'date'
    end_date: Optional[str] = None     # for mode='range'


@router.post("/sales-expense-excel")
async def sales_expense_excel(req: SalesExpenseRequest):
    """Generate a Sales + Expenses Excel for the given period."""
    session = await check_access(req.token)
    center = req.center.upper().strip()

    if req.mode == "month":
        if not req.month:
            raise HTTPException(400, "month is required for mode='month'")
        start, end = _month_bounds(req.month)
        await enforce_owner_visibility(session, center, req.month)
        suffix = req.month
    elif req.mode == "range":
        if not req.start_date or not req.end_date:
            raise HTTPException(400, "start_date and end_date are required for mode='range'")
        start, end = req.start_date, req.end_date
        suffix = f"{start} to {end}"
    elif req.mode == "date":
        if not req.start_date:
            raise HTTPException(400, "start_date is required for mode='date'")
        start = end = req.start_date
        suffix = start
    else:
        raise HTTPException(400, "mode must be 'month', 'range', or 'date'")

    try:
        xlsx_bytes = await build_sales_expense_excel(
            db, center, start, end, title_suffix=suffix
        )
    except Exception as e:
        logger.error(f"sales-expense-excel build failed: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to generate Excel: {e}")

    filename = f"Sales_Expense_{center}_{start}_to_{end}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


class RawFilesRequest(BaseModel):
    token: str
    center: str
    month: str


@router.post("/raw-files")
async def list_raw_files(req: RawFilesRequest):
    """List raw uploaded files (Swiggy/Zomato/Bank Statement, etc.) for the given
    center+month. Used by the Franchise Owner Dashboard → Raw Uploaded Files panel.

    Returns:
        {
          "files": [
            {raw_id, kind, platform, original_filename, size_kb, uploaded_at, uploaded_by},
            ...
          ]
        }
    """
    session = await check_access(req.token)
    await enforce_owner_visibility(session, req.center, req.month)

    rows = await db.raw_uploads.find(
        {"center": req.center.upper(), "month": req.month},
        {"_id": 0, "stored_path": 0},
    ).sort("uploaded_at", -1).to_list(200)

    files = []
    for r in rows:
        files.append({
            "raw_id": r.get("raw_id"),
            "kind": r.get("kind"),
            "platform": r.get("platform"),
            "original_filename": r.get("original_filename"),
            "size_kb": round((r.get("size_bytes") or 0) / 1024.0, 1),
            "uploaded_at": r.get("uploaded_at"),
            "uploaded_by": r.get("uploaded_by"),
        })
    return {"files": files, "center": req.center, "month": req.month}


class RawFileDownloadRequest(BaseModel):
    token: str
    raw_id: str


@router.post("/bundle")
async def franchise_owner_bundle(req: RawFilesRequest):
    """Build the complete monthly bundle for the Franchise Owner.

    Mirrors the Accounts Email Pack but INCLUDES the Franchise Owner Ledger PDF
    (which is intentionally excluded from the Accounts email pack to avoid
    duplication, but is wanted in the owner-facing bundle).

    Returns a ZIP with:
      - PIB / GST / Commission / Bank Statement PDFs
      - Sales/Expense Excel (full month)
      - Franchise Owner Ledger PDF
      - Raw uploaded files (Swiggy / Zomato / Bank) when present
    """
    from routes.center_accounts import (
        check_access as _ca_check, enforce_owner_visibility as _ca_enforce,
        generate_email_pack, EmailPackRequest,
    )
    from routes.ledgers import (
        build_franchise_owner_ledger as _bld_owner_led,
        _render_pdf, _owner_ledger_to_table,
    )
    import io as _io
    import zipfile

    session = await _ca_check(req.token)
    await _ca_enforce(session, req.center, req.month)

    # 1) Reuse the accounts email-pack ZIP as the base (already excludes ledger)
    pack_zip_resp = await generate_email_pack(EmailPackRequest(
        token=req.token, center=req.center, month=req.month, format="zip",
    ))
    base_zip_bytes = bytes(pack_zip_resp.body) if hasattr(pack_zip_resp, "body") else None
    if not base_zip_bytes:
        raise HTTPException(500, "Failed to build base bundle")

    # 2) Build Owner Ledger PDF
    owner_pdf_bytes = b""
    try:
        owner_data = await _bld_owner_led(req.center, [req.month])
        sections = [("Franchise Owner — Running Account with HQ", _owner_ledger_to_table(owner_data))]
        country = owner_data.get("country") or "India"
        owner_pdf_bytes = _render_pdf(
            title="Franchise Owner Ledger",
            subtitle=f"{req.center} · {req.month}",
            sections=sections,
            country=country,
        )
    except Exception as _ex:
        logger.warning(f"franchise-owner bundle ledger PDF failed: {_ex}")

    # 3) Open the base ZIP, append the Owner Ledger PDF, re-zip
    out_buf = _io.BytesIO()
    with zipfile.ZipFile(_io.BytesIO(base_zip_bytes), "r") as inz, \
         zipfile.ZipFile(out_buf, "w", zipfile.ZIP_DEFLATED) as outz:
        for n in inz.namelist():
            outz.writestr(n, inz.read(n))
        if owner_pdf_bytes:
            outz.writestr(f"Owner_Ledger_{req.center}_{req.month}.pdf", owner_pdf_bytes)

    out_buf.seek(0)
    filename = f"Monthly_Bundle_{req.center}_{req.month}.zip"
    return Response(
        content=out_buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/raw-file/download")
async def download_raw_file(req: RawFileDownloadRequest):
    """Download a single raw uploaded file by its raw_id (read-only)."""
    session = await check_access(req.token)
    doc = await db.raw_uploads.find_one({"raw_id": req.raw_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Raw file not found")

    # Permission: enforce franchise-owner visibility for the doc's (center, month)
    await enforce_owner_visibility(session, doc.get("center"), doc.get("month"))

    path = doc.get("stored_path")
    if not path or not os.path.exists(path):
        raise HTTPException(404, "Raw file no longer available on disk")

    with open(path, "rb") as f:
        content = f.read()

    filename = doc.get("original_filename") or f"{req.raw_id}.bin"
    # Guess media type from extension
    media_type = "application/octet-stream"
    low = filename.lower()
    if low.endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif low.endswith(".xls"):
        media_type = "application/vnd.ms-excel"
    elif low.endswith(".pdf"):
        media_type = "application/pdf"
    elif low.endswith(".csv"):
        media_type = "text/csv"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
