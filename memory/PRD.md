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
  - All `session.center === "PB-MGT"` replaced with `isAdminUser(session)`
  - All `isPerth/PB-PERTH` checks replaced with `isInternationalCenter` using DB center data
  - All hardcoded CENTERS arrays replaced with `fetchCentersFromDB()` API calls
  - Backend `has_admin_access()` purely RBAC-driven
  - International centers cache populated at startup from DB
- [x] **P0: Role-based visibility enforcement**
  - Sidebar menu items controlled by admin/permission flags
  - Page-level access denied screens use isAdminUser() check
  - Backend routes check is_super_admin/is_admin instead of center codes
- [x] **Bug Fix: isPerth not defined** (COMPLETED 2026-03-27)
  - SalesDataEntry.jsx calculateGST renamed isPerth → isIntl with centersList prop
  - ExpenseEntry.jsx uses fmtCurrency wrapper with centersList
  - SalesGridEditor.jsx passes centersList for currency detection
- [x] **Center-Specific Menu Management** (COMPLETED 2026-03-27)
  - 146 real menu items seeded from India + Australia PDF menus
  - 17 categories: Balgopal Kids, Tea/Coffee, Snacks, Heavy Brunch, Bhaji, Thali, etc.
  - Per-center pricing: India (INR), Australia (AUD)
  - Per-center availability: some items not served at certain centers
  - MenuManagement.jsx: Admin-only page with center selector, pricing editor, search
  - Endpoints: /api/masters/menu-items/by-center/{code}, /api/masters/seed-menu-data

## Prioritized Backlog

### P0 — Critical
- Phase 3: Full Master-Driven Restaurant Billing Software (POS, KOT, Invoicing)

### P1 — High
- Franchise document management & Approval hierarchy
- Master tables to populate: Tables, Vendors, Order Types, Cancellation Reasons

### P2 — Medium/Future
- Image Upload for Recipes
- Franchise Deal Simulator
- 7-year retention deletion prompt for attachments
- Menu card PDF generation per center (sharable digital menu)

## Key DB Schema
- `permissions`: {role_key, permissions_list, description}
- `centers`: {code, name, phone, email, address, active, is_india_center, country, is_hq}
- `master_menu_items`: {name, category, base_price, serves, is_veg, center_prices: {CENTER: {price, available}}, is_active}
- `master_menu_categories`: {name, description, display_order}
- `employees`: {..., transfer_tag, transfer_info} (dynamically injected)

## Key API Endpoints
- `/api/centers`: Returns all centers from DB (with is_india_center, country, is_hq)
- `/api/masters/*`: CRUD for master tables
- `/api/masters/menu-items/by-center/{code}`: Center-specific menu with pricing
- `/api/masters/seed-menu-data`: Seeds 146 real menu items from PDF data
- `/api/permissions/engine`: Returns user role and capability matrix

## Test Credentials
- Super Admin: Center PB-MGT, Mobile 9741399190, OTP 123456

## Completed Features (continued)
- [x] **MIS Dashboard PDF Export** (COMPLETED 2026-03-27)
  - Backend `/api/mis/download-pdf` endpoint using ReportLab
  - Professional branded PDF with Purnabramha logo header
  - Includes: Financial Summary, Center Performance, Expense Analysis, Working Capital, Quarterly Comparison
  - Color-coded profit/loss cells, alert status highlights
  - Auto-detects international centers for currency symbol ($)
  - Supports all period filters (current month, quarter, YTD, custom)
- [x] **Premium MIS Dashboard UI** (COMPLETED 2026-03-27)
  - Dark-themed header with brand colors (saffron, gold, emerald)
  - 6 gradient KPI cards with change indicators
  - 7 tabbed sections: Overview, Working Capital, Centers, Expenses, Alerts, Quarterly, Performers
  - Recharts-based composited charts with premium tooltips
  - Alerts banner with severity badges
- [x] **Restaurant POS / Billing System** (COMPLETED 2026-03-27)
  - Full touchscreen-style POS UI with category sidebar, item grid (224 items), order panel
  - Billing config per country: India 5% GST exclusive, Australia 10% GST inclusive
  - Service charge: % or fixed amount, configurable by admin
  - Discounts: % or fixed at billing time
  - Payment modes: Cash / UPI / Card
  - KOT (Kitchen Order Ticket) with thermal printer format (80mm)
  - Bill generation with auto-numbered sequences (ORD-, KOT-, BILL-)
  - Bill void for admin users only, with reason tracking
  - Active orders list, order cancellation with reason
  - Daily report: item-wise & category-wise breakdown, payment mode split
  - Receipt dialog with Purnabramha branding, print button
  - 17 backend routes at /api/billing/*
  - **Separate sidebar section** "Billing / POS" (admin-only by default, assignable via Role Master `billing` module)
  - Role Management updated with "Billing / POS" permission module

## Key DB Schema (continued)
- `billing_config`: {country, gst_percentage, gst_type, service_charge_enabled, service_charge_type, service_charge_value, currency_symbol, currency_code}
- `orders`: {order_id, center, table_no, order_type, items[], status, kot_count, created_at, created_by}
- `bills`: {bill_no, order_id, center, items[], subtotal, gst_amount, service_charge_amount, discount_amount, grand_total, payment_mode, status, date}
- `kot_entries`: {kot_no, order_id, center, table_no, items[], printed_at, printed_by}
- `sequences`: {_id: "PREFIX-CENTER-DATE", seq: auto-increment}

## Prioritized Backlog (Updated)

### P0 — Critical
- Phase 3 continued: Billing Reports Dashboard, Daily Settlement, Void/Cancel Reports

### P1 — High
- Franchise document management & Approval hierarchy
- Master tables: Tables, Vendors, Order Types, Cancellation Reasons

### P2 — Medium/Future
- WhatsApp/Email notification hooks
- Image Upload for Recipes
- Franchise Deal Simulator
- 7-year retention deletion prompt for attachments

## Project Health
- Broken: None
- Mocked: WhatsApp Integration
- Fixed: Working Capital logic, muted colors, profit removed from all dashboards/exports

- Menu card PDF generation per center
