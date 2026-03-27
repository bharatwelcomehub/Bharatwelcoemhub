import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "@/App";
import { api, fetchCentersFromDB, isAdminUser } from "@/lib/api";
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
  Edit,
  Upload,
  Download,
  FileSpreadsheet,
  AlertCircle,
  CheckCircle
} from "lucide-react";
import * as XLSX from "xlsx";

export default function Employees() {
  const { session } = useAuth();
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [centerFilter, setCenterFilter] = useState("");
  const [centersList, setCentersList] = useState([]);
  
  // Selected employee for editing
  const [selectedEmp, setSelectedEmp] = useState(null);
  const [editMode, setEditMode] = useState(false); // true = edit existing, false = add new
  
  // Bulk upload state
  const [showBulkUpload, setShowBulkUpload] = useState(false);
  const [uploadData, setUploadData] = useState([]);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const fileInputRef = useRef(null);
  
  // Form state
  const [formData, setFormData] = useState({
    name: "",
    center: "",
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
      center: "",
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
        center: session.center
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
    if (isAdminUser(session)) {
      loadEmployees();
      // Fetch centers from DB
      fetchCentersFromDB(session.token).then(setCentersList);
    }
  }, [session?.is_super_admin, session?.is_admin, loadEmployees]);

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
      center: emp.center || "",
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
        center: session.center,
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
        center: session.center,
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
        center: session.center,
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

  // Download Excel template
  const downloadTemplate = () => {
    const templateData = [
      {
        "Center Code": "CENTER-1",
        "Employee Name": "JOHN DOE",
        "Gender": "Male",
        "Designation": "Chef",
        "Base Salary": 15000,
        "Current Salary": 18000,
        "Date of Joining": "2024-01-15",
        "Bank Name": "HDFC Bank",
        "Account Number": "1234567890",
        "IFSC Code": "HDFC0001234",
        "Mobile": "9876543210",
        "Email": "john@email.com",
        "Remarks": "Full time"
      },
      {
        "Center Code": "CENTER-2",
        "Employee Name": "JANE SMITH",
        "Gender": "Female",
        "Designation": "Manager",
        "Base Salary": 25000,
        "Current Salary": 30000,
        "Date of Joining": "2023-06-01",
        "Bank Name": "ICICI Bank",
        "Account Number": "0987654321",
        "IFSC Code": "ICIC0005678",
        "Mobile": "9123456789",
        "Email": "jane@email.com",
        "Remarks": ""
      }
    ];
    
    const ws = XLSX.utils.json_to_sheet(templateData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Employees");
    
    // Set column widths
    ws['!cols'] = [
      { wch: 12 }, { wch: 20 }, { wch: 10 }, { wch: 15 },
      { wch: 12 }, { wch: 14 }, { wch: 15 }, { wch: 15 },
      { wch: 18 }, { wch: 14 }, { wch: 12 }, { wch: 20 }, { wch: 15 }
    ];
    
    XLSX.writeFile(wb, "Employee_Upload_Template.xlsx");
    toast.success("Template downloaded!");
  };

  // Handle file upload
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const data = evt.target.result;
        const workbook = XLSX.read(data, { type: "binary" });
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        const jsonData = XLSX.utils.sheet_to_json(worksheet);
        
        // Map Excel columns to API fields
        const mappedData = jsonData.map(row => ({
          center: row["Center Code"] || row["center"] || "",
          name: row["Employee Name"] || row["name"] || "",
          gender: row["Gender"] || row["gender"] || "",
          designation: row["Designation"] || row["designation"] || "",
          salaryBase: row["Base Salary"] || row["salaryBase"] || 0,
          currentSalary: row["Current Salary"] || row["currentSalary"] || 0,
          dateOfJoining: row["Date of Joining"] || row["dateOfJoining"] || "",
          bankName: row["Bank Name"] || row["bankName"] || "",
          beneAccNo: String(row["Account Number"] || row["beneAccNo"] || ""),
          ifsc: row["IFSC Code"] || row["ifsc"] || "",
          mobile: String(row["Mobile"] || row["mobile"] || ""),
          email: row["Email"] || row["email"] || "",
          remark: row["Remarks"] || row["remark"] || ""
        }));
        
        setUploadData(mappedData);
        setUploadResult(null);
        toast.success(`Loaded ${mappedData.length} employees from file`);
      } catch (err) {
        console.error("File parse error:", err);
        toast.error("Failed to parse Excel file. Please use the correct template.");
      }
    };
    reader.readAsBinaryString(file);
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Submit bulk upload
  const submitBulkUpload = async () => {
    if (uploadData.length === 0) {
      toast.error("No data to upload. Please select a file first.");
      return;
    }
    
    if (!window.confirm(`Upload ${uploadData.length} employees? Existing employees with same name and center will be updated.`)) {
      return;
    }
    
    setUploadLoading(true);
    try {
      const res = await api.post("/mgt_employee_bulk_upload", {
        token: session.token,
        employees: uploadData
      });
      
      setUploadResult(res.data);
      toast.success(res.data.message);
      
      // Refresh employee list
      loadEmployees();
    } catch (err) {
      console.error("Bulk upload error:", err);
      toast.error(err.response?.data?.detail || "Bulk upload failed");
    } finally {
      setUploadLoading(false);
    }
  };

  // Clear bulk upload
  const clearBulkUpload = () => {
    setUploadData([]);
    setUploadResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Update form field
  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  if (!isAdminUser(session)) {
    return (
      <div className="text-center py-20">
        <Users className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
        <h2 className="text-2xl font-bold text-muted-foreground">Access Denied</h2>
        <p className="text-muted-foreground mt-2">Only Admin users can manage employees</p>
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
        <div className="flex gap-2">
          <Button 
            onClick={() => setShowBulkUpload(!showBulkUpload)} 
            variant={showBulkUpload ? "default" : "outline"}
          >
            <Upload className="w-4 h-4 mr-2" />
            Bulk Upload
          </Button>
          <Button onClick={loadEmployees} disabled={loading} variant="outline">
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Bulk Upload Section */}
      {showBulkUpload && (
        <Card className="border-2 border-blue-500">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <FileSpreadsheet className="w-5 h-5 text-blue-500" />
                  Bulk Employee Upload
                </CardTitle>
                <CardDescription>
                  Upload multiple employees at once using Excel file
                </CardDescription>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setShowBulkUpload(false)}>
                <X className="w-4 h-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Instructions */}
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm">
              <h4 className="font-semibold text-blue-800 dark:text-blue-300 mb-2">Instructions:</h4>
              <ol className="list-decimal list-inside space-y-1 text-blue-700 dark:text-blue-400">
                <li>Download the Excel template using the button below</li>
                <li>Fill in employee data (Center Code and Name are required)</li>
                <li>Upload the filled Excel file</li>
                <li>Review the preview and click "Upload All"</li>
              </ol>
              <p className="mt-2 text-blue-600 dark:text-blue-400">
                <strong>Note:</strong> Existing employees (same name + center) will be updated. New employees will be created.
              </p>
              <p className="mt-2 text-blue-600 dark:text-blue-400">
                <strong>Valid Center Codes:</strong> Use center codes as configured in Master Data
              </p>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap gap-3">
              <Button onClick={downloadTemplate} variant="outline" className="border-green-500 text-green-600 hover:bg-green-50">
                <Download className="w-4 h-4 mr-2" />
                Download Template
              </Button>
              
              <div className="relative">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleFileUpload}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <Button variant="outline" className="border-blue-500 text-blue-600 hover:bg-blue-50">
                  <Upload className="w-4 h-4 mr-2" />
                  Select Excel File
                </Button>
              </div>
              
              {uploadData.length > 0 && (
                <>
                  <Button 
                    onClick={submitBulkUpload} 
                    disabled={uploadLoading}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {uploadLoading ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <CheckCircle className="w-4 h-4 mr-2" />
                    )}
                    Upload {uploadData.length} Employees
                  </Button>
                  <Button onClick={clearBulkUpload} variant="ghost" className="text-red-500">
                    <X className="w-4 h-4 mr-2" />
                    Clear
                  </Button>
                </>
              )}
            </div>

            {/* Upload Result */}
            {uploadResult && (
              <div className={`p-4 rounded-lg ${uploadResult.errors?.length > 0 ? 'bg-amber-50 border border-amber-200' : 'bg-green-50 border border-green-200'}`}>
                <div className="flex items-center gap-2 mb-2">
                  {uploadResult.errors?.length > 0 ? (
                    <AlertCircle className="w-5 h-5 text-amber-600" />
                  ) : (
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  )}
                  <span className="font-semibold">{uploadResult.message}</span>
                </div>
                <div className="flex gap-4 text-sm">
                  <span className="text-green-600">Created: {uploadResult.created}</span>
                  <span className="text-blue-600">Updated: {uploadResult.updated}</span>
                  {uploadResult.errors?.length > 0 && (
                    <span className="text-red-600">Errors: {uploadResult.errors.length}</span>
                  )}
                </div>
                {uploadResult.errors?.length > 0 && (
                  <div className="mt-2 text-sm text-red-600">
                    {uploadResult.errors.map((err, i) => (
                      <div key={i}>• {err}</div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Preview Table */}
            {uploadData.length > 0 && !uploadResult && (
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-muted px-4 py-2 font-semibold">
                  Preview: {uploadData.length} employees to upload
                </div>
                <div className="max-h-64 overflow-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50 sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left">#</th>
                        <th className="px-3 py-2 text-left">Center</th>
                        <th className="px-3 py-2 text-left">Name</th>
                        <th className="px-3 py-2 text-left">Designation</th>
                        <th className="px-3 py-2 text-right">Salary</th>
                        <th className="px-3 py-2 text-left">Mobile</th>
                      </tr>
                    </thead>
                    <tbody>
                      {uploadData.slice(0, 50).map((emp, idx) => (
                        <tr key={idx} className="border-t hover:bg-muted/30">
                          <td className="px-3 py-2">{idx + 1}</td>
                          <td className="px-3 py-2">
                            <Badge variant="outline">{emp.center}</Badge>
                          </td>
                          <td className="px-3 py-2 font-medium">{emp.name}</td>
                          <td className="px-3 py-2">{emp.designation}</td>
                          <td className="px-3 py-2 text-right">₹{emp.currentSalary || emp.salaryBase || 0}</td>
                          <td className="px-3 py-2">{emp.mobile}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {uploadData.length > 50 && (
                    <div className="p-2 text-center text-sm text-muted-foreground bg-muted/30">
                      ... and {uploadData.length - 50} more employees
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

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
                {centersList.map(c => (
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
                {centersList.map(c => (
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
