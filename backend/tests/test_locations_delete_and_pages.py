"""
Iteration 14: tests DELETE /api/admin/locations/{id} with cascade and
regression on /api/tiffin-*, /api/catering-*, /api/promotions, /api/centers.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "PBadmin@purnabramha.com"
ADMIN_PASS = "PB22052012"

BASELINE_CENTERS = {
    "pb-hsr", "pb-sambhajinagar", "pb-kharadi",
    "pb-hinjawadi", "pb-thane", "pb-dombivli", "pb-kalyan",
    "pb-perth",
}


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(session):
    r = session.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, data
    return tok


@pytest.fixture()
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# -------- DELETE /api/admin/locations/{id} --------
class TestLocationDelete:
    def test_delete_without_auth_401_or_403(self, session):
        r = session.delete(f"{API}/admin/locations/any-id")
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_delete_bad_token_401_or_403(self, session):
        r = session.delete(
            f"{API}/admin/locations/any-id",
            headers={"Authorization": "Bearer NOT_A_TOKEN"},
        )
        assert r.status_code in (401, 403)

    def test_delete_nonexistent_returns_404(self, session, admin_headers):
        r = session.delete(f"{API}/admin/locations/does-not-exist-xyz", headers=admin_headers)
        assert r.status_code == 404, r.text

    def test_create_then_delete_with_cascade(self, session, admin_headers):
        # 1) Create a test location
        ts = int(time.time())
        center_id = f"pb-test-del-{ts}"
        payload = {
            "name": f"TEST_DelCity_{ts}",
            "display_name": f"TEST Del Display {ts}",
            "city": f"DelCity{ts}",
            "state": "Test",
            "country": "India",
            "address": "x",
            "phone": "x",
            "whatsapp": "x",
            "center_id": center_id,
            "currency": "INR",
            "currency_symbol": "₹",
            "is_active": True,
        }
        r = session.post(f"{API}/admin/locations", headers=admin_headers, json=payload)
        assert r.status_code == 200, r.text
        loc = r.json()
        loc_id = loc["id"]

        # 2) Verify appears in /api/centers
        centers = session.get(f"{API}/centers").json()
        ids = {c["id"] for c in centers["india"]}
        assert center_id in ids, f"New center {center_id} missing from /api/centers"

        # 3) Save custom timeslots for center -> creates center_timeslots doc
        slots = [{"id": "s1", "label": "TEST 10-11", "start": "10:00", "end": "11:00", "isActive": True}]
        r2 = session.put(
            f"{API}/admin/center-timeslots/{center_id}",
            headers=admin_headers,
            json={"slots": slots},
        )
        assert r2.status_code == 200

        # 4) Delete the location
        r3 = session.delete(f"{API}/admin/locations/{loc_id}", headers=admin_headers)
        assert r3.status_code == 200, r3.text
        body = r3.json()
        assert body.get("id") == loc_id

        # 5) GET /api/centers must no longer list it
        centers_after = session.get(f"{API}/centers").json()
        ids_after = {c["id"] for c in centers_after["india"]}
        assert center_id not in ids_after, "Deleted center still in /api/centers"

        # 6) Cascade check: timeslots for this center_id should be defaults again (no persisted doc)
        ts_resp = session.get(f"{API}/center-timeslots/{center_id}")
        assert ts_resp.status_code == 200
        got_slots = ts_resp.json()["slots"]
        # The custom label we saved must be gone (cascade worked) -- documents as known issue if present
        labels = [s.get("label") for s in got_slots]
        assert "TEST 10-11" not in labels, (
            f"Cascade delete of center_timeslots did NOT work. Custom slot still present. "
            f"DELETE uses location_id but center_timeslots keyed by center_id. slots={labels}"
        )

    def test_delete_twice_returns_404_second_time(self, session, admin_headers):
        ts = int(time.time())
        payload = {
            "name": f"TEST_DoubleDel_{ts}",
            "display_name": "x", "city": "x",
            "state": "x", "country": "India", "address": "x",
            "phone": "x", "whatsapp": "x",
            "center_id": f"pb-test-dd-{ts}",
            "currency": "INR", "currency_symbol": "₹", "is_active": True,
        }
        loc = session.post(f"{API}/admin/locations", headers=admin_headers, json=payload).json()
        r1 = session.delete(f"{API}/admin/locations/{loc['id']}", headers=admin_headers)
        assert r1.status_code == 200
        r2 = session.delete(f"{API}/admin/locations/{loc['id']}", headers=admin_headers)
        assert r2.status_code == 404


# -------- Baseline integrity --------
class TestBaselineIntact:
    def test_baseline_8_centers_present(self, session):
        data = session.get(f"{API}/centers").json()
        all_ids = {c["id"] for c in data["india"] + data["australia"]}
        missing = BASELINE_CENTERS - all_ids
        assert not missing, f"Missing baseline centers: {missing}"

    def test_public_locations_no_test_leaks(self, session):
        locs = session.get(f"{API}/locations").json()
        leaked = [l for l in locs if (l.get("center_id") or "").startswith("pb-test-")]
        assert not leaked, f"Leaked TEST locations in /api/locations: {leaked}"


# -------- Regression: key endpoints respond 200 with expected shape --------
class TestRegressionEndpoints:
    def test_promotions_200(self, session):
        r = session.get(f"{API}/promotions")
        assert r.status_code == 200
        d = r.json()
        assert "brunch" in d and "evening_snack" in d

    def test_centers_200(self, session):
        r = session.get(f"{API}/centers")
        assert r.status_code == 200
        assert "india" in r.json() and "australia" in r.json()

    def test_center_timeslots_default(self, session):
        r = session.get(f"{API}/center-timeslots/pb-hsr")
        assert r.status_code == 200
        assert isinstance(r.json().get("slots"), list)

    def test_tiffin_config_200(self, session):
        r = session.get(f"{API}/tiffin-config")
        assert r.status_code == 200
        assert isinstance(r.json(), (list, dict))

    def test_tiffin_items_200(self, session):
        r = session.get(f"{API}/tiffin-items")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_catering_packages_200(self, session):
        r = session.get(f"{API}/catering-packages")
        assert r.status_code == 200
        d = r.json()
        assert "packages" in d and "menuOptions" in d
        assert "india" in d["packages"] and "australia" in d["packages"]
        # Baseline: 4 india + 4 australia (8 total), >=9 menu categories
        assert len(d["packages"]["india"]) >= 4, f"India packages={len(d['packages']['india'])}"
        assert len(d["packages"]["australia"]) >= 4, f"Australia packages={len(d['packages']['australia'])}"
        # Verify prices
        india_prices = sorted(p.get("price_per_person_inr", 0) for p in d["packages"]["india"])
        assert 450 in india_prices and 600 in india_prices and 750 in india_prices and 950 in india_prices
        aus_prices = sorted(p.get("price_per_person_aud", 0) for p in d["packages"]["australia"])
        assert 35 in aus_prices and 45 in aus_prices and 55 in aus_prices and 70 in aus_prices

    def test_locations_200(self, session):
        r = session.get(f"{API}/locations")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_menu_200(self, session):
        r = session.get(f"{API}/menu")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
