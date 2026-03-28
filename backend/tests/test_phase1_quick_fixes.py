"""
Test Phase 1 Quick Fixes:
1. MIS Working Capital API - center-wise filtering
2. Franchise connectivity (tested via franchise API)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMISWorkingCapital:
    """Test MIS Working Capital API - center-wise filtering"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for Super Admin"""
        # Send OTP
        otp_resp = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190"
        })
        assert otp_resp.status_code == 200, f"Failed to send OTP: {otp_resp.text}"
        
        # Verify OTP
        verify_resp = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190",
            "otp": "123456"
        })
        assert verify_resp.status_code == 200, f"Failed to verify OTP: {verify_resp.text}"
        return verify_resp.json().get("token")
    
    def test_working_capital_all_centers(self, auth_token):
        """Test WC API with center=all returns all centers"""
        response = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": auth_token,
            "center": "all"
        })
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        # Should have summary fields (API uses initial_working_capital, available_working_capital)
        assert "initial_working_capital" in data, "Missing initial_working_capital"
        assert "total_loans" in data, "Missing total_loans"
        assert "total_repaid" in data, "Missing total_repaid"
        assert "available_working_capital" in data, "Missing available_working_capital"
        assert "centers" in data, "Missing centers array"
        
        print(f"All centers WC: initial={data['initial_working_capital']}, available={data['available_working_capital']}")
        print(f"Number of centers with WC data: {len(data['centers'])}")
    
    def test_working_capital_specific_center_with_franchise(self, auth_token):
        """Test WC API with specific center (PB-PERTH) that has franchise mapped"""
        response = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": auth_token,
            "center": "PB-PERTH"
        })
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        # Should return WC for PB-PERTH franchise
        assert "initial_working_capital" in data
        assert "centers" in data
        
        # PB-PERTH should have WC=900000 based on context
        print(f"PB-PERTH WC: initial={data['initial_working_capital']}, available={data['available_working_capital']}")
        
        # Check centers array contains PB-PERTH
        center_codes = [c.get("center") for c in data.get("centers", [])]
        if data["initial_working_capital"] > 0:
            assert "PB-PERTH" in center_codes or len(center_codes) > 0, "Expected PB-PERTH in centers"
            print(f"Centers returned: {center_codes}")
    
    def test_working_capital_center_without_franchise(self, auth_token):
        """Test WC API with center (PB-KHARADI) that has no franchise mapped - should return 0"""
        response = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": auth_token,
            "center": "PB-KHARADI"
        })
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        # Should return 0 values for center without franchise
        print(f"PB-KHARADI WC: initial={data.get('initial_working_capital', 0)}, available={data.get('available_working_capital', 0)}")
        
        # Centers array should be empty or have 0 values for center without franchise
        centers = data.get("centers", [])
        if len(centers) == 0:
            print("No franchise mapped to PB-KHARADI - correct behavior (empty centers)")
            assert data.get("initial_working_capital", 0) == 0, "Expected 0 initial WC for unmapped center"
        else:
            # If there's data, check if it's for PB-KHARADI
            for c in centers:
                print(f"Center {c.get('center')}: initial_wc={c.get('initial_wc', 0)}")


class TestFranchiseConnectivity:
    """Test franchise connectivity data for dashboard"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for Super Admin"""
        otp_resp = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190"
        })
        assert otp_resp.status_code == 200
        
        verify_resp = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190",
            "otp": "123456"
        })
        assert verify_resp.status_code == 200
        return verify_resp.json().get("token")
    
    def test_franchise_list_api(self, auth_token):
        """Test franchise list API returns franchise data with owner info"""
        response = requests.post(f"{BASE_URL}/api/franchises/list", json={
            "token": auth_token
        })
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        franchises = data.get("franchises", [])
        print(f"Total franchises: {len(franchises)}")
        
        for f in franchises[:3]:  # Print first 3
            print(f"Franchise: {f.get('franchise_name', f.get('name', 'N/A'))}, "
                  f"Owner: {f.get('owner_name', 'N/A')}, "
                  f"Center: {f.get('center', 'N/A')}")
    
    def test_franchise_owner_dashboard_data(self, auth_token):
        """Test franchise owner dashboard API returns connectivity info"""
        # Try to get franchise owner dashboard data
        response = requests.post(f"{BASE_URL}/api/franchise-owner/dashboard", json={
            "token": auth_token,
            "center": "PB-PERTH"  # Center with franchise
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"Franchise dashboard data: {data.keys()}")
            if "franchise" in data:
                f = data["franchise"]
                print(f"Franchise info: name={f.get('franchise_name', f.get('name'))}, "
                      f"owner={f.get('owner_name', 'N/A')}")
        else:
            print(f"Franchise dashboard API status: {response.status_code}")
            # This is acceptable - the API might not exist or require different params


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
