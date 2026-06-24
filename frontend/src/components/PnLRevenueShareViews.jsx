import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Badge } from "./ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "./ui/select";
import {
  FileSpreadsheet, FileText, Loader2, RefreshCw, Sparkles,
} from "lucide-react";
import { toast } from "sonner";

const API = process.env.REACT_APP_BACKEND_URL;
const getToken = () => {
  try { return (JSON.parse(localStorage.getItem("pb_session_v2") || "{}").token) || ""; }
  catch { return ""; }
};

const fmt = (n) => Number(n || 0).toLocaleString("en-IN", {
  minimumFractionDigits: 2, maximumFractionDigits: 2,
});

const COLS_RS = [
  { key: "month", label: "Month", numeric: false },
  { key: "sale", label: "Sale" },
  { key: "expenses", label: "Expenses" },
  { key: "pnl", label: "P / L" },
  { key: "revenue_share_base", label: "Rev Share Base" },
  { key: "revenue_share_amount", label: "Revenue Share" },
  { key: "revenue_share_plus_gst", label: "Rev Share + GST" },
  { key: "mg_amount", label: "MG" },
  { key: "mg_plus_gst", label: "MG + GST" },
  { key: "amount_paid", label: "Amount Paid" },
  { key: "eligible_adjustments", label: "Eligible Adj." },
  { key: "profit_share_mfpl", label: "Profit Share MFPL" },
];

const COLS_PS = [
  { key: "month", label: "Month", numeric: false },
  { key: "sale", label: "Sale" },
  { key: "expenses", label: "Expenses" },
  { key: "expense_adjustment", label: "Expense Adj." },
  { key: "adjusted_expenses", label: "Adjusted Expenses" },
  { key: "commissions", label: "Commissions" },
  { key: "commission_gst", label: "Commission GST" },
  { key: "profit_share_base", label: "Profit Share Base" },
  { key: "franchise_share", label: "Franchise Share" },
  { key: "mfpl_share", label: "MFPL Share" },
  { key: "amount_paid", label: "Amount Paid" },
  { key: "pending", label: "Pending" },
  { key: "status", label: "Status", numeric: false, text: true },
];

const colsFor = (model) => (model === "profit_share" ? COLS_PS : COLS_RS);

function statusBadge(s) {
  const map = {
    Paid: "bg-emerald-100 text-emerald-800 border-emerald-300",
    Partial: "bg-amber-100 text-amber-800 border-amber-300",
    Pending: "bg-slate-100 text-slate-700 border-slate-300",
    Projected: "bg-indigo-100 text-indigo-800 border-indigo-300",
  };
  const cls = map[s] || "bg-slate-100 text-slate-700 border-slate-300";
  return <span className={`px-2 py-0.5 rounded border text-[10px] font-semibold ${cls}`}>{s || "—"}</span>;
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click();
  a.remove(); setTimeout(() => URL.revokeObjectURL(url), 5000);
}

async function postBinary(path, payload, filename) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: getToken(), ...payload }),
  });
  if (!res.ok) throw new Error(`Download failed (${res.status})`);
  downloadBlob(await res.blob(), filename);
}

function GridTable({ rows, totals, loading, payoutModel = "revenue_share" }) {
  const cols = colsFor(payoutModel);
  if (loading) {
    return <div className="flex items-center text-sm text-muted-foreground p-6"><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Loading…</div>;
  }
  if (!rows?.length) {
    return <div className="text-sm text-muted-foreground py-8 text-center" data-testid="pnl-rs-grid-empty">No data for the selected filters.</div>;
  }
  return (
    <div className="overflow-x-auto border rounded">
      <table className="w-full text-xs" data-testid="pnl-rs-grid-table">
        <thead className="bg-slate-700 text-white sticky top-0">
          <tr>
            {cols.map((c) => <th key={c.key} className={`p-2 ${c.text ? "text-center" : "text-right"} whitespace-nowrap`}>{c.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {/* TOTAL ROW AT TOP */}
          <tr className="bg-amber-100 font-bold border-b-2 border-amber-400" data-testid="pnl-rs-totals-row">
            <td className="p-2 text-left">TOTAL</td>
            {cols.slice(1).map((c) => (
              <td key={c.key} className={`p-2 ${c.text ? "text-center" : "text-right"}`}>{c.text ? "" : fmt(totals?.[c.key])}</td>
            ))}
          </tr>
          {rows.map((r) => (
            <tr key={r.month} className="border-t hover:bg-slate-50" data-testid={`pnl-rs-row-${r.month}`}>
              <td className="p-2 text-left">{r.month}</td>
              {cols.slice(1).map((c) => (
                <td key={c.key} className={`p-2 ${c.text ? "text-center" : "text-right"}`}>
                  {c.key === "status" ? statusBadge(r[c.key]) : fmt(r[c.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── */
/* P&L Revenue Share Overview                                 */
/* ─────────────────────────────────────────────────────────── */
export function PnLRevenueShareOverview({ center }) {
  const [fy, setFy] = useState("");
  const [fromMonth, setFromMonth] = useState("");
  const [toMonth, setToMonth] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fyOptions = (() => {
    const now = new Date();
    const baseYr = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
    const out = [];
    for (let i = 0; i < 6; i++) {
      const y = baseYr - i;
      out.push(`${y}-${String((y + 1) % 100).padStart(2, "0")}`);
    }
    return out;
  })();

  const run = useCallback(async () => {
    if (!center) { toast.error("Select a center first"); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/center-accounts/pnl-revenue-share-overview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: getToken(), center,
          financial_year: fy || null,
          from_month: fromMonth || null, to_month: toMonth || null,
          // payout_model & share % are now pulled from Franchise Management.
          // GST is left unset so backend uses the franchise's gst_applicable flag.
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.detail || "Load failed");
      setData(json);
    } catch (e) {
      toast.error(e.message || "Load failed");
    } finally {
      setLoading(false);
    }
  }, [center, fy, fromMonth, toMonth]);

  useEffect(() => { if (center) run(); }, [center, run]);

  const exportPdf = async () => {
    try {
      await postBinary(
        "/api/center-accounts/pnl-revenue-share-overview/export-pdf",
        {
          center, financial_year: fy || null,
          from_month: fromMonth || null, to_month: toMonth || null,
          account_manager: "—",
        },
        `PnL_${data?.payout_model_label || "RevenueShare"}_${center}.pdf`.replace(/\s+/g, "_"),
      );
    } catch (e) { toast.error(e.message); }
  };
  const exportExcel = async () => {
    try {
      await postBinary(
        "/api/center-accounts/pnl-revenue-share-overview/export-excel",
        {
          center, financial_year: fy || null,
          from_month: fromMonth || null, to_month: toMonth || null,
          account_manager: "—",
        },
        `PnL_${data?.payout_model_label || "RevenueShare"}_${center}.xlsx`.replace(/\s+/g, "_"),
      );
    } catch (e) { toast.error(e.message); }
  };

  const isPS = data?.payout_model === "profit_share";

  return (
    <Card data-testid="pnl-rs-overview-card">
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle>P&amp;L {data?.payout_model_label || "Revenue Share"} Overview</CardTitle>
            <CardDescription>
              Month-wise actuals · {isPS ? "Sale → Franchise Share / MFPL Share" : "Sale → Profit Share MFPL"} · {center || "select a center"}
            </CardDescription>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button size="sm" variant="outline" onClick={run} disabled={loading || !center} data-testid="pnl-rs-refresh">
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} /> Refresh
            </Button>
            <Button size="sm" variant="outline" onClick={exportPdf} disabled={!data} data-testid="pnl-rs-pdf">
              <FileText className="h-4 w-4 mr-1" /> Download PDF
            </Button>
            <Button size="sm" variant="outline" onClick={exportExcel} disabled={!data} data-testid="pnl-rs-excel">
              <FileSpreadsheet className="h-4 w-4 mr-1" /> Download Excel
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Business Model + Share % — read-only from Franchise Management */}
        {data && (
          <div className="flex flex-wrap gap-2 items-center text-xs border rounded p-2 bg-slate-50" data-testid="pnl-rs-model-banner">
            <span className="text-muted-foreground">Business Model:</span>
            <Badge variant={isPS ? "default" : "secondary"} data-testid="pnl-rs-model-badge">
              {data.payout_model_label}
            </Badge>
            {isPS ? (
              <>
                <span className="text-muted-foreground ml-3">Franchise Share:</span>
                <Badge variant="outline">{data.franchise_owner_share_percentage}%</Badge>
                <span className="text-muted-foreground ml-2">MFPL Share:</span>
                <Badge variant="outline">{data.mfpl_share_percentage}%</Badge>
              </>
            ) : (
              <>
                <span className="text-muted-foreground ml-3">Revenue Share:</span>
                <Badge variant="outline">{data.franchise_owner_share_percentage}%</Badge>
                <span className="text-muted-foreground ml-2">GST:</span>
                <Badge variant="outline">{data.filters?.gst_applicable ? "Yes (18%)" : "No"}</Badge>
              </>
            )}
            <span className="ml-auto text-muted-foreground italic">
              Configure these in <b>Franchise Management → Edit</b>
            </span>
          </div>
        )}

        {/* Filters — only period selectors stay; % and model come from Franchise */}
        <div className="grid md:grid-cols-3 gap-2">
          <div>
            <Label className="text-xs">Financial Year</Label>
            <Select value={fy} onValueChange={(v) => { setFy(v); setFromMonth(""); setToMonth(""); }}>
              <SelectTrigger className="h-8" data-testid="pnl-rs-fy"><SelectValue placeholder="Pick FY" /></SelectTrigger>
              <SelectContent>{fyOptions.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">From Month</Label>
            <Input type="month" value={fromMonth} onChange={(e) => { setFromMonth(e.target.value); setFy(""); }} className="h-8" data-testid="pnl-rs-from" />
          </div>
          <div>
            <Label className="text-xs">To Month</Label>
            <Input type="month" value={toMonth} onChange={(e) => { setToMonth(e.target.value); setFy(""); }} className="h-8" data-testid="pnl-rs-to" />
          </div>
        </div>

        {data && (
          <div className="text-xs text-muted-foreground">
            Center: <b>{data.center_name}</b> · Country: <b>{data.country}</b> · Period: <b>{data.filters?.financial_year || `${data.filters?.from_month} → ${data.filters?.to_month}`}</b>
          </div>
        )}

        <GridTable rows={data?.rows || []} totals={data?.totals} loading={loading} payoutModel={data?.payout_model} />
      </CardContent>
    </Card>
  );
}

/* ─────────────────────────────────────────────────────────── */
/* Revenue Share Projection                                   */
/* ─────────────────────────────────────────────────────────── */
export function RevenueShareProjection({ center }) {
  const [years, setYears] = useState("3");
  const [salesGrowth, setSalesGrowth] = useState("3");
  const [expenseGrowth, setExpenseGrowth] = useState("2");
  const [gstPct, setGstPct] = useState("18");
  const [mgAmount, setMgAmount] = useState("");
  const [startMonth, setStartMonth] = useState("");
  const [earlyExitYear, setEarlyExitYear] = useState("");        // "" = disabled
  const [profitReductionPct, setProfitReductionPct] = useState("10");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const run = useCallback(async () => {
    if (!center) { toast.error("Select a center first"); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/center-accounts/revenue-share-projection`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: getToken(), center,
          years: Number(years),
          // Use 0 fallback (not undefined) so backend honours user-entered zero.
          sales_growth_pct: salesGrowth === "" ? 0 : Number(salesGrowth),
          expense_growth_pct: expenseGrowth === "" ? 0 : Number(expenseGrowth),
          gst_pct: gstPct === "" ? 0 : Number(gstPct),
          mg_amount: mgAmount ? Number(mgAmount) : null,
          start_month: startMonth || null,
          early_exit_year: earlyExitYear ? Number(earlyExitYear) : null,
          profit_reduction_pct: Number(profitReductionPct) || 10,
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.detail || "Projection failed");
      setData(json);
      toast.success(`Projected ${json.rows?.length || 0} months · ${json.payout_model_label}`);
    } catch (e) {
      toast.error(e.message || "Projection failed");
    } finally { setLoading(false); }
  }, [center, years, salesGrowth, expenseGrowth, gstPct, mgAmount, startMonth, earlyExitYear, profitReductionPct]);

  // Common payload for exports — ensures PDF/Excel always uses LATEST inputs
  const buildExportBody = () => ({
    center,
    years: Number(years),
    sales_growth_pct: salesGrowth === "" ? 0 : Number(salesGrowth),
    expense_growth_pct: expenseGrowth === "" ? 0 : Number(expenseGrowth),
    gst_pct: gstPct === "" ? 0 : Number(gstPct),
    mg_amount: mgAmount ? Number(mgAmount) : null,
    start_month: startMonth || null,
    early_exit_year: earlyExitYear ? Number(earlyExitYear) : null,
    profit_reduction_pct: Number(profitReductionPct) || 10,
    account_manager: "—",
  });

  const exportPdf = async () => {
    try {
      await postBinary("/api/center-accounts/revenue-share-projection/export-pdf",
        buildExportBody(),
        `Projection_${data?.payout_model_label || ""}_${center}.pdf`.replace(/\s+/g, "_"));
    } catch (e) { toast.error(e.message); }
  };
  const exportExcel = async () => {
    try {
      await postBinary("/api/center-accounts/revenue-share-projection/export-excel",
        buildExportBody(),
        `Projection_${data?.payout_model_label || ""}_${center}.xlsx`.replace(/\s+/g, "_"));
    } catch (e) { toast.error(e.message); }
  };

  const isPS = data?.payout_model === "profit_share";

  return (
    <Card data-testid="rs-projection-card">
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" /> {data?.payout_model_label || "Revenue Share"} Projection
            </CardTitle>
            <CardDescription>
              Forward projection from the last 3 actual months of {center || "this center"} with your growth assumptions.
            </CardDescription>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button size="sm" variant="outline" onClick={exportPdf} disabled={!data} data-testid="rs-proj-pdf">
              <FileText className="h-4 w-4 mr-1" /> Download PDF
            </Button>
            <Button size="sm" variant="outline" onClick={exportExcel} disabled={!data} data-testid="rs-proj-excel">
              <FileSpreadsheet className="h-4 w-4 mr-1" /> Download Excel
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {data && (
          <div className="flex flex-wrap gap-2 items-center text-xs border rounded p-2 bg-slate-50" data-testid="rs-proj-model-banner">
            <span className="text-muted-foreground">Business Model:</span>
            <Badge variant={isPS ? "default" : "secondary"}>{data.payout_model_label}</Badge>
            {isPS ? (
              <>
                <span className="text-muted-foreground ml-3">Franchise Share:</span>
                <Badge variant="outline">{data.franchise_owner_share_percentage}%</Badge>
                <span className="text-muted-foreground ml-2">MFPL Share:</span>
                <Badge variant="outline">{data.mfpl_share_percentage}%</Badge>
              </>
            ) : (
              <>
                <span className="text-muted-foreground ml-3">Revenue Share:</span>
                <Badge variant="outline">{data.franchise_owner_share_percentage}%</Badge>
              </>
            )}
            <span className="ml-auto text-muted-foreground italic">From <b>Franchise Management</b></span>
          </div>
        )}

        <div className="grid md:grid-cols-4 gap-3">
          <div>
            <Label className="text-xs">Projection Years</Label>
            <Select value={years} onValueChange={setYears}>
              <SelectTrigger className="h-8" data-testid="rs-proj-years"><SelectValue /></SelectTrigger>
              <SelectContent>
                {[1, 2, 3, 4, 5, 6, 7].map((y) => <SelectItem key={y} value={String(y)}>{y} Year{y > 1 ? "s" : ""}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Starting Month</Label>
            <Input type="month" value={startMonth} onChange={(e) => setStartMonth(e.target.value)} className="h-8" placeholder="auto = next month" data-testid="rs-proj-start" />
          </div>
          <div>
            <Label className="text-xs">Monthly Sales Growth %</Label>
            <Input type="number" step="0.1" value={salesGrowth} onChange={(e) => setSalesGrowth(e.target.value)} className="h-8" data-testid="rs-proj-sales-growth" />
          </div>
          <div>
            <Label className="text-xs">Expense Growth %</Label>
            <Input type="number" step="0.1" value={expenseGrowth} onChange={(e) => setExpenseGrowth(e.target.value)} className="h-8" data-testid="rs-proj-expense-growth" />
          </div>
          {!isPS && (
            <>
              <div>
                <Label className="text-xs">GST %</Label>
                <Input type="number" step="0.1" value={gstPct} onChange={(e) => setGstPct(e.target.value)} className="h-8" data-testid="rs-proj-gst-pct" />
              </div>
              <div>
                <Label className="text-xs">MG Amount (override)</Label>
                <Input type="number" step="100" value={mgAmount} onChange={(e) => setMgAmount(e.target.value)} className="h-8" placeholder="auto = last actual" data-testid="rs-proj-mg" />
              </div>
            </>
          )}
          <div className="flex items-end">
            <Button size="sm" className="h-8 w-full" onClick={run} disabled={loading || !center} data-testid="rs-proj-run">
              {loading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Sparkles className="h-4 w-4 mr-1" />}
              Run Projection
            </Button>
          </div>
        </div>

        {/* ── Early Exit Profitability Loss inputs ── */}
        <details className="border-2 border-rose-200 rounded p-3 bg-rose-50/40" data-testid="rs-proj-early-exit-section" open={!!earlyExitYear}>
          <summary className="cursor-pointer font-medium text-sm flex items-center gap-2">
            <span className="text-rose-700">Franchise Early-Exit Profitability Loss</span>
            <span className="text-xs text-muted-foreground italic">— estimate what MFPL forfeits if the franchise exits before the 7-year tenure</span>
          </summary>
          <div className="grid md:grid-cols-3 gap-3 mt-3">
            <div>
              <Label className="text-xs">Expected Tenure</Label>
              <Input value="7 years" disabled className="h-8 bg-slate-50" />
            </div>
            <div>
              <Label className="text-xs">Actual Exit Year</Label>
              <Select value={earlyExitYear || "none"} onValueChange={(v) => setEarlyExitYear(v === "none" ? "" : v)}>
                <SelectTrigger className="h-8" data-testid="rs-proj-exit-year"><SelectValue placeholder="Pick year" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">— (don&apos;t compute) —</SelectItem>
                  {[1, 2, 3, 4, 5, 6].map((y) => <SelectItem key={y} value={String(y)}>After Year {y}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Profit Reduction %</Label>
              <Select value={profitReductionPct} onValueChange={setProfitReductionPct}>
                <SelectTrigger className="h-8" data-testid="rs-proj-reduction"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="10">10% (conservative)</SelectItem>
                  <SelectItem value="12">12% (very conservative)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {data?.early_exit && (
            <div className="mt-4 rounded border-2 border-rose-300 bg-white p-3" data-testid="rs-proj-early-exit-result">
              <div className="text-xs uppercase tracking-wider text-rose-700 font-semibold mb-2">
                Loss if franchise exits after Year {data.early_exit.exit_year}
              </div>
              <div className="grid md:grid-cols-4 gap-3 text-sm">
                <div>
                  <div className="text-xs text-muted-foreground">Remaining Years</div>
                  <div className="font-semibold">{data.early_exit.remaining_years}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Projected MFPL (7yr)</div>
                  <div className="font-semibold">{fmt(data.early_exit.projected_mfpl_7yr)}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Projected MFPL (remaining)</div>
                  <div className="font-semibold">{fmt(data.early_exit.projected_mfpl_remaining)}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Conservative Loss ({data.early_exit.profit_reduction_pct}%)</div>
                  <div className="font-bold text-rose-700 text-base">{fmt(data.early_exit.conservative_loss)}</div>
                </div>
              </div>
              <div className="text-xs text-muted-foreground italic mt-2">{data.early_exit.note}</div>
            </div>
          )}
        </details>

        {data?.baseline_seed_months?.length > 0 && (
          <div className="text-xs text-muted-foreground">
            Seeded from <Badge variant="outline">{data.baseline_seed_months.join(", ")}</Badge>
          </div>
        )}

        <GridTable rows={data?.rows || []} totals={data?.totals} loading={loading} payoutModel={data?.payout_model} />
      </CardContent>
    </Card>
  );
}
