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

## Backlog/Future
- **Payslip Data Overlap (P1)**: Verify and fix any remaining overlap issues in PDF payslip generation
- **HR Letter PDF Download Verification (P2)**: User verification pending for the fix applied earlier
- **Refactor server.py into modular FastAPI routers** (HIGH PRIORITY - file is very large, ~3500 lines)
- Add image upload for recipes (currently URL only)
- Add company CIN number to HR letter templates
- Email generated letters directly to employees
