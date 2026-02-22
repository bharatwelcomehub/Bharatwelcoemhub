# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
User had existing HTML/Python files for an attendance and salary management system using Excel as database storage. Required migration to MongoDB with modern UI design while preserving all functionality. Added Guest Response AI feature for managers to answer guest queries. Updated Bhojan Guru with real recipe data and added center selector to Guest Response AI.

## Project Overview
**Purnabramha IntraPB** - Internal portal for attendance, salary management, and guest response for Purnabramha Restaurant Chain (Manswini Foods Pvt. Ltd.)

## Target Audience
- Restaurant center managers across India and Australia
- Management headquarters (PB-MGT) - Jayanti Kathale & Sandeep Gadhwal
- Chefs (for Bhojan Guru recipes)

## Core Requirements
1. **Authentication**: OTP-based login for center managers
2. **Attendance Management**: Daily and monthly tracking
3. **Advances Tracking**: Record salary advances
4. **Salary Generation**: Export for ICICI bank upload
5. **Payslip Generation**: PDF payslips
6. **Employee Management**: CRUD operations (PB-MGT only)
7. **Bhojan Guru**: Maharashtrian recipe database with 47 recipes, 5 thalis, 126 menu descriptions
8. **Guest Response AI**: GPT-5.2 powered assistant with center-specific context
9. **Recipe Admin**: Full CRUD for recipes (PB-MGT only)

## Centers & Contact Information
| Center | Location | Phone |
|--------|----------|-------|
| PB-HSR | Bangalore | +91 85500 78515 |
| PB-TH | Thane, Mumbai | +91 89047 49084 |
| PB-SN | Sambhajinagar | +91 89710 49084 |
| PB-DV | Dombivli, Mumbai | +91 96064 55433 |
| PB-HW | Hinjawadi, Pune | +91 96064 55434 |
| PB-KN | Kharadi, Pune | +91 99000 89803 |
| PB-KAL | Kalyan | +91 96064 55433 |
| PB-MEL | Melbourne, Australia | +61 401 832 922 |
| PB-PERTH | Perth, Australia | +61 401 832 922 |

## PB-MGT Admin Users
- Jayanti Kathale (Mobile: 9741399190)
- Sandeep Gadhwal (Mobile: 9960886185)

## What's Been Implemented

### Latest Update (Feb 22, 2026)
- ✅ **ResizeObserver Error Fixed**: Enhanced error suppression with debounced ResizeObserver
- ✅ **Bhojan Guru with Real Recipes**: Using exact data from RECIPE_DB.js and DESC_DB_WITH_MR.js
  - 47 recipes with ingredients and method steps
  - 5 thali configurations
  - 126 menu descriptions in English and Marathi
  - Copy to clipboard functionality for chefs
  - Category filters (All, Drinks, Snacks, Mains, Sweets, Thalis)
  
- ✅ **Recipe Admin Panel (MGT Only)**: Full CRUD for recipes
  - Create new recipes with ingredients and method steps
  - Edit existing recipes
  - Delete recipes
  - Search functionality
  - Category selection (Drinks, Snacks, Main Course, Sweets/Desserts)
  
- ✅ **Guest Response AI Center Selector**: Added dropdown to select specific center
  - All 8 centers available in dropdown
  - AI responds with center-specific context (address, phone, timings)
  - Selected center badge displayed in chat

- ✅ **OTP Email System**: SMTP email integration ready
  - Sends HTML-formatted OTP emails
  - Falls back to console logging when SMTP not configured
  - Beautiful email template with Purnabramha branding

### Backend APIs (35+ endpoints - 100% working)
- Authentication (send_otp, verify_otp)
- Employee CRUD (create, update, delete, list)
- Attendance (daily, monthly, bulk save)
- Advances management
- Payroll (status, lock, generate)
- Payslips generation
- **Guest AI** (OpenAI GPT-5.2 powered) with center context
- Center info API
- **Recipes API** (GET, POST, PUT, DELETE) - 47 recipes, 5 thalis
- **Descriptions API** (126 menu items with English + Marathi)

### Frontend Pages
- Login page with OTP verification
- Dashboard with sidebar navigation
- Attendance (Daily + Monthly + Advances)
- Employees management (MGT only)
- Salary generation (MGT only)
- Payslips generation (MGT only)
- **Bhojan Guru** - Recipe database with 3 tabs (Recipes, Thalis, Descriptions)
- **Guest Response AI** - Chat interface with center selector
- **Recipe Admin** - Full CRUD for recipes (MGT only)

### Database Collections
- managers, employees, attendance, advances, payroll_locks, salary_rules, chat_history

## Prioritized Backlog

### P0 (Completed)
- ✅ MongoDB migration
- ✅ OTP authentication (both MGT managers)
- ✅ Attendance management
- ✅ Employee CRUD
- ✅ Salary/Payslip generation
- ✅ Guest Response AI with GPT-5.2
- ✅ Center info with phone numbers
- ✅ Bhojan Guru with real recipe data (47 recipes, 126 descriptions)
- ✅ Guest Response center selector
- ✅ Recipe Admin panel (MGT only)
- ✅ ResizeObserver error fix

### P1 (Ready but needs config)
- 🟡 Email OTP delivery (SMTP code ready, needs credentials)
  - Add SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS to backend/.env

### P2 (Future)
- Chat history persistence per manager
- Employee self-service portal
- Mobile app version
- Photo attendance
- Leave management
- Attendance analytics dashboard

## Testing Status
- Backend: 100% tests passed
- Frontend: 100% tests passed
- Recipe CRUD: Tested and working

## Technical Notes

### OTP Email Configuration
To enable OTP emails, add to `/app/backend/.env`:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SMTP_FROM=noreply@purnabramha.com
```

### Recipe Data Files
- `/app/backend/recipe_data.json` - Parsed recipes (47 items from RECIPE_DB.js)
- `/app/backend/description_data.json` - Menu descriptions (126 items from DESC_DB_WITH_MR.js)

### Dev Mode OTP
For testing without email, OTP is logged to console and master OTP "123456" works.

### Recipe Admin Access
Only PB-MGT center managers can access Recipe Admin panel.
