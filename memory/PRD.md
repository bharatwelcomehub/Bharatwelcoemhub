# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
User had existing HTML/Python files for an attendance and salary management system using Excel as database storage. Required migration to MongoDB with modern UI design while preserving all functionality. Added Guest Response AI feature, Bhojan Guru with recipes from user's PDF file, Recipe Admin panel for MGT, and HR Letters generation.

## Project Overview
**Purnabramha IntraPB** - Internal portal for attendance, salary management, HR documents, and guest response for Purnabramha Restaurant Chain (Manswini Foods Pvt. Ltd.)

## What's Been Implemented

### Latest Update (Mar 26, 2026 - Session 25)

- **UPDATE HOURLY RATE UI (COMPLETE)**
  - Pencil icon next to Rate column in International Attendance table
  - Click opens modal with employee name, category, current rate
  - Input for new hourly rate with Save/Cancel buttons
  - Backend endpoint refactored: POST /api/international-attendance/update-rate (JSON body)
  - Rate update reflects immediately after save
  - Tested: 100% pass (8/8 backend, all frontend)

- **DUPLICATE PB-PERTH CENTER FIX (COMPLETE)**
  - Removed duplicate PB-PERTH entry from database
  - Merged currency/GST fields (AUD, 10% GST inclusive) into remaining entry
  - Now only 1 PB-PERTH center exists

- **PAYSLIP PDF TEXT OVERLAP FIX (COMPLETE)**
  - Root cause: Net Salary box bottom (1.3") overlapped with footer "Purnabramha" text (1.3")
  - Fix: Raised box_bottom from 1.8" to 2.2", adjusted net salary section to use relative positioning
  - Footer text repositioned to 1.15" to maintain clear gap
  - Recurring issue (4x) now resolved

### Previous Update (Mar 26, 2026 - Session 24)

- INTERNATIONAL ATTENDANCE MODULE (COMPLETE)
- EXPENSE BILL ATTACHMENT FEATURE (COMPLETE)
- INVOICE GROUPING FEATURE (COMPLETE)
- CA/AUDITOR EXPORT (COMPLETE)

### Previous Updates
(See CHANGELOG.md for full history of Sessions 1-23)

## Key API Endpoints

### International Attendance
- GET /api/international-attendance/centers - List international centers
- POST /api/international-attendance/week-data - Get weekly attendance
- POST /api/international-attendance/save - Save weekly hours
- POST /api/international-attendance/monthly-report - Monthly payroll report
- POST /api/international-attendance/update-rate - Update employee hourly rate (NEW)
- POST /api/international-attendance/export/weekly-excel - Export weekly CSV
- POST /api/international-attendance/export/monthly-excel - Export monthly CSV
- POST /api/international-attendance/export/attendance-sheet - Full attendance sheet

### Sales & Expenses
- POST /api/sales/expenses - Get expenses
- PUT /api/sales/expenses/{id} - Update expense (inline edit)
- POST /api/attachments/upload - Upload expense attachment
- GET /api/attachments/export/zip - Batched ZIP export

### Franchises
- POST /api/franchises/list - List franchises
- POST /api/center-accounts/summary - Financial summary
- POST /api/center-accounts/payout-summary - Monthly payouts

## Testing Credentials
- Super Admin: Center PB-MGT, Mobile 9741399190, OTP 123456
- Perth Manager: Center PB-PERTH, Mobile 0401832922, OTP 123456

## Database Collections
employees, centers, daily_sales, commission_statements, attendance_audit, guests, advances, hr_letters, payout_payments, chat_history, bookings, managers, unlock_requests, salary_rules, expenses, international_attendance, invoice_groups, franchise_exits, attendance, loan_entries, admin_freezes, payroll_locks, attendance_locks, franchises, franchise_audit, expense_heads, sessions, unlock_grants

## Backlog/Future Tasks

### P1 - Upcoming
- PDF export for International payroll reports
- Complete server.py refactoring (extract HR letters & centers/managers routes)

### P2 - Improvements
- Test file upload flow for Expense Attachments (visual UI verification)
- 7-year retention deletion prompt for attachments
- Frontend Babel build fix

### P3 - Future
- Image Upload for Recipes
- Franchise Deal Simulator
- Real WhatsApp Business API integration (currently MOCKED)
- Custom roles (Trainer, Marketing)

## Test Reports
- /app/test_reports/iteration_20.json - Session 25: Update Rate, Duplicate Fix, Payslip Fix (100% pass)
- /app/test_reports/iteration_19.json - Previous session tests

## Project Health
- Broken: None
- Mocked: WhatsApp Integration
