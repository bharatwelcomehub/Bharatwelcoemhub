import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/App';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { FileText, AlertCircle, Download, Eye, TrendingUp, TrendingDown } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

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

  const visible = report?.visibility?.ready;
  const notReadyReason = report?.visibility?.reason || 'Current month in progress. Accounts team has not yet approved visibility.';

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

      {/* Visibility gate */}
      {report && !visible && (
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

      {report && visible && (
        <>
          {/* Download Reports — PDFs */}
          <Card data-testid="or-downloads">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2"><Download className="w-4 h-4" /> Download Reports (PDF)</CardTitle>
              <CardDescription>Pre-formatted statements for {center} · {year}-{month}. Click <strong>Preview</strong> to view inline before downloading.</CardDescription>
            </CardHeader>
            <CardContent>
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
            </CardContent>
          </Card>

          {/* Top row — key metrics */}
          <div className={`grid grid-cols-2 ${report.country === 'Australia' ? 'md:grid-cols-5' : 'md:grid-cols-4'} gap-4`} data-testid="or-kpi-cards">
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
              <p className="text-[10px] text-muted-foreground mt-1">Base: {fmtINR(report.gst.eligible_base)} · {report.gst.liability_paid ? <Badge className="bg-green-100 text-green-700 border-green-300 ml-1">Paid</Badge> : <Badge className="bg-amber-100 text-amber-700 border-amber-300 ml-1">Payable</Badge>}</p>
            </CardContent></Card>
            <Card><CardContent className="p-4">
              <p className="text-xs text-muted-foreground">{report.country === 'Australia' ? 'Net Revenue' : 'Net P/L'}</p>
              <p className={`text-xl font-bold ${report.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {report.pnl >= 0 ? <TrendingUp className="inline w-4 h-4 mr-1" /> : <TrendingDown className="inline w-4 h-4 mr-1" />}
                {fmtINR(report.pnl)}
              </p>
              <p className="text-[10px] text-muted-foreground mt-1">Sales − Comm − GST</p>
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
          <Card>
            <CardHeader><CardTitle className="text-base">Sales Breakdown</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-6 gap-2 text-sm">
                {[['Cash', report.sales.cash], ['Online', report.sales.online], ['Swiggy', report.sales.swiggy], ['Zomato', report.sales.zomato], ['DoorDash', report.sales.doordash], ['Card', report.sales.card]].map(([k, v]) => (
                  <div key={k} className="rounded border px-3 py-2">
                    <p className="text-xs text-muted-foreground">{k}</p>
                    <p className="font-semibold">{fmtINR(v)}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Commissions */}
          {report.commissions?.by_platform?.length > 0 && (
            <Card>
              <CardHeader><CardTitle className="text-base">Platform Commissions</CardTitle><CardDescription>Swiggy · Zomato · Card · PhonePe deductions</CardDescription></CardHeader>
              <CardContent>
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
                    <tr className="bg-muted/50 font-semibold">
                      <td className="px-3 py-2">Total</td>
                      <td></td>
                      <td className="px-3 py-2 text-right font-mono text-red-700">-{fmtINR(report.commissions.total)}</td>
                      <td></td>
                    </tr>
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}

          {/* Expense breakdown */}
          {report.expenses?.by_category?.length > 0 && (
            <Card>
              <CardHeader><CardTitle className="text-base">Expense Breakdown</CardTitle></CardHeader>
              <CardContent>
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
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </>
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
