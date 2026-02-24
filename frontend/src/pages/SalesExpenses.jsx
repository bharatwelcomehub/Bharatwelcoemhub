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
  PieChart
} from "lucide-react";
import { api, API_URL } from "@/lib/api";
import SalesDataEntry from "@/components/SalesDataEntry";
import ExpenseEntry from "@/components/ExpenseEntry";

// Format currency
const formatCurrency = (amount) => {
  if (amount === null || amount === undefined) return "₹0";
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount);
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
  
  // Check if user has admin access (can view all centers)
  const hasAllCentersAccess = session?.center === "PB-MGT" || 
                              session?.is_super_admin === true || 
                              session?.is_admin === true ||
                              session?.roles?.view_all_centers === true;
  
  // Filters
  const [selectedMonth, setSelectedMonth] = useState(getCurrentMonthStr());
  const [selectedCenter, setSelectedCenter] = useState(hasAllCentersAccess ? "all" : session?.center);
  const [centers, setCenters] = useState([]);
  
  // Data
  const [monthlySummary, setMonthlySummary] = useState(null);
  const [dailyData, setDailyData] = useState([]);
  const [expenseByType, setExpenseByType] = useState({});
  const [expenses, setExpenses] = useState([]);

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
    if (!selectedMonth) return;
    
    setLoading(true);
    try {
      const res = await api.post("/sales/reports/monthly-summary", {
        token: session?.token,
        month: selectedMonth,
        center: selectedCenter || "all"
      });
      
      if (res.data) {
        setMonthlySummary(res.data.summary || res.data.grand_total);
        setDailyData(res.data.daily_data || []);
        setExpenseByType(res.data.expense_by_type || {});
        
        // If we got centers data (all centers view)
        if (res.data.centers) {
          setDailyData(res.data.centers);
        }
      }
    } catch (err) {
      console.error("Failed to fetch summary:", err);
      toast.error("Failed to load sales data");
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
        center: selectedCenter || undefined
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
      value: formatCurrency(monthlySummary?.total_sale),
      icon: IndianRupee,
      color: "text-green-500",
      bg: "bg-green-500/10"
    },
    {
      title: "Cash Sales",
      value: formatCurrency(monthlySummary?.total_cash_sale),
      icon: Wallet,
      color: "text-blue-500",
      bg: "bg-blue-500/10"
    },
    {
      title: "Online Sales",
      value: formatCurrency(monthlySummary?.total_online_sale),
      icon: CreditCard,
      color: "text-purple-500",
      bg: "bg-purple-500/10"
    },
    {
      title: "Total Expenses",
      value: formatCurrency(monthlySummary?.total_expenses),
      icon: Receipt,
      color: "text-red-500",
      bg: "bg-red-500/10"
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
            <Select value={selectedCenter || "all"} onValueChange={(val) => setSelectedCenter(val === "all" ? "" : val)}>
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

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-muted flex-wrap">
          <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
          <TabsTrigger value="sales-entry" data-testid="tab-sales-entry">Sales Entry</TabsTrigger>
          <TabsTrigger value="expense-entry" data-testid="tab-expense-entry">Expense Entry</TabsTrigger>
          <TabsTrigger value="daily" data-testid="tab-daily">Daily Report</TabsTrigger>
          <TabsTrigger value="expenses" data-testid="tab-expenses">Expense List</TabsTrigger>
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
