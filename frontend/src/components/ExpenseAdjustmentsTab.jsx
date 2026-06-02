/**
 * Expense Adjustments Tab — center-accounts feature.
 * Lets Admin / Super Admin / Accountant carve prepaid/advance amounts out of
 * the current month's profitability without touching the raw expense row.
 *
 * Props:
 *  - center, month, currencySymbol, summary (parent's accountSummary)
 *  - onChanged: callback to re-fetch the parent dashboard after CRUD
 */
import React, { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Plus, Trash2, Edit, Scale, Loader2, AlertCircle,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/App";

const API = process.env.REACT_APP_BACKEND_URL;

export default function ExpenseAdjustmentsTab({
  center, month, currencySymbol = "₹", summary, onChanged,
}) {
  const { session } = useAuth();
  const token = session?.token;
  const canWrite =
    session?.is_super_admin ||
    session?.is_admin ||
    session?.role_key === "accountant" ||
    !!session?.roles?.accounting ||
    !!session?.roles?.accounts;

  const [types, setTypes] = useState([]);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expenseRows, setExpenseRows] = useState([]);
  const [showDlg, setShowDlg] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    expense_id: "",
    adjustment_amount: "",
    adjustment_type: "Next Month Rent Paid in Advance",
    adjustment_reason: "",
  });

  // Load type list (static)
  useEffect(() => {
    if (!token) return;
    fetch(`${API}/api/center-accounts/adjustments/types`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    }).then(r => r.ok && r.json()).then(d => d?.types && setTypes(d.types));
  }, [token]);

  // Load adjustments + expense rows for the dialog dropdown
  const load = useCallback(async () => {
    if (!token || !center || !month) return;
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/center-accounts/adjustments/list`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, center, month }),
      });
      if (r.ok) setItems((await r.json()).items || []);
      // For the picker, fetch expenses of the period.
      const start = `${month}-01`;
      const [y, m] = month.split("-").map(Number);
      const ny = m === 12 ? y + 1 : y; const nm = m === 12 ? 1 : m + 1;
      const end = `${ny}-${String(nm).padStart(2, "0")}-01`;
      const er = await fetch(`${API}/api/sales/expenses-list`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, center, from_date: start, to_date: end }),
      });
      if (er.ok) {
        const ed = await er.json();
        setExpenseRows(ed.expenses || ed.rows || []);
      }
    } finally { setLoading(false); }
  }, [token, center, month]);

  useEffect(() => { load(); }, [load]);

  const fmt = (n) => `${currencySymbol}${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const totalExpenses = summary?.financial_summary?.total_expenses ?? summary?.expenses?.total ?? 0;
  const totalAdj      = summary?.financial_summary?.total_adjustments ?? items.reduce((s, r) => s + Number(r.adjustment_amount || 0), 0);
  const adjustedExp   = summary?.financial_summary?.adjusted_expenses ?? Math.max(0, totalExpenses - totalAdj);
  const netRevenue    = summary?.financial_summary?.net_revenue ?? 0;
  const profit        = summary?.financial_summary?.profitability ?? (netRevenue - adjustedExp);

  const openCreate = () => {
    setEditing(null);
    setForm({ expense_id: "", adjustment_amount: "", adjustment_type: types[0] || "Manual Adjustment", adjustment_reason: "" });
    setShowDlg(true);
  };

  const openEdit = (row) => {
    setEditing(row);
    setForm({
      expense_id: row.expense_id,
      adjustment_amount: String(row.adjustment_amount || ""),
      adjustment_type: row.adjustment_type,
      adjustment_reason: row.adjustment_reason || "",
    });
    setShowDlg(true);
  };

  const save = async () => {
    if (!form.expense_id) { toast.error("Pick the underlying expense row"); return; }
    const amt = Number(form.adjustment_amount);
    if (!amt || amt <= 0) { toast.error("Adjustment amount must be > 0"); return; }
    try {
      const url = editing
        ? `${API}/api/center-accounts/adjustments/update/${editing.adjustment_id}`
        : `${API}/api/center-accounts/adjustments/create`;
      const body = editing
        ? { token, adjustment_amount: amt, adjustment_type: form.adjustment_type, adjustment_reason: form.adjustment_reason }
        : { token, expense_id: form.expense_id, center, month, adjustment_amount: amt, adjustment_type: form.adjustment_type, adjustment_reason: form.adjustment_reason };
      const r = await fetch(url, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      if (r.ok) {
        toast.success(editing ? "Adjustment updated" : "Adjustment added");
        setShowDlg(false);
        await load();
        onChanged?.();
      } else {
        const e = await r.json().catch(() => ({}));
        toast.error(e.detail || "Failed");
      }
    } catch {
      toast.error("Network error");
    }
  };

  const del = async (row) => {
    if (!window.confirm(`Delete adjustment ${fmt(row.adjustment_amount)} on ${row.expense_head}?`)) return;
    const r = await fetch(`${API}/api/center-accounts/adjustments/delete/${row.adjustment_id}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }),
    });
    if (r.ok) {
      toast.success("Deleted");
      await load();
      onChanged?.();
    } else {
      toast.error("Delete failed");
    }
  };

  return (
    <div className="space-y-4" data-testid="expense-adjustments-tab">
      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <SummaryCard label="Total Expenses" value={fmt(totalExpenses)} tone="rose" />
        <SummaryCard label="Less Adjustments" value={`− ${fmt(totalAdj)}`} tone="amber" />
        <SummaryCard label="Adjusted Expenses" value={fmt(adjustedExp)} tone="indigo" />
        <SummaryCard label="Net Revenue" value={fmt(netRevenue)} tone="sky" />
        <SummaryCard label="Profitability" value={fmt(profit)} tone={profit >= 0 ? "emerald" : "rose"} />
      </div>

      {/* Action row */}
      <Card>
        <CardHeader className="pb-2 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Scale className="w-4 h-4 text-amber-600" />
              Expense Adjustments · {center} · {month}
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Carve prepaid / advance / future-month amounts out of Profitability & Revenue Share without touching the original expense row.
            </p>
          </div>
          {canWrite && (
            <Button onClick={openCreate} data-testid="adjustment-new-btn">
              <Plus className="w-4 h-4 mr-1" /> New Adjustment
            </Button>
          )}
        </CardHeader>
        <CardContent className="pt-0">
          {loading ? (
            <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin" /></div>
          ) : items.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <AlertCircle className="w-5 h-5 inline mr-2 -mt-1" />
              No adjustments for this month. Existing P&L is unchanged.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Expense Date</TableHead>
                  <TableHead>Expense Head</TableHead>
                  <TableHead className="text-right">Original</TableHead>
                  <TableHead className="text-right">Adjustment</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Created By</TableHead>
                  {canWrite && <TableHead></TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((r) => (
                  <TableRow key={r.adjustment_id} data-testid={`adj-row-${r.adjustment_id}`}>
                    <TableCell className="text-xs">{r.expense_date}</TableCell>
                    <TableCell>{r.expense_head}</TableCell>
                    <TableCell className="text-right">{fmt(r.original_expense_amount)}</TableCell>
                    <TableCell className="text-right font-semibold text-amber-700">{fmt(r.adjustment_amount)}</TableCell>
                    <TableCell><Badge variant="outline">{r.adjustment_type}</Badge></TableCell>
                    <TableCell className="text-xs max-w-[260px] truncate" title={r.adjustment_reason}>{r.adjustment_reason || "—"}</TableCell>
                    <TableCell className="text-xs">{r.created_by}</TableCell>
                    {canWrite && (
                      <TableCell>
                        <div className="flex gap-1">
                          <Button size="icon" variant="ghost" onClick={() => openEdit(r)}><Edit className="w-4 h-4" /></Button>
                          <Button size="icon" variant="ghost" onClick={() => del(r)}><Trash2 className="w-4 h-4 text-red-500" /></Button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit dialog */}
      <Dialog open={showDlg} onOpenChange={setShowDlg}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{editing ? "Edit Adjustment" : "New Expense Adjustment"}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>Expense Row *</Label>
              <Select value={form.expense_id} onValueChange={(v) => setForm(f => ({ ...f, expense_id: v }))} disabled={!!editing}>
                <SelectTrigger data-testid="adj-expense-select">
                  <SelectValue placeholder="Pick the underlying expense..." />
                </SelectTrigger>
                <SelectContent className="max-h-72">
                  {expenseRows.length === 0 && <SelectItem value="__none" disabled>No expenses for this month</SelectItem>}
                  {expenseRows.map((e) => {
                    const eid = e.id || e.expense_id;
                    const label = `${e.date} · ${e.expense_type || "Other"} · ${currencySymbol}${Number(e.amount || 0).toLocaleString()}${e.description ? ` · ${String(e.description).slice(0, 40)}` : ""}`;
                    return <SelectItem key={eid} value={eid}>{label}</SelectItem>;
                  })}
                </SelectContent>
              </Select>
              {editing && (
                <p className="text-xs text-muted-foreground mt-1">
                  Original: {fmt(editing.original_expense_amount)} · Head: {editing.expense_head}
                </p>
              )}
            </div>
            <div>
              <Label>Adjustment Amount *</Label>
              <Input type="number" value={form.adjustment_amount} placeholder="0.00"
                onChange={(e) => setForm(f => ({ ...f, adjustment_amount: e.target.value }))}
                data-testid="adj-amount-input" />
            </div>
            <div>
              <Label>Adjustment Type *</Label>
              <Select value={form.adjustment_type} onValueChange={(v) => setForm(f => ({ ...f, adjustment_type: v }))}>
                <SelectTrigger data-testid="adj-type-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {types.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Reason / Note</Label>
              <Textarea rows={3} value={form.adjustment_reason}
                onChange={(e) => setForm(f => ({ ...f, adjustment_reason: e.target.value }))}
                placeholder="e.g. June 2026 rent paid in advance via cheque #4521 on 28-May-2026"
                data-testid="adj-reason-input" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDlg(false)}>Cancel</Button>
            <Button onClick={save} data-testid="adj-save-btn">{editing ? "Update" : "Add Adjustment"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function SummaryCard({ label, value, tone = "indigo" }) {
  const tones = {
    rose:    "bg-rose-50  text-rose-700  border-rose-200",
    amber:   "bg-amber-50 text-amber-700 border-amber-200",
    indigo:  "bg-indigo-50 text-indigo-700 border-indigo-200",
    sky:     "bg-sky-50   text-sky-700   border-sky-200",
    emerald: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };
  return (
    <Card className={`border ${tones[tone] || tones.indigo}`}>
      <CardContent className="pt-3 pb-3">
        <div className="text-[11px] uppercase tracking-wide opacity-70">{label}</div>
        <div className="text-lg font-bold mt-1">{value}</div>
      </CardContent>
    </Card>
  );
}
