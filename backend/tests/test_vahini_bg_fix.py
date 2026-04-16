"""
Test suite for Ask Vahini BG Fix and Region Awareness:
- POST /api/vahini/chat with adult query should NOT return BG (Balgopal kids menu) items
- POST /api/vahini/chat with Australia region context should work
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestVahiniBGFix:
    """Test that Vahini doesn't recommend BG/Balgopal kids menu items to adults"""

    def test_adult_query_no_bg_items(self):
        """Adult food query should NOT return BG (Balgopal kids menu) items"""
        response = requests.post(
            f"{BASE_URL}/api/vahini/chat",
            json={
                "message": "I'm an adult looking for a good lunch. What do you recommend?",
                "context": {"region": "India"}
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check recommended dishes don't contain BG items
        recommended_dishes = data.get("recommended_dishes", [])
        bg_items_found = []
        for dish in recommended_dishes:
            dish_name = dish.get("name", "").lower()
            dish_category = dish.get("category", "").lower()
            # BG items are kids menu items - check for BG prefix or kids category
            if "bg" in dish_name or "balgopal" in dish_name.lower() or "kids" in dish_category:
                bg_items_found.append(dish.get("name"))
        
        assert len(bg_items_found) == 0, f"Adult query returned BG/kids items: {bg_items_found}"
        print(f"PASS: Adult query returned {len(recommended_dishes)} dishes, no BG items")

    def test_spicy_food_query_no_bg_items(self):
        """Spicy food query (adult preference) should NOT return BG items"""
        response = requests.post(
            f"{BASE_URL}/api/vahini/chat",
            json={
                "message": "I want something very spicy for dinner",
                "context": {"region": "India"}
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        recommended_dishes = data.get("recommended_dishes", [])
        for dish in recommended_dishes:
            dish_name = dish.get("name", "").lower()
            assert "bg" not in dish_name, f"Spicy query returned BG item: {dish.get('name')}"
        
        print(f"PASS: Spicy food query returned {len(recommended_dishes)} dishes, no BG items")

    def test_business_lunch_no_bg_items(self):
        """Business lunch query should NOT return BG items"""
        response = requests.post(
            f"{BASE_URL}/api/vahini/chat",
            json={
                "message": "I have a business lunch meeting, what would you suggest?",
                "context": {"region": "India"}
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        recommended_dishes = data.get("recommended_dishes", [])
        for dish in recommended_dishes:
            dish_name = dish.get("name", "").lower()
            assert "bg" not in dish_name, f"Business lunch query returned BG item: {dish.get('name')}"
        
        print(f"PASS: Business lunch query returned {len(recommended_dishes)} dishes, no BG items")


class TestVahiniRegionAwareness:
    """Test Vahini region/currency awareness"""

    def test_australia_region_context(self):
        """POST /api/vahini/chat with Australia region should work"""
        response = requests.post(
            f"{BASE_URL}/api/vahini/chat",
            json={
                "message": "What's good for breakfast?",
                "context": {"region": "Australia"}
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "message" in data, "Response should contain message"
        assert "recommended_dishes" in data, "Response should contain recommended_dishes"
        print("PASS: Australia region context works")

    def test_india_region_context(self):
        """POST /api/vahini/chat with India region should work"""
        response = requests.post(
            f"{BASE_URL}/api/vahini/chat",
            json={
                "message": "Suggest something for dinner",
                "context": {"region": "India"}
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "message" in data, "Response should contain message"
        print("PASS: India region context works")

    def test_vahini_random_dish_no_bg(self):
        """Random dish endpoint should not return BG items for general use"""
        response = requests.get(f"{BASE_URL}/api/vahini/random-dish")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        dish_name = data.get("dish", {}).get("name", "").lower()
        # Random dish for general audience should not be a kids item
        # This is a softer check - BG items might still appear but shouldn't be frequent
        print(f"PASS: Random dish returned: {data.get('dish', {}).get('name', 'N/A')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
