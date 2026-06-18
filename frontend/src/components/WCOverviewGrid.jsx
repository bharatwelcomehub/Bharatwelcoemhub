import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Download, FileSpreadsheet, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";

/**
 * Working-Capital Month-wise Overview Grid
 *
 * Restores the legacy "Overview" grid screen requested by the user (Feb-2026):
 *   Month · Opening WC · Sales · GST · Expenses · Commissions ·
 *   Net Available (Op. Balance) · Revenue Share Base · Closing WC · Remarks.
 *
 * Totals row at the bottom (bold). PDF / Excel downloads reuse the existing
 * /api/center-accounts/wc-table/export-pdf|excel endpoints which already
 * include the Purnabramha logo, account-manager signature, and download date.
 */
const fmt = (n, cur = "Rs.") => {
  const v = Number(n || 0);
  return `${cur} ${v.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const fmtMonth = (m) => {
  // "2026-06" → "Jun 2026"
  if (!m || typeof m !== "string" || !m.includes("-")) return m || "";
  const [y, mm] = m.split("-");
  const date = new Date(Number(y), Number(mm) - 1, 1);
  return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
};

export function WCOverviewGrid({ apiBase, token, center, country, cur = "Rs." }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(null);   // 'pdf' | 'excel' | null
  const [meta, setMeta] = useState({ base_wc: 0, current_wc: 0, status: "" });

  const load = useCallback(async () => {
    if (!center) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/api/center-accounts/wc-table`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, center }),
      });
      const data = await res.json();
      if (!res.ok || !data?.success) throw new Error(data?.detail || "Failed");
      setRows(data.rows || []);
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

  const downloadFile = async (kind /* 'pdf' | 'excel' */) => {
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

  // Column totals
  const totals = rows.reduce((acc, r) => ({
    sale: acc.sale + Number(r.sale || 0),
    gst: acc.gst + Number(r.gst || 0),
    expenses: acc.expenses + Number(r.expenses || 0),
    commission: acc.commission + Number(r.commission || 0),
    operational_balance: acc.operational_balance + Number(r.operational_balance || r.pnl || 0),
    revenue_share_base: acc.revenue_share_base + Number(
      r.revenue_share_base
      ?? Math.max(0, Number(r.sale || 0) - Number(r.commission || 0) - Number(r.gst || 0))
    ),
  }), { sale: 0, gst: 0, expenses: 0, commission: 0, operational_balance: 0, revenue_share_base: 0 });

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
              Working Capital — Month-wise Overview
            </CardTitle>
            <p className="text-[11px] text-muted-foreground mt-1">
              Base WC: <strong>{fmt(meta.base_wc, cur)}</strong>
              {" · "}Current WC: <strong>{fmt(meta.current_wc, cur)}</strong>
              {meta.status && (
                <Badge variant="outline" className={`ml-2 ${statusPillClass(meta.status)}`}>{meta.status}</Badge>
              )}
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              size="sm" variant="outline"
              disabled={!rows.length || downloading === "pdf"}
              onClick={() => downloadFile("pdf")}
              data-testid="wc-overview-download-pdf"
            >
              {downloading === "pdf" ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <FileText className="w-4 h-4 mr-1" />}
              Download PDF
            </Button>
            <Button
              size="sm" variant="outline"
              disabled={!rows.length || downloading === "excel"}
              onClick={() => downloadFile("excel")}
              data-testid="wc-overview-download-excel"
            >
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
                <th className="text-right py-2 px-3 font-semibold">GST</th>
                <th className="text-right py-2 px-3 font-semibold">Expenses</th>
                <th className="text-right py-2 px-3 font-semibold">Commissions</th>
                <th className="text-right py-2 px-3 font-semibold">Net Available</th>
                <th className="text-right py-2 px-3 font-semibold">Revenue Share Base</th>
                <th className="text-right py-2 px-3 font-semibold">Closing WC</th>
                <th className="text-center py-2 px-3 font-semibold">Status</th>
              </tr>
              {/* Totals row directly under header (per user spec) */}
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
                  <td className="py-2 px-3 text-center text-amber-900">—</td>
                </tr>
              )}
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={10} className="py-6 text-center text-muted-foreground"><Loader2 className="w-4 h-4 inline mr-2 animate-spin" /> Loading…</td></tr>
              )}
              {!loading && rows.length === 0 && (
                <tr><td colSpan={10} className="py-6 text-center text-muted-foreground">No data available for this center.</td></tr>
              )}
              {!loading && rows.map((r, idx) => {
                const opBalance = Number(r.operational_balance ?? r.pnl ?? 0);
                const rsbVal = Number(
                  r.revenue_share_base
                  ?? Math.max(0, Number(r.sale || 0) - Number(r.commission || 0) - Number(r.gst || 0))
                );
                return (
                  <tr key={r.month || idx} className="border-b border-gray-100 hover:bg-purple-50/40" data-testid={`wc-overview-row-${r.month}`}>
                    <td className="py-2 px-3 font-medium">{fmtMonth(r.month)}</td>
                    <td className="py-2 px-3 text-right text-gray-700">{fmt(r.opening_wc, cur)}</td>
                    <td className="py-2 px-3 text-right text-blue-700">{fmt(r.sale, cur)}</td>
                    <td className="py-2 px-3 text-right text-orange-600">{fmt(r.gst, cur)}</td>
                    <td className="py-2 px-3 text-right text-rose-600">{fmt(r.expenses, cur)}</td>
                    <td className="py-2 px-3 text-right text-rose-600">{fmt(r.commission, cur)}</td>
                    <td className={`py-2 px-3 text-right font-semibold ${opBalance >= 0 ? "text-emerald-700" : "text-red-700"}`}>{fmt(opBalance, cur)}</td>
                    <td className="py-2 px-3 text-right text-sky-700">{fmt(rsbVal, cur)}</td>
                    <td className="py-2 px-3 text-right font-semibold text-purple-700">{fmt(r.closing_wc ?? r.balance_wc, cur)}</td>
                    <td className="py-2 px-3 text-center">
                      <Badge variant="outline" className={statusPillClass(r.rev_share_status)}>{r.rev_share_status || "—"}</Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {rows.length > 0 && (
          <div className="px-3 py-2 text-[10px] text-muted-foreground border-t bg-gray-50">
            {country === "Australia" ? "AU" : "India"} center · numbers driven by Single Financial Engine ·
            <strong> Net Available</strong> = Sales − Expenses − Commissions ·
            <strong> Revenue Share Base</strong> = Sales − Commissions − GST.
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default WCOverviewGrid;
