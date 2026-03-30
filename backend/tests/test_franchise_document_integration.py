"""
Test Franchise Document Integration
Tests document management integration within franchise detail page
"""
import pytest
import requests
import os
import tempfile

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://franchise-payroll-1.preview.emergentagent.com')

# Test credentials
TEST_CENTER = "PB-MGT"
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"
TEST_FRANCHISE = "FR-TEST-INDIA"


class TestFranchiseDocumentIntegration:
    """Test document management integration in franchise detail page"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        # Send OTP
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        assert res.status_code == 200
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        assert res.status_code == 200
        self.token = res.json()["token"]
        self.session = res.json()
    
    def test_document_categories_list_franchise_level(self):
        """Test: Document categories list returns franchise-level categories"""
        res = requests.post(f"{BASE_URL}/api/documents/categories/list", json={
            "token": self.token,
            "level": "franchise"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "categories" in data
        
        # Verify franchise-level categories exist
        categories = data["categories"]
        assert len(categories) > 0
        
        # Check for seeded categories
        category_names = [c["name"] for c in categories]
        assert any("Agreement" in name for name in category_names), "Franchise Agreement category should exist"
        assert any("License" in name for name in category_names), "License category should exist"
        
        # All should be franchise level
        for cat in categories:
            assert cat["level"] == "franchise"
        
        print(f"✓ Found {len(categories)} franchise-level categories")
    
    def test_franchise_detail_exists(self):
        """Test: Franchise FR-TEST-INDIA exists and can be retrieved"""
        res = requests.post(f"{BASE_URL}/api/franchises/get/{TEST_FRANCHISE}", json={
            "token": self.token
        })
        assert res.status_code == 200
        data = res.json()
        assert "franchise" in data
        assert data["franchise"]["franchise_code"] == TEST_FRANCHISE
        assert data["franchise"]["status"] == "Active"
        print(f"✓ Franchise {TEST_FRANCHISE} exists and is Active")
    
    def test_document_upload_for_franchise(self):
        """Test: Upload document for a franchise"""
        # Create a test PDF file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF")
            temp_path = f.name
        
        try:
            # Get a category ID
            cat_res = requests.post(f"{BASE_URL}/api/documents/categories/list", json={
                "token": self.token,
                "level": "franchise"
            })
            categories = cat_res.json()["categories"]
            category_id = categories[0]["category_id"]
            
            # Upload document
            with open(temp_path, "rb") as f:
                res = requests.post(f"{BASE_URL}/api/documents/upload", data={
                    "token": self.token,
                    "center": TEST_CENTER,
                    "category_id": category_id,
                    "level": "franchise",
                    "franchise_code": TEST_FRANCHISE,
                    "notes": "TEST_Integration Test Document",
                    "expiry_date": "2027-12-31"
                }, files={"file": ("test_doc.pdf", f, "application/pdf")})
            
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert "document_id" in data
            
            self.uploaded_doc_id = data["document_id"]
            print(f"✓ Document uploaded: {self.uploaded_doc_id}")
            
            # Verify document appears in franchise document list
            list_res = requests.post(f"{BASE_URL}/api/documents/list", json={
                "token": self.token,
                "franchise_code": TEST_FRANCHISE,
                "level": "franchise"
            })
            assert list_res.status_code == 200
            docs = list_res.json()["documents"]
            doc_ids = [d["document_id"] for d in docs]
            assert self.uploaded_doc_id in doc_ids, "Uploaded document should appear in franchise document list"
            print(f"✓ Document appears in franchise document list")
            
            # Clean up - delete the test document
            del_res = requests.post(f"{BASE_URL}/api/documents/delete", json={
                "token": self.token,
                "document_id": self.uploaded_doc_id
            })
            assert del_res.status_code == 200
            print(f"✓ Test document cleaned up")
            
        finally:
            os.unlink(temp_path)
    
    def test_document_download_with_auth(self):
        """Test: Download document with auth token"""
        # First upload a document
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4\nTest content for download\n%%EOF")
            temp_path = f.name
        
        try:
            cat_res = requests.post(f"{BASE_URL}/api/documents/categories/list", json={
                "token": self.token,
                "level": "franchise"
            })
            category_id = cat_res.json()["categories"][0]["category_id"]
            
            with open(temp_path, "rb") as f:
                upload_res = requests.post(f"{BASE_URL}/api/documents/upload", data={
                    "token": self.token,
                    "center": TEST_CENTER,
                    "category_id": category_id,
                    "level": "franchise",
                    "franchise_code": TEST_FRANCHISE,
                    "notes": "TEST_Download Test"
                }, files={"file": ("download_test.pdf", f, "application/pdf")})
            
            doc_id = upload_res.json()["document_id"]
            
            # Test download with auth query param
            download_res = requests.get(f"{BASE_URL}/api/documents/file/{doc_id}?auth={self.token}")
            assert download_res.status_code == 200
            assert len(download_res.content) > 0
            print(f"✓ Document downloaded successfully ({len(download_res.content)} bytes)")
            
            # Test download without auth - should fail
            no_auth_res = requests.get(f"{BASE_URL}/api/documents/file/{doc_id}")
            assert no_auth_res.status_code == 401
            print(f"✓ Download without auth correctly rejected")
            
            # Clean up
            requests.post(f"{BASE_URL}/api/documents/delete", json={
                "token": self.token,
                "document_id": doc_id
            })
            
        finally:
            os.unlink(temp_path)
    
    def test_document_delete_from_franchise(self):
        """Test: Delete document from franchise"""
        # Upload a document
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4\nDelete test\n%%EOF")
            temp_path = f.name
        
        try:
            cat_res = requests.post(f"{BASE_URL}/api/documents/categories/list", json={
                "token": self.token,
                "level": "franchise"
            })
            category_id = cat_res.json()["categories"][0]["category_id"]
            
            with open(temp_path, "rb") as f:
                upload_res = requests.post(f"{BASE_URL}/api/documents/upload", data={
                    "token": self.token,
                    "center": TEST_CENTER,
                    "category_id": category_id,
                    "level": "franchise",
                    "franchise_code": TEST_FRANCHISE,
                    "notes": "TEST_Delete Test"
                }, files={"file": ("delete_test.pdf", f, "application/pdf")})
            
            doc_id = upload_res.json()["document_id"]
            
            # Verify document exists
            list_res = requests.post(f"{BASE_URL}/api/documents/list", json={
                "token": self.token,
                "franchise_code": TEST_FRANCHISE
            })
            doc_ids = [d["document_id"] for d in list_res.json()["documents"]]
            assert doc_id in doc_ids
            
            # Delete document
            del_res = requests.post(f"{BASE_URL}/api/documents/delete", json={
                "token": self.token,
                "document_id": doc_id
            })
            assert del_res.status_code == 200
            assert del_res.json()["success"] is True
            print(f"✓ Document deleted successfully")
            
            # Verify document no longer appears
            list_res2 = requests.post(f"{BASE_URL}/api/documents/list", json={
                "token": self.token,
                "franchise_code": TEST_FRANCHISE
            })
            doc_ids2 = [d["document_id"] for d in list_res2.json()["documents"]]
            assert doc_id not in doc_ids2
            print(f"✓ Deleted document no longer in list")
            
        finally:
            os.unlink(temp_path)


class TestRegressionCommissionTracking:
    """Regression tests for Commission Tracking"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        res = requests.post(f"{BASE_URL}/api/send_otp", json={"center": TEST_CENTER, "mobile": TEST_MOBILE})
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={"center": TEST_CENTER, "mobile": TEST_MOBILE, "otp": TEST_OTP})
        self.token = res.json()["token"]
    
    def test_commission_config_get(self):
        """Regression: Commission config endpoint works"""
        res = requests.post(f"{BASE_URL}/api/commissions/config/get", json={
            "token": self.token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        data = res.json()
        assert "config" in data
        assert "platforms" in data["config"]
        assert "payment_modes" in data["config"]
        print(f"✓ Commission config endpoint working")
    
    def test_commission_dashboard(self):
        """Regression: Commission dashboard endpoint works"""
        res = requests.post(f"{BASE_URL}/api/commissions/dashboard", json={
            "token": self.token,
            "month": "2026-03"
        })
        assert res.status_code == 200
        data = res.json()
        assert "grand_totals" in data or "centers" in data or "data" in data
        print(f"✓ Commission dashboard endpoint working")


class TestRegressionDocumentManagement:
    """Regression tests for standalone Document Management"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        res = requests.post(f"{BASE_URL}/api/send_otp", json={"center": TEST_CENTER, "mobile": TEST_MOBILE})
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={"center": TEST_CENTER, "mobile": TEST_MOBILE, "otp": TEST_OTP})
        self.token = res.json()["token"]
    
    def test_document_stats(self):
        """Regression: Document stats endpoint works"""
        res = requests.post(f"{BASE_URL}/api/documents/stats", json={
            "token": self.token
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "stats" in data
        stats = data["stats"]
        assert "total" in stats
        assert "pending" in stats
        assert "approved" in stats
        print(f"✓ Document stats: total={stats['total']}, pending={stats['pending']}")
    
    def test_document_expiring(self):
        """Regression: Document expiring endpoint works"""
        res = requests.post(f"{BASE_URL}/api/documents/expiring", json={
            "token": self.token,
            "days": 60
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "expiring_soon" in data
        assert "already_expired" in data
        print(f"✓ Expiry alerts: {data.get('total_alerts', 0)} alerts")
    
    def test_document_categories_all(self):
        """Regression: Document categories list all levels"""
        res = requests.post(f"{BASE_URL}/api/documents/categories/list", json={
            "token": self.token
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "categories" in data
        print(f"✓ Found {len(data['categories'])} total categories")


class TestRegressionMISDashboard:
    """Regression tests for MIS Dashboard with Commissions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        res = requests.post(f"{BASE_URL}/api/send_otp", json={"center": TEST_CENTER, "mobile": TEST_MOBILE})
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={"center": TEST_CENTER, "mobile": TEST_MOBILE, "otp": TEST_OTP})
        self.token = res.json()["token"]
    
    def test_mis_overview_includes_commissions(self):
        """Regression: MIS overview includes commissions in profit calculation"""
        res = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": self.token,
            "month": "2026-03"
        })
        assert res.status_code == 200
        data = res.json()
        assert "summary" in data
        # Commissions should be in summary
        summary = data["summary"]
        assert "total_commissions" in summary or "commissions" in str(data).lower()
        print(f"✓ MIS overview includes commissions data")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
