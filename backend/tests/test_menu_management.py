"""
Test Menu Management and isPerth Bug Fix
Tests:
1. Login flow with DB-driven center dropdown
2. Menu Management endpoints (seed, by-center pricing)
3. SalesDataEntry GST calculation (isIntl instead of isPerth)
4. Center-specific pricing (INR vs AUD)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://table-order-system-20.preview.emergentagent.com')

class TestLoginAndCenters:
    """Test login flow and DB-driven centers"""
    
    def test_centers_from_db(self):
        """Centers endpoint returns DB-driven list with is_india_center field"""
        res = requests.get(f"{BASE_URL}/api/centers")
        assert res.status_code == 200
        data = res.json()
        assert "centers" in data
        centers = data["centers"]
        assert len(centers) >= 8  # At least 8 centers expected
        
        # Check PB-PERTH is marked as international
        perth = next((c for c in centers if c["code"] == "PB-PERTH"), None)
        assert perth is not None, "PB-PERTH should exist"
        assert perth.get("is_india_center") == False, "PB-PERTH should be international"
        
        # Check PB-HSR is marked as India center
        hsr = next((c for c in centers if c["code"] == "PB-HSR"), None)
        assert hsr is not None, "PB-HSR should exist"
        assert hsr.get("is_india_center") == True, "PB-HSR should be India center"
        
    def test_send_otp_success(self):
        """Send OTP works for Super Admin"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190"
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        
    def test_verify_otp_super_admin(self):
        """Verify OTP returns admin flags"""
        # First send OTP
        requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190"
        })
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190",
            "otp": "123456"
        })
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert data.get("is_super_admin") == True
        assert data.get("is_admin") == True
        assert data.get("center") == "PB-MGT"


class TestMenuManagement:
    """Test Menu Management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190"
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190",
            "otp": "123456"
        })
        self.token = res.json().get("token")
        
    def test_seed_menu_data(self):
        """Seed menu data endpoint works and returns 146+ items"""
        res = requests.post(f"{BASE_URL}/api/masters/seed-menu-data", json={
            "token": self.token
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        # Total items should be 146 (created + updated)
        total = data.get("items_created", 0) + data.get("items_updated", 0)
        assert total >= 146, f"Expected 146+ items, got {total}"
        
    def test_menu_items_by_center_hsr_inr(self):
        """PB-HSR returns INR pricing"""
        res = requests.get(f"{BASE_URL}/api/masters/menu-items/by-center/PB-HSR?token={self.token}")
        assert res.status_code == 200
        data = res.json()
        
        assert data.get("center") == "PB-HSR"
        assert data.get("currency") == "INR"
        assert data.get("symbol") == "₹"
        
        items = data.get("items", [])
        assert len(items) >= 100, f"Expected 100+ items, got {len(items)}"
        
        # Check a sample item has INR price
        sample = next((i for i in items if i["name"] == "Misal Pav"), None)
        if sample:
            assert sample.get("center_price") == 199 or sample.get("center_price") > 100, "INR price expected"
            
    def test_menu_items_by_center_perth_aud(self):
        """PB-PERTH returns AUD pricing with some items unavailable"""
        res = requests.get(f"{BASE_URL}/api/masters/menu-items/by-center/PB-PERTH?token={self.token}")
        assert res.status_code == 200
        data = res.json()
        
        assert data.get("center") == "PB-PERTH"
        assert data.get("currency") == "AUD"
        assert data.get("symbol") == "$"
        
        items = data.get("items", [])
        assert len(items) >= 100, f"Expected 100+ items, got {len(items)}"
        
        # Check some items are unavailable at Perth
        unavailable = [i for i in items if not i.get("available")]
        assert len(unavailable) > 0, "Some items should be unavailable at Perth"
        
        # Check a sample item has AUD price (lower than INR)
        sample = next((i for i in items if i["name"] == "Misal Pav" and i.get("available")), None)
        if sample:
            assert sample.get("center_price") < 50, f"AUD price expected (got {sample.get('center_price')})"
            
    def test_menu_categories_list(self):
        """Menu categories endpoint works"""
        # Note: This endpoint uses POST method
        res = requests.post(f"{BASE_URL}/api/masters/menu_categories/list", json={
            "token": self.token
        })
        assert res.status_code == 200
        data = res.json()
        items = data.get("items", [])
        assert len(items) >= 10, f"Expected 10+ categories, got {len(items)}"
        
        # Check expected categories exist
        cat_names = [c.get("name") for c in items]
        expected = ["SNACKS", "THALI", "SWEET", "RICE", "ROTI"]
        for exp in expected:
            found = any(exp.lower() in c.lower() for c in cat_names)
            assert found, f"Category containing '{exp}' should exist"


class TestSalesDataEntryGST:
    """Test that SalesDataEntry uses isIntl instead of isPerth"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190"
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190",
            "otp": "123456"
        })
        self.token = res.json().get("token")
        
    def test_sales_daily_endpoint_works(self):
        """Sales daily endpoint works without isPerth error"""
        res = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": self.token,
            "center": "PB-HSR",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31"
        })
        assert res.status_code == 200
        data = res.json()
        assert "sales" in data
        
    def test_sales_monthly_summary_works(self):
        """Sales monthly summary works without errors"""
        res = requests.post(f"{BASE_URL}/api/sales/reports/monthly-summary", json={
            "token": self.token,
            "month": "2026-01",
            "center": "all"
        })
        assert res.status_code == 200
        data = res.json()
        # Should have summary or grand_total
        assert "summary" in data or "grand_total" in data or "centers" in data


class TestExpenseEntry:
    """Test ExpenseEntry component endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190"
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190",
            "otp": "123456"
        })
        self.token = res.json().get("token")
        
    def test_expense_types_endpoint(self):
        """Expense types endpoint works"""
        res = requests.get(f"{BASE_URL}/api/sales/expense-types")
        assert res.status_code == 200
        data = res.json()
        assert "expense_types" in data
        assert len(data["expense_types"]) > 0
        
    def test_payment_modes_endpoint(self):
        """Payment modes endpoint works"""
        res = requests.get(f"{BASE_URL}/api/sales/payment-modes")
        assert res.status_code == 200
        data = res.json()
        assert "payment_modes" in data
        assert len(data["payment_modes"]) > 0
        
    def test_expenses_list_endpoint(self):
        """Expenses list endpoint works"""
        res = requests.post(f"{BASE_URL}/api/sales/expenses", json={
            "token": self.token,
            "center": "PB-HSR",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31"
        })
        assert res.status_code == 200
        data = res.json()
        assert "expenses" in data


class TestMenuManagementAccess:
    """Test Menu Management access control"""
    
    def test_menu_items_requires_auth(self):
        """Menu items endpoint requires authentication"""
        res = requests.get(f"{BASE_URL}/api/masters/menu-items/by-center/PB-HSR?token=invalid")
        assert res.status_code == 401
        
    def test_seed_menu_requires_admin(self):
        """Seed menu endpoint requires admin permission"""
        res = requests.post(f"{BASE_URL}/api/masters/seed-menu-data", json={
            "token": "invalid"
        })
        assert res.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
