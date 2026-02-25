import { useState, useEffect, useRef } from "react";
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
  Upload,
  FileSpreadsheet,
  Loader2,
  CheckCircle
} from "lucide-react";
import { api, API_URL } from "@/lib/api";
import SalesDataEntry from "@/components/SalesDataEntry";
import ExpenseEntry from "@/components/ExpenseEntry";

// Check if center is Perth (Australia)
const isPerth = (center) => center && center.toUpperCase() === "PB-PT";

// Get currency symbol based on center
const getCurrencySymbol = (center) => isPerth(center) ? "$" : "₹";

// Format currency with dynamic symbol
const formatCurrency = (amount, center = null) => {
  if (amount === null || amount === undefined) return "₹0";
  const symbol = center ? getCurrencySymbol(center) : "₹";
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
  
  // Perth Excel Upload state
  const [uploadingExcel, setUploadingExcel] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const fileInputRef = useRef(null);
  
  // Check if user has admin access - recalculate on every render
  const hasAllCentersAccess = session?.center === "PB-MGT" || 
                              session?.is_super_admin === true || 
                              session?.is_admin === true ||
                              session?.roles?.view_all_centers === true;

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

  // Perth Excel Upload handler
  const handlePerthExcelUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    // Validate file type
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      toast.error("Please select an Excel file (.xlsx or .xls)");
      return;
    }
    
    setUploadingExcel(true);
    setUploadResult(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const res = await api.post(`/sales/perth/upload-excel?token=${session.token}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      if (res.data.success) {
        setUploadResult(res.data);
        toast.success(`Perth Excel imported: ${res.data.imported_count} records`);
        // Refresh data
        fetchMonthlySummary();
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to upload Excel");
      setUploadResult({ error: err.response?.data?.detail || "Upload failed" });
    } finally {
      setUploadingExcel(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

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
    setLoading(true);
    try {
      const res = await api.post("/sales/expenses", {
        token: session?.token,
        month: selectedMonth,
        center: selectedCenter || "all"
      });
      
      if (res.data.expenses) {
        setExpenses(res.data.expenses);
      }
    } catch (err) {
      console.error("Failed to fetch expenses:", err);
      toast.error("Failed to load expenses");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (session?.token) {
      fetchMonthlySummary();
      fetchExpenses();
    }
  }, [selectedMonth, selectedCenter, session?.token]);

  // Summary cards data
  const summaryCards = [
    {
      title: "Total Sales",
      value: formatCurrency(monthlySummary?.total_sale, selectedCenter),
      icon: IndianRupee,
      color: "text-green-500",
      bg: "bg-green-500/10"
    },
    {
      title: "Cash Sales",
      value: formatCurrency(monthlySummary?.total_cash_sale, selectedCenter),
      icon: Wallet,
      color: "text-blue-500",
      bg: "bg-blue-500/10"
    },
    {
      title: "Online Sales",
      value: formatCurrency(monthlySummary?.total_online_sale, selectedCenter),
      icon: CreditCard,
      color: "text-purple-500",
      bg: "bg-purple-500/10"
    },
    {
      title: "Total Expenses",
      value: formatCurrency(monthlySummary?.total_expenses, selectedCenter),
      icon: Receipt,
      color: "text-red-500",
      bg: "bg-red-500/10"
    }
  ];

  // GST & Guest Stats cards
  const statsCards = [
    {
      title: `GST Payable (${monthlySummary?.gst_rate || 5}%)`,
      value: formatCurrency(monthlySummary?.gst_amount || monthlySummary?.total_gst, selectedCenter),
      subtitle: monthlySummary?.gst_inclusive ? "Inclusive in price" : "Added on subtotal",
      icon: FileText,
      color: "text-amber-600",
      bg: "bg-amber-500/10"
    },
    {
      title: "Total Guests",
      value: (monthlySummary?.total_guests || 0).toLocaleString(),
      subtitle: `Avg ${formatCurrency(monthlySummary?.avg_per_pax, selectedCenter)}/pax`,
      icon: Users,
      color: "text-indigo-500",
      bg: "bg-indigo-500/10"
    },
    {
      title: "Total Bills",
      value: (monthlySummary?.total_bills || 0).toLocaleString(),
      subtitle: `Avg ${formatCurrency(monthlySummary?.avg_per_bill, selectedCenter)}/bill`,
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
              <SelectTrigger className="w-40" data-testid="center-filter">
                <SelectValue placeholder="All Centers" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Centers</SelectItem>
                {centers.map(c => (
                  <SelectItem key={c} value={c}>{c}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          
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
          <TabsTrigger value="expense-entry" data-testid="tab-expense-entry">Expense Entry</TabsTrigger>
          <TabsTrigger value="daily" data-testid="tab-daily">Daily Report</TabsTrigger>
          <TabsTrigger value="expenses" data-testid="tab-expenses">Expense List</TabsTrigger>
          <TabsTrigger value="breakdown" data-testid="tab-breakdown">Payment Breakdown</TabsTrigger>
          {/* Perth Excel Upload - Only for admins */}
          {(session?.is_super_admin || session?.is_admin) && (
            <TabsTrigger value="perth-upload" data-testid="tab-perth-upload" className="gap-2">
              <FileSpreadsheet className="w-4 h-4" />
              Perth Excel
            </TabsTrigger>
          )}
        </TabsList>

        {/* Perth Excel Upload Tab */}
        {(session?.is_super_admin || session?.is_admin) && (
          <TabsContent value="perth-upload">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileSpreadsheet className="w-5 h-5 text-green-600" />
                  Perth Sales Excel Upload
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Upload Perth center's Excel file. Data will be imported exactly as-is without modification.
                </p>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Upload Area */}
                <div className="border-2 border-dashed border-muted rounded-lg p-8 text-center">
                  <input
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={handlePerthExcelUpload}
                    ref={fileInputRef}
                    className="hidden"
                    id="perth-excel-upload"
                    disabled={uploadingExcel}
                  />
                  <label 
                    htmlFor="perth-excel-upload"
                    className="cursor-pointer flex flex-col items-center gap-4"
                  >
                    {uploadingExcel ? (
                      <>
                        <Loader2 className="w-12 h-12 text-primary animate-spin" />
                        <span className="text-lg">Uploading & Processing...</span>
                      </>
                    ) : (
                      <>
                        <Upload className="w-12 h-12 text-muted-foreground" />
                        <div>
                          <p className="text-lg font-medium">Click to upload Perth Excel</p>
                          <p className="text-sm text-muted-foreground">
                            Supports .xlsx and .xls files
                          </p>
                        </div>
                      </>
                    )}
                  </label>
                </div>

                {/* Upload Result */}
                {uploadResult && (
                  <div className={`p-4 rounded-lg ${uploadResult.error ? 'bg-red-50 border border-red-200' : 'bg-green-50 border border-green-200'}`}>
                    {uploadResult.error ? (
                      <p className="text-red-600">{uploadResult.error}</p>
                    ) : (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 text-green-700">
                          <CheckCircle className="w-5 h-5" />
                          <span className="font-medium">Import Successful!</span>
                        </div>
                        <div className="grid grid-cols-3 gap-4 mt-3">
                          <div className="text-center p-3 bg-white rounded">
                            <p className="text-2xl font-bold text-green-600">{uploadResult.imported_count}</p>
                            <p className="text-xs text-muted-foreground">Records Imported</p>
                          </div>
                          <div className="text-center p-3 bg-white rounded">
                            <p className="text-2xl font-bold text-amber-600">{uploadResult.skipped_count}</p>
                            <p className="text-xs text-muted-foreground">Rows Skipped</p>
                          </div>
                          <div className="text-center p-3 bg-white rounded">
                            <p className="text-2xl font-bold text-blue-600">{uploadResult.gst_rate}</p>
                            <p className="text-xs text-muted-foreground">GST Rate</p>
                          </div>
                        </div>
                        {uploadResult.errors?.length > 0 && (
                          <div className="mt-3 p-2 bg-amber-50 rounded text-xs">
                            <p className="font-medium text-amber-800">Warnings:</p>
                            {uploadResult.errors.map((err, i) => (
                              <p key={i} className="text-amber-700">{err}</p>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Info Box */}
                <div className="p-4 bg-blue-50 rounded-lg">
                  <h4 className="font-medium text-blue-800 mb-2">Perth Excel Import Rules</h4>
                  <ul className="text-sm text-blue-700 space-y-1">
                    <li>• Center: <strong>PB-PT (Perth)</strong></li>
                    <li>• Currency: <strong>Australian Dollars ($AUD)</strong></li>
                    <li>• GST: <strong>10% Inclusive</strong> (GST amount extracted from total)</li>
                    <li>• DoorDash and UberEats excluded from GST calculation</li>
                    <li>• Data imported exactly as-is without modification</li>
                    <li>• Existing records for same date will be updated</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        )}

        {/* Sales Data Entry Tab */}
        <TabsContent value="sales-entry">
          <SalesDataEntry session={session} selectedCenter={selectedCenter} />
        </TabsContent>

        {/* Expense Entry Tab */}
        <TabsContent value="expense-entry">
          <ExpenseEntry session={session} selectedCenter={selectedCenter} />
        </TabsContent>

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
                          <span className="font-medium">{formatCurrency(item.value)}</span>
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
                          <span className="font-medium text-sm">{formatCurrency(amount)}</span>
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
                      {formatCurrency((monthlySummary.total_sale || 0) - (monthlySummary.total_expenses || 0))}
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
            <CardHeader>
              <CardTitle className="text-lg">Daily Sales Report - {selectedMonth}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-2 font-medium text-muted-foreground">Date</th>
                      {hasAllCentersAccess && !selectedCenter && <th className="text-left py-3 px-2 font-medium text-muted-foreground">Center</th>}
                      <th className="text-right py-3 px-2 font-medium text-muted-foreground">Total Sale</th>
                      <th className="text-right py-3 px-2 font-medium text-muted-foreground">Cash</th>
                      <th className="text-right py-3 px-2 font-medium text-muted-foreground">Online</th>
                      <th className="text-right py-3 px-2 font-medium text-muted-foreground">Expenses</th>
                      <th className="text-right py-3 px-2 font-medium text-muted-foreground">Net</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dailyData.length > 0 ? (
                      dailyData.map((row, idx) => (
                        <tr key={idx} className="border-b border-border/50 hover:bg-muted/50">
                          <td className="py-3 px-2">{row.date ? formatDateDisplay(row.date) : '-'}</td>
                          {hasAllCentersAccess && !selectedCenter && <td className="py-3 px-2">{row.center}</td>}
                          <td className="text-right py-3 px-2 font-medium">{formatCurrency(row.total_sale)}</td>
                          <td className="text-right py-3 px-2">{formatCurrency(row.cash_sale || row.total_cash_sale)}</td>
                          <td className="text-right py-3 px-2">{formatCurrency(row.online_sale || row.total_online_sale)}</td>
                          <td className="text-right py-3 px-2 text-red-500">{formatCurrency(row.expenses || row.total_expenses)}</td>
                          <td className={`text-right py-3 px-2 font-medium ${
                            (row.net || (row.total_sale - (row.expenses || row.total_expenses || 0))) >= 0 
                              ? 'text-green-500' 
                              : 'text-red-500'
                          }`}>
                            {formatCurrency(row.net || (row.total_sale - (row.expenses || row.total_expenses || 0)))}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={hasAllCentersAccess && !selectedCenter ? 7 : 6} className="text-center py-8 text-muted-foreground">
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
        <TabsContent value="expenses">
          <Card className="bg-card border-border">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Expense Records - {selectedMonth}</CardTitle>
              <Button size="sm" className="gap-2" data-testid="add-expense-btn">
                <Plus className="w-4 h-4" /> Add Expense
              </Button>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-2 font-medium text-muted-foreground">Date</th>
                      {hasAllCentersAccess && <th className="text-left py-3 px-2 font-medium text-muted-foreground">Center</th>}
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
                          {hasAllCentersAccess && <td className="py-3 px-2 text-xs">{exp.center}</td>}
                          <td className="py-3 px-2 max-w-[200px] truncate">{exp.description}</td>
                          <td className="py-3 px-2 text-xs">
                            <span className="px-2 py-1 rounded-full bg-muted">{exp.expense_type}</span>
                          </td>
                          <td className="py-3 px-2 text-xs">{exp.payment_mode}</td>
                          <td className="text-right py-3 px-2 font-medium">{formatCurrency(exp.amount)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={hasAllCentersAccess ? 6 : 5} className="text-center py-8 text-muted-foreground">
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
                      <span className="font-bold text-green-500">{formatCurrency(monthlySummary?.total_cash_sale)}</span>
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
                      <span className="font-bold text-purple-500">{formatCurrency(monthlySummary?.total_online_sale)}</span>
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
                      <span className="font-medium">{formatCurrency(item.value)}</span>
                    </div>
                  ))}
                  <div className="flex items-center justify-between pt-2 font-bold">
                    <span>Total Online</span>
                    <span className="text-purple-500">{formatCurrency(monthlySummary?.total_online_sale)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
