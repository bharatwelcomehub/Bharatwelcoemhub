#!/usr/bin/env python3
"""
Backend API Testing for Purnabramha IntraPB
Tests all critical API endpoints for attendance and salary management system
"""

import requests
import sys
from datetime import datetime, timedelta
import json

class PurnabramhaAPITester:
    def __init__(self, base_url="https://sales-expenses-hub.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.session_data = {}
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api{endpoint}"
        request_headers = {'Content-Type': 'application/json'}
        if headers:
            request_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=request_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=request_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=request_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=request_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                try:
                    response_json = response.json() if response.content else {}
                    if response_json and len(str(response_json)) < 200:
                        print(f"   Response: {response_json}")
                except:
                    pass
                return True, response.json() if response.content else {}
            else:
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_resp = response.json() if response.content else {}
                    print(f"   Error: {error_resp}")
                except:
                    print(f"   Raw response: {response.text[:300]}")
                return False, {}

        except requests.exceptions.RequestException as e:
            print(f"❌ FAILED - Network Error: {str(e)}")
            return False, {}

    def test_basic_endpoints(self):
        """Test basic API endpoints"""
        print("\n" + "="*60)
        print("TESTING BASIC ENDPOINTS")
        print("="*60)
        
        # Health check
        self.run_test("Health Check", "GET", "/health", 200)
        
        # Root endpoint
        self.run_test("Root API", "GET", "/", 200)
        
        # Get centers
        success, response = self.run_test("Get Centers", "GET", "/centers", 200)
        if success and 'centers' in response:
            centers = response['centers']
            pb_mgt_found = any(c['code'] == 'PB-MGT' for c in centers)
            if pb_mgt_found:
                print("   ✅ PB-MGT center found in centers list")
            else:
                print("   ❌ PB-MGT center not found in centers list")

    def test_auth_flow(self):
        """Test complete authentication flow"""
        print("\n" + "="*60)
        print("TESTING AUTHENTICATION FLOW")
        print("="*60)
        
        # Test Jayanti login
        otp_data = {
            "center": "PB-MGT",
            "mobile": "9741399190"
        }
        success, response = self.run_test("Send OTP (Jayanti)", "POST", "/send_otp", 200, otp_data)
        if not success:
            print("❌ Cannot proceed without OTP sending capability")
            return False
        
        # Verify OTP with master OTP
        verify_data = {
            "center": "PB-MGT", 
            "mobile": "9741399190",
            "otp": "123456"  # Master OTP for dev
        }
        success, response = self.run_test("Verify OTP (Jayanti)", "POST", "/verify_otp", 200, verify_data)
        if success and 'token' in response:
            self.token = response['token']
            self.session_data = response
            print(f"   ✅ Jayanti login successful")
            print(f"   Manager: {response.get('managerName', 'N/A')}")
            print(f"   Center: {response.get('center', 'N/A')}")
            
            # Verify manager name
            expected_name = "Jayanti Kathale"
            actual_name = response.get('managerName', '')
            if expected_name in actual_name:
                print(f"   ✅ Manager name correct: {actual_name}")
            else:
                print(f"   ❌ Manager name incorrect. Expected: {expected_name}, Got: {actual_name}")
        else:
            print("❌ Jayanti authentication failed")
        
        # Test Sandeep login
        otp_data_sandeep = {
            "center": "PB-MGT",
            "mobile": "9960886185"
        }
        success, response = self.run_test("Send OTP (Sandeep)", "POST", "/send_otp", 200, otp_data_sandeep)
        
        verify_data_sandeep = {
            "center": "PB-MGT", 
            "mobile": "9960886185",
            "otp": "123456"  # Master OTP for dev
        }
        success, response = self.run_test("Verify OTP (Sandeep)", "POST", "/verify_otp", 200, verify_data_sandeep)
        if success and 'token' in response:
            print(f"   ✅ Sandeep login successful")
            print(f"   Manager: {response.get('managerName', 'N/A')}")
            
            # Verify manager name
            expected_name = "Sandeep Gadhwal"
            actual_name = response.get('managerName', '')
            if expected_name in actual_name:
                print(f"   ✅ Manager name correct: {actual_name}")
            else:
                print(f"   ❌ Manager name incorrect. Expected: {expected_name}, Got: {actual_name}")
            return True
        else:
            print("❌ Sandeep authentication failed")
            return self.token is not None

    def test_employee_management(self):
        """Test employee management endpoints (PB-MGT only)"""
        if not self.token:
            print("❌ No auth token - skipping employee tests")
            return
            
        print("\n" + "="*60)
        print("TESTING EMPLOYEE MANAGEMENT")
        print("="*60)
        
        # Get employees for PB-MGT center
        req_data = {"token": self.token, "center": "PB-MGT"}
        success, response = self.run_test("Get Employees for Center", "POST", "/employees", 200, req_data)
        
        # Get all employees (MGT only)
        success, response = self.run_test("Get All Employees (MGT)", "POST", "/mgt_employees_list", 200, req_data)
        if success:
            employees = response.get('employees', [])
            print(f"   Found {len(employees)} employees in system")
            
            # Test create new employee
            test_emp_data = {
                "token": self.token,
                "center": "PB-MGT",
                "empCenter": "PB-HSR",
                "name": "TEST EMPLOYEE " + datetime.now().strftime("%H%M%S"),
                "designation": "TEST ROLE",
                "currentSalary": 25000,
                "bankName": "TEST BANK",
                "beneAccNo": "1234567890",
                "ifsc": "TEST0001234",
                "mobile": "9999999999",
                "email": "test@example.com"
            }
            
            self.run_test("Create Test Employee", "POST", "/mgt_employee_create", 200, test_emp_data)

    def test_attendance_management(self):
        """Test attendance management endpoints"""
        if not self.token:
            print("❌ No auth token - skipping attendance tests")
            return
            
        print("\n" + "="*60)
        print("TESTING ATTENDANCE MANAGEMENT")
        print("="*60)
        
        today = datetime.now().strftime("%Y-%m-%d")
        current_month = datetime.now().strftime("%Y-%m")
        
        req_data = {"token": self.token, "center": "PB-MGT"}
        
        # Get employees first
        success, response = self.run_test("Load Employees for Attendance", "POST", "/employees", 200, req_data)
        employees = response.get('employees', []) if success else []
        
        if employees:
            print(f"   Found {len(employees)} employees for attendance")
            
            # Test bulk attendance save
            attendance_data = {
                "token": self.token,
                "center": "PB-MGT", 
                "date": today,
                "submittedBy": "9741399190",
                "rows": [
                    {
                        "employeeName": employees[0].get('name', 'TEST'),
                        "designation": employees[0].get('designation', ''),
                        "status": "P",
                        "notes": "Test attendance"
                    }
                ]
            }
            self.run_test("Save Bulk Attendance", "POST", "/bulk_attendance", 200, attendance_data)
            
            # Test get attendance by date
            date_req = {"token": self.token, "center": "PB-MGT", "date": today}
            self.run_test("Get Attendance by Date", "POST", "/attendance_by_date", 200, date_req)
            
            # Test monthly attendance
            month_req = {"token": self.token, "center": "PB-MGT", "month": current_month}
            self.run_test("Get Monthly Attendance", "POST", "/attendance_month", 200, month_req)

    def test_advances_management(self):
        """Test advances management"""
        if not self.token:
            print("❌ No auth token - skipping advances tests")
            return
            
        print("\n" + "="*60)
        print("TESTING ADVANCES MANAGEMENT")
        print("="*60)
        
        today = datetime.now().strftime("%Y-%m-%d")
        current_month = datetime.now().strftime("%Y-%m")
        
        # Test bulk advances
        advances_data = {
            "token": self.token,
            "center": "PB-MGT",
            "date": today,
            "submittedBy": "9741399190",
            "rows": [
                {
                    "employeeName": "TEST EMPLOYEE",
                    "advanceAmount": 500.0,
                    "mode": "CASH",
                    "notes": "Test advance"
                }
            ]
        }
        self.run_test("Save Bulk Advances", "POST", "/bulk_advances", 200, advances_data)
        
        # Get advances by date
        date_req = {"token": self.token, "center": "PB-MGT", "date": today}
        self.run_test("Get Advances by Date", "POST", "/advances_by_date", 200, date_req)
        
        # Get advances by month
        month_req = {"token": self.token, "center": "PB-MGT", "month": current_month}
        self.run_test("Get Advances by Month", "POST", "/advances_by_month", 200, month_req)

    def test_payroll_management(self):
        """Test payroll and salary generation"""
        if not self.token:
            print("❌ No auth token - skipping payroll tests")
            return
            
        print("\n" + "="*60)
        print("TESTING PAYROLL MANAGEMENT")
        print("="*60)
        
        current_month = datetime.now().strftime("%Y-%m")
        
        # Check payroll status
        month_req = {"token": self.token, "center": "PB-MGT", "month": current_month}
        self.run_test("Check Payroll Status", "POST", "/payroll_status", 200, month_req)
        
        # Test salary generation
        salary_req = {
            "token": self.token,
            "center": "PB-MGT",
            "month": current_month,
            "mode": "single",
            "targetCenter": "PB-HSR"
        }
        self.run_test("Generate Salary Excel", "POST", "/generate_salary", 200, salary_req)
        
        # Test payslip generation
        payslip_req = {
            "token": self.token,
            "center": "PB-MGT",
            "month": current_month,
            "period": "1",
            "fmt": "pdf",
            "mode": "single",
            "targetCenter": "PB-HSR"
        }
        self.run_test("Generate Payslips", "POST", "/payslips_generate", 200, payslip_req)

    def test_guest_response_ai(self):
        """Test Guest Response AI feature"""
        if not self.token:
            print("❌ No auth token - skipping Guest AI tests")
            return
            
        print("\n" + "="*60)
        print("TESTING GUEST RESPONSE AI")
        print("="*60)
        
        # Test center info endpoint
        success, response = self.run_test("Get Center Info", "GET", "/center_info", 200)
        if success:
            centers = response.get('centers', {})
            print(f"   Found {len(centers)} centers in info")
            
            # Check if key centers exist
            key_centers = ["PB-HSR", "PB-TH", "PB-SN", "PB-DV", "PB-HW", "PB-KN", "PB-KAL", "PB-PERTH"]
            for center in key_centers:
                if center in centers:
                    center_data = centers[center]
                    print(f"   ✅ {center}: {center_data.get('name', 'N/A')} - {center_data.get('phone', 'N/A')}")
                else:
                    print(f"   ❌ {center} not found in center info")
        
        # Test AI chat functionality
        ai_request = {
            "token": self.token,
            "center": "PB-MGT",
            "question": "What are the timings for Purnabramha restaurants?",
            "sessionId": f"test_session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        success, response = self.run_test("Guest AI Response", "POST", "/guest_ai", 200, ai_request)
        if success:
            if 'answer' in response and 'sessionId' in response:
                print(f"   ✅ AI Response received (length: {len(response.get('answer', ''))} chars)")
                print(f"   Session ID: {response.get('sessionId', 'N/A')}")
                
                # Check if response contains restaurant info
                answer = response.get('answer', '').lower()
                if any(keyword in answer for keyword in ['12:00', 'pm', 'timing', 'purnabramha']):
                    print(f"   ✅ Response contains relevant restaurant information")
                else:
                    print(f"   ⚠️  Response may not contain expected restaurant information")
            else:
                print(f"   ❌ AI response missing required fields")
        
        # Test another question
        ai_request2 = {
            "token": self.token,
            "center": "PB-HSR",
            "question": "What is the phone number for HSR location?",
            "sessionId": ai_request["sessionId"]
        }
        
        success, response = self.run_test("Guest AI HSR Query", "POST", "/guest_ai", 200, ai_request2)
        if success and 'answer' in response:
            answer = response.get('answer', '').lower()
            if '85500' in answer or 'hsr' in answer:
                print(f"   ✅ HSR-specific response detected")

    def test_bhojan_guru(self):
        """Test Bhojan Guru recipe endpoints"""
        print("\n" + "="*60)
        print("TESTING BHOJAN GURU")
        print("="*60)
        
        # Get recipes
        success, response = self.run_test("Get Recipes", "GET", "/recipes", 200)
        if success:
            recipes = response.get('recipes', [])
            print(f"   Found {len(recipes)} recipes")
        
        # Get descriptions
        self.run_test("Get Descriptions", "GET", "/descriptions", 200)

    def test_data_seeding(self):
        """Test data seeding capability"""
        print("\n" + "="*60)
        print("TESTING DATA SEEDING")
        print("="*60)
        
        self.run_test("Seed Database", "POST", "/seed_data", 200)

    def run_all_tests(self):
        """Run comprehensive API test suite"""
        print("🚀 Starting Purnabramha IntraPB API Tests")
        print(f"Backend URL: {self.base_url}")
        print("="*80)
        
        # Test basic endpoints first
        self.test_basic_endpoints()
        
        # Test authentication (critical for other tests)
        auth_success = self.test_auth_flow()
        
        # Test all authenticated endpoints
        if auth_success:
            self.test_employee_management()
            self.test_attendance_management() 
            self.test_advances_management()
            self.test_payroll_management()
            self.test_guest_response_ai()  # New Guest AI tests
        
        # Test public endpoints
        self.test_bhojan_guru()
        self.test_data_seeding()
        
        # Print final results
        print("\n" + "="*80)
        print("📊 FINAL TEST RESULTS")
        print("="*80)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%" if self.tests_run > 0 else "No tests run")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED!")
            return 0
        else:
            print("❌ SOME TESTS FAILED")
            return 1

def main():
    tester = PurnabramhaAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())