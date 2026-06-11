"""GST calculation utilities — single source of truth for sales GST.

Formula (per business rules as of Apr 2026):

    Net Eligible Sales = Total Sales − Swiggy − Zomato − DoorDash
    GST = Eligible − Eligible / (1 + rate)   ← INCLUSIVE basis
        where rate = 5%  for India centers
                   = 10% for Perth / outside-India centers

Receipt prices in our system are GST-INCLUSIVE, so this carves out the
govt-payable GST already collected within the receipt amount.

Aggregator-channel sales (Swiggy/Zomato/DoorDash) are excluded because the
platforms remit GST to govt directly on those orders.

Net Revenue (India) = Total Sale − Total Commissions − GST on Sale
"""
from typing import Iterable, Optional

INDIA_GST_RATE = 0.05
PERTH_GST_RATE = 0.10
OUTSIDE_INDIA_GST_RATE = 0.10


def gst_rate_for(country: Optional[str], center: Optional[str] = None) -> float:
    """Return the correct GST rate for a center/country."""
    if center and str(center).upper().endswith("-PERTH"):
        return PERTH_GST_RATE
    if country and str(country).lower() not in ("india", ""):
        return OUTSIDE_INDIA_GST_RATE
    return INDIA_GST_RATE


def eligible_base_from_daily_row(row: dict) -> float:
    """Given one daily_sales row, return the portion that attracts GST.
       = total_sale − swiggy − zomato − doordash."""
    total = float(row.get("total_sale", 0) or 0)
    swiggy = float(row.get("swiggy_sale", row.get("swiggy", 0)) or 0)
    zomato = float(row.get("zomato_sale", row.get("zomato", 0)) or 0)
    doordash = float(row.get("doordash_sale", row.get("doordash", 0)) or 0)
    return max(0.0, total - swiggy - zomato - doordash)


def carve_inclusive_gst(eligible_base: float, rate: float) -> float:
    """GST carved out from a GST-inclusive eligible amount.
       gst = eligible − eligible / (1 + rate)
    """
    eligible = max(0.0, float(eligible_base))
    if eligible <= 0 or rate <= 0:
        return 0.0
    return round(eligible - eligible / (1.0 + rate), 2)


def compute_gst_from_rows(rows: Iterable[dict], country: Optional[str] = None, center: Optional[str] = None) -> dict:
    """Given a list of daily_sales rows, return:
       {eligible_base, gst_amount, rate, total_sale, aggregator_sale, stored_gst_sum}.

    GST is computed INCLUSIVE: gst = eligible − eligible / (1 + rate).
    """
    rate = gst_rate_for(country, center)
    eligible = 0.0
    total = 0.0
    agg = 0.0
    stored_gst = 0.0
    for r in rows or []:
        base = eligible_base_from_daily_row(r)
        eligible += base
        total += float(r.get("total_sale", 0) or 0)
        agg += (
            float(r.get("swiggy_sale", r.get("swiggy", 0)) or 0)
            + float(r.get("zomato_sale", r.get("zomato", 0)) or 0)
            + float(r.get("doordash_sale", r.get("doordash", 0)) or 0)
        )
        stored_gst += float(r.get("gst_amount", 0) or 0)
    gst = carve_inclusive_gst(eligible, rate)
    return {
        "eligible_base": round(eligible, 2),
        "gst_amount": gst,
        "rate": rate,
        "total_sale": round(total, 2),
        "aggregator_sale": round(agg, 2),
        "stored_gst_sum": round(stored_gst, 2),
    }


def compute_gst_from_totals(total_sale: float, aggregator_sale: float,
                            country: Optional[str] = None, center: Optional[str] = None) -> dict:
    """Variant for pre-aggregated totals."""
    rate = gst_rate_for(country, center)
    eligible = max(0.0, float(total_sale) - float(aggregator_sale))
    return {
        "eligible_base": round(eligible, 2),
        "gst_amount": carve_inclusive_gst(eligible, rate),
        "rate": rate,
    }


def compute_net_revenue(total_sale: float, total_commissions: float,
                        gst_on_sales: float, total_expenses: float = 0.0,
                        country: Optional[str] = None) -> float:
    """Single source of truth for Management Net Revenue (revenue line in P&L).

    Per Feb-2026 management-reporting correction (Owner directive): GST is
    displayed separately for compliance but does NOT reduce the management
    sales figure. Profitability uses GROSS sales.

    India     : Net Revenue = Gross Sale − Commissions
    Outside-IN: Net Revenue = Gross Sale − Commissions × (1 + commGSTRate)

    `gst_on_sales` is kept in the signature for backward compatibility +
    surfaced separately for compliance reporting (GST Collected card).
    `total_expenses` similarly retained for callers that pass it; expenses
    are subtracted downstream in P&L / Revenue-Share, not here.
    """
    is_india = (not country) or str(country).lower() == "india"
    _ = gst_on_sales  # intentionally ignored — see Feb-2026 directive
    _ = total_expenses
    if is_india:
        return round(float(total_sale) - float(total_commissions), 2)
    rate = gst_rate_for(country, None)
    return round(float(total_sale) - float(total_commissions) * (1.0 + rate), 2)
