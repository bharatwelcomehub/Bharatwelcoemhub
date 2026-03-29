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

## Completed Features
- [x] 16 Master Data Tables + Permission Engine + Franchise Owner Dashboard
- [x] MIS Dashboard (center-wise, WC, XLSX/PDF Export, **Commissions in Profit**)
- [x] Expense Entry Grid (wider amount fields, batch add)
- [x] Attendance/Payroll for transfers, PDF exports
- [x] POS/Billing (touchscreen UI, 17+ routes, dual-view Table/Order)
- [x] Billing Configuration (Tables, Cancel Reasons, Categories CRUD)
- [x] KOT/Bill Cancellation Engine (master reasons, audit trail)
- [x] MASTER-DATA-FIRST Architecture Fix
- [x] Attendance Transfer Bug Fix
- [x] Commission Tracking Module (Platform/Payment/GST, Dashboard + Config, MIS integration)
- [x] **Document Management Module** — with Object Storage, Approval Workflow, Expiry Tracking
- [x] **Franchise Detail Document Integration** — Documents section embedded in Franchise Management detail view, uses new Document Management system with DB-driven categories (Franchise Agreement, License, Compliance, Financial, Legal, Exit, Offer Letter, ID Proof, Police Verification)

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

## Project Health
- Broken: None
- Mocked: WhatsApp Integration
- Tested: All features tested (iterations 37-39)
