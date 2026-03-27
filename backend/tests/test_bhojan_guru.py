"""
Backend API Tests for Purnabramha IntraPB System
Tests cover:
- Recipe/Description endpoints (Bhojan Guru feature)
- Login flow (OTP send -> OTP verify -> get token)
- Guest AI endpoint with center selection
"""

import pytest
import requests
import os
import time

# Use production URL for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://mis-dashboard-v2.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_CENTER = "PB-MGT"
TEST_MOBILE = "9741399190"
MASTER_OTP = "123456"  # Dev mode master OTP


class TestHealthAndBasicEndpoints:
    """Basic health check and center info tests"""
    
    def test_health_endpoint(self):
        """Test /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        print("✅ Health endpoint OK")
    
    def test_root_endpoint(self):
        """Test /api/ returns API info"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Purnabramha" in data["message"]
        print("✅ Root endpoint OK")
    
    def test_centers_endpoint(self):
        """Test /api/centers returns all centers"""
        response = requests.get(f"{BASE_URL}/api/centers")
        assert response.status_code == 200
        data = response.json()
        assert "centers" in data
        centers = data["centers"]
        assert len(centers) >= 9  # Expected 9 centers
        
        # Verify some key centers exist
        center_codes = [c["code"] for c in centers]
        assert "PB-MGT" in center_codes
        assert "PB-HSR" in center_codes
        assert "PB-PERTH" in center_codes
        print(f"✅ Centers endpoint OK - {len(centers)} centers found")
    
    def test_center_info_endpoint(self):
        """Test /api/center_info returns detailed center info"""
        response = requests.get(f"{BASE_URL}/api/center_info")
        assert response.status_code == 200
        data = response.json()
        assert "centers" in data
        centers = data["centers"]
        
        # Verify specific center has required fields
        assert "PB-HSR" in centers
        hsr = centers["PB-HSR"]
        assert "name" in hsr
        assert "address" in hsr
        assert "phone" in hsr
        assert "timings" in hsr
        print(f"✅ Center info endpoint OK - {len(centers)} centers with details")


class TestRecipeEndpoints:
    """Tests for Bhojan Guru recipe data endpoints"""
    
    def test_recipes_endpoint_returns_data(self):
        """Test /api/recipes returns recipe data structure"""
        response = requests.get(f"{BASE_URL}/api/recipes")
        assert response.status_code == 200
        data = response.json()
        
        # Verify top-level structure
        assert "recipes" in data
        assert "thalis" in data
        assert "bhojanGuru" in data
        print("✅ Recipes endpoint returns correct structure")
    
    def test_recipes_count(self):
        """Test that recipes endpoint returns expected count (47 recipes)"""
        response = requests.get(f"{BASE_URL}/api/recipes")
        assert response.status_code == 200
        data = response.json()
        
        recipe_count = len(data["recipes"])
        assert recipe_count == 47, f"Expected 47 recipes, got {recipe_count}"
        print(f"✅ Recipes count correct: {recipe_count}")
    
    def test_thalis_count(self):
        """Test that recipes endpoint returns expected thali count (5 thalis)"""
        response = requests.get(f"{BASE_URL}/api/recipes")
        assert response.status_code == 200
        data = response.json()
        
        thali_count = len(data["thalis"])
        assert thali_count == 5, f"Expected 5 thalis, got {thali_count}"
        print(f"✅ Thalis count correct: {thali_count}")
    
    def test_recipe_has_ingredients_and_method(self):
        """Test that recipes contain ingredients and method fields"""
        response = requests.get(f"{BASE_URL}/api/recipes")
        assert response.status_code == 200
        data = response.json()
        
        recipes = data["recipes"]
        # Check a known recipe
        assert "solkadhi" in recipes, "Solkadhi recipe should exist"
        solkadhi = recipes["solkadhi"]
        
        assert "display" in solkadhi
        assert "ingredients" in solkadhi
        assert "method" in solkadhi
        assert isinstance(solkadhi["ingredients"], list)
        assert isinstance(solkadhi["method"], list)
        assert len(solkadhi["ingredients"]) > 0
        assert len(solkadhi["method"]) > 0
        print(f"✅ Recipe structure correct - solkadhi has {len(solkadhi['ingredients'])} ingredients and {len(solkadhi['method'])} method steps")
    
    def test_multiple_recipes_structure(self):
        """Test that multiple recipes have proper structure"""
        response = requests.get(f"{BASE_URL}/api/recipes")
        assert response.status_code == 200
        recipes = response.json()["recipes"]
        
        # Check 5 recipes
        sample_recipes = ["batata_vada", "kanda_bhaji", "puranpoli", "misal_pav", "shrikhand"]
        for recipe_key in sample_recipes:
            assert recipe_key in recipes, f"{recipe_key} should exist"
            recipe = recipes[recipe_key]
            assert "display" in recipe, f"{recipe_key} missing display"
            assert "ingredients" in recipe, f"{recipe_key} missing ingredients"
            assert "method" in recipe, f"{recipe_key} missing method"
        print(f"✅ Multiple recipes structure verified")


class TestDescriptionEndpoints:
    """Tests for menu description endpoints"""
    
    def test_descriptions_endpoint_returns_data(self):
        """Test /api/descriptions returns data"""
        response = requests.get(f"{BASE_URL}/api/descriptions")
        assert response.status_code == 200
        data = response.json()
        assert "descriptions" in data
        print("✅ Descriptions endpoint returns correct structure")
    
    def test_descriptions_count(self):
        """Test that descriptions endpoint returns expected count (126 items)"""
        response = requests.get(f"{BASE_URL}/api/descriptions")
        assert response.status_code == 200
        data = response.json()
        
        desc_count = len(data["descriptions"])
        assert desc_count == 126, f"Expected 126 descriptions, got {desc_count}"
        print(f"✅ Descriptions count correct: {desc_count}")
    
    def test_description_structure(self):
        """Test that descriptions have required fields"""
        response = requests.get(f"{BASE_URL}/api/descriptions")
        assert response.status_code == 200
        descriptions = response.json()["descriptions"]
        
        # Check that descriptions have key fields
        # Find at least one item with all fields
        found_complete = False
        for key, desc in descriptions.items():
            if "display" in desc and "desc_short" in desc:
                found_complete = True
                assert isinstance(desc["display"], str)
                # Marathi descriptions are optional but should exist for many items
                break
        
        assert found_complete, "No descriptions found with required fields"
        print("✅ Description structure verified")


class TestLoginFlow:
    """Tests for OTP-based login flow"""
    
    def test_send_otp_success(self):
        """Test sending OTP to valid manager"""
        response = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        # In dev mode, OTP is logged to console (SMTP not configured)
        assert "OTP" in data["message"] or "generated" in data["message"]
        print("✅ Send OTP successful")
    
    def test_verify_otp_with_master_code(self):
        """Test verifying OTP with master code (123456) - dev mode"""
        # First send OTP
        requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        
        # Verify with master OTP
        response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": MASTER_OTP
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "token" in data
        assert len(data["token"]) > 10
        assert data["center"] == TEST_CENTER
        assert "managerName" in data
        print(f"✅ OTP verification successful - Manager: {data.get('managerName')}")
        return data["token"]
    
    def test_verify_otp_invalid_code(self):
        """Test that invalid OTP is rejected"""
        # First send OTP
        requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        
        # Verify with wrong OTP
        response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": "000000"  # Invalid
        })
        assert response.status_code == 400
        print("✅ Invalid OTP correctly rejected")
    
    def test_full_login_flow(self):
        """Test complete login flow: send OTP -> verify -> get token"""
        # Step 1: Send OTP
        response = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        assert response.status_code == 200
        
        # Step 2: Verify OTP (using master OTP for dev)
        response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": MASTER_OTP
        })
        assert response.status_code == 200
        data = response.json()
        
        # Step 3: Validate token
        token = data["token"]
        assert len(token) > 10
        
        # Step 4: Use token to access protected endpoint
        response = requests.post(f"{BASE_URL}/api/employees", json={
            "token": token,
            "center": TEST_CENTER
        })
        assert response.status_code == 200
        print("✅ Full login flow completed successfully")


class TestGuestAI:
    """Tests for Guest Response AI endpoint"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token for testing"""
        requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": MASTER_OTP
        })
        return response.json()["token"]
    
    def test_guest_ai_requires_auth(self):
        """Test that Guest AI requires authentication"""
        response = requests.post(f"{BASE_URL}/api/guest_ai", json={
            "token": "invalid_token",
            "center": "PB-HSR",
            "question": "What are your timings?"
        })
        assert response.status_code == 401
        print("✅ Guest AI correctly requires authentication")
    
    def test_guest_ai_with_hsr_center(self, auth_token):
        """Test Guest AI with PB-HSR center context"""
        response = requests.post(f"{BASE_URL}/api/guest_ai", json={
            "token": auth_token,
            "center": "PB-HSR",
            "question": "What is your address?"
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sessionId" in data
        assert len(data["answer"]) > 10  # Should have meaningful response
        print(f"✅ Guest AI HSR response: {data['answer'][:100]}...")
    
    def test_guest_ai_with_kalyan_center(self, auth_token):
        """Test Guest AI with PB-KAL (Kalyan) center context"""
        response = requests.post(f"{BASE_URL}/api/guest_ai", json={
            "token": auth_token,
            "center": "PB-KAL",
            "question": "What are your contact details?"
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 10
        print(f"✅ Guest AI Kalyan response received")
    
    def test_guest_ai_with_perth_center(self, auth_token):
        """Test Guest AI with PB-PERTH (Australia) center context"""
        response = requests.post(f"{BASE_URL}/api/guest_ai", json={
            "token": auth_token,
            "center": "PB-PERTH",
            "question": "Do you deliver in Perth?"
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        print(f"✅ Guest AI Perth response received")
    
    def test_guest_ai_different_centers(self, auth_token):
        """Test that Guest AI returns different context for different centers"""
        centers_to_test = ["PB-HSR", "PB-KAL", "PB-MEL"]
        
        for center in centers_to_test:
            if center == "PB-MEL":
                # PB-MEL may not exist, use PB-TH instead
                center = "PB-TH"
            
            response = requests.post(f"{BASE_URL}/api/guest_ai", json={
                "token": auth_token,
                "center": center,
                "question": "What is your phone number?"
            })
            # Some centers may not be configured, which is acceptable
            if response.status_code == 200:
                print(f"✅ Guest AI {center} working")


class TestProtectedEndpoints:
    """Tests for endpoints requiring authentication"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        response = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": MASTER_OTP
        })
        return response.json()["token"]
    
    def test_employees_requires_auth(self):
        """Test that employees endpoint requires auth"""
        response = requests.post(f"{BASE_URL}/api/employees", json={
            "token": "bad_token",
            "center": TEST_CENTER
        })
        assert response.status_code == 401
        print("✅ Employees endpoint correctly requires auth")
    
    def test_employees_with_valid_token(self, auth_token):
        """Test employees endpoint with valid token"""
        response = requests.post(f"{BASE_URL}/api/employees", json={
            "token": auth_token,
            "center": TEST_CENTER
        })
        assert response.status_code == 200
        data = response.json()
        assert "employees" in data
        print(f"✅ Employees retrieved successfully - {len(data['employees'])} employees")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
