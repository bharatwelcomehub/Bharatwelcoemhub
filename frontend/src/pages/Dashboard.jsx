import { useState } from "react";
import { Routes, Route, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/App";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
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
  BarChart3
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
import BookingIntelligence from "@/pages/BookingIntelligence";
import AttendanceDashboard from "@/pages/AttendanceDashboard";

// Menu categories structure
const menuCategories = [
  {
    id: "attendance",
    label: "Attendance",
    icon: Calendar,
    roleKey: "attendance",
    items: [
      { path: "/", icon: Calendar, label: "Daily Attendance", roleKey: "attendance" },
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
    ]
  },
  {
    id: "accounts",
    label: "Accounts",
    icon: BarChart3,
    forAccounts: true,
    items: [
      { path: "/center-accounts", icon: Building2, label: "Center Accounts", forAccounts: true },
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
    ]
  },
  {
    id: "franchise",
    label: "Franchise",
    icon: Store,
    forFranchise: true,
    items: [
      { path: "/franchises", icon: Store, label: "Franchise Management", forFranchise: true },
      { path: "/franchise-exit", icon: FileText, label: "Exit & Closure", forFranchise: true },
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
];

export default function Dashboard() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState(["attendance", "sales", "hr", "mgt", "franchise", "operations"]);
  
  // Check user access levels
  const isSuperAdmin = session?.is_super_admin === true;
  const isAdmin = session?.is_admin === true;
  
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
    franchise: true
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
    if (item.forMGT) return isSuperAdmin; // MGT-only items require Super Admin
    if (item.forAdmin) {
      // Admin items accessible to Admin or Super Admin
      return isAdmin || isSuperAdmin;
    }
    if (item.forFranchise) {
      // Franchise items accessible to Admin or users with franchise role
      return isAdmin || userRoles.franchise === true;
    }
    if (item.forAccounts) {
      // Accounts items accessible to Admin or Accounting role
      return isAdmin || userRoles.accounting === true;
    }
    if (item.roleKey) {
      // Special case: Accounting role gets sales_cash access
      if (item.roleKey === "sales_cash" && userRoles.accounting) {
        return true;
      }
      return userRoles[item.roleKey] === true;
    }
    return true; // Items without roleKey are accessible by default
  };

  // Check if user has access to a category
  const hasCategoryAccess = (category) => {
    if (isSuperAdmin) return true;
    if (category.forMGT) return isSuperAdmin;
    if (category.forFranchise) {
      // Franchise category accessible to Admin or users with franchise role
      return isAdmin || userRoles.franchise === true;
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
            <Route path="/mis-dashboard" element={<MISDashboard />} />
            <Route path="/booking-intelligence" element={<BookingIntelligence />} />
            <Route path="/bhojan-guru" element={<BhojanGuru />} />
            <Route path="/recipe-admin" element={<RecipeAdmin />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
