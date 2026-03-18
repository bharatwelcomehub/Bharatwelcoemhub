import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  Area
} from "recharts";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Building2,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Calendar,
  PieChart as PieChartIcon,
  BarChart3,
  Settings,
  Bell,
  ArrowUpRight,
  ArrowDownRight,
  Users,
  Receipt,
  Wallet,
  Filter,
  Download
} from "lucide-react";
import { api } from "@/lib/api";

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088FE', '#00C49F', '#FFBB28', '#FF8042'];
const ALERT_COLORS = { high: "#ef4444", medium: "#f59e0b", normal: "#22c55e" };

const formatCurrency = (value) => {
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(2)}Cr`;
  if (value >= 100000) return `₹${(value / 100000).toFixed(2)}L`;
  if (value >= 1000) return `₹${(value / 1000).toFixed(1)}K`;
  return `₹${value?.toFixed(0) || 0}`;
};

const formatPercent = (value) => `${value?.toFixed(1) || 0}%`;

export default function MISDashboard() {
  const { session } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(false);
  
  // Filters
  const [period, setPeriod] = useState("current_month");
  const [selectedCenter, setSelectedCenter] = useState("all");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  
  // Data
  const [overview, setOverview] = useState(null);
  const [trends, setTrends] = useState([]);
  const [centerComparison, setCenterComparison] = useState([]);
  const [expenseAnalysis, setExpenseAnalysis] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [quarterlyData, setQuarterlyData] = useState([]);
  const [topPerformers, setTopPerformers] = useState(null);
  
  // Settings
  const [alertThreshold, setAlertThreshold] = useState(20);
  const [showSettings, setShowSettings] = useState(false);

  // Fetch all data
  const fetchData = useCallback(async () => {
    if (!session?.token) return;
    
    setLoading(true);
    try {
      const params = {
        token: session.token,
        period,
        center: selectedCenter,
        custom_start: customStart,
        custom_end: customEnd
      };
      
      // Fetch all data in parallel
      const [overviewRes, trendsRes, centerRes, expenseRes, alertsRes, quarterRes, topRes] = await Promise.all([
        api.post("/mis/overview", params),
        api.post("/mis/sales-trends", { ...params, group_by: period === "current_month" ? "daily" : "weekly" }),
        api.post("/mis/center-comparison", params),
        api.post("/mis/expense-analysis", params),
        api.post("/mis/alerts", { token: session.token, alert_threshold: alertThreshold }),
        api.post("/mis/quarterly-comparison", { token: session.token, center: selectedCenter }),
        api.post("/mis/top-performers", params)
      ]);
      
      setOverview(overviewRes.data);
      setTrends(trendsRes.data.trends || []);
      setCenterComparison(centerRes.data.centers || []);
      setExpenseAnalysis(expenseRes.data);
      setAlerts(alertsRes.data.alerts || []);
      setQuarterlyData(quarterRes.data.quarters || []);
      setTopPerformers(topRes.data);
      
    } catch (err) {
      toast.error("Failed to load dashboard data");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [session?.token, period, selectedCenter, customStart, customEnd, alertThreshold]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Fetch alert settings
  useEffect(() => {
    const fetchSettings = async () => {
      if (session?.token) {
        try {
          const res = await api.post("/mis/get-alert-settings", { token: session.token });
          setAlertThreshold(res.data.threshold || 20);
        } catch (err) {
          console.error("Failed to fetch settings");
        }
      }
    };
    fetchSettings();
  }, [session?.token]);

  // Save alert threshold
  const saveAlertThreshold = async () => {
    try {
      await api.post("/mis/save-alert-settings", { 
        token: session?.token, 
        threshold: alertThreshold 
      });
      toast.success("Alert threshold saved");
      setShowSettings(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to save");
    }
  };

  // Access check
  const isSuperAdmin = session?.is_super_admin;
  const isAdmin = session?.is_admin;
  const hasAccounting = session?.roles?.accounting;
  
  if (!isSuperAdmin && !isAdmin && !hasAccounting) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <AlertTriangle className="w-16 h-16 text-red-500 mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">Access Denied</h2>
        <p className="text-muted-foreground">Only Admin or Accounts users can access MIS Dashboard.</p>
      </div>
    );
  }

  const getChangeIcon = (change) => {
    if (change > 0) return <ArrowUpRight className="w-4 h-4 text-green-500" />;
    if (change < 0) return <ArrowDownRight className="w-4 h-4 text-red-500" />;
    return null;
  };

  const getChangeColor = (change, isExpense = false) => {
    // For expenses, increase is bad (red), decrease is good (green)
    if (isExpense) {
      if (change > 10) return "text-red-500";
      if (change < -10) return "text-green-500";
    } else {
      if (change > 10) return "text-green-500";
      if (change < -10) return "text-red-500";
    }
    return "text-yellow-500";
  };

  return (
    <div className="space-y-6" data-testid="mis-dashboard">
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-secondary" />
            MIS Dashboard
          </h1>
          <p className="text-muted-foreground mt-1">
            Centralized analytics for sales, expenses, and performance
          </p>
        </div>
        
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-[160px] bg-card border-border">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="current_month">Current Month</SelectItem>
              <SelectItem value="current_quarter">Current Quarter</SelectItem>
              <SelectItem value="last_3_months">Last 3 Months</SelectItem>
              <SelectItem value="ytd">Year to Date</SelectItem>
              <SelectItem value="custom">Custom Range</SelectItem>
            </SelectContent>
          </Select>
          
          <Select value={selectedCenter} onValueChange={setSelectedCenter}>
            <SelectTrigger className="w-[140px] bg-card border-border">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Centers</SelectItem>
              {overview?.centers?.map(c => (
                <SelectItem key={c.center} value={c.center}>{c.center}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          {period === "custom" && (
            <>
              <Input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="w-[140px] bg-card border-border"
              />
              <Input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="w-[140px] bg-card border-border"
              />
            </>
          )}
          
          <Button variant="outline" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          
          {isSuperAdmin && (
            <Button variant="ghost" size="icon" onClick={() => setShowSettings(!showSettings)}>
              <Settings className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Alert Settings Modal */}
      {showSettings && (
        <Card className="bg-amber-500/10 border-amber-500/30">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Label>Alert Threshold (%)</Label>
                <Input
                  type="number"
                  value={alertThreshold}
                  onChange={(e) => setAlertThreshold(parseInt(e.target.value) || 20)}
                  className="w-20 bg-card"
                />
                <span className="text-sm text-muted-foreground">
                  Trigger alerts when expenses increase by more than {alertThreshold}%
                </span>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setShowSettings(false)}>Cancel</Button>
                <Button onClick={saveAlertThreshold}>Save</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Alerts Banner */}
      {alerts.length > 0 && (
        <Card className="bg-red-500/10 border-red-500/30">
          <CardContent className="pt-4">
            <div className="flex items-start gap-3">
              <Bell className="w-5 h-5 text-red-500 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-red-400 mb-2">
                  {alerts.length} Alert{alerts.length > 1 ? 's' : ''} Detected
                </h3>
                <div className="flex flex-wrap gap-2">
                  {alerts.slice(0, 5).map((alert, i) => (
                    <Badge 
                      key={i} 
                      className={`${alert.severity === 'high' ? 'bg-red-500' : 'bg-amber-500'}`}
                    >
                      {alert.entity}: +{alert.change?.toFixed(1)}%
                    </Badge>
                  ))}
                  {alerts.length > 5 && (
                    <Badge variant="outline">+{alerts.length - 5} more</Badge>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary Cards */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {/* Total Sales */}
          <Card className="bg-card border-border">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground">Total Sales</p>
                  <p className="text-xl font-bold text-white">{formatCurrency(overview.summary?.total_sales)}</p>
                  <div className={`flex items-center text-xs ${getChangeColor(overview.changes?.sales_change)}`}>
                    {getChangeIcon(overview.changes?.sales_change)}
                    {overview.changes?.sales_change?.toFixed(1)}% vs prev
                  </div>
                </div>
                <DollarSign className="w-8 h-8 text-green-500 opacity-50" />
              </div>
            </CardContent>
          </Card>

          {/* Total Expenses */}
          <Card className="bg-card border-border">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground">Total Expenses</p>
                  <p className="text-xl font-bold text-white">{formatCurrency(overview.summary?.total_expenses)}</p>
                  <div className={`flex items-center text-xs ${getChangeColor(overview.changes?.expenses_change, true)}`}>
                    {getChangeIcon(overview.changes?.expenses_change)}
                    {overview.changes?.expenses_change?.toFixed(1)}% vs prev
                  </div>
                </div>
                <Receipt className="w-8 h-8 text-red-500 opacity-50" />
              </div>
            </CardContent>
          </Card>

          {/* GST */}
          <Card className="bg-card border-border">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground">GST (5%)</p>
                  <p className="text-xl font-bold text-white">{formatCurrency(overview.summary?.total_gst)}</p>
                  <p className="text-xs text-muted-foreground">Payable</p>
                </div>
                <Wallet className="w-8 h-8 text-amber-500 opacity-50" />
              </div>
            </CardContent>
          </Card>

          {/* Profit */}
          <Card className={`border-border ${overview.summary?.profit >= 0 ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground">Net Profit</p>
                  <p className={`text-xl font-bold ${overview.summary?.profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {formatCurrency(Math.abs(overview.summary?.profit))}
                    {overview.summary?.profit < 0 && ' (Loss)'}
                  </p>
                  <div className={`flex items-center text-xs ${getChangeColor(overview.changes?.profit_change)}`}>
                    {getChangeIcon(overview.changes?.profit_change)}
                    {overview.changes?.profit_change?.toFixed(1)}% vs prev
                  </div>
                </div>
                {overview.summary?.profit >= 0 ? 
                  <TrendingUp className="w-8 h-8 text-green-500 opacity-50" /> :
                  <TrendingDown className="w-8 h-8 text-red-500 opacity-50" />
                }
              </div>
            </CardContent>
          </Card>

          {/* Profit Margin */}
          <Card className="bg-card border-border">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground">Profit Margin</p>
                  <p className={`text-xl font-bold ${overview.summary?.profit_margin >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {overview.summary?.profit_margin?.toFixed(1)}%
                  </p>
                  <p className="text-xs text-muted-foreground">of sales</p>
                </div>
                <PieChartIcon className="w-8 h-8 text-secondary opacity-50" />
              </div>
            </CardContent>
          </Card>

          {/* Centers Count */}
          <Card className="bg-card border-border">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground">Active Centers</p>
                  <p className="text-xl font-bold text-white">{overview.centers?.length || 0}</p>
                  <p className="text-xs text-muted-foreground">{overview.summary?.total_guests?.toLocaleString()} guests</p>
                </div>
                <Building2 className="w-8 h-8 text-secondary opacity-50" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs for detailed views */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-card border border-border flex-wrap">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="centers">Center Analysis</TabsTrigger>
          <TabsTrigger value="expenses">Expense Analysis</TabsTrigger>
          <TabsTrigger value="alerts">Alerts & Warnings</TabsTrigger>
          <TabsTrigger value="quarterly">Quarterly Trends</TabsTrigger>
          <TabsTrigger value="performers">Top Performers</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Sales vs Expenses Trend */}
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="text-lg">Sales vs Expenses Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={trends}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey={period === "current_month" ? "date" : "week"} stroke="#888" fontSize={10} />
                    <YAxis stroke="#888" fontSize={10} tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #333' }}
                      formatter={(value) => formatCurrency(value)}
                    />
                    <Legend />
                    <Area type="monotone" dataKey="sales" fill="#22c55e" stroke="#22c55e" fillOpacity={0.2} name="Sales" />
                    <Area type="monotone" dataKey="expenses" fill="#ef4444" stroke="#ef4444" fillOpacity={0.2} name="Expenses" />
                    <Line type="monotone" dataKey="profit" stroke="#8884d8" strokeWidth={2} name="Profit" />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Center-wise Sales Distribution */}
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="text-lg">Sales by Center</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={centerComparison}
                      dataKey="sales"
                      nameKey="center"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label={({ center, percent }) => `${center} (${(percent * 100).toFixed(0)}%)`}
                    >
                      {centerComparison.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => formatCurrency(value)} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Center Performance Table */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-lg">Center Performance Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left p-2">Center</th>
                      <th className="text-right p-2">Sales</th>
                      <th className="text-right p-2">Expenses</th>
                      <th className="text-right p-2">GST</th>
                      <th className="text-right p-2">Profit</th>
                      <th className="text-right p-2">Margin</th>
                      <th className="text-right p-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview?.centers?.map((c, i) => (
                      <tr key={i} className="border-b border-border/50 hover:bg-white/5">
                        <td className="p-2 font-medium">{c.center}</td>
                        <td className="p-2 text-right text-green-400">{formatCurrency(c.sales)}</td>
                        <td className="p-2 text-right text-red-400">{formatCurrency(c.expenses)}</td>
                        <td className="p-2 text-right text-amber-400">{formatCurrency(c.gst)}</td>
                        <td className={`p-2 text-right font-semibold ${c.profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatCurrency(Math.abs(c.profit))}{c.profit < 0 && ' (L)'}
                        </td>
                        <td className={`p-2 text-right ${c.profit_margin >= 10 ? 'text-green-400' : c.profit_margin >= 0 ? 'text-yellow-400' : 'text-red-400'}`}>
                          {c.profit_margin?.toFixed(1)}%
                        </td>
                        <td className="p-2 text-right">
                          {c.profit_margin >= 15 ? (
                            <Badge className="bg-green-500">Healthy</Badge>
                          ) : c.profit_margin >= 5 ? (
                            <Badge className="bg-yellow-500">Moderate</Badge>
                          ) : (
                            <Badge className="bg-red-500">At Risk</Badge>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Center Analysis Tab */}
        <TabsContent value="centers" className="space-y-6">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-lg">Center-wise Comparison</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={centerComparison} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis type="number" stroke="#888" tickFormatter={(v) => `₹${(v/100000).toFixed(0)}L`} />
                  <YAxis dataKey="center" type="category" stroke="#888" width={80} />
                  <Tooltip formatter={(value) => formatCurrency(value)} />
                  <Legend />
                  <Bar dataKey="sales" fill="#22c55e" name="Sales" />
                  <Bar dataKey="expenses" fill="#ef4444" name="Expenses" />
                  <Bar dataKey="profit" fill="#8884d8" name="Profit" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Growth/Decline Table */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-lg">Growth vs Previous Period</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left p-2">Center</th>
                      <th className="text-right p-2">Current Sales</th>
                      <th className="text-right p-2">Prev Sales</th>
                      <th className="text-right p-2">Sales Change</th>
                      <th className="text-right p-2">Current Exp</th>
                      <th className="text-right p-2">Prev Exp</th>
                      <th className="text-right p-2">Exp Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {centerComparison.map((c, i) => (
                      <tr key={i} className="border-b border-border/50">
                        <td className="p-2 font-medium">{c.center}</td>
                        <td className="p-2 text-right">{formatCurrency(c.sales)}</td>
                        <td className="p-2 text-right text-muted-foreground">{formatCurrency(c.prev_sales)}</td>
                        <td className={`p-2 text-right font-semibold ${getChangeColor(c.sales_change)}`}>
                          {c.sales_change > 0 ? '+' : ''}{c.sales_change?.toFixed(1)}%
                        </td>
                        <td className="p-2 text-right">{formatCurrency(c.expenses)}</td>
                        <td className="p-2 text-right text-muted-foreground">{formatCurrency(c.prev_expenses)}</td>
                        <td className={`p-2 text-right font-semibold ${getChangeColor(c.expenses_change, true)}`}>
                          {c.expenses_change > 0 ? '+' : ''}{c.expenses_change?.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Expense Analysis Tab */}
        <TabsContent value="expenses" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Expense Distribution Pie */}
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="text-lg">Expense Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={expenseAnalysis?.by_type || []}
                      dataKey="amount"
                      nameKey="type"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label={({ type, percentage }) => `${type} (${percentage}%)`}
                    >
                      {(expenseAnalysis?.by_type || []).map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={entry.alert === 'high' ? '#ef4444' : entry.alert === 'medium' ? '#f59e0b' : COLORS[index % COLORS.length]} 
                        />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => formatCurrency(value)} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Expense by Category Bar */}
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="text-lg">Expenses by Category</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={expenseAnalysis?.by_type || []} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis type="number" stroke="#888" tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`} />
                    <YAxis dataKey="type" type="category" stroke="#888" width={100} />
                    <Tooltip formatter={(value) => formatCurrency(value)} />
                    <Bar dataKey="amount" name="Amount">
                      {(expenseAnalysis?.by_type || []).map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={entry.alert === 'high' ? '#ef4444' : entry.alert === 'medium' ? '#f59e0b' : '#8884d8'} 
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Expense Details Table */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-lg">Expense Head Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left p-2">Expense Head</th>
                      <th className="text-right p-2">Amount</th>
                      <th className="text-right p-2">% of Total</th>
                      <th className="text-right p-2">Count</th>
                      <th className="text-right p-2">Prev Period</th>
                      <th className="text-right p-2">Change</th>
                      <th className="text-right p-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {expenseAnalysis?.by_type?.map((exp, i) => (
                      <tr key={i} className="border-b border-border/50">
                        <td className="p-2 font-medium">{exp.type}</td>
                        <td className="p-2 text-right">{formatCurrency(exp.amount)}</td>
                        <td className="p-2 text-right">{exp.percentage}%</td>
                        <td className="p-2 text-right">{exp.count}</td>
                        <td className="p-2 text-right text-muted-foreground">{formatCurrency(exp.prev_amount)}</td>
                        <td className={`p-2 text-right font-semibold ${getChangeColor(exp.change, true)}`}>
                          {exp.change > 0 ? '+' : ''}{exp.change?.toFixed(1)}%
                        </td>
                        <td className="p-2 text-right">
                          {exp.alert === 'high' ? (
                            <Badge className="bg-red-500">High Alert</Badge>
                          ) : exp.alert === 'medium' ? (
                            <Badge className="bg-yellow-500">Watch</Badge>
                          ) : (
                            <Badge className="bg-green-500">Normal</Badge>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Alerts Tab */}
        <TabsContent value="alerts" className="space-y-6">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                Expense Alerts (Quarter over Quarter)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {alerts.length === 0 ? (
                <div className="text-center py-8">
                  <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
                  <p className="text-muted-foreground">No alerts! All expenses are within acceptable limits.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {alerts.map((alert, i) => (
                    <div 
                      key={i} 
                      className={`p-4 rounded-lg border ${
                        alert.severity === 'high' ? 'bg-red-500/10 border-red-500/30' : 'bg-amber-500/10 border-amber-500/30'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3">
                          {alert.severity === 'high' ? (
                            <XCircle className="w-5 h-5 text-red-500 mt-0.5" />
                          ) : (
                            <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5" />
                          )}
                          <div>
                            <p className="font-medium">{alert.message}</p>
                            <p className="text-sm text-muted-foreground mt-1">
                              {alert.type === 'center' ? 'Center' : 'Expense Head'}: {alert.entity}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm">Current: {formatCurrency(alert.current)}</p>
                          <p className="text-sm text-muted-foreground">Previous: {formatCurrency(alert.previous)}</p>
                          <Badge className={alert.severity === 'high' ? 'bg-red-500' : 'bg-amber-500'}>
                            +{alert.change?.toFixed(1)}%
                          </Badge>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Quarterly Trends Tab */}
        <TabsContent value="quarterly" className="space-y-6">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-lg">Quarterly Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <ComposedChart data={quarterlyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="label" stroke="#888" />
                  <YAxis stroke="#888" tickFormatter={(v) => `₹${(v/100000).toFixed(0)}L`} />
                  <Tooltip formatter={(value) => formatCurrency(value)} />
                  <Legend />
                  <Bar dataKey="sales" fill="#22c55e" name="Sales" />
                  <Bar dataKey="expenses" fill="#ef4444" name="Expenses" />
                  <Line type="monotone" dataKey="profit" stroke="#8884d8" strokeWidth={3} name="Profit" />
                </ComposedChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Quarterly Table */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-lg">Quarter-wise Breakdown</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left p-2">Quarter</th>
                      <th className="text-right p-2">Sales</th>
                      <th className="text-right p-2">Expenses</th>
                      <th className="text-right p-2">GST</th>
                      <th className="text-right p-2">Profit</th>
                      <th className="text-right p-2">Margin</th>
                    </tr>
                  </thead>
                  <tbody>
                    {quarterlyData.map((q, i) => (
                      <tr key={i} className="border-b border-border/50">
                        <td className="p-2 font-medium">{q.label}</td>
                        <td className="p-2 text-right text-green-400">{formatCurrency(q.sales)}</td>
                        <td className="p-2 text-right text-red-400">{formatCurrency(q.expenses)}</td>
                        <td className="p-2 text-right text-amber-400">{formatCurrency(q.gst)}</td>
                        <td className={`p-2 text-right font-semibold ${q.profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatCurrency(Math.abs(q.profit))}{q.profit < 0 && ' (L)'}
                        </td>
                        <td className="p-2 text-right">{q.profit_margin?.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Top Performers Tab */}
        <TabsContent value="performers" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top by Sales */}
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="text-lg text-green-400">Top Centers by Sales</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {topPerformers?.top_by_sales?.map((c, i) => (
                    <div key={i} className="flex items-center justify-between p-2 bg-green-500/10 rounded">
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold text-green-400">#{i + 1}</span>
                        <span className="font-medium">{c.center}</span>
                      </div>
                      <span className="text-green-400">{formatCurrency(c.sales)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Top by Profit Margin */}
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="text-lg text-blue-400">Top Centers by Profit Margin</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {topPerformers?.top_by_margin?.map((c, i) => (
                    <div key={i} className="flex items-center justify-between p-2 bg-blue-500/10 rounded">
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold text-blue-400">#{i + 1}</span>
                        <span className="font-medium">{c.center}</span>
                      </div>
                      <span className="text-blue-400">{c.profit_margin?.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Bottom by Sales */}
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="text-lg text-amber-400">Needs Attention (Low Sales)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {topPerformers?.bottom_by_sales?.map((c, i) => (
                    <div key={i} className="flex items-center justify-between p-2 bg-amber-500/10 rounded">
                      <span className="font-medium">{c.center}</span>
                      <span className="text-amber-400">{formatCurrency(c.sales)}</span>
                    </div>
                  ))}
                  {(!topPerformers?.bottom_by_sales || topPerformers.bottom_by_sales.length === 0) && (
                    <p className="text-muted-foreground text-center py-2">All centers performing well</p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Bottom by Margin */}
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="text-lg text-red-400">At Risk (Low Margin)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {topPerformers?.bottom_by_margin?.map((c, i) => (
                    <div key={i} className="flex items-center justify-between p-2 bg-red-500/10 rounded">
                      <span className="font-medium">{c.center}</span>
                      <span className="text-red-400">{c.profit_margin?.toFixed(1)}%</span>
                    </div>
                  ))}
                  {(!topPerformers?.bottom_by_margin || topPerformers.bottom_by_margin.length === 0) && (
                    <p className="text-muted-foreground text-center py-2">All centers healthy</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
