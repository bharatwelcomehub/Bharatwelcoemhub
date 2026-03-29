# Purnabramha IntraPB Portal — Product Requirements Document

## Original Problem Statement
Internal management system for "Purnabramha," a restaurant franchise. Manages attendance, payroll, sales/expenses, HR letters, transfers, MIS dashboards, POS/billing, commissions, document management, and franchise operations across India + Australia centers.

## CORE ARCHITECTURE: MASTER-DATA-FIRST, ROLE-BASED, NO-HARDCODING
- ALL dropdowns, filters, and lists pulled from MongoDB master collections
- Center->Franchise mapping via `centers.franchise_code` field
- RBAC via Permission Engine (Super Admin, Admin, Center Manager, Franchise Owner)
- No hardcoded center codes, franchise names, or static lists
- Public GET `/api/masters/{type}` endpoint for all dropdown data

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS
- Backend: FastAPI + Python
- Database: MongoDB
- Libraries: xlsx (Excel), ReportLab (PDF), emergentintegrations (Object Storage)

## Master Collections (Single Source of Truth)
- `centers`: {code, name, franchise_code, is_india_center, active, country}
- `franchises`: {franchise_code, franchise_name, working_capital, primary_contact_name, status}
- `master_payment_modes`, `master_order_types`, `master_discount_types`, `master_menu_categories`
- `billing_tables`, `billing_cancel_reasons`, `billing_audit_trail`
- `expense_heads`, `permissions`, `transfer_requests`
- `commission_config`: {center, platforms[{platform, commission_pct, gst_on_commission_pct}], payment_modes[{payment_mode, commission_pct}]}
- `document_categories`: {category_id, name, level (franchise/employee), requires_expiry}
- `documents`: {document_id, center, category_id, level, storage_path, status (pending/approved/rejected), expiry_date, uploaded_by, approved_by}

## Completed Features
- [x] 16 Master Data Tables + Permission Engine + Franchise Owner Dashboard
- [x] MIS Dashboard (center-wise, WC from franchise mapping, XLSX/PDF Export)
- [x] Expense Entry Grid (wider amount fields, batch add)
- [x] Attendance/Payroll for transfers, PDF exports
- [x] POS/Billing (touchscreen UI, 17+ routes, dual-view Table/Order)
- [x] Billing Configuration (Tables, Cancel Reasons, Categories CRUD)
- [x] POS Workflow (Table Selection -> Guest Count -> Order)
- [x] KOT/Bill Cancellation Engine (master reasons, audit trail)
- [x] MASTER-DATA-FIRST Architecture Fix
- [x] POS UI Redesign — Dual-view Table View + Order View
- [x] Attendance Transfer Bug Fix — Transferred-out employees appear in source center grid
- [x] **Commission Tracking Module** (COMPLETED 2026-03-29)
  - Platform commissions (Swiggy/Zomato/Magicpin/Direct)
  - Payment mode commissions (Card/UPI/Cash/Bank Transfer)
  - GST on commissions
  - Center-wise dashboard + Configuration tab
  - MIS Dashboard integration (Profit = Sales - Expenses - GST - Commissions)
- [x] **Document Management Module** (COMPLETED 2026-03-29)
  - Franchise-level & Employee-level documents
  - Object storage (Emergent) for file upload/download
  - Approval workflow: Center Manager uploads → Admin approves/rejects
  - Expiry tracking with alerts (30/60 day windows)
  - Document categories management
  - Stats dashboard (total, pending, approved, rejected, expiring, expired)

## Test Credentials
- Super Admin: Center PB-MGT, Mobile 9741399190, OTP 123456

## Prioritized Backlog

### P1 — High
- WhatsApp/Email notification hooks

### P2 — Medium/Future
- Image Upload for Recipes
- Franchise Deal Simulator
- 7-year retention deletion prompt
- Menu card PDF generation per center

## Code Architecture
```
/app/backend/routes/
├── commissions.py        # NEW: Commission config, dashboard, MIS integration
├── documents.py          # NEW: Document CRUD, approval, object storage
├── attendance.py         # Updated: Transfer-aware monthly grid
├── attendance_dashboard.py # Updated: Transfer-aware dashboard
├── billing.py
├── billing_config.py
├── masters.py
├── mis_dashboard.py      # Updated: Includes commissions in profit calc
├── transfers.py
├── sales_expenses.py
└── server.py

/app/frontend/src/pages/
├── CommissionTracking.jsx  # NEW: Dashboard + Config tabs
├── DocumentManagement.jsx  # NEW: Documents + Expiry + Categories tabs
├── Dashboard.jsx           # Updated: New sidebar items + routes
├── MISDashboard.jsx        # Updated: Commissions + Net Profit cards
├── AttendanceDashboard.jsx # Updated: Transfer OUT badge
├── POSBilling.jsx
└── ...
```

## Project Health
- Broken: None
- Mocked: WhatsApp Integration
- Tested: All features tested via testing_agent (iterations 37, 38)
