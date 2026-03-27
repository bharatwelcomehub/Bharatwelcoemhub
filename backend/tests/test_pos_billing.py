"""
POS/Billing System Tests
Tests for Restaurant POS, KOT, Invoice, GST calculations, and Bill management
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
OPERATIONAL_CENTER = "PB-HSR"  # India center with menu items (5% GST exclusive)
INTERNATIONAL_CENTER = "PB-PERTH"  # Australia center (10% GST inclusive)


class TestAuthentication:
    """Authentication tests for POS billing"""
    
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
        token = verify_res.json().get("token")
        assert token, "No token returned"
        return token
    
    def test_auth_flow(self, auth_token):
        """Test authentication returns valid token"""
        assert auth_token is not None
        assert len(auth_token) > 10


class TestBillingConfig:
    """Billing configuration tests - GST settings per country"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_india_center_config(self, auth_token):
        """Test India center returns 5% exclusive GST"""
        res = requests.post(f"{BASE_URL}/api/billing/config/get", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER
        })
        assert res.status_code == 200, f"Config get failed: {res.text}"
        data = res.json()
        config = data.get("config", {})
        
        # Verify India GST config
        assert config.get("gst_percentage") == 5, f"Expected 5% GST, got {config.get('gst_percentage')}"
        assert config.get("gst_type") == "exclusive", f"Expected exclusive GST, got {config.get('gst_type')}"
        assert config.get("currency_symbol") == "₹", f"Expected ₹ symbol, got {config.get('currency_symbol')}"
        assert data.get("country") == "India", f"Expected India, got {data.get('country')}"
    
    def test_australia_center_config(self, auth_token):
        """Test Australia center returns 10% inclusive GST"""
        res = requests.post(f"{BASE_URL}/api/billing/config/get", json={
            "token": auth_token,
            "center": INTERNATIONAL_CENTER
        })
        assert res.status_code == 200, f"Config get failed: {res.text}"
        data = res.json()
        config = data.get("config", {})
        
        # Verify Australia GST config
        assert config.get("gst_percentage") == 10, f"Expected 10% GST, got {config.get('gst_percentage')}"
        assert config.get("gst_type") == "inclusive", f"Expected inclusive GST, got {config.get('gst_type')}"
        assert config.get("currency_symbol") == "$", f"Expected $ symbol, got {config.get('currency_symbol')}"
        assert data.get("country") == "Australia", f"Expected Australia, got {data.get('country')}"


class TestMenuItems:
    """Menu items retrieval tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_get_menu_for_operational_center(self, auth_token):
        """Test menu retrieval for PB-HSR (operational center with items)"""
        res = requests.post(f"{BASE_URL}/api/billing/menu", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER
        })
        assert res.status_code == 200, f"Menu get failed: {res.text}"
        data = res.json()
        
        items = data.get("items", [])
        categories = data.get("categories", [])
        total = data.get("total", 0)
        
        # PB-HSR should have menu items
        assert total > 0, f"Expected menu items for {OPERATIONAL_CENTER}, got {total}"
        assert len(items) > 0, "Items list should not be empty"
        assert len(categories) > 0, "Categories list should not be empty"
        
        # Verify item structure
        first_item = items[0]
        assert "name" in first_item, "Item should have name"
        assert "price" in first_item, "Item should have price"
        assert "category" in first_item, "Item should have category"
        assert first_item["price"] > 0, "Item price should be positive"
    
    def test_menu_item_structure(self, auth_token):
        """Test menu item has all required fields"""
        res = requests.post(f"{BASE_URL}/api/billing/menu", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER
        })
        data = res.json()
        items = data.get("items", [])
        
        if items:
            item = items[0]
            required_fields = ["name", "category", "price", "is_veg"]
            for field in required_fields:
                assert field in item, f"Item missing field: {field}"


class TestOrderManagement:
    """Order CRUD operations tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_create_order(self, auth_token):
        """Test order creation returns order_id"""
        res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "table_no": "T99",
            "order_type": "Dine-In"
        })
        assert res.status_code == 200, f"Order create failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True, "Order creation should succeed"
        order = data.get("order", {})
        assert "order_id" in order, "Order should have order_id"
        assert order["order_id"].startswith("ORD-"), f"Order ID should start with ORD-, got {order['order_id']}"
        assert order["center"] == OPERATIONAL_CENTER
        assert order["table_no"] == "T99"
        assert order["status"] == "active"
    
    def test_add_items_to_order(self, auth_token):
        """Test adding items to order"""
        # Create order first
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "table_no": "T98",
            "order_type": "Takeaway"
        })
        order_id = create_res.json()["order"]["order_id"]
        
        # Add items
        add_res = requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [
                {"item_name": "Test Item 1", "category": "Test", "qty": 2, "unit_price": 100, "is_veg": True},
                {"item_name": "Test Item 2", "category": "Test", "qty": 1, "unit_price": 150, "is_veg": False}
            ]
        })
        assert add_res.status_code == 200, f"Add items failed: {add_res.text}"
        data = add_res.json()
        
        assert data.get("success") == True
        order = data.get("order", {})
        items = order.get("items", [])
        assert len(items) == 2, f"Expected 2 items, got {len(items)}"
        
        # Verify item totals
        assert items[0]["total"] == 200, f"Item 1 total should be 200, got {items[0]['total']}"
        assert items[1]["total"] == 150, f"Item 2 total should be 150, got {items[1]['total']}"
    
    def test_update_item_quantity(self, auth_token):
        """Test updating item quantity"""
        # Create order and add item
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "table_no": "T97"
        })
        order_id = create_res.json()["order"]["order_id"]
        
        requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [{"item_name": "Qty Test Item", "qty": 1, "unit_price": 100}]
        })
        
        # Update quantity
        update_res = requests.post(f"{BASE_URL}/api/billing/order/update-item-qty", json={
            "token": auth_token,
            "order_id": order_id,
            "item_index": 0,
            "qty": 5
        })
        assert update_res.status_code == 200, f"Update qty failed: {update_res.text}"
        
        order = update_res.json()["order"]
        assert order["items"][0]["qty"] == 5
        assert order["items"][0]["total"] == 500  # 5 * 100
    
    def test_cancel_order(self, auth_token):
        """Test order cancellation"""
        # Create order
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "table_no": "T96"
        })
        order_id = create_res.json()["order"]["order_id"]
        
        # Cancel order
        cancel_res = requests.post(f"{BASE_URL}/api/billing/order/cancel", json={
            "token": auth_token,
            "order_id": order_id,
            "reason": "Test cancellation"
        })
        assert cancel_res.status_code == 200, f"Cancel failed: {cancel_res.text}"
        assert cancel_res.json().get("success") == True
    
    def test_get_active_orders(self, auth_token):
        """Test fetching active orders for a center"""
        res = requests.post(f"{BASE_URL}/api/billing/orders/active", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER
        })
        assert res.status_code == 200, f"Get active orders failed: {res.text}"
        data = res.json()
        
        assert "orders" in data
        assert "count" in data
        assert isinstance(data["orders"], list)


class TestKOTGeneration:
    """Kitchen Order Ticket tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_generate_kot(self, auth_token):
        """Test KOT generation for new items"""
        # Create order with items
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "table_no": "T95"
        })
        order_id = create_res.json()["order"]["order_id"]
        
        requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [
                {"item_name": "KOT Test Item 1", "qty": 2, "unit_price": 100, "is_veg": True},
                {"item_name": "KOT Test Item 2", "qty": 1, "unit_price": 200, "is_veg": False}
            ]
        })
        
        # Generate KOT
        kot_res = requests.post(f"{BASE_URL}/api/billing/kot/generate", json={
            "token": auth_token,
            "order_id": order_id
        })
        assert kot_res.status_code == 200, f"KOT generate failed: {kot_res.text}"
        data = kot_res.json()
        
        assert data.get("success") == True
        kot = data.get("kot", {})
        assert "kot_no" in kot, "KOT should have kot_no"
        assert kot["kot_no"].startswith("KOT-"), f"KOT number should start with KOT-, got {kot['kot_no']}"
        assert len(kot.get("items", [])) == 2, "KOT should have 2 items"
    
    def test_kot_only_new_items(self, auth_token):
        """Test KOT only includes items not yet sent to kitchen"""
        # Create order with items
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "table_no": "T94"
        })
        order_id = create_res.json()["order"]["order_id"]
        
        # Add first batch
        requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [{"item_name": "First Batch Item", "qty": 1, "unit_price": 100}]
        })
        
        # Generate first KOT
        kot1_res = requests.post(f"{BASE_URL}/api/billing/kot/generate", json={
            "token": auth_token,
            "order_id": order_id
        })
        assert kot1_res.status_code == 200
        
        # Add second batch
        requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [{"item_name": "Second Batch Item", "qty": 2, "unit_price": 150}]
        })
        
        # Generate second KOT - should only have new item
        kot2_res = requests.post(f"{BASE_URL}/api/billing/kot/generate", json={
            "token": auth_token,
            "order_id": order_id
        })
        assert kot2_res.status_code == 200
        kot2 = kot2_res.json()["kot"]
        
        assert len(kot2["items"]) == 1, "Second KOT should only have 1 new item"
        assert kot2["items"][0]["item_name"] == "Second Batch Item"
    
    def test_kot_no_new_items_error(self, auth_token):
        """Test KOT generation fails when no new items"""
        # Create order with items
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "table_no": "T93"
        })
        order_id = create_res.json()["order"]["order_id"]
        
        requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [{"item_name": "Single Item", "qty": 1, "unit_price": 100}]
        })
        
        # First KOT
        requests.post(f"{BASE_URL}/api/billing/kot/generate", json={
            "token": auth_token,
            "order_id": order_id
        })
        
        # Second KOT should fail - no new items
        kot2_res = requests.post(f"{BASE_URL}/api/billing/kot/generate", json={
            "token": auth_token,
            "order_id": order_id
        })
        assert kot2_res.status_code == 400, "Should fail when no new items"


class TestBillGeneration:
    """Bill generation and calculation tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_bill_preview_india_exclusive_gst(self, auth_token):
        """Test bill preview with India 5% exclusive GST"""
        # Create order with items
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "table_no": "T92"
        })
        order_id = create_res.json()["order"]["order_id"]
        
        # Add items totaling 1000
        requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [
                {"item_name": "Bill Test Item 1", "qty": 5, "unit_price": 100},  # 500
                {"item_name": "Bill Test Item 2", "qty": 2, "unit_price": 250}   # 500
            ]
        })
        
        # Preview bill
        preview_res = requests.post(f"{BASE_URL}/api/billing/bill/preview", json={
            "token": auth_token,
            "order_id": order_id,
            "center": OPERATIONAL_CENTER
        })
        assert preview_res.status_code == 200, f"Bill preview failed: {preview_res.text}"
        
        calc = preview_res.json()["calculation"]
        
        # For exclusive GST: subtotal = item_total, GST added on top
        assert calc["item_total"] == 1000
        assert calc["subtotal"] == 1000
        assert calc["gst_percentage"] == 5
        assert calc["gst_type"] == "exclusive"
        assert calc["gst_amount"] == 50  # 5% of 1000
        assert calc["grand_total"] == 1050  # 1000 + 50
    
    def test_bill_preview_with_discount_percentage(self, auth_token):
        """Test bill preview with percentage discount"""
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "table_no": "T91"
        })
        order_id = create_res.json()["order"]["order_id"]
        
        requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [{"item_name": "Discount Test", "qty": 10, "unit_price": 100}]  # 1000
        })
        
        # Preview with 10% discount
        preview_res = requests.post(f"{BASE_URL}/api/billing/bill/preview", json={
            "token": auth_token,
            "order_id": order_id,
            "center": OPERATIONAL_CENTER,
            "discount_type": "percentage",
            "discount_value": 10
        })
        
        calc = preview_res.json()["calculation"]
        
        # Subtotal 1000 + GST 50 = 1050, then 10% discount = 105
        assert calc["discount_type"] == "percentage"
        assert calc["discount_value"] == 10
        assert calc["discount_amount"] == 105  # 10% of 1050
        assert calc["grand_total"] == 945  # 1050 - 105
    
    def test_bill_preview_with_fixed_discount(self, auth_token):
        """Test bill preview with fixed amount discount"""
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "table_no": "T90"
        })
        order_id = create_res.json()["order"]["order_id"]
        
        requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [{"item_name": "Fixed Discount Test", "qty": 10, "unit_price": 100}]
        })
        
        # Preview with fixed 100 discount
        preview_res = requests.post(f"{BASE_URL}/api/billing/bill/preview", json={
            "token": auth_token,
            "order_id": order_id,
            "center": OPERATIONAL_CENTER,
            "discount_type": "fixed",
            "discount_value": 100
        })
        
        calc = preview_res.json()["calculation"]
        
        assert calc["discount_type"] == "fixed"
        assert calc["discount_amount"] == 100
        assert calc["grand_total"] == 950  # 1050 - 100
    
    def test_generate_bill(self, auth_token):
        """Test full bill generation"""
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "table_no": "T89"
        })
        order_id = create_res.json()["order"]["order_id"]
        
        requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [{"item_name": "Final Bill Item", "qty": 2, "unit_price": 250}]
        })
        
        # Generate bill
        bill_res = requests.post(f"{BASE_URL}/api/billing/bill/generate", json={
            "token": auth_token,
            "order_id": order_id,
            "payment_mode": "UPI",
            "discount_type": "percentage",
            "discount_value": 5,
            "customer_name": "Test Customer",
            "customer_phone": "9876543210"
        })
        assert bill_res.status_code == 200, f"Bill generate failed: {bill_res.text}"
        
        data = bill_res.json()
        assert data.get("success") == True
        
        bill = data.get("bill", {})
        assert "bill_no" in bill
        assert bill["bill_no"].startswith("BILL-")
        assert bill["payment_mode"] == "UPI"
        assert bill["customer_name"] == "Test Customer"
        assert bill["status"] == "paid"
    
    def test_bill_marks_order_as_billed(self, auth_token):
        """Test that generating bill marks order as billed"""
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "table_no": "T88"
        })
        order_id = create_res.json()["order"]["order_id"]
        
        requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [{"item_name": "Status Test Item", "qty": 1, "unit_price": 100}]
        })
        
        # Generate bill
        requests.post(f"{BASE_URL}/api/billing/bill/generate", json={
            "token": auth_token,
            "order_id": order_id,
            "payment_mode": "Cash"
        })
        
        # Check order status
        order_res = requests.post(f"{BASE_URL}/api/billing/order/get", json={
            "token": auth_token,
            "order_id": order_id
        })
        order = order_res.json()["order"]
        assert order["status"] == "billed"


class TestBillVoid:
    """Bill void tests (admin only)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_void_bill_admin(self, auth_token):
        """Test admin can void a bill"""
        # Create and bill an order
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "table_no": "T87"
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
        
        # Void the bill
        void_res = requests.post(f"{BASE_URL}/api/billing/bill/void", json={
            "token": auth_token,
            "bill_no": bill_no,
            "reason": "Test void"
        })
        assert void_res.status_code == 200, f"Void failed: {void_res.text}"
        assert void_res.json().get("success") == True


class TestBillsListing:
    """Bills listing and reports tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_list_bills_by_center_and_date(self, auth_token):
        """Test listing bills for a center on a date"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        res = requests.post(f"{BASE_URL}/api/billing/bills/list", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "date": today
        })
        assert res.status_code == 200, f"List bills failed: {res.text}"
        
        data = res.json()
        assert "bills" in data
        assert "summary" in data
        
        summary = data["summary"]
        assert "total_sales" in summary
        assert "total_bills" in summary
        assert "void_count" in summary
        assert "by_payment" in summary
    
    def test_daily_report(self, auth_token):
        """Test daily report with item-wise and category-wise breakdown"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        res = requests.post(f"{BASE_URL}/api/billing/bills/daily-report", json={
            "token": auth_token,
            "center": OPERATIONAL_CENTER,
            "date": today
        })
        assert res.status_code == 200, f"Daily report failed: {res.text}"
        
        data = res.json()
        assert "date" in data
        assert "center" in data
        assert "total_bills" in data
        assert "total_revenue" in data
        assert "total_gst" in data
        assert "item_wise" in data
        assert "category_wise" in data


class TestGSTInclusiveCalculation:
    """Test GST inclusive calculation for international centers"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": TEST_MOBILE, "center": TEST_CENTER})
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER})
        return verify_res.json().get("token")
    
    def test_inclusive_gst_calculation(self, auth_token):
        """Test Perth (10% inclusive GST) calculation: subtotal = item_total / 1.10"""
        # Create order for Perth
        create_res = requests.post(f"{BASE_URL}/api/billing/order/create", json={
            "token": auth_token,
            "center": INTERNATIONAL_CENTER,
            "table_no": "P1"
        })
        order_id = create_res.json()["order"]["order_id"]
        
        # Add items totaling $110 (inclusive of GST)
        requests.post(f"{BASE_URL}/api/billing/order/add-items", json={
            "token": auth_token,
            "order_id": order_id,
            "items": [{"item_name": "Perth Item", "qty": 1, "unit_price": 110}]
        })
        
        # Preview bill
        preview_res = requests.post(f"{BASE_URL}/api/billing/bill/preview", json={
            "token": auth_token,
            "order_id": order_id,
            "center": INTERNATIONAL_CENTER
        })
        assert preview_res.status_code == 200
        
        calc = preview_res.json()["calculation"]
        
        # For inclusive GST: subtotal = item_total / 1.10
        # item_total = 110, subtotal = 110/1.10 = 100, GST = 10
        assert calc["item_total"] == 110
        assert calc["gst_type"] == "inclusive"
        assert calc["gst_percentage"] == 10
        assert calc["subtotal"] == 100  # 110 / 1.10
        assert calc["gst_amount"] == 10  # 110 - 100
        assert calc["grand_total"] == 110  # Same as item_total for inclusive


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
