"""
Test Suite for Transfer-Aware Features (Iteration 24)
=====================================================
Tests for:
1. Transfer-aware attendance endpoints (attendance_month, attendance_by_date, bulk_attendance)
2. Transfer-aware payroll (salary_preview with transferTag and workingCenter)
3. International PDF export endpoint
4. Refactored HR Letters and Centers/Managers endpoints
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_CENTER = "PB-MGT"
SUPER_ADMIN_MOBILE = "9741399190"
INDIA_CENTER = "PB-HSR"
INDIA_MOBILE = "9999999999"
PERTH_CENTER = "PB-PERTH"
PERTH_MOBILE = "0401832922"
OTP = "123456"


class TestAuth:
    """Authentication helper tests"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        # Send OTP
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE
        })
        assert res.status_code == 200
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": OTP
        })
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        return data["token"]
    
    @pytest.fixture(scope="class")
    def india_manager_token(self):
        """Get India center manager token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": INDIA_CENTER,
            "mobile": INDIA_MOBILE
        })
        assert res.status_code == 200
        
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": INDIA_CENTER,
            "mobile": INDIA_MOBILE,
            "otp": OTP
        })
        assert res.status_code == 200
        data = res.json()
        return data["token"]
    
    @pytest.fixture(scope="class")
    def perth_manager_token(self):
        """Get Perth center manager token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": PERTH_CENTER,
            "mobile": PERTH_MOBILE
        })
        assert res.status_code == 200
        
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": PERTH_CENTER,
            "mobile": PERTH_MOBILE,
            "otp": OTP
        })
        assert res.status_code == 200
        data = res.json()
        return data["token"]


class TestTransferAwareAttendance(TestAuth):
    """Tests for transfer-aware attendance endpoints"""
    
    def test_attendance_month_returns_transfer_tags(self, india_manager_token):
        """Test /api/attendance_month returns transfer_tag and transfer_info for employees"""
        res = requests.post(f"{BASE_URL}/api/attendance_month", json={
            "token": india_manager_token,
            "center": INDIA_CENTER,
            "month": "2025-01"
        })
        assert res.status_code == 200
        data = res.json()
        
        # Should have grid and daysInMonth
        assert "grid" in data
        assert "daysInMonth" in data
        assert isinstance(data["grid"], list)
        
        # Each employee in grid should have transfer_tag
        for emp in data["grid"]:
            assert "employeeName" in emp
            assert "transfer_tag" in emp, f"Employee {emp.get('employeeName')} missing transfer_tag"
            assert emp["transfer_tag"] in ["HOME", "TRANSFERRED_IN", "TRANSFERRED_OUT"]
            assert "transfer_info" in emp
            assert "days" in emp
    
    def test_attendance_by_date_returns_transfer_info(self, india_manager_token):
        """Test /api/attendance_by_date returns transferred_in_names and transferred_out_names"""
        res = requests.post(f"{BASE_URL}/api/attendance_by_date", json={
            "token": india_manager_token,
            "center": INDIA_CENTER,
            "date": "2025-01-15"
        })
        assert res.status_code == 200
        data = res.json()
        
        # Should have rows and transfer lists
        assert "rows" in data
        assert "transferred_in_names" in data
        assert "transferred_out_names" in data
        assert isinstance(data["transferred_in_names"], list)
        assert isinstance(data["transferred_out_names"], list)
        
        # Each row should have transfer_tag
        for row in data["rows"]:
            assert "transfer_tag" in row
            assert row["transfer_tag"] in ["HOME", "TRANSFERRED_IN", "TRANSFERRED_OUT"]
    
    def test_bulk_attendance_skips_transferred_out(self, india_manager_token):
        """Test /api/bulk_attendance returns skipped_transferred_out count"""
        res = requests.post(f"{BASE_URL}/api/bulk_attendance", json={
            "token": india_manager_token,
            "center": INDIA_CENTER,
            "date": "2025-01-20",
            "rows": [
                {"employeeName": "TEST_EMPLOYEE", "designation": "Test", "status": "P", "notes": ""}
            ]
        })
        assert res.status_code == 200
        data = res.json()
        
        # Should have skipped_transferred_out field
        assert "success" in data
        assert "skipped_transferred_out" in data
        assert isinstance(data["skipped_transferred_out"], int)
    
    def test_employees_endpoint_returns_transfer_info(self, india_manager_token):
        """Test /api/employees returns transfer_tag, transfer_from, transfer_to"""
        res = requests.post(f"{BASE_URL}/api/employees", json={
            "token": india_manager_token,
            "center": INDIA_CENTER
        })
        assert res.status_code == 200
        data = res.json()
        
        assert "employees" in data
        assert isinstance(data["employees"], list)
        
        # Each employee should have transfer_tag
        for emp in data["employees"]:
            assert "name" in emp
            assert "transfer_tag" in emp, f"Employee {emp.get('name')} missing transfer_tag"
            assert emp["transfer_tag"] in ["HOME", "TRANSFERRED_IN", "TRANSFERRED_OUT"]


class TestTransferAwarePayroll(TestAuth):
    """Tests for transfer-aware payroll (salary_preview)"""
    
    def test_salary_preview_returns_transfer_fields(self, super_admin_token):
        """Test /api/salary_preview returns transferTag and workingCenter for each employee"""
        res = requests.post(f"{BASE_URL}/api/salary_preview", json={
            "token": super_admin_token,
            "month": "2025-01",
            "targetCenter": INDIA_CENTER
        })
        assert res.status_code == 200
        data = res.json()
        
        # Should have salaryData array
        assert "success" in data
        assert data["success"] == True
        assert "salaryData" in data
        assert isinstance(data["salaryData"], list)
        
        # Each employee should have transferTag and workingCenter
        for emp in data["salaryData"]:
            assert "employeeName" in emp
            assert "transferTag" in emp, f"Employee {emp.get('employeeName')} missing transferTag"
            assert "workingCenter" in emp, f"Employee {emp.get('employeeName')} missing workingCenter"
            assert emp["transferTag"] in ["HOME", "TRANSFERRED_IN", "TRANSFERRED_OUT"]
            assert emp["workingCenter"] is not None
    
    def test_salary_preview_requires_admin(self, india_manager_token):
        """Test /api/salary_preview requires admin access"""
        res = requests.post(f"{BASE_URL}/api/salary_preview", json={
            "token": india_manager_token,
            "month": "2025-01",
            "targetCenter": INDIA_CENTER
        })
        # Should be 403 for non-admin
        assert res.status_code == 403


class TestInternationalPDFExport(TestAuth):
    """Tests for International Attendance PDF export"""
    
    def test_monthly_pdf_export_returns_pdf(self, super_admin_token):
        """Test /api/international-attendance/export/monthly-pdf returns valid PDF"""
        res = requests.post(f"{BASE_URL}/api/international-attendance/export/monthly-pdf", json={
            "token": super_admin_token,
            "center": PERTH_CENTER,
            "year": 2025,
            "month": 1
        })
        assert res.status_code == 200
        
        # Check content type is PDF
        content_type = res.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected PDF content-type, got {content_type}"
        
        # Check content disposition header
        content_disp = res.headers.get("content-disposition", "")
        assert "attachment" in content_disp
        assert ".pdf" in content_disp.lower()
        
        # Check PDF magic bytes
        assert res.content[:4] == b'%PDF', "Response does not start with PDF magic bytes"
    
    def test_monthly_pdf_export_with_perth_manager(self, perth_manager_token):
        """Test Perth manager can export their own center's PDF"""
        res = requests.post(f"{BASE_URL}/api/international-attendance/export/monthly-pdf", json={
            "token": perth_manager_token,
            "center": PERTH_CENTER,
            "year": 2025,
            "month": 1
        })
        assert res.status_code == 200
        content_type = res.headers.get("content-type", "")
        assert "application/pdf" in content_type


class TestRefactoredCentersManagers(TestAuth):
    """Tests for refactored Centers & Managers endpoints (routes/centers_managers.py)"""
    
    def test_mgt_centers_endpoint(self, super_admin_token):
        """Test /api/mgt/centers returns all centers"""
        res = requests.post(f"{BASE_URL}/api/mgt/centers", json={
            "token": super_admin_token
        })
        assert res.status_code == 200
        data = res.json()
        
        assert "centers" in data
        assert isinstance(data["centers"], list)
        assert len(data["centers"]) > 0
        
        # Each center should have code and name
        for center in data["centers"]:
            assert "code" in center
            assert "name" in center
    
    def test_mgt_managers_endpoint(self, super_admin_token):
        """Test /api/mgt/managers returns all managers"""
        res = requests.post(f"{BASE_URL}/api/mgt/managers", json={
            "token": super_admin_token
        })
        assert res.status_code == 200
        data = res.json()
        
        assert "managers" in data
        assert isinstance(data["managers"], list)
        
        # Each manager should have center and email
        for manager in data["managers"]:
            assert "center" in manager
            assert "email" in manager


class TestRefactoredHRLetters(TestAuth):
    """Tests for refactored HR Letters endpoints (routes/hr_letters.py)"""
    
    def test_hr_letter_employees_endpoint(self, super_admin_token):
        """Test /api/hr_letter/employees returns employee list"""
        res = requests.get(f"{BASE_URL}/api/hr_letter/employees", params={
            "token": super_admin_token
        })
        assert res.status_code == 200
        data = res.json()
        
        assert "employees" in data
        assert isinstance(data["employees"], list)
        
        # Each employee should have name and center
        for emp in data["employees"]:
            assert "name" in emp
            assert "center" in emp
    
    def test_hr_letter_employees_requires_mgt(self, india_manager_token):
        """Test /api/hr_letter/employees requires PB-MGT access"""
        res = requests.get(f"{BASE_URL}/api/hr_letter/employees", params={
            "token": india_manager_token
        })
        # Should be 403 for non-MGT
        assert res.status_code == 403


class TestHealthAndBasicEndpoints:
    """Basic health and endpoint tests"""
    
    def test_health_endpoint(self):
        """Test /api/health returns healthy status"""
        res = requests.get(f"{BASE_URL}/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data.get("status") == "healthy"
    
    def test_centers_endpoint(self):
        """Test /api/centers returns center list"""
        res = requests.get(f"{BASE_URL}/api/centers")
        assert res.status_code == 200
        data = res.json()
        assert "centers" in data
        assert len(data["centers"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
