"""
Test Working Capital Feature Rewrite - Iteration 57
Tests:
1. POST /api/center-accounts/wc-table - new WC logic: P/L = Sales - (Expenses + Commission)
2. POST /api/center-accounts/wc-topup - manual WC top-up with audit trail
3. POST /api/center-accounts/wc-override - set initial WC value
4. Revenue share status logic (stops at 50% threshold)
5. Top-up correctly increases WC
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"
TEST_CENTER = "PB-MGT"

# Test data for WC testing - use future months to avoid conflicts
TEST_WC_CENTER = "TEST-WC-57"
TEST_MONTH = "2099-01"


class TestWCRewrite:
    """Working Capital Feature Rewrite Tests"""
    
    token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before tests"""
        if TestWCRewrite.token is None:
            # Login to get token
            res = requests.post(f"{BASE_URL}/api/verify_otp", json={
                "mobile": TEST_MOBILE,
                "otp": TEST_OTP,
                "center": TEST_CENTER
            })
            assert res.status_code == 200, f"Login failed: {res.text}"
            data = res.json()
            assert data.get("success") or data.get("token"), f"Login response invalid: {data}"
            TestWCRewrite.token = data.get("token")
        yield
    
    def test_01_wc_table_endpoint_returns_success(self):
        """Test wc-table endpoint returns success with expected fields"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        assert res.status_code == 200, f"wc-table failed: {res.text}"
        data = res.json()
        
        # Check required fields in response
        assert data.get("success") == True, f"Expected success=True, got: {data}"
        assert "rows" in data, "Missing 'rows' in response"
        assert "initial_wc" in data, "Missing 'initial_wc' in response"
        assert "current_wc" in data, "Missing 'current_wc' in response"
        assert "revenue_share_status" in data, "Missing 'revenue_share_status' in response"
        assert "last_topup" in data, "Missing 'last_topup' in response"
        assert "topup_log" in data, "Missing 'topup_log' in response"
        
        print(f"WC Table response: initial_wc={data['initial_wc']}, current_wc={data['current_wc']}, status={data['revenue_share_status']}")
    
    def test_02_wc_table_row_structure(self):
        """Test wc-table rows have correct structure with P/L formula"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        assert res.status_code == 200
        data = res.json()
        
        if data.get("rows") and len(data["rows"]) > 0:
            row = data["rows"][0]
            # Check row has all required fields
            required_fields = ["month", "sale", "expenses", "commission", "pnl", 
                              "opening_wc", "topup", "closing_wc", "rev_share_status"]
            for field in required_fields:
                assert field in row, f"Missing field '{field}' in row: {row}"
            
            # Verify P/L formula: P/L = Sale - (Expenses + Commission)
            expected_pnl = round(row["sale"] - (row["expenses"] + row["commission"]), 2)
            actual_pnl = round(row["pnl"], 2)
            assert abs(actual_pnl - expected_pnl) < 0.01, f"P/L formula incorrect: expected {expected_pnl}, got {actual_pnl}"
            
            print(f"Row structure verified: month={row['month']}, sale={row['sale']}, expenses={row['expenses']}, commission={row['commission']}, pnl={row['pnl']}")
    
    def test_03_wc_topup_endpoint(self):
        """Test wc-topup endpoint adds manual top-up with audit trail"""
        topup_amount = 5000.50
        topup_reason = "TEST_TOPUP_ITERATION57"
        topup_month = TEST_MONTH
        
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-topup", json={
            "token": self.token,
            "center": TEST_CENTER,
            "amount": topup_amount,
            "reason": topup_reason,
            "month": topup_month
        })
        assert res.status_code == 200, f"wc-topup failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True, f"Expected success=True, got: {data}"
        assert "topup" in data, "Missing 'topup' in response"
        
        topup = data["topup"]
        assert topup.get("amount") == topup_amount, f"Amount mismatch: expected {topup_amount}, got {topup.get('amount')}"
        assert topup.get("reason") == topup_reason, f"Reason mismatch"
        assert topup.get("month") == topup_month, f"Month mismatch"
        assert "added_by" in topup, "Missing 'added_by' in topup record"
        assert "date" in topup, "Missing 'date' in topup record"
        
        print(f"Top-up created: amount={topup['amount']}, reason={topup['reason']}, added_by={topup['added_by']}")
    
    def test_04_wc_topup_appears_in_table(self):
        """Test that top-up appears in wc-table response"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        assert res.status_code == 200
        data = res.json()
        
        # Check topup_log contains our test topup
        topup_log = data.get("topup_log", [])
        test_topups = [t for t in topup_log if t.get("reason") == "TEST_TOPUP_ITERATION57"]
        assert len(test_topups) > 0, f"Test topup not found in topup_log: {topup_log}"
        
        print(f"Found {len(test_topups)} test topup(s) in audit log")
    
    def test_05_wc_override_endpoint(self):
        """Test wc-override endpoint sets initial WC value"""
        override_value = 100000.00
        
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-override", json={
            "token": self.token,
            "center": TEST_CENTER,
            "value": override_value
        })
        assert res.status_code == 200, f"wc-override failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True, f"Expected success=True, got: {data}"
        
        # Verify override is reflected in wc-table
        res2 = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        assert res2.status_code == 200
        data2 = res2.json()
        
        assert data2.get("initial_wc") == override_value, f"Initial WC not updated: expected {override_value}, got {data2.get('initial_wc')}"
        
        print(f"WC override set: initial_wc={data2['initial_wc']}")
    
    def test_06_revenue_share_status_active(self):
        """Test revenue share status is 'active' when WC > 50% of initial"""
        # First set a known initial WC
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-override", json={
            "token": self.token,
            "center": TEST_CENTER,
            "value": 100000.00
        })
        assert res.status_code == 200
        
        # Get WC table
        res2 = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        assert res2.status_code == 200
        data = res2.json()
        
        initial_wc = data.get("initial_wc", 0)
        current_wc = data.get("current_wc", 0)
        status = data.get("revenue_share_status")
        
        # If current_wc > 50% of initial, status should be 'active'
        threshold = initial_wc * 0.5
        if current_wc > threshold:
            assert status == "active", f"Expected 'active' when WC > 50%, got '{status}'"
        else:
            assert status == "stopped", f"Expected 'stopped' when WC <= 50%, got '{status}'"
        
        print(f"Revenue share status: {status} (current_wc={current_wc}, threshold={threshold})")
    
    def test_07_wc_topup_validation_amount_required(self):
        """Test wc-topup requires amount field"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-topup", json={
            "token": self.token,
            "center": TEST_CENTER,
            "reason": "Test without amount"
        })
        # Should return 400 error
        assert res.status_code == 400, f"Expected 400 for missing amount, got {res.status_code}"
    
    def test_08_wc_override_validation_value_required(self):
        """Test wc-override requires value field"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-override", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        # Should return 400 error
        assert res.status_code == 400, f"Expected 400 for missing value, got {res.status_code}"
    
    def test_09_wc_table_pnl_losses_deduct_profits_dont_add(self):
        """Test that losses deduct from WC but profits don't auto-add"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        assert res.status_code == 200
        data = res.json()
        
        rows = data.get("rows", [])
        if len(rows) >= 2:
            # Check WC calculation logic across rows
            for i in range(1, len(rows)):
                prev_row = rows[i-1]
                curr_row = rows[i]
                
                # Opening WC should equal previous closing WC
                # (accounting for topups which are added after P/L)
                expected_opening = prev_row["closing_wc"]
                actual_opening = curr_row["opening_wc"]
                
                # Allow small floating point differences
                assert abs(actual_opening - expected_opening) < 0.01, \
                    f"Opening WC mismatch at {curr_row['month']}: expected {expected_opening}, got {actual_opening}"
                
                # Verify closing WC calculation:
                # If P/L < 0: closing = opening + pnl + topup
                # If P/L >= 0: closing = opening + topup (profit doesn't add)
                pnl = curr_row["pnl"]
                topup = curr_row["topup"]
                opening = curr_row["opening_wc"]
                closing = curr_row["closing_wc"]
                
                if pnl < 0:
                    expected_closing = round(opening + pnl + topup, 2)
                else:
                    expected_closing = round(opening + topup, 2)
                
                assert abs(closing - expected_closing) < 0.01, \
                    f"Closing WC mismatch at {curr_row['month']}: expected {expected_closing}, got {closing} (pnl={pnl}, topup={topup})"
            
            print(f"Verified WC calculation logic across {len(rows)} rows")
        else:
            print("Not enough rows to verify WC calculation logic")
    
    def test_10_wc_table_auth_required(self):
        """Test wc-table requires authentication"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "center": TEST_CENTER
        })
        assert res.status_code == 401, f"Expected 401 for missing token, got {res.status_code}"


class TestWCCleanup:
    """Cleanup test data after tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP,
            "center": TEST_CENTER
        })
        if res.status_code == 200:
            data = res.json()
            self.token = data.get("token")
        yield
    
    def test_cleanup_test_topups(self):
        """Clean up test topup records (informational only)"""
        # Note: In a real scenario, we'd have a delete endpoint
        # For now, just verify we can see the test data
        if hasattr(self, 'token') and self.token:
            res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
                "token": self.token,
                "center": TEST_CENTER
            })
            if res.status_code == 200:
                data = res.json()
                test_topups = [t for t in data.get("topup_log", []) if "TEST_TOPUP" in str(t.get("reason", ""))]
                print(f"Test topups to clean up: {len(test_topups)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
