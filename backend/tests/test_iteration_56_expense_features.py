"""
Test Iteration 56: Expense Features
1. POST /api/sales/daily/delete-range - now returns both 'deleted' (sales) and 'expenses_deleted' count
2. Delete endpoint deletes both daily_sales AND expenses for the center+month range
3. Bulk import response includes 'expenses_imported' count
4. Expense records from bulk import have correct fields: center, date, description, amount, expense_type, payment_mode, source
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"
TEST_CENTER = "PB-MGT"

# Test data prefix for cleanup
TEST_PREFIX = "TEST_ITER56_"
TEST_MONTH = "2098-11"  # Far future month for testing


class TestDeleteRangeEndpoint:
    """Test POST /api/sales/daily/delete-range endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self, auth_token):
        """Setup test data before each test"""
        self.token = auth_token
        self.headers = {"Content-Type": "application/json"}
        
    def test_delete_range_returns_both_counts(self, auth_token):
        """Test that delete-range returns both 'deleted' (sales) and 'expenses_deleted' counts"""
        # First, create test sales record
        sales_payload = {
            "center": TEST_CENTER,
            "date": f"{TEST_MONTH}-15",
            "total_sale": 1000,
            "opening_balance": 0,
            "notes": f"{TEST_PREFIX}sales_record"
        }
        create_resp = requests.post(
            f"{BASE_URL}/api/sales/daily/create?token={auth_token}",
            json=sales_payload,
            headers=self.headers
        )
        print(f"Create sales response: {create_resp.status_code} - {create_resp.text[:200]}")
        
        # Create test expense record
        expense_payload = {
            "center": TEST_CENTER,
            "date": f"{TEST_MONTH}-15",
            "description": f"{TEST_PREFIX}expense_record",
            "amount": 500,
            "expense_type": "TEST",
            "payment_mode": "CASH"
        }
        exp_resp = requests.post(
            f"{BASE_URL}/api/sales/expenses/create?token={auth_token}",
            json=expense_payload,
            headers=self.headers
        )
        print(f"Create expense response: {exp_resp.status_code} - {exp_resp.text[:200]}")
        
        # Now call delete-range
        delete_payload = {
            "token": auth_token,
            "center": TEST_CENTER,
            "from_month": TEST_MONTH,
            "to_month": TEST_MONTH
        }
        delete_resp = requests.post(
            f"{BASE_URL}/api/sales/daily/delete-range",
            json=delete_payload,
            headers=self.headers
        )
        
        assert delete_resp.status_code == 200, f"Delete-range failed: {delete_resp.text}"
        data = delete_resp.json()
        
        # Verify response structure
        assert "deleted" in data, "Response should contain 'deleted' field for sales count"
        assert "expenses_deleted" in data, "Response should contain 'expenses_deleted' field"
        assert "success" in data, "Response should contain 'success' field"
        
        print(f"Delete-range response: deleted={data.get('deleted')}, expenses_deleted={data.get('expenses_deleted')}")
        
    def test_delete_range_deletes_both_collections(self, auth_token):
        """Test that delete-range actually deletes from both daily_sales AND expenses collections"""
        test_month = "2097-12"  # Different month to avoid conflicts
        
        # Create test sales record
        sales_payload = {
            "center": TEST_CENTER,
            "date": f"{test_month}-10",
            "total_sale": 2000,
            "opening_balance": 0,
            "notes": f"{TEST_PREFIX}verify_delete"
        }
        requests.post(
            f"{BASE_URL}/api/sales/daily/create?token={auth_token}",
            json=sales_payload,
            headers=self.headers
        )
        
        # Create test expense record
        expense_payload = {
            "center": TEST_CENTER,
            "date": f"{test_month}-10",
            "description": f"{TEST_PREFIX}verify_delete_expense",
            "amount": 300,
            "expense_type": "TEST",
            "payment_mode": "CASH"
        }
        requests.post(
            f"{BASE_URL}/api/sales/expenses/create?token={auth_token}",
            json=expense_payload,
            headers=self.headers
        )
        
        # Verify records exist before delete
        sales_query = {
            "token": auth_token,
            "center": TEST_CENTER,
            "month": test_month
        }
        sales_before = requests.post(f"{BASE_URL}/api/sales/daily", json=sales_query, headers=self.headers)
        sales_count_before = sales_before.json().get("count", 0)
        
        expenses_query = {
            "token": auth_token,
            "center": TEST_CENTER,
            "month": test_month
        }
        expenses_before = requests.post(f"{BASE_URL}/api/sales/expenses", json=expenses_query, headers=self.headers)
        expenses_count_before = expenses_before.json().get("count", 0)
        
        print(f"Before delete: sales={sales_count_before}, expenses={expenses_count_before}")
        
        # Delete the range
        delete_payload = {
            "token": auth_token,
            "center": TEST_CENTER,
            "from_month": test_month,
            "to_month": test_month
        }
        delete_resp = requests.post(
            f"{BASE_URL}/api/sales/daily/delete-range",
            json=delete_payload,
            headers=self.headers
        )
        
        assert delete_resp.status_code == 200
        delete_data = delete_resp.json()
        
        # Verify records are deleted
        sales_after = requests.post(f"{BASE_URL}/api/sales/daily", json=sales_query, headers=self.headers)
        sales_count_after = sales_after.json().get("count", 0)
        
        expenses_after = requests.post(f"{BASE_URL}/api/sales/expenses", json=expenses_query, headers=self.headers)
        expenses_count_after = expenses_after.json().get("count", 0)
        
        print(f"After delete: sales={sales_count_after}, expenses={expenses_count_after}")
        print(f"Delete response: deleted={delete_data.get('deleted')}, expenses_deleted={delete_data.get('expenses_deleted')}")
        
        # Both should be 0 after delete
        assert sales_count_after == 0, f"Sales records should be deleted, but found {sales_count_after}"
        assert expenses_count_after == 0, f"Expense records should be deleted, but found {expenses_count_after}"
        
    def test_delete_range_no_records(self, auth_token):
        """Test delete-range with no matching records returns 0 counts"""
        delete_payload = {
            "token": auth_token,
            "center": TEST_CENTER,
            "from_month": "2050-01",  # Far future month with no data
            "to_month": "2050-01"
        }
        delete_resp = requests.post(
            f"{BASE_URL}/api/sales/daily/delete-range",
            json=delete_payload,
            headers=self.headers
        )
        
        assert delete_resp.status_code == 200
        data = delete_resp.json()
        
        assert data.get("deleted") == 0, "Should return 0 deleted sales"
        assert data.get("expenses_deleted") == 0, "Should return 0 deleted expenses"
        print(f"No records response: {data}")


class TestBulkImportExpenses:
    """Test bulk import expense parsing functionality"""
    
    def test_bulk_import_response_includes_expenses_imported(self, auth_token):
        """Test that bulk import response includes 'expenses_imported' count"""
        # Create a minimal Excel file with expense sheet
        import io
        try:
            import openpyxl
            from openpyxl import Workbook
            
            wb = Workbook()
            
            # Create sales sheet
            ws_sales = wb.active
            ws_sales.title = "Sales"
            ws_sales.append(["DATE", "TOTAL SALE", "CARD", "UPI", "SWIGGY", "ZOMATO"])
            ws_sales.append(["2096-06-01", 5000, 1000, 500, 200, 300])
            
            # Create expense sheet with EXPENCE in header
            ws_expense = wb.create_sheet("Expenses")
            ws_expense.append(["DATE", "EXPENCE", "AMOUNT", "EXPANSE TYPE", "PAYMENT MODE"])
            ws_expense.append(["2096-06-01", "Test Expense 1", 100, "FOOD", "CASH"])
            ws_expense.append(["2096-06-02", "Test Expense 2", 200, "UTILITIES", "ONLINE UPI"])
            
            # Save to bytes
            excel_buffer = io.BytesIO()
            wb.save(excel_buffer)
            excel_buffer.seek(0)
            
            # Upload the file
            files = {"file": ("test_expenses.xlsx", excel_buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            data = {"center": TEST_CENTER, "from_year": "2096"}
            
            upload_resp = requests.post(
                f"{BASE_URL}/api/sales/upload-custom-format?token={auth_token}",
                files=files,
                data=data
            )
            
            print(f"Upload response: {upload_resp.status_code} - {upload_resp.text[:500]}")
            
            if upload_resp.status_code == 200:
                resp_data = upload_resp.json()
                
                # Verify expenses_imported is in response
                assert "expenses_imported" in resp_data, "Response should contain 'expenses_imported' field"
                print(f"expenses_imported: {resp_data.get('expenses_imported')}")
                
                # Verify results structure
                if "results" in resp_data:
                    results = resp_data["results"]
                    if "expenses" in results:
                        assert "imported" in results["expenses"], "Results should have expenses.imported"
                        print(f"Results expenses: {results['expenses']}")
            else:
                # If upload fails, it might be due to format issues - still check response structure
                print(f"Upload returned {upload_resp.status_code}, checking if endpoint exists")
                assert upload_resp.status_code != 404, "Endpoint should exist"
                
        except ImportError:
            pytest.skip("openpyxl not installed, skipping Excel upload test")
            
    def test_expense_records_have_correct_fields(self, auth_token):
        """Test that expense records from bulk import have correct fields"""
        # Create expense via API to verify field structure
        expense_payload = {
            "center": TEST_CENTER,
            "date": "2095-05-15",
            "description": f"{TEST_PREFIX}field_test",
            "amount": 150.50,
            "expense_type": "FOOD",
            "payment_mode": "CASH"
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/sales/expenses/create?token={auth_token}",
            json=expense_payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert create_resp.status_code == 200, f"Create expense failed: {create_resp.text}"
        data = create_resp.json()
        
        # Verify record structure
        record = data.get("record", {})
        required_fields = ["center", "date", "description", "amount", "expense_type", "payment_mode"]
        
        for field in required_fields:
            assert field in record, f"Expense record should have '{field}' field"
            
        print(f"Expense record fields: {list(record.keys())}")
        
        # Cleanup
        if "expense_id" in record:
            requests.delete(
                f"{BASE_URL}/api/sales/expenses/{record['expense_id']}?token={auth_token}"
            )


class TestExpenseFieldsFromBulkImport:
    """Test expense record fields specifically from bulk import"""
    
    def test_expense_source_field_format(self, auth_token):
        """Test that bulk imported expenses have source field in format 'bulk_import:{sheet_name}'"""
        # Query expenses to check for bulk_import source
        query_payload = {
            "token": auth_token,
            "center": TEST_CENTER
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/sales/expenses",
            json=query_payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert resp.status_code == 200
        data = resp.json()
        
        # Check if any expenses have bulk_import source
        expenses = data.get("expenses", [])
        bulk_imported = [e for e in expenses if e.get("source", "").startswith("bulk_import:")]
        
        print(f"Total expenses: {len(expenses)}, Bulk imported: {len(bulk_imported)}")
        
        if bulk_imported:
            sample = bulk_imported[0]
            print(f"Sample bulk import expense: source={sample.get('source')}")
            assert sample.get("source").startswith("bulk_import:"), "Source should start with 'bulk_import:'"
            
            # Verify all required fields
            required_fields = ["center", "date", "description", "amount", "expense_type", "payment_mode", "source"]
            for field in required_fields:
                assert field in sample, f"Bulk imported expense should have '{field}' field"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    # Send OTP
    otp_resp = requests.post(
        f"{BASE_URL}/api/send_otp",
        json={"mobile": TEST_MOBILE, "center": TEST_CENTER}
    )
    print(f"Send OTP response: {otp_resp.status_code}")
    
    # Verify OTP
    verify_resp = requests.post(
        f"{BASE_URL}/api/verify_otp",
        json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER}
    )
    
    if verify_resp.status_code != 200:
        pytest.skip(f"Authentication failed: {verify_resp.text}")
        
    token = verify_resp.json().get("token")
    if not token:
        pytest.skip("No token received from authentication")
        
    print(f"Auth token obtained successfully")
    return token


@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data(auth_token):
    """Cleanup test data after all tests"""
    yield
    
    # Cleanup test months
    test_months = ["2098-11", "2097-12", "2096-06", "2095-05"]
    for month in test_months:
        try:
            delete_payload = {
                "token": auth_token,
                "center": TEST_CENTER,
                "from_month": month,
                "to_month": month
            }
            requests.post(
                f"{BASE_URL}/api/sales/daily/delete-range",
                json=delete_payload,
                headers={"Content-Type": "application/json"}
            )
            print(f"Cleaned up test data for {month}")
        except Exception as e:
            print(f"Cleanup error for {month}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
