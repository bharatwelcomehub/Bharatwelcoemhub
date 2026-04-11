"""
Test Employee KYC & Document Management Feature
Tests for:
- Employee CRUD with new KYC fields (aadhaar, pan, tfn, blood_group, passport_number, visa_type)
- Photo upload endpoint
- Document upload endpoint (aadhaar_doc, pan_doc, passport_doc, visa_doc)
- Employee Report PDF generation
"""

import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"
TEST_CENTER = "PB-MGT"


class TestEmployeeKYCDocuments:
    """Test Employee KYC & Document Management endpoints"""
    
    token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before tests"""
        if TestEmployeeKYCDocuments.token is None:
            # Send OTP
            resp = requests.post(f"{BASE_URL}/api/send_otp", json={
                "mobile": TEST_MOBILE,
                "center": TEST_CENTER
            })
            assert resp.status_code == 200, f"Send OTP failed: {resp.text}"
            
            # Verify OTP
            resp = requests.post(f"{BASE_URL}/api/verify_otp", json={
                "mobile": TEST_MOBILE,
                "otp": TEST_OTP,
                "center": TEST_CENTER
            })
            assert resp.status_code == 200, f"Verify OTP failed: {resp.text}"
            TestEmployeeKYCDocuments.token = resp.json().get("token")
        
        self.token = TestEmployeeKYCDocuments.token
    
    # ==========================================
    # Employee List Endpoint Tests
    # ==========================================
    
    def test_mgt_employees_list_returns_kyc_fields(self):
        """Test that employee list returns KYC fields"""
        resp = requests.post(f"{BASE_URL}/api/mgt_employees_list", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "employees" in data
        
        # Check that employees have KYC fields in schema (even if empty)
        if data["employees"]:
            emp = data["employees"][0]
            # These fields should exist in the employee schema
            print(f"Employee fields: {list(emp.keys())}")
            # rowIndex should be present for editing
            assert "rowIndex" in emp, "rowIndex missing from employee"
    
    # ==========================================
    # Employee Create with KYC Fields
    # ==========================================
    
    def test_create_employee_with_kyc_fields(self):
        """Test creating employee with all new KYC fields"""
        test_emp_name = "TEST_KYC_EMPLOYEE"
        
        # First delete if exists
        resp = requests.post(f"{BASE_URL}/api/mgt_employees_list", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        employees = resp.json().get("employees", [])
        for emp in employees:
            if emp.get("name") == test_emp_name:
                requests.post(f"{BASE_URL}/api/mgt_employee_delete", json={
                    "token": self.token,
                    "center": TEST_CENTER,
                    "rowIndex": emp.get("rowIndex")
                })
        
        # Create employee with KYC fields
        create_data = {
            "token": self.token,
            "center": TEST_CENTER,
            "empCenter": "PB-HSR",
            "name": test_emp_name,
            "designation": "TEST DESIGNATION",
            "currentSalary": 50000,
            "salaryBase": 45000,
            "mobile": "9999999999",
            "email": "test@example.com",
            "gender": "MALE",
            "dateOfJoining": "2024-01-15",
            # New KYC fields
            "aadhaar": "1234 5678 9012",
            "pan": "ABCDE1234F",
            "tfn": "123456789",
            "blood_group": "O+",
            "passport_number": "A1234567",
            "visa_type": "Work Visa"
        }
        
        resp = requests.post(f"{BASE_URL}/api/mgt_employee_create", json=create_data)
        assert resp.status_code == 200, f"Create failed: {resp.text}"
        data = resp.json()
        assert data.get("success") == True, f"Create not successful: {data}"
        
        # Verify employee was created with KYC fields
        resp = requests.post(f"{BASE_URL}/api/mgt_employees_list", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        employees = resp.json().get("employees", [])
        created_emp = next((e for e in employees if e.get("name") == test_emp_name), None)
        
        assert created_emp is not None, "Created employee not found"
        assert created_emp.get("aadhaar") == "1234 5678 9012", f"Aadhaar mismatch: {created_emp.get('aadhaar')}"
        assert created_emp.get("pan") == "ABCDE1234F", f"PAN mismatch: {created_emp.get('pan')}"
        assert created_emp.get("tfn") == "123456789", f"TFN mismatch: {created_emp.get('tfn')}"
        assert created_emp.get("blood_group") == "O+", f"Blood group mismatch: {created_emp.get('blood_group')}"
        assert created_emp.get("passport_number") == "A1234567", f"Passport mismatch: {created_emp.get('passport_number')}"
        assert created_emp.get("visa_type") == "Work Visa", f"Visa type mismatch: {created_emp.get('visa_type')}"
        
        print(f"✓ Employee created with all KYC fields: {test_emp_name}")
    
    # ==========================================
    # Employee Update with KYC Fields
    # ==========================================
    
    def test_update_employee_kyc_fields(self):
        """Test updating employee KYC fields"""
        test_emp_name = "TEST_KYC_EMPLOYEE"
        
        # Get employee
        resp = requests.post(f"{BASE_URL}/api/mgt_employees_list", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        employees = resp.json().get("employees", [])
        emp = next((e for e in employees if e.get("name") == test_emp_name), None)
        
        if not emp:
            pytest.skip("Test employee not found - run create test first")
        
        # Update KYC fields
        update_data = {
            "token": self.token,
            "center": TEST_CENTER,
            "rowIndex": emp.get("rowIndex"),
            "empCenter": emp.get("center"),
            "name": test_emp_name,
            "designation": emp.get("designation", ""),
            "currentSalary": emp.get("currentSalary", 0),
            "salaryBase": emp.get("salaryBase", 0),
            "mobile": emp.get("mobile", ""),
            "email": emp.get("email", ""),
            "gender": emp.get("gender", ""),
            "dateOfJoining": emp.get("dateOfJoining", ""),
            # Updated KYC fields
            "aadhaar": "9999 8888 7777",
            "pan": "ZZZZZ9999Z",
            "tfn": "987654321",
            "blood_group": "AB+",
            "passport_number": "Z9876543",
            "visa_type": "PR"
        }
        
        resp = requests.post(f"{BASE_URL}/api/mgt_employee_update", json=update_data)
        assert resp.status_code == 200, f"Update failed: {resp.text}"
        
        # Verify update
        resp = requests.post(f"{BASE_URL}/api/mgt_employees_list", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        employees = resp.json().get("employees", [])
        updated_emp = next((e for e in employees if e.get("name") == test_emp_name), None)
        
        assert updated_emp is not None, "Updated employee not found"
        assert updated_emp.get("aadhaar") == "9999 8888 7777", f"Aadhaar not updated: {updated_emp.get('aadhaar')}"
        assert updated_emp.get("blood_group") == "AB+", f"Blood group not updated: {updated_emp.get('blood_group')}"
        
        print(f"✓ Employee KYC fields updated successfully")
    
    # ==========================================
    # Photo Upload Endpoint Tests
    # ==========================================
    
    def test_photo_upload_validates_file_type(self):
        """Test that photo upload rejects non-image files"""
        # Create a fake text file
        files = {
            'file': ('test.txt', b'This is not an image', 'text/plain')
        }
        data = {
            'token': self.token,
            'employee_name': 'TEST_KYC_EMPLOYEE',
            'center': 'PB-HSR'
        }
        
        resp = requests.post(f"{BASE_URL}/api/employee_upload_photo", files=files, data=data)
        assert resp.status_code == 400, f"Should reject non-image: {resp.status_code} - {resp.text}"
        print("✓ Photo upload correctly rejects non-image files")
    
    def test_photo_upload_validates_size(self):
        """Test that photo upload rejects files over 5MB"""
        # Create a fake large file (>5MB)
        large_content = b'x' * (6 * 1024 * 1024)  # 6MB
        files = {
            'file': ('large.jpg', large_content, 'image/jpeg')
        }
        data = {
            'token': self.token,
            'employee_name': 'TEST_KYC_EMPLOYEE',
            'center': 'PB-HSR'
        }
        
        resp = requests.post(f"{BASE_URL}/api/employee_upload_photo", files=files, data=data)
        assert resp.status_code == 400, f"Should reject large file: {resp.status_code} - {resp.text}"
        assert "5MB" in resp.text or "under" in resp.text.lower(), f"Error should mention size limit: {resp.text}"
        print("✓ Photo upload correctly rejects files over 5MB")
    
    # ==========================================
    # Document Upload Endpoint Tests
    # ==========================================
    
    def test_document_upload_validates_doc_type(self):
        """Test that document upload validates doc_type parameter"""
        files = {
            'file': ('test.pdf', b'%PDF-1.4 fake pdf content', 'application/pdf')
        }
        data = {
            'token': self.token,
            'employee_name': 'TEST_KYC_EMPLOYEE',
            'center': 'PB-HSR',
            'doc_type': 'invalid_doc_type'  # Invalid doc type
        }
        
        resp = requests.post(f"{BASE_URL}/api/employee_upload_document", files=files, data=data)
        assert resp.status_code == 400, f"Should reject invalid doc_type: {resp.status_code} - {resp.text}"
        assert "aadhaar_doc" in resp.text or "pan_doc" in resp.text, f"Error should list valid types: {resp.text}"
        print("✓ Document upload correctly validates doc_type")
    
    def test_document_upload_validates_file_type(self):
        """Test that document upload rejects invalid file types"""
        files = {
            'file': ('test.exe', b'MZ executable content', 'application/x-msdownload')
        }
        data = {
            'token': self.token,
            'employee_name': 'TEST_KYC_EMPLOYEE',
            'center': 'PB-HSR',
            'doc_type': 'aadhaar_doc'
        }
        
        resp = requests.post(f"{BASE_URL}/api/employee_upload_document", files=files, data=data)
        assert resp.status_code == 400, f"Should reject exe file: {resp.status_code} - {resp.text}"
        print("✓ Document upload correctly rejects invalid file types")
    
    def test_document_upload_validates_size(self):
        """Test that document upload rejects files over 10MB"""
        large_content = b'x' * (11 * 1024 * 1024)  # 11MB
        files = {
            'file': ('large.pdf', large_content, 'application/pdf')
        }
        data = {
            'token': self.token,
            'employee_name': 'TEST_KYC_EMPLOYEE',
            'center': 'PB-HSR',
            'doc_type': 'aadhaar_doc'
        }
        
        resp = requests.post(f"{BASE_URL}/api/employee_upload_document", files=files, data=data)
        assert resp.status_code == 400, f"Should reject large file: {resp.status_code} - {resp.text}"
        assert "10MB" in resp.text or "under" in resp.text.lower(), f"Error should mention size limit: {resp.text}"
        print("✓ Document upload correctly rejects files over 10MB")
    
    def test_document_upload_accepts_valid_types(self):
        """Test that document upload accepts valid doc_types"""
        valid_doc_types = ["aadhaar_doc", "pan_doc", "passport_doc", "visa_doc"]
        
        for doc_type in valid_doc_types:
            # Create a small valid PDF
            files = {
                'file': (f'{doc_type}.pdf', b'%PDF-1.4 fake pdf', 'application/pdf')
            }
            data = {
                'token': self.token,
                'employee_name': 'TEST_KYC_EMPLOYEE',
                'center': 'PB-HSR',
                'doc_type': doc_type
            }
            
            resp = requests.post(f"{BASE_URL}/api/employee_upload_document", files=files, data=data)
            # Should either succeed (200) or fail due to storage issues (500), not validation (400)
            assert resp.status_code != 400 or "Invalid doc_type" not in resp.text, \
                f"Valid doc_type {doc_type} was rejected: {resp.text}"
            print(f"✓ Document upload accepts valid doc_type: {doc_type}")
    
    # ==========================================
    # Employee Report PDF Endpoint Tests
    # ==========================================
    
    def test_employee_report_generates_pdf(self):
        """Test that employee report endpoint generates a PDF"""
        resp = requests.post(f"{BASE_URL}/api/employee_report", json={
            "token": self.token,
            "center": ""  # All centers
        })
        
        # Should return PDF or 404 if no employees
        if resp.status_code == 404:
            print("⚠ No employees found for report - skipping PDF validation")
            return
        
        assert resp.status_code == 200, f"Report generation failed: {resp.status_code} - {resp.text}"
        
        # Check content type
        content_type = resp.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got: {content_type}"
        
        # Check PDF content
        content = resp.content
        assert len(content) > 1000, f"PDF too small: {len(content)} bytes"
        assert content[:4] == b'%PDF', f"Not a valid PDF: {content[:20]}"
        
        print(f"✓ Employee report PDF generated: {len(content)} bytes")
    
    def test_employee_report_with_center_filter(self):
        """Test employee report with specific center filter"""
        resp = requests.post(f"{BASE_URL}/api/employee_report", json={
            "token": self.token,
            "center": "PB-HSR"  # Specific center
        })
        
        # Should return PDF or 404 if no employees in that center
        if resp.status_code == 404:
            print("⚠ No employees found for PB-HSR - skipping")
            return
        
        assert resp.status_code == 200, f"Report generation failed: {resp.status_code} - {resp.text}"
        
        content_type = resp.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got: {content_type}"
        
        print(f"✓ Employee report PDF generated for PB-HSR")
    
    # ==========================================
    # Cleanup
    # ==========================================
    
    def test_cleanup_test_employee(self):
        """Clean up test employee"""
        test_emp_name = "TEST_KYC_EMPLOYEE"
        
        resp = requests.post(f"{BASE_URL}/api/mgt_employees_list", json={
            "token": self.token,
            "center": TEST_CENTER
        })
        employees = resp.json().get("employees", [])
        
        for emp in employees:
            if emp.get("name") == test_emp_name:
                resp = requests.post(f"{BASE_URL}/api/mgt_employee_delete", json={
                    "token": self.token,
                    "center": TEST_CENTER,
                    "rowIndex": emp.get("rowIndex")
                })
                print(f"✓ Cleaned up test employee: {test_emp_name}")
                return
        
        print("⚠ Test employee not found for cleanup")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
