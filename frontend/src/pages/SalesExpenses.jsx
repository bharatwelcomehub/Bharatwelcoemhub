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
  Shield
} from "lucide-react";
import { api, API_URL } from "@/lib/api";
import SalesDataEntry from "@/components/SalesDataEntry";
import ExpenseEntry from "@/components/ExpenseEntry";
import FreezeControl from "@/components/FreezeControl";

// Check if center is Perth (Australia) - standardized to PB-PERTH
const isPerth = (center) => {
  if (!center) return false;
  const c = center.toUpperCase();
  return c === "PB-PERTH" || c === "PERTH";
};

// Get currency symbol based on center
const getCurrencySymbol = (center) => isPerth(center) ? "$" : "₹";

// Format currency with dynamic symbol - can accept center code OR currency symbol directly
const formatCurrency = (amount, centerOrCurrency = null) => {
  if (amount === null || amount === undefined) return "₹0";
  
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
  const hasAllCentersAccess = session?.center === "PB-MGT" || 
                              session?.is_super_admin === true || 
                              session?.is_admin === true ||
                              session?.roles?.view_all_centers === true ||
                              session?.roles?.accounting === true;  // Accounting role can view all centers

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

  // Retry fetch if data is empty after initial load
  useEffect(() => {
    if (session?.token && !loading && !monthlySummary && dailyData.length === 0) {
      const timer = setTimeout(() => {
        fetchMonthlySummary();
        fetchExpenses();
      }, 1000);
      return () => clearTimeout(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.token, loading, monthlySummary, dailyData.length]);

  // Get currency from API response or fallback to center-based logic
  // For non-admin users, use their session center to determine currency
  const effectiveCenter = selectedCenter !== "all" ? selectedCenter : session?.center;
  const currentCurrency = monthlySummary?.currency || getCurrencySymbol(effectiveCenter);

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
          {session?.is_super_admin && (
            <TabsTrigger value="expenses" data-testid="tab-expenses">Expense List (Admin)</TabsTrigger>
          )}
          <TabsTrigger value="breakdown" data-testid="tab-breakdown">Payment Breakdown</TabsTrigger>
        </TabsList>

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
