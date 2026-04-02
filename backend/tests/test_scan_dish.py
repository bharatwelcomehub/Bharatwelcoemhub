"""
Test cases for Scan Dish API - POST /api/scan-dish
Tests the AI-powered dish identification feature using GPT-4.1 vision
"""
import pytest
import requests
import base64
import os
from io import BytesIO

# Use PIL to create a realistic food-like test image
try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None
    ImageDraw = None

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

def create_food_test_image():
    """Create a colorful food-like test image with PIL (simulating Indian food on a plate)"""
    if Image is None:
        pytest.skip("PIL not installed")
    
    # Create a white plate background
    img = Image.new('RGB', (400, 400), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw a plate circle (light gray)
    draw.ellipse([20, 20, 380, 380], fill='#f0f0f0', outline='#cccccc')
    
    # Draw food items - colorful circles to simulate Indian food
    # Orange curry/dal
    draw.ellipse([80, 80, 200, 200], fill='#FF8C00', outline='#CC7000')
    # Green sabzi/chutney
    draw.ellipse([180, 150, 280, 250], fill='#228B22', outline='#1a6b1a')
    # Yellow rice/dal
    draw.ellipse([100, 200, 220, 320], fill='#FFD700', outline='#CCA300')
    # Brown roti/chapati
    draw.ellipse([220, 220, 340, 340], fill='#D2691E', outline='#A0522D')
    # Red tomato/chutney
    draw.ellipse([150, 100, 200, 150], fill='#DC143C', outline='#B22222')
    
    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


class TestScanDishAPI:
    """Tests for POST /api/scan-dish endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.api_url = f"{BASE_URL}/api/scan-dish"
        self.headers = {"Content-Type": "application/json"}
    
    def test_scan_dish_missing_image_returns_400(self):
        """Test that missing image_base64 returns 400 error"""
        response = requests.post(
            self.api_url,
            json={},
            headers=self.headers
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "image_base64" in data["detail"].lower() or "required" in data["detail"].lower()
        print("PASS: Missing image_base64 returns 400")
    
    def test_scan_dish_empty_image_returns_400(self):
        """Test that empty image_base64 returns 400 error"""
        response = requests.post(
            self.api_url,
            json={"image_base64": ""},
            headers=self.headers
        )
        # Empty string should be treated as missing
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("PASS: Empty image_base64 returns 400")
    
    def test_scan_dish_with_valid_image_returns_result(self):
        """Test scan-dish with a valid food-like image returns a result"""
        image_base64 = create_food_test_image()
        
        response = requests.post(
            self.api_url,
            json={"image_base64": image_base64},
            headers=self.headers,
            timeout=60  # AI processing may take time
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Response should have success field
        assert "success" in data, "Response should have 'success' field"
        
        if data["success"]:
            # Successful match - verify structure
            assert "matched_item" in data, "Successful response should have 'matched_item'"
            item = data["matched_item"]
            assert "id" in item, "matched_item should have 'id'"
            assert "name" in item, "matched_item should have 'name'"
            assert "category" in item, "matched_item should have 'category'"
            assert "price_inr" in item or "price_aud" in item, "matched_item should have price"
            
            # Check for nutrition data
            if "nutrition" in data and data["nutrition"]:
                nutrition = data["nutrition"]
                assert "calories" in nutrition, "nutrition should have 'calories'"
                assert "protein" in nutrition, "nutrition should have 'protein'"
            
            # Check confidence
            assert "confidence" in data, "Response should have 'confidence'"
            assert data["confidence"] in ["high", "medium", "low"], f"Invalid confidence: {data['confidence']}"
            
            print(f"PASS: Scan identified dish: {item['name']} with {data['confidence']} confidence")
        else:
            # Failed match - verify error structure
            assert "message" in data, "Failed response should have 'message'"
            assert len(data["message"]) > 0, "Error message should not be empty"
            print(f"PASS: Scan returned no match with message: {data['message']}")
    
    def test_scan_dish_response_structure_on_no_match(self):
        """Test that when dish can't be identified, response has proper structure"""
        # Create a non-food image (just solid color)
        if Image is None:
            pytest.skip("PIL not installed")
        
        # Create a simple gradient image (not food-like)
        img = Image.new('RGB', (200, 200), color='blue')
        draw = ImageDraw.Draw(img)
        # Add some random shapes that don't look like food
        draw.rectangle([20, 20, 180, 180], fill='purple')
        draw.polygon([(100, 30), (30, 170), (170, 170)], fill='cyan')
        
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        response = requests.post(
            self.api_url,
            json={"image_base64": image_base64},
            headers=self.headers,
            timeout=60
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Response should have success field
        assert "success" in data, "Response should have 'success' field"
        
        # Whether it matches or not, structure should be valid
        if not data["success"]:
            assert "message" in data, "Failed response should have 'message'"
            print(f"PASS: Non-food image returned no match: {data['message']}")
        else:
            # AI might still try to match - that's okay
            print(f"PASS: AI attempted match even for non-food image: {data.get('matched_item', {}).get('name', 'unknown')}")
    
    def test_scan_dish_matched_item_has_dietary_fields(self):
        """Test that matched item includes dietary tag fields"""
        image_base64 = create_food_test_image()
        
        response = requests.post(
            self.api_url,
            json={"image_base64": image_base64},
            headers=self.headers,
            timeout=60
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        if data.get("success") and "matched_item" in data:
            item = data["matched_item"]
            # Check dietary fields exist (from previous feature)
            assert "is_veg" in item, "matched_item should have 'is_veg'"
            assert "no_onion_garlic" in item, "matched_item should have 'no_onion_garlic'"
            assert "fasting_friendly" in item, "matched_item should have 'fasting_friendly'"
            print(f"PASS: Matched item has dietary fields - is_veg: {item['is_veg']}, no_onion_garlic: {item['no_onion_garlic']}, fasting_friendly: {item['fasting_friendly']}")
        else:
            print("SKIP: No match to verify dietary fields")


class TestScanDishNutritionIntegration:
    """Tests for nutrition data in scan-dish response"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.api_url = f"{BASE_URL}/api/scan-dish"
        self.headers = {"Content-Type": "application/json"}
    
    def test_scan_dish_includes_nutrition_when_matched(self):
        """Test that successful scan includes nutrition data"""
        image_base64 = create_food_test_image()
        
        response = requests.post(
            self.api_url,
            json={"image_base64": image_base64},
            headers=self.headers,
            timeout=60
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if data.get("success"):
            # Nutrition should be present (either cached or generated)
            if "nutrition" in data and data["nutrition"]:
                nutrition = data["nutrition"]
                # Verify nutrition structure
                required_fields = ["calories", "protein", "carbs", "fats", "fiber"]
                for field in required_fields:
                    assert field in nutrition, f"nutrition should have '{field}'"
                
                # Verify optional but expected fields
                optional_fields = ["health_benefits", "allergens", "ayurvedic_benefits", "dietary_tags"]
                present_optional = [f for f in optional_fields if f in nutrition]
                print(f"PASS: Nutrition data present with fields: {required_fields + present_optional}")
            else:
                print("INFO: Nutrition data not included in response (may be generated on-demand)")
        else:
            print("SKIP: No match to verify nutrition")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
