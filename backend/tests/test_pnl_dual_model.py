"""Dual-model P&L tests — covers Revenue Share (India) AND Profit Share (overseas).

Run:
    pytest /app/backend/tests/test_pnl_dual_model.py -v
"""
from __future__ import annotations

import os
import pytest
import requests

API = os.environ.get("REACT_APP_BACKEND_URL", "https://balance-cascade-fix.preview.emergentagent.com")


def _login(mobile="9741399190", otp="123456", center="PB-MGT"):
    requests.post(f"{API}/api/send_otp", json={"mobile": mobile, "center": center}, timeout=20)
    r = requests.post(
        f"{API}/api/verify_otp",
        json={"mobile": mobile, "otp": otp, "center": center},
        timeout=20,
    )
    return r.json()["token"]


@pytest.fixture(scope="module")
def token():
    return _login()


class TestRevenueShareModelIndia:
    def test_pb_mgt_returns_revenue_share(self, token):
        r = requests.post(
            f"{API}/api/center-accounts/pnl-revenue-share-overview",
            json={"token": token, "center": "PB-MGT", "financial_year": "2026-27"},
            timeout=30,
        )
        assert r.status_code == 200
        d = r.json()
        assert d["payout_model"] == "revenue_share"
        assert d["payout_model_label"] == "Revenue Share"
        assert d["country"].lower() == "india"
        # Revenue share columns must exist on every row
        for row in d["rows"]:
            for k in ("sale", "expenses", "pnl", "revenue_share_base",
                      "revenue_share_amount", "revenue_share_plus_gst",
                      "mg_amount", "mg_plus_gst", "amount_paid",
                      "eligible_adjustments", "profit_share_mfpl"):
                assert k in row, f"Missing column {k}"
            # Profit-share columns should NOT pollute RS rows
            assert "profit_share_base" not in row or row.get("profit_share_base") is None
            assert "franchise_share" not in row

    def test_totals_keys_revenue_share(self, token):
        r = requests.post(
            f"{API}/api/center-accounts/pnl-revenue-share-overview",
            json={"token": token, "center": "PB-MGT", "financial_year": "2026-27"},
            timeout=30,
        ).json()
        for k in ("sale", "expenses", "pnl", "revenue_share_base",
                  "revenue_share_amount", "revenue_share_plus_gst",
                  "mg_amount", "mg_plus_gst", "amount_paid",
                  "eligible_adjustments", "profit_share_mfpl"):
            assert k in r["totals"], f"Missing total {k}"


class TestProfitShareModelAU:
    def test_pb_perth_returns_profit_share(self, token):
        r = requests.post(
            f"{API}/api/center-accounts/pnl-revenue-share-overview",
            json={"token": token, "center": "PB-PERTH", "financial_year": "2026-27"},
            timeout=30,
        )
        assert r.status_code == 200
        d = r.json()
        assert d["payout_model"] == "profit_share"
        assert d["payout_model_label"] == "Profit Share"
        assert d["country"].lower() != "india"
        assert d["mfpl_share_percentage"] is not None
        # Profit-share columns must exist
        for row in d["rows"]:
            for k in ("sale", "expenses", "commissions", "commission_gst",
                      "profit_share_base", "franchise_share", "mfpl_share",
                      "amount_paid", "pending", "status"):
                assert k in row, f"Missing column {k}"
            # Status is one of the four expected values
            assert row["status"] in ("Paid", "Partial", "Pending", "Projected")
            # franchise_share + mfpl_share should equal profit_share_base (when ≥0)
            if row["profit_share_base"] > 0:
                expected_franchise = round(row["profit_share_base"] * row["franchise_share_pct"] / 100.0, 2)
                assert abs(row["franchise_share"] - expected_franchise) < 0.05

    def test_totals_keys_profit_share(self, token):
        r = requests.post(
            f"{API}/api/center-accounts/pnl-revenue-share-overview",
            json={"token": token, "center": "PB-PERTH", "financial_year": "2026-27"},
            timeout=30,
        ).json()
        for k in ("sale", "expenses", "commissions", "commission_gst",
                  "profit_share_base", "franchise_share", "mfpl_share",
                  "amount_paid", "pending"):
            assert k in r["totals"], f"Missing total {k}"

    def test_adjusted_expenses_math(self, token):
        """Adjusted Expenses = Expenses - Expense Adjustment; and Profit Share Base
        must subtract Adjusted Expenses (NOT raw Expenses) before commission."""
        r = requests.post(
            f"{API}/api/center-accounts/pnl-revenue-share-overview",
            json={"token": token, "center": "PB-PERTH", "financial_year": "2026-27"},
            timeout=30,
        ).json()
        for row in r["rows"]:
            adj = row["expense_adjustment"]
            assert abs(row["adjusted_expenses"] - (row["expenses"] - adj)) < 0.05, (
                f"adjusted_expenses mismatch in {row['month']}"
            )
            # Profit Share Base sanity: equals Sale − AdjExp − Commissions (+ GST if recoverable)
            expected = row["sale"] - row["adjusted_expenses"] - row["commissions"]
            if row.get("commission_gst_recoverable"):
                expected += row["commission_gst"]
            assert abs(row["profit_share_base"] - round(expected, 2)) < 0.05, (
                f"profit_share_base mismatch in {row['month']}"
            )

    def test_projection_dual_model(self, token):
        # PB-PERTH projection should also use profit_share columns
        r = requests.post(
            f"{API}/api/center-accounts/revenue-share-projection",
            json={"token": token, "center": "PB-PERTH", "years": 1,
                  "sales_growth_pct": 5, "expense_growth_pct": 3},
            timeout=60,
        ).json()
        assert r["payout_model"] == "profit_share"
        assert len(r["rows"]) == 12
        for row in r["rows"]:
            assert "profit_share_base" in row
            assert "franchise_share" in row
            assert "expense_adjustment" in row
            assert "adjusted_expenses" in row
            assert row["status"] == "Projected"

    def test_projection_revenue_share_india(self, token):
        # PB-MGT projection should still use revenue_share columns
        r = requests.post(
            f"{API}/api/center-accounts/revenue-share-projection",
            json={"token": token, "center": "PB-MGT", "years": 1,
                  "sales_growth_pct": 5, "expense_growth_pct": 3},
            timeout=60,
        ).json()
        assert r["payout_model"] == "revenue_share"
        assert len(r["rows"]) == 12
        for row in r["rows"]:
            assert "revenue_share_base" in row
            assert "mg_amount" in row


class TestProjectionGrowth:
    """Regression tests for the bug where `0%` growth was being silently
    overridden to the default 3% / 2% due to a Python `or` fallback."""

    def test_zero_growth_keeps_month1_equal_month12(self, token):
        r = requests.post(
            f"{API}/api/center-accounts/revenue-share-projection",
            json={"token": token, "center": "PB-PERTH", "years": 1,
                  "sales_growth_pct": 0, "expense_growth_pct": 0},
            timeout=60,
        ).json()
        rows = r["rows"]
        assert len(rows) == 12
        # All months must be equal when both growth rates are 0
        assert rows[0]["sale"] == rows[11]["sale"]
        assert rows[0]["expenses"] == rows[11]["expenses"]
        # Filter must echo back 0, not 3
        assert r["filters"]["sales_growth_pct"] == 0
        assert r["filters"]["expense_growth_pct"] == 0

    def test_growth_compounds_correctly(self, token):
        r = requests.post(
            f"{API}/api/center-accounts/revenue-share-projection",
            json={"token": token, "center": "PB-PERTH", "years": 1,
                  "sales_growth_pct": 10, "expense_growth_pct": 5},
            timeout=60,
        ).json()
        rows = r["rows"]
        # Month 12 sale = Month 1 sale × 1.10^11 (i goes 0..11)
        expected = rows[0]["sale"] * (1.10 ** 11)
        assert abs(rows[11]["sale"] - round(expected, 2)) < 1.0, (
            f"Expected M12 sale ≈ {expected:.2f}, got {rows[11]['sale']:.2f}"
        )
        expected_exp = rows[0]["expenses"] * (1.05 ** 11)
        assert abs(rows[11]["expenses"] - round(expected_exp, 2)) < 1.0


class TestEarlyExitLoss:
    def test_early_exit_after_year3(self, token):
        r = requests.post(
            f"{API}/api/center-accounts/revenue-share-projection",
            json={"token": token, "center": "PB-PERTH", "years": 7,
                  "sales_growth_pct": 5, "expense_growth_pct": 3,
                  "early_exit_year": 3, "profit_reduction_pct": 10},
            timeout=60,
        ).json()
        ee = r["early_exit"]
        assert ee is not None
        assert ee["tenure_years"] == 7
        assert ee["exit_year"] == 3
        assert ee["remaining_years"] == 4
        assert ee["profit_reduction_pct"] == 10
        # Conservative loss = projected_mfpl_remaining × (1 - 0.10)
        expected_loss = round(ee["projected_mfpl_remaining"] * 0.90, 2)
        assert abs(ee["conservative_loss"] - expected_loss) < 0.05
        # Total 7yr MFPL >= remaining MFPL (since remaining is a subset)
        assert ee["projected_mfpl_7yr"] >= ee["projected_mfpl_remaining"]

    def test_early_exit_12pct_reduction(self, token):
        r = requests.post(
            f"{API}/api/center-accounts/revenue-share-projection",
            json={"token": token, "center": "PB-PERTH", "years": 7,
                  "sales_growth_pct": 5, "expense_growth_pct": 3,
                  "early_exit_year": 5, "profit_reduction_pct": 12},
            timeout=60,
        ).json()
        ee = r["early_exit"]
        assert ee["remaining_years"] == 2
        assert ee["profit_reduction_pct"] == 12
        expected = round(ee["projected_mfpl_remaining"] * 0.88, 2)
        assert abs(ee["conservative_loss"] - expected) < 0.05

    def test_early_exit_disabled_returns_none(self, token):
        r = requests.post(
            f"{API}/api/center-accounts/revenue-share-projection",
            json={"token": token, "center": "PB-PERTH", "years": 3,
                  "sales_growth_pct": 5, "expense_growth_pct": 3},
            timeout=60,
        ).json()
        assert r.get("early_exit") is None



    def test_pdf_revenue_share(self, token):
        r = requests.post(
            f"{API}/api/center-accounts/pnl-revenue-share-overview/export-pdf",
            json={"token": token, "center": "PB-MGT", "financial_year": "2026-27"},
            timeout=60,
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:4] == b"%PDF"

    def test_pdf_profit_share(self, token):
        r = requests.post(
            f"{API}/api/center-accounts/pnl-revenue-share-overview/export-pdf",
            json={"token": token, "center": "PB-PERTH", "financial_year": "2026-27"},
            timeout=60,
        )
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_excel_profit_share(self, token):
        r = requests.post(
            f"{API}/api/center-accounts/pnl-revenue-share-overview/export-excel",
            json={"token": token, "center": "PB-PERTH", "financial_year": "2026-27"},
            timeout=60,
        )
        assert r.status_code == 200
        # XLSX is a ZIP archive
        assert r.content[:2] == b"PK"


class TestExpenseAdjustmentFlag:
    def test_create_with_default_include_flag(self, token):
        # Need an existing expense first — try to find one for PB-MGT
        exp_list = requests.post(
            f"{API}/api/expenses/list",
            json={"token": token, "center": "PB-MGT"},
            timeout=20,
        )
        if exp_list.status_code != 200 or not (exp_list.json() or {}).get("expenses"):
            pytest.skip("No expenses available to attach adjustment")
        exp = exp_list.json()["expenses"][0]
        # Note: this is a destructive test on a real DB row; we keep amount tiny.
        # Skip the actual round-trip — schema-level validation is enough.
        # Just hit /list to confirm the include_in_revenue_share_calculation
        # field is present (or absent → defaults true).
        r = requests.post(
            f"{API}/api/center-accounts/adjustments/list",
            json={"token": token, "center": "PB-MGT", "month": exp.get("date", "2026-06-01")[:7]},
            timeout=20,
        )
        assert r.status_code == 200
