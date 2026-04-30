import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { 
  Wallet, Plus, ArrowDownCircle, ArrowUpCircle, Clock, CheckCircle, 
  Building2, DollarSign, RefreshCw, Loader2, AlertCircle, History,
  TrendingDown, Percent, FileText, Download, Trash2
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const formatCurrency = (value, country = 'India') => {
  const symbol = country === 'Australia' ? 'AUD ' : 'Rs. ';
  return `${symbol}${(value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const STATUS_COLORS = {
  active: 'bg-yellow-100 text-yellow-800',
  partially_repaid: 'bg-blue-100 text-blue-800',
  fully_repaid: 'bg-green-100 text-green-800'
};

export default function LoanEntries() {
  const { session } = useAuth();
  const token = session?.token;
  
  const [loading, setLoading] = useState(false);
  const [centers, setCenters] = useState([]);
  const [selectedCenter, setSelectedCenter] = useState('');
  const [loans, setLoans] = useState([]);
  const [loanSummary, setLoanSummary] = useState(null);
  const [selectedLoan, setSelectedLoan] = useState(null);
  
  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showRepaymentModal, setShowRepaymentModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  
  // Form states
  const [createForm, setCreateForm] = useState({
    amount: '',
    loan_date: new Date().toISOString().split('T')[0],
    reason: '',
    notes: '',
    source_center: ''
  });
  
  const [repaymentForm, setRepaymentForm] = useState({
    amount: '',
    repayment_date: new Date().toISOString().split('T')[0],
    notes: ''
  });

  // Delete states
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [loanToDelete, setLoanToDelete] = useState(null);
  const [deleteForce, setDeleteForce] = useState(false);

  // Bulk delete states
  const [showBulkDeleteModal, setShowBulkDeleteModal] = useState(false);
  const [bulkCenter, setBulkCenter] = useState('all');
  const [bulkMonth, setBulkMonth] = useState('');
  const [bulkForce, setBulkForce] = useState(false);

  // Source filter (for grouping loans by who funded/received them)
  const [sourceFilter, setSourceFilter] = useState('all'); // 'all' | '<source_key>'

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

  // Fetch loans
  const fetchLoans = useCallback(async () => {
    if (!token || !selectedCenter) return;
    
    setLoading(true);
    setSourceFilter('all');
    try {
      const res = await fetch(`${API}/api/loan-entries/list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, center: selectedCenter })
      });
      const data = await res.json();
      if (data.success) {
        setLoans(data.loans || []);
      }
    } catch (error) {
      toast.error('Failed to fetch loans');
    } finally {
      setLoading(false);
    }
  }, [token, selectedCenter]);

  // Fetch loan summary
  const fetchLoanSummary = useCallback(async () => {
    if (!token || !selectedCenter) return;
    
    try {
      const res = await fetch(`${API}/api/loan-entries/summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, center: selectedCenter })
      });
      const data = await res.json();
      if (data.success) {
        setLoanSummary(data);
      }
    } catch (error) {
      console.error('Failed to fetch loan summary');
    }
  }, [token, selectedCenter]);

  useEffect(() => {
    fetchCenters();
  }, [fetchCenters]);

  useEffect(() => {
    if (selectedCenter) {
      fetchLoans();
      fetchLoanSummary();
    }
  }, [selectedCenter, fetchLoans, fetchLoanSummary]);

  // Create loan entry
  const handleCreateLoan = async () => {
    if (!createForm.amount || !createForm.loan_date || !createForm.reason) {
      toast.error('Please fill all required fields');
      return;
    }
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/loan-entries/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token,
          center: selectedCenter,
          amount: parseFloat(createForm.amount),
          loan_date: createForm.loan_date,
          reason: createForm.reason,
          notes: createForm.notes,
          source_center: createForm.source_center
        })
      });
      const data = await res.json();
      if (data.success) {
        toast.success(data.message || 'Loan entry created successfully');
        setShowCreateModal(false);
        setCreateForm({ amount: '', loan_date: new Date().toISOString().split('T')[0], reason: '', notes: '', source_center: '' });
        fetchLoans();
        fetchLoanSummary();
      } else {
        toast.error(data.detail || 'Failed to create loan entry');
      }
    } catch (error) {
      toast.error('Failed to create loan entry');
    } finally {
      setLoading(false);
    }
  };

  // Download PDF Report
  const downloadPdfReport = async () => {
    if (!selectedCenter) { toast.error("Select a center"); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/loan-entries/report/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, center: selectedCenter })
      });
      if (!res.ok) { const err = await res.json(); toast.error(err.detail || "Download failed"); return; }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Loan_Report_${selectedCenter}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("PDF downloaded");
    } catch { toast.error("Download failed"); }
    finally { setLoading(false); }
  };


  // Add repayment
  const handleAddRepayment = async () => {
    if (!selectedLoan || !repaymentForm.amount || !repaymentForm.repayment_date) {
      toast.error('Please fill all required fields');
      return;
    }
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/loan-entries/add-repayment/${selectedLoan.loan_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token,
          amount: parseFloat(repaymentForm.amount),
          repayment_date: repaymentForm.repayment_date,
          notes: repaymentForm.notes
        })
      });
      const data = await res.json();
      if (data.success) {
        toast.success(`Repayment of ${repaymentForm.amount} recorded`);
        setShowRepaymentModal(false);
        setRepaymentForm({ amount: '', repayment_date: new Date().toISOString().split('T')[0], notes: '' });
        fetchLoans();
        fetchLoanSummary();
        // Refresh selected loan details
        if (showDetailModal) {
          fetchLoanDetails(selectedLoan.loan_id);
        }
      } else {
        toast.error(data.detail || 'Failed to add repayment');
      }
    } catch (error) {
      toast.error('Failed to add repayment');
    } finally {
      setLoading(false);
    }
  };

  // Fetch loan details
  const fetchLoanDetails = async (loanId) => {
    try {
      const res = await fetch(`${API}/api/loan-entries/get/${loanId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      });
      const data = await res.json();
      if (data.success) {
        setSelectedLoan(data.loan);
      }
    } catch (error) {
      toast.error('Failed to fetch loan details');
    }
  };

  // Delete single loan
  const handleDeleteLoan = async () => {
    if (!loanToDelete) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/loan-entries/delete/${loanToDelete.loan_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, force: deleteForce })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        toast.success(data.message || 'Loan entry deleted');
        setShowDeleteModal(false);
        setLoanToDelete(null);
        setDeleteForce(false);
        fetchLoans();
        fetchLoanSummary();
      } else {
        toast.error(data.detail || 'Failed to delete loan');
      }
    } catch (e) {
      toast.error('Failed to delete loan');
    } finally {
      setLoading(false);
    }
  };

  // Bulk delete
  const handleBulkDelete = async () => {
    if (!bulkCenter) {
      toast.error("Please select a center scope");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/loan-entries/bulk-delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token,
          center: bulkCenter,
          month: bulkMonth,
          force: bulkForce,
          confirm: true
        })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        toast.success(data.message);
        setShowBulkDeleteModal(false);
        setBulkMonth('');
        setBulkForce(false);
        fetchLoans();
        fetchLoanSummary();
      } else {
        toast.error(data.detail || 'Bulk delete failed');
      }
    } catch (e) {
      toast.error('Bulk delete failed');
    } finally {
      setLoading(false);
    }
  };

  const getCountry = () => {
    if (!selectedCenter) return 'India';
    const center = centers.find(c => c.code === selectedCenter);
    return center?.country === 'Australia' || center?.is_india_center === false ? 'Australia' : 'India';
  };

  const country = getCountry();

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="loan-entries-page">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Loan Entries</h1>
        <p className="text-gray-600">Track working capital usage as loans</p>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
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
            <Button onClick={() => { fetchLoans(); fetchLoanSummary(); }} disabled={!selectedCenter || loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <RefreshCw className="w-4 h-4 mr-2" />}
              Refresh
            </Button>
            {(session?.is_super_admin || session?.is_admin) && (
              <Button onClick={() => setShowCreateModal(true)} disabled={!selectedCenter}>
                <Plus className="w-4 h-4 mr-2" />
                New Loan Entry
              </Button>
            )}
            <Button variant="outline" onClick={downloadPdfReport} disabled={!selectedCenter || loading} data-testid="loan-pdf-btn">
              <Download className="w-4 h-4 mr-2" />
              PDF Report
            </Button>
            {session?.is_super_admin && (
              <Button
                variant="outline"
                onClick={() => { setBulkCenter(selectedCenter || 'all'); setBulkMonth(''); setBulkForce(false); setShowBulkDeleteModal(true); }}
                disabled={loading}
                data-testid="loan-bulk-delete-btn"
                className="text-red-600 border-red-300 hover:bg-red-50"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Bulk Delete
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      {loanSummary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <Card className="bg-gradient-to-br from-blue-50 to-blue-100">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-blue-600">Working Capital</p>
                  <p className="text-xl font-bold text-blue-800">
                    {formatCurrency(loanSummary.working_capital?.total, country)}
                  </p>
                  <p className="text-xs text-blue-500">Security Deposit</p>
                </div>
                <Wallet className="w-8 h-8 text-blue-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-red-50 to-red-100">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-red-600">Loans Outstanding</p>
                  <p className="text-xl font-bold text-red-800">
                    {formatCurrency(loanSummary.loans?.total_outstanding, country)}
                  </p>
                  <p className="text-xs text-red-500">{loanSummary.loans?.active_count || 0} active loans</p>
                </div>
                <TrendingDown className="w-8 h-8 text-red-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-50 to-green-100">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-green-600">Available Capital</p>
                  <p className="text-xl font-bold text-green-800">
                    {formatCurrency(loanSummary.working_capital?.available, country)}
                  </p>
                  <p className="text-xs text-green-500">For new loans</p>
                </div>
                <DollarSign className="w-8 h-8 text-green-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-50 to-purple-100">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-purple-600">Utilization</p>
                  <p className="text-xl font-bold text-purple-800">
                    {(loanSummary.working_capital?.utilization_percentage || 0).toFixed(1)}%
                  </p>
                  <p className="text-xs text-purple-500">Of working capital</p>
                </div>
                <Percent className="w-8 h-8 text-purple-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-teal-50 to-teal-100">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-teal-600">Loans Given</p>
                  <p className="text-xl font-bold text-teal-800">
                    {formatCurrency(loanSummary.summary?.total_given || 0, country)}
                  </p>
                  <p className="text-xs text-teal-500">Outstanding: {formatCurrency(loanSummary.summary?.total_given_outstanding || 0, country)}</p>
                </div>
                <ArrowUpCircle className="w-8 h-8 text-teal-400" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Loans List */}
      {selectedCenter ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Loan History</CardTitle>
            <CardDescription>All loan entries for {selectedCenter}</CardDescription>
          </CardHeader>
          <CardContent>
            {/* Source / Counterparty Filter */}
            {loans.length > 0 && (() => {
              // Group loans by counterparty. For 'taken' → source_center (or 'HQ / External' when empty)
              // For 'given' → target_center (or 'Other' when empty)
              const groups = {};
              loans.forEach(l => {
                const isGiven = l.loan_type === 'given';
                const key = isGiven
                  ? (l.target_center || 'OTHER')
                  : (l.source_center || 'HQ');
                const label = isGiven
                  ? `→ ${l.target_center_name || l.target_center || 'Other'}`
                  : `← ${l.source_center_name || (l.source_center ? l.source_center : 'HQ / External')}`;
                const g = groups[key] || { key, label, isGiven, count: 0, principal: 0, repaid: 0, outstanding: 0 };
                g.count += 1;
                g.principal += (l.amount || 0);
                g.repaid += (l.total_repaid || 0);
                g.outstanding += Math.max(0, (l.amount || 0) - (l.total_repaid || 0));
                groups[key] = g;
              });
              const groupList = Object.values(groups).sort((a, b) => b.outstanding - a.outstanding);
              if (groupList.length <= 1) return null;
              return (
                <div className="mb-4 p-3 bg-slate-50 border border-slate-200 rounded-lg" data-testid="loan-source-filter-block">
                  <div className="flex items-center gap-2 mb-2">
                    <Building2 className="w-4 h-4 text-slate-600" />
                    <span className="text-sm font-medium text-slate-700">Filter by Counterparty</span>
                    <span className="text-xs text-slate-500">(grouped by source for Taken / target for Given)</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setSourceFilter('all')}
                      data-testid="loan-filter-chip-all"
                      className={`px-3 py-1.5 rounded-full text-xs font-medium border transition ${sourceFilter === 'all' ? 'bg-slate-800 text-white border-slate-800' : 'bg-white text-slate-700 border-slate-300 hover:border-slate-500'}`}
                    >
                      All ({loans.length})
                    </button>
                    {groupList.map(g => (
                      <button
                        type="button"
                        key={g.key}
                        onClick={() => setSourceFilter(g.key)}
                        data-testid={`loan-filter-chip-${g.key}`}
                        title={`${g.count} loan(s) · Principal ${formatCurrency(g.principal, country)} · Outstanding ${formatCurrency(g.outstanding, country)}`}
                        className={`px-3 py-1.5 rounded-full text-xs font-medium border transition flex items-center gap-1.5 ${sourceFilter === g.key ? (g.isGiven ? 'bg-teal-600 text-white border-teal-600' : 'bg-blue-600 text-white border-blue-600') : (g.isGiven ? 'bg-teal-50 text-teal-700 border-teal-200 hover:border-teal-400' : 'bg-blue-50 text-blue-700 border-blue-200 hover:border-blue-400')}`}
                      >
                        <span>{g.label}</span>
                        <span className="opacity-75">· {g.count}</span>
                        {g.outstanding > 0 && (
                          <span className="opacity-90 font-semibold">· O/S {formatCurrency(g.outstanding, country).replace(/\.00$/, '')}</span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })()}
            {loans.length === 0 ? (
              <div className="text-center py-12">
                <Wallet className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <p className="text-gray-500">No loan entries found</p>
                <p className="text-sm text-gray-400">Working capital has not been utilized yet</p>
              </div>
            ) : (
              <div className="space-y-4">
                {loans.filter(l => {
                  if (sourceFilter === 'all') return true;
                  const isGiven = l.loan_type === 'given';
                  const key = isGiven ? (l.target_center || 'OTHER') : (l.source_center || 'HQ');
                  return key === sourceFilter;
                }).map(loan => {
                  const outstanding = loan.amount - loan.total_repaid;
                  const repaidPercent = (loan.total_repaid / loan.amount) * 100;
                  const isGiven = loan.loan_type === "given";
                  
                  return (
                    <div 
                      key={loan.loan_id} 
                      className={`border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer ${isGiven ? 'border-l-4 border-l-teal-500' : 'border-l-4 border-l-red-400'}`}
                      onClick={() => { setSelectedLoan(loan); setShowDetailModal(true); }}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="flex items-center gap-2">
                            <Badge className={isGiven ? 'bg-teal-100 text-teal-800' : 'bg-red-100 text-red-800'}>
                              {isGiven ? 'GIVEN' : 'TAKEN'}
                            </Badge>
                            <span className="font-mono text-sm text-gray-500">{loan.loan_id}</span>
                            <Badge className={STATUS_COLORS[loan.status]}>
                              {loan.status.replace('_', ' ')}
                            </Badge>
                          </div>
                          <p className="font-medium mt-1">{loan.reason}</p>
                          <p className="text-sm text-gray-500">Date: {loan.loan_date}</p>
                          {isGiven && loan.target_center && (
                            <p className="text-sm text-teal-600 font-medium">Given to: {loan.target_center_name || loan.target_center}</p>
                          )}
                          {!isGiven && loan.source_center && (
                            <p className="text-sm text-blue-600 font-medium">From: {loan.source_center_name || loan.source_center}</p>
                          )}
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold">{formatCurrency(loan.amount, country)}</p>
                          {outstanding > 0 && (
                            <p className="text-sm text-red-600">
                              Outstanding: {formatCurrency(outstanding, country)}
                            </p>
                          )}
                        </div>
                      </div>
                      
                      {/* Progress bar */}
                      <div className="mt-3">
                        <div className="flex justify-between text-xs text-gray-500 mb-1">
                          <span>Repaid: {formatCurrency(loan.total_repaid, country)}</span>
                          <span>{repaidPercent.toFixed(0)}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full ${loan.status === 'fully_repaid' ? 'bg-green-500' : 'bg-blue-500'}`}
                            style={{ width: `${Math.min(repaidPercent, 100)}%` }}
                          />
                        </div>
                      </div>
                      
                      {/* Action buttons */}
                      <div className="mt-3 flex gap-2 flex-wrap">
                        {loan.status !== 'fully_repaid' && (session?.is_super_admin || session?.is_admin) && (
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedLoan(loan);
                              setShowRepaymentModal(true);
                            }}
                          >
                            <ArrowUpCircle className="w-4 h-4 mr-1" />
                            Add Repayment
                          </Button>
                        )}
                        {session?.is_super_admin && (
                          <Button
                            size="sm"
                            variant="outline"
                            data-testid={`loan-delete-btn-${loan.loan_id}`}
                            className="text-red-600 border-red-300 hover:bg-red-50"
                            onClick={(e) => {
                              e.stopPropagation();
                              setLoanToDelete(loan);
                              setDeleteForce(false);
                              setShowDeleteModal(true);
                            }}
                          >
                            <Trash2 className="w-4 h-4 mr-1" />
                            Delete
                          </Button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Building2 className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <h3 className="text-lg font-medium text-gray-600">Select a Center</h3>
            <p className="text-gray-400 mt-1">Choose a center to view loan entries</p>
          </CardContent>
        </Card>
      )}

      {/* Create Loan Modal */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Loan Entry</DialogTitle>
            <DialogDescription>
              Record working capital usage as a loan for {selectedCenter}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {loanSummary && (
              <div className="p-3 bg-blue-50 rounded-lg text-sm">
                <p className="text-blue-700">
                  <strong>Available Working Capital:</strong> {formatCurrency(loanSummary.working_capital?.available, country)}
                </p>
              </div>
            )}
            <div>
              <Label>Loan Amount *</Label>
              <Input 
                type="number"
                placeholder="Enter amount"
                value={createForm.amount}
                onChange={(e) => setCreateForm(p => ({ ...p, amount: e.target.value }))}
              />
            </div>
            <div>
              <Label>Loan Source / Given By (Center) *</Label>
              <Select value={createForm.source_center} onValueChange={(v) => setCreateForm(p => ({ ...p, source_center: v }))}>
                <SelectTrigger data-testid="source-center-select">
                  <Building2 className="w-4 h-4 mr-2 text-muted-foreground" />
                  <SelectValue placeholder="Select source center" />
                </SelectTrigger>
                <SelectContent>
                  {centers.filter(c => c.code !== selectedCenter).map(c => (
                    <SelectItem key={c.code} value={c.code}>{c.code} - {c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground mt-1">This center will see a "Loan Given" entry automatically</p>
            </div>
            <div>
              <Label>Loan Date *</Label>
              <Input 
                type="date"
                value={createForm.loan_date}
                onChange={(e) => setCreateForm(p => ({ ...p, loan_date: e.target.value }))}
              />
            </div>
            <div>
              <Label>Reason *</Label>
              <Select value={createForm.reason} onValueChange={(v) => setCreateForm(p => ({ ...p, reason: v }))}>
                <SelectTrigger>
                  <SelectValue placeholder="Select reason" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Operational Expenses">Operational Expenses</SelectItem>
                  <SelectItem value="Equipment Purchase">Equipment Purchase</SelectItem>
                  <SelectItem value="Salary Advance">Salary Advance</SelectItem>
                  <SelectItem value="Vendor Payment">Vendor Payment</SelectItem>
                  <SelectItem value="Emergency Expense">Emergency Expense</SelectItem>
                  <SelectItem value="Other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Notes</Label>
              <Textarea 
                placeholder="Additional details..."
                value={createForm.notes}
                onChange={(e) => setCreateForm(p => ({ ...p, notes: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>Cancel</Button>
            <Button onClick={handleCreateLoan} disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
              Create Loan
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Repayment Modal */}
      <Dialog open={showRepaymentModal} onOpenChange={setShowRepaymentModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add Repayment</DialogTitle>
            <DialogDescription>
              Record a repayment for loan {selectedLoan?.loan_id}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {selectedLoan && (
              <div className="p-3 bg-gray-50 rounded-lg text-sm space-y-1">
                <p><strong>Loan Amount:</strong> {formatCurrency(selectedLoan.amount, country)}</p>
                <p><strong>Already Repaid:</strong> {formatCurrency(selectedLoan.total_repaid, country)}</p>
                <p className="text-red-600"><strong>Outstanding:</strong> {formatCurrency(selectedLoan.amount - selectedLoan.total_repaid, country)}</p>
              </div>
            )}
            <div>
              <Label>Repayment Amount *</Label>
              <Input 
                type="number"
                placeholder="Enter amount"
                value={repaymentForm.amount}
                onChange={(e) => setRepaymentForm(p => ({ ...p, amount: e.target.value }))}
                max={selectedLoan ? selectedLoan.amount - selectedLoan.total_repaid : undefined}
              />
            </div>
            <div>
              <Label>Repayment Date *</Label>
              <Input 
                type="date"
                value={repaymentForm.repayment_date}
                onChange={(e) => setRepaymentForm(p => ({ ...p, repayment_date: e.target.value }))}
              />
            </div>
            <div>
              <Label>Notes</Label>
              <Textarea 
                placeholder="Additional details..."
                value={repaymentForm.notes}
                onChange={(e) => setRepaymentForm(p => ({ ...p, notes: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRepaymentModal(false)}>Cancel</Button>
            <Button onClick={handleAddRepayment} disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ArrowUpCircle className="w-4 h-4 mr-2" />}
              Record Repayment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Loan Detail Modal */}
      <Dialog open={showDetailModal} onOpenChange={setShowDetailModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Loan Details</DialogTitle>
          </DialogHeader>
          {selectedLoan && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-gray-500">Loan ID</Label>
                  <p className="font-mono text-sm">{selectedLoan.loan_id}</p>
                </div>
                <div>
                  <Label className="text-gray-500">Status</Label>
                  <Badge className={STATUS_COLORS[selectedLoan.status]}>
                    {selectedLoan.status.replace('_', ' ')}
                  </Badge>
                </div>
                <div>
                  <Label className="text-gray-500">Amount</Label>
                  <p className="font-bold">{formatCurrency(selectedLoan.amount, country)}</p>
                </div>
                <div>
                  <Label className="text-gray-500">Loan Date</Label>
                  <p>{selectedLoan.loan_date}</p>
                </div>
                <div className="col-span-2">
                  <Label className="text-gray-500">Reason</Label>
                  <p>{selectedLoan.reason}</p>
                </div>
                {selectedLoan.notes && (
                  <div className="col-span-2">
                    <Label className="text-gray-500">Notes</Label>
                    <p className="text-sm">{selectedLoan.notes}</p>
                  </div>
                )}
              </div>

              <hr />

              <div>
                <div className="flex justify-between items-center mb-2">
                  <Label className="text-gray-500">Repayment History</Label>
                  <span className="text-sm">
                    {formatCurrency(selectedLoan.total_repaid, country)} / {formatCurrency(selectedLoan.amount, country)}
                  </span>
                </div>
                
                {selectedLoan.repayments?.length > 0 ? (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {selectedLoan.repayments.map((rep, idx) => (
                      <div key={idx} className="flex justify-between items-center p-2 bg-green-50 rounded">
                        <div>
                          <p className="text-sm font-medium text-green-800">{formatCurrency(rep.amount, country)}</p>
                          <p className="text-xs text-green-600">{rep.repayment_date}</p>
                        </div>
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-400 text-center py-4">No repayments recorded yet</p>
                )}
              </div>

              {selectedLoan.status !== 'fully_repaid' && (session?.is_super_admin || session?.is_admin) && (
                <Button 
                  className="w-full"
                  onClick={() => {
                    setShowDetailModal(false);
                    setShowRepaymentModal(true);
                  }}
                >
                  <ArrowUpCircle className="w-4 h-4 mr-2" />
                  Add Repayment
                </Button>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Modal */}
      <Dialog open={showDeleteModal} onOpenChange={setShowDeleteModal}>
        <DialogContent className="max-w-md" data-testid="loan-delete-modal">
          <DialogHeader>
            <DialogTitle className="text-red-600 flex items-center gap-2">
              <Trash2 className="w-5 h-5" />
              Delete Loan Entry
            </DialogTitle>
            <DialogDescription>
              This will permanently delete the loan and its mirrored entry on the linked center.
            </DialogDescription>
          </DialogHeader>
          {loanToDelete && (
            <div className="space-y-3">
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm space-y-1">
                <p><strong>Loan ID:</strong> <span className="font-mono">{loanToDelete.loan_id}</span></p>
                <p><strong>Type:</strong> {loanToDelete.loan_type === 'given' ? 'GIVEN' : 'TAKEN'}</p>
                <p><strong>Amount:</strong> {formatCurrency(loanToDelete.amount, country)}</p>
                <p><strong>Date:</strong> {loanToDelete.loan_date}</p>
                <p><strong>Total Repaid:</strong> {formatCurrency(loanToDelete.total_repaid, country)}</p>
                {loanToDelete.linked_loan_id && (
                  <p className="text-amber-700"><strong>Linked Mirror:</strong> <span className="font-mono">{loanToDelete.linked_loan_id}</span> (will also be deleted)</p>
                )}
              </div>
              {(loanToDelete.total_repaid || 0) > 0 && (
                <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <input
                    type="checkbox"
                    id="delete-force"
                    data-testid="loan-delete-force"
                    checked={deleteForce}
                    onChange={(e) => setDeleteForce(e.target.checked)}
                    className="mt-1"
                  />
                  <label htmlFor="delete-force" className="text-sm text-amber-800">
                    This loan has repayments. Check to force delete anyway (also clears the mirrored repayments).
                  </label>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteModal(false)} disabled={loading}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={handleDeleteLoan}
              disabled={loading || ((loanToDelete?.total_repaid || 0) > 0 && !deleteForce)}
              data-testid="loan-delete-confirm-btn"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Trash2 className="w-4 h-4 mr-2" />}
              Delete Permanently
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Delete Modal */}
      <Dialog open={showBulkDeleteModal} onOpenChange={setShowBulkDeleteModal}>
        <DialogContent className="max-w-md" data-testid="loan-bulk-delete-modal">
          <DialogHeader>
            <DialogTitle className="text-red-600 flex items-center gap-2">
              <Trash2 className="w-5 h-5" />
              Bulk Delete Loan Entries
            </DialogTitle>
            <DialogDescription>
              Delete loans by center scope and (optionally) by month. Mirrored linked entries are also removed.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Center Scope *</Label>
              <Select value={bulkCenter} onValueChange={setBulkCenter}>
                <SelectTrigger data-testid="loan-bulk-center-select">
                  <SelectValue placeholder="Select scope" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">ALL CENTERS</SelectItem>
                  {centers.map(c => (
                    <SelectItem key={c.code} value={c.code}>{c.code} - {c.name || c.code}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Month (optional, leave blank for all months)</Label>
              <Input
                type="month"
                value={bulkMonth}
                onChange={(e) => setBulkMonth(e.target.value)}
                data-testid="loan-bulk-month-input"
              />
              <p className="text-xs text-muted-foreground mt-1">Filters by loan_date YYYY-MM</p>
            </div>
            <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <input
                type="checkbox"
                id="bulk-force"
                data-testid="loan-bulk-force"
                checked={bulkForce}
                onChange={(e) => setBulkForce(e.target.checked)}
                className="mt-1"
              />
              <label htmlFor="bulk-force" className="text-sm text-amber-800">
                Force delete loans that already have repayments (otherwise they'll be skipped).
              </label>
            </div>
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              <strong>Warning:</strong> This action cannot be undone. Confirm scope:
              <div className="mt-1 font-mono text-xs">
                center = {bulkCenter || '(none)'} | month = {bulkMonth || 'ALL MONTHS'} | force = {bulkForce ? 'yes' : 'no'}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBulkDeleteModal(false)} disabled={loading}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={handleBulkDelete}
              disabled={loading || !bulkCenter}
              data-testid="loan-bulk-delete-confirm-btn"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Trash2 className="w-4 h-4 mr-2" />}
              Delete Matching Loans
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
