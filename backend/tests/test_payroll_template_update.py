"""
Test Australian Payroll Template Update (Iteration 61)
- Super rate: 12% (not 11.5%)
- Medicare threshold: $18,200 (tax-free threshold, not $26k)
- Reverse calculation: weekly annualization (net × 52) instead of hourly (rate × 1976)
- CSV export endpoint: /api/international-attendance/export/payroll-summary-csv
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPayrollTemplateUpdate:
    """Test updated Australian payroll calculation parameters"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        # Send OTP
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT"
        })
        assert otp_res.status_code == 200, f"Failed to send OTP: {otp_res.text}"
        
        # Verify OTP
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": "9741399190",
            "otp": "123456",
            "center": "PB-MGT"
        })
        assert verify_res.status_code == 200, f"Failed to verify OTP: {verify_res.text}"
        data = verify_res.json()
        self.token = data.get("token")
        assert self.token, "No token received"
        self.center = "PB-PERTH"
        self.year = 2026
        self.month = 1
    
    # ==========================================
    # Test 1: Super rate is 12% (not 11.5%)
    # ==========================================
    def test_super_rate_is_12_percent(self):
        """Verify payroll-report returns super_rate as '12.0%'"""
        res = requests.post(f"{BASE_URL}/api/international-attendance/payroll-report", json={
            "token": self.token,
            "center": self.center,
            "year": self.year,
            "month": self.month
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True
        assert "rates" in data, "Missing 'rates' in response"
        
        super_rate = data["rates"].get("super_rate")
        assert super_rate == "12.0%", f"Expected super_rate '12.0%', got '{super_rate}'"
        print(f"✓ Super rate is correctly set to {super_rate}")
    
    def test_medicare_rate_is_2_percent(self):
        """Verify payroll-report returns medicare_rate as '2.0%'"""
        res = requests.post(f"{BASE_URL}/api/international-attendance/payroll-report", json={
            "token": self.token,
            "center": self.center,
            "year": self.year,
            "month": self.month
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        medicare_rate = data["rates"].get("medicare_rate")
        assert medicare_rate == "2.0%", f"Expected medicare_rate '2.0%', got '{medicare_rate}'"
        print(f"✓ Medicare rate is correctly set to {medicare_rate}")
    
    # ==========================================
    # Test 2: Medicare applies above $18,200 (not $26k)
    # ==========================================
    def test_medicare_threshold_18200(self):
        """Verify Medicare applies to income above $18,200 (tax-free threshold)"""
        # Test with $20/hr × 38hrs = $760/week = $39,520 annual (above $18,200)
        res = requests.post(f"{BASE_URL}/api/international-attendance/reverse-payroll-calculate", json={
            "token": self.token,
            "target_takehome_hourly": 20.0,
            "hours_worked": 38
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        payroll = data.get("payroll", {})
        
        # Annual gross should be above $18,200, so Medicare should apply
        annual_gross = payroll.get("annual_gross_salary", 0)
        medicare_levy = payroll.get("medicare_levy", 0)
        
        assert annual_gross > 18200, f"Annual gross {annual_gross} should be > $18,200"
        assert medicare_levy > 0, f"Medicare levy should be > 0 for income above $18,200, got {medicare_levy}"
        print(f"✓ Medicare levy ${medicare_levy:.2f} applied for annual gross ${annual_gross:.2f}")
    
    def test_no_medicare_below_threshold(self):
        """Verify no Medicare for income below $18,200"""
        # Test with very low rate: $5/hr × 10hrs = $50/week = $2,600 annual (below $18,200)
        res = requests.post(f"{BASE_URL}/api/international-attendance/reverse-payroll-calculate", json={
            "token": self.token,
            "target_takehome_hourly": 5.0,
            "hours_worked": 10
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        payroll = data.get("payroll", {})
        
        annual_gross = payroll.get("annual_gross_salary", 0)
        medicare_levy = payroll.get("medicare_levy", 0)
        
        # Below $18,200 threshold - no Medicare
        if annual_gross <= 18200:
            assert medicare_levy == 0, f"Medicare should be $0 for income below $18,200, got ${medicare_levy}"
            print(f"✓ No Medicare levy for annual gross ${annual_gross:.2f} (below $18,200)")
        else:
            print(f"Note: Annual gross ${annual_gross:.2f} is above threshold, Medicare applies")
    
    # ==========================================
    # Test 3: Reverse calculation uses weekly annualization
    # ==========================================
    def test_weekly_annualization_calculation(self):
        """
        Verify reverse calculation uses weekly × 52 annualization.
        Example: $25/hr × 23hrs = $575 weekly net → $575 × 52 = $29,900 annual net
        Then reverse-calculate gross from this annual net.
        """
        target_rate = 25.0
        hours = 23.0
        expected_weekly_net = target_rate * hours  # $575
        expected_annual_net = expected_weekly_net * 52  # $29,900
        
        res = requests.post(f"{BASE_URL}/api/international-attendance/reverse-payroll-calculate", json={
            "token": self.token,
            "target_takehome_hourly": target_rate,
            "hours_worked": hours
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        payroll = data.get("payroll", {})
        
        # Verify net_pay matches expected weekly net
        net_pay = payroll.get("net_pay", 0)
        assert abs(net_pay - expected_weekly_net) < 1.0, \
            f"Expected weekly net ~${expected_weekly_net}, got ${net_pay}"
        
        # Verify annual_net is approximately weekly × 52
        annual_net = payroll.get("annual_net", 0)
        assert abs(annual_net - expected_annual_net) < 100, \
            f"Expected annual net ~${expected_annual_net}, got ${annual_net}"
        
        print(f"✓ Weekly annualization: ${target_rate}/hr × {hours}hrs = ${net_pay:.2f}/week")
        print(f"  Annual net: ${annual_net:.2f} (expected ~${expected_annual_net})")
    
    def test_gross_calculation_for_known_inputs(self):
        """
        Verify gross calculations for known inputs using weekly annualization.
        $25/hr take-home × 23hrs = $575 weekly net
        $575 × 52 = $29,900 annual net
        Reverse calculation: ~$32,912 annual gross → ~$632.93 weekly gross
        """
        res = requests.post(f"{BASE_URL}/api/international-attendance/reverse-payroll-calculate", json={
            "token": self.token,
            "target_takehome_hourly": 25.0,
            "hours_worked": 23.0
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        payroll = data.get("payroll", {})
        
        gross_pay = payroll.get("gross_pay", 0)
        payg_tax = payroll.get("payg_tax", 0)
        medicare_levy = payroll.get("medicare_levy", 0)
        total_deductions = payg_tax + medicare_levy
        net_pay = payroll.get("net_pay", 0)
        
        # Gross should be higher than net (575) due to tax
        assert gross_pay > 575, f"Gross ${gross_pay} should be > net $575"
        
        # Weekly annualization: $575 net × 52 = $29,900 annual net
        # Reverse calc gives ~$32,912 annual gross → ~$632.93 weekly gross
        assert 600 < gross_pay < 700, f"Expected gross ~$632.93, got ${gross_pay}"
        
        # Verify net_pay matches expected
        assert abs(net_pay - 575) < 1, f"Expected net $575, got ${net_pay}"
        
        print(f"✓ Gross calculation: ${gross_pay:.2f} gross for ${net_pay:.2f} net")
        print(f"  PAYG Tax: ${payg_tax:.2f}, Medicare: ${medicare_levy:.2f}")
        print(f"  Total deductions: ${total_deductions:.2f}")
    
    def test_super_calculated_at_12_percent(self):
        """Verify superannuation is calculated at 12% of gross"""
        res = requests.post(f"{BASE_URL}/api/international-attendance/reverse-payroll-calculate", json={
            "token": self.token,
            "target_takehome_hourly": 25.0,
            "hours_worked": 38
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        payroll = data.get("payroll", {})
        
        gross_pay = payroll.get("gross_pay", 0)
        superannuation = payroll.get("superannuation", 0)
        super_rate_pct = payroll.get("super_rate_pct", 0)
        
        # Verify super rate is 12%
        assert super_rate_pct == 12.0, f"Expected super_rate_pct 12.0, got {super_rate_pct}"
        
        # Verify super = gross × 12%
        expected_super = gross_pay * 0.12
        assert abs(superannuation - expected_super) < 0.1, \
            f"Expected super ${expected_super:.2f}, got ${superannuation:.2f}"
        
        print(f"✓ Super at 12%: ${superannuation:.2f} (12% of ${gross_pay:.2f})")
    
    # ==========================================
    # Test 4: CSV Export Endpoint
    # ==========================================
    def test_csv_export_endpoint_exists(self):
        """Verify /api/international-attendance/export/payroll-summary-csv returns 200"""
        res = requests.post(f"{BASE_URL}/api/international-attendance/export/payroll-summary-csv", json={
            "token": self.token,
            "center": self.center,
            "year": self.year,
            "month": self.month
        })
        assert res.status_code == 200, f"CSV export failed with status {res.status_code}: {res.text}"
        
        # Verify content type is CSV
        content_type = res.headers.get("Content-Type", "")
        assert "text/csv" in content_type, f"Expected text/csv, got {content_type}"
        
        print(f"✓ CSV export endpoint returns 200 with Content-Type: {content_type}")
    
    def test_csv_export_has_valid_content(self):
        """Verify CSV export contains valid CSV content"""
        res = requests.post(f"{BASE_URL}/api/international-attendance/export/payroll-summary-csv", json={
            "token": self.token,
            "center": self.center,
            "year": self.year,
            "month": self.month
        })
        assert res.status_code == 200
        
        content = res.text
        assert len(content) > 0, "CSV content is empty"
        
        # Check for expected headers/sections
        assert "Payroll Summary" in content, "Missing 'Payroll Summary' header"
        assert "Super Rate" in content or "12.0%" in content, "Missing super rate info"
        
        print(f"✓ CSV export has valid content ({len(content)} bytes)")
    
    def test_csv_export_has_employee_section(self):
        """Verify CSV export includes Employee Payroll section"""
        res = requests.post(f"{BASE_URL}/api/international-attendance/export/payroll-summary-csv", json={
            "token": self.token,
            "center": self.center,
            "year": self.year,
            "month": self.month
        })
        assert res.status_code == 200
        
        content = res.text
        
        # Check for employee payroll columns
        assert "Employee" in content, "Missing 'Employee' column"
        assert "Category" in content, "Missing 'Category' column"
        assert "Net Pay" in content or "Net" in content, "Missing 'Net Pay' column"
        assert "Gross" in content, "Missing 'Gross' column"
        
        print(f"✓ CSV export includes Employee Payroll section")
    
    def test_csv_export_has_weekly_breakdown(self):
        """Verify CSV export includes Weekly Organization Cost Breakdown section"""
        res = requests.post(f"{BASE_URL}/api/international-attendance/export/payroll-summary-csv", json={
            "token": self.token,
            "center": self.center,
            "year": self.year,
            "month": self.month
        })
        assert res.status_code == 200
        
        content = res.text
        
        # Check for weekly breakdown section
        assert "Weekly Organization Cost Breakdown" in content, \
            "Missing 'Weekly Organization Cost Breakdown' section"
        assert "Week" in content, "Missing 'Week' column"
        assert "Employer Cost" in content, "Missing 'Employer Cost' column"
        
        print(f"✓ CSV export includes Weekly Organization Cost Breakdown section")
    
    def test_csv_export_filename(self):
        """Verify CSV export has correct filename in Content-Disposition"""
        res = requests.post(f"{BASE_URL}/api/international-attendance/export/payroll-summary-csv", json={
            "token": self.token,
            "center": self.center,
            "year": self.year,
            "month": self.month
        })
        assert res.status_code == 200
        
        content_disp = res.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, "Missing attachment disposition"
        assert ".csv" in content_disp, "Missing .csv extension in filename"
        assert self.center in content_disp, f"Missing center {self.center} in filename"
        
        print(f"✓ CSV export filename: {content_disp}")
    
    # ==========================================
    # Test 5: Verify rates in payroll-report response
    # ==========================================
    def test_payroll_report_rates_structure(self):
        """Verify payroll-report returns correct rates structure"""
        res = requests.post(f"{BASE_URL}/api/international-attendance/payroll-report", json={
            "token": self.token,
            "center": self.center,
            "year": self.year,
            "month": self.month
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        rates = data.get("rates", {})
        
        # Verify all expected rate fields
        assert "super_rate" in rates, "Missing super_rate in rates"
        assert "medicare_rate" in rates, "Missing medicare_rate in rates"
        
        # Verify values
        assert rates["super_rate"] == "12.0%", f"Expected super_rate '12.0%', got '{rates['super_rate']}'"
        assert rates["medicare_rate"] == "2.0%", f"Expected medicare_rate '2.0%', got '{rates['medicare_rate']}'"
        
        print(f"✓ Payroll report rates: super={rates['super_rate']}, medicare={rates['medicare_rate']}")


class TestEmployeeGrossRateCalculation:
    """Test gross rate calculation for employees with take-home rates"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT"
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": "9741399190",
            "otp": "123456",
            "center": "PB-MGT"
        })
        self.token = verify_res.json().get("token")
        self.center = "PB-PERTH"
    
    def test_employees_have_gross_hourly_rate(self):
        """Verify employees endpoint returns gross_hourly_rate"""
        res = requests.post(f"{BASE_URL}/api/international-attendance/employees", json={
            "token": self.token,
            "center": self.center
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        employees = data.get("employees", [])
        assert len(employees) > 0, "No employees found"
        
        for emp in employees:
            assert "gross_hourly_rate" in emp, f"Missing gross_hourly_rate for {emp.get('name')}"
            assert "target_takehome_rate" in emp, f"Missing target_takehome_rate for {emp.get('name')}"
            
            # If take-home rate > 0, gross should be >= take-home
            takehome = emp.get("target_takehome_rate", 0)
            gross = emp.get("gross_hourly_rate", 0)
            if takehome > 0:
                assert gross >= takehome, \
                    f"Gross ${gross} should be >= take-home ${takehome} for {emp.get('name')}"
        
        print(f"✓ All {len(employees)} employees have gross_hourly_rate field")
    
    def test_standard_38hr_week_gross_calculation(self):
        """
        Verify gross calculation for 38-hour standard week.
        $25/hr take-home × 38hrs = $950/week net → $49,400 annual net
        Expected gross ~$59,100 annual → ~$29.91/hr gross
        """
        res = requests.post(f"{BASE_URL}/api/international-attendance/reverse-payroll-calculate", json={
            "token": self.token,
            "target_takehome_hourly": 25.0,
            "hours_worked": 38
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        payroll = data.get("payroll", {})
        
        gross_hourly = payroll.get("gross_hourly_rate", 0)
        annual_gross = payroll.get("annual_gross_salary", 0)
        
        # Expected: ~$29.91/hr gross for $25/hr take-home at 38hrs/week
        assert 28 < gross_hourly < 35, f"Expected gross hourly ~$29.91, got ${gross_hourly}"
        
        # Annual gross should be around $59,100
        assert 55000 < annual_gross < 65000, f"Expected annual gross ~$59,100, got ${annual_gross}"
        
        print(f"✓ 38hr week: ${gross_hourly:.2f}/hr gross for $25/hr take-home")
        print(f"  Annual gross: ${annual_gross:.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
