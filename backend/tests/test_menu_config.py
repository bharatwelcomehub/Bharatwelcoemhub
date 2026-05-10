"""
Backend tests for Super Admin Menu Configuration feature.
Endpoints under /api/menu-config.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://balance-cascade-fix.preview.emergentagent.com").rstrip("/")

SUPER_ADMIN = {"mobile": "9741399190", "center": "PB-MGT", "otp": "123456"}
FRANCHISE_OWNER = {"mobile": "8888888888", "center": "PB-HSR", "otp": "123456"}


def _login(creds):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/send_otp", json={"mobile": creds["mobile"], "center": creds["center"]}, timeout=20)
    assert r.status_code == 200, f"send_otp failed: {r.status_code} {r.text}"
    r = s.post(f"{BASE_URL}/api/verify_otp", json=creds, timeout=20)
    assert r.status_code == 200, f"verify_otp failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("token") or data.get("session", {}).get("token")
    assert token, f"No token in {data}"
    return token, data


@pytest.fixture(scope="module")
def super_admin_token():
    token, _ = _login(SUPER_ADMIN)
    yield token
    # cleanup: reset overrides at end so we don't pollute the env
    requests.post(f"{BASE_URL}/api/menu-config/reset", json={"token": token}, timeout=20)


@pytest.fixture(scope="module")
def franchise_owner_token():
    token, _ = _login(FRANCHISE_OWNER)
    return token


# ---------- GET /api/menu-config ----------
class TestGetMenuConfig:
    def test_get_requires_valid_token(self):
        r = requests.get(f"{BASE_URL}/api/menu-config", params={"token": "invalid_token_xyz"}, timeout=20)
        assert r.status_code == 401

    def test_get_super_admin_returns_shape(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/menu-config", params={"token": super_admin_token}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert "categories" in data
        assert "items" in data
        assert "updated_at" in data
        assert isinstance(data["categories"], dict)
        assert isinstance(data["items"], dict)

    def test_get_franchise_owner_can_read(self, franchise_owner_token):
        r = requests.get(f"{BASE_URL}/api/menu-config", params={"token": franchise_owner_token}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert "categories" in data and "items" in data


# ---------- GET /api/menu-config/valid-roles ----------
class TestValidRoles:
    def test_valid_roles_catalog(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/menu-config/valid-roles", params={"token": super_admin_token}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert "roles" in data
        roles = data["roles"]
        assert isinstance(roles, list)
        assert len(roles) == 14, f"Expected 14 roles, got {len(roles)}"
        keys = {r["key"] for r in roles}
        expected = {"super_admin", "admin", "mgt", "accounting", "attendance",
                    "sales_cash", "hr", "operations", "franchise", "billing",
                    "international", "center_manager", "franchise_owner", "staff"}
        assert keys == expected
        # All entries should have a label
        for r_obj in roles:
            assert r_obj.get("label"), f"missing label for {r_obj}"

    def test_valid_roles_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/menu-config/valid-roles", params={"token": "bad_token"}, timeout=20)
        assert r.status_code == 401


# ---------- POST /api/menu-config/save ----------
class TestSaveMenuConfig:
    def test_save_forbidden_for_franchise_owner(self, franchise_owner_token):
        body = {"token": franchise_owner_token,
                "categories": {"mgt": {"order": 0, "visible_roles": ["super_admin"]}},
                "items": {}}
        r = requests.post(f"{BASE_URL}/api/menu-config/save", json=body, timeout=20)
        assert r.status_code == 403, f"Expected 403, got {r.status_code} {r.text}"

    def test_save_super_admin_persists(self, super_admin_token):
        # 1) Save with a known unique override
        body = {
            "token": super_admin_token,
            "categories": {
                "mgt": {"order": 1, "visible_roles": ["super_admin", "admin", "mgt"]}
            },
            "items": {
                "/social-media-planner": {
                    "category_id": "sales_cash",
                    "order": 5,
                    "visible_roles": ["super_admin", "sales_cash"],
                }
            },
        }
        r = requests.post(f"{BASE_URL}/api/menu-config/save", json=body, timeout=20)
        assert r.status_code == 200, f"Save failed: {r.status_code} {r.text}"
        save_resp = r.json()
        assert save_resp.get("success") is True
        assert "updated_at" in save_resp

        # 2) GET reflects the override
        r2 = requests.get(f"{BASE_URL}/api/menu-config", params={"token": super_admin_token}, timeout=20)
        assert r2.status_code == 200
        d = r2.json()
        assert d["categories"].get("mgt", {}).get("order") == 1
        assert "super_admin" in d["categories"]["mgt"]["visible_roles"]
        assert d["items"].get("/social-media-planner", {}).get("category_id") == "sales_cash"
        assert d["items"]["/social-media-planner"]["order"] == 5
        assert "sales_cash" in d["items"]["/social-media-planner"]["visible_roles"]
        assert d.get("updated_at") is not None

    def test_save_sanitizes_invalid_roles(self, super_admin_token):
        body = {
            "token": super_admin_token,
            "categories": {
                "mgt": {"order": 2, "visible_roles": ["super_admin", "bogus_role", "admin"]}
            },
            "items": {},
        }
        r = requests.post(f"{BASE_URL}/api/menu-config/save", json=body, timeout=20)
        assert r.status_code == 200
        # Verify bogus role got filtered out
        r2 = requests.get(f"{BASE_URL}/api/menu-config", params={"token": super_admin_token}, timeout=20)
        d = r2.json()
        roles = d["categories"]["mgt"]["visible_roles"]
        assert "bogus_role" not in roles
        assert set(roles) == {"super_admin", "admin"}


# ---------- POST /api/menu-config/reset ----------
class TestResetMenuConfig:
    def test_reset_forbidden_for_franchise_owner(self, franchise_owner_token):
        r = requests.post(f"{BASE_URL}/api/menu-config/reset", json={"token": franchise_owner_token}, timeout=20)
        assert r.status_code == 403

    def test_reset_super_admin_clears_overrides(self, super_admin_token):
        # First save something so reset has work to do
        save_body = {
            "token": super_admin_token,
            "categories": {"mgt": {"order": 9, "visible_roles": ["super_admin"]}},
            "items": {},
        }
        sr = requests.post(f"{BASE_URL}/api/menu-config/save", json=save_body, timeout=20)
        assert sr.status_code == 200

        # Reset
        r = requests.post(f"{BASE_URL}/api/menu-config/reset", json={"token": super_admin_token}, timeout=20)
        assert r.status_code == 200, f"Reset failed: {r.status_code} {r.text}"
        assert r.json().get("success") is True

        # GET shows empty overrides
        r2 = requests.get(f"{BASE_URL}/api/menu-config", params={"token": super_admin_token}, timeout=20)
        assert r2.status_code == 200
        d = r2.json()
        assert d["categories"] == {}
        assert d["items"] == {}
