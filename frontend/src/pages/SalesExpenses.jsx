import { useState, useEffect } from "react";
import { useAuth } from "@/App";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { 
  IndianRupee, 
  TrendingUp, 
  CreditCard, 
  Wallet, 
  Receipt,
  Calendar,
  Building2,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  Filter,
  Download,
  RefreshCw,
  PieChart,
  Users,
  FileText,
  DollarSign,
  Lock,
  Unlock,
  Clock,
  CheckCircle,
  XCircle,
  Shield,
  Table2,
  Upload,
  Settings,
  AlertTriangle,
  ArrowRightLeft,
  Calculator
} from "lucide-react";
import { api, API_URL, fetchCentersFromDB } from "@/lib/api";
import SalesDataEntry from "@/components/SalesDataEntry";
import ExpenseEntry from "@/components/ExpenseEntry";
import FreezeControl from "@/components/FreezeControl";
import SalesGridEditor from "@/components/SalesGridEditor";
import BankReconciliation from "@/components/BankReconciliation";
import * as XLSX from "xlsx";

// Check if center is international (non-India) — replaces hardcoded PB-PERTH check
const isInternational = (center, centersList = []) => {
  if (!center) return false;
  const c = center.toUpperCase();
  const centerData = centersList.find(cd => cd.code === c);
  if (centerData) return centerData.is_india_center === false;
  return false;
};

// Get currency symbol based on center data
const getCurrencySymbol = (center, centersList = []) => isInternational(center, centersList) ? "$" : "₹";

// Format currency with dynamic symbol - can accept center code OR currency symbol directly
const formatCurrency = (amount, centerOrCurrency = null) => {
  let symbol = "₹";
  if (centerOrCurrency) {
    // If it's already a symbol ($ or ₹), use it directly
    if (centerOrCurrency === "$" || centerOrCurrency === "₹") {
      symbol = centerOrCurrency;
    } else {
      // Otherwise it's a center code, get the symbol
      symbol = getCurrencySymbol(centerOrCurrency);
    }
  }
  
  if (amount === null || amount === undefined || isNaN(amount)) return `${symbol}0`;
  
  return `${symbol}${new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount)}`;
};

// Format date for display
const formatDateDisplay = (dateStr) => {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
};

// Get current month in YYYY-MM format
const getCurrentMonthStr = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
};

// Get today's date in YYYY-MM-DD format
const getTodayStr = () => {
  const now = new Date();
  return now.toISOString().split('T')[0];
};

// Check if a date is frozen (previous day or older)
const isDateFrozen = (dateStr) => {
  if (!dateStr) return true;
  const recordDate = new Date(dateStr);
  recordDate.setHours(0, 0, 0, 0);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return recordDate < today;
};

// =======================================
// SALES UPLOAD TAB COMPONENT
// =======================================
function SalesUploadTab({ session, selectedCenter, onUploadComplete }) {
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadCenter, setUploadCenter] = useState(selectedCenter !== "all" ? selectedCenter : "");
  const [uploadResult, setUploadResult] = useState(null);
  const [showConfirm, setShowConfirm] = useState(false);
  
  // Custom format states
  const [uploadMode, setUploadMode] = useState("template"); // "template" or "custom"
  const [fromYear, setFromYear] = useState(new Date().getFullYear() - 1);
  const [customFile, setCustomFile] = useState(null);
  const [customUploading, setCustomUploading] = useState(false);
  const [customResult, setCustomResult] = useState(null);
  const [showCustomConfirm, setShowCustomConfirm] = useState(false);

  const userCenter = session?.center || "";
  const isSuperAdmin = session?.is_super_admin;
  const canSelectCenter = isSuperAdmin || session?.is_admin;

  // Download template
  const handleDownloadTemplate = async () => {
    if (!session?.token) {
      toast.error("Please login again to download template");
      return;
    }
    
    try {
      toast.loading("Downloading template...", { id: "download-template" });
      
      const res = await fetch(`${API_URL}/sales/upload-template?token=${session.token}`);
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Download failed");
      }
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'Sales_Upload_Template.xlsx';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success("Template downloaded", { id: "download-template" });
    } catch (err) {
      toast.error(err.message || "Failed to download template", { id: "download-template" });
    }
  };

  // Handle file selection
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
        toast.error("Please select an Excel file (.xlsx or .xls)");
        return;
      }
      setSelectedFile(file);
      setUploadResult(null);
    }
  };

  // Confirm and upload
  const handleUpload = async () => {
    const targetCenter = canSelectCenter ? uploadCenter : userCenter;
    
    if (!targetCenter) {
      toast.error("Please select a center");
      return;
    }
    
    if (!selectedFile) {
      toast.error("Please select a file");
      return;
    }

    setShowConfirm(false);
    setUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('token', session?.token);
      formData.append('center', targetCenter);
      formData.append('file', selectedFile);
      
      const res = await fetch(`${API_URL}/sales/upload-data`, {
        method: 'POST',
        body: formData
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }
      
      setUploadResult(data);
      toast.success(data.message);
      setSelectedFile(null);
      
      // Refresh data
      if (onUploadComplete) onUploadComplete();
      
    } catch (err) {
      toast.error(err.message);
    } finally {
      setUploading(false);
    }
  };

  // Handle custom format file selection
  const handleCustomFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
        toast.error("Please select an Excel file (.xlsx or .xls)");
        return;
      }
      setCustomFile(file);
      setCustomResult(null);
    }
  };

  // Handle custom format upload
  const handleCustomUpload = async () => {
    const targetCenter = canSelectCenter ? uploadCenter : userCenter;
    
    if (!targetCenter) {
      toast.error("Please select a center");
      return;
    }
    
    if (!customFile) {
      toast.error("Please select a file");
      return;
    }

    if (!fromYear || fromYear < 2015 || fromYear > 2030) {
      toast.error("Please enter a valid year (2015-2030)");
      return;
    }

    setShowCustomConfirm(false);
    setCustomUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('token', session?.token);
      formData.append('center', targetCenter);
      formData.append('from_year', fromYear.toString());
      formData.append('file', customFile);
      
      const res = await fetch(`${API_URL}/sales/upload-custom-format`, {
        method: 'POST',
        body: formData
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }
      
      setCustomResult(data);
      toast.success(data.message);
      setCustomFile(null);
      
      if (onUploadComplete) onUploadComplete();
      
    } catch (err) {
      toast.error(err.message);
    } finally {
      setCustomUploading(false);
    }
  };

  return (
    <Card className="bg-card border-border">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="w-5 h-5 text-green-500" />
          Upload Sales & Expenses Data
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Upload Mode Tabs */}
        <div className="flex gap-2 p-1 bg-muted rounded-lg w-fit">
          <button
            onClick={() => setUploadMode("template")}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              uploadMode === "template" 
                ? "bg-primary text-primary-foreground" 
                : "hover:bg-muted-foreground/10"
            }`}
          >
            Template Format
          </button>
          <button
            onClick={() => setUploadMode("custom")}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              uploadMode === "custom" 
                ? "bg-primary text-primary-foreground" 
                : "hover:bg-muted-foreground/10"
            }`}
          >
            Custom Format (Bulk Import)
          </button>
        </div>

        {uploadMode === "template" ? (
          <>
            {/* Instructions */}
            <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
              <h3 className="font-semibold text-blue-400 mb-2">How to Upload (Template):</h3>
              <ol className="list-decimal list-inside space-y-1 text-sm text-muted-foreground">
                <li>Download the Excel template using the button below</li>
                <li>Fill in your sales and expense data (Sheet 1: Sales, Sheet 2: Expenses)</li>
                <li>Select your center and upload the file</li>
                <li className="text-amber-400 font-medium">Warning: Existing data for uploaded dates will be REPLACED</li>
              </ol>
            </div>

            {/* Download Template */}
            <div>
              <Button onClick={handleDownloadTemplate} variant="outline" className="gap-2">
                <Download className="w-4 h-4" />
                Download Template
              </Button>
            </div>

            {/* Center Selection */}
            <div className="space-y-2">
              <Label>Center *</Label>
              {canSelectCenter ? (
                <Input
                  value={uploadCenter}
                  onChange={(e) => setUploadCenter(e.target.value.toUpperCase())}
                  placeholder="Enter center code"
                  className="max-w-xs"
                />
              ) : (
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-muted-foreground" />
                  <span className="font-medium">{userCenter}</span>
                  <span className="text-xs text-muted-foreground">(Your center)</span>
                </div>
              )}
            </div>

            {/* File Upload */}
            <div className="space-y-2">
              <Label>Excel File *</Label>
              <Input
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileSelect}
                className="max-w-md"
              />
              {selectedFile && (
                <p className="text-sm text-green-500">Selected: {selectedFile.name}</p>
              )}
            </div>

            {/* Upload Button */}
            <div className="flex gap-3">
              <Button 
                onClick={() => setShowConfirm(true)} 
                disabled={!selectedFile || uploading || (!canSelectCenter && !userCenter)}
                className="bg-green-600 hover:bg-green-700"
              >
                {uploading ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" />
                    Upload Data
                  </>
                )}
              </Button>
            </div>

            {/* Upload Result */}
            {uploadResult && (
              <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg space-y-2">
                <h3 className="font-semibold text-green-400 flex items-center gap-2">
                  <CheckCircle className="w-5 h-5" />
                  Upload Complete
                </h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="font-medium">Sales Data:</p>
                    <p>Imported: {uploadResult.results?.sales?.imported || 0} records</p>
                    <p>Deleted: {uploadResult.results?.sales?.deleted || 0} records</p>
                  </div>
                  <div>
                    <p className="font-medium">Expenses:</p>
                    <p>Imported: {uploadResult.results?.expenses?.imported || 0} records</p>
                    <p>Deleted: {uploadResult.results?.expenses?.deleted || 0} records</p>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            {/* Custom Format Instructions */}
            <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
              <h3 className="font-semibold text-amber-400 mb-2">Bulk Import from Custom Format:</h3>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li>Upload your existing Excel file with monthly sheets (e.g., "FEB 26", "JAN 25", "MAR 2024")</li>
                <li>System auto-detects columns: DATE, OPENING BALANCE, CASH RECEIPTS, TOTAL SALE, CARD/IDFC/EFTPOS, BHARAT PAY/UPI, SWIGGY, ZOMATO, DOORDASH, ONLINE/PICKUP</li>
                <li>Select the year from which you want to import data</li>
                <li className="text-amber-400 font-medium">Warning: Existing data for imported dates will be REPLACED</li>
              </ul>
            </div>

            {/* Center Selection */}
            <div className="space-y-2">
              <Label>Center *</Label>
              {canSelectCenter ? (
                <Input
                  value={uploadCenter}
                  onChange={(e) => setUploadCenter(e.target.value.toUpperCase())}
                  placeholder="Enter center code"
                  className="max-w-xs"
                />
              ) : (
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-muted-foreground" />
                  <span className="font-medium">{userCenter}</span>
                  <span className="text-xs text-muted-foreground">(Your center)</span>
                </div>
              )}
            </div>

            {/* Year Filter */}
            <div className="space-y-2">
              <Label>Import data from year *</Label>
              <Input
                type="number"
                min="2015"
                max="2030"
                value={fromYear}
                onChange={(e) => setFromYear(parseInt(e.target.value) || 2024)}
                placeholder="e.g., 2023"
                className="max-w-xs"
              />
              <p className="text-xs text-muted-foreground">
                Only data from {fromYear} onwards will be imported
              </p>
            </div>

            {/* File Upload */}
            <div className="space-y-2">
              <Label>Excel File (Custom Format) *</Label>
              <Input
                type="file"
                accept=".xlsx,.xls"
                onChange={handleCustomFileSelect}
                className="max-w-md"
              />
              {customFile && (
                <p className="text-sm text-green-500">Selected: {customFile.name}</p>
              )}
            </div>

            {/* Upload Button */}
            <div className="flex gap-3">
              <Button 
                onClick={() => setShowCustomConfirm(true)} 
                disabled={!customFile || customUploading || (!canSelectCenter && !userCenter)}
                className="bg-amber-600 hover:bg-amber-700"
              >
                {customUploading ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" />
                    Import Data
                  </>
                )}
              </Button>
            </div>

            {/* Custom Upload Result */}
            {customResult && (
              <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg space-y-2">
                <h3 className="font-semibold text-green-400 flex items-center gap-2">
                  <CheckCircle className="w-5 h-5" />
                  Import Complete
                </h3>
                <div className="text-sm space-y-2">
                  <p><strong>Sales Records Imported:</strong> {customResult.results?.sales?.imported || 0}</p>
                  <p><strong>Existing Records Replaced:</strong> {customResult.results?.sales?.deleted || 0}</p>
                  {customResult.sheets_processed?.length > 0 && (
                    <div>
                      <p className="font-medium">Sheets Processed:</p>
                      <p className="text-muted-foreground">{customResult.sheets_processed.join(", ")}</p>
                    </div>
                  )}
                  {customResult.results?.sales?.errors?.length > 0 && (
                    <div className="mt-2 p-2 bg-red-500/10 rounded text-xs text-red-400">
                      <p className="font-medium">Errors:</p>
                      {customResult.results.sales.errors.slice(0, 5).map((err, i) => (
                        <p key={i}>{err}</p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {/* Confirmation Dialog for Template Upload */}
        {showConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-card border border-border rounded-lg p-6 max-w-md m-4">
              <div className="flex items-start gap-3 mb-4">
                <AlertTriangle className="w-6 h-6 text-amber-500 flex-shrink-0" />
                <div>
                  <h3 className="font-semibold text-lg">Confirm Data Upload</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    This will <strong className="text-red-500">DELETE</strong> existing sales and expense data 
                    for the dates in your Excel file and replace them with new data.
                  </p>
                </div>
              </div>
              <div className="bg-amber-500/10 p-3 rounded mb-4 text-sm">
                <p><strong>Center:</strong> {canSelectCenter ? uploadCenter : userCenter}</p>
                <p><strong>File:</strong> {selectedFile?.name}</p>
              </div>
              <div className="flex justify-end gap-3">
                <Button variant="outline" onClick={() => setShowConfirm(false)}>
                  Cancel
                </Button>
                <Button onClick={handleUpload} className="bg-red-600 hover:bg-red-700">
                  Yes, Replace Data
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Confirmation Dialog for Custom Format Upload */}
        {showCustomConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-card border border-border rounded-lg p-6 max-w-md m-4">
              <div className="flex items-start gap-3 mb-4">
                <AlertTriangle className="w-6 h-6 text-amber-500 flex-shrink-0" />
                <div>
                  <h3 className="font-semibold text-lg">Confirm Bulk Import</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    This will import sales data from all monthly sheets (from {fromYear} onwards) 
                    and <strong className="text-red-500">REPLACE</strong> existing data for those dates.
                  </p>
                </div>
              </div>
              <div className="bg-amber-500/10 p-3 rounded mb-4 text-sm">
                <p><strong>Center:</strong> {canSelectCenter ? uploadCenter : userCenter}</p>
                <p><strong>From Year:</strong> {fromYear}</p>
                <p><strong>File:</strong> {customFile?.name}</p>
              </div>
              <div className="flex justify-end gap-3">
                <Button variant="outline" onClick={() => setShowCustomConfirm(false)}>
                  Cancel
                </Button>
                <Button onClick={handleCustomUpload} className="bg-amber-600 hover:bg-amber-700">
                  Yes, Import Data
                </Button>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// =======================================
// UPLOAD SETTINGS TAB (SUPER ADMIN ONLY)
// =======================================
function UploadSettingsTab({ session, centers }) {
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(false);

  // Fetch current permissions
  const fetchPermissions = async () => {
    setLoading(true);
    try {
      const res = await api.post("/sales/get-upload-permissions", {
        token: session?.token
      });
      setPermissions(res.data.centers || []);
    } catch (err) {
      toast.error("Failed to load permissions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (session?.token) {
      fetchPermissions();
    }
  }, [session?.token]);

  // Toggle permission
  const togglePermission = async (centerCode, currentEnabled) => {
    try {
      await api.post("/sales/toggle-upload-permission", {
        token: session?.token,
        center: centerCode,
        enabled: !currentEnabled
      });
      
      toast.success(`Upload ${!currentEnabled ? 'enabled' : 'disabled'} for ${centerCode}`);
      fetchPermissions();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to update permission");
    }
  };

  return (
    <Card className="bg-card border-border">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="w-5 h-5 text-amber-500" />
          Upload Permissions (MGT Control)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">
          Control which centers can upload sales data via Excel. When disabled, center managers will not see the upload option.
        </p>
        
        <div className="space-y-2">
          {loading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <RefreshCw className="w-4 h-4 animate-spin" />
              Loading...
            </div>
          ) : permissions.length === 0 ? (
            <p className="text-muted-foreground">No centers found</p>
          ) : (
            <div className="grid gap-2">
              {permissions.map((center) => (
                <div 
                  key={center.code} 
                  className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-border"
                >
                  <div>
                    <span className="font-medium">{center.code}</span>
                    <span className="text-sm text-muted-foreground ml-2">{center.name}</span>
                  </div>
                  <Button
                    size="sm"
                    variant={center.sales_upload_enabled ? "default" : "outline"}
                    className={center.sales_upload_enabled ? "bg-green-600 hover:bg-green-700" : ""}
                    onClick={() => togglePermission(center.code, center.sales_upload_enabled)}
                  >
                    {center.sales_upload_enabled ? (
                      <>
                        <CheckCircle className="w-4 h-4 mr-1" />
                        Enabled
                      </>
                    ) : (
                      <>
                        <XCircle className="w-4 h-4 mr-1" />
                        Disabled
                      </>
                    )}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="mt-4 pt-4 border-t border-border">
          <Button variant="outline" onClick={fetchPermissions} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function SalesExpenses() {
  const { session } = useAuth();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  
  // Filters - ALWAYS default to "all" centers and let backend handle access control
  const [selectedMonth, setSelectedMonth] = useState(getCurrentMonthStr());
  const [selectedCenter, setSelectedCenter] = useState("all");
  const [centers, setCenters] = useState([]);
  
  // Data
  const [monthlySummary, setMonthlySummary] = useState(null);
  const [dailyData, setDailyData] = useState([]);
  const [expenseByType, setExpenseByType] = useState({});
  const [expenses, setExpenses] = useState([]);
  
  // Unlock Request State
  const [unlockRequests, setUnlockRequests] = useState([]);
  const [showUnlockModal, setShowUnlockModal] = useState(false);
  const [selectedDateForUnlock, setSelectedDateForUnlock] = useState(null);
  const [unlockReason, setUnlockReason] = useState("");
  const [showUnlockRequestsPanel, setShowUnlockRequestsPanel] = useState(false);
  
  // Check if user has admin access - recalculate on every render
  // NEW: Accounting role also has access to ALL centers for Sales & Cash
  const hasAllCentersAccess = session?.is_super_admin === true || 
                              session?.is_admin === true ||
                              session?.roles?.view_all_centers === true ||
                              session?.roles?.accounting === true;

  // Fetch centers list
  useEffect(() => {
    const fetchCenters = async () => {
      try {
        const res = await api.get("/sales/centers-list");
        if (res.data.centers) {
          setCenters(res.data.centers);
        }
      } catch (err) {
        console.error("Failed to fetch centers:", err);
      }
    };
    fetchCenters();
  }, []);

  // Fetch monthly summary
  const fetchMonthlySummary = async () => {
    if (!selectedMonth || !session?.token) {
      console.log("Skipping fetch - no month or token", { selectedMonth, hasToken: !!session?.token });
      return;
    }
    
    setLoading(true);
    try {
      console.log("Fetching monthly summary:", { month: selectedMonth, center: selectedCenter, token: session?.token?.substring(0,10) + "..." });
      
      const res = await api.post("/sales/reports/monthly-summary", {
        token: session.token,
        month: selectedMonth,
        center: selectedCenter || "all"
      });
      
      console.log("API Response:", res.data);
      
      if (res.data) {
        setMonthlySummary(res.data.summary || res.data.grand_total || null);
        setDailyData(res.data.daily_data || []);
        setExpenseByType(res.data.expense_by_type || {});
        
        // If we got centers data (all centers view)
        if (res.data.centers) {
          setDailyData(res.data.centers);
        }
      }
    } catch (err) {
      console.error("Failed to fetch summary:", err.response?.data || err.message || err);
      toast.error(err.response?.data?.detail || "Failed to load sales data");
    } finally {
      setLoading(false);
    }
  };

  // Fetch expenses
  const fetchExpenses = async () => {
    if (!session?.token) return;
    
    setLoading(true);
    try {
      const res = await api.post("/sales/expenses", {
        token: session.token,
        month: selectedMonth,
        center: selectedCenter || "all"
      });
      
      if (res.data.expenses) {
        setExpenses(res.data.expenses);
      }
    } catch (err) {
      console.error("Failed to fetch expenses:", err);
      if (err.response?.status === 401) {
        toast.error("Session expired. Please refresh and login again.");
      } else {
        toast.error("Failed to load expenses");
      }
    } finally {
      setLoading(false);
    }
  };

  // Fetch unlock requests (for Super Admin or center manager)
  const fetchUnlockRequests = async () => {
    if (!session?.token) return;
    
    try {
      const res = await api.get(`/sales/unlock-requests?token=${session.token}&status=all`);
      if (res.data.requests) {
        setUnlockRequests(res.data.requests);
      }
    } catch (err) {
      console.error("Failed to fetch unlock requests:", err);
    }
  };

  // Submit unlock request
  const submitUnlockRequest = async () => {
    if (!session?.token) {
      toast.error("Session expired. Please refresh and login again.");
      return;
    }
    if (!selectedDateForUnlock || !unlockReason.trim()) {
      toast.error("Please provide a reason for the unlock request");
      return;
    }
    
    try {
      const res = await api.post(`/sales/unlock-request?token=${session.token}`, {
        center: selectedDateForUnlock.center || session?.center,
        date: selectedDateForUnlock.date,
        reason: unlockReason
      });
      
      if (res.data.success) {
        toast.success("Unlock request submitted successfully");
        setShowUnlockModal(false);
        setUnlockReason("");
        setSelectedDateForUnlock(null);
        fetchUnlockRequests();
      }
    } catch (err) {
      if (err.response?.status === 401) {
        toast.error("Session expired. Please refresh and login again.");
      } else {
        toast.error(err.response?.data?.detail || "Failed to submit unlock request");
      }
    }
  };

  // Process unlock request (Super Admin)
  const processUnlockRequest = async (requestId, action) => {
    if (!session?.token) {
      toast.error("Session expired. Please refresh and login again.");
      return;
    }
    
    try {
      const res = await api.post(`/sales/unlock-request/${requestId}/action?token=${session.token}`, {
        action: action
      });
      
      if (res.data.success) {
        toast.success(`Request ${action}d successfully`);
        fetchUnlockRequests();
      }
    } catch (err) {
      if (err.response?.status === 401) {
        toast.error("Session expired. Please refresh and login again.");
      } else {
        toast.error(err.response?.data?.detail || `Failed to ${action} request`);
      }
    }
  };

  useEffect(() => {
    if (session?.token) {
      fetchMonthlySummary();
      fetchExpenses();
      fetchUnlockRequests();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMonth, selectedCenter, session?.token]);

  // Note: Removed the retry useEffect that was causing flickering
  // The API interceptor already handles retries for failed requests

  // Recalculate opening/closing balances for the selected center and month
  const [recalculating, setRecalculating] = useState(false);
  const recalculateBalances = async () => {
    if (!session?.token || !selectedMonth) return;
    const center = (selectedCenter && selectedCenter !== "all") ? selectedCenter : session?.center;
    if (!center) {
      toast.error("Please select a specific center to recalculate");
      return;
    }
    setRecalculating(true);
    try {
      const res = await api.post("/sales/daily/recalculate", {
        token: session.token,
        center,
        month: selectedMonth
      });
      if (res.data.success) {
        toast.success(res.data.message);
        fetchMonthlySummary();
      } else {
        toast.error("Recalculation failed");
      }
    } catch (err) {
      console.error("Recalculate error:", err);
      toast.error("Failed to recalculate balances");
    } finally {
      setRecalculating(false);
    }
  };

  // Download Monthly Excel Report
  const downloadMonthlyExcel = async () => {
    if (!session?.token) {
      toast.error("Please login to download");
      return;
    }

    setLoading(true);
    toast.info("Preparing Excel download...");

    try {
      // Fetch daily sales data
      const salesRes = await api.post("/sales/daily", {
        token: session.token,
        month: selectedMonth,
        center: selectedCenter
      });

      // Fetch expenses data
      const [year, month] = selectedMonth.split("-");
      const startDate = `${selectedMonth}-01`;
      const lastDay = new Date(parseInt(year), parseInt(month), 0).getDate();
      const endDate = `${selectedMonth}-${lastDay}`;
      
      const expenseRes = await api.post("/sales/expenses", {
        token: session.token,
        center: selectedCenter,
        start_date: startDate,
        end_date: endDate
      });

      const salesData = salesRes.data.sales || [];
      const expensesData = expenseRes.data.expenses || [];

      if (salesData.length === 0 && expensesData.length === 0) {
        toast.error("No data found for selected period");
        setLoading(false);
        return;
      }

      // Create workbook
      const wb = XLSX.utils.book_new();

      // Get center name for filename
      const centerName = selectedCenter === "all" ? "All_Centers" : selectedCenter;
      const monthName = new Date(`${selectedMonth}-01`).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

      // Sheet 1: Day-wise Sales Data
      const salesSheetData = salesData.map(s => ({
        "Date": s.date,
        "Center": s.center,
        "Sale PBM": s.sale_pbm || 0,
        "Sale Other": s.sale_other || 0,
        "Total Sale": s.total_sale || 0,
        "Card/IDFC": s.card_idfc || 0,
        "Bharat Pay": s.bharat_pay || 0,
        "Swiggy": s.swiggy || 0,
        "Zomato": s.zomato || 0,
        "Online Other": s.online_other || 0,
        "Total Online": s.total_online_sale || 0,
        "Total Cash Sale": s.total_cash_sale || 0,
        "Opening Balance": s.opening_balance || 0,
        "Cash Receipts": s.cash_receipts || 0,
        "Deposited in Bank": s.deposited_in_bank || 0,
        "Cash Expense": s.cash_expense || 0,
        "Closing Balance": s.closing_balance || 0,
        "Petty Cash Opening": s.petty_cash_opening || 0,
        "Petty Cash Closing": s.petty_cash_closing || 0,
        "No. of Guests": s.num_guests || 0,
        "No. of Bills": s.num_bills || 0
      }));

      const salesWs = XLSX.utils.json_to_sheet(salesSheetData);
      
      // Set column widths for sales sheet
      salesWs['!cols'] = [
        { wch: 12 }, { wch: 10 }, { wch: 12 }, { wch: 12 }, { wch: 12 },
        { wch: 12 }, { wch: 12 }, { wch: 10 }, { wch: 10 }, { wch: 12 },
        { wch: 12 }, { wch: 14 }, { wch: 14 }, { wch: 12 }, { wch: 15 },
        { wch: 12 }, { wch: 14 }, { wch: 14 }, { wch: 14 }, { wch: 12 }, { wch: 12 }
      ];
      
      XLSX.utils.book_append_sheet(wb, salesWs, "Daily Sales");

      // Sheet 2: Day-wise Expense Details
      const expenseSheetData = expensesData.map(e => ({
        "Date": e.date,
        "Center": e.center,
        "Description": e.description || "",
        "Expense Type": e.expense_type || "",
        "Payment Mode": e.payment_mode || "",
        "Amount": e.amount || 0
      }));

      const expenseWs = XLSX.utils.json_to_sheet(expenseSheetData);
      expenseWs['!cols'] = [
        { wch: 12 }, { wch: 10 }, { wch: 30 }, { wch: 20 }, { wch: 15 }, { wch: 12 }
      ];
      XLSX.utils.book_append_sheet(wb, expenseWs, "Expense Details");

      // Sheet 3: Expense Summary by Type
      const expenseSummary = {};
      expensesData.forEach(e => {
        const type = e.expense_type || "Unknown";
        expenseSummary[type] = (expenseSummary[type] || 0) + (e.amount || 0);
      });

      const summarySheetData = Object.entries(expenseSummary).map(([type, amount]) => ({
        "Expense Type": type,
        "Total Amount": amount
      })).sort((a, b) => b["Total Amount"] - a["Total Amount"]);

      // Add total row
      const totalExpense = Object.values(expenseSummary).reduce((sum, v) => sum + v, 0);
      summarySheetData.push({
        "Expense Type": "TOTAL",
        "Total Amount": totalExpense
      });

      const summaryWs = XLSX.utils.json_to_sheet(summarySheetData);
      summaryWs['!cols'] = [{ wch: 25 }, { wch: 15 }];
      XLSX.utils.book_append_sheet(wb, summaryWs, "Expense Summary");

      // Sheet 4: Monthly Totals (if All Centers)
      if (selectedCenter === "all") {
        const centerTotals = {};
        salesData.forEach(s => {
          const center = s.center;
          if (!centerTotals[center]) {
            centerTotals[center] = {
              total_sale: 0,
              cash_sale: 0,
              online_sale: 0,
              cash_expense: 0,
              days: 0
            };
          }
          centerTotals[center].total_sale += s.total_sale || 0;
          centerTotals[center].cash_sale += s.total_cash_sale || 0;
          centerTotals[center].online_sale += s.total_online_sale || 0;
          centerTotals[center].cash_expense += s.cash_expense || 0;
          centerTotals[center].days += 1;
        });

        const centerSummaryData = Object.entries(centerTotals).map(([center, data]) => ({
          "Center": center,
          "Total Sales": data.total_sale,
          "Cash Sales": data.cash_sale,
          "Online Sales": data.online_sale,
          "Cash Expenses": data.cash_expense,
          "Days with Data": data.days
        }));

        const centerWs = XLSX.utils.json_to_sheet(centerSummaryData);
        centerWs['!cols'] = [
          { wch: 12 }, { wch: 14 }, { wch: 14 }, { wch: 14 }, { wch: 14 }, { wch: 14 }
        ];
        XLSX.utils.book_append_sheet(wb, centerWs, "Center Summary");
      }

      // Download the file
      const filename = `PB_${centerName}_${selectedMonth}.xlsx`;
      XLSX.writeFile(wb, filename);
      
      toast.success(`Downloaded: ${filename}`);
    } catch (err) {
      console.error("Excel download error:", err);
      toast.error("Failed to download Excel. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Get currency from API response or fallback to center-based logic
  // For non-admin users, use their session center to determine currency
  const effectiveCenter = selectedCenter !== "all" ? selectedCenter : session?.center;
  const currentCurrency = monthlySummary?.currency || getCurrencySymbol(effectiveCenter, centers);

  // Summary cards data
  const summaryCards = [
    {
      title: "Total Sales",
      value: formatCurrency(monthlySummary?.total_sale, currentCurrency),
      icon: IndianRupee,
      color: "text-green-500",
      bg: "bg-green-500/10"
    },
    {
      title: "Cash Sales",
      value: formatCurrency(monthlySummary?.total_cash_sale, currentCurrency),
      icon: Wallet,
      color: "text-blue-500",
      bg: "bg-blue-500/10"
    },
    {
      title: "Online Sales",
      value: formatCurrency(monthlySummary?.total_online_sale, currentCurrency),
      icon: CreditCard,
      color: "text-purple-500",
      bg: "bg-purple-500/10"
    },
    {
      title: "Total Expenses",
      value: formatCurrency(monthlySummary?.total_expenses, currentCurrency),
      icon: Receipt,
      color: "text-red-500",
      bg: "bg-red-500/10"
    }
  ];

  // GST & Guest Stats cards
  const statsCards = [
    {
      title: `GST Payable (${monthlySummary?.gst_rate || 5}%)`,
      value: formatCurrency(monthlySummary?.gst_amount || monthlySummary?.total_gst, currentCurrency),
      subtitle: monthlySummary?.gst_inclusive ? "Inclusive in price" : "Added on subtotal",
      icon: FileText,
      color: "text-amber-600",
      bg: "bg-amber-500/10"
    },
    {
      title: "Total Guests",
      value: (monthlySummary?.total_guests || 0).toLocaleString(),
      subtitle: `Avg ${formatCurrency(monthlySummary?.avg_per_pax, currentCurrency)}/pax`,
      icon: Users,
      color: "text-indigo-500",
      bg: "bg-indigo-500/10"
    },
    {
      title: "Total Bills",
      value: (monthlySummary?.total_bills || 0).toLocaleString(),
      subtitle: `Avg ${formatCurrency(monthlySummary?.avg_per_bill, currentCurrency)}/bill`,
      icon: Receipt,
      color: "text-teal-500",
      bg: "bg-teal-500/10"
    }
  ];

  // Online payment breakdown
  const onlineBreakdown = [
    { name: "Card (IDFC)", value: monthlySummary?.total_card_idfc || 0, color: "bg-blue-500" },
    { name: "Bharat Pay", value: monthlySummary?.total_bharat_pay || 0, color: "bg-indigo-500" },
    { name: "Swiggy", value: monthlySummary?.total_swiggy || 0, color: "bg-orange-500" },
    { name: "Zomato", value: monthlySummary?.total_zomato || 0, color: "bg-red-500" }
  ];

  return (
    <div className="p-6 space-y-6" data-testid="sales-expenses-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Sales & Cash Summary</h1>
          <p className="text-muted-foreground">Track daily sales, payments, and expenses</p>
        </div>
        
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <Input
              type="month"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="w-40"
              data-testid="month-filter"
            />
          </div>
          
          {hasAllCentersAccess && (
            <Select value={selectedCenter} onValueChange={setSelectedCenter}>
              <SelectTrigger className="w-52" data-testid="center-filter">
                <SelectValue placeholder="All Centers" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Centers</SelectItem>
                {centers.map(c => (
                  <SelectItem key={typeof c === 'string' ? c : c.code} value={typeof c === 'string' ? c : c.code}>
                    {typeof c === 'string' ? c : `${c.code} - ${c.name}`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          
          <Button
            variant="outline"
            onClick={downloadMonthlyExcel}
            disabled={loading}
            className="text-green-600 border-green-600 hover:bg-green-50"
            data-testid="download-excel-btn"
          >
            <Download className="w-4 h-4 mr-2" />
            Download Excel
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={recalculateBalances}
            disabled={recalculating || loading || selectedCenter === "all"}
            title="Recalculate opening/closing balances for all days in this month"
            data-testid="recalculate-btn"
          >
            <Calculator className={`w-4 h-4 mr-1 ${recalculating ? 'animate-spin' : ''}`} />
            {recalculating ? "Fixing..." : "Fix Balances"}
          </Button>
          
          <Button
            variant="outline"
            size="icon"
            onClick={() => { fetchMonthlySummary(); fetchExpenses(); }}
            disabled={loading}
            data-testid="refresh-btn"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map((card, idx) => (
          <Card key={idx} className="bg-card border-border" data-testid={`summary-card-${idx}`}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{card.title}</p>
                  <p className="text-2xl font-bold mt-1">{card.value}</p>
                </div>
                <div className={`p-3 rounded-full ${card.bg}`}>
                  <card.icon className={`w-6 h-6 ${card.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* GST & Guest Stats Cards */}
      {monthlySummary && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {statsCards.map((card, idx) => (
            <Card key={idx} className="bg-card border-border" data-testid={`stats-card-${idx}`}>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{card.title}</p>
                    <p className="text-xl font-bold mt-1">{card.value}</p>
                    {card.subtitle && (
                      <p className="text-xs text-muted-foreground mt-1">{card.subtitle}</p>
                    )}
                  </div>
                  <div className={`p-3 rounded-full ${card.bg}`}>
                    <card.icon className={`w-5 h-5 ${card.color}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-muted flex-wrap">
          <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
          <TabsTrigger value="sales-entry" data-testid="tab-sales-entry">Sales Entry</TabsTrigger>
          <TabsTrigger value="grid-update" data-testid="tab-grid-update" className="text-blue-600">
            <Table2 className="w-4 h-4 mr-1" />
            Grid Update
          </TabsTrigger>
          <TabsTrigger value="upload" data-testid="tab-upload" className="text-green-600">
            <Upload className="w-4 h-4 mr-1" />
            Upload Excel
          </TabsTrigger>
          <TabsTrigger value="expense-entry" data-testid="tab-expense-entry">Expense Entry</TabsTrigger>
          <TabsTrigger value="bank-reconciliation" data-testid="tab-bank-reconciliation" className="text-amber-600">
            <ArrowRightLeft className="w-4 h-4 mr-1" />
            Bank Reconciliation
          </TabsTrigger>
          <TabsTrigger value="daily" data-testid="tab-daily">Daily Report</TabsTrigger>
          {session?.is_super_admin && (
            <TabsTrigger value="expenses" data-testid="tab-expenses">Expense List (Admin)</TabsTrigger>
          )}
          <TabsTrigger value="breakdown" data-testid="tab-breakdown">Payment Breakdown</TabsTrigger>
          {session?.is_super_admin && (
            <TabsTrigger value="freeze-control" data-testid="tab-freeze-control" className="text-red-500">
              <Shield className="w-4 h-4 mr-1" />
              Freeze Control
            </TabsTrigger>
          )}
          {session?.is_super_admin && (
            <TabsTrigger value="upload-settings" data-testid="tab-upload-settings" className="text-amber-600">
              <Settings className="w-4 h-4 mr-1" />
              Upload Settings
            </TabsTrigger>
          )}
        </TabsList>

        {/* Sales Data Entry Tab */}
        <TabsContent value="sales-entry">
          <SalesDataEntry session={session} selectedCenter={selectedCenter} centersList={centers} />
        </TabsContent>

        {/* Grid Update Tab */}
        <TabsContent value="grid-update">
          <SalesGridEditor 
            session={session} 
            selectedCenter={selectedCenter} 
            selectedMonth={selectedMonth}
            centersList={centers}
          />
        </TabsContent>

        {/* Upload Excel Tab */}
        <TabsContent value="upload">
          <SalesUploadTab 
            session={session} 
            selectedCenter={selectedCenter}
            onUploadComplete={fetchMonthlySummary}
          />
        </TabsContent>

        {/* Upload Settings Tab - Super Admin Only */}
        {session?.is_super_admin && (
          <TabsContent value="upload-settings">
            <UploadSettingsTab session={session} centers={centers} />
          </TabsContent>
        )}

        {/* Expense Entry Tab */}
        <TabsContent value="expense-entry">
          <ExpenseEntry session={session} selectedCenter={selectedCenter} centersList={centers} />
        </TabsContent>

        {/* Bank Statement Reconciliation Tab */}
        <TabsContent value="bank-reconciliation">
          <BankReconciliation 
            session={session} 
            selectedCenter={selectedCenter !== "all" ? selectedCenter : ""} 
            centersList={centers}
          />
        </TabsContent>

        {/* Freeze Control Tab - Super Admin Only */}
        {session?.is_super_admin && (
          <TabsContent value="freeze-control">
            <FreezeControl session={session} />
          </TabsContent>
        )}

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Online Payment Breakdown */}
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <CreditCard className="w-5 h-5 text-primary" />
                  Online Payment Breakdown
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {onlineBreakdown.map((item, idx) => {
                    const total = onlineBreakdown.reduce((a, b) => a + b.value, 0);
                    const percentage = total > 0 ? (item.value / total) * 100 : 0;
                    return (
                      <div key={idx} className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">{item.name}</span>
                          <span className="font-medium">{formatCurrency(item.value, currentCurrency)}</span>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${item.color} transition-all duration-500`}
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Expense by Category */}
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <PieChart className="w-5 h-5 text-primary" />
                  Expenses by Category
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {Object.entries(expenseByType).length > 0 ? (
                    Object.entries(expenseByType)
                      .sort((a, b) => b[1] - a[1])
                      .slice(0, 8)
                      .map(([type, amount], idx) => (
                        <div key={idx} className="flex justify-between items-center py-2 border-b border-border last:border-0">
                          <span className="text-sm text-muted-foreground truncate max-w-[60%]">{type}</span>
                          <span className="font-medium text-sm">{formatCurrency(amount, currentCurrency)}</span>
                        </div>
                      ))
                  ) : (
                    <p className="text-center text-muted-foreground py-4">No expense data</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Net Summary */}
          {monthlySummary && (
            <Card className="bg-card border-border">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Net Profit (Sales - Expenses)</p>
                    <p className={`text-3xl font-bold ${
                      (monthlySummary.total_sale - (monthlySummary.total_expenses || 0)) >= 0 
                        ? 'text-green-500' 
                        : 'text-red-500'
                    }`}>
                      {formatCurrency((monthlySummary.total_sale || 0) - (monthlySummary.total_expenses || 0), currentCurrency)}
                    </p>
                  </div>
                  <div className={`p-4 rounded-full ${
                    (monthlySummary.total_sale - (monthlySummary.total_expenses || 0)) >= 0 
                      ? 'bg-green-500/10' 
                      : 'bg-red-500/10'
                  }`}>
                    {(monthlySummary.total_sale - (monthlySummary.total_expenses || 0)) >= 0 
                      ? <ArrowUpRight className="w-8 h-8 text-green-500" />
                      : <ArrowDownRight className="w-8 h-8 text-red-500" />
                    }
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Daily Report Tab */}
        <TabsContent value="daily">
          <Card className="bg-card border-border">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Daily Sales Report - {selectedMonth}</CardTitle>
              {session?.is_super_admin && unlockRequests.filter(r => r.status === 'pending').length > 0 && (
                <Button 
                  size="sm" 
                  variant="outline" 
                  className="gap-2"
                  onClick={() => setShowUnlockRequestsPanel(!showUnlockRequestsPanel)}
                >
                  <Clock className="w-4 h-4" />
                  {unlockRequests.filter(r => r.status === 'pending').length} Pending Requests
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {/* Unlock Requests Panel (Super Admin Only) */}
              {showUnlockRequestsPanel && session?.is_super_admin && (
                <div className="mb-6 p-4 bg-amber-500/10 rounded-lg border border-amber-500/30">
                  <h4 className="font-semibold mb-3 flex items-center gap-2">
                    <Clock className="w-4 h-4" /> Pending Unlock Requests
                  </h4>
                  <div className="space-y-3">
                    {unlockRequests.filter(r => r.status === 'pending').map((req) => (
                      <div key={req.id} className="flex items-center justify-between p-3 bg-background rounded border">
                        <div>
                          <p className="font-medium">{req.center} - {formatDateDisplay(req.date)}</p>
                          <p className="text-sm text-muted-foreground">By: {req.requested_by}</p>
                          <p className="text-sm text-muted-foreground">Reason: {req.reason}</p>
                        </div>
                        <div className="flex gap-2">
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="text-green-600 border-green-600"
                            onClick={() => processUnlockRequest(req.id, 'approve')}
                          >
                            <CheckCircle className="w-4 h-4 mr-1" /> Approve
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="text-red-600 border-red-600"
                            onClick={() => processUnlockRequest(req.id, 'reject')}
                          >
                            <XCircle className="w-4 h-4 mr-1" /> Reject
                          </Button>
                        </div>
                      </div>
                    ))}
                    {unlockRequests.filter(r => r.status === 'pending').length === 0 && (
                      <p className="text-muted-foreground text-sm">No pending requests</p>
                    )}
                  </div>
                </div>
              )}
              
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-2 font-medium text-muted-foreground">Date</th>
                      <th className="text-center py-3 px-2 font-medium text-muted-foreground w-10">Status</th>
                      {hasAllCentersAccess && !selectedCenter && <th className="text-left py-3 px-2 font-medium text-muted-foreground">Center</th>}
                      <th className="text-right py-3 px-2 font-medium text-muted-foreground">Total Sale</th>
                      <th className="text-right py-3 px-2 font-medium text-muted-foreground">Cash</th>
                      <th className="text-right py-3 px-2 font-medium text-muted-foreground">Online</th>
                      <th className="text-right py-3 px-2 font-medium text-muted-foreground">Expenses</th>
                      <th className="text-right py-3 px-2 font-medium text-muted-foreground">Net</th>
                      {!session?.is_super_admin && <th className="text-center py-3 px-2 font-medium text-muted-foreground">Action</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {dailyData.length > 0 ? (
                      dailyData.map((row, idx) => {
                        const frozen = isDateFrozen(row.date);
                        const hasPendingRequest = unlockRequests.some(
                          r => r.date === row.date && r.center === (row.center || session?.center) && r.status === 'pending'
                        );
                        
                        return (
                          <tr key={idx} className={`border-b border-border/50 hover:bg-muted/50 ${frozen ? 'bg-muted/20' : ''}`}>
                            <td className="py-3 px-2">{row.date ? formatDateDisplay(row.date) : '-'}</td>
                            <td className="py-3 px-2 text-center">
                              {frozen ? (
                                <span title="Frozen - Previous day data locked">
                                  <Lock className="w-4 h-4 text-amber-500 inline" />
                                </span>
                              ) : (
                                <span title="Editable - Today's data">
                                  <Unlock className="w-4 h-4 text-green-500 inline" />
                                </span>
                              )}
                            </td>
                            {hasAllCentersAccess && !selectedCenter && <td className="py-3 px-2">{row.center}</td>}
                            <td className="text-right py-3 px-2 font-medium">{formatCurrency(row.total_sale, currentCurrency)}</td>
                            <td className="text-right py-3 px-2">{formatCurrency(row.cash_sale || row.total_cash_sale, currentCurrency)}</td>
                            <td className="text-right py-3 px-2">{formatCurrency(row.online_sale || row.total_online_sale, currentCurrency)}</td>
                            <td className="text-right py-3 px-2 text-red-500">{formatCurrency(row.expenses || row.total_expenses, currentCurrency)}</td>
                            <td className={`text-right py-3 px-2 font-medium ${
                              (row.net || (row.total_sale - (row.expenses || row.total_expenses || 0))) >= 0 
                                ? 'text-green-500' 
                                : 'text-red-500'
                            }`}>
                              {formatCurrency(row.net || (row.total_sale - (row.expenses || row.total_expenses || 0)), currentCurrency)}
                            </td>
                            {!session?.is_super_admin && (
                              <td className="py-3 px-2 text-center">
                                {frozen && !hasPendingRequest && (
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    className="text-xs h-7"
                                    onClick={() => {
                                      setSelectedDateForUnlock({ date: row.date, center: row.center || session?.center });
                                      setShowUnlockModal(true);
                                    }}
                                  >
                                    Request Unlock
                                  </Button>
                                )}
                                {frozen && hasPendingRequest && (
                                  <span className="text-xs text-amber-500 flex items-center justify-center gap-1">
                                    <Clock className="w-3 h-3" /> Pending
                                  </span>
                                )}
                              </td>
                            )}
                          </tr>
                        );
                      })
                    ) : (
                      <tr>
                        <td colSpan={hasAllCentersAccess && !selectedCenter ? 9 : 8} className="text-center py-8 text-muted-foreground">
                          No data available for selected period
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Expenses Tab */}
        {/* Expense List Tab - Admin Only */}
        {session?.is_super_admin && (
        <TabsContent value="expenses">
          <Card className="bg-card border-border">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Expense Records - {selectedMonth}</CardTitle>
              <div className="flex items-center gap-3">
                <Select value={selectedCenter} onValueChange={setSelectedCenter}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="All Centers" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Centers</SelectItem>
                    {centers.map(c => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button 
                  variant="outline" 
                  size="icon" 
                  onClick={fetchExpenses}
                  disabled={loading}
                >
                  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-2 font-medium text-muted-foreground">Date</th>
                      <th className="text-left py-3 px-2 font-medium text-muted-foreground">Center</th>
                      <th className="text-left py-3 px-2 font-medium text-muted-foreground">Description</th>
                      <th className="text-left py-3 px-2 font-medium text-muted-foreground">Category</th>
                      <th className="text-left py-3 px-2 font-medium text-muted-foreground">Mode</th>
                      <th className="text-right py-3 px-2 font-medium text-muted-foreground">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {expenses.length > 0 ? (
                      expenses.slice(0, 50).map((exp, idx) => (
                        <tr key={idx} className="border-b border-border/50 hover:bg-muted/50">
                          <td className="py-3 px-2">{formatDateDisplay(exp.date)}</td>
                          <td className="py-3 px-2 text-xs">{exp.center}</td>
                          <td className="py-3 px-2 max-w-[200px] truncate">{exp.description}</td>
                          <td className="py-3 px-2 text-xs">
                            <span className="px-2 py-1 rounded-full bg-muted">{exp.expense_type}</span>
                          </td>
                          <td className="py-3 px-2 text-xs">{exp.payment_mode}</td>
                          <td className="text-right py-3 px-2 font-medium">{formatCurrency(exp.amount, currentCurrency)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={6} className="text-center py-8 text-muted-foreground">
                          No expenses recorded for selected period
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
                {expenses.length > 50 && (
                  <p className="text-center text-muted-foreground py-4 text-sm">
                    Showing 50 of {expenses.length} records
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        )}

        {/* Payment Breakdown Tab */}
        <TabsContent value="breakdown">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Cash vs Online */}
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="text-lg">Cash vs Online Sales</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-muted-foreground">Cash Sales</span>
                      <span className="font-bold text-green-500">{formatCurrency(monthlySummary?.total_cash_sale, currentCurrency)}</span>
                    </div>
                    <div className="h-4 bg-muted rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-green-500"
                        style={{ 
                          width: `${monthlySummary?.total_sale > 0 
                            ? (monthlySummary.total_cash_sale / monthlySummary.total_sale) * 100 
                            : 0}%` 
                        }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-muted-foreground">Online Sales</span>
                      <span className="font-bold text-purple-500">{formatCurrency(monthlySummary?.total_online_sale, currentCurrency)}</span>
                    </div>
                    <div className="h-4 bg-muted rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-purple-500"
                        style={{ 
                          width: `${monthlySummary?.total_sale > 0 
                            ? (monthlySummary.total_online_sale / monthlySummary.total_sale) * 100 
                            : 0}%` 
                        }}
                      />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Detailed Online Breakdown */}
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="text-lg">Online Payment Details</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {onlineBreakdown.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                      <div className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${item.color}`} />
                        <span>{item.name}</span>
                      </div>
                      <span className="font-medium">{formatCurrency(item.value, currentCurrency)}</span>
                    </div>
                  ))}
                  <div className="flex items-center justify-between pt-2 font-bold">
                    <span>Total Online</span>
                    <span className="text-purple-500">{formatCurrency(monthlySummary?.total_online_sale, currentCurrency)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Unlock Request Modal */}
      {showUnlockModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background p-6 rounded-lg shadow-lg max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Lock className="w-5 h-5 text-amber-500" />
              Request Unlock for Frozen Date
            </h3>
            
            <div className="space-y-4">
              <div>
                <Label className="text-sm text-muted-foreground">Date</Label>
                <p className="font-medium">{selectedDateForUnlock?.date ? formatDateDisplay(selectedDateForUnlock.date) : ''}</p>
              </div>
              
              <div>
                <Label className="text-sm text-muted-foreground">Center</Label>
                <p className="font-medium">{selectedDateForUnlock?.center}</p>
              </div>
              
              <div>
                <Label htmlFor="unlock-reason">Reason for Unlock Request *</Label>
                <textarea
                  id="unlock-reason"
                  className="w-full mt-1 p-3 border rounded-md bg-background text-foreground min-h-[100px]"
                  placeholder="Please explain why you need to edit this frozen date's data..."
                  value={unlockReason}
                  onChange={(e) => setUnlockReason(e.target.value)}
                />
              </div>
              
              <div className="bg-amber-500/10 p-3 rounded text-sm text-amber-700 dark:text-amber-300">
                <strong>Note:</strong> Your request will be sent to Super Admin for approval. 
                Once approved, you will have 24 hours to make edits.
              </div>
            </div>
            
            <div className="flex gap-3 mt-6 justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setShowUnlockModal(false);
                  setUnlockReason("");
                  setSelectedDateForUnlock(null);
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={submitUnlockRequest}
                disabled={!unlockReason.trim()}
              >
                Submit Request
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
