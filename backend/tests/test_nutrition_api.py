"""
Test suite for AI-Powered Dish Nutrition & Health Analysis feature.
Tests:
- GET /api/nutrition/{item_id}: Returns nutrition data (cached or AI-generated)
- POST /api/admin/nutrition/generate-bulk: Admin bulk generation
- PUT /api/admin/nutrition/{item_id}: Admin manual edit
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "PBadmin@purnabramha.com"
ADMIN_PASSWORD = "PB22052012"

# Known item with cached nutrition
CACHED_ITEM_ID = "e746b985-7519-4133-ba4b-a8aa0000f497"  # Sabudana Khichadi


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed - skipping admin tests")


@pytest.fixture(scope="module")
def menu_items():
    """Get list of menu items"""
    response = requests.get(f"{BASE_URL}/api/menu")
    if response.status_code == 200:
        return response.json()
    return []


class TestNutritionGetEndpoint:
    """Tests for GET /api/nutrition/{item_id}"""
    
    def test_get_cached_nutrition_returns_200(self):
        """Test getting nutrition for item with cached data"""
        response = requests.get(f"{BASE_URL}/api/nutrition/{CACHED_ITEM_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"PASS: GET /api/nutrition/{CACHED_ITEM_ID} returns 200")
    
    def test_cached_nutrition_has_required_fields(self):
        """Test that cached nutrition data has all required fields"""
        response = requests.get(f"{BASE_URL}/api/nutrition/{CACHED_ITEM_ID}")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = [
            "menu_item_id", "menu_item_name", "calories", "protein", 
            "carbs", "fats", "fiber", "serving_size", "health_benefits",
            "allergens", "ayurvedic_benefits", "dietary_tags"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print(f"PASS: Nutrition data has all required fields: {required_fields}")
    
    def test_nutrition_data_types(self):
        """Test that nutrition data has correct types"""
        response = requests.get(f"{BASE_URL}/api/nutrition/{CACHED_ITEM_ID}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Numeric fields
        assert isinstance(data["calories"], (int, float)), "calories should be numeric"
        assert isinstance(data["protein"], (int, float)), "protein should be numeric"
        assert isinstance(data["carbs"], (int, float)), "carbs should be numeric"
        assert isinstance(data["fats"], (int, float)), "fats should be numeric"
        assert isinstance(data["fiber"], (int, float)), "fiber should be numeric"
        
        # String fields
        assert isinstance(data["menu_item_name"], str), "menu_item_name should be string"
        assert isinstance(data["serving_size"], str), "serving_size should be string"
        assert isinstance(data["ayurvedic_benefits"], str), "ayurvedic_benefits should be string"
        
        # Array fields
        assert isinstance(data["health_benefits"], list), "health_benefits should be list"
        assert isinstance(data["allergens"], list), "allergens should be list"
        assert isinstance(data["dietary_tags"], list), "dietary_tags should be list"
        
        print("PASS: All nutrition data types are correct")
    
    def test_nutrition_values_are_reasonable(self):
        """Test that nutrition values are within reasonable ranges"""
        response = requests.get(f"{BASE_URL}/api/nutrition/{CACHED_ITEM_ID}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Calories should be positive and reasonable for a dish
        assert 50 <= data["calories"] <= 2000, f"Calories {data['calories']} out of range"
        
        # Macros should be non-negative
        assert data["protein"] >= 0, "Protein should be non-negative"
        assert data["carbs"] >= 0, "Carbs should be non-negative"
        assert data["fats"] >= 0, "Fats should be non-negative"
        assert data["fiber"] >= 0, "Fiber should be non-negative"
        
        # Health benefits should have at least one item
        assert len(data["health_benefits"]) >= 1, "Should have at least one health benefit"
        
        print(f"PASS: Nutrition values are reasonable - {data['calories']} kcal, {data['protein']}g protein")
    
    def test_nutrition_for_nonexistent_item_returns_404(self):
        """Test that requesting nutrition for non-existent item returns 404"""
        fake_id = "nonexistent-item-id-12345"
        response = requests.get(f"{BASE_URL}/api/nutrition/{fake_id}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Non-existent item returns 404")
    
    def test_nutrition_caching_returns_same_data(self):
        """Test that repeated calls return cached data (same values)"""
        response1 = requests.get(f"{BASE_URL}/api/nutrition/{CACHED_ITEM_ID}")
        response2 = requests.get(f"{BASE_URL}/api/nutrition/{CACHED_ITEM_ID}")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Core values should be identical (cached)
        assert data1["calories"] == data2["calories"], "Cached calories should match"
        assert data1["protein"] == data2["protein"], "Cached protein should match"
        assert data1["menu_item_name"] == data2["menu_item_name"], "Cached name should match"
        
        print("PASS: Repeated calls return same cached data")


class TestNutritionAdminEndpoints:
    """Tests for admin nutrition endpoints"""
    
    def test_admin_update_nutrition_requires_auth(self):
        """Test that PUT /api/admin/nutrition/{item_id} requires authentication"""
        response = requests.put(
            f"{BASE_URL}/api/admin/nutrition/{CACHED_ITEM_ID}",
            json={"calories": 400}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Admin update nutrition requires auth")
    
    def test_admin_bulk_generate_requires_auth(self):
        """Test that POST /api/admin/nutrition/generate-bulk requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/admin/nutrition/generate-bulk",
            json={"force": False}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Admin bulk generate requires auth")
    
    def test_admin_update_nutrition_with_auth(self, admin_token):
        """Test admin can update nutrition data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get current data first
        get_response = requests.get(f"{BASE_URL}/api/nutrition/{CACHED_ITEM_ID}")
        original_data = get_response.json()
        
        # Update with new calories value
        new_calories = original_data["calories"] + 10
        update_data = {
            "calories": new_calories,
            "protein": original_data["protein"],
            "carbs": original_data["carbs"],
            "fats": original_data["fats"],
            "fiber": original_data["fiber"],
            "serving_size": original_data["serving_size"],
            "health_benefits": original_data["health_benefits"],
            "allergens": original_data["allergens"],
            "ayurvedic_benefits": original_data["ayurvedic_benefits"],
            "dietary_tags": original_data["dietary_tags"],
            "menu_item_name": original_data["menu_item_name"]
        }
        
        response = requests.put(
            f"{BASE_URL}/api/admin/nutrition/{CACHED_ITEM_ID}",
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        updated_data = response.json()
        assert updated_data["calories"] == new_calories, "Calories should be updated"
        
        # Restore original value
        update_data["calories"] = original_data["calories"]
        requests.put(
            f"{BASE_URL}/api/admin/nutrition/{CACHED_ITEM_ID}",
            json=update_data,
            headers=headers
        )
        
        print(f"PASS: Admin can update nutrition data (changed calories to {new_calories}, then restored)")
    
    def test_admin_bulk_generate_returns_stats(self, admin_token):
        """Test bulk generate returns proper statistics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Call with force=False to skip already cached items
        response = requests.post(
            f"{BASE_URL}/api/admin/nutrition/generate-bulk",
            json={"force": False},
            headers=headers,
            timeout=120  # Allow time for AI generation
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "generated" in data, "Response should have 'generated' count"
        assert "skipped" in data, "Response should have 'skipped' count"
        assert "errors" in data, "Response should have 'errors' count"
        assert "total" in data, "Response should have 'total' count"
        
        print(f"PASS: Bulk generate returned stats - generated: {data['generated']}, skipped: {data['skipped']}, errors: {data['errors']}, total: {data['total']}")


class TestNutritionAIGeneration:
    """Tests for AI nutrition generation (for items without cached data)"""
    
    def test_nutrition_generation_for_new_item(self, menu_items, admin_token):
        """Test that nutrition is generated for items without cached data"""
        if not menu_items:
            pytest.skip("No menu items available")
        
        # Find an item that might not have nutrition cached
        # We'll use a random item and check if it generates
        test_item = None
        for item in menu_items:
            if item["id"] != CACHED_ITEM_ID:
                test_item = item
                break
        
        if not test_item:
            pytest.skip("No other menu items to test")
        
        # Request nutrition - this may trigger AI generation
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/api/nutrition/{test_item['id']}", timeout=60)
        elapsed = time.time() - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["menu_item_id"] == test_item["id"], "Item ID should match"
        assert data["menu_item_name"] == test_item["name"], "Item name should match"
        
        print(f"PASS: Nutrition for '{test_item['name']}' returned in {elapsed:.2f}s")


class TestMenuItemDietaryTags:
    """Verify dietary tags still work (from previous feature)"""
    
    def test_menu_items_have_dietary_fields(self, menu_items):
        """Test that menu items include dietary tag fields"""
        if not menu_items:
            pytest.skip("No menu items available")
        
        # Check first few items have the fields
        for item in menu_items[:5]:
            assert "no_onion_garlic" in item, f"Item {item['name']} missing no_onion_garlic field"
            assert "fasting_friendly" in item, f"Item {item['name']} missing fasting_friendly field"
        
        print("PASS: Menu items have dietary tag fields")
    
    def test_sabudana_khichadi_has_dietary_tags(self, menu_items):
        """Test that Sabudana Khichadi has correct dietary tags"""
        sabudana = next((item for item in menu_items if item["id"] == CACHED_ITEM_ID), None)
        
        if not sabudana:
            pytest.skip("Sabudana Khichadi not found")
        
        assert sabudana["no_onion_garlic"] == True, "Sabudana should be no onion/garlic"
        assert sabudana["fasting_friendly"] == True, "Sabudana should be fasting friendly"
        
        print(f"PASS: Sabudana Khichadi has correct dietary tags - no_onion_garlic: {sabudana['no_onion_garlic']}, fasting_friendly: {sabudana['fasting_friendly']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
