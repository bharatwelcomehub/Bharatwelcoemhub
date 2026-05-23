"""Iteration 84 — Booking Extensions backend tests.

Covers:
- New /api/bookings/ext/* routes (menu master, tiffin, catering, event CRUD)
- Per-booking PDF generation (Tiffin/Catering/Event/Today)
- Dashboard rollup
- Permission check (franchise owner cannot write tiffin/catering/event)
- Regression check: existing /api/bookings/* table booking endpoints still work
  and the new `table_allotted` field persists.
"""
from __future__ import annotations

import os
import time
import uuid
import pytest
import requests

def _read_backend_url() -> str:
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.strip().startswith("REACT_APP_BACKEND_URL"):
                        url = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    assert url, "REACT_APP_BACKEND_URL not set"
    return url.rstrip("/")


BASE_URL = _read_backend_url()
API = f"{BASE_URL}/api"

SA_MOBILE = "9741399190"
SA_CENTER = "PB-MGT"
FO_MOBILE = "8888888888"
FO_CENTER = "PB-HSR"
OTP = "123456"


# ---------------------- shared session / fixtures ----------------------
def _login(mobile: str, center: str) -> str:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/send_otp", json={"mobile": mobile, "center": center}, timeout=20)
    assert r.status_code == 200, f"send_otp failed: {r.status_code} {r.text}"
    r = s.post(f"{API}/verify_otp", json={"mobile": mobile, "otp": OTP, "center": center}, timeout=20)
    assert r.status_code == 200, f"verify_otp failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("token") or data.get("session", {}).get("token")
    assert token, f"No token in verify_otp response: {data}"
    return token


@pytest.fixture(scope="module")
def sa_token() -> str:
    return _login(SA_MOBILE, SA_CENTER)


@pytest.fixture(scope="module")
def fo_token() -> str:
    return _login(FO_MOBILE, FO_CENTER)


# ----------------------------- Menu Master -----------------------------
class TestMenuMaster:
    def test_menu_list_smoke(self, sa_token):
        r = requests.post(f"{API}/bookings/ext/menu/list", json={"token": sa_token}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert "by_category" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_menu_upsert_sa(self, sa_token):
        item = {"name": f"TEST_Paneer_{uuid.uuid4().hex[:6]}", "category": "Starters", "default_rate": 150.0, "is_active": True}
        r = requests.post(f"{API}/bookings/ext/menu/upsert",
                          json={"token": sa_token, "item": item}, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json().get("success") is True
        # Verify via list
        r = requests.post(f"{API}/bookings/ext/menu/list", json={"token": sa_token}, timeout=20)
        items = r.json().get("items", [])
        names = [i.get("name") for i in items]
        assert item["name"] in names
        # Cleanup
        requests.post(f"{API}/bookings/ext/menu/delete",
                      json={"token": sa_token, "id": f"{item['name']}|{item['category']}"}, timeout=20)

    def test_menu_upsert_fo_forbidden(self, fo_token):
        item = {"name": "TEST_FO_blocked", "category": "Starters", "default_rate": 100.0, "is_active": True}
        r = requests.post(f"{API}/bookings/ext/menu/upsert",
                          json={"token": fo_token, "item": item}, timeout=20)
        assert r.status_code == 403, f"Expected 403 for franchise owner, got {r.status_code}: {r.text}"


# --------------------- Generic helpers for CRUD tests ----------------------
def _create_tiffin(token, center):
    payload = {
        "token": token,
        "customer_name": "TEST_Tiffin_Customer",
        "phone": "9999999991",
        "center": center,
        "start_date": "2026-01-15",
        "end_date": "2026-01-22",
        "meal_type": "Lunch",
        "selected_days": ["Mon", "Tue", "Wed"],
        "selected_items": [{"name": "Paneer", "qty": 1, "rate": 150, "amount": 150}],
        "subtotal": 1000.0,
        "gst": 50.0,
        "total": 1234.0,  # free-form (not required to equal subtotal+gst)
        "payment_status": "Pending",
        "booking_status": "Confirmed",
    }
    return requests.post(f"{API}/bookings/ext/tiffin/create", json=payload, timeout=20)


def _create_catering(token, center):
    payload = {
        "token": token,
        "customer_name": "TEST_Catering_Customer",
        "phone": "9999999992",
        "center": center,
        "order_date": "2026-01-10",
        "event_date": "2026-02-01",
        "guest_count": 80,
        "subtotal": 19047.62,
        "gst": 952.38,
        "total": 20000.00,
    }
    return requests.post(f"{API}/bookings/ext/catering/create", json=payload, timeout=20)


def _create_event(token, center):
    payload = {
        "token": token,
        "customer_name": "TEST_Event_Customer",
        "phone": "9999999993",
        "center": center,
        "event_type": "Birthday",
        "event_date": "2026-02-14",
        "guest_count": 30,
        "estimated_total": 14285.71,
        "gst": 714.29,
        "final_total": 15000.00,
    }
    return requests.post(f"{API}/bookings/ext/event/create", json=payload, timeout=20)


# ------------------------------- Tiffin --------------------------------
class TestTiffin:
    created_id = None

    def test_create(self, sa_token):
        r = _create_tiffin(sa_token, SA_CENTER)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("id", "").startswith("TIFFIN-")
        assert body.get("customer_name") == "TEST_Tiffin_Customer"
        assert body.get("total") == 1234.0  # free-form preserved
        TestTiffin.created_id = body["id"]

    def test_list_filters(self, sa_token):
        r = requests.post(f"{API}/bookings/ext/tiffin/list",
                          json={"token": sa_token, "centers": [SA_CENTER],
                                "from_date": "2026-01-01", "to_date": "2026-01-31",
                                "search": "TEST_Tiffin_"}, timeout=20)
        assert r.status_code == 200
        rows = r.json().get("rows", [])
        assert any(row.get("id") == TestTiffin.created_id for row in rows)

    def test_update(self, sa_token):
        assert TestTiffin.created_id
        r = requests.post(f"{API}/bookings/ext/tiffin/update/{TestTiffin.created_id}",
                          json={"token": sa_token, "notes": "Updated test note", "total": 1500.0},
                          timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("notes") == "Updated test note"
        assert body.get("total") == 1500.0

    def test_pdf(self, sa_token):
        assert TestTiffin.created_id
        r = requests.post(f"{API}/bookings/ext/tiffin/pdf/{TestTiffin.created_id}",
                          json={"token": sa_token, "id": TestTiffin.created_id},
                          timeout=30)
        assert r.status_code == 200, r.text
        assert r.content[:5] == b"%PDF-"

    def test_fo_cannot_create(self, fo_token):
        r = _create_tiffin(fo_token, FO_CENTER)
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    def test_delete(self, sa_token):
        assert TestTiffin.created_id
        r = requests.post(f"{API}/bookings/ext/tiffin/delete/{TestTiffin.created_id}",
                          json={"token": sa_token}, timeout=20)
        assert r.status_code == 200
        assert r.json().get("success") is True


# ------------------------------ Catering -------------------------------
class TestCatering:
    created_id = None

    def test_create(self, sa_token):
        r = _create_catering(sa_token, SA_CENTER)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("id", "").startswith("CATERING-")
        TestCatering.created_id = body["id"]

    def test_list(self, sa_token):
        r = requests.post(f"{API}/bookings/ext/catering/list",
                          json={"token": sa_token, "centers": [SA_CENTER],
                                "from_date": "2026-01-01", "to_date": "2026-12-31"},
                          timeout=20)
        assert r.status_code == 200
        rows = r.json().get("rows", [])
        assert any(row.get("id") == TestCatering.created_id for row in rows)

    def test_pdf(self, sa_token):
        assert TestCatering.created_id
        r = requests.post(f"{API}/bookings/ext/catering/pdf/{TestCatering.created_id}",
                          json={"token": sa_token, "id": TestCatering.created_id},
                          timeout=30)
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"

    def test_fo_cannot_create(self, fo_token):
        r = _create_catering(fo_token, FO_CENTER)
        assert r.status_code == 403

    def test_delete(self, sa_token):
        assert TestCatering.created_id
        r = requests.post(f"{API}/bookings/ext/catering/delete/{TestCatering.created_id}",
                          json={"token": sa_token}, timeout=20)
        assert r.status_code == 200


# ------------------------------- Event ---------------------------------
class TestEvent:
    created_id = None

    def test_create(self, sa_token):
        r = _create_event(sa_token, SA_CENTER)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("id", "").startswith("EVENT-")
        TestEvent.created_id = body["id"]

    def test_list(self, sa_token):
        r = requests.post(f"{API}/bookings/ext/event/list",
                          json={"token": sa_token, "centers": [SA_CENTER]}, timeout=20)
        assert r.status_code == 200
        rows = r.json().get("rows", [])
        assert any(row.get("id") == TestEvent.created_id for row in rows)

    def test_update(self, sa_token):
        assert TestEvent.created_id
        r = requests.post(f"{API}/bookings/ext/event/update/{TestEvent.created_id}",
                          json={"token": sa_token, "guest_count": 45},
                          timeout=20)
        assert r.status_code == 200
        assert r.json().get("guest_count") == 45

    def test_pdf(self, sa_token):
        assert TestEvent.created_id
        r = requests.post(f"{API}/bookings/ext/event/pdf/{TestEvent.created_id}",
                          json={"token": sa_token, "id": TestEvent.created_id}, timeout=30)
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"

    def test_fo_cannot_create(self, fo_token):
        r = _create_event(fo_token, FO_CENTER)
        assert r.status_code == 403

    def test_delete(self, sa_token):
        assert TestEvent.created_id
        r = requests.post(f"{API}/bookings/ext/event/delete/{TestEvent.created_id}",
                          json={"token": sa_token}, timeout=20)
        assert r.status_code == 200


# ----------------------------- Today PDF -------------------------------
class TestTodayPdf:
    def test_today_pdf(self, sa_token):
        r = requests.post(f"{API}/bookings/ext/today-table-pdf",
                          json={"token": sa_token, "center": SA_CENTER}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.content[:5] == b"%PDF-"


# ----------------------------- Dashboard -------------------------------
class TestDashboard:
    def test_rollup(self, sa_token):
        r = requests.post(f"{API}/bookings/ext/dashboard",
                          json={"token": sa_token, "centers": [SA_CENTER],
                                "from_date": "2026-01-01", "to_date": "2026-12-31"},
                          timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        for key in ("tables", "tiffin", "catering", "event"):
            assert key in data
        assert "count" in data["tables"]
        for k in ("tiffin", "catering", "event"):
            assert "count" in data[k]
            assert "amount" in data[k]


# --------- REGRESSION: existing table booking endpoints unchanged -----------
class TestTableBookingRegression:
    created_id = None

    def test_create_booking(self, sa_token):
        payload = {
            "token": sa_token,
            "guest_name": "TEST_TableRegression",
            "phone": "9999999900",
            "center": SA_CENTER,
            "date": "2026-01-20",
            "time_slot": "19:00-21:00",
            "num_guests": 4,
            "status": "Confirmed",
            "table_allotted": "T-7",  # NOTE: create endpoint ignores this; update accepts it
        }
        r = requests.post(f"{API}/bookings/create", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        bid = body.get("booking_id") or (body.get("booking") or {}).get("booking_id")
        assert bid, f"No booking_id in create response: {body}"
        TestTableBookingRegression.created_id = bid

    def test_list_returns_booking(self, sa_token):
        r = requests.post(f"{API}/bookings/list",
                          json={"token": sa_token, "center": SA_CENTER,
                                "date_from": "2026-01-20", "date_to": "2026-01-20"},
                          timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        rows = data.get("bookings") or data.get("rows") or data.get("data") or []
        match = [x for x in rows if x.get("booking_id") == TestTableBookingRegression.created_id]
        assert match, "Created booking not returned by list endpoint"

    def test_update_table_allotted_persists(self, sa_token):
        bid = TestTableBookingRegression.created_id
        assert bid
        r = requests.post(f"{API}/bookings/update/{bid}",
                          json={"token": sa_token, "table_allotted": "T-12"},
                          timeout=20)
        assert r.status_code == 200, r.text
        # Verify via list
        r = requests.post(f"{API}/bookings/list",
                          json={"token": sa_token, "center": SA_CENTER,
                                "date_from": "2026-01-20", "date_to": "2026-01-20"},
                          timeout=20)
        rows = r.json().get("bookings") or r.json().get("rows") or []
        match = [x for x in rows if x.get("booking_id") == bid]
        assert match
        assert match[0].get("table_allotted") == "T-12", \
            f"table_allotted not persisted via update: {match[0]}"

    def test_cleanup(self, sa_token):
        bid = TestTableBookingRegression.created_id
        if not bid:
            return
        try:
            requests.post(f"{API}/bookings/delete/{bid}",
                          json={"token": sa_token}, timeout=10)
        except Exception:
            pass
