"""Single Financial Calculation Engine — the canonical source of truth for
ALL franchise payout math across the platform.

Every dashboard, PDF, Excel export and API response must call into this
module instead of reimplementing the formulas. When a business rule
changes (Revenue Share %, MG floor, Protection Mode threshold, Profit
Share base) — change it HERE only.

Public entry point: `compute_franchise_payout(...)`.

Returned shape is the canonical payload consumed by:
  • `routes/center_accounts.py::get_center_account_summary` (PIB summary)
  • `routes/center_accounts.py::month_wise_payout_summary` (per-month grid)
  • `routes/ledgers.py` (Franchise Owner Ledger)
  • `utils/pdf_generator.py` (PIB Section 7 + MG Payout Excel/PDF)
  • Frontend Center Accounts dashboard, MIS Dashboard, Owner Dashboard

It is intentionally a pure function — no DB, no IO — so it stays trivially
testable.
"""
from __future__ import annotations
from typing import Optional, Dict, Any

from .entity import entity_share_label

# Supported payout-model identifiers.
REVENUE_SHARE = "revenue_share"
PROFIT_SHARE = "profit_share"
SUPPORTED_MODELS = (REVENUE_SHARE, PROFIT_SHARE)


def default_payout_model_for_country(country: Optional[str]) -> str:
    """India defaults to Revenue Share; Australia / overseas defaults to
    Profit Share. Either default can be overridden per-franchise."""
    if (country or "India").strip().lower() == "india":
        return REVENUE_SHARE
    return PROFIT_SHARE


def normalize_model(model: Optional[str], country: Optional[str]) -> str:
    """Resolve a free-form value to a supported model, falling back to the
    country default if invalid/missing. This keeps legacy franchise rows
    (no `payout_model` field) working without migration."""
    m = (model or "").strip().lower().replace(" ", "_")
    if m in SUPPORTED_MODELS:
        return m
    return default_payout_model_for_country(country)


def compute_revenue_share_base(sales: float, commissions: float, gst_on_sales: float) -> float:
    """Revenue Share Base = Sales − Commissions − GST.

    GST is deducted because it's a collected liability, not the franchise's
    money. This is the canonical base for India centers on Revenue Share.
    """
    return round((sales or 0) - (commissions or 0) - (gst_on_sales or 0), 2)


def compute_profit_share_base(
    sales: float,
    commissions: float,
    expenses: float,
    wc_adjustments: float = 0.0,
    manual_adjustments: float = 0.0,
) -> float:
    """Profit Share Base = Sales − Commissions − Expenses − Adjustments.

    GST is shown separately in reports but NOT deducted again from this
    base (it's already excluded from net Sales / surfaced as a liability
    line in operating reports). Adjustments cover both WC adjustments
    (debit notes that affect operational balance) and manual admin
    overrides logged in the audit trail.
    """
    return round(
        (sales or 0)
        - (commissions or 0)
        - (expenses or 0)
        - (wc_adjustments or 0)
        - (manual_adjustments or 0),
        2,
    )


def compute_franchise_payout(
    *,
    sales: float,
    commissions: float,
    gst_on_sales: float,
    expenses: float,
    wc_adjustments: float = 0.0,
    manual_adjustments: float = 0.0,
    payout_model: Optional[str] = None,
    franchise_owner_pct: float = 0.0,
    mg_applicable: bool = True,
    monthly_mg: float = 0.0,
    operational_balance: float = 0.0,
    protection_mode: bool = False,
    country: Optional[str] = "India",
) -> Dict[str, Any]:
    """Compute the canonical franchise payout payload for one month.

    Returns a dict with both bases (so callers can show them side-by-side
    if desired), the selected base, owner/company shares, MG result and
    the final payable amount/type/reason.
    """
    # 1. Both bases are computed unconditionally so consumers can show
    #    both for transparency. Negative bases are clamped to 0 for
    #    payout math (a center cannot pay a negative share).
    rs_base_raw = compute_revenue_share_base(sales, commissions, gst_on_sales)
    ps_base_raw = compute_profit_share_base(
        sales, commissions, expenses, wc_adjustments, manual_adjustments
    )

    # 2. Resolve the model.
    model = normalize_model(payout_model, country)

    # 3. Select the base for the share split.
    if model == PROFIT_SHARE:
        chosen_base_raw = ps_base_raw
        base_label = "Profit Share Base"
        section_heading = "PROFIT SHARE CALCULATION"
        payable_type_when_share_wins = "profit_share"
    else:
        chosen_base_raw = rs_base_raw
        base_label = "Revenue Share Base"
        section_heading = "REVENUE SHARE CALCULATION"
        payable_type_when_share_wins = "revenue_share"

    # Clamp the share base to >= 0 for downstream multiplications.
    chosen_base = max(0.0, chosen_base_raw)

    # 4. Owner & company split.
    owner_pct = float(franchise_owner_pct or 0)
    company_pct = round(100.0 - owner_pct, 4)
    owner_share = round(chosen_base * owner_pct / 100.0, 2)
    company_share = round(chosen_base * company_pct / 100.0, 2)

    # 5. MG resolution. When the franchise has MG disabled, we never
    #    compare and the MG line item is suppressed in the UI.
    mg_amount = round(float(monthly_mg or 0), 2) if mg_applicable else 0.0

    # 6. Final payable + reason.
    if protection_mode:
        # WC Protection Mode caps payout regardless of MG/model. The
        # gated amount is operational_balance × owner% (clamped to 0).
        gated = max(0.0, round(max(0.0, float(operational_balance or 0)) * owner_pct / 100.0, 2))
        payable = gated
        payable_type = "revenue_share_protection" if model == REVENUE_SHARE else "profit_share_protection"
        if gated <= 0:
            payable_type = "wc_protection_no_payout"
        if mg_applicable:
            reason = (
                f"WC Protection: MG blocked. Owner share gated to operational balance × {owner_pct:g}% "
                f"= ₹{gated:,.2f}"
            )
        else:
            reason = (
                f"WC Protection: Owner share gated to operational balance × {owner_pct:g}% "
                f"= ₹{gated:,.2f}"
            )
    elif mg_applicable and mg_amount > owner_share:
        payable = mg_amount
        payable_type = "minimum_guarantee"
        reason = (
            f"MG (₹{mg_amount:,.2f}) > {base_label[:-5]} payout "
            f"(₹{owner_share:,.2f}) → MG applied."
        )
    else:
        payable = owner_share
        payable_type = payable_type_when_share_wins
        if not mg_applicable:
            reason = (
                f"{base_label} × {owner_pct:g}% = ₹{owner_share:,.2f}. "
                f"MG not applicable for this franchise."
            )
        else:
            reason = (
                f"{base_label[:-5]} payout (₹{owner_share:,.2f}) >= "
                f"MG (₹{mg_amount:,.2f}) → owner share applied."
            )

    return {
        # Inputs reflected back for downstream tables ----------------------
        "country": country or "India",
        "payout_model": model,
        "section_heading": section_heading,
        "base_label": base_label,
        # Both bases — UIs can show both side-by-side for transparency. ---
        "revenue_share_base": rs_base_raw,
        "profit_share_base": ps_base_raw,
        # Selected base & owner/company split -----------------------------
        "base": chosen_base_raw,
        "base_clamped": chosen_base,
        "owner_pct": owner_pct,
        "company_pct": company_pct,
        "owner_share": owner_share,
        "company_share": company_share,
        "company_entity_label": entity_share_label(country),
        # MG --------------------------------------------------------------
        "mg_applicable": bool(mg_applicable),
        "mg_amount": mg_amount,
        # Final payable ---------------------------------------------------
        "payable": payable,
        "payable_type": payable_type,
        "protection_mode": bool(protection_mode),
        "reason": reason,
    }


__all__ = [
    "REVENUE_SHARE",
    "PROFIT_SHARE",
    "SUPPORTED_MODELS",
    "default_payout_model_for_country",
    "normalize_model",
    "compute_revenue_share_base",
    "compute_profit_share_base",
    "compute_franchise_payout",
]
