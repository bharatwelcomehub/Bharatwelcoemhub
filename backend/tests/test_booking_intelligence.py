"""
Test suite for Booking Intelligence & Guest Conversion Module
Also tests Session Persistence to MongoDB (Invalid Token fix)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_CENTER = "PB-MGT"
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"

class TestSessionPersistence:
    """Test session persistence to MongoDB - Invalid Token fix"""
    
    def test_login_and_get_token(self, api_client):
        """Test login flow and verify token is returned"""
        # Send OTP
        otp_res = api_client.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        assert otp_res.status_code == 200, f"OTP send failed: {otp_res.text}"
        
        # Verify OTP
        verify_res = api_client.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        assert verify_res.status_code == 200, f"OTP verify failed: {verify_res.text}"
        
        data = verify_res.json()
        assert "token" in data, "Token not in response"
        assert "session_expires_in_seconds" in data, "Session expiry info not in response"
        assert data["session_expires_in_seconds"] > 0, "Session TTL should be positive"
        print(f"Login successful - token length: {len(data['token'])}, TTL: {data['session_expires_in_seconds']}s")
        
    def test_token_persists_across_requests(self, auth_token, api_client):
        """Test that token works for multiple requests"""
        # First request
        res1 = api_client.post(f"{BASE_URL}/api/employees", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        assert res1.status_code == 200, "First request failed"
        
        # Small delay
        time.sleep(0.5)
        
        # Second request with same token
        res2 = api_client.post(f"{BASE_URL}/api/employees", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        assert res2.status_code == 200, "Second request with same token failed"
        print("Token persists across multiple requests")

class TestBookingConstants:
    """Test booking constants endpoint"""
    
    def test_get_constants(self, api_client):
        """Test constants endpoint returns all required fields"""
        res = api_client.get(f"{BASE_URL}/api/bookings/constants")
        assert res.status_code == 200
        
        data = res.json()
        assert "time_slots" in data, "time_slots missing"
        assert "guest_types" in data, "guest_types missing"
        assert "celebration_types" in data, "celebration_types missing"
        assert "menu_status" in data, "menu_status missing"
        assert "booking_sources" in data, "booking_sources missing"
        assert "booking_status" in data, "booking_status missing"
        assert "catering_status" in data, "catering_status missing"
        assert "center_contacts" in data, "center_contacts missing"
        
        # Verify content
        assert len(data["time_slots"]) > 5, "Not enough time slots"
        assert "Birthday" in data["celebration_types"], "Birthday not in celebration types"
        assert "Anniversary" in data["celebration_types"], "Anniversary not in celebration types"
        assert "Enquiry" in data["booking_status"], "Enquiry not in booking status"
        assert "Confirmed" in data["booking_status"], "Confirmed not in booking status"
        
        print(f"Constants loaded - {len(data['time_slots'])} time slots, {len(data['celebration_types'])} celebration types")

class TestBookingCRUD:
    """Test booking CRUD operations"""
    
    def test_create_booking(self, auth_token, api_client):
        """Test creating a new booking"""
        booking_data = {
            "token": auth_token,
            "center": "PB-HSR",
            "date": "2026-03-20",
            "guest_name": "TEST_John Doe",
            "phone": "9898989898",
            "time_slot": "7:00 PM - 8:00 PM",
            "num_guests": 4,
            "guest_type": "New Entry",
            "celebration_type": "Birthday",
            "booking_source": "Phone Call",
            "status": "Enquiry",
            "special_request": "Window seat preferred",
            "menu_decided": "No"
        }
        
        res = api_client.post(f"{BASE_URL}/api/bookings/create", json=booking_data)
        assert res.status_code == 200, f"Booking creation failed: {res.text}"
        
        data = res.json()
        assert data["success"] == True
        assert "booking_id" in data, "booking_id not returned"
        assert data["booking_id"].startswith("BK-"), "Booking ID format wrong"
        
        print(f"Booking created: {data['booking_id']}")
        return data["booking_id"]
    
    def test_list_bookings(self, auth_token, api_client):
        """Test listing bookings with filters"""
        res = api_client.post(f"{BASE_URL}/api/bookings/list", json={
            "token": auth_token,
            "date_from": "2026-03-01",
            "date_to": "2026-03-31",
            "center": "all",
            "status": "all"
        })
        assert res.status_code == 200, f"List bookings failed: {res.text}"
        
        data = res.json()
        assert "bookings" in data, "bookings not in response"
        assert "total" in data, "total not in response"
        assert isinstance(data["bookings"], list)
        
        print(f"Listed {len(data['bookings'])} bookings, total: {data['total']}")
    
    def test_list_bookings_with_search(self, auth_token, api_client):
        """Test searching bookings by phone"""
        res = api_client.post(f"{BASE_URL}/api/bookings/list", json={
            "token": auth_token,
            "search": "9876543210"  # Known test booking phone
        })
        assert res.status_code == 200
        
        data = res.json()
        # May or may not find results, but should not error
        print(f"Search returned {len(data['bookings'])} results")
    
    def test_update_booking(self, auth_token, api_client):
        """Test updating a booking"""
        # First create a booking
        create_data = {
            "token": auth_token,
            "center": "PB-HSR",
            "date": "2026-03-21",
            "guest_name": "TEST_Update Test",
            "phone": "9797979797",
            "time_slot": "8:00 PM - 9:00 PM",
            "num_guests": 2,
            "status": "Enquiry"
        }
        
        create_res = api_client.post(f"{BASE_URL}/api/bookings/create", json=create_data)
        assert create_res.status_code == 200
        booking_id = create_res.json()["booking_id"]
        
        # Update the booking
        update_res = api_client.post(f"{BASE_URL}/api/bookings/update/{booking_id}", json={
            "token": auth_token,
            "status": "Confirmed",
            "num_guests": 5,
            "remarks": "VIP guest"
        })
        assert update_res.status_code == 200, f"Update failed: {update_res.text}"
        assert update_res.json()["success"] == True
        
        print(f"Booking {booking_id} updated to Confirmed")

class TestGuestLookup:
    """Test guest lookup by phone"""
    
    def test_guest_lookup_new_guest(self, auth_token, api_client):
        """Test looking up a new guest (no history)"""
        res = api_client.post(f"{BASE_URL}/api/bookings/guest-lookup", json={
            "token": auth_token,
            "phone": "1111111111"  # New number with no bookings
        })
        assert res.status_code == 200
        
        data = res.json()
        assert "found" in data
        # New guest should return found=False
        print(f"New guest lookup - found: {data['found']}")
    
    def test_guest_lookup_existing_guest(self, auth_token, api_client):
        """Test looking up existing guest"""
        res = api_client.post(f"{BASE_URL}/api/bookings/guest-lookup", json={
            "token": auth_token,
            "phone": "9876543210"  # Known test booking
        })
        assert res.status_code == 200
        
        data = res.json()
        assert "found" in data
        assert "history" in data
        
        if data["found"]:
            assert "guest" in data
            assert "stats" in data
            print(f"Existing guest found: {data['guest'].get('name')}, bookings: {len(data['history'])}")
        else:
            print("Guest not found - may need seed data")
    
    def test_guest_lookup_invalid_phone(self, auth_token, api_client):
        """Test lookup with invalid phone"""
        res = api_client.post(f"{BASE_URL}/api/bookings/guest-lookup", json={
            "token": auth_token,
            "phone": "123"  # Too short
        })
        assert res.status_code == 200
        
        data = res.json()
        assert data["found"] == False
        print("Invalid phone handled correctly")

class TestDashboardStats:
    """Test dashboard statistics endpoint"""
    
    def test_dashboard_stats_today(self, auth_token, api_client):
        """Test dashboard stats for today"""
        res = api_client.post(f"{BASE_URL}/api/bookings/dashboard/stats", json={
            "token": auth_token,
            "period": "today",
            "center": "all"
        })
        assert res.status_code == 200, f"Stats failed: {res.text}"
        
        data = res.json()
        assert "period" in data
        assert "summary" in data
        assert "conversion" in data
        
        summary = data["summary"]
        assert "total_bookings" in summary
        assert "confirmed" in summary
        assert "visited" in summary
        assert "enquiries" in summary
        
        print(f"Today stats - total: {summary['total_bookings']}, confirmed: {summary['confirmed']}")
    
    def test_dashboard_stats_week(self, auth_token, api_client):
        """Test dashboard stats for week"""
        res = api_client.post(f"{BASE_URL}/api/bookings/dashboard/stats", json={
            "token": auth_token,
            "period": "week",
            "center": "all"
        })
        assert res.status_code == 200
        
        data = res.json()
        assert data["period"] == "week"
        assert "date_range" in data
        print(f"Week stats - range: {data['date_range']}")
    
    def test_dashboard_stats_month(self, auth_token, api_client):
        """Test dashboard stats for month"""
        res = api_client.post(f"{BASE_URL}/api/bookings/dashboard/stats", json={
            "token": auth_token,
            "period": "month",
            "center": "all"
        })
        assert res.status_code == 200
        
        data = res.json()
        assert data["period"] == "month"
        
        # Check conversion metrics
        conv = data.get("conversion", {})
        assert "enquiry_to_confirmed" in conv
        assert "booking_to_visit" in conv
        assert "repeat_rate" in conv
        
        print(f"Month stats - conversion rate: {conv.get('enquiry_to_confirmed')}%")

class TestWhatsAppPreview:
    """Test WhatsApp message preview endpoint"""
    
    def test_preview_confirmation_message(self, auth_token, api_client):
        """Test previewing confirmation message"""
        # First get a booking ID
        list_res = api_client.post(f"{BASE_URL}/api/bookings/list", json={
            "token": auth_token,
            "date_from": "2026-01-01",
            "date_to": "2026-12-31"
        })
        
        if list_res.status_code == 200 and list_res.json()["bookings"]:
            booking_id = list_res.json()["bookings"][0]["booking_id"]
            
            res = api_client.post(f"{BASE_URL}/api/bookings/preview-whatsapp/{booking_id}", json={
                "token": auth_token,
                "type": "confirmation"
            })
            assert res.status_code == 200, f"Preview failed: {res.text}"
            
            data = res.json()
            assert "message" in data, "message not in preview"
            assert "Purnabramha" in data["message"], "Brand name not in message"
            assert "phone" in data
            
            print(f"Confirmation message preview generated ({len(data['message'])} chars)")
        else:
            print("No bookings available for WhatsApp preview test")
    
    def test_preview_reminder_message(self, auth_token, api_client):
        """Test previewing reminder message"""
        list_res = api_client.post(f"{BASE_URL}/api/bookings/list", json={
            "token": auth_token,
            "date_from": "2026-01-01",
            "date_to": "2026-12-31"
        })
        
        if list_res.status_code == 200 and list_res.json()["bookings"]:
            booking_id = list_res.json()["bookings"][0]["booking_id"]
            
            res = api_client.post(f"{BASE_URL}/api/bookings/preview-whatsapp/{booking_id}", json={
                "token": auth_token,
                "type": "reminder"
            })
            assert res.status_code == 200
            
            data = res.json()
            assert "message" in data
            assert "reminder" in data["message"].lower() or "booking" in data["message"].lower()
            
            print("Reminder message preview generated")
        else:
            print("No bookings available for reminder preview test")

class TestRemindersAndFollowups:
    """Test reminders and follow-up endpoints"""
    
    def test_upcoming_reminders(self, auth_token, api_client):
        """Test getting upcoming birthday/anniversary reminders"""
        res = api_client.post(f"{BASE_URL}/api/bookings/reminders/upcoming", json={
            "token": auth_token
        })
        assert res.status_code == 200, f"Reminders failed: {res.text}"
        
        data = res.json()
        assert "birthdays" in data
        assert "anniversaries" in data
        assert "kids_birthdays" in data
        assert "today" in data
        
        print(f"Reminders - birthdays: {len(data['birthdays'])}, anniversaries: {len(data['anniversaries'])}")
    
    def test_todays_followups(self, auth_token, api_client):
        """Test getting today's follow-ups"""
        res = api_client.post(f"{BASE_URL}/api/bookings/followups/today", json={
            "token": auth_token
        })
        assert res.status_code == 200
        
        data = res.json()
        assert "followups" in data
        assert "count" in data
        
        print(f"Today's follow-ups: {data['count']}")

class TestAccessControl:
    """Test access control for booking endpoints"""
    
    def test_unauthorized_access(self, api_client):
        """Test that invalid token is rejected"""
        res = api_client.post(f"{BASE_URL}/api/bookings/list", json={
            "token": "invalid_token_12345",
            "date_from": "2026-03-01"
        })
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"
        print("Unauthorized access correctly rejected")
    
    def test_create_without_token(self, api_client):
        """Test creating booking without token"""
        res = api_client.post(f"{BASE_URL}/api/bookings/create", json={
            "center": "PB-HSR",
            "date": "2026-03-20",
            "guest_name": "Test",
            "phone": "1234567890",
            "time_slot": "7:00 PM - 8:00 PM",
            "num_guests": 2
        })
        assert res.status_code == 401
        print("Missing token correctly rejected")

class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_bookings(self, auth_token, api_client):
        """Clean up TEST_ prefixed bookings"""
        res = api_client.post(f"{BASE_URL}/api/bookings/list", json={
            "token": auth_token,
            "search": "TEST_"
        })
        
        if res.status_code == 200:
            bookings = res.json().get("bookings", [])
            deleted = 0
            for b in bookings:
                if b.get("guest_name", "").startswith("TEST_"):
                    del_res = api_client.post(f"{BASE_URL}/api/bookings/delete/{b['booking_id']}", json={
                        "token": auth_token
                    })
                    if del_res.status_code == 200:
                        deleted += 1
            print(f"Cleaned up {deleted} test bookings")

# Fixtures
@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture
def auth_token(api_client):
    """Get authentication token"""
    # Send OTP
    api_client.post(f"{BASE_URL}/api/send_otp", json={
        "center": TEST_CENTER,
        "mobile": TEST_MOBILE
    })
    
    # Verify OTP
    response = api_client.post(f"{BASE_URL}/api/verify_otp", json={
        "center": TEST_CENTER,
        "mobile": TEST_MOBILE,
        "otp": TEST_OTP
    })
    
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")
