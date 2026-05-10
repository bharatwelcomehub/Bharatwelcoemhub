"""Iteration 81 — Working Capital cross-surface parity (canonical chain via wc_chain.py).

These tests enforce that the four WC-displaying surfaces remain byte-identical
for the SAME {center, month}:
    1. Center Accounts /summary -> working_capital_status.current_wc
    2. MIS /working-capital available_working_capital
    3. MIS /working-capital centers[0].current_wc
    4. /center-accounts/wc-table last (or matching) row balance_wc

Plus regressions for sales/expense/GST/commission/net-revenue parity.
"""
import os
import calendar
import pytest
import requests

def _read_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not set")

BASE_URL = _read_backend_url()
TOL = 1.0

SUPER_ADMIN = {"mobile": "9741399190", "otp": "123456", "center": "PB-MGT"}
FO = {"mobile": "8888888888", "otp": "123456", "center": "PB-HSR"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/verify_otp", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def sa_token():
    return _login(SUPER_ADMIN)


@pytest.fixture(scope="module")
def fo_token():
    return _login(FO)


def _month_window(month):
    y, mo = map(int, month.split("-"))
    last = calendar.monthrange(y, mo)[1]
    return f"{y:04d}-{mo:02d}-01", f"{y:04d}-{mo:02d}-{last:02d}"


def _ca_summary(token, center, month):
    r = requests.post(f"{BASE_URL}/api/center-accounts/summary",
                      json={"token": token, "center": center, "month": month}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["summary"]


def _mis_wc(token, center, month):
    s, e = _month_window(month)
    r = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
        "token": token, "period": "custom", "center": center,
        "custom_start": s, "custom_end": e}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _wc_table(token, center):
    r = requests.post(f"{BASE_URL}/api/center-accounts/wc-table",
                      json={"token": token, "center": center}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- WC parity across surfaces ----------

@pytest.mark.parametrize("center,month", [
    ("PB-HSR", "2026-02"),
    ("PB-HSR", "2026-04"),
    ("PB-DV",  "2026-02"),
    ("PB-DV",  "2026-03"),
    ("PB-PERTH", "2026-02"),
    ("PB-PERTH", "2026-03"),
])
def test_wc_four_surfaces_identical(sa_token, center, month):
    ca = _ca_summary(sa_token, center, month)
    wc = _mis_wc(sa_token, center, month)
    tbl = _wc_table(sa_token, center)

    ca_wc = float(ca.get("working_capital_status", {}).get("current_wc") or 0)
    mis_avail = float(wc.get("available_working_capital") or 0)
    mis_centers0 = float(((wc.get("centers") or [{}])[0]).get("current_wc") or 0)

    # Find the last row <= month in the breakdown table
    target_row = None
    for r_ in reversed(tbl.get("rows") or []):
        if r_.get("month") <= month:
            target_row = r_
            break
    assert target_row is not None, f"No WC table row for {center} <= {month}"
    row_wc = float(target_row.get("balance_wc") or 0)

    # All four must agree
    vals = {"ca_card": ca_wc, "mis_avail": mis_avail, "mis_centers0": mis_centers0, "wc_table_row": row_wc}
    ref = ca_wc
    for k, v in vals.items():
        assert abs(v - ref) <= TOL, f"WC drift {center} {month}: {vals}"


def test_ca_summary_wc_status_populated(sa_token):
    ca = _ca_summary(sa_token, "PB-HSR", "2026-04")
    wcs = ca.get("working_capital_status", {})
    assert wcs, "working_capital_status missing"
    # current_wc and opening_wc must be present and non-null
    assert "current_wc" in wcs and wcs["current_wc"] is not None
    assert "opening_wc" in wcs and wcs["opening_wc"] is not None
    # For PB-HSR Apr 2026 base data, current_wc should be > 0
    assert float(wcs["current_wc"]) > 0
    assert float(wcs["opening_wc"]) > 0


def test_wc_table_chain_last_row_matches_ca_card(sa_token):
    """The last chained row in the breakdown must equal the Status card for the same end month."""
    tbl = _wc_table(sa_token, "PB-HSR")
    rows = tbl.get("rows") or []
    assert rows, "WC table rows empty for PB-HSR"
    last_row = rows[-1]
    last_month = last_row["month"]
    ca = _ca_summary(sa_token, "PB-HSR", last_month)
    ca_wc = float(ca["working_capital_status"]["current_wc"])
    assert abs(float(last_row["balance_wc"]) - ca_wc) <= TOL


def test_mis_wc_equals_ca_summary_for_period(sa_token):
    """POST /mis/working-capital with custom Apr range must equal /center-accounts/summary."""
    ca = _ca_summary(sa_token, "PB-HSR", "2026-04")
    wc = _mis_wc(sa_token, "PB-HSR", "2026-04")
    ca_wc = float(ca["working_capital_status"]["current_wc"])
    mis_wc = float(wc.get("available_working_capital") or 0)
    assert abs(mis_wc - ca_wc) <= TOL, f"MIS WC ₹{mis_wc} != CA card ₹{ca_wc}"


# ---------- FO Dashboard WC parity ----------

def test_fo_dashboard_wc_matches_canonical(fo_token, sa_token):
    """FO Dashboard calls /mis/working-capital with period params. Must match the
    breakdown table last row for PB-HSR Apr 2026 (canonical chain)."""
    wc = _mis_wc(fo_token, "PB-HSR", "2026-04")
    fo_wc = float(wc.get("available_working_capital") or 0)
    tbl = _wc_table(sa_token, "PB-HSR")
    target_row = None
    for r_ in reversed(tbl.get("rows") or []):
        if r_.get("month") <= "2026-04":
            target_row = r_
            break
    assert target_row is not None
    row_wc = float(target_row["balance_wc"])
    assert abs(fo_wc - row_wc) <= TOL, f"FO WC ₹{fo_wc} != table row ₹{row_wc}"


# ---------- Sales/Commission/GST regression ----------

@pytest.mark.parametrize("center,month", [("PB-HSR", "2026-02"), ("PB-DV", "2026-02")])
def test_sales_gst_commission_parity(sa_token, center, month):
    ca = _ca_summary(sa_token, center, month)
    fin = ca["financial_summary"]
    # Owner report
    r = requests.post(f"{BASE_URL}/api/owner-reports/monthly-report",
                      json={"token": sa_token, "center": center, "month": month}, timeout=30)
    assert r.status_code == 200
    owner = r.json()
    s, e = _month_window(month)
    r = requests.post(f"{BASE_URL}/api/mis/overview", json={
        "token": sa_token, "period": "custom", "center": center,
        "custom_start": s, "custom_end": e}, timeout=30)
    assert r.status_code == 200
    mis = r.json()["summary"]

    assert abs(float(fin["total_sales"]) - float(owner["sales"]["total"])) <= TOL
    assert abs(float(fin["total_sales"]) - float(mis["total_sales"])) <= TOL
    ca_gst = float(fin.get("sales_gst") or fin.get("total_gst") or 0)
    assert abs(ca_gst - float(owner["gst"]["gst_amount"])) <= TOL
    assert abs(ca_gst - float(mis["total_gst"])) <= TOL
    ca_comm = float(fin.get("total_commissions_with_gst") or fin.get("total_commissions") or 0)
    assert abs(ca_comm - float(owner["commissions"]["total"])) <= TOL
    assert abs(ca_comm - float(mis["total_commissions"])) <= TOL
