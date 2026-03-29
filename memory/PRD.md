# Purnabramha IntraPB — Product Requirements Document

## Problem Statement
Internal management system for "Purnabramha," a restaurant franchise. Core philosophy: **MASTER-DATA-FIRST, ROLE-BASED, NO-HARDCODING**.

## User Personas
- **Super Admin**: Full system access, manages all centers
- **Center Manager**: Day-to-day operations at a specific center
- **Accountant**: Financial reporting, commission tracking, MIS

## Core Modules

### 1. Authentication (OTP-based)
- Center selection → Mobile → OTP flow
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
- **Commission Upload (NEW - Excel-driven)**:
  - Upload monthly Excel reports (Zomato, Swiggy, DoorDash, PhonePe, Cards)
  - Auto-parse gross amount, commission, GST on commission, TDS, net payout
  - Stored in `monthly_commissions` collection
  - Replaces old formula-based commission calculation

### 7. MIS Dashboard
- Profit = Total Sales - Total Expenses - GST (actual) - Commissions (uploaded)
- Per-center breakdown with date range filtering

### 8. Franchise Management
- Franchise profiles with document management (Object Storage)
- Document categories: Agreement, License, ID Proof, etc.

### 9. Document Management
- Integrated inside Franchise Details view
- Uses Emergent Object Storage

## Technical Architecture
- **Frontend**: React + Shadcn UI
- **Backend**: FastAPI + Motor (async MongoDB)
- **Database**: MongoDB
- **Storage**: Emergent Object Storage for documents
- **Excel Parsing**: pandas + openpyxl

## Key DB Collections
- `centers`, `employees`, `attendance`, `daily_sales`, `expenses`
- `monthly_commissions` — Single source of truth for commission data
- `documents`, `document_categories` — File/doc management
- `franchises`, `franchise_linkages` — Franchise profiles

## Profit Calculation Rule
`Profit = Total Sales - Total Expenses - GST (from actual gst_amount) - Commissions (from uploaded Excel)`

## What's Been Implemented

### Completed (as of March 29, 2026)
- Auth system with OTP login
- Employee CRUD with transfers
- Attendance module with transfer handling
- POS Billing system (100% E2E tested)
- Sales & Expenses module
- Center Accounts with financial summary
- **Commission Upload (Excel-driven)** — Parses Zomato, Swiggy, DoorDash, PhonePe, Cards
- MIS Dashboard with correct profit formula
- Franchise Management with Document Management
- Document Management via Object Storage

### Pending / Backlog
- (P1) WhatsApp/Email notification hooks
- (P2) Image Upload for Recipes
- (P2) Franchise Deal Simulator
- (P2) 7-year retention deletion prompt for attachments
- (P2) Menu card PDF generation per center
