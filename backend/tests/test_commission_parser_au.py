"""Regression tests for the Australia commission parsers — DoorDash payout
summary, ANZ Worldline EDC + ANZ Business Essentials bank statement.

The three fixture files live alongside this test:
  • dd_au.xlsx        — DoorDash FINANCIAL_PAYOUT_SUMMARY May 2026 (4 payouts)
  • cards_au.xlsx     — ANZ Worldline Transactions list, 563 txns May 2026
  • bank_au.xlsx      — ANZ Business Essentials bank statement Apr-Jun 2026
"""
import os
import pytest
import pandas as pd

from routes.commission_parser import (
    parse_doordash,
    parse_cards,
    _load_bank_statement_normalized,
    _load_cards_edc,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures_au")
DD = os.path.join(FIXTURES, "dd_au.xlsx")
CARDS = os.path.join(FIXTURES, "cards_au.xlsx")
BANK = os.path.join(FIXTURES, "bank_au.xlsx")


@pytest.mark.skipif(not os.path.exists(DD), reason="DoorDash fixture not present")
def test_doordash_au_parse():
    r = parse_doordash(DD)
    assert r["currency"] == "AUD"
    assert r["order_count"] == 4
    assert r["gross_amount"] == pytest.approx(2163.21, abs=0.01)
    assert r["net_payout"] == pytest.approx(1222.29, abs=0.01)
    assert r["other_deductions"] == pytest.approx(940.92, abs=0.01)
    assert r["gst_tax_deductions"] == 0.0
    # Breakdown must be present
    rs = r["raw_summary"]
    assert rs["commission"] == pytest.approx(692.32, abs=0.01)
    assert rs["marketing_fees"] == pytest.approx(209.48, abs=0.01)


@pytest.mark.skipif(not os.path.exists(CARDS), reason="Cards fixture not present")
def test_cards_anz_edc_only():
    r = parse_cards(CARDS)
    assert r["currency"] == "AUD"
    assert r["raw_summary"]["edc_format"] == "anz"
    assert r["gross_amount"] == pytest.approx(35370.05, abs=0.5)
    # MDR comes from Surcharge column
    assert r["other_deductions"] == pytest.approx(380.31, abs=0.5)
    assert r["net_payout"] == pytest.approx(34989.74, abs=0.5)
    assert r["order_count"] == 542


@pytest.mark.skipif(not (os.path.exists(CARDS) and os.path.exists(BANK)),
                    reason="Cards or bank fixture not present")
def test_cards_anz_with_bank_reconciliation():
    r = parse_cards(CARDS, BANK)
    rs = r["raw_summary"]
    assert r["currency"] == "AUD"
    assert rs["bank_format"] == "anz"
    assert rs["edc_format"] == "anz"
    assert r["gross_amount"] == pytest.approx(35370.05, abs=0.5)
    # MDR prefers the EDC surcharge column when present
    assert rs["mdr_source"] == "edc_surcharge_column"
    assert r["other_deductions"] == pytest.approx(380.31, abs=0.5)
    assert rs["bank_settlements_matched"] >= 30
    assert rs["bank_statement_uploaded"] is True


@pytest.mark.skipif(not os.path.exists(BANK), reason="Bank fixture not present")
def test_anz_bank_statement_normalisation():
    bn = _load_bank_statement_normalized(BANK)
    assert bn["format"] == "anz"
    df = bn["df"]
    assert len(df) > 200  # ANZ statement parses ~300+ rows
    # Date range spans April → June 2026
    assert df["date"].min() <= pd.Timestamp("2026-04-30")
    assert df["date"].max() >= pd.Timestamp("2026-06-01")
    # Card settlement rows recognisable
    mask = df["particulars"].str.contains(
        r"ANZ\s*WORLDLINE|AMEX\s*GR", case=False, regex=True, na=False
    )
    assert mask.sum() >= 30, "Expected at least 30 card-settlement entries"


@pytest.mark.skipif(not os.path.exists(CARDS), reason="Cards fixture not present")
def test_anz_cards_edc_loader_dynamic_header():
    """Header is on row 5 in ANZ Worldline export, not row 0."""
    edc = _load_cards_edc(CARDS)
    assert edc["format"] == "anz"
    assert edc["currency"] == "AUD"
    assert "Gross amount" in edc["df"].columns
    assert "Status" in edc["df"].columns
    assert edc["amount_col"] == "Gross amount"
