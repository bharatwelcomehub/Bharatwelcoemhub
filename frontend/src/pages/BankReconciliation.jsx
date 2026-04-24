import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/App';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Banknote, Upload, FileText, AlertTriangle, CheckCircle2, X, Plus } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

function fmtINR(n) {
  return `₹${Math.round(n || 0).toLocaleString('en-IN')}`;
}

export default function BankReconciliation() {
  const { session } = useAuth();
  const [centers, setCenters] = useState([]);
  const [center, setCenter] = useState('');
  const [month, setMonth] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  });
  const [file, setFile] = useState(null);
  const [uploads, setUploads] = useState([]);
  const [activeUpload, setActiveUpload] = useState(null);
  const [summary, setSummary] = useState(null);
  const [expenseCats, setExpenseCats] = useState([]);
  const [addDialog, setAddDialog] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API}/api/mgt/centers`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: session.token }),
        });
        const data = await res.json();
        const list = (data.centers || []).map(c => c.code).filter(Boolean);
        setCenters(list);
        if (list.length && !center) setCenter(list[0]);
      } catch { /* ignore */ }
      try {
        const res = await fetch(`${API}/api/category-master/expense-heads`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: session.token }),
        });
        const data = await res.json();
        setExpenseCats((data.expense_heads || data.rows || data.categories || []).map(c => c.name || c));
      } catch { /* ignore */ }
    })();
  }, [session, center]);

  const loadUploads = useCallback(async () => {
    if (!center) return;
    try {
      const res = await fetch(`${API}/api/bank-reconciliation/uploads?center=${encodeURIComponent(center)}&token=${encodeURIComponent(session.token)}`);
      const data = await res.json();
      setUploads(data.uploads || []);
    } catch (e) { toast.error(e.message); }
  }, [center, session]);

  useEffect(() => { loadUploads(); }, [loadUploads]);

  const loadSummary = useCallback(async (upload_id) => {
    try {
      const res = await fetch(`${API}/api/bank-reconciliation/summary`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ upload_id, token: session.token }),
      });
      const data = await res.json();
      if (data.detail) throw new Error(data.detail);
      setSummary(data);
      setActiveUpload(upload_id);
    } catch (e) { toast.error(e.message); }
  }, [session]);

  const doUpload = async () => {
    if (!file) { toast.error('Please choose a CSV or Excel file'); return; }
    if (!center || !month) { toast.error('Pick a center and month first'); return; }
    const fd = new FormData();
    fd.append('file', file);
    fd.append('center', center);
    fd.append('month', month);
    fd.append('token', session.token);
    try {
      toast.info('Uploading & parsing…');
      const res = await fetch(`${API}/api/bank-reconciliation/upload`, { method: 'POST', body: fd });
      const data = await res.json();
      if (data.detail) throw new Error(data.detail);
      toast.success(`Parsed ${data.summary.total_bank_transactions} txns — Matched: ${data.summary.matched_count}, Unrecorded: ${data.summary.unrecorded_count}`);
      setFile(null);
      await loadUploads();
      await loadSummary(data.upload_id);
    } catch (e) { toast.error(e.message); }
  };

  const openAdd = (txn) => setAddDialog({ ...txn, expense_type: expenseCats[0] || '', payment_mode: 'Bank Transfer', description: txn.narration || '' });

  const saveAdd = async () => {
    try {
      const res = await fetch(`${API}/api/bank-reconciliation/add-expense`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transaction_id: addDialog.transaction_id,
          upload_id: activeUpload,
          expense_type: addDialog.expense_type,
          payment_mode: addDialog.payment_mode,
          description: addDialog.description,
          token: session.token,
        }),
      });
      const data = await res.json();
      if (data.detail && !data.success) throw new Error(data.detail);
      toast.success('Expense recorded');
      setAddDialog(null);
      loadSummary(activeUpload);
    } catch (e) { toast.error(e.message); }
  };

  const ignoreTxn = async (txn) => {
    const reason = window.prompt('Reason for ignoring this transaction?');
    if (!reason) return;
    try {
      const res = await fetch(`${API}/api/bank-reconciliation/ignore`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transaction_id: txn.transaction_id,
          upload_id: activeUpload,
          reason,
          token: session.token,
        }),
      });
      const data = await res.json();
      if (data.detail && !data.success) throw new Error(data.detail);
      toast.success('Transaction ignored');
      loadSummary(activeUpload);
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6" data-testid="bank-reconciliation-page">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2"><Banknote className="w-6 h-6 text-sky-700" /> Bank Reconciliation</h1>
        <p className="text-sm text-muted-foreground">Upload a bank statement (CSV / Excel). The system matches each debit against your recorded expenses and surfaces unrecorded transactions for quick booking.</p>
      </div>

      {/* Upload */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Upload Bank Statement</CardTitle>
          <CardDescription>Supported: CSV, XLS, XLSX. Expected columns: Date, Narration, Debit.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Center</label>
              <Select value={center} onValueChange={setCenter}>
                <SelectTrigger data-testid="br-center-select"><SelectValue /></SelectTrigger>
                <SelectContent>{centers.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Month</label>
              <Input type="month" value={month} onChange={e => setMonth(e.target.value)} data-testid="br-month-input" />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs font-semibold text-muted-foreground">File</label>
              <Input type="file" accept=".csv,.xls,.xlsx" onChange={e => setFile(e.target.files[0])} data-testid="br-file-input" />
            </div>
            <Button className="bg-sky-700 hover:bg-sky-800 text-white" onClick={doUpload} data-testid="br-upload-btn">
              <Upload className="w-4 h-4 mr-1" /> Upload & Reconcile
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Recent uploads */}
      <Card>
        <CardHeader><CardTitle className="text-base">Recent Uploads {center && `— ${center}`}</CardTitle></CardHeader>
        <CardContent>
          {uploads.length === 0 ? (
            <p className="text-sm text-muted-foreground">No previous uploads for this center.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm border rounded" data-testid="br-uploads-table">
                <thead className="bg-slate-100 text-xs uppercase">
                  <tr>
                    <th className="p-2 text-left">Date</th>
                    <th className="p-2 text-left">Month</th>
                    <th className="p-2 text-left">File</th>
                    <th className="p-2 text-right">Txns</th>
                    <th className="p-2 text-right">Matched</th>
                    <th className="p-2 text-right">Unrecorded</th>
                    <th className="p-2 text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {uploads.map((u) => (
                    <tr key={u.upload_id} className={`border-t hover:bg-slate-50 ${activeUpload === u.upload_id ? 'bg-sky-50' : ''}`}>
                      <td className="p-2 text-xs text-muted-foreground">{u.uploaded_at?.slice(0, 10)}</td>
                      <td className="p-2">{u.month}</td>
                      <td className="p-2 text-xs">{u.filename}</td>
                      <td className="p-2 text-right">{u.total_transactions || u.summary?.total_bank_transactions || '—'}</td>
                      <td className="p-2 text-right text-green-700">{u.matched_count || u.summary?.matched_count || '—'}</td>
                      <td className="p-2 text-right text-amber-700">{u.unrecorded_count || u.summary?.unrecorded_count || '—'}</td>
                      <td className="p-2 text-right">
                        <Button size="sm" variant="outline" onClick={() => loadSummary(u.upload_id)} data-testid={`br-view-${u.upload_id}`}>
                          <FileText className="w-3 h-3 mr-1" /> View
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Summary tabs */}
      {summary && (
        <Card data-testid="br-summary">
          <CardHeader>
            <CardTitle className="text-base">Reconciliation — {summary.upload?.filename || activeUpload}</CardTitle>
            <CardDescription>
              Bank Debits: <strong>{fmtINR(summary.summary.total_bank_debits)}</strong> · Matched: <strong className="text-green-700">{fmtINR(summary.summary.matched_amount)}</strong> · Unrecorded: <strong className="text-amber-700">{fmtINR(summary.summary.unrecorded_amount)}</strong>
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="unrecorded">
              <TabsList>
                <TabsTrigger value="unrecorded" data-testid="br-tab-unrecorded">Unrecorded ({summary.summary.unrecorded_count})</TabsTrigger>
                <TabsTrigger value="matched" data-testid="br-tab-matched">Matched ({summary.summary.matched_count})</TabsTrigger>
                <TabsTrigger value="added" data-testid="br-tab-added">Added ({summary.summary.added_count || 0})</TabsTrigger>
                <TabsTrigger value="ignored" data-testid="br-tab-ignored">Ignored ({summary.summary.ignored_count || 0})</TabsTrigger>
              </TabsList>

              <TabsContent value="unrecorded" className="mt-3">
                <TxnTable
                  rows={summary.unrecorded}
                  empty="All bank debits are reconciled!"
                  badgeColor="bg-amber-100 text-amber-700 border-amber-300"
                  actions={(txn) => (
                    <div className="flex gap-1 justify-end">
                      <Button size="sm" className="bg-green-700 hover:bg-green-800 text-white" onClick={() => openAdd(txn)} data-testid={`br-add-${txn.transaction_id}`}><Plus className="w-3 h-3 mr-1" /> Add</Button>
                      <Button size="sm" variant="outline" className="border-red-300 text-red-700" onClick={() => ignoreTxn(txn)} data-testid={`br-ignore-${txn.transaction_id}`}><X className="w-3 h-3 mr-1" /> Ignore</Button>
                    </div>
                  )}
                />
              </TabsContent>
              <TabsContent value="matched" className="mt-3">
                <TxnTable rows={summary.matched} empty="No matched transactions yet." badgeColor="bg-green-100 text-green-700 border-green-300" />
              </TabsContent>
              <TabsContent value="added" className="mt-3">
                <TxnTable rows={summary.added || []} empty="No transactions added as expense yet." badgeColor="bg-blue-100 text-blue-700 border-blue-300" />
              </TabsContent>
              <TabsContent value="ignored" className="mt-3">
                <TxnTable rows={summary.ignored || []} empty="No ignored transactions." badgeColor="bg-slate-100 text-slate-700 border-slate-300" />
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}

      {/* Add-expense dialog */}
      <Dialog open={!!addDialog} onOpenChange={(open) => { if (!open) setAddDialog(null); }}>
        <DialogContent data-testid="br-add-dialog">
          <DialogHeader><DialogTitle>Add as Expense</DialogTitle></DialogHeader>
          {addDialog && (
            <div className="space-y-3">
              <div className="p-3 bg-slate-50 rounded text-sm">
                <p><strong>Date:</strong> {addDialog.transaction_date}</p>
                <p><strong>Amount:</strong> {fmtINR(addDialog.debit_amount)}</p>
                <p><strong>Narration:</strong> {addDialog.narration}</p>
              </div>
              <div>
                <label className="text-xs font-semibold">Expense Category</label>
                <Select value={addDialog.expense_type} onValueChange={v => setAddDialog({ ...addDialog, expense_type: v })}>
                  <SelectTrigger><SelectValue placeholder="Pick category" /></SelectTrigger>
                  <SelectContent>{expenseCats.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                </Select>
                {addDialog.suggested_category && (
                  <p className="text-xs text-sky-700 mt-1">Suggested: <strong>{addDialog.suggested_category}</strong></p>
                )}
              </div>
              <div>
                <label className="text-xs font-semibold">Payment Mode</label>
                <Select value={addDialog.payment_mode} onValueChange={v => setAddDialog({ ...addDialog, payment_mode: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Bank Transfer">Bank Transfer</SelectItem>
                    <SelectItem value="UPI">UPI</SelectItem>
                    <SelectItem value="Cheque">Cheque</SelectItem>
                    <SelectItem value="Cash">Cash</SelectItem>
                    <SelectItem value="Card">Card</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs font-semibold">Description</label>
                <Input value={addDialog.description} onChange={e => setAddDialog({ ...addDialog, description: e.target.value })} />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddDialog(null)}>Cancel</Button>
            <Button onClick={saveAdd} className="bg-green-700 hover:bg-green-800 text-white" data-testid="br-add-save">Save Expense</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function TxnTable({ rows, empty, badgeColor, actions }) {
  if (!rows || rows.length === 0) return <p className="text-sm text-muted-foreground p-4">{empty}</p>;
  return (
    <div className="overflow-x-auto border rounded">
      <table className="w-full text-sm">
        <thead className="bg-slate-100 text-xs uppercase">
          <tr>
            <th className="p-2 text-left">Date</th>
            <th className="p-2 text-left">Narration</th>
            <th className="p-2 text-right">Debit (₹)</th>
            <th className="p-2 text-left">Suggested Category</th>
            <th className="p-2 text-center">Status</th>
            {actions && <th className="p-2 text-right">Action</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => (
            <tr key={t.transaction_id} className="border-t hover:bg-slate-50">
              <td className="p-2 text-xs">{t.transaction_date}</td>
              <td className="p-2 text-xs max-w-sm truncate" title={t.narration}>{t.narration}</td>
              <td className="p-2 text-right font-semibold">{fmtINR(t.debit_amount)}</td>
              <td className="p-2 text-xs text-sky-700">{t.suggested_category || '—'}</td>
              <td className="p-2 text-center">
                <Badge className={badgeColor}>{(t.match_status || 'unknown').toUpperCase()}</Badge>
              </td>
              {actions && <td className="p-2 text-right">{actions(t)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
