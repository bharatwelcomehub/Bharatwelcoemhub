"""
Test Suite for Iteration 41: Document Management & Franchise Integration
Tests document categories, document listing, franchise management, and center data integrity
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
TEST_CENTER = "PB-MGT"
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"

# Expected centers
EXPECTED_CENTERS = ["PB-HSR", "PB-TH", "PB-SN", "PB-DV", "PB-HW", "PB-KN", "PB-KAL", "PB-PERTH", "PB-MGT"]


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for testing"""
    # Send OTP
    res = requests.post(f"{BASE_URL}/api/send_otp", json={
        "center": TEST_CENTER,
        "mobile": TEST_MOBILE
    })
    assert res.status_code == 200, f"Failed to send OTP: {res.text}"
    
    # Verify OTP
    res = requests.post(f"{BASE_URL}/api/verify_otp", json={
        "center": TEST_CENTER,
        "mobile": TEST_MOBILE,
        "otp": TEST_OTP
    })
    assert res.status_code == 200, f"Failed to verify OTP: {res.text}"
    data = res.json()
    assert "token" in data, "No token in response"
    assert data.get("is_super_admin") == True, "User should be super admin"
    return data["token"]


class TestAuthentication:
    """Test authentication flow"""
    
    def test_send_otp(self):
        """Test OTP sending"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
    
    def test_verify_otp_and_get_session(self):
        """Test OTP verification returns proper session data"""
        # Send OTP first
        requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        assert res.status_code == 200
        data = res.json()
        
        # Validate session data
        assert "token" in data
        assert data.get("center") == TEST_CENTER
        assert data.get("is_super_admin") == True
        assert data.get("is_admin") == True


class TestCenters:
    """Test centers endpoint and data integrity"""
    
    def test_get_centers_returns_all_expected(self):
        """Verify all 9 centers are available"""
        res = requests.get(f"{BASE_URL}/api/centers")
        assert res.status_code == 200
        data = res.json()
        
        centers = data.get("centers", [])
        center_codes = [c.get("code") for c in centers]
        
        # Check all expected centers exist
        for expected in EXPECTED_CENTERS:
            assert expected in center_codes, f"Missing center: {expected}"
        
        print(f"Found {len(centers)} centers: {center_codes}")
    
    def test_centers_have_required_fields(self):
        """Verify centers have required fields"""
        res = requests.get(f"{BASE_URL}/api/centers")
        assert res.status_code == 200
        data = res.json()
        
        for center in data.get("centers", []):
            assert "code" in center, f"Center missing 'code': {center}"
            assert "name" in center, f"Center missing 'name': {center}"


class TestDocumentCategories:
    """Test document categories endpoint"""
    
    def test_list_categories_returns_9(self, auth_token):
        """POST /api/documents/categories/list returns 9 categories"""
        res = requests.post(f"{BASE_URL}/api/documents/categories/list", json={
            "token": auth_token
        })
        assert res.status_code == 200
        data = res.json()
        
        assert data.get("success") == True
        categories = data.get("categories", [])
        
        print(f"Found {len(categories)} categories")
        for cat in categories:
            print(f"  - {cat.get('name')} (level: {cat.get('level')})")
        
        # Should have 9 categories
        assert len(categories) == 9, f"Expected 9 categories, got {len(categories)}"
    
    def test_no_test_prefix_categories(self, auth_token):
        """Verify no TEST_ prefixed categories exist"""
        res = requests.post(f"{BASE_URL}/api/documents/categories/list", json={
            "token": auth_token,
            "active_only": False  # Include inactive too
        })
        assert res.status_code == 200
        data = res.json()
        
        categories = data.get("categories", [])
        test_categories = [c for c in categories if c.get("name", "").upper().startswith("TEST")]
        
        assert len(test_categories) == 0, f"Found TEST_ prefixed categories: {[c.get('name') for c in test_categories]}"
    
    def test_categories_have_required_fields(self, auth_token):
        """Verify categories have required fields"""
        res = requests.post(f"{BASE_URL}/api/documents/categories/list", json={
            "token": auth_token
        })
        assert res.status_code == 200
        data = res.json()
        
        for cat in data.get("categories", []):
            assert "category_id" in cat, f"Category missing 'category_id': {cat}"
            assert "name" in cat, f"Category missing 'name': {cat}"
            assert "level" in cat, f"Category missing 'level': {cat}"
            assert cat.get("level") in ["franchise", "employee"], f"Invalid level: {cat.get('level')}"


class TestDocumentList:
    """Test document listing endpoint"""
    
    def test_list_documents_empty_expected(self, auth_token):
        """POST /api/documents/list returns documents (empty is expected)"""
        res = requests.post(f"{BASE_URL}/api/documents/list", json={
            "token": auth_token
        })
        assert res.status_code == 200
        data = res.json()
        
        assert data.get("success") == True
        documents = data.get("documents", [])
        total = data.get("total", 0)
        
        print(f"Found {total} documents (empty is expected after data cleanup)")
        assert isinstance(documents, list)
    
    def test_list_documents_by_center(self, auth_token):
        """Test filtering documents by center"""
        res = requests.post(f"{BASE_URL}/api/documents/list", json={
            "token": auth_token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        data = res.json()
        
        assert data.get("success") == True
        # All returned docs should be for PB-HSR
        for doc in data.get("documents", []):
            assert doc.get("center") == "PB-HSR", f"Document center mismatch: {doc.get('center')}"
    
    def test_list_documents_by_level(self, auth_token):
        """Test filtering documents by level (franchise/employee)"""
        for level in ["franchise", "employee"]:
            res = requests.post(f"{BASE_URL}/api/documents/list", json={
                "token": auth_token,
                "level": level
            })
            assert res.status_code == 200
            data = res.json()
            
            assert data.get("success") == True
            # All returned docs should match the level
            for doc in data.get("documents", []):
                assert doc.get("level") == level, f"Document level mismatch: {doc.get('level')}"


class TestFranchiseManagement:
    """Test franchise management endpoints"""
    
    def test_list_franchises(self, auth_token):
        """POST /api/franchises/list returns franchise list (may be empty)"""
        res = requests.post(f"{BASE_URL}/api/franchises/list", json={
            "token": auth_token
        })
        assert res.status_code == 200
        data = res.json()
        
        franchises = data.get("franchises", [])
        counts = data.get("counts", {})
        
        print(f"Found {len(franchises)} franchises")
        print(f"Counts: active={counts.get('active', 0)}, pending={counts.get('pending', 0)}, terminated={counts.get('terminated', 0)}")
        
        # Empty is expected after data cleanup
        assert isinstance(franchises, list)
    
    def test_franchise_list_with_filters(self, auth_token):
        """Test franchise list with various filters"""
        # Filter by country
        res = requests.post(f"{BASE_URL}/api/franchises/list", json={
            "token": auth_token,
            "country": "India"
        })
        assert res.status_code == 200
        
        # Filter by status
        res = requests.post(f"{BASE_URL}/api/franchises/list", json={
            "token": auth_token,
            "status": "Active"
        })
        assert res.status_code == 200


class TestCenterAccounts:
    """Test center accounts endpoints"""
    
    def test_get_centers_for_accounts(self, auth_token):
        """Test fetching centers for center accounts page"""
        res = requests.post(f"{BASE_URL}/api/mgt/centers", json={
            "token": auth_token
        })
        assert res.status_code == 200
        data = res.json()
        
        centers = data.get("centers", [])
        assert len(centers) > 0, "No centers returned"
        print(f"Found {len(centers)} centers for accounts")
    
    def test_account_summary(self, auth_token):
        """Test account summary endpoint"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": auth_token,
            "center": "PB-HSR",
            "month": "2025-12"
        })
        assert res.status_code == 200
        data = res.json()
        
        if data.get("success"):
            summary = data.get("summary", {})
            assert "sales" in summary
            assert "expenses" in summary
            print(f"Account summary for PB-HSR: sales={summary.get('sales', {}).get('total_sale', 0)}")
    
    def test_list_commissions(self, auth_token):
        """Test commission listing endpoint"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/list-commissions", json={
            "token": auth_token,
            "center": "PB-HSR",
            "month": "2025-12"
        })
        assert res.status_code == 200
        data = res.json()
        
        if data.get("success"):
            statements = data.get("statements", [])
            print(f"Found {len(statements)} commission statements")


class TestMISDashboard:
    """Test MIS Dashboard endpoints"""
    
    def test_mis_dashboard_data(self, auth_token):
        """Test MIS dashboard data endpoint"""
        res = requests.post(f"{BASE_URL}/api/mis/dashboard", json={
            "token": auth_token,
            "month": "2025-12"
        })
        
        # MIS dashboard may return 200 or 404 depending on data
        if res.status_code == 200:
            data = res.json()
            print(f"MIS Dashboard data: {data.get('success', False)}")
        else:
            print(f"MIS Dashboard returned {res.status_code} - may need data")


class TestDocumentFranchiseIntegration:
    """Test the updated document listing with franchise OR center query"""
    
    def test_document_list_franchise_code_filter(self, auth_token):
        """Test /api/documents/list with franchise_code filter (OR query for linked centers)"""
        # First, check if any franchises exist
        franchise_res = requests.post(f"{BASE_URL}/api/franchises/list", json={
            "token": auth_token
        })
        franchises = franchise_res.json().get("franchises", [])
        
        if len(franchises) > 0:
            # Test with an existing franchise
            franchise_code = franchises[0].get("franchise_code")
            res = requests.post(f"{BASE_URL}/api/documents/list", json={
                "token": auth_token,
                "franchise_code": franchise_code
            })
            assert res.status_code == 200
            data = res.json()
            assert data.get("success") == True
            print(f"Documents for franchise {franchise_code}: {data.get('total', 0)}")
        else:
            # No franchises - test with a dummy code (should return empty)
            res = requests.post(f"{BASE_URL}/api/documents/list", json={
                "token": auth_token,
                "franchise_code": "TEST-FRANCHISE"
            })
            assert res.status_code == 200
            data = res.json()
            assert data.get("success") == True
            assert data.get("total", 0) == 0
            print("No franchises exist - document list returns empty as expected")


class TestDataIntegrity:
    """Test data integrity after re-seeding"""
    
    def test_managers_exist(self, auth_token):
        """Verify managers are seeded"""
        res = requests.post(f"{BASE_URL}/api/mgt/managers", json={
            "token": auth_token
        })
        assert res.status_code == 200
        data = res.json()
        
        managers = data.get("managers", [])
        assert len(managers) >= 7, f"Expected at least 7 managers, got {len(managers)}"
        print(f"Found {len(managers)} managers")
    
    def test_expense_heads_exist(self, auth_token):
        """Verify expense heads are seeded"""
        # Expense heads endpoint is GET /api/sales/expense-heads
        res = requests.get(f"{BASE_URL}/api/sales/expense-heads")
        assert res.status_code == 200
        data = res.json()
        
        heads = data.get("expense_heads", [])
        assert len(heads) >= 30, f"Expected at least 30 expense heads, got {len(heads)}"
        print(f"Found {len(heads)} expense heads")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
