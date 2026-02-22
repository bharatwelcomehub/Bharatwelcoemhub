# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
User had existing HTML/Python files for an attendance and salary management system using Excel as database storage. Required migration to MongoDB with modern UI design while preserving all functionality.

## Project Overview
**Purnabramha IntraPB** - Internal portal for attendance and salary management for Purnabramha Restaurant Chain (Manswini Foods Pvt. Ltd.)

## Target Audience
- Restaurant center managers across India (HSR Bangalore, Thane, Dombivli, Kalyan, Sambhajinagar, Hinjawadi, Kharadi)
- International locations (Perth, Australia)
- Management headquarters (PB-MGT)

## Core Requirements
1. **Authentication**: OTP-based login for center managers
2. **Attendance Management**: Daily and monthly attendance tracking with status codes (P, A, HD, WO, L)
3. **Advances Tracking**: Record salary advances with payment modes
4. **Salary Generation**: Export salary data for ICICI bank bulk upload
5. **Payslip Generation**: PDF payslips for employees
6. **Employee Management**: CRUD operations for PB-MGT only
7. **Bhojan Guru**: Maharashtrian recipe database with Marathi descriptions

## Tech Stack
- **Frontend**: React.js with Tailwind CSS
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Authentication**: OTP-based with email verification

## What's Been Implemented (Jan 22, 2026)

### Backend APIs (21 endpoints - 100% working)
- `/api/send_otp` - Send OTP to manager
- `/api/verify_otp` - Verify OTP and create session
- `/api/employees` - Get employees by center
- `/api/mgt_employees_list` - Get all employees (MGT only)
- `/api/mgt_employee_create` - Create employee
- `/api/mgt_employee_update` - Update employee
- `/api/mgt_employee_delete` - Delete employee
- `/api/bulk_attendance` - Save daily attendance
- `/api/attendance_by_date` - Get attendance for date
- `/api/attendance_month` - Get monthly grid
- `/api/bulk_attendance_month` - Save monthly attendance
- `/api/bulk_advances` - Save advances
- `/api/advances_by_date` - Get advances for date
- `/api/advances_by_month` - Get monthly advances
- `/api/payroll_status` - Check payroll lock status
- `/api/lock_payroll` - Lock payroll for month
- `/api/generate_salary` - Generate salary Excel
- `/api/payslips_generate` - Generate PDF payslips
- `/api/recipes` - Get recipes
- `/api/seed_data` - Seed initial data
- `/api/centers` - Get center list

### Frontend Pages
- Login page with OTP verification
- Dashboard with sidebar navigation
- Attendance page (Daily + Monthly + Advances tabs)
- Employees page (MGT only)
- Salary generation page (MGT only)
- Payslips generation page (MGT only)
- Bhojan Guru recipe explorer

### Database Collections
- managers - Center manager credentials
- employees - Employee data
- attendance - Daily attendance records
- advances - Salary advance records
- payroll_locks - Month-wise payroll locks
- salary_rules - Salary calculation rules

## User Personas
1. **Center Manager**: Marks daily attendance, records advances
2. **HQ Admin (PB-MGT)**: Manages employees, generates salary, payslips, locks payroll

## Prioritized Backlog

### P0 (Completed)
- ✅ MongoDB migration from Excel
- ✅ OTP authentication
- ✅ Attendance management
- ✅ Employee CRUD
- ✅ Salary generation
- ✅ Modern UI design

### P1 (Future)
- Email OTP delivery integration (currently logged to console)
- Employee self-service portal
- Attendance reports/analytics dashboard

### P2 (Nice to Have)
- Mobile app version
- Multi-language support (beyond Marathi)
- Photo attendance with face recognition
- Leave management system

## Next Tasks
1. Configure SMTP for actual email OTP delivery
2. Add attendance analytics dashboard
3. Implement employee self-service portal
