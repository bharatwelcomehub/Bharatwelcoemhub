# Purnabramha IntraPB — Product Requirements Document

## Problem Statement
Internal management system for "Purnabramha," a restaurant franchise.

## What's Been Implemented (Latest)

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
