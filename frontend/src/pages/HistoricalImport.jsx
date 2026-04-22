import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/App';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Upload, FileSpreadsheet, CheckCircle, AlertCircle, Database, Trash2, ArrowLeft, Landmark, Calendar } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function HistoricalImport() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  // Loans state
  const [loansFile, setLoansFile] = useState(null);
  const [loansUploading, setLoansUploading] = useState(false);
  const [lastLoansResult, setLastLoansResult] = useState(null);
  const [loansSummary, setLoansSummary] = useState(null);
  // Monthly file state
  const [monthlyFiles, setMonthlyFiles] = useState([]);
  const [monthlyUploading, setMonthlyUploading] = useState(false);
  const [monthlyResults, setMonthlyResults] = useState([]);
  const [monthlySummary, setMonthlySummary] = useState(null);

  const isSuperAdmin = session?.role === 'super_admin' || session?.is_super_admin;

  const fetchSummary = useCallback(async () => {
    if (!session?.token) return;
    setLoadingSummary(true);
    try {
      const [wcRes, ldRes, mRes] = await Promise.all([
        fetch(`${API}/api/historical/summary`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: session.token }),
        }),
        fetch(`${API}/api/historical/loans-summary`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: session.token }),
        }),
        fetch(`${API}/api/historical/monthly-summary`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: session.token }),
        }),
      ]);
      if (wcRes.ok) setSummary(await wcRes.json());
      if (ldRes.ok) setLoansSummary(await ldRes.json());
      if (mRes.ok) setMonthlySummary(await mRes.json());
    } finally {
      setLoadingSummary(false);
    }
  }, [session]);

  useEffect(() => { fetchSummary(); }, [fetchSummary]);

  const handleUpload = async () => {
    if (!file) { toast.error('Pick a .xlsx file first'); return; }
    setUploading(true);
    const fd = new FormData();
    fd.append('file', file);
    fd.append('token', session.token);
    try {
      const res = await fetch(`${API}/api/historical/import-wc-file`, { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Import failed');
      setLastResult(data);
      toast.success(`Imported ${data.total_rows} month rows across ${Object.keys(data.centers).length} centers`);
      fetchSummary();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleClear = async (center) => {
    if (!window.confirm(`Delete historical rows for ${center || 'ALL CENTERS'}? This cannot be undone.`)) return;
    const res = await fetch(`${API}/api/historical/clear`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: session.token, center }),
    });
    const data = await res.json();
    if (res.ok) { toast.success(`Deleted ${data.deleted} rows`); fetchSummary(); }
    else toast.error(data.detail || 'Failed');
  };

  const handleLoansUpload = async () => {
    if (!loansFile) { toast.error('Pick a .xlsx file first'); return; }
    setLoansUploading(true);
    const fd = new FormData();
    fd.append('file', loansFile);
    fd.append('token', session.token);
    try {
      const res = await fetch(`${API}/api/historical/import-loans-file`, { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Import failed');
      setLastLoansResult(data);
      toast.success(`Imported ${data.pairs_upserted} loan pairs across ${Object.keys(data.by_home_center).length} centers`);
      fetchSummary();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoansUploading(false);
    }
  };

  const handleClearLoans = async (center) => {
    if (!window.confirm(`Delete historical LOAN entries for ${center || 'ALL CENTERS'}? This cannot be undone.`)) return;
    const res = await fetch(`${API}/api/historical/clear-loans`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: session.token, center }),
    });
    const data = await res.json();
    if (res.ok) { toast.success(`Deleted ${data.deleted} loan rows`); fetchSummary(); }
    else toast.error(data.detail || 'Failed');
  };

  const handleMonthlyUpload = async () => {
    if (!monthlyFiles.length) { toast.error('Pick one or more .xlsx files'); return; }
    setMonthlyUploading(true);
    const results = [];
    for (const f of monthlyFiles) {
      const fd = new FormData();
      fd.append('file', f);
      fd.append('token', session.token);
      try {
        const res = await fetch(`${API}/api/historical/import-monthly-file`, { method: 'POST', body: fd });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Import failed');
        results.push({ ok: true, name: f.name, ...data });
      } catch (err) {
        results.push({ ok: false, name: f.name, error: err.message });
      }
    }
    setMonthlyResults(results);
    const okCount = results.filter(r => r.ok).length;
    toast[okCount === results.length ? 'success' : 'warning'](
      `${okCount} of ${results.length} files imported`
    );
    setMonthlyFiles([]);
    fetchSummary();
    setMonthlyUploading(false);
  };

  const handleClearMonthly = async (center, month) => {
    const label = month ? `${center} ${month}` : (center || 'ALL monthly imports');
    if (!window.confirm(`Delete monthly import data for ${label}? (trial balance + expenses + sales rows from imports)`)) return;
    const res = await fetch(`${API}/api/historical/clear-monthly`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: session.token, center, month }),
    });
    const data = await res.json();
    if (res.ok) {
      toast.success(`Cleared: ${data.expenses_deleted} exp · ${data.sales_deleted} sales · ${data.trial_balance_deleted} TB`);
      fetchSummary();
    } else {
      toast.error(data.detail || 'Failed');
    }
  };

  if (!isSuperAdmin) {
    return <div className="p-8 text-center text-muted-foreground">Only Super Admin can access Historical Import.</div>;
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6" data-testid="historical-import-page">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)} data-testid="historical-back-btn"><ArrowLeft className="w-4 h-4 mr-1" /> Back</Button>
        <div>
          <h1 className="text-2xl font-bold">Historical Data Import</h1>
          <p className="text-sm text-muted-foreground">Upload WC Assessment Excel files (Apr 2024 onwards). Imported rows flow into WC Breakdown, MIS Dashboard and Franchise Dashboard for months without live daily data.</p>
        </div>
      </div>

      <Card className="border-[#8B0000]/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Upload className="w-5 h-5 text-[#8B0000]" /> Upload WC Rollup File</CardTitle>
          <CardDescription>Accepted: <strong>.xlsx</strong> with sheets whose names contain center keywords (HSR, DOMBIVLI, THANE, S-NAGAR, KHARADI, HINJAWADI, BANER). Each sheet must have columns <code>MONTH</code>, <code>SALE</code>, <code>EXPENSES</code>, <code>P/L</code>, <code>WORKING CAPITAL</code>, <code>BAL. WC.</code>, <code>BANK CL.BAL.</code>.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="file" accept=".xlsx,.xls"
              data-testid="historical-file-input"
              onChange={(e) => { setFile(e.target.files?.[0] || null); setLastResult(null); }}
              className="flex-1 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-[#8B0000] file:text-white hover:file:bg-[#6B0000]"
            />
            <Button onClick={handleUpload} disabled={!file || uploading} className="bg-[#8B0000] hover:bg-[#6B0000]" data-testid="historical-upload-btn">
              {uploading ? 'Importing...' : 'Import'}
            </Button>
          </div>

          {lastResult && (
            <div className="rounded-lg border p-4 bg-green-50 dark:bg-green-900/10" data-testid="historical-last-result">
              <div className="flex items-start gap-2">
                <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1 text-sm">
                  <p className="font-semibold text-green-800 dark:text-green-200">
                    {lastResult.file}: {lastResult.total_rows} rows upserted across {lastResult.sheets_processed} sheets
                  </p>
                  <ul className="mt-2 space-y-1">
                    {Object.entries(lastResult.centers).map(([c, n]) => (
                      <li key={c} className="text-xs">• <strong>{c}</strong>: {n} months</li>
                    ))}
                  </ul>
                  {lastResult.sheets_skipped?.length > 0 && (
                    <div className="mt-3">
                      <p className="text-xs font-semibold text-amber-700 dark:text-amber-300 flex items-center gap-1"><AlertCircle className="w-3 h-3" /> Skipped sheets:</p>
                      <ul className="mt-1 space-y-0.5">
                        {lastResult.sheets_skipped.map((s, i) => (
                          <li key={i} className="text-xs text-muted-foreground">• {s.sheet} — {s.reason}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Database className="w-5 h-5" /> Current Historical Data</CardTitle>
          <CardDescription>Month-level summary per center, imported into the <code>historical_monthly_summary</code> collection.</CardDescription>
        </CardHeader>
        <CardContent>
          {loadingSummary ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : summary?.centers?.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="historical-summary-table">
                <thead>
                  <tr className="border-b bg-muted">
                    <th className="px-3 py-2 text-left font-medium">Center</th>
                    <th className="px-3 py-2 text-right font-medium">Months</th>
                    <th className="px-3 py-2 text-left font-medium">Range</th>
                    <th className="px-3 py-2 text-right font-medium">Total Sales</th>
                    <th className="px-3 py-2 text-right font-medium">Total Expenses</th>
                    <th className="px-3 py-2 text-center font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.centers.map(c => (
                    <tr key={c.center} className="border-b hover:bg-muted/30">
                      <td className="px-3 py-2 font-semibold">{c.center}</td>
                      <td className="px-3 py-2 text-right">{c.months}</td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">{c.earliest} → {c.latest}</td>
                      <td className="px-3 py-2 text-right font-mono">₹{Math.round(c.total_sale).toLocaleString('en-IN')}</td>
                      <td className="px-3 py-2 text-right font-mono">₹{Math.round(c.total_expenses).toLocaleString('en-IN')}</td>
                      <td className="px-3 py-2 text-center">
                        <Button size="sm" variant="ghost" onClick={() => handleClear(c.center)} data-testid={`historical-clear-${c.center}`}>
                          <Trash2 className="w-4 h-4 text-red-600" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                  <tr className="bg-muted/50 font-semibold">
                    <td className="px-3 py-2">Total</td>
                    <td className="px-3 py-2 text-right">{summary.total_rows}</td>
                    <td></td>
                    <td className="px-3 py-2 text-right font-mono">₹{summary.centers.reduce((a,c)=>a+c.total_sale,0).toLocaleString('en-IN', {maximumFractionDigits:0})}</td>
                    <td className="px-3 py-2 text-right font-mono">₹{summary.centers.reduce((a,c)=>a+c.total_expenses,0).toLocaleString('en-IN', {maximumFractionDigits:0})}</td>
                    <td className="px-3 py-2 text-center">
                      <Button size="sm" variant="ghost" onClick={() => handleClear(null)} data-testid="historical-clear-all">
                        <Trash2 className="w-4 h-4 text-red-600" />
                      </Button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8">
              <FileSpreadsheet className="w-12 h-12 text-muted-foreground mx-auto mb-3 opacity-50" />
              <p className="text-sm text-muted-foreground">No historical data imported yet. Upload a WC Assessment Excel to get started.</p>
            </div>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Landmark className="w-5 h-5 text-amber-700" /> Loans Import (Inter-Center Transfers)</CardTitle>
          <CardDescription>Upload the same WC file to ingest LOANS sheets. Each DATE / AMOUNT GIVEN / AMOUNT RECD. column-group creates a mirror pair (given + taken) in the Loans module. Idempotent by <code>loan_id</code> — safe to re-upload.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="file" accept=".xlsx,.xls"
              data-testid="loans-file-input"
              onChange={(e) => { setLoansFile(e.target.files?.[0] || null); setLastLoansResult(null); }}
              className="flex-1 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-amber-700 file:text-white hover:file:bg-amber-800"
            />
            <Button onClick={handleLoansUpload} disabled={!loansFile || loansUploading} className="bg-amber-700 hover:bg-amber-800" data-testid="loans-upload-btn">
              {loansUploading ? 'Importing...' : 'Import Loans'}
            </Button>
          </div>

          {lastLoansResult && (
            <div className="rounded-lg border p-4 bg-amber-50 dark:bg-amber-900/10" data-testid="loans-last-result">
              <div className="flex items-start gap-2">
                <CheckCircle className="w-5 h-5 text-amber-700 flex-shrink-0 mt-0.5" />
                <div className="flex-1 text-sm">
                  <p className="font-semibold text-amber-800 dark:text-amber-200">
                    {lastLoansResult.file}: {lastLoansResult.pairs_upserted} pairs upserted across {lastLoansResult.sheets_processed} sheets
                  </p>
                  <ul className="mt-2 space-y-1">
                    {Object.entries(lastLoansResult.by_home_center).map(([c, n]) => (
                      <li key={c} className="text-xs">• <strong>{c}</strong>: {n} txns</li>
                    ))}
                  </ul>
                  {lastLoansResult.sheets_skipped?.length > 0 && (
                    <div className="mt-3">
                      <p className="text-xs font-semibold text-amber-700 flex items-center gap-1"><AlertCircle className="w-3 h-3" /> Skipped sheets:</p>
                      <ul className="mt-1 space-y-0.5">
                        {lastLoansResult.sheets_skipped.map((s, i) => (
                          <li key={i} className="text-xs text-muted-foreground">• {s.sheet} — {s.reason}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {loansSummary?.centers?.length > 0 && (
            <div className="overflow-x-auto pt-3">
              <table className="w-full text-sm" data-testid="loans-summary-table">
                <thead>
                  <tr className="border-b bg-muted">
                    <th className="px-3 py-2 text-left font-medium">Center</th>
                    <th className="px-3 py-2 text-right font-medium">Txns</th>
                    <th className="px-3 py-2 text-right font-medium">Total Given</th>
                    <th className="px-3 py-2 text-right font-medium">Total Taken</th>
                    <th className="px-3 py-2 text-right font-medium">Net</th>
                    <th className="px-3 py-2 text-center font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {loansSummary.centers.map(c => (
                    <tr key={c.center} className="border-b hover:bg-muted/30">
                      <td className="px-3 py-2 font-semibold">{c.center}</td>
                      <td className="px-3 py-2 text-right">{c.count}</td>
                      <td className="px-3 py-2 text-right font-mono text-green-700">₹{Math.round(c.given).toLocaleString('en-IN')}</td>
                      <td className="px-3 py-2 text-right font-mono text-red-700">₹{Math.round(c.taken).toLocaleString('en-IN')}</td>
                      <td className={`px-3 py-2 text-right font-mono font-semibold ${(c.given - c.taken) >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                        ₹{Math.round(c.given - c.taken).toLocaleString('en-IN')}
                      </td>
                      <td className="px-3 py-2 text-center">
                        <Button size="sm" variant="ghost" onClick={() => handleClearLoans(c.center)} data-testid={`loans-clear-${c.center}`}>
                          <Trash2 className="w-4 h-4 text-red-600" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                  <tr className="bg-muted/50 font-semibold">
                    <td className="px-3 py-2">Total</td>
                    <td className="px-3 py-2 text-right">{loansSummary.total_rows}</td>
                    <td colSpan={3}></td>
                    <td className="px-3 py-2 text-center">
                      <Button size="sm" variant="ghost" onClick={() => handleClearLoans(null)} data-testid="loans-clear-all">
                        <Trash2 className="w-4 h-4 text-red-600" />
                      </Button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
      <Card className="border-blue-700/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Calendar className="w-5 h-5 text-blue-700" /> Monthly Expense/Trial Balance Import</CardTitle>
          <CardDescription>
            Upload one or more monthly expense files (e.g. <code>EXPENCE SHEET -HSR- MARCH. 2026.xlsx</code>). Center + month are auto-detected from filename. Ingests:
            <span className="block mt-1">• <strong>TRIAL BAL.</strong> sheet → head-wise monthly rollup (GROCERY, RENT, etc.)</span>
            <span className="block">• <strong>Daily expense sheet</strong> (e.g. MARCH.26) → expense rows into the Expense Master</span>
            <span className="block">• <strong>CASH SALE + PHONE PE + CARD + SW + ZM</strong> → daily sales rows</span>
            <span className="block text-amber-700">Live daily sales (entered by operators) are never overwritten — they take precedence.</span>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="file" accept=".xlsx,.xls" multiple
              data-testid="monthly-file-input"
              onChange={(e) => { setMonthlyFiles(Array.from(e.target.files || [])); setMonthlyResults([]); }}
              className="flex-1 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-700 file:text-white hover:file:bg-blue-800"
            />
            <Button onClick={handleMonthlyUpload} disabled={!monthlyFiles.length || monthlyUploading} className="bg-blue-700 hover:bg-blue-800" data-testid="monthly-upload-btn">
              {monthlyUploading ? 'Importing…' : `Import ${monthlyFiles.length || ''} file${monthlyFiles.length === 1 ? '' : 's'}`}
            </Button>
          </div>

          {monthlyResults.length > 0 && (
            <div className="rounded-lg border p-4 bg-blue-50 dark:bg-blue-900/10 space-y-2 max-h-80 overflow-auto" data-testid="monthly-last-result">
              {monthlyResults.map((r, i) => (
                <div key={i} className="text-sm">
                  {r.ok ? (
                    <div className="flex items-start gap-2">
                      <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium">{r.name} → <strong>{r.center}</strong> {r.month}</p>
                        <p className="text-xs text-muted-foreground">
                          TB: {r.trial_balance.heads} heads (₹{Math.round(r.trial_balance.total_expenses).toLocaleString('en-IN')} exp / ₹{Math.round(r.trial_balance.total_sales).toLocaleString('en-IN')} sale)
                          · Expenses: {r.expenses.rows} rows
                          · Sales: {r.daily_sales.days} days{r.daily_sales.skipped_live_days ? ` (${r.daily_sales.skipped_live_days} kept live)` : ''}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium text-red-700">{r.name}</p>
                        <p className="text-xs text-muted-foreground">{r.error}</p>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {monthlySummary?.centers?.length > 0 && (
            <div className="overflow-x-auto pt-3">
              <table className="w-full text-sm" data-testid="monthly-summary-table">
                <thead>
                  <tr className="border-b bg-muted">
                    <th className="px-3 py-2 text-left font-medium">Center</th>
                    <th className="px-3 py-2 text-right font-medium">Months</th>
                    <th className="px-3 py-2 text-left font-medium">Range</th>
                    <th className="px-3 py-2 text-right font-medium">Total Expenses</th>
                    <th className="px-3 py-2 text-right font-medium">Total Sales</th>
                    <th className="px-3 py-2 text-center font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {monthlySummary.centers.map(c => (
                    <tr key={c.center} className="border-b hover:bg-muted/30">
                      <td className="px-3 py-2 font-semibold">{c.center}</td>
                      <td className="px-3 py-2 text-right">{c.months_count}</td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">{c.earliest} → {c.latest}</td>
                      <td className="px-3 py-2 text-right font-mono">₹{Math.round(c.total_expenses).toLocaleString('en-IN')}</td>
                      <td className="px-3 py-2 text-right font-mono">₹{Math.round(c.total_sales).toLocaleString('en-IN')}</td>
                      <td className="px-3 py-2 text-center">
                        <Button size="sm" variant="ghost" onClick={() => handleClearMonthly(c.center, null)} data-testid={`monthly-clear-${c.center}`}>
                          <Trash2 className="w-4 h-4 text-red-600" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                  <tr className="bg-muted/50 font-semibold">
                    <td className="px-3 py-2">Total</td>
                    <td className="px-3 py-2 text-right">{monthlySummary.total_files}</td>
                    <td></td>
                    <td className="px-3 py-2 text-right font-mono">₹{monthlySummary.centers.reduce((a,c)=>a+c.total_expenses,0).toLocaleString('en-IN', {maximumFractionDigits:0})}</td>
                    <td className="px-3 py-2 text-right font-mono">₹{monthlySummary.centers.reduce((a,c)=>a+c.total_sales,0).toLocaleString('en-IN', {maximumFractionDigits:0})}</td>
                    <td className="px-3 py-2 text-center">
                      <Button size="sm" variant="ghost" onClick={() => handleClearMonthly(null, null)} data-testid="monthly-clear-all">
                        <Trash2 className="w-4 h-4 text-red-600" />
                      </Button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          <div className="text-xs text-muted-foreground border-t pt-3">
            <strong>Where does the imported data appear?</strong>
            <ul className="list-disc pl-5 mt-1 space-y-0.5">
              <li>Center Accounts → <strong>WC Breakdown</strong> (the month row for that center)</li>
              <li><strong>MIS Dashboard</strong> sales / expenses / profit for any date range that includes the imported month</li>
              <li><strong>Franchise Owner Dashboard</strong> for the same center</li>
              <li>Expense Master / Sales ↔ Expenses Grid → the per-day rows with source="monthly_import:..."</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
