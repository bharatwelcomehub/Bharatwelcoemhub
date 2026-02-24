import { useState } from "react";
import { Routes, Route, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/App";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { 
  Calendar, 
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
  Shield
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

// Menu categories structure
const menuCategories = [
  {
    id: "attendance",
    label: "Attendance",
    icon: Calendar,
    roleKey: "attendance",
    items: [
      { path: "/", icon: Calendar, label: "Daily Attendance", roleKey: "attendance" },
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
    id: "operations",
    label: "Operations",
    icon: ChefHat,
    roleKey: "operations",
    items: [
      { path: "/bhojan-guru", icon: ChefHat, label: "Bhojan Guru", roleKey: "operations" },
      { path: "/guest-response", icon: MessageCircle, label: "Guest Response", roleKey: "operations" },
      { path: "/recipe-admin", icon: Settings, label: "Recipe Admin", forMGT: true },
    ]
  },
];

export default function Dashboard() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState(["attendance", "sales", "hr", "mgt", "operations"]);
  const isMGT = session?.center === "PB-MGT";
  
  // Get user's role permissions (MGT has all access)
  const userRoles = isMGT ? {
    attendance: true,
    sales_cash: true,
    hr: true,
    mgt: true,
    operations: true
  } : (session?.roles || {
    attendance: true,
    sales_cash: true,
    hr: false,
    mgt: false,
    operations: true
  });

  // Toggle category expansion
  const toggleCategory = (categoryId) => {
    setExpandedCategories(prev => 
      prev.includes(categoryId)
        ? prev.filter(id => id !== categoryId)
        : [...prev, categoryId]
    );
  };

  // Check if user has access to an item
  const hasAccess = (item) => {
    if (isMGT) return true; // MGT has full access
    if (item.forMGT) return false; // MGT-only items
    if (item.roleKey) return userRoles[item.roleKey] !== false;
    return true;
  };

  // Check if user has access to a category
  const hasCategoryAccess = (category) => {
    if (isMGT) return true;
    if (category.forMGT) return false;
    if (category.roleKey) return userRoles[category.roleKey] !== false;
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
              {isMGT && (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-secondary/20 text-secondary border border-secondary/30">
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
            <Route path="/sales" element={<SalesExpenses />} />
            <Route path="/expense-heads" element={<ExpenseHeads />} />
            <Route path="/guest-response" element={<GuestResponse />} />
            <Route path="/employees" element={<Employees />} />
            <Route path="/salary" element={<Salary />} />
            <Route path="/payslips" element={<Salary isPayslips />} />
            <Route path="/hr-letters" element={<HRLetters />} />
            <Route path="/centers" element={<CentersManagement />} />
            <Route path="/managers" element={<ManagersManagement />} />
            <Route path="/bhojan-guru" element={<BhojanGuru />} />
            <Route path="/recipe-admin" element={<RecipeAdmin />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
