import { useState, useEffect } from "react";
import { Routes, Route, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/App";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { fetchCentersFromDB, isAdminUser } from "@/lib/api";
import { 
  Calendar, 
  CalendarDays,
  Users, 
  Wallet, 
  FileSpreadsheet, 
  FileText, 
  ChefHat, 
  LogOut, 
  Menu, 
  X,
  Building2,
  Clock,
  MessageCircle,
  Settings,
  Briefcase,
  IndianRupee,
  Receipt,
  Tags,
  ChevronDown,
  ChevronRight,
  UserCog,
  Shield,
  Store,
  BarChart3,
  Globe,
  ArrowRightLeft,
  Database,
  UtensilsCrossed,
  LayoutGrid,
  Ban,
  Cog,
  FileCheck2,
  BookOpen,
  MessageSquare,
  Download,
  Share2,
  Upload,
} from "lucide-react";

// Import pages
import Attendance from "@/pages/Attendance";
import Employees from "@/pages/Employees";
import Salary from "@/pages/Salary";
import BhojanGuru from "@/pages/BhojanGuru";
import GuestResponse from "@/pages/GuestResponse";
import RecipeAdmin from "@/pages/RecipeAdmin";
import HRLetters from "@/pages/HRLetters";
import CentersManagement from "@/pages/CentersManagement";
import ManagersManagement from "@/pages/ManagersManagement";
import SalesExpenses from "@/pages/SalesExpenses";
import ExpenseHeads from "@/pages/ExpenseHeads";
import RoleManagement from "@/pages/RoleManagement";
import FranchiseManagement from "@/pages/FranchiseManagement";
import FranchiseExit from "@/pages/FranchiseExit";
import MISDashboard from "@/pages/MISDashboard";
import CenterAccounts from "@/pages/CenterAccounts";
import HistoricalImport from "@/pages/HistoricalImport";
import OwnerReports from "@/pages/OwnerReports";
import LoanEntries from "@/pages/LoanEntries";
import BookingIntelligence from "@/pages/BookingIntelligence";
import AttendanceDashboard from "@/pages/AttendanceDashboard";
import InternationalAttendance from "@/pages/InternationalAttendance";
import EmployeeTransfers from "@/pages/EmployeeTransfers";
import MasterDataManagement from "@/pages/MasterDataManagement";
import FranchiseOwnerDashboard from "@/pages/FranchiseOwnerDashboard";
import MenuManagement from "@/pages/MenuManagement";
import POSBilling from "@/pages/POSBilling";
import BillingConfiguration from "@/pages/BillingConfiguration";
import DocumentManagement from "@/pages/DocumentManagement";
import UserManuals from "@/pages/UserManuals";
import FoodSafety from "@/pages/FoodSafety";
import DailyTextGenerator from "@/pages/DailyTextGenerator";
import SocialMediaPlanner from "@/pages/SocialMediaPlanner";
import BillDownload from "@/pages/BillDownload";
import InternationalRoster from "@/pages/InternationalRoster";

// Menu categories structure
const menuCategories = [
  {
    id: "attendance",
    label: "Attendance",
    icon: Calendar,
    roleKey: "attendance",
    items: [
      { path: "/", icon: Calendar, label: "India Centers", roleKey: "attendance" },
      { path: "/international-attendance", icon: Globe, label: "International", roleKey: "attendance", forInternational: true },
      { path: "/international-roster", icon: CalendarDays, label: "Intl Roster", roleKey: "attendance", forInternational: true },
      { path: "/employee-transfers", icon: ArrowRightLeft, label: "Transfers", roleKey: "attendance" },
      { path: "/attendance-dashboard", icon: BarChart3, label: "Attendance Dashboard", forAdmin: true },
    ]
  },
  {
    id: "sales",
    label: "Sales & Cash",
    icon: IndianRupee,
    roleKey: "sales_cash",
    items: [
      { path: "/sales", icon: IndianRupee, label: "Sales Dashboard", roleKey: "sales_cash" },
      { path: "/expense-heads", icon: Tags, label: "Expense Heads", forMGT: true },
      { path: "/daily-text", icon: MessageSquare, label: "Daily Text Generator", roleKey: "sales_cash" },
    ]
  },
  {
    id: "accounts",
    label: "Accounts",
    icon: BarChart3,
    forAccounts: true,
    items: [
      { path: "/center-accounts", icon: Building2, label: "Center Accounts", forAccounts: true },
      { path: "/loan-entries", icon: Wallet, label: "Loan Entries", forAccounts: true },
      { path: "/historical-import", icon: Upload, label: "Historical Import", forAccounts: true, superAdminOnly: true },
      { path: "/mis-dashboard", icon: BarChart3, label: "MIS Dashboard", forAccounts: true },
    ]
  },
  {
    id: "hr",
    label: "HR Management",
    icon: Users,
    roleKey: "hr",
    forMGT: true,
    items: [
      { path: "/employees", icon: Users, label: "Employees", roleKey: "hr" },
      { path: "/salary", icon: FileSpreadsheet, label: "Salary", roleKey: "hr" },
      { path: "/payslips", icon: FileText, label: "Payslips", roleKey: "hr" },
      { path: "/hr-letters", icon: Briefcase, label: "HR Letters", roleKey: "hr" },
    ]
  },
  {
    id: "mgt",
    label: "Management",
    icon: Building2,
    roleKey: "mgt",
    forMGT: true,
    items: [
      { path: "/centers", icon: Building2, label: "Centers", forMGT: true },
      { path: "/managers", icon: UserCog, label: "Managers", forMGT: true },
      { path: "/role-management", icon: Shield, label: "Role Management", forMGT: true },
      { path: "/master-data", icon: Database, label: "Master Data", forMGT: true },
      { path: "/user-manuals", icon: BookOpen, label: "User Manuals", forMGT: true },
    ]
  },
  {
    id: "franchise",
    label: "Franchise",
    icon: Store,
    forFranchise: true,
    items: [
      { path: "/franchises", icon: Store, label: "Franchise Management", forFranchise: true, franchiseAdminOnly: true },
      { path: "/owner-reports", icon: FileText, label: "Owner Reports", forFranchise: true },
      { path: "/franchise-exit", icon: FileText, label: "Exit & Closure", forFranchise: true },
      { path: "/franchise-dashboard", icon: BarChart3, label: "Owner Dashboard", forFranchise: true },
      { path: "/social-media", icon: Share2, label: "Social Media Planner", forFranchise: true },
      { path: "/bill-download", icon: Download, label: "Bill Download", forFranchise: true },
      { path: "/documents", icon: FileCheck2, label: "Documents", forFranchise: true, franchiseAdminOnly: true },
    ]
  },
  {
    id: "operations",
    label: "Operations",
    icon: ChefHat,
    roleKey: "operations",
    items: [
      { path: "/booking-intelligence", icon: CalendarDays, label: "Booking Intelligence", roleKey: "operations" },
      { path: "/bhojan-guru", icon: ChefHat, label: "Bhojan Guru", roleKey: "operations" },
      { path: "/guest-response", icon: MessageCircle, label: "Guest Response", roleKey: "operations" },
      { path: "/recipe-admin", icon: Settings, label: "Recipe Admin", roleKey: "operations" },
    ]
  },
  {
    id: "billing",
    label: "Billing / POS",
    icon: Receipt,
    roleKey: "billing",
    forAdmin: true,
    items: [
      { path: "/pos-billing", icon: Receipt, label: "POS / Billing", roleKey: "billing", forAdmin: true },
      { path: "/billing-config", icon: Cog, label: "Configuration", roleKey: "billing", forAdmin: true },
      { path: "/menu-management", icon: UtensilsCrossed, label: "Menu Items", roleKey: "billing", forAdmin: true },
    ]
  },
  {
    id: "food_safety",
    label: "Food Safety",
    icon: Shield,
    forInternational: true,
    items: [
      { path: "/food-safety", icon: Shield, label: "Food Safety", forInternational: true },
    ]
  },
];

export default function Dashboard() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState(["attendance", "sales", "hr", "mgt", "franchise", "operations", "billing", "food_safety"]);
  const [centersList, setCentersList] = useState([]);
  
  // Fetch centers from DB on mount
  useEffect(() => {
    if (session?.token) {
      fetchCentersFromDB(session.token).then(setCentersList);
    }
  }, [session?.token]);
  
  // Check user access levels (RBAC-driven, no hardcoding)
  const isSuperAdmin = session?.is_super_admin === true;
  const isAdmin = isAdminUser(session);
  
  // Get user's role permissions from session (assigned by Super Admin)
  // Super Admin gets all access, others get their assigned roles
  // NEW: Accounting role gets sales_cash access to ALL centers
  const userRoles = isSuperAdmin ? {
    attendance: true,
    sales_cash: true,
    hr: true,
    mgt: true,
    operations: true,
    view_all_centers: true,
    accounting: true,
    franchise: true,
    billing: true
  } : (session?.roles || {});
  
  // Check if user has accounting role (can view all centers in Sales & Cash)
  const hasAccountingRole = userRoles.accounting === true;

  // Toggle category expansion
  const toggleCategory = (categoryId) => {
    setExpandedCategories(prev => 
      prev.includes(categoryId)
        ? prev.filter(id => id !== categoryId)
        : [...prev, categoryId]
    );
  };

  // Check if user has access to an item based on their assigned roles
  const hasAccess = (item) => {
    if (isSuperAdmin) return true; // Super Admin has full access
    if (item.forMGT) return isAdmin; // Management items require Admin access
    if (item.forAdmin) {
      // Admin-only items can also be accessed via roleKey assignment
      if (isAdmin || isSuperAdmin) return true;
      if (item.roleKey && userRoles[item.roleKey] === true) return true;
      return false;
    }
    if (item.forInternational) {
      // International items: visible to Admin, Super Admin, and international center managers
      // NOT visible to India center managers
      if (isAdmin || isSuperAdmin) return true;
      // Check session for center info - allow if not an India center
      // We rely on the backend to reject India centers, but hide from sidebar too
      const centerCode = session?.center || "";
      // If center has is_india_center flag from session, use it
      if (session?.is_india_center === false) return true;
      if (session?.is_india_center === true) return false;
      // Default: use center data from DB to determine if India center
      const centerData = centersList.find(c => c.code === centerCode);
      if (centerData) return centerData.is_india_center === false;
      return false; // Default hide for unknown centers
    }
    if (item.forFranchise) {
      const hasFranchiseAccess = isAdmin || userRoles.franchise === true;
      if (!hasFranchiseAccess) return false;
      // Franchise owners (non-admin users with franchise role) can only see Owner Dashboard + Exit
      // franchiseAdminOnly items are hidden for non-admin franchise users
      if (item.franchiseAdminOnly) {
        const isFranchiseOnlyUser = !isAdmin && !isSuperAdmin && (session?.role_key === "franchise_owner" || userRoles.franchise === true);
        if (isFranchiseOnlyUser) return false;
      }
      return true;
    }
    if (item.superAdminOnly && !isSuperAdmin) return false;
    if (item.forAccounts) {
      return isAdmin || userRoles.accounting === true;
    }
    if (item.roleKey) {
      if (item.roleKey === "sales_cash" && userRoles.accounting) {
        return true;
      }
      return userRoles[item.roleKey] === true;
    }
    return true;
  };

  // Check if user has access to a category
  const hasCategoryAccess = (category) => {
    if (isSuperAdmin) return true;
    if (category.forMGT) return isAdmin;
    if (category.forInternational) {
      if (isAdmin) return true;
      const centerCode = session?.center || "";
      if (session?.is_india_center === false) return true;
      if (session?.is_india_center === true) return false;
      const centerData = centersList.find(c => c.code === centerCode);
      if (centerData) return centerData.is_india_center === false;
      return false;
    }
    if (category.forFranchise) {
      // Franchise category accessible to Admin or users with franchise role
      const hasFranchiseAccess = isAdmin || userRoles.franchise === true;
      if (!hasFranchiseAccess) return false;
      // Check at least one item is accessible
      return category.items.some(item => hasAccess(item));
    }
    if (category.roleKey) {
      // Special case: Accounting role gets sales_cash category access
      if (category.roleKey === "sales_cash" && userRoles.accounting) {
        return true;
      }
      return userRoles[category.roleKey] === true;
    }
    return true;
  };

  // Filter categories and items based on access
  const filteredCategories = menuCategories
    .filter(cat => hasCategoryAccess(cat))
    .map(cat => ({
      ...cat,
      items: cat.items.filter(item => hasAccess(item))
    }))
    .filter(cat => cat.items.length > 0);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-background">
      {/* Mobile menu button */}
      <Button
        variant="ghost"
        size="icon"
        className="fixed top-4 left-4 z-50 lg:hidden"
        onClick={() => setSidebarOpen(!sidebarOpen)}
      >
        {sidebarOpen ? <X /> : <Menu />}
      </Button>

      {/* Sidebar overlay for mobile */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={cn(
        "fixed lg:sticky top-0 left-0 h-screen w-64 sidebar z-50 transition-transform duration-300 flex flex-col",
        sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}>
        {/* Logo */}
        <div className="p-6 border-b border-white/10">
          <h1 className="text-2xl font-bold text-white">Purnabramha</h1>
          <p className="text-white/60 text-sm mt-1">IntraPB Portal</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
          {filteredCategories.map((category) => (
            <div key={category.id} className="space-y-1">
              {/* Category Header */}
              <button
                onClick={() => toggleCategory(category.id)}
                className="w-full flex items-center justify-between px-3 py-2 text-sm font-semibold text-white/70 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
              >
                <div className="flex items-center gap-2">
                  <category.icon className="w-4 h-4" />
                  <span>{category.label}</span>
                </div>
                {expandedCategories.includes(category.id) 
                  ? <ChevronDown className="w-4 h-4" />
                  : <ChevronRight className="w-4 h-4" />
                }
              </button>
              
              {/* Category Items */}
              {expandedCategories.includes(category.id) && (
                <div className="ml-4 space-y-1">
                  {category.items.map((item) => (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      end={item.path === "/"}
                      onClick={() => setSidebarOpen(false)}
                      className={({ isActive }) => cn(
                        "sidebar-item text-sm",
                        isActive && "active"
                      )}
                      data-testid={`nav-${item.label.toLowerCase().replace(/\s/g, '-')}`}
                    >
                      <item.icon className="w-4 h-4" />
                      <span>{item.label}</span>
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          ))}
        </nav>

        {/* User info & Logout */}
        <div className="p-4 border-t border-white/10">
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/5 mb-3">
            <Building2 className="w-5 h-5 text-secondary" />
            <div className="flex-1 min-w-0">
              <p className="text-white font-semibold text-sm truncate">
                {session?.center}
              </p>
              <p className="text-white/60 text-xs truncate">
                {session?.managerName}
              </p>
            </div>
          </div>
          <Button
            data-testid="logout-btn"
            variant="ghost"
            className="w-full justify-start text-white/80 hover:text-white hover:bg-white/10"
            onClick={handleLogout}
          >
            <LogOut className="w-5 h-5 mr-3" />
            Logout
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-h-screen lg:ml-0">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-card/80 backdrop-blur-md border-b border-border">
          <div className="flex items-center justify-between px-6 py-4 lg:px-8">
            <div className="flex items-center gap-4 lg:gap-6">
              <div className="lg:hidden w-10" /> {/* Spacer for mobile menu */}
              <div>
                <h2 className="text-lg font-bold text-primary">
                  {session?.center}
                </h2>
                <p className="text-sm text-muted-foreground">
                  {session?.managerName}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-2 text-sm text-muted-foreground">
                <Clock className="w-4 h-4" />
                <span>{new Date().toLocaleDateString()}</span>
              </div>
              {isSuperAdmin && (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-red-500/20 text-red-500 border border-red-500/30">
                  Super Admin
                </span>
              )}
              {!isSuperAdmin && isAdmin && (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-purple-500/20 text-purple-500 border border-purple-500/30">
                  Admin
                </span>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <div className="p-4 lg:p-8 animate-fadeIn">
          <Routes>
            <Route path="/" element={<Attendance />} />
            <Route path="/international-attendance" element={<InternationalAttendance />} />
            <Route path="/international-roster" element={<InternationalRoster />} />
            <Route path="/employee-transfers" element={<EmployeeTransfers />} />
            <Route path="/attendance-dashboard" element={<AttendanceDashboard />} />
            <Route path="/sales" element={<SalesExpenses />} />
            <Route path="/expense-heads" element={<ExpenseHeads />} />
            <Route path="/guest-response" element={<GuestResponse />} />
            <Route path="/employees" element={<Employees />} />
            <Route path="/salary" element={<Salary />} />
            <Route path="/payslips" element={<Salary isPayslips />} />
            <Route path="/hr-letters" element={<HRLetters />} />
            <Route path="/centers" element={<CentersManagement />} />
            <Route path="/managers" element={<ManagersManagement />} />
            <Route path="/role-management" element={<RoleManagement />} />
            <Route path="/franchises" element={<FranchiseManagement />} />
            <Route path="/franchise-exit" element={<FranchiseExit />} />
            <Route path="/center-accounts" element={<CenterAccounts />} />
            <Route path="/historical-import" element={<HistoricalImport />} />
            <Route path="/owner-reports" element={<OwnerReports />} />
            <Route path="/loan-entries" element={<LoanEntries />} />
            <Route path="/mis-dashboard" element={<MISDashboard />} />
            <Route path="/booking-intelligence" element={<BookingIntelligence />} />
            <Route path="/bhojan-guru" element={<BhojanGuru />} />
            <Route path="/recipe-admin" element={<RecipeAdmin />} />
            <Route path="/master-data" element={<MasterDataManagement />} />
            <Route path="/user-manuals" element={<UserManuals />} />
            <Route path="/menu-management" element={<MenuManagement />} />
            <Route path="/franchise-dashboard" element={<FranchiseOwnerDashboard />} />
            <Route path="/pos-billing" element={<POSBilling />} />
            <Route path="/billing-config" element={<BillingConfiguration />} />
            <Route path="/documents" element={<DocumentManagement />} />
            <Route path="/food-safety" element={<FoodSafety />} />
            <Route path="/daily-text" element={<DailyTextGenerator />} />
            <Route path="/social-media" element={<SocialMediaPlanner />} />
            <Route path="/bill-download" element={<BillDownload />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
