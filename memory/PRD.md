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

### [2026-04-16] Salary ALL CENTERS Bug Fix + Clear Button (Complete)
- Fixed: ALL CENTERS salary preview was double-counting transferred employees (129 vs correct 125)
- Root cause: Frontend looped through centers individually, causing duplicates. Now uses single backend call with deduplication
- Added: Clear/unselect button (×) next to center dropdown
- Backend: `/salary_preview` now accepts `targetCenter: "ALL"` and fetches all employees once with name deduplication

### [2026-04-16] Food Safety Tablet-First UI Redesign (Complete)
- Rewrote FoodSafety.jsx to tablet-optimized card-based layout
- Dashboard: 2-column grid with color-coded cards, unique icons per template type
- Record Entry: Card-based vertical layout instead of horizontal-scrolling table
- All inputs h-14 (56px), all text text-lg (18px) for kitchen readability
- Tested: 20/20 backend + 20/20 frontend (iteration_67)

### Earlier completed work
- [2026-04-13] Daily Sales Text Generator, Social Media Planner, Bill Download (iteration_66)
- [2026-04-13] PIB Operational Sustainability Update
- [2026-04-12] Food Safety Compliance Module
- [2026-04-11] Employee KYC & Document Management
- Location-Aware Payslips, Payroll, all base modules

## Pending / Backlog
- (P0) Center-Specific Attendance Unlock (user requested, analysis started)
- (P1) WhatsApp/Email notification hooks
- (P1) Code freeze preparation audit
- (P2) Image Upload for Recipes
- (P2) Franchise Deal Simulator
- (P2) 7-year retention deletion prompt
- (P2) Menu card PDF per center
- (P2) PDF generation refactoring
