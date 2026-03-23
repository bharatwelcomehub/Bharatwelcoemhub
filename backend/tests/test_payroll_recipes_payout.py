"""
Test cases for Payroll, Recipes, and Payout Summary endpoints
Testing the refactored modules: payroll.py, recipes.py, and center_accounts.py payout-summary
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPayrollEndpoints:
    """Test payroll module endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        # Login as Super Admin
        login_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT"
        })
        assert login_res.status_code == 200
        
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT",
            "otp": "123456"
        })
        assert verify_res.status_code == 200
        data = verify_res.json()
        self.token = data.get("token")
        assert self.token, "Failed to get auth token"
    
    def test_payroll_status(self):
        """Test POST /api/payroll_status - Check payroll lock status"""
        # Note: server.py endpoint requires center field
        response = requests.post(f"{BASE_URL}/api/payroll_status", json={
            "token": self.token,
            "center": "PB-HSR",
            "month": "2025-12"
        })
        assert response.status_code == 200
        data = response.json()
        assert "locked" in data
        assert isinstance(data["locked"], bool)
        print(f"Payroll status for 2025-12: locked={data['locked']}")
    
    def test_salary_preview(self):
        """Test POST /api/salary_preview - Preview salary data"""
        response = requests.post(f"{BASE_URL}/api/salary_preview", json={
            "token": self.token,
            "month": "2025-12",
            "targetCenter": "PB-HSR"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "salaryData" in data
        assert "totals" in data
        assert "employeeCount" in data
        print(f"Salary preview: {data['employeeCount']} employees, totals: {data['totals']}")
    
    def test_lock_payroll(self):
        """Test POST /api/lock_payroll - Lock payroll for a month"""
        # Note: server.py endpoint requires center field
        response = requests.post(f"{BASE_URL}/api/lock_payroll", json={
            "token": self.token,
            "center": "PB-HSR",
            "month": "2025-11"  # Use a different month to avoid conflicts
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"Lock payroll result: {data}")


class TestRecipesEndpoints:
    """Test recipes module endpoints"""
    
    def test_get_recipes(self):
        """Test GET /api/recipes - Get all recipes"""
        response = requests.get(f"{BASE_URL}/api/recipes")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "recipes" in data
        assert isinstance(data["categories"], list)
        assert isinstance(data["recipes"], dict)
        print(f"Recipes: {len(data['recipes'])} recipes in {len(data['categories'])} categories")
    
    def test_get_bhojan_guru(self):
        """Test GET /api/bhojan_guru - Get Bhojan Guru recommendations"""
        response = requests.get(f"{BASE_URL}/api/bhojan_guru")
        assert response.status_code == 200
        data = response.json()
        assert "bhojanGuru" in data
        assert "regionWise" in data
        assert "bodyNeedMatrix" in data
        print(f"Bhojan Guru: {len(data['bhojanGuru'])} items")
    
    def test_recipes_search(self):
        """Test GET /api/recipes/search - Search recipes"""
        response = requests.get(f"{BASE_URL}/api/recipes/search?q=dal")
        assert response.status_code == 200
        data = response.json()
        assert "recipes" in data
        print(f"Search 'dal': {len(data['recipes'])} results")
    
    def test_recipes_search_empty(self):
        """Test GET /api/recipes/search with empty query - Returns all recipes"""
        response = requests.get(f"{BASE_URL}/api/recipes/search?q=")
        assert response.status_code == 200
        data = response.json()
        assert "recipes" in data
        print(f"Search empty: {len(data['recipes'])} results")


class TestPayoutSummaryEndpoint:
    """Test payout-summary endpoint for Month-wise Payout Grid"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        login_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT"
        })
        assert login_res.status_code == 200
        
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT",
            "otp": "123456"
        })
        assert verify_res.status_code == 200
        data = verify_res.json()
        self.token = data.get("token")
        assert self.token, "Failed to get auth token"
    
    def test_payout_summary_perth(self):
        """Test POST /api/center-accounts/payout-summary for PB-PERTH"""
        response = requests.post(f"{BASE_URL}/api/center-accounts/payout-summary", json={
            "token": self.token,
            "center": "PB-PERTH"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        # Verify franchise info
        assert "franchise" in data
        assert data["franchise"]["code"] == "FR-PERTH"
        assert data["franchise"]["mg_amount"] == 22191.27  # Expected MG for Perth
        
        # Verify period info
        assert "period" in data
        assert data["period"]["revenue_start_date"] is not None
        
        # Verify totals
        assert "totals" in data
        totals = data["totals"]
        assert "revenue_share" in totals
        assert "payable" in totals
        assert "paid" in totals
        assert "pending" in totals
        
        # Verify monthly_data structure
        assert "monthly_data" in data
        assert len(data["monthly_data"]) > 0
        
        # Check first month data structure
        first_month = data["monthly_data"][0]
        assert "month" in first_month
        assert "total_sales" in first_month
        assert "revenue_share" in first_month
        assert "mg_amount" in first_month
        assert "payable_type" in first_month
        assert "payable_amount" in first_month
        assert "paid" in first_month
        assert "pending" in first_month
        assert "status" in first_month
        
        print(f"Payout summary for PB-PERTH: {len(data['monthly_data'])} months, MG={data['franchise']['mg_amount']}")
    
    def test_payout_summary_india_center(self):
        """Test POST /api/center-accounts/payout-summary for an India center"""
        response = requests.post(f"{BASE_URL}/api/center-accounts/payout-summary", json={
            "token": self.token,
            "center": "PB-HSR"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "monthly_data" in data
        print(f"Payout summary for PB-HSR: {len(data['monthly_data'])} months")
    
    def test_payout_summary_with_date_range(self):
        """Test POST /api/center-accounts/payout-summary with custom date range"""
        response = requests.post(f"{BASE_URL}/api/center-accounts/payout-summary", json={
            "token": self.token,
            "center": "PB-PERTH",
            "from_month": "2025-10",
            "to_month": "2026-01"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "monthly_data" in data
        
        # Should have 4 months (Oct, Nov, Dec 2025, Jan 2026)
        assert len(data["monthly_data"]) == 4
        print(f"Payout summary with date range: {len(data['monthly_data'])} months")


class TestCenterAccountsSummary:
    """Test center accounts summary endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        login_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT"
        })
        assert login_res.status_code == 200
        
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT",
            "otp": "123456"
        })
        assert verify_res.status_code == 200
        data = verify_res.json()
        self.token = data.get("token")
        assert self.token, "Failed to get auth token"
    
    def test_account_summary_perth(self):
        """Test POST /api/center-accounts/summary for PB-PERTH"""
        response = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": self.token,
            "center": "PB-PERTH",
            "month": "2025-11"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        summary = data.get("summary")
        assert summary is not None
        
        # Verify MG calculation is present
        assert "mg_calculation" in summary
        assert "payout" in summary
        
        # Verify payout structure
        payout = summary["payout"]
        assert "type" in payout
        assert "amount" in payout
        assert "mg_amount" in payout
        assert "revenue_share_amount" in payout
        
        print(f"Account summary for PB-PERTH 2025-11: payout type={payout['type']}, amount={payout['amount']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
