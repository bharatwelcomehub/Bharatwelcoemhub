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
14. **Daily Sales Text Generator** (WhatsApp-style summary)
15. **Social Media Planning & Content Tracker**
16. **Bill Download Access** (ZIP support for franchise owners)

## What's Been Implemented (Latest)

### [2026-04-13] Three New Features (Complete)
1. **Daily Sales Summary Text Generator**
   - Auto-pulls data from daily_sales and expenses collections
   - WhatsApp-ready format with "Jai Hind Namskar" header
   - Editable fields with real-time preview
   - Copy to clipboard, date picker, center selector
   - Role: Manager=own center, Admin=all, Franchise Owner=view+copy
   - Files: `/app/backend/routes/daily_text.py`, `/app/frontend/src/pages/DailyTextGenerator.jsx`

2. **Social Media Planning & Content Tracker**
   - 10 content types, 5 platforms, 5 statuses, 8 campaign categories
   - Admin: full CRUD (create/edit/delete posts with creatives)
   - Franchise Owner: read-only view of their center's content
   - Dashboard widgets (total, posted, planned, ratio, by status/platform)
   - Content List table + Calendar view
   - Files: `/app/backend/routes/social_media.py`, `/app/frontend/src/pages/SocialMediaPlanner.jsx`

3. **Bill Download Access for Franchise Owners**
   - View bills from bills + expenses collections
   - Single download, multi-select download
   - Month ZIP, Custom date-range ZIP, Doc-type ZIP
   - 8 document types (Sales Bill, Expense Bill, Invoice, etc.)
   - Franchise owner: own center only; Admin: all centers
   - Files: `/app/backend/routes/bill_download.py`, `/app/frontend/src/pages/BillDownload.jsx`

- **Tested**: 22/22 backend + all frontend verified (iteration_66)

### [2026-04-13] PIB Operational Sustainability Update (Complete)
### [2026-04-12] Food Safety Compliance Module (Complete)
### [2026-04-11] Employee KYC & Document Management (Complete)
### Earlier: Location-Aware Payslips, Payroll, all base modules

## Pending / Backlog
- (P1) WhatsApp/Email notification hooks
- (P1) Code freeze preparation audit
- (P2) Image Upload for Recipes
- (P2) Franchise Deal Simulator
- (P2) 7-year retention deletion prompt
- (P2) Menu card PDF per center
- (P2) PDF generation refactoring
