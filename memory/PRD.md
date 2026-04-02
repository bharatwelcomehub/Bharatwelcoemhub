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

### [2026-04-02] Role-Based User Manuals + Download Page
- Created 4 standalone HTML manuals, each with unique color theme:
  - `manual-super-admin.html` (Maroon) — 18 sections covering all modules
  - `manual-center-manager.html` (Green) — 8 sections: attendance, sales, expenses, HR
  - `manual-accountant.html` (Orange) — 10 sections: accounts, revenue share, MIS, loans
  - `manual-franchise-owner.html` (Purple) — 8 sections: dashboard, revenue breakdown, documents
- Added User Manuals page (`/user-manuals`) with View/Download buttons per role
- Added sidebar link under Management > User Manuals
- Files: `/app/frontend/public/manual-*.html`, `/app/frontend/src/pages/UserManuals.jsx`

### [2026-04-02] Expense Category/Mode Dropdown Fix
- Fixed: saved custom expense_type/payment_mode values not showing in dropdowns
- Root cause: Custom values not in master list caused empty Select
- Fix: `allExpenseTypes` / `allPaymentModes` via useMemo merge in ExpenseEntry.jsx

### [2026-04-02] Revenue/Profit Share Financial Breakdown + GST Changes
- India step-by-step calculation: Total Sales → Less 5% GST → Less Commissions → = Net Revenue
- 18% GST on Revenue Share shown as info note (not added to Purnabramha's 85% total)
- For Australia: 10% GST still applied to Profit Share
- Backend: `center_accounts.py`, Frontend: `CenterAccounts.jsx`

### [2026-04-01] User Manual, PIB GST, Exit Signatures, MG Payout, Payslips, Bug Fixes
- Full standalone HTML User Manual, PIB 5% GST display, Exit Agreement signatures
- MG Payout month range + Export, Edit/Delete payments, Payslip generation
- Commission display fix, ZIP download fix, Franchise list fix

### Earlier
- Commission parsers, Dual-file upload, 4-Card UI, RBAC, all base modules

## Pending / Backlog
- (P1) WhatsApp/Email notification hooks
- (P2) Image Upload for Recipes
- (P2) Franchise Deal Simulator
- (P2) 7-year retention deletion prompt
- (P2) Menu card PDF generation per center
- Code freeze preparation audit

## Refactoring Needed
- PDF Generation logic in `center_accounts.py` → dedicated generator utility
