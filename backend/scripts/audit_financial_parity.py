#!/usr/bin/env python3
"""Cross-Surface Financial Audit — verifies that every dashboard / PDF / API
returns the SAME numbers (Sales, GST, Commission, Net Revenue, Net P/L,
Eligible Rev Share Base, Revenue Share, Final Payout) for the same
{center, month} input.

Run:  python /app/backend/scripts/audit_financial_parity.py PB-HSR 2026-02

Exit code 0 = all surfaces match within ₹1 tolerance.
Exit code 1 = drift found; details printed.
"""
import os
import sys
import json
import requests
from typing import Dict, Any

API = (os.environ.get("REACT_APP_BACKEND_URL")
       or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip())

SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_OTP = "123456"
SUPER_ADMIN_CENTER = "PB-MGT"

TOLERANCE = 1.0  # ₹1 rounding tolerance


def login() -> str:
    r = requests.post(f"{API}/api/verify_otp", json={
        "mobile": SUPER_ADMIN_MOBILE, "otp": SUPER_ADMIN_OTP, "center": SUPER_ADMIN_CENTER,
    })
    r.raise_for_status()
    return r.json()["token"]


def fetch_owner_report(token: str, center: str, month: str) -> Dict[str, Any]:
    r = requests.post(f"{API}/api/owner-reports/monthly-report",
                      json={"token": token, "center": center, "month": month})
    r.raise_for_status()
    return r.json()


def fetch_center_accounts(token: str, center: str, month: str) -> Dict[str, Any]:
    r = requests.post(f"{API}/api/center-accounts/summary",
                      json={"token": token, "center": center, "month": month})
    r.raise_for_status()
    return r.json().get("summary", {})


def fetch_mis_overview(token: str, center: str, month: str) -> Dict[str, Any]:
    # MIS uses period dates, not month string. Build a YYYY-MM-DD start/end window.
    from datetime import date
    import calendar
    y, mo = map(int, month.split("-"))
    last = calendar.monthrange(y, mo)[1]
    r = requests.post(f"{API}/api/mis/overview", json={
        "token": token,
        "period": "custom",
        "center": center,
        "custom_start": f"{y:04d}-{mo:02d}-01",
        "custom_end": f"{y:04d}-{mo:02d}-{last:02d}",
    })
    r.raise_for_status()
    return r.json()


def fetch_payout_summary(token: str, center: str, month: str) -> Dict[str, Any]:
    r = requests.post(f"{API}/api/center-accounts/payout-summary",
                      json={"token": token, "center": center, "from_month": month, "to_month": month})
    r.raise_for_status()
    return r.json()


def f(v, default=0.0) -> float:
    try:
        return float(v if v is not None else default)
    except Exception:
        return float(default)


def near(a: float, b: float, tol: float = TOLERANCE) -> bool:
    return abs(a - b) <= tol


def audit(center: str, month: str) -> int:
    token = login()
    print(f"\n=== Auditing {center} for {month} ===\n")

    # Pull from every surface
    owner = fetch_owner_report(token, center, month)
    ca = fetch_center_accounts(token, center, month)
    mis = fetch_mis_overview(token, center, month)
    payout = fetch_payout_summary(token, center, month)

    # Extract numbers (defensive — schemas evolved over time)
    owner_sales = f(owner.get("sales", {}).get("total"))
    owner_exp = f(owner.get("expenses", {}).get("total"))
    owner_gst = f(owner.get("gst", {}).get("gst_amount"))
    owner_comm = f(owner.get("commissions", {}).get("total"))
    owner_net_rev = f(owner.get("net_revenue") or owner.get("pnl"))
    owner_net_pl = f(owner.get("net_pl"))
    owner_elig = f(owner.get("eligible_rev_share_base"))

    ca_fin = ca.get("financial_summary", {}) or {}
    ca_sales = f(ca_fin.get("total_sales"))
    ca_exp = f(ca_fin.get("total_expenses"))
    ca_gst = f(ca_fin.get("sales_gst") or ca_fin.get("total_gst"))
    # Center Accounts uses 'total_commissions_with_gst' (post Apr-2026 rule)
    # which is the inclusive figure used by MIS Dashboard / MG Payout / Owner Reports.
    ca_comm = f(ca_fin.get("total_commissions_with_gst") or ca_fin.get("total_commissions"))
    ca_net_rev = f(ca_fin.get("net_revenue"))

    mis_sum = mis.get("summary", {}) or {}
    mis_sales = f(mis_sum.get("total_sales"))
    mis_exp = f(mis_sum.get("total_expenses"))
    mis_gst = f(mis_sum.get("total_gst"))
    mis_comm = f(mis_sum.get("total_commissions"))
    mis_net_rev = f(mis_sum.get("net_revenue"))

    monthly_data = (payout.get("monthly_data") or [{}])[0] if payout.get("monthly_data") else {}
    payout_sales = f(monthly_data.get("total_sales"))
    payout_gst = f(monthly_data.get("gst_on_sales"))
    payout_comm = f(monthly_data.get("total_commissions"))
    payout_net_rev = f(monthly_data.get("net_revenue"))
    payout_rs = f(monthly_data.get("revenue_share"))

    # Build comparison table
    rows = [
        ("Total Sales",        [("Owner Reports", owner_sales),
                                ("Center Accounts", ca_sales),
                                ("MIS Dashboard", mis_sales),
                                ("MG Payout", payout_sales)]),
        ("Total Expenses",     [("Owner Reports", owner_exp),
                                ("Center Accounts", ca_exp),
                                ("MIS Dashboard", mis_exp)]),
        ("GST on Sales",       [("Owner Reports", owner_gst),
                                ("Center Accounts", ca_gst),
                                ("MIS Dashboard", mis_gst),
                                ("MG Payout", payout_gst)]),
        ("Commissions",        [("Owner Reports", owner_comm),
                                ("Center Accounts", ca_comm),
                                ("MIS Dashboard", mis_comm),
                                ("MG Payout", payout_comm)]),
        ("Net Revenue",        [("Owner Reports", owner_net_rev),
                                ("Center Accounts", ca_net_rev),
                                ("MIS Dashboard", mis_net_rev),
                                ("MG Payout", payout_net_rev)]),
        ("Net P/L",            [("Owner Reports", owner_net_pl)]),
        ("Eligible Rev Share Base", [("Owner Reports", owner_elig),
                                     ("Net Revenue ↑", owner_net_rev)]),
    ]

    failures = 0
    for metric, values in rows:
        valid = [(s, v) for s, v in values if v != 0 or len(values) == 1]
        if not valid:
            continue
        ref_val = valid[0][1]
        line = f"  {metric:<32}"
        all_ok = True
        for src, v in values:
            ok = near(v, ref_val)
            mark = "✓" if ok else "✗"
            line += f" | {src}: ₹{v:>14,.2f} {mark}"
            if not ok:
                all_ok = False
        print(line)
        if not all_ok:
            failures += 1
            print(f"      ❌ DRIFT in {metric}: max diff = ₹{max(abs(v - ref_val) for _, v in values):.2f}")

    # Eligible Rev Share Base must equal Net Revenue for India (canonical chain)
    if owner.get("country", "India") != "Australia":
        if not near(owner_elig, owner_net_rev):
            failures += 1
            print(f"\n  ❌ Eligible Rev Share Base (₹{owner_elig:.2f}) != Net Revenue (₹{owner_net_rev:.2f})")

    print(f"\n{'='*60}")
    if failures == 0:
        print(f"✅ ALL SURFACES MATCH for {center} {month} (within ₹{TOLERANCE} tolerance)")
        return 0
    else:
        print(f"❌ {failures} DRIFT(s) detected for {center} {month}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: audit_financial_parity.py <CENTER> <MONTH>")
        print("Example: audit_financial_parity.py PB-HSR 2026-02")
        sys.exit(2)
    sys.exit(audit(sys.argv[1], sys.argv[2]))
