# Purnabramha IntraPB Portal — Product Requirements Document

## Original Problem Statement
Internal management system for "Purnabramha," a restaurant franchise. Core philosophy: MASTER-DATA-FIRST, ROLE-BASED, NO-HARDCODING.

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS
- Backend: FastAPI + Python
- Database: MongoDB
- Libraries: xlsx, ReportLab, emergentintegrations (Object Storage)

## Completed Features
- [x] 16 Master Data Tables + Permission Engine + Franchise Owner Dashboard
- [x] MIS Dashboard (center-wise, WC, XLSX/PDF, **Commissions in Profit**)
- [x] Expense Entry Grid, Attendance/Payroll, POS/Billing (dual-view Table/Order)
- [x] Billing Configuration, KOT/Bill Cancellation Engine
- [x] MASTER-DATA-FIRST Architecture, Attendance Transfer Bug Fix
- [x] Commission Tracking Module — **reads from daily_sales** (same source as Sales Dashboard)
  - Platform commissions from swiggy/zomato fields (25%/22% default)
  - Payment mode commissions from card_idfc/bharat_pay fields (Card 2% default)
  - GST on commissions (18% default)
  - Monthly + Date Range mode, center-wise dashboard
  - MIS integration: Profit = Sales - Expenses - GST - Commissions
- [x] Document Management Module — Object Storage, Approval Workflow, Expiry Tracking
- [x] Franchise Detail Document Integration

## Test Credentials
- Super Admin: Center PB-MGT, Mobile 9741399190, OTP 123456

## Prioritized Backlog
### P1 — WhatsApp/Email notification hooks
### P2 — Image Upload for Recipes, Franchise Deal Simulator, 7-year retention, Menu PDF

## Key Data: daily_sales schema
Each record = one day, one center:
- total_sale, total_cash_sale, total_online_sale
- swiggy, zomato (platform amounts)
- card_idfc, bharat_pay, online_other (payment mode amounts)
- num_guests, num_bills, gst
