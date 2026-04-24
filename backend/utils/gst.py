"""GST calculation utilities.

Correct formula (per business rules as of Apr 2026):

    Net Eligible Sales = Total Sales − Swiggy − Zomato − DoorDash
    GST = Net Eligible Sales × rate
        where rate = 5% for India centers
                   = 10% for Perth / outside-India centers

IMPORTANT: GST is NOT calculated on the gross total sales. Aggregator-channel
sales (Swiggy/Zomato/DoorDash) already have GST handled upstream by the
platforms, so only the dine-in + card + UPI portion attracts restaurant GST.
"""
from typing import Iterable, Optional

INDIA_GST_RATE = 0.05
PERTH_GST_RATE = 0.10    # Australia / outside-India
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


def compute_gst_from_rows(rows: Iterable[dict], country: Optional[str] = None, center: Optional[str] = None) -> dict:
    """Given a list of daily_sales rows, return:
       {eligible_base, gst_amount, rate, total_sale, aggregator_sale}.
    Falls back to `gst_amount` on the row if total_sale is 0 but gst_amount is set.
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
    gst = eligible * rate
    return {
        "eligible_base": round(eligible, 2),
        "gst_amount": round(gst, 2),
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
        "gst_amount": round(eligible * rate, 2),
        "rate": rate,
    }
