# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
User had existing HTML/Python files for an attendance and salary management system using Excel as database storage. Required migration to MongoDB with modern UI design while preserving all functionality. Added Guest Response AI feature, Bhojan Guru with recipes from user's PDF file, Recipe Admin panel for MGT, and HR Letters generation.

## Project Overview
**Purnabramha IntraPB** - Internal portal for attendance, salary management, HR documents, and guest response for Purnabramha Restaurant Chain (Manswini Foods Pvt. Ltd.)

## What's Been Implemented

### Latest Update (Feb 22, 2026 - Session 3)

- ✅ **Payslip PDF Format Fixed**
  - Fixed text overlap issue (NET TAKE/Rs. overlapping)
  - Added proper spacing between fields
  - Updated footer with Purnabramha branding
  - **New Signature**: "Mr. Sandeep Gadhwal, Director, MANASWINI FOODS PVT. LTD."

- ✅ **HR Letters Generator (AI-Powered)** - New Feature
  - **Offer Letter**: Generate professional offer letters for new employees
  - **Exit Letter**: Resignation acceptance letters
  - **Experience Letter**: Work experience certificates
  - **Visa/Immigration Letter**: Support letters for visa applications with:
    - Destination country
    - Visa number
    - Travel purpose (business, training, project work)
    - Travel duration and dates
    - Inviting company/organization
    - Project details
  - Uses GPT-5.2 for professional content generation
  - Picks employee data from database automatically
  - MGT-only access

### Previous Implementations
- ✅ **Salary Excel CREDIT_NARR/DEB_NARR** - Uses remark if filled, defaults otherwise
- ✅ **Bhojan Guru** - Region Thali, Body Need questionnaire, Recipes, Menu Descriptions
- ✅ **OTP Email System** - Live email delivery
- ✅ **Recipe Admin Panel (MGT Only)** - Full CRUD for recipes
- ✅ **Guest Response AI** - Center-based AI responses

## Key API Endpoints

### HR Letters
- `GET /api/hr_letter/employees?token=` - Get employees list (MGT only)
- `POST /api/hr_letter/generate` - Generate HR letter with AI

### Other Endpoints
- `GET /api/bhojan_guru` - Bhojan Guru data
- `POST /api/bhojan_guru/body_need` - Body need recommendations
- `POST /api/generate_salary` - Generate salary Excel
- `POST /api/payslips_generate` - Generate payslip PDFs

## Key Files
- `/app/backend/server.py` - Main API server with HR Letters endpoints
- `/app/frontend/src/pages/HRLetters.jsx` - HR Letters UI
- `/app/frontend/src/pages/Dashboard.jsx` - Updated with HR Letters nav

## Centers & Managers
| Center | Manager | Mobile | Email |
|--------|---------|--------|-------|
| PB-MGT | Jayanti Kathale | 9741399190 | jayanti.kathale@purnabramha.com |
| PB-MGT | Sandeep Gadhwal | 9960886185 | sandeep.gadhwal@purnabramha.com |

## Testing Credentials
- Center: PB-MGT
- Mobile: 9741399190
- Master OTP (dev mode): 123456

## Verified Features
1. Payslip PDF - Fixed formatting, proper signature
2. HR Letters - All 4 types working (offer, exit, experience, visa)
3. Visa letters include all travel details from form inputs
4. Employee data pulled from database automatically

## Backlog/Future
- Add company CIN number to letter templates
- Generate PDF versions of HR letters
- Add letterhead/logo to PDF letters
- Email generated letters directly to employees
