"""
Test suite for POST /api/sales/daily/recalculate endpoint
Tests the opening/closing balance chaining logic for daily sales records.

Formulas being tested:
- Cash Sale = Total Sale - (Card + UPI + Swiggy + Zomato + Doordash + Due/Other)
- Closing Balance = (Total Sale + Opening Balance + Cash Receipts) - (Deposited in Bank + Total Online Sale + Cash Expense)
- Petty Cash Closing = Petty Cash Opening + Cash Receipts - Cash Expense
- Opening Balance = Previous day's Closing Balance
- Petty Cash Opening = Previous day's Petty Cash Closing
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"
TEST_CENTER = "PB-MGT"
TEST_MONTH = "2026-01"  # Use a test month


class TestRecalculateBalances:
    """Test the recalculate endpoint for opening/closing balance chaining"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Get auth token
        otp_res = self.session.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        assert otp_res.status_code == 200, f"Failed to send OTP: {otp_res.text}"
        
        verify_res = self.session.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP,
            "center": TEST_CENTER
        })
        assert verify_res.status_code == 200, f"Failed to verify OTP: {verify_res.text}"
        self.token = verify_res.json().get("token")
        assert self.token, "No token received"
        print(f"Auth token obtained: {self.token[:20]}...")
    
    def test_recalculate_endpoint_exists(self):
        """Test that the recalculate endpoint exists and accepts requests"""
        response = self.session.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": self.token,
            "center": TEST_CENTER,
            "month": TEST_MONTH
        })
        
        # Should return 200 even if no records exist
        assert response.status_code == 200, f"Endpoint failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "success" in data, f"Response missing 'success' field: {data}"
        print(f"Recalculate response: {data}")
    
    def test_recalculate_chains_opening_balance(self):
        """Test that recalculate chains opening_balance = previous day's closing_balance
        
        Note: Recalculate chains from previous month's last record, so day 1's opening
        may change. We verify that day 2's opening = day 1's closing AFTER recalculate.
        """
        # First, create test data for day 1 and day 2
        day1_date = f"{TEST_MONTH}-15"
        day2_date = f"{TEST_MONTH}-16"
        
        # Create day 1 record with known values
        day1_payload = {
            "center": TEST_CENTER,
            "date": day1_date,
            "opening_balance": 1000,
            "petty_cash_opening": 500,
            "total_sale": 5000,
            "card_idfc": 1000,
            "bharat_pay": 500,
            "swiggy": 300,
            "zomato": 200,
            "doordash": 0,
            "online_other": 0,
            "due_amount": 0,
            "deposited_in_bank": 0,
            "cash_receipts": 200,
            "cash_expense": 100,
            "num_guests": 50,
            "num_bills": 30
        }
        
        # Try to create or update day 1
        create_res = self.session.post(f"{BASE_URL}/api/sales/daily/create?token={self.token}", json=day1_payload)
        if create_res.status_code == 400 and "already exists" in create_res.text:
            # Update existing record
            update_res = self.session.put(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{day1_date}?token={self.token}", json=day1_payload)
            assert update_res.status_code == 200, f"Failed to update day 1: {update_res.text}"
        else:
            assert create_res.status_code == 200, f"Failed to create day 1: {create_res.text}"
        
        # Create day 2 record with WRONG opening balance (to test recalculate fixes it)
        day2_payload = {
            "center": TEST_CENTER,
            "date": day2_date,
            "opening_balance": 9999,  # Wrong value - should be day1's closing
            "petty_cash_opening": 9999,  # Wrong value - should be day1's petty_cash_closing
            "total_sale": 6000,
            "card_idfc": 1200,
            "bharat_pay": 600,
            "swiggy": 400,
            "zomato": 300,
            "doordash": 0,
            "online_other": 0,
            "due_amount": 0,
            "deposited_in_bank": 0,
            "cash_receipts": 300,
            "cash_expense": 150,
            "num_guests": 60,
            "num_bills": 35
        }
        
        create_res2 = self.session.post(f"{BASE_URL}/api/sales/daily/create?token={self.token}", json=day2_payload)
        if create_res2.status_code == 400 and "already exists" in create_res2.text:
            update_res2 = self.session.put(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{day2_date}?token={self.token}", json=day2_payload)
            assert update_res2.status_code == 200, f"Failed to update day 2: {update_res2.text}"
        else:
            assert create_res2.status_code == 200, f"Failed to create day 2: {create_res2.text}"
        
        # Now run recalculate
        recalc_res = self.session.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": self.token,
            "center": TEST_CENTER,
            "month": TEST_MONTH
        })
        assert recalc_res.status_code == 200, f"Recalculate failed: {recalc_res.text}"
        recalc_data = recalc_res.json()
        print(f"Recalculate result: {recalc_data}")
        assert recalc_data.get("success") == True, "Recalculate did not succeed"
        assert recalc_data.get("updated", 0) >= 2, "Expected at least 2 records to be updated"
        
        # Fetch BOTH day 1 and day 2 records AFTER recalculate
        fetch_res = self.session.post(f"{BASE_URL}/api/sales/daily", json={
            "token": self.token,
            "center": TEST_CENTER,
            "start_date": day1_date,
            "end_date": day2_date
        })
        assert fetch_res.status_code == 200, f"Failed to fetch records: {fetch_res.text}"
        records = fetch_res.json().get("sales", [])
        assert len(records) >= 2, f"Expected at least 2 records, got {len(records)}"
        
        # Sort by date to ensure correct order
        records_sorted = sorted(records, key=lambda x: x.get("date", ""))
        day1_after = next((r for r in records_sorted if r.get("date") == day1_date), None)
        day2_after = next((r for r in records_sorted if r.get("date") == day2_date), None)
        
        assert day1_after, f"Day 1 record not found after recalculate"
        assert day2_after, f"Day 2 record not found after recalculate"
        
        print(f"Day 1 after recalculate: opening={day1_after.get('opening_balance')}, closing={day1_after.get('closing_balance')}, petty_closing={day1_after.get('petty_cash_closing')}")
        print(f"Day 2 after recalculate: opening={day2_after.get('opening_balance')}, petty_opening={day2_after.get('petty_cash_opening')}")
        
        # Verify chaining: day 2's opening = day 1's closing (AFTER recalculate)
        assert day2_after.get("opening_balance") == day1_after.get("closing_balance"), \
            f"Opening balance not chained: day2.opening={day2_after.get('opening_balance')} != day1.closing={day1_after.get('closing_balance')}"
        
        assert day2_after.get("petty_cash_opening") == day1_after.get("petty_cash_closing"), \
            f"Petty cash opening not chained: day2.petty_opening={day2_after.get('petty_cash_opening')} != day1.petty_closing={day1_after.get('petty_cash_closing')}"
        
        print("SUCCESS: Opening balances correctly chained after recalculate")
    
    def test_closing_balance_formula(self):
        """Test that closing_balance formula is correct:
        Closing Balance = (Total Sale + Opening + Cash Receipts) - (Deposited + Online Sale + Cash Expense)
        """
        test_date = f"{TEST_MONTH}-20"
        
        # Create record with known values
        payload = {
            "center": TEST_CENTER,
            "date": test_date,
            "opening_balance": 1000,
            "petty_cash_opening": 500,
            "total_sale": 10000,
            "card_idfc": 2000,
            "bharat_pay": 1000,
            "swiggy": 500,
            "zomato": 500,
            "doordash": 0,
            "online_other": 0,
            "due_amount": 0,
            "deposited_in_bank": 500,
            "cash_receipts": 300,
            "cash_expense": 200,
            "num_guests": 100,
            "num_bills": 60
        }
        
        # Expected calculations:
        # total_online_sale = 2000 + 1000 + 500 + 500 + 0 + 0 = 4000
        # closing_balance = (10000 + 1000 + 300) - (500 + 4000 + 200) = 11300 - 4700 = 6600
        expected_closing = (10000 + 1000 + 300) - (500 + 4000 + 200)
        
        create_res = self.session.post(f"{BASE_URL}/api/sales/daily/create?token={self.token}", json=payload)
        if create_res.status_code == 400 and "already exists" in create_res.text:
            update_res = self.session.put(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{test_date}?token={self.token}", json=payload)
            assert update_res.status_code == 200, f"Failed to update: {update_res.text}"
            record = update_res.json().get("record", {})
        else:
            assert create_res.status_code == 200, f"Failed to create: {create_res.text}"
            record = create_res.json().get("record", {})
        
        actual_closing = record.get("closing_balance")
        print(f"Closing balance: expected={expected_closing}, actual={actual_closing}")
        
        assert actual_closing == expected_closing, \
            f"Closing balance formula incorrect: expected {expected_closing}, got {actual_closing}"
        
        print("SUCCESS: Closing balance formula is correct")
    
    def test_petty_cash_closing_formula(self):
        """Test that petty_cash_closing formula is correct:
        Petty Cash Closing = Petty Cash Opening + Cash Receipts - Cash Expense
        """
        test_date = f"{TEST_MONTH}-21"
        
        payload = {
            "center": TEST_CENTER,
            "date": test_date,
            "opening_balance": 1000,
            "petty_cash_opening": 500,
            "total_sale": 5000,
            "card_idfc": 1000,
            "bharat_pay": 500,
            "swiggy": 0,
            "zomato": 0,
            "doordash": 0,
            "online_other": 0,
            "due_amount": 0,
            "deposited_in_bank": 0,
            "cash_receipts": 400,
            "cash_expense": 150,
            "num_guests": 50,
            "num_bills": 30
        }
        
        # Expected: petty_cash_closing = 500 + 400 - 150 = 750
        expected_petty_closing = 500 + 400 - 150
        
        create_res = self.session.post(f"{BASE_URL}/api/sales/daily/create?token={self.token}", json=payload)
        if create_res.status_code == 400 and "already exists" in create_res.text:
            update_res = self.session.put(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{test_date}?token={self.token}", json=payload)
            assert update_res.status_code == 200, f"Failed to update: {update_res.text}"
            record = update_res.json().get("record", {})
        else:
            assert create_res.status_code == 200, f"Failed to create: {create_res.text}"
            record = create_res.json().get("record", {})
        
        actual_petty_closing = record.get("petty_cash_closing")
        print(f"Petty cash closing: expected={expected_petty_closing}, actual={actual_petty_closing}")
        
        assert actual_petty_closing == expected_petty_closing, \
            f"Petty cash closing formula incorrect: expected {expected_petty_closing}, got {actual_petty_closing}"
        
        print("SUCCESS: Petty cash closing formula is correct")
    
    def test_cash_sale_formula(self):
        """Test that cash_sale formula is correct:
        Cash Sale = Total Sale - Total Online Sale
        """
        test_date = f"{TEST_MONTH}-22"
        
        payload = {
            "center": TEST_CENTER,
            "date": test_date,
            "opening_balance": 1000,
            "petty_cash_opening": 500,
            "total_sale": 10000,
            "card_idfc": 2000,
            "bharat_pay": 1500,
            "swiggy": 800,
            "zomato": 700,
            "doordash": 500,
            "online_other": 500,
            "due_amount": 0,
            "deposited_in_bank": 0,
            "cash_receipts": 0,
            "cash_expense": 0,
            "num_guests": 100,
            "num_bills": 60
        }
        
        # Expected:
        # total_online_sale = 2000 + 1500 + 800 + 700 + 500 + 500 = 6000
        # total_cash_sale = 10000 - 6000 = 4000
        expected_online = 2000 + 1500 + 800 + 700 + 500 + 500
        expected_cash = 10000 - expected_online
        
        create_res = self.session.post(f"{BASE_URL}/api/sales/daily/create?token={self.token}", json=payload)
        if create_res.status_code == 400 and "already exists" in create_res.text:
            update_res = self.session.put(f"{BASE_URL}/api/sales/daily/{TEST_CENTER}/{test_date}?token={self.token}", json=payload)
            assert update_res.status_code == 200, f"Failed to update: {update_res.text}"
            record = update_res.json().get("record", {})
        else:
            assert create_res.status_code == 200, f"Failed to create: {create_res.text}"
            record = create_res.json().get("record", {})
        
        actual_online = record.get("total_online_sale")
        actual_cash = record.get("total_cash_sale")
        
        print(f"Online sale: expected={expected_online}, actual={actual_online}")
        print(f"Cash sale: expected={expected_cash}, actual={actual_cash}")
        
        assert actual_online == expected_online, \
            f"Total online sale incorrect: expected {expected_online}, got {actual_online}"
        
        assert actual_cash == expected_cash, \
            f"Cash sale formula incorrect: expected {expected_cash}, got {actual_cash}"
        
        print("SUCCESS: Cash sale formula is correct")


class TestRecalculateEdgeCases:
    """Test edge cases for the recalculate endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        otp_res = self.session.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        assert otp_res.status_code == 200
        
        verify_res = self.session.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP,
            "center": TEST_CENTER
        })
        assert verify_res.status_code == 200
        self.token = verify_res.json().get("token")
    
    def test_recalculate_empty_month(self):
        """Test recalculate on a month with no records"""
        response = self.session.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": self.token,
            "center": TEST_CENTER,
            "month": "2020-01"  # Old month with no data
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("updated") == 0
        print(f"Empty month recalculate: {data}")
    
    def test_recalculate_invalid_token(self):
        """Test recalculate with invalid token"""
        response = self.session.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": "invalid_token_12345",
            "center": TEST_CENTER,
            "month": TEST_MONTH
        })
        
        assert response.status_code == 401
        print("Invalid token correctly rejected")
    
    def test_recalculate_missing_center(self):
        """Test recalculate with missing center"""
        response = self.session.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": self.token,
            "month": TEST_MONTH
        })
        
        # Should fail validation
        assert response.status_code in [400, 422]
        print("Missing center correctly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
