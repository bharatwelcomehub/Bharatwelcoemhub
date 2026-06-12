import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Card, CardContent, CardHeader, CardTitle,
} from "@/components/ui/card";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import {
  DollarSign, Settings, BarChart3, TrendingDown, Building2,
  Save, RefreshCw, Loader2, Percent, Plus, Trash2, Info,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

export default function CommissionTracking() {
  const { session } = useAuth();
  const [centers, setCenters] = useState([]);
  const [selectedCenter, setSelectedCenter] = useState("");
  const [month, setMonth] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
  const [dateMode, setDateMode] = useState("month"); // "month" or "range"
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("dashboard");

  // Config state
  const [config, setConfig] = useState(null);
  const [configCenter, setConfigCenter] = useState("");

  // Dashboard state
  const [dashboardData, setDashboardData] = useState(null);

  const isAdmin = session?.is_super_admin || session?.is_admin;

  useEffect(() => {
    const fetchCenters = async () => {
      try {
        const res = await api.get("/centers");
        setCenters((res.data.centers || []).filter(c => c.active !== false));
      } catch {}
    };
    fetchCenters();
  }, []);

  // Load config when center changes
  const loadConfig = useCallback(async (center) => {
    if (!center || !session?.token) return;
    try {
      const res = await api.post("/commissions/config/get", { token: session.token, center });
      setConfig(res.data.config);
    } catch { toast.error("Failed to load config"); }
  }, [session?.token]);

  useEffect(() => {
    if (configCenter) loadConfig(configCenter);
  }, [configCenter, loadConfig]);

  // Load dashboard
  const loadDashboard = useCallback(async () => {
    if (!session?.token) return;
    setLoading(true);
    try {
      const params = { token: session.token };
      if (dateMode === "month") {
        params.month = month;
      } else {
        params.start_date = startDate;
        params.end_date = endDate;
      }
      if (selectedCenter && selectedCenter !== "all") params.center = selectedCenter;
      const res = await api.post("/commissions/dashboard", params);
      setDashboardData(res.data);
    } catch { toast.error("Failed to load dashboard"); }
    setLoading(false);
  }, [session?.token, month, selectedCenter, dateMode, startDate, endDate]);

  useEffect(() => {
    if (tab === "dashboard") loadDashboard();
  }, [tab, loadDashboard]);

  // Config handlers
  const updatePlatform = (idx, field, value) => {
    const updated = [...config.platforms];
    updated[idx] = { ...updated[idx], [field]: field.includes("pct") ? parseFloat(value) || 0 : value };
    setConfig({ ...config, platforms: updated });
  };

  const updatePaymentMode = (idx, field, value) => {
    const updated = [...config.payment_modes];
    updated[idx] = { ...updated[idx], [field]: field.includes("pct") ? parseFloat(value) || 0 : value };
    setConfig({ ...config, payment_modes: updated });
  };

  const addPlatform = () => {
    setConfig({
      ...config,
      platforms: [...config.platforms, { platform: "", commission_pct: 0, gst_on_commission_pct: 18, is_active: true }],
    });
  };

  const addPaymentMode = () => {
    setConfig({
      ...config,
      payment_modes: [...config.payment_modes, { payment_mode: "", commission_pct: 0, is_active: true }],
    });
  };

  const removePlatform = (idx) => {
    setConfig({ ...config, platforms: config.platforms.filter((_, i) => i !== idx) });
  };

  const removePaymentMode = (idx) => {
    setConfig({ ...config, payment_modes: config.payment_modes.filter((_, i) => i !== idx) });
  };

  const saveConfig = async () => {
    if (!configCenter) { toast.error("Select a center"); return; }
    try {
      await api.post("/commissions/config/save", {
        token: session.token,
        center: configCenter,
        platforms: config.platforms,
        payment_modes: config.payment_modes,
      });
      toast.success("Commission config saved");
    } catch { toast.error("Save failed"); }
  };

  const fmt = (n) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(n || 0);

  return (
    <div className="p-4 md:p-6 space-y-6" data-testid="commission-tracking-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#8B0000]" data-testid="commission-title">Commission Tracking</h1>
          <p className="text-sm text-muted-foreground">Platform, Payment & GST Commission Management</p>
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="dashboard" data-testid="tab-dashboard"><BarChart3 className="w-4 h-4 mr-1" /> Dashboard</TabsTrigger>
          <TabsTrigger value="config" data-testid="tab-config"><Settings className="w-4 h-4 mr-1" /> Configuration</TabsTrigger>
        </TabsList>

        {/* ── DASHBOARD TAB ── */}
        <TabsContent value="dashboard" className="space-y-4">
          <div className="flex flex-wrap gap-3 items-end">
            <div>
              <Label className="text-xs">Center</Label>
              <Select value={selectedCenter} onValueChange={setSelectedCenter} data-testid="dash-center-select">
                <SelectTrigger className="w-48"><SelectValue placeholder="All Centers" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Centers</SelectItem>
                  {centers.map(c => (
                    <SelectItem key={c.code} value={c.code}>{c.code} - {c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Mode</Label>
              <Select value={dateMode} onValueChange={setDateMode} data-testid="date-mode-select">
                <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="month">Monthly</SelectItem>
                  <SelectItem value="range">Date Range</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {dateMode === "month" ? (
              <div>
                <Label className="text-xs">Month</Label>
                <Input type="month" value={month} onChange={e => setMonth(e.target.value)} className="w-44" data-testid="dash-month-input" />
              </div>
            ) : (
              <>
                <div>
                  <Label className="text-xs">From</Label>
                  <Input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="w-40" data-testid="dash-start-date" />
                </div>
                <div>
                  <Label className="text-xs">To</Label>
                  <Input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="w-40" data-testid="dash-end-date" />
                </div>
              </>
            )}
            <Button onClick={loadDashboard} variant="outline" data-testid="refresh-dashboard">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              <span className="ml-1">Refresh</span>
            </Button>
          </div>

          {/* Grand Totals */}
          {dashboardData && (
            <>
              {dashboardData.grand_totals && (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                  {[
                    { label: "Total Sales", val: dashboardData.grand_totals.total_sales, icon: DollarSign, color: "text-green-600" },
                    { label: "Platform Commission", val: dashboardData.grand_totals.platform_commission, icon: TrendingDown, color: "text-red-600" },
                    { label: "GST on Commission", val: dashboardData.grand_totals.gst_on_commission, icon: Percent, color: "text-orange-600" },
                    { label: "Payment Commission", val: dashboardData.grand_totals.payment_commission, icon: TrendingDown, color: "text-purple-600" },
                    { label: "Total Commission", val: dashboardData.grand_totals.total_commission, icon: TrendingDown, color: "text-red-700 font-bold" },
                    { label: "Revenue Share Base", val: dashboardData.grand_totals.net_revenue, icon: DollarSign, color: "text-sky-700 font-bold" },
                  ].map((item, i) => (
                    <Card key={i}>
                      <CardContent className="p-3 text-center">
                        <item.icon className={`w-5 h-5 mx-auto mb-1 ${item.color}`} />
                        <p className="text-xs text-muted-foreground">{item.label}</p>
                        <p className={`text-lg font-semibold ${item.color}`}>{fmt(item.val)}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}

              {/* Center-wise Table */}
              {dashboardData.centers && dashboardData.centers.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Center-wise Commission Breakdown</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm" data-testid="commission-center-table">
                        <thead>
                          <tr className="bg-[#8B0000] text-white">
                            <th className="p-2 text-left">Center</th>
                            <th className="p-2 text-right">Sales</th>
                            <th className="p-2 text-right">Platform Comm.</th>
                            <th className="p-2 text-right">GST</th>
                            <th className="p-2 text-right">Payment Comm.</th>
                            <th className="p-2 text-right font-bold">Total Comm.</th>
                            <th className="p-2 text-right font-bold">Rev Share Base</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dashboardData.centers.map((c, i) => (
                            <tr key={c.center} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                              <td className="p-2 font-medium">{c.center_name || c.center}</td>
                              <td className="p-2 text-right text-green-600">{fmt(c.total_sales)}</td>
                              <td className="p-2 text-right text-red-500">{fmt(c.platform_commission)}</td>
                              <td className="p-2 text-right text-orange-500">{fmt(c.gst_on_commission)}</td>
                              <td className="p-2 text-right text-purple-500">{fmt(c.payment_commission)}</td>
                              <td className="p-2 text-right font-bold text-red-700">{fmt(c.total_commission)}</td>
                              <td className="p-2 text-right font-bold text-emerald-700">{fmt(c.net_revenue)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Single center detail: platform & payment breakdowns */}
              {dashboardData.data && (
                <div className="grid md:grid-cols-2 gap-4">
                  <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-base">Platform Breakdown</CardTitle></CardHeader>
                    <CardContent>
                      <table className="w-full text-sm" data-testid="platform-breakdown-table">
                        <thead><tr className="border-b"><th className="p-2 text-left">Platform</th><th className="p-2 text-right">Sales</th><th className="p-2 text-right">Commission</th><th className="p-2 text-right">GST</th></tr></thead>
                        <tbody>
                          {Object.entries(dashboardData.data.platform_breakdown || {}).map(([platform, v]) => (
                            <tr key={platform} className="border-b">
                              <td className="p-2 font-medium">{platform}</td>
                              <td className="p-2 text-right">{fmt(v.sales)}</td>
                              <td className="p-2 text-right text-red-500">{fmt(v.commission)}</td>
                              <td className="p-2 text-right text-orange-500">{fmt(v.gst)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-base">Payment Mode Breakdown</CardTitle></CardHeader>
                    <CardContent>
                      <table className="w-full text-sm" data-testid="payment-breakdown-table">
                        <thead><tr className="border-b"><th className="p-2 text-left">Mode</th><th className="p-2 text-right">Sales</th><th className="p-2 text-right">Commission</th></tr></thead>
                        <tbody>
                          {Object.entries(dashboardData.data.payment_breakdown || {}).map(([mode, v]) => (
                            <tr key={mode} className="border-b">
                              <td className="p-2 font-medium">{mode}</td>
                              <td className="p-2 text-right">{fmt(v.sales)}</td>
                              <td className="p-2 text-right text-purple-500">{fmt(v.commission)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </CardContent>
                  </Card>
                </div>
              )}
            </>
          )}

          {!dashboardData && !loading && (
            <div className="text-center py-12 text-muted-foreground">
              <BarChart3 className="w-12 h-12 mx-auto mb-2 opacity-30" />
              <p>Select a month and click Refresh to load commission data</p>
            </div>
          )}
        </TabsContent>

        {/* ── CONFIG TAB ── */}
        <TabsContent value="config" className="space-y-4">
          {!isAdmin && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded text-amber-800 text-sm">
              <Info className="w-4 h-4 inline mr-1" /> Only Admin/Super Admin can modify commission configuration.
            </div>
          )}

          <div className="flex gap-3 items-end">
            <div>
              <Label className="text-xs">Select Center</Label>
              <Select value={configCenter} onValueChange={setConfigCenter} data-testid="config-center-select">
                <SelectTrigger className="w-56"><SelectValue placeholder="Select Center" /></SelectTrigger>
                <SelectContent>
                  {centers.map(c => (
                    <SelectItem key={c.code} value={c.code}>{c.code} - {c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {isAdmin && config && (
              <Button onClick={saveConfig} className="bg-[#8B0000] hover:bg-[#6B0000]" data-testid="save-config-btn">
                <Save className="w-4 h-4 mr-1" /> Save Config
              </Button>
            )}
          </div>

          {config && (
            <div className="grid md:grid-cols-2 gap-4">
              {/* Platform Commissions */}
              <Card>
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-base">Platform Commissions</CardTitle>
                    {isAdmin && <Button size="sm" variant="outline" onClick={addPlatform} data-testid="add-platform-btn"><Plus className="w-3 h-3 mr-1" /> Add</Button>}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {config.platforms.map((p, i) => (
                    <div key={i} className="flex items-center gap-2 p-2 rounded border bg-gray-50" data-testid={`platform-row-${i}`}>
                      <Input
                        value={p.platform}
                        onChange={e => updatePlatform(i, "platform", e.target.value.toUpperCase())}
                        placeholder="Platform name"
                        className="flex-1 h-8 text-sm"
                        disabled={!isAdmin}
                      />
                      <div className="flex items-center gap-1">
                        <Input
                          type="number" value={p.commission_pct}
                          onChange={e => updatePlatform(i, "commission_pct", e.target.value)}
                          className="w-16 h-8 text-sm text-right" disabled={!isAdmin}
                        />
                        <span className="text-xs text-muted-foreground">%</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-muted-foreground">GST</span>
                        <Input
                          type="number" value={p.gst_on_commission_pct}
                          onChange={e => updatePlatform(i, "gst_on_commission_pct", e.target.value)}
                          className="w-14 h-8 text-sm text-right" disabled={!isAdmin}
                        />
                        <span className="text-xs text-muted-foreground">%</span>
                      </div>
                      {isAdmin && (
                        <Button size="icon" variant="ghost" className="h-7 w-7 text-red-500" onClick={() => removePlatform(i)}>
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* Payment Mode Commissions */}
              <Card>
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-base">Payment Mode Commissions</CardTitle>
                    {isAdmin && <Button size="sm" variant="outline" onClick={addPaymentMode} data-testid="add-payment-mode-btn"><Plus className="w-3 h-3 mr-1" /> Add</Button>}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {config.payment_modes.map((pm, i) => (
                    <div key={i} className="flex items-center gap-2 p-2 rounded border bg-gray-50" data-testid={`payment-mode-row-${i}`}>
                      <Input
                        value={pm.payment_mode}
                        onChange={e => updatePaymentMode(i, "payment_mode", e.target.value.toUpperCase())}
                        placeholder="Mode name"
                        className="flex-1 h-8 text-sm"
                        disabled={!isAdmin}
                      />
                      <div className="flex items-center gap-1">
                        <Input
                          type="number" value={pm.commission_pct}
                          onChange={e => updatePaymentMode(i, "commission_pct", e.target.value)}
                          className="w-16 h-8 text-sm text-right" disabled={!isAdmin}
                        />
                        <span className="text-xs text-muted-foreground">%</span>
                      </div>
                      {isAdmin && (
                        <Button size="icon" variant="ghost" className="h-7 w-7 text-red-500" onClick={() => removePaymentMode(i)}>
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          )}

          {!config && configCenter && (
            <div className="text-center py-8"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
