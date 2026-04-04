"""
Test WC Table and WC Override endpoints
Features:
- POST /api/center-accounts/wc-table - returns month-by-month WC data
- POST /api/center-accounts/wc-override - set initial WC or month-specific override
- P/L = Sale - Expenses (simple formula, no GST/commissions)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"
TEST_CENTER = "PB-MGT"
TEST_CENTER_WITH_DATA = "PB-HSR"  # Center with sales data


class TestWCTableEndpoint:
    """Test /api/center-accounts/wc-table endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        # Send OTP
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        assert res.status_code == 200, f"Send OTP failed: {res.text}"
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP,
            "center": TEST_CENTER
        })
        assert res.status_code == 200, f"Verify OTP failed: {res.text}"
        data = res.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_wc_table_endpoint_exists(self, auth_token):
        """Test that wc-table endpoint exists and returns data"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": auth_token,
            "center": TEST_CENTER_WITH_DATA
        })
        assert res.status_code == 200, f"WC table endpoint failed: {res.text}"
        data = res.json()
        assert data.get("success") == True, f"WC table not successful: {data}"
        assert "rows" in data, "No rows in response"
        assert "initial_wc" in data, "No initial_wc in response"
        assert "center" in data, "No center in response"
        print(f"PASSED: WC table endpoint returns data for {TEST_CENTER_WITH_DATA}")
    
    def test_wc_table_returns_month_data(self, auth_token):
        """Test that wc-table returns month-by-month data with correct columns"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": auth_token,
            "center": TEST_CENTER_WITH_DATA
        })
        assert res.status_code == 200
        data = res.json()
        
        rows = data.get("rows", [])
        if len(rows) > 0:
            # Check first row has all required columns
            first_row = rows[0]
            required_columns = ["month", "sale", "expenses", "pnl", "opening_wc", "closing_wc", "diff_from_initial"]
            for col in required_columns:
                assert col in first_row, f"Missing column: {col}"
            
            # Verify P/L formula: P/L = Sale - Expenses
            sale = first_row.get("sale", 0)
            expenses = first_row.get("expenses", 0)
            pnl = first_row.get("pnl", 0)
            expected_pnl = round(sale - expenses, 2)
            assert abs(pnl - expected_pnl) < 0.01, f"P/L formula incorrect: {pnl} != {expected_pnl}"
            
            print(f"PASSED: WC table has {len(rows)} months with correct columns")
            print(f"  First row: month={first_row['month']}, sale={sale}, expenses={expenses}, pnl={pnl}")
        else:
            print("PASSED: WC table returns empty rows (no data for center)")
    
    def test_wc_table_closing_wc_formula(self, auth_token):
        """Test that closing WC = opening WC + P/L"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": auth_token,
            "center": TEST_CENTER_WITH_DATA
        })
        assert res.status_code == 200
        data = res.json()
        
        rows = data.get("rows", [])
        if len(rows) > 0:
            for row in rows:
                opening_wc = row.get("opening_wc", 0)
                pnl = row.get("pnl", 0)
                closing_wc = row.get("closing_wc", 0)
                expected_closing = round(opening_wc + pnl, 2)
                assert abs(closing_wc - expected_closing) < 0.01, f"Closing WC formula incorrect for {row['month']}: {closing_wc} != {expected_closing}"
            print(f"PASSED: Closing WC formula verified for {len(rows)} months")
    
    def test_wc_table_diff_from_initial(self, auth_token):
        """Test that diff_from_initial = closing_wc - initial_wc"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": auth_token,
            "center": TEST_CENTER_WITH_DATA
        })
        assert res.status_code == 200
        data = res.json()
        
        initial_wc = data.get("initial_wc", 0)
        rows = data.get("rows", [])
        if len(rows) > 0:
            for row in rows:
                closing_wc = row.get("closing_wc", 0)
                diff = row.get("diff_from_initial", 0)
                expected_diff = round(closing_wc - initial_wc, 2)
                assert abs(diff - expected_diff) < 0.01, f"Diff formula incorrect for {row['month']}: {diff} != {expected_diff}"
            print(f"PASSED: Diff from initial formula verified for {len(rows)} months")
    
    def test_wc_table_requires_auth(self):
        """Test that wc-table requires authentication"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": "invalid_token",
            "center": TEST_CENTER_WITH_DATA
        })
        assert res.status_code == 401, f"Expected 401 for invalid token, got {res.status_code}"
        print("PASSED: WC table requires valid authentication")


class TestWCOverrideEndpoint:
    """Test /api/center-accounts/wc-override endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        assert res.status_code == 200
        
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP,
            "center": TEST_CENTER
        })
        assert res.status_code == 200
        return res.json()["token"]
    
    def test_wc_override_set_initial_wc(self, auth_token):
        """Test setting initial WC value (no month param)"""
        test_value = 950000
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-override", json={
            "token": auth_token,
            "center": TEST_CENTER_WITH_DATA,
            "value": test_value
        })
        assert res.status_code == 200, f"WC override failed: {res.text}"
        data = res.json()
        assert data.get("success") == True, f"WC override not successful: {data}"
        assert "message" in data, "No message in response"
        print(f"PASSED: Initial WC override set to {test_value}")
        
        # Verify the override is reflected in wc-table
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": auth_token,
            "center": TEST_CENTER_WITH_DATA
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("initial_wc") == test_value, f"Initial WC not updated: {data.get('initial_wc')} != {test_value}"
        print(f"PASSED: Initial WC verified in wc-table response")
    
    def test_wc_override_set_month_override(self, auth_token):
        """Test setting month-specific opening WC override"""
        # First get the first month from wc-table
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": auth_token,
            "center": TEST_CENTER_WITH_DATA
        })
        assert res.status_code == 200
        data = res.json()
        rows = data.get("rows", [])
        
        if len(rows) > 0:
            first_month = rows[0]["month"]
            test_value = 800000
            
            # Set month override
            res = requests.post(f"{BASE_URL}/api/center-accounts/wc-override", json={
                "token": auth_token,
                "center": TEST_CENTER_WITH_DATA,
                "month": first_month,
                "value": test_value
            })
            assert res.status_code == 200, f"Month override failed: {res.text}"
            data = res.json()
            assert data.get("success") == True
            print(f"PASSED: Month override set for {first_month} to {test_value}")
            
            # Verify the override is reflected
            res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
                "token": auth_token,
                "center": TEST_CENTER_WITH_DATA
            })
            assert res.status_code == 200
            data = res.json()
            rows = data.get("rows", [])
            first_row = rows[0]
            assert first_row.get("opening_wc") == test_value, f"Month override not applied: {first_row.get('opening_wc')} != {test_value}"
            assert first_row.get("has_override") == True, "has_override flag not set"
            print(f"PASSED: Month override verified in wc-table response")
        else:
            pytest.skip("No data for center to test month override")
    
    def test_wc_override_requires_value(self, auth_token):
        """Test that wc-override requires value parameter"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-override", json={
            "token": auth_token,
            "center": TEST_CENTER_WITH_DATA
        })
        assert res.status_code == 400, f"Expected 400 for missing value, got {res.status_code}"
        print("PASSED: WC override requires value parameter")
    
    def test_wc_override_requires_auth(self):
        """Test that wc-override requires authentication"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-override", json={
            "token": "invalid_token",
            "center": TEST_CENTER_WITH_DATA,
            "value": 100000
        })
        assert res.status_code == 401, f"Expected 401 for invalid token, got {res.status_code}"
        print("PASSED: WC override requires valid authentication")


class TestWCTableChaining:
    """Test that WC table chains opening/closing balances correctly"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        assert res.status_code == 200
        
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP,
            "center": TEST_CENTER
        })
        assert res.status_code == 200
        return res.json()["token"]
    
    def test_wc_chaining_between_months(self, auth_token):
        """Test that opening WC of month N = closing WC of month N-1"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": auth_token,
            "center": TEST_CENTER_WITH_DATA
        })
        assert res.status_code == 200
        data = res.json()
        
        rows = data.get("rows", [])
        if len(rows) > 1:
            chain_breaks = 0
            for i in range(1, len(rows)):
                prev_closing = rows[i-1].get("closing_wc", 0)
                curr_opening = rows[i].get("opening_wc", 0)
                # Skip if current month has override
                if rows[i].get("has_override"):
                    continue
                if abs(prev_closing - curr_opening) > 0.01:
                    chain_breaks += 1
                    print(f"  Chain break at {rows[i]['month']}: prev_closing={prev_closing}, curr_opening={curr_opening}")
            
            assert chain_breaks == 0, f"Found {chain_breaks} chain breaks in WC table"
            print(f"PASSED: WC chaining verified for {len(rows)} months, 0 breaks")
        else:
            print("PASSED: Not enough months to test chaining")
    
    def test_first_month_uses_initial_wc(self, auth_token):
        """Test that first month's opening WC = initial WC (unless overridden)"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": auth_token,
            "center": TEST_CENTER_WITH_DATA
        })
        assert res.status_code == 200
        data = res.json()
        
        initial_wc = data.get("initial_wc", 0)
        rows = data.get("rows", [])
        
        if len(rows) > 0:
            first_row = rows[0]
            # If first month has override, skip this check
            if not first_row.get("has_override"):
                opening_wc = first_row.get("opening_wc", 0)
                assert abs(opening_wc - initial_wc) < 0.01, f"First month opening WC != initial WC: {opening_wc} != {initial_wc}"
                print(f"PASSED: First month opening WC = initial WC ({initial_wc})")
            else:
                print(f"PASSED: First month has override, skipping initial WC check")


# Cleanup: Reset initial WC to original value
class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP,
            "center": TEST_CENTER
        })
        return res.json()["token"]
    
    def test_reset_initial_wc(self, auth_token):
        """Reset initial WC to original value (900000)"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/wc-override", json={
            "token": auth_token,
            "center": TEST_CENTER_WITH_DATA,
            "value": 900000
        })
        assert res.status_code == 200
        print("PASSED: Reset initial WC to 900000")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
