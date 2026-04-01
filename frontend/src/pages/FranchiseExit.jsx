import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Checkbox } from '../components/ui/checkbox';
import { toast } from 'sonner';
import { 
  FileText, AlertTriangle, CheckCircle, Clock, Users, Building, 
  DollarSign, ClipboardCheck, Download, Plus, Trash2, X, Loader2,
  FileSignature, Package, Calculator, Award, ArrowRight, RefreshCw
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const EXIT_REASONS = [
  { value: 'losses', label: 'Continuous Operational Losses' },
  { value: 'voluntary', label: 'Voluntary Closure by Franchisee' },
  { value: 'mutual_decision', label: 'Mutual Decision' },
  { value: 'breach', label: 'Breach of Agreement' },
  { value: 'other', label: 'Other Reasons' }
];

const ASSET_CATEGORIES = [
  { key: 'kitchen_equipment', label: 'Kitchen Equipment', icon: '🍳' },
  { key: 'furniture_fixtures', label: 'Furniture & Fixtures', icon: '🪑' },
  { key: 'utensils_machinery', label: 'Utensils & Machinery', icon: '🔧' },
  { key: 'food_inventory', label: 'Food Inventory', icon: '🍲' },
  { key: 'packaging_materials', label: 'Packaging Materials', icon: '📦' },
  { key: 'other_assets', label: 'Other Assets', icon: '📋' }
];

const STATUS_COLORS = {
  initiated: 'bg-yellow-100 text-yellow-800',
  in_progress: 'bg-blue-100 text-blue-800',
  pending_signatures: 'bg-purple-100 text-purple-800',
  completed: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800'
};

export default function FranchiseExit() {
  const { session } = useAuth();
  const token = session?.token;
  const isFranchiseOwner = session?.role_key === "franchise_owner";
  const [exits, setExits] = useState([]);
  const [franchises, setFranchises] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedExit, setSelectedExit] = useState(null);
  const [activeTab, setActiveTab] = useState('list');
  
  // Modal states
  const [showInitiateModal, setShowInitiateModal] = useState(false);
  const [showAssetModal, setShowAssetModal] = useState(false);
  const [showFinanceModal, setShowFinanceModal] = useState(false);
  const [showSignatureModal, setShowSignatureModal] = useState(false);
  const [showComplianceModal, setShowComplianceModal] = useState(false);
  
  // Form states
  const [initiateForm, setInitiateForm] = useState({
    franchise_code: '',
    exit_reason: '',
    exit_reason_details: '',
    effective_date: '',
    initiated_by: 'franchisor'
  });
  
  const [assetForm, setAssetForm] = useState({
    kitchen_equipment: [],
    furniture_fixtures: [],
    utensils_machinery: [],
    food_inventory: [],
    packaging_materials: [],
    other_assets: [],
    condition_notes: ''
  });
  
  const [financeForm, setFinanceForm] = useState({
    working_capital_balance: 0,
    staff_salary_current: 0,
    shop_rental_current: 0,
    vendor_payments: 0,
    utility_bills: 0,
    other_dues: 0,
    settlement_notes: ''
  });
  
  const [signatureForm, setSignatureForm] = useState({
    // Franchisor signatories
    sandeep_selected: false,
    jayanti_selected: false,
    // Exit manager
    exit_manager_name: '',
    exit_manager_designation: 'Exit Manager',
    // Franchisee directors (auto-pulled)
    franchisee_directors: []
  });
  const [franchiseDirectors, setFranchiseDirectors] = useState([]);
  
  const [complianceForm, setComplianceForm] = useState({
    no_pending_payments: false,
    brand_assets_transferred: false,
    financial_report_signed: false,
    handover_report_signed: false
  });

  // Fetch exits
  const fetchExits = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/franchise-exit/list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      });
      const data = await res.json();
      if (data.success) {
        setExits(data.exits || []);
      }
    } catch (error) {
      toast.error('Failed to fetch exit records');
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Fetch franchises
  const fetchFranchises = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/franchises/list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      });
      const data = await res.json();
      if (data.franchises) {
        setFranchises(data.franchises.filter(f => f.status === 'Active'));
      }
    } catch (error) {
      console.error('Failed to fetch franchises');
    }
  }, [token]);

  useEffect(() => {
    fetchExits();
    if (!isFranchiseOwner) fetchFranchises();
  }, [fetchExits, fetchFranchises, isFranchiseOwner]);

  // Initiate Exit
  const handleInitiateExit = async () => {
    if (!initiateForm.franchise_code || !initiateForm.exit_reason || !initiateForm.effective_date) {
      toast.error('Please fill all required fields');
      return;
    }
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/franchise-exit/initiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, ...initiateForm })
      });
      const data = await res.json();
      if (data.success) {
        toast.success('Exit process initiated successfully');
        setShowInitiateModal(false);
        setInitiateForm({
          franchise_code: '',
          exit_reason: '',
          exit_reason_details: '',
          effective_date: '',
          initiated_by: 'franchisor'
        });
        fetchExits();
      } else {
        toast.error(data.detail || 'Failed to initiate exit');
      }
    } catch (error) {
      toast.error('Failed to initiate exit');
    } finally {
      setLoading(false);
    }
  };

  // Update Asset Handover
  const handleUpdateAssets = async () => {
    if (!selectedExit) return;
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/franchise-exit/update-asset-handover/${selectedExit.exit_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, ...assetForm })
      });
      const data = await res.json();
      if (data.success) {
        toast.success('Asset handover updated');
        setShowAssetModal(false);
        fetchExitDetails(selectedExit.exit_id);
      } else {
        toast.error(data.detail || 'Failed to update assets');
      }
    } catch (error) {
      toast.error('Failed to update assets');
    } finally {
      setLoading(false);
    }
  };

  // Update Financial Settlement
  const handleUpdateFinance = async () => {
    if (!selectedExit) return;
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/franchise-exit/update-financial-settlement/${selectedExit.exit_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, ...financeForm })
      });
      const data = await res.json();
      if (data.success) {
        toast.success('Financial settlement updated');
        setShowFinanceModal(false);
        fetchExitDetails(selectedExit.exit_id);
      } else {
        toast.error(data.detail || 'Failed to update settlement');
      }
    } catch (error) {
      toast.error('Failed to update settlement');
    } finally {
      setLoading(false);
    }
  };

  // Migrate signatures for current exit (pull from master data)
  const handleMigrateSignatures = async () => {
    if (!selectedExit) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/franchise-exit/migrate-signatures/${selectedExit.exit_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      });
      const data = await res.json();
      if (data.success) {
        toast.success('Signatures updated from master data');
        fetchExitDetails(selectedExit.exit_id);
      } else {
        toast.error(data.detail || 'Migration failed');
      }
    } catch (error) {
      toast.error('Failed to migrate signatures');
    } finally {
      setLoading(false);
    }
  };

  // Migrate ALL exit signatures at once
  const handleMigrateAllSignatures = async () => {
    if (!window.confirm('This will update signature structure for ALL existing exit records. Continue?')) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/franchise-exit/migrate-all-signatures`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      });
      const data = await res.json();
      if (data.success) {
        toast.success(`${data.results?.length || 0} exit records updated`);
        if (selectedExit) fetchExitDetails(selectedExit.exit_id);
      } else {
        toast.error(data.detail || 'Migration failed');
      }
    } catch (error) {
      toast.error('Failed to migrate');
    } finally {
      setLoading(false);
    }
  };

  // Fetch franchise directors when opening signature modal
  const fetchFranchiseDirectors = useCallback(async (franchiseCode) => {
    try {
      const res = await fetch(`${API}/api/franchise-exit/franchise-directors/${franchiseCode}`);
      const data = await res.json();
      setFranchiseDirectors(data.directors || []);
    } catch {
      setFranchiseDirectors([]);
    }
  }, []);

  // Open signature modal with pre-populated data
  const openSignatureModal = () => {
    if (!selectedExit) return;
    const sigs = selectedExit.signatures || {};
    
    // Pre-fill from existing data
    const existingFranchisor = sigs.franchisor_signatories || [];
    const existingManager = sigs.exit_manager || null;
    
    setSignatureForm({
      sandeep_selected: existingFranchisor.some(s => s.signer_name === 'Sandeep Gadhwal'),
      jayanti_selected: existingFranchisor.some(s => s.signer_name === 'Jayanti Kathale'),
      exit_manager_name: existingManager?.signer_name || selectedExit.initiated_by_user || '',
      exit_manager_designation: existingManager?.signer_designation || 'Exit Manager',
      franchisee_directors: []
    });
    
    // Fetch directors
    fetchFranchiseDirectors(selectedExit.franchise_code);
    setShowSignatureModal(true);
  };

  // Add Signatures (all three sections at once)
  const handleAddSignature = async () => {
    if (!selectedExit) return;
    
    const { sandeep_selected, jayanti_selected, exit_manager_name } = signatureForm;
    
    if (!sandeep_selected && !jayanti_selected) {
      toast.error('Please select at least one Franchisor signatory');
      return;
    }
    if (!exit_manager_name.trim()) {
      toast.error('Please enter Exit Manager name');
      return;
    }
    if (franchiseDirectors.length === 0) {
      toast.error('No directors found for this franchise');
      return;
    }

    setLoading(true);
    try {
      // 1. Save Franchisor Signatories
      const selectedSignatories = [];
      if (sandeep_selected) selectedSignatories.push('Sandeep Gadhwal');
      if (jayanti_selected) selectedSignatories.push('Jayanti Kathale');
      
      await fetch(`${API}/api/franchise-exit/sign/${selectedExit.exit_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token,
          signer_type: 'franchisor_signatories',
          selected_signatories: selectedSignatories
        })
      });

      // 2. Save Exit Manager
      await fetch(`${API}/api/franchise-exit/sign/${selectedExit.exit_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token,
          signer_type: 'exit_manager',
          signer_name: exit_manager_name.trim(),
          signer_designation: signatureForm.exit_manager_designation
        })
      });

      // 3. Save Franchisee Directors
      await fetch(`${API}/api/franchise-exit/sign/${selectedExit.exit_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token,
          signer_type: 'franchisee_directors',
          directors: franchiseDirectors
        })
      });

      toast.success('All signatures recorded successfully');
      setShowSignatureModal(false);
      fetchExitDetails(selectedExit.exit_id);
    } catch (error) {
      toast.error('Failed to record signatures');
    } finally {
      setLoading(false);
    }
  };

  // Update Compliance
  const handleUpdateCompliance = async () => {
    if (!selectedExit) return;
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/franchise-exit/update-compliance/${selectedExit.exit_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, ...complianceForm })
      });
      const data = await res.json();
      if (data.success) {
        toast.success('Compliance checklist updated');
        setShowComplianceModal(false);
        fetchExitDetails(selectedExit.exit_id);
      } else {
        toast.error(data.detail || 'Failed to update compliance');
      }
    } catch (error) {
      toast.error('Failed to update compliance');
    } finally {
      setLoading(false);
    }
  };

  // Complete Exit
  const handleCompleteExit = async () => {
    if (!selectedExit) return;
    
    if (!window.confirm('Are you sure you want to finalize this exit? This action cannot be undone.')) {
      return;
    }
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/franchise-exit/complete/${selectedExit.exit_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      });
      const data = await res.json();
      if (data.success) {
        toast.success('Exit process completed successfully');
        fetchExitDetails(selectedExit.exit_id);
        fetchExits();
      } else {
        toast.error(data.detail || 'Failed to complete exit');
      }
    } catch (error) {
      toast.error('Failed to complete exit');
    } finally {
      setLoading(false);
    }
  };

  // Cancel Exit
  const handleCancelExit = async () => {
    if (!selectedExit) return;
    
    const reason = window.prompt('Please enter cancellation reason:');
    if (!reason) return;
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/franchise-exit/cancel/${selectedExit.exit_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, cancellation_reason: reason })
      });
      const data = await res.json();
      if (data.success) {
        toast.success('Exit process cancelled');
        fetchExitDetails(selectedExit.exit_id);
        fetchExits();
      } else {
        toast.error(data.detail || 'Failed to cancel exit');
      }
    } catch (error) {
      toast.error('Failed to cancel exit');
    } finally {
      setLoading(false);
    }
  };

  // Fetch exit details
  const fetchExitDetails = async (exitId) => {
    try {
      const res = await fetch(`${API}/api/franchise-exit/get/${exitId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      });
      const data = await res.json();
      if (data.success) {
        setSelectedExit(data.exit);
        // Populate forms with existing data
        if (data.exit.asset_handover) {
          setAssetForm(data.exit.asset_handover);
        }
        if (data.exit.financial_settlement) {
          setFinanceForm(data.exit.financial_settlement);
        }
        if (data.exit.compliance_checklist) {
          setComplianceForm(data.exit.compliance_checklist);
        }
      }
    } catch (error) {
      toast.error('Failed to fetch exit details');
    }
  };

  // Download document
  const downloadDocument = async (docType) => {
    if (!selectedExit) return;
    
    const endpoints = {
      agreement: 'generate-exit-agreement',
      handover: 'generate-handover-report',
      settlement: 'generate-settlement-sheet',
      certificate: 'generate-exit-certificate'
    };
    
    const filenames = {
      agreement: 'Exit_Agreement',
      handover: 'Handover_Report',
      settlement: 'Settlement_Sheet',
      certificate: 'Exit_Certificate'
    };
    
    try {
      toast.info(`Generating ${docType}...`);
      const res = await fetch(`${API}/api/franchise-exit/${endpoints[docType]}/${selectedExit.exit_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      });
      
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to generate document');
      }
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${filenames[docType]}_${selectedExit.exit_id}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('Document downloaded');
    } catch (error) {
      toast.error(error.message || 'Failed to download document');
    }
  };

  // Add asset item
  const addAssetItem = (category) => {
    setAssetForm(prev => ({
      ...prev,
      [category]: [...prev[category], { name: '', quantity: '', condition: 'Good', remarks: '' }]
    }));
  };

  // Remove asset item
  const removeAssetItem = (category, index) => {
    setAssetForm(prev => ({
      ...prev,
      [category]: prev[category].filter((_, i) => i !== index)
    }));
  };

  // Update asset item
  const updateAssetItem = (category, index, field, value) => {
    setAssetForm(prev => ({
      ...prev,
      [category]: prev[category].map((item, i) => 
        i === index ? { ...item, [field]: value } : item
      )
    }));
  };

  // Calculate net settlement
  const calculateNetSettlement = () => {
    const balance = parseFloat(financeForm.working_capital_balance) || 0;
    const deductions = 
      (parseFloat(financeForm.staff_salary_current) || 0) +
      (parseFloat(financeForm.shop_rental_current) || 0) +
      (parseFloat(financeForm.vendor_payments) || 0) +
      (parseFloat(financeForm.utility_bills) || 0) +
      (parseFloat(financeForm.other_dues) || 0);
    return balance - deductions;
  };

  // Get step status
  const getStepStatus = (stepKey) => {
    if (!selectedExit?.steps_completed) return false;
    return selectedExit.steps_completed[stepKey];
  };

  // Render exit list
  const renderExitList = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-gray-800">
          {isFranchiseOwner ? "Your Exit Records" : "Exit Records"}
        </h2>
        {!isFranchiseOwner && (
          <Button onClick={() => setShowInitiateModal(true)} data-testid="initiate-exit-btn">
            <Plus className="w-4 h-4 mr-2" />
            Initiate Exit
          </Button>
        )}
      </div>
      
      {exits.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p className="text-gray-500">
              {isFranchiseOwner ? "No exit process has been initiated for your franchise" : "No exit records found"}
            </p>
            {!isFranchiseOwner && (
              <p className="text-sm text-gray-400 mt-1">Click "Initiate Exit" to start a new exit process</p>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {exits.map(exit => (
            <Card 
              key={exit.exit_id} 
              className="cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => {
                fetchExitDetails(exit.exit_id);
                setActiveTab('details');
              }}
              data-testid={`exit-card-${exit.exit_id}`}
            >
              <CardContent className="p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold">{exit.franchise_code}</h3>
                      <Badge className={STATUS_COLORS[exit.status] || 'bg-gray-100'}>
                        {exit.status.replace('_', ' ')}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-600">{exit.franchise_name}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      Exit ID: {exit.exit_id}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-600">Effective Date</p>
                    <p className="font-medium">{exit.effective_date}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {EXIT_REASONS.find(r => r.value === exit.exit_reason)?.label || exit.exit_reason}
                    </p>
                  </div>
                </div>
                
                {/* Progress indicators */}
                <div className="mt-4 flex gap-1">
                  {['exit_agreement', 'asset_handover', 'financial_settlement', 'compliance_confirmation', 'exit_certificate'].map(step => (
                    <div 
                      key={step}
                      className={`flex-1 h-2 rounded ${exit.steps_completed?.[step] ? 'bg-green-500' : 'bg-gray-200'}`}
                      title={step.replace('_', ' ')}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );

  // Render exit details
  const renderExitDetails = () => {
    if (!selectedExit) {
      return (
        <div className="text-center py-12">
          <p className="text-gray-500">Select an exit record to view details</p>
          <Button variant="outline" className="mt-4" onClick={() => setActiveTab('list')}>
            Back to List
          </Button>
        </div>
      );
    }

    const isCompleted = selectedExit.status === 'completed';
    const isCancelled = selectedExit.status === 'cancelled';
    const canEdit = !isCompleted && !isCancelled && !isFranchiseOwner;

    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div>
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="sm" onClick={() => setActiveTab('list')}>
                ← Back
              </Button>
              <h2 className="text-xl font-semibold">{selectedExit.franchise_code}</h2>
              <Badge className={STATUS_COLORS[selectedExit.status] || 'bg-gray-100'}>
                {selectedExit.status.replace('_', ' ')}
              </Badge>
            </div>
            <p className="text-gray-600 ml-16">{selectedExit.franchise_name}</p>
            <p className="text-sm text-gray-400 ml-16">{selectedExit.legal_entity_name}</p>
          </div>
          {canEdit && (
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleCancelExit} className="text-red-600">
                <X className="w-4 h-4 mr-2" />
                Cancel Exit
              </Button>
              <Button onClick={handleCompleteExit} disabled={!Object.values(selectedExit.steps_completed || {}).slice(0, 4).every(Boolean)}>
                <CheckCircle className="w-4 h-4 mr-2" />
                Complete Exit
              </Button>
            </div>
          )}
        </div>

        {/* Exit Info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Exit Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <Label className="text-gray-500">Exit ID</Label>
                <p className="font-mono text-sm">{selectedExit.exit_id}</p>
              </div>
              <div>
                <Label className="text-gray-500">Effective Date</Label>
                <p className="font-medium">{selectedExit.effective_date}</p>
              </div>
              <div>
                <Label className="text-gray-500">Initiated By</Label>
                <p className="capitalize">{selectedExit.initiated_by}</p>
              </div>
              <div>
                <Label className="text-gray-500">Reason</Label>
                <p>{EXIT_REASONS.find(r => r.value === selectedExit.exit_reason)?.label || selectedExit.exit_reason}</p>
              </div>
            </div>
            {selectedExit.exit_reason_details && (
              <div className="mt-4">
                <Label className="text-gray-500">Details</Label>
                <p className="text-sm">{selectedExit.exit_reason_details}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Progress Steps */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {/* Step 1: Exit Agreement */}
          <Card className={getStepStatus('exit_agreement') ? 'border-green-500' : ''}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <FileSignature className="w-5 h-5 text-blue-600" />
                <span className="font-medium">Exit Agreement</span>
                {getStepStatus('exit_agreement') && <CheckCircle className="w-4 h-4 text-green-500" />}
              </div>
              <p className="text-xs text-gray-500 mb-3">Signatures from both parties</p>
              <Button 
                size="sm" 
                variant="outline" 
                className="w-full"
                onClick={() => openSignatureModal()}
                disabled={!canEdit}
              >
                {canEdit ? 'Add Signature' : 'View'}
              </Button>
              {(getStepStatus('exit_agreement') || selectedExit.signatures?.franchisor || selectedExit.signatures?.franchisee) && (
                <Button 
                  size="sm" 
                  variant="ghost" 
                  className="w-full mt-1"
                  onClick={() => downloadDocument('agreement')}
                >
                  <Download className="w-3 h-3 mr-1" /> PDF
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Step 2: Asset Handover */}
          <Card className={getStepStatus('asset_handover') ? 'border-green-500' : ''}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <Package className="w-5 h-5 text-orange-600" />
                <span className="font-medium">Asset Handover</span>
                {getStepStatus('asset_handover') && <CheckCircle className="w-4 h-4 text-green-500" />}
              </div>
              <p className="text-xs text-gray-500 mb-3">Physical assets checklist</p>
              <Button 
                size="sm" 
                variant="outline" 
                className="w-full"
                onClick={() => setShowAssetModal(true)}
                disabled={!canEdit}
              >
                {canEdit ? 'Record Assets' : 'View'}
              </Button>
              {getStepStatus('asset_handover') && (
                <Button 
                  size="sm" 
                  variant="ghost" 
                  className="w-full mt-1"
                  onClick={() => downloadDocument('handover')}
                >
                  <Download className="w-3 h-3 mr-1" /> PDF
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Step 3: Financial Settlement */}
          <Card className={getStepStatus('financial_settlement') ? 'border-green-500' : ''}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <Calculator className="w-5 h-5 text-green-600" />
                <span className="font-medium">Settlement</span>
                {getStepStatus('financial_settlement') && <CheckCircle className="w-4 h-4 text-green-500" />}
              </div>
              <p className="text-xs text-gray-500 mb-3">Financial reconciliation</p>
              <Button 
                size="sm" 
                variant="outline" 
                className="w-full"
                onClick={() => setShowFinanceModal(true)}
                disabled={!canEdit}
              >
                {canEdit ? 'Enter Details' : 'View'}
              </Button>
              {getStepStatus('financial_settlement') && (
                <Button 
                  size="sm" 
                  variant="ghost" 
                  className="w-full mt-1"
                  onClick={() => downloadDocument('settlement')}
                >
                  <Download className="w-3 h-3 mr-1" /> PDF
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Step 4: Compliance */}
          <Card className={getStepStatus('compliance_confirmation') ? 'border-green-500' : ''}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <ClipboardCheck className="w-5 h-5 text-purple-600" />
                <span className="font-medium">Compliance</span>
                {getStepStatus('compliance_confirmation') && <CheckCircle className="w-4 h-4 text-green-500" />}
              </div>
              <p className="text-xs text-gray-500 mb-3">Final checklist</p>
              <Button 
                size="sm" 
                variant="outline" 
                className="w-full"
                onClick={() => setShowComplianceModal(true)}
                disabled={!canEdit}
              >
                {canEdit ? 'Update' : 'View'}
              </Button>
            </CardContent>
          </Card>

          {/* Step 5: Certificate */}
          <Card className={getStepStatus('exit_certificate') ? 'border-green-500' : ''}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <Award className="w-5 h-5 text-yellow-600" />
                <span className="font-medium">Certificate</span>
                {getStepStatus('exit_certificate') && <CheckCircle className="w-4 h-4 text-green-500" />}
              </div>
              <p className="text-xs text-gray-500 mb-3">Final exit certificate</p>
              {isCompleted ? (
                <Button 
                  size="sm" 
                  className="w-full"
                  onClick={() => downloadDocument('certificate')}
                >
                  <Download className="w-3 h-3 mr-1" /> Download
                </Button>
              ) : (
                <p className="text-xs text-gray-400 text-center">Complete all steps first</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Signatures Summary */}
        {selectedExit.signatures && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Signatures</CardTitle>
                <div className="flex gap-2">
                  <Button 
                    size="sm" variant="outline" 
                    onClick={handleMigrateSignatures} 
                    disabled={loading}
                    data-testid="refresh-signatures-btn"
                  >
                    {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <RefreshCw className="w-3.5 h-3.5 mr-1" />}
                    Refresh from Master Data
                  </Button>
                  {!isFranchiseOwner && (
                    <Button 
                      size="sm" variant="outline"
                      onClick={handleMigrateAllSignatures}
                      disabled={loading}
                      data-testid="migrate-all-signatures-btn"
                      className="text-xs"
                    >
                      Update All Exits
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* FRANCHISOR SIGNATORIES */}
              <div>
                <h4 className="font-semibold text-sm text-gray-600 mb-3 uppercase tracking-wide">Franchisor (Purnabramha)</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {(selectedExit.signatures.franchisor_signatories?.length > 0) ? (
                    selectedExit.signatures.franchisor_signatories.map((s, i) => (
                      <div key={i} className="p-4 bg-green-50 rounded-lg border border-green-200">
                        <div className="flex items-center gap-2 mb-1">
                          <CheckCircle className="w-4 h-4 text-green-600" />
                          <span className="font-medium text-sm">{s.signer_name}</span>
                        </div>
                        <p className="text-xs text-gray-500 ml-6">{s.signer_designation}</p>
                        <p className="text-xs text-gray-400 ml-6">Signed: {new Date(s.signature_date).toLocaleDateString()}</p>
                      </div>
                    ))
                  ) : selectedExit.signatures.franchisor ? (
                    <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                      <div className="flex items-center gap-2 mb-1">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        <span className="font-medium text-sm">{selectedExit.signatures.franchisor.signer_name}</span>
                      </div>
                      <p className="text-xs text-gray-500 ml-6">{selectedExit.signatures.franchisor.signer_designation}</p>
                      <p className="text-xs text-gray-400 ml-6">Signed: {new Date(selectedExit.signatures.franchisor.signature_date).toLocaleDateString()}</p>
                    </div>
                  ) : (
                    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                      <p className="text-sm text-gray-400">Pending</p>
                    </div>
                  )}
                </div>
              </div>

              {/* EXIT MANAGER */}
              <div>
                <h4 className="font-semibold text-sm text-gray-600 mb-3 uppercase tracking-wide">Exit Manager (Franchisor Side)</h4>
                {selectedExit.signatures.exit_manager ? (
                  <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="flex items-center gap-2 mb-1">
                      <CheckCircle className="w-4 h-4 text-blue-600" />
                      <span className="font-medium text-sm">{selectedExit.signatures.exit_manager.signer_name}</span>
                    </div>
                    <p className="text-xs text-gray-500 ml-6">{selectedExit.signatures.exit_manager.signer_role || selectedExit.signatures.exit_manager.signer_designation}</p>
                    <p className="text-xs text-gray-400 ml-6">Signed: {new Date(selectedExit.signatures.exit_manager.signature_date).toLocaleDateString()}</p>
                  </div>
                ) : (
                  <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <p className="text-sm text-gray-400">Pending</p>
                  </div>
                )}
              </div>

              {/* FRANCHISEE DIRECTORS */}
              <div>
                <h4 className="font-semibold text-sm text-gray-600 mb-3 uppercase tracking-wide">Franchisee Directors</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {(selectedExit.signatures.franchisee_directors?.length > 0) ? (
                    selectedExit.signatures.franchisee_directors.map((d, i) => (
                      <div key={i} className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                        <div className="flex items-center gap-2 mb-1">
                          <CheckCircle className="w-4 h-4 text-amber-600" />
                          <span className="font-medium text-sm">{d.signer_name}</span>
                        </div>
                        <p className="text-xs text-gray-500 ml-6">{d.signer_designation}</p>
                        <p className="text-xs text-gray-400 ml-6">Signed: {new Date(d.signature_date).toLocaleDateString()}</p>
                      </div>
                    ))
                  ) : selectedExit.signatures.franchisee ? (
                    <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                      <div className="flex items-center gap-2 mb-1">
                        <CheckCircle className="w-4 h-4 text-amber-600" />
                        <span className="font-medium text-sm">{selectedExit.signatures.franchisee.signer_name}</span>
                      </div>
                      <p className="text-xs text-gray-500 ml-6">{selectedExit.signatures.franchisee.signer_designation}</p>
                      <p className="text-xs text-gray-400 ml-6">Signed: {new Date(selectedExit.signatures.franchisee.signature_date).toLocaleDateString()}</p>
                    </div>
                  ) : (
                    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                      <p className="text-sm text-gray-400">Pending</p>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Financial Summary */}
        {selectedExit.financial_settlement && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Financial Settlement Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div className="bg-blue-50 p-3 rounded-lg">
                  <p className="text-sm text-blue-600">Working Capital</p>
                  <p className="text-lg font-semibold">Rs. {selectedExit.financial_settlement.working_capital_balance?.toLocaleString()}</p>
                </div>
                <div className="bg-red-50 p-3 rounded-lg">
                  <p className="text-sm text-red-600">Total Deductions</p>
                  <p className="text-lg font-semibold">Rs. {(
                    (selectedExit.financial_settlement.staff_salary_current || 0) +
                    (selectedExit.financial_settlement.shop_rental_current || 0) +
                    (selectedExit.financial_settlement.vendor_payments || 0) +
                    (selectedExit.financial_settlement.utility_bills || 0) +
                    (selectedExit.financial_settlement.other_dues || 0)
                  ).toLocaleString()}</p>
                </div>
                <div className="bg-green-50 p-3 rounded-lg col-span-2">
                  <p className="text-sm text-green-600">Net Settlement Amount</p>
                  <p className="text-2xl font-bold text-green-700">
                    Rs. {selectedExit.financial_settlement.total_settlement?.toLocaleString()}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    );
  };

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="franchise-exit-page">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Franchise Exit & Closure</h1>
        <p className="text-gray-600">Manage franchise exit processes and generate legal documents</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="list">Exit Records</TabsTrigger>
          <TabsTrigger value="details" disabled={!selectedExit}>Exit Details</TabsTrigger>
        </TabsList>
        
        <TabsContent value="list" className="mt-6">
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
          ) : renderExitList()}
        </TabsContent>
        
        <TabsContent value="details" className="mt-6">
          {renderExitDetails()}
        </TabsContent>
      </Tabs>

      {/* Initiate Exit Modal */}
      <Dialog open={showInitiateModal} onOpenChange={setShowInitiateModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Initiate Franchise Exit</DialogTitle>
            <DialogDescription>Start the exit process for a franchise</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Franchise *</Label>
              <Select value={initiateForm.franchise_code} onValueChange={(v) => setInitiateForm(p => ({ ...p, franchise_code: v }))}>
                <SelectTrigger data-testid="franchise-select">
                  <SelectValue placeholder="Select franchise" />
                </SelectTrigger>
                <SelectContent>
                  {franchises.map(f => (
                    <SelectItem key={f.franchise_code} value={f.franchise_code}>
                      {f.franchise_code} - {f.franchise_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Exit Reason *</Label>
              <Select value={initiateForm.exit_reason} onValueChange={(v) => setInitiateForm(p => ({ ...p, exit_reason: v }))}>
                <SelectTrigger data-testid="reason-select">
                  <SelectValue placeholder="Select reason" />
                </SelectTrigger>
                <SelectContent>
                  {EXIT_REASONS.map(r => (
                    <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Reason Details</Label>
              <Textarea 
                placeholder="Additional details..."
                value={initiateForm.exit_reason_details}
                onChange={(e) => setInitiateForm(p => ({ ...p, exit_reason_details: e.target.value }))}
              />
            </div>
            <div>
              <Label>Effective Date *</Label>
              <Input 
                type="date"
                value={initiateForm.effective_date}
                onChange={(e) => setInitiateForm(p => ({ ...p, effective_date: e.target.value }))}
                data-testid="effective-date-input"
              />
            </div>
            <div>
              <Label>Initiated By</Label>
              <Select value={initiateForm.initiated_by} onValueChange={(v) => setInitiateForm(p => ({ ...p, initiated_by: v }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="franchisor">Franchisor</SelectItem>
                  <SelectItem value="franchisee">Franchisee</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowInitiateModal(false)}>Cancel</Button>
            <Button onClick={handleInitiateExit} disabled={loading} data-testid="confirm-initiate-btn">
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Initiate Exit
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Asset Handover Modal */}
      <Dialog open={showAssetModal} onOpenChange={setShowAssetModal}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Asset Handover Record</DialogTitle>
            <DialogDescription>Record all physical assets being transferred to the franchisee</DialogDescription>
          </DialogHeader>
          <div className="space-y-6">
            {ASSET_CATEGORIES.map(cat => (
              <div key={cat.key} className="border rounded-lg p-4">
                <div className="flex justify-between items-center mb-3">
                  <h4 className="font-medium">{cat.icon} {cat.label}</h4>
                  <Button size="sm" variant="outline" onClick={() => addAssetItem(cat.key)}>
                    <Plus className="w-3 h-3 mr-1" /> Add
                  </Button>
                </div>
                {assetForm[cat.key]?.length > 0 ? (
                  <div className="space-y-2">
                    {assetForm[cat.key].map((item, idx) => (
                      <div key={idx} className="grid grid-cols-12 gap-2 items-center">
                        <Input 
                          className="col-span-4"
                          placeholder="Item name"
                          value={item.name}
                          onChange={(e) => updateAssetItem(cat.key, idx, 'name', e.target.value)}
                        />
                        <Input 
                          className="col-span-2"
                          placeholder="Qty"
                          value={item.quantity}
                          onChange={(e) => updateAssetItem(cat.key, idx, 'quantity', e.target.value)}
                        />
                        <Select value={item.condition} onValueChange={(v) => updateAssetItem(cat.key, idx, 'condition', v)}>
                          <SelectTrigger className="col-span-2">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Good">Good</SelectItem>
                            <SelectItem value="Fair">Fair</SelectItem>
                            <SelectItem value="Poor">Poor</SelectItem>
                            <SelectItem value="New">New</SelectItem>
                          </SelectContent>
                        </Select>
                        <Input 
                          className="col-span-3"
                          placeholder="Remarks"
                          value={item.remarks}
                          onChange={(e) => updateAssetItem(cat.key, idx, 'remarks', e.target.value)}
                        />
                        <Button size="icon" variant="ghost" onClick={() => removeAssetItem(cat.key, idx)}>
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-400">No items added</p>
                )}
              </div>
            ))}
            <div>
              <Label>General Condition Notes</Label>
              <Textarea 
                placeholder="Overall condition notes..."
                value={assetForm.condition_notes}
                onChange={(e) => setAssetForm(p => ({ ...p, condition_notes: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAssetModal(false)}>Cancel</Button>
            <Button onClick={handleUpdateAssets} disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Save Assets
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Financial Settlement Modal */}
      <Dialog open={showFinanceModal} onOpenChange={setShowFinanceModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Financial Settlement</DialogTitle>
            <DialogDescription>Enter all financial details for settlement calculation</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <Label className="text-blue-700">Working Capital Balance (Credit)</Label>
              <Input 
                type="number"
                value={financeForm.working_capital_balance}
                onChange={(e) => setFinanceForm(p => ({ ...p, working_capital_balance: parseFloat(e.target.value) || 0 }))}
                className="mt-1"
              />
            </div>
            <div className="border-t pt-4">
              <p className="text-sm font-medium text-red-600 mb-3">DEDUCTIONS</p>
              <div className="space-y-3">
                <div>
                  <Label>Staff Salary (Current Month)</Label>
                  <Input 
                    type="number"
                    value={financeForm.staff_salary_current}
                    onChange={(e) => setFinanceForm(p => ({ ...p, staff_salary_current: parseFloat(e.target.value) || 0 }))}
                  />
                </div>
                <div>
                  <Label>Shop Rental (Current Month)</Label>
                  <Input 
                    type="number"
                    value={financeForm.shop_rental_current}
                    onChange={(e) => setFinanceForm(p => ({ ...p, shop_rental_current: parseFloat(e.target.value) || 0 }))}
                  />
                </div>
                <div>
                  <Label>Vendor Payments</Label>
                  <Input 
                    type="number"
                    value={financeForm.vendor_payments}
                    onChange={(e) => setFinanceForm(p => ({ ...p, vendor_payments: parseFloat(e.target.value) || 0 }))}
                  />
                </div>
                <div>
                  <Label>Utility Bills</Label>
                  <Input 
                    type="number"
                    value={financeForm.utility_bills}
                    onChange={(e) => setFinanceForm(p => ({ ...p, utility_bills: parseFloat(e.target.value) || 0 }))}
                  />
                </div>
                <div>
                  <Label>Other Dues</Label>
                  <Input 
                    type="number"
                    value={financeForm.other_dues}
                    onChange={(e) => setFinanceForm(p => ({ ...p, other_dues: parseFloat(e.target.value) || 0 }))}
                  />
                </div>
              </div>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <p className="text-sm text-green-600">Net Settlement Amount</p>
              <p className={`text-2xl font-bold ${calculateNetSettlement() >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                Rs. {calculateNetSettlement().toLocaleString()}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {calculateNetSettlement() >= 0 ? 'Payable to Franchisee' : 'Owed by Franchisee'}
              </p>
            </div>
            <div>
              <Label>Settlement Notes</Label>
              <Textarea 
                placeholder="Additional notes..."
                value={financeForm.settlement_notes}
                onChange={(e) => setFinanceForm(p => ({ ...p, settlement_notes: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowFinanceModal(false)}>Cancel</Button>
            <Button onClick={handleUpdateFinance} disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Save Settlement
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Signature Modal */}
      <Dialog open={showSignatureModal} onOpenChange={setShowSignatureModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Exit Agreement Signatures</DialogTitle>
            <DialogDescription>Record signatures from all parties for the exit agreement</DialogDescription>
          </DialogHeader>
          <div className="space-y-5 max-h-[60vh] overflow-y-auto pr-1">
            {/* Section 1: Franchisor Signatories */}
            <div className="space-y-3">
              <h4 className="font-semibold text-sm text-gray-700 uppercase tracking-wide border-b pb-1">
                1. Franchisor Signatory (Select one or both)
              </h4>
              <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                <Checkbox 
                  id="sandeep_sign"
                  checked={signatureForm.sandeep_selected}
                  onCheckedChange={(checked) => setSignatureForm(p => ({ ...p, sandeep_selected: checked }))}
                  data-testid="sandeep-checkbox"
                />
                <Label htmlFor="sandeep_sign" className="cursor-pointer flex-1">
                  <span className="font-medium">Sandeep Gadhwal</span>
                  <span className="text-xs text-gray-500 block">Director - Manaswini Foods Pvt. Ltd.</span>
                </Label>
              </div>
              <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                <Checkbox 
                  id="jayanti_sign"
                  checked={signatureForm.jayanti_selected}
                  onCheckedChange={(checked) => setSignatureForm(p => ({ ...p, jayanti_selected: checked }))}
                  data-testid="jayanti-checkbox"
                />
                <Label htmlFor="jayanti_sign" className="cursor-pointer flex-1">
                  <span className="font-medium">Jayanti Kathale</span>
                  <span className="text-xs text-gray-500 block">Director - Manaswini Foods Pvt. Ltd.</span>
                </Label>
              </div>
            </div>

            {/* Section 2: Exit Manager */}
            <div className="space-y-3">
              <h4 className="font-semibold text-sm text-gray-700 uppercase tracking-wide border-b pb-1">
                2. Exit Manager (Franchisor Side)
              </h4>
              <div>
                <Label className="text-xs">Name *</Label>
                <Input 
                  placeholder="e.g., Anirudha Suryavanshi"
                  value={signatureForm.exit_manager_name}
                  onChange={(e) => setSignatureForm(p => ({ ...p, exit_manager_name: e.target.value }))}
                  data-testid="exit-manager-name"
                />
              </div>
              <div>
                <Label className="text-xs">Designation</Label>
                <Input 
                  placeholder="Exit Manager"
                  value={signatureForm.exit_manager_designation}
                  onChange={(e) => setSignatureForm(p => ({ ...p, exit_manager_designation: e.target.value }))}
                  data-testid="exit-manager-designation"
                />
              </div>
            </div>

            {/* Section 3: Franchisee Directors (auto-pulled) */}
            <div className="space-y-3">
              <h4 className="font-semibold text-sm text-gray-700 uppercase tracking-wide border-b pb-1">
                3. Franchisee Directors (Auto-populated from Franchise Management)
              </h4>
              {franchiseDirectors.length > 0 ? (
                <div className="space-y-2">
                  {franchiseDirectors.map((d, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 bg-amber-50 rounded-lg border border-amber-100">
                      <CheckCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="font-medium text-sm">{d.name}</p>
                        <p className="text-xs text-gray-500">{d.designation || 'Director'} {d.email ? `| ${d.email}` : ''}</p>
                      </div>
                    </div>
                  ))}
                  <p className="text-xs text-gray-400">All directors will be signed automatically</p>
                </div>
              ) : (
                <div className="p-4 bg-red-50 rounded-lg text-center">
                  <p className="text-sm text-red-600">No directors found in Franchise Management</p>
                  <p className="text-xs text-gray-500 mt-1">Please add directors in Franchise Management first</p>
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSignatureModal(false)}>Cancel</Button>
            <Button onClick={handleAddSignature} disabled={loading} data-testid="record-all-signatures-btn">
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <FileSignature className="w-4 h-4 mr-2" />}
              Record All Signatures
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Compliance Modal */}
      <Dialog open={showComplianceModal} onOpenChange={setShowComplianceModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Compliance Confirmation</DialogTitle>
            <DialogDescription>Verify all compliance requirements before finalization</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
              <Checkbox 
                id="no_pending_payments"
                checked={complianceForm.no_pending_payments}
                onCheckedChange={(checked) => setComplianceForm(p => ({ ...p, no_pending_payments: checked }))}
              />
              <Label htmlFor="no_pending_payments" className="cursor-pointer">
                No pending payments to vendors, staff, or utilities
              </Label>
            </div>
            <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
              <Checkbox 
                id="brand_assets_transferred"
                checked={complianceForm.brand_assets_transferred}
                onCheckedChange={(checked) => setComplianceForm(p => ({ ...p, brand_assets_transferred: checked }))}
              />
              <Label htmlFor="brand_assets_transferred" className="cursor-pointer">
                Brand assets & digital properties returned to franchisor
              </Label>
            </div>
            <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
              <Checkbox 
                id="financial_report_signed"
                checked={complianceForm.financial_report_signed}
                onCheckedChange={(checked) => setComplianceForm(p => ({ ...p, financial_report_signed: checked }))}
              />
              <Label htmlFor="financial_report_signed" className="cursor-pointer">
                Financial settlement report signed by both parties
              </Label>
            </div>
            <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
              <Checkbox 
                id="handover_report_signed"
                checked={complianceForm.handover_report_signed}
                onCheckedChange={(checked) => setComplianceForm(p => ({ ...p, handover_report_signed: checked }))}
              />
              <Label htmlFor="handover_report_signed" className="cursor-pointer">
                Asset handover report signed by both parties
              </Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowComplianceModal(false)}>Cancel</Button>
            <Button onClick={handleUpdateCompliance} disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Update Compliance
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
