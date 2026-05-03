"""Backend tests for Promotions / Discount engine endpoints.

Covers:
- GET /api/promotions returns default brunch + evening_snack config
- PUT /api/admin/promotions persists changes (admin auth)
- PUT /api/admin/promotions without token returns 401/403
- Regression: GET /api/centers, /api/locations still functional
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://golden-luxury-app.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "PBadmin@purnabramha.com"
ADMIN_PASSWORD = "PB22052012"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token(api):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text}")
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_client(api, admin_token):
    api.headers.update({"Authorization": f"Bearer {admin_token}"})
    yield api
    # remove auth after module
    api.headers.pop("Authorization", None)


# ============ DEFAULT PROMOTIONS ============
class TestPromotionDefaults:
    def test_get_promotions_public(self, api):
        r = requests.get(f"{BASE_URL}/api/promotions")
        assert r.status_code == 200
        data = r.json()
        assert "brunch" in data
        assert "evening_snack" in data

    def test_brunch_default_shape(self, api):
        r = requests.get(f"{BASE_URL}/api/promotions")
        data = r.json()
        b = data["brunch"]
        assert b["enabled"] is True
        assert b["start_time"] in ("11:00", "00:00")  # could be overridden by previous tests, will reset later
        # At minimum, regions key present
        assert "regions" in b
        assert isinstance(b["regions"], list)
        assert "combo_categories" in b
        assert "drink_categories" in b
        assert b.get("discount_pct", 0) >= 0

    def test_evening_snack_default_shape(self, api):
        r = requests.get(f"{BASE_URL}/api/promotions")
        data = r.json()
        e = data["evening_snack"]
        assert e["enabled"] is True
        assert "regions" in e
        assert "snack_categories" in e
        assert "tea_keyword" in e


# ============ ADMIN AUTH ============
class TestPromotionAuth:
    def test_put_without_token_unauthorized(self, api):
        # Use a fresh session (no auth headers)
        s = requests.Session()
        r = s.put(f"{BASE_URL}/api/admin/promotions", json={"brunch": {"discount_pct": 15}})
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}: {r.text}"

    def test_put_with_invalid_token(self):
        s = requests.Session()
        s.headers.update({"Authorization": "Bearer invalid_token_xyz"})
        r = s.put(f"{BASE_URL}/api/admin/promotions", json={"brunch": {"discount_pct": 15}})
        assert r.status_code in (401, 403)


# ============ ADMIN UPDATE / PERSIST ============
class TestPromotionUpdates:
    def test_update_brunch_discount_pct_persists(self, admin_client):
        # Get current
        cur = requests.get(f"{BASE_URL}/api/promotions").json()
        original_pct = cur["brunch"].get("discount_pct", 10)

        new_pct = 17 if original_pct != 17 else 18
        r = admin_client.put(f"{BASE_URL}/api/admin/promotions", json={"brunch": {"discount_pct": new_pct}})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "promotions" in body
        assert body["promotions"]["brunch"]["discount_pct"] == new_pct

        # GET reflects change
        g = requests.get(f"{BASE_URL}/api/promotions").json()
        assert g["brunch"]["discount_pct"] == new_pct

        # Restore original
        admin_client.put(f"{BASE_URL}/api/admin/promotions", json={"brunch": {"discount_pct": original_pct}})

    def test_update_brunch_times_and_regions(self, admin_client):
        cur = requests.get(f"{BASE_URL}/api/promotions").json()["brunch"]
        original = {
            "start_time": cur.get("start_time", "11:00"),
            "end_time": cur.get("end_time", "12:00"),
            "regions": cur.get("regions", ["India", "Australia"]),
            "enabled": cur.get("enabled", True),
        }

        r = admin_client.put(
            f"{BASE_URL}/api/admin/promotions",
            json={"brunch": {"start_time": "10:30", "end_time": "13:00", "regions": ["India"], "enabled": False}},
        )
        assert r.status_code == 200
        g = requests.get(f"{BASE_URL}/api/promotions").json()["brunch"]
        assert g["start_time"] == "10:30"
        assert g["end_time"] == "13:00"
        assert g["regions"] == ["India"]
        assert g["enabled"] is False

        # restore
        admin_client.put(f"{BASE_URL}/api/admin/promotions", json={"brunch": original})
        g2 = requests.get(f"{BASE_URL}/api/promotions").json()["brunch"]
        assert g2["start_time"] == original["start_time"]
        assert g2["enabled"] == original["enabled"]

    def test_update_evening_snack_persists(self, admin_client):
        cur = requests.get(f"{BASE_URL}/api/promotions").json()["evening_snack"]
        original_pct = cur.get("discount_pct", 10)

        new_pct = 12 if original_pct != 12 else 13
        r = admin_client.put(f"{BASE_URL}/api/admin/promotions", json={"evening_snack": {"discount_pct": new_pct}})
        assert r.status_code == 200
        g = requests.get(f"{BASE_URL}/api/promotions").json()["evening_snack"]
        assert g["discount_pct"] == new_pct

        # restore
        admin_client.put(f"{BASE_URL}/api/admin/promotions", json={"evening_snack": {"discount_pct": original_pct}})

    def test_merged_with_defaults_preserves_combo_categories(self, admin_client):
        # Even if we PUT only discount_pct, other default keys should be preserved
        admin_client.put(f"{BASE_URL}/api/admin/promotions", json={"brunch": {"discount_pct": 10}})
        g = requests.get(f"{BASE_URL}/api/promotions").json()["brunch"]
        assert "combo_categories" in g
        assert "drink_categories" in g
        assert isinstance(g["combo_categories"], list)
        assert len(g["combo_categories"]) >= 1


# ============ REGRESSION ============
class TestRegression:
    def test_centers_endpoint(self):
        r = requests.get(f"{BASE_URL}/api/centers")
        assert r.status_code == 200
        data = r.json()
        # should be grouped object with India/Australia keys, or list
        assert data is not None

    def test_locations_endpoint(self):
        r = requests.get(f"{BASE_URL}/api/locations")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_center_timeslots(self):
        # Use HSR center
        r = requests.get(f"{BASE_URL}/api/center-timeslots/pb-hsr")
        assert r.status_code == 200


# ============ CLEANUP / RESTORE DEFAULTS ============
class TestCleanup:
    def test_restore_defaults(self, admin_client):
        """Final cleanup: restore the documented defaults."""
        defaults = {
            "brunch": {
                "enabled": True,
                "start_time": "11:00",
                "end_time": "12:00",
                "discount_pct": 10,
                "regions": ["India", "Australia"],
            },
            "evening_snack": {
                "enabled": True,
                "start_time": "16:00",
                "end_time": "17:00",
                "discount_pct": 10,
                "regions": ["India"],
            },
        }
        r = admin_client.put(f"{BASE_URL}/api/admin/promotions", json=defaults)
        assert r.status_code == 200
        g = requests.get(f"{BASE_URL}/api/promotions").json()
        assert g["brunch"]["start_time"] == "11:00"
        assert g["brunch"]["end_time"] == "12:00"
        assert g["brunch"]["discount_pct"] == 10
        assert "India" in g["brunch"]["regions"]
        assert "Australia" in g["brunch"]["regions"]
        assert g["evening_snack"]["start_time"] == "16:00"
        assert g["evening_snack"]["end_time"] == "17:00"
        assert g["evening_snack"]["regions"] == ["India"]
