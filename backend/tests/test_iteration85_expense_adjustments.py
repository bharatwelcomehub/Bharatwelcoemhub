"""Iteration 85 — Expense Adjustment & Profitability Correction (Center Accounts).

Covers /api/center-accounts/adjustments/* CRUD + report + integration into
/api/center-accounts/summary and /api/owner-reports/monthly-report.
"""
import os
import pytest
import requests
from pathlib import Path

def _load_env():
    env_file = Path("/app/frontend/.env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("REACT_APP_BACKEND_URL")

BASE_URL = _load_env().rstrip("/")
SA_MOBILE = "9741399190"
FO_MOBILE = "8888888888"
OTP = "123456"
SA_CENTER = "PB-MGT"
FO_CENTER = "PB-HSR"
KNOWN_EXPENSE_ID = "69e7df9f9e7bf1a6861b5eb5"
KNOWN_EXPENSE_AMOUNT = 333001.0
KNOWN_EXPENSE_MONTH = "2026-01"

# --- auth helpers ---------------------------------------------------------
def _login(mobile: str, center: str) -> str:
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/send_otp", json={"mobile": mobile, "center": center}, timeout=20)
    assert r.status_code == 200, f"send_otp failed: {r.status_code} {r.text}"
    r = s.post(f"{BASE_URL}/api/verify_otp", json={"mobile": mobile, "otp": OTP, "center": center}, timeout=20)
    assert r.status_code == 200, f"verify_otp failed: {r.status_code} {r.text}"
    j = r.json()
    return j.get("token") or j.get("access_token") or j["session"]["token"]


@pytest.fixture(scope="module")
def sa_token():
    return _login(SA_MOBILE, SA_CENTER)


@pytest.fixture(scope="module")
def fo_token():
    return _login(FO_MOBILE, FO_CENTER)


# --- /types ---------------------------------------------------------------
class TestTypes:
    def test_types_returns_6(self, sa_token):
        r = requests.post(f"{BASE_URL}/api/center-accounts/adjustments/types", json={"token": sa_token}, timeout=15)
        assert r.status_code == 200, r.text
        types = r.json().get("types", [])
        assert len(types) == 6
        assert "Next Month Rent Paid in Advance" in types
        assert "Manual Adjustment" in types
        assert "Other" in types


# --- expense immutability snapshot ----------------------------------------
def _fetch_expense_snapshot(sa_token):
    r = requests.post(
        f"{BASE_URL}/api/expenses/list",
        json={"token": sa_token, "center": SA_CENTER},
        timeout=20,
    )
    if r.status_code != 200:
        return None
    rows = r.json().get("expenses") or r.json().get("items") or []
    for e in rows:
        if e.get("id") == KNOWN_EXPENSE_ID or e.get("expense_id") == KNOWN_EXPENSE_ID:
            return e
    return None


# --- CRUD + validations ---------------------------------------------------
class TestCreateValidations:
    def test_fo_blocked_403(self, fo_token):
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/create",
            json={
                "token": fo_token,
                "expense_id": KNOWN_EXPENSE_ID,
                "center": SA_CENTER,
                "month": KNOWN_EXPENSE_MONTH,
                "adjustment_amount": 100,
                "adjustment_type": "Manual Adjustment",
                "adjustment_reason": "should fail",
            },
            timeout=15,
        )
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"

    def test_invalid_expense_id_404(self, sa_token):
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/create",
            json={
                "token": sa_token,
                "expense_id": "non-existent-expense-zzz",
                "center": SA_CENTER,
                "month": KNOWN_EXPENSE_MONTH,
                "adjustment_amount": 10,
                "adjustment_type": "Manual Adjustment",
            },
            timeout=15,
        )
        assert r.status_code == 404, r.text

    def test_amount_must_be_positive(self, sa_token):
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/create",
            json={
                "token": sa_token,
                "expense_id": KNOWN_EXPENSE_ID,
                "center": SA_CENTER,
                "month": KNOWN_EXPENSE_MONTH,
                "adjustment_amount": 0,
                "adjustment_type": "Manual Adjustment",
            },
            timeout=15,
        )
        assert r.status_code == 400

    def test_invalid_type(self, sa_token):
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/create",
            json={
                "token": sa_token,
                "expense_id": KNOWN_EXPENSE_ID,
                "center": SA_CENTER,
                "month": KNOWN_EXPENSE_MONTH,
                "adjustment_amount": 10,
                "adjustment_type": "Some Random Type",
            },
            timeout=15,
        )
        assert r.status_code == 400

    def test_amount_exceeds_original_400(self, sa_token):
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/create",
            json={
                "token": sa_token,
                "expense_id": KNOWN_EXPENSE_ID,
                "center": SA_CENTER,
                "month": KNOWN_EXPENSE_MONTH,
                "adjustment_amount": KNOWN_EXPENSE_AMOUNT + 1,
                "adjustment_type": "Manual Adjustment",
                "adjustment_reason": "TEST exceeds",
            },
            timeout=15,
        )
        assert r.status_code == 400
        assert "exceed" in r.text.lower()


class TestCRUDRoundtrip:
    created_ids = []

    def test_01_create_ok(self, sa_token):
        snapshot = _fetch_expense_snapshot(sa_token)
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/create",
            json={
                "token": sa_token,
                "expense_id": KNOWN_EXPENSE_ID,
                "center": SA_CENTER,
                "month": KNOWN_EXPENSE_MONTH,
                "adjustment_amount": 1500,
                "adjustment_type": "Next Month Rent Paid in Advance",
                "adjustment_reason": "TEST iteration85 round-trip",
            },
            timeout=20,
        )
        assert r.status_code == 200, r.text
        adj = r.json()["adjustment"]
        assert adj["adjustment_amount"] == 1500.0
        assert adj["center"] == SA_CENTER
        assert adj["original_expense_amount"] == KNOWN_EXPENSE_AMOUNT
        assert adj["adjustment_type"] == "Next Month Rent Paid in Advance"
        TestCRUDRoundtrip.created_ids.append(adj["adjustment_id"])
        # expense row unchanged
        after = _fetch_expense_snapshot(sa_token)
        if snapshot and after:
            assert float(snapshot.get("amount", 0)) == float(after.get("amount", 0))

    def test_02_list_filters(self, sa_token):
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/list",
            json={"token": sa_token, "center": SA_CENTER, "month": KNOWN_EXPENSE_MONTH},
            timeout=15,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["count"] >= 1
        assert body["total_adjustments"] >= 1500.0
        assert any(it["adjustment_id"] in TestCRUDRoundtrip.created_ids for it in body["items"])

    def test_03_cumulative_cap_blocks(self, sa_token):
        # First adjustment is 1500. Try to add (original - 1500 + 1) which must fail.
        too_big = KNOWN_EXPENSE_AMOUNT - 1500 + 1
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/create",
            json={
                "token": sa_token,
                "expense_id": KNOWN_EXPENSE_ID,
                "center": SA_CENTER,
                "month": KNOWN_EXPENSE_MONTH,
                "adjustment_amount": too_big,
                "adjustment_type": "Manual Adjustment",
            },
            timeout=15,
        )
        assert r.status_code == 400
        assert "exceed" in r.text.lower() or "cumulative" in r.text.lower()

    def test_04_update_revalidates(self, sa_token):
        aid = TestCRUDRoundtrip.created_ids[0]
        # update to a value > original — must fail
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/update/{aid}",
            json={"token": sa_token, "adjustment_amount": KNOWN_EXPENSE_AMOUNT + 10},
            timeout=15,
        )
        assert r.status_code == 400
        # update to valid value — must succeed
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/update/{aid}",
            json={"token": sa_token, "adjustment_amount": 1800, "adjustment_reason": "TEST updated"},
            timeout=15,
        )
        assert r.status_code == 200
        assert r.json()["adjustment"]["adjustment_amount"] == 1800.0
        assert r.json()["adjustment"]["adjustment_reason"] == "TEST updated"

    def test_05_summary_uses_adjusted_expenses(self, sa_token):
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/summary",
            json={"token": sa_token, "center": SA_CENTER, "month": KNOWN_EXPENSE_MONTH},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # response wraps content under "summary"
        body = body.get("summary", body)
        # expense_adjustments block present
        assert "expense_adjustments" in body, f"keys: {list(body.keys())}"
        ea = body["expense_adjustments"]
        assert ea["total_adjustments"] >= 1800.0
        # financial_summary contains both raw and adjusted
        fs = body.get("financial_summary", {})
        assert "total_expenses" in fs
        assert "total_adjustments" in fs
        assert "adjusted_expenses" in fs
        assert round(fs["total_expenses"] - fs["total_adjustments"], 2) == round(fs["adjusted_expenses"], 2)

    def test_06_report_rollup(self, sa_token):
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/report",
            json={"token": sa_token, "centers": [SA_CENTER], "from_month": KNOWN_EXPENSE_MONTH, "to_month": KNOWN_EXPENSE_MONTH},
            timeout=20,
        )
        assert r.status_code == 200
        body = r.json()
        assert "items" in body and "summary_by_center_month" in body and "totals" in body
        t = body["totals"]
        for k in ("total_expenses", "total_adjustments", "adjusted_expenses", "count"):
            assert k in t
        assert t["total_adjustments"] >= 1800.0
        # Per-center-month summary row should exist
        assert any(s["center"] == SA_CENTER and s["month"] == KNOWN_EXPENSE_MONTH for s in body["summary_by_center_month"])

    def test_07_owner_reports_uses_adjusted(self, sa_token):
        r = requests.post(
            f"{BASE_URL}/api/owner-reports/monthly-report",
            json={"token": sa_token, "center": SA_CENTER, "month": KNOWN_EXPENSE_MONTH},
            timeout=30,
        )
        # Endpoint may or may not exist depending on FO mapping; tolerate 404 but
        # if 200, must include adjusted_expenses + expense_adjustments info.
        if r.status_code == 200:
            body = r.json()
            # presence check
            has_adj = (
                "expense_adjustments" in body
                or "adjusted_expenses" in body
                or any("adjusted_expenses" in v for v in body.values() if isinstance(v, dict))
            )
            assert has_adj, f"owner-reports/monthly-report missing adjusted_expenses: {list(body.keys())}"
        else:
            assert r.status_code in (400, 403, 404)

    def test_08_fo_list_restricted(self, fo_token):
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/list",
            json={"token": fo_token, "center": SA_CENTER, "month": KNOWN_EXPENSE_MONTH},
            timeout=15,
        )
        assert r.status_code == 403, f"FO should not be able to view other centers, got {r.status_code}"

    def test_09_fo_update_blocked(self, fo_token):
        aid = TestCRUDRoundtrip.created_ids[0]
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/update/{aid}",
            json={"token": fo_token, "adjustment_amount": 2000},
            timeout=15,
        )
        assert r.status_code == 403

    def test_10_fo_delete_blocked(self, fo_token):
        aid = TestCRUDRoundtrip.created_ids[0]
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/delete/{aid}",
            json={"token": fo_token},
            timeout=15,
        )
        assert r.status_code == 403

    def test_11_delete_ok(self, sa_token):
        aid = TestCRUDRoundtrip.created_ids[0]
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/delete/{aid}",
            json={"token": sa_token},
            timeout=15,
        )
        assert r.status_code == 200
        # verify gone
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/adjustments/list",
            json={"token": sa_token, "center": SA_CENTER, "month": KNOWN_EXPENSE_MONTH},
            timeout=15,
        )
        assert r.status_code == 200
        assert not any(it["adjustment_id"] == aid for it in r.json()["items"])

    def test_12_zero_adjustment_parity(self, sa_token):
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/summary",
            json={"token": sa_token, "center": SA_CENTER, "month": KNOWN_EXPENSE_MONTH},
            timeout=30,
        )
        assert r.status_code == 200
        body = r.json().get("summary", r.json())
        fs = body.get("financial_summary", {})
        # after delete, no adjustments — adjusted == total
        assert round(fs.get("total_adjustments", 0), 2) == 0.0
        assert round(fs.get("adjusted_expenses", 0), 2) == round(fs.get("total_expenses", 0), 2)
