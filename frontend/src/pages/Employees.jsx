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
  CheckCircle,
  Camera,
  FileText,
  Paperclip
} from "lucide-react";
import * as XLSX from "xlsx";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const BLOOD_GROUPS = ["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];
const VISA_TYPES = ["", "Student Visa", "Work Visa", "Holiday Visa", "PR", "Citizen", "Other"];

export default function Employees() {
  const { session } = useAuth();
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [centerFilter, setCenterFilter] = useState("");
  const [centersList, setCentersList] = useState([]);
  
  // Selected employee for editing
  const [selectedEmp, setSelectedEmp] = useState(null);
  const [editMode, setEditMode] = useState(false);
  
  // Bulk upload state
  const [showBulkUpload, setShowBulkUpload] = useState(false);
  const [uploadData, setUploadData] = useState([]);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const fileInputRef = useRef(null);
  
  // Photo & doc upload state
  const photoInputRef = useRef(null);
  const docInputRefs = useRef({});
  const [photoUploading, setPhotoUploading] = useState(false);
  const [docUploading, setDocUploading] = useState({});
  const [reportLoading, setReportLoading] = useState(false);
  
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
    remark: "",
    aadhaar: "",
    pan: "",
    tfn: "",
    blood_group: "",
    passport_number: "",
    visa_type: "",
    photo_url: "",
  });

  // Reset form
  const resetForm = () => {
    setFormData({
      name: "", center: "", designation: "", currentSalary: "", salaryBase: "",
      bankName: "", beneAccNo: "", ifsc: "", mobile: "", email: "", gender: "",
      dateOfJoining: "", remark: "", aadhaar: "", pan: "", tfn: "", blood_group: "",
      passport_number: "", visa_type: "", photo_url: "",
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
      remark: emp.remark || "",
      aadhaar: emp.aadhaar || "",
      pan: emp.pan || "",
      tfn: emp.tfn || "",
      blood_group: emp.blood_group || "",
      passport_number: emp.passport_number || "",
      visa_type: emp.visa_type || "",
      photo_url: emp.photo_url || "",
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
        remark: formData.remark,
        aadhaar: formData.aadhaar,
        pan: formData.pan,
        tfn: formData.tfn,
        blood_group: formData.blood_group,
        passport_number: formData.passport_number,
        visa_type: formData.visa_type,
        photo_url: formData.photo_url,
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
        remark: formData.remark,
        aadhaar: formData.aadhaar,
        pan: formData.pan,
        tfn: formData.tfn,
        blood_group: formData.blood_group,
        passport_number: formData.passport_number,
        visa_type: formData.visa_type,
        photo_url: formData.photo_url,
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

  // Upload photo
  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!formData.name || !formData.center) {
      toast.error("Save the employee first (Name + Center required) before uploading photo");
      return;
    }
    setPhotoUploading(true);
    try {
      const fd = new FormData();
      fd.append("token", session.token);
      fd.append("employee_name", formData.name.toUpperCase());
      fd.append("center", formData.center);
      fd.append("file", file);
      const res = await fetch(`${API_URL}/api/employee_upload_photo`, { method: "POST", body: fd });
      const data = await res.json();
      if (data.success) {
        setFormData(prev => ({ ...prev, photo_url: data.photo_url }));
        toast.success("Photo uploaded!");
        loadEmployees();
      } else {
        toast.error(data.detail || "Photo upload failed");
      }
    } catch (err) {
      toast.error("Photo upload failed");
    } finally {
      setPhotoUploading(false);
      if (photoInputRef.current) photoInputRef.current.value = "";
    }
  };

  // Upload document (aadhaar_doc, pan_doc, passport_doc, visa_doc)
  const handleDocUpload = async (docType, e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!formData.name || !formData.center) {
      toast.error("Save the employee first (Name + Center required) before uploading documents");
      return;
    }
    setDocUploading(prev => ({ ...prev, [docType]: true }));
    try {
      const fd = new FormData();
      fd.append("token", session.token);
      fd.append("employee_name", formData.name.toUpperCase());
      fd.append("center", formData.center);
      fd.append("doc_type", docType);
      fd.append("file", file);
      const res = await fetch(`${API_URL}/api/employee_upload_document`, { method: "POST", body: fd });
      const data = await res.json();
      if (data.success) {
        toast.success(`${docType.replace("_doc", "").toUpperCase()} document uploaded!`);
        loadEmployees();
      } else {
        toast.error(data.detail || "Document upload failed");
      }
    } catch (err) {
      toast.error("Document upload failed");
    } finally {
      setDocUploading(prev => ({ ...prev, [docType]: false }));
      if (docInputRefs.current[docType]) docInputRefs.current[docType].value = "";
    }
  };

  // Export Employee Report PDF
  const exportEmployeeReport = async () => {
    setReportLoading(true);
    try {
      const res = await api.post("/employee_report", {
        token: session.token,
        center: centerFilter || ""
      }, { responseType: "blob" });
      const contentType = res.headers["content-type"] || "";
      if (contentType.includes("application/json")) {
        const text = await res.data.text();
        const json = JSON.parse(text);
        toast.error(json.detail || "Failed to generate report");
        return;
      }
      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `Employee_Report_${centerFilter || "ALL"}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success("Employee Report downloaded!");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to generate report");
    } finally {
      setReportLoading(false);
    }
  };

  // Download Excel template
  const downloadTemplate = () => {
    const templateData = [
      {
        "Center Code": "CENTER-1", "Employee Name": "JOHN DOE", "Gender": "Male",
        "Designation": "Chef", "Base Salary": 15000, "Current Salary": 18000,
        "Date of Joining": "2024-01-15", "Bank Name": "HDFC Bank",
        "Account Number": "1234567890", "IFSC Code": "HDFC0001234",
        "Mobile": "9876543210", "Email": "john@email.com", "Remarks": "Full time"
      },
    ];
    const ws = XLSX.utils.json_to_sheet(templateData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Employees");
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
        toast.error("Failed to parse Excel file.");
      }
    };
    reader.readAsBinaryString(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // Submit bulk upload
  const submitBulkUpload = async () => {
    if (uploadData.length === 0) { toast.error("No data to upload."); return; }
    if (!window.confirm(`Upload ${uploadData.length} employees?`)) return;
    setUploadLoading(true);
    try {
      const res = await api.post("/mgt_employee_bulk_upload", { token: session.token, employees: uploadData });
      setUploadResult(res.data);
      toast.success(res.data.message);
      loadEmployees();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Bulk upload failed");
    } finally {
      setUploadLoading(false);
    }
  };

  const clearBulkUpload = () => {
    setUploadData([]);
    setUploadResult(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  // Doc upload button helper
  const DocUploadBtn = ({ docType, label, hasUrl }) => (
    <div className="flex items-center gap-2">
      <div className="relative">
        <input
          type="file"
          accept="image/*,.pdf"
          ref={el => docInputRefs.current[docType] = el}
          onChange={(e) => handleDocUpload(docType, e)}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          data-testid={`upload-${docType}`}
        />
        <Button
          variant="outline" size="sm" type="button"
          disabled={docUploading[docType] || !formData.name || !formData.center}
          className="text-xs h-7"
        >
          {docUploading[docType] ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Paperclip className="w-3 h-3 mr-1" />}
          {label}
        </Button>
      </div>
      {hasUrl && <Badge variant="outline" className="text-green-600 text-xs h-5">Uploaded</Badge>}
    </div>
  );

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
          <h1 className="text-3xl font-bold text-primary" data-testid="employee-page-title">Employee Management</h1>
          <p className="text-muted-foreground mt-1">
            {employees.length} employees
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={exportEmployeeReport}
            disabled={reportLoading}
            variant="outline"
            className="border-purple-500 text-purple-600 hover:bg-purple-50"
            data-testid="export-report-btn"
          >
            {reportLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileText className="w-4 h-4 mr-2" />}
            Employee Report
          </Button>
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
                <CardDescription>Upload multiple employees at once using Excel file</CardDescription>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setShowBulkUpload(false)}>
                <X className="w-4 h-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm">
              <h4 className="font-semibold text-blue-800 dark:text-blue-300 mb-2">Instructions:</h4>
              <ol className="list-decimal list-inside space-y-1 text-blue-700 dark:text-blue-400">
                <li>Download the Excel template</li>
                <li>Fill in employee data (Center Code and Name are required)</li>
                <li>Upload the filled Excel file</li>
                <li>Review the preview and click "Upload All"</li>
              </ol>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button onClick={downloadTemplate} variant="outline" className="border-green-500 text-green-600 hover:bg-green-50">
                <Download className="w-4 h-4 mr-2" /> Download Template
              </Button>
              <div className="relative">
                <input ref={fileInputRef} type="file" accept=".xlsx,.xls" onChange={handleFileUpload}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                <Button variant="outline" className="border-blue-500 text-blue-600 hover:bg-blue-50">
                  <Upload className="w-4 h-4 mr-2" /> Select Excel File
                </Button>
              </div>
              {uploadData.length > 0 && (
                <>
                  <Button onClick={submitBulkUpload} disabled={uploadLoading} className="bg-green-600 hover:bg-green-700">
                    {uploadLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle className="w-4 h-4 mr-2" />}
                    Upload {uploadData.length} Employees
                  </Button>
                  <Button onClick={clearBulkUpload} variant="ghost" className="text-red-500">
                    <X className="w-4 h-4 mr-2" /> Clear
                  </Button>
                </>
              )}
            </div>
            {uploadResult && (
              <div className={`p-4 rounded-lg ${uploadResult.errors?.length > 0 ? 'bg-amber-50 border border-amber-200' : 'bg-green-50 border border-green-200'}`}>
                <div className="flex items-center gap-2 mb-2">
                  {uploadResult.errors?.length > 0 ? <AlertCircle className="w-5 h-5 text-amber-600" /> : <CheckCircle className="w-5 h-5 text-green-600" />}
                  <span className="font-semibold">{uploadResult.message}</span>
                </div>
                <div className="flex gap-4 text-sm">
                  <span className="text-green-600">Created: {uploadResult.created}</span>
                  <span className="text-blue-600">Updated: {uploadResult.updated}</span>
                  {uploadResult.errors?.length > 0 && <span className="text-red-600">Errors: {uploadResult.errors.length}</span>}
                </div>
                {uploadResult.errors?.length > 0 && (
                  <div className="mt-2 text-sm text-red-600">
                    {uploadResult.errors.map((err, i) => <div key={i}>{err}</div>)}
                  </div>
                )}
              </div>
            )}
            {uploadData.length > 0 && !uploadResult && (
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-muted px-4 py-2 font-semibold">Preview: {uploadData.length} employees</div>
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
                          <td className="px-3 py-2"><Badge variant="outline">{emp.center}</Badge></td>
                          <td className="px-3 py-2 font-medium">{emp.name}</td>
                          <td className="px-3 py-2">{emp.designation}</td>
                          <td className="px-3 py-2 text-right">{emp.currentSalary || emp.salaryBase || 0}</td>
                          <td className="px-3 py-2">{emp.mobile}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Edit/Add Card */}
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
                <X className="w-4 h-4 mr-1" /> Clear
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Basic Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input value={formData.name} onChange={(e) => updateField("name", e.target.value)}
                placeholder="EMPLOYEE NAME" className="uppercase" data-testid="emp-name" />
            </div>
            <div className="space-y-2">
              <Label>Center *</Label>
              <select value={formData.center} onChange={(e) => updateField("center", e.target.value)}
                className="w-full h-10 px-3 rounded-md border border-input bg-background" data-testid="emp-center">
                {centersList.map(c => <option key={c.code} value={c.code}>{c.code}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Designation</Label>
              <Input value={formData.designation} onChange={(e) => updateField("designation", e.target.value)}
                placeholder="e.g. MANAGER, CHEF" />
            </div>
            <div className="space-y-2">
              <Label>Gender</Label>
              <select value={formData.gender} onChange={(e) => updateField("gender", e.target.value)}
                className="w-full h-10 px-3 rounded-md border border-input bg-background">
                <option value="">Select</option>
                <option value="MALE">MALE</option>
                <option value="FEMALE">FEMALE</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>Current Salary</Label>
              <Input type="number" value={formData.currentSalary}
                onChange={(e) => updateField("currentSalary", e.target.value)} placeholder="45000" />
            </div>
            <div className="space-y-2">
              <Label>Base Salary</Label>
              <Input type="number" value={formData.salaryBase}
                onChange={(e) => updateField("salaryBase", e.target.value)} placeholder="40000" />
            </div>
            <div className="space-y-2">
              <Label>Bank Name</Label>
              <Input value={formData.bankName} onChange={(e) => updateField("bankName", e.target.value)}
                placeholder="HDFC, ICICI, SBI" />
            </div>
            <div className="space-y-2">
              <Label>Account No</Label>
              <Input value={formData.beneAccNo} onChange={(e) => updateField("beneAccNo", e.target.value)}
                placeholder="50100291509491" />
            </div>
            <div className="space-y-2">
              <Label>IFSC Code</Label>
              <Input value={formData.ifsc} onChange={(e) => updateField("ifsc", e.target.value)}
                placeholder="HDFC0004220" />
            </div>
            <div className="space-y-2">
              <Label>Mobile</Label>
              <Input value={formData.mobile} onChange={(e) => updateField("mobile", e.target.value)}
                placeholder="9876543210" />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input type="email" value={formData.email}
                onChange={(e) => updateField("email", e.target.value)} placeholder="email@example.com" />
            </div>
            <div className="space-y-2">
              <Label>Date of Joining</Label>
              <Input type="date" value={formData.dateOfJoining}
                onChange={(e) => updateField("dateOfJoining", e.target.value)} />
            </div>
          </div>

          {/* KYC / Document Fields */}
          <div className="border-t pt-4">
            <h3 className="text-sm font-semibold text-muted-foreground mb-3 flex items-center gap-2">
              <FileText className="w-4 h-4" /> KYC & Document Details
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label>Aadhaar Number</Label>
                <Input value={formData.aadhaar} onChange={(e) => updateField("aadhaar", e.target.value)}
                  placeholder="1234 5678 9012" data-testid="emp-aadhaar" />
                <DocUploadBtn docType="aadhaar_doc" label="Attach Aadhaar"
                  hasUrl={selectedEmp?.aadhaar_doc_url} />
              </div>
              <div className="space-y-2">
                <Label>PAN / TFN</Label>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Input value={formData.pan} onChange={(e) => updateField("pan", e.target.value)}
                      placeholder="PAN" data-testid="emp-pan" className="text-xs" />
                  </div>
                  <div>
                    <Input value={formData.tfn} onChange={(e) => updateField("tfn", e.target.value)}
                      placeholder="TFN" data-testid="emp-tfn" className="text-xs" />
                  </div>
                </div>
                <DocUploadBtn docType="pan_doc" label="Attach PAN/TFN"
                  hasUrl={selectedEmp?.pan_doc_url} />
              </div>
              <div className="space-y-2">
                <Label>Passport Number</Label>
                <Input value={formData.passport_number}
                  onChange={(e) => updateField("passport_number", e.target.value)}
                  placeholder="A1234567" data-testid="emp-passport" />
                <DocUploadBtn docType="passport_doc" label="Attach Passport"
                  hasUrl={selectedEmp?.passport_doc_url} />
              </div>
              <div className="space-y-2">
                <Label>Visa Type</Label>
                <select value={formData.visa_type}
                  onChange={(e) => updateField("visa_type", e.target.value)}
                  className="w-full h-10 px-3 rounded-md border border-input bg-background"
                  data-testid="emp-visa-type">
                  {VISA_TYPES.map(v => <option key={v} value={v}>{v || "Select"}</option>)}
                </select>
                <DocUploadBtn docType="visa_doc" label="Attach Visa"
                  hasUrl={selectedEmp?.visa_doc_url} />
              </div>
              <div className="space-y-2">
                <Label>Blood Group (Optional)</Label>
                <select value={formData.blood_group}
                  onChange={(e) => updateField("blood_group", e.target.value)}
                  className="w-full h-10 px-3 rounded-md border border-input bg-background"
                  data-testid="emp-blood-group">
                  {BLOOD_GROUPS.map(b => <option key={b} value={b}>{b || "Select"}</option>)}
                </select>
              </div>
              <div className="space-y-2">
                <Label>Passport Photo</Label>
                <div className="flex items-center gap-3">
                  {formData.photo_url ? (
                    <img src={formData.photo_url} alt="Employee" className="w-12 h-14 object-cover rounded border" />
                  ) : (
                    <div className="w-12 h-14 rounded border bg-muted flex items-center justify-center">
                      <Camera className="w-5 h-5 text-muted-foreground" />
                    </div>
                  )}
                  <div className="relative">
                    <input type="file" accept="image/*" ref={photoInputRef}
                      onChange={handlePhotoUpload}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                      data-testid="upload-photo" />
                    <Button variant="outline" size="sm" type="button"
                      disabled={photoUploading || !formData.name || !formData.center}>
                      {photoUploading ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Camera className="w-3 h-3 mr-1" />}
                      Upload Photo
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Notes/Remark field */}
          <div className="space-y-2">
            <Label>Notes / Remark (for fund transfer)</Label>
            <Textarea value={formData.remark} onChange={(e) => updateField("remark", e.target.value)}
              placeholder="Add notes for account fund transfer or other remarks..." rows={2} data-testid="emp-remark" />
          </div>

          {/* Action buttons */}
          <div className="flex gap-3 pt-2">
            {editMode ? (
              <>
                <Button onClick={updateEmployee} disabled={loading} data-testid="update-emp-btn">
                  {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  <Save className="w-4 h-4 mr-2" /> Update Employee
                </Button>
                <Button variant="destructive" onClick={deleteEmployee} disabled={loading}>
                  <Trash2 className="w-4 h-4 mr-2" /> Delete
                </Button>
              </>
            ) : (
              <Button onClick={createEmployee} disabled={loading} data-testid="add-emp-btn">
                {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                <Plus className="w-4 h-4 mr-2" /> Add Employee
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
              <select value={centerFilter} onChange={(e) => setCenterFilter(e.target.value)}
                className="h-10 px-3 rounded-md border border-input bg-background text-sm" data-testid="center-filter">
                <option value="">All Centers</option>
                {centersList.map(c => <option key={c.code} value={c.code}>{c.code}</option>)}
              </select>
              <div className="relative w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input placeholder="Search..." value={search} onChange={(e) => setSearch(e.target.value)}
                  className="pl-9" data-testid="emp-search" />
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
                      <th className="p-3 text-center w-12">Photo</th>
                      <th className="text-left p-3 font-bold">Center</th>
                      <th className="text-left p-3 font-bold">Name</th>
                      <th className="text-left p-3 font-bold">Designation</th>
                      <th className="text-left p-3 font-bold">Salary</th>
                      <th className="text-left p-3 font-bold">Blood</th>
                      <th className="text-left p-3 font-bold">Mobile</th>
                      <th className="text-left p-3 font-bold">Docs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredEmployees.map((emp, idx) => (
                      <tr key={idx}
                        className={`border-t hover:bg-muted/30 cursor-pointer ${selectedEmp?.name === emp.name ? 'bg-primary/10' : ''}`}
                        onClick={() => selectEmployee(emp)} data-testid={`emp-row-${idx}`}>
                        <td className="p-3 text-center">
                          <Checkbox checked={selectedEmp?.name === emp.name}
                            onCheckedChange={() => selectEmployee(emp)}
                            onClick={(e) => e.stopPropagation()} />
                        </td>
                        <td className="p-3 text-center">
                          {emp.photo_url ? (
                            <img src={emp.photo_url} alt="" className="w-8 h-10 object-cover rounded border mx-auto" />
                          ) : (
                            <div className="w-8 h-10 rounded border bg-muted flex items-center justify-center mx-auto">
                              <Camera className="w-3 h-3 text-muted-foreground" />
                            </div>
                          )}
                        </td>
                        <td className="p-3"><Badge variant="outline">{emp.center}</Badge></td>
                        <td className="p-3 font-semibold">{emp.name}</td>
                        <td className="p-3 text-muted-foreground">{emp.designation}</td>
                        <td className="p-3">{emp.currentSalary ? `${emp.currentSalary.toLocaleString()}` : '-'}</td>
                        <td className="p-3">
                          {emp.blood_group ? <Badge variant="outline" className="text-red-600 border-red-300">{emp.blood_group}</Badge> : '-'}
                        </td>
                        <td className="p-3 font-mono text-xs">{emp.mobile}</td>
                        <td className="p-3">
                          <div className="flex gap-1 flex-wrap">
                            {emp.aadhaar && <Badge variant="secondary" className="text-[10px] h-4">ADH</Badge>}
                            {emp.pan && <Badge variant="secondary" className="text-[10px] h-4">PAN</Badge>}
                            {emp.tfn && <Badge variant="secondary" className="text-[10px] h-4">TFN</Badge>}
                            {emp.passport_number && <Badge variant="secondary" className="text-[10px] h-4">PP</Badge>}
                            {!emp.aadhaar && !emp.pan && !emp.tfn && !emp.passport_number && '-'}
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
