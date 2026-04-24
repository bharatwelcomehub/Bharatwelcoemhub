import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/App';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Receipt, RefreshCw, CheckCircle2, XCircle } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const YEARS = (() => { const y = new Date().getFullYear(); return Array.from({length: y - 2022}, (_, i) => String(y - i)); })();

function fmtINR(n) {
  return `₹${Math.round(n || 0).toLocaleString('en-IN')}`;
}

export default function GSTReconciliation() {
  const { session } = useAuth();
  const [centers, setCenters] = useState([]);
  const [center, setCenter] = useState('all');
  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [status, setStatus] = useState('');
  const [rows, setRows] = useState([]);
  const [totals, setTotals] = useState({ total_payable: 0, total_paid: 0 });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API}/api/mgt/centers`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: session.token }),
        });
        const data = await res.json();
        setCenters((data.centers || []).map(c => c.code).filter(Boolean));
      } catch { /* ignore */ }
    })();
  }, [session]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/gst/liabilities`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, center, year, status }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed');
      setRows(data.rows || []);
      setTotals({ total_payable: data.total_payable, total_paid: data.total_paid });
    } catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  }, [center, year, status, session]);

  useEffect(() => { load(); }, [load]);

  const recompute = async () => {
    try {
      const res = await fetch(`${API}/api/gst/recompute`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed');
      toast.success(`Recomputed ${data.updated} liability buckets.`);
      load();
    } catch (e) { toast.error(e.message); }
  };

  const togglePaid = async (row) => {
    const paid = !!row.paid;
    const endpoint = paid ? 'unmark-paid' : 'mark-paid';
    const confirmMsg = paid
      ? `Unmark GST for ${row.center} ${row.month} as paid? This deletes the linked M+1 expense row.`
      : `Mark GST for ${row.center} ${row.month} (${fmtINR(row.gst_amount)}) as paid? An expense row will be auto-created in month ${nextMonth(row.month)}.`;
    if (!window.confirm(confirmMsg)) return;
    try {
      const res = await fetch(`${API}/api/gst/${endpoint}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, center: row.center, month: row.month }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed');
      toast.success(paid ? 'GST payment reversed' : 'GST marked paid — expense entry created in M+1');
      load();
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6" data-testid="gst-reconciliation-page">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2"><Receipt className="w-6 h-6 text-[#8B0000]" /> GST Reconciliation</h1>
        <p className="text-sm text-muted-foreground">Track GST liabilities per center/month and their M+1 payment entries. Rate: 5% on eligible sales (10% for Perth).</p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-end justify-between gap-4 space-y-0">
          <div className="flex-1 grid grid-cols-1 md:grid-cols-4 gap-3">
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Center</label>
              <Select value={center} onValueChange={setCenter}>
                <SelectTrigger data-testid="gr-center-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All centers</SelectItem>
                  {centers.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Year</label>
              <Select value={year} onValueChange={setYear}>
                <SelectTrigger data-testid="gr-year-select"><SelectValue /></SelectTrigger>
                <SelectContent>{YEARS.map(y => <SelectItem key={y} value={y}>{y}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Status</label>
              <Select value={status || 'all'} onValueChange={v => setStatus(v === 'all' ? '' : v)}>
                <SelectTrigger data-testid="gr-status-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="unpaid">Payable (Unpaid)</SelectItem>
                  <SelectItem value="paid">Paid</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end gap-2">
              <Button onClick={load} variant="outline" className="flex-1" data-testid="gr-load-btn">
                <RefreshCw className="w-4 h-4 mr-1" /> Refresh
              </Button>
              <Button onClick={recompute} className="bg-[#8B0000] hover:bg-[#6B0000] text-white" data-testid="gr-recompute-btn">
                Recompute All
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
            <div className="p-3 rounded border bg-amber-50">
              <p className="text-xs text-amber-700 font-semibold">Total Payable</p>
              <p className="text-xl font-bold text-amber-700">{fmtINR(totals.total_payable)}</p>
            </div>
            <div className="p-3 rounded border bg-green-50">
              <p className="text-xs text-green-700 font-semibold">Total Paid</p>
              <p className="text-xl font-bold text-green-700">{fmtINR(totals.total_paid)}</p>
            </div>
            <div className="p-3 rounded border bg-slate-50">
              <p className="text-xs text-slate-600 font-semibold">Rows</p>
              <p className="text-xl font-bold text-slate-700">{rows.length}</p>
            </div>
          </div>

          <div className="overflow-x-auto border rounded">
            <table className="w-full text-sm" data-testid="gr-table">
              <thead className="bg-slate-100 text-xs uppercase">
                <tr>
                  <th className="p-2 text-left">Center</th>
                  <th className="p-2 text-left">Month (M)</th>
                  <th className="p-2 text-right">Eligible Base</th>
                  <th className="p-2 text-right">Rate</th>
                  <th className="p-2 text-right">GST Amount</th>
                  <th className="p-2 text-center">Status</th>
                  <th className="p-2 text-left">M+1 Paid On</th>
                  <th className="p-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {loading && <tr><td colSpan="8" className="p-6 text-center text-muted-foreground">Loading…</td></tr>}
                {!loading && rows.length === 0 && <tr><td colSpan="8" className="p-6 text-center text-muted-foreground">No records. Click <strong>Recompute All</strong> to seed from daily sales.</td></tr>}
                {rows.map((r) => (
                  <tr key={`${r.center}-${r.month}`} className="border-t hover:bg-slate-50" data-testid={`gr-row-${r.center}-${r.month}`}>
                    <td className="p-2 font-medium">{r.center}</td>
                    <td className="p-2">{r.month}</td>
                    <td className="p-2 text-right">{fmtINR(r.eligible_base)}</td>
                    <td className="p-2 text-right">{r.rate_pct || 5}%</td>
                    <td className="p-2 text-right font-semibold">{fmtINR(r.gst_amount)}</td>
                    <td className="p-2 text-center">
                      {r.paid
                        ? <Badge className="bg-green-100 text-green-700 border-green-300"><CheckCircle2 className="w-3 h-3 mr-1 inline" />Paid</Badge>
                        : <Badge className="bg-amber-100 text-amber-700 border-amber-300">Payable</Badge>}
                    </td>
                    <td className="p-2 text-xs text-muted-foreground">{r.paid_date || (r.paid ? 'paid' : '—')}</td>
                    <td className="p-2 text-right">
                      <Button
                        size="sm"
                        variant={r.paid ? 'outline' : 'default'}
                        className={r.paid ? 'border-red-300 text-red-700' : 'bg-green-700 hover:bg-green-800 text-white'}
                        data-testid={`gr-toggle-${r.center}-${r.month}`}
                        onClick={() => togglePaid(r)}
                      >
                        {r.paid ? <><XCircle className="w-3 h-3 mr-1" /> Unmark</> : <><CheckCircle2 className="w-3 h-3 mr-1" /> Mark Paid</>}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function nextMonth(yyyymm) {
  const [y, m] = yyyymm.split('-').map(Number);
  const nm = m === 12 ? 1 : m + 1;
  const ny = m === 12 ? y + 1 : y;
  return `${ny}-${String(nm).padStart(2, '0')}`;
}
