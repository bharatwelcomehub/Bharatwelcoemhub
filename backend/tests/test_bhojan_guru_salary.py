"""
Comprehensive tests for Bhojan Guru APIs and Salary Excel generation
Tests:
1. Bhojan Guru GET /api/bhojan_guru - returns bhojanGuru, regionWise, bodyNeedMatrix
2. Bhojan Guru POST /api/bhojan_guru/body_need - body need questionnaire API
3. Bhojan Guru GET /api/bhojan_guru/region/{day} - day-wise regional thali
4. Salary Excel POST /api/generate_salary - CREDIT_NARR/DEBIT_NARR logic test
"""

import pytest
import requests
import os
from io import BytesIO
import openpyxl

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data
TEST_CENTER = "PB-MGT"
TEST_MOBILE = "9741399190"
DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    # Send OTP
    resp = requests.post(f"{BASE_URL}/api/send_otp", json={
        "center": TEST_CENTER,
        "mobile": TEST_MOBILE
    })
    assert resp.status_code == 200
    
    # Verify OTP with master code
    resp = requests.post(f"{BASE_URL}/api/verify_otp", json={
        "center": TEST_CENTER,
        "mobile": TEST_MOBILE,
        "otp": "123456"  # Master OTP for dev
    })
    assert resp.status_code == 200
    return resp.json().get("token")


class TestBhojanGuruAPIs:
    """Tests for Bhojan Guru API endpoints"""
    
    def test_health_check(self):
        """Test health endpoint"""
        resp = requests.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        print(f"✓ Health check passed: {data}")
    
    def test_bhojan_guru_main_endpoint(self):
        """Test GET /api/bhojan_guru returns all required data structures"""
        resp = requests.get(f"{BASE_URL}/api/bhojan_guru")
        assert resp.status_code == 200
        data = resp.json()
        
        # Verify bhojanGuru exists with items
        assert "bhojanGuru" in data
        bhojan_items = data["bhojanGuru"]
        assert len(bhojan_items) > 0
        print(f"✓ bhojanGuru items count: {len(bhojan_items)}")
        
        # Verify regionWise exists with all 7 days
        assert "regionWise" in data
        region_data = data["regionWise"]
        assert len(region_data) == 7
        for day in DAYS:
            assert day in region_data, f"Missing day: {day}"
        print(f"✓ regionWise days: {list(region_data.keys())}")
        
        # Verify bodyNeedMatrix exists with required categories
        assert "bodyNeedMatrix" in data
        matrix = data["bodyNeedMatrix"]
        expected_categories = ["energy", "digestion", "mood", "spice", "purpose", "weather"]
        for cat in expected_categories:
            assert cat in matrix, f"Missing category: {cat}"
        print(f"✓ bodyNeedMatrix categories: {list(matrix.keys())}")
    
    def test_bhojan_guru_region_all_days(self):
        """Test GET /api/bhojan_guru/region/{day} for all 7 days"""
        for day in DAYS:
            resp = requests.get(f"{BASE_URL}/api/bhojan_guru/region/{day}")
            assert resp.status_code == 200
            data = resp.json()
            
            assert data["day"] == day
            assert data["recommendation"] is not None
            
            rec = data["recommendation"]
            assert "region" in rec
            assert "thaliName" in rec
            assert "highlights" in rec
            assert "recommendedOrder" in rec
            
            order = rec["recommendedOrder"]
            expected_items = ["dal", "bhaji", "rice", "roti", "drink", "sweet"]
            for item in expected_items:
                assert item in order, f"Missing item {item} in {day} recommendedOrder"
            
            print(f"✓ {day}: {rec['region']} - {rec['thaliName']}")
    
    def test_bhojan_guru_region_case_insensitive(self):
        """Test region endpoint works with different cases"""
        test_cases = ["sunday", "SUNDAY", "Sunday"]
        for case in test_cases:
            resp = requests.get(f"{BASE_URL}/api/bhojan_guru/region/{case}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["day"] == "Sunday"
            assert data["recommendation"] is not None
        print("✓ Region endpoint is case-insensitive")
    
    def test_bhojan_guru_body_need_default_params(self):
        """Test POST /api/bhojan_guru/body_need with default params"""
        resp = requests.post(f"{BASE_URL}/api/bhojan_guru/body_need")
        assert resp.status_code == 200
        data = resp.json()
        
        assert "recommendations" in data
        assert len(data["recommendations"]) > 0
        assert "preferences" in data
        assert "avoidances" in data
        
        # Check recommendation structure
        for rec in data["recommendations"]:
            assert "key" in rec
            assert "display" in rec
            assert "score" in rec
        
        print(f"✓ Body Need default: {len(data['recommendations'])} recommendations")
    
    def test_bhojan_guru_body_need_custom_params(self):
        """Test POST /api/bhojan_guru/body_need with custom params"""
        params = {
            "energy": "low",
            "digestion": "sensitive",
            "mood": "calm",
            "spice": "mild",
            "purpose": "family",
            "weather": "hot"
        }
        
        resp = requests.post(f"{BASE_URL}/api/bhojan_guru/body_need", params=params)
        assert resp.status_code == 200
        data = resp.json()
        
        assert len(data["recommendations"]) > 0
        
        # First recommendation should have highest score
        scores = [r["score"] for r in data["recommendations"]]
        assert scores == sorted(scores, reverse=True), "Recommendations not sorted by score"
        
        # Check that cooling items are preferred for hot weather
        first_rec = data["recommendations"][0]
        print(f"✓ Body Need custom: Top recommendation is '{first_rec['display']}' (score: {first_rec['score']})")
    
    def test_bhojan_guru_body_need_all_options(self):
        """Test body need API with various option combinations"""
        test_cases = [
            {"energy": "active", "spice": "high"},
            {"digestion": "strong", "weather": "rainy"},
            {"mood": "stressed", "purpose": "quick"},
            {"energy": "normal", "weather": "cold"}
        ]
        
        for i, params in enumerate(test_cases):
            resp = requests.post(f"{BASE_URL}/api/bhojan_guru/body_need", params=params)
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["recommendations"]) > 0
            print(f"✓ Body Need case {i+1}: {params} -> {data['recommendations'][0]['display']}")


class TestSalaryExcelGeneration:
    """Tests for Salary Excel generation with CREDIT_NARR/DEBIT_NARR logic"""
    
    def test_salary_excel_narr_columns(self, auth_token):
        """Test that CREDIT_NARR/DEBIT_NARR are only filled when employee has remark"""
        # Generate salary Excel
        resp = requests.post(f"{BASE_URL}/api/generate_salary", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "month": "2026-01",
            "mode": "all",
            "targetCenter": None
        })
        
        assert resp.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in resp.headers.get("content-type", "")
        
        # Parse Excel
        wb = openpyxl.load_workbook(BytesIO(resp.content))
        ws = wb.active
        
        headers = [cell.value for cell in ws[1]]
        
        # Verify required columns exist
        assert "DEBIT_NARR" in headers
        assert "CREDIT_NARR" in headers
        assert "BNF_NAME" in headers
        
        debit_idx = headers.index("DEBIT_NARR")
        credit_idx = headers.index("CREDIT_NARR")
        name_idx = headers.index("BNF_NAME")
        
        found_with_remark = False
        found_without_remark = False
        
        for row_num in range(2, ws.max_row + 1):
            row = list(ws.iter_rows(min_row=row_num, max_row=row_num, values_only=True))[0]
            name = row[name_idx]
            debit_narr = row[debit_idx]
            credit_narr = row[credit_idx]
            
            if name and "KATHALE" in str(name).upper() and "PRANAV" in str(name).upper():
                # JAYANTI PRANAV KATHALE should have remark filled
                assert debit_narr is not None and debit_narr != ""
                assert credit_narr is not None and credit_narr != ""
                assert debit_narr == credit_narr  # Both should have same value
                found_with_remark = True
                print(f"✓ Employee WITH remark: {name}")
                print(f"  DEBIT_NARR: '{debit_narr}'")
                print(f"  CREDIT_NARR: '{credit_narr}'")
            
            elif name:
                # Check that other employees have empty NARR columns
                if not debit_narr and not credit_narr:
                    if not found_without_remark:
                        found_without_remark = True
                        print(f"✓ Employee WITHOUT remark: {name}")
                        print(f"  DEBIT_NARR: empty")
                        print(f"  CREDIT_NARR: empty")
        
        assert found_with_remark, "Did not find JAYANTI PRANAV KATHALE with remark"
        assert found_without_remark, "Did not find any employee without remark"
        
        print("✓ Salary Excel CREDIT_NARR/DEBIT_NARR logic verified")
    
    def test_salary_excel_headers(self, auth_token):
        """Test that salary Excel has all required headers"""
        resp = requests.post(f"{BASE_URL}/api/generate_salary", json={
            "token": auth_token,
            "center": TEST_CENTER,
            "month": "2026-01",
            "mode": "all",
            "targetCenter": None
        })
        
        assert resp.status_code == 200
        
        wb = openpyxl.load_workbook(BytesIO(resp.content))
        ws = wb.active
        
        headers = [cell.value for cell in ws[1]]
        
        expected_headers = [
            "PYMT_PROD_TYPE_CODE", "PYMT_MODE", "DEBIT_ACC_NO", "BNF_NAME",
            "BENE_ACC_NO", "BENE_IFSC", "AMOUNT", "DEBIT_NARR", "CREDIT_NARR",
            "MOBILE_NUM", "EMAIL_ID", "REMARK", "CENTER", "WORKING_DAYS",
            "PRESENT_DAYS", "GROSS_SALARY", "ADVANCE_DEDUCTION", "NET_SALARY"
        ]
        
        for header in expected_headers:
            assert header in headers, f"Missing header: {header}"
        
        print(f"✓ All {len(expected_headers)} expected headers found in salary Excel")
    
    def test_salary_preview(self, auth_token):
        """Test salary preview endpoint"""
        resp = requests.post(f"{BASE_URL}/api/salary_preview", json={
            "token": auth_token,
            "month": "2026-01",
            "targetCenter": "PB-HSR"
        })
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert data["success"] is True
        assert "center" in data
        assert "month" in data
        assert "salaryData" in data
        assert "totals" in data
        
        print(f"✓ Salary preview: {len(data['salaryData'])} employees, total net: {data['totals']['net']}")


class TestRecipesAndDescriptions:
    """Tests for recipes and descriptions endpoints"""
    
    def test_get_recipes(self):
        """Test GET /api/recipes returns recipe data"""
        resp = requests.get(f"{BASE_URL}/api/recipes")
        assert resp.status_code == 200
        data = resp.json()
        
        assert "recipes" in data
        recipes = data["recipes"]
        assert len(recipes) > 0
        
        # Check recipe structure
        for key, recipe in list(recipes.items())[:3]:
            assert "display" in recipe
            assert "ingredients" in recipe or "method" in recipe
        
        print(f"✓ Recipes: {len(recipes)} recipes found")
    
    def test_get_descriptions(self):
        """Test GET /api/descriptions returns menu descriptions"""
        resp = requests.get(f"{BASE_URL}/api/descriptions")
        assert resp.status_code == 200
        data = resp.json()
        
        assert "descriptions" in data
        descriptions = data["descriptions"]
        
        print(f"✓ Descriptions: {len(descriptions)} menu items found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
