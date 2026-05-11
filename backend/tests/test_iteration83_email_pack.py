"""Iteration 83 backend tests:
- POST /api/center-accounts/email-pack (JSON + ZIP) for PB-HSR / PB-PERTH 2026-01
- MFPL gating: 2026-01 < 2026-04 must return 0 cumulative MFPL for PB-PERTH
- Owner Ledger MFPL gating for PB-PERTH 2026-01
- delete_advance permissions (super admin, 404, 403)
"""
import os
import io
import json
import zipfile
import pytest
import requests

# Load REACT_APP_BACKEND_URL from frontend/.env (required for proper k8s routing)
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    try:
        with open("/app/frontend/.env") as _f:
            for _line in _f:
                if _line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = _line.split("=", 1)[1].strip()
                    break
    except Exception:
        pass
assert BASE_URL, "REACT_APP_BACKEND_URL missing"
BASE_URL = BASE_URL.rstrip("/")

SUPER_ADMIN_MOBILE = "9741399190"
OTP = "123456"


def _login(mobile=SUPER_ADMIN_MOBILE, center="PB-MGT"):
    r = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": mobile, "center": center}, timeout=20)
    assert r.status_code == 200, f"send_otp failed: {r.text}"
    r = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": mobile, "otp": OTP, "center": center}, timeout=20)
    assert r.status_code == 200, f"verify_otp failed: {r.text}"
    return r.json().get("token")


@pytest.fixture(scope="module")
def sa_token():
    tok = _login()
    if not tok:
        pytest.skip("Cannot obtain super-admin token")
    return tok


# -----------------------------
# MFPL Gating tests (Perth, 2026-01 must be 0)
# -----------------------------
class TestMFPLGating:
    def test_summary_perth_pre_april_mfpl_zero(self, sa_token):
        body = {"token": sa_token, "center": "PB-PERTH", "month": "2026-01"}
        r = requests.post(f"{BASE_URL}/api/center-accounts/summary", json=body, timeout=60)
        assert r.status_code == 200, f"summary failed: {r.text[:500]}"
        envelope = r.json()
        data = envelope.get("summary") or envelope
        mfpl = data.get("mfpl_royalty") or {}
        assert mfpl.get("cumulative_mfpl", -1) == 0.0, f"expected cumulative_mfpl=0 got {mfpl}"
        assert mfpl.get("outstanding_mfpl", -1) == 0.0, f"expected outstanding_mfpl=0"
        assert mfpl.get("monthly", None) == [], f"expected monthly=[] got {mfpl.get('monthly')}"
        os_share = data.get("overseas_share") or {}
        assert os_share.get("mfpl_royalty", -1) == 0.0, f"overseas_share.mfpl_royalty must be 0 pre-April, got {os_share}"
        # Make sure owner/franchisor share are still computed
        assert os_share.get("owner_share", 0) > 0, f"owner_share should still be > 0: {os_share}"
        assert os_share.get("franchisor_share", 0) > 0, f"franchisor_share should still be > 0: {os_share}"

    def test_owner_ledger_perth_pre_april_mfpl_zero(self, sa_token):
        body = {"token": sa_token, "center": "PB-PERTH", "period_type": "month", "month": "2026-01", "fmt": "json"}
        r = requests.post(f"{BASE_URL}/api/ledgers/owner", json=body, timeout=60)
        assert r.status_code == 200, f"owner ledger failed: {r.text[:500]}"
        j = r.json()
        d = j.get("data") or j
        accrued = d.get("total_mfpl_accrued", None)
        if accrued is None:
            accrued = (d.get("summary") or {}).get("total_mfpl_accrued")
        assert accrued == 0.0, f"expected total_mfpl_accrued=0 got {accrued}"


# -----------------------------
# Email Pack tests
# -----------------------------
class TestEmailPack:
    def test_email_pack_json_hsr(self, sa_token):
        body = {"token": sa_token, "center": "PB-HSR", "month": "2026-01", "format": "json"}
        r = requests.post(f"{BASE_URL}/api/center-accounts/email-pack", json=body, timeout=120)
        assert r.status_code == 200, f"email-pack json failed: {r.text[:500]}"
        j = r.json()
        subj = j.get("subject", "")
        body_txt = j.get("body", "")
        attachments = j.get("attachments", [])
        assert subj.startswith("Purnabramha — "), f"subject prefix wrong: {subj!r}"
        assert body_txt.startswith("Jai Hind Namaskar Team "), f"body greeting wrong: {body_txt[:80]!r}"
        assert "With warm regards and gratitude" in body_txt, "missing warm regards"
        assert "— Purnabramha Accounts Team" in body_txt, "missing accounts team sign-off"
        names = [a.get("filename", "") for a in attachments]
        for token in ["PIB", "GST_Summary", "Commission_Summary", "Owner_Ledger", "Bank_Statement"]:
            assert any(token in n for n in names), f"attachment {token} missing from {names}"

    def test_email_pack_json_perth_aud(self, sa_token):
        body = {"token": sa_token, "center": "PB-PERTH", "month": "2026-01", "format": "json"}
        r = requests.post(f"{BASE_URL}/api/center-accounts/email-pack", json=body, timeout=120)
        assert r.status_code == 200, f"email-pack json perth failed: {r.text[:500]}"
        j = r.json()
        body_txt = j.get("body", "") + " " + j.get("subject", "")
        assert "AUD" in body_txt or "A$" in body_txt, f"AUD currency missing for PERTH: subj/body={body_txt[:200]!r}"
        assert "Jai Hind Namaskar Team " in j.get("body", ""), "greeting missing"

    def test_email_pack_zip_hsr(self, sa_token):
        body = {"token": sa_token, "center": "PB-HSR", "month": "2026-01", "format": "zip"}
        r = requests.post(f"{BASE_URL}/api/center-accounts/email-pack", json=body, timeout=180)
        assert r.status_code == 200, f"email-pack zip failed: {r.text[:300]}"
        ctype = r.headers.get("content-type", "")
        assert "application/zip" in ctype, f"wrong content-type: {ctype}"
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower(), f"missing attachment disposition: {cd}"
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
        assert any(n.upper() == "EMAIL.TXT" or n.upper().endswith("EMAIL.TXT") for n in names), f"EMAIL.txt missing: {names}"
        pdf_count = sum(1 for n in names if n.lower().endswith(".pdf"))
        assert pdf_count >= 1, f"Expected PDFs in zip, got names={names}"


# -----------------------------
# delete_advance permission tests
# -----------------------------
class TestDeleteAdvance:
    def test_super_admin_delete_nonexistent_returns_404(self, sa_token):
        body = {
            "token": sa_token,
            "center": "PB-HSR",
            "date": "1999-01-01",
            "employeeName": "ZZZ_DOES_NOT_EXIST",
        }
        r = requests.post(f"{BASE_URL}/api/delete_advance", json=body, timeout=20)
        assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text[:200]}"

    def test_super_admin_create_and_delete_advance(self, sa_token):
        # Create a TEST advance via bulk_advances
        emp = "TEST_ITER83_ADV"
        date = "2025-12-31"
        create = {
            "token": sa_token,
            "center": "PB-HSR",
            "date": date,
            "rows": [{"employeeName": emp, "advanceAmount": 100, "mode": "CASH", "notes": "iter83"}],
        }
        r = requests.post(f"{BASE_URL}/api/bulk_advances", json=create, timeout=20)
        assert r.status_code == 200, f"bulk_advances failed: {r.text[:200]}"
        # Delete it
        r = requests.post(
            f"{BASE_URL}/api/delete_advance",
            json={"token": sa_token, "center": "PB-HSR", "date": date, "employeeName": emp},
            timeout=20,
        )
        assert r.status_code == 200, f"super-admin delete failed: {r.text[:200]}"
        j = r.json()
        assert j.get("deleted") == 1

    def test_invalid_token_rejected(self):
        r = requests.post(
            f"{BASE_URL}/api/delete_advance",
            json={"token": "INVALID_TOKEN_XYZ", "center": "PB-HSR", "date": "2025-01-01", "employeeName": "X"},
            timeout=10,
        )
        assert r.status_code == 401, f"expected 401, got {r.status_code}"
