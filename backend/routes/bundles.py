"""Bundle download routes — three consolidated downloadable bundles per the
Feb-2026 architecture refactor.

  GET /api/bundles/ca          { center?, period (YYYY-MM) }
  GET /api/bundles/owner       { center,  period }
  GET /api/bundles/franchisor  { center?, period }   ← "Full Center Package"

Each ZIP contains:
  • CA Bundle ........ Cover PDF + Sales/Expense Excel + GST Summary PDF +
                       Profit-Share (PIB) PDF + Commission Recon PDF +
                       Bank Statement PDF + engine manifest
  • Owner Bundle ..... Owner cover-sheet PDF + Sales/Expense Excel +
                       PIB PDF + manifest
  • Franchisor (Full
    Center Package) .. Everything in CA + Owner + Franchisor cover PDF +
                       engine manifest (one click, all artefacts)

All numbers come from the single Financial Calculation Engine — never from
page-specific math.
"""
from __future__ import annotations
import io
import logging
import zipfile
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from utils.bundle_generator import (
    build_bundle_zip,
    build_ca_bundle_pdf,
    build_franchise_owner_bundle_pdf,
    build_franchisor_bundle_pdf,
)
from utils.financial_engine import compute_franchise_payout, normalize_model
from utils.gst import compute_gst_from_totals

logger = logging.getLogger(__name__)

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

    # Sales — read from the canonical `daily_sales` collection (NOT
    # `sales`, which is an unrelated debit-note ledger). Aggregation
    # mirrors routes/center_accounts.py:1245-1280 exactly so every
    # bundle reports the same totals the dashboard does.
    year, month = map(int, period.split("-"))
    start = f"{year}-{month:02d}-01"
    end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"

    sales_rows = await _db.daily_sales.find(
        {"center": center, "date": {"$gte": start, "$lt": end}},
        {"_id": 0},
    ).to_list(None)
    total_sales = sum(float(r.get("total_sale", 0) or 0) for r in sales_rows)
    # Aggregator sales (eligible-for-GST base = total − aggregator). Read
    # new + legacy field names so eligible matches PIB / center summary.
    swiggy = sum(float(r.get("swiggy_sale", r.get("swiggy", 0)) or 0) for r in sales_rows)
    zomato = sum(float(r.get("zomato_sale", r.get("zomato", 0)) or 0) for r in sales_rows)
    doordash = sum(float(r.get("doordash_sale", r.get("doordash", 0)) or 0) for r in sales_rows)
    aggregator_sale = swiggy + zomato + doordash

    # Commissions — `monthly_commissions` is the canonical source per the
    # Feb-2026 refactor; `daily_sales.commission` is not used by the engine.
    comm_rows = await _db.monthly_commissions.find(
        {"center": center, "month": period}, {"_id": 0}
    ).to_list(None)
    total_comm = 0.0
    for c in comm_rows:
        # New schema: gst_tax_deductions + other_deductions. Fallback to
        # legacy `commission_amount` for older rows.
        gst_ded = float(c.get("gst_tax_deductions", 0) or 0)
        oth_ded = float(c.get("other_deductions", 0) or 0)
        legacy = float(c.get("commission_amount", 0) or 0)
        total_comm += (gst_ded + oth_ded) if (gst_ded + oth_ded) > 0 else legacy

    # Expenses — direct sum off the `expenses` collection.
    expense_rows = await _db.expenses.find(
        {"center": center, "date": {"$gte": start, "$lt": end}},
        {"_id": 0},
    ).to_list(None)
    total_expenses = sum(float(r.get("amount", 0) or 0) for r in expense_rows)

    # GST on eligible sales — matches the same helper signature used by
    # routes/center_accounts.py (eligible = total_sale − aggregator_sale).
    try:
        gst_breakdown = compute_gst_from_totals(total_sales, aggregator_sale, country=country, center=center)
        gst_on_sales = float(gst_breakdown.get("gst_amount", 0) or 0)
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

    # Per-center per-month GST Revenue Treatment flag (Feb-2026)
    _gst_doc = await _db.gst_treatment_overrides.find_one(
        {"center_code": center.upper(), "month": period}
    )
    include_gst_in_revenue = bool(_gst_doc and _gst_doc.get("include_gst_in_revenue", False))

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
        include_gst_in_revenue=include_gst_in_revenue,
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
    """CA Bundle — Accounts Team. Rich ZIP with cover-sheet PDF + Sales/Expense
    Excel + GST Summary + PIB + Commission Recon + Bank Statement + manifest."""
    await _require_valid_token(token)
    ctx = await _resolve_period_data(center, period)
    zip_bytes = await _build_rich_bundle_zip("ca", token, center, period, ctx)
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
    """Franchise Owner Bundle. ZIP of cover PDF + Sales/Expense Excel + PIB + manifest."""
    await _require_valid_token(token)
    ctx = await _resolve_period_data(center, period)
    zip_bytes = await _build_rich_bundle_zip("owner", token, center, period, ctx)
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
    """Franchisor "Full Center Package" — master bundle, one-click everything.

    Includes every artefact from the CA + Owner bundles plus the Franchisor
    executive cover-sheet so founders see one consolidated download.
    """
    await _require_valid_token(token)
    ctx = await _resolve_period_data(center, period)
    zip_bytes = await _build_rich_bundle_zip("franchisor", token, center, period, ctx)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="FullCenter_{center}_{period}.zip"'},
    )


# ──────────────────────────────────────────────────────────────────────────
# Rich bundle aggregator — gathers every PDF/Excel a persona needs.
# Each fetch is wrapped in try/except so a single missing artefact (e.g.
# franchise not linked → PIB unavailable) doesn't break the whole download.
# ──────────────────────────────────────────────────────────────────────────
async def _build_summary_safe(token: str, center: str, period: str) -> Optional[Dict[str, Any]]:
    """Fetch the unified center-account summary used by every PDF builder.
    Returns None on failure (bundle continues without the dependent PDFs).
    """
    try:
        # Lazy import to avoid circular import at module load time.
        from routes.center_accounts import (
            get_center_account_summary,
            AccountPeriodRequest,
        )
        req = AccountPeriodRequest(token=token, center=center, month=period)
        resp = await get_center_account_summary(req)
        return resp.get("summary")
    except Exception as ex:  # noqa: BLE001
        logger.warning(f"bundle: summary fetch failed for {center} {period}: {ex}")
        return None


def _mk_month_range_safe(period: str) -> Tuple[str, str]:
    """Y-M → (start_iso, end_iso) inclusive."""
    year, month = map(int, period.split("-"))
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year}-12-31"
    else:
        from calendar import monthrange
        last_day = monthrange(year, month)[1]
        end = f"{year}-{month:02d}-{last_day:02d}"
    return start, end


async def _gather_artefacts(
    token: str, center: str, period: str, ctx: Dict[str, Any],
) -> Dict[str, bytes]:
    """Collect every artefact that *can* be generated for (center, period).

    Returns a dict of `<filename> → bytes`. Missing artefacts are silently
    skipped with a warning so a one-click bundle keeps working even when
    e.g. a franchise isn't linked yet.
    """
    out: Dict[str, bytes] = {}
    safe_center = (center or "ALL").upper()
    summary = await _build_summary_safe(token, center, period)

    # 1. Sales + Expense Excel ────────────────────────────────────────────
    try:
        from utils.sales_expense_excel import build_sales_expense_excel
        start, end = _mk_month_range_safe(period)
        xlsx = await build_sales_expense_excel(_db, safe_center, start, end)
        out[f"Sales_Expense_{safe_center}_{period}.xlsx"] = xlsx
    except Exception as ex:  # noqa: BLE001
        logger.warning(f"bundle: Sales/Expense Excel failed: {ex}")

    # 2. PIB / Profit-Share Calculation PDF ───────────────────────────────
    if summary and summary.get("franchise", {}).get("linked"):
        try:
            from utils.pdf_generator import build_pib_pdf
            out[f"PIB_{safe_center}_{period}.pdf"] = build_pib_pdf(summary)
        except Exception as ex:  # noqa: BLE001
            logger.warning(f"bundle: PIB PDF failed: {ex}")

    # 3. GST Summary PDF ──────────────────────────────────────────────────
    if summary:
        try:
            from utils.pdf_generator import build_gst_summary_pdf
            out[f"GST_Summary_{safe_center}_{period}.pdf"] = build_gst_summary_pdf(summary)
        except Exception as ex:  # noqa: BLE001
            logger.warning(f"bundle: GST Summary PDF failed: {ex}")

    # 4. Commission Reconciliation PDF ────────────────────────────────────
    if summary:
        try:
            from utils.pdf_generator import build_commission_summary_pdf
            out[f"Commission_Reconciliation_{safe_center}_{period}.pdf"] = build_commission_summary_pdf(summary)
        except Exception as ex:  # noqa: BLE001
            logger.warning(f"bundle: Commission Summary PDF failed: {ex}")

    # 5. Bank Statement / Reconciliation PDF ──────────────────────────────
    try:
        from utils.pdf_generator import build_bank_statement_pdf
        start, end = _mk_month_range_safe(period)
        # Build the same `pdf_data` shape used by routes/center_accounts.py:generate_bank_statement
        sales = await _db.daily_sales.find(
            {"center": safe_center, "date": {"$gte": start, "$lte": end}}, {"_id": 0}
        ).sort("date", 1).to_list(200)
        credits: list = []
        for s in sales:
            d = s.get("date")
            cash = float(s.get("total_cash_sale") or s.get("cash_sale") or 0)
            online_card = float(s.get("total_online_sale") or s.get("online_sale") or s.get("card_sale") or 0)
            swiggy = float(s.get("swiggy_sale") or s.get("swiggy") or 0)
            zomato = float(s.get("zomato_sale") or s.get("zomato") or 0)
            doordash = float(s.get("doordash_sale") or s.get("doordash") or 0)
            if cash:
                credits.append({"date": d, "description": "Cash sales", "amount": cash})
            if online_card:
                credits.append({"date": d, "description": "Online / Card sales", "amount": online_card})
            agg = swiggy + zomato + doordash
            if agg:
                credits.append({"date": d, "description": "Aggregator receipts (Swiggy+Zomato+DoorDash gross)", "amount": agg})
        expenses = await _db.expenses.find(
            {"center": safe_center, "date": {"$gte": start, "$lte": end}}, {"_id": 0}
        ).sort("date", 1).to_list(500)
        debits: list = []
        for e in expenses:
            amt = float(e.get("amount", 0) or 0)
            if amt <= 0:
                continue
            cat = e.get("expense_type") or e.get("category") or "Expense"
            debits.append({"date": e.get("date", ""), "description": cat, "amount": amt})
        if summary:
            total_comm = float(summary.get("commissions", {}).get("total", 0) or 0)
            if total_comm > 0:
                debits.append({
                    "date": end,
                    "description": "Aggregator / Card commissions (Swiggy / Zomato / Card deductions)",
                    "amount": total_comm,
                })
        wc_info = (summary or {}).get("working_capital_status", {}) or {}
        opening = float(wc_info.get("opening_wc", 0) or 0)
        total_credits = sum(float(r["amount"]) for r in credits)
        total_debits = sum(float(r["amount"]) for r in debits)
        closing = opening + total_credits - total_debits
        center_doc = await _db.centers.find_one({"code": safe_center}) or {}
        pdf_data = {
            "center": safe_center,
            "center_name": center_doc.get("name", safe_center),
            "month": period,
            "period_label": f"Period: {start} to {end}",
            "opening_balance": opening,
            "closing_balance": closing,
            "credits": credits,
            "debits": debits,
            "totals": {
                "total_credits": total_credits,
                "total_debits": total_debits,
                "net_movement": total_credits - total_debits,
            },
        }
        out[f"Bank_Reconciliation_{safe_center}_{period}.pdf"] = build_bank_statement_pdf(pdf_data)
    except Exception as ex:  # noqa: BLE001
        logger.warning(f"bundle: Bank Statement PDF failed: {ex}")

    return out


def _engine_manifest(bundle_kind: str, ctx: Dict[str, Any], artefact_names: list) -> str:
    engine = ctx.get("engine", {}) or {}
    contents = "\n".join(f"  • {n}" for n in artefact_names)
    return (
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
        f"\nContents of this bundle:\n{contents}\n"
        f"\nGenerated {datetime.now().isoformat()}\n"
        f"Source-of-truth: backend/utils/financial_engine.py\n"
    )


async def _build_rich_bundle_zip(
    bundle_kind: str, token: str, center: str, period: str, ctx: Dict[str, Any]
) -> bytes:
    """Aggregate every artefact a persona needs into one ZIP."""
    safe_center = (center or "ALL").upper()

    # Cover-sheet PDF (engine-derived executive view per persona)
    if bundle_kind == "ca":
        cover_name = f"CA_{safe_center}_{period}.pdf"
        cover_bytes = build_ca_bundle_pdf(ctx)
        prefix = "CA"
    elif bundle_kind in ("owner", "franchise_owner"):
        cover_name = f"OWNER_{safe_center}_{period}.pdf"
        cover_bytes = build_franchise_owner_bundle_pdf(ctx)
        prefix = "OWNER"
    elif bundle_kind == "franchisor":
        cover_name = f"FRANCHISOR_{safe_center}_{period}.pdf"
        cover_bytes = build_franchisor_bundle_pdf(ctx)
        prefix = "FullCenter"
    else:
        raise ValueError(f"Unknown bundle kind: {bundle_kind!r}")

    # Gather supporting artefacts. CA & Franchisor get the full set; the
    # Owner bundle keeps it lean (cover + Sales/Expense Excel + PIB).
    artefacts = await _gather_artefacts(token, center, period, ctx)
    if bundle_kind in ("owner", "franchise_owner"):
        artefacts = {
            k: v for k, v in artefacts.items()
            if k.endswith(".xlsx") or k.startswith("PIB_")
        }

    # Assemble the ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(cover_name, cover_bytes)
        for name, blob in artefacts.items():
            zf.writestr(name, blob)
        names = [cover_name, *artefacts.keys()]
        zf.writestr(
            f"{prefix}_{safe_center}_{period}_manifest.txt",
            _engine_manifest(bundle_kind, ctx, names),
        )
    return buf.getvalue()
