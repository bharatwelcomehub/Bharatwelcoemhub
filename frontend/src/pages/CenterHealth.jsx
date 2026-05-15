import React, { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/App";
import { toast } from "sonner";
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, Brain,
  CheckCircle2, Download, IndianRupee, LineChart as LineIcon,
  Loader2, ShieldAlert, Sparkles, TrendingDown, TrendingUp, Wallet,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

const API = process.env.REACT_APP_BACKEND_URL;

// ---------- helpers ----------
const sym = (currency) => (currency === "AUD" ? "A$" : "₹");
const fmt = (n, currency) => `${sym(currency)}${Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
const pct = (n) => `${Number(n || 0).toFixed(1)}%`;
const monthOptions = () => {
  // last 24 months ending current month
  const out = [];
  const d = new Date();
  for (let i = 0; i < 24; i++) {
    const m = new Date(d.getFullYear(), d.getMonth() - i, 1);
    const key = `${m.getFullYear()}-${String(m.getMonth() + 1).padStart(2, "0")}`;
    const label = m.toLocaleString("en-US", { month: "short", year: "numeric" });
    out.push({ key, label });
  }
  return out;
};

const tierStyles = {
  Excellent: { bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-700", dot: "bg-emerald-500" },
  Stable:    { bg: "bg-green-50",   border: "border-green-200",   text: "text-green-700",   dot: "bg-green-500" },
  Warning:   { bg: "bg-amber-50",   border: "border-amber-200",   text: "text-amber-700",   dot: "bg-amber-500" },
  Critical:  { bg: "bg-orange-50",  border: "border-orange-200",  text: "text-orange-700",  dot: "bg-orange-500" },
  Dangerous: { bg: "bg-red-50",     border: "border-red-200",     text: "text-red-700",     dot: "bg-red-500" },
};

const severityBadge = {
  critical: "bg-red-100 text-red-800 border-red-300",
  high: "bg-orange-100 text-orange-800 border-orange-300",
  medium: "bg-amber-100 text-amber-800 border-amber-300",
  low: "bg-slate-100 text-slate-700 border-slate-300",
};

// ---------- sub-components ----------
function HealthMeter({ score, currency }) {
  const tier = score?.tier || "Stable";
  const s = tierStyles[tier] || tierStyles.Stable;
  const val = Math.max(0, Math.min(100, score?.score ?? 0));
  return (
    <div className={`rounded-2xl border ${s.border} ${s.bg} p-6 flex flex-col items-center justify-center h-full`} data-testid="health-score-card">
      <div className="text-xs uppercase tracking-wider text-slate-500 font-medium">Health Score</div>
      <div className={`text-6xl font-black mt-2 ${s.text}`} data-testid="health-score-value">{val.toFixed(0)}</div>
      <div className={`mt-1 inline-flex items-center gap-2 text-sm font-bold ${s.text}`} data-testid="health-score-tier">
        <span className={`w-2 h-2 rounded-full ${s.dot} animate-pulse`} />
        {tier}
      </div>
      <div className="mt-4 w-full bg-white/60 rounded-full h-2 overflow-hidden">
        <div className={`h-2 ${s.dot.replace("bg-", "bg-")}`} style={{ width: `${val}%` }} />
      </div>
      <div className="text-[10px] mt-2 text-slate-500 uppercase tracking-wide">0–100 scale · {currency}</div>
    </div>
  );
}

function FounderSummary({ narrative, generatedAt }) {
  return (
    <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 via-yellow-50 to-orange-50 p-6 h-full" data-testid="founder-summary">
      <div className="flex items-center gap-2 mb-3">
        <Brain className="w-4 h-4 text-amber-700" />
        <span className="text-xs font-semibold uppercase tracking-wider text-amber-800">Founder's Monthly Reality Check</span>
      </div>
      <p className="text-sm leading-relaxed text-slate-800 whitespace-pre-wrap">{narrative?.founder_summary}</p>
      <div className="text-[10px] mt-3 text-slate-500">AI-assisted · GPT-5.2 · Generated {generatedAt ? new Date(generatedAt).toLocaleString() : "—"}</div>
    </div>
  );
}

function KpiCard({ icon: Icon, label, value, sub, tone = "slate", trend, "data-testid": testid }) {
  const tones = {
    slate: "bg-white border-slate-200",
    emerald: "bg-emerald-50 border-emerald-200",
    red: "bg-red-50 border-red-200",
    blue: "bg-blue-50 border-blue-200",
    amber: "bg-amber-50 border-amber-200",
    rose: "bg-rose-50 border-rose-200",
    indigo: "bg-indigo-50 border-indigo-200",
    fuchsia: "bg-fuchsia-50 border-fuchsia-200",
  };
  return (
    <div className={`rounded-xl border p-4 ${tones[tone]}`} data-testid={testid}>
      <div className="flex items-center justify-between">
        <div className="text-[11px] uppercase tracking-wider text-slate-600 font-medium">{label}</div>
        {Icon && <Icon className="w-4 h-4 text-slate-500" />}
      </div>
      <div className="text-xl font-bold text-slate-900 mt-2">{value}</div>
      {sub && <div className="text-[11px] text-slate-500 mt-1">{sub}</div>}
      {trend != null && (
        <div className={`mt-2 flex items-center gap-1 text-xs ${trend >= 0 ? "text-emerald-700" : "text-red-700"}`}>
          {trend >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
          {Math.abs(trend).toFixed(1)}% vs prev
        </div>
      )}
    </div>
  );
}

function RatioRow({ label, current, ideal, idealLabel = "≤" }) {
  let status, color, Icon;
  if (current <= ideal) {
    status = "OK"; color = "text-emerald-700 bg-emerald-50"; Icon = CheckCircle2;
  } else if (current <= ideal * 1.3) {
    status = "High"; color = "text-amber-700 bg-amber-50"; Icon = AlertTriangle;
  } else {
    status = "Critical"; color = "text-red-700 bg-red-50"; Icon = ShieldAlert;
  }
  return (
    <div className="grid grid-cols-12 items-center gap-2 py-2.5 border-b border-slate-100 last:border-0 text-sm">
      <div className="col-span-5 font-medium text-slate-700">{label}</div>
      <div className="col-span-3 font-bold text-slate-900">{pct(current)}</div>
      <div className="col-span-2 text-xs text-slate-500">{idealLabel} {pct(ideal)}</div>
      <div className={`col-span-2 inline-flex items-center justify-end gap-1 text-xs font-semibold rounded-full px-2 py-0.5 ${color}`}>
        <Icon className="w-3 h-3" /> {status}
      </div>
    </div>
  );
}

function TrendStrip({ trend, currency }) {
  if (!trend?.length) return null;
  const max = Math.max(...trend.map((t) => Math.abs(t.net_profit)), 1);
  return (
    <div className="grid grid-cols-12 gap-1 h-32 items-end" data-testid="trend-strip">
      {trend.map((t, idx) => {
        const h = Math.max(2, (Math.abs(t.net_profit) / max) * 100);
        const positive = t.net_profit >= 0;
        return (
          <div key={idx} className="flex flex-col items-center justify-end h-full">
            <div
              className={`w-full rounded-t-sm ${positive ? "bg-emerald-500" : "bg-red-500"} opacity-80 hover:opacity-100 transition-opacity`}
              style={{ height: `${h}%` }}
              title={`${t.label} · P/L ${fmt(t.net_profit, currency)} · Sales ${fmt(t.sales, currency)}`}
            />
            <div className="text-[9px] text-slate-500 mt-1 truncate w-full text-center">{t.label.slice(0, 3)}</div>
          </div>
        );
      })}
    </div>
  );
}

// ---------- main page ----------
export default function CenterHealth() {
  const { session } = useAuth();
  const [centers, setCenters] = useState([]);
  const [center, setCenter] = useState("");
  const [month, setMonth] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const months = useMemo(monthOptions, []);

  // Fetch accessible centers on mount
  useEffect(() => {
    if (!session?.token) return;
    (async () => {
      try {
        const r = await fetch(`${API}/api/health-dashboard/centers`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: session.token }),
        });
        if (!r.ok) throw new Error(await r.text());
        const j = await r.json();
        setCenters(j.centers || []);
        if (j.centers?.length && !center) setCenter(j.centers[0].code);
      } catch (e) {
        toast.error(`Failed to load centers: ${e.message || e}`);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.token]);

  const loadHealth = async () => {
    if (!center) return;
    setLoading(true);
    setData(null);
    try {
      const r = await fetch(`${API}/api/health-dashboard/score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: session.token, center, month }),
      });
      if (!r.ok) {
        const t = await r.text();
        throw new Error(t || `HTTP ${r.status}`);
      }
      const j = await r.json();
      setData(j);
    } catch (e) {
      toast.error(`${e.message || e}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (center && month && session?.token) loadHealth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center, month, session?.token]);

  const downloadPdf = async () => {
    if (!center) return;
    setDownloading(true);
    try {
      const r = await fetch(`${API}/api/health-dashboard/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: session.token, center, month }),
      });
      if (!r.ok) throw new Error(await r.text());
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `health_${center}_${month}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("PDF downloaded · ready to share with franchisee");
    } catch (e) {
      toast.error(`PDF failed: ${e.message || e}`);
    } finally {
      setDownloading(false);
    }
  };

  const cur = data?.current;
  const prev = data?.previous;
  const yoy = data?.yoy;
  const currency = data?.currency || "INR";

  const prevTrend = useMemo(() => {
    if (!cur || !prev || !prev.sales?.total) return null;
    return ((cur.sales.total - prev.sales.total) / prev.sales.total) * 100;
  }, [cur, prev]);
  const profitTrend = useMemo(() => {
    if (!cur || !prev) return null;
    if (Math.abs(prev.net_profit) < 1) return null;
    return ((cur.net_profit - prev.net_profit) / Math.abs(prev.net_profit)) * 100;
  }, [cur, prev]);

  const r = data?.ratios || {};
  const ideal = data?.ideal_ratios || {};

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="center-health-page">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Activity className="w-6 h-6 text-rose-600" />
            Center Profitability Health Dashboard
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Single-source AI-assisted health view · powered by canonical financial helpers
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Select value={center} onValueChange={setCenter}>
            <SelectTrigger className="w-56" data-testid="center-selector">
              <SelectValue placeholder="Select center" />
            </SelectTrigger>
            <SelectContent>
              {centers.map((c) => (
                <SelectItem key={c.code} value={c.code} data-testid={`center-opt-${c.code}`}>
                  {c.code} · {c.name} {c.country !== "India" ? `(${c.country})` : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={month} onValueChange={setMonth}>
            <SelectTrigger className="w-40" data-testid="month-selector">
              <SelectValue placeholder="Month" />
            </SelectTrigger>
            <SelectContent>
              {months.map((m) => (
                <SelectItem key={m.key} value={m.key}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            onClick={loadHealth}
            disabled={loading || !center}
            data-testid="refresh-btn"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Refresh"}
          </Button>
          <Button
            onClick={downloadPdf}
            disabled={downloading || !data}
            className="bg-rose-700 hover:bg-rose-800 text-white"
            data-testid="download-pdf-btn"
          >
            {downloading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Download className="w-4 h-4 mr-2" />}
            Download PDF
          </Button>
        </div>
      </div>

      {/* Empty / loading */}
      {loading && (
        <div className="flex items-center justify-center py-20 text-slate-500">
          <Loader2 className="w-6 h-6 animate-spin mr-2" /> Computing health metrics…
        </div>
      )}
      {!loading && !data && (
        <div className="text-center py-20 text-slate-500" data-testid="empty-state">
          Pick a center and month to see the health view.
        </div>
      )}

      {data && (
        <>
          {/* Hero: Score + Founder Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <HealthMeter score={data.score} currency={currency} />
            <div className="md:col-span-2">
              <FounderSummary narrative={data.narrative} generatedAt={data.generated_at} />
            </div>
          </div>

          {/* KPI Strip */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-6" data-testid="kpi-grid">
            <KpiCard icon={IndianRupee} label="Sales" tone="blue"
              value={fmt(cur.sales.total, currency)}
              sub={`${cur.sales.bills_count} entries · ${pct((cur.sales.dinein/(cur.sales.total||1))*100)} dine-in`}
              trend={prevTrend} data-testid="kpi-sales" />
            <KpiCard icon={TrendingDown} label="Commissions" tone="rose"
              value={fmt(cur.commission, currency)}
              sub={`${pct(r.commission_pct)} of sales`} data-testid="kpi-comm" />
            <KpiCard icon={ShieldAlert} label="GST" tone="fuchsia"
              value={fmt(cur.gst, currency)}
              sub={`${pct(r.gst_pct)} of sales`} data-testid="kpi-gst" />
            <KpiCard icon={LineIcon} label="Net Revenue" tone="indigo"
              value={fmt(cur.net_revenue, currency)}
              sub="Sales − Comm − GST" data-testid="kpi-net-rev" />
            <KpiCard icon={TrendingDown} label="Expenses" tone="amber"
              value={fmt(cur.expenses_total, currency)}
              sub={`${pct((cur.expenses_total/(cur.sales.total||1))*100)} of sales`} data-testid="kpi-expenses" />
            <KpiCard icon={cur.net_profit >= 0 ? TrendingUp : TrendingDown}
              label="Net P/L" tone={cur.net_profit >= 0 ? "emerald" : "red"}
              value={fmt(cur.net_profit, currency)}
              sub={`${pct(r.net_margin_pct)} margin`}
              trend={profitTrend} data-testid="kpi-pl" />
          </div>

          {/* Profitability formula + WC */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
            <Card className="lg:col-span-2" data-testid="formula-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2"><LineIcon className="w-4 h-4" /> Profitability Formula</CardTitle>
              </CardHeader>
              <CardContent className="text-sm">
                {[
                  ["Total Sales", cur.sales.total, "bold"],
                  ["Less: Platform Commission", -cur.commission],
                  ["Less: GST (inclusive carve)", -cur.gst],
                  ["= Net Revenue", cur.net_revenue, "bold-indigo"],
                  ["Less: Operating Expenses", -cur.expenses_total],
                  ["= Net Profit / (Loss)", cur.net_profit, cur.net_profit >= 0 ? "bold-green" : "bold-red"],
                ].map(([label, value, tone], i) => (
                  <div key={i} className={`flex justify-between py-2 border-b border-slate-100 last:border-0 ${tone?.includes("bold") ? "font-bold" : ""} ${tone === "bold-green" ? "text-emerald-700 text-base" : tone === "bold-red" ? "text-red-700 text-base" : tone === "bold-indigo" ? "text-indigo-700" : ""}`}>
                    <span>{label}</span>
                    <span>{fmt(value, currency)}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
            <Card data-testid="wc-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2"><Wallet className="w-4 h-4" /> Working Capital Health</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                <div className="flex justify-between"><span className="text-slate-500">Current WC</span><span className="font-bold">{fmt(data.wc.current_wc, currency)}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Base WC</span><span>{fmt(data.wc.base_wc, currency)}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">% of Base</span><span className={data.wc.wc_pct >= 50 ? "text-emerald-700 font-bold" : data.wc.wc_pct >= 0 ? "text-amber-700 font-bold" : "text-red-700 font-bold"}>{pct(data.wc.wc_pct)}</span></div>
                <div className="mt-3">
                  <div className="bg-slate-100 rounded-full h-3 overflow-hidden">
                    <div className={`h-3 ${data.wc.wc_pct >= 50 ? "bg-emerald-500" : data.wc.wc_pct >= 0 ? "bg-amber-500" : "bg-red-500"}`} style={{ width: `${Math.max(0, Math.min(100, data.wc.wc_pct))}%` }} />
                  </div>
                </div>
                <div className="text-xs text-slate-500 mt-2">Status: <span className="font-semibold">{data.wc.status}</span></div>
              </CardContent>
            </Card>
          </div>

          {/* Ratios + trend */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
            <Card className="lg:col-span-2" data-testid="ratios-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Operational Ratios (% of Sales)</CardTitle>
              </CardHeader>
              <CardContent>
                <RatioRow label="Food Cost" current={r.food_cost_pct} ideal={ideal.food_cost_pct} />
                <RatioRow label="Salary" current={r.salary_pct} ideal={ideal.salary_pct} />
                <RatioRow label="Rent" current={r.rent_pct} ideal={ideal.rent_pct} />
                <RatioRow label="Utility (LPG/Electricity/Water)" current={r.utility_pct} ideal={ideal.utility_pct} />
                <RatioRow label="Commission Burden" current={r.commission_pct} ideal={ideal.commission_burden_pct} />
                <RatioRow label="Aggregator Share of Sales" current={r.aggregator_share_pct} ideal={ideal.aggregator_share_pct} />
              </CardContent>
            </Card>
            <Card data-testid="trend-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">12-Month P/L Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <TrendStrip trend={data.trend} currency={currency} />
                {yoy && (
                  <div className="mt-4 text-xs text-slate-600 border-t pt-3">
                    <div className="font-semibold text-slate-700 mb-1">Same month last year ({yoy.label})</div>
                    <div className="flex justify-between"><span>Sales</span><span>{fmt(yoy.sales.total, currency)}</span></div>
                    <div className="flex justify-between"><span>Net P/L</span><span className={yoy.net_profit >= 0 ? "text-emerald-700" : "text-red-700"}>{fmt(yoy.net_profit, currency)}</span></div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Leakages */}
          <Card className="mb-6" data-testid="leakages-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-orange-600" />
                Monthly Leakage Analysis
                <span className="ml-auto text-xs font-normal text-slate-500">{data.leakages.length} signal(s)</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {data.leakages.length === 0 ? (
                <div className="text-sm text-emerald-700 py-4 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" /> No significant leakage detected this month.
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {data.leakages.map((lk, i) => (
                    <div key={i} className="py-3 flex items-start gap-3" data-testid={`leakage-${i}`}>
                      <Badge variant="outline" className={`uppercase text-[10px] font-bold ${severityBadge[lk.severity] || severityBadge.low}`}>
                        {lk.severity}
                      </Badge>
                      <div className="flex-1">
                        <div className="font-semibold text-sm text-slate-900">{lk.category}</div>
                        <div className="text-xs text-slate-600 mt-0.5">{lk.detail}</div>
                      </div>
                      <div className="text-right shrink-0">
                        <div className="text-xs text-slate-500">Est. Impact</div>
                        <div className="font-bold text-sm text-rose-700">{fmt(lk.impact, currency)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Actions + Predictive */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
            <Card data-testid="actions-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-amber-600" />
                  What Needs Correction
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="space-y-3 text-sm text-slate-700">
                  {data.actions.map((a, i) => (
                    <li key={i} className="flex items-start gap-3" data-testid={`action-${i}`}>
                      <span className="bg-rose-100 text-rose-800 font-bold text-xs rounded-full w-5 h-5 flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
                      <span>{a}</span>
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-rose-50 to-orange-50 border-rose-200" data-testid="predictive-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2 text-rose-800">
                  <ShieldAlert className="w-4 h-4" />
                  Predictive 3-Month Warning
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-slate-800 whitespace-pre-wrap">
                  {data.narrative.predictive_warning}
                </p>
                <div className="text-[10px] text-slate-500 mt-3">
                  AI-assisted projection from current pattern · for management discussion, not a financial commitment
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Comparisons */}
          {prev && (
            <Card className="mb-6" data-testid="comparison-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Smart Comparisons</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <div className="text-xs text-slate-500 mb-2 uppercase tracking-wide">Vs Previous Month ({prev.label})</div>
                    {[["Sales", cur.sales.total, prev.sales.total],
                      ["Expenses", cur.expenses_total, prev.expenses_total],
                      ["Net P/L", cur.net_profit, prev.net_profit]].map(([lbl, c, p]) => {
                        const delta = p ? ((c - p) / Math.abs(p)) * 100 : 0;
                        return (
                          <div key={lbl} className="flex justify-between py-1">
                            <span className="text-slate-600">{lbl}</span>
                            <span className={delta >= 0 ? "text-emerald-700 font-semibold" : "text-red-700 font-semibold"}>
                              {delta >= 0 ? "▲" : "▼"} {Math.abs(delta).toFixed(1)}%
                            </span>
                          </div>
                        );
                      })}
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-2 uppercase tracking-wide">Channel Mix</div>
                    <div className="flex justify-between py-1"><span>Dine-in</span><span className="font-semibold">{fmt(cur.sales.dinein, currency)}</span></div>
                    <div className="flex justify-between py-1"><span>Aggregator</span><span className="font-semibold">{fmt(cur.sales.aggregator, currency)}</span></div>
                    <div className="flex justify-between py-1 text-xs text-slate-500"><span>Swiggy / Zomato / DoorDash</span><span>{fmt(cur.sales.swiggy, currency)} / {fmt(cur.sales.zomato, currency)} / {fmt(cur.sales.doordash, currency)}</span></div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-2 uppercase tracking-wide">Expense Buckets</div>
                    {Object.entries(data.expense_buckets)
                      .filter(([, v]) => v > 0)
                      .sort((a, b) => b[1] - a[1])
                      .slice(0, 5)
                      .map(([k, v]) => (
                        <div key={k} className="flex justify-between py-1">
                          <span className="capitalize text-slate-600">{k.replace("_", " ")}</span>
                          <span className="font-semibold">{fmt(v, currency)}</span>
                        </div>
                      ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
