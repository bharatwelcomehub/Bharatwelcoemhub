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
13. Food Safety Compliance Module (8 templates) — Tablet-first UI redesign complete
14. Daily Sales Text Generator (WhatsApp-style summary)
15. Social Media Planning & Content Tracker
16. Bill Download Access (ZIP support for franchise owners)

## What's Been Implemented (Latest)

### [2026-04-16] International Attendance Calendar Week Logic (Complete)
- Replaced month-based week logic (Week 1=days 1-6, etc.) with TRUE calendar weeks
- Week 1: Jan 1 to first Sunday. Week 2+: Monday to Sunday (continues all year)
- Weeks span across month boundaries (e.g., Week 14: Mar 30 - Apr 5)
- New `/weeks-for-month` API returns which calendar weeks overlap with a month
- Frontend: Week selector shows "Wk 14: Mar 30 - Apr 5", column headers show date + day
- Month filter only controls which weeks are shown, doesn't break week structure
- Backend: Updated save, week-data, monthly-report, payroll-report endpoints

### [2026-04-16] Salary Bug Fixes (Complete)
- Leave (L) weight: 1 → 0 (unpaid)
- Transfer salary: per-center view now only counts attendance AT that center
- Transferred-out employees added back to source center's salary
- ALL CENTERS: single backend call with deduplication

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
