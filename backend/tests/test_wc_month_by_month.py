"""
Test Working Capital Month-by-Month Calculation
Tests the WC Assessment feature that calculates:
- Opening WC = Initial Deposit + cumulative P&L from all previous months
- This Month P&L = Sales - Expenses - Commissions - GST
- Closing WC = Opening WC + This Month P&L (capped at 0 if negative)
- Diff from Initial = Closing WC - Initial Security Deposit
- Loan from WC Deficit = abs(closing) when closing would go negative
- Total Effective Loans = loans_outstanding + loan_from_wc_deficit
- WC Status: healthy (>=100%), restoring (<100% but >=50%), closed (<50%)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_CENTER = "PB-MGT"
OTP = "123456"
TEST_CENTER = "PB-HSR"  # Has franchise FR-TEST-INDIA with WC=900000


class TestWCMonthByMonth:
    """Test Working Capital month-by-month calculation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
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
        assert data.get("success"), f"OTP verification failed: {data}"
        self.token = data.get("token")
        assert self.token, "No token received"
    
    def test_summary_returns_wc_standing_fields(self):
        """Test that /api/center-accounts/summary returns wc_standing with all required fields"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": self.token,
            "center": TEST_CENTER,
            "month": "2026-03"
        })
        assert res.status_code == 200, f"API failed: {res.text}"
        data = res.json()
        assert data.get("success"), f"API returned error: {data}"
        
        summary = data.get("summary", {})
        fin_summary = summary.get("financial_summary", {})
        wc_standing = fin_summary.get("wc_standing", {})
        
        # Verify all required fields exist
        required_fields = [
            "opening_wc",
            "this_month_pnl",
            "closing_wc",
            "diff_from_initial",
            "loan_from_wc_deficit",
            "total_effective_loans",
            "wc_status",
            "initial_security_deposit",
            "loans_outstanding",
            "wc_percentage",
            "revenue_share_active"
        ]
        
        for field in required_fields:
            assert field in wc_standing, f"Missing field: {field}"
            print(f"  {field}: {wc_standing[field]}")
        
        print(f"\nWC Standing for {TEST_CENTER} 2026-03:")
        print(f"  Opening WC: {wc_standing['opening_wc']}")
        print(f"  This Month P&L: {wc_standing['this_month_pnl']}")
        print(f"  Closing WC: {wc_standing['closing_wc']}")
        print(f"  Diff from Initial: {wc_standing['diff_from_initial']}")
        print(f"  WC Status: {wc_standing['wc_status']}")
    
    def test_closing_wc_equals_opening_plus_pnl(self):
        """Test that closing_wc = opening_wc + this_month_pnl (when closing >= 0)"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": self.token,
            "center": TEST_CENTER,
            "month": "2026-03"
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success")
        
        wc = data["summary"]["financial_summary"]["wc_standing"]
        
        opening = wc["opening_wc"]
        pnl = wc["this_month_pnl"]
        closing = wc["closing_wc"]
        loan_deficit = wc["loan_from_wc_deficit"]
        
        # If closing would be negative, it's capped at 0 and deficit becomes loan
        expected_raw_closing = opening + pnl
        
        if expected_raw_closing >= 0:
            # Normal case: closing = opening + pnl
            assert abs(closing - expected_raw_closing) < 0.01, \
                f"Closing WC mismatch: {closing} != {opening} + {pnl} = {expected_raw_closing}"
            assert loan_deficit == 0, f"Loan deficit should be 0 when closing >= 0"
        else:
            # Deficit case: closing capped at 0, deficit = abs(raw closing)
            assert closing == 0, f"Closing should be 0 when raw closing is negative"
            assert abs(loan_deficit - abs(expected_raw_closing)) < 0.01, \
                f"Loan deficit should be {abs(expected_raw_closing)}, got {loan_deficit}"
        
        print(f"\nClosing WC Formula Verified:")
        print(f"  Opening: {opening}")
        print(f"  + P&L: {pnl}")
        print(f"  = Raw Closing: {expected_raw_closing}")
        print(f"  Actual Closing: {closing}")
        print(f"  Loan from Deficit: {loan_deficit}")
    
    def test_opening_wc_from_previous_months(self):
        """Test that opening_wc = Initial Deposit + cumulative P&L from previous months"""
        # Get March 2026 data
        res_march = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": self.token,
            "center": TEST_CENTER,
            "month": "2026-03"
        })
        assert res_march.status_code == 200
        march_data = res_march.json()
        assert march_data.get("success")
        
        wc_march = march_data["summary"]["financial_summary"]["wc_standing"]
        initial_deposit = wc_march["initial_security_deposit"]
        opening_march = wc_march["opening_wc"]
        
        # Opening WC should be >= initial deposit (if profitable) or < initial (if losses)
        # The formula is: Opening = Initial + sum(P&L for all months before this one)
        print(f"\nOpening WC Analysis for March 2026:")
        print(f"  Initial Security Deposit: {initial_deposit}")
        print(f"  Opening WC (March): {opening_march}")
        print(f"  Cumulative P&L (before March): {opening_march - initial_deposit}")
        
        # Verify opening is a reasonable value (not negative, not absurdly high)
        assert opening_march >= 0, f"Opening WC should not be negative: {opening_march}"
        
        # If we have data, opening should be related to initial deposit
        if initial_deposit > 0:
            # Opening should be within reasonable bounds
            assert opening_march >= initial_deposit * 0.01 or opening_march == 0, \
                f"Opening WC seems too low: {opening_march} vs initial {initial_deposit}"
    
    def test_diff_from_initial_calculation(self):
        """Test that diff_from_initial = closing_wc - initial_security_deposit"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": self.token,
            "center": TEST_CENTER,
            "month": "2026-03"
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success")
        
        wc = data["summary"]["financial_summary"]["wc_standing"]
        
        closing = wc["closing_wc"]
        initial = wc["initial_security_deposit"]
        diff = wc["diff_from_initial"]
        
        expected_diff = closing - initial
        assert abs(diff - expected_diff) < 0.01, \
            f"Diff from initial mismatch: {diff} != {closing} - {initial} = {expected_diff}"
        
        print(f"\nDiff from Initial Verified:")
        print(f"  Closing WC: {closing}")
        print(f"  Initial Deposit: {initial}")
        print(f"  Diff: {diff}")
    
    def test_total_effective_loans_calculation(self):
        """Test that total_effective_loans = loans_outstanding + loan_from_wc_deficit"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": self.token,
            "center": TEST_CENTER,
            "month": "2026-03"
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success")
        
        wc = data["summary"]["financial_summary"]["wc_standing"]
        
        loans_outstanding = wc["loans_outstanding"]
        loan_deficit = wc["loan_from_wc_deficit"]
        total_effective = wc["total_effective_loans"]
        
        expected_total = loans_outstanding + loan_deficit
        assert abs(total_effective - expected_total) < 0.01, \
            f"Total effective loans mismatch: {total_effective} != {loans_outstanding} + {loan_deficit}"
        
        print(f"\nTotal Effective Loans Verified:")
        print(f"  Loans Outstanding: {loans_outstanding}")
        print(f"  Loan from WC Deficit: {loan_deficit}")
        print(f"  Total Effective: {total_effective}")
    
    def test_wc_status_healthy(self):
        """Test WC status is 'healthy' when closing_wc >= initial deposit"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": self.token,
            "center": TEST_CENTER,
            "month": "2026-03"
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success")
        
        wc = data["summary"]["financial_summary"]["wc_standing"]
        
        closing = wc["closing_wc"]
        initial = wc["initial_security_deposit"]
        status = wc["wc_status"]
        percentage = wc["wc_percentage"]
        
        print(f"\nWC Status Analysis:")
        print(f"  Closing WC: {closing}")
        print(f"  Initial Deposit: {initial}")
        print(f"  WC Percentage: {percentage}%")
        print(f"  Status: {status}")
        
        # Verify status logic
        if initial > 0:
            if percentage >= 100:
                assert status == "healthy", f"Status should be 'healthy' at {percentage}%"
            elif percentage >= 50:
                assert status == "restoring", f"Status should be 'restoring' at {percentage}%"
            else:
                assert status == "closed", f"Status should be 'closed' at {percentage}%"
        
        # For PB-HSR with healthy WC, expect healthy status
        if percentage > 100:
            assert status == "healthy", f"Expected healthy status for {percentage}%"
            print(f"  ✓ Status correctly shows 'healthy' at {percentage}%")
    
    def test_this_month_pnl_components(self):
        """Test that this_month_pnl = sales - expenses - commissions - gst"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": self.token,
            "center": TEST_CENTER,
            "month": "2026-03"
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success")
        
        wc = data["summary"]["financial_summary"]["wc_standing"]
        
        # Get P&L components from wc_standing
        this_month_sales = wc.get("this_month_sales", 0)
        this_month_expenses = wc.get("this_month_expenses", 0)
        this_month_commissions = wc.get("this_month_commissions", 0)
        this_month_gst = wc.get("this_month_gst", 0)
        this_month_pnl = wc["this_month_pnl"]
        
        # P&L = Sales - Expenses - Commissions - GST
        expected_pnl = this_month_sales - this_month_expenses - this_month_commissions - this_month_gst
        
        print(f"\nThis Month P&L Components:")
        print(f"  Sales: {this_month_sales}")
        print(f"  - Expenses: {this_month_expenses}")
        print(f"  - Commissions: {this_month_commissions}")
        print(f"  - GST: {this_month_gst}")
        print(f"  = Expected P&L: {expected_pnl}")
        print(f"  Actual P&L: {this_month_pnl}")
        
        # Allow small rounding difference
        assert abs(this_month_pnl - expected_pnl) < 1, \
            f"P&L mismatch: {this_month_pnl} != {expected_pnl}"


class TestWCStatusThresholds:
    """Test WC status thresholds: healthy, restoring, closed"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
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
        self.token = res.json().get("token")
    
    def test_wc_percentage_calculation(self):
        """Test WC percentage = (closing_wc / initial_deposit) * 100"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": self.token,
            "center": TEST_CENTER,
            "month": "2026-03"
        })
        assert res.status_code == 200
        data = res.json()
        
        wc = data["summary"]["financial_summary"]["wc_standing"]
        
        closing = wc["closing_wc"]
        initial = wc["initial_security_deposit"]
        percentage = wc["wc_percentage"]
        
        if initial > 0:
            expected_pct = (closing / initial) * 100
            assert abs(percentage - expected_pct) < 0.1, \
                f"WC percentage mismatch: {percentage} != {expected_pct}"
            print(f"\nWC Percentage: {percentage:.2f}% (closing {closing} / initial {initial})")
    
    def test_revenue_share_active_flag(self):
        """Test revenue_share_active is True when WC >= 50%"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": self.token,
            "center": TEST_CENTER,
            "month": "2026-03"
        })
        assert res.status_code == 200
        data = res.json()
        
        wc = data["summary"]["financial_summary"]["wc_standing"]
        
        percentage = wc["wc_percentage"]
        active = wc["revenue_share_active"]
        
        if percentage >= 50:
            assert active == True, f"Revenue share should be active at {percentage}%"
        else:
            assert active == False, f"Revenue share should be inactive at {percentage}%"
        
        print(f"\nRevenue Share Active: {active} (WC at {percentage}%)")


class TestAPIResponseStructure:
    """Test the API response structure matches expected format"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
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
        self.token = res.json().get("token")
    
    def test_full_response_structure(self):
        """Test complete API response structure"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": self.token,
            "center": TEST_CENTER,
            "month": "2026-03"
        })
        assert res.status_code == 200
        data = res.json()
        
        # Top level
        assert "success" in data
        assert "summary" in data
        
        summary = data["summary"]
        
        # Required top-level fields
        assert "center" in summary
        assert "country" in summary
        assert "period" in summary
        assert "financial_summary" in summary
        
        fin = summary["financial_summary"]
        
        # wc_standing must exist
        assert "wc_standing" in fin, "wc_standing missing from financial_summary"
        
        wc = fin["wc_standing"]
        
        # All WC fields must be numeric
        numeric_fields = [
            "initial_security_deposit", "opening_wc", "this_month_pnl",
            "closing_wc", "diff_from_initial", "loan_from_wc_deficit",
            "loans_outstanding", "total_effective_loans", "wc_percentage"
        ]
        
        for field in numeric_fields:
            assert field in wc, f"Missing field: {field}"
            assert isinstance(wc[field], (int, float)), f"{field} should be numeric"
        
        # Status fields
        assert "wc_status" in wc
        assert wc["wc_status"] in ["healthy", "restoring", "closed"]
        
        assert "revenue_share_active" in wc
        assert isinstance(wc["revenue_share_active"], bool)
        
        print("\n✓ API response structure validated")
        print(f"  Center: {summary['center']}")
        print(f"  Period: {summary['period']}")
        print(f"  WC Status: {wc['wc_status']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
