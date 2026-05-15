import React, { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/App";
import { toast } from "sonner";
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, Brain,
  CheckCircle2, Download, FileSpreadsheet, IndianRupee, Loader2,
  Sparkles, TrendingDown, TrendingUp,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const API = process.env.REACT_APP_BACKEND_URL;

const fmt = (n) => `₹${Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
const pct = (n) => `${Number(n || 0).toFixed(1)}%`;

// last 36 months for selectors
const monthOptions = () => {
  const out = [];
  const d = new Date();
  for (let i = 0; i < 36; i++) {
    const m = new Date(d.getFullYear(), d.getMonth() - i, 1);
    out.push({
      key: `${m.getFullYear()}-${String(m.getMonth() + 1).padStart(2, "0")}`,
      label: m.toLocaleString("en-US", { month: "short", year: "numeric" }),
    });
  }
  return out;
};

const fyOptions = () => {
  const out = [];
  const now = new Date();
  const curFyStart = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
  for (let i = 0; i < 4; i++) {
    const y = curFyStart - i;
    out.push({ key: `FY ${y}-${String((y + 1) % 100).padStart(2, "0")}` });
  }
  return out;
};

function Kpi({ label, value, sub, trend, tone = "slate", icon: Icon, "data-testid": tid }) {
  const tones = {
    slate: "bg-white border-slate-200",
    emerald: "bg-emerald-50 border-emerald-200",
    red: "bg-red-50 border-red-200",
    blue: "bg-blue-50 border-blue-200",
    amber: "bg-amber-50 border-amber-200",
    rose: "bg-rose-50 border-rose-200",
    indigo: "bg-indigo-50 border-indigo-200",
    fuchsia: "bg-fuchsia-50 border-fuchsia-200",
    violet: "bg-violet-50 border-violet-200",
  };
  return (
    <div className={`rounded-xl border p-3 ${tones[tone]}`} data-testid={tid}>
      <div className="flex items-center justify-between">
        <div className="text-[10px] uppercase tracking-wider text-slate-600 font-semibold">{label}</div>
        {Icon && <Icon className="w-3.5 h-3.5 text-slate-500" />}
      </div>
      <div className="text-lg font-bold text-slate-900 mt-1.5">{value}</div>
      {sub && <div className="text-[10px] text-slate-500 mt-0.5">{sub}</div>}
      {trend != null && (
        <div className={`mt-1 flex items-center gap-1 text-[11px] font-semibold ${trend >= 0 ? "text-emerald-700" : "text-red-700"}`}>
          {trend >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
          {Math.abs(trend).toFixed(1)}%
        </div>
      )}
    </div>
  );
}

function RatioRow({ label, value, ideal }) {
  let badge, color, Icon;
  if (value <= ideal) { badge = "Good"; color = "text-emerald-700 bg-emerald-50"; Icon = CheckCircle2; }
  else if (value <= ideal * 1.3) { badge = "Warning"; color = "text-amber-700 bg-amber-50"; Icon = AlertTriangle; }
  else { badge = "Critical"; color = "text-red-700 bg-red-50"; Icon = TrendingDown; }
  return (
    <div className="grid grid-cols-12 items-center py-2 border-b border-slate-100 last:border-0 text-sm">
      <div className="col-span-5 text-slate-700 font-medium">{label}</div>
      <div className="col-span-3 font-bold text-slate-900">{pct(value)}</div>
      <div className="col-span-2 text-xs text-slate-500">≤ {pct(ideal)}</div>
      <div className={`col-span-2 inline-flex items-center justify-end gap-1 text-[11px] font-semibold rounded-full px-2 py-0.5 ${color}`}>
        <Icon className="w-3 h-3" /> {badge}
      </div>
    </div>
  );
}

function TrendBars({ trend }) {
  if (!trend?.length) return null;
  const max = Math.max(...trend.map((t) => Math.abs(t.net_profit)), 1);
  return (
    <div className="grid grid-cols-12 gap-1 h-28 items-end" data-testid="insights-trend">
      {trend.map((t, idx) => {
        const h = Math.max(2, (Math.abs(t.net_profit) / max) * 100);
        const positive = t.net_profit >= 0;
        return (
          <div key={idx} className="flex flex-col items-center justify-end h-full">
            <div
              className={`w-full rounded-t-sm ${positive ? "bg-emerald-500" : "bg-red-500"} opacity-80 hover:opacity-100`}
              style={{ height: `${h}%` }}
              title={`${t.label} · P/L ${fmt(t.net_profit)} · Sales ${fmt(t.sales)}`}
            />
            <div className="text-[9px] text-slate-500 mt-1 truncate w-full text-center">{t.label.slice(0, 3)}</div>
          </div>
        );
      })}
    </div>
  );
}

export default function FinancialInsightsTab({ centersList = [] }) {
  const { session } = useAuth();
  const months = useMemo(monthOptions, []);
  const fyList = useMemo(fyOptions, []);

  // Filter state
  const [periodType, setPeriodType] = useState("month");
  const [month, setMonth] = useState(months[0]?.key);
  const [fromMonth, setFromMonth] = useState(months[5]?.key);
  const [toMonth, setToMonth] = useState(months[0]?.key);
  const [fy, setFy] = useState(fyList[0]?.key);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [selectedCenters, setSelectedCenters] = useState(() => {
    if (centersList?.length) return [centersList[0].code];
    return [];
  });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!selectedCenters.length && centersList.length) {
      setSelectedCenters([centersList[0].code]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [centersList]);

  const buildPayload = () => ({
    token: session.token,
    centers: selectedCenters,
    period_type: periodType,
    month: periodType === "month" ? month : undefined,
    from_month: periodType === "month_range" ? fromMonth : undefined,
    to_month: periodType === "month_range" ? toMonth : undefined,
    fy: periodType === "fy" ? fy : undefined,
    from_date: periodType === "custom" ? fromDate : undefined,
    to_date: periodType === "custom" ? toDate : undefined,
    compare_previous: true,
  });

  const load = async () => {
    if (!selectedCenters.length) {
      toast.error("Select at least one center");
      return;
    }
    setLoading(true); setData(null);
    try {
      const res = await fetch(`${API}/api/financial-insights/summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildPayload()),
      });
      if (!res.ok) throw new Error(await res.text());
      setData(await res.json());
    } catch (e) {
      toast.error(`Failed: ${e.message || e}`);
    } finally { setLoading(false); }
  };

  const exportFile = async (format) => {
    setExporting(true);
    try {
      const res = await fetch(`${API}/api/financial-insights/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...buildPayload(), format }),
      });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `financial_insights_${selectedCenters.join("_")}.${format === "excel" ? "xlsx" : format}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`${format.toUpperCase()} downloaded`);
    } catch (e) {
      toast.error(`Export failed: ${e.message || e}`);
    } finally { setExporting(false); }
  };

  // Auto-load on first mount when centers ready
  useEffect(() => {
    if (selectedCenters.length && session?.token) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCenters.length, session?.token]);

  const cur = data?.current?.total;
  const prev = data?.previous?.total;
  const ratios = data?.current?.ratios || {};
  const ideal = data?.ideal_ratios || {};

  const deltaSales = useMemo(() => {
    if (!cur || !prev || !prev.sales) return null;
    return ((cur.sales - prev.sales) / prev.sales) * 100;
  }, [cur, prev]);
  const deltaProfit = useMemo(() => {
    if (!cur || !prev || Math.abs(prev.net_profit) < 1) return null;
    return ((cur.net_profit - prev.net_profit) / Math.abs(prev.net_profit)) * 100;
  }, [cur, prev]);

  const toggleCenter = (code) => {
    setSelectedCenters((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  return (
    <div className="space-y-4" data-testid="financial-insights-tab">
      {/* Filter bar */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
            <div className="md:col-span-2">
              <Label className="text-xs">Period Type</Label>
              <Select value={periodType} onValueChange={setPeriodType}>
                <SelectTrigger className="h-9" data-testid="insights-period-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="month">Single Month</SelectItem>
                  <SelectItem value="month_range">Month Range</SelectItem>
                  <SelectItem value="fy">Financial Year</SelectItem>
                  <SelectItem value="custom">Custom Dates</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {periodType === "month" && (
              <div className="md:col-span-3">
                <Label className="text-xs">Month</Label>
                <Select value={month} onValueChange={setMonth}>
                  <SelectTrigger className="h-9" data-testid="insights-month"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {months.map((m) => <SelectItem key={m.key} value={m.key}>{m.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            )}

            {periodType === "month_range" && (
              <>
                <div className="md:col-span-2">
                  <Label className="text-xs">From</Label>
                  <Select value={fromMonth} onValueChange={setFromMonth}>
                    <SelectTrigger className="h-9" data-testid="insights-from-month"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {months.map((m) => <SelectItem key={m.key} value={m.key}>{m.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="md:col-span-2">
                  <Label className="text-xs">To</Label>
                  <Select value={toMonth} onValueChange={setToMonth}>
                    <SelectTrigger className="h-9" data-testid="insights-to-month"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {months.map((m) => <SelectItem key={m.key} value={m.key}>{m.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </>
            )}

            {periodType === "fy" && (
              <div className="md:col-span-3">
                <Label className="text-xs">Financial Year</Label>
                <Select value={fy} onValueChange={setFy}>
                  <SelectTrigger className="h-9" data-testid="insights-fy"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {fyList.map((f) => <SelectItem key={f.key} value={f.key}>{f.key}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            )}

            {periodType === "custom" && (
              <>
                <div className="md:col-span-2">
                  <Label className="text-xs">From Date</Label>
                  <Input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="h-9" data-testid="insights-from-date" />
                </div>
                <div className="md:col-span-2">
                  <Label className="text-xs">To Date</Label>
                  <Input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="h-9" data-testid="insights-to-date" />
                </div>
              </>
            )}

            <div className="md:col-span-5">
              <Label className="text-xs">Centers ({selectedCenters.length} selected)</Label>
              <div className="flex flex-wrap gap-1.5 mt-1 max-h-20 overflow-auto p-1 border rounded" data-testid="insights-centers">
                {centersList.map((c) => (
                  <button
                    key={c.code}
                    type="button"
                    onClick={() => toggleCenter(c.code)}
                    className={`text-[11px] px-2 py-0.5 rounded-full border ${
                      selectedCenters.includes(c.code)
                        ? "bg-rose-700 text-white border-rose-700"
                        : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
                    }`}
                    data-testid={`insights-center-${c.code}`}
                  >
                    {c.code}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 mt-3">
            <Button onClick={load} disabled={loading} className="bg-rose-700 hover:bg-rose-800 text-white" data-testid="insights-apply">
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Activity className="w-4 h-4 mr-2" />}
              Apply Filters
            </Button>
            <Button variant="outline" onClick={() => exportFile("excel")} disabled={exporting || !data} data-testid="insights-export-xlsx">
              <FileSpreadsheet className="w-4 h-4 mr-2" /> Excel
            </Button>
            <Button variant="outline" onClick={() => exportFile("csv")} disabled={exporting || !data} data-testid="insights-export-csv">
              <Download className="w-4 h-4 mr-2" /> CSV
            </Button>
          </div>
        </CardContent>
      </Card>

      {loading && (
        <div className="flex items-center justify-center py-16 text-slate-500">
          <Loader2 className="w-6 h-6 animate-spin mr-2" /> Computing analytics…
        </div>
      )}

      {data && (
        <>
          {/* AI Summary */}
          <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50 p-5" data-testid="insights-ai-summary">
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-4 h-4 text-amber-700" />
              <span className="text-xs font-bold uppercase tracking-wider text-amber-800">Executive Summary · {data.period_label}</span>
            </div>
            <p className="text-sm text-slate-800 leading-relaxed">{data.ai_summary}</p>
            <div className="text-[10px] text-slate-500 mt-2">AI-assisted · GPT-5.2 · Centers: {data.centers.join(", ")}</div>
          </div>

          {/* Financial Summary KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2" data-testid="insights-kpis">
            <Kpi icon={IndianRupee} label="Total Sales" tone="blue" value={fmt(cur.sales)} sub={`${cur.bills_count} entries`} trend={deltaSales} data-testid="kpi-sales" />
            <Kpi icon={TrendingDown} label="Expenses" tone="amber" value={fmt(cur.expenses)} sub={pct(ratios.expense_to_sales_pct) + " of sales"} data-testid="kpi-exp" />
            <Kpi icon={Activity} label="Commission" tone="rose" value={fmt(cur.commission)} sub={pct(ratios.commission_pct) + " of sales"} data-testid="kpi-comm" />
            <Kpi icon={Activity} label="GST" tone="fuchsia" value={fmt(cur.gst)} sub={pct(ratios.gst_pct) + " of sales"} data-testid="kpi-gst" />
            <Kpi icon={Sparkles} label="Gross Profit" tone="indigo" value={fmt(cur.gross_profit)} sub="Sales − RM − Comm − GST" data-testid="kpi-gross" />
            <Kpi icon={cur.net_profit >= 0 ? TrendingUp : TrendingDown} label="Net P/L"
              tone={cur.net_profit >= 0 ? "emerald" : "red"}
              value={fmt(cur.net_profit)} sub={pct(ratios.net_margin_pct) + " margin"} trend={deltaProfit} data-testid="kpi-pl" />
          </div>

          {/* Channels + Ratios + Trend */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card data-testid="insights-channels">
              <CardHeader className="pb-2"><CardTitle className="text-base">Sales Channels</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span>Dine-in</span><span className="font-bold">{fmt(cur.dinein)} · {pct(ratios.dinein_share_pct)}</span></div>
                  <div className="flex justify-between"><span>Swiggy</span><span className="font-bold">{fmt(cur.swiggy)}</span></div>
                  <div className="flex justify-between"><span>Zomato</span><span className="font-bold">{fmt(cur.zomato)}</span></div>
                  <div className="flex justify-between"><span>DoorDash</span><span className="font-bold">{fmt(cur.doordash)}</span></div>
                  <div className="flex justify-between border-t pt-2 mt-2">
                    <span className="font-semibold">Aggregator Total</span>
                    <span className="font-bold text-rose-700">{fmt(cur.aggregator)} · {pct(ratios.aggregator_share_pct)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card data-testid="insights-ratios">
              <CardHeader className="pb-2"><CardTitle className="text-base">Financial Ratios</CardTitle></CardHeader>
              <CardContent>
                <RatioRow label="Food Cost" value={ratios.food_cost_pct} ideal={ideal.food_cost_pct} />
                <RatioRow label="Salary" value={ratios.salary_pct} ideal={ideal.salary_pct} />
                <RatioRow label="Rent" value={ratios.rent_pct} ideal={ideal.rent_pct} />
                <RatioRow label="Utility" value={ratios.utility_pct} ideal={ideal.utility_pct} />
                <RatioRow label="Commission Burden" value={ratios.commission_pct} ideal={ideal.commission_burden_pct} />
                <RatioRow label="Aggregator Share" value={ratios.aggregator_share_pct} ideal={ideal.aggregator_share_pct} />
              </CardContent>
            </Card>

            <Card data-testid="insights-trend-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">12-Month Profit Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <TrendBars trend={data.trend} />
                {prev && (
                  <div className="mt-3 text-xs text-slate-600 border-t pt-2">
                    <div className="font-semibold mb-1">Prior period comparison</div>
                    <div className="flex justify-between"><span>Sales</span><span>{fmt(prev.sales)}</span></div>
                    <div className="flex justify-between"><span>Net P/L</span><span className={prev.net_profit >= 0 ? "text-emerald-700" : "text-red-700"}>{fmt(prev.net_profit)}</span></div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Expense breakdown */}
          <Card data-testid="insights-expense-table">
            <CardHeader className="pb-2"><CardTitle className="text-base">Expense Segregation</CardTitle></CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr><th className="text-left p-2">Category</th><th className="text-right p-2">Amount</th><th className="text-right p-2">% of Sales</th></tr>
                </thead>
                <tbody>
                  {Object.entries(data.current.total.expense_by_category)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 12)
                    .map(([cat, amt]) => (
                      <tr key={cat} className="border-b border-slate-100">
                        <td className="p-2">{cat}</td>
                        <td className="p-2 text-right font-semibold">{fmt(amt)}</td>
                        <td className="p-2 text-right">{cur.sales ? pct((amt / cur.sales) * 100) : "—"}</td>
                      </tr>
                    ))}
                  {Object.keys(data.current.total.expense_by_category).length === 0 && (
                    <tr><td colSpan="3" className="p-4 text-center text-slate-500">No expenses recorded</td></tr>
                  )}
                </tbody>
              </table>
            </CardContent>
          </Card>

          {/* By-month detail (when range / FY / custom selected) */}
          {data.current.by_month.length > 1 && (
            <Card data-testid="insights-by-month">
              <CardHeader className="pb-2"><CardTitle className="text-base">Month-by-Month Breakdown</CardTitle></CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                      <tr>
                        <th className="text-left p-2">Month</th>
                        <th className="text-right p-2">Sales</th>
                        <th className="text-right p-2">Expenses</th>
                        <th className="text-right p-2">Comm</th>
                        <th className="text-right p-2">GST</th>
                        <th className="text-right p-2">Net P/L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.current.by_month.map((m) => (
                        <tr key={m.month} className="border-b border-slate-100">
                          <td className="p-2 font-medium">{m.label}</td>
                          <td className="p-2 text-right">{fmt(m.sales)}</td>
                          <td className="p-2 text-right">{fmt(m.expenses)}</td>
                          <td className="p-2 text-right">{fmt(m.commission)}</td>
                          <td className="p-2 text-right">{fmt(m.gst)}</td>
                          <td className={`p-2 text-right font-bold ${m.net_profit >= 0 ? "text-emerald-700" : "text-red-700"}`}>{fmt(m.net_profit)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Per-center comparison (only when multiple centers selected) */}
          {Object.keys(data.current.per_center || {}).length > 1 && (
            <Card data-testid="insights-per-center">
              <CardHeader className="pb-2"><CardTitle className="text-base">Center Comparison</CardTitle></CardHeader>
              <CardContent>
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                    <tr>
                      <th className="text-left p-2">Center</th>
                      <th className="text-right p-2">Sales</th>
                      <th className="text-right p-2">Expenses</th>
                      <th className="text-right p-2">Comm</th>
                      <th className="text-right p-2">GST</th>
                      <th className="text-right p-2">Net P/L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data.current.per_center).map(([code, v]) => (
                      <tr key={code} className="border-b border-slate-100">
                        <td className="p-2 font-medium">{code}</td>
                        <td className="p-2 text-right">{fmt(v.sales)}</td>
                        <td className="p-2 text-right">{fmt(v.expenses)}</td>
                        <td className="p-2 text-right">{fmt(v.commission)}</td>
                        <td className="p-2 text-right">{fmt(v.gst)}</td>
                        <td className={`p-2 text-right font-bold ${v.net_profit >= 0 ? "text-emerald-700" : "text-red-700"}`}>{fmt(v.net_profit)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
