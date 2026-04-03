# =======================================
# Franchise Exit & Closure Module Tests
# Tests all exit-related API endpoints and PDF generation
# =======================================

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://bank-recon-fix-1.preview.emergentagent.com')

# Test credentials
TEST_CENTER = "PB-MGT"
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"

# Global token storage
_token = None
_test_exit_id = None

def get_token():
    """Get authentication token"""
    global _token
    if _token:
        return _token
    
    # Request OTP (endpoint is /api/send_otp)
    res = requests.post(f"{BASE_URL}/api/send_otp", json={
        "center": TEST_CENTER,
        "mobile": TEST_MOBILE
    })
    assert res.status_code == 200, f"Failed to request OTP: {res.text}"
    
    # Verify OTP
    res = requests.post(f"{BASE_URL}/api/verify_otp", json={
        "center": TEST_CENTER,
        "mobile": TEST_MOBILE,
        "otp": TEST_OTP
    })
    assert res.status_code == 200, f"Failed to verify OTP: {res.text}"
    data = res.json()
    _token = data.get("token")
    assert _token, "No token received"
    return _token


class TestAuthentication:
    """Test authentication requirements for exit endpoints"""
    
    def test_list_exits_requires_auth(self):
        """List exits should require valid token"""
        res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={})
        assert res.status_code == 401, "Should require authentication"
    
    def test_list_exits_invalid_token(self):
        """List exits should reject invalid token"""
        res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={"token": "invalid-token"})
        assert res.status_code == 401, "Should reject invalid token"


class TestListExits:
    """Test listing exit records"""
    
    def test_list_all_exits(self):
        """Should list all exit records"""
        token = get_token()
        res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={"token": token})
        assert res.status_code == 200, f"Failed to list exits: {res.text}"
        data = res.json()
        assert data.get("success") == True
        assert "exits" in data
        assert "total" in data
        print(f"Found {data['total']} exit records")
    
    def test_list_exits_by_status(self):
        """Should filter exits by status"""
        token = get_token()
        res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={
            "token": token,
            "status": "completed"
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        # All returned exits should have completed status
        for exit_record in data.get("exits", []):
            assert exit_record.get("status") == "completed"


class TestInitiateExit:
    """Test initiating exit process"""
    
    def test_initiate_exit_missing_fields(self):
        """Should reject initiation with missing required fields"""
        token = get_token()
        res = requests.post(f"{BASE_URL}/api/franchise-exit/initiate", json={
            "token": token,
            "franchise_code": "FR-PERTH"
            # Missing exit_reason and effective_date
        })
        # Accept 422 (validation error) or 500 (server error due to missing fields)
        assert res.status_code in [422, 500], f"Should reject missing fields, got {res.status_code}"
    
    def test_initiate_exit_invalid_franchise(self):
        """Should reject initiation for non-existent franchise"""
        token = get_token()
        res = requests.post(f"{BASE_URL}/api/franchise-exit/initiate", json={
            "token": token,
            "franchise_code": "INVALID-CODE",
            "exit_reason": "voluntary",
            "effective_date": "2026-04-01",
            "initiated_by": "franchisor"
        })
        assert res.status_code == 404, "Should return 404 for invalid franchise"
    
    def test_initiate_exit_success(self):
        """Should successfully initiate exit for valid franchise"""
        global _test_exit_id
        token = get_token()
        
        # Use a test franchise that doesn't have an active exit
        effective_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        res = requests.post(f"{BASE_URL}/api/franchise-exit/initiate", json={
            "token": token,
            "franchise_code": "FR-PERTH",
            "exit_reason": "voluntary",
            "exit_reason_details": "Test exit for automated testing",
            "effective_date": effective_date,
            "initiated_by": "franchisor"
        })
        
        # Could be 200 (success) or 400 (exit already in progress)
        if res.status_code == 200:
            data = res.json()
            assert data.get("success") == True
            assert "exit_id" in data
            _test_exit_id = data["exit_id"]
            print(f"Created exit: {_test_exit_id}")
        elif res.status_code == 400:
            # Exit already in progress - this is acceptable
            print("Exit already in progress for this franchise")
        else:
            pytest.fail(f"Unexpected status code: {res.status_code}, {res.text}")


class TestGetExitDetails:
    """Test getting exit details"""
    
    def test_get_exit_not_found(self):
        """Should return 404 for non-existent exit"""
        token = get_token()
        res = requests.post(f"{BASE_URL}/api/franchise-exit/get/INVALID-EXIT-ID", json={"token": token})
        assert res.status_code == 404
    
    def test_get_existing_exit(self):
        """Should return details for existing exit"""
        token = get_token()
        
        # First get list of exits to find an existing one
        list_res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={"token": token})
        exits = list_res.json().get("exits", [])
        
        if not exits:
            pytest.skip("No exit records to test")
        
        exit_id = exits[0]["exit_id"]
        res = requests.post(f"{BASE_URL}/api/franchise-exit/get/{exit_id}", json={"token": token})
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        assert "exit" in data
        assert "franchise" in data
        
        exit_record = data["exit"]
        assert exit_record.get("exit_id") == exit_id
        assert "franchise_code" in exit_record
        assert "status" in exit_record
        assert "steps_completed" in exit_record
        print(f"Exit {exit_id} status: {exit_record['status']}")


class TestAssetHandover:
    """Test asset handover functionality"""
    
    def test_update_asset_handover(self):
        """Should update asset handover details"""
        token = get_token()
        
        # Get an exit that's not completed
        list_res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={"token": token})
        exits = [e for e in list_res.json().get("exits", []) if e["status"] not in ["completed", "cancelled"]]
        
        if not exits:
            pytest.skip("No active exit records to test")
        
        exit_id = exits[0]["exit_id"]
        
        res = requests.post(f"{BASE_URL}/api/franchise-exit/update-asset-handover/{exit_id}", json={
            "token": token,
            "kitchen_equipment": [
                {"name": "Commercial Stove", "quantity": "2", "condition": "Good", "remarks": "Working condition"}
            ],
            "furniture_fixtures": [
                {"name": "Dining Tables", "quantity": "10", "condition": "Fair", "remarks": "Minor scratches"}
            ],
            "utensils_machinery": [],
            "food_inventory": [],
            "packaging_materials": [],
            "other_assets": [],
            "condition_notes": "Overall assets in acceptable condition"
        })
        
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        print(f"Asset handover updated for {exit_id}")


class TestFinancialSettlement:
    """Test financial settlement functionality"""
    
    def test_update_financial_settlement(self):
        """Should update financial settlement details"""
        token = get_token()
        
        # Get an exit that's not completed
        list_res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={"token": token})
        exits = [e for e in list_res.json().get("exits", []) if e["status"] not in ["completed", "cancelled"]]
        
        if not exits:
            pytest.skip("No active exit records to test")
        
        exit_id = exits[0]["exit_id"]
        
        res = requests.post(f"{BASE_URL}/api/franchise-exit/update-financial-settlement/{exit_id}", json={
            "token": token,
            "working_capital_balance": 500000,
            "staff_salary_current": 50000,
            "shop_rental_current": 75000,
            "vendor_payments": 25000,
            "utility_bills": 10000,
            "other_dues": 5000,
            "settlement_notes": "Test settlement for automated testing"
        })
        
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        print(f"Financial settlement updated for {exit_id}")


class TestSignatures:
    """Test signature functionality"""
    
    def test_add_franchisor_signature(self):
        """Should add franchisor signature"""
        token = get_token()
        
        # Get an exit that's not completed
        list_res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={"token": token})
        exits = [e for e in list_res.json().get("exits", []) if e["status"] not in ["completed", "cancelled"]]
        
        if not exits:
            pytest.skip("No active exit records to test")
        
        exit_id = exits[0]["exit_id"]
        
        res = requests.post(f"{BASE_URL}/api/franchise-exit/sign/{exit_id}", json={
            "token": token,
            "signer_role": "franchisor",
            "signer_name": "Test Franchisor",
            "signer_designation": "Director"
        })
        
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        print(f"Franchisor signature added for {exit_id}")
    
    def test_add_franchisee_signature(self):
        """Should add franchisee signature"""
        token = get_token()
        
        # Get an exit that's not completed
        list_res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={"token": token})
        exits = [e for e in list_res.json().get("exits", []) if e["status"] not in ["completed", "cancelled"]]
        
        if not exits:
            pytest.skip("No active exit records to test")
        
        exit_id = exits[0]["exit_id"]
        
        res = requests.post(f"{BASE_URL}/api/franchise-exit/sign/{exit_id}", json={
            "token": token,
            "signer_role": "franchisee",
            "signer_name": "Test Franchisee",
            "signer_designation": "Managing Partner"
        })
        
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        print(f"Franchisee signature added for {exit_id}")
    
    def test_invalid_signer_role(self):
        """Should reject invalid signer role"""
        token = get_token()
        
        list_res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={"token": token})
        exits = [e for e in list_res.json().get("exits", []) if e["status"] not in ["completed", "cancelled"]]
        
        if not exits:
            pytest.skip("No active exit records to test")
        
        exit_id = exits[0]["exit_id"]
        
        res = requests.post(f"{BASE_URL}/api/franchise-exit/sign/{exit_id}", json={
            "token": token,
            "signer_role": "invalid_role",
            "signer_name": "Test",
            "signer_designation": "Test"
        })
        
        assert res.status_code == 400


class TestCompliance:
    """Test compliance checklist functionality"""
    
    def test_update_compliance(self):
        """Should update compliance checklist"""
        token = get_token()
        
        # Get an exit that's not completed
        list_res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={"token": token})
        exits = [e for e in list_res.json().get("exits", []) if e["status"] not in ["completed", "cancelled"]]
        
        if not exits:
            pytest.skip("No active exit records to test")
        
        exit_id = exits[0]["exit_id"]
        
        res = requests.post(f"{BASE_URL}/api/franchise-exit/update-compliance/{exit_id}", json={
            "token": token,
            "no_pending_payments": True,
            "brand_assets_transferred": True,
            "financial_report_signed": True,
            "handover_report_signed": True
        })
        
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        print(f"Compliance updated for {exit_id}")


class TestPDFGeneration:
    """Test PDF document generation"""
    
    def test_generate_exit_agreement_pdf(self):
        """Should generate Exit Agreement PDF"""
        token = get_token()
        
        # Get any exit record
        list_res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={"token": token})
        exits = list_res.json().get("exits", [])
        
        if not exits:
            pytest.skip("No exit records to test")
        
        exit_id = exits[0]["exit_id"]
        
        res = requests.post(f"{BASE_URL}/api/franchise-exit/generate-exit-agreement/{exit_id}", json={"token": token})
        
        assert res.status_code == 200, f"Failed to generate PDF: {res.text}"
        assert res.headers.get("content-type") == "application/pdf"
        assert "Content-Disposition" in res.headers
        
        # Verify PDF content
        content = res.content
        assert content[:4] == b'%PDF', "Response should be valid PDF"
        print(f"Exit Agreement PDF generated: {len(content)} bytes")
    
    def test_generate_handover_report_pdf(self):
        """Should generate Handover Report PDF"""
        token = get_token()
        
        # Get an exit with asset handover data
        list_res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={"token": token})
        exits = list_res.json().get("exits", [])
        
        # Find exit with asset_handover
        exit_with_assets = None
        for exit_record in exits:
            detail_res = requests.post(f"{BASE_URL}/api/franchise-exit/get/{exit_record['exit_id']}", json={"token": token})
            if detail_res.status_code == 200:
                detail = detail_res.json().get("exit", {})
                if detail.get("asset_handover"):
                    exit_with_assets = exit_record
                    break
        
        if not exit_with_assets:
            pytest.skip("No exit with asset handover data")
        
        exit_id = exit_with_assets["exit_id"]
        res = requests.post(f"{BASE_URL}/api/franchise-exit/generate-handover-report/{exit_id}", json={"token": token})
        
        assert res.status_code == 200, f"Failed to generate PDF: {res.text}"
        assert res.headers.get("content-type") == "application/pdf"
        
        content = res.content
        assert content[:4] == b'%PDF', "Response should be valid PDF"
        print(f"Handover Report PDF generated: {len(content)} bytes")
    
    def test_generate_settlement_sheet_pdf(self):
        """Should generate Settlement Sheet PDF"""
        token = get_token()
        
        # Get an exit with financial settlement data
        list_res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={"token": token})
        exits = list_res.json().get("exits", [])
        
        # Find exit with financial_settlement
        exit_with_settlement = None
        for exit_record in exits:
            detail_res = requests.post(f"{BASE_URL}/api/franchise-exit/get/{exit_record['exit_id']}", json={"token": token})
            if detail_res.status_code == 200:
                detail = detail_res.json().get("exit", {})
                if detail.get("financial_settlement"):
                    exit_with_settlement = exit_record
                    break
        
        if not exit_with_settlement:
            pytest.skip("No exit with financial settlement data")
        
        exit_id = exit_with_settlement["exit_id"]
        res = requests.post(f"{BASE_URL}/api/franchise-exit/generate-settlement-sheet/{exit_id}", json={"token": token})
        
        assert res.status_code == 200, f"Failed to generate PDF: {res.text}"
        assert res.headers.get("content-type") == "application/pdf"
        
        content = res.content
        assert content[:4] == b'%PDF', "Response should be valid PDF"
        print(f"Settlement Sheet PDF generated: {len(content)} bytes")
    
    def test_generate_exit_certificate_pdf(self):
        """Should generate Exit Certificate PDF for completed exit"""
        token = get_token()
        
        # Get a completed exit
        list_res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={
            "token": token,
            "status": "completed"
        })
        exits = list_res.json().get("exits", [])
        
        if not exits:
            pytest.skip("No completed exit records to test")
        
        exit_id = exits[0]["exit_id"]
        res = requests.post(f"{BASE_URL}/api/franchise-exit/generate-exit-certificate/{exit_id}", json={"token": token})
        
        assert res.status_code == 200, f"Failed to generate PDF: {res.text}"
        assert res.headers.get("content-type") == "application/pdf"
        
        content = res.content
        assert content[:4] == b'%PDF', "Response should be valid PDF"
        print(f"Exit Certificate PDF generated: {len(content)} bytes")
    
    def test_certificate_requires_completed_status(self):
        """Exit certificate should only be generated for completed exits"""
        token = get_token()
        
        # Get a non-completed exit
        list_res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={"token": token})
        exits = [e for e in list_res.json().get("exits", []) if e["status"] != "completed"]
        
        if not exits:
            pytest.skip("No non-completed exit records to test")
        
        exit_id = exits[0]["exit_id"]
        res = requests.post(f"{BASE_URL}/api/franchise-exit/generate-exit-certificate/{exit_id}", json={"token": token})
        
        assert res.status_code == 400, "Should reject certificate generation for non-completed exit"


class TestCompleteExit:
    """Test exit completion functionality"""
    
    def test_complete_exit_requires_all_steps(self):
        """Should not complete exit without all steps done"""
        token = get_token()
        
        # Get an exit that's not completed and doesn't have all steps
        list_res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={"token": token})
        exits = list_res.json().get("exits", [])
        
        incomplete_exit = None
        for exit_record in exits:
            if exit_record["status"] not in ["completed", "cancelled"]:
                steps = exit_record.get("steps_completed", {})
                required_steps = ["exit_agreement", "asset_handover", "financial_settlement", "compliance_confirmation"]
                if not all(steps.get(s) for s in required_steps):
                    incomplete_exit = exit_record
                    break
        
        if not incomplete_exit:
            pytest.skip("No incomplete exit records to test")
        
        exit_id = incomplete_exit["exit_id"]
        res = requests.post(f"{BASE_URL}/api/franchise-exit/complete/{exit_id}", json={"token": token})
        
        # Should fail because not all steps are complete
        assert res.status_code == 400, "Should reject completion without all steps"


class TestCancelExit:
    """Test exit cancellation functionality"""
    
    def test_cancel_completed_exit_fails(self):
        """Should not allow cancelling a completed exit"""
        token = get_token()
        
        # Get a completed exit
        list_res = requests.post(f"{BASE_URL}/api/franchise-exit/list", json={
            "token": token,
            "status": "completed"
        })
        exits = list_res.json().get("exits", [])
        
        if not exits:
            pytest.skip("No completed exit records to test")
        
        exit_id = exits[0]["exit_id"]
        res = requests.post(f"{BASE_URL}/api/franchise-exit/cancel/{exit_id}", json={
            "token": token,
            "cancellation_reason": "Test cancellation"
        })
        
        assert res.status_code == 400, "Should not allow cancelling completed exit"


class TestExistingCompletedExit:
    """Test the existing completed exit record"""
    
    def test_existing_completed_exit(self):
        """Verify the existing completed exit EXIT-FR-TEST-INDIA-20260322094816"""
        token = get_token()
        
        exit_id = "EXIT-FR-TEST-INDIA-20260322094816"
        res = requests.post(f"{BASE_URL}/api/franchise-exit/get/{exit_id}", json={"token": token})
        
        if res.status_code == 404:
            pytest.skip("Existing completed exit not found")
        
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        
        exit_record = data["exit"]
        assert exit_record["status"] == "completed"
        assert exit_record["franchise_code"] == "FR-TEST-INDIA"
        
        # Verify all steps are completed
        steps = exit_record.get("steps_completed", {})
        assert steps.get("exit_agreement") == True
        assert steps.get("asset_handover") == True
        assert steps.get("financial_settlement") == True
        assert steps.get("compliance_confirmation") == True
        assert steps.get("exit_certificate") == True
        
        print(f"Verified completed exit: {exit_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
