"""Regression: Section 7 PIB "Revenue Share Calculation" MUST use
Revenue Share Base (Sales − Commissions − GST) — NOT plain Net Revenue
(Sales − Commissions, GST informational).

Re-confirmed by owner after Dombivali (PB-DV) Section 7 showed
Rs. 1,061,345 (= Sale − Commission) instead of Rs. 1,013,147 (= Sale −
Commission − GST). The franchise-owner 15% share must therefore be
calculated on the GST-deducted base.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.gst import compute_net_revenue, compute_revenue_share_base


# Dombivali (PB-DV) · 2026-05 — values pulled from the PDF the user shared.
DV_SALE = 1088002.00
DV_COMM = 26656.96
DV_GST = 48197.67
EXPECTED_SHARE_BASE = 1013147.37  # Sale − Commission − GST (Section 4 canonical)
EXPECTED_NET_REVENUE = 1061345.04  # Sale − Commission only (legacy buggy base)


def test_compute_revenue_share_base_subtracts_gst_for_india():
    base = compute_revenue_share_base(DV_SALE, DV_COMM, DV_GST, "India")
    assert base == EXPECTED_SHARE_BASE, (
        f"Revenue Share Base must subtract GST; got {base}, expected {EXPECTED_SHARE_BASE}"
    )


def test_compute_net_revenue_intentionally_ignores_gst_for_india():
    """`compute_net_revenue` is the management Net Revenue helper — by
    Feb-2026 directive it intentionally ignores GST. Section 7 must NOT
    use this helper."""
    nr = compute_net_revenue(DV_SALE, DV_COMM, DV_GST, 0, "India")
    assert nr == EXPECTED_NET_REVENUE, (
        f"Net Revenue (management) excludes GST; got {nr}, expected {EXPECTED_NET_REVENUE}"
    )


def test_section_7_must_not_call_compute_net_revenue_for_share_split():
    """Hard guard — the share-calculation block for India must use
    `compute_revenue_share_base`, NOT `compute_net_revenue`. If a future
    refactor reintroduces the wrong helper, this test trips."""
    src = (Path(__file__).resolve().parent.parent / "routes" / "center_accounts.py").read_text()

    # Locate the India share-split block.
    idx = src.find("if country == \"India\":")
    assert idx >= 0, "Could not locate the India share-split block"
    # Grab the next 40 lines as the block under test.
    block = "\n".join(src[idx:].splitlines()[:40])

    assert "compute_revenue_share_base(" in block, (
        "India share-split must call compute_revenue_share_base() — "
        "found compute_net_revenue() (or no helper at all), which would "
        "skip the GST deduction and reproduce the Section 7 bug."
    )


def test_franchise_owner_share_uses_gst_deducted_base():
    """End-to-end math: 15% × Revenue Share Base."""
    base = compute_revenue_share_base(DV_SALE, DV_COMM, DV_GST, "India")
    franchise_owner_share = round(base * 0.15, 2)
    # 15% of 1,013,147.37 = 151,972.11 (NOT 159,201.76, which was the bug)
    assert franchise_owner_share == 151972.11, (
        f"Owner share must be 15% of GST-deducted base; got {franchise_owner_share}"
    )
    # Sanity: the buggy result must differ
    buggy = round((DV_SALE - DV_COMM) * 0.15, 2)
    assert franchise_owner_share != buggy, (
        "Fix did not change the result — share is still being computed on the pre-GST base"
    )
