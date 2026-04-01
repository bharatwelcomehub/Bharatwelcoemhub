"""
Test suite for dietary tags feature (no_onion_garlic, fasting_friendly)
Tests: Backend API endpoints for menu items with dietary tags
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://menu-badges-preview.preview.emergentagent.com')

# Admin credentials
ADMIN_EMAIL = "PBadmin@purnabramha.com"
ADMIN_PASSWORD = "PB22052012"


class TestPublicMenuDietaryTags:
    """Test public menu endpoint returns dietary tag fields"""
    
    def test_menu_returns_dietary_fields(self):
        """Verify GET /api/menu returns no_onion_garlic and fasting_friendly fields"""
        response = requests.get(f"{BASE_URL}/api/menu")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert len(data) > 0, "Menu should have items"
        
        # Check first item has dietary fields
        first_item = data[0]
        assert "no_onion_garlic" in first_item, "Menu item should have no_onion_garlic field"
        assert "fasting_friendly" in first_item, "Menu item should have fasting_friendly field"
        print(f"✓ Menu items have dietary tag fields")
    
    def test_tagged_items_exist(self):
        """Verify items with dietary tags exist in database"""
        response = requests.get(f"{BASE_URL}/api/menu")
        assert response.status_code == 200
        
        data = response.json()
        tagged_items = [i for i in data if i.get('no_onion_garlic') or i.get('fasting_friendly')]
        
        assert len(tagged_items) >= 2, f"Expected at least 2 tagged items, found {len(tagged_items)}"
        print(f"✓ Found {len(tagged_items)} items with dietary tags")
        
        # Verify specific items
        sabudana_khichadi = next((i for i in data if i['name'] == 'Sabudana Khichadi'), None)
        assert sabudana_khichadi is not None, "Sabudana Khichadi should exist"
        assert sabudana_khichadi['no_onion_garlic'] == True, "Sabudana Khichadi should have no_onion_garlic=true"
        assert sabudana_khichadi['fasting_friendly'] == True, "Sabudana Khichadi should have fasting_friendly=true"
        print(f"✓ Sabudana Khichadi has correct dietary tags")
    
    def test_dietary_fields_are_boolean(self):
        """Verify dietary fields are boolean type"""
        response = requests.get(f"{BASE_URL}/api/menu")
        assert response.status_code == 200
        
        data = response.json()
        for item in data[:10]:  # Check first 10 items
            assert isinstance(item.get('no_onion_garlic'), bool), f"no_onion_garlic should be bool for {item['name']}"
            assert isinstance(item.get('fasting_friendly'), bool), f"fasting_friendly should be bool for {item['name']}"
        print(f"✓ Dietary fields are boolean type")


class TestAdminAuthentication:
    """Test admin authentication for menu management"""
    
    def test_admin_login_success(self):
        """Verify admin can login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "Response should contain token"
        assert "user" in data, "Response should contain user"
        print(f"✓ Admin login successful")
        return data['token']
    
    def test_admin_login_wrong_password(self):
        """Verify login fails with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Wrong password rejected")


class TestAdminMenuDietaryTags:
    """Test admin menu CRUD with dietary tags"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_admin_menu_returns_dietary_fields(self, auth_token):
        """Verify GET /api/admin/menu returns dietary tag fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/menu",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert len(data) > 0, "Admin menu should have items"
        
        first_item = data[0]
        assert "no_onion_garlic" in first_item, "Admin menu item should have no_onion_garlic field"
        assert "fasting_friendly" in first_item, "Admin menu item should have fasting_friendly field"
        print(f"✓ Admin menu items have dietary tag fields")
    
    def test_create_menu_item_with_dietary_tags(self, auth_token):
        """Verify POST /api/admin/menu creates item with dietary tags"""
        test_item = {
            "name": "TEST_Dietary_Tag_Item",
            "description": "Test item with dietary tags",
            "category": "Fasting",
            "price_inr": 150,
            "price_aud": 10,
            "is_veg": True,
            "is_available": True,
            "no_onion_garlic": True,
            "fasting_friendly": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/admin/menu",
            json=test_item,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        created_item = response.json()
        assert created_item['name'] == test_item['name'], "Name should match"
        assert created_item['no_onion_garlic'] == True, "no_onion_garlic should be True"
        assert created_item['fasting_friendly'] == True, "fasting_friendly should be True"
        print(f"✓ Created menu item with dietary tags: {created_item['id']}")
        
        # Verify item appears in public menu
        menu_response = requests.get(f"{BASE_URL}/api/menu")
        menu_data = menu_response.json()
        found_item = next((i for i in menu_data if i['id'] == created_item['id']), None)
        assert found_item is not None, "Created item should appear in public menu"
        assert found_item['no_onion_garlic'] == True, "Public menu should show no_onion_garlic=True"
        assert found_item['fasting_friendly'] == True, "Public menu should show fasting_friendly=True"
        print(f"✓ Item appears in public menu with correct dietary tags")
        
        # Cleanup - delete the test item
        delete_response = requests.delete(
            f"{BASE_URL}/api/admin/menu/{created_item['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        print(f"✓ Test item cleaned up")
    
    def test_create_menu_item_without_dietary_tags(self, auth_token):
        """Verify POST /api/admin/menu defaults dietary tags to false"""
        test_item = {
            "name": "TEST_No_Dietary_Tags",
            "description": "Test item without dietary tags",
            "category": "Snacks",
            "price_inr": 100,
            "price_aud": 8,
            "is_veg": True,
            "is_available": True
            # no_onion_garlic and fasting_friendly not provided
        }
        
        response = requests.post(
            f"{BASE_URL}/api/admin/menu",
            json=test_item,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        created_item = response.json()
        assert created_item['no_onion_garlic'] == False, "no_onion_garlic should default to False"
        assert created_item['fasting_friendly'] == False, "fasting_friendly should default to False"
        print(f"✓ Dietary tags default to False when not provided")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/admin/menu/{created_item['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        print(f"✓ Test item cleaned up")
    
    def test_update_menu_item_dietary_tags(self, auth_token):
        """Verify PUT /api/admin/menu/{id} updates dietary tags"""
        # First create an item
        test_item = {
            "name": "TEST_Update_Dietary_Tags",
            "description": "Test item for update",
            "category": "Snacks",
            "price_inr": 120,
            "price_aud": 9,
            "is_veg": True,
            "is_available": True,
            "no_onion_garlic": False,
            "fasting_friendly": False
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/admin/menu",
            json=test_item,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert create_response.status_code == 200
        created_item = create_response.json()
        item_id = created_item['id']
        
        # Update dietary tags
        update_data = {
            "name": "TEST_Update_Dietary_Tags",
            "description": "Test item for update",
            "category": "Fasting",
            "price_inr": 120,
            "price_aud": 9,
            "is_veg": True,
            "is_available": True,
            "no_onion_garlic": True,
            "fasting_friendly": True
        }
        
        update_response = requests.put(
            f"{BASE_URL}/api/admin/menu/{item_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        
        updated_item = update_response.json()
        assert updated_item['no_onion_garlic'] == True, "no_onion_garlic should be updated to True"
        assert updated_item['fasting_friendly'] == True, "fasting_friendly should be updated to True"
        print(f"✓ Dietary tags updated successfully")
        
        # Verify in GET request
        get_response = requests.get(f"{BASE_URL}/api/menu")
        menu_data = get_response.json()
        found_item = next((i for i in menu_data if i['id'] == item_id), None)
        assert found_item is not None, "Updated item should exist"
        assert found_item['no_onion_garlic'] == True, "GET should show updated no_onion_garlic"
        assert found_item['fasting_friendly'] == True, "GET should show updated fasting_friendly"
        print(f"✓ Updated dietary tags persisted correctly")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/admin/menu/{item_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        print(f"✓ Test item cleaned up")
    
    def test_toggle_dietary_tags_off(self, auth_token):
        """Verify dietary tags can be toggled from true to false"""
        # Create item with tags enabled
        test_item = {
            "name": "TEST_Toggle_Tags_Off",
            "description": "Test toggling tags off",
            "category": "Fasting",
            "price_inr": 130,
            "price_aud": 10,
            "is_veg": True,
            "is_available": True,
            "no_onion_garlic": True,
            "fasting_friendly": True
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/admin/menu",
            json=test_item,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert create_response.status_code == 200
        item_id = create_response.json()['id']
        
        # Toggle tags off
        update_data = {
            **test_item,
            "no_onion_garlic": False,
            "fasting_friendly": False
        }
        
        update_response = requests.put(
            f"{BASE_URL}/api/admin/menu/{item_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert update_response.status_code == 200
        
        updated_item = update_response.json()
        assert updated_item['no_onion_garlic'] == False, "no_onion_garlic should be toggled to False"
        assert updated_item['fasting_friendly'] == False, "fasting_friendly should be toggled to False"
        print(f"✓ Dietary tags toggled off successfully")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/admin/menu/{item_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        print(f"✓ Test item cleaned up")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
