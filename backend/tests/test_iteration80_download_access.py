"""Iteration 80: Downloads access control regression.

Validates the fixes for:
  - Franchise Owner ledger 500 → clean 403 on unreleased month
  - Owner ledger always allowed for FO of that center
  - Super Admin can download PIB / GST / Comm / Bank / Sales-Ledger even for
    unreleased months
  - franchise PDF range download as franchise owner returns 200
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

SA_MOBILE = "9741399190"
FO_MOBILE = "8888888888"
OTP = "123456"
SA_CENTER = "PB-MGT"
FO_CENTER = "PB-HSR"

# An "unreleased" month that has not been released to FOs. Test month chosen
# is intentionally a future / non-released month per the review request.
UNRELEASED_MONTH = "2026-02"


# ---------- helpers ----------
def _login(mobile: str, center: str) -> str:
    s = requests.Session()
    s.post(f"{BASE_URL}/api/send_otp", json={"mobile": mobile, "center": center}, timeout=30)
    r = s.post(f"{BASE_URL}/api/verify_otp",
               json={"mobile": mobile, "otp": OTP, "center": center}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    return r.json().get("token")


@pytest.fixture(scope="module")
def sa_token():
    return _login(SA_MOBILE, SA_CENTER)


@pytest.fixture(scope="module")
def fo_token():
    try:
        return _login(FO_MOBILE, FO_CENTER)
    except Exception as e:
        pytest.skip(f"Franchise owner login failed: {e}")


# Ensure the test month is NOT released to FO (idempotent best-effort revoke)
@pytest.fixture(scope="module", autouse=True)
def _ensure_unreleased(sa_token):
    try:
        # Revoke general visibility
        requests.post(f"{BASE_URL}/api/owner-reports/set-visibility",
                      json={"token": sa_token, "center": FO_CENTER,
                            "month": UNRELEASED_MONTH, "ready": False},
                      timeout=30)
        # Revoke owner-ledger release (correct schema = action: 'revoke')
        requests.post(f"{BASE_URL}/api/ledgers/owner/release",
                      json={"token": sa_token, "center": FO_CENTER,
                            "month": UNRELEASED_MONTH, "action": "revoke"},
                      timeout=30)
    except Exception:
        pass


# ---------- Ledgers — franchise owner ----------
class TestFOLedgerAccess:
    def test_sales_ledger_unreleased_returns_403_not_500(self, fo_token):
        """Was 500 (AttributeError on roles dict). Must now be a clean 403."""
        r = requests.post(f"{BASE_URL}/api/ledgers/sales",
                          json={"token": fo_token, "center": FO_CENTER,
                                "period_type": "month", "month": UNRELEASED_MONTH,
                                "fmt": "pdf"}, timeout=60)
        assert r.status_code == 403, f"Expected 403, got {r.status_code} body={r.text[:300]}"
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        # Validate clear, helpful message
        msg = (body.get("detail") or "").lower()
        assert "release" in msg or "not available" in msg or "authorized" in msg, \
            f"Error message not clear: {body}"

    def test_owner_ledger_returns_200_pdf(self, fo_token):
        """Owner ledger for FO of that center is always allowed (no release gate)."""
        r = requests.post(f"{BASE_URL}/api/ledgers/owner",
                          json={"token": fo_token, "center": FO_CENTER,
                                "period_type": "month", "month": UNRELEASED_MONTH,
                                "fmt": "pdf"}, timeout=120)
        assert r.status_code == 200, f"got {r.status_code} body={r.text[:300]}"
        ct = r.headers.get("content-type", "")
        assert "pdf" in ct.lower(), f"unexpected content-type: {ct}"
        assert len(r.content) > 500, "PDF body suspiciously small"

    def test_other_center_ledger_forbidden(self, fo_token):
        """FO must not be able to read another center's ledger."""
        r = requests.post(f"{BASE_URL}/api/ledgers/sales",
                          json={"token": fo_token, "center": "PB-MGT",
                                "period_type": "month", "month": UNRELEASED_MONTH,
                                "fmt": "pdf"}, timeout=30)
        assert r.status_code == 403, f"got {r.status_code} {r.text[:200]}"


# ---------- Ledgers — super admin ----------
class TestSuperAdminLedgerBypass:
    def test_sales_ledger_unreleased_returns_200(self, sa_token):
        """Super Admin can download even when month is not released."""
        r = requests.post(f"{BASE_URL}/api/ledgers/sales",
                          json={"token": sa_token, "center": FO_CENTER,
                                "period_type": "month", "month": UNRELEASED_MONTH,
                                "fmt": "pdf"}, timeout=120)
        assert r.status_code == 200, f"got {r.status_code} body={r.text[:300]}"
        assert "pdf" in r.headers.get("content-type", "").lower()
        assert len(r.content) > 500


# ---------- Center Accounts — super admin bypass ----------
class TestCenterAccountsSuperAdminBypass:
    @pytest.mark.parametrize("path", [
        "/api/center-accounts/generate-pib",
        "/api/center-accounts/generate-gst-summary",
        "/api/center-accounts/generate-commission-summary",
        "/api/center-accounts/generate-bank-statement",
    ])
    def test_generate_returns_200_for_unreleased(self, sa_token, path):
        r = requests.post(f"{BASE_URL}{path}",
                          json={"token": sa_token, "center": FO_CENTER,
                                "month": UNRELEASED_MONTH}, timeout=120)
        assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:300]}"
        ct = r.headers.get("content-type", "").lower()
        # Could be PDF or JSON wrapper — accept either
        assert "pdf" in ct or "json" in ct, f"{path}: unexpected ct={ct}"
        if "pdf" in ct:
            assert len(r.content) > 500, f"{path}: body too small"


# ---------- Center Accounts — FO 403 on unreleased ----------
class TestCenterAccountsFOForbidden:
    def test_pib_unreleased_returns_403(self, fo_token):
        r = requests.post(f"{BASE_URL}/api/center-accounts/generate-pib",
                          json={"token": fo_token, "center": FO_CENTER,
                                "month": UNRELEASED_MONTH}, timeout=60)
        assert r.status_code == 403, f"got {r.status_code} {r.text[:300]}"
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        msg = (body.get("detail") or "").lower()
        assert "release" in msg or "not available" in msg or "not authorized" in msg, body


# ---------- MIS franchise PDF (range download) ----------
class TestMISFranchisePDF:
    def test_franchise_pdf_as_fo_returns_200(self, fo_token):
        r = requests.post(f"{BASE_URL}/api/mis/franchise-pdf",
                          json={"token": fo_token, "center": FO_CENTER,
                                "from_date": "2026-01-01", "to_date": "2026-01-31"},
                          timeout=120)
        assert r.status_code == 200, f"got {r.status_code} {r.text[:300]}"
        assert "pdf" in r.headers.get("content-type", "").lower()
        assert len(r.content) > 500
