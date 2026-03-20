# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
User had existing HTML/Python files for an attendance and salary management system using Excel as database storage. Required migration to MongoDB with modern UI design while preserving all functionality. Added Guest Response AI feature, Bhojan Guru with recipes from user's PDF file, Recipe Admin panel for MGT, and HR Letters generation.

## Project Overview
**Purnabramha IntraPB** - Internal portal for attendance, salary management, HR documents, and guest response for Purnabramha Restaurant Chain (Manswini Foods Pvt. Ltd.)

## What's Been Implemented

### Latest Update (Mar 20, 2026 - Session 15)

- ✅ **P0: COMPREHENSIVE FRANCHISE AGREEMENT GENERATOR (COMPLETE REBUILD)**
  - **Problem Solved:** Previous generator only created 5-page documents. User needed 60+ page comprehensive legal agreements.
  - **Solution:** Complete rewrite of the agreement generator producing 52-53 page professional documents
  - **Features:**
    - **8 Main Sections:**
      1. Definitions (20+ legal definitions)
      2. Agreement Structure & Business Transfer
      3. Operational Structure & Control Framework
      4. Financial Framework, Profit Share, Loss Exit & Business Sale Mechanism
      5. Intellectual Property, Brand Protection, Confidentiality & Non-Compete
      6. Legal Liability, Insurance, Health & Safety Compliance
      7. Term, Renewal, Termination & Post-Termination Obligations
      8. Dispute Resolution, Governing Law, Force Majeure & Miscellaneous
    - **8 Schedules (A-H):**
      - A: Business Asset & Goodwill Valuation Breakdown
      - B: Bank Account & Financial Control Structure
      - C: Royalty, Profit Share & Honorarium Matrix
      - D: Operational Control & SOP Framework
      - E: Visa & Staff Deployment Plan
      - F: Exit & Sale Valuation Protocol
      - G: Confidential Information & IP Document List
      - H: Non-Compete Zones
    - **11 Annexures (A-K):**
      - A: Shop Deposit - Refund & Exit Understanding
      - B: Service Contract Understanding
      - C: Detailed Operational Guidelines
      - D: ROI Calculations & Financial Projections Framework
      - E: Legal & Regulatory Compliance Checklist
      - F: Training Program Details
      - G: Brand Guidelines Summary
      - H: Emergency Procedures & Crisis Management
      - I: Menu & Recipe Standards
      - J: Technology Systems & Digital Infrastructure
      - K: Quality Assurance Checklist
    - **Country-Specific Logic:**
      - **Australia Model:** 80/20 profit share, Director Honorarium, Royalty to MFPL, AUD currency
      - **India Model:** 15% Revenue Share, Service Contract Fee ₹10,000/month, INR currency
    - **Dynamic Data Population:** Franchise fee, working capital, directors, setup costs, dates
    - **Professional Formatting:** Page numbers, headers, footers, table of contents, tables
  - **Backend:** `/app/backend/utils/agreement_generator.py` (3200+ lines)
  - **Testing:** 32/32 tests passed, 100% success rate

### Previous Update (Mar 18, 2026 - Session 14)

- ✅ **P0: BOOKING INTELLIGENCE & GUEST CONVERSION MODULE (COMPLETE)**
  - **Booking Management:**
    - Full CRUD for bookings (create, list, update, delete)
    - Booking ID format: `BK-{CENTER}-{TIMESTAMP}-{UUID}`
    - 18 fields: date, time_slot, guest_name, phone, num_guests, celebration_type, etc.
    - Status tracking: Enquiry, Confirmed, Visited, Cancelled, No Show, Repeat Visit
  - **Guest CRM:**
    - Guest lookup by phone number
    - Automatic guest tracking (new vs repeat)
    - Store DOB, anniversary, kids birthday for reminders
    - Guest history and preferences tracking
  - **Dashboard Analytics:**
    - Period filters: Today, Week, Month
    - Summary: Total bookings, Enquiries, Confirmed, Visited, Cancelled
    - Conversion metrics: Enquiry-to-Confirm, Booking-to-Visit, Repeat rate
    - Celebration breakdown, Time slot distribution, Booking sources
  - **WhatsApp Integration (MOCKED):**
    - Confirmation, Reminder, Thank You message templates
    - Message preview before sending
    - Messages logged to `whatsapp_logs` collection (actual API pending)
  - **Reminders System:**
    - Upcoming birthdays (next 7 days)
    - Upcoming anniversaries (next 7 days)
    - Kids birthdays
    - Today's follow-ups based on follow_up_date
  - **Catering Leads:**
    - Mark booking as catering enquiry
    - Separate catering_leads collection
  - **Backend:** `/app/backend/routes/booking_intelligence.py` (1066 lines)
  - **Frontend:** `/app/frontend/src/pages/BookingIntelligence.jsx` (1357 lines)
  - **Testing:** 20/20 backend tests passed, frontend fully verified

- ✅ **P0: CENTRALIZED ATTENDANCE DASHBOARD (NEW)**
  - **Admin Panel Feature:**
    - Read-only access for Admin users
    - Full edit access for Super Admin only
    - Located under Attendance section in navigation
  - **Summary Cards:**
    - Total Employees, Present, Absent, Half Day, Week Off, Leave, Attendance %
    - Color-coded with icons
  - **Attendance Distribution:**
    - Pie chart showing Present vs Not Marked breakdown
  - **Center-wise Breakdown:**
    - Table with all centers showing staff count, status counts, attendance %
    - Alert icons: Red (< 70%), Yellow (70-85%), Green (> 85%)
    - "View" button to drill down to employee level
  - **Employee Detail View:**
    - Shows all employees for selected center
    - Status badges with color coding
    - Notes column and edit action (Super Admin only)
  - **Trends Tab:**
    - Daily Attendance Trend line chart (day-by-day)
    - Center-wise Attendance Comparison bar chart
    - Low/High Attendance Alerts cards
  - **Excel Export:**
    - Daily attendance report (per date)
    - Monthly attendance report (full month grid)
  - **Edit Capability (Super Admin):**
    - Edit dialog with status dropdown
    - Audit trail in `attendance_audit` collection
  - **Backend:** `/app/backend/routes/attendance_dashboard.py` (650 lines)
  - **Frontend:** `/app/frontend/src/pages/AttendanceDashboard.jsx` (900 lines)
  - **Testing:** 15/15 backend tests passed, frontend fully verified

- ✅ **P1: INVALID TOKEN FIX (CRITICAL STABILITY FIX)**
  - **Root Cause:** In-memory `otp_store` dictionary was wiped on every server restart
  - **Solution:** Sessions now persist to MongoDB `sessions` collection
  - **Implementation:**
    - New functions: `save_session_to_db()`, `get_session_from_db()`, `get_session_by_token()`
    - `verify_token_async()` checks MongoDB if token not in memory
    - Both `send_otp` and `verify_otp` save to MongoDB
  - **Session TTL:** 12 hours (43200 seconds)
  - **Result:** Tokens survive server restarts, no more "Invalid Token" errors

### Previous Update (Mar 15, 2026 - Session 13)

- ✅ **P0: FOCO MODEL UPGRADE FOR FRANCHISE AGREEMENTS**
  - **Business Model:** FOCO (Franchise Owned - Company Operated)
    - Franchise Owner invests capital and owns the franchise unit
    - Purnabramha (brand owner) manages all operations: menu, staff, procurement, accounting
  - **4 Franchise Types with Auto-Fee:**
    - Sanskriti: ₹11,00,000 (2500+ Sq.Ft, 20-25 staff)
    - Maaza: ₹9,00,000 (1500-2000 Sq.Ft, 8-9 staff)
    - Potoba: ₹7,00,000 (Express format)
    - Peshwayee: ₹25,00,000 (Premium fine dining)
  - **Fixed 7-Year Tenure:** Auto-calculated end date from start date
  - **Revenue Model (India):**
    - 15% Revenue Share to franchise owner
    - Remaining profit to Manaswini Foods Pvt Ltd
  - **Working Capital Protection:**
    - If WC falls below 50%, revenue share becomes 0%
    - Resumes when WC restored to original level
  - **Monthly Service Fee:** ₹10,000/center for brand management
  - **Setup Costs Tracking:** Shop deposit, first month rent, salary fund, grocery cost
  - **Country-Specific Logic:**
    - India: Manaswini Foods Pvt Ltd, INR currency
    - International: Purnabramha LLC, USD/local currency
  - **Full Legal Agreement PDF Generator:** 12 sections including FOCO model explanation
  - **Backend:** `/app/backend/routes/franchises.py` (1200+ lines with FOCO model)
  - **Frontend:** `/app/frontend/src/pages/FranchiseManagement.jsx` (1300+ lines)

### Previous Update (Mar 11, 2026 - Session 12)

- ✅ **P0: FRANCHISE MANAGEMENT MODULE**
  - **Full CRUD for Franchises:** Create, Read, Update, Delete franchise records
  - **Comprehensive Data Model:** Franchise code, name, legal entity, country, state, city, address, pincode
  - **Primary Contact:** Name, email, phone for main contact person
  - **Multiple Directors:** Support for multiple directors with name, email, phone, designation
  - **Agreement Details:** Start date, end date, franchise fee, royalty percentage
  - **Status Tracking:** Active, Inactive, Pending, Terminated states
  - **Document Management:**
    - Upload documents (Agreement, Legal, Compliance, Exit, Other)
    - File types supported: PDF, DOC, DOCX, JPG, PNG, XLS, XLSX
    - Download, preview, and delete documents
    - Audit logging for all document operations
  - **Agreement PDF Generation:** Automatic franchise agreement PDF with terms and conditions
  - **Audit History:** Full tracking of all changes (CREATE, UPDATE, DELETE, DOCUMENT_UPLOAD, AGREEMENT_GENERATED)
  - **Access Control:** Only Admin and Accounts roles can access
  - **Search & Filter:** Search by code/name/city, filter by country and status
  - **Statistics Dashboard:** Cards showing Total, Active, Pending, Terminated counts
  - **Backend:** `/app/backend/routes/franchises.py` (600+ lines)
  - **Frontend:** `/app/frontend/src/pages/FranchiseManagement.jsx` (1140 lines)
  - **Testing:** 22 backend tests + frontend verification (100% pass rate)

### Previous Update (Mar 05, 2026 - Session 11)

- ✅ **P0: CORRECTED & SIMPLIFIED Financial Calculations**
  - **Cash Sale** = Total Sale - (Swiggy + Zomato + Other/Pickups)
  - **Cash in Hand** = Opening + Withdrawal + Total Sale - (Swiggy + Zomato + Other + Card + BharatPay + Expenses)
  - **Petty Cash** = Last Day Petty Cash + Withdrawal - Expenses in Cash
  - **Removed unnecessary fields:** Amazon, ECWID, Paytm, PBM Online (not needed)
  
- ✅ **P0: Grid Bulk Update Feature**
  - **8 Editable columns:** Total Sale, Swiggy, Zomato, Card/IDFC, Bharat Pay, Other/Pickup, Guests, Bills
  - **3 Auto-calculated columns:** Online Sale, Cash Sale, Cash in Hand
  - Click cell to edit, Tab to navigate, Ctrl+V to paste from Excel
  - **Focus fix:** Using local state for input values to prevent focus jumping

- ✅ **P0: Fixed Focus Jumping Issue**
  - Changed grid input handling to use local state (`editValue`)
  - Grid data only updates on blur (when leaving cell)
  - Using plain HTML input for better focus control

### Previous Sessions
(see CHANGELOG.md for full history)

- ✅ **P0: 5 Critical Features Implemented**

1. **Synchronized Unlock (Sales + Expenses)**
   - When Super Admin approves an unlock request for a frozen date, BOTH sales AND expenses records are now unlocked simultaneously
   - Backend creates two unlock_grants records (type: "sales" and type: "expenses")
   - Allows managers to update petty cash and expenses when needed
   - Implementation: `/app/backend/routes/sales_expenses.py` lines 629-660

2. **Petty Cash Logic Fix**
   - Formula: `Opening Balance = Previous Day's Closing Balance`
   - `Petty Cash Available = Opening + Cash Added Today (cash_receipts)`
   - `Closing Balance = Petty Cash Available - Today's CASH Expenses Only`
   - Only CASH payment mode expenses reduce petty cash (not Card/UPI/Online)
   - Implementation: `/app/backend/routes/sales_expenses.py` lines 245-297

3. **Session Timeout (2+ Hours)**
   - Session TTL configured to 12 hours (43200 seconds) - exceeds minimum 2 hours
   - Token now tracks creation time (`token_created_at`)
   - `verify_token()` function checks expiry before validating
   - Login response includes `session_expires_in_seconds` field

4. **Invalid Token / Data Loading Fix**
   - Global Axios interceptor with 401 error handling
   - Automatic retry mechanism (one retry before clearing session)
   - Network error retry for connection issues
   - Dispatches `session-expired` event to clear React state
   - Implementation: `/app/frontend/src/lib/api.js` lines 36-96

5. **New Accounting Role**
   - Users with `accounting` role get full "Sales & Cash" access for ALL centers
   - Can view all centers' sales data (like Super Admin, but limited to finance features)
   - Added to Role Management page as "Accounting (Full Access)"
   - Backend checks: `has_accounting_role()`, updated `has_all_centers_access()`, `has_sales_access()`
   - Frontend checks in Dashboard.jsx and SalesExpenses.jsx

- ✅ **P0: Super Admin Freeze Control (NEW)**
   - New "Freeze Control" tab in Sales & Cash (visible to Super Admin only)
   - Allows manual freeze/unfreeze of sales & expense data
   - Options:
     - **Scope**: Single Day or Full Month
     - **Center**: Specific center or All Centers
     - **Action**: Freeze (prevents all editing) or Unfreeze (allows editing for 30 days)
   - Shows current freeze status with Admin Frozen Dates and Unlocked Dates counts
   - API endpoints: `/api/sales/admin/freeze-control`, `/api/sales/admin/freeze-status`
   - Implementation: 
     - Backend: `/app/backend/routes/sales_expenses.py` (AdminFreezeRequest model, freeze-control endpoint)
     - Frontend: `/app/frontend/src/components/FreezeControl.jsx`
   - Creates records in `admin_freezes` collection
   - Super Admin access verified by email: jayanti.devashree@gmail.com, sandeep.gadhwal@purnabramha.com

### Previous Update (Feb 24, 2026 - Session 7)

- ✅ **P0 Bug Fixes (Critical)**
  - **Role Assignment Error (Fixed)**: Consecutive role updates were failing due to regex email matching without proper escaping. Added `re.escape()` for case-insensitive email search with special character support.
  - **Expense Heads Not Listing (Fixed)**: Frontend was using `_id` for edit/delete but API returns data without `_id`. Changed to use `name` as identifier (matches backend PUT/DELETE endpoints). Also seeded 35 expense categories into database.

- ✅ **Super Admin & Admin Role System (NEW)**
  - **Super Admin (Jayanti Kathale)**: Full access to everything, can manage all users including other Super Admins
  - **Admin**: Full access to all features, can view all centers, but cannot see/modify Super Admins
  - **Regular User**: Access based on assigned module roles only
  - Jayanti can see ALL managers including Super Admins
  - Other users CANNOT see Jayanti's record (hidden from everyone except herself)
  - Other users CANNOT see other Super Admin records (except their own)
  - Only Jayanti can grant/revoke Super Admin status
  - Only Jayanti can delete Super Admin accounts

- ✅ **Role Management UI Updates**
  - Added "Access Level" selector: Regular User, Admin, Super Admin
  - Added "View All Centers" permission toggle
  - Shows color-coded badges: Super Admin (red), Admin (purple), All Access (green)
  - Backend filters manager list based on current user's permissions

- ✅ **Frontend Improvements**
  - ExpenseHeads.jsx: Fixed edit/delete to use expense head `name` instead of `_id`
  - URL encoding for expense head names with special characters (e.g., "WATER CAN / BOTTLE")
  - Login now stores `is_super_admin` and `is_admin` flags in session
  - Dashboard checks `is_super_admin` and `is_admin` for access control

### Previous Update (Feb 24, 2026 - Session 6)

- ✅ **Sales & Expenses Tracking System (MAJOR FEATURE)**
  - Imported data from 8 Excel files: PB-DV, PB-HW, PB-HSR, PB-KAL, PB-KN, PB-PT, PB-SN, PB-TH
  - Total 2050 daily sales records and 2819 expense records imported
  - **Sales Dashboard** with 6 tabs:
    - **Overview Tab**: Summary cards, Online Payment Breakdown, Expenses by Category, Net Profit
    - **Sales Entry Tab**: Form for daily sales with editable (white) vs calculated (gray) fields
    - **Expense Entry Tab**: Form to add daily expenses with category, amount, payment mode
    - **Daily Report Tab**: Center-wise breakdown
    - **Expense List Tab**: All expense records
    - **Payment Breakdown Tab**: Cash vs Online comparison

- ✅ **Expense Heads Master**
  - CRUD page for managing expense categories (`/expense-heads`)
  - 20 standard expense categories pre-loaded
  - Add/Edit/Delete functionality for MGT users

- ✅ **Role & Access Management (NEW)**
  - New page at `/role-management` for MGT to assign module access to managers
  - 5 role modules: Attendance, Sales & Cash, HR Management, Management, Operations
  - Visual checkboxes for each role with descriptions
  - Role-based sidebar filtering (managers only see allowed modules)
  - Backend API: `/api/mgt/manager_roles` for saving role assignments

- ✅ **Sidebar Reorganization**
  - Categorized navigation: Attendance, Sales & Cash, HR Management, Management, Operations
  - Role Management added under Management section
  - Collapsible category sections

- ✅ **Bug Fix: Input Focus Issue**
  - Fixed text input focus jumping when typing in Sales Entry and Expense Entry forms
  - Changed from `type="number"` to `type="text"` with `inputMode="decimal"` for better control
  - Input fields now retain focus while typing multiple digits

### Previous Update (Feb 22, 2026 - Session 5)

- ✅ **Recipe Database Expanded to 164 Recipes**
  - Added ALL recipes from user's PDF (was 79, now 164)
  - Complete extraction of recipes from all categories
  - New categories and recipes added:
    - Additional SNACKS: Moong Dal Pakoda, Palak Pakoda, Dadpe Pohe, Dhirade, etc.
    - Additional BALGOPAL: Sabudana Khichadi, Sabudana Vada, Aloo Paratha, Kanda Poha, Puri
    - Additional SWEETS: Shirvale, Tilgul Poli, Sevya Chi Kheer, Tillache Ladoo, Gulab Jamun
    - Additional MAINS: Thalipith, Varan Fal, Vangyache Bharit, Pithala, multiple Bhajis
    - Additional CURRIES: Patodi Rassa, Katachi Aamti, Multiple Varan types
    - Additional RICE: 15+ rice varieties (Dahi Bhat, Pulao, Khajur Bhat, etc.)
    - Additional CHAPATI: Paratha, Phulka, Masala Puri, Red Puri
    - Additional CHUTNEYS: Mokali Dal, Fresh Coconut, Sunday Special
    - FASTING recipes: Sabudana Khichdi, Rajgeera dishes, Fasting Kadhi

- ✅ **User Manual PDF Generation**
  - New endpoint: `GET /api/docs/user-manual`
  - 9-page comprehensive user manual
  - Covers: Login, Dashboard, Attendance, Salary, Recipes, HR Letters, etc.
  - Download button added to Recipe Admin page

- ✅ **Recipe Brochure PDF Generation**
  - New endpoint: `GET /api/docs/brochure`
  - Beautiful recipe brochure with cover page
  - All 164 recipes organized by category
  - 6 featured recipes with full details
  - Download button added to Recipe Admin page

- ✅ **HR Letters Center Dropdown Fix**
  - Fixed: Centers now load from database instead of hardcoded values
  - Dropdown shows actual centers: PB-HSR, PB-TH, PB-SN, PB-DV, PB-HW, PB-KN, PB-KAL, PB-PERTH, PB-MGT

- ✅ **Manager Phone Update Fix**
  - Fixed: Update now uses original email as identifier
  - Email field made read-only in edit dialog
  - Mobile number can now be updated without errors

- ✅ **Recipe Admin Complete Overhaul**
  - Added 79 recipes from user's PDF document to recipes_db.json
  - Organized by 10 categories: SNACKS(15), DRINKS(10), BALGOPAL(2), MAINS(6), CURRIES(8), RICE(2), CHAPATI(4), SWEETS(19), CHUTNEYS(8), SALADS(5)
  - Category tabs with recipe counts for easy filtering
  - Search functionality by recipe name
  - Full CRUD: Add, Edit, Delete recipes
  - Image URL support for each recipe
  - Bilingual display (English + Marathi/Hindi)

- ✅ **Payslip PDF/DOCX Format Support**
  - Added DOCX format option alongside PDF for payslip generation
  - Completely redesigned PDF layout with cleaner two-column structure
  - Fixed data overlap issue with proper spacing
  - Earnings on left column, Deductions on right column
  - Net salary highlighted in gray box at bottom
  - Professional footer with signature

- ✅ **Centers Management (New Feature)**
  - Full CRUD operations for center management
  - List all centers with Code, Name, Phone, Email, Address, Status
  - Add new center with validation
  - Edit existing center details
  - Delete center (PB-MGT protected from deletion)
  - Centers stored in MongoDB `centers` collection
  - MGT-only access

- ✅ **Managers Management (New Feature)**
  - Full CRUD operations for manager management
  - Stats cards: Total Managers, Active Managers, Centers with Managers
  - List all managers with Center, Name, Contact, Status
  - Add new manager with center dropdown
  - Edit manager (email used as identifier, cannot be changed)
  - Delete manager (cannot delete own account)
  - MGT-only access

### Previous Implementations
- ✅ **HR Letters Generator (AI-Powered)** - Offer, Exit, Experience, Visa letters
- ✅ **Salary Excel CREDIT_NARR/DEB_NARR** - Uses remark if filled, defaults otherwise
- ✅ **Bhojan Guru** - Region Thali, Body Need questionnaire, Recipes, Menu Descriptions
- ✅ **OTP Email System** - Live email delivery
- ✅ **Guest Response AI** - Center-based AI responses

## Recipe Categories & Counts (Updated - 164 Total)
| Category | Count | Examples |
|----------|-------|----------|
| SNACKS | 30+ | Kanda Bhaji, Batata Vada, Kothimbir Vadi, Sabudana Vada |
| DRINKS | 12 | Solkadhi, Masala Buttermilk, Aam Panha, Rose Piyush |
| BALGOPAL | 7 | Sabudana Khichadi, Sabudana Vada, Aloo Paratha, Kanda Poha |
| MAINS | 25+ | Aloo Bhaji, Zhunka, Thalipith, Pithala, Various Bhajis |
| CURRIES | 20+ | Bharli Vangi, Kaju Curry, Special Kadhi, Katachi Aamti |
| RICE | 18 | Masale Bhaat, Dahi Bhat, Pulao, Wangi Bhat, Jeera Rice |
| CHAPATI | 10 | Bhakri, Paratha, Phulka, Puri, Masala Puri |
| SWEETS | 25+ | Puran Poli, Gajar Halwa, Modak, Shrikhand, Gulab Jamun |
| CHUTNEYS | 10 | Green Chutney, Thecha, Tamarind, Panchamrut |
| SALADS | 7 | Gajar Koshimber, Kakdi, Lauki, Pachaddi Koshimbir |

## Key API Endpoints

### Sales & Expenses (NEW)
- `GET /api/sales/centers-list` - Get centers with sales data
- `POST /api/sales/reports/monthly-summary` - Monthly summary with expense breakdown
- `POST /api/sales/expenses` - Get expense records with filters
- `POST /api/sales/daily` - Get daily sales records
- `POST /api/sales/daily/create` - Create daily sales entry
- `PUT /api/sales/daily/{center}/{date}` - Update daily sales
- `DELETE /api/sales/daily/{center}/{date}` - Delete daily sales (MGT only)
- `POST /api/sales/expenses/create` - Create expense record
- `PUT /api/sales/expenses/{id}` - Update expense
- `DELETE /api/sales/expenses/{id}` - Delete expense
- `GET /api/sales/expense-types` - Get expense categories
- `GET /api/sales/payment-modes` - Get payment modes

### Recipes
- `GET /api/recipes` - Get all recipes with categories
- `GET /api/recipes/categories` - Get category list
- `GET /api/recipes/search?q=` - Search recipes
- `POST /api/recipes?token=` - Create recipe (MGT only)
- `PUT /api/recipes/{key}?token=` - Update recipe (MGT only)
- `DELETE /api/recipes/{key}?token=` - Delete recipe (MGT only)

### Centers Management
- `POST /api/mgt/centers` - Get all centers (MGT only)
- `POST /api/mgt/center_create` - Create new center
- `POST /api/mgt/center_update` - Update center details
- `POST /api/mgt/center_delete` - Delete center

### Managers Management
- `POST /api/mgt/managers` - Get all managers (MGT only)
- `POST /api/mgt/manager_create` - Create new manager
- `POST /api/mgt/manager_update` - Update manager details
- `POST /api/mgt/manager_delete` - Delete manager

### Payslips
- `POST /api/payslips_generate` - Generate payslips (supports fmt=pdf|docx)

### Documentation PDFs
- `GET /api/docs/user-manual` - Download User Manual PDF
- `GET /api/docs/brochure` - Download Recipe Brochure PDF

### HR Letters
- `POST /api/hr/generate-letter` - Generate HR letter with AI
- `POST /api/hr/download-letter-pdf` - Download letter as PDF
- `POST /api/hr/download-letter-word` - Download letter as DOCX

### Franchise Management (NEW)
- `POST /api/franchises/list` - List franchises with filters (search, country, status)
- `POST /api/franchises/create` - Create new franchise
- `POST /api/franchises/get/{code}` - Get franchise details with audit history
- `POST /api/franchises/update/{code}` - Update franchise
- `POST /api/franchises/delete/{code}` - Delete franchise (Super Admin only)
- `POST /api/franchises/documents/upload` - Upload document (multipart form)
- `GET /api/franchises/documents/download/{code}/{docId}` - Download document
- `POST /api/franchises/documents/delete/{code}/{docId}` - Delete document
- `POST /api/franchises/generate-agreement/{code}` - Generate agreement PDF
- `POST /api/franchises/stats` - Get franchise statistics
- `GET /api/franchises/countries` - Get available countries list

### Booking Intelligence (NEW - Session 14)
- `GET /api/bookings/constants` - Get all booking form constants
- `POST /api/bookings/create` - Create new booking
- `POST /api/bookings/list` - List bookings with filters
- `POST /api/bookings/get/{booking_id}` - Get single booking details
- `POST /api/bookings/update/{booking_id}` - Update booking
- `POST /api/bookings/delete/{booking_id}` - Delete booking (Super Admin only)
- `POST /api/bookings/guest-lookup` - Look up guest by phone number
- `POST /api/bookings/dashboard/stats` - Get dashboard statistics
- `POST /api/bookings/dashboard/center-comparison` - Get center-wise comparison (Admin only)
- `POST /api/bookings/dashboard/trends` - Get booking trends over time
- `POST /api/bookings/preview-whatsapp/{booking_id}` - Preview WhatsApp message
- `POST /api/bookings/send-whatsapp/{booking_id}` - Send/log WhatsApp message
- `POST /api/bookings/reminders/upcoming` - Get upcoming birthday/anniversary reminders
- `POST /api/bookings/reminders/send-greeting` - Send greeting message
- `POST /api/bookings/followups/today` - Get today's follow-ups
- `POST /api/bookings/catering/list` - List catering leads
- `POST /api/bookings/catering/update/{booking_id}` - Update catering lead

### Attendance Dashboard (NEW - Session 14)
- `POST /api/attendance-dashboard/summary` - Get overall attendance summary
- `POST /api/attendance-dashboard/center-breakdown` - Get center-wise attendance breakdown
- `POST /api/attendance-dashboard/center-detail` - Get employee-level detail for a center
- `POST /api/attendance-dashboard/monthly-trend` - Get daily attendance trend for a month
- `POST /api/attendance-dashboard/center-comparison` - Get monthly center comparison
- `POST /api/attendance-dashboard/export` - Export daily attendance to Excel
- `POST /api/attendance-dashboard/export-monthly` - Export monthly attendance to Excel
- `POST /api/attendance-dashboard/edit` - Edit attendance (Super Admin only)
- `GET /api/attendance-dashboard/status-options` - Get attendance status options

## Key Files
- `/app/backend/server.py` - Main API server (includes session persistence, PDF generation)
- `/app/backend/routes/sales_expenses.py` - Sales & Expenses API routes (includes Expense Heads CRUD)
- `/app/backend/routes/franchises.py` - Franchise Management API routes
- `/app/backend/routes/booking_intelligence.py` - Booking Intelligence API routes (NEW)
- `/app/backend/routes/mis_dashboard.py` - MIS Dashboard API routes
- `/app/backend/routes/attendance_dashboard.py` - Attendance Dashboard API routes (NEW)
- `/app/backend/scripts/import_sales_data.py` - Excel data import script
- `/app/backend/recipes_db.json` - 164 recipes from user's PDF (expanded from 79)
- `/app/frontend/src/pages/SalesExpenses.jsx` - Sales & Cash Summary dashboard
- `/app/frontend/src/pages/ExpenseHeads.jsx` - Expense Heads Master CRUD page
- `/app/frontend/src/pages/FranchiseManagement.jsx` - Franchise Management page
- `/app/frontend/src/pages/BookingIntelligence.jsx` - Booking Intelligence page (NEW)
- `/app/frontend/src/pages/MISDashboard.jsx` - MIS Dashboard page
- `/app/frontend/src/pages/AttendanceDashboard.jsx` - Attendance Dashboard page (NEW)
- `/app/frontend/src/components/SalesDataEntry.jsx` - Sales data entry form
- `/app/frontend/src/components/ExpenseEntry.jsx` - Expense entry form
- `/app/frontend/src/pages/Dashboard.jsx` - Categorized navigation sidebar (UPDATED)
- `/app/frontend/src/pages/RecipeAdmin.jsx` - Recipe management UI with category tabs
- `/app/frontend/src/pages/CentersManagement.jsx` - Centers management UI
- `/app/frontend/src/pages/ManagersManagement.jsx` - Managers management UI
- `/app/frontend/src/pages/Salary.jsx` - Salary & Payslips with format selector
- `/app/frontend/src/pages/HRLetters.jsx` - HR Letters UI

## Database Collections
- `managers` - Manager login credentials
- `employees` - Employee data
- `centers` - Center details
- `attendance` - Daily attendance records
- `advances` - Employee advances
- `payroll_locks` - Payroll lock status
- `daily_sales` - Daily sales and cash summary records
- `expenses` - Individual expense records with categories
- `franchises` - Franchise records with documents array
- `franchise_audit` - Audit log for all franchise changes
- `sessions` - User session tokens for persistence (NEW - fixes Invalid Token)
- `bookings` - Guest bookings (NEW)
- `guests` - Guest CRM data (NEW)
- `catering_leads` - Catering enquiries (NEW)
- `whatsapp_logs` - WhatsApp message logs (NEW)
- `attendance_audit` - Audit trail for attendance edits (NEW)

## Testing Credentials
- Center: PB-MGT
- Mobile: 9741399190
- Master OTP (dev mode): 123456

## Test Reports
- `/app/test_reports/iteration_6.json` - Centers & Managers tests
- `/app/test_reports/iteration_7.json` - Recipe Admin tests (100% pass)
- `/app/test_reports/iteration_8.json` - Sales & Expenses tests (100% pass - 11/11 backend, full frontend)
- `/app/test_reports/iteration_9.json` - Sales Enhancements (GST, Guest/Bill counts, Booking Response) - 100% pass
- `/app/test_reports/iteration_12.json` - Franchise Management tests (100% pass - 22 backend tests)
- `/app/test_reports/iteration_13.json` - Booking Intelligence & Session Persistence tests (100% pass - 20 backend tests)
- `/app/test_reports/iteration_14.json` - Attendance Dashboard tests (100% pass - 15 backend tests) (NEW)

## Backlog/Future
- **P2: Payslip Data Overlap**: Verify and fix any remaining overlap issues in PDF payslip generation
- **P2: HR Letter PDF Download Verification**: User verification pending for the fix applied earlier
- **P1: Refactor server.py into modular FastAPI routers** (HIGH PRIORITY - file is very large, ~4000 lines)
- **P1: Verify Doordash field and financial calculations**: Recently added but not fully tested
- ~~**P1: Invalid Token issue**: Root cause investigation - in-memory token store~~ **FIXED in Session 14**
- **P1: Enhance Franchise Agreement to 60+ pages** - BLOCKED waiting for user templates
- **P2: Real WhatsApp Business API integration** - Currently MOCKED
- Add custom roles (Trainer, Marketing)
- Add image upload for recipes (currently URL only)
- Add company CIN number to HR letter templates
- Email generated letters directly to employees
- Perth Excel Upload Rule (import without modification)
- Feature Icons display in UI (auto-generated based on booking features)

## Latest Updates (Feb 25, 2026)

### Session 10 - Sales Data Freeze & Unlock Request System (NEW FEATURE)

- ✅ **Automatic Date Freeze**
  - Previous day's sales data is **automatically frozen at midnight**
  - Only today's date can be edited by center managers
  - Visual **lock icons (🔒)** displayed in Daily Report table for frozen dates
  - **Unlock icon (🔓)** shown for editable dates (today)

- ✅ **Unlock Request System**
  - Center managers can **submit unlock requests** for frozen dates
  - Request includes: date, center, reason for unlock
  - **Pending request indicator** shown for dates with active requests
  - Requests stored in `unlock_requests` collection

- ✅ **Super Admin Unlock Approval**
  - Super Admin sees **"Pending Requests"** button when there are requests
  - Can **approve or reject** unlock requests with notes
  - Approved requests grant **24-hour temporary access** to edit frozen date
  - Unlock grants stored in `unlock_grants` collection with expiry

- ✅ **Super Admin Override**
  - Super Admin can **always edit any date** directly (no unlock needed)
  - Bypasses freeze check completely

- ✅ **API Endpoints Added**
  - `GET /api/sales/check-frozen/{center}/{date}` - Check if date is frozen
  - `POST /api/sales/unlock-request` - Submit unlock request
  - `GET /api/sales/unlock-requests` - View all unlock requests
  - `POST /api/sales/unlock-request/{id}/action` - Approve/reject request

### Session 9 - P0 Bug Fixes

- ✅ **P0 Fix: Managers Missing "Sales & Cash" Feature (RESOLVED)**
  - **Root Cause**: `verify_otp` was only looking up managers by mobile number, but most managers in DB have empty mobile fields
  - **Fix**: Added fallback to lookup manager by center code if mobile lookup fails
  - **Result**: All managers now correctly receive their assigned roles (including `sales_cash: true`) upon login

- ✅ **P0 Fix: Perth Center Code Standardization (RESOLVED)**
  - **Issue**: Inconsistent use of "PB-PT" and "PB-PERTH" causing login and data visibility issues
  - **Fix**: Standardized ALL references to use only "PB-PERTH" across frontend and backend

### Previous Session - Session 8 - Sales Data Entry Enhancements & Guest Response Generator
- ✅ **Multi-Currency & GST Logic (CRITICAL)**
  - Perth Center (PB-PT): Australian Dollars (`$`), 10% GST **inclusive** (extracted from total)
  - Indian Centers: Indian Rupees (`₹`), 5% GST **exclusive** (added on subtotal)
  - GST excludes Swiggy & Zomato orders
  - GST Payable displayed on daily/monthly reports
  - Backend helper functions: `is_perth_center()`, `get_currency_symbol()`, `calculate_gst()`

- ✅ **Perth Sales Data Imported**
  - 165 records imported from Perth Excel file (Oct 2025 - Mar 2026)
  - Data imported exactly as-is without modification
  - Currency: AUD ($), GST: 10% inclusive
  - DoorDash and UberEats excluded from GST calculation (like Swiggy/Zomato)

- ✅ **Guest & Bill Count Tracking**
  - New fields in Sales Entry form: Number of Guests (Pax), Number of Bills (excl. Swiggy/Zomato)
  - Auto-calculated: Avg Per Pax (Total Sale / Guests), Avg Per Bill (Total Sale / Bills)
  - Dashboard shows Total Guests and Total Bills cards with averages
  - Data stored in `daily_sales` collection: `num_guests`, `num_bills`, `avg_per_pax`, `avg_per_bill`

- ✅ **Guest Booking Response Generator (NEW FEATURE)**
  - New tab in Guest Response page: "Booking Response"
  - Converts raw booking data to warm, emoji-rich WhatsApp message
  - Uses GPT-5.2 via Emergent LLM Key
  - Feature icons reference: 🍽️ Dine-In, 📦 Takeaway, 🛵 Delivery, ⭐ Bestseller, 🥬 Veg, 🌿 Jain, 👶 Kids, 🎂 Birthday, 💕 Anniversary, 🎊 Party, 🪔 Festival, 💼 Corporate
  - Brand tone: Maharashtrian hospitality, women-led values, warm & homely
  - API endpoint: `POST /api/guest/booking-response`

- ✅ **API Enhancements**
  - `/api/sales/reports/monthly-summary` - now returns: `gst_rate`, `gst_amount`, `gst_inclusive`, `net_sale`, `total_guests`, `total_bills`, `avg_per_pax`, `avg_per_bill`, `currency`
  - `/api/guest/booking-response` - new endpoint for WhatsApp message generation

## Previous Updates (Feb 24, 2026)

### Session 7 - Admin Role System & Data Access Fix
- ✅ **Super Admin & Admin Role System**
  - Super Admin (Jayanti): Full access, can manage other Super Admins
  - Admin: Full access to features, cannot modify Super Admins
  - Regular User: Access based on assigned module roles
  - Jayanti's record hidden from all other users
  
- ✅ **All Centers Access Fix**
  - Super Admins, Admins, and users with "View All Centers" role can now see data from ALL centers
  - Sales Dashboard now shows combined data for all centers
  - Center dropdown shows "All Centers" option for authorized users
  - Backend helper functions `has_admin_access()` and `has_all_centers_access()` added
  
- ✅ **API Access Control Updates**
  - `/api/sales/reports/monthly-summary` - respects admin roles
  - `/api/sales/expenses` - respects admin roles
  - `/api/mgt/managers` - filters based on user permissions
  - Employee management endpoints updated for admin access


## Database Collections

- `managers` - Manager login credentials and roles (including new `accounting` role)
- `employees` - Employee data
- `centers` - Center details
- `attendance` - Daily attendance records
- `advances` - Employee advances
- `payroll_locks` - Payroll lock status
- `daily_sales` - Daily sales and cash summary records (2,238 records)
- `expenses` - Individual expense records (2,819 records)
- `expense_heads` - Expense categories (35 categories)
- `unlock_requests` - Unlock requests for frozen dates
- `unlock_grants` - Approved unlocks with 24-hour expiry (UPDATED: now creates both SALES and EXPENSES grants)
- `admin_freezes` - **NEW** - Super Admin manual freeze records (date, center, frozen_by, type)

## Testing Credentials
- Super Admin: Center `PB-MGT`, Mobile `9741399190`, OTP `123456`
- Perth Manager: Center `PB-PERTH`, Mobile `0401832922`, OTP `123456`
- HSR Manager: Center `PB-HSR`, any mobile, OTP `123456`

## Backlog/Future
- **P2: Payslip Data Overlap** - Verify and fix any remaining overlap issues in PDF payslip generation
- **P2: HR Letter PDF Download Verification** - User verification pending
- **P1: Refactor server.py** - Split into modular FastAPI routers (currently ~3500 lines)
- Add custom roles (Trainer, Marketing)
- Add image upload for recipes (currently URL only)

