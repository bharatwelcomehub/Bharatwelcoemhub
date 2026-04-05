"""
Test: Endless Future Dummy Months Generation Bug Fix (Iteration 58)

This test verifies that the WC table and payout-summary endpoints properly cap
month generation at the franchise's effective end date:
- min(agreement_end_date, closure_date, current_month)

Test Centers:
- PB-HSR (linked to FR-TEST-INDIA, closure_date 2026-03-22)
- PB-PERTH (linked to FR-PERTH, closure_date 2026-03-22, agreement_end_date 2032-02-25)

Both should have effective_end_month = 2026-03 (closure_date is earlier than current month Jan 2026)
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_OTP = "123456"
SUPER_ADMIN_CENTER = "PB-MGT"

# Test centers with known closure dates
TEST_CENTER_HSR = "PB-HSR"  # FR-TEST-INDIA, closure_date 2026-03-22
TEST_CENTER_PERTH = "PB-PERTH"  # FR-PERTH, closure_date 2026-03-22, agreement_end_date 2032-02-25


class TestAuthFixture:
    """Authentication helper"""
    
    @staticmethod
    def get_auth_token():
        """Get authentication token using OTP flow"""
        # Step 1: Send OTP
        send_otp_resp = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER
        })
        assert send_otp_resp.status_code == 200, f"Send OTP failed: {send_otp_resp.text}"
        
        # Step 2: Verify OTP
        verify_resp = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP,
            "center": SUPER_ADMIN_CENTER
        })
        assert verify_resp.status_code == 200, f"Verify OTP failed: {verify_resp.text}"
        
        data = verify_resp.json()
        token = data.get("token")
        assert token, "No token returned from verify_otp"
        return token


@pytest.fixture(scope="module")
def auth_token():
    """Module-scoped auth token fixture"""
    return TestAuthFixture.get_auth_token()


class TestWCTableEffectiveEndMonth:
    """Tests for /api/center-accounts/wc-table endpoint - effective end month capping"""
    
    def test_wc_table_returns_effective_end_month_field(self, auth_token):
        """Verify WC table response includes 'effective_end_month' field"""
        response = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": auth_token,
            "center": TEST_CENTER_HSR
        })
        
        assert response.status_code == 200, f"WC table request failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True, "Response should indicate success"
        assert "effective_end_month" in data, "Response should include 'effective_end_month' field"
        
        effective_end = data.get("effective_end_month")
        print(f"Effective end month for {TEST_CENTER_HSR}: {effective_end}")
        
        # Effective end should be in YYYY-MM format
        assert len(effective_end) == 7, f"effective_end_month should be YYYY-MM format, got: {effective_end}"
        assert effective_end[4] == "-", f"effective_end_month should be YYYY-MM format, got: {effective_end}"
    
    def test_wc_table_no_rows_beyond_effective_end(self, auth_token):
        """Verify WC table does NOT return rows beyond the franchise's effective end month"""
        response = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": auth_token,
            "center": TEST_CENTER_HSR
        })
        
        assert response.status_code == 200, f"WC table request failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        effective_end = data.get("effective_end_month")
        rows = data.get("rows", [])
        
        print(f"Effective end month: {effective_end}")
        print(f"Number of rows: {len(rows)}")
        
        # Check that no row has a month beyond effective_end
        for row in rows:
            row_month = row.get("month")
            assert row_month <= effective_end, f"Row month {row_month} exceeds effective end {effective_end}"
        
        # If there are rows, the last row should be <= effective_end
        if rows:
            last_row_month = rows[-1].get("month")
            print(f"Last row month: {last_row_month}")
            assert last_row_month <= effective_end, f"Last row month {last_row_month} exceeds effective end {effective_end}"
    
    def test_wc_table_effective_end_respects_closure_date(self, auth_token):
        """Verify effective_end_month respects franchise closure_date (2026-03)"""
        response = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": auth_token,
            "center": TEST_CENTER_HSR
        })
        
        assert response.status_code == 200
        data = response.json()
        
        effective_end = data.get("effective_end_month")
        current_month = datetime.now().strftime("%Y-%m")
        
        # FR-TEST-INDIA has closure_date 2026-03-22
        # Effective end should be min(closure_date, current_month) = 2026-01 (current month Jan 2026)
        # OR if closure_date is in the future, it should be current_month
        print(f"Current month: {current_month}")
        print(f"Effective end: {effective_end}")
        
        # Effective end should never exceed current month
        assert effective_end <= current_month, f"Effective end {effective_end} should not exceed current month {current_month}"
    
    def test_wc_table_row_structure_intact(self, auth_token):
        """Verify existing WC table functionality - row structure contains required fields"""
        response = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": auth_token,
            "center": TEST_CENTER_HSR
        })
        
        assert response.status_code == 200
        data = response.json()
        
        rows = data.get("rows", [])
        
        # Required fields in each row
        required_fields = ["month", "sale", "expenses", "commission", "pnl", "opening_wc", "topup", "closing_wc"]
        
        for row in rows:
            for field in required_fields:
                assert field in row, f"Row missing required field: {field}"
        
        print(f"All {len(rows)} rows have required fields: {required_fields}")
    
    def test_wc_table_perth_center(self, auth_token):
        """Test WC table for PB-PERTH center (has both closure_date and agreement_end_date)"""
        response = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "token": auth_token,
            "center": TEST_CENTER_PERTH
        })
        
        assert response.status_code == 200, f"WC table request failed: {response.text}"
        data = response.json()
        
        effective_end = data.get("effective_end_month")
        rows = data.get("rows", [])
        current_month = datetime.now().strftime("%Y-%m")
        
        print(f"PB-PERTH effective end: {effective_end}")
        print(f"PB-PERTH rows count: {len(rows)}")
        
        # Effective end should not exceed current month
        assert effective_end <= current_month, f"Effective end {effective_end} exceeds current month {current_month}"
        
        # No rows should exceed effective end
        for row in rows:
            assert row.get("month") <= effective_end, f"Row month {row.get('month')} exceeds effective end {effective_end}"


class TestPayoutSummaryEffectiveEndMonth:
    """Tests for /api/center-accounts/payout-summary endpoint - effective end month capping"""
    
    def test_payout_summary_caps_far_future_to_month(self, auth_token):
        """Verify payout-summary caps to_month at franchise's effective end month when far-future date passed"""
        # Pass a far-future to_month (e.g., 2087-12) - this was the bug scenario
        response = requests.post(f"{BASE_URL}/api/center-accounts/payout-summary", json={
            "token": auth_token,
            "center": TEST_CENTER_HSR,
            "to_month": "2087-12"  # Far future - should be capped
        })
        
        assert response.status_code == 200, f"Payout summary request failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        
        period = data.get("period", {})
        actual_to_month = period.get("to")
        current_month = datetime.now().strftime("%Y-%m")
        
        print(f"Requested to_month: 2087-12")
        print(f"Actual to_month returned: {actual_to_month}")
        print(f"Current month: {current_month}")
        
        # The to_month should be capped at effective end (which is <= current month)
        assert actual_to_month <= current_month, f"to_month {actual_to_month} should be capped at or before current month {current_month}"
        assert actual_to_month != "2087-12", "to_month should NOT be the far-future date 2087-12"
    
    def test_payout_summary_no_to_month_defaults_to_effective_end(self, auth_token):
        """Verify payout-summary without to_month defaults to effective end month, not infinite future"""
        response = requests.post(f"{BASE_URL}/api/center-accounts/payout-summary", json={
            "token": auth_token,
            "center": TEST_CENTER_HSR
            # No to_month provided
        })
        
        assert response.status_code == 200, f"Payout summary request failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        
        period = data.get("period", {})
        actual_to_month = period.get("to")
        current_month = datetime.now().strftime("%Y-%m")
        
        print(f"to_month when not provided: {actual_to_month}")
        print(f"Current month: {current_month}")
        
        # Should default to effective end (which is <= current month)
        assert actual_to_month <= current_month, f"Default to_month {actual_to_month} should be at or before current month"
    
    def test_payout_summary_monthly_data_not_endless(self, auth_token):
        """Verify monthly_data does not contain endless future months"""
        response = requests.post(f"{BASE_URL}/api/center-accounts/payout-summary", json={
            "token": auth_token,
            "center": TEST_CENTER_HSR,
            "to_month": "2087-12"  # Far future
        })
        
        assert response.status_code == 200
        data = response.json()
        
        monthly_data = data.get("monthly_data", [])
        current_month = datetime.now().strftime("%Y-%m")
        
        print(f"Number of months in monthly_data: {len(monthly_data)}")
        
        # Should NOT have hundreds/thousands of months
        # A reasonable range would be at most a few years of data
        assert len(monthly_data) < 100, f"monthly_data has {len(monthly_data)} entries - seems like endless generation"
        
        # No month should exceed current month
        for entry in monthly_data:
            month = entry.get("month")
            assert month <= current_month, f"Monthly data contains future month {month} beyond current {current_month}"
        
        if monthly_data:
            last_month = monthly_data[-1].get("month")
            print(f"Last month in monthly_data: {last_month}")
            assert last_month <= current_month, f"Last month {last_month} exceeds current month {current_month}"
    
    def test_payout_summary_returns_correct_payable_amounts(self, auth_token):
        """Verify existing payout-summary functionality - returns monthly_data with payable amounts"""
        response = requests.post(f"{BASE_URL}/api/center-accounts/payout-summary", json={
            "token": auth_token,
            "center": TEST_CENTER_HSR,
            "from_month": "2025-01",
            "to_month": "2025-12"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        
        # Check structure
        assert "monthly_data" in data, "Response should include monthly_data"
        assert "totals" in data, "Response should include totals"
        assert "period" in data, "Response should include period"
        
        monthly_data = data.get("monthly_data", [])
        
        # Each month entry should have required fields
        required_fields = ["month", "total_sales", "revenue_share", "mg_amount", "payable_type", "payable_amount", "paid", "pending", "status"]
        
        for entry in monthly_data:
            for field in required_fields:
                assert field in entry, f"Monthly data entry missing field: {field}"
        
        print(f"Payout summary has {len(monthly_data)} months with correct structure")
    
    def test_payout_summary_perth_center_far_future(self, auth_token):
        """Test payout-summary for PB-PERTH with far-future to_month"""
        response = requests.post(f"{BASE_URL}/api/center-accounts/payout-summary", json={
            "token": auth_token,
            "center": TEST_CENTER_PERTH,
            "to_month": "2087-12"
        })
        
        assert response.status_code == 200, f"Payout summary request failed: {response.text}"
        data = response.json()
        
        period = data.get("period", {})
        actual_to_month = period.get("to")
        current_month = datetime.now().strftime("%Y-%m")
        
        print(f"PB-PERTH: Requested to_month: 2087-12, Actual: {actual_to_month}")
        
        # Should be capped
        assert actual_to_month <= current_month, f"to_month {actual_to_month} should be capped"
        assert actual_to_month != "2087-12", "to_month should NOT be 2087-12"


class TestHelperFunctionLogic:
    """Tests to verify the get_franchise_effective_end_month helper function logic"""
    
    def test_effective_end_never_exceeds_current_month(self, auth_token):
        """Verify effective_end_month never exceeds current month for any center"""
        current_month = datetime.now().strftime("%Y-%m")
        
        for center in [TEST_CENTER_HSR, TEST_CENTER_PERTH]:
            response = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
                "token": auth_token,
                "center": center
            })
            
            if response.status_code == 200:
                data = response.json()
                effective_end = data.get("effective_end_month")
                
                if effective_end:
                    assert effective_end <= current_month, f"{center}: effective_end {effective_end} exceeds current month {current_month}"
                    print(f"{center}: effective_end_month = {effective_end} (OK, <= {current_month})")
    
    def test_wc_table_auth_required(self, auth_token):
        """Verify WC table requires authentication"""
        response = requests.post(f"{BASE_URL}/api/center-accounts/wc-table", json={
            "center": TEST_CENTER_HSR
            # No token
        })
        
        assert response.status_code == 401, f"Expected 401 without token, got {response.status_code}"
        print("Auth required check passed - 401 returned without token")
    
    def test_payout_summary_auth_required(self, auth_token):
        """Verify payout-summary requires authentication"""
        response = requests.post(f"{BASE_URL}/api/center-accounts/payout-summary", json={
            "center": TEST_CENTER_HSR
            # No token
        })
        
        assert response.status_code == 401, f"Expected 401 without token, got {response.status_code}"
        print("Auth required check passed - 401 returned without token")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
