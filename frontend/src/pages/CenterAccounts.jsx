import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { 
  Building2, DollarSign, TrendingUp, TrendingDown, FileText, Upload, 
  Download, Calculator, Receipt, Wallet, CreditCard, ShoppingBag,
  Link, Unlink, RefreshCw, Loader2, ChevronRight, PieChart,
  IndianRupee, AlertCircle, CheckCircle, FileSpreadsheet
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const PLATFORMS = {
  india: [
    { value: 'swiggy', label: 'Swiggy', color: 'bg-orange-100 text-orange-800' },
    { value: 'zomato', label: 'Zomato', color: 'bg-red-100 text-red-800' },
    { value: 'card_settlement', label: 'Card Settlement', color: 'bg-blue-100 text-blue-800' }
  ],
  australia: [
    { value: 'doordash', label: 'DoorDash', color: 'bg-red-100 text-red-800' },
    { value: 'card_settlement', label: 'Card Settlement', color: 'bg-blue-100 text-blue-800' }
  ]
};

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
  
  // Modal states
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showCommissionModal, setShowCommissionModal] = useState(false);
  const [showLinkModal, setShowLinkModal] = useState(false);
  
  // Form states
  const [uploadForm, setUploadForm] = useState({
    platform: '',
    file: null
  });
  
  const [commissionForm, setCommissionForm] = useState({
    platform: '',
    settlement_period_start: '',
    settlement_period_end: '',
    gross_order_amount: 0,
    commission_charged: 0,
    net_payout_received: 0,
    notes: ''
  });
  
  const [linkForm, setLinkForm] = useState({
    center_code: '',
    franchise_code: ''
  });

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
        setCenters(uniqueCenters.filter(c => c.code !== 'PB-MGT'));
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

  useEffect(() => {
    fetchCenters();
    fetchLinkageStatus();
  }, [fetchCenters, fetchLinkageStatus]);

  useEffect(() => {
    if (selectedCenter) {
      fetchAccountSummary();
      fetchCommissions();
    }
  }, [selectedCenter, selectedMonth, fetchAccountSummary, fetchCommissions]);

  // Save commission statement
  const handleSaveCommission = async () => {
    if (!commissionForm.platform || !commissionForm.settlement_period_start || !commissionForm.settlement_period_end) {
      toast.error('Please fill all required fields');
      return;
    }
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/center-accounts/save-commission`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          token, 
          center: selectedCenter,
          ...commissionForm 
        })
      });
      const data = await res.json();
      if (data.success) {
        toast.success('Commission statement saved');
        setShowCommissionModal(false);
        setCommissionForm({
          platform: '',
          settlement_period_start: '',
          settlement_period_end: '',
          gross_order_amount: 0,
          commission_charged: 0,
          net_payout_received: 0,
          notes: ''
        });
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
    return center.country === 'Australia' || selectedCenter === 'PB-PERTH' ? 'Australia' : 'India';
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
              <Button variant="outline" onClick={() => setShowCommissionModal(true)} disabled={!selectedCenter}>
                <Upload className="w-4 h-4 mr-2" />
                Add Commission
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
                    <p className="text-sm text-orange-600">Commissions</p>
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
            <TabsList>
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="sales">Sales Breakdown</TabsTrigger>
              <TabsTrigger value="commissions">Commissions</TabsTrigger>
              <TabsTrigger value="share">Revenue/Profit Share</TabsTrigger>
              <TabsTrigger value="reports">Reports</TabsTrigger>
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
                    </div>
                    <div className="space-y-2">
                      <h4 className="font-medium text-gray-600">Working Capital</h4>
                      <div className="flex justify-between text-sm">
                        <span>Initial</span>
                        <span>{formatCurrency(accountSummary.financial_summary.working_capital_initial, accountSummary.country)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Remaining</span>
                        <span className="font-medium text-green-600">{formatCurrency(accountSummary.financial_summary.working_capital_remaining, accountSummary.country)}</span>
                      </div>
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

            {/* Commissions Tab */}
            <TabsContent value="commissions" className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-medium">Commission Statements</h3>
                <Button onClick={() => setShowCommissionModal(true)}>
                  <Upload className="w-4 h-4 mr-2" />
                  Add Commission Statement
                </Button>
              </div>

              <Card>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50 border-b">
                        <tr>
                          <th className="text-left p-3 text-sm font-medium">Platform</th>
                          <th className="text-left p-3 text-sm font-medium">Period</th>
                          <th className="text-right p-3 text-sm font-medium">Gross Amount</th>
                          <th className="text-right p-3 text-sm font-medium">Commission</th>
                          <th className="text-right p-3 text-sm font-medium">Net Payout</th>
                          <th className="text-right p-3 text-sm font-medium">Commission %</th>
                        </tr>
                      </thead>
                      <tbody>
                        {commissionStatements.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="text-center py-8 text-gray-500">
                              No commission statements found for this period
                            </td>
                          </tr>
                        ) : (
                          commissionStatements.map((stmt, idx) => (
                            <tr key={idx} className="border-b hover:bg-gray-50">
                              <td className="p-3">
                                <Badge className={availablePlatforms.find(p => p.value === stmt.platform)?.color || 'bg-gray-100'}>
                                  {stmt.platform.replace('_', ' ').toUpperCase()}
                                </Badge>
                              </td>
                              <td className="p-3 text-sm">
                                {stmt.settlement_period_start} to {stmt.settlement_period_end}
                              </td>
                              <td className="p-3 text-right">
                                {formatCurrency(stmt.gross_order_amount, accountSummary.country)}
                              </td>
                              <td className="p-3 text-right text-red-600">
                                {formatCurrency(stmt.commission_charged, accountSummary.country)}
                              </td>
                              <td className="p-3 text-right text-green-600">
                                {formatCurrency(stmt.net_payout_received, accountSummary.country)}
                              </td>
                              <td className="p-3 text-right">
                                {stmt.gross_order_amount > 0 ? formatPercent(stmt.commission_charged / stmt.gross_order_amount * 100) : '0%'}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {/* Commission Summary */}
              <div className="grid md:grid-cols-3 gap-4">
                <Card className="bg-orange-50">
                  <CardContent className="p-4">
                    <p className="text-sm text-orange-600">Aggregator Commission</p>
                    <p className="text-xl font-bold text-orange-800">
                      {formatCurrency(accountSummary.commissions.aggregator_total, accountSummary.country)}
                    </p>
                  </CardContent>
                </Card>
                <Card className="bg-blue-50">
                  <CardContent className="p-4">
                    <p className="text-sm text-blue-600">Card Commission</p>
                    <p className="text-xl font-bold text-blue-800">
                      {formatCurrency(accountSummary.commissions.card_total, accountSummary.country)}
                    </p>
                  </CardContent>
                </Card>
                <Card className="bg-red-50">
                  <CardContent className="p-4">
                    <p className="text-sm text-red-600">Total Commission</p>
                    <p className="text-xl font-bold text-red-800">
                      {formatCurrency(accountSummary.commissions.total, accountSummary.country)}
                    </p>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Revenue/Profit Share Tab */}
            <TabsContent value="share" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">
                    {accountSummary.share_calculation.type === 'profit_share' ? 'Profit Share' : 'Revenue Share'} Calculation
                  </CardTitle>
                  <CardDescription>
                    {accountSummary.country === 'Australia' 
                      ? 'Australia: Profit share model (% of net profit)'
                      : 'India: Revenue share model (% of total sales)'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <div className="space-y-3">
                        <div className="flex justify-between items-center">
                          <span className="text-gray-600">Share Type</span>
                          <Badge>{accountSummary.share_calculation.type.replace('_', ' ').toUpperCase()}</Badge>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-gray-600">Percentage</span>
                          <span className="font-medium">{accountSummary.share_calculation.percentage}%</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-gray-600">Base Amount</span>
                          <span className="font-medium">
                            {formatCurrency(accountSummary.share_calculation.base_amount, accountSummary.country)}
                          </span>
                        </div>
                        
                        <hr className="my-2" />
                        
                        {accountSummary.country === 'India' ? (
                          <>
                            <div className="flex justify-between items-center text-sm">
                              <span className="text-gray-500">CGST (9%)</span>
                              <span>{formatCurrency(accountSummary.share_calculation.cgst, accountSummary.country)}</span>
                            </div>
                            <div className="flex justify-between items-center text-sm">
                              <span className="text-gray-500">SGST (9%)</span>
                              <span>{formatCurrency(accountSummary.share_calculation.sgst, accountSummary.country)}</span>
                            </div>
                          </>
                        ) : (
                          <div className="flex justify-between items-center text-sm">
                            <span className="text-gray-500">GST (10%)</span>
                            <span>{formatCurrency(accountSummary.share_calculation.gst_amount, accountSummary.country)}</span>
                          </div>
                        )}
                        
                        <hr className="my-2" />
                        
                        <div className="flex justify-between items-center text-lg font-bold">
                          <span>Total Payable</span>
                          <span className="text-green-600">
                            {formatCurrency(accountSummary.share_calculation.total_payable, accountSummary.country)}
                          </span>
                        </div>
                      </div>
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

      {/* Add Commission Modal */}
      <Dialog open={showCommissionModal} onOpenChange={setShowCommissionModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Add Commission Statement</DialogTitle>
            <DialogDescription>Enter commission details for {selectedCenter}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Platform *</Label>
              <Select value={commissionForm.platform} onValueChange={(v) => setCommissionForm(p => ({ ...p, platform: v }))}>
                <SelectTrigger>
                  <SelectValue placeholder="Select platform" />
                </SelectTrigger>
                <SelectContent>
                  {availablePlatforms.map(p => (
                    <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Period Start *</Label>
                <Input 
                  type="date" 
                  value={commissionForm.settlement_period_start}
                  onChange={(e) => setCommissionForm(p => ({ ...p, settlement_period_start: e.target.value }))}
                />
              </div>
              <div>
                <Label>Period End *</Label>
                <Input 
                  type="date" 
                  value={commissionForm.settlement_period_end}
                  onChange={(e) => setCommissionForm(p => ({ ...p, settlement_period_end: e.target.value }))}
                />
              </div>
            </div>
            <div>
              <Label>Gross Order Amount</Label>
              <Input 
                type="number" 
                value={commissionForm.gross_order_amount}
                onChange={(e) => setCommissionForm(p => ({ ...p, gross_order_amount: parseFloat(e.target.value) || 0 }))}
              />
            </div>
            <div>
              <Label>Commission Charged</Label>
              <Input 
                type="number" 
                value={commissionForm.commission_charged}
                onChange={(e) => setCommissionForm(p => ({ ...p, commission_charged: parseFloat(e.target.value) || 0 }))}
              />
            </div>
            <div>
              <Label>Net Payout Received</Label>
              <Input 
                type="number" 
                value={commissionForm.net_payout_received}
                onChange={(e) => setCommissionForm(p => ({ ...p, net_payout_received: parseFloat(e.target.value) || 0 }))}
              />
            </div>
            <div>
              <Label>Notes</Label>
              <Textarea 
                placeholder="Optional notes..."
                value={commissionForm.notes}
                onChange={(e) => setCommissionForm(p => ({ ...p, notes: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCommissionModal(false)}>Cancel</Button>
            <Button onClick={handleSaveCommission} disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Save Commission
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
    </div>
  );
}
