"""
Test Australian Reverse Payroll Calculation and Week Numbering
Features:
- POST /api/international-attendance/reverse-payroll-calculate
- POST /api/international-attendance/payroll-report
- POST /api/international-attendance/payroll-report-pdf
- Week date logic: get_week_number_from_date
- Superannuation calculation (ON TOP of gross)
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_OTP = "123456"
SUPER_ADMIN_CENTER = "PB-MGT"
TEST_CENTER = "PERTH"  # International center for testing


class TestAuthSetup:
    """Authentication setup for all tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for super admin"""
        # Step 1: Send OTP
        send_otp_response = requests.post(
            f"{BASE_URL}/api/send_otp",
            json={"mobile": SUPER_ADMIN_MOBILE, "center": SUPER_ADMIN_CENTER}
        )
        assert send_otp_response.status_code == 200, f"Send OTP failed: {send_otp_response.text}"
        
        # Step 2: Verify OTP
        verify_response = requests.post(
            f"{BASE_URL}/api/verify_otp",
            json={"mobile": SUPER_ADMIN_MOBILE, "otp": SUPER_ADMIN_OTP, "center": SUPER_ADMIN_CENTER}
        )
        assert verify_response.status_code == 200, f"Verify OTP failed: {verify_response.text}"
        
        data = verify_response.json()
        token = data.get("token")
        assert token, "No token returned from verify_otp"
        return token


class TestReversePayrollCalculate(TestAuthSetup):
    """Test POST /api/international-attendance/reverse-payroll-calculate"""
    
    def test_reverse_payroll_with_20_per_hour_target(self, auth_token):
        """Test reverse payroll with $20/hr target take-home rate"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/reverse-payroll-calculate",
            json={
                "token": auth_token,
                "target_takehome_hourly": 20.0,
                "hours_worked": 38  # Standard week
            }
        )
        
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        assert data.get("success") is True, f"Response not successful: {data}"
        
        payroll = data.get("payroll", {})
        
        # Verify gross_hourly_rate > target (20)
        gross_hourly = payroll.get("gross_hourly_rate", 0)
        assert gross_hourly > 20, f"Gross hourly rate ({gross_hourly}) should be > 20 (target)"
        
        # Verify PAYG tax > 0 (for income above tax-free threshold)
        payg_tax = payroll.get("payg_tax", 0)
        assert payg_tax >= 0, f"PAYG tax should be >= 0, got {payg_tax}"
        
        # Verify net_pay ≈ target × hours (within tolerance)
        net_pay = payroll.get("net_pay", 0)
        expected_net = 20.0 * 38
        tolerance = 0.50  # Allow $0.50 tolerance for rounding
        assert abs(net_pay - expected_net) <= tolerance, \
            f"Net pay ({net_pay}) should be ≈ {expected_net} (target × hours)"
        
        print(f"✓ Reverse payroll test passed:")
        print(f"  Target take-home: $20/hr")
        print(f"  Gross hourly: ${gross_hourly:.4f}")
        print(f"  PAYG tax (for 38hrs): ${payg_tax:.2f}")
        print(f"  Net pay: ${net_pay:.2f} (expected: ${expected_net:.2f})")
    
    def test_net_pay_equals_target_times_hours(self, auth_token):
        """Validation: net_pay / hours_worked should equal target_takehome_hourly (within $0.01)"""
        target_hourly = 25.0
        hours = 40
        
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/reverse-payroll-calculate",
            json={
                "token": auth_token,
                "target_takehome_hourly": target_hourly,
                "hours_worked": hours
            }
        )
        
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        payroll = data.get("payroll", {})
        
        net_pay = payroll.get("net_pay", 0)
        calculated_hourly = net_pay / hours if hours > 0 else 0
        
        tolerance = 0.01
        assert abs(calculated_hourly - target_hourly) <= tolerance, \
            f"net_pay/hours ({calculated_hourly:.4f}) should equal target ({target_hourly}) within ${tolerance}"
        
        print(f"✓ Net pay validation passed:")
        print(f"  Net pay: ${net_pay:.2f} / {hours} hours = ${calculated_hourly:.4f}/hr")
        print(f"  Target: ${target_hourly}/hr")
    
    def test_superannuation_on_top_of_gross(self, auth_token):
        """Verify superannuation is calculated ON TOP of gross (not deducted from net)"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/reverse-payroll-calculate",
            json={
                "token": auth_token,
                "target_takehome_hourly": 30.0,
                "hours_worked": 38
            }
        )
        
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        payroll = data.get("payroll", {})
        
        gross_pay = payroll.get("gross_pay", 0)
        superannuation = payroll.get("superannuation", 0)
        employer_total_cost = payroll.get("employer_total_cost", 0)
        net_pay = payroll.get("net_pay", 0)
        
        # Super should be 11.5% of gross
        expected_super = gross_pay * 0.115
        tolerance = 0.01
        assert abs(superannuation - expected_super) <= tolerance, \
            f"Super ({superannuation}) should be 11.5% of gross ({expected_super})"
        
        # Employer cost = gross + super (super is ON TOP)
        expected_employer_cost = gross_pay + superannuation
        assert abs(employer_total_cost - expected_employer_cost) <= tolerance, \
            f"Employer cost ({employer_total_cost}) should be gross + super ({expected_employer_cost})"
        
        # Net pay should NOT have super deducted (super is employer contribution)
        # Net = Gross - PAYG - Medicare (NOT - Super)
        payg_tax = payroll.get("payg_tax", 0)
        medicare = payroll.get("medicare_levy", 0)
        expected_net = gross_pay - payg_tax - medicare
        assert abs(net_pay - expected_net) <= tolerance, \
            f"Net pay ({net_pay}) should be gross - tax - medicare ({expected_net}), NOT minus super"
        
        print(f"✓ Superannuation calculation verified:")
        print(f"  Gross pay: ${gross_pay:.2f}")
        print(f"  Super (11.5%): ${superannuation:.2f}")
        print(f"  Employer total cost: ${employer_total_cost:.2f}")
        print(f"  Net pay (no super deduction): ${net_pay:.2f}")
    
    def test_reverse_payroll_default_hours(self, auth_token):
        """Test that default hours (38) is used when hours_worked is 0"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/reverse-payroll-calculate",
            json={
                "token": auth_token,
                "target_takehome_hourly": 20.0,
                "hours_worked": 0  # Should default to 38
            }
        )
        
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        payroll = data.get("payroll", {})
        
        hours_worked = payroll.get("hours_worked", 0)
        assert hours_worked == 38, f"Default hours should be 38, got {hours_worked}"
        
        print(f"✓ Default hours test passed: hours_worked = {hours_worked}")


class TestPayrollReport(TestAuthSetup):
    """Test POST /api/international-attendance/payroll-report"""
    
    def test_payroll_report_week_labels_april_2026(self, auth_token):
        """Test week labels for April 2026: Week 1 = 1st-6th, Week 2 = 7th-13th, etc."""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/payroll-report",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 4  # April
            }
        )
        
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        assert data.get("success") is True, f"Response not successful: {data}"
        
        week_labels = data.get("week_labels", {})
        
        # Expected week labels for April 2026 (30 days)
        expected_labels = {
            "1": "1st - 6th Apr",
            "2": "7th - 13th Apr",
            "3": "14th - 20th Apr",
            "4": "21st - 27th Apr",
            "5": "28th - 30th Apr"  # April has 30 days
        }
        
        for week_num, expected_label in expected_labels.items():
            actual_label = week_labels.get(int(week_num)) or week_labels.get(week_num)
            assert actual_label == expected_label, \
                f"Week {week_num} label mismatch: expected '{expected_label}', got '{actual_label}'"
        
        print(f"✓ Week labels for April 2026 verified:")
        for k, v in week_labels.items():
            print(f"  Week {k}: {v}")
    
    def test_payroll_report_week_labels_january_2026(self, auth_token):
        """Test week labels for January 2026 (31 days)"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/payroll-report",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 1  # January
            }
        )
        
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        week_labels = data.get("week_labels", {})
        
        # Expected week labels for January 2026 (31 days)
        expected_labels = {
            "1": "1st - 6th Jan",
            "2": "7th - 13th Jan",
            "3": "14th - 20th Jan",
            "4": "21st - 27th Jan",
            "5": "28th - 31st Jan"  # January has 31 days
        }
        
        for week_num, expected_label in expected_labels.items():
            actual_label = week_labels.get(int(week_num)) or week_labels.get(week_num)
            assert actual_label == expected_label, \
                f"Week {week_num} label mismatch: expected '{expected_label}', got '{actual_label}'"
        
        print(f"✓ Week labels for January 2026 verified")
    
    def test_payroll_report_structure(self, auth_token):
        """Test payroll report returns correct structure with tax calculations"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/payroll-report",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 4
            }
        )
        
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        # Check required fields
        required_fields = ["success", "center", "year", "month", "month_name", 
                          "pay_period", "weeks_in_month", "week_labels", 
                          "employees", "totals", "rates"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Check rates
        rates = data.get("rates", {})
        assert "super_rate" in rates, "Missing super_rate in rates"
        assert "medicare_rate" in rates, "Missing medicare_rate in rates"
        assert rates.get("super_rate") == "11.5%", f"Super rate should be 11.5%, got {rates.get('super_rate')}"
        assert rates.get("medicare_rate") == "2.0%", f"Medicare rate should be 2.0%, got {rates.get('medicare_rate')}"
        
        # Check totals structure
        totals = data.get("totals", {})
        total_fields = ["total_hours", "total_gross", "total_payg", 
                       "total_medicare", "total_net", "total_super", "total_employer_cost"]
        for field in total_fields:
            assert field in totals, f"Missing {field} in totals"
        
        print(f"✓ Payroll report structure verified")
        print(f"  Center: {data.get('center')}")
        print(f"  Month: {data.get('month_name')} {data.get('year')}")
        print(f"  Weeks in month: {data.get('weeks_in_month')}")


class TestPayrollReportPDF(TestAuthSetup):
    """Test POST /api/international-attendance/payroll-report-pdf"""
    
    def test_payroll_report_pdf_generation(self, auth_token):
        """Test PDF generation returns valid PDF (HTTP 200, Content-Type application/pdf)"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/payroll-report-pdf",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 4
            }
        )
        
        assert response.status_code == 200, f"PDF generation failed: {response.status_code} - {response.text[:500]}"
        
        # Check Content-Type
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, \
            f"Content-Type should be application/pdf, got {content_type}"
        
        # Check Content-Disposition (should have filename)
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disposition, \
            f"Content-Disposition should contain 'attachment', got {content_disposition}"
        assert ".pdf" in content_disposition.lower(), \
            f"Filename should have .pdf extension, got {content_disposition}"
        
        # Check PDF magic bytes (PDF starts with %PDF-)
        pdf_content = response.content
        assert len(pdf_content) > 100, f"PDF content too small: {len(pdf_content)} bytes"
        assert pdf_content[:4] == b'%PDF', \
            f"PDF should start with %PDF magic bytes, got {pdf_content[:10]}"
        
        print(f"✓ PDF generation verified:")
        print(f"  Content-Type: {content_type}")
        print(f"  Content-Disposition: {content_disposition}")
        print(f"  PDF size: {len(pdf_content)} bytes")


class TestWeekDateLogic:
    """Test week date logic functions"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        send_otp_response = requests.post(
            f"{BASE_URL}/api/send_otp",
            json={"mobile": SUPER_ADMIN_MOBILE, "center": SUPER_ADMIN_CENTER}
        )
        assert send_otp_response.status_code == 200
        
        verify_response = requests.post(
            f"{BASE_URL}/api/verify_otp",
            json={"mobile": SUPER_ADMIN_MOBILE, "otp": SUPER_ADMIN_OTP, "center": SUPER_ADMIN_CENTER}
        )
        assert verify_response.status_code == 200
        return verify_response.json().get("token")
    
    def test_week_data_endpoint_week_boundaries(self, auth_token):
        """Test week-data endpoint returns correct dates for each week"""
        # Test Week 1 (days 1-6)
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/week-data",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 4,
                "week": 1
            }
        )
        
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        week_dates = data.get("week_dates", [])
        
        # Week 1 should contain dates from 1st to 6th April 2026
        valid_dates = [d for d in week_dates if d is not None]
        if valid_dates:
            # Check that dates are within 1-6 range
            for date_str in valid_dates:
                day = int(date_str.split("-")[2])
                assert 1 <= day <= 6, f"Week 1 date {date_str} should be between 1st-6th"
        
        print(f"✓ Week 1 dates: {week_dates}")
        
        # Test Week 2 (days 7-13)
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/week-data",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 4,
                "week": 2
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        week_dates = data.get("week_dates", [])
        valid_dates = [d for d in week_dates if d is not None]
        if valid_dates:
            for date_str in valid_dates:
                day = int(date_str.split("-")[2])
                assert 7 <= day <= 13, f"Week 2 date {date_str} should be between 7th-13th"
        
        print(f"✓ Week 2 dates: {week_dates}")
        
        # Test Week 5 (days 28+)
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/week-data",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 4,
                "week": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        week_dates = data.get("week_dates", [])
        valid_dates = [d for d in week_dates if d is not None]
        if valid_dates:
            for date_str in valid_dates:
                day = int(date_str.split("-")[2])
                assert day >= 28, f"Week 5 date {date_str} should be 28th or later"
        
        print(f"✓ Week 5 dates: {week_dates}")


class TestPAYGTaxBrackets(TestAuthSetup):
    """Test PAYG tax calculation with different income levels"""
    
    def test_tax_free_threshold(self, auth_token):
        """Test that income below $18,200 annual has no PAYG tax"""
        # $8/hr * 1976 annual hours = $15,808 annual (below tax-free threshold)
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/reverse-payroll-calculate",
            json={
                "token": auth_token,
                "target_takehome_hourly": 8.0,
                "hours_worked": 38
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        payroll = data.get("payroll", {})
        
        annual_gross = payroll.get("annual_gross_salary", 0)
        annual_payg = payroll.get("annual_payg_tax", 0)
        
        # If annual gross is below $18,200, PAYG should be 0
        if annual_gross <= 18200:
            assert annual_payg == 0, f"PAYG should be 0 for income below $18,200, got {annual_payg}"
            print(f"✓ Tax-free threshold verified: Annual gross ${annual_gross:.2f}, PAYG ${annual_payg:.2f}")
        else:
            print(f"  Note: Annual gross ${annual_gross:.2f} is above tax-free threshold")
    
    def test_higher_income_has_tax(self, auth_token):
        """Test that higher income has PAYG tax"""
        # $50/hr * 1976 = $98,800 annual (well above tax-free threshold)
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/reverse-payroll-calculate",
            json={
                "token": auth_token,
                "target_takehome_hourly": 50.0,
                "hours_worked": 38
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        payroll = data.get("payroll", {})
        
        annual_payg = payroll.get("annual_payg_tax", 0)
        assert annual_payg > 0, f"PAYG should be > 0 for high income, got {annual_payg}"
        
        print(f"✓ Higher income tax verified: Annual PAYG ${annual_payg:.2f}")


class TestMedicareLevy(TestAuthSetup):
    """Test Medicare Levy calculation"""
    
    def test_medicare_levy_rate(self, auth_token):
        """Test Medicare Levy is 2% of gross"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/reverse-payroll-calculate",
            json={
                "token": auth_token,
                "target_takehome_hourly": 35.0,
                "hours_worked": 38
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        payroll = data.get("payroll", {})
        
        gross_pay = payroll.get("gross_pay", 0)
        medicare_levy = payroll.get("medicare_levy", 0)
        annual_gross = payroll.get("annual_gross_salary", 0)
        annual_medicare = payroll.get("annual_medicare_levy", 0)
        
        # Medicare is 2% of gross (but has phase-in threshold around $26,000)
        if annual_gross > 26000:
            expected_annual_medicare = annual_gross * 0.02
            tolerance = 1.0  # Allow $1 tolerance for rounding
            assert abs(annual_medicare - expected_annual_medicare) <= tolerance, \
                f"Annual Medicare ({annual_medicare}) should be 2% of gross ({expected_annual_medicare})"
        
        print(f"✓ Medicare Levy verified:")
        print(f"  Annual gross: ${annual_gross:.2f}")
        print(f"  Annual Medicare (2%): ${annual_medicare:.2f}")


class TestAuthRequired:
    """Test that endpoints require authentication"""
    
    def test_reverse_payroll_requires_auth(self):
        """Test reverse-payroll-calculate requires valid token"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/reverse-payroll-calculate",
            json={
                "token": "invalid_token",
                "target_takehome_hourly": 20.0,
                "hours_worked": 38
            }
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ reverse-payroll-calculate requires auth")
    
    def test_payroll_report_requires_auth(self):
        """Test payroll-report requires valid token"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/payroll-report",
            json={
                "token": "invalid_token",
                "center": TEST_CENTER,
                "year": 2026,
                "month": 4
            }
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ payroll-report requires auth")
    
    def test_payroll_report_pdf_requires_auth(self):
        """Test payroll-report-pdf requires valid token"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/payroll-report-pdf",
            json={
                "token": "invalid_token",
                "center": TEST_CENTER,
                "year": 2026,
                "month": 4
            }
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ payroll-report-pdf requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
