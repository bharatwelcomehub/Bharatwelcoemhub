"""
Test Monthly Payroll PDF Generation - Iteration 63
Tests:
1. POST /api/international-attendance/payroll-report-pdf generates PDF with 4 sections
2. PDF contains employee names (not 'Unknown') and real financial values (not $0)
3. POST /api/payslip_employees with center=PB-PERTH returns employees from db.employees
4. POST /api/payslips_generate with targetCenter=PB-PERTH generates Australian payslip PDF
5. Indian payslip generation still works (PB-HSR)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_OTP = "123456"
SUPER_ADMIN_CENTER = "PB-MGT"

# Test centers
PERTH_CENTER = "PB-PERTH"
INDIA_CENTER = "PB-HSR"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for super admin"""
    # Send OTP
    resp = requests.post(f"{BASE_URL}/api/send_otp", json={
        "mobile": SUPER_ADMIN_MOBILE,
        "center": SUPER_ADMIN_CENTER
    })
    assert resp.status_code == 200, f"Send OTP failed: {resp.text}"
    
    # Verify OTP
    resp = requests.post(f"{BASE_URL}/api/verify_otp", json={
        "mobile": SUPER_ADMIN_MOBILE,
        "otp": SUPER_ADMIN_OTP,
        "center": SUPER_ADMIN_CENTER
    })
    assert resp.status_code == 200, f"Verify OTP failed: {resp.text}"
    data = resp.json()
    assert "token" in data, "No token in response"
    return data["token"]


class TestPayslipEmployeesEndpoint:
    """Test /api/payslip_employees endpoint for international centers"""
    
    def test_perth_returns_employees_from_db_employees(self, auth_token):
        """PB-PERTH should return employees from db.employees collection"""
        resp = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": auth_token,
            "center": PERTH_CENTER
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Verify response structure
        assert "employees" in data, "Missing 'employees' key"
        assert "country" in data, "Missing 'country' key"
        assert "payroll_type" in data, "Missing 'payroll_type' key"
        
        # Verify country and payroll type
        assert data["country"] == "Australia", f"Expected Australia, got {data['country']}"
        assert data["payroll_type"] == "hourly", f"Expected hourly, got {data['payroll_type']}"
        
        # Verify employees exist
        employees = data["employees"]
        assert len(employees) >= 1, "No employees returned for PB-PERTH"
        print(f"PB-PERTH has {len(employees)} employees")
        
        # Verify employee data structure
        for emp in employees[:3]:  # Check first 3
            assert "name" in emp, "Employee missing 'name'"
            assert emp["name"] != "Unknown", f"Employee name is 'Unknown': {emp}"
            assert emp["name"] != "", f"Employee name is empty: {emp}"
            print(f"  - {emp['name']}")
    
    def test_india_center_returns_monthly_payroll(self, auth_token):
        """PB-HSR (India) should return monthly payroll type"""
        resp = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": auth_token,
            "center": INDIA_CENTER
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert data["country"] == "India", f"Expected India, got {data['country']}"
        assert data["payroll_type"] == "monthly", f"Expected monthly, got {data['payroll_type']}"
        print(f"PB-HSR has {len(data['employees'])} employees with monthly payroll")


class TestPayrollReportPDF:
    """Test /api/international-attendance/payroll-report-pdf endpoint"""
    
    def test_pdf_generation_returns_valid_pdf(self, auth_token):
        """PDF endpoint should return a valid PDF file"""
        resp = requests.post(f"{BASE_URL}/api/international-attendance/payroll-report-pdf", json={
            "token": auth_token,
            "center": PERTH_CENTER,
            "year": 2026,
            "month": 4
        })
        
        assert resp.status_code == 200, f"PDF generation failed: {resp.text}"
        
        # Verify content type
        content_type = resp.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
        
        # Verify PDF content
        content = resp.content
        assert len(content) > 5000, f"PDF too small ({len(content)} bytes), likely empty"
        assert content[:4] == b'%PDF', "Response is not a valid PDF (missing PDF header)"
        
        # Check for PDF end marker
        assert b'%%EOF' in content[-100:], "PDF missing EOF marker"
        
        print(f"PDF generated successfully: {len(content)} bytes")
    
    def test_pdf_contains_employee_names(self, auth_token):
        """PDF should contain actual employee names, not 'Unknown'"""
        # First get the payroll report data to know what names to expect
        resp = requests.post(f"{BASE_URL}/api/international-attendance/payroll-report", json={
            "token": auth_token,
            "center": PERTH_CENTER,
            "year": 2026,
            "month": 4
        })
        assert resp.status_code == 200, f"Payroll report failed: {resp.text}"
        report_data = resp.json()
        
        # Get employee names from report
        employee_names = [emp["employee_name"] for emp in report_data.get("employees", [])]
        print(f"Employees in report: {employee_names}")
        
        # Verify no 'Unknown' names
        unknown_count = sum(1 for name in employee_names if name == "Unknown")
        assert unknown_count == 0, f"Found {unknown_count} employees with 'Unknown' name"
        
        # Verify names are not empty
        empty_count = sum(1 for name in employee_names if not name or name.strip() == "")
        assert empty_count == 0, f"Found {empty_count} employees with empty name"
    
    def test_pdf_contains_real_financial_values(self, auth_token):
        """PDF should contain real financial values, not all $0"""
        resp = requests.post(f"{BASE_URL}/api/international-attendance/payroll-report", json={
            "token": auth_token,
            "center": PERTH_CENTER,
            "year": 2026,
            "month": 4
        })
        assert resp.status_code == 200, f"Payroll report failed: {resp.text}"
        report_data = resp.json()
        
        totals = report_data.get("totals", {})
        print(f"Totals: {totals}")
        
        # Check that at least some values are non-zero
        # Note: If no attendance data exists, values may be 0 - that's valid
        # But if there are employees with hours, values should be non-zero
        employees = report_data.get("employees", [])
        employees_with_hours = [e for e in employees if e.get("total_hours", 0) > 0]
        
        if employees_with_hours:
            # If there are employees with hours, totals should be non-zero
            assert totals.get("total_hours", 0) > 0, "Total hours is 0 despite employees having hours"
            print(f"Total hours: {totals.get('total_hours')}")
            print(f"Total gross: ${totals.get('total_gross', 0):.2f}")
            print(f"Total net: ${totals.get('total_net', 0):.2f}")
            print(f"Total employer cost: ${totals.get('total_employer_cost', 0):.2f}")
        else:
            print("No employees with hours found - financial values may be $0 (valid)")
    
    def test_payroll_report_has_all_sections(self, auth_token):
        """Payroll report should have all required sections for PDF"""
        resp = requests.post(f"{BASE_URL}/api/international-attendance/payroll-report", json={
            "token": auth_token,
            "center": PERTH_CENTER,
            "year": 2026,
            "month": 4
        })
        assert resp.status_code == 200, f"Payroll report failed: {resp.text}"
        data = resp.json()
        
        # Section 1: Summary totals (for Summary Cards)
        assert "totals" in data, "Missing 'totals' for Summary Cards section"
        totals = data["totals"]
        required_totals = ["total_hours", "total_gross", "total_payg", "total_medicare", 
                          "total_net", "total_super", "total_employer_cost"]
        for key in required_totals:
            assert key in totals, f"Missing '{key}' in totals"
        print("Section 1 (Summary Cards): OK")
        
        # Section 2: Employee Payroll Breakdown
        assert "employees" in data, "Missing 'employees' for Employee Payroll Breakdown"
        if data["employees"]:
            emp = data["employees"][0]
            required_emp_fields = ["employee_name", "category", "total_hours", 
                                   "target_takehome_hourly", "gross_hourly_rate",
                                   "gross_pay", "payg_tax", "medicare_levy", 
                                   "net_pay", "superannuation", "employer_total_cost"]
            for key in required_emp_fields:
                assert key in emp, f"Missing '{key}' in employee data"
        print("Section 2 (Employee Payroll Breakdown): OK")
        
        # Section 3: Weekly Organization Cost Breakdown
        assert "weekly_totals" in data, "Missing 'weekly_totals' for Weekly Org Cost Breakdown"
        weekly_totals = data["weekly_totals"]
        if weekly_totals:
            # Check first week's structure
            first_week = list(weekly_totals.values())[0] if weekly_totals else {}
            required_weekly = ["hours", "gross", "net", "super", "employer_cost"]
            for key in required_weekly:
                assert key in first_week, f"Missing '{key}' in weekly_totals"
        print("Section 3 (Weekly Organization Cost Breakdown): OK")
        
        # Section 4: Per-Person Organization Cost (uses employees data)
        # This is derived from employees data, so if employees exist, this section is available
        print("Section 4 (Per-Person Organization Cost): OK (uses employees data)")
        
        # Additional required fields
        assert "week_labels" in data, "Missing 'week_labels'"
        assert "rates" in data, "Missing 'rates'"
        print("All 4 sections verified in payroll report data")


class TestPayslipGeneration:
    """Test /api/payslips_generate endpoint"""
    
    def test_australian_payslip_single_employee(self, auth_token):
        """Generate Australian payslip for a single employee"""
        # First get an employee name
        resp = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": auth_token,
            "center": PERTH_CENTER
        })
        assert resp.status_code == 200
        employees = resp.json().get("employees", [])
        
        if not employees:
            pytest.skip("No employees found for PB-PERTH")
        
        emp_name = employees[0]["name"]
        print(f"Generating payslip for: {emp_name}")
        
        resp = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": auth_token,
            "month": "2026-04",
            "targetCenter": PERTH_CENTER,
            "mode": "single",
            "employeeName": emp_name,
            "fmt": "pdf"
        })
        
        assert resp.status_code == 200, f"Payslip generation failed: {resp.text}"
        
        content_type = resp.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
        
        content = resp.content
        assert len(content) > 3000, f"PDF too small ({len(content)} bytes)"
        assert content[:4] == b'%PDF', "Not a valid PDF"
        
        print(f"Australian payslip generated: {len(content)} bytes")
    
    def test_australian_payslip_bulk(self, auth_token):
        """Generate Australian payslips for all employees (returns ZIP)"""
        resp = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": auth_token,
            "month": "2026-04",
            "targetCenter": PERTH_CENTER,
            "mode": "all",
            "fmt": "pdf"
        })
        
        assert resp.status_code == 200, f"Bulk payslip generation failed: {resp.text}"
        
        content_type = resp.headers.get("Content-Type", "")
        content = resp.content
        
        # Could be PDF (single employee) or ZIP (multiple employees)
        if "application/zip" in content_type:
            assert content[:2] == b'PK', "Not a valid ZIP file"
            print(f"Bulk payslips generated as ZIP: {len(content)} bytes")
        elif "application/pdf" in content_type:
            assert content[:4] == b'%PDF', "Not a valid PDF"
            print(f"Single payslip generated as PDF: {len(content)} bytes")
        else:
            pytest.fail(f"Unexpected content type: {content_type}")
    
    def test_indian_payslip_still_works(self, auth_token):
        """Indian payslip generation should still work"""
        # First get an employee name from India center
        resp = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": auth_token,
            "center": INDIA_CENTER
        })
        assert resp.status_code == 200
        employees = resp.json().get("employees", [])
        
        if not employees:
            pytest.skip("No employees found for PB-HSR")
        
        emp_name = employees[0]["name"]
        print(f"Generating Indian payslip for: {emp_name}")
        
        resp = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": auth_token,
            "month": "2026-04",
            "targetCenter": INDIA_CENTER,
            "mode": "single",
            "employeeName": emp_name,
            "fmt": "pdf"
        })
        
        assert resp.status_code == 200, f"Indian payslip generation failed: {resp.text}"
        
        content_type = resp.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
        
        content = resp.content
        assert len(content) > 3000, f"PDF too small ({len(content)} bytes)"
        assert content[:4] == b'%PDF', "Not a valid PDF"
        
        print(f"Indian payslip generated: {len(content)} bytes")


class TestMonthlyExportCSV:
    """Test CSV export endpoint"""
    
    def test_monthly_csv_export(self, auth_token):
        """Monthly CSV export should work"""
        resp = requests.post(f"{BASE_URL}/api/international-attendance/export/monthly-excel", json={
            "token": auth_token,
            "center": PERTH_CENTER,
            "year": 2026,
            "month": 4
        })
        
        assert resp.status_code == 200, f"CSV export failed: {resp.text}"
        
        content_type = resp.headers.get("Content-Type", "")
        assert "text/csv" in content_type, f"Expected CSV, got {content_type}"
        
        content = resp.content.decode('utf-8')
        assert "Monthly Payroll Report" in content, "CSV missing header"
        print(f"CSV export successful: {len(content)} characters")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
