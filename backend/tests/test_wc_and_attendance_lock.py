# Tests for: (1) WC table wc-row-save INTRA auto-expense + PDF/Excel exports
#            (2) Center-specific Attendance Lock/Unlock scope semantics
import os
import pytest
import pymongo
import requests

_mongo_cli = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
_db = _mongo_cli[os.environ.get("DB_NAME", "test_database")]


def _get_intra_entries(center: str, month: str):
    return list(_db.expenses.find({"intra_entry_id": f"INTRA-{center}-{month}"}, {"_id": 0}))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://balance-cascade-fix.preview.emergentagent.com").rstrip("/")
MOBILE = "9741399190"
OTP = "123456"
CENTER_PRIMARY = "PB-HSR"
CENTER_SECONDARY = "PB-MGT"
TEST_MONTH = "2026-02"


@pytest.fixture(scope="module")
def token():
    s = requests.Session()
    s.post(f"{BASE_URL}/api/send_otp", json={"mobile": MOBILE, "center": CENTER_SECONDARY}, timeout=30)
    r = s.post(f"{BASE_URL}/api/verify_otp",
               json={"mobile": MOBILE, "otp": OTP, "center": CENTER_SECONDARY}, timeout=30)
    assert r.status_code == 200, r.text
    tok = r.json().get("token")
    assert tok, r.text
    return tok


# ---------------- WC auto-expense tests ----------------

class TestWCRowSaveAutoExpense:
    def test_wc_row_save_creates_intra_expense(self, token):
        payload = {
            "token": token,
            "center": CENTER_PRIMARY,
            "month": TEST_MONTH,
            "expense_adjustment": 1234.56,
        }
        r = requests.post(f"{BASE_URL}/api/center-accounts/wc-row-save", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("success") is True

        # Verify intra expense directly in Mongo
        intra = _get_intra_entries(CENTER_PRIMARY, TEST_MONTH)
        assert len(intra) == 1, f"Expected exactly 1 INTRA entry, got {len(intra)}"
        assert intra[0].get("expense_type") == "INTRA CENTER ADJUSTMENT"
        assert abs(float(intra[0].get("amount", 0)) - 1234.56) < 0.01

    def test_wc_row_save_replaces_prior_intra_entry(self, token):
        payload = {
            "token": token,
            "center": CENTER_PRIMARY,
            "month": TEST_MONTH,
            "expense_adjustment": 500.00,
        }
        r = requests.post(f"{BASE_URL}/api/center-accounts/wc-row-save", json=payload, timeout=30)
        assert r.status_code == 200, r.text

        lp = {"token": token, "center": CENTER_PRIMARY, "month": TEST_MONTH}
        intra = _get_intra_entries(CENTER_PRIMARY, TEST_MONTH)
        assert len(intra) == 1, "Duplicate INTRA entries created on re-save"
        assert abs(float(intra[0].get("amount", 0)) - 500.00) < 0.01


# ---------------- WC export tests ----------------

class TestWCTableExports:
    def test_export_pdf(self, token):
        payload = {"token": token, "center": CENTER_PRIMARY}
        r = requests.post(f"{BASE_URL}/api/center-accounts/wc-table/export-pdf",
                          json=payload, timeout=60)
        assert r.status_code == 200, r.text
        assert "application/pdf" in r.headers.get("content-type", "")
        assert r.content[:4] == b"%PDF", f"Not a PDF: {r.content[:8]}"

    def test_export_excel(self, token):
        payload = {"token": token, "center": CENTER_PRIMARY}
        r = requests.post(f"{BASE_URL}/api/center-accounts/wc-table/export-excel",
                          json=payload, timeout=60)
        assert r.status_code == 200, r.text
        ctype = r.headers.get("content-type", "")
        assert "sheet" in ctype or "excel" in ctype or "openxml" in ctype, ctype
        assert r.content[:2] == b"PK", f"Not an xlsx (zip): {r.content[:4]}"


# ---------------- Center-specific attendance lock tests ----------------

@pytest.fixture(scope="class")
def cleanup_locks():
    """Cleanup any leftover test-month locks before class."""
    import pymongo
    cli = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = cli[os.environ.get("DB_NAME", "test_database")]
    db.attendance_locks.delete_many({"month": TEST_MONTH})
    yield
    db.attendance_locks.delete_many({"month": TEST_MONTH})


class TestAttendanceLockScope:
    def test_01_center_lock_locks_only_that_center(self, token, cleanup_locks):
        # Lock PB-HSR only
        r = requests.post(f"{BASE_URL}/api/attendance-dashboard/lock",
                          json={"token": token, "month": TEST_MONTH, "action": "lock",
                                "center": CENTER_PRIMARY}, timeout=30)
        assert r.status_code == 200, r.text

        # Status for PB-HSR -> locked, scope=center
        s1 = requests.post(f"{BASE_URL}/api/attendance-dashboard/lock-status",
                           json={"token": token, "month": TEST_MONTH,
                                 "center": CENTER_PRIMARY}, timeout=30)
        assert s1.status_code == 200, s1.text
        d1 = s1.json()
        assert d1.get("locked") is True
        assert d1.get("scope") == "center", d1

        # Status for PB-MGT -> unlocked
        s2 = requests.post(f"{BASE_URL}/api/attendance-dashboard/lock-status",
                           json={"token": token, "month": TEST_MONTH,
                                 "center": CENTER_SECONDARY}, timeout=30)
        assert s2.status_code == 200, s2.text
        d2 = s2.json()
        assert d2.get("locked") is False, d2

    def test_02_bulk_month_rejected_for_locked_center(self, token):
        payload = {"token": token, "center": CENTER_PRIMARY, "month": TEST_MONTH,
                   "submittedBy": "test", "cells": [
                       {"employeeName": "TEST_EMP", "day": 1, "status": "P", "notes": ""}
                   ]}
        r = requests.post(f"{BASE_URL}/api/bulk_attendance_month", json=payload, timeout=30)
        assert r.status_code == 400, f"Expected 400 when center locked, got {r.status_code}: {r.text}"
        assert "locked" in r.text.lower()

    def test_03_bulk_month_allowed_for_unlocked_center(self, token):
        # PB-MGT should still be writable
        payload = {"token": token, "center": CENTER_SECONDARY, "month": TEST_MONTH,
                   "submittedBy": "test", "cells": []}
        r = requests.post(f"{BASE_URL}/api/bulk_attendance_month", json=payload, timeout=30)
        assert r.status_code == 200, r.text

    def test_04_unlock_center_leaves_others_untouched(self, token):
        # Unlock PB-HSR
        r = requests.post(f"{BASE_URL}/api/attendance-dashboard/lock",
                          json={"token": token, "month": TEST_MONTH, "action": "unlock",
                                "center": CENTER_PRIMARY}, timeout=30)
        assert r.status_code == 200, r.text

        s = requests.post(f"{BASE_URL}/api/attendance-dashboard/lock-status",
                          json={"token": token, "month": TEST_MONTH,
                                "center": CENTER_PRIMARY}, timeout=30)
        assert s.status_code == 200
        assert s.json().get("locked") is False

    def test_05_global_lock_affects_any_center(self, token):
        # Global lock (no center)
        r = requests.post(f"{BASE_URL}/api/attendance-dashboard/lock",
                          json={"token": token, "month": TEST_MONTH, "action": "lock"},
                          timeout=30)
        assert r.status_code == 200, r.text

        for c in [CENTER_PRIMARY, CENTER_SECONDARY]:
            s = requests.post(f"{BASE_URL}/api/attendance-dashboard/lock-status",
                              json={"token": token, "month": TEST_MONTH, "center": c},
                              timeout=30)
            assert s.status_code == 200
            d = s.json()
            assert d.get("locked") is True, f"{c}: {d}"
            assert d.get("scope") == "global", f"{c}: {d}"

        # Writes should be blocked for any center
        payload = {"token": token, "center": CENTER_SECONDARY, "month": TEST_MONTH,
                   "submittedBy": "test", "cells": []}
        w = requests.post(f"{BASE_URL}/api/bulk_attendance_month", json=payload, timeout=30)
        assert w.status_code == 400, w.text

    def test_06_global_unlock_clears_lock(self, token):
        r = requests.post(f"{BASE_URL}/api/attendance-dashboard/lock",
                          json={"token": token, "month": TEST_MONTH, "action": "unlock"},
                          timeout=30)
        assert r.status_code == 200, r.text

        s = requests.post(f"{BASE_URL}/api/attendance-dashboard/lock-status",
                          json={"token": token, "month": TEST_MONTH,
                                "center": CENTER_PRIMARY}, timeout=30)
        assert s.json().get("locked") is False
