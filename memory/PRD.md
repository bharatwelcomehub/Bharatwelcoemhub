# Purnabramha IntraPB — Product Requirements Document

## Problem Statement
Internal management system for "Purnabramha," a restaurant franchise.

## What's Been Implemented (Latest)

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
