# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
Internal management system for Purnabramha restaurant franchise. Includes financial features, attendance, payroll, HR letters, recipes, guest management, and employee transfers.

## Latest Session (Mar 26, 2026) - Employee Transfer Feature

### Employee Transfer / Accept Shift (COMPLETE - 100% tested)

**Core Workflow:**
- Create transfer request (Temporary or Permanent)
- Destination center manager accepts/rejects
- On accept: employee center auto-updates
- Temporary transfers auto-complete after end date

**Features Built:**
1. Full CRUD: Create, Accept, Reject, Cancel transfers
2. Manager Dashboard: Incoming / Outgoing / Active Shifts
3. Transfer Types: Temporary (date range) and Permanent
4. Employee Master auto-update on acceptance
5. Notifications for all transfer events
6. Complete audit trail / history
7. Center-wise transfer summary reports
8. Validation: no self-transfer, no overlapping dates, no duplicate active transfers
9. Auto-complete expired temporary transfers on startup

**Database Collections:**
- `transfer_requests`: Full transfer lifecycle with audit fields
- `transfer_notifications`: In-app notification system
- `employees`: Added `home_center`, `current_operating_center`, `transfer_status`, `active_transfer_id`

**API Endpoints:**
- POST /api/transfers/create
- POST /api/transfers/action (accept/reject/cancel)
- POST /api/transfers/list
- POST /api/transfers/history
- POST /api/transfers/reports/summary
- POST /api/transfers/notifications
- POST /api/transfers/notifications/mark-read
- POST /api/transfers/employee-status
- POST /api/transfers/auto-complete-expired

### Previous Changes This Session
- International Attendance RBAC overhaul (9/9 tests passed)
- Center Master "Is India Center?" flag
- Data save bug fix (per-employee hours)
- Center code normalization (PB-PERTH- → PB-PERTH)
- Update Hourly Rate UI
- Payslip PDF text overlap fix

## Testing Credentials
- Super Admin: PB-MGT, Mobile 9741399190, OTP 123456
- Perth Manager: PB-PERTH, Mobile 0401832922, OTP 123456
- India Manager: PB-HSR, Mobile 9999999999, OTP 123456

## Test Reports
- /app/test_reports/iteration_22.json - Employee Transfers (100% pass, 24/24 backend + all frontend)
- /app/test_reports/iteration_21.json - RBAC overhaul (100% pass, 9/9)

## Backlog
### P1
- Attendance integration: transferred employees appear in correct center
- Status tags in attendance: "Home", "Transferred In", "Transferred Out"
- Duplicate attendance prevention across centers
- Payroll mapping to actual working center

### P2
- PDF export for International payroll reports
- Complete server.py refactoring
- Approval hierarchy config (admin approval before destination)
- WhatsApp/Email notification hooks

### P3
- Image Upload for Recipes
- Franchise Deal Simulator
- International center support for transfers

## Project Health
- Broken: None
- Mocked: WhatsApp Integration
