"""
Backend API Tests for Catering Admin and Hero Image Features
Tests: Hero Image API, Catering Packages CRUD, Catering Menu Items CRUD
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://golden-luxury-app.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "PBadmin@purnabramha.com"
ADMIN_PASSWORD = "PB22052012"


class TestHeroImageAPI:
    """Tests for Hero Image API - Banner DB fetch fix"""
    
    def test_get_hero_image_public(self):
        """Test public hero image endpoint returns data"""
        response = requests.get(f"{BASE_URL}/api/hero-image")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "title" in data
        assert "image_url" in data
        assert "is_active" in data
        
        # Verify image_url is a valid URL
        assert data["image_url"].startswith("http")
        print(f"✓ Hero image API returns: {data['title'][:50]}...")
    
    def test_admin_hero_images_requires_auth(self):
        """Test admin hero images endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/hero-images")
        assert response.status_code == 401 or response.status_code == 403
        print("✓ Admin hero images endpoint requires authentication")


class TestAdminAuth:
    """Tests for Admin Authentication"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token for admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    def test_admin_login(self, auth_token):
        """Test admin can login successfully"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print(f"✓ Admin login successful, token length: {len(auth_token)}")


class TestCateringPackagesAPI:
    """Tests for Catering Packages CRUD API"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token for admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Authentication failed")
        return response.json()["token"]
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_get_catering_packages_public(self):
        """Test public catering packages endpoint"""
        response = requests.get(f"{BASE_URL}/api/catering-packages")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "packages" in data
        assert "menuOptions" in data
        
        # Check packages exist
        packages = data["packages"]
        assert "india" in packages or len(packages) > 0
        print(f"✓ Public catering packages API returns data with {len(packages.get('india', []))} India packages")
    
    def test_get_admin_catering_packages(self, auth_headers):
        """Test admin catering packages endpoint"""
        response = requests.get(f"{BASE_URL}/api/admin/catering-packages", headers=auth_headers)
        assert response.status_code == 200
        packages = response.json()
        
        assert isinstance(packages, list)
        print(f"✓ Admin catering packages returns {len(packages)} packages")
        
        # Verify package structure if packages exist
        if len(packages) > 0:
            pkg = packages[0]
            assert "id" in pkg
            assert "name" in pkg
            assert "price_per_person_inr" in pkg or "price_per_person_aud" in pkg
            print(f"  First package: {pkg['name']}")
    
    def test_create_catering_package(self, auth_headers):
        """Test creating a new catering package"""
        test_package = {
            "name": "TEST_Package_Delete_Me",
            "description": "Test package for automated testing",
            "price_per_person_inr": 999,
            "price_per_person_aud": 99,
            "is_popular": False,
            "requirements": {"starters": 1, "mains": 1},
            "is_active": True,
            "display_order": 99
        }
        
        response = requests.post(
            f"{BASE_URL}/api/admin/catering-packages",
            json=test_package,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "package" in data or "message" in data
        print(f"✓ Created test catering package")
        
        # Cleanup - delete the test package
        if "package" in data and "id" in data["package"]:
            pkg_id = data["package"]["id"]
            delete_response = requests.delete(
                f"{BASE_URL}/api/admin/catering-packages/{pkg_id}",
                headers=auth_headers
            )
            assert delete_response.status_code == 200
            print(f"✓ Cleaned up test package")
    
    def test_catering_packages_requires_auth(self):
        """Test admin catering packages endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/catering-packages")
        assert response.status_code == 401 or response.status_code == 403
        print("✓ Admin catering packages endpoint requires authentication")


class TestCateringMenuItemsAPI:
    """Tests for Catering Menu Items CRUD API"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token for admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Authentication failed")
        return response.json()["token"]
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_get_admin_catering_menu(self, auth_headers):
        """Test admin catering menu items endpoint"""
        response = requests.get(f"{BASE_URL}/api/admin/catering-menu", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()
        
        assert isinstance(items, list)
        print(f"✓ Admin catering menu returns {len(items)} items")
        
        # Verify item structure if items exist
        if len(items) > 0:
            item = items[0]
            assert "id" in item
            assert "name" in item
            assert "category" in item
            print(f"  First item: {item['name']} ({item['category']})")
    
    def test_create_catering_menu_item(self, auth_headers):
        """Test creating a new catering menu item"""
        test_item = {
            "name": "TEST_Item_Delete_Me",
            "description": "Test item for automated testing",
            "category": "starters",
            "image_url": "",
            "is_veg": True,
            "is_available": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/admin/catering-menu",
            json=test_item,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "item" in data or "message" in data
        print(f"✓ Created test catering menu item")
        
        # Cleanup - delete the test item
        if "item" in data and "id" in data["item"]:
            item_id = data["item"]["id"]
            delete_response = requests.delete(
                f"{BASE_URL}/api/admin/catering-menu/{item_id}",
                headers=auth_headers
            )
            assert delete_response.status_code == 200
            print(f"✓ Cleaned up test menu item")
    
    def test_catering_menu_requires_auth(self):
        """Test admin catering menu endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/catering-menu")
        assert response.status_code == 401 or response.status_code == 403
        print("✓ Admin catering menu endpoint requires authentication")


class TestTiffinAPI:
    """Tests for Tiffin Admin API - Verify existing CRUD still works"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token for admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Authentication failed")
        return response.json()["token"]
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_get_tiffin_items_public(self):
        """Test public tiffin items endpoint"""
        response = requests.get(f"{BASE_URL}/api/tiffin-items")
        assert response.status_code == 200
        items = response.json()
        assert isinstance(items, list)
        print(f"✓ Public tiffin items returns {len(items)} items")
    
    def test_get_admin_tiffin_items(self, auth_headers):
        """Test admin tiffin items endpoint"""
        response = requests.get(f"{BASE_URL}/api/admin/tiffin-items", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()
        assert isinstance(items, list)
        print(f"✓ Admin tiffin items returns {len(items)} items")
    
    def test_get_tiffin_config(self):
        """Test tiffin config endpoint"""
        response = requests.get(f"{BASE_URL}/api/tiffin-config")
        assert response.status_code == 200
        config = response.json()
        
        # Verify config structure
        assert "unlimited_breakfast_price_inr" in config
        assert "unlimited_breakfast_price_aud" in config
        print(f"✓ Tiffin config: ₹{config['unlimited_breakfast_price_inr']} / ${config['unlimited_breakfast_price_aud']}")


class TestAdminHeroImagesCRUD:
    """Tests for Admin Hero Images CRUD - Banner management"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token for admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Authentication failed")
        return response.json()["token"]
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_get_admin_hero_images(self, auth_headers):
        """Test admin hero images endpoint"""
        response = requests.get(f"{BASE_URL}/api/admin/hero-images", headers=auth_headers)
        assert response.status_code == 200
        images = response.json()
        assert isinstance(images, list)
        print(f"✓ Admin hero images returns {len(images)} images")
    
    def test_create_and_delete_hero_image(self, auth_headers):
        """Test creating and deleting a hero image"""
        test_image = {
            "title": "TEST_Banner_Delete_Me",
            "description": "Test banner for automated testing",
            "image_url": "https://example.com/test-image.jpg",
            "is_active": False  # Don't set as active to avoid affecting homepage
        }
        
        # Create
        response = requests.post(
            f"{BASE_URL}/api/admin/hero-images",
            json=test_image,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        image_id = data["id"]
        print(f"✓ Created test hero image with id: {image_id}")
        
        # Verify it exists
        get_response = requests.get(f"{BASE_URL}/api/admin/hero-images", headers=auth_headers)
        images = get_response.json()
        found = any(img["id"] == image_id for img in images)
        assert found, "Created image not found in list"
        print(f"✓ Verified test hero image exists")
        
        # Delete
        delete_response = requests.delete(
            f"{BASE_URL}/api/admin/hero-images/{image_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200
        print(f"✓ Deleted test hero image")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
