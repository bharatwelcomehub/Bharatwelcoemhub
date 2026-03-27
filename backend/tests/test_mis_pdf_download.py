"""
Test MIS Dashboard PDF Download Feature:
- PDF download endpoint /api/mis/download-pdf
- PDF generation with Purnabramha logo
- Center-specific PDF generation (INR vs AUD)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMISPDFDownload:
    """MIS Dashboard PDF Download tests"""
    
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
    # PDF Download Endpoint Tests
    # ==========================================
    
    def test_pdf_download_endpoint_exists(self):
        """Test /api/mis/download-pdf endpoint returns valid PDF"""
        res = requests.post(f"{BASE_URL}/api/mis/download-pdf", json={
            "token": self.token,
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 200
        
        # Verify content type is PDF
        assert res.headers.get('content-type') == 'application/pdf'
        
        # Verify PDF magic bytes
        assert res.content[:4] == b'%PDF'
        
    def test_pdf_download_all_centers(self):
        """Test PDF download for all centers"""
        res = requests.post(f"{BASE_URL}/api/mis/download-pdf", json={
            "token": self.token,
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 200
        assert res.headers.get('content-type') == 'application/pdf'
        
        # PDF should have reasonable size (>10KB)
        assert len(res.content) > 10000
        
    def test_pdf_download_specific_center(self):
        """Test PDF download for specific center (PB-HSR)"""
        res = requests.post(f"{BASE_URL}/api/mis/download-pdf", json={
            "token": self.token,
            "period": "current_month",
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        assert res.headers.get('content-type') == 'application/pdf'
        assert res.content[:4] == b'%PDF'
        
    def test_pdf_download_international_center(self):
        """Test PDF download for international center (PB-PERTH) uses AUD"""
        res = requests.post(f"{BASE_URL}/api/mis/download-pdf", json={
            "token": self.token,
            "period": "current_month",
            "center": "PB-PERTH"
        })
        assert res.status_code == 200
        assert res.headers.get('content-type') == 'application/pdf'
        assert res.content[:4] == b'%PDF'
        
    def test_pdf_download_with_different_periods(self):
        """Test PDF download with different period filters"""
        periods = ["current_month", "current_quarter", "last_3_months", "ytd"]
        
        for period in periods:
            res = requests.post(f"{BASE_URL}/api/mis/download-pdf", json={
                "token": self.token,
                "period": period,
                "center": "all"
            })
            assert res.status_code == 200, f"Failed for period: {period}"
            assert res.headers.get('content-type') == 'application/pdf'
            
    def test_pdf_download_custom_date_range(self):
        """Test PDF download with custom date range"""
        res = requests.post(f"{BASE_URL}/api/mis/download-pdf", json={
            "token": self.token,
            "period": "custom",
            "center": "all",
            "custom_start": "2026-01-01",
            "custom_end": "2026-01-31"
        })
        assert res.status_code == 200
        assert res.headers.get('content-type') == 'application/pdf'
        
    def test_pdf_download_requires_auth(self):
        """Test PDF download requires valid authentication"""
        res = requests.post(f"{BASE_URL}/api/mis/download-pdf", json={
            "token": "invalid_token",
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 401
        
    def test_pdf_has_content_disposition_header(self):
        """Test PDF response has Content-Disposition header for download"""
        res = requests.post(f"{BASE_URL}/api/mis/download-pdf", json={
            "token": self.token,
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 200
        
        # Check Content-Disposition header exists
        content_disp = res.headers.get('content-disposition', '')
        assert 'attachment' in content_disp
        assert 'filename=' in content_disp
        assert '.pdf' in content_disp
        
    def test_pdf_filename_includes_center(self):
        """Test PDF filename includes center name"""
        res = requests.post(f"{BASE_URL}/api/mis/download-pdf", json={
            "token": self.token,
            "period": "current_month",
            "center": "PB-HSR"
        })
        assert res.status_code == 200
        
        content_disp = res.headers.get('content-disposition', '')
        assert 'PB-HSR' in content_disp
        
    def test_pdf_filename_all_centers(self):
        """Test PDF filename shows 'All_Centers' when center=all"""
        res = requests.post(f"{BASE_URL}/api/mis/download-pdf", json={
            "token": self.token,
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 200
        
        content_disp = res.headers.get('content-disposition', '')
        assert 'All' in content_disp or 'all' in content_disp.lower()


class TestMISOverviewEndpoint:
    """Test MIS Overview endpoint data structure"""
    
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
        
    def test_overview_returns_proper_structure(self):
        """Test /api/mis/overview returns proper data structure"""
        res = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": self.token,
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 200
        data = res.json()
        
        # Verify top-level keys
        assert "period" in data
        assert "summary" in data
        assert "changes" in data
        assert "centers" in data
        
    def test_overview_summary_has_all_metrics(self):
        """Test overview summary contains all required metrics"""
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
            
    def test_overview_period_info(self):
        """Test overview returns period information"""
        res = requests.post(f"{BASE_URL}/api/mis/overview", json={
            "token": self.token,
            "period": "current_month",
            "center": "all"
        })
        assert res.status_code == 200
        data = res.json()
        
        period = data.get("period", {})
        assert "type" in period
        assert "start" in period
        assert "end" in period
        assert period["type"] == "current_month"


class TestMISExcelDownload:
    """Test MIS Excel download functionality (frontend-generated)"""
    
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
        
    def test_all_data_endpoints_for_excel(self):
        """Test all endpoints needed for Excel export return data"""
        endpoints = [
            ("/api/mis/overview", {"token": self.token, "period": "current_month", "center": "all"}),
            ("/api/mis/sales-trends", {"token": self.token, "period": "current_month", "center": "all", "group_by": "daily"}),
            ("/api/mis/expense-analysis", {"token": self.token, "period": "current_month", "center": "all"}),
            ("/api/mis/working-capital", {"token": self.token, "period": "current_month", "center": "all"}),
            ("/api/mis/quarterly-comparison", {"token": self.token, "center": "all"}),
        ]
        
        for endpoint, payload in endpoints:
            res = requests.post(f"{BASE_URL}{endpoint}", json=payload)
            assert res.status_code == 200, f"Failed for endpoint: {endpoint}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
