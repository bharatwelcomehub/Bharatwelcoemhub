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

### [2026-04-02] Revenue/Profit Share Financial Breakdown + GST Changes
- Added India-specific step-by-step calculation breakdown on Revenue/Profit Share tab:
  Total Sales → Less 5% GST → Less Commissions → = Net Revenue
- 18% GST (CGST 9% + SGST 9%) on Revenue Share shown as informational display (not added to total)
- Removed GST component from Purnabramha's 85% share total for India (Total Payable = Base Amount)
- For outside India (Australia): 10% GST still applied to Profit Share as before
- Backend: `center_accounts.py` — India always calculates GST for display but `total_with_gst = base_amount`
- Frontend: `CenterAccounts.jsx` — India breakdown section, Purnabramha card shows GST as info note

### [2026-04-01] User Manual
- Created full standalone HTML User Manual at `/app/frontend/public/user-manual.html`

### [2026-04-01] PIB Report GST Display
- PIB Financial Summary PDF updated to explicitly deduct and show 5% GST on sales

### [2026-04-01] Exit Agreement Signature Migration
- Backend migration endpoint: `POST /api/franchise-exit/migrate-all-signatures`
- Single exit migration: `POST /api/franchise-exit/migrate-signatures/{exit_id}`
- Directors auto-pull: `GET /api/franchise-exit/franchise-directors/{code}`
- Converts old `signatures.franchisor` to `franchisor_signatories[]`
- Populates `exit_manager` from `initiated_by_user`
- Auto-populates `franchisee_directors` from Franchise Management directors list

### [2026-04-01] Exit Agreement Signature Logic Overhaul
- Franchisor Signatories: Select Sandeep Gadhwal and/or Jayanti Kathale
- Exit Manager: New signature block from exit process
- Franchisee Directors: Auto-populated from Franchise Management

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

## Refactoring Needed
- PDF Generation logic in `center_accounts.py` should be moved to a dedicated generator utility
