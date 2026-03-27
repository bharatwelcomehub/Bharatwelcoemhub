# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
Internal management system for Purnabramha restaurant franchise. Includes financial features (MIS, sales, expenses), attendance, payroll, HR letters, recipes, guest management, employee transfers, and international (Perth) attendance with hourly rates.

## Architecture
```
/app/backend/
├── server.py              # Auth, employees, advances, data seeding, startup hooks
├── routes/
│   ├── attendance.py      # Transfer-aware attendance (daily + monthly)
│   ├── payroll.py         # Transfer-aware salary preview + generation
│   ├── transfers.py       # Employee transfer request/accept/reject
│   ├── international_attendance.py  # Perth attendance + PDF export
│   ├── mis_dashboard.py   # MIS charts + working capital + center filtering
│   ├── hr_letters.py      # EXTRACTED from server.py - AI letter generation
│   ├── centers_managers.py # EXTRACTED from server.py - CRUD for centers & managers
│   ├── sales_expenses.py
│   ├── expense_attachments.py
│   ├── net_revenue.py
│   ├── booking_intelligence.py
│   └── recipes.py
/app/frontend/src/pages/
├── Attendance.jsx         # Transfer badges (IN/OUT) in daily + monthly views
├── Salary.jsx             # Shows transferTag + workingCenter
├── MISDashboard.jsx       # Center filtering fixed, Working Capital, Export
├── InternationalAttendance.jsx  # PDF export added
├── EmployeeTransfers.jsx
├── CentersManagement.jsx
└── ... (20+ pages)
```

## Completed - Session Mar 27, 2026 (Current)

### P1: Attendance Integration for Transfers (DONE, 100% tested)
- `attendance_month` and `attendance_by_date` return `transfer_tag` (HOME/TRANSFERRED_IN/TRANSFERRED_OUT) and `transfer_info`
- `bulk_attendance` skips marking for transferred-out employees
- `/api/employees` returns transfer context (tag, from, to)
- Frontend shows IN/OUT badges, disables editing for transferred-out

### P1: Payroll Mapping to Working Center (DONE, 100% tested)
- `salary_preview` includes `transferTag` and `workingCenter` per employee
- Attendance fetched from actual working center (not home center)
- Permanently transferred-in employees added to payroll automatically

### P2: PDF Export for International Payroll (DONE, 100% tested)
- `/api/international-attendance/export/monthly-pdf` generates reportlab PDF
- PDF includes header, summary, employee table with weekly hours, rates, totals
- Frontend button added with red styling on export tab

### P2: server.py Refactoring (DONE, 100% tested)
- HR Letters → `routes/hr_letters.py` (generate, download, employees, custom)
- Centers & Managers → `routes/centers_managers.py` (CRUD, dedup, roles)
- Old attendance endpoints removed from server.py (routes/attendance.py handles them)

## Completed - Session Mar 27, 2026 (Previous Fork)
- MIS Dashboard center filtering fix (independent center dropdown)
- Working Capital Remaining chart
- MIS Report Excel export
- Expense Entry sorting + batch entry ("Add 3 More Entries")

## Completed - Earlier Sessions
- Employee Transfer / Accept Shift workflow
- International Attendance RBAC overhaul
- Payslip PDF fix, center code normalization, deduplication
- All core modules (attendance, sales, expenses, recipes, HR letters, etc.)

## Testing Credentials
- Super Admin: PB-MGT, Mobile 9741399190, OTP 123456
- Perth Manager: PB-PERTH, Mobile 0401832922, OTP 123456
- India Manager: PB-HSR, Mobile 9999999999, OTP 123456

## Test Reports
- iteration_24.json: Transfer-aware attendance/payroll, PDF export, refactoring (100%, 14/14)
- iteration_23.json: MIS Dashboard v2 + Expense enhancements (100%, 18/18)
- iteration_22.json: Employee Transfers (100%, 24/24)

## Backlog

### P1
- Approval hierarchy config (admin approval before destination center receives transfer)

### P2
- WhatsApp/Email notification hooks for transfers
- OTP Email verification on live site (works in preview)

### P3
- Image Upload for Recipes
- Franchise Deal Simulator
- International center support for transfers
- 7-year retention deletion prompt

## Project Health
- Broken: None
- Mocked: WhatsApp Integration
