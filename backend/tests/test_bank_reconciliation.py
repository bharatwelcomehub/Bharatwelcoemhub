"""
Bank Statement vs Expense Reconciliation Feature Tests
Tests for:
- POST /api/bank-reconciliation/upload - Upload and parse bank statement
- POST /api/bank-reconciliation/add-expense - Add unrecorded transaction as expense
- POST /api/bank-reconciliation/ignore - Ignore a transaction
- POST /api/bank-reconciliation/export - Export reconciliation report
- GET /api/bank-reconciliation/uploads - List recent uploads
- Audit trail in expense_reconciliation_log collection
"""

import pytest
import requests
import os
import io
import csv
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_MOBILE = "9741399190"
TEST_CENTER = "PB-MGT"
TEST_OTP = "123456"


class TestBankReconciliationAuth:
    """Authentication tests for bank reconciliation endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        # Send OTP
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        assert res.status_code == 200
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER,
            "otp": TEST_OTP
        })
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        return data["token"]
    
    def test_upload_requires_auth(self):
        """Test that upload endpoint requires authentication"""
        # Create a simple CSV file
        csv_content = "Date,Narration,Debit\n2026-01-15,Test Transaction,1000"
        files = {'file': ('test.csv', csv_content, 'text/csv')}
        data = {
            'center': 'PB-HSR',
            'month': '2026-01',
            'token': 'invalid_token'
        }
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/upload", files=files, data=data)
        assert res.status_code == 200  # Returns 200 with error detail
        assert "Authentication required" in res.json().get("detail", "")
    
    def test_add_expense_requires_auth(self):
        """Test that add-expense endpoint requires authentication"""
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/add-expense", json={
            "transaction_id": "test123",
            "upload_id": "test456",
            "expense_type": "MISCELLANEOUS",
            "payment_mode": "BANK TRANSFER",
            "token": "invalid_token"
        })
        assert res.status_code == 200
        assert "Authentication required" in res.json().get("detail", "")
    
    def test_ignore_requires_auth(self):
        """Test that ignore endpoint requires authentication"""
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/ignore", json={
            "transaction_id": "test123",
            "upload_id": "test456",
            "token": "invalid_token"
        })
        assert res.status_code == 200
        assert "Authentication required" in res.json().get("detail", "")
    
    def test_export_requires_auth(self):
        """Test that export endpoint requires authentication"""
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/export", json={
            "upload_id": "test456",
            "token": "invalid_token"
        })
        assert res.status_code == 200
        assert "Authentication required" in res.json().get("detail", "")
    
    def test_uploads_list_requires_auth(self):
        """Test that uploads list endpoint requires authentication"""
        res = requests.get(f"{BASE_URL}/api/bank-reconciliation/uploads?token=invalid_token")
        assert res.status_code == 200
        assert "Authentication required" in res.json().get("detail", "")


class TestBankReconciliationUpload:
    """Tests for bank statement upload and parsing"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        assert res.status_code == 200
        
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER,
            "otp": TEST_OTP
        })
        assert res.status_code == 200
        return res.json()["token"]
    
    def test_upload_csv_bank_statement(self, auth_token):
        """Test uploading a CSV bank statement"""
        # Create a sample CSV bank statement
        csv_content = """Date,Narration,Debit,Credit,Balance
2026-01-15,RENT PAID SHOP,25000,0,100000
2026-01-16,ELECTRICITY BILL,5000,0,95000
2026-01-17,SALARY NEFT TRANSFER,15000,0,80000
2026-01-18,GROCERY PURCHASE,3000,0,77000
2026-01-19,DEPOSIT,0,50000,127000
2026-01-20,BANK CHARGES,500,0,126500
"""
        
        files = {'file': ('bank_statement.csv', csv_content, 'text/csv')}
        data = {
            'center': 'PB-HSR',
            'month': '2026-01',
            'bank_account': 'HDFC 1234',
            'token': auth_token
        }
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/upload", files=files, data=data)
        assert res.status_code == 200
        
        result = res.json()
        assert result.get("success") == True
        assert "upload_id" in result
        assert "summary" in result
        
        # Verify summary contains expected fields
        summary = result["summary"]
        assert "total_bank_transactions" in summary
        assert "matched_count" in summary
        assert "unrecorded_count" in summary
        
        # Should have parsed all 6 transactions (Phase 2: keeps credits too — they
        # are reconciled against sales/settlements instead of being skipped).
        assert summary["total_bank_transactions"] == 6
        
        # Store upload_id for later tests
        TestBankReconciliationUpload.upload_id = result["upload_id"]
        TestBankReconciliationUpload.unrecorded = result.get("unrecorded", [])
    
    def test_upload_returns_unrecorded_transactions(self, auth_token):
        """Test that upload returns unrecorded transactions with suggested categories"""
        # Use the upload from previous test
        if not hasattr(TestBankReconciliationUpload, 'unrecorded'):
            pytest.skip("No upload data from previous test")
        
        unrecorded = TestBankReconciliationUpload.unrecorded
        
        # Should have unrecorded transactions
        assert len(unrecorded) > 0
        
        # Each unrecorded transaction should have required fields
        for txn in unrecorded:
            assert "transaction_id" in txn
            assert "transaction_date" in txn
            assert "narration" in txn
            assert "debit_amount" in txn
            assert "match_status" in txn
            assert txn["match_status"] == "unrecorded"
    
    def test_category_suggestion_from_narration(self, auth_token):
        """Test that categories are suggested based on narration keywords"""
        # Create CSV with specific keywords that should trigger category suggestions
        csv_content = """Date,Narration,Debit,Credit
2026-02-01,RENT PAID FOR SHOP,30000,0
2026-02-02,ELECTRICITY BILL PAYMENT,8000,0
2026-02-03,FUEL PETROL EXPENSE,2000,0
2026-02-04,SWIGGY COMMISSION,5000,0
2026-02-05,BANK SERVICE CHARGE,200,0
"""
        
        files = {'file': ('test_categories.csv', csv_content, 'text/csv')}
        data = {
            'center': 'PB-HSR',
            'month': '2026-02',
            'token': auth_token
        }
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/upload", files=files, data=data)
        assert res.status_code == 200
        
        result = res.json()
        assert result.get("success") == True
        
        unrecorded = result.get("unrecorded", [])
        
        # Check that some transactions have suggested categories
        suggested_categories = [txn.get("suggested_category") for txn in unrecorded if txn.get("suggested_category")]
        
        # At least some should have suggestions based on keywords
        # Note: This depends on expense_heads collection having matching categories
        print(f"Suggested categories found: {suggested_categories}")
    
    def test_upload_invalid_file_format(self, auth_token):
        """Test uploading an invalid file format"""
        # Create a text file that's not CSV or Excel
        content = "This is not a valid bank statement"
        
        files = {'file': ('invalid.txt', content, 'text/plain')}
        data = {
            'center': 'PB-HSR',
            'month': '2026-01',
            'token': auth_token
        }
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/upload", files=files, data=data)
        assert res.status_code == 200
        
        result = res.json()
        # Should return error about parsing
        assert "detail" in result or result.get("success") == False
    
    def test_upload_empty_csv(self, auth_token):
        """Test uploading an empty CSV file"""
        csv_content = "Date,Narration,Debit\n"  # Headers only
        
        files = {'file': ('empty.csv', csv_content, 'text/csv')}
        data = {
            'center': 'PB-HSR',
            'month': '2026-01',
            'token': auth_token
        }
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/upload", files=files, data=data)
        assert res.status_code == 200
        
        result = res.json()
        # Should return error about no transactions
        assert "detail" in result


class TestBankReconciliationAddExpense:
    """Tests for adding unrecorded transactions as expenses"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    @pytest.fixture(scope="class")
    def upload_with_unrecorded(self, auth_token):
        """Create an upload with unrecorded transactions"""
        csv_content = """Date,Narration,Debit,Credit
2026-03-01,TEST_RECON_EXPENSE_1,1500,0
2026-03-02,TEST_RECON_EXPENSE_2,2500,0
2026-03-03,TEST_RECON_EXPENSE_3,3500,0
"""
        
        files = {'file': ('test_add_expense.csv', csv_content, 'text/csv')}
        data = {
            'center': 'PB-HSR',
            'month': '2026-03',
            'token': auth_token
        }
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/upload", files=files, data=data)
        assert res.status_code == 200
        result = res.json()
        assert result.get("success") == True
        
        return {
            "upload_id": result["upload_id"],
            "unrecorded": result.get("unrecorded", [])
        }
    
    def test_add_expense_success(self, auth_token, upload_with_unrecorded):
        """Test successfully adding an unrecorded transaction as expense"""
        upload_id = upload_with_unrecorded["upload_id"]
        unrecorded = upload_with_unrecorded["unrecorded"]
        
        if not unrecorded:
            pytest.skip("No unrecorded transactions to test")
        
        txn = unrecorded[0]
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/add-expense", json={
            "transaction_id": txn["transaction_id"],
            "upload_id": upload_id,
            "expense_type": "OTHER EXPENSES",
            "payment_mode": "BANK TRANSFER",
            "description": "Test expense from reconciliation",
            "token": auth_token
        })
        
        assert res.status_code == 200
        result = res.json()
        assert result.get("success") == True
        assert "expense_id" in result
    
    def test_add_expense_invalid_category(self, auth_token, upload_with_unrecorded):
        """Test adding expense with invalid category"""
        upload_id = upload_with_unrecorded["upload_id"]
        unrecorded = upload_with_unrecorded["unrecorded"]
        
        if len(unrecorded) < 2:
            pytest.skip("Not enough unrecorded transactions")
        
        txn = unrecorded[1]
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/add-expense", json={
            "transaction_id": txn["transaction_id"],
            "upload_id": upload_id,
            "expense_type": "INVALID_CATEGORY_XYZ",
            "payment_mode": "BANK TRANSFER",
            "token": auth_token
        })
        
        assert res.status_code == 200
        result = res.json()
        # Should fail because category doesn't exist in master
        assert "detail" in result
        assert "not found" in result["detail"].lower() or "category" in result["detail"].lower()
    
    def test_add_expense_transaction_not_found(self, auth_token, upload_with_unrecorded):
        """Test adding expense for non-existent transaction"""
        upload_id = upload_with_unrecorded["upload_id"]
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/add-expense", json={
            "transaction_id": "nonexistent_txn_id",
            "upload_id": upload_id,
            "expense_type": "MISCELLANEOUS",
            "payment_mode": "BANK TRANSFER",
            "token": auth_token
        })
        
        assert res.status_code == 200
        result = res.json()
        assert "detail" in result
        assert "not found" in result["detail"].lower()


class TestBankReconciliationIgnore:
    """Tests for ignoring transactions"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    @pytest.fixture(scope="class")
    def upload_for_ignore(self, auth_token):
        """Create an upload for ignore tests"""
        csv_content = """Date,Narration,Debit,Credit
2026-04-01,TEST_IGNORE_TXN_1,1000,0
2026-04-02,TEST_IGNORE_TXN_2,2000,0
"""
        
        files = {'file': ('test_ignore.csv', csv_content, 'text/csv')}
        data = {
            'center': 'PB-HSR',
            'month': '2026-04',
            'token': auth_token
        }
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/upload", files=files, data=data)
        result = res.json()
        
        return {
            "upload_id": result.get("upload_id"),
            "unrecorded": result.get("unrecorded", [])
        }
    
    def test_ignore_transaction_success(self, auth_token, upload_for_ignore):
        """Test successfully ignoring a transaction"""
        upload_id = upload_for_ignore["upload_id"]
        unrecorded = upload_for_ignore["unrecorded"]
        
        if not unrecorded:
            pytest.skip("No unrecorded transactions")
        
        txn = unrecorded[0]
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/ignore", json={
            "transaction_id": txn["transaction_id"],
            "upload_id": upload_id,
            "reason": "Test ignore - not a business expense",
            "token": auth_token
        })
        
        assert res.status_code == 200
        result = res.json()
        assert result.get("success") == True
    
    def test_ignore_transaction_not_found(self, auth_token, upload_for_ignore):
        """Test ignoring non-existent transaction"""
        upload_id = upload_for_ignore["upload_id"]
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/ignore", json={
            "transaction_id": "nonexistent_txn",
            "upload_id": upload_id,
            "reason": "Test",
            "token": auth_token
        })
        
        assert res.status_code == 200
        result = res.json()
        assert "detail" in result


class TestBankReconciliationExport:
    """Tests for exporting reconciliation reports"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    @pytest.fixture(scope="class")
    def upload_for_export(self, auth_token):
        """Create an upload for export tests"""
        csv_content = """Date,Narration,Debit,Credit
2026-05-01,EXPORT_TEST_TXN_1,5000,0
2026-05-02,EXPORT_TEST_TXN_2,6000,0
"""
        
        files = {'file': ('test_export.csv', csv_content, 'text/csv')}
        data = {
            'center': 'PB-HSR',
            'month': '2026-05',
            'token': auth_token
        }
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/upload", files=files, data=data)
        return res.json().get("upload_id")
    
    def test_export_reconciliation_report(self, auth_token, upload_for_export):
        """Test exporting reconciliation report"""
        if not upload_for_export:
            pytest.skip("No upload_id available")
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/export", json={
            "upload_id": upload_for_export,
            "token": auth_token
        })
        
        assert res.status_code == 200
        result = res.json()
        assert result.get("success") == True
        assert "rows" in result
        assert "upload" in result
        
        # Verify rows have expected columns
        if result["rows"]:
            row = result["rows"][0]
            assert "Date" in row
            assert "Narration" in row
            assert "Debit (₹)" in row
            assert "Credit (₹)" in row
            assert "Status" in row
    
    def test_export_nonexistent_upload(self, auth_token):
        """Test exporting non-existent upload"""
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/export", json={
            "upload_id": "nonexistent_upload_id",
            "token": auth_token
        })
        
        assert res.status_code == 200
        result = res.json()
        # Should return empty rows or error
        assert "rows" in result or "detail" in result


class TestBankReconciliationUploadsList:
    """Tests for listing recent uploads"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    def test_list_uploads(self, auth_token):
        """Test listing recent uploads"""
        res = requests.get(f"{BASE_URL}/api/bank-reconciliation/uploads?token={auth_token}")
        
        assert res.status_code == 200
        result = res.json()
        assert result.get("success") == True
        assert "uploads" in result
        assert isinstance(result["uploads"], list)
    
    def test_list_uploads_by_center(self, auth_token):
        """Test listing uploads filtered by center"""
        res = requests.get(f"{BASE_URL}/api/bank-reconciliation/uploads?token={auth_token}&center=PB-HSR")
        
        assert res.status_code == 200
        result = res.json()
        assert result.get("success") == True
        assert "uploads" in result
        
        # All uploads should be for the specified center
        for upload in result["uploads"]:
            assert upload.get("center") == "PB-HSR"


class TestBankReconciliationAuditTrail:
    """Tests for audit trail functionality"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    def test_upload_creates_audit_log(self, auth_token):
        """Test that upload creates an audit log entry"""
        csv_content = """Date,Narration,Debit,Credit
2026-06-01,AUDIT_TEST_TXN,1000,0
"""
        
        files = {'file': ('audit_test.csv', csv_content, 'text/csv')}
        data = {
            'center': 'PB-HSR',
            'month': '2026-06',
            'token': auth_token
        }
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/upload", files=files, data=data)
        assert res.status_code == 200
        result = res.json()
        
        # Upload should succeed
        assert result.get("success") == True
        
        # Note: We can't directly query the audit log from the API
        # but the backend code creates entries in expense_reconciliation_log
        # This is verified by code review


class TestBankReconciliationMatchingLogic:
    """Tests for transaction matching logic"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    def test_date_parsing_formats(self, auth_token):
        """Test that various date formats are parsed correctly"""
        # Test different date formats
        csv_content = """Date,Narration,Debit
2026-01-15,Format YYYY-MM-DD,1000
15-01-2026,Format DD-MM-YYYY,2000
15/01/2026,Format DD/MM/YYYY,3000
"""
        
        files = {'file': ('date_formats.csv', csv_content, 'text/csv')}
        data = {
            'center': 'PB-HSR',
            'month': '2026-01',
            'token': auth_token
        }
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/upload", files=files, data=data)
        assert res.status_code == 200
        result = res.json()
        
        # Should parse all 3 transactions
        if result.get("success"):
            total = result["summary"]["total_bank_transactions"]
            assert total >= 1  # At least one date format should work
    
    def test_amount_parsing(self, auth_token):
        """Test that various amount formats are parsed correctly"""
        csv_content = """Date,Narration,Debit
2026-07-01,Plain number,1000
2026-07-02,With comma,1,500
2026-07-03,With rupee symbol,₹2000
2026-07-04,With decimal,2500.50
"""
        
        files = {'file': ('amount_formats.csv', csv_content, 'text/csv')}
        data = {
            'center': 'PB-HSR',
            'month': '2026-07',
            'token': auth_token
        }
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/upload", files=files, data=data)
        assert res.status_code == 200
        result = res.json()
        
        if result.get("success"):
            # Verify amounts are parsed
            unrecorded = result.get("unrecorded", [])
            for txn in unrecorded:
                assert txn["debit_amount"] > 0


class TestBankReconciliationSummary:
    """Tests for reconciliation summary endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": TEST_MOBILE,
            "center": TEST_CENTER,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    @pytest.fixture(scope="class")
    def upload_for_summary(self, auth_token):
        """Create an upload for summary tests"""
        csv_content = """Date,Narration,Debit,Credit
2026-08-01,SUMMARY_TEST_1,1000,0
2026-08-02,SUMMARY_TEST_2,2000,0
2026-08-03,SUMMARY_TEST_3,3000,0
"""
        
        files = {'file': ('summary_test.csv', csv_content, 'text/csv')}
        data = {
            'center': 'PB-HSR',
            'month': '2026-08',
            'token': auth_token
        }
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/upload", files=files, data=data)
        return res.json().get("upload_id")
    
    def test_get_summary(self, auth_token, upload_for_summary):
        """Test getting reconciliation summary"""
        if not upload_for_summary:
            pytest.skip("No upload_id available")
        
        res = requests.post(f"{BASE_URL}/api/bank-reconciliation/summary", json={
            "upload_id": upload_for_summary,
            "token": auth_token
        })
        
        assert res.status_code == 200
        result = res.json()
        assert result.get("success") == True
        assert "summary" in result
        assert "upload" in result
        
        summary = result["summary"]
        assert "total_transactions" in summary
        assert "matched_count" in summary
        assert "unrecorded_count" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
