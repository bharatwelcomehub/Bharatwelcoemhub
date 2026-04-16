"""
Test suite for Book Reading Platform features:
- GET /api/book/parts - returns 3 parts with correct pricing
- POST /api/book/purchase - creates Stripe checkout session
- GET /api/book/pages/{part} - returns book pages (requires auth + purchase)
- POST /api/book/bookmark - creates bookmark
- GET /api/book/bookmarks - returns user bookmarks
- DELETE /api/book/bookmark/{page} - removes bookmark
- PUT /api/book/progress - saves reading progress
- GET /api/book/progress - returns reading progress
- GET /api/admin/book/analytics - returns reader stats
- POST /api/admin/book/pages - admin can add book pages
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "PBadmin@purnabramha.com"
ADMIN_PASSWORD = "PB22052012"


class TestBookPartsAPI:
    """Test /api/book/parts endpoint - public access"""

    def test_get_book_parts_returns_200(self):
        """GET /api/book/parts should return 200"""
        response = requests.get(f"{BASE_URL}/api/book/parts")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: GET /api/book/parts returns 200")

    def test_book_parts_returns_3_parts(self):
        """Should return exactly 3 parts"""
        response = requests.get(f"{BASE_URL}/api/book/parts")
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) == 3, f"Expected 3 parts, got {len(data)}"
        print("PASS: Returns exactly 3 parts")

    def test_book_parts_correct_pricing_inr(self):
        """Each part should have price_inr = 50"""
        response = requests.get(f"{BASE_URL}/api/book/parts")
        data = response.json()
        for part in data:
            assert part.get("price_inr") == 50.0, f"Part {part.get('part_number')} price_inr should be 50, got {part.get('price_inr')}"
        print("PASS: All parts have correct INR pricing (₹50)")

    def test_book_parts_correct_pricing_aud(self):
        """Each part should have price_aud = 1"""
        response = requests.get(f"{BASE_URL}/api/book/parts")
        data = response.json()
        for part in data:
            assert part.get("price_aud") == 1.0, f"Part {part.get('part_number')} price_aud should be 1, got {part.get('price_aud')}"
        print("PASS: All parts have correct AUD pricing ($1)")

    def test_book_parts_structure(self):
        """Each part should have required fields"""
        response = requests.get(f"{BASE_URL}/api/book/parts")
        data = response.json()
        required_fields = ["part_number", "name", "pages", "price_inr", "price_aud", "start_page", "end_page", "purchased"]
        for part in data:
            for field in required_fields:
                assert field in part, f"Part missing field: {field}"
        print("PASS: All parts have required structure")


class TestBookPurchaseAPI:
    """Test /api/book/purchase endpoint - requires auth"""

    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Auth failed: {response.status_code} - {response.text}")

    def test_purchase_requires_auth(self):
        """POST /api/book/purchase without auth should return 401"""
        response = requests.post(f"{BASE_URL}/api/book/purchase", json={
            "part_number": 1,
            "origin_url": "https://test.com"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Purchase endpoint requires authentication")

    def test_purchase_creates_checkout_session(self, auth_token):
        """POST /api/book/purchase should create Stripe checkout session"""
        # Note: Admin already has all parts purchased, so this will return 400 "already own"
        response = requests.post(
            f"{BASE_URL}/api/book/purchase",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "part_number": 1,
                "origin_url": "https://golden-luxury-app.preview.emergentagent.com",
                "region": "India"
            }
        )
        # Admin already owns all parts, so expect 400
        if response.status_code == 400:
            data = response.json()
            assert "already own" in data.get("detail", "").lower(), f"Unexpected error: {data}"
            print("PASS: Purchase correctly rejects already-owned part")
        elif response.status_code == 200:
            data = response.json()
            assert "url" in data, "Response should contain checkout URL"
            assert "session_id" in data, "Response should contain session_id"
            assert data["url"].startswith("https://checkout.stripe.com"), f"URL should be Stripe checkout: {data['url']}"
            print("PASS: Purchase creates valid Stripe checkout session")
        else:
            pytest.fail(f"Unexpected status: {response.status_code} - {response.text}")

    def test_purchase_invalid_part_number(self, auth_token):
        """POST /api/book/purchase with invalid part should return 400"""
        response = requests.post(
            f"{BASE_URL}/api/book/purchase",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "part_number": 99,
                "origin_url": "https://test.com"
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Invalid part number returns 400")


class TestBookPagesAPI:
    """Test /api/book/pages/{part} endpoint - requires auth + purchase"""

    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Auth failed: {response.status_code}")

    def test_pages_requires_auth(self):
        """GET /api/book/pages/1 without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/book/pages/1")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Pages endpoint requires authentication")

    def test_pages_returns_content_for_purchased_part(self, auth_token):
        """GET /api/book/pages/1 should return pages for admin (who has purchased)"""
        response = requests.get(
            f"{BASE_URL}/api/book/pages/1",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "part" in data, "Response should contain part info"
        assert "pages" in data, "Response should contain pages array"
        assert isinstance(data["pages"], list), "Pages should be a list"
        print(f"PASS: Returns {len(data['pages'])} pages for part 1")

    def test_pages_part_2_accessible(self, auth_token):
        """GET /api/book/pages/2 should work for admin"""
        response = requests.get(
            f"{BASE_URL}/api/book/pages/2",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Part 2 pages accessible for admin")

    def test_pages_part_3_accessible(self, auth_token):
        """GET /api/book/pages/3 should work for admin"""
        response = requests.get(
            f"{BASE_URL}/api/book/pages/3",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Part 3 pages accessible for admin")

    def test_pages_invalid_part_returns_404(self, auth_token):
        """GET /api/book/pages/99 should return 404"""
        response = requests.get(
            f"{BASE_URL}/api/book/pages/99",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Invalid part number returns 404")


class TestBookBookmarksAPI:
    """Test bookmark endpoints"""

    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Auth failed: {response.status_code}")

    def test_create_bookmark(self, auth_token):
        """POST /api/book/bookmark should create bookmark"""
        response = requests.post(
            f"{BASE_URL}/api/book/bookmark",
            headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"},
            json={"page_number": 5, "note": "Test bookmark"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data, "Response should contain message"
        print("PASS: Bookmark created successfully")

    def test_get_bookmarks(self, auth_token):
        """GET /api/book/bookmarks should return user bookmarks"""
        response = requests.get(
            f"{BASE_URL}/api/book/bookmarks",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"PASS: Returns {len(data)} bookmarks")

    def test_delete_bookmark(self, auth_token):
        """DELETE /api/book/bookmark/{page} should remove bookmark"""
        # First create a bookmark to delete
        requests.post(
            f"{BASE_URL}/api/book/bookmark",
            headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"},
            json={"page_number": 99, "note": "To be deleted"}
        )
        
        # Now delete it
        response = requests.delete(
            f"{BASE_URL}/api/book/bookmark/99",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Bookmark deleted successfully")


class TestBookProgressAPI:
    """Test reading progress endpoints"""

    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Auth failed: {response.status_code}")

    def test_save_progress(self, auth_token):
        """PUT /api/book/progress should save reading progress"""
        response = requests.put(
            f"{BASE_URL}/api/book/progress",
            headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"},
            json={"last_page": 25, "last_part": 1}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: Progress saved successfully")

    def test_get_progress(self, auth_token):
        """GET /api/book/progress should return reading progress"""
        response = requests.get(
            f"{BASE_URL}/api/book/progress",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "last_page" in data, "Response should contain last_page"
        assert "last_part" in data, "Response should contain last_part"
        print(f"PASS: Progress returned - Page {data['last_page']}, Part {data['last_part']}")


class TestAdminBookAPI:
    """Test admin book management endpoints"""

    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Auth failed: {response.status_code}")

    def test_admin_analytics(self, auth_token):
        """GET /api/admin/book/analytics should return reader stats"""
        response = requests.get(
            f"{BASE_URL}/api/admin/book/analytics",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "total_readers" in data, "Response should contain total_readers"
        assert "total_purchases" in data, "Response should contain total_purchases"
        assert "total_bookmarks" in data, "Response should contain total_bookmarks"
        assert "part_stats" in data, "Response should contain part_stats"
        print(f"PASS: Analytics - {data['total_readers']} readers, {data['total_purchases']} purchases")

    def test_admin_add_pages(self, auth_token):
        """POST /api/admin/book/pages should add book pages"""
        response = requests.post(
            f"{BASE_URL}/api/admin/book/pages",
            headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"},
            json={
                "pages": [
                    {"page_number": 999, "part_number": 1, "content": "TEST PAGE CONTENT"}
                ]
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data, "Response should contain message"
        print("PASS: Admin can add book pages")

    def test_admin_get_all_pages(self, auth_token):
        """GET /api/admin/book/pages should return all book pages"""
        response = requests.get(
            f"{BASE_URL}/api/admin/book/pages",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"PASS: Admin can view all {len(data)} book pages")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
