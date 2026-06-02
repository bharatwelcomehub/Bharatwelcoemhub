// =====================================================================
// MENU DEFAULTS — labels-only mirror of the sidebar structure used by
// Dashboard.jsx. Kept in sync manually so the Menu Customization page
// (Super Admin) can render the editable structure without pulling in
// the icon imports from Dashboard.
//
// NOTE: When you add/remove/rename items in Dashboard.jsx#menuCategories,
// update this file too.
// =====================================================================

export const MENU_DEFAULTS = [
  {
    id: "attendance",
    label: "Attendance",
    items: [
      { path: "/", label: "India Centers" },
      { path: "/international-attendance", label: "International" },
      { path: "/international-roster", label: "Intl Roster" },
      { path: "/employee-transfers", label: "Transfers" },
      { path: "/attendance-dashboard", label: "Attendance Dashboard" },
      { path: "/duty-roster", label: "Daily Duty Roster" },
    ],
  },
  {
    id: "sales",
    label: "Sales & Cash",
    items: [
      { path: "/sales", label: "Sales Dashboard" },
      { path: "/expense-heads", label: "Expense Heads" },
      { path: "/daily-text", label: "Sales Text Generator" },
    ],
  },
  {
    id: "accounts",
    label: "Accounts",
    items: [
      { path: "/center-accounts", label: "Center Accounts" },
      { path: "/center-health", label: "Center Health Dashboard" },
      { path: "/expense-adjustments-report", label: "Expense Adjustments Report" },
      { path: "/gst-paid-report", label: "GST Paid Report" },
      { path: "/gst-reconciliation", label: "GST Reconciliation" },
      { path: "/bank-reconciliation", label: "Bank Reconciliation" },
      { path: "/loan-entries", label: "Loan Entries" },
      { path: "/historical-import", label: "Historical Import" },
      { path: "/mis-dashboard", label: "MIS Dashboard" },
    ],
  },
  {
    id: "hr",
    label: "HR Management",
    items: [
      { path: "/employees", label: "Employees" },
      { path: "/salary", label: "Salary" },
      { path: "/payslips", label: "Payslips" },
      { path: "/hr-letters", label: "HR Letters" },
    ],
  },
  {
    id: "marketing",
    label: "Marketing / Creative Studio",
    items: [
      { path: "/social-media", label: "Social Media Planner" },
    ],
  },
  {
    id: "mgt",
    label: "Management",
    items: [
      { path: "/centers", label: "Centers" },
      { path: "/managers", label: "Managers" },
      { path: "/role-management", label: "Role Management" },
      { path: "/master-data", label: "Master Data" },
      { path: "/menu-config", label: "Menu Customization" },
      { path: "/social-media", label: "Social Media Planner" },
    ],
  },
  {
    id: "franchise",
    label: "Franchise",
    items: [
      { path: "/franchises", label: "Franchise Management" },
      { path: "/owner-reports", label: "Owner Reports" },
      { path: "/franchise-exit", label: "Exit & Closure" },
      { path: "/franchise-dashboard", label: "Owner Dashboard" },
      { path: "/bill-download", label: "Bill Download" },
      { path: "/documents", label: "Documents" },
    ],
  },
  {
    id: "operations",
    label: "Operations",
    items: [
      { path: "/booking-intelligence", label: "Booking Intelligence" },
      { path: "/menu-master", label: "Menu Master" },
      { path: "/bhojan-guru", label: "Bhojan Guru" },
      { path: "/guest-response", label: "Guest Response" },
      { path: "/recipe-admin", label: "Recipe Admin" },
      { path: "/ad-creator", label: "Center Manager Ad Creator" },
    ],
  },
  {
    id: "billing",
    label: "Billing / POS",
    items: [
      { path: "/pos-billing", label: "POS / Billing" },
      { path: "/billing-config", label: "Configuration" },
      { path: "/menu-management", label: "Menu Items" },
    ],
  },
  {
    id: "food_safety",
    label: "Food Safety",
    items: [
      { path: "/food-safety", label: "Food Safety" },
    ],
  },
  {
    id: "help",
    label: "Help & Resources",
    items: [
      { path: "/user-manuals", label: "User Manuals" },
    ],
  },
];
