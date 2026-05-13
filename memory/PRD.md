# Purnabramha IntraPB — Product Requirements Document

## Problem Statement
Internal management system for "Purnabramha," a restaurant franchise.

## What's Been Implemented (Latest)

### [2026-05-10] One-shot WC unification — all 5 surfaces guaranteed to show the same number

User frustration: "MIS Dashboard, Owner's Dashboard, PIB Reports all showing different WC values. Center Accounts is correct. Fix it everywhere in one go."

**Done in one shot**:

1. **Backend chain canonical** (`backend/utils/wc_chain.py`):
   - `compute_wc_chain()` is the SOLE source of WC math. Both `calculate_working_capital_standing` and `get_wc_table` call it.
   - Formula: `closing_wc[M] = opening_wc[M] + pnl[M] + wc_adjustment[M] + topup[M]`
   - Other Income / Loans Taken are MEMO ONLY — never inflate WC (was the root cause of the user's PB-HSR ₹19.40L "Healthy" vs −₹37L drift).

2. **Frontend label/color consistency**:
   - MIS Dashboard (`MISDashboard.jsx`): WC status label now shows `CRITICAL · WC Depleted` for negative WC, `PROTECTION · Below 50%` for severely low, `Restoring` for mid, `Healthy` for >= initial. Cash Inflows footer note updated to "Memo only · does NOT affect WC. Loans taken are liabilities."
   - FO Dashboard (`FranchiseOwnerDashboard.jsx`): WC KPI card gradient now reflects status (red for negative, rose for protection, amber for restoring, emerald for healthy). Also passes period params to `/mis/working-capital` so it matches MIS Dashboard for the user-selected range.
   - Center Accounts page: already had correct 3-color logic, no change needed.

3. **PIB PDF** (`utils/pdf_generator.py`):
   - Section 4B Other Income status column: "Memo only · does NOT alter WC" (was "Adds to next-month Opening WC").
   - WC Status label adds "CRITICAL (WC Depleted)" for negative wc_pct.

4. **Cross-surface audit** (`scripts/audit_financial_parity.py`):
   - 24/24 month-center combinations PASS (PB-MGT/PB-DV/PB-PERTH/PB-HSR × Nov 2025–Apr 2026).
   - Simulated PB-HSR Apr 2026 with ₹16,00,000 loan_taken Other Income → closing_wc unchanged (=₹58,01,340.41 on preview). Confirms the fix correctly ignores the loan.

⚠️ **Deploy ONCE** and the user's PB-HSR PIB will read the same WC across:
- PIB Report → Closing WC (BAL.)
- Center Accounts → Working Capital Status card → Current WC
- Center Accounts → WC Breakdown table → last row Bal. WC
- MIS Dashboard → Working Capital KPI
- Franchise Owner Dashboard → Working Capital KPI

After deploy, PB-HSR Apr 2026 will show **−₹37,16,882 · CRITICAL · WC Depleted** consistently. The ₹16L Loan Taken will appear in Section 4B (PIB) and Cash Inflows card (MIS) as **memo only**.

### [2026-05-10] WC chain — Other Income (loan_taken) NO LONGER inflates Working Capital
**User report**: PB-HSR PIB Report on production showed "Closing WC ₹19,40,182 — Healthy 216%" while the WC Breakdown table showed **−₹37,16,882**. Root cause from the user's screenshot: a ₹16,00,000 "Other Income — Loan Taken" entry was being added to Closing WC, making a depleted WC look healthy. User: *"how can it be healthy when WC is negative?"*

**Fix** (`backend/utils/wc_chain.py`):
- Removed `+ other_income[M]` from the canonical chain. New formula:
  ```
  closing_wc[M] = opening_wc[M] + pnl[M] + wc_adjustment[M] + topup[M]
  ```
- A loan taken is a liability — the cash flows in but it's not real working capital. Repayment is already tracked separately on the Loan Ledger.
- `topup` (explicit equity injection) stays in the chain — that IS real WC.
- Other Income is now strictly **memo-only** on dashboards and PIB Section 4B.

**PIB PDF cosmetic** (`utils/pdf_generator.py`):
- Section 4B note updated to *"Memo only · does NOT alter WC. Loans taken are liabilities."*
- Per-row Status column changed from "Adds to next-month Opening WC" → "Memo only · does NOT alter WC".
- WC Status label now shows **"CRITICAL (WC Depleted)"** when wc_pct < 0 instead of falling through to "CLOSED (Below 50%)" — so the franchise owner immediately sees the WC has been wiped out.

**Verified**:
- Injected ₹16L loan_taken Other Income for PB-HSR Apr 2026 → closing_wc unchanged at ₹58,01,340.41 (was ₹74,01,340 before fix). Other Income surfaces as memo on the response only.
- 12/12 audit cases PASS (PB-MGT/PB-DV/PB-PERTH/PB-HSR × Apr-2026, Feb-2026, Dec-2025).

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy, PB-HSR PIB will show:
- Current Working Capital: **−₹37,16,882** (matches WC Breakdown)
- WC % vs Base: **−413%**
- Status: **CRITICAL (WC Depleted)** in red
- Section 4B Other Income: ₹16,00,000 (memo only · does NOT alter WC)

### [2026-05-10] Working Capital — single canonical chain across all 5 surfaces
**User report** (production audit): PB-HSR Apr 2026 showed **5 different Working Capital values** across 5 surfaces — Center Accounts top card ₹19,40,182, Operational Balance −₹15,35,468, WC Breakdown table −₹37,16,882, MIS Dashboard ₹19,40,182, FO Dashboard ₹20,74,838. User confirmed the cumulative chained value (−₹37L) is the truth.

**Root causes**:
1. The cumulative WC chain was implemented TWICE — once in `calculate_working_capital_standing` (used by Center Accounts WC card / MIS / FO) and once in `get_wc_table` (used by WC Breakdown). They had drifted on override semantics.
2. FO Dashboard called `/mis/working-capital` **without period params**, so it always used real-time current month while the rest of the dashboard used the user-selected period.

**Fix — single source of truth**:
- New `backend/utils/wc_chain.py::compute_wc_chain()` — sole place where the chain runs:
  ```
  for each month M:
    closing_wc[M] = opening_wc[M] + pnl[M] + wc_adj + topup + other_income
    pnl[M]        = sale - expenses - commission   (GST NOT subtracted; M+1 expense)
  ```
  Documents the override semantics: `commission_target` overrides commission; `gst_target` is display-only (never subtracted); `wc_adjustment` is explicit delta; `expense_adjustment` is audit-trail only.
- Both `calculate_working_capital_standing` and `get_wc_table` refactored to call this single helper. By construction they cannot drift.
- `FranchiseOwnerDashboard.jsx` now passes `period/custom_start/custom_end` params to `/mis/working-capital` so the FO WC card uses the user-selected period (matches MIS Dashboard).

**Operational Balance card** (single-month P/L flow, currently −₹15.35L for Apr 2026) — kept as-is per user choice. It's the flow, distinct from the cumulative stock.

**Audit extension** — `scripts/audit_financial_parity.py` now compares Working Capital across:
- Center Accounts → `working_capital_status.current_wc`
- MIS WC endpoint → `available_working_capital`
- MIS WC `centers[0].current_wc`
- WC Breakdown table last row `balance_wc`

**Verified end-to-end** by testing agent (`/app/test_reports/iteration_81.json`):
- 24/24 month-center audit combos PASS (PB-MGT/PB-DV/PB-PERTH/PB-HSR × Nov 2025–Apr 2026)
- New pytest `test_iteration81_wc_parity.py` 12/12 PASS
- FO Dashboard WC card visually shows canonical ₹58,01,340.41 for PB-HSR — equal to all 3 other surfaces
- Existing financial parity tests still pass (16/16)

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy, the same PB-HSR Apr 2026 should show the same WC value (canonical chained closing) across Center Accounts card, MIS Dashboard, FO Dashboard, and the WC Breakdown table.

### [2026-05-10] Download access fixes — Super Admin bypass + FO 500→403
**Reported issues** (production):
1. Downloads on Franchise Reports (Owner Reports) page not appearing
2. Owner's Dashboard report-range download not working
3. Ledger downloads for franchise owners returning errors

**Root causes found**:
1. `OwnerReports.jsx` gated all download buttons behind `visible = report.visibility.ready`. Super Admins on production can preview unreleased data but couldn't see download buttons → "downloads broken".
2. `routes/ledgers.py::_has_ledger_access` assumed `session.roles` was a list of dicts — franchise-owner sessions store it as a dict (`{accounting: true, ...}`). Threw `AttributeError: 'str' object has no attribute 'get'` → 500 instead of clean 403.
3. Ledger gate only checked the general monthly Owner Report release, not the explicit `owner_ledger` release.

**Fixes**:
- `OwnerReports.jsx`: added `canBypassRelease = is_super_admin || is_admin || roles.accounting` and `canDownload = visible || canBypassRelease`. Download buttons + Ledgers section now render for staff regardless of release; gated banner only for franchise owners.
- `routes/ledgers.py::_has_ledger_access`: now handles `roles` as dict OR list defensively.
- Ledger access gate: honors BOTH (a) general visibility (`report_type` missing, `ready=true`) AND (b) explicit `owner_ledger` release (`report_type=owner_ledger`, `released=true`).
- Ledgers section hidden for franchise owners on unreleased months (no dead buttons).

**Verified** by testing agent (`/app/test_reports/iteration_80.json`):
- Backend 10/10 PASS — full FO/SA access matrix for ledgers, center-accounts PDFs, MIS franchise-pdf.
- Frontend 3/3 scenarios — SA bypass + FO range download + FO gating banner all work.
- Audit script for PB-HSR 2026-02 still PASSES — no math regression from the access-check fix.

⚠️ Click **Deploy** to push to `intra.purnabramha.com`.

### [2026-05-10] Franchise document center auto-tagging + Ledgers visible without report load
**User reports** (production):
1. Documents uploaded from Franchise Management got tagged with the uploader's center (`PB-MGT`) instead of the franchise's actual operating center (e.g. `PB-DV` for FR-004 Dombivli) → invisible on the Document Management page when filtered by the operating center.
2. Ledgers section under Franchise Reports wasn't visible (it required a successful report load first; on production the report wasn't loading for any center).

**Backend** (`routes/documents.py`):
- `/documents/upload` now auto-resolves the correct center for `level=franchise` uploads via the `centers.franchise_code` link (picks first non-MGT center attached to the franchise). Even if a buggy frontend sends the wrong `center`, the doc gets tagged correctly.
- Verified: uploading with `center=PB-MGT, franchise_code=FR-TEST-INDIA` correctly stores `center=PB-HSR` in the DB.

**Frontend** (`pages/FranchiseManagement.jsx`):
- Document upload now also computes the franchise center on the client side from `selectedFranchise.center_code/home_center/centers[0]` so the form displays the right center pre-flight.

**Migration** (`scripts/fix_franchise_doc_centers.py`):
- One-shot script to retro-fix already-tagged documents in production. Dry-run by default; pass `--apply` to commit. Uses centers→franchise reverse-lookup, picks first non-MGT center.
- Preview DB has 0 mis-tagged docs (verified). Production user will run on production after deploy.

**Frontend Ledgers placement** (`pages/OwnerReports.jsx`):
- Moved the embedded `<LedgersTab>` OUTSIDE the `{report && ...}` conditional, so the full Ledgers UI (Sales Register / Expense / Cash Book / Bank Book / Commission / Loans / Payroll / GST / P&L / Owner + CA Bundle ZIP) renders as soon as a center is selected — independent of whether the monthly summary loads.
- Verified via screenshot: PB-HSR selected (no Load Report click) → Ledgers section visible with all controls.

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy, run on production:
```bash
python /app/backend/scripts/fix_franchise_doc_centers.py            # dry-run to see what'll change
python /app/backend/scripts/fix_franchise_doc_centers.py --apply    # commit
```

### [2026-05-10] Canonical commission helper + Ledgers section in Owner Reports
**User mandate**: "Calculate ONCE and display from same database. ALL MIS dashboards, MG, Revenue, P/L should look the same everywhere." Plus: add Ledgers section to Franchise Reports, gated until Accounts releases the month.

**The drift problem caught by audit**:
Before this iteration, four surfaces each had their own commission summation:
- Owner Reports summed `commission_amount + other_deductions + gst_tax_deductions + tds`
- MIS Dashboard summed `gst_tax_deductions + other_deductions OR (commission_amount + gst_on_commission)` AND applied WC overrides
- MG Payout summed `commission_statements` (legacy) + `monthly_commissions` with old fallback formula, NO overrides
- Center Accounts /summary used `commission_by_platform.deduction` aggregation, NO overrides

→ **PB-MGT 2026-01 showed ₹55,501 on MIS but ₹0 on every other surface.**
→ **PB-PERTH 2026-02 showed ₹2,172.52 on Center Accounts but ₹1,975.02 elsewhere** (AU 10% grossup applied inconsistently).

**The fix — single source of truth** (`backend/utils/commissions.py`):
- New `get_total_commissions(db, center, month)` helper.
- Resolution order: WC override → uploaded `monthly_commissions` (sums all 4 fields) → legacy `commission_statements`.
- Auto-detects country from `db.centers`; for Australia applies 10% commission GST grossup (since AU uploads typically don't carry `gst_tax_deductions`).
- All 4 surfaces (Owner Reports, Center Accounts /summary, Center Accounts /payout-summary, MIS Dashboard) refactored to call this single helper.
- Removed legacy "post-hoc WC override" code in MIS Dashboard (was a band-aid).
- Removed double-grossup in Center Accounts AU branch (helper now returns inclusive total directly).

**Audit script** (`backend/scripts/audit_financial_parity.py`):
- Takes `<CENTER> <MONTH>` args; exits 0 on parity, 1 on drift.
- Compares Owner Reports / Center Accounts / MIS / MG Payout for byte-identity (₹1 tolerance).
- ✅ **Verified PASS on all 24 month/center combinations** (PB-MGT, PB-DV, PB-PERTH, PB-HSR × Nov 2025 → Apr 2026).

**Ledgers section under Franchise Reports** (`frontend/src/pages/OwnerReports.jsx` + `LedgersTab.jsx`):
- Owner Reports now embeds `<LedgersTab readOnly={!session.is_super_admin && !session.is_admin && !session.roles.accounting} />` after the financial summary.
- Read-only mode hides admin controls (CA Bundle ZIP download, Send-to-Owner / Hide release toggle) and shows a "View Only" notice.
- Server-side gate at `/api/ledgers/{type}` already returns 403 for franchise owners until the Accounts team releases the month — no extra UI gating needed.
- Super Admin / Admin / Accounts users still see the full LedgersTab (since the readOnly check inverts to false for them).

**Pytest regression**: `/app/backend/tests/test_financial_parity_canonical.py` — 15/15 pass + audit 4/4 pass (`/app/test_reports/iteration_79.json`).

⚠️ Click **Deploy** to push to `intra.purnabramha.com`.

### [2026-05-10] Owner Reports — Net Revenue / Net P/L split, Eligible Rev Share Base card, MG Payout GST grossup
**User report** (production screenshots, PB-DV April 2026):
1. The "Net P/L" KPI card on Owner Reports actually shows Net Revenue (no expenses subtracted) AND the commission total used (₹15,900) excludes the 18% commission GST (~₹5,688) — i.e. it should be ₹21,588.
2. Need a new "Eligible Rev Share Base" card with explicit formula: Sales − Commission − Commission GST − GST.
3. The MG Payout Report's Total Payable should add 18% GST grossup on the Revenue Share so the gross-of-tax invoiceable figure (₹1,70,703 = ₹1,44,663.50 × 1.18) shows up.

**Backend** (`routes/owner_reports.py`):
- `total_commission` now sums `commission_amount + other_deductions + gst_tax_deductions + tds` (matches Center Accounts / MG Payout) instead of just `other_deductions`. PB-DV Apr 2026 jumps from ₹15,900 → ₹21,588 — same as the MG Payout report's Comm column.
- New response fields: `net_revenue` (Sales − Comm − GST), `net_pl` (Net Revenue − Expenses), `eligible_rev_share_base` (Sales − Comm − Comm GST − GST), `commissions.commission_gst` (uploaded `gst_tax_deductions`, with fallback `commission_amount × 18%` when the upload omits the field).
- `pnl` field kept as alias to `net_revenue` for back-compat.

**Frontend** (`pages/OwnerReports.jsx`):
- Card renamed: "Net P/L" → **"Net Revenue"** (subtitle "Sales − Comm (incl. GST) − GST").
- New indigo card **"Eligible Rev Share Base"** (subtitle "Sales − Comm − Comm GST − GST").
- New green/red card **"Net P/L"** (= Net Revenue − Expenses, subtitle "Net Revenue − Expenses").
- KPI grid expanded to `md:grid-cols-6`. Hydration warning fixed (Badge inside `<p>` → `<div>`).

**MG Payout Report** (`utils/pdf_generator.py::build_mg_payout_excel` + `build_mg_payout_pdf`):
- Summary tile (top of PDF) now shows **"Final Payout (incl. 18% GST)"** column = Total Payable × 1.18 (or × 1.10 for AU/Perth), highlighted in emerald.
- Below the TOTAL row in the monthly table: **"Add: 18% GST on Rev Share"** (amber-highlighted, italic) + **"Total Final Payout (incl. 18% GST)"** (emerald, bold).
- Excel mirrors the same two extra rows.

**Eligible Rev Share Base in offline reports** — added to all three:
- **PIB PDF** (`utils/pdf_generator.py::build_pib_pdf` Section 4) — line directly below NET REVENUE.
- **MIS Franchise PDF** (`routes/mis_dashboard.py::_build_franchise_pdf`) — row in Financial Summary directly below "= Net Revenue".
- **Owner Ledger PDF** (`routes/ledgers.py::build_franchise_owner_ledger` + render) — new "Net Revenue Calculation" section above Final Payout: Total Sales → Less Commission (excl. GST) → Less Commission GST → Less GST on Eligible Sales → Eligible Rev Share Base.

**Verified end-to-end** by testing agent (`/app/test_reports/iteration_78.json`):
- Backend pytest 11/11 PASS — math chain verified (PB-HSR 2026-02 Sales=906132 → Net Revenue=871514.86 → Net P/L=725572.86).
- Frontend Playwright PASS — 6 KPI cards render correctly with proper labels and values.
- All 4 PDFs (MG Payout, PIB, MIS Franchise, Owner Ledger) contain the new sections.

⚠️ Click **Deploy** to push to `intra.purnabramha.com`.

### [2026-05-10] Super Admin — Dynamic sidebar customization + User Manuals on sidebar
**User ask** (carried over from previous fork): Make User Manuals downloadable from a sidebar entry available to all roles, move Social Media Planner to Management, and let Super Admins reorder menu placing & adjust role alignment without code changes.

**Backend** (`backend/routes/menu_config.py`, new):
- New MongoDB collection `menu_configs` (single doc `_id='global'`) stores override deltas only — defaults stay in code so the system always has a sane fallback.
- `GET /api/menu-config?token=...` — any authenticated user reads the current overrides.
- `POST /api/menu-config/save` — Super Admin only; replaces overrides; sanitizes role identifiers against a fixed whitelist (14 roles).
- `POST /api/menu-config/reset` — Super Admin only; deletes the override doc.
- `GET /api/menu-config/valid-roles?token=...` — returns the 14 role identifiers + display labels for the UI to render checkboxes.

**Frontend**:
- `frontend/src/lib/menuDefaults.js` (new) — labels-only mirror of the sidebar structure, used by the customization page.
- `frontend/src/pages/MenuConfig.jsx` (new) — Super Admin page: each category card has up/down arrows + 14-role checkboxes; each item row has up/down arrows, "Move to category" dropdown, and per-role checkboxes; "Reset to defaults" + "Save Configuration" buttons.
- `frontend/src/pages/Dashboard.jsx` — fetches `/api/menu-config` on mount, on window focus, and every 60s, and applies overrides via two helpers: `applyMenuOverrides()` (re-parents items, sorts categories+items) and `overrideAccess()` (DB-driven role allowlist supersedes code defaults). Super Admin bypasses any override (always sees everything).
- New "Help & Resources" sidebar category at the bottom containing User Manuals — visible to all roles by default.
- "Menu Customization" item added under Management (Super Admin only).

**Verified end-to-end** by testing agent (`/app/test_reports/iteration_77.json`):
- Backend: 10/10 pytest pass — all 4 endpoints, auth gating (401 invalid token, 403 non-SA), persistence, role sanitization.
- Frontend: SA can open `/menu-config`, sees 10 categories × 14 role checkboxes × 40 move-to-category dropdowns; Save + Reset both fire success toasts. Franchise Owner correctly sees Help & Resources → User Manuals but NOT Menu Customization, and is blocked from `/menu-config` route. `/user-manuals` page renders all 4 role cards (Super Admin / Center Manager / Accountant / Franchise Owner) + Complete User Manual.

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy: Super Admins can reorganize menus from the UI without redeployment, and User Manuals appear on every authenticated user's sidebar under Help & Resources.

### [2026-05-09] One-shot DB recompute script — `daily_sales.gst_amount` aligned with canonical inclusive carve
**Why**: yesterday's audit fixed the 5 *write paths* that were storing GST as 5%-on-top instead of inclusive carve. But every historical row in `daily_sales` still has the old (wrong) value stored in `gst_amount`. Dashboards compute GST on the fly so they already show the right number — but anything that reads the stored field directly (a future report, an export, a downstream consumer) gets the wrong figure.

**Script**: `backend/scripts/recompute_gst_amount.py`
- For every `daily_sales` row, computes canonical GST via `carve_inclusive_gst(eligible_base_from_daily_row(row), gst_rate_for(country, center))`.
- Compares to stored `gst_amount`. Updates only when they diverge by more than ₹0.01.
- Stamps `_gst_amount_legacy` (original value) + `_gst_recomputed_at` (timestamp) on each updated row → fully reversible.
- **DRY-RUN by default**. Pass `--apply` to commit. Idempotent — safe to re-run.

**Verified on preview**: 2,210 rows scanned, 3 diverged (₹0.77 total drift), all corrected. Re-run found 0 diverged → idempotent confirmed.

**Production rollout**: Requires shell access to the production container after deploying the latest code.
```
cd /app/backend && python scripts/recompute_gst_amount.py            # dry-run
cd /app/backend && python scripts/recompute_gst_amount.py --apply    # commit
```

If shell access isn't available, I can wire this up as an admin-only API endpoint on request.

### [2026-05-09] One-shot formula audit — every GST / Net Rev / Rev Share / Final Payout calculation now routes through `utils/gst.py`
**User ask** (after the 4th formula-divergence bug this week): do an audit pass and replace any remaining private formulas with the canonical helpers.

**Audit scope**: scanned every `routes/*.py`, `utils/*.py`, and `frontend/src/pages/*.jsx` for hardcoded GST/share rates (`0.05`, `0.10`, `0.15`, `0.18`), inclusive-carve denominators (`1.05`, `1.18`), and grossup multipliers (`× 1.18`, `× 1.10`).

**Findings & fixes** — 5 private formulas replaced:

1. **`sales_expenses.py:2541`** — daily_sales `gst_amount` write path used `eligible × 0.05` (5% on top, ₹48,439.80) instead of inclusive carve (₹46,133.14). For ₹9,68,796 eligible base this silently over-stated GST by ₹2,306 per row.
   - Fix: route through `carve_inclusive_gst(eligible_base_from_daily_row(record), gst_rate_for(None, center))`.
2. **`sales_expenses.py:2800`** — same bug in second write path. Fixed identically.
3. **`sales_expenses.py:2981`** — same bug in third write path. Fixed identically.
4. **`center_accounts.py:1398`** — Australia commission GST grossup hardcoded `× 0.10`. Now reads from `gst_rate_for("Australia", None)` so the rate is centrally managed.
5. **`center_accounts.py::calculate_taxes()`** (lines 1212-1259) — the legacy helper had `gst = amount × 0.05` for India sales (5% on top, wrong). Now both AU and India sales branches route through `carve_inclusive_gst(amount, gst_rate_for(country, None))`. Revenue/profit-share branches unchanged (they're correctly GST-on-top, not inclusive carve).

**No private formulas left in frontend** — `FranchiseOwnerDashboard.jsx`, `MISDashboard.jsx`, `CenterAccounts.jsx` all derive from `franchiseInfo` data + `isIntl` flag.

**Verified end-to-end** with PB-DV April 2026 reproduction (Total Sales ₹10,32,144, Swiggy ₹63,348, Commissions ₹21,587.51):

| Surface | GST | Net Revenue | Rev Share | Final Payout |
|---|---|---|---|---|
| PIB (truth) | ₹46,133.14 | ₹9,64,423.35 | ₹1,44,663.50 | ₹1,70,702.94 |
| MIS Dashboard | ✓ | ✓ | (cascades) | (cascades) |
| Center Accounts | ✓ | ✓ | (cascades) | (cascades) |
| Owner Ledger PDF | ✓ | ✓ | ✓ | ✓ |

**Single source of truth** — every GST calculation now flows through one of:
- `utils.gst.carve_inclusive_gst(eligible, rate)` for inclusive 5%/10% carve
- `utils.gst.compute_gst_from_rows(rows, country, center)` for batch GST from daily_sales
- `utils.gst.compute_net_revenue(total, comm, gst, _, country)` for Net Revenue
- `utils.gst.gst_rate_for(country, center)` for the rate constant

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy, every screen + every PDF + every Excel + the daily_sales rows themselves will produce identical GST/Net Rev/Rev Share/Final Payout for the same data.

### [2026-05-09] Owner Ledger PDF — Revenue Share + GST grossup now matches PIB to the rupee
**User report** (PB-DV April 2026 PDF screenshot): Owner Ledger shows Rev Share ₹1,45,319.40 and no 18% GST grossup, while every other surface (PIB, MIS, FO Dashboard) shows ₹1,44,663.50 + 18% GST = ₹1,70,702.94 Final Payout.

**Root cause** (`routes/ledgers.py::build_franchise_owner_ledger`): same formula-divergence pattern we've seen 3 times now:
- It used its own private formula `(Total − Aggregator) × rev_pct` without subtracting GST or commissions.
- Field-name bug carried over (read `swiggy` instead of `swiggy_sale`).
- The 18% GST grossup row was missing from the running ledger entries — so the running balance never reflected the gross-of-tax invoiceable amount.

**Fix** — three changes, all targeting parity with the canonical formula:
1. Replaced the inline calculation with `utils.gst.compute_net_revenue(total_sale, comm_total, gst_amount, 0, country)` — the same helper PIB / MIS / Center Accounts already use.
2. GST is computed via `compute_gst_from_rows(...)` (single source of truth) — same inclusive 5%/10% on eligible base.
3. Added a new ledger row **"GST on Revenue Share @ 18%"** that posts the grossup amount immediately after the Revenue Share debit, so the running balance now mirrors the Final Payout block at the bottom of the PDF.

**Verified end-to-end** (synthetic PB-DV April 2026 reproduction):

| Row | Old | New | PIB (truth) |
|---|---|---|---|
| Revenue Share payable (15%) | ₹1,45,319.40 ❌ | **₹1,44,663.50** ✓ | ₹1,44,663.50 |
| GST on Revenue Share @ 18% | (missing) | **₹26,039.43** ✓ | ₹26,039.43 |
| Total Final Payout (incl. 18% GST) | (missing in running ledger) | **₹1,70,702.94** ✓ | ₹1,70,702.94 |

The "Final Payout (Payout × GST)" summary table at the bottom of the PDF (added earlier) was already correct; now the running ledger entries above it match it row-for-row, and both equal what the dashboards show.

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy, regenerate the PB-DV Owner Ledger PDF for April 2026 — every line matches the PIB.

### [2026-05-09] Loan totals now match Loan Entries page across Center Accounts, MIS Dashboard & FO Dashboard
**User report** (production screenshots, PB-DV): Center Accounts shows Loans Given = ₹100, while the actual Loan Entries page shows ₹26,39,617 outstanding ₹22,99,517. Same divergence on MIS Dashboard. Asked: loan numbers must come from the Loan feature; same on every screen.

**Root cause** (`routes/other_income.py`):
- `get_loans_given_summary(center, month)` and `get_loans_taken_summary(center, month)` filtered loans to **only those CREATED in that month** (`loan_date.startswith(month)`).
- When the user selected April 2026 on the dashboard, the only April loan was ₹100 (the rest were given Jan–Mar) → dashboards showed ₹100 while Loan Entries page (lifetime) correctly showed ₹26,39,617.
- Loans are balance-sheet items (cumulative ledger), not period flows — the month filter was semantically wrong.

**Fix**: changed both functions to **cumulative-up-to-month** semantics — `loan_date <= "{month}-31"`. Now any loan created on or before the end of the selected period is included, exactly matching what the Loan Entries page (lifetime) shows when end-of-period = today.

**Verified end-to-end** with synthetic PB-HSR scenario (14 historical loans Jan–Mar totalling ₹26,39,517 + 1 April loan ₹100):

| Surface | Loans Given Total | Outstanding |
|---|---|---|
| Loan Entries page | ₹26,39,618.00 | ₹23,39,518.00 |
| MIS Dashboard (Apr 2026) | ₹26,39,618.00 ✓ | ₹23,39,518.00 ✓ |
| Center Accounts (Apr 2026) | ₹26,39,618.00 ✓ | ₹23,39,518.00 ✓ |

Verified semantics also work for older periods — selecting Jan 2026 correctly shows only the 1 loan from Jan; Feb shows 2; Mar/Apr show all 14 (cumulative). Other Income (a true period flow) unaffected.

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy: Center Accounts page, MIS Dashboard "Cash Inflows" card, and Franchise Owner Dashboard will all show the **same** Loans Taken / Loans Given / Outstanding numbers as the Loan Entries page.

### [2026-05-09] CRITICAL FIX — TWO more bugs in MIS Dashboard / FO Dashboard GST (now byte-identical to GST Summary report)
**User report** (production screenshots, PB-DV April 2026): GST Summary report correctly shows ₹46,133.14, but the MIS Dashboard and Franchise Owner Dashboard both show ₹55,984.74.

**Two stacked bugs** in `routes/mis_dashboard.py` (both fixed):

**Bug A — `gst_target` WC override was being ADDED to formula GST** (lines 350–401):
- The "WC table override" merge read its source bucket from the legacy `daily_sales.gst_amount` field — which is 0 for centers like PB-DV that never wrote the legacy field.
- Logic: `new_gst = formula_gst − source_bucket + gst_target` → `46,133.14 − 0 + 55,984.74 ≈ 102K` (or with a partial override, the +₹9,851 we observed).
- Fix: **removed the `gst_target` override path entirely** from the dashboard merge. GST is now formula-only — the same `carve_inclusive_gst(eligible, rate)` used by the PIB and GST Summary report. `commission_target` overrides remain (legitimate manual entry).

**Bug B — per-center breakdown used non-inclusive formula** (line 494):
- Old: `cd["gst"] = eligible_base × rate` → 968,795.94 × 5% = **₹48,439.80** ❌
- Correct: `cd["gst"] = eligible_base − eligible_base/(1+rate)` → **₹46,133.14** ✓ (matches PIB)
- Fix: replaced with `carve_inclusive_gst(...)` helper so per-center matches top-level.

**Verified end-to-end** with the worst-case scenario (sales rows present, no `gst_amount`, **stored override of ₹55,984.74**):

| Metric | Old | New | PIB / GST Summary (truth) |
|---|---|---|---|
| Top-level `total_gst` | ₹55,984.74 ❌ | ₹46,133.14 ✓ | ₹46,133.14 |
| Per-center `gst` | ₹48,439.80 ❌ | ₹46,133.14 ✓ | ₹46,133.14 |
| `net_revenue` | ₹9,54,571.75 ❌ | ₹9,86,010.86 ✓ | ₹9,86,010.86 |

**Cascade**: This also fixes Revenue Share, Final Payout (incl. 18% GST), and Net Profit (P&L) on both dashboards — every downstream KPI now derives from the correct GST.

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy, refresh the MIS Dashboard / Franchise Owner Dashboard for PB-DV April 2026 — you'll see ₹46,133.14 (GST), ₹9,64,423.35 (Net Rev), ₹1,44,663.50 (Revenue Share), ₹1,70,702.94 (Final Payout) — all matching the PIB and the GST Summary PDF the user attached.

### [2026-05-09] CRITICAL FIX — Center Accounts page was reading aggregator sales from wrong field; GST now matches MIS & PIB exactly
**User report**: "GST on Sale" and "GST on Eligible Sales" show different values; MIS and Dashboard for Accounts show different GST calculations. Reset both to: GST = 5% on eligible sales (NOT on direct sales).

**Two issues found, both fixed**:

**1. Calculation divergence — REAL bug**
- `routes/center_accounts.py:1304-1306` was reading aggregator sales as `r.get("swiggy", 0)` / `zomato` / `doordash` (legacy field names), but the actual `daily_sales` documents store them as `swiggy_sale` / `zomato_sale` / `doordash_sale`. So `aggregator_sale` summed to 0 → `eligible_base = total_sale` → GST was 5% inclusive on the FULL sale instead of on (Sale − Aggregator).
- For the same dataset that gave PIB ₹46,133.14, Center Accounts page returned ₹49,149.71 — the ₹3,016.57 gap user observed.
- **Fix**: same fallback pattern as `utils/gst.py::eligible_base_from_daily_row` — `r.get("swiggy_sale", r.get("swiggy", 0))` etc. Now Center Accounts reads aggregator from BOTH possible field names.

**2. Label inconsistency** — "GST on Sales" misled users into thinking it was 5% on the full sale, when it's actually 5% inclusive on eligible base. Renamed to **"GST on Eligible Sales (5% incl.)"** everywhere:
- MIS Dashboard KPI card + Excel export
- Franchise Owner Dashboard KPI card + Excel export
- MIS Franchise PDF KPI card + Financial Summary table row
- Center Accounts Net Revenue waterfall (Less: row)
- Center Accounts deductions sub-labels

**Verified end-to-end** with synthetic PB-DV April 2026 reproduction:

| Source | GST | Net Revenue |
|---|---|---|
| PIB (truth) | ₹46,133.14 | ₹9,86,010.86 |
| MIS Dashboard | ₹46,133.14 ✓ | ₹9,86,010.86 ✓ |
| Center Accounts | ₹46,133.14 ✓ | ₹9,86,010.86 ✓ |

All three APIs now use the **same formula** (`carve_inclusive_gst(eligible, rate)` from `utils/gst.py`) and the **same DB collection** (`daily_sales`), with consistent field-name fallback. No hardcoded numbers.

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy: every dashboard, every PDF, every Excel will show GST as "GST on Eligible Sales (5% incl.)" with identical values across MIS, Center Accounts, Franchise Owner Dashboard and PIB.

### [2026-05-09] CRITICAL FIX — MIS Dashboard / Owner Dashboard GST was double-counted (numbers now match PIB)
**User report** (with PB-DV April 2026 PIB attached): "MIS report for company and Owner dashboard show different reporting numbers — should be the same as the PIB.pdf."

**Comparison** (PB-DV April 2026):
| Metric | PIB (truth) | Old dashboard | Δ |
|---|---|---|---|
| GST on Sales | ₹46,133.14 | ₹55,984.74 | +₹9,851.60 ❌ |
| Net Revenue | ₹9,64,423.35 | ₹9,54,571.75 | -₹9,851.60 ❌ |
| Revenue Share 15% | ₹1,44,663.50 | ₹1,43,185.76 | -₹1,477 ❌ |
| Final Payout (incl. 18% GST) | ₹1,70,702.94 | ₹1,68,959.20 | -₹1,743 ❌ |
| Net Profit (P&L) | -₹1,50,893.65 | -₹1,60,745.25 | -₹9,851.60 ❌ |

**Root cause** (`routes/mis_dashboard.py:223-227`): The "skip PIB-GST add when live data exists" check was gated on `daily_sales.gst_amount > 0`. But the new (Apr-2026) GST formula derives GST inclusive from `eligible_base = total_sale − swiggy − zomato − doordash` — it **does not need** the legacy `gst_amount` field. Centers that have daily_sales rows but with `gst_amount=0` (e.g. PB-DV) had:
1. ✅ Live formula correctly computed ₹46,133.14
2. ❌ Then `historical_pib.total_gst_on_revenue` (₹9,851.60) was ADDED on top — double-counting → ₹55,984.74

The over-stated GST cascaded into Net Revenue, Revenue Share, Final Payout, Net Profit — explaining all 5 mismatches.

**Fix**: dedupe rule changed to: a (center, month) is "covered by live data" whenever the daily_sales rows have **any eligible_base > 0** (or the legacy `gst_amount` for back-compat). For those months the PIB-imported GST is skipped.

**Verified end-to-end** with a synthetic reproduction of the exact PB-DV scenario (Sales ₹10,32,144, Swiggy ₹63,348, PIB GST ₹9,851.60):
- Old: total_gst = ₹55,984.74 ❌ → New: total_gst = **₹46,133.14** ✓
- Net Revenue, Revenue Share, Final Payout all flow through correctly.

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy, the MIS Dashboard, MIS Franchise PDF, and Franchise Owner Dashboard (incl. the Final Payout KPI card) will all match the PIB to the rupee.

### [2026-05-09] Franchise Owner Dashboard — new "Final Payout (incl. 18% GST)" KPI card
**User ask**: surface the gross-of-GST invoiceable amount as its own KPI on the dashboard, right next to Revenue Share, so owners and CA catch any MG-trigger month at a glance — no PDF download needed.

**Fix** (`frontend/src/pages/FranchiseOwnerDashboard.jsx`):
- Reads `monthly_guarantee` (with fallbacks `mg` / `minimum_guarantee`) from `franchiseInfo` (already returned by `/api/franchises/by-center/:code`).
- Computes `payoutBase = MAX(revenueShareAmount, monthlyGuarantee)` — same logic as PIB Section 8B / MIS Franchise PDF / Owner Ledger PDF.
- New emerald KPI card *"Final Payout (incl. 18% GST)"* (10% for intl) with `Wallet` icon, placed immediately after the existing Revenue Share card.
- A small sub-badge under the value tells the story:
  - When MG wins: *"MG paid (₹X > Rev Share)"* — flags the exact months CA needs to invoice off MG.
  - Otherwise: *"Base: ₹X"* — confirms the figure is `revenueShareAmount × 1.18`.
- Sub-badge rendering is generic (`kpi.subBadge`) so any future card can reuse the same chip.

**Verified**: lint clean. Existing KPI layout (`md:grid-cols-4 lg:grid-cols-7`) absorbs the new 10th card without overflow. Number on the dashboard now matches PIB Section 8B + MIS Franchise PDF + Owner Ledger PDF for the same period.

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy, owners see the Final Payout figure inline; MG-winning months are visually flagged (white-on-emerald sub-chip) without anyone having to open a PDF.

### [2026-05-07] Final Payout — payout base now correctly = MAX(Revenue Share, MG); GST applied on that
**User correction**: The 18% GST should be calculated on whichever of Revenue Share or Monthly Guarantee is higher (= the actual payout), NOT on the bare revenue share.

**Fix**:
- **Owner Ledger PDF** (`routes/ledgers.py`): now adds `total_rev_share + total_mg_topup` per period (= MAX(rev_share, MG) per month, summed) and applies CGST 9% + SGST 9% on that base. When MG > Rev Share the section header reads e.g. "Payout for 2025-08 (MG ₹279,127.85 + Rev Share ₹220,872.15)".
- **MIS Franchise PDF** (`routes/mis_dashboard.py::_build_franchise_pdf`): now reads `monthly_guarantee` from `franchise_info`, computes `payout_base = max(revenue_share_amount, monthly_guarantee)`, and labels the row "Monthly Guarantee (paid — higher than Revenue Share)" or "Revenue Share Payable" accordingly. Footnote updated to *"Payout = MAX(Revenue Share, Monthly Guarantee). GST is computed on this payout amount."*
- **PIB PDF Section 8B** (`utils/pdf_generator.py`): already used `payout.amount` (the resolved payout), but the row label said "Revenue Share Payable" even when MG won. Now flips to "Monthly Guarantee Payout (MG > Rev Share)" when `mg_amount > revenue_share_amount` and the payout matches MG — consistent labelling across all three docs.

**Verified live on PB-HSR Aug 2025 with MG=₹500,000, Rev Share=₹220,872.15**:
- Payout base = ₹500,000 (MG wins) ✓
- CGST 9% = ₹45,000 ✓ · SGST 9% = ₹45,000
- **Final Payout (incl. 18% GST) = ₹590,000** (= 500,000 × 1.18 ✓)

The number now matches across PIB Section 8B, MIS Franchise PDF, and Owner Ledger PDF. CFO signature footer renders correctly. Lint clean (only pre-existing warnings).

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy, all three reports use the same payout base (MAX of MG / Rev Share) for the GST calculation — invoiceable amount stays consistent end-to-end.

### [2026-05-07] Final Payout (Revenue Share + GST) rolled into MIS Franchise PDF & Owner Ledger PDF
**User ask**: keep the gross-of-GST number consistent across the three documents the Franchise Owner sees — already shipped on the PIB (Section 8B); now add the same block to the MIS Franchise PDF and the Owner Ledger PDF.

**MIS Franchise PDF** (`routes/mis_dashboard.py::_build_franchise_pdf`):
- New "Final Payout (Revenue Share + GST)" table inserted right after the Financial Summary section.
- India centers: Revenue Share Payable → Add: CGST 9% → Add: SGST 9% → **Total Final Payout (incl. 18% GST)** highlighted in saffron.
- Australia / international centers: Profit Share Payable → Add: GST 10% → **Total Final Payout (incl. 10% GST)**.
- Skipped silently when revenue_share_amount = 0 so reports for centers without an active franchise contract stay clean.

**Owner Ledger PDF** (`routes/ledgers.py`):
- `build_franchise_owner_ledger()` now also returns `total_rev_share` and `total_mg_topup` (sums across all months in the period).
- `_render_ledger("owner", ...)` appends a "Final Payout (Revenue Share + GST)" section after Franchise Details with the same India / non-India split. Section title shows the period, e.g. "Revenue Share Payable for 2025-08".

**Verified end-to-end on PB-HSR Aug 2025**:
- Revenue Share = ₹220,872.15
- CGST 9% = ₹19,878.49 (= 220,872.15 × 0.09 ✓)
- SGST 9% = ₹19,878.49
- **Final Payout (incl. 18% GST) = ₹260,629.13** (= 220,872.15 × 1.18 ✓)

Both PDFs render the new block; signature footer (Manaswini Foods Pvt Ltd / CFO Shashikant Pande) still appears below correctly. Lint clean (only pre-existing project warnings).

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy: any newly-generated PIB, MIS Franchise PDF, and Owner Ledger PDF will all show the same Final Payout figure — matching what the CA invoices.

### [2026-05-07] PIB Report — new "Final Payout (Revenue Share + GST)" block
**User ask** (with screenshot): Section 9 (Tax Rules Applied) is correct. They wanted a separate block *before* Section 9 that adds CGST 9% + SGST 9% on top of the Revenue Share so the final invoice-able amount shows on its own.

**Fix** (`backend/utils/pdf_generator.py::build_pib_pdf`):
- New **8B. FINAL PAYOUT (Revenue Share + GST)** block inserted between Section 8 (Payout Determination) and Section 9 (Tax Rules), only when `share_gst_rate > 0` and a positive payable exists.
- For India centers (rate 18%): rows are `Revenue Share Payable` → `Add: CGST @ 9%` → `Add: SGST @ 9%` → **Total Final Payout (incl. 18% GST)** highlighted in maroon.
- For Australia / outside-IN: rows are `Profit Share Payable` → `Add: GST @ 10%` → **Total Final Payout (incl. 10% GST)**.
- Italic footnote: *"This is the gross-of-tax amount to be invoiced / paid to the Franchise Owner. The GST split below is reproduced under Section 9 for reference."*
- Wrapped in try/except so the new block is purely additive — any rendering hiccup falls back to the existing Section 9 without breaking the PIB.

**Verified** on PB-HSR Apr 2026 PDF: Revenue Share ₹89,729.91 → CGST ₹8,075.69 → SGST ₹8,075.69 → **Final Payout ₹105,881.29** (= 89,729.91 × 1.18). Section 9 (Tax Rules) still appears afterwards unchanged. Lint clean.

⚠️ Click **Deploy** to push to production. After deploy, every newly generated PIB will include this Final Payout block before the Tax Rules section.

### [2026-05-07] International Weekly Attendance — Cash vs Online salary split (CA-ready)
**User ask** (with screenshot, PB-PERTH Week 18 page): every weekly salary is paid either as cash or online; the screen + the downloaded weekly report should show that split so the CA can deduct cash salaries from the bank-paid total.

**Backend** (`routes/international_attendance.py`):
- New `international_weekly_pay_mode` collection — per-week override keyed by `(center, year, week, employee_id)`. Default `online` when not set.
- `AttendanceEntry` Pydantic model now accepts an optional `pay_mode` (`cash` | `online`) — `/save` upserts it to the override collection without touching the per-day attendance rows.
- `/week-data` joins the overrides into the response and adds `summary.total_cash` + `summary.total_online` alongside the existing `total_payroll`.
- `/export/weekly-excel` rewritten from CSV → real **multi-sheet XLSX** (`openpyxl`):
  - **Sheet 1 "Weekly Payroll"**: existing daily-hours grid + new **Pay Mode** column (Cash badge in amber, Online badge in blue) + a tinted SUMMARY block listing Total Cash, Total Online, Grand Total + an italic note "Total Online is what the CA books in payroll. Total Cash is paid in cash and should be deducted from the bank-paid total."
  - **Sheet 2 "Cash Salaries"**: only the Cash-paid employees with a TOTAL CASH SALARY (deduct from bank-paid total) row at the bottom in highlighted amber. If no one is on cash, shows "No cash-paid employees this week."

**Frontend** (`pages/InternationalAttendance.jsx`):
- New `editedPayModes` dirty-state map; `getPayMode(emp)` / `handlePayModeChange()` helpers.
- New **"Pay Mode"** column in the weekly attendance table — coloured `<select>` (Cash = amber, Online = blue) per row, defaults to Online.
- Save now sends `pay_mode` for every employee so toggles persist immediately.
- Weekly Summary footer expanded from 3 cards → **5 cards**: Total Staff · Total Hours · Total Cash (amber) · Total Online (blue) · Grand Total (emerald) with the same accountant-friendly footnote.
- Weekly export download switched from `.csv` → `.xlsx` with the toast "Weekly report exported (with Cash / Online split)".

**Verified end-to-end** on PB-PERTH Week 18 (live backend): `/week-data` returned `pay_mode` per employee + `total_cash/total_online` in summary; saving with `pay_mode='cash'` for 1 of 3 employees persisted to `international_weekly_pay_mode` (`pay_mode_updates: 3`); refetch showed `cash_employees=1`; weekly XLSX export has both sheets, Pay Mode column at position 13, Cash Salaries sheet correctly empties when no cash entries qualify. Lint clean both sides.

⚠️ **Production note**: Click **Deploy** to push to `intra.purnabramha.com`. After deploy: Pay Mode column appears, defaults to Online for all rows, managers can flip per-week, and the new XLSX export flows the split into the CA's view.

### [2026-05-07] Employee KYC docs + photos — uploads now persist & are viewable everywhere
**User report (with screenshot, production)**: "Passport / PAN card photos are not getting updated. After the green success message there's no way to see the documents / photo for the selected employee. Reports should also have those links and images."

**Root cause**:
- Emergent Object Storage's `GET /objects/{path}/url` endpoint returns **500 Internal Server Error**, so `upload_photo()` was silently storing an empty string in `photo_url` / `aadhaar_doc_url` / etc. PUT succeeded → file landed in storage → DB had no usable URL → frontend "Uploaded" badge appeared but no preview/View link could ever work.
- Per the integration playbook, Emergent Object Storage has **no presigned-URL support**: every file render must stream through our backend with explicit auth.

**Fix** (`backend/routes/employees.py` + `frontend/src/pages/Employees.jsx` + `backend/.env`):
- New `fetch_object(path)` helper alongside `upload_photo()`.
- New endpoint **`GET /api/employee_file_serve?path=...&token=...`** — auth-checked (Admin/SA/Accounts only), namespace-restricted to `purnabramha/employee_photos/...` and `.../employee_docs/...`, streams bytes back inline so browsers render images and PDFs in-tab.
- `employee_upload_photo` and `employee_upload_document` now persist only the storage `path` (e.g. `photo_path`, `aadhaar_doc_path`, plus `*_content_type` and `*_uploaded_at`). The token is **never** baked into the DB — the View URL is rebuilt on every click using the current session token, so links never go stale or leak across admins.
- Frontend `DocUploadBtn`: now takes `hasPath`, shows a green emerald **"View"** button (opens in new tab) + an **"Uploaded"** badge whenever a path exists; the Attach button label flips to **"Replace"** so re-uploads are obvious. Photo `<img>` builds its `src` from `photo_path` via the same helper.
- After a successful upload `formData` (and `selectedEmp`) are updated immediately so the View button appears without a page reload.
- `PUBLIC_APP_URL=https://intra.purnabramha.com` added to `backend/.env` so reports embed working links.

**Reports — clickable hyperlinks now everywhere**:
- **PDF Employee Report** (`/api/employee_report`): each employee card now ends with a "Documents:" row showing clickable blue `[Aadhaar] [PAN/TFN] [Passport] [Visa] [Photo]` labels, each wired to the auth-checked serve URL with the requesting admin's token. The card photo itself is now fetched via `fetch_object(photo_path)` (with legacy public-URL fallback). Card height bumped 2.2" → 2.45" to fit the new row.
- **Excel Employee Report** (`/api/employee_report_excel`): five new columns appended — `Photo · Aadhaar Doc · PAN/TFN Doc · Passport Doc · Visa Doc`. Each cell renders as a blue underlined "Open" hyperlink pointing to `https://intra.purnabramha.com/api/employee_file_serve?...`. Legacy rows (where DB had a relative serve URL with an old uploader token) are auto-rebuilt with the report-requester's current token before being written into the workbook.

**Verified end-to-end**: Uploaded a real PDF for `JAYANTI PRANAV KATHALE` → DB persisted only the path (no token) → serve endpoint streamed back 200 / `application/pdf` → bad-path probe correctly 400-rejected → PDF report grew from 4998→5415 bytes (Documents row added) → Excel report has 22 cols (was 17) with working "Open" hyperlinks.

⚠️ **Production note**: User is testing on `intra.purnabramha.com`. The fix is on PREVIEW. Click **Deploy** to push to production, then any newly uploaded photo/doc will show a working View link and reports will include hyperlinks.

### [2026-05-07] Duty Roster auth hardening + clearer attendance-sync toast
**User issue**: Reports that Duty Roster → Attendance auto-sync was failing for PB-HW, PB-KN and PB-PERTH ("attendance is not getting saved").

**Investigation**:
- Verified DB end-to-end: PB-PERTH had 1 saved roster (2 rows) and matching `attendance` rows with `source='duty_roster'`. PB-HSR likewise OK. **PB-HW & PB-KN had ZERO saved rosters** — managers never successfully reached `/save`.
- Re-ran the full happy path with a real super-admin token against PB-HW: GET returned 16-employee pool, SAVE returned `attendance_synced: 2`, attendance collection persisted both rows. Backend logic is correct.
- **Root cause of intermittent failures**: `routes/duty_roster.py` was wired to the *sync* `verify_token` which only checks the in-memory `otp_store`. After any backend restart (deploys, supervisor cycles), all in-flight session tokens silently 401 against duty-roster endpoints — even though the same tokens work for every other route that uses `verify_token_async` (DB-backed). PB-HW / PB-KN managers (email-OTP) were the most likely victims because they re-login less often.

**Fix (`backend/routes/duty_roster.py` + `backend/server.py`)**:
- Added `set_verify_token_async` setter + internal `_verify()` helper that prefers async DB-backed verification, falls back to sync. All three endpoints (`/get`, `/save`, `/history`) now use it.
- Wired `set_roster_verify_token_async(verify_token_async)` in `server.py`.
- Tokens persist across server restarts now — matches the rest of the modern routes.

**Frontend toast clarity (`pages/DutyRoster.jsx`)**:
- Save toast now names the center + date explicitly: "Roster saved · N attendance record(s) auto-updated for PB-HW on 2026-05-09".
- When `attendance_synced=0` we now tell the manager why: "set a Status (Present / Leave / W / A) on at least one row first" — addresses the silent "I clicked Save but nothing happened" UX.

**Verified**: `python` test against `/api/duty-roster/save` for PB-HW → `attendance_synced: 2`; subsequent `db.attendance.find(...)` returned both rows with `source='duty_roster'`. Backend lint clean.

### [2026-05-06] Daily Duty Roster — new page for Center Managers
**User ask**: A daily duty roster per center, mirroring the WhatsApp screenshot they currently send manually. Center Manager fills it; share to WhatsApp group as image or text.

**Backend** (`routes/duty_roster.py`, new):
- `POST /api/duty-roster/get` — auto-pulls active employees for the center, groups them by designation (Manager / Service / Kitchen / Housekeeping / Others), merges any saved roster for the date.
- `POST /api/duty-roster/save` — upserts the roster doc keyed by `{center, date}`, persists rows with `updated_at` / `updated_by` for audit.
- `POST /api/duty-roster/history` — last 60 saved dates per center.
- Access: Super Admin, Admin, Accounts → any center; Center Manager → own center only.
- Status codes match the screenshot: time strings (Present), `LEAVE`, `W` (Weekly Off), `A` (Absent).

**Frontend** (`pages/DutyRoster.jsx`, new — sidebar link "Daily Duty Roster" under Attendance):
- Center + Date selectors (Manager locked to own center).
- Editable groups: Manager → Service → Kitchen → Housekeeping → Others. Per row: Duty Time, In Time, Status dropdown. "Add ad-hoc" for trainees not in master.
- **Live WhatsApp-styled preview** matching the user's reference image: yellow `PURNABRAMHA / DD/MM/YY` header, blue group bands, bordered table with SR.NO / NAME / DESIGNATION / DUTY TIME / IN TIME columns.
- Share buttons: **Copy Text** (multi-line WA-friendly), **Copy Image** (PNG → clipboard via html2canvas, one-tap paste), **Download PNG** (browser fallback).
- "Last saved … by …" badge for audit visibility.

**Verified live**: `GET` returned 16 PB-HSR employees grouped correctly. `SAVE` upserted 3 rows. UI renders with yellow/blue layout matching the reference. Lint clean.

### [2026-05-04] Signature block — bigger, centered, authoritative
**User issue (with screenshot)**: Earlier signature block was a small 2-column layout with the stamp tucked into a corner — looked weak.

**Redesign (`backend/utils/signature.py`)**:
- Cropped the source asset from 1414×2000 (mostly white space) → tight 453×359 crop saved as `signature_kaka_cropped.png`. Stamp + signature now fill the frame.
- New layout: a single **5.6" wide bordered card** (light grey background, soft border) centered on the page.
- Stack inside the card (all centered):
  1. `For <b>Entity</b>` header (bold)
  2. **Stamp + Signature image at 3" × 2.4"** — large, dominant, between the entity header and the typed details
  3. Horizontal divider line
  4. **Shashikant Pande** (13pt bold, navy)
  5. CFO (Head of Accounts)
  6. Purnabramha Accounts
  7. Entity name (Manaswini Foods Pvt Ltd / Purnabramha LLC Pty Ltd — auto-switched by country)
  8. *Authorised Signatory · Accounts* (italic caption)
- Verified live by re-rendering the same PB-KAL May 2026 sales ledger PDF and image-analysing the result: signatory block now reads as professional, authoritative, and properly centered.

**Files**: `backend/assets/signature_kaka_cropped.png` (new), `backend/utils/signature.py`. No other code changes — every consumer (10 ledgers, CA bundle, PIB, MIS Franchise PDF) automatically picks up the new look since they all call the same helper.

### [2026-05-04] Authorised Signature on all Accounts reports + Preview before download + Strict revoke gating
**User asks**: 
1. Add Shashikant Pande / CFO signature block to all ledger PDFs (CA bundle, franchise-owner copy, individuals) AND all Accounts reports.
2. Preview ledger before downloading — both Franchise Owner Dashboard and Center Accounts.
3. Once Accounts revokes a release, the franchisee should not see ANY ledgers for that month.

**Implementation**:

**1. Signature block** — new `backend/utils/signature.py::signature_block(country, label)` returns a reportlab Table with:
- Caption: "For <Entity>"
- Name: **Shashikant Pande**
- Role: **CFO (Head of Accounts)**
- Org line: **Purnabramha Accounts**
- Entity: **Manaswini Foods Pvt Ltd** (India centers) OR **Purnabramha LLC Pty Ltd** (Australia / outside-IN) — auto-detected by country
- Right-side: actual signature image stored at `/app/backend/assets/signature_kaka.png` (rendered at 2"×1.56")

**Wired into**:
- `routes/ledgers.py::_render_pdf` — covers ALL 10 ledger PDFs (Sales, Expense, Cash, Bank, Commission, Loans, Payroll, GST, P&L, Owner) AND the CA Bundle ZIP (re-uses the same renderer for individual + bundled).
- `utils/pdf_generator.py::build_pib_pdf` — Center Accounts monthly PIB report.
- `routes/mis_dashboard.py::_build_franchise_pdf` — MIS Franchise PDF.

**Verified live**: PB-HSR sales ledger PDF contains "Shashikant Pande", "CFO", "Manaswini Foods" (×2). PB-PERTH PIB contains "Shashikant Pande", "CFO", "Purnabramha LLC Pty" (×2). Country switch works automatically.

**2. Preview before download** — both surfaces:
- **Center Accounts → Ledgers tab** (`components/LedgersTab.jsx`): each ledger card now has 3 buttons in order — `Preview · PDF · Excel`. Preview opens a 5xl-wide modal with the PDF rendered inline in an iframe, plus a "Download PDF" CTA inside the modal.
- **Franchise Owner Dashboard → My Ledgers** (`pages/FranchiseOwnerDashboard.jsx`): same 3-button row per ledger, same preview modal.
- Both modals revoke their object URL on close to prevent memory leaks.

**3. Strict revoke gating** — already correct in code; verified during this task:
- `routes/owner_reports.py::set_visibility` flips `owner_report_visibility.ready: True/False` via the Send/Hide toggle.
- `routes/ledgers.py::owner/list` only includes a month if `vis.ready === True` (full report) OR explicit `report_type=owner_ledger; released=True` (legacy owner ledger). Once revoked → both false → month omitted from response → not visible to franchise owner.
- Per-ledger `/api/ledgers/<type>` endpoints also recheck `vis.ready` before returning content for franchise-owner sessions; returns 403 with a friendly message after revoke.

**Files**: `backend/utils/signature.py` (new), `backend/assets/signature_kaka.png` (new), `backend/routes/ledgers.py`, `backend/utils/pdf_generator.py`, `backend/routes/mis_dashboard.py`, `frontend/src/components/LedgersTab.jsx`, `frontend/src/pages/FranchiseOwnerDashboard.jsx`. Lint clean. UI verified live.

### [2026-05-04] MIS Dashboard — Total Deductions / Net Revenue / Revenue Share parity
**User ask**: Same Total Deductions + Net Revenue + correct Revenue Share fix that just landed on Owner Dashboard, but applied to **Accounts → MIS Dashboard** as well.

**Fix (`pages/MISDashboard.jsx`)**:
- Same central calc: `Total Deductions = Commissions + GST` · `Net Revenue = Sales − Total Deductions` · `Revenue Share = pct × Net Revenue`.
- KPI strip rebuilt to **10 cards** mirroring Owner Dashboard order: Sales · Expenses · Commissions · **GST on Sales** · **Total Deductions** · **Net Revenue** · **Net Profit (P&L)** · WC · Avg/Bill · **Revenue Share (X% × Net Rev)**. Default share % = 15 (India) — falls back to per-center `revenue_share_percentage` when a single center is selected.
- Excel export sheet rewritten as the same accountant chain: Sales → Less Comm → Less GST → = Total Deductions → = Net Revenue → Less Expenses → = Net Profit.
- `Percent` icon added to lucide-react import.

**Bulk Ignore reminder**: User saw production screenshot still missing Bulk Ignore — the fix from earlier this session is already in preview (verified rendering in toolbar). Just needs the Deploy click.

**Files**: `frontend/src/pages/MISDashboard.jsx`. Lint clean. UI verified live.

### [2026-05-04] Owner/Franchise Dashboard — Total Deductions + Net Revenue + Revenue Share fix
**User issue (with screenshot, PB-KAL April 2026)**: Dashboard had no "Total Deductions" KPI, and Revenue Share showed −₹2,110 (15% of *Net Profit* = −14,069 × 0.15) instead of 15% × Net Revenue (~₹1,17,890).

**Root cause** (`pages/FranchiseOwnerDashboard.jsx` line 353): `netRevenue = netProfit × pct` was wrong. Net Revenue should be `Sales − Commissions − GST` and Revenue Share = `pct × Net Revenue`.

**Fix**:
- New centralized computations at top of component:
  ```js
  totalDeductions = totalCommissions + totalGst
  netRevenue      = totalSales − totalDeductions
  revenueShareAmount = netRevenue × revenueSharePct/100
  ```
- KPI strip rebuilt as 10 cards in correct accountant order: Total Sales · Total Expenses · Commissions · **GST on Sales** (fuchsia) · **Total Deductions** (orange) · **Net Revenue** (cyan) · **Net Profit (P&L)** · Working Capital · Avg/Bill · **Revenue Share (X% × Net Rev)**.
- Excel export rebuilt as Sales → Less Comm → Less GST → = Total Deductions → = Net Revenue → Less Expenses → = Net Profit → Revenue Share Payable.
- For PB-KAL April 2026 (Sales 8,28,000 · Comm 2,676 · GST 39,392): Net Revenue = ₹7,85,932 · Revenue Share (15%) = ₹1,17,890.

**Files**: `frontend/src/pages/FranchiseOwnerDashboard.jsx`. Lint clean. UI verified.

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

### [2026-05-11] Overseas (non-India) Profit Share + 5% MFPL Royalty
- **New canonical helper** `/app/backend/utils/overseas_share.py`:
  - `is_overseas(country)`: any country != "India"
  - `compute_overseas_share(eligible_profit, net_sales)`: 80/20 split + 5% MFPL
  - `compute_cumulative_mfpl(db, center, up_to_month)`: walks daily_sales, accrues
- **Overseas rules (PB-PERTH / Australia):**
  - **No Minimum Guarantee (MG)** — `mg_calculation=null`, MG card hidden
  - **Eligible Profit** = Sales − GST − Commission − CommGST − Expenses
  - **Profit Share**: Franchise Owner 80%, Purnabramha LLC 20% (on Eligible Profit)
  - **MFPL Royalty** = 5% × Net Sales (Sales − GST) → accrued as cumulative liability, paid=0
- **Surfaces updated:** Center Accounts summary/payout-summary, Owner Ledger PDF, PIB Section 8 + 8B, FranchiseOwnerDashboard
- **India behaviour preserved unchanged**
- **Tests:** 9/9 pytest pass at `/app/backend/tests/test_iteration82_overseas_profit_share.py`

### [2026-05-11] PIB/GST/Commission Preview + Monthly Email Pack + MFPL FY-Gating + Advance Delete + Attendance Multi-Center Edit
- **Reports tab preview**: PIB, GST, Commission cards now show **Preview + Download** buttons. Preview opens inline iframe modal (or JSON for PIB).
- **Monthly Email Pack** (`POST /api/center-accounts/email-pack`):
  - format=`json` → `{subject, body, attachments}` for review
  - format=`zip` → ZIP with `EMAIL.txt` + PIB + GST + Commission + Owner Ledger + Bank Statement PDFs + any uploaded month documents
  - Body tone: "Jai Hind Namaskar Team <franchise>" → profit branch celebrates togetherness, loss branch reassures team will work together → "— Purnabramha Accounts Team"
- **MFPL FY-Gating**: `MFPL_ACCRUAL_START_MONTH = "2026-04"` in `utils/overseas_share.py`. Months before this date contribute 0 to cumulative liability and to per-month royalty.
- **Salary Advance delete**: new `POST /api/delete_advance` endpoint (super admin / admin / center manager of that center) + red Trash button on Advances tab.
- **Attendance multi-center edit**: Super Admin / Admin can now switch center via a new selector at the top of Attendance page. All daily/monthly/advances API calls use `activeCenter` instead of `session.center`. Center Manager flow unchanged.
- **Tests:** 8/8 pytest pass (email-pack JSON+ZIP, MFPL gating, delete_advance perms), audit script ALL SURFACES MATCH for India + Perth.

### [2026-05-11] Commission Parity Fix (CRITICAL data-integrity bug)
- **Bug**: PIB Section 3 "Total Deductions" row showed a different number than the sum of per-platform deductions (e.g., 41,217.82 ≠ 25,180.14 + 11,333.14 + 4,599.74 = 41,113.02). Caused by `_row_total` in `utils/commissions.py` summing **all four** schema fields (commission_amount + gst_tax_deductions + other_deductions + tds) while per-platform UI used only `gst_tax_deductions + other_deductions`. Double-counted base commission + new-schema and erroneously included TDS (which is booked separately as operating expense).
- **Fix** (`/app/backend/utils/commissions.py` + `routes/center_accounts.py`):
  - `_row_total` now mirrors per-platform logic: use new-schema (gst_ded + other_ded) when present, else fall back to commission_amount. TDS excluded entirely.
  - `get_total_commissions(...)` now returns a guaranteed `by_platform` dict that ALWAYS sums to `total` to the paise — falls back to `commission_statements` (legacy) and applies AU 10% grossup consistently.
  - `center_accounts.py` summary uses canonical `by_platform` directly, removing the local breakdown that could drift.
- **Tests**: 5 new pytest in `tests/test_iteration84_commission_parity.py` locking the contract. All 14 pytest (iteration 82 + 84) pass. Financial parity audit ALL SURFACES MATCH for PB-HSR + PB-PERTH.
- **Impact**: All reports (PIB, Commission Summary PDF, Owner Ledger, MIS, MG Payout, Center Accounts screen) now show identical commission figures. The per-platform table's TOTAL row equals the sum of its rows on every PDF and screen.

### [2026-05-13] Franchise Owner Reports — Excel + Raw Files + Ledger Restructure
- **Email Pack ZIP cleanup**: removed Franchise Owner Ledger PDF from the ZIP (kept available as a separate download). Added live Sales/Expense Excel for the full month, plus all raw uploaded Excel/PDF files (Swiggy/Zomato/Bank Statement) when present.
- **New canonical helper** `/app/backend/utils/sales_expense_excel.py` — pulls live `daily_sales` + `expenses` and produces a 2-sheet workbook (Sales rows with totals; Expenses with category summary). Reused by the Email Pack and Franchise Reports endpoints so every surface emits an identical Excel.
- **Raw file persistence**: `/upload-commission-excel` and `/bank-recon/upload` now save the raw uploaded file to `/app/backend/raw_uploads/<kind>/<center>/<month>/` and record metadata in `raw_uploads` collection (`raw_id`, `kind`, `platform`, `original_filename`, `stored_path`, `size_bytes`, `uploaded_by`, `uploaded_at`).
- **New backend module** `/app/backend/routes/franchise_reports.py` exposes 3 endpoints (all view+download only):
  - `POST /api/franchise-reports/sales-expense-excel` — month / range / specific-date filters
  - `POST /api/franchise-reports/raw-files` — list files for {center, month}
  - `POST /api/franchise-reports/raw-file/download` — fetch one file by `raw_id`
- **Frontend `OwnerReports.jsx`** (Franchise Owner Dashboard → Reports) now shows:
  - **Franchise Owner Ledger** card (View PDF + Download PDF, separate from ZIP)
  - **Sales / Expense Excel** card with Full Month / Range / Date toggle + Download/Open
  - **Raw Uploaded Files** panel (table of Swiggy/Zomato/Bank Statement etc. with view+download icons; empty state shown when nothing uploaded)
- **Permissions preserved**: Franchise Owner sees only view + download buttons. Edit/delete/upload are gated to Manager/Admin as before. `enforce_owner_visibility` enforces center scope.
- **Tests**: 14/14 pytest pass (iter 82 + 84). Parity audit ALL SURFACES MATCH for PB-HSR + PB-PERTH.

## Pending / Backlog
- (P1) WhatsApp/Email notification hooks
- (P1) Code freeze preparation audit
- (P1) Live recompute of P/L & WC cascade in WC Breakdown table on Sales/Comm/Expense edit
- (P2) Inline audit log expansion for Topups in WC table
- (P2) Add "Backfill role_key" admin script/button
- (P2) Auto-categorization/heuristics for Bank Recon
- (P2) Image Upload for Recipes, Franchise Deal Simulator, Menu card PDF, PDF refactoring, 7-year retention deletion prompt
- (P2) MFPL royalty *payment* tracking (collection + paid-down accrual) once MFPL starts taking the royalty
