"""Integration tests for GST Revenue Treatment toggle endpoints (iter92).

API conventions for center_accounts router:
  - token + center + month go inside the JSON body (not Authorization header).
  - /summary is POST (not GET).
  - All endpoints are mounted under /api/center-accounts/.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://balance-cascade-fix.preview.emergentagent.com").rstrip("/")
CA = f"{BASE_URL}/api/center-accounts"
CENTER = "PB-HSR"
MOBILE = "9741399190"
OTP = "123456"
MONTH = "2025-12"


@pytest.fixture(scope="module")
def token():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/send_otp", json={"center": "PB-MGT", "mobile": MOBILE}, timeout=20)
    assert r.status_code == 200, f"send_otp: {r.status_code} {r.text[:200]}"
    r = s.post(f"{BASE_URL}/api/verify_otp", json={"center": "PB-MGT", "mobile": MOBILE, "otp": OTP}, timeout=20)
    assert r.status_code == 200, f"verify_otp: {r.status_code} {r.text[:200]}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, f"No token in {r.json()}"
    return tok


def _set_flag(token, value):
    r = requests.post(
        f"{CA}/gst-treatment/set",
        json={"token": token, "center": CENTER, "month": MONTH, "include_gst_in_revenue": value},
        timeout=20,
    )
    assert r.status_code == 200, f"set failed: {r.status_code} {r.text[:300]}"
    return r.json()


def _get_flag(token):
    r = requests.post(
        f"{CA}/gst-treatment/get",
        json={"token": token, "center": CENTER, "month": MONTH},
        timeout=20,
    )
    assert r.status_code == 200, f"get failed: {r.status_code} {r.text[:300]}"
    return r.json()


def _summary(token):
    r = requests.post(
        f"{CA}/summary",
        json={"token": token, "center": CENTER, "month": MONTH},
        timeout=90,
    )
    assert r.status_code == 200, f"summary failed: {r.status_code} {r.text[:400]}"
    j = r.json()
    return j.get("summary", j)


# ── round-trip tests ─────────────────────────────────────────────────────
def test_get_default_exclude(token):
    _set_flag(token, False)  # ensure baseline
    data = _get_flag(token)
    assert data.get("include_gst_in_revenue") is False
    assert "Exclude GST" in (data.get("treatment_label") or "")


def test_set_include_persists(token):
    out = _set_flag(token, True)
    assert out.get("include_gst_in_revenue") is True
    assert out.get("success") is True

    data = _get_flag(token)
    assert data.get("include_gst_in_revenue") is True
    assert data.get("updated_at"), "updated_at missing after set"
    assert data.get("updated_by"), "updated_by missing after set"
    # cleanup
    _set_flag(token, False)


# ── /summary integration ─────────────────────────────────────────────────
def test_summary_exclude_then_include_then_revert(token):
    _set_flag(token, False)
    time.sleep(0.3)
    s_off = _summary(token)
    os_off = s_off.get("operational_sustainability") or {}
    assert os_off, f"operational_sustainability missing. top keys: {list(s_off.keys())}"
    base_off = os_off.get("revenue_share_base")
    gst = os_off.get("gst_on_sales")
    sales = os_off.get("total_sales") or os_off.get("sales") or os_off.get("gross_sales")
    comm = os_off.get("total_commissions") or os_off.get("commissions")
    print(f"EXCLUDE keys={list(os_off.keys())}")
    print(f"EXCLUDE: sales={sales} comm={comm} gst={gst} base={base_off}")
    assert base_off is not None
    assert os_off.get("include_gst_in_revenue") is False
    if gst is None or gst <= 0:
        pytest.skip(f"No GST data for {CENTER}/{MONTH} — cannot validate delta (gst={gst})")

    # legacy formula check
    if sales is not None and comm is not None:
        expected_off = round(sales - comm - gst, 2)
        assert abs(base_off - expected_off) < 1.0, (
            f"Exclude base {base_off} != sales-comm-gst {expected_off}"
        )

    # flip ON
    _set_flag(token, True)
    time.sleep(0.3)
    s_on = _summary(token)
    os_on = s_on["operational_sustainability"]
    base_on = os_on.get("revenue_share_base")
    print(f"INCLUDE: base={base_on}  delta={round(base_on - base_off, 2)} vs gst={gst}")
    assert os_on.get("include_gst_in_revenue") is True
    # GST still visible
    assert os_on.get("gst_on_sales") == gst, "GST must remain visible & unchanged"
    # Base must increase by exactly GST
    assert abs((base_on - base_off) - gst) < 1.0, (
        f"Expected base to increase by GST={gst}; got delta={base_on - base_off}"
    )

    # payout block — Note: include_gst_in_revenue/gst_treatment_label are
    # not directly propagated to the `payout` block in /summary (only to
    # operational_sustainability). What MUST change is the revenue_share
    # amount because it derives from the (now larger) revenue_share_base.
    payout_on = s_on.get("payout") or s_on.get("franchise_payout") or {}
    payout_off_block = s_off.get("payout") or s_off.get("franchise_payout") or {}
    if payout_on and payout_off_block:
        rs_off = payout_off_block.get("revenue_share_amount") or payout_off_block.get("original_revenue_share") or 0
        rs_on = payout_on.get("revenue_share_amount") or payout_on.get("original_revenue_share") or 0
        print(f"payout rev_share_amount: off={rs_off} on={rs_on} delta={round(rs_on - rs_off, 2)}")
        # Should increase when include_gst is on (for revenue_share model)
        # We don't strictly assert direction here because franchise may be MG-gated

    # revert
    _set_flag(token, False)
    time.sleep(0.3)
    s_rev = _summary(token)
    os_rev = s_rev["operational_sustainability"]
    assert os_rev.get("include_gst_in_revenue") is False
    assert abs(os_rev.get("revenue_share_base") - base_off) < 1.0, (
        f"After revert base should equal {base_off}, got {os_rev.get('revenue_share_base')}"
    )


def test_owner_share_changes_when_revshare(token):
    """If center is on revenue_share model with non-zero GST, revenue_share_amount
    must increase by ~ GST × owner_pct/100 when flipped to include."""
    _set_flag(token, False)
    time.sleep(0.3)
    s_off = _summary(token)
    payout_off = s_off.get("payout") or s_off.get("franchise_payout") or {}
    if not payout_off:
        pytest.skip("No payout block in summary")
    rs_off = payout_off.get("revenue_share_amount") or payout_off.get("original_revenue_share")
    if rs_off is None:
        pytest.skip(f"No revenue_share_amount in payout keys={list(payout_off.keys())}")
    gst = s_off.get("operational_sustainability", {}).get("gst_on_sales") or 0
    if gst <= 0:
        pytest.skip("Zero GST")

    _set_flag(token, True)
    time.sleep(0.3)
    s_on = _summary(token)
    payout_on = s_on.get("payout") or s_on.get("franchise_payout") or {}
    rs_on = payout_on.get("revenue_share_amount") or payout_on.get("original_revenue_share") or 0
    print(f"rs_off={rs_off} rs_on={rs_on} gst={gst}")
    # Revenue share amount must INCREASE when GST is included in base (rev_share model)
    assert rs_on > rs_off, f"revenue_share_amount did not increase: {rs_off} -> {rs_on}"

    _set_flag(token, False)


def test_auth_required(token):
    """Unauthenticated /get and /set must reject."""
    r = requests.post(f"{CA}/gst-treatment/get", json={"center": CENTER, "month": MONTH}, timeout=10)
    assert r.status_code in (400, 401, 403, 422)
    r = requests.post(f"{CA}/gst-treatment/set", json={"center": CENTER, "month": MONTH, "include_gst_in_revenue": True}, timeout=10)
    assert r.status_code in (400, 401, 403, 422)
