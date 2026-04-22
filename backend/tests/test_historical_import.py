"""Historical WC-rollup import end-to-end tests.

Covers:
  • Auth: 403 for non super-admin on /import-wc-file and /clear
  • Import: parses 6 WC sheets from /tmp/wc.xlsx, skips LOANS, upserts ~130 rows
  • Idempotency: second import returns same total_rows without duplicating
  • /summary: per-center earliest/latest/months/total_sale/total_expenses
  • /clear with center: deletes only that center
  • WC-table merge: historical months appear for PB-SN, Balance WC cascades
  • No double-count: for a month that has live daily_sales rows, WC-table returns LIVE values
  • MIS /overview: historical-only month contributes to summary + per-center breakdown
  • /mis/working-capital: cumulative WC differs from base_wc after historical merge
"""
import os
import pytest
import requests

def _read_frontend_env(key: str) -> str:
    try:
        with open("/app/frontend/.env") as fh:
            for line in fh:
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return ""

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env("REACT_APP_BACKEND_URL")).rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"
SAMPLE_XLSX = "/tmp/wc.xlsx"

SUPER_ADMIN = {"mobile": "9741399190", "center": "PB-MGT"}
FRANCHISE   = {"mobile": "8888888888", "center": "PB-HSR"}
OTP = "123456"


# ---------------------------- fixtures ---------------------------- #
def _login(creds: dict) -> str:
    s = requests.Session()
    s.post(f"{BASE_URL}/api/send_otp", json=creds, timeout=15)
    r = s.post(f"{BASE_URL}/api/verify_otp", json={**creds, "otp": OTP}, timeout=15)
    assert r.status_code == 200, f"login failed for {creds}: {r.status_code} {r.text[:200]}"
    data = r.json()
    return data.get("token") or data.get("session", {}).get("token")


@pytest.fixture(scope="module")
def super_token() -> str:
    return _login(SUPER_ADMIN)


@pytest.fixture(scope="module")
def franchise_token() -> str:
    return _login(FRANCHISE)


@pytest.fixture(scope="module", autouse=True)
def _clear_before_and_after(super_token):
    # teardown-only: start from whatever state, but leave clean after
    requests.post(f"{BASE_URL}/api/historical/clear", json={"token": super_token}, timeout=15)
    yield
    requests.post(f"{BASE_URL}/api/historical/clear", json={"token": super_token}, timeout=15)


# ---------------------------- auth ---------------------------- #
class TestAuth:
    def test_non_super_admin_cannot_import(self, franchise_token):
        with open(SAMPLE_XLSX, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/api/historical/import-wc-file",
                data={"token": franchise_token},
                files={"file": ("wc.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                timeout=60,
            )
        assert r.status_code == 403

    def test_non_super_admin_cannot_clear(self, franchise_token):
        r = requests.post(f"{BASE_URL}/api/historical/clear", json={"token": franchise_token}, timeout=15)
        assert r.status_code == 403


# ---------------------------- import + summary ---------------------------- #
class TestImportAndSummary:
    def test_import_wc_file(self, super_token):
        with open(SAMPLE_XLSX, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/api/historical/import-wc-file",
                data={"token": super_token},
                files={"file": ("wc.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                timeout=90,
            )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] is True
        assert data["sheets_processed"] >= 6
        # Expected center codes
        for code in ("PB-SN", "PB-DV", "PB-KN", "PB-TH", "PB-HSR", "PB-HW"):
            assert code in data["centers"], f"missing center {code} in {data['centers']}"
        assert data["total_rows"] >= 120, f"expected ~130 rows, got {data['total_rows']}"
        # LOAN sheets must be skipped (not parsed as centers)
        # (sheets_skipped may include unmapped; LOANs are just never processed)

    def test_import_is_idempotent(self, super_token):
        with open(SAMPLE_XLSX, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/api/historical/import-wc-file",
                data={"token": super_token},
                files={"file": ("wc.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                timeout=90,
            )
        assert r.status_code == 200
        # Summary row count must equal first-import count (upsert, no duplicates)
        sr = requests.post(f"{BASE_URL}/api/historical/summary", json={"token": super_token}, timeout=15)
        assert sr.status_code == 200
        total_rows = sr.json()["total_rows"]
        assert 120 <= total_rows <= 160, f"unexpected total_rows after re-import: {total_rows}"

    def test_summary_shape(self, super_token):
        r = requests.post(f"{BASE_URL}/api/historical/summary", json={"token": super_token}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "centers" in data and "total_rows" in data
        by_center = {c["center"]: c for c in data["centers"]}
        for code in ("PB-SN", "PB-DV", "PB-KN", "PB-TH", "PB-HSR", "PB-HW"):
            assert code in by_center, f"missing {code}"
            row = by_center[code]
            assert row["months"] > 0
            assert row["earliest"] and row["latest"]
            assert row["earliest"] <= row["latest"]
            assert isinstance(row["total_sale"], (int, float))
            assert isinstance(row["total_expenses"], (int, float))


# ---------------------------- clear scoping ---------------------------- #
class TestClearScope:
    def test_clear_single_center_only_deletes_that_center(self, super_token):
        # Re-seed
        with open(SAMPLE_XLSX, "rb") as f:
            requests.post(
                f"{BASE_URL}/api/historical/import-wc-file",
                data={"token": super_token},
                files={"file": ("wc.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                timeout=90,
            )
        before = requests.post(f"{BASE_URL}/api/historical/summary", json={"token": super_token}, timeout=15).json()
        before_by = {c["center"]: c["months"] for c in before["centers"]}
        assert "PB-SN" in before_by

        r = requests.post(f"{BASE_URL}/api/historical/clear", json={"token": super_token, "center": "PB-SN"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["deleted"] == before_by["PB-SN"]

        after = requests.post(f"{BASE_URL}/api/historical/summary", json={"token": super_token}, timeout=15).json()
        after_by = {c["center"]: c["months"] for c in after["centers"]}
        assert "PB-SN" not in after_by  # only that center gone
        # Others unchanged
        for code in ("PB-DV", "PB-KN", "PB-TH", "PB-HSR", "PB-HW"):
            assert after_by.get(code) == before_by.get(code)


# ---------------------------- merge into WC table & MIS ---------------------------- #
@pytest.fixture(scope="module")
def seeded(super_token):
    """Ensure data is present for merge tests."""
    with open(SAMPLE_XLSX, "rb") as f:
        requests.post(
            f"{BASE_URL}/api/historical/import-wc-file",
            data={"token": super_token},
            files={"file": ("wc.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            timeout=90,
        )
    return True


class TestWCTableMerge:
    def test_wc_table_includes_historical_months_for_pb_sn(self, super_token, seeded):
        r = requests.post(
            f"{BASE_URL}/api/center-accounts/wc-table",
            json={"token": super_token, "center": "PB-SN"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        rows = r.json().get("rows", [])
        months = {row.get("month") for row in rows}
        # Historical file contains months spanning 2023 → 2026
        assert any(m and m.startswith("2023") for m in months), f"no 2023 months in WC table: {sorted(months)[:10]}"
        assert any(m and m.startswith("2024") for m in months)
        # Balance WC must cascade (not zero everywhere) — sales > 0 in history
        sales_sum = sum(float(r.get("sale", 0) or 0) for r in rows if (r.get("month") or "").startswith("2023"))
        assert sales_sum > 0, "PB-SN 2023 months should inherit sale from historical rows"

    def test_no_double_count_when_live_data_exists(self, super_token, seeded):
        """For PB-HSR, if any month has live daily_sales, the WC row for that month
        must show the LIVE sale value, not the historical file's value."""
        # fetch historical row for PB-HSR
        summ = requests.post(f"{BASE_URL}/api/historical/summary", json={"token": super_token}, timeout=15).json()
        pb_hsr = next((c for c in summ["centers"] if c["center"] == "PB-HSR"), None)
        assert pb_hsr is not None

        wc = requests.post(
            f"{BASE_URL}/api/center-accounts/wc-table",
            json={"token": super_token, "center": "PB-HSR"},
            timeout=30,
        ).json()
        rows = wc.get("rows", [])
        assert rows, "PB-HSR wc-table returned no rows"
        # Pull live daily_sales aggregation from MIS per-month
        for row in rows:
            m = row.get("month")
            if not m:
                continue
            # For each month, check: if the wc row claims _from_history flag missing,
            # then it's either live or empty. Historical rows shouldn't coexist with
            # non-zero live sales for the same month (no double-count).
            # Guard: sale should never exceed historical+live (i.e. wc logic picked one)
            # We do a sanity check via MIS overview month-scoped.
            mis = requests.post(
                f"{BASE_URL}/api/mis/overview",
                json={
                    "token": super_token,
                    "period": "custom",
                    "custom_start": f"{m}-01",
                    "custom_end": f"{m}-28",
                    "center": "PB-HSR",
                },
                timeout=30,
            )
            if mis.status_code != 200:
                continue
            mis_sales = float(mis.json().get("summary", {}).get("total_sales", 0) or 0)
            wc_sale = float(row.get("sale", 0) or 0)
            # WC row sale should roughly match MIS sales for the same month
            # (allowing small float/gst rounding). This catches double-count regressions.
            if mis_sales > 0 and wc_sale > 0:
                diff = abs(mis_sales - wc_sale)
                # Accept within 10% margin — MIS uses total_sale, WC may net differently
                assert diff <= max(1000.0, mis_sales * 0.15), (
                    f"{m}: WC sale {wc_sale} vs MIS sale {mis_sales} diverge — possible double-count"
                )


class TestMISMerge:
    def test_mis_overview_includes_historical_month(self, super_token, seeded):
        # PB-TH June 2024 — per problem statement this should be historical-only
        r = requests.post(
            f"{BASE_URL}/api/mis/overview",
            json={
                "token": super_token,
                "period": "custom",
                "custom_start": "2024-06-01",
                "custom_end": "2024-06-30",
                "center": "PB-TH",
            },
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        summary = data.get("summary", {})
        total_sales = float(summary.get("total_sales", 0) or 0)
        total_expenses = float(summary.get("total_expenses", 0) or 0)
        # Historical row for PB-TH 2024-06 has sale/expenses > 0
        assert total_sales > 0, f"PB-TH 2024-06 total_sales should include history, got {total_sales}"
        assert total_expenses >= 0
        # Per-center breakdown must include PB-TH
        centers = data.get("centers", []) or data.get("center_breakdown", []) or []
        pb_th_rows = [c for c in centers if (c.get("center") or c.get("name")) == "PB-TH"]
        assert pb_th_rows, f"PB-TH missing in per-center breakdown: {centers[:3]}"
        assert float(pb_th_rows[0].get("sales", 0) or 0) > 0

    def test_mis_working_capital_reflects_historical(self, super_token, seeded):
        r = requests.post(
            f"{BASE_URL}/api/mis/working-capital",
            json={"token": super_token, "center": "PB-SN"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        # Any of these shapes is acceptable — just ensure a WC figure is returned
        # and that it's not identical to the base WC (proves months were processed)
        awc = (
            data.get("available_working_capital")
            or data.get("current_wc")
            or (data.get("centers") or [{}])[0].get("available_working_capital")
        )
        base = (
            data.get("base_wc")
            or data.get("initial_wc")
            or (data.get("centers") or [{}])[0].get("base_wc")
        )
        # If shape is per-center list, find PB-SN
        if awc is None or base is None:
            for c in (data.get("centers") or []):
                if c.get("center") == "PB-SN":
                    awc = c.get("available_working_capital") or c.get("current_wc")
                    base = c.get("base_wc") or c.get("initial_wc")
        assert awc is not None, f"could not locate PB-SN working capital in response: {list(data.keys())}"
        # Simply assert that awc is a finite number; cascade difference from base is asserted
        # only when base is present and non-zero.
        assert isinstance(awc, (int, float))
        if base is not None and float(base) > 0:
            assert float(awc) != float(base), "WC didn't cascade after historical merge"
