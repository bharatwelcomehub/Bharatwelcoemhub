"""
Test International Attendance Update Rate Feature and Related Endpoints
Tests: Update hourly rate, week data loading, centers endpoint, payslip PDF generation
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestInternationalAttendanceUpdateRate:
    """Tests for International Attendance Update Rate feature"""
    
    @pytest.fixture(scope="class")
    def perth_token(self):
        """Get Perth manager token"""
        # Send OTP
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": "PB-PERTH",
            "mobile": "0401832922"
        })
        assert res.status_code == 200
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": "PB-PERTH",
            "mobile": "0401832922",
            "otp": "123456"
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        return data.get("token")
    
    @pytest.fixture(scope="class")
    def mgt_token(self):
        """Get MGT super admin token"""
        # Send OTP
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190"
        })
        assert res.status_code == 200
        
        # Verify OTP
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190",
            "otp": "123456"
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") == True
        assert data.get("is_super_admin") == True
        return data.get("token")
    
    def test_international_centers_endpoint(self, perth_token):
        """Test GET /api/international-attendance/centers returns only 1 PB-PERTH"""
        res = requests.get(f"{BASE_URL}/api/international-attendance/centers", params={
            "token": perth_token
        })
        assert res.status_code == 200
        data = res.json()
        
        assert data.get("success") == True
        assert "centers" in data
        
        # Verify only 1 PB-PERTH center exists (duplicate fix verification)
        perth_centers = [c for c in data["centers"] if c.get("code") == "PB-PERTH"]
        assert len(perth_centers) == 1, f"Expected 1 PB-PERTH center, found {len(perth_centers)}"
        
        # Verify center details
        perth = perth_centers[0]
        assert perth.get("country") == "Australia"
        print(f"PASS: Only 1 PB-PERTH center exists with country=Australia")
    
    def test_week_data_loads_correctly(self, perth_token):
        """Test POST /api/international-attendance/week-data returns employees with hours"""
        res = requests.post(f"{BASE_URL}/api/international-attendance/week-data", json={
            "token": perth_token,
            "center": "PB-PERTH",
            "year": 2026,
            "month": 3,
            "week": 1
        })
        assert res.status_code == 200
        data = res.json()
        
        assert data.get("success") == True
        assert "employees" in data
        assert "week_dates" in data
        assert "summary" in data
        
        # Verify employees have required fields
        employees = data["employees"]
        assert len(employees) > 0, "Expected at least 1 employee"
        
        for emp in employees:
            assert "employee_id" in emp
            assert "employee_name" in emp
            assert "hourly_rate" in emp
            assert "hours" in emp
            assert isinstance(emp["hourly_rate"], (int, float))
            assert emp["hourly_rate"] >= 0
        
        # Verify week_dates has 7 days
        assert len(data["week_dates"]) == 7
        
        print(f"PASS: Week data loaded with {len(employees)} employees")
    
    def test_update_rate_endpoint_success(self, perth_token):
        """Test POST /api/international-attendance/update-rate with JSON body"""
        # First get current rate
        res = requests.post(f"{BASE_URL}/api/international-attendance/week-data", json={
            "token": perth_token,
            "center": "PB-PERTH",
            "year": 2026,
            "month": 3,
            "week": 1
        })
        assert res.status_code == 200
        employees = res.json().get("employees", [])
        
        # Find PERTH-C001 (Sneha Patel)
        emp = next((e for e in employees if e["employee_id"] == "PERTH-C001"), None)
        if not emp:
            emp = employees[0] if employees else None
        
        assert emp is not None, "No employees found to test rate update"
        
        original_rate = emp["hourly_rate"]
        new_rate = 31.0 if original_rate != 31.0 else 30.0
        
        # Update rate using JSON body (not query params)
        res = requests.post(f"{BASE_URL}/api/international-attendance/update-rate", json={
            "token": perth_token,
            "center": "PB-PERTH",
            "employee_id": emp["employee_id"],
            "new_rate": new_rate
        })
        assert res.status_code == 200
        data = res.json()
        
        assert data.get("success") == True
        assert "message" in data
        assert f"${new_rate:.2f}" in data["message"]
        
        # Verify rate was updated by fetching week data again
        res = requests.post(f"{BASE_URL}/api/international-attendance/week-data", json={
            "token": perth_token,
            "center": "PB-PERTH",
            "year": 2026,
            "month": 3,
            "week": 1
        })
        assert res.status_code == 200
        employees = res.json().get("employees", [])
        
        updated_emp = next((e for e in employees if e["employee_id"] == emp["employee_id"]), None)
        assert updated_emp is not None
        assert updated_emp["hourly_rate"] == new_rate, f"Rate not updated: expected {new_rate}, got {updated_emp['hourly_rate']}"
        
        print(f"PASS: Rate updated from ${original_rate} to ${new_rate} for {emp['employee_id']}")
    
    def test_update_rate_negative_rate_rejected(self, perth_token):
        """Test that negative rates are rejected"""
        res = requests.post(f"{BASE_URL}/api/international-attendance/update-rate", json={
            "token": perth_token,
            "center": "PB-PERTH",
            "employee_id": "PERTH-C001",
            "new_rate": -5.0
        })
        assert res.status_code == 400
        print("PASS: Negative rate correctly rejected with 400")
    
    def test_update_rate_unauthorized_center(self, perth_token):
        """Test that Perth manager cannot update rates for other centers"""
        res = requests.post(f"{BASE_URL}/api/international-attendance/update-rate", json={
            "token": perth_token,
            "center": "PB-HSR",  # Different center
            "employee_id": "PERTH-C001",
            "new_rate": 30.0
        })
        assert res.status_code == 403
        print("PASS: Unauthorized center access correctly rejected with 403")


class TestPayslipPDFGeneration:
    """Tests for Payslip PDF generation (text overlap fix verification)"""
    
    @pytest.fixture(scope="class")
    def mgt_token(self):
        """Get MGT super admin token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190"
        })
        assert res.status_code == 200
        
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190",
            "otp": "123456"
        })
        assert res.status_code == 200
        return res.json().get("token")
    
    def test_payslip_pdf_generation_success(self, mgt_token):
        """Test POST /api/payslips_generate returns valid PDF"""
        res = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": mgt_token,
            "month": "2026-03",
            "period": "1",
            "mode": "single",
            "employeeName": "SNEHA PATEL",
            "targetCenter": "PB-PERTH",
            "fmt": "pdf"
        })
        
        assert res.status_code == 200
        
        # Verify it's a PDF
        content = res.content
        assert content[:4] == b'%PDF', "Response is not a valid PDF"
        assert len(content) > 1000, f"PDF too small ({len(content)} bytes), may be corrupted"
        
        print(f"PASS: PDF generated successfully ({len(content)} bytes)")
    
    def test_payslip_pdf_for_indian_center(self, mgt_token):
        """Test PDF generation for Indian center employee (bulk mode returns ZIP)"""
        # Bulk PDF returns a ZIP file containing multiple PDFs
        res = requests.post(f"{BASE_URL}/api/payslips_generate", json={
            "token": mgt_token,
            "month": "2026-03",
            "period": "1",
            "mode": "bulk",
            "targetCenter": "PB-HSR",
            "fmt": "pdf"
        })
        
        # May return 404 if no employees, or 200 with ZIP (bulk) or PDF (single)
        if res.status_code == 200:
            content = res.content
            # Bulk mode returns ZIP file (PK header), single mode returns PDF
            is_zip = content[:2] == b'PK'
            is_pdf = content[:4] == b'%PDF'
            assert is_zip or is_pdf, f"Response is neither PDF nor ZIP: {content[:10]}"
            file_type = "ZIP" if is_zip else "PDF"
            print(f"PASS: Bulk {file_type} generated for PB-HSR ({len(content)} bytes)")
        elif res.status_code == 404:
            print("SKIP: No employees found in PB-HSR for PDF generation")
        else:
            pytest.fail(f"Unexpected status code: {res.status_code}")


class TestDuplicatePerthCenterFix:
    """Verify duplicate PB-PERTH center was cleaned up"""
    
    @pytest.fixture(scope="class")
    def mgt_token(self):
        """Get MGT super admin token"""
        res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190"
        })
        res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": "PB-MGT",
            "mobile": "9741399190",
            "otp": "123456"
        })
        return res.json().get("token")
    
    def test_only_one_perth_center_in_centers_list(self, mgt_token):
        """Verify only 1 PB-PERTH exists in centers list"""
        res = requests.get(f"{BASE_URL}/api/centers", params={"token": mgt_token})
        
        if res.status_code == 200:
            data = res.json()
            centers = data if isinstance(data, list) else data.get("centers", [])
            perth_centers = [c for c in centers if c.get("code") == "PB-PERTH"]
            assert len(perth_centers) <= 1, f"Found {len(perth_centers)} PB-PERTH centers (duplicate not cleaned)"
            print(f"PASS: Only {len(perth_centers)} PB-PERTH center(s) in centers list")
        else:
            # Try international centers endpoint
            res = requests.get(f"{BASE_URL}/api/international-attendance/centers", params={"token": mgt_token})
            assert res.status_code == 200
            data = res.json()
            perth_centers = [c for c in data.get("centers", []) if c.get("code") == "PB-PERTH"]
            assert len(perth_centers) == 1, f"Found {len(perth_centers)} PB-PERTH centers"
            print(f"PASS: Only 1 PB-PERTH center in international centers")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
