# Purnabramha IntraPB — Product Requirements Document

## Problem Statement
Internal management system for "Purnabramha," a restaurant franchise.


### [2026-02-18 — Visa Recommender: added AU short-stay activity visas 400 / 407 / 408] (P0 hotfix)

User asked: *"why this is not helping me to find out 400 or 407 or 408 visa?"* — the Recommender was not even surfacing Australia's short-stay activity visas, despite a goal like *"400 visa for Australia for Purnabramha Perth operation for 2 major events"*. Even Claude's own AI rationale was hinting *"better suited as Subclass 400 or 482"* but **those pathways simply didn't exist in our catalog** (catalog only had the 5 long-term PR pathways).

**Fix** (`/app/backend/routes/visa.py`):
- Added 3 new AU pathways: **AU-400** Temporary Work (Short Stay Specialist, 2-4 wk, 1-3 mo stay), **AU-407** Training Visa (2-4 mo, up to 24 mo stay), **AU-408** Temporary Activity (1-3 mo, event/entertainment/exchange-driven). Each with realistic cost bands, timeline bands and key requirements.
- Updated `AU.common_pathway_ids` to include the new short-stay set (8 total AU pathways now).
- Added **short-stay keyword boost** in `_score_pathway`: when the applicant goal contains any of `event/events/festival/launch/training/short/short-stay/specific event/specialist/activity/temporary stay/few months/specialised`, the activity visas (400/407/408) get **+22 score**, and Permanent pathways get **−8** because they over-shoot a short-stay need.
- Upsert seeds (existing v2 idempotent pattern) auto-add the 3 new pathways on production the moment Visa Helper page is opened post-deploy.

**Verified on preview** with Anirudha S profile + goal "400 visa for australia for purnabramha perth operation for 2 major events": Top-3 is now **AU-400, AU-407, AU-408 all at Strong 100/100**, with AU-482 / AU-188 dropping to #4 / #5.

⚠️ **Deploy required** to push to `intra.purnabramha.com`.

---


### [2026-02-18 — P&L Revenue Share fixes: MFPL with zero-paid + Projection RS] (P0 hotfix)

User reported on production:
1. **MFPL incorrect when Amount Paid = 0** — should deduct the *payable* (max of Rev Share + GST, MG + GST), not 0.
2. **Projection Revenue Share = 0** for many months until 2028 Feb — because projection used `rs_base = Sale − Expense` (P/L) so loss-making months produced 0.

**Fixes** (`/app/backend/routes/pnl_revenue_share.py`):
- **Overview MFPL**: when `amount_paid > 0` deduct that (cash basis); when `amount_paid == 0` deduct `max(rs_plus_gst, mg_plus_gst)` (payable). Verified: PB-HSR Jun-2025 (paid=0) now ₹1.32 L instead of ₹3.74 L; total FY MFPL went from ₹28.31 L → ₹13.20 L.
- **Projection RS**: now computes a `rs_base/sale` ratio from the seed months (effectively inheriting the historical commission + GST structure ≈ 90-95% of sale) and applies it forward. Every projected month now produces a positive Revenue Share even if Sale < Expense.
- **Projection MFPL**: uses payable as the outflow (matches Overview's zero-paid branch).
- **Projection start_month default**: changed to `max(today+1month, last_actual+1month)` so projections start in the *future*, not from a historical month. Verified: today=2026-06 → projection starts at 2026-07 (was 2026-04 before).

**Verified end-to-end on preview** with PB-HSR FY 2025-26 + PB-MGT 3-year projection from baseline.

⚠️ **Deploy required** to push to `intra.purnabramha.com`.

---


### [2026-02-18 — Center Accounts: P&L Revenue Share Overview + Revenue Share Projection] (P0)

Two new tabs added under **Accounts → Center Accounts** (right after *Bundles & Exports*). The existing Overview tab is left untouched.

**New route file**: `/app/backend/routes/pnl_revenue_share.py` (~440 lines — also kicks off the planned refactor away from the 3700-line `center_accounts.py`).

**Endpoints**:
- `POST /api/center-accounts/pnl-revenue-share-overview` — month-wise grid for a center with filters: `financial_year` (e.g. "2025-26") · `from_month`/`to_month` · `revenue_share_pct` (10/15) · `gst_applicable` (Yes/No, 18% standard). Returns 11 columns: Month · Sale · Expenses · P/L · Revenue Share Base · Revenue Share · Revenue Share + GST · MG · MG + GST · Amount Paid · Profit Share MFPL — plus a totals object.
- `POST /api/center-accounts/revenue-share-projection` — forward projection for 1-5 years. Seeds baseline from the last 3 months that had actual sales (scans up to 18 months back to handle gaps); compounds Sale × (1 + sales_growth%)^i, Expense × (1 + expense_growth%)^i. Inputs: `years`, `sales_growth_pct`, `expense_growth_pct`, `gst_pct`, `revenue_share_pct`, `mg_amount` (override, else last actual), `start_month` (else next month after last actual).
- `POST /api/center-accounts/pnl-revenue-share-overview/export-pdf` / `export-excel` — landscape PDF + XLSX with Purnabramha logo (if present), center name, period, full grid, total row at TOP, "Prepared by: System", account manager line, download date.
- `POST /api/center-accounts/revenue-share-projection/export-pdf` / `export-excel` — same export pattern for projections.

**Formulas** (matches existing `/payout-summary` engine):
- P/L = `Sale − Expenses − Commission − GST_on_sales`
- Revenue Share Base = `Sale − Commission [− GST]` (honours per-month GST treatment toggle)
- Revenue Share = `max(0, RS Base) × pct` · with-GST = `RS × 1.18` when GST filter = Yes
- MG from `calculate_mg()` (existing) · with-GST = `MG × 1.18` when GST filter = Yes
- Amount Paid = sum of `payout_payments.amount` for that month (actual disbursed — user-confirmed convention)
- Profit Share MFPL = `Sale − Expenses − Amount Paid` (user-specified)

**Frontend**: `/app/frontend/src/components/PnLRevenueShareViews.jsx` exposes `PnLRevenueShareOverview` and `RevenueShareProjection`. Both wired as new tabs inside `CenterAccounts.jsx` (after *Bundles & Exports*). Tab IDs: `tab-pnl-rs`, `tab-rs-projection`. Layout: sticky dark header + bold amber **TOTAL row at the top** + monthly rows; PDF / Excel download buttons in the card header.

**Verified** on preview with center `PB-HSR` FY 2025-26:
- 12 monthly rows · Totals: Sale ₹1.17 Cr · Expenses ₹88.4 L · Revenue Share ₹16.99 L · Rev Share + GST ₹20.05 L · Amount Paid ₹1.25 L · Profit Share MFPL ₹28.31 L
- 3-year projection rendered 36 rows · Sales grow from ₹10.39 L (Jan-2026, seeded from Oct-Dec 2025 actuals) to ₹57.29 L (Dec-2028) at 5% MoM compounding.
- PDF export = 4.1 KB landscape · Excel export = 6.5 KB

⚠️ **Deploy required** — these tabs are in preview only.

---


### [2026-02-18 — Visa Helper letter generation: background-job + thread-pool fix] (P0 hotfix)

User reported on production (`intra.purnabramha.com`): **"Letter generation failed"** + **"Failed to fetch"** when clicking *Generate AI Letters* with All letters (15) scope.

**Root cause** (3-layer issue):
1. `emergentintegrations` LLM client is sync-under-the-hood — a plain `asyncio.gather(await chat.send_message(...))` ran each call sequentially because the GIL/blocking client never yielded the event loop.
2. With ~15-30s per Claude Sonnet 4.5 letter × 15 letters, total wall time was 2-4 minutes.
3. Production ingress (Cloudflare → k8s) hard-kills any HTTP request after ~60s with a 502 — browser shows "Failed to fetch".

**Fix** (`/app/backend/routes/visa.py`):
- `POST /api/visa/application/{aid}/generate-letters` now **kicks off the work as a background job** via `asyncio.create_task` and returns immediately with `{job_id, status: "running", total: N}` (response in <1s — ingress-safe).
- Each LLM call now runs through `loop.run_in_executor(None, _call_llm)` — a thread pool — so they **truly parallelize** despite the sync HTTP client (verified: **28 letters in 55s**, ~12× speed-up over sequential).
- Per-letter 90s `asyncio.wait_for` so a single hang can't block the batch.
- Job state persisted on the application doc (`letters_job: {status, drafted_count, total, started_at, completed_at}`) and stays consistent if user reloads the page.
- New endpoint `GET /api/visa/application/{aid}/letter-status` returns the job status + accumulated `letters`.
- Failed letters get `status: "Pending"` with a clear error placeholder; partial results are preserved so the user can regenerate just the ones that failed.

**Frontend** (`/app/frontend/src/pages/VisaHelper.jsx`):
- "Generate AI Letters" button now kicks off the background job, shows a toast "Drafting N letters in the background — this typically takes 30-90s", and **polls every 4s** for up to 4 minutes — UI stays responsive.
- Letters appear in the UI as soon as the job completes; partial successes show a yellow toast "Drafted X/N — the rest timed out. Click Regenerate."
- Clean error message replaces the previous generic "Letter generation failed" toast.

**Architectural side benefit**: `build-complete-bundle` no longer tries to LLM-draft letters in-line (which would have hit the same ingress timeout). Users now run *Generate AI Letters* once, then *Generate Complete Bundle* simply packages the already-drafted letters into a structured ZIP in <5s.

**Testing**: 35/35 backend tests pass (including 3 affected tests rewritten to use the polling pattern). Verified end-to-end on preview with all 28 templates in scope=all completing in 55s.

⚠️ **Deploy required** — these fixes are in preview only. Click *Save to Github → Deploy* to push to `intra.purnabramha.com`.

---


### [2026-02-18 — Visa Helper v2: AI Visa Advisor + Document Factory + Server-Stored Bundles] (P0)

Major upgrade turning the Visa Helper from a 10-step questionnaire into an **AI-first founder tool**.

**Backend** (`/app/backend/routes/visa.py`, now ~2000 lines):
- **De-dupe fix** — `_ensure_seeds()` rewritten to **upsert with `$set` on machine fields** (idempotent across deploys, also backfills new fields onto previously-seeded rows). All list endpoints (`/countries`, `/pathways`, `/entities`, `/signatories`, `/letter-templates`) now run through `_dedupe_by()` so the API surface is always unique even if the DB has stragglers.
- **One-time cleanup migration** — `POST /api/visa/admin/cleanup-duplicates` deletes duplicate rows across all 5 collections by primary key (keeps oldest). Super-Admin-only.
- **Expanded catalog** —
  - AU: 186 ENS, 482 TSS, 188 BIIP, **494 Regional**, **Global Talent**
  - USA: **L-1A**, **E-2**, **EB-1C**, **EB-2 NIW**
  - Japan: Business Manager, **HSP** (Highly Skilled Professional)
  - Belgium/EU: Single Permit, Self-employed, **EU Blue Card**, **ICT Directive**
  - Singapore: Employment Pass, EntrePass
  - 12 new country-specific **expansion-letter templates** (AU South Perth / Melbourne / Sydney, US Atlanta / Dallas / L-1A / EB-1C support, JP market entry, BE single permit, SG EP/EntrePass)
  - 5 new entities (Purnabramha AU/US/JP/BE/SG subsidiaries) + 4 signatories.
  - Each pathway now ships `key_requirements`, `company_cost_band`, `applicant_cost_band`, `timeline_band`, `spouse_work_rights` so the Recommender output matches the Sandeep-style spec exactly.
- **AI Recommender Engine** — `POST /api/visa/recommend` takes founder-style profile (age, role, experience, English, family, shareholding, expansion/business-plan/financial/franchise/skills flags, goal, optional country shortlist) and runs a **hybrid scoring engine**: deterministic rules (~1s) produce score + reasons + risks; if `use_ai_narrative=true`, Claude Sonnet 4.5 enriches the top-5 picks with a 2-3 sentence rationale (~30s). Returns `top` (5 best) + `all` (every pathway scored). India-not-an-E2-treaty risk auto-detected.
- **Server-stored bundles** — `POST /api/visa/application/{aid}/build-complete-bundle` ensures report+letters are drafted, packages a structured ZIP (01_Report.pdf + 02_Checklist.xlsx + 03_Letters/*.docx + 99_manifest.txt), persists to `/app/backend/visa_bundles/<applicant>/<timestamp>_*.zip`, logs to `visa_bundle_history`, **prunes to last 30** globally. New admin endpoints `GET /admin/bundles` and `GET /admin/bundle/{id}` for re-download. Caller can override `signatory_id` / `entity_id` / `pathway_id` at build time.

**Frontend** (`/app/frontend/src/pages/VisaHelper.jsx`, ~1700 lines):
- **AI Recommender is now the default first tab** (Tabs: AI Recommender · Applications · Manual Wizard · Admin Panel).
- **Recommender form** — compact founder-style inputs (applicant name, role, age, YoE, nationality, English status, shareholding %, goal) + 6-country pill picker + 8 toggle switches (family, existing ops, expansion plan, business plan, financial proof, franchise letter, skills assessment, AI narrative). Result cards show score badge (Strong/Medium/Low), country flag, timeline, cost bands, ✓ Why bullets, ⚠ Risk bullets, AI rationale (italic), and a **"Proceed with this visa"** CTA that seeds the Manual Wizard with country + applicant snapshot + selected pathway.
- **"Generate Complete Bundle"** — new amber button on Wizard Review step. Calls `build-complete-bundle` (with chosen signatory + entity + pathway), downloads the ZIP, and the bundle becomes visible in Admin Panel → **Bundle History** (new sub-tab) for re-download.

**Testing**: testing agent confirmed **35/35 backend tests pass** (12 new v2 + 23 v1 regression). Frontend end-to-end Recommender → Wizard prefill flow verified; Bundle History sub-tab confirmed via screenshot showing the persisted `PB_CompleteBundle_SandeepKathale_AU_VA-3F0A0162DD.zip` (45 KB) with Download button.

⚠️ **Deploy required** — preview only. On first production hit, `_ensure_seeds()` will auto-de-duplicate the live DB (idempotent). If you still see duplicate country tiles on `intra.purnabramha.com` immediately after deploy, super-admin can hit `POST /api/visa/admin/cleanup-duplicates` once to force it.

---


### [2026-02-18 — Visa Helper: Send to Immigration Lawyer (preview + one-click ZIP)] (P1)

Add-on to the new Visa Helper module: a polished **"Send to Immigration Lawyer"** flow on the Wizard's Review step.

**Backend** (`/app/backend/routes/visa.py`):
- `POST /api/visa/application/{aid}/lawyer-bundle-preview` — returns a typed file manifest (order, name, kind, description) + warnings (e.g. missing report or zero letters) so the UI can show users exactly what will ship before they click download.
- `POST /api/visa/application/{aid}/lawyer-bundle` — builds an enhanced ZIP with structured ordering:
  - `00_COVER_LETTER_TO_LAWYER.pdf` — newly generated, lawyer-facing cover letter (ReportLab) addressed to `lawyer_name` / `lawyer_firm`, with applicant snapshot, proposed role, internal readiness assessment, open risks, contents map, and notes provided by the caller.
  - `01_Visa_Readiness_Report.pdf` (existing report engine).
  - `02_Letter_Checklist.xlsx` (existing checklist engine).
  - `03_Letters/<safe_name>.docx` for every drafted letter.
  - `99_manifest.txt` machine-readable manifest including who/where it was addressed.
- Filename: `PB_VisaBundle_{ApplicantName}_{CountryCode}_{AID}.zip`.
- Audit trail: persists `lawyer_dispatch` (lawyer name, firm, notes, generated_at) on the application doc and bumps `status` to `lawyer_bundle_ready`.

**Frontend** (`/app/frontend/src/pages/VisaHelper.jsx`):
- New emerald-green **Send to Immigration Lawyer** button on the Review step, next to PDF / Excel / ZIP downloads.
- Click opens a **preview Dialog** with lawyer name / firm / notes inputs, a live file-manifest table (#, file name + description, kind badge), warnings if the report or letters are missing, and a single **Download Bundle (.zip)** CTA.
- Uses a new `downloadAuthedPost()` helper so the POST body carries lawyer metadata and the response streams as a Blob download.

**Verified live** (PB-MGT super admin, AID `VA-3F0A0162DD`): preview returns 5 files (cover, report, checklist, 1 letter, manifest), POST `/lawyer-bundle` returns a 49 KB zip with the expected entries; UI dialog renders the manifest table and download button.

⚠️ **Deploy required** to push to `intra.purnabramha.com`.

---


### [2026-02-18 — Visa Helper / Global Mobility module shipped] (P0)

Brand-new intranet module under **HR Management → Visa Helper**, restricted to Super Admin + Founders.

**Backend** (`/app/backend/routes/visa.py`, ~1050 lines, wired in `server.py`):
- **Seeded masters**: 6 priority countries (Australia, USA, Japan, Belgium, Europe, Singapore), 14 visa pathways with min/max age + duration + summary, 15 default letter templates, 1 parent entity (Manaswini Foods Pvt. Ltd.), 2 signatories (Jayanti Kathale, Sandeep Kathale).
- **Application CRUD**: `POST /api/visa/application` upserts wizard answers (applicant + business), `GET /api/visa/applications`, `GET /application/{id}`, `DELETE /application/{id}`. Non-admin users only see their own apps; Super Admin / Founder see all.
- **Readiness Report**: `POST /application/{id}/generate-report` runs rule-based suitability scoring (age, experience, English status, document availability), ranks pathways by fit, builds document checklists (company / applicant / family), cost-head estimates, next-step list, and a 15-letter signatory plan.
- **AI Letter Generation**: `POST /application/{id}/generate-letters` calls Emergent LLM with **Claude Sonnet 4.5** (`emergentintegrations.llm.chat`) using the saved Emergent LLM Key. Scope filter supports `all | company | franchise | personal | resolutions`. Each letter persisted on the application document.
- **Exports**: `GET /report-pdf` (ReportLab), `GET /checklist-excel` (openpyxl), `GET /letter/{key}/word` (python-docx), `GET /zip` (one-click bundle of PDF + Excel + every Word letter + manifest).
- **Admin CRUD**: `POST/DELETE /admin/{country|pathway|letter-template|entity|signatory}` — Super-Admin only, enforced via `_require_admin()` checking `is_super_admin` / `is_admin` booleans (the platform's actual session shape).

**Frontend** (`/app/frontend/src/pages/VisaHelper.jsx`, ~1130 lines):
- Three top-level tabs: **Applications** · **+ New Wizard** · **Admin Panel** (admin tab hidden for non-admins).
- **Applications list**: table with App ID, Applicant, Country, Status, Updated + Open / Delete actions.
- **10-step Wizard**: Country selection (tile grid with flags + available pathways preview) → Applicant → Education & Skills → Experience → Family (conditional spouse/children fields) → Business / Role → Signatory & Entity → Documents-ready toggles → Goals & Notes → Review.
- **Review step**: Save Draft · Generate Readiness Report (renders suitability badge, risks list, ranked-pathways table, document checklists, letter checklist) · Generate AI Letters with scope picker (Claude Sonnet 4.5) · per-letter expandable view with `.docx` download · top-level PDF / Excel / ZIP download buttons.
- **Admin Panel**: 5 sub-tabs (Countries, Pathways, Letter Templates, Entities, Signatories) each rendered by a generic `CRUDTable` component supporting Add / Edit / Delete with mixed inputs (text, number, textarea, select).
- Sidebar entry under HR Management with `superAdminOnly: true`.

**Testing**: 23/23 pytest tests pass (`/app/backend/tests/test_visa_helper.py`) covering list endpoints, application CRUD, report + letter generation, all 4 export formats, admin CRUD upsert/delete on all 5 collections, plus non-admin 403 rejection. Frontend rendering verified via testing agent (page load, 3 tabs, sidebar link, 6 country tiles, 5 admin sub-tabs).

**Bug fixed mid-test**: `_require_admin()` originally only checked a `role` string; the platform's `/api/verify_otp` response uses `is_super_admin` / `is_admin` boolean flags instead, causing all admin upserts to return 403. Patched to accept booleans first, role-string as fallback.

⚠️ **Deploy required** to push to `intra.purnabramha.com`.

---


### [2026-02-18 — WC Overview Grid: added 4 legacy columns user was missing] (P1)

User confirmed (option 1): *"Add all 4 missing columns and keep Revenue Share Base."*

Added to `WCOverviewGrid.jsx`:

| Column | What it shows |
|---|---|
| **Topup** | Manual WC top-up amount for the month (read-only; green when > 0, dash otherwise). Added via the existing dedicated "Add Top-up" dialog. |
| **Other Income** | Non-operational income line (refunds, scrap, etc.). Read-only; teal when > 0. |
| **Diff WC** | Closing − Opening (net WC change for the month). Green +Δ = gained capital, red −Δ = lost capital. Includes the "+" sign for positive deltas. |
| **WC %** | Closing ÷ Base × 100. Colour-coded against the policy thresholds: green ≥100% (active), amber 50-99% (restoring), red <50% (blocked). |

Grid now has **15 columns** matching the legacy WC chain + the new Revenue Share Base + editable controls. Totals row updated to include Topup and Other Income sums. Footer caption explains the new column formulas and colour thresholds.

All 4 fields are already returned by `/api/center-accounts/wc-table` — purely a frontend addition, no backend change.

⚠️ **Deploy required** to push to `intra.purnabramha.com`.

---



### [2026-02-18 — WC Overview Grid made editable with live recalculation] (P1)

User feedback: *"and all are editable but all are having calculation on it like what we were having before — same thing u have to bring it back."*

**Implementation** (`components/WCOverviewGrid.jsx` v2):
- **Editable cells** (✎ pencil hint in header): GST · Expenses · Commissions · WC Adjustment — the four override fields the backend `/wc-row-save` route accepts as absolute targets.
- **Read-only cells**: Month · Opening WC · Sales (sourced from Daily Sales) · Net Available · Revenue Share Base · Closing WC — all driven by Single Financial Engine.
- **Live row recalculation as you type** (no save needed for preview):
  - `Net Available = Sales − Expenses − Commissions`
  - `Revenue Share Base = max(0, Sales − Commissions − GST)`
  - `Closing WC = Opening + Net Available + WC Adj + Topup + Other Income`
- **Dirty rows** highlight amber and show inline Save (✓) and Reset (↺) icons next to the status badge. Save POSTs `target_expenses` / `gst_target` / `commission_target` / `wc_adjustment` and refreshes the whole table so the chain recomputes correctly on the server.
- **Totals row** under header continues to sum live values (including unsaved edits), so users see total impact across months at a glance.
- Footer caption explains the formulas + the ✎ amber editable hint + that Sales is read-only.

**Verified live** (PB-MGT 2026-01): `/wc-row-save` with target_expenses=200000, gst_target=40000, commission_target=50000, wc_adjustment=5000 returns success=True and creates the mirrored INTRA CENTER ADJUSTMENT expense row. Reset to zero restored cleanly. `/wc-table` continues to return correct rows.

⚠️ **Deploy required** to push to `intra.purnabramha.com`.

---



### [2026-02-18 — Month-wise Working Capital Overview Grid restored in Overview tab] (P1)

User feedback: *"Add the old Overview screen back in grid format with columns Month / Opening WC / Sales / GST / Expenses / Commissions / Net Available / Revenue Share Base / Closing WC / Remarks · totals row · Download PDF (landscape with logo + signature) + Excel."*

**Implementation** — backend was already fully built (`/api/center-accounts/wc-table` returns month-wise rows; export-pdf/excel already produce landscape PDF with Purnabramha logo, account-manager signature, and download date). The missing piece was the **frontend grid display** inside the Overview tab.

**Created** `/app/frontend/src/components/WCOverviewGrid.jsx`:
- Self-contained card with: header (Base WC, Current WC, status badge), **Download PDF + Excel buttons**, and a 10-column grid.
- Columns: Month · Opening WC · Sales · GST · Expenses · Commissions · Net Available · Revenue Share Base · Closing WC · Status.
- **Totals row directly under the table header** (per user spec — "if total is not possible at bottom, then show total under the header row") with each numeric column summed and **bold**.
- Per-row status pill (active / restoring / blocked) with semantic colours.
- Footer caption explaining the Net Available and Revenue Share Base formulas.
- Loading + empty states.
- Test ids on every interactive element + row + total cell for QA automation.

**Wired into** `CenterAccounts.jsx` → Overview tab, just above the footer-hint paragraph. Existing tabs and KPI tiles remain untouched (user requested "Do not remove existing tabs or reports").

**Verified live** on PB-MGT — `/wc-table` returns 1 row with all expected keys; PDF (2.3 KB, application/pdf) and Excel (5.4 KB, with "Purnabramha — Working Capital Statement" title + center + Base WC header) downloads both work cleanly.

⚠️ **Deploy required** to push to `intra.purnabramha.com`.

---



### [2026-02-18 — Inter-Center Transfer Attendance Dashboard Bugs Fixed] (P0)

User feedback (production): *"LAUNG transferred PB-HSR → PB-KAL (Active, Temporary, June 1). But in HSR attendance LAUNG still showing as Absent, in PB-KAL attendance dashboard LAUNG not showing at all."*

**Root causes** in `routes/attendance_dashboard.py:get_monthly_grid`:
1. ❌ **TRANSFERRED_IN was entirely missing** — endpoint only handled OUT employees. Destination centers never saw incoming transfers.
2. ❌ **No transfer-window masking** — HOME employees were shown as Absent on dates inside their transfer window (should be "Shifted Out").
3. ❌ **Employee lookup was case-sensitive** — `find_one({"name": "LAUNG"})` missed stored "Laung" / mixed-case names → transferred employee silently dropped.

**Same root causes** existed in `routes/attendance.py:attendance_month` (legacy endpoint).

**Fix** (3 surfaces, single source of truth):
1. **`attendance_dashboard.py`** — Rebuilt the transfer-handling block: now builds `out_window_map` + `in_window_map` keyed by (center, employee_name) so the same lookup serves both directions. HOME loop masks attendance to `"OUT"` on dates inside the transfer window (does NOT count toward Absent stats). New **TRANSFERRED_IN injection loop** appends incoming employees to the destination center grid; attendance outside the window is rendered blank (employee still belongs to their original center on those days).
2. **`attendance.py:attendance_month`** — Same `_is_within` window-masking logic added for OLD center (set to `"OUT"`) and NEW center (set to blank outside window).
3. **`AttendanceDashboard.jsx`** — New `OUT` entry in `STATUS_STYLES` map → renders as a neutral grey "Shifted Out" pill so the UI clearly distinguishes a transfer absence from an actual Absent (red).
4. **Case-insensitive employee lookup** — `find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})` so transferred employees are surfaced regardless of how their name is cased in the `employees` collection.

**Verified live** (preview synthetic transfer JAYANTI PB-MGT → PB-DV, 2026-06):
- PB-MGT grid: JAYANTI shows `transfer_tag=TRANSFERRED_OUT`, all 30 days masked as "OUT" ✅
- PB-DV grid: JAYANTI shows `transfer_tag=TRANSFERRED_IN`, ready for KAL team to mark attendance ✅
- Center stats no longer over-count "Absent" for transfer windows ✅

**Tests**: 33/33 GST regression tests still PASS. Backend boots cleanly.

⚠️ **Deploy required** to push to `intra.purnabramha.com`.

---



### [2026-02-18 — Inter-Center Employee Transfer Salary / Attendance polish] (P1)

User feedback (production): Detailed spec for Attendance & Salary with Inter-Center Employee Transfer. Example: Prabhat (Hinjewadi → Kalyan, effective 15 June) should appear in Hinjewadi attendance for 1–15 June + Kalyan attendance for 16+ June, individual center salary counts only days at that center, and ALL-Centers salary merges into ONE row with "Centers Worked = Hinjewadi + Kalyan" and total days = 30.

**Investigation result**: Most of the spec was already implemented:
- ✅ `attendance_by_date` / `attendance_month` show employees per (date, center) using `get_transfer_status_for_center` — old center stops showing after transfer date, new center starts showing.
- ✅ Attendance history NEVER overwritten — every `attendance` doc keyed by `(date, center, employeeName)`.
- ✅ `salary_preview` and `generate_salary` per-center mode only count attendance with matching `center==target_center`.
- ✅ `salary_preview` / `generate_salary` ALL mode deduplicates employees and counts all attendance.

**Gaps closed in this iteration** (`routes/payroll.py` + `pages/Salary.jsx`):

1. **`CENTERS_WORKED` column added** to the Excel (ICICI upload format) — shows the actual distinct centers an employee worked at this month (e.g. *"HINJEWADI + KALYAN"*). In per-center mode, shows just that center.
2. **`centersWorked` field added** to the `salary_preview` JSON response — frontend reads this directly.
3. **Frontend Salary table** — in ALL mode, the Center column header reads "Centers Worked" and renders each center as its own Badge so transferred employees stand out at a glance.

**Verified live (PB-MGT, 2026-06)** — `/api/salary_preview` returns `centersWorked` field on each row; `/api/generate_salary` Excel has `CENTERS_WORKED` as column 14.

**Tests**: 33/33 GST tests still PASS. Lint clean for backend; frontend warnings pre-existing.

⚠️ **Deploy required** — push to `intra.purnabramha.com`.

---



### [2026-02-17 — Excel-style column filters: master "Select all" toggle + "Only" shortcut] (P1)

User feedback (production): *"the filters are not working for unselect all coz if i have to select only one then i have to unselect each of them one by one — just give this filter same as excel filters"*

**Root cause** (`ColumnFilterMenu.jsx`): The "Select all" link only ever added items. Clicking "Clear" produced `selected = new Set()` (size 0), which the rendering logic interpreted as "no filter → all checked" — so unchecked items immediately re-appeared as checked. The user had to manually uncheck 14+ items to keep only one.

**Fix** — true Excel-style filter UX:

1. **Master "Select all" checkbox** at the top (tri-state: ☑ all / ☐ none / ▣ some). Clicking it TOGGLES every visible item: if everything is checked, one click clears all → user picks the one they want. If some are checked, one click selects all visible.
2. **"Only" shortcut** — hover any item → "Only" link appears → one click filters to just that value. Excel power-user pattern.
3. **Tri-state rendering** distinguishes three legitimate states cleanly:
   - `selected == null` → no filter applied yet → render all checked (Excel default)
   - `selected.size === 0` → user explicitly cleared → render all unchecked (so they can pick from scratch)
   - `selected.has(key)` → standard per-item membership
4. **Search "(filtered)" hint** so user knows their toggle only affects items matching the search term.

**Where it surfaces**: Every column filter that uses `ColumnFilterMenu` — Expense Entry (Category, Description, Mode, Amount, Date), Sales Dashboard, and any future use. Single source of truth — fix once, applies everywhere.

⚠️ **Deploy required** to push to `intra.purnabramha.com`.

---



### [2026-02-17 — All "Coming Soon" reports shipped + Expense Attachments in CA Bundle] (P0)

User feedback (production):
1. *"CA Bundle should have Expense Attachments"*
2. *"Please generate all this coming soon report with view option for bills give zip folders: Profit & Loss, MG Summary, Payout Summary, PhonePe Reconciliation, GST Paid, Missing Bills, Expense Attachments"*

**Build summary**: Created new `utils/extra_reports_pdf.py` with 6 PDF builders + `routes/extra_reports.py` with 7 new endpoints. Frontend report tiles updated to remove all "Coming Soon" badges.

| # | Report | Endpoint | Notes |
|---|---|---|---|
| 1 | **Profit & Loss PDF** | `POST /api/extra-reports/profit-loss` | Cash-basis P&L: Sales − GST − Commissions − Adjusted Expenses |
| 2 | **MG Summary PDF** | `POST /api/extra-reports/mg-summary` | Month-wise MG vs RS comparison + total MG top-up; landscape; auto-skips when MG not applicable |
| 3 | **Payout Summary PDF** | `POST /api/extra-reports/payout-summary` | Month-wise Payable / Paid / Pending with totals row |
| 4 | **PhonePe Reconciliation PDF** | `POST /api/extra-reports/phonepe-recon` | Daily Online Sale vs PhonePe/UPI portion + variance column |
| 5 | **GST Paid PDF** | `POST /api/extra-reports/gst-paid` | GST collected vs GST PAYMENT expenses; net liability |
| 6 | **Missing Bills PDF** | `POST /api/extra-reports/missing-bills` | Compliance audit list — expenses without attachments (Indian Rule 6F + AU ATO context) |
| 7 | **Expense Attachments ZIP** | `POST /api/extra-reports/expense-attachments-zip` | Every uploaded bill/invoice for the month + `_attachments_index.csv` + `_missing_bills.csv` + manifest |

**Verified live (PB-PERTH 2026-02)** — all 7 endpoints return 200 OK with correct content-type (PDF / ZIP).

**CA Bundle ZIP now contains 10 files** (was 7): Cover PDF + Sales/Expense XLSX + PIB PDF + GST Summary PDF + Commission Reconciliation PDF + Bank Reconciliation PDF + **Profit_Loss PDF** + **Missing_Bills PDF** + **Expense_Attachments ZIP** + engine manifest. Each artefact still fetched defensively so a single missing input gracefully skips that one report.

**Tests**: 33/33 backend regression tests PASS. Backend boots cleanly.

⚠️ **Deploy required** — Push to `intra.purnabramha.com`.

---



### [2026-02-17 — MG Payout Totals row + Per-Franchise Owner Share aggregate] (P1)

User feedback:
1. *"For each head can we have total amount on top of the grid just below this line: Total Sales | GST | Commissions | ⭐ Revenue Share Base | Revenue Share Payout @ 10% | MG | Type | Payable | Paid | Pending | Status | Action"*
2. *"Should get the franchise owners revenue/profit share % from franchise management, either revenue or profit share, and MG active or not active from franchise management for all centers"*

**Fixes**:

1. ✅ **MG Payout grid TOTAL row** (`CenterAccounts.jsx`) — Added an amber-highlighted sticky "TOTAL" row at the top of the monthly-data table summing every numeric column (Total Sales, GST, Commissions, Revenue Share Base, Revenue Share Payout, MG, Payable, Paid, Pending). Now visible without scrolling. `data-testid="mg-payout-totals-row"` + per-cell test ids (`totals-total-sales`, `totals-gst`, etc.) for QA.

2. ✅ **MIS Dashboard Owner Share** (`mis_dashboard.py` + `MISDashboard.jsx`) — Was hard-coded to 15% × Revenue Share Base in the "All Centers" view, ignoring each franchise's actual %, payout model, and MG applicability.
   - **Backend**: New per-(center, month) aggregation runs each pair through `compute_franchise_payout` using the **franchise master**'s own `franchise_owner_share_percentage`, `payout_model` (revenue_share / profit_share), `mg_calculation_applicable`, `monthly_mg`, AND the per-month GST Treatment toggle. Returns 4 new fields:
     - `summary.owner_share_amount` — sum of each franchise's correct share
     - `summary.owner_share_pct_weighted_avg` — sales-weighted average % across centers
     - `summary.payout_model_breakdown` — `{revenue_share, profit_share, mg}` amounts
     - `summary.mg_active_centers` — count of franchises with MG enabled
   - **Frontend**: Reads `owner_share_amount` directly when `selectedCenter === "all"`. KPI label now reads *"Owner Share (per-franchise · avg X%)"* so users know the % is weighted across multiple centers. Single-center view unchanged (still uses that center's franchise %).

**Verified live** (preview DB has uniform 15% franchises so delta = 0; on production with mixed 10/15/20/80% franchises the aggregate will now correctly reflect each center's own settings).

**Tests**: 33/33 GST + AU net-revenue tests PASS. Backend imports cleanly.

⚠️ **Deploy required** to push to `intra.purnabramha.com`.

---



### [2026-02-17 — DoorDash column + Rich ZIP Bundles] (P0)

User feedback (production):
1. *"Sales_Expense_PB-PERTH_2026-05.xlsx is not loading doordash entry for perth center only zomato and swiggy is coming"*
2. *"CA Bundle should contain All Ledgers (PDF + Excel), Bills / Attachments, P&L, GST Summary, Bank & Commission Recon, Engine-snapshot manifest"*
3. *"Full Center Package should contain All Reports, All Ledgers, Payout Summary, Executive cover-sheet + engine manifest"*

**Fixes**:

1. ✅ **`utils/sales_expense_excel.py`** — Added missing **DoorDash** column (between Zomato and Online Other) + handled both `doordash_sale` and legacy `doordash` field names. Also fixed Swiggy/Zomato to read both new/legacy field names so AU centers consistently show all three aggregators. Verified on PB-PERTH 2026-02: Swiggy A$2,627, Zomato A$31, **DoorDash A$7,053.66** (previously zero/hidden).

2. ✅ **`routes/bundles.py`** — Refactored `_build_rich_bundle_zip` to aggregate ALL expected artefacts into a single ZIP. Each artefact is fetched defensively (try/except) so a missing link (e.g. franchise not yet wired) gracefully skips that PDF instead of breaking the download.

| Bundle | Contents (verified live PB-PERTH 2026-02) |
|---|---|
| `/api/bundles/ca` (CA Bundle) | Cover PDF + **Sales_Expense XLSX** + **PIB PDF** + **GST_Summary PDF** + **Commission_Reconciliation PDF** + **Bank_Reconciliation PDF** + manifest (7 files, 167 KB) |
| `/api/bundles/owner` (Owner Bundle) | Cover PDF + Sales_Expense XLSX + PIB PDF + manifest (4 files, 157 KB — kept lean for franchise owner) |
| `/api/bundles/franchisor` (**FullCenter Package**) | Franchisor cover PDF + Sales_Expense XLSX + PIB PDF + GST_Summary PDF + Commission_Reconciliation PDF + Bank_Reconciliation PDF + manifest (7 files, 167 KB — one-click everything) |

3. ✅ **Engine manifest** — now lists every contained artefact + the engine snapshot (revenue/profit share base, owner/company %, payable, source-of-truth pointer) so auditors can verify each PDF was generated from consistent numbers.

**Tests**: 42/42 backend tests PASS. Lint clean.

⚠️ **Deploy required** — Push to `intra.purnabramha.com` for production users.

---



### [2026-02-16 — GST Toggle propagated EVERYWHERE (codebase-wide sweep)] (P0)

User feedback: *"is there anywhere like in reports zip folder bundles on any screen has got this issue please and solve it for once coz i cant chk it everwhere"*

Comprehensive sweep + fix of every surface that touched `net_revenue`, `profitability`, or `revenue_share_base` so the per-month GST Treatment toggle works **everywhere** — UI screens, PDFs, Excel exports, and ZIP bundles.

**Surfaces audited & fixed**:

1. ✅ `routes/center_accounts.py` — Summary API & PIB Generator (was the original bug; fixed earlier).
2. ✅ `routes/center_health.py` — **Center Health Dashboard** Net Revenue / Net Profit now honor the toggle. Bonus fix: pre-existing typo `total_gst` → `gst_amount` (GST was being read as `None` for years).
3. ✅ `routes/mis_dashboard.py` — **MIS Dashboard** Revenue Share Base now sums per-(center,month) GST only for pairs NOT on Include mode. AU centers no longer over-deduct GST in aggregate KPIs.
4. ✅ `routes/daily_text.py` — **Sales Text Generator** Net Revenue honors the toggle when the period is contained in a single month. Multi-month spans fall back to legacy (toggle is per-month).
5. ✅ `utils/pdf_generator.py` — **PIB PDF Section 4** no longer adds GST back to `net_revenue` (since `net_revenue` itself is now toggle-aware). **MG Payout PDF + Excel** TOTAL row now sums per-month `revenue_share_base` instead of recomputing `Sales − Comm − GST`.
6. ✅ `routes/bundles.py` — **CA/Owner/Franchisor ZIP Bundles** already used the engine correctly; verified live both modes produce the right Revenue Share Base.
7. ✅ `routes/ledgers.py` — Franchise Ledger PDF already toggle-aware (Feb-2026 first pass).
8. ✅ `routes/owner_reports.py` — Already correct (uses shared GST helper with the flag passed through).
9. ✅ Frontend (`CenterAccounts.jsx`, `CenterHealth.jsx`, `OwnerReports.jsx`, `ExpenseAdjustmentsTab.jsx`, `MISDashboard.jsx`) — all read `net_revenue` / `profitability` / `revenue_share_base` directly from backend; no local recompute → propagates automatically.

**Verified live on PB-PERTH 2026-02 (Sales A$31,183 · GST A$1,951.94 · Comm A$2,172.52 · AdjExp A$175)**:

| Surface | Toggle OFF | Toggle ON | Delta |
|---|---:|---:|---:|
| Center Accounts Net Revenue | A$27,058.54 | **A$29,010.48** | +A$1,951.94 (GST) |
| Center Accounts Profitability | A$26,883.54 | **A$28,835.48** | +A$1,951.94 |
| Center Accounts Revenue Share Base | A$29,010.48 | A$29,010.48 | (was already toggle-aware) |
| Center Health Net Revenue | A$27,058.54 | **A$29,010.48** | +A$1,951.94 |
| Center Health Net Profit | A$26,883.54 | **A$28,835.48** | +A$1,951.94 |
| CA Bundle ZIP Revenue Share Base | A$29,231.06 | **A$31,183.00** | toggle-aware ✅ |

**Invariant** (now holds end-to-end for AU centers): `Net Revenue ≡ Revenue Share Base ≡ Sales − Commissions` in Include-GST mode. Profitability = Net Revenue − Adjusted Expenses.

**Tests**: 42/42 PASS (engine + AU/India parser + GST treatment unit + AU net-revenue regression suite). Lint clean for all modified files.

⚠️ **Deploy required** — Push to `intra.purnabramha.com` for production users to see these fixes.

---



### [2026-02-16 — AU Net Revenue & Profitability fixed for "Include GST" mode] (P0)

**Reported bug** (PB-PERTH 2026-05):
- Revenue Share Base = AUD 42,138.65 ✅ (correct under Include-GST toggle)
- Net Revenue = AUD 38,447.35 ❌ (still subtracting GST)
- Profitability = AUD −839.99 ❌ (negative because Net Rev was wrong)

**Root cause**: `routes/center_accounts.py` AU branches (summary endpoint line ~1577 and PIB section ~3438) had `net_revenue = total_sale − total_commission − sales_gst_amount` hard-coded — they ignored the per-center per-month `include_gst_in_revenue` toggle. Only the Revenue Share Base formula honored it.

**Fix**:
- Fetch `include_gst_in_revenue_flag` upfront (before AU/India branching) so both Net Revenue and Revenue Share Base use the same value.
- AU summary endpoint: `if flag: net_revenue = sales − commission` (no GST), else legacy formula. `profitability = net_revenue − adjusted_expenses` flows automatically.
- AU PIB section: same conditional formula, plus `net_revenue_for_share = max(0, net_revenue − adjusted_expenses)` propagation.
- India branch unchanged (already correctly using engine + toggle).

**Verified live** PB-PERTH 2026-02 (Sales A$31,183 · GST A$1,951.94 · Comm A$2,172.52 · AdjExp A$175):

| Mode | RSB | Net Revenue | Profitability | Δ Net Rev vs Exclude |
|---|---:|---:|---:|---:|
| Exclude (default) | A$29,010.48 | A$27,058.54 | A$26,883.54 | — |
| Include (toggle ON) | A$29,010.48 | **A$29,010.48** ✅ | **A$28,835.48** ✅ | +A$1,951.94 = GST |

Symmetry invariant holds: Net Revenue ≡ Revenue Share Base in Include-GST mode. Profitability ≡ RSB − AdjExp. 80/20 profit share now computes against the correct base.

**Tests**: 42/42 PASS (new `tests/test_au_net_revenue_gst_toggle.py` + all existing GST/parser suites).

⚠️ Deploy to push to `intra.purnabramha.com`.

---



### [2026-02-16 — GST Toggle propagation: PIB PDF + Franchise Ledger PDF] (P0)

Extended the per-center per-month GST Revenue Treatment toggle into PDF outputs so PIB and Franchise Ledger PDFs match the on-screen numbers exactly.

**PIB PDF** (`utils/pdf_generator.py`):
- Section 4 "Financial Summary" — when `include_gst_in_revenue=True`, the GST line stays informational (`"GST on Eligible Sales (5%) — informational"`) instead of being subtracted from Net Revenue. Revenue Share Base formula caption switches to `"(Sales − Commissions) [Include-GST mode]"`.
- Section 5 "Operational Sustainability — Revenue Share Base" — same treatment: GST row labelled either `"Less: GST on Eligible Sales"` (Exclude) or `"GST on Eligible Sales — informational only"` (Include). Section header switches to `"Revenue Share Base — Include-GST mode (Sales − Commissions)"` when toggle is on.
- For Australia centers on Include-GST mode the section 4 chain also reflects the AU-specific "Sales − Comm − Comm GST" formula (no GST subtraction).

**Franchise Ledger PDF** (`routes/ledgers.py`):
- Per-month iteration now tracks `period_gst_deducted` separately from `period_total_gst_on_sales` — only sums GST into the deducted bucket when the month is NOT on Include-GST mode.
- New `period_totals.total_gst_deducted_from_base` and `period_totals.months_include_gst` fields surfaced via the API.
- "Revenue Share Base Calculation" table in PDF now shows two GST rows when some months are on Include mode: `"Less: GST on Eligible Sales (deducted)"` for months where it was, and `"GST on Eligible Sales — informational (Include-GST mode, N month/s)"` for months where it wasn't. This keeps the bottom-line `eligible_rev_share_base` accurate while clearly disclosing which months were on which method (audit-friendly).

**Email/WhatsApp text (`routes/daily_text.py`)** — already correct: only prints "GST on Eligible Sales" as a line item within Net Revenue, doesn't deduct from a share base. No changes needed.

**Test status**: 25/25 PASS unchanged (10 engine + 6 API + 5 AU + 4 India parser). Lint clean for `pdf_generator.py`. Backend running.

⚠️ Deploy to push to `intra.purnabramha.com`. Once deployed, generate a PIB PDF for any AU center with the toggle ON — the GST row will show as informational and the Revenue Share Base header will read "[Include-GST mode]".

---


### [2026-02-16 — GST Revenue Treatment: dynamic Total Deductions everywhere] (P0)

**Follow-up to the earlier GST toggle feature.** User clarified the toggle must also reshape **Total Deductions** and its label across every surface — not just the Revenue Share Base.

Spec:
- **Option 1 (Exclude GST)** — `Total Deductions = Commissions (incl GST) + GST on Eligible Sales`
- **Option 2 (Include GST)** — `Total Deductions = Commissions (incl GST)` only (GST removed from deductions but still displayed separately)
- Same reconciliation invariant in both modes: `Revenue Share Base + Total Deductions = Total Sales`.

**Implementation**
- `routes/center_accounts.py` — `share_calculation.total_deductions` now equals `total_commission_with_gst + (0 if include_gst_in_revenue else sales_gst_amount)`. New fields `share_calculation.total_deductions_label` and `share_calculation.include_gst_in_revenue` propagated to FE.
- `frontend/src/pages/CenterAccounts.jsx` — Overview KPI tile *"Total Deductions"* and Commissions tab tile *"Total Deductions (incl. GST)"* now read **backend-computed** `share_calculation.total_deductions` + `total_deductions_label`. Local fallback preserved for safety. Data-testids added: `commissions-total-deductions`, `commissions-total-deductions-label`, `kpi-total-deductions-label`.

**Verified live** for PB-HSR / 2025-12 (Sales ₹9,91,876 · GST ₹42,250.57 · Comm ₹0):

| Mode | Total Deductions | Label | RS Base |
|---|---:|---|---:|
| Exclude (default) | **₹42,250.57** | `Commissions (incl GST) + GST on Eligible Sales` | ₹9,49,625.43 |
| Include | **₹0.00** | `Commissions (incl GST)` | ₹9,91,876.00 |

Δ Total Deductions == GST · Δ RS Base == GST · Sales − Deductions reconciles in both modes ✅

**New test**: `test_total_deductions_changes_with_toggle` in `tests/test_gst_treatment_api.py`. Full suite **25/25 PASS** (10 engine unit + 6 API integration including new test + 5 AU + 4 India parser).

⚠️ Click **Deploy** to push to `intra.purnabramha.com`.

---


### [2026-02-16 — GST Revenue Treatment Toggle (per-center, per-month)] (P0)

**User spec**: For AU centers, GST collected from sales is not immediately remitted — it sits with the business until the filing period. Reducing the Revenue Share Base by GST every month therefore mis-states operational position. Build a per-center per-month toggle in **Center Accounts → Adjustments** that switches between:
- **Option 1 (default, current behaviour)** — `Revenue Share Base = Sales − GST − Commissions`
- **Option 2 (opt-in)** — `Revenue Share Base = Sales − Commissions` (GST stays separately visible in every report — *only the share-base treatment changes*).

The toggle must auto-apply across Center Overview, MG Payout, Profit & Loss, Revenue Share, Profit Share, Settlement Summary, CA Bundle, Email Package, all Reports & Ledgers — no manual recalculation, no GST ever hidden.

**Implementation**

*Backend* (single financial engine wiring):
- `utils/financial_engine.py` — `compute_revenue_share_base(...)` and `compute_franchise_payout(...)` now accept `include_gst_in_revenue: bool = False`. Returned payload exposes `include_gst_in_revenue` + `gst_treatment_label`.
- `utils/gst.py` — same `include_gst_in_revenue` parameter added to the shared helper (India + AU branches).
- `routes/center_accounts.py`:
  - New endpoints **`POST /api/center-accounts/gst-treatment/get`** and **`/set`** (modelled on `protection-gating`). Persists to MongoDB collection **`gst_treatment_overrides`** keyed by `(center_code, month)` with `updated_at` + `updated_by` audit fields.
  - New helper `get_gst_treatment_flag(center, month)` called from every callsite (summary engine call, operational_sustainability block, PIB generation branch).
  - `operational_sustainability` block now exposes `include_gst_in_revenue` + `gst_treatment_label` + dynamic `revenue_share_formula`.
  - `payout` block also mirrors `include_gst_in_revenue` + `gst_treatment_label` for downstream consumers.
- `routes/bundles.py` — reads override + passes to engine for CA Bundle generation.
- `routes/ledgers.py` — reads override + passes to `compute_revenue_share_base` in the Ledger period loop.
- `routes/owner_reports.py` — reads override + passes to share-base helper.

*Frontend* (`/app/frontend/src/pages/CenterAccounts.jsx`):
- New `GSTRevenueTreatmentCard` component (lines 107-247) rendered at the top of the **Adjustments tab**.
- Auto-display tiles: Gross Sales · GST Collected From Sales · Commissions (sourced from `operational_sustainability`).
- Dropdown with both options. Save is automatic on change → toast → re-fetches summary so every other tab/PDF/email reflects the new base instantly.
- Live "Resulting Revenue Share Base" preview tile shows the active formula and amount.
- Audit line shows `updated_by` and `updated_at`.
- Data-testids: `gst-revenue-treatment-card`, `gst-card-gross-sales`, `gst-card-gst-collected`, `gst-card-commissions`, `gst-treatment-select`, `gst-treatment-updated`, `gst-treatment-base-preview`, `gst-treatment-base-amount`.

**Test coverage** — 24/24 PASS

| Suite | File | Count |
|---|---|---|
| Engine unit tests | `tests/test_gst_revenue_treatment.py` | 10 |
| API integration | `tests/test_gst_treatment_api.py` *(testing agent)* | 5 |
| AU parser regression | `tests/test_commission_parser_au.py` | 5 |
| India parser regression | `tests/test_commission_parser_india.py` | 4 |

Frontend verified by `testing_agent_v3_fork` on PB-HSR/2025-12 (Gross ₹9,91,876, GST ₹42,250.57 → base flips from ₹9,49,625.43 to ₹9,91,876.00 on toggle; owner share Δ = GST × owner_pct).

**Rules honoured**
- ✅ Center-specific + month-wise persistence
- ✅ Editable by Super Admin / Accounts Team (auth via `check_access`)
- ✅ GST always remains visible in every report — only the base formula changes
- ✅ Applies automatically to all reports/ledgers without manual recalculation
- ✅ Profit Share Base is unaffected (GST never deducted there)

⚠️ Click **Deploy** to push to `intra.purnabramha.com`.

---


### [2026-02-16 — Australia Commission Parsers (DoorDash gross + Cards/ANZ Worldline EDC + ANZ Bank Statement)] (P0)

**User report**: For PB-PERTH (Australia center) two bugs:
1. Uploaded DoorDash payout summary showed **"Gross Amount: AUD 0.00"** even though Net Payout = AUD 1,222.29 (5 deduction fields missing context).
2. Cards upload (ANZ Worldline EDC + ANZ Business Essentials bank statement) failed with:
   *"Failed to parse file: Could not find transaction header in bank statement. Expected columns: Transaction Date, Particulars, Credit, Debit."*

**Root causes**:
1. `parse_doordash` used `df.get("Subtotal including GST")` — **lowercase 'i'**; the file ships the column as `"Subtotal Including GST"` (capital I). `df.get()` is case-sensitive → returned empty → sum = 0.
2. `parse_cards` expected HDFC India layout (`Date` / `Amount` / `Status` columns starting at row 0). ANZ Worldline EDC has 5 metadata rows on top and uses `Transaction date`, `Gross amount`, `Status`, `Surcharge amount`, `Amount excluding surcharge`.
3. Bank-statement matcher expected HDFC layout (`Transaction Date` / `Particulars` / `Debit` / `Credit`) and an embedded `SETDT-DDMMYYYY` settle date in particulars. ANZ Business Essentials uses `Date` + `Transaction Details` (merged into one cell on Layout A, separate cells on Layout B) + `Withdrawals` + `Deposits`, and settles via `ANZ TRANSACTIVE DIRECT CREDIT ANZ WORLDLINE …` / `… AMEX GR …` patterns.

**Implementation** — single file: `backend/routes/commission_parser.py`
- Added `find_col_ci()` + `col_sum_ci()` for case-insensitive column matching.
- Added `_load_bank_statement_normalized()` returning a unified `{date, particulars, debit, credit}` DataFrame; handles **both HDFC India and ANZ Australia** layouts (including ANZ's two row variants and year inference from header metadata).
- Added `_load_cards_edc()` that auto-detects HDFC vs ANZ Worldline EDC format (dynamic header-row scanning) and sets currency to `AUD` for ANZ.
- Rewrote `parse_doordash` with case-insensitive lookup + full deduction breakdown (commission, marketing fees, customer discounts funded by you, error charges, adjustments, tax remitted).
- Rewrote `parse_cards` to:
  - Run on either EDC format.
  - **Prefer ANZ Worldline's per-txn `Surcharge amount` column as MDR ground truth** (`mdr_source = "edc_surcharge_column"`). Falls back to `bank_diff` when only HDFC files are uploaded.
  - Clamp `net_payout` ≤ `gross_amount` (defensive — you can't bank more than you collected).
  - Persist `currency: "AUD"` for ANZ format end-to-end (UI already reads it).

**Verified live via API** (POST `/api/center-accounts/upload-commission-excel`):
- DoorDash → Gross AUD 2,163.21 · Other AUD 940.92 · Net AUD 1,222.29 · 4 orders ✓
- Cards + ANZ bank → Gross AUD 35,370.05 · MDR AUD 380.31 (1.08 %) · Net AUD 34,989.74 · 542 settled txns · 53 bank settlements matched ✓

**Tests added** (`/app/backend/tests/test_commission_parser_au.py` — 5/5 PASS):
- `test_doordash_au_parse` — gross/net/other reconciliation
- `test_cards_anz_edc_only` — Surcharge → MDR for AU
- `test_cards_anz_with_bank_reconciliation` — end-to-end + `mdr_source` assertion
- `test_anz_bank_statement_normalisation` — Apr→Jun parsing + card-settlement detection
- `test_anz_cards_edc_loader_dynamic_header` — header-row auto-detect

Fixture files: `/app/backend/tests/fixtures_au/{dd_au,cards_au,bank_au}.xlsx`

⚠️ Click **Deploy** to push to `intra.purnabramha.com` — Preview only until deployed.
Previously-uploaded DoorDash records in DB will still show `gross=0` until re-uploaded.

---


### [2026-02-16 — Center Accounts 5-Tab Restructure — Phases A + B + C + D] (P0)

**User directive** (Message 324, re-issued 327): Eliminate every standalone dashboard / duplicate report and collapse the Center Accounts page to **exactly 5 tabs**: Overview · MG Payout · Reports · Ledgers · Bundles & Exports. One Single Financial Engine driving every screen. No duplicate calculations. Each report shows only its own purpose.

**Implementation (delivered in one session)**:

`frontend/src/pages/CenterAccounts.jsx`:
- TabsList replaced — old 11 tabs ➜ exactly 5 (`tab-overview`, `tab-mg-payout`, `tab-reports`, `tab-ledgers`, `tab-bundles`).
- **Tab 1 Overview** — rebuilt from scratch as an 11-tile KPI grid (Gross Sales · GST · Commissions · Expenses · Adjustments · Revenue Share Base · Profit Share Base · PBT · WC · MG · Payout). Each tile has a stable `overview-tile-{key}` data-testid. Header strip surfaces Payout Model badge.
- **Tab 2 MG Payout** — `value="payout"` renamed to `value="mg-payout"`, content preserved (MG vs share comparison, payout determination, monthly grid).
- **Tab 3 Reports** — rewritten as 4 grouped sections (Financial · Settlement · Reconciliation · Compliance) with 13 report tiles. Settlement tile flips between "Revenue Share Calculation (PIB)" / "Profit Share Calculation (PIB)" based on `payout_model`. Reports not yet implemented show a "Coming Soon" badge.
- **Tab 4 Ledgers** — `LedgersTab.jsx` internally re-grouped into 3 sections (Financial · Franchise · Adjustment). LEDGER_CATALOG gained a `group` field; new LEDGER_GROUPS array drives 3 sub-sections (`ledger-group-financial` / `-franchise` / `-adjustment`). Re-categorised existing 10 ledgers; renamed "P&L" → "General Ledger (P&L)", "Loans" → "Settlement Ledger", "Cash/Bank Book" → "Cash/Bank Ledger" per spec.
- **Tab 5 Bundles & Exports** — rewritten as exactly 3 cards (CA Bundle / Email Package / Full Center Package). Each card has a "Contains" list + download button. CA → `/api/bundles/ca`, Email Pack → existing `openEmailPack()`, Full Center → `/api/bundles/franchisor`.
- **Dead code cleanup**: 6 orphan `<TabsContent>` blocks (sales, commissions, share, insights, health, adjustments) deleted — ~63 KB / 850 lines removed. File shrunk 3811 → 2965 lines (−22 %).

`backend/routes/center_accounts.py`:
- `PIBGenerateRequest` and `EmailPackRequest` now accept `period` as alias for `month` (forward-compat with new callers that use the spec field name).

**Tests (38/38 PASS)**:
- `test_payout_model_strict_pdf.py` (2)
- `test_iter91_5tab_strict_wording.py` (2 — NEW: live PIB PDF + Email Pack body extraction confirms no "Profit Share" leak on a Revenue-Share franchise)
- `test_financial_engine.py` (14)
- `test_entity_naming.py` (7)
- `test_share_calculation_base.py` (4)
- `test_bundle_generator.py` (7)
- `test_wc_protection_base_display.py` (2)

**testing_agent iteration_91**: 100 % structural pass on frontend (5/5 tabs · 11/11 overview tiles · 13/13 report tiles · 3/3 ledger groups · 3/3 bundle cards) + 100 % strict-wording pass on backend.

⚠️ Click **Deploy** to push to `intra.purnabramha.com` — Preview only until deployed.

---


### [2026-02-16 — Strict Model Wording Sweep — All Surfaces] (P0)

**User report**: Despite previous fixes, the Center Accounts share-split cards still showed generic "Franchise Owner Share" / "Manaswini Foods Pvt Ltd Share" / "Total Payable", and the PIB PDF title still read **"Profit & Income Balance Report"** even when the franchise was set to Revenue Share. User was emphatic: when model is Revenue Share, EVERY label must say "Revenue Share"; same for Profit Share — including the calculation rows.

**Fix (one pass, all surfaces)**:

`backend/utils/entity.py` — added 3 helpers (`model_share_phrase`, `entity_model_share_label`, `owner_model_share_label`) so the model phrase ("Revenue Share" / "Profit Share") is appended consistently.

`backend/utils/financial_engine.py` — `company_entity_label` now returns "Manaswini Foods Pvt Ltd Revenue Share" / "... Profit Share" by model.

`backend/utils/pdf_generator.py` — PIB title flips between **"Revenue & Income Balance Report"** and **"Profit & Income Balance Report"**. Section 7 rows now say "FRANCHISE OWNER REVENUE SHARE" / "MANASWINI FOODS PVT LTD REVENUE SHARE" (and "... PROFIT SHARE" for profit centers). Section 8 overseas rows and Section 8B base-row labels are model-aware.

`backend/utils/bundle_generator.py` — CA / Owner / Franchisor bundle PDFs: share-calculation table rows ("Franchise Owner Revenue Share" / "<Entity> Revenue Share") + executive summary rows model-aware.

`backend/routes/center_accounts.py` — Email Pack attachments line now reads "1. PIB Report (Revenue & Income Balance)" or "(Profit & Income Balance)" by model. Subject was already model-aware.

`frontend/src/pages/CenterAccounts.jsx` — Share-split cards (Franchise Owner / Entity), Total Payable, WC status tile, Protection-Mode banner, Restoring banner, MG vs Share comparison card, Payout Badge label, italic distribution note, GST notice, MG & Payout KPI tiles ("Total Revenue Share", "Total Revenue Share Payout", subtitle "@ X% of Rev Share Base"), Month-wise table column headers, WC table "Rev Share" column header, PIB Preview Dialog footer tiles — ALL now switch wording based on `accountSummary.payout_model` / `share_calculation.type`.

**Live smoke test** (PB-SN · 2026-05 — a Revenue-Share franchise):
- PIB PDF title: `Revenue & Income Balance Report` ✓
- Section 7 rows: `FRANCHISE OWNER REVENUE SHARE`, `MANASWINI FOODS PVT LTD REVENUE SHARE` ✓
- Section 8B title: `8B. FINAL PAYOUT (Revenue Share + GST)` ✓
- Email subject: `Monthly Revenue Share Report · May 2026` ✓
- Email attachments: `1. PIB Report (Revenue & Income Balance)` ✓
- ZERO "Profit Share" leak anywhere in the rendered PDF or email body ✓

**Tests**: `tests/test_payout_model_strict_pdf.py` extended with title-brand-name + entity-label assertions for both models (2/2 pass). Full strict suite green (27/27).

⚠️ Click **Deploy** to push to `intra.purnabramha.com` — Preview only until deployed.

---


### [2026-02-16 — second pass] WC Protection Mode Display Consistency (P0)

**User report**: Section 7 of PIB and the Center Accounts page (e.g. PB-SN · 2026-05 in WC Protection) showed:
- Revenue Share Base = Rs. 13,60,891.94 (regular base)
- Franchise Owner 10% = Rs. 24,285.58 (10% of operational balance 2.42L, NOT 10% of 13.6L)
- Manaswini 90% = Rs. 2,18,570.20

The displayed base and the displayed share amounts were computed from two different bases → users could not reconcile the math (`10% × 13,60,891.94 ≠ 24,285.58`).

**Fix** (`routes/center_accounts.py`):
1. When `protection_mode=True`, set `net_revenue_for_share = max(0, operational_balance)` so the "Base for Calculation" row equals the base actually used.
2. Override `summary.base_label` to `"Operational Balance (Base under WC Protection)"` so the label tells the user why the base is gated.
3. PIB Section 7 (`utils/pdf_generator.py`) suppresses the redundant "(Base for Calculation)" suffix when the label already contains "Protection". Same suppression on the Center Accounts page (`CenterAccounts.jsx`).

**Net effect**: under WC Protection, Section 7 now reads:
```
Operational Balance (Base under WC Protection)        Rs. 2,42,856.00
FRANCHISE OWNER SHARE                       10.0%     Rs. 24,285.60
MANASWINI FOODS PVT LTD SHARE               90.0%     Rs. 2,18,570.40
```
Math is now visibly self-consistent. Section 7 title still includes `*** CLOSED - WC BELOW 50% ***` so users immediately see the gating cause.

**Tests**: `tests/test_wc_protection_base_display.py` (2 new tests) + 55/55 full unit suite green.

⚠️ Click **Deploy** to push to `intra.purnabramha.com`.

---

### [2026-02-16] Post-Phase-3 Stabilization — 3 P0 Bug Fixes + 1 Critical Data-Source Fix (P0)

**User report after deploying Phase 3**:
1. Bundle downloads returning **404** (CA / Franchisor dashboards passed `franchise_code`, backend expected `center_code`).
2. **PIB report rendered as "Profit Share"** even when the franchise was configured for Revenue Share.
3. **Profit Share math being computed/displayed** when the franchise was strictly on Revenue Share.

**Shipped fixes**:
1. **`backend/routes/bundles.py`** — new `_resolve_center_code()` helper accepts EITHER a `center_code` OR a `franchise_code` (resolves franchise → first linked active center). Unknown identifiers still return 401/404. **CRITICAL secondary fix**: switched the data source from the wrong `db.sales` collection to the canonical `db.daily_sales` + `db.monthly_commissions` (matching `routes/center_accounts.py`). Bundle Selected Base / Owner Share / Company Share now match the dashboard exactly (e.g. PB-HSR Dec-2025 = 949,625.43 / 142,443.81 / 807,181.62 across all surfaces).
2. **`backend/utils/bundle_generator.py`**: Executive Summary block is now model-aware (a Revenue-Share bundle never surfaces a "Profit Share Base" row, and vice-versa). Payout Calculation block reads `engine.base` (was `engine.selected_base`, which returned 0 since the engine doesn't emit that key — silent bug).
3. **`backend/utils/pdf_generator.py`** PIB Section 8 + 8B: "Franchise Owner Revenue/Profit Share" row label and "FINAL PAYOUT (Revenue/Profit Share + GST)" title flip strictly with `summary.payout_model`. Verified by extracting PDF text: toggling FR-TEST-INDIA between models flips every label cleanly.
4. **`backend/routes/center_accounts.py`** `get_center_account_summary`: default `payable_type` now derived from `engine_payload["payout_model"]` instead of hard-coded `"revenue_share"`. `payout.reason` uses the model word (`Profit Share (X) >= MG (Y)` vs `Revenue Share (X) >= MG (Y)`).
5. **`backend/routes/bundles.py`** auth: replaced sync-only `_verify_token` with async-with-Mongo-fallback (matches `routes/franchises.check_access`). Fixes intermittent 401s on multi-pod deployments where the per-process `otp_store` was invisible to a sibling pod.
6. **`frontend/src/pages/CADashboard.jsx` + `FranchisorDashboard.jsx`**: centers dropdown now sourced from `GET /api/centers` (the canonical list) instead of `POST /api/franchises/list`. This was the root cause of the 404 — the dashboards were passing franchise codes when the bundle endpoint expected center codes.

**Tests**:
- New: `tests/test_payout_model_strict_pdf.py` (2 PIB-text-extraction regressions enforcing label strictness for both Revenue Share and Profit Share scenarios).
- Testing agent: 8/8 HTTP integration tests pass (`tests/test_iter90_p0_post_phase3.py`).
- Full unit suite: 53/53 green.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. Production lags Preview until the user explicitly deploys.

---



### [2026-02-15] Phase 3 — 3 Master Dashboards + 3 Bundles + Legacy Sunset (P0)

**User directive** *Build 3 brand-new master dashboard pages (CA / Franchise Owner / Franchisor) consuming the engine exclusively. 3 PDF/ZIP bundles (CA / Franchise Owner / Franchisor). Sunset overlapping legacy reports.*

**Shipped**:
1. **`backend/utils/bundle_generator.py`** — single consolidated PDF generator with 3 builders (`build_ca_bundle_pdf`, `build_franchise_owner_bundle_pdf`, `build_franchisor_bundle_pdf`) and a `build_bundle_zip` wrapper that emits `PDF + manifest.txt`. Every number sourced from `compute_franchise_payout()`. The manifest is the audit trail (engine inputs + outputs + reference to `financial_engine.py`).
2. **`backend/routes/bundles.py`** — three GET endpoints:
   - `GET /api/bundles/ca?token=&center=&period=`
   - `GET /api/bundles/owner?token=&center=&period=`
   - `GET /api/bundles/franchisor?token=&center=&period=`
   All gated by `_require_valid_token()` (returns 401 for bad tokens — security fix from iteration 89). Returns `application/zip`.
3. **3 new dashboard pages**:
   - `frontend/src/pages/CADashboard.jsx` → `/dashboard/ca` — Accounts persona
   - `frontend/src/pages/FranchisorDashboard.jsx` → `/dashboard/franchisor` — Founder / Director persona
   - `/dashboard/franchise-owner` re-uses existing `FranchiseOwnerDashboard.jsx` with a new "Bundle" download button (`data-testid=fo-download-bundle-btn`)
4. **Sidebar nav** — `★ CA Dashboard` and `★ Franchisor Dashboard` added to Accounts group (Crown icon, super-admin-only for Franchisor).
5. **Legacy sunset** — `OwnerReports.jsx` gets a prominent amber deprecation banner pointing users to the new 3-bundle architecture. Page kept available for historical generation but flagged "(legacy)" in title.

**Architecture wins**:
- **Single source of truth** verified — testing agent's PDF text extraction proved bundles contain engine-computed `Revenue Share Base` & `Owner Share` verbatim + correct legal entity (`Manaswini` for India).
- **Manifest audit trail** every bundle ZIP includes a `_manifest.txt` listing Selected Base / Owner % / Owner Share / Company Entity + the source-file path. Auditors can re-derive figures without opening the PDF.
- **Security**: invalid/expired tokens → **401** (closed silent-bypass that returned valid downloads).
- **Schema correctness**: bundle resolver queries `centers` by `code` (not `center_code`) — matches the rest of the codebase (testing agent caught this P0 before it hit production).

**Tests**: 49/49 unit tests + 9/9 HTTP integration tests (test_bundles_endpoints.py) all green. Testing agent verdict: 100% backend + 100% frontend.

**Out of scope (still in Phase 3 backlog)**:
- Refactor split of `routes/center_accounts.py` (3376 lines) and `utils/pdf_generator.py` (1500+ lines) into focused modules. Deferred to a maintenance pass — current files work, refactor would not change any user-visible behaviour.
- Full removal of legacy Revenue Share / Profit Share / Email Pack PDFs. Today they remain available (with deprecation banner pointing to new bundles) so users can fall back during the transition.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. Post-deploy quick test:
1. Open Accounts → ★ CA Dashboard → pick a center + month → click "Download CA Bundle (.zip)" — should download `CA_<CENTER>_<PERIOD>.zip` containing a PDF + manifest.
2. Repeat for Franchisor Dashboard.
3. Inside Franchise Owner Dashboard, new green "Bundle" button next to "PDF" / "Export" — clicks download Owner Bundle ZIP.
4. /owner-reports page — see amber deprecation banner at the top.

---



### [2026-02-15] Financial Architecture Refactor — Single Engine + Per-Franchise Payout Model (P0)

**User directive** *Consolidate dozens of overlapping reports into a single source of truth. Each franchise must explicitly declare its Payout Model (Revenue Share / Profit Share). Rename the % field. Rebuild around 3 dashboards + 3 bundles.*

This commit ships **Phase 1 + Phase 2 of the refactor**.

**Phase 1 — Single Financial Engine + new franchise fields**

1. **`backend/utils/financial_engine.py`** — new pure-function module that owns every payout formula:
   - `compute_revenue_share_base(sales, commissions, gst)` → Sales − Comm − GST
   - `compute_profit_share_base(sales, commissions, expenses, wc_adj, manual_adj)` → Sales − Comm − Exp − Adj
   - `compute_franchise_payout(...)` → canonical payload (both bases, owner/company share, MG resolution, WC Protection gating, dynamic section heading + base label, country-aware company entity label).
2. **New franchise fields** (`routes/franchises.py`):
   - `payout_model` — `"revenue_share" | "profit_share"` (defaulted to India=`revenue_share`, Australia=`profit_share`, overridable).
   - `franchise_owner_share_percentage` — renamed from `revenue_share_percentage`. Both fields persisted in parallel; mirror-write keeps them in sync until legacy field retired.
   - `list_franchises` + `get_franchise` endpoints inject defaults for legacy rows so consumers always see populated values.
3. **Wiring** — `routes/center_accounts.py` (`get_center_account_summary`, `month_wise_payout_summary`) and `utils/pdf_generator.py` (Section 7) now read the canonical engine payload (`section_heading`, `base_label`, `engine{}`). Mirror layer keeps existing variables (`franchise_owner_share`, `purnabramha_share`, etc.) in sync so all downstream rendering continues to work unchanged.
4. **WC Protection Mode** — engine returns `revenue_share_protection` / `profit_share_protection` / `wc_protection_no_payout` payable types depending on model + operational balance, with model-aware reason text.

**Phase 2 — Dashboard alignment**

5. **Franchise Management UI** (`FranchiseManagement.jsx`):
   - New **Payout Model** dropdown (`data-testid=payout-model-select`) — Revenue Share / Profit Share.
   - **Franchise Owner Share %** label (renamed) with `data-testid=franchise-owner-share-pct-input`. Company Share % auto-computed = 100 − Owner %.
   - Summary card surfaces Payout Model + Franchise Owner Share % + Company Share %.
6. **MIS / Center Accounts / Franchise Owner Dashboards** all read `payout_model` from the franchise object. KPI tiles dynamically flip between "Revenue Share Base" and "Profit Share Base" depending on the model.
7. **PIB PDF Section 7** — heading + base label now driven by the engine. Same India center on Revenue Share shows "REVENUE SHARE CALCULATION"; switch to Profit Share and the same center's next PIB renders "PROFIT SHARE CALCULATION" with the Profit Share Base.

**Regression**: 
- `backend/tests/test_financial_engine.py` — 14 new tests (default model resolution, both base formulas, end-to-end engine, WC Protection cap, source-guards that pdf_generator + center_accounts must use the engine).
- `backend/tests/test_payout_model_engine_integration.py` (created by testing agent) — 12 HTTP integration tests covering CRUD persistence, dual-write mirror, model-switch flips section heading.
- Total: **42/42 unit + 12 integration = 54 tests all green.** Testing agent verdict: 100% backend + 100% frontend, no critical issues.

**Backwards compatibility — important**:
- Every legacy franchise (no `payout_model` / no `franchise_owner_share_percentage` field) keeps today's exact behaviour. `normalize_model()` defaults by country; readers prefer new field but fall back to legacy %.
- Mirror-write on create/update keeps both `revenue_share_percentage` and `franchise_owner_share_percentage` synchronised on disk.
- MG-OFF toggle (regression from previous turn) re-verified — still persists.

**Out of scope for this session** (deferred to Phase 3):
- Building 3 brand-new CA / Franchise Owner / Franchisor *master* dashboard pages from scratch + 3 PDF/ZIP bundles. Existing screens were aligned to the engine instead — same outcome with far less surface-area churn.
- Refactor split of `mis_dashboard.py`, `center_accounts.py`, `pdf_generator.py` (all > 700 lines).
- Sunsetting overlapping legacy reports (Revenue Share Report / Profit Share Report / Email Pack) — these still work; consolidating them is Phase 3.

⚠️ **Click Deploy** to ship to `intra.purnabramha.com`. Post-deploy quick test: open Franchise Management → edit any India center → flip Payout Model to "Profit Share" → save → reopen Center Accounts → Section 7 heading reads "PROFIT SHARE CALCULATION" with Profit Share Base.

---



### [2026-02-15] MG Calculation ON/OFF per Franchise (P0 feature)

**User directive** *Different franchises follow different payout models. Some
have an MG (minimum-guarantee) floor; others are pure Revenue Share. All
calculations, ledgers and reports must first check this flag.*

**New field**: `mg_calculation_applicable` (bool, default `True`) on the
`franchises` collection. Default `True` preserves today's behaviour for every
existing center (1.a).

**Calculation logic** (`routes/center_accounts.py` & `routes/ledgers.py`):

| Mode | Computation | `payable_type` |
|------|-------------|----------------|
| MG ON, Normal | `max(MG, Revenue Share Base × %)` | `minimum_guarantee` or `revenue_share` |
| MG OFF, Normal | `Revenue Share Base × %` (no MG calc) | `revenue_share` |
| MG ON, WC Protection | `operational_balance × %` (MG blocked) | `revenue_share_protection` — reason: *"MG Blocked"* |
| MG OFF, WC Protection | `operational_balance × %` | `revenue_share_protection` — reason: *"WC Protection"* (no MG mention) |
| Australia (any toggle) | 80/20 profit-share, untouched | `profit_share` |

**UI / Report surfaces updated**:
1. **Franchise Management** (`FranchiseManagement.jsx`) — new amber checkbox above
   "Total Investment (for MG Calculation)" block. When OFF, the entire Total
   Investment / MG-deductions panel is hidden. Read-only summary card shows
   "MG Calculation: Applicable" vs "Not Applicable (Revenue Share only)".
2. **Center Accounts dashboard** (`CenterAccounts.jsx`) — the MG vs Revenue Share
   "versus" tile renders **N/A** with the explanation "Revenue-Share-only" when
   MG is OFF; the Month-wise Payout Summary table replaces MG amount with "N/A"
   and forces Type = "RS".
2. **PIB PDF Section 8 (`utils/pdf_generator.py`)** — shows "MG Applicable: No"
   instead of the MG amount when toggle is OFF.
3. **MG Payout Excel + PDF (`build_mg_payout_excel/pdf`)** — title becomes
   "Revenue Share Payout Report", "Monthly MG" header replaced with "MG: Not
   applicable (Revenue-Share-only model)", new "MG Applicable" column added to
   per-month rows.
4. **Franchise Owner Ledger** (`routes/ledgers.py`) — sets `mg = 0` for MG-OFF
   centers so the comparison never picks MG.
5. **API response** — `summary.mg_calculation_applicable` and
   `payout_summary.franchise.mg_calculation_applicable` exposed for the UI to
   render correctly.

**Regression**: `backend/tests/test_mg_applicable_toggle.py` (7 tests) plus
source-guard tests ensure the toggle is wired into:
- The Pydantic FranchiseCreate / FranchiseUpdate models
- The MG-vs-RS comparison in payout summary
- The summary response shape
- The Franchise Management UI

Total test suite: **26/26 passing**.

⚠️ **All existing franchises default to MG ON** — no behavioural change for
already-onboarded centers. To switch a center to Revenue-Share-only, open
Franchise Management → edit franchise → uncheck "MG Calculation Applicable" → Save.

---



### [2026-02-12] Legal Entity Name Correction Across All Reports (P0)

**User directive**: *Replace hardcoded "Purnabramha LLC Share" with the legal entity name resolved by the center's country.*

**Naming convention**:
- India center → **"Manaswini Foods Pvt Ltd Share"**
- Australia center → **"Purnabramha LLC Pty Ltd Share"**

**New shared helper**:
- `backend/utils/entity.py` → `entity_for_country(country)` + `entity_share_label(country)` — single source of truth.
- Frontend mirror helper `entityName(country)` declared at top of `pages/CenterAccounts.jsx`.

**Surfaces updated**:

| Surface | Change |
|---------|--------|
| `backend/utils/pdf_generator.py` (Section 8 — Payout Determination) | Row label for franchisor 20% share now `entity_share_label(country) + " (20%)"`. Renders "Manaswini Foods Pvt Ltd Share (20%)" for India PDFs, "Purnabramha LLC Pty Ltd Share (20%)" for Australia. |
| `backend/routes/center_accounts.py` (monthly accounting email signature) | Footer now picks the single correct entity per center country instead of listing both. |
| `backend/utils/agreement_generator.py` (Australian franchise agreement — 6 references) | Hardcoded "Purnabramha LLC" upgraded to legally-correct "Purnabramha LLC Pty Ltd" across Definitions 1.15, Profit Share clause 4.1.2, Director Honorarium 4.2.1, and Special Termination 7.7.1 / 7.7.2. |
| `frontend/src/pages/CenterAccounts.jsx` (5 places) | Share-card heading, overseas-share KPI tile, overseas-payout description, overseas-payout 20% row, and overseas-payout invoice row — all now driven by `entityName(accountSummary.country)`. |

**Already country-aware (no change needed)**:
- `backend/utils/signature.py` — CFO signature block already resolves entity by country.
- `backend/routes/ledgers.py` — uses `signature.py` for sign-off.
- `backend/utils/agreement_generator.py::_set_franchisor_details` — `franchisor_name`/`franchisor_short` already differ per country.

**Regression tests**: `backend/tests/test_entity_naming.py` — 7 tests covering the helper, both PDF source guard (no legacy string in `pdf_generator.py`) and frontend source guard (no legacy string outside the `entityName` helper). Australian agreement PDF rendered live and verified — 6 occurrences of "Purnabramha LLC Pty Ltd" present.

**Test suite**: 15/15 passing across `test_entity_naming.py`, `test_payout_release_status.py`, `test_profit_loss_vs_revenue_share.py`.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. After deploy, India centers will see "Manaswini Foods Pvt Ltd Share" everywhere; Australia centers will see "Purnabramha LLC Pty Ltd Share".

---



### [2026-02-12] Revenue Share Payout column re-added across all surfaces (P0 transparency)

**User directive**: *"Revenue Share Payout is not separately visible. Make it clear how much payout is coming from the Revenue Share calculation versus MG."*

**Column position** (everywhere): `Rev Share Base → Revenue Share Payout → MG → Type → Payable`

**Formula**: `Revenue Share Payout = Revenue Share Base × Franchise Revenue Share %` — percentage pulled automatically from Franchise Management (`franchise_info.revenue_share_percentage`). No manual entry on payout reports.

**Surfaces updated**:

| Surface | Change |
|---------|--------|
| `pages/CenterAccounts.jsx` — Monthly Payout table | New "Revenue Share Payout" column between Rev Share Base and MG, with the `% from Franchise Management` displayed in the header subtitle. Per-row testid `rev-share-payout-{month}` for testing. |
| `pages/CenterAccounts.jsx` — Summary tiles | NEW **Total Revenue Share Payout** card (sky blue) alongside Total MG and Total Payable. Shows totals.revenue_share + `@ X% of Rev Share Base` caption. Tooltip per spec. `data-testid="kpi-total-rev-share-payout"`. |
| `utils/pdf_generator.py` — MG-Payout PDF | Column re-added: header shows `Rev Share Payout (15%)` (dynamic). Total row carries the running sum. Column layout now: Month · Total Sales · GST · Comm · Rev Share Base · **Rev Share Payout** · MG · Type · Payable · Paid · Pending · Status. Column widths recalibrated for 12 columns. |
| `utils/pdf_generator.py` — MG-Payout Excel | Same column structure. Header includes the % for clarity: `"Revenue Share Payout (15%)"`. Totals row + Final-Payout-Add-GST + Grand-Total rows updated to leave the column blank correctly. |

**Backend payload — already correct**:
- `payout_summary.monthly_data[i].revenue_share` is computed by `get_payout_summary` (line 3052/3055): `net_revenue_for_share × franchise_owner_pct%` where `net_revenue_for_share = max(0, revenue_share_base)` for India after the prior Feb-2026 fix. No backend changes needed.
- `payout_summary.totals.revenue_share` and `payout_summary.franchise.revenue_share_percentage` already exposed — frontend reads them as the source of truth.

**Tooltip** wired on the column header + the summary tile: *"Calculated as Revenue Share Base × Franchise Revenue Share Percentage configured in Franchise Management."*

**Tests**: 14/14 regression passing. Lint clean.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. After deploy:
- Center Accounts page → Monthly Payout table gets the new column.
- Summary cards above the table now show 4 cards: Months · Monthly MG · **Total Revenue Share Payout** · Total Payable.
- Re-download a MG Payout PDF or Excel → new "Revenue Share Payout (X%)" column visible between Rev Share Base and MG.

---


### [2026-02-12] Payout Release Status Banner — informational only, NO calc changes (P0)

**User directive**: *"Do not change existing Franchise Owner Ledger, PIB Reports, Revenue Share Reports or Payout Calculations. However, if WC Protection Mode is active or payout manually blocked, the report should clearly indicate that the calculated payout is currently not eligible for release."*

**Implementation**:
- **Backend** (`utils/payout_status.py` — NEW canonical helper):
  - `derive_payout_release_status(db, center, month, protection_mode)` returns `{status, label, color, narrative, reason, source, override_active}` with three statuses: `eligible` (🟢) / `review` (🟠) / `blocked` (🔴).
  - Priority order: **(1) manual override** in `center_settings` (per-month or per-center) → **(2) WC Protection Mode active → blocked** → **(3) default eligible**.
  - Manual `eligible` override beats WC Protection — gives Accounts the explicit "release anyway" authority you specified.
- **API**:
  - `POST /api/center-accounts/set-payout-release-status` (Super Admin / Admin / Accounts only). Value: `eligible | review | blocked | auto`. Audit-logged in `expense_reconciliation_log`.
  - `payout_release_status` now exposed in `/api/center-accounts/summary` response.
- **PDF banners** added at the TOP (after logo / header) of:
  - PIB Report (`utils/pdf_generator.py:build_pib_pdf`)
  - Franchise Owner Ledger / Revenue Share Report (`routes/ledgers.py:_render_pdf`)
  - Franchise Payout Report / MG-Payout multi-month (`utils/pdf_generator.py:build_mg_payout_pdf`)
  - Reusable helper `_append_payout_status_banner(story, status)` keeps the banner uniform across all 4 PDF surfaces. ReportLab Table with coloured strip + body + reason.
- **Frontend** (`pages/CenterAccounts.jsx`):
  - NEW `<PayoutStatusBanner>` component above the KPI tiles — coloured strip + label + reason + narrative.
  - Super Admin / Admin / Accounts see an inline dropdown to set: `Auto (WC-driven) · 🟢 Eligible · 🟠 Review · 🔴 Blocked`.
  - `data-testid="payout-release-banner"`, `payout-release-label`, `payout-release-select`.

**NO calculation changed**: Profit/Loss, Revenue Share Base, Revenue Share Amount, Payable, MG, Paid, Pending — all unchanged. Only the visible status indicator is new.

**Tests**: `tests/test_payout_release_status.py` — 5/5 passing covering default / WC auto / manual override-beats-WC / review / invalid-value rejection. End-to-end curl verified all 4 transitions (blocked → review → eligible → auto).

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. After deploy:
- Center Accounts page → coloured banner appears at the top of the report area; admins get the override dropdown.
- Re-download PIB PDF / Franchise Owner Ledger PDF / MG Payout PDF — coloured banner appears at top of each.
- If WC Protection is currently active for a center, the banner reads 🔴 *Currently Blocked* with reason `"Working Capital Protection Mode active"`. Accounts can override via the dropdown without touching any numbers.

---


### [2026-02-12] Net Revenue HIDDEN · Revenue Share Base elevated as primary metric (P0 visibility sweep)

**User directive**: *"Hide Net Revenue from all user-facing screens and reports. Highlight Revenue Share Base instead — Sales − Commissions − GST — this is the actual amount used for owner percentage split and payout calculations."*

**Worked example — PB-HSR · May 2026** (still verifiable):
- Total Sales: ₹12,53,972
- GST: ₹52,128
- Commissions: ₹59,234
- **⭐ Revenue Share Base = ₹11,42,610** *(Sales − Comm − GST)*
- ~~Net Revenue ₹11,94,738~~ ← removed from UI

**Frontend changes** (all data-testids preserved/added):

| File | Change |
|------|--------|
| `pages/CenterAccounts.jsx` | Net Revenue tile **removed**. Revenue Share Base tile now **PROMINENT** with `border-2 border-sky-400 shadow-lg`, ⭐ icon, larger font (text-3xl extrabold), tooltip per spec, `data-testid="kpi-revenue-share-base-card"`. Formula chain block "= Net Revenue (Base for Split)" renamed "⭐ = Revenue Share Base (Base for Split)" with sky-blue emphasis. Monthly payout table column renamed: **Revenue Share Base** (replacing "Net Revenue" + dropped redundant "Revenue Share" amount column — Payable is the canonical amount). PIB preview KPI card "Net Revenue" renamed "⭐ Revenue Share Base". |
| `pages/OwnerReports.jsx` | Net Revenue tile **removed**. Revenue Share Base now primary (col-span-1 sky gradient + shadow). Tooltip added per spec. |
| `pages/MISDashboard.jsx` | "Net Revenue" KPI card removed. ⭐ Revenue Share Base reordered ahead of Owner Share per visual priority. Excel export sheet drops "Net Revenue" row. |
| `pages/FranchiseOwnerDashboard.jsx` | Variable `netRevenue` renamed `revenueShareBase` (was already computing the right number). KPI "Net Revenue" + "Total Deductions" cards both removed. Excel export updated. Eligible Profit chain for AU continues to use Rev Share Base − Expenses. |
| `pages/CenterHealth.jsx` | KPI "Net Revenue" relabelled "⭐ Revenue Share Base" (tone sky). Profitability formula chain "= Net Revenue" → "= ⭐ Revenue Share Base". |
| `pages/CommissionTracking.jsx` | Grand totals card + table column renamed Net Revenue → Rev Share Base. |

**Backend PDF / Excel changes**:

| File | Change |
|------|--------|
| `utils/pdf_generator.py` — PIB PDF (Section 4 Financial Summary) | India: "NET REVENUE" row **removed**. "⭐ REVENUE SHARE BASE" is now the highlighted (BRAND_GOLD background) row. Australia keeps Net Revenue + Profitability chain. |
| `utils/pdf_generator.py` — Multi-month MG Payout Excel | Column "Net Revenue" **removed**. New column "Revenue Share Base" (= Sales − Comm − GST). Columns now: Month · Total Sales · GST · Commissions · **Revenue Share Base** · MG · Type · Payable · Paid · Pending · Status (matches user's spec exactly). |
| `utils/pdf_generator.py` — Multi-month MG Payout PDF | Same column overhaul. Table widths recalibrated (12 → 11 cols). Dropped redundant "Rev Share" amount column. |
| `routes/ledgers.py` — Ledger PDF section | Renamed "Net Revenue & Revenue Share Base" → "⭐ Revenue Share Base Calculation". The intermediate "= Net Revenue" line removed; chain goes straight Sales − GST − Comm − Comm-GST → ⭐ Revenue Share Base. |

**Visual priority** implemented per spec:
1. Gross Sales
2. GST
3. Commissions
4. ⭐ **Revenue Share Base** *(larger font, sky border, gold highlight in PDF)*
5. Owner Share
6. Profit / Loss
7. Working Capital + Final Payout

**Tooltip** added to all Rev Share Base tiles: *"The amount available for owner/company percentage sharing after deducting GST and commissions from sales."*

**Tests**: 10/10 regression suite passing. Lint clean.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. After deploy:
- Every dashboard tile that previously said "Net Revenue" now says "⭐ Revenue Share Base" (or has been removed)
- PIB PDF Section 4 highlights Revenue Share Base in gold
- MG Payout PDF + Excel columns now read: Month · Total Sales · GST · Comm · **Rev Share Base** · MG · Type · Payable · Paid · Pending · Status

---


### [2026-02-11 Phase 3 — Gap closure] Credit→Sales auto-convert + AI for credits + Inline edit + Sales Dashboard link + Original-narration tracking (P0)

User reviewed the full Bank Reconciliation spec and confirmed Phase 1+2 + Phase 3 (debit→expense) are deployed. Five remaining gaps shipped in one pass:

**A. Auto-convert credits → daily_sales** — NEW `POST /api/bank-reconciliation/auto-convert-credits-to-sales`
- Groups AI-categorized credits with confidence ≥ 0.7 by `(center, transaction_date)`.
- For each bucket: if a `daily_sales` row already exists → **skip** and link the bank txn (dedupe guard via `match_method=auto_convert_dedupe_credit`). Otherwise CREATE a new row with `source=bank_reconciliation` and `ai_provenance[]` listing each contributing bank txn.
- AI category → daily_sales field mapping: Cash Sale → `total_cash_sale`, PhonePe Sale → `phonepe`, Swiggy → `swiggy`, Zomato → `zomato`, Card Sale → `card_idfc`, UPI Sale → `bharat_pay`, Online Sale → `total_online_sale`, Razorpay/Other Income → `online_other`. `total_online_sale` is re-derived from the buckets (single source of truth). `Inter-Account Transfer` rows are skipped (not revenue).

**B. AI categorize for credits** — `POST /api/bank-reconciliation/ai-categorize` now runs **two** Claude passes (one per side) with separate constrained masters:
- Credit master: Cash / Online / Card / UPI / PhonePe / Razorpay / Swiggy / Zomato / Doordash / Franchise Payment / Other Income / Inter-Account Transfer.
- Each `bank_transactions` doc gets `ai_side ∈ {debit,credit}` so downstream filters can target the right side.
- Response now exposes `debit_categorized` and `credit_categorized` counts separately.

**C. Inline narration edit** — NEW `POST /api/bank-reconciliation/edit-transaction`
- Edits any of: `narration`, `ai_suggested_category`, `transaction_date`, `debit_amount`, `credit_amount`, `user_notes`.
- Tracks per-field `{field, old, new}` changes in the response + writes an entry to `expense_reconciliation_log` (action='edit_transaction'). Stores `edited_by`, `edited_at`. **Preserves `original_narration`** (never overwritten).
- Frontend: each row in `TxnTable` now has a small `✎ edit` button. Inline Input with Save/Cancel. After save, the row shows the new narration plus a small italic `(raw: ...)` line showing the original — full audit visible at-a-glance.

**D. Sales Dashboard quick link** — `SalesExpenses.jsx` header now shows an emerald "📄 Import sales from Bank Statement" link for Super Admin / Admin (gated on `session?.is_super_admin || session?.is_admin`). `data-testid="sales-import-from-bank-link"`. Page route is `/sales` (NOT `/sales-expenses`).

**E. Original-narration immutability** — All 3 parsers (PDF table, PDF text-fallback, CSV/Excel) now write `original_narration = narration` at upload time. The field is never overwritten by `/edit-transaction`. UI shows both side-by-side when they differ, giving MGT Admin a full audit trail of what the bank reported vs what they re-titled it as.

**Tests**: `tests/test_bank_recon_phase3_gaps.py` — 10 HTTP integration tests, 100% pass. Includes a real Claude /ai-categorize call (3 txns) verifying `debit_categorized` + `credit_categorized` counts. Phase 2 regression suite still 100%.

**Frontend wiring** confirmed by testing agent: `br-tab-credits`, `br-credit-ai-categorize`, `br-auto-convert-credits-to-sales`, `br-edit-narration-{id}`, `br-edit-save-{id}`, `br-edit-narration-input-{id}`, `sales-import-from-bank-link` — all present and functional.

⚠️ **Known refactor backlog**: `routes/bank_reconciliation.py` is now 2181 lines — should be split into `recon_match.py + recon_ai.py + recon_credit_to_sale.py + recon_edit.py` in a future cleanup turn.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`.

---


### [2026-02-11 sweep] Profit/Loss + Revenue Share Base propagated across ALL reports (P0 — financial consistency)

**User directive**: *"now with this calculation we have to reapply at all reports and every place"*

**Goal**: Every report, dashboard tile, PDF section, and ledger entry across the app must use the SAME two canonical formulas:
1. **Revenue Share Base** = `Total Sales − Commissions − GST` *(the 80/20 split base)*
2. **Profit / Loss** = `Total Sales − Total Expenses − Commissions` *(GST excluded — operational health)*

Both metrics share the same `Total Sales` but never confuse each other.

**Canonical helpers added** (`utils/gst.py`):
- `compute_revenue_share_base(total_sale, total_commissions, gst_on_sales, country)` — Sale − Comm − GST for India
- `compute_profit_loss(total_sale, total_expenses, total_commissions, country)` — Sale − Exp − Comm
- These join the existing `compute_net_revenue` so the three SSOT helpers cover the three management metrics.

**Files updated** (with verified end-to-end via curl smoke + 12-test pytest suite):

| File | Surface | Change |
|------|---------|--------|
| `utils/gst.py` | SSOT helpers | Added `compute_revenue_share_base` + `compute_profit_loss` |
| `routes/center_accounts.py` | `/summary` payload | `operational_sustainability` now exposes `profit_loss`, `profit_loss_formula`, `revenue_share_base`, `revenue_share_formula` |
| `routes/center_accounts.py` | `get_payout_summary` (India) | Payout-split now uses `revenue_share_base = Sales − Comm − GST` |
| `routes/owner_reports.py` | `/monthly-report` payload | Surfaces `net_revenue`, `revenue_share_base`, `profit_loss` as 3 distinct fields (legacy `pnl/net_pl` kept for back-compat) |
| `routes/mis_dashboard.py` | `/overview` payload | `summary.net_revenue` (Sales−Comm), `summary.revenue_share_base` (Sales−Comm−GST), `summary.profit_loss` (Sales−Exp−Comm) |
| `routes/mis_dashboard.py` | Franchise PDF export | KPI cards + Financial Summary now show **Net Revenue · Rev Share Base · Profit/Loss** as 3 distinct lines. Revenue Share Payable = pct × Rev Share Base (not Net Revenue). |
| `routes/mis_dashboard.py` | Latent bug fix | `period_days` was previously undefined (would `NameError` at runtime). Defensive fallback added. Dead `prev_net_revenue/prev_profit` pre-allocation removed. |
| `routes/ledgers.py` | Monthly ledger PDF | Net Revenue & Revenue Share Base shown as **two separate lines** with both formulas. Monthly payout uses `rev_share_base` (not net_revenue) for the % split. |
| `routes/ledgers.py` | Period totals | `period_totals.net_revenue` + `period_totals.eligible_rev_share_base` both exposed. |
| `routes/financial_health.py` | `/center` payload | `net_profit` formula switched from `Sales − Expenses` to **`Sales − Expenses − Commissions`** (now aligned with Profit/Loss across the app). New helper `_commissions_for_period` aggregates monthly commissions. `total_commissions` + `profit_loss_formula` added to headline. |
| `utils/wc_chain.py` | WC chain row | Each month row now carries `profit_loss`, `net_revenue`, `revenue_share_base` alongside legacy `pnl`. |
| `utils/pdf_generator.py` | PIB Section 5 | (from prior turn) Split into **A. Profit/Loss** + **B. Revenue Share Base** sub-tables with explanatory note. |
| `frontend/pages/CenterAccounts.jsx` | KPI tiles | Net Revenue, Profit/Loss, Revenue Share Base — 3 distinct tiles with formula captions |
| `frontend/pages/OwnerReports.jsx` | KPI tiles | Renamed "Net P/L" → "Profit / Loss", "Eligible Rev Share Base" → "Revenue Share Base", with corrected formula captions |
| `frontend/pages/MISDashboard.jsx` | KPI grid + Excel export | New "Rev Share Base" KPI card, "Net Profit (P&L)" relabelled "Profit / Loss". Excel summary sheet now lists all 3 metrics on separate rows. Revenue Share computed on Rev Share Base. |

**Worked example — PB-HSR · May 2026** (your numbers):
| Metric | Formula | Value |
|--------|---------|------:|
| Net Revenue | `Sales − Commissions` | ₹11,94,738 |
| **Revenue Share Base** | `Sales − Commissions − GST` | **₹11,42,610** |
| **Profit / Loss** | `Sales − Expenses − Commissions` | **₹-1,69,420** |

**Regression suite**: 12/12 passing (`test_profit_loss_vs_revenue_share.py` · `test_pnl_gross_sales.py` · `test_bank_recon_phase2.py` · `test_commission_overview_vs_ledger_parity.py`).

**API contracts verified** end-to-end via curl on `/api/center-accounts/summary`, `/api/owner-reports/monthly-report`, `/api/mis/overview`, `/api/financial-health/center` — all four return the new fields cleanly.

⚠️ **Click Deploy** to push the consistency sweep to `intra.purnabramha.com`. After deploy, the three metrics will read identically wherever they appear: Center Accounts page · MIS Dashboard · Franchise PIB PDF · Owner Reports · Ledgers PDF · Financial Health.

⚠️ **Behavioral change**: India franchise owner payout is now computed on Revenue Share Base (Sales − Comm − **GST**) instead of Net Revenue (Sales − Comm). For PB-HSR May 2026 this is a ₹52,128 reduction in the share base → at 15% split that's ~₹7,800 lower owner payout. If you want me to keep the *legacy* payout base (Net Revenue, no GST deduction), say the word and I'll revert just the ledger payout split.

---


### [2026-02-11 follow-up] Two distinct metrics: Profit/Loss vs Revenue Share Base (P0 clarification)

**User directive** (verbatim):
> 1) Revenue Share = `Total Sale − Commission − GST of current month`
> 2) Profit / Loss = `Total Sale − Total Expense − Commission` *(without GST)*

**Worked example — PB-HSR · May 2026**:
| Component        | Value         |
|------------------|--------------:|
| Sales            | ₹12,53,972    |
| Expenses         | ₹13,64,786    |
| Commissions      | ₹59,234       |
| GST on Sales     | ₹52,128       |
| **Profit / Loss**       | **₹-1,70,048** = Sales − Expenses − Commissions |
| **Revenue Share Base**  | **₹11,42,610** = Sales − Commissions − GST      |

**Key insight**: Profit/Loss and Revenue Share Base are *distinct* metrics that should never be conflated:
- Profit/Loss measures **operational health** (expenses included, GST excluded — GST is a govt pass-through booked in M+1)
- Revenue Share Base is the **franchise owner's entitlement** (commissions & GST excluded, expenses excluded)

**Backend changes** (`routes/center_accounts.py`):
- `operational_sustainability` payload now exposes BOTH metrics explicitly: `profit_loss`, `profit_loss_formula`, `revenue_share_base`, `revenue_share_formula`, plus existing `operational_balance` (alias for `profit_loss`).
- Payout-split logic at `get_payout_summary`:
  - India: `revenue_share_base = Sales − Commissions − GST` (used for the % split)
  - India: `net_revenue = Sales − Commissions` (used for the management Net Revenue tile)
  - Two distinct fields — no longer collapsed.

**PIB PDF** (`utils/pdf_generator.py`):
- Section 5 "Operational Sustainability Check" now has **two sub-tables**:
  - **A. Profit / Loss Calculation** (red/green per sign) — Sales − Expenses − Commissions, GST shown as informational only.
  - **B. Revenue Share Base** (blue) — Sales − Commissions − GST, used for the franchise owner % split.
- Both sub-tables share the same Total Sales but the deductions differ, with an explanatory note underneath.
- Financial Summary "Eligible Rev Share Base" line for India now correctly shows `Sales − Commissions − GST` value (not `Sales − Commissions`).

**Frontend** (`pages/CenterAccounts.jsx`):
- Net Revenue tile label corrected for India: now reads **"Sales − Commissions"** (was wrongly "Sales − GST − Commissions").
- NEW **Profit / Loss** KPI tile (rose/emerald based on sign) with formula "Sales − Expenses − Commissions (GST excluded)". `data-testid="kpi-profit-loss"`.
- NEW **Revenue Share Base** KPI tile (sky blue) with formula "Sales − Commissions − GST (for owner % split)". `data-testid="kpi-revenue-share-base"`.

**Tests**: `tests/test_profit_loss_vs_revenue_share.py` locks in both formulas + guards against future collisions. 4/4 passing (3 new + existing P&L Gross-Sales).

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. After deploy:
- Center Accounts page → expect **3 distinct tiles** (Net Revenue / Profit-Loss / Rev Share Base) with the correct numbers above.
- PIB PDF section 5 → two sub-tables (A & B) clearly labelled.

---


### [2026-02-11 hotfix] Operational Balance was still deducting GST in PIB PDF & API (P0 bug)

**Symptom** (user-reported, PB-HSR · 2026-05):
- Total Sale ₹12,53,972 · Total Expenses ₹13,64,158 · Total Commissions ₹59,234 · GST (info) ₹52,128
- PIB PDF page 4 ("Operational Sustainability Check") showed Operational Balance = **-₹2,21,548**
- User expected ~**-₹1,69,420** (Sales − Expenses − Commissions, GST NOT deducted)

**Root cause**: Previous Feb-2026 Gross-Sales correction fixed `compute_net_revenue` and the UI tiles BUT missed three places where GST was still being subtracted:
1. `routes/center_accounts.py:1535` — `operational_balance = total_sale - total_expenses - total_commission - sales_gst_amount` (the comment even said "would double-count", but the code did anyway)
2. `routes/center_accounts.py:3000` — payout-split net revenue for India was `total_sale - total_commission - gst_on_sales`
3. `utils/pdf_generator.py` — Financial Summary AND Operational Sustainability Check sections still rendered "Less: GST on Eligible Sales" deduction lines

**Fix**:
- `operational_balance = total_sale - total_expenses - total_commission` (no GST). GST is a govt pass-through — it lands in M+1 as the auto-generated "GST PAYMENT" expense row, so subtracting it here was double-counting.
- Added `gst_informational_only: true` flag in `operational_sustainability` payload so any future UI can short-circuit GST deduction logic.
- India payout-split: `net_revenue = total_sale - total_commission` (no GST).
- PDF generator:
  - Financial Summary: India shows GST as `"GST on Eligible Sales (5%) — informational"` (no "Less:" prefix, no parentheses); Australia unchanged.
  - Operational Sustainability Check: same informational treatment — GST row is shown but NOT deducted.
  - "Eligible Rev Share Base" formula label simplified to `"Sales − Commissions"` for India.

**Verified** via API contract test: `/api/center-accounts/summary` now returns `operational_sustainability.gst_informational_only=true` and `operational_balance = total_sales - total_expenses - total_commissions` (GST NOT subtracted). Pre-existing `test_pnl_gross_sales.py` still passes.

⚠️ **Click Deploy** to push the fix to `intra.purnabramha.com`. After deploy, PIB Preview for PB-HSR · 2026-05 should show Operational Balance ≈ **-₹1,69,420** (not -₹2,21,548).

---


### [2026-02-11] Bank Reconciliation Phase 2 + Phase 3 — Credit/Debit + AI Categorization (P0 — financial)

**User directive**: *(1) Reconcile both credit and debit transactions. (2) Auto-ignore ATM/Cash Withdrawals. (3) Add new statuses: Matched, Partially Matched, Unmatched, Ignored, Manual Review. (4) Surface PhonePe Commission in bank-recon. (5) Allow MGT IDFC statement upload with AI vendor categorisation that auto-propagates to Sales/Expenses without duplicates.*

**Phase 2 — Credit + Debit reconciliation** (`backend/routes/bank_reconciliation.py`):
1. **Parser**: PDF / Excel / CSV now KEEP credit rows (previously skipped). Each transaction carries `txn_type ∈ {debit, credit}`.
2. **Auto-Ignore Cash Withdrawals**: regex pattern catches `ATM, NFS, NWD, CASH WDL, CASH WITHDRAW, CSH WDL`. Marked `match_status=ignored`, `auto_ignored=True`, reason `"Cash Withdrawal (auto)"`. No expense double-count.
3. **New 5-state status taxonomy** (`recon_status`):
   - `matched` — exact date + amount
   - `partially_matched` — fuzzy date (±2-3 days) OR fuzzy amount (≤5% drift)
   - `unmatched` (legacy `unrecorded` retained for UI compat) — no candidate
   - `ignored` — auto cash withdrawal OR user-ignored
   - `manual_review` — high-value (≥ ₹50,000) unmatched
4. **Credit reconciliation source pool**: built from `daily_sales` (cash/online/phonepe/swiggy/zomato/doordash) + `monthly_commissions` (PhonePe / Razorpay net settlements). Each matched credit row carries through `pg_commission` and `gst_on_commission` so PhonePe MDR is visible in the bank-recon UI.
5. **Credit source hints**: for unmatched credits, `credit_source_hint` is detected from narration (PhonePe / Razorpay / Swiggy / Zomato / UPI / Card / NEFT_IMPS) so analyst can see at a glance what was likely deposited.
6. **API `/upload` response** now exposes `partially_matched`, `unmatched_credits`, `auto_ignored`, `manual_review` buckets plus per-bucket amount totals.

**Phase 3 — IDFC MGT statement → AI categorisation → auto-propagate to Expenses**:
1. **NEW `POST /api/bank-reconciliation/ai-categorize`** — Claude Sonnet 4.5 (Emergent Universal Key) reads each unmatched debit narration and assigns the most likely category from the active Category Master. Returns JSON `{id, category, confidence, reasoning}`. Confidence ≥ 0.7 means the AI is sure enough for auto-conversion.
2. **NEW `POST /api/bank-reconciliation/auto-convert`** — bulk-converts AI-tagged debits into expense rows. Duplicate guard: if an expense already exists for the same `(center, date, amount)` it is **NOT** re-booked — instead the bank transaction is auto-linked to the existing expense (`match_status=matched`, `match_method=auto_convert_dedupe`).
3. **Audit trail**: every AI categorisation and auto-conversion writes a `expense_reconciliation_log` entry with the actor, confidence, AI reasoning and final category.

**Frontend** (`frontend/src/pages/BankReconciliation.jsx`):
- New tabs: **Partially Matched**, **Unmatched Credits**, **Manual Review** (in addition to existing Unmatched / Matched / Added / Ignored).
- New violet "🤖 AI Categorizer" toolbar inside the Unmatched tab with **AI Categorize** + **Auto-Convert to Expenses** buttons (test IDs `br-ai-categorize`, `br-auto-convert`).
- Each row now shows the AI suggestion (with confidence %) as a violet badge instead of the keyword-based suggestion when available.
- Recent uploads table grew columns for **Partial · Manual Review · Ignored** counts.
- Summary header shows debits + credits separately, plus per-bucket amounts.
- File picker now accepts `.pdf` in addition to `.csv/.xls/.xlsx`.

**Verified end-to-end** via new regression tests (`tests/test_bank_recon_phase2.py` — 6 tests, all green):
- ATM auto-ignore ✓ · Debit exact match ✓ · Debit partial (fuzzy amount ≤5%) ✓
- PhonePe settlement credit matched + `pg_commission` carried through ✓
- Razorpay unmatched credit → `credit_source_hint=razorpay` ✓
- ≥ ₹75,000 unmatched → `manual_review` ✓

Existing bank-recon regression suite updated for new column names — **27 passed, 2 skipped, 0 regressions**.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`.

---


### [2026-02-11] P&L correction — Gross Sales basis for management profitability (P0 — financial directive)

**Owner directive**: *"GST is being deducted from Sales while calculating profitability — this distorts the operating picture. For management reporting, franchise profitability, center performance analysis and revenue-share calculations we must use **Gross Sales** and show GST separately. GST tracking + compliance reporting must stay intact."*

**New canonical formula**:
```
PBT = Gross Sales − Adjusted Expenses − Commissions
```
GST stays visible (Collected / Paid / Payable / Receivable) but does **NOT** reduce sales in any management calc.

**Files changed**:
1. `routes/ledgers.py` — `build_monthly_pnl` now computes `pbt = gross − adj_expenses − commissions`. P&L PDF + Excel renamed columns: **Gross Sales · GST (Display) · Expenses (Raw) · Adjustments · Adj. Expenses · Commissions · PBT** (removed "Sales (Ex-GST)" from the math columns).
2. `utils/gst.py` — `compute_net_revenue` rewritten. India: `Gross − Commissions`. Overseas: `Gross − Commissions × (1 + commGSTRate)`. GST argument retained for signature compat but explicitly ignored (with a comment + Feb-2026 directive reference).
3. `routes/financial_health.py` — `_snapshot` net_profit was already using gross; added explicit comment to lock the directive in place.
4. `routes/mis_dashboard.py` — `net_revenue = sales − commissions` (was `− commissions − gst`). Previous-period mirror updated for apples-to-apples MoM. UI labels updated: *"Gross Sales − Comm"*.

**Auto-propagated** (all consume the same helpers above):
- Center Accounts summary → revenue / share-eligible base
- Franchise Owner Dashboard → Net Revenue / PBT cards
- Revenue Share calculations (India + Overseas)
- Financial Insights tab
- Monthly + Annual reports
- Ledger Exports + PDF + Excel + CA Bundle Reports

**Verified end-to-end** via new pytest `tests/test_pnl_gross_sales.py`:
- User's worked example: Sales ₹10L · GST ₹50k · Expenses ₹7L · Commission ₹50k
- New PBT = ₹2,50,000 ✓  (was ₹2,00,000 before)
- All 12 existing regression tests still pass (Financial Health, Adjustments propagation, Commission parity)

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. After redeploy, every PBT figure across the platform will jump by exactly the period's GST amount — that's by design.

**Phase 2 (Bank Reconciliation credit/debit upgrade) and Phase 3 (MGT IDFC bank-statement → sales/expenses with Claude categorisation) deferred to the next turn — couldn't safely fit in this context.**

---


### [2026-02-11] Phase 1 — PIB inline-PDF preview + PhonePe Commission visibility

**User pain solved**:
1. *"Preview for PIB is not visible — it's showing only number cards. Everytime we have to download and see it."*
2. *"PhonePe Commission is being calculated correctly but not visible on screen — only the net settlement shows."*

**1. PIB Preview now mirrors the full PDF inline**
- `openPibPreview()` in `CenterAccounts.jsx` now fires `preview-pib` and `generate-pib` in parallel; the PDF blob is materialised into a `URL.createObjectURL` and embedded in an `<iframe>` (70vh) inside the existing dialog.
- Dialog widened (`max-w-6xl`, `max-h-92vh`).
- "Open in new tab" link on the iframe header for users who want a full-screen view.
- Blob URL revoked on close.
- No backend changes — reuses the existing `generate-pib` route.

**2. PhonePe Commission now visible**
- Backend (`routes/center_accounts.py`):
  - Per-platform commission map now tracks `pg_commission` (= `sundry_debtors`, falls back to Gross − Net for legacy rows) plus `settlement_date` and `txn_count` for PhonePe.
  - Summary response exposes a new `commissions.phonepe = {gross, pg_commission, gst_on_commission, net_settlement, settlement_date, txn_count}` block and a top-level `commissions.payment_gateway_total` (PhonePe MDR + Cards MDR).
- Frontend (`CenterAccounts.jsx`):
  - New **"Payment Gateway Deductions"** stat card (purple) next to Payment Mode Deductions.
  - New full-width **PhonePe Settlement** card with 5 metrics (Gross · Commission · GST on Commission · Net Settlement · Txn count + date).
  - Uploaded Commission Reports table now has a **PG Comm.** column (purple) so PhonePe and Cards rows show their MDR.

**Verified end-to-end** with real data (PB-SN / 2026-02):
- PhonePe gross ₹3,55,532.00 → PG commission ₹17,604.64 → net ₹3,37,927.36 (was hidden before; now visible in 3 places: summary card, dedicated PhonePe card, table column) ✓
- 228 transactions · settled 2026-03-30 ✓
- All other commission totals (`aggregator_total`, `card_total`, `total`) unchanged ✓

⚠️ **Click Deploy** to push to `intra.purnabramha.com`.

---

**Phase 2 (Bank Reconciliation upgrade) and Phase 3 (MGT bank-statement → sales/expenses with IDFC parser + AI categorisation) deferred per phased plan.**


### [2026-02-10] Expense Adjustments propagation to ALL reports (P0 — financial)

**User report**: *"Expense adjustments are happening correctly and showing in the Adjustments report — but we need this calculation to flow into P&L, Ledger, Franchise reports and everywhere else expenses are shown."*

**Root cause**: The Adjustments tab and Owner-Reports correctly subtracted prepaid/advance adjustments, but the rest of the reporting surface (`build_monthly_pnl`, MIS Dashboard overview, Financial Health module, overseas Franchise Owner Ledger) summed raw `expenses.amount` and ignored `expense_adjustments` — so the P&L PDF showed ₹13,64,158 even though the Adjustments tab had carved out ₹46,756.

**Fix**: One shared helper, applied in every monthly/period-aware report.

1. **`utils/adjustments.py`** — added `get_adjustments_for_period(db, center, df, dt)` that supports arbitrary date ranges (not just months). Existing `get_total_adjustments` (per-month) preserved.

2. **`routes/ledgers.py`** — `build_monthly_pnl` now subtracts `get_total_adjustments` per month. Output rows expose both `expenses_raw` and the adjusted `expenses` plus the `adjustments` figure. PDF & Excel renderers updated with **Expenses (Raw) · Adjustments · Adj. Expenses** columns so auditors can trace every rupee.

3. **`routes/ledgers.py`** — overseas (AU) Franchise Owner Ledger eligible-profit math now uses adjusted expenses too.

4. **`routes/financial_health.py`** — `_snapshot` subtracts period-aware adjustments. Summary payload exposes `total_expenses` (adjusted), `total_expenses_raw`, and `adjustments`.

5. **`routes/mis_dashboard.py`** — Sales / MIS Overview now subtracts adjustments for the chosen period AND the previous period (so MoM delta stays apples-to-apples).

6. **`frontend/src/pages/FinancialHealth.jsx`** — when adjustments > 0 the "Expenses" card relabels to **"Adj. Expenses"** with a `Raw − Adj` sub-line so managers see exactly why the number differs from the raw expense tab.

**Already adjusted** (no change needed):
- `owner_reports.py` (already subtracted via `get_total_adjustments`)
- `financial_insights.py` (already aggregated `expense_adjustments` per-month)
- Per-center Status Card + WC Table (already used `compute_wc_chain` which respects month overrides)

**Verified end-to-end** via regression test (`tests/test_adjustments_propagation.py`):
- Insert ₹50,000 adjustment for PB-HSR / 2026-02
- `build_monthly_pnl` → PBT shifts by exactly +₹50,000 ✓
- `financial_health._snapshot` → net_profit shifts by exactly +₹50,000 ✓
- `total_expenses_raw` stays constant, `adjustments` = ₹50,000, `total_expenses` = raw − 50,000 ✓
- All 6 existing tests + 1 new propagation test pass

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. The P&L PDF in your screenshot will then show ₹13,17,401.74 (adjusted) instead of ₹13,64,158 (raw).

---


### [2026-02-10] Financial Health & Profitability Intelligence Module (P1 — major)

**User ask**: Build a complete executive-grade financial health module with 11 sections, auto-derived from existing data (sales, expenses, attendance, salary), visible in both Center Accounts and Franchise Owner Dashboard.

**What shipped** (single-shot, per user direction):

**Backend** (`backend/routes/financial_health.py` · 600 LOC):
- `POST /api/financial-health/center` — full per-center snapshot for any period
- `POST /api/financial-health/portfolio` — all centers side-by-side (admin only)
- `POST /api/financial-health/list-centers` — center picker support

**11 sections delivered** (Section 8 deferred per user — needs item-level POS data):

| # | Section | Data Source |
|---|---------|-------------|
| 1 | Health Summary + Score /100 | aggregated from all sections |
| 2 | Prime Cost Monitor | food+labor / sales |
| 3 | Food Cost Intelligence (India 28% / AU 30%) | expenses (GROCERY/DAIRY/F&V/PAV/MANGO RASS/CYLINDER) |
| 4 | Labor Cost Intelligence | expenses (SALARY/OT/ADVANCE/DIRECTOR FEES) + attendance hours |
| 5 | Contribution Margin (sales − food) | derived |
| 6 | Orders per Labor Hour | daily_sales.num_bills ÷ attendance hours |
| 7 | Expense Leakage Monitor (14 buckets, MoM) | expenses |
| 9 | Red Alerts (12+ rules) | derived from sections 1-7 |
| 10 | AI Recommended Actions (rule-based) | mapped to each alert code |
| 11 | Portfolio Ranking (best/worst/highest food/labor/profit) | all centers in one call |

**Health Score (out of 100)**: Net Profit % (40) + Prime Cost band (30) + Leakage flags (20) + Sales-trend (10). Status thresholds: ≥75 Healthy · 50–75 Watch · <50 Action Required.

**Period filters**: Month, Quarter (e.g. `2025-Q2`), FY (e.g. `FY26` = Apr 2025–Mar 2026), Custom date range. Every metric has a previous-period delta computed automatically.

**Permission model**:
- Manager → only own center
- Admin / Super-Admin → any center + portfolio

**Frontend** (`frontend/src/pages/FinancialHealth.jsx` · 470 LOC):
- Health Score hero card with traffic-light colour
- Alert stack with severity dots
- Mini-cards for Prime Cost, Food Cost, Labor Cost, Contribution Margin, Orders/Hour
- Leakage table (red/yellow/green dot per bucket, sorted by severity)
- AI Recommendations panel (each alert → 2–4 specific actions)
- Portfolio table with rankings cards above

**Mount points**:
- `CenterAccounts.jsx` → new **Financial Health** tab
- `FranchiseOwnerDashboard.jsx` → new **Portfolio Health** tab (admin-only)

**Verified end-to-end**:
- `curl /center` for PB-HSR / PB-SN / PB-PERTH (AU) → all sections populated, AU food target correctly 30%
- All 4 period kinds (month/quarter/fy/custom) parse correctly
- Portfolio call enumerates 8 active centers, computes 6 rankings, excludes PB-MGT (HQ)
- 4 pytest regression tests pass (`tests/test_financial_health.py`)
- Frontend bundle compiled cleanly (12 MB)
- Lint: 0 blocking issues on `financial_health.py` and `FinancialHealth.jsx`

**Section 8 (Menu Profitability)** — explicitly skipped per user. Will need item-level POS sales data when we revisit.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`.

---


### [2026-02-10] Creative Studio Library + per-creative delete (P1)

**User ask**: *"please give delete options for each center to delete the creatives once they create the final one and delete all repeated ones coz it will eat memory. And super admin + admin should have option to see all and can download all and see each creative to keep the control."*

**Solution**: Unified soft-delete + admin oversight across all 4 creative types.

**Type registry** (`backend/routes/creative_library.py`):
- Memory Box → `memory_boxes` (id=`box_id`)
- Ad → `ad_creations` where `kind != invitation` (id=`ad_id`)
- Invitation → `ad_creations` where `kind == invitation` (id=`ad_id`)
- Video → `marketing_videos` (id=`video_id`)

**Endpoints** (mounted at `/api/creative-library`):
- `POST /list` — cross-type listing; admin sees all centers + can request `status=deleted` for the recycle bin; managers see only their own center's active items. Filters: types[], center, manager substring, from_date, to_date.
- `POST /delete` — soft-delete (sets `status=deleted`, `deleted_at`, `deleted_by`). Manager: own center only. Admin: any center.
- `POST /restore` — admin/super-admin only.
- `POST /bulk-delete` / `/bulk-restore` — multi-select friendly.
- `POST /bulk-download` — admin/super-admin only. Builds an on-the-fly ZIP grouped as `Center/Type/Date_Title_ShortId.ext`. Hard cap 100 items/ZIP.
- `POST /types` — registry exposure for the UI.
- **Startup auto-purge**: `auto_purge_soft_deleted()` runs once per backend boot and hard-deletes rows soft-deleted >30 days ago, plus unlinks their disk assets.

**Permission model**:
- Manager → can soft-delete only own-center creatives.
- Admin / Super-Admin → can do everything across all centers (including restore, bulk download, view deleted).
- Cross-center modify attempts return 403.

**Frontend**:
- New page `frontend/src/pages/CreativeLibrary.jsx` — admin-only. Type pills, full filter panel, multi-select with bulk download / delete / restore actions, type-aware open buttons (Memory Box → web view; Video → inline; Ad/Invitation → asset stream).
- New tab `Library` added inside `AdCreator.jsx` (visible only to `is_admin / is_super_admin`).
- Per-row Trash button added to:
  - `MemoryBoxCreator.jsx` history table → `deleteMemoryBox()`
  - `AdCreator.jsx` Marketing Gallery → `deleteCreative()` (auto-detects ad vs invitation via `kind`)
  - `VideoCreator.jsx` videos list → `deleteVideo()`
- All buttons confirm before delete, refresh the list, and show toast.

**Soft-delete already filtered** for: `memory_boxes/list`, `marketing_videos/list`. Patched `marketing_ads/history` to add the same filter for non-admins.

**Verified end-to-end** via curl:
- `/list` → counts: `memory_box:8, ad:8, invitation:3, video:8`
- soft-delete → recycle bin → restore round-trip ✓
- bulk-delete + bulk-restore (2 items) ✓
- bulk-download produced 1.9 MB ZIP with friendly paths: `PB-HSR/Memory Box/2026-06-05_Pranav_Joshi_a4543a99.{pdf,png,mp4,html}` ✓
- Frontend Library page screenshot — perfect render with 41 creatives, 4 type pills, multi-select, action buttons.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`.

---


### [2026-02-10] Background music on Memory Box MP4 (+ enhancement)

Added a pre-generated **tanpura drone** track (`backend/static/audio/tanpura_drone.mp3`, 235 KB, 60s loop) — Sa (C3 130.81 Hz) + Pa (G3 196 Hz) + Sa (C4 261.63 Hz) with subtle vibrato, soft envelope. Synthesised once via ffmpeg's sine generators so we ship it royalty-free with the repo.

`build_video()` now accepts an optional `music_path` — when set, ffmpeg loops the track to match the video length, applies 1.2s fade-in + 1.5s fade-out, mixes at 55% volume, encodes as AAC 128 k stereo. Total MP4 size grows from ~1.2 → ~1.6 MB (still well under WhatsApp's 16 MB cap).

Toggle exposed in:
- `MemoryBoxRequest.music: bool = True` (defaults ON)
- Frontend checkbox "🎵 Background music on MP4 (gentle tanpura drone)" (disabled when video is off)

Verified end-to-end via the live `/api/memory-box/view-video/{id}` stream — output has `Stream #0:1 Audio: aac, 44.1 kHz, stereo`.

---

### [2026-02-10] Animated Memory Box — MP4 video + shareable web link (P1)

**User ask**: *"can we generate something else… some animation kind of thing which opens the memory box and first will come thank you… then event photos collage of 2-3 best, then team photo with names, then 'Your Story With Us', then 10% off QR, then center QR + Insta + Website."*

**Solution**: Brand-new animated Memory Box deliverable, in addition to the existing PDF.

**6 Scenes**:
1. 📦 **Box opens** — animated gold gift-box pictogram, "Dhanyavad!" + "Thank you for hosting your <Occasion> with us." + Center name + "एक छोटीशी आठवण" Marathi tagline.
2. 🪄 **Photo collages × 3** — AI ranker scores all uploaded photos by sharpness + exposure + colour variance + resolution, picks top 6-9, splits into 3 polaroid sets of 2-3 photos with rotation & sparkle.
3. 👥 **Team** — group photo (polaroid) + gold pill cards for every team member with name + role.
4. 📖 **Your Story With Us** — LLM-written narrative recap on a cream parchment card.
5. 🎁 **Discount** — "10% OFF your next order · MEMORY10" + scannable QR encoding the promo code.
6. 📲 **Stay Connected** — center QR (Instagram / Website fallback) + Instagram handle + phone + website.

**Two deliverables generated in parallel**:
- 🎬 **MP4** — 1080×1080 square (WhatsApp + IG friendly), ~42 sec, ~1.2 MB. Built with ffmpeg (bundled via `imageio-ffmpeg`, no system dependency) using PNG-per-scene + `xfade` crossfade + `tune=stillimage` for tiny file size. PIL renders all scenes locally.
- 🌐 **Shareable web link** — public `/api/memory-box/view/{box_id}` GET endpoint serving a single self-contained HTML page with CSS keyframe animations (box lid opens, photos fade-in with stagger, team pills cascade, QR cards). Tap-to-advance + auto-play. Works on WhatsApp in-app browsers, iOS, Android.

**Stack**:
- New: `qrcode==8.2`, `imageio-ffmpeg==0.6.0` (both vendored in `backend/requirements.txt`).
- `backend/utils/memory_photo_rank.py` — Pillow-only photo scorer (no external API).
- `backend/utils/memory_video.py` — scene renderer + ffmpeg stitcher.
- `backend/utils/memory_web.py` — Jinja HTML template with CSS animation.
- `backend/utils/memory_qr.py` — shared QR generator.
- `backend/routes/memory_box.py` — `MemoryBoxRequest` extended with `generate_video / generate_web / delivery_mode / website`; new endpoints: `POST /video/{id}` (auth download), `GET /view/{id}` (public web view), `GET /view-video/{id}` (public MP4 stream for inline player).
- `frontend/src/pages/MemoryBoxCreator.jsx` — new "Animated Memory Box" form section + result UI with inline `<video>` player, Copy-link / Open / WhatsApp share buttons.

**Verified end-to-end** (`/tmp/test_memory_animated.py`):
- AI auto-picked 7 of 7 test photos, split into [3,2,2] collage sets
- MP4: 1.26 MB · 42.1 sec · h264 1080×1080 · 25fps · plays cleanly
- HTML web view: 74 KB self-contained, public link returns 200, contains all 6 scenes
- PDF still works (316 KB) — untouched

**Marathi rendering**: Devanagari font loaded explicitly for the तagline so we don't regress to tofu boxes.

**Existing PDF**: unchanged. User asked to keep it for now.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`.

---


### [2026-02-10] Commission OVERVIEW vs LEDGER parity fix (P0 — financial)

**User report**: *"Commission amount OVERVIEW madhye Actual peksha JAST yet aahe LEDGER madhye correct aahe Zomato upload kelyavar HSR & S NAGAR"* — the Overview / Status Card / WC Table showed a higher commission than the Ledger after Zomato Excel upload.

**Root cause**: Two MongoDB aggregations in `routes/center_accounts.py` (lines ~185 inside `calculate_working_capital_standing` and ~506 inside `get_wc_table`) summed FOUR fields together:
```
commission_amount + other_deductions + gst_tax_deductions + tds
```
For new Zomato/Swiggy parser uploads this:
1. Was correct for `commission_amount` (always 0 in new schema) — no harm but redundant.
2. **Inflated by `tds`** — TDS is booked as a separate operating expense (per canonical helper `utils/commissions._row_total`); summing it here double-counts.

The Ledger (`build_commission_ledger`) and MIS Dashboard (`get_total_commissions`) both use `_row_total` semantics: `gst_tax_deductions + other_deductions` if populated, else `commission_amount`. NEVER TDS.

**Fix**: Rewrote both aggregations to mirror `_row_total` exactly using a `$cond` expression. Also corrected legacy `commission_statements` to be a fallback (used only when monthly_commissions has nothing for that month) — previously they were additively merged, causing further drift on centers with both data sources.

**Verified end-to-end** (PB-SN 2026-02 via `/api/center-accounts/summary` + `/wc-table`):
- Old buggy total: 9984.50 (TDS inflated by 20.34)
- New total: **9964.16** — matches Ledger / canonical / `_row_total` to the paise

**Regression tests added** (`backend/tests/test_commission_overview_vs_ledger_parity.py`):
- `test_overview_aggregation_matches_canonical_row_total` — synthetic Zomato+Swiggy rows; agg == canonical for every month ✓
- `test_tds_is_excluded_from_overview` — TDS-only row contributes 0 ✓
- Existing `test_iteration84_commission_parity.py` — all 5 pass ✓

**Files changed**: `backend/routes/center_accounts.py` (2 aggregation blocks).

⚠️ **Click Deploy** to push to `intra.purnabramha.com`.

---


### [2026-06-03 PM v2] Free-flow AI creative + reliable brand overlay (P0 FIX — corrected)

**User correction**: *"i dont want fixed layout why are not understanding et it be free flow .. still no text overlay no logo is visible on the image"* — rejecting the deterministic two-column composer from v1 of this fix.

**Corrected approach**:
- AI (Nano Banana) gets **total creative freedom** to compose varied premium Maharashtrian ads each generation — split panels, full-bleed, framed cameos, diptychs, asymmetric, textile collage, whatever feels fresh.
- The guest photo is sent back to Nano Banana as a reference image so it integrates the real face/group elegantly into ITS composition (no Pillow side-paste).
- New `apply_smart_brand_overlay()` in `text_overlay.py` adds ONLY three things on top — never touches the AI layout:
  1. Bilingual caption on a soft cream pill positioned in the **calmest top corner** (auto-detected via per-corner variance scoring)
  2. Circular Purnabramha logo medallion in the **opposite corner** (also auto-detected)
  3. Thin chocolate brand strip at the very bottom: "Purnabramha — Authentic Maharashtrian Cuisine"
- Hard-fails (HTTP 500) if overlay raises — no more silent skips that leave the ad blank.
- `_corner_calmness()` resamples each candidate region to 48×48 grayscale, computes variance + mid-tone preference; lowest score = calmest = chosen.

**Removed**: the deterministic `compose_premium_ad` two-column composer (v1 of this fix). It still exists in code for reference but is no longer called.

**Verified end-to-end**:
- Product-only call (no photo): ad_id `76d3c1dd-…` — caption, logo, brand strip all present ✓
- With guest photo: ad_id `2e915b92-…` — AI freely composed a paisley + portrait + Puran-Poli ad; smart overlay placed Marathi text top-right, circular logo bottom-left, brand strip at bottom. Independent analyzer scored **8/10** premium ✓
- Preview viewable at: `{REACT_APP_BACKEND_URL}/static/freeflow_p.png`

**Files changed**:
- `backend/utils/text_overlay.py` — added `_corner_calmness`, `_pick_corners`, `apply_smart_brand_overlay`.
- `backend/routes/marketing_ads.py` — `_build_image_prompt` rewritten for free-flow creative; `/api/marketing/ads/generate` now (a) re-sends the guest photo to Nano Banana as a reference, (b) calls `apply_smart_brand_overlay` instead of `compose_premium_ad`, (c) hard-fails on overlay errors.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. All preview tests confirm the fix works.

**Hotfix [2026-06-03 PM v3]**: Production reported `Brand overlay failed: '_io.BytesIO' object has no attribute 'lower'`. Root cause: PIL 12.1.1's `ImageFont.load_default()` returns a font whose `.path` is a `_io.BytesIO` object, not a str. My `_wrap_to_width()` called `.lower()` on it. Fixed by adding `isinstance(_path, str)` guard. Verified end-to-end (ad_id `93e9bcf3-…`) — Nikam couple anniversary ad rendered cleanly with the user's exact form input. **Redeploy required**.

**Hotfix [2026-06-03 PM v4]**: After v3 deploy, user reported two issues on the produced ad:
1. **Tofu (☐☐☐) boxes** at top of cream pill — production container lacked the Noto Sans Devanagari font, so Marathi rendered as missing-glyph placeholders.
2. **Text pill covered the couple's faces** — corner-calmness scoring picked the top-left paisley band which actually extended over the people.

Fixes:
- Bundled fonts **into the repo** at `backend/static/fonts/` (NotoSansDevanagari Bold/Regular, LiberationSerif Bold/Regular/Italic). Font discovery now prefers bundled paths and falls back to system. Production will ALWAYS render Devanagari correctly.
- `_pick_corners()` redesigned: evaluates all 4 corners (TR/TL/BR/BL), shrinks the pill to 38% × 17% (was 46% × 22%), adds **saturation** to the calmness score so gold paisley areas correctly score as "busy" instead of "calm". Logo lands in the geometrically opposite corner for visual balance.
- Caption truncation tightened (Marathi 50, English 70, byline 26) so the smaller pill never overflows.

**Verified end-to-end** (ad_id `bcdf8f06-…`): Marathi caption renders perfectly in Devanagari, pill lands in TOP-RIGHT, logo in BOTTOM-LEFT, no face occlusion. Independent analyzer scored **8/10**. **Redeploy required.**

### [2026-06-03 PM v5] Party Invitation polish — optional footer + host name size + extras

User request: *"foot note at party invitation should be optional, host name are too big should have option to choose size, anything which u feel is better add that as well"*

Added 5 new optional invitation controls (`backend/routes/marketing_ads.py` `InvitationRequest` model, `backend/utils/text_overlay.py` `apply_invitation_overlay()`, `frontend/src/pages/InvitationCreator.jsx` form):

1. **`show_footer`** (bool, default `true`) — toggles the "With warm regards · Purnabramha / पुर्णब्रह्म परिवाराकडून प्रेमपूर्वक" brand footer.
2. **`host_name_size`** ('S' / 'M' / 'L', default 'M') — S=72pt compact, M=96pt default, L=124pt poster hero (was a fixed 112pt). Auto-shrinks to fit 2 lines max.
3. **`save_the_date`** (bool, default `false`) — shows a gold-outlined "SAVE THE DATE · वाचवा हा दिवस" pill above the occasion line.
4. **`rsvp_contact`** (string, optional) — adds a small "RSVP · +91 …" cream line near the bottom of the panel.
5. **`dress_code`** (string, optional) — adds a small gold-uppercase "DRESS CODE · …" line.

Bonus reliability fix: the dark-chocolate panel now **auto-grows** between 55-70% of canvas height based on how many optional fields are populated. Previously content overflowed off the bottom when L size + all optional fields were on; now everything fits cleanly.

**Verified end-to-end** (preview): all 11 elements visible inside the panel when every option is on (analyzer Layout 8/10, Readability 9/10), brand footer correctly hidden when toggled off. UI form gained a "Polish" section with 5 controls (data-testid: `invite-host-size`, `invite-dress-code`, `invite-rsvp`, `invite-save-the-date`, `invite-show-footer`).

⚠️ **Redeploy required.**

### [2026-06-03 PM v6] Video Creator — polish controls + Instagram audio suggestions

User request: *"the videos should also have option for all footer note, sizes of headline and subheading and anything u recommand , like any music which goes gr8 with that video so that managers can pull that on instagram"*

Added 3 control + 1 power feature to `backend/routes/video_overlay.py` + `frontend/src/pages/VideoCreator.jsx`:

1. **`show_footer`** (bool, default `true`) — toggles the sub-line + byline. When OFF, the chocolate strip auto-shrinks from 30% to 20% of video height and the headline is centered inside it for a minimal "single line" look.
2. **`headline_size`** ('S' / 'M' / 'L') — drives `fontsize` (h/11, h/9, h/7). L is poster-sized.
3. **`subline_size`** ('S' / 'M' / 'L') — drives `fontsize` (h/20, h/16, h/13).
4. **NEW endpoint `POST /api/marketing/videos/music-suggestions`** — uses Claude (Emergent Universal Key) to suggest 5 Instagram Reels audio tracks that pair well with the video's headline/sub-line/occasion. Returns track name, artist, vibe, why-it-fits, and a deep-search Instagram URL.

Bonus reliability fix: ffmpeg y-positions for headline/sub/byline are now **dynamically computed** from the font-size ratios so the larger L headline never overlaps the sub-line.

**Verified end-to-end**:
- Video V1 (footer ON, headline L, sub M): Marathi "पुरणपोळी मऊ मखमली" + English "Authentic since 2008" + "— Jayanti Kathale —" + circular logo. Independent analyzer **9/10** readability, no overlap.
- Video V2 (footer OFF, headline M): minimal 20%-tall chocolate strip with only the headline centered.
- Music endpoint: returns 5 hand-curated Marathi devotional/folk/instrumental tracks (Mauli Jaidev, Dhol Tasha, Sairat Zala Ji, Flute Marathi, Apsara Aali) with Instagram audio search URLs.

UI: added "Polish" section with `video-headline-size`, `video-subline-size`, `video-show-footer` controls; new "Suggest Instagram Audio" button (data-testid `video-music-suggest`) opens a panel with clickable track tiles.

⚠️ **Redeploy required.**

### [2026-06-05 v2] Memory Box — culturally-correct Marathi blessings (P0 FIX)

User feedback: *"see the text is not correct"* — pointed out previous GPT-generated blessings contained Devanagari typos ("वाढदविसाच्या" → should be "वाढदिवसाच्या", "हार्दकि" → "हार्दिक") and lacked the traditional "श्री स्वामी समर्थ" invocation cadence.

User-provided gold standard:
```
श्री स्वामी समर्थ.
आयुष्य दीर्घ असो, आरोग्य उत्तम लाभो, सुख-समृद्धी नित्य वाढो.
कुटुंबात प्रेम, ऐक्य आणि आनंद सदैव नांदो.
```

Fix in `_gpt_story()` (backend/routes/memory_box.py):
1. **Per-occasion anchor blessings**: hand-curated, Marathi-verified templates for Birthday, Anniversary, Wedding, Naming, Housewarming, + default.
2. **Strict Marathi accuracy rules** in the GPT prompt — explicitly lists common misspellings to avoid (वाढदविस, हार्दकि, आर्शीवाद, वर्धापनदनि) and shows the anchor as a few-shot example.
3. **System message upgrade**: GPT now told it is *"NATIVE-FLUENT in Marathi and never produces a misspelled Devanagari word"*.
4. **Safety net post-process**: if the GPT output still contains any flagged typo OR returns empty, we substitute the occasion's anchor blessing automatically.
5. Deterministic fallback (when GPT is unavailable) now also uses the user's gold-standard blessing — never English.

**Verified end-to-end**:
- Anniversary box `788e257c-…` → `श्री स्वामी समर्थ. तुमचे सहजीवन प्रेम, विश्वास आणि आनंदाने बहरलेले राहो. एकमेकांची साथ, समजूत आणि आदर सदैव वाढत जावो.` ✓
- Birthday box `e0bec416-…` → `श्री स्वामी समर्थ. वाढदिवसाच्या हार्दिक शुभेच्छा; आयुष्य दीर्घ असो, आरोग्य उत्तम लाभो, सुख-समृद्धी नित्य वाढो. कुटुंबात प्रेम, ऐक्य आणि आनंद सदैव नांदो.` ✓ (correctly spelled "वाढदिवस" and "हार्दिक", invocation prefix present)

Preview Birthday PDF: `https://balance-cascade-fix.preview.emergentagent.com/static/membox_birthday_v7.pdf`

⚠️ **Redeploy required.**

## What's Been Implemented (Latest)

### [2026-06-05 v4] Memory Box — language, font sizes, artistic collage, shareable summary image

User request — 5 items:
1. Language picker (English / Marathi / Bilingual)
2. Font size picker (Small / Medium / Large)
3. Per-center social link — DONE in v3, confirmed visible on the form
4. Replace the block-grid photo page with TRUE artistic collage templates (multiple creative styles)
5. ADD a single-page summary image (in addition to the PDF) containing ALL highlights

**Implementation**:

1. **Language toggle** (`MemoryBoxRequest.language`)
   - `English` → story/gratitude/future_invitation in English. Blessing stays in Marathi as a cultural anchor (matches Indian practice).
   - `Marathi` → all 4 sections in Devanagari.
   - `Bilingual` (default) → English narrative + Marathi blessing.
   - GPT prompt rewritten with explicit `lang_rules` block; safety net skips its Devanagari fallback in English mode.

2. **Font size picker** (`MemoryBoxRequest.font_size`) — S=0.85×, M=1.0×, L=1.18×. Applied to every heading + body ParagraphStyle via a single `_fs()` helper.

3. **Per-center social link** — already implemented in v3; confirmed UI is showing the Instagram + Phone inputs under "Center Branding & Booking QR" inside the Memory Box form.

4. **True artistic photo collage** — `_render_artistic_collage()` (Pillow, 6.4"x7.4" @ 200 dpi) picks ONE of 4 creative templates:
   - **Polaroid Scatter** — 4-6 rotated polaroids with paper texture + masking tape strips
   - **Magazine Mosaic** — 1 hero photo + asymmetric tiles in cream/gold frames
   - **Filmstrip** — wide hero banner + horizontal black-filmstrip with perforation dots
   - **Mandala Radial** — circular hero + 4-6 mini circular thumbnails arranged radially
   - Template chosen per-call via deterministic seed; outer gold double border, paisley dot texture, drop shadows on every tile. Replaces the boring hero-plus-grid layout from v3.
   - Independent analyzer (post-test): *"definitively artistic, not block-grid... reminiscent of a casual collage / scrapbook with overlapping and slightly askew photos + masking tape tabs."*

5. **Single-page summary image** — `_render_cover_png()` upgraded from a thank-you cover into a comprehensive WhatsApp-shareable card (1080×1620 PNG):
   - Top: logo + brand + bilingual "MEMORY BOX · आठवणींची पेटी" header
   - Big guest name in gold
   - Occasion + date pill
   - 3 tilted photo thumbnails in a strip
   - Marathi blessing snippet
   - "SCAN TO BOOK" QR card on left + contact info on right
   - Gold brand footer with center name + bilingual Marathi line
   - Returned as `cover_png_base64` in the existing API response.
   - Independent analyzer: **8/10** WhatsApp-shareable card with all 8 elements verified present.

**Frontend** (`MemoryBoxCreator.jsx`):
   - New "Personalisation" panel with Language + Font Size dropdowns (data-testid `mb-language`, `mb-font-size`).
   - New "Summary Image" download button next to the existing PDF button (data-testid `mb-download-png`).

**Verified end-to-end**:
- English / Marathi / Bilingual modes all generate correctly (`194061a9-…`, `d5e357c6-…`, `086cfcae-…`).
- Latest sample (`c9c0314d-…`) confirmed collage is artistic + summary image looks premium.
- Preview PDF: `https://balance-cascade-fix.preview.emergentagent.com/static/membox_v9.pdf`
- Preview Summary Image: `https://balance-cascade-fix.preview.emergentagent.com/static/membox_v9.png`

⚠️ **Redeploy required.**



### [2026-06-05 v3] Per-center branding + Booking QR across ALL creatives

User request: *"can u add the website link, insta page link and QR code for them, for each center it is different link for social media, website is one and QR code is one for all kind of bookings, and center number to get added"* + later: *"give option for center's admin panel"*

**Implementation**:

1. **Schema + Admin UI (`backend/routes/centers_managers.py` + `frontend/src/pages/CentersManagement.jsx`)**:
   - Added `instagram_url` field to `centers` collection. Wired through `mgt_center_create` and `mgt_center_update` endpoints.
   - Added "Instagram URL" input to both the Add Center and Edit Center dialogs (data-testid `center-instagram-input`, `center-instagram-edit-input`).

2. **New `POST /api/mgt/center_branding` endpoint** (centers_managers.py):
   - Returns `{code, name, phone, email, address, instagram_url}` for a single center.
   - Uses async `check_access` so any logged-in session works.

3. **QR code asset**: User's booking QR image saved at `backend/static/purnabramha_booking_qr.png` — embedded into all 4 creatives.

4. **Ad Creator (`backend/routes/marketing_ads.py` + `frontend/src/pages/AdCreator.jsx`)**:
   - Added `instagram_url`, `phone`, `show_qr` fields to `AdGenerateRequest`.
   - `apply_smart_brand_overlay` extended to render: (a) Scan-to-Book QR card with cream backdrop + gold border in the opposite corner from the logo, (b) two-line chocolate brand strip: line 1 brand line, line 2 `www.purnabramha.com · @handle · +91 …`.
   - Frontend auto-fetches branding when center changes; manager can override.
   - Composition rated 8/10 by independent analyzer; all 4 elements confirmed.

5. **Invitation (`apply_invitation_overlay` in text_overlay.py)**:
   - Same `instagram_url`, `phone`, `show_qr` flow.
   - Renders a small QR card inside the dark panel + a single gold contact line above the brand footer.

6. **Memory Box (`backend/routes/memory_box.py`)**:
   - Cover page: small "SCAN TO BOOK" QR badge + gold contact line under center name.
   - Final page: dedicated dark-chocolate "Book Your Next Celebration" card with the QR on the left and `+91 phone / @handle / www.purnabramha.com` on the right.

7. **Video Creator (`backend/routes/video_overlay.py` + `VideoCreator.jsx`)**:
   - Form accepts `instagram_url` and `phone` (auto-filled from center).
   - The contact line is appended to the existing sub-line so it appears in the chocolate strip alongside the existing branding.

**Verified end-to-end**:
- Branding endpoint: `POST /api/mgt/center_branding` returns the new `instagram_url` field.
- Ad preview: `…/static/ad_with_qr.png` (8/10 by analyzer, all 4 elements present).
- Memory Box preview: `…/static/membox_branded_v8.pdf` — analyzer confirmed cover QR + gold contact line + last-page booking card.

⚠️ **Redeploy required.**



### [2026-06-05] Memory Box PDF — creative collage + per-member team avatars + gold-on-chocolate roster (P0 FIX)

User feedback: *"all the memory box pdf are creating good but images are just coming as block instead create some creative box placing of images and team image should one which is right but team names are coming with black font i mean basic are error"*

Three confirmed bugs fixed in `backend/routes/memory_box.py`:

1. **Team names rendered in black** — root cause: `Table` `TEXTCOLOR` style was only set for the header row, leaving data rows at the ReportLab default (black). Fixed: replaced the entire team table with a **circular initial-avatar grid** (3 per row) where each cell has a chocolate background, gold border, gold-bright `Aniruddh Suryawanshi` initials in a `Circle()` flowable, cream member name, and gold-bright role tag.

2. **Generic single team photo** — root cause: previous design just pasted one large group photo for the whole team. Fixed: new `_initial_avatar_flowable(name)` helper renders a gold-ringed chocolate disc with the member's initials (Slack-style avatar). The group `team_photo` (if uploaded) still shows but as a smaller cream-framed banner above the avatar grid, not as the sole representation.

3. **Plain rectangular photo grid** — root cause: `Page 3` was a uniform 3×3 grid. Fixed: new `_build_scrapbook_pages()` helper composes:
   - **Hero photo** (6" × 3.4") on top with cream + gold-bright frame
   - **4 smaller tiles** (2.9" × 2.0") in a 2×2 grid below, each with cream + gold frames
   - **Overflow page** (only when >5 photos): 6 more tiles in 2×3 grid

Plus: Bundled Devanagari + Liberation fonts are now preferred over system paths so the PDF renders correctly on any container (same fix pattern we applied to the ads).

**Verified end-to-end** (preview box `5b074c60-…`): independent analyzer confirms team names render in gold/cream, circular initial medallions present for every member, photos in hero+tile layout with cream/gold frames.
Preview: `https://balance-cascade-fix.preview.emergentagent.com/static/memorybox_v6.pdf`

⚠️ **Redeploy required.**



### [2026-06-03] One logo only + new official logo PNG (BUG FIX)

**User report** (production): "Use one logo not multiple please — I am loading both the logos again." + uploaded fresh `Logo of Purnabramha.pdf` (4500×4500 official wordmark with bilingual `purnabramha` / `पूर्णब्रम्ह`, tagline *"The Largest Authentic Maharashtrian Restra"*, *"Manaswini Foods Pvt.Ltd"*, country list, ® mark).

**Root cause**: Invitation flow was rendering TWO logos:
1. The AI prompt told Nano Banana *"PURNABRAMHA LOGO at the very TOP, centered, large (~18% of canvas height). The logo is provided as the LAST reference image — reproduce EXACTLY."* AND we sent the logo as a reference image.
2. Then `apply_invitation_overlay()` pasted ANOTHER logo top-right via Pillow.

**Fix**:
1. **Replaced logo**: extracted the new PDF to a 3240×3402 transparent PNG (white pixels → alpha=0 with feathered edge, auto-trimmed). Old logo backed up as `purnabramha_logo_v1.png`.
2. **Invitation prompt rewritten** — top section now reads: *"DO NOT draw any logo. The brand logo is rendered crisply on top of your image by our server — leave the TOP-RIGHT corner visually CLEAN."* + explicit forbidden list: *"DO NOT render the word 'Purnabramha', 'पूर्णब्रम्ह', 'Manaswini Foods', or any variant. DO NOT draw a logo, mandala-with-text, or wordmark."*
3. **Logo no longer sent as a reference image** to Nano Banana (it was a key trigger for the AI to "reproduce" a logo). Only the host photo is passed.
4. **Marketing Ad prompt** also strengthened with the same "LOGO-SAFE ZONE" block to prevent any future leak.

**Verified**: invitation generated in 1088.8 KB, single Pillow-rendered logo top-right only (AI no longer drew a centered logo).

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. Every new creative now uses the new official logo, rendered exactly once.


### [2026-06-03] PURNABRAMHA Brand Design System v2 — Premium upgrade across ALL creatives

**User mandate** (verbatim): "All creatives — Marketing Ad, Party Invitation, Memory Box, Event Invitations, Catering, Festival, WhatsApp, Social Media, Memory Book PDFs — must follow a premium Purnabramha brand identity. Should feel warm, premium, traditional, emotional and culturally rich. Should NEVER look like a generic Canva template."

**User design decisions** (1c, 2a):
- 1c: Chocolate band for Marketing Ad / Video; **FULL chocolate** for Invitation / Memory Box
- 2a: When "English" language is selected, output English ONLY (when "Bilingual" → both)

**Official Brand Palette (2026)**:
- Dark Chocolate Brown `#2B1810` — primary background
- Rich Antique Gold `#BF8C32` / bright `#DCAE50` — headings, borders, accents
- Deep Maroon `#660E0E` — festive / celebration
- Warm Cream `#FAF0DC` — readability

**Changes**:

**`backend/utils/text_overlay.py`** — Brand colour constants rewritten. `apply_overlay()` (Marketing Ad band): chocolate gradient band (was black/maroon), gold top-border, **paisley dot row** centered inside band, fonts +39–47% (Marathi 78pt, English 50pt italic, byline 34pt, brand 36pt), gold-bright headline with shadow, divider between scripts. `apply_invitation_overlay()` (Party Invitation panel): **full chocolate panel** (was cream semi-transparent), antique-gold DOUBLE border + 4 paisley corner ornaments, host name 90pt+ (was 64pt) — visual hero, occasion bilingual (Marathi 52pt + English italic), date/time 44pt cream, venue 36pt gold, bilingual brand footer (English + Marathi *"पुर्णब्रह्म परिवाराकडून प्रेमपूर्वक"*).

**`backend/routes/marketing_ads.py`** — `BRAND_COLORS` and `BRAND_DESIGN` strings rewritten with official palette + traditional motifs (paisley, rangoli, warli, temple bells, diyas, marigold, banana-leaf, brass-copper). Added BILINGUAL ENFORCEMENT block in Claude caption prompt: *"If language is Bilingual, BOTH marathi and english MUST be filled with substantive content. Do NOT transliterate."*

**`backend/routes/memory_box.py`** — 7-page PDF: **full chocolate page background**, antique-gold double border, 4 corner paisley ornaments on EVERY page (via `onFirstPage`/`onLaterPages` canvas hook). Heading fontsize 22 → 30 (+36%), H2 24, body 14 (was 11.5, +22%), blessing 18 (was 14, +29%). Cover page now has bilingual subtitle *"आमच्या सोबत आनंदाचे क्षण साजरे केल्याबद्दल धन्यवाद"*. Bilingual brand sign-off on page 7. **Cover PNG**: chocolate background (was cream), gold double border + paisley corner ornaments + paisley dividers, host name 72pt (was 56pt), 84pt heading, full bilingual greeting.

**`backend/routes/video_overlay.py`** — ffmpeg `drawbox` filter now uses chocolate `#2B1810@0.85` (was black@0.55), antique-gold border line, headline font `h/12` (was `h/16`, +33%) in `#DCAE50`, sub `h/22` (was `h/28`, +27%) in `#FAF0DC` cream.

**Verified end-to-end**:
- Marketing Ad overlay: sampled bottom-center pixel = `(92, 62, 39)` (chocolate gradient) ✓
- Invitation overlay: sampled panel pixel = `(52, 31, 20)` (full chocolate) ✓
- Memory Box: 265 KB valid PDF; cover PNG bg pixel = `(43, 24, 16)` = **exact DARK_CHOCOLATE match** ✓
- Memory Box bilingual cover greeting + brand sign-off in Devanagari rendered crisply ✓
- Video overlay: 66.5 KB valid MP4 with chocolate band + gold/cream text + Marathi headline ✓

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. After deploy, every creative — Marketing Ad / Party Invitation / Memory Box PDF + cover / Video — uses the new premium Purnabramha 2026 design system with significantly larger typography and proper bilingual rendering.


### [2026-06-03] Marketing Ad — Menu image "food-only" + Group photo contain-fit (BUG FIX)

**User report** (production screenshot): "The use of menu photo and multiple face photos is not working."

**Two distinct bugs found**:

1. **Menu reference photo leaked people into the AI output** — when the menu image is a marketing poster (e.g. a Shrikhand poster containing a kid + decorative text), Nano Banana saw the kid and copied it into the output despite the global "NO PERSON" rule.
2. **Multi-face composite cropped outer faces** — wide group photos (aspect > 1.3:1) were forced into a tall left panel using cover-fit, which crops the outer 30-40% of the photo (i.e. the people on the edges disappear).

**Fixes**:

1. **`routes/marketing_ads.py::_build_image_prompt`** — Menu directive completely rewritten as a FOOD-ONLY EXTRACTION block:
   > "A reference image is provided. It MAY contain people, faces, decorative text, marketing layouts, or other clutter — IGNORE ALL OF THAT. Extract ONLY the FOOD content from the reference: the dish, plating, vessel, garnish, colour, portion. DO NOT copy any human face, child, person, model, hand, body part, text letter, logo, or watermark from the reference image."
   Also added a global GENERAL RULES line: *"If ANY reference image contains a person/child/face, do NOT carry that person into the output."*

2. **`utils/text_overlay.py::composite_guest_photo`** — New `is_group` argument:
   - `is_group=True` → **contain-fit** (entire photo visible, cream letterbox bars on sides if needed). Every face preserved.
   - `is_group=False` → cover-fit (faces dominate, slight edge crop). Good for single-person.

3. **`routes/marketing_ads.py::generate_ad`** — Auto-detects `is_group_auto = req.is_group_photo OR (photo.width / photo.height >= 1.3)`. The manager doesn't have to tick the checkbox for landscape group photos — wide aspect triggers contain-fit automatically.

**Verified end-to-end** (test: wide 3-face group photo `1200×600` + menu poster containing a kid):
- 1,059 KB ad ✓
- All 3 skin tones from the group photo present in the left panel: `(240,201,170)` + `(220,181,150)` + cream `(253,246,231)` bars on either side ✓
- Right (food) half = food browns/golds only (no skin) — menu poster's kid was NOT copied into the output ✓
- Caption: *"बालगोपाळ रियाजींनी श्रीखंड-पुरी-भाजी संपवली — आजचे गोल्डन तारा चॅम्पियन! ⭐"* ✓

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. After deploy:
- Menu/dish posters with people in them → only the food is extracted, no person leak.
- Wide group photos → every face preserved (no edge cropping).


### [2026-06-03] Marketing Ad — Guest photo composited as-is (NEVER AI-stylized)

**User report** (verbatim, screenshot from production): "Why are we not taking photo of guest as is and create the creatives as visible as possible" — Balgopal generation was showing an AI-painted child face that did NOT match the uploaded photo (group of 2 people uploaded → 1 stylized child rendered).

**Root cause**: Nano Banana (Gemini-3 image) is unreliable at preserving real faces from a reference photo — it tends to "interpret" rather than reproduce. We were trusting it to embed the guest's face.

**Fix — hybrid AI + Pillow compositing**:

1. **AI prompt now explicitly forbids drawing any person** when a guest photo is provided. New person block: *"NO HUMAN FIGURE IN THIS GENERATION. DO NOT add any human face, head, body, hand, silhouette, child, or person. DO NOT redraw, stylise, or interpret any guest. Leave the LEFT 45% of the canvas completely clean (cream/gold soft texture, NO food, NO person, NO objects) — the real guest photo will be pasted there."*

2. **Guest photo is NO longer sent as a reference to Nano Banana** — we only send the menu/dish image if uploaded. AI generates ONLY the brand backdrop + food on the right half.

3. **New `utils/text_overlay.py::composite_guest_photo()`** — Pillow pastes the actual uploaded photo on the LEFT panel (or TOP half for 9:16 vertical) with:
   - Proportional cover-fit (faces dominate the frame)
   - Cream card background + drop shadow (premium look)
   - Gold rounded-corner inner border (matches brand)
   - **Balgopal mode**: gold 8-point star burst behind the photo with soft glow (Gaussian-blurred) — visually celebrates the kid as a "Star Eater" without altering the real face.

4. Pipeline order: AI generates clean backdrop + food → Pillow composites guest photo → Pillow overlays Devanagari caption + transparent logo.

**Verified end-to-end** (PB-MGT, Balgopal Riya, test photo with `skin=(240,200,170)`):
- 950.2 KB ad generated ✓
- Sampled left-panel pixels = `(240, 201, 170)` = **exact match with uploaded photo** (off-by-1 = JPEG round-trip) — confirms the real photo pixels are preserved, NOT re-painted ✓
- Caption: *"बालगोपाळ रियाजींनी विशेष मोदक ताट संपवली — आजच्या अन्नदात्याच्या मित्राला ⭐ स्वर्णतारा!"* (kid finished the special modak plate; today's farmer-friend earns a gold star) ✓
- Group photos: every face in the original upload is preserved because we paste the WHOLE image, not a stylization.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. After deploy, every guest's face appears in the ad exactly as uploaded — no more AI re-interpretation.


### [2026-06-03] Marketing Ad — free-text menu, dish photo upload, Balgopal kids mode (NEW)

**User asks** (verbatim, on production):
> "only asking menu item name allow center manager to upload the menu. If any Balgopal details been placed then please consider this is kids creatives — who finish there food and enjoying star and becoming super queen and super hero and farmer friend. Don't give drop down of menu, give text box and image uploading."

**Backend** (`routes/marketing_ads.py`):
1. `AdGenerateRequest` extended with `menu_item_image_base64: Optional[str]` — when present, passed to Nano Banana as a second reference image with prompt: *"DISH REFERENCE PHOTO — AUTHORITATIVE. Use THAT image as the ground truth for what the food looks like… do NOT swap to a stock interpretation."*
2. New helper `_is_balgopal(guest_name, subject_text)` — detects "balgopal" / "बालगोपाळ" in either field (case-insensitive).
3. **Balgopal image prompt branch**: when triggered + has photo → preserves kid faces, shows **CLEAN/EMPTY plate** with crumbs as "proof of finished with love", adds ONE motif (gold star burst / superhero cape & dupatta / farmer's hat + wheat sprigs) — storybook-watercolour, NOT cartoony. Without photo → illustrative kid hero scene, no specific child face.
4. **Balgopal caption brief** added to Claude prompt with 3 archetype examples (Star Eater / Super Hero–Queen / Farmer Friend). New JSON example with "बालगोपाळ रिया → आजची स्टार खाद्यवीर ⭐" output.
5. New record fields: `has_menu_image`, `is_balgopal` (persisted in `ad_creations`).

**Frontend** (`pages/AdCreator.jsx`):
1. Menu Item field changed from `<Select>` dropdown → `<Input>` with HTML `<datalist>` suggestions from `masters.menu_items` (manager can pick from history OR type anything).
2. New "Menu / Dish Photo" upload row below the menu input (8 MB max, optional). Preview thumbnail + Remove button.
3. New **Balgopal mode badge** that auto-appears (amber/rose gradient with ⭐) whenever `guest_name` or `subject_text` contains "balgopal" / "बालगोपाळ" — copy: *"The ad will celebrate the child finishing their plate as a Star Eater / Super Hero–Queen / Farmer Friend."*

**Verified end-to-end via curl** (PB-MGT, Balgopal Riya, "Finished her plate of Puran Poli"):
- 200 OK, 1224.9 KB image generated ✓
- Caption (Marathi): *"बालगोपाळ रियाजींनी ⭐ स्टार खाद्यवीराचं नाव — पुरणपोळीची ताट संपवली, एकही दाणा न ठेवता!"* ✓
- Caption (English): *"Balgopal Riya earned today's Star Plate — finished every bite of her Puran Poli! 🌾"* ✓
- Headline: *"बालगोपाळ रिया → आजची स्टार खाद्यवीर ⭐"* ✓

**Lint**: clean (frontend + backend).

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. After deploy: Marketing Ad form lets manager TYPE the menu item + UPLOAD a dish photo; mentioning "Balgopal" auto-switches to the kids' champion creative theme.


### [2026-06-03] Transparent logo everywhere

**User ask** (verbatim): "kindly use transparent logo for all places"

**Implementation**:
- Created `/app/backend/static/purnabramha_logo.png` — a 444×422 transparent PNG generated from the existing JPG by mapping near-white pixels (brightness ≥ 230) to full transparency with a feathered alpha edge for crisp anti-aliasing. Transparent borders auto-trimmed for tight cropping.
- Updated all 3 backend logo references (`routes/marketing_ads.py`, `routes/memory_box.py`, `routes/video_overlay.py`) — all now point at the PNG.
- Removed the soft white "halo" rectangle that was previously painted behind the logo in `utils/text_overlay.py::apply_overlay()` and `apply_invitation_overlay()` — the transparency now renders cleanly over the AI background.
- Memory Box cover PNG, Memory Box PDF, Marketing Ad overlay, Party Invitation overlay, and Video Overlay (ffmpeg) all now respect the alpha channel automatically (Pillow `paste(im, pos, im)` + ffmpeg overlay filter both honor PNG transparency).
- Old JPG kept on disk as a fallback (no removal, zero regression risk).

**Verified**:
- Pillow overlay smoke test: dark background (40,25,25) → top-right logo region pixel = (40,25,25) i.e. background bleeds through transparent edges = transparency confirmed ✓
- Video overlay: 71.2 KB MP4 generated with logo + Marathi sub-line ✓

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. After deploy, every newly-generated Marketing Ad, Party Invitation, Memory Box PDF/cover, and Branded Video uses the transparent logo — no more white rectangle around it.


### [2026-06-03] Invitation prompt — multi-person-aware by DEFAULT (no checkbox required)

**User report** (verbatim): "Party invitation is still taking single person photo many times — it comes as couple who is hosting party or team who is hosting it, so any one single photo is not the right approach."

**Fix** (`routes/marketing_ads.py::_build_invitation_prompt`):
- Removed the implicit "single host" default. The DEFAULT prompt now reads: *"FIRST reference image contains the host(s). Examine it carefully — it may be a SINGLE person, a COUPLE, a FAMILY, or a TEAM. Whatever the count, preserve EVERY face you see — do NOT crop anyone out, do NOT remove people, do NOT replace any face."*
- Frame adapts to count: **circular gold-rim** only when exactly 1 person; **rounded rectangular** when 2+ people (circles crop people out).
- Added a fresh `PEOPLE PRESERVATION — CRITICAL` block to the prompt: *"If you cannot fit everyone gracefully in a circular frame, switch to a wider oval or rectangular ornate frame — never sacrifice a face."*
- The `is_group_photo` checkbox now only ADDS extra emphasis (gold ornate rectangular frame regardless), never relaxes the rule.

**Net effect**: Even WITHOUT ticking the checkbox, a couple/family/team uploaded as the host photo is preserved in full. No more single-face cropping by default.

⚠️ **Click Deploy** to push the change to `intra.purnabramha.com`.


### [2026-06-03] Creative Studio v2 — Group-photo support, crisp Marathi overlay, Video branding (NEW MAJOR FEATURES)

**User asks** (verbatim, on production):
1. "If I add a group photo, it takes a single photo of person and not creating group creatives for both marketing and party as well for memory box — please solve."
2. "For Marathi script it is creating a lot of errors. We have to redesign the creatives — which is another headache."
3. "Like upload images can we upload a few videos which u just create with logo on it and add text overlay on it."

**User decisions** (1c, 2b, 3a):
1. Both — checkbox + auto-detect group photos
2. Redesign — AI generates clean visual ONLY; we overlay crisp Marathi server-side with Pillow + Noto Sans Devanagari
3. Manager uploads existing phone clip → we burn logo + caption with ffmpeg

**Backend**:
- **NEW `backend/utils/text_overlay.py`** — Pillow text overlay engine. Auto-picks Devanagari font when text contains `\u0900-\u097F`, falls back to Liberation Serif for Latin. Two main helpers: `apply_overlay()` for marketing ads (gradient band + headline + sub + byline + logo) and `apply_invitation_overlay()` (lower-half info-panel with host, date/time, venue, address, menu, custom message — all crisp Devanagari). `OCCASION_MARATHI` lookup for 13 occasions.
- **`routes/marketing_ads.py`** — `is_group_photo: bool` added to AdGenerateRequest + InvitationRequest. Image prompts rewritten to instruct Nano Banana to **NOT render ANY text** (leaves clean band/lower 45% for our overlay). Group-aware prompts: when checkbox is set OR LLM detects multiple faces, instructs "preserve EVERY face — do not crop anyone out". `apply_overlay`/`apply_invitation_overlay` runs after AI returns; client gets the overlayed image.
- **`routes/memory_box.py`** — Registers Noto Sans Devanagari with ReportLab via `pdfmetrics.registerFont(TTFont("NotoDev", ...))` so the GPT-5.2 Marathi blessing on page 6 renders crisply. Cover PNG font switched from DejaVu (not installed) to Liberation Serif.
- **NEW `routes/video_overlay.py`** (registered in `server.py`):
  - `POST /api/marketing/videos/overlay` (multipart) — accepts video upload (≤60 MB, ≤90s), runs ffmpeg `filter_complex` with `drawbox` (dark gradient) + `drawtext` (Marathi-aware font picker: Noto Sans Devanagari for Devanagari, Liberation Serif for Latin) + logo overlay top-right.
  - `POST /list`, `POST /asset/{id}`, `GET /asset/{id}?token=…` (for inline `<video>` streaming).
- **System dependencies installed**: `ffmpeg`, `fonts-noto`, `fonts-noto-extra`, `fonts-indic`. Devanagari font path = `/usr/share/fonts/truetype/noto/NotoSansDevanagari-{Bold,Regular}.ttf`.

**Frontend**:
- **`pages/AdCreator.jsx`** — now 5 tabs (Marketing Ad · Party Invitation · Memory Box · **Video** · Gallery). Tab state URL-controlled via `?tab=`.
- **Marketing Ad form**: new "This is a group photo (multiple people)" checkbox appears below the photo preview when a photo is uploaded (`data-testid="ad-group-photo-check"`).
- **Invitation form**: same group-photo checkbox (`data-testid="invite-group-photo-check"`).
- **NEW `pages/VideoCreator.jsx`** — upload (≤60 MB), set headline + sub + byline, position (top/bottom), checkbox to burn logo. Live upload progress bar. Original + BRANDED preview side by side. Download MP4 + WhatsApp share + history strip of recent branded videos with inline `<video>` players.

**Verified end-to-end via curl** on preview:
- Marketing Ad: `ad_id=706ad9a0-…`, 1329.9 KB, Marathi caption *"एक चावा घेतला... आणि थांबताच आलं नाही!"* rendered crisply via Pillow ✓
- Pillow overlay smoke test: 52.5 KB marketing ad + 71 KB invitation, both with proper Devanagari ✓
- Video processing: 3s test clip with Marathi headline *"विसावा, चव घ्या"* → 69.5 KB branded MP4 (valid `ftypisom`) returned in <5s. List + asset GET both 200 OK ✓

**Lint**: All touched JSX + Python files clean (only cosmetic warnings).

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. After deploy:
- Group photos: tick the checkbox → all faces preserved
- Marathi script: rendered by us, not the AI → pixel-perfect Devanagari every time
- Video tab: upload a 30s clip → branded MP4 ready in under a minute


### [2026-06-03] Digital Memory Box Generator — 3rd tab in Center Manager Ad Creator (NEW MAJOR FEATURE)

**User ask** (verbatim summary): A new tab to generate a personalised 7-page PDF **Memory Box** for guests after their event / catering / tiffin / dine-in experience. Powered by GPT-5.2 for emotional story + blessing generation, auto-pulling the team roster from the `attendance` collection, and delivering via PDF download + WhatsApp + Email.

**User decisions** (gathered via ask_human):
- AI engine: **GPT-5.2** (Emergent Universal Key)
- Output: **7-page PDF Memory Book**
- Delivery: **PDF download + WhatsApp + Email**
- Team source: **Auto-pull from `attendance` collection** (status = "P" on event date)
- UI: **Single-page form with collapsible sections** (5 accordion groups)

**Backend** (`backend/routes/memory_box.py`, NEW, registered in `server.py`):
- `POST /api/memory-box/types` — returns 15 occasions + 10 emotions for the dropdowns
- `POST /api/memory-box/team-roster` — auto-pull team members marked **Present** at the center on the event date (queries `attendance` collection: `{center, date, status:"P"}`)
- `POST /api/memory-box/generate` — runs GPT-5.2 → builds 7-page PDF via ReportLab → generates 1080×1350 PNG cover (Pillow) → persists to `memory_boxes` collection + `static/memory_boxes/{CENTER}/{box_id}.{pdf,png}`
- `POST /api/memory-box/asset/{box_id}` — secure PDF download stream + increments `delivery.downloads`
- `POST /api/memory-box/list` — paginated history; FO/CM scope to own center, staff sees all
- `POST /api/memory-box/stats` — aggregated counts (created / WA shared / email shared / downloads)
- `POST /api/memory-box/whatsapp-preview/{box_id}` — returns pre-composed bilingual WA message + phone
- `POST /api/memory-box/mark-whatsapp-sent/{box_id}` — audit stamp
- `POST /api/memory-box/send-email/{box_id}` — sends PDF as SMTP attachment, audit-stamps `delivery.email`

**GPT-5.2 prompt** produces strict JSON `{story, gratitude, blessing, future_invitation}`:
- Story: 2-paragraph warm narrative weaving guest answers (organiser, special moment, family)
- Gratitude: occasion-specific thank-you (1 paragraph)
- Blessing: 2-3 line traditional Marathi blessing fitting the occasion
- Future invitation: 1-line warm welcome back (complimentary taak / chef special / priority booking — never discount-based)
- Deterministic templated fallback when LLM call fails — feature still works

**7-page PDF layout** (Times serif, maroon/gold/cream brand palette):
1. **Cover**: Logo + "Thank You For Making Us Part Of Your Celebration" + Guest name + Occasion + Date + Center
2. **Your Story With Us**: GPT-5.2 narrative + italic host quote
3. **Moments Captured**: 3×3 photo gallery (up to 9 of 10 uploaded photos)
4. **Meet The Team**: Single team photo + Name/Role table (auto-pulled or manually entered)
5. **With Gratitude**: GPT-5.2 occasion-specific thank-you
6. **Our Blessings For You**: GPT-5.2 Marathi blessing in italic
7. **Until We Meet Again**: GPT-5.2 future invitation + signature + Memory Box ID

**Frontend** (`pages/MemoryBoxCreator.jsx`, NEW + wired as 3rd tab in `pages/AdCreator.jsx`):
- **Stats strip**: 4 KPI cards (Created / WA Shared / Email Sent / Downloads)
- **Left card**: 5-section collapsible accordion (Guest+Center → Occasion+Emotion → Memory Questions → Photos → Team Roster). "Auto-pull from attendance" button + manual add. Photos up to 10 (6 MB max each). Optional team photo.
- **Right card**: live cover PNG preview, scrollable GPT narrative excerpt, and 3 delivery buttons (PDF Download · WhatsApp · Email).
- **History table** at bottom: re-download / re-share / re-email any past box.
- Permission: `_can_create()` accepts Super Admin / Admin / Accountant / Center Manager / Operations / Manager.

**Verified end-to-end via curl** on preview (PB-MGT, 2026-02-15, Birthday for Mr. & Mrs. Kulkarni, 60th of Aaji):
- `/types` → 15 occasions + 10 emotions ✓
- `/team-roster` → 200 OK with `team:[], count:0` (no attendance for that synthetic date) ✓
- `/generate` → 200 OK · **box_id** issued · 54.1 KB PDF (`%PDF-1.4` magic) · cover_png present · **GPT-5.2 narrative real**: *"15 February 2026 will stay tenderly etched in our hearts at Purnabramha…"* + blessing in Marathi: *"Aaji, दीर्घायुषी भव—आरोग्य, सुख आणि समाधान सदैव लाभो…"* ✓
- `/asset/{box_id}` → 200 OK · 55,396 byte valid PDF stream ✓
- `/list` → 200 OK · 1 item (the just-created one) ✓
- `/whatsapp-preview/{box_id}` → 200 OK · pre-composed bilingual message + phone ✓

**Frontend lint**: clean. **Backend lint**: 3 cosmetic warnings (multi-import on one line, one f-string without placeholders, one semicolon) — not blocking.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. After deploy, every Center Manager sees a new "Memory Box" tab inside Ad Creator and can generate emotionally-personalised 7-page memory books for guests in under 30 seconds.

### [2026-06-03] Memory Box one-click link from Catering Orders & Event Bookings (CROSS-MODULE INTEGRATION)

**User ask** (verbatim): "Would you like a small 'Memory Box link' that gets auto-suggested on every completed Catering Order / Event Booking — so the center manager is one click away from sending a memory box right after settling the bill?"

**Implementation**:
- `pages/AdCreator.jsx`: tab state is now URL-controlled via `?tab=` query param (preserves deep-linking). Initial tab respects `?tab=memory-box`.
- `pages/MemoryBoxCreator.jsx`: on mount, reads `localStorage['mbox_prefill']` (set by other modules) and prefills center/guest_name/mobile/email/event_date/order_number/occasion/celebration_for, then clears the key. Toast acknowledges the source ("Prefilled from Catering Order — answer the memory questions to make it personal").
- `pages/CateringOrders.jsx`: new BookHeart action button on every row (`data-testid="catering-memory-box-{id}"`) → stashes prefill (occasion = "Catering Event", celebration_for = booking occasion) → navigates to `/ad-creator?tab=memory-box`.
- `pages/EventBookings.jsx`: same button (`data-testid="event-memory-box-{id}"`) with a smart `event_type → occasion` mapping (Birthday/Anniversary/Baby Shower/Dohal Jevan/Upanayan/Naming Ceremony/Retirement Function/Corporate Event/Family Gathering).

**Net result**: One click on the rose BookHeart icon → Center Manager lands on the Memory Box tab with guest name, mobile, email, event date, center, occasion, and source order number all pre-filled. They only need to answer the 4 memory questions, upload photos, click Generate → PDF + WhatsApp + Email goes out in <60s.

**Lint clean** on all 4 touched files.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`.

### [2026-06-02] Center Accounts — Expense Adjustment & Profitability Correction (NEW MAJOR FEATURE)

**User ask** (verbatim, summarized): When the franchise pays a future-month expense (e.g. June rent paid in May), it should be recorded normally for audit, but **NOT** distort May profitability or Revenue Share. Need a transparent adjustment mechanism that never modifies the underlying expense row, with a per-adjustment audit trail and visibility across every report.

**User decisions**:
- Writers: Admin + Super Admin + **Accountant** (1b)
- Each adjustment is **tied to a specific expense row** (2b)
- Adjustments only flow through **Profitability + Revenue Share** — GST / aggregator math untouched (3a)

**Backend**:
- New collection `expense_adjustments` with full audit fields (adjustment_id, expense_id FK, center, month, expense_head + date snapshot, original_expense_amount, adjustment_amount, type, reason, created_by/at, updated_by/at)
- New routes `/api/center-accounts/adjustments/{types,list,create,update,delete,report}` in `routes/expense_adjustments.py`
- Single source of truth `utils/adjustments.py::get_total_adjustments(db, center, month)` — wired into both `routes/center_accounts.py::summary` and `routes/owner_reports.py::monthly-report`
- **Profitability** and **Revenue Share** now use `adjusted_expenses = total_expenses − total_adjustments`; raw `total_expenses` retained for transparency in every response
- Validations: amount > 0, amount ≤ original expense, cumulative siblings ≤ original, type in 6 allowed values, expense_id must exist
- Permissions: 403 for Franchise Owner / Center Manager on writes; non-admin can only view own center

**Frontend**:
- New "**Adjustments**" tab in Center Accounts → 5 summary cards (Total Expenses, Less Adjustments, Adjusted Expenses, Net Revenue, Profitability) + per-month list with add/edit/delete dialog. Expense row picker shows all month's expenses with date + head + amount + description.
- New "**Expense Adjustments Report**" page (sidebar under Accounts) → center / from-month / to-month filters, totals cards, Center×Month summary, detail table, **Export CSV**.
- Permissions: write controls hidden for Franchise Owner / Center Manager.

**6 Adjustment Types**: Next Month Rent Paid in Advance · Advance Utility Payment · Security Deposit · Future Expense Allocation · Manual Adjustment · Other.

**Zero-adjustment parity**: If no adjustment exists for the month, `total_adjustments=0` and `adjusted_expenses == total_expenses` exactly — pre-release behavior preserved.

**Testing**: `testing_agent_v3_fork` iteration_85 → **18/18 backend pytest PASS** + frontend live verified. No critical/minor issues. Zero regressions, all permission guards correct, cumulative cap excludes-self on update, original expense rows never modified across CRUD lifecycle.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`.

### [2026-05-29] Customer Party Invitation Creator (NEW — second tab in Ad Creator)

**User ask** (verbatim): "under same head create one tab, and let center manager create this — as customer give request for creating image for their function at Purnabramha like wedding, gettogether, bday party invitation, it should ask name of the host, reason for the party, date time, and center address and menu - optional and if they give any of there party host photo (optional). Create image with Purnabramha Logo and center name and host name."

**Implementation**:
- Saved brand logo (user-uploaded JPG) to `/app/backend/static/purnabramha_logo.jpg` as the reference asset.
- New backend endpoint `POST /api/marketing/ads/invitation/generate` — uses the same Nano Banana (gemini-3.1-flash-image-preview) pipeline as Marketing Ad, but with an **invitation-tuned prompt template** and **logo passed as a reference image** (host photo, if provided, passed first so face is preserved).
- New form fields: host_name *, occasion (Wedding / Engagement / Anniversary / Birthday / Baby Shower / Get-together / Corporate / Festival / Other), event_date *, event_time *, center *, center_address (auto-filled from `centers` collection, editable), menu_highlights (optional), custom_message (optional), language, output_format, host photo (optional).
- Output stored to `ad_creations` collection with `kind="invitation"`. History endpoint accepts a `kind` filter.
- Permission: same `_is_center_manager_or_above` guard (which now also honors `roles.operations`).

**Frontend** (`pages/InvitationCreator.jsx` + updated `pages/AdCreator.jsx`):
- New "**Party Invitation**" tab inside the existing Center Manager Ad Creator (sidebar untouched).
- Left card: full form with auto-address fill, optional host photo (circular preview).
- Right card: live preview + Download PNG + Share on WhatsApp.

**Verified live** with real Nano Banana generation: Wedding for "Shri Mahesh & Sau. Pooja Kulkarni" @ PB-MGT, 2026-06-15, 7:30 PM, menu = Puran Poli, Misal Pav, Modak → 657 KB JPEG in 20s with all 6 required elements visible (logo, host name, occasion in Marathi+English, date, time, venue, menu). Readability rated 9/10 via image analysis.

⚠️ **Click Deploy** to push to `intra.purnabramha.com`. Every Center Manager will see a "Party Invitation" tab inside Ad Creator and can generate branded customer invitations in <30s.

### [2026-05-23] One-click "Send Quote to Customer" for Catering + Event bookings (NEW)

**User ask** (verbatim): "Would you like a one-click Send Quote to Customer action that auto-generates the PDF — closes the loop from enquiry → quote → confirmed order?"

**Backend** (`routes/booking_extensions.py`):
- New endpoint `POST /api/bookings/ext/{kind}/send-quote/{rid}` (kind = catering / event / tiffin).
- Auto-generates the same canonical PDF via `_build_single_pdf(kind, doc)` and emails it via the SMTP credentials already configured for the OTP / Email-Pack flow (no new secrets needed).
- Recipient resolution: `to_email` override (form prompt on UI) → falls back to `doc.email`. 400 if neither is present.
- Stamps `quote_sent_at` + `quote_sent_to` + `quote_sent_by` on the booking doc + writes an audit row to `booking_quote_sends`.
- 503 with actionable message if SMTP not configured; 500 with logged exception on transport failure.

**Frontend** (`pages/CateringOrders.jsx` + `pages/EventBookings.jsx`):
- New action button in every row (Mail icon, data-testid="catering-send-quote-{id}" / "event-send-quote-{id}").
- Once sent, the icon auto-flips to an emerald CheckCircle so the manager sees at-a-glance which orders have already been quoted.
- If `doc.email` is blank, the manager is prompted for an email at click-time.
- Toast: "Quote sent to <email> (<size> KB)".

**Verified end-to-end on PB-MGT preview**:
- Catering quote `CATERING-20260523-65C2B9` → emailed to `test@example.com` (2.6 KB PDF attachment) → 200 OK → doc now has `quote_sent_at: 2026-05-23T12:50:25.958537+00:00` + `quote_sent_to: test@example.com` + `quote_sent_by: Jayanti Kathale`.
- Missing-email case correctly returns 400 with actionable message.
- All lint clean (no new warnings).

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy, Catering Orders and Event Bookings rows show a new Mail icon — one click emails the PDF directly to the customer using the existing SMTP credentials.

### [2026-05-23] Booking Intelligence Expansion — Tiffin / Catering / Event + Menu Master (NEW MAJOR FEATURE)

**User ask**: Expand Booking Intelligence beyond table bookings. Add Tiffin (subscription), Catering (B2B orders), and Event/Celebration bookings with full CRUD, searchable lists, per-booking PDFs, and a hybrid menu (master list + custom typed items). Also add "Table Allotted" to existing table bookings + a "Download Today PDF" for table bookings. KEEP existing table booking logic 100% intact.

**User decisions**:
- 3 new modules sit as **separate sidebar items under Operations** (not sub-tabs).
- Tiffin pricing = **free-form** (manager types subtotal / gst / total).
- Catering & Event GST = **canonical inclusive carve** (India 5% / Perth 10%) — single source of truth.

**Backend** (`backend/routes/booking_extensions.py`, NEW + `server.py:2155`):
- New router `/api/bookings/ext/*`.
- Collections: `tiffin_bookings`, `catering_orders`, `event_bookings`, `menu_master`.
- Endpoints (each kind): `/create`, `/list`, `/update/{id}`, `/delete/{id}`, `/pdf/{id}`.
- Menu Master: `/menu/list`, `/menu/upsert`, `/menu/delete`.
- Today PDF: `/today-table-pdf` for existing `bookings` collection.
- Consolidated rollup: `/dashboard` returns counts + amounts across all 4 booking types.
- Permissions: Admin / Super Admin / Operations / Mgt can write; Accounts / Franchise Owner are read-only (verified by tests → 403 for FO writes).
- Existing `booking_intelligence.py` `/create` now also persists `table_allotted` (was previously update-only).

**Frontend** (4 new pages + 1 helper):
- `pages/TiffinBookings.jsx` — date-range/center/status filters, free-form pricing, days-of-week selector, hybrid item picker, per-booking PDF.
- `pages/CateringOrders.jsx` — full quotation builder with hybrid menu by category (Starters / Main / Roti / Rice / Dal / Veg / Dessert / Salad), beverages, add-ons, transport, advance/balance, **auto canonical GST recompute** (India 5% / Perth 10% inclusive carve).
- `pages/EventBookings.jsx` — event-type selector (Birthday / Anniversary / Wedding / Baby Shower / Corporate / Kitty / etc.), package + dal selector, hybrid menu by category, **auto canonical GST recompute**.
- `pages/MenuMaster.jsx` — Admin/SA/Operations CRUD for `menu_master`. 13 categories.
- `components/booking/MenuPicker.jsx` — shared hybrid picker (pick from category master OR type custom).
- `pages/BookingIntelligence.jsx` (existing) — added "Table Allotted" column + input (data-testid="table-allotted-input") and "Download Today PDF" button (data-testid="download-today-pdf-btn"). Existing functionality untouched.
- Sidebar `pages/Dashboard.jsx` + `lib/menuDefaults.js` — 4 new entries under Operations: Tiffin Bookings, Catering Orders, Event Bookings, Menu Master.

**Verified end-to-end**:
- Backend tests: 26/26 PASS via `testing_agent_v3_fork` iteration_84 (`/app/backend/tests/test_iteration84_booking_extensions.py`).
- Curl smoke: Menu upsert ✓, Tiffin/Catering/Event create+list+PDF (all valid `%PDF-1.4`) ✓, Today PDF ✓, Dashboard rollup ✓.
- Frontend: All 4 pages render with correct data-testids verified via Playwright (`tiffin-bookings-page`, `catering-orders-page`, `event-bookings-page`, `menu-master-page`, `download-today-pdf-btn`).
- `table_allotted` persistence on `/api/bookings/create` confirmed via curl (T7 round-trip).
- All lint clean (`yarn lint` / `ruff` — no errors).

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy, the 4 new Operations entries appear; existing table bookings continue to work identically with added Table Allotted field + Today PDF button.

### [2026-05-15] Financial Insights tab under Center Accounts (NEW)

**User ask** (verbatim): Build a new tab called "Financial Insights" inside Center Accounts with month / month-range / FY / custom-date filters, single + multi-center, financial summary cards with % and trends, expense + sales segregation, ratio analysis with color indicators, comparative analysis, trend graphs, drill-down, Excel/PDF/CSV downloads, and an AI executive summary.

**Backend** (`backend/routes/financial_insights.py`, NEW):
- `POST /api/financial-insights/summary` — full structured analytics for any period+centers combo
- `POST /api/financial-insights/export` — Excel + CSV download
- `POST /api/financial-insights/drill-down` — category-level breakdown (expense_category / sales_channel)
- Reuses canonical helpers (`utils/gst.py`, `utils/commissions.py`, `routes/center_health.py::_month_metrics`) — byte-identical numbers to MIS / Center Accounts / PIB / Center Health Dashboard.
- AI Executive Summary via GPT-5.2 (Emergent Universal Key) — 1-paragraph plain-prose narrative, sanitized of markdown.
- Permissions enforced: staff sees all centers, franchise owner sees only own/franchise-mapped centers.

**Frontend** (`frontend/src/components/FinancialInsightsTab.jsx`, NEW + embedded into `CenterAccounts.jsx`):
- New "Financial Insights" tab (Activity icon, rose color) added between Reports and Ledgers tabs.
- Filter bar: Period Type (Single Month / Month Range / Financial Year / Custom Dates), per-type controls, multi-select centers as pill toggles, Apply / Excel / CSV buttons.
- AI Executive Summary card (amber gradient) at top.
- 6 KPI cards: Sales / Expenses / Commission / GST / Gross Profit / Net P/L — each with % of sales sub-line and trend % vs previous comparable period.
- Sales Channels card (Dine-in / Swiggy / Zomato / DoorDash with shares).
- Financial Ratios card with Good / Warning / Critical badges (food cost, salary, rent, utility, commission burden, aggregator share).
- 12-Month Profit Trend bar strip (green/red).
- Expense Segregation table (top 12 categories, amount + % of sales).
- Month-by-month breakdown table (when range/FY/custom selected).
- Per-center comparison table (when multiple centers selected).

**Verified end-to-end on preview** (PB-HSR Feb 2026):
- Sales ₹9,06,132 · Net P/L ₹7,60,190 · 83.9% margin
- AI summary auto-generated: identified 12% sales drop + 23.2% profit gain + sub-ideal salary/rent/food ratios
- Excel export: 9,461 bytes, valid XLSX with 5 sheets (Summary / Ratios / 12-Month Trend / By Month / Expense Categories)
- CSV export: 820 bytes, plain text
- Frontend production build (`yarn build`) succeeds in 27s.

⚠️ Click **Deploy** to push to `intra.purnabramha.com`.

### [2026-05-15] Marketing Ad Creator — guest testimonial mode + optional photo

**User ask**: Allow 3 inputs (Guest Name, Posted by, Subject) and optional guest photo. If no photo → text-only product ad. Stop forcing the "आठवड्याच्या शेवटी एक आठवण" tagline.

**Backend** (`routes/marketing_ads.py`):
- `AdGenerateRequest` extended with `guest_name`, `subject_text`.
- Photo is now OPTIONAL — removed 400 error.
- Image prompt branches: with-photo (guest face preserved) vs no-photo (product-only, NO human figure).
- Caption + image prompts explicitly forbid "आठवड्याच्या शेवटी / एक आठवण / घरची आठवण / weekend memory" cliches.
- New examples in caption prompt show testimonial-style + product-only outputs.
- Persisted record now includes `guest_name`, `subject_text`, `has_photo` flags.

**Frontend** (`pages/AdCreator.jsx`):
- Added Guest Name + Subject/Message free-text inputs.
- "Full Name" relabeled to "Posted by (center manager / host)".
- Photo upload now labeled "Guest Photo (optional — leave blank for product-only ad)" with "Remove photo" button.
- Generate button auto-switches label: "Generate Product Ad" (no photo) vs "Generate Guest Testimonial Ad" (with photo).

**Verified live**:
- Guest mode caption (Balgopal / Thali): "बालगोपाळजींनी पहिल्यांदाच चाखली पूर्णब्रह्माची थाळी — आणि दिलं मनापासून प्रेम!"
- Product mode (no guest / Misal Pav): "विसावा, चव घ्या, आनंद साजरा करा — मिसळ पावासोबत!"
- Neither contains the forced "athawadyachya shewati" template.
- User-validated production screenshot shows "बालगोपाळ - रिया यांनी प्रेमाने ताट रिकामी केली — पुरणपोळीची गोडी, मनाला भिडली!" — fresh, dignified, and guest-specific.

### [2026-05-15] Center Profitability Health Dashboard (NEW MAJOR FEATURE)

**User ask** (verbatim): "Create one powerful feature called Center Profitability Health Dashboard. It should not just show numbers — it should identify why profitability is dropping, where money leakage is happening, which operational mistakes are affecting business, what actions are immediately needed, what trend is dangerous long term."

**Build approach**:
- Sidebar: under **Accounts → Center Health Dashboard** (accessible to Accounts / Admin / SA / Franchise Owner)
- AI engine: **GPT-5.2** via Emergent Universal Key for narrative paragraphs ONLY (never for numbers)
- Coverage: India + International (Australia/Perth) with currency/GST awareness

**Backend** (`backend/routes/center_health.py`, NEW):
- `POST /api/health-dashboard/centers` — list centers the requester can view (FO sees only own, staff sees all)
- `POST /api/health-dashboard/score` — full structured health payload
- `POST /api/health-dashboard/pdf` — downloadable PDF (signature block included, share-ready for franchisees)
- All financial numbers reuse canonical helpers (`utils/gst.py`, `utils/commissions.py`, `routes/center_accounts.py::calculate_working_capital_standing`) — byte-identical to MIS / Center Accounts / PIB.

**12 sections implemented**:
1. **Overall Health Score** (0-100, 5 tiers: Excellent / Stable / Warning / Critical / Dangerous) — rule-based deduction per leakage severity + margin + WC bias.
2. **AI Profitability Analysis** — detects sales drop, aggregator dependency, commission burden, salary/rent/food-cost ratio breaches, utility spike, sales drop, negative P/L.
3. **What Needs Correction** — deterministic action list mapped from active leakages (8 max, deduped).
4. **Monthly Leakage Analysis** — 9 leakage categories with severity (critical/high/medium) + estimated monthly impact (₹).
5. **Profitability Formula Engine** — Sales − Comm − GST = Net Revenue ; − Expenses = Net P/L (canonical).
6. **Working Capital Health** — current WC, base WC, % of base, status with color-coded progress bar.
7. **Smart Comparisons** — vs previous month, YoY same-month, channel mix (Dine-in/Swiggy/Zomato/DoorDash), top-5 expense buckets.
8. **Visual Dashboard** — 12-month P/L trend bars (green/red), tier-coded score meter, hexcode-controlled palette.
9. **AI Founder's Reality Check** — GPT-5.2 generated 80-120 word executive paragraph (no markdown, plain prose, sanitized).
10. **Predictive 3-Month Warning** — GPT-5.2 generated 60-90 word forecast paragraph based on current pattern.
11. **Data Sources** — `daily_sales`, `expenses`, `monthly_commissions`, canonical WC chain, centers (for country/currency).
12. **PDF download** — 2-page reportlab PDF with Score, Founder Summary, Formula, WC card, Ratios table, Leakage table, Action list, Predictive warning, 12-month trend table, signature block.

**Frontend** (`frontend/src/pages/CenterHealth.jsx`, NEW):
- Header: Center selector + Month selector (last 24 months) + Refresh + Download PDF button.
- Hero: Health Score meter (tier-coloured) + Founder's Reality Check card (gradient amber).
- KPI strip (6 cards): Sales / Commissions / GST / Net Revenue / Expenses / Net P/L — with trend % vs previous month.
- Profitability Formula card + WC Health card.
- Operational Ratios table (Food Cost / Salary / Rent / Utility / Commission / Aggregator share) with OK / High / Critical badges.
- 12-Month P/L Trend bar strip (green/red).
- Leakage Analysis list with severity badges + estimated impact.
- "What Needs Correction" numbered action list.
- "Predictive 3-Month Warning" gradient card.
- Smart Comparisons section (vs prev / channel mix / expense buckets).
- Every interactive element has `data-testid`.

**Sidebar wiring**:
- Added "Center Health Dashboard" under Accounts in `Dashboard.jsx` + `menuDefaults.js` (visible to Accounts AND Franchise).
- New route `/center-health`.
- Imported `Activity` icon from lucide-react.

**Verified end-to-end on preview** (PB-HSR Feb 2026):
- Score: 88/100 (Excellent)
- Sales ₹9,06,132 · Net P/L ₹7,60,190 · Net margin 83.9%
- AI narrative renders cleanly without markdown leakage
- PDF: 145KB valid PDF with `%PDF-1.4` magic bytes
- Frontend production build (`yarn build`) succeeds in 24s — no eslint errors.

**Earlier this session — Marketing Ad Creator move**:
- Moved "Center Manager Ad Creator" from sidebar "Marketing / Creative Studio" → **Operations** category (per user request).
- Fixed deployment-blocking build error: `AdCreator.jsx` had `import { useAuth } from '../components/AuthContext'` (file didn't exist). Replaced with `import { useAuth } from "@/App"` matching codebase convention. Production deploy now builds.

⚠️ Click **Deploy** to push to `intra.purnabramha.com`. After deploy, the Center Health Dashboard appears in the Accounts category for all eligible roles.

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

### [2026-05-13] Reports Restructure + SMTP Direct Send
- **Center Accounts → Reports tab cleanup**: replaced the 3 large per-report cards (PIB / GST / Commission) with:
  - A **hero "Monthly Franchise Email Pack" CTA** as the primary monthly-delivery flow
  - A **compact "Quick Single-Report Downloads" row** of small ghost buttons (PIB / GST / Commission, Preview + PDF) for audit use only
  - Clarifying line: "For audit use. For monthly delivery, prefer the Email Pack above."
- **Email Pack dialog — Send via SMTP button**: opens an inline form with To + CC inputs; clicking Send Now POSTs to new `/api/center-accounts/email-pack/send` which uses the existing OTP-mailer SMTP credentials to deliver the same ZIP attachment. Falls back to a clear 503 error when SMTP isn't configured (UI then prompts manual Download ZIP).
- **Permission gate on send**: Only Super Admin / Admin / Accounts roles can trigger `email-pack/send` (franchise owners can NEVER send, only view + download).
- **Audit log**: every send writes to `email_pack_sends` (`{send_id, center, month, to_email, cc, subject, size_bytes, sent_by, sent_at}`).
- **Owner Reports (`/owner-reports`) — kept separate** with collapsible sections from earlier iteration (no duplication with Center Accounts).
- **Ledgers (`/ledgers`)** — confirmed gated to accounts-only (`_has_ledger_access`) and not present in franchise-owner sidebars.
- **Tests:** 14/14 pytest pass. Parity audit ALL SURFACES MATCH for PB-HSR + PB-PERTH. End-to-end SMTP send verified in preview (137.5 KB ZIP delivered to test address).

## Pending / Backlog
- (P1) WhatsApp/Email notification hooks
- (P1) Code freeze preparation audit
- (P1) Live recompute of P/L & WC cascade in WC Breakdown table on Sales/Comm/Expense edit
- (P2) Inline audit log expansion for Topups in WC table
- (P2) Add "Backfill role_key" admin script/button
- (P2) Auto-categorization/heuristics for Bank Recon
- (P2) Image Upload for Recipes, Franchise Deal Simulator, Menu card PDF, PDF refactoring, 7-year retention deletion prompt
- (P2) MFPL royalty *payment* tracking (collection + paid-down accrual) once MFPL starts taking the royalty
