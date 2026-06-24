"""Regression tests for 3 new features:
1. Vahini AI (/vahini)
2. Guest Experience Card (/guest-card)
3. PB Chai Cafe Franchise (/pb-chai-cafe)
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "PBadmin@purnabramha.com"
ADMIN_PASS = "PB22052012"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=20)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"No token in login response: {data}"
    return tok


# ========================= VAHINI =========================

class TestVahini:
    def test_vahini_talk_and_usage(self):
        client_id = f"TEST_client_{uuid.uuid4().hex[:8]}"
        session_id = f"TEST_sess_{uuid.uuid4().hex[:8]}"
        payload = {
            "persona": "vahini",
            "message": "Namaste! What is a good breakfast tip for me today?",
            "session_id": session_id,
            "client_id": client_id,
            "tier": "free",
        }
        r = requests.post(f"{API}/vahini/talk", json=payload, timeout=60)
        assert r.status_code == 200, f"vahini/talk failed: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("session_id") == session_id
        assert data.get("persona") == "vahini"
        assert isinstance(data.get("message"), str) and len(data["message"]) > 0
        assert "_id" not in data

        # Verify history accumulates - second call with same session_id
        payload2 = {**payload, "message": "Thank you, what else?"}
        r2 = requests.post(f"{API}/vahini/talk", json=payload2, timeout=60)
        assert r2.status_code == 200
        assert r2.json().get("session_id") == session_id

        # Usage tracking
        u = requests.get(f"{API}/vahini/usage", params={"client_id": client_id}, timeout=20)
        assert u.status_code == 200
        ud = u.json()
        assert ud["limit"] >= 1
        assert ud["used"] >= 1  # one session opened
        assert "remaining" in ud

    def test_vahini_talk_invalid_persona(self):
        r = requests.post(f"{API}/vahini/talk", json={"persona": "notapersona", "message": "hi"}, timeout=15)
        assert r.status_code == 400

    def test_vahini_talk_other_personas(self):
        for persona in ("founder", "krishna", "purnabramha", "aai"):
            payload = {
                "persona": persona,
                "message": "Hello!",
                "session_id": f"TEST_{persona}_{uuid.uuid4().hex[:6]}",
                "client_id": f"TEST_{persona}_client_{uuid.uuid4().hex[:6]}",
                "tier": "free",
            }
            r = requests.post(f"{API}/vahini/talk", json=payload, timeout=60)
            assert r.status_code == 200, f"{persona} -> {r.status_code} {r.text}"
            assert r.json().get("persona") == persona

    def test_vahini_membership(self):
        payload = {
            "name": "TEST Sneha",
            "mobile": "9999900000",
            "email": "TEST_sneha@example.com",
            "tier": "silver",
        }
        r = requests.post(f"{API}/vahini/membership", json=payload, timeout=15)
        assert r.status_code == 200, f"membership: {r.status_code} {r.text}"
        d = r.json()
        assert "_id" not in d
        assert d["name"] == "TEST Sneha"
        assert d["tier"] == "silver"
        assert d["status"] == "pending"
        assert "id" in d

    def test_vahini_membership_invalid(self):
        r = requests.post(f"{API}/vahini/membership", json={"name": "x"}, timeout=15)
        assert r.status_code == 400


# ========================= GUEST CARD =========================

# Module-level holder for coupon code captured across tests
COUPON_HOLDER = {}


class TestGuestCard:
    def test_submit_feedback_and_get_coupon(self):
        payload = {
            "guest_name": "TEST Rohan",
            "mobile": "9876500000",
            "email": "TEST_rohan@example.com",
            "center_id": "pb-hsr",
            "center_name": "HSR Layout",
            "visit_date": "2026-01-15",
            "visit_type": "Dine-in",
            "liked_most": "Modak was divine",
            "see_more": "More Maharashtrian thali options",
            "will_recommend": "Yes",
            "will_visit_again": "Yes",
            "three_changes": "Better seating, faster service, more sweets",
            "overall_rating": 5,
            "food_rating": 5,
            "service_rating": 5,
            "cleanliness_rating": 5,
        }
        r = requests.post(f"{API}/guest-feedback", json=payload, timeout=20)
        assert r.status_code == 200, f"guest-feedback: {r.status_code} {r.text}"
        data = r.json()
        assert "_id" not in data
        assert data["guest_name"] == "TEST Rohan"
        assert "coupon_code" in data
        assert data["coupon_code"].startswith("PB-")
        assert len(data["coupon_code"]) == 9  # PB- + 6 chars
        assert "discount_pct" in data
        assert "offer_title" in data
        assert data["status"] == "pending"
        COUPON_HOLDER["code"] = data["coupon_code"]
        COUPON_HOLDER["id"] = data["id"]

    def test_get_coupon_public(self):
        code = COUPON_HOLDER.get("code")
        assert code, "Previous test must have generated a coupon"
        r = requests.get(f"{API}/guest-feedback/coupon/{code}", timeout=15)
        assert r.status_code == 200, f"coupon lookup: {r.status_code} {r.text}"
        data = r.json()
        assert data["coupon_code"] == code
        # PII must be stripped
        assert "mobile" not in data
        assert "email" not in data
        assert "_id" not in data

    def test_get_coupon_not_found(self):
        r = requests.get(f"{API}/guest-feedback/coupon/PB-NOTREAL", timeout=15)
        assert r.status_code == 404

    def test_submit_feedback_missing_required(self):
        r = requests.post(f"{API}/guest-feedback", json={"guest_name": "x"}, timeout=15)
        assert r.status_code == 400

    def test_public_feedback_list(self):
        r = requests.get(f"{API}/guest-feedback/public", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "feedback" in data
        assert isinstance(data["feedback"], list)
        # Each entry must NOT expose PII or coupon
        for entry in data["feedback"]:
            assert "mobile" not in entry
            assert "email" not in entry
            assert "coupon_code" not in entry
            assert "_id" not in entry


# ========================= PB CHAI CAFE =========================

APP_HOLDER = {}


class TestPBChai:
    def test_get_config_public(self):
        r = requests.get(f"{API}/pb-chai/config", timeout=15)
        assert r.status_code == 200, f"pb-chai/config: {r.status_code} {r.text}"
        data = r.json()
        assert "_id" not in data
        assert "franchise_fee_inr" in data
        assert isinstance(data["franchise_fee_inr"], (int, float))
        assert "security_deposit_inr" in data
        assert "setup_heads" in data and isinstance(data["setup_heads"], list)
        assert "menu_items" in data
        assert "footer" in data
        assert "email" in data["footer"]

    def test_submit_franchise_application(self):
        # Backend uses 'full_name' and 'mobile' field names
        payload = {
            "full_name": "TEST Aniket Joshi",
            "mobile": "9888800000",
            "email": "TEST_aniket@example.com",
            "city": "Pune",
            "state": "Maharashtra",
            "country": "India",
            "occupation": "Entrepreneur",
            "business_experience": "5 years in food service",
            "investment_capacity": "25 lakh",
            "preferred_location": "Baner",
            "available_area": "400 sq ft",
            "expected_launch": "3 months",
            "message": "Excited to bring PB Chai to Pune",
            "agreed_disclosure": True,
        }
        r = requests.post(f"{API}/pb-chai/franchise-application", json=payload, timeout=20)
        assert r.status_code == 200, f"franchise-application: {r.status_code} {r.text}"
        d = r.json()
        assert "_id" not in d
        assert d["full_name"] == "TEST Aniket Joshi"
        assert d["status"] == "submitted"
        assert "id" in d
        APP_HOLDER["id"] = d["id"]

    def test_submit_franchise_app_missing(self):
        r = requests.post(f"{API}/pb-chai/franchise-application", json={"full_name": "x"}, timeout=15)
        assert r.status_code == 400

    def test_admin_list_apps_requires_auth(self):
        r = requests.get(f"{API}/admin/pb-chai/franchise-applications", timeout=15)
        assert r.status_code in (401, 403)

    def test_admin_list_apps(self, admin_token):
        r = requests.get(
            f"{API}/admin/pb-chai/franchise-applications",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r.status_code == 200, f"admin list: {r.status_code} {r.text}"
        data = r.json()
        assert "applications" in data
        ids = [a["id"] for a in data["applications"]]
        assert APP_HOLDER.get("id") in ids, "Just-submitted application should appear in admin list"

    def test_admin_update_config(self, admin_token):
        # Get current config
        cur = requests.get(f"{API}/pb-chai/config", timeout=15).json()
        original_fee = cur.get("franchise_fee_inr", 200000)
        # Update to a slightly different value
        new_fee = int(original_fee) + 1
        cur["franchise_fee_inr"] = new_fee
        r = requests.put(
            f"{API}/admin/pb-chai/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=cur,
            timeout=20,
        )
        assert r.status_code == 200, f"update config: {r.status_code} {r.text}"
        # Verify persisted
        r2 = requests.get(f"{API}/pb-chai/config", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["franchise_fee_inr"] == new_fee
        # Restore
        cur["franchise_fee_inr"] = original_fee
        requests.put(
            f"{API}/admin/pb-chai/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=cur,
            timeout=20,
        )

    def test_admin_update_config_unauthorized(self):
        r = requests.put(f"{API}/admin/pb-chai/config", json={"franchise_fee_inr": 1}, timeout=15)
        assert r.status_code in (401, 403)


# ========================= CLEANUP =========================

def teardown_module(module):
    """Best-effort cleanup: delete TEST_* docs via direct mongo."""
    try:
        from pymongo import MongoClient
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME")
        if not mongo_url or not db_name:
            # Try backend .env
            for line in open("/app/backend/.env"):
                if line.startswith("MONGO_URL="):
                    mongo_url = line.split("=", 1)[1].strip()
                if line.startswith("DB_NAME="):
                    db_name = line.split("=", 1)[1].strip()
        if mongo_url and db_name:
            c = MongoClient(mongo_url)
            d = c[db_name]
            d.guest_feedback.delete_many({"guest_name": {"$regex": "^TEST "}})
            d.vahini_memberships.delete_many({"name": {"$regex": "^TEST "}})
            d.pbchai_applications.delete_many({"full_name": {"$regex": "^TEST "}})
            d.vahini_usage.delete_many({"client_id": {"$regex": "^TEST_"}})
            d.vahini_talk.delete_many({"session_id": {"$regex": "^TEST_"}})
            c.close()
    except Exception as e:
        print(f"cleanup error: {e}")
