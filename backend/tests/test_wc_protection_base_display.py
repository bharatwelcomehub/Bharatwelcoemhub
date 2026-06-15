"""Regression: under WC Protection Mode, the base displayed in Section 7
(both PIB and Center Accounts) must equal the base the franchise owner /
company shares were actually computed against (operational_balance,
clamped to 0). Otherwise users see the visual inconsistency reported
on 2026-06-15 PIB Report Preview for PB-SN · 2026-05:

  Revenue Share Base   Rs. 13,60,891.94   ← OLD (wrong: regular base)
  Franchise Owner 10%  Rs.    24,285.58   ← 10% of 2,42,855 (OB), not 13.6L
  Manaswini       90%  Rs.   218,570.20   ← 90% of 2,42,855

The fix: when `protection_mode=True`, set `net_revenue_for_share` to
`max(0, operational_balance)` and surface a clearer `base_label`.
"""
from __future__ import annotations
import io

from utils.pdf_generator import build_pib_pdf


def _stub_summary_wc_protection() -> dict:
    """Mirror PB-SN-like protection-mode payload: regular Revenue Share Base
    is 13.6L but operational balance is only 2.42L → shares should be
    computed off 2.42L and the displayed base should also be 2.42L."""
    operational_balance = 242856.0
    owner_pct = 10.0
    company_pct = 90.0
    owner_share = round(operational_balance * owner_pct / 100.0, 2)
    company_share = round(operational_balance * company_pct / 100.0, 2)
    return {
        "center": "PB-SN", "center_name": "Test Center", "country": "India",
        "period": "2026-05",
        "franchise": {"code": "FR-TEST", "name": "Test", "legal_entity": "Test Pvt Ltd", "linked": True},
        "sales": {"total_sale": 1460641.0, "direct_sale": 0, "aggregator_sale": 0,
                  "swiggy": 0, "zomato": 0, "doordash": 0, "card_sale": 0,
                  "bharat_pay": 0, "online_other": 0, "total_online_sale": 0,
                  "total_cash_sale": 0, "num_days": 31},
        "expenses": {"total": 1183342.0, "by_category": {}},
        "commissions": {"total": 34443.0, "total_with_gst": 34443.0, "by_platform": {}},
        "financial_summary": {
            "total_sales": 1460641.0, "sales_gst": 65306.0, "commission_gst": 0,
            "total_commissions": 34443.0, "total_commissions_with_gst": 34443.0,
            "total_expenses": 1183342.0,
            "net_revenue": 1426198.0, "profitability": 242856.0,
            "working_capital": 100000.0, "loans_outstanding": 0,
            "working_capital_available": 49000.0,
            "wc_standing": {"opening_wc": 100000, "closing_wc": 49000,
                            "revenue_share_active": False,
                            "base_wc": 100000, "wc_floor": 50000,
                            "monthly_recovery_cap": 0, "ytd_recovered": 0},
        },
        # Section 7 must show the OB-based base (operational_balance) and
        # the post-fix `base_label` clarifies the gating.
        "share_calculation": {
            "type": "revenue_share",
            "net_profit_or_sales": operational_balance,
            "total_sales": 1460641.0, "total_deductions": 0,
            "wc_gated": True,
            "wc_status": "protection",
            "franchise_owner": {"percentage": owner_pct, "amount": owner_share},
            "purnabramha": {"percentage": company_pct, "base_amount": company_share,
                            "cgst": 0, "sgst": 0, "gst_amount": 0,
                            "total_payable": company_share, "gst_applicable": True},
        },
        "mg_calculation": None, "mg_calculation_applicable": True,
        "payout_model": "revenue_share", "payout_model_label": "Revenue Share",
        "section_heading": "REVENUE SHARE CALCULATION",
        "base_label": "Operational Balance (Base under WC Protection)",
        "engine": {
            "payout_model": "revenue_share",
            "revenue_share_base": 1360891.94, "profit_share_base": 242856.0,
            "selected_base": operational_balance,
            "base_label": "Operational Balance (Base under WC Protection)",
            "owner_pct": owner_pct, "company_pct": company_pct,
            "owner_share": owner_share, "company_share": company_share,
            "company_entity_label": "Manaswini Foods Pvt Ltd Share",
            "adjustments": {"wc_adjustments": 0, "manual_adjustments": 0},
        },
        "overseas_share": None, "mfpl_royalty": None,
        "operational_sustainability": {
            "revenue_share_base": 1360891.94, "profit_loss": 242856.0,
            "operational_balance": operational_balance,
            "wc_safe": False, "status": "protection",
        },
        "loans_taken": [], "loans_given": [], "loan_repayments": [],
        "payout": {
            "operational_balance": operational_balance,
            "amount": owner_share, "type": "revenue_share_protection",
            "reason": "Protection Mode: Revenue Share on Operational Balance only.",
            "mg_amount": 0, "revenue_share_amount": owner_share,
            "protection_mode": True,
            "protection_gating_applied": True,
            "protection_gating_available": True,
        },
        "tax_rules": {
            "country": "India", "share_gst_rate": 18.0,
            "sales_gst_rate": 5.0, "commission_gst_rate": 0.0,
            "rationale": "India: GST 18% on share; 5% on sales.",
            "applicable_taxes": {"gst_on_sales": "5%", "gst_on_share": "18%"},
        },
    }


def _pdf_text(pdf_bytes: bytes) -> str:
    from pdfminer.high_level import extract_text
    return extract_text(io.BytesIO(pdf_bytes))


def test_pib_wc_protection_base_matches_displayed_share_math():
    """PIB Section 7 under WC Protection must show:
        - Base label = 'Operational Balance (Base under WC Protection)'
        - Base value = operational_balance (2,42,856), NOT regular base (13,60,891)
        - 10% × base = displayed owner share
    """
    pdf = build_pib_pdf(_stub_summary_wc_protection())
    text = _pdf_text(pdf)
    # The base row must surface the protection-aware label + the OB value.
    assert "Operational Balance (Base under WC Protection)" in text, \
        f"Base label not updated under WC Protection. PDF text: {text[:500]}"
    assert "242,856.00" in text or "242,855" in text, \
        f"Operational balance not surfaced as the base value. PDF text: {text[:500]}"
    # The regular 13,60,891 should NOT be the Section 7 base (it should still
    # appear elsewhere — Section 5 Operational Sustainability — but not as
    # the "Base for Calculation" in Section 7).
    # Looser check: Section 7 base row should have OB, not regular base.
    section7_idx = text.find("REVENUE SHARE CALCULATION")
    assert section7_idx >= 0
    section7_block = text[section7_idx:section7_idx + 1500]
    assert "242,856" in section7_block, \
        f"Section 7 should reference OB. Got: {section7_block[:500]}"


def test_pib_wc_protection_section_title_still_indicates_closure():
    """Section 7 title should still say *** CLOSED - WC BELOW 50% ***
    so users immediately see why the base is gated."""
    pdf = build_pib_pdf(_stub_summary_wc_protection())
    text = _pdf_text(pdf)
    assert "*** CLOSED" in text, f"WC closure marker missing. Text: {text[:500]}"
    assert "WC BELOW 50%" in text, f"WC threshold marker missing. Text: {text[:500]}"



def test_pib_wc_protection_formula_visible_on_each_share_row():
    """Section 7 must show the formula '10% × Rs. 2,42,856.00' on the
    Franchise Owner row and '90% × Rs. 2,42,856.00' on the Manaswini row,
    so users can verify the math at a glance (the Feb-2026 PB-SN complaint
    was that 24,285.58 didn't look like 10% of 13,60,891.94 — they didn't
    realise WC Protection had gated the base)."""
    pdf = build_pib_pdf(_stub_summary_wc_protection())
    text = _pdf_text(pdf)
    # Franchise Owner row: must show "10% × Rs. 2,42,856" formula
    assert "10.0% ×" in text or "10% ×" in text, \
        f"Owner-share formula missing. Text: {text[:1000]}"
    # Manaswini row: must show "90% × Rs. 2,42,856" formula
    assert "90.0% ×" in text or "90% ×" in text, \
        f"Company-share formula missing. Text: {text[:1000]}"
    # Both formulas must reference the gated base (2,42,856), NOT the
    # regular Revenue Share Base (13,60,891).
    section7_idx = text.find("REVENUE SHARE CALCULATION")
    section7_block = text[section7_idx:section7_idx + 1500]
    assert "242,856" in section7_block, \
        f"Formula must reference the gated base 242,856. Section 7: {section7_block[:600]}"


def test_pib_wc_protection_includes_explainer_note():
    """A plain-English note must appear right under the Section 7 heading
    explaining WHY the base differs from the gross Revenue Share Base shown
    in Section 5. Without this note users assume the math is wrong."""
    pdf = build_pib_pdf(_stub_summary_wc_protection())
    text = _pdf_text(pdf)
    assert "Working Capital Protection" in text, \
        f"WC Protection explainer missing. Text: {text[:2000]}"
    assert "Operational Balance" in text and "gated" in text.lower(), \
        f"Explainer must mention gating. Text: {text[:2000]}"
