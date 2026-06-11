import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/App';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { FileText, AlertCircle, Download, Eye, TrendingUp, TrendingDown, FileSpreadsheet, FileBox, Calendar, ChevronDown, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import { Input } from '../components/ui/input';
import LedgersTab from '../components/LedgersTab';
import FinancialInsightsTab from '../components/FinancialInsightsTab';

const API = process.env.REACT_APP_BACKEND_URL;

// Small wrapper that turns a Card section into a click-to-collapse panel.
// Header stays clickable; chevron flips; content animates with the browser's
// native height-auto rules (no extra deps).
function CollapsibleSection({ id, title, description, defaultOpen = true, className = '', children, testId, headerExtra }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Card data-testid={testId || id} className={className}>
      <CardHeader
        className="pb-3 cursor-pointer select-none"
        onClick={() => setOpen(v => !v)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOpen(v => !v); } }}
        data-testid={`${testId || id}-toggle`}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            {open ? <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" /> : <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />}
            <div className="min-w-0">
              <CardTitle className="text-base">{title}</CardTitle>
              {description && <CardDescription className="mt-0.5">{description}</CardDescription>}
            </div>
          </div>
          {headerExtra}
        </div>
      </CardHeader>
      {open && <CardContent>{children}</CardContent>}
    </Card>
  );
}

const MONTHS = [
  '01', '02', '03', '04', '05', '06',
  '07', '08', '09', '10', '11', '12'
];
const YEARS = (() => {
  const y = new Date().getFullYear();
  const out = [];
  for (let i = y; i >= 2023; i--) out.push(String(i));
  return out;
})();

function fmtINR(n) {
  return `₹${Math.round(n || 0).toLocaleString('en-IN')}`;
}

export default function OwnerReports() {
  const { session } = useAuth();
  const [centers, setCenters] = useState([]);
  const [center, setCenter] = useState('');
  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [month, setMonth] = useState(String(new Date().getMonth() + 1).padStart(2, '0'));
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [previewBlobUrl, setPreviewBlobUrl] = useState(null);
  const [previewTitle, setPreviewTitle] = useState('');
  // Sales/Expense Excel filter state
  const [seMode, setSeMode] = useState('month'); // 'month' | 'range' | 'date'
  const [seStart, setSeStart] = useState('');
  const [seEnd, setSeEnd] = useState('');
  // Raw uploaded files for the selected month
  const [rawFiles, setRawFiles] = useState([]);
  const [rawFilesLoading, setRawFilesLoading] = useState(false);

  // Fetch the Sales/Expense Excel with the chosen filter
  const fetchSalesExpenseExcel = async (mode) => {
    try {
      const body = { token: session.token, center, mode: seMode };
      if (seMode === 'month') body.month = `${year}-${month}`;
      else if (seMode === 'range') { body.start_date = seStart; body.end_date = seEnd; }
      else if (seMode === 'date')  { body.start_date = seStart; }
      const res = await fetch(`${API}/api/franchise-reports/sales-expense-excel`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      if (!res.ok) { const err = await res.json().catch(()=>({})); throw new Error(err.detail || 'Failed'); }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      if (mode === 'preview') {
        // Excel can't render inline in <iframe>; show a sheet-style preview using a
        // SheetJS-driven view would be ideal, but for now offer Download with toast.
        const a = document.createElement('a');
        a.href = url; a.download = `Sales_Expense_${center}.xlsx`;
        document.body.appendChild(a); a.click(); a.remove();
        URL.revokeObjectURL(url);
        toast.info('Excel cannot be previewed inline — downloaded instead');
      } else {
        const a = document.createElement('a');
        a.href = url; a.download = `Sales_Expense_${center}_${seMode === 'month' ? `${year}-${month}` : `${seStart}_${seEnd || seStart}`}.xlsx`;
        document.body.appendChild(a); a.click(); a.remove();
        URL.revokeObjectURL(url);
        toast.success('Sales/Expense Excel downloaded');
      }
    } catch (e) { toast.error(e.message); }
  };

  // Fetch the Franchise Owner Ledger PDF (kept available outside the Email Pack)
  const fetchOwnerLedgerPdf = async (mode, lmode) => {
    try {
      const body = { token: session.token, center, period_type: 'month', month: `${year}-${month}`, fmt: 'pdf' };
      if (lmode === 'range') { body.period_type = 'range'; body.from_month = `${year}-${month}`; body.to_month = `${year}-${month}`; }
      const res = await fetch(`${API}/api/ledgers/owner`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      if (!res.ok) { const err = await res.json().catch(()=>({})); throw new Error(err.detail || 'Failed'); }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      if (mode === 'preview') {
        setPreviewBlobUrl(url);
        setPreviewTitle(`Franchise Owner Ledger — ${center} · ${year}-${month}`);
      } else {
        const a = document.createElement('a');
        a.href = url; a.download = `Owner_Ledger_${center}_${year}-${month}.pdf`;
        document.body.appendChild(a); a.click(); a.remove();
        URL.revokeObjectURL(url);
        toast.success('Owner Ledger downloaded');
      }
    } catch (e) { toast.error(e.message); }
  };

  // Load raw uploaded files for the current center+month
  const loadRawFiles = useCallback(async () => {
    if (!center) return;
    setRawFilesLoading(true);
    try {
      const res = await fetch(`${API}/api/franchise-reports/raw-files`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, center, month: `${year}-${month}` }),
      });
      if (!res.ok) { const err = await res.json().catch(()=>({})); throw new Error(err.detail || 'Failed'); }
      const data = await res.json();
      setRawFiles(data.files || []);
    } catch (e) {
      toast.error(e.message); setRawFiles([]);
    } finally {
      setRawFilesLoading(false);
    }
  }, [session?.token, center, year, month]);

  // Download a single raw file
  const downloadRawFile = async (rawId, filename) => {
    try {
      const res = await fetch(`${API}/api/franchise-reports/raw-file/download`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, raw_id: rawId }),
      });
      if (!res.ok) { const err = await res.json().catch(()=>({})); throw new Error(err.detail || 'Failed'); }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = filename || 'raw_file';
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error(e.message); }
  };

  // Common helper — fetch a PDF and either trigger download or show preview modal.
  const fetchReportPdf = async (r, mode) => {
    try {
      const res = await fetch(`${API}/api/${r.endpoint || 'center-accounts'}/${r.path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, center, month: `${year}-${month}` }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed' }));
        throw new Error(err.detail || 'Failed');
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      if (mode === 'preview') {
        setPreviewBlobUrl(url);
        setPreviewTitle(`${r.label} — ${center} · ${year}-${month}`);
      } else {
        const a = document.createElement('a');
        a.href = url;
        a.download = `${r.label.replace(/\s+/g, '_')}_${center}_${year}-${month}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        toast.success(`${r.label} downloaded`);
      }
    } catch (e) { toast.error(e.message); }
  };

  const fetchMgPdf = async (mode) => {
    try {
      const res = await fetch(`${API}/api/center-accounts/export-mg-payout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: session.token, center,
          from_month: `${year}-${month}`, to_month: `${year}-${month}`,
          format: 'pdf',
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed' }));
        throw new Error(err.detail || 'Failed');
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      if (mode === 'preview') {
        setPreviewBlobUrl(url);
        setPreviewTitle(`MG Report — ${center} · ${year}-${month}`);
      } else {
        const a = document.createElement('a');
        a.href = url;
        a.download = `MG_Report_${center}_${year}-${month}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        toast.success('MG Report downloaded');
      }
    } catch (e) { toast.error(e.message); }
  };

  useEffect(() => {
    // Staff (Admin / Super Admin / Accountant) can pick any center — fetch
    // the full centers list. Franchise Owners are scoped to ownerCenters
    // returned by login.
    const isStaff = !!(session?.is_super_admin || session?.is_admin
      || session?.role_key === 'accountant' || session?.roles?.accounting);
    (async () => {
      if (isStaff) {
        try {
          const res = await fetch(`${API}/api/mgt/centers`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: session.token }),
          });
          const data = await res.json();
          const list = (data.centers || []).map(c => c.code || c).filter(Boolean);
          if (list.length) {
            setCenters(list);
            setCenter(prev => prev || list[0]);
            return;
          }
        } catch { /* fall through */ }
      }
      if (session?.ownerCenters?.length) {
        setCenters(session.ownerCenters);
        setCenter(session.ownerCenters[0]);
      } else if (session?.center) {
        setCenters([session.center]);
        setCenter(session.center);
      }
    })();
  }, [session]);

  const load = useCallback(async () => {
    if (!center) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/owner-reports/monthly-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, center, month: `${year}-${month}` }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed');
      setReport(data);
    } catch (e) {
      toast.error(e.message);
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, [center, year, month, session]);

  useEffect(() => { if (center) load(); }, [center, year, month, load]);
  useEffect(() => { if (center) loadRawFiles(); }, [center, year, month, loadRawFiles]);

  const visible = report?.visibility?.ready;
  const notReadyReason = report?.visibility?.reason || 'Current month in progress. Accounts team has not yet approved visibility.';
  // Staff (Super Admin / Admin / Accounts) can always download / view reports
  // regardless of whether the month has been released to franchise owners.
  // Franchise owners only get downloads after release. This mirrors the
  // server-side gate at /api/center-accounts/generate-* and /api/ledgers/*.
  const canBypassRelease = !!(session?.is_super_admin || session?.is_admin
    || session?.role_key === 'accountant' || session?.roles?.accounting);
  const canDownload = visible || canBypassRelease;

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6" data-testid="owner-reports-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><FileText className="w-6 h-6 text-[#8B0000]" /> Monthly Reports</h1>
          <p className="text-sm text-muted-foreground">PIB · GST · Sales · Expenses — by center & month</p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base">Filters</CardTitle>
          {(session?.is_super_admin || session?.is_admin || session?.role_key === 'accountant' || session?.roles?.accounting) && (
            <div className="flex gap-2">
              <Button
                size="sm"
                className="bg-emerald-700 hover:bg-emerald-800 text-white"
                data-testid="or-release-all-btn"
                onClick={async () => {
                  if (!window.confirm(`Release ${year}-${month} for ALL active centers to franchise owners?`)) return;
                  try {
                    const res = await fetch(`${API}/api/owner-reports/release-all`, {
                      method: 'POST', headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ token: session.token, month: `${year}-${month}`, ready: true }),
                    });
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail || 'Failed');
                    toast.success(`Released ${year}-${month} for ${data.updated} center(s).`);
                    load();
                  } catch (e) { toast.error(e.message); }
                }}
              >Release All for {year}-{month}</Button>
              <Button
                size="sm"
                variant="outline"
                className="border-red-300 text-red-700 hover:bg-red-50"
                data-testid="or-revoke-all-btn"
                onClick={async () => {
                  if (!window.confirm(`Revoke owner access to ${year}-${month} for ALL centers?`)) return;
                  try {
                    const res = await fetch(`${API}/api/owner-reports/release-all`, {
                      method: 'POST', headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ token: session.token, month: `${year}-${month}`, ready: false }),
                    });
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail || 'Failed');
                    toast.success(`Revoked ${year}-${month} across ${data.updated} center(s).`);
                    load();
                  } catch (e) { toast.error(e.message); }
                }}
              >Revoke All</Button>
            </div>
          )}
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Center</label>
              <Select value={center} onValueChange={setCenter}>
                <SelectTrigger data-testid="or-center-select"><SelectValue placeholder="Select center" /></SelectTrigger>
                <SelectContent>
                  {centers.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Year</label>
              <Select value={year} onValueChange={setYear}>
                <SelectTrigger data-testid="or-year-select"><SelectValue /></SelectTrigger>
                <SelectContent>{YEARS.map(y => <SelectItem key={y} value={y}>{y}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Month</label>
              <Select value={month} onValueChange={setMonth}>
                <SelectTrigger data-testid="or-month-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {MONTHS.map(m => (
                    <SelectItem key={m} value={m}>
                      {new Date(`2024-${m}-01`).toLocaleDateString('en-IN', { month: 'long' })}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end">
              <Button onClick={load} disabled={loading || !center} className="w-full bg-[#8B0000] hover:bg-[#6B0000]" data-testid="or-load-btn">
                {loading ? 'Loading…' : 'Load Report'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Visibility gate — only block franchise owners with no release. Staff
          see the admin_bypass banner instead and full data + downloads. */}
      {report && !visible && !canBypassRelease && (
        <Card className="border-amber-300 bg-amber-50 dark:bg-amber-900/10" data-testid="or-gated-banner">
          <CardContent className="p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-700 mt-0.5" />
            <div>
              <p className="font-semibold text-amber-900 dark:text-amber-100">Report not yet available</p>
              <p className="text-sm text-amber-800 dark:text-amber-200">{notReadyReason}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Admin bypass notice — data is shown but owners still blocked */}
      {report?.visibility?.admin_bypass && (
        <Card className="border-sky-300 bg-sky-50 dark:bg-sky-900/10" data-testid="or-admin-bypass-banner">
          <CardContent className="p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-sky-700 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-sky-900 dark:text-sky-100">Admin preview — not yet released to owners</p>
              <p className="text-sm text-sky-800 dark:text-sky-200">
                Accounts team has not flagged this month as ready. Franchise owners will see the "Report not yet available" screen until released.
              </p>
            </div>
            <Button
              size="sm"
              className="bg-green-600 hover:bg-green-700 text-white"
              data-testid="or-release-btn"
              onClick={async () => {
                try {
                  const res = await fetch(`${API}/api/owner-reports/set-visibility`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      token: session.token, center, month: `${year}-${month}`, ready: true,
                      note: `Released by ${session.managerName || 'admin'} on ${new Date().toLocaleString()}`,
                    }),
                  });
                  const data = await res.json();
                  if (!res.ok) throw new Error(data.detail || 'Failed');
                  toast.success(`Released ${center} · ${year}-${month} to franchise owners.`);
                  load();
                } catch (e) { toast.error(e.message); }
              }}
            >Release to Owners</Button>
          </CardContent>
        </Card>
      )}

      {/* Released banner — admin can revoke */}
      {report?.visibility?.flagged_ready && (
        <Card className="border-emerald-300 bg-emerald-50 dark:bg-emerald-900/10" data-testid="or-released-banner">
          <CardContent className="p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-emerald-700 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-emerald-900 dark:text-emerald-100">Released to franchise owners ✓</p>
              <p className="text-sm text-emerald-800 dark:text-emerald-200">
                {report.visibility.note || 'This month is visible to franchise owners.'}
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              className="border-red-300 text-red-700 hover:bg-red-50"
              data-testid="or-revoke-btn"
              onClick={async () => {
                if (!window.confirm('Revoke access so franchise owners can no longer see this month?')) return;
                try {
                  const res = await fetch(`${API}/api/owner-reports/set-visibility`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      token: session.token, center, month: `${year}-${month}`, ready: false,
                      note: `Revoked by ${session.managerName || 'admin'} on ${new Date().toLocaleString()}`,
                    }),
                  });
                  const data = await res.json();
                  if (!res.ok) throw new Error(data.detail || 'Failed');
                  toast.success(`Access revoked for ${center} · ${year}-${month}.`);
                  load();
                } catch (e) { toast.error(e.message); }
              }}
            >Revoke Access</Button>
          </CardContent>
        </Card>
      )}

      {report && visible && !canBypassRelease && null}
      {report && canDownload && (
        <>
          {/* Hero: Download Complete Monthly Bundle */}
          <Card data-testid="or-download-bundle-card" className="border-2 border-rose-300 bg-rose-50/50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-start gap-4">
                  <div className="w-14 h-14 rounded-lg bg-rose-100 flex items-center justify-center flex-shrink-0">
                    <Download className="w-7 h-7 text-rose-700" />
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold text-rose-900">Download Complete Monthly Bundle</h4>
                    <p className="text-sm text-rose-700 mt-1 max-w-xl">
                      One ZIP with everything for {center} · {year}-{month} — PIB, GST, Commission, Bank Statement PDFs + Sales/Expense Excel + Franchise Owner Ledger + any raw uploaded files (Swiggy / Zomato / Bank).
                    </p>
                  </div>
                </div>
                <Button
                  size="lg"
                  className="bg-rose-700 hover:bg-rose-800 text-white"
                  data-testid="or-download-bundle-btn"
                  onClick={async () => {
                    try {
                      const res = await fetch(`${API}/api/franchise-reports/bundle`, {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ token: session.token, center, month: `${year}-${month}` }),
                      });
                      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'Failed'); }
                      const blob = await res.blob();
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url; a.download = `Monthly_Bundle_${center}_${year}-${month}.zip`;
                      document.body.appendChild(a); a.click(); a.remove();
                      URL.revokeObjectURL(url);
                      toast.success('Monthly bundle downloaded');
                    } catch (e) { toast.error(e.message); }
                  }}
                >
                  <Download className="w-4 h-4 mr-2" /> Download Bundle (ZIP)
                </Button>
              </div>
              <p className="text-xs text-rose-700 mt-3">Prefer to preview each report first? Open the collapsible sections below.</p>
            </CardContent>
          </Card>

          {/* Download Reports — PDFs */}
          <CollapsibleSection
            id="or-downloads"
            testId="or-downloads"
            title={<span className="flex items-center gap-2"><Download className="w-4 h-4" /> Download Reports (PDF)</span>}
            description={<>Pre-formatted statements for {center} · {year}-{month}. Click <strong>Preview</strong> to view inline before downloading.</>}
            defaultOpen={true}
          >
            <div className="flex flex-wrap gap-3">
                {[
                  { id: 'pib', label: 'PIB Report', path: 'generate-pib', endpoint: 'center-accounts', color: 'bg-[#8B0000] hover:bg-[#6B0000] text-white' },
                  { id: 'gst', label: 'GST Summary', path: 'generate-gst-summary', endpoint: 'center-accounts', color: 'bg-amber-600 hover:bg-amber-700 text-white' },
                  { id: 'comm', label: 'Commission Summary', path: 'generate-commission-summary', endpoint: 'center-accounts', color: 'bg-emerald-700 hover:bg-emerald-800 text-white' },
                  { id: 'bank', label: 'Bank Statement', path: 'generate-bank-statement', endpoint: 'center-accounts', color: 'bg-sky-700 hover:bg-sky-800 text-white' },
                ].map(r => (
                  <div key={r.id} className="flex flex-col gap-1.5">
                    <Button
                      className={r.color}
                      data-testid={`or-dl-${r.id}`}
                      onClick={() => fetchReportPdf(r, 'download')}
                    >
                      <Download className="w-4 h-4 mr-2" /> {r.label}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-xs h-7"
                      data-testid={`or-preview-${r.id}`}
                      onClick={() => fetchReportPdf(r, 'preview')}
                    >
                      <Eye className="w-3.5 h-3.5 mr-1" /> Preview
                    </Button>
                  </div>
                ))}
                {/* MG Report — uses a different endpoint (accepts from_month/to_month) */}
                <div className="flex flex-col gap-1.5">
                  <Button
                    className="bg-indigo-700 hover:bg-indigo-800 text-white"
                    data-testid="or-dl-mg"
                    onClick={() => fetchMgPdf('download')}
                  >
                    <Download className="w-4 h-4 mr-2" /> MG Report
                  </Button>
                  <Button variant="outline" size="sm" className="text-xs h-7" data-testid="or-preview-mg" onClick={() => fetchMgPdf('preview')}>
                    <Eye className="w-3.5 h-3.5 mr-1" /> Preview
                  </Button>
                </div>
              </div>
          </CollapsibleSection>

          {/* Franchise Owner Ledger — separate from the Email Pack ZIP */}
          <CollapsibleSection
            id="or-owner-ledger-card"
            testId="or-owner-ledger-card"
            className="border-2 border-violet-200 bg-violet-50/30"
            title={<span className="flex items-center gap-2"><FileText className="w-4 h-4 text-violet-700" /> Franchise Owner Ledger</span>}
            description={<>HQ ↔ Franchise running account for {center} · {year}-{month}. Available here separately — not bundled into the Email Pack ZIP.</>}
            defaultOpen={true}
          >
            <div className="flex gap-3 flex-wrap">
                <Button className="bg-violet-700 hover:bg-violet-800 text-white" data-testid="or-owner-ledger-download" onClick={() => fetchOwnerLedgerPdf('download', 'month')}>
                  <Download className="w-4 h-4 mr-2" /> Download PDF
                </Button>
                <Button variant="outline" data-testid="or-owner-ledger-preview" onClick={() => fetchOwnerLedgerPdf('preview', 'month')}>
                  <Eye className="w-4 h-4 mr-2" /> View PDF
                </Button>
                <span className="text-xs text-muted-foreground self-center">Filter: selected month (use the global Year/Month above)</span>
              </div>
          </CollapsibleSection>

          {/* Sales / Expense Excel — month / date-range / single date */}
          <CollapsibleSection
            id="or-sales-expense-excel"
            testId="or-sales-expense-excel"
            className="border-2 border-emerald-200 bg-emerald-50/30"
            title={<span className="flex items-center gap-2"><FileSpreadsheet className="w-4 h-4 text-emerald-700" /> Sales / Expense Excel</span>}
            description="Daily sales + expenses pulled live from the Sales Dashboard. Choose the period below."
            defaultOpen={true}
          >
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <Select value={seMode} onValueChange={setSeMode}>
                  <SelectTrigger className="w-40 h-9" data-testid="se-mode-trigger"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="month">Full Month</SelectItem>
                    <SelectItem value="range">Date Range</SelectItem>
                    <SelectItem value="date">Specific Date</SelectItem>
                  </SelectContent>
                </Select>
                {seMode === 'month' && (
                  <span className="text-sm text-muted-foreground"><Calendar className="inline w-4 h-4 mr-1" />{year}-{month}</span>
                )}
                {seMode === 'range' && (
                  <>
                    <Input type="date" value={seStart} onChange={(e) => setSeStart(e.target.value)} className="w-40 h-9" data-testid="se-start" />
                    <span className="text-xs text-muted-foreground">to</span>
                    <Input type="date" value={seEnd} onChange={(e) => setSeEnd(e.target.value)} className="w-40 h-9" data-testid="se-end" />
                  </>
                )}
                {seMode === 'date' && (
                  <Input type="date" value={seStart} onChange={(e) => setSeStart(e.target.value)} className="w-40 h-9" data-testid="se-date" />
                )}
              </div>
              <div className="flex gap-2 flex-wrap">
                <Button className="bg-emerald-700 hover:bg-emerald-800 text-white" data-testid="se-download" onClick={() => fetchSalesExpenseExcel('download')}>
                  <Download className="w-4 h-4 mr-2" /> Download Excel
                </Button>
                <Button variant="outline" data-testid="se-preview" onClick={() => fetchSalesExpenseExcel('preview')}>
                  <Eye className="w-4 h-4 mr-2" /> Open Excel
                </Button>
              </div>
            </div>
          </CollapsibleSection>

          {/* Raw Uploaded Files — Swiggy / Zomato / Bank Statement etc. */}
          <CollapsibleSection
            id="or-raw-files-card"
            testId="or-raw-files-card"
            className="border-2 border-sky-200 bg-sky-50/30"
            title={<span className="flex items-center gap-2"><FileBox className="w-4 h-4 text-sky-700" /> Raw Uploaded Files — {year}-{month}</span>}
            description="Original Excel/PDF files uploaded for commission upload + bank reconciliation. View-only."
            defaultOpen={false}
            headerExtra={rawFiles.length > 0 && <Badge variant="secondary">{rawFiles.length} file{rawFiles.length === 1 ? '' : 's'}</Badge>}
          >
            {rawFilesLoading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
              ) : rawFiles.length === 0 ? (
                <p className="text-sm text-muted-foreground italic">No raw files uploaded yet for this month. They will appear here automatically after Commission / Bank Reconciliation uploads.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-sky-100/60 text-left">
                        <th className="p-2">Type</th>
                        <th className="p-2">Filename</th>
                        <th className="p-2">Size</th>
                        <th className="p-2">Uploaded</th>
                        <th className="p-2">By</th>
                        <th className="p-2 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rawFiles.map((f) => (
                        <tr key={f.raw_id} className="border-t hover:bg-white">
                          <td className="p-2">
                            <Badge variant="secondary" className="capitalize">
                              {f.kind === 'commission' ? (f.platform || 'commission') : f.kind?.replace('_', ' ')}
                            </Badge>
                          </td>
                          <td className="p-2 font-medium">{f.original_filename}</td>
                          <td className="p-2 text-muted-foreground">{f.size_kb} KB</td>
                          <td className="p-2 text-xs text-muted-foreground">{(f.uploaded_at || '').slice(0, 10)}</td>
                          <td className="p-2 text-xs text-muted-foreground">{f.uploaded_by}</td>
                          <td className="p-2 text-right">
                            <Button size="sm" variant="outline" data-testid={`raw-download-${f.raw_id}`}
                                    onClick={() => downloadRawFile(f.raw_id, f.original_filename)}>
                              <Download className="w-3.5 h-3.5 mr-1" /> Download
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
          </CollapsibleSection>

          {/* Top row — key metrics */}
          <div className={`grid grid-cols-2 ${report.country === 'Australia' ? 'md:grid-cols-6' : 'md:grid-cols-6'} gap-4`} data-testid="or-kpi-cards">
            <Card><CardContent className="p-4">
              <p className="text-xs text-muted-foreground">Sales</p>
              <p className="text-xl font-bold">{fmtINR(report.sales.total)}</p>
              <p className="text-[10px] text-muted-foreground mt-1">{report.sales.days} day(s)</p>
            </CardContent></Card>
            <Card><CardContent className="p-4">
              <p className="text-xs text-muted-foreground">Expenses</p>
              <p className="text-xl font-bold">{fmtINR(report.expenses.total)}</p>
              <p className="text-[10px] text-muted-foreground mt-1">{report.expenses.rows} entries</p>
            </CardContent></Card>
            <Card><CardContent className="p-4">
              <p className="text-xs text-muted-foreground">GST ({report.gst.rate_pct}% of eligible)</p>
              <p className="text-xl font-bold">{fmtINR(report.gst.gst_amount)}</p>
              <div className="text-[10px] text-muted-foreground mt-1">Base: {fmtINR(report.gst.eligible_base)} · {report.gst.liability_paid ? <Badge className="bg-green-100 text-green-700 border-green-300 ml-1">Paid</Badge> : <Badge className="bg-amber-100 text-amber-700 border-amber-300 ml-1">Payable</Badge>}</div>
            </CardContent></Card>
            <Card data-testid="or-net-revenue-card"><CardContent className="p-4">
              <p className="text-xs text-muted-foreground">Net Revenue</p>
              <p className={`text-xl font-bold ${(report.net_revenue ?? report.pnl) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {(report.net_revenue ?? report.pnl) >= 0 ? <TrendingUp className="inline w-4 h-4 mr-1" /> : <TrendingDown className="inline w-4 h-4 mr-1" />}
                {fmtINR(report.net_revenue ?? report.pnl)}
              </p>
              <p className="text-[10px] text-muted-foreground mt-1">Sales − Commissions (management view)</p>
            </CardContent></Card>
            <Card data-testid="or-eligible-rev-share-card" className="bg-sky-50"><CardContent className="p-4">
              <p className="text-xs text-sky-700">Revenue Share Base</p>
              <p className={`text-xl font-bold ${(report.revenue_share_base ?? report.eligible_rev_share_base ?? 0) >= 0 ? 'text-sky-900' : 'text-red-600'}`}>
                {fmtINR(report.revenue_share_base ?? report.eligible_rev_share_base ?? 0)}
              </p>
              <p className="text-[10px] text-sky-700 mt-1">Sales − Commissions − GST (for 80/20 split)</p>
            </CardContent></Card>
            <Card data-testid="or-net-pl-card" className="bg-rose-50"><CardContent className="p-4">
              <p className="text-xs text-rose-700">Profit / Loss</p>
              <p className={`text-xl font-bold ${(report.profit_loss ?? report.net_pl ?? 0) >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                {(report.profit_loss ?? report.net_pl ?? 0) >= 0 ? <TrendingUp className="inline w-4 h-4 mr-1" /> : <TrendingDown className="inline w-4 h-4 mr-1" />}
                {fmtINR(report.profit_loss ?? report.net_pl ?? 0)}
              </p>
              <p className="text-[10px] text-rose-700 mt-1">Sales − Expenses − Commissions (GST excluded)</p>
            </CardContent></Card>
            {report.country === 'Australia' && (
              <Card data-testid="or-profitability-card"><CardContent className="p-4">
                <p className="text-xs text-emerald-700">Profitability</p>
                <p className={`text-xl font-bold ${(report.profitability ?? 0) >= 0 ? 'text-emerald-700' : 'text-red-600'}`}>
                  {fmtINR(report.profitability ?? 0)}
                </p>
                <p className="text-[10px] text-emerald-700 mt-1">Net Revenue − Expenses · 80/20 base</p>
              </CardContent></Card>
            )}
          </div>

          {/* Sales breakdown */}
          <CollapsibleSection
            id="or-sales-breakdown"
            title="Sales Breakdown"
            description="Cash · Online · Swiggy · Zomato · DoorDash · Card"
            defaultOpen={false}
          >
              <div className="grid grid-cols-2 md:grid-cols-6 gap-2 text-sm">
                {[['Cash', report.sales.cash], ['Online', report.sales.online], ['Swiggy', report.sales.swiggy], ['Zomato', report.sales.zomato], ['DoorDash', report.sales.doordash], ['Card', report.sales.card]].map(([k, v]) => (
                  <div key={k} className="rounded border px-3 py-2">
                    <p className="text-xs text-muted-foreground">{k}</p>
                    <p className="font-semibold">{fmtINR(v)}</p>
                  </div>
                ))}
              </div>
          </CollapsibleSection>

          {/* Commissions */}
          {report.commissions?.by_platform?.length > 0 && (
            <CollapsibleSection
              id="or-platform-commissions"
              title="Platform Commissions"
              description="Swiggy · Zomato · Card · PhonePe deductions"
              defaultOpen={false}
            >
                <table className="w-full text-sm">
                  <thead className="bg-muted">
                    <tr>
                      <th className="px-3 py-2 text-left">Platform</th>
                      <th className="px-3 py-2 text-right">Gross</th>
                      <th className="px-3 py-2 text-right">Commission</th>
                      <th className="px-3 py-2 text-right">Net Payout</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.commissions.by_platform.map((p, i) => (
                      <tr key={i} className="border-b">
                        <td className="px-3 py-2 font-medium capitalize">{p.platform}</td>
                        <td className="px-3 py-2 text-right font-mono">{fmtINR(p.gross)}</td>
                        <td className="px-3 py-2 text-right font-mono text-red-600">-{fmtINR(p.commission)}</td>
                        <td className="px-3 py-2 text-right font-mono font-semibold">{fmtINR(p.net_payout)}</td>
                      </tr>
                    ))}
                    <tr className="bg-muted/50 font-semibold" data-testid="or-commissions-total">
                      <td className="px-3 py-2">Total</td>
                      <td className="px-3 py-2 text-right font-mono">{fmtINR(report.commissions.by_platform.reduce((s, p) => s + (p.gross || 0), 0))}</td>
                      <td className="px-3 py-2 text-right font-mono text-red-700">-{fmtINR(report.commissions.total)}</td>
                      <td className="px-3 py-2 text-right font-mono">{fmtINR(report.commissions.by_platform.reduce((s, p) => s + (p.net_payout || 0), 0))}</td>
                    </tr>
                  </tbody>
                </table>
            </CollapsibleSection>
          )}

          {/* Expense breakdown */}
          {report.expenses?.by_category?.length > 0 && (
            <CollapsibleSection
              id="or-expense-breakdown"
              title="Expense Breakdown"
              description="By category"
              defaultOpen={false}
            >
                <table className="w-full text-sm">
                  <thead className="bg-muted">
                    <tr><th className="px-3 py-2 text-left">Category</th><th className="px-3 py-2 text-right">Amount</th><th className="px-3 py-2 text-right">% of Total</th></tr>
                  </thead>
                  <tbody>
                    {report.expenses.by_category.map((e, i) => (
                      <tr key={i} className="border-b">
                        <td className="px-3 py-2">{e.category}</td>
                        <td className="px-3 py-2 text-right font-mono">{fmtINR(e.amount)}</td>
                        <td className="px-3 py-2 text-right text-muted-foreground">{report.expenses.total ? ((e.amount / report.expenses.total) * 100).toFixed(1) : 0}%</td>
                      </tr>
                    ))}
                    <tr className="bg-muted/50 font-semibold border-t-2 border-slate-300" data-testid="or-expense-total">
                      <td className="px-3 py-2">TOTAL</td>
                      <td className="px-3 py-2 text-right font-mono">{fmtINR(report.expenses.total)}</td>
                      <td className="px-3 py-2 text-right text-muted-foreground">100.0%</td>
                    </tr>
                  </tbody>
                </table>
            </CollapsibleSection>
          )}
        </>
      )}

      {/* Ledgers Section — same UI as Center Accounts; lives OUTSIDE the
          {report && ...} block so it shows as soon as a center is selected,
          even if the monthly report fails to load. Hidden for franchise owners
          when the month hasn't been released (server returns 403 anyway, but
          UX is cleaner without dead buttons). Staff (SA / Admin / Accounts)
          always see the section. */}
      {center && (canDownload || canBypassRelease) && (
        <LedgersTab
          session={session}
          selectedCenter={center}
          country={report?.country}
          readOnly={!canBypassRelease}
        />
      )}

      {/* Financial Insights — collapsible analytics & AI summary */}
      {center && (canDownload || canBypassRelease) && (
        <CollapsibleSection
          id="financial-insights"
          title="Financial Insights"
          description="Analytics, ratios, trends + AI executive summary. Excel / CSV download."
          defaultOpen={false}
          testId="or-financial-insights"
        >
          <FinancialInsightsTab centersList={[{ code: center, name: center }]} />
        </CollapsibleSection>
      )}

      {/* Inline Preview modal */}
      <Dialog open={!!previewBlobUrl} onOpenChange={(o) => { if (!o) { if (previewBlobUrl) URL.revokeObjectURL(previewBlobUrl); setPreviewBlobUrl(null); } }}>
        <DialogContent className="max-w-5xl h-[85vh] p-0 flex flex-col" data-testid="or-preview-modal">
          <DialogHeader className="px-5 py-3 border-b border-slate-200">
            <DialogTitle className="text-base">{previewTitle || 'Preview'}</DialogTitle>
            <DialogDescription className="text-xs">View the report inline before downloading.</DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-hidden">
            {previewBlobUrl && (
              <iframe title="report-preview" src={previewBlobUrl} className="w-full h-full" data-testid="or-preview-frame" />
            )}
          </div>
          <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-slate-200">
            <Button variant="outline" size="sm" onClick={() => { if (previewBlobUrl) URL.revokeObjectURL(previewBlobUrl); setPreviewBlobUrl(null); }} data-testid="or-preview-close">Close</Button>
            {previewBlobUrl && (
              <a href={previewBlobUrl} download={`${previewTitle.replace(/[^a-z0-9]+/gi, '_')}.pdf`} data-testid="or-preview-download">
                <Button size="sm" className="bg-[#8B0000] hover:bg-[#6B0000] text-white">
                  <Download className="w-4 h-4 mr-1" /> Download PDF
                </Button>
              </a>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
