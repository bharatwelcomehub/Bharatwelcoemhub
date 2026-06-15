"""Regression tests for the single Financial Calculation Engine.

This module locks down the canonical formulas that every report / dashboard
in the platform must use. If a future change accidentally re-introduces
duplicate logic anywhere else, this suite will trip.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from utils.financial_engine import (
    REVENUE_SHARE,
    PROFIT_SHARE,
    default_payout_model_for_country,
    normalize_model,
    compute_revenue_share_base,
    compute_profit_share_base,
    compute_franchise_payout,
)


# ----------------------------------------------------------------------
# Defaults & model normalisation
# ----------------------------------------------------------------------
def test_default_model_india_is_revenue_share():
    assert default_payout_model_for_country("India") == REVENUE_SHARE


def test_default_model_australia_is_profit_share():
    assert default_payout_model_for_country("Australia") == PROFIT_SHARE
    assert default_payout_model_for_country("USA") == PROFIT_SHARE


def test_normalize_model_accepts_supported_values():
    assert normalize_model("revenue_share", "India") == REVENUE_SHARE
    assert normalize_model("Profit Share", "India") == PROFIT_SHARE
    assert normalize_model("PROFIT_SHARE", "India") == PROFIT_SHARE


def test_normalize_model_falls_back_to_country_default():
    assert normalize_model(None, "India") == REVENUE_SHARE
    assert normalize_model("", "Australia") == PROFIT_SHARE
    assert normalize_model("garbage", "India") == REVENUE_SHARE


# ----------------------------------------------------------------------
# Base formulas
# ----------------------------------------------------------------------
def test_revenue_share_base_deducts_gst_and_commission():
    # Dombivali 2026-05 canonical numbers
    assert compute_revenue_share_base(1088002.00, 26656.96, 48197.67) == 1013147.37


def test_profit_share_base_deducts_expenses_and_adjustments():
    base = compute_profit_share_base(
        sales=1_000_000,
        commissions=50_000,
        expenses=600_000,
        wc_adjustments=10_000,
        manual_adjustments=5_000,
    )
    assert base == 335_000.0


# ----------------------------------------------------------------------
# Engine end-to-end — Revenue Share / MG OFF
# ----------------------------------------------------------------------
def test_revenue_share_model_no_mg_picks_owner_share():
    out = compute_franchise_payout(
        sales=1088002.00,
        commissions=26656.96,
        gst_on_sales=48197.67,
        expenses=0,
        payout_model=REVENUE_SHARE,
        franchise_owner_pct=15,
        mg_applicable=False,
        country="India",
    )
    assert out["section_heading"] == "REVENUE SHARE CALCULATION"
    assert out["base_label"] == "Revenue Share Base"
    assert out["revenue_share_base"] == 1013147.37
    assert out["owner_share"] == 151972.11
    assert out["company_share"] == 861175.26
    assert out["payable"] == 151972.11
    assert out["payable_type"] == REVENUE_SHARE
    assert "Manaswini" in out["company_entity_label"]


# ----------------------------------------------------------------------
# Engine end-to-end — Revenue Share / MG ON (MG wins)
# ----------------------------------------------------------------------
def test_revenue_share_model_mg_wins_when_higher():
    out = compute_franchise_payout(
        sales=1088002.00,
        commissions=26656.96,
        gst_on_sales=48197.67,
        expenses=0,
        payout_model=REVENUE_SHARE,
        franchise_owner_pct=15,
        mg_applicable=True,
        monthly_mg=200_000,
        country="India",
    )
    assert out["payable"] == 200_000
    assert out["payable_type"] == "minimum_guarantee"


# ----------------------------------------------------------------------
# Engine end-to-end — Profit Share
# ----------------------------------------------------------------------
def test_profit_share_model_uses_profit_base_and_pty_ltd_label():
    out = compute_franchise_payout(
        sales=1_000_000,
        commissions=50_000,
        gst_on_sales=0,
        expenses=600_000,
        wc_adjustments=10_000,
        manual_adjustments=5_000,
        payout_model=PROFIT_SHARE,
        franchise_owner_pct=80,
        mg_applicable=False,
        country="Australia",
    )
    assert out["section_heading"] == "PROFIT SHARE CALCULATION"
    assert out["base_label"] == "Profit Share Base"
    assert out["profit_share_base"] == 335_000
    assert out["owner_share"] == round(335_000 * 0.80, 2)
    assert out["company_share"] == round(335_000 * 0.20, 2)
    assert "Pty Ltd" in out["company_entity_label"]


# ----------------------------------------------------------------------
# WC Protection Mode — supersedes MG/RS regardless of model
# ----------------------------------------------------------------------
def test_wc_protection_caps_to_operational_balance():
    out = compute_franchise_payout(
        sales=1088002.00,
        commissions=26656.96,
        gst_on_sales=48197.67,
        expenses=0,
        payout_model=REVENUE_SHARE,
        franchise_owner_pct=15,
        mg_applicable=True,
        monthly_mg=200_000,
        operational_balance=80_000,
        protection_mode=True,
        country="India",
    )
    # gated = 80,000 × 15% = 12,000
    assert out["payable"] == 12_000
    assert out["payable_type"] == "revenue_share_protection"
    assert "WC Protection" in out["reason"]


def test_wc_protection_with_zero_balance_pays_zero():
    out = compute_franchise_payout(
        sales=1088002.00,
        commissions=26656.96,
        gst_on_sales=48197.67,
        expenses=0,
        payout_model=REVENUE_SHARE,
        franchise_owner_pct=15,
        mg_applicable=False,
        operational_balance=0,
        protection_mode=True,
        country="India",
    )
    assert out["payable"] == 0
    assert out["payable_type"] == "wc_protection_no_payout"


# ----------------------------------------------------------------------
# Source guards — no other module reimplements the formulas
# ----------------------------------------------------------------------
def test_pdf_generator_uses_engine_section_heading():
    src = (Path(__file__).resolve().parent.parent / "utils" / "pdf_generator.py").read_text()
    assert 'summary.get("section_heading")' in src or 'summary.get("base_label")' in src, (
        "pdf_generator must source Section 7 heading + base label from the "
        "engine payload (summary.section_heading / summary.base_label)."
    )


def test_center_accounts_route_imports_engine():
    src = (Path(__file__).resolve().parent.parent / "routes" / "center_accounts.py").read_text()
    assert "from utils.financial_engine import" in src
    assert "compute_franchise_payout" in src


def test_franchise_model_has_payout_model_and_owner_share_pct():
    src = (Path(__file__).resolve().parent.parent / "routes" / "franchises.py").read_text()
    assert "payout_model: Optional[str] = None" in src
    assert "franchise_owner_share_percentage: Optional[float] = None" in src
    # Mirror-write logic between legacy and new % field.
    assert "franchise_owner_share_percentage" in src
    assert "revenue_share_percentage" in src
