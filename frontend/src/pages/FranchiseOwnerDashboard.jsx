import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ComposedChart, Area
} from "recharts";
import {
  BarChart3, Download, IndianRupee, Receipt, FileText, Store, Calendar,
  TrendingUp, TrendingDown, Loader2, UserCheck, FileDown, Wallet,
  Activity, ArrowUpRight, ArrowDownRight, Percent
} from "lucide-react";
import { api } from "@/lib/api";
import * as XLSX from "xlsx";

const CHART_COLORS = ['#D97706', '#059669', '#7C3AED', '#DC2626', '#2563EB', '#F59E0B', '#10B981', '#8B5CF6'];

const formatCurrency = (value, intl = false) => {
  const sym = intl ? "$" : "\u20B9";
  if (value === null || value === undefined) return `${sym}0`;
  const abs = Math.abs(value);
  if (abs >= 10000000) return `${value < 0 ? '-' : ''}${sym}${(abs / 10000000).toFixed(2)}Cr`;
  if (abs >= 100000) return `${value < 0 ? '-' : ''}${sym}${(abs / 100000).toFixed(2)}L`;
  if (abs >= 1000) return `${value < 0 ? '-' : ''}${sym}${(abs / 1000).toFixed(1)}K`;
  return `${value < 0 ? '-' : ''}${sym}${abs.toFixed(0)}`;
};

const formatFullCurrency = (value, intl = false) => {
  const sym = intl ? "$" : "\u20B9";
  if (value === null || value === undefined) return `${sym}0`;
  const sign = value < 0 ? '-' : '';
  return `${sign}${sym}${Math.abs(value).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
};

const PremiumTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-700/50 rounded-xl px-4 py-3 shadow-2xl">
      <p className="text-xs font-medium text-slate-400 mb-2">{label}</p>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: p.color }} />
          <span className="text-slate-300">{p.name}:</span>
          <span className="font-bold text-white">{formatFullCurrency(p.value)}</span>
        </div>
      ))}
    </div>
  );
};

export default function FranchiseOwnerDashboard() {
  const { session } = useAuth();
  const isFranchiseOwner = session?.role_key === "franchise_owner";
  const isAdmin = session?.is_super_admin || session?.is_admin;
  const canSelectCenter = isAdmin; // Only admin/super admin can switch centers

  const [selectedCenter, setSelectedCenter] = useState("");
  const [centersList, setCentersList] = useState([]);
  const [period, setPeriod] = useState("custom");
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [useRange, setUseRange] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");

  // Data states
  const [overview, setOverview] = useState(null);
  const [salesData, setSalesData] = useState([]);
  const [expenseData, setExpenseData] = useState([]);
  const [workingCapital, setWorkingCapital] = useState(null);
  const [franchiseInfo, setFranchiseInfo] = useState(null);
  const [franchiseDocs, setFranchiseDocs] = useState([]);

  // Owner Ledger (published by Admin/Accounts team)
  const [showOwnerLedgers, setShowOwnerLedgers] = useState(false);
  const [ownerLedgerMonths, setOwnerLedgerMonths] = useState([]);
  const [ownerLedgerLoading, setOwnerLedgerLoading] = useState(false);

  const [ledgerLabels, setLedgerLabels] = useState({});

  // Fetch released owner ledgers when modal opens
  useEffect(() => {
    if (!showOwnerLedgers || !session?.token || !selectedCenter) return;
    const fetchOL = async () => {
      setOwnerLedgerLoading(true);
      try {
        const API = process.env.REACT_APP_BACKEND_URL;
        const res = await fetch(`${API}/api/ledgers/owner/list`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: session.token, center: selectedCenter })
        });
        const data = await res.json();
        setOwnerLedgerMonths(data.months || []);
        setLedgerLabels(data.ledger_labels || {});
      } catch {
        toast.error('Could not fetch released ledgers');
      } finally {
        setOwnerLedgerLoading(false);
      }
    };
    fetchOL();
  }, [showOwnerLedgers, session?.token, selectedCenter]);

  const [previewBlobUrl, setPreviewBlobUrl] = useState(null);
  const [previewTitle, setPreviewTitle] = useState("");

  const previewLedger = async (month, ltype) => {
    try {
      const API = process.env.REACT_APP_BACKEND_URL;
      const res = await fetch(`${API}/api/ledgers/${ltype}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, center: selectedCenter, period_type: 'month', month, fmt: 'pdf' })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || 'Preview failed');
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setPreviewBlobUrl(url);
      setPreviewTitle(`${ledgerLabels[ltype] || ltype} — ${selectedCenter} · ${month}`);
    } catch {
      toast.error('Preview failed');
    }
  };

  const downloadLedger = async (month, ltype, fmt) => {
    try {
      const API = process.env.REACT_APP_BACKEND_URL;
      const res = await fetch(`${API}/api/ledgers/${ltype}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, center: selectedCenter, period_type: 'month', month, fmt })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || 'Download failed');
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${ltype}_${selectedCenter}_${month}.${fmt === 'excel' ? 'xlsx' : 'pdf'}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Download failed');
    }
  };

  // Only admin/super admin can see center dropdown
  useEffect(() => {
    const fetchCenters = async () => {
      if (!session?.token) return;
      try {
        const res = await api.get("/centers");
        const centers = (res.data.centers || []).filter(c => c.active !== false);
        setCentersList(centers);
      } catch {}
    };
    if (canSelectCenter) fetchCenters();
  }, [canSelectCenter, session?.token]);

  // Resolve franchise owner's center from DB mapping (no dropdown needed)
  useEffect(() => {
    const resolveCenter = async () => {
      if (!session?.token) return;
      
      // For admins: default to their login center, they can switch via dropdown
      if (canSelectCenter) {
        if (!selectedCenter) {
          setSelectedCenter(session.center || "");
        }
        return;
      }
      
      // For franchise owners: resolve from DB mapping, no manual selection
      try {
        const res = await api.post("/franchises/resolve-owner-center", { token: session.token });
        const resolved = res.data?.center;
        if (resolved) {
          setSelectedCenter(resolved);
        } else {
          // Fallback: use session fields
          setSelectedCenter(session.franchise_center || session.center || "");
        }
      } catch {
        // Fallback if endpoint fails
        setSelectedCenter(session.franchise_center || session.center || "");
      }
    };
    
    if (!selectedCenter) resolveCenter();
  }, [session, canSelectCenter, selectedCenter]);

  const fetchData = useCallback(async () => {
    if (!session?.token || !selectedCenter) return;
    setLoading(true);
    try {
      const center = selectedCenter;

      // Build period params from month or date range
      let params;
      if (useRange && customStart && customEnd) {
        params = { token: session.token, period: "custom", custom_start: customStart, custom_end: customEnd, center };
      } else {
        // Derive start/end from selected month
        const [y, m] = selectedMonth.split("-").map(Number);
        const monthStart = `${y}-${String(m).padStart(2, '0')}-01`;
        const lastDay = new Date(y, m, 0).getDate();
        const monthEnd = `${y}-${String(m).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;
        params = { token: session.token, period: "custom", custom_start: monthStart, custom_end: monthEnd, center };
      }

      const [ovRes, salesRes, expRes, wcRes] = await Promise.all([
        api.post("/mis/overview", params).catch(() => ({ data: {} })),
        api.post("/mis/sales-trends", { ...params, group_by: "daily" }).catch(() => ({ data: { trends: [] } })),
        api.post("/mis/expense-analysis", params).catch(() => ({ data: {} })),
        api.post("/mis/working-capital", { token: session.token, center }).catch(() => ({ data: {} })),
      ]);

      setOverview(ovRes.data);
      setSalesData(salesRes.data.trends || []);
      setExpenseData(expRes.data.by_type || []);
      setWorkingCapital(wcRes.data || null);

      // Fetch franchise info
      const frRes = await api.post(`/franchises/by-center/${center}`, { token: session.token }).catch(() => ({ data: { found: false, franchise: null } }));
      const franchise = frRes.data.found ? frRes.data.franchise : null;
      setFranchiseInfo(franchise);

      // Fetch documents (no level filter — show ALL docs for this franchise/center)
      try {
        const docParams = { token: session.token, center };
        if (franchise?.franchise_code) {
          docParams.franchise_code = franchise.franchise_code;
        }
        const docRes = await api.post("/documents/list", docParams).catch(() => ({ data: { documents: [] } }));
        setFranchiseDocs(docRes.data.documents || []);
      } catch { setFranchiseDocs([]); }
    } catch (err) {
      toast.error("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  }, [session, selectedMonth, customStart, customEnd, useRange, selectedCenter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const downloadDocument = async (doc) => {
    try {
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/documents/file/${doc.document_id}?auth=${session?.token}`);
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.original_filename || "document";
      a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error("Download failed"); }
  };

  const downloadFranchiseDoc = async (doc) => {
    try {
      const fc = franchiseInfo?.franchise_code;
      if (!fc) { toast.error("Franchise not linked"); return; }
      const url = `${process.env.REACT_APP_BACKEND_URL}/api/franchises/documents/download/${fc}/${doc.document_id}?token=${encodeURIComponent(session?.token || "")}`;
      const res = await fetch(url);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || "Download failed");
        return;
      }
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = doc.original_name || doc.file_name || "document";
      a.click();
      URL.revokeObjectURL(blobUrl);
    } catch { toast.error("Download failed"); }
  };

  const downloadAgreement = async () => {
    try {
      const fc = franchiseInfo?.franchise_code;
      if (!fc) { toast.error("Franchise not linked"); return; }
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/franchises/generate-agreement/${fc}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: session?.token, format: "pdf" }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || "Agreement download failed");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `FOCO_Agreement_${fc}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error("Agreement download failed"); }
  };

  const handleExportReport = () => {
    if (!overview?.summary) return;
    const sm = overview.summary;
    const sharePct = franchiseInfo?.revenue_share_percentage || 0;
    const totalSales = sm?.total_sales || 0;
    const totalComm = sm?.total_commissions || 0;
    const totalGst = sm?.total_gst || 0;
    const totalDeductions = totalComm + totalGst;
    const netRev = totalSales - totalDeductions;
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.aoa_to_sheet([
      ["Franchise Report - Purnabramha"], ["Center", selectedCenter], ["Period", period], [],
      ["Metric", "Value"],
      ["Total Sales", totalSales],
      ["Less: Commissions", totalComm],
      ["Less: GST on Eligible Sales (5% incl.)", totalGst],
      ["= Total Deductions", totalDeductions],
      ["= Net Revenue (Sales − Deductions)", netRev],
      ["Less: Total Expenses", sm?.total_expenses || 0],
      ["= Net Profit (P&L)", sm?.profit || 0],
      [],
      ["Revenue Share %", sharePct],
      [`Revenue Share Payable (${sharePct}% × Net Revenue)`, netRev * (sharePct / 100)],
    ]);
    XLSX.utils.book_append_sheet(wb, ws, "Summary");
    XLSX.writeFile(wb, `Franchise_Report_${selectedCenter}_${period}.xlsx`);
    toast.success("Report exported");
  };

  const [pdfLoading, setPdfLoading] = useState(false);
  const handleDownloadPDF = async () => {
    if (!overview?.summary) { toast.error("No data to export"); return; }
    setPdfLoading(true);
    try {
      const res = await api.post("/mis/franchise-pdf", {
        token: session.token, period, center: selectedCenter,
        custom_start: customStart || undefined, custom_end: customEnd || undefined,
        franchise_info: franchiseInfo || {},
        revenue_share_pct: franchiseInfo?.revenue_share_percentage || 0,
      }, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `Franchise_Report_${selectedCenter}_${period}.pdf`;
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

  const centerObj = centersList.find(c => c.code === selectedCenter);
  const isIntl = centerObj?.is_india_center === false || centerObj?.country === "Australia";
  const sm = overview?.summary;
  const ch = overview?.changes;
  const revenueSharePct = franchiseInfo?.revenue_share_percentage || 0;
  const netProfit = sm?.profit || 0;
  // Per Apr-2026 rule:
  //   Total Deductions  = Commissions + GST on Sales
  //   Net Revenue       = Total Sales − Total Deductions   (NOT minus expenses)
  //   Revenue Share     = revenue_share_pct × Net Revenue  (NOT × Net Profit)
  const totalCommissions = sm?.total_commissions || 0;
  const totalGst = sm?.total_gst || 0;
  const totalDeductions = totalCommissions + totalGst;
  const netRevenue = (sm?.total_sales || 0) - totalDeductions;
  const revenueShareAmount = netRevenue * (revenueSharePct / 100);
  // Final Payout: payout base = MAX(Revenue Share, Monthly Guarantee). GST is
  // computed on that base — matches PIB Section 8B / MIS Franchise PDF /
  // Owner Ledger PDF so the dashboard, screen and downloaded reports always
  // show the same gross-of-GST invoiceable figure.
  const monthlyGuarantee = parseFloat(
    franchiseInfo?.monthly_guarantee
    ?? franchiseInfo?.mg
    ?? franchiseInfo?.minimum_guarantee
    ?? 0
  ) || 0;
  const payoutBase = Math.max(revenueShareAmount, monthlyGuarantee);
  const isMgPayout = monthlyGuarantee > revenueShareAmount && payoutBase > 0;
  const finalGstRate = isIntl ? 10 : 18;
  const finalPayoutAmount = payoutBase * (1 + finalGstRate / 100);
  const trends = salesData;

  const kpiCards = sm ? [
    { label: "Total Sales", value: sm.total_sales, change: ch?.sales_change, icon: IndianRupee, gradient: "from-emerald-600 to-emerald-400", textColor: "text-emerald-50" },
    { label: "Total Expenses", value: sm.total_expenses, change: ch?.expenses_change, icon: Receipt, gradient: "from-red-600 to-red-400", textColor: "text-red-50" },
    { label: "Commissions", displayValue: formatFullCurrency(totalCommissions, isIntl), icon: Receipt, gradient: "from-purple-600 to-purple-400", textColor: "text-purple-50" },
    { label: `GST on Eligible Sales (${isIntl ? "10" : "5"}% incl.)`, displayValue: formatFullCurrency(totalGst, isIntl), icon: Receipt, gradient: "from-fuchsia-600 to-fuchsia-400", textColor: "text-fuchsia-50" },
    { label: "Total Deductions", displayValue: formatFullCurrency(totalDeductions, isIntl), icon: Receipt, gradient: "from-orange-600 to-orange-400", textColor: "text-orange-50" },
    { label: "Net Revenue", displayValue: formatFullCurrency(netRevenue, isIntl), icon: Activity, gradient: netRevenue >= 0 ? "from-cyan-700 to-cyan-500" : "from-rose-700 to-rose-500", textColor: "text-cyan-50" },
    { label: "Net Profit (P&L)", displayValue: formatFullCurrency(netProfit, isIntl), change: ch?.profit_change, icon: Activity, gradient: netProfit >= 0 ? "from-emerald-700 to-emerald-500" : "from-red-700 to-red-500", textColor: "text-emerald-50" },
    { label: "Working Capital", displayValue: formatFullCurrency(workingCapital?.available_working_capital || 0, isIntl), icon: Wallet, gradient: "from-amber-600 to-amber-400", textColor: "text-amber-50" },
    { label: "Avg / Bill", displayValue: formatFullCurrency(sm.avg_per_bill, isIntl), icon: Activity, gradient: "from-teal-600 to-teal-400", textColor: "text-teal-50" },
    { label: `Revenue Share (${revenueSharePct}% × Net Rev)`, displayValue: formatFullCurrency(revenueShareAmount, isIntl), icon: Percent, gradient: revenueShareAmount >= 0 ? "from-blue-600 to-blue-400" : "from-rose-600 to-rose-400", textColor: "text-blue-50" },
    {
      label: `Final Payout (incl. ${finalGstRate}% GST)`,
      displayValue: formatFullCurrency(finalPayoutAmount, isIntl),
      icon: Wallet,
      gradient: "from-emerald-700 to-emerald-500",
      textColor: "text-emerald-50",
      // Sub-badge surfaces the MG-trigger condition — exactly the cases the CA
      // needs to flag. Falls back to the breakdown otherwise.
      subBadge: isMgPayout
        ? `MG paid (₹${monthlyGuarantee.toLocaleString()} > Rev Share)`
        : `Base: ${formatFullCurrency(payoutBase, isIntl)}`,
    },
  ] : [];

  // Allow admin/super-admin, franchise owners, and users with franchise role
  const hasAccess = isAdmin || isFranchiseOwner || session?.roles?.franchise === true;
  if (!hasAccess) return null;

  return (
    <div className="space-y-6" data-testid="franchise-owner-dashboard">
      {/* HEADER */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 rounded-2xl p-6 border border-slate-700/40">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
                <Store className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white tracking-tight">Franchise Dashboard</h1>
                <p className="text-sm text-slate-400">
                  {franchiseInfo ? `${franchiseInfo.franchise_name} - ${selectedCenter}` : selectedCenter} &middot; View Only
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Badge className="bg-yellow-500/20 text-yellow-300 border border-yellow-500/30 text-xs">View Only</Badge>

            {!useRange ? (
              <input
                type="month"
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className="h-9 px-3 rounded-md bg-slate-800/80 border border-slate-600 text-white text-sm focus:outline-none focus:ring-1 focus:ring-amber-500"
                data-testid="fo-month-picker"
              />
            ) : (
              <div className="flex items-center gap-1">
                <input
                  type="date"
                  value={customStart}
                  onChange={(e) => setCustomStart(e.target.value)}
                  className="h-9 px-2 rounded-md bg-slate-800/80 border border-slate-600 text-white text-xs focus:outline-none focus:ring-1 focus:ring-amber-500 w-[130px]"
                  data-testid="fo-range-start"
                />
                <span className="text-slate-400 text-xs">to</span>
                <input
                  type="date"
                  value={customEnd}
                  onChange={(e) => setCustomEnd(e.target.value)}
                  className="h-9 px-2 rounded-md bg-slate-800/80 border border-slate-600 text-white text-xs focus:outline-none focus:ring-1 focus:ring-amber-500 w-[130px]"
                  data-testid="fo-range-end"
                />
              </div>
            )}

            <Button
              variant="outline"
              size="sm"
              className={`h-9 text-xs ${useRange ? 'bg-amber-600 text-white border-amber-500' : 'bg-slate-800/80 border-slate-600 text-white'}`}
              onClick={() => setUseRange(!useRange)}
            >
              <Calendar className="w-3.5 h-3.5 mr-1" />
              {useRange ? 'Month' : 'Range'}
            </Button>

            {canSelectCenter && centersList.length > 0 && (
              <Select value={selectedCenter} onValueChange={setSelectedCenter}>
                <SelectTrigger className="w-[140px] bg-slate-800/80 border-slate-600 text-white text-sm h-9" data-testid="fo-center-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {centersList.map(c => (
                    <SelectItem key={c.code} value={c.code}>{c.code} - {c.name?.split(' - ')[0]?.substring(0, 12)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}

            <Button variant="outline" size="sm" className="bg-amber-600/90 border-amber-500 text-white h-9 hover:bg-amber-500" onClick={handleDownloadPDF} disabled={pdfLoading || loading} data-testid="fo-download-pdf-btn">
              <FileText className={`w-4 h-4 mr-1 ${pdfLoading ? 'animate-pulse' : ''}`} />
              {pdfLoading ? "..." : "PDF"}
            </Button>
            <Button variant="outline" size="sm" className="bg-slate-800/80 border-slate-600 text-white h-9" onClick={handleExportReport}>
              <Download className="w-4 h-4 mr-1" /> Export
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="bg-fuchsia-600/90 border-fuchsia-500 text-white h-9 hover:bg-fuchsia-500"
              onClick={() => setShowOwnerLedgers(true)}
              data-testid="fo-owner-ledgers-btn"
            >
              <FileText className="w-4 h-4 mr-1" /> My Ledgers
            </Button>
          </div>
        </div>

        {/* Franchise Owner Info */}
        {franchiseInfo && (
          <div className="mt-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <UserCheck className="w-5 h-5 text-emerald-400" />
              <div>
                <p className="text-sm font-medium text-emerald-300">{franchiseInfo.owner_name} &mdash; Franchise Owner</p>
                <p className="text-xs text-emerald-400/70">{franchiseInfo.email} | Revenue Share: {revenueSharePct}%</p>
              </div>
            </div>
            <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-500/30">{franchiseInfo.status || 'Active'}</Badge>
          </div>
        )}
      </div>

      {/* LOADING */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-amber-600" />
        </div>
      )}

      {/* KPI CARDS */}
      {sm && !loading && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          {kpiCards.map((kpi, i) => {
            const Icon = kpi.icon;
            const displayVal = kpi.displayValue || formatCurrency(kpi.value, isIntl);
            return (
              <div
                key={i}
                className={`relative overflow-hidden rounded-xl bg-gradient-to-br ${kpi.gradient} p-4 shadow-lg transition-transform hover:scale-[1.02]`}
                data-testid={`fo-kpi-${kpi.label.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
              >
                <div className="absolute -right-3 -top-3 w-16 h-16 rounded-full bg-white/10" />
                <div className="absolute -right-1 -bottom-4 w-12 h-12 rounded-full bg-white/5" />
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-2">
                    <p className={`text-xs font-medium ${kpi.textColor} opacity-80`}>{kpi.label}</p>
                    <Icon className={`w-4 h-4 ${kpi.textColor} opacity-60`} />
                  </div>
                  <p className={`text-lg font-bold ${kpi.textColor} tracking-tight`}>{displayVal}</p>
                  {kpi.subBadge && (
                    <div className={`inline-block mt-1 px-1.5 py-0.5 rounded bg-white/15 text-[10px] font-medium ${kpi.textColor} opacity-90 truncate max-w-full`}>
                      {kpi.subBadge}
                    </div>
                  )}
                  {kpi.change !== undefined && kpi.change !== null && (
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

      {/* TABS */}
      {sm && !loading && (
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-slate-100 border border-slate-200 rounded-xl p-1 flex-wrap">
            <TabsTrigger value="overview" className="rounded-lg text-xs data-[state=active]:bg-amber-600 data-[state=active]:text-white">Sales Overview</TabsTrigger>
            <TabsTrigger value="expenses" className="rounded-lg text-xs data-[state=active]:bg-amber-600 data-[state=active]:text-white">Expense Breakdown</TabsTrigger>
            <TabsTrigger value="franchise" className="rounded-lg text-xs data-[state=active]:bg-amber-600 data-[state=active]:text-white">Franchise Info</TabsTrigger>
            <TabsTrigger value="documents" className="rounded-lg text-xs data-[state=active]:bg-amber-600 data-[state=active]:text-white">Documents</TabsTrigger>
          </TabsList>

          {/* SALES OVERVIEW TAB */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Sales vs Expenses Trend */}
              <Card className="bg-white border-slate-200/60 rounded-xl">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base font-semibold text-slate-800">Sales vs Expenses Trend</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <ComposedChart data={trends}>
                      <defs>
                        <linearGradient id="foSalesGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#059669" stopOpacity={0.4}/>
                          <stop offset="95%" stopColor="#059669" stopOpacity={0.02}/>
                        </linearGradient>
                        <linearGradient id="foExpGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#DC2626" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#DC2626" stopOpacity={0.02}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#CBD5E1" />
                      <XAxis dataKey="date" stroke="#64748B" fontSize={10} tickLine={false} />
                      <YAxis stroke="#64748B" fontSize={10} tickLine={false} tickFormatter={(v) => formatCurrency(v, isIntl)} />
                      <Tooltip content={<PremiumTooltip />} />
                      <Legend wrapperStyle={{ fontSize: '12px' }} />
                      <Area type="monotone" dataKey="sales" fill="url(#foSalesGrad)" stroke="#059669" strokeWidth={2.5} name="Sales" />
                      <Area type="monotone" dataKey="expenses" fill="url(#foExpGrad)" stroke="#DC2626" strokeWidth={2} name="Expenses" />
                    </ComposedChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Sales Breakdown */}
              <Card className="bg-white border-slate-200/60 rounded-xl">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base font-semibold text-slate-800">Sales Breakdown</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { label: "Cash Sales", value: sm?.total_cash_sales || 0, color: "bg-emerald-500" },
                      { label: "Online Sales", value: sm?.total_online_sales || 0, color: "bg-blue-500" },
                      { label: "Total Guests", value: sm?.total_guests || 0, color: "bg-amber-500", isCurrency: false },
                      { label: "Total Bills", value: sm?.total_bills || 0, color: "bg-purple-500", isCurrency: false },
                      { label: "GST", value: sm?.total_gst || 0, color: "bg-red-400" },
                      { label: "Profit Margin", value: `${sm?.profit_margin?.toFixed(1) || 0}%`, color: "bg-teal-500", isRaw: true },
                    ].map((item, i) => (
                      <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100">
                        <div className={`w-3 h-3 rounded-full ${item.color}`} />
                        <div>
                          <p className="text-xs text-slate-500">{item.label}</p>
                          <p className="text-sm font-bold text-slate-800">
                            {item.isRaw ? item.value : item.isCurrency === false ? item.value.toLocaleString() : formatCurrency(item.value, isIntl)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* EXPENSE BREAKDOWN TAB */}
          <TabsContent value="expenses" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-white border-slate-200/60 rounded-xl">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base font-semibold text-slate-800">Expense Distribution</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie data={expenseData.filter(e => e.amount > 0)} cx="50%" cy="50%" outerRadius={100} dataKey="amount" nameKey="type" label={({ type, percent }) => `${type?.substring(0, 10)} ${(percent * 100).toFixed(0)}%`} labelLine={false} fontSize={10}>
                        {expenseData.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip content={<PremiumTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card className="bg-white border-slate-200/60 rounded-xl overflow-hidden">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base font-semibold text-slate-800">Expense Details</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="max-h-[350px] overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50 sticky top-0">
                        <tr>
                          <th className="text-left px-4 py-2 text-xs font-semibold text-slate-500">Type</th>
                          <th className="text-right px-4 py-2 text-xs font-semibold text-slate-500">Amount</th>
                          <th className="text-right px-4 py-2 text-xs font-semibold text-slate-500">%</th>
                        </tr>
                      </thead>
                      <tbody>
                        {expenseData.filter(e => e.amount > 0).sort((a, b) => b.amount - a.amount).map((exp, i) => (
                          <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                            <td className="px-4 py-2 flex items-center gap-2">
                              <span className="w-2.5 h-2.5 rounded-full" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
                              {exp.type}
                            </td>
                            <td className="text-right px-4 py-2 font-medium">{formatFullCurrency(exp.amount, isIntl)}</td>
                            <td className="text-right px-4 py-2 text-slate-500">{sm?.total_expenses ? ((exp.amount / sm.total_expenses) * 100).toFixed(1) : 0}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* FRANCHISE INFO TAB */}
          <TabsContent value="franchise" className="space-y-4">
            {franchiseInfo ? (
              <Card className="bg-white border-slate-200/60 rounded-xl">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Store className="w-5 h-5" /> Franchise Profile
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {[
                      { label: "Franchise Name", value: franchiseInfo.franchise_name },
                      { label: "Owner / Primary Contact", value: franchiseInfo.owner_name || franchiseInfo.primary_contact_name },
                      { label: "Franchise Code", value: franchiseInfo.franchise_code },
                      { label: "Center Name", value: franchiseInfo.center || franchiseInfo.center_code || selectedCenter },
                      { label: "Email", value: franchiseInfo.email || franchiseInfo.primary_contact_email },
                      { label: "Phone", value: franchiseInfo.phone || franchiseInfo.contact_phone || franchiseInfo.primary_contact_phone },
                      { label: "Legal Entity", value: franchiseInfo.legal_entity || franchiseInfo.company_name || franchiseInfo.legal_entity_name },
                      { label: "Agreement Start", value: franchiseInfo.agreement_start_date },
                      { label: "Agreement End", value: franchiseInfo.agreement_end_date },
                      { label: "Revenue Share %", value: `${revenueSharePct}%` },
                      { label: "City", value: franchiseInfo.city },
                      { label: "State", value: franchiseInfo.state },
                      { label: "Address", value: franchiseInfo.address },
                      { label: "Status", value: franchiseInfo.status },
                    ].map((item, i) => (
                      <div key={i} data-testid={`franchise-info-${i}`}>
                        <p className="text-xs text-slate-500 mb-1">{item.label}</p>
                        <p className="text-sm font-semibold text-slate-800">{item.value || "—"}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="bg-white border-slate-200/60 rounded-xl">
                <CardContent className="py-8 text-center text-slate-500">
                  No franchise linked to this center.
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* DOCUMENTS TAB */}
          <TabsContent value="documents" className="space-y-4">
            {/* Auto-generated Agreement */}
            <Card className="bg-white border-slate-200/60 rounded-xl">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileText className="w-5 h-5 text-amber-700" /> Franchise Agreement
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between p-4 rounded-lg border border-amber-200 bg-amber-50/40" data-testid="fo-agreement-row">
                  <div>
                    <p className="font-medium text-sm">Auto-Generated FOCO Agreement</p>
                    <p className="text-xs text-slate-600 mt-0.5">
                      Comprehensive franchise agreement (60+ pages). Generated on demand from your latest franchise record.
                    </p>
                    {franchiseInfo?.agreement_start_date && (
                      <p className="text-[11px] text-slate-500 mt-1">
                        Term: {franchiseInfo.agreement_start_date} → {franchiseInfo.agreement_end_date || "—"}
                      </p>
                    )}
                  </div>
                  <Button variant="outline" size="sm" onClick={downloadAgreement} disabled={!franchiseInfo?.franchise_code} data-testid="fo-download-agreement-btn">
                    <FileDown className="w-4 h-4 mr-1" /> Download Agreement PDF
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Franchise-level uploaded docs (LIC, GST, agreements, KYC, etc.) */}
            <Card className="bg-white border-slate-200/60 rounded-xl">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileText className="w-5 h-5 text-fuchsia-600" /> Franchise Records (LIC, KYC, Agreements, etc.)
                </CardTitle>
              </CardHeader>
              <CardContent>
                {(franchiseInfo?.documents?.length || 0) === 0 ? (
                  <p className="text-center py-6 text-slate-500 text-sm" data-testid="fo-no-franchise-docs">
                    No franchise records uploaded yet by Admin.
                  </p>
                ) : (
                  <div className="space-y-3" data-testid="fo-franchise-docs-list">
                    {(franchiseInfo.documents || []).map((doc) => (
                      <div
                        key={doc.document_id}
                        className="flex items-center justify-between p-4 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors"
                        data-testid={`fo-fr-doc-${doc.document_id}`}
                      >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <div className="p-2 rounded-lg bg-fuchsia-50">
                            <FileText className="w-5 h-5 text-fuchsia-600" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="font-medium text-sm truncate">{doc.original_name || doc.file_name}</p>
                            <div className="flex items-center gap-2 mt-1 flex-wrap">
                              {doc.document_type && (
                                <Badge variant="outline" className="text-xs uppercase">{doc.document_type}</Badge>
                              )}
                              {doc.uploaded_at && (
                                <span className="text-xs text-slate-500">Uploaded: {String(doc.uploaded_at).split('T')[0]}</span>
                              )}
                            </div>
                            {doc.description && <p className="text-xs text-slate-500 mt-1">{doc.description}</p>}
                          </div>
                        </div>
                        <Button variant="outline" size="sm" onClick={() => downloadFranchiseDoc(doc)} data-testid={`fo-download-fr-doc-${doc.document_id}`}>
                          <FileDown className="w-4 h-4 mr-1" /> Download
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* General center documents (bills, certificates uploaded via Documents module) */}
            <Card className="bg-white border-slate-200/60 rounded-xl">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileText className="w-5 h-5" /> Other Documents
                </CardTitle>
              </CardHeader>
              <CardContent>
                {franchiseDocs.length === 0 ? (
                  <p className="text-center py-6 text-slate-500 text-sm" data-testid="fo-no-docs">
                    No additional documents available for this franchise.
                  </p>
                ) : (
                  <div className="space-y-3" data-testid="fo-documents-list">
                    {franchiseDocs.map((doc) => (
                      <div
                        key={doc.document_id}
                        className="flex items-center justify-between p-4 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors"
                        data-testid={`fo-doc-${doc.document_id}`}
                      >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <div className="p-2 rounded-lg bg-red-50">
                            <FileText className="w-5 h-5 text-red-600" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="font-medium text-sm truncate">{doc.original_filename}</p>
                            <div className="flex items-center gap-2 mt-1 flex-wrap">
                              {doc.category_name && (
                                <Badge variant="outline" className="text-xs">{doc.category_name}</Badge>
                              )}
                              {doc.status && (
                                <Badge className={`text-xs ${doc.status === 'approved' ? 'bg-green-100 text-green-700' : doc.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                                  {doc.status}
                                </Badge>
                              )}
                              {doc.expiry_date && (
                                <span className="text-xs text-slate-500">Expires: {new Date(doc.expiry_date).toLocaleDateString()}</span>
                              )}
                            </div>
                            <p className="text-xs text-slate-400 mt-1">
                              Uploaded: {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : '—'}
                              {doc.uploaded_by ? ` by ${doc.uploaded_by}` : ''}
                            </p>
                          </div>
                        </div>
                        <Button variant="outline" size="sm" onClick={() => downloadDocument(doc)} data-testid={`fo-download-doc-${doc.document_id}`}>
                          <FileDown className="w-4 h-4 mr-1" /> Download
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}

      {/* Owner Ledger — released months modal */}
      <Dialog open={showOwnerLedgers} onOpenChange={setShowOwnerLedgers}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="fo-owner-ledgers-modal">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-fuchsia-600" />
              My Ledgers — {selectedCenter}
            </DialogTitle>
            <DialogDescription>
              Statutory ledgers and account statements for your franchise. Each month is unlocked once Accounts releases the monthly report.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            {ownerLedgerLoading ? (
              <div className="py-6 text-center text-slate-500 text-sm">Loading…</div>
            ) : ownerLedgerMonths.length === 0 ? (
              <div className="py-6 text-center text-slate-500 text-sm">
                No ledgers have been released yet. Ask Accounts to release a monthly report from the Owner Reports page.
              </div>
            ) : (
              ownerLedgerMonths.map(m => (
                <div key={m.month} className="border border-slate-200 rounded-lg p-3" data-testid={`fo-month-${m.month}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <p className="font-semibold text-sm text-slate-800">{m.month}</p>
                      {m.released_at && <p className="text-[10px] text-slate-500">Released: {String(m.released_at).split('T')[0]}</p>}
                    </div>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full ${m.report_ready ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                      {m.report_ready ? 'Full Report Released' : 'Owner Ledger Only'}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                    {(m.available_ledgers || []).map(lt => (
                      <div key={lt} className="flex items-center justify-between px-2 py-1.5 bg-slate-50 rounded text-xs hover:bg-slate-100">
                        <span className="text-slate-700">{ledgerLabels[lt] || lt}</span>
                        <div className="flex gap-1">
                          <Button size="sm" variant="outline" className="h-6 px-2 text-[10px]" onClick={() => previewLedger(m.month, lt)} data-testid={`fo-preview-${lt}-${m.month}`}>Preview</Button>
                          <Button size="sm" variant="outline" className="h-6 px-2 text-[10px]" onClick={() => downloadLedger(m.month, lt, 'pdf')} data-testid={`fo-dl-${lt}-${m.month}-pdf`}>PDF</Button>
                          <Button size="sm" variant="outline" className="h-6 px-2 text-[10px]" onClick={() => downloadLedger(m.month, lt, 'excel')} data-testid={`fo-dl-${lt}-${m.month}-xls`}>Excel</Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Inline Preview modal */}
      <Dialog open={!!previewBlobUrl} onOpenChange={(o) => { if (!o) { if (previewBlobUrl) URL.revokeObjectURL(previewBlobUrl); setPreviewBlobUrl(null); } }}>
        <DialogContent className="max-w-5xl h-[85vh] p-0 flex flex-col" data-testid="fo-preview-modal">
          <DialogHeader className="px-5 py-3 border-b border-slate-200">
            <DialogTitle className="text-base">{previewTitle || "Preview"}</DialogTitle>
            <DialogDescription className="text-xs">View the ledger before downloading. Use the buttons below to save it.</DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-hidden">
            {previewBlobUrl && (
              <iframe title="ledger-preview" src={previewBlobUrl} className="w-full h-full" data-testid="fo-preview-frame" />
            )}
          </div>
          <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-slate-200">
            <Button variant="outline" size="sm" onClick={() => { if (previewBlobUrl) URL.revokeObjectURL(previewBlobUrl); setPreviewBlobUrl(null); }} data-testid="fo-preview-close">Close</Button>
            {previewBlobUrl && (
              <a href={previewBlobUrl} download={`${previewTitle.replace(/[^a-z0-9]+/gi, '_')}.pdf`} data-testid="fo-preview-download">
                <Button size="sm" className="bg-fuchsia-600 hover:bg-fuchsia-700 text-white">
                  <FileDown className="w-4 h-4 mr-1" /> Download PDF
                </Button>
              </a>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
