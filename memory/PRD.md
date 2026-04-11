# Purnabramha IntraPB — Product Requirements Document

## Problem Statement
Internal management system for "Purnabramha," a restaurant franchise. Core philosophy: **MASTER-DATA-FIRST, ROLE-BASED, NO-HARDCODING**.

## User Personas
- **Super Admin**: Full system access, manages all centers
- **Center Manager**: Day-to-day operations at a specific center
- **Accountant**: Financial reporting, commission tracking, MIS
- **Franchise Owner**: View-only dashboard with sales, expenses, franchise info, documents

## Core Modules
1. Authentication (OTP-based)
2. Employee Management (CRUD, transfers)
3. Attendance Module (monthly grid)
4. POS Billing
5. Sales & Expenses
6. Center Accounts (Financial summary, Commission Upload, MG Payout)
7. MIS Dashboard
8. Franchise Management (with Directors list)
9. Document Management (Emergent Object Storage)
10. Franchise Owner Dashboard (RBAC)
11. Payslip Generation (Logo, Signature selection, Employee dropdown)
12. Franchise Exit & Closure Module

## What's Been Implemented (Latest first)

### [2026-04-05] Working Capital Feature Rewrite (Complete)
- **New P/L Formula**: P/L = Sales - (Expenses + Commission)
- **Core Logic**: Losses deduct from WC. Profits do NOT auto-add to WC.
- **Revenue Share Control**: Stops if WC falls to 50% or below of initial. Resumes when restored above threshold.
- **Manual Top-up**: New `POST /api/center-accounts/wc-topup` endpoint with full audit log (date, amount, reason, user).
- **Simplified UI**: 5 summary cards (Initial WC, Current WC, P/L, Rev Share Status, Last Top-up) + clean month table (Sale, Expenses, Commission, P/L, Opening WC, Top-up, Closing WC, Rev Share) + audit log toggle.
- **Removed**: Old per-row WC edit/override logic. Month-by-month carry-forward. Loan conversion. Progress bars.
- Files: `/app/backend/routes/center_accounts.py`, `/app/frontend/src/pages/CenterAccounts.jsx`

### [2026-04-05] Bulk Upload Parses Expenses + Delete Cleans Both
- **Bulk Import**: Custom format Excel upload now also parses expense sheets (sheets with EXPENCE/EXPENSE header). Extracts DATE, description, AMOUNT, TYPE, PAYMENT MODE. Saved to `expenses` collection with `source=bulk_import:{sheet_name}`.
- **Delete Data**: Now deletes both `daily_sales` AND `expenses` for the center+month range. Response shows both counts.
- Files: `/app/backend/routes/sales_expenses.py`

### [2026-04-04] 11 Changes — Access Control, Charts, Glossy UI, Bug Fixes
- **Bug Fix**: Upload parsing now saves `deposited_in_bank`, `cash_expense`, `due_amount` from Excel bulk import (was missing)
- **Access Control**: Bank Reconciliation → super admin + admin + accounting only. Freeze Control + Upload Settings → super admin only. Expense List (Admin) tab → removed entirely.
- **Grid Visibility**: Super admin can hide/show Grid Update tab per center via "Hide Grid"/"Show Grid" button. Fix All Balances and Delete Data buttons hidden when grid is hidden. Settings stored in `center_settings` collection.
- **Single Day Entry**: Opening Balance, Petty Cash Opening back to auto-calculated (read-only). Cash Expense editable. GST (5%) shown in Closing Summary.
- **Payment Breakdown**: Added % of total sale for each payment method. Added donut chart for online breakdown (Recharts).
- **Overview**: Added glossy summary cards with %, payment split pie chart, expense bar chart.
- **Glossy Styling**: Gradient backgrounds, shadows, hover effects on summary cards across all screens.
- New backend endpoints: `POST /api/sales/settings/get`, `POST /api/sales/settings/update`
- Files: `sales_expenses.py`, `SalesExpenses.jsx`, `SalesDataEntry.jsx`, `index.css`

### [2026-04-04] Sales Grid Columns Match Excel + Delete Data + Editable Balances
- **Grid Columns**: Now match Excel "Sale's Cash Summery" exactly — 22 columns total:
  - Day 1 editable (green): Opening Bal, Petty Cash Opening
  - Editable (blue): Deposited, Cash Rcpt, Total Sale, Card, UPI, Swiggy, Zomato, Doordash, Online, Due, Cash Expense, Guests, Bills
  - Calculated (gray): Online Total, Cash Sale, Closing Bal, To Deposit, Petty Close
- **Delete Data**: New "Delete Data" button + dialog to delete sales records for a month or month range. Backend: `POST /api/sales/daily/delete-range`
- **Single Day Entry**: Opening Balance, Petty Cash Opening, and Cash Expense are all now editable (were read-only)
- Files: `SalesGridEditor.jsx`, `SalesDataEntry.jsx`, `SalesExpenses.jsx`, `sales_expenses.py`

### [2026-04-04] WC Assessment Redesign — Excel-Format Table (P0)
- **Redesign**: Replaced old WC cards/progress bars/financial summary with a clean Excel-like table
- **Columns**: MONTH | SALE | EXPENSES | P/L | WORKING CAPITAL (Opening) | BAL. WC. (Closing) | DIFF.OF WC.
- **Formula**: P/L = Sale - Expenses (simple subtraction, NO GST/Commission deduction — matching user's Excel)
- **WC can go negative** (removed old cap-at-0 + loan conversion logic)
- **Edit Features**: 
  - Edit Initial WC value (button next to header)
  - Edit Opening WC for first month (pencil icon on first row)
  - Overrides stored in `wc_overrides` collection
- **New Endpoints**: `POST /api/center-accounts/wc-table`, `POST /api/center-accounts/wc-override`
- Files: `/app/backend/routes/center_accounts.py`, `/app/frontend/src/pages/CenterAccounts.jsx`

### [2026-04-04] Opening Balance Editable for 1st Day of Month
- **Enhancement**: Added `opening_balance` column to SalesGridEditor, editable ONLY for the 1st row (day 1 of month)
- **Also added**: `deposited_in_bank` and `cash_receipts` columns to the editable grid
- **Purpose**: Users can manually correct the opening balance before running "Fix All Balances"
- File: `/app/frontend/src/components/SalesGridEditor.jsx`

### [2026-04-04] Full Historical Balance Recalculation Fix (P0)
- **Bug Fix**: `/api/sales/daily/recalculate` now recalculates ALL records for a center from first to last day (not just one month)
- **Root Cause**: Single-month recalculation couldn't fix cascading errors from historical data corruption — each month pulled the wrong closing from the prior month
- **Fix**: Endpoint fetches all `daily_sales` records with valid YYYY-MM-DD dates, iterates chronologically, chains `opening_balance = prev_closing_balance`, uses `bulk_write(ReplaceOne)` for batch efficiency
- **Invalid Data Handling**: Records with malformed dates (e.g., "Monday,July" from Excel import) are filtered out via regex
- **Verified**: 0 chain breaks across 364 records for PB-HSR (2025-04-01 to 2026-03-31)
- **Frontend**: Button renamed "Fix All Balances", no longer sends month parameter, shows record count + date range in toast
- Files: `/app/backend/routes/sales_expenses.py`, `/app/frontend/src/pages/SalesExpenses.jsx`

### [2026-04-04] ANZ PDF Parsing Fix — Table-to-Text Fallback
- **Bug Fix**: ANZ Bank PDF (JAN-FEB 2026) was returning 0 transactions
- **Root Cause**: Table extraction found partial headers (date+narration, no debit column), blocking text fallback
- **Fix**: Added fallback in `parse_pdf_bank_statement()` — if table parsing yields 0 transactions, automatically uses text parser
- **Result**: 111 debit transactions parsed correctly, total $33,182.40 matches PDF summary
- File: `/app/backend/routes/bank_reconciliation.py`

### [2026-04-04] Grid Closing Balance Carry-Forward Fix
- **Bug Fix**: First day of month wasn't getting opening balance from previous month's last day closing
- **Root Cause**: Grid chaining only worked within-month; didn't fetch previous month's last closing
- **Fix**: `SalesGridEditor.fetchGridData()` now fetches previous month's last day's closing_balance and uses it as the first row's opening
- File: `/app/frontend/src/components/SalesGridEditor.jsx`

### [2026-04-04] Month-by-Month Working Capital Assessment (SUPERSEDED)
- **REPLACED** by the Excel-format WC table above. Old card-based UI and loan logic removed.
- Old formula used P&L = Sales - Expenses - Commissions - GST (now simplified to P/L = Sale - Expenses)

### [2026-04-04] Opening Balance & Petty Cash Formula Fix
- **Bug Fix**: Opening Balance and Petty Cash Opening were wrong for all centers
- **Root Cause #1**: `update_petty_cash_for_expense()` used wrong formula (`petty_opening - cash_expense` instead of `petty_opening + cash_receipts - cash_expense`), also didn't update `closing_balance`
- **Root Cause #2**: Frontend used stale stored `opening_balance` instead of always using previous day's closing
- **Fixes Applied**:
  1. `update_petty_cash_for_expense()` now uses `calculate_totals()` for consistent recalculation of all derived fields
  2. Frontend `SalesDataEntry.jsx` always uses previous day's closing as today's opening
  3. Frontend `SalesGridEditor.jsx` chains opening balances after loading grid data
  4. New `POST /api/sales/daily/recalculate` endpoint to fix historical data (chains balances for a center+month)
  5. "Fix Balances" button added to Sales Dashboard header
- Files: `/app/backend/routes/sales_expenses.py`, `/app/frontend/src/components/SalesDataEntry.jsx`, `/app/frontend/src/components/SalesGridEditor.jsx`, `/app/frontend/src/pages/SalesExpenses.jsx`

### [2026-04-02] Bank Statement vs Expense Reconciliation Feature
- **Full Feature Implementation**: Upload bank statements (Excel/CSV/PDF), parse debit transactions, match against recorded expenses
- **File Format Support**: 
  - India Excel/CSV: Auto-detects columns (Transaction Date, Particulars, Debit) even with 20+ header rows
  - Australia PDF: Parses ANZ-style statements with "DD MMM Description $Amount" format
- **Matching Logic**: Exact date+amount match, Fuzzy date (±2 days) + exact amount match
- **Category Suggestions**: Auto-suggests categories from `expense_heads` (Category Master) using keyword mapping
- **Actions**: Add as Expense (validates category in master), Ignore, Export CSV report
- **Audit Trail**: Full logging in `expense_reconciliation_log` collection
- **UI Integration**: New "Bank Reconciliation" tab in Sales Dashboard with summary cards and transaction tables
- **Critical Rules Followed**: Never auto-deletes existing expenses, categories strictly from Category Master
- Files: `/app/backend/routes/bank_reconciliation.py`, `/app/frontend/src/components/BankReconciliation.jsx`
- Collections: `bank_statement_uploads`, `bank_transactions`, `expense_reconciliation_log`
- Dependencies: `pdfplumber` added for PDF parsing

### [2026-04-02] Role-Based User Manuals + Download Page
- Created 4 standalone HTML manuals, each with unique color theme:
  - `manual-super-admin.html` (Maroon) — 18 sections covering all modules
  - `manual-center-manager.html` (Green) — 8 sections: attendance, sales, expenses, HR
  - `manual-accountant.html` (Orange) — 10 sections: accounts, revenue share, MIS, loans
  - `manual-franchise-owner.html` (Purple) — 8 sections: dashboard, revenue breakdown, documents
- Added User Manuals page (`/user-manuals`) with View/Download buttons per role
- Added sidebar link under Management > User Manuals
- Files: `/app/frontend/public/manual-*.html`, `/app/frontend/src/pages/UserManuals.jsx`

### [2026-04-02] Expense Category/Mode Dropdown Fix
- Fixed: saved custom expense_type/payment_mode values not showing in dropdowns
- Root cause: Custom values not in master list caused empty Select
- Fix: `allExpenseTypes` / `allPaymentModes` via useMemo merge in ExpenseEntry.jsx

### [2026-04-02] Revenue/Profit Share Financial Breakdown + GST Changes
- India step-by-step calculation: Total Sales → Less 5% GST → Less Commissions → = Net Revenue
- 18% GST on Revenue Share shown as info note (not added to Purnabramha's 85% total)
- For Australia: 10% GST still applied to Profit Share
- Backend: `center_accounts.py`, Frontend: `CenterAccounts.jsx`

### [2026-04-01] User Manual, PIB GST, Exit Signatures, MG Payout, Payslips, Bug Fixes
- Full standalone HTML User Manual, PIB 5% GST display, Exit Agreement signatures
- MG Payout month range + Export, Edit/Delete payments, Payslip generation
- Commission display fix, ZIP download fix, Franchise list fix

### Earlier
- Commission parsers, Dual-file upload, 4-Card UI, RBAC, all base modules

## Pending / Backlog
- (P1) WhatsApp/Email notification hooks
- (P1) Code freeze preparation audit
- (P2) Image Upload for Recipes
- (P2) Franchise Deal Simulator
- (P2) 7-year retention deletion prompt
- (P2) Menu card PDF generation per center
- (P2) PDF generation refactoring (center_accounts.py + mis_dashboard.py → dedicated utility)

## Completed in This Session
- ✅ Bank Statement vs Expense Reconciliation Feature (P0) - DONE

### [2026-04-11] Location-Aware Payslip Generation (International Centers)
- **Feature**: Payslip generation is now country-aware. Auto-detects center country from DB.
- **Australia (PB-PERTH)**: Generates WA payroll format PDF with Hourly Rate, Total Hours, Gross Pay, PAYG Tax, Medicare Levy, Super (12%), Net Pay, Employer Cost. Hours fetched from `international_attendance` collection.
- **India**: Continues using existing Indian salary format (Basic, HRA, ESI, Rs currency)
- **Backend**: `get_center_country()` helper, `payslip_employees` returns `country` + `payroll_type`, `payslips_generate` routes to correct PDF generator
- **Frontend**: Badge shows "Australia - Hourly Payroll (WA Format)", info section dynamically shows relevant rules
- **Tested**: 10/10 backend + all frontend verified (iteration_62)
- Files: `/app/backend/routes/payroll.py`, `/app/frontend/src/pages/Salary.jsx`

### [2026-04-08] Payroll Calculation Template Update + CSV Export
- **Super Rate**: Updated from 11.5% to 12% (FY 2025-26)
- **Medicare Threshold**: Changed from $26k to $18,200 (tax-free threshold), matching user's Excel template
- **Calculation Method**: Changed from hourly annualization (rate × 1,976) to weekly annualization (net_weekly × 52), matching Australian payroll practice for casual workers
- **CSV Export**: Added `/api/international-attendance/export/payroll-summary-csv` endpoint with Employee Payroll + Weekly Org Cost Breakdown sections
- **Frontend**: Added Export CSV / Export PDF buttons in Monthly Summary tab, fixed Super label to 12%
- **Tested**: 15/15 backend + all frontend verified (iteration_61)

### [2026-04-08] Weekly/Monthly Organization Payroll Cost Breakdown (P0)
- **Feature**: Added organizational cost visibility — admin can see per-person and total weekly/monthly costs
- **Backend Fix**: `week-data` endpoint now returns `target_takehome_rate` and `gross_hourly_rate` per employee (was missing)
- **Frontend Updates**: 
  - Monthly Summary tab: Added "Employer Cost" column to Employee Payroll table
  - New "Weekly Organization Cost Breakdown" table: per-week Hours, Gross Pay, Net Pay, Super, Employer Cost with Monthly Total row
  - New "Per-Person Organization Cost" table: per-employee breakdown of Net Pay, Super, PAYG+Medicare, Employer Cost
  - 7 summary KPI cards (Staff, Hours, Gross, PAYG, Net, Super, Employer Cost)
- **Tested**: 12/12 backend + all frontend tests passed (iteration_60)
- Files: `/app/backend/routes/international_attendance.py`, `/app/frontend/src/pages/InternationalAttendance.jsx`

### [2026-04-08] Australian Reverse Payroll Calculation (PB-PERTH)
- **Feature**: Full reverse payroll engine — given target take-home hourly rate, calculates gross, PAYG tax, Medicare levy, superannuation, net pay, employer cost
- **Formulas**: Target net annual = hourly × 1,976. Bisection to find gross. Super 11.5% on top of gross. PAYG 2025-26 brackets. Medicare 2%.
- **Endpoints**: `/api/international-attendance/reverse-payroll-calculate`, `/api/international-attendance/payroll-report`, `/api/international-attendance/payslip`, `/api/international-attendance/payslip-pdf`, `/api/international-attendance/payroll-report-pdf`
- **Week Fix**: Week 1 = 1st-6th, Week 2 = 7th-13th, Week 3 = 14th-20th, Week 4 = 21st-27th, Week 5 = 28th-end
- **Frontend**: Updated payroll table with Gross/PAYG/Medicare/Net/Super columns and week labels
- **Tested**: 15/15 backend tests passed (iteration_59)
- Files: `/app/backend/routes/international_attendance.py`, `/app/frontend/src/pages/InternationalAttendance.jsx`

### [2026-04-05] Visual PDF Reports with KPI Cards, Charts & Logo
- MIS + Franchise Dashboard PDFs now include colored KPI cards, trend/pie charts (matplotlib), Purnabramha logo
- Fixed negative sign display in both UI (formatCurrency) and PDF (fmt)
- Added Franchise Dashboard PDF endpoint `/api/mis/franchise-pdf`

### [2026-04-05] WC Standing Consistency Fix
- Rewired `calculate_working_capital_standing()` to use `get_franchise_for_center()` (same as WC table)
- Enhanced franchise lookup with generic city/name fallback matching
- Both profits and losses now affect WC (Closing WC = Opening WC + P/L)

### [2026-04-05] MIS Working Capital Data Fix
- MIS `/working-capital` endpoint now uses same P/L logic as WC table

### [2026-04-05] Fix Endless Future Dummy Months Generation (P0)
- **Bug Fix**: WC Table and Payout Summary endpoints were not bounded by franchise agreement dates
- **Root Cause**: No date-bounding logic existed — month generation could extend indefinitely
- **Fix**: Added `get_franchise_effective_end_month(franchise)` helper that calculates `min(agreement_end_date, closure_date, current_month)`
- **Applied to**: `/api/center-accounts/wc-table` (filters sorted_months), `/api/center-accounts/payout-summary` (caps to_month)
- **Result**: Far-future dates (e.g., 2087-12) are now correctly capped at franchise's effective end month
- **Tested**: 13/13 backend tests passed (iteration_58)
- Files: `/app/backend/routes/center_accounts.py`

## Refactoring Needed
- PDF Generation logic in `center_accounts.py` → dedicated generator utility
