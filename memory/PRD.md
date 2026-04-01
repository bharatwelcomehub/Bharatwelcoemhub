# Purnabramha IntraPB — Product Requirements Document

## Problem Statement
Internal management system for "Purnabramha," a restaurant franchise. Core philosophy: **MASTER-DATA-FIRST, ROLE-BASED, NO-HARDCODING**.

## User Personas
- **Super Admin**: Full system access, manages all centers
- **Center Manager**: Day-to-day operations at a specific center
- **Accountant**: Financial reporting, commission tracking, MIS
- **Franchise Owner**: View-only dashboard with sales, expenses, franchise info, documents

## Core Modules
1. Authentication (OTP-based)
2. Employee Management (CRUD, transfers)
3. Attendance Module (monthly grid)
4. POS Billing
5. Sales & Expenses
6. Center Accounts (Financial summary, Commission Upload, MG Payout)
7. MIS Dashboard
8. Franchise Management (with Directors list)
9. Document Management (Emergent Object Storage)
10. Franchise Owner Dashboard (RBAC)
11. Payslip Generation (Logo, Signature selection, Employee dropdown)
12. Franchise Exit & Closure Module

## What's Been Implemented (Latest first)

### [2026-04-01] Exit Agreement Signature Migration
- Backend migration endpoint: `POST /api/franchise-exit/migrate-all-signatures` — updates ALL existing exits
- Single exit migration: `POST /api/franchise-exit/migrate-signatures/{exit_id}`
- Directors auto-pull: `GET /api/franchise-exit/franchise-directors/{code}`
- Converts old `signatures.franchisor` → `franchisor_signatories[]`
- Populates `exit_manager` from `initiated_by_user`
- Auto-populates `franchisee_directors` from Franchise Management directors list
- Frontend: "Refresh from Master Data" and "Update All Exits" buttons

### [2026-04-01] Exit Agreement Signature Logic Overhaul
- Franchisor Signatories: Select Sandeep Gadhwal and/or Jayanti Kathale
- Exit Manager: New signature block from exit process
- Franchisee Directors: Auto-populated from Franchise Management
- Backward compatible with old format

### [2026-03-30] MG Payout Month Range + Export
- FROM/TO month range picker, Excel + PDF export
- `POST /api/center-accounts/export-mg-payout`

### [2026-03-30] Edit & Delete Payments, Payslip Generation, Bug Fixes
- Payment edit/delete on Payout Summary
- Payslip with Logo, Signatory selection, Employee dropdown
- Franchise List route decorator fix, Master Data sync fix

### Earlier
- Commission parsers (all platforms), Dual-file upload, 4-Card UI
- Franchise Owner Dashboard RBAC, PIB/GST/Commission PDFs
- All base modules

## Pending / Backlog
- (P1) WhatsApp/Email notification hooks
- (P2) Image Upload for Recipes
- (P2) Franchise Deal Simulator
- (P2) 7-year retention deletion prompt
- (P2) Menu card PDF generation per center
- Code freeze preparation audit
