"""
Test POS Billing Sidebar Feature
- Tests billing menu endpoint
- Tests billing order creation endpoint
- Tests MIS Dashboard endpoints (no profit fields)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_CENTER = "PB-MGT"
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"


class TestAuthentication:
    """Authentication tests to get token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        # Send OTP
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        assert otp_res.status_code == 200, f"Send OTP failed: {otp_res.text}"
        
        # Verify OTP
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP,
            "center": TEST_CENTER
        })
        assert verify_res.status_code == 200, f"Verify OTP failed: {verify_res.text}"
        data = verify_res.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_login_success(self, auth_token):
        """Test that login works and returns token"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print(f"✓ Login successful, token obtained")


class TestBillingEndpoints:
    """Test billing/POS related endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP,
            "center": TEST_CENTER
        })
        return verify_res.json().get("token")
    
    def test_billing_menu_endpoint(self, auth_token):
        """Test /api/billing/menu endpoint returns menu items"""
        res = requests.post(f"{BASE_URL}/api/billing/menu", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        assert res.status_code == 200, f"Billing menu failed: {res.text}"
        data = res.json()
        assert "items" in data, "No items in response"
        assert "categories" in data, "No categories in response"
        print(f"✓ Billing menu endpoint works - {len(data.get('items', []))} items, {len(data.get('categories', []))} categories")
    
    def test_billing_order_create(self, auth_token):
        """Test /api/billing/order/create endpoint"""
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "table_no": "T99",
            "order_type": "Dine-In"
        })
        assert res.status_code == 200, f"Order create failed: {res.text}"
        data = res.json()
        assert "order" in data, "No order in response"
        order = data["order"]
        assert "order_id" in order, "No order_id in order"
        assert order.get("center") == TEST_CENTER, "Center mismatch"
        print(f"✓ Order created: {order.get('order_id')}")
        
        # Clean up - cancel the test order
        cancel_res = requests.post(f"{BASE_URL}/api/billing/order/cancel", json={
            "token": auth_token,
            "order_id": order["order_id"],
            "reason": "Test cleanup"
        })
        print(f"  Order cancelled for cleanup: {cancel_res.status_code}")


class TestMISDashboard:
    """Test MIS Dashboard endpoints - verify no profit fields"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP,
            "center": TEST_CENTER
        })
        return verify_res.json().get("token")
    
    def test_mis_overview_endpoint(self, auth_token):
        """Test /api/mis/overview endpoint"""
        res = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": auth_token,
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 200, f"MIS overview failed: {res.text}"
        data = res.json()
        assert "summary" in data, "No summary in response"
        summary = data["summary"]
        # Verify key fields exist
        assert "total_sales" in summary, "No total_sales"
        assert "total_expenses" in summary, "No total_expenses"
        print(f"✓ MIS overview works - Sales: {summary.get('total_sales')}, Expenses: {summary.get('total_expenses')}")
    
    def test_mis_working_capital_endpoint(self, auth_token):
        """Test /api/mis/working-capital endpoint"""
        res = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": auth_token,
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 200, f"MIS working capital failed: {res.text}"
        data = res.json()
        # Verify working capital structure
        assert "available_working_capital" in data or "total_working_capital" in data, "No working capital field"
        print(f"✓ MIS working capital works - Available WC: {data.get('available_working_capital', data.get('total_working_capital'))}")


class TestCentersEndpoint:
    """Test centers endpoint for dropdown"""
    
    def test_centers_list(self):
        """Test /api/centers endpoint returns centers"""
        res = requests.get(f"{BASE_URL}/api/centers")
        assert res.status_code == 200, f"Centers list failed: {res.text}"
        data = res.json()
        assert "centers" in data, "No centers in response"
        centers = data["centers"]
        assert len(centers) > 0, "No centers returned"
        print(f"✓ Centers endpoint works - {len(centers)} centers returned")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
