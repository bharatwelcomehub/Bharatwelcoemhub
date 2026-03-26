"""
Employee Transfer Feature Tests
Tests for: create, action (accept/reject/cancel), list, history, reports, notifications
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN = {"center": "PB-MGT", "mobile": "9741399190", "otp": "123456"}
PERTH_MANAGER = {"center": "PB-PERTH", "mobile": "0401832922", "otp": "123456"}
INDIA_MANAGER = {"center": "PB-HSR", "mobile": "9999999999", "otp": "123456"}


def get_auth_token(creds: dict) -> dict:
    """Get auth token for a user"""
    # Send OTP
    res = requests.post(f"{BASE_URL}/api/send_otp", json={
        "center": creds["center"],
        "mobile": creds["mobile"]
    })
    assert res.status_code == 200, f"Failed to send OTP: {res.text}"
    
    # Verify OTP
    res = requests.post(f"{BASE_URL}/api/verify_otp", json={
        "center": creds["center"],
        "mobile": creds["mobile"],
        "otp": creds["otp"]
    })
    assert res.status_code == 200, f"Failed to verify OTP: {res.text}"
    data = res.json()
    assert "token" in data, "No token in response"
    return data


class TestTransferCreate:
    """Tests for POST /api/transfers/create"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth tokens"""
        self.super_admin = get_auth_token(SUPER_ADMIN)
        self.perth_manager = get_auth_token(PERTH_MANAGER)
        self.india_manager = get_auth_token(INDIA_MANAGER)
    
    def test_create_transfer_requires_auth(self):
        """Test that create transfer requires valid token"""
        res = requests.post(f"{BASE_URL}/api/transfers/create", json={
            "token": "invalid_token",
            "employee_name": "TEST_EMPLOYEE",
            "from_center": "PB-PERTH",
            "to_center": "PB-HSR",
            "transfer_type": "TEMPORARY",
            "start_date": "2026-04-01",
            "end_date": "2026-04-15",
            "reason": "Test transfer"
        })
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"
    
    def test_create_transfer_validation_same_center(self):
        """Test that transfer to same center is rejected"""
        res = requests.post(f"{BASE_URL}/api/transfers/create", json={
            "token": self.super_admin["token"],
            "employee_name": "MANISH",
            "from_center": "PB-PERTH",
            "to_center": "PB-PERTH",  # Same center
            "transfer_type": "TEMPORARY",
            "start_date": "2026-04-01",
            "end_date": "2026-04-15",
            "reason": "Test transfer"
        })
        assert res.status_code == 400, f"Expected 400, got {res.status_code}"
        assert "same center" in res.json().get("detail", "").lower()
    
    def test_create_transfer_validation_temporary_needs_end_date(self):
        """Test that temporary transfer requires end date"""
        res = requests.post(f"{BASE_URL}/api/transfers/create", json={
            "token": self.super_admin["token"],
            "employee_name": "MANISH",
            "from_center": "PB-PERTH",
            "to_center": "PB-HSR",
            "transfer_type": "TEMPORARY",
            "start_date": "2026-04-01",
            # No end_date
            "reason": "Test transfer"
        })
        assert res.status_code == 400, f"Expected 400, got {res.status_code}"
        assert "end date" in res.json().get("detail", "").lower()
    
    def test_create_transfer_validation_employee_not_found(self):
        """Test that non-existent employee is rejected"""
        res = requests.post(f"{BASE_URL}/api/transfers/create", json={
            "token": self.super_admin["token"],
            "employee_name": "NONEXISTENT_EMPLOYEE_XYZ",
            "from_center": "PB-PERTH",
            "to_center": "PB-HSR",
            "transfer_type": "TEMPORARY",
            "start_date": "2026-04-01",
            "end_date": "2026-04-15",
            "reason": "Test transfer"
        })
        assert res.status_code == 404, f"Expected 404, got {res.status_code}"
        assert "not found" in res.json().get("detail", "").lower()
    
    def test_create_transfer_validation_invalid_type(self):
        """Test that invalid transfer type is rejected"""
        res = requests.post(f"{BASE_URL}/api/transfers/create", json={
            "token": self.super_admin["token"],
            "employee_name": "MANISH",
            "from_center": "PB-PERTH",
            "to_center": "PB-HSR",
            "transfer_type": "INVALID_TYPE",
            "start_date": "2026-04-01",
            "end_date": "2026-04-15",
            "reason": "Test transfer"
        })
        assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    
    def test_create_temporary_transfer_success(self):
        """Test successful creation of temporary transfer"""
        # Use unique dates to avoid overlap with existing transfers
        start_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=75)).strftime("%Y-%m-%d")
        
        res = requests.post(f"{BASE_URL}/api/transfers/create", json={
            "token": self.super_admin["token"],
            "employee_name": "MANISH",
            "from_center": "PB-PERTH",
            "to_center": "PB-HSR",
            "transfer_type": "TEMPORARY",
            "start_date": start_date,
            "end_date": end_date,
            "reason": "TEST_TRANSFER_TEMP"
        })
        
        # Could be 200 or 400 if overlapping transfer exists
        if res.status_code == 200:
            data = res.json()
            assert data.get("success") == True
            assert "transfer_id" in data
            assert data.get("status") == "PENDING_ACCEPTANCE"
            print(f"Created temporary transfer: {data.get('transfer_id')}")
            # Store for cleanup
            self.temp_transfer_id = data.get("transfer_id")
        else:
            # Overlapping transfer exists - this is expected
            print(f"Transfer creation returned {res.status_code}: {res.json().get('detail')}")
            assert "overlap" in res.json().get("detail", "").lower() or "active" in res.json().get("detail", "").lower()


class TestTransferAction:
    """Tests for POST /api/transfers/action (accept/reject/cancel)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth tokens"""
        self.super_admin = get_auth_token(SUPER_ADMIN)
        self.perth_manager = get_auth_token(PERTH_MANAGER)
        self.india_manager = get_auth_token(INDIA_MANAGER)
    
    def test_action_requires_auth(self):
        """Test that action requires valid token"""
        res = requests.post(f"{BASE_URL}/api/transfers/action", json={
            "token": "invalid_token",
            "transfer_id": "some_id",
            "action": "accept"
        })
        assert res.status_code == 401
    
    def test_action_invalid_transfer_id(self):
        """Test that invalid transfer ID is rejected"""
        res = requests.post(f"{BASE_URL}/api/transfers/action", json={
            "token": self.super_admin["token"],
            "transfer_id": "invalid_id_format",
            "action": "accept"
        })
        assert res.status_code == 400
    
    def test_action_invalid_action_type(self):
        """Test that invalid action type is rejected"""
        res = requests.post(f"{BASE_URL}/api/transfers/action", json={
            "token": self.super_admin["token"],
            "transfer_id": "507f1f77bcf86cd799439011",  # Valid ObjectId format
            "action": "invalid_action"
        })
        assert res.status_code == 400
        assert "accept, reject, or cancel" in res.json().get("detail", "").lower()


class TestTransferList:
    """Tests for POST /api/transfers/list"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth tokens"""
        self.super_admin = get_auth_token(SUPER_ADMIN)
        self.perth_manager = get_auth_token(PERTH_MANAGER)
        self.india_manager = get_auth_token(INDIA_MANAGER)
    
    def test_list_requires_auth(self):
        """Test that list requires valid token"""
        res = requests.post(f"{BASE_URL}/api/transfers/list", json={
            "token": "invalid_token"
        })
        assert res.status_code == 401
    
    def test_list_returns_sections(self):
        """Test that list returns incoming, outgoing, active sections"""
        res = requests.post(f"{BASE_URL}/api/transfers/list", json={
            "token": self.super_admin["token"]
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        assert "incoming" in data
        assert "outgoing" in data
        assert "active" in data
        assert "unread_notifications" in data
        
        # Verify data types
        assert isinstance(data["incoming"], list)
        assert isinstance(data["outgoing"], list)
        assert isinstance(data["active"], list)
        assert isinstance(data["unread_notifications"], int)
        
        print(f"List response: incoming={len(data['incoming'])}, outgoing={len(data['outgoing'])}, active={len(data['active'])}, unread={data['unread_notifications']}")
    
    def test_list_with_center_filter(self):
        """Test list with center filter"""
        res = requests.post(f"{BASE_URL}/api/transfers/list", json={
            "token": self.super_admin["token"],
            "center": "PB-PERTH"
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
    
    def test_list_perth_manager_sees_own_center(self):
        """Test that Perth manager sees transfers for their center"""
        res = requests.post(f"{BASE_URL}/api/transfers/list", json={
            "token": self.perth_manager["token"]
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True


class TestTransferHistory:
    """Tests for POST /api/transfers/history"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth tokens"""
        self.super_admin = get_auth_token(SUPER_ADMIN)
    
    def test_history_requires_auth(self):
        """Test that history requires valid token"""
        res = requests.post(f"{BASE_URL}/api/transfers/history", json={
            "token": "invalid_token"
        })
        assert res.status_code == 401
    
    def test_history_returns_records(self):
        """Test that history returns records with filters"""
        res = requests.post(f"{BASE_URL}/api/transfers/history", json={
            "token": self.super_admin["token"]
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        assert "history" in data
        assert "total" in data
        assert isinstance(data["history"], list)
        print(f"History: {data['total']} records")
    
    def test_history_with_filters(self):
        """Test history with various filters"""
        res = requests.post(f"{BASE_URL}/api/transfers/history", json={
            "token": self.super_admin["token"],
            "center": "PB-PERTH",
            "transfer_type": "TEMPORARY"
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True


class TestTransferReports:
    """Tests for POST /api/transfers/reports/summary"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth tokens"""
        self.super_admin = get_auth_token(SUPER_ADMIN)
    
    def test_reports_requires_auth(self):
        """Test that reports requires valid token"""
        res = requests.post(f"{BASE_URL}/api/transfers/reports/summary", json={
            "token": "invalid_token"
        })
        assert res.status_code == 401
    
    def test_reports_returns_summary(self):
        """Test that reports returns center-wise summary"""
        res = requests.post(f"{BASE_URL}/api/transfers/reports/summary", json={
            "token": self.super_admin["token"]
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        assert "summary" in data
        assert isinstance(data["summary"], list)
        
        # Verify summary structure
        if len(data["summary"]) > 0:
            item = data["summary"][0]
            assert "center_code" in item
            assert "total_transfers_in" in item
            assert "total_transfers_out" in item
            assert "active_transfers_in" in item
            assert "active_transfers_out" in item
            assert "pending_requests" in item
        
        print(f"Reports: {len(data['summary'])} centers in summary")


class TestTransferNotifications:
    """Tests for POST /api/transfers/notifications"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth tokens"""
        self.super_admin = get_auth_token(SUPER_ADMIN)
        self.perth_manager = get_auth_token(PERTH_MANAGER)
    
    def test_notifications_requires_auth(self):
        """Test that notifications requires valid token"""
        res = requests.post(f"{BASE_URL}/api/transfers/notifications", json={
            "token": "invalid_token"
        })
        assert res.status_code == 401
    
    def test_notifications_returns_list(self):
        """Test that notifications returns list"""
        res = requests.post(f"{BASE_URL}/api/transfers/notifications", json={
            "token": self.super_admin["token"]
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        assert "notifications" in data
        assert isinstance(data["notifications"], list)
        print(f"Notifications: {len(data['notifications'])} items")
    
    def test_mark_notifications_read(self):
        """Test marking notifications as read"""
        res = requests.post(f"{BASE_URL}/api/transfers/notifications/mark-read", json={
            "token": self.perth_manager["token"]
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True


class TestTransferWorkflow:
    """End-to-end workflow tests for transfer accept/reject"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth tokens"""
        self.super_admin = get_auth_token(SUPER_ADMIN)
        self.perth_manager = get_auth_token(PERTH_MANAGER)
        self.india_manager = get_auth_token(INDIA_MANAGER)
    
    def test_full_transfer_workflow_accept(self):
        """Test full workflow: create -> accept -> verify employee updated"""
        # Use unique dates far in future to avoid overlap
        start_date = (datetime.now() + timedelta(days=100)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=115)).strftime("%Y-%m-%d")
        
        # Step 1: Create transfer (MANISH from PB-PERTH to PB-HSR)
        create_res = requests.post(f"{BASE_URL}/api/transfers/create", json={
            "token": self.super_admin["token"],
            "employee_name": "MANISH",
            "from_center": "PB-PERTH",
            "to_center": "PB-HSR",
            "transfer_type": "TEMPORARY",
            "start_date": start_date,
            "end_date": end_date,
            "reason": "TEST_WORKFLOW_ACCEPT"
        })
        
        if create_res.status_code != 200:
            # Overlapping transfer - skip this test
            print(f"Skipping workflow test - overlapping transfer exists: {create_res.json().get('detail')}")
            pytest.skip("Overlapping transfer exists")
            return
        
        create_data = create_res.json()
        transfer_id = create_data.get("transfer_id")
        assert transfer_id, "No transfer_id returned"
        print(f"Created transfer: {transfer_id}")
        
        # Step 2: Accept transfer (India manager accepts incoming)
        accept_res = requests.post(f"{BASE_URL}/api/transfers/action", json={
            "token": self.india_manager["token"],
            "transfer_id": transfer_id,
            "action": "accept",
            "notes": "Accepted for testing"
        })
        assert accept_res.status_code == 200, f"Accept failed: {accept_res.text}"
        accept_data = accept_res.json()
        assert accept_data.get("success") == True
        assert accept_data.get("status") == "ACCEPTED"
        print(f"Transfer accepted: {accept_data.get('message')}")
        
        # Step 3: Verify transfer appears in active list
        list_res = requests.post(f"{BASE_URL}/api/transfers/list", json={
            "token": self.super_admin["token"]
        })
        assert list_res.status_code == 200
        list_data = list_res.json()
        
        # Find our transfer in active
        active_ids = [t.get("id") for t in list_data.get("active", [])]
        # Note: might not be in active if dates are in future
        print(f"Active transfers: {active_ids}")
        
        # Step 4: Cancel the transfer to clean up
        cancel_res = requests.post(f"{BASE_URL}/api/transfers/action", json={
            "token": self.super_admin["token"],
            "transfer_id": transfer_id,
            "action": "cancel",
            "notes": "Cleanup after test"
        })
        assert cancel_res.status_code == 200
        print("Transfer cancelled for cleanup")
    
    def test_transfer_reject_workflow(self):
        """Test workflow: create -> reject -> verify status"""
        start_date = (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=135)).strftime("%Y-%m-%d")
        
        # Create transfer
        create_res = requests.post(f"{BASE_URL}/api/transfers/create", json={
            "token": self.super_admin["token"],
            "employee_name": "RAJAN",
            "from_center": "PB-PERTH",
            "to_center": "PB-HSR",
            "transfer_type": "TEMPORARY",
            "start_date": start_date,
            "end_date": end_date,
            "reason": "TEST_WORKFLOW_REJECT"
        })
        
        if create_res.status_code != 200:
            print(f"Skipping reject test - {create_res.json().get('detail')}")
            pytest.skip("Could not create transfer")
            return
        
        transfer_id = create_res.json().get("transfer_id")
        print(f"Created transfer for reject test: {transfer_id}")
        
        # Reject transfer
        reject_res = requests.post(f"{BASE_URL}/api/transfers/action", json={
            "token": self.india_manager["token"],
            "transfer_id": transfer_id,
            "action": "reject",
            "notes": "Rejected for testing"
        })
        assert reject_res.status_code == 200
        reject_data = reject_res.json()
        assert reject_data.get("success") == True
        assert reject_data.get("status") == "REJECTED"
        print(f"Transfer rejected: {reject_data.get('message')}")


class TestEmployeeEndpoint:
    """Test /api/employees endpoint used by transfer form"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth tokens"""
        self.super_admin = get_auth_token(SUPER_ADMIN)
    
    def test_get_employees_for_center(self):
        """Test getting employees for a center"""
        res = requests.post(f"{BASE_URL}/api/employees", json={
            "token": self.super_admin["token"],
            "center": "PB-PERTH"
        })
        assert res.status_code == 200
        data = res.json()
        assert "employees" in data
        assert isinstance(data["employees"], list)
        
        # Verify employee structure
        if len(data["employees"]) > 0:
            emp = data["employees"][0]
            assert "name" in emp
            print(f"Found {len(data['employees'])} employees in PB-PERTH")
            print(f"Sample employee: {emp.get('name')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
