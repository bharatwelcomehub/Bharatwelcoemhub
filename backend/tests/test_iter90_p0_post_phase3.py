"""Iteration 90 — P0 regression: bundles franchise_code, payout_model
toggle on /summary, and the PIB strict labels.

Builds on tests/test_payout_model_strict_pdf.py + tests/test_bundles_endpoints.py.
This file is HTTP-only and re-auths per call to dodge per-pod token gaps
(the in-memory otp_store is not shared across replicas).
"""
from __future__ import annotations
import io
import os
import time
import zipfile
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
MOBILE, OTP, CENTER = "9741399190", "123456", "PB-MGT"


def _auth():
    s = requests.Session()
    r1 = s.post(f"{BASE_URL}/api/send_otp", json={"mobile": MOBILE, "center": CENTER}, timeout=20)
    if r1.status_code != 200:
        pytest.skip(f"send_otp failed: {r1.status_code}")
    r2 = s.post(f"{BASE_URL}/api/verify_otp", json={"mobile": MOBILE, "otp": OTP, "center": CENTER}, timeout=20)
    if r2.status_code != 200:
        pytest.skip(f"verify_otp failed: {r2.status_code}")
    return s, r2.json()["token"]


def _call(method: str, path: str, *, json_body=None, params=None, retries=18):
    last = None
    for _ in range(retries):
        s, tok = _auth()
        if method == "post":
            body = dict(json_body or {}); body["token"] = tok
            r = s.post(f"{BASE_URL}{path}", json=body, timeout=60)
        else:
            qs = dict(params or {}); qs["token"] = tok
            r = s.get(f"{BASE_URL}{path}", params=qs, timeout=60)
        last = r
        if r.status_code in (200, 404):
            return r
        time.sleep(0.4)
    return last


def _manifest(r) -> str:
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    for n in zf.namelist():
        if n.endswith("_manifest.txt"):
            return zf.read(n).decode()
    return ""


# ---- BUG #1: bundle accepts center_code OR franchise_code -------------------
@pytest.mark.parametrize("kind", ["ca", "owner", "franchisor"])
def test_bundle_accepts_franchise_code(kind):
    r = _call("get", f"/api/bundles/{kind}", params={"center": "FR-TEST-INDIA", "period": "2025-12"})
    assert r.status_code == 200, f"{kind} status={r.status_code} body={r.text[:200]}"
    assert "application/zip" in r.headers.get("content-type", "")
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert sum(1 for n in names if n.endswith(".pdf")) == 1
    assert sum(1 for n in names if n.endswith("_manifest.txt")) == 1


def test_bundle_unknown_identifier_is_404():
    r = _call("get", "/api/bundles/ca", params={"center": "ZZ-NOPE-NEVER", "period": "2025-12"})
    assert r.status_code == 404
    assert "No center found" in r.text


# ---- BUG #2 & #3: payout_model toggles propagate everywhere -----------------
def _set_payout(model: str):
    r = _call("post", "/api/franchises/update/FR-TEST-INDIA", json_body={"payout_model": model})
    assert r.status_code == 200, f"toggle to {model} failed: {r.text[:200]}"
    time.sleep(1)


def _check_model(model: str):
    rb = _call("get", "/api/bundles/ca", params={"center": "FR-TEST-INDIA", "period": "2025-12"})
    assert rb.status_code == 200
    m = _manifest(rb)
    assert f"Payout Model: {model}" in m, f"manifest Payout Model mismatch for {model}: {m[:400]}"

    rs = _call("post", "/api/center-accounts/summary", json_body={"center": "PB-HSR", "month": "2025-12"})
    assert rs.status_code == 200
    s = (rs.json() or {}).get("summary") or {}
    assert s.get("payout_model") == model
    word = "Profit Share" if model == "profit_share" else "Revenue Share"
    assert word.upper() in (s.get("section_heading") or "").upper()
    assert word in (s.get("base_label") or "")

    # payout.type & reason — only assert when MG does not win
    mg = (s.get("mg_calculation") or {}) or {}
    mg_amount = float(mg.get("monthly_mg") or mg.get("amount") or 0)
    share_amount = float(((s.get("share_calculation") or {}).get("franchise_owner") or {}).get("amount") or 0)
    p = s.get("payout") or {}
    if mg_amount <= share_amount:
        assert p.get("type") == model
        assert (p.get("reason") or "").startswith(word)


def test_toggle_revenue_share_then_profit_share_then_restore():
    try:
        _set_payout("revenue_share"); _check_model("revenue_share")
        _set_payout("profit_share");  _check_model("profit_share")
    finally:
        # Restore so we don't pollute downstream tests.
        _set_payout("revenue_share")


# ---- Regression: overseas always profit_share -------------------------------
def test_overseas_pb_perth_is_profit_share():
    r = _call("post", "/api/center-accounts/summary", json_body={"center": "PB-PERTH", "month": "2025-12"})
    assert r.status_code == 200
    s = (r.json() or {}).get("summary") or {}
    assert s.get("payout_model") == "profit_share"
    assert "PROFIT SHARE" in (s.get("section_heading") or "").upper()
    assert "Profit Share" in (s.get("base_label") or "")
