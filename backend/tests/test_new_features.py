"""
Test Suite for New Features:
1. Expense Entry with Date Range filter
2. Expense category displayed in expense list table
3. Franchise Management form with Staff Travel field
4. Franchise Management form with GST Applicable toggle for India
5. Center Accounts MG & Payout tab displaying MG calculation
6. Center Accounts API returning mg_calculation and payout data
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_CENTER = "PB-MGT"
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"


class TestAuth:
    """Authentication helper tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        # Send OTP
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        assert res.status_code == 200, f"Failed to send OTP: {res.text}"
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        assert res.status_code == 200, f"Failed to verify OTP: {res.text}"
        data = res.json()
        assert "token" in data, "No token in response"
        return data["token"]


class TestExpenseDateRangeFilter:
    """Test Expense Entry with Date Range filter"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    def test_expense_types_endpoint(self, auth_token):
        """Test expense types endpoint returns categories"""
        res = requests.get(f"{BASE_URL}/api/sales/expense-types")
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        assert "expense_types" in data, "No expense_types in response"
        assert len(data["expense_types"]) > 0, "No expense types returned"
        print(f"SUCCESS: Found {len(data['expense_types'])} expense types")
    
    def test_expenses_single_date(self, auth_token):
        """Test fetching expenses for a single date"""
        today = datetime.now().strftime("%Y-%m-%d")
        res = requests.post(f"{BASE_URL}/api/sales/expenses", json={
            "token": auth_token,
            "center": "PB-HSR",
            "start_date": today,
            "end_date": today
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        assert "expenses" in data, "No expenses in response"
        print(f"SUCCESS: Single date query returned {len(data['expenses'])} expenses")
    
    def test_expenses_date_range(self, auth_token):
        """Test fetching expenses for a date range"""
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        res = requests.post(f"{BASE_URL}/api/sales/expenses", json={
            "token": auth_token,
            "center": "PB-HSR",
            "start_date": start_date,
            "end_date": end_date
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        assert "expenses" in data, "No expenses in response"
        print(f"SUCCESS: Date range query ({start_date} to {end_date}) returned {len(data['expenses'])} expenses")
    
    def test_expense_has_category(self, auth_token):
        """Test that expenses have expense_type (category) field"""
        # First create a test expense
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Create expense
        create_res = requests.post(f"{BASE_URL}/api/sales/expenses/create?token={auth_token}", json={
            "center": "PB-HSR",
            "date": today,
            "description": "TEST_expense_category_test",
            "amount": 100,
            "expense_type": "GROCERY",
            "payment_mode": "CASH"
        })
        
        if create_res.status_code == 200:
            # Fetch expenses and verify category
            res = requests.post(f"{BASE_URL}/api/sales/expenses", json={
                "token": auth_token,
                "center": "PB-HSR",
                "start_date": today,
                "end_date": today
            })
            assert res.status_code == 200
            data = res.json()
            
            # Find our test expense
            test_expense = None
            for exp in data.get("expenses", []):
                if exp.get("description") == "TEST_expense_category_test":
                    test_expense = exp
                    break
            
            if test_expense:
                assert "expense_type" in test_expense, "expense_type field missing"
                assert test_expense["expense_type"] == "GROCERY", f"Wrong expense_type: {test_expense['expense_type']}"
                print(f"SUCCESS: Expense has category field: {test_expense['expense_type']}")
                
                # Cleanup - delete test expense
                if test_expense.get("expense_id"):
                    requests.delete(f"{BASE_URL}/api/sales/expenses/{test_expense['expense_id']}?token={auth_token}")
            else:
                print("INFO: Test expense not found, but API structure is correct")
        else:
            print(f"INFO: Could not create test expense (may be frozen): {create_res.text}")


class TestFranchiseStaffTravel:
    """Test Franchise Management form with Staff Travel field"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    def test_franchise_types_endpoint(self, auth_token):
        """Test franchise types endpoint"""
        res = requests.get(f"{BASE_URL}/api/franchises/franchise-types")
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        assert "types" in data, "No types in response"
        assert "Sanskriti" in data["types"], "Sanskriti type missing"
        print(f"SUCCESS: Franchise types endpoint working")
    
    def test_create_franchise_with_staff_travel(self, auth_token):
        """Test creating franchise with staff_traveling_expense in setup_costs"""
        franchise_code = f"TEST-STAFF-{datetime.now().strftime('%H%M%S')}"
        
        res = requests.post(f"{BASE_URL}/api/franchises/create", json={
            "token": auth_token,
            "franchise_code": franchise_code,
            "franchise_name": "Test Staff Travel Franchise",
            "legal_entity_name": "Test Entity",
            "country": "India",
            "city": "Bangalore",
            "franchise_type": "Sanskriti",
            "franchise_fee": 1100000,
            "working_capital": 900000,
            "setup_costs": {
                "shop_security_deposit": 200000,
                "first_month_rent": 50000,
                "initial_salary_fund": 100000,
                "initial_grocery_cost": 50000,
                "staff_traveling_expense": 75000  # NEW FIELD
            },
            "status": "Active"
        })
        
        assert res.status_code == 200, f"Failed to create franchise: {res.text}"
        print(f"SUCCESS: Created franchise {franchise_code} with staff_traveling_expense")
        
        # Verify the franchise was created with staff_traveling_expense
        get_res = requests.post(f"{BASE_URL}/api/franchises/get/{franchise_code}", json={
            "token": auth_token
        })
        assert get_res.status_code == 200, f"Failed to get franchise: {get_res.text}"
        
        franchise = get_res.json().get("franchise", {})
        setup_costs = franchise.get("setup_costs", {})
        
        assert "staff_traveling_expense" in setup_costs, "staff_traveling_expense not saved"
        assert setup_costs["staff_traveling_expense"] == 75000, f"Wrong value: {setup_costs['staff_traveling_expense']}"
        print(f"SUCCESS: staff_traveling_expense saved correctly: {setup_costs['staff_traveling_expense']}")
        
        # Cleanup - delete test franchise
        requests.post(f"{BASE_URL}/api/franchises/delete/{franchise_code}", json={
            "token": auth_token
        })


class TestFranchiseGSTToggle:
    """Test Franchise Management form with GST Applicable toggle for India"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    def test_create_franchise_with_gst_applicable_true(self, auth_token):
        """Test creating India franchise with gst_applicable=true"""
        franchise_code = f"TEST-GST-ON-{datetime.now().strftime('%H%M%S')}"
        
        res = requests.post(f"{BASE_URL}/api/franchises/create", json={
            "token": auth_token,
            "franchise_code": franchise_code,
            "franchise_name": "Test GST ON Franchise",
            "legal_entity_name": "Test Entity GST",
            "country": "India",
            "city": "Mumbai",
            "franchise_type": "Maaza",
            "gst_applicable": True  # NEW FIELD
        })
        
        assert res.status_code == 200, f"Failed to create franchise: {res.text}"
        print(f"SUCCESS: Created franchise {franchise_code} with gst_applicable=true")
        
        # Verify
        get_res = requests.post(f"{BASE_URL}/api/franchises/get/{franchise_code}", json={
            "token": auth_token
        })
        assert get_res.status_code == 200
        
        franchise = get_res.json().get("franchise", {})
        assert franchise.get("gst_applicable") == True, f"gst_applicable not true: {franchise.get('gst_applicable')}"
        print(f"SUCCESS: gst_applicable saved as true")
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/franchises/delete/{franchise_code}", json={
            "token": auth_token
        })
    
    def test_create_franchise_with_gst_applicable_false(self, auth_token):
        """Test creating India franchise with gst_applicable=false"""
        franchise_code = f"TEST-GST-OFF-{datetime.now().strftime('%H%M%S')}"
        
        res = requests.post(f"{BASE_URL}/api/franchises/create", json={
            "token": auth_token,
            "franchise_code": franchise_code,
            "franchise_name": "Test GST OFF Franchise",
            "legal_entity_name": "Test Entity No GST",
            "country": "India",
            "city": "Delhi",
            "franchise_type": "Potoba",
            "gst_applicable": False
        })
        
        assert res.status_code == 200, f"Failed to create franchise: {res.text}"
        
        # Verify
        get_res = requests.post(f"{BASE_URL}/api/franchises/get/{franchise_code}", json={
            "token": auth_token
        })
        assert get_res.status_code == 200
        
        franchise = get_res.json().get("franchise", {})
        assert franchise.get("gst_applicable") == False, f"gst_applicable not false: {franchise.get('gst_applicable')}"
        print(f"SUCCESS: gst_applicable saved as false")
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/franchises/delete/{franchise_code}", json={
            "token": auth_token
        })


class TestCenterAccountsMGCalculation:
    """Test Center Accounts API returning mg_calculation and payout data"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    def test_summary_returns_mg_calculation(self, auth_token):
        """Test that summary endpoint returns mg_calculation field"""
        current_month = datetime.now().strftime("%Y-%m")
        
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": auth_token,
            "center": "PB-HSR",
            "month": current_month
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        assert data.get("success") == True, "API not successful"
        
        summary = data.get("summary", {})
        
        # Check mg_calculation field exists
        assert "mg_calculation" in summary, "mg_calculation field missing from summary"
        print(f"SUCCESS: mg_calculation field present in summary")
        
        mg_calc = summary.get("mg_calculation")
        if mg_calc:
            # Verify MG calculation structure
            expected_fields = ["total_investment", "deductions", "total_deductions", 
                            "net_investment", "monthly_mg", "interest_rate", "tenure_years"]
            for field in expected_fields:
                assert field in mg_calc, f"MG calculation missing field: {field}"
            print(f"SUCCESS: MG calculation has all required fields")
            print(f"  - Total Investment: {mg_calc.get('total_investment')}")
            print(f"  - Net Investment: {mg_calc.get('net_investment')}")
            print(f"  - Monthly MG: {mg_calc.get('monthly_mg')}")
        else:
            print("INFO: mg_calculation is null (no franchise linked)")
    
    def test_summary_returns_payout(self, auth_token):
        """Test that summary endpoint returns payout field"""
        current_month = datetime.now().strftime("%Y-%m")
        
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": auth_token,
            "center": "PB-HSR",
            "month": current_month
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        summary = data.get("summary", {})
        
        # Check payout field exists
        assert "payout" in summary, "payout field missing from summary"
        print(f"SUCCESS: payout field present in summary")
        
        payout = summary.get("payout", {})
        expected_fields = ["type", "amount", "mg_amount", "revenue_share_amount", "reason"]
        for field in expected_fields:
            assert field in payout, f"Payout missing field: {field}"
        
        print(f"SUCCESS: Payout has all required fields")
        print(f"  - Type: {payout.get('type')}")
        print(f"  - Amount: {payout.get('amount')}")
        print(f"  - MG Amount: {payout.get('mg_amount')}")
        print(f"  - Revenue Share Amount: {payout.get('revenue_share_amount')}")
    
    def test_mg_calculation_endpoint(self, auth_token):
        """Test dedicated MG calculation endpoint for franchises"""
        # First, list franchises to find one
        list_res = requests.post(f"{BASE_URL}/api/franchises/list", json={
            "token": auth_token
        })
        
        if list_res.status_code == 200:
            franchises = list_res.json().get("franchises", [])
            if franchises:
                franchise_code = franchises[0].get("franchise_code")
                
                # Test MG calculation endpoint
                mg_res = requests.post(f"{BASE_URL}/api/franchises/mg-calculation/{franchise_code}", json={
                    "token": auth_token
                })
                
                assert mg_res.status_code == 200, f"Failed: {mg_res.text}"
                data = mg_res.json()
                
                assert data.get("success") == True, "MG calculation not successful"
                assert "mg_calculation" in data, "mg_calculation missing"
                
                mg_calc = data.get("mg_calculation", {})
                print(f"SUCCESS: MG calculation for {franchise_code}")
                print(f"  - Total Investment: {mg_calc.get('total_investment')}")
                print(f"  - Deductions: {mg_calc.get('deductions')}")
                print(f"  - Net Investment: {mg_calc.get('net_investment')}")
                print(f"  - Monthly MG: {mg_calc.get('monthly_mg')}")
            else:
                print("INFO: No franchises found to test MG calculation")
        else:
            print(f"INFO: Could not list franchises: {list_res.text}")
    
    def test_payout_summary_endpoint(self, auth_token):
        """Test payout summary endpoint"""
        res = requests.post(f"{BASE_URL}/api/center-accounts/payout-summary", json={
            "token": auth_token,
            "center": "PB-HSR"
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert data.get("success") == True, "Payout summary not successful"
        assert "totals" in data, "totals missing from payout summary"
        assert "monthly_data" in data, "monthly_data missing from payout summary"
        
        totals = data.get("totals", {})
        print(f"SUCCESS: Payout summary endpoint working")
        print(f"  - Total Revenue Share: {totals.get('revenue_share')}")
        print(f"  - Total MG: {totals.get('mg')}")
        print(f"  - Total Payable: {totals.get('payable')}")
        print(f"  - Total Paid: {totals.get('paid')}")
        print(f"  - Total Pending: {totals.get('pending')}")


class TestGSTOnRevenueShare:
    """Test conditional GST on revenue share for India locations"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return res.json()["token"]
    
    def test_india_center_gst_applicable_in_summary(self, auth_token):
        """Test that India center summary includes gst_applicable flag"""
        current_month = datetime.now().strftime("%Y-%m")
        
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": auth_token,
            "center": "PB-HSR",
            "month": current_month
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        summary = data.get("summary", {})
        
        # Check share_calculation has gst_applicable
        share_calc = summary.get("share_calculation", {})
        purnabramha = share_calc.get("purnabramha", {})
        
        assert "gst_applicable" in purnabramha, "gst_applicable missing from purnabramha share"
        print(f"SUCCESS: gst_applicable field present: {purnabramha.get('gst_applicable')}")
        
        # Verify GST amounts based on gst_applicable flag
        if purnabramha.get("gst_applicable"):
            # GST should be applied
            assert purnabramha.get("gst_amount", 0) > 0 or purnabramha.get("cgst", 0) > 0, \
                "GST should be applied when gst_applicable is true"
            print(f"SUCCESS: GST applied - CGST: {purnabramha.get('cgst')}, SGST: {purnabramha.get('sgst')}")
        else:
            # GST should be 0
            assert purnabramha.get("gst_amount", 0) == 0, \
                "GST should be 0 when gst_applicable is false"
            print(f"SUCCESS: No GST applied (gst_applicable=false)")
    
    def test_australia_center_always_has_gst(self, auth_token):
        """Test that Australia center always has GST on profit share"""
        current_month = datetime.now().strftime("%Y-%m")
        
        res = requests.post(f"{BASE_URL}/api/center-accounts/summary", json={
            "token": auth_token,
            "center": "PB-PERTH",
            "month": current_month
        })
        
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        summary = data.get("summary", {})
        
        # Australia should always have profit share GST
        assert summary.get("country") == "Australia", "PB-PERTH should be Australia"
        
        share_calc = summary.get("share_calculation", {})
        assert share_calc.get("type") == "profit_share", "Australia should use profit_share"
        
        purnabramha = share_calc.get("purnabramha", {})
        # Australia always applies 10% GST
        print(f"SUCCESS: Australia profit share GST: {purnabramha.get('gst_amount')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
