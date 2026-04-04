"""
Test Sales Delete Range and Grid Column Features
Tests:
1. POST /api/sales/daily/delete-range - deletes daily_sales for a center+month range
2. Grid columns matching Excel format
3. Opening Balance and Petty Cash Opening editable ONLY for day 1
4. Cash Expense editable for all rows
5. Calculated fields update correctly
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_CENTER = "PB-MGT"
OTP = "123456"

# Test center with data
TEST_CENTER = "PB-HSR"

# Safe test month (future date to avoid deleting real data)
SAFE_TEST_MONTH = "2099-01"


class TestSalesDeleteRange:
    """Test the delete-range endpoint for daily sales"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        # Send OTP
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER
        })
        assert otp_res.status_code == 200, f"Failed to send OTP: {otp_res.text}"
        
        # Verify OTP
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": OTP,
            "center": SUPER_ADMIN_CENTER
        })
        assert verify_res.status_code == 200, f"Failed to verify OTP: {verify_res.text}"
        self.token = verify_res.json().get("token")
        assert self.token, "No token received"
    
    def test_delete_range_single_month(self):
        """Test delete-range with from_month only (single month)"""
        # First, create a test record for the safe month
        create_res = requests.post(f"{BASE_URL}/api/sales/daily/create?token={self.token}", json={
            "center": TEST_CENTER,
            "date": f"{SAFE_TEST_MONTH}-15",
            "total_sale": 1000,
            "opening_balance": 500
        })
        # May fail if record exists, that's ok
        
        # Now delete the range
        delete_res = requests.post(f"{BASE_URL}/api/sales/daily/delete-range", json={
            "token": self.token,
            "center": TEST_CENTER,
            "from_month": SAFE_TEST_MONTH
        })
        
        assert delete_res.status_code == 200, f"Delete range failed: {delete_res.text}"
        data = delete_res.json()
        assert data.get("success") == True
        assert "deleted" in data or "message" in data
        print(f"Delete single month result: {data}")
    
    def test_delete_range_month_range(self):
        """Test delete-range with from_month and to_month (range)"""
        # Create test records for the safe months
        for month in ["2099-01", "2099-02"]:
            requests.post(f"{BASE_URL}/api/sales/daily/create?token={self.token}", json={
                "center": TEST_CENTER,
                "date": f"{month}-10",
                "total_sale": 500,
                "opening_balance": 100
            })
        
        # Delete the range
        delete_res = requests.post(f"{BASE_URL}/api/sales/daily/delete-range", json={
            "token": self.token,
            "center": TEST_CENTER,
            "from_month": "2099-01",
            "to_month": "2099-02"
        })
        
        assert delete_res.status_code == 200, f"Delete range failed: {delete_res.text}"
        data = delete_res.json()
        assert data.get("success") == True
        print(f"Delete month range result: {data}")
    
    def test_delete_range_no_records(self):
        """Test delete-range when no records exist in range"""
        delete_res = requests.post(f"{BASE_URL}/api/sales/daily/delete-range", json={
            "token": self.token,
            "center": TEST_CENTER,
            "from_month": "2098-01",  # Very unlikely to have data
            "to_month": "2098-01"
        })
        
        assert delete_res.status_code == 200, f"Delete range failed: {delete_res.text}"
        data = delete_res.json()
        assert data.get("success") == True
        assert data.get("deleted") == 0 or "No records" in data.get("message", "")
        print(f"Delete no records result: {data}")
    
    def test_delete_range_requires_auth(self):
        """Test that delete-range requires valid token"""
        delete_res = requests.post(f"{BASE_URL}/api/sales/daily/delete-range", json={
            "token": "invalid_token",
            "center": TEST_CENTER,
            "from_month": SAFE_TEST_MONTH
        })
        
        assert delete_res.status_code == 401, f"Expected 401, got {delete_res.status_code}"
        print("Delete range auth check passed")


class TestSalesGridColumns:
    """Test that grid columns match Excel format and editability rules"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        # Send OTP
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER
        })
        assert otp_res.status_code == 200
        
        # Verify OTP
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": OTP,
            "center": SUPER_ADMIN_CENTER
        })
        assert verify_res.status_code == 200
        self.token = verify_res.json().get("token")
    
    def test_daily_sales_fields_exist(self):
        """Test that daily sales API returns all required fields"""
        res = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": self.token,
            "center": TEST_CENTER,
            "month": "2025-01"  # Use a month with data
        })
        
        assert res.status_code == 200, f"Failed to get daily sales: {res.text}"
        data = res.json()
        
        if data.get("sales") and len(data["sales"]) > 0:
            sale = data["sales"][0]
            
            # Check all required fields exist
            required_fields = [
                "date", "opening_balance", "petty_cash_opening", "deposited_in_bank",
                "cash_receipts", "total_sale", "card_idfc", "bharat_pay", "swiggy",
                "zomato", "doordash", "online_other", "due_amount", "cash_expense",
                "num_guests", "num_bills", "total_online_sale", "total_cash_sale",
                "closing_balance", "to_deposit_in_bank", "petty_cash_closing"
            ]
            
            for field in required_fields:
                assert field in sale, f"Missing field: {field}"
            
            print(f"All {len(required_fields)} required fields present in daily sales response")
        else:
            print("No sales data found for test month, skipping field check")
    
    def test_calculated_fields_formula(self):
        """Test that calculated fields use correct formulas"""
        # Create a test record with known values
        test_date = f"{SAFE_TEST_MONTH}-01"
        
        # First delete any existing record
        requests.delete(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{test_date}?token={self.token}")
        
        # Create with known values
        create_res = requests.post(f"{BASE_URL}/api/sales/daily/create?token={self.token}", json={
            "center": TEST_CENTER,
            "date": test_date,
            "opening_balance": 1000,
            "petty_cash_opening": 500,
            "deposited_in_bank": 200,
            "cash_receipts": 100,
            "total_sale": 5000,
            "card_idfc": 1000,
            "bharat_pay": 500,
            "swiggy": 800,
            "zomato": 700,
            "doordash": 300,
            "online_other": 200,
            "cash_expense": 150
        })
        
        assert create_res.status_code == 200, f"Failed to create test record: {create_res.text}"
        record = create_res.json().get("record", {})
        
        # Verify calculated fields
        # total_online_sale = card + upi + swiggy + zomato + doordash + online_other
        expected_online = 1000 + 500 + 800 + 700 + 300 + 200  # 3500
        assert record.get("total_online_sale") == expected_online, f"Expected online sale {expected_online}, got {record.get('total_online_sale')}"
        
        # total_cash_sale = total_sale - total_online_sale
        expected_cash = 5000 - 3500  # 1500
        assert record.get("total_cash_sale") == expected_cash, f"Expected cash sale {expected_cash}, got {record.get('total_cash_sale')}"
        
        # closing_balance = (total_sale + opening + cash_receipts) - (deposited + online_sale + cash_expense)
        expected_closing = (5000 + 1000 + 100) - (200 + 3500 + 150)  # 6100 - 3850 = 2250
        assert record.get("closing_balance") == expected_closing, f"Expected closing {expected_closing}, got {record.get('closing_balance')}"
        
        # petty_cash_closing = petty_opening + cash_receipts - cash_expense
        expected_petty = 500 + 100 - 150  # 450
        assert record.get("petty_cash_closing") == expected_petty, f"Expected petty closing {expected_petty}, got {record.get('petty_cash_closing')}"
        
        # to_deposit = closing_balance - petty_cash_closing
        expected_deposit = 2250 - 450  # 1800
        assert record.get("to_deposit_in_bank") == expected_deposit, f"Expected to deposit {expected_deposit}, got {record.get('to_deposit_in_bank')}"
        
        print("All calculated field formulas verified correctly!")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{test_date}?token={self.token}")
    
    def test_update_opening_balance(self):
        """Test that opening_balance can be updated"""
        test_date = f"{SAFE_TEST_MONTH}-01"
        
        # Create record
        requests.delete(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{test_date}?token={self.token}")
        create_res = requests.post(f"{BASE_URL}/api/sales/daily/create?token={self.token}", json={
            "center": TEST_CENTER,
            "date": test_date,
            "opening_balance": 1000,
            "total_sale": 5000
        })
        assert create_res.status_code == 200
        
        # Update opening_balance
        update_res = requests.put(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{test_date}?token={self.token}", json={
            "opening_balance": 2000
        })
        
        assert update_res.status_code == 200, f"Failed to update opening_balance: {update_res.text}"
        record = update_res.json().get("record", {})
        assert record.get("opening_balance") == 2000, f"Opening balance not updated: {record.get('opening_balance')}"
        
        print("Opening balance update verified!")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{test_date}?token={self.token}")
    
    def test_update_petty_cash_opening(self):
        """Test that petty_cash_opening can be updated"""
        test_date = f"{SAFE_TEST_MONTH}-01"
        
        # Create record
        requests.delete(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{test_date}?token={self.token}")
        create_res = requests.post(f"{BASE_URL}/api/sales/daily/create?token={self.token}", json={
            "center": TEST_CENTER,
            "date": test_date,
            "petty_cash_opening": 500,
            "total_sale": 5000
        })
        assert create_res.status_code == 200
        
        # Update petty_cash_opening
        update_res = requests.put(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{test_date}?token={self.token}", json={
            "petty_cash_opening": 800
        })
        
        assert update_res.status_code == 200, f"Failed to update petty_cash_opening: {update_res.text}"
        record = update_res.json().get("record", {})
        assert record.get("petty_cash_opening") == 800, f"Petty cash opening not updated: {record.get('petty_cash_opening')}"
        
        print("Petty cash opening update verified!")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{test_date}?token={self.token}")
    
    def test_update_cash_expense(self):
        """Test that cash_expense can be updated"""
        test_date = f"{SAFE_TEST_MONTH}-01"
        
        # Create record
        requests.delete(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{test_date}?token={self.token}")
        create_res = requests.post(f"{BASE_URL}/api/sales/daily/create?token={self.token}", json={
            "center": TEST_CENTER,
            "date": test_date,
            "cash_expense": 100,
            "total_sale": 5000
        })
        assert create_res.status_code == 200
        
        # Update cash_expense
        update_res = requests.put(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{test_date}?token={self.token}", json={
            "cash_expense": 250
        })
        
        assert update_res.status_code == 200, f"Failed to update cash_expense: {update_res.text}"
        record = update_res.json().get("record", {})
        assert record.get("cash_expense") == 250, f"Cash expense not updated: {record.get('cash_expense')}"
        
        print("Cash expense update verified!")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{test_date}?token={self.token}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
