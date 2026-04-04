"""
Test ANZ PDF Bank Statement Parsing Fix
- Verifies that ANZ PDF parsing returns transactions (not 0)
- Tests the fallback to text-based parsing when table extraction fails
- Expected: 111 debit transactions totaling $33,182.40
"""

import pytest
import requests
import os
import tempfile

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ANZ_PDF_URL = "https://customer-assets.emergentagent.com/job_2c10de5f-98eb-4599-94c4-76d674650f81/artifacts/rm7t0unc_ANZ%20STATEMENT%20-%20JAN%20TO%20FEB%202026.pdf"

# Test credentials
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"
TEST_CENTER = "PB-MGT"
UPLOAD_CENTER = "PB-PERTH"  # Center for upload test
UPLOAD_MONTH = "2026-01"


class TestANZPDFParsing:
    """Test ANZ PDF parsing fix - fallback to text parsing when table extraction fails"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token via OTP flow"""
        # Step 1: Send OTP
        send_otp_response = requests.post(
            f"{BASE_URL}/api/send_otp",
            json={"mobile": TEST_MOBILE, "center": TEST_CENTER}
        )
        print(f"Send OTP response: {send_otp_response.status_code} - {send_otp_response.text}")
        assert send_otp_response.status_code == 200, f"Failed to send OTP: {send_otp_response.text}"
        
        # Step 2: Verify OTP
        verify_otp_response = requests.post(
            f"{BASE_URL}/api/verify_otp",
            json={"mobile": TEST_MOBILE, "otp": TEST_OTP, "center": TEST_CENTER}
        )
        print(f"Verify OTP response: {verify_otp_response.status_code} - {verify_otp_response.text}")
        assert verify_otp_response.status_code == 200, f"Failed to verify OTP: {verify_otp_response.text}"
        
        data = verify_otp_response.json()
        token = data.get("token")
        assert token, f"No token in response: {data}"
        print(f"Got auth token: {token[:20]}...")
        return token
    
    @pytest.fixture(scope="class")
    def anz_pdf_content(self):
        """Download ANZ PDF file"""
        print(f"Downloading ANZ PDF from: {ANZ_PDF_URL}")
        response = requests.get(ANZ_PDF_URL, timeout=60)
        assert response.status_code == 200, f"Failed to download PDF: {response.status_code}"
        
        content = response.content
        print(f"Downloaded PDF: {len(content)} bytes")
        assert len(content) > 0, "PDF content is empty"
        return content
    
    def test_health_check(self):
        """Test backend health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("Health check passed")
    
    def test_anz_pdf_upload_returns_transactions(self, auth_token, anz_pdf_content):
        """
        CRITICAL TEST: Upload ANZ PDF and verify it returns transactions (not 0)
        
        This tests the fix where parse_pdf_bank_statement() falls back to 
        parse_pdf_text_fallback() when table extraction yields 0 results.
        
        Expected: ~111 debit transactions totaling ~$33,182.40
        """
        # Prepare multipart form data
        files = {
            'file': ('ANZ_STATEMENT_JAN_FEB_2026.pdf', anz_pdf_content, 'application/pdf')
        }
        data = {
            'center': UPLOAD_CENTER,
            'month': UPLOAD_MONTH,
            'bank_account': 'ANZ-TEST',
            'token': auth_token
        }
        
        print(f"Uploading ANZ PDF to /api/bank-reconciliation/upload")
        print(f"  Center: {UPLOAD_CENTER}, Month: {UPLOAD_MONTH}")
        
        response = requests.post(
            f"{BASE_URL}/api/bank-reconciliation/upload",
            files=files,
            data=data,
            timeout=120  # PDF parsing may take time
        )
        
        print(f"Upload response status: {response.status_code}")
        print(f"Upload response: {response.text[:1000]}...")
        
        assert response.status_code == 200, f"Upload failed: {response.status_code} - {response.text}"
        
        result = response.json()
        
        # Check for success
        assert result.get("success") == True, f"Upload not successful: {result}"
        
        # Check summary exists
        summary = result.get("summary", {})
        assert summary, f"No summary in response: {result}"
        
        # CRITICAL: Verify transactions were parsed (not 0)
        total_bank_transactions = summary.get("total_bank_transactions", 0)
        print(f"Total bank transactions parsed: {total_bank_transactions}")
        
        assert total_bank_transactions > 0, (
            f"CRITICAL BUG: ANZ PDF parsing returned 0 transactions! "
            f"Expected ~111 transactions. Summary: {summary}"
        )
        
        # Verify reasonable number of transactions (expecting ~111)
        assert total_bank_transactions >= 50, (
            f"Too few transactions parsed: {total_bank_transactions}. "
            f"Expected ~111 transactions from ANZ PDF."
        )
        
        # Check total debit amount (expecting ~$33,182.40)
        total_bank_debits = summary.get("total_bank_debits", 0)
        print(f"Total bank debits: ${total_bank_debits}")
        
        assert total_bank_debits > 0, f"Total debits is 0: {summary}"
        
        # Verify debit total is in expected range (allowing some variance)
        # Expected: $33,182.40
        assert total_bank_debits >= 30000, (
            f"Total debits too low: ${total_bank_debits}. "
            f"Expected ~$33,182.40"
        )
        assert total_bank_debits <= 40000, (
            f"Total debits too high: ${total_bank_debits}. "
            f"Expected ~$33,182.40"
        )
        
        # Check matched and unrecorded counts
        matched_count = summary.get("matched_count", 0)
        unrecorded_count = summary.get("unrecorded_count", 0)
        
        print(f"Matched: {matched_count}, Unrecorded: {unrecorded_count}")
        
        # Total should equal total_bank_transactions
        assert matched_count + unrecorded_count == total_bank_transactions, (
            f"Matched ({matched_count}) + Unrecorded ({unrecorded_count}) != "
            f"Total ({total_bank_transactions})"
        )
        
        # Verify upload_id was returned
        upload_id = result.get("upload_id")
        assert upload_id, f"No upload_id in response: {result}"
        print(f"Upload ID: {upload_id}")
        
        # Verify transactions list is populated
        matched = result.get("matched", [])
        unrecorded = result.get("unrecorded", [])
        
        print(f"Matched transactions: {len(matched)}")
        print(f"Unrecorded transactions: {len(unrecorded)}")
        
        # Verify transaction structure
        all_transactions = matched + unrecorded
        assert len(all_transactions) > 0, "No transactions in response"
        
        # Check first transaction has required fields
        first_txn = all_transactions[0]
        required_fields = ["transaction_id", "transaction_date", "narration", "debit_amount"]
        for field in required_fields:
            assert field in first_txn, f"Missing field '{field}' in transaction: {first_txn}"
        
        print(f"\n=== ANZ PDF PARSING TEST PASSED ===")
        print(f"Total transactions: {total_bank_transactions}")
        print(f"Total debits: ${total_bank_debits}")
        print(f"Matched: {matched_count}, Unrecorded: {unrecorded_count}")
        
        return result
    
    def test_verify_transaction_dates_in_range(self, auth_token, anz_pdf_content):
        """Verify parsed transactions have dates in expected range (Jan-Feb 2026)"""
        files = {
            'file': ('ANZ_STATEMENT_JAN_FEB_2026.pdf', anz_pdf_content, 'application/pdf')
        }
        data = {
            'center': UPLOAD_CENTER,
            'month': UPLOAD_MONTH,
            'bank_account': 'ANZ-TEST-DATES',
            'token': auth_token
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bank-reconciliation/upload",
            files=files,
            data=data,
            timeout=120
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result.get("success") == True
        
        all_transactions = result.get("matched", []) + result.get("unrecorded", [])
        
        # Check dates are in expected range
        valid_date_count = 0
        for txn in all_transactions:
            date = txn.get("transaction_date", "")
            if date.startswith("2026-01") or date.startswith("2026-02"):
                valid_date_count += 1
        
        print(f"Transactions with valid dates (Jan-Feb 2026): {valid_date_count}/{len(all_transactions)}")
        
        # At least 90% should have valid dates
        assert valid_date_count >= len(all_transactions) * 0.9, (
            f"Too many transactions with invalid dates. "
            f"Valid: {valid_date_count}, Total: {len(all_transactions)}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
