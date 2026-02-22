import { useState, useEffect } from "react";
import { useAuth } from "@/App";
import { api, CENTERS } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Loader2, 
  Plus, 
  Save, 
  Trash2, 
  Search,
  Users,
  Building2
} from "lucide-react";

export default function Employees() {
  const { session } = useAuth();
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  
  // New employee form
  const [newEmp, setNewEmp] = useState({
    name: "",
    empCenter: "PB-HSR",
    designation: "",
    currentSalary: "",
    beneAccNo: "",
    ifsc: "",
    bankName: "",
    mobile: "",
    email: ""
  });

  // Load employees
  const loadEmployees = async () => {
    setLoading(true);
    try {
      const res = await api.post("/mgt_employees_list", {
        token: session.token,
        center: "PB-MGT"
      });
      setEmployees(res.data.employees || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to load employees");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (session?.center === "PB-MGT") {
      loadEmployees();
    }
  }, []);

  // Filter employees by search
  const filteredEmployees = employees.filter(emp => {
    const q = search.toLowerCase();
    return (
      emp.name?.toLowerCase().includes(q) ||
      emp.center?.toLowerCase().includes(q) ||
      emp.designation?.toLowerCase().includes(q) ||
      emp.mobile?.toLowerCase().includes(q)
    );
  });

  // Create employee
  const createEmployee = async () => {
    if (!newEmp.name || !newEmp.empCenter) {
      toast.error("Name and Center are required");
      return;
    }
    
    setLoading(true);
    try {
      await api.post("/mgt_employee_create", {
        token: session.token,
        center: "PB-MGT",
        ...newEmp,
        currentSalary: parseFloat(newEmp.currentSalary) || 0
      });
      toast.success("Employee created!");
      setNewEmp({
        name: "",
        empCenter: "PB-HSR",
        designation: "",
        currentSalary: "",
        beneAccNo: "",
        ifsc: "",
        bankName: "",
        mobile: "",
        email: ""
      });
      loadEmployees();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to create employee");
    } finally {
      setLoading(false);
    }
  };

  // Update employee
  const updateEmployee = async (emp) => {
    setLoading(true);
    try {
      await api.post("/mgt_employee_update", {
        token: session.token,
        center: "PB-MGT",
        rowIndex: emp.rowIndex,
        ...emp
      });
      toast.success("Employee updated!");
      loadEmployees();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to update");
    } finally {
      setLoading(false);
    }
  };

  // Delete employee
  const deleteEmployee = async (emp) => {
    if (!window.confirm(`Delete "${emp.name}"?`)) return;
    
    setLoading(true);
    try {
      await api.post("/mgt_employee_delete", {
        token: session.token,
        center: "PB-MGT",
        rowIndex: emp.rowIndex
      });
      toast.success("Employee deleted!");
      loadEmployees();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to delete");
    } finally {
      setLoading(false);
    }
  };

  // Update local employee data
  const updateLocalEmployee = (index, field, value) => {
    setEmployees(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  if (session?.center !== "PB-MGT") {
    return (
      <div className="text-center py-20">
        <Users className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
        <h2 className="text-2xl font-bold text-muted-foreground">Access Denied</h2>
        <p className="text-muted-foreground mt-2">Only PB-MGT can manage employees</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-primary">Employee Management</h1>
        <p className="text-muted-foreground mt-1">
          Add, update, or remove employees (PB-MGT only)
        </p>
      </div>

      {/* Add Employee Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="w-5 h-5" />
            Add New Employee
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input
                value={newEmp.name}
                onChange={(e) => setNewEmp({ ...newEmp, name: e.target.value })}
                placeholder="Employee Name"
                data-testid="new-emp-name"
              />
            </div>
            <div className="space-y-2">
              <Label>Center *</Label>
              <Select
                value={newEmp.empCenter}
                onValueChange={(v) => setNewEmp({ ...newEmp, empCenter: v })}
              >
                <SelectTrigger data-testid="new-emp-center">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CENTERS.map(c => (
                    <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Designation</Label>
              <Input
                value={newEmp.designation}
                onChange={(e) => setNewEmp({ ...newEmp, designation: e.target.value })}
                placeholder="e.g. Chef, Manager"
              />
            </div>
            <div className="space-y-2">
              <Label>Salary</Label>
              <Input
                type="number"
                value={newEmp.currentSalary}
                onChange={(e) => setNewEmp({ ...newEmp, currentSalary: e.target.value })}
                placeholder="45000"
              />
            </div>
            <div className="space-y-2">
              <Label>Bank A/C</Label>
              <Input
                value={newEmp.beneAccNo}
                onChange={(e) => setNewEmp({ ...newEmp, beneAccNo: e.target.value })}
                placeholder="Account Number"
              />
            </div>
            <div className="space-y-2">
              <Label>IFSC</Label>
              <Input
                value={newEmp.ifsc}
                onChange={(e) => setNewEmp({ ...newEmp, ifsc: e.target.value })}
                placeholder="HDFC0001234"
              />
            </div>
            <div className="space-y-2">
              <Label>Bank Name</Label>
              <Input
                value={newEmp.bankName}
                onChange={(e) => setNewEmp({ ...newEmp, bankName: e.target.value })}
                placeholder="HDFC Bank"
              />
            </div>
            <div className="space-y-2">
              <Label>Mobile</Label>
              <Input
                value={newEmp.mobile}
                onChange={(e) => setNewEmp({ ...newEmp, mobile: e.target.value })}
                placeholder="9876543210"
              />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                type="email"
                value={newEmp.email}
                onChange={(e) => setNewEmp({ ...newEmp, email: e.target.value })}
                placeholder="email@example.com"
              />
            </div>
          </div>
          <Button onClick={createEmployee} disabled={loading} data-testid="add-emp-btn">
            {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            <Plus className="w-4 h-4 mr-2" />
            Add Employee
          </Button>
        </CardContent>
      </Card>

      {/* Employee List */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <CardTitle>Employee List ({filteredEmployees.length})</CardTitle>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search employees..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
                data-testid="emp-search"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredEmployees.length > 0 ? (
            <div className="border rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted">
                    <tr>
                      <th className="text-left p-3 font-bold">Center</th>
                      <th className="text-left p-3 font-bold">Name</th>
                      <th className="text-left p-3 font-bold">Designation</th>
                      <th className="text-left p-3 font-bold">Salary</th>
                      <th className="text-left p-3 font-bold">Bank</th>
                      <th className="text-left p-3 font-bold">Mobile</th>
                      <th className="text-left p-3 font-bold">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredEmployees.map((emp, idx) => (
                      <tr key={idx} className="border-t hover:bg-muted/30">
                        <td className="p-2">
                          <Input
                            value={emp.center || ""}
                            onChange={(e) => updateLocalEmployee(idx, "center", e.target.value)}
                            className="w-24 h-8"
                          />
                        </td>
                        <td className="p-2">
                          <Input
                            value={emp.name || ""}
                            onChange={(e) => updateLocalEmployee(idx, "name", e.target.value)}
                            className="w-40 h-8 font-semibold"
                          />
                        </td>
                        <td className="p-2">
                          <Input
                            value={emp.designation || ""}
                            onChange={(e) => updateLocalEmployee(idx, "designation", e.target.value)}
                            className="w-28 h-8"
                          />
                        </td>
                        <td className="p-2">
                          <Input
                            type="number"
                            value={emp.currentSalary || ""}
                            onChange={(e) => updateLocalEmployee(idx, "currentSalary", e.target.value)}
                            className="w-24 h-8"
                          />
                        </td>
                        <td className="p-2">
                          <div className="flex flex-col gap-1">
                            <Input
                              value={emp.bankName || ""}
                              onChange={(e) => updateLocalEmployee(idx, "bankName", e.target.value)}
                              placeholder="Bank"
                              className="w-28 h-7 text-xs"
                            />
                            <Input
                              value={emp.beneAccNo || ""}
                              onChange={(e) => updateLocalEmployee(idx, "beneAccNo", e.target.value)}
                              placeholder="A/C No"
                              className="w-28 h-7 text-xs"
                            />
                          </div>
                        </td>
                        <td className="p-2">
                          <Input
                            value={emp.mobile || ""}
                            onChange={(e) => updateLocalEmployee(idx, "mobile", e.target.value)}
                            className="w-28 h-8"
                          />
                        </td>
                        <td className="p-2">
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              onClick={() => updateEmployee(emp)}
                              disabled={loading}
                            >
                              <Save className="w-3 h-3" />
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => deleteEmployee(emp)}
                              disabled={loading}
                            >
                              <Trash2 className="w-3 h-3" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No employees found</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
