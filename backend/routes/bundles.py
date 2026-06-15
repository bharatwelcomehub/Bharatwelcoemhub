"""Bundle download routes — three consolidated downloadable bundles per the
Feb-2026 architecture refactor.

  GET /api/bundles/ca          { center?, period (YYYY-MM) }
  GET /api/bundles/owner       { center,  period }
  GET /api/bundles/franchisor  { center?, period }

Each returns a `.zip` containing a PDF + manifest. All numbers come from
the single Financial Calculation Engine — never from page-specific math.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from utils.bundle_generator import build_bundle_zip
from utils.financial_engine import compute_franchise_payout, normalize_model
from utils.gst import compute_gst_from_totals

router = APIRouter(prefix="/api/bundles", tags=["Bundles"])

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


async def _require_valid_token(token: str) -> None:
    """Enforce the auth check — `_verify_token` returns None for bad /
    expired tokens; the route MUST surface that as 401 (testing agent
    caught the prior silent-bypass).

    Multi-worker fix (Feb-2026): the synchronous in-memory `otp_store`
    is *per process*. With multiple uvicorn workers, a token minted on
    worker-A is invisible to worker-B. Prefer the async verifier which
    falls back to MongoDB session lookup; fall back to sync only when
    the async hook is not wired (unit tests).
    """
    session = None
    if _verify_token_async is not None:
        session = await _verify_token_async(token)
    if not session and _verify_token is not None:
        session = _verify_token(token)
    if _verify_token is None and _verify_token_async is None:
        return  # No hook wired (unit-test mode)
    if not session:
        raise HTTPException(401, "Invalid or expired token")


async def _resolve_center_code(identifier: str) -> dict:
    """Resolve a free-form identifier (center code OR franchise code) to a
    concrete center document.

    The Master Dashboards (CA / Franchisor) populate their dropdowns from
    the franchises list, so the value sent over the wire is often a
    `franchise_code` (e.g. `FR-TEST-INDIA`). Center docs live under their
    own `code` (e.g. `PB-HSR`). We try the direct match first, then fall
    back to "first center linked to this franchise" so the bundles UX
    keeps working without forcing every caller to also send a center code.
    """
    ident = (identifier or "").upper()
    # 1) Direct center-code match.
    doc = await _db.centers.find_one({"code": ident})
    if doc:
        return doc
    # 2) Treat input as a franchise_code; pick the first active center.
    doc = await _db.centers.find_one(
        {"franchise_code": ident, "active": {"$ne": False}}
    ) or await _db.centers.find_one({"franchise_code": ident})
    if doc:
        return doc
    raise HTTPException(
        404,
        f"No center found for {identifier!r} (tried center_code and franchise_code).",
    )


async def _resolve_period_data(center: str, period: str) -> dict:
    """Pull the canonical inputs for a (center, period) and run them
    through the Financial Engine. This is the *only* place a bundle ever
    talks to the database — every downstream PDF reads the engine output.
    """
    if not center or not period:
        raise HTTPException(400, "center and period (YYYY-MM) are required")

    center_doc = await _resolve_center_code(center)
    # Use the resolved center's actual code for all downstream lookups so
    # passing a franchise_code still pulls sales/expenses for the right
    # center.
    center = center_doc.get("code", center).upper()
    country = center_doc.get("country") or ("India" if center_doc.get("is_india_center") else "India")

    franchise = await _db.franchises.find_one({"franchise_code": center_doc.get("franchise_code")}) or {}

    # Sales / commissions for the period.
    start, end = f"{period}-01", f"{period}-31"
    sales_rows = await _db.sales.find({
        "center": center.upper(),
        "date": {"$gte": start, "$lte": end},
    }).to_list(None)
    total_sales = sum(float(r.get("amount", 0) or 0) for r in sales_rows)
    total_comm = sum(float(r.get("commission", 0) or 0) for r in sales_rows)

    expense_rows = await _db.expenses.find({
        "center": center.upper(),
        "date": {"$gte": start, "$lte": end},
    }).to_list(None)
    total_expenses = sum(float(r.get("amount", 0) or 0) for r in expense_rows)

    # GST — same helper used by the rest of the platform.
    try:
        gst_breakdown = compute_gst_from_totals(total_sales, country, gst_applicable=True)
        gst_on_sales = float(gst_breakdown.get("total_gst", 0) or 0)
    except Exception:
        gst_on_sales = 0.0

    payout_model = normalize_model(franchise.get("payout_model"), country)
    owner_pct = float(
        franchise.get("franchise_owner_share_percentage")
        or franchise.get("revenue_share_percentage")
        or (80 if country.lower() != "india" else 15)
    )
    mg_applicable = bool(franchise.get("mg_calculation_applicable", True)) and country.lower() == "india"
    monthly_mg = float(franchise.get("monthly_mg") or franchise.get("mg") or 0)

    engine = compute_franchise_payout(
        sales=total_sales,
        commissions=total_comm,
        gst_on_sales=gst_on_sales,
        expenses=total_expenses,
        wc_adjustments=0,
        manual_adjustments=0,
        payout_model=payout_model,
        franchise_owner_pct=owner_pct,
        mg_applicable=mg_applicable,
        monthly_mg=monthly_mg,
        operational_balance=0,
        protection_mode=False,
        country=country,
    )

    return {
        "center": center.upper(),
        "period": period,
        "period_label": datetime.strptime(period + "-01", "%Y-%m-%d").strftime("%B %Y"),
        "country": country,
        "currency": "AUD" if country.lower() != "india" else "Rs.",
        "financial_summary": {
            "total_sales": total_sales,
            "sales_gst": gst_on_sales,
            "total_commissions": total_comm,
            "total_expenses": total_expenses,
        },
        "engine": engine,
        "payout": {
            "amount": engine["payable"],
            "type": engine["payable_type"],
            "reason": engine["reason"],
            "paid_amount": 0,
            "pending_amount": engine["payable"],
            "release_status": "eligible",
        },
        "working_capital": {
            "opening_wc": 0, "current_wc": 0, "recovery_amount": 0,
            "protection_mode": False,
        },
        "gst": {"paid": 0, "outstanding": gst_on_sales},
    }


@router.get("/ca")
async def download_ca_bundle(
    token: str = Query(...),
    center: str = Query(...),
    period: str = Query(...),
):
    """CA Bundle — Accounts Team. ZIP of PDF + manifest."""
    await _require_valid_token(token)
    ctx = await _resolve_period_data(center, period)
    zip_bytes = build_bundle_zip("ca", ctx)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="CA_{center}_{period}.zip"'},
    )


@router.get("/owner")
async def download_owner_bundle(
    token: str = Query(...),
    center: str = Query(...),
    period: str = Query(...),
):
    """Franchise Owner Bundle. ZIP of PDF + manifest."""
    await _require_valid_token(token)
    ctx = await _resolve_period_data(center, period)
    zip_bytes = build_bundle_zip("owner", ctx)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="OWNER_{center}_{period}.zip"'},
    )


@router.get("/franchisor")
async def download_franchisor_bundle(
    token: str = Query(...),
    center: str = Query(...),
    period: str = Query(...),
):
    """Franchisor Bundle — Founder / Director / Super Admin."""
    await _require_valid_token(token)
    ctx = await _resolve_period_data(center, period)
    zip_bytes = build_bundle_zip("franchisor", ctx)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="FRANCHISOR_{center}_{period}.zip"'},
    )
