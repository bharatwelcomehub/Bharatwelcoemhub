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
- Documents uploaded for a center auto-appear in linked franchise details
- Franchise Owner Dashboard shows documents (view + download only, no upload)

### 10. Franchise Owner Dashboard
- View-only dashboard for franchise owners
- Tabs: Sales Overview, Expense Breakdown, Franchise Info, **Documents**
- Documents tab: Read-only view with download capability

## Technical Architecture
- **Frontend**: React + Shadcn UI
- **Backend**: FastAPI + Motor (async MongoDB)
- **Database**: MongoDB
- **Storage**: Emergent Object Storage for documents
- **Excel Parsing**: pandas + openpyxl

## Profit Calculation Rule
`Profit = Total Sales - Total Expenses - GST (from actual gst_amount) - Commissions (from uploaded Excel)`

## What's Been Implemented (as of March 29, 2026)

### Completed
- Auth system with OTP login
- Employee CRUD with transfers
- Attendance module with transfer handling
- POS Billing system (100% E2E tested)
- Sales & Expenses module
- Center Accounts with financial summary
- Commission Upload (Excel-driven) — Parses Zomato, Swiggy, DoorDash, PhonePe, Cards
- MIS Dashboard with correct profit formula
- Franchise Management with Document Management
- Document Management via Object Storage (unified - center-linked docs show in franchise details)
- Franchise Owner Dashboard with Documents tab (view + download only)
- Master data re-seeded (centers, managers, expenses, expense_heads, doc categories)
- **[2026-03-29] Fixed $0 KPI bug**: Frontend now reads `overview.summary.*` instead of `overview.*`
- **[2026-03-29] Fixed expense data mapping**: Pie chart uses `amount` key (was incorrectly using `total`)
- **[2026-03-29] RBAC: Franchise Exit filtering**: Franchise owners only see their own exit entries
- **[2026-03-29] RBAC: Center dropdown hidden for franchise owners** on Owner Dashboard
- **[2026-03-29] Franchise owners can access Exit & Closure** (view-only, no initiate/edit)

### Pending / Backlog
- (P1) WhatsApp/Email notification hooks
- (P2) Image Upload for Recipes
- (P2) Franchise Deal Simulator
- (P2) 7-year retention deletion prompt for attachments
- (P2) Menu card PDF generation per center
