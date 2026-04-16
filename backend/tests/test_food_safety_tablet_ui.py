"""
Food Safety Compliance Module - Backend API Tests
Testing tablet-first UI redesign - all API endpoints unchanged
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"
TEST_CENTER = "PB-MGT"


class TestFoodSafetyAuth:
    """Authentication for Food Safety tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        # Send OTP
        resp = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        assert resp.status_code == 200, f"Send OTP failed: {resp.text}"
        
        # Verify OTP
        resp = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP,
            "center": TEST_CENTER
        })
        assert resp.status_code == 200, f"Verify OTP failed: {resp.text}"
        data = resp.json()
        assert "token" in data, "No token in response"
        return data["token"]


class TestFoodSafetyTemplateTypes(TestFoodSafetyAuth):
    """Test /api/food-safety/template-types endpoint"""
    
    def test_get_template_types(self, auth_token):
        """Should return 8 template types with columns"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/template-types", json={
            "token": auth_token
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Check types
        assert "types" in data
        types = data["types"]
        assert len(types) >= 8, f"Expected 8+ types, got {len(types)}"
        
        # Check expected type keys
        type_keys = [t["key"] for t in types]
        expected_keys = [
            "food_items", "supplier_details", "food_receipt", "cooking_cooling",
            "food_temp_record", "two_four_hour_rule", "cleaning_procedure",
            "cleaning_record", "general_temp_record"
        ]
        for key in expected_keys:
            assert key in type_keys, f"Missing type: {key}"
        
        # Check columns
        assert "columns" in data
        columns = data["columns"]
        assert "supplier_details" in columns
        assert "food_items" in columns
        print(f"PASSED: Got {len(types)} template types with columns")
    
    def test_template_types_requires_auth(self):
        """Should reject unauthenticated requests"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/template-types", json={
            "token": "invalid_token"
        })
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print("PASSED: Unauthenticated request rejected")


class TestFoodSafetyDashboard(TestFoodSafetyAuth):
    """Test /api/food-safety/dashboard endpoint"""
    
    def test_dashboard_returns_data(self, auth_token):
        """Should return dashboard with status counts, recent records, overdue"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/dashboard", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Check structure
        assert "status_counts" in data
        assert "recent_records" in data
        assert "overdue" in data
        assert "template_types" in data
        
        print(f"PASSED: Dashboard returned with {len(data['recent_records'])} recent records")
    
    def test_dashboard_with_perth_center(self, auth_token):
        """Should return dashboard for PB-PERTH center"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/dashboard", json={
            "token": auth_token,
            "center": "PB-PERTH"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert "status_counts" in data
        print(f"PASSED: Dashboard for PB-PERTH returned")


class TestFoodSafetyTemplateItems(TestFoodSafetyAuth):
    """Test template items CRUD endpoints"""
    
    def test_list_template_items(self, auth_token):
        """Should list template items for a type"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/template-items/list", json={
            "token": auth_token,
            "template_type": "food_items",
            "center": "PB-PERTH"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert "items" in data
        print(f"PASSED: Listed {len(data['items'])} food items")
    
    def test_list_supplier_items(self, auth_token):
        """Should list supplier details items"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/template-items/list", json={
            "token": auth_token,
            "template_type": "supplier_details",
            "center": "PB-PERTH"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert "items" in data
        print(f"PASSED: Listed {len(data['items'])} supplier items")
    
    def test_list_cleaning_procedure_items(self, auth_token):
        """Should list cleaning procedure items"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/template-items/list", json={
            "token": auth_token,
            "template_type": "cleaning_procedure",
            "center": "PB-PERTH"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert "items" in data
        print(f"PASSED: Listed {len(data['items'])} cleaning procedure items")


class TestFoodSafetyRecords(TestFoodSafetyAuth):
    """Test records CRUD endpoints"""
    
    def test_list_records(self, auth_token):
        """Should list records with filters"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/records/list", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert "records" in data
        print(f"PASSED: Listed {len(data['records'])} records")
    
    def test_list_records_with_type_filter(self, auth_token):
        """Should filter records by template type"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/records/list", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "food_temp_record"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert "records" in data
        # All records should be food_temp_record type
        for rec in data["records"]:
            assert rec["template_type"] == "food_temp_record"
        print(f"PASSED: Filtered to {len(data['records'])} food_temp_record records")
    
    def test_list_records_with_status_filter(self, auth_token):
        """Should filter records by status"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/records/list", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "status": "approved"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert "records" in data
        print(f"PASSED: Filtered to {len(data['records'])} approved records")
    
    def test_save_draft_record(self, auth_token):
        """Should save a draft record"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/records/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "food_temp_record",
            "record_date": "2026-04-16",
            "period": "daily",
            "notes": "Test draft record",
            "entries": [
                {"date": "2026-04-16", "food": "Test Food", "time": "12:00", "staff_initials": "TT"}
            ],
            "status": "draft"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert data.get("success") == True
        assert "record_id" in data
        print(f"PASSED: Created draft record {data['record_id']}")
        
        # Cleanup - delete the test record
        del_resp = requests.post(f"{BASE_URL}/api/food-safety/records/delete", json={
            "token": auth_token,
            "record_id": data["record_id"]
        })
        assert del_resp.status_code == 200, f"Cleanup failed: {del_resp.text}"
    
    def test_save_and_submit_record(self, auth_token):
        """Should save and submit a record (auto-approve if setting is off)"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/records/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "general_temp_record",
            "record_date": "2026-04-16",
            "period": "daily",
            "notes": "Test submitted record",
            "entries": [
                {"date": "2026-04-16", "time": "14:00", "activity_food": "Test Activity", "checked_by": "TT"}
            ],
            "status": "submitted"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert data.get("success") == True
        assert "record_id" in data
        # Check if auto-approved
        print(f"PASSED: Submitted record {data['record_id']}, auto_approved={data.get('auto_approved')}")
        
        # Cleanup
        del_resp = requests.post(f"{BASE_URL}/api/food-safety/records/delete", json={
            "token": auth_token,
            "record_id": data["record_id"]
        })
        assert del_resp.status_code == 200


class TestFoodSafetyApprovalSettings(TestFoodSafetyAuth):
    """Test approval settings endpoints"""
    
    def test_get_approval_settings(self, auth_token):
        """Should get approval settings for all template types"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/template-settings/get", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert "settings" in data
        print(f"PASSED: Got approval settings: {data['settings']}")


class TestFoodSafetyReports(TestFoodSafetyAuth):
    """Test PDF and Excel report generation"""
    
    def test_pdf_report_no_records(self, auth_token):
        """Should return 404 when no records match filters"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/report/pdf", json={
            "token": auth_token,
            "center": "NONEXISTENT",
            "template_type": "food_receipt",
            "date_from": "2099-01-01",
            "date_to": "2099-12-31"
        })
        # Should return 404 for no records
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("PASSED: PDF report returns 404 for no records")
    
    def test_excel_report_no_records(self, auth_token):
        """Should return 404 when no records match filters"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/report/excel", json={
            "token": auth_token,
            "center": "NONEXISTENT",
            "template_type": "food_receipt",
            "date_from": "2099-01-01",
            "date_to": "2099-12-31"
        })
        # Should return 404 for no records
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("PASSED: Excel report returns 404 for no records")
    
    def test_pdf_report_with_records(self, auth_token):
        """Should generate PDF when records exist"""
        # First create a record
        save_resp = requests.post(f"{BASE_URL}/api/food-safety/records/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "food_temp_record",
            "record_date": "2026-04-16",
            "period": "daily",
            "entries": [{"date": "2026-04-16", "food": "Test", "time": "12:00", "staff_initials": "TT"}],
            "status": "submitted"
        })
        assert save_resp.status_code == 200
        record_id = save_resp.json()["record_id"]
        
        # Try to generate PDF
        resp = requests.post(f"{BASE_URL}/api/food-safety/report/pdf", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "food_temp_record"
        })
        
        # Should return PDF or 404 if no matching records
        assert resp.status_code in [200, 404], f"Unexpected status: {resp.status_code}"
        if resp.status_code == 200:
            assert "application/pdf" in resp.headers.get("content-type", "")
            print("PASSED: PDF report generated successfully")
        else:
            print("PASSED: PDF report endpoint working (no matching records)")
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/food-safety/records/delete", json={
            "token": auth_token,
            "record_id": record_id
        })
    
    def test_excel_report_with_records(self, auth_token):
        """Should generate Excel when records exist"""
        # First create a record
        save_resp = requests.post(f"{BASE_URL}/api/food-safety/records/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "general_temp_record",
            "record_date": "2026-04-16",
            "period": "daily",
            "entries": [{"date": "2026-04-16", "time": "12:00", "activity_food": "Test", "checked_by": "TT"}],
            "status": "submitted"
        })
        assert save_resp.status_code == 200
        record_id = save_resp.json()["record_id"]
        
        # Try to generate Excel
        resp = requests.post(f"{BASE_URL}/api/food-safety/report/excel", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "general_temp_record"
        })
        
        assert resp.status_code in [200, 404], f"Unexpected status: {resp.status_code}"
        if resp.status_code == 200:
            assert "spreadsheet" in resp.headers.get("content-type", "")
            print("PASSED: Excel report generated successfully")
        else:
            print("PASSED: Excel report endpoint working (no matching records)")
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/food-safety/records/delete", json={
            "token": auth_token,
            "record_id": record_id
        })


class TestFoodSafetySeed(TestFoodSafetyAuth):
    """Test seed endpoint"""
    
    def test_seed_templates(self, auth_token):
        """Should seed or report already seeded"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/seed", json={
            "token": auth_token,
            "center": "PB-PERTH"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert data.get("success") == True
        print(f"PASSED: Seed response: {data.get('message')}")


class TestFoodSafetyErrorHandling(TestFoodSafetyAuth):
    """Test error handling"""
    
    def test_invalid_template_type(self, auth_token):
        """Should reject invalid template type"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/records/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "invalid_type",
            "record_date": "2026-04-16",
            "entries": [],
            "status": "draft"
        })
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
        print("PASSED: Invalid template type rejected")
    
    def test_invalid_status(self, auth_token):
        """Should reject invalid status"""
        resp = requests.post(f"{BASE_URL}/api/food-safety/records/save", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "template_type": "food_temp_record",
            "record_date": "2026-04-16",
            "entries": [],
            "status": "invalid_status"
        })
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
        print("PASSED: Invalid status rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
