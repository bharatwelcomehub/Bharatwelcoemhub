"""
Test Commission Tracking and Document Management Features
- Commission config CRUD
- Commission dashboard
- MIS integration with commissions
- Document categories CRUD
- Document upload/list/approve/reject
- Document stats and expiry tracking
"""

import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_CENTER = "PB-MGT"
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for Super Admin"""
    # Send OTP
    res = requests.post(f"{BASE_URL}/api/send_otp", json={
        "center": TEST_CENTER,
        "mobile": TEST_MOBILE
    })
    assert res.status_code == 200, f"Send OTP failed: {res.text}"
    
    # Verify OTP
    res = requests.post(f"{BASE_URL}/api/verify_otp", json={
        "center": TEST_CENTER,
        "mobile": TEST_MOBILE,
        "otp": TEST_OTP
    })
    assert res.status_code == 200, f"Verify OTP failed: {res.text}"
    data = res.json()
    assert "token" in data, "No token in response"
    return data["token"]


# ============================================
# COMMISSION CONFIG TESTS
# ============================================

class TestCommissionConfig:
    """Test commission configuration endpoints"""
    
    def test_get_default_config(self, auth_token):
        """GET /api/commissions/config/get - returns default template for new center"""
        res = requests.post(f"{BASE_URL}/api/commissions/config/get", json={
            "token": auth_token,
            "center": "PB-KHARADI"
        })
        assert res.status_code == 200, f"Get config failed: {res.text}"
        data = res.json()
        assert data.get("success") is True
        assert "config" in data
        config = data["config"]
        
        # Verify default template structure
        assert "platforms" in config
        assert "payment_modes" in config
        assert len(config["platforms"]) >= 3  # SWIGGY, ZOMATO, MAGICPIN, DIRECT
        assert len(config["payment_modes"]) >= 3  # CARD, UPI, CASH, BANK TRANSFER
        
        # Verify platform structure
        for p in config["platforms"]:
            assert "platform" in p
            assert "commission_pct" in p
            assert "gst_on_commission_pct" in p
            assert "is_active" in p
        
        # Verify payment mode structure
        for pm in config["payment_modes"]:
            assert "payment_mode" in pm
            assert "commission_pct" in pm
            assert "is_active" in pm
        
        print(f"✓ Default config returned with {len(config['platforms'])} platforms, {len(config['payment_modes'])} payment modes")
    
    def test_save_commission_config(self, auth_token):
        """POST /api/commissions/config/save - save config for a center"""
        res = requests.post(f"{BASE_URL}/api/commissions/config/save", json={
            "token": auth_token,
            "center": "PB-KHARADI",
            "platforms": [
                {"platform": "SWIGGY", "commission_pct": 25.0, "gst_on_commission_pct": 18.0, "is_active": True},
                {"platform": "ZOMATO", "commission_pct": 22.0, "gst_on_commission_pct": 18.0, "is_active": True},
                {"platform": "MAGICPIN", "commission_pct": 15.0, "gst_on_commission_pct": 18.0, "is_active": True},
                {"platform": "DIRECT", "commission_pct": 0.0, "gst_on_commission_pct": 0.0, "is_active": True},
            ],
            "payment_modes": [
                {"payment_mode": "CARD", "commission_pct": 2.0, "is_active": True},
                {"payment_mode": "UPI", "commission_pct": 0.0, "is_active": True},
                {"payment_mode": "CASH", "commission_pct": 0.0, "is_active": True},
                {"payment_mode": "BANK TRANSFER", "commission_pct": 0.0, "is_active": True},
            ]
        })
        assert res.status_code == 200, f"Save config failed: {res.text}"
        data = res.json()
        assert data.get("success") is True
        print("✓ Commission config saved successfully")
    
    def test_get_saved_config(self, auth_token):
        """Verify saved config is returned correctly"""
        res = requests.post(f"{BASE_URL}/api/commissions/config/get", json={
            "token": auth_token,
            "center": "PB-KHARADI"
        })
        assert res.status_code == 200
        data = res.json()
        config = data["config"]
        
        # Verify saved values
        swiggy = next((p for p in config["platforms"] if p["platform"] == "SWIGGY"), None)
        assert swiggy is not None
        assert swiggy["commission_pct"] == 25.0
        assert swiggy["gst_on_commission_pct"] == 18.0
        
        card = next((pm for pm in config["payment_modes"] if pm["payment_mode"] == "CARD"), None)
        assert card is not None
        assert card["commission_pct"] == 2.0
        print("✓ Saved config retrieved correctly")
    
    def test_config_requires_auth(self):
        """Config endpoints require valid token"""
        res = requests.post(f"{BASE_URL}/api/commissions/config/get", json={
            "token": "invalid_token",
            "center": "PB-KHARADI"
        })
        assert res.status_code == 401
        print("✓ Config endpoint properly rejects invalid token")
    
    def test_save_config_requires_admin(self, auth_token):
        """Save config requires admin access - Super Admin should work"""
        # This should work since we're using Super Admin token
        res = requests.post(f"{BASE_URL}/api/commissions/config/save", json={
            "token": auth_token,
            "center": "PB-KHARADI",
            "platforms": [
                {"platform": "SWIGGY", "commission_pct": 25.0, "gst_on_commission_pct": 18.0, "is_active": True},
            ],
            "payment_modes": [
                {"payment_mode": "CARD", "commission_pct": 2.0, "is_active": True},
            ]
        })
        assert res.status_code == 200
        print("✓ Admin can save config")


# ============================================
# COMMISSION DASHBOARD TESTS
# ============================================

class TestCommissionDashboard:
    """Test commission dashboard endpoints"""
    
    def test_dashboard_all_centers(self, auth_token):
        """POST /api/commissions/dashboard - get all centers dashboard"""
        res = requests.post(f"{BASE_URL}/api/commissions/dashboard", json={
            "token": auth_token,
            "month": "2025-01"
        })
        assert res.status_code == 200, f"Dashboard failed: {res.text}"
        data = res.json()
        assert data.get("success") is True
        
        # Verify response structure
        assert "period" in data
        assert "centers" in data or "data" in data
        assert "grand_totals" in data or "data" in data
        
        if "grand_totals" in data:
            totals = data["grand_totals"]
            assert "total_sales" in totals
            assert "platform_commission" in totals
            assert "gst_on_commission" in totals
            assert "payment_commission" in totals
            assert "total_commission" in totals
            assert "net_revenue" in totals
        
        print(f"✓ Dashboard returned for all centers")
    
    def test_dashboard_single_center(self, auth_token):
        """POST /api/commissions/dashboard - get single center detail"""
        res = requests.post(f"{BASE_URL}/api/commissions/dashboard", json={
            "token": auth_token,
            "center": "PB-KHARADI",
            "month": "2025-01"
        })
        assert res.status_code == 200, f"Dashboard failed: {res.text}"
        data = res.json()
        assert data.get("success") is True
        assert "data" in data
        
        detail = data["data"]
        assert "center" in detail
        assert "total_sales" in detail
        assert "platform_commission" in detail
        assert "gst_on_commission" in detail
        assert "payment_commission" in detail
        assert "total_commission" in detail
        assert "net_revenue" in detail
        assert "platform_breakdown" in detail
        assert "payment_breakdown" in detail
        
        print(f"✓ Single center dashboard returned with breakdowns")
    
    def test_dashboard_with_date_range(self, auth_token):
        """Dashboard with custom date range"""
        res = requests.post(f"{BASE_URL}/api/commissions/dashboard", json={
            "token": auth_token,
            "start_date": "2025-01-01",
            "end_date": "2025-01-15"
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") is True
        print("✓ Dashboard works with custom date range")
    
    def test_commissions_for_mis(self, auth_token):
        """POST /api/commissions/for-mis - lightweight MIS integration"""
        res = requests.post(f"{BASE_URL}/api/commissions/for-mis", json={
            "token": auth_token,
            "month": "2025-01"
        })
        assert res.status_code == 200, f"MIS endpoint failed: {res.text}"
        data = res.json()
        assert data.get("success") is True
        assert "commissions" in data
        assert "period" in data
        print("✓ Commissions for MIS endpoint works")


# ============================================
# MIS DASHBOARD INTEGRATION TESTS
# ============================================

class TestMISIntegration:
    """Test MIS Dashboard includes commissions"""
    
    def test_mis_overview_includes_commissions(self, auth_token):
        """POST /api/mis/overview - should include total_commissions in summary"""
        res = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": auth_token,
            "period": "current_month"
        })
        assert res.status_code == 200, f"MIS overview failed: {res.text}"
        data = res.json()
        
        assert "summary" in data
        summary = data["summary"]
        assert "total_commissions" in summary, "total_commissions missing from MIS summary"
        assert "profit" in summary
        
        # Profit should be: Sales - Expenses - GST - Commissions
        print(f"✓ MIS overview includes total_commissions: {summary['total_commissions']}")
        print(f"  Profit: {summary['profit']}")
    
    def test_mis_overview_single_center(self, auth_token):
        """MIS overview for single center includes commissions"""
        res = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": auth_token,
            "period": "current_month",
            "center": "PB-KHARADI"
        })
        assert res.status_code == 200
        data = res.json()
        assert "summary" in data
        assert "total_commissions" in data["summary"]
        print("✓ MIS single center includes commissions")
    
    def test_mis_centers_include_commissions(self, auth_token):
        """MIS overview centers array includes commissions per center"""
        res = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": auth_token,
            "period": "current_month"
        })
        assert res.status_code == 200
        data = res.json()
        
        if "centers" in data and len(data["centers"]) > 0:
            center = data["centers"][0]
            assert "commissions" in center, "commissions missing from center data"
            print(f"✓ MIS centers include commissions field")
        else:
            print("⚠ No centers data to verify commissions field")


# ============================================
# DOCUMENT CATEGORY TESTS
# ============================================

class TestDocumentCategories:
    """Test document category management"""
    
    created_category_id = None
    
    def test_create_category(self, auth_token):
        """POST /api/documents/categories/create - create a category"""
        res = requests.post(f"{BASE_URL}/api/documents/categories/create", json={
            "token": auth_token,
            "name": "TEST_Franchise Agreement",
            "level": "franchise",
            "requires_expiry": True,
            "description": "Test category for franchise agreements"
        })
        assert res.status_code == 200, f"Create category failed: {res.text}"
        data = res.json()
        assert data.get("success") is True
        assert "category_id" in data
        TestDocumentCategories.created_category_id = data["category_id"]
        print(f"✓ Category created with ID: {data['category_id']}")
    
    def test_create_employee_category(self, auth_token):
        """Create employee level category"""
        res = requests.post(f"{BASE_URL}/api/documents/categories/create", json={
            "token": auth_token,
            "name": "TEST_ID Proof",
            "level": "employee",
            "requires_expiry": False,
            "description": "Employee ID documents"
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") is True
        print("✓ Employee category created")
    
    def test_list_categories(self, auth_token):
        """POST /api/documents/categories/list - list all categories"""
        res = requests.post(f"{BASE_URL}/api/documents/categories/list", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"List categories failed: {res.text}"
        data = res.json()
        assert data.get("success") is True
        assert "categories" in data
        
        # Find our test category
        test_cats = [c for c in data["categories"] if c["name"].startswith("TEST_")]
        assert len(test_cats) >= 1, "Test categories not found"
        print(f"✓ Listed {len(data['categories'])} categories, {len(test_cats)} test categories")
    
    def test_list_categories_by_level(self, auth_token):
        """List categories filtered by level"""
        res = requests.post(f"{BASE_URL}/api/documents/categories/list", json={
            "token": auth_token,
            "level": "franchise"
        })
        assert res.status_code == 200
        data = res.json()
        for cat in data["categories"]:
            assert cat["level"] == "franchise"
        print("✓ Category filtering by level works")
    
    def test_invalid_level_rejected(self, auth_token):
        """Invalid level should be rejected"""
        res = requests.post(f"{BASE_URL}/api/documents/categories/create", json={
            "token": auth_token,
            "name": "Invalid Category",
            "level": "invalid_level",
            "requires_expiry": False
        })
        assert res.status_code == 400
        print("✓ Invalid level properly rejected")


# ============================================
# DOCUMENT UPLOAD/LIST TESTS
# ============================================

class TestDocumentUpload:
    """Test document upload and listing"""
    
    uploaded_doc_id = None
    
    def test_upload_document(self, auth_token):
        """POST /api/documents/upload - upload a document"""
        # First get a category ID
        res = requests.post(f"{BASE_URL}/api/documents/categories/list", json={
            "token": auth_token,
            "level": "franchise"
        })
        assert res.status_code == 200
        cats = res.json()["categories"]
        assert len(cats) > 0, "No categories available for upload"
        category_id = cats[0]["category_id"]
        
        # Create a test file
        test_content = b"This is a test PDF content for document management testing."
        files = {
            'file': ('test_document.pdf', io.BytesIO(test_content), 'application/pdf')
        }
        data = {
            'token': auth_token,
            'center': 'PB-KHARADI',
            'category_id': category_id,
            'level': 'franchise',
            'expiry_date': '2026-12-31',
            'franchise_code': 'TEST-FC-001',
            'notes': 'Test document upload'
        }
        
        res = requests.post(f"{BASE_URL}/api/documents/upload", data=data, files=files)
        assert res.status_code == 200, f"Upload failed: {res.text}"
        result = res.json()
        assert result.get("success") is True
        assert "document_id" in result
        TestDocumentUpload.uploaded_doc_id = result["document_id"]
        print(f"✓ Document uploaded with ID: {result['document_id']}")
    
    def test_list_documents(self, auth_token):
        """POST /api/documents/list - list documents"""
        res = requests.post(f"{BASE_URL}/api/documents/list", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"List documents failed: {res.text}"
        data = res.json()
        assert data.get("success") is True
        assert "documents" in data
        assert "total" in data
        print(f"✓ Listed {data['total']} documents")
    
    def test_list_documents_with_filters(self, auth_token):
        """List documents with various filters"""
        # Filter by center
        res = requests.post(f"{BASE_URL}/api/documents/list", json={
            "token": auth_token,
            "center": "PB-KHARADI"
        })
        assert res.status_code == 200
        
        # Filter by status
        res = requests.post(f"{BASE_URL}/api/documents/list", json={
            "token": auth_token,
            "status": "pending"
        })
        assert res.status_code == 200
        
        # Filter by level
        res = requests.post(f"{BASE_URL}/api/documents/list", json={
            "token": auth_token,
            "level": "franchise"
        })
        assert res.status_code == 200
        print("✓ Document filtering works")
    
    def test_document_stats(self, auth_token):
        """POST /api/documents/stats - get document statistics"""
        res = requests.post(f"{BASE_URL}/api/documents/stats", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"Stats failed: {res.text}"
        data = res.json()
        assert data.get("success") is True
        assert "stats" in data
        
        stats = data["stats"]
        assert "total" in stats
        assert "pending" in stats
        assert "approved" in stats
        assert "rejected" in stats
        assert "expiring_soon" in stats
        assert "expired" in stats
        print(f"✓ Document stats: total={stats['total']}, pending={stats['pending']}, approved={stats['approved']}")
    
    def test_expiring_documents(self, auth_token):
        """POST /api/documents/expiring - get expiring documents"""
        res = requests.post(f"{BASE_URL}/api/documents/expiring", json={
            "token": auth_token,
            "days": 60
        })
        assert res.status_code == 200, f"Expiring docs failed: {res.text}"
        data = res.json()
        assert data.get("success") is True
        assert "expiring_soon" in data
        assert "already_expired" in data
        assert "total_alerts" in data
        print(f"✓ Expiring documents: {data['total_alerts']} alerts")


# ============================================
# DOCUMENT APPROVAL TESTS
# ============================================

class TestDocumentApproval:
    """Test document approval/rejection workflow"""
    
    def test_approve_document(self, auth_token):
        """POST /api/documents/action - approve a document"""
        # First upload a document to approve
        res = requests.post(f"{BASE_URL}/api/documents/categories/list", json={
            "token": auth_token,
            "level": "franchise"
        })
        cats = res.json()["categories"]
        category_id = cats[0]["category_id"] if cats else None
        
        if not category_id:
            pytest.skip("No category available")
        
        # Upload
        test_content = b"Test document for approval"
        files = {'file': ('approve_test.pdf', io.BytesIO(test_content), 'application/pdf')}
        data = {
            'token': auth_token,
            'center': 'PB-KHARADI',
            'category_id': category_id,
            'level': 'franchise',
            'notes': 'Document for approval test'
        }
        res = requests.post(f"{BASE_URL}/api/documents/upload", data=data, files=files)
        assert res.status_code == 200
        doc_id = res.json()["document_id"]
        
        # Approve
        res = requests.post(f"{BASE_URL}/api/documents/action", json={
            "token": auth_token,
            "document_id": doc_id,
            "action": "approve",
            "notes": "Approved for testing"
        })
        assert res.status_code == 200, f"Approve failed: {res.text}"
        data = res.json()
        assert data.get("success") is True
        print(f"✓ Document {doc_id} approved")
        
        # Verify status changed
        res = requests.post(f"{BASE_URL}/api/documents/list", json={
            "token": auth_token,
            "status": "approved"
        })
        docs = res.json()["documents"]
        approved_doc = next((d for d in docs if d["document_id"] == doc_id), None)
        assert approved_doc is not None
        assert approved_doc["status"] == "approved"
        print("✓ Document status verified as approved")
    
    def test_reject_document(self, auth_token):
        """POST /api/documents/action - reject a document"""
        # Upload a document to reject
        res = requests.post(f"{BASE_URL}/api/documents/categories/list", json={
            "token": auth_token,
            "level": "franchise"
        })
        cats = res.json()["categories"]
        category_id = cats[0]["category_id"]
        
        # Upload
        test_content = b"Test document for rejection"
        files = {'file': ('reject_test.pdf', io.BytesIO(test_content), 'application/pdf')}
        data = {
            'token': auth_token,
            'center': 'PB-KHARADI',
            'category_id': category_id,
            'level': 'franchise',
            'notes': 'Document for rejection test'
        }
        res = requests.post(f"{BASE_URL}/api/documents/upload", data=data, files=files)
        assert res.status_code == 200
        doc_id = res.json()["document_id"]
        
        # Reject
        res = requests.post(f"{BASE_URL}/api/documents/action", json={
            "token": auth_token,
            "document_id": doc_id,
            "action": "reject",
            "notes": "Document quality is poor"
        })
        assert res.status_code == 200, f"Reject failed: {res.text}"
        data = res.json()
        assert data.get("success") is True
        print(f"✓ Document {doc_id} rejected")
    
    def test_invalid_action_rejected(self, auth_token):
        """Invalid action should be rejected"""
        res = requests.post(f"{BASE_URL}/api/documents/action", json={
            "token": auth_token,
            "document_id": "some-id",
            "action": "invalid_action"
        })
        assert res.status_code in [400, 404]
        print("✓ Invalid action properly rejected")


# ============================================
# DOCUMENT DOWNLOAD TESTS
# ============================================

class TestDocumentDownload:
    """Test document download functionality"""
    
    def test_download_document(self, auth_token):
        """GET /api/documents/file/{document_id} - download a document"""
        # First upload a document
        res = requests.post(f"{BASE_URL}/api/documents/categories/list", json={
            "token": auth_token,
            "level": "franchise"
        })
        cats = res.json()["categories"]
        if not cats:
            pytest.skip("No categories available")
        category_id = cats[0]["category_id"]
        
        # Upload
        test_content = b"Test document content for download verification"
        files = {'file': ('download_test.pdf', io.BytesIO(test_content), 'application/pdf')}
        data = {
            'token': auth_token,
            'center': 'PB-KHARADI',
            'category_id': category_id,
            'level': 'franchise'
        }
        res = requests.post(f"{BASE_URL}/api/documents/upload", data=data, files=files)
        assert res.status_code == 200
        doc_id = res.json()["document_id"]
        
        # Download using query param auth
        res = requests.get(f"{BASE_URL}/api/documents/file/{doc_id}?auth={auth_token}")
        assert res.status_code == 200, f"Download failed: {res.text}"
        assert len(res.content) > 0
        print(f"✓ Document downloaded successfully ({len(res.content)} bytes)")
    
    def test_download_requires_auth(self):
        """Download requires authentication"""
        res = requests.get(f"{BASE_URL}/api/documents/file/some-id")
        assert res.status_code == 401
        print("✓ Download properly requires authentication")
    
    def test_download_nonexistent_document(self, auth_token):
        """Download nonexistent document returns 404"""
        res = requests.get(f"{BASE_URL}/api/documents/file/nonexistent-id?auth={auth_token}")
        assert res.status_code == 404
        print("✓ Nonexistent document returns 404")


# ============================================
# CLEANUP
# ============================================

class TestCleanup:
    """Clean up test data"""
    
    def test_delete_test_documents(self, auth_token):
        """Delete test documents"""
        # List all documents
        res = requests.post(f"{BASE_URL}/api/documents/list", json={
            "token": auth_token
        })
        if res.status_code == 200:
            docs = res.json().get("documents", [])
            # Delete documents with test notes
            for doc in docs:
                if "test" in (doc.get("notes", "") or "").lower() or "TEST" in (doc.get("franchise_code", "") or ""):
                    requests.post(f"{BASE_URL}/api/documents/delete", json={
                        "token": auth_token,
                        "document_id": doc["document_id"]
                    })
        print("✓ Test documents cleaned up")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
