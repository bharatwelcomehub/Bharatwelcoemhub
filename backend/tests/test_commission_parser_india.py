"""Regression tests for India bank-statement formats (HDFC, IDFC, ICICI, Axis)
using the shared `_load_bank_statement_normalized` helper.

These tests use synthetic fixtures built in-memory because real bank exports
contain customer data. The shapes/headers reflect actual statement layouts.
"""
import pytest
import pandas as pd

from routes.commission_parser import _load_bank_statement_normalized, parse_cards


def _write_hdfc_xlsx(path):
    """HDFC India layout: Transaction Date | Particulars | Debit | Credit."""
    rows = [
        ['HDFC BANK LTD', '', '', '', ''],
        ['Account 12345', '', '', '', ''],
        ['', '', '', '', ''],
        ['Transaction Date', 'Particulars', 'Withdrawal Amt.', 'Debit', 'Credit'],
        ['01/05/2026', 'CARD PMT SETDT-01052026 RAZORPAY', None, None, 1200.50],
        ['02/05/2026', 'CARD PMT SETDT-02052026 PINELABS', None, None, 3500.25],
        ['03/05/2026', 'NEFT INWARD ABCD', None, None, 500.00],
        ['03/05/2026', 'ATM WITHDRAWAL', None, 1000.00, None],
    ]
    pd.DataFrame(rows).to_excel(path, header=False, index=False)


def _write_idfc_xlsx(path):
    """IDFC FIRST Bank layout: Date | Narration | Debit | Credit | Balance.
    Settlements usually appear as 'POS SETT' / 'EDC SETT' / 'MERCH SETT'."""
    rows = [
        ['IDFC FIRST BANK', '', '', '', '', ''],
        ['Account 7777', '', '', '', '', ''],
        ['', '', '', '', '', ''],
        ['Date', 'Narration', 'Debit', 'Credit', 'Balance', 'Ref No'],
        ['01/05/2026', 'EDC SETT EZETAP 12345', None, 2800.00, 10000.00, 'R1'],
        ['02/05/2026', 'POS SETT PINELABS', None, 4400.50, 14400.50, 'R2'],
        ['03/05/2026', 'UPI INWARD', None, 100.00, 14500.50, 'R3'],
        ['04/05/2026', 'ATM WDL', 500.00, None, 14000.50, 'R4'],
    ]
    pd.DataFrame(rows).to_excel(path, header=False, index=False)


def _write_icici_xlsx(path):
    """ICICI: Tran Date | Description | Debit Amount | Credit Amount layout."""
    rows = [
        ['ICICI BANK', '', '', ''],
        ['', '', '', ''],
        ['Tran Date', 'Description', 'Debit Amount', 'Credit Amount'],
        ['05/05/2026', 'MERCH SETT MSWIPE', None, 7200.00],
        ['06/05/2026', 'CARD SETT POS', None, 3300.00],
    ]
    pd.DataFrame(rows).to_excel(path, header=False, index=False)


def test_hdfc_bank_statement_parses(tmp_path):
    fp = tmp_path / "hdfc.xlsx"
    _write_hdfc_xlsx(fp)
    bn = _load_bank_statement_normalized(str(fp))
    assert bn["format"] == "hdfc"
    df = bn["df"]
    assert len(df) == 4
    assert df["credit"].sum() == pytest.approx(5200.75, abs=0.01)
    assert df["debit"].sum() == pytest.approx(1000.0, abs=0.01)
    # Card-settlement detection
    card_mask = df["particulars"].str.contains(r"CARD\s*PMT", case=False, regex=True)
    assert card_mask.sum() == 2


def test_idfc_bank_statement_parses(tmp_path):
    """IDFC uses 'Date'/'Narration'/'Debit'/'Credit' headers."""
    fp = tmp_path / "idfc.xlsx"
    _write_idfc_xlsx(fp)
    bn = _load_bank_statement_normalized(str(fp))
    assert bn["format"] == "hdfc"  # generic India layout family
    df = bn["df"]
    assert len(df) == 4
    # Settlement-line detection works for IDFC's POS/EDC SETT pattern
    card_mask = df["particulars"].str.contains(
        r"POS\s*SETT|EDC\s*SETT|MERCH\s*SETT", case=False, regex=True
    )
    assert card_mask.sum() == 2
    assert df.loc[card_mask, "credit"].sum() == pytest.approx(7200.50, abs=0.01)


def test_icici_bank_statement_parses(tmp_path):
    fp = tmp_path / "icici.xlsx"
    _write_icici_xlsx(fp)
    bn = _load_bank_statement_normalized(str(fp))
    assert bn["format"] == "hdfc"
    df = bn["df"]
    assert len(df) == 2
    card_mask = df["particulars"].str.contains(
        r"MERCH\s*SETT|CARD\s*SETT", case=False, regex=True
    )
    assert card_mask.sum() == 2


def test_idfc_cards_reconciliation_end_to_end(tmp_path):
    """Full Cards EDC + IDFC bank flow → MDR computation."""
    # Synthesize an HDFC-shape EDC (Date / Amount / Status)
    edc_rows = [
        ['Date', 'Amount', 'Status', 'Card Type'],
        ['01/05/2026', 1500.00, 'SETTLED', 'VISA'],
        ['01/05/2026', 1400.00, 'SETTLED', 'MASTERCARD'],
        ['02/05/2026', 4500.00, 'SETTLED', 'VISA'],
        ['02/05/2026', 100.00, 'FAILED',  'VISA'],
    ]
    edc_fp = tmp_path / "edc.xlsx"
    pd.DataFrame(edc_rows[1:], columns=edc_rows[0]).to_excel(edc_fp, index=False)

    bank_fp = tmp_path / "idfc.xlsx"
    _write_idfc_xlsx(bank_fp)

    r = parse_cards(str(edc_fp), str(bank_fp))
    rs = r["raw_summary"]
    assert r["currency"] == "INR"
    assert r["gross_amount"] == pytest.approx(7400.00, abs=0.01)  # 3 SETTLED txns
    assert rs["bank_format"] == "hdfc"  # IDFC parses under the generic-India branch
    # Bank credits for May 1-2 = 2800 + 4400.50 = 7200.50 → MDR ≈ gross − net
    assert rs["bank_settlements_matched"] >= 2
    assert r["net_payout"] <= r["gross_amount"]
