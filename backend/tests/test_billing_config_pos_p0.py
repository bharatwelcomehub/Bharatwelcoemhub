"""
P0 Billing Configuration & POS Workflow Tests
Tests for:
1. Billing Configuration CRUD (Tables, Cancellation Reasons, Menu Categories)
2. POS Workflow Validation (Dine-In table/guest, Takeaway/Delivery customer)
3. KOT/Bill Cancellation with mandatory reasons and audit trail
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
OPERATIONAL_CENTER = "PB-KHARADI"  # Center with seeded tables
OPERATIONAL_CENTER_ALT = "PB-PERTH"  # Alternative center with tables


class TestAuthentication:
    """Authentication for all tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        assert otp_res.status_code == 200, f"Send OTP failed: {otp_res.text}"
        
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP,
            "center": TEST_CENTER
        })
        assert verify_res.status_code == 200, f"Verify OTP failed: {verify_res.text}"
        token = verify_res.json().get("token")
        assert token, "No token returned"
        return token
    
    def test_auth_flow(self, auth_token):
        """Test authentication returns valid token"""
        assert auth_token is not None
        assert len(auth_token) > 10


# ============================================
# BILLING CONFIGURATION - TABLES CRUD
# ============================================

class TestTableManagement:
    """Table Management CRUD tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_list_tables_for_center(self, auth_token):
        """Test listing tables for a specific center"""
        res = requests.post(f"{BASE_URL}/api/billing-config/tables/list", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER
        })
        assert res.status_code == 200, f"List tables failed: {res.text}"
        data = res.json()
        
        assert "tables" in data, "Response should have 'tables' key"
        assert "total" in data, "Response should have 'total' key"
        assert isinstance(data["tables"], list), "Tables should be a list"
        
        # PB-KHARADI should have seeded tables (T1-T5, VIP1-VIP2)
        if data["total"] > 0:
            table = data["tables"][0]
            assert "table_no" in table, "Table should have table_no"
            assert "table_id" in table, "Table should have table_id"
            assert "capacity" in table, "Table should have capacity"
            assert "status" in table, "Table should have status"
    
    def test_create_table(self, auth_token):
        """Test creating a new table"""
        unique_table_no = f"TEST-{datetime.now().strftime('%H%M%S')}"
        
        res = requests.post(f"{BASE_URL}/api/billing-config/tables/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "table_no": unique_table_no,
            "capacity": 6,
            "floor": "1st Floor",
            "section": "Test Section",
            "is_active": True
        })
        assert res.status_code == 200, f"Create table failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True, "Table creation should succeed"
        assert "table_id" in data, "Response should have table_id"
        assert data["table_id"].startswith("TBL-"), f"Table ID should start with TBL-, got {data['table_id']}"
        
        # Verify table was created by listing
        list_res = requests.post(f"{BASE_URL}/api/billing-config/tables/list", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        tables = list_res.json().get("tables", [])
        created_table = next((t for t in tables if t["table_no"] == unique_table_no), None)
        assert created_table is not None, f"Created table {unique_table_no} not found in list"
        assert created_table["capacity"] == 6
        assert created_table["floor"] == "1st Floor"
    
    def test_create_table_duplicate_fails(self, auth_token):
        """Test creating duplicate table fails"""
        unique_table_no = f"DUP-{datetime.now().strftime('%H%M%S')}"
        
        # Create first table
        res1 = requests.post(f"{BASE_URL}/api/billing-config/tables/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "table_no": unique_table_no,
            "capacity": 4
        })
        assert res1.status_code == 200
        
        # Try to create duplicate
        res2 = requests.post(f"{BASE_URL}/api/billing-config/tables/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "table_no": unique_table_no,
            "capacity": 4
        })
        assert res2.status_code == 400, "Duplicate table should fail"
        assert "already exists" in res2.json().get("detail", "").lower()
    
    def test_create_table_missing_fields_fails(self, auth_token):
        """Test creating table without required fields fails"""
        # Missing table_no
        res = requests.post(f"{BASE_URL}/api/billing-config/tables/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "capacity": 4
        })
        assert res.status_code == 400, "Missing table_no should fail"
        
        # Missing center
        res2 = requests.post(f"{BASE_URL}/api/billing-config/tables/save", json={
            "token": auth_token,
            "table_no": "TEST-X",
            "capacity": 4
        })
        assert res2.status_code == 400, "Missing center should fail"
    
    def test_delete_table(self, auth_token):
        """Test deleting a table"""
        # Create a table to delete
        unique_table_no = f"DEL-{datetime.now().strftime('%H%M%S')}"
        create_res = requests.post(f"{BASE_URL}/api/billing-config/tables/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "table_no": unique_table_no,
            "capacity": 2
        })
        table_id = create_res.json()["table_id"]
        
        # Delete the table
        del_res = requests.post(f"{BASE_URL}/api/billing-config/tables/delete", json={
            "token": auth_token,
            "table_id": table_id
        })
        assert del_res.status_code == 200, f"Delete table failed: {del_res.text}"
        assert del_res.json().get("success") == True
        
        # Verify deletion
        list_res = requests.post(f"{BASE_URL}/api/billing-config/tables/list", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        tables = list_res.json().get("tables", [])
        deleted_table = next((t for t in tables if t["table_id"] == table_id), None)
        assert deleted_table is None, "Deleted table should not appear in list"


# ============================================
# BILLING CONFIGURATION - CANCELLATION REASONS CRUD
# ============================================

class TestCancellationReasons:
    """Cancellation Reasons CRUD tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_list_cancel_reasons(self, auth_token):
        """Test listing all cancellation reasons"""
        res = requests.post(f"{BASE_URL}/api/billing-config/cancel-reasons/list", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"List reasons failed: {res.text}"
        data = res.json()
        
        assert "reasons" in data, "Response should have 'reasons' key"
        assert "total" in data, "Response should have 'total' key"
        
        # Should have seeded reasons
        if data["total"] > 0:
            reason = data["reasons"][0]
            assert "reason_id" in reason, "Reason should have reason_id"
            assert "reason" in reason, "Reason should have reason text"
            assert "type" in reason, "Reason should have type (order/bill/kot)"
    
    def test_list_cancel_reasons_by_type(self, auth_token):
        """Test listing cancellation reasons filtered by type"""
        for reason_type in ["order", "bill", "kot"]:
            res = requests.post(f"{BASE_URL}/api/billing-config/cancel-reasons/list", json={
                "token": auth_token,
                "type": reason_type
            })
            assert res.status_code == 200, f"List {reason_type} reasons failed: {res.text}"
            data = res.json()
            
            # All returned reasons should be of the requested type
            for reason in data.get("reasons", []):
                assert reason["type"] == reason_type, f"Expected type {reason_type}, got {reason['type']}"
    
    def test_create_cancel_reason_order(self, auth_token):
        """Test creating an order cancellation reason"""
        unique_reason = f"TEST Order Reason {datetime.now().strftime('%H%M%S')}"
        
        res = requests.post(f"{BASE_URL}/api/billing-config/cancel-reasons/save", json={
            "token": auth_token,
            "reason": unique_reason,
            "type": "order",
            "is_active": True
        })
        assert res.status_code == 200, f"Create reason failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True
        assert "reason_id" in data
        assert data["reason_id"].startswith("CR-ORDER-")
    
    def test_create_cancel_reason_bill(self, auth_token):
        """Test creating a bill void reason"""
        unique_reason = f"TEST Bill Reason {datetime.now().strftime('%H%M%S')}"
        
        res = requests.post(f"{BASE_URL}/api/billing-config/cancel-reasons/save", json={
            "token": auth_token,
            "reason": unique_reason,
            "type": "bill",
            "is_active": True
        })
        assert res.status_code == 200, f"Create reason failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True
        assert data["reason_id"].startswith("CR-BILL-")
    
    def test_create_cancel_reason_kot(self, auth_token):
        """Test creating a KOT cancellation reason"""
        unique_reason = f"TEST KOT Reason {datetime.now().strftime('%H%M%S')}"
        
        res = requests.post(f"{BASE_URL}/api/billing-config/cancel-reasons/save", json={
            "token": auth_token,
            "reason": unique_reason,
            "type": "kot",
            "is_active": True
        })
        assert res.status_code == 200, f"Create reason failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True
        assert data["reason_id"].startswith("CR-KOT-")
    
    def test_create_cancel_reason_invalid_type_fails(self, auth_token):
        """Test creating reason with invalid type fails"""
        res = requests.post(f"{BASE_URL}/api/billing-config/cancel-reasons/save", json={
            "token": auth_token,
            "reason": "Invalid Type Reason",
            "type": "invalid"
        })
        assert res.status_code == 400, "Invalid type should fail"
    
    def test_delete_cancel_reason(self, auth_token):
        """Test deleting a cancellation reason"""
        # Create a reason to delete
        unique_reason = f"DELETE Reason {datetime.now().strftime('%H%M%S')}"
        create_res = requests.post(f"{BASE_URL}/api/billing-config/cancel-reasons/save", json={
            "token": auth_token,
            "reason": unique_reason,
            "type": "order"
        })
        reason_id = create_res.json()["reason_id"]
        
        # Delete
        del_res = requests.post(f"{BASE_URL}/api/billing-config/cancel-reasons/delete", json={
            "token": auth_token,
            "reason_id": reason_id
        })
        assert del_res.status_code == 200, f"Delete reason failed: {del_res.text}"
        assert del_res.json().get("success") == True


# ============================================
# BILLING CONFIGURATION - MENU CATEGORIES CRUD
# ============================================

class TestMenuCategories:
    """Menu Categories CRUD tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_list_categories(self, auth_token):
        """Test listing menu categories"""
        res = requests.post(f"{BASE_URL}/api/billing-config/categories/list", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"List categories failed: {res.text}"
        data = res.json()
        
        assert "categories" in data
        assert "total" in data
        
        if data["total"] > 0:
            cat = data["categories"][0]
            assert "name" in cat
            assert "display_order" in cat
    
    def test_create_category(self, auth_token):
        """Test creating a menu category"""
        unique_name = f"TEST Category {datetime.now().strftime('%H%M%S')}"
        
        res = requests.post(f"{BASE_URL}/api/billing-config/categories/save", json={
            "token": auth_token,
            "name": unique_name,
            "description": "Test category description",
            "display_order": 50,
            "is_active": True
        })
        assert res.status_code == 200, f"Create category failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True
        assert "category_id" in data
        assert data["category_id"].startswith("CAT-")
    
    def test_create_duplicate_category_fails(self, auth_token):
        """Test creating duplicate category fails"""
        unique_name = f"DUP Category {datetime.now().strftime('%H%M%S')}"
        
        # Create first
        res1 = requests.post(f"{BASE_URL}/api/billing-config/categories/save", json={
            "token": auth_token,
            "name": unique_name
        })
        assert res1.status_code == 200
        
        # Try duplicate
        res2 = requests.post(f"{BASE_URL}/api/billing-config/categories/save", json={
            "token": auth_token,
            "name": unique_name
        })
        assert res2.status_code == 400, "Duplicate category should fail"
    
    def test_delete_category(self, auth_token):
        """Test deleting a category"""
        unique_name = f"DEL Category {datetime.now().strftime('%H%M%S')}"
        create_res = requests.post(f"{BASE_URL}/api/billing-config/categories/save", json={
            "token": auth_token,
            "name": unique_name
        })
        category_id = create_res.json()["category_id"]
        
        del_res = requests.post(f"{BASE_URL}/api/billing-config/categories/delete", json={
            "token": auth_token,
            "category_id": category_id
        })
        assert del_res.status_code == 200, f"Delete category failed: {del_res.text}"
        assert del_res.json().get("success") == True


# ============================================
# POS WORKFLOW - DINE-IN VALIDATION
# ============================================

class TestPOSDineInWorkflow:
    """POS Dine-In workflow tests - Table and Guest Count mandatory"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_dinein_without_table_fails(self, auth_token):
        """Test Dine-In order without table selection returns 400"""
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Dine-In",
            "guest_count": 4
            # Missing table_no and table_id
        })
        assert res.status_code == 400, f"Dine-In without table should fail, got {res.status_code}: {res.text}"
        assert "table" in res.json().get("detail", "").lower(), "Error should mention table"
    
    def test_dinein_without_guest_count_fails(self, auth_token):
        """Test Dine-In order without guest count returns 400"""
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Dine-In",
            "table_no": "T1"
            # Missing guest_count
        })
        assert res.status_code == 400, f"Dine-In without guest count should fail, got {res.status_code}: {res.text}"
        assert "guest" in res.json().get("detail", "").lower(), "Error should mention guest count"
    
    def test_dinein_with_zero_guest_count_fails(self, auth_token):
        """Test Dine-In order with zero guest count returns 400"""
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Dine-In",
            "table_no": "T1",
            "guest_count": 0
        })
        assert res.status_code == 400, f"Dine-In with 0 guests should fail, got {res.status_code}: {res.text}"
    
    def test_dinein_with_table_and_guest_succeeds(self, auth_token):
        """Test Dine-In order with table and guest count succeeds"""
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Dine-In",
            "table_no": "T1",
            "guest_count": 4
        })
        assert res.status_code == 200, f"Dine-In with table and guests should succeed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True
        order = data.get("order", {})
        assert order["table_no"] == "T1"
        assert order["guest_count"] == 4
        assert order["order_type"] == "Dine-In"
    
    def test_dinein_with_table_id_succeeds(self, auth_token):
        """Test Dine-In order with table_id (from master) succeeds"""
        # First get a table_id from the tables list
        tables_res = requests.post(f"{BASE_URL}/api/billing-config/tables/list", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER
        })
        tables = tables_res.json().get("tables", [])
        
        if tables:
            table_id = tables[0]["table_id"]
            table_no = tables[0]["table_no"]
            
            res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
                "token": auth_token,
                "center": OPERATIONAL_CENTER,
                "order_type": "Dine-In",
                "table_id": table_id,
                "table_no": table_no,
                "guest_count": 2
            })
            assert res.status_code == 200, f"Dine-In with table_id should succeed: {res.text}"
            order = res.json().get("order", {})
            assert order["table_id"] == table_id


# ============================================
# POS WORKFLOW - TAKEAWAY/DELIVERY VALIDATION
# ============================================

class TestPOSTakeawayDeliveryWorkflow:
    """POS Takeaway/Delivery workflow tests - Customer Name and Phone mandatory"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_takeaway_without_customer_name_fails(self, auth_token):
        """Test Takeaway order without customer name returns 400"""
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Takeaway",
            "customer_phone": "9876543210"
            # Missing customer_name
        })
        assert res.status_code == 400, f"Takeaway without name should fail, got {res.status_code}: {res.text}"
        assert "name" in res.json().get("detail", "").lower(), "Error should mention customer name"
    
    def test_takeaway_without_customer_phone_fails(self, auth_token):
        """Test Takeaway order without customer phone returns 400"""
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Takeaway",
            "customer_name": "Test Customer"
            # Missing customer_phone
        })
        assert res.status_code == 400, f"Takeaway without phone should fail, got {res.status_code}: {res.text}"
        assert "phone" in res.json().get("detail", "").lower(), "Error should mention customer phone"
    
    def test_takeaway_with_customer_details_succeeds(self, auth_token):
        """Test Takeaway order with customer name and phone succeeds"""
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Takeaway",
            "customer_name": "Test Takeaway Customer",
            "customer_phone": "9876543210"
        })
        assert res.status_code == 200, f"Takeaway with customer details should succeed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True
        order = data.get("order", {})
        assert order["customer_name"] == "Test Takeaway Customer"
        assert order["customer_phone"] == "9876543210"
        assert order["order_type"] == "Takeaway"
    
    def test_delivery_without_customer_name_fails(self, auth_token):
        """Test Delivery order without customer name returns 400"""
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Delivery",
            "customer_phone": "9876543210"
        })
        assert res.status_code == 400, f"Delivery without name should fail, got {res.status_code}: {res.text}"
    
    def test_delivery_with_customer_details_succeeds(self, auth_token):
        """Test Delivery order with customer name and phone succeeds"""
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Delivery",
            "customer_name": "Test Delivery Customer",
            "customer_phone": "9876543211"
        })
        assert res.status_code == 200, f"Delivery with customer details should succeed: {res.text}"
        order = res.json().get("order", {})
        assert order["order_type"] == "Delivery"


# ============================================
# ORDER CANCELLATION WITH REASON & AUDIT TRAIL
# ============================================

class TestOrderCancellationWithReason:
    """Order cancellation with mandatory reason from master"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_cancel_order_without_reason_fails(self, auth_token):
        """Test cancelling order without reason fails"""
        # Create an order
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Dine-In",
            "table_no": "T99",
            "guest_count": 2
        })
        order_id = create_res.json()["order"]["order_id"]
        
        # Try to cancel without reason
        cancel_res = requests.post(f"{BASE_URL}/api/billing/order/cancel", json={
            "token": auth_token,
            "order_id": order_id
            # Missing reason_id and reason
        })
        assert cancel_res.status_code == 400, f"Cancel without reason should fail: {cancel_res.text}"
        assert "reason" in cancel_res.json().get("detail", "").lower()
    
    def test_cancel_order_with_reason_id_succeeds(self, auth_token):
        """Test cancelling order with reason_id from master succeeds"""
        # Get a cancel reason from master
        reasons_res = requests.post(f"{BASE_URL}/api/billing-config/cancel-reasons/list", json={
            "token": auth_token,
            "type": "order"
        })
        reasons = reasons_res.json().get("reasons", [])
        
        # Create a reason if none exist
        if not reasons:
            create_reason_res = requests.post(f"{BASE_URL}/api/billing-config/cancel-reasons/save", json={
                "token": auth_token,
                "reason": "Customer changed mind",
                "type": "order"
            })
            reason_id = create_reason_res.json()["reason_id"]
        else:
            reason_id = reasons[0]["reason_id"]
        
        # Create an order
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Dine-In",
            "table_no": "T98",
            "guest_count": 3
        })
        order_id = create_res.json()["order"]["order_id"]
        
        # Cancel with reason_id
        cancel_res = requests.post(f"{BASE_URL}/api/billing/order/cancel", json={
            "token": auth_token,
            "order_id": order_id,
            "reason_id": reason_id
        })
        assert cancel_res.status_code == 200, f"Cancel with reason_id should succeed: {cancel_res.text}"
        assert cancel_res.json().get("success") == True
    
    def test_cancel_order_with_free_text_reason_succeeds(self, auth_token):
        """Test cancelling order with free text reason succeeds"""
        # Create an order
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Takeaway",
            "customer_name": "Cancel Test",
            "customer_phone": "9999999999"
        })
        order_id = create_res.json()["order"]["order_id"]
        
        # Cancel with free text reason
        cancel_res = requests.post(f"{BASE_URL}/api/billing/order/cancel", json={
            "token": auth_token,
            "order_id": order_id,
            "reason": "Customer requested cancellation - other reason"
        })
        assert cancel_res.status_code == 200, f"Cancel with text reason should succeed: {cancel_res.text}"


# ============================================
# BILL VOID WITH REASON & AUDIT TRAIL
# ============================================

class TestBillVoidWithReason:
    """Bill void with mandatory reason and audit trail"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_void_bill_without_reason_fails(self, auth_token):
        """Test voiding bill without reason fails"""
        # Create order, add items, generate bill
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Dine-In",
            "table_no": "T97",
            "guest_count": 2
        })
        order_id = create_res.json()["order"]["order_id"]
        
        requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [{"item_name": "Void Test Item", "qty": 1, "unit_price": 100}]
        })
        
        bill_res = requests.post(f"{BASE_URL}/api/billing/bill/generate", json={
            "token": auth_token,
            "order_id": order_id,
            "payment_mode": "Cash"
        })
        bill_no = bill_res.json()["bill"]["bill_no"]
        
        # Try to void without reason
        void_res = requests.post(f"{BASE_URL}/api/billing/bill/void", json={
            "token": auth_token,
            "bill_no": bill_no
            # Missing reason_id and reason
        })
        assert void_res.status_code == 400, f"Void without reason should fail: {void_res.text}"
    
    def test_void_bill_with_reason_id_succeeds(self, auth_token):
        """Test voiding bill with reason_id from master succeeds"""
        # Get or create a bill void reason
        reasons_res = requests.post(f"{BASE_URL}/api/billing-config/cancel-reasons/list", json={
            "token": auth_token,
            "type": "bill"
        })
        reasons = reasons_res.json().get("reasons", [])
        
        if not reasons:
            create_reason_res = requests.post(f"{BASE_URL}/api/billing-config/cancel-reasons/save", json={
                "token": auth_token,
                "reason": "Duplicate bill generated",
                "type": "bill"
            })
            reason_id = create_reason_res.json()["reason_id"]
        else:
            reason_id = reasons[0]["reason_id"]
        
        # Create order, add items, generate bill
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Dine-In",
            "table_no": "T96",
            "guest_count": 2
        })
        order_id = create_res.json()["order"]["order_id"]
        
        requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [{"item_name": "Void Test Item 2", "qty": 1, "unit_price": 150}]
        })
        
        bill_res = requests.post(f"{BASE_URL}/api/billing/bill/generate", json={
            "token": auth_token,
            "order_id": order_id,
            "payment_mode": "UPI"
        })
        bill_no = bill_res.json()["bill"]["bill_no"]
        
        # Void with reason_id
        void_res = requests.post(f"{BASE_URL}/api/billing/bill/void", json={
            "token": auth_token,
            "bill_no": bill_no,
            "reason_id": reason_id
        })
        assert void_res.status_code == 200, f"Void with reason_id should succeed: {void_res.text}"
        assert void_res.json().get("success") == True


# ============================================
# KOT CANCELLATION WITH REASON & AUDIT TRAIL
# ============================================

class TestKOTCancellationWithReason:
    """KOT cancellation with mandatory reason"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_cancel_kot_without_reason_fails(self, auth_token):
        """Test cancelling KOT without reason fails"""
        # Create order, add items, generate KOT
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Dine-In",
            "table_no": "T95",
            "guest_count": 2
        })
        order_id = create_res.json()["order"]["order_id"]
        
        requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [{"item_name": "KOT Cancel Test", "qty": 1, "unit_price": 100}]
        })
        
        kot_res = requests.post(f"{BASE_URL}/api/billing/kot/generate", json={
            "token": auth_token,
            "order_id": order_id
        })
        kot_no = kot_res.json()["kot"]["kot_no"]
        
        # Try to cancel without reason
        cancel_res = requests.post(f"{BASE_URL}/api/billing/kot/cancel", json={
            "token": auth_token,
            "kot_no": kot_no
            # Missing reason_id and reason
        })
        assert cancel_res.status_code == 400, f"KOT cancel without reason should fail: {cancel_res.text}"
    
    def test_cancel_kot_with_reason_succeeds(self, auth_token):
        """Test cancelling KOT with reason succeeds"""
        # Get or create a KOT cancel reason
        reasons_res = requests.post(f"{BASE_URL}/api/billing-config/cancel-reasons/list", json={
            "token": auth_token,
            "type": "kot"
        })
        reasons = reasons_res.json().get("reasons", [])
        
        if not reasons:
            create_reason_res = requests.post(f"{BASE_URL}/api/billing-config/cancel-reasons/save", json={
                "token": auth_token,
                "reason": "Item out of stock",
                "type": "kot"
            })
            reason_id = create_reason_res.json()["reason_id"]
        else:
            reason_id = reasons[0]["reason_id"]
        
        # Create order, add items, generate KOT
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "order_type": "Dine-In",
            "table_no": "T94",
            "guest_count": 2
        })
        order_id = create_res.json()["order"]["order_id"]
        
        requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [{"item_name": "KOT Cancel Test 2", "qty": 1, "unit_price": 100}]
        })
        
        kot_res = requests.post(f"{BASE_URL}/api/billing/kot/generate", json={
            "token": auth_token,
            "order_id": order_id
        })
        kot_no = kot_res.json()["kot"]["kot_no"]
        
        # Cancel with reason_id
        cancel_res = requests.post(f"{BASE_URL}/api/billing/kot/cancel", json={
            "token": auth_token,
            "kot_no": kot_no,
            "reason_id": reason_id
        })
        assert cancel_res.status_code == 200, f"KOT cancel with reason should succeed: {cancel_res.text}"
        assert cancel_res.json().get("success") == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
