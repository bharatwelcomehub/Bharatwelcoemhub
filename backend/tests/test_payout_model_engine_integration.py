"""Iteration 88 — Integration tests for the Financial Calculation Engine
+ Payout Model + Franchise Owner Share % refactor.

These tests hit the LIVE running backend via REACT_APP_BACKEND_URL and
exercise the full HTTP surface (auth → franchise CRUD → center accounts
summary). The Engine's unit-level guarantees are pinned by
test_financial_engine.py — this suite verifies wiring.
"""
from __future__ import annotations
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")

# Super-admin creds from /app/memory/test_credentials.md
ADMIN_MOBILE = "9741399190"
ADMIN_OTP = "123456"
ADMIN_CENTER = "PB-MGT"

# India franchise present in DB (per pre-test inspection)
INDIA_FRANCHISE = "FR-TEST-INDIA"
AUS_FRANCHISE = "FR-PERTH"


# ----------------------------------------------------------------------
# Auth fixture — verifies once per test session
# ----------------------------------------------------------------------
@pytest.fixture(scope="module")
def admin_token() -> str:
    s = requests.Session()
    r = s.post(
        f"{BASE_URL}/api/send_otp",
        json={"mobile": ADMIN_MOBILE, "center": ADMIN_CENTER},
        timeout=15,
    )
    assert r.status_code == 200, f"send_otp failed: {r.status_code} {r.text}"
    r = s.post(
        f"{BASE_URL}/api/verify_otp",
        json={"mobile": ADMIN_MOBILE, "otp": ADMIN_OTP, "center": ADMIN_CENTER},
        timeout=15,
    )
    assert r.status_code == 200, f"verify_otp failed: {r.status_code} {r.text}"
    token = r.json().get("token")
    assert token, f"No token in verify_otp response: {r.json()}"
    return token


@pytest.fixture(scope="module")
def original_india_state(admin_token):
    """Snapshot the India franchise's pre-test state so we can restore it
    at the end of the module — these tests mutate payout_model / share %."""
    r = requests.post(
        f"{BASE_URL}/api/franchises/get/{INDIA_FRANCHISE}",
        json={"token": admin_token},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    fr = r.json()["franchise"]
    snapshot = {
        "payout_model": fr.get("payout_model"),
        "franchise_owner_share_percentage": fr.get("franchise_owner_share_percentage"),
        "revenue_share_percentage": fr.get("revenue_share_percentage"),
        "mg_calculation_applicable": fr.get("mg_calculation_applicable", True),
    }
    yield snapshot
    # Restore — push back whatever was there (use 'revenue_share' if both null,
    # else the original value)
    restore = {
        "token": admin_token,
        "payout_model": snapshot["payout_model"] or "revenue_share",
        "franchise_owner_share_percentage": snapshot["franchise_owner_share_percentage"]
        or snapshot["revenue_share_percentage"]
        or 15.0,
        "mg_calculation_applicable": snapshot["mg_calculation_applicable"]
        if snapshot["mg_calculation_applicable"] is not None
        else True,
    }
    requests.post(
        f"{BASE_URL}/api/franchises/update/{INDIA_FRANCHISE}",
        json=restore,
        timeout=15,
    )


# ----------------------------------------------------------------------
# 1. Franchise list / get endpoints — fields readable
# ----------------------------------------------------------------------
class TestFranchiseListGet:
    def test_list_returns_known_franchises(self, admin_token):
        r = requests.post(
            f"{BASE_URL}/api/franchises/list",
            json={"token": admin_token},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        codes = {f["franchise_code"] for f in r.json()["franchises"]}
        assert INDIA_FRANCHISE in codes
        assert AUS_FRANCHISE in codes

    def test_get_india_franchise(self, admin_token):
        r = requests.post(
            f"{BASE_URL}/api/franchises/get/{INDIA_FRANCHISE}",
            json={"token": admin_token},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        fr = r.json()["franchise"]
        assert fr["franchise_code"] == INDIA_FRANCHISE
        assert fr.get("country") == "India"


# ----------------------------------------------------------------------
# 2. PUT /update — payout_model + franchise_owner_share_percentage
#    persist and mirror legacy field.
# ----------------------------------------------------------------------
class TestPayoutModelPersistence:
    def test_set_profit_share_persists(self, admin_token, original_india_state):
        # Switch India franchise to profit_share + 20% owner share
        r = requests.post(
            f"{BASE_URL}/api/franchises/update/{INDIA_FRANCHISE}",
            json={
                "token": admin_token,
                "payout_model": "profit_share",
                "franchise_owner_share_percentage": 20.0,
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json().get("success") is True

        # Re-fetch and assert persistence
        g = requests.post(
            f"{BASE_URL}/api/franchises/get/{INDIA_FRANCHISE}",
            json={"token": admin_token},
            timeout=15,
        )
        assert g.status_code == 200
        fr = g.json()["franchise"]
        assert fr.get("payout_model") == "profit_share"
        assert fr.get("franchise_owner_share_percentage") == 20.0
        # Legacy mirror — both fields should hold the same value
        assert fr.get("revenue_share_percentage") == 20.0

    def test_set_revenue_share_back_persists(self, admin_token, original_india_state):
        r = requests.post(
            f"{BASE_URL}/api/franchises/update/{INDIA_FRANCHISE}",
            json={
                "token": admin_token,
                "payout_model": "revenue_share",
                "franchise_owner_share_percentage": 15.0,
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text

        g = requests.post(
            f"{BASE_URL}/api/franchises/get/{INDIA_FRANCHISE}",
            json={"token": admin_token},
            timeout=15,
        )
        fr = g.json()["franchise"]
        assert fr.get("payout_model") == "revenue_share"
        assert fr.get("franchise_owner_share_percentage") == 15.0
        assert fr.get("revenue_share_percentage") == 15.0

    def test_legacy_revenue_share_percentage_mirrors_to_new(
        self, admin_token, original_india_state
    ):
        """When a caller writes only legacy `revenue_share_percentage`, the
        new `franchise_owner_share_percentage` field must mirror."""
        r = requests.post(
            f"{BASE_URL}/api/franchises/update/{INDIA_FRANCHISE}",
            json={"token": admin_token, "revenue_share_percentage": 17.5},
            timeout=15,
        )
        assert r.status_code == 200, r.text

        g = requests.post(
            f"{BASE_URL}/api/franchises/get/{INDIA_FRANCHISE}",
            json={"token": admin_token},
            timeout=15,
        )
        fr = g.json()["franchise"]
        assert fr.get("revenue_share_percentage") == 17.5
        assert fr.get("franchise_owner_share_percentage") == 17.5


# ----------------------------------------------------------------------
# 3. MG checkbox regression — `mg_calculation_applicable=False` persists
# ----------------------------------------------------------------------
class TestMGApplicableRegression:
    def test_mg_off_persists(self, admin_token, original_india_state):
        r = requests.post(
            f"{BASE_URL}/api/franchises/update/{INDIA_FRANCHISE}",
            json={"token": admin_token, "mg_calculation_applicable": False},
            timeout=15,
        )
        assert r.status_code == 200, r.text

        g = requests.post(
            f"{BASE_URL}/api/franchises/get/{INDIA_FRANCHISE}",
            json={"token": admin_token},
            timeout=15,
        )
        fr = g.json()["franchise"]
        assert fr.get("mg_calculation_applicable") is False

    def test_mg_on_persists(self, admin_token, original_india_state):
        r = requests.post(
            f"{BASE_URL}/api/franchises/update/{INDIA_FRANCHISE}",
            json={"token": admin_token, "mg_calculation_applicable": True},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        g = requests.post(
            f"{BASE_URL}/api/franchises/get/{INDIA_FRANCHISE}",
            json={"token": admin_token},
            timeout=15,
        )
        assert g.json()["franchise"].get("mg_calculation_applicable") is True


# ----------------------------------------------------------------------
# 4. Center Accounts summary — engine payload exposed
# ----------------------------------------------------------------------
class TestCenterAccountsEnginePayload:
    """Verify /api/center-accounts/summary surfaces the engine fields
    needed by the dashboards / PDFs."""

    @pytest.fixture(scope="class")
    def summary_india_revshare(self, admin_token, original_india_state):
        # Ensure India franchise is on revenue_share / 15%
        requests.post(
            f"{BASE_URL}/api/franchises/update/{INDIA_FRANCHISE}",
            json={
                "token": admin_token,
                "payout_model": "revenue_share",
                "franchise_owner_share_percentage": 15.0,
                "mg_calculation_applicable": False,
            },
            timeout=15,
        )
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/summary",
            json={"token": admin_token, "center": "PB-HSR", "month": "2026-01"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # The route returns {"success": True, "summary": {...}} — unwrap.
        return body.get("summary", body)

    def test_engine_top_level_fields_present(self, summary_india_revshare):
        s = summary_india_revshare
        assert "payout_model" in s
        assert "section_heading" in s
        assert "base_label" in s
        assert "engine" in s
        assert isinstance(s["engine"], dict)

    def test_engine_object_has_both_bases(self, summary_india_revshare):
        e = summary_india_revshare["engine"]
        assert "revenue_share_base" in e
        assert "profit_share_base" in e
        assert "selected_base" in e
        assert "owner_pct" in e
        assert "owner_share" in e

    def test_india_revshare_section_heading(self, summary_india_revshare):
        s = summary_india_revshare
        assert s["payout_model"] == "revenue_share"
        assert "REVENUE SHARE" in s["section_heading"].upper()
        assert s["base_label"] == "Revenue Share Base"
        assert s["engine"]["payout_model"] == "revenue_share"

    def test_india_revshare_payout_equals_engine_owner_share(
        self, summary_india_revshare
    ):
        """For India / revenue_share, share_calculation.franchise_owner.amount
        must equal engine.owner_share (engine is the single source of truth)."""
        s = summary_india_revshare
        engine_owner_share = s["engine"]["owner_share"]
        sc = s.get("share_calculation") or {}
        fo = sc.get("franchise_owner") or {}
        share_amt = fo.get("amount")
        assert share_amt is not None, f"share_calculation missing: {sc}"
        assert abs(share_amt - engine_owner_share) < 0.01, (
            f"share_calc owner amt {share_amt} != engine.owner_share {engine_owner_share}"
        )
        # And the type matches the engine's model
        assert sc.get("type") == "revenue_share"


# ----------------------------------------------------------------------
# 5. Switch model → summary flips heading + base label
# ----------------------------------------------------------------------
class TestSwitchPayoutModelFlow:
    def test_switch_india_to_profit_share_flips_summary(
        self, admin_token, original_india_state
    ):
        # 1. Set India franchise to profit_share / 30%
        r = requests.post(
            f"{BASE_URL}/api/franchises/update/{INDIA_FRANCHISE}",
            json={
                "token": admin_token,
                "payout_model": "profit_share",
                "franchise_owner_share_percentage": 30.0,
                "mg_calculation_applicable": False,
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text

        # 2. Re-fetch center summary
        s = requests.post(
            f"{BASE_URL}/api/center-accounts/summary",
            json={"token": admin_token, "center": "PB-HSR", "month": "2026-01"},
            timeout=30,
        ).json()
        s = s.get("summary", s)

        assert s["payout_model"] == "profit_share"
        assert s["section_heading"] == "PROFIT SHARE CALCULATION"
        assert s["base_label"] == "Profit Share Base"
        assert s["engine"]["payout_model"] == "profit_share"
        assert s["engine"]["owner_pct"] == 30.0

        # 3. Switch back to revenue_share — verify it flips back
        requests.post(
            f"{BASE_URL}/api/franchises/update/{INDIA_FRANCHISE}",
            json={
                "token": admin_token,
                "payout_model": "revenue_share",
                "franchise_owner_share_percentage": 15.0,
            },
            timeout=15,
        )
        s2 = requests.post(
            f"{BASE_URL}/api/center-accounts/summary",
            json={"token": admin_token, "center": "PB-HSR", "month": "2026-01"},
            timeout=30,
        ).json()
        s2 = s2.get("summary", s2)
        assert s2["payout_model"] == "revenue_share"
        assert s2["section_heading"] == "REVENUE SHARE CALCULATION"
        assert s2["base_label"] == "Revenue Share Base"
