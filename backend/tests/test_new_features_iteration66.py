# =======================================
# Test Suite for 3 New Features (Iteration 66)
# 1. Daily Text Generator
# 2. Social Media Planner
# 3. Bill Download
# =======================================

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_CENTER = "PB-MGT"
TEST_OTP = "123456"
TEST_CENTER_WITH_DATA = "PB-SN"  # Center with sales data for daily text
TEST_DATE_WITH_DATA = "2025-12-15"  # Date with actual sales data


class TestAuth:
    """Authentication helper tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for super admin"""
        # Send OTP
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER
        })
        assert res.status_code == 200, f"Send OTP failed: {res.text}"
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER,
            "otp": TEST_OTP
        })
        assert res.status_code == 200, f"Verify OTP failed: {res.text}"
        data = res.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_health_check(self):
        """Verify API is accessible"""
        res = requests.get(f"{BASE_URL}/api/health")
        assert res.status_code == 200
        print("✓ Health check passed")


class TestDailyTextGenerator:
    """Feature 1: Daily Text Generator tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    def test_generate_daily_text_endpoint_exists(self, auth_token):
        """Test POST /api/daily-text/generate endpoint exists"""
        res = requests.post(f"{BASE_URL}/api/daily-text/generate", json={
            "token": auth_token,
            "center": TEST_CENTER_WITH_DATA,
            "date": TEST_DATE_WITH_DATA
        })
        assert res.status_code in [200, 404], f"Unexpected status: {res.status_code} - {res.text}"
        print(f"✓ Daily text generate endpoint accessible (status: {res.status_code})")
    
    def test_generate_daily_text_returns_text(self, auth_token):
        """Test that generate returns WhatsApp-formatted text"""
        res = requests.post(f"{BASE_URL}/api/daily-text/generate", json={
            "token": auth_token,
            "center": TEST_CENTER_WITH_DATA,
            "date": TEST_DATE_WITH_DATA
        })
        assert res.status_code == 200, f"Generate failed: {res.text}"
        data = res.json()
        
        # Verify response structure
        assert "text" in data, "No 'text' field in response"
        assert "data" in data, "No 'data' field in response"
        assert "success" in data, "No 'success' field in response"
        
        # Verify text contains expected header
        text = data["text"]
        assert "Jai Hind Namskar" in text, "Missing 'Jai Hind Namskar' header"
        
        print(f"✓ Daily text generated successfully")
        print(f"  - Has sales data: {data.get('has_sales_data', False)}")
        print(f"  - Expense count: {data.get('expense_count', 0)}")
    
    def test_generate_daily_text_data_fields(self, auth_token):
        """Test that data contains all expected fields"""
        res = requests.post(f"{BASE_URL}/api/daily-text/generate", json={
            "token": auth_token,
            "center": TEST_CENTER_WITH_DATA,
            "date": TEST_DATE_WITH_DATA
        })
        assert res.status_code == 200
        data = res.json()["data"]
        
        expected_fields = [
            "opening_balance", "deposit", "withdrawal", "total_sale",
            "card", "phone_pay", "swiggy", "zomato", "due_amount",
            "cash_sale", "online_expense", "cash_expense", "cash_in_hand",
            "petty_cash_balance", "total_guests", "apc"
        ]
        
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ All expected data fields present")
    
    def test_generate_daily_text_with_overrides(self, auth_token):
        """Test that overrides are applied"""
        res = requests.post(f"{BASE_URL}/api/daily-text/generate", json={
            "token": auth_token,
            "center": TEST_CENTER_WITH_DATA,
            "date": TEST_DATE_WITH_DATA,
            "overrides": {
                "total_sale": 99999,
                "total_guests": 500
            }
        })
        assert res.status_code == 200
        data = res.json()["data"]
        
        assert data["total_sale"] == 99999, "Override for total_sale not applied"
        assert data["total_guests"] == 500, "Override for total_guests not applied"
        
        print(f"✓ Overrides applied correctly")
    
    def test_generate_daily_text_unauthorized(self):
        """Test that invalid token is rejected"""
        res = requests.post(f"{BASE_URL}/api/daily-text/generate", json={
            "token": "invalid_token",
            "center": TEST_CENTER_WITH_DATA,
            "date": TEST_DATE_WITH_DATA
        })
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"
        print(f"✓ Unauthorized request rejected")


class TestSocialMediaPlanner:
    """Feature 2: Social Media Planner tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    def test_constants_endpoint(self, auth_token):
        """Test POST /api/social-media/constants returns dropdown values"""
        res = requests.post(f"{BASE_URL}/api/social-media/constants", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"Constants failed: {res.text}"
        data = res.json()
        
        assert "content_types" in data, "Missing content_types"
        assert "platforms" in data, "Missing platforms"
        assert "statuses" in data, "Missing statuses"
        assert "campaign_categories" in data, "Missing campaign_categories"
        
        # Verify expected values
        assert "Video Post" in data["content_types"], "Missing 'Video Post' content type"
        assert "Instagram" in data["platforms"], "Missing 'Instagram' platform"
        assert "Planned" in data["statuses"], "Missing 'Planned' status"
        
        print(f"✓ Constants endpoint returns all dropdown values")
        print(f"  - Content types: {len(data['content_types'])}")
        print(f"  - Platforms: {len(data['platforms'])}")
        print(f"  - Statuses: {len(data['statuses'])}")
    
    def test_list_posts_endpoint(self, auth_token):
        """Test POST /api/social-media/list returns posts"""
        res = requests.post(f"{BASE_URL}/api/social-media/list", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"List failed: {res.text}"
        data = res.json()
        
        assert "posts" in data, "Missing posts array"
        assert "count" in data, "Missing count"
        
        print(f"✓ List posts endpoint works (count: {data['count']})")
    
    def test_save_post_creates_new(self, auth_token):
        """Test POST /api/social-media/save creates a new post"""
        import uuid
        test_title = f"TEST_Post_{uuid.uuid4().hex[:8]}"
        
        res = requests.post(f"{BASE_URL}/api/social-media/save", json={
            "token": auth_token,
            "center": "PB-HSR",
            "content_type": "Static Post",
            "platform": "Instagram",
            "post_title": test_title,
            "caption": "Test caption for automated testing",
            "hashtags": "#test #automation",
            "status": "Planned",
            "campaign_category": "Daily",
            "planned_date": "2026-01-20"
        })
        assert res.status_code == 200, f"Save failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True, "Save not successful"
        assert "post_id" in data, "No post_id returned"
        
        print(f"✓ Post created successfully (ID: {data['post_id']})")
        return data["post_id"]
    
    def test_save_post_updates_existing(self, auth_token):
        """Test POST /api/social-media/save updates existing post"""
        # First create a post
        import uuid
        test_title = f"TEST_Update_{uuid.uuid4().hex[:8]}"
        
        res = requests.post(f"{BASE_URL}/api/social-media/save", json={
            "token": auth_token,
            "center": "PB-HSR",
            "content_type": "Reel",
            "platform": "Facebook",
            "post_title": test_title,
            "status": "Planned"
        })
        assert res.status_code == 200
        post_id = res.json()["post_id"]
        
        # Now update it
        res = requests.post(f"{BASE_URL}/api/social-media/save", json={
            "token": auth_token,
            "post_id": post_id,
            "center": "PB-HSR",
            "content_type": "Reel",
            "platform": "Facebook",
            "post_title": test_title + "_UPDATED",
            "status": "Posted"
        })
        assert res.status_code == 200
        assert res.json().get("message") == "Post updated"
        
        print(f"✓ Post updated successfully")
    
    def test_dashboard_endpoint(self, auth_token):
        """Test POST /api/social-media/dashboard returns widgets data"""
        res = requests.post(f"{BASE_URL}/api/social-media/dashboard", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"Dashboard failed: {res.text}"
        data = res.json()
        
        assert "total_posts" in data, "Missing total_posts"
        assert "status_counts" in data, "Missing status_counts"
        assert "platform_counts" in data, "Missing platform_counts"
        assert "posted_count" in data, "Missing posted_count"
        assert "planned_count" in data, "Missing planned_count"
        
        print(f"✓ Dashboard endpoint returns widget data")
        print(f"  - Total posts: {data['total_posts']}")
        print(f"  - Posted: {data['posted_count']}")
        print(f"  - Planned: {data['planned_count']}")
    
    def test_delete_post(self, auth_token):
        """Test POST /api/social-media/delete removes a post"""
        # First create a post to delete
        import uuid
        test_title = f"TEST_Delete_{uuid.uuid4().hex[:8]}"
        
        res = requests.post(f"{BASE_URL}/api/social-media/save", json={
            "token": auth_token,
            "center": "PB-HSR",
            "content_type": "Story",
            "platform": "Instagram",
            "post_title": test_title,
            "status": "Planned"
        })
        post_id = res.json()["post_id"]
        
        # Delete it
        res = requests.post(f"{BASE_URL}/api/social-media/delete", json={
            "token": auth_token,
            "post_id": post_id
        })
        assert res.status_code == 200, f"Delete failed: {res.text}"
        assert res.json().get("success") == True
        
        print(f"✓ Post deleted successfully")
    
    def test_save_post_unauthorized(self):
        """Test that non-admin cannot save posts"""
        res = requests.post(f"{BASE_URL}/api/social-media/save", json={
            "token": "invalid_token",
            "center": "PB-HSR",
            "post_title": "Should fail"
        })
        assert res.status_code in [401, 403], f"Expected 401/403, got {res.status_code}"
        print(f"✓ Unauthorized save rejected")


class TestBillDownload:
    """Feature 3: Bill Download tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    def test_list_bills_endpoint(self, auth_token):
        """Test POST /api/bill-download/list returns bills"""
        res = requests.post(f"{BASE_URL}/api/bill-download/list", json={
            "token": auth_token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200, f"List bills failed: {res.text}"
        data = res.json()
        
        assert "bills" in data, "Missing bills array"
        assert "count" in data, "Missing count"
        assert "doc_types" in data, "Missing doc_types"
        
        # Verify doc_types contains expected values
        expected_types = ["Sales Bill", "Expense Bill", "Invoice", "Purchase Bill"]
        for t in expected_types:
            assert t in data["doc_types"], f"Missing doc type: {t}"
        
        print(f"✓ List bills endpoint works")
        print(f"  - Bills count: {data['count']}")
        print(f"  - Doc types: {len(data['doc_types'])}")
    
    def test_list_bills_with_filters(self, auth_token):
        """Test list bills with various filters"""
        # Test with month filter
        res = requests.post(f"{BASE_URL}/api/bill-download/list", json={
            "token": auth_token,
            "center": "PB-HSR",
            "month": "2025-12"
        })
        assert res.status_code == 200
        
        # Test with date range filter
        res = requests.post(f"{BASE_URL}/api/bill-download/list", json={
            "token": auth_token,
            "center": "PB-HSR",
            "date_from": "2025-12-01",
            "date_to": "2025-12-31"
        })
        assert res.status_code == 200
        
        # Test with doc_type filter
        res = requests.post(f"{BASE_URL}/api/bill-download/list", json={
            "token": auth_token,
            "center": "PB-HSR",
            "doc_type": "Expense Bill"
        })
        assert res.status_code == 200
        
        print(f"✓ List bills with filters works")
    
    def test_upload_bill_endpoint(self, auth_token):
        """Test POST /api/bill-download/upload creates a bill record"""
        import uuid
        
        res = requests.post(f"{BASE_URL}/api/bill-download/upload", json={
            "token": auth_token,
            "center": "PB-HSR",
            "date": "2026-01-15",
            "doc_type": "Invoice",
            "description": f"TEST_Bill_{uuid.uuid4().hex[:8]}",
            "amount": 5000,
            "file_url": "https://example.com/test-bill.pdf",
            "file_name": "test-bill.pdf"
        })
        assert res.status_code == 200, f"Upload failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True
        assert "bill_id" in data
        
        print(f"✓ Bill uploaded successfully (ID: {data['bill_id']})")
    
    def test_download_zip_endpoint(self, auth_token):
        """Test POST /api/bill-download/download-zip endpoint"""
        res = requests.post(f"{BASE_URL}/api/bill-download/download-zip", json={
            "token": auth_token,
            "center": "PB-HSR",
            "month": "2025-12"
        })
        # May return 404 if no bills with file_url, or 200 with ZIP
        assert res.status_code in [200, 404], f"Unexpected status: {res.status_code}"
        
        if res.status_code == 200:
            # Verify it's a ZIP file
            content_type = res.headers.get("content-type", "")
            assert "application/zip" in content_type or "application/octet-stream" in content_type
            print(f"✓ ZIP download works (size: {len(res.content)} bytes)")
        else:
            print(f"✓ ZIP endpoint accessible (no downloadable files found)")
    
    def test_download_zip_with_bill_ids(self, auth_token):
        """Test ZIP download with specific bill IDs"""
        # First get some bill IDs
        res = requests.post(f"{BASE_URL}/api/bill-download/list", json={
            "token": auth_token,
            "center": "PB-HSR"
        })
        bills = res.json().get("bills", [])
        
        if bills:
            bill_ids = [b["bill_id"] for b in bills[:3] if b.get("bill_id")]
            if bill_ids:
                res = requests.post(f"{BASE_URL}/api/bill-download/download-zip", json={
                    "token": auth_token,
                    "center": "PB-HSR",
                    "bill_ids": bill_ids
                })
                assert res.status_code in [200, 404]
                print(f"✓ ZIP with specific bill IDs works")
            else:
                print(f"✓ No bill IDs to test (skipped)")
        else:
            print(f"✓ No bills to test ZIP download (skipped)")
    
    def test_list_bills_unauthorized(self):
        """Test that invalid token is rejected"""
        res = requests.post(f"{BASE_URL}/api/bill-download/list", json={
            "token": "invalid_token",
            "center": "PB-HSR"
        })
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"
        print(f"✓ Unauthorized request rejected")


class TestSidebarRoutes:
    """Test that sidebar routes are properly configured"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    def test_daily_text_route_prefix(self, auth_token):
        """Verify /api/daily-text/* routes work"""
        res = requests.post(f"{BASE_URL}/api/daily-text/generate", json={
            "token": auth_token,
            "center": "PB-HSR",
            "date": "2025-12-15"
        })
        assert res.status_code == 200
        print(f"✓ /api/daily-text/* route prefix works")
    
    def test_social_media_route_prefix(self, auth_token):
        """Verify /api/social-media/* routes work"""
        res = requests.post(f"{BASE_URL}/api/social-media/constants", json={
            "token": auth_token
        })
        assert res.status_code == 200
        print(f"✓ /api/social-media/* route prefix works")
    
    def test_bill_download_route_prefix(self, auth_token):
        """Verify /api/bill-download/* routes work"""
        res = requests.post(f"{BASE_URL}/api/bill-download/list", json={
            "token": auth_token
        })
        assert res.status_code == 200
        print(f"✓ /api/bill-download/* route prefix works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
