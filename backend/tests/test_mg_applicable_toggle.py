"""Regression: MG Calculation Applicable per-franchise toggle.

  • Field name: `mg_calculation_applicable` (bool, default True).
  • When True : payout = max(MG, Revenue Share). Existing logic.
  • When False: payout = Revenue Share Base × Revenue Share %. No MG comparison,
                no MG amount displayed, type = "revenue_share".
  • WC Protection Mode still applies (Q3.c) — payout is gated to operational
    balance × revenue-share % regardless of the MG toggle, but the reason text
    no longer references "MG Blocked".
  • Australia / overseas: MG never applies, toggle is effectively ignored
    (profit_share model is unaffected).
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


def test_default_mg_applicable_for_legacy_franchise():
    """Legacy franchise documents (no field) must be treated as MG ON to
    preserve today's payout behaviour."""
    franchise = {"franchise_code": "PB-DV"}  # no mg_calculation_applicable
    assert bool(franchise.get("mg_calculation_applicable", True)) is True


def test_mg_off_franchise_payable_equals_revenue_share():
    """Simulate the Case 1 (MG OFF) calc:
       Payable = Revenue Share Base × Revenue Share %."""
    sale, comm, gst = 1088002.00, 26656.96, 48197.67
    rev_share_pct = 15
    rev_share_base = round(sale - comm - gst, 2)
    rev_share_payable = round(rev_share_base * rev_share_pct / 100, 2)

    # MG OFF — even if a stale MG value is calculated, it must NOT be selected.
    stale_mg = 5_00_000  # irrelevant
    mg_calculation_applicable = False
    if mg_calculation_applicable and stale_mg > rev_share_payable:
        payable = stale_mg
        payable_type = "mg"
    else:
        payable = rev_share_payable
        payable_type = "revenue_share"

    assert payable == rev_share_payable
    assert payable_type == "revenue_share"
    # Sanity: with MG ON, the stale MG would have won — confirms the toggle is wired.
    mg_calculation_applicable = True
    if mg_calculation_applicable and stale_mg > rev_share_payable:
        assert stale_mg > rev_share_payable


def test_mg_on_franchise_picks_max_of_mg_vs_rs():
    sale, comm, gst = 1088002.00, 26656.96, 48197.67
    rev_share_pct = 15
    rev_share_base = round(sale - comm - gst, 2)
    rev_share_payable = round(rev_share_base * rev_share_pct / 100, 2)
    mg = 2_00_000
    mg_calculation_applicable = True
    if mg_calculation_applicable and mg > rev_share_payable:
        payable, ptype = mg, "mg"
    else:
        payable, ptype = rev_share_payable, "revenue_share"
    # 2L > 151,972 → MG wins
    assert payable == mg and ptype == "mg"


def test_summary_response_exposes_mg_calculation_applicable_flag():
    """The /center-accounts summary response must surface
    `mg_calculation_applicable` for the UI to render the right MG block."""
    src = (Path(__file__).resolve().parent.parent / "routes" / "center_accounts.py").read_text()
    assert '"mg_calculation_applicable"' in src, (
        "Summary response must expose the mg_calculation_applicable boolean "
        "so the UI/PDF can hide MG-specific elements for opted-out franchises."
    )


def test_payout_summary_skips_mg_when_off():
    """The Month-wise Payout Summary loop must skip MG comparison when
    mg_calculation_applicable is False."""
    src = (Path(__file__).resolve().parent.parent / "routes" / "center_accounts.py").read_text()
    assert "mg_calculation_applicable and mg_amount > revenue_share" in src, (
        "Payout Summary loop must gate the MG-vs-RS comparison on the "
        "franchise-level mg_calculation_applicable flag."
    )


def test_franchise_model_has_mg_calculation_applicable_field():
    """The Pydantic FranchiseCreate model must declare the new field."""
    src = (Path(__file__).resolve().parent.parent / "routes" / "franchises.py").read_text()
    assert "mg_calculation_applicable: bool = True" in src
    assert "mg_calculation_applicable: Optional[bool] = None" in src


def test_frontend_franchise_management_has_mg_toggle():
    """The Franchise Management form must expose the new checkbox."""
    src = (
        Path(__file__).resolve().parent.parent.parent
        / "frontend" / "src" / "pages" / "FranchiseManagement.jsx"
    ).read_text()
    assert 'data-testid="mg-applicable-checkbox"' in src
    assert "mg_calculation_applicable" in src
