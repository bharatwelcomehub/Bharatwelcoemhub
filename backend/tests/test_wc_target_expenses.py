# Tests for the WC target_expenses contract:
#   POST /api/center-accounts/wc-row-save with {target_expenses: N}
#     - replaces a single INTRA row dated on the LAST day of the month
#     - INTRA amount = target - (real db expenses excluding prior INTRA)
#     - target == real -> INTRA row is DELETED (count == 0)
#     - wc_adjustment alone does NOT touch db.expenses
#   POST /api/center-accounts/wc-table after save:
#     - row.expenses == target_expenses (no double counting)
#     - row shape is preserved
#   Additional coverage: leap year Feb 29 (2024-02), real_db == 0 month creates positive INTRA.
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

_mongo_cli = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
_db = _mongo_cli[os.environ.get("DB_NAME", "test_database")]


def _intra_id(center: str, month: str) -> str:
    return f"INTRA-{center}-{month}"


def _intra_rows(center: str, month: str):
    return list(_db.expenses.find({"intra_entry_id": _intra_id(center, month)}, {"_id": 0}))


def _real_total(center: str, month: str) -> float:
    pipeline = [
        {"$match": {
            "center": center,
            "date": {"$regex": f"^{month}"},
            "$or": [
                {"intra_entry_id": {"$exists": False}},
                {"intra_entry_id": {"$ne": _intra_id(center, month)}},
            ],
        }},
        {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$amount", 0]}}}},
    ]
    res = list(_db.expenses.aggregate(pipeline))
    return float(res[0]["total"]) if res else 0.0


def _last_day(month: str) -> str:
    yy, mm = int(month[:4]), int(month[5:7])
    return f"{month}-{calendar.monthrange(yy, mm)[1]:02d}"


def _save_target(token, center, month, target=None, wc_adj=None):
    body = {"token": token, "center": center, "month": month}
    if target is not None:
        body["target_expenses"] = target
    if wc_adj is not None:
        body["wc_adjustment"] = wc_adj
    return requests.post(f"{BASE_URL}/api/center-accounts/wc-row-save", json=body, timeout=30)


def _wc_table_row(token, center, month):
    r = requests.post(
        f"{BASE_URL}/api/center-accounts/wc-table",
        json={"token": token, "center": center},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    rows = {row["month"]: row for row in r.json().get("rows", [])}
    return rows.get(month)


@pytest.fixture(scope="module")
def token():
    s = requests.Session()
    s.post(f"{BASE_URL}/api/send_otp",
           json={"mobile": MOBILE, "center": LOGIN_CENTER}, timeout=30)
    r = s.post(f"{BASE_URL}/api/verify_otp",
               json={"mobile": MOBILE, "otp": OTP, "center": LOGIN_CENTER}, timeout=30)
    assert r.status_code == 200, r.text
    tok = r.json().get("token")
    assert tok
    return tok


@pytest.fixture(autouse=True)
def _cleanup_intra():
    """Clean up INTRA rows + overrides for the test months before AND after every test."""
    months = ["2026-02", "2024-02", "2030-07"]
    _db.expenses.delete_many({
        "center": TEST_CENTER,
        "expense_type": "INTRA CENTER ADJUSTMENT",
        "intra_entry_id": {"$in": [_intra_id(TEST_CENTER, m) for m in months]},
    })
    _db.wc_month_overrides.delete_many({"center": TEST_CENTER, "month": {"$in": months}})
    yield
    _db.expenses.delete_many({
        "center": TEST_CENTER,
        "expense_type": "INTRA CENTER ADJUSTMENT",
        "intra_entry_id": {"$in": [_intra_id(TEST_CENTER, m) for m in months]},
    })
    _db.wc_month_overrides.delete_many({"center": TEST_CENTER, "month": {"$in": months}})


# ----------------------------------------------------------------------
# Contract: target_expenses
# ----------------------------------------------------------------------

class TestTargetExpensesContract:
    MONTH = "2026-02"  # 28-day month

    def test_save_target_creates_intra_on_last_day(self, token):
        target = 5000.0
        real = _real_total(TEST_CENTER, self.MONTH)
        r = _save_target(token, TEST_CENTER, self.MONTH, target=target)
        assert r.status_code == 200, r.text

        rows = _intra_rows(TEST_CENTER, self.MONTH)
        if abs(target - real) < 0.01:
            assert len(rows) == 0, rows
        else:
            assert len(rows) == 1, rows
            assert rows[0]["expense_type"] == "INTRA CENTER ADJUSTMENT"
            assert rows[0]["date"] == _last_day(self.MONTH) == "2026-02-28"
            assert abs(float(rows[0]["amount"]) - round(target - real, 2)) < 0.01

    def test_wc_table_returns_target_no_double_count(self, token):
        target = 7777.0
        r = _save_target(token, TEST_CENTER, self.MONTH, target=target)
        assert r.status_code == 200, r.text
        row = _wc_table_row(token, TEST_CENTER, self.MONTH)
        assert row is not None, "Month row missing in wc-table response"
        assert abs(float(row["expenses"]) - target) < 0.01, row

        # Required row shape (subset)
        for k in ["month", "sale", "expenses", "expenses_db", "expense_adjustment",
                  "commission", "pnl", "opening_wc", "balance_wc", "diff_wc",
                  "wc_adjustment", "rev_share_status"]:
            assert k in row, f"Missing key {k} in row {row}"

    def test_repeated_saves_replace_intra(self, token):
        for tgt in (5000.0, 200000.0, 12345.67):
            r = _save_target(token, TEST_CENTER, self.MONTH, target=tgt)
            assert r.status_code == 200, r.text
            rows = _intra_rows(TEST_CENTER, self.MONTH)
            real = _real_total(TEST_CENTER, self.MONTH)
            delta = round(tgt - real, 2)
            if abs(delta) < 0.01:
                assert len(rows) == 0
            else:
                assert len(rows) == 1, f"Expected single INTRA row after target={tgt}, got {rows}"
                assert abs(float(rows[0]["amount"]) - delta) < 0.01

    def test_target_equal_real_deletes_intra(self, token):
        # First create an INTRA row, then save target == real to clear it
        _save_target(token, TEST_CENTER, self.MONTH, target=99999.0)
        assert len(_intra_rows(TEST_CENTER, self.MONTH)) == 1

        real = _real_total(TEST_CENTER, self.MONTH)
        r = _save_target(token, TEST_CENTER, self.MONTH, target=real)
        assert r.status_code == 200, r.text
        # Count via raw mongo (count_documents) per spec
        cnt = _db.expenses.count_documents({
            "center": TEST_CENTER,
            "expense_type": "INTRA CENTER ADJUSTMENT",
            "intra_entry_id": _intra_id(TEST_CENTER, self.MONTH),
        })
        assert cnt == 0, f"INTRA row should be deleted when target==real, count={cnt}"

    def test_wc_adjustment_only_no_db_expense(self, token):
        # Ensure no INTRA exists, then send wc_adjustment alone
        r = _save_target(token, TEST_CENTER, self.MONTH, wc_adj=2500.0)
        assert r.status_code == 200, r.text
        cnt = _db.expenses.count_documents({
            "center": TEST_CENTER,
            "expense_type": "INTRA CENTER ADJUSTMENT",
            "intra_entry_id": _intra_id(TEST_CENTER, self.MONTH),
        })
        assert cnt == 0, "wc_adjustment alone must NOT create INTRA row"

        # And the override doc should carry the wc_adjustment
        ov = _db.wc_month_overrides.find_one({"center": TEST_CENTER, "month": self.MONTH})
        assert ov is not None
        assert abs(float(ov.get("wc_adjustment", 0)) - 2500.0) < 0.01


# ----------------------------------------------------------------------
# Edge cases requested in problem statement
# ----------------------------------------------------------------------

class TestEdgeCases:
    def test_leap_year_feb_29(self, token):
        month = "2024-02"  # leap year -> 29 days
        target = 4321.0
        real = _real_total(TEST_CENTER, month)
        r = _save_target(token, TEST_CENTER, month, target=target)
        assert r.status_code == 200, r.text
        rows = _intra_rows(TEST_CENTER, month)
        if abs(target - real) < 0.01:
            assert len(rows) == 0
        else:
            assert len(rows) == 1
            assert rows[0]["date"] == "2024-02-29", rows[0]
            assert abs(float(rows[0]["amount"]) - round(target - real, 2)) < 0.01

    def test_month_with_no_real_expenses_creates_positive_intra(self, token):
        month = "2030-07"  # far-future month, expected to have no real expenses
        # Pre-condition: no real expenses
        real = _real_total(TEST_CENTER, month)
        if real != 0:
            pytest.skip(f"Real expenses for {TEST_CENTER} {month} = {real}; skipping")

        target = 10000.0
        r = _save_target(token, TEST_CENTER, month, target=target)
        assert r.status_code == 200, r.text
        rows = _intra_rows(TEST_CENTER, month)
        assert len(rows) == 1
        assert rows[0]["date"] == "2030-07-31"
        assert abs(float(rows[0]["amount"]) - target) < 0.01
        assert float(rows[0]["amount"]) > 0
