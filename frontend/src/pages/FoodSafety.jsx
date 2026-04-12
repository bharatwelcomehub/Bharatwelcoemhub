import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "@/App";
import { api, isAdminUser, fetchCentersFromDB } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Loader2, Plus, Save, Trash2, Search, X, RefreshCw, Edit, Download,
  FileText, ClipboardCheck, Thermometer, Clock, Sparkles, Shield,
  AlertTriangle, CheckCircle, FileSpreadsheet, Eye,
} from "lucide-react";

const STATUS_COLORS = {
  draft: "bg-yellow-100 text-yellow-800 border-yellow-300",
  submitted: "bg-blue-100 text-blue-800 border-blue-300",
  approved: "bg-green-100 text-green-800 border-green-300",
  locked: "bg-gray-200 text-gray-700 border-gray-400",
  overdue: "bg-red-100 text-red-800 border-red-300",
};

const TYPE_ICONS = {
  supplier_details: ClipboardCheck,
  food_receipt: FileText,
  cooking_cooling: Thermometer,
  food_temp_record: Thermometer,
  two_four_hour_rule: Clock,
  cleaning_procedure: Sparkles,
  cleaning_record: Sparkles,
  general_temp_record: Thermometer,
};

export default function FoodSafety() {
  const { session } = useAuth();
  const isAdmin = isAdminUser(session);

  const [activeTab, setActiveTab] = useState("dashboard");
  const [templateTypes, setTemplateTypes] = useState([]);
  const [templateColumns, setTemplateColumns] = useState({});
  const [loading, setLoading] = useState(false);
  const columnsRef = useRef({});

  // Dashboard
  const [dashboard, setDashboard] = useState(null);
  const [dashCenter, setDashCenter] = useState(session?.center || "PB-PERTH");
  const [centersList, setCentersList] = useState([]);

  // Template Items (CRUD)
  const [templateItems, setTemplateItems] = useState([]);
  const [selectedType, setSelectedType] = useState("supplier_details");
  const [itemForm, setItemForm] = useState(null);

  // Records
  const [records, setRecords] = useState([]);
  const [recordFilter, setRecordFilter] = useState({ template_type: "", status: "", date_from: "", date_to: "" });
  const [recordForm, setRecordForm] = useState(null);
  const [recordEntries, setRecordEntries] = useState([]);

  // Load centers list for selector
  useEffect(() => {
    if (session?.token) {
      fetchCentersFromDB(session.token).then(centers => {
        // Filter to non-India centers + always include current
        const nonIndia = centers.filter(c => c.is_india_center === false || c.code === dashCenter);
        setCentersList(nonIndia.length > 0 ? nonIndia : centers);
      });
    }
  }, [session?.token]);

  // Load template types on mount
  useEffect(() => {
    if (session?.token) {
      api.post("/food-safety/template-types", { token: session.token })
        .then(res => {
          setTemplateTypes(res.data.types || []);
          const cols = res.data.columns || {};
          setTemplateColumns(cols);
          columnsRef.current = cols;
        })
        .catch((e) => {
          console.error("Failed to load template types:", e);
          toast.error("Failed to load template types");
        });
    }
  }, [session?.token]);

  // Load dashboard
  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.post("/food-safety/dashboard", { token: session.token, center: dashCenter });
      setDashboard(res.data);
    } catch (e) {
      toast.error("Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, [session?.token, dashCenter]);

  useEffect(() => {
    if (activeTab === "dashboard" && session?.token) loadDashboard();
  }, [activeTab, loadDashboard, session?.token]);

  // Seed templates
  const seedTemplates = async () => {
    try {
      const res = await api.post("/food-safety/seed", { token: session.token, center: dashCenter });
      toast.success(res.data.message);
      loadTemplateItems();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Seed failed");
    }
  };

  // Load template items
  const loadTemplateItems = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.post("/food-safety/template-items/list", {
        token: session.token, template_type: selectedType, center: dashCenter,
      });
      setTemplateItems(res.data.items || []);
    } catch (e) {
      toast.error("Failed to load items");
    } finally {
      setLoading(false);
    }
  }, [session?.token, selectedType, dashCenter]);

  useEffect(() => {
    if (activeTab === "templates" && session?.token) loadTemplateItems();
  }, [activeTab, loadTemplateItems, session?.token]);

  // Save template item
  const saveTemplateItem = async () => {
    if (!itemForm) return;
    try {
      const payload = {
        token: session.token, template_type: selectedType, center: dashCenter,
        name: itemForm.name, fields: itemForm.fields, active: itemForm.active !== false,
        order: itemForm.order || 0, item_id: itemForm.item_id || "",
      };
      await api.post("/food-safety/template-items/save", payload);
      toast.success("Item saved");
      setItemForm(null);
      loadTemplateItems();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Save failed");
    }
  };

  // Delete template item
  const deleteTemplateItem = async (item_id) => {
    if (!window.confirm("Delete this template item?")) return;
    try {
      await api.post("/food-safety/template-items/delete", { token: session.token, item_id });
      toast.success("Deleted");
      loadTemplateItems();
    } catch (e) {
      toast.error("Delete failed");
    }
  };

  // Toggle template item
  const toggleTemplateItem = async (item_id, active) => {
    try {
      await api.post("/food-safety/template-items/toggle", { token: session.token, item_id, active: !active });
      loadTemplateItems();
    } catch (e) {
      toast.error("Toggle failed");
    }
  };

  // Load records
  const loadRecords = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.post("/food-safety/records/list", {
        token: session.token, center: dashCenter, ...recordFilter,
      });
      setRecords(res.data.records || []);
    } catch (e) {
      toast.error("Failed to load records");
    } finally {
      setLoading(false);
    }
  }, [session?.token, dashCenter, recordFilter]);

  useEffect(() => {
    if (activeTab === "records" && session?.token) loadRecords();
  }, [activeTab, loadRecords, session?.token]);

  // Start new record
  const startNewRecord = (templateType) => {
    // Use ref to get latest columns (avoids stale closure)
    const cols = columnsRef.current[templateType] || templateColumns[templateType] || [];
    setRecordForm({
      template_type: templateType,
      record_date: new Date().toISOString().split("T")[0],
      period: "daily",
      notes: "",
      status: "draft",
    });
    // Create one empty entry row with all column keys
    const emptyRow = {};
    cols.forEach(col => { emptyRow[col.key] = ""; });
    setRecordEntries([emptyRow]);
    setActiveTab("record-entry");
  };

  // Add row to record entries
  const addEntryRow = () => {
    const cols = columnsRef.current[recordForm?.template_type] || templateColumns[recordForm?.template_type] || [];
    const emptyRow = {};
    cols.forEach(col => { emptyRow[col.key] = ""; });
    setRecordEntries(prev => [...prev, emptyRow]);
  };

  // Update entry field
  const updateEntry = (rowIdx, key, value) => {
    setRecordEntries(prev => prev.map((row, i) => i === rowIdx ? { ...row, [key]: value } : row));
  };

  // Remove entry row
  const removeEntryRow = (rowIdx) => {
    setRecordEntries(prev => prev.filter((_, i) => i !== rowIdx));
  };

  // Save record
  const saveRecord = async (submitStatus = "draft") => {
    if (!recordForm) return;
    setLoading(true);
    try {
      const payload = {
        token: session.token, center: dashCenter,
        template_type: recordForm.template_type,
        record_date: recordForm.record_date,
        period: recordForm.period,
        notes: recordForm.notes,
        entries: recordEntries,
        status: submitStatus,
        record_id: recordForm.record_id || "",
      };
      const res = await api.post("/food-safety/records/save", payload);
      toast.success(res.data.message);
      setRecordForm(null);
      setRecordEntries([]);
      setActiveTab("records");
      loadRecords();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Save failed");
    } finally {
      setLoading(false);
    }
  };

  // Approve record
  const approveRecord = async (record_id) => {
    try {
      await api.post("/food-safety/records/approve", { token: session.token, record_id });
      toast.success("Record approved");
      loadRecords();
      loadDashboard();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Approve failed");
    }
  };

  // Edit existing record
  const editRecord = (rec) => {
    if (rec.status === "locked" || rec.status === "approved") {
      toast.error("Cannot edit locked/approved records");
      return;
    }
    setRecordForm({
      template_type: rec.template_type,
      record_date: rec.record_date,
      period: rec.period || "daily",
      notes: rec.notes || "",
      status: rec.status,
      record_id: rec.record_id,
    });
    setRecordEntries(rec.entries || []);
    setActiveTab("record-entry");
  };

  // Download report
  const downloadReport = async (format) => {
    setLoading(true);
    try {
      const endpoint = format === "pdf" ? "/food-safety/report/pdf" : "/food-safety/report/excel";
      const res = await api.post(endpoint, {
        token: session.token, center: dashCenter,
        template_type: recordFilter.template_type,
        date_from: recordFilter.date_from, date_to: recordFilter.date_to,
      }, { responseType: "blob" });
      const ct = res.headers["content-type"] || "";
      if (ct.includes("application/json")) {
        const text = await res.data.text();
        toast.error(JSON.parse(text).detail || "No records found");
        return;
      }
      const blob = new Blob([res.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `FoodSafety_Report.${format === "pdf" ? "pdf" : "xlsx"}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success(`${format.toUpperCase()} downloaded`);
    } catch (e) {
      toast.error("Download failed");
    } finally {
      setLoading(false);
    }
  };

  // Tab navigation
  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: Shield },
    { id: "records", label: "Records", icon: FileText },
    { id: "templates", label: "Template Master", icon: ClipboardCheck },
  ];

  const typeLabel = (key) => templateTypes.find(t => t.key === key)?.label || key;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-primary" data-testid="food-safety-title">
            Food Safety Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Compliance records for {dashCenter}
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <select value={dashCenter} onChange={e => setDashCenter(e.target.value)}
            className="h-10 px-3 rounded-md border border-input bg-background text-sm" data-testid="fs-center-select">
            {centersList.length > 0 ? centersList.map(c => (
              <option key={c.code} value={c.code}>{c.code}</option>
            )) : (
              <option value={dashCenter}>{dashCenter}</option>
            )}
          </select>
          {isAdmin && (
            <Button onClick={seedTemplates} variant="outline" size="sm" data-testid="seed-btn">
              <Sparkles className="w-4 h-4 mr-1" /> Seed Templates
            </Button>
          )}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 border-b" data-testid="fs-tabs">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
            }`} data-testid={`tab-${tab.id}`}>
            <tab.icon className="w-4 h-4" /> {tab.label}
          </button>
        ))}
        {activeTab === "record-entry" && (
          <button className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 border-primary text-primary">
            <Edit className="w-4 h-4" /> Record Entry
          </button>
        )}
      </div>

      {/* ===== DASHBOARD TAB ===== */}
      {activeTab === "dashboard" && (
        <div className="space-y-6">
          {/* Overdue alerts */}
          {dashboard?.overdue?.length > 0 && (
            <Card className="border-red-300 bg-red-50" data-testid="overdue-alerts">
              <CardHeader className="pb-2">
                <CardTitle className="text-red-800 text-sm flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" /> Missing Today's Records
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {dashboard.overdue.map((o, i) => (
                    <Badge key={i} className="bg-red-200 text-red-900 cursor-pointer" onClick={() => startNewRecord(o.template_type)}>
                      {o.label} - {o.date}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Status cards per template */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {templateTypes.map(tt => {
              const counts = dashboard?.status_counts?.[tt.key] || { draft: 0, submitted: 0, approved: 0, locked: 0 };
              const Icon = TYPE_ICONS[tt.key] || FileText;
              const total = counts.draft + counts.submitted + counts.approved + counts.locked;
              return (
                <Card key={tt.key} className="hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => startNewRecord(tt.key)} data-testid={`dash-card-${tt.key}`}>
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between mb-2">
                      <Icon className="w-5 h-5 text-primary" />
                      <Badge variant="outline">{total}</Badge>
                    </div>
                    <h3 className="font-semibold text-sm">{tt.label}</h3>
                    <div className="flex gap-1 mt-2 flex-wrap">
                      {counts.draft > 0 && <Badge className={STATUS_COLORS.draft}>{counts.draft} Draft</Badge>}
                      {counts.submitted > 0 && <Badge className={STATUS_COLORS.submitted}>{counts.submitted} Submitted</Badge>}
                      {counts.approved > 0 && <Badge className={STATUS_COLORS.approved}>{counts.approved} Approved</Badge>}
                      {counts.locked > 0 && <Badge className={STATUS_COLORS.locked}>{counts.locked} Locked</Badge>}
                      {total === 0 && <span className="text-xs text-muted-foreground">No records yet</span>}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Recent records */}
          {dashboard?.recent_records?.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Recent Records</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {dashboard.recent_records.slice(0, 15).map((rec, i) => (
                    <div key={i} className="flex items-center justify-between p-2 border rounded hover:bg-muted/30 cursor-pointer"
                      onClick={() => editRecord(rec)} data-testid={`recent-rec-${i}`}>
                      <div className="flex items-center gap-3">
                        <Badge className={STATUS_COLORS[rec.status] || ""}>{rec.status}</Badge>
                        <span className="text-sm font-medium">{typeLabel(rec.template_type)}</span>
                        <span className="text-xs text-muted-foreground">{rec.record_date}</span>
                      </div>
                      <span className="text-xs text-muted-foreground">{rec.submittedBy || rec.createdBy || ""}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ===== TEMPLATE MASTER TAB ===== */}
      {activeTab === "templates" && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 flex-wrap">
            <select value={selectedType} onChange={e => setSelectedType(e.target.value)}
              className="h-10 px-3 rounded-md border border-input bg-background text-sm" data-testid="template-type-select">
              {templateTypes.map(tt => (
                <option key={tt.key} value={tt.key}>{tt.label}</option>
              ))}
            </select>
            <Button onClick={loadTemplateItems} variant="outline" size="sm" disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} /> Refresh
            </Button>
            {isAdmin && (
              <Button onClick={() => setItemForm({ name: "", fields: {}, active: true, order: templateItems.length })} size="sm" data-testid="add-item-btn">
                <Plus className="w-4 h-4 mr-1" /> Add Item
              </Button>
            )}
            <Badge variant="outline">{templateItems.length} items</Badge>
          </div>

          {/* Item form */}
          {itemForm && (
            <Card className="border-2 border-primary">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center justify-between">
                  {itemForm.item_id ? "Edit Item" : "Add New Item"}
                  <Button variant="ghost" size="sm" onClick={() => setItemForm(null)}><X className="w-4 h-4" /></Button>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">Name</Label>
                    <Input value={itemForm.name} onChange={e => setItemForm(p => ({ ...p, name: e.target.value }))}
                      placeholder="Item name" data-testid="item-name" />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Order</Label>
                    <Input type="number" value={itemForm.order} onChange={e => setItemForm(p => ({ ...p, order: parseInt(e.target.value) || 0 }))} />
                  </div>
                  <div className="flex items-end gap-2">
                    <div className="flex items-center gap-2">
                      <Checkbox checked={itemForm.active !== false} onCheckedChange={v => setItemForm(p => ({ ...p, active: v }))} />
                      <Label className="text-xs">Active</Label>
                    </div>
                  </div>
                </div>
                {/* Field inputs based on template columns */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {(templateColumns[selectedType] || []).map(col => (
                    <div key={col.key} className="space-y-1">
                      <Label className="text-xs">{col.label}</Label>
                      {col.type === "textarea" ? (
                        <Textarea value={itemForm.fields?.[col.key] || ""}
                          onChange={e => setItemForm(p => ({ ...p, fields: { ...p.fields, [col.key]: e.target.value } }))}
                          rows={2} className="text-xs" />
                      ) : col.type === "select" ? (
                        <select value={itemForm.fields?.[col.key] || ""}
                          onChange={e => setItemForm(p => ({ ...p, fields: { ...p.fields, [col.key]: e.target.value } }))}
                          className="w-full h-9 px-2 rounded-md border border-input bg-background text-xs">
                          <option value="">Select</option>
                          {(col.options || []).map(o => <option key={o} value={o}>{o}</option>)}
                        </select>
                      ) : (
                        <Input value={itemForm.fields?.[col.key] || ""}
                          onChange={e => setItemForm(p => ({ ...p, fields: { ...p.fields, [col.key]: e.target.value } }))}
                          type={col.type === "number" ? "number" : "text"} className="text-xs" />
                      )}
                    </div>
                  ))}
                </div>
                <Button onClick={saveTemplateItem} size="sm" data-testid="save-item-btn">
                  <Save className="w-4 h-4 mr-1" /> Save Item
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Items list */}
          <div className="border rounded-lg overflow-hidden">
            <div className="overflow-x-auto max-h-[500px]">
              <table className="w-full text-sm">
                <thead className="bg-muted sticky top-0 z-10">
                  <tr>
                    <th className="p-3 text-left font-bold">Name</th>
                    {(templateColumns[selectedType] || []).slice(0, 4).map(col => (
                      <th key={col.key} className="p-3 text-left font-bold">{col.label}</th>
                    ))}
                    <th className="p-3 text-center font-bold">Status</th>
                    {isAdmin && <th className="p-3 text-center font-bold">Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {templateItems.map((item, idx) => (
                    <tr key={item.item_id || idx} className="border-t hover:bg-muted/30" data-testid={`template-item-${idx}`}>
                      <td className="p-3 font-medium">{item.name}</td>
                      {(templateColumns[selectedType] || []).slice(0, 4).map(col => (
                        <td key={col.key} className="p-3 text-xs text-muted-foreground max-w-[150px] truncate">
                          {item.fields?.[col.key] || "-"}
                        </td>
                      ))}
                      <td className="p-3 text-center">
                        <Badge variant={item.active !== false ? "default" : "secondary"}>
                          {item.active !== false ? "Active" : "Inactive"}
                        </Badge>
                      </td>
                      {isAdmin && (
                        <td className="p-3 text-center">
                          <div className="flex gap-1 justify-center">
                            <Button size="sm" variant="ghost" onClick={() => setItemForm({ ...item })}>
                              <Edit className="w-3 h-3" />
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => toggleTemplateItem(item.item_id, item.active !== false)}>
                              {item.active !== false ? <X className="w-3 h-3 text-red-500" /> : <CheckCircle className="w-3 h-3 text-green-500" />}
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => deleteTemplateItem(item.item_id)}>
                              <Trash2 className="w-3 h-3 text-red-500" />
                            </Button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                  {templateItems.length === 0 && (
                    <tr><td colSpan={10} className="p-8 text-center text-muted-foreground">
                      No template items. {isAdmin ? "Click 'Seed Templates' or 'Add Item' to get started." : ""}
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ===== RECORDS TAB ===== */}
      {activeTab === "records" && (
        <div className="space-y-4">
          {/* Filters */}
          <Card>
            <CardContent className="pt-4">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 items-end">
                <div className="space-y-1">
                  <Label className="text-xs">Template Type</Label>
                  <select value={recordFilter.template_type}
                    onChange={e => setRecordFilter(p => ({ ...p, template_type: e.target.value }))}
                    className="w-full h-9 px-2 rounded-md border border-input bg-background text-xs" data-testid="rec-type-filter">
                    <option value="">All Types</option>
                    {templateTypes.map(tt => <option key={tt.key} value={tt.key}>{tt.label}</option>)}
                  </select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Status</Label>
                  <select value={recordFilter.status}
                    onChange={e => setRecordFilter(p => ({ ...p, status: e.target.value }))}
                    className="w-full h-9 px-2 rounded-md border border-input bg-background text-xs" data-testid="rec-status-filter">
                    <option value="">All</option>
                    <option value="draft">Draft</option>
                    <option value="submitted">Submitted</option>
                    <option value="approved">Approved</option>
                    <option value="locked">Locked</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">From Date</Label>
                  <Input type="date" value={recordFilter.date_from} className="text-xs h-9"
                    onChange={e => setRecordFilter(p => ({ ...p, date_from: e.target.value }))} />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">To Date</Label>
                  <Input type="date" value={recordFilter.date_to} className="text-xs h-9"
                    onChange={e => setRecordFilter(p => ({ ...p, date_to: e.target.value }))} />
                </div>
                <div className="flex gap-2">
                  <Button onClick={loadRecords} size="sm" variant="outline" disabled={loading}>
                    <Search className="w-3 h-3 mr-1" /> Filter
                  </Button>
                  <Button onClick={() => downloadReport("pdf")} size="sm" variant="outline" disabled={loading}>
                    <Download className="w-3 h-3 mr-1" /> PDF
                  </Button>
                  <Button onClick={() => downloadReport("excel")} size="sm" variant="outline" disabled={loading}>
                    <FileSpreadsheet className="w-3 h-3 mr-1" /> Excel
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick add buttons */}
          <div className="flex gap-2 flex-wrap">
            {templateTypes.map(tt => (
              <Button key={tt.key} size="sm" variant="outline" onClick={() => startNewRecord(tt.key)} data-testid={`new-rec-${tt.key}`}>
                <Plus className="w-3 h-3 mr-1" /> {tt.label}
              </Button>
            ))}
          </div>

          {/* Records table */}
          <div className="border rounded-lg overflow-hidden">
            <div className="overflow-x-auto max-h-[500px]">
              <table className="w-full text-sm">
                <thead className="bg-muted sticky top-0 z-10">
                  <tr>
                    <th className="p-3 text-left font-bold">Record ID</th>
                    <th className="p-3 text-left font-bold">Type</th>
                    <th className="p-3 text-left font-bold">Date</th>
                    <th className="p-3 text-left font-bold">Entries</th>
                    <th className="p-3 text-left font-bold">Status</th>
                    <th className="p-3 text-left font-bold">Submitted By</th>
                    <th className="p-3 text-left font-bold">Approved By</th>
                    <th className="p-3 text-center font-bold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((rec, idx) => (
                    <tr key={rec.record_id || idx} className="border-t hover:bg-muted/30" data-testid={`record-row-${idx}`}>
                      <td className="p-3 font-mono text-xs">{rec.record_id}</td>
                      <td className="p-3">{typeLabel(rec.template_type)}</td>
                      <td className="p-3">{rec.record_date}</td>
                      <td className="p-3"><Badge variant="outline">{rec.entries?.length || 0}</Badge></td>
                      <td className="p-3"><Badge className={STATUS_COLORS[rec.status] || ""}>{rec.status}</Badge></td>
                      <td className="p-3 text-xs">{rec.submittedBy || rec.createdBy || "-"}</td>
                      <td className="p-3 text-xs">{rec.approvedBy || "-"}</td>
                      <td className="p-3 text-center">
                        <div className="flex gap-1 justify-center">
                          {(rec.status === "draft" || rec.status === "submitted") && (
                            <Button size="sm" variant="ghost" onClick={() => editRecord(rec)}>
                              <Edit className="w-3 h-3" />
                            </Button>
                          )}
                          {rec.status === "submitted" && isAdmin && (
                            <Button size="sm" variant="ghost" onClick={() => approveRecord(rec.record_id)}
                              className="text-green-600" data-testid={`approve-${rec.record_id}`}>
                              <CheckCircle className="w-3 h-3" />
                            </Button>
                          )}
                          {(rec.status === "approved" || rec.status === "locked") && (
                            <Button size="sm" variant="ghost" onClick={() => { setRecordForm({ ...rec }); setRecordEntries(rec.entries || []); setActiveTab("record-entry"); }}>
                              <Eye className="w-3 h-3" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {records.length === 0 && (
                    <tr><td colSpan={8} className="p-8 text-center text-muted-foreground">
                      No records found. Use the buttons above to create new records.
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ===== RECORD ENTRY TAB ===== */}
      {activeTab === "record-entry" && recordForm && (() => {
        const entryCols = templateColumns[recordForm.template_type] || columnsRef.current[recordForm.template_type] || [];
        const isReadOnly = recordForm.status === "locked" || recordForm.status === "approved";
        return (
        <div className="space-y-4">
          <Card className="border-2 border-primary">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Edit className="w-4 h-4" />
                  {recordForm.record_id ? `Edit Record: ${recordForm.record_id}` : `New ${typeLabel(recordForm.template_type)} Record`}
                </span>
                <Button variant="ghost" size="sm" onClick={() => { setRecordForm(null); setActiveTab("records"); }}>
                  <X className="w-4 h-4" />
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs">Record Date</Label>
                  <Input type="date" value={recordForm.record_date} className="text-xs"
                    onChange={e => setRecordForm(p => ({ ...p, record_date: e.target.value }))} data-testid="record-date" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Period</Label>
                  <select value={recordForm.period}
                    onChange={e => setRecordForm(p => ({ ...p, period: e.target.value }))}
                    className="w-full h-10 px-2 rounded-md border border-input bg-background text-xs">
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>
                <div className="space-y-1 col-span-2">
                  <Label className="text-xs">Notes</Label>
                  <Input value={recordForm.notes} onChange={e => setRecordForm(p => ({ ...p, notes: e.target.value }))}
                    placeholder="Optional notes" className="text-xs" />
                </div>
              </div>

              {/* Entry rows */}
              {entryCols.length === 0 ? (
                <div className="p-6 text-center border rounded-lg bg-muted/30">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">Loading template columns...</p>
                </div>
              ) : (
              <div className="border rounded-lg overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted">
                      <tr>
                        <th className="p-2 text-center w-10">#</th>
                        {entryCols.map(col => (
                          <th key={col.key} className="p-2 text-left text-xs font-bold whitespace-nowrap">
                            {col.label} {col.required && <span className="text-red-500">*</span>}
                          </th>
                        ))}
                        <th className="p-2 w-10"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {recordEntries.map((entry, rowIdx) => (
                        <tr key={rowIdx} className="border-t" data-testid={`entry-row-${rowIdx}`}>
                          <td className="p-2 text-center text-xs text-muted-foreground">{rowIdx + 1}</td>
                          {entryCols.map(col => (
                            <td key={col.key} className="p-1">
                              {col.type === "textarea" ? (
                                <Textarea value={entry[col.key] || ""} rows={1} className="text-xs min-w-[120px]"
                                  onChange={e => updateEntry(rowIdx, col.key, e.target.value)}
                                  disabled={isReadOnly} />
                              ) : col.type === "select" ? (
                                <select value={entry[col.key] || ""}
                                  onChange={e => updateEntry(rowIdx, col.key, e.target.value)}
                                  disabled={isReadOnly}
                                  className="h-8 px-1 rounded border border-input bg-background text-xs min-w-[100px]">
                                  <option value="">Select</option>
                                  {(col.options || []).map(o => <option key={o} value={o}>{o}</option>)}
                                </select>
                              ) : col.type === "check" ? (
                                <div className="flex justify-center">
                                  <Checkbox checked={entry[col.key] === true || entry[col.key] === "true"}
                                    onCheckedChange={v => updateEntry(rowIdx, col.key, v)}
                                    disabled={isReadOnly} />
                                </div>
                              ) : (
                                <Input value={entry[col.key] || ""} className="text-xs h-8 min-w-[80px]"
                                  type={col.type === "number" ? "number" : col.type === "date" ? "date" : col.type === "time" ? "time" : "text"}
                                  onChange={e => updateEntry(rowIdx, col.key, e.target.value)}
                                  disabled={isReadOnly} />
                              )}
                            </td>
                          ))}
                          <td className="p-1">
                            {!isReadOnly && recordEntries.length > 1 && (
                              <Button size="sm" variant="ghost" onClick={() => removeEntryRow(rowIdx)}>
                                <X className="w-3 h-3 text-red-500" />
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              )}

              {!isReadOnly && (
                <Button onClick={addEntryRow} variant="outline" size="sm" data-testid="add-entry-row">
                  <Plus className="w-3 h-3 mr-1" /> Add Row
                </Button>
              )}

              {/* Action buttons */}
              {!isReadOnly && (
                <div className="flex gap-3 pt-3 border-t">
                  <Button onClick={() => saveRecord("draft")} variant="outline" disabled={loading} data-testid="save-draft-btn">
                    {loading && <Loader2 className="w-4 h-4 mr-1 animate-spin" />}
                    <Save className="w-4 h-4 mr-1" /> Save Draft
                  </Button>
                  <Button onClick={() => saveRecord("submitted")} disabled={loading} data-testid="submit-record-btn">
                    {loading && <Loader2 className="w-4 h-4 mr-1 animate-spin" />}
                    <CheckCircle className="w-4 h-4 mr-1" /> Submit Record
                  </Button>
                </div>
              )}

              {/* Submission info for approved/locked */}
              {isReadOnly && (
                <div className="p-3 bg-green-50 border border-green-200 rounded text-sm">
                  <p><strong>Submitted By:</strong> {recordForm.submittedBy || "N/A"} on {recordForm.submittedAt?.split("T")[0] || "N/A"}</p>
                  <p><strong>Approved By:</strong> {recordForm.approvedBy || "N/A"} on {recordForm.approvedAt?.split("T")[0] || "N/A"}</p>
                  <Badge className={STATUS_COLORS[recordForm.status]}>{recordForm.status.toUpperCase()}</Badge>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
        );
      })()}
    </div>
  );
}
