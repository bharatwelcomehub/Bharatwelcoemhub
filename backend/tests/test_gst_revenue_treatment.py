"""Unit tests for the new per-center per-month GST Revenue Treatment toggle.

Feb-2026 spec:
   Option 1 (default, include_gst_in_revenue=False):
       Base = Sales − GST − Commissions
   Option 2 (opt-in, include_gst_in_revenue=True):
       Base = Sales − Commissions
       (GST stays visible separately in reports; never disappears.)

Profit Share Base must be unaffected by this toggle.
"""
import pytest

from utils.financial_engine import (
    compute_revenue_share_base as engine_rsb,
    compute_franchise_payout,
)
from utils.gst import compute_revenue_share_base as gst_rsb


SALES = 100000.0
GST = 9090.91  # AU 10% inclusive on $100k
COMM = 12000.0
EXP = 30000.0


# ── Engine helpers ────────────────────────────────────────────────────
def test_engine_default_excludes_gst():
    assert engine_rsb(SALES, COMM, GST) == round(SALES - COMM - GST, 2)


def test_engine_opt_in_includes_gst():
    base = engine_rsb(SALES, COMM, GST, include_gst_in_revenue=True)
    assert base == round(SALES - COMM, 2)
    # Difference is exactly the GST that was previously deducted
    assert engine_rsb(SALES, COMM, GST) + GST == base


def test_gst_helper_default_matches_legacy():
    """utils.gst.compute_revenue_share_base default behaviour preserved."""
    assert gst_rsb(SALES, COMM, GST, country="India") == round(SALES - COMM - GST, 2)


def test_gst_helper_opt_in_includes_gst():
    base = gst_rsb(SALES, COMM, GST, country="India", include_gst_in_revenue=True)
    assert base == round(SALES - COMM, 2)


def test_gst_helper_opt_in_australia():
    """For Australia branch, opt-in also stops deducting GST from base."""
    base = gst_rsb(SALES, COMM, GST, country="Australia", include_gst_in_revenue=True)
    # AU formula: Sale − Commission*(1+rate) − GST. With opt-in the trailing
    # GST term goes away.
    expected = round(SALES - COMM * (1 + 0.1), 2)
    assert base == expected


# ── Full payout integration ───────────────────────────────────────────
def test_payout_payload_reports_treatment_label():
    payload = compute_franchise_payout(
        sales=SALES, commissions=COMM, gst_on_sales=GST, expenses=EXP,
        payout_model="revenue_share", franchise_owner_pct=15,
        country="India", include_gst_in_revenue=True,
    )
    assert payload["include_gst_in_revenue"] is True
    assert "Include GST in Revenue" in payload["gst_treatment_label"]
    # Revenue Share Base = Sales − Comm
    assert payload["revenue_share_base"] == round(SALES - COMM, 2)


def test_payout_default_excludes_gst():
    payload = compute_franchise_payout(
        sales=SALES, commissions=COMM, gst_on_sales=GST, expenses=EXP,
        payout_model="revenue_share", franchise_owner_pct=15,
        country="India",  # no include flag
    )
    assert payload["include_gst_in_revenue"] is False
    assert payload["revenue_share_base"] == round(SALES - COMM - GST, 2)


def test_owner_share_changes_with_toggle():
    base_kwargs = dict(
        sales=SALES, commissions=COMM, gst_on_sales=GST, expenses=EXP,
        payout_model="revenue_share", franchise_owner_pct=15, country="India",
    )
    p_off = compute_franchise_payout(**base_kwargs, include_gst_in_revenue=False)
    p_on = compute_franchise_payout(**base_kwargs, include_gst_in_revenue=True)
    # Owner share when GST is INCLUDED in base must be HIGHER (because base
    # is larger).
    assert p_on["owner_share"] > p_off["owner_share"]
    # Extra owner share = GST × 15 %
    delta = round(GST * 0.15, 2)
    assert p_on["owner_share"] - p_off["owner_share"] == pytest.approx(delta, abs=0.05)


def test_profit_share_base_unaffected_by_gst_toggle():
    """Profit Share base only depends on Sales − Comm − Expenses − Adj.
    The GST toggle should NEVER change Profit Share Base."""
    base_kwargs = dict(
        sales=SALES, commissions=COMM, gst_on_sales=GST, expenses=EXP,
        payout_model="profit_share", franchise_owner_pct=80, country="Australia",
    )
    p_off = compute_franchise_payout(**base_kwargs, include_gst_in_revenue=False)
    p_on = compute_franchise_payout(**base_kwargs, include_gst_in_revenue=True)
    assert p_off["profit_share_base"] == p_on["profit_share_base"]
    # The chosen base for profit_share model is profit_share_base
    assert p_off["base"] == p_on["base"]


def test_zero_gst_toggle_has_no_effect():
    """Sanity: when GST is 0 either toggle setting yields the same base."""
    p_off = compute_franchise_payout(
        sales=SALES, commissions=COMM, gst_on_sales=0, expenses=EXP,
        payout_model="revenue_share", franchise_owner_pct=15, country="India",
    )
    p_on = compute_franchise_payout(
        sales=SALES, commissions=COMM, gst_on_sales=0, expenses=EXP,
        payout_model="revenue_share", franchise_owner_pct=15, country="India",
        include_gst_in_revenue=True,
    )
    assert p_off["revenue_share_base"] == p_on["revenue_share_base"]
    assert p_off["owner_share"] == p_on["owner_share"]
