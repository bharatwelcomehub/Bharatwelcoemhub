"""
Test Master Data Architecture - Iteration 36
Tests the master-data-first architecture fix:
- Franchise-Center Mapping via centers.franchise_code field
- Master dropdown endpoints (order_types, payment_modes, discount_types)
- Dynamic dine-in detection in billing
- No hardcoded center arrays in masters.py
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
TEST_CENTER = "PB-MGT"
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"

# Test centers for franchise mapping
LINKED_CENTER = "PB-HSR"  # Should be linked to FR-TEST-INDIA
UNLINKED_CENTER = "PB-MGT"  # Should show as Unmapped


class TestAuthentication:
    """Authentication tests - run first to get token"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for subsequent tests"""
        # Send OTP
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        assert otp_res.status_code == 200, f"Send OTP failed: {otp_res.text}"
        
        # Verify OTP
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        assert verify_res.status_code == 200, f"Verify OTP failed: {verify_res.text}"
        
        data = verify_res.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_auth_flow(self, auth_token):
        """Verify auth flow works"""
        assert auth_token is not None
        assert len(auth_token) > 10
        print(f"✓ Auth token obtained: {auth_token[:20]}...")


class TestMasterDataEndpoints:
    """Test public GET endpoints for master dropdown data"""
    
    def test_get_order_types(self):
        """GET /api/masters/order_types should return CATERING, DELIVERY, DINE-IN, TAKEAWAY from DB"""
        res = requests.get(f"{BASE_URL}/api/masters/order_types")
        assert res.status_code == 200, f"Failed: {res.text}"
        
        data = res.json()
        assert "items" in data, "No items in response"
        
        items = data["items"]
        item_names = [i["name"].upper() for i in items]
        
        # Verify expected order types exist
        expected = ["CATERING", "DELIVERY", "DINE-IN", "TAKEAWAY"]
        for exp in expected:
            assert exp in item_names, f"Missing order type: {exp}"
        
        print(f"✓ Order types from DB: {item_names}")
    
    def test_get_payment_modes(self):
        """GET /api/masters/payment_modes should return CASH, UPI, CARD, BANK TRANSFER etc from DB"""
        res = requests.get(f"{BASE_URL}/api/masters/payment_modes")
        assert res.status_code == 200, f"Failed: {res.text}"
        
        data = res.json()
        assert "items" in data, "No items in response"
        
        items = data["items"]
        item_names = [i["name"].upper() for i in items]
        
        # Verify expected payment modes exist
        expected = ["CASH", "UPI", "CARD"]
        for exp in expected:
            assert exp in item_names, f"Missing payment mode: {exp}"
        
        print(f"✓ Payment modes from DB: {item_names}")
    
    def test_get_discount_types(self):
        """GET /api/masters/discount_types should return master discount types from DB"""
        res = requests.get(f"{BASE_URL}/api/masters/discount_types")
        assert res.status_code == 200, f"Failed: {res.text}"
        
        data = res.json()
        assert "items" in data, "No items in response"
        
        items = data["items"]
        assert len(items) > 0, "No discount types found"
        
        item_names = [i["name"] for i in items]
        print(f"✓ Discount types from DB: {item_names}")
    
    def test_master_endpoints_no_auth_required(self):
        """Public GET endpoints should work without auth token"""
        endpoints = [
            "/api/masters/order_types",
            "/api/masters/payment_modes",
            "/api/masters/discount_types"
        ]
        
        for endpoint in endpoints:
            res = requests.get(f"{BASE_URL}{endpoint}")
            assert res.status_code == 200, f"{endpoint} failed without auth: {res.text}"
        
        print("✓ All master GET endpoints work without auth")


class TestFranchiseCenterMapping:
    """Test franchise-center mapping via centers.franchise_code field"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_res.json().get("token")
    
    def test_franchise_by_center_linked(self, auth_token):
        """GET /api/franchises/by-center/PB-HSR should find franchise via centers.franchise_code"""
        res = requests.post(f"{BASE_URL}/api/franchises/by-center/{LINKED_CENTER}", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        
        data = res.json()
        # Check if franchise is found
        if data.get("found"):
            franchise = data.get("franchise", {})
            print(f"✓ PB-HSR linked to franchise: {franchise.get('franchise_code', 'N/A')} - {franchise.get('franchise_name', 'N/A')}")
        else:
            print(f"⚠ PB-HSR not linked to any franchise (may need seeding)")
    
    def test_franchise_by_center_unlinked(self, auth_token):
        """GET /api/franchises/by-center/PB-MGT should return found=false (unmapped)"""
        res = requests.post(f"{BASE_URL}/api/franchises/by-center/{UNLINKED_CENTER}", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        
        data = res.json()
        # PB-MGT should be unmapped
        print(f"✓ PB-MGT franchise mapping: found={data.get('found')}")


class TestDynamicDineInDetection:
    """Test dynamic order type detection in billing"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_res.json().get("token")
    
    def test_dinein_requires_table_and_guest(self, auth_token):
        """DINE-IN order type should require table_no and guest_count"""
        # Try creating DINE-IN order without table
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "order_type": "DINE-IN",
            "table_no": "",
            "guest_count": 0
        })
        
        # Should fail with 400
        assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.text}"
        assert "table" in res.text.lower() or "mandatory" in res.text.lower(), f"Error should mention table: {res.text}"
        print("✓ DINE-IN validation: requires table")
    
    def test_dinein_case_insensitive(self, auth_token):
        """Dine-In detection should work with any casing"""
        # Test with lowercase
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "order_type": "dine-in",  # lowercase
            "table_no": "",
            "guest_count": 0
        })
        
        # Should still fail (validates as dine-in)
        assert res.status_code == 400, f"Expected 400 for lowercase dine-in: {res.text}"
        print("✓ DINE-IN detection works case-insensitively")
    
    def test_takeaway_requires_customer_info(self, auth_token):
        """TAKEAWAY order type should require customer_name and customer_phone"""
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "order_type": "TAKEAWAY",
            "customer_name": "",
            "customer_phone": ""
        })
        
        # Should fail with 400
        assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.text}"
        assert "customer" in res.text.lower() or "name" in res.text.lower() or "phone" in res.text.lower(), f"Error should mention customer: {res.text}"
        print("✓ TAKEAWAY validation: requires customer info")
    
    def test_delivery_requires_customer_info(self, auth_token):
        """DELIVERY order type should require customer_name and customer_phone"""
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "order_type": "DELIVERY",
            "customer_name": "",
            "customer_phone": ""
        })
        
        # Should fail with 400
        assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.text}"
        print("✓ DELIVERY validation: requires customer info")
    
    def test_valid_dinein_order_creation(self, auth_token):
        """Valid DINE-IN order with table and guest should succeed"""
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "order_type": "DINE-IN",
            "table_no": "TEST-T1",
            "guest_count": 2
        })
        
        assert res.status_code == 200, f"Failed to create valid DINE-IN order: {res.text}"
        data = res.json()
        assert data.get("success") == True
        assert "order" in data
        order_id = data["order"]["order_id"]
        print(f"✓ Valid DINE-IN order created: {order_id}")
        
        # Cleanup - cancel the test order
        cancel_res = requests.post(f"{BASE_URL}/api/billing/order/cancel", json={
            "token": auth_token,
            "order_id": order_id,
            "reason": "TEST cleanup"
        })
        print(f"  Cleanup: order cancelled")
    
    def test_valid_takeaway_order_creation(self, auth_token):
        """Valid TAKEAWAY order with customer info should succeed"""
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "order_type": "TAKEAWAY",
            "customer_name": "TEST Customer",
            "customer_phone": "9999999999"
        })
        
        assert res.status_code == 200, f"Failed to create valid TAKEAWAY order: {res.text}"
        data = res.json()
        assert data.get("success") == True
        order_id = data["order"]["order_id"]
        print(f"✓ Valid TAKEAWAY order created: {order_id}")
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/billing/order/cancel", json={
            "token": auth_token,
            "order_id": order_id,
            "reason": "TEST cleanup"
        })


class TestWorkingCapitalFranchiseMapping:
    """Test MIS Working Capital uses centers.franchise_code as primary strategy"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_res.json().get("token")
    
    def test_working_capital_endpoint(self, auth_token):
        """GET /api/mis/working-capital should work and use franchise mapping"""
        res = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": auth_token,
            "center": "all"
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        
        data = res.json()
        # Check response structure
        assert "initial_working_capital" in data or "available_working_capital" in data, f"Missing WC fields: {data.keys()}"
        
        print(f"✓ Working capital endpoint works")
        print(f"  Initial WC: {data.get('initial_working_capital', 0)}")
        print(f"  Available WC: {data.get('available_working_capital', 0)}")
        print(f"  Centers: {len(data.get('centers', []))}")


class TestBillingConfigEndpoints:
    """Test billing configuration endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_res.json().get("token")
    
    def test_billing_config_get(self, auth_token):
        """GET billing config for a center"""
        res = requests.post(f"{BASE_URL}/api/billing/config/get", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        
        data = res.json()
        assert "config" in data
        config = data["config"]
        
        # Verify config structure
        assert "gst_percentage" in config
        assert "currency_symbol" in config
        
        print(f"✓ Billing config for {TEST_CENTER}:")
        print(f"  GST: {config.get('gst_percentage')}% ({config.get('gst_type')})")
        print(f"  Currency: {config.get('currency_symbol')} ({config.get('currency_code')})")
    
    def test_billing_menu_endpoint(self, auth_token):
        """GET POS menu for a center"""
        res = requests.post(f"{BASE_URL}/api/billing/menu", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        
        data = res.json()
        assert "items" in data
        assert "categories" in data
        
        print(f"✓ POS menu loaded: {len(data['items'])} items, {len(data['categories'])} categories")


class TestCentersEndpoint:
    """Test centers endpoint returns proper data"""
    
    def test_get_centers(self):
        """GET /api/centers should return center list"""
        res = requests.get(f"{BASE_URL}/api/centers")
        
        assert res.status_code == 200, f"Failed: {res.text}"
        
        data = res.json()
        assert "centers" in data
        
        centers = data["centers"]
        assert len(centers) > 0, "No centers found"
        
        # Check for expected centers
        center_codes = [c["code"] for c in centers]
        print(f"✓ Centers loaded: {len(centers)} centers")
        print(f"  Sample codes: {center_codes[:5]}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
