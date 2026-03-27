# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
Internal management system for Purnabramha restaurant franchise. Full operational system covering financial (MIS, sales, expenses), attendance, payroll, HR letters, recipes, guest management, employee transfers, international (Perth) attendance, and now **master-data-driven architecture** with role-based access control.

## Architecture
```
/app/backend/
├── server.py              # Auth, employees (transfer-aware), advances, startup hooks
├── routes/
│   ├── masters.py         # NEW: 16 master type CRUD, seed-from-existing migration
│   ├── permissions.py     # NEW: Permission engine, 7 roles, check_permission
│   ├── attendance.py      # Transfer-aware attendance (daily + monthly)
│   ├── payroll.py         # Transfer-aware salary preview + generation
│   ├── transfers.py       # Employee transfer request/accept/reject
│   ├── international_attendance.py  # Perth attendance + PDF export
│   ├── mis_dashboard.py   # MIS charts + working capital + center filtering
│   ├── hr_letters.py      # EXTRACTED - AI letter generation
│   ├── centers_managers.py # EXTRACTED - CRUD for centers & managers
│   ├── sales_expenses.py  # Updated: expense-types/payment-modes pull from masters
│   ├── expense_attachments.py
│   ├── net_revenue.py
│   ├── booking_intelligence.py
│   └── recipes.py
/app/frontend/src/pages/
├── MasterDataManagement.jsx  # NEW: Admin UI for all 16 master tables
├── FranchiseOwnerDashboard.jsx # NEW: View-only dashboard for franchise owners
├── RoleManagement.jsx      # ENHANCED: DB-driven system roles + legacy module roles
├── Attendance.jsx         # Transfer badges (IN/OUT) in daily + monthly views
├── Salary.jsx             # Shows transferTag + workingCenter
├── MISDashboard.jsx       # Center filtering fixed, Working Capital, Export
├── InternationalAttendance.jsx  # PDF export added
└── ... (25+ pages)
```

## Master Data Architecture (Phase 1 - COMPLETE)

### 16 Master Tables
| Master | Collection | Seeded Count |
|--------|-----------|-------------|
| Expense Category | master_expense_categories | 35 |
| Payment Mode | master_payment_modes | 8 |
| Employee Category | master_employee_categories | 21 |
| Tax Configuration | master_tax | 3 |
| Menu Category | master_menu_categories | 7 |
| Menu Item | master_menu_items | 0 (to be populated) |
| Table | master_tables | 0 (to be populated) |
| Order Type | master_order_types | 4 |
| Vendor | master_vendors | 0 (to be populated) |
| Cancellation Reason | master_cancellation_reasons | 6 |
| Franchise | master_franchises | 0 |
| License/Document Type | master_licenses | 6 |
| Sales Channel | master_sales_channels | 6 |
| Discount Type | master_discount_types | 5 |

Each master supports: name, is_active, created_at, created_by, updated_at, updated_by + type-specific fields.

### Permission Engine (Phase 1 - COMPLETE)
7 Roles with full permission matrices:
1. **Super Admin** — all_centers, all modules
2. **Admin** — all_centers, all except role management
3. **Center Manager** — own_center, operational modules
4. **Super Manager** — assigned_centers, extended operational + reporting
5. **Accountant** — all_centers, finance + reports + payroll
6. **Franchise Owner** — own_franchise, view-only sales/expenses/reports/franchise
7. **Staff** — own_center, limited (dashboard + attendance + billing)

22 permission modules with granular actions (view, create, edit, delete, lock, unlock, etc.)

### Franchise Owner Dashboard (Phase 2 - COMPLETE)
- View-only KPI cards (Sales, Expenses, Profit, Margin)
- Sales trend chart + day-wise table
- Expense breakdown pie chart
- Franchise profile info
- Excel export

### Master-Driven Dropdowns (Phase 2 - COMPLETE)
- Expense types: `/api/sales/expense-types` returns `source: master` from `master_expense_categories`
- Payment modes: `/api/sales/payment-modes` returns `source: master` from `master_payment_modes`
- Fallback to legacy hardcoded values if master tables empty (safe migration)

## Testing Credentials
- Super Admin: PB-MGT, Mobile 9741399190, OTP 123456
- Perth Manager: PB-PERTH, Mobile 0401832922, OTP 123456
- India Manager: PB-HSR, Mobile 9999999999, OTP 123456

## Test Reports
- iteration_25.json: Master Data + Permission Engine + Franchise Dashboard (100%, 16/16)
- iteration_24.json: Transfer-aware attendance/payroll, PDF export, refactoring (100%, 14/14)
- iteration_23.json: MIS Dashboard v2 + Expense enhancements (100%, 18/18)

## Backlog (Phases 3-4)

### P0 — Phase 3: Billing/POS System
- Order creation (dine-in/takeaway/delivery)
- Table mapping, KOT generation, kitchen routing
- Cancellation with audit trail + role-based approval
- Tax, discounts, split payments
- Invoice generation
- Internal feed to sales/finance/dashboard

### P1 — Phase 4: Full Integration
- Replace ALL remaining hardcoded values across 30+ files
- Complete role-based visibility on every button/screen/action
- Live data migration verification
- Franchise document management (agreements, licenses)
- Approval hierarchy config

### P2
- WhatsApp/Email notification hooks
- International center support for transfers
- 7-year retention deletion prompt

## Project Health
- Broken: None
- Mocked: WhatsApp Integration
