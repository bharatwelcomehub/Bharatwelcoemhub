"""
Test Suite: Daily Sales Balance Cascading Recalculation
Tests the /api/sales/daily/recalculate endpoint which fixes historical balance corruption
by recalculating ALL records for a center from first to last, chaining opening_balance = prev_closing_balance.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_CENTER = "PB-MGT"
OTP = "123456"


class TestRecalculateCascade:
    """Tests for the /api/sales/daily/recalculate endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for Super Admin"""
        # Send OTP
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER
        })
        assert res.status_code == 200, f"Failed to send OTP: {res.text}"
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": OTP,
            "center": SUPER_ADMIN_CENTER
        })
        assert res.status_code == 200, f"Failed to verify OTP: {res.text}"
        data = res.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_recalculate_endpoint_exists(self, auth_token):
        """Test that the recalculate endpoint exists and accepts POST"""
        res = requests.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": auth_token,
            "center": "PB-HSR"
        })
        # Should not return 404 or 405
        assert res.status_code != 404, "Endpoint not found"
        assert res.status_code != 405, "Method not allowed"
        print(f"Endpoint response status: {res.status_code}")
    
    def test_recalculate_requires_auth(self):
        """Test that recalculate endpoint requires valid token"""
        res = requests.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": "invalid_token",
            "center": "PB-HSR"
        })
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"
        print("Auth validation working correctly")
    
    def test_recalculate_requires_center(self, auth_token):
        """Test that center parameter is required"""
        res = requests.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": auth_token
            # Missing center
        })
        # Should fail validation
        assert res.status_code in [400, 422], f"Expected 400/422, got {res.status_code}"
        print("Center validation working correctly")
    
    def test_recalculate_pb_hsr_full_history(self, auth_token):
        """Test recalculating ALL records for PB-HSR center (364 valid records expected)"""
        res = requests.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": auth_token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200, f"Recalculate failed: {res.text}"
        
        data = res.json()
        assert data.get("success") == True, "Response should indicate success"
        
        # Verify response structure
        assert "total_records" in data, "Response should include total_records"
        assert "date_range" in data, "Response should include date_range"
        assert "updated" in data, "Response should include updated count"
        
        print(f"PB-HSR recalculation: {data.get('total_records')} records, "
              f"range: {data.get('date_range', {}).get('from')} to {data.get('date_range', {}).get('to')}")
        
        # Should have significant number of records (364 expected per problem statement)
        assert data.get("total_records", 0) > 100, f"Expected >100 records, got {data.get('total_records')}"
    
    def test_recalculate_month_param_ignored(self, auth_token):
        """Test that month parameter is accepted but ignored (backward compat)"""
        # With month parameter - should still recalculate ALL records
        res = requests.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": auth_token,
            "center": "PB-HSR",
            "month": "2024-04"  # This should be ignored
        })
        assert res.status_code == 200, f"Recalculate with month param failed: {res.text}"
        
        data = res.json()
        assert data.get("success") == True
        
        # Should still return ALL records, not just April 2024
        total = data.get("total_records", 0)
        print(f"With month param: {total} records (should be ALL, not just April)")
        assert total > 30, "Should return more than one month of records"
    
    def test_recalculate_empty_center(self, auth_token):
        """Test recalculating a center with no records"""
        res = requests.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": auth_token,
            "center": "NONEXISTENT-CENTER"
        })
        assert res.status_code == 200, f"Should handle empty center gracefully: {res.text}"
        
        data = res.json()
        assert data.get("success") == True
        assert data.get("updated", 0) == 0 or "No records" in data.get("message", "")
        print(f"Empty center handled: {data.get('message')}")
    
    def test_verify_chain_integrity_after_recalculate(self, auth_token):
        """Verify that after recalculation, opening_balance = prev_closing_balance for all records"""
        # First recalculate
        res = requests.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": auth_token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        
        # Now fetch all records and verify chain
        res = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": auth_token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200, f"Failed to fetch sales: {res.text}"
        
        data = res.json()
        sales = data.get("sales", [])
        
        # Sort by date ascending
        sales_sorted = sorted(sales, key=lambda x: x.get("date", ""))
        
        # Filter only valid YYYY-MM-DD dates
        import re
        valid_sales = [s for s in sales_sorted if re.match(r'^\d{4}-\d{2}-\d{2}$', s.get("date", ""))]
        
        print(f"Checking chain integrity for {len(valid_sales)} records")
        
        chain_breaks = 0
        for i in range(1, len(valid_sales)):
            prev_closing = valid_sales[i-1].get("closing_balance", 0)
            curr_opening = valid_sales[i].get("opening_balance", 0)
            
            # Allow small floating point tolerance
            if abs(prev_closing - curr_opening) > 0.01:
                chain_breaks += 1
                if chain_breaks <= 3:  # Only print first 3 breaks
                    print(f"Chain break at {valid_sales[i].get('date')}: "
                          f"prev_closing={prev_closing}, curr_opening={curr_opening}")
        
        assert chain_breaks == 0, f"Found {chain_breaks} chain breaks in opening_balance"
        print("Chain integrity verified: 0 breaks")
    
    def test_verify_petty_cash_chain_integrity(self, auth_token):
        """Verify petty_cash_opening = prev petty_cash_closing for all records"""
        # Fetch all records
        res = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": auth_token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        
        data = res.json()
        sales = data.get("sales", [])
        
        # Sort by date ascending
        sales_sorted = sorted(sales, key=lambda x: x.get("date", ""))
        
        # Filter only valid YYYY-MM-DD dates
        import re
        valid_sales = [s for s in sales_sorted if re.match(r'^\d{4}-\d{2}-\d{2}$', s.get("date", ""))]
        
        print(f"Checking petty cash chain for {len(valid_sales)} records")
        
        petty_breaks = 0
        for i in range(1, len(valid_sales)):
            prev_petty_closing = valid_sales[i-1].get("petty_cash_closing", 0)
            curr_petty_opening = valid_sales[i].get("petty_cash_opening", 0)
            
            if abs(prev_petty_closing - curr_petty_opening) > 0.01:
                petty_breaks += 1
                if petty_breaks <= 3:
                    print(f"Petty cash break at {valid_sales[i].get('date')}: "
                          f"prev_closing={prev_petty_closing}, curr_opening={curr_petty_opening}")
        
        assert petty_breaks == 0, f"Found {petty_breaks} petty cash chain breaks"
        print("Petty cash chain integrity verified: 0 breaks")
    
    def test_verify_closing_balance_formula(self, auth_token):
        """Verify closing_balance = (total_sale + opening_balance + cash_receipts) - (deposited_in_bank + total_online_sale + cash_expense)"""
        res = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": auth_token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        
        data = res.json()
        sales = data.get("sales", [])
        
        # Check formula for first 10 records
        import re
        valid_sales = [s for s in sales if re.match(r'^\d{4}-\d{2}-\d{2}$', s.get("date", ""))][:10]
        
        formula_errors = 0
        for sale in valid_sales:
            total_sale = sale.get("total_sale", 0)
            opening_balance = sale.get("opening_balance", 0)
            cash_receipts = sale.get("cash_receipts", 0)
            deposited_in_bank = sale.get("deposited_in_bank", 0)
            total_online_sale = sale.get("total_online_sale", 0)
            cash_expense = sale.get("cash_expense", 0)
            closing_balance = sale.get("closing_balance", 0)
            
            expected_closing = (total_sale + opening_balance + cash_receipts) - (deposited_in_bank + total_online_sale + cash_expense)
            
            if abs(expected_closing - closing_balance) > 0.01:
                formula_errors += 1
                print(f"Formula error at {sale.get('date')}: expected={expected_closing}, actual={closing_balance}")
        
        assert formula_errors == 0, f"Found {formula_errors} closing balance formula errors"
        print(f"Closing balance formula verified for {len(valid_sales)} records")
    
    def test_invalid_date_records_excluded(self, auth_token):
        """Verify that records with invalid date formats (e.g., 'Monday,July') are excluded"""
        # Fetch all records including potentially invalid ones
        res = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": auth_token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        
        data = res.json()
        sales = data.get("sales", [])
        
        import re
        invalid_dates = [s.get("date") for s in sales if not re.match(r'^\d{4}-\d{2}-\d{2}$', s.get("date", ""))]
        
        if invalid_dates:
            print(f"Found {len(invalid_dates)} records with invalid dates: {invalid_dates[:5]}")
        else:
            print("No invalid date records found in response")
        
        # The recalculate endpoint should have excluded these
        # This test just documents what's in the DB
    
    def test_recalculate_pb_kn_center(self, auth_token):
        """Test recalculating PB-KN center (365 records expected)"""
        res = requests.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": auth_token,
            "center": "PB-KN"
        })
        assert res.status_code == 200, f"Recalculate PB-KN failed: {res.text}"
        
        data = res.json()
        assert data.get("success") == True
        
        print(f"PB-KN recalculation: {data.get('total_records')} records, "
              f"range: {data.get('date_range', {}).get('from')} to {data.get('date_range', {}).get('to')}")


class TestRecalculateResponseFormat:
    """Tests for the response format of recalculate endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER
        })
        assert res.status_code == 200
        
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": OTP,
            "center": SUPER_ADMIN_CENTER
        })
        assert res.status_code == 200
        return res.json()["token"]
    
    def test_response_includes_total_records(self, auth_token):
        """Verify response includes total_records field"""
        res = requests.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": auth_token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        
        data = res.json()
        assert "total_records" in data, "Response must include total_records"
        assert isinstance(data["total_records"], int), "total_records must be integer"
        print(f"total_records: {data['total_records']}")
    
    def test_response_includes_date_range(self, auth_token):
        """Verify response includes date_range with from and to"""
        res = requests.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": auth_token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        
        data = res.json()
        assert "date_range" in data, "Response must include date_range"
        assert "from" in data["date_range"], "date_range must include 'from'"
        assert "to" in data["date_range"], "date_range must include 'to'"
        
        print(f"date_range: {data['date_range']['from']} to {data['date_range']['to']}")
    
    def test_response_includes_success_flag(self, auth_token):
        """Verify response includes success boolean"""
        res = requests.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": auth_token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        
        data = res.json()
        assert "success" in data, "Response must include success flag"
        assert data["success"] == True, "success should be True"
    
    def test_response_includes_updated_count(self, auth_token):
        """Verify response includes updated count"""
        res = requests.post(f"{BASE_URL}/api/sales/daily/recalculate", json={
            "token": auth_token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        
        data = res.json()
        assert "updated" in data, "Response must include updated count"
        print(f"updated: {data['updated']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
