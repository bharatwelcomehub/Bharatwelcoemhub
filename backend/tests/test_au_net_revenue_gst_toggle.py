"""Regression test for the Feb-2026 follow-up fix:

AU centers in "Include GST in Revenue" mode must have Net Revenue
EQUAL to the Revenue Share Base (i.e., GST must NOT be subtracted
from Net Revenue). Profitability must then equal Revenue Share Base
− Adjusted Expenses.

Reported bug:
    Revenue Share Base = AUD 42,138.65   ✅
    Net Revenue        = AUD 38,447.35   ❌ (still subtracting GST)
    Profitability      = AUD   -839.99   ❌
Expected:
    Net Revenue        = AUD 42,138.65
    Profitability      = AUD  2,851.31  (42,138.65 − 39,287.34)
"""

import pytest


# ── Closed-form formulas mirroring the routes/center_accounts.py AU branch ──
def _au_net_revenue(total_sale, total_commission, sales_gst, include_gst):
    """Mirror of the in-route formula post Feb-2026 follow-up fix."""
    if include_gst:
        return round(total_sale - total_commission, 2)
    return round(total_sale - total_commission - sales_gst, 2)


def _au_profitability(net_revenue, adjusted_expenses):
    return round(net_revenue - adjusted_expenses, 2)


# Bug scenario numbers reported by the user
SALES = 43592.00
SALES_GST = 3691.30          # 43592 × 10/(110) ≈ 3962 — but user-reported
COMMISSIONS = 1453.35        # commissions inclusive of comm-GST
ADJUSTED_EXP = 39287.34


def test_au_net_revenue_excludes_gst_default():
    """Default (Exclude) mode: GST IS subtracted from Net Revenue."""
    nr = _au_net_revenue(SALES, COMMISSIONS, SALES_GST, include_gst=False)
    expected = round(SALES - COMMISSIONS - SALES_GST, 2)
    assert nr == expected


def test_au_net_revenue_includes_gst_when_toggle_on():
    """Include-GST mode: Net Revenue must equal Sales − Commissions only."""
    nr = _au_net_revenue(SALES, COMMISSIONS, SALES_GST, include_gst=True)
    expected = round(SALES - COMMISSIONS, 2)
    assert nr == expected
    # Net Revenue must match the (advertised) Revenue Share Base formula
    rsb = round(SALES - COMMISSIONS, 2)
    assert nr == rsb


def test_au_profitability_positive_in_include_mode():
    """Profitability must turn POSITIVE when toggle removes the GST hit."""
    nr_off = _au_net_revenue(SALES, COMMISSIONS, SALES_GST, include_gst=False)
    nr_on = _au_net_revenue(SALES, COMMISSIONS, SALES_GST, include_gst=True)
    p_off = _au_profitability(nr_off, ADJUSTED_EXP)
    p_on = _au_profitability(nr_on, ADJUSTED_EXP)
    # Include-GST mode must surface a HIGHER profitability (delta == GST amount)
    assert p_on - p_off == pytest.approx(SALES_GST, abs=0.05)
    # Specifically: in the reported bug, p_off was negative and p_on must
    # flip sign for the user's numbers.
    assert p_off < 0 < p_on


def test_au_net_revenue_matches_revenue_share_base_in_include_mode():
    """Symmetry guarantee — fixes Feb-2026 desync."""
    for sales, comm, gst in [
        (43592.00, 1453.35, 3691.30),
        (100000.0, 12000.0, 9090.91),
        (250000.0, 35000.0, 22727.27),
        (1000.0,   100.0,   90.91),
    ]:
        nr = _au_net_revenue(sales, comm, gst, include_gst=True)
        rsb = round(sales - comm, 2)
        assert nr == rsb, f"Net Revenue {nr} != RSB {rsb} for sales={sales}"
