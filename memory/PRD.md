# Purnabramha IntraPB — Product Requirements Document

## Problem Statement
Internal management system for "Purnabramha," a restaurant franchise.

## What's Been Implemented (Latest)

### [2026-05-04] Loan Entries — TAKEN vs GIVEN bug fix (Dombivali)
**User issue (with screenshot, PB-DV)**: "Loans Outstanding" tile showed ₹22,99,517 with 12 active loans, but Dombivali only ever **gave** loans (to HSR/MGT/Sambhajinagar/Thane) — outstanding (taken) should be ₹0. Conversely, "Loans Given" tile showed ₹0.

**Root cause**: `/api/loan-entries/summary` was summing ALL loan rows (regardless of `loan_type`) into `total_outstanding`. So GIVEN loans were polluting the TAKEN KPI and reducing Available Capital. The `summary.total_given` field that the UI reads from didn't even exist on this endpoint — only on `/list`.

**Fix (`routes/loan_entries.py::get_loan_summary`)**:
- Splits rows into `loans_taken` (`loan_type != "given"`) and `loans_given` (`loan_type == "given"`).
- `loans.total_outstanding` and `loans.active_count` now reflect TAKEN only — drives the "Loans Outstanding" red KPI and "X active loans" subtitle.
- `working_capital.utilized` and `available` now subtract TAKEN outstanding only — Dombivali's full ₹9L WC stays available.
- New `summary` block exposes `total_given`, `total_given_repaid`, `total_given_outstanding`, `active_given_count` — matching the keys the existing UI reads for the teal "Loans Given" tile.

**Result for PB-DV on production**:
- Loans Outstanding: ₹0 · 0 active loans ✓
- Loans Given: ₹22,99,517 · Outstanding: ₹22,99,517 ✓
- Available Capital: ₹9,00,000 (full WC) ✓

**Files**: `backend/routes/loan_entries.py`. Lint warnings pre-existing.

### [2026-05-04] Bank Reconciliation — Bulk Ignore + Category Dropdown bug fix
**User issues (with screenshot)**:
1. Category dropdown blank in "Bulk Add as Expense" modal.
2. Need a "Bulk Ignore" action for selecting multiple unrecorded transactions.

**Fix 1 — Categories not loading**:
- Frontend was calling `POST /api/category-master/expense-heads` with token. **No such endpoint exists**.
- Actual endpoint: `GET /api/sales/expense-heads` (no auth, returns 35 standard heads or DB-customised list).
- Updated `pages/BankReconciliation.jsx` to call the correct endpoint. Verified live: `count: 35` heads loaded.

**Fix 2 — Bulk Ignore**:
- New backend endpoint `POST /api/bank-reconciliation/bulk-ignore` (`routes/bank_reconciliation.py`):
  - Accepts `{ transaction_ids[], upload_id, reason, token }`.
  - `update_many` flips `match_status: ignored` for all selected txns + writes one audit log row per txn.
  - Returns `ignored_count` for the toast.
- Frontend: new red-outline "Bulk Ignore (N)" button next to "Bulk Add as Expense" in the selection toolbar (Unrecorded tab). Prompts for a reason once and applies to all selected rows.

**Files**: `backend/routes/bank_reconciliation.py`, `frontend/src/pages/BankReconciliation.jsx`. Lint clean. UI smoke-test green.

### [2026-05-04] Franchise Owner read-only access to all docs + Full Net Revenue/GST chain in PDFs
**User asks**:
1. Franchise Owner Dashboard should expose ALL documents (LIC, agreements, KYC) — read-only, no edits.
2. All report PDFs must clearly show Net Revenue + GST + Revenue Share + Commission details.

**Documents — Franchise Owner Dashboard (`pages/FranchiseOwnerDashboard.jsx`)**:
- Documents tab now has 3 sections:
  - **Franchise Agreement**: one-click "Download Agreement PDF" button that calls `/api/franchises/generate-agreement/{code}` (60+ page comprehensive FOCO agreement, generated on-demand from current franchise record).
  - **Franchise Records (LIC, KYC, Agreements)**: lists everything in `franchiseInfo.documents`. Each row has tag + uploaded-date + download button (no edit/upload controls).
  - **Other Documents**: existing general documents tab (bills, certificates) — unchanged.
- All download flows are strictly read-only.

**Backend authorization (`routes/franchises.py`)**:
- `/franchises/documents/download/{code}/{doc_id}` and `/franchises/generate-agreement/{code}` switched from admin-only to `check_access_with_franchise`. Franchise owners can ONLY download for their own franchise (verified by matching `session.franchise_code`); admins/SA/accounting unrestricted as before.

**PDF reports — Net Revenue / GST / Comm / Rev Share chain (`routes/mis_dashboard.py::_build_franchise_pdf`)**:
- **Bug fix**: `Revenue Share` was computed as `profit × rev_share_pct` (wrong — that's profit-share, not revenue-share). Now correctly = `Net Revenue × rev_share_pct` where Net Revenue = Sales − Commissions − GST.
- **New KPI cards**: "GST on Sales" (purple) and "Net Revenue" (cyan) added alongside Sales/Expenses/Commissions/Profit/WC/Avg-per-Bill/Revenue-Share — 9 cards total.
- **Financial Summary table** rewritten as an accountant-friendly chain:
  ```
  Total Sales
  Less: Total Commissions
  Less: GST on Sales
  = Net Revenue                    (Sales − Comm − GST)
  Less: Total Expenses
  = Net Profit
  Working Capital
  Revenue Share Payable (X% × Net Revenue)
  Avg per Bill
  ```
- Verified via `/api/mis/franchise-pdf` + `pdfminer`: rendered PDF contains "Net Revenue" 4×, "GST on Sales" 2×, "= Net Revenue" 1×, "Less: Total Commissions" 1×, "Less: GST on Sales" 1×, "Revenue Share" 3×.

**Files**: `backend/routes/franchises.py`, `backend/routes/mis_dashboard.py`, `frontend/src/pages/FranchiseOwnerDashboard.jsx`. Lint clean (warnings are pre-existing). UI smoke-test green.

### [2026-05-04] CRITICAL BUG FIX — India Net Revenue + 3 Center Account fixes
**User issue (with screenshot, PB-KAL April 2026)**: Net Revenue showed −14,069.31 on Sales 8,27,928 with Deductions 42,101.49. Math impossible. Plus 3 more issues reported.

**Root cause for Net Revenue**: My previous Outside-IN fix accidentally kept the legacy line `net_revenue = sales_ex_gst − total_expenses − total_commission` for India. Then I changed `financial_summary.net_revenue` to use this `net_revenue` variable (instead of `india_net_revenue`), which made the API return Sales − Comm − GST − **Expenses** for India centers. With Kalyan's 7.99L expenses, this drove Net Revenue negative.

**Fixes**:
1. **India Net Revenue** (`routes/center_accounts.py` ~line 1402): Now uses centralized `compute_net_revenue(total_sale, total_commission, sales_gst_amount, 0, "India")` — Expenses are NOT subtracted. Verified: Kalyan 8,27,928 − 42,101.49 = **₹7,85,826.51**.
2. **PhonePe / BharatPe row in Sales Breakdown** (`pages/CenterAccounts.jsx`): Backend already returns `sales.bharat_pay`. Added an indigo-50 row "PhonePe / BharatPe (UPI)" beneath Cash Sales when value > 0.
3. **Loans Given/Taken now cumulative** (`routes/center_accounts.py` ~line 1485): Was filtering by selected month so older 22-lakh loans created in earlier months disappeared. Now passes `month=None` to `get_loans_given_summary` / `get_loans_taken_summary`, returning all-time outstanding (correct balance-sheet view).
4. **Ledgers in Franchise Owner Dashboard** — gated on monthly report release:
   - Backend (`routes/ledgers.py`): Each `/api/ledgers/<type>` endpoint now allows franchise owners to download ANY of the 10 ledger types if `owner_report_visibility` for that center+month has `ready: True`. Otherwise 403 with helpful message.
   - `/api/ledgers/owner/list` updated to return both classes of release (full monthly report ready vs legacy owner-ledger-only) plus `available_ledgers` per month and human labels.
   - Frontend (`pages/FranchiseOwnerDashboard.jsx`): "My Ledgers" dialog now shows each released month as an expandable card listing ALL 10 unlocked ledger types (Sales Register, Expense Register, Cash, Bank, Commission, Loans, Payroll, GST, P&L, Owner Ledger) with PDF + Excel download buttons. Released months are tagged "Full Report Released" or "Owner Ledger Only".

**Files**: `backend/routes/center_accounts.py`, `backend/routes/ledgers.py`, `frontend/src/pages/CenterAccounts.jsx`, `frontend/src/pages/FranchiseOwnerDashboard.jsx`. Lint clean.

### [2026-05-04] Australia Profitability chain mirrored across PIB / Owner Reports / Excel
**User ask**: Make the new "Sales − Deductions = Net Revenue, Net Revenue − Expenses = Profitability, 80/20 on Profitability" chain visible in offline exports too.

**Updates (Australia / Outside-IN only — India unchanged)**:
- **PIB PDF (`utils/pdf_generator.py::build_pib_pdf`)** — Section 4 now prints:
  - Total Sales → Less: Commissions → Less: Commission GST (10%) → Less: GST on Eligible Sales (10%) → **NET REVENUE** (gold-highlighted) → Less: Total Expenses → **PROFITABILITY (Base for 80/20 Split)** (green-highlighted).
  - Section 7 base label changed from "Net Revenue" → "Profitability" for profit_share centers.
- **Owner Reports**:
  - Backend (`routes/owner_reports.py`) now returns `country` + `profitability` (Sales − Comm − GST − Expenses) for Australia.
  - Frontend (`pages/OwnerReports.jsx`) shows a 5th emerald "Profitability" KPI card for Australia centers; renames "Net P/L" → "Net Revenue" and adds subtitle "Sales − Comm − GST".
- **Backend MG/Payout aggregator** (`routes/center_accounts.py` line 2448-2462): Australia branch now computes `net_revenue_for_share = max(0, NetRev − Expenses)` using the centralized `compute_net_revenue` helper. This keeps the MG Payout Excel/PDF columns in sync with the new model (80% × Profitability for Franchise Owner share).

**Verification**: Generated live PIB PDF via `/api/center-accounts/generate-pib` for PB-PERTH 2026-04. `pdfminer` confirmed the rendered PDF contains "NET REVENUE", "PROFITABILITY", "Less: Total Expenses", and "Section 7: PROFIT SHARE CALCULATION (80/20 SPLIT) … Profitability (Base for Calculation)".

**Files**: `backend/utils/pdf_generator.py`, `backend/routes/owner_reports.py`, `backend/routes/center_accounts.py`, `frontend/src/pages/OwnerReports.jsx`. Lint clean.

### [2026-05-04] Australia (PB-PERTH) — Net Revenue / Profitability split + 80/20 on Profitability
**User issue (with screenshot)**: For Perth Australia, "Net Revenue" was showing 3,467.19 on Sales 36,310 — incorrect. User spec:
1. **Net Revenue = Total Sales − Total Deductions ONLY** (no expenses)
2. **Profitability = Net Revenue − Total Expenses**
3. **Profit Split = 80% Franchisee / 20% Purnabramha LLC** on Profitability

**Fix (Australia / Outside-India only — India behaviour unchanged)**:
- `utils/gst.py::compute_net_revenue` for Outside-IN now returns `Total Sale − GST − Commissions × (1 + rate)` (expenses removed from this formula).
- `routes/center_accounts.py` Australia branch:
  - Computes `profitability = net_revenue − total_expenses`.
  - 80/20 share now uses `profitability` (was `net_revenue`).
  - `financial_summary.net_revenue` (Sales − Deductions) and `financial_summary.profitability` (NetRev − Expenses) both exposed in the API.
  - `share_calculation.total_deductions` now includes commission GST (10%) so `Sales − Deductions = Net Revenue` matches exactly.
- Frontend `CenterAccounts.jsx`:
  - KPI grid expands to 5 columns for Australia. New "Profitability" card (emerald) sits beside "Net Revenue".
  - Total Deductions card now includes commission GST for Australia (label: "Commissions (incl GST) + GST on Sale").
  - Net Revenue card subtitle: "Sales − Deductions" (AUS) / "Sales − GST − Commissions" (India).
  - Profit Calculation Breakdown reordered: Sales → Less GST → Less Comm → Less Comm GST = **Net Revenue** → Less Expenses = **Profitability (Base for 80/20 Split)**.
- Math sanity-checked: `Sales − Deductions = Net Revenue` and `NetRev − Expenses = Profitability` and `80%/20% × Profitability = franchise/PB shares` all OK.

**Files**: `backend/utils/gst.py`, `backend/routes/center_accounts.py`, `frontend/src/pages/CenterAccounts.jsx`. Lint clean.

### [2026-05-03] Bank Reconciliation — Single source + label cleanup
**User issue**: Bank Reconciliation existed in TWO places (sidebar `/bank-reconciliation` AND a tab inside Sales & Expenses), and the two were not state-synced. Action labels were inconsistent ("Remove", "Undo Ignore") instead of a clean "Delete".

**Fix**:
- **Removed** the duplicate Bank Reconciliation tab from `pages/SalesExpenses.jsx` (tab trigger + tab content + import).
- **Deleted** the now-orphan component file `frontend/src/components/BankReconciliation.jsx`.
- **Single entry point**: only the dedicated sidebar page `/bank-reconciliation` (rendered by `pages/BankReconciliation.jsx`) remains. Eliminates state-sync confusion entirely.
- **Renamed action buttons** on contextual tabs (per user spec):
  - Unrecorded: `Add` · `Ignore` (unchanged)
  - Added: `Delete` (was "Remove") · `Move to Ignored`
  - Ignored: `Delete` (was "Undo Ignore") · `Add as Expense`
- "Delete" everywhere = soft reset → transaction goes back to Unrecorded.

**Files**: `frontend/src/pages/SalesExpenses.jsx`, `frontend/src/pages/BankReconciliation.jsx`, deleted `frontend/src/components/BankReconciliation.jsx`. Lint clean. Verified: Sales & Expenses no longer shows the BR tab; standalone page renders correctly.

### [2026-05-03] BUG FIX — Bank Reconciliation page rendering blank
**User issue**: `intra.purnabramha.com/bank-reconciliation` came up completely blank (white screen).

**Root cause**: Recently added "Reset/Undo" dialog in `BankReconciliation.jsx` used `<DialogDescription>` JSX, but the import statement was missing this symbol. Result: ReferenceError at render time → React component crash → blank page.

**Fix**: Added `DialogDescription` to the import on line 9 of `frontend/src/pages/BankReconciliation.jsx`. Verified by logging in as super admin on preview and rendering the page — Recent Uploads table loads correctly with all rows, no console errors.

**Files**: `frontend/src/pages/BankReconciliation.jsx` (1-line import fix).

### [2026-04-30] Bank Reconciliation — Bulk Add for Similar Narrations
**User issue**: With 100+ unrecorded txns having repeating narrations (Salary debits, Card 2473 purchases, etc.), adding them one by one as expenses was very tedious.

**Fix**:
- New backend endpoint `POST /api/bank-reconciliation/bulk-add-expense` — accepts `{token, upload_id, transaction_ids[], expense_type, payment_mode, description}`. Each txn becomes its own expense row using its own date + amount. Common category + payment_mode + optional description applied to all. Returns `{added, skipped, errors[]}`.
- Frontend: BankReconciliation page now has:
  - **Checkboxes** on every Unrecorded row (header has "select all on page")
  - **Click on any narration text** auto-selects every other row with the same narration prefix (first 30 chars, case-insensitive) — perfect for grouping all "VISA DEBIT PURCHASE CARD 2473" or "RTGS SALARY" entries in one click
  - **Sticky bulk toolbar** at the top of the table when ≥1 row is selected: shows count + total ₹, plus "Bulk Add as Expense" button
  - **Bulk Add Dialog**: shows preview list (up to 8 rows + "…and N more"), category dropdown (validated against Category Master), payment mode select, optional description override
  - Tooltip below the toolbar (when no selection) explains the workflow
- Validation: backend checks category exists in `expense_heads`, skips already-added txns, returns first 20 errors for surfacing.
- Audit: each bulk-added expense logs `action: bulk_add_expense` to `expense_reconciliation_log`.

**Files**: `backend/routes/bank_reconciliation.py` (new endpoint + Body import), `frontend/src/pages/BankReconciliation.jsx` (selection state, dialog, toolbar, narration-click grouping). Lint clean.

### [2026-04-30] Net Revenue chain visible in EVERY report/export — PIB, Payout Excel/PDF, Daily/Monthly/Yearly Text
**User instruction**: "HOPE THE SAME IS AVAILABLE IN REPORT AND PIB MONTHLY AND ALL SALES TEXT GENERATOR AND ALL PLACES."

**Updated all consumer-facing exports to show the same Net Revenue chain**:

1. **PIB Report (Section 4 Financial Summary)** — `pdf_generator.py::build_pib_pdf`
   - Old: Total Sales − Expenses − Commissions = Net Revenue (with GST as memo)
   - New: Total Sales − Commissions − GST on Eligible Sales (5% inclusive) = NET REVENUE; Expenses shown separately as info only
2. **PIB Section 5 (Operational Sustainability)** — same fix applied: GST now `Less: GST on Eligible Sales`. `operational_balance` formula updated in `center_accounts.py` to subtract GST.
3. **Month-wise Payout Summary Excel** (`build_mg_payout_excel`) — added 3 columns: GST, Commissions, Net Revenue. Now 12 cols. TOTAL row sums all.
4. **Month-wise Payout Summary PDF** (`build_mg_payout_pdf`) — added Net Rev, GST, Comm columns. 12 cols total with adjusted column widths.
5. **Monthly Text Generator** — appends "Net Revenue Calculation" block with Aggregator Sales / Eligible Sales / GST / Total Commissions / NET REVENUE.
6. **Yearly Text Generator** — same block.
7. **Daily Text Generator** — appends per-day Net Revenue Calculation block (Aggregator + Eligible + GST + Net Revenue) on each daily summary.

**Daily/Monthly/Yearly text use shared `compute_gst_from_rows`** — single source of truth.

**Verified PB-HSR Feb-26**:
- PIB: NET REVENUE = ₹8,71,514.86, OPERATIONAL BALANCE updated, Revenue Share Base shown as ₹8,71,514.86
- Payout Excel TOTAL row (Dec25–Feb26): Sales 29,27,404 / GST 1,18,463.61 / Comm 0 / Net Rev 28,08,940.39 / Rev Share 4,21,341.06
- Monthly Text: shows full chain block at the end

### [2026-04-30] Payout Summary table — Net Revenue chain visible
**User issue**: Month-wise Payout Summary table only showed `Total Sales` then jumped straight to `Revenue Share`. User asked to see the calculation base (Net Revenue) since the 15% is computed on Net Revenue, not on Total Sales.

**Fix**:
- Backend `/api/center-accounts/payout-summary` now returns `gst_on_sales`, `total_commissions`, and `net_revenue` for each month.
- Frontend table expanded from 10 → 13 columns: **Month · Total Sales · GST · Commissions · Net Revenue · Revenue Share · MG · Type · Payable · Paid · Pending · Status · Action**.
- Net Revenue column is highlighted in blue + bold to make the calculation chain visible: Sales → minus GST → minus Comm = Net Rev → × 15% = Rev Share.

**Verified on PB-HSR Dec-25 to Feb-26**:
| Month | Sales | GST | Comm | Net Revenue | Rev Share |
|---|---|---|---|---|---|
| Dec-25 | 9,91,876 | 42,250.57 | 0 | 9,49,625.43 | 1,42,443.81 |
| Jan-26 | 10,29,396 | 41,595.90 | 0 | 9,87,800.10 | 1,48,170.01 |
| Feb-26 | 9,06,132 | 34,617.14 | 0 | 8,71,514.86 | 1,30,727.23 |

**Expected on PB-KAL Apr-2026 after deploy**: 8,27,928 → GST 39,425.14 → Comm 2,676.35 → **Net Rev 7,85,826.51 → Rev Share ₹1,17,873.98**.

### [2026-04-30] Payout Summary — Revenue Share now subtracts GST from base
**User issue**: Payout Summary showed Apr-2026 PB-KAL Revenue Share = ₹1,23,787.75 (= 15% × Sale − Comm), but expected = 15% × (Sale − Comm − GST) ≈ ₹1,17,874.

**Root cause**: `/api/center-accounts/payout-summary` had its OWN duplicate net-revenue calc on lines 2440-2453 of `center_accounts.py` that did NOT subtract GST. The main `summary` endpoint had been fixed earlier but the payout endpoint kept the old "GST is paid in M+1, don't double count" formula.

**Fix**: Replaced inline math with the shared `compute_gst_from_rows` utility + the corrected formula:
- India: Net Rev = `Total Sales − Commissions − GST`
- Outside: Net Profit = `(Sales − GST) − Expenses − Commissions`

**Verified on PB-HSR Nov-2025 to Feb-2026**:
- Nov-25: Sale 9,87,909 → GST 38,643.24 → Net Rev 9,49,266 → Rev Share **₹1,42,389.86** ✓
- Dec-25: Sale 9,91,876 → GST 42,250.57 → Net Rev 9,49,625 → Rev Share **₹1,42,443.81** ✓

**For PB-KAL Apr-2026 post-deploy**: Sale 8,27,928 → GST 39,425.14 → Comm 2,676.35 → Net Rev 7,85,826.51 → **Rev Share ₹1,17,873.98** (was ₹1,23,787.75).

### [2026-04-30] GST shown UNCONDITIONALLY in dashboard (decoupled from gst_applicable flag)
**User issue**: PB-KAL Apr-2026 KPI cards showed Total Deductions ₹2,676.35 (commissions only) and Net Revenue ₹8,25,251.65 (Sales − Commissions only). GST was missing because the franchise has `gst_applicable=False` set, so the backend was zeroing out `sales_gst` in the response.

**Fix**: In `center_accounts.py::get_center_account_summary` line 1422, removed the `if gst_applicable_india else 0` guard. GST is now computed unconditionally from sales receipts (inclusive carve-out from eligible base) and shown in:
- `financial_summary.sales_gst`
- `share_calculation.total_deductions` (= commissions + GST)
- `financial_summary.net_revenue` (= Sales − Commissions − GST)

The `gst_applicable` flag is now **only** used by the `gst_liabilities` collection to decide if a payable row should be created (i.e., govt-payment tracking). The dashboard math is consistent across every center regardless of the flag — matching user spec "GST same calculation everywhere".

**Verified on PB-HSR Feb-2026 with flag forced to False**: Sales GST ₹34,617.14, Total Deductions ₹34,617.14, Net Revenue ₹8,71,514.86 — all correct. Flag restored to True after test.

**Expected on PB-KAL Apr-2026 post-deploy** (Sale ₹8,27,928, Comm ₹2,676.35):
- GST on Sale: ₹39,425.14 (eligible × 5/105)
- Total Deductions: **₹42,101.49**  
- Net Revenue: **₹7,85,826.51**

### [2026-04-30] Final GST consistency fix — WC Table + gst_applicable default
**User issue**: Total Deductions KPI showed only commissions (excl. GST), and the WC Standing table column showed old-formula GST (₹41,396 vs the correct ₹39,425.14 from GST Reconciliation page).

**Two root causes**:
1. **WC Standing table & Center Accounts summary** had two extra inline `eligible_base × rate` (exclusive) calculations on lines 236 + 582 of `center_accounts.py` that bypassed `utils/gst.py`. Both now use `carve_inclusive_gst`.
2. **`gst_applicable_india` defaulted to False** when the franchise document didn't have the field. This made `sales_gst = 0` for those franchises, so Total Deductions = commissions only and Net Revenue = Total Sales − commissions. Changed default to **True** (GST is mandatory in India above ₹40L turnover, which all our centers exceed).

**Verification on PB-HSR Feb-2026**:
- Center Accounts summary: GST ₹34,617.14, Deductions ₹34,617.14, Net Revenue ₹8,71,514.86 ✓
- WC Table standing rows: Nov-25 ₹38,643.24, Dec-25 ₹42,250.57, Jan-26 ₹41,595.90, **Feb-26 ₹34,617.14** ✓ (matches gst-liabilities exactly)
- KPI cards now correctly show Total Deductions = Commissions + GST
- Frontend `(commissions.total || 0) + (financial_summary.sales_gst || 0)` returns the right amount

After deploy + Recompute All on production GST Liabilities page, every screen will show identical GST numbers from the same shared utility.

### [2026-04-30] GST Liabilities — backfill + auto-recompute
**Issue**: User reported PB-KAL Apr 2026 GST page showing ₹41,396 on ₹8,27,928 eligible (old `× 0.05`), should be ₹39,425.14 (new `eligible − eligible/1.05`).

**Fix**:
- Endpoint `POST /api/gst/recompute` (existing) — now uses the centralized `compute_gst_from_rows` from `utils/gst.py` (inclusive formula). Was already wired but stored data was stale.
- **Backfilled 73 existing `gst_liabilities` rows** in preview DB to the new inclusive formula. Examples:
  - PB-HSR 2025-05: ₹57,328.35 → ₹54,598.43
  - PB-TH 2026-02: ₹31,531.10 → ₹30,029.62
  - PB-KN 2025-06: ₹54,919.25 → ₹52,304.05
- All 73 verified consistent: India centers @ 5% inclusive, PB-PERTH @ 10% inclusive.
- User's exact example confirmed: ₹8,27,928 × inclusive 5% = **₹39,425.14** ✓
- After deploying to production, click **"Recompute All"** on the GST Liabilities page once to update the production DB. Or call `POST /api/gst/recompute` (no body args) → recomputes everything from `daily_sales`.

### [2026-04-30] GST + Net Revenue formula — ONE source of truth, applied EVERYWHERE
**User instruction**: change should reflect every screen, every report, every place; come from common DB; no hardcoding.

**Single source of truth**: `backend/utils/gst.py` — three new helper functions:
- `gst_rate_for(country, center)` — returns 5% for India, 10% for Perth/Australia
- `carve_inclusive_gst(eligible_base, rate)` — `eligible − eligible / (1 + rate)` (INCLUSIVE basis)
- `compute_gst_from_rows(rows, ...)` and `compute_gst_from_totals(...)` — delegate to the carve formula
- `compute_net_revenue(total_sale, commissions, gst, expenses, country)` — single formula

**Refactored to use shared utility (NO duplicate inline math anywhere)**:
1. `backend/routes/sales_expenses.py::calculate_gst()` — now delegates to `compute_gst_from_totals`
2. `backend/routes/center_accounts.py::get_center_account_summary()` — uses `compute_gst_from_totals` + `compute_net_revenue`; `share_calculation.total_deductions` is now `commissions + sales_gst` for ALL countries (was per-country split before)
3. `backend/routes/ledgers.py::build_sales_register()`, `build_gst_summary()`, `build_monthly_pnl()` — all use `compute_gst_from_rows` / `carve_inclusive_gst`
4. `backend/utils/pdf_generator.py` (PIB report) — fallback now uses `carve_inclusive_gst`
5. `backend/routes/owner_reports.py::_compute_monthly_report()` — `pnl = total_sales − commissions − gst_amount` (was missing GST subtraction)
6. `backend/routes/mis_dashboard.py::get_mis_overview()` — `profit = sales − commissions − gst − expenses`; new fields `net_revenue` and `total_deductions` exposed in `summary` block

**Frontend** (`pages/CenterAccounts.jsx`): both KPI cards "Total Deductions" and "Total Deductions (incl. GST)" now compute `commissions + sales_gst` directly from the response.

**Backfilled** 1,918 historical `daily_sales.gst_amount` rows with the new inclusive formula so any reader (MIS daily/weekly/monthly summaries, sales-trends charts, PIB drivers, etc.) automatically picks up the corrected numbers.

**Cross-endpoint verification — PB-HSR Feb 2026** (real data):
| Endpoint | GST | Net Revenue | Total Deductions |
|---|---|---|---|
| `/api/center-accounts/summary` | 34,617.14 | 8,71,514.86 | 34,617.14 |
| `/api/mis/overview` | 34,617.14 | 8,71,514.86 | 34,617.14 |
| `/api/ledgers/gst` | 34,617.14 | — | — |
| `/api/ledgers/sales` | 34,617.17* | — | — |
| `/api/ledgers/pnl` | 34,617.14 | — | — |
*Per-day rounding (3 paise diff acceptable).

**Cross-center verification**:
- PB-HSR Dec 2025: Sales Rs 9,91,876 → Eligible 8,87,262 → GST Rs 42,250.57 (consistent across all 3 endpoints)
- PB-PERTH Feb 2026 (10%): Sales Rs 31,183 → Eligible 21,471 → GST Rs 1,951.94 (consistent across all 3 endpoints)

**Test updated**: `tests/test_gst_owner_pib.py::test_gst_math_india_5pct` switched from `eligible × 0.05` to `eligible − eligible / 1.05`.

### [2026-04-30] Net Revenue + GST formula correction (per user spec)
**User's request**:
> 1. Net Revenue = Total Sale − Total Deduction − Total GST on Sale (currently total_deductions only had commissions; GST not subtracted from net revenue)
> 2. GST = (Total Sale − Swiggy − Zomato − DoorDash) − (Eligible / 1.05)  [inclusive 5%]

**Fixes**:
1. **GST formula switched from EXCLUSIVE to INCLUSIVE** (5/105 carve-out): receipt prices in our system include GST, so the correct govt-payable is `eligible − eligible/1.05`. Earlier `eligible × 0.05` was over-stating GST by ~5% relative to receipt total.
   - File: `backend/routes/sales_expenses.py::calculate_gst()` and `backend/routes/center_accounts.py` (sales_gst_amount + gst_on_sales).
   - Same change applied for Australia/Perth at 1.10 divisor.
2. **India `net_revenue` now subtracts `gst_on_sales`** in addition to commissions: `net_revenue = total_sale − total_commission − gst_on_sales`. Revenue share split for India is computed on this updated base, so franchise-owner share is no longer paid on the GST portion (which is govt money, not franchise revenue).
3. **Frontend "Total Deductions" KPI card** now shows `commissions + sales_gst` (was just commissions). Sub-label added: "Commissions + GST on Sale".

**Verified on PB-HSR Feb 2026 (real data)**:
- Total Sales Rs 9,06,132 · Aggregator Rs 1,79,172 · Eligible Rs 7,26,960
- GST (5% inclusive carve-out) = **Rs 34,617.14** ✓
- Total Deductions = Commissions Rs 0 + GST Rs 34,617.14 = **Rs 34,617.14** ✓
- Net Revenue = 9,06,132 − 0 − 34,617.14 = **Rs 8,71,514.86** ✓

### [2026-04-30] Ledgers — Self-verification fixes (Payroll + Owner Ledger)
**Bugs found during FY2025-26 PB-HSR self-verification, all fixed:**

1. **Payroll Register showed 0 salary for all employees** — DB stores salary as camelCase fields (`salaryBase`, `currentSalary`, `bankName`, `beneAccNo`, `dateOfJoining`) but the ledger builder was looking up snake_case. Fixed `build_payroll_register` to try camelCase first, snake_case as fallback. Now correctly shows 16 employees × Rs 2.55 L total monthly salary for PB-HSR.

2. **Owner Ledger was empty** — Franchise lookup was using `centers_mapped` and `center` keys on the `franchises` collection, but the actual mapping is on the `centers` collection (`centers.franchise_code` → `franchises.franchise_code`). Also field name was `revenue_share_percentage` (not `revenue_share_percent`). Fixed both lookups. PB-HSR FY2025-26 Owner Ledger now shows 12 monthly revenue share entries → cumulative payable to HQ Rs 17,08,977.75.

3. **Owner Ledger had duplicate "Opening Balance" rows** — fixed to render once at the start of the period only (was showing for every month). Row count went from 26 → 14 with cleaner running balance.

4. **GST ITC pipeline verified end-to-end with real data**:
   - Tagged 15 real Feb-2026 PB-HSR expenses with appropriate GST rates (Rent/Packaging/Housekeeping/Print 18%, Cylinder 5%, etc.) — Rs 10,984.73 ITC claimable.
   - GST Summary correctly computes: Output GST 36,348 − Input GST (ITC) 10,985 = **Net Liability Rs 25,363** (vs. previously Rs 36,348 without ITC) → **30% reduction** in tax outflow.
   - FY2025-26 cumulative: Sales taxable Rs 1.32 Cr, Output GST Rs 5.69 L, ITC Rs 10,985 (only Feb tagged), Net Liability Rs 5.58 L.

### [2026-04-30] Expense GST / ITC tagging — for CA reconciliation
- **New optional fields on Expense Entry** form (India centers): Vendor Name, Vendor GSTIN, GST Rate (0/5/12/18/28), GST Amount (auto-derived).
- **Auto-derivation** (inclusive basis): `gst_amount = amount × gst_rate / (100 + gst_rate)`. E.g., Rs 1180 @ 18% → GST Rs 180, Taxable Rs 1000. Client preview shows the computed value live; backend re-validates and persists. Both `create_expense` and `update_expense` endpoints support the new fields.
- **GST Summary ledger now computes Net Liability correctly**: `Output GST − Input GST (ITC) = Net Liability`. Previously ITC was assumed zero. Verified via curl: a Rs 1180 expense @ 18% on PB-HSR Apr-26 → `input_gst=180, itc_taxable_value=1000` flowing into `/api/ledgers/gst`.
- **Expense Register ledger** now has 11 columns: Date, Vendor, Vendor GSTIN, Description, Category, Mode, Taxable Value, GST Rate %, GST Amount (ITC), Total, Bill — with grand totals row showing taxable base + total ITC.
- Files: `backend/routes/sales_expenses.py` (ExpenseCreate/Update + auto-derive), `backend/routes/ledgers.py` (build_expense_register + build_gst_summary + renderers), `frontend/src/components/ExpenseEntry.jsx` (new GST/Vendor row in Add form).

### [2026-04-30] Ledgers Tab — Live FY2025-26 Verified for PB-HSR
**A full Indian accounts-compliant ledger suite added under Center Accounts → Ledgers tab.**

**Access**: Super Admin + Admin + Accounts role (key 'accounts' / 'cfo' / 'finance'). Franchise Owner can download only their own Franchise Owner Ledger once Accounts releases it.

**10 ledger types generated** per Center by Month or FY (Apr–Mar), as PDF + Excel:
1. **Sales Register** — daily breakdown: direct, Swiggy, Zomato, DoorDash, Card, UPI/PhonePe, Online Other, Cash, Total, GST @5% (inclusive).
2. **Expense / Purchase Register** — date, description, category, payment mode, amount, bill-attached flag + category summary.
3. **Cash Book** — daily: opening + cash sales + receipts (bank→cash) − cash expenses − deposits to bank = closing petty cash.
4. **Bank Book** — uses `bank_transactions` if present; else derives deposits/withdrawals from daily_sales. Running balance.
5. **Commission / Aggregator Ledger** — month × platform: gross, GST deduction, other deduction, commission total, net.
6. **Loan / Counterparty Ledger** — per-counterparty (HQ / center) running ledger with principal, repayments, outstanding.
7. **Payroll Register** — employee-wise base salary, current salary, bank/IFSC/PAN.
8. **GST Summary** — Taxable value, Output GST, commission GST charged, net liability (ITC not auto-tagged — noted for CA).
9. **Monthly P&L** — month-wise gross sales, GST, ex-GST, expenses, commissions, PBT.
10. **Franchise Owner Ledger** — running current account with HQ (debit/credit/balance) built from revenue share %, MG, loans, loan repayments, commissions, WC top-ups, other income.

**CA Bundle ZIP** (`POST /api/ledgers/bundle`): single-click download containing
- `01_PDFs/` — all 10 ledgers as printable PDFs
- `02_Excel/` — same 10 as editable xlsx
- `03_Bills/` — every expense attachment for the period, organized by expense date
- `00_README.txt` — notes on GST basis, ITC handling, payroll
Verified: 67KB for a sparse month; 217KB for full FY with 22 files.

**Franchise Owner release flow** (like PIB visibility):
- Admin/Accounts clicks "Send to Owner" on the Owner Ledger card → `POST /api/ledgers/owner/release` marks `owner_report_visibility` collection with `report_type='owner_ledger'` + `released=true`.
- Franchise Owner Dashboard gets a new "My Ledgers" button (fuchsia) → modal lists all released months with PDF / Excel download buttons. Backend endpoint `POST /api/ledgers/owner/list`.
- Toggle to "Hide from Owner" also supported.

**Files added/modified**:
- NEW `backend/routes/ledgers.py` (~760 lines) — all builders + renderers + endpoints.
- NEW `frontend/src/components/LedgersTab.jsx` — tab component with period selector, 10 ledger cards, bundle button, owner release.
- `frontend/src/pages/CenterAccounts.jsx` — added `<BookOpen>` "Ledgers" tab trigger + content + `country` derived variable + `LedgersTab` import.
- `frontend/src/pages/FranchiseOwnerDashboard.jsx` — added "My Ledgers" button + modal + `/api/ledgers/owner/list` fetch + `Dialog` import.
- `backend/server.py` — registered ledgers router.

**Verified via curl**:
- `/api/ledgers/sales` JSON on PB-HSR Sep-2025: Total Rs 12.14 L (Swiggy 1.12L, Zomato 1.23L, Card 2.77L, UPI 6.61L, Cash 0.41L, GST 48,988).
- FY2025-26 Total: Rs 1.38 Cr.
- `/api/ledgers/owner` PB-HSR 2026-04: 3 rows, closing balance −80,000.
- Release → visibility → list flow works; `released_by` captures the Admin's name.
- Bundle ZIP HTTP 200 with all 22 files.

### [2026-04-30] Loan Entries — Counterparty Filter chips + Loan WC cap removal
- **New**: On the Loan Entries page, above the Loan History list, a "Filter by Counterparty" row of chips now appears whenever there are 2+ distinct counterparties. Each chip shows: counterparty label (e.g., `← HQ / External`, `← PB-HSR`, `→ PB-SN`), loan count, and outstanding amount. Clicking a chip filters the loan list to that counterparty only. "All" chip resets the filter. The filter resets automatically when switching centers.
- Taken loans are grouped by `source_center` (empty `source_center` → `HQ / External`). Given loans are grouped by `target_center`. Chip colors: blue for Taken, teal for Given, dark slate for the active chip.
- Test-ids: `loan-source-filter-block`, `loan-filter-chip-all`, `loan-filter-chip-{key}`.
- **Loan WC cap removed** (backend): `POST /api/loan-entries/create` no longer enforces `(new + outstanding) <= franchise.working_capital`. Verified via 3 consecutive loan creations (100k, 50k, 30k) all returning HTTP 200 where previously the 400 "exceeds available working capital" error would have been raised.

### [2026-04-30] PIB Sales Summary + Loan WC cap removal
- **PIB Report PDF — PhonePe / UPI row added**: `build_pib_pdf` in `utils/pdf_generator.py` Section 1 "SALES SUMMARY" now renders two additional rows between Card Sales and Cash Sales:
  - `PhonePe / UPI` (sourced from `summary.sales.bharat_pay`)
  - `Online Other` (sourced from `summary.sales.online_other`)
  Both show currency amount + `% of Total`. Verified via PyPDF2 extraction: all labels ("PhonePe", "UPI", "Online Other", "Card Sales", "Cash Sales", "Aggregator Sales") present in rendered PDF.
- **Loan Entries — Working Capital cap REMOVED**: `POST /api/loan-entries/create` in `routes/loan_entries.py` previously rejected loans where `(new amount + existing outstanding) > franchise.working_capital` with the error "Loan amount (X) plus existing outstanding (Y) exceeds available working capital (Z)". Per business rule, loans may be sourced from other centers or HQ, so amounts are no longer capped. The positive-amount check remains. `working_capital_at_time` is still stored on the loan doc for audit (snapshot of franchise WC at the time of entry).

### [2026-04-30] Expense Bill column always shows "None" — root-cause fix
- **Bug**: User attached a bill via the paperclip icon, but the row still showed a red "None" badge. No View/Download icon ever appeared, even for previously linked bills.
- **Root cause**: `db.expenses` documents have only `_id` (ObjectId) — they never had an `expense_id` string field, because `create_expense` set `record["expense_id"]` only in the response object, not in MongoDB. The upload endpoint then queried `db.expenses.update_one({"expense_id": expense_id}, ...)` which matched 0 documents, so `expenses.attachments` cache was never populated. The list endpoint was reading that empty cache → `attachment_status="missing"` → "None" badge.
- **Fix**:
  1. `/api/sales/expenses` list endpoint now queries `db.expense_attachments` directly by `expense_id` (which IS persisted on every attachment upload). This makes the source of truth the attachments collection, working for legacy + new + all centers.
  2. `create_expense` now persists `expense_id = str(_id)` on the expense document so all future operations match.
  3. Upload endpoint adds an ObjectId fallback (`{"_id": ObjectId(expense_id)}`) when `{"expense_id": ...}` doesn't match — handles legacy records.
  4. Delete attachment uses the same fallback and re-checks remaining count via the attachments collection.
  5. One-time backfill: 2,836 legacy expenses got `expense_id` field set to `str(_id)`.
- **Verified** end-to-end via Python script: expense + attachment record → list endpoint returns `attachment_status: "attached"`, `attachment_count: 1`, `direct_attachments: [{attachment_id, original_filename}]`. Frontend already renders the green Eye "View (1)" button when these fields are present.
- Files: `backend/routes/sales_expenses.py` (list + create), `backend/routes/expense_attachments.py` (upload + delete).

### [2026-04-29] Expense Bill / Invoice attachment is now clickable + Owner Dashboard parity check
- **Bill column on Expenses table is now clickable** — previously showed a static "None"/green/blue badge with no way to actually view the attached file. Now:
  - **Attached** (direct): emerald "View (N)" button → opens the attachment in a new tab via `viewAttachment(attachment_id)`. Multiple attachments open multiple tabs.
  - **Grp** (grouped invoice): blue "Grp (N)" button → opens the group's bill attachment(s); falls back to `handleViewGroup()` modal if attachments not present.
  - **None**: unchanged red outline (no file to show).
- **Backend** (`GET /api/sales/expenses`) now ships `direct_attachments` and `group_attachments` arrays on every expense row with `attachment_id`, `original_filename`, `file_size`, `content_type` so the UI can display file names and trigger downloads without a round-trip. Verified the new fields are always present (empty array when no attachment).
- Test-ids: `view-bill-{expense_id}`, `view-group-{expense_id}`.
- **Owner Dashboard data** — confirmed `FranchiseOwnerDashboard.jsx` calls `POST /mis/working-capital` which uses the same `calculate_working_capital_standing()` fn that was fixed for parity. Owner Dashboard, MIS Dashboard, Center Accounts Standing card, WC Breakdown Table, PIB and Owner Report PDFs therefore all share the same source of truth. Any remaining difference on the production site is because production hasn't been deployed with the recent WC parity fix yet — **click Deploy**.

### [2026-04-29] Employee Report — Salary details added + Excel export
- **PDF report** (`POST /api/employee_report`): added a new "Base Salary / Current Salary" row inside each employee card. Card height bumped 2.0 → 2.2 inch and pagination threshold raised 2.5 → 2.7 inch to keep layout clean. Currency prefix is `Rs.` for India centers and `$` for international. Verified via PyPDF2 — both `Base Salary` and `Current Salary` strings present in extracted text.
- **Excel report** (`POST /api/employee_report_excel`, NEW): generates a styled `.xlsx` with 17 columns — Center, Name, Designation, Gender, DoJ, Mobile, Email, **Base Salary**, **Current Salary**, Bank Name, Account No, IFSC, Aadhaar/TFN, PAN/Passport, Visa Type, Blood Group, Remarks. Indian-format number cells (`#,##0.00`) on salary columns, navy header row, frozen pane, alternating-row borders, and a bold summary row at the bottom showing total employee count + sum of Base/Current salaries. India vs International field handling (Aadhaar/PAN vs TFN/Passport+Visa) applied per-row by looking up the employee's center country.
- **Frontend**: new emerald "Employee Report (Excel)" button next to the existing purple "Employee Report (PDF)" button on `/employees`. Both share the same `centerFilter` and `reportLoading` state. Test-id: `export-report-excel-btn`.
- Verified via curl on PB-HSR: PDF 10 KB with salary lines; Excel 7 KB, 16 rows + summary row showing Total Employees: 16 and total Base Salary ₹2,55,000.

### [2026-04-28] Other Income / Loans Taken / Loans Given moved to a prominent always-visible spot
- User feedback: blocks were buried inside Sales Breakdown tab so they didn't appear next to the Working Capital Standing card on the WC tab where users actually look.
- **Fix**: rendered the same three blocks (Other Income with Add/Delete buttons, Loans Taken with source center + outstanding/repaid/status, Loans Given anonymised with outstanding/repaid/status) directly beneath the Working Capital Standing card on the Tax/WC tab. Test-ids: `ot-other-income-block`, `ot-loans-taken-block`, `ot-loans-given-block`, `add-other-income-btn-top`, `oi-row-top-{id}`, `oi-delete-top-{id}`.
- **MIS WC parity verified** by curl across PB-MGT, PB-PERTH, PB-HSR, PB-SN for Jan 2026 — Table opening/closing exactly equal Standing card opening/closing. Since MIS calls the same `calculate_working_capital_standing()` function, MIS Dashboard / Owner Reports / PIB / Sales Breakdown all produce identical numbers.

### [2026-04-27] Cash Inflows (Non-Operating) surfaced on PIB / MIS / Owner Reports
Closes the loop on Other Income visibility — same data, three audiences:
- **PIB Report PDF** (`utils/pdf_generator.py` `build_pib_pdf`): new section **"4B. Cash Inflows (Non-Operating) & Inter-Center Loans"** rendered between Financial Summary (4) and Operational Sustainability (5). Lists every Other Income row by category (loan_taken auto-rows + manual vendor_refund / franchisee_repayment / other), every Loan Taken with `From {source_center}` + Repaid/Outstanding/Status, and every Loan Given anonymised as `To Other Center` with the same Repaid/Outstanding/Status. Disclaimer at the top: "These rows do NOT affect Sales / P&L / Revenue Share / MG. Other Income adjusts next month's Opening Working Capital." Verified by extracting PB-PERTH 2026-01 PDF text (8 KB, 200 OK) — section + auto + manual + loan-taken row all present.
- **MIS Dashboard JSON** (`mis_dashboard.py /working-capital`): each center entry now carries `other_income_total`, `other_income_by_category`, `loans_taken_total`, `loans_taken_outstanding`, `loans_given_total`, `loans_given_outstanding`. Top-level totals also added (`total_other_income`, `total_loans_taken`, `total_loans_taken_outstanding`, `total_loans_given`, `total_loans_given_outstanding`).
- **MIS Dashboard UI** (`MISDashboard.jsx`): new emerald/amber/rose tri-card row "Cash Inflows (Non-Operating) & Inter-Center Loans" appearing under the WC headline cards, only when at least one total is > 0. Each KPI card shows total + outstanding sub-line. Test-ids: `cash-inflows-card`, `mis-other-income-card`, `mis-loans-taken-card`, `mis-loans-given-card`.
- **MIS PDF** (`mis_dashboard.py _build_mis_pdf` + `_build_franchise_pdf`): same tri-cell row inserted right after the WC headline cards in both the admin/CXO MIS PDF and the franchise-owner-scoped PDF. Brand-tinted backgrounds (emerald/amber/rose) with totals and outstanding sub-text.

### [2026-04-27] Other Income → Opening Balance + Loans Taken/Given Outstanding Visibility
Addresses 4 user requests on the Sales Breakdown UI:
- **Loan Taken now visible to borrower** — new "Loans Taken" memo block (amber) on Sales Breakdown showing the source center, principal, repaid, outstanding, and per-loan status badges (FULLY REPAID / PARTIAL / OUTSTANDING).
- **Outstanding / Repaid status on both sides** — both `loans_taken` (borrower view) and `loans_given` (lender view, anonymised) now expose `total`, `repaid`, `outstanding`, and per-row breakdown. Computed live from `loan_entries.amount - total_repaid`.
- **Other Income now flows into next-month Opening Balance** — changed from pure-memo to non-operating cash inflow. Aggregated per month via `get_other_income_by_month()` and added to the WC chain in BOTH `calculate_working_capital_standing` and `get_wc_table`: `closing = opening + pnl + wc_adj + topup + other_income`. P&L / Sales / Commission / MG / Revenue Share remain UNAFFECTED — Other Income only boosts WC closing so it carries to next month's opening balance. New `other_income` column in WC table rows.
  - Verified: PB-MGT Jan 2026 closing went from -252,502 → -244,725 after adding Rs 7,777 Other Income (delta = exactly +7,777, as expected).
- **Per-row Delete on Other Income** — admin/accountant-visible Trash icon on every manual row. Auto-generated rows show "linked to loan" hint and require deleting the source loan instead (cascade already in place).
- New backend endpoint `get_loans_taken_summary()` returns rows with `source_center` (visible to borrower) for transparent repayment tracking.

### [2026-04-27] Other Income (Memo-Only) + Loans Given memo on PIB / Sales Breakdown
- **New collection**: `other_income` with fields `income_id`, `center`, `date`, `month`, `amount`, `category` (`loan_taken | vendor_refund | franchisee_repayment | other`), `reason`, `linked_loan_id`, `auto_generated`, `created_by`, `created_at`.
- **New routes** at `/api/other-income/`:
  - `POST /create` — manual entry by Admin / Accountant. Accepts categories `vendor_refund | franchisee_repayment | other` only. `loan_taken` is reserved for auto-creation.
  - `POST /list` — by `center` (+ optional `month`). Franchise Owners restricted to own center.
  - `POST /delete/{income_id}` — deletes manual rows. Auto-generated rows protected (must delete via the source loan, or Super Admin override).
- **Auto-cascade with Loan Entries**:
  - When a TAKEN loan is created via `/api/loan-entries/create`, an auto Other Income row is inserted on the borrower center (`category=loan_taken`, `reason="Loan taken from {source_center}"`, `linked_loan_id=loan_id`, `auto_generated=true`).
  - When the loan is deleted (single or bulk), `cascade_delete_for_loan()` removes the linked auto Other Income rows automatically.
- **Memo-only semantics** — does NOT affect Total Sales / P&L / WC chain / MG / Revenue Share. Strictly informational for accounting visibility.
- **Center Accounts Summary endpoint** now returns:
  - `other_income`: `{total, by_category, rows}`
  - `loans_given`: `{total, count, rows}` — destination center name STRIPPED per requirement (rows show "Loan Given to Other Center" only).
- **Frontend Sales Breakdown tab** (`/center-accounts`):
  - New emerald "Other Income (Memo Only)" card with category badges, AUTO chip for auto-generated rows.
  - New rose "Loan Given to Other Center (Memo Only)" card sourced from `loans_given` (anonymised destination).
  - "Add Other Income" button (admin/accountant) opens a modal with date, amount, category dropdown (3 manual options), and reason — wired to `POST /create` and refreshes the summary on save.
- Verified end-to-end via curl on live preview:
  1. Manual `vendor_refund` Rs 2500 → appears in summary; reserved-category guard returns 400 for `loan_taken`.
  2. Loan create Rs 75,000 PB-HSR ← PB-SN → auto Other Income row appears on PB-HSR; PB-SN summary shows `loans_given.total = 75000` with sanitized "Loan Given to Other Center" reason (no destination).
  3. Loan delete → cascade removes the auto row, leaves the manual row untouched.

### [2026-04-27] WC Parity Fix — Standing Card / MIS / Owner Reports now match WC Breakdown table
- **Bug**: Working Capital Standing card on `/center-accounts` showed Opening WC of `Rs. -21,63,635.24` for PB-MGT March 2026 while the Month-by-Month WC Breakdown table (correct) showed `Rs. -16,97,058`. Same divergence appeared on MIS Dashboard, Franchise Owner Dashboard, and downloaded Owner Report PDFs.
- **Root cause**: `calculate_working_capital_standing` (powering Standing card / MIS / PDFs) used a different chain than `get_wc_table`:
  - Did NOT apply per-month `wc_adjustment` overrides.
  - Did NOT honor the franchise `effective_end_month` cap (so future months past the franchise contract were still chained).
  - Did NOT load `historical_pib` rows.
  - Used a non-linear "deficit-restore" branch that could drop surplus profit when WC ≥ Base.
  - Fell back to `base_wc` defaults whenever the requested month had no live data, instead of carrying the running chain forward.
- **Fix**: Rewrote `calculate_working_capital_standing` to chain identically to `get_wc_table`:
  - Same data sources: `daily_sales`, `expenses`, `monthly_commissions`, `commission_statements`, `historical_monthly_summary`, `historical_pib`, `wc_overrides`, `wc_month_overrides`, `wc_topups`.
  - Same linear formula: `closing_wc = opening_wc + (sale − expenses − commission) + wc_adj + topup`.
  - Same `effective_end_month` cap.
  - Added explicit fallback: if requested month has no data, opening = closing = current chain value (carries forward).
  - Kept `wc_used` / `wc_restored` semantics for the Protection-Mode badge logic.
- **Verified via curl**: Both endpoints now agree on Jan 2026 (open=100000 from base, close=-252502 after Jan loss) and on Mar 2026 (open=-252502 chained from Jan close — no data months in between).
- All consumers automatically benefit: `/center-accounts/summary`, MIS Dashboard (`mis_dashboard.py` line 1141), Owner Reports / PDF generator (`pdf_generator.py` line 456).

### [2026-04-27] Sales vs Expenses Charts (UI + PDF) on all 4 tabs
- **On-screen chart card** added on every tab (`/daily-text` Daily | Weekly | Monthly | Yearly).
  - Renders a Recharts dual-bar chart (`BarChart` + 2 `Bar`s — Sales in `#800020` maroon, Expenses in `#C9A227` gold) with X-axis labels rotated when bars > 8.
  - Sub-title shows "Total Sales: Rs. X · Total Expenses: Rs. Y" in the brand colors.
  - Daily tab shows a single comparison bar (sales vs sum of cash + online expenses for that day).
- **In-PDF chart**: matplotlib renders the same `chart_series` as a 9.5" × 3.5" PNG (150 dpi, brand maroon/gold bars, navy title, value labels above bars when ≤ 12 buckets) and embeds it via reportlab `Image` between the meta block and the WhatsApp body. PDF size grew from 189 KB → 239 KB (proves chart embedded).
- **Auto-bucketing rule** in `_build_chart_series`:
  - ≤ 31 days → per-day buckets (e.g. weekly = 7 bars, monthly = 28-31 bars).
  - > 31 days → bucket by `YYYY-MM` (e.g. yearly = 12 month bars).
- `data.total_expenses` now also returned from the aggregator for KPI display.
- Verified via curl: weekly returns `chart_series` len 7, monthly len 31, yearly len 12 (Apr 25 → Mar 26 with correct per-month rollup).

### [2026-04-27] Yearly Tab + Branded PDF Downloads + Franchise Owner Access (Sales Text Generator)
- **Yearly tab** added to `/daily-text` (now Daily | Weekly | Monthly | Yearly).
  - New endpoint `POST /api/daily-text/generate-yearly` with `year` (int).
  - **India FY logic**: `year=2026` → `FY 2026-27 (Apr 2026 - Mar 2027)`, aggregates ~365 days.
  - **International CY logic**: PB-PERTH `year=2026` → `CY 2026 (Jan-Dec 2026)`. Decision driven by `centers.is_india_center`.
  - Verified PB-HSR FY 2025-26 → 50 days of live data aggregated, top-6 expense categories computed; PB-PERTH header correctly labeled CY.
- **Branded PDF Downloads** for ALL 4 periods (Daily / Weekly / Monthly / Yearly).
  - New endpoint `POST /api/daily-text/download-pdf` with `period_type` + period-specific param (`date`, `week_date`, `month`, `year`).
  - PDF rendered with Purnabramha logo (`/app/backend/assets/pb_logo.png`), maroon brand title, navy sub-headline, gold underline, meta block (Center, Period, Generated, Generated by), and the WhatsApp-style summary in a navy-bordered light-gray box. Auto-generated footer disclaimer.
  - All 4 sample PDFs verified valid (`%PDF-1.4` magic bytes, ~190 KB each with logo embedded).
  - Reuses centralized formatting; no duplicated text logic.
- **Franchise Owner access** unlocked end-to-end:
  - Sidebar: `/daily-text` now visible to `role_key=franchise_owner` (override added in `hasAccess` + `hasCategoryAccess` for the `sales_cash` category).
  - Backend: existing access-check (own-center-only) already allowed FO to call generate endpoints; PDF endpoint inherits the same guard. Verified — FO `8888888888` (PB-HSR) gets 200 for own center and 403 for PB-SN.
  - Page renders read-only for FO (`canEdit` is `false`) — no Edit Values panel, but Copy Text & Download PDF buttons remain.
- Test-ids: `tab-yearly`, `yearly-center-select`, `yearly-input`, `yearly-generate-btn`, `yearly-refresh-btn`, `yearly-copy-btn`, `yearly-pdf-btn`, `yearly-text-preview`, `yearly-field-{key}`, `daily-pdf-btn`, `weekly-pdf-btn`, `monthly-pdf-btn`.

### [2026-04-27] Weekly Sales Text Generator (Tab on /daily-text)
- New backend endpoint `POST /api/daily-text/generate-weekly` aggregates Mon-Sun (snapped from any selected date) from `daily_sales` + `expenses` for a center.
  - Outputs the requested WhatsApp format: `Jai Hind Namskar` → ordinal date range (e.g. `20th April 2026 to 26th April 2026`) → `↪️ Total Sale / Card / Deposit / Withdrawl` → `DESCRIPTION Expenses` block (top 6 expense categories grouped from `expense_type` or `description`, lettered a/b/c…) → `↪️ Swiggy / Zomato / [Doordash if international] / Paytm / Bharat Pay / Cash Sale / Cash Expenses / Cash In Hand / Online Expenses / APC / Total No. Of Guest`.
  - Doordash line is **conditionally rendered** only when the center is international (`is_india_center === false` or non-India `country` field, e.g. PB-PERTH).
  - Cash In Hand = closing balance on the LAST day of the week with sales data (no double-counting). APC = total_sale / total_guests (weekly average).
  - Accepts `overrides` dict (any field, including `expense_categories: [{name, amount}]`) for manager edits before send.
- Frontend `/daily-text` page rebuilt as **Tabs (Daily | Weekly)**:
  - Weekly tab: Center select, "pick any date in week" picker (Mon-Sun snap explained inline), Generate / Refresh / Copy buttons.
  - Editable values panel with all 15 numeric fields + dynamic add/remove rows for expense categories.
  - Live regeneration of the WhatsApp preview as the manager edits (mirrors backend formatter exactly).
  - Test-ids: `tab-daily`, `tab-weekly`, `weekly-center-select`, `weekly-date`, `weekly-generate-btn`, `weekly-refresh-btn`, `weekly-copy-btn`, `weekly-text-preview`, `weekly-field-{key}`, `weekly-add-cat-btn`, `weekly-cat-row-{i}`, `weekly-cat-remove-{i}`.
- Verified via curl: PB-HSR Mar 2-8 2026 → 7 days aggregated correctly (Total Sale 15000, Card 4000, Swiggy/Zomato 1000 each, Bharat Pay 2000, Guests 100, APC 150, expense category "Other Expenses" 2500, Cash In Hand = 76355 from last-day closing). PB-PERTH preview correctly inserts "Total Doordash" line.

### [2026-04-25] Loan Entry Delete — Per-row + Bulk (center+month / all centers)
- **Per-row delete**: existing `POST /api/loan-entries/delete/{loan_id}` enhanced — now cascade-deletes the linked mirror entry (taken↔given pair) automatically. Added `force=true` flag to override the "has repayments" guard. Verified via curl: creating a TAKEN at PB-HSR mirrored to PB-SN, then deleting via the taken loan_id removed both entries (`{"deleted_loan_ids":["LOAN-PB-HSR-...","LOAN-PB-SN-...-G"]}`); subsequent `get` on the mirror returns 404.
- **Bulk delete**: new `POST /api/loan-entries/bulk-delete` (Super Admin only) — accepts `center` (or `"all"`), optional `month` (YYYY-MM, filters by `loan_date` regex), `force` and `confirm:true` (mandatory). Mirrors are also cascaded. Returns `deleted_count`, `skipped_count`, `skipped_loan_ids`. Validation: 400 for missing confirm, bad month format, missing center.
- **Frontend `/loan-entries`**:
  - Per-row red **Delete** button (super-admin only) with confirmation modal showing loan_id, type, amount, repaid total, and the linked mirror that will also be removed; force checkbox auto-shown when total_repaid > 0.
  - Header **Bulk Delete** button (super-admin only) → modal with Center scope (incl. "ALL CENTERS"), optional month picker, force toggle, and a live red summary banner showing the active scope before confirm.
  - Test-ids: `loan-bulk-delete-btn`, `loan-bulk-center-select`, `loan-bulk-month-input`, `loan-bulk-force`, `loan-bulk-delete-confirm-btn`, `loan-delete-btn-{loan_id}`, `loan-delete-confirm-btn`, `loan-delete-force`.

### [2026-04-24] Release-All + GST Reconciliation + Bank Reconciliation
Shipped 3 features requested from the backlog:

1. **Release All for Month bulk action** — new `POST /api/owner-reports/release-all` upserts visibility for ALL active centers in one call; `Release All` (green) + `Revoke All` (red) buttons in the Owner Reports header. Verified: 10 centers toggled in a single click.

2. **GST Reconciliation sub-page** — new `/gst-reconciliation` route (Admin/Accountant only) using the existing `/api/gst/*` endpoints. Table columns: Center, Month, Eligible Base, Rate, GST Amount, Status, Paid Date, Action. Filters: Center, Year, Status (all/paid/unpaid). "Recompute All" seed button + inline "Mark Paid"/"Unmark" actions per row. `mark-paid` / `unmark-paid` access broadened from Super-Admin-only to the `check_release_access()` group (SA + Admin + Accountant).

3. **Bank Reconciliation page** — new `/bank-reconciliation` route consuming the already-mature `bank_reconciliation.py` backend (21 pre-existing uploads visible). Upload form (Center/Month/CSV|XLSX), Recent Uploads table, 4-tab summary view (Unrecorded / Matched / Added / Ignored), Add-as-Expense dialog with expense-category dropdown + payment-mode picker, Ignore flow with reason capture.

All 3 pages wired into sidebar; test-ids present throughout (`or-release-all-btn`, `gr-*`, `br-*`).

### [2026-04-24] Added MG Report + Bank Statement on Owner Reports
- **MG Report** button — wires to existing `/api/center-accounts/export-mg-payout` (PDF format). Now gated by `enforce_owner_visibility()` so Franchise Owners only get released months.
- **Bank Statement** (new) — `POST /api/center-accounts/generate-bank-statement` builds a derived monthly cash-flow PDF via new `build_bank_statement_pdf()` in `utils/pdf_generator.py`. Sections: Opening Balance → Credits (daily sales by Cash/Online/Aggregator) → Debits (expenses + commissions + revenue-share payouts if paid) → Net Movement → Closing Balance. Includes disclaimer labelling it as a derived statement (not bank-feed reconciliation).
- Both new buttons added to the "Download Reports (PDF)" card on `/owner-reports` (test-ids: `or-dl-bank`, `or-dl-mg`). Total 5 reports now downloadable.
- Verified: Bank Statement 6/6 sections rendered; MG PDF valid; 403 gating confirmed for Franchise Owners.

### [2026-04-24] Download buttons for PIB / GST / Commission on Owner Reports
- Added **"Download Reports (PDF)"** card on `/owner-reports` (shown only when the month is visible) with 3 branded buttons: PIB Report, GST Summary, Commission Summary — each streams a Blob from the existing `/api/center-accounts/generate-*` endpoints.
- **Backend visibility gating added**: new `enforce_owner_visibility()` helper in `center_accounts.py` — Franchise Owners get **HTTP 403** "not yet released" on un-flagged months; Staff (SA/Admin/Accountant) bypass.
- Verified E2E: Franchise Owner `8888888888` blocked with 403 on un-released PB-HSR 2026-03 → released via SA → PDF download succeeds (6,884B valid PDF).
- Test-ids: `or-downloads`, `or-dl-pib`, `or-dl-gst`, `or-dl-comm`.

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
