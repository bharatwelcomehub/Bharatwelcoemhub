# Purnabramha IntraPB — Product Requirements Document

## Problem Statement
Internal management system for "Purnabramha," a restaurant franchise. Core philosophy: **MASTER-DATA-FIRST, ROLE-BASED, NO-HARDCODING**.

## Core Modules
1. Authentication (OTP-based)
2. Employee Management (CRUD, KYC/Documents)
3. Attendance Module (Dashboard with role-based access)
4. POS Billing
5. Sales & Expenses
6. Center Accounts (Financial summary, Commission, PIB with Operational Sustainability)
7. MIS Dashboard
8. Franchise Management
9. Document Management
10. Franchise Owner Dashboard (with full franchise info)
11. Payslip Generation (Location-aware)
12. Franchise Exit & Closure
13. Food Safety Compliance Module (8 templates, tablet-first UI)
14. Daily Sales Text Generator (WhatsApp-style summary)
15. Social Media Planning & Content Tracker
16. Bill Download Access (ZIP support, expense attachments)

## What's Been Implemented (Latest)

### [2026-04-16] Dashboard & Data Visibility Fixes (Complete)
1. **Attendance Dashboard** — Added role-based access: Center Managers see only their center, Admin/Super Admin see all
2. **Daily Text Generator** — Fixed data reset bug: now pulls actual stored data from daily_sales/expenses with case-insensitive center matching
3. **Bill Download** — Wired expense_attachments collection, normalized POS bills (bill_no→bill_id), auth token for downloads
4. **Owner Dashboard** — Added Center Name, Phone, Legal Entity fields with field fallback chains
5. **Expense Bill Visibility** — Fixed "None" display by reading from expense_attachments collection instead of non-existent expenses.bill_url
- Tested: 16/16 backend + 5/5 frontend (iteration_68)

### [2026-04-16] International Attendance Calendar Weeks (Complete)
### [2026-04-16] Salary Fixes (Leave weight, Transfer calculation) (Complete)
### [2026-04-16] Food Safety Tablet-First UI Redesign (Complete)

### Earlier completed work
- [2026-04-13] Daily Sales Text Generator, Social Media Planner, Bill Download
- [2026-04-13] PIB Operational Sustainability Update
- [2026-04-12] Food Safety Compliance Module
- [2026-04-11] Employee KYC & Document Management

## Pending / Backlog
- (P0) Center-Specific Attendance Unlock
- (P1) WhatsApp/Email notification hooks
- (P1) Code freeze preparation audit
- (P2) Image Upload for Recipes
- (P2) Franchise Deal Simulator
- (P2) 7-year retention deletion prompt
- (P2) Menu card PDF per center
- (P2) PDF generation refactoring
