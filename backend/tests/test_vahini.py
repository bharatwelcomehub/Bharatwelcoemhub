"""
Test suite for Ask Vahini - AI Food Wisdom Engine
Tests POST /api/vahini/chat and GET /api/vahini/random-dish endpoints
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestVahiniRandomDish:
    """Tests for GET /api/vahini/random-dish endpoint"""
    
    def test_random_dish_returns_200(self):
        """Test that random dish endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/vahini/random-dish", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Random dish endpoint returns 200")
    
    def test_random_dish_response_structure(self):
        """Test that random dish response has required fields"""
        response = requests.get(f"{BASE_URL}/api/vahini/random-dish", timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required top-level fields
        assert "message" in data, "Response missing 'message' field"
        assert "dish" in data, "Response missing 'dish' field"
        assert isinstance(data["message"], str), "Message should be a string"
        assert len(data["message"]) > 0, "Message should not be empty"
        
        # Check dish object structure
        dish = data["dish"]
        assert "id" in dish, "Dish missing 'id'"
        assert "name" in dish, "Dish missing 'name'"
        assert "category" in dish, "Dish missing 'category'"
        assert "price_inr" in dish, "Dish missing 'price_inr'"
        
        print(f"PASS: Random dish response structure valid - Dish: {dish['name']}")
    
    def test_random_dish_has_nutrition(self):
        """Test that random dish may include nutrition info"""
        response = requests.get(f"{BASE_URL}/api/vahini/random-dish", timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        # Nutrition is optional but should be present if available
        if data.get("nutrition"):
            nutrition = data["nutrition"]
            assert "calories" in nutrition or "menu_item_id" in nutrition
            print(f"PASS: Nutrition info present for dish")
        else:
            print("INFO: No nutrition info for this dish (acceptable)")
    
    def test_random_dish_vahini_message_style(self):
        """Test that Vahini message has warm, personal style"""
        response = requests.get(f"{BASE_URL}/api/vahini/random-dish", timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        message = data["message"].lower()
        
        # Check for Vahini-style language
        vahini_indicators = ["vahini", "suggests", "today", "dish", "eat"]
        has_vahini_style = any(word in message for word in vahini_indicators)
        
        assert has_vahini_style, f"Message doesn't seem Vahini-style: {data['message'][:100]}"
        print(f"PASS: Vahini message has warm style")


class TestVahiniChat:
    """Tests for POST /api/vahini/chat endpoint"""
    
    def test_chat_returns_200(self):
        """Test that chat endpoint returns 200 OK"""
        payload = {
            "message": "What should I eat today?",
            "session_id": None,
            "context": {"time_of_day": "afternoon"}
        }
        response = requests.post(
            f"{BASE_URL}/api/vahini/chat",
            json=payload,
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Chat endpoint returns 200")
    
    def test_chat_response_structure(self):
        """Test that chat response has required fields"""
        payload = {
            "message": "Suggest something for acidity",
            "session_id": None,
            "context": {}
        }
        response = requests.post(
            f"{BASE_URL}/api/vahini/chat",
            json=payload,
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields
        assert "session_id" in data, "Response missing 'session_id'"
        assert "message" in data, "Response missing 'message'"
        assert "recommended_dishes" in data, "Response missing 'recommended_dishes'"
        assert "cultural_note" in data, "Response missing 'cultural_note'"
        
        # Validate types
        assert isinstance(data["session_id"], str), "session_id should be string"
        assert isinstance(data["message"], str), "message should be string"
        assert isinstance(data["recommended_dishes"], list), "recommended_dishes should be list"
        
        print(f"PASS: Chat response structure valid - Session: {data['session_id'][:20]}...")
    
    def test_chat_first_message_greeting(self):
        """Test that first message includes Jai Hind Namaskar greeting"""
        payload = {
            "message": "Hello Vahini",
            "session_id": None,
            "context": {}
        }
        response = requests.post(
            f"{BASE_URL}/api/vahini/chat",
            json=payload,
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        message = data["message"]
        
        # First message should have the greeting
        assert data.get("is_first_message") == True, "Should be marked as first message"
        assert "jai hind" in message.lower() or "namaskar" in message.lower(), \
            f"First message should include 'Jai Hind Namaskar': {message[:100]}"
        
        print("PASS: First message includes proper greeting")
    
    def test_chat_recommended_dishes_structure(self):
        """Test that recommended dishes have proper structure"""
        payload = {
            "message": "What's good for breakfast?",
            "session_id": None,
            "context": {"time_of_day": "morning"}
        }
        response = requests.post(
            f"{BASE_URL}/api/vahini/chat",
            json=payload,
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        dishes = data.get("recommended_dishes", [])
        
        if len(dishes) > 0:
            dish = dishes[0]
            # Check dish structure
            assert "id" in dish, "Dish missing 'id'"
            assert "name" in dish, "Dish missing 'name'"
            assert "category" in dish, "Dish missing 'category'"
            assert "price_inr" in dish, "Dish missing 'price_inr'"
            print(f"PASS: Recommended dish structure valid - {dish['name']}")
        else:
            print("INFO: No dishes recommended for this query (acceptable for greetings)")
    
    def test_chat_session_persistence(self):
        """Test that session_id is returned and can be reused"""
        # First message
        payload1 = {
            "message": "I want something spicy",
            "session_id": None,
            "context": {}
        }
        response1 = requests.post(
            f"{BASE_URL}/api/vahini/chat",
            json=payload1,
            timeout=30
        )
        assert response1.status_code == 200
        
        data1 = response1.json()
        session_id = data1["session_id"]
        assert session_id is not None, "Session ID should be returned"
        
        # Second message with same session
        time.sleep(1)  # Small delay
        payload2 = {
            "message": "What about something sweet?",
            "session_id": session_id,
            "context": {}
        }
        response2 = requests.post(
            f"{BASE_URL}/api/vahini/chat",
            json=payload2,
            timeout=30
        )
        assert response2.status_code == 200
        
        data2 = response2.json()
        assert data2["session_id"] == session_id, "Session ID should persist"
        # Second message should NOT have the greeting
        assert data2.get("is_first_message") != True, "Should not be first message"
        
        print(f"PASS: Session persistence works - {session_id[:20]}...")
    
    def test_chat_with_context(self):
        """Test that context (time_of_day, mood, health) is accepted"""
        payload = {
            "message": "I'm feeling tired",
            "session_id": None,
            "context": {
                "time_of_day": "evening",
                "mood": "tired",
                "health": "low energy"
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/vahini/chat",
            json=payload,
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert len(data["message"]) > 0
        
        print("PASS: Chat accepts context parameters")
    
    def test_chat_empty_message_handling(self):
        """Test handling of empty message"""
        payload = {
            "message": "",
            "session_id": None,
            "context": {}
        }
        response = requests.post(
            f"{BASE_URL}/api/vahini/chat",
            json=payload,
            timeout=30
        )
        # Should either return 400 or handle gracefully
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"
        print(f"PASS: Empty message handled with status {response.status_code}")


class TestVahiniIntegration:
    """Integration tests for Vahini feature"""
    
    def test_menu_items_exist_for_recommendations(self):
        """Test that menu items exist for Vahini to recommend"""
        response = requests.get(f"{BASE_URL}/api/menu", timeout=10)
        assert response.status_code == 200
        
        items = response.json()
        assert len(items) > 0, "Menu should have items for Vahini to recommend"
        print(f"PASS: {len(items)} menu items available for recommendations")
    
    def test_vahini_recommends_actual_menu_items(self):
        """Test that Vahini recommends items from actual menu"""
        # Get menu items
        menu_response = requests.get(f"{BASE_URL}/api/menu", timeout=10)
        menu_items = menu_response.json()
        menu_names = [item["name"].lower() for item in menu_items]
        
        # Get Vahini recommendation
        payload = {
            "message": "Suggest a thali for lunch",
            "session_id": None,
            "context": {"time_of_day": "afternoon"}
        }
        chat_response = requests.post(
            f"{BASE_URL}/api/vahini/chat",
            json=payload,
            timeout=30
        )
        assert chat_response.status_code == 200
        
        data = chat_response.json()
        recommended = data.get("recommended_dishes", [])
        
        if len(recommended) > 0:
            # Check that recommended dishes exist in menu
            for dish in recommended:
                assert dish["name"].lower() in menu_names or any(
                    dish["name"].lower() in name for name in menu_names
                ), f"Recommended dish '{dish['name']}' not found in menu"
            print(f"PASS: All {len(recommended)} recommended dishes exist in menu")
        else:
            print("INFO: No specific dishes recommended (acceptable)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
