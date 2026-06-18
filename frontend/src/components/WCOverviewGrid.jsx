import React, { useState, useEffect, useCallback, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Input } from "./ui/input";
import {
  FileSpreadsheet, FileText, Loader2, Save, RotateCcw,
} from "lucide-react";
import { toast } from "sonner";

/**
 * Working-Capital Month-wise Overview Grid
 *
 * Restores the legacy "Overview" grid screen requested by the user (Feb-2026):
 *   Month · Opening WC · Sales · GST · Expenses · Commissions ·
 *   Net Available (Op. Balance) · Revenue Share Base · Closing WC · Status.
 *
 * • Editable cells: GST · Expenses · Commissions · WC Adjustment (the four
 *   the backend `/wc-row-save` route supports as `_target` overrides). Sales
 *   is read-only (sourced from daily-sales).
 * • Auto-recalculation runs CLIENT-SIDE as the user types so they see the new
 *   Net Available / Revenue Share Base / Closing WC instantly — Save commits
 *   the override + INTRA CENTER ADJUSTMENT side effect.
 * • Totals row directly under the header (bold, amber).
 * • Download PDF / Excel reuses the existing landscape-PDF + Excel exports.
 */

const fmt = (n, cur = "Rs.") => {
  const v = Number(n || 0);
  return `${cur} ${v.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};
const fmtNum = (n) => {
  const v = Number(n || 0);
  return v.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};
const fmtMonth = (m) => {
  if (!m || typeof m !== "string" || !m.includes("-")) return m || "";
  const [y, mm] = m.split("-");
  return new Date(Number(y), Number(mm) - 1, 1)
    .toLocaleDateString("en-US", { month: "short", year: "numeric" });
};

// Tiny editable-number cell — keeps "string while typing", commits to number onBlur
function NumCell({ value, onChange, disabled, testid }) {
  const [draft, setDraft] = useState(String(Number(value || 0)));
  useEffect(() => { setDraft(String(Number(value || 0))); }, [value]);
  return (
    <Input
      type="number"
      step="0.01"
      value={draft}
      disabled={disabled}
      onChange={(e) => {
        setDraft(e.target.value);
        const n = parseFloat(e.target.value);
        if (!Number.isNaN(n)) onChange(n);
      }}
      onBlur={() => {
        const n = parseFloat(draft);
        if (Number.isNaN(n)) { setDraft(String(Number(value || 0))); return; }
        onChange(n);
      }}
      className="h-7 text-xs text-right bg-white"
      data-testid={testid}
    />
  );
}

export function WCOverviewGrid({ apiBase, token, center, country, cur = "Rs." }) {
  const [serverRows, setServerRows] = useState([]);
  const [edits, setEdits] = useState({});  // month → { gst, expenses, commission, wc_adjustment }
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(null);
  const [savingMonth, setSavingMonth] = useState(null);
  const [meta, setMeta] = useState({ base_wc: 0, current_wc: 0, status: "" });

  const load = useCallback(async () => {
    if (!center) return;
    setLoading(true);
    setEdits({});
    try {
      const res = await fetch(`${apiBase}/api/center-accounts/wc-table`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, center }),
      });
      const data = await res.json();
      if (!res.ok || !data?.success) throw new Error(data?.detail || "Failed");
      setServerRows(data.rows || []);
      setMeta({
        base_wc: Number(data.base_wc || 0),
        current_wc: Number(data.current_wc || 0),
        status: data.current_status || "",
      });
    } catch (e) {
      toast.error(e.message || "Failed to load Working Capital overview");
    } finally {
      setLoading(false);
    }
  }, [apiBase, token, center]);

  useEffect(() => { load(); }, [load]);

  // Merge server rows with in-flight edits so the user sees their typed
  // values + recomputed Net Available / RSB / Closing WC live.
  const rows = useMemo(() => {
    const merged = serverRows.map((r) => {
      const e = edits[r.month] || {};
      const sale = Number(r.sale || 0);
      const gst = e.gst !== undefined ? Number(e.gst) : Number(r.gst || 0);
      const expenses = e.expenses !== undefined ? Number(e.expenses) : Number(r.expenses || 0);
      const commission = e.commission !== undefined ? Number(e.commission) : Number(r.commission || 0);
      const wc_adj = e.wc_adjustment !== undefined
        ? Number(e.wc_adjustment)
        : Number(r.wc_adjustment || 0);
      const op_balance = sale - expenses - commission;
      const rev_share_base = Math.max(0, sale - commission - gst);
      return {
        ...r, sale, gst, expenses, commission,
        operational_balance: op_balance,
        revenue_share_base: rev_share_base,
        wc_adjustment: wc_adj,
        // Closing WC preview — uses opening_wc from server (chain anchor) +
        // new operational balance + wc_adjustment + topup + other_income.
        closing_wc:
          Number(r.opening_wc || 0)
          + op_balance
          + wc_adj
          + Number(r.topup || 0)
          + Number(r.other_income || 0),
        _dirty: Boolean(e.gst !== undefined || e.expenses !== undefined
                       || e.commission !== undefined || e.wc_adjustment !== undefined),
      };
    });
    return merged;
  }, [serverRows, edits]);

  const totals = useMemo(() => rows.reduce((acc, r) => ({
    sale: acc.sale + Number(r.sale || 0),
    gst: acc.gst + Number(r.gst || 0),
    expenses: acc.expenses + Number(r.expenses || 0),
    commission: acc.commission + Number(r.commission || 0),
    operational_balance: acc.operational_balance + Number(r.operational_balance || 0),
    revenue_share_base: acc.revenue_share_base + Number(r.revenue_share_base || 0),
  }), { sale: 0, gst: 0, expenses: 0, commission: 0, operational_balance: 0, revenue_share_base: 0 }), [rows]);

  const setEdit = (month, field, value) => {
    setEdits((d) => ({ ...d, [month]: { ...(d[month] || {}), [field]: value } }));
  };

  const resetRow = (month) => {
    setEdits((d) => { const copy = { ...d }; delete copy[month]; return copy; });
  };

  const saveRow = async (row) => {
    const e = edits[row.month];
    if (!e) return;
    setSavingMonth(row.month);
    try {
      const payload = { token, center, month: row.month };
      // Use absolute *_target fields so the backend mirrors an INTRA row.
      if (e.expenses !== undefined) payload.target_expenses = Number(e.expenses);
      if (e.gst !== undefined) payload.gst_target = Number(e.gst);
      if (e.commission !== undefined) payload.commission_target = Number(e.commission);
      if (e.wc_adjustment !== undefined) payload.wc_adjustment = Number(e.wc_adjustment);
      const res = await fetch(`${apiBase}/api/center-accounts/wc-row-save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok || !data?.success) throw new Error(data?.detail || data?.message || "Save failed");
      toast.success(`Saved ${row.month}`);
      await load();   // refresh from server so chain recomputes
    } catch (err) {
      toast.error(err.message || "Save failed");
    } finally {
      setSavingMonth(null);
    }
  };

  const downloadFile = async (kind) => {
    setDownloading(kind);
    try {
      const url = `${apiBase}/api/center-accounts/wc-table/export-${kind}`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, center }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const link = document.createElement("a");
      link.href = window.URL.createObjectURL(blob);
      link.download = kind === "pdf"
        ? `WC_Overview_${center}.pdf`
        : `WC_Overview_${center}.xlsx`;
      link.click();
      window.URL.revokeObjectURL(link.href);
      toast.success(`${kind.toUpperCase()} downloaded`);
    } catch (e) {
      toast.error(e.message || "Download failed");
    } finally {
      setDownloading(null);
    }
  };

  const statusPillClass = (s) =>
    s === "active" ? "bg-green-100 text-green-800 border-green-300"
    : s === "restoring" ? "bg-amber-100 text-amber-800 border-amber-300"
    : s === "blocked" ? "bg-red-100 text-red-800 border-red-300"
    : "bg-gray-100 text-gray-700 border-gray-300";

  return (
    <Card data-testid="wc-overview-grid-card" className="border-purple-200">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="w-4 h-4 text-purple-700" />
              Working Capital — Month-wise Overview (Editable)
            </CardTitle>
            <p className="text-[11px] text-muted-foreground mt-1">
              Base WC: <strong>{fmt(meta.base_wc, cur)}</strong>
              {" · "}Current WC: <strong>{fmt(meta.current_wc, cur)}</strong>
              {meta.status && (
                <Badge variant="outline" className={`ml-2 ${statusPillClass(meta.status)}`}>{meta.status}</Badge>
              )}
              <span className="ml-2 text-amber-700">· Edit GST / Expenses / Commissions / WC Adj → Save → row chain recomputes.</span>
            </p>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline"
                    disabled={!rows.length || downloading === "pdf"}
                    onClick={() => downloadFile("pdf")}
                    data-testid="wc-overview-download-pdf">
              {downloading === "pdf" ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <FileText className="w-4 h-4 mr-1" />}
              Download PDF
            </Button>
            <Button size="sm" variant="outline"
                    disabled={!rows.length || downloading === "excel"}
                    onClick={() => downloadFile("excel")}
                    data-testid="wc-overview-download-excel">
              {downloading === "excel" ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <FileSpreadsheet className="w-4 h-4 mr-1" />}
              Download Excel
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-xs" data-testid="wc-overview-table">
            <thead>
              <tr className="bg-purple-50 border-b border-purple-200 text-purple-900">
                <th className="text-left py-2 px-3 font-semibold">Month</th>
                <th className="text-right py-2 px-3 font-semibold">Opening WC</th>
                <th className="text-right py-2 px-3 font-semibold">Sales</th>
                <th className="text-right py-2 px-3 font-semibold w-[110px]">GST <span className="text-amber-600">✎</span></th>
                <th className="text-right py-2 px-3 font-semibold w-[110px]">Expenses <span className="text-amber-600">✎</span></th>
                <th className="text-right py-2 px-3 font-semibold w-[110px]">Commissions <span className="text-amber-600">✎</span></th>
                <th className="text-right py-2 px-3 font-semibold">Net Available</th>
                <th className="text-right py-2 px-3 font-semibold">Revenue Share Base</th>
                <th className="text-right py-2 px-3 font-semibold w-[110px]">WC Adj <span className="text-amber-600">✎</span></th>
                <th className="text-right py-2 px-3 font-semibold">Closing WC</th>
                <th className="text-center py-2 px-3 font-semibold w-[100px]">Action</th>
              </tr>
              {rows.length > 0 && (
                <tr className="bg-amber-50 border-b-2 border-amber-300 font-bold" data-testid="wc-overview-totals-row">
                  <td className="py-2 px-3 text-amber-900 uppercase text-[10px] tracking-wider">Total</td>
                  <td className="py-2 px-3 text-right text-amber-900">—</td>
                  <td className="py-2 px-3 text-right text-blue-900" data-testid="wc-totals-sales">{fmt(totals.sale, cur)}</td>
                  <td className="py-2 px-3 text-right text-orange-700" data-testid="wc-totals-gst">{fmt(totals.gst, cur)}</td>
                  <td className="py-2 px-3 text-right text-rose-700" data-testid="wc-totals-expenses">{fmt(totals.expenses, cur)}</td>
                  <td className="py-2 px-3 text-right text-rose-700" data-testid="wc-totals-commissions">{fmt(totals.commission, cur)}</td>
                  <td className="py-2 px-3 text-right text-emerald-700" data-testid="wc-totals-netavail">{fmt(totals.operational_balance, cur)}</td>
                  <td className="py-2 px-3 text-right text-sky-900" data-testid="wc-totals-rev-share-base">{fmt(totals.revenue_share_base, cur)}</td>
                  <td className="py-2 px-3 text-right text-amber-900">—</td>
                  <td className="py-2 px-3 text-right text-amber-900">—</td>
                  <td className="py-2 px-3 text-center text-amber-900">—</td>
                </tr>
              )}
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={11} className="py-6 text-center text-muted-foreground"><Loader2 className="w-4 h-4 inline mr-2 animate-spin" /> Loading…</td></tr>
              )}
              {!loading && rows.length === 0 && (
                <tr><td colSpan={11} className="py-6 text-center text-muted-foreground">No data available for this center.</td></tr>
              )}
              {!loading && rows.map((r) => {
                const opBalance = Number(r.operational_balance || 0);
                const rsbVal = Number(r.revenue_share_base || 0);
                const closing = Number(r.closing_wc || 0);
                return (
                  <tr key={r.month} className={`border-b border-gray-100 hover:bg-purple-50/40 ${r._dirty ? "bg-amber-50/50" : ""}`} data-testid={`wc-overview-row-${r.month}`}>
                    <td className="py-1 px-3 font-medium">{fmtMonth(r.month)}</td>
                    <td className="py-1 px-3 text-right text-gray-700">{fmtNum(r.opening_wc)}</td>
                    <td className="py-1 px-3 text-right text-blue-700">{fmtNum(r.sale)}</td>
                    <td className="py-1 px-1">
                      <NumCell value={r.gst} onChange={(v) => setEdit(r.month, "gst", v)} testid={`wc-edit-gst-${r.month}`} />
                    </td>
                    <td className="py-1 px-1">
                      <NumCell value={r.expenses} onChange={(v) => setEdit(r.month, "expenses", v)} testid={`wc-edit-expenses-${r.month}`} />
                    </td>
                    <td className="py-1 px-1">
                      <NumCell value={r.commission} onChange={(v) => setEdit(r.month, "commission", v)} testid={`wc-edit-commission-${r.month}`} />
                    </td>
                    <td className={`py-1 px-3 text-right font-semibold ${opBalance >= 0 ? "text-emerald-700" : "text-red-700"}`}>{fmtNum(opBalance)}</td>
                    <td className="py-1 px-3 text-right text-sky-700">{fmtNum(rsbVal)}</td>
                    <td className="py-1 px-1">
                      <NumCell value={r.wc_adjustment} onChange={(v) => setEdit(r.month, "wc_adjustment", v)} testid={`wc-edit-wcadj-${r.month}`} />
                    </td>
                    <td className={`py-1 px-3 text-right font-semibold ${closing >= 0 ? "text-purple-700" : "text-red-700"}`}>{fmtNum(closing)}</td>
                    <td className="py-1 px-3 text-center">
                      {r._dirty ? (
                        <div className="flex gap-1 justify-center">
                          <Button size="sm" variant="ghost" className="h-7 px-2 text-emerald-700 hover:bg-emerald-100"
                                  disabled={savingMonth === r.month}
                                  onClick={() => saveRow(r)}
                                  data-testid={`wc-save-${r.month}`}>
                            {savingMonth === r.month ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                          </Button>
                          <Button size="sm" variant="ghost" className="h-7 px-2 text-gray-600 hover:bg-gray-100"
                                  onClick={() => resetRow(r.month)}
                                  data-testid={`wc-reset-${r.month}`}>
                            <RotateCcw className="w-3 h-3" />
                          </Button>
                        </div>
                      ) : (
                        <Badge variant="outline" className={statusPillClass(r.rev_share_status)}>{r.rev_share_status || "—"}</Badge>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {rows.length > 0 && (
          <div className="px-3 py-2 text-[10px] text-muted-foreground border-t bg-gray-50 space-y-0.5">
            <div>{country === "Australia" ? "AU" : "India"} center · Single Financial Engine.</div>
            <div><strong>Net Available</strong> = Sales − Expenses − Commissions · <strong>Revenue Share Base</strong> = Sales − Commissions − GST · <strong>Closing WC</strong> = Opening + Net Avail + WC Adj + Topup.</div>
            <div className="text-amber-700">✎ editable cells auto-recompute the row live; click <Save className="w-3 h-3 inline" /> to commit. Sales is read-only (sourced from Daily Sales).</div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default WCOverviewGrid;
