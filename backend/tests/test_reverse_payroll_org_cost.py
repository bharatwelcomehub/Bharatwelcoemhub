"""
Test Australian Reverse Payroll - Organization Cost Features (Iteration 60)
Features:
- GET /api/international-attendance/week-data returns target_takehome_rate and gross_hourly_rate
- POST /api/international-attendance/payroll-report returns weekly_totals (per-week org cost breakdown)
- POST /api/international-attendance/payroll-report returns per-employee employer_total_cost and weekly_costs
- POST /api/international-attendance/payroll-report returns totals.total_employer_cost
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_OTP = "123456"
SUPER_ADMIN_CENTER = "PB-MGT"
TEST_CENTER = "PB-PERTH"  # International center with employees


class TestOrgCostFeatures:
    """Test organization cost features in reverse payroll"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for super admin"""
        send_otp_response = requests.post(
            f"{BASE_URL}/api/send_otp",
            json={"mobile": SUPER_ADMIN_MOBILE, "center": SUPER_ADMIN_CENTER}
        )
        assert send_otp_response.status_code == 200, f"Send OTP failed: {send_otp_response.text}"
        
        verify_response = requests.post(
            f"{BASE_URL}/api/verify_otp",
            json={"mobile": SUPER_ADMIN_MOBILE, "otp": SUPER_ADMIN_OTP, "center": SUPER_ADMIN_CENTER}
        )
        assert verify_response.status_code == 200, f"Verify OTP failed: {verify_response.text}"
        
        data = verify_response.json()
        token = data.get("token")
        assert token, "No token returned from verify_otp"
        return token

    # ==========================================
    # Test week-data endpoint returns rates
    # ==========================================
    
    def test_week_data_returns_target_takehome_rate(self, auth_token):
        """Test that week-data endpoint returns target_takehome_rate for each employee"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/week-data",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 1,
                "week": 1
            }
        )
        
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        assert data.get("success") is True, f"Response not successful: {data}"
        
        employees = data.get("employees", [])
        print(f"Found {len(employees)} employees in {TEST_CENTER}")
        
        # Check that each employee has target_takehome_rate field
        for emp in employees:
            assert "target_takehome_rate" in emp, \
                f"Employee {emp.get('employee_name')} missing target_takehome_rate field"
            # Value can be 0 if not set, but field must exist
            assert isinstance(emp["target_takehome_rate"], (int, float)), \
                f"target_takehome_rate should be numeric, got {type(emp['target_takehome_rate'])}"
        
        print(f"✓ week-data returns target_takehome_rate for all {len(employees)} employees")
    
    def test_week_data_returns_gross_hourly_rate(self, auth_token):
        """Test that week-data endpoint returns gross_hourly_rate for each employee"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/week-data",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 1,
                "week": 1
            }
        )
        
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        employees = data.get("employees", [])
        
        # Check that each employee has gross_hourly_rate field
        for emp in employees:
            assert "gross_hourly_rate" in emp, \
                f"Employee {emp.get('employee_name')} missing gross_hourly_rate field"
            assert isinstance(emp["gross_hourly_rate"], (int, float)), \
                f"gross_hourly_rate should be numeric, got {type(emp['gross_hourly_rate'])}"
        
        print(f"✓ week-data returns gross_hourly_rate for all {len(employees)} employees")
    
    def test_week_data_gross_rate_greater_than_net_rate(self, auth_token):
        """Test that gross_hourly_rate > target_takehome_rate (when rate > 0)"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/week-data",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 1,
                "week": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        employees = data.get("employees", [])
        
        for emp in employees:
            net_rate = emp.get("target_takehome_rate", 0)
            gross_rate = emp.get("gross_hourly_rate", 0)
            
            if net_rate > 0:
                # Gross should be higher than net (to account for tax/medicare)
                assert gross_rate >= net_rate, \
                    f"Employee {emp.get('employee_name')}: gross ({gross_rate}) should be >= net ({net_rate})"
        
        print(f"✓ gross_hourly_rate >= target_takehome_rate for all employees with rates > 0")

    # ==========================================
    # Test payroll-report returns weekly_totals
    # ==========================================
    
    def test_payroll_report_returns_weekly_totals(self, auth_token):
        """Test that payroll-report returns weekly_totals with per-week org cost breakdown"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/payroll-report",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 1
            }
        )
        
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        assert data.get("success") is True, f"Response not successful: {data}"
        
        # Check weekly_totals exists
        assert "weekly_totals" in data, "Missing weekly_totals in payroll-report response"
        weekly_totals = data.get("weekly_totals", {})
        
        weeks_in_month = data.get("weeks_in_month", 5)
        
        # Check each week has the required fields
        for w in range(1, weeks_in_month + 1):
            week_data = weekly_totals.get(w) or weekly_totals.get(str(w))
            assert week_data is not None, f"Missing weekly_totals for week {w}"
            
            required_fields = ["hours", "gross", "net", "super", "employer_cost"]
            for field in required_fields:
                assert field in week_data, f"Week {w} missing field: {field}"
                assert isinstance(week_data[field], (int, float)), \
                    f"Week {w} {field} should be numeric, got {type(week_data[field])}"
        
        print(f"✓ payroll-report returns weekly_totals with {weeks_in_month} weeks")
        for w in range(1, min(3, weeks_in_month + 1)):  # Print first 2 weeks
            wt = weekly_totals.get(w) or weekly_totals.get(str(w))
            print(f"  Week {w}: hours={wt['hours']}, gross=${wt['gross']:.2f}, employer_cost=${wt['employer_cost']:.2f}")
    
    def test_payroll_report_weekly_totals_employer_cost_calculation(self, auth_token):
        """Test that weekly employer_cost = gross + super"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/payroll-report",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        weekly_totals = data.get("weekly_totals", {})
        
        for w_key, wt in weekly_totals.items():
            gross = wt.get("gross", 0)
            super_amount = wt.get("super", 0)
            employer_cost = wt.get("employer_cost", 0)
            
            expected_employer_cost = gross + super_amount
            tolerance = 0.02  # Allow small rounding tolerance
            
            assert abs(employer_cost - expected_employer_cost) <= tolerance, \
                f"Week {w_key}: employer_cost ({employer_cost}) should equal gross ({gross}) + super ({super_amount}) = {expected_employer_cost}"
        
        print(f"✓ weekly_totals employer_cost = gross + super verified")

    # ==========================================
    # Test payroll-report returns per-employee costs
    # ==========================================
    
    def test_payroll_report_employee_has_employer_total_cost(self, auth_token):
        """Test that each employee in payroll-report has employer_total_cost"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/payroll-report",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        employees = data.get("employees", [])
        
        for emp in employees:
            assert "employer_total_cost" in emp, \
                f"Employee {emp.get('employee_name')} missing employer_total_cost"
            assert isinstance(emp["employer_total_cost"], (int, float)), \
                f"employer_total_cost should be numeric"
        
        print(f"✓ All {len(employees)} employees have employer_total_cost field")
    
    def test_payroll_report_employee_has_weekly_costs(self, auth_token):
        """Test that each employee in payroll-report has weekly_costs breakdown"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/payroll-report",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        employees = data.get("employees", [])
        weeks_in_month = data.get("weeks_in_month", 5)
        
        for emp in employees:
            assert "weekly_costs" in emp, \
                f"Employee {emp.get('employee_name')} missing weekly_costs"
            
            weekly_costs = emp.get("weekly_costs", {})
            
            # Check each week has cost breakdown
            for w in range(1, weeks_in_month + 1):
                week_cost = weekly_costs.get(w) or weekly_costs.get(str(w))
                assert week_cost is not None, \
                    f"Employee {emp.get('employee_name')} missing weekly_costs for week {w}"
                
                # Each week should have these fields
                required_fields = ["hours", "gross", "net", "employer_cost"]
                for field in required_fields:
                    assert field in week_cost, \
                        f"Employee {emp.get('employee_name')} week {w} missing {field}"
        
        print(f"✓ All {len(employees)} employees have weekly_costs with {weeks_in_month} weeks")

    # ==========================================
    # Test payroll-report totals.total_employer_cost
    # ==========================================
    
    def test_payroll_report_totals_has_total_employer_cost(self, auth_token):
        """Test that payroll-report totals includes total_employer_cost"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/payroll-report",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        totals = data.get("totals", {})
        assert "total_employer_cost" in totals, "Missing total_employer_cost in totals"
        assert isinstance(totals["total_employer_cost"], (int, float)), \
            "total_employer_cost should be numeric"
        
        print(f"✓ totals.total_employer_cost = ${totals['total_employer_cost']:.2f}")
    
    def test_payroll_report_total_employer_cost_equals_sum_of_employees(self, auth_token):
        """Test that totals.total_employer_cost equals sum of all employee employer_total_cost"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/payroll-report",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        employees = data.get("employees", [])
        totals = data.get("totals", {})
        
        # Sum up all employee employer_total_cost
        sum_employee_costs = sum(emp.get("employer_total_cost", 0) for emp in employees)
        total_employer_cost = totals.get("total_employer_cost", 0)
        
        tolerance = 0.05  # Allow small rounding tolerance
        assert abs(total_employer_cost - sum_employee_costs) <= tolerance, \
            f"total_employer_cost ({total_employer_cost}) should equal sum of employee costs ({sum_employee_costs})"
        
        print(f"✓ total_employer_cost ({total_employer_cost:.2f}) = sum of employee costs ({sum_employee_costs:.2f})")
    
    def test_payroll_report_total_employer_cost_equals_gross_plus_super(self, auth_token):
        """Test that total_employer_cost = total_gross + total_super"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/payroll-report",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "year": 2026,
                "month": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        totals = data.get("totals", {})
        total_gross = totals.get("total_gross", 0)
        total_super = totals.get("total_super", 0)
        total_employer_cost = totals.get("total_employer_cost", 0)
        
        expected = total_gross + total_super
        tolerance = 0.05
        
        assert abs(total_employer_cost - expected) <= tolerance, \
            f"total_employer_cost ({total_employer_cost}) should equal total_gross ({total_gross}) + total_super ({total_super}) = {expected}"
        
        print(f"✓ total_employer_cost = total_gross + total_super verified")
        print(f"  total_gross: ${total_gross:.2f}")
        print(f"  total_super: ${total_super:.2f}")
        print(f"  total_employer_cost: ${total_employer_cost:.2f}")

    # ==========================================
    # Test employees endpoint returns rates
    # ==========================================
    
    def test_employees_endpoint_returns_rates(self, auth_token):
        """Test that /employees endpoint returns target_takehome_rate and gross_hourly_rate"""
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/employees",
            json={
                "token": auth_token,
                "center": TEST_CENTER
            }
        )
        
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        assert data.get("success") is True
        
        employees = data.get("employees", [])
        print(f"Found {len(employees)} employees")
        
        for emp in employees:
            assert "target_takehome_rate" in emp, \
                f"Employee {emp.get('name')} missing target_takehome_rate"
            assert "gross_hourly_rate" in emp, \
                f"Employee {emp.get('name')} missing gross_hourly_rate"
        
        print(f"✓ /employees endpoint returns both rate fields for all {len(employees)} employees")


class TestUpdateRateEndpoint:
    """Test update-rate endpoint for editing take-home hourly rate"""
    
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
    
    def test_update_rate_endpoint_exists(self, auth_token):
        """Test that update-rate endpoint exists and accepts requests"""
        # First get an employee ID
        emp_response = requests.post(
            f"{BASE_URL}/api/international-attendance/employees",
            json={"token": auth_token, "center": TEST_CENTER}
        )
        
        if emp_response.status_code != 200:
            pytest.skip("Could not get employees")
        
        employees = emp_response.json().get("employees", [])
        if not employees:
            pytest.skip("No employees found in test center")
        
        emp_id = employees[0].get("employee_id")
        current_rate = employees[0].get("hourly_rate", 0)
        
        # Try to update rate (use same rate to avoid changing data)
        response = requests.post(
            f"{BASE_URL}/api/international-attendance/update-rate",
            json={
                "token": auth_token,
                "center": TEST_CENTER,
                "employee_id": emp_id,
                "new_rate": current_rate
            }
        )
        
        assert response.status_code == 200, f"update-rate failed: {response.text}"
        data = response.json()
        assert data.get("success") is True, f"update-rate not successful: {data}"
        
        print(f"✓ update-rate endpoint works for employee {emp_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
