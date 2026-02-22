# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
User had existing HTML/Python files for an attendance and salary management system using Excel as database storage. Required migration to MongoDB with modern UI design while preserving all functionality. Added Guest Response AI feature, Bhojan Guru with recipes from user's PDF file, and Recipe Admin panel for MGT.

## Project Overview
**Purnabramha IntraPB** - Internal portal for attendance, salary management, and guest response for Purnabramha Restaurant Chain (Manswini Foods Pvt. Ltd.)

## What's Been Implemented

### Latest Update (Feb 22, 2026 - Session 2)
- ✅ **Salary Excel CREDIT_NARR/DEB_NARR Fix**
  - CREDIT_NARR and DEBIT_NARR columns now ONLY populated when employee has Notes/Remark field filled
  - Employees without remark have empty NARR columns

- ✅ **Bhojan Guru Complete Overhaul** - Matching original purnabramhai.html logic
  - **Region Thali Tab**: Day-wise regional thali recommendations
    - Sunday: Kolhapur - Mahalaxmi Thali
    - Monday: Pune - Peshwe Thali
    - Tuesday: Vidarbha - Vidarbha Thali
    - Wednesday: Konkan - Konkan Thali
    - Thursday: Marathwada - Marathwada Thali
    - Friday: Mumbai - Mumbai Street Special
    - Saturday: Khandesh - Khandeshi Thali
  - **Body Need Tab**: 6-question questionnaire with AI recommendations
    - Energy, Digestion, Mood, Spice comfort, Purpose, Weather
  - **Recipes Tab**: 42+ recipes with category filters (Drinks, Snacks, Mains, Sweets, Fasting, Chutneys)
  - **Menu Descriptions Tab**: English and Marathi descriptions

### Previous Implementations
- ✅ **OTP Email System** - Using EXACT method from original server.py
- ✅ **Recipe Admin Panel (MGT Only)** - Full CRUD for recipes
- ✅ **Guest Response AI with Center Selector**
- ✅ **Salary Generation** - Excel file with ICICI bank format
- ✅ **Payslip PDF Generation** - Formatted to match user's template

## Key API Endpoints
- `GET /api/bhojan_guru` - Returns bhojanGuru items, regionWise data, bodyNeedMatrix
- `POST /api/bhojan_guru/body_need` - AI recommendations based on body needs
- `GET /api/bhojan_guru/region/{day}` - Day-wise regional thali
- `POST /api/generate_salary` - Generate salary Excel with NARR logic
- `POST /api/payslips_generate` - Generate payslip PDFs

## Key Files
- `/app/backend/server.py` - Main API server
- `/app/backend/bhojan_guru_data.json` - Bhojan Guru region/body need data
- `/app/backend/recipe_data.json` - 42 recipes from PDF
- `/app/backend/config.json` - Email/SMTP configuration
- `/app/frontend/src/pages/BhojanGuru.jsx` - Bhojan Guru frontend

## Centers & Managers
| Center | Manager | Mobile | Email |
|--------|---------|--------|-------|
| PB-MGT | Jayanti Kathale | 9741399190 | jayanti.kathale@purnabramha.com |
| PB-MGT | Sandeep Gadhwal | 9960886185 | sandeep.gadhwal@purnabramha.com |

## Testing Credentials
- Center: PB-MGT
- Mobile: 9741399190
- Master OTP (dev mode): 123456
- OTP sent to manager's registered email

## Test Reports
- `/app/test_reports/iteration_5.json` - All tests passed (100% backend, 100% frontend)

## Verified Features
1. Bhojan Guru Region Thali - All 7 days working
2. Bhojan Guru Body Need - 6 questions, returns recommendations
3. Salary Excel NARR columns - Only populated with remark
4. Payslip PDF generation - MANASWINI FOODS PVT. LTD. format
5. OTP Email delivery - Working with user's SMTP credentials

## Backlog/Future
- Refactor server.py into modular FastAPI routers for better maintainability
- Add more Bhojan Guru items based on user feedback
