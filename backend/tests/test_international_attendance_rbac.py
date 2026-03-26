"""
Test International Attendance RBAC and Data Save Bug Fix
=========================================================
Tests:
1. Super Admin (PB-MGT) sees dropdown with ONLY international centers
2. Perth Manager sees fixed badge (no dropdown), only their center
3. India Manager (PB-HSR) gets 403 Access Denied
4. Data save bug: Different employees can have different hours
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN = {"center": "PB-MGT", "mobile": "9741399190", "otp": "123456"}
PERTH_MANAGER = {"center": "PB-PERTH", "mobile": "0401832922", "otp": "123456"}
INDIA_MANAGER = {"center": "PB-HSR", "mobile": "9999999999", "otp": "123456"}


class TestAuthentication:
    """Test login flows for different user types"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get Super Admin token"""
        # Send OTP
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN["center"],
            "mobile": SUPER_ADMIN["mobile"]
        })
        assert res.status_code == 200, f"Send OTP failed: {res.text}"
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN["center"],
            "mobile": SUPER_ADMIN["mobile"],
            "otp": SUPER_ADMIN["otp"]
        })
        assert res.status_code == 200, f"Verify OTP failed: {res.text}"
        data = res.json()
        assert "token" in data, "No token in response"
        assert data.get("is_super_admin") == True, "Should be super admin"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def perth_manager_token(self):
        """Get Perth Manager token"""
        # Send OTP
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": PERTH_MANAGER["center"],
            "mobile": PERTH_MANAGER["mobile"]
        })
        assert res.status_code == 200, f"Send OTP failed: {res.text}"
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": PERTH_MANAGER["center"],
            "mobile": PERTH_MANAGER["mobile"],
            "otp": PERTH_MANAGER["otp"]
        })
        assert res.status_code == 200, f"Verify OTP failed: {res.text}"
        data = res.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def india_manager_token(self):
        """Get India Manager token"""
        # Send OTP
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": INDIA_MANAGER["center"],
            "mobile": INDIA_MANAGER["mobile"]
        })
        assert res.status_code == 200, f"Send OTP failed: {res.text}"
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": INDIA_MANAGER["center"],
            "mobile": INDIA_MANAGER["mobile"],
            "otp": INDIA_MANAGER["otp"]
        })
        assert res.status_code == 200, f"Verify OTP failed: {res.text}"
        data = res.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_super_admin_login(self, super_admin_token):
        """Test Super Admin login returns is_super_admin=true"""
        assert super_admin_token is not None
        print(f"✓ Super Admin token obtained")
    
    def test_perth_manager_login(self, perth_manager_token):
        """Test Perth Manager login"""
        assert perth_manager_token is not None
        print(f"✓ Perth Manager token obtained")
    
    def test_india_manager_login(self, india_manager_token):
        """Test India Manager login"""
        assert india_manager_token is not None
        print(f"✓ India Manager token obtained")


class TestInternationalCentersRBAC:
    """Test RBAC for /api/international-attendance/centers endpoint"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get Super Admin token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN["center"],
            "mobile": SUPER_ADMIN["mobile"]
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN["center"],
            "mobile": SUPER_ADMIN["mobile"],
            "otp": SUPER_ADMIN["otp"]
        })
        return res.json()["token"]
    
    @pytest.fixture(scope="class")
    def perth_manager_token(self):
        """Get Perth Manager token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": PERTH_MANAGER["center"],
            "mobile": PERTH_MANAGER["mobile"]
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": PERTH_MANAGER["center"],
            "mobile": PERTH_MANAGER["mobile"],
            "otp": PERTH_MANAGER["otp"]
        })
        return res.json()["token"]
    
    @pytest.fixture(scope="class")
    def india_manager_token(self):
        """Get India Manager token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": INDIA_MANAGER["center"],
            "mobile": INDIA_MANAGER["mobile"]
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": INDIA_MANAGER["center"],
            "mobile": INDIA_MANAGER["mobile"],
            "otp": INDIA_MANAGER["otp"]
        })
        return res.json()["token"]
    
    def test_super_admin_sees_dropdown_with_international_centers_only(self, super_admin_token):
        """
        Test 1 & 5: Super Admin should see:
        - show_dropdown=true
        - ONLY international centers (is_india_center=false)
        - Should include PB-PERTH
        - Should NOT include India centers like PB-HSR
        """
        res = requests.get(f"{BASE_URL}/api/international-attendance/centers", params={
            "token": super_admin_token
        })
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert data.get("success") == True, "Response should be successful"
        assert data.get("show_dropdown") == True, "Super Admin should see dropdown"
        
        centers = data.get("centers", [])
        assert len(centers) > 0, "Should have at least one international center"
        
        # Check that PB-PERTH is in the list
        center_codes = [c.get("code") for c in centers]
        assert "PB-PERTH" in center_codes, f"PB-PERTH should be in centers list: {center_codes}"
        
        # Check that NO India centers are in the list
        india_centers = ["PB-HSR", "PB-TH", "PB-SN", "PB-DV", "PB-HW", "PB-KN", "PB-KAL"]
        for india_code in india_centers:
            assert india_code not in center_codes, f"India center {india_code} should NOT be in international centers list"
        
        # Verify all returned centers have is_india_center=false or not set
        for center in centers:
            is_india = center.get("is_india_center", False)
            assert is_india != True, f"Center {center.get('code')} should not be an India center"
        
        print(f"✓ Super Admin sees dropdown with {len(centers)} international centers: {center_codes}")
    
    def test_perth_manager_no_dropdown_only_own_center(self, perth_manager_token):
        """
        Test 2 & 6: Perth Manager should see:
        - show_dropdown=false
        - Only their own center (PB-PERTH)
        """
        res = requests.get(f"{BASE_URL}/api/international-attendance/centers", params={
            "token": perth_manager_token
        })
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert data.get("success") == True, "Response should be successful"
        assert data.get("show_dropdown") == False, "Perth Manager should NOT see dropdown"
        
        centers = data.get("centers", [])
        assert len(centers) == 1, f"Perth Manager should see only 1 center, got {len(centers)}"
        
        center = centers[0]
        assert center.get("code") == "PB-PERTH", f"Expected PB-PERTH, got {center.get('code')}"
        
        print(f"✓ Perth Manager sees fixed badge with only PB-PERTH (no dropdown)")
    
    def test_india_manager_gets_403_forbidden(self, india_manager_token):
        """
        Test 3 & 4: India Manager (PB-HSR) should get 403 Forbidden
        with message about India centers not having access
        """
        res = requests.get(f"{BASE_URL}/api/international-attendance/centers", params={
            "token": india_manager_token
        })
        assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"
        
        data = res.json()
        detail = data.get("detail", "")
        assert "India" in detail or "not available" in detail.lower(), f"Error should mention India centers: {detail}"
        
        print(f"✓ India Manager gets 403 Forbidden: {detail}")


class TestDataSaveBug:
    """
    Test 7: Data Save Bug Fix
    Save different hours for different employees and verify they persist correctly
    """
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get Super Admin token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN["center"],
            "mobile": SUPER_ADMIN["mobile"]
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN["center"],
            "mobile": SUPER_ADMIN["mobile"],
            "otp": SUPER_ADMIN["otp"]
        })
        return res.json()["token"]
    
    def test_save_different_hours_for_different_employees(self, super_admin_token):
        """
        Save hours for employee A=8, employee B=4
        Then fetch week-data and verify each employee has DIFFERENT hours
        """
        # First, get employees for PB-PERTH
        res = requests.post(f"{BASE_URL}/api/international-attendance/employees", json={
            "token": super_admin_token,
            "center": "PB-PERTH"
        })
        assert res.status_code == 200, f"Get employees failed: {res.text}"
        
        employees = res.json().get("employees", [])
        assert len(employees) >= 2, f"Need at least 2 employees for this test, got {len(employees)}"
        
        # Get first two employees
        emp_a = employees[0]
        emp_b = employees[1]
        emp_a_id = emp_a.get("employee_id")
        emp_b_id = emp_b.get("employee_id")
        
        print(f"Testing with employees: {emp_a.get('name')} ({emp_a_id}) and {emp_b.get('name')} ({emp_b_id})")
        
        # Save different hours for each employee
        # Employee A: 8 hours on Monday
        # Employee B: 4 hours on Monday
        entries = [
            {
                "employee_id": emp_a_id,
                "hours": {"mon": 8, "tue": 0, "wed": 0, "thu": 0, "fri": 0, "sat": 0, "sun": 0}
            },
            {
                "employee_id": emp_b_id,
                "hours": {"mon": 4, "tue": 0, "wed": 0, "thu": 0, "fri": 0, "sat": 0, "sun": 0}
            }
        ]
        
        # Use current year/month and week 1
        from datetime import datetime
        now = datetime.now()
        year = now.year
        month = now.month
        week = 1
        
        res = requests.post(f"{BASE_URL}/api/international-attendance/save", json={
            "token": super_admin_token,
            "center": "PB-PERTH",
            "year": year,
            "month": month,
            "week": week,
            "entries": entries
        })
        assert res.status_code == 200, f"Save attendance failed: {res.text}"
        
        save_data = res.json()
        assert save_data.get("success") == True, f"Save should be successful: {save_data}"
        print(f"✓ Saved attendance: {save_data.get('saved_count')} records")
        
        # Now fetch week-data and verify hours are different
        res = requests.post(f"{BASE_URL}/api/international-attendance/week-data", json={
            "token": super_admin_token,
            "center": "PB-PERTH",
            "year": year,
            "month": month,
            "week": week
        })
        assert res.status_code == 200, f"Get week-data failed: {res.text}"
        
        week_data = res.json()
        assert week_data.get("success") == True, "Week data should be successful"
        
        employees_data = week_data.get("employees", [])
        
        # Find our two employees in the response
        emp_a_data = None
        emp_b_data = None
        for emp in employees_data:
            if emp.get("employee_id") == emp_a_id:
                emp_a_data = emp
            elif emp.get("employee_id") == emp_b_id:
                emp_b_data = emp
        
        assert emp_a_data is not None, f"Employee A ({emp_a_id}) not found in response"
        assert emp_b_data is not None, f"Employee B ({emp_b_id}) not found in response"
        
        # Verify hours are DIFFERENT
        emp_a_mon_hours = emp_a_data.get("hours", {}).get("mon", 0)
        emp_b_mon_hours = emp_b_data.get("hours", {}).get("mon", 0)
        
        print(f"Employee A ({emp_a.get('name')}) Monday hours: {emp_a_mon_hours}")
        print(f"Employee B ({emp_b.get('name')}) Monday hours: {emp_b_mon_hours}")
        
        # The bug was that all employees got the same hours
        # After fix, they should have different hours
        assert emp_a_mon_hours == 8, f"Employee A should have 8 hours, got {emp_a_mon_hours}"
        assert emp_b_mon_hours == 4, f"Employee B should have 4 hours, got {emp_b_mon_hours}"
        assert emp_a_mon_hours != emp_b_mon_hours, "Hours should be DIFFERENT for different employees (bug fix verification)"
        
        print(f"✓ DATA SAVE BUG FIXED: Different employees have different hours!")


class TestWeekDataEndpoint:
    """Test week-data endpoint access control"""
    
    @pytest.fixture(scope="class")
    def perth_manager_token(self):
        """Get Perth Manager token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": PERTH_MANAGER["center"],
            "mobile": PERTH_MANAGER["mobile"]
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": PERTH_MANAGER["center"],
            "mobile": PERTH_MANAGER["mobile"],
            "otp": PERTH_MANAGER["otp"]
        })
        return res.json()["token"]
    
    @pytest.fixture(scope="class")
    def india_manager_token(self):
        """Get India Manager token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": INDIA_MANAGER["center"],
            "mobile": INDIA_MANAGER["mobile"]
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": INDIA_MANAGER["center"],
            "mobile": INDIA_MANAGER["mobile"],
            "otp": INDIA_MANAGER["otp"]
        })
        return res.json()["token"]
    
    def test_perth_manager_can_access_own_center_week_data(self, perth_manager_token):
        """Perth Manager can access their own center's week data"""
        from datetime import datetime
        now = datetime.now()
        
        res = requests.post(f"{BASE_URL}/api/international-attendance/week-data", json={
            "token": perth_manager_token,
            "center": "PB-PERTH",
            "year": now.year,
            "month": now.month,
            "week": 1
        })
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert data.get("success") == True, "Should be successful"
        print(f"✓ Perth Manager can access PB-PERTH week data")
    
    def test_india_manager_cannot_access_week_data(self, india_manager_token):
        """India Manager cannot access international attendance week data"""
        from datetime import datetime
        now = datetime.now()
        
        res = requests.post(f"{BASE_URL}/api/international-attendance/week-data", json={
            "token": india_manager_token,
            "center": "PB-PERTH",
            "year": now.year,
            "month": now.month,
            "week": 1
        })
        assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"
        print(f"✓ India Manager correctly denied access to week data")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
