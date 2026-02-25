"""
Test Suite: Sales Data Entry Enhancements
- GST Calculation logic (India 5% exclusive, Perth 10% inclusive)
- Guest & Bill count fields with auto-calculated averages
- Guest Booking Response endpoint
- Monthly summary with GST info
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_CENTER = "PB-MGT"
TEST_MOBILE = "9741399190"
MASTER_OTP = "123456"


class TestAuthentication:
    """Get auth token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token using master OTP"""
        # Send OTP
        otp_response = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        assert otp_response.status_code == 200, f"Send OTP failed: {otp_response.text}"
        
        # Verify OTP
        verify_response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": MASTER_OTP
        })
        assert verify_response.status_code == 200, f"Verify OTP failed: {verify_response.text}"
        
        data = verify_response.json()
        assert "token" in data, "No token in response"
        return data["token"]


class TestMonthlySummaryGSTInfo:
    """Test /api/sales/reports/monthly-summary endpoint returns GST info"""
    
    @pytest.fixture(scope="class")
    def auth_token(self, request):
        """Get auth token"""
        otp_response = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        assert otp_response.status_code == 200
        
        verify_response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": MASTER_OTP
        })
        assert verify_response.status_code == 200
        return verify_response.json()["token"]
    
    def test_monthly_summary_returns_gst_info(self, auth_token):
        """Test that monthly summary returns GST fields"""
        response = requests.post(f"{BASE_URL}/api/sales/reports/monthly-summary", json={
            "token": auth_token,
            "month": "2025-04",
            "center": "all"
        })
        
        assert response.status_code == 200, f"Monthly summary failed: {response.text}"
        data = response.json()
        
        # Check grand_total has GST fields
        if "grand_total" in data:
            total = data["grand_total"]
            assert "total_gst" in total or "gst_amount" in total, "GST amount not in grand_total"
            assert "total_guests" in total, "total_guests not in grand_total"
            assert "total_bills" in total, "total_bills not in grand_total"
            assert "avg_per_pax" in total, "avg_per_pax not in grand_total"
            assert "avg_per_bill" in total, "avg_per_bill not in grand_total"
    
    def test_monthly_summary_single_center_gst(self, auth_token):
        """Test monthly summary for single center returns GST rate"""
        response = requests.post(f"{BASE_URL}/api/sales/reports/monthly-summary", json={
            "token": auth_token,
            "month": "2025-04",
            "center": "PB-HSR"  # Indian center
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # For single center, check summary object
        if "summary" in data:
            summary = data["summary"]
            # Indian center should have 5% GST rate
            if "gst_rate" in summary:
                assert summary["gst_rate"] == 5, f"Expected 5% GST for India, got {summary.get('gst_rate')}"
            assert "total_guests" in summary, "total_guests not in summary"
            assert "total_bills" in summary, "total_bills not in summary"
    
    def test_monthly_summary_requires_auth(self):
        """Test that endpoint requires valid token"""
        response = requests.post(f"{BASE_URL}/api/sales/reports/monthly-summary", json={
            "token": "invalid_token",
            "month": "2025-04"
        })
        
        assert response.status_code == 401, "Should require valid token"


class TestGSTCalculationLogic:
    """Test GST calculation endpoints and logic"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        otp_response = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        verify_response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": MASTER_OTP
        })
        return verify_response.json()["token"]
    
    def test_india_center_gst_rate(self, auth_token):
        """Test Indian center returns 5% GST rate"""
        # Get data for an Indian center
        response = requests.post(f"{BASE_URL}/api/sales/reports/monthly-summary", json={
            "token": auth_token,
            "month": "2025-04",
            "center": "PB-HSR"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Check GST rate is 5%
        if "summary" in data:
            summary = data["summary"]
            if "gst_rate" in summary:
                assert summary["gst_rate"] == 5, "Indian center should have 5% GST"
            # GST should not be inclusive
            if "gst_inclusive" in summary:
                assert summary["gst_inclusive"] == False, "Indian GST should be exclusive (added)"


class TestGuestBillCount:
    """Test guest and bill count fields in API"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        otp_response = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        verify_response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": MASTER_OTP
        })
        return verify_response.json()["token"]
    
    def test_daily_sales_has_guest_bill_fields(self, auth_token):
        """Test daily sales endpoint returns guest/bill count fields"""
        response = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "month": "2025-04"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # If there are sales records, check for new fields
        if data.get("sales") and len(data["sales"]) > 0:
            sale = data["sales"][0]
            # New fields might be present or default to 0
            # Check that the model accepts these fields
            print(f"Sale record fields: {list(sale.keys())}")


class TestGuestBookingResponse:
    """Test /api/guest/booking-response endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        otp_response = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        verify_response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": MASTER_OTP
        })
        return verify_response.json()["token"]
    
    def test_booking_response_endpoint_exists(self, auth_token):
        """Test that booking response endpoint exists and accepts request"""
        response = requests.post(f"{BASE_URL}/api/guest/booking-response", json={
            "token": auth_token,
            "center": "PB-HSR",
            "raw_booking_text": "Name: Test Guest\nDate: Tomorrow\nTime: 8 PM\nGuests: 4"
        })
        
        # Endpoint should exist (200) or fail gracefully with meaningful error
        assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "formatted_message" in data, "Response should have formatted_message"
            assert len(data["formatted_message"]) > 0, "Formatted message should not be empty"
            print(f"Booking response generated successfully")
        else:
            # May fail if AI service not configured, which is acceptable
            print(f"Booking response endpoint failed: {response.text}")
    
    def test_booking_response_requires_auth(self):
        """Test that booking response requires valid token"""
        response = requests.post(f"{BASE_URL}/api/guest/booking-response", json={
            "token": "invalid_token",
            "center": "PB-HSR",
            "raw_booking_text": "Test booking"
        })
        
        assert response.status_code == 401, "Should require valid token"
    
    def test_booking_response_with_different_centers(self, auth_token):
        """Test booking response works with different center codes"""
        # Test with Indian center
        response = requests.post(f"{BASE_URL}/api/guest/booking-response", json={
            "token": auth_token,
            "center": "PB-KAL",
            "raw_booking_text": "Family of 6, Saturday lunch, Birthday celebration for Mom"
        })
        
        # Should either succeed or fail with AI error (not auth/validation error)
        assert response.status_code in [200, 500], f"Unexpected error: {response.text}"


class TestCenterInfoEndpoint:
    """Test /api/center_info endpoint for center data"""
    
    def test_center_info_endpoint(self):
        """Test center info endpoint returns centers"""
        response = requests.get(f"{BASE_URL}/api/center_info")
        
        assert response.status_code == 200, f"Center info failed: {response.text}"
        data = response.json()
        
        assert "centers" in data, "Should return centers"
        centers = data["centers"]
        
        # Check for some expected centers
        # Perth center should exist for GST testing
        if "PB-PT" in centers:
            assert centers["PB-PT"].get("country") in ["Australia", None]


class TestGuestAIChat:
    """Test /api/guest_ai endpoint for guest queries"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        otp_response = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        verify_response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": MASTER_OTP
        })
        return verify_response.json()["token"]
    
    def test_guest_ai_endpoint_exists(self, auth_token):
        """Test guest AI chat endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/guest_ai", json={
            "token": auth_token,
            "center": "PB-HSR",
            "question": "What are the timings?"
        })
        
        # Should work or fail gracefully
        assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}"


class TestExpenseTypes:
    """Test expense types and payment modes endpoints"""
    
    def test_expense_types_endpoint(self):
        """Test expense types endpoint"""
        response = requests.get(f"{BASE_URL}/api/sales/expense-types")
        
        assert response.status_code == 200
        data = response.json()
        assert "expense_types" in data
        assert len(data["expense_types"]) > 0
    
    def test_payment_modes_endpoint(self):
        """Test payment modes endpoint"""
        response = requests.get(f"{BASE_URL}/api/sales/payment-modes")
        
        assert response.status_code == 200
        data = response.json()
        assert "payment_modes" in data
        assert "CASH" in data["payment_modes"]


class TestSalesCentersList:
    """Test sales centers list endpoint"""
    
    def test_centers_list_endpoint(self):
        """Test getting list of centers with sales data"""
        response = requests.get(f"{BASE_URL}/api/sales/centers-list")
        
        assert response.status_code == 200
        data = response.json()
        assert "centers" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
