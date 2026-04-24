import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@/App';
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
  Check, X, Shield, Save
} from 'lucide-react';

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

  const openPibPreview = async () => {
    if (!selectedCenter || !selectedMonth) { toast.error('Please select center and month'); return; }
    setPibPreviewLoading(true);
    setPibPreview({ loading: true });
    try {
      const res = await fetch(`${API}/api/center-accounts/preview-pib`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, center: selectedCenter, month: selectedMonth }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to load preview');
      }
      setPibPreview(await res.json());
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
    
    const endpoints = {
      pib: 'generate-pib',
      gst: 'generate-gst-summary',
      commission: 'generate-commission-summary'
    };
    
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

          {/* Key Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
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
                    <p className="text-2xl font-bold text-orange-800">
                      {formatCurrency(accountSummary.commissions.total, accountSummary.country)}
                    </p>
                  </div>
                  <CreditCard className="w-8 h-8 text-orange-400" />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-green-50 to-green-100">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-green-600">Net Revenue</p>
                    <p className="text-2xl font-bold text-green-800">
                      {formatCurrency(accountSummary.financial_summary.net_revenue, accountSummary.country)}
                    </p>
                  </div>
                  <TrendingUp className="w-8 h-8 text-green-400" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Main Content Tabs */}
          <Tabs defaultValue="overview" className="space-y-4">
            <TabsList className="flex-wrap">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="sales">Sales Breakdown</TabsTrigger>
              <TabsTrigger value="commissions">Commissions</TabsTrigger>
              <TabsTrigger value="share">Revenue/Profit Share</TabsTrigger>
              <TabsTrigger value="payout">MG & Payout</TabsTrigger>
              <TabsTrigger value="reports">Reports</TabsTrigger>
              <TabsTrigger value="invoices" className="text-purple-600">Invoice Export</TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview" className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                {/* Center Info */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Building2 className="w-5 h-5" />
                      Center Information
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-500">Center Code</span>
                        <span className="font-medium">{accountSummary.center}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Country</span>
                        <Badge variant={accountSummary.country === 'Australia' ? 'secondary' : 'default'}>
                          {accountSummary.country}
                        </Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Period</span>
                        <span className="font-medium">{accountSummary.period}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Sales Days</span>
                        <span className="font-medium">{accountSummary.sales.num_days} days</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Franchise Info */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <ShoppingBag className="w-5 h-5" />
                      Franchise Information
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {accountSummary.franchise.linked ? (
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-gray-500">Franchise Code</span>
                          <span className="font-medium">{accountSummary.franchise.code}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Franchise Name</span>
                          <span className="font-medium">{accountSummary.franchise.name}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Legal Entity</span>
                          <span className="font-medium text-sm">{accountSummary.franchise.legal_entity}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Status</span>
                          <Badge className="bg-green-100 text-green-800">
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Linked
                          </Badge>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-6 text-gray-500">
                        <Unlink className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                        <p>No franchise linked</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* WC Status Banner */}
              {wcTableData?.revenue_share_status === "stopped" && (
                <div className="p-4 bg-red-50 border-2 border-red-300 rounded-lg" data-testid="wc-closed-banner">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-red-800">Revenue Share / Profit Share STOPPED</p>
                      <p className="text-sm text-red-700">Working Capital is at or below 50% of initial. Revenue Share will resume once WC is restored.</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Working Capital Summary Cards */}
              {wcTableData && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="wc-summary-cards">
                  <div className="p-4 rounded-xl bg-gradient-to-br from-blue-50 to-blue-100/50 border border-blue-200/60 shadow-sm">
                    <p className="text-xs text-blue-600 font-medium">Initial WC</p>
                    <p className="text-lg font-bold text-blue-800">{formatCurrency(wcTableData.initial_wc, accountSummary?.country)}</p>
                    {wcEditingInitial ? (
                      <div className="flex gap-1 mt-1">
                        <Input type="number" value={wcInitialValue} onChange={(e) => setWcInitialValue(e.target.value)} className="h-7 text-xs w-28" data-testid="wc-initial-input" />
                        <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => saveWcOverride(null, wcInitialValue)}><Check className="w-3 h-3 text-green-600" /></Button>
                        <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => setWcEditingInitial(false)}><X className="w-3 h-3 text-red-600" /></Button>
                      </div>
                    ) : (
                      <Button variant="ghost" size="sm" className="h-5 px-1 text-xs mt-1" onClick={() => { setWcEditingInitial(true); setWcInitialValue(wcTableData.initial_wc); }} data-testid="edit-initial-wc-btn">
                        <Pencil className="w-3 h-3 mr-1" /> Edit
                      </Button>
                    )}
                  </div>
                  <div className={`p-4 rounded-xl border shadow-sm ${wcTableData.current_wc >= wcTableData.initial_wc ? 'bg-gradient-to-br from-green-50 to-green-100/50 border-green-200/60' : wcTableData.current_wc > wcTableData.initial_wc * 0.5 ? 'bg-gradient-to-br from-amber-50 to-amber-100/50 border-amber-200/60' : 'bg-gradient-to-br from-red-50 to-red-100/50 border-red-200/60'}`}>
                    <p className="text-xs font-medium text-gray-600">Current WC</p>
                    <p className={`text-lg font-bold ${wcTableData.current_wc >= wcTableData.initial_wc ? 'text-green-800' : wcTableData.current_wc > wcTableData.initial_wc * 0.5 ? 'text-amber-800' : 'text-red-800'}`}>
                      {formatCurrency(wcTableData.current_wc, accountSummary?.country)}
                    </p>
                    <p className="text-xs text-gray-500">{wcTableData.initial_wc > 0 ? ((wcTableData.current_wc / wcTableData.initial_wc) * 100).toFixed(0) : 0}% of initial</p>
                  </div>
                  <div className="p-4 rounded-xl bg-gradient-to-br from-gray-50 to-gray-100/50 border border-gray-200/60 shadow-sm">
                    <p className="text-xs font-medium text-gray-600">P/L This Month</p>
                    {wcTableData.rows?.length > 0 && (() => {
                      const last = wcTableData.rows[wcTableData.rows.length - 1];
                      return <p className={`text-lg font-bold ${last.pnl >= 0 ? 'text-green-700' : 'text-red-700'}`}>{formatCurrency(last.pnl, accountSummary?.country)}</p>;
                    })()}
                  </div>
                  <div className={`p-4 rounded-xl border shadow-sm ${wcTableData.revenue_share_status === 'active' ? 'bg-gradient-to-br from-emerald-50 to-emerald-100/50 border-emerald-200/60' : 'bg-gradient-to-br from-red-50 to-red-100/50 border-red-200/60'}`}>
                    <p className="text-xs font-medium text-gray-600">Revenue Share</p>
                    <p className={`text-lg font-bold ${wcTableData.revenue_share_status === 'active' ? 'text-emerald-700' : 'text-red-700'}`}>
                      {wcTableData.revenue_share_status === 'active' ? 'Active' : 'Stopped'}
                    </p>
                    <p className="text-xs text-gray-500">50% threshold</p>
                  </div>
                  <div className="p-4 rounded-xl bg-gradient-to-br from-purple-50 to-purple-100/50 border border-purple-200/60 shadow-sm">
                    <p className="text-xs text-purple-600 font-medium">Last Top-up</p>
                    {wcTableData.last_topup ? (
                      <>
                        <p className="text-lg font-bold text-purple-800">{formatCurrency(wcTableData.last_topup.amount, accountSummary?.country)}</p>
                        <p className="text-xs text-purple-500 truncate">{wcTableData.last_topup.reason || 'No reason'}</p>
                      </>
                    ) : (
                      <p className="text-sm text-purple-400 mt-1">None</p>
                    )}
                  </div>
                </div>
              )}

              {/* WC Actions */}
              <div className="flex gap-2 flex-wrap">
                <Button variant="outline" size="sm" onClick={fetchWcTable} disabled={wcLoading} className="gap-1">
                  <RefreshCw className={`w-4 h-4 ${wcLoading ? 'animate-spin' : ''}`} /> Refresh
                </Button>
                <Button variant="outline" size="sm" onClick={() => { setShowTopupDialog(true); setTopupMonth(new Date().toISOString().slice(0, 7)); }} className="gap-1 text-purple-600 border-purple-200" data-testid="wc-topup-btn">
                  <DollarSign className="w-4 h-4" /> Add Top-up / Adjustment
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setShowTopupLog(!showTopupLog)} className="gap-1 text-gray-500" data-testid="wc-log-btn">
                  <FileText className="w-4 h-4" /> {showTopupLog ? 'Hide' : 'Show'} Audit Log
                </Button>
              </div>

              {/* Top-up Audit Log */}
              {showTopupLog && wcTableData?.topup_log?.length > 0 && (
                <Card className="border-purple-200">
                  <CardContent className="pt-4">
                    <table className="w-full text-sm">
                      <thead><tr className="border-b"><th className="text-left py-1 px-2 text-xs text-muted-foreground">Date</th><th className="text-left py-1 px-2 text-xs text-muted-foreground">Month</th><th className="text-right py-1 px-2 text-xs text-muted-foreground">Amount</th><th className="text-left py-1 px-2 text-xs text-muted-foreground">Reason</th><th className="text-left py-1 px-2 text-xs text-muted-foreground">By</th></tr></thead>
                      <tbody>
                        {wcTableData.topup_log.map((t, i) => (
                          <tr key={i} className="border-b last:border-0">
                            <td className="py-1 px-2 text-xs">{new Date(t.date).toLocaleDateString()}</td>
                            <td className="py-1 px-2 text-xs">{t.month}</td>
                            <td className="py-1 px-2 text-xs text-right font-medium text-purple-600">{formatCurrency(t.amount, accountSummary?.country)}</td>
                            <td className="py-1 px-2 text-xs">{t.reason || '-'}</td>
                            <td className="py-1 px-2 text-xs">{t.added_by}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </CardContent>
                </Card>
              )}

              {/* Top-up Dialog */}
              {showTopupDialog && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                  <Card className="w-full max-w-md shadow-xl">
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2"><DollarSign className="w-5 h-5 text-purple-600" /> WC Top-up / Adjustment</CardTitle>
                      <CardDescription>Manual fund infusion or adjustment. This will be logged with audit trail.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div>
                        <label className="text-sm font-medium">Amount *</label>
                        <Input type="number" value={topupAmount} onChange={(e) => setTopupAmount(e.target.value)} placeholder="Enter amount (negative to deduct)" data-testid="topup-amount" />
                      </div>
                      <div>
                        <label className="text-sm font-medium">Month</label>
                        <Input type="month" value={topupMonth} onChange={(e) => setTopupMonth(e.target.value)} data-testid="topup-month" />
                      </div>
                      <div>
                        <label className="text-sm font-medium">Reason *</label>
                        <Input value={topupReason} onChange={(e) => setTopupReason(e.target.value)} placeholder="e.g., Fund arrangement, Partner infusion" data-testid="topup-reason" />
                      </div>
                    </CardContent>
                    <div className="flex justify-end gap-2 p-4 pt-0">
                      <Button variant="outline" onClick={() => setShowTopupDialog(false)}>Cancel</Button>
                      <Button onClick={addWcTopup} disabled={!topupAmount || !topupReason} data-testid="topup-confirm-btn">Add Top-up</Button>
                    </div>
                  </Card>
                </div>
              )}

              {/* Working Capital Month-by-Month Table */}
              <Card data-testid="wc-table-card">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Wallet className="w-5 h-5" /> Month-by-Month WC Breakdown
                      </CardTitle>
                      <CardDescription>P/L = Sale − Expenses − Commission. Opening WC = Last month's Balance WC. Balance WC = Opening WC + P/L + WC Adj. GST is shown for reference — it's paid as an expense in the following month (M+1).</CardDescription>
                    </div>
                    <Button size="sm" disabled={wcSaving || wcLoading} onClick={async () => {
                      if (!wcTableData?.rows) return;
                      setWcSaving(true);
                      try {
                        const saves = [];
                        wcTableData.rows.forEach(r => {
                          const edit = wcEdits[r.month];
                          if (!edit) return;
                          const origExpense = Math.round(r.expenses || 0);
                          const origAdj = Math.round(r.wc_adjustment || 0);
                          const origCommission = Math.round(r.commission || 0);
                          const origGst = Math.round(r.gst || 0);
                          const newExpense = Math.round(Number(edit.expense) || 0);
                          const newAdj = Math.round(Number(edit.wc_adj) || 0);
                          const newCommission = Math.round(Number(edit.commission) || 0);
                          const newGst = Math.round(Number(edit.gst) || 0);
                          const body = { token: session?.token, center: selectedCenter, month: r.month };
                          let dirty = false;
                          if (newExpense !== origExpense) {
                            body.target_expenses = newExpense;
                            dirty = true;
                          }
                          if (newAdj !== origAdj) {
                            body.wc_adjustment = newAdj;
                            dirty = true;
                          }
                          if (newCommission !== origCommission) {
                            body.commission_target = newCommission;
                            dirty = true;
                          }
                          if (newGst !== origGst) {
                            body.gst_target = newGst;
                            dirty = true;
                          }
                          if (dirty) {
                            saves.push(fetch(`${API}/api/center-accounts/wc-row-save`, {
                              method: 'POST', headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify(body)
                            }));
                          }
                        });
                        if (saves.length > 0) {
                          await Promise.all(saves);
                          await fetchWcTable();
                          toast.success(`Saved ${saves.length} row${saves.length > 1 ? 's' : ''} (Expense Master updated on last day of month)`);
                        } else {
                          toast.info("No changes to save");
                        }
                      } finally {
                        setWcSaving(false);
                      }
                    }} className="bg-[#8B0000] hover:bg-[#6B0000]" data-testid="wc-save-all-btn">
                      <Save className="w-4 h-4 mr-1" /> {wcSaving ? 'Saving...' : 'Save All'}
                    </Button>
                    <Button size="sm" variant="outline" onClick={async () => {
                      try {
                        const res = await fetch(`${API}/api/center-accounts/wc-table/export-pdf`, {
                          method: 'POST', headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ token: session?.token, center: selectedCenter })
                        });
                        if (!res.ok) { toast.error("PDF export failed"); return; }
                        const blob = await res.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a'); a.href = url;
                        a.download = `WC_Statement_${selectedCenter}.pdf`;
                        document.body.appendChild(a); a.click(); a.remove();
                        toast.success("PDF downloaded");
                      } catch { toast.error("PDF export failed"); }
                    }} data-testid="wc-pdf-btn">
                      <Download className="w-4 h-4 mr-1" /> PDF
                    </Button>
                    <Button size="sm" variant="outline" onClick={async () => {
                      try {
                        const res = await fetch(`${API}/api/center-accounts/wc-table/export-excel`, {
                          method: 'POST', headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ token: session?.token, center: selectedCenter })
                        });
                        if (!res.ok) { toast.error("Excel export failed"); return; }
                        const blob = await res.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a'); a.href = url;
                        a.download = `WC_Statement_${selectedCenter}.xlsx`;
                        document.body.appendChild(a); a.click(); a.remove();
                        toast.success("Excel downloaded");
                      } catch { toast.error("Excel export failed"); }
                    }} data-testid="wc-excel-btn">
                      <FileSpreadsheet className="w-4 h-4 mr-1" /> Excel
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  {wcLoading ? (
                    <div className="text-center py-8 text-muted-foreground">Loading...</div>
                  ) : computedWcRows.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm border-collapse" data-testid="wc-assessment-table">
                        <thead className="bg-muted sticky top-0">
                          <tr>
                            <th className="px-2 py-2 text-left font-medium text-muted-foreground border-b text-xs">Month</th>
                            <th className="px-2 py-2 text-right font-medium text-muted-foreground border-b text-xs">Sale</th>
                            <th className="px-2 py-2 text-right font-medium text-muted-foreground border-b text-xs bg-amber-50" title="Editable">Expenses</th>
                            <th className="px-2 py-2 text-right font-medium text-muted-foreground border-b text-xs bg-rose-50" title="Editable">GST</th>
                            <th className="px-2 py-2 text-right font-medium text-muted-foreground border-b text-xs bg-orange-50" title="Editable">Commission</th>
                            <th className="px-2 py-2 text-right font-medium text-muted-foreground border-b text-xs">P/L</th>
                            <th className="px-2 py-2 text-right font-medium text-muted-foreground border-b text-xs bg-blue-50">Working Capital</th>
                            <th className="px-2 py-2 text-right font-medium text-muted-foreground border-b text-xs bg-green-50">Bal. WC</th>
                            <th className="px-2 py-2 text-right font-medium text-muted-foreground border-b text-xs bg-cyan-50">Diff of WC</th>
                            <th className="px-2 py-2 text-right font-medium text-muted-foreground border-b text-xs bg-purple-50" title="Editable">WC Adj</th>
                            <th className="px-2 py-2 text-center font-medium text-muted-foreground border-b text-xs">Rev Share</th>
                          </tr>
                        </thead>
                        <tbody>
                          {computedWcRows.map((row) => {
                            const monthLabel = new Date(row.month + '-01').toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });
                            const fmt = (v) => Math.round(v).toLocaleString('en-IN');
                            const edit = wcEdits[row.month] || { expense: row.expenses, wc_adj: row.wc_adjustment || 0, commission: row.commission || 0, gst: row.gst || 0 };
                            const mergeEdit = (patch) => setWcEdits(prev => ({
                              ...prev,
                              [row.month]: {
                                expense: prev[row.month]?.expense ?? row.expenses ?? 0,
                                wc_adj: prev[row.month]?.wc_adj ?? row.wc_adjustment ?? 0,
                                commission: prev[row.month]?.commission ?? row.commission ?? 0,
                                gst: prev[row.month]?.gst ?? row.gst ?? 0,
                                ...patch,
                              }
                            }));
                            return (
                              <tr key={row.month} className={`border-b hover:bg-muted/30 ${row._dirty ? 'bg-yellow-50/60' : ''}`} data-testid={`wc-row-${row.month}`}>
                                <td className="px-2 py-2 font-medium text-xs">{monthLabel}{row._dirty && <span className="ml-1 text-[10px] text-amber-700" title="Unsaved change">*</span>}</td>
                                <td className="px-2 py-2 text-right font-mono text-xs">{fmt(row.sale)}</td>
                                <td className="px-2 py-2 text-right bg-amber-50/50">
                                  <input type="number"
                                    className="w-24 text-right font-mono text-xs border rounded px-1 py-0.5 bg-white"
                                    value={edit.expense}
                                    onChange={(e) => {
                                      const v = e.target.value === '' ? 0 : parseFloat(e.target.value);
                                      mergeEdit({ expense: isNaN(v) ? 0 : v });
                                    }}
                                    data-testid={`wc-expense-${row.month}`}
                                  />
                                </td>
                                <td className="px-2 py-2 text-right bg-rose-50/50">
                                  <input type="number"
                                    className="w-20 text-right font-mono text-xs border rounded px-1 py-0.5 bg-white"
                                    value={edit.gst}
                                    onChange={(e) => {
                                      const v = e.target.value === '' ? 0 : parseFloat(e.target.value);
                                      mergeEdit({ gst: isNaN(v) ? 0 : v });
                                    }}
                                    data-testid={`wc-gst-${row.month}`}
                                  />
                                </td>
                                <td className="px-2 py-2 text-right bg-orange-50/50">
                                  <input type="number"
                                    className="w-20 text-right font-mono text-xs border rounded px-1 py-0.5 bg-white"
                                    value={edit.commission}
                                    onChange={(e) => {
                                      const v = e.target.value === '' ? 0 : parseFloat(e.target.value);
                                      mergeEdit({ commission: isNaN(v) ? 0 : v });
                                    }}
                                    data-testid={`wc-commission-${row.month}`}
                                  />
                                </td>
                                <td className={`px-2 py-2 text-right font-mono text-xs font-semibold ${row.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                  {fmt(row.pnl)}
                                </td>
                                <td className="px-2 py-2 text-right font-mono text-xs bg-blue-50/50 font-medium">{fmt(row.opening_wc)}</td>
                                <td className="px-2 py-2 text-right font-mono text-xs bg-green-50/50 font-bold">{fmt(row.balance_wc)}</td>
                                <td className="px-2 py-2 text-right font-mono text-xs bg-cyan-50/50 font-bold">{fmt(row.diff_wc || row.balance_wc)}</td>
                                <td className="px-2 py-2 text-right bg-purple-50/50">
                                  <input type="number"
                                    className="w-20 text-right font-mono text-xs border rounded px-1 py-0.5 bg-white"
                                    value={edit.wc_adj}
                                    onChange={(e) => {
                                      const v = e.target.value === '' ? 0 : parseFloat(e.target.value);
                                      mergeEdit({ wc_adj: isNaN(v) ? 0 : v });
                                    }}
                                    data-testid={`wc-adj-${row.month}`}
                                  />
                                </td>
                                <td className="px-2 py-2 text-center">
                                  {row.rev_share_status === 'active' ? (
                                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700">Active</span>
                                  ) : row.rev_share_status === 'restoring' ? (
                                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700">Restoring</span>
                                  ) : (
                                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-700">Blocked</span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="text-center py-6 text-muted-foreground">No WC data for this center</div>
                  )}
                </CardContent>
              </Card>
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
                </CardContent>
              </Card>
            </TabsContent>

            {/* Commissions Tab — Upload-Driven */}
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
                          <th className="text-right p-3 text-sm font-medium">Net Payout</th>
                          <th className="text-right p-3 text-sm font-medium">Orders</th>
                          <th className="text-left p-3 text-sm font-medium">File</th>
                          <th className="text-center p-3 text-sm font-medium">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {commissionStatements.length === 0 ? (
                          <tr>
                            <td colSpan={9} className="text-center py-8 text-gray-500">
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
                    <p className="text-xl font-bold text-red-800">
                      {formatCurrency(accountSummary.commissions.total, accountSummary.country)}
                    </p>
                  </CardContent>
                </Card>
              </div>
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
                  <CardTitle className="text-lg">
                    {accountSummary.share_calculation.type === 'profit_share' 
                      ? `Profit Share Calculation (${accountSummary.share_calculation.franchise_owner?.percentage || 80}/${accountSummary.share_calculation.purnabramha?.percentage || 20} Split)`
                      : `Revenue Share Calculation (${accountSummary.share_calculation.franchise_owner?.percentage || 15}/${accountSummary.share_calculation.purnabramha?.percentage || 85} Split)`
                    }
                  </CardTitle>
                  <CardDescription>
                    {accountSummary.country === 'India' 
                      ? 'India: Revenue share model (% of total sales)'
                      : `${accountSummary.country}: Profit share model (% of net profit) - Fixed 80/20`}
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

                        {/* Step 2: Less GST on Sales (5%) */}
                        {accountSummary.financial_summary.sales_gst > 0 && (
                          <div className="flex justify-between text-sm items-center text-red-600">
                            <span className="pl-4">Less: GST on Sales (5%)</span>
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

                        {/* Result: Net Revenue */}
                        <div className="flex justify-between items-center bg-green-50 border border-green-200 rounded-lg px-4 py-3">
                          <span className="text-green-800 font-bold text-base">= Net Revenue (Base for Split)</span>
                          <span className="text-green-900 font-bold text-lg" data-testid="india-net-revenue">
                            {formatCurrency(accountSummary.financial_summary.net_revenue, accountSummary.country)}
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
                        <div className="flex justify-between text-sm text-gray-500">
                          <span className="pl-4">Less: Sales GST (10%)</span>
                          <span>-{formatCurrency(accountSummary.financial_summary.sales_gst, accountSummary.country)}</span>
                        </div>
                        <div className="flex justify-between text-sm font-medium border-t pt-1">
                          <span>Sales (Ex GST)</span>
                          <span>{formatCurrency(accountSummary.financial_summary.sales_ex_gst, accountSummary.country)}</span>
                        </div>
                        <div className="flex justify-between text-sm text-red-600">
                          <span>Less: Expenses</span>
                          <span>-{formatCurrency(accountSummary.financial_summary.total_expenses, accountSummary.country)}</span>
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
                        <div className="flex justify-between items-center bg-green-50 border border-green-200 rounded-lg px-4 py-3">
                          <span className="text-green-800 font-bold">= Net Profit (for Share Calculation)</span>
                          <span className="text-green-900 font-bold text-lg">{formatCurrency(accountSummary.financial_summary.net_revenue, accountSummary.country)}</span>
                        </div>
                        <div className="flex items-start gap-2 mt-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                          <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
                          <p className="text-xs text-amber-800">
                            <strong>Profit Share GST:</strong> 10% GST is applied on profit share for Australia.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Base Amount */}
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">
                          {accountSummary.share_calculation.type === 'profit_share' 
                            ? `Net Profit (Base for ${accountSummary.share_calculation.franchise_owner?.percentage || 80}/${accountSummary.share_calculation.purnabramha?.percentage || 20} Split)` 
                            : `Net Revenue (Base for ${accountSummary.share_calculation.franchise_owner?.percentage || 15}/${accountSummary.share_calculation.purnabramha?.percentage || 85} Split)`}
                        </span>
                        <span className="text-xl font-bold">
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
                            <h4 className="font-medium text-green-800">Franchise Owner Share</h4>
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
                            <h4 className="font-medium text-orange-800">Purnabramha LLC Share</h4>
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
                              <span className="text-orange-800">Total Payable</span>
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
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Reports Tab */}
            <TabsContent value="reports" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Generate Reports</CardTitle>
                  <CardDescription>Download PDF reports for the selected period</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-3 gap-4">
                    <Card className="border-2 hover:border-blue-300 transition-colors cursor-pointer" onClick={() => downloadReport('pib')}>
                      <CardContent className="p-6 text-center">
                        <FileText className="w-12 h-12 mx-auto mb-3 text-blue-600" />
                        <h4 className="font-medium">PIB Report</h4>
                        <p className="text-sm text-gray-500 mt-1">Complete Profit & Income Balance</p>
                        <Button className="mt-4 w-full" variant="outline" disabled={!accountSummary?.franchise?.linked}>
                          <Download className="w-4 h-4 mr-2" />
                          Download
                        </Button>
                        {!accountSummary?.franchise?.linked && (
                          <p className="text-xs text-red-500 mt-2">Link franchise first</p>
                        )}
                      </CardContent>
                    </Card>

                    <Card className="border-2 hover:border-green-300 transition-colors cursor-pointer" onClick={() => downloadReport('gst')}>
                      <CardContent className="p-6 text-center">
                        <Calculator className="w-12 h-12 mx-auto mb-3 text-green-600" />
                        <h4 className="font-medium">GST Summary</h4>
                        <p className="text-sm text-gray-500 mt-1">Tax calculation breakdown</p>
                        <Button className="mt-4 w-full" variant="outline">
                          <Download className="w-4 h-4 mr-2" />
                          Download
                        </Button>
                      </CardContent>
                    </Card>

                    <Card className="border-2 hover:border-orange-300 transition-colors cursor-pointer" onClick={() => downloadReport('commission')}>
                      <CardContent className="p-6 text-center">
                        <CreditCard className="w-12 h-12 mx-auto mb-3 text-orange-600" />
                        <h4 className="font-medium">Commission Summary</h4>
                        <p className="text-sm text-gray-500 mt-1">Aggregator & card commissions</p>
                        <Button className="mt-4 w-full" variant="outline">
                          <Download className="w-4 h-4 mr-2" />
                          Download
                        </Button>
                      </CardContent>
                    </Card>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* MG & Payout Tab */}
            <TabsContent value="payout" className="space-y-4">
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
              {/* MG Calculation Card */}
              {accountSummary.mg_calculation && (
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
                    <CardDescription>Operational Balance = Sales - Expenses - Commissions - GST</CardDescription>
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
                      <div className="p-3 bg-amber-50 rounded text-center">
                        <p className="text-xs text-gray-500">GST on Sales</p>
                        <p className="text-lg font-bold text-amber-600">({formatCurrency(accountSummary.operational_sustainability.gst_on_sales, accountSummary.country)})</p>
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
                        <p className="text-xs text-gray-500">Revenue Share</p>
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
                        <strong>Protection Mode Active:</strong> WC is below 50% of Base. MG payouts are blocked. Revenue share blocked. All profit directed to WC recovery.
                      </div>
                    )}
                    {accountSummary.working_capital_status.status === 'Restoring' && !accountSummary.working_capital_status.protection_mode && (
                      <div className="p-3 bg-amber-100 border border-amber-300 rounded text-sm text-amber-800">
                        <strong>WC Restoring:</strong> Working Capital is between 50-100% of Base. Revenue share is blocked until WC is fully restored to Base level. Profits are being used to restore WC.
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Payout Determination Card */}
              {accountSummary.payout && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Wallet className="w-5 h-5" />
                      Payout to Franchise Owner - {accountSummary.period}
                    </CardTitle>
                    <CardDescription>
                      {accountSummary.payout.protection_mode
                        ? "Protection Mode: Revenue share on operational balance only. MG blocked."
                        : "Comparison: MG vs Franchise Owner's Revenue Share - Higher amount is payable to Franchise Owner"
                      }
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid md:grid-cols-3 gap-4">
                      <Card className={`border-2 ${accountSummary.payout.type === 'minimum_guarantee' ? 'border-purple-400 bg-purple-50' : 'border-gray-200'} ${accountSummary.payout.protection_mode ? 'opacity-50' : ''}`}>
                        <CardContent className="p-4 text-center">
                          <p className="text-sm text-gray-500">Minimum Guarantee</p>
                          <p className="text-2xl font-bold text-purple-600">
                            {formatCurrency(accountSummary.payout.mg_amount, accountSummary.country)}
                          </p>
                          {accountSummary.payout.type === 'minimum_guarantee' && !accountSummary.payout.protection_mode && (
                            <Badge className="mt-2 bg-purple-600">Payable</Badge>
                          )}
                          {accountSummary.payout.protection_mode && (
                            <Badge className="mt-2 bg-red-600 text-white">BLOCKED</Badge>
                          )}
                        </CardContent>
                      </Card>
                      <div className="flex items-center justify-center">
                        <span className="text-2xl font-bold text-gray-400">vs</span>
                      </div>
                      <Card className={`border-2 ${accountSummary.payout.type === 'revenue_share' || accountSummary.payout.type === 'revenue_share_protection' ? 'border-green-400 bg-green-50' : 'border-gray-200'} ${accountSummary.payout.protection_mode && accountSummary.payout.operational_balance <= 0 ? 'opacity-50' : ''}`}>
                        <CardContent className="p-4 text-center">
                          <p className="text-sm text-gray-500">Franchise Owner's Revenue Share ({accountSummary.share_calculation?.franchise_owner?.percentage || 15}%)</p>
                          <p className="text-2xl font-bold text-green-600">
                            {formatCurrency(accountSummary.payout.revenue_share_amount, accountSummary.country)}
                          </p>
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
                          {accountSummary.payout.protection_mode ? 'PROTECTION MODE' : accountSummary.payout.type === 'minimum_guarantee' ? 'MG' : 'Revenue Share'}
                        </Badge>
                      </div>
                      <p className={`text-xs mt-2 ${accountSummary.payout.protection_mode ? 'text-red-500' : 'text-blue-500'}`}>{accountSummary.payout.reason}</p>
                      <p className="text-xs mt-2 text-gray-500 italic">Revenue share distribution follows Operational Sustainability rules. Operational costs and working capital protection are prioritized before profit distribution.</p>
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
                      <strong>Note:</strong> 18% GST (CGST 9% + SGST 9%) on Revenue Share is shown for reference only and is <strong>not included</strong> in Purnabramha's total payable amount. For outside India, 10% GST is applicable on Profit Share.
                    </p>
                  </div>
                </div>
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
                          <p className="text-xs text-blue-600">Total Revenue Share</p>
                          <p className="text-lg font-bold text-blue-800">{formatCurrency(payoutSummary.totals?.revenue_share, accountSummary?.country)}</p>
                        </div>
                        <div className="p-3 bg-purple-50 rounded-lg text-center">
                          <p className="text-xs text-purple-600">Monthly MG</p>
                          <p className="text-lg font-bold text-purple-800">{formatCurrency(payoutSummary.franchise?.mg_amount, accountSummary?.country)}</p>
                        </div>
                        <div className="p-3 bg-green-50 rounded-lg text-center">
                          <p className="text-xs text-green-600">Total Payable</p>
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
                              <th className="text-right py-3 px-4 font-medium text-gray-600">Revenue Share</th>
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
                            {payoutSummary.monthly_data.map((month, idx) => (
                              <tr key={month.month} className={`border-t ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'} hover:bg-blue-50/50`}>
                                <td className="py-3 px-4 font-medium">
                                  {new Date(month.month + '-01').toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}
                                </td>
                                <td className="py-3 px-4 text-right">{formatCurrency(month.total_sales, accountSummary?.country)}</td>
                                <td className="py-3 px-4 text-right text-green-600">{formatCurrency(month.revenue_share, accountSummary?.country)}</td>
                                <td className="py-3 px-4 text-right text-purple-600">{formatCurrency(month.mg_amount, accountSummary?.country)}</td>
                                <td className="py-3 px-4 text-center">
                                  <Badge variant={month.payable_type === 'mg' ? 'default' : 'secondary'} className="text-xs">
                                    {month.payable_type === 'mg' ? 'MG' : 'RS'}
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
                            ))}
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
            <TabsContent value="invoices" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="w-5 h-5 text-purple-600" />
                    Invoice & Bill Export (CA/Auditor Ready)
                  </CardTitle>
                  <CardDescription>
                    Export expense invoices with attachment status, grouped invoice summary, and missing bill reports
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Filters */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
                    <div>
                      <Label className="text-xs">From Date</Label>
                      <Input
                        type="date"
                        value={invoiceExportState.startDate}
                        onChange={(e) => setInvoiceExportState(p => ({ ...p, startDate: e.target.value }))}
                      />
                    </div>
                    <div>
                      <Label className="text-xs">To Date</Label>
                      <Input
                        type="date"
                        value={invoiceExportState.endDate}
                        onChange={(e) => setInvoiceExportState(p => ({ ...p, endDate: e.target.value }))}
                      />
                    </div>
                    <div>
                      <Label className="text-xs">Attachment Status</Label>
                      <Select 
                        value={invoiceExportState.attachmentStatus} 
                        onValueChange={(v) => setInvoiceExportState(p => ({ ...p, attachmentStatus: v }))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All</SelectItem>
                          <SelectItem value="attached">With Attachment</SelectItem>
                          <SelectItem value="missing">Missing Attachment</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-xs">Grouped Status</Label>
                      <Select 
                        value={invoiceExportState.groupedStatus} 
                        onValueChange={(v) => setInvoiceExportState(p => ({ ...p, groupedStatus: v }))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All</SelectItem>
                          <SelectItem value="grouped">Grouped Only</SelectItem>
                          <SelectItem value="ungrouped">Ungrouped Only</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-wrap gap-3">
                    <Button
                      onClick={async () => {
                        if (!invoiceExportState.startDate || !invoiceExportState.endDate) {
                          toast.error('Please select date range');
                          return;
                        }
                        setAuditLoading(true);
                        try {
                          const res = await fetch(`${API}/api/expense-attachments/audit-report`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                              token,
                              center: selectedCenter,
                              start_date: invoiceExportState.startDate,
                              end_date: invoiceExportState.endDate,
                              attachment_status: invoiceExportState.attachmentStatus === 'all' ? null : invoiceExportState.attachmentStatus,
                              grouped_status: invoiceExportState.groupedStatus === 'all' ? null : invoiceExportState.groupedStatus
                            })
                          });
                          const data = await res.json();
                          if (data.success) {
                            setAuditReport(data);
                            toast.success(`Found ${data.summary.total_count} expenses`);
                          }
                        } catch (err) {
                          toast.error('Failed to generate report');
                        } finally {
                          setAuditLoading(false);
                        }
                      }}
                      disabled={auditLoading}
                      className="gap-2"
                    >
                      {auditLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                      Generate Audit Report
                    </Button>

                    <Button
                      variant="outline"
                      onClick={async () => {
                        if (!invoiceExportState.startDate || !invoiceExportState.endDate) {
                          toast.error('Please select date range');
                          return;
                        }
                        setAuditLoading(true);
                        try {
                          const res = await fetch(`${API}/api/expense-attachments/export-zip`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                              token,
                              center: selectedCenter,
                              start_date: invoiceExportState.startDate,
                              end_date: invoiceExportState.endDate
                            })
                          });
                          
                          const contentType = res.headers.get('content-type') || '';
                          if (contentType.includes('application/json')) {
                            // Batching response
                            const data = await res.json();
                            if (data.requires_batching) {
                              setExportBatches(data.batches);
                              toast.info(data.message);
                            } else if (data.detail) {
                              toast.error(data.detail);
                            }
                          } else {
                            // Direct ZIP download
                            const blob = await res.blob();
                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `${selectedCenter}_Invoices_${invoiceExportState.startDate}_to_${invoiceExportState.endDate}.zip`;
                            document.body.appendChild(a);
                            a.click();
                            a.remove();
                            window.URL.revokeObjectURL(url);
                            toast.success('ZIP downloaded');
                          }
                        } catch (err) {
                          toast.error('Failed to export ZIP');
                        } finally {
                          setAuditLoading(false);
                        }
                      }}
                      disabled={auditLoading}
                      className="gap-2"
                    >
                      <Download className="w-4 h-4" /> Download ZIP
                    </Button>
                  </div>

                  {/* Export Batches (when >3 months) */}
                  {exportBatches && (
                    <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                      <p className="text-sm text-amber-800 mb-3 font-medium">
                        Date range exceeds 3 months. Download in batches:
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {exportBatches.map((batch, idx) => (
                          <Button
                            key={idx}
                            size="sm"
                            variant="outline"
                            onClick={async () => {
                              const res = await fetch(`${API}/api/expense-attachments/export-zip-batch`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                  token,
                                  center: selectedCenter,
                                  start_date: batch.start_date,
                                  end_date: batch.end_date
                                })
                              });
                              const blob = await res.blob();
                              const url = window.URL.createObjectURL(blob);
                              const a = document.createElement('a');
                              a.href = url;
                              a.download = `${selectedCenter}_${batch.label.replace(/\s/g, '_')}.zip`;
                              a.click();
                            }}
                            className="gap-1"
                          >
                            <Download className="w-3 h-3" /> {batch.label}
                          </Button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Audit Report Summary */}
                  {auditReport && (
                    <div className="space-y-4">
                      {/* Summary Cards */}
                      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                        <div className="p-3 bg-blue-50 rounded-lg text-center">
                          <p className="text-2xl font-bold text-blue-700">{auditReport.summary.total_count}</p>
                          <p className="text-xs text-blue-600">Total Expenses</p>
                        </div>
                        <div className="p-3 bg-green-50 rounded-lg text-center">
                          <p className="text-2xl font-bold text-green-700">{auditReport.summary.attached_count}</p>
                          <p className="text-xs text-green-600">With Attachments</p>
                        </div>
                        <div className="p-3 bg-red-50 rounded-lg text-center">
                          <p className="text-2xl font-bold text-red-700">{auditReport.summary.missing_count}</p>
                          <p className="text-xs text-red-600">Missing Bills</p>
                        </div>
                        <div className="p-3 bg-purple-50 rounded-lg text-center">
                          <p className="text-2xl font-bold text-purple-700">{auditReport.summary.grouped_count}</p>
                          <p className="text-xs text-purple-600">Grouped</p>
                        </div>
                        <div className="p-3 bg-amber-50 rounded-lg text-center">
                          <p className="text-2xl font-bold text-amber-700">{auditReport.summary.mismatch_count}</p>
                          <p className="text-xs text-amber-600">Mismatched</p>
                        </div>
                      </div>

                      {/* Expense List with Audit Details */}
                      <div className="border rounded-lg overflow-hidden">
                        <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                          <table className="w-full text-sm">
                            <thead className="bg-gray-50 sticky top-0">
                              <tr>
                                <th className="text-left py-2 px-3 font-medium text-gray-600">Date</th>
                                <th className="text-left py-2 px-3 font-medium text-gray-600">Description</th>
                                <th className="text-left py-2 px-3 font-medium text-gray-600">Category</th>
                                <th className="text-right py-2 px-3 font-medium text-gray-600">Amount</th>
                                <th className="text-left py-2 px-3 font-medium text-gray-600">Vendor</th>
                                <th className="text-left py-2 px-3 font-medium text-gray-600">Invoice #</th>
                                <th className="text-center py-2 px-3 font-medium text-gray-600">Bill</th>
                                <th className="text-left py-2 px-3 font-medium text-gray-600">Uploaded By</th>
                              </tr>
                            </thead>
                            <tbody>
                              {auditReport.expenses.map((exp, idx) => (
                                <tr 
                                  key={idx} 
                                  className={`border-t ${
                                    exp.attachment_status === 'missing' ? 'bg-red-50' : 
                                    exp.amount_match === 'mismatch' ? 'bg-amber-50' : ''
                                  }`}
                                >
                                  <td className="py-2 px-3">{exp.date}</td>
                                  <td className="py-2 px-3">{exp.description}</td>
                                  <td className="py-2 px-3">
                                    <Badge variant="outline" className="text-xs">{exp.expense_type}</Badge>
                                  </td>
                                  <td className="py-2 px-3 text-right font-medium">
                                    {formatCurrency(exp.amount, accountSummary?.country)}
                                  </td>
                                  <td className="py-2 px-3 text-xs">
                                    {exp.group_info?.vendor_name || '-'}
                                  </td>
                                  <td className="py-2 px-3 text-xs">
                                    {exp.group_info?.invoice_number || '-'}
                                  </td>
                                  <td className="py-2 px-3 text-center">
                                    {exp.attachment_status === 'attached' ? (
                                      <Badge className="bg-green-100 text-green-800 text-xs">✓</Badge>
                                    ) : exp.attachment_status === 'attached_via_group' ? (
                                      <Badge className="bg-blue-100 text-blue-800 text-xs">Grp</Badge>
                                    ) : (
                                      <Badge className="bg-red-100 text-red-800 text-xs">✗</Badge>
                                    )}
                                  </td>
                                  <td className="py-2 px-3 text-xs text-gray-500">
                                    {exp.uploaded_by || exp.created_by || '-'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      {/* Total */}
                      <div className="text-right text-lg font-bold">
                        Total: {formatCurrency(auditReport.summary.total_amount, accountSummary?.country)}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
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
                  <span className="text-gray-500">Total Payable:</span>
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
      <Dialog open={!!pibPreview} onOpenChange={(open) => { if (!open) setPibPreview(null); }}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto" data-testid="pib-preview-dialog">
          <DialogHeader>
            <DialogTitle>PIB Report Preview — {selectedCenter} · {selectedMonth}</DialogTitle>
            <DialogDescription>Review the figures, then click Download to save the PDF.</DialogDescription>
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
                const pnlFig = finCur.net_revenue ?? finCur.profit ?? finCur.pnl;
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
                      <div className="rounded-lg border p-3 bg-green-50 dark:bg-green-900/20">
                        <p className="text-xs text-muted-foreground">Net Revenue</p>
                        <p className="text-lg font-bold">₹{Math.round(pnlFig || 0).toLocaleString('en-IN')}</p>
                      </div>
                      <div className="rounded-lg border p-3 bg-purple-50 dark:bg-purple-900/20">
                        <p className="text-xs text-muted-foreground">Revenue Share</p>
                        <p className="text-lg font-bold">₹{Math.round(revShare.share_amount || revShare.amount || finCur.revenue_share || 0).toLocaleString('en-IN')}</p>
                      </div>
                    </div>
                    <div className="rounded-lg border p-3 bg-muted/40">
                      <p className="font-semibold text-xs text-muted-foreground mb-2">SALES BREAKDOWN</p>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                        <div>Cash: ₹{Math.round(sales.total_cash_sale || sales.cash_sale || 0).toLocaleString('en-IN')}</div>
                        <div>Online/Card: ₹{Math.round(sales.total_online_sale || sales.card_sale || sales.online_sale || 0).toLocaleString('en-IN')}</div>
                        <div>Swiggy: ₹{Math.round(sales.swiggy || sales.swiggy_sale || 0).toLocaleString('en-IN')}</div>
                        <div>Zomato: ₹{Math.round(sales.zomato || sales.zomato_sale || 0).toLocaleString('en-IN')}</div>
                      </div>
                    </div>
                    <details className="rounded-lg border p-2 bg-muted/20">
                      <summary className="cursor-pointer text-xs font-semibold">Show full summary JSON</summary>
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
            <Button variant="outline" onClick={() => setPibPreview(null)} data-testid="pib-preview-cancel">Close</Button>
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
    </div>
  );
}
