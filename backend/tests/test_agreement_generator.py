"""
Franchise Agreement Generator Tests
Tests comprehensive agreement PDF generation for Australia and India models
User Story: Franchise agreement generator rebuilding - generating 60+ page documents

Features tested:
- PDF generation endpoint /api/franchises/generate-agreement/{franchise_code}
- Australia (FR-PERTH) agreement with 80/20 profit share, director honorarium, royalty to MFPL
- India (FR-TEST-INDIA) agreement with revenue share model and service contract fee
- Agreement structure: 8 main sections, schedules, annexures
- Dynamic data from franchise record (franchise_fee, working_capital, directors, etc.)
"""

import pytest
import requests
import os
import io
from datetime import datetime

# Try to import PyPDF2 for PDF content verification
try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials - Super Admin
TEST_CENTER = "PB-MGT"
TEST_MOBILE = "9741399190"
TEST_OTP = "123456"


class TestAgreementAuth:
    """Test authentication for agreement generation"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for Super Admin"""
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        if verify_res.status_code != 200:
            pytest.skip("Auth failed - cannot proceed")
        return verify_res.json().get("token")
    
    def test_agreement_generation_requires_auth(self):
        """Test that agreement generation requires valid token"""
        res = requests.post(
            f"{BASE_URL}/api/franchises/generate-agreement/FR-PERTH",
            json={"token": "invalid_token_xyz", "format": "pdf"}
        )
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"
        print("✓ Agreement generation requires valid auth token")
    
    def test_agreement_generation_nonexistent_franchise(self, auth_token):
        """Test agreement generation for non-existent franchise"""
        res = requests.post(
            f"{BASE_URL}/api/franchises/generate-agreement/NONEXISTENT-CODE",
            json={"token": auth_token, "format": "pdf"}
        )
        assert res.status_code == 404, f"Expected 404, got {res.status_code}"
        print("✓ Non-existent franchise returns 404")


class TestAustraliaAgreement:
    """Test FR-PERTH (Australia) agreement generation - 80/20 profit share model"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_res.json().get("token")
    
    @pytest.fixture(scope="class")
    def perth_pdf(self, auth_token):
        """Generate FR-PERTH agreement PDF"""
        res = requests.post(
            f"{BASE_URL}/api/franchises/generate-agreement/FR-PERTH",
            json={"token": auth_token, "format": "pdf"}
        )
        assert res.status_code == 200, f"PDF generation failed: {res.status_code}"
        return res
    
    def test_pdf_generated_successfully(self, perth_pdf):
        """Test that PDF is generated with correct headers"""
        assert perth_pdf.headers.get("content-type") == "application/pdf"
        
        content_disp = perth_pdf.headers.get("content-disposition", "")
        assert "attachment" in content_disp
        assert "FOCO_Agreement" in content_disp
        assert "FR-PERTH" in content_disp
        
        print(f"✓ FR-PERTH PDF generated")
        print(f"  Content-Disposition: {content_disp}")
    
    def test_pdf_valid_format(self, perth_pdf):
        """Test that PDF has valid format"""
        content = perth_pdf.content
        assert content[:4] == b'%PDF', "Not a valid PDF file"
        assert len(content) > 50000, f"PDF too small ({len(content)} bytes)"
        print(f"✓ Valid PDF format, size: {len(content)} bytes")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_pdf_has_50_plus_pages(self, perth_pdf):
        """Test that PDF has 50+ pages (comprehensive agreement)"""
        reader = PdfReader(io.BytesIO(perth_pdf.content))
        page_count = len(reader.pages)
        assert page_count >= 50, f"Expected 50+ pages, got {page_count}"
        print(f"✓ PDF has {page_count} pages (comprehensive agreement)")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_contains_australia_specific_content(self, perth_pdf):
        """Test that PDF contains Australia-specific content"""
        reader = PdfReader(io.BytesIO(perth_pdf.content))
        full_text = ''.join([page.extract_text() or '' for page in reader.pages])
        
        assert "Australia" in full_text, "Missing 'Australia'"
        assert "Perth" in full_text, "Missing 'Perth'"
        assert "PURNABRAMHA LLC" in full_text or "Purnabramha LLC" in full_text, "Missing Purnabramha LLC"
        assert "AUD" in full_text, "Missing AUD currency"
        
        print("✓ Contains Australia-specific content")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_contains_80_20_profit_share(self, perth_pdf):
        """Test that PDF contains 80/20 profit share model"""
        reader = PdfReader(io.BytesIO(perth_pdf.content))
        full_text = ''.join([page.extract_text() or '' for page in reader.pages])
        
        # Check for profit share structure section
        assert "PROFIT SHARE STRUCTURE" in full_text, "Missing profit share section"
        assert "80" in full_text, "Missing 80% reference"
        assert "20" in full_text, "Missing 20% reference"
        
        print("✓ Contains 80/20 profit share model")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_contains_director_honorarium(self, perth_pdf):
        """Test that PDF contains director honorarium section"""
        reader = PdfReader(io.BytesIO(perth_pdf.content))
        full_text = ''.join([page.extract_text() or '' for page in reader.pages])
        
        assert "Honorarium" in full_text, "Missing director honorarium"
        assert "DIRECTOR" in full_text.upper(), "Missing director reference"
        
        print("✓ Contains director honorarium section")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_contains_royalty_to_mfpl(self, perth_pdf):
        """Test that PDF contains royalty to MFPL (India)"""
        reader = PdfReader(io.BytesIO(perth_pdf.content))
        full_text = ''.join([page.extract_text() or '' for page in reader.pages])
        
        assert "MFPL" in full_text or "Manaswini" in full_text, "Missing MFPL royalty reference"
        assert "Royalty" in full_text, "Missing royalty section"
        
        print("✓ Contains royalty to MFPL section")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_contains_franchise_data(self, perth_pdf):
        """Test that PDF contains dynamic franchise data"""
        reader = PdfReader(io.BytesIO(perth_pdf.content))
        full_text = ''.join([page.extract_text() or '' for page in reader.pages])
        
        # Check for franchise-specific data
        assert "SAAVI" in full_text.upper(), "Missing legal entity name (SAAVI PTY LTD)"
        assert "ASHWINI" in full_text.upper() or "DAVARAY" in full_text.upper(), "Missing director name"
        assert "SANJAY" in full_text.upper() or "MUKHEDKAR" in full_text.upper(), "Missing director name"
        
        print("✓ Contains dynamic franchise data (directors, entity name)")


class TestIndiaAgreement:
    """Test FR-TEST-INDIA (India) agreement generation - Revenue share model"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_res.json().get("token")
    
    @pytest.fixture(scope="class")
    def india_pdf(self, auth_token):
        """Generate FR-TEST-INDIA agreement PDF"""
        res = requests.post(
            f"{BASE_URL}/api/franchises/generate-agreement/FR-TEST-INDIA",
            json={"token": auth_token, "format": "pdf"}
        )
        assert res.status_code == 200, f"PDF generation failed: {res.status_code}"
        return res
    
    def test_pdf_generated_successfully(self, india_pdf):
        """Test that PDF is generated with correct headers"""
        assert india_pdf.headers.get("content-type") == "application/pdf"
        
        content_disp = india_pdf.headers.get("content-disposition", "")
        assert "attachment" in content_disp
        assert "FOCO_Agreement" in content_disp
        assert "FR-TEST-INDIA" in content_disp
        
        print(f"✓ FR-TEST-INDIA PDF generated")
        print(f"  Content-Disposition: {content_disp}")
    
    def test_pdf_valid_format(self, india_pdf):
        """Test that PDF has valid format"""
        content = india_pdf.content
        assert content[:4] == b'%PDF', "Not a valid PDF file"
        assert len(content) > 50000, f"PDF too small ({len(content)} bytes)"
        print(f"✓ Valid PDF format, size: {len(content)} bytes")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_pdf_has_50_plus_pages(self, india_pdf):
        """Test that PDF has 50+ pages (comprehensive agreement)"""
        reader = PdfReader(io.BytesIO(india_pdf.content))
        page_count = len(reader.pages)
        assert page_count >= 50, f"Expected 50+ pages, got {page_count}"
        print(f"✓ PDF has {page_count} pages (comprehensive agreement)")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_contains_india_specific_content(self, india_pdf):
        """Test that PDF contains India-specific content"""
        reader = PdfReader(io.BytesIO(india_pdf.content))
        full_text = ''.join([page.extract_text() or '' for page in reader.pages])
        
        assert "India" in full_text, "Missing 'India'"
        assert "MANASWINI" in full_text.upper() or "MFPL" in full_text, "Missing Manaswini Foods"
        assert "Rupee" in full_text or "₹" in full_text, "Missing Rupee currency"
        
        print("✓ Contains India-specific content")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_contains_revenue_share_model(self, india_pdf):
        """Test that PDF contains revenue share model (15%)"""
        reader = PdfReader(io.BytesIO(india_pdf.content))
        full_text = ''.join([page.extract_text() or '' for page in reader.pages])
        
        assert "Revenue Share" in full_text or "revenue share" in full_text.lower(), "Missing revenue share"
        assert "15" in full_text, "Missing 15% revenue share"
        
        print("✓ Contains revenue share model (15%)")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_contains_service_contract_fee(self, india_pdf):
        """Test that PDF contains service contract fee (₹10,000)"""
        reader = PdfReader(io.BytesIO(india_pdf.content))
        full_text = ''.join([page.extract_text() or '' for page in reader.pages])
        
        assert "Service Contract" in full_text, "Missing service contract fee"
        assert "10,000" in full_text or "10000" in full_text, "Missing ₹10,000 amount"
        
        print("✓ Contains service contract fee (₹10,000/month)")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_contains_franchise_data(self, india_pdf):
        """Test that PDF contains dynamic franchise data"""
        reader = PdfReader(io.BytesIO(india_pdf.content))
        full_text = ''.join([page.extract_text() or '' for page in reader.pages])
        
        # Check for franchise-specific data
        assert "Test Foods" in full_text, "Missing legal entity name (Test Foods Pvt Ltd)"
        assert "John Doe" in full_text, "Missing director name"
        
        print("✓ Contains dynamic franchise data (directors, entity name)")


class TestAgreementStructure:
    """Test agreement structure - 8 main sections, schedules, annexures"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_res.json().get("token")
    
    @pytest.fixture(scope="class")
    def agreement_text(self, auth_token):
        """Get agreement text for structure testing"""
        res = requests.post(
            f"{BASE_URL}/api/franchises/generate-agreement/FR-PERTH",
            json={"token": auth_token, "format": "pdf"}
        )
        if res.status_code != 200 or not HAS_PYPDF2:
            return ""
        reader = PdfReader(io.BytesIO(res.content))
        return ''.join([page.extract_text() or '' for page in reader.pages])
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_has_table_of_contents(self, agreement_text):
        """Test that agreement has table of contents"""
        assert "TABLE OF CONTENTS" in agreement_text.upper(), "Missing table of contents"
        print("✓ Contains table of contents")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_has_definitions_section(self, agreement_text):
        """Test that agreement has definitions section"""
        assert "DEFINITIONS" in agreement_text.upper(), "Missing definitions section"
        assert "1.1" in agreement_text, "Missing clause 1.1"
        print("✓ Contains definitions section (Section 1)")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_has_agreement_structure_section(self, agreement_text):
        """Test that agreement has agreement structure section"""
        assert "AGREEMENT STRUCTURE" in agreement_text.upper() or "BUSINESS TRANSFER" in agreement_text.upper(), "Missing agreement structure section"
        print("✓ Contains agreement structure section (Section 2)")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_has_operational_framework_section(self, agreement_text):
        """Test that agreement has operational framework section"""
        assert "OPERATIONAL" in agreement_text.upper(), "Missing operational section"
        assert "CONTROL FRAMEWORK" in agreement_text.upper() or "OPERATIONAL STRUCTURE" in agreement_text.upper(), "Missing control framework"
        print("✓ Contains operational framework section (Section 3)")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_has_financial_framework_section(self, agreement_text):
        """Test that agreement has financial framework section"""
        assert "FINANCIAL FRAMEWORK" in agreement_text.upper(), "Missing financial framework section"
        print("✓ Contains financial framework section (Section 4)")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_has_ip_section(self, agreement_text):
        """Test that agreement has IP/confidentiality section"""
        assert "INTELLECTUAL PROPERTY" in agreement_text.upper() or "CONFIDENTIALITY" in agreement_text.upper(), "Missing IP section"
        print("✓ Contains IP & confidentiality section (Section 5)")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_has_legal_liability_section(self, agreement_text):
        """Test that agreement has legal liability section"""
        assert "LIABILITY" in agreement_text.upper() or "INSURANCE" in agreement_text.upper(), "Missing liability section"
        print("✓ Contains legal liability section (Section 6)")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_has_termination_section(self, agreement_text):
        """Test that agreement has term/termination section"""
        assert "TERMINATION" in agreement_text.upper(), "Missing termination section"
        assert "RENEWAL" in agreement_text.upper() or "TERM" in agreement_text.upper(), "Missing term section"
        print("✓ Contains term & termination section (Section 7)")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_has_dispute_resolution_section(self, agreement_text):
        """Test that agreement has dispute resolution section"""
        assert "DISPUTE" in agreement_text.upper() or "ARBITRATION" in agreement_text.upper(), "Missing dispute resolution"
        print("✓ Contains dispute resolution section (Section 8)")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_has_schedules(self, agreement_text):
        """Test that agreement has schedules A-H"""
        assert "SCHEDULE A" in agreement_text.upper() or "SCHEDULE-A" in agreement_text.upper(), "Missing Schedule A"
        assert "SCHEDULE B" in agreement_text.upper() or "SCHEDULE-B" in agreement_text.upper(), "Missing Schedule B"
        assert "SCHEDULE C" in agreement_text.upper() or "SCHEDULE-C" in agreement_text.upper(), "Missing Schedule C"
        print("✓ Contains schedules (A, B, C...)")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_has_annexures(self, agreement_text):
        """Test that agreement has annexures"""
        assert "ANNEXURE" in agreement_text.upper(), "Missing annexures"
        print("✓ Contains annexures")
    
    @pytest.mark.skipif(not HAS_PYPDF2, reason="PyPDF2 not installed")
    def test_has_signature_section(self, agreement_text):
        """Test that agreement has signature section"""
        assert "SIGNATURE" in agreement_text.upper() or "FRANCHISOR" in agreement_text.upper(), "Missing signature section"
        assert "WITNESS" in agreement_text.upper() or "EXECUTED" in agreement_text.upper(), "Missing execution section"
        print("✓ Contains signature/execution section")


class TestPDFDownloadability:
    """Test that PDF is properly downloadable"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        verify_res = requests.post(f"{BASE_URL}/api/verify_otp", json={
            "center": TEST_CENTER,
            "mobile": TEST_MOBILE,
            "otp": TEST_OTP
        })
        return verify_res.json().get("token")
    
    def test_pdf_has_content_disposition(self, auth_token):
        """Test that PDF response has proper Content-Disposition for download"""
        res = requests.post(
            f"{BASE_URL}/api/franchises/generate-agreement/FR-PERTH",
            json={"token": auth_token, "format": "pdf"}
        )
        
        assert res.status_code == 200
        content_disp = res.headers.get("content-disposition", "")
        
        assert "attachment" in content_disp, "Missing attachment directive"
        assert "filename=" in content_disp, "Missing filename"
        assert ".pdf" in content_disp, "Missing .pdf extension"
        
        print(f"✓ Content-Disposition: {content_disp}")
    
    def test_pdf_has_correct_content_type(self, auth_token):
        """Test that PDF response has correct content type"""
        res = requests.post(
            f"{BASE_URL}/api/franchises/generate-agreement/FR-PERTH",
            json={"token": auth_token, "format": "pdf"}
        )
        
        assert res.headers.get("content-type") == "application/pdf"
        print("✓ Content-Type: application/pdf")
    
    def test_pdf_content_is_complete(self, auth_token):
        """Test that PDF content is complete and not truncated"""
        res = requests.post(
            f"{BASE_URL}/api/franchises/generate-agreement/FR-PERTH",
            json={"token": auth_token, "format": "pdf"}
        )
        
        content = res.content
        # PDF should end with %%EOF
        assert b'%%EOF' in content[-100:], "PDF may be truncated (missing %%EOF)"
        print(f"✓ PDF content complete ({len(content)} bytes, ends with %%EOF)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
