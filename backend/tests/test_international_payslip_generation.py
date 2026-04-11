"""
Test International Payslip Generation - Iteration 62
Tests the auto-detection of center country and correct payslip format generation.

Features tested:
1. POST /api/payslip_employees - returns country and payroll_type based on center
2. POST /api/payslips_generate - generates correct format (Australian WA vs Indian)
3. Single employee payslip generation for international centers
4. Bulk payslip generation (ZIP) for international centers
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
AUSTRALIA_CENTER = "PB-PERTH"  # International center in Australia
INDIA_CENTER = "PB-HSR"  # Indian center

# Test month (April 2026 has attendance data for PB-PERTH)
TEST_MONTH = "2026-04"


class TestInternationalPayslipGeneration:
    """Test suite for international payslip generation feature"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for super admin"""
        # Send OTP
        send_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER
        })
        assert send_res.status_code == 200, f"Failed to send OTP: {send_res.text}"
        
        # Verify OTP
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP,
            "center": SUPER_ADMIN_CENTER
        })
        assert verify_res.status_code == 200, f"Failed to verify OTP: {verify_res.text}"
        
        data = verify_res.json()
        assert "token" in data, "No token in verify_otp response"
        return data["token"]
    
    # ==========================================
    # TEST: payslip_employees endpoint
    # ==========================================
    
    def test_payslip_employees_australia_center(self, auth_token):
        """Test payslip_employees returns Australia country and hourly payroll_type for PB-PERTH"""
        res = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": auth_token,
            "center": AUSTRALIA_CENTER
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        # Verify country detection
        assert data.get("country") == "Australia", f"Expected country='Australia', got '{data.get('country')}'"
        
        # Verify payroll type
        assert data.get("payroll_type") == "hourly", f"Expected payroll_type='hourly', got '{data.get('payroll_type')}'"
        
        # Verify employees list
        employees = data.get("employees", [])
        assert len(employees) > 0, "No employees returned for PB-PERTH"
        print(f"✓ PB-PERTH: country=Australia, payroll_type=hourly, {len(employees)} employees")
        
        # Verify employee structure has hourly rate fields
        emp = employees[0]
        assert "name" in emp, "Employee missing 'name' field"
        # International employees should have hourly rate fields
        print(f"  Sample employee: {emp.get('name')}, designation={emp.get('designation')}")
    
    def test_payslip_employees_india_center(self, auth_token):
        """Test payslip_employees returns India country and monthly payroll_type for PB-HSR"""
        res = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": auth_token,
            "center": INDIA_CENTER
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        # Verify country detection
        assert data.get("country") == "India", f"Expected country='India', got '{data.get('country')}'"
        
        # Verify payroll type
        assert data.get("payroll_type") == "monthly", f"Expected payroll_type='monthly', got '{data.get('payroll_type')}'"
        
        # Verify employees list
        employees = data.get("employees", [])
        assert len(employees) > 0, "No employees returned for PB-HSR"
        print(f"✓ PB-HSR: country=India, payroll_type=monthly, {len(employees)} employees")
    
    def test_payslip_employees_australia_has_8_employees(self, auth_token):
        """Test PB-PERTH has 8 international employees"""
        res = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": auth_token,
            "center": AUSTRALIA_CENTER
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        employees = data.get("employees", [])
        
        # Should have 8 employees as per context
        assert len(employees) == 8, f"Expected 8 employees for PB-PERTH, got {len(employees)}"
        
        # Verify expected employee names
        expected_names = {"BINTI", "KELSA", "LAVANYA", "NUSRAT", "OM", "PURVA", "SHUBH", "TINDI"}
        actual_names = {emp.get("name", "").upper() for emp in employees}
        
        for name in expected_names:
            assert name in actual_names, f"Expected employee '{name}' not found in PB-PERTH"
        
        print(f"✓ PB-PERTH has all 8 expected employees: {', '.join(sorted(actual_names))}")
    
    # ==========================================
    # TEST: payslips_generate endpoint - Australian format
    # ==========================================
    
    def test_payslips_generate_australia_single_employee(self, auth_token):
        """Test single employee payslip generation for Australian center returns PDF"""
        res = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": auth_token,
            "month": TEST_MONTH,
            "period": "1",
            "targetCenter": AUSTRALIA_CENTER,
            "mode": "single",
            "employeeName": "BINTI",
            "fmt": "pdf",
            "signatory": "sandeep"
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        
        # Verify response is PDF
        content_type = res.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
        
        # Verify filename in Content-Disposition
        content_disp = res.headers.get("Content-Disposition", "")
        assert "BINTI" in content_disp, f"Filename should contain 'BINTI': {content_disp}"
        assert ".pdf" in content_disp, f"Filename should be .pdf: {content_disp}"
        
        # Verify PDF content (check for PDF magic bytes)
        assert res.content[:4] == b'%PDF', "Response is not a valid PDF"
        
        print(f"✓ Single Australian payslip generated for BINTI ({len(res.content)} bytes)")
    
    def test_payslips_generate_australia_bulk(self, auth_token):
        """Test bulk payslip generation for Australian center returns ZIP"""
        res = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": auth_token,
            "month": TEST_MONTH,
            "period": "1",
            "targetCenter": AUSTRALIA_CENTER,
            "mode": "all",
            "fmt": "pdf",
            "signatory": "sandeep"
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        
        # Verify response is ZIP
        content_type = res.headers.get("Content-Type", "")
        assert "application/zip" in content_type, f"Expected ZIP, got {content_type}"
        
        # Verify filename in Content-Disposition
        content_disp = res.headers.get("Content-Disposition", "")
        assert AUSTRALIA_CENTER in content_disp, f"Filename should contain '{AUSTRALIA_CENTER}': {content_disp}"
        assert ".zip" in content_disp, f"Filename should be .zip: {content_disp}"
        
        # Verify ZIP content (check for ZIP magic bytes)
        assert res.content[:2] == b'PK', "Response is not a valid ZIP"
        
        print(f"✓ Bulk Australian payslips generated as ZIP ({len(res.content)} bytes)")
    
    def test_australian_payslip_pdf_valid_structure(self, auth_token):
        """Test Australian payslip PDF is valid and has reasonable size"""
        res = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": auth_token,
            "month": TEST_MONTH,
            "period": "1",
            "targetCenter": AUSTRALIA_CENTER,
            "mode": "single",
            "employeeName": "BINTI",
            "fmt": "pdf",
            "signatory": "sandeep"
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        
        # Verify it's a valid PDF
        assert res.content[:4] == b'%PDF', "Response is not a valid PDF"
        
        # PDF should have reasonable size (at least 5KB for a payslip with content)
        assert len(res.content) > 5000, f"PDF too small ({len(res.content)} bytes), may be missing content"
        
        # Check for some basic PDF structure elements
        pdf_content = res.content.decode('latin-1', errors='ignore')
        assert 'endobj' in pdf_content, "PDF missing object structure"
        assert '%%EOF' in pdf_content, "PDF missing EOF marker"
        
        print(f"✓ Australian payslip PDF is valid ({len(res.content)} bytes)")
    
    # ==========================================
    # TEST: payslips_generate endpoint - Indian format
    # ==========================================
    
    def test_payslips_generate_india_single_employee(self, auth_token):
        """Test single employee payslip generation for Indian center returns PDF"""
        # First get an employee name from PB-HSR
        emp_res = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": auth_token,
            "center": INDIA_CENTER
        })
        assert emp_res.status_code == 200, f"Failed to get employees: {emp_res.text}"
        
        employees = emp_res.json().get("employees", [])
        assert len(employees) > 0, "No employees in PB-HSR"
        
        emp_name = employees[0].get("name", "")
        assert emp_name, "Employee name is empty"
        
        # Generate payslip
        res = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": auth_token,
            "month": TEST_MONTH,
            "period": "1",
            "targetCenter": INDIA_CENTER,
            "mode": "single",
            "employeeName": emp_name,
            "fmt": "pdf",
            "signatory": "sandeep"
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        
        # Verify response is PDF
        content_type = res.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
        
        # Verify PDF content
        assert res.content[:4] == b'%PDF', "Response is not a valid PDF"
        
        print(f"✓ Single Indian payslip generated for {emp_name} ({len(res.content)} bytes)")
    
    def test_indian_payslip_pdf_valid_structure(self, auth_token):
        """Test Indian payslip PDF is valid and has reasonable size"""
        # First get an employee name from PB-HSR
        emp_res = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": auth_token,
            "center": INDIA_CENTER
        })
        assert emp_res.status_code == 200
        
        employees = emp_res.json().get("employees", [])
        assert len(employees) > 0
        
        emp_name = employees[0].get("name", "")
        
        # Generate payslip
        res = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": auth_token,
            "month": TEST_MONTH,
            "period": "1",
            "targetCenter": INDIA_CENTER,
            "mode": "single",
            "employeeName": emp_name,
            "fmt": "pdf",
            "signatory": "sandeep"
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        
        # Verify it's a valid PDF
        assert res.content[:4] == b'%PDF', "Response is not a valid PDF"
        
        # PDF should have reasonable size (at least 5KB for a payslip with content)
        assert len(res.content) > 5000, f"PDF too small ({len(res.content)} bytes), may be missing content"
        
        # Check for some basic PDF structure elements
        pdf_content = res.content.decode('latin-1', errors='ignore')
        assert 'endobj' in pdf_content, "PDF missing object structure"
        assert '%%EOF' in pdf_content, "PDF missing EOF marker"
        
        print(f"✓ Indian payslip PDF is valid ({len(res.content)} bytes)")
    
    # ==========================================
    # TEST: Error handling
    # ==========================================
    
    def test_payslips_generate_invalid_employee_name(self, auth_token):
        """Test payslip generation with invalid employee name returns 404"""
        res = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": auth_token,
            "month": TEST_MONTH,
            "period": "1",
            "targetCenter": AUSTRALIA_CENTER,
            "mode": "single",
            "employeeName": "NONEXISTENT_EMPLOYEE_XYZ",
            "fmt": "pdf",
            "signatory": "sandeep"
        })
        
        assert res.status_code == 404, f"Expected 404, got {res.status_code}: {res.text}"
        print("✓ Invalid employee name correctly returns 404")
    
    def test_payslips_generate_unauthorized(self):
        """Test payslip generation without valid token returns 401/403"""
        res = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": "invalid_token_xyz",
            "month": TEST_MONTH,
            "period": "1",
            "targetCenter": AUSTRALIA_CENTER,
            "mode": "all",
            "fmt": "pdf",
            "signatory": "sandeep"
        })
        
        assert res.status_code in [401, 403], f"Expected 401/403, got {res.status_code}: {res.text}"
        print("✓ Unauthorized request correctly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
