import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { toast } from 'sonner';
import {
  BookOpen, FileText, FileSpreadsheet, Archive, Calendar, Loader2,
  Send, Eye, EyeOff, Info, Download, AlertTriangle
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const LEDGER_CATALOG = [
  { key: 'pnl', label: 'General Ledger (P&L)', desc: 'Sales − Expenses − Commissions = PBT', color: 'slate', group: 'financial' },
  { key: 'sales', label: 'Sales Register', desc: 'Daily sales with platform & GST breakdown', color: 'emerald', group: 'financial' },
  { key: 'expenses', label: 'Expense / Purchase Register', desc: 'All expenses with category & payment mode', color: 'rose', group: 'financial' },
  { key: 'cash', label: 'Cash Ledger', desc: 'Daily cash movement (opening → closing)', color: 'amber', group: 'financial' },
  { key: 'bank', label: 'Bank Ledger', desc: 'Deposits, withdrawals, running bank balance', color: 'blue', group: 'financial' },
  { key: 'gst', label: 'GST Summary', desc: 'Output GST vs commissions (GSTR-ready)', color: 'orange', group: 'financial' },
  { key: 'owner', label: 'Franchise Running Account', desc: 'Running current account with HQ', color: 'fuchsia', group: 'franchise' },
  { key: 'loans', label: 'Settlement Ledger (Loans & Inter-Center)', desc: 'Inter-center + HQ loans with balances', color: 'indigo', group: 'franchise' },
  { key: 'commission', label: 'Commission Ledger', desc: 'Swiggy / Zomato / Card / UPI deductions', color: 'purple', group: 'adjustment' },
  { key: 'payroll', label: 'Payroll Register', desc: 'Employee-wise salary + bank details', color: 'teal', group: 'adjustment' },
];

const LEDGER_GROUPS = [
  { key: 'financial', label: 'Financial Ledgers', accent: 'border-blue-500' },
  { key: 'franchise', label: 'Franchise Ledgers', accent: 'border-fuchsia-500' },
  { key: 'adjustment', label: 'Adjustment Ledgers', accent: 'border-amber-500' },
];

const colorClasses = (c) => ({
  emerald: 'border-emerald-200 bg-emerald-50 hover:border-emerald-400',
  rose: 'border-rose-200 bg-rose-50 hover:border-rose-400',
  amber: 'border-amber-200 bg-amber-50 hover:border-amber-400',
  blue: 'border-blue-200 bg-blue-50 hover:border-blue-400',
  purple: 'border-purple-200 bg-purple-50 hover:border-purple-400',
  indigo: 'border-indigo-200 bg-indigo-50 hover:border-indigo-400',
  teal: 'border-teal-200 bg-teal-50 hover:border-teal-400',
  orange: 'border-orange-200 bg-orange-50 hover:border-orange-400',
  slate: 'border-slate-200 bg-slate-50 hover:border-slate-400',
  fuchsia: 'border-fuchsia-200 bg-fuchsia-50 hover:border-fuchsia-400',
}[c] || 'border-slate-200 bg-slate-50 hover:border-slate-400');

export default function LedgersTab({ session, selectedCenter, country, readOnly = false }) {
  const token = session?.token;
  const [periodType, setPeriodType] = useState('month');
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  });
  const [fyStartYear, setFyStartYear] = useState(() => {
    const d = new Date();
    return d.getMonth() + 1 >= 4 ? d.getFullYear() : d.getFullYear() - 1;
  });
  const [busy, setBusy] = useState(null); // ledger key currently downloading
  const [bundleBusy, setBundleBusy] = useState(false);
  const [releaseBusy, setReleaseBusy] = useState(false);
  const [ownerReleasedStatus, setOwnerReleasedStatus] = useState(null);

  const periodLabel = useMemo(() => {
    if (periodType === 'month') return selectedMonth;
    return `FY${fyStartYear}-${String((fyStartYear + 1) % 100).padStart(2, '0')}`;
  }, [periodType, selectedMonth, fyStartYear]);

  const buildBody = useCallback(() => {
    const body = { token, center: selectedCenter, period_type: periodType };
    if (periodType === 'month') body.month = selectedMonth;
    else body.fy_start_year = parseInt(fyStartYear, 10);
    return body;
  }, [token, selectedCenter, periodType, selectedMonth, fyStartYear]);

  const [previewBlobUrl, setPreviewBlobUrl] = useState(null);
  const [previewTitle, setPreviewTitle] = useState("");

  const previewLedger = async (ledgerKey) => {
    if (!selectedCenter) { toast.error('Select a center'); return; }
    setBusy(`${ledgerKey}-preview`);
    try {
      const body = { ...buildBody(), fmt: 'pdf' };
      const res = await fetch(`${API}/api/ledgers/${ledgerKey}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Preview failed' }));
        throw new Error(err.detail || 'Preview failed');
      }
      const blob = await res.blob();
      setPreviewBlobUrl(URL.createObjectURL(blob));
      setPreviewTitle(`${ledgerKey.toUpperCase()} — ${selectedCenter} · ${periodLabel}`);
    } catch (e) {
      toast.error(e.message || 'Preview failed');
    } finally {
      setBusy(null);
    }
  };

  const downloadLedger = async (ledgerKey, fmt) => {
    if (!selectedCenter) { toast.error('Select a center'); return; }
    setBusy(`${ledgerKey}-${fmt}`);
    try {
      const body = { ...buildBody(), fmt };
      const res = await fetch(`${API}/api/ledgers/${ledgerKey}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Download failed' }));
        throw new Error(err.detail || 'Download failed');
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${ledgerKey}_${selectedCenter}_${periodLabel}.${fmt === 'excel' ? 'xlsx' : 'pdf'}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`${ledgerKey.toUpperCase()} ${fmt.toUpperCase()} downloaded`);
    } catch (e) {
      toast.error(e.message || 'Failed');
    } finally {
      setBusy(null);
    }
  };

  const downloadBundle = async () => {
    if (!selectedCenter) { toast.error('Select a center'); return; }
    setBundleBusy(true);
    try {
      const body = { ...buildBody(), include_bills: true };
      const res = await fetch(`${API}/api/ledgers/bundle`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Bundle failed' }));
        throw new Error(err.detail || 'Bundle failed');
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `CA_Bundle_${selectedCenter}_${periodLabel}.zip`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('CA Bundle ZIP downloaded');
    } catch (e) {
      toast.error(e.message || 'Failed');
    } finally {
      setBundleBusy(false);
    }
  };

  const fetchOwnerReleaseStatus = useCallback(async () => {
    if (!token || !selectedCenter || periodType !== 'month') { setOwnerReleasedStatus(null); return; }
    try {
      const res = await fetch(`${API}/api/ledgers/owner/visibility`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, center: selectedCenter, month: selectedMonth })
      });
      const data = await res.json();
      setOwnerReleasedStatus(data.visible ? 'released' : 'hidden');
    } catch (_) {
      setOwnerReleasedStatus(null);
    }
  }, [token, selectedCenter, periodType, selectedMonth]);

  useEffect(() => { fetchOwnerReleaseStatus(); }, [fetchOwnerReleaseStatus]);

  const toggleOwnerRelease = async () => {
    if (periodType !== 'month') { toast.error('Owner Ledger release works per month'); return; }
    setReleaseBusy(true);
    try {
      const action = ownerReleasedStatus === 'released' ? 'hide' : 'release';
      const res = await fetch(`${API}/api/ledgers/owner/release`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, center: selectedCenter, month: selectedMonth, action })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed' }));
        throw new Error(err.detail || 'Failed');
      }
      toast.success(action === 'release' ? 'Owner Ledger released' : 'Owner Ledger hidden');
      fetchOwnerReleaseStatus();
    } catch (e) {
      toast.error(e.message || 'Failed');
    } finally {
      setReleaseBusy(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="ledgers-tab">
      {/* Header / Period selector */}
      <Card className="border-l-4 border-l-indigo-500">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl">
            <BookOpen className="w-5 h-5 text-indigo-600" />
            {readOnly ? 'Ledgers — Released by Accounts' : 'Ledgers — CA-Ready Books of Accounts'}
          </CardTitle>
          <CardDescription>
            {readOnly
              ? `View-only access to ledgers for ${selectedCenter || 'your center'}. Available only after the Accounts team releases the month.`
              : `Indian accounting books for ${selectedCenter || 'selected center'}. Super Admin / Admin / Accounts access only.`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-4 items-end">
            <div>
              <Label className="text-xs">Period Type</Label>
              <Select value={periodType} onValueChange={setPeriodType}>
                <SelectTrigger data-testid="ledger-period-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="month">Monthly</SelectItem>
                  <SelectItem value="fy">Financial Year (Apr–Mar)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {periodType === 'month' ? (
              <div>
                <Label className="text-xs">Month</Label>
                <Input type="month" value={selectedMonth} onChange={(e) => setSelectedMonth(e.target.value)} data-testid="ledger-month" />
              </div>
            ) : (
              <div>
                <Label className="text-xs">Financial Year Start</Label>
                <Select value={String(fyStartYear)} onValueChange={(v) => setFyStartYear(parseInt(v, 10))}>
                  <SelectTrigger data-testid="ledger-fy"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {[...Array(6)].map((_, i) => {
                      const y = new Date().getFullYear() - 2 + i;
                      return <SelectItem key={y} value={String(y)}>FY{y}-{String((y + 1) % 100).padStart(2, '0')}</SelectItem>;
                    })}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div>
              <Button
                onClick={downloadBundle}
                disabled={bundleBusy || !selectedCenter || readOnly}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white"
                data-testid="ledger-bundle-btn"
                style={readOnly ? { display: 'none' } : {}}
              >
                {bundleBusy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Archive className="w-4 h-4 mr-2" />}
                Download CA Bundle (ZIP)
              </Button>
              {!readOnly && <p className="text-[10px] text-slate-500 mt-1">All ledgers + Excel + PDF + Bills</p>}
              {readOnly && (
                <div className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-md p-2">
                  <strong>View Only.</strong> Ledgers visible only after Accounts releases this month.
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Info banner */}
      {!readOnly && (
      <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm">
        <Info className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
        <div className="text-amber-800">
          <strong>For your CA:</strong> The CA Bundle ZIP includes all ledgers as both PDF (printable) and Excel (editable), plus every bill attachment organized by date, Monthly P&L, Bank/Commission reconciliations, Payroll, and a GST summary.
          Output GST is computed at 5% on food sales (inclusive). <strong>Input GST (ITC) from vendor bills is not auto-tagged</strong> — please reconcile with your CA. Fixed Asset register not maintained in app.
        </div>
      </div>
      )}
      {readOnly && ownerReleasedStatus === 'hidden' && periodType === 'month' && (
        <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm" data-testid="ledger-not-released-banner">
          <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
          <div className="text-amber-800">
            <strong>Not yet released by Accounts.</strong> The selected month has not been flagged as ready by the Accounts team.
            Ledger downloads will return "not available" until the month is released. Please check back later or contact your CA.
          </div>
        </div>
      )}

      {/* Ledger cards — grouped into 3 sections per Center Accounts spec */}
      {LEDGER_GROUPS.map((g) => {
        const items = LEDGER_CATALOG.filter((l) => l.group === g.key);
        if (items.length === 0) return null;
        return (
          <div key={g.key} className="space-y-2" data-testid={`ledger-group-${g.key}`}>
            <Card className={`border-l-4 ${g.accent}`}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{g.label}</CardTitle>
              </CardHeader>
            </Card>
            <div className="grid md:grid-cols-2 gap-4">
              {items.map((l) => (
                <Card key={l.key} className={`border-2 ${colorClasses(l.color)} transition-all`} data-testid={`ledger-card-${l.key}`}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center justify-between">
                      <span>{l.label}</span>
                      {l.key === 'owner' && ownerReleasedStatus === 'released' && (
                        <Badge className="bg-emerald-100 text-emerald-800">Released to Owner</Badge>
                      )}
                      {l.key === 'owner' && ownerReleasedStatus === 'hidden' && (
                        <Badge className="bg-slate-100 text-slate-700">Not released</Badge>
                      )}
                    </CardTitle>
                    <CardDescription className="text-xs">{l.desc}</CardDescription>
                  </CardHeader>
                  <CardContent className="pt-2">
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" variant="outline" onClick={() => previewLedger(l.key)} disabled={busy === `${l.key}-preview`} data-testid={`ledger-${l.key}-preview`}>
                        {busy === `${l.key}-preview` ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> : <Eye className="w-3.5 h-3.5 mr-1" />}
                        Preview
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => downloadLedger(l.key, 'pdf')} disabled={busy === `${l.key}-pdf`} data-testid={`ledger-${l.key}-pdf`}>
                        {busy === `${l.key}-pdf` ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> : <FileText className="w-3.5 h-3.5 mr-1" />}
                        PDF
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => downloadLedger(l.key, 'excel')} disabled={busy === `${l.key}-excel`} data-testid={`ledger-${l.key}-excel`}>
                        {busy === `${l.key}-excel` ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> : <FileSpreadsheet className="w-3.5 h-3.5 mr-1" />}
                        Excel
                      </Button>
                      {l.key === 'owner' && periodType === 'month' && !readOnly && (
                        <Button
                          size="sm"
                          onClick={toggleOwnerRelease}
                          disabled={releaseBusy}
                          className={ownerReleasedStatus === 'released' ? 'bg-slate-600 hover:bg-slate-700 text-white' : 'bg-fuchsia-600 hover:bg-fuchsia-700 text-white'}
                          data-testid="ledger-owner-release"
                        >
                          {releaseBusy ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> :
                            ownerReleasedStatus === 'released' ? <EyeOff className="w-3.5 h-3.5 mr-1" /> : <Send className="w-3.5 h-3.5 mr-1" />}
                          {ownerReleasedStatus === 'released' ? 'Hide from Owner' : 'Send to Owner'}
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        );
      })}

      {/* CA Bundle contents */}
      {!readOnly && (
      <Card className="border-dashed border-2 border-indigo-200">
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Archive className="w-4 h-4 text-indigo-600" />
            CA Bundle ZIP — What's included
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="text-xs text-slate-700 space-y-1">
            <li>📁 <strong>01_PDFs/</strong> — all 10 ledgers as printable PDFs</li>
            <li>📁 <strong>02_Excel/</strong> — same 10 ledgers as editable .xlsx workbooks</li>
            <li>📁 <strong>03_Bills/</strong> — every expense attachment for the period, organized by date</li>
            <li>📄 <strong>00_README.txt</strong> — notes for CA on GST basis, ITC handling, payroll</li>
          </ul>
        </CardContent>
      </Card>
      )}

      {/* Inline Preview modal */}
      <Dialog open={!!previewBlobUrl} onOpenChange={(o) => { if (!o) { if (previewBlobUrl) URL.revokeObjectURL(previewBlobUrl); setPreviewBlobUrl(null); } }}>
        <DialogContent className="max-w-5xl h-[85vh] p-0 flex flex-col" data-testid="ledger-preview-modal">
          <DialogHeader className="px-5 py-3 border-b border-slate-200">
            <DialogTitle className="text-base">{previewTitle || "Preview"}</DialogTitle>
            <DialogDescription className="text-xs">View the ledger before downloading.</DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-hidden">
            {previewBlobUrl && (
              <iframe title="ledger-preview" src={previewBlobUrl} className="w-full h-full" data-testid="ledger-preview-frame" />
            )}
          </div>
          <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-slate-200">
            <Button variant="outline" size="sm" onClick={() => { if (previewBlobUrl) URL.revokeObjectURL(previewBlobUrl); setPreviewBlobUrl(null); }} data-testid="ledger-preview-close">Close</Button>
            {previewBlobUrl && (
              <a href={previewBlobUrl} download={`${previewTitle.replace(/[^a-z0-9]+/gi, '_')}.pdf`} data-testid="ledger-preview-download">
                <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700 text-white">
                  <FileText className="w-4 h-4 mr-1" /> Download PDF
                </Button>
              </a>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
