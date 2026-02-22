# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
User had existing HTML/Python files for an attendance and salary management system using Excel as database storage. Required migration to MongoDB with modern UI design while preserving all functionality. Added Guest Response AI feature, Bhojan Guru with recipes from user's PDF file, Recipe Admin panel for MGT, and HR Letters generation.

## Project Overview
**Purnabramha IntraPB** - Internal portal for attendance, salary management, HR documents, and guest response for Purnabramha Restaurant Chain (Manswini Foods Pvt. Ltd.)

## What's Been Implemented

### Latest Update (Feb 22, 2026 - Session 4)

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

## Recipe Categories & Counts
| Category | Count | Examples |
|----------|-------|----------|
| SNACKS | 15 | Kanda Bhaji, Batata Vada, Kothimbir Vadi |
| DRINKS | 10 | Solkadhi, Masala Buttermilk, Aam Panha |
| BALGOPAL | 2 | Balgopal Aloochi Bhaji, Balgopal Misal Pav |
| MAINS | 6 | Aloo Bhaji, Zhunka, Misal Usal |
| CURRIES | 8 | Bharli Vangi, Kaju Curry, Special Kadhi |
| RICE | 2 | Masale Bhaat, Plain Rice |
| CHAPATI | 4 | Tandalachi Bhakri, Jowar Bhakri, Puri |
| SWEETS | 19 | Puran Poli, Gajar Halwa, Modak, Shrikhand |
| CHUTNEYS | 8 | Green Chutney, Thecha, Tamarind Chutney |
| SALADS | 5 | Gajar Koshimber, Kakdi Koshimber |

## Key API Endpoints

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

### HR Letters
- `POST /api/hr/generate-letter` - Generate HR letter with AI
- `POST /api/hr/download-letter-pdf` - Download letter as PDF
- `POST /api/hr/download-letter-word` - Download letter as DOCX

## Key Files
- `/app/backend/server.py` - Main API server
- `/app/backend/recipes_db.json` - 79 recipes from user's PDF
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

## Testing Credentials
- Center: PB-MGT
- Mobile: 9741399190
- Master OTP (dev mode): 123456

## Test Reports
- `/app/test_reports/iteration_6.json` - Centers & Managers tests
- `/app/test_reports/iteration_7.json` - Recipe Admin tests (100% pass)

## Backlog/Future
- Add company CIN number to HR letter templates
- Email generated letters directly to employees
- Refactor server.py into modular FastAPI routers
- Add image upload (currently URL only)
