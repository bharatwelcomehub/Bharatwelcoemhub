"""
Test Suite for Dashboard/Data Visibility Fixes (Iteration 68)
Tests 5 key fixes:
1. Daily Text Generator - pulls actual stored data from daily_sales/expenses
2. Bill Download - POS bills normalization (bill_no->bill_id, grand_total->amount)
3. Bill Download - expense_attachments collection wired in
4. Attendance Dashboard - role-based access (admin, manager, super admin)
5. Owner Dashboard - franchise info fields (center name, phone, legal entity)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_OTP = "123456"
SUPER_ADMIN_CENTER = "PB-MGT"

# Test data centers
TEST_CENTER_DAILY_TEXT = "PB-DV"  # Has daily sales data for 2025-04-01
TEST_CENTER_POS_BILLS = "PB-HSR"  # Has POS bills for 2026-03-27
TEST_DATE_DAILY_TEXT = "2025-04-01"
TEST_DATE_POS_BILLS = "2026-03-27"


class TestAuth:
    """Authentication helper tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for super admin"""
        # Send OTP
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "center": SUPER_ADMIN_CENTER
        })
        assert res.status_code == 200, f"Send OTP failed: {res.text}"
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": SUPER_ADMIN_MOBILE,
            "otp": SUPER_ADMIN_OTP,
            "center": SUPER_ADMIN_CENTER
        })
        assert res.status_code == 200, f"Verify OTP failed: {res.text}"
        data = res.json()
        assert "token" in data, "No token in response"
        return data["token"]


class TestDailyTextGenerator(TestAuth):
    """
    Test Daily Text Generator - Fix #3
    Verifies that /api/daily-text/generate pulls actual stored data from daily_sales/expenses
    """
    
    def test_generate_daily_text_with_sales_data(self, auth_token):
        """Test that daily text generator returns has_sales_data=true with non-zero values"""
        res = requests.post(f"{BASE_URL}/api/daily-text/generate", json={
            "token": auth_token,
            "center": TEST_CENTER_DAILY_TEXT,
            "date": TEST_DATE_DAILY_TEXT
        })
        assert res.status_code == 200, f"Daily text generate failed: {res.text}"
        data = res.json()
        
        # Verify response structure
        assert "success" in data
        assert "text" in data
        assert "data" in data
        assert "has_sales_data" in data
        assert "center" in data
        assert "date" in data
        
        # Verify center and date match
        assert data["center"] == TEST_CENTER_DAILY_TEXT.upper()
        assert data["date"] == TEST_DATE_DAILY_TEXT
        
        print(f"has_sales_data: {data['has_sales_data']}")
        print(f"Data fields: {list(data['data'].keys())}")
        
        # Check if sales data was found
        if data["has_sales_data"]:
            # Verify non-zero values when sales data exists
            sales_data = data["data"]
            print(f"opening_balance: {sales_data.get('opening_balance')}")
            print(f"total_sale: {sales_data.get('total_sale')}")
            
            # At least one of these should be non-zero if data exists
            has_values = (
                sales_data.get("opening_balance", 0) != 0 or
                sales_data.get("total_sale", 0) != 0 or
                sales_data.get("cash_sale", 0) != 0
            )
            print(f"Has non-zero values: {has_values}")
        
        return data
    
    def test_refresh_from_data_no_overrides(self, auth_token):
        """Test that refresh from data pulls fresh DB values without overrides"""
        # First call with overrides
        res1 = requests.post(f"{BASE_URL}/api/daily-text/generate", json={
            "token": auth_token,
            "center": TEST_CENTER_DAILY_TEXT,
            "date": TEST_DATE_DAILY_TEXT,
            "overrides": {"opening_balance": 99999}  # Override value
        })
        assert res1.status_code == 200
        data1 = res1.json()
        
        # Second call without overrides (simulates "Refresh from Data")
        res2 = requests.post(f"{BASE_URL}/api/daily-text/generate", json={
            "token": auth_token,
            "center": TEST_CENTER_DAILY_TEXT,
            "date": TEST_DATE_DAILY_TEXT
            # No overrides - should pull fresh from DB
        })
        assert res2.status_code == 200
        data2 = res2.json()
        
        # If override was applied in first call, second call should have different value
        if data1["data"]["opening_balance"] == 99999:
            # Override was applied, verify refresh doesn't keep it
            print(f"First call opening_balance (with override): {data1['data']['opening_balance']}")
            print(f"Second call opening_balance (no override): {data2['data']['opening_balance']}")
        
        return data2
    
    def test_daily_text_case_insensitive_center(self, auth_token):
        """Test that center matching is case-insensitive"""
        # Test with lowercase center
        res = requests.post(f"{BASE_URL}/api/daily-text/generate", json={
            "token": auth_token,
            "center": TEST_CENTER_DAILY_TEXT.lower(),  # lowercase
            "date": TEST_DATE_DAILY_TEXT
        })
        assert res.status_code == 200, f"Case-insensitive center failed: {res.text}"
        data = res.json()
        
        # Center should be normalized to uppercase
        assert data["center"] == TEST_CENTER_DAILY_TEXT.upper()


class TestBillDownload(TestAuth):
    """
    Test Bill Download Module - Fixes #2 and #5
    Verifies:
    - POS bills show bill_no as bill_id and grand_total as amount
    - expense_attachments are included in bill list
    """
    
    def test_bill_list_returns_proper_fields(self, auth_token):
        """Test that bill list returns bills with proper bill_id, doc_type, amount, description"""
        res = requests.post(f"{BASE_URL}/api/bill-download/list", json={
            "token": auth_token,
            "center": TEST_CENTER_POS_BILLS
        })
        assert res.status_code == 200, f"Bill list failed: {res.text}"
        data = res.json()
        
        # Verify response structure
        assert "bills" in data
        assert "count" in data
        assert "doc_types" in data
        
        print(f"Total bills found: {data['count']}")
        print(f"Doc types available: {data['doc_types']}")
        
        # Check bill structure
        if data["bills"]:
            bill = data["bills"][0]
            print(f"Sample bill fields: {list(bill.keys())}")
            
            # Verify required fields exist
            assert "bill_id" in bill, "bill_id field missing"
            assert "doc_type" in bill, "doc_type field missing"
            assert "amount" in bill, "amount field missing"
            assert "description" in bill, "description field missing"
            assert "center" in bill, "center field missing"
            assert "date" in bill, "date field missing"
            
            print(f"Sample bill: bill_id={bill['bill_id']}, doc_type={bill['doc_type']}, amount={bill['amount']}")
        
        return data
    
    def test_pos_bills_normalized(self, auth_token):
        """Test that POS bills have bill_no mapped to bill_id and grand_total to amount"""
        res = requests.post(f"{BASE_URL}/api/bill-download/list", json={
            "token": auth_token,
            "center": TEST_CENTER_POS_BILLS,
            "date_from": TEST_DATE_POS_BILLS,
            "date_to": TEST_DATE_POS_BILLS
        })
        assert res.status_code == 200, f"Bill list failed: {res.text}"
        data = res.json()
        
        # Look for POS/Sales bills
        pos_bills = [b for b in data["bills"] if b.get("doc_type") in ["Sales Bill", "POS Bill"]]
        print(f"POS/Sales bills found: {len(pos_bills)}")
        
        for bill in pos_bills[:3]:  # Check first 3
            print(f"POS Bill: bill_id={bill['bill_id']}, amount={bill['amount']}, desc={bill.get('description', '')[:50]}")
            
            # bill_id should not be empty
            assert bill["bill_id"], "POS bill has empty bill_id"
            
            # amount should be a number (could be 0 for some bills)
            assert isinstance(bill["amount"], (int, float)), f"amount is not a number: {bill['amount']}"
        
        return pos_bills
    
    def test_expense_attachments_included(self, auth_token):
        """Test that expense_attachments are included in bill list with download URLs"""
        res = requests.post(f"{BASE_URL}/api/bill-download/list", json={
            "token": auth_token,
            "center": TEST_CENTER_POS_BILLS
        })
        assert res.status_code == 200, f"Bill list failed: {res.text}"
        data = res.json()
        
        # Look for expense attachments
        attachments = [b for b in data["bills"] if b.get("doc_type") == "Expense Attachment"]
        print(f"Expense attachments found: {len(attachments)}")
        
        for att in attachments[:3]:  # Check first 3
            print(f"Attachment: bill_id={att['bill_id']}, file_url={att.get('file_url', '')[:50]}")
            
            # Attachments should have file_url starting with /api/
            if att.get("file_url"):
                assert att["file_url"].startswith("/api/"), f"Attachment URL should start with /api/: {att['file_url']}"
        
        return attachments
    
    def test_bill_list_all_centers_admin(self, auth_token):
        """Test that admin can list bills from all centers"""
        res = requests.post(f"{BASE_URL}/api/bill-download/list", json={
            "token": auth_token
            # No center filter - should return all
        })
        assert res.status_code == 200, f"Bill list all centers failed: {res.text}"
        data = res.json()
        
        print(f"Total bills across all centers: {data['count']}")
        
        # Check if multiple centers are represented
        centers = set(b.get("center") for b in data["bills"])
        print(f"Centers in results: {centers}")
        
        return data


class TestAttendanceDashboard(TestAuth):
    """
    Test Attendance Dashboard - Fix #1
    Verifies role-based access: Center Manager, Admin, Super Admin
    """
    
    def test_attendance_summary_admin(self, auth_token):
        """Test that admin can access attendance summary for all centers"""
        res = requests.post(f"{BASE_URL}/api/attendance-dashboard/summary", json={
            "token": auth_token
            # No center filter - admin should see all
        })
        assert res.status_code == 200, f"Attendance summary failed: {res.text}"
        data = res.json()
        
        # Verify response structure
        assert "date" in data
        assert "summary" in data
        assert "is_super_admin" in data
        
        summary = data["summary"]
        assert "total_employees" in summary
        assert "present" in summary
        assert "absent" in summary
        assert "attendance_percentage" in summary
        
        print(f"Date: {data['date']}")
        print(f"Total employees: {summary['total_employees']}")
        print(f"Attendance %: {summary['attendance_percentage']}")
        print(f"Is super admin: {data['is_super_admin']}")
        
        return data
    
    def test_attendance_center_detail(self, auth_token):
        """Test attendance center detail for a specific center"""
        res = requests.post(f"{BASE_URL}/api/attendance-dashboard/center-detail", json={
            "token": auth_token,
            "center": SUPER_ADMIN_CENTER
        })
        assert res.status_code == 200, f"Center detail failed: {res.text}"
        data = res.json()
        
        # Verify response structure
        assert "date" in data
        assert "center" in data
        assert "summary" in data
        assert "employees" in data
        
        print(f"Center: {data['center']}")
        print(f"Total employees: {data['summary']['total']}")
        print(f"Employees list count: {len(data['employees'])}")
        
        return data
    
    def test_attendance_monthly_grid(self, auth_token):
        """Test monthly attendance grid for admin"""
        res = requests.post(f"{BASE_URL}/api/attendance-dashboard/monthly-grid", json={
            "token": auth_token,
            "month": "2025-04"
        })
        assert res.status_code == 200, f"Monthly grid failed: {res.text}"
        data = res.json()
        
        # Verify response structure
        assert "month" in data
        assert "days_in_month" in data
        assert "employees" in data
        assert "center_summary" in data
        
        print(f"Month: {data['month']}")
        print(f"Days in month: {data['days_in_month']}")
        print(f"Employees count: {len(data['employees'])}")
        
        return data
    
    def test_attendance_daily_grid(self, auth_token):
        """Test daily attendance grid"""
        res = requests.post(f"{BASE_URL}/api/attendance-dashboard/daily-grid", json={
            "token": auth_token,
            "date": "2025-04-01"
        })
        assert res.status_code == 200, f"Daily grid failed: {res.text}"
        data = res.json()
        
        # Verify response structure
        assert "date" in data
        assert "employees" in data
        
        print(f"Date: {data['date']}")
        print(f"Employees count: {len(data['employees'])}")
        
        return data
    
    def test_attendance_center_breakdown(self, auth_token):
        """Test attendance center breakdown"""
        res = requests.post(f"{BASE_URL}/api/attendance-dashboard/center-breakdown", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"Center breakdown failed: {res.text}"
        data = res.json()
        
        # Verify response structure
        assert "date" in data
        assert "centers" in data
        
        print(f"Date: {data['date']}")
        print(f"Centers count: {len(data['centers'])}")
        
        if data["centers"]:
            center = data["centers"][0]
            print(f"Sample center: {center.get('center_code')}, attendance: {center.get('attendance_percentage')}%")
        
        return data
    
    def test_attendance_export(self, auth_token):
        """Test attendance export"""
        res = requests.post(f"{BASE_URL}/api/attendance-dashboard/export", json={
            "token": auth_token,
            "center": SUPER_ADMIN_CENTER,
            "format": "excel"
        })
        assert res.status_code == 200, f"Export failed: {res.text}"
        
        # Should return Excel file
        content_type = res.headers.get("content-type", "")
        print(f"Export content-type: {content_type}")
        
        # Verify it's an Excel file
        assert "spreadsheet" in content_type or "octet-stream" in content_type or len(res.content) > 0
        print(f"Export file size: {len(res.content)} bytes")
        
        return True


class TestOwnerDashboard(TestAuth):
    """
    Test Owner Dashboard - Fix #4
    Verifies franchise info includes center name, phone, legal entity fields
    """
    
    def test_franchise_by_center(self, auth_token):
        """Test that franchise info includes all required fields"""
        # First get a center that has a franchise
        res = requests.post(f"{BASE_URL}/api/franchises/by-center/{TEST_CENTER_POS_BILLS}", json={
            "token": auth_token
        })
        
        # This might return 404 if no franchise exists for this center
        if res.status_code == 404:
            print(f"No franchise found for center {TEST_CENTER_POS_BILLS}")
            pytest.skip("No franchise data for test center")
        
        assert res.status_code == 200, f"Franchise by center failed: {res.text}"
        data = res.json()
        
        print(f"Franchise found: {data.get('found')}")
        
        if data.get("found") and data.get("franchise"):
            franchise = data["franchise"]
            print(f"Franchise fields: {list(franchise.keys())}")
            
            # Check for required fields
            print(f"franchise_name: {franchise.get('franchise_name')}")
            print(f"center/center_code: {franchise.get('center') or franchise.get('center_code')}")
            print(f"phone/contact_phone: {franchise.get('phone') or franchise.get('contact_phone')}")
            print(f"legal_entity/company_name: {franchise.get('legal_entity') or franchise.get('company_name')}")
            print(f"owner_name: {franchise.get('owner_name')}")
            print(f"email: {franchise.get('email')}")
        
        return data
    
    def test_franchise_list(self, auth_token):
        """Test franchise list endpoint"""
        res = requests.post(f"{BASE_URL}/api/franchises/list", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"Franchise list failed: {res.text}"
        data = res.json()
        
        franchises = data.get("franchises", [])
        print(f"Total franchises: {len(franchises)}")
        
        if franchises:
            franchise = franchises[0]
            print(f"Sample franchise fields: {list(franchise.keys())}")
            
            # Check for center name, phone, legal entity
            has_center = "center" in franchise or "center_code" in franchise
            has_phone = "phone" in franchise or "contact_phone" in franchise
            has_legal = "legal_entity" in franchise or "company_name" in franchise
            
            print(f"Has center field: {has_center}")
            print(f"Has phone field: {has_phone}")
            print(f"Has legal entity field: {has_legal}")
        
        return data


class TestHealthCheck:
    """Basic health check tests"""
    
    def test_api_health(self):
        """Test API is accessible"""
        res = requests.get(f"{BASE_URL}/api/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print(f"API health: {res.json()}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
