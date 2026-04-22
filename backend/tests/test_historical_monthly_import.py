"""Historical Monthly-File Importer end-to-end tests.

Covers the 8 backend scenarios from the review request for
/api/historical/import-monthly-file (Trial Balance + Daily Expenses
+ Daily Sales) and the new /monthly-summary, /clear-monthly endpoints.

Sample file: /tmp/hsr_mar26.xlsx ('EXPENCE SHEET -HSR- MARCH. 2026.xlsx')
Expected: PB-HSR / 2026-03 / TB ~37 heads / total_expenses ~14.6L
/ total_sales ~12.47L / 93 expense rows / 31 sales days.

Note: PB-HSR currently has live daily_sales rows for 2026-03 (operator-
entered) so all 31 imported days will be skipped — that's the expected
behaviour of the live-data protection rule.
"""
import os
import re
import shutil
import pytest
import requests
from pymongo import MongoClient


# ---------- helpers ----------

def _read_frontend_env(key: str) -> str:
    try:
        with open("/app/frontend/.env") as fh:
            for line in fh:
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return ""


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env("REACT_APP_BACKEND_URL")).rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

ORIG_XLSX = "/tmp/hsr_mar26.xlsx"
RENAMED_HSR = "/tmp/EXPENCE SHEET -HSR- MARCH. 2026.xlsx"
NO_CENTER_XLSX = "/tmp/EXPENCE SHEET MARCH 2026.xlsx"  # same file, no center keyword

SUPER_ADMIN = {"mobile": "9741399190", "center": "PB-MGT"}
FRANCHISE = {"mobile": "8888888888", "center": "PB-HSR"}
OTP = "123456"


def _login(creds: dict) -> str:
    s = requests.Session()
    s.post(f"{BASE_URL}/api/send_otp", json=creds, timeout=15)
    r = s.post(f"{BASE_URL}/api/verify_otp", json={**creds, "otp": OTP}, timeout=15)
    assert r.status_code == 200, f"login failed for {creds}: {r.status_code} {r.text[:200]}"
    data = r.json()
    return data.get("token") or data.get("session", {}).get("token")


def _mongo():
    backend_env = {}
    with open("/app/backend/.env") as fh:
        for ln in fh:
            if "=" in ln and not ln.strip().startswith("#"):
                k, v = ln.strip().split("=", 1)
                backend_env[k] = v.strip().strip('"').strip("'")
    return MongoClient(backend_env["MONGO_URL"]), backend_env["DB_NAME"]


# ---------- session-scoped fixtures ----------

@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER_ADMIN)


@pytest.fixture(scope="module")
def franchise_token():
    return _login(FRANCHISE)


@pytest.fixture(scope="module", autouse=True)
def _ensure_renamed_files():
    """Make filename-auto-detect copies. Cleaned up at end."""
    assert os.path.exists(ORIG_XLSX), f"sample file missing: {ORIG_XLSX}"
    shutil.copy(ORIG_XLSX, RENAMED_HSR)
    shutil.copy(ORIG_XLSX, NO_CENTER_XLSX)
    yield
    for f in (RENAMED_HSR, NO_CENTER_XLSX):
        try:
            os.remove(f)
        except OSError:
            pass


@pytest.fixture(scope="module", autouse=True)
def _cleanup_after_run():
    """Per main-agent instructions: wipe monthly_import rows and trial-balance docs after the suite."""
    yield
    cli, dbname = _mongo()
    db = cli[dbname]
    db.expenses.delete_many({"source": {"$regex": "^monthly_import:"}})
    db.daily_sales.delete_many({"source": {"$regex": "^monthly_import:"}})
    db.historical_trial_balance.delete_many({})
    cli.close()


def _upload(token: str, path: str, **extra):
    with open(path, "rb") as fh:
        files = {"file": (os.path.basename(path), fh, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        data = {"token": token, **extra}
        return requests.post(f"{BASE_URL}/api/historical/import-monthly-file", files=files, data=data, timeout=120)


# ---------- 1. Happy-path import ----------

class TestImportMonthlyFile:
    def test_01_import_hsr_march_2026(self, super_token):
        r = _upload(super_token, ORIG_XLSX)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body["success"] is True
        assert body["center"] == "PB-HSR"
        assert body["month"] == "2026-03"
        tb = body["trial_balance"]
        # TB heads ~37, total_expenses ~14.6L, total_sales ~12.47L
        assert 30 <= tb["heads"] <= 45, f"unexpected heads count {tb['heads']}"
        assert 1_300_000 <= tb["total_expenses"] <= 1_600_000, f"total_expenses {tb['total_expenses']}"
        assert 1_100_000 <= tb["total_sales"] <= 1_400_000, f"total_sales {tb['total_sales']}"
        # Expenses ~93 rows
        assert 80 <= body["expenses"]["rows"] <= 110, f"expense rows {body['expenses']['rows']}"
        # Daily sales: 31 days parsed from the 5 sales sheets
        assert body["daily_sales"]["days"] == 31, f"days {body['daily_sales']['days']}"
        # Skipped-live counter must be present
        assert "skipped_live_days" in body["daily_sales"]


# ---------- 2. Filename auto-detection ----------

class TestFilenameAutoDetect:
    def test_02_renamed_hsr_filename_detects_center(self, super_token):
        r = _upload(super_token, RENAMED_HSR)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body["center"] == "PB-HSR"
        assert body["month"] == "2026-03"

    def test_03_no_center_keyword_returns_400(self, super_token):
        r = _upload(super_token, NO_CENTER_XLSX)
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text[:200]}"
        assert "center" in r.text.lower()

    def test_04_center_override_rescues_no_center_filename(self, super_token):
        r = _upload(super_token, NO_CENTER_XLSX, center_override="PB-HSR")
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body["center"] == "PB-HSR"
        assert body["month"] == "2026-03"


# ---------- 3. Idempotency ----------

class TestIdempotency:
    def test_05_double_import_does_not_duplicate(self, super_token):
        cli, dbname = _mongo()
        db = cli[dbname]
        # First (the suite has already imported once but call again to be explicit)
        r1 = _upload(super_token, ORIG_XLSX)
        assert r1.status_code == 200
        exp_count_1 = db.expenses.count_documents({
            "center": "PB-HSR",
            "date": {"$regex": "^2026-03"},
            "source": {"$regex": "^monthly_import:"},
        })
        tb_count_1 = db.historical_trial_balance.count_documents({"center": "PB-HSR", "month": "2026-03"})
        # Second import
        r2 = _upload(super_token, ORIG_XLSX)
        assert r2.status_code == 200
        exp_count_2 = db.expenses.count_documents({
            "center": "PB-HSR",
            "date": {"$regex": "^2026-03"},
            "source": {"$regex": "^monthly_import:"},
        })
        tb_count_2 = db.historical_trial_balance.count_documents({"center": "PB-HSR", "month": "2026-03"})
        cli.close()
        assert exp_count_1 == exp_count_2, f"expense rows changed across re-import {exp_count_1}->{exp_count_2}"
        assert tb_count_1 == 1 and tb_count_2 == 1, "must be exactly ONE TB doc per center+month"


# ---------- 4. Live-data protection ----------

class TestLiveDataProtection:
    def test_06_existing_live_daily_sale_not_overwritten(self, super_token):
        cli, dbname = _mongo()
        db = cli[dbname]
        # Seed a live row (source != monthly_import) for one day in 2026-03
        sentinel_date = "2026-03-15"
        db.daily_sales.delete_many({
            "center": "PB-HSR", "date": sentinel_date,
            "source": {"$regex": "^monthly_import:"},
        })
        # Upsert a live doc; if a live row already exists from real ops, leave it
        existing = db.daily_sales.find_one({"center": "PB-HSR", "date": sentinel_date})
        seeded = False
        if not existing:
            db.daily_sales.insert_one({
                "center": "PB-HSR", "date": sentinel_date,
                "total_cash_sale": 11111, "total_online_sale": 22222, "total_sale": 33333,
                "source": "manual_test_seed",
            })
            seeded = True
        else:
            # Force the source to be a non-monthly_import marker for the test
            if str(existing.get("source", "")).startswith("monthly_import:"):
                db.daily_sales.update_one({"_id": existing["_id"]}, {"$set": {"source": "manual_test_seed"}})
                seeded = True
        try:
            r = _upload(super_token, ORIG_XLSX)
            assert r.status_code == 200
            body = r.json()
            # Skipped counter must be >= 1 (the sentinel day)
            assert body["daily_sales"]["skipped_live_days"] >= 1
            # And the live row must remain non-monthly_import
            after = db.daily_sales.find_one({"center": "PB-HSR", "date": sentinel_date})
            assert after is not None
            assert not str(after.get("source", "")).startswith("monthly_import:"), \
                f"live row was overwritten by import: source={after.get('source')}"
        finally:
            if seeded:
                db.daily_sales.delete_one({"center": "PB-HSR", "date": sentinel_date, "source": "manual_test_seed"})
            cli.close()


# ---------- 5. /monthly-summary ----------

class TestMonthlySummary:
    def test_07_summary_includes_pb_hsr(self, super_token):
        # Make sure HSR is imported
        _upload(super_token, ORIG_XLSX)
        r = requests.post(f"{BASE_URL}/api/historical/monthly-summary", json={"token": super_token}, timeout=20)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert "centers" in body
        hsr = next((c for c in body["centers"] if c["center"] == "PB-HSR"), None)
        assert hsr is not None, "PB-HSR not in monthly-summary"
        assert hsr["months_count"] >= 1
        assert hsr["earliest"] <= "2026-03" <= hsr["latest"]
        assert hsr["total_expenses"] > 1_000_000
        assert hsr["total_sales"] > 1_000_000


# ---------- 6. RBAC: non super-admin gets 403 ----------

class TestRBAC:
    def test_08_franchise_cannot_import(self, franchise_token):
        r = _upload(franchise_token, ORIG_XLSX)
        assert r.status_code == 403, f"expected 403 for franchise, got {r.status_code}"

    def test_09_franchise_cannot_clear(self, franchise_token):
        r = requests.post(
            f"{BASE_URL}/api/historical/clear-monthly",
            json={"token": franchise_token, "center": "PB-HSR", "month": "2026-03"},
            timeout=15,
        )
        assert r.status_code == 403


# ---------- 7. Downstream visibility (WC-table + MIS) ----------

class TestDownstreamVisibility:
    def test_10_wc_table_includes_imported_expense_for_2026_03(self, super_token):
        # Ensure imported
        _upload(super_token, ORIG_XLSX)
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/wc-table",
            json={"token": super_token, "center": "PB-HSR"},
            timeout=30,
        )
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        rows = body.get("rows", [])
        row = next((x for x in rows if x.get("month") == "2026-03"), None)
        assert row is not None, "no 2026-03 row in WC-table"
        # Imported expense total ~14.6L; minimum 9L sanity check from review request
        assert row.get("expenses", 0) >= 900_000, f"2026-03 expenses too low: {row.get('expenses')}"

    def test_11_mis_overview_includes_imported_expenses(self, super_token):
        _upload(super_token, ORIG_XLSX)
        r = requests.post(
            f"{BASE_URL}/api/mis/overview",
            json={
                "token": super_token,
                "period": "custom",
                "custom_start": "2026-03-01",
                "custom_end": "2026-03-31",
                "center": "PB-HSR",
            },
            timeout=30,
        )
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        # Total expenses for 2026-03 should reflect imported amount (>= 9L)
        # Field name in mis_dashboard varies; check a few common ones
        candidates = []
        for k in ("total_expenses", "totalExpenses", "expenses_total"):
            if k in body and isinstance(body[k], (int, float)):
                candidates.append(body[k])
        # Some MIS responses nest under a key; flatten the top-level numbers
        for v in body.values():
            if isinstance(v, dict):
                for k2 in ("total_expenses", "totalExpenses", "expenses_total"):
                    if k2 in v and isinstance(v[k2], (int, float)):
                        candidates.append(v[k2])
        assert candidates, f"no total_expenses field in MIS overview response: keys={list(body.keys())}"
        assert max(candidates) >= 900_000, f"MIS overview expenses too low: {candidates}"


# ---------- 8. /clear-monthly ----------

class TestClearMonthly:
    def test_12_clear_monthly_deletes_only_monthly_import_rows(self, super_token):
        cli, dbname = _mongo()
        db = cli[dbname]
        # Seed a live expense row that must NOT be deleted
        live_marker = {
            "center": "PB-HSR",
            "date": "2026-03-20",
            "amount": 7777,
            "expense_type": "MARKER",
            "description": "live marker - do not delete",
            "source": "manual_test_seed",
        }
        db.expenses.delete_many(live_marker)  # ensure clean
        db.expenses.insert_one(dict(live_marker))
        # Ensure imported state
        r_imp = _upload(super_token, ORIG_XLSX)
        assert r_imp.status_code == 200

        # Clear
        r = requests.post(
            f"{BASE_URL}/api/historical/clear-monthly",
            json={"token": super_token, "center": "PB-HSR", "month": "2026-03"},
            timeout=20,
        )
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body["success"] is True
        assert body["expenses_deleted"] >= 1
        assert body["trial_balance_deleted"] == 1

        # Live marker still present
        live_after = db.expenses.find_one({"date": "2026-03-20", "amount": 7777, "source": "manual_test_seed"})
        assert live_after is not None, "live (non-monthly_import) expense was deleted by clear-monthly"
        # No more monthly_import rows for this center+month
        leftover = db.expenses.count_documents({
            "center": "PB-HSR", "date": {"$regex": "^2026-03"},
            "source": {"$regex": "^monthly_import:"},
        })
        assert leftover == 0, f"still {leftover} monthly_import expense rows after clear"
        # TB doc gone
        tb_after = db.historical_trial_balance.count_documents({"center": "PB-HSR", "month": "2026-03"})
        assert tb_after == 0

        # Cleanup live marker
        db.expenses.delete_one({"_id": live_after["_id"]})
        cli.close()
