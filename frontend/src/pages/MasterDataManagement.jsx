import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import {
  Database, Plus, Pencil, Trash2, RefreshCw, Search, Download, Upload, 
  CheckCircle, XCircle, Loader2, Settings2
} from "lucide-react";

export default function MasterDataManagement() {
  const { session } = useAuth();
  const [masterTypes, setMasterTypes] = useState([]);
  const [selectedType, setSelectedType] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  
  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState("create"); // create | edit
  const [formData, setFormData] = useState({});
  const [saving, setSaving] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState("");
  const [selectedFields, setSelectedFields] = useState([]);

  // Load master types
  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get(`/masters/types?token=${session.token}`);
        setMasterTypes(res.data.master_types || []);
        if (res.data.master_types?.length > 0 && !selectedType) {
          setSelectedType(res.data.master_types[0].key);
        }
      } catch (err) {
        toast.error("Failed to load master types");
      }
    };
    if (session?.token) load();
  }, [session?.token]);

  // Load items for selected type
  const loadItems = useCallback(async () => {
    if (!selectedType || !session?.token) return;
    setLoading(true);
    try {
      const res = await api.post(`/masters/${selectedType}/list`, {
        token: session.token,
        active_only: !showInactive
      });
      setItems(res.data.items || []);
      setSelectedLabel(res.data.label || selectedType);
      
      const typeInfo = masterTypes.find(t => t.key === selectedType);
      setSelectedFields(typeInfo?.fields || ["name", "description"]);
    } catch (err) {
      toast.error("Failed to load items");
    } finally {
      setLoading(false);
    }
  }, [selectedType, session?.token, showInactive, masterTypes]);

  useEffect(() => { loadItems(); }, [loadItems]);

  const openCreate = () => {
    setFormData({ name: "", description: "", is_active: true });
    setDialogMode("create");
    setDialogOpen(true);
  };

  const openEdit = (item) => {
    setFormData({ ...item });
    setDialogMode("edit");
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const endpoint = dialogMode === "create" ? "create" : "update";
      await api.post(`/masters/${selectedType}/${endpoint}`, {
        token: session.token,
        ...formData
      });
      toast.success(dialogMode === "create" ? "Created successfully" : "Updated successfully");
      setDialogOpen(false);
      loadItems();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (name) => {
    if (!confirm(`Deactivate "${name}"?`)) return;
    try {
      await api.post(`/masters/${selectedType}/delete`, { token: session.token, name });
      toast.success("Deactivated");
      loadItems();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed");
    }
  };

  const handleSeedAll = async () => {
    if (!confirm("Seed master data from existing system data? This is safe and won't overwrite.")) return;
    setLoading(true);
    try {
      const res = await api.post("/masters/seed-from-existing", { token: session.token });
      const migrated = res.data.migrated || {};
      const total = Object.values(migrated).reduce((a, b) => a + b, 0);
      toast.success(`Seeded ${total} records across all masters`);
      loadItems();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Seed failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSeedRoles = async () => {
    try {
      await api.post("/permissions/roles/seed-defaults", { token: session.token });
      toast.success("Default roles seeded");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed");
    }
  };

  const filteredItems = items.filter(item => {
    if (!search) return true;
    const s = search.toLowerCase();
    return Object.values(item).some(v => String(v).toLowerCase().includes(s));
  });

  return (
    <div className="space-y-6" data-testid="master-data-management">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Database className="w-6 h-6 text-primary" />
            Master Data Management
          </h1>
          <p className="text-sm text-muted-foreground">Single source of truth — all dropdowns, filters, and reports pull from here</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleSeedAll} disabled={loading} data-testid="seed-masters-btn">
            <Upload className="w-4 h-4 mr-2" /> Seed from System
          </Button>
          <Button variant="outline" onClick={handleSeedRoles} data-testid="seed-roles-btn">
            <Settings2 className="w-4 h-4 mr-2" /> Seed Roles
          </Button>
        </div>
      </div>

      {/* Master Type Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {masterTypes.map(mt => (
          <Card 
            key={mt.key}
            className={`cursor-pointer transition-all hover:border-primary/50 ${selectedType === mt.key ? 'border-primary bg-primary/5' : 'border-border'}`}
            onClick={() => setSelectedType(mt.key)}
            data-testid={`master-type-${mt.key}`}
          >
            <CardContent className="pt-3 pb-3 text-center">
              <p className="text-xs font-semibold truncate">{mt.label}</p>
              <div className="flex justify-center gap-2 mt-1">
                <Badge variant="outline" className="text-[10px]">{mt.active_count} active</Badge>
                {mt.total_count > mt.active_count && (
                  <Badge variant="secondary" className="text-[10px]">{mt.total_count - mt.active_count} inactive</Badge>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Items Table */}
      {selectedType && (
        <Card className="bg-card border-border">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-lg">{selectedLabel}</CardTitle>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-xs">
                <Switch checked={showInactive} onCheckedChange={setShowInactive} />
                <span>Show Inactive</span>
              </div>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 w-4 h-4 text-muted-foreground" />
                <Input 
                  value={search} 
                  onChange={e => setSearch(e.target.value)} 
                  placeholder="Search..." 
                  className="pl-8 h-9 w-48"
                  data-testid="master-search"
                />
              </div>
              <Button onClick={() => loadItems()} variant="ghost" size="sm">
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
              <Button onClick={openCreate} size="sm" data-testid="master-create-btn">
                <Plus className="w-4 h-4 mr-1" /> Add
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-auto max-h-[500px]">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-card">
                  <tr className="border-b border-border">
                    <th className="text-left p-2 w-8">#</th>
                    {selectedFields.map(f => (
                      <th key={f} className="text-left p-2 capitalize">{f.replace(/_/g, ' ')}</th>
                    ))}
                    <th className="text-center p-2 w-20">Status</th>
                    <th className="text-center p-2 w-10">Updated</th>
                    <th className="text-center p-2 w-24">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredItems.map((item, idx) => (
                    <tr key={idx} className={`border-b border-border/50 hover:bg-muted/50 ${!item.is_active ? 'opacity-50' : ''}`}>
                      <td className="p-2 text-muted-foreground">{idx + 1}</td>
                      {selectedFields.map(f => (
                        <td key={f} className="p-2 max-w-[200px] truncate">{String(item[f] ?? "—")}</td>
                      ))}
                      <td className="p-2 text-center">
                        {item.is_active !== false ? (
                          <Badge className="bg-green-500/20 text-green-400 text-[10px]"><CheckCircle className="w-3 h-3 mr-1" />Active</Badge>
                        ) : (
                          <Badge variant="secondary" className="text-[10px]"><XCircle className="w-3 h-3 mr-1" />Inactive</Badge>
                        )}
                      </td>
                      <td className="p-2 text-center text-xs text-muted-foreground">{item.updated_by || "—"}</td>
                      <td className="p-2 text-center">
                        <div className="flex justify-center gap-1">
                          <Button variant="ghost" size="sm" onClick={() => openEdit(item)} className="h-7 w-7 p-0">
                            <Pencil className="w-3 h-3" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(item.name)} className="h-7 w-7 p-0 text-red-500">
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {filteredItems.length === 0 && (
                    <tr><td colSpan={selectedFields.length + 4} className="p-8 text-center text-muted-foreground">
                      {loading ? <Loader2 className="w-6 h-6 animate-spin mx-auto" /> : "No items found. Click 'Add' or 'Seed from System' to populate."}
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{dialogMode === "create" ? "Add" : "Edit"} {selectedLabel}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            {selectedFields.map(field => (
              <div key={field}>
                <label className="text-sm font-medium capitalize">{field.replace(/_/g, ' ')}</label>
                {typeof formData[field] === "boolean" ? (
                  <Switch checked={formData[field]} onCheckedChange={v => setFormData(prev => ({ ...prev, [field]: v }))} />
                ) : typeof formData[field] === "number" ? (
                  <Input type="number" value={formData[field] || ""} onChange={e => setFormData(prev => ({ ...prev, [field]: parseFloat(e.target.value) || 0 }))} />
                ) : (
                  <Input 
                    value={formData[field] || ""} 
                    onChange={e => setFormData(prev => ({ ...prev, [field]: e.target.value }))}
                    disabled={dialogMode === "edit" && field === "name"}
                    data-testid={`master-field-${field}`}
                  />
                )}
              </div>
            ))}
            <div className="flex items-center gap-2">
              <Switch checked={formData.is_active !== false} onCheckedChange={v => setFormData(prev => ({ ...prev, is_active: v }))} />
              <span className="text-sm">Active</span>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving} data-testid="master-save-btn">
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              {dialogMode === "create" ? "Create" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
