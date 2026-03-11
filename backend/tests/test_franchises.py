"""
Franchise Management Module Tests
Tests for CRUD operations, documents, agreement generation, and access control
"""

import pytest
import requests
import os
import tempfile
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials - Super Admin
TEST_CENTER = "PB-MGT"
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"

# Test franchise data
TEST_FRANCHISE_CODE = f"TEST-FR-{datetime.now().strftime('%H%M%S')}"
TEST_FRANCHISE_DATA = {
    "franchise_code": TEST_FRANCHISE_CODE,
    "franchise_name": "Test Franchise Perth",
    "legal_entity_name": "Test Legal Entity Pty Ltd",
    "country": "Australia",
    "state": "Western Australia",
    "city": "Perth",
    "address": "123 Test Street",
    "pincode": "6000",
    "primary_contact_name": "John Test",
    "primary_contact_email": "john@test.com",
    "primary_contact_phone": "+61400000000",
    "directors": [
        {"name": "Director One", "email": "d1@test.com", "phone": "+61400000001", "designation": "Managing Director"},
        {"name": "Director Two", "email": "d2@test.com", "phone": "+61400000002", "designation": "Director"}
    ],
    "agreement_start_date": "2025-01-01",
    "agreement_end_date": "2028-12-31",
    "franchise_fee": 50000,
    "royalty_percentage": 5.5,
    "status": "Pending",
    "notes": "Test franchise for automated testing"
}


class TestFranchiseAuth:
    """Test authentication and access control for franchise endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for Super Admin"""
        # Send OTP
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        assert otp_res.status_code == 200, f"Failed to send OTP: {otp_res.text}"
        
        # Verify OTP
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        assert verify_res.status_code == 200, f"Failed to verify OTP: {verify_res.text}"
        
        data = verify_res.json()
        assert "token" in data, "Token not in response"
        return data["token"]
    
    def test_auth_token_exists(self, auth_token):
        """Verify we have a valid auth token"""
        assert auth_token is not None
        assert len(auth_token) > 10
        print(f"✓ Auth token obtained: {auth_token[:20]}...")
    
    def test_unauthorized_access_rejected(self):
        """Verify franchise list rejects invalid token"""
        res = requests.post(f"{BASE_URL}/api/franchises/list", json={
            "token": "invalid_token_12345"
        })
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"
        print("✓ Unauthorized access correctly rejected")


class TestFranchiseList:
    """Test franchise listing and filtering"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_res.json().get("token")
    
    def test_list_franchises_returns_data(self, auth_token):
        """Test GET franchise list returns franchises array"""
        res = requests.post(f"{BASE_URL}/api/franchises/list", json={
            "token": auth_token
        })
        assert res.status_code == 200
        data = res.json()
        
        assert "franchises" in data, "Missing 'franchises' key"
        assert "total" in data, "Missing 'total' key"
        assert "counts" in data, "Missing 'counts' key"
        assert isinstance(data["franchises"], list)
        
        print(f"✓ Franchise list returned {len(data['franchises'])} franchises")
        print(f"  Counts: Active={data['counts']['active']}, Pending={data['counts']['pending']}")
    
    def test_list_franchises_has_counts(self, auth_token):
        """Verify list returns status counts"""
        res = requests.post(f"{BASE_URL}/api/franchises/list", json={"token": auth_token})
        data = res.json()
        
        counts = data.get("counts", {})
        assert "active" in counts, "Missing active count"
        assert "pending" in counts, "Missing pending count"
        assert "terminated" in counts, "Missing terminated count"
        assert "inactive" in counts, "Missing inactive count"
        print(f"✓ Status counts present: {counts}")
    
    def test_list_franchises_filter_by_country(self, auth_token):
        """Test filtering by country"""
        res = requests.post(f"{BASE_URL}/api/franchises/list", json={
            "token": auth_token,
            "country": "Australia"
        })
        assert res.status_code == 200
        data = res.json()
        
        # All results should be from Australia
        for f in data.get("franchises", []):
            assert f.get("country") == "Australia", f"Expected Australia, got {f.get('country')}"
        
        print(f"✓ Country filter working - {len(data['franchises'])} Australian franchises")
    
    def test_list_franchises_search(self, auth_token):
        """Test search functionality"""
        res = requests.post(f"{BASE_URL}/api/franchises/list", json={
            "token": auth_token,
            "search": "PERTH"
        })
        assert res.status_code == 200
        data = res.json()
        print(f"✓ Search working - found {len(data['franchises'])} results for 'PERTH'")


class TestFranchiseCRUD:
    """Test Create, Read, Update, Delete operations"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_res.json().get("token")
    
    def test_create_franchise(self, auth_token):
        """Test creating a new franchise"""
        payload = {**TEST_FRANCHISE_DATA, "token": auth_token}
        
        res = requests.post(f"{BASE_URL}/api/franchises/create", json=payload)
        assert res.status_code == 200, f"Create failed: {res.text}"
        
        data = res.json()
        assert data.get("success") == True
        assert TEST_FRANCHISE_CODE in data.get("message", "")
        
        print(f"✓ Franchise created: {TEST_FRANCHISE_CODE}")
    
    def test_get_franchise_details(self, auth_token):
        """Test getting franchise details"""
        res = requests.post(f"{BASE_URL}/api/franchises/get/{TEST_FRANCHISE_CODE}", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"Get failed: {res.text}"
        
        data = res.json()
        assert "franchise" in data
        assert "audit_history" in data
        
        franchise = data["franchise"]
        assert franchise["franchise_code"] == TEST_FRANCHISE_CODE
        assert franchise["franchise_name"] == TEST_FRANCHISE_DATA["franchise_name"]
        assert franchise["country"] == "Australia"
        assert franchise["city"] == "Perth"
        assert len(franchise.get("directors", [])) == 2
        
        print(f"✓ Franchise details retrieved: {franchise['franchise_name']}")
        print(f"  Location: {franchise['city']}, {franchise['country']}")
        print(f"  Directors: {len(franchise.get('directors', []))}")
    
    def test_franchise_has_audit_history(self, auth_token):
        """Verify franchise details include audit history"""
        res = requests.post(f"{BASE_URL}/api/franchises/get/{TEST_FRANCHISE_CODE}", json={
            "token": auth_token
        })
        data = res.json()
        
        audit = data.get("audit_history", [])
        assert len(audit) > 0, "No audit history found"
        
        # Should have CREATE entry
        create_entry = next((a for a in audit if a.get("action") == "CREATE"), None)
        assert create_entry is not None, "CREATE audit entry not found"
        assert "timestamp" in create_entry
        assert "performed_by" in create_entry
        
        print(f"✓ Audit history present: {len(audit)} entries")
        print(f"  Latest: {audit[0]['action']} by {audit[0]['performed_by']}")
    
    def test_update_franchise(self, auth_token):
        """Test updating franchise fields"""
        update_data = {
            "token": auth_token,
            "city": "Sydney",
            "state": "New South Wales",
            "status": "Active",
            "franchise_fee": 60000
        }
        
        res = requests.post(f"{BASE_URL}/api/franchises/update/{TEST_FRANCHISE_CODE}", json=update_data)
        assert res.status_code == 200, f"Update failed: {res.text}"
        
        data = res.json()
        assert data.get("success") == True
        
        # Verify update was persisted
        get_res = requests.post(f"{BASE_URL}/api/franchises/get/{TEST_FRANCHISE_CODE}", json={
            "token": auth_token
        })
        franchise = get_res.json().get("franchise", {})
        
        assert franchise["city"] == "Sydney", f"City not updated: {franchise.get('city')}"
        assert franchise["status"] == "Active", f"Status not updated: {franchise.get('status')}"
        assert franchise["franchise_fee"] == 60000
        
        print(f"✓ Franchise updated successfully")
        print(f"  New city: {franchise['city']}")
        print(f"  New status: {franchise['status']}")
        print(f"  New fee: {franchise['franchise_fee']}")
    
    def test_update_creates_audit_entry(self, auth_token):
        """Verify update creates audit log"""
        # Get audit history
        res = requests.post(f"{BASE_URL}/api/franchises/get/{TEST_FRANCHISE_CODE}", json={
            "token": auth_token
        })
        audit = res.json().get("audit_history", [])
        
        # Should have UPDATE entry
        update_entry = next((a for a in audit if a.get("action") == "UPDATE"), None)
        assert update_entry is not None, "UPDATE audit entry not found"
        assert "details" in update_entry
        
        print(f"✓ Update audit entry found")
        print(f"  Changes: {list(update_entry.get('details', {}).keys())}")
    
    def test_duplicate_franchise_code_rejected(self, auth_token):
        """Test that duplicate franchise code is rejected"""
        payload = {
            "token": auth_token,
            "franchise_code": TEST_FRANCHISE_CODE,  # Already exists
            "franchise_name": "Duplicate Test"
        }
        
        res = requests.post(f"{BASE_URL}/api/franchises/create", json=payload)
        assert res.status_code == 400, f"Expected 400, got {res.status_code}"
        print("✓ Duplicate franchise code correctly rejected")
    
    def test_get_nonexistent_franchise(self, auth_token):
        """Test getting non-existent franchise returns 404"""
        res = requests.post(f"{BASE_URL}/api/franchises/get/NONEXISTENT-FR", json={
            "token": auth_token
        })
        assert res.status_code == 404
        print("✓ Non-existent franchise correctly returns 404")


class TestFranchiseDocuments:
    """Test document upload, download, and delete"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_res.json().get("token")
    
    def test_document_upload(self, auth_token):
        """Test uploading a document"""
        # Create a temporary PDF-like file for testing
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4 Test Document Content')
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as file:
                files = {'file': ('test_agreement.pdf', file, 'application/pdf')}
                data = {
                    'token': auth_token,
                    'franchise_code': TEST_FRANCHISE_CODE,
                    'document_type': 'Agreement',
                    'document_name': 'Test Franchise Agreement 2025',
                    'notes': 'Uploaded via automated testing'
                }
                
                res = requests.post(f"{BASE_URL}/api/franchises/documents/upload", 
                                   files=files, data=data)
            
            assert res.status_code == 200, f"Upload failed: {res.text}"
            response_data = res.json()
            assert response_data.get("success") == True
            assert "document" in response_data
            
            doc = response_data["document"]
            assert doc.get("document_name") == "Test Franchise Agreement 2025"
            assert doc.get("document_type") == "Agreement"
            assert "document_id" in doc
            
            print(f"✓ Document uploaded: {doc['document_name']}")
            print(f"  Document ID: {doc['document_id']}")
            print(f"  Type: {doc['document_type']}")
            
            # Store document_id for later tests
            TestFranchiseDocuments.uploaded_doc_id = doc["document_id"]
            
        finally:
            os.unlink(temp_path)
    
    def test_franchise_has_documents(self, auth_token):
        """Verify franchise now has documents"""
        res = requests.post(f"{BASE_URL}/api/franchises/get/{TEST_FRANCHISE_CODE}", json={
            "token": auth_token
        })
        franchise = res.json().get("franchise", {})
        documents = franchise.get("documents", [])
        
        assert len(documents) > 0, "No documents found after upload"
        
        doc = documents[-1]  # Latest document
        assert "document_id" in doc
        assert "document_name" in doc
        assert "uploaded_at" in doc
        
        print(f"✓ Franchise has {len(documents)} document(s)")
    
    def test_document_download(self, auth_token):
        """Test downloading a document"""
        doc_id = getattr(TestFranchiseDocuments, 'uploaded_doc_id', None)
        if not doc_id:
            pytest.skip("No document ID from previous test")
        
        # Document download uses GET with query param
        res = requests.get(
            f"{BASE_URL}/api/franchises/documents/download/{TEST_FRANCHISE_CODE}/{doc_id}",
            params={"token": auth_token}
        )
        
        assert res.status_code == 200, f"Download failed: {res.status_code}"
        assert len(res.content) > 0, "Empty file content"
        
        print(f"✓ Document downloaded successfully ({len(res.content)} bytes)")
    
    def test_document_delete(self, auth_token):
        """Test deleting a document"""
        doc_id = getattr(TestFranchiseDocuments, 'uploaded_doc_id', None)
        if not doc_id:
            pytest.skip("No document ID from previous test")
        
        res = requests.post(
            f"{BASE_URL}/api/franchises/documents/delete/{TEST_FRANCHISE_CODE}/{doc_id}",
            json={"token": auth_token}
        )
        
        assert res.status_code == 200, f"Delete failed: {res.text}"
        data = res.json()
        assert data.get("success") == True
        
        # Verify document is removed
        get_res = requests.post(f"{BASE_URL}/api/franchises/get/{TEST_FRANCHISE_CODE}", json={
            "token": auth_token
        })
        franchise = get_res.json().get("franchise", {})
        documents = franchise.get("documents", [])
        
        doc_ids = [d.get("document_id") for d in documents]
        assert doc_id not in doc_ids, "Document still exists after delete"
        
        print(f"✓ Document deleted successfully")


class TestFranchiseAgreement:
    """Test agreement PDF generation"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_res.json().get("token")
    
    def test_generate_agreement_pdf(self, auth_token):
        """Test generating franchise agreement PDF"""
        res = requests.post(
            f"{BASE_URL}/api/franchises/generate-agreement/{TEST_FRANCHISE_CODE}",
            json={"token": auth_token}
        )
        
        assert res.status_code == 200, f"Agreement generation failed: {res.text}"
        assert res.headers.get("content-type") == "application/pdf"
        
        # Verify PDF content starts with PDF header
        content = res.content
        assert content[:4] == b'%PDF', f"Invalid PDF: starts with {content[:10]}"
        assert len(content) > 1000, "PDF seems too small"
        
        # Check Content-Disposition header
        content_disp = res.headers.get("content-disposition", "")
        assert "attachment" in content_disp
        assert "Franchise_Agreement" in content_disp
        assert TEST_FRANCHISE_CODE in content_disp
        
        print(f"✓ Agreement PDF generated ({len(content)} bytes)")
        print(f"  Content-Disposition: {content_disp}")
    
    def test_generate_agreement_for_existing_franchise(self, auth_token):
        """Test agreement generation for existing FR-PERTH franchise"""
        res = requests.post(
            f"{BASE_URL}/api/franchises/generate-agreement/FR-PERTH",
            json={"token": auth_token}
        )
        
        # Should work or return 404 if franchise doesn't exist
        if res.status_code == 200:
            assert res.headers.get("content-type") == "application/pdf"
            print(f"✓ Agreement for FR-PERTH generated ({len(res.content)} bytes)")
        elif res.status_code == 404:
            print("⚠ FR-PERTH franchise not found (expected if using fresh DB)")
        else:
            pytest.fail(f"Unexpected status: {res.status_code}")


class TestFranchiseStats:
    """Test franchise statistics endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_res.json().get("token")
    
    def test_franchise_stats(self, auth_token):
        """Test getting franchise statistics"""
        res = requests.post(f"{BASE_URL}/api/franchises/stats", json={
            "token": auth_token
        })
        
        assert res.status_code == 200
        data = res.json()
        
        assert "total" in data
        assert "by_country" in data
        assert "by_status" in data
        
        print(f"✓ Franchise stats retrieved")
        print(f"  Total: {data['total']}")
        print(f"  By country: {data['by_country']}")
        print(f"  By status: {data['by_status']}")
    
    def test_countries_list(self):
        """Test getting available countries list"""
        res = requests.get(f"{BASE_URL}/api/franchises/countries")
        
        assert res.status_code == 200
        data = res.json()
        
        assert "countries" in data
        assert isinstance(data["countries"], list)
        assert "India" in data["countries"]
        assert "Australia" in data["countries"]
        
        print(f"✓ Countries list: {data['countries']}")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_res.json().get("token")
    
    def test_delete_test_franchise(self, auth_token):
        """Cleanup: Delete the test franchise"""
        res = requests.post(
            f"{BASE_URL}/api/franchises/delete/{TEST_FRANCHISE_CODE}",
            json={"token": auth_token}
        )
        
        # Super Admin should be able to delete
        if res.status_code == 200:
            print(f"✓ Test franchise {TEST_FRANCHISE_CODE} deleted")
        elif res.status_code == 404:
            print(f"⚠ Test franchise already deleted or not found")
        else:
            print(f"⚠ Delete returned {res.status_code}: {res.text}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
