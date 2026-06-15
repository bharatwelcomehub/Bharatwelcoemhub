"""
Iteration 91 — Smoke tests for the 5-tab refactor strict-wording regression.
Targets:
  - POST /api/center-accounts/generate-pib  (PB-SN 2026-05) — PDF text must say
    'Revenue & Income Balance Report', 'FRANCHISE OWNER REVENUE SHARE',
    'MANASWINI FOODS PVT LTD REVENUE SHARE'. No 'Profit Share' leak.
  - POST /api/center-accounts/email-pack   (PB-SN 2026-05, format=json) — subject
    must contain 'Revenue Share Report' and body must contain
    '1. PIB Report (Revenue & Income Balance)'.
Auth: Super Admin (9741399190 / 123456 / PB-MGT) -- credentials from
/app/memory/test_credentials.md
"""
import io
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://balance-cascade-fix.preview.emergentagent.com").rstrip("/")

ADMIN_MOBILE = "9741399190"
ADMIN_OTP = "123456"
ADMIN_CENTER = "PB-MGT"

PIB_CENTER = "PB-SN"
PIB_PERIOD = "2026-05"


@pytest.fixture(scope="module")
def auth_token():
    s = requests.Session()
    s.post(f"{BASE_URL}/api/send_otp",
           json={"mobile": ADMIN_MOBILE, "center": ADMIN_CENTER}, timeout=20)
    r = s.post(f"{BASE_URL}/api/verify_otp",
               json={"mobile": ADMIN_MOBILE, "otp": ADMIN_OTP, "center": ADMIN_CENTER},
               timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:300]}"
    j = r.json()
    tok = j.get("token") or j.get("session", {}).get("token")
    assert tok, f"no token in response: {j}"
    return tok


def _pdf_to_text(pdf_bytes):
    """Extract text using pdfminer (already in backend deps)."""
    from pdfminer.high_level import extract_text
    return extract_text(io.BytesIO(pdf_bytes))


# ---------- PIB PDF wording -----------------------------------------------

def test_pib_pdf_strict_revenue_share_wording(auth_token):
    url = f"{BASE_URL}/api/center-accounts/generate-pib"
    r = requests.post(url, json={"center": PIB_CENTER, "month": PIB_PERIOD,
                                 "period": PIB_PERIOD, "token": auth_token}, timeout=60)
    assert r.status_code == 200, f"generate-pib failed: {r.status_code} {r.text[:400]}"
    assert r.headers.get("content-type", "").startswith("application/pdf"), \
        f"expected PDF, got {r.headers.get('content-type')}"
    pdf_bytes = r.content
    assert len(pdf_bytes) > 1000, f"PDF too small: {len(pdf_bytes)} bytes"

    text = _pdf_to_text(pdf_bytes)
    upper = text.upper()

    # Must contain (Revenue Share franchise)
    assert "FRANCHISE OWNER REVENUE SHARE" in upper, \
        f"Missing 'FRANCHISE OWNER REVENUE SHARE'. Sample: {text[:1500]}"
    assert "MANASWINI FOODS PVT LTD REVENUE SHARE" in upper, \
        f"Missing 'MANASWINI FOODS PVT LTD REVENUE SHARE'. Sample: {text[:2000]}"
    assert "Revenue & Income Balance Report" in text or \
           "REVENUE & INCOME BALANCE REPORT" in upper, \
        f"Missing 'Revenue & Income Balance Report'. Sample: {text[:1500]}"

    # Must NOT contain Profit-Share wording
    assert "FRANCHISE OWNER PROFIT SHARE" not in upper, \
        "Forbidden 'FRANCHISE OWNER PROFIT SHARE' leaked into Revenue-Share PIB"
    assert "Profit & Income Balance Report" not in text and \
           "PROFIT & INCOME BALANCE REPORT" not in upper, \
        "Forbidden 'Profit & Income Balance Report' leaked into Revenue-Share PIB"
    assert "MANASWINI FOODS PVT LTD PROFIT SHARE" not in upper, \
        "Forbidden 'MANASWINI FOODS PVT LTD PROFIT SHARE' leaked into Revenue-Share PIB"


# ---------- Email Pack wording --------------------------------------------

def test_email_pack_strict_revenue_share_wording(auth_token):
    url = f"{BASE_URL}/api/center-accounts/email-pack"
    r = requests.post(url, json={"center": PIB_CENTER, "month": PIB_PERIOD,
                                 "period": PIB_PERIOD, "format": "json",
                                 "token": auth_token}, timeout=60)
    assert r.status_code == 200, f"email-pack failed: {r.status_code} {r.text[:400]}"
    j = r.json()
    # response may be wrapped — try both top-level and nested
    payload = j.get("email") or j.get("pack") or j
    subject = payload.get("subject") or j.get("subject") or ""
    body = payload.get("body") or j.get("body") or payload.get("text") or ""
    assert subject, f"no subject in email pack response: keys={list(j.keys())}"
    assert body, f"no body in email pack response: keys={list(j.keys())}"

    # Strict wording
    assert "Revenue Share Report" in subject, \
        f"subject missing 'Revenue Share Report': {subject!r}"
    assert "Profit Share" not in subject, \
        f"subject leaks 'Profit Share': {subject!r}"

    assert "1. PIB Report (Revenue & Income Balance)" in body, \
        f"body missing '1. PIB Report (Revenue & Income Balance)'. Body head: {body[:600]}"
    assert "Profit & Income Balance" not in body, \
        f"body leaks 'Profit & Income Balance'. Body head: {body[:600]}"
    assert "Profit Share" not in body, \
        f"body leaks 'Profit Share'. Body head: {body[:600]}"
