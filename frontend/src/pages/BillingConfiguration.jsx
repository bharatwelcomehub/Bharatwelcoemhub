import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from "@/components/ui/dialog";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import {
  Plus, Pencil, Trash2, LayoutGrid, Ban, Tags, Loader2, CheckCircle, XCircle
} from "lucide-react";

export default function BillingConfiguration() {
  const { session } = useAuth();
  const [activeTab, setActiveTab] = useState("tables");
  const [centersList, setCentersList] = useState([]);
  const [selectedCenter, setSelectedCenter] = useState("");

  // Tables state
  const [tables, setTables] = useState([]);
  const [showTableDialog, setShowTableDialog] = useState(false);
  const [tableForm, setTableForm] = useState({ table_no: "", capacity: 4, floor: "Ground", section: "", is_active: true });
  const [editingTableId, setEditingTableId] = useState(null);

  // Cancel Reasons state
  const [cancelReasons, setCancelReasons] = useState([]);
  const [showReasonDialog, setShowReasonDialog] = useState(false);
  const [reasonForm, setReasonForm] = useState({ reason: "", type: "order", is_active: true });
  const [editingReasonId, setEditingReasonId] = useState(null);

  // Categories state
  const [categories, setCategories] = useState([]);
  const [showCatDialog, setShowCatDialog] = useState(false);
  const [catForm, setCatForm] = useState({ name: "", description: "", display_order: 99, is_active: true });
  const [editingCatId, setEditingCatId] = useState(null);

  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchCenters = async () => {
      try {
        const res = await api.get("/centers");
        const centers = (res.data.centers || []).filter(c => c.active !== false);
        setCentersList(centers);
        if (!selectedCenter && session?.center) setSelectedCenter(session.center);
      } catch {}
    };
    fetchCenters();
  }, [session?.center]);

  const fetchTables = useCallback(async () => {
    if (!session?.token) return;
    setLoading(true);
    try {
      const res = await api.post("/billing-config/tables/list", { token: session.token, center: selectedCenter });
      setTables(res.data.tables || []);
    } catch { toast.error("Failed to load tables"); }
    finally { setLoading(false); }
  }, [session?.token, selectedCenter]);

  const fetchReasons = useCallback(async () => {
    if (!session?.token) return;
    try {
      const res = await api.post("/billing-config/cancel-reasons/list", { token: session.token });
      setCancelReasons(res.data.reasons || []);
    } catch { toast.error("Failed to load reasons"); }
  }, [session?.token]);

  const fetchCategories = useCallback(async () => {
    if (!session?.token) return;
    try {
      const res = await api.post("/billing-config/categories/list", { token: session.token });
      setCategories(res.data.categories || []);
    } catch { toast.error("Failed to load categories"); }
  }, [session?.token]);

  useEffect(() => {
    if (activeTab === "tables") fetchTables();
    else if (activeTab === "reasons") fetchReasons();
    else if (activeTab === "categories") fetchCategories();
  }, [activeTab, fetchTables, fetchReasons, fetchCategories]);

  // ── TABLE HANDLERS ──
  const openNewTable = () => {
    setTableForm({ table_no: "", capacity: 4, floor: "Ground", section: "", is_active: true });
    setEditingTableId(null);
    setShowTableDialog(true);
  };
  const openEditTable = (t) => {
    setTableForm({ table_no: t.table_no, capacity: t.capacity || 4, floor: t.floor || "Ground", section: t.section || "", is_active: t.is_active !== false });
    setEditingTableId(t.table_id);
    setShowTableDialog(true);
  };
  const saveTable = async () => {
    if (!tableForm.table_no.trim()) { toast.error("Table number is required"); return; }
    if (!selectedCenter) { toast.error("Select a center first"); return; }
    try {
      await api.post("/billing-config/tables/save", {
        token: session.token, center: selectedCenter, ...tableForm,
        table_id: editingTableId || undefined
      });
      toast.success(editingTableId ? "Table updated" : "Table added");
      setShowTableDialog(false);
      fetchTables();
    } catch (err) { toast.error(err.response?.data?.detail || "Save failed"); }
  };
  const deleteTable = async (id) => {
    if (!confirm("Delete this table?")) return;
    try {
      await api.post("/billing-config/tables/delete", { token: session.token, table_id: id });
      toast.success("Table deleted");
      fetchTables();
    } catch (err) { toast.error(err.response?.data?.detail || "Delete failed"); }
  };

  // ── REASON HANDLERS ──
  const openNewReason = () => {
    setReasonForm({ reason: "", type: "order", is_active: true });
    setEditingReasonId(null);
    setShowReasonDialog(true);
  };
  const openEditReason = (r) => {
    setReasonForm({ reason: r.reason, type: r.type, is_active: r.is_active !== false });
    setEditingReasonId(r.reason_id);
    setShowReasonDialog(true);
  };
  const saveReason = async () => {
    if (!reasonForm.reason.trim()) { toast.error("Reason text is required"); return; }
    try {
      await api.post("/billing-config/cancel-reasons/save", {
        token: session.token, ...reasonForm,
        reason_id: editingReasonId || undefined
      });
      toast.success(editingReasonId ? "Reason updated" : "Reason added");
      setShowReasonDialog(false);
      fetchReasons();
    } catch (err) { toast.error(err.response?.data?.detail || "Save failed"); }
  };
  const deleteReason = async (id) => {
    if (!confirm("Delete this reason?")) return;
    try {
      await api.post("/billing-config/cancel-reasons/delete", { token: session.token, reason_id: id });
      toast.success("Reason deleted");
      fetchReasons();
    } catch (err) { toast.error(err.response?.data?.detail || "Delete failed"); }
  };

  // ── CATEGORY HANDLERS ──
  const openNewCat = () => {
    setCatForm({ name: "", description: "", display_order: 99, is_active: true });
    setEditingCatId(null);
    setShowCatDialog(true);
  };
  const openEditCat = (c) => {
    setCatForm({ name: c.name, description: c.description || "", display_order: c.display_order || 99, is_active: c.is_active !== false });
    setEditingCatId(c.category_id);
    setShowCatDialog(true);
  };
  const saveCat = async () => {
    if (!catForm.name.trim()) { toast.error("Category name is required"); return; }
    try {
      await api.post("/billing-config/categories/save", {
        token: session.token, ...catForm,
        category_id: editingCatId || undefined
      });
      toast.success(editingCatId ? "Category updated" : "Category added");
      setShowCatDialog(false);
      fetchCategories();
    } catch (err) { toast.error(err.response?.data?.detail || "Save failed"); }
  };
  const deleteCat = async (id) => {
    if (!confirm("Delete this category?")) return;
    try {
      await api.post("/billing-config/categories/delete", { token: session.token, category_id: id });
      toast.success("Category deleted");
      fetchCategories();
    } catch (err) { toast.error(err.response?.data?.detail || "Delete failed"); }
  };

  const statusColor = (s) => {
    if (s === "available") return "bg-emerald-100 text-emerald-700 border-emerald-200";
    if (s === "occupied") return "bg-red-100 text-red-700 border-red-200";
    if (s === "reserved") return "bg-amber-100 text-amber-700 border-amber-200";
    return "bg-slate-100 text-slate-700 border-slate-200";
  };

  const reasonTypeColor = (t) => {
    if (t === "order") return "bg-blue-100 text-blue-700";
    if (t === "bill") return "bg-purple-100 text-purple-700";
    if (t === "kot") return "bg-orange-100 text-orange-700";
    return "bg-slate-100 text-slate-700";
  };

  return (
    <div className="space-y-4" data-testid="billing-configuration">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Billing / POS Configuration</h1>
          <p className="text-sm text-muted-foreground">Manage tables, cancellation reasons, and menu categories</p>
        </div>
        {activeTab === "tables" && (
          <Select value={selectedCenter} onValueChange={(v) => { setSelectedCenter(v); }}>
            <SelectTrigger className="w-[160px]" data-testid="config-center-select">
              <SelectValue placeholder="Select Center" />
            </SelectTrigger>
            <SelectContent>
              {centersList.map(c => <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-3 w-fit">
          <TabsTrigger value="tables" data-testid="tab-tables" className="gap-1.5">
            <LayoutGrid className="w-4 h-4" /> Tables
          </TabsTrigger>
          <TabsTrigger value="reasons" data-testid="tab-reasons" className="gap-1.5">
            <Ban className="w-4 h-4" /> Cancellation Reasons
          </TabsTrigger>
          <TabsTrigger value="categories" data-testid="tab-categories" className="gap-1.5">
            <Tags className="w-4 h-4" /> Menu Categories
          </TabsTrigger>
        </TabsList>

        {/* ═══ TABLES TAB ═══ */}
        <TabsContent value="tables">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between py-3">
              <CardTitle className="text-base">Tables — {selectedCenter || "All Centers"}</CardTitle>
              <Button size="sm" onClick={openNewTable} disabled={!selectedCenter} data-testid="add-table-btn">
                <Plus className="w-4 h-4 mr-1" /> Add Table
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              {loading ? (
                <div className="flex items-center justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
              ) : tables.length === 0 ? (
                <p className="text-center text-muted-foreground py-12">No tables configured{selectedCenter ? ` for ${selectedCenter}` : ". Select a center."}
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Table No</TableHead>
                      <TableHead>Capacity</TableHead>
                      <TableHead>Floor</TableHead>
                      <TableHead>Section</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Active</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tables.map(t => (
                      <TableRow key={t.table_id} data-testid={`table-row-${t.table_no}`}>
                        <TableCell className="font-semibold">{t.table_no}</TableCell>
                        <TableCell>{t.capacity} pax</TableCell>
                        <TableCell>{t.floor}</TableCell>
                        <TableCell>{t.section || "—"}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={statusColor(t.status)}>{t.status}</Badge>
                        </TableCell>
                        <TableCell>
                          {t.is_active !== false ? (
                            <CheckCircle className="w-4 h-4 text-emerald-500" />
                          ) : (
                            <XCircle className="w-4 h-4 text-red-400" />
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="icon" onClick={() => openEditTable(t)} className="h-7 w-7">
                            <Pencil className="w-3.5 h-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => deleteTable(t.table_id)} className="h-7 w-7 text-red-500 hover:text-red-600">
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ═══ CANCELLATION REASONS TAB ═══ */}
        <TabsContent value="reasons">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between py-3">
              <CardTitle className="text-base">Cancellation Reasons</CardTitle>
              <Button size="sm" onClick={openNewReason} data-testid="add-reason-btn">
                <Plus className="w-4 h-4 mr-1" /> Add Reason
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              {cancelReasons.length === 0 ? (
                <p className="text-center text-muted-foreground py-12">No cancellation reasons configured yet</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Reason</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Active</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {cancelReasons.map(r => (
                      <TableRow key={r.reason_id} data-testid={`reason-row-${r.reason_id}`}>
                        <TableCell className="font-medium">{r.reason}</TableCell>
                        <TableCell>
                          <Badge className={reasonTypeColor(r.type)}>{r.type.toUpperCase()}</Badge>
                        </TableCell>
                        <TableCell>
                          {r.is_active !== false ? (
                            <CheckCircle className="w-4 h-4 text-emerald-500" />
                          ) : (
                            <XCircle className="w-4 h-4 text-red-400" />
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="icon" onClick={() => openEditReason(r)} className="h-7 w-7">
                            <Pencil className="w-3.5 h-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => deleteReason(r.reason_id)} className="h-7 w-7 text-red-500 hover:text-red-600">
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ═══ MENU CATEGORIES TAB ═══ */}
        <TabsContent value="categories">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between py-3">
              <CardTitle className="text-base">Menu Categories</CardTitle>
              <Button size="sm" onClick={openNewCat} data-testid="add-category-btn">
                <Plus className="w-4 h-4 mr-1" /> Add Category
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              {categories.length === 0 ? (
                <p className="text-center text-muted-foreground py-12">No menu categories configured yet</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Order</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Active</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {categories.map(c => (
                      <TableRow key={c.category_id || c.name} data-testid={`cat-row-${c.name}`}>
                        <TableCell className="w-16 text-center">{c.display_order}</TableCell>
                        <TableCell className="font-semibold">{c.name}</TableCell>
                        <TableCell className="text-muted-foreground">{c.description || "—"}</TableCell>
                        <TableCell>
                          {c.is_active !== false ? (
                            <CheckCircle className="w-4 h-4 text-emerald-500" />
                          ) : (
                            <XCircle className="w-4 h-4 text-red-400" />
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="icon" onClick={() => openEditCat(c)} className="h-7 w-7">
                            <Pencil className="w-3.5 h-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => deleteCat(c.category_id)} className="h-7 w-7 text-red-500 hover:text-red-600">
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* ═══ TABLE DIALOG ═══ */}
      <Dialog open={showTableDialog} onOpenChange={setShowTableDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingTableId ? "Edit Table" : "Add Table"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Table Number *</label>
              <Input value={tableForm.table_no} onChange={e => setTableForm({...tableForm, table_no: e.target.value})} placeholder="e.g. T1, A3" data-testid="table-no-input" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Capacity (pax)</label>
                <Input type="number" value={tableForm.capacity} onChange={e => setTableForm({...tableForm, capacity: parseInt(e.target.value) || 1})} data-testid="table-capacity-input" />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Floor</label>
                <Select value={tableForm.floor} onValueChange={v => setTableForm({...tableForm, floor: v})}>
                  <SelectTrigger data-testid="table-floor-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Ground">Ground</SelectItem>
                    <SelectItem value="1st Floor">1st Floor</SelectItem>
                    <SelectItem value="2nd Floor">2nd Floor</SelectItem>
                    <SelectItem value="Terrace">Terrace</SelectItem>
                    <SelectItem value="Outdoor">Outdoor</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Section (optional)</label>
              <Input value={tableForm.section} onChange={e => setTableForm({...tableForm, section: e.target.value})} placeholder="e.g. VIP, Garden" data-testid="table-section-input" />
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" checked={tableForm.is_active} onChange={e => setTableForm({...tableForm, is_active: e.target.checked})} className="accent-emerald-500" id="table-active" />
              <label htmlFor="table-active" className="text-sm">Active</label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTableDialog(false)}>Cancel</Button>
            <Button onClick={saveTable} data-testid="save-table-btn">Save Table</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ═══ REASON DIALOG ═══ */}
      <Dialog open={showReasonDialog} onOpenChange={setShowReasonDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingReasonId ? "Edit Reason" : "Add Cancellation Reason"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Reason *</label>
              <Input value={reasonForm.reason} onChange={e => setReasonForm({...reasonForm, reason: e.target.value})} placeholder="e.g. Customer changed mind" data-testid="reason-text-input" />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Type</label>
              <Select value={reasonForm.type} onValueChange={v => setReasonForm({...reasonForm, type: v})}>
                <SelectTrigger data-testid="reason-type-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="order">Order Cancellation</SelectItem>
                  <SelectItem value="bill">Bill Void</SelectItem>
                  <SelectItem value="kot">KOT Cancellation</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" checked={reasonForm.is_active} onChange={e => setReasonForm({...reasonForm, is_active: e.target.checked})} className="accent-emerald-500" id="reason-active" />
              <label htmlFor="reason-active" className="text-sm">Active</label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowReasonDialog(false)}>Cancel</Button>
            <Button onClick={saveReason} data-testid="save-reason-btn">Save Reason</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ═══ CATEGORY DIALOG ═══ */}
      <Dialog open={showCatDialog} onOpenChange={setShowCatDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingCatId ? "Edit Category" : "Add Menu Category"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Category Name *</label>
              <Input value={catForm.name} onChange={e => setCatForm({...catForm, name: e.target.value})} placeholder="e.g. Starters, Main Course" data-testid="cat-name-input" />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Description</label>
              <Input value={catForm.description} onChange={e => setCatForm({...catForm, description: e.target.value})} placeholder="Optional description" />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Display Order</label>
              <Input type="number" value={catForm.display_order} onChange={e => setCatForm({...catForm, display_order: parseInt(e.target.value) || 0})} data-testid="cat-order-input" />
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" checked={catForm.is_active} onChange={e => setCatForm({...catForm, is_active: e.target.checked})} className="accent-emerald-500" id="cat-active" />
              <label htmlFor="cat-active" className="text-sm">Active</label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCatDialog(false)}>Cancel</Button>
            <Button onClick={saveCat} data-testid="save-category-btn">Save Category</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
