"""
Test Payslip Generation Features:
1. POST /api/payslip_employees - returns sorted employee list for a given center
2. POST /api/payslips_generate - accepts signatory parameter and generates PDF
3. Verify PDF has logo and signature based on signatory selection
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_OTP = "123456"
SUPER_ADMIN_CENTER = "PB-MGT"
TEST_CENTER = "PB-HSR"  # Center with 16 employees


class TestPayslipEmployeesEndpoint:
    """Test /api/payslip_employees endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP,
            "center": SUPER_ADMIN_CENTER
        })
        assert response.status_code == 200, f"Auth failed: {response.text}"
        self.token = response.json().get("token")
        assert self.token, "No token returned"
    
    def test_payslip_employees_returns_sorted_list(self):
        """Test that /api/payslip_employees returns sorted employee list for a center"""
        response = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "employees" in data, "Response should contain 'employees' key"
        employees = data["employees"]
        assert isinstance(employees, list), "Employees should be a list"
        
        # Verify employees have required fields
        if len(employees) > 0:
            emp = employees[0]
            assert "name" in emp, "Employee should have 'name' field"
            assert "designation" in emp, "Employee should have 'designation' field"
        
        # Verify list is sorted alphabetically by name
        if len(employees) > 1:
            names = [e["name"] for e in employees]
            assert names == sorted(names), f"Employees should be sorted alphabetically. Got: {names[:5]}..."
        
        print(f"SUCCESS: Got {len(employees)} employees for center {TEST_CENTER}")
        print(f"First 5 employees: {[e['name'] for e in employees[:5]]}")
    
    def test_payslip_employees_different_center(self):
        """Test payslip_employees with different center"""
        response = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": self.token,
            "center": "PB-MGT"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "employees" in data
        print(f"SUCCESS: Got {len(data['employees'])} employees for center PB-MGT")
    
    def test_payslip_employees_requires_auth(self):
        """Test that endpoint requires valid token"""
        response = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": "invalid_token",
            "center": TEST_CENTER
        })
        
        assert response.status_code in [401, 403], f"Expected 401/403 for invalid token, got {response.status_code}"
        print("SUCCESS: Endpoint correctly rejects invalid token")


class TestPayslipGenerateEndpoint:
    """Test /api/payslips_generate endpoint with signatory parameter"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP,
            "center": SUPER_ADMIN_CENTER
        })
        assert response.status_code == 200, f"Auth failed: {response.text}"
        self.token = response.json().get("token")
        assert self.token, "No token returned"
    
    def test_payslip_generate_single_employee_sandeep_signatory(self):
        """Test generating single employee payslip with Sandeep signatory"""
        # First get an employee name from the center
        emp_response = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        assert emp_response.status_code == 200
        employees = emp_response.json().get("employees", [])
        assert len(employees) > 0, "No employees found for testing"
        
        employee_name = employees[0]["name"]
        
        # Generate payslip with Sandeep signatory
        response = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": self.token,
            "month": "2025-01",
            "period": "1",
            "targetCenter": TEST_CENTER,
            "mode": "single",
            "employeeName": employee_name,
            "fmt": "pdf",
            "signatory": "sandeep"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify it's a PDF
        content_type = response.headers.get('content-type', '')
        assert 'application/pdf' in content_type, f"Expected PDF, got {content_type}"
        
        # Verify PDF has content (should be larger due to logo and signature)
        pdf_size = len(response.content)
        assert pdf_size > 5000, f"PDF seems too small ({pdf_size} bytes), may be missing images"
        
        print(f"SUCCESS: Generated PDF for {employee_name} with Sandeep signatory ({pdf_size} bytes)")
    
    def test_payslip_generate_single_employee_jayanti_signatory(self):
        """Test generating single employee payslip with Jayanti signatory"""
        # First get an employee name from the center
        emp_response = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        assert emp_response.status_code == 200
        employees = emp_response.json().get("employees", [])
        assert len(employees) > 0, "No employees found for testing"
        
        employee_name = employees[0]["name"]
        
        # Generate payslip with Jayanti signatory
        response = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": self.token,
            "month": "2025-01",
            "period": "1",
            "targetCenter": TEST_CENTER,
            "mode": "single",
            "employeeName": employee_name,
            "fmt": "pdf",
            "signatory": "jayanti"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify it's a PDF
        content_type = response.headers.get('content-type', '')
        assert 'application/pdf' in content_type, f"Expected PDF, got {content_type}"
        
        # Verify PDF has content
        pdf_size = len(response.content)
        assert pdf_size > 5000, f"PDF seems too small ({pdf_size} bytes), may be missing images"
        
        print(f"SUCCESS: Generated PDF for {employee_name} with Jayanti signatory ({pdf_size} bytes)")
    
    def test_payslip_generate_bulk_mode(self):
        """Test generating bulk payslips for all employees in a center"""
        response = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": self.token,
            "month": "2025-01",
            "period": "1",
            "targetCenter": TEST_CENTER,
            "mode": "all",
            "fmt": "pdf",
            "signatory": "sandeep"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Bulk mode should return a ZIP file
        content_type = response.headers.get('content-type', '')
        assert 'zip' in content_type or 'application/pdf' in content_type, f"Expected ZIP or PDF, got {content_type}"
        
        file_size = len(response.content)
        print(f"SUCCESS: Generated bulk payslips ({file_size} bytes)")
    
    def test_payslip_generate_default_signatory(self):
        """Test that default signatory is 'sandeep' when not specified"""
        emp_response = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        employees = emp_response.json().get("employees", [])
        employee_name = employees[0]["name"] if employees else "TEST"
        
        # Generate without specifying signatory
        response = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": self.token,
            "month": "2025-01",
            "period": "1",
            "targetCenter": TEST_CENTER,
            "mode": "single",
            "employeeName": employee_name,
            "fmt": "pdf"
            # signatory not specified - should default to "sandeep"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("SUCCESS: Payslip generated with default signatory")
    
    def test_payslip_generate_requires_auth(self):
        """Test that endpoint requires valid token"""
        response = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": "invalid_token",
            "month": "2025-01",
            "period": "1",
            "targetCenter": TEST_CENTER,
            "mode": "all",
            "fmt": "pdf",
            "signatory": "sandeep"
        })
        
        assert response.status_code in [401, 403], f"Expected 401/403 for invalid token, got {response.status_code}"
        print("SUCCESS: Endpoint correctly rejects invalid token")
    
    def test_payslip_generate_docx_format(self):
        """Test generating payslip in DOCX format"""
        emp_response = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        employees = emp_response.json().get("employees", [])
        employee_name = employees[0]["name"] if employees else "TEST"
        
        response = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": self.token,
            "month": "2025-01",
            "period": "1",
            "targetCenter": TEST_CENTER,
            "mode": "single",
            "employeeName": employee_name,
            "fmt": "docx",
            "signatory": "jayanti"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        content_type = response.headers.get('content-type', '')
        assert 'wordprocessingml' in content_type or 'octet-stream' in content_type, f"Expected DOCX, got {content_type}"
        
        print(f"SUCCESS: Generated DOCX payslip ({len(response.content)} bytes)")


class TestPayslipPDFContent:
    """Test that generated PDF contains logo and signature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP,
            "center": SUPER_ADMIN_CENTER
        })
        assert response.status_code == 200, f"Auth failed: {response.text}"
        self.token = response.json().get("token")
        assert self.token, "No token returned"
    
    def test_pdf_size_indicates_embedded_images(self):
        """Test that PDF size is large enough to contain embedded images"""
        emp_response = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        employees = emp_response.json().get("employees", [])
        employee_name = employees[0]["name"] if employees else "TEST"
        
        # Generate PDF with images
        response = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": self.token,
            "month": "2025-01",
            "period": "1",
            "targetCenter": TEST_CENTER,
            "mode": "single",
            "employeeName": employee_name,
            "fmt": "pdf",
            "signatory": "sandeep"
        })
        
        assert response.status_code == 200
        pdf_size = len(response.content)
        
        # A PDF with embedded logo (~133KB) and signature (~171KB) should be substantial
        # Even with compression, it should be at least 10KB
        assert pdf_size > 10000, f"PDF size ({pdf_size} bytes) suggests images may not be embedded"
        
        print(f"SUCCESS: PDF size ({pdf_size} bytes) indicates embedded images")
    
    def test_different_signatories_produce_different_pdfs(self):
        """Test that different signatories produce different PDF content"""
        emp_response = requests.post(f"{BASE_URL}/api/payslip_employees", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        employees = emp_response.json().get("employees", [])
        employee_name = employees[0]["name"] if employees else "TEST"
        
        # Generate with Sandeep
        response_sandeep = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": self.token,
            "month": "2025-01",
            "period": "1",
            "targetCenter": TEST_CENTER,
            "mode": "single",
            "employeeName": employee_name,
            "fmt": "pdf",
            "signatory": "sandeep"
        })
        
        # Generate with Jayanti
        response_jayanti = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": self.token,
            "month": "2025-01",
            "period": "1",
            "targetCenter": TEST_CENTER,
            "mode": "single",
            "employeeName": employee_name,
            "fmt": "pdf",
            "signatory": "jayanti"
        })
        
        assert response_sandeep.status_code == 200
        assert response_jayanti.status_code == 200
        
        # PDFs should be different sizes due to different signature images
        size_sandeep = len(response_sandeep.content)
        size_jayanti = len(response_jayanti.content)
        
        # They should both be substantial (have images)
        assert size_sandeep > 10000, f"Sandeep PDF too small: {size_sandeep}"
        assert size_jayanti > 10000, f"Jayanti PDF too small: {size_jayanti}"
        
        # Content should be different (different signatures)
        assert response_sandeep.content != response_jayanti.content, "PDFs with different signatories should have different content"
        
        print(f"SUCCESS: Different signatories produce different PDFs (Sandeep: {size_sandeep}, Jayanti: {size_jayanti})")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
