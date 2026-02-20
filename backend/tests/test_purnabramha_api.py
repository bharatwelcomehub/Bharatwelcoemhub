"""
Purnabramha Restaurant API Tests
Tests for Menu, Admin, Locations, and Videos APIs
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPublicEndpoints:
    """Test public endpoints (no auth required)"""
    
    def test_get_menu_returns_items(self):
        """Test that menu endpoint returns items"""
        response = requests.get(f"{BASE_URL}/api/menu")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Menu should have items"
        print(f"✓ Menu returned {len(data)} items")
    
    def test_menu_item_structure(self):
        """Test that menu items have required fields"""
        response = requests.get(f"{BASE_URL}/api/menu")
        assert response.status_code == 200
        data = response.json()
        item = data[0]
        
        # Check required fields
        required_fields = ['id', 'name', 'description', 'category', 'price_inr', 'is_veg', 'is_available']
        for field in required_fields:
            assert field in item, f"Missing field: {field}"
        
        # Check price_aud exists (may be null for India-only items)
        assert 'price_aud' in item, "Missing field: price_aud"
        print(f"✓ Menu item has all required fields")
    
    def test_menu_has_country_based_pricing(self):
        """Test that menu items have both INR and AUD pricing"""
        response = requests.get(f"{BASE_URL}/api/menu")
        assert response.status_code == 200
        data = response.json()
        
        # Check that some items have INR pricing
        inr_items = [item for item in data if item.get('price_inr') and item['price_inr'] > 0]
        assert len(inr_items) > 0, "Should have items with INR pricing"
        
        # Check that some items have AUD pricing
        aud_items = [item for item in data if item.get('price_aud') and item['price_aud'] > 0]
        assert len(aud_items) > 0, "Should have items with AUD pricing"
        
        print(f"✓ Menu has {len(inr_items)} INR items and {len(aud_items)} AUD items")
    
    def test_get_locations_returns_list(self):
        """Test that locations endpoint returns list of locations"""
        response = requests.get(f"{BASE_URL}/api/locations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 8, "Should have 8 locations"
        print(f"✓ Locations returned {len(data)} locations")
    
    def test_location_structure(self):
        """Test that locations have required fields"""
        response = requests.get(f"{BASE_URL}/api/locations")
        assert response.status_code == 200
        data = response.json()
        location = data[0]
        
        required_fields = ['id', 'name', 'city', 'country', 'address', 'phone', 'is_active']
        for field in required_fields:
            assert field in location, f"Missing field: {field}"
        print(f"✓ Location has all required fields")
    
    def test_locations_has_india_and_australia(self):
        """Test that locations exist in both India and Australia"""
        response = requests.get(f"{BASE_URL}/api/locations")
        assert response.status_code == 200
        data = response.json()
        
        india_locations = [loc for loc in data if loc.get('country') == 'India']
        australia_locations = [loc for loc in data if loc.get('country') == 'Australia']
        
        assert len(india_locations) > 0, "Should have India locations"
        assert len(australia_locations) > 0, "Should have Australia locations"
        print(f"✓ Locations: {len(india_locations)} in India, {len(australia_locations)} in Australia")
    
    def test_get_videos_returns_list(self):
        """Test that videos endpoint returns list"""
        response = requests.get(f"{BASE_URL}/api/videos")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Videos endpoint returned {len(data)} videos")


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_login_success(self):
        """Test admin login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@purnabramha.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data, "Response should have token"
        assert "user" in data, "Response should have user"
        assert data["user"]["email"] == "admin@purnabramha.com"
        print(f"✓ Admin login successful")
    
    def test_login_failure_wrong_password(self):
        """Test login fails with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@purnabramha.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print(f"✓ Login correctly rejected wrong password")
    
    def test_login_failure_wrong_email(self):
        """Test login fails with non-existent email"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "admin123"
        })
        assert response.status_code == 401
        print(f"✓ Login correctly rejected unknown email")


class TestAdminEndpoints:
    """Test admin protected endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@purnabramha.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not get auth token")
    
    def test_admin_menu_requires_auth(self):
        """Test that admin menu endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/menu")
        assert response.status_code == 403 or response.status_code == 401
        print(f"✓ Admin menu correctly requires authentication")
    
    def test_admin_menu_returns_all_items(self, auth_token):
        """Test that admin menu returns all items including unavailable"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/menu", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 173, f"Expected 173 menu items, got {len(data)}"
        print(f"✓ Admin menu returned {len(data)} items")
    
    def test_admin_locations_returns_all(self, auth_token):
        """Test that admin locations returns all locations"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/locations", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 8, f"Expected 8 locations, got {len(data)}"
        print(f"✓ Admin locations returned {len(data)} locations")
    
    def test_admin_create_menu_item(self, auth_token):
        """Test creating a new menu item"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        new_item = {
            "name": "TEST_Test Menu Item",
            "description": "Test description for automated testing",
            "category": "Snacks",
            "price_inr": 99,
            "price_aud": 5.99,
            "is_veg": True,
            "is_available": True
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/menu", headers=headers, json=new_item)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_item["name"]
        assert data["price_inr"] == new_item["price_inr"]
        assert "id" in data
        
        # Store ID for cleanup
        item_id = data["id"]
        
        # Verify item was created via GET
        get_response = requests.get(f"{BASE_URL}/api/admin/menu", headers=headers)
        all_items = get_response.json()
        created_item = next((item for item in all_items if item["id"] == item_id), None)
        assert created_item is not None, "Created item should be retrievable"
        
        # Cleanup - delete the test item
        delete_response = requests.delete(f"{BASE_URL}/api/admin/menu/{item_id}", headers=headers)
        assert delete_response.status_code == 200
        
        print(f"✓ Admin can create and delete menu items")
    
    def test_admin_update_menu_item(self, auth_token):
        """Test updating a menu item"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # First create a test item
        new_item = {
            "name": "TEST_Update Test Item",
            "description": "Original description",
            "category": "Snacks",
            "price_inr": 99,
            "price_aud": 5.99,
            "is_veg": True,
            "is_available": True
        }
        
        create_response = requests.post(f"{BASE_URL}/api/admin/menu", headers=headers, json=new_item)
        item_id = create_response.json()["id"]
        
        # Update the item
        updated_data = {
            "name": "TEST_Updated Item Name",
            "description": "Updated description",
            "category": "Snacks",
            "price_inr": 149,
            "price_aud": 8.99,
            "is_veg": True,
            "is_available": True
        }
        
        update_response = requests.put(f"{BASE_URL}/api/admin/menu/{item_id}", headers=headers, json=updated_data)
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == updated_data["name"]
        assert data["price_inr"] == updated_data["price_inr"]
        
        # Verify update persisted
        get_response = requests.get(f"{BASE_URL}/api/admin/menu", headers=headers)
        all_items = get_response.json()
        updated_item = next((item for item in all_items if item["id"] == item_id), None)
        assert updated_item["name"] == updated_data["name"]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/admin/menu/{item_id}", headers=headers)
        
        print(f"✓ Admin can update menu items")
    
    def test_admin_add_video(self, auth_token):
        """Test adding a video"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        new_video = {
            "title": "TEST_Test Video",
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "description": "Test video description",
            "category": "reels",
            "is_active": True
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/videos", headers=headers, json=new_video)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == new_video["title"]
        assert "id" in data
        
        video_id = data["id"]
        
        # Cleanup
        delete_response = requests.delete(f"{BASE_URL}/api/admin/videos/{video_id}", headers=headers)
        assert delete_response.status_code == 200
        
        print(f"✓ Admin can add and delete videos")


class TestMenuCategories:
    """Test menu category filtering"""
    
    def test_menu_has_expected_categories(self):
        """Test that menu items have expected categories"""
        response = requests.get(f"{BASE_URL}/api/menu")
        assert response.status_code == 200
        data = response.json()
        
        categories = set(item.get('category') for item in data)
        expected_categories = {
            'Balgopal (Kids)', 'Tea & Coffee', 'Drinks', 'Soup & Saar',
            'Snacks', 'Fasting', 'Heavy Brunch', 'Bhakar Combo',
            'Bhaji', 'Dal', 'Rice', 'Roti', 'Sweets', 'Special Thalis', 'Sides'
        }
        
        # Check that all expected categories exist
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"
        
        print(f"✓ Menu has {len(categories)} categories: {categories}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
