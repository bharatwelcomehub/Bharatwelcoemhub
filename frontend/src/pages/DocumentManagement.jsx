import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Card, CardContent, CardHeader, CardTitle,
} from "@/components/ui/card";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import {
  FileText, Upload, CheckCircle2, XCircle, Clock, AlertTriangle,
  Eye, Download, Trash2, Plus, RefreshCw, Loader2, Filter,
  Building2, Users, ShieldCheck, CalendarClock, Search, FolderOpen,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const STATUS_STYLES = {
  pending: { bg: "bg-amber-100 text-amber-800 border-amber-300", icon: Clock },
  approved: { bg: "bg-green-100 text-green-800 border-green-300", icon: CheckCircle2 },
  rejected: { bg: "bg-red-100 text-red-800 border-red-300", icon: XCircle },
};

export default function DocumentManagement() {
  const { session } = useAuth();
  const [tab, setTab] = useState("documents");
  const [loading, setLoading] = useState(false);
  const [centers, setCenters] = useState([]);
  const [categories, setCategories] = useState([]);

  // Document list state
  const [documents, setDocuments] = useState([]);
  const [filterCenter, setFilterCenter] = useState("");
  const [filterLevel, setFilterLevel] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  // Upload dialog
  const [showUpload, setShowUpload] = useState(false);
  const [uploadForm, setUploadForm] = useState({
    center: "", category_id: "", level: "franchise", expiry_date: "",
    employee_name: "", franchise_code: "", notes: "",
  });
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Action dialog
  const [showAction, setShowAction] = useState(false);
  const [actionDoc, setActionDoc] = useState(null);
  const [actionType, setActionType] = useState("");
  const [actionNotes, setActionNotes] = useState("");

  // Category dialog
  const [showCategoryDialog, setShowCategoryDialog] = useState(false);
  const [catForm, setCatForm] = useState({ name: "", level: "franchise", requires_expiry: false, description: "" });

  // Expiry alerts
  const [expiryData, setExpiryData] = useState(null);

  // Stats
  const [stats, setStats] = useState(null);

  const isAdmin = session?.is_super_admin || session?.is_admin;

  useEffect(() => {
    const init = async () => {
      try {
        const [centersRes, catsRes] = await Promise.all([
          api.get("/centers"),
          api.post("/documents/categories/list", { token: session?.token }),
        ]);
        setCenters((centersRes.data.centers || []).filter(c => c.active !== false));
        setCategories(catsRes.data.categories || []);
      } catch {}
    };
    if (session?.token) init();
  }, [session?.token]);

  const loadDocuments = useCallback(async () => {
    if (!session?.token) return;
    setLoading(true);
    try {
      const params = { token: session.token };
      if (filterCenter) params.center = filterCenter;
      if (filterLevel) params.level = filterLevel;
      if (filterCategory) params.category = filterCategory;
      if (filterStatus) params.status = filterStatus;
      const res = await api.post("/documents/list", params);
      setDocuments(res.data.documents || []);
    } catch { toast.error("Failed to load documents"); }
    setLoading(false);
  }, [session?.token, filterCenter, filterLevel, filterCategory, filterStatus]);

  const loadStats = useCallback(async () => {
    if (!session?.token) return;
    try {
      const res = await api.post("/documents/stats", { token: session.token });
      setStats(res.data.stats);
    } catch {}
  }, [session?.token]);

  const loadExpiry = useCallback(async () => {
    if (!session?.token) return;
    try {
      const res = await api.post("/documents/expiring", { token: session.token, days: 60 });
      setExpiryData(res.data);
    } catch {}
  }, [session?.token]);

  useEffect(() => {
    loadDocuments();
    loadStats();
  }, [loadDocuments, loadStats]);

  useEffect(() => {
    if (tab === "expiry") loadExpiry();
  }, [tab, loadExpiry]);

  // Upload handler
  const handleUpload = async () => {
    if (!uploadFile) { toast.error("Select a file"); return; }
    if (!uploadForm.center) { toast.error("Select a center"); return; }
    if (!uploadForm.category_id) { toast.error("Select a category"); return; }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("token", session.token);
      formData.append("center", uploadForm.center);
      formData.append("category_id", uploadForm.category_id);
      formData.append("level", uploadForm.level);
      formData.append("expiry_date", uploadForm.expiry_date || "");
      formData.append("employee_name", uploadForm.employee_name || "");
      formData.append("franchise_code", uploadForm.franchise_code || "");
      formData.append("notes", uploadForm.notes || "");
      formData.append("file", uploadFile);

      await fetch(`${API}/api/documents/upload`, { method: "POST", body: formData });
      toast.success("Document uploaded successfully");
      setShowUpload(false);
      setUploadFile(null);
      setUploadForm({ center: "", category_id: "", level: "franchise", expiry_date: "", employee_name: "", franchise_code: "", notes: "" });
      loadDocuments();
      loadStats();
    } catch { toast.error("Upload failed"); }
    setUploading(false);
  };

  // Approve/Reject
  const handleAction = async () => {
    if (!actionDoc) return;
    try {
      await api.post("/documents/action", {
        token: session.token,
        document_id: actionDoc.document_id,
        action: actionType,
        notes: actionNotes,
      });
      toast.success(`Document ${actionType}d`);
      setShowAction(false);
      setActionDoc(null);
      setActionNotes("");
      loadDocuments();
      loadStats();
    } catch { toast.error("Action failed"); }
  };

  // Download
  const handleDownload = async (doc) => {
    try {
      const res = await fetch(`${API}/api/documents/file/${doc.document_id}?auth=${session.token}`);
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.original_filename || "document";
      a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error("Download failed"); }
  };

  // Delete
  const handleDelete = async (docId) => {
    if (!window.confirm("Delete this document?")) return;
    try {
      await api.post("/documents/delete", { token: session.token, document_id: docId });
      toast.success("Document deleted");
      loadDocuments();
      loadStats();
    } catch { toast.error("Delete failed"); }
  };

  // Category create
  const handleCreateCategory = async () => {
    if (!catForm.name) { toast.error("Enter category name"); return; }
    try {
      await api.post("/documents/categories/create", { token: session.token, ...catForm });
      toast.success("Category created");
      setShowCategoryDialog(false);
      setCatForm({ name: "", level: "franchise", requires_expiry: false, description: "" });
      const catsRes = await api.post("/documents/categories/list", { token: session.token });
      setCategories(catsRes.data.categories || []);
    } catch { toast.error("Failed to create category"); }
  };

  const formatDate = (d) => d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "-";
  const isExpired = (d) => d && new Date(d) < new Date();
  const isExpiringSoon = (d) => {
    if (!d) return false;
    const diff = (new Date(d) - new Date()) / (1000 * 60 * 60 * 24);
    return diff >= 0 && diff <= 30;
  };

  return (
    <div className="p-4 md:p-6 space-y-6" data-testid="document-management-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[#8B0000]" data-testid="document-title">Document Management</h1>
          <p className="text-sm text-muted-foreground">Franchise & Employee Documents with Approval Workflow</p>
        </div>
        <div className="flex gap-2">
          {isAdmin && (
            <Button variant="outline" size="sm" onClick={() => setShowCategoryDialog(true)} data-testid="manage-categories-btn">
              <FolderOpen className="w-4 h-4 mr-1" /> Categories
            </Button>
          )}
          <Button className="bg-[#8B0000] hover:bg-[#6B0000]" size="sm" onClick={() => setShowUpload(true)} data-testid="upload-document-btn">
            <Upload className="w-4 h-4 mr-1" /> Upload Document
          </Button>
        </div>
      </div>

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { label: "Total", val: stats.total, icon: FileText, color: "text-gray-700" },
            { label: "Pending", val: stats.pending, icon: Clock, color: "text-amber-600" },
            { label: "Approved", val: stats.approved, icon: CheckCircle2, color: "text-green-600" },
            { label: "Rejected", val: stats.rejected, icon: XCircle, color: "text-red-600" },
            { label: "Expiring Soon", val: stats.expiring_soon, icon: CalendarClock, color: "text-orange-600" },
            { label: "Expired", val: stats.expired, icon: AlertTriangle, color: "text-red-700" },
          ].map((item, i) => (
            <Card key={i}>
              <CardContent className="p-3 text-center">
                <item.icon className={`w-5 h-5 mx-auto mb-1 ${item.color}`} />
                <p className="text-xs text-muted-foreground">{item.label}</p>
                <p className={`text-xl font-bold ${item.color}`}>{item.val}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="grid w-full max-w-lg grid-cols-3">
          <TabsTrigger value="documents" data-testid="tab-documents"><FileText className="w-4 h-4 mr-1" /> Documents</TabsTrigger>
          <TabsTrigger value="expiry" data-testid="tab-expiry"><AlertTriangle className="w-4 h-4 mr-1" /> Expiry Alerts</TabsTrigger>
          <TabsTrigger value="categories" data-testid="tab-categories"><FolderOpen className="w-4 h-4 mr-1" /> Categories</TabsTrigger>
        </TabsList>

        {/* ── DOCUMENTS TAB ── */}
        <TabsContent value="documents" className="space-y-4">
          <div className="flex flex-wrap gap-2 items-end">
            <Select value={filterCenter} onValueChange={setFilterCenter}>
              <SelectTrigger className="w-40"><SelectValue placeholder="All Centers" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Centers</SelectItem>
                {centers.map(c => <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={filterLevel} onValueChange={setFilterLevel}>
              <SelectTrigger className="w-36"><SelectValue placeholder="All Levels" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Levels</SelectItem>
                <SelectItem value="franchise">Franchise</SelectItem>
                <SelectItem value="employee">Employee</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterCategory} onValueChange={setFilterCategory}>
              <SelectTrigger className="w-44"><SelectValue placeholder="All Categories" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categories.map(c => <SelectItem key={c.category_id} value={c.category_id}>{c.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-32"><SelectValue placeholder="All Status" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm" onClick={loadDocuments} data-testid="refresh-docs-btn">
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>

          {loading ? (
            <div className="text-center py-8"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
          ) : documents.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <FileText className="w-12 h-12 mx-auto mb-2 opacity-30" />
              <p>No documents found</p>
            </div>
          ) : (
            <div className="space-y-2">
              {documents.map(doc => {
                const st = STATUS_STYLES[doc.status] || STATUS_STYLES.pending;
                const StatusIcon = st.icon;
                return (
                  <Card key={doc.document_id} className="overflow-hidden" data-testid={`doc-card-${doc.document_id}`}>
                    <CardContent className="p-3 flex items-center gap-3">
                      <div className="flex-shrink-0">
                        <FileText className="w-8 h-8 text-[#8B0000]" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium truncate">{doc.original_filename}</span>
                          <Badge variant="outline" className={`text-[10px] ${st.bg}`}>
                            <StatusIcon className="w-3 h-3 mr-0.5" />{doc.status}
                          </Badge>
                          <Badge variant="outline" className="text-[10px]">{doc.level}</Badge>
                          <Badge variant="secondary" className="text-[10px]">{doc.category_name}</Badge>
                        </div>
                        <div className="text-xs text-muted-foreground mt-0.5 flex flex-wrap gap-x-3">
                          <span>Center: {doc.center}</span>
                          {doc.employee_name && <span>Employee: {doc.employee_name}</span>}
                          {doc.franchise_code && <span>Franchise: {doc.franchise_code}</span>}
                          <span>Uploaded: {formatDate(doc.created_at)} by {doc.uploaded_by}</span>
                          {doc.expiry_date && (
                            <span className={isExpired(doc.expiry_date) ? "text-red-600 font-semibold" : isExpiringSoon(doc.expiry_date) ? "text-orange-600 font-semibold" : ""}>
                              Expires: {formatDate(doc.expiry_date)}
                              {isExpired(doc.expiry_date) && " (EXPIRED)"}
                              {isExpiringSoon(doc.expiry_date) && " (EXPIRING SOON)"}
                            </span>
                          )}
                          {doc.approved_by && <span>{doc.status === "approved" ? "Approved" : "Reviewed"} by {doc.approved_by}</span>}
                          {doc.rejection_reason && <span className="text-red-600">Reason: {doc.rejection_reason}</span>}
                        </div>
                      </div>
                      <div className="flex gap-1 flex-shrink-0">
                        <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => handleDownload(doc)} title="Download" data-testid={`download-${doc.document_id}`}>
                          <Download className="w-4 h-4" />
                        </Button>
                        {isAdmin && doc.status === "pending" && (
                          <>
                            <Button size="icon" variant="ghost" className="h-7 w-7 text-green-600" onClick={() => { setActionDoc(doc); setActionType("approve"); setShowAction(true); }} title="Approve" data-testid={`approve-${doc.document_id}`}>
                              <CheckCircle2 className="w-4 h-4" />
                            </Button>
                            <Button size="icon" variant="ghost" className="h-7 w-7 text-red-600" onClick={() => { setActionDoc(doc); setActionType("reject"); setShowAction(true); }} title="Reject" data-testid={`reject-${doc.document_id}`}>
                              <XCircle className="w-4 h-4" />
                            </Button>
                          </>
                        )}
                        {isAdmin && (
                          <Button size="icon" variant="ghost" className="h-7 w-7 text-red-400" onClick={() => handleDelete(doc.document_id)} title="Delete" data-testid={`delete-${doc.document_id}`}>
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>

        {/* ── EXPIRY ALERTS TAB ── */}
        <TabsContent value="expiry" className="space-y-4">
          {expiryData ? (
            <>
              {expiryData.already_expired?.length > 0 && (
                <Card className="border-red-200">
                  <CardHeader className="pb-2"><CardTitle className="text-base text-red-700"><AlertTriangle className="w-4 h-4 inline mr-1" /> Already Expired ({expiryData.already_expired.length})</CardTitle></CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {expiryData.already_expired.map(doc => (
                        <div key={doc.document_id} className="flex items-center justify-between p-2 bg-red-50 rounded border border-red-200 text-sm">
                          <div>
                            <span className="font-medium">{doc.original_filename}</span>
                            <span className="text-muted-foreground ml-2">{doc.center} | {doc.category_name}</span>
                            <span className="text-red-600 ml-2 font-semibold">Expired: {formatDate(doc.expiry_date)}</span>
                          </div>
                          <Button size="sm" variant="outline" onClick={() => handleDownload(doc)}>
                            <Download className="w-3 h-3 mr-1" /> View
                          </Button>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
              {expiryData.expiring_soon?.length > 0 && (
                <Card className="border-orange-200">
                  <CardHeader className="pb-2"><CardTitle className="text-base text-orange-700"><CalendarClock className="w-4 h-4 inline mr-1" /> Expiring Soon ({expiryData.expiring_soon.length})</CardTitle></CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {expiryData.expiring_soon.map(doc => (
                        <div key={doc.document_id} className="flex items-center justify-between p-2 bg-orange-50 rounded border border-orange-200 text-sm">
                          <div>
                            <span className="font-medium">{doc.original_filename}</span>
                            <span className="text-muted-foreground ml-2">{doc.center} | {doc.category_name}</span>
                            <span className="text-orange-600 ml-2 font-semibold">Expires: {formatDate(doc.expiry_date)}</span>
                          </div>
                          <Button size="sm" variant="outline" onClick={() => handleDownload(doc)}>
                            <Download className="w-3 h-3 mr-1" /> View
                          </Button>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
              {!expiryData.already_expired?.length && !expiryData.expiring_soon?.length && (
                <div className="text-center py-12 text-muted-foreground">
                  <CheckCircle2 className="w-12 h-12 mx-auto mb-2 text-green-300" />
                  <p>No expiry alerts. All documents are current.</p>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-8"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
          )}
        </TabsContent>

        {/* ── CATEGORIES TAB ── */}
        <TabsContent value="categories" className="space-y-4">
          <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3">
            {categories.map(cat => (
              <Card key={cat.category_id} data-testid={`category-${cat.category_id}`}>
                <CardContent className="p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <FolderOpen className="w-4 h-4 text-[#8B0000]" />
                    <span className="font-medium">{cat.name}</span>
                  </div>
                  <div className="flex gap-2 text-xs">
                    <Badge variant="outline">{cat.level}</Badge>
                    {cat.requires_expiry && <Badge variant="secondary">Expiry Required</Badge>}
                  </div>
                  {cat.description && <p className="text-xs text-muted-foreground mt-1">{cat.description}</p>}
                </CardContent>
              </Card>
            ))}
            {categories.length === 0 && (
              <div className="col-span-full text-center py-8 text-muted-foreground">
                No categories defined. {isAdmin && "Click 'Categories' to create one."}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* ── UPLOAD DIALOG ── */}
      <Dialog open={showUpload} onOpenChange={setShowUpload}>
        <DialogContent className="max-w-lg" data-testid="upload-dialog">
          <DialogHeader><DialogTitle>Upload Document</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Center *</Label>
                <Select value={uploadForm.center} onValueChange={v => setUploadForm({ ...uploadForm, center: v })}>
                  <SelectTrigger data-testid="upload-center-select"><SelectValue placeholder="Select Center" /></SelectTrigger>
                  <SelectContent>{centers.map(c => <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Level *</Label>
                <Select value={uploadForm.level} onValueChange={v => setUploadForm({ ...uploadForm, level: v })}>
                  <SelectTrigger data-testid="upload-level-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="franchise">Franchise</SelectItem>
                    <SelectItem value="employee">Employee</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label className="text-xs">Category *</Label>
              <Select value={uploadForm.category_id} onValueChange={v => setUploadForm({ ...uploadForm, category_id: v })}>
                <SelectTrigger data-testid="upload-category-select"><SelectValue placeholder="Select Category" /></SelectTrigger>
                <SelectContent>
                  {categories.filter(c => !uploadForm.level || c.level === uploadForm.level).map(c => (
                    <SelectItem key={c.category_id} value={c.category_id}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {uploadForm.level === "employee" && (
              <div>
                <Label className="text-xs">Employee Name</Label>
                <Input value={uploadForm.employee_name} onChange={e => setUploadForm({ ...uploadForm, employee_name: e.target.value })} placeholder="Employee name" data-testid="upload-employee-name" />
              </div>
            )}
            {uploadForm.level === "franchise" && (
              <div>
                <Label className="text-xs">Franchise Code</Label>
                <Input value={uploadForm.franchise_code} onChange={e => setUploadForm({ ...uploadForm, franchise_code: e.target.value })} placeholder="Franchise code" data-testid="upload-franchise-code" />
              </div>
            )}
            <div>
              <Label className="text-xs">Expiry Date</Label>
              <Input type="date" value={uploadForm.expiry_date} onChange={e => setUploadForm({ ...uploadForm, expiry_date: e.target.value })} data-testid="upload-expiry-date" />
            </div>
            <div>
              <Label className="text-xs">Notes</Label>
              <Input value={uploadForm.notes} onChange={e => setUploadForm({ ...uploadForm, notes: e.target.value })} placeholder="Optional notes" data-testid="upload-notes" />
            </div>
            <div>
              <Label className="text-xs">File * (PDF, JPG, PNG, DOC, DOCX, XLS, XLSX - Max 10MB)</Label>
              <Input type="file" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx" onChange={e => setUploadFile(e.target.files?.[0] || null)} data-testid="upload-file-input" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUpload(false)}>Cancel</Button>
            <Button onClick={handleUpload} disabled={uploading} className="bg-[#8B0000] hover:bg-[#6B0000]" data-testid="upload-submit-btn">
              {uploading ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Upload className="w-4 h-4 mr-1" />}
              Upload
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── APPROVE/REJECT DIALOG ── */}
      <Dialog open={showAction} onOpenChange={setShowAction}>
        <DialogContent data-testid="action-dialog">
          <DialogHeader>
            <DialogTitle>{actionType === "approve" ? "Approve" : "Reject"} Document</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            {actionDoc && (
              <div className="p-3 bg-gray-50 rounded text-sm">
                <p><strong>{actionDoc.original_filename}</strong></p>
                <p className="text-muted-foreground">{actionDoc.center} | {actionDoc.category_name} | {actionDoc.level}</p>
              </div>
            )}
            <div>
              <Label className="text-xs">Notes {actionType === "reject" ? "(Reason for rejection)" : "(optional)"}</Label>
              <Input value={actionNotes} onChange={e => setActionNotes(e.target.value)} placeholder="Enter notes..." data-testid="action-notes" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAction(false)}>Cancel</Button>
            <Button
              onClick={handleAction}
              className={actionType === "approve" ? "bg-green-600 hover:bg-green-700" : "bg-red-600 hover:bg-red-700"}
              data-testid="action-submit-btn"
            >
              {actionType === "approve" ? <CheckCircle2 className="w-4 h-4 mr-1" /> : <XCircle className="w-4 h-4 mr-1" />}
              {actionType === "approve" ? "Approve" : "Reject"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── CATEGORY CREATE DIALOG ── */}
      <Dialog open={showCategoryDialog} onOpenChange={setShowCategoryDialog}>
        <DialogContent data-testid="category-dialog">
          <DialogHeader><DialogTitle>Create Document Category</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <Label className="text-xs">Name *</Label>
              <Input value={catForm.name} onChange={e => setCatForm({ ...catForm, name: e.target.value })} placeholder="e.g. Franchise Agreement" data-testid="cat-name-input" />
            </div>
            <div>
              <Label className="text-xs">Level *</Label>
              <Select value={catForm.level} onValueChange={v => setCatForm({ ...catForm, level: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="franchise">Franchise</SelectItem>
                  <SelectItem value="employee">Employee</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="req-expiry" checked={catForm.requires_expiry} onChange={e => setCatForm({ ...catForm, requires_expiry: e.target.checked })} />
              <Label htmlFor="req-expiry" className="text-sm">Requires Expiry Date</Label>
            </div>
            <div>
              <Label className="text-xs">Description</Label>
              <Input value={catForm.description} onChange={e => setCatForm({ ...catForm, description: e.target.value })} placeholder="Optional description" data-testid="cat-desc-input" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCategoryDialog(false)}>Cancel</Button>
            <Button onClick={handleCreateCategory} className="bg-[#8B0000] hover:bg-[#6B0000]" data-testid="create-category-btn">
              <Plus className="w-4 h-4 mr-1" /> Create Category
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
