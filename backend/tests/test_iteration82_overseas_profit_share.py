"""Iteration 82 — Overseas Profit Share (PB-PERTH) vs India MG/Rev-Share (PB-HSR).

Validates per the review request:
  - /api/center-accounts/summary returns overseas_share & mfpl_royalty for AU,
    and mg_calculation for India.
  - /api/center-accounts/payout-summary zeros MG for overseas; preserves MG for India.
  - /api/ledgers/owner returns data.overseas flag, profit-share rows for AU, MG rows for India.
  - /api/ledgers/owner fmt=pdf returns a valid PDF for AU.
  - /api/center-accounts/generate-pib returns valid PDF for both AU and India.
"""
import os
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()
           ).rstrip("/")

SUPER_ADMIN = {"mobile": "9741399190", "otp": "123456", "center": "PB-MGT"}
MONTH = "2026-01"
PERTH = "PB-PERTH"
HSR = "PB-HSR"


# ----- Fixtures -----------------------------------------------------------------
@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/verify_otp", json=SUPER_ADMIN, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _post(path, payload, token, timeout=60):
    body = {"token": token, **payload}
    return requests.post(f"{BASE_URL}{path}", json=body, timeout=timeout)


# ----- /center-accounts/summary -------------------------------------------------
class TestSummaryOverseas:
    def test_perth_summary_overseas_payload(self, token):
        r = _post("/api/center-accounts/summary", {"center": PERTH, "month": MONTH}, token)
        assert r.status_code == 200, r.text
        s = r.json().get("summary", {})

        # Country detection
        assert (s.get("country") or "").lower() == "australia", f"country={s.get('country')}"

        # MG must be absent (null/None) for overseas
        assert s.get("mg_calculation") in (None, {}, []), f"mg_calculation should be empty for AU; got {s.get('mg_calculation')}"

        ov = s.get("overseas_share")
        assert ov is not None, "overseas_share missing"
        for k in ("eligible_profit", "owner_share", "franchisor_share", "mfpl_royalty"):
            assert k in ov, f"overseas_share missing {k}"
        # Owner is 80%, franchisor 20% of eligible profit
        ep = float(ov["eligible_profit"])
        if ep > 0:
            assert abs(float(ov["owner_share"]) - ep * 0.80) <= 1.0, ov
            assert abs(float(ov["franchisor_share"]) - ep * 0.20) <= 1.0, ov

        mfpl = s.get("mfpl_royalty")
        assert mfpl is not None, "mfpl_royalty missing"
        assert "monthly" in mfpl or "monthly_data" in mfpl or isinstance(mfpl.get("monthly"), list)
        assert "cumulative_mfpl" in mfpl
        assert "outstanding_mfpl" in mfpl

        po = s.get("payout") or {}
        assert (po.get("type") or "").lower() == "profit_share", f"payout.type={po.get('type')}"


class TestSummaryIndia:
    def test_hsr_summary_india_payload(self, token):
        r = _post("/api/center-accounts/summary", {"center": HSR, "month": MONTH}, token)
        assert r.status_code == 200, r.text
        s = r.json().get("summary", {})

        # India parity
        country = (s.get("country") or "India").lower()
        assert country == "india", f"country={country}"

        assert s.get("mg_calculation") is not None, "mg_calculation must be present for India"
        assert s.get("overseas_share") in (None, {}, []), f"overseas_share must be absent for India; got {s.get('overseas_share')}"
        assert s.get("mfpl_royalty") in (None, {}, []), f"mfpl_royalty must be absent for India; got {s.get('mfpl_royalty')}"

        po = s.get("payout") or {}
        ptype = (po.get("type") or "").lower()
        assert ptype in ("revenue_share", "minimum_guarantee", "mg"), f"payout.type={ptype}"


# ----- /center-accounts/payout-summary -----------------------------------------
class TestPayoutSummary:
    def test_perth_payout_zero_mg(self, token):
        r = _post("/api/center-accounts/payout-summary",
                  {"center": PERTH, "from_month": MONTH, "to_month": MONTH}, token)
        assert r.status_code == 200, r.text
        body = r.json()
        franchise = body.get("franchise", {}) or {}
        totals = body.get("totals", {}) or {}
        monthly = body.get("monthly_data", []) or []
        assert float(franchise.get("mg_amount") or 0) == 0.0, franchise
        assert float(totals.get("mg") or 0) == 0.0, totals
        for m in monthly:
            assert float(m.get("mg_amount") or 0) == 0.0, m
        # Revenue share should reflect 80% of eligible profit (positive when profit > 0)
        if monthly:
            rs = float(monthly[0].get("revenue_share") or 0)
            assert rs >= 0.0  # presence check; sign should not be negative

    def test_hsr_payout_mg_preserved(self, token):
        r = _post("/api/center-accounts/payout-summary",
                  {"center": HSR, "from_month": MONTH, "to_month": MONTH}, token)
        assert r.status_code == 200, r.text
        body = r.json()
        # MG fields must exist (value may be 0 if RS won)
        assert "mg_amount" in (body.get("franchise") or {})
        assert "mg" in (body.get("totals") or {})


# ----- /ledgers/owner ----------------------------------------------------------
class TestOwnerLedger:
    def test_perth_owner_ledger_json(self, token):
        r = _post("/api/ledgers/owner",
                  {"center": PERTH, "period_type": "month", "month": MONTH, "fmt": "json"}, token)
        assert r.status_code == 200, r.text
        data = r.json().get("data") or r.json()
        assert data.get("overseas") is True, f"overseas flag missing/false: {data.get('overseas')}"
        assert float(data.get("total_mfpl_accrued") or 0) >= 0.0
        rows = data.get("rows") or []
        text_blob = " | ".join((r_.get("particulars") or r_.get("description") or "")
                               for r_ in rows).lower()
        # No MG top-up rows
        assert "mg top-up" not in text_blob and "minimum guarantee top" not in text_blob, text_blob
        # Profit share rows present
        assert "profit share payable" in text_blob, f"missing 'Profit Share payable' row: {text_blob}"
        assert "gst on profit share" in text_blob, f"missing 'GST on Profit Share' row: {text_blob}"

    def test_hsr_owner_ledger_json(self, token):
        r = _post("/api/ledgers/owner",
                  {"center": HSR, "period_type": "month", "month": MONTH, "fmt": "json"}, token)
        assert r.status_code == 200, r.text
        data = r.json().get("data") or r.json()
        assert data.get("overseas") in (False, None), f"overseas flag should be false for India: {data.get('overseas')}"
        rows = data.get("rows") or []
        text_blob = " | ".join((r_.get("particulars") or r_.get("description") or "")
                               for r_ in rows).lower()
        assert "revenue share payable" in text_blob or "minimum guarantee" in text_blob or "mg top-up" in text_blob, text_blob

    def test_perth_owner_ledger_pdf(self, token):
        r = _post("/api/ledgers/owner",
                  {"center": PERTH, "period_type": "month", "month": MONTH, "fmt": "pdf"},
                  token, timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"%PDF", r.content[:50]
        assert len(r.content) > 50_000, f"PDF too small: {len(r.content)}B"


# ----- /center-accounts/generate-pib -------------------------------------------
class TestGeneratePIB:
    def test_perth_pib_pdf(self, token):
        r = _post("/api/center-accounts/generate-pib",
                  {"center": PERTH, "month": MONTH}, token, timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 30_000

    def test_hsr_pib_pdf(self, token):
        r = _post("/api/center-accounts/generate-pib",
                  {"center": HSR, "month": MONTH}, token, timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 30_000
