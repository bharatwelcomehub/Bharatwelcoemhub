import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { api, CENTERS } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { 
  Loader2, 
  Plus, 
  Save, 
  Trash2, 
  Search,
  Users,
  X,
  RefreshCw,
  Edit
} from "lucide-react";

export default function Employees() {
  const { session } = useAuth();
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [centerFilter, setCenterFilter] = useState("");
  
  // Selected employee for editing
  const [selectedEmp, setSelectedEmp] = useState(null);
  const [editMode, setEditMode] = useState(false); // true = edit existing, false = add new
  
  // Form state
  const [formData, setFormData] = useState({
    name: "",
    center: "PB-HSR",
    designation: "",
    currentSalary: "",
    salaryBase: "",
    bankName: "",
    beneAccNo: "",
    ifsc: "",
    mobile: "",
    email: "",
    gender: "",
    dateOfJoining: "",
    remark: ""
  });

  // Reset form
  const resetForm = () => {
    setFormData({
      name: "",
      center: "PB-HSR",
      designation: "",
      currentSalary: "",
      salaryBase: "",
      bankName: "",
      beneAccNo: "",
      ifsc: "",
      mobile: "",
      email: "",
      gender: "",
      dateOfJoining: "",
      remark: ""
    });
    setSelectedEmp(null);
    setEditMode(false);
  };

  // Load employees
  const loadEmployees = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.post("/mgt_employees_list", {
        token: session.token,
        center: "PB-MGT"
      });
      setEmployees(res.data.employees || []);
      toast.success(`Loaded ${res.data.employees?.length || 0} employees`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to load employees");
    } finally {
      setLoading(false);
    }
  }, [session?.token]);

  useEffect(() => {
    if (session?.center === "PB-MGT") {
      loadEmployees();
    }
  }, [session?.center, loadEmployees]);

  // Filter employees
  const filteredEmployees = employees.filter(emp => {
    const q = search.toLowerCase();
    const matchesSearch = !search || 
      emp.name?.toLowerCase().includes(q) ||
      emp.center?.toLowerCase().includes(q) ||
      emp.designation?.toLowerCase().includes(q) ||
      emp.mobile?.toLowerCase().includes(q) ||
      emp.bankName?.toLowerCase().includes(q);
    const matchesCenter = !centerFilter || emp.center === centerFilter;
    return matchesSearch && matchesCenter;
  });

  // Select employee for editing
  const selectEmployee = (emp) => {
    setSelectedEmp(emp);
    setEditMode(true);
    setFormData({
      name: emp.name || "",
      center: emp.center || "PB-HSR",
      designation: emp.designation || "",
      currentSalary: emp.currentSalary?.toString() || "",
      salaryBase: emp.salaryBase?.toString() || "",
      bankName: emp.bankName || "",
      beneAccNo: emp.beneAccNo || "",
      ifsc: emp.ifsc || "",
      mobile: emp.mobile || "",
      email: emp.email || "",
      gender: emp.gender || "",
      dateOfJoining: emp.dateOfJoining || "",
      remark: emp.remark || ""
    });
  };

  // Create new employee
  const createEmployee = async () => {
    if (!formData.name || !formData.center) {
      toast.error("Name and Center are required");
      return;
    }
    
    setLoading(true);
    try {
      await api.post("/mgt_employee_create", {
        token: session.token,
        center: "PB-MGT",
        empCenter: formData.center,
        name: formData.name.toUpperCase(),
        designation: formData.designation,
        currentSalary: parseFloat(formData.currentSalary) || 0,
        salaryBase: parseFloat(formData.salaryBase) || 0,
        bankName: formData.bankName,
        beneAccNo: formData.beneAccNo,
        ifsc: formData.ifsc,
        mobile: formData.mobile,
        email: formData.email,
        gender: formData.gender,
        dateOfJoining: formData.dateOfJoining,
        remark: formData.remark
      });
      toast.success("Employee created!");
      resetForm();
      loadEmployees();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to create employee");
    } finally {
      setLoading(false);
    }
  };

  // Update employee
  const updateEmployee = async () => {
    if (!selectedEmp) return;
    
    setLoading(true);
    try {
      await api.post("/mgt_employee_update", {
        token: session.token,
        center: "PB-MGT",
        rowIndex: selectedEmp.rowIndex,
        empCenter: formData.center,
        name: formData.name.toUpperCase(),
        designation: formData.designation,
        currentSalary: parseFloat(formData.currentSalary) || 0,
        salaryBase: parseFloat(formData.salaryBase) || 0,
        bankName: formData.bankName,
        beneAccNo: formData.beneAccNo,
        ifsc: formData.ifsc,
        mobile: formData.mobile,
        email: formData.email,
        gender: formData.gender,
        dateOfJoining: formData.dateOfJoining,
        remark: formData.remark
      });
      toast.success("Employee updated!");
      resetForm();
      loadEmployees();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to update");
    } finally {
      setLoading(false);
    }
  };

  // Delete employee
  const deleteEmployee = async () => {
    if (!selectedEmp) return;
    if (!window.confirm(`Delete "${selectedEmp.name}"?`)) return;
    
    setLoading(true);
    try {
      await api.post("/mgt_employee_delete", {
        token: session.token,
        center: "PB-MGT",
        rowIndex: selectedEmp.rowIndex
      });
      toast.success("Employee deleted!");
      resetForm();
      loadEmployees();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to delete");
    } finally {
      setLoading(false);
    }
  };

  // Update form field
  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-primary">Employee Management</h1>
          <p className="text-muted-foreground mt-1">
            {employees.length} employees • Click checkbox to edit
          </p>
        </div>
        <Button onClick={loadEmployees} disabled={loading} variant="outline">
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Edit/Add Card - Shows when employee selected or adding new */}
      <Card className={`border-2 ${editMode ? 'border-primary' : 'border-secondary'}`}>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                {editMode ? <Edit className="w-5 h-5" /> : <Plus className="w-5 h-5" />}
                {editMode ? `Edit: ${selectedEmp?.name}` : "Add New Employee"}
              </CardTitle>
              <CardDescription>
                {editMode ? "Update employee details below" : "Fill in the form to add a new employee"}
              </CardDescription>
            </div>
            {(editMode || formData.name) && (
              <Button variant="ghost" size="sm" onClick={resetForm}>
                <X className="w-4 h-4 mr-1" />
                Clear
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input
                value={formData.name}
                onChange={(e) => updateField("name", e.target.value)}
                placeholder="EMPLOYEE NAME"
                className="uppercase"
                data-testid="emp-name"
              />
            </div>
            <div className="space-y-2">
              <Label>Center *</Label>
              <select
                value={formData.center}
                onChange={(e) => updateField("center", e.target.value)}
                className="w-full h-10 px-3 rounded-md border border-input bg-background"
                data-testid="emp-center"
              >
                {CENTERS.map(c => (
                  <option key={c.code} value={c.code}>{c.code}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Designation</Label>
              <Input
                value={formData.designation}
                onChange={(e) => updateField("designation", e.target.value)}
                placeholder="e.g. MANAGER, EMPLOYEE"
              />
            </div>
            <div className="space-y-2">
              <Label>Gender</Label>
              <select
                value={formData.gender}
                onChange={(e) => updateField("gender", e.target.value)}
                className="w-full h-10 px-3 rounded-md border border-input bg-background"
              >
                <option value="">Select</option>
                <option value="MALE">MALE</option>
                <option value="FEMALE">FEMALE</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>Current Salary</Label>
              <Input
                type="number"
                value={formData.currentSalary}
                onChange={(e) => updateField("currentSalary", e.target.value)}
                placeholder="45000"
              />
            </div>
            <div className="space-y-2">
              <Label>Base Salary</Label>
              <Input
                type="number"
                value={formData.salaryBase}
                onChange={(e) => updateField("salaryBase", e.target.value)}
                placeholder="40000"
              />
            </div>
            <div className="space-y-2">
              <Label>Bank Name</Label>
              <Input
                value={formData.bankName}
                onChange={(e) => updateField("bankName", e.target.value)}
                placeholder="HDFC, ICICI, SBI"
              />
            </div>
            <div className="space-y-2">
              <Label>Account No</Label>
              <Input
                value={formData.beneAccNo}
                onChange={(e) => updateField("beneAccNo", e.target.value)}
                placeholder="50100291509491"
              />
            </div>
            <div className="space-y-2">
              <Label>IFSC Code</Label>
              <Input
                value={formData.ifsc}
                onChange={(e) => updateField("ifsc", e.target.value)}
                placeholder="HDFC0004220"
              />
            </div>
            <div className="space-y-2">
              <Label>Mobile</Label>
              <Input
                value={formData.mobile}
                onChange={(e) => updateField("mobile", e.target.value)}
                placeholder="9876543210"
              />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) => updateField("email", e.target.value)}
                placeholder="email@example.com"
              />
            </div>
            <div className="space-y-2">
              <Label>Date of Joining</Label>
              <Input
                type="date"
                value={formData.dateOfJoining}
                onChange={(e) => updateField("dateOfJoining", e.target.value)}
              />
            </div>
          </div>
          
          {/* Notes/Remark field - full width */}
          <div className="space-y-2">
            <Label>Notes / Remark (for fund transfer)</Label>
            <Textarea
              value={formData.remark}
              onChange={(e) => updateField("remark", e.target.value)}
              placeholder="Add notes for account fund transfer or other remarks..."
              rows={2}
              data-testid="emp-remark"
            />
          </div>

          {/* Action buttons */}
          <div className="flex gap-3 pt-2">
            {editMode ? (
              <>
                <Button onClick={updateEmployee} disabled={loading} data-testid="update-emp-btn">
                  {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  <Save className="w-4 h-4 mr-2" />
                  Update Employee
                </Button>
                <Button variant="destructive" onClick={deleteEmployee} disabled={loading}>
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete
                </Button>
              </>
            ) : (
              <Button onClick={createEmployee} disabled={loading} data-testid="add-emp-btn">
                {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                <Plus className="w-4 h-4 mr-2" />
                Add Employee
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Employee List */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <CardTitle>Employee List ({filteredEmployees.length})</CardTitle>
            <div className="flex gap-2">
              {/* Center filter - using native select to avoid caching */}
              <select
                value={centerFilter}
                onChange={(e) => setCenterFilter(e.target.value)}
                className="h-10 px-3 rounded-md border border-input bg-background text-sm"
              >
                <option value="">All Centers</option>
                {CENTERS.map(c => (
                  <option key={c.code} value={c.code}>{c.code}</option>
                ))}
              </select>
              <div className="relative w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9"
                  data-testid="emp-search"
                />
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredEmployees.length > 0 ? (
            <div className="border rounded-lg overflow-hidden">
              <div className="overflow-x-auto max-h-[500px]">
                <table className="w-full text-sm">
                  <thead className="bg-muted sticky top-0 z-10">
                    <tr>
                      <th className="w-10 p-3"></th>
                      <th className="text-left p-3 font-bold">Center</th>
                      <th className="text-left p-3 font-bold">Name</th>
                      <th className="text-left p-3 font-bold">Designation</th>
                      <th className="text-left p-3 font-bold">Salary</th>
                      <th className="text-left p-3 font-bold">Bank</th>
                      <th className="text-left p-3 font-bold">Mobile</th>
                      <th className="text-left p-3 font-bold">Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredEmployees.map((emp, idx) => (
                      <tr 
                        key={idx} 
                        className={`border-t hover:bg-muted/30 cursor-pointer ${
                          selectedEmp?.name === emp.name ? 'bg-primary/10' : ''
                        }`}
                        onClick={() => selectEmployee(emp)}
                      >
                        <td className="p-3 text-center">
                          <Checkbox
                            checked={selectedEmp?.name === emp.name}
                            onCheckedChange={() => selectEmployee(emp)}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </td>
                        <td className="p-3">
                          <Badge variant="outline">{emp.center}</Badge>
                        </td>
                        <td className="p-3 font-semibold">{emp.name}</td>
                        <td className="p-3 text-muted-foreground">{emp.designation}</td>
                        <td className="p-3">
                          {emp.currentSalary ? `₹${emp.currentSalary.toLocaleString()}` : '-'}
                        </td>
                        <td className="p-3">
                          <div className="text-xs">
                            <p>{emp.bankName}</p>
                            <p className="text-muted-foreground font-mono">{emp.beneAccNo}</p>
                          </div>
                        </td>
                        <td className="p-3 font-mono text-xs">{emp.mobile}</td>
                        <td className="p-3 max-w-[150px]">
                          <p className="truncate text-xs text-muted-foreground" title={emp.remark}>
                            {emp.remark || '-'}
                          </p>
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
