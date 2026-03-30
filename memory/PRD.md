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
- Center selection -> Mobile -> OTP flow
- Role-based access (super_admin, center, hr, accounts, franchise)

### 2. Employee Management
- CRUD, transfers between centers
- Historical attendance preserved for transferred employees

### 3. Attendance Module
- Monthly grid with IN/OFF/HALF/ABSENT status
- Handles transferred-out employees gracefully

### 4. POS Billing
- Multi-item billing with tax calculation
- Payment mode tracking (Cash, Card, UPI, Swiggy, Zomato)

### 5. Sales & Expenses
- Daily sales entry with GST and payment mode breakdown
- Monthly expense tracking

### 6. Center Accounts
- Financial summary: Sales, Expenses, Commissions, Profit Share
- **Commission Upload (Excel-driven)**:
  - Upload monthly Excel reports (Zomato, Swiggy, DoorDash, PhonePe, Cards)
  - Auto-parse gross amount, commission, GST on commission, TDS, net payout
  - Dual-file upload for Cards (EDC + Bank Statement) and PhonePe (EDC + Bank Statement)
  - Stored in `monthly_commissions` collection

### 7. MIS Dashboard
- Profit = Total Sales - Total Expenses - GST (actual) - Commissions (uploaded)
- Per-center breakdown with date range filtering

### 8. Franchise Management
- Franchise profiles with document management
- Document categories: Agreement, License, Compliance, Financial, Legal, Exit, etc.

### 9. Document Management
- Centralized system using Emergent Object Storage
- Approval workflow (pending/approved/rejected)
- Center and franchise-level filtering

### 10. Franchise Owner Dashboard
- View-only dashboard for franchise owners
- Tabs: Sales Overview, Expense Breakdown, Franchise Info, Documents
- RBAC: No center dropdown, auto-resolved center from DB mapping

### 11. Payslip Generation
- Sorted employee dropdown from Employee Master DB for selected center
- Signatory selection: Sandeep Gadhwal or Jayanti Kathale (with Seal)
- PDF with Logo (pb_logo.png) at top
- PDF with selected signature image at bottom
- Bulk and single employee modes
- PDF and DOCX format support

## Technical Architecture
- **Frontend**: React + Shadcn UI
- **Backend**: FastAPI + Motor (async MongoDB)
- **Database**: MongoDB
- **Storage**: Emergent Object Storage for documents
- **Excel Parsing**: pandas + openpyxl
- **PDF Generation**: ReportLab

## What's Been Implemented

### Completed
- Auth system with OTP login
- Employee CRUD with transfers
- Attendance module with transfer handling
- POS Billing system (100% E2E tested)
- Sales & Expenses module
- Center Accounts with financial summary
- Commission Upload (Excel-driven) — Parses Zomato, Swiggy, DoorDash, PhonePe, Cards
- Dual-file upload for Cards (EDC + Bank Statement) for MDR calculation
- Dual-file upload for PhonePe (EDC + Bank Statement) for Sundry Debtors
- 4-Card Commission UI (Gross -> GST/Tax -> Other Deductions -> Net Payout)
- MIS Dashboard with correct profit formula
- Franchise Management with Document Management
- Document Management via Object Storage
- Franchise Owner Dashboard with RBAC (auto-resolved center, no dropdown)
- PIB, GST, and Commission PDF generation
- **[2026-03-30] Payslip Generation with Logo, Signatory Selection, Sorted Employee Dropdown**
  - `POST /api/payslip_employees` — Returns sorted employee list for a center
  - Signatory dropdown (Sandeep Gadhwal / Jayanti Kathale with Seal)
  - PDF embeds `pb_logo.png` at top and selected signature at bottom
  - Employee dropdown replaces free-text input for single employee mode
  - 100% test pass rate (11/11 backend, all frontend verified)

### Pending / Backlog
- (P1) WhatsApp/Email notification hooks
- (P2) Image Upload for Recipes
- (P2) Franchise Deal Simulator
- (P2) 7-year retention deletion prompt for attachments
- (P2) Menu card PDF generation per center
