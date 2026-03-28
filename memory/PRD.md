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
- [x] P0: Hardcoding removal across 34+ files
- [x] P0: Role-based visibility enforcement
- [x] Bug Fix: isPerth not defined
- [x] Center-Specific Menu Management (146 real menu items)
- [x] MIS Dashboard PDF Export (ReportLab branded)
- [x] Premium MIS Dashboard UI (White theme, 7 tabbed sections)
- [x] Restaurant POS / Billing System (Full touchscreen UI, 17 backend routes)
- [x] **Expense Entry Amount Width Fix** (COMPLETED 2026-03-28) — Widened amount input fields (min-w-[140px] new entry, min-w-[120px] inline/batch, w-36 column header)
- [x] **Franchise Dashboard Connectivity Link** (COMPLETED 2026-03-28) — Green card with franchise owner name when connected, amber "Vacant" card when not. Uses new `/api/franchises/by-center/{center_code}` endpoint with multi-strategy lookup.
- [x] **MIS Working Capital Center-wise Mapping** (COMPLETED 2026-03-28) — Backend now builds `center_franchise_map` from `franchises` collection. Each center shows WC from its mapped franchise record. Super Admin sees all, franchise owner sees their mapped center.

## Key DB Schema
- `permissions`: {role_key, permissions_list, description}
- `centers`: {code, name, phone, email, address, active, is_india_center, country, is_hq}
- `master_menu_items`: {name, category, base_price, serves, is_veg, center_prices: {CENTER: {price, available}}, is_active}
- `master_menu_categories`: {name, description, display_order}
- `franchises`: {franchise_code, franchise_name, legal_entity_name, country, city, working_capital, primary_contact_name, primary_contact_email, primary_contact_phone, status, ...}
- `loan_entries`: {center, franchise_code, franchise_name, amount, total_repaid, working_capital_at_time, status, repayments[]}
- `billing_config`: {country, gst_percentage, gst_type, service_charge_enabled, ...}
- `orders`: {order_id, center, table_no, order_type, items[], status, kot_count, ...}
- `bills`: {bill_no, order_id, center, items[], subtotal, gst_amount, grand_total, payment_mode, status, ...}

## Key API Endpoints
- `/api/centers`: Returns all centers from DB
- `/api/masters/*`: CRUD for master tables
- `/api/mis/working-capital`: Center-wise working capital (franchise deposit - loans)
- `/api/franchises/by-center/{code}`: Get franchise mapped to a center (new)
- `/api/franchises/list`: List all franchises
- `/api/billing/*`: POS billing routes (17 endpoints)
- `/api/mis/download-pdf`: Branded MIS PDF report

## Test Credentials
- Super Admin: Center PB-MGT, Mobile 9741399190, OTP 123456

## Prioritized Backlog

### P0 — Critical
- Billing/POS Configuration Module Overhaul: Move Menu Management under "Configuration" submenu in Billing/POS. Build CRUD for Menu Categories, Subcategories, Items, Tables, Cancellation Reasons.
- POS Workflow Update: Dine-in = Table Selection first → Guest Count → Item entry. Pickup/Delivery = Mandatory Mobile + Customer Name.
- KOT/Bill Cancellation Engine: Cancellation with mandatory reason (from master), role-checks, audit trail.

### P1 — High
- Franchise document management & Approval hierarchy
- Commission tracking module (Platform/Card commissions + GST) — Required before "Profit" metrics can be re-enabled
- WhatsApp/Email notification hooks

### P2 — Medium/Future
- Image Upload for Recipes
- Franchise Deal Simulator
- 7-year retention deletion prompt for attachments
- Menu card PDF generation per center

## Project Health
- Broken: None
- Mocked: WhatsApp Integration
- Hidden: Net Profit metrics (until commission module is built)
