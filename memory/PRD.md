# Purnabramha IntraPB Portal — Product Requirements Document

## Original Problem Statement
Internal management system for "Purnabramha," a restaurant franchise. The system manages attendance, payroll, sales/expenses, HR letters, employee transfers, booking intelligence, MIS dashboards, and franchise operations across multiple centers in India and Australia.

## Architecture: MASTER-DATA-FIRST, ROLE-BASED, NO-HARDCODING
- All center names, roles, expense categories, payment modes fetched from MongoDB master tables
- Strict RBAC via Permission Engine (Super Admin, Admin, Center Manager, Franchise Owner)
- No hardcoded center codes (PB-MGT, PB-PERTH, etc.) in access control logic

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS
- Backend: FastAPI + Python
- Database: MongoDB
- Libraries: xlsx (Excel), ReportLab (PDF), Emergent Object Storage

## User Personas
- **Super Admin**: Full access to all modules, centers, and settings
- **Admin**: Full access to operations, limited settings
- **Center Manager**: Access only to their assigned center's data
- **Franchise Owner**: View-only dashboard for their mapped business entity

## Completed Features
- [x] Phase 1 & 2: Master Data Tables (16 master collections), Permission Engine, Franchise Owner Dashboard
- [x] MIS Dashboard with center filtering, Working Capital Graph, XLSX Export
- [x] Expense Entry Grid with sorting and batch add
- [x] Attendance integration for transferred employees (HOME/TRANSFERRED badges)
- [x] Payroll mapping to actual working center for transfers
- [x] PDF export for international payroll reports
- [x] server.py refactoring (hr_letters.py, centers_managers.py extracted)
- [x] **P0: Hardcoding removal across 34+ files** (COMPLETED 2026-03-27)
  - All `session.center === "PB-MGT"` replaced with `isAdminUser(session)` (checks is_super_admin || is_admin)
  - All `isPerth/PB-PERTH` checks replaced with `isInternationalCenter` using DB center data (is_india_center field)
  - All hardcoded CENTERS arrays replaced with `fetchCentersFromDB()` API calls
  - Backend `has_admin_access()` no longer checks center == PB-MGT
  - International centers cache populated at startup from DB
  - Booking intelligence phone numbers fetched from center DB records
  - All 17 automated tests passed (100% backend, 100% frontend)
- [x] **P0: Role-based visibility enforcement**
  - Sidebar menu items controlled by admin/permission flags
  - Page-level access denied screens use isAdminUser() check
  - Backend routes check is_super_admin/is_admin instead of center codes

## Prioritized Backlog

### P0 — Critical
- Phase 3: Full Master-Driven Restaurant Billing Software (POS, KOT, Invoicing)

### P1 — High
- Franchise document management & Approval hierarchy
- Master tables to populate: Menu Items, Tables, Vendors, Order Types, Cancellation Reasons

### P2 — Medium/Future
- Image Upload for Recipes
- Franchise Deal Simulator
- 7-year retention deletion prompt for attachments

## Key DB Schema
- `permissions`: {role_key, permissions_list, description}
- Master collections: expense_categories, payment_modes, employee_categories, tax_config, menu_categories, roles
- `centers`: {code, name, phone, email, address, active, is_india_center, country, is_hq}
- `employees`: {..., transfer_tag, transfer_info} (dynamically injected)

## Key API Endpoints
- `/api/centers`: Returns all centers from DB (with is_india_center, country, is_hq fields)
- `/api/masters/*`: CRUD for master tables
- `/api/permissions/engine`: Returns user role and capability matrix
- `/api/attendance_month`, `/api/payroll/preview`: Transfer-aware

## Test Credentials
- Super Admin: Center PB-MGT, Mobile 9741399190, OTP 123456

## Project Health
- Broken: None
- Mocked: WhatsApp Integration
