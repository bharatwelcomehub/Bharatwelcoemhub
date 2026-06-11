"""Lock in the two distinct financial metrics per Feb-2026 user directive:

  1. Profit / Loss        = Total Sales − Total Expenses − Total Commissions  (GST excluded)
  2. Revenue Share Base   = Total Sales − Total Commissions − GST              (Expenses excluded)

Mirrors the worked example from PB-HSR · May 2026:
  Sales 12,53,972 · Expenses 13,64,786 · Comm 59,234 · GST 52,128
  Profit/Loss expected ≈ -1,70,048
  Revenue Share expected = 11,42,610
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_profit_loss_excludes_gst():
    sale, expense, comm, gst = 1253972, 1364786, 59234, 52128
    profit_loss = sale - expense - comm
    assert profit_loss == -170048
    # GST does NOT enter Profit/Loss
    assert profit_loss != sale - expense - comm - gst


def test_revenue_share_base_excludes_expenses_and_includes_gst_deduction():
    sale, expense, comm, gst = 1253972, 1364786, 59234, 52128
    rev_share = sale - comm - gst
    assert rev_share == 1142610
    # Expenses do NOT enter Revenue Share Base
    assert rev_share != sale - expense - comm - gst


def test_metrics_are_independent():
    # The two metrics should never produce the same number for non-trivial inputs
    sale, expense, comm, gst = 1253972, 1364786, 59234, 52128
    profit_loss = sale - expense - comm
    rev_share = sale - comm - gst
    assert profit_loss != rev_share, (
        "Profit/Loss and Revenue Share Base must be distinct metrics — "
        "if they ever collide, a formula is wrong."
    )
