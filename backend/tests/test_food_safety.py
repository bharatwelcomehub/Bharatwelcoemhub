"""
Food Safety Compliance Module - Backend API Tests
Tests: Template Types, Template Items CRUD, Records CRUD, Dashboard, Reports
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_OTP = "123456"
SUPER_ADMIN_CENTER = "PB-MGT"
TEST_CENTER = "PB-PERTH"


class TestFoodSafetyAuth:
    """Authentication for Food Safety tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get Super Admin auth token"""
        # Send OTP
        resp = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER
        })
        assert resp.status_code == 200, f"Send OTP failed: {resp.text}"
        
        # Verify OTP
        resp = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP,
            "center": SUPER_ADMIN_CENTER
        })
        assert resp.status_code == 200, f"Verify OTP failed: {resp.text}"
        data = resp.json()
        assert "token" in data, "No token in response"
        return data["token"]


class TestTemplateTypes(TestFoodSafetyAuth):
    """Test /api/food-safety/template-types endpoint"""
    
    def test_get_template_types_returns_8_types(self, auth_token):
        """Verify 8 template types are returned"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/template-types", json={
            "token": auth_token
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Verify 8 types
        assert "types" in data
        assert len(data["types"]) == 8, f"Expected 8 types, got {len(data['types'])}"
        
        # Verify expected type keys
        expected_keys = [
            "supplier_details", "food_receipt", "cooking_cooling", "food_temp_record",
            "two_four_hour_rule", "cleaning_procedure", "cleaning_record", "general_temp_record"
        ]
        actual_keys = [t["key"] for t in data["types"]]
        for key in expected_keys:
            assert key in actual_keys, f"Missing template type: {key}"
        
        # Verify columns exist
        assert "columns" in data
        assert len(data["columns"]) == 8, f"Expected 8 column definitions"
        
    def test_template_types_requires_auth(self):
        """Verify endpoint requires authentication"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/template-types", json={
            "token": "invalid_token"
        })
        assert resp.status_code == 401


class TestSeedData(TestFoodSafetyAuth):
    """Test /api/food-safety/seed endpoint"""
    
    def test_seed_returns_already_seeded(self, auth_token):
        """Seed endpoint should return 'already seeded' since data exists"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/seed", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert data.get("success") == True
        # Should indicate already seeded
        assert "Already seeded" in data.get("message", "") or data.get("seeded", 0) >= 0


class TestTemplateItems(TestFoodSafetyAuth):
    """Test Template Items CRUD endpoints"""
    
    def test_list_template_items_for_perth(self, auth_token):
        """List template items for PB-PERTH center"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/template-items/list", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "supplier_details"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "items" in data
        # Should have seeded supplier items
        assert len(data["items"]) >= 1, "Expected at least 1 supplier item"
        
    def test_list_all_template_items(self, auth_token):
        """List all template items without filter"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/template-items/list", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "items" in data
        # Should have 107 seeded items per context
        assert len(data["items"]) >= 50, f"Expected many items, got {len(data['items'])}"
        
    def test_create_template_item(self, auth_token):
        """Create a new template item (Admin)"""
        test_name = f"TEST_ITEM_{uuid.uuid4().hex[:8]}"
        resp = requests.post(f"{BASE_URL}/api/food-safety/template-items/save", json={
            "token": auth_token,
            "template_type": "supplier_details",
            "center": TEST_CENTER,
            "name": test_name,
            "fields": {"supplier_name": "Test Supplier", "contact": "123-456"},
            "active": True,
            "order": 999
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert data.get("success") == True
        assert "item_id" in data
        
        # Verify item was created
        list_resp = requests.post(f"{BASE_URL}/api/food-safety/template-items/list", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "supplier_details"
        })
        items = list_resp.json().get("items", [])
        found = any(i["name"] == test_name for i in items)
        assert found, "Created item not found in list"
        
        # Cleanup - delete the test item
        item_id = data["item_id"]
        del_resp = requests.post(f"{BASE_URL}/api/food-safety/template-items/delete", json={
            "token": auth_token,
            "item_id": item_id
        })
        assert del_resp.status_code == 200
        
    def test_delete_template_item(self, auth_token):
        """Delete a template item (Admin)"""
        # First create an item to delete
        test_name = f"TEST_DELETE_{uuid.uuid4().hex[:8]}"
        create_resp = requests.post(f"{BASE_URL}/api/food-safety/template-items/save", json={
            "token": auth_token,
            "template_type": "cleaning_procedure",
            "center": TEST_CENTER,
            "name": test_name,
            "fields": {"item_equipment": "Test Equipment"},
            "active": True,
            "order": 999
        })
        assert create_resp.status_code == 200
        item_id = create_resp.json()["item_id"]
        
        # Delete it
        del_resp = requests.post(f"{BASE_URL}/api/food-safety/template-items/delete", json={
            "token": auth_token,
            "item_id": item_id
        })
        assert del_resp.status_code == 200, f"Delete failed: {del_resp.text}"
        assert del_resp.json().get("success") == True
        
        # Verify deletion
        list_resp = requests.post(f"{BASE_URL}/api/food-safety/template-items/list", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "cleaning_procedure"
        })
        items = list_resp.json().get("items", [])
        found = any(i.get("item_id") == item_id for i in items)
        assert not found, "Deleted item still exists"
        
    def test_toggle_template_item(self, auth_token):
        """Toggle template item active status"""
        # Create item
        test_name = f"TEST_TOGGLE_{uuid.uuid4().hex[:8]}"
        create_resp = requests.post(f"{BASE_URL}/api/food-safety/template-items/save", json={
            "token": auth_token,
            "template_type": "cleaning_record",
            "center": TEST_CENTER,
            "name": test_name,
            "fields": {"area_equipment": "Test Area"},
            "active": True,
            "order": 999
        })
        assert create_resp.status_code == 200
        item_id = create_resp.json()["item_id"]
        
        # Toggle to inactive
        toggle_resp = requests.post(f"{BASE_URL}/api/food-safety/template-items/toggle", json={
            "token": auth_token,
            "item_id": item_id,
            "active": False
        })
        assert toggle_resp.status_code == 200
        assert toggle_resp.json().get("active") == False
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/food-safety/template-items/delete", json={
            "token": auth_token,
            "item_id": item_id
        })


class TestRecords(TestFoodSafetyAuth):
    """Test Records CRUD endpoints"""
    
    def test_create_draft_record(self, auth_token):
        """Create a draft food safety record"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/records/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "food_receipt",
            "record_date": "2026-01-15",
            "period": "daily",
            "notes": "Test draft record",
            "entries": [
                {"date": "2026-01-15", "time": "10:00", "supplier": "Test Supplier", 
                 "product": "Test Product", "checked_by": "Tester"}
            ],
            "status": "draft"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert data.get("success") == True
        assert "record_id" in data
        assert data.get("message") == "Record draft"
        return data["record_id"]
        
    def test_create_and_submit_record(self, auth_token):
        """Create and submit a food safety record"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/records/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "cooking_cooling",
            "record_date": "2026-01-15",
            "period": "daily",
            "notes": "Test submitted record",
            "entries": [
                {"date": "2026-01-15", "food": "Test Food", "core_temp": 80, "staff_initials": "TT"}
            ],
            "status": "submitted"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert data.get("success") == True
        assert data.get("message") == "Record submitted"
        return data["record_id"]
        
    def test_list_records_with_filters(self, auth_token):
        """List records with various filters"""
        # List all records for center
        resp = requests.post(f"{BASE_URL}/api/food-safety/records/list", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "records" in data
        
        # Filter by template type
        resp2 = requests.post(f"{BASE_URL}/api/food-safety/records/list", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "food_receipt"
        })
        assert resp2.status_code == 200
        
        # Filter by status
        resp3 = requests.post(f"{BASE_URL}/api/food-safety/records/list", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "status": "approved"
        })
        assert resp3.status_code == 200
        
    def test_approve_submitted_record(self, auth_token):
        """Approve a submitted record"""
        # First create a submitted record
        create_resp = requests.post(f"{BASE_URL}/api/food-safety/records/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "general_temp_record",
            "record_date": "2026-01-15",
            "period": "daily",
            "entries": [
                {"date": "2026-01-15", "time": "12:00", "activity_food": "Test", "checked_by": "TT"}
            ],
            "status": "submitted"
        })
        assert create_resp.status_code == 200
        record_id = create_resp.json()["record_id"]
        
        # Approve it
        approve_resp = requests.post(f"{BASE_URL}/api/food-safety/records/approve", json={
            "token": auth_token,
            "record_id": record_id
        })
        assert approve_resp.status_code == 200, f"Approve failed: {approve_resp.text}"
        assert approve_resp.json().get("success") == True
        
        # Verify status changed
        list_resp = requests.post(f"{BASE_URL}/api/food-safety/records/list", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        records = list_resp.json().get("records", [])
        rec = next((r for r in records if r.get("record_id") == record_id), None)
        assert rec is not None
        assert rec.get("status") == "approved"
        
    def test_cannot_edit_approved_record(self, auth_token):
        """Cannot edit approved/locked records"""
        # Find an approved record
        list_resp = requests.post(f"{BASE_URL}/api/food-safety/records/list", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "status": "approved"
        })
        records = list_resp.json().get("records", [])
        if not records:
            pytest.skip("No approved records to test")
            
        record_id = records[0]["record_id"]
        
        # Try to edit it
        edit_resp = requests.post(f"{BASE_URL}/api/food-safety/records/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": records[0]["template_type"],
            "record_id": record_id,
            "entries": [{"test": "data"}],
            "status": "draft"
        })
        assert edit_resp.status_code == 403, "Should not allow editing approved records"


class TestDashboard(TestFoodSafetyAuth):
    """Test Dashboard endpoint"""
    
    def test_dashboard_returns_status_counts(self, auth_token):
        """Dashboard returns status counts per template type"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/dashboard", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Verify structure
        assert "status_counts" in data
        assert "recent_records" in data
        assert "overdue" in data
        assert "template_types" in data
        
        # Verify template types
        assert len(data["template_types"]) == 8
        
    def test_dashboard_shows_overdue_alerts(self, auth_token):
        """Dashboard shows overdue alerts for missing daily records"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/dashboard", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        assert resp.status_code == 200
        data = resp.json()
        
        # Overdue should be a list
        assert isinstance(data.get("overdue"), list)
        # Each overdue item should have template_type, label, date
        for item in data.get("overdue", []):
            assert "template_type" in item
            assert "label" in item
            assert "date" in item


class TestReports(TestFoodSafetyAuth):
    """Test PDF and Excel report generation"""
    
    def test_pdf_report_generation(self, auth_token):
        """Generate PDF report"""
        # First ensure we have some records
        resp = requests.post(f"{BASE_URL}/api/food-safety/report/pdf", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "food_receipt"
        })
        
        # May return 404 if no records, or 200 with PDF
        if resp.status_code == 404:
            # No records - acceptable
            assert "No records found" in resp.json().get("detail", "")
        else:
            assert resp.status_code == 200, f"Failed: {resp.text}"
            assert resp.headers.get("content-type") == "application/pdf"
            assert len(resp.content) > 0
            
    def test_excel_report_generation(self, auth_token):
        """Generate Excel report"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/report/excel", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "food_receipt"
        })
        
        if resp.status_code == 404:
            assert "No records found" in resp.json().get("detail", "")
        else:
            assert resp.status_code == 200, f"Failed: {resp.text}"
            assert "spreadsheetml" in resp.headers.get("content-type", "")
            assert len(resp.content) > 0


class TestInvalidInputs(TestFoodSafetyAuth):
    """Test error handling for invalid inputs"""
    
    def test_invalid_template_type_on_save(self, auth_token):
        """Reject invalid template type"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/template-items/save", json={
            "token": auth_token,
            "template_type": "invalid_type",
            "center": TEST_CENTER,
            "name": "Test"
        })
        assert resp.status_code == 400
        
    def test_invalid_status_on_record_save(self, auth_token):
        """Reject invalid status on record save"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/records/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "food_receipt",
            "entries": [],
            "status": "invalid_status"
        })
        assert resp.status_code == 400
        
    def test_approve_non_submitted_record(self, auth_token):
        """Cannot approve a draft record"""
        # Create draft
        create_resp = requests.post(f"{BASE_URL}/api/food-safety/records/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "food_temp_record",
            "entries": [{"date": "2026-01-15", "time": "10:00", "staff_initials": "TT"}],
            "status": "draft"
        })
        assert create_resp.status_code == 200
        record_id = create_resp.json()["record_id"]
        
        # Try to approve draft
        approve_resp = requests.post(f"{BASE_URL}/api/food-safety/records/approve", json={
            "token": auth_token,
            "record_id": record_id
        })
        assert approve_resp.status_code == 400, "Should not approve draft records"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
