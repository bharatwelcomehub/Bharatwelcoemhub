import React, { useState, useEffect, useCallback } from 'react';
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
  IndianRupee, AlertCircle, CheckCircle, FileSpreadsheet, Trash2, Pencil
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

  useEffect(() => {
    fetchCenters();
    fetchLinkageStatus();
  }, [fetchCenters, fetchLinkageStatus]);

  useEffect(() => {
    if (selectedCenter) {
      fetchAccountSummary();
      fetchCommissions();
      fetchPayoutSummary();
    }
  }, [selectedCenter, selectedMonth, fetchAccountSummary, fetchCommissions, fetchPayoutSummary]);

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
  const downloadReport = async (reportType) => {
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

              {/* WC Gating Alert Banner */}
              {accountSummary.financial_summary.wc_standing?.wc_status === "closed" && (
                <div className="p-4 bg-red-50 border-2 border-red-300 rounded-lg" data-testid="wc-closed-banner">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-red-800">Revenue Share & MG CLOSED</p>
                      <p className="text-sm text-red-700">Working Capital is below 50% of Security Deposit. All profits will be used to refill Working Capital first. Revenue Share and Minimum Guarantee are suspended until WC is restored.</p>
                    </div>
                  </div>
                </div>
              )}
              {accountSummary.financial_summary.wc_standing?.wc_status === "restoring" && (
                <div className="p-4 bg-amber-50 border border-amber-300 rounded-lg" data-testid="wc-restoring-banner">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-amber-800">Working Capital Being Restored</p>
                      <p className="text-sm text-amber-700">WC is below initial deposit. Profits are first restoring Working Capital. Revenue Share resumes once WC is fully restored to initial amount.</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Working Capital Utilisation Card */}
              {accountSummary.financial_summary.wc_standing && accountSummary.financial_summary.working_capital > 0 && (
                <Card data-testid="wc-utilisation-card">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg">Working Capital Utilisation</CardTitle>
                    <CardDescription>Standing as of {accountSummary.period} (from center opening)</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                      <div className="p-3 bg-gray-50 rounded-lg text-center">
                        <p className="text-xs text-gray-500">Initial WC</p>
                        <p className="text-sm font-semibold">{formatCurrency(accountSummary.financial_summary.wc_standing.initial_security_deposit, accountSummary.country)}</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg text-center">
                        <p className="text-xs text-gray-500">Cumulative P&L</p>
                        <p className={`text-sm font-semibold ${accountSummary.financial_summary.wc_standing.cumulative_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(accountSummary.financial_summary.wc_standing.cumulative_pnl, accountSummary.country)}
                        </p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg text-center">
                        <p className="text-xs text-gray-500">WC Utilised</p>
                        <p className="text-sm font-semibold text-orange-600">{formatCurrency(accountSummary.financial_summary.wc_standing.wc_utilised, accountSummary.country)}</p>
                      </div>
                      <div className={`p-3 rounded-lg text-center ${accountSummary.financial_summary.working_capital_available >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                        <p className="text-xs text-gray-500">Available Capital</p>
                        <p className={`text-sm font-bold ${accountSummary.financial_summary.working_capital_available >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                          {formatCurrency(accountSummary.financial_summary.working_capital_available, accountSummary.country)}
                        </p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg text-center">
                        <p className="text-xs text-gray-500">WC Status</p>
                        <p className={`text-sm font-bold ${
                          accountSummary.financial_summary.wc_standing.wc_status === 'healthy' ? 'text-green-600' :
                          accountSummary.financial_summary.wc_standing.wc_status === 'restoring' ? 'text-amber-600' : 'text-red-600'
                        }`}>
                          {accountSummary.financial_summary.wc_standing.wc_percentage?.toFixed(0)}%
                          {accountSummary.financial_summary.wc_standing.wc_status === 'closed' && ' (CLOSED)'}
                        </p>
                      </div>
                    </div>
                    {/* Progress bar */}
                    <div className="mt-3">
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div
                          className={`h-2.5 rounded-full ${
                            accountSummary.financial_summary.wc_standing.wc_percentage >= 100 ? 'bg-green-500' :
                            accountSummary.financial_summary.wc_standing.wc_percentage >= 50 ? 'bg-amber-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${Math.min(100, Math.max(0, accountSummary.financial_summary.wc_standing.wc_percentage))}%` }}
                        />
                      </div>
                      <div className="flex justify-between text-xs text-gray-400 mt-1">
                        <span>0%</span>
                        <span className="text-red-400">50% (Threshold)</span>
                        <span>100% (Initial)</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Financial Summary */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Financial Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-3 gap-6">
                    <div className="space-y-2">
                      <h4 className="font-medium text-gray-600">Revenue</h4>
                      <div className="flex justify-between text-sm">
                        <span>Total Sales</span>
                        <span className="font-medium">{formatCurrency(accountSummary.financial_summary.total_sales, accountSummary.country)}</span>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <h4 className="font-medium text-gray-600">Deductions</h4>
                      <div className="flex justify-between text-sm">
                        <span>Expenses</span>
                        <span className="text-red-600">-{formatCurrency(accountSummary.financial_summary.total_expenses, accountSummary.country)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Commissions</span>
                        <span className="text-red-600">-{formatCurrency(accountSummary.financial_summary.total_commissions, accountSummary.country)}</span>
                      </div>
                      {accountSummary.financial_summary.sales_gst > 0 && (
                        <div className="flex justify-between text-sm">
                          <span>GST on Sales ({accountSummary.financial_summary.sales_gst_rate || '5%'})</span>
                          <span className="text-red-600">-{formatCurrency(accountSummary.financial_summary.sales_gst, accountSummary.country)}</span>
                        </div>
                      )}
                    </div>
                    <div className="space-y-2">
                      <h4 className="font-medium text-gray-600">Working Capital</h4>
                      <div className="flex justify-between text-sm">
                        <span>Security Deposit</span>
                        <span className="font-medium">{formatCurrency(accountSummary.financial_summary.working_capital, accountSummary.country)}</span>
                      </div>
                      {/* Cumulative P&L Impact */}
                      {accountSummary.financial_summary.wc_standing && accountSummary.financial_summary.wc_standing.cumulative_pnl !== 0 && (
                        <div className="flex justify-between text-sm">
                          <span>{accountSummary.financial_summary.wc_standing.cumulative_pnl >= 0 ? "Cumulative P&L Surplus" : "Cumulative P&L Deficit"}</span>
                          <span className={accountSummary.financial_summary.wc_standing.cumulative_pnl >= 0 ? "text-green-600" : "text-red-600"}>
                            {accountSummary.financial_summary.wc_standing.cumulative_pnl >= 0 ? "+" : ""}{formatCurrency(accountSummary.financial_summary.wc_standing.cumulative_pnl, accountSummary.country)}
                          </span>
                        </div>
                      )}
                      {accountSummary.financial_summary.loans_outstanding > 0 && (
                        <div className="flex justify-between text-sm">
                          <span>Loans Outstanding</span>
                          <span className="text-red-600">-{formatCurrency(accountSummary.financial_summary.loans_outstanding, accountSummary.country)}</span>
                        </div>
                      )}
                      <div className="flex justify-between text-sm font-semibold pt-1 border-t border-gray-200">
                        <span>Available Working Capital</span>
                        <span className={accountSummary.financial_summary.working_capital_available >= 0 ? "text-green-600" : "text-red-600"} data-testid="available-wc">
                          {formatCurrency(accountSummary.financial_summary.working_capital_available, accountSummary.country)}
                        </span>
                      </div>
                      {/* Current Month P&L */}
                      {accountSummary.financial_summary.wc_standing && (
                        <div className="text-xs text-gray-500 pt-1">
                          This month: Sales {formatCurrency(accountSummary.financial_summary.wc_standing.current_month_sales, accountSummary.country)} - Expenses {formatCurrency(accountSummary.financial_summary.wc_standing.current_month_expenses, accountSummary.country)} = <span className={accountSummary.financial_summary.wc_standing.current_month_pnl >= 0 ? "text-green-600" : "text-red-600"}>{formatCurrency(accountSummary.financial_summary.wc_standing.current_month_pnl, accountSummary.country)}</span>
                        </div>
                      )}
                      {/* MG (Minimum Guarantee) */}
                      {accountSummary.mg_calculation && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <div className="flex justify-between text-sm font-medium">
                            <span>Minimum Guarantee (MG)</span>
                            <span className="text-purple-600">{formatCurrency(accountSummary.mg_calculation.monthly_mg, accountSummary.country)}</span>
                          </div>
                          <p className="text-xs text-gray-400 italic">EMI on Net Investment @ 15% for 7 years</p>
                        </div>
                      )}
                      <p className="text-xs text-gray-400 italic">Standing as of {accountSummary.period}</p>
                    </div>
                  </div>
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
                        <h4 className="font-medium text-amber-800 mb-2">Working Capital Standing (as of {accountSummary.period})</h4>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <span className="text-gray-600">Security Deposit:</span>
                          <span className="text-right font-medium">{formatCurrency(accountSummary.financial_summary.wc_standing.initial_security_deposit, accountSummary.country)}</span>
                          <span className="text-gray-600">Cumulative P&L:</span>
                          <span className={`text-right font-medium ${accountSummary.financial_summary.wc_standing.cumulative_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatCurrency(accountSummary.financial_summary.wc_standing.cumulative_pnl, accountSummary.country)}
                          </span>
                          {accountSummary.financial_summary.loans_outstanding > 0 && (
                            <>
                              <span className="text-gray-600">Loans Outstanding:</span>
                              <span className="text-right font-medium text-red-600">-{formatCurrency(accountSummary.financial_summary.loans_outstanding, accountSummary.country)}</span>
                            </>
                          )}
                          <span className="text-gray-700 font-semibold border-t pt-1">Available Capital:</span>
                          <span className={`text-right font-bold border-t pt-1 ${accountSummary.financial_summary.working_capital_available >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                            {formatCurrency(accountSummary.financial_summary.working_capital_available, accountSummary.country)}
                          </span>
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
              {/* WC Gating Banner for MG & Payout */}
              {accountSummary.payout?.wc_gated && (
                <div className="p-4 bg-red-50 border-2 border-red-300 rounded-lg" data-testid="payout-wc-closed-banner">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-red-800">MG & Revenue Share CLOSED</p>
                      <p className="text-sm text-red-700">
                        Working Capital is at {accountSummary.financial_summary.wc_standing?.wc_percentage?.toFixed(0)}% of initial deposit.
                        Both Minimum Guarantee and Revenue Share are suspended. Available WC: {formatCurrency(accountSummary.financial_summary.working_capital_available, accountSummary.country)}
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

              {/* Payout Determination Card */}
              {accountSummary.payout && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Wallet className="w-5 h-5" />
                      Payout to Franchise Owner - {accountSummary.period}
                    </CardTitle>
                    <CardDescription>
                      Comparison: MG vs Franchise Owner's Revenue Share - Higher amount is payable to Franchise Owner
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid md:grid-cols-3 gap-4">
                      <Card className={`border-2 ${accountSummary.payout.type === 'minimum_guarantee' ? 'border-purple-400 bg-purple-50' : 'border-gray-200'} ${accountSummary.payout.wc_gated ? 'opacity-50' : ''}`}>
                        <CardContent className="p-4 text-center">
                          <p className="text-sm text-gray-500">Minimum Guarantee</p>
                          <p className="text-2xl font-bold text-purple-600">
                            {formatCurrency(accountSummary.payout.mg_amount, accountSummary.country)}
                          </p>
                          {accountSummary.payout.type === 'minimum_guarantee' && (
                            <Badge className="mt-2 bg-purple-600">Payable</Badge>
                          )}
                          {accountSummary.payout.wc_gated && (
                            <Badge className="mt-2 bg-red-600 text-white">CLOSED</Badge>
                          )}
                        </CardContent>
                      </Card>
                      <div className="flex items-center justify-center">
                        <span className="text-2xl font-bold text-gray-400">vs</span>
                      </div>
                      <Card className={`border-2 ${accountSummary.payout.type === 'revenue_share' ? 'border-green-400 bg-green-50' : 'border-gray-200'} ${accountSummary.payout.wc_gated ? 'opacity-50' : ''}`}>
                        <CardContent className="p-4 text-center">
                          <p className="text-sm text-gray-500">Franchise Owner's Revenue Share ({accountSummary.share_calculation?.franchise_owner?.percentage || 15}%)</p>
                          <p className="text-2xl font-bold text-green-600">
                            {formatCurrency(accountSummary.payout.revenue_share_amount, accountSummary.country)}
                          </p>
                          {accountSummary.payout.type === 'revenue_share' && (
                            <Badge className="mt-2 bg-green-600">Payable</Badge>
                          )}
                          {accountSummary.payout.wc_gated && (
                            <Badge className="mt-2 bg-red-600 text-white">CLOSED</Badge>
                          )}
                        </CardContent>
                      </Card>
                    </div>
                    <div className={`mt-4 p-4 rounded-lg ${accountSummary.payout.wc_gated ? 'bg-red-50' : 'bg-blue-50'}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className={`text-sm ${accountSummary.payout.wc_gated ? 'text-red-600' : 'text-blue-600'}`}>Amount Payable to Franchise Owner This Month</p>
                          <p className={`text-3xl font-bold ${accountSummary.payout.wc_gated ? 'text-red-800' : 'text-blue-800'}`}>
                            {formatCurrency(accountSummary.payout.amount, accountSummary.country)}
                          </p>
                        </div>
                        <Badge className="text-lg px-4 py-2" variant={accountSummary.payout.wc_gated ? 'destructive' : accountSummary.payout.type === 'minimum_guarantee' ? 'default' : 'secondary'}>
                          {accountSummary.payout.wc_gated ? 'WC CLOSED' : accountSummary.payout.type === 'minimum_guarantee' ? 'MG' : 'Revenue Share'}
                        </Badge>
                      </div>
                      <p className={`text-xs mt-2 ${accountSummary.payout.wc_gated ? 'text-red-500' : 'text-blue-500'}`}>{accountSummary.payout.reason}</p>
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
                    <CardTitle className="text-lg">Working Capital Standing (as of {accountSummary.period})</CardTitle>
                    <CardDescription>Dynamic working capital based on cumulative P&L from opening</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="p-3 bg-gray-50 rounded-lg text-center">
                        <p className="text-xs text-gray-500">Security Deposit</p>
                        <p className="text-lg font-semibold">{formatCurrency(accountSummary.financial_summary.wc_standing.initial_security_deposit, accountSummary.country)}</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg text-center">
                        <p className="text-xs text-gray-500">Cumulative P&L</p>
                        <p className={`text-lg font-semibold ${accountSummary.financial_summary.wc_standing.cumulative_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(accountSummary.financial_summary.wc_standing.cumulative_pnl, accountSummary.country)}
                        </p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg text-center">
                        <p className="text-xs text-gray-500">Loans Outstanding</p>
                        <p className="text-lg font-semibold text-red-600">{formatCurrency(accountSummary.financial_summary.loans_outstanding, accountSummary.country)}</p>
                      </div>
                      <div className={`p-3 rounded-lg text-center ${accountSummary.financial_summary.working_capital_available >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                        <p className="text-xs text-gray-500">Available Capital</p>
                        <p className={`text-lg font-bold ${accountSummary.financial_summary.working_capital_available >= 0 ? 'text-green-700' : 'text-red-700'}`} data-testid="payout-available-wc">
                          {formatCurrency(accountSummary.financial_summary.working_capital_available, accountSummary.country)}
                        </p>
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
    </div>
  );
}
