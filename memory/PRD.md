# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
User had existing HTML/Python files for an attendance and salary management system using Excel as database storage. Required migration to MongoDB with modern UI design while preserving all functionality. Added Guest Response AI feature, Bhojan Guru with recipes from user's PDF file, Recipe Admin panel for MGT, and HR Letters generation.

## Project Overview
**Purnabramha IntraPB** - Internal portal for attendance, salary management, HR documents, and guest response for Purnabramha Restaurant Chain (Manswini Foods Pvt. Ltd.)

## What's Been Implemented

### Latest Update (Feb 24, 2026 - Session 7)

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

## Key Files
- `/app/backend/server.py` - Main API server (includes PDF generation endpoints)
- `/app/backend/routes/sales_expenses.py` - Sales & Expenses API routes (includes Expense Heads CRUD)
- `/app/backend/scripts/import_sales_data.py` - Excel data import script
- `/app/backend/recipes_db.json` - 164 recipes from user's PDF (expanded from 79)
- `/app/frontend/src/pages/SalesExpenses.jsx` - Sales & Cash Summary dashboard
- `/app/frontend/src/pages/ExpenseHeads.jsx` - Expense Heads Master CRUD page (NEW)
- `/app/frontend/src/components/SalesDataEntry.jsx` - Sales data entry form
- `/app/frontend/src/components/ExpenseEntry.jsx` - Expense entry form (NEW)
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
- `daily_sales` - Daily sales and cash summary records (NEW)
- `expenses` - Individual expense records with categories (NEW)

## Testing Credentials
- Center: PB-MGT
- Mobile: 9741399190
- Master OTP (dev mode): 123456

## Test Reports
- `/app/test_reports/iteration_6.json` - Centers & Managers tests
- `/app/test_reports/iteration_7.json` - Recipe Admin tests (100% pass)
- `/app/test_reports/iteration_8.json` - Sales & Expenses tests (100% pass - 11/11 backend, full frontend)
- `/app/test_reports/iteration_9.json` - Sales Enhancements (GST, Guest/Bill counts, Booking Response) - 100% pass

## Backlog/Future
- **P2: Payslip Data Overlap**: Verify and fix any remaining overlap issues in PDF payslip generation
- **P2: HR Letter PDF Download Verification**: User verification pending for the fix applied earlier
- **P1: Refactor server.py into modular FastAPI routers** (HIGH PRIORITY - file is very large, ~3500 lines)
- Add custom roles (Accounts, Trainer, Marketing)
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
  - **Files Modified**: `/app/backend/server.py` (lines 334-346)

- ✅ **P0 Fix: Perth Center Code Standardization (RESOLVED)**
  - **Issue**: Inconsistent use of "PB-PT" and "PB-PERTH" causing login and data visibility issues
  - **Fix**: Standardized ALL references to use only "PB-PERTH"
  - **Files Modified**:
    - `/app/frontend/src/pages/SalesExpenses.jsx` - `isPerth()` function
    - `/app/backend/routes/sales_expenses.py` - `is_perth_center()` helper and Perth Excel upload
    - `/app/backend/server.py` - Perth center detection
    - `/app/backend/scripts/import_sales_data.py` - Center code mapping
  - **Database**: Already uses "PB-PERTH" (no migration needed)

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
