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
2. Employee Management (CRUD, transfers, KYC/Documents)
3. Attendance Module (monthly grid)
4. POS Billing
5. Sales & Expenses
6. Center Accounts (Financial summary, Commission Upload, MG Payout)
7. MIS Dashboard
8. Franchise Management (with Directors list)
9. Document Management (Emergent Object Storage)
10. Franchise Owner Dashboard (RBAC)
11. Payslip Generation (Logo, Signature selection, Employee dropdown, KYC info on payslips)
12. Franchise Exit & Closure Module

## What's Been Implemented (Latest first)

### [2026-04-11] Employee KYC & Document Management + Payslip Integration (Complete)
- **New Fields**: Aadhaar, PAN, TFN, Blood Group, Passport Number, Visa Type added to Employee form
- **Document Uploads**: Attachment option for each document (Aadhaar, PAN/TFN, Passport, Visa) via Emergent Object Storage
- **Photo Upload**: Passport-size photo upload with preview in the form
- **Employee Report PDF**: Export button generates a PDF directory with all employee details, photos, and blood groups
- **Payslip Integration**: 
  - Australian payslips now show TFN and Employee Photo
  - Indian payslips now show Aadhaar + PAN and Employee Photo
- **Employee List**: Updated table with Photo, Blood Group, and Docs columns
- **Backend Endpoints**: `/api/employee_upload_photo`, `/api/employee_upload_document`, `/api/employee_report`
- **Tested**: 12/12 backend tests + full frontend UI verified (iteration_64)
- Files: `/app/backend/routes/employees.py`, `/app/backend/routes/payroll.py`, `/app/backend/server.py`, `/app/frontend/src/pages/Employees.jsx`

### [2026-04-11] Fix Monthly Payroll PDF — Complete All Sections
- **Bug Fix**: PDF was missing Weekly Organization Cost Breakdown and Per-Person Organization Cost tables
- **Bug Fix**: Employee names showing as "Unknown" and $0 values — fixed by querying correct `db.employees` collection
- **Bug Fix**: Payslip employees endpoint querying wrong collection (`international_employees` → `employees`)
- **Added**: PDF now contains all 4 sections matching the screen: Summary Cards, Employee Payroll Breakdown, Weekly Org Cost, Per-Person Cost
- **Tested**: 10/10 backend + all frontend verified (iteration_63)

### [2026-04-11] Location-Aware Payslip Generation (International Centers)
- **Feature**: Payslip generation is now country-aware. Auto-detects center country from DB.
- **Australia (PB-PERTH)**: Generates WA payroll format PDF with Hourly Rate, Total Hours, Gross Pay, PAYG Tax, Medicare Levy, Super (12%), Net Pay, Employer Cost. Hours fetched from `international_attendance` collection.
- **India**: Continues using existing Indian salary format (Basic, HRA, ESI, Rs currency)
- **Tested**: 10/10 backend + all frontend verified (iteration_62)
- Files: `/app/backend/routes/payroll.py`, `/app/frontend/src/pages/Salary.jsx`

### [2026-04-08] Payroll Calculation Template Update + CSV Export
- **Super Rate**: Updated from 11.5% to 12% (FY 2025-26)
- **Medicare Threshold**: Changed from $26k to $18,200 (tax-free threshold)
- **CSV Export**: Added payroll summary CSV endpoint
- **Tested**: 15/15 backend + all frontend verified (iteration_61)

### [2026-04-08] Weekly/Monthly Organization Payroll Cost Breakdown (P0)
- **Feature**: Added organizational cost visibility
- **Tested**: 12/12 backend + all frontend tests passed (iteration_60)

### Earlier (see CHANGELOG.md for full history)
- Australian Reverse Payroll Calculation
- Visual PDF Reports with KPI Cards
- Working Capital Feature Rewrite
- Bulk Upload + Delete
- Bank Reconciliation
- Revenue/Profit Share Financial Breakdown
- All base modules

## Pending / Backlog
- (P1) WhatsApp/Email notification hooks
- (P1) Code freeze preparation audit
- (P2) Image Upload for Recipes
- (P2) Franchise Deal Simulator
- (P2) 7-year retention deletion prompt
- (P2) Menu card PDF generation per center
- (P2) PDF generation refactoring (center_accounts.py + mis_dashboard.py → dedicated utility)

## Refactoring Needed
- PDF Generation logic in `center_accounts.py` → dedicated generator utility
