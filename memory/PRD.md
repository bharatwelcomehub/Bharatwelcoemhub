# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
User had existing HTML/Python files for an attendance and salary management system using Excel as database storage. Required migration to MongoDB with modern UI design while preserving all functionality. Added Guest Response AI feature, Bhojan Guru with recipes from user's PDF file, Recipe Admin panel for MGT, and HR Letters generation.

## Project Overview
**Purnabramha IntraPB** - Internal portal for attendance, salary management, HR documents, and guest response for Purnabramha Restaurant Chain (Manswini Foods Pvt. Ltd.)

## What's Been Implemented

### Latest Update (Feb 24, 2026 - Session 6)

- ✅ **Sales & Expenses Tracking System (NEW MAJOR FEATURE)**
  - Imported data from 7 Excel files for centers: PB-DV, PB-HW, PB-HSR, PB-KAL, PB-KN, PB-SN, PB-TH
  - Total 1964 daily sales records and 2819 expense records imported
  - New dashboard with comprehensive reports:
    - **Overview Tab**: Summary cards (Total Sales, Cash Sales, Online Sales, Total Expenses), Online Payment Breakdown (Card IDFC, Bharat Pay, Swiggy, Zomato), Expenses by Category, Net Profit
    - **Daily Report Tab**: Center-wise breakdown with Date, Center, Total Sale, Cash, Online, Expenses, Net columns
    - **Expenses Tab**: Full expense records list with Date, Description, Category, Payment Mode, Amount
    - **Payment Breakdown Tab**: Cash vs Online comparison, detailed online payment breakdown
  - Month filter (YYYY-MM format) for historical data
  - Center filter (MGT only) to view individual centers
  - Backend routes in `/app/backend/routes/sales_expenses.py`
  - Frontend page at `/app/frontend/src/pages/SalesExpenses.jsx`
  - Navigation link "Sales & Cash" in sidebar
  - All tests passed: 100% backend (11/11), 100% frontend

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
- `/app/backend/routes/sales_expenses.py` - Sales & Expenses API routes (NEW)
- `/app/backend/scripts/import_sales_data.py` - Excel data import script (NEW)
- `/app/backend/recipes_db.json` - 164 recipes from user's PDF (expanded from 79)
- `/app/frontend/src/pages/SalesExpenses.jsx` - Sales & Cash Summary dashboard (NEW)
- `/app/frontend/src/pages/RecipeAdmin.jsx` - Recipe management UI with category tabs
- `/app/frontend/src/pages/CentersManagement.jsx` - Centers management UI
- `/app/frontend/src/pages/ManagersManagement.jsx` - Managers management UI
- `/app/frontend/src/pages/Salary.jsx` - Salary & Payslips with format selector
- `/app/frontend/src/pages/HRLetters.jsx` - HR Letters UI
- `/app/frontend/src/pages/Dashboard.jsx` - Navigation sidebar

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
- **Role-Based Access Control (RBAC)** - Create two management roles: "hsr related work" and "data related work" (USER REQUESTED)
- Implement CRUD operations for Sales & Expenses (Create/Update/Delete) - Currently read-only view
- Add company CIN number to HR letter templates
- Email generated letters directly to employees
- **Refactor server.py into modular FastAPI routers** (HIGH PRIORITY - file is very large)
- Add image upload for recipes (currently URL only)
- Verify payslip data overlap issue is fully resolved
