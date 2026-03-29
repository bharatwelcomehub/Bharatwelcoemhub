import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { 
  BarChart3, Download, IndianRupee, Receipt, FileText, Store, Calendar,
  TrendingUp, TrendingDown, Loader2, Eye, UserCheck, UserX, Link2, FileDown
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from "recharts";
import * as XLSX from "xlsx";

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088FE', '#00C49F'];
const formatCurrency = (v) => {
  if (!v) return "0";
  if (v >= 100000) return `${(v / 100000).toFixed(2)}L`;
  if (v >= 1000) return `${(v / 1000).toFixed(1)}K`;
  return v.toFixed(0);
};

export default function FranchiseOwnerDashboard() {
  const { session } = useAuth();
  const [loading, setLoading] = useState(false);
  const [period, setPeriod] = useState("current_month");
  const [tab, setTab] = useState("overview");
  const [centersList, setCentersList] = useState([]);
  const [selectedCenter, setSelectedCenter] = useState("");
  
  // Data
  const [overview, setOverview] = useState(null);
  const [salesData, setSalesData] = useState([]);
  const [expenseData, setExpenseData] = useState([]);
  const [franchiseInfo, setFranchiseInfo] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [workingCapital, setWorkingCapital] = useState(null);
  const [franchiseDocs, setFranchiseDocs] = useState([]);

  const isAdmin = session?.is_super_admin || session?.is_admin;

  // Fetch centers for admin dropdown
  useEffect(() => {
    const fetchCenters = async () => {
      if (!isAdmin || !session?.token) return;
      try {
        const res = await api.get("/centers");
        const centers = (res.data.centers || []).filter(c => c.active !== false);
        setCentersList(centers);
      } catch {}
    };
    fetchCenters();
  }, [isAdmin, session?.token]);

  // Set initial center
  useEffect(() => {
    if (!selectedCenter && session?.center) {
      setSelectedCenter(session.franchise_center || session.center);
    }
  }, [session, selectedCenter]);

  const fetchData = useCallback(async () => {
    if (!session?.token || !selectedCenter) return;
    setLoading(true);
    try {
      const center = selectedCenter;
      const params = { token: session.token, period, center };
      
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
      
      // Fetch franchise info for this center
      const frRes = await api.post(`/franchises/by-center/${center}`, { token: session.token }).catch(() => ({ data: { found: false, franchise: null } }));
      const franchise = frRes.data.found ? frRes.data.franchise : null;
      setFranchiseInfo(franchise);
      
      // Fetch documents for this franchise/center (view only)
      try {
        const docParams = { token: session.token, level: "franchise" };
        if (franchise?.franchise_code) {
          docParams.franchise_code = franchise.franchise_code;
        } else {
          docParams.center = center;
        }
        const docRes = await api.post("/documents/list", docParams).catch(() => ({ data: { documents: [] } }));
        setFranchiseDocs(docRes.data.documents || []);
      } catch { setFranchiseDocs([]); }
      
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [session, period, selectedCenter]);

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

  const handleExportReport = () => {
    if (!overview) return;
    const wb = XLSX.utils.book_new();
    const center = session.franchise_center || session.center;
    
    // Summary
    const summary = [
      ["Franchise Report - Purnabramha"], ["Center", center], ["Period", period], [],
      ["Metric", "Value"],
      ["Total Sales", overview?.summary?.total_sales],
      ["Total Expenses", overview?.summary?.total_expenses],
      ["GST", overview?.summary?.total_gst],
      ["Working Capital", workingCapital?.available_working_capital || "N/A"],
    ];
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(summary), "Summary");
    
    // Sales Trends
    if (salesData.length > 0) {
      const rows = salesData.map(s => [s.date, s.sales, s.expenses, s.gst]);
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([["Date", "Sales", "Expenses", "GST"], ...rows]), "Sales Trends");
    }
    
    // Expense Breakdown
    if (expenseData.length > 0) {
      const rows = expenseData.map(e => [e.type, e.amount, e.percentage, e.count]);
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([["Type", "Amount", "%", "Count"], ...rows]), "Expenses");
    }
    
    XLSX.writeFile(wb, `Franchise_Report_${center}_${period}.xlsx`);
    toast.success("Report downloaded");
  };

  const summary = overview?.summary || {};
  const center = session?.franchise_center || session?.center;

  return (
    <div className="space-y-6" data-testid="franchise-owner-dashboard">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Store className="w-6 h-6 text-primary" />
            Franchise Dashboard
          </h1>
          <p className="text-sm text-muted-foreground">
            {franchiseInfo?.franchise_name || franchiseInfo?.name || center} — View Only
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="text-xs border-amber-400 text-amber-600 bg-amber-50">
            <Eye className="w-3 h-3 mr-1" /> View Only
          </Badge>
          {isAdmin && centersList.length > 0 && (
            <Select value={selectedCenter} onValueChange={setSelectedCenter}>
              <SelectTrigger className="w-[140px]" data-testid="fo-center-select">
                <SelectValue placeholder="Center" />
              </SelectTrigger>
              <SelectContent>
                {centersList.map(c => (
                  <SelectItem key={c.code} value={c.code}>{c.code} - {c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-[160px]" data-testid="fo-period-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="current_month">This Month</SelectItem>
              <SelectItem value="last_month">Last Month</SelectItem>
              <SelectItem value="last_3_months">Last 3 Months</SelectItem>
              <SelectItem value="last_6_months">Last 6 Months</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handleExportReport} disabled={loading} data-testid="fo-export-btn">
            <Download className="w-4 h-4 mr-2" /> Export
          </Button>
        </div>
      </div>

      {loading && (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      )}

      {!loading && (
        <>
          {/* Franchise Ownership Status */}
          <Card className={`border-2 ${franchiseInfo ? 'border-green-200 bg-green-50/50' : 'border-amber-200 bg-amber-50/50'}`} data-testid="franchise-connectivity-card">
            <CardContent className="py-3 px-4">
              <div className="flex items-center gap-3">
                {franchiseInfo ? (
                  <>
                    <div className="p-2 rounded-full bg-green-100">
                      <UserCheck className="w-5 h-5 text-green-600" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-green-800" data-testid="franchise-owner-name">
                        {franchiseInfo.primary_contact_name || franchiseInfo.franchise_name || franchiseInfo.name} — Franchise Owner Connected
                      </p>
                      <p className="text-xs text-green-600">
                        Center: {selectedCenter || center} | {franchiseInfo.primary_contact_email || ''} {franchiseInfo.primary_contact_phone ? `| ${franchiseInfo.primary_contact_phone}` : ''}
                      </p>
                    </div>
                    <Badge className="bg-green-100 text-green-700 border-green-300">
                      <Link2 className="w-3 h-3 mr-1" /> Active
                    </Badge>
                  </>
                ) : (
                  <>
                    <div className="p-2 rounded-full bg-amber-100">
                      <UserX className="w-5 h-5 text-amber-600" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-amber-800" data-testid="franchise-unmapped-status">
                        No Franchise Mapped to This Center
                      </p>
                      <p className="text-xs text-amber-600">
                        Center: {selectedCenter || center} | Link a franchise via Center Accounts
                      </p>
                    </div>
                    <Badge variant="outline" className="border-amber-400 text-amber-600 bg-amber-50">
                      Unmapped
                    </Badge>
                  </>
                )}
              </div>
            </CardContent>
          </Card>

          {/* KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="bg-card border-border">
              <CardContent className="pt-4">
                <p className="text-xs text-muted-foreground">Total Sales</p>
                <p className="text-xl font-bold text-green-400" data-testid="fo-total-sales">
                  {formatCurrency(summary.total_sales || 0)}
                </p>
              </CardContent>
            </Card>
            <Card className="bg-card border-border">
              <CardContent className="pt-4">
                <p className="text-xs text-muted-foreground">Total Expenses</p>
                <p className="text-xl font-bold text-red-400" data-testid="fo-total-expenses">
                  {formatCurrency(summary.total_expenses || 0)}
                </p>
              </CardContent>
            </Card>
            <Card className="bg-card border-border">
              <CardContent className="pt-4">
                <p className="text-xs text-muted-foreground">GST</p>
                <p className="text-xl font-bold text-amber-400" data-testid="fo-gst">
                  {formatCurrency(summary.total_gst || 0)}
                </p>
              </CardContent>
            </Card>
            <Card className="bg-card border-border">
              <CardContent className="pt-4">
                <p className="text-xs text-muted-foreground">Working Capital</p>
                <p className="text-xl font-bold text-primary" data-testid="fo-working-capital">
                  {formatCurrency(workingCapital?.available_working_capital || 0)}
                </p>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  {(workingCapital?.total_outstanding || 0) > 0 
                    ? `${formatCurrency(workingCapital.total_outstanding)} outstanding` 
                    : 'Fully intact'}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Tabs */}
          <Tabs value={tab} onValueChange={setTab}>
            <TabsList className="bg-card border border-border">
              <TabsTrigger value="overview">Sales Overview</TabsTrigger>
              <TabsTrigger value="expenses">Expense Breakdown</TabsTrigger>
              <TabsTrigger value="franchise">Franchise Info</TabsTrigger>
              <TabsTrigger value="documents">Documents</TabsTrigger>
            </TabsList>

            {/* Sales Overview Tab */}
            <TabsContent value="overview" className="space-y-4">
              <Card className="bg-card border-border">
                <CardHeader><CardTitle className="text-lg flex items-center gap-2"><TrendingUp className="w-5 h-5" /> Sales Trend</CardTitle></CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={350}>
                    <BarChart data={salesData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                      <XAxis dataKey="date" stroke="#888" fontSize={10} />
                      <YAxis stroke="#888" fontSize={10} tickFormatter={v => `${(v/1000).toFixed(0)}K`} />
                      <Tooltip contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #333' }} />
                      <Legend />
                      <Bar dataKey="sales" fill="#22c55e" name="Sales" />
                      <Bar dataKey="expenses" fill="#ef4444" name="Expenses" />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
              
              {/* Daily table */}
              <Card className="bg-card border-border">
                <CardHeader><CardTitle className="text-lg">Day-wise Sales</CardTitle></CardHeader>
                <CardContent>
                  <div className="overflow-auto max-h-[400px]">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-card">
                        <tr className="border-b border-border">
                          <th className="text-left p-2">Date</th>
                          <th className="text-right p-2">Sales</th>
                          <th className="text-right p-2">Expenses</th>
                          <th className="text-right p-2">GST</th>
                        </tr>
                      </thead>
                      <tbody>
                        {salesData.map((d, i) => (
                          <tr key={i} className="border-b border-border/50 hover:bg-white/5">
                            <td className="p-2">{d.date}</td>
                            <td className="p-2 text-right text-green-400">{formatCurrency(d.sales)}</td>
                            <td className="p-2 text-right text-red-400">{formatCurrency(d.expenses)}</td>
                            <td className="p-2 text-right text-amber-400">{formatCurrency(d.gst)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Expense Breakdown Tab */}
            <TabsContent value="expenses" className="space-y-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card className="bg-card border-border">
                  <CardHeader><CardTitle className="text-lg flex items-center gap-2"><Receipt className="w-5 h-5" /> By Category</CardTitle></CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie data={expenseData} dataKey="amount" nameKey="type" cx="50%" cy="50%" outerRadius={100} label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`}>
                          {expenseData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                        </Pie>
                        <Tooltip formatter={v => formatCurrency(v)} />
                      </PieChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
                <Card className="bg-card border-border">
                  <CardHeader><CardTitle className="text-lg">Expense Details</CardTitle></CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {expenseData.map((e, i) => (
                        <div key={i} className="flex justify-between items-center p-2 rounded bg-muted/30">
                          <span className="text-sm font-medium">{e.type}</span>
                          <div className="text-right">
                            <span className="font-bold">{formatCurrency(e.amount)}</span>
                            <span className="text-xs text-muted-foreground ml-2">({e.percentage?.toFixed(1)}%)</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Franchise Info Tab */}
            <TabsContent value="franchise" className="space-y-4">
              <Card className="bg-card border-border">
                <CardHeader><CardTitle className="text-lg flex items-center gap-2"><Store className="w-5 h-5" /> Franchise Profile</CardTitle></CardHeader>
                <CardContent>
                  {franchiseInfo ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {[
                        ["Franchise Name", franchiseInfo.franchise_name || franchiseInfo.name],
                        ["Owner / Primary Contact", franchiseInfo.primary_contact_name],
                        ["Franchise Code", franchiseInfo.franchise_code],
                        ["Email", franchiseInfo.primary_contact_email],
                        ["Phone", franchiseInfo.primary_contact_phone],
                        ["Agreement Start", franchiseInfo.agreement_start_date],
                        ["Agreement End", franchiseInfo.agreement_end_date],
                        ["Revenue Share %", franchiseInfo.revenue_share_percentage ? `${franchiseInfo.revenue_share_percentage}%` : "N/A"],
                        ["City", franchiseInfo.city],
                        ["State", franchiseInfo.state],
                        ["Address", franchiseInfo.address],
                        ["Status", franchiseInfo.status],
                      ].map(([label, value]) => (
                        <div key={label} className="space-y-1">
                          <p className="text-xs text-muted-foreground">{label}</p>
                          <p className="font-medium">{value || "—"}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground">No franchise profile found for this center. Contact admin to set up.</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Documents Tab - View & Download Only */}
            <TabsContent value="documents" className="space-y-4">
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <FileText className="w-5 h-5" /> Franchise Documents
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {franchiseDocs.length === 0 ? (
                    <p className="text-center py-8 text-muted-foreground" data-testid="fo-no-docs">
                      No documents available for this franchise.
                    </p>
                  ) : (
                    <div className="space-y-3" data-testid="fo-documents-list">
                      {franchiseDocs.map((doc) => (
                        <div
                          key={doc.document_id}
                          className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-muted/30 transition-colors"
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
                                  <span className="text-xs text-muted-foreground">
                                    Expires: {new Date(doc.expiry_date).toLocaleDateString()}
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-muted-foreground mt-1">
                                Uploaded: {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : '—'}
                                {doc.uploaded_by ? ` by ${doc.uploaded_by}` : ''}
                              </p>
                            </div>
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => downloadDocument(doc)}
                            data-testid={`fo-download-doc-${doc.document_id}`}
                          >
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
        </>
      )}
    </div>
  );
}
