# Purnabramha IntraPB Portal — Product Requirements Document

## Original Problem Statement
Internal management system for "Purnabramha," a restaurant franchise. Manages attendance, payroll, sales/expenses, HR letters, transfers, MIS dashboards, POS/billing, and franchise operations across India + Australia centers.

## CORE ARCHITECTURE: MASTER-DATA-FIRST, ROLE-BASED, NO-HARDCODING
- ALL dropdowns, filters, and lists pulled from MongoDB master collections
- Center->Franchise mapping via `centers.franchise_code` field (set by Center Accounts "Link Franchise")
- RBAC via Permission Engine (Super Admin, Admin, Center Manager, Franchise Owner)
- No hardcoded center codes, franchise names, or static lists in any module
- Public GET `/api/masters/{type}` endpoint for all dropdown data

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS
- Backend: FastAPI + Python
- Database: MongoDB
- Libraries: xlsx (Excel), ReportLab (PDF)

## Master Collections (Single Source of Truth)
- `centers`: {code, name, franchise_code, is_india_center, active, country}
- `franchises`: {franchise_code, franchise_name, working_capital, primary_contact_name, status}
- `master_payment_modes`: {name, is_active} — CASH, UPI, CARD, BANK TRANSFER, etc.
- `master_order_types`: {name, is_active} — DINE-IN, TAKEAWAY, DELIVERY, CATERING
- `master_discount_types`: {name, is_active} — NO DISCOUNT, COMPLIMENTARY, STAFF DISCOUNT, etc.
- `master_menu_categories`: {category_id, name, display_order, is_active}
- `billing_tables`: {table_id, table_no, center, capacity, floor, section, status}
- `billing_cancel_reasons`: {reason_id, reason, type (order/bill/kot), is_active}
- `billing_audit_trail`: {action, order_id/bill_no, center, reason, cancelled_by, role, timestamp}
- `expense_heads`: {name, description, is_active}
- `permissions`: {role_key, permissions_list}
- `transfer_requests`: {employee_name, from_center, to_center, transfer_type, start_date, end_date, status}

## Completed Features
- [x] 16 Master Data Tables + Permission Engine + Franchise Owner Dashboard
- [x] MIS Dashboard (center-wise, WC from franchise mapping, XLSX/PDF Export)
- [x] Expense Entry Grid (wider amount fields, batch add)
- [x] Attendance/Payroll for transfers, PDF exports
- [x] POS/Billing (touchscreen UI, 17+ routes)
- [x] Billing Configuration (Tables, Cancel Reasons, Categories CRUD)
- [x] POS Workflow (Table Selection -> Guest Count -> Order for Dine-In; Name+Phone for Takeaway/Delivery)
- [x] KOT/Bill Cancellation Engine (master reasons, audit trail)
- [x] Franchise Connectivity Indicator (connected=green, unmapped=amber)
- [x] **MASTER-DATA-FIRST Architecture Fix** (COMPLETED 2026-03-28)
- [x] **POS UI Redesign** — Dual-view: Table View landing (table grid, status colors, Delivery/Pickup buttons) + Order View (menu + cart) (COMPLETED 2026-03-28)
- [x] **Attendance Transfer Bug Fix** — Permanently transferred-out employees now appear in source center's attendance grid with TRANSFERRED_OUT tag, preserving pre-transfer attendance data (COMPLETED 2026-03-28)

## Test Credentials
- Super Admin: Center PB-MGT, Mobile 9741399190, OTP 123456

## Prioritized Backlog

### P1 — High
- Franchise document management & Approval hierarchy
- Commission tracking module (needed to re-enable Profit metrics)
- WhatsApp/Email notification hooks

### P2 — Medium/Future
- Image Upload for Recipes
- Franchise Deal Simulator
- 7-year retention deletion prompt
- Menu card PDF generation per center

## Project Health
- Broken: None
- Mocked: WhatsApp Integration
- Hidden: Net Profit metrics (until commission module is built)
