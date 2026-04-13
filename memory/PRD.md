# Purnabramha IntraPB — Product Requirements Document

## Problem Statement
Internal management system for "Purnabramha," a restaurant franchise. Core philosophy: **MASTER-DATA-FIRST, ROLE-BASED, NO-HARDCODING**.

## Core Modules
1. Authentication (OTP-based)
2. Employee Management (CRUD, KYC/Documents)
3. Attendance Module
4. POS Billing
5. Sales & Expenses
6. Center Accounts (Financial summary, Commission, PIB with Operational Sustainability)
7. MIS Dashboard
8. Franchise Management
9. Document Management
10. Franchise Owner Dashboard
11. Payslip Generation (Location-aware)
12. Franchise Exit & Closure
13. Food Safety Compliance Module (8 templates)

## What's Been Implemented (Latest first)

### [2026-04-13] PIB Operational Sustainability Update (Complete)
- **New Section: Operational Sustainability Check**: Operational Balance = Sales - Expenses - Commissions - GST
- **New Section: Working Capital Status**: Healthy vs Protection Mode with 50% threshold
- **Updated Revenue Share Logic**: Normal Mode (WC >= 50%): MG vs Revenue Share → pay higher. Protection Mode (WC < 50%): MG blocked, revenue share on operational balance only, remaining to WC recovery
- **Updated PIB PDF**: Now has 9 sections (Sales, Expenses, Commissions, Financial Summary, Operational Sustainability, WC Status, Revenue Share, Payout Determination, Tax Rules)
- **Frontend**: New cards in MG & Payout tab showing Operational Sustainability Check, WC Status with green/red badges, transparency message
- Files: `/app/backend/routes/center_accounts.py`, `/app/frontend/src/pages/CenterAccounts.jsx`

### [2026-04-12] Food Safety Compliance Module (Complete)
- 8 template types, Template Master CRUD, record workflow, dashboard, PDF/Excel reports
- Files: `/app/backend/routes/food_safety.py`, `/app/frontend/src/pages/FoodSafety.jsx`

### [2026-04-11] Employee KYC & Document Management (Complete)
- Aadhaar, PAN, TFN, Blood Group, Passport, Visa fields + document uploads + photo
- Payslip integration (Australian: TFN+Photo, Indian: Aadhaar+PAN+Photo)

### Earlier
- Location-Aware Payslip Generation, Monthly Payroll PDF Fix, Payroll Template Update, Org Cost Breakdown, all base modules

## Pending / Backlog
- (P1) WhatsApp/Email notification hooks
- (P1) Code freeze preparation audit
- (P2) Image Upload for Recipes
- (P2) Franchise Deal Simulator
- (P2) 7-year retention deletion prompt
- (P2) Menu card PDF generation per center
- (P2) PDF generation refactoring
