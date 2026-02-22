# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
User had existing HTML/Python files for an attendance and salary management system using Excel as database storage. Required migration to MongoDB with modern UI design while preserving all functionality. Added Guest Response AI feature for managers to answer guest queries.

## Project Overview
**Purnabramha IntraPB** - Internal portal for attendance, salary management, and guest response for Purnabramha Restaurant Chain (Manswini Foods Pvt. Ltd.)

## Target Audience
- Restaurant center managers across India and Australia
- Management headquarters (PB-MGT) - Jayanti Kathale & Sandeep Gadhwal

## Core Requirements
1. **Authentication**: OTP-based login for center managers
2. **Attendance Management**: Daily and monthly tracking
3. **Advances Tracking**: Record salary advances
4. **Salary Generation**: Export for ICICI bank upload
5. **Payslip Generation**: PDF payslips
6. **Employee Management**: CRUD operations (PB-MGT only)
7. **Bhojan Guru**: Maharashtrian recipe database
8. **Guest Response AI**: GPT-5.2 powered assistant

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
| PB-PERTH | Perth, Australia | +61 401 832 922 |

## PB-MGT Admin Users
- Jayanti Kathale (Mobile: 9741399190)
- Sandeep Gadhwal (Mobile: 9960886185)

## What's Been Implemented (Jan 22, 2026)

### Backend APIs (26+ endpoints - 100% working)
- Authentication (send_otp, verify_otp)
- Employee CRUD (create, update, delete, list)
- Attendance (daily, monthly, bulk save)
- Advances management
- Payroll (status, lock, generate)
- Payslips generation
- **Guest AI** (OpenAI GPT-5.2 powered)
- Center info API

### Frontend Pages
- Login page with OTP verification
- Dashboard with sidebar navigation
- Attendance (Daily + Monthly + Advances)
- Employees management (MGT only)
- Salary generation (MGT only)
- Payslips generation (MGT only)
- Bhojan Guru recipe explorer
- **Guest Response AI** (chat interface)

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

### P1 (Future)
- Email OTP delivery (SMTP)
- Chat history per manager
- Employee self-service portal

### P2 (Nice to Have)
- Mobile app version
- Photo attendance
- Leave management

## Next Tasks
1. Configure SMTP for email OTP
2. Add attendance analytics dashboard
3. Import remaining employee data from Excel
