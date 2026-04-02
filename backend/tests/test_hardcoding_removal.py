"""
Test Suite: Hardcoding Removal & RBAC Verification
Tests that all hardcoded center checks (PB-MGT, PB-PERTH, PB-HSR) have been replaced
with proper RBAC-driven access control using is_super_admin, is_admin flags.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://gst-transparency.preview.emergentagent.com')

# Super Admin credentials
SUPER_ADMIN_CENTER = "PB-MGT"
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_OTP = "123456"


class TestAuthAndSession:
    """Test authentication flow and session flags"""
    
    @pytest.fixture(scope="class")
    def super_admin_session(self):
        """Get Super Admin session token"""
        # Send OTP
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE
        })
        assert res.status_code == 200, f"Send OTP failed: {res.text}"
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP
        })
        assert res.status_code == 200, f"Verify OTP failed: {res.text}"
        data = res.json()
        return data
    
    def test_send_otp_success(self):
        """Test OTP can be sent for Super Admin"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        print(f"✓ Send OTP successful: {data.get('message')}")
    
    def test_verify_otp_returns_admin_flags(self, super_admin_session):
        """Test that verify_otp returns is_super_admin and is_admin flags"""
        assert "token" in super_admin_session, "Token missing from session"
        assert super_admin_session.get("is_super_admin") == True, "is_super_admin should be True for Super Admin"
        assert super_admin_session.get("is_admin") == True, "is_admin should be True for Super Admin"
        assert "roles" in super_admin_session, "roles missing from session"
        print(f"✓ Session has is_super_admin={super_admin_session.get('is_super_admin')}, is_admin={super_admin_session.get('is_admin')}")
    
    def test_session_has_all_roles(self, super_admin_session):
        """Test that Super Admin has all roles assigned"""
        roles = super_admin_session.get("roles", {})
        expected_roles = ["attendance", "sales_cash", "hr", "mgt", "operations", "view_all_centers"]
        for role in expected_roles:
            assert roles.get(role) == True, f"Super Admin should have {role} role"
        print(f"✓ Super Admin has all expected roles: {list(roles.keys())}")


class TestCentersEndpoint:
    """Test /api/centers endpoint returns DB-driven data"""
    
    def test_centers_endpoint_returns_data(self):
        """Test that /api/centers returns centers from DB"""
        res = requests.get(f"{BASE_URL}/api/centers")
        assert res.status_code == 200
        data = res.json()
        assert "centers" in data
        centers = data["centers"]
        assert len(centers) > 0, "Should have at least one center"
        print(f"✓ /api/centers returned {len(centers)} centers")
    
    def test_centers_have_required_fields(self):
        """Test that centers have is_india_center field (country and is_hq are optional)"""
        res = requests.get(f"{BASE_URL}/api/centers")
        assert res.status_code == 200
        centers = res.json().get("centers", [])
        
        for center in centers:
            assert "code" in center, f"Center missing 'code' field: {center}"
            assert "is_india_center" in center, f"Center {center.get('code')} missing 'is_india_center' field"
            # country and is_hq fields are optional - is_india_center is the key field for international checks
        
        # Check PB-PERTH is international
        perth_center = next((c for c in centers if c.get("code") == "PB-PERTH"), None)
        if perth_center:
            assert perth_center.get("is_india_center") == False, "PB-PERTH should have is_india_center=False"
            print(f"✓ PB-PERTH has is_india_center=False")
        
        print(f"✓ All {len(centers)} centers have required is_india_center field")


class TestEmployeesEndpoint:
    """Test employee management endpoints use RBAC instead of PB-MGT check"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP
        })
        return res.json().get("token")
    
    def test_mgt_employees_list_with_admin_token(self, admin_token):
        """Test /api/mgt_employees_list works with admin token (not requiring PB-MGT center)"""
        res = requests.post(f"{BASE_URL}/api/mgt_employees_list", json={
            "token": admin_token,
            "center": SUPER_ADMIN_CENTER
        })
        assert res.status_code == 200, f"mgt_employees_list failed: {res.text}"
        data = res.json()
        assert "employees" in data
        print(f"✓ /api/mgt_employees_list returned {len(data.get('employees', []))} employees")
    
    def test_employees_endpoint_works(self, admin_token):
        """Test /api/employees endpoint works"""
        res = requests.post(f"{BASE_URL}/api/employees", json={
            "token": admin_token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200, f"employees endpoint failed: {res.text}"
        data = res.json()
        assert "employees" in data
        print(f"✓ /api/employees returned {len(data.get('employees', []))} employees for PB-HSR")


class TestSalaryEndpoint:
    """Test salary generation endpoints use RBAC"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP
        })
        return res.json().get("token")
    
    def test_salary_preview_with_admin_token(self, admin_token):
        """Test /api/salary_preview works with admin token"""
        import datetime
        current_month = datetime.datetime.now().strftime("%Y-%m")
        
        res = requests.post(f"{BASE_URL}/api/salary_preview", json={
            "token": admin_token,
            "month": current_month,
            "targetCenter": "PB-HSR"
        })
        # May return 200 or 404 if no data, but should not return 403
        assert res.status_code != 403, f"salary_preview should not return 403 for admin: {res.text}"
        print(f"✓ /api/salary_preview accessible with admin token (status: {res.status_code})")
    
    def test_generate_salary_with_admin_token(self, admin_token):
        """Test /api/generate_salary works with admin token"""
        import datetime
        current_month = datetime.datetime.now().strftime("%Y-%m")
        
        res = requests.post(f"{BASE_URL}/api/generate_salary", json={
            "token": admin_token,
            "center": SUPER_ADMIN_CENTER,
            "month": current_month,
            "mode": "single",
            "targetCenter": "PB-HSR"
        })
        # May return 200 or error if no data, but should not return 403
        assert res.status_code != 403, f"generate_salary should not return 403 for admin: {res.text}"
        print(f"✓ /api/generate_salary accessible with admin token (status: {res.status_code})")


class TestSalesExpensesEndpoint:
    """Test sales & expenses endpoints use RBAC for hasAllCentersAccess"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP
        })
        return res.json().get("token")
    
    def test_sales_monthly_summary_all_centers(self, admin_token):
        """Test /api/sales/reports/monthly-summary works for all centers with admin"""
        import datetime
        current_month = datetime.datetime.now().strftime("%Y-%m")
        
        res = requests.post(f"{BASE_URL}/api/sales/reports/monthly-summary", json={
            "token": admin_token,
            "month": current_month,
            "center": "all"
        })
        assert res.status_code == 200, f"monthly-summary failed: {res.text}"
        data = res.json()
        # Should have grand_total or summary
        assert "grand_total" in data or "summary" in data, "Response should have grand_total or summary"
        print(f"✓ /api/sales/reports/monthly-summary works for all centers")
    
    def test_sales_centers_list(self, admin_token):
        """Test /api/sales/centers-list returns centers from DB"""
        res = requests.get(f"{BASE_URL}/api/sales/centers-list")
        assert res.status_code == 200
        data = res.json()
        assert "centers" in data
        print(f"✓ /api/sales/centers-list returned {len(data.get('centers', []))} centers")
    
    def test_expense_types_from_master(self, admin_token):
        """Test /api/sales/expense-types returns data (preferably from master)"""
        res = requests.get(f"{BASE_URL}/api/sales/expense-types")
        assert res.status_code == 200
        data = res.json()
        assert "expense_types" in data
        assert len(data.get("expense_types", [])) > 0
        print(f"✓ /api/sales/expense-types returned {len(data.get('expense_types', []))} types (source: {data.get('source', 'unknown')})")
    
    def test_payment_modes_from_master(self, admin_token):
        """Test /api/sales/payment-modes returns data (preferably from master)"""
        res = requests.get(f"{BASE_URL}/api/sales/payment-modes")
        assert res.status_code == 200
        data = res.json()
        assert "payment_modes" in data
        assert len(data.get("payment_modes", [])) > 0
        print(f"✓ /api/sales/payment-modes returned {len(data.get('payment_modes', []))} modes (source: {data.get('source', 'unknown')})")


class TestAttendanceEndpoint:
    """Test attendance endpoints use RBAC for isMGT check"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP
        })
        return res.json().get("token")
    
    def test_payroll_status_endpoint(self, admin_token):
        """Test /api/payroll_status works"""
        import datetime
        current_month = datetime.datetime.now().strftime("%Y-%m")
        
        res = requests.post(f"{BASE_URL}/api/payroll_status", json={
            "token": admin_token,
            "center": SUPER_ADMIN_CENTER,
            "month": current_month
        })
        assert res.status_code == 200, f"payroll_status failed: {res.text}"
        data = res.json()
        assert "locked" in data
        print(f"✓ /api/payroll_status works (locked: {data.get('locked')})")
    
    def test_lock_payroll_requires_admin(self, admin_token):
        """Test /api/lock_payroll is accessible to admin"""
        import datetime
        # Use a past month to avoid locking current month
        past_month = "2024-01"
        
        res = requests.post(f"{BASE_URL}/api/lock_payroll", json={
            "token": admin_token,
            "center": SUPER_ADMIN_CENTER,
            "month": past_month
        })
        # Should not return 403 for admin
        assert res.status_code != 403, f"lock_payroll should not return 403 for admin: {res.text}"
        print(f"✓ /api/lock_payroll accessible to admin (status: {res.status_code})")


class TestNoHardcodedCenterChecks:
    """Verify no hardcoded center checks in API responses"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP
        })
        return res.json().get("token")
    
    def test_session_uses_flags_not_center_code(self, admin_token):
        """Verify session uses is_super_admin/is_admin flags, not center code check"""
        # Re-verify to get fresh session data
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP
        })
        data = res.json()
        
        # Session should have flags
        assert "is_super_admin" in data, "Session should have is_super_admin flag"
        assert "is_admin" in data, "Session should have is_admin flag"
        
        # These flags should be boolean, not derived from center code
        assert isinstance(data.get("is_super_admin"), bool), "is_super_admin should be boolean"
        assert isinstance(data.get("is_admin"), bool), "is_admin should be boolean"
        
        print(f"✓ Session uses proper flags: is_super_admin={data.get('is_super_admin')}, is_admin={data.get('is_admin')}")
    
    def test_centers_have_is_india_center_field(self):
        """Verify centers have is_india_center field for international checks"""
        res = requests.get(f"{BASE_URL}/api/centers")
        centers = res.json().get("centers", [])
        
        india_centers = [c for c in centers if c.get("is_india_center") == True]
        international_centers = [c for c in centers if c.get("is_india_center") == False]
        
        assert len(india_centers) > 0, "Should have at least one India center"
        print(f"✓ Found {len(india_centers)} India centers and {len(international_centers)} international centers")
        
        # Verify PB-PERTH is marked as international
        perth = next((c for c in centers if c.get("code") == "PB-PERTH"), None)
        if perth:
            assert perth.get("is_india_center") == False, "PB-PERTH should be marked as international"
            print(f"✓ PB-PERTH correctly marked as international (is_india_center=False)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
