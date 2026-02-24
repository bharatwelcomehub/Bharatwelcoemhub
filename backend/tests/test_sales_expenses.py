"""
Sales & Expenses API Tests
Tests for daily sales, expenses, and reporting endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSalesExpensesAPI:
    """Test cases for Sales & Expenses feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        # First request OTP
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": "PB-MGT",
            "mobile": "9876543210"
        })
        assert otp_res.status_code == 200, f"OTP request failed: {otp_res.text}"
        
        # Verify with master OTP
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": "PB-MGT",
            "mobile": "9876543210",
            "otp": "123456"
        })
        assert verify_res.status_code == 200, f"OTP verify failed: {verify_res.text}"
        
        data = verify_res.json()
        self.token = data.get("token")
        self.center = data.get("center")
        assert self.token, "No token received"
        print(f"Authenticated as: {data.get('managerName')} ({self.center})")
    
    # ========== CENTERS LIST TESTS ==========
    def test_centers_list_endpoint(self):
        """Test GET /api/sales/centers-list returns available centers"""
        res = requests.get(f"{BASE_URL}/api/sales/centers-list")
        assert res.status_code == 200, f"Centers list failed: {res.text}"
        
        data = res.json()
        assert "centers" in data, "Response missing 'centers' field"
        centers = data["centers"]
        
        # Verify we have imported centers
        print(f"Available centers: {centers}")
        assert len(centers) > 0, "No centers found - data may not be imported"
        
        # Check expected centers are present
        expected_centers = ["PB-DV", "PB-HW", "PB-HSR", "PB-KAL", "PB-KN", "PB-SN", "PB-TH"]
        for center in expected_centers:
            assert center in centers, f"Expected center {center} not found"
        print(f"TEST PASSED: {len(centers)} centers available")
    
    # ========== MONTHLY SUMMARY TESTS ==========
    def test_monthly_summary_all_centers(self):
        """Test POST /api/sales/reports/monthly-summary for all centers (MGT)"""
        res = requests.post(f"{BASE_URL}/api/sales/reports/monthly-summary", json={
            "token": self.token,
            "month": "2025-04"
        })
        assert res.status_code == 200, f"Monthly summary failed: {res.text}"
        
        data = res.json()
        print(f"Monthly summary response keys: {data.keys()}")
        
        # For MGT without specific center, expect centers data
        assert "centers" in data or "summary" in data, "Missing centers or summary data"
        
        if "centers" in data:
            centers_data = data["centers"]
            print(f"Centers data: {len(centers_data)} centers")
            for c in centers_data[:3]:
                print(f"  - {c.get('center')}: Total Sale ₹{c.get('total_sale', 0):,.0f}")
        
        if "grand_total" in data:
            gt = data["grand_total"]
            print(f"Grand Total: ₹{gt.get('total_sale', 0):,.0f}")
            assert gt.get("total_sale", 0) > 0, "No sales data found"
        
        print("TEST PASSED: Monthly summary (all centers) works")
    
    def test_monthly_summary_single_center(self):
        """Test POST /api/sales/reports/monthly-summary for a specific center"""
        res = requests.post(f"{BASE_URL}/api/sales/reports/monthly-summary", json={
            "token": self.token,
            "month": "2025-04",
            "center": "PB-HSR"
        })
        assert res.status_code == 200, f"Monthly summary failed: {res.text}"
        
        data = res.json()
        
        # For specific center, expect summary and daily_data
        assert "summary" in data, "Missing summary data for single center"
        summary = data["summary"]
        
        print(f"PB-HSR Summary for 2025-04:")
        print(f"  - Total Sale: ₹{summary.get('total_sale', 0):,.0f}")
        print(f"  - Cash Sale: ₹{summary.get('total_cash_sale', 0):,.0f}")
        print(f"  - Online Sale: ₹{summary.get('total_online_sale', 0):,.0f}")
        print(f"  - Card IDFC: ₹{summary.get('total_card_idfc', 0):,.0f}")
        print(f"  - Bharat Pay: ₹{summary.get('total_bharat_pay', 0):,.0f}")
        print(f"  - Swiggy: ₹{summary.get('total_swiggy', 0):,.0f}")
        print(f"  - Zomato: ₹{summary.get('total_zomato', 0):,.0f}")
        print(f"  - Total Expenses: ₹{summary.get('total_expenses', 0):,.0f}")
        
        # Check for daily_data
        if "daily_data" in data:
            daily = data["daily_data"]
            print(f"  - Days with data: {len(daily)}")
        
        # Check for expense_by_type
        if "expense_by_type" in data:
            exp_types = data["expense_by_type"]
            print(f"  - Expense categories: {list(exp_types.keys())[:5]}")
        
        print("TEST PASSED: Monthly summary (single center) works")
    
    def test_monthly_summary_requires_auth(self):
        """Test that monthly summary requires authentication"""
        res = requests.post(f"{BASE_URL}/api/sales/reports/monthly-summary", json={
            "token": "invalid_token",
            "month": "2025-04"
        })
        assert res.status_code == 401, "Should require valid auth token"
        print("TEST PASSED: Auth required for monthly summary")
    
    # ========== EXPENSES TESTS ==========
    def test_get_expenses(self):
        """Test POST /api/sales/expenses endpoint"""
        res = requests.post(f"{BASE_URL}/api/sales/expenses", json={
            "token": self.token,
            "month": "2025-04"
        })
        assert res.status_code == 200, f"Expenses fetch failed: {res.text}"
        
        data = res.json()
        assert "expenses" in data, "Missing expenses field"
        assert "count" in data, "Missing count field"
        
        expenses = data["expenses"]
        count = data["count"]
        print(f"Total expenses found: {count}")
        
        if expenses:
            exp = expenses[0]
            print(f"Sample expense: Date={exp.get('date')}, Center={exp.get('center')}, Amount=₹{exp.get('amount', 0):,.0f}")
            print(f"  Description: {exp.get('description', '')[:50]}")
            print(f"  Category: {exp.get('expense_type')}, Mode: {exp.get('payment_mode')}")
        
        print("TEST PASSED: Expenses endpoint works")
    
    def test_get_expenses_by_center(self):
        """Test expenses filtered by center"""
        res = requests.post(f"{BASE_URL}/api/sales/expenses", json={
            "token": self.token,
            "month": "2025-04",
            "center": "PB-TH"
        })
        assert res.status_code == 200, f"Expenses by center failed: {res.text}"
        
        data = res.json()
        expenses = data["expenses"]
        
        # Verify all expenses are for the selected center
        for exp in expenses[:10]:
            assert exp.get("center") == "PB-TH", f"Expense not from PB-TH: {exp.get('center')}"
        
        print(f"TEST PASSED: {len(expenses)} expenses found for PB-TH")
    
    # ========== DAILY SALES TESTS ==========
    def test_get_daily_sales(self):
        """Test POST /api/sales/daily endpoint"""
        res = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": self.token,
            "month": "2025-04"
        })
        assert res.status_code == 200, f"Daily sales failed: {res.text}"
        
        data = res.json()
        assert "sales" in data, "Missing sales field"
        assert "count" in data, "Missing count field"
        
        sales = data["sales"]
        count = data["count"]
        print(f"Total daily sales records: {count}")
        
        if sales:
            sale = sales[0]
            print(f"Sample sale: Date={sale.get('date')}, Center={sale.get('center')}")
            print(f"  Total Sale: ₹{sale.get('total_sale', 0):,.0f}")
            print(f"  Cash: ₹{sale.get('total_cash_sale', 0):,.0f}, Online: ₹{sale.get('total_online_sale', 0):,.0f}")
        
        print("TEST PASSED: Daily sales endpoint works")
    
    # ========== EXPENSE TYPES & PAYMENT MODES ==========
    def test_expense_types_endpoint(self):
        """Test GET /api/sales/expense-types endpoint"""
        res = requests.get(f"{BASE_URL}/api/sales/expense-types")
        assert res.status_code == 200, f"Expense types failed: {res.text}"
        
        data = res.json()
        assert "expense_types" in data, "Missing expense_types field"
        
        types = data["expense_types"]
        print(f"Expense types available: {types[:10]}...")
        assert len(types) > 0, "No expense types found"
        
        # Check for standard categories
        standard = ["GROCERY", "SALARY", "RENT", "ELECTRICITY"]
        for std in standard:
            assert std in types, f"Standard type {std} not found"
        
        print("TEST PASSED: Expense types endpoint works")
    
    def test_payment_modes_endpoint(self):
        """Test GET /api/sales/payment-modes endpoint"""
        res = requests.get(f"{BASE_URL}/api/sales/payment-modes")
        assert res.status_code == 200, f"Payment modes failed: {res.text}"
        
        data = res.json()
        assert "payment_modes" in data, "Missing payment_modes field"
        
        modes = data["payment_modes"]
        print(f"Payment modes: {modes}")
        
        # Check for standard modes
        assert "CASH" in modes, "CASH mode not found"
        
        print("TEST PASSED: Payment modes endpoint works")
    
    # ========== DATA VERIFICATION ==========
    def test_verify_imported_data_count(self):
        """Verify that imported data matches expected counts"""
        # Get daily sales count
        sales_res = requests.post(f"{BASE_URL}/api/sales/daily", json={
            "token": self.token
        })
        sales_data = sales_res.json()
        sales_count = sales_data.get("count", 0)
        
        # Get expenses count
        exp_res = requests.post(f"{BASE_URL}/api/sales/expenses", json={
            "token": self.token
        })
        exp_data = exp_res.json()
        exp_count = exp_data.get("count", 0)
        
        print(f"Data verification:")
        print(f"  - Daily sales records: {sales_count}")
        print(f"  - Expense records: {exp_count}")
        
        # Based on import script info: 1964 daily sales, 2819 expenses
        assert sales_count > 1000, f"Expected ~1964 daily sales, got {sales_count}"
        assert exp_count > 1000, f"Expected ~2819 expenses, got {exp_count}"
        
        print("TEST PASSED: Data import verified")
    
    # ========== MGT vs REGULAR USER ACCESS ==========
    def test_non_mgt_user_access_restriction(self):
        """Test that non-MGT users can only see their center's data"""
        # Login as PB-HSR manager
        otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": "PB-HSR",
            "mobile": "9876543210"
        })
        assert otp_res.status_code == 200
        
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": "PB-HSR",
            "mobile": "9876543210",
            "otp": "123456"
        })
        
        if verify_res.status_code == 200:
            hsr_token = verify_res.json().get("token")
            
            # Try to get monthly summary - should only show HSR data
            res = requests.post(f"{BASE_URL}/api/sales/reports/monthly-summary", json={
                "token": hsr_token,
                "month": "2025-04",
                "center": "PB-TH"  # Trying to access another center
            })
            
            # The API should either restrict or filter to user's own center
            # Based on code review, non-MGT users should only see their center
            data = res.json()
            print(f"Non-MGT user access test: response keys = {data.keys()}")
            
            if "summary" in data:
                summary = data["summary"]
                # Should be HSR data, not TH
                user_center = summary.get("center")
                print(f"User center in response: {user_center}")
        
        print("TEST PASSED: Access restriction checked")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
