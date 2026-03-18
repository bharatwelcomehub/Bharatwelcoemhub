"""
Attendance Dashboard Module - Backend API Tests
Tests: Summary, Center Breakdown, Center Detail, Monthly Trend, Center Comparison, Export, Edit (Super Admin)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials - Super Admin
SUPER_ADMIN_CENTER = "PB-MGT"
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_OTP = "123456"

# Test date with existing attendance data (Feb 2026)
TEST_DATE = "2026-02-22"
TEST_MONTH = "2026-02"


class TestAttendanceDashboard:
    """Attendance Dashboard API Tests"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create a session and authenticate as Super Admin"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        return s
    
    @pytest.fixture(scope="class")
    def auth_token(self, session):
        """Get authentication token for Super Admin"""
        # Send OTP
        otp_res = session.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE
        })
        assert otp_res.status_code == 200, f"Failed to send OTP: {otp_res.text}"
        
        # Verify OTP
        verify_res = session.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP
        })
        assert verify_res.status_code == 200, f"Failed to verify OTP: {verify_res.text}"
        
        data = verify_res.json()
        assert "token" in data, "Token not in response"
        assert data.get("is_super_admin") == True, "User should be Super Admin"
        return data["token"]
    
    # =======================================
    # STATUS OPTIONS ENDPOINT
    # =======================================
    
    def test_status_options_endpoint(self, session):
        """Test /status-options returns all attendance status options"""
        res = session.get(f"{BASE_URL}/api/attendance-dashboard/status-options")
        assert res.status_code == 200, f"Status: {res.status_code}"
        
        data = res.json()
        assert "statuses" in data
        assert len(data["statuses"]) >= 5, "Should have at least 5 status options"
        
        # Verify expected statuses
        status_codes = [s["code"] for s in data["statuses"]]
        assert "P" in status_codes, "Present status missing"
        assert "A" in status_codes, "Absent status missing"
        assert "HD" in status_codes, "Half Day status missing"
        assert "WO" in status_codes, "Week Off status missing"
        assert "L" in status_codes, "Leave status missing"
        print(f"✓ Status options: {status_codes}")
    
    # =======================================
    # SUMMARY ENDPOINT
    # =======================================
    
    def test_summary_endpoint_success(self, session, auth_token):
        """Test /summary returns overall attendance summary"""
        res = session.post(f"{BASE_URL}/api/attendance-dashboard/summary", json={
            "token": auth_token,
            "date": TEST_DATE
        })
        assert res.status_code == 200, f"Status: {res.status_code}, Body: {res.text}"
        
        data = res.json()
        assert "date" in data
        assert "summary" in data
        assert data["date"] == TEST_DATE
        
        summary = data["summary"]
        assert "total_employees" in summary
        assert "present" in summary
        assert "absent" in summary
        assert "half_day" in summary
        assert "week_off" in summary
        assert "leave" in summary
        assert "attendance_percentage" in summary
        
        assert data.get("is_super_admin") == True
        assert data.get("can_edit") == True
        print(f"✓ Summary: Total={summary['total_employees']}, Present={summary['present']}, Absent={summary['absent']}, Attendance={summary['attendance_percentage']}%")
    
    def test_summary_without_date_uses_today(self, session, auth_token):
        """Test /summary without date defaults to today"""
        res = session.post(f"{BASE_URL}/api/attendance-dashboard/summary", json={
            "token": auth_token
        })
        assert res.status_code == 200
        
        data = res.json()
        assert "date" in data
        assert "summary" in data
        print(f"✓ Summary (today): {data['date']}")
    
    def test_summary_invalid_token(self, session):
        """Test /summary returns 401 for invalid token"""
        res = session.post(f"{BASE_URL}/api/attendance-dashboard/summary", json={
            "token": "invalid_token_12345",
            "date": TEST_DATE
        })
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"
        print("✓ Summary: Invalid token returns 401")
    
    # =======================================
    # CENTER BREAKDOWN ENDPOINT
    # =======================================
    
    def test_center_breakdown_endpoint(self, session, auth_token):
        """Test /center-breakdown returns per-center attendance data"""
        res = session.post(f"{BASE_URL}/api/attendance-dashboard/center-breakdown", json={
            "token": auth_token,
            "date": TEST_DATE
        })
        assert res.status_code == 200, f"Status: {res.status_code}"
        
        data = res.json()
        assert "date" in data
        assert "centers" in data
        assert isinstance(data["centers"], list)
        
        if len(data["centers"]) > 0:
            center = data["centers"][0]
            assert "center_code" in center
            assert "total_staff" in center
            assert "present" in center
            assert "absent" in center
            assert "attendance_percentage" in center
            assert "alert" in center
            assert center["alert"] in ["green", "yellow", "red"]
            print(f"✓ Center Breakdown: {len(data['centers'])} centers found")
            print(f"  First center: {center['center_code']} - {center['attendance_percentage']}% ({center['alert']} alert)")
        else:
            print("✓ Center Breakdown: No centers returned (empty list)")
    
    # =======================================
    # CENTER DETAIL ENDPOINT
    # =======================================
    
    def test_center_detail_endpoint(self, session, auth_token):
        """Test /center-detail returns employee-level attendance for a center"""
        # First get a center code
        breakdown_res = session.post(f"{BASE_URL}/api/attendance-dashboard/center-breakdown", json={
            "token": auth_token,
            "date": TEST_DATE
        })
        centers = breakdown_res.json().get("centers", [])
        
        if len(centers) == 0:
            pytest.skip("No centers available for detail testing")
        
        test_center = centers[0]["center_code"]
        
        res = session.post(f"{BASE_URL}/api/attendance-dashboard/center-detail", json={
            "token": auth_token,
            "center": test_center,
            "date": TEST_DATE
        })
        assert res.status_code == 200, f"Status: {res.status_code}"
        
        data = res.json()
        assert "date" in data
        assert "center" in data
        assert "summary" in data
        assert "employees" in data
        assert data["center"].upper() == test_center.upper()
        
        summary = data["summary"]
        assert "total" in summary
        assert "present" in summary
        assert "absent" in summary
        assert "attendance_percentage" in summary
        
        if len(data["employees"]) > 0:
            emp = data["employees"][0]
            assert "name" in emp
            assert "status" in emp
            assert "status_label" in emp
            assert "status_color" in emp
            print(f"✓ Center Detail ({test_center}): {len(data['employees'])} employees, {summary['attendance_percentage']}%")
        else:
            print(f"✓ Center Detail ({test_center}): No employees found")
    
    # =======================================
    # MONTHLY TREND ENDPOINT
    # =======================================
    
    def test_monthly_trend_endpoint(self, session, auth_token):
        """Test /monthly-trend returns daily attendance trend for a month"""
        res = session.post(f"{BASE_URL}/api/attendance-dashboard/monthly-trend", json={
            "token": auth_token,
            "month": TEST_MONTH
        })
        assert res.status_code == 200, f"Status: {res.status_code}"
        
        data = res.json()
        assert "month" in data
        assert "total_employees" in data
        assert "days_in_month" in data
        assert "trend" in data
        assert data["month"] == TEST_MONTH
        
        trend = data["trend"]
        assert isinstance(trend, list)
        assert len(trend) == data["days_in_month"]
        
        if len(trend) > 0:
            day_data = trend[0]
            assert "date" in day_data
            assert "day" in day_data
            assert "present" in day_data
            assert "absent" in day_data
            assert "attendance_percentage" in day_data
            print(f"✓ Monthly Trend ({TEST_MONTH}): {data['days_in_month']} days, {data['total_employees']} employees")
        else:
            print("✓ Monthly Trend: Empty trend data")
    
    # =======================================
    # CENTER COMPARISON ENDPOINT
    # =======================================
    
    def test_center_comparison_endpoint(self, session, auth_token):
        """Test /center-comparison returns monthly attendance comparison across centers"""
        res = session.post(f"{BASE_URL}/api/attendance-dashboard/center-comparison", json={
            "token": auth_token,
            "month": TEST_MONTH
        })
        assert res.status_code == 200, f"Status: {res.status_code}"
        
        data = res.json()
        assert "month" in data
        assert "comparison" in data
        assert data["month"] == TEST_MONTH
        
        comparison = data["comparison"]
        assert isinstance(comparison, list)
        
        if len(comparison) > 0:
            center = comparison[0]
            assert "center_code" in center
            assert "total_employees" in center
            assert "total_present" in center
            assert "total_absent" in center
            assert "attendance_percentage" in center
            print(f"✓ Center Comparison ({TEST_MONTH}): {len(comparison)} centers")
            print(f"  Top center: {center['center_code']} - {center['attendance_percentage']}%")
        else:
            print("✓ Center Comparison: No comparison data")
    
    # =======================================
    # EXPORT ENDPOINTS
    # =======================================
    
    def test_export_daily_attendance(self, session, auth_token):
        """Test /export returns Excel file for daily attendance"""
        res = session.post(f"{BASE_URL}/api/attendance-dashboard/export", json={
            "token": auth_token,
            "date": TEST_DATE,
            "center": None
        })
        assert res.status_code == 200, f"Status: {res.status_code}"
        
        # Check content type is Excel
        content_type = res.headers.get("Content-Type", "")
        assert "spreadsheetml" in content_type or "application/vnd" in content_type, f"Expected Excel content type, got: {content_type}"
        
        # Check Content-Disposition header
        content_disp = res.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp
        assert ".xlsx" in content_disp
        
        # Check file has content
        assert len(res.content) > 0, "Export file is empty"
        print(f"✓ Daily Export: {len(res.content)} bytes, Content-Type: {content_type}")
    
    def test_export_monthly_attendance(self, session, auth_token):
        """Test /export-monthly returns Excel file for monthly attendance"""
        res = session.post(f"{BASE_URL}/api/attendance-dashboard/export-monthly", json={
            "token": auth_token,
            "month": TEST_MONTH,
            "center": None
        })
        assert res.status_code == 200, f"Status: {res.status_code}"
        
        # Check content type is Excel
        content_type = res.headers.get("Content-Type", "")
        assert "spreadsheetml" in content_type or "application/vnd" in content_type, f"Expected Excel content type, got: {content_type}"
        
        # Check file has content
        assert len(res.content) > 0, "Export file is empty"
        print(f"✓ Monthly Export: {len(res.content)} bytes")
    
    def test_export_with_center_filter(self, session, auth_token):
        """Test /export with center filter"""
        res = session.post(f"{BASE_URL}/api/attendance-dashboard/export", json={
            "token": auth_token,
            "date": TEST_DATE,
            "center": "PB-MGT"
        })
        assert res.status_code == 200, f"Status: {res.status_code}"
        
        content_disp = res.headers.get("Content-Disposition", "")
        assert "PB-MGT" in content_disp or "attachment" in content_disp
        print("✓ Export with center filter works")
    
    # =======================================
    # EDIT ENDPOINT (SUPER ADMIN ONLY)
    # =======================================
    
    def test_edit_attendance_success(self, session, auth_token):
        """Test /edit allows Super Admin to edit attendance"""
        # First get an employee from a center
        detail_res = session.post(f"{BASE_URL}/api/attendance-dashboard/center-detail", json={
            "token": auth_token,
            "center": "PB-MGT",
            "date": TEST_DATE
        })
        
        if detail_res.status_code != 200:
            pytest.skip("Could not get center detail for edit test")
        
        employees = detail_res.json().get("employees", [])
        if len(employees) == 0:
            pytest.skip("No employees available for edit test")
        
        test_employee = employees[0]["name"]
        original_status = employees[0]["status"]
        
        # Edit to a different status
        new_status = "L" if original_status != "L" else "P"
        
        res = session.post(f"{BASE_URL}/api/attendance-dashboard/edit", json={
            "token": auth_token,
            "center": "PB-MGT",
            "date": TEST_DATE,
            "employee_name": test_employee,
            "status": new_status,
            "notes": "TEST edit by testing agent"
        })
        assert res.status_code == 200, f"Status: {res.status_code}, Body: {res.text}"
        
        data = res.json()
        assert data.get("success") == True
        print(f"✓ Edit attendance: {test_employee} changed to {new_status}")
        
        # Restore original status
        restore_res = session.post(f"{BASE_URL}/api/attendance-dashboard/edit", json={
            "token": auth_token,
            "center": "PB-MGT",
            "date": TEST_DATE,
            "employee_name": test_employee,
            "status": original_status if original_status else "P",
            "notes": "Restored by testing agent"
        })
        assert restore_res.status_code == 200
        print(f"✓ Restored original status: {original_status if original_status else 'P'}")
    
    def test_edit_invalid_status(self, session, auth_token):
        """Test /edit rejects invalid status codes"""
        res = session.post(f"{BASE_URL}/api/attendance-dashboard/edit", json={
            "token": auth_token,
            "center": "PB-MGT",
            "date": TEST_DATE,
            "employee_name": "TEST EMPLOYEE",
            "status": "INVALID_STATUS",
            "notes": ""
        })
        assert res.status_code == 400, f"Expected 400, got {res.status_code}"
        print("✓ Edit: Invalid status returns 400")
    
    def test_edit_invalid_token(self, session):
        """Test /edit returns 401 for invalid token"""
        res = session.post(f"{BASE_URL}/api/attendance-dashboard/edit", json={
            "token": "invalid_token",
            "center": "PB-MGT",
            "date": TEST_DATE,
            "employee_name": "TEST",
            "status": "P",
            "notes": ""
        })
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"
        print("✓ Edit: Invalid token returns 401")
    
    # =======================================
    # ACCESS CONTROL TESTS
    # =======================================
    
    def test_access_denied_without_admin_role(self, session):
        """Test endpoints return 401/403 without proper authentication"""
        # Test without token
        res = session.post(f"{BASE_URL}/api/attendance-dashboard/summary", json={
            "date": TEST_DATE
        })
        # Should fail - either 422 (validation) or 401 (auth)
        assert res.status_code in [401, 422], f"Expected 401/422, got {res.status_code}"
        print("✓ Access control: Request without token rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
