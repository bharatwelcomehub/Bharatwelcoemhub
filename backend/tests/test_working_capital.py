"""
Test Working Capital Calculation Feature
Tests the dynamic WC calculation: WC Available = Initial Security Deposit + Cumulative P&L - Loans Outstanding
where P&L = Sales - Expenses - Commissions - GST from center opening to selected month
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_CENTER = "PB-MGT"
OTP = "123456"

# Test centers with data
TEST_CENTER_POSITIVE_PNL = "PB-TH"  # Has positive cumulative P&L
TEST_CENTER_NEGATIVE_PNL = "PB-KAL"  # Has negative cumulative P&L
TEST_MONTH = "2026-03"


class TestWorkingCapitalBackend:
    """Test Working Capital calculation in center-accounts/summary endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        # Send OTP
        send_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER
        })
        assert send_res.status_code == 200, f"Send OTP failed: {send_res.text}"
        
        # Verify OTP
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": OTP,
            "center": SUPER_ADMIN_CENTER
        })
        assert verify_res.status_code == 200, f"Verify OTP failed: {verify_res.text}"
        data = verify_res.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_summary_endpoint_returns_wc_standing(self, auth_token):
        """Test that POST /api/center-accounts/summary returns wc_standing in financial_summary"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": auth_token,
            "center": TEST_CENTER_POSITIVE_PNL,
            "month": TEST_MONTH
        })
        assert res.status_code == 200, f"Summary endpoint failed: {res.text}"
        data = res.json()
        
        # Verify response structure
        assert data.get("success") is True, "Response should have success=True"
        assert "summary" in data, "Response should have 'summary' wrapper"
        
        summary = data["summary"]
        assert "financial_summary" in summary, "Summary should have financial_summary"
        
        fin_summary = summary["financial_summary"]
        assert "wc_standing" in fin_summary, "financial_summary should have wc_standing"
        
        print(f"PASSED: wc_standing present in financial_summary")
    
    def test_wc_standing_contains_required_fields(self, auth_token):
        """Test that wc_standing contains all required fields"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": auth_token,
            "center": TEST_CENTER_POSITIVE_PNL,
            "month": TEST_MONTH
        })
        assert res.status_code == 200
        data = res.json()
        
        wc_standing = data["summary"]["financial_summary"]["wc_standing"]
        
        # Required fields
        required_fields = [
            "initial_security_deposit",
            "cumulative_sales",
            "cumulative_expenses",
            "cumulative_commissions",
            "cumulative_gst",
            "cumulative_pnl",
            "loans_outstanding",
            "available_capital",
            "current_month_pnl"
        ]
        
        for field in required_fields:
            assert field in wc_standing, f"wc_standing missing required field: {field}"
            print(f"  - {field}: {wc_standing[field]}")
        
        print(f"PASSED: All required fields present in wc_standing")
    
    def test_working_capital_formula(self, auth_token):
        """Test WC Available = Initial Security Deposit + Cumulative P&L - Loans Outstanding"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": auth_token,
            "center": TEST_CENTER_POSITIVE_PNL,
            "month": TEST_MONTH
        })
        assert res.status_code == 200
        data = res.json()
        
        wc = data["summary"]["financial_summary"]["wc_standing"]
        
        # Calculate expected available capital
        expected_available = (
            wc["initial_security_deposit"] + 
            wc["cumulative_pnl"] - 
            wc["loans_outstanding"]
        )
        
        # Allow small floating point tolerance
        actual_available = wc["available_capital"]
        assert abs(actual_available - expected_available) < 0.01, \
            f"WC formula mismatch: expected {expected_available}, got {actual_available}"
        
        print(f"PASSED: WC formula verified")
        print(f"  Security Deposit: {wc['initial_security_deposit']}")
        print(f"  + Cumulative P&L: {wc['cumulative_pnl']}")
        print(f"  - Loans Outstanding: {wc['loans_outstanding']}")
        print(f"  = Available Capital: {actual_available}")
    
    def test_cumulative_pnl_formula(self, auth_token):
        """Test Cumulative P&L = Sales - Expenses - Commissions - GST"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": auth_token,
            "center": TEST_CENTER_POSITIVE_PNL,
            "month": TEST_MONTH
        })
        assert res.status_code == 200
        data = res.json()
        
        wc = data["summary"]["financial_summary"]["wc_standing"]
        
        # Calculate expected P&L
        expected_pnl = (
            wc["cumulative_sales"] - 
            wc["cumulative_expenses"] - 
            wc["cumulative_commissions"] - 
            wc["cumulative_gst"]
        )
        
        actual_pnl = wc["cumulative_pnl"]
        assert abs(actual_pnl - expected_pnl) < 0.01, \
            f"P&L formula mismatch: expected {expected_pnl}, got {actual_pnl}"
        
        print(f"PASSED: Cumulative P&L formula verified")
        print(f"  Sales: {wc['cumulative_sales']}")
        print(f"  - Expenses: {wc['cumulative_expenses']}")
        print(f"  - Commissions: {wc['cumulative_commissions']}")
        print(f"  - GST: {wc['cumulative_gst']}")
        print(f"  = P&L: {actual_pnl}")
    
    def test_positive_pnl_center(self, auth_token):
        """Test center with positive cumulative P&L (PB-TH)"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": auth_token,
            "center": TEST_CENTER_POSITIVE_PNL,
            "month": TEST_MONTH
        })
        assert res.status_code == 200
        data = res.json()
        
        wc = data["summary"]["financial_summary"]["wc_standing"]
        
        # PB-TH should have positive P&L based on context
        # cumulative_sales ~12.7M, cumulative_expenses ~1.6M
        print(f"PB-TH Working Capital Standing:")
        print(f"  Cumulative Sales: {wc['cumulative_sales']}")
        print(f"  Cumulative Expenses: {wc['cumulative_expenses']}")
        print(f"  Cumulative P&L: {wc['cumulative_pnl']}")
        print(f"  Available Capital: {wc['available_capital']}")
        
        # Verify sales are significant (should be in millions)
        assert wc["cumulative_sales"] > 1000000, \
            f"PB-TH should have significant sales, got {wc['cumulative_sales']}"
        
        print(f"PASSED: PB-TH has significant cumulative sales")
    
    def test_negative_pnl_center(self, auth_token):
        """Test center with negative cumulative P&L (PB-KAL)"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": auth_token,
            "center": TEST_CENTER_NEGATIVE_PNL,
            "month": TEST_MONTH
        })
        assert res.status_code == 200
        data = res.json()
        
        wc = data["summary"]["financial_summary"]["wc_standing"]
        
        # PB-KAL should have negative P&L based on context
        # cumulative_sales ~338K, cumulative_expenses ~755K
        print(f"PB-KAL Working Capital Standing:")
        print(f"  Cumulative Sales: {wc['cumulative_sales']}")
        print(f"  Cumulative Expenses: {wc['cumulative_expenses']}")
        print(f"  Cumulative P&L: {wc['cumulative_pnl']}")
        print(f"  Available Capital: {wc['available_capital']}")
        
        # Just verify the endpoint works for this center
        assert "cumulative_pnl" in wc, "Should have cumulative_pnl field"
        
        print(f"PASSED: PB-KAL working capital data retrieved")
    
    def test_financial_summary_has_wc_fields(self, auth_token):
        """Test that financial_summary has working_capital_available field"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": auth_token,
            "center": TEST_CENTER_POSITIVE_PNL,
            "month": TEST_MONTH
        })
        assert res.status_code == 200
        data = res.json()
        
        fin_summary = data["summary"]["financial_summary"]
        
        # Check for working_capital_available at top level of financial_summary
        assert "working_capital_available" in fin_summary, \
            "financial_summary should have working_capital_available"
        
        # Should match wc_standing.available_capital
        wc_standing = fin_summary["wc_standing"]
        assert fin_summary["working_capital_available"] == wc_standing["available_capital"], \
            "working_capital_available should match wc_standing.available_capital"
        
        print(f"PASSED: working_capital_available field present and matches wc_standing")
    
    def test_current_month_pnl(self, auth_token):
        """Test that current_month_pnl is calculated correctly"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": auth_token,
            "center": TEST_CENTER_POSITIVE_PNL,
            "month": TEST_MONTH
        })
        assert res.status_code == 200
        data = res.json()
        
        wc = data["summary"]["financial_summary"]["wc_standing"]
        
        # current_month_pnl should be present
        assert "current_month_pnl" in wc, "Should have current_month_pnl"
        assert "current_month_sales" in wc, "Should have current_month_sales"
        assert "current_month_expenses" in wc, "Should have current_month_expenses"
        
        # Verify formula: current_month_pnl = current_month_sales - current_month_expenses
        expected_month_pnl = wc["current_month_sales"] - wc["current_month_expenses"]
        assert abs(wc["current_month_pnl"] - expected_month_pnl) < 0.01, \
            f"Current month P&L mismatch: expected {expected_month_pnl}, got {wc['current_month_pnl']}"
        
        print(f"PASSED: Current month P&L formula verified")
        print(f"  Current Month Sales: {wc['current_month_sales']}")
        print(f"  Current Month Expenses: {wc['current_month_expenses']}")
        print(f"  Current Month P&L: {wc['current_month_pnl']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
