# Purnabramha IntraPB — Product Requirements Document

## Problem Statement
Internal management system for "Purnabramha," a restaurant franchise. Core philosophy: **MASTER-DATA-FIRST, ROLE-BASED, NO-HARDCODING**.

## User Personas
- **Super Admin**: Full system access, manages all centers
- **Center Manager**: Day-to-day operations at a specific center
- **Accountant**: Financial reporting, commission tracking, MIS
- **Franchise Owner**: View-only dashboard with sales, expenses, franchise info, documents

## Core Modules

### 1. Authentication (OTP-based)
### 2. Employee Management (CRUD, transfers)
### 3. Attendance Module (monthly grid)
### 4. POS Billing
### 5. Sales & Expenses
### 6. Center Accounts (Financial summary, Commission Upload, MG Payout)
### 7. MIS Dashboard
### 8. Franchise Management (with Directors list)
### 9. Document Management (Emergent Object Storage)
### 10. Franchise Owner Dashboard (RBAC)
### 11. Payslip Generation (Logo, Signature selection, Employee dropdown)
### 12. Franchise Exit & Closure Module

## What's Been Implemented

### Completed (Latest first)
- **[2026-04-01] Exit Agreement Signature Logic Overhaul**
  - Franchisor Signatories: Select Sandeep Gadhwal and/or Jayanti Kathale (one or both)
  - Exit Manager: New signature block pulled from exit process (name, role, date)
  - Franchisee Directors: Auto-populated from Franchise Management directors list
  - New endpoint: `GET /api/franchise-exit/franchise-directors/{code}`
  - Updated `POST /api/franchise-exit/sign/{exit_id}` with signer_type: franchisor_signatories, exit_manager, franchisee_directors
  - Backward compatible with old franchisor/franchisee single-sign format

- **[2026-03-30] MG Payout Month Range + Export**
  - FROM/TO month range picker (defaults from revenue start date to current month)
  - Excel export (.xlsx) with header info + month-wise table
  - PDF export with Purnabramha logo, summary cards, color-coded table
  - `POST /api/center-accounts/export-mg-payout`

- **[2026-03-30] Edit & Delete Payments on Payout Summary**
  - `POST /api/center-accounts/update-payment` and `delete-payment`
  - Payment History shown in dialog with Edit/Delete buttons

- **[2026-03-30] Payslip Generation with Logo, Signatory, Employee Dropdown**
- **[2026-03-30] Franchise List fix (missing route decorator)**
- **[2026-03-30] Master Data Franchise Sync fix (field mapping)**
- Commission parsers (Swiggy/Zomato/DoorDash/Cards/PhonePe)
- Dual-file upload (EDC + Bank Statement) for Cards & PhonePe
- 4-Card Commission UI (Gross -> GST/Tax -> Other Deductions -> Net Payout)
- Franchise Owner Dashboard RBAC
- PIB, GST, Commission PDF generation
- All base modules (Auth, Employees, Attendance, POS, Sales, Expenses, MIS)

### Pending / Backlog
- (P1) WhatsApp/Email notification hooks
- (P2) Image Upload for Recipes
- (P2) Franchise Deal Simulator
- (P2) 7-year retention deletion prompt for attachments
- (P2) Menu card PDF generation per center
- Code freeze preparation audit (hardcoded values, master data connections)
