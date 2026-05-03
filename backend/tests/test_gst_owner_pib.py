"""Iteration 76: GST liabilities + Owner Reports + PIB Preview."""
import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://balance-cascade-fix.preview.emergentagent.com").rstrip("/")
SA_MOBILE = "9741399190"
FO_MOBILE = "8888888888"
OTP = "123456"


def _login(mobile, center):
    s = requests.Session()
    s.post(f"{BASE_URL}/api/send_otp", json={"mobile": mobile, "center": center}, timeout=30)
    r = s.post(f"{BASE_URL}/api/verify_otp", json={"mobile": mobile, "otp": OTP, "center": center}, timeout=30)
    assert r.status_code == 200, f"login failed for {mobile}: {r.status_code} {r.text[:200]}"
    return r.json().get("token")


@pytest.fixture(scope="module")
def sa_token():
    return _login(SA_MOBILE, "PB-MGT")


@pytest.fixture(scope="module")
def fo_token():
    try:
        return _login(FO_MOBILE, "PB-HSR")
    except Exception:
        return None


# ---- GST Liabilities ----
class TestGSTLiabilities:
    def test_recompute_idempotent(self, sa_token):
        r1 = requests.post(f"{BASE_URL}/api/gst/recompute", json={"token": sa_token}, timeout=120)
        assert r1.status_code == 200, r1.text[:300]
        d1 = r1.json()
        assert d1.get("success") is True
        assert d1.get("recomputed", 0) >= 1
        # Run again — should not flip paid status
        r2 = requests.post(f"{BASE_URL}/api/gst/recompute", json={"token": sa_token}, timeout=120)
        assert r2.status_code == 200

    def test_liabilities_list_totals(self, sa_token):
        r = requests.post(f"{BASE_URL}/api/gst/liabilities", json={"token": sa_token}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "rows" in d and "total_payable" in d and "total_paid" in d
        assert isinstance(d["rows"], list)

    def test_liabilities_filter_unpaid(self, sa_token):
        r = requests.post(f"{BASE_URL}/api/gst/liabilities",
                          json={"token": sa_token, "status": "unpaid"}, timeout=30)
        assert r.status_code == 200
        for row in r.json()["rows"]:
            assert not row.get("paid")

    def test_gst_math_india_5pct(self, sa_token):
        # Pick any PB-HSR month with sales, compute expected GST (INCLUSIVE basis)
        rep = requests.post(f"{BASE_URL}/api/owner-reports/monthly-report",
                            json={"token": sa_token, "center": "PB-HSR", "month": "2026-03"}, timeout=30).json()
        if "gst" in rep:
            assert rep["gst"]["rate_pct"] == 5
            # Inclusive carve-out: gst = eligible − eligible / 1.05
            eligible = float(rep["gst"]["eligible_base"])
            expected = round(eligible - eligible / 1.05, 2)
            assert abs(rep["gst"]["gst_amount"] - expected) < 0.5

    def test_mark_and_unmark_paid_flow(self, sa_token):
        # Find an unpaid liability with amount > 0
        r = requests.post(f"{BASE_URL}/api/gst/liabilities",
                          json={"token": sa_token, "status": "unpaid"}, timeout=30).json()
        target = next((x for x in r["rows"] if float(x.get("gst_amount", 0)) > 0), None)
        if not target:
            pytest.skip("no unpaid liability with amount>0")
        center, month = target["center"], target["month"]
        mr = requests.post(f"{BASE_URL}/api/gst/mark-paid",
                           json={"token": sa_token, "center": center, "month": month}, timeout=30)
        assert mr.status_code == 200, mr.text[:300]
        md = mr.json()
        assert md.get("success") is True
        expense_id = md.get("expense_id")
        paid_date = md.get("paid_date", "")
        # Should be in month M+1 and day 20
        assert paid_date.endswith("-20"), paid_date
        # Verify liability reflects paid=true
        rows = requests.post(f"{BASE_URL}/api/gst/liabilities",
                             json={"token": sa_token, "center": center}, timeout=30).json()["rows"]
        paid_row = next(x for x in rows if x["month"] == month)
        assert paid_row.get("paid") is True
        assert paid_row.get("paid_expense_id") == expense_id

        # Idempotency — calling again says already_paid
        mr2 = requests.post(f"{BASE_URL}/api/gst/mark-paid",
                            json={"token": sa_token, "center": center, "month": month}, timeout=30).json()
        assert mr2.get("already_paid") is True or mr2.get("success") is True

        # Unmark paid
        ur = requests.post(f"{BASE_URL}/api/gst/unmark-paid",
                           json={"token": sa_token, "center": center, "month": month}, timeout=30)
        assert ur.status_code == 200, ur.text[:300]
        rows2 = requests.post(f"{BASE_URL}/api/gst/liabilities",
                              json={"token": sa_token, "center": center}, timeout=30).json()["rows"]
        clean_row = next(x for x in rows2 if x["month"] == month)
        assert not clean_row.get("paid")

    def test_mark_paid_requires_super_admin(self, fo_token):
        if not fo_token:
            pytest.skip("no franchise owner token")
        r = requests.post(f"{BASE_URL}/api/gst/mark-paid",
                          json={"token": fo_token, "center": "PB-HSR", "month": "2026-03"}, timeout=30)
        assert r.status_code == 403


# ---- Owner Reports ----
class TestOwnerReports:
    def test_set_visibility_admin_only(self, sa_token, fo_token):
        r = requests.post(f"{BASE_URL}/api/owner-reports/set-visibility",
                          json={"token": sa_token, "center": "PB-HSR", "month": "2026-03", "ready": True},
                          timeout=30)
        assert r.status_code == 200
        if fo_token:
            r2 = requests.post(f"{BASE_URL}/api/owner-reports/set-visibility",
                               json={"token": fo_token, "center": "PB-HSR", "month": "2026-03", "ready": True},
                               timeout=30)
            assert r2.status_code == 403

    def test_visibility_status(self, sa_token):
        r = requests.post(f"{BASE_URL}/api/owner-reports/visibility-status",
                          json={"token": sa_token}, timeout=30)
        assert r.status_code == 200
        assert "rows" in r.json()

    def test_monthly_report_admin_sees_data(self, sa_token):
        r = requests.post(f"{BASE_URL}/api/owner-reports/monthly-report",
                          json={"token": sa_token, "center": "PB-HSR", "month": "2026-03"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d.get("success") is True
        assert "sales" in d and "gst" in d and "expenses" in d and "pnl" in d
        assert d["gst"]["rate_pct"] == 5
        # eligible_base == total_sale - aggregator_sale
        agg = d["gst"]["aggregator_sale"]
        tot = d["sales"]["total"]
        assert abs(d["gst"]["eligible_base"] - max(0, tot - agg)) < 1

    def test_owner_gated_when_not_ready(self, sa_token, fo_token):
        if not fo_token:
            pytest.skip("no franchise owner token")
        # Use a future month unlikely to be flagged
        future = "2099-12"
        r = requests.post(f"{BASE_URL}/api/owner-reports/monthly-report",
                          json={"token": fo_token, "center": "PB-HSR", "month": future}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d.get("success") is True
        assert d["visibility"]["ready"] is False
        assert "sales" not in d and "gst" not in d

    def test_owner_unlocked_after_visibility(self, sa_token, fo_token):
        if not fo_token:
            pytest.skip("no franchise owner token")
        center, month = "PB-HSR", "2026-03"
        # Ensure flag set
        requests.post(f"{BASE_URL}/api/owner-reports/set-visibility",
                      json={"token": sa_token, "center": center, "month": month, "ready": True}, timeout=30)
        r = requests.post(f"{BASE_URL}/api/owner-reports/monthly-report",
                          json={"token": fo_token, "center": center, "month": month}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["visibility"]["ready"] is True
        # Should now include full packet
        assert "sales" in d and "gst" in d

    def test_perth_rate_10pct(self, sa_token):
        r = requests.post(f"{BASE_URL}/api/owner-reports/monthly-report",
                          json={"token": sa_token, "center": "PB-PERTH", "month": "2026-03"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        if "gst" in d:
            assert d["gst"]["rate_pct"] == 10, f"Perth GST rate should be 10, got {d['gst']['rate_pct']}"


# ---- PIB Preview ----
class TestPIBPreview:
    def test_preview_pib_returns_summary(self, sa_token):
        r = requests.post(f"{BASE_URL}/api/center-accounts/preview-pib",
                          json={"token": sa_token, "center": "PB-HSR", "month": "2026-03"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d.get("success") is True
        assert "summary" in d
        assert "generated_at" in d
        assert d.get("center") == "PB-HSR"
        assert d.get("month") == "2026-03"
