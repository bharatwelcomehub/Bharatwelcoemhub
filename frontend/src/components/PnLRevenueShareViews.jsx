import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Badge } from "./ui/badge";
import { Switch } from "./ui/switch";
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

const COLS = [
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
  { key: "profit_share_mfpl", label: "Profit Share MFPL" },
];

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

function GridTable({ rows, totals, loading }) {
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
            {COLS.map((c) => <th key={c.key} className="p-2 text-right whitespace-nowrap">{c.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {/* TOTAL ROW AT TOP */}
          <tr className="bg-amber-100 font-bold border-b-2 border-amber-400" data-testid="pnl-rs-totals-row">
            <td className="p-2 text-left">TOTAL</td>
            {COLS.slice(1).map((c) => (
              <td key={c.key} className="p-2 text-right">{fmt(totals?.[c.key])}</td>
            ))}
          </tr>
          {rows.map((r) => (
            <tr key={r.month} className="border-t hover:bg-slate-50" data-testid={`pnl-rs-row-${r.month}`}>
              <td className="p-2 text-left">{r.month}</td>
              {COLS.slice(1).map((c) => (
                <td key={c.key} className="p-2 text-right">{fmt(r[c.key])}</td>
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
  const [rsPct, setRsPct] = useState("15");
  const [gstOn, setGstOn] = useState(true);
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
          revenue_share_pct: Number(rsPct) || null,
          gst_applicable: gstOn,
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
  }, [center, fy, fromMonth, toMonth, rsPct, gstOn]);

  useEffect(() => { if (center) run(); }, [center, run]);

  const exportPdf = async () => {
    try {
      await postBinary(
        "/api/center-accounts/pnl-revenue-share-overview/export-pdf",
        {
          center, financial_year: fy || null,
          from_month: fromMonth || null, to_month: toMonth || null,
          revenue_share_pct: Number(rsPct) || null, gst_applicable: gstOn,
          account_manager: "—",
        },
        `PnL_RevenueShare_${center}.pdf`,
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
          revenue_share_pct: Number(rsPct) || null, gst_applicable: gstOn,
          account_manager: "—",
        },
        `PnL_RevenueShare_${center}.xlsx`,
      );
    } catch (e) { toast.error(e.message); }
  };

  return (
    <Card data-testid="pnl-rs-overview-card">
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle>P&amp;L Revenue Share Overview</CardTitle>
            <CardDescription>
              Month-wise actuals · Sale → Profit Share MFPL · {center || "select a center"}
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
        {/* Filters */}
        <div className="grid md:grid-cols-5 gap-2">
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
          <div>
            <Label className="text-xs">Revenue Share %</Label>
            <Select value={rsPct} onValueChange={setRsPct}>
              <SelectTrigger className="h-8" data-testid="pnl-rs-pct"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10 %</SelectItem>
                <SelectItem value="15">15 %</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">GST Applicable</Label>
            <div className="flex items-center gap-2 h-8">
              <Switch checked={gstOn} onCheckedChange={setGstOn} data-testid="pnl-rs-gst" />
              <span className="text-xs">{gstOn ? "Yes (18%)" : "No"}</span>
            </div>
          </div>
        </div>

        {data && (
          <div className="text-xs text-muted-foreground">
            Center: <b>{data.center_name}</b> · Period: <b>{data.filters?.financial_year || `${data.filters?.from_month} → ${data.filters?.to_month}`}</b>
          </div>
        )}

        <GridTable rows={data?.rows || []} totals={data?.totals} loading={loading} />
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
  const [rsPct, setRsPct] = useState("15");
  const [mgAmount, setMgAmount] = useState("");
  const [startMonth, setStartMonth] = useState("");
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
          years: Number(years), sales_growth_pct: Number(salesGrowth),
          expense_growth_pct: Number(expenseGrowth), gst_pct: Number(gstPct),
          revenue_share_pct: Number(rsPct),
          mg_amount: mgAmount ? Number(mgAmount) : null,
          start_month: startMonth || null,
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.detail || "Projection failed");
      setData(json);
      toast.success(`Projected ${json.rows?.length || 0} months`);
    } catch (e) {
      toast.error(e.message || "Projection failed");
    } finally { setLoading(false); }
  }, [center, years, salesGrowth, expenseGrowth, gstPct, rsPct, mgAmount, startMonth]);

  const exportPdf = async () => {
    try {
      await postBinary("/api/center-accounts/revenue-share-projection/export-pdf",
        { center, years: Number(years), sales_growth_pct: Number(salesGrowth),
          expense_growth_pct: Number(expenseGrowth), gst_pct: Number(gstPct),
          revenue_share_pct: Number(rsPct), mg_amount: mgAmount ? Number(mgAmount) : null,
          start_month: startMonth || null, account_manager: "—",
        },
        `RevenueShareProjection_${center}.pdf`);
    } catch (e) { toast.error(e.message); }
  };
  const exportExcel = async () => {
    try {
      await postBinary("/api/center-accounts/revenue-share-projection/export-excel",
        { center, years: Number(years), sales_growth_pct: Number(salesGrowth),
          expense_growth_pct: Number(expenseGrowth), gst_pct: Number(gstPct),
          revenue_share_pct: Number(rsPct), mg_amount: mgAmount ? Number(mgAmount) : null,
          start_month: startMonth || null, account_manager: "—",
        },
        `RevenueShareProjection_${center}.xlsx`);
    } catch (e) { toast.error(e.message); }
  };

  return (
    <Card data-testid="rs-projection-card">
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" /> Revenue Share Projection
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
        <div className="grid md:grid-cols-4 gap-3">
          <div>
            <Label className="text-xs">Projection Years</Label>
            <Select value={years} onValueChange={setYears}>
              <SelectTrigger className="h-8" data-testid="rs-proj-years"><SelectValue /></SelectTrigger>
              <SelectContent>
                {[1, 2, 3, 4, 5].map((y) => <SelectItem key={y} value={String(y)}>{y} Year{y > 1 ? "s" : ""}</SelectItem>)}
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
          <div>
            <Label className="text-xs">Revenue Share %</Label>
            <Input type="number" step="0.1" value={rsPct} onChange={(e) => setRsPct(e.target.value)} className="h-8" data-testid="rs-proj-rs-pct" />
          </div>
          <div>
            <Label className="text-xs">GST %</Label>
            <Input type="number" step="0.1" value={gstPct} onChange={(e) => setGstPct(e.target.value)} className="h-8" data-testid="rs-proj-gst-pct" />
          </div>
          <div>
            <Label className="text-xs">MG Amount (override)</Label>
            <Input type="number" step="100" value={mgAmount} onChange={(e) => setMgAmount(e.target.value)} className="h-8" placeholder="auto = last actual" data-testid="rs-proj-mg" />
          </div>
          <div className="flex items-end">
            <Button size="sm" className="h-8 w-full" onClick={run} disabled={loading || !center} data-testid="rs-proj-run">
              {loading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Sparkles className="h-4 w-4 mr-1" />}
              Run Projection
            </Button>
          </div>
        </div>

        {data?.baseline_seed_months?.length > 0 && (
          <div className="text-xs text-muted-foreground">
            Seeded from <Badge variant="outline">{data.baseline_seed_months.join(", ")}</Badge>
            · Avg seed sale ₹{fmt(data.totals && data.rows?.length ? data.totals.sale / data.rows.length / Math.pow(1 + Number(salesGrowth) / 100, data.rows.length / 2) : 0)}
          </div>
        )}

        <GridTable rows={data?.rows || []} totals={data?.totals} loading={loading} />
      </CardContent>
    </Card>
  );
}
