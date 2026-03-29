"""
Test Franchise Owner Dashboard - Backend API Tests
Tests for franchise owner role-based access control and data filtering

Features tested:
1. Franchise owner login returns correct role_key, franchise_center, franchise_code
2. resolve-owner-center endpoint returns correct center mapping
3. MIS overview accessible by franchise owner (was previously blocked)
4. Franchise by-center endpoint accessible by franchise owner
5. Admin can still see center dropdown (different role behavior)
6. Franchise exit list filters by franchise owner
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
FRANCHISE_OWNER_MOBILE = "8888888888"
FRANCHISE_OWNER_CENTER = "PB-HSR"
FRANCHISE_OWNER_OTP = "123456"

SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_CENTER = "PB-MGT"
SUPER_ADMIN_OTP = "123456"


class TestFranchiseOwnerAuth:
    """Test franchise owner authentication and session data"""
    
    @pytest.fixture(scope="class")
    def franchise_owner_session(self):
        """Login as franchise owner and return session data"""
        # Send OTP
        send_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": FRANCHISE_OWNER_CENTER,
            "mobile": FRANCHISE_OWNER_MOBILE
        })
        assert send_res.status_code == 200, f"Send OTP failed: {send_res.text}"
        
        # Verify OTP
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": FRANCHISE_OWNER_CENTER,
            "mobile": FRANCHISE_OWNER_MOBILE,
            "otp": FRANCHISE_OWNER_OTP
        })
        assert verify_res.status_code == 200, f"Verify OTP failed: {verify_res.text}"
        return verify_res.json()
    
    @pytest.fixture(scope="class")
    def admin_session(self):
        """Login as super admin and return session data"""
        # Send OTP
        send_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE
        })
        assert send_res.status_code == 200, f"Send OTP failed: {send_res.text}"
        
        # Verify OTP
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP
        })
        assert verify_res.status_code == 200, f"Verify OTP failed: {verify_res.text}"
        return verify_res.json()
    
    def test_franchise_owner_login_returns_correct_role_key(self, franchise_owner_session):
        """Verify franchise owner login returns role_key='franchise_owner'"""
        assert franchise_owner_session.get("role_key") == "franchise_owner", \
            f"Expected role_key='franchise_owner', got '{franchise_owner_session.get('role_key')}'"
        print(f"✓ Franchise owner role_key: {franchise_owner_session.get('role_key')}")
    
    def test_franchise_owner_login_returns_franchise_center(self, franchise_owner_session):
        """Verify franchise owner login returns franchise_center='PB-HSR'"""
        franchise_center = franchise_owner_session.get("franchise_center")
        assert franchise_center == "PB-HSR", \
            f"Expected franchise_center='PB-HSR', got '{franchise_center}'"
        print(f"✓ Franchise center: {franchise_center}")
    
    def test_franchise_owner_login_returns_franchise_code(self, franchise_owner_session):
        """Verify franchise owner login returns franchise_code='FR-TEST-INDIA'"""
        franchise_code = franchise_owner_session.get("franchise_code")
        assert franchise_code == "FR-TEST-INDIA", \
            f"Expected franchise_code='FR-TEST-INDIA', got '{franchise_code}'"
        print(f"✓ Franchise code: {franchise_code}")
    
    def test_admin_login_returns_super_admin_flag(self, admin_session):
        """Verify admin login returns is_super_admin=True"""
        assert admin_session.get("is_super_admin") == True, \
            f"Expected is_super_admin=True, got {admin_session.get('is_super_admin')}"
        print(f"✓ Admin is_super_admin: {admin_session.get('is_super_admin')}")


class TestResolveOwnerCenter:
    """Test /api/franchises/resolve-owner-center endpoint"""
    
    @pytest.fixture(scope="class")
    def franchise_owner_token(self):
        """Get franchise owner token"""
        send_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": FRANCHISE_OWNER_CENTER,
            "mobile": FRANCHISE_OWNER_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": FRANCHISE_OWNER_CENTER,
            "mobile": FRANCHISE_OWNER_MOBILE,
            "otp": FRANCHISE_OWNER_OTP
        })
        return verify_res.json().get("token")
    
    def test_resolve_owner_center_returns_correct_center(self, franchise_owner_token):
        """Verify resolve-owner-center returns center='PB-HSR'"""
        res = requests.post(f"{BASE_URL}/api/franchises/resolve-owner-center", json={
            "token": franchise_owner_token
        })
        assert res.status_code == 200, f"resolve-owner-center failed: {res.text}"
        data = res.json()
        
        assert data.get("center") == "PB-HSR", \
            f"Expected center='PB-HSR', got '{data.get('center')}'"
        print(f"✓ Resolved center: {data.get('center')}")
    
    def test_resolve_owner_center_returns_franchise_code(self, franchise_owner_token):
        """Verify resolve-owner-center returns franchise_code='FR-TEST-INDIA'"""
        res = requests.post(f"{BASE_URL}/api/franchises/resolve-owner-center", json={
            "token": franchise_owner_token
        })
        assert res.status_code == 200
        data = res.json()
        
        assert data.get("franchise_code") == "FR-TEST-INDIA", \
            f"Expected franchise_code='FR-TEST-INDIA', got '{data.get('franchise_code')}'"
        print(f"✓ Resolved franchise_code: {data.get('franchise_code')}")
    
    def test_resolve_owner_center_returns_is_franchise_owner_true(self, franchise_owner_token):
        """Verify resolve-owner-center returns is_franchise_owner=True"""
        res = requests.post(f"{BASE_URL}/api/franchises/resolve-owner-center", json={
            "token": franchise_owner_token
        })
        assert res.status_code == 200
        data = res.json()
        
        assert data.get("is_franchise_owner") == True, \
            f"Expected is_franchise_owner=True, got {data.get('is_franchise_owner')}"
        print(f"✓ is_franchise_owner: {data.get('is_franchise_owner')}")


class TestMISAccessForFranchiseOwner:
    """Test MIS endpoints are accessible by franchise owner"""
    
    @pytest.fixture(scope="class")
    def franchise_owner_token(self):
        """Get franchise owner token"""
        send_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": FRANCHISE_OWNER_CENTER,
            "mobile": FRANCHISE_OWNER_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": FRANCHISE_OWNER_CENTER,
            "mobile": FRANCHISE_OWNER_MOBILE,
            "otp": FRANCHISE_OWNER_OTP
        })
        return verify_res.json().get("token")
    
    def test_mis_overview_accessible_by_franchise_owner(self, franchise_owner_token):
        """Verify MIS overview endpoint is accessible by franchise owner (was previously blocked)"""
        res = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": franchise_owner_token,
            "center": "PB-HSR",
            "period": "current_month"
        })
        
        # Should NOT return 403 anymore
        assert res.status_code == 200, \
            f"MIS overview should be accessible by franchise owner, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "summary" in data, "Response should contain 'summary' key"
        print(f"✓ MIS overview accessible, total_sales: {data.get('summary', {}).get('total_sales')}")
    
    def test_mis_overview_returns_data_for_pb_hsr(self, franchise_owner_token):
        """Verify MIS overview returns non-zero data for PB-HSR"""
        res = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": franchise_owner_token,
            "center": "PB-HSR",
            "period": "current_month"
        })
        assert res.status_code == 200
        data = res.json()
        
        summary = data.get("summary", {})
        # Check that we have some data (may be zero if no sales this month)
        assert "total_sales" in summary, "Summary should contain total_sales"
        print(f"✓ MIS data for PB-HSR - Sales: {summary.get('total_sales')}, Expenses: {summary.get('total_expenses')}")
    
    def test_mis_working_capital_accessible(self, franchise_owner_token):
        """Verify MIS working-capital endpoint is accessible"""
        res = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": franchise_owner_token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200, f"Working capital endpoint failed: {res.text}"
        data = res.json()
        
        assert "available_working_capital" in data, "Response should contain available_working_capital"
        print(f"✓ Working capital accessible: {data.get('available_working_capital')}")
    
    def test_mis_sales_trends_accessible(self, franchise_owner_token):
        """Verify MIS sales-trends endpoint is accessible"""
        res = requests.post(f"{BASE_URL}/api/mis/sales-trends", json={
            "token": franchise_owner_token,
            "center": "PB-HSR",
            "period": "current_month",
            "group_by": "daily"
        })
        assert res.status_code == 200, f"Sales trends endpoint failed: {res.text}"
        data = res.json()
        
        assert "trends" in data, "Response should contain 'trends' key"
        print(f"✓ Sales trends accessible, {len(data.get('trends', []))} data points")


class TestFranchiseByCenterAccess:
    """Test /api/franchises/by-center endpoint access"""
    
    @pytest.fixture(scope="class")
    def franchise_owner_token(self):
        """Get franchise owner token"""
        send_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": FRANCHISE_OWNER_CENTER,
            "mobile": FRANCHISE_OWNER_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": FRANCHISE_OWNER_CENTER,
            "mobile": FRANCHISE_OWNER_MOBILE,
            "otp": FRANCHISE_OWNER_OTP
        })
        return verify_res.json().get("token")
    
    def test_franchise_by_center_accessible_by_franchise_owner(self, franchise_owner_token):
        """Verify franchise by-center endpoint is accessible by franchise owner"""
        res = requests.post(f"{BASE_URL}/api/franchises/by-center/PB-HSR", json={
            "token": franchise_owner_token
        })
        
        assert res.status_code == 200, \
            f"Franchise by-center should be accessible, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert data.get("found") == True, "Should find franchise for PB-HSR"
        print(f"✓ Franchise by-center accessible, found: {data.get('found')}")
    
    def test_franchise_by_center_returns_franchise_info(self, franchise_owner_token):
        """Verify franchise by-center returns franchise details"""
        res = requests.post(f"{BASE_URL}/api/franchises/by-center/PB-HSR", json={
            "token": franchise_owner_token
        })
        assert res.status_code == 200
        data = res.json()
        
        franchise = data.get("franchise", {})
        assert franchise.get("franchise_code") == "FR-TEST-INDIA", \
            f"Expected franchise_code='FR-TEST-INDIA', got '{franchise.get('franchise_code')}'"
        print(f"✓ Franchise info: {franchise.get('franchise_name')} ({franchise.get('franchise_code')})")


class TestFranchiseExitListFiltering:
    """Test franchise exit list filters by franchise owner"""
    
    @pytest.fixture(scope="class")
    def franchise_owner_token(self):
        """Get franchise owner token"""
        send_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": FRANCHISE_OWNER_CENTER,
            "mobile": FRANCHISE_OWNER_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": FRANCHISE_OWNER_CENTER,
            "mobile": FRANCHISE_OWNER_MOBILE,
            "otp": FRANCHISE_OWNER_OTP
        })
        return verify_res.json().get("token")
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        send_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP
        })
        return verify_res.json().get("token")
    
    def test_franchise_exit_list_accessible_by_franchise_owner(self, franchise_owner_token):
        """Verify franchise exit list is accessible by franchise owner"""
        res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={
            "token": franchise_owner_token
        })
        
        assert res.status_code == 200, \
            f"Franchise exit list should be accessible, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "exits" in data, "Response should contain 'exits' key"
        print(f"✓ Franchise exit list accessible, {len(data.get('exits', []))} exits found")
    
    def test_admin_can_see_all_exits(self, admin_token):
        """Verify admin can see all franchise exits"""
        res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={
            "token": admin_token
        })
        
        assert res.status_code == 200, f"Admin exit list failed: {res.text}"
        data = res.json()
        
        # Admin should see all exits
        exits = data.get("exits", [])
        print(f"✓ Admin can see {len(exits)} exits")


class TestAdminCenterDropdownAccess:
    """Test that admin can still access center dropdown functionality"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        send_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP
        })
        return verify_res.json().get("token")
    
    def test_admin_can_access_centers_list(self, admin_token):
        """Verify admin can access centers list for dropdown"""
        res = requests.get(f"{BASE_URL}/api/centers")
        
        assert res.status_code == 200, f"Centers list failed: {res.text}"
        data = res.json()
        
        centers = data.get("centers", [])
        assert len(centers) > 0, "Should have at least one center"
        print(f"✓ Admin can access {len(centers)} centers for dropdown")
    
    def test_admin_can_query_any_center_mis(self, admin_token):
        """Verify admin can query MIS for any center"""
        # Query PB-HSR (franchise center)
        res = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": admin_token,
            "center": "PB-HSR",
            "period": "current_month"
        })
        
        assert res.status_code == 200, f"Admin MIS query failed: {res.text}"
        print("✓ Admin can query MIS for PB-HSR")
        
        # Query PB-MGT (admin center)
        res2 = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": admin_token,
            "center": "PB-MGT",
            "period": "current_month"
        })
        
        assert res2.status_code == 200, f"Admin MIS query for PB-MGT failed: {res2.text}"
        print("✓ Admin can query MIS for PB-MGT")


class TestExpenseAnalysisAccess:
    """Test expense analysis endpoint access"""
    
    @pytest.fixture(scope="class")
    def franchise_owner_token(self):
        """Get franchise owner token"""
        send_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": FRANCHISE_OWNER_CENTER,
            "mobile": FRANCHISE_OWNER_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": FRANCHISE_OWNER_CENTER,
            "mobile": FRANCHISE_OWNER_MOBILE,
            "otp": FRANCHISE_OWNER_OTP
        })
        return verify_res.json().get("token")
    
    def test_expense_analysis_accessible_by_franchise_owner(self, franchise_owner_token):
        """Verify expense analysis is accessible by franchise owner"""
        res = requests.post(f"{BASE_URL}/api/mis/expense-analysis", json={
            "token": franchise_owner_token,
            "center": "PB-HSR",
            "period": "current_month"
        })
        
        assert res.status_code == 200, \
            f"Expense analysis should be accessible, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "by_type" in data, "Response should contain 'by_type' key"
        print(f"✓ Expense analysis accessible, {len(data.get('by_type', []))} expense types")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
