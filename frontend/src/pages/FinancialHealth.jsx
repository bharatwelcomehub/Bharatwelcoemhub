/**
 * Financial Health & Profitability Intelligence — single component that
 * renders all 11 sections of the spec for a given center, plus a Portfolio
 * variant for franchise owners.
 *
 * Usage:
 *   <FinancialHealth center="PB-SN" />          ← per-center
 *   <FinancialHealth portfolio />               ← all centers (admin only)
 *
 * Pulls /api/financial-health/center or /portfolio.
 */
import { useState, useEffect } from 'react';
import { useAuth } from '@/App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import {
  Activity, TrendingUp, TrendingDown, AlertTriangle, Shield,
  IndianRupee, BadgePercent, Users, ClipboardCheck, Lightbulb,
  Loader2, RefreshCw, ArrowUpRight, ArrowDownRight, Award, Building,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const COLORS = {
  green: { bar: 'bg-emerald-500', text: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-300' },
  yellow: { bar: 'bg-amber-500', text: 'text-amber-800', bg: 'bg-amber-50', border: 'border-amber-300' },
  red: { bar: 'bg-rose-500', text: 'text-rose-800', bg: 'bg-rose-50', border: 'border-rose-300' },
};

const fmtMoney = (v) => (typeof v === 'number')
  ? `₹${Math.round(v).toLocaleString('en-IN')}`
  : v;
const fmtPct = (v) => (typeof v === 'number') ? `${v.toFixed(1)}%` : '—';

function DeltaBadge({ value, invert = false }) {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  const up = value > 0;
  const positive = invert ? !up : up;
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  const cls = positive ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                       : 'text-rose-700 bg-rose-50 border-rose-200';
  return (
    <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] border rounded ${cls}`}>
      <Icon className="w-3 h-3" />{Math.abs(value).toFixed(1)}%
    </span>
  );
}

function StatCard({ label, value, color = 'green', sub = null, badge = null, Icon = null, testid }) {
  const c = COLORS[color] || COLORS.green;
  return (
    <Card className={`${c.border} border-l-4 hover:shadow-md transition-shadow`} data-testid={testid}>
      <CardContent className="p-4 space-y-1">
        <div className="flex items-center justify-between">
          <div className="text-[11px] uppercase tracking-wider text-stone-500 flex items-center gap-1">
            {Icon ? <Icon className="w-3.5 h-3.5" /> : null}{label}
          </div>
          {badge}
        </div>
        <div className={`text-xl font-bold ${c.text}`}>{value}</div>
        {sub && <div className="text-[11px] text-muted-foreground">{sub}</div>}
      </CardContent>
    </Card>
  );
}

function PeriodPicker({ period, onChange, disabled }) {
  return (
    <Card className="bg-stone-50">
      <CardContent className="p-3 flex flex-wrap items-end gap-3">
        <div>
          <Label className="text-xs">Period</Label>
          <Select value={period.type} disabled={disabled}
            onValueChange={v => onChange({ ...period, type: v })}>
            <SelectTrigger className="h-9 w-32" data-testid="fh-period-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="month">Month</SelectItem>
              <SelectItem value="quarter">Quarter</SelectItem>
              <SelectItem value="fy">Financial Year</SelectItem>
              <SelectItem value="custom">Custom Range</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {period.type === 'month' && (
          <div>
            <Label className="text-xs">Month</Label>
            <Input type="month" value={period.month || ''}
              onChange={e => onChange({ ...period, month: e.target.value })}
              className="h-9 w-40" data-testid="fh-period-month" />
          </div>
        )}
        {period.type === 'quarter' && (
          <div>
            <Label className="text-xs">Quarter (YYYY-Q#)</Label>
            <Input value={period.quarter || ''} placeholder="2026-Q1"
              onChange={e => onChange({ ...period, quarter: e.target.value })}
              className="h-9 w-32" data-testid="fh-period-quarter" />
          </div>
        )}
        {period.type === 'fy' && (
          <div>
            <Label className="text-xs">Financial Year (e.g. FY26)</Label>
            <Input value={period.fy || ''} placeholder="FY26"
              onChange={e => onChange({ ...period, fy: e.target.value })}
              className="h-9 w-24" data-testid="fh-period-fy" />
          </div>
        )}
        {period.type === 'custom' && (
          <>
            <div>
              <Label className="text-xs">From</Label>
              <Input type="date" value={period.from_date || ''}
                onChange={e => onChange({ ...period, from_date: e.target.value })}
                className="h-9" data-testid="fh-period-from" />
            </div>
            <div>
              <Label className="text-xs">To</Label>
              <Input type="date" value={period.to_date || ''}
                onChange={e => onChange({ ...period, to_date: e.target.value })}
                className="h-9" data-testid="fh-period-to" />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Section panels
// ──────────────────────────────────────────────────────────────────────────
function HealthScoreHero({ s }) {
  const c = COLORS[s.status_color] || COLORS.green;
  return (
    <Card className={`${c.bg} ${c.border} border-2`}>
      <CardContent className="p-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-stone-500">Financial Health Score</div>
          <div className={`text-5xl font-black ${c.text}`}>{s.health_score}<span className="text-2xl text-stone-400">/100</span></div>
          <Badge className={`${c.bar} text-white mt-1`}>{s.status}</Badge>
        </div>
        <div className="grid grid-cols-3 gap-x-6 gap-y-2 text-sm">
          <div><div className="text-[11px] text-stone-500">Net Profit</div><div className={`font-bold ${c.text}`}>{fmtMoney(s.net_profit)}</div></div>
          <div><div className="text-[11px] text-stone-500">Net Profit %</div><div className={`font-bold ${c.text}`}>{fmtPct(s.net_profit_pct)}</div></div>
          <div><div className="text-[11px] text-stone-500">Sales</div><div className="font-bold">{fmtMoney(s.total_sales)}</div></div>
          <div>
            <div className="text-[11px] text-stone-500">
              {s.adjustments > 0 ? 'Adj. Expenses' : 'Expenses'}
            </div>
            <div className="font-bold">{fmtMoney(s.total_expenses)}</div>
            {s.adjustments > 0 && (
              <div className="text-[9px] text-amber-700">
                less ₹{Math.round(s.adjustments).toLocaleString('en-IN')} adj
              </div>
            )}
          </div>
          <div><div className="text-[11px] text-stone-500">Prime Cost</div><div className="font-bold">{fmtPct(s.prime_cost_pct)}</div></div>
          <div><div className="text-[11px] text-stone-500">Sales MoM</div><div className="font-bold">
            <DeltaBadge value={s.sales_delta_pct} />
          </div></div>
        </div>
      </CardContent>
    </Card>
  );
}

function AlertStack({ alerts }) {
  if (!alerts?.length) {
    return (
      <Card className="border-emerald-300 bg-emerald-50">
        <CardContent className="p-4 flex items-center gap-2 text-emerald-800">
          <Shield className="w-5 h-5" />
          <span className="text-sm font-medium">No red alerts. Center is in healthy zone.</span>
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-700" />Red Alert System ({alerts.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1.5">
        {alerts.map((a, i) => {
          const c = COLORS[a.level] || COLORS.yellow;
          return (
            <div key={i} className={`flex items-start gap-2 p-2 rounded border ${c.bg} ${c.border}`} data-testid={`fh-alert-${a.code}`}>
              <span className={`w-2 h-2 rounded-full mt-1.5 ${c.bar}`}></span>
              <div className="flex-1">
                <div className={`text-sm font-semibold ${c.text}`}>{a.title}</div>
                <div className="text-xs text-stone-700">{a.detail}</div>
              </div>
              <Badge variant="outline" className="text-[10px]">{a.code}</Badge>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

function PrimeCostMonitor({ p }) {
  const c = COLORS[p.color] || COLORS.green;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <BadgePercent className="w-4 h-4" />Prime Cost Monitor
        </CardTitle>
        <CardDescription className="text-xs">Food + Labor as % of Sales · target &lt; 55%</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex items-baseline gap-3">
          <div className={`text-3xl font-bold ${c.text}`}>{fmtPct(p.current_pct)}</div>
          <DeltaBadge value={p.delta_pct} invert />
          <span className="text-xs text-muted-foreground">vs prev {fmtPct(p.previous_pct)}</span>
        </div>
        <div className="h-3 bg-stone-100 rounded overflow-hidden">
          <div className={`h-full ${c.bar}`} style={{ width: `${Math.min(p.current_pct, 100)}%` }}></div>
        </div>
        <div className="flex justify-between text-[10px] text-stone-500">
          <span>0%</span><span className="text-emerald-600">55%</span><span className="text-rose-600">60%</span><span>100%</span>
        </div>
      </CardContent>
    </Card>
  );
}

function FoodCostCard({ f }) {
  const c = COLORS[f.color] || COLORS.green;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <IndianRupee className="w-4 h-4" />Food Cost Intelligence
        </CardTitle>
        <CardDescription className="text-xs">Target: {fmtPct(f.target_pct)}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-1.5">
        <div className="flex items-baseline gap-2">
          <div className={`text-2xl font-bold ${c.text}`}>{fmtPct(f.actual_pct)}</div>
          <DeltaBadge value={f.delta_pct} invert />
        </div>
        <div className="text-xs text-muted-foreground">Amount {fmtMoney(f.amount)} · prev {fmtPct(f.previous_pct)}</div>
        <Badge className={`${c.bar} text-white text-[10px]`}>
          {f.actual_pct <= f.target_pct ? 'Within Target' :
            (f.actual_pct <= f.target_pct + 1 ? 'Just Over' : `Over by ${(f.actual_pct - f.target_pct).toFixed(1)}%`)}
        </Badge>
      </CardContent>
    </Card>
  );
}

function LaborCostCard({ l }) {
  const c = COLORS[l.color] || COLORS.green;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Users className="w-4 h-4" />Labor Cost Intelligence
        </CardTitle>
        <CardDescription className="text-xs">From attendance × salary expenses</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-sm">
        <div><div className="text-[10px] text-stone-500">Cost</div><div className="font-bold">{fmtMoney(l.labor_cost)}</div></div>
        <div><div className="text-[10px] text-stone-500">% of Sales</div><div className={`font-bold ${c.text}`}>{fmtPct(l.labor_cost_pct)} <DeltaBadge value={l.delta_pct} invert /></div></div>
        <div><div className="text-[10px] text-stone-500">Employees</div><div className="font-bold">{l.total_employees}</div></div>
        <div><div className="text-[10px] text-stone-500">Labor Hours</div><div className="font-bold">{l.labor_hours.toLocaleString()}</div></div>
        <div><div className="text-[10px] text-stone-500">Per Employee</div><div className="font-bold">{fmtMoney(l.cost_per_employee)}</div></div>
        <div><div className="text-[10px] text-stone-500">Per Hour</div><div className="font-bold">{fmtMoney(l.cost_per_hour)}</div></div>
      </CardContent>
    </Card>
  );
}

function ContribMargin({ cm }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <TrendingUp className="w-4 h-4" />Contribution Margin
        </CardTitle>
        <CardDescription className="text-xs">Sales − Food Cost</CardDescription>
      </CardHeader>
      <CardContent className="space-y-1.5">
        <div className="text-2xl font-bold text-emerald-700">{fmtMoney(cm.margin)}</div>
        <div className="text-xs text-muted-foreground">{fmtPct(cm.margin_pct)} of sales · prev {fmtPct(cm.previous_pct)}</div>
        <div className="h-2 bg-stone-100 rounded overflow-hidden">
          <div className="h-full bg-emerald-500" style={{ width: `${Math.min(cm.margin_pct, 100)}%` }}></div>
        </div>
      </CardContent>
    </Card>
  );
}

function OrdersPerHour({ o }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <ClipboardCheck className="w-4 h-4" />Orders per Labor Hour
        </CardTitle>
        <CardDescription className="text-xs">Productivity index — higher is better</CardDescription>
      </CardHeader>
      <CardContent className="space-y-1.5">
        <div className="flex items-baseline gap-2">
          <div className="text-2xl font-bold text-stone-800">{o.opl_h}</div>
          <DeltaBadge value={o.delta_pct} />
        </div>
        <div className="text-xs text-muted-foreground">
          {o.orders.toLocaleString()} orders ÷ {o.labor_hours.toLocaleString()} hours · prev {o.previous_opl_h}
        </div>
      </CardContent>
    </Card>
  );
}

function LeakageTable({ leaks }) {
  if (!leaks?.length) return null;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Activity className="w-4 h-4 text-rose-700" />Expense Leakage Monitor
        </CardTitle>
        <CardDescription className="text-xs">Per-head MoM with overrun flags</CardDescription>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead className="bg-stone-100 text-stone-700">
            <tr>
              <th className="px-3 py-2 text-left">Bucket</th>
              <th className="px-3 py-2 text-right">Current</th>
              <th className="px-3 py-2 text-right">Previous</th>
              <th className="px-3 py-2 text-right">Δ %</th>
              <th className="px-3 py-2 text-center">Status</th>
            </tr>
          </thead>
          <tbody>
            {leaks.map(r => {
              const c = COLORS[r.severity] || COLORS.green;
              return (
                <tr key={r.bucket} className="border-t border-stone-100 hover:bg-stone-50">
                  <td className="px-3 py-1.5">{r.bucket}</td>
                  <td className="px-3 py-1.5 text-right font-medium">{fmtMoney(r.current)}</td>
                  <td className="px-3 py-1.5 text-right text-stone-500">{fmtMoney(r.previous)}</td>
                  <td className={`px-3 py-1.5 text-right font-medium ${c.text}`}>
                    {r.delta_pct > 0 ? '+' : ''}{r.delta_pct}%
                  </td>
                  <td className="px-3 py-1.5 text-center">
                    <span className={`inline-block w-2.5 h-2.5 rounded-full ${c.bar}`}></span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function Recommendations({ recs }) {
  if (!recs?.length) {
    return (
      <Card className="border-emerald-300 bg-emerald-50/40">
        <CardContent className="p-4 flex items-center gap-2 text-sm text-emerald-800">
          <Lightbulb className="w-4 h-4" />
          No immediate actions needed. Keep tracking weekly.
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-amber-600" />AI Recommended Actions ({recs.length})
        </CardTitle>
        <CardDescription className="text-xs">Practical, specific steps for each detected issue</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {recs.map((r, i) => (
          <div key={i} className="p-3 rounded border bg-amber-50/40 border-amber-200" data-testid={`fh-rec-${r.trigger}`}>
            <div className="text-sm font-semibold text-amber-900 mb-1">→ {r.title}</div>
            <ul className="list-disc list-inside text-xs text-stone-700 space-y-0.5">
              {r.actions.map((a, j) => <li key={j}>{a}</li>)}
            </ul>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Main component
// ──────────────────────────────────────────────────────────────────────────
export default function FinancialHealth({ center: propCenter, portfolio = false }) {
  const { session } = useAuth();
  const isAdmin = session?.is_super_admin || session?.is_admin;
  const today = new Date();
  const defaultMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;

  const [period, setPeriod] = useState({ type: 'month', month: defaultMonth });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [centers, setCenters] = useState([]);
  const [center, setCenter] = useState(propCenter || session?.center || '');

  useEffect(() => {
    fetch(`${API}/api/financial-health/list-centers`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: session.token }),
    })
      .then(r => r.json())
      .then(d => setCenters(d?.centers || []))
      .catch(() => {});
  }, [session.token]);

  const load = async () => {
    if (!portfolio && !center) return;
    setLoading(true);
    setData(null);
    try {
      const url = portfolio ? '/api/financial-health/portfolio' : '/api/financial-health/center';
      const body = portfolio ? { token: session.token, period }
                              : { token: session.token, center, period };
      const r = await fetch(`${API}${url}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Failed to load');
      setData(d);
    } catch (e) { toast.error(e.message); }
    setLoading(false);
  };

  // eslint-disable-next-line
  useEffect(() => { load(); }, [center, portfolio]);

  if (portfolio && !isAdmin) {
    return (
      <Card><CardContent className="py-12 text-center text-muted-foreground">
        🔒 Portfolio view is admin-only.
      </CardContent></Card>
    );
  }

  return (
    <div className="space-y-4" data-testid={portfolio ? 'fh-portfolio' : 'fh-center'}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-[#5C0000] flex items-center gap-2">
            <Activity className="w-6 h-6 text-rose-700" />
            {portfolio ? 'Portfolio Financial Health' : 'Center Financial Health'}
          </h2>
          <p className="text-sm text-muted-foreground">
            {portfolio
              ? 'Every center side-by-side · profitability, leakages, ranking'
              : 'Profitability snapshot · prime cost · alerts · recommended actions'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {!portfolio && (
            <Select value={center} onValueChange={setCenter}>
              <SelectTrigger className="h-9 w-56" data-testid="fh-center-picker">
                <SelectValue placeholder="Select center" />
              </SelectTrigger>
              <SelectContent>
                {centers.map(c => (
                  <SelectItem key={c.code} value={c.code}>
                    {c.code} · {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Button size="sm" onClick={load} disabled={loading}
            className="bg-[#8B0000] hover:bg-[#5C0000]" data-testid="fh-refresh">
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
                     : <RefreshCw className="w-3.5 h-3.5 mr-1" />}
            Refresh
          </Button>
        </div>
      </div>

      <PeriodPicker period={period} onChange={setPeriod} disabled={loading} />

      {loading && (
        <Card><CardContent className="py-12 text-center text-muted-foreground">
          <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />Computing health metrics…
        </CardContent></Card>
      )}

      {!loading && !data && (
        <Card><CardContent className="py-12 text-center text-muted-foreground">
          Choose a period and {portfolio ? 'click Refresh' : 'a center'} to view financial health.
        </CardContent></Card>
      )}

      {!portfolio && data && (
        <>
          <HealthScoreHero s={data.summary} />
          <AlertStack alerts={data.alerts} />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <StatCard testid="fh-stat-sales" label="Total Sales" value={fmtMoney(data.summary.total_sales)}
              sub={`${data.period.label} · ${data.period.from} → ${data.period.to}`}
              color="green" Icon={IndianRupee} />
            <StatCard testid="fh-stat-expenses"
              label={data.summary.adjustments > 0 ? "Adjusted Expenses" : "Total Expenses"}
              value={fmtMoney(data.summary.total_expenses)}
              sub={data.summary.adjustments > 0
                ? `Raw ${fmtMoney(data.summary.total_expenses_raw)} − Adj ${fmtMoney(data.summary.adjustments)}`
                : null}
              color="yellow" Icon={Activity} />
            <StatCard testid="fh-stat-np" label="Net Profit"
              value={`${fmtMoney(data.summary.net_profit)} (${fmtPct(data.summary.net_profit_pct)})`}
              color={data.summary.status_color} Icon={TrendingUp} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <PrimeCostMonitor p={data.prime_cost} />
            <FoodCostCard f={data.food_cost} />
            <LaborCostCard l={data.labor_cost} />
            <ContribMargin cm={data.contribution_margin} />
            <OrdersPerHour o={data.orders_per_labor_hour} />
          </div>

          <LeakageTable leaks={data.expense_leakage} />
          <Recommendations recs={data.recommendations} />
        </>
      )}

      {portfolio && data && (
        <>
          {/* Rankings cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
            {Object.entries(data.rankings).map(([key, row]) => {
              if (!row) return null;
              const labels = {
                best_performing: 'Best',
                worst_performing: 'Worst',
                highest_food_cost: 'Highest Food %',
                highest_labor_cost: 'Highest Labor %',
                highest_profit: 'Top Profit',
                lowest_profit: 'Lowest Profit',
              };
              return (
                <Card key={key} className="bg-stone-50">
                  <CardContent className="p-2.5">
                    <div className="text-[10px] uppercase tracking-wider text-stone-500">{labels[key]}</div>
                    <div className="text-sm font-bold text-[#5C0000]">{row.center}</div>
                    <div className="text-[10px] text-stone-600 truncate">{row.center_name}</div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Building className="w-4 h-4" />All Centers — {data.active_centers}/{data.total_centers} active
              </CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto p-0">
              <table className="w-full text-sm">
                <thead className="bg-stone-100 text-stone-700">
                  <tr>
                    <th className="px-3 py-2 text-left">Center</th>
                    <th className="px-3 py-2 text-right">Sales</th>
                    <th className="px-3 py-2 text-right">Food %</th>
                    <th className="px-3 py-2 text-right">Labor %</th>
                    <th className="px-3 py-2 text-right">Prime %</th>
                    <th className="px-3 py-2 text-right">Net Profit</th>
                    <th className="px-3 py-2 text-right">NP %</th>
                    <th className="px-3 py-2 text-center">Score</th>
                    <th className="px-3 py-2 text-center">Alerts</th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map(r => {
                    const c = COLORS[r.status_color] || COLORS.green;
                    return (
                      <tr key={r.center} className="border-t border-stone-100 hover:bg-amber-50/40">
                        <td className="px-3 py-2">
                          <div className="font-medium">{r.center}</div>
                          <div className="text-[10px] text-stone-500">{r.center_name}</div>
                        </td>
                        <td className="px-3 py-2 text-right font-medium">{fmtMoney(r.sales)}</td>
                        <td className="px-3 py-2 text-right">{fmtPct(r.food_cost_pct)}</td>
                        <td className="px-3 py-2 text-right">{fmtPct(r.labor_cost_pct)}</td>
                        <td className="px-3 py-2 text-right">{fmtPct(r.prime_cost_pct)}</td>
                        <td className="px-3 py-2 text-right">{fmtMoney(r.net_profit)}</td>
                        <td className="px-3 py-2 text-right">{fmtPct(r.net_profit_pct)}</td>
                        <td className="px-3 py-2 text-center">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] ${c.bg} ${c.text}`}>
                            <Award className="w-3 h-3" />{r.health_score}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-center">
                          {r.alerts > 0
                            ? <Badge variant="destructive" className="text-[10px]">{r.alerts}</Badge>
                            : <span className="text-emerald-600 text-[11px]">✓</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
