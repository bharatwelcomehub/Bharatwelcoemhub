import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  Building2,
  Plus,
  Search,
  Edit,
  Trash2,
  FileText,
  Upload,
  Download,
  Eye,
  Users,
  Globe,
  Phone,
  Mail,
  MapPin,
  Calendar,
  DollarSign,
  Percent,
  History,
  FileSignature,
  X,
  Loader2,
  ChevronRight,
  AlertCircle
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const COUNTRIES = ["India", "Australia", "United States", "United Kingdom", "Canada", "UAE", "Singapore", "Other"];
const STATUS_OPTIONS = ["Active", "Inactive", "Pending", "Terminated"];
const DOCUMENT_TYPES = ["Agreement", "Legal", "Compliance", "Exit", "Other"];

// FOCO Model Constants
const FRANCHISE_TYPES = {
  "Sanskriti": { fee: 1100000, description: "2500+ Sq. Ft., 20-25 staff, 25-30 tables, 100-120 seating" },
  "Maaza": { fee: 900000, description: "1500-2000 Sq. Ft., 8-9 staff, 6-15 tables, 40-45 seating" },
  "Potoba": { fee: 700000, description: "Express format, smaller footprint" },
  "Peshwayee": { fee: 2500000, description: "Premium fine dining concept" }
};

const DEFAULT_WORKING_CAPITAL = 900000; // 9 Lakhs
const MONTHLY_SERVICE_CONTRACT = 10000;
const REVENUE_SHARE_PERCENTAGE = 15;

const formatCurrency = (amount, country = "India") => {
  if (country === "India") {
    return `₹${(amount || 0).toLocaleString('en-IN')}`;
  }
  return `$${(amount || 0).toLocaleString('en-US')}`;
};

const statusColors = {
  Active: "bg-green-500/20 text-green-400 border-green-500/30",
  Inactive: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  Pending: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  Terminated: "bg-red-500/20 text-red-400 border-red-500/30",
  Deleted: "bg-red-800/20 text-red-600 border-red-800/30"
};

export default function FranchiseManagement() {
  const { session } = useAuth();
  const [activeTab, setActiveTab] = useState("list");
  const [franchises, setFranchises] = useState([]);
  const [loading, setLoading] = useState(false);
  const [counts, setCounts] = useState({ active: 0, pending: 0, terminated: 0, inactive: 0 });
  
  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [filterCountry, setFilterCountry] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  
  // Form state
  const [showForm, setShowForm] = useState(false);
  const [editingFranchise, setEditingFranchise] = useState(null);
  const [formData, setFormData] = useState(getEmptyForm());
  
  // Detail view
  const [selectedFranchise, setSelectedFranchise] = useState(null);
  const [auditHistory, setAuditHistory] = useState([]);
  
  // Document upload
  const [showUpload, setShowUpload] = useState(false);
  const [uploadData, setUploadData] = useState({ document_type: "", document_name: "", notes: "" });
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  function getEmptyForm() {
    return {
      franchise_code: "",
      franchise_name: "",
      legal_entity_name: "",
      country: "India",
      state: "",
      city: "",
      address: "",
      pincode: "",
      primary_contact_name: "",
      primary_contact_email: "",
      primary_contact_phone: "",
      directors: [{ name: "", email: "", phone: "", designation: "Director", address: "", pan: "" }],
      // FOCO Model fields
      franchise_type: "Sanskriti",
      franchise_fee: FRANCHISE_TYPES["Sanskriti"].fee,
      working_capital: DEFAULT_WORKING_CAPITAL,
      total_investment: 0,  // NEW: Total Investment for MG calculation
      setup_costs: {
        shop_security_deposit: 0,
        first_month_rent: 0,
        initial_salary_fund: 0,
        initial_grocery_cost: 0,
        staff_traveling_expense: 0
      },
      operations_start_date: "",
      agreement_start_date: "",
      agreement_end_date: "",
      revenue_share_start_date: "",  // NEW: When revenue share calculation starts
      revenue_share_percentage: REVENUE_SHARE_PERCENTAGE,
      service_contract_fee: MONTHLY_SERVICE_CONTRACT,
      nominees: [],
      status: "Active",
      notes: "",
      gst_applicable: false  // NEW: GST toggle for India locations
    };
  }

  // Auto-calculate agreement end date (7 years from start)
  const calculateEndDate = (startDate) => {
    if (!startDate) return "";
    const start = new Date(startDate);
    const end = new Date(start);
    end.setFullYear(end.getFullYear() + 7);
    return end.toISOString().split('T')[0];
  };

  // Update franchise fee when type changes
  const handleFranchiseTypeChange = (type) => {
    setFormData(prev => ({
      ...prev,
      franchise_type: type,
      franchise_fee: FRANCHISE_TYPES[type]?.fee || 0
    }));
  };

  // Update end date when start date changes
  const handleStartDateChange = (date) => {
    setFormData(prev => ({
      ...prev,
      operations_start_date: date,
      agreement_start_date: date,
      agreement_end_date: calculateEndDate(date)
    }));
  };

  const loadFranchises = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/franchises/list`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: session?.token,
          search: searchQuery || null,
          country: filterCountry && filterCountry !== "all" ? filterCountry : null,
          status: filterStatus && filterStatus !== "all" ? filterStatus : null
        })
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to load franchises");
      }
      
      const data = await res.json();
      setFranchises(data.franchises || []);
      setCounts(data.counts || { active: 0, pending: 0, terminated: 0, inactive: 0 });
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }, [session?.token, searchQuery, filterCountry, filterStatus]);

  useEffect(() => {
    if (session?.token) {
      loadFranchises();
    }
  }, [session?.token, loadFranchises]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.franchise_code || !formData.franchise_name) {
      toast.error("Franchise code and name are required");
      return;
    }
    
    setLoading(true);
    try {
      const endpoint = editingFranchise 
        ? `${API}/api/franchises/update/${editingFranchise.franchise_code}`
        : `${API}/api/franchises/create`;
      
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...formData, token: session?.token })
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save franchise");
      }
      
      toast.success(editingFranchise ? "Franchise updated" : "Franchise created");
      setShowForm(false);
      setEditingFranchise(null);
      setFormData(getEmptyForm());
      loadFranchises();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (franchise) => {
    setEditingFranchise(franchise);
    setFormData({
      ...franchise,
      directors: franchise.directors?.length > 0 ? franchise.directors : [{ name: "", email: "", phone: "", designation: "Director", address: "", pan: "" }],
      franchise_type: franchise.franchise_type || "Sanskriti",
      franchise_fee: franchise.franchise_fee || FRANCHISE_TYPES[franchise.franchise_type || "Sanskriti"]?.fee || 0,
      working_capital: franchise.working_capital || DEFAULT_WORKING_CAPITAL,
      total_investment: franchise.total_investment || 0,
      setup_costs: franchise.setup_costs || { shop_security_deposit: 0, first_month_rent: 0, initial_salary_fund: 0, initial_grocery_cost: 0, staff_traveling_expense: 0 },
      revenue_share_start_date: franchise.revenue_share_start_date || franchise.operations_start_date || "",
      revenue_share_percentage: franchise.revenue_share_percentage || REVENUE_SHARE_PERCENTAGE,
      service_contract_fee: franchise.service_contract_fee || MONTHLY_SERVICE_CONTRACT,
      nominees: franchise.nominees || [],
      gst_applicable: franchise.gst_applicable || false
    });
    setShowForm(true);
  };

  const handleDelete = async (franchise) => {
    if (!window.confirm(`Are you sure you want to delete franchise "${franchise.franchise_code}"?`)) {
      return;
    }
    
    try {
      const res = await fetch(`${API}/api/franchises/delete/${franchise.franchise_code}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: session?.token })
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to delete");
      }
      
      toast.success("Franchise deleted");
      loadFranchises();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const loadFranchiseDetails = async (code) => {
    try {
      const res = await fetch(`${API}/api/franchises/get/${code}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: session?.token })
      });
      
      if (!res.ok) throw new Error("Failed to load details");
      
      const data = await res.json();
      setSelectedFranchise(data.franchise);
      setAuditHistory(data.audit_history || []);
      setActiveTab("detail");
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleDocumentUpload = async (e) => {
    e.preventDefault();
    
    if (!uploadFile || !uploadData.document_type || !uploadData.document_name) {
      toast.error("Please fill all required fields and select a file");
      return;
    }
    
    setUploading(true);
    try {
      const formDataUpload = new FormData();
      formDataUpload.append("token", session?.token);
      formDataUpload.append("franchise_code", selectedFranchise.franchise_code);
      formDataUpload.append("document_type", uploadData.document_type);
      formDataUpload.append("document_name", uploadData.document_name);
      formDataUpload.append("notes", uploadData.notes || "");
      formDataUpload.append("file", uploadFile);
      
      const res = await fetch(`${API}/api/franchises/documents/upload`, {
        method: "POST",
        body: formDataUpload
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }
      
      toast.success("Document uploaded");
      setShowUpload(false);
      setUploadFile(null);
      setUploadData({ document_type: "", document_name: "", notes: "" });
      loadFranchiseDetails(selectedFranchise.franchise_code);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDocumentDelete = async (docId) => {
    if (!window.confirm("Delete this document?")) return;
    
    try {
      const res = await fetch(`${API}/api/franchises/documents/delete/${selectedFranchise.franchise_code}/${docId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: session?.token })
      });
      
      if (!res.ok) throw new Error("Delete failed");
      
      toast.success("Document deleted");
      loadFranchiseDetails(selectedFranchise.franchise_code);
    } catch (err) {
      toast.error(err.message);
    }
  };

  const downloadDocument = (docId) => {
    window.open(`${API}/api/franchises/documents/download/${selectedFranchise.franchise_code}/${docId}?token=${session?.token}`, "_blank");
  };

  const generateAgreement = async () => {
    try {
      toast.loading("Generating FOCO Agreement...", { id: "gen-agreement" });
      const res = await fetch(`${API}/api/franchises/generate-agreement/${selectedFranchise.franchise_code}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: session?.token, format: "pdf" })
      });
      
      if (!res.ok) throw new Error("Failed to generate agreement");
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `FOCO_Agreement_${selectedFranchise.franchise_code}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      
      toast.success("Agreement generated", { id: "gen-agreement" });
    } catch (err) {
      toast.error(err.message, { id: "gen-agreement" });
    }
  };

  const addDirector = () => {
    setFormData(prev => ({
      ...prev,
      directors: [...prev.directors, { name: "", email: "", phone: "", designation: "Director", address: "", pan: "" }]
    }));
  };

  const removeDirector = (index) => {
    setFormData(prev => ({
      ...prev,
      directors: prev.directors.filter((_, i) => i !== index)
    }));
  };

  const updateDirector = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      directors: prev.directors.map((d, i) => i === index ? { ...d, [field]: value } : d)
    }));
  };

  // Access check
  const isSuperAdmin = session?.is_super_admin;
  const isAdmin = session?.is_admin;
  const hasAccounting = session?.roles?.accounting;
  
  if (!isSuperAdmin && !isAdmin && !hasAccounting) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">Access Denied</h2>
        <p className="text-muted-foreground">Only Admin or Accounts users can access Franchise Management.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="franchise-management">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Building2 className="w-6 h-6 text-secondary" />
            Franchise Management
          </h1>
          <p className="text-muted-foreground mt-1">Manage franchise records, documents, and agreements</p>
        </div>
        <Button 
          onClick={() => { setShowForm(true); setEditingFranchise(null); setFormData(getEmptyForm()); }}
          className="bg-secondary hover:bg-secondary/90"
          data-testid="add-franchise-btn"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Franchise
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-card border-border">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total</p>
                <p className="text-2xl font-bold text-white">{franchises.length}</p>
              </div>
              <Building2 className="w-8 h-8 text-secondary" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card border-border">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active</p>
                <p className="text-2xl font-bold text-green-400">{counts.active}</p>
              </div>
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card border-border">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pending</p>
                <p className="text-2xl font-bold text-yellow-400">{counts.pending}</p>
              </div>
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card border-border">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Terminated</p>
                <p className="text-2xl font-bold text-red-400">{counts.terminated}</p>
              </div>
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-card border border-border">
          <TabsTrigger value="list" data-testid="tab-list">Franchise List</TabsTrigger>
          {selectedFranchise && <TabsTrigger value="detail" data-testid="tab-detail">Details</TabsTrigger>}
        </TabsList>

        {/* List Tab */}
        <TabsContent value="list" className="space-y-4">
          {/* Filters */}
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search by code, name, city..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-card border-border"
                  data-testid="search-input"
                />
              </div>
            </div>
            <Select value={filterCountry} onValueChange={setFilterCountry}>
              <SelectTrigger className="w-[150px] bg-card border-border">
                <SelectValue placeholder="Country" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Countries</SelectItem>
                {COUNTRIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[130px] bg-card border-border">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                {STATUS_OPTIONS.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={loadFranchises} disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Refresh"}
            </Button>
          </div>

          {/* Table */}
          <Card className="bg-card border-border">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="border-border hover:bg-transparent">
                    <TableHead>Code</TableHead>
                    <TableHead>Franchise Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Country</TableHead>
                    <TableHead>Fee</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8">
                        <Loader2 className="w-6 h-6 animate-spin mx-auto text-secondary" />
                      </TableCell>
                    </TableRow>
                  ) : franchises.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                        No franchises found. Click "Add Franchise" to create one.
                      </TableCell>
                    </TableRow>
                  ) : (
                    franchises.map((f) => (
                      <TableRow 
                        key={f.franchise_code} 
                        className="border-border cursor-pointer hover:bg-white/5"
                        onClick={() => loadFranchiseDetails(f.franchise_code)}
                        data-testid={`franchise-row-${f.franchise_code}`}
                      >
                        <TableCell className="font-mono font-semibold text-secondary">
                          {f.franchise_code}
                        </TableCell>
                        <TableCell>
                          <div>
                            <p className="font-medium text-white">{f.franchise_name}</p>
                            <p className="text-xs text-muted-foreground">{f.city}, {f.country}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">
                            {f.franchise_type || "Sanskriti"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Globe className="w-3 h-3 text-muted-foreground" />
                            {f.country}
                          </div>
                        </TableCell>
                        <TableCell className="text-sm">
                          {formatCurrency(f.franchise_fee, f.country)}
                        </TableCell>
                        <TableCell>
                          <Badge className={statusColors[f.status] || statusColors.Inactive}>
                            {f.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button 
                              size="icon" 
                              variant="ghost"
                              onClick={(e) => { e.stopPropagation(); handleEdit(f); }}
                              data-testid={`edit-btn-${f.franchise_code}`}
                            >
                              <Edit className="w-4 h-4" />
                            </Button>
                            {isSuperAdmin && (
                              <Button 
                                size="icon" 
                                variant="ghost"
                                className="text-red-500 hover:text-red-400"
                                onClick={(e) => { e.stopPropagation(); handleDelete(f); }}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            )}
                            <ChevronRight className="w-4 h-4 text-muted-foreground" />
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Detail Tab */}
        <TabsContent value="detail" className="space-y-4">
          {selectedFranchise && (
            <>
              {/* Franchise Header */}
              <Card className="bg-card border-border">
                <CardHeader className="flex flex-row items-start justify-between">
                  <div>
                    <CardTitle className="text-xl text-white flex items-center gap-2">
                      <Building2 className="w-5 h-5 text-secondary" />
                      {selectedFranchise.franchise_name}
                    </CardTitle>
                    <p className="text-muted-foreground mt-1">{selectedFranchise.legal_entity_name}</p>
                    <Badge className={`mt-2 ${statusColors[selectedFranchise.status]}`}>
                      {selectedFranchise.status}
                    </Badge>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" onClick={() => handleEdit(selectedFranchise)}>
                      <Edit className="w-4 h-4 mr-2" />
                      Edit
                    </Button>
                    <Button onClick={generateAgreement} className="bg-secondary hover:bg-secondary/90">
                      <FileSignature className="w-4 h-4 mr-2" />
                      Generate Agreement
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Location */}
                    <div className="space-y-3">
                      <h3 className="font-semibold text-white flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-secondary" />
                        Location
                      </h3>
                      <div className="space-y-1 text-sm">
                        <p><span className="text-muted-foreground">Code:</span> <span className="font-mono text-secondary">{selectedFranchise.franchise_code}</span></p>
                        <p><span className="text-muted-foreground">Country:</span> {selectedFranchise.country}</p>
                        <p><span className="text-muted-foreground">State:</span> {selectedFranchise.state || "-"}</p>
                        <p><span className="text-muted-foreground">City:</span> {selectedFranchise.city || "-"}</p>
                        <p><span className="text-muted-foreground">Address:</span> {selectedFranchise.address || "-"}</p>
                        <p><span className="text-muted-foreground">Pincode:</span> {selectedFranchise.pincode || "-"}</p>
                      </div>
                    </div>

                    {/* Contact */}
                    <div className="space-y-3">
                      <h3 className="font-semibold text-white flex items-center gap-2">
                        <Phone className="w-4 h-4 text-secondary" />
                        Primary Contact
                      </h3>
                      <div className="space-y-1 text-sm">
                        <p><span className="text-muted-foreground">Name:</span> {selectedFranchise.primary_contact_name || "-"}</p>
                        <p className="flex items-center gap-1">
                          <Mail className="w-3 h-3 text-muted-foreground" />
                          {selectedFranchise.primary_contact_email || "-"}
                        </p>
                        <p className="flex items-center gap-1">
                          <Phone className="w-3 h-3 text-muted-foreground" />
                          {selectedFranchise.primary_contact_phone || "-"}
                        </p>
                      </div>
                    </div>

                    {/* Agreement */}
                    <div className="space-y-3">
                      <h3 className="font-semibold text-white flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-secondary" />
                        FOCO Agreement
                      </h3>
                      <div className="space-y-1 text-sm">
                        <p><span className="text-muted-foreground">Type:</span> <span className="text-secondary font-medium">{selectedFranchise.franchise_type || "Sanskriti"}</span></p>
                        <p><span className="text-muted-foreground">Start:</span> {selectedFranchise.operations_start_date || selectedFranchise.agreement_start_date || "-"}</p>
                        <p><span className="text-muted-foreground">End:</span> {selectedFranchise.agreement_end_date || "-"} <span className="text-xs text-muted-foreground">(7 years)</span></p>
                        <p className="flex items-center gap-1">
                          <DollarSign className="w-3 h-3 text-muted-foreground" />
                          Fee: {formatCurrency(selectedFranchise.franchise_fee, selectedFranchise.country)}
                        </p>
                        <p className="flex items-center gap-1">
                          <Percent className="w-3 h-3 text-muted-foreground" />
                          Revenue Share: {selectedFranchise.revenue_share_percentage || 15}%
                        </p>
                        <p><span className="text-muted-foreground">Working Capital:</span> {formatCurrency(selectedFranchise.working_capital, selectedFranchise.country)}</p>
                        <p><span className="text-muted-foreground">Service Fee:</span> {formatCurrency(selectedFranchise.service_contract_fee || 10000, selectedFranchise.country)}/month</p>
                      </div>
                    </div>
                  </div>

                  {/* FOCO Model Info Banner */}
                  <div className="mt-4 p-3 rounded-lg bg-secondary/10 border border-secondary/30">
                    <p className="text-sm text-secondary font-medium">FOCO Model: Franchise Owned - Company Operated</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Franchise Owner invests capital. Purnabramha manages all operations including menu, staff, procurement, and accounting.
                    </p>
                  </div>

                  {/* Directors */}
                  {selectedFranchise.directors?.length > 0 && (
                    <div className="mt-6">
                      <h3 className="font-semibold text-white flex items-center gap-2 mb-3">
                        <Users className="w-4 h-4 text-secondary" />
                        Directors
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {selectedFranchise.directors.map((d, i) => (
                          <div key={i} className="p-3 rounded-lg bg-white/5 border border-border">
                            <p className="font-medium text-white">{d.name || "N/A"}</p>
                            <p className="text-sm text-muted-foreground">{d.designation || "Director"}</p>
                            <p className="text-sm">{d.email}</p>
                            <p className="text-sm">{d.phone}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Notes */}
                  {selectedFranchise.notes && (
                    <div className="mt-6">
                      <h3 className="font-semibold text-white mb-2">Notes</h3>
                      <p className="text-sm text-muted-foreground">{selectedFranchise.notes}</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Documents Section */}
              <Card className="bg-card border-border">
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-lg text-white flex items-center gap-2">
                    <FileText className="w-5 h-5 text-secondary" />
                    Documents
                  </CardTitle>
                  <Button onClick={() => setShowUpload(true)} size="sm">
                    <Upload className="w-4 h-4 mr-2" />
                    Upload Document
                  </Button>
                </CardHeader>
                <CardContent>
                  {selectedFranchise.documents?.length > 0 ? (
                    <Table>
                      <TableHeader>
                        <TableRow className="border-border">
                          <TableHead>Name</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead>Uploaded</TableHead>
                          <TableHead>By</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedFranchise.documents.map((doc) => (
                          <TableRow key={doc.document_id} className="border-border">
                            <TableCell>
                              <div>
                                <p className="font-medium">{doc.document_name}</p>
                                <p className="text-xs text-muted-foreground">{doc.original_name}</p>
                              </div>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">{doc.document_type}</Badge>
                            </TableCell>
                            <TableCell className="text-sm">
                              {new Date(doc.uploaded_at).toLocaleDateString()}
                            </TableCell>
                            <TableCell className="text-sm text-muted-foreground">
                              {doc.uploaded_by}
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex items-center justify-end gap-1">
                                <Button 
                                  size="icon" 
                                  variant="ghost"
                                  onClick={() => downloadDocument(doc.document_id)}
                                >
                                  <Download className="w-4 h-4" />
                                </Button>
                                <Button 
                                  size="icon" 
                                  variant="ghost"
                                  className="text-red-500"
                                  onClick={() => handleDocumentDelete(doc.document_id)}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <p className="text-center text-muted-foreground py-8">No documents uploaded yet.</p>
                  )}
                </CardContent>
              </Card>

              {/* Audit History */}
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle className="text-lg text-white flex items-center gap-2">
                    <History className="w-5 h-5 text-secondary" />
                    Audit History
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {auditHistory.length > 0 ? (
                    <div className="space-y-3 max-h-[300px] overflow-y-auto">
                      {auditHistory.map((entry, i) => (
                        <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-white/5">
                          <div className="w-2 h-2 rounded-full bg-secondary mt-2"></div>
                          <div className="flex-1">
                            <div className="flex items-center justify-between">
                              <p className="font-medium text-white">{entry.action}</p>
                              <p className="text-xs text-muted-foreground">
                                {new Date(entry.timestamp).toLocaleString()}
                              </p>
                            </div>
                            <p className="text-sm text-muted-foreground">by {entry.performed_by}</p>
                            {entry.details && (
                              <pre className="text-xs mt-1 text-muted-foreground overflow-x-auto">
                                {JSON.stringify(entry.details, null, 2)}
                              </pre>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-muted-foreground py-4">No audit history available.</p>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>
      </Tabs>

      {/* Create/Edit Dialog */}
      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto bg-card border-border">
          <DialogHeader>
            <DialogTitle className="text-xl text-white">
              {editingFranchise ? "Edit Franchise" : "Add New Franchise"}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Info */}
            <div className="space-y-4">
              <h3 className="font-semibold text-white border-b border-border pb-2">Basic Information</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Franchise Code *</Label>
                  <Input
                    value={formData.franchise_code}
                    onChange={(e) => setFormData(p => ({ ...p, franchise_code: e.target.value.toUpperCase() }))}
                    placeholder="FR-001"
                    disabled={!!editingFranchise}
                    className="bg-background"
                    data-testid="input-franchise-code"
                  />
                </div>
                <div>
                  <Label>Status</Label>
                  <Select value={formData.status} onValueChange={(v) => setFormData(p => ({ ...p, status: v }))}>
                    <SelectTrigger className="bg-background">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {STATUS_OPTIONS.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="col-span-2">
                  <Label>Franchise Name *</Label>
                  <Input
                    value={formData.franchise_name}
                    onChange={(e) => setFormData(p => ({ ...p, franchise_name: e.target.value }))}
                    placeholder="Purnabramha Perth"
                    className="bg-background"
                    data-testid="input-franchise-name"
                  />
                </div>
                <div className="col-span-2">
                  <Label>Legal Entity Name</Label>
                  <Input
                    value={formData.legal_entity_name}
                    onChange={(e) => setFormData(p => ({ ...p, legal_entity_name: e.target.value }))}
                    placeholder="ABC Foods Pvt Ltd"
                    className="bg-background"
                  />
                </div>
              </div>
            </div>

            {/* Location */}
            <div className="space-y-4">
              <h3 className="font-semibold text-white border-b border-border pb-2">Location</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Country</Label>
                  <Select value={formData.country} onValueChange={(v) => setFormData(p => ({ ...p, country: v }))}>
                    <SelectTrigger className="bg-background">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {COUNTRIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>State/Province</Label>
                  <Input
                    value={formData.state}
                    onChange={(e) => setFormData(p => ({ ...p, state: e.target.value }))}
                    className="bg-background"
                  />
                </div>
                <div>
                  <Label>City</Label>
                  <Input
                    value={formData.city}
                    onChange={(e) => setFormData(p => ({ ...p, city: e.target.value }))}
                    className="bg-background"
                  />
                </div>
                <div>
                  <Label>Pincode/ZIP</Label>
                  <Input
                    value={formData.pincode}
                    onChange={(e) => setFormData(p => ({ ...p, pincode: e.target.value }))}
                    className="bg-background"
                  />
                </div>
                <div className="col-span-2">
                  <Label>Address</Label>
                  <Textarea
                    value={formData.address}
                    onChange={(e) => setFormData(p => ({ ...p, address: e.target.value }))}
                    className="bg-background"
                    rows={2}
                  />
                </div>
              </div>
            </div>

            {/* Contact */}
            <div className="space-y-4">
              <h3 className="font-semibold text-white border-b border-border pb-2">Primary Contact</h3>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label>Contact Name</Label>
                  <Input
                    value={formData.primary_contact_name}
                    onChange={(e) => setFormData(p => ({ ...p, primary_contact_name: e.target.value }))}
                    className="bg-background"
                  />
                </div>
                <div>
                  <Label>Email</Label>
                  <Input
                    type="email"
                    value={formData.primary_contact_email}
                    onChange={(e) => setFormData(p => ({ ...p, primary_contact_email: e.target.value }))}
                    className="bg-background"
                  />
                </div>
                <div>
                  <Label>Phone</Label>
                  <Input
                    value={formData.primary_contact_phone}
                    onChange={(e) => setFormData(p => ({ ...p, primary_contact_phone: e.target.value }))}
                    className="bg-background"
                  />
                </div>
              </div>
            </div>

            {/* Directors */}
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <h3 className="font-semibold text-white">Directors</h3>
                <Button type="button" variant="outline" size="sm" onClick={addDirector}>
                  <Plus className="w-4 h-4 mr-1" />
                  Add Director
                </Button>
              </div>
              {formData.directors.map((d, i) => (
                <div key={i} className="p-4 rounded-lg bg-white/5 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-muted-foreground">Director {i + 1}</span>
                    {formData.directors.length > 1 && (
                      <Button type="button" variant="ghost" size="icon" onClick={() => removeDirector(i)}>
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <Input
                      placeholder="Name"
                      value={d.name}
                      onChange={(e) => updateDirector(i, "name", e.target.value)}
                      className="bg-background"
                    />
                    <Input
                      placeholder="Designation"
                      value={d.designation}
                      onChange={(e) => updateDirector(i, "designation", e.target.value)}
                      className="bg-background"
                    />
                    <Input
                      placeholder="Email"
                      value={d.email}
                      onChange={(e) => updateDirector(i, "email", e.target.value)}
                      className="bg-background"
                    />
                    <Input
                      placeholder="Phone"
                      value={d.phone}
                      onChange={(e) => updateDirector(i, "phone", e.target.value)}
                      className="bg-background"
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* FOCO Model - Franchise Type */}
            <div className="space-y-4">
              <h3 className="font-semibold text-white border-b border-border pb-2">FOCO Model - Franchise Type</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Franchise Type *</Label>
                  <Select value={formData.franchise_type} onValueChange={handleFranchiseTypeChange}>
                    <SelectTrigger className="bg-background">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(FRANCHISE_TYPES).map(([type, info]) => (
                        <SelectItem key={type} value={type}>
                          {type} - {formatCurrency(info.fee, formData.country)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground mt-1">
                    {FRANCHISE_TYPES[formData.franchise_type]?.description}
                  </p>
                </div>
                <div>
                  <Label>Franchise Fee (Non-Refundable)</Label>
                  <Input
                    type="number"
                    value={formData.franchise_fee}
                    onChange={(e) => setFormData(p => ({ ...p, franchise_fee: parseFloat(e.target.value) || 0 }))}
                    className="bg-background"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {formatCurrency(formData.franchise_fee, formData.country)}
                  </p>
                </div>
                <div>
                  <Label>Working Capital</Label>
                  <Input
                    type="number"
                    value={formData.working_capital}
                    onChange={(e) => setFormData(p => ({ ...p, working_capital: parseFloat(e.target.value) || 0 }))}
                    className="bg-background"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Default: {formatCurrency(DEFAULT_WORKING_CAPITAL, formData.country)}
                  </p>
                </div>
                <div>
                  <Label>Revenue Share % (to Franchise Owner)</Label>
                  <Input
                    type="number"
                    step="0.1"
                    value={formData.revenue_share_percentage}
                    onChange={(e) => setFormData(p => ({ ...p, revenue_share_percentage: parseFloat(e.target.value) || 15 }))}
                    className="bg-background"
                  />
                </div>
              </div>
            </div>

            {/* Total Investment for MG Calculation */}
            <div className="space-y-4">
              <h3 className="font-semibold text-white border-b border-border pb-2">Total Investment (for MG Calculation)</h3>
              <div className="grid grid-cols-1 gap-4">
                <div className="p-4 bg-purple-900/30 border border-purple-500/30 rounded-lg">
                  <Label className="text-purple-200">Total Investment Done *</Label>
                  <Input
                    type="number"
                    value={formData.total_investment || 0}
                    onChange={(e) => setFormData(p => ({ ...p, total_investment: parseFloat(e.target.value) || 0 }))}
                    className="bg-background mt-2 text-lg font-bold"
                    placeholder="Enter total investment amount"
                    data-testid="total-investment-input"
                  />
                  <p className="text-xs text-purple-300 mt-2">
                    This is the actual total investment amount. All deductions below (including Franchise Fee & Working Capital) will be subtracted to calculate Net Investment for MG.
                  </p>
                  {formData.total_investment > 0 && (
                    <div className="mt-3 p-3 bg-background/50 rounded text-sm space-y-1">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Total Investment:</span>
                        <span className="font-medium">{formatCurrency(formData.total_investment, formData.country)}</span>
                      </div>
                      <div className="text-xs text-muted-foreground mt-2 mb-1">Deductions:</div>
                      <div className="flex justify-between text-red-400 text-xs pl-2">
                        <span>- Shop Rent Deposit:</span>
                        <span>-{formatCurrency(formData.setup_costs?.shop_security_deposit || 0, formData.country)}</span>
                      </div>
                      <div className="flex justify-between text-red-400 text-xs pl-2">
                        <span>- First Month Rent:</span>
                        <span>-{formatCurrency(formData.setup_costs?.first_month_rent || 0, formData.country)}</span>
                      </div>
                      <div className="flex justify-between text-red-400 text-xs pl-2">
                        <span>- Initial Salary Fund:</span>
                        <span>-{formatCurrency(formData.setup_costs?.initial_salary_fund || 0, formData.country)}</span>
                      </div>
                      <div className="flex justify-between text-red-400 text-xs pl-2">
                        <span>- Staff Travel Expense:</span>
                        <span>-{formatCurrency(formData.setup_costs?.staff_traveling_expense || 0, formData.country)}</span>
                      </div>
                      <div className="flex justify-between text-red-400 text-xs pl-2">
                        <span>- Franchise Fee:</span>
                        <span>-{formatCurrency(formData.franchise_fee || 0, formData.country)}</span>
                      </div>
                      <div className="flex justify-between text-red-400 text-xs pl-2">
                        <span>- Working Capital:</span>
                        <span>-{formatCurrency(formData.working_capital || 0, formData.country)}</span>
                      </div>
                      <div className="flex justify-between text-red-400 font-medium border-t border-border/50 pt-1 mt-1">
                        <span>Total Deductions:</span>
                        <span>-{formatCurrency(
                          (formData.setup_costs?.shop_security_deposit || 0) +
                          (formData.setup_costs?.first_month_rent || 0) +
                          (formData.setup_costs?.initial_salary_fund || 0) +
                          (formData.setup_costs?.staff_traveling_expense || 0) +
                          (formData.franchise_fee || 0) +
                          (formData.working_capital || 0),
                          formData.country
                        )}</span>
                      </div>
                      <div className="flex justify-between font-bold text-green-400 border-t-2 border-green-500/50 pt-2 mt-2 text-base">
                        <span>Net Investment:</span>
                        <span>{formatCurrency(
                          Math.max(0, (formData.total_investment || 0) -
                            (formData.setup_costs?.shop_security_deposit || 0) -
                            (formData.setup_costs?.first_month_rent || 0) -
                            (formData.setup_costs?.initial_salary_fund || 0) -
                            (formData.setup_costs?.staff_traveling_expense || 0) -
                            (formData.franchise_fee || 0) -
                            (formData.working_capital || 0)),
                          formData.country
                        )}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Setup Costs */}
            <div className="space-y-4">
              <h3 className="font-semibold text-white border-b border-border pb-2">Setup Costs (Before Operations)</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Shop Security Deposit</Label>
                  <Input
                    type="number"
                    value={formData.setup_costs?.shop_security_deposit || 0}
                    onChange={(e) => setFormData(p => ({ 
                      ...p, 
                      setup_costs: { ...p.setup_costs, shop_security_deposit: parseFloat(e.target.value) || 0 }
                    }))}
                    className="bg-background"
                  />
                </div>
                <div>
                  <Label>First Month Rent</Label>
                  <Input
                    type="number"
                    value={formData.setup_costs?.first_month_rent || 0}
                    onChange={(e) => setFormData(p => ({ 
                      ...p, 
                      setup_costs: { ...p.setup_costs, first_month_rent: parseFloat(e.target.value) || 0 }
                    }))}
                    className="bg-background"
                  />
                </div>
                <div>
                  <Label>Initial Salary Fund</Label>
                  <Input
                    type="number"
                    value={formData.setup_costs?.initial_salary_fund || 0}
                    onChange={(e) => setFormData(p => ({ 
                      ...p, 
                      setup_costs: { ...p.setup_costs, initial_salary_fund: parseFloat(e.target.value) || 0 }
                    }))}
                    className="bg-background"
                  />
                </div>
                <div>
                  <Label>Initial Grocery Cost</Label>
                  <Input
                    type="number"
                    value={formData.setup_costs?.initial_grocery_cost || 0}
                    onChange={(e) => setFormData(p => ({ 
                      ...p, 
                      setup_costs: { ...p.setup_costs, initial_grocery_cost: parseFloat(e.target.value) || 0 }
                    }))}
                    className="bg-background"
                  />
                </div>
                <div>
                  <Label>Staff Traveling Expense</Label>
                  <Input
                    type="number"
                    value={formData.setup_costs?.staff_traveling_expense || 0}
                    onChange={(e) => setFormData(p => ({ 
                      ...p, 
                      setup_costs: { ...p.setup_costs, staff_traveling_expense: parseFloat(e.target.value) || 0 }
                    }))}
                    className="bg-background"
                    data-testid="input-staff-travel"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Used for MG (Minimum Guarantee) calculation
                  </p>
                </div>
              </div>
            </div>

            {/* Agreement Dates */}
            <div className="space-y-4">
              <h3 className="font-semibold text-white border-b border-border pb-2">Agreement Dates (Tenure: 7 Years Fixed)</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Operations Start Date</Label>
                  <Input
                    type="date"
                    value={formData.operations_start_date}
                    onChange={(e) => handleStartDateChange(e.target.value)}
                    className="bg-background"
                  />
                </div>
                <div>
                  <Label>Agreement End Date (Auto-calculated)</Label>
                  <Input
                    type="date"
                    value={formData.agreement_end_date}
                    disabled
                    className="bg-background opacity-70"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    7 years from start date (fixed tenure)
                  </p>
                </div>
                <div>
                  <Label>Revenue Share Start Date *</Label>
                  <Input
                    type="date"
                    value={formData.revenue_share_start_date || formData.operations_start_date}
                    onChange={(e) => setFormData(p => ({ ...p, revenue_share_start_date: e.target.value }))}
                    className="bg-background"
                    data-testid="revenue-share-start-date"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Date from which payout calculations start (defaults to Operations Start)
                  </p>
                </div>
                <div>
                  <Label>Monthly Service Contract Fee</Label>
                  <Input
                    type="number"
                    value={formData.service_contract_fee}
                    onChange={(e) => setFormData(p => ({ ...p, service_contract_fee: parseFloat(e.target.value) || 10000 }))}
                    className="bg-background"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Default: {formatCurrency(MONTHLY_SERVICE_CONTRACT, formData.country)}/month
                  </p>
                </div>
              </div>
            </div>

            {/* GST Settings (India Only) */}
            {formData.country === "India" && (
              <div className="space-y-4">
                <h3 className="font-semibold text-white border-b border-border pb-2">GST Settings (India Only)</h3>
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/5 border border-border">
                  <div>
                    <Label className="text-base">GST Applicable on Revenue Share</Label>
                    <p className="text-sm text-muted-foreground mt-1">
                      When enabled, 18% GST (9% CGST + 9% SGST) will be applied to the revenue share payable.
                    </p>
                  </div>
                  <Switch
                    checked={formData.gst_applicable || false}
                    onCheckedChange={(checked) => setFormData(p => ({ ...p, gst_applicable: checked }))}
                    data-testid="gst-applicable-switch"
                  />
                </div>
              </div>
            )}

            {/* Notes */}
            <div>
              <Label>Notes</Label>
              <Textarea
                value={formData.notes}
                onChange={(e) => setFormData(p => ({ ...p, notes: e.target.value }))}
                className="bg-background"
                rows={3}
              />
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={loading} className="bg-secondary hover:bg-secondary/90">
                {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                {editingFranchise ? "Update" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Document Upload Dialog */}
      <Dialog open={showUpload} onOpenChange={setShowUpload}>
        <DialogContent className="bg-card border-border">
          <DialogHeader>
            <DialogTitle className="text-white">Upload Document</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleDocumentUpload} className="space-y-4">
            <div>
              <Label>Document Type *</Label>
              <Select 
                value={uploadData.document_type} 
                onValueChange={(v) => setUploadData(p => ({ ...p, document_type: v }))}
              >
                <SelectTrigger className="bg-background">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {DOCUMENT_TYPES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Document Name *</Label>
              <Input
                value={uploadData.document_name}
                onChange={(e) => setUploadData(p => ({ ...p, document_name: e.target.value }))}
                placeholder="e.g., Franchise Agreement 2024"
                className="bg-background"
              />
            </div>
            <div>
              <Label>Notes</Label>
              <Textarea
                value={uploadData.notes}
                onChange={(e) => setUploadData(p => ({ ...p, notes: e.target.value }))}
                className="bg-background"
                rows={2}
              />
            </div>
            <div>
              <Label>File *</Label>
              <Input
                type="file"
                accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.xlsx,.xls"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                className="bg-background"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Allowed: PDF, DOC, DOCX, JPG, PNG, XLS, XLSX
              </p>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowUpload(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={uploading}>
                {uploading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Upload
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
