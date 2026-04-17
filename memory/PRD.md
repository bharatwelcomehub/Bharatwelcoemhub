# Purnabramha IntraPB — Product Requirements Document

## Problem Statement
Internal management system for "Purnabramha," a restaurant franchise. Core philosophy: **MASTER-DATA-FIRST, ROLE-BASED, NO-HARDCODING**.

## What's Been Implemented (Latest)

### [2026-04-17] Working Capital Logic Overhaul (Complete)
- **Rewrote** `calculate_working_capital_standing()` with proper monthly flow:
  - Step 1: Opening WC (previous month's closing, or Base WC)
  - Step 2: Calculate Operational Balance (Sales - Expenses - Commission - GST)
  - Step 3: Profit restores WC if below Base (doesn't inflate beyond Base)
  - Step 4: Loss deducts from WC
  - Step 5: Revenue Share blocked if WC <= 50% of Base
  - Step 6: Revenue Share resumes ONLY when WC restored to Base level
  - Step 7: Closing WC carries forward
- **Updated WC Table** endpoint with same logic + new columns (WC Used, WC Restored, GST, Revenue Share Status per month)
- **Updated PIB PDF** with new fields: Base WC, Opening WC (Month), WC Used, WC Restored, Current WC, WC%, Revenue Share Status
- **Updated Frontend** Working Capital Status section with 8 data cards including WC Used/Restored, Revenue Share Status, and contextual banners (Protection Mode / Restoring)
- **Result**: WC no longer inflates to crores. PB-DV shows correct ₹9,00,000 base vs old ₹2,05,28,314

### [2026-04-16] Previous session work
- Attendance Dashboard advanced visibility (role-based + advance amounts)
- Dashboard & Data Visibility Fixes (5 issues)
- International Attendance Calendar Weeks
- Salary Fixes (Leave weight, Transfer calculation)
- Food Safety Tablet-First UI Redesign

## Pending / Backlog
- (P0) Center-Specific Attendance Unlock
- (P1) WhatsApp/Email notification hooks
- (P1) Code freeze preparation audit
- (P2) Image Upload for Recipes
- (P2) Franchise Deal Simulator
- (P2) 7-year retention deletion prompt
- (P2) Menu card PDF per center
- (P2) PDF generation refactoring
