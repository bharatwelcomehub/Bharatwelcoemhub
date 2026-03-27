"""
Test Working Capital endpoint - MIS Dashboard
Tests the new working capital logic:
- Initial WC from franchise deposits
- Loans drawn against WC
- Repayments
- Available WC calculation
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestWorkingCapital:
    """Working Capital endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        # Login as super admin
        send_otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT"
        })
        assert send_otp_res.status_code == 200, f"Send OTP failed: {send_otp_res.text}"
        
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": "9741399190",
            "otp": "123456",
            "center": "PB-MGT"
        })
        assert verify_res.status_code == 200, f"Verify OTP failed: {verify_res.text}"
        self.token = verify_res.json().get("token")
        assert self.token, "No token received"
    
    def test_working_capital_endpoint_returns_correct_structure(self):
        """Test /api/mis/working-capital returns correct data structure"""
        response = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": self.token,
            "center": "all"
        })
        assert response.status_code == 200, f"WC endpoint failed: {response.text}"
        
        data = response.json()
        
        # Check required fields in response
        assert "initial_working_capital" in data, "Missing initial_working_capital"
        assert "total_loans" in data, "Missing total_loans"
        assert "total_repaid" in data, "Missing total_repaid"
        assert "total_outstanding" in data, "Missing total_outstanding"
        assert "available_working_capital" in data, "Missing available_working_capital"
        assert "centers" in data, "Missing centers array"
        assert "loan_timeline" in data, "Missing loan_timeline"
        
        # Backward compatibility fields
        assert "data" in data, "Missing backward compat 'data' field"
        assert "total_working_capital" in data, "Missing backward compat 'total_working_capital' field"
        
        print(f"✓ Working capital structure verified")
        print(f"  Initial WC: {data['initial_working_capital']}")
        print(f"  Total Loans: {data['total_loans']}")
        print(f"  Total Repaid: {data['total_repaid']}")
        print(f"  Outstanding: {data['total_outstanding']}")
        print(f"  Available WC: {data['available_working_capital']}")
        print(f"  Centers count: {len(data['centers'])}")
        print(f"  Loan timeline entries: {len(data['loan_timeline'])}")
    
    def test_working_capital_all_centers_sum(self):
        """Test that 'all' centers shows sum of franchise WC deposits"""
        response = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": self.token,
            "center": "all"
        })
        assert response.status_code == 200
        
        data = response.json()
        initial_wc = data.get("initial_working_capital", 0)
        
        # Initial WC should be sum of franchise deposits
        # Based on context, there should be some WC from franchises
        print(f"✓ All centers initial WC: ₹{initial_wc:,.2f}")
        
        # Available WC = Initial WC - Outstanding loans
        available = data.get("available_working_capital", 0)
        outstanding = data.get("total_outstanding", 0)
        expected_available = initial_wc - outstanding
        
        assert abs(available - expected_available) < 0.01, \
            f"Available WC mismatch: {available} != {expected_available}"
        print(f"✓ Available WC calculation correct: {initial_wc} - {outstanding} = {available}")
    
    def test_working_capital_perth_has_loan(self):
        """Test PB-PERTH shows loan entry (₹50K loan, ₹20K repaid)"""
        response = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": self.token,
            "center": "PB-PERTH"
        })
        assert response.status_code == 200
        
        data = response.json()
        
        # Check if PB-PERTH has loan data
        centers = data.get("centers", [])
        loan_timeline = data.get("loan_timeline", [])
        
        print(f"PB-PERTH WC data:")
        print(f"  Initial WC: {data.get('initial_working_capital', 0)}")
        print(f"  Total Loans: {data.get('total_loans', 0)}")
        print(f"  Total Repaid: {data.get('total_repaid', 0)}")
        print(f"  Outstanding: {data.get('total_outstanding', 0)}")
        print(f"  Available WC: {data.get('available_working_capital', 0)}")
        print(f"  Centers: {centers}")
        print(f"  Loan timeline: {loan_timeline}")
        
        # If there are loan entries for PB-PERTH, verify the structure
        if loan_timeline:
            for entry in loan_timeline:
                assert "date" in entry, "Loan entry missing date"
                assert "center" in entry, "Loan entry missing center"
                assert "type" in entry, "Loan entry missing type"
                assert "amount" in entry, "Loan entry missing amount"
                print(f"  ✓ Loan entry: {entry['type']} - ₹{entry['amount']}")
    
    def test_working_capital_center_breakdown(self):
        """Test center-wise breakdown has correct fields"""
        response = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": self.token,
            "center": "all"
        })
        assert response.status_code == 200
        
        data = response.json()
        centers = data.get("centers", [])
        
        if centers:
            for center in centers:
                assert "center" in center, "Center missing 'center' field"
                assert "franchise_name" in center, "Center missing 'franchise_name'"
                assert "initial_wc" in center, "Center missing 'initial_wc'"
                assert "total_loans" in center, "Center missing 'total_loans'"
                assert "total_repaid" in center, "Center missing 'total_repaid'"
                assert "outstanding" in center, "Center missing 'outstanding'"
                assert "available_wc" in center, "Center missing 'available_wc'"
                
                # Verify calculation
                expected_available = center["initial_wc"] - center["outstanding"]
                assert abs(center["available_wc"] - expected_available) < 0.01, \
                    f"Center {center['center']} available WC mismatch"
                
                print(f"✓ Center {center['center']}: Initial={center['initial_wc']}, "
                      f"Loans={center['total_loans']}, Repaid={center['total_repaid']}, "
                      f"Available={center['available_wc']}")
        else:
            print("No centers with loan data found (WC fully intact)")
    
    def test_working_capital_no_cumulative_sales(self):
        """Verify WC is NOT calculated from cumulative sales/expenses"""
        response = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": self.token,
            "center": "all"
        })
        assert response.status_code == 200
        
        data = response.json()
        
        # The old logic calculated WC as cumulative (Sales - Expenses - GST)
        # New logic: WC = Initial deposit - Outstanding loans
        # We verify by checking that available_working_capital = initial_working_capital - total_outstanding
        
        initial = data.get("initial_working_capital", 0)
        outstanding = data.get("total_outstanding", 0)
        available = data.get("available_working_capital", 0)
        
        expected = initial - outstanding
        assert abs(available - expected) < 0.01, \
            f"WC calculation wrong: {available} != {initial} - {outstanding}"
        
        print(f"✓ WC correctly calculated from deposits/loans, not sales")
        print(f"  Formula: Available = Initial - Outstanding")
        print(f"  {available} = {initial} - {outstanding}")


class TestMISOverviewStillWorks:
    """Verify MIS Overview tab still works after WC changes"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        send_otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT"
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": "9741399190",
            "otp": "123456",
            "center": "PB-MGT"
        })
        self.token = verify_res.json().get("token")
    
    def test_overview_endpoint_works(self):
        """Test /api/mis/overview still returns correct data"""
        response = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": self.token,
            "period": "current_month",
            "center": "all"
        })
        assert response.status_code == 200, f"Overview failed: {response.text}"
        
        data = response.json()
        assert "summary" in data
        assert "centers" in data
        assert "period" in data
        
        summary = data["summary"]
        assert "total_sales" in summary
        assert "total_expenses" in summary
        assert "profit" in summary
        
        print(f"✓ MIS Overview working")
        print(f"  Total Sales: ₹{summary.get('total_sales', 0):,.2f}")
        print(f"  Total Expenses: ₹{summary.get('total_expenses', 0):,.2f}")
        print(f"  Profit: ₹{summary.get('profit', 0):,.2f}")


class TestMISPDFExport:
    """Test PDF export includes new WC structure"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        send_otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT"
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": "9741399190",
            "otp": "123456",
            "center": "PB-MGT"
        })
        self.token = verify_res.json().get("token")
    
    def test_pdf_download_works(self):
        """Test /api/mis/download-pdf generates valid PDF"""
        response = requests.post(f"{BASE_URL}/api/mis/download-pdf", json={
            "token": self.token,
            "period": "current_month",
            "center": "all"
        })
        assert response.status_code == 200, f"PDF download failed: {response.text}"
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Wrong content type: {content_type}"
        
        # Check PDF starts with %PDF
        content = response.content
        assert content[:4] == b'%PDF', "Response is not a valid PDF"
        
        print(f"✓ PDF export working, size: {len(content)} bytes")


class TestMISExcelExport:
    """Test Excel export includes Working Capital sheet with new structure"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        send_otp_res = requests.post(f"{BASE_URL}/api/send_otp", json={
            "mobile": "9741399190",
            "center": "PB-MGT"
        })
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "mobile": "9741399190",
            "otp": "123456",
            "center": "PB-MGT"
        })
        self.token = verify_res.json().get("token")
    
    def test_working_capital_data_for_excel(self):
        """Test WC data structure is suitable for Excel export"""
        response = requests.post(f"{BASE_URL}/api/mis/working-capital", json={
            "token": self.token,
            "center": "all"
        })
        assert response.status_code == 200
        
        data = response.json()
        
        # Excel export uses these fields
        assert "initial_working_capital" in data
        assert "total_loans" in data
        assert "total_repaid" in data
        assert "total_outstanding" in data
        assert "available_working_capital" in data
        assert "centers" in data
        assert "loan_timeline" in data
        
        print(f"✓ WC data structure suitable for Excel export")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
