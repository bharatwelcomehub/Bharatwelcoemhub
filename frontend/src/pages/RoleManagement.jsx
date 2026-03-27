import { useState, useEffect } from "react";
import { useAuth } from "@/App";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { 
  Shield, 
  Save, 
  Users, 
  Lock,
  Calendar,
  IndianRupee,
  Briefcase,
  Building2,
  ChefHat,
  Store,
  Receipt,
  RefreshCw,
  Search
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";

// Role definitions matching sidebar categories
const ROLE_MODULES = [
  {
    id: "attendance",
    label: "Attendance",
    icon: Calendar,
    description: "Daily attendance management"
  },
  {
    id: "sales_cash",
    label: "Sales & Cash",
    icon: IndianRupee,
    description: "Sales dashboard, expense entry, expense heads"
  },
  {
    id: "accounting",
    label: "Accounting (Full Access)",
    icon: IndianRupee,
    description: "Full Sales & Cash access for ALL centers"
  },
  {
    id: "hr",
    label: "HR Management",
    icon: Briefcase,
    description: "Employees, salary, payslips, HR letters"
  },
  {
    id: "mgt",
    label: "Management",
    icon: Building2,
    description: "Centers, managers, role management"
  },
  {
    id: "operations",
    label: "Operations",
    icon: ChefHat,
    description: "Bhojan Guru, guest response, recipes"
  },
  {
    id: "franchise",
    label: "Franchise",
    icon: Store,
    description: "Franchise management, exit & closure processes"
  },
  {
    id: "billing",
    label: "Billing / POS",
    icon: Receipt,
    description: "POS billing, KOT, invoices, bill management"
  },
  {
    id: "view_all_centers",
    label: "View All Centers",
    icon: Building2,
    description: "Access data from all centers (not just own)"
  }
];

// Admin level options (Super Admin is hardcoded - only Jayanti & Sandeep)
const ADMIN_LEVELS = [
  { id: "none", label: "Regular User", description: "Access based on assigned roles only" },
  { id: "admin", label: "Admin", description: "Has all assigned roles + can view all centers" }
];

export default function RoleManagement() {
  const { session } = useAuth();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [managers, setManagers] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [editingManager, setEditingManager] = useState(null);
  const [selectedRoles, setSelectedRoles] = useState({});
  const [selectedAdminLevel, setSelectedAdminLevel] = useState("none");
  
  // New: DB-driven roles
  const [systemRoles, setSystemRoles] = useState([]);
  const [selectedRoleKey, setSelectedRoleKey] = useState("");
  
  // Check if current user is super admin
  const isSuperAdmin = session?.is_super_admin === true;

  // Fetch managers with their roles
  const fetchManagers = async () => {
    setLoading(true);
    try {
      const [mgrRes, rolesRes] = await Promise.all([
        api.post("/mgt/managers", { token: session?.token }),
        api.post("/permissions/roles/list", { token: session?.token }).catch(() => ({ data: { roles: [] } }))
      ]);
      if (mgrRes.data.managers) setManagers(mgrRes.data.managers);
      if (rolesRes.data.roles) setSystemRoles(rolesRes.data.roles);
    } catch (err) {
      console.error("Failed to fetch managers:", err);
      toast.error("Failed to load managers");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (session?.token) {
      fetchManagers();
    }
  }, [session?.token]);

  // Filter managers by search
  const filteredManagers = managers.filter(m => 
    m.managerName?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.center?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Start editing a manager's roles
  const handleEditRoles = (manager) => {
    setEditingManager(manager);
    const roles = manager.roles || {
      attendance: true, sales_cash: true, hr: false,
      mgt: false, operations: true, franchise: false, view_all_centers: false
    };
    setSelectedRoles(roles);
    setSelectedRoleKey(manager.role_key || "");
    
    if (manager.is_super_admin) {
      setSelectedAdminLevel("super_admin");
    } else if (manager.is_admin) {
      setSelectedAdminLevel("admin");
    } else {
      setSelectedAdminLevel("none");
    }
  };

  // Toggle role selection
  const toggleRole = (roleId) => {
    setSelectedRoles(prev => ({
      ...prev,
      [roleId]: !prev[roleId]
    }));
  };

  // Save roles for a manager
  const handleSaveRoles = async () => {
    if (!editingManager) return;
    
    setSaving(true);
    try {
      // Save legacy module roles
      await api.post("/mgt/manager_roles", {
        token: session?.token,
        email: editingManager.email,
        roles: selectedRoles,
        is_admin: selectedAdminLevel === "admin"
      });
      
      // Also save the system role key if selected
      if (selectedRoleKey) {
        await api.post("/permissions/roles/assign", {
          token: session?.token,
          email: editingManager.email,
          role_key: selectedRoleKey
        }).catch(() => {});
      }
      
      toast.success(`Roles updated for ${editingManager.managerName || editingManager.email}`);
      setEditingManager(null);
      setSelectedRoles({});
      setSelectedAdminLevel("none");
      fetchManagers();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to update roles");
    } finally {
      setSaving(false);
    }
  };

  // Cancel editing
  const handleCancel = () => {
    setEditingManager(null);
    setSelectedRoles({});
    setSelectedAdminLevel("none");
  };

  // Get role badges for a manager
  const getRoleBadges = (manager) => {
    // Show admin level badge first
    const badges = [];
    
    if (manager.is_super_admin) {
      badges.push(
        <span key="super" className="text-xs px-2 py-1 bg-red-100 text-red-800 rounded-full font-semibold">
          Super Admin
        </span>
      );
    } else if (manager.is_admin) {
      badges.push(
        <span key="admin" className="text-xs px-2 py-1 bg-purple-100 text-purple-800 rounded-full font-semibold">
          Admin
        </span>
      );
    }
    
    const roles = manager.roles || {};
    const activeRoles = ROLE_MODULES.filter(r => roles[r.id] === true);
    
    if (manager.is_super_admin || manager.is_admin) {
      badges.push(
        <span key="all" className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded-full">All Access</span>
      );
    } else if (activeRoles.length > 0) {
      activeRoles.slice(0, 3).forEach(r => {
        badges.push(
          <span key={r.id} className="text-xs px-2 py-1 bg-muted rounded-full">{r.label}</span>
        );
      });
      if (activeRoles.length > 3) {
        badges.push(
          <span key="more" className="text-xs px-2 py-1 bg-muted rounded-full">+{activeRoles.length - 3} more</span>
        );
      }
    } else {
      badges.push(
        <span key="default" className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-full">Default</span>
      );
    }
    
    return badges;
  };

  // Check access - Only Super Admin can manage roles
  const canManageRoles = session?.is_super_admin === true;
  
  if (!canManageRoles) {
    return (
      <div className="text-center py-20">
        <Lock className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
        <h2 className="text-2xl font-bold text-muted-foreground">Access Denied</h2>
        <p className="text-muted-foreground mt-2">Only Super Admin can manage roles</p>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="role-management-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Shield className="w-6 h-6 text-primary" />
            Role & Access Management
          </h1>
          <p className="text-muted-foreground">Assign module access to managers</p>
        </div>
        
        <Button variant="outline" size="icon" onClick={fetchManagers} disabled={loading}>
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Search managers..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Role Editor */}
      {editingManager && (
        <Card className="bg-card border-border border-2 border-primary">
          <CardHeader>
            <CardTitle className="text-lg">
              Edit Roles for: {editingManager.managerName || editingManager.email}
              <span className="ml-2 text-sm font-normal text-muted-foreground">({editingManager.center})</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Admin Level Selector */}
            {isSuperAdmin && (
              <div className="space-y-3">
                <h3 className="font-semibold text-sm text-primary">Access Level</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {ADMIN_LEVELS.map(level => (
                    <div 
                      key={level.id}
                      className={`p-3 rounded-lg border-2 cursor-pointer transition-colors ${
                        selectedAdminLevel === level.id 
                          ? 'border-primary bg-primary/10' 
                          : 'border-border hover:border-muted-foreground'
                      }`}
                      onClick={() => setSelectedAdminLevel(level.id)}
                    >
                      <div className="flex items-center gap-2">
                        <input 
                          type="radio" 
                          checked={selectedAdminLevel === level.id}
                          onChange={() => setSelectedAdminLevel(level.id)}
                          className="w-4 h-4"
                        />
                        <span className="font-medium text-sm">{level.label}</span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 ml-6">{level.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* System Role (DB-driven) */}
            {systemRoles.length > 0 && (
              <div className="space-y-3">
                <h3 className="font-semibold text-sm text-primary">System Role (DB-Driven)</h3>
                <p className="text-xs text-muted-foreground">Assign a role from the permission engine. This overrides module-level access above.</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  <div 
                    className={`p-3 rounded-lg border-2 cursor-pointer transition-colors text-center ${!selectedRoleKey ? 'border-primary bg-primary/10' : 'border-border hover:border-muted-foreground'}`}
                    onClick={() => setSelectedRoleKey("")}
                  >
                    <span className="text-xs font-medium">No System Role</span>
                    <p className="text-[10px] text-muted-foreground mt-1">Use module-level access above</p>
                  </div>
                  {systemRoles.filter(r => r.is_active !== false).map(r => (
                    <div 
                      key={r.key}
                      className={`p-3 rounded-lg border-2 cursor-pointer transition-colors text-center ${selectedRoleKey === r.key ? 'border-primary bg-primary/10' : 'border-border hover:border-muted-foreground'}`}
                      onClick={() => setSelectedRoleKey(r.key)}
                      data-testid={`role-${r.key}`}
                    >
                      <span className="text-xs font-medium">{r.name}</span>
                      <p className="text-[10px] text-muted-foreground mt-1">{r.scope?.replace(/_/g, ' ')}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Module Roles */}
            <div className="space-y-3">
              <h3 className="font-semibold text-sm text-primary">Module Access</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {ROLE_MODULES.map(role => (
                  <div 
                    key={role.id}
                    className={`p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                      selectedRoles[role.id] 
                        ? 'border-primary bg-primary/5' 
                        : 'border-border hover:border-muted-foreground'
                    }`}
                    onClick={() => toggleRole(role.id)}
                  >
                    <div className="flex items-start gap-3">
                      <Checkbox
                        checked={selectedRoles[role.id] || false}
                        onCheckedChange={() => toggleRole(role.id)}
                        className="mt-1"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <role.icon className={`w-4 h-4 ${selectedRoles[role.id] ? 'text-primary' : 'text-muted-foreground'}`} />
                          <span className="font-medium">{role.label}</span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">{role.description}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="flex gap-2 justify-end pt-4">
              <Button variant="outline" onClick={handleCancel}>Cancel</Button>
              <Button onClick={handleSaveRoles} disabled={saving} className="gap-2">
                <Save className="w-4 h-4" />
                {saving ? "Saving..." : "Save Roles"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Managers List */}
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Users className="w-5 h-5 text-primary" />
            Managers ({filteredManagers.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">Center</th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">Manager Name</th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">Email</th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">Access</th>
                  <th className="text-right py-3 px-2 font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredManagers.map((manager, idx) => (
                  <tr key={manager.email || idx} className="border-b border-border/50 hover:bg-muted/50">
                    <td className="py-3 px-2">
                      <span className="px-2 py-1 bg-primary/10 text-primary rounded-md text-xs font-medium">
                        {manager.center}
                      </span>
                    </td>
                    <td className="py-3 px-2 font-medium">{manager.managerName || "-"}</td>
                    <td className="py-3 px-2 text-muted-foreground">{manager.email}</td>
                    <td className="py-3 px-2">
                      <div className="flex flex-wrap gap-1">
                        {manager.role_key && (
                          <Badge className="bg-purple-500/20 text-purple-400 text-[10px]">{manager.role_name || manager.role_key}</Badge>
                        )}
                        {getRoleBadges(manager)}
                      </div>
                    </td>
                    <td className="py-3 px-2 text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEditRoles(manager)}
                        disabled={editingManager?.email === manager.email}
                        data-testid={`edit-roles-${idx}`}
                      >
                        <Shield className="w-4 h-4 mr-1" />
                        Edit Roles
                      </Button>
                    </td>
                  </tr>
                ))}
                {filteredManagers.length === 0 && (
                  <tr>
                    <td colSpan={5} className="text-center py-8 text-muted-foreground">
                      {loading ? "Loading..." : "No managers found"}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="bg-muted/50 border-border">
        <CardContent className="pt-6">
          <h3 className="font-medium mb-2">Role Access Information</h3>
          <ul className="text-sm text-muted-foreground space-y-1">
            <li>• <strong>Attendance:</strong> View and manage daily attendance</li>
            <li>• <strong>Sales & Cash:</strong> Sales dashboard, daily entries, expense management</li>
            <li>• <strong>HR Management:</strong> Employee records, salary, payslips, HR letters</li>
            <li>• <strong>Management:</strong> Center management, manager administration</li>
            <li>• <strong>Operations:</strong> Menu planning (Bhojan Guru), guest response, recipes</li>
          </ul>
          <p className="text-xs text-muted-foreground mt-3">
            Note: Super Admin and Admin users have full access to all modules.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
