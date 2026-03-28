# Purnabramha IntraPB Portal — Product Requirements Document

## Original Problem Statement
Internal management system for "Purnabramha," a restaurant franchise. The system manages attendance, payroll, sales/expenses, HR letters, employee transfers, booking intelligence, MIS dashboards, and franchise operations across multiple centers in India and Australia.

## Architecture: MASTER-DATA-FIRST, ROLE-BASED, NO-HARDCODING
- All center names, roles, expense categories, payment modes fetched from MongoDB master tables
- Strict RBAC via Permission Engine (Super Admin, Admin, Center Manager, Franchise Owner)
- No hardcoded center codes in access control logic

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS
- Backend: FastAPI + Python
- Database: MongoDB
- Libraries: xlsx (Excel), ReportLab (PDF), Emergent Object Storage

## Key DB Collections
- `billing_tables`: {table_id, table_no, center, capacity, floor, section, status, is_active}
- `billing_cancel_reasons`: {reason_id, reason, type (order/bill/kot), is_active}
- `billing_audit_trail`: {action, order_id/bill_no/kot_no, center, reason_id, reason, cancelled_by, cancelled_by_role, timestamp, items, total}
- `master_menu_categories`: {category_id, name, description, display_order, is_active}
- `master_menu_items`: {name, category, base_price, center_prices, is_active}
- `orders`: {order_id, center, table_no, table_id, order_type, guest_count, customer_name, customer_phone, items[], status, kot_count}
- `bills`: {bill_no, order_id, center, items[], subtotal, gst_amount, grand_total, payment_mode, status, void_reason_id}
- `franchises`: {franchise_code, franchise_name, working_capital, primary_contact_name, status}

## Completed Features
- [x] Master Data Tables (16 master collections), Permission Engine, Franchise Owner Dashboard
- [x] MIS Dashboard with center filtering, Working Capital, XLSX/PDF Export (White theme)
- [x] Expense Entry Grid with wider amount fields, batch add
- [x] Attendance for transfers, Payroll mapping, PDF exports
- [x] Franchise connectivity indicator (green=connected, amber=vacant)
- [x] MIS Working Capital center-wise from franchise DB
- [x] **Billing/POS Configuration Module** (COMPLETED 2026-03-28)
  - Sidebar restructured: Billing/POS → POS/Billing, Configuration, Menu Items
  - Tables CRUD per center (table_no, capacity, floor, section, status)
  - Cancellation Reasons CRUD (order/bill/kot types)
  - Menu Categories CRUD (name, display_order)
- [x] **POS Workflow Update** (COMPLETED 2026-03-28)
  - Dine-In: Type Selection → Table Selection (from master grid) → Guest Count → Order Created
  - Takeaway/Delivery: Type Selection → Mandatory Name + Mobile → Order Created
  - Backend validation enforced for both flows
- [x] **KOT/Bill Cancellation Engine** (COMPLETED 2026-03-28)
  - Order cancel: mandatory reason from master dropdown + audit trail
  - Bill void: mandatory reason from master dropdown + audit trail (Admin only)
  - KOT cancel: mandatory reason + audit trail
  - All actions logged to `billing_audit_trail` collection

## Key API Endpoints
- `/api/billing-config/tables/list|save|delete|update-status` — Table CRUD
- `/api/billing-config/cancel-reasons/list|save|delete` — Cancel Reasons CRUD
- `/api/billing-config/categories/list|save|delete` — Menu Categories CRUD
- `/api/billing/order/create` — Now validates table+guest for Dine-In, name+phone for Takeaway
- `/api/billing/order/cancel` — Now requires reason_id, logs to audit trail
- `/api/billing/bill/void` — Now requires reason_id, logs to audit trail
- `/api/billing/kot/cancel` — New, requires reason_id, logs to audit trail
- `/api/franchises/by-center/{code}` — Franchise lookup for connectivity indicator

## Test Credentials
- Super Admin: Center PB-MGT, Mobile 9741399190, OTP 123456

## Prioritized Backlog

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
