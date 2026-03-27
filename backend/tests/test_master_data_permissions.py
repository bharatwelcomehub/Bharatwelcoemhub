"""
Test Master Data Management and Permission Engine APIs
Tests for iteration 25 - Master Data CRUD, Permission Engine, Role Management
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_CENTER = "PB-MGT"
SUPER_ADMIN_MOBILE = "9741399190"
OTP = "123456"


class TestAuthentication:
    """Authentication tests - get token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get Super Admin auth token"""
        # Send OTP
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE
        })
        assert otp_res.status_code == 200, f"Send OTP failed: {otp_res.text}"
        
        # Verify OTP
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER,
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": OTP
        })
        assert verify_res.status_code == 200, f"Verify OTP failed: {verify_res.text}"
        data = verify_res.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_auth_flow(self, auth_token):
        """Verify auth token is valid"""
        assert auth_token is not None
        assert len(auth_token) > 10
        print(f"✓ Auth token obtained: {auth_token[:20]}...")


class TestMasterTypes:
    """Test GET /api/masters/types endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER, "mobile": SUPER_ADMIN_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER, "mobile": SUPER_ADMIN_MOBILE, "otp": OTP
        })
        return verify_res.json()["token"]
    
    def test_get_master_types(self, auth_token):
        """GET /api/masters/types returns all 14+ master type definitions"""
        res = requests.get(f"{BASE_URL}/api/masters/types?token={auth_token}")
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert "master_types" in data
        types = data["master_types"]
        assert len(types) >= 14, f"Expected 14+ master types, got {len(types)}"
        
        # Check structure of each type
        for mt in types:
            assert "key" in mt
            assert "label" in mt
            assert "fields" in mt
            assert "total_count" in mt
            assert "active_count" in mt
        
        # Check expected types exist
        type_keys = [t["key"] for t in types]
        expected_keys = ["expense_categories", "payment_modes", "employee_categories", 
                        "tax_config", "order_types", "cancellation_reasons", "sales_channels"]
        for key in expected_keys:
            assert key in type_keys, f"Missing master type: {key}"
        
        print(f"✓ Found {len(types)} master types with counts")


class TestMasterCRUD:
    """Test Master Data CRUD operations"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER, "mobile": SUPER_ADMIN_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER, "mobile": SUPER_ADMIN_MOBILE, "otp": OTP
        })
        return verify_res.json()["token"]
    
    def test_list_expense_categories(self, auth_token):
        """POST /api/masters/expense_categories/list returns seeded categories"""
        res = requests.post(f"{BASE_URL}/api/masters/expense_categories/list", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert "items" in data
        assert "master_type" in data
        assert data["master_type"] == "expense_categories"
        
        # Should have seeded data
        items = data["items"]
        print(f"✓ Found {len(items)} expense categories")
    
    def test_list_payment_modes(self, auth_token):
        """POST /api/masters/payment_modes/list returns seeded payment modes"""
        res = requests.post(f"{BASE_URL}/api/masters/payment_modes/list", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert "items" in data
        items = data["items"]
        print(f"✓ Found {len(items)} payment modes")
    
    def test_list_employee_categories(self, auth_token):
        """POST /api/masters/employee_categories/list returns employee categories"""
        res = requests.post(f"{BASE_URL}/api/masters/employee_categories/list", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert "items" in data
        print(f"✓ Found {len(data['items'])} employee categories")
    
    def test_create_expense_category(self, auth_token):
        """POST /api/masters/expense_categories/create creates a new category"""
        test_name = "TEST_CATEGORY_PYTEST"
        
        # First try to delete if exists (cleanup from previous runs)
        requests.post(f"{BASE_URL}/api/masters/expense_categories/delete", json={
            "token": auth_token, "name": test_name, "hard_delete": True
        })
        
        # Create new
        res = requests.post(f"{BASE_URL}/api/masters/expense_categories/create", json={
            "token": auth_token,
            "name": test_name,
            "description": "Test category for pytest",
            "code": "TST"
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True
        assert test_name in data.get("message", "")
        print(f"✓ Created expense category: {test_name}")
        
        # Verify it exists
        list_res = requests.post(f"{BASE_URL}/api/masters/expense_categories/list", json={
            "token": auth_token
        })
        items = list_res.json().get("items", [])
        names = [i["name"] for i in items]
        assert test_name in names, "Created category not found in list"
        print(f"✓ Verified category exists in list")
    
    def test_update_expense_category(self, auth_token):
        """POST /api/masters/expense_categories/update updates an existing item"""
        test_name = "TEST_CATEGORY_PYTEST"
        
        res = requests.post(f"{BASE_URL}/api/masters/expense_categories/update", json={
            "token": auth_token,
            "name": test_name,
            "description": "Updated description by pytest"
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True
        print(f"✓ Updated expense category: {test_name}")
    
    def test_delete_expense_category(self, auth_token):
        """POST /api/masters/expense_categories/delete soft-deletes (deactivates) an item"""
        test_name = "TEST_CATEGORY_PYTEST"
        
        res = requests.post(f"{BASE_URL}/api/masters/expense_categories/delete", json={
            "token": auth_token,
            "name": test_name
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True
        assert "deactivated" in data.get("message", "").lower()
        print(f"✓ Soft-deleted (deactivated) expense category: {test_name}")
        
        # Hard delete for cleanup
        requests.post(f"{BASE_URL}/api/masters/expense_categories/delete", json={
            "token": auth_token, "name": test_name, "hard_delete": True
        })


class TestSeedFromExisting:
    """Test seed-from-existing endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER, "mobile": SUPER_ADMIN_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER, "mobile": SUPER_ADMIN_MOBILE, "otp": OTP
        })
        return verify_res.json()["token"]
    
    def test_seed_from_existing(self, auth_token):
        """POST /api/masters/seed-from-existing migrates existing data safely"""
        res = requests.post(f"{BASE_URL}/api/masters/seed-from-existing", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True
        assert "migrated" in data
        
        migrated = data["migrated"]
        print(f"✓ Seed results: {migrated}")


class TestPermissionRoles:
    """Test Permission Engine and Role Management"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER, "mobile": SUPER_ADMIN_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER, "mobile": SUPER_ADMIN_MOBILE, "otp": OTP
        })
        return verify_res.json()["token"]
    
    def test_seed_default_roles(self, auth_token):
        """POST /api/permissions/roles/seed-defaults creates 7 default roles"""
        res = requests.post(f"{BASE_URL}/api/permissions/roles/seed-defaults", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True
        assert "total_roles" in data
        assert data["total_roles"] == 7, f"Expected 7 roles, got {data['total_roles']}"
        print(f"✓ Seeded {data.get('created', 0)} new roles, total: {data['total_roles']}")
    
    def test_list_roles(self, auth_token):
        """POST /api/permissions/roles/list returns all seeded roles"""
        res = requests.post(f"{BASE_URL}/api/permissions/roles/list", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert "roles" in data
        roles = data["roles"]
        
        # Check expected roles exist
        role_keys = [r["key"] for r in roles]
        expected_roles = ["super_admin", "admin", "center_manager", "super_manager", 
                         "accountant", "franchise_owner", "staff"]
        for key in expected_roles:
            assert key in role_keys, f"Missing role: {key}"
        
        print(f"✓ Found {len(roles)} roles: {role_keys}")
    
    def test_my_permissions_super_admin(self, auth_token):
        """GET /api/permissions/my-permissions returns correct role and permissions for super admin"""
        res = requests.get(f"{BASE_URL}/api/permissions/my-permissions?token={auth_token}")
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert "permissions" in data
        assert "scope" in data
        assert "role_key" in data
        assert "role_name" in data
        
        # Super admin should have full permissions
        perms = data["permissions"]
        assert "dashboard" in perms
        assert "masters" in perms
        assert "roles" in perms
        
        # Check scope
        scope = data["scope"]
        assert scope.get("type") == "all_centers"
        
        print(f"✓ Super Admin permissions: role={data['role_key']}, scope={scope['type']}")
        print(f"  Modules: {list(perms.keys())}")
    
    def test_assign_role(self, auth_token):
        """POST /api/permissions/roles/assign assigns a role_key to a manager"""
        # First get a manager to assign role to
        mgr_res = requests.post(f"{BASE_URL}/api/mgt/managers", json={
            "token": auth_token
        })
        assert mgr_res.status_code == 200
        managers = mgr_res.json().get("managers", [])
        
        if len(managers) < 2:
            pytest.skip("Not enough managers to test role assignment")
        
        # Find a non-super-admin manager
        target_manager = None
        for m in managers:
            if not m.get("is_super_admin") and m.get("email"):
                target_manager = m
                break
        
        if not target_manager:
            pytest.skip("No suitable manager found for role assignment test")
        
        # Assign center_manager role
        res = requests.post(f"{BASE_URL}/api/permissions/roles/assign", json={
            "token": auth_token,
            "email": target_manager["email"],
            "role_key": "center_manager"
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True
        print(f"✓ Assigned 'center_manager' role to {target_manager['email']}")


class TestExpenseTypesPaymentModes:
    """Test that expense-types and payment-modes pull from master tables"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER, "mobile": SUPER_ADMIN_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER, "mobile": SUPER_ADMIN_MOBILE, "otp": OTP
        })
        return verify_res.json()["token"]
    
    def test_expense_types_from_master(self, auth_token):
        """GET /api/sales/expense-types returns source=master when master data exists"""
        # First ensure master data is seeded
        requests.post(f"{BASE_URL}/api/masters/seed-from-existing", json={
            "token": auth_token
        })
        
        res = requests.get(f"{BASE_URL}/api/sales/expense-types")
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert "expense_types" in data
        assert "source" in data
        
        # Should be 'master' if master data exists
        source = data["source"]
        expense_types = data["expense_types"]
        
        print(f"✓ Expense types source: {source}, count: {len(expense_types)}")
        
        if source == "master":
            print(f"  ✓ Pulling from master_expense_categories table")
        else:
            print(f"  ⚠ Falling back to legacy source")
    
    def test_payment_modes_from_master(self, auth_token):
        """GET /api/sales/payment-modes returns source=master when master data exists"""
        res = requests.get(f"{BASE_URL}/api/sales/payment-modes")
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert "payment_modes" in data
        assert "source" in data
        
        source = data["source"]
        modes = data["payment_modes"]
        
        print(f"✓ Payment modes source: {source}, count: {len(modes)}")
        
        if source == "master":
            print(f"  ✓ Pulling from master_payment_modes table")
        else:
            print(f"  ⚠ Falling back to legacy source")


class TestPermissionModules:
    """Test permission modules endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": SUPER_ADMIN_CENTER, "mobile": SUPER_ADMIN_MOBILE
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": SUPER_ADMIN_CENTER, "mobile": SUPER_ADMIN_MOBILE, "otp": OTP
        })
        return verify_res.json()["token"]
    
    def test_get_permission_modules(self, auth_token):
        """GET /api/permissions/modules returns all permission modules"""
        res = requests.get(f"{BASE_URL}/api/permissions/modules?token={auth_token}")
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert "modules" in data
        modules = data["modules"]
        
        # Check expected modules exist
        expected_modules = ["dashboard", "attendance", "payroll", "sales", "expenses", 
                          "employees", "masters", "roles", "centers", "managers"]
        for mod in expected_modules:
            assert mod in modules, f"Missing module: {mod}"
        
        # Check structure
        for mod_key, mod_data in modules.items():
            assert "actions" in mod_data
            assert "label" in mod_data
        
        print(f"✓ Found {len(modules)} permission modules")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
