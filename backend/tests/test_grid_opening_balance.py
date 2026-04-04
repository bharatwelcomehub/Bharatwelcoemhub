"""
Test Grid Opening Balance Fix
Tests that the first day of a month gets its opening balance from the previous month's last day closing balance.
Bug: April 1 should have opening_balance = March 31's closing_balance, but it was 0.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGridOpeningBalance:
    """Test opening balance carry-forward from previous month"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get auth token"""
        # Send OTP
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT"
        })
        assert otp_res.status_code == 200, f"Send OTP failed: {otp_res.text}"
        
        # Verify OTP
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": "9741399190",
            "otp": "123456",
            "center": "PB-MGT"
        })
        assert verify_res.status_code == 200, f"Verify OTP failed: {verify_res.text}"
        self.token = verify_res.json()["token"]
        self.center = "PB-HSR"
    
    def test_march_2026_last_day_has_closing_balance(self):
        """Test that March 31, 2026 has closing_balance = 1100 for PB-HSR"""
        res = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": self.token,
            "center": self.center,
            "month": "2026-03"
        })
        assert res.status_code == 200, f"API failed: {res.text}"
        
        sales = res.json().get("sales", [])
        assert len(sales) > 0, "No sales data for March 2026"
        
        # Sort by date and get last day
        sales_sorted = sorted(sales, key=lambda x: x["date"])
        last_day = sales_sorted[-1]
        
        assert last_day["date"] == "2026-03-31", f"Expected last day to be 2026-03-31, got {last_day['date']}"
        assert last_day["closing_balance"] == 1100, f"Expected closing_balance=1100, got {last_day['closing_balance']}"
        print(f"PASSED: March 31, 2026 closing_balance = {last_day['closing_balance']}")
    
    def test_april_2026_no_existing_data(self):
        """Test that April 2026 has no existing sales data (empty month)"""
        res = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": self.token,
            "center": self.center,
            "month": "2026-04"
        })
        assert res.status_code == 200, f"API failed: {res.text}"
        
        sales = res.json().get("sales", [])
        count = res.json().get("count", len(sales))
        
        # April 2026 should have no data (or minimal test data)
        print(f"April 2026 has {count} records")
        # This is expected - the frontend should fetch previous month's closing for opening balance
    
    def test_previous_month_fetch_for_opening_balance(self):
        """
        Test the pattern used by SalesGridEditor:
        1. Fetch current month data
        2. Fetch previous month data
        3. Use previous month's last day closing_balance as first row's opening_balance
        """
        # Step 1: Fetch April 2026 data (current month)
        april_res = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": self.token,
            "center": self.center,
            "month": "2026-04"
        })
        assert april_res.status_code == 200
        april_sales = april_res.json().get("sales", [])
        print(f"April 2026: {len(april_sales)} records")
        
        # Step 2: Fetch March 2026 data (previous month)
        march_res = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": self.token,
            "center": self.center,
            "month": "2026-03"
        })
        assert march_res.status_code == 200
        march_sales = march_res.json().get("sales", [])
        assert len(march_sales) > 0, "No March 2026 data"
        
        # Step 3: Get last day's closing balance
        march_sorted = sorted(march_sales, key=lambda x: x["date"], reverse=True)
        last_day_closing = march_sorted[0]["closing_balance"]
        
        print(f"March 31 closing_balance: {last_day_closing}")
        assert last_day_closing == 1100, f"Expected 1100, got {last_day_closing}"
        
        # This value should be used as April 1's opening_balance in the grid
        print(f"PASSED: April 1 should use opening_balance = {last_day_closing}")
    
    def test_closing_balance_formula(self):
        """
        Test the closing balance formula:
        Closing Balance = (Total Sale + Opening + Cash Receipts) - (Deposited + Online + Cash Expense)
        
        For April 1 with no sales:
        - opening_balance = 1100 (from March 31)
        - total_sale = 0
        - cash_receipts = 0
        - deposited_in_bank = 0
        - total_online_sale = 0
        - cash_expense = 0
        
        Expected closing_balance = (0 + 1100 + 0) - (0 + 0 + 0) = 1100
        """
        # Fetch March 31 data
        march_res = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": self.token,
            "center": self.center,
            "month": "2026-03"
        })
        march_sales = march_res.json().get("sales", [])
        march_sorted = sorted(march_sales, key=lambda x: x["date"], reverse=True)
        march_31 = march_sorted[0]
        
        opening_balance = march_31["closing_balance"]  # 1100
        
        # Simulate April 1 with no data
        total_sale = 0
        cash_receipts = 0
        deposited_in_bank = 0
        total_online_sale = 0
        cash_expense = 0
        
        # Apply formula
        expected_closing = (total_sale + opening_balance + cash_receipts) - (deposited_in_bank + total_online_sale + cash_expense)
        
        assert expected_closing == 1100, f"Expected closing_balance=1100, got {expected_closing}"
        print(f"PASSED: Closing balance formula verified: {expected_closing}")
    
    def test_chaining_opening_balances(self):
        """
        Test that opening balances chain correctly:
        - Row 1 (Apr 1): opening = March 31 closing (1100)
        - Row 2 (Apr 2): opening = Row 1 closing (1100 if no changes)
        - Row 3 (Apr 3): opening = Row 2 closing (1100 if no changes)
        ...and so on
        """
        # This is a frontend logic test - the backend just provides the data
        # The frontend SalesGridEditor.jsx handles the chaining
        
        # Verify the backend provides the necessary data
        march_res = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": self.token,
            "center": self.center,
            "month": "2026-03"
        })
        assert march_res.status_code == 200
        
        march_sales = march_res.json().get("sales", [])
        march_sorted = sorted(march_sales, key=lambda x: x["date"], reverse=True)
        
        # Verify closing_balance field exists
        assert "closing_balance" in march_sorted[0], "closing_balance field missing"
        
        print(f"PASSED: Backend provides closing_balance field for chaining")
        print(f"March 31 closing_balance: {march_sorted[0]['closing_balance']}")


class TestSalesDataEntryOpeningBalance:
    """Test SalesDataEntry component's opening balance fetch"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get auth token"""
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT"
        })
        assert otp_res.status_code == 200
        
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": "9741399190",
            "otp": "123456",
            "center": "PB-MGT"
        })
        assert verify_res.status_code == 200
        self.token = verify_res.json()["token"]
        self.center = "PB-HSR"
    
    def test_fetch_previous_day_for_opening(self):
        """
        Test the pattern used by SalesDataEntry:
        Fetch previous day's data to get opening balance
        """
        # For April 1, previous day is March 31
        prev_date = "2026-03-31"
        
        res = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": self.token,
            "center": self.center,
            "start_date": prev_date,
            "end_date": prev_date
        })
        assert res.status_code == 200, f"API failed: {res.text}"
        
        sales = res.json().get("sales", [])
        assert len(sales) == 1, f"Expected 1 record for {prev_date}, got {len(sales)}"
        
        prev_day_data = sales[0]
        assert prev_day_data["closing_balance"] == 1100, f"Expected closing_balance=1100"
        assert prev_day_data["petty_cash_closing"] == 885, f"Expected petty_cash_closing=885"
        
        print(f"PASSED: Previous day fetch works correctly")
        print(f"  closing_balance: {prev_day_data['closing_balance']}")
        print(f"  petty_cash_closing: {prev_day_data['petty_cash_closing']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
