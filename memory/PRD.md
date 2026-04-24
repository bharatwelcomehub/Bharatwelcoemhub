# Purnabramha IntraPB — Product Requirements Document

## Problem Statement
Internal management system for "Purnabramha," a restaurant franchise.

## What's Been Implemented (Latest)

### [2026-04-24] GST Summary PDF fix + Owner Report Release UI
- **GST Summary PDF bug**: was computing GST as `total_sale × rate` (on gross), displaying "Sales GST | Rs. 10,01,161 | 5% | Rs. 50,058". Now shows the full eligible-sales breakdown: `Total Sales (Gross)` → `Less: Aggregator Sales` → `Eligible Sales (Taxable Base)` with the correct 5% on the eligible base. Fallback logic kept for edge cases (Australia uses GST-inclusive math).
- **Owner Report Release workflow**: added in-page controls on `/owner-reports`:
  - Green **"Release to Owners"** button in the sky-blue admin-preview banner → calls `POST /api/owner-reports/set-visibility {ready:true}`.
  - After release, banner turns emerald with a red **"Revoke Access"** button that sets `ready:false` (with browser confirm).
  - Test-ids: `or-release-btn`, `or-revoke-btn`, `or-released-banner`.

### [2026-04-24] GST removed from Month-M P/L everywhere (M+1 single-source-of-truth)
- User reported: PIB Section 5 Operational Balance was over-stating loss by the current month's GST because GST for Month M is paid in Month M+1 via our new `gst_liability_payment` expense row — deducting it in Month M was double-counting.
- **Fix applied everywhere** (so dashboards reconcile):
  - `center_accounts.py::calculate_working_capital_standing` — `operational_balance = sale − expenses − commission` (GST removed)
  - `center_accounts.py::get_wc_table` — `pnl = sale − expenses − commission` (GST column still displayed for reference)
  - `center_accounts.py::get_center_account_summary` — `india_net_revenue = sales − commissions`, `operational_balance = sales − expenses − commissions`
  - `center_accounts.py::get_payout_summary` — `net_revenue_for_share = sales − commissions`
  - `mis_dashboard.py` — 3 profit formulas (`overview`, `trends`, `quarters`) all updated
  - `owner_reports.py::_compute_monthly_report` — `pnl = sales − expenses − commissions`
  - `frontend/CenterAccounts.jsx::computedWcRows` live cascade — `pnl = sale − expenses − commission`; UI description updated
- **PIB PDF cleanup**: Section 4 and Section 5 now show GST as a **Memo line** labelled "booked as liability, paid next month" instead of a `Less:` deduction. Subtotals match the new formula.
- **Verified on PB-HSR 2026-03** (Sales ₹27,000, Expenses ₹4,000, Comm ₹0, GST ₹1,150):
  - Old Net Revenue: ₹25,850 (wrongly deducted GST) → New Net Revenue: **₹27,000** ✅
  - Old Owner PNL: ₹21,850 → New PNL: **₹23,000** (diff = exactly ₹1,150 GST) ✅
  - WC P/L, Operational Balance, MIS profit all realigned.
- Model: GST cash-impact is now recorded exactly **once** — as the auto-created "GST PAYMENT" expense row on the 20th of M+1 (via `/api/gst/mark-paid`).

### [2026-04-24] Refactor — Extracted all PDF/Excel generation into `utils/pdf_generator.py`
- Moved 855 lines of `reportlab` / `openpyxl` rendering code out of `/app/backend/routes/center_accounts.py` (was 3,207 lines → now 2,352 lines, -27%).
- New `/app/backend/utils/pdf_generator.py` (~640 lines) exposes 7 pure byte-returning builders:
  - `build_wc_table_pdf`, `build_wc_table_excel` (Working Capital statements)
  - `build_pib_pdf` (9-section PIB report)
  - `build_gst_summary_pdf`, `build_commission_summary_pdf`
  - `build_mg_payout_excel`, `build_mg_payout_pdf`
- Brand palette (`BRAND_MAROON`, `BRAND_NAVY`, `BRAND_GOLD`, etc.) centralised at top of the new module.
- Route handlers in `center_accounts.py` are now 5-10 lines each (auth + fetch data → `build_*_pdf(data)` → Response). Each builder is pure (no DB, no request) and can be unit-tested in isolation or reused by future scheduled-email / audit flows.
- **Verified zero regression**: all 5 endpoints return valid PDFs (magic `0x25504446`) / XLSX (`0x504b0304`); `pypdf` text extraction on the PIB PDF confirms all 9 sections present (`1. SALES SUMMARY` … `9. TAX RULES`), GST value `1,150`, Sales `Rs. 27,000`, Net Revenue all correct. Lint clean on the new file.

### [2026-04-24] GST Eligible-Sales, M+1 Liability Accounting, PIB Preview, Owner Reports (5-feature batch)
- **GST on Net Eligible Sales**: New central `/app/backend/utils/gst.py` — `compute_gst_from_rows()` and `gst_rate_for()`. Rule: `GST = (Total Sale − Swiggy − Zomato − DoorDash) × rate`, rate = 5% for India centers, 10% for PB-PERTH / outside-India. Replaces prior gross-sales math everywhere it's referenced.
- **GST Liability & M+1 Payment**: New collection `gst_liabilities` keyed by (center, month). Endpoints at `/app/backend/routes/gst_liabilities.py`:
  - `POST /api/gst/recompute` → scans daily_sales, upserts a liability per (center, month) bucket; idempotent (preserves paid state).
  - `POST /api/gst/liabilities` → list with optional filters (center / year / paid|unpaid) + total_payable + total_paid.
  - `POST /api/gst/mark-paid` (SA only) → creates expense row in Month M+1 dated the 20th by default with `expense_type=GST PAYMENT`, `source=gst_liability_payment`, links `paid_expense_id` back to the liability.
  - `POST /api/gst/unmark-paid` (SA only) → deletes the linked expense and clears paid flags (reversal).
- **PIB Preview-Before-Download**: `POST /api/center-accounts/preview-pib` returns the summary payload without writing a PDF. Frontend Center Accounts page intercepts the PIB card click to open a Dialog (`data-testid=pib-preview-dialog`) showing Total Sale / GST (with rate × eligible) / Commission / Expenses / Net Revenue / Revenue Share + Sales Breakdown + collapsible raw JSON, with an in-modal **Download PDF** button that streams `generate-pib`.
- **Owner Reports** (`/app/frontend/src/pages/OwnerReports.jsx` + `/app/backend/routes/owner_reports.py`): New `/owner-reports` route gated by visibility. Admin/Super Admin sees data always (with sky "Admin preview — not yet released to owners" banner when unflagged). Franchise Owners see the amber "Report not yet available" banner until Accounts calls `POST /api/owner-reports/set-visibility {ready:true}`. Filters: Center / Year / Month. Shows KPI cards (Sales, Expenses, GST %, Net P/L), Sales Breakdown, Platform Commissions table, Expense-by-Category table. Collection: `owner_report_visibility`.
- **Verified end-to-end (iteration_76)**: 13/13 backend pytest cases passed on live preview URL. Manual browser verification of Owner Reports page + PIB Preview modal for PB-HSR 2026-03 (Sales ₹27,000 → Eligible ₹23,000 → GST ₹1,150 at 5%) all rendered correctly.

### [2026-04-22] PIB Commissions & GST Deductions — Monthly Importer Extended
- `_parse_pib_sheet` parses the PIB (Profit Invoice Breakdown) sheet inside each monthly Excel:
  - Per-platform commissions (Swiggy, Zomato, Card, PhonePe) → one `monthly_commissions` row per platform with deterministic `commission_id = HIST-{center}-{month}-{PLATFORM}` (idempotent)
  - Revenue Share %, SGST, CGST, GST Paid, Gross & Net Sale for Revenue → `historical_pib` collection (new)
- WC Breakdown (`get_wc_table`) merges `historical_pib.total_gst_on_revenue` into the GST column for imported months (without overwriting live gst).
- MIS Overview merges PIB GST into `summary.total_gst` + per-center GST breakdown.
- **Verified on HSR March 2026**: Swiggy ₹84,517 − ₹29,528.55 = ₹54,988.45 net, Zomato ₹52,034 − ₹15,347.14 = ₹36,686.86 net, Card ₹2,86,525 − ₹5,445.03 = ₹2,81,079.97 net. Revenue Share ₹1,71,614.97, SGST+CGST = ₹30,890.70 flowing into MIS + WC. 55/55 regression green.

### [2026-04-22] Phase 2: Monthly Expense / Trial Balance Importer
- New endpoint `POST /api/historical/import-monthly-file` (Super Admin, multi-file capable) for the "EXPENCE SHEET -{CENTER}- {MONTH}.xlsx" workflow.
- Parses **3 data sources** from one upload:
  - `TRIAL BAL.` sheet → head-wise rollup into new `historical_trial_balance` collection (center, month, heads:{}, total_expenses, total_sales)
  - Matching daily expense sheet (e.g. `MARCH.26`) → writes rows into `db.expenses` with `source:"monthly_import:..."` (93 rows for HSR March 2026)
  - `CASH SALE + PHONE PE + CARD + SW + ZM` sheets → `db.daily_sales` upsert per date (cash/online/phone_pe/card/swiggy/zomato breakdown)
- Auto-detects center + month from filename; optional `center_override` / `month_override` form fields for edge-cases.
- Idempotent (re-import replaces monthly_import rows cleanly). **Live operator-entered data is protected** — if `daily_sales` has a row for that date with a non-monthly_import source, import skips it and reports `skipped_live_days`.
- Supporting endpoints: `/monthly-summary` (per-center earliest/latest month + totals), `/clear-monthly` (scoped wipe).
- Admin UI `/historical-import` now has a third "Monthly Expense/Trial Balance Import" card (blue theme) with multi-file picker and per-file result detail, plus a help footer listing where the imported data shows up (WC Breakdown, MIS Dashboard, Franchise Dashboard, Expense Master).
- **Verified**: HSR March 2026 file → 37 TB heads (₹14.6L exp / ₹12.5L sale), 93 expense rows, 31 days parsed (31 skipped because PB-HSR already had live sales for March). 12 new pytest + 43 regression = 55/55 green (iteration_75).

### [2026-04-22] Phase 1b: Loans Historical Importer (inter-center transfers)
- New endpoint `/api/historical/import-loans-file` (Super Admin) parses LOANS sheets in the WC Assessment Excel — each date-by-counterparty cell in a 4-column group (DATE / AMOUNT GIVEN / AMOUNT RECD / BALANCE) produces a mirror pair in `loan_entries` (given + taken, linked via `linked_loan_id`).
- Deterministic `loan_id` = `HIST-{giver}-{taker}-{date}-{int_amount}-{G|T}` → safe to re-import, auto-dedupes cross-sheet overlaps.
- `/api/historical/loans-summary` rolls up per center (count, total given, total taken) and `/clear-loans` supports per-center or global wipe.
- Frontend `/historical-import` page gets a second "Loans Import" card (amber theme) with upload, result card, summary table with net-flow column.
- Verified on user's file: 247 txn pairs (396 HIST- docs after cross-sheet dedup) imported for 6 centers spanning 2023-2026. Mirror integrity verified. 10 new pytest + 33 regression = 43/43 (iteration_74).

### [2026-04-22] Phase 1: Historical Monthly Rollup Migration (Apr 2023 onwards)
- New collection `historical_monthly_summary` keyed by `{center, month}` carrying sale, expenses, pnl, opening_wc, closing_wc, diff_wc, bank_balance.
- New module `/app/backend/routes/historical_import.py` with endpoints:
  - `POST /api/historical/import-wc-file` (Super-Admin only) — multipart xlsx upload; maps sheet names (S-NAGAR, DOMBIVLI, KHARADI, THANE, HSR-BLR, HINJAWADI) to system center codes (PB-SN, PB-DV, PB-KN, PB-TH, PB-HSR, PB-HW); upserts per {center, month}; skips LOANS sheets.
  - `POST /api/historical/summary` — per-center aggregate row counts + date range + totals.
  - `POST /api/historical/clear` — scoped delete (per center or global).
- Merged into Center Accounts `get_wc_table` and `calculate_working_capital_standing`: for months without live daily data, historical rows fill the WC Breakdown view and cascade Balance WC correctly (no double count where live data exists).
- Merged into `/api/mis/overview`: historical sales/expenses inject into summary + per-center rows for months with no live data.
- New frontend page `/historical-import` (Super Admin only) — upload button, import result card, per-center summary table with clear-per-center action.
- **Verified**: user's sample file `Working Cap Assesment And Loans.xlsx` → 130 rows imported across 6 centers, Jan 2023 → Mar 2026. 10 new pytest + 23 regression = 33/33 passed (iteration_73).

### [2026-04-21] MIS + Franchise Dashboard ↔ WC Table Parity
- Reported: Sales / Expenses / GST / Commission / Working Capital on MIS Dashboard and Franchise Owner Dashboard didn't reflect the WC table master data.
- Root cause: `/api/mis/overview` and `/api/mis/working-capital` aggregated directly from `daily_sales`, `expenses`, `monthly_commissions` without applying the WC-table overrides (`commission_target`, `gst_target`). Expense adjustments were already flowing via INTRA rows in `db.expenses`.
- Fix: New helper `fetch_wc_overrides()` in `mis_dashboard.py`; applies `gst_target` and `commission_target` as absolute replacements to the summary + per-center rows. `center_accounts.calculate_working_capital_standing()` updated with the same override logic so Working Capital card cascades loss/profit correctly.
- Verified via iteration_72: all 6 new pytest cases (parity + override propagation + WC loss cascade) + 17 regression tests passed.

### [2026-04-21] WC Table — Live Cascade + Single-Source INTRA (3 bug fixes)
- **Bug 1 (no live recalc)**: Expense & WC-Adj inputs converted from uncontrolled `defaultValue` to controlled React state (`wcEdits`). Added `computedWcRows` useMemo that cascades P/L → Opening WC → Balance WC → Diff of WC → Rev-Share status across all months on every keystroke. Dirty rows get a yellow tint + '*' marker.
- **Bug 2 (expenses reset / double counted)**: `get_wc_table` no longer adds `expense_adjustment` from `wc_month_overrides` on top of the db.expenses aggregate (the INTRA row IS the adjustment). `wc-row-save` contract changed to accept `target_expenses` (absolute desired total); backend computes delta vs real (non-INTRA) db.expenses and writes a single INTRA row, replacing any prior one. Saving a target equal to real deletes the INTRA row.
- **Bug 3 (INTRA not visible in Expense Master on correct date)**: INTRA row now dated on the LAST day of the month (calendar.monthrange; handles leap years) instead of the 1st.
- Verified end-to-end via testing_agent_v3_fork (iteration_70): 7/7 new pytest cases + 10/10 regression (attendance lock + prior WC) + full frontend live-cascade flow all green.

### [2026-04-21] WC Table Exports + Auto INTRA Expense + Center-Specific Attendance Lock
- `POST /api/center-accounts/wc-row-save` auto-creates a mirrored "INTRA CENTER ADJUSTMENT" entry in `db.expenses` for the same center+month (idempotent via `intra_entry_id`).
- `POST /api/center-accounts/wc-table/export-pdf` and `/export-excel` produce branded Purnabramha PDF / XLSX downloads.
- `AttendanceLockRequest.center` now optional. Lock docs keyed by `{month, center}`; empty center represents a global (all-centers) lock.
- `/lock`, `/lock-status`, `is_month_locked`, `is_date_locked`, `is_attendance_locked` (attendance_dashboard.py, attendance.py, server.py) updated to be center-aware; global locks take precedence.
- `bulk_attendance` and `bulk_attendance_month` write-gates now pass the request center to the lock check, so a center-specific lock only blocks writes for that center.
- Frontend `AttendanceDashboard.jsx`: lock button label, badge and confirm dialog now echo the selected center or "ALL CENTERS".
- Verified end-to-end via testing_agent_v3_fork — 10/10 backend pytest cases + frontend scope label checks passed (iteration_69.json).

### [2026-04-18] International Weekly Roster (Complete - All 3 Phases)
**Phase 1 - Core CRUD + Masters:**
- Role Master (10 default roles: Biller, Plater, Service, Kitchen Hand, etc.)
- Shift Master (Morning, Evening, Full Day, Split Shift with default times)
- Settings Master (WhatsApp template, confirmation cutoff, max hours)
- Weekly roster creation with header (week, center, status) + line items
- Grid View (day cards with color-coded shifts) + List View (tabular)
- Employee auto-fill from Employee Master (active, international only)
- Working hours auto-calculation, day name auto-derivation
- Copy Last Week feature
- Excel export with color-coded statuses
- Full audit trail on all changes
- Role-based access (Super Admin, Admin, Center Manager)

**Phase 2 - WhatsApp Confirmation:**
- wa.me link generation with configurable message template
- Send for Confirmation workflow (Draft → Sent)
- Confirm/Deny response capture
- Replacement flow after denial (with history tracking)
- Status flow: Draft → Sent → Confirmed/Denied → Replaced

**Phase 3 - Attendance Sync + Dashboard:**
- Confirmed roster → International Attendance sync
- Dashboard stats (Total Shifts, Confirmed, Pending, Denied, Hours, Staff)
- Lock/Unlock roster weeks

### [2026-04-17] Working Capital Logic Overhaul
### [2026-04-16] Dashboard & Data Visibility Fixes (5 issues)
### [2026-04-16] International Attendance Calendar Weeks
### [2026-04-16] Salary Fixes + Food Safety Tablet UI

## Pending / Backlog
- (P1) WhatsApp/Email notification hooks
- (P1) Code freeze preparation audit
- (P2) Image Upload for Recipes, Franchise Deal Simulator, Menu card PDF, PDF refactoring, 7-year retention deletion prompt
