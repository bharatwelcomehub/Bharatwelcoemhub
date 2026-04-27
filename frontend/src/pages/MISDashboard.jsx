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
  PieChart as PieChartIcon,
  BarChart3,
  Settings,
  Bell,
  ArrowUpRight,
  ArrowDownRight,
  Users,
  Receipt,
  Wallet,
  Download,
  FileText,
  IndianRupee,
  Activity
} from "lucide-react";
import { api } from "@/lib/api";
import * as XLSX from "xlsx";

// Premium color palette — Purnabramha brand-inspired (saffron, gold, deep green)
const CHART_COLORS = ['#D97706', '#059669', '#7C3AED', '#DC2626', '#2563EB', '#F59E0B', '#10B981', '#8B5CF6'];
const GRADIENT_PAIRS = [
  { from: '#D97706', to: '#F59E0B' }, // Saffron → Gold
  { from: '#DC2626', to: '#F87171' }, // Red
  { from: '#059669', to: '#34D399' }, // Emerald
  { from: '#7C3AED', to: '#A78BFA' }, // Purple
  { from: '#2563EB', to: '#60A5FA' }, // Blue
  { from: '#0891B2', to: '#67E8F9' }, // Cyan
];

const formatCurrency = (value, intl = false) => {
  const sym = intl ? "$" : "₹";
  if (value === null || value === undefined) return `${sym}0`;
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  if (abs >= 10000000) return `${sign}${sym}${(abs / 10000000).toFixed(2)}Cr`;
  if (abs >= 100000) return `${sign}${sym}${(abs / 100000).toFixed(2)}L`;
  if (abs >= 1000) return `${sign}${sym}${(abs / 1000).toFixed(1)}K`;
  return `${sign}${sym}${abs.toFixed(0)}`;
};

const formatFullCurrency = (value, intl = false) => {
  const sym = intl ? "$" : "₹";
  if (value === null || value === undefined) return `${sym}0`;
  const sign = value < 0 ? '-' : '';
  return `${sign}${sym}${Math.abs(value).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
};

// Custom tooltip for charts
const PremiumTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-700/50 rounded-xl px-4 py-3 shadow-2xl">
      <p className="text-xs font-medium text-slate-400 mb-2">{label}</p>
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-slate-600">{entry.name}:</span>
          <span className="font-semibold text-white">{formatFullCurrency(entry.value)}</span>
        </div>
      ))}
    </div>
  );
};

export default function MISDashboard() {
  const { session } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(false);
  const [period, setPeriod] = useState("current_month");
  const [selectedCenter, setSelectedCenter] = useState("all");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [overview, setOverview] = useState(null);
  const [trends, setTrends] = useState([]);
  const [centerComparison, setCenterComparison] = useState([]);
  const [expenseAnalysis, setExpenseAnalysis] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [quarterlyData, setQuarterlyData] = useState([]);
  const [topPerformers, setTopPerformers] = useState(null);
  const [workingCapital, setWorkingCapital] = useState(null);
  const [totalWorkingCapital, setTotalWorkingCapital] = useState(0);
  const [centersList, setCentersList] = useState([]);
  const [alertThreshold, setAlertThreshold] = useState(20);
  const [showSettings, setShowSettings] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);

  useEffect(() => {
    const fetchCenters = async () => {
      try {
        const res = await api.get("/centers");
        setCentersList((res.data.centers || []).filter(c => c.active !== false));
      } catch {}
    };
    fetchCenters();
  }, []);

  const fetchData = useCallback(async () => {
    if (!session?.token) return;
    setLoading(true);
    try {
      const params = { token: session.token, period, center: selectedCenter, custom_start: customStart, custom_end: customEnd };
      const [overviewRes, trendsRes, centerRes, expenseRes, alertsRes, quarterRes, topRes, wcRes] = await Promise.all([
        api.post("/mis/overview", params),
        api.post("/mis/sales-trends", { ...params, group_by: period === "current_month" ? "daily" : "weekly" }),
        api.post("/mis/center-comparison", params),
        api.post("/mis/expense-analysis", params),
        api.post("/mis/alerts", { token: session.token, alert_threshold: alertThreshold, center: selectedCenter }),
        api.post("/mis/quarterly-comparison", { token: session.token, center: selectedCenter }),
        api.post("/mis/top-performers", params),
        api.post("/mis/working-capital", params)
      ]);
      setOverview(overviewRes.data);
      setTrends(trendsRes.data.trends || []);
      setCenterComparison(centerRes.data.centers || []);
      setExpenseAnalysis(expenseRes.data);
      setAlerts(alertsRes.data.alerts || []);
      setQuarterlyData(quarterRes.data.quarters || []);
      setTopPerformers(topRes.data);
      setWorkingCapital(wcRes.data || {});
      setTotalWorkingCapital(wcRes.data.available_working_capital || 0);
    } catch (err) {
      toast.error("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  }, [session?.token, period, selectedCenter, customStart, customEnd, alertThreshold]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => {
    const fetchSettings = async () => {
      if (session?.token) {
        try { const res = await api.post("/mis/get-alert-settings", { token: session.token }); setAlertThreshold(res.data.threshold || 20); } catch {}
      }
    };
    fetchSettings();
  }, [session?.token]);

  const saveAlertThreshold = async () => {
    try {
      await api.post("/mis/save-alert-settings", { token: session?.token, threshold: alertThreshold });
      toast.success("Alert threshold saved");
      setShowSettings(false);
      fetchData();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed to save"); }
  };

  // Excel Download
  const handleDownloadExcel = () => {
    if (!overview) { toast.error("No data to export"); return; }
    const wb = XLSX.utils.book_new();
    const cl = selectedCenter === "all" ? "All Centers" : selectedCenter;
    const pl = overview?.period?.start + " to " + overview?.period?.end;
    const s = overview?.summary;
    const ws1 = XLSX.utils.aoa_to_sheet([["MIS Report - Purnabramha"], ["Center", cl], ["Period", pl], [], ["Metric", "Value"],
      ["Total Sales", s?.total_sales], ["Cash Sales", s?.total_cash_sales], ["Online Sales", s?.total_online_sales],
      ["Total Expenses", s?.total_expenses], ["GST", s?.total_gst],
      ["Total Guests", s?.total_guests], ["Total Bills", s?.total_bills],
      ["Avg per Guest", s?.avg_per_guest], ["Avg per Bill", s?.avg_per_bill],
      ["Working Capital", workingCapital?.available_working_capital || "N/A"]]);
    XLSX.utils.book_append_sheet(wb, ws1, "Summary");
    if (overview?.centers?.length > 0) {
      const ws2 = XLSX.utils.aoa_to_sheet([["Center", "Sales", "Expenses", "GST"],
        ...overview.centers.map(c => [c.center, c.sales, c.expenses, c.gst])]);
      XLSX.utils.book_append_sheet(wb, ws2, "Centers");
    }
    if (trends.length > 0) {
      const ws3 = XLSX.utils.aoa_to_sheet([["Date", "Sales", "Expenses", "GST"],
        ...trends.map(t => [t.date || t.week || t.month, t.sales, t.expenses, t.gst])]);
      XLSX.utils.book_append_sheet(wb, ws3, "Trends");
    }
    if (expenseAnalysis?.by_type?.length > 0) {
      const ws4 = XLSX.utils.aoa_to_sheet([["Expense Head", "Amount", "% of Total", "Count", "Prev Period", "Change (%)"],
        ...expenseAnalysis.by_type.map(e => [e.type, e.amount, e.percentage, e.count, e.prev_amount, e.change])]);
      XLSX.utils.book_append_sheet(wb, ws4, "Expenses");
    }
    if (workingCapital?.centers?.length > 0) {
      const ws5 = XLSX.utils.aoa_to_sheet([
        ["Working Capital Summary"],
        ["Initial WC", workingCapital.initial_working_capital],
        ["Total Loans", workingCapital.total_loans],
        ["Total Repaid", workingCapital.total_repaid],
        ["Outstanding", workingCapital.total_outstanding],
        ["Available WC", workingCapital.available_working_capital],
        [],
        ["Center", "Franchise", "Initial WC", "Total Loans", "Repaid", "Outstanding", "Available"],
        ...workingCapital.centers.map(c => [c.center, c.franchise_name, c.initial_wc, c.total_loans, c.total_repaid, c.outstanding, c.available_wc]),
        [],
        ...(workingCapital.loan_timeline?.length > 0 ? [
          ["Loan Timeline"],
          ["Date", "Center", "Loan ID", "Type", "Description", "Amount", "Repaid", "Outstanding", "Status"],
          ...workingCapital.loan_timeline.map(l => [l.date, l.center, l.loan_id, l.type, l.description, l.amount, l.repaid, l.outstanding, l.status])
        ] : [])
      ]);
      XLSX.utils.book_append_sheet(wb, ws5, "Working Capital");
    }
    if (quarterlyData.length > 0) {
      const ws6 = XLSX.utils.aoa_to_sheet([["Quarter", "Sales", "Expenses", "GST"],
        ...quarterlyData.map(q => [q.label, q.sales, q.expenses, q.gst])]);
      XLSX.utils.book_append_sheet(wb, ws6, "Quarterly");
    }
    XLSX.writeFile(wb, `MIS_Report_${cl}_${overview?.period?.start}_to_${overview?.period?.end}.xlsx`.replace(/ /g, '_'));
    toast.success("Excel report downloaded");
  };

  // PDF Download
  const handleDownloadPDF = async () => {
    if (!overview) { toast.error("No data to export"); return; }
    setPdfLoading(true);
    try {
      const res = await api.post("/mis/download-pdf", {
        token: session.token, period, center: selectedCenter,
        custom_start: customStart, custom_end: customEnd
      }, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      const cl = selectedCenter === "all" ? "All_Centers" : selectedCenter;
      a.download = `MIS_Report_${cl}_${overview?.period?.start}_to_${overview?.period?.end}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("PDF report downloaded");
    } catch (err) {
      toast.error("PDF generation failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setPdfLoading(false);
    }
  };

  const isSuperAdmin = session?.is_super_admin;
  const isAdmin = session?.is_admin;
  const hasAccounting = session?.roles?.accounting;
  
  if (!isSuperAdmin && !isAdmin && !hasAccounting) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <AlertTriangle className="w-16 h-16 text-red-500 mb-4" />
        <h2 className="text-xl font-bold mb-2">Access Denied</h2>
        <p className="text-muted-foreground">Only Admin or Accounts users can access MIS Dashboard.</p>
      </div>
    );
  }

  const s = overview?.summary;
  const centerLabel = selectedCenter === "all" ? "All Centers" : selectedCenter;
  const centerObj = centersList.find(c => c.code === selectedCenter);
  const isIntl = centerObj?.is_india_center === false;

  const kpiCards = s ? [
    { label: "Total Sales", value: s.total_sales, change: overview?.changes?.sales_change, icon: IndianRupee, gradient: "from-emerald-600 to-emerald-400", textColor: "text-emerald-50", changeBad: false },
    { label: "Total Expenses", value: s.total_expenses, change: overview?.changes?.expenses_change, icon: Receipt, gradient: "from-red-600 to-red-400", textColor: "text-red-50", changeBad: true },
    { label: "Commissions", value: null, displayValue: formatFullCurrency(s.total_commissions || 0, isIntl), icon: Receipt, gradient: "from-purple-600 to-purple-400", textColor: "text-purple-50" },
    { label: "Net Profit", value: null, displayValue: formatFullCurrency(s.profit || 0, isIntl), change: overview?.changes?.profit_change, icon: Activity, gradient: s.profit >= 0 ? "from-emerald-700 to-emerald-500" : "from-red-700 to-red-500", textColor: "text-emerald-50" },
    { label: "Working Capital", value: null, displayValue: formatFullCurrency(workingCapital?.available_working_capital || 0, isIntl), icon: Wallet, gradient: "from-amber-600 to-amber-400", textColor: "text-amber-50" },
    { label: "Avg / Bill", value: null, displayValue: formatFullCurrency(s.avg_per_bill, isIntl), icon: Activity, gradient: "from-teal-600 to-teal-400", textColor: "text-teal-50" },
  ] : [];

  return (
    <div className="space-y-6" data-testid="mis-dashboard">
      {/* Data availability banner — shown when the selected period has no data */}
      {overview?.data_availability && !overview.data_availability.has_data_in_range && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-700/50 p-4 flex items-start gap-3" data-testid="data-availability-banner">
          <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-800 flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-amber-700 dark:text-amber-300" />
          </div>
          <div className="flex-1 text-sm">
            {overview.data_availability.earliest_month ? (
              <>
                <p className="font-semibold text-amber-900 dark:text-amber-100">
                  No data for the selected range.
                </p>
                <p className="text-amber-800 dark:text-amber-200 mt-0.5">
                  Data available from <strong>{new Date(overview.data_availability.earliest_month + "-01").toLocaleDateString("en-IN", { month: "long", year: "numeric" })}</strong> onwards. Previous data not available in system.
                </p>
              </>
            ) : (
              <>
                <p className="font-semibold text-amber-900 dark:text-amber-100">
                  No data available for this center yet.
                </p>
                <p className="text-amber-800 dark:text-amber-200 mt-0.5">
                  Either upload historical files via <em>Accounts → Historical Import</em>, or enter daily sales/expenses for the current month.
                </p>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── HEADER ── */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 rounded-2xl p-6 border border-slate-700/40">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
                <BarChart3 className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white tracking-tight">MIS Dashboard</h1>
                <p className="text-sm text-slate-400">
                  {centerLabel} &middot; {overview?.period?.start || "..."} to {overview?.period?.end || "..."}
                </p>
              </div>
            </div>
          </div>
          
          <div className="flex flex-wrap items-center gap-2">
            <Select value={period} onValueChange={setPeriod}>
              <SelectTrigger className="w-[150px] bg-slate-800/80 border-slate-600 text-white text-sm h-9">
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
              <SelectTrigger className="w-[130px] bg-slate-800/80 border-slate-600 text-white text-sm h-9" data-testid="mis-center-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Centers</SelectItem>
                {centersList.map(c => (
                  <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            {period === "custom" && (
              <>
                <Input type="date" value={customStart} onChange={(e) => setCustomStart(e.target.value)} className="w-[130px] bg-slate-800/80 border-slate-600 text-white text-sm h-9" />
                <Input type="date" value={customEnd} onChange={(e) => setCustomEnd(e.target.value)} className="w-[130px] bg-slate-800/80 border-slate-600 text-white text-sm h-9" />
              </>
            )}
            
            <Button variant="outline" size="sm" onClick={fetchData} disabled={loading} className="h-9 border-slate-600 text-slate-600 hover:text-white hover:bg-slate-700" data-testid="mis-refresh-btn">
              <RefreshCw className={`w-4 h-4 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            
            <Button size="sm" onClick={handleDownloadPDF} disabled={pdfLoading || loading} className="h-9 bg-amber-600 hover:bg-amber-500 text-white shadow-lg shadow-amber-600/20" data-testid="mis-download-pdf-btn">
              <FileText className={`w-4 h-4 mr-1.5 ${pdfLoading ? 'animate-pulse' : ''}`} />
              {pdfLoading ? "Generating..." : "PDF"}
            </Button>
            
            <Button variant="outline" size="sm" onClick={handleDownloadExcel} disabled={loading} className="h-9 border-slate-600 text-slate-600 hover:text-white hover:bg-slate-700" data-testid="mis-download-btn">
              <Download className="w-4 h-4 mr-1.5" />
              Excel
            </Button>
            
            {isSuperAdmin && (
              <Button variant="ghost" size="icon" onClick={() => setShowSettings(!showSettings)} className="h-9 w-9 text-slate-400 hover:text-white">
                <Settings className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Alert Settings */}
      {showSettings && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Label className="text-amber-200">Alert Threshold (%)</Label>
              <Input type="number" value={alertThreshold} onChange={(e) => setAlertThreshold(parseInt(e.target.value) || 20)} className="w-20 bg-slate-800 border-slate-600 text-white" />
              <span className="text-sm text-slate-400">Trigger alerts when expenses increase by more than {alertThreshold}%</span>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowSettings(false)}>Cancel</Button>
              <Button size="sm" onClick={saveAlertThreshold} className="bg-amber-600 hover:bg-amber-500">Save</Button>
            </div>
          </div>
        </div>
      )}

      {/* Alerts Banner */}
      {alerts.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-red-100 flex items-center justify-center flex-shrink-0">
              <Bell className="w-4 h-4 text-red-400" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-red-300 text-sm mb-2">{alerts.length} Alert{alerts.length > 1 ? 's' : ''} Detected</h3>
              <div className="flex flex-wrap gap-1.5">
                {alerts.slice(0, 5).map((alert, i) => (
                  <Badge key={i} className={`text-xs font-medium ${alert.severity === 'high' ? 'bg-red-500/80' : 'bg-amber-500/80'}`}>
                    {alert.entity}: +{alert.change?.toFixed(1)}%
                  </Badge>
                ))}
                {alerts.length > 5 && <Badge variant="outline" className="text-xs border-red-500/30 text-red-300">+{alerts.length - 5} more</Badge>}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── KPI CARDS ── */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {kpiCards.map((kpi, i) => {
            const Icon = kpi.icon;
            const displayVal = kpi.displayValue || formatCurrency(kpi.value, isIntl);
            return (
              <div
                key={i}
                className={`relative overflow-hidden rounded-xl bg-gradient-to-br ${kpi.gradient} p-4 shadow-lg transition-transform hover:scale-[1.02]`}
                style={{ animationDelay: `${i * 60}ms` }}
                data-testid={`kpi-${kpi.label.toLowerCase().replace(/ /g, '-')}`}
              >
                {/* Decorative circle */}
                <div className="absolute -right-3 -top-3 w-16 h-16 rounded-full bg-white/10" />
                <div className="absolute -right-1 -bottom-4 w-12 h-12 rounded-full bg-white/5" />
                
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-2">
                    <p className={`text-xs font-medium ${kpi.textColor} opacity-80`}>{kpi.label}</p>
                    <Icon className={`w-4 h-4 ${kpi.textColor} opacity-60`} />
                  </div>
                  <p className={`text-xl font-bold ${kpi.textColor} tracking-tight`}>
                    {displayVal}
                  </p>
                  {kpi.change !== undefined && (
                    <div className={`flex items-center gap-1 mt-1 text-xs font-medium ${kpi.textColor} opacity-70`}>
                      {kpi.change > 0 ? <ArrowUpRight className="w-3 h-3" /> : kpi.change < 0 ? <ArrowDownRight className="w-3 h-3" /> : null}
                      {kpi.change?.toFixed(1)}% vs prev
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── TABS ── */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-slate-100 border border-slate-200 rounded-xl p-1 flex-wrap">
          {["overview", "working-capital", "centers", "expenses", "alerts", "quarterly", "performers"].map(tab => (
            <TabsTrigger key={tab} value={tab} className="rounded-lg text-xs capitalize data-[state=active]:bg-amber-600 data-[state=active]:text-white">
              {tab.replace("-", " ")}
            </TabsTrigger>
          ))}
        </TabsList>

        {/* ── OVERVIEW TAB ── */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Sales vs Expenses Trend */}
            <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold text-slate-800">Sales vs Expenses Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={trends}>
                    <defs>
                      <linearGradient id="salesGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#059669" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#059669" stopOpacity={0.02}/>
                      </linearGradient>
                      <linearGradient id="expGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#DC2626" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#DC2626" stopOpacity={0.02}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#CBD5E1" />
                    <XAxis dataKey={period === "current_month" ? "date" : "week"} stroke="#64748B" fontSize={10} tickLine={false} />
                    <YAxis stroke="#64748B" fontSize={10} tickLine={false} tickFormatter={(v) => formatCurrency(v, isIntl)} />
                    <Tooltip content={<PremiumTooltip />} />
                    <Legend wrapperStyle={{ fontSize: '12px' }} />
                    <Area type="monotone" dataKey="sales" fill="url(#salesGrad)" stroke="#059669" strokeWidth={2.5} name="Sales" />
                    <Area type="monotone" dataKey="expenses" fill="url(#expGrad)" stroke="#DC2626" strokeWidth={2} name="Expenses" />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Pie Chart */}
            <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold text-slate-800">Sales by Center</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie data={centerComparison} dataKey="sales" nameKey="center" cx="50%" cy="50%" innerRadius={60} outerRadius={110} paddingAngle={2}
                      label={({ center, percent }) => `${center} (${(percent * 100).toFixed(0)}%)`}
                      labelLine={{ stroke: '#64748B' }}
                    >
                      {centerComparison.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} stroke="transparent" />
                      ))}
                    </Pie>
                    <Tooltip content={<PremiumTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Center Performance Table */}
          <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold text-slate-800">Center Performance Summary</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm" data-testid="center-perf-table">
                  <thead>
                    <tr className="bg-slate-100/80">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Center</th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Sales</th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Expenses</th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">GST</th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Commission</th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Profit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview?.centers?.map((c, i) => (
                      <tr key={i} className="border-t border-slate-200/60 hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3 font-semibold text-slate-800">{c.center}</td>
                        <td className="px-4 py-3 text-right font-medium text-emerald-400">{formatCurrency(c.sales, isIntl)}</td>
                        <td className="px-4 py-3 text-right font-medium text-red-400">{formatCurrency(c.expenses, isIntl)}</td>
                        <td className="px-4 py-3 text-right text-amber-400">{formatCurrency(c.gst, isIntl)}</td>
                        <td className="px-4 py-3 text-right text-purple-400">{formatCurrency(c.commissions || 0, isIntl)}</td>
                        <td className={`px-4 py-3 text-right font-bold ${(c.profit || 0) >= 0 ? "text-emerald-500" : "text-red-500"}`}>{formatCurrency(c.profit || 0, isIntl)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Day-wise Sales Table */}
          <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold text-slate-800">Day-wise Sales</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                <table className="w-full text-sm" data-testid="day-wise-table">
                  <thead className="sticky top-0 bg-slate-100/90 backdrop-blur">
                    <tr>
                      <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase">Date</th>
                      <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase">Sales</th>
                      <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase">Expenses</th>
                      <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase">GST</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trends.map((d, i) => (
                      <tr key={i} className={`border-t border-slate-200/60 ${i % 2 ? 'bg-slate-50' : ''} hover:bg-slate-50`}>
                        <td className="px-4 py-2 text-slate-600">{d.date || d.week}</td>
                        <td className="px-4 py-2 text-right text-emerald-400">{formatCurrency(d.sales, isIntl)}</td>
                        <td className="px-4 py-2 text-right text-red-400">{formatCurrency(d.expenses, isIntl)}</td>
                        <td className="px-4 py-2 text-right text-amber-400">{formatCurrency(d.gst, isIntl)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Month-wise Sales Chart */}
          {quarterlyData.length > 0 && (
            <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold text-slate-800">Month / Quarter-wise Sales Comparison</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={quarterlyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#CBD5E1" />
                    <XAxis dataKey="label" stroke="#64748B" fontSize={11} />
                    <YAxis stroke="#64748B" fontSize={10} tickFormatter={(v) => formatCurrency(v, isIntl)} />
                    <Tooltip content={<PremiumTooltip />} />
                    <Legend wrapperStyle={{ fontSize: '12px' }} />
                    <Bar dataKey="sales" fill="#059669" name="Sales" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="expenses" fill="#DC2626" name="Expenses" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ── WORKING CAPITAL TAB ── */}
        <TabsContent value="working-capital" className="space-y-6">
          {/* WC Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="rounded-xl p-5 bg-white border border-slate-200">
              <p className="text-xs font-medium text-slate-500 mb-1">Initial Working Capital</p>
              <p className="text-2xl font-bold text-slate-900" data-testid="initial-wc">
                {formatFullCurrency(workingCapital?.initial_working_capital || 0, isIntl)}
              </p>
              <p className="text-xs text-slate-500 mt-1">Franchise deposit</p>
            </div>
            <div className={`rounded-xl p-5 border ${(workingCapital?.available_working_capital || 0) >= (workingCapital?.initial_working_capital || 0) ? 'bg-white border-slate-200' : (workingCapital?.available_working_capital || 0) > 0 ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200'}`}>
              <p className="text-xs font-medium text-slate-500 mb-1">Current Working Capital</p>
              <p className={`text-2xl font-bold ${(workingCapital?.available_working_capital || 0) >= (workingCapital?.initial_working_capital || 0) ? 'text-green-700' : (workingCapital?.available_working_capital || 0) > 0 ? 'text-amber-700' : 'text-red-700'}`} data-testid="total-working-capital">
                {formatFullCurrency(workingCapital?.available_working_capital || 0, isIntl)}
              </p>
              <p className="text-xs text-slate-500 mt-1">As of {workingCapital?.up_to_month || 'current month'}</p>
            </div>
            <div className="rounded-xl p-5 bg-white border border-slate-200">
              <p className="text-xs font-medium text-slate-500 mb-1">Total Loans Outstanding</p>
              <p className="text-2xl font-bold text-orange-600">
                {formatFullCurrency(workingCapital?.total_outstanding || 0, isIntl)}
              </p>
              <p className="text-xs text-slate-500 mt-1">Drawn against WC</p>
            </div>
            <div className="rounded-xl p-5 bg-white border border-slate-200">
              <p className="text-xs font-medium text-slate-500 mb-1">WC vs Initial</p>
              <p className={`text-2xl font-bold ${(workingCapital?.available_working_capital || 0) >= (workingCapital?.initial_working_capital || 0) ? 'text-green-600' : 'text-red-600'}`}>
                {workingCapital?.initial_working_capital > 0 
                  ? `${((workingCapital?.available_working_capital || 0) / workingCapital.initial_working_capital * 100).toFixed(0)}%`
                  : 'N/A'}
              </p>
              <p className="text-xs text-slate-500 mt-1">
                {(workingCapital?.available_working_capital || 0) >= (workingCapital?.initial_working_capital || 0) ? 'Healthy' : 'Below initial deposit'}
              </p>
            </div>
          </div>

          {/* Cash Inflows (Non-Operating) */}
          {((workingCapital?.total_other_income || 0) > 0 ||
            (workingCapital?.total_loans_taken || 0) > 0 ||
            (workingCapital?.total_loans_given || 0) > 0) && (
            <Card className="bg-white border-slate-200/60 rounded-xl" data-testid="cash-inflows-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold text-slate-800 flex items-center gap-2">
                  <Wallet className="w-4 h-4 text-emerald-500" /> Cash Inflows (Non-Operating) & Inter-Center Loans
                </CardTitle>
                <p className="text-xs text-slate-500">
                  Does <strong>not</strong> affect Sales / P&amp;L / Revenue Share.
                  Other Income adjusts next-month Opening Working Capital.
                </p>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="rounded-lg p-4 bg-emerald-50 border border-emerald-200" data-testid="mis-other-income-card">
                    <p className="text-xs font-medium text-emerald-700 uppercase tracking-wide">Other Income</p>
                    <p className="text-2xl font-bold text-emerald-800 mt-1">
                      {formatFullCurrency(workingCapital?.total_other_income || 0, isIntl)}
                    </p>
                    <p className="text-[11px] text-emerald-700/70 mt-1">
                      Vendor refunds, repayments, loan-taken entries
                    </p>
                  </div>
                  <div className="rounded-lg p-4 bg-amber-50 border border-amber-200" data-testid="mis-loans-taken-card">
                    <p className="text-xs font-medium text-amber-700 uppercase tracking-wide">Loans Taken</p>
                    <p className="text-2xl font-bold text-amber-800 mt-1">
                      {formatFullCurrency(workingCapital?.total_loans_taken || 0, isIntl)}
                    </p>
                    <p className="text-[11px] text-amber-700/70 mt-1">
                      Outstanding: <strong>{formatFullCurrency(workingCapital?.total_loans_taken_outstanding || 0, isIntl)}</strong>
                    </p>
                  </div>
                  <div className="rounded-lg p-4 bg-rose-50 border border-rose-200" data-testid="mis-loans-given-card">
                    <p className="text-xs font-medium text-rose-700 uppercase tracking-wide">Loans Given</p>
                    <p className="text-2xl font-bold text-rose-800 mt-1">
                      {formatFullCurrency(workingCapital?.total_loans_given || 0, isIntl)}
                    </p>
                    <p className="text-[11px] text-rose-700/70 mt-1">
                      Outstanding: <strong>{formatFullCurrency(workingCapital?.total_loans_given_outstanding || 0, isIntl)}</strong>
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Center-wise WC Breakdown */}
          {workingCapital?.centers?.length > 0 && (
            <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur overflow-hidden">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold text-slate-800 flex items-center gap-2">
                  <Wallet className="w-4 h-4 text-amber-400" /> Center-wise Working Capital
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-100">
                      <tr>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase">Center</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase">Franchise</th>
                        <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase">Initial WC</th>
                        <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase">Current WC</th>
                        <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase">This Month P/L</th>
                        <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase">Loans</th>
                        <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {workingCapital.centers.map((c, i) => (
                        <tr key={i} className={`border-t border-slate-200/60 ${i % 2 === 0 ? '' : 'bg-slate-50'}`}>
                          <td className="px-4 py-2.5 text-slate-800 font-medium">{c.center}</td>
                          <td className="px-4 py-2.5 text-slate-400">{c.franchise_name}</td>
                          <td className="px-4 py-2.5 text-right text-slate-600">{formatCurrency(c.initial_wc, isIntl)}</td>
                          <td className={`px-4 py-2.5 text-right font-semibold ${c.current_wc >= c.initial_wc ? 'text-green-700' : c.current_wc > 0 ? 'text-amber-700' : 'text-red-700'}`}>
                            {formatCurrency(c.current_wc || c.available_wc, isIntl)}
                          </td>
                          <td className={`px-4 py-2.5 text-right ${(c.this_month_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {(c.this_month_pnl || 0) >= 0 ? '+' : ''}{formatCurrency(c.this_month_pnl || 0, isIntl)}
                          </td>
                          <td className="px-4 py-2.5 text-right text-orange-600">
                            {c.loans_outstanding > 0 ? formatCurrency(c.loans_outstanding, isIntl) : '-'}
                          </td>
                          <td className="px-4 py-2.5 text-center">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                              c.wc_status === 'healthy' ? 'bg-green-100 text-green-700' :
                              c.wc_status === 'restoring' ? 'bg-amber-100 text-amber-700' :
                              'bg-red-100 text-red-700'
                            }`}>
                              {c.wc_status === 'healthy' ? 'Healthy' : c.wc_status === 'restoring' ? 'Restoring' : 'Stopped'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Loan Timeline */}
          {workingCapital?.loan_timeline?.length > 0 ? (
            <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur overflow-hidden">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold text-slate-800">Loan Activity Timeline</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-slate-100/90 backdrop-blur">
                      <tr>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase">Date</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase">Center</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase">Type</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase">Description</th>
                        <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase">Amount</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {workingCapital.loan_timeline.map((l, i) => (
                        <tr key={i} className={`border-t border-slate-200/60 ${i % 2 === 0 ? '' : 'bg-slate-50'}`}>
                          <td className="px-4 py-2 text-slate-600">{l.date}</td>
                          <td className="px-4 py-2 text-slate-600">{l.center}</td>
                          <td className="px-4 py-2">
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                              l.type === 'loan' ? 'bg-orange-100 text-orange-700' : 'bg-teal-100 text-teal-700'
                            }`}>
                              {l.type === 'loan' ? 'Loan' : 'Repayment'}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-slate-400">{l.description}</td>
                          <td className={`px-4 py-2 text-right font-medium ${l.type === 'loan' ? 'text-orange-600' : 'text-teal-600'}`}>
                            {l.type === 'repayment' ? '+' : ''}{formatCurrency(l.amount, isIntl)}
                          </td>
                          <td className="px-4 py-2">
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              l.status === 'fully_repaid' ? 'bg-teal-100 text-teal-700' :
                              l.status === 'partially_repaid' ? 'bg-amber-100 text-amber-700' :
                              l.status === 'repaid' ? 'bg-teal-100 text-teal-700' :
                              'bg-slate-100 text-slate-600'
                            }`}>
                              {l.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur">
              <CardContent className="py-12 text-center">
                <Wallet className="w-10 h-10 mx-auto mb-3 text-slate-600" />
                <p className="text-slate-400 text-sm">No loan entries found.</p>
                <p className="text-slate-500 text-xs mt-1">Working capital remains fully intact until loans are drawn against it.</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ── CENTER ANALYSIS TAB ── */}
        <TabsContent value="centers" className="space-y-6">
          <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur">
            <CardHeader className="pb-2"><CardTitle className="text-base font-semibold text-slate-800">Center Comparison</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={centerComparison} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#CBD5E1" />
                  <XAxis type="number" stroke="#64748B" tickFormatter={(v) => formatCurrency(v, isIntl)} />
                  <YAxis dataKey="center" type="category" stroke="#64748B" width={80} fontSize={11} />
                  <Tooltip content={<PremiumTooltip />} />
                  <Legend wrapperStyle={{ fontSize: '12px' }} />
                  <Bar dataKey="sales" fill="#059669" name="Sales" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="expenses" fill="#DC2626" name="Expenses" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur overflow-hidden">
            <CardHeader className="pb-2"><CardTitle className="text-base font-semibold text-slate-800">Growth vs Previous Period</CardTitle></CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="bg-slate-100/80">
                    {["Center", "Current Sales", "Prev Sales", "Sales Change", "Current Exp", "Prev Exp", "Exp Change"].map(h => (
                      <th key={h} className={`${h === "Center" ? "text-left" : "text-right"} px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider`}>{h}</th>
                    ))}
                  </tr></thead>
                  <tbody>
                    {centerComparison.map((c, i) => (
                      <tr key={i} className="border-t border-slate-200/60 hover:bg-slate-50">
                        <td className="px-4 py-3 font-semibold text-slate-800">{c.center}</td>
                        <td className="px-4 py-3 text-right text-emerald-400">{formatCurrency(c.sales, isIntl)}</td>
                        <td className="px-4 py-3 text-right text-slate-500">{formatCurrency(c.prev_sales, isIntl)}</td>
                        <td className={`px-4 py-3 text-right font-bold ${c.sales_change > 0 ? 'text-emerald-400' : c.sales_change < 0 ? 'text-red-400' : 'text-slate-400'}`}>
                          {c.sales_change > 0 ? '+' : ''}{c.sales_change?.toFixed(1)}%
                        </td>
                        <td className="px-4 py-3 text-right text-red-400">{formatCurrency(c.expenses, isIntl)}</td>
                        <td className="px-4 py-3 text-right text-slate-500">{formatCurrency(c.prev_expenses, isIntl)}</td>
                        <td className={`px-4 py-3 text-right font-bold ${c.expenses_change > 10 ? 'text-red-400' : c.expenses_change < -10 ? 'text-emerald-400' : 'text-amber-400'}`}>
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

        {/* ── EXPENSE ANALYSIS TAB ── */}
        <TabsContent value="expenses" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur">
              <CardHeader className="pb-2"><CardTitle className="text-base font-semibold text-slate-800">Expense Distribution</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie data={expenseAnalysis?.by_type || []} dataKey="amount" nameKey="type" cx="50%" cy="50%" innerRadius={50} outerRadius={110} paddingAngle={1}
                      label={({ type, percentage }) => `${type} (${percentage}%)`} labelLine={{ stroke: '#64748B' }}>
                      {(expenseAnalysis?.by_type || []).map((entry, index) => (
                        <Cell key={index} fill={entry.alert === 'high' ? '#DC2626' : entry.alert === 'medium' ? '#D97706' : CHART_COLORS[index % CHART_COLORS.length]} stroke="transparent" />
                      ))}
                    </Pie>
                    <Tooltip content={<PremiumTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur">
              <CardHeader className="pb-2"><CardTitle className="text-base font-semibold text-slate-800">Expenses by Category</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={expenseAnalysis?.by_type || []} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#CBD5E1" />
                    <XAxis type="number" stroke="#64748B" tickFormatter={(v) => formatCurrency(v, isIntl)} />
                    <YAxis dataKey="type" type="category" stroke="#64748B" width={100} fontSize={10} />
                    <Tooltip content={<PremiumTooltip />} />
                    <Bar dataKey="amount" name="Amount" radius={[0, 4, 4, 0]}>
                      {(expenseAnalysis?.by_type || []).map((e, i) => (
                        <Cell key={i} fill={e.alert === 'high' ? '#DC2626' : e.alert === 'medium' ? '#D97706' : '#7C3AED'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur overflow-hidden">
            <CardHeader className="pb-2"><CardTitle className="text-base font-semibold text-slate-800">Expense Head Analysis</CardTitle></CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="bg-slate-100/80">
                    {["Expense Head", "Amount", "% of Total", "Count", "Prev Period", "Change", "Status"].map(h => (
                      <th key={h} className={`${h === "Expense Head" ? "text-left" : "text-right"} px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider`}>{h}</th>
                    ))}
                  </tr></thead>
                  <tbody>
                    {expenseAnalysis?.by_type?.map((exp, i) => (
                      <tr key={i} className={`border-t border-slate-200/60 ${i % 2 ? 'bg-slate-50' : ''}`}>
                        <td className="px-4 py-2.5 font-medium text-slate-800">{exp.type}</td>
                        <td className="px-4 py-2.5 text-right font-medium text-slate-600">{formatCurrency(exp.amount, isIntl)}</td>
                        <td className="px-4 py-2.5 text-right text-slate-400">{exp.percentage}%</td>
                        <td className="px-4 py-2.5 text-right text-slate-400">{exp.count}</td>
                        <td className="px-4 py-2.5 text-right text-slate-500">{formatCurrency(exp.prev_amount, isIntl)}</td>
                        <td className={`px-4 py-2.5 text-right font-bold ${exp.change > 10 ? 'text-red-400' : exp.change < -10 ? 'text-emerald-400' : 'text-amber-400'}`}>
                          {exp.change > 0 ? '+' : ''}{exp.change?.toFixed(1)}%
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${
                            exp.alert === 'high' ? 'bg-red-100 text-red-700' : exp.alert === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'
                          }`}>{exp.alert === 'high' ? 'Alert' : exp.alert === 'medium' ? 'Watch' : 'Normal'}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── ALERTS TAB ── */}
        <TabsContent value="alerts" className="space-y-6">
          <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur">
            <CardHeader><CardTitle className="text-base font-semibold text-slate-800 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-amber-400" /> Expense Alerts</CardTitle></CardHeader>
            <CardContent>
              {alerts.length === 0 ? (
                <div className="text-center py-10">
                  <CheckCircle className="w-14 h-14 text-emerald-500 mx-auto mb-3 opacity-60" />
                  <p className="text-slate-400">All expenses within acceptable limits</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {alerts.map((alert, i) => (
                    <div key={i} className={`p-4 rounded-xl border ${alert.severity === 'high' ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200'}`}>
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3">
                          {alert.severity === 'high' ? <XCircle className="w-5 h-5 text-red-400 mt-0.5" /> : <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5" />}
                          <div>
                            <p className="font-medium text-slate-800 text-sm">{alert.message}</p>
                            <p className="text-xs text-slate-500 mt-1">{alert.type === 'center' ? 'Center' : 'Expense Head'}: {alert.entity}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-slate-600">Current: {formatCurrency(alert.current, isIntl)}</p>
                          <p className="text-xs text-slate-500">Previous: {formatCurrency(alert.previous, isIntl)}</p>
                          <span className={`inline-flex mt-1 px-2 py-0.5 rounded-full text-xs font-bold ${alert.severity === 'high' ? 'bg-red-500/30 text-red-300' : 'bg-amber-500/30 text-amber-300'}`}>+{alert.change?.toFixed(1)}%</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── QUARTERLY TAB ── */}
        <TabsContent value="quarterly" className="space-y-6">
          <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur">
            <CardHeader className="pb-2"><CardTitle className="text-base font-semibold text-slate-800">Quarterly Performance</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={380}>
                <ComposedChart data={quarterlyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#CBD5E1" />
                  <XAxis dataKey="label" stroke="#64748B" fontSize={11} />
                  <YAxis stroke="#64748B" fontSize={10} tickFormatter={(v) => formatCurrency(v, isIntl)} />
                  <Tooltip content={<PremiumTooltip />} />
                  <Legend wrapperStyle={{ fontSize: '12px' }} />
                  <Bar dataKey="sales" fill="#059669" name="Sales" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="expenses" fill="#DC2626" name="Expenses" radius={[4, 4, 0, 0]} />
                </ComposedChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="bg-white border-slate-200/60 rounded-xl backdrop-blur overflow-hidden">
            <CardHeader className="pb-2"><CardTitle className="text-base font-semibold text-slate-800">Quarter-wise Breakdown</CardTitle></CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="bg-slate-100/80">
                    {["Quarter", "Sales", "Expenses", "GST"].map(h => (
                      <th key={h} className={`${h === "Quarter" ? "text-left" : "text-right"} px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider`}>{h}</th>
                    ))}
                  </tr></thead>
                  <tbody>
                    {quarterlyData.map((q, i) => (
                      <tr key={i} className={`border-t border-slate-200/60 ${i % 2 ? 'bg-slate-50' : ''}`}>
                        <td className="px-4 py-2.5 font-semibold text-slate-800">{q.label}</td>
                        <td className="px-4 py-2.5 text-right text-emerald-400">{formatCurrency(q.sales, isIntl)}</td>
                        <td className="px-4 py-2.5 text-right text-red-400">{formatCurrency(q.expenses, isIntl)}</td>
                        <td className="px-4 py-2.5 text-right text-amber-400">{formatCurrency(q.gst, isIntl)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── PERFORMERS TAB ── */}
        <TabsContent value="performers" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {[
              { title: "Top by Sales", data: topPerformers?.top_by_sales, field: "sales", color: "emerald", format: true },
              { title: "Top by Guests", data: topPerformers?.top_by_sales, field: "guests", color: "sky", format: false },
              { title: "Needs Attention (Low Sales)", data: topPerformers?.bottom_by_sales, field: "sales", color: "orange", format: true },
              { title: "Highest Expenses", data: topPerformers?.top_by_sales?.sort?.((a, b) => (b.expenses || 0) - (a.expenses || 0))?.slice(0, 5), field: "expenses", color: "red", format: true },
            ].map((section, si) => (
              <Card key={si} className="bg-white border-slate-200/60 rounded-xl backdrop-blur">
                <CardHeader className="pb-2">
                  <CardTitle className={`text-base font-semibold text-${section.color}-400`}>{section.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {section.data?.map((c, i) => (
                      <div key={i} className={`flex items-center justify-between p-3 rounded-lg bg-${section.color}-500/10 border border-${section.color}-500/10`}>
                        <div className="flex items-center gap-3">
                          <span className={`w-7 h-7 rounded-lg bg-${section.color}-500/20 flex items-center justify-center text-sm font-bold text-${section.color}-400`}>
                            {i + 1}
                          </span>
                          <span className="font-medium text-slate-800">{c.center}</span>
                        </div>
                        <span className={`font-bold text-${section.color}-400`}>
                          {section.format ? formatCurrency(c[section.field], isIntl) : `${c[section.field]?.toFixed(1)}${section.suffix || ''}`}
                        </span>
                      </div>
                    ))}
                    {(!section.data || section.data.length === 0) && (
                      <p className="text-slate-500 text-center py-4 text-sm">No data available</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
