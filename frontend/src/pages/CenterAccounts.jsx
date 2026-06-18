import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@/App';
import { WCOverviewGrid } from '@/components/WCOverviewGrid';
import { PnLRevenueShareOverview, RevenueShareProjection } from '@/components/PnLRevenueShareViews';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { 
  Building2, DollarSign, TrendingUp, TrendingDown, FileText, Upload, 
  Download, Calculator, Receipt, Wallet, CreditCard, ShoppingBag,
  Link, Unlink, RefreshCw, Loader2, ChevronRight, PieChart,
  IndianRupee, AlertCircle, CheckCircle, FileSpreadsheet, Trash2, Pencil,
  Check, X, Shield, Save, Plus, BookOpen, Eye, Mail, FileBox, Activity, HeartPulse, Archive
} from 'lucide-react';
import FinancialHealth from '@/pages/FinancialHealth';

import LedgersTab from '@/components/LedgersTab';
import FinancialInsightsTab from '@/components/FinancialInsightsTab';
import ExpenseAdjustmentsTab from '@/components/ExpenseAdjustmentsTab';

const API = process.env.REACT_APP_BACKEND_URL;

const PLATFORMS = {
  india: [
    { value: 'swiggy', label: 'Swiggy', color: 'bg-orange-100 text-orange-800' },
    { value: 'zomato', label: 'Zomato', color: 'bg-red-100 text-red-800' },
    { value: 'phonepe', label: 'PhonePe', color: 'bg-purple-100 text-purple-800' },
    { value: 'cards', label: 'Cards', color: 'bg-blue-100 text-blue-800' }
  ],
  australia: [
    { value: 'doordash', label: 'DoorDash', color: 'bg-red-100 text-red-800' },
    { value: 'cards', label: 'Cards', color: 'bg-blue-100 text-blue-800' }
  ]
};

const ALL_PLATFORMS = [
  { value: 'swiggy', label: 'Swiggy', color: 'bg-orange-100 text-orange-800' },
  { value: 'zomato', label: 'Zomato', color: 'bg-red-100 text-red-800' },
  { value: 'doordash', label: 'DoorDash', color: 'bg-red-100 text-red-800' },
  { value: 'phonepe', label: 'PhonePe', color: 'bg-purple-100 text-purple-800' },
  { value: 'cards', label: 'Cards', color: 'bg-blue-100 text-blue-800' }
];

const formatCurrency = (value, country) => {
  const symbol = country === 'Australia' ? 'AUD ' : 'Rs. ';
  return `${symbol}${(value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const formatPercent = (value) => `${(value || 0).toFixed(1)}%`;

// Country-aware legal entity name for share / payout labels.
//   India     → "Manaswini Foods Pvt Ltd"
//   Australia → "Purnabramha LLC Pty Ltd"
const entityName = (country) =>
  country === 'Australia' ? 'Purnabramha LLC Pty Ltd' : 'Manaswini Foods Pvt Ltd';

// ── Payout Release Status Banner (Feb-2026 directive) ──────────────────
// Informational only — does NOT change any calculations or payout amounts.
// Auto-derived from WC Protection Mode + manual override stored in
// center_settings. Super Admin / Accounts can change via the dropdown.
function PayoutStatusBanner({ status, isAdmin, onChange }) {
  if (!status) return null;
  const tone = status.color === 'red'
    ? { border: 'border-rose-400', bg: 'bg-rose-50', text: 'text-rose-900', strip: 'bg-rose-500', icon: '🔴' }
    : status.color === 'amber'
    ? { border: 'border-amber-400', bg: 'bg-amber-50', text: 'text-amber-900', strip: 'bg-amber-500', icon: '🟠' }
    : { border: 'border-emerald-400', bg: 'bg-emerald-50', text: 'text-emerald-900', strip: 'bg-emerald-500', icon: '🟢' };
  return (
    <div className={`mb-6 flex items-stretch rounded-lg border-2 ${tone.border} ${tone.bg} shadow-sm overflow-hidden`} data-testid="payout-release-banner">
      <div className={`w-1.5 ${tone.strip}`} />
      <div className="flex-1 p-4 flex items-start justify-between gap-4">
        <div className="flex-1">
          <p className={`font-bold text-base ${tone.text} flex items-center gap-2`} data-testid="payout-release-label">
            <span>{tone.icon}</span>
            <span>Payout Status: {status.label}</span>
            {status.reason && (
              <span className="text-xs font-normal opacity-75 italic">({status.reason})</span>
            )}
          </p>
          <p className={`text-sm mt-1 ${tone.text} opacity-80`}>{status.narrative}</p>
        </div>
        {isAdmin && (
          <div className="flex-shrink-0">
            <label className="text-[10px] uppercase tracking-wide font-semibold text-slate-600 block mb-1">Admin Override</label>
            <select
              defaultValue={status.source === 'manual' ? status.status : 'auto'}
              className="text-xs border border-slate-300 rounded px-2 py-1 bg-white"
              onChange={(e) => onChange(e.target.value)}
              data-testid="payout-release-select"
            >
              <option value="auto">Auto (WC-driven)</option>
              <option value="eligible">🟢 Eligible For Release</option>
              <option value="review">🟠 Management Review Required</option>
              <option value="blocked">🔴 Currently Blocked</option>
            </select>
          </div>
        )}
      </div>
    </div>
  );
}


// ── GST Revenue Treatment Card (Feb-2026, Adjustments tab) ─────────────
// Per-center per-month toggle: choose whether GST reduces the Revenue
// Share Base or stays separate. Editable by Super Admin / Accounts Team.
function GSTRevenueTreatmentCard({ token, center, month, summary, onChanged }) {
  const [loading, setLoading] = React.useState(false);
  const [current, setCurrent] = React.useState(null);
  const [saving, setSaving] = React.useState(false);
  const sustainability = summary?.operational_sustainability || {};
  const country = summary?.country || 'India';
  const isAU = country === 'Australia';
  const symbol = isAU ? 'AUD ' : '₹';

  const fmt = (n) => {
    const v = Number(n || 0);
    return `${symbol}${v.toLocaleString(isAU ? 'en-AU' : 'en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const grossSales = Number(sustainability.total_sales || 0);
  const gstCollected = Number(sustainability.gst_on_sales || 0);
  const commissions = Number(sustainability.total_commissions || 0);

  const fetchTreatment = React.useCallback(async () => {
    if (!center || !month || !token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/center-accounts/gst-treatment/get`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, center, month }),
      });
      if (res.ok) setCurrent(await res.json());
    } catch (e) {
      console.error('[GST treatment] fetch failed', e);
    } finally { setLoading(false); }
  }, [token, center, month]);

  React.useEffect(() => { fetchTreatment(); }, [fetchTreatment]);

  const handleChange = async (newValue) => {
    if (!token) { toast.error('Session expired — please log in again'); return; }
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/center-accounts/gst-treatment/set`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, center, month, include_gst_in_revenue: newValue }),
      });
      if (!res.ok) throw new Error(await res.text());
      toast.success(newValue
        ? 'GST Treatment: Include GST in Revenue (Base = Sales − Commissions)'
        : 'GST Treatment: Exclude GST from Revenue (Base = Sales − GST − Commissions)');
      await fetchTreatment();
      if (onChanged) await onChanged();
    } catch (e) {
      toast.error(`Failed to save: ${e.message}`);
    } finally { setSaving(false); }
  };

  const include = !!(current && current.include_gst_in_revenue);
  const base = include ? (grossSales - commissions) : (grossSales - commissions - gstCollected);

  return (
    <Card className="border-2 border-amber-300" data-testid="gst-revenue-treatment-card">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2 text-amber-800">
          <Wallet className="w-5 h-5" />
          GST Revenue Treatment
          <span className="ml-2 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-semibold">
            {center} · {month}
          </span>
        </CardTitle>
        <CardDescription>
          Decide how GST collected from sales is treated when computing the Revenue Share Base for this center & month.
          GST <strong>always remains visible</strong> in every report — only the Revenue Share Base formula changes.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Auto-display block */}
        <div className="grid md:grid-cols-3 gap-3">
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg" data-testid="gst-card-gross-sales">
            <p className="text-xs uppercase tracking-wide text-slate-500 font-semibold">Gross Sales</p>
            <p className="text-xl font-bold text-slate-800">{fmt(grossSales)}</p>
          </div>
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg" data-testid="gst-card-gst-collected">
            <p className="text-xs uppercase tracking-wide text-amber-700 font-semibold">GST Collected From Sales</p>
            <p className="text-xl font-bold text-amber-800">{fmt(gstCollected)}</p>
            <p className="text-[11px] text-amber-700 mt-1 italic">Display only · auto-calculated</p>
          </div>
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg" data-testid="gst-card-commissions">
            <p className="text-xs uppercase tracking-wide text-slate-500 font-semibold">Commissions</p>
            <p className="text-xl font-bold text-slate-800">{fmt(commissions)}</p>
          </div>
        </div>

        {/* Dropdown */}
        <div className="p-4 bg-white border-2 border-amber-200 rounded-lg space-y-3">
          <label className="text-sm font-semibold text-slate-700 block">
            GST Treatment for Revenue Calculation
          </label>
          <select
            value={include ? 'include' : 'exclude'}
            disabled={loading || saving}
            onChange={(e) => handleChange(e.target.value === 'include')}
            className="w-full text-sm border-2 border-slate-300 rounded-md px-3 py-2 bg-white focus:border-amber-500 focus:outline-none"
            data-testid="gst-treatment-select"
          >
            <option value="exclude">Option 1 — Exclude GST from Revenue (Current Method) · Base = Sales − GST − Commissions</option>
            <option value="include">Option 2 — Include GST in Revenue (Optional) · Base = Sales − Commissions</option>
          </select>
          {(loading || saving) && (
            <p className="text-xs text-slate-500 italic">{saving ? 'Saving…' : 'Loading current setting…'}</p>
          )}
          {current?.updated_at && (
            <p className="text-[11px] text-slate-500" data-testid="gst-treatment-updated">
              Last changed by <strong>{current.updated_by || 'unknown'}</strong> · {new Date(current.updated_at).toLocaleString()}
            </p>
          )}
        </div>

        {/* Resulting base preview */}
        <div className="p-4 bg-emerald-50 border-2 border-emerald-200 rounded-lg" data-testid="gst-treatment-base-preview">
          <p className="text-xs uppercase tracking-wide text-emerald-700 font-bold mb-1">
            Resulting Revenue Share Base for {month}
          </p>
          <p className="text-2xl font-bold text-emerald-800" data-testid="gst-treatment-base-amount">
            {fmt(Math.max(0, base))}
          </p>
          <p className="text-xs text-emerald-700 mt-1 font-mono">
            {include
              ? `${fmt(grossSales)} − ${fmt(commissions)} = ${fmt(Math.max(0, base))}`
              : `${fmt(grossSales)} − ${fmt(gstCollected)} − ${fmt(commissions)} = ${fmt(Math.max(0, base))}`}
          </p>
        </div>

        {/* Note */}
        <div className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-md p-3 leading-relaxed">
          <strong>Note:</strong> This setting is saved per center per month. Changes apply automatically to
          Center Overview · MG Payout · Profit &amp; Loss · Revenue Share · Profit Share · Settlement Summary ·
          CA Bundle · Email Package · all Reports &amp; Ledgers. <strong>GST is never hidden</strong> — only its
          treatment in the Revenue Share Base changes.
        </div>
      </CardContent>
    </Card>
  );
}





export default function CenterAccounts() {
  const { session } = useAuth();
  const token = session?.token;
  
  const [loading, setLoading] = useState(false);
  const [centers, setCenters] = useState([]);
  const [selectedCenter, setSelectedCenter] = useState('');
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  
  const [accountSummary, setAccountSummary] = useState(null);
  const [commissionStatements, setCommissionStatements] = useState([]);
  const [linkageStatus, setLinkageStatus] = useState(null);
  const [payoutSummary, setPayoutSummary] = useState(null);
  const [payoutLoading, setPayoutLoading] = useState(false);
  const [payoutFromMonth, setPayoutFromMonth] = useState('');
  const [payoutToMonth, setPayoutToMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  const [exportLoading, setExportLoading] = useState(null);
  
  // Modal states
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showOtherIncomeModal, setShowOtherIncomeModal] = useState(false);
  const [otherIncomeForm, setOtherIncomeForm] = useState({
    date: new Date().toISOString().split("T")[0],
    amount: "",
    category: "vendor_refund",
    reason: "",
  });
  const [otherIncomeSaving, setOtherIncomeSaving] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [selectedPayoutMonth, setSelectedPayoutMonth] = useState(null);
  
  // Commission upload states
  const [uploadPlatform, setUploadPlatform] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [bankFile, setBankFile] = useState(null);
  const [uploadMonth, setUploadMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  const [parsedPreview, setParsedPreview] = useState(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  
  const [paymentForm, setPaymentForm] = useState({
    amount: 0,
    payment_date: new Date().toISOString().split('T')[0],
    notes: ''
  });
  const [editingPayment, setEditingPayment] = useState(null);
  
  const [linkForm, setLinkForm] = useState({
    center_code: '',
    franchise_code: ''
  });

  // Invoice Export state
  const [invoiceExportState, setInvoiceExportState] = useState({
    startDate: '',
    endDate: '',
    category: '',
    vendor: '',
    attachmentStatus: 'all',
    groupedStatus: 'all',
    paymentMode: ''
  });
  const [auditReport, setAuditReport] = useState(null);
  const [exportBatches, setExportBatches] = useState(null);
  const [auditLoading, setAuditLoading] = useState(false);

  // WC Table state
  const [wcTableData, setWcTableData] = useState(null);
  const [wcLoading, setWcLoading] = useState(false);
  const [wcEditingInitial, setWcEditingInitial] = useState(false);
  const [wcInitialValue, setWcInitialValue] = useState('');
  const [showTopupDialog, setShowTopupDialog] = useState(false);
  const [topupAmount, setTopupAmount] = useState('');
  const [topupReason, setTopupReason] = useState('');
  const [topupMonth, setTopupMonth] = useState('');
  const [showTopupLog, setShowTopupLog] = useState(false);
  // Live-edit state for WC row inputs (keyed by month).
  // { "2024-01": { expense: 1000, wc_adj: 0 } }
  const [wcEdits, setWcEdits] = useState({});
  const [wcSaving, setWcSaving] = useState(false);

  // Fetch centers
  const fetchCenters = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API}/api/mgt/centers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      });
      const data = await res.json();
      if (data.centers) {
        // Filter out duplicates by code
        const uniqueCenters = data.centers.reduce((acc, center) => {
          if (!acc.find(c => c.code === center.code)) {
            acc.push(center);
          }
          return acc;
        }, []);
        setCenters(uniqueCenters);
      }
    } catch (error) {
      console.error('Failed to fetch centers');
    }
  }, [token]);

  // Fetch account summary
  const fetchAccountSummary = useCallback(async () => {
    if (!token || !selectedCenter || !selectedMonth) return;
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/center-accounts/summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, center: selectedCenter, month: selectedMonth })
      });
      const data = await res.json();
      if (data.success) {
        setAccountSummary(data.summary);
      } else {
        toast.error(data.detail || 'Failed to fetch account summary');
      }
    } catch (error) {
      toast.error('Failed to fetch account summary');
    } finally {
      setLoading(false);
    }
  }, [token, selectedCenter, selectedMonth]);

  // Fetch commission statements
  const fetchCommissions = useCallback(async () => {
    if (!token || !selectedCenter) return;
    
    try {
      const res = await fetch(`${API}/api/center-accounts/list-commissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, center: selectedCenter, month: selectedMonth })
      });
      const data = await res.json();
      if (data.success) {
        setCommissionStatements(data.statements || []);
      }
    } catch (error) {
      console.error('Failed to fetch commissions');
    }
  }, [token, selectedCenter, selectedMonth]);

  // Fetch linkage status
  const fetchLinkageStatus = useCallback(async () => {
    if (!token) return;
    
    try {
      const res = await fetch(`${API}/api/center-accounts/get-linkage-status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      });
      const data = await res.json();
      if (data.success) {
        setLinkageStatus(data);
      }
    } catch (error) {
      console.error('Failed to fetch linkage status');
    }
  }, [token]);

  // Fetch payout summary for month-wise grid
  const fetchPayoutSummary = useCallback(async () => {
    if (!token || !selectedCenter) return;
    
    setPayoutLoading(true);
    try {
      const body = { token, center: selectedCenter };
      if (payoutFromMonth) body.from_month = payoutFromMonth;
      if (payoutToMonth) body.to_month = payoutToMonth;
      
      const res = await fetch(`${API}/api/center-accounts/payout-summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (data.success) {
        setPayoutSummary(data);
        // Set fromMonth from server response if not set (revenue start date)
        if (!payoutFromMonth && data.period?.from) {
          setPayoutFromMonth(data.period.from);
        }
      }
    } catch (error) {
      console.error('Failed to fetch payout summary:', error);
    } finally {
      setPayoutLoading(false);
    }
  }, [token, selectedCenter, payoutFromMonth, payoutToMonth]);

  // Fetch WC table data
  const fetchWcTable = useCallback(async () => {
    if (!token || !selectedCenter) return;
    setWcLoading(true);
    try {
      const res = await fetch(`${API}/api/center-accounts/wc-table`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, center: selectedCenter })
      });
      const data = await res.json();
      if (data.success) {
        setWcTableData(data);
        // Reset live-edit state to the newly fetched values
        const init = {};
        (data.rows || []).forEach(r => {
          init[r.month] = {
            expense: Math.round(r.expenses || 0),
            wc_adj: Math.round(r.wc_adjustment || 0),
            commission: Math.round(r.commission || 0),
            gst: Math.round(r.gst || 0),
          };
        });
        setWcEdits(init);
      }
    } catch (error) {
      console.error('Failed to fetch WC table');
    } finally {
      setWcLoading(false);
    }
  }, [token, selectedCenter]);

  // Derived: rows recomputed live based on wcEdits, cascading Balance WC forward
  const computedWcRows = useMemo(() => {
    if (!wcTableData?.rows?.length) return [];
    const initialWc = wcTableData.initial_wc || 0;
    let balance = initialWc;
    return wcTableData.rows.map((r) => {
      const edit = wcEdits[r.month] || { expense: r.expenses, wc_adj: r.wc_adjustment || 0, commission: r.commission || 0, gst: r.gst || 0 };
      const expenses = Number(edit.expense) || 0;
      const wcAdj = Number(edit.wc_adj) || 0;
      const commission = Number(edit.commission) || 0;
      const gst = Number(edit.gst) || 0;
      const sale = Number(r.sale) || 0;
      const topup = Number(r.topup) || 0;
      // P/L = Sale - Expenses - Commission (GST column is shown but NOT deducted;
      // GST for Month M is paid as an expense in Month M+1 via the auto-created
      // 'GST PAYMENT' entry, so deducting it here would double-count.)
      const pnl = sale - expenses - commission;
      const openingWc = balance;
      const balanceWc = openingWc + pnl + wcAdj + topup;
      balance = balanceWc;
      let rev = 'active';
      if (initialWc > 0 && balanceWc < initialWc) {
        rev = balanceWc <= initialWc * 0.5 ? 'blocked' : 'restoring';
      }
      return {
        ...r,
        expenses,
        wc_adjustment: wcAdj,
        commission,
        gst,
        pnl,
        opening_wc: openingWc,
        balance_wc: balanceWc,
        diff_wc: balanceWc,
        topup,
        other_income: Number(r.other_income) || 0,
        rev_share_status: rev,
        // flag rows where user has pending unsaved changes
        _dirty: (
          Math.round(expenses) !== Math.round(r.expenses) ||
          Math.round(wcAdj) !== Math.round(r.wc_adjustment || 0) ||
          Math.round(commission) !== Math.round(r.commission || 0) ||
          Math.round(gst) !== Math.round(r.gst || 0)
        ),
      };
    });
  }, [wcTableData, wcEdits]);

  // Save WC override (initial value only)
  const saveWcOverride = async (month, value) => {
    try {
      const body = { token, center: selectedCenter, value: parseFloat(value) };
      const res = await fetch(`${API}/api/center-accounts/wc-override`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (data.success) {
        toast.success(data.message);
        setWcEditingInitial(false);
        fetchWcTable();
      } else {
        toast.error(data.detail || 'Failed to save');
      }
    } catch (error) {
      toast.error('Failed to save WC override');
    }
  };

  // Add manual WC top-up
  const addWcTopup = async () => {
    if (!topupAmount) return;
    try {
      const res = await fetch(`${API}/api/center-accounts/wc-topup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          token, center: selectedCenter, 
          amount: parseFloat(topupAmount),
          reason: topupReason,
          month: topupMonth
        })
      });
      const data = await res.json();
      if (data.success) {
        toast.success(data.message);
        setShowTopupDialog(false);
        setTopupAmount('');
        setTopupReason('');
        setTopupMonth('');
        fetchWcTable();
      } else {
        toast.error(data.detail || 'Failed to add top-up');
      }
    } catch (error) {
      toast.error('Failed to add WC top-up');
    }
  };

  useEffect(() => {
    fetchCenters();
    fetchLinkageStatus();
  }, [fetchCenters, fetchLinkageStatus]);

  useEffect(() => {
    if (selectedCenter) {
      fetchAccountSummary();
      fetchCommissions();
      fetchPayoutSummary();
      fetchWcTable();
    }
  }, [selectedCenter, selectedMonth, fetchAccountSummary, fetchCommissions, fetchPayoutSummary, fetchWcTable]);

  // Upload and parse commission Excel
  const handleUploadCommission = async () => {
    if (!uploadFile || !uploadPlatform || !selectedCenter) {
      toast.error('Please select a file, platform, and center');
      return;
    }
    setUploadLoading(true);
    try {
      const formData = new FormData();
      formData.append('token', token);
      formData.append('platform', uploadPlatform);
      formData.append('center', selectedCenter);
      formData.append('month', uploadMonth);
      formData.append('file', uploadFile);
      if (bankFile && (uploadPlatform === 'cards' || uploadPlatform === 'phonepe')) {
        formData.append('bank_file', bankFile);
      }

      const res = await fetch(`${API}/api/center-accounts/upload-commission-excel`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.success) {
        setParsedPreview(data.parsed);
        setShowUploadModal(false);
        setShowPreviewModal(true);
      } else {
        toast.error(data.detail || 'Failed to parse file');
      }
    } catch (error) {
      toast.error('Failed to upload file');
    } finally {
      setUploadLoading(false);
    }
  };

  // Save parsed commission to DB
  const handleSaveCommission = async () => {
    if (!parsedPreview) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/center-accounts/save-commission`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token,
          center: selectedCenter,
          month: uploadMonth,
          ...parsedPreview
        })
      });
      const data = await res.json();
      if (data.success) {
        toast.success(data.message);
        setShowPreviewModal(false);
        setParsedPreview(null);
        setUploadFile(null);
        setBankFile(null);
        setUploadPlatform('');
        fetchCommissions();
        fetchAccountSummary();
      } else {
        toast.error(data.detail || 'Failed to save commission');
      }
    } catch (error) {
      toast.error('Failed to save commission');
    } finally {
      setLoading(false);
    }
  };

  // Delete commission
  const handleDeleteCommission = async (commissionId) => {
    if (!window.confirm('Delete this commission record?')) return;
    try {
      const res = await fetch(`${API}/api/center-accounts/delete-commission`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, commission_id: commissionId })
      });
      const data = await res.json();
      if (data.success) {
        toast.success('Commission deleted');
        fetchCommissions();
        fetchAccountSummary();
      } else {
        toast.error(data.detail || 'Failed to delete');
      }
    } catch (error) {
      toast.error('Failed to delete commission');
    }
  };

  // Link center to franchise
  const handleLinkFranchise = async () => {
    if (!linkForm.center_code || !linkForm.franchise_code) {
      toast.error('Please select both center and franchise');
      return;
    }
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/center-accounts/link-franchise`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, ...linkForm })
      });
      const data = await res.json();
      if (data.success) {
        toast.success('Center linked to franchise');
        setShowLinkModal(false);
        fetchLinkageStatus();
        if (selectedCenter === linkForm.center_code) {
          fetchAccountSummary();
        }
      } else {
        toast.error(data.detail || 'Failed to link');
      }
    } catch (error) {
      toast.error('Failed to link center to franchise');
    } finally {
      setLoading(false);
    }
  };

  // Record payment for a month
  const handleRecordPayment = async () => {
    if (!paymentForm.amount || paymentForm.amount <= 0) {
      toast.error('Please enter a valid payment amount');
      return;
    }
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/center-accounts/record-payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          token, 
          center: selectedCenter,
          month: selectedPayoutMonth?.month,
          amount: parseFloat(paymentForm.amount),
          payment_date: paymentForm.payment_date,
          notes: paymentForm.notes
        })
      });
      const data = await res.json();
      if (data.success) {
        toast.success(`Payment of ${formatCurrency(paymentForm.amount, accountSummary?.country)} recorded`);
        setShowPaymentModal(false);
        setPaymentForm({ amount: 0, payment_date: new Date().toISOString().split('T')[0], notes: '' });
        setSelectedPayoutMonth(null);
        fetchPayoutSummary();  // Refresh payout data
      } else {
        toast.error(data.detail || 'Failed to record payment');
      }
    } catch (error) {
      toast.error('Failed to record payment');
    } finally {
      setLoading(false);
    }
  };

  // Open payment dialog for a month
  const openPaymentDialog = (monthData) => {
    setSelectedPayoutMonth(monthData);
    setEditingPayment(null);
    setPaymentForm({ 
      amount: monthData.pending || 0,
      payment_date: new Date().toISOString().split('T')[0], 
      notes: '' 
    });
    setShowPaymentModal(true);
  };

  // Start editing a payment
  const startEditPayment = (payment) => {
    setEditingPayment(payment.payment_id);
    setPaymentForm({
      amount: payment.amount || 0,
      payment_date: payment.payment_date || new Date().toISOString().split('T')[0],
      notes: payment.notes || ''
    });
  };

  // Save edited payment
  const handleUpdatePayment = async () => {
    if (!editingPayment) return;
    if (!paymentForm.amount || paymentForm.amount <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/center-accounts/update-payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token,
          payment_id: editingPayment,
          amount: parseFloat(paymentForm.amount),
          payment_date: paymentForm.payment_date,
          notes: paymentForm.notes
        })
      });
      const data = await res.json();
      if (data.success) {
        toast.success('Payment updated');
        setEditingPayment(null);
        setShowPaymentModal(false);
        fetchPayoutSummary();
      } else {
        toast.error(data.detail || 'Failed to update payment');
      }
    } catch (error) {
      toast.error('Failed to update payment');
    } finally {
      setLoading(false);
    }
  };

  // Delete a payment
  const handleDeletePayment = async (paymentId) => {
    if (!window.confirm('Are you sure you want to delete this payment?')) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/center-accounts/delete-payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, payment_id: paymentId })
      });
      const data = await res.json();
      if (data.success) {
        toast.success('Payment deleted');
        setShowPaymentModal(false);
        fetchPayoutSummary();
      } else {
        toast.error(data.detail || 'Failed to delete payment');
      }
    } catch (error) {
      toast.error('Failed to delete payment');
    } finally {
      setLoading(false);
    }
  };

  // Export MG Payout as Excel or PDF
  const handleExportMGPayout = async (format) => {
    if (!token || !selectedCenter) return;
    setExportLoading(format);
    try {
      const body = { token, center: selectedCenter, format };
      if (payoutFromMonth) body.from_month = payoutFromMonth;
      if (payoutToMonth) body.to_month = payoutToMonth;
      
      const res = await fetch(`${API}/api/center-accounts/export-mg-payout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      
      if (!res.ok) {
        const err = await res.json();
        toast.error(err.detail || 'Export failed');
        return;
      }
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      const ext = format === 'excel' ? 'xlsx' : 'pdf';
      a.href = url;
      a.download = `MG_Payout_${selectedCenter}_${payoutFromMonth || 'start'}_to_${payoutToMonth}.${ext}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`MG Payout ${format.toUpperCase()} downloaded`);
    } catch (error) {
      toast.error('Export failed');
    } finally {
      setExportLoading(null);
    }
  };

  // Download PDF report
  const [pibPreview, setPibPreview] = useState(null);      // PIB preview data for view-before-download
  const [pibPreviewLoading, setPibPreviewLoading] = useState(false);
  // Generic PDF preview (GST / Commission) — fetches the PDF blob and renders inline
  const [pdfPreview, setPdfPreview] = useState(null);  // { url, title, reportType } | null
  const [pdfPreviewLoading, setPdfPreviewLoading] = useState(false);

  // Email Pack — generate the monthly email body + ZIP bundle
  const [emailPack, setEmailPack] = useState(null); // { subject, body, attachments, zip_url, zip_filename }
  const [emailPackLoading, setEmailPackLoading] = useState(false);
  // Inline SMTP send form { to, cc, sending } | null
  const [sendForm, setSendForm] = useState(null);
  // Sales/Expense Excel filter on Center Accounts Reports tab
  const [seCaMode, setSeCaMode] = useState('month');   // 'month' | 'range' | 'date'
  const [seCaStart, setSeCaStart] = useState('');
  const [seCaEnd, setSeCaEnd] = useState('');

  const downloadSalesExpenseExcel = async (mode, start, end) => {
    if (!selectedCenter) { toast.error('Select a center first'); return; }
    const body = { token, center: selectedCenter, mode };
    if (mode === 'month') {
      if (!selectedMonth) { toast.error('Select a month first'); return; }
      body.month = selectedMonth;
    } else if (mode === 'range') {
      if (!start || !end) { toast.error('Pick a start and end date'); return; }
      body.start_date = start; body.end_date = end;
    } else if (mode === 'date') {
      if (!start) { toast.error('Pick a date'); return; }
      body.start_date = start;
    }
    try {
      toast.info('Generating Sales/Expense Excel...');
      const res = await fetch(`${API}/api/franchise-reports/sales-expense-excel`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'Failed'); }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      const tag = mode === 'month' ? selectedMonth : (mode === 'range' ? `${start}_to_${end}` : start);
      a.href = url; a.download = `Sales_Expense_${selectedCenter}_${tag}.xlsx`;
      a.click(); window.URL.revokeObjectURL(url);
      toast.success('Excel downloaded');
    } catch (e) { toast.error(e.message || 'Failed'); }
  };

  const openEmailPack = async () => {
    if (!selectedCenter || !selectedMonth) { toast.error('Please select center and month'); return; }
    setEmailPackLoading(true);
    setEmailPack({});
    try {
      // 1) Generate email text + attachment metadata
      const metaRes = await fetch(`${API}/api/center-accounts/email-pack`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, center: selectedCenter, month: selectedMonth, format: 'json' }),
      });
      if (!metaRes.ok) {
        const err = await metaRes.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to build email pack');
      }
      const meta = await metaRes.json();
      // 2) Fetch the ZIP bundle as blob and create object URL
      const zipRes = await fetch(`${API}/api/center-accounts/email-pack`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, center: selectedCenter, month: selectedMonth, format: 'zip' }),
      });
      if (!zipRes.ok) {
        const err = await zipRes.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to build ZIP');
      }
      const blob = await zipRes.blob();
      const url = window.URL.createObjectURL(blob);
      setEmailPack({ ...meta, zip_url: url });
      toast.success('Email pack ready');
    } catch (e) {
      toast.error(e.message || 'Failed');
      setEmailPack(null);
    } finally {
      setEmailPackLoading(false);
    }
  };

  const openPdfPreview = async (reportType) => {
    if (!selectedCenter || !selectedMonth) { toast.error('Please select center and month'); return; }
    const endpoints = {
      gst: 'generate-gst-summary',
      commission: 'generate-commission-summary',
      bank: 'generate-bank-statement',
    };
    const titles = { gst: 'GST Summary', commission: 'Commission Summary', bank: 'Bank Statement' };
    setPdfPreviewLoading(true);
    setPdfPreview({ loading: true, title: titles[reportType], reportType });
    try {
      const res = await fetch(`${API}/api/center-accounts/${endpoints[reportType]}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, center: selectedCenter, month: selectedMonth }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to load preview');
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      setPdfPreview({ url, title: titles[reportType], reportType });
    } catch (e) {
      toast.error(e.message || 'Failed');
      setPdfPreview(null);
    } finally {
      setPdfPreviewLoading(false);
    }
  };

  const openPibPreview = async () => {
    if (!selectedCenter || !selectedMonth) { toast.error('Please select center and month'); return; }
    setPibPreviewLoading(true);
    setPibPreview({ loading: true });
    try {
      // Fire both in parallel: summary numbers (existing) + full PDF blob for inline iframe.
      const [sumRes, pdfRes] = await Promise.all([
        fetch(`${API}/api/center-accounts/preview-pib`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token, center: selectedCenter, month: selectedMonth }),
        }),
        fetch(`${API}/api/center-accounts/generate-pib`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token, center: selectedCenter, month: selectedMonth }),
        }),
      ]);
      if (!sumRes.ok) {
        const err = await sumRes.json();
        throw new Error(err.detail || 'Failed to load preview');
      }
      const summary = await sumRes.json();
      let pdfBlobUrl = null;
      if (pdfRes.ok) {
        const blob = await pdfRes.blob();
        pdfBlobUrl = URL.createObjectURL(blob);
      }
      setPibPreview({ ...summary, pdfBlobUrl });
    } catch (e) {
      toast.error(e.message || 'Failed');
      setPibPreview(null);
    } finally {
      setPibPreviewLoading(false);
    }
  };

  const downloadReport = async (reportType) => {
    // Intercept PIB: show preview first, then the user clicks Download inside the modal.
    if (reportType === 'pib') {
      return openPibPreview();
    }
    if (!selectedCenter || !selectedMonth) {
      toast.error('Please select center and month');
      return;
    }
    
    // Sales/Expense Excel — different endpoint + different content type
    if (reportType === 'sales_expense') {
      try {
        toast.info('Generating Sales/Expense Excel...');
        const res = await fetch(`${API}/api/franchise-reports/sales-expense-excel`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token, center: selectedCenter, mode: 'month', month: selectedMonth }),
        });
        if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'Failed'); }
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `Sales_Expense_${selectedCenter}_${selectedMonth}.xlsx`;
        a.click(); window.URL.revokeObjectURL(url);
        toast.success('Excel downloaded');
      } catch (e) { toast.error(e.message || 'Failed'); }
      return;
    }

    const endpoints = {
      pib: 'generate-pib',
      gst: 'generate-gst-summary',
      commission: 'generate-commission-summary',
      bank: 'generate-bank-statement',
    };
    // ── New extra-report endpoints (Feb-2026 sprint) ──
    const extraEndpoints = {
      pnl: 'profit-loss',
      'mg-summary': 'mg-summary',
      'payout-summary': 'payout-summary',
      phonepe: 'phonepe-recon',
      'gst-paid': 'gst-paid',
      'missing-bills': 'missing-bills',
      'expense-attachments': 'expense-attachments-zip',
    };
    if (extraEndpoints[reportType]) {
      try {
        toast.info(`Generating ${reportType.replace(/-/g,' ').toUpperCase()}...`);
        const res = await fetch(`${API}/api/extra-reports/${extraEndpoints[reportType]}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token, center: selectedCenter, month: selectedMonth }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `Failed (${res.status})`);
        }
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const isZip = reportType === 'expense-attachments';
        a.download = isZip
          ? `Expense_Attachments_${selectedCenter}_${selectedMonth}.zip`
          : `${reportType.toUpperCase()}_${selectedCenter}_${selectedMonth}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
        toast.success(`${isZip ? 'ZIP' : 'PDF'} downloaded`);
      } catch (e) { toast.error(e.message || 'Failed'); }
      return;
    }
    
    try {
      toast.info(`Generating ${reportType.toUpperCase()} report...`);
      const res = await fetch(`${API}/api/center-accounts/${endpoints[reportType]}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, center: selectedCenter, month: selectedMonth })
      });
      
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to generate report');
      }
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${reportType.toUpperCase()}_${selectedCenter}_${selectedMonth}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('Report downloaded');
    } catch (error) {
      toast.error(error.message || 'Failed to download report');
    }
  };

  const getCountry = () => {
    if (!selectedCenter) return 'India';
    const center = centers.find(c => c.code === selectedCenter);
    if (!center) return 'India';
    return center.country === 'Australia' || center.is_india_center === false ? 'Australia' : 'India';
  };

  const availablePlatforms = getCountry() === 'Australia' ? PLATFORMS.australia : PLATFORMS.india;
  const country = getCountry();

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="center-accounts-page">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Center Accounts</h1>
        <p className="text-gray-600">Financial management, commission tracking & PIB generation</p>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            <div>
              <Label>Select Center</Label>
              <Select value={selectedCenter} onValueChange={setSelectedCenter}>
                <SelectTrigger data-testid="center-select">
                  <SelectValue placeholder="Select center" />
                </SelectTrigger>
                <SelectContent>
                  {centers.map(c => (
                    <SelectItem key={c.code} value={c.code}>
                      {c.code} - {c.name || c.code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Month</Label>
              <Input 
                type="month" 
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                data-testid="month-select"
              />
            </div>
            <div>
              <Button onClick={fetchAccountSummary} disabled={!selectedCenter || loading}>
                {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <RefreshCw className="w-4 h-4 mr-2" />}
                Refresh
              </Button>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setShowUploadModal(true)} disabled={!selectedCenter}>
                <Upload className="w-4 h-4 mr-2" />
                Upload Commission
              </Button>
              {session?.is_super_admin && (
                <Button variant="outline" onClick={() => setShowLinkModal(true)}>
                  <Link className="w-4 h-4 mr-2" />
                  Link Franchise
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      {accountSummary && (
        <>
          {/* Franchise Linkage Warning */}
          {!accountSummary.franchise.linked && (
            <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-yellow-600" />
              <div>
                <p className="font-medium text-yellow-800">Center not linked to a franchise</p>
                <p className="text-sm text-yellow-600">Link this center to a franchise to enable PIB generation and revenue share calculations.</p>
              </div>
              {session?.is_super_admin && (
                <Button size="sm" variant="outline" className="ml-auto" onClick={() => {
                  setLinkForm({ center_code: selectedCenter, franchise_code: '' });
                  setShowLinkModal(true);
                }}>
                  <Link className="w-4 h-4 mr-2" />
                  Link Now
                </Button>
              )}
            </div>
          )}

          {/* Payout Release Status Banner (Feb-2026 directive — informational only) */}
          <PayoutStatusBanner
            status={accountSummary.payout_release_status}
            isAdmin={!!(session?.is_super_admin || session?.is_admin || session?.role === 'Accounts')}
            onChange={async (value) => {
              try {
                const res = await fetch(`${API}/api/center-accounts/set-payout-release-status`, {
                  method: 'POST', headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ center: selectedCenter, token: session.token, value, month: selectedMonth }),
                });
                const data = await res.json();
                if (data.detail) throw new Error(data.detail);
                toast.success(`Payout release status set to "${value}"`);
                fetchAccountSummary();
              } catch (e) { toast.error(e.message); }
            }}
          />

          {/* Key Metrics */}
          <div className={`grid grid-cols-2 ${accountSummary.country === "Australia" ? "md:grid-cols-5" : "md:grid-cols-4"} gap-4 mb-6`}>
            <Card className="bg-gradient-to-br from-blue-50 to-blue-100">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-blue-600">Total Sales</p>
                    <p className="text-2xl font-bold text-blue-800">
                      {formatCurrency(accountSummary.sales.total_sale, accountSummary.country)}
                    </p>
                  </div>
                  <DollarSign className="w-8 h-8 text-blue-400" />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-red-50 to-red-100">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-red-600">Total Expenses</p>
                    <p className="text-2xl font-bold text-red-800">
                      {formatCurrency(accountSummary.expenses.total, accountSummary.country)}
                    </p>
                  </div>
                  <Receipt className="w-8 h-8 text-red-400" />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-orange-50 to-orange-100">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-orange-600">Total Deductions</p>
                    <p className="text-2xl font-bold text-orange-800" data-testid="kpi-total-deductions">
                      {(() => {
                        const includeGst = accountSummary.share_calculation?.include_gst_in_revenue
                          || accountSummary.operational_sustainability?.include_gst_in_revenue;
                        // Prefer backend-computed value (already honours GST toggle).
                        if (accountSummary.share_calculation?.total_deductions !== undefined) {
                          return formatCurrency(accountSummary.share_calculation.total_deductions, accountSummary.country);
                        }
                        // Fallback: compute locally.
                        const commIncl = accountSummary.country === "Australia"
                          ? (accountSummary.commissions?.total_with_gst || accountSummary.commissions?.total || 0)
                          : (accountSummary.commissions?.total || 0);
                        const gstTerm = includeGst ? 0 : (accountSummary.financial_summary?.sales_gst || 0);
                        return formatCurrency(commIncl + gstTerm, accountSummary.country);
                      })()}
                    </p>
                    <p className="text-[10px] text-orange-700 mt-1" data-testid="kpi-total-deductions-label">
                      {accountSummary.share_calculation?.total_deductions_label
                        || (accountSummary.country === "Australia"
                            ? "Commissions (incl GST) + GST on Eligible Sales"
                            : "Commissions + GST on Eligible Sales")}
                    </p>
                  </div>
                  <CreditCard className="w-8 h-8 text-orange-400" />
                </div>
              </CardContent>
            </Card>

            {/* Net Revenue tile HIDDEN per Feb-2026 owner directive — Net Revenue
                creates confusion since it's NOT the basis for owner payout.
                Revenue Share Base (below) is the canonical primary metric. */}

            {accountSummary.country !== "Australia" && accountSummary.operational_sustainability?.revenue_share_base !== undefined && (() => {
              // Model-aware KPI tile — single base shown, matching the franchise's
              // Payout Model from Franchise Management. No mixed bases anywhere.
              const isProfit = accountSummary.payout_model === 'profit_share';
              const baseValue = isProfit
                ? (accountSummary.engine?.profit_share_base ?? accountSummary.engine?.selected_base ?? 0)
                : (accountSummary.operational_sustainability.revenue_share_base ?? 0);
              const baseLabel = isProfit ? "Profit Share Base" : "Revenue Share Base";
              const formula = isProfit
                ? "Sales − Commissions − Expenses − Adjustments · used for owner % split"
                : "Sales − Commissions − GST · used for owner % split";
              return (
              <Card className="bg-gradient-to-br from-sky-100 to-sky-200 border-2 border-sky-400 shadow-lg" data-testid="kpi-revenue-share-base-card" title="Base for the owner / company % split, as configured in Franchise Management → Payout Model.">
                <CardContent className="p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-semibold text-sky-800 uppercase tracking-wide" data-testid="kpi-base-label">⭐ {baseLabel}</p>
                      <p className="text-3xl font-extrabold text-sky-900" data-testid="kpi-revenue-share-base">
                        {formatCurrency(baseValue, accountSummary.country)}
                      </p>
                      <p className="text-[11px] text-sky-800 mt-1 font-medium">{formula}</p>
                    </div>
                    <TrendingUp className="w-10 h-10 text-sky-600" />
                  </div>
                </CardContent>
              </Card>
              );
            })()}

            {accountSummary.country !== "Australia" && accountSummary.operational_sustainability && accountSummary.payout_model === 'profit_share' && (
              <Card className="bg-gradient-to-br from-rose-50 to-rose-100" data-testid="kpi-profit-loss-card">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-rose-700">Profit Share Base (Operational)</p>
                      <p className={`text-2xl font-bold ${(accountSummary.operational_sustainability.profit_loss ?? 0) >= 0 ? 'text-emerald-800' : 'text-rose-800'}`} data-testid="kpi-profit-loss">
                        {formatCurrency(accountSummary.operational_sustainability.profit_loss ?? accountSummary.operational_sustainability.operational_balance ?? 0, accountSummary.country)}
                      </p>
                      <p className="text-[10px] text-rose-700 mt-1">Sales − Expenses − Commissions (base for 80/20 split)</p>
                    </div>
                    <TrendingUp className={`w-8 h-8 ${(accountSummary.operational_sustainability.profit_loss ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`} />
                  </div>
                </CardContent>
              </Card>
            )}

            {accountSummary.country === "Australia" && (
              <Card className="bg-gradient-to-br from-emerald-50 to-emerald-100">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-emerald-700">Profitability</p>
                      <p className="text-2xl font-bold text-emerald-900" data-testid="kpi-profitability">
                        {formatCurrency(accountSummary.financial_summary.profitability ?? 0, accountSummary.country)}
                      </p>
                      <p className="text-[10px] text-emerald-700 mt-1">
                        Net Revenue − Expenses · 80/20 base
                      </p>
                    </div>
                    <TrendingUp className="w-8 h-8 text-emerald-500" />
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Main Content Tabs */}
          <Tabs defaultValue="overview" className="space-y-4">
            <TabsList className="flex-wrap" data-testid="center-accounts-tabs">
              <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
              <TabsTrigger value="sales" data-testid="tab-sales">Sales Breakdown</TabsTrigger>
              <TabsTrigger value="commissions" data-testid="tab-commissions">Commissions</TabsTrigger>
              <TabsTrigger value="share" data-testid="tab-share">{accountSummary?.payout_model === 'profit_share' ? 'Profit Share' : 'Revenue Share'}</TabsTrigger>
              <TabsTrigger value="mg-payout" data-testid="tab-mg-payout">MG Payout</TabsTrigger>
              <TabsTrigger value="adjustments" data-testid="tab-adjustments" className="text-amber-700">Adjustments</TabsTrigger>
              <TabsTrigger value="insights" data-testid="tab-insights" className="text-rose-700"><Activity className="w-3.5 h-3.5 mr-1" />Financial Insights</TabsTrigger>
              <TabsTrigger value="health" data-testid="tab-health" className="text-rose-800"><HeartPulse className="w-3.5 h-3.5 mr-1" />Financial Health</TabsTrigger>
              <TabsTrigger value="reports" data-testid="tab-reports">Reports</TabsTrigger>
              <TabsTrigger value="ledgers" data-testid="tab-ledgers" className="text-indigo-600"><BookOpen className="w-3.5 h-3.5 mr-1" />Ledgers</TabsTrigger>
              <TabsTrigger value="bundles" data-testid="tab-bundles" className="text-purple-600">Bundles &amp; Exports</TabsTrigger>
              <TabsTrigger value="pnl-rs" data-testid="tab-pnl-rs" className="text-emerald-700">P&amp;L Revenue Share Overview</TabsTrigger>
              <TabsTrigger value="rs-projection" data-testid="tab-rs-projection" className="text-emerald-700">Revenue Share Projection</TabsTrigger>
            </TabsList>

            {/* Overview Tab — 11-item Snapshot */}
            <TabsContent value="overview" className="space-y-4" data-testid="overview-tab-content">
              {(() => {
                const cur = accountSummary?.country || 'India';
                const fin = accountSummary?.financial_summary || {};
                const eng = accountSummary?.engine || {};
                const wc = accountSummary?.working_capital_status || {};
                const payout = accountSummary?.payout || {};
                const shareCalc = accountSummary?.share_calculation || {};
                const modelWord = accountSummary?.payout_model === 'profit_share' ? 'Profit Share' : 'Revenue Share';

                const totalSales = fin.total_sales || 0;
                const gst = fin.sales_gst || 0;
                const commissions = fin.total_commissions || 0;
                const expenses = fin.total_expenses || 0;
                const wcAdj = fin.wc_adjustments || eng.adjustments?.wc_adjustments || 0;
                const manualAdj = fin.manual_adjustments || eng.adjustments?.manual_adjustments || 0;
                const adjustments = wcAdj + manualAdj;
                const revenueShareBase = eng.revenue_share_base ?? (totalSales - commissions - gst);
                const profitShareBase = eng.profit_share_base ?? (totalSales - commissions - expenses + wcAdj + manualAdj);
                const pbt = totalSales - expenses - commissions;

                const wcCurrent = wc.current_wc || 0;
                const wcBase = wc.base_wc || wc.initial_wc || 0;
                const wcPct = wc.wc_percentage || (wcBase > 0 ? (wcCurrent / wcBase) * 100 : 100);
                const wcStatus = wc.status || (wc.protection_mode ? 'Protection' : 'Healthy');
                const wcSafe = !wc.protection_mode && wcPct >= 50;

                const mgApplicable = accountSummary?.mg_calculation_applicable !== false;
                const mgAmount = payout.mg_amount || 0;
                const mgWon = payout.type === 'minimum_guarantee';

                const payoutAmount = payout.amount || 0;
                const payoutType = payout.type || '—';
                const payoutLabel = payout.protection_mode
                  ? 'Protection Mode'
                  : payoutType === 'minimum_guarantee'
                    ? 'MG'
                    : payoutType.includes('share')
                      ? modelWord
                      : payoutType.replace(/_/g, ' ');

                const tile = (label, value, opts = {}) => (
                  <Card className={`border ${opts.tone || 'border-gray-200'} ${opts.bg || 'bg-white'} hover:shadow-md transition-shadow`} data-testid={`overview-tile-${opts.testid}`}>
                    <CardContent className="p-4">
                      <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium">{label}</p>
                      <div className="mt-2 flex items-baseline justify-between gap-2">
                        <p className={`text-2xl font-bold ${opts.text || 'text-gray-900'}`}>{value}</p>
                        {opts.badge && <Badge className={opts.badgeClass}>{opts.badge}</Badge>}
                      </div>
                      {opts.sub && <p className="text-[11px] text-muted-foreground mt-1">{opts.sub}</p>}
                    </CardContent>
                  </Card>
                );

                return (
                  <>
                    {/* Header strip — Center / Period / Payout Model context */}
                    <Card className="bg-gradient-to-r from-stone-50 to-stone-100 border-stone-200">
                      <CardContent className="p-4 flex flex-wrap items-center justify-between gap-4">
                        <div>
                          <p className="text-xs text-muted-foreground">Center · Period</p>
                          <p className="text-xl font-bold text-stone-800">{accountSummary?.center_name || selectedCenter} <span className="text-stone-400 text-base">·</span> {accountSummary?.period}</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="text-right">
                            <p className="text-xs text-muted-foreground">Payout Model</p>
                            <Badge className={accountSummary?.payout_model === 'profit_share' ? 'bg-purple-700' : 'bg-sky-700'}>{modelWord}</Badge>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-muted-foreground">Country</p>
                            <Badge variant="outline">{cur}</Badge>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* 11-item Snapshot Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                      {tile('Gross Sales', formatCurrency(totalSales, cur), { tone: 'border-blue-200', bg: 'bg-blue-50', text: 'text-blue-900', testid: 'gross-sales' })}
                      {tile('GST', formatCurrency(gst, cur), { tone: 'border-rose-200', bg: 'bg-rose-50', text: 'text-rose-800', testid: 'gst' })}
                      {tile('Commissions', formatCurrency(commissions, cur), { tone: 'border-orange-200', bg: 'bg-orange-50', text: 'text-orange-800', testid: 'commissions' })}
                      {tile('Expenses', formatCurrency(expenses, cur), { tone: 'border-amber-200', bg: 'bg-amber-50', text: 'text-amber-800', testid: 'expenses' })}
                      {tile('Adjustments', formatCurrency(adjustments, cur), { tone: 'border-violet-200', bg: 'bg-violet-50', text: 'text-violet-800', testid: 'adjustments', sub: `WC: ${formatCurrency(wcAdj, cur)} · Manual: ${formatCurrency(manualAdj, cur)}` })}
                      {tile('Revenue Share Base', formatCurrency(revenueShareBase, cur), { tone: 'border-sky-300', bg: 'bg-sky-50', text: 'text-sky-900', testid: 'revenue-share-base', sub: 'Sales − Commissions − GST' })}
                      {tile('Profit Share Base', formatCurrency(profitShareBase, cur), { tone: 'border-emerald-300', bg: 'bg-emerald-50', text: 'text-emerald-900', testid: 'profit-share-base', sub: 'Sales − Commissions − Expenses + Adj' })}
                      {tile('PBT', formatCurrency(pbt, cur), { tone: 'border-indigo-200', bg: 'bg-indigo-50', text: pbt >= 0 ? 'text-indigo-900' : 'text-red-700', testid: 'pbt', sub: 'Profit Before Tax' })}
                      {tile('Working Capital', formatCurrency(wcCurrent, cur), {
                        tone: wcSafe ? 'border-green-300' : 'border-red-300',
                        bg: wcSafe ? 'bg-green-50' : 'bg-red-50',
                        text: wcSafe ? 'text-green-800' : 'text-red-700',
                        testid: 'wc-status',
                        badge: wcStatus,
                        badgeClass: wcSafe ? 'bg-green-600 text-white' : 'bg-red-600 text-white',
                        sub: `${wcPct.toFixed(0)}% of base · ${formatCurrency(wcBase, cur)}`
                      })}
                      {tile('MG Status', mgApplicable ? formatCurrency(mgAmount, cur) : 'N/A', {
                        tone: mgWon ? 'border-purple-300' : 'border-gray-200',
                        bg: mgWon ? 'bg-purple-50' : 'bg-gray-50',
                        text: mgWon ? 'text-purple-800' : 'text-gray-700',
                        testid: 'mg-status',
                        badge: mgApplicable ? (mgWon ? 'Won' : 'Applicable') : 'Off',
                        badgeClass: mgWon ? 'bg-purple-600 text-white' : mgApplicable ? 'bg-gray-300 text-gray-700' : 'bg-stone-300 text-stone-700',
                        sub: mgApplicable ? `Monthly MG floor` : `${modelWord}-only model`
                      })}
                      {tile('Payout Status', formatCurrency(payoutAmount, cur), {
                        tone: payout.protection_mode ? 'border-red-300' : 'border-teal-300',
                        bg: payout.protection_mode ? 'bg-red-50' : 'bg-teal-50',
                        text: payout.protection_mode ? 'text-red-800' : 'text-teal-800',
                        testid: 'payout-status',
                        badge: payoutLabel,
                        badgeClass: payout.protection_mode ? 'bg-red-600 text-white' : 'bg-teal-600 text-white',
                        sub: payout.reason ? (payout.reason.length > 60 ? payout.reason.slice(0, 60) + '…' : payout.reason) : '—'
                      })}
                    </div>

                    {/* Month-wise Working Capital Overview Grid (Feb-2026 — restored per user spec).
                        Pulls from /api/center-accounts/wc-table which already powers the existing
                        Working Capital chain elsewhere; this just surfaces it inside the Overview
                        tab with a clean grid + totals + PDF/Excel downloads. */}
                    <WCOverviewGrid
                      apiBase={API}
                      token={token}
                      center={selectedCenter}
                      country={accountSummary?.country}
                      cur={cur}
                    />

                    {/* Footer hint */}
                    <p className="text-[11px] text-muted-foreground italic pt-2">
                      All numbers driven by the Single Financial Engine. Open <strong>MG Payout</strong> for payout breakdown,
                      <strong> Reports</strong> for full P&amp;L / GST / Settlement reports, <strong>Ledgers</strong> for books of account,
                      <strong> Bundles &amp; Exports</strong> for one-click ZIP downloads.
                    </p>
                  </>
                );
              })()}
            </TabsContent>
            {/* Sales Breakdown Tab */}
            <TabsContent value="sales" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Sales Breakdown</CardTitle>
                  <CardDescription>Detailed breakdown of all sales channels</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="grid md:grid-cols-2 gap-6">
                      {/* Direct vs Aggregator */}
                      <div>
                        <h4 className="font-medium mb-3">By Channel</h4>
                        <div className="space-y-2">
                          <div className="flex justify-between items-center p-2 bg-blue-50 rounded">
                            <span>Direct Sales</span>
                            <span className="font-medium">{formatCurrency(accountSummary.sales.direct_sale, accountSummary.country)}</span>
                          </div>
                          <div className="flex justify-between items-center p-2 bg-orange-50 rounded">
                            <span>Aggregator Sales</span>
                            <span className="font-medium">{formatCurrency(accountSummary.sales.aggregator_sale, accountSummary.country)}</span>
                          </div>
                          <div className="flex justify-between items-center p-2 bg-purple-50 rounded">
                            <span>Card Sales</span>
                            <span className="font-medium">{formatCurrency(accountSummary.sales.card_sale, accountSummary.country)}</span>
                          </div>
                          <div className="flex justify-between items-center p-2 bg-green-50 rounded">
                            <span>Cash Sales</span>
                            <span className="font-medium">{formatCurrency(accountSummary.sales.total_cash_sale, accountSummary.country)}</span>
                          </div>
                          {(accountSummary.sales.bharat_pay || 0) > 0 && (
                            <div className="flex justify-between items-center p-2 bg-indigo-50 rounded" data-testid="sales-row-bharatpe">
                              <span>PhonePe / BharatPe (UPI)</span>
                              <span className="font-medium">{formatCurrency(accountSummary.sales.bharat_pay, accountSummary.country)}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Aggregator Breakdown */}
                      <div>
                        <h4 className="font-medium mb-3">Aggregator Details</h4>
                        <div className="space-y-2">
                          {accountSummary.country === 'India' ? (
                            <>
                              <div className="flex justify-between items-center p-2 bg-orange-50 rounded">
                                <span>Swiggy</span>
                                <span className="font-medium">{formatCurrency(accountSummary.sales.swiggy, accountSummary.country)}</span>
                              </div>
                              <div className="flex justify-between items-center p-2 bg-red-50 rounded">
                                <span>Zomato</span>
                                <span className="font-medium">{formatCurrency(accountSummary.sales.zomato, accountSummary.country)}</span>
                              </div>
                            </>
                          ) : (
                            <div className="flex justify-between items-center p-2 bg-red-50 rounded">
                              <span>DoorDash</span>
                              <span className="font-medium">{formatCurrency(accountSummary.sales.doordash, accountSummary.country)}</span>
                            </div>
                          )}
                          <div className="flex justify-between items-center p-2 bg-gray-50 rounded">
                            <span>Other Online</span>
                            <span className="font-medium">{formatCurrency(accountSummary.sales.online_other, accountSummary.country)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Other Income (adjusts next-month Opening Balance) */}
                  {(accountSummary.other_income?.total > 0 || accountSummary.other_income?.rows?.length > 0) && (
                    <div className="mt-6 p-4 rounded-lg border-2 border-emerald-200 bg-emerald-50/50" data-testid="other-income-block">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <h4 className="font-semibold text-emerald-800">Other Income</h4>
                          <p className="text-xs text-emerald-700/80">
                            Non-operating cash inflow. Stays OUT of Sales / P&amp;L / MG, but
                            <strong> adjusts next month's Opening Balance (WC)</strong>.
                          </p>
                        </div>
                        <span className="font-bold text-emerald-700">
                          {formatCurrency(accountSummary.other_income?.total || 0, accountSummary.country)}
                        </span>
                      </div>
                      <div className="space-y-1.5">
                        {(accountSummary.other_income?.rows || []).map((r) => (
                          <div key={r.income_id} className="flex justify-between items-center px-3 py-1.5 bg-white rounded text-sm" data-testid={`oi-row-${r.income_id}`}>
                            <span className="flex items-center gap-2 flex-1 min-w-0">
                              <span className="text-[10px] uppercase tracking-wide text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded shrink-0">
                                {(r.category || "other").replace(/_/g, " ")}
                              </span>
                              <span className="text-muted-foreground shrink-0">{r.date}</span>
                              <span className="text-foreground truncate">{r.reason}</span>
                              {r.auto_generated && <span className="text-[9px] text-amber-700 bg-amber-100 px-1 rounded shrink-0">AUTO</span>}
                            </span>
                            <span className="flex items-center gap-2 shrink-0">
                              <span className="font-medium">{formatCurrency(r.amount, accountSummary.country)}</span>
                              {(session?.is_super_admin || session?.is_admin || session?.role_key === "accountant" || session?.role_key === "accounts") && !r.auto_generated && (
                                <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-rose-600 hover:bg-rose-50"
                                  data-testid={`oi-delete-${r.income_id}`}
                                  onClick={async () => {
                                    if (!window.confirm(`Delete Other Income entry of ${formatCurrency(r.amount, accountSummary.country)}?`)) return;
                                    try {
                                      const resp = await fetch(`${API}/api/other-income/delete/${r.income_id}`, {
                                        method: "POST",
                                        headers: { "Content-Type": "application/json" },
                                        body: JSON.stringify({ token: session?.token }),
                                      });
                                      const dd = await resp.json();
                                      if (resp.ok && dd.success) {
                                        toast.success("Deleted");
                                        await fetchAccountSummary();
                                      } else {
                                        toast.error(dd.detail || "Delete failed");
                                      }
                                    } catch { toast.error("Delete failed"); }
                                  }}>
                                  <Trash2 className="w-3.5 h-3.5" />
                                </Button>
                              )}
                              {r.auto_generated && (
                                <span className="text-[9px] text-muted-foreground italic shrink-0" title="Delete the source loan to remove this entry">linked to loan</span>
                              )}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Loans Taken — borrower-side memo with outstanding/repaid */}
                  {accountSummary.loans_taken?.total > 0 && (
                    <div className="mt-4 p-4 rounded-lg border-2 border-amber-200 bg-amber-50/50" data-testid="loans-taken-block">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <h4 className="font-semibold text-amber-800">Loans Taken (this center)</h4>
                          <p className="text-xs text-amber-700/80">
                            Loan principal received. Auto-added to Other Income above.
                          </p>
                        </div>
                        <div className="text-right text-xs">
                          <div><span className="text-muted-foreground">Total taken:</span> <span className="font-bold text-amber-700">{formatCurrency(accountSummary.loans_taken.total, accountSummary.country)}</span></div>
                          <div><span className="text-muted-foreground">Repaid:</span> <span className="text-emerald-700 font-medium">{formatCurrency(accountSummary.loans_taken.repaid || 0, accountSummary.country)}</span></div>
                          <div><span className="text-muted-foreground">Outstanding:</span> <span className="text-rose-700 font-bold">{formatCurrency(accountSummary.loans_taken.outstanding || 0, accountSummary.country)}</span></div>
                        </div>
                      </div>
                      <div className="space-y-1.5">
                        {(accountSummary.loans_taken.rows || []).map((r) => (
                          <div key={r.loan_id} className="flex justify-between items-center px-3 py-1.5 bg-white rounded text-sm">
                            <span className="flex items-center gap-2 flex-1 min-w-0">
                              <span className="text-[10px] uppercase tracking-wide text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded shrink-0">From {r.source_center || "Ext"}</span>
                              <span className="text-muted-foreground shrink-0">{r.loan_date}</span>
                              <span className="text-foreground truncate">{r.reason}</span>
                              {r.status === "fully_repaid" && <span className="text-[9px] text-emerald-700 bg-emerald-100 px-1 rounded shrink-0">FULLY REPAID</span>}
                              {r.status === "partial" && <span className="text-[9px] text-amber-700 bg-amber-100 px-1 rounded shrink-0">PARTIAL</span>}
                              {(!r.status || r.status === "outstanding") && <span className="text-[9px] text-rose-700 bg-rose-100 px-1 rounded shrink-0">OUTSTANDING</span>}
                            </span>
                            <span className="flex items-center gap-3 shrink-0 text-xs">
                              <span><span className="text-muted-foreground">Amt:</span> <span className="font-medium">{formatCurrency(r.amount, accountSummary.country)}</span></span>
                              <span><span className="text-muted-foreground">Repaid:</span> <span className="text-emerald-700">{formatCurrency(r.repaid, accountSummary.country)}</span></span>
                              <span><span className="text-muted-foreground">Out:</span> <span className="text-rose-700 font-semibold">{formatCurrency(r.outstanding, accountSummary.country)}</span></span>
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Loans Given — anonymised, with outstanding/repaid */}
                  {accountSummary.loans_given?.total > 0 && (
                    <div className="mt-4 p-4 rounded-lg border-2 border-rose-200 bg-rose-50/50" data-testid="loans-given-block">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <h4 className="font-semibold text-rose-800">Loan Given to Other Center (Memo)</h4>
                          <p className="text-xs text-rose-700/80">
                            Cash given out as a loan. Tracked in Loan Entries ledger.
                          </p>
                        </div>
                        <div className="text-right text-xs">
                          <div><span className="text-muted-foreground">Total given:</span> <span className="font-bold text-rose-700">{formatCurrency(accountSummary.loans_given.total, accountSummary.country)}</span></div>
                          <div><span className="text-muted-foreground">Repaid:</span> <span className="text-emerald-700 font-medium">{formatCurrency(accountSummary.loans_given.repaid || 0, accountSummary.country)}</span></div>
                          <div><span className="text-muted-foreground">Outstanding:</span> <span className="text-rose-700 font-bold">{formatCurrency(accountSummary.loans_given.outstanding || 0, accountSummary.country)}</span></div>
                        </div>
                      </div>
                      <div className="space-y-1.5">
                        {(accountSummary.loans_given.rows || []).map((r) => (
                          <div key={r.loan_id} className="flex justify-between items-center px-3 py-1.5 bg-white rounded text-sm">
                            <span className="flex items-center gap-2 flex-1 min-w-0">
                              <span className="text-[10px] uppercase tracking-wide text-rose-700 bg-rose-100 px-1.5 py-0.5 rounded shrink-0">Loan Given</span>
                              <span className="text-muted-foreground shrink-0">{r.loan_date}</span>
                              <span className="text-foreground truncate">{r.reason}</span>
                              {r.status === "fully_repaid" && <span className="text-[9px] text-emerald-700 bg-emerald-100 px-1 rounded shrink-0">FULLY REPAID</span>}
                              {r.status === "partial" && <span className="text-[9px] text-amber-700 bg-amber-100 px-1 rounded shrink-0">PARTIAL</span>}
                              {(!r.status || r.status === "outstanding") && <span className="text-[9px] text-rose-700 bg-rose-100 px-1 rounded shrink-0">OUTSTANDING</span>}
                            </span>
                            <span className="flex items-center gap-3 shrink-0 text-xs">
                              <span><span className="text-muted-foreground">Amt:</span> <span className="font-medium">{formatCurrency(r.amount, accountSummary.country)}</span></span>
                              <span><span className="text-muted-foreground">Repaid:</span> <span className="text-emerald-700">{formatCurrency(r.repaid, accountSummary.country)}</span></span>
                              <span><span className="text-muted-foreground">Out:</span> <span className="text-rose-700 font-semibold">{formatCurrency(r.outstanding, accountSummary.country)}</span></span>
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Add Other Income button (admin / accounts) */}
                  {(session?.is_super_admin || session?.is_admin || session?.role_key === "accountant" || session?.role_key === "accounts") && (
                    <div className="mt-4 flex justify-end">
                      <Button size="sm" variant="outline"
                        className="border-emerald-500 text-emerald-700 hover:bg-emerald-50"
                        onClick={() => setShowOtherIncomeModal(true)}
                        data-testid="add-other-income-btn">
                        <Plus className="w-4 h-4 mr-1" /> Add Other Income
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="commissions" className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-medium" data-testid="commissions-header">Uploaded Commission Reports</h3>
                <Button onClick={() => setShowUploadModal(true)} data-testid="upload-commission-btn">
                  <Upload className="w-4 h-4 mr-2" />
                  Upload Excel Report
                </Button>
              </div>

              <Card>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full" data-testid="commission-table">
                      <thead className="bg-gray-50 border-b">
                        <tr>
                          <th className="text-left p-3 text-sm font-medium">Platform</th>
                          <th className="text-left p-3 text-sm font-medium">Month</th>
                          <th className="text-right p-3 text-sm font-medium">Gross Amount</th>
                          <th className="text-right p-3 text-sm font-medium">GST/Tax Ded.</th>
                          <th className="text-right p-3 text-sm font-medium">Other Ded.</th>
                          <th className="text-right p-3 text-sm font-medium" title="PhonePe Commission / MDR (Gross − Net)">PG Comm.</th>
                          <th className="text-right p-3 text-sm font-medium">Net Payout</th>
                          <th className="text-right p-3 text-sm font-medium">Orders</th>
                          <th className="text-left p-3 text-sm font-medium">File</th>
                          <th className="text-center p-3 text-sm font-medium">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {commissionStatements.length === 0 ? (
                          <tr>
                            <td colSpan={10} className="text-center py-8 text-gray-500">
                              No commission uploads for this period. Upload an Excel report to get started.
                            </td>
                          </tr>
                        ) : (
                          commissionStatements.map((stmt) => (
                            <tr key={stmt.commission_id} className="border-b hover:bg-gray-50">
                              <td className="p-3">
                                <Badge className={ALL_PLATFORMS.find(p => p.value === stmt.platform)?.color || 'bg-gray-100 text-gray-800'}>
                                  {stmt.platform.toUpperCase()}
                                </Badge>
                              </td>
                              <td className="p-3 text-sm font-medium">{stmt.month}</td>
                              <td className="p-3 text-right">{formatCurrency(stmt.gross_amount, accountSummary?.country)}</td>
                              <td className="p-3 text-right text-orange-600">{formatCurrency(stmt.gst_tax_deductions || stmt.gst_on_commission || 0, accountSummary?.country)}</td>
                              <td className="p-3 text-right text-red-600">{formatCurrency(stmt.other_deductions || stmt.commission_amount || 0, accountSummary?.country)}</td>
                              <td className="p-3 text-right text-purple-700" title="Payment-Gateway commission (PhonePe MDR, etc.)">{formatCurrency(stmt.sundry_debtors || 0, accountSummary?.country)}</td>
                              <td className="p-3 text-right text-green-600">{formatCurrency(stmt.net_payout, accountSummary?.country)}</td>
                              <td className="p-3 text-right">{stmt.order_count}</td>
                              <td className="p-3 text-sm text-gray-500 max-w-[150px] truncate" title={stmt.original_filename}>
                                {stmt.original_filename || '-'}
                              </td>
                              <td className="p-3 text-center">
                                <Button 
                                  variant="ghost" size="sm" 
                                  className="text-red-500 hover:text-red-700"
                                  onClick={() => handleDeleteCommission(stmt.commission_id)}
                                  data-testid={`delete-commission-${stmt.commission_id}`}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {/* Commission Summary Cards */}
              <div className="grid md:grid-cols-4 gap-4">
                <Card className="bg-orange-50">
                  <CardContent className="p-4">
                    <p className="text-sm text-orange-600">Aggregator Deductions</p>
                    <p className="text-xl font-bold text-orange-800">
                      {formatCurrency(accountSummary.commissions.aggregator_total, accountSummary.country)}
                    </p>
                    <p className="text-xs text-orange-500 mt-1">Swiggy + Zomato + DoorDash</p>
                  </CardContent>
                </Card>
                <Card className="bg-blue-50">
                  <CardContent className="p-4">
                    <p className="text-sm text-blue-600">Payment Mode Deductions</p>
                    <p className="text-xl font-bold text-blue-800">
                      {formatCurrency(accountSummary.commissions.card_total, accountSummary.country)}
                    </p>
                    <p className="text-xs text-blue-500 mt-1">Cards + PhonePe</p>
                  </CardContent>
                </Card>
                <Card className="bg-purple-50" data-testid="payment-gateway-deductions-card">
                  <CardContent className="p-4">
                    <p className="text-sm text-purple-700">Payment Gateway Deductions</p>
                    <p className="text-xl font-bold text-purple-900">
                      {formatCurrency(accountSummary.commissions.payment_gateway_total || 0, accountSummary.country)}
                    </p>
                    <p className="text-xs text-purple-500 mt-1">PhonePe MDR + Cards MDR</p>
                  </CardContent>
                </Card>
                {accountSummary.country === 'Australia' && (
                  <Card className="bg-purple-50">
                    <CardContent className="p-4">
                      <p className="text-sm text-purple-600">Commission GST (10%)</p>
                      <p className="text-xl font-bold text-purple-800">
                        {formatCurrency(accountSummary.commissions.commission_gst, accountSummary.country)}
                      </p>
                    </CardContent>
                  </Card>
                )}
                <Card className="bg-red-50">
                  <CardContent className="p-4">
                    <p className="text-sm text-red-600">Total Deductions (incl. GST)</p>
                    <p className="text-xl font-bold text-red-800" data-testid="commissions-total-deductions">
                      {(() => {
                        if (accountSummary.share_calculation?.total_deductions !== undefined) {
                          return formatCurrency(accountSummary.share_calculation.total_deductions, accountSummary.country);
                        }
                        const includeGst = accountSummary.share_calculation?.include_gst_in_revenue
                          || accountSummary.operational_sustainability?.include_gst_in_revenue;
                        const gstTerm = includeGst ? 0 : (accountSummary.financial_summary?.sales_gst || 0);
                        return formatCurrency((accountSummary.commissions?.total || 0) + gstTerm, accountSummary.country);
                      })()}
                    </p>
                    <p className="text-[10px] text-red-700 mt-1" data-testid="commissions-total-deductions-label">
                      {accountSummary.share_calculation?.total_deductions_label
                        || "Commissions + GST on Eligible Sales"}
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Dedicated PhonePe Settlement Card */}
              {accountSummary.commissions?.phonepe?.gross > 0 && (
                <Card className="border-purple-300 border-2" data-testid="phonepe-settlement-card">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Badge className="bg-purple-100 text-purple-800">PhonePe</Badge>
                      <span className="text-purple-900">Payment Gateway Settlement</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
                    <div>
                      <p className="text-[11px] uppercase text-stone-500 tracking-wider">Gross</p>
                      <p className="font-bold text-stone-800">{formatCurrency(accountSummary.commissions.phonepe.gross, accountSummary.country)}</p>
                    </div>
                    <div>
                      <p className="text-[11px] uppercase text-stone-500 tracking-wider">PhonePe Commission</p>
                      <p className="font-bold text-purple-800">{formatCurrency(accountSummary.commissions.phonepe.pg_commission, accountSummary.country)}</p>
                    </div>
                    <div>
                      <p className="text-[11px] uppercase text-stone-500 tracking-wider">GST on Commission</p>
                      <p className="font-bold text-orange-700">{formatCurrency(accountSummary.commissions.phonepe.gst_on_commission, accountSummary.country)}</p>
                    </div>
                    <div>
                      <p className="text-[11px] uppercase text-stone-500 tracking-wider">Net Settlement</p>
                      <p className="font-bold text-emerald-700">{formatCurrency(accountSummary.commissions.phonepe.net_settlement, accountSummary.country)}</p>
                    </div>
                    <div>
                      <p className="text-[11px] uppercase text-stone-500 tracking-wider">Transactions</p>
                      <p className="font-bold text-stone-800">{accountSummary.commissions.phonepe.txn_count || 0}</p>
                      {accountSummary.commissions.phonepe.settlement_date && (
                        <p className="text-[10px] text-stone-500">{accountSummary.commissions.phonepe.settlement_date}</p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>
            {/* Revenue/Profit Share Tab */}
            <TabsContent value="share" className="space-y-4">
              {/* WC Gating Banner for Revenue/Profit Share */}
              {accountSummary.share_calculation?.wc_gated && (
                <div className="p-4 bg-red-50 border-2 border-red-300 rounded-lg" data-testid="share-wc-closed-banner">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-red-800">
                        {accountSummary.share_calculation.type === 'profit_share' ? 'Profit' : 'Revenue'} Share CLOSED
                      </p>
                      <p className="text-sm text-red-700">
                        Working Capital is below 50% of Security Deposit ({formatCurrency(accountSummary.financial_summary.wc_standing?.initial_security_deposit * 0.5, accountSummary.country)}).
                        Current WC: {formatCurrency(accountSummary.financial_summary.working_capital_available, accountSummary.country)} ({accountSummary.financial_summary.wc_standing?.wc_percentage?.toFixed(0)}%).
                        Profits will refill WC first. Share resumes once WC is restored to initial deposit.
                      </p>
                    </div>
                  </div>
                </div>
              )}
              {accountSummary.share_calculation?.wc_status === "restoring" && !accountSummary.share_calculation?.wc_gated && (
                <div className="p-4 bg-amber-50 border border-amber-300 rounded-lg">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-amber-600" />
                    <p className="text-sm text-amber-800">
                      <strong>WC Restoring:</strong> Working Capital is below initial amount. Profits first restore WC, then {accountSummary.share_calculation.type === 'profit_share' ? 'profit' : 'revenue'} share applies.
                    </p>
                  </div>
                </div>
              )}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2" data-testid="share-calc-heading">
                    {/* Heading + Payout Model badge — both sourced from the Financial Engine. */}
                    <span>
                      {accountSummary.section_heading
                        ? `${accountSummary.section_heading.charAt(0)}${accountSummary.section_heading.slice(1).toLowerCase()} (${accountSummary.share_calculation.franchise_owner?.percentage || 15}/${accountSummary.share_calculation.purnabramha?.percentage || 85} Split)`
                        : accountSummary.share_calculation.type === 'profit_share'
                        ? `Profit Share Calculation (${accountSummary.share_calculation.franchise_owner?.percentage || 80}/${accountSummary.share_calculation.purnabramha?.percentage || 20} Split)`
                        : `Revenue Share Calculation (${accountSummary.share_calculation.franchise_owner?.percentage || 15}/${accountSummary.share_calculation.purnabramha?.percentage || 85} Split)`}
                    </span>
                    <Badge
                      variant="outline"
                      data-testid="payout-model-badge"
                      className={accountSummary.payout_model === 'profit_share'
                        ? 'border-blue-300 text-blue-700 bg-blue-50'
                        : 'border-emerald-300 text-emerald-700 bg-emerald-50'}>
                      Payout Model: {accountSummary.payout_model === 'profit_share' ? 'Profit Share' : 'Revenue Share'}
                    </Badge>
                  </CardTitle>
                  <CardDescription>
                    {accountSummary.payout_model === 'profit_share'
                      ? `${accountSummary.country}: Profit share model — owner / company split on Profit Share Base (Sales − Comm − Expenses − Adjustments).`
                      : `${accountSummary.country}: Revenue share model — owner / company split on Revenue Share Base (Sales − Comm − GST).`}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    {/* Step-by-step Calculation Breakdown for India */}
                    {accountSummary.country === 'India' && (
                      <div className="p-5 bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl border border-gray-200 space-y-3" data-testid="india-calculation-breakdown">
                        <h4 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                          <Calculator className="w-4 h-4 text-gray-600" />
                          Revenue Calculation Breakdown
                        </h4>

                        {/* Step 1: Total Sales */}
                        <div className="flex justify-between text-sm items-center">
                          <span className="text-gray-700 font-medium">Total Sales</span>
                          <span className="font-semibold text-gray-900">{formatCurrency(accountSummary.financial_summary.total_sales, accountSummary.country)}</span>
                        </div>

                        {/* Step 2: Less GST on Eligible Sales (5% inclusive) — same formula as PIB */}
                        {accountSummary.financial_summary.sales_gst > 0 && (
                          <div className="flex justify-between text-sm items-center text-red-600">
                            <span className="pl-4">Less: GST on Eligible Sales (5% incl.)</span>
                            <span className="font-medium">- {formatCurrency(accountSummary.financial_summary.sales_gst, accountSummary.country)}</span>
                          </div>
                        )}

                        {/* Step 3: Less Commissions */}
                        <div className="flex justify-between text-sm items-center text-red-600">
                          <span className="pl-4">Less: Total Commissions (Swiggy, Zomato, Cards)</span>
                          <span className="font-medium">- {formatCurrency(accountSummary.financial_summary.total_commissions, accountSummary.country)}</span>
                        </div>

                        {/* Divider */}
                        <div className="border-t-2 border-dashed border-gray-300 my-1" />

                        {/* Result: Revenue Share Base (India) */}
                        <div className="flex justify-between items-center bg-sky-50 border-2 border-sky-300 rounded-lg px-4 py-3 shadow-sm">
                          <span className="text-sky-800 font-bold text-base">⭐ = Revenue Share Base (Base for Split)</span>
                          <span className="text-sky-900 font-extrabold text-xl" data-testid="india-revenue-share-base" title="The amount available for owner/company percentage sharing after deducting GST and commissions from sales.">
                            {formatCurrency(accountSummary.operational_sustainability?.revenue_share_base ?? (accountSummary.financial_summary.net_revenue - (accountSummary.financial_summary.sales_gst || 0)), accountSummary.country)}
                          </span>
                        </div>

                        {/* GST Info Note */}
                        <div className="flex items-start gap-2 mt-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                          <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
                          <p className="text-xs text-amber-800">
                            <strong>Revenue Share GST:</strong> 18% GST (CGST 9% + SGST 9%) is applicable on revenue share invoicing. For outside India, GST is 10%.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Calculation Breakdown for Australia */}
                    {accountSummary.country === 'Australia' && (
                      <div className="p-5 bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl border border-gray-200 space-y-3" data-testid="australia-calculation-breakdown">
                        <h4 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                          <Calculator className="w-4 h-4 text-gray-600" />
                          Profit Calculation Breakdown
                        </h4>
                        <div className="flex justify-between text-sm">
                          <span>Total Sales (GST Inclusive)</span>
                          <span>{formatCurrency(accountSummary.financial_summary.total_sales, accountSummary.country)}</span>
                        </div>
                        <div className="flex justify-between text-sm text-red-600">
                          <span>Less: Sales GST (10%)</span>
                          <span>-{formatCurrency(accountSummary.financial_summary.sales_gst, accountSummary.country)}</span>
                        </div>
                        <div className="flex justify-between text-sm text-red-600">
                          <span>Less: Commission</span>
                          <span>-{formatCurrency(accountSummary.financial_summary.total_commissions, accountSummary.country)}</span>
                        </div>
                        <div className="flex justify-between text-sm text-red-600">
                          <span className="pl-4">Less: Commission GST (10%)</span>
                          <span>-{formatCurrency(accountSummary.financial_summary.commission_gst, accountSummary.country)}</span>
                        </div>
                        <div className="border-t-2 border-dashed border-gray-300 my-1" />
                        <div className="flex justify-between items-center bg-green-50 border border-green-200 rounded-lg px-4 py-2">
                          <span className="text-green-800 font-semibold">= Net Revenue (Sales − Deductions)</span>
                          <span className="text-green-900 font-bold">{formatCurrency(accountSummary.financial_summary.net_revenue, accountSummary.country)}</span>
                        </div>
                        <div className="flex justify-between text-sm text-red-600">
                          <span>Less: Total Expenses</span>
                          <span>-{formatCurrency(accountSummary.financial_summary.total_expenses, accountSummary.country)}</span>
                        </div>
                        <div className="border-t-2 border-dashed border-gray-300 my-1" />
                        <div className="flex justify-between items-center bg-emerald-50 border border-emerald-300 rounded-lg px-4 py-3">
                          <span className="text-emerald-800 font-bold">= Profitability (Base for 80/20 Split)</span>
                          <span className="text-emerald-900 font-bold text-lg" data-testid="aus-profitability">{formatCurrency(accountSummary.financial_summary.profitability ?? 0, accountSummary.country)}</span>
                        </div>
                        <div className="flex items-start gap-2 mt-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                          <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
                          <p className="text-xs text-amber-800">
                            <strong>Profit Share GST:</strong> 10% GST is applied on Purnabramha's 20% profit share for Australia.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Base Amount — model-aware (Payout Model from Franchise Management). */}
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600" data-testid="share-split-base-label">
                          {(() => {
                            const isProfit = accountSummary.payout_model === 'profit_share'
                              || accountSummary.share_calculation.type === 'profit_share';
                            const label = accountSummary.base_label
                              || (isProfit ? "Profit Share Base" : "Revenue Share Base");
                            const fp = accountSummary.share_calculation.franchise_owner?.percentage || (isProfit ? 80 : 15);
                            const pp = accountSummary.share_calculation.purnabramha?.percentage || (isProfit ? 20 : 85);
                            // Under WC Protection the backend already encodes
                            // the gating in the label (e.g. "Operational
                            // Balance (Base under WC Protection)") — don't
                            // double-up the "(Base for X/Y Split)" suffix.
                            const suffix = /Base/i.test(label) && /Protection/i.test(label)
                              ? ` — ${fp}/${pp} Split applied`
                              : ` (Base for ${fp}/${pp} Split)`;
                            return `⭐ ${label}${suffix}`;
                          })()}
                        </span>
                        <span className="text-xl font-bold" data-testid="share-split-base-value">
                          {formatCurrency(accountSummary.share_calculation.net_profit_or_sales, accountSummary.country)}
                        </span>
                      </div>
                    </div>

                    {/* Share Split Cards */}
                    <div className="grid md:grid-cols-2 gap-4">
                      {/* Franchise Owner Share */}
                      <Card className="border-2 border-green-200 bg-green-50">
                        <CardContent className="p-4">
                          <div className="flex items-center gap-2 mb-3">
                            <Building2 className="w-5 h-5 text-green-600" />
                            <h4 className="font-medium text-green-800" data-testid="franchise-owner-share-label">
                              Franchise Owner {accountSummary.share_calculation?.type === 'profit_share' ? 'Profit Share' : 'Revenue Share'}
                            </h4>
                          </div>
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span className="text-green-700">Percentage</span>
                              <Badge className="bg-green-600 text-white">{accountSummary.share_calculation.franchise_owner?.percentage || 15}%</Badge>
                            </div>
                            <div className="flex justify-between text-lg">
                              <span className="text-green-700">Amount</span>
                              <span className="font-bold text-green-800">
                                {formatCurrency(accountSummary.share_calculation.franchise_owner?.amount || 0, accountSummary.country)}
                              </span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>

                      {/* Purnabramha Share */}
                      <Card className="border-2 border-orange-200 bg-orange-50">
                        <CardContent className="p-4">
                          <div className="flex items-center gap-2 mb-3">
                            <DollarSign className="w-5 h-5 text-orange-600" />
                            <h4 className="font-medium text-orange-800" data-testid="entity-share-label">
                              {entityName(accountSummary.country)} {accountSummary.share_calculation?.type === 'profit_share' ? 'Profit Share' : 'Revenue Share'}
                            </h4>
                          </div>
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span className="text-orange-700">Percentage</span>
                              <Badge className="bg-orange-600 text-white">{accountSummary.share_calculation.purnabramha?.percentage || 85}%</Badge>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-orange-700">Base Amount</span>
                              <span className="font-medium">
                                {formatCurrency(accountSummary.share_calculation.purnabramha?.base_amount || 0, accountSummary.country)}
                              </span>
                            </div>
                            
                            <hr className="border-orange-200 my-2" />
                            
                            {accountSummary.country === 'India' ? (
                              <div className="text-xs text-orange-500 italic p-2 bg-orange-50 rounded">
                                <span>Revenue Share GST (18%): {formatCurrency(accountSummary.share_calculation.purnabramha?.gst_amount || 0, accountSummary.country)}</span>
                                <span className="block text-orange-400 mt-0.5">(CGST 9%: {formatCurrency(accountSummary.share_calculation.purnabramha?.cgst || 0, accountSummary.country)} + SGST 9%: {formatCurrency(accountSummary.share_calculation.purnabramha?.sgst || 0, accountSummary.country)})</span>
                                <span className="block text-orange-400 mt-0.5">GST not included in total payable</span>
                              </div>
                            ) : (
                              <div className="flex justify-between text-sm">
                                <span className="text-orange-600">+ GST (10%)</span>
                                <span>{formatCurrency(accountSummary.share_calculation.purnabramha?.gst_amount || 0, accountSummary.country)}</span>
                              </div>
                            )}
                            
                            <hr className="border-orange-200 my-2" />
                            
                            <div className="flex justify-between text-lg font-bold">
                              <span className="text-orange-800">
                                Total {accountSummary.share_calculation?.type === 'profit_share' ? 'Profit Share' : 'Revenue Share'} Payable
                              </span>
                              <span className="text-orange-900">
                                {formatCurrency(accountSummary.share_calculation.purnabramha?.total_payable || 0, accountSummary.country)}
                              </span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </div>

                    {/* Tax Rules Info */}
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <h4 className="font-medium text-blue-800 mb-2">Tax Rules Applied ({accountSummary.tax_rules.country})</h4>
                      <ul className="text-sm text-blue-700 space-y-1">
                        <li>
                          Sales GST: {accountSummary.tax_rules.sales_gst_rate}% 
                          ({accountSummary.tax_rules.sales_gst_treatment === 'inclusive' ? 'Inclusive' : 'Exclusive'})
                        </li>
                        <li>
                          {accountSummary.share_calculation.type === 'profit_share' ? 'Profit' : 'Revenue'} Share GST: {accountSummary.tax_rules.share_gst_rate}%
                          {accountSummary.country === 'India' && ' (CGST 9% + SGST 9%)'}
                        </li>
                      </ul>
                    </div>

                    {/* Working Capital Standing */}
                    {accountSummary.financial_summary.wc_standing && (
                      <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                        <h4 className="font-medium text-amber-800 mb-2">Working Capital Standing ({accountSummary.period})</h4>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <span className="text-gray-600">Initial Deposit:</span>
                          <span className="text-right font-medium">{formatCurrency(accountSummary.financial_summary.wc_standing.initial_security_deposit, accountSummary.country)}</span>
                          <span className="text-gray-600">Opening WC:</span>
                          <span className="text-right font-medium">{formatCurrency(accountSummary.financial_summary.wc_standing.opening_wc, accountSummary.country)}</span>
                          <span className="text-gray-600">This Month P&L:</span>
                          <span className={`text-right font-medium ${accountSummary.financial_summary.wc_standing.this_month_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatCurrency(accountSummary.financial_summary.wc_standing.this_month_pnl, accountSummary.country)}
                          </span>
                          <span className="text-gray-700 font-semibold border-t pt-1">Closing WC:</span>
                          <span className={`text-right font-bold border-t pt-1 ${accountSummary.financial_summary.wc_standing.closing_wc >= accountSummary.financial_summary.wc_standing.initial_security_deposit ? 'text-green-700' : accountSummary.financial_summary.wc_standing.closing_wc > 0 ? 'text-amber-700' : 'text-red-700'}`}>
                            {formatCurrency(accountSummary.financial_summary.wc_standing.closing_wc, accountSummary.country)}
                          </span>
                          {accountSummary.financial_summary.wc_standing.total_effective_loans > 0 && (
                            <>
                              <span className="text-gray-600">Total Loans:</span>
                              <span className="text-right font-medium text-red-600">{formatCurrency(accountSummary.financial_summary.wc_standing.total_effective_loans, accountSummary.country)}</span>
                            </>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Cash Inflows row — Other Income + Loans Taken + Loans Given (always visible alongside WC) */}
                    <div className="p-4 rounded-lg border-2 border-emerald-200 bg-emerald-50/50" data-testid="ot-other-income-block">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <h4 className="font-semibold text-emerald-800">Other Income</h4>
                          <p className="text-xs text-emerald-700/80">
                            Non-operating cash. Stays out of Sales/P&amp;L/MG; <strong>adjusts next-month Opening WC</strong>.
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-emerald-700">
                            {formatCurrency(accountSummary.other_income?.total || 0, accountSummary.country)}
                          </span>
                          {(session?.is_super_admin || session?.is_admin || session?.role_key === "accountant" || session?.role_key === "accounts") && (
                            <Button size="sm" variant="outline"
                              className="border-emerald-500 text-emerald-700 hover:bg-emerald-50 h-8"
                              onClick={() => setShowOtherIncomeModal(true)}
                              data-testid="add-other-income-btn-top">
                              <Plus className="w-3.5 h-3.5 mr-1" /> Add
                            </Button>
                          )}
                        </div>
                      </div>
                      {(accountSummary.other_income?.rows || []).length === 0 ? (
                        <p className="text-xs text-emerald-700/70 italic px-3 py-2">No Other Income entries this period.</p>
                      ) : (
                        <div className="space-y-1.5">
                          {accountSummary.other_income.rows.map((r) => (
                            <div key={r.income_id} className="flex justify-between items-center px-3 py-1.5 bg-white rounded text-sm" data-testid={`oi-row-top-${r.income_id}`}>
                              <span className="flex items-center gap-2 flex-1 min-w-0">
                                <span className="text-[10px] uppercase tracking-wide text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded shrink-0">
                                  {(r.category || "other").replace(/_/g, " ")}
                                </span>
                                <span className="text-muted-foreground shrink-0">{r.date}</span>
                                <span className="text-foreground truncate">{r.reason}</span>
                                {r.auto_generated && <span className="text-[9px] text-amber-700 bg-amber-100 px-1 rounded shrink-0">AUTO</span>}
                              </span>
                              <span className="flex items-center gap-2 shrink-0">
                                <span className="font-medium">{formatCurrency(r.amount, accountSummary.country)}</span>
                                {(session?.is_super_admin || session?.is_admin || session?.role_key === "accountant" || session?.role_key === "accounts") && !r.auto_generated && (
                                  <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-rose-600 hover:bg-rose-50"
                                    data-testid={`oi-delete-top-${r.income_id}`}
                                    onClick={async () => {
                                      if (!window.confirm(`Delete Other Income entry of ${formatCurrency(r.amount, accountSummary.country)}?`)) return;
                                      try {
                                        const resp = await fetch(`${API}/api/other-income/delete/${r.income_id}`, {
                                          method: "POST",
                                          headers: { "Content-Type": "application/json" },
                                          body: JSON.stringify({ token: session?.token }),
                                        });
                                        const dd = await resp.json();
                                        if (resp.ok && dd.success) {
                                          toast.success("Deleted");
                                          await fetchAccountSummary();
                                        } else {
                                          toast.error(dd.detail || "Delete failed");
                                        }
                                      } catch { toast.error("Delete failed"); }
                                    }}>
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </Button>
                                )}
                                {r.auto_generated && (
                                  <span className="text-[9px] text-muted-foreground italic shrink-0">linked to loan</span>
                                )}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Loans Taken (borrower view) */}
                    {accountSummary.loans_taken?.total > 0 && (
                      <div className="p-4 rounded-lg border-2 border-amber-200 bg-amber-50/50" data-testid="ot-loans-taken-block">
                        <div className="flex items-center justify-between mb-3">
                          <div>
                            <h4 className="font-semibold text-amber-800">Loans Taken (this center)</h4>
                            <p className="text-xs text-amber-700/80">Auto-added to Other Income above.</p>
                          </div>
                          <div className="text-right text-xs">
                            <div><span className="text-muted-foreground">Total:</span> <span className="font-bold text-amber-700">{formatCurrency(accountSummary.loans_taken.total, accountSummary.country)}</span></div>
                            <div><span className="text-muted-foreground">Repaid:</span> <span className="text-emerald-700 font-medium">{formatCurrency(accountSummary.loans_taken.repaid || 0, accountSummary.country)}</span></div>
                            <div><span className="text-muted-foreground">Outstanding:</span> <span className="text-rose-700 font-bold">{formatCurrency(accountSummary.loans_taken.outstanding || 0, accountSummary.country)}</span></div>
                          </div>
                        </div>
                        <div className="space-y-1.5">
                          {(accountSummary.loans_taken.rows || []).map((r) => (
                            <div key={r.loan_id} className="flex justify-between items-center px-3 py-1.5 bg-white rounded text-sm">
                              <span className="flex items-center gap-2 flex-1 min-w-0">
                                <span className="text-[10px] uppercase tracking-wide text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded shrink-0">From {r.source_center || "Ext"}</span>
                                <span className="text-muted-foreground shrink-0">{r.loan_date}</span>
                                <span className="text-foreground truncate">{r.reason}</span>
                                {r.status === "fully_repaid" && <span className="text-[9px] text-emerald-700 bg-emerald-100 px-1 rounded shrink-0">FULLY REPAID</span>}
                                {r.status === "partial" && <span className="text-[9px] text-amber-700 bg-amber-100 px-1 rounded shrink-0">PARTIAL</span>}
                                {(!r.status || r.status === "outstanding" || r.status === "active") && <span className="text-[9px] text-rose-700 bg-rose-100 px-1 rounded shrink-0">OUTSTANDING</span>}
                              </span>
                              <span className="flex items-center gap-3 shrink-0 text-xs">
                                <span><span className="text-muted-foreground">Amt:</span> <span className="font-medium">{formatCurrency(r.amount, accountSummary.country)}</span></span>
                                <span><span className="text-muted-foreground">Repaid:</span> <span className="text-emerald-700">{formatCurrency(r.repaid, accountSummary.country)}</span></span>
                                <span><span className="text-muted-foreground">Out:</span> <span className="text-rose-700 font-semibold">{formatCurrency(r.outstanding, accountSummary.country)}</span></span>
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Loans Given (lender view, anonymised) */}
                    {accountSummary.loans_given?.total > 0 && (
                      <div className="p-4 rounded-lg border-2 border-rose-200 bg-rose-50/50" data-testid="ot-loans-given-block">
                        <div className="flex items-center justify-between mb-3">
                          <div>
                            <h4 className="font-semibold text-rose-800">Loan Given to Other Center</h4>
                            <p className="text-xs text-rose-700/80">Tracked in Loan Entries ledger.</p>
                          </div>
                          <div className="text-right text-xs">
                            <div><span className="text-muted-foreground">Total:</span> <span className="font-bold text-rose-700">{formatCurrency(accountSummary.loans_given.total, accountSummary.country)}</span></div>
                            <div><span className="text-muted-foreground">Repaid:</span> <span className="text-emerald-700 font-medium">{formatCurrency(accountSummary.loans_given.repaid || 0, accountSummary.country)}</span></div>
                            <div><span className="text-muted-foreground">Outstanding:</span> <span className="text-rose-700 font-bold">{formatCurrency(accountSummary.loans_given.outstanding || 0, accountSummary.country)}</span></div>
                          </div>
                        </div>
                        <div className="space-y-1.5">
                          {(accountSummary.loans_given.rows || []).map((r) => (
                            <div key={r.loan_id} className="flex justify-between items-center px-3 py-1.5 bg-white rounded text-sm">
                              <span className="flex items-center gap-2 flex-1 min-w-0">
                                <span className="text-[10px] uppercase tracking-wide text-rose-700 bg-rose-100 px-1.5 py-0.5 rounded shrink-0">Loan Given</span>
                                <span className="text-muted-foreground shrink-0">{r.loan_date}</span>
                                <span className="text-foreground truncate">{r.reason}</span>
                                {r.status === "fully_repaid" && <span className="text-[9px] text-emerald-700 bg-emerald-100 px-1 rounded shrink-0">FULLY REPAID</span>}
                                {r.status === "partial" && <span className="text-[9px] text-amber-700 bg-amber-100 px-1 rounded shrink-0">PARTIAL</span>}
                                {(!r.status || r.status === "outstanding" || r.status === "active") && <span className="text-[9px] text-rose-700 bg-rose-100 px-1 rounded shrink-0">OUTSTANDING</span>}
                              </span>
                              <span className="flex items-center gap-3 shrink-0 text-xs">
                                <span><span className="text-muted-foreground">Amt:</span> <span className="font-medium">{formatCurrency(r.amount, accountSummary.country)}</span></span>
                                <span><span className="text-muted-foreground">Repaid:</span> <span className="text-emerald-700">{formatCurrency(r.repaid, accountSummary.country)}</span></span>
                                <span><span className="text-muted-foreground">Out:</span> <span className="text-rose-700 font-semibold">{formatCurrency(r.outstanding, accountSummary.country)}</span></span>
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Reports Tab */}
            <TabsContent value="reports" className="space-y-4" data-testid="reports-tab-content">
              {(() => {
                const linked = !!accountSummary?.franchise?.linked;
                const ReportTile = ({ icon, label, testid, onPreview, onDownload, disabled, comingSoon, tone = 'border-gray-200', accent = 'text-gray-700' }) => (
                  <div className={`rounded-lg border ${tone} bg-white p-3 flex items-center justify-between gap-2`} data-testid={`report-tile-${testid}`}>
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`shrink-0 ${accent}`}>{icon}</span>
                      <span className="text-sm font-medium truncate text-stone-800">{label}</span>
                    </div>
                    <div className="flex gap-1 shrink-0 items-center">
                      {comingSoon ? (
                        <Badge variant="outline" className="text-[10px] text-muted-foreground">Coming Soon</Badge>
                      ) : (
                        <>
                          {onPreview && (
                            <Button size="sm" variant="ghost" className="h-7 w-7 p-0" disabled={disabled}
                                    onClick={onPreview} data-testid={`${testid}-preview-btn`} title="Preview">
                              <Eye className="w-3.5 h-3.5" />
                            </Button>
                          )}
                          {onDownload && (
                            <Button size="sm" variant="ghost" className="h-7 w-7 p-0" disabled={disabled}
                                    onClick={onDownload} data-testid={`${testid}-download-btn`} title="Download">
                              <Download className="w-3.5 h-3.5" />
                            </Button>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                );

                const Section = ({ title, color, children }) => (
                  <Card className={`border-l-4 ${color}`}>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base">{title}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-2">{children}</div>
                    </CardContent>
                  </Card>
                );

                return (
                  <>
                    <Card className="bg-gradient-to-r from-stone-50 to-stone-100 border-stone-200">
                      <CardContent className="p-4">
                        <p className="text-sm text-stone-700">
                          All reports for <strong>{selectedCenter}</strong> · <strong>{selectedMonth}</strong>.
                          Each report shows only its own purpose. Engine: <Badge variant="outline" className="ml-1">Single Financial Engine</Badge>
                        </p>
                      </CardContent>
                    </Card>

                    {/* Financial Reports */}
                    <Section title="Financial Reports" color="border-blue-500">
                      <ReportTile icon={<FileText className="w-4 h-4" />} label="Profit & Loss"
                                  testid="pnl" accent="text-blue-700" tone="border-blue-200" disabled={!linked}
                                  onDownload={() => downloadReport('pnl')} />
                      <ReportTile icon={<FileSpreadsheet className="w-4 h-4" />} label="Sales Summary"
                                  testid="sales-summary" accent="text-emerald-700" tone="border-emerald-200" disabled={!linked}
                                  onDownload={() => downloadSalesExpenseExcel('month', '', '')} />
                      <ReportTile icon={<FileSpreadsheet className="w-4 h-4" />} label="Expense Summary"
                                  testid="expense-summary" accent="text-amber-700" tone="border-amber-200" disabled={!linked}
                                  onDownload={() => downloadSalesExpenseExcel('month', '', '')} />
                      <ReportTile icon={<Calculator className="w-4 h-4" />} label="GST Summary"
                                  testid="gst-summary" accent="text-green-700" tone="border-green-200"
                                  onPreview={() => openPdfPreview('gst')} onDownload={() => downloadReport('gst')} />
                    </Section>

                    {/* Settlement Reports */}
                    <Section title="Settlement Reports" color="border-sky-500">
                      <ReportTile icon={<FileText className="w-4 h-4" />}
                                  label={accountSummary?.payout_model === 'profit_share' ? 'Profit Share Calculation (PIB)' : 'Revenue Share Calculation (PIB)'}
                                  testid="rev-share-calc" accent="text-sky-700" tone="border-sky-200" disabled={!linked}
                                  onPreview={() => openPibPreview()} onDownload={() => downloadReport('pib')} />
                      <ReportTile icon={<Wallet className="w-4 h-4" />} label="MG Summary"
                                  testid="mg-summary" accent="text-purple-700" tone="border-purple-200" disabled={!linked}
                                  onDownload={() => downloadReport('mg-summary')} />
                      <ReportTile icon={<Wallet className="w-4 h-4" />} label="Payout Summary"
                                  testid="payout-summary" accent="text-indigo-700" tone="border-indigo-200" disabled={!linked}
                                  onDownload={() => downloadReport('payout-summary')} />
                    </Section>

                    {/* Reconciliation Reports */}
                    <Section title="Reconciliation Reports" color="border-orange-500">
                      <ReportTile icon={<Building2 className="w-4 h-4" />} label="Bank Reconciliation"
                                  testid="bank-recon" accent="text-sky-700" tone="border-sky-200"
                                  onPreview={() => openPdfPreview('bank')} onDownload={() => downloadReport('bank')} />
                      <ReportTile icon={<CreditCard className="w-4 h-4" />} label="PhonePe Reconciliation"
                                  testid="phonepe-recon" accent="text-violet-700" tone="border-violet-200"
                                  onDownload={() => downloadReport('phonepe')} />
                      <ReportTile icon={<CreditCard className="w-4 h-4" />} label="Commission Reconciliation"
                                  testid="commission-recon" accent="text-orange-700" tone="border-orange-200"
                                  onPreview={() => openPdfPreview('commission')} onDownload={() => downloadReport('commission')} />
                    </Section>

                    {/* Compliance Reports */}
                    <Section title="Compliance Reports" color="border-rose-500">
                      <ReportTile icon={<Calculator className="w-4 h-4" />} label="GST Paid"
                                  testid="gst-paid" accent="text-green-700" tone="border-green-200"
                                  onDownload={() => downloadReport('gst-paid')} />
                      <ReportTile icon={<FileBox className="w-4 h-4" />} label="Missing Bills"
                                  testid="missing-bills" accent="text-rose-700" tone="border-rose-200"
                                  onDownload={() => downloadReport('missing-bills')} />
                      <ReportTile icon={<FileBox className="w-4 h-4" />} label="Expense Attachments (ZIP)"
                                  testid="expense-attachments" accent="text-amber-700" tone="border-amber-200"
                                  onDownload={() => downloadReport('expense-attachments')} />
                    </Section>

                    <p className="text-[11px] text-muted-foreground italic px-1">
                      Each report shows only its own purpose. Email Pack &amp; one-click ZIP bundles live under <strong>Bundles &amp; Exports</strong>.
                    </p>
                  </>
                );
              })()}
            </TabsContent>

            {/* Ledgers Tab — CA-ready books of accounts */}
            <TabsContent value="ledgers" className="space-y-4">
              <LedgersTab session={session} selectedCenter={selectedCenter} country={country} />
            </TabsContent>
            {/* Financial Insights Tab — analytics, ratios, trends, AI summary */}
            <TabsContent value="insights" className="space-y-4">
              <FinancialInsightsTab centersList={centers} />
            </TabsContent>
            {/* Financial Health Tab — profitability intelligence (11-section module) */}
            <TabsContent value="health" className="space-y-4">
              <FinancialHealth center={selectedCenter} />
            </TabsContent>
            {/* Expense Adjustments Tab — prepaid / advance / future-month carve */}
            <TabsContent value="adjustments" className="space-y-4">
              {/* GST Revenue Treatment toggle — per-center per-month */}
              <GSTRevenueTreatmentCard
                token={token}
                center={selectedCenter}
                month={selectedMonth}
                summary={accountSummary}
                onChanged={fetchAccountSummary}
              />
              <ExpenseAdjustmentsTab
                center={selectedCenter}
                month={selectedMonth}
                currencySymbol={accountSummary?.country === 'Australia' ? 'AUD ' : '₹'}
                summary={accountSummary}
                onChanged={fetchAccountSummary}
              />
            </TabsContent>

            {/* MG & Payout Tab */}
            <TabsContent value="mg-payout" className="space-y-4">
              {/* Protection Mode Banner */}
              {accountSummary.payout?.protection_mode && (
                <div className="p-4 bg-red-50 border-2 border-red-300 rounded-lg" data-testid="payout-protection-banner">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-red-800">Protection Mode Active - MG Blocked</p>
                      <p className="text-sm text-red-700">
                        Working Capital is at {accountSummary.working_capital_status?.wc_percentage?.toFixed(0)}% of initial deposit (below 50% threshold).
                        MG payouts are blocked. Revenue share calculated on Operational Balance only. Remaining funds directed to WC recovery.
                      </p>
                    </div>
                  </div>
                </div>
              )}
              {/* Overseas Profit Share Panel — replaces MG for non-India centers */}
              {accountSummary.country !== 'India' && accountSummary.overseas_share && (
                <Card className="border-2 border-emerald-300" data-testid="overseas-profit-share">
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Wallet className="w-5 h-5 text-emerald-700" />
                      Overseas Profit Share & MFPL Royalty
                    </CardTitle>
                    <CardDescription>
                      Fixed 80/20 split on Eligible Profit (Sales − GST − Commission − Commission GST − Expenses). 5% MFPL royalty accrued on Net Sales as a payable liability.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="p-4 bg-emerald-50 rounded-lg space-y-2">
                        <p className="text-sm font-medium text-emerald-700">Eligible Profit (this month)</p>
                        <p className="text-3xl font-bold text-emerald-800" data-testid="overseas-eligible-profit">
                          {formatCurrency(accountSummary.overseas_share.eligible_profit, accountSummary.country)}
                        </p>
                        <p className="text-xs text-emerald-600">= Sales − GST − Commission − Commission GST − Expenses</p>
                      </div>
                      <div className="p-4 bg-sky-50 rounded-lg space-y-2">
                        <p className="text-sm font-medium text-sky-700">Eligible Revenue (Net Sales)</p>
                        <p className="text-3xl font-bold text-sky-800" data-testid="overseas-eligible-revenue">
                          {formatCurrency(accountSummary.overseas_share.eligible_revenue, accountSummary.country)}
                        </p>
                        <p className="text-xs text-sky-600">= Sales − GST (basis for 5% MFPL royalty)</p>
                      </div>
                    </div>

                    <div className="grid md:grid-cols-3 gap-3">
                      <Card className="border-2 border-green-400 bg-green-50">
                        <CardContent className="p-4 text-center">
                          <p className="text-xs text-gray-600">Franchise Owner ({accountSummary.overseas_share.owner_pct}%)</p>
                          <p className="text-2xl font-bold text-green-700" data-testid="overseas-owner-share">
                            {formatCurrency(accountSummary.overseas_share.owner_share, accountSummary.country)}
                          </p>
                          <Badge className="mt-1 bg-green-600">Payable</Badge>
                        </CardContent>
                      </Card>
                      <Card className="border-2 border-indigo-400 bg-indigo-50">
                        <CardContent className="p-4 text-center">
                          <p className="text-xs text-gray-600">{entityName(accountSummary.country)} ({accountSummary.overseas_share.franchisor_pct}%)</p>
                          <p className="text-2xl font-bold text-indigo-700" data-testid="overseas-franchisor-share">
                            {formatCurrency(accountSummary.overseas_share.franchisor_share, accountSummary.country)}
                          </p>
                          <Badge className="mt-1 bg-indigo-600">Franchisor</Badge>
                        </CardContent>
                      </Card>
                      <Card className="border-2 border-amber-400 bg-amber-50">
                        <CardContent className="p-4 text-center">
                          <p className="text-xs text-gray-600">MFPL Royalty ({accountSummary.overseas_share.mfpl_royalty_pct}%)</p>
                          <p className="text-2xl font-bold text-amber-700" data-testid="overseas-mfpl-monthly">
                            {formatCurrency(accountSummary.overseas_share.mfpl_royalty, accountSummary.country)}
                          </p>
                          <Badge className="mt-1 bg-amber-600">Accrued (not paid)</Badge>
                        </CardContent>
                      </Card>
                    </div>

                    {accountSummary.mfpl_royalty && accountSummary.mfpl_royalty.applicable && (
                      <div className="p-4 bg-amber-50 border border-amber-300 rounded-lg" data-testid="mfpl-cumulative">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div>
                            <p className="text-sm font-semibold text-amber-900">MFPL Liability Outstanding (cumulative)</p>
                            <p className="text-xs text-amber-700">5% royalty accrued across {(accountSummary.mfpl_royalty.monthly || []).length} months. Not yet paid.</p>
                          </div>
                          <p className="text-2xl font-bold text-amber-800" data-testid="mfpl-outstanding-amount">
                            {formatCurrency(accountSummary.mfpl_royalty.outstanding_mfpl, accountSummary.country)}
                          </p>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* MG Calculation Card — India only */}
              {accountSummary.country === 'India' && accountSummary.mg_calculation && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Calculator className="w-5 h-5" />
                      Minimum Guarantee (MG) Calculation
                    </CardTitle>
                    <CardDescription>
                      MG = EMI on Net Investment @ {accountSummary.mg_calculation.interest_rate}% for {accountSummary.mg_calculation.tenure_years} years
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid md:grid-cols-2 gap-6">
                      <div className="space-y-3">
                        <h4 className="font-medium text-gray-600">Investment Breakdown</h4>
                        <div className="p-4 bg-gray-50 rounded-lg space-y-2">
                          <div className="flex justify-between text-sm">
                            <span>Total Investment</span>
                            <span className="font-medium">{formatCurrency(accountSummary.mg_calculation.total_investment, accountSummary.country)}</span>
                          </div>
                          <hr />
                          <div className="text-sm text-gray-500">Deductions:</div>
                          <div className="flex justify-between text-sm">
                            <span className="pl-2">Shop Rent Deposit</span>
                            <span className="text-red-600">-{formatCurrency(accountSummary.mg_calculation.deductions?.shop_rent_deposit || 0, accountSummary.country)}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="pl-2">Staff Travel</span>
                            <span className="text-red-600">-{formatCurrency(accountSummary.mg_calculation.deductions?.staff_traveling_expense || 0, accountSummary.country)}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="pl-2">First Salary</span>
                            <span className="text-red-600">-{formatCurrency(accountSummary.mg_calculation.deductions?.first_salary || 0, accountSummary.country)}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="pl-2">First Shop Rent</span>
                            <span className="text-red-600">-{formatCurrency(accountSummary.mg_calculation.deductions?.first_shop_rent || 0, accountSummary.country)}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="pl-2">Working Capital</span>
                            <span className="text-red-600">-{formatCurrency(accountSummary.mg_calculation.deductions?.working_capital || 0, accountSummary.country)}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="pl-2">Franchise Fee</span>
                            <span className="text-red-600">-{formatCurrency(accountSummary.mg_calculation.deductions?.franchise_fee || 0, accountSummary.country)}</span>
                          </div>
                          <hr />
                          <div className="flex justify-between text-sm font-medium">
                            <span>Total Deductions</span>
                            <span className="text-red-600">-{formatCurrency(accountSummary.mg_calculation.total_deductions, accountSummary.country)}</span>
                          </div>
                          <div className="flex justify-between text-lg font-bold border-t-2 pt-2 mt-2">
                            <span>Net Investment</span>
                            <span className="text-green-600">{formatCurrency(accountSummary.mg_calculation.net_investment, accountSummary.country)}</span>
                          </div>
                        </div>
                      </div>
                      <div className="space-y-3">
                        <h4 className="font-medium text-gray-600">Monthly MG (EMI)</h4>
                        <div className="p-6 bg-purple-50 rounded-lg text-center">
                          <p className="text-sm text-purple-600 mb-2">Minimum Guarantee per Month</p>
                          <p className="text-4xl font-bold text-purple-800">
                            {formatCurrency(accountSummary.mg_calculation.monthly_mg, accountSummary.country)}
                          </p>
                          <p className="text-xs text-purple-500 mt-2">
                            @ {accountSummary.mg_calculation.interest_rate}% p.a. for {accountSummary.mg_calculation.tenure_years} years
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* 5. Operational Sustainability Check */}
              {accountSummary.operational_sustainability && (
                <Card className="border-2 border-slate-300" data-testid="ops-sustainability">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Shield className="w-5 h-5 text-slate-700" />
                      Operational Sustainability Check
                    </CardTitle>
                    <CardDescription>Operational Balance = Sales − Expenses − Commissions. GST is booked as a liability and paid as an expense in the following month (M+1).</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                      <div className="p-3 bg-blue-50 rounded text-center">
                        <p className="text-xs text-gray-500">Total Sales</p>
                        <p className="text-lg font-bold text-blue-700">{formatCurrency(accountSummary.operational_sustainability.total_sales, accountSummary.country)}</p>
                      </div>
                      <div className="p-3 bg-red-50 rounded text-center">
                        <p className="text-xs text-gray-500">Total Expenses</p>
                        <p className="text-lg font-bold text-red-600">({formatCurrency(accountSummary.operational_sustainability.total_expenses, accountSummary.country)})</p>
                      </div>
                      <div className="p-3 bg-orange-50 rounded text-center">
                        <p className="text-xs text-gray-500">Total Commission</p>
                        <p className="text-lg font-bold text-orange-600">({formatCurrency(accountSummary.operational_sustainability.total_commissions, accountSummary.country)})</p>
                      </div>
                      <div className="p-3 bg-amber-50 rounded text-center" title="Memo only — paid as expense in M+1">
                        <p className="text-xs text-gray-500">GST <span className="text-[10px]">(memo, paid M+1)</span></p>
                        <p className="text-lg font-bold text-amber-600">{formatCurrency(accountSummary.operational_sustainability.gst_on_sales, accountSummary.country)}</p>
                      </div>
                      <div className={`p-3 rounded text-center ${accountSummary.operational_sustainability.is_positive ? 'bg-green-50' : 'bg-red-100'}`}>
                        <p className="text-xs text-gray-500">Operational Balance</p>
                        <p className={`text-xl font-bold ${accountSummary.operational_sustainability.is_positive ? 'text-green-700' : 'text-red-700'}`}>
                          {formatCurrency(accountSummary.operational_sustainability.operational_balance, accountSummary.country)}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* 6. Working Capital Status */}
              {accountSummary.working_capital_status && (
                <Card className={`border-2 ${accountSummary.working_capital_status.protection_mode ? 'border-red-400 bg-red-50/30' : (accountSummary.working_capital_status.status === 'Restoring' ? 'border-amber-400 bg-amber-50/30' : 'border-green-400 bg-green-50/30')}`} data-testid="wc-status">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Wallet className="w-5 h-5" />
                      Working Capital Status
                      <Badge className={
                        accountSummary.working_capital_status.protection_mode ? 'bg-red-600 text-white' :
                        accountSummary.working_capital_status.status === 'Restoring' ? 'bg-amber-600 text-white' :
                        'bg-green-600 text-white'
                      }>
                        {accountSummary.working_capital_status.status}
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <div className="p-3 bg-white rounded border text-center">
                        <p className="text-xs text-blue-600 font-medium">Base WC</p>
                        <p className="text-lg font-bold">{formatCurrency(accountSummary.working_capital_status.base_wc || accountSummary.working_capital_status.initial_wc, accountSummary.country)}</p>
                      </div>
                      <div className="p-3 bg-white rounded border text-center">
                        <p className="text-xs text-gray-500">Opening WC (Month)</p>
                        <p className="text-lg font-bold">{formatCurrency(accountSummary.working_capital_status.opening_wc || 0, accountSummary.country)}</p>
                      </div>
                      <div className="p-3 bg-white rounded border text-center">
                        <p className="text-xs font-medium text-gray-600">Current WC</p>
                        <p className="text-lg font-bold">{formatCurrency(accountSummary.working_capital_status.current_wc, accountSummary.country)}</p>
                      </div>
                      <div className="p-3 bg-white rounded border text-center">
                        <p className="text-xs text-gray-500">WC % vs Base</p>
                        <p className={`text-lg font-bold ${accountSummary.working_capital_status.wc_percentage >= 100 ? 'text-green-600' : accountSummary.working_capital_status.wc_percentage >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                          {accountSummary.working_capital_status.wc_percentage?.toFixed(0) || 0}%
                        </p>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <div className="p-3 bg-white rounded border text-center">
                        <p className="text-xs text-red-500 font-medium">WC Used (This Month)</p>
                        <p className="text-lg font-bold text-red-600">{formatCurrency(accountSummary.working_capital_status.wc_used || 0, accountSummary.country)}</p>
                      </div>
                      <div className="p-3 bg-white rounded border text-center">
                        <p className="text-xs text-green-500 font-medium">WC Restored (This Month)</p>
                        <p className="text-lg font-bold text-green-600">{formatCurrency(accountSummary.working_capital_status.wc_restored || 0, accountSummary.country)}</p>
                      </div>
                      <div className="p-3 bg-white rounded border text-center">
                        <p className="text-xs text-gray-500">{accountSummary?.payout_model === 'profit_share' ? 'Profit Share' : 'Revenue Share'}</p>
                        <p className={`text-lg font-bold ${accountSummary.working_capital_status.revenue_share_active ? 'text-green-600' : 'text-red-600'}`}>
                          {accountSummary.working_capital_status.revenue_share_active ? 'Active' : 'Blocked'}
                        </p>
                      </div>
                      <div className="p-3 bg-white rounded border text-center">
                        <p className="text-xs text-gray-500">Threshold</p>
                        <p className="text-lg font-bold">{accountSummary.working_capital_status.threshold}</p>
                      </div>
                    </div>
                    {accountSummary.working_capital_status.protection_mode && (
                      <div className="p-3 bg-red-100 border border-red-300 rounded text-sm text-red-800">
                        <strong>Protection Mode Active:</strong> WC is below 50% of Base. MG payouts are blocked. {accountSummary?.payout_model === 'profit_share' ? 'Profit share' : 'Revenue share'} blocked. All operational surplus directed to WC recovery.
                      </div>
                    )}
                    {accountSummary.working_capital_status.status === 'Restoring' && !accountSummary.working_capital_status.protection_mode && (
                      <div className="p-3 bg-amber-100 border border-amber-300 rounded text-sm text-amber-800">
                        <strong>WC Restoring:</strong> Working Capital is between 50-100% of Base. {accountSummary?.payout_model === 'profit_share' ? 'Profit share' : 'Revenue share'} is blocked until WC is fully restored to Base level. Operational surplus is being used to restore WC.
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Payout Determination Card — India only (MG vs Revenue Share). Overseas uses the Overseas Profit Share card above. */}
              {accountSummary.country === 'India' && accountSummary.payout && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Wallet className="w-5 h-5" />
                      Payout to Franchise Owner - {accountSummary.period}
                    </CardTitle>
                    <CardDescription>
                      {accountSummary.payout.protection_mode
                        ? `Protection Mode: ${accountSummary?.payout_model === 'profit_share' ? 'Profit share' : 'Revenue share'} on operational balance only. MG blocked.`
                        : `Comparison: MG vs Franchise Owner's ${accountSummary?.payout_model === 'profit_share' ? 'Profit Share' : 'Revenue Share'} - Higher amount is payable to Franchise Owner`
                      }
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {/* Operational Sustainability — per-month opt-in toggle */}
                    {accountSummary.payout?.protection_gating_available && (
                      <div className="mb-4 p-3 bg-amber-50 border-2 border-amber-300 rounded-lg" data-testid="protection-gating-toggle-card">
                        <div className="flex items-start justify-between gap-4 flex-wrap">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-amber-900 flex items-center gap-2">
                              <Shield className="w-4 h-4" />
                              Operational Sustainability — WC below 50 %
                            </p>
                            <p className="text-xs text-amber-700 mt-1">
                              Working Capital is below the 50% safety threshold. By default, the {accountSummary?.payout_model === 'profit_share' ? 'Profit Share' : 'Revenue Share'} is still <strong>Base × %</strong>.
                              Toggle ON to gate the payout to <strong>Operational Balance × %</strong> for this month only.
                            </p>
                          </div>
                          <Button
                            size="sm"
                            variant={accountSummary.payout.protection_gating_applied ? "default" : "outline"}
                            className={accountSummary.payout.protection_gating_applied ? "bg-amber-700 hover:bg-amber-800 text-white" : "border-amber-400 text-amber-800"}
                            data-testid="protection-gating-toggle-btn"
                            onClick={async () => {
                              try {
                                const newVal = !accountSummary.payout.protection_gating_applied;
                                const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
                                const res = await fetch(`${API}/center-accounts/protection-gating/set`, {
                                  method: 'POST', headers: { 'Content-Type': 'application/json' },
                                  body: JSON.stringify({ token: session.token, center: selectedCenter, month: selectedMonth, apply: newVal }),
                                });
                                if (!res.ok) throw new Error('Failed to toggle');
                                toast.success(newVal ? 'Operational Sustainability gating ENABLED for this month' : 'Operational Sustainability gating DISABLED — Share returns to Base × %');
                                await fetchAccountSummary();
                              } catch (e) {
                                toast.error(`Toggle failed: ${e.message}`);
                              }
                            }}
                          >
                            {accountSummary.payout.protection_gating_applied ? 'Gating: ON · Click to turn OFF' : 'Gating: OFF · Click to turn ON'}
                          </Button>
                        </div>
                      </div>
                    )}
                    {/* Protection Mode explainer — only shown when gating IS active */}
                    {accountSummary.payout.protection_mode && accountSummary.payout.protection_gating_applied && (
                      <div className="mb-4 p-3 bg-red-50 border-2 border-red-200 rounded-lg text-sm" data-testid="protection-mode-explainer">
                        <p className="text-red-800">
                          <strong>Why is the {accountSummary?.payout_model === 'profit_share' ? 'Profit Share' : 'Revenue Share'} calculated on Rs. {Math.round(accountSummary.share_calculation?.net_profit_or_sales || 0).toLocaleString('en-IN')} instead of Rs. {Math.round(accountSummary?.payout_model === 'profit_share' ? (accountSummary.engine?.profit_share_base || 0) : (accountSummary.engine?.revenue_share_base || 0)).toLocaleString('en-IN')}?</strong>
                        </p>
                        <p className="text-red-700 mt-1 text-xs">
                          Working Capital is below the 50% safety threshold. To protect the franchise from paying cash it can't afford,
                          the engine gates the {accountSummary?.payout_model === 'profit_share' ? 'profit share' : 'revenue share'} to the <strong>Operational Balance</strong> (Sales − Expenses − Commissions)
                          instead of the gross {accountSummary?.payout_model === 'profit_share' ? 'Profit Share Base' : 'Revenue Share Base'}. MG is also blocked.
                          Normal calculation resumes once WC ≥ 100% of the base.
                        </p>
                      </div>
                    )}
                    <div className="grid md:grid-cols-3 gap-4">
                      <Card className={`border-2 ${accountSummary.payout.type === 'minimum_guarantee' ? 'border-purple-400 bg-purple-50' : 'border-gray-200'} ${accountSummary.payout.protection_mode || accountSummary.mg_calculation_applicable === false ? 'opacity-50' : ''}`}>
                        <CardContent className="p-4 text-center">
                          <p className="text-sm text-gray-500">Minimum Guarantee</p>
                          <p className="text-2xl font-bold text-purple-600">
                            {accountSummary.mg_calculation_applicable === false
                              ? <span className="text-gray-400 text-base">N/A</span>
                              : formatCurrency(accountSummary.payout.mg_amount, accountSummary.country)}
                          </p>
                          {accountSummary.mg_calculation_applicable === false && (
                            <p className="text-xs text-gray-500 mt-2">MG not applicable<br/><span className="text-[10px]">({accountSummary?.payout_model === 'profit_share' ? 'Profit-Share-only' : 'Revenue-Share-only'})</span></p>
                          )}
                          {accountSummary.mg_calculation_applicable !== false && accountSummary.payout.type === 'minimum_guarantee' && !accountSummary.payout.protection_mode && (
                            <Badge className="mt-2 bg-purple-600">Payable</Badge>
                          )}
                          {accountSummary.mg_calculation_applicable !== false && accountSummary.payout.protection_mode && (
                            <Badge className="mt-2 bg-red-600 text-white">BLOCKED</Badge>
                          )}
                        </CardContent>
                      </Card>
                      <div className="flex items-center justify-center">
                        <span className="text-2xl font-bold text-gray-400">vs</span>
                      </div>
                      <Card className={`border-2 ${accountSummary.payout.type === 'revenue_share' || accountSummary.payout.type === 'revenue_share_protection' ? 'border-green-400 bg-green-50' : 'border-gray-200'} ${accountSummary.payout.protection_mode && accountSummary.payout.operational_balance <= 0 ? 'opacity-50' : ''}`}>
                        <CardContent className="p-4 text-center">
                          <p className="text-sm text-gray-500">Franchise Owner's {accountSummary?.payout_model === 'profit_share' ? 'Profit Share' : 'Revenue Share'} ({accountSummary.share_calculation?.franchise_owner?.percentage || 15}%)</p>
                          <p className="text-2xl font-bold text-green-600">
                            {formatCurrency(accountSummary.payout.revenue_share_amount, accountSummary.country)}
                          </p>
                          {/* Formula — makes "% × base = amount" visible so user can verify math */}
                          {(() => {
                            const pct = accountSummary.share_calculation?.franchise_owner?.percentage || 0;
                            const base = accountSummary.share_calculation?.net_profit_or_sales || 0;
                            const baseLabel = accountSummary.payout?.protection_mode ? 'Operational Balance' : (accountSummary?.payout_model === 'profit_share' ? 'Profit Share Base' : 'Revenue Share Base');
                            return (
                              <p className="text-[11px] text-gray-500 mt-1 font-mono" data-testid="share-formula">
                                = {pct}% × {formatCurrency(base, accountSummary.country)}
                                <span className="block text-[10px] not-italic text-gray-400">({baseLabel})</span>
                              </p>
                            );
                          })()}
                          {(accountSummary.payout.type === 'revenue_share' || accountSummary.payout.type === 'revenue_share_protection') && (
                            <Badge className="mt-2 bg-green-600">Payable</Badge>
                          )}
                        </CardContent>
                      </Card>
                    </div>

                    {/* WC Recovery info for Protection Mode */}
                    {accountSummary.payout.protection_mode && accountSummary.payout.wc_recovery_amount > 0 && (
                      <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded text-sm">
                        <strong>WC Recovery:</strong> {formatCurrency(accountSummary.payout.wc_recovery_amount, accountSummary.country)} directed to Working Capital recovery
                      </div>
                    )}

                    <div className={`mt-4 p-4 rounded-lg ${accountSummary.payout.protection_mode ? 'bg-red-50' : 'bg-blue-50'}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className={`text-sm ${accountSummary.payout.protection_mode ? 'text-red-600' : 'text-blue-600'}`}>Amount Payable to Franchise Owner This Month</p>
                          <p className={`text-3xl font-bold ${accountSummary.payout.protection_mode ? 'text-red-800' : 'text-blue-800'}`}>
                            {formatCurrency(accountSummary.payout.amount, accountSummary.country)}
                          </p>
                        </div>
                        <Badge className="text-lg px-4 py-2" variant={accountSummary.payout.protection_mode ? 'destructive' : accountSummary.payout.type === 'minimum_guarantee' ? 'default' : 'secondary'}>
                          {accountSummary.payout.protection_mode ? 'PROTECTION MODE' : accountSummary.payout.type === 'minimum_guarantee' ? 'MG' : (accountSummary?.payout_model === 'profit_share' ? 'Profit Share' : 'Revenue Share')}
                        </Badge>
                      </div>
                      <p className={`text-xs mt-2 ${accountSummary.payout.protection_mode ? 'text-red-500' : 'text-blue-500'}`}>{accountSummary.payout.reason}</p>
                      {accountSummary.payout.protection_gating_applied && (
                        <p className="text-xs mt-2 text-gray-500 italic">{accountSummary?.payout_model === 'profit_share' ? 'Profit share' : 'Revenue share'} distribution follows Operational Sustainability rules. Operational costs and working capital protection are prioritized before owner distribution.</p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* GST Notice for India */}
              {accountSummary.country === 'India' && (
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-amber-600" />
                    <p className="text-sm text-amber-800">
                      <strong>Note:</strong> 18% GST (CGST 9% + SGST 9%) on {accountSummary?.payout_model === 'profit_share' ? 'Profit Share' : 'Revenue Share'} is shown for reference only and is <strong>not included</strong> in {entityName(accountSummary.country)}'s total payable amount. For outside India, 10% GST is applicable on Profit Share.
                    </p>
                  </div>
                </div>
              )}

              {/* Final Payout (incl. GST) — Overseas */}
              {accountSummary.country !== 'India' && accountSummary.overseas_share && accountSummary.share_calculation?.purnabramha && (
                <Card className="border-2 border-blue-300" data-testid="overseas-final-payout">
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Wallet className="w-5 h-5 text-blue-700" />
                      Final Payout (incl. 10% GST on Franchisor {accountSummary.share_calculation?.type === 'profit_share' ? 'Profit Share' : 'Revenue Share'}) — {accountSummary.period}
                    </CardTitle>
                    <CardDescription>
                      Owner gets 80% of Eligible Profit. {entityName(accountSummary.country)} invoices 20% + 10% GST. MFPL royalty is accrued separately as a liability.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between"><span>Franchise Owner {accountSummary.share_calculation?.type === 'profit_share' ? 'Profit Share' : 'Revenue Share'} (80%)</span>
                        <span className="font-medium text-green-700">{formatCurrency(accountSummary.overseas_share.owner_share, accountSummary.country)}</span></div>
                      <div className="flex justify-between"><span>{entityName(accountSummary.country)} {accountSummary.share_calculation?.type === 'profit_share' ? 'Profit Share' : 'Revenue Share'} (20%)</span>
                        <span className="font-medium">{formatCurrency(accountSummary.share_calculation.purnabramha.base_amount, accountSummary.country)}</span></div>
                      <div className="flex justify-between"><span className="pl-4 text-gray-500">Add: GST @ 10%</span>
                        <span className="text-gray-700">{formatCurrency(accountSummary.share_calculation.purnabramha.gst_amount, accountSummary.country)}</span></div>
                      <div className="flex justify-between border-t pt-2"><span className="font-medium">{entityName(accountSummary.country)} Invoice (incl. GST)</span>
                        <span className="font-bold text-indigo-700">{formatCurrency(accountSummary.share_calculation.purnabramha.total_payable, accountSummary.country)}</span></div>
                      <div className="flex justify-between"><span>MFPL Royalty Accrued (5% of Net Sales)</span>
                        <span className="font-medium text-amber-700">{formatCurrency(accountSummary.overseas_share.mfpl_royalty, accountSummary.country)}</span></div>
                      <div className="flex justify-between bg-amber-50 px-2 py-1 rounded"><span className="font-medium">MFPL Liability Outstanding (cumulative)</span>
                        <span className="font-bold text-amber-800">{formatCurrency(accountSummary.mfpl_royalty?.outstanding_mfpl || 0, accountSummary.country)}</span></div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Working Capital Standing in MG & Payout */}
              {accountSummary.financial_summary.wc_standing && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg">Working Capital Standing ({accountSummary.period})</CardTitle>
                    <CardDescription>Monthly WC assessment: Opening + P&L = Closing</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                      <div className="p-3 bg-blue-50 rounded-lg text-center border border-blue-200">
                        <p className="text-xs text-gray-500">Opening WC</p>
                        <p className="text-lg font-semibold text-blue-700">{formatCurrency(accountSummary.financial_summary.wc_standing.opening_wc, accountSummary.country)}</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg text-center">
                        <p className="text-xs text-gray-500">This Month P&L</p>
                        <p className={`text-lg font-semibold ${accountSummary.financial_summary.wc_standing.this_month_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {accountSummary.financial_summary.wc_standing.this_month_pnl >= 0 ? '+' : ''}{formatCurrency(accountSummary.financial_summary.wc_standing.this_month_pnl, accountSummary.country)}
                        </p>
                      </div>
                      <div className={`p-3 rounded-lg text-center border ${accountSummary.financial_summary.wc_standing.closing_wc >= accountSummary.financial_summary.wc_standing.initial_security_deposit ? 'bg-green-50 border-green-200' : accountSummary.financial_summary.wc_standing.closing_wc > 0 ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200'}`}>
                        <p className="text-xs text-gray-500">Closing WC</p>
                        <p className={`text-lg font-bold ${accountSummary.financial_summary.wc_standing.closing_wc >= accountSummary.financial_summary.wc_standing.initial_security_deposit ? 'text-green-700' : accountSummary.financial_summary.wc_standing.closing_wc > 0 ? 'text-amber-700' : 'text-red-700'}`} data-testid="payout-available-wc">
                          {formatCurrency(accountSummary.financial_summary.wc_standing.closing_wc, accountSummary.country)}
                        </p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg text-center">
                        <p className="text-xs text-gray-500">Diff from Initial</p>
                        <p className={`text-lg font-semibold ${accountSummary.financial_summary.wc_standing.diff_from_initial >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(accountSummary.financial_summary.wc_standing.diff_from_initial, accountSummary.country)}
                        </p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg text-center">
                        <p className="text-xs text-gray-500">Total Loans</p>
                        <p className="text-lg font-semibold text-red-600">{formatCurrency(accountSummary.financial_summary.wc_standing.total_effective_loans, accountSummary.country)}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Month-wise Payout Grid */}
              <Card>
                <CardHeader>
                  <div className="flex flex-col gap-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-lg flex items-center gap-2">
                          <FileSpreadsheet className="w-5 h-5" />
                          Month-wise Payout Summary
                        </CardTitle>
                        <CardDescription>
                          {payoutSummary?.period?.revenue_start_date 
                            ? `Revenue start: ${new Date(payoutSummary.period.revenue_start_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}`
                            : 'Historical payout data with payment tracking'
                          }
                        </CardDescription>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button 
                          variant="outline" size="sm" 
                          onClick={() => handleExportMGPayout('excel')} 
                          disabled={!!exportLoading || !payoutSummary?.monthly_data?.length}
                          data-testid="export-mg-excel"
                        >
                          {exportLoading === 'excel' ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <FileSpreadsheet className="w-4 h-4 mr-1" />}
                          Excel
                        </Button>
                        <Button 
                          variant="outline" size="sm"
                          onClick={() => handleExportMGPayout('pdf')}
                          disabled={!!exportLoading || !payoutSummary?.monthly_data?.length}
                          data-testid="export-mg-pdf"
                        >
                          {exportLoading === 'pdf' ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Download className="w-4 h-4 mr-1" />}
                          PDF
                        </Button>
                        <Button variant="outline" size="sm" onClick={fetchPayoutSummary} disabled={payoutLoading}>
                          <RefreshCw className={`w-4 h-4 ${payoutLoading ? 'animate-spin' : ''}`} />
                        </Button>
                      </div>
                    </div>
                    {/* Month Range Filter */}
                    <div className="flex items-end gap-3 p-3 bg-gray-50 rounded-lg">
                      <div className="space-y-1">
                        <Label className="text-xs text-gray-500">From Month</Label>
                        <Input
                          type="month"
                          value={payoutFromMonth}
                          onChange={(e) => setPayoutFromMonth(e.target.value)}
                          className="h-9 w-40 text-sm"
                          data-testid="payout-from-month"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs text-gray-500">To Month</Label>
                        <Input
                          type="month"
                          value={payoutToMonth}
                          onChange={(e) => setPayoutToMonth(e.target.value)}
                          className="h-9 w-40 text-sm"
                          data-testid="payout-to-month"
                        />
                      </div>
                      <Button size="sm" onClick={fetchPayoutSummary} disabled={payoutLoading} className="h-9">
                        {payoutLoading ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <RefreshCw className="w-4 h-4 mr-1" />}
                        Apply
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {payoutLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                      <span className="ml-2 text-gray-500">Loading payout data...</span>
                    </div>
                  ) : payoutSummary?.monthly_data?.length > 0 ? (
                    <>
                      {/* Summary Cards */}
                      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                        <div className="p-3 bg-blue-50 rounded-lg text-center">
                          <p className="text-xs text-blue-600">Total {accountSummary?.share_calculation?.type === 'profit_share' ? 'Profit Share' : 'Revenue Share'}</p>
                          <p className="text-lg font-bold text-blue-800">{formatCurrency(payoutSummary.totals?.revenue_share, accountSummary?.country)}</p>
                        </div>
                        <div className="p-3 bg-purple-50 rounded-lg text-center">
                          <p className="text-xs text-purple-600">Monthly MG</p>
                          <p className="text-lg font-bold text-purple-800" data-testid="kpi-monthly-mg">
                            {payoutSummary.franchise?.mg_calculation_applicable === false
                              ? <span className="text-gray-500 text-sm">N/A</span>
                              : formatCurrency(payoutSummary.franchise?.mg_amount, accountSummary?.country)}
                          </p>
                          {payoutSummary.franchise?.mg_calculation_applicable === false && (
                            <p className="text-[10px] text-gray-500 mt-1">{accountSummary?.share_calculation?.type === 'profit_share' ? 'Profit-Share-only model' : 'Revenue-Share-only model'}</p>
                          )}
                        </div>
                        <div className="p-3 bg-sky-50 rounded-lg text-center border border-sky-200" title={`Calculated as ${accountSummary?.share_calculation?.type === 'profit_share' ? 'Profit Share' : 'Revenue Share'} Base × Franchise ${accountSummary?.share_calculation?.type === 'profit_share' ? 'Profit Share' : 'Revenue Share'} Percentage configured in Franchise Management.`}>
                          <p className="text-xs text-sky-700 font-semibold">Total {accountSummary?.share_calculation?.type === 'profit_share' ? 'Profit Share' : 'Revenue Share'} Payout</p>
                          <p className="text-lg font-bold text-sky-900" data-testid="kpi-total-rev-share-payout">
                            {formatCurrency(payoutSummary.totals?.revenue_share || 0, accountSummary?.country)}
                          </p>
                          <p className="text-[10px] text-sky-700">@ {payoutSummary.franchise?.revenue_share_percentage || 0}% of {accountSummary?.share_calculation?.type === 'profit_share' ? 'Profit' : 'Revenue'} Share Base</p>
                        </div>
                        <div className="p-3 bg-green-50 rounded-lg text-center">
                          <p className="text-xs text-green-600">Total {accountSummary?.share_calculation?.type === 'profit_share' ? 'Profit Share' : 'Revenue Share'} Payable</p>
                          <p className="text-lg font-bold text-green-800">{formatCurrency(payoutSummary.totals?.payable, accountSummary?.country)}</p>
                        </div>
                        <div className="p-3 bg-emerald-50 rounded-lg text-center">
                          <p className="text-xs text-emerald-600">Total Paid</p>
                          <p className="text-lg font-bold text-emerald-800">{formatCurrency(payoutSummary.totals?.paid, accountSummary?.country)}</p>
                        </div>
                        <div className="p-3 bg-red-50 rounded-lg text-center">
                          <p className="text-xs text-red-600">Total Pending</p>
                          <p className="text-lg font-bold text-red-800">{formatCurrency(payoutSummary.totals?.pending, accountSummary?.country)}</p>
                        </div>
                      </div>

                      {/* Month-wise Table */}
                      <div className="overflow-x-auto border rounded-lg">
                        <table className="w-full text-sm">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="text-left py-3 px-4 font-medium text-gray-600">Month</th>
                              <th className="text-right py-3 px-4 font-medium text-gray-600">Total Sales</th>
                              <th className="text-right py-3 px-4 font-medium text-gray-600">GST</th>
                              <th className="text-right py-3 px-4 font-medium text-gray-600">Commissions</th>
                              <th className="text-right py-3 px-4 font-bold text-sky-700">⭐ {accountSummary?.payout_model === 'profit_share' ? 'Profit Share' : 'Revenue Share'} Base</th>
                              <th className="text-right py-3 px-4 font-semibold text-sky-700" title={`${accountSummary?.payout_model === 'profit_share' ? 'Profit Share' : 'Revenue Share'} Base × Franchise ${accountSummary?.payout_model === 'profit_share' ? 'Profit Share' : 'Revenue Share'} %`}>
                                {accountSummary?.payout_model === 'profit_share' ? 'Profit Share' : 'Revenue Share'} Payout
                                <span className="block text-[10px] font-normal opacity-75">@ {payoutSummary.franchise?.revenue_share_percentage || 0}%</span>
                              </th>
                              <th className="text-right py-3 px-4 font-medium text-gray-600">MG</th>
                              <th className="text-center py-3 px-4 font-medium text-gray-600">Type</th>
                              <th className="text-right py-3 px-4 font-medium text-gray-600">Payable</th>
                              <th className="text-right py-3 px-4 font-medium text-gray-600">Paid</th>
                              <th className="text-right py-3 px-4 font-medium text-gray-600">Pending</th>
                              <th className="text-center py-3 px-4 font-medium text-gray-600">Status</th>
                              <th className="text-center py-3 px-4 font-medium text-gray-600">Action</th>
                            </tr>
                          </thead>
                          <tbody>
                            {/* TOTALS row — sum each numeric column so the user sees
                                the aggregate without scrolling down (Feb-2026 fix) */}
                            {(() => {
                              const rows = payoutSummary.monthly_data || [];
                              const sum = (key) => rows.reduce((acc, m) => acc + (Number(m[key]) || 0), 0);
                              const totSales = sum('total_sales');
                              const totGst = sum('gst_on_sales');
                              const totComm = sum('total_commissions');
                              const totRsb = rows.reduce((acc, m) => acc + (Number(m.revenue_share_base
                                ?? Math.max(0, (m.total_sales||0) - (m.total_commissions||0) - (m.gst_on_sales||0)))
                              ), 0);
                              const rsPct = payoutSummary.franchise?.revenue_share_percentage || 0;
                              const totRsPayout = rows.reduce((acc, m) => acc + (Number(
                                m.revenue_share
                                ?? ((m.revenue_share_base
                                  ?? Math.max(0, (m.total_sales||0) - (m.total_commissions||0) - (m.gst_on_sales||0))) * rsPct / 100)
                              ) || 0), 0);
                              const totMg = rows.reduce((acc, m) => acc + (m.mg_applicable === false ? 0 : (Number(m.mg_amount) || 0)), 0);
                              const totPayable = sum('payable_amount');
                              const totPaid = sum('paid');
                              const totPending = sum('pending');
                              return (
                                <tr className="bg-amber-50 border-t-2 border-b-2 border-amber-300 font-bold sticky top-0" data-testid="mg-payout-totals-row">
                                  <td className="py-3 px-4 text-amber-900 uppercase text-xs tracking-wider">Total</td>
                                  <td className="py-3 px-4 text-right text-amber-900" data-testid="totals-total-sales">{formatCurrency(totSales, accountSummary?.country)}</td>
                                  <td className="py-3 px-4 text-right text-orange-700" data-testid="totals-gst">{formatCurrency(totGst, accountSummary?.country)}</td>
                                  <td className="py-3 px-4 text-right text-rose-700" data-testid="totals-commissions">{formatCurrency(totComm, accountSummary?.country)}</td>
                                  <td className="py-3 px-4 text-right text-sky-900" data-testid="totals-rev-share-base">{formatCurrency(totRsb, accountSummary?.country)}</td>
                                  <td className="py-3 px-4 text-right text-sky-800" data-testid="totals-rev-share-payout">{formatCurrency(totRsPayout, accountSummary?.country)}</td>
                                  <td className="py-3 px-4 text-right text-purple-700" data-testid="totals-mg">{formatCurrency(totMg, accountSummary?.country)}</td>
                                  <td className="py-3 px-4 text-center text-amber-900 text-[10px]">—</td>
                                  <td className="py-3 px-4 text-right text-amber-900" data-testid="totals-payable">{formatCurrency(totPayable, accountSummary?.country)}</td>
                                  <td className="py-3 px-4 text-right text-emerald-700" data-testid="totals-paid">{formatCurrency(totPaid, accountSummary?.country)}</td>
                                  <td className="py-3 px-4 text-right text-red-700" data-testid="totals-pending">{formatCurrency(totPending, accountSummary?.country)}</td>
                                  <td className="py-3 px-4 text-center text-amber-900 text-[10px]">—</td>
                                  <td className="py-3 px-4 text-center text-amber-900 text-[10px]">—</td>
                                </tr>
                              );
                            })()}
                            {payoutSummary.monthly_data.map((month, idx) => {
                              const revShareBaseRow = (
                                month.revenue_share_base
                                ?? Math.max(0, (month.total_sales || 0) - (month.total_commissions || 0) - (month.gst_on_sales || 0))
                              );
                              const revSharePct = payoutSummary.franchise?.revenue_share_percentage || 0;
                              const revSharePayoutRow = month.revenue_share ?? (revShareBaseRow * revSharePct / 100);
                              return (
                              <tr key={month.month} className={`border-t ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'} hover:bg-blue-50/50`}>
                                <td className="py-3 px-4 font-medium">
                                  {new Date(month.month + '-01').toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}
                                </td>
                                <td className="py-3 px-4 text-right">{formatCurrency(month.total_sales, accountSummary?.country)}</td>
                                <td className="py-3 px-4 text-right text-orange-600">{formatCurrency(month.gst_on_sales || 0, accountSummary?.country)}</td>
                                <td className="py-3 px-4 text-right text-rose-600">{formatCurrency(month.total_commissions || 0, accountSummary?.country)}</td>
                                <td className="py-3 px-4 text-right text-sky-800 font-bold">{formatCurrency(revShareBaseRow, accountSummary?.country)}</td>
                                <td className="py-3 px-4 text-right text-sky-700 font-semibold" data-testid={`rev-share-payout-${month.month}`}>{formatCurrency(revSharePayoutRow, accountSummary?.country)}</td>
                                <td className="py-3 px-4 text-right text-purple-600">
                                  {month.mg_applicable === false
                                    ? <span className="text-gray-400 text-xs">N/A</span>
                                    : formatCurrency(month.mg_amount, accountSummary?.country)}
                                </td>
                                <td className="py-3 px-4 text-center">
                                  <Badge variant={month.payable_type === 'mg' ? 'default' : 'secondary'} className="text-xs">
                                    {month.mg_applicable === false ? 'RS' : (month.payable_type === 'mg' ? 'MG' : 'RS')}
                                  </Badge>
                                </td>
                                <td className="py-3 px-4 text-right font-medium">{formatCurrency(month.payable_amount, accountSummary?.country)}</td>
                                <td className="py-3 px-4 text-right text-emerald-600">{formatCurrency(month.paid, accountSummary?.country)}</td>
                                <td className="py-3 px-4 text-right text-red-600">{formatCurrency(month.pending, accountSummary?.country)}</td>
                                <td className="py-3 px-4 text-center">
                                  {month.status === 'paid' ? (
                                    <Badge className="bg-green-100 text-green-800 text-xs">Paid</Badge>
                                  ) : month.status === 'partial' ? (
                                    <Badge className="bg-amber-100 text-amber-800 text-xs">Partial</Badge>
                                  ) : (
                                    <Badge className="bg-red-100 text-red-800 text-xs">Unpaid</Badge>
                                  )}
                                </td>
                                <td className="py-3 px-4 text-center">
                                  <Button 
                                    size="sm" 
                                    variant="outline" 
                                    className="h-7 text-xs"
                                    onClick={() => openPaymentDialog(month)}
                                    data-testid={`record-payment-${month.month}`}
                                  >
                                    <DollarSign className="w-3 h-3 mr-1" />
                                    Pay
                                  </Button>
                                </td>
                              </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <FileSpreadsheet className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                      <p>No payout data available</p>
                      <p className="text-sm text-gray-400 mt-1">Data will appear once franchise is linked and has sales</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Invoice Export Tab (CA/Auditor Ready) */}
            <TabsContent value="bundles" className="space-y-4" data-testid="bundles-tab-content">
              {(() => {
                const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
                const linked = !!accountSummary?.franchise?.linked;
                const period = selectedMonth;
                const center = selectedCenter;

                const downloadZip = async (url, filename) => {
                  try {
                    const res = await fetch(url);
                    if (!res.ok) throw new Error(`HTTP ${res.status}`);
                    const blob = await res.blob();
                    const a = document.createElement('a');
                    a.href = URL.createObjectURL(blob);
                    a.download = filename;
                    a.click();
                    URL.revokeObjectURL(a.href);
                    toast.success(`${filename} downloaded`);
                  } catch (e) {
                    toast.error(`Download failed: ${e.message}`);
                  }
                };

                const dlCA = () => downloadZip(
                  `${API}/bundles/ca?token=${encodeURIComponent(session?.token || '')}&center=${encodeURIComponent(center)}&period=${encodeURIComponent(period)}`,
                  `CA_${center}_${period}.zip`,
                );
                const dlFull = () => downloadZip(
                  `${API}/bundles/franchisor?token=${encodeURIComponent(session?.token || '')}&center=${encodeURIComponent(center)}&period=${encodeURIComponent(period)}`,
                  `FullCenter_${center}_${period}.zip`,
                );

                const ExportCard = ({ tone, icon, title, desc, contents, action, testid, disabled }) => (
                  <Card className={`border-2 ${tone}`} data-testid={`bundle-card-${testid}`}>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-lg">
                        {icon}
                        {title}
                      </CardTitle>
                      <CardDescription>{desc}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <p className="text-xs font-semibold text-stone-600 mb-2">Contains</p>
                        <ul className="text-xs text-stone-700 space-y-1 list-disc pl-5">
                          {contents.map((c, i) => <li key={i}>{c}</li>)}
                        </ul>
                      </div>
                      {action}
                    </CardContent>
                  </Card>
                );

                return (
                  <>
                    <Card className="bg-gradient-to-r from-stone-50 to-stone-100 border-stone-200">
                      <CardContent className="p-4">
                        <p className="text-sm text-stone-700">
                          One-click exports for <strong>{center}</strong> · <strong>{period}</strong>.
                          All packages pull from the <strong>Single Financial Engine</strong> — no duplicate calculations.
                        </p>
                      </CardContent>
                    </Card>

                    <div className="grid md:grid-cols-3 gap-4" data-testid="bundle-export-grid">
                      <ExportCard
                        tone="border-emerald-300 hover:border-emerald-500"
                        icon={<Archive className="w-5 h-5 text-emerald-700" />}
                        title="CA Bundle"
                        desc="Complete Accounts Package — for the CA / Auditor."
                        testid="ca"
                        contents={[
                          'All Ledgers (PDF + Excel)',
                          'Bills / Attachments (by date)',
                          'P&L, GST Summary, Bank & Commission Recon',
                          'Engine-snapshot manifest for audit trail',
                        ]}
                        action={
                          <Button onClick={dlCA} disabled={!center || !period}
                                  className="bg-emerald-600 hover:bg-emerald-700 text-white w-full"
                                  data-testid="bundle-ca-download">
                            <Download className="w-4 h-4 mr-2" />
                            Download CA Bundle (.zip)
                          </Button>
                        }
                      />

                      <ExportCard
                        tone="border-rose-300 hover:border-rose-500"
                        icon={<Mail className="w-5 h-5 text-rose-700" />}
                        title="Email Package"
                        desc="Professional email-ready package for the Franchise Owner."
                        testid="email"
                        contents={[
                          'Executive Summary (subject + body)',
                          'Key Financial Numbers',
                          'PIB Report, GST, Commission, Bank',
                          'Raw aggregator / bank uploads (where available)',
                        ]}
                        action={
                          <Button onClick={() => openEmailPack()} disabled={!linked}
                                  className="bg-rose-700 hover:bg-rose-800 text-white w-full"
                                  data-testid="bundle-email-open">
                            <Mail className="w-4 h-4 mr-2" />
                            Open Email Package
                          </Button>
                        }
                      />

                      <ExportCard
                        tone="border-indigo-300 hover:border-indigo-500"
                        icon={<FileBox className="w-5 h-5 text-indigo-700" />}
                        title="Full Center Package"
                        desc="Master bundle — everything for this center, one click."
                        testid="full"
                        contents={[
                          'All Reports (Financial · Settlement · Recon · Compliance)',
                          'All Ledgers (Financial · Franchise · Adjustment)',
                          'Payout Summary (MG / Revenue / Profit Share)',
                          'Executive cover-sheet + engine manifest',
                        ]}
                        action={
                          <Button onClick={dlFull} disabled={!center || !period}
                                  className="bg-indigo-600 hover:bg-indigo-700 text-white w-full"
                                  data-testid="bundle-full-download">
                            <Download className="w-4 h-4 mr-2" />
                            Download Full Center Package (.zip)
                          </Button>
                        }
                      />
                    </div>

                    <p className="text-[11px] text-muted-foreground italic px-1">
                      All three packages are independent — pick the one that matches your audience (CA, Owner, or full archive).
                      No duplicated calculations: the same Financial Engine output feeds every report inside.
                    </p>
                  </>
                );
              })()}
            </TabsContent>

            <TabsContent value="pnl-rs" className="space-y-4" data-testid="pnl-rs-tab-content">
              <PnLRevenueShareOverview center={selectedCenter} />
            </TabsContent>

            <TabsContent value="rs-projection" className="space-y-4" data-testid="rs-projection-tab-content">
              <RevenueShareProjection center={selectedCenter} />
            </TabsContent>
          </Tabs>
        </>
      )}

      {/* No Center Selected */}
      {!selectedCenter && (
        <Card>
          <CardContent className="py-12 text-center">
            <Building2 className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <h3 className="text-lg font-medium text-gray-600">Select a Center</h3>
            <p className="text-gray-400 mt-1">Choose a center from the dropdown to view account details</p>
          </CardContent>
        </Card>
      )}

      {/* Upload Commission Excel Modal */}
      <Dialog open={showOtherIncomeModal} onOpenChange={setShowOtherIncomeModal}>
        <DialogContent className="max-w-md" data-testid="other-income-modal">
          <DialogHeader>
            <DialogTitle className="text-emerald-700 flex items-center gap-2">
              <Plus className="w-5 h-5" /> Add Other Income
            </DialogTitle>
            <DialogDescription>
              Memo entry for {selectedCenter}. Not added to Sales / P&L / WC.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Date *</Label>
              <Input type="date" value={otherIncomeForm.date}
                onChange={(e) => setOtherIncomeForm(p => ({ ...p, date: e.target.value }))}
                data-testid="oi-date" />
            </div>
            <div>
              <Label>Amount *</Label>
              <Input type="number" min="0" step="0.01" value={otherIncomeForm.amount}
                onChange={(e) => setOtherIncomeForm(p => ({ ...p, amount: e.target.value }))}
                placeholder="0.00" data-testid="oi-amount" />
            </div>
            <div>
              <Label>Category *</Label>
              <Select value={otherIncomeForm.category}
                onValueChange={(v) => setOtherIncomeForm(p => ({ ...p, category: v }))}>
                <SelectTrigger data-testid="oi-category"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="vendor_refund">Vendor Refund</SelectItem>
                  <SelectItem value="franchisee_repayment">Franchisee Repayment</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-[10px] text-muted-foreground mt-1">
                "Loan Taken" entries are auto-created when you log a new loan in Loan Entries.
              </p>
            </div>
            <div>
              <Label>Reason / Notes *</Label>
              <Input value={otherIncomeForm.reason}
                onChange={(e) => setOtherIncomeForm(p => ({ ...p, reason: e.target.value }))}
                placeholder="Why is this an Other Income?" data-testid="oi-reason" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowOtherIncomeModal(false)} disabled={otherIncomeSaving}>Cancel</Button>
            <Button
              className="bg-emerald-600 hover:bg-emerald-700"
              disabled={otherIncomeSaving || !otherIncomeForm.amount || !otherIncomeForm.reason}
              onClick={async () => {
                setOtherIncomeSaving(true);
                try {
                  const res = await fetch(`${API}/api/other-income/create`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      token: session?.token,
                      center: selectedCenter,
                      date: otherIncomeForm.date,
                      amount: parseFloat(otherIncomeForm.amount) || 0,
                      category: otherIncomeForm.category,
                      reason: otherIncomeForm.reason,
                    }),
                  });
                  const data = await res.json();
                  if (res.ok && data.success) {
                    toast.success("Other Income added");
                    setShowOtherIncomeModal(false);
                    setOtherIncomeForm({
                      date: new Date().toISOString().split("T")[0],
                      amount: "", category: "vendor_refund", reason: "",
                    });
                    await fetchAccountSummary();
                  } else {
                    toast.error(data.detail || "Failed to add Other Income");
                  }
                } catch {
                  toast.error("Failed to add Other Income");
                } finally {
                  setOtherIncomeSaving(false);
                }
              }}
              data-testid="oi-save-btn">
              {otherIncomeSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
              Save Entry
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showUploadModal} onOpenChange={setShowUploadModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Upload Commission Report</DialogTitle>
            <DialogDescription>Upload monthly Excel report for {selectedCenter}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Platform *</Label>
              <Select value={uploadPlatform} onValueChange={setUploadPlatform}>
                <SelectTrigger data-testid="upload-platform-select">
                  <SelectValue placeholder="Select platform" />
                </SelectTrigger>
                <SelectContent>
                  {availablePlatforms.map(p => (
                    <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Month *</Label>
              <Input
                type="month"
                value={uploadMonth}
                onChange={(e) => setUploadMonth(e.target.value)}
                data-testid="upload-month-input"
              />
            </div>
            <div>
              <Label>Excel File (.xlsx) *</Label>
              <Input
                type="file"
                accept=".xlsx,.xls"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                data-testid="upload-file-input"
              />
              {uploadFile && (
                <p className="text-sm text-gray-500 mt-1">{uploadFile.name}</p>
              )}
            </div>
            {(uploadPlatform === 'cards' || uploadPlatform === 'phonepe') && (
              <div>
                <Label>Bank Statement (.xlsx) — for charge calculation</Label>
                <Input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={(e) => setBankFile(e.target.files?.[0] || null)}
                  data-testid="upload-bank-file-input"
                />
                {bankFile && (
                  <p className="text-sm text-gray-500 mt-1">{bankFile.name}</p>
                )}
                <p className="text-xs text-amber-600 mt-1">
                  {uploadPlatform === 'cards'
                    ? 'Upload your bank statement to auto-calculate card charges by matching EDC settlements with bank credits.'
                    : 'Upload your bank statement to auto-calculate PhonePe charges by matching UPI settlements with bank credits (next-day settlement).'}
                </p>
              </div>
            )}
            <div className="p-3 bg-blue-50 rounded-lg text-sm text-blue-700">
              <p className="font-medium mb-1">Supported formats:</p>
              <p>Zomato, Swiggy, DoorDash, PhonePe, Cards — monthly reports as downloaded from each platform.</p>
              {uploadPlatform === 'cards' && <p className="mt-1">For Cards: Upload EDC report + Bank Statement to calculate exact bank charges (MDR).</p>}
              {uploadPlatform === 'phonepe' && <p className="mt-1">For PhonePe: Upload transaction report + Bank Statement to calculate exact PhonePe charges.</p>}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUploadModal(false)}>Cancel</Button>
            <Button onClick={handleUploadCommission} disabled={uploadLoading || !uploadFile || !uploadPlatform}>
              {uploadLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Upload className="w-4 h-4 mr-2" />}
              Parse & Preview
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Parsed Preview Modal */}
      <Dialog open={showPreviewModal} onOpenChange={setShowPreviewModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Review Parsed Data</DialogTitle>
            <DialogDescription>
              {parsedPreview?.platform?.toUpperCase()} — {parsedPreview?.month} — {parsedPreview?.original_filename}
            </DialogDescription>
          </DialogHeader>
          {parsedPreview && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-100">
                  <p className="text-sm text-emerald-600">Gross Amount</p>
                  <p className="text-2xl font-bold text-emerald-800">{formatCurrency(parsedPreview.gross_amount, accountSummary?.country)}</p>
                </div>
                <div className="p-4 bg-orange-50 rounded-lg border border-orange-100">
                  <p className="text-sm text-orange-600">GST / Tax Deductions</p>
                  <p className="text-2xl font-bold text-orange-700">{formatCurrency(parsedPreview.gst_tax_deductions, accountSummary?.country)}</p>
                </div>
                {parsedPreview.sundry_debtors > 0 ? (
                  <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                    <p className="text-sm text-blue-600">Sundry Debtors (Next Month)</p>
                    <p className="text-2xl font-bold text-blue-700">{formatCurrency(parsedPreview.sundry_debtors, accountSummary?.country)}</p>
                  </div>
                ) : (
                  <div className="p-4 bg-red-50 rounded-lg border border-red-100">
                    <p className="text-sm text-red-600">Other Deductions</p>
                    <p className="text-2xl font-bold text-red-700">{formatCurrency(parsedPreview.other_deductions, accountSummary?.country)}</p>
                  </div>
                )}
                <div className="p-4 bg-green-50 rounded-lg border border-green-100">
                  <p className="text-sm text-green-600">Net Payout</p>
                  <p className="text-2xl font-bold text-green-700">{formatCurrency(parsedPreview.net_payout, accountSummary?.country)}</p>
                </div>
              </div>
              <div className="flex gap-4 text-sm text-gray-600 flex-wrap">
                <span>Orders: <strong>{parsedPreview.order_count}</strong></span>
                <span>TDS: <strong>{formatCurrency(parsedPreview.tds, accountSummary?.country)}</strong></span>
                <span>Currency: <strong>{parsedPreview.currency}</strong></span>
              </div>
              {parsedPreview.gross_amount > 0 && (parsedPreview.gst_tax_deductions > 0 || parsedPreview.other_deductions > 0) && !parsedPreview.sundry_debtors && (
                <div className="p-3 bg-amber-50 rounded text-sm text-amber-700">
                  Total Deduction Rate: <strong>{(((parsedPreview.gst_tax_deductions + parsedPreview.other_deductions) / parsedPreview.gross_amount) * 100).toFixed(1)}%</strong>
                </div>
              )}
              {/* Daily breakdown for Cards with bank statement */}
              {(parsedPreview.platform === 'cards' || parsedPreview.platform === 'phonepe') && parsedPreview.raw_summary?.bank_statement_uploaded && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-gray-700">
                      {parsedPreview.platform === 'phonepe' ? 'Daily Settlement Breakdown' : 'Daily MDR Breakdown'}
                    </p>
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                      {parsedPreview.platform === 'phonepe'
                        ? `Settlements: ${parsedPreview.raw_summary.bank_settlements_matched}`
                        : `Avg MDR: ${parsedPreview.raw_summary.avg_mdr_rate}% | Settlements: ${parsedPreview.raw_summary.bank_settlements_matched}`
                      }
                    </span>
                  </div>
                  <div className="max-h-48 overflow-y-auto border rounded">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-50 sticky top-0">
                        <tr>
                          <th className="text-left p-2">Date</th>
                          <th className="text-right p-2">EDC Amt</th>
                          <th className="text-right p-2">Bank Credit</th>
                          <th className="text-right p-2">Charge</th>
                          <th className="text-right p-2">%</th>
                          <th className="text-right p-2">Txns</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(parsedPreview.raw_summary.daily_breakdown || []).filter(d => d.edc_amount > 0 || d.bank_credit > 0).map((d, i) => (
                          <tr key={i} className={`border-t ${d.edc_amount > 0 && d.bank_credit === 0 ? 'bg-yellow-50' : d.edc_amount === 0 ? 'bg-gray-50' : ''}`}>
                            <td className="p-2">{d.date}</td>
                            <td className="p-2 text-right">{formatCurrency(d.edc_amount, accountSummary?.country)}</td>
                            <td className="p-2 text-right">{formatCurrency(d.bank_credit, accountSummary?.country)}</td>
                            <td className="p-2 text-right text-red-600">{formatCurrency(d.bank_charge, accountSummary?.country)}</td>
                            <td className="p-2 text-right">{d.charge_pct.toFixed(2)}%</td>
                            <td className="p-2 text-right">{d.txn_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {parsedPreview.raw_summary.unmatched_edc_days > 0 && (
                    <p className="text-xs text-amber-600">Note: {parsedPreview.raw_summary.unmatched_edc_days} day(s) have EDC transactions but no bank settlement yet (may settle next month).</p>
                  )}
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowPreviewModal(false); setParsedPreview(null); }}>Cancel</Button>
            <Button onClick={handleSaveCommission} disabled={loading} data-testid="confirm-save-commission">
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CheckCircle className="w-4 h-4 mr-2" />}
              Confirm & Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Link Franchise Modal */}
      <Dialog open={showLinkModal} onOpenChange={setShowLinkModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Link Center to Franchise</DialogTitle>
            <DialogDescription>Connect a center with its franchise profile</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Center</Label>
              <Select value={linkForm.center_code} onValueChange={(v) => setLinkForm(p => ({ ...p, center_code: v }))}>
                <SelectTrigger>
                  <SelectValue placeholder="Select center" />
                </SelectTrigger>
                <SelectContent>
                  {linkageStatus?.centers?.filter(c => !c.linked).map(c => (
                    <SelectItem key={c.code} value={c.code}>{c.code} - {c.name || c.code}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Franchise</Label>
              <Select value={linkForm.franchise_code} onValueChange={(v) => setLinkForm(p => ({ ...p, franchise_code: v }))}>
                <SelectTrigger>
                  <SelectValue placeholder="Select franchise" />
                </SelectTrigger>
                <SelectContent>
                  {linkageStatus?.franchises?.map(f => (
                    <SelectItem key={f.franchise_code} value={f.franchise_code}>
                      {f.franchise_code} - {f.franchise_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLinkModal(false)}>Cancel</Button>
            <Button onClick={handleLinkFranchise} disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Link className="w-4 h-4 mr-2" />}
              Link
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Record Payment Modal */}
      <Dialog open={showPaymentModal} onOpenChange={setShowPaymentModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editingPayment ? 'Edit Payment' : 'Record Payment'}</DialogTitle>
            <DialogDescription>
              {selectedPayoutMonth && (
                <>
                  {editingPayment ? 'Update' : 'Record'} payment for {new Date(selectedPayoutMonth.month + '-01').toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}
                  <br />
                  <span className="text-xs">
                    Payable: {formatCurrency(selectedPayoutMonth.payable_amount, accountSummary?.country)} | 
                    Pending: {formatCurrency(selectedPayoutMonth.pending, accountSummary?.country)}
                  </span>
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {/* Existing payments list */}
            {selectedPayoutMonth?.payments?.length > 0 && !editingPayment && (
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-3 py-2 text-xs font-medium text-gray-600">
                  Payment History ({selectedPayoutMonth.payments.length})
                </div>
                <div className="max-h-40 overflow-y-auto divide-y">
                  {selectedPayoutMonth.payments.map((p) => (
                    <div key={p.payment_id} className="flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-50">
                      <div className="flex-1">
                        <span className="font-medium text-green-700">{formatCurrency(p.amount, accountSummary?.country)}</span>
                        <span className="text-gray-400 mx-2">|</span>
                        <span className="text-gray-500 text-xs">{p.payment_date}</span>
                        {p.notes && <span className="text-gray-400 text-xs ml-2">({p.notes})</span>}
                      </div>
                      <div className="flex gap-1 ml-2">
                        <Button 
                          size="sm" variant="ghost" className="h-7 w-7 p-0 text-blue-600 hover:text-blue-800"
                          onClick={() => startEditPayment(p)}
                          data-testid={`edit-payment-${p.payment_id}`}
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </Button>
                        <Button 
                          size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-600 hover:text-red-800"
                          onClick={() => handleDeletePayment(p.payment_id)}
                          data-testid={`delete-payment-${p.payment_id}`}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedPayoutMonth && !editingPayment && (
              <div className="p-3 bg-gray-50 rounded-lg space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Total {accountSummary?.share_calculation?.type === 'profit_share' ? 'Profit Share' : 'Revenue Share'} Payable:</span>
                  <span className="font-medium">{formatCurrency(selectedPayoutMonth.payable_amount, accountSummary?.country)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Already Paid:</span>
                  <span className="text-green-600">{formatCurrency(selectedPayoutMonth.paid, accountSummary?.country)}</span>
                </div>
                <div className="flex justify-between font-medium">
                  <span className="text-gray-500">Pending:</span>
                  <span className="text-red-600">{formatCurrency(selectedPayoutMonth.pending, accountSummary?.country)}</span>
                </div>
              </div>
            )}
            <div>
              <Label>Payment Amount *</Label>
              <Input 
                type="number" 
                value={paymentForm.amount}
                onChange={(e) => setPaymentForm(p => ({ ...p, amount: parseFloat(e.target.value) || 0 }))}
                placeholder="Enter amount"
                data-testid="payment-amount-input"
              />
            </div>
            <div>
              <Label>Payment Date *</Label>
              <Input 
                type="date" 
                value={paymentForm.payment_date}
                onChange={(e) => setPaymentForm(p => ({ ...p, payment_date: e.target.value }))}
                data-testid="payment-date-input"
              />
            </div>
            <div>
              <Label>Notes (Optional)</Label>
              <Input 
                value={paymentForm.notes}
                onChange={(e) => setPaymentForm(p => ({ ...p, notes: e.target.value }))}
                placeholder="e.g., Bank transfer, Cheque #123"
              />
            </div>
          </div>
          <DialogFooter>
            {editingPayment && (
              <Button variant="outline" onClick={() => {
                setEditingPayment(null);
                setPaymentForm({ amount: selectedPayoutMonth?.pending || 0, payment_date: new Date().toISOString().split('T')[0], notes: '' });
              }}>Cancel Edit</Button>
            )}
            <Button variant="outline" onClick={() => { setShowPaymentModal(false); setEditingPayment(null); }}>Close</Button>
            <Button 
              onClick={editingPayment ? handleUpdatePayment : handleRecordPayment} 
              disabled={loading} 
              className={editingPayment ? "bg-blue-600 hover:bg-blue-700" : "bg-green-600 hover:bg-green-700"}
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : editingPayment ? <Pencil className="w-4 h-4 mr-2" /> : <DollarSign className="w-4 h-4 mr-2" />}
              {editingPayment ? 'Update Payment' : 'Record Payment'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* PIB Preview Dialog — View before Download */}
      <Dialog open={!!pibPreview} onOpenChange={(open) => {
        if (!open) {
          if (pibPreview?.pdfBlobUrl) URL.revokeObjectURL(pibPreview.pdfBlobUrl);
          setPibPreview(null);
        }
      }}>
        <DialogContent className="max-w-6xl max-h-[92vh] overflow-y-auto" data-testid="pib-preview-dialog">
          <DialogHeader>
            <DialogTitle>PIB Report Preview — {selectedCenter} · {selectedMonth}</DialogTitle>
            <DialogDescription>Full report below. Scroll or use Download to save the PDF.</DialogDescription>
          </DialogHeader>
          {pibPreviewLoading || (pibPreview && pibPreview.loading) ? (
            <div className="py-12 text-center text-muted-foreground">Loading preview…</div>
          ) : pibPreview?.summary ? (
            <div className="space-y-4 text-sm" data-testid="pib-preview-content">
              {(() => {
                const s = pibPreview.summary;
                const sales = s.sales || {};
                const finCur = s.financial_summary || s.financial || s.summary || {};
                const comms = s.commissions || {};
                const revShare = s.share_calculation || s.revenue_share || {};
                // Canonical Revenue Share Base = Sales − Commissions − GST (matches main dashboard tile).
                // Falls back to net_revenue only if the canonical field is unavailable.
                const rsBase = s.operational_sustainability?.revenue_share_base
                  ?? finCur.net_revenue ?? finCur.profit ?? finCur.pnl ?? 0;
                const ownerPct = revShare.franchise_owner?.percentage
                  ?? s.payout_summary?.franchise?.revenue_share_percentage
                  ?? 15;
                const _previewModelWord = (s.payout_model === 'profit_share') ? 'Profit Share' : 'Revenue Share';
                // Revenue Share = Revenue Share Base × Franchise % (gross, ungated).
                // Protection-Mode gating is communicated separately via the payout status banner.
                const revenueShareAmount = Math.round((rsBase || 0) * (ownerPct || 0) / 100);
                const pnlFig = rsBase;
                return (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      <div className="rounded-lg border p-3 bg-blue-50 dark:bg-blue-900/20">
                        <p className="text-xs text-muted-foreground">Total Sale</p>
                        <p className="text-lg font-bold">₹{Math.round(sales.total_sale || finCur.total_sales || finCur.total_sale || 0).toLocaleString('en-IN')}</p>
                      </div>
                      <div className="rounded-lg border p-3 bg-rose-50 dark:bg-rose-900/20">
                        <p className="text-xs text-muted-foreground">GST ({finCur.sales_gst_rate || '5%'} × eligible)</p>
                        <p className="text-lg font-bold">₹{Math.round(finCur.sales_gst || finCur.sales_gst_amount || finCur.gst || 0).toLocaleString('en-IN')}</p>
                      </div>
                      <div className="rounded-lg border p-3 bg-orange-50 dark:bg-orange-900/20">
                        <p className="text-xs text-muted-foreground">Total Commission</p>
                        <p className="text-lg font-bold">₹{Math.round(comms.total || finCur.total_commissions || finCur.total_commission || finCur.commission || 0).toLocaleString('en-IN')}</p>
                      </div>
                      <div className="rounded-lg border p-3 bg-amber-50 dark:bg-amber-900/20">
                        <p className="text-xs text-muted-foreground">Total Expenses</p>
                        <p className="text-lg font-bold">₹{Math.round(finCur.total_expenses || finCur.expenses || 0).toLocaleString('en-IN')}</p>
                      </div>
                      <div className="rounded-lg border-2 border-sky-300 p-3 bg-sky-50 dark:bg-sky-900/20" title={`Sales − Commissions − GST. Canonical base for the ${_previewModelWord.toLowerCase()} split.`}>
                        <p className="text-xs font-semibold text-sky-700">⭐ {_previewModelWord} Base</p>
                        <p className="text-lg font-bold text-sky-900">₹{Math.round(pnlFig || 0).toLocaleString('en-IN')}</p>
                      </div>
                      <div className="rounded-lg border p-3 bg-purple-50 dark:bg-purple-900/20" title={`${_previewModelWord} Base × ${ownerPct}% (gross, before any Protection-Mode gating).`}>
                        <p className="text-xs text-muted-foreground">{_previewModelWord} ({ownerPct}%)</p>
                        <p className="text-lg font-bold">₹{revenueShareAmount.toLocaleString('en-IN')}</p>
                      </div>
                    </div>

                    {/* Full PDF rendered inline — exact mirror of what download would save */}
                    {pibPreview.pdfBlobUrl ? (
                      <div className="border rounded-lg overflow-hidden bg-stone-900" data-testid="pib-preview-pdf-iframe">
                        <div className="px-3 py-2 bg-stone-100 text-xs text-stone-700 border-b flex items-center justify-between">
                          <span>Full PIB Report (PDF)</span>
                          <a href={pibPreview.pdfBlobUrl} target="_blank" rel="noopener noreferrer"
                             className="text-blue-700 hover:underline text-[11px]">Open in new tab ↗</a>
                        </div>
                        <iframe
                          src={pibPreview.pdfBlobUrl}
                          title="PIB Report PDF"
                          className="w-full"
                          style={{ height: '70vh', border: 'none' }}
                        />
                      </div>
                    ) : (
                      <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
                        PDF could not be rendered inline. Use Download below.
                      </div>
                    )}

                    <details className="rounded-lg border p-2 bg-muted/20">
                      <summary className="cursor-pointer text-xs font-semibold">Show raw summary JSON</summary>
                      <pre className="text-[10px] mt-2 overflow-auto max-h-60">{JSON.stringify(s, null, 2)}</pre>
                    </details>
                  </>
                );
              })()}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground py-8">No data to preview.</p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              if (pibPreview?.pdfBlobUrl) URL.revokeObjectURL(pibPreview.pdfBlobUrl);
              setPibPreview(null);
            }} data-testid="pib-preview-cancel">Close</Button>
            <Button
              onClick={async () => {
                try {
                  const res = await fetch(`${API}/api/center-accounts/generate-pib`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token, center: selectedCenter, month: selectedMonth }),
                  });
                  if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Failed'); }
                  const blob = await res.blob();
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url; a.download = `PIB_${selectedCenter}_${selectedMonth}.pdf`;
                  a.click(); window.URL.revokeObjectURL(url);
                  toast.success('PIB downloaded');
                  setPibPreview(null);
                } catch (e) { toast.error(e.message); }
              }}
              className="bg-[#8B0000] hover:bg-[#6B0000]"
              disabled={!pibPreview?.summary}
              data-testid="pib-preview-download"
            >
              <Download className="w-4 h-4 mr-1" /> Download PDF
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Generic PDF Preview (GST / Commission) */}
      <Dialog open={!!pdfPreview} onOpenChange={(open) => {
        if (!open) {
          if (pdfPreview?.url) window.URL.revokeObjectURL(pdfPreview.url);
          setPdfPreview(null);
        }
      }}>
        <DialogContent className="max-w-5xl max-h-[90vh]" data-testid="pdf-preview-dialog">
          <DialogHeader>
            <DialogTitle>{pdfPreview?.title} — {selectedCenter} · {selectedMonth}</DialogTitle>
            <DialogDescription>Review the report, then click Download to save.</DialogDescription>
          </DialogHeader>
          {pdfPreviewLoading || pdfPreview?.loading ? (
            <div className="py-16 text-center text-muted-foreground"><Loader2 className="w-6 h-6 animate-spin inline-block mr-2" />Loading preview…</div>
          ) : pdfPreview?.url ? (
            <iframe src={pdfPreview.url} className="w-full" style={{ height: '70vh' }} title={pdfPreview.title} data-testid="pdf-preview-iframe" />
          ) : (
            <p className="text-sm text-muted-foreground py-8">No data to preview.</p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              if (pdfPreview?.url) window.URL.revokeObjectURL(pdfPreview.url);
              setPdfPreview(null);
            }}>Close</Button>
            <Button onClick={() => {
              if (!pdfPreview?.url) return;
              const a = document.createElement('a');
              a.href = pdfPreview.url;
              a.download = `${pdfPreview.title.replace(/\s/g, '_')}_${selectedCenter}_${selectedMonth}.pdf`;
              a.click();
              toast.success('Downloaded');
            }} className="bg-[#8B0000] hover:bg-[#6B0000]" disabled={!pdfPreview?.url}>
              <Download className="w-4 h-4 mr-1" /> Download PDF
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Email Pack Dialog */}
      <Dialog open={!!emailPack} onOpenChange={(open) => { if (!open) { setEmailPack(null); setSendForm(null); } }}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" data-testid="email-pack-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><Mail className="w-5 h-5 text-rose-700" /> Monthly Email Pack — {selectedCenter} · {selectedMonth}</DialogTitle>
            <DialogDescription>Beautifully formatted email + ZIP bundle (PIB, GST, Commission, Sales/Expense Excel + uploaded raw files) ready to send.</DialogDescription>
          </DialogHeader>
          {emailPackLoading ? (
            <div className="py-12 text-center text-muted-foreground"><Loader2 className="w-6 h-6 animate-spin inline-block mr-2" />Building bundle…</div>
          ) : emailPack ? (
            <div className="space-y-4">
              <div>
                <Label className="text-xs uppercase tracking-wider">Subject</Label>
                <Input readOnly value={emailPack.subject || ''} className="font-medium" data-testid="email-pack-subject" />
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wider">Body</Label>
                <textarea
                  readOnly
                  value={emailPack.body || ''}
                  className="w-full min-h-[280px] p-3 rounded border bg-muted/30 font-mono text-xs leading-relaxed"
                  data-testid="email-pack-body"
                />
              </div>
              <div className="rounded-lg border p-3 bg-rose-50/40">
                <p className="text-xs font-semibold text-rose-900 mb-1">Bundle Contents ({(emailPack.attachments || []).length} files)</p>
                <ul className="text-xs space-y-0.5">
                  {(emailPack.attachments || []).map((a, i) => (
                    <li key={i} className="flex items-center gap-2">
                      <FileText className="w-3 h-3 text-rose-700" /> {a.filename} <span className="text-muted-foreground">({a.size_kb} KB)</span>
                    </li>
                  ))}
                </ul>
              </div>
              {/* Direct Send via SMTP — optional one-click delivery */}
              {sendForm && (
                <div className="rounded-lg border-2 border-blue-300 p-3 bg-blue-50/50 space-y-2" data-testid="email-pack-send-form">
                  <p className="text-sm font-semibold text-blue-900 flex items-center gap-2"><Mail className="w-4 h-4" /> Send Email Directly via SMTP</p>
                  <div className="grid sm:grid-cols-2 gap-2">
                    <div>
                      <Label className="text-xs">To (recipient email)</Label>
                      <Input type="email" placeholder="owner@example.com" value={sendForm.to} onChange={e => setSendForm({...sendForm, to: e.target.value})} data-testid="email-pack-send-to" />
                    </div>
                    <div>
                      <Label className="text-xs">CC (optional)</Label>
                      <Input type="email" placeholder="accounts@purnabramha.com" value={sendForm.cc} onChange={e => setSendForm({...sendForm, cc: e.target.value})} data-testid="email-pack-send-cc" />
                    </div>
                  </div>
                  <div className="flex gap-2 justify-end">
                    <Button size="sm" variant="ghost" onClick={() => setSendForm(null)}>Cancel</Button>
                    <Button size="sm" className="bg-blue-700 hover:bg-blue-800 text-white"
                            disabled={!sendForm.to || sendForm.sending}
                            onClick={async () => {
                              setSendForm({...sendForm, sending: true});
                              try {
                                const res = await fetch(`${API}/api/center-accounts/email-pack/send`, {
                                  method: 'POST', headers: { 'Content-Type': 'application/json' },
                                  body: JSON.stringify({
                                    token, center: selectedCenter, month: selectedMonth,
                                    to_email: sendForm.to, cc: sendForm.cc || null,
                                    subject: emailPack.subject, body: emailPack.body,
                                  }),
                                });
                                const data = await res.json();
                                if (!res.ok) throw new Error(data.detail || 'Send failed');
                                toast.success(`Email sent to ${data.to} (${data.size_kb} KB)`);
                                setSendForm(null);
                              } catch (e) {
                                toast.error(e.message || 'Send failed');
                                setSendForm(s => ({...s, sending: false}));
                              }
                            }}
                            data-testid="email-pack-send-submit">
                      {sendForm.sending ? <><Loader2 className="w-3 h-3 animate-spin mr-1" />Sending…</> : <><Mail className="w-3.5 h-3.5 mr-1" />Send Now</>}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ) : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => { setEmailPack(null); setSendForm(null); }}>Close</Button>
            <Button variant="outline" disabled={!emailPack} onClick={() => {
              navigator.clipboard.writeText(`Subject: ${emailPack.subject}\n\n${emailPack.body}`);
              toast.success('Email subject + body copied');
            }} data-testid="email-pack-copy">
              Copy Email Text
            </Button>
            <Button variant="outline" disabled={!emailPack || !!sendForm}
                    onClick={() => setSendForm({ to: '', cc: '', sending: false })}
                    className="border-blue-400 text-blue-700 hover:bg-blue-50" data-testid="email-pack-send-open">
              <Mail className="w-4 h-4 mr-1" /> Send via SMTP
            </Button>
            <Button disabled={!emailPack} onClick={() => {
              const a = document.createElement('a');
              a.href = emailPack.zip_url; a.download = emailPack.zip_filename || `Email_Pack_${selectedCenter}_${selectedMonth}.zip`;
              a.click();
              toast.success('Bundle downloaded');
            }} className="bg-rose-700 hover:bg-rose-800 text-white" data-testid="email-pack-download">
              <Download className="w-4 h-4 mr-1" /> Download ZIP Bundle
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
