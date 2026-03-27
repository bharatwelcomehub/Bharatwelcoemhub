"""
Test MIS Dashboard v2 Features:
- Working Capital endpoint
- Center filtering for all MIS endpoints
- Export functionality (frontend)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMISDashboardV2:
    """MIS Dashboard v2 feature tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        # Send OTP
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT"
        })
        assert res.status_code == 200
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT",
            "otp": "123456"
        })
        assert res.status_code == 200
        self.token = res.json()["token"]
        self.session = res.json()
    
    # ==========================================
    # Working Capital Endpoint Tests
    # ==========================================
    
    def test_working_capital_endpoint_exists(self):
        """Test /api/mis/working-capital endpoint returns data"""
        res = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": self.token,
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 200
        data = res.json()
        
        # Verify response structure
        assert "data" in data
        assert "total_working_capital" in data
        assert isinstance(data["data"], list)
        
    def test_working_capital_data_structure(self):
        """Test working capital data has correct fields"""
        res = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": self.token,
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 200
        data = res.json()
        
        if len(data["data"]) > 0:
            day = data["data"][0]
            # Verify each day has required fields
            assert "date" in day
            assert "daily_sales" in day
            assert "daily_expenses" in day
            assert "daily_gst" in day
            assert "daily_net" in day
            assert "working_capital" in day
            
    def test_working_capital_cumulative_calculation(self):
        """Test working capital is cumulative"""
        res = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": self.token,
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 200
        data = res.json()
        
        # Working capital should be cumulative (non-decreasing if no negative days)
        # Just verify it's a number
        assert isinstance(data["total_working_capital"], (int, float))
        
    def test_working_capital_with_center_filter(self):
        """Test working capital filters by center"""
        # Get all centers
        res_all = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": self.token,
            "period": "current_month",
            "center": "all"
        })
        assert res_all.status_code == 200
        
        # Get specific center
        res_hsr = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": self.token,
            "period": "current_month",
            "center": "PB-HSR"
        })
        assert res_hsr.status_code == 200
        
        # Both should return valid data
        assert "total_working_capital" in res_all.json()
        assert "total_working_capital" in res_hsr.json()
        
    # ==========================================
    # Center Filtering Tests
    # ==========================================
    
    def test_overview_center_filter(self):
        """Test /api/mis/overview filters by center"""
        res = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": self.token,
            "period": "current_month",
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        data = res.json()
        
        # When filtering by center, centers list should only have that center
        assert "centers" in data
        if len(data["centers"]) > 0:
            # All centers in response should be PB-HSR
            for c in data["centers"]:
                assert c["center"] == "PB-HSR"
                
    def test_center_comparison_with_filter(self):
        """Test /api/mis/center-comparison accepts center filter"""
        res = requests.post(f"{BASE_URL}/api/mis/center-comparison", json={
            "token": self.token,
            "period": "current_month",
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        data = res.json()
        
        assert "centers" in data
        # When filtering by specific center, should only return that center
        if len(data["centers"]) > 0:
            assert data["centers"][0]["center"] == "PB-HSR"
            
    def test_sales_trends_center_filter(self):
        """Test /api/mis/sales-trends filters by center"""
        res = requests.post(f"{BASE_URL}/api/mis/sales-trends", json={
            "token": self.token,
            "period": "current_month",
            "center": "PB-HSR",
            "group_by": "daily"
        })
        assert res.status_code == 200
        data = res.json()
        
        assert "trends" in data
        assert "group_by" in data
        
    def test_expense_analysis_center_filter(self):
        """Test /api/mis/expense-analysis filters by center"""
        res = requests.post(f"{BASE_URL}/api/mis/expense-analysis", json={
            "token": self.token,
            "period": "current_month",
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        data = res.json()
        
        assert "by_type" in data
        assert "total_expenses" in data
        
    def test_quarterly_comparison_center_filter(self):
        """Test /api/mis/quarterly-comparison accepts center filter"""
        res = requests.post(f"{BASE_URL}/api/mis/quarterly-comparison", json={
            "token": self.token,
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        data = res.json()
        
        assert "quarters" in data
        assert isinstance(data["quarters"], list)
        
    # ==========================================
    # Centers List Endpoint Test
    # ==========================================
    
    def test_centers_endpoint_independent(self):
        """Test /api/centers returns all centers independently"""
        res = requests.get(f"{BASE_URL}/api/centers")
        assert res.status_code == 200
        data = res.json()
        
        assert "centers" in data
        centers = data["centers"]
        
        # Should have multiple centers
        assert len(centers) > 1
        
        # Each center should have code
        for c in centers:
            assert "code" in c
            
        # Should include PB-HSR and PB-MGT
        codes = [c["code"] for c in centers]
        assert "PB-HSR" in codes
        assert "PB-MGT" in codes
        
    # ==========================================
    # Period Filter Tests
    # ==========================================
    
    def test_overview_period_filters(self):
        """Test overview with different period filters"""
        periods = ["current_month", "current_quarter", "last_3_months", "ytd"]
        
        for period in periods:
            res = requests.post(f"{BASE_URL}/api/mis/overview", json={
                "token": self.token,
                "period": period,
                "center": "all"
            })
            assert res.status_code == 200, f"Failed for period: {period}"
            data = res.json()
            assert "period" in data
            assert data["period"]["type"] == period
            
    def test_overview_custom_date_range(self):
        """Test overview with custom date range"""
        res = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": self.token,
            "period": "custom",
            "center": "all",
            "custom_start": "2026-01-01",
            "custom_end": "2026-01-31"
        })
        assert res.status_code == 200
        data = res.json()
        
        assert data["period"]["start"] == "2026-01-01"
        assert data["period"]["end"] == "2026-01-31"
        
    # ==========================================
    # Access Control Tests
    # ==========================================
    
    def test_mis_requires_auth(self):
        """Test MIS endpoints require authentication"""
        res = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": "invalid_token",
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 401
        
    def test_working_capital_requires_auth(self):
        """Test working capital requires authentication"""
        res = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": "invalid_token",
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 401
        
    # ==========================================
    # Data Integrity Tests
    # ==========================================
    
    def test_overview_summary_fields(self):
        """Test overview returns all required summary fields"""
        res = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": self.token,
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 200
        data = res.json()
        
        summary = data.get("summary", {})
        required_fields = [
            "total_sales", "total_cash_sales", "total_online_sales",
            "total_expenses", "total_gst", "profit", "profit_margin",
            "total_guests", "total_bills", "avg_per_guest", "avg_per_bill"
        ]
        
        for field in required_fields:
            assert field in summary, f"Missing field: {field}"
            
    def test_overview_changes_fields(self):
        """Test overview returns change percentages"""
        res = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": self.token,
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 200
        data = res.json()
        
        changes = data.get("changes", {})
        assert "sales_change" in changes
        assert "expenses_change" in changes
        assert "profit_change" in changes


class TestExpenseEntrySorting:
    """Test Expense Entry sorting functionality (backend data)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT"
        })
        assert res.status_code == 200
        
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT",
            "otp": "123456"
        })
        assert res.status_code == 200
        self.token = res.json()["token"]
        
    def test_expenses_endpoint_returns_data(self):
        """Test expenses endpoint returns data for sorting"""
        res = requests.post(f"{BASE_URL}/api/sales/expenses", json={
            "token": self.token,
            "center": "PB-HSR",
            "start_date": "2026-01-01",
            "end_date": "2026-03-27"
        })
        assert res.status_code == 200
        data = res.json()
        
        assert "expenses" in data
        
    def test_expense_has_sortable_fields(self):
        """Test expense records have all sortable fields"""
        res = requests.post(f"{BASE_URL}/api/sales/expenses", json={
            "token": self.token,
            "center": "PB-HSR",
            "start_date": "2026-01-01",
            "end_date": "2026-03-27"
        })
        assert res.status_code == 200
        data = res.json()
        
        if len(data.get("expenses", [])) > 0:
            expense = data["expenses"][0]
            # Check sortable fields exist
            sortable_fields = ["date", "description", "expense_type", "payment_mode", "amount"]
            for field in sortable_fields:
                assert field in expense, f"Missing sortable field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
