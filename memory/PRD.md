# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
Internal management system for Purnabramha restaurant franchise. Includes financial features (MG, Revenue/Profit Share), attendance, payroll, HR letters, recipes, and guest management.

## What's Been Implemented

### Session 25 (Mar 26, 2026) - International Attendance Major Overhaul

**RBAC & Visibility Control (COMPLETE - 100% tested)**
- International Attendance visible ONLY to: Super Admin, Admin, International Center Managers
- India center managers see "Access Restricted" (403 from backend)
- Center dropdown shows ONLY international centers (is_india_center=false) for Admin/Super Admin
- International center managers see fixed badge with their center code — no dropdown
- Sidebar hides International Attendance from India center managers

**Center Master: "Is India Center?" Flag (COMPLETE)**
- Added `is_india_center` boolean field to centers collection
- Auto-set on startup: PERTH/non-India country = false, everything else = true
- Toggle visible in Centers Management Add/Edit dialogs
- "Intl" badge shows for international centers in list

**Data Save Bug Fix (COMPLETE)**
- Root cause: Production employees lacked `employee_id` field → all shared `None` key → editing one updated all
- Fix: Uses MongoDB `_id` as fallback unique identifier
- Uses `designation` field as fallback for `category`
- Verified: ASHA=8hrs, MANISH=4hrs saved independently

**Center Code Normalization (COMPLETE)**
- `PB-PERTH-` auto-renamed to `PB-PERTH` on startup
- Duplicate centers auto-removed (keeps richest entry)
- All queries use `center_code_variants()` for mismatch handling

**Other Fixes**
- Update Hourly Rate UI: Pencil icon + modal in attendance table
- Payslip PDF text overlap: Fixed box_bottom from 1.8" to 2.2"
- Delete visible for Admin + Super Admin in Centers Management

## Key API Endpoints (International Attendance)
- GET /api/international-attendance/centers - RBAC-filtered centers
- POST /api/international-attendance/week-data - Weekly hours (with access check)
- POST /api/international-attendance/save - Save hours (with access check)
- POST /api/international-attendance/update-rate - Update hourly rate
- POST /api/international-attendance/monthly-report - Monthly payroll
- POST /api/international-attendance/export/* - CSV exports

## Testing Credentials
- Super Admin: PB-MGT, Mobile 9741399190, OTP 123456
- Perth Manager: PB-PERTH, Mobile 0401832922, OTP 123456
- India Manager (test): PB-HSR, Mobile 9999999999, OTP 123456

## Test Reports
- /app/test_reports/iteration_21.json - Session 25: RBAC overhaul (100% pass, 9/9)
- /app/test_reports/iteration_20.json - Session 25: Initial fixes (100% pass, 8/8)

## Backlog
### P1
- PDF export for International payroll reports
- Complete server.py refactoring (HR letters, centers/managers routes)

### P2
- Test expense attachment file upload flow visually
- 7-year retention deletion prompt for attachments
- Frontend Babel build fix

### P3
- Image Upload for Recipes
- Franchise Deal Simulator
- Real WhatsApp Business API (currently MOCKED)

## Project Health
- Broken: None
- Mocked: WhatsApp Integration
