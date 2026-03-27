# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
Internal management system for Purnabramha restaurant franchise. Includes financial features, attendance, payroll, HR letters, recipes, guest management, and employee transfers.

## Latest Session (Mar 27, 2026) - MIS Dashboard Fixes + Expense Enhancements

### MIS Dashboard Center Filtering Fix (COMPLETE - 100% tested)
- Fixed center dropdown: now loads from `/api/centers` independently (no longer depends on filtered overview response)
- All charts (pie, trends, expense analysis, center comparison) properly filter by selected center
- Added `center` parameter support to `/api/mis/center-comparison` endpoint

### Working Capital Remaining Chart (COMPLETE - 100% tested)
- New `/api/mis/working-capital` endpoint calculates cumulative (Sales - Expenses - GST) per day
- New "Working Capital" tab with: summary cards, composed bar+line chart, daily breakdown table

### MIS Report Export (COMPLETE - 100% tested)
- Export button generates multi-sheet Excel file (xlsx library)
- Sheets: Summary, Centers, Trends, Expenses, Working Capital, Quarterly

### Expense Entry Enhancements (COMPLETE - 100% tested)
- Sortable column headers: Date, Description, Category, Mode, Amount, Invoice, Bill
- Click to toggle asc/desc, visual sort indicators
- "Add 3 More Entries" button for batch expense entry
- Batch rows with save all / clear all / remove individual row

## Previous Session (Mar 26, 2026)

### Employee Transfer / Accept Shift (COMPLETE - 100% tested)
- Full CRUD: Create, Accept, Reject, Cancel transfers
- Manager Dashboard: Incoming / Outgoing / Active Shifts
- Transfer Types: Temporary (date range) and Permanent
- Employee Master auto-update on acceptance
- Auto-complete expired temporary transfers on startup

### International Attendance RBAC Overhaul (COMPLETE)
- Center Master "Is India Center?" flag
- Module visibility locked to Super Admin, Admin, Int'l Manager only
- Per-employee hours save fix, center code normalization

## Testing Credentials
- Super Admin: PB-MGT, Mobile 9741399190, OTP 123456
- Perth Manager: PB-PERTH, Mobile 0401832922, OTP 123456
- India Manager: PB-HSR, Mobile 9999999999, OTP 123456

## Test Reports
- /app/test_reports/iteration_23.json - MIS Dashboard v2 + Expense Enhancements (100% pass, 18/18 backend + all frontend)
- /app/test_reports/iteration_22.json - Employee Transfers (100% pass, 24/24 backend + all frontend)
- /app/test_reports/iteration_21.json - RBAC overhaul (100% pass, 9/9)

## Backlog
### P1
- Attendance integration: transferred employees appear in correct center
- Status tags in attendance: "Home", "Transferred In", "Transferred Out"
- Duplicate attendance prevention across centers
- Payroll mapping to actual working center
- Attendance marking maps to previous/new centers across transfer date boundary

### P2
- PDF export for International payroll reports
- Complete server.py refactoring (extract remaining monolithic routes)
- Approval hierarchy config (admin approval before destination)
- WhatsApp/Email notification hooks
- OTP Email verification on live site (works in preview)

### P3
- Image Upload for Recipes
- Franchise Deal Simulator
- International center support for transfers
- 7-year retention deletion prompt

## Project Health
- Broken: None
- Mocked: WhatsApp Integration
