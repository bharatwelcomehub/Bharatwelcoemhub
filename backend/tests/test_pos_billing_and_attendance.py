"""
Test POS Billing (dual-view rewrite) and Attendance Transfer-Aware Features
Tests:
1. Master data endpoints (payment_modes, order_types, discount_types)
2. POS Table listing for centers with tables
3. POS Order creation (Dine-In, Delivery, Takeaway)
4. POS Add items to order
5. POS KOT generation
6. POS Bill generation with payment modes
7. Attendance monthly-grid with transfer-aware employees
8. Attendance attendance_month with transfer-aware employees
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_CENTER = "PB-MGT"
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"

# Centers with tables configured (PB-PERTH is an Australia center)
CENTER_WITH_TABLES = "PB-PERTH"


class TestMasterDataEndpoints:
    """Test public master data endpoints (no auth required)"""
    
    def test_get_payment_modes(self):
        """GET /api/masters/payment_modes returns active payment modes"""
        response = requests.get(f"{BASE_URL}/api/masters/payment_modes")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0, "Expected at least one payment mode"
        
        # Verify expected payment modes exist
        names = [item["name"] for item in data["items"]]
        assert "CASH" in names, "CASH payment mode should exist"
        print(f"PASS: Found {len(data['items'])} payment modes: {names[:5]}...")
    
    def test_get_order_types(self):
        """GET /api/masters/order_types returns active order types"""
        response = requests.get(f"{BASE_URL}/api/masters/order_types")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0, "Expected at least one order type"
        
        names = [item["name"] for item in data["items"]]
        # Verify expected order types
        assert "DINE-IN" in names, "DINE-IN order type should exist"
        assert "DELIVERY" in names, "DELIVERY order type should exist"
        assert "TAKEAWAY" in names, "TAKEAWAY order type should exist"
        print(f"PASS: Found {len(data['items'])} order types: {names}")
    
    def test_get_discount_types(self):
        """GET /api/masters/discount_types returns active discount types"""
        response = requests.get(f"{BASE_URL}/api/masters/discount_types")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0, "Expected at least one discount type"
        
        names = [item["name"] for item in data["items"]]
        print(f"PASS: Found {len(data['items'])} discount types: {names[:5]}...")


class TestAuthentication:
    """Test authentication flow"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        # Send OTP
        otp_response = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        assert otp_response.status_code == 200, f"Send OTP failed: {otp_response.text}"
        
        # Verify OTP
        verify_response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        assert verify_response.status_code == 200, f"Verify OTP failed: {verify_response.text}"
        
        data = verify_response.json()
        assert "token" in data, "Token not returned in verify_otp response"
        print(f"PASS: Authentication successful, token obtained")
        return data["token"]
    
    def test_auth_flow(self, auth_token):
        """Verify auth token is valid"""
        assert auth_token is not None
        assert len(auth_token) > 10
        print(f"PASS: Auth token is valid (length: {len(auth_token)})")


class TestPOSTableListing:
    """Test POS table listing for centers"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        otp_response = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        verify_response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_response.json().get("token")
    
    def test_list_tables_for_center_with_tables(self, auth_token):
        """POST /api/billing-config/tables/list returns tables for PB-KHARADI"""
        response = requests.post(f"{BASE_URL}/api/billing-config/tables/list", json={
            "token": auth_token,
            "center": CENTER_WITH_TABLES
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "tables" in data
        # PB-KHARADI should have tables configured
        print(f"PASS: Found {len(data['tables'])} tables for {CENTER_WITH_TABLES}")
    
    def test_list_tables_for_center_without_tables(self, auth_token):
        """POST /api/billing-config/tables/list returns empty for PB-MGT"""
        response = requests.post(f"{BASE_URL}/api/billing-config/tables/list", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "tables" in data
        # PB-MGT has no tables configured
        print(f"PASS: Found {len(data['tables'])} tables for {TEST_CENTER} (expected 0 or few)")


class TestPOSOrderFlow:
    """Test complete POS order flow: Create -> Add Items -> KOT -> Bill"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        otp_response = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        verify_response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_response.json().get("token")
    
    def test_create_delivery_order(self, auth_token):
        """POST /api/billing/order/create creates a DELIVERY order"""
        response = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": CENTER_WITH_TABLES,
            "table_no": "",
            "table_id": "",
            "order_type": "DELIVERY",
            "guest_count": 0,
            "customer_name": "TEST_Customer",
            "customer_phone": "9876543210"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "order" in data
        assert data["order"]["order_type"] == "DELIVERY"
        assert data["order"]["customer_name"] == "TEST_Customer"
        assert data["order"]["status"] == "active"
        print(f"PASS: Created DELIVERY order {data['order']['order_id']}")
        return data["order"]["order_id"]
    
    def test_create_takeaway_order(self, auth_token):
        """POST /api/billing/order/create creates a TAKEAWAY order"""
        response = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": CENTER_WITH_TABLES,
            "table_no": "",
            "table_id": "",
            "order_type": "TAKEAWAY",
            "guest_count": 0,
            "customer_name": "TEST_Takeaway_Customer",
            "customer_phone": "9876543211"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "order" in data
        assert data["order"]["order_type"] == "TAKEAWAY"
        print(f"PASS: Created TAKEAWAY order {data['order']['order_id']}")
    
    def test_delivery_order_requires_customer_info(self, auth_token):
        """DELIVERY order without customer info should fail"""
        response = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": CENTER_WITH_TABLES,
            "table_no": "",
            "table_id": "",
            "order_type": "DELIVERY",
            "guest_count": 0,
            "customer_name": "",
            "customer_phone": ""
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("PASS: DELIVERY order correctly requires customer info")
    
    def test_full_order_flow_with_kot_and_bill(self, auth_token):
        """Complete flow: Create order -> Add items -> Generate KOT -> Generate Bill"""
        # Step 1: Create order
        create_response = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": CENTER_WITH_TABLES,
            "table_no": "",
            "table_id": "",
            "order_type": "DELIVERY",
            "guest_count": 0,
            "customer_name": "TEST_Full_Flow",
            "customer_phone": "9876543212"
        })
        assert create_response.status_code == 200, f"Create order failed: {create_response.text}"
        order_id = create_response.json()["order"]["order_id"]
        print(f"Step 1 PASS: Created order {order_id}")
        
        # Step 2: Add items
        add_response = requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [
                {"item_name": "Masala Tea", "category": "TEA / COFFEE", "qty": 2, "unit_price": 65, "is_veg": True},
                {"item_name": "Vada Pav", "category": "SNACKS", "qty": 1, "unit_price": 55, "is_veg": True}
            ]
        })
        assert add_response.status_code == 200, f"Add items failed: {add_response.text}"
        order_data = add_response.json()["order"]
        assert len(order_data["items"]) == 2, "Expected 2 items in order"
        print(f"Step 2 PASS: Added 2 items to order")
        
        # Step 3: Generate KOT
        kot_response = requests.post(f"{BASE_URL}/api/billing/kot/generate", json={
            "token": auth_token,
            "order_id": order_id
        })
        assert kot_response.status_code == 200, f"Generate KOT failed: {kot_response.text}"
        kot_data = kot_response.json()["kot"]
        assert "kot_no" in kot_data
        print(f"Step 3 PASS: Generated KOT {kot_data['kot_no']}")
        
        # Step 4: Generate Bill
        bill_response = requests.post(f"{BASE_URL}/api/billing/bill/generate", json={
            "token": auth_token,
            "order_id": order_id,
            "payment_mode": "CASH",
            "discount_type": "none",
            "discount_value": 0,
            "customer_name": "TEST_Full_Flow",
            "customer_phone": "9876543212"
        })
        assert bill_response.status_code == 200, f"Generate Bill failed: {bill_response.text}"
        bill_data = bill_response.json()["bill"]
        assert "bill_no" in bill_data
        assert bill_data["payment_mode"] == "CASH"
        assert bill_data["grand_total"] > 0
        print(f"Step 4 PASS: Generated Bill {bill_data['bill_no']} with total {bill_data['grand_total']}")
        
        # Verify order status changed to billed
        get_order_response = requests.post(f"{BASE_URL}/api/billing/order/get", json={
            "token": auth_token,
            "order_id": order_id
        })
        assert get_order_response.status_code == 200
        final_order = get_order_response.json()["order"]
        assert final_order["status"] == "billed", f"Expected status 'billed', got '{final_order['status']}'"
        print("Step 5 PASS: Order status is 'billed'")


class TestPOSMenu:
    """Test POS menu retrieval"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        otp_response = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        verify_response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_response.json().get("token")
    
    def test_get_pos_menu(self, auth_token):
        """POST /api/billing/menu returns menu items for center"""
        response = requests.post(f"{BASE_URL}/api/billing/menu", json={
            "token": auth_token,
            "center": CENTER_WITH_TABLES
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data
        assert "categories" in data
        print(f"PASS: Found {len(data['items'])} menu items in {len(data['categories'])} categories")


class TestAttendanceTransferAwareness:
    """Test attendance endpoints include transferred-out employees"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        otp_response = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        verify_response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_response.json().get("token")
    
    def test_monthly_grid_endpoint(self, auth_token):
        """POST /api/attendance-dashboard/monthly-grid returns employee grid with transfer_tag"""
        current_month = datetime.now().strftime("%Y-%m")
        response = requests.post(f"{BASE_URL}/api/attendance-dashboard/monthly-grid", json={
            "token": auth_token,
            "center": CENTER_WITH_TABLES,
            "month": current_month
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "employees" in data
        assert "days_in_month" in data
        
        # Check that employees have transfer_tag field
        if len(data["employees"]) > 0:
            first_emp = data["employees"][0]
            assert "transfer_tag" in first_emp, "Employee should have transfer_tag field"
            assert first_emp["transfer_tag"] in ["HOME", "TRANSFERRED_OUT", "TRANSFERRED_IN"], \
                f"Invalid transfer_tag: {first_emp['transfer_tag']}"
        
        print(f"PASS: Monthly grid returned {len(data['employees'])} employees for {current_month}")
        
        # Count employees by transfer_tag
        tags = {}
        for emp in data["employees"]:
            tag = emp.get("transfer_tag", "UNKNOWN")
            tags[tag] = tags.get(tag, 0) + 1
        print(f"  Transfer tags breakdown: {tags}")
    
    def test_attendance_month_endpoint(self, auth_token):
        """POST /api/attendance_month returns employee grid with transfer_tag"""
        current_month = datetime.now().strftime("%Y-%m")
        response = requests.post(f"{BASE_URL}/api/attendance_month", json={
            "token": auth_token,
            "center": CENTER_WITH_TABLES,
            "month": current_month
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "grid" in data
        
        # Check that grid entries have transfer_tag field
        if len(data["grid"]) > 0:
            first_emp = data["grid"][0]
            assert "transfer_tag" in first_emp, "Grid entry should have transfer_tag field"
            assert first_emp["transfer_tag"] in ["HOME", "TRANSFERRED_OUT", "TRANSFERRED_IN"], \
                f"Invalid transfer_tag: {first_emp['transfer_tag']}"
        
        print(f"PASS: Attendance month returned {len(data['grid'])} employees for {current_month}")
        
        # Count employees by transfer_tag
        tags = {}
        for emp in data["grid"]:
            tag = emp.get("transfer_tag", "UNKNOWN")
            tags[tag] = tags.get(tag, 0) + 1
        print(f"  Transfer tags breakdown: {tags}")


class TestPOSCancelReasons:
    """Test POS cancel reasons from master data"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        otp_response = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        verify_response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_response.json().get("token")
    
    def test_list_cancel_reasons(self, auth_token):
        """POST /api/billing-config/cancel-reasons/list returns cancel reasons"""
        response = requests.post(f"{BASE_URL}/api/billing-config/cancel-reasons/list", json={
            "token": auth_token
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "reasons" in data
        print(f"PASS: Found {len(data['reasons'])} cancel reasons")


class TestPOSBillingConfig:
    """Test POS billing configuration"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        otp_response = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        verify_response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_response.json().get("token")
    
    def test_get_billing_config(self, auth_token):
        """POST /api/billing/config/get returns billing config for center"""
        response = requests.post(f"{BASE_URL}/api/billing/config/get", json={
            "token": auth_token,
            "center": CENTER_WITH_TABLES
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "config" in data
        config = data["config"]
        assert "gst_percentage" in config
        assert "currency_symbol" in config
        print(f"PASS: Billing config for {CENTER_WITH_TABLES}: GST {config['gst_percentage']}%, Currency {config['currency_symbol']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
