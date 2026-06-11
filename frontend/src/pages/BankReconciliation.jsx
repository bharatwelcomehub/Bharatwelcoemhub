import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/App';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Banknote, Upload, FileText, AlertTriangle, CheckCircle2, X, Plus, Layers, Loader2 } from 'lucide-react';
import { Checkbox } from '../components/ui/checkbox';
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
  // Bulk-add state for similar-narration mass update
  const [selectedIds, setSelectedIds] = useState([]);
  const [bulkDialogOpen, setBulkDialogOpen] = useState(false);
  const [bulkExpenseType, setBulkExpenseType] = useState('');
  const [bulkPaymentMode, setBulkPaymentMode] = useState('Bank Transfer');
  const [bulkDescription, setBulkDescription] = useState('');
  const [aiBusy, setAiBusy] = useState(false);
  const [bulkBusy, setBulkBusy] = useState(false);

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
        const res = await fetch(`${API}/api/sales/expense-heads`);
        const data = await res.json();
        const heads = data.expense_heads || data.rows || data.categories || [];
        setExpenseCats(heads.map(c => c.name || c).filter(Boolean));
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
      const s = data.summary;
      toast.success(`Parsed ${s.total_bank_transactions} txns — Matched: ${s.matched_count}, Partial: ${s.partially_matched_count || 0}, Unmatched: ${s.unrecorded_count}, Manual Review: ${s.manual_review_count || 0}, Auto-Ignored: ${s.auto_ignored_count || 0}`);
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

  const submitBulk = async () => {
    if (!bulkExpenseType) { toast.error('Pick a category'); return; }
    if (selectedIds.length === 0) { toast.error('No rows selected'); return; }
    setBulkBusy(true);
    try {
      const res = await fetch(`${API}/api/bank-reconciliation/bulk-add-expense`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: session.token,
          upload_id: activeUpload,
          transaction_ids: selectedIds,
          expense_type: bulkExpenseType,
          payment_mode: bulkPaymentMode,
          description: bulkDescription,
        }),
      });
      const data = await res.json();
      if (data.detail && !data.success) throw new Error(data.detail);
      toast.success(data.message || `Bulk added ${data.added} expense(s)`);
      setBulkDialogOpen(false);
      setSelectedIds([]);
      setBulkExpenseType('');
      setBulkDescription('');
      loadSummary(activeUpload);
    } catch (e) { toast.error(e.message); }
    finally { setBulkBusy(false); }
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

  const bulkIgnore = async () => {
    if (selectedIds.length === 0) return;
    const reason = window.prompt(`Reason for ignoring ${selectedIds.length} selected transaction(s)?`);
    if (!reason) return;
    setBulkBusy(true);
    try {
      const res = await fetch(`${API}/api/bank-reconciliation/bulk-ignore`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transaction_ids: selectedIds,
          upload_id: activeUpload,
          reason,
          token: session.token,
        }),
      });
      const data = await res.json();
      if (data.detail && !data.success) throw new Error(data.detail);
      toast.success(`${data.ignored_count || selectedIds.length} transaction(s) ignored`);
      setSelectedIds([]);
      loadSummary(activeUpload);
    } catch (e) { toast.error(e.message); }
    finally { setBulkBusy(false); }
  };

  const aiCategorize = async () => {
    if (!activeUpload) return;
    setAiBusy(true);
    try {
      toast.info('Asking Claude to categorize unmatched transactions...');
      const res = await fetch(`${API}/api/bank-reconciliation/ai-categorize`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          upload_id: activeUpload,
          token: session.token,
          transaction_ids: selectedIds.length > 0 ? selectedIds : null,
        }),
      });
      const data = await res.json();
      if (data.detail && !data.success) throw new Error(data.detail);
      toast.success(data.message || `AI categorized ${data.categorized} transactions`);
      loadSummary(activeUpload);
    } catch (e) { toast.error(e.message); }
    finally { setAiBusy(false); }
  };

  const autoConvert = async () => {
    if (!activeUpload) return;
    if (!window.confirm('Auto-convert AI-categorized debits to Expense rows? Duplicates (same date+amount already booked) will be skipped.')) return;
    setAiBusy(true);
    try {
      const res = await fetch(`${API}/api/bank-reconciliation/auto-convert`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          upload_id: activeUpload,
          token: session.token,
          transaction_ids: selectedIds.length > 0 ? selectedIds : null,
          min_confidence: 0.7,
          payment_mode: 'Bank Transfer',
        }),
      });
      const data = await res.json();
      if (data.detail && !data.success) throw new Error(data.detail);
      toast.success(data.message || `Converted ${data.converted}`);
      setSelectedIds([]);
      loadSummary(activeUpload);
    } catch (e) { toast.error(e.message); }
    finally { setAiBusy(false); }
  };

  const autoConvertCreditsToSales = async () => {
    if (!activeUpload) return;
    if (!window.confirm('Auto-convert AI-categorized CREDITS into Daily Sales rows? Days that already have a sales record will be skipped (no overwrite).')) return;
    setAiBusy(true);
    try {
      const res = await fetch(`${API}/api/bank-reconciliation/auto-convert-credits-to-sales`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          upload_id: activeUpload,
          token: session.token,
          transaction_ids: selectedIds.length > 0 ? selectedIds : null,
          min_confidence: 0.7,
        }),
      });
      const data = await res.json();
      if (data.detail && !data.success) throw new Error(data.detail);
      toast.success(data.message || `Created ${data.created} sales row(s)`);
      setSelectedIds([]);
      loadSummary(activeUpload);
    } catch (e) { toast.error(e.message); }
    finally { setAiBusy(false); }
  };

  const editTxnInline = async (txn, patch) => {
    try {
      const res = await fetch(`${API}/api/bank-reconciliation/edit-transaction`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          upload_id: activeUpload,
          transaction_id: txn.transaction_id,
          token: session.token,
          ...patch,
        }),
      });
      const data = await res.json();
      if (data.detail && !data.success) throw new Error(data.detail);
      if (data.changes && data.changes.length > 0) toast.success(`Updated ${data.changes.length} field(s)`);
      loadSummary(activeUpload);
    } catch (e) { toast.error(e.message); }
  };

  const autoConvert_legacy_removed = async () => {
    // placeholder removed
    return;
  };

  const resetTxn = async (txn, fromStatus, silent = false) => {
    if (!silent) {
      const msg = fromStatus === 'added'
        ? 'Remove this expense and reset transaction to Unrecorded?'
        : 'Undo Ignore — move this transaction back to Unrecorded?';
      if (!window.confirm(msg)) return;
    }
    try {
      const res = await fetch(`${API}/api/bank-reconciliation/reset-transaction`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: session.token,
          upload_id: activeUpload,
          transaction_id: txn.transaction_id,
        }),
      });
      const data = await res.json();
      if (data.detail && !data.success) throw new Error(data.detail);
      if (!silent) toast.success(fromStatus === 'added' ? 'Expense removed; txn back to Unrecorded' : 'Undone; txn back to Unrecorded');
      loadSummary(activeUpload);
    } catch (e) { toast.error(e.message); }
  };

  const moveToIgnored = async (txn) => {
    if (!window.confirm('Remove the linked expense and mark this transaction as Ignored?')) return;
    try {
      // First reset (deletes expense), then ignore
      await fetch(`${API}/api/bank-reconciliation/reset-transaction`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, upload_id: activeUpload, transaction_id: txn.transaction_id }),
      });
      const reason = window.prompt('Reason for ignoring? (optional)') || '';
      await fetch(`${API}/api/bank-reconciliation/ignore`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, upload_id: activeUpload, transaction_id: txn.transaction_id, reason }),
      });
      toast.success('Moved to Ignored');
      loadSummary(activeUpload);
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6" data-testid="bank-reconciliation-page">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2"><Banknote className="w-6 h-6 text-sky-700" /> Bank Reconciliation</h1>
        <p className="text-sm text-muted-foreground">Upload a bank statement (CSV / Excel / PDF). The system reconciles both credits (sales/PhonePe/Razorpay/aggregators) and debits (expenses), auto-flags cash withdrawals as Ignored, and routes high-value unknowns to Manual Review.</p>
      </div>

      {/* Upload */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Upload Bank Statement</CardTitle>
        <CardDescription>Supported: CSV, XLS, XLSX, PDF. Matches both <strong>credits</strong> (sales / PhonePe / Razorpay / Aggregators) and <strong>debits</strong> (expenses). ATM / cash withdrawals are auto-ignored.</CardDescription>
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
              <Input type="file" accept=".csv,.xls,.xlsx,.pdf" onChange={e => setFile(e.target.files[0])} data-testid="br-file-input" />
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
                    <th className="p-2 text-right">Partial</th>
                    <th className="p-2 text-right">Unmatched</th>
                    <th className="p-2 text-right whitespace-nowrap">Manual Review</th>
                    <th className="p-2 text-right">Ignored</th>
                    <th className="p-2 text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {uploads.map((u) => (
                    <tr key={u.upload_id} className={`border-t hover:bg-slate-50 ${activeUpload === u.upload_id ? 'bg-sky-50' : ''}`}>
                      <td className="p-2 text-xs text-muted-foreground">{u.uploaded_at?.slice(0, 10)}</td>
                      <td className="p-2">{u.month}</td>
                      <td className="p-2 text-xs">{u.filename}</td>
                      <td className="p-2 text-right">{u.total_transactions || '—'}</td>
                      <td className="p-2 text-right text-green-700">{u.matched_count || '—'}</td>
                      <td className="p-2 text-right text-yellow-700">{u.partially_matched_count || '—'}</td>
                      <td className="p-2 text-right text-amber-700">{u.unrecorded_count || '—'}</td>
                      <td className="p-2 text-right text-rose-700">{u.manual_review_count || '—'}</td>
                      <td className="p-2 text-right text-slate-500">{u.auto_ignored_count || '—'}</td>
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
            <CardDescription className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
              <span>Debits: <strong>{fmtINR(summary.summary.total_bank_debits)}</strong></span>
              <span>Credits: <strong className="text-emerald-700">{fmtINR(summary.summary.total_bank_credits || 0)}</strong></span>
              <span>Matched: <strong className="text-green-700">{fmtINR(summary.summary.matched_amount)}</strong></span>
              <span>Partial: <strong className="text-yellow-700">{fmtINR(summary.summary.partially_matched_amount || 0)}</strong></span>
              <span>Unmatched: <strong className="text-amber-700">{fmtINR(summary.summary.unrecorded_amount)}</strong></span>
              <span>Manual Review: <strong className="text-rose-700">{fmtINR(summary.summary.manual_review_amount || 0)}</strong></span>
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="unrecorded">
              <TabsList className="flex-wrap h-auto">
                <TabsTrigger value="unrecorded" data-testid="br-tab-unrecorded">Unmatched ({summary.summary.unrecorded_count})</TabsTrigger>
                <TabsTrigger value="partial" data-testid="br-tab-partial">Partially Matched ({summary.summary.partially_matched_count || 0})</TabsTrigger>
                <TabsTrigger value="matched" data-testid="br-tab-matched">Matched ({summary.summary.matched_count})</TabsTrigger>
                <TabsTrigger value="credits" data-testid="br-tab-credits">Unmatched Credits ({summary.summary.unmatched_credit_count || 0})</TabsTrigger>
                <TabsTrigger value="manual" data-testid="br-tab-manual">Manual Review ({summary.summary.manual_review_count || 0})</TabsTrigger>
                <TabsTrigger value="added" data-testid="br-tab-added">Added ({summary.summary.added_count || 0})</TabsTrigger>
                <TabsTrigger value="ignored" data-testid="br-tab-ignored">Ignored ({summary.summary.ignored_count || 0})</TabsTrigger>
              </TabsList>

              <TabsContent value="unrecorded" className="mt-3">
                {/* Phase 3: AI categorize + auto-convert toolbar (always visible) */}
                <div className="flex flex-wrap items-center justify-between gap-3 p-3 mb-3 bg-violet-50 border border-violet-200 rounded-lg" data-testid="br-ai-toolbar">
                  <div className="text-sm">
                    <strong className="text-violet-800">🤖 AI Categorizer</strong>
                    <span className="text-muted-foreground ml-2 text-xs">
                      Claude reads each bank narration and suggests the best Category Master tag.
                      Confidence ≥ 0.7 → can auto-convert to expense rows (duplicates skipped).
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" className="border-violet-300 text-violet-800 hover:bg-violet-100"
                      disabled={aiBusy} onClick={aiCategorize} data-testid="br-ai-categorize">
                      {aiBusy && <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />}
                      🤖 AI Categorize {selectedIds.length > 0 ? `(${selectedIds.length} selected)` : '(all unmatched)'}
                    </Button>
                    <Button size="sm" className="bg-violet-700 hover:bg-violet-800 text-white"
                      disabled={aiBusy} onClick={autoConvert} data-testid="br-auto-convert">
                      ⚡ Auto-Convert to Expenses
                    </Button>
                  </div>
                </div>

                {/* Bulk-add toolbar — appears when 1+ row(s) selected */}
                {selectedIds.length > 0 && (
                  <div className="flex flex-wrap items-center justify-between gap-3 p-3 mb-3 bg-sky-50 border border-sky-200 rounded-lg" data-testid="br-bulk-toolbar">
                    <div className="text-sm">
                      <strong>{selectedIds.length}</strong> transaction(s) selected
                      <span className="text-muted-foreground ml-2">· Total ₹{(summary.unrecorded || []).filter(t => selectedIds.includes(t.transaction_id)).reduce((a, t) => a + (t.debit_amount || 0), 0).toLocaleString('en-IN')}</span>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => setSelectedIds([])} data-testid="br-bulk-clear">Clear</Button>
                      <Button size="sm" variant="outline" className="border-red-300 text-red-700 hover:bg-red-50"
                        onClick={bulkIgnore} disabled={bulkBusy}
                        data-testid="br-bulk-ignore">
                        <X className="w-3.5 h-3.5 mr-1" /> Bulk Ignore ({selectedIds.length})
                      </Button>
                      <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white" onClick={() => setBulkDialogOpen(true)} data-testid="br-bulk-open">
                        <Layers className="w-3.5 h-3.5 mr-1" /> Bulk Add as Expense ({selectedIds.length})
                      </Button>
                    </div>
                  </div>
                )}
                {selectedIds.length === 0 && summary.unrecorded?.length > 1 && (
                  <p className="text-xs text-slate-500 mb-2">💡 Tip: tick the checkboxes (or click on any narration text to auto-select all rows with the same narration) to bulk-add similar transactions in one click.</p>
                )}
                <TxnTable
                  rows={summary.unrecorded}
                  empty="All bank debits are reconciled!"
                  badgeColor="bg-amber-100 text-amber-700 border-amber-300"
                  selection={{ selected: selectedIds, setSelected: setSelectedIds }}
                  onEdit={editTxnInline}
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
              <TabsContent value="partial" className="mt-3">
                <p className="text-xs text-slate-500 mb-2">💡 Fuzzy match — date within ±2-3 days OR amount drift ≤5%. Verify these manually.</p>
                <TxnTable rows={summary.partially_matched} empty="No partially-matched transactions." badgeColor="bg-yellow-100 text-yellow-800 border-yellow-300" />
              </TabsContent>
              <TabsContent value="credits" className="mt-3">
                <p className="text-xs text-slate-500 mb-2">💰 Credits (Sales / PhonePe / Razorpay / Aggregator) that don&apos;t tie back to recorded sources. Run AI Categorize to classify, then Convert to Sales to auto-create daily_sales rows.</p>
                <div className="flex flex-wrap items-center justify-between gap-3 p-3 mb-3 bg-emerald-50 border border-emerald-200 rounded-lg" data-testid="br-credit-ai-toolbar">
                  <div className="text-sm">
                    <strong className="text-emerald-800">🤖 AI Sales Classifier</strong>
                    <span className="text-muted-foreground ml-2 text-xs">
                      Claude tags each credit as Cash / Online / PhonePe / Swiggy / Zomato / etc. then auto-creates daily_sales rows. Existing manual sales are NEVER overwritten.
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" className="border-emerald-300 text-emerald-800 hover:bg-emerald-100"
                      disabled={aiBusy} onClick={aiCategorize} data-testid="br-credit-ai-categorize">
                      {aiBusy && <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />}
                      🤖 AI Categorize {selectedIds.length > 0 ? `(${selectedIds.length} selected)` : '(all unmatched)'}
                    </Button>
                    <Button size="sm" className="bg-emerald-700 hover:bg-emerald-800 text-white"
                      disabled={aiBusy} onClick={autoConvertCreditsToSales} data-testid="br-auto-convert-credits-to-sales">
                      ⚡ Convert Credits to Sales
                    </Button>
                  </div>
                </div>
                <TxnTable rows={summary.unmatched_credits || []} empty="All credit deposits reconciled with recorded sales / settlements." badgeColor="bg-emerald-100 text-emerald-700 border-emerald-300" onEdit={editTxnInline} />
              </TabsContent>
              <TabsContent value="manual" className="mt-3">
                <p className="text-xs text-slate-500 mb-2">🚨 High-value (≥ ₹50,000) transactions that didn&apos;t match. Review and either Add as Expense or Ignore.</p>
                <TxnTable
                  rows={summary.manual_review || []}
                  empty="No transactions need manual review."
                  badgeColor="bg-rose-100 text-rose-700 border-rose-300"
                  actions={(txn) => txn.txn_type === 'debit' ? (
                    <div className="flex gap-1 justify-end">
                      <Button size="sm" className="bg-green-700 hover:bg-green-800 text-white" onClick={() => openAdd(txn)} data-testid={`br-add-${txn.transaction_id}`}><Plus className="w-3 h-3 mr-1" /> Add</Button>
                      <Button size="sm" variant="outline" className="border-red-300 text-red-700" onClick={() => ignoreTxn(txn)} data-testid={`br-ignore-${txn.transaction_id}`}><X className="w-3 h-3 mr-1" /> Ignore</Button>
                    </div>
                  ) : (
                    <Button size="sm" variant="outline" className="border-red-300 text-red-700" onClick={() => ignoreTxn(txn)} data-testid={`br-ignore-${txn.transaction_id}`}><X className="w-3 h-3 mr-1" /> Ignore</Button>
                  )}
                />
              </TabsContent>
              <TabsContent value="added" className="mt-3">
                <TxnTable
                  rows={summary.added || []}
                  empty="No transactions added as expense yet."
                  badgeColor="bg-blue-100 text-blue-700 border-blue-300"
                  actions={(txn) => (
                    <div className="flex gap-1 justify-end">
                      <Button size="sm" variant="outline" className="border-red-300 text-red-700 hover:bg-red-50"
                        onClick={() => resetTxn(txn, 'added')}
                        data-testid={`br-remove-${txn.transaction_id}`}>
                        <X className="w-3 h-3 mr-1" /> Delete
                      </Button>
                      <Button size="sm" variant="outline" className="border-slate-300 text-slate-700"
                        onClick={() => moveToIgnored(txn)}
                        data-testid={`br-move-ignore-${txn.transaction_id}`}>
                        Move to Ignore
                      </Button>
                    </div>
                  )}
                />
              </TabsContent>
              <TabsContent value="ignored" className="mt-3">
                <TxnTable
                  rows={summary.ignored || []}
                  empty="No ignored transactions."
                  badgeColor="bg-slate-100 text-slate-700 border-slate-300"
                  actions={(txn) => (
                    <div className="flex gap-1 justify-end">
                      <Button size="sm" variant="outline" className="border-red-300 text-red-700 hover:bg-red-50"
                        onClick={() => resetTxn(txn, 'ignored')}
                        data-testid={`br-undo-ignore-${txn.transaction_id}`}>
                        <X className="w-3 h-3 mr-1" /> Delete
                      </Button>
                      <Button size="sm" className="bg-green-700 hover:bg-green-800 text-white"
                        onClick={async () => { await resetTxn(txn, 'ignored', true); openAdd(txn); }}
                        data-testid={`br-add-from-ignored-${txn.transaction_id}`}>
                        <Plus className="w-3 h-3 mr-1" /> Add as Expense
                      </Button>
                    </div>
                  )}
                />
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

      {/* Bulk Add Dialog */}
      <Dialog open={bulkDialogOpen} onOpenChange={(o) => !bulkBusy && setBulkDialogOpen(o)}>
        <DialogContent className="max-w-lg" data-testid="br-bulk-dialog">
          <DialogHeader>
            <DialogTitle>Bulk Add as Expense</DialogTitle>
            <DialogDescription>
              Apply the same category to <strong>{selectedIds.length}</strong> selected transaction(s).
              Each will become a separate expense row using its own date and amount.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            {/* Preview */}
            <div className="max-h-48 overflow-y-auto border rounded p-2 bg-slate-50 text-xs space-y-1">
              {(summary?.unrecorded || []).filter(t => selectedIds.includes(t.transaction_id)).slice(0, 8).map(t => (
                <div key={t.transaction_id} className="flex justify-between">
                  <span className="truncate max-w-[260px]" title={t.narration}>{t.transaction_date} · {t.narration}</span>
                  <span className="font-semibold">{fmtINR(t.debit_amount)}</span>
                </div>
              ))}
              {selectedIds.length > 8 && <p className="text-slate-500 italic">…and {selectedIds.length - 8} more</p>}
            </div>
            <div>
              <label className="text-xs font-semibold">Expense Category *</label>
              <Select value={bulkExpenseType} onValueChange={setBulkExpenseType}>
                <SelectTrigger data-testid="br-bulk-category"><SelectValue placeholder="Select category" /></SelectTrigger>
                <SelectContent>
                  {expenseCats.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-semibold">Payment Mode</label>
              <Select value={bulkPaymentMode} onValueChange={setBulkPaymentMode}>
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
              <label className="text-xs font-semibold">Description override (optional)</label>
              <Input
                value={bulkDescription}
                onChange={e => setBulkDescription(e.target.value)}
                placeholder="Leave blank to use each row's narration as-is"
                data-testid="br-bulk-description"
              />
              <p className="text-[10px] text-slate-500 mt-1">If blank, each expense uses its own bank narration.</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBulkDialogOpen(false)} disabled={bulkBusy}>Cancel</Button>
            <Button onClick={submitBulk} disabled={bulkBusy || !bulkExpenseType} className="bg-blue-600 hover:bg-blue-700 text-white" data-testid="br-bulk-save">
              {bulkBusy && <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />}
              {bulkBusy ? 'Adding...' : `Add ${selectedIds.length} Expense(s)`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function TxnTable({ rows, empty, badgeColor, actions, selection, onEdit }) {
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState('');
  if (!rows || rows.length === 0) return <p className="text-sm text-muted-foreground p-4">{empty}</p>;
  const showSelect = !!selection;
  const allOnPage = showSelect && rows.every(r => selection.selected.includes(r.transaction_id));
  const toggleAll = () => {
    if (allOnPage) selection.setSelected(selection.selected.filter(id => !rows.some(r => r.transaction_id === id)));
    else selection.setSelected([...new Set([...selection.selected, ...rows.map(r => r.transaction_id)])]);
  };
  const toggleOne = (id) => {
    if (selection.selected.includes(id)) selection.setSelected(selection.selected.filter(x => x !== id));
    else selection.setSelected([...selection.selected, id]);
  };
  // Group similar narrations: stable hash on first 3 words / 30 chars
  const narrationKey = (n) => (n || '').replace(/\s+/g, ' ').trim().slice(0, 30).toUpperCase();
  // Show Credit column whenever ANY row has a credit OR is a credit type
  const hasCredits = rows.some(r => (r.credit_amount || 0) > 0 || r.txn_type === 'credit');
  return (
    <div className="overflow-x-auto border rounded">
      <table className="w-full text-sm">
        <thead className="bg-slate-100 text-xs uppercase">
          <tr>
            {showSelect && (
              <th className="p-2 text-center w-8">
                <Checkbox checked={allOnPage} onCheckedChange={toggleAll} data-testid="br-select-all" />
              </th>
            )}
            <th className="p-2 text-left">Date</th>
            <th className="p-2 text-left">Narration</th>
            <th className="p-2 text-right">Debit (₹)</th>
            {hasCredits && <th className="p-2 text-right text-emerald-700">Credit (₹)</th>}
            <th className="p-2 text-left">Suggested / Source</th>
            <th className="p-2 text-center">Status</th>
            {actions && <th className="p-2 text-right">Action</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => {
            const isCredit = (t.credit_amount || 0) > 0 || t.txn_type === 'credit';
            const aiTag = t.ai_suggested_category;
            const aiConf = t.ai_confidence;
            const hint = aiTag || t.suggested_category || t.credit_source_hint || (t.matched_credit?.source) || (t.matched_expense?.expense_type) || '—';
            const statusLabel = (t.recon_status || t.match_status || 'unknown').replace(/_/g, ' ').toUpperCase();
            // Show PhonePe MDR commission if the matched credit carried it through
            const pgComm = t.matched_credit?.pg_commission;
            return (
              <tr key={t.transaction_id} className={`border-t hover:bg-slate-50 ${showSelect && selection.selected.includes(t.transaction_id) ? 'bg-sky-50' : ''}`}>
                {showSelect && (
                  <td className="p-2 text-center">
                    <Checkbox checked={selection.selected.includes(t.transaction_id)} onCheckedChange={() => toggleOne(t.transaction_id)} data-testid={`br-select-${t.transaction_id}`} />
                  </td>
                )}
                <td className="p-2 text-xs">{t.transaction_date}</td>
                <td className="p-2 text-xs max-w-sm">
                  {editingId === t.transaction_id ? (
                    <span className="flex items-center gap-1">
                      <Input
                        value={editDraft}
                        onChange={(e) => setEditDraft(e.target.value)}
                        className="h-7 text-xs"
                        data-testid={`br-edit-narration-input-${t.transaction_id}`}
                      />
                      <Button size="sm" variant="outline" className="h-7 px-2"
                        onClick={() => { onEdit && onEdit(t, { narration: editDraft }); setEditingId(null); }}
                        data-testid={`br-edit-save-${t.transaction_id}`}>Save</Button>
                      <Button size="sm" variant="ghost" className="h-7 px-2"
                        onClick={() => setEditingId(null)}>Cancel</Button>
                    </span>
                  ) : (
                    <span>
                      <span className="cursor-pointer text-sky-700 underline-offset-2 hover:underline" title="Click to select all rows with same narration"
                        onClick={(e) => {
                          if (!showSelect) return;
                          e.stopPropagation();
                          const key = narrationKey(t.narration);
                          const ids = rows.filter(r => narrationKey(r.narration) === key).map(r => r.transaction_id);
                          selection.setSelected([...new Set([...selection.selected, ...ids])]);
                        }}>
                        {t.narration}
                      </span>
                      {onEdit && (
                        <button
                          className="ml-1 text-[10px] text-violet-600 hover:text-violet-900"
                          title="Edit narration"
                          onClick={() => { setEditingId(t.transaction_id); setEditDraft(t.narration || ''); }}
                          data-testid={`br-edit-narration-${t.transaction_id}`}
                        >✎ edit</button>
                      )}
                      {t.original_narration && t.original_narration !== t.narration && (
                        <span className="block text-[9px] text-slate-400 italic mt-0.5" title="Original bank narration before edit">
                          (raw: {t.original_narration})
                        </span>
                      )}
                      {t.auto_ignored && <Badge className="ml-2 bg-slate-200 text-slate-700 text-[10px]">AUTO</Badge>}
                      {pgComm > 0 && <span className="block text-[10px] text-purple-700 mt-0.5">PG Comm: {fmtINR(pgComm)}</span>}
                    </span>
                  )}
                </td>
                <td className="p-2 text-right font-semibold text-slate-700">{(t.debit_amount || 0) > 0 ? fmtINR(t.debit_amount) : '—'}</td>
                {hasCredits && (
                  <td className="p-2 text-right font-semibold text-emerald-700">{(t.credit_amount || 0) > 0 ? fmtINR(t.credit_amount) : '—'}</td>
                )}
                <td className="p-2 text-xs text-sky-700">
                  {aiTag ? (
                    <span className="inline-flex items-center gap-1">
                      <Badge className="bg-violet-100 text-violet-800 border-violet-300 text-[10px]">🤖 AI</Badge>
                      <span className="font-semibold">{aiTag}</span>
                      {typeof aiConf === 'number' && (
                        <span className={`text-[10px] ${aiConf >= 0.7 ? 'text-green-600' : 'text-amber-600'}`}>{(aiConf * 100).toFixed(0)}%</span>
                      )}
                    </span>
                  ) : (hint)}
                </td>
                <td className="p-2 text-center">
                  <Badge className={badgeColor}>{statusLabel}</Badge>
                  {isCredit && <Badge className="ml-1 bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px]">CR</Badge>}
                </td>
                {actions && <td className="p-2 text-right">{actions(t)}</td>}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
