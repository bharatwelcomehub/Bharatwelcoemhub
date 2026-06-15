"""Regression: PIB report must strictly honour the Single Financial
Engine's `payout_model`. A Revenue-Share franchise must never surface
"Profit Share" labels and vice-versa.

Covers the 3 bug reports from Feb-2026 post-Phase-3 stabilisation:
  1. Section 7 heading reflects the model.
  2. Section 8 "Franchise Owner Revenue/Profit Share" label flips.
  3. Section 8B title + base label flip with the model.
"""
from __future__ import annotations
import io

from utils.pdf_generator import build_pib_pdf


def _stub_summary(payout_model: str) -> dict:
    """Minimal `summary` payload the PIB builder accepts. Mirrors the
    shape produced by `routes/center_accounts.get_center_account_summary`
    just enough to exercise Sections 7, 8 and 8B."""
    is_ps = payout_model == "profit_share"
    return {
        "center": "PB-HSR",
        "center_name": "Test Center",
        "country": "India",
        "period": "2025-12",
        "franchise": {"code": "FR-TEST", "name": "Test", "legal_entity": "Test Pvt Ltd", "linked": True},
        "sales": {"total_sale": 100000.0, "direct_sale": 0, "aggregator_sale": 0,
                  "swiggy": 0, "zomato": 0, "doordash": 0, "card_sale": 0,
                  "bharat_pay": 0, "online_other": 0, "total_online_sale": 0,
                  "total_cash_sale": 0, "num_days": 30},
        "expenses": {"total": 20000.0, "by_category": {}},
        "commissions": {"total": 5000.0, "total_with_gst": 5000.0, "by_platform": {}},
        "financial_summary": {
            "total_sales": 100000.0, "sales_gst": 5000.0, "commission_gst": 0,
            "total_commissions": 5000.0, "total_commissions_with_gst": 5000.0,
            "total_expenses": 20000.0,
            "net_revenue": 90000.0, "profitability": 70000.0,
            "working_capital": 100000.0, "loans_outstanding": 0,
            "working_capital_available": 100000.0,
            "wc_standing": {"opening_wc": 100000, "closing_wc": 100000, "revenue_share_active": True,
                            "base_wc": 100000, "wc_floor": 50000, "monthly_recovery_cap": 0, "ytd_recovered": 0},
        },
        "share_calculation": {
            "type": payout_model,
            "net_profit_or_sales": 70000.0 if is_ps else 90000.0,
            "total_sales": 100000.0,
            "total_deductions": 10000.0,
            "wc_gated": False,
            "wc_status": "active",
            "franchise_owner": {"percentage": 80 if is_ps else 15, "amount": 56000.0 if is_ps else 13500.0},
            "purnabramha": {"percentage": 20 if is_ps else 85, "base_amount": 14000.0 if is_ps else 76500.0,
                            "cgst": 0, "sgst": 0, "gst_amount": 0,
                            "total_payable": 14000.0 if is_ps else 76500.0, "gst_applicable": True},
        },
        "mg_calculation": None,
        "mg_calculation_applicable": False,
        "payout_model": payout_model,
        "payout_model_label": "Profit Share" if is_ps else "Revenue Share",
        "section_heading": "PROFIT SHARE CALCULATION" if is_ps else "REVENUE SHARE CALCULATION",
        "base_label": "Profit Share Base" if is_ps else "Revenue Share Base",
        "engine": {
            "payout_model": payout_model,
            "revenue_share_base": 90000.0,
            "profit_share_base": 70000.0,
            "selected_base": 70000.0 if is_ps else 90000.0,
            "base_label": "Profit Share Base" if is_ps else "Revenue Share Base",
            "owner_pct": 80 if is_ps else 15,
            "company_pct": 20 if is_ps else 85,
            "owner_share": 56000.0 if is_ps else 13500.0,
            "company_share": 14000.0 if is_ps else 76500.0,
            "company_entity_label": "Manaswini Foods Pvt Ltd Share",
            "adjustments": {"wc_adjustments": 0, "manual_adjustments": 0},
        },
        "overseas_share": None,
        "mfpl_royalty": None,
        "operational_sustainability": {"revenue_share_base": 90000.0, "profit_loss": 70000.0,
                                       "operational_balance": 70000.0, "wc_safe": True, "status": "active"},
        "loans_taken": [], "loans_given": [], "loan_repayments": [],
        "payout": {
            "operational_balance": 70000.0,
            "amount": 56000.0 if is_ps else 13500.0,
            "type": payout_model,
            "reason": f"{'Profit' if is_ps else 'Revenue'} Share owner share applied.",
            "mg_amount": 0,
            "revenue_share_amount": 56000.0 if is_ps else 13500.0,
            "protection_mode": False,
        },
        "tax_rules": {
            "country": "India",
            "share_gst_rate": 18.0,
            "sales_gst_rate": 5.0,
            "commission_gst_rate": 0.0,
            "rationale": "India: GST 18% on share; 5% on sales.",
            "applicable_taxes": {"gst_on_sales": "5%", "gst_on_share": "18%"},
        },
    }


def _pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from a PDF using pdfminer."""
    from pdfminer.high_level import extract_text
    return extract_text(io.BytesIO(pdf_bytes))


def test_pib_revenue_share_never_shows_profit_share_labels():
    pdf = build_pib_pdf(_stub_summary("revenue_share"))
    text = _pdf_text(pdf).upper()
    # Required sections.
    assert "7. REVENUE SHARE CALCULATION" in text
    assert "FRANCHISE OWNER REVENUE SHARE" in text
    assert "MANASWINI FOODS PVT LTD REVENUE SHARE" in text
    assert "8B. FINAL PAYOUT (REVENUE SHARE + GST)" in text
    assert "REVENUE SHARE PAYABLE" in text
    # Title brand name flips with model.
    assert "REVENUE & INCOME BALANCE REPORT" in text
    assert "PROFIT & INCOME BALANCE REPORT" not in text
    # Forbidden labels.
    assert "FRANCHISE OWNER PROFIT SHARE" not in text
    assert "MANASWINI FOODS PVT LTD PROFIT SHARE" not in text
    assert "8B. FINAL PAYOUT (PROFIT SHARE + GST)" not in text
    assert "PROFIT SHARE PAYABLE" not in text


def test_pib_profit_share_never_shows_revenue_share_payable_labels():
    pdf = build_pib_pdf(_stub_summary("profit_share"))
    text = _pdf_text(pdf).upper()
    # Required.
    assert "7. PROFIT SHARE CALCULATION" in text
    assert "FRANCHISE OWNER PROFIT SHARE" in text
    assert "MANASWINI FOODS PVT LTD PROFIT SHARE" in text
    assert "8B. FINAL PAYOUT (PROFIT SHARE + GST)" in text
    assert "PROFIT SHARE PAYABLE" in text
    # Title brand name flips with model.
    assert "PROFIT & INCOME BALANCE REPORT" in text
    assert "REVENUE & INCOME BALANCE REPORT" not in text
    # Forbidden specifically — Section 8/8B should NOT call the franchise
    # owner's row "Revenue Share" for a Profit-Share franchise. Generic
    # "REVENUE SHARE" mentions (e.g. ⭐ Operational Sustainability rev-share
    # base block) are allowed.
    assert "FRANCHISE OWNER REVENUE SHARE" not in text
    assert "MANASWINI FOODS PVT LTD REVENUE SHARE" not in text
    assert "8B. FINAL PAYOUT (REVENUE SHARE + GST)" not in text
    assert "REVENUE SHARE PAYABLE" not in text
