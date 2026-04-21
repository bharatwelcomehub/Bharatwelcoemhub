# Parity tests: MIS Dashboard Overview vs Center Accounts WC Table
# -----------------------------------------------------------------
# User bug: MIS Dashboard and Franchise Owner Dashboard don't reflect
# WC-table master data (expenses/commission/gst) when overrides are
# applied. This file validates that after saving overrides via
# /api/center-accounts/wc-row-save, the /api/mis/overview endpoint
# returns the exact same numbers for the same center + month.
#
# Clean-up: all test data targets PB-HSR 2025-05 (and 2025-04..2025-07
# for parity sweeps); INTRA rows + wc_month_overrides docs are wiped
# before and after every test module session.
import os
import calendar
import pytest
import pymongo
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://balance-cascade-fix.preview.emergentagent.com",
).rstrip("/")
MOBILE = "9741399190"
OTP = "123456"
LOGIN_CENTER = "PB-MGT"
TEST_CENTER = "PB-HSR"

# Module-level cleanup months
CLEANUP_MONTHS = ["2025-04", "2025-05", "2025-06", "2025-07"]

_mongo_cli = pymongo.MongoClient(
    os.environ.get("MONGO_URL", "mongodb://localhost:27017")
)
_db = _mongo_cli[os.environ.get("DB_NAME", "test_database")]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _intra_id(center: str, month: str) -> str:
    return f"INTRA-{center}-{month}"


def _last_day(month: str) -> str:
    yy, mm = int(month[:4]), int(month[5:7])
    return f"{month}-{calendar.monthrange(yy, mm)[1]:02d}"


def _save_wc_row(token, center, month, target_expenses=None,
                 commission_target=None, gst_target=None, wc_adjustment=None):
    body = {"token": token, "center": center, "month": month}
    if target_expenses is not None:
        body["target_expenses"] = target_expenses
    if commission_target is not None:
        body["commission_target"] = commission_target
    if gst_target is not None:
        body["gst_target"] = gst_target
    if wc_adjustment is not None:
        body["wc_adjustment"] = wc_adjustment
    return requests.post(
        f"{BASE_URL}/api/center-accounts/wc-row-save", json=body, timeout=30
    )


def _get_wc_row(token, center, month):
    r = requests.post(
        f"{BASE_URL}/api/center-accounts/wc-table",
        json={"token": token, "center": center},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    rows = {row["month"]: row for row in r.json().get("rows", [])}
    return rows.get(month), r.json()


def _get_mis_overview(token, center, month):
    start = f"{month}-01"
    end = _last_day(month)
    r = requests.post(
        f"{BASE_URL}/api/mis/overview",
        json={
            "token": token,
            "period": "custom",
            "center": center,
            "custom_start": start,
            "custom_end": end,
        },
        timeout=45,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _get_mis_wc(token, center, month):
    end = _last_day(month)
    start = f"{month}-01"
    r = requests.post(
        f"{BASE_URL}/api/mis/working-capital",
        json={
            "token": token,
            "period": "custom",
            "center": center,
            "custom_start": start,
            "custom_end": end,
        },
        timeout=45,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _approx(a, b, tol=1.0):
    return abs(float(a) - float(b)) < tol


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

@pytest.fixture(scope="module")
def token():
    s = requests.Session()
    s.post(
        f"{BASE_URL}/api/send_otp",
        json={"mobile": MOBILE, "center": LOGIN_CENTER},
        timeout=30,
    )
    r = s.post(
        f"{BASE_URL}/api/verify_otp",
        json={"mobile": MOBILE, "otp": OTP, "center": LOGIN_CENTER},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    tok = r.json().get("token")
    assert tok, "No token returned"
    return tok


@pytest.fixture(autouse=True)
def _cleanup():
    """Ensure a clean override state before & after every test."""
    _db.expenses.delete_many({
        "center": TEST_CENTER,
        "expense_type": "INTRA CENTER ADJUSTMENT",
        "intra_entry_id": {"$in": [_intra_id(TEST_CENTER, m) for m in CLEANUP_MONTHS]},
    })
    _db.wc_month_overrides.delete_many({
        "center": TEST_CENTER, "month": {"$in": CLEANUP_MONTHS}
    })
    yield
    _db.expenses.delete_many({
        "center": TEST_CENTER,
        "expense_type": "INTRA CENTER ADJUSTMENT",
        "intra_entry_id": {"$in": [_intra_id(TEST_CENTER, m) for m in CLEANUP_MONTHS]},
    })
    _db.wc_month_overrides.delete_many({
        "center": TEST_CENTER, "month": {"$in": CLEANUP_MONTHS}
    })


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

class TestParityNoOverride:
    """Clean-state parity: MIS overview must equal WC-table row values."""

    @pytest.mark.parametrize("month", ["2025-04", "2025-05", "2025-06", "2025-07"])
    def test_parity_clean_state(self, token, month):
        wc_row, wc_full = _get_wc_row(token, TEST_CENTER, month)
        if wc_row is None:
            pytest.skip(f"No WC row present for {TEST_CENTER} {month}")

        mis = _get_mis_overview(token, TEST_CENTER, month)
        summary = mis.get("summary", {})

        # Sales parity
        assert _approx(summary.get("total_sales", 0), wc_row["sale"], tol=2.0), (
            f"Sales mismatch {month}: MIS={summary.get('total_sales')} "
            f"WC={wc_row['sale']}"
        )
        # Expenses parity (already captures INTRA rows if any)
        assert _approx(summary.get("total_expenses", 0), wc_row["expenses"], tol=2.0), (
            f"Expenses mismatch {month}: MIS={summary.get('total_expenses')} "
            f"WC={wc_row['expenses']}"
        )
        # GST parity
        assert _approx(summary.get("total_gst", 0), wc_row["gst"], tol=2.0), (
            f"GST mismatch {month}: MIS={summary.get('total_gst')} "
            f"WC={wc_row['gst']}"
        )
        # Commission parity
        assert _approx(
            summary.get("total_commissions", 0), wc_row["commission"], tol=2.0
        ), (
            f"Commission mismatch {month}: MIS={summary.get('total_commissions')} "
            f"WC={wc_row['commission']}"
        )


class TestParityWithOverrides:
    """After saving WC overrides, MIS overview must reflect them."""

    MONTH = "2025-05"

    def test_override_reflects_in_mis_summary_and_per_center(self, token):
        target_expenses = 700000.0
        commission_target = 50000.0
        gst_target = 80000.0

        r = _save_wc_row(
            token,
            TEST_CENTER,
            self.MONTH,
            target_expenses=target_expenses,
            commission_target=commission_target,
            gst_target=gst_target,
        )
        assert r.status_code == 200, r.text

        # Re-fetch WC row after override
        wc_row, _ = _get_wc_row(token, TEST_CENTER, self.MONTH)
        assert wc_row is not None
        assert _approx(wc_row["expenses"], target_expenses), wc_row
        assert _approx(wc_row["commission"], commission_target), wc_row
        assert _approx(wc_row["gst"], gst_target), wc_row

        mis = _get_mis_overview(token, TEST_CENTER, self.MONTH)
        summary = mis.get("summary", {})
        centers = mis.get("centers", [])

        # Summary-level
        assert _approx(summary.get("total_expenses", 0), target_expenses, tol=2.0), (
            f"Summary expenses: expected {target_expenses}, "
            f"got {summary.get('total_expenses')}"
        )
        assert _approx(summary.get("total_gst", 0), gst_target, tol=2.0), (
            f"Summary GST: expected {gst_target}, got {summary.get('total_gst')}"
        )
        assert _approx(
            summary.get("total_commissions", 0), commission_target, tol=2.0
        ), (
            f"Summary commissions: expected {commission_target}, "
            f"got {summary.get('total_commissions')}"
        )

        # Profit = Sales - Expenses - GST - Commissions
        expected_profit = (
            float(summary.get("total_sales", 0))
            - target_expenses
            - gst_target
            - commission_target
        )
        assert _approx(summary.get("profit", 0), expected_profit, tol=2.0), (
            f"Profit mismatch: expected {expected_profit}, "
            f"got {summary.get('profit')}"
        )

        # Per-center row must match
        assert len(centers) >= 1, f"No centers returned: {centers}"
        center_row = next((c for c in centers if c.get("center") == TEST_CENTER), None)
        assert center_row is not None, f"{TEST_CENTER} row missing: {centers}"
        assert _approx(center_row.get("expenses", 0), target_expenses, tol=2.0)
        assert _approx(center_row.get("gst", 0), gst_target, tol=2.0)
        assert _approx(center_row.get("commissions", 0), commission_target, tol=2.0)
        expected_center_profit = (
            float(center_row.get("sales", 0))
            - target_expenses
            - gst_target
            - commission_target
        )
        assert _approx(center_row.get("profit", 0), expected_center_profit, tol=2.0), (
            f"Per-center profit mismatch: expected {expected_center_profit}, "
            f"got {center_row.get('profit')}"
        )

    def test_working_capital_reflects_forced_loss(self, token):
        # Force a heavy loss via huge target_expenses -> WC must drop below base
        huge_expense = 5_000_000.0
        r = _save_wc_row(
            token, TEST_CENTER, self.MONTH, target_expenses=huge_expense
        )
        assert r.status_code == 200, r.text

        wc_resp = _get_mis_wc(token, TEST_CENTER, self.MONTH)
        centers = wc_resp.get("centers", [])
        me = next((c for c in centers if c.get("center") == TEST_CENTER), None)
        assert me is not None, f"{TEST_CENTER} missing in MIS WC: {centers}"

        initial = float(me.get("initial_wc", 0))
        current = float(me.get("current_wc", 0))
        # After a 5M forced expense loss, current WC must be strictly below base
        assert initial > 0, me
        assert current < initial, (
            f"WC should have dropped after forced loss: initial={initial}, "
            f"current={current}"
        )
