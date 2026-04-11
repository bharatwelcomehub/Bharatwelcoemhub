# Purnabramha IntraPB — Product Requirements Document

## Problem Statement
Internal management system for "Purnabramha," a restaurant franchise. Core philosophy: **MASTER-DATA-FIRST, ROLE-BASED, NO-HARDCODING**.

## User Personas
- **Super Admin**: Full system access, manages all centers
- **Center Manager**: Day-to-day operations at a specific center
- **Accountant**: Financial reporting, commission tracking, MIS
- **Franchise Owner**: View-only dashboard with sales, expenses, franchise info, documents
- **Chef (Perth)**: Fill and submit kitchen food safety records
- **Manager (Perth)**: Review, submit, download, approve food safety records

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
11. Payslip Generation (Logo, Signature, KYC info on payslips)
12. Franchise Exit & Closure Module
13. **Food Safety Compliance Module** (8 templates, CRUD, records, reports)

## What's Been Implemented (Latest first)

### [2026-04-11] Food Safety Compliance Module (Complete)
- **8 Template Types**: Supplier Details, Food Receipt, Cooking & Cooling, Food Temp Record, 2-Hour/4-Hour Rule Log, Cleaning & Sanitising Procedure, Cleaning & Sanitising Record, General Temperature Record
- **Template Master CRUD**: Admin can add/edit/delete/activate template items per center
- **Seed Data**: 107 Purnabramha Perth menu items auto-seeded (thali, bhaji, amti, rice, solkadhi, etc. + suppliers + cleaning procedures)
- **Record Workflow**: Draft → Submitted → Approved → Locked
- **Dashboard**: Status cards per template type, overdue alerts for missing daily records, recent records
- **Reports**: PDF and Excel export with date range filters
- **Role Access**: Admin has full CRUD. Perth/non-Indian center staff can fill and submit records. Indian center users cannot access the module.
- **Sidebar**: "Food Safety" section visible only to Admin and non-Indian center users
- **Tested**: 20/20 backend + all frontend verified (iteration_65)
- Files: `/app/backend/routes/food_safety.py`, `/app/frontend/src/pages/FoodSafety.jsx`
- Collections: `fs_template_items`, `fs_records`

### [2026-04-11] Employee KYC & Document Management + Payslip Integration (Complete)
- New fields: Aadhaar, PAN, TFN, Blood Group, Passport Number, Visa Type
- Document uploads for each (Aadhaar, PAN/TFN, Passport, Visa) via Emergent Object Storage
- Photo upload with preview
- Employee Report PDF export
- Payslip Integration: Australian = TFN + Photo, Indian = Aadhaar + PAN + Photo
- Tested: 12/12 backend + all frontend verified (iteration_64)

### [2026-04-11] Fix Monthly Payroll PDF + Location-Aware Payslip Generation
- Fixed missing PDF sections + employee name/value bugs
- Auto-detect center country for payslip format
- Tested: iterations 62-63

### [2026-04-08] Payroll Calculation Template Update + CSV Export + Org Cost Breakdown
- Super 12%, Medicare threshold fix, CSV export, weekly/monthly cost tables
- Tested: iterations 60-61

### Earlier (see git log for full history)
- Australian Reverse Payroll, Visual PDF Reports, Working Capital, Bank Reconciliation, Revenue Share, all base modules

## Pending / Backlog
- (P1) WhatsApp/Email notification hooks
- (P1) Code freeze preparation audit
- (P2) Image Upload for Recipes
- (P2) Franchise Deal Simulator
- (P2) 7-year retention deletion prompt
- (P2) Menu card PDF generation per center
- (P2) PDF generation refactoring (dedicated utility)

## Refactoring Needed
- PDF Generation logic in routes → dedicated generator utility
