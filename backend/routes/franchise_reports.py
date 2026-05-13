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
