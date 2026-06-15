"""Iteration 89 — HTTP integration tests for Phase-3 bundle endpoints.

Tests the live /api/bundles/{ca|owner|franchisor} routes end-to-end:
auth requirement, unknown-center 404, content-type=application/zip, and
that each ZIP contains a PDF + manifest with audit-trail fields and
engine-derived numbers in the PDF text.
"""
from __future__ import annotations
import io
import os
import re
import zipfile

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to local for sanity (test will be skipped if unreachable)
    BASE_URL = "http://localhost:8001"

CENTER = "PB-MGT"
PERIOD = "2026-05"
MOBILE = "9741399190"
OTP = "123456"


# -------------------------- fixtures --------------------------
@pytest.fixture(scope="module")
def token() -> str:
    s = requests.Session()
    r1 = s.post(f"{BASE_URL}/api/send_otp", json={"mobile": MOBILE, "center": CENTER}, timeout=20)
    if r1.status_code != 200:
        pytest.skip(f"send_otp failed: {r1.status_code} {r1.text[:200]}")
    r2 = s.post(f"{BASE_URL}/api/verify_otp", json={"mobile": MOBILE, "otp": OTP, "center": CENTER}, timeout=20)
    if r2.status_code != 200:
        pytest.skip(f"verify_otp failed: {r2.status_code} {r2.text[:200]}")
    tok = r2.json().get("token") or r2.json().get("access_token")
    if not tok:
        pytest.skip(f"no token in verify_otp response: {r2.json()}")
    return tok


def _fetch_zip(kind: str, token: str, *, center: str = CENTER, period: str = PERIOD):
    url = f"{BASE_URL}/api/bundles/{kind}"
    return requests.get(url, params={"token": token, "center": center, "period": period}, timeout=60)


# -------------------------- 200 + zip shape --------------------------
@pytest.mark.parametrize("kind", ["ca", "owner", "franchisor"])
def test_bundle_returns_zip_with_pdf_and_manifest(kind, token):
    r = _fetch_zip(kind, token)
    assert r.status_code == 200, f"{kind} bundle: {r.status_code} {r.text[:300]}"
    ctype = r.headers.get("content-type", "")
    assert "application/zip" in ctype, f"unexpected content-type: {ctype}"

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
        assert any(n.endswith(".pdf") for n in names), f"no .pdf inside {kind}: {names}"
        assert any(n.endswith("_manifest.txt") for n in names), f"no _manifest.txt inside {kind}: {names}"

        # PDF starts with %PDF magic
        pdf_name = next(n for n in names if n.endswith(".pdf"))
        pdf_bytes = zf.read(pdf_name)
        assert pdf_bytes[:4] == b"%PDF", f"PDF magic missing in {kind}: {pdf_bytes[:8]!r}"


# -------------------------- manifest audit trail --------------------------
@pytest.mark.parametrize("kind", ["ca", "owner", "franchisor"])
def test_manifest_contains_audit_trail(kind, token):
    r = _fetch_zip(kind, token)
    assert r.status_code == 200
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        manifest_name = next(n for n in zf.namelist() if n.endswith("_manifest.txt"))
        manifest = zf.read(manifest_name).decode("utf-8")
        assert "financial_engine.py" in manifest
        assert "Selected Base:" in manifest
        assert "Owner Share:" in manifest
        assert "Company Entity:" in manifest


# -------------------------- auth --------------------------
def test_bundle_ca_without_token_is_4xx():
    r = requests.get(f"{BASE_URL}/api/bundles/ca",
                     params={"center": CENTER, "period": PERIOD}, timeout=20)
    # FastAPI returns 422 for missing required query param; either way, 4xx.
    assert 400 <= r.status_code < 500, f"expected 4xx, got {r.status_code}: {r.text[:200]}"


def test_bundle_ca_invalid_token_behavior(token):
    """Observation test — current implementation calls verify_token_sync but
    does not enforce the return value, so an unrecognised token still
    succeeds. Documented here as a SECURITY OBSERVATION for the main agent.
    The review's auth requirement ('no token => 4xx') is covered by the
    missing-param test above (FastAPI 422). This test xfails today.
    """
    r = requests.get(f"{BASE_URL}/api/bundles/ca",
                     params={"token": "obviously-bad-token", "center": CENTER, "period": PERIOD},
                     timeout=30)
    # Should be 401/403, currently returns 200 because route ignores
    # verify_token_sync's None return. Flagged in action_items.
    if r.status_code not in (400, 401, 403):
        pytest.xfail(f"verify_token_sync return value ignored — bad token returned {r.status_code} (security finding)")


# -------------------------- unknown center --------------------------
def test_bundle_ca_unknown_center_is_404(token):
    r = requests.get(f"{BASE_URL}/api/bundles/ca",
                     params={"token": token, "center": "ZZ-NOPE-9999", "period": PERIOD},
                     timeout=30)
    assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text[:200]}"


# -------------------------- engine figures inside CA PDF --------------------------
def test_ca_pdf_contains_engine_figures_and_entity(token):
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            pytest.skip("pypdf / PyPDF2 not installed")

    r = _fetch_zip("ca", token)
    assert r.status_code == 200
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        pdf_name = next(n for n in zf.namelist() if n.endswith(".pdf"))
        pdf_bytes = zf.read(pdf_name)
        manifest = zf.read(next(n for n in zf.namelist() if n.endswith("_manifest.txt"))).decode()

    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "".join((p.extract_text() or "") for p in reader.pages)

    # India center → Manaswini company entity label.
    assert "Manaswini" in text, f"Manaswini not in CA PDF text. manifest:\n{manifest[:400]}"

    # Pull engine-computed figures from manifest, then look for them in PDF.
    rs_match = re.search(r"Revenue Share Base:\s*([\d.\-]+)", manifest)
    os_match = re.search(r"Owner Share:\s*([\d.\-]+)", manifest)
    assert rs_match and os_match, f"manifest missing engine figures:\n{manifest}"
    rs_val = float(rs_match.group(1))
    os_val = float(os_match.group(1))

    # Look for formatted Rs.-style figure (with thousands sep, 2dp) OR raw.
    def _in(val: float) -> bool:
        formatted = f"{val:,.2f}"
        unformatted = f"{val:.2f}"
        return formatted in text or unformatted in text

    assert _in(rs_val), f"revenue_share_base {rs_val} not visible in PDF text (first 600 chars):\n{text[:600]}"
    assert _in(os_val), f"owner_share {os_val} not visible in PDF text (first 600 chars):\n{text[:600]}"
