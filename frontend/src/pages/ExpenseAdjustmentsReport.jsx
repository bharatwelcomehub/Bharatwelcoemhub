/**
 * Expense Adjustments Report — cross-center / cross-month view for accounting.
 */
import React, { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Scale, Loader2, Download, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/App";

const API = process.env.REACT_APP_BACKEND_URL;

const today = () => new Date().toISOString().slice(0, 7);          // YYYY-MM
const lastYear = () => {
  const d = new Date(); d.setMonth(d.getMonth() - 11);
  return d.toISOString().slice(0, 7);
};

export default function ExpenseAdjustmentsReport() {
  const { session } = useAuth();
  const token = session?.token;

  const [centers, setCenters] = useState([]);
  const [filters, setFilters] = useState({
    centers: [],                  // empty = own / all (server enforces)
    from_month: lastYear(),
    to_month: today(),
  });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/sales/centers-list`).then(r => r.ok && r.json())
      .then(d => setCenters(d?.centers || []));
  }, []);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/center-accounts/adjustments/report`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          centers: filters.centers.length ? filters.centers : null,
          from_month: filters.from_month || null,
          to_month: filters.to_month || null,
        }),
      });
      if (r.ok) setData(await r.json());
      else toast.error("Failed to load report");
    } finally { setLoading(false); }
  }, [token, filters]);

  useEffect(() => { load(); }, [load]);

  const exportCsv = () => {
    if (!data?.items?.length) { toast.error("Nothing to export"); return; }
    const head = [
      "Date","Center","Month","Expense Head","Original",
      "Adjustment","Type","Reason","Created By","Created At",
    ];
    const rows = data.items.map(r => [
      r.expense_date, r.center, r.month, r.expense_head,
      r.original_expense_amount, r.adjustment_amount,
      r.adjustment_type,
      (r.adjustment_reason || "").replace(/[\r\n,]+/g, " "),
      r.created_by, r.created_at,
    ]);
    const csv = [head, ...rows].map(row => row.map(c => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `expense_adjustments_${filters.from_month}_to_${filters.to_month}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const fmt = (n) => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  return (
    <div className="space-y-6 p-4 md:p-6" data-testid="expense-adjustments-report">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold text-[#5C0000] flex items-center gap-2">
            <Scale className="w-7 h-7 text-amber-600" /> Expense Adjustments Report
          </h1>
          <p className="text-muted-foreground mt-1">
            Prepaid / advance / future-month carve outs across centers and months. Original expense rows are never altered.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} /> Refresh
          </Button>
          <Button onClick={exportCsv} disabled={!data?.items?.length} data-testid="export-csv-btn">
            <Download className="w-4 h-4 mr-1" /> Export CSV
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <Label className="text-xs">Center</Label>
            <Select value={filters.centers[0] || "all"}
              onValueChange={(v) => setFilters(f => ({ ...f, centers: v === "all" ? [] : [v] }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Centers</SelectItem>
                {centers.map(c => <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">From Month</Label>
            <Input type="month" value={filters.from_month}
              onChange={(e) => setFilters(f => ({ ...f, from_month: e.target.value }))} />
          </div>
          <div>
            <Label className="text-xs">To Month</Label>
            <Input type="month" value={filters.to_month}
              onChange={(e) => setFilters(f => ({ ...f, to_month: e.target.value }))} />
          </div>
        </CardContent>
      </Card>

      {/* Totals */}
      {data?.totals && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card className="border-rose-200 bg-rose-50">
            <CardContent className="pt-3 pb-3">
              <div className="text-[11px] uppercase tracking-wide text-rose-700">Total Expenses</div>
              <div className="text-lg font-bold text-rose-800">₹ {fmt(data.totals.total_expenses)}</div>
            </CardContent>
          </Card>
          <Card className="border-amber-200 bg-amber-50">
            <CardContent className="pt-3 pb-3">
              <div className="text-[11px] uppercase tracking-wide text-amber-700">Less Adjustments</div>
              <div className="text-lg font-bold text-amber-800">− ₹ {fmt(data.totals.total_adjustments)}</div>
            </CardContent>
          </Card>
          <Card className="border-indigo-200 bg-indigo-50">
            <CardContent className="pt-3 pb-3">
              <div className="text-[11px] uppercase tracking-wide text-indigo-700">Adjusted Expenses</div>
              <div className="text-lg font-bold text-indigo-800">₹ {fmt(data.totals.adjusted_expenses)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-3 pb-3">
              <div className="text-[11px] uppercase tracking-wide opacity-70">Adjustment Rows</div>
              <div className="text-lg font-bold">{data.totals.count}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Per-center-month summary */}
      {data?.summary_by_center_month?.length > 0 && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Center × Month Summary</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Center</TableHead><TableHead>Month</TableHead>
                  <TableHead className="text-right">Total Expenses</TableHead>
                  <TableHead className="text-right">Adjustments</TableHead>
                  <TableHead className="text-right">Adjusted Expenses</TableHead>
                  <TableHead className="text-right">Rows</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.summary_by_center_month.map((r, i) => (
                  <TableRow key={`${r.center}-${r.month}-${i}`}>
                    <TableCell>{r.center}</TableCell>
                    <TableCell>{r.month}</TableCell>
                    <TableCell className="text-right">₹ {fmt(r.total_expenses)}</TableCell>
                    <TableCell className="text-right text-amber-700">− ₹ {fmt(r.total_adjustments)}</TableCell>
                    <TableCell className="text-right font-semibold">₹ {fmt(r.adjusted_expenses)}</TableCell>
                    <TableCell className="text-right">{r.row_count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Detail */}
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Adjustment Entries</CardTitle></CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin" /></div>
          ) : !data?.items?.length ? (
            <div className="text-center py-8 text-muted-foreground">No adjustments in the selected range.</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead><TableHead>Center</TableHead>
                  <TableHead>Expense Head</TableHead>
                  <TableHead className="text-right">Original</TableHead>
                  <TableHead className="text-right">Adjustment</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Created By</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((r) => (
                  <TableRow key={r.adjustment_id}>
                    <TableCell className="text-xs">{r.expense_date}</TableCell>
                    <TableCell><Badge variant="outline">{r.center}</Badge></TableCell>
                    <TableCell>{r.expense_head}</TableCell>
                    <TableCell className="text-right">₹ {fmt(r.original_expense_amount)}</TableCell>
                    <TableCell className="text-right font-semibold text-amber-700">₹ {fmt(r.adjustment_amount)}</TableCell>
                    <TableCell><Badge variant="outline" className="text-xs">{r.adjustment_type}</Badge></TableCell>
                    <TableCell className="text-xs max-w-[260px] truncate" title={r.adjustment_reason}>
                      {r.adjustment_reason || "—"}
                    </TableCell>
                    <TableCell className="text-xs">{r.created_by}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
