import { useState, useEffect } from "react";
import { useAuth } from "@/App";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  Loader2, 
  Building2, 
  Plus,
  Pencil,
  Trash2,
  Phone,
  Mail,
  MapPin,
  Lock
} from "lucide-react";

export default function CentersManagement() {
  const { session } = useAuth();
  const [centers, setCenters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Dialog states
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingCenter, setEditingCenter] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    code: "",
    name: "",
    phone: "",
    email: "",
    address: "",
    active: true,
    is_india_center: true
  });

  useEffect(() => {
    fetchCenters();
  }, []);

  const fetchCenters = async () => {
    setLoading(true);
    try {
      const res = await api.post("/mgt/centers", { token: session.token });
      setCenters(res.data.centers || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to fetch centers");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      code: "",
      name: "",
      phone: "",
      email: "",
      address: "",
      active: true,
      is_india_center: true
    });
  };

  const handleAdd = async () => {
    if (!formData.code || !formData.name) {
      toast.error("Code and Name are required");
      return;
    }
    
    setSaving(true);
    try {
      await api.post("/mgt/center_create", {
        token: session.token,
        ...formData
      });
      toast.success("Center created successfully!");
      setShowAddDialog(false);
      resetForm();
      fetchCenters();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to create center");
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (center) => {
    setEditingCenter(center);
    setFormData({
      code: center.code,
      name: center.name || "",
      phone: center.phone || "",
      email: center.email || "",
      address: center.address || "",
      active: center.active !== false,
      is_india_center: center.is_india_center !== false
    });
    setShowEditDialog(true);
  };

  const handleUpdate = async () => {
    if (!formData.name) {
      toast.error("Name is required");
      return;
    }
    
    setSaving(true);
    try {
      await api.post("/mgt/center_update", {
        token: session.token,
        ...formData
      });
      toast.success("Center updated successfully!");
      setShowEditDialog(false);
      setEditingCenter(null);
      resetForm();
      fetchCenters();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to update center");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (code) => {
    if (!confirm(`Are you sure you want to delete center "${code}"?`)) return;
    
    try {
      await api.post("/mgt/center_delete", {
        token: session.token,
        code
      });
      toast.success("Center deleted successfully!");
      fetchCenters();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to delete center");
    }
  };

  if (!session) {
    return (
      <div className="text-center py-20">
        <Lock className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
        <h2 className="text-2xl font-bold text-muted-foreground">Access Denied</h2>
        <p className="text-muted-foreground mt-2">Please login to manage centers</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-primary" data-testid="centers-page-title">
            Centers Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage all Purnabramha centers and their contact details
          </p>
        </div>
        
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button data-testid="add-center-btn" onClick={() => { resetForm(); setShowAddDialog(true); }}>
              <Plus className="w-4 h-4 mr-2" />
              Add Center
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Add New Center</DialogTitle>
              <DialogDescription>Enter the details for the new center</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Center Code *</Label>
                <Input
                  data-testid="center-code-input"
                  value={formData.code}
                  onChange={(e) => setFormData({...formData, code: e.target.value.toUpperCase()})}
                  placeholder="e.g., PB-NEW"
                />
              </div>
              <div className="space-y-2">
                <Label>Center Name *</Label>
                <Input
                  data-testid="center-name-input"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  placeholder="e.g., Purnabramha New Location"
                />
              </div>
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input
                  data-testid="center-phone-input"
                  value={formData.phone}
                  onChange={(e) => setFormData({...formData, phone: e.target.value})}
                  placeholder="+91 XXXXX XXXXX"
                />
              </div>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input
                  data-testid="center-email-input"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  placeholder="center@purnabramha.com"
                />
              </div>
              <div className="space-y-2">
                <Label>Address</Label>
                <Input
                  data-testid="center-address-input"
                  value={formData.address}
                  onChange={(e) => setFormData({...formData, address: e.target.value})}
                  placeholder="Full address"
                />
              </div>
              <div className="flex items-center justify-between">
                <Label>Active</Label>
                <Switch
                  checked={formData.active}
                  onCheckedChange={(checked) => setFormData({...formData, active: checked})}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label>Is India Center?</Label>
                <Switch
                  data-testid="is-india-center-toggle"
                  checked={formData.is_india_center}
                  onCheckedChange={(checked) => setFormData({...formData, is_india_center: checked})}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowAddDialog(false)}>Cancel</Button>
              <Button onClick={handleAdd} disabled={saving} data-testid="save-center-btn">
                {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                Create Center
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Centers Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="w-5 h-5" />
            All Centers ({centers.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : (
            <ScrollArea className="h-[500px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Code</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Contact</TableHead>
                    <TableHead>Address</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {centers.map((center) => (
                    <TableRow key={center.code} data-testid={`center-row-${center.code}`}>
                      <TableCell>
                        <Badge variant="outline" className="font-mono">
                          {center.code}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">{center.name}</TableCell>
                      <TableCell>
                        <div className="space-y-1 text-sm">
                          {center.phone && (
                            <div className="flex items-center gap-1 text-muted-foreground">
                              <Phone className="w-3 h-3" />
                              {center.phone}
                            </div>
                          )}
                          {center.email && (
                            <div className="flex items-center gap-1 text-muted-foreground">
                              <Mail className="w-3 h-3" />
                              {center.email}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        {center.address && (
                          <div className="flex items-center gap-1 text-sm text-muted-foreground max-w-[200px] truncate">
                            <MapPin className="w-3 h-3 flex-shrink-0" />
                            <span className="truncate">{center.address}</span>
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={center.active !== false ? "default" : "secondary"}>
                          {center.active !== false ? "Active" : "Inactive"}
                        </Badge>
                        {center.is_india_center === false && (
                          <Badge variant="outline" className="ml-1 text-xs">Intl</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(center)}
                            data-testid={`edit-center-${center.code}`}
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                          {center.code !== "PB-MGT" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-destructive hover:text-destructive"
                              onClick={() => handleDelete(center.code)}
                              data-testid={`delete-center-${center.code}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Center - {editingCenter?.code}</DialogTitle>
            <DialogDescription>Update center details</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Center Code</Label>
              <Input value={formData.code} disabled className="bg-muted" />
            </div>
            <div className="space-y-2">
              <Label>Center Name *</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                placeholder="e.g., Purnabramha New Location"
              />
            </div>
            <div className="space-y-2">
              <Label>Phone</Label>
              <Input
                value={formData.phone}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
                placeholder="+91 XXXXX XXXXX"
              />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                placeholder="center@purnabramha.com"
              />
            </div>
            <div className="space-y-2">
              <Label>Address</Label>
              <Input
                value={formData.address}
                onChange={(e) => setFormData({...formData, address: e.target.value})}
                placeholder="Full address"
              />
            </div>
            <div className="flex items-center justify-between">
              <Label>Active</Label>
              <Switch
                checked={formData.active}
                onCheckedChange={(checked) => setFormData({...formData, active: checked})}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label>Is India Center?</Label>
              <Switch
                checked={formData.is_india_center}
                onCheckedChange={(checked) => setFormData({...formData, is_india_center: checked})}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>Cancel</Button>
            <Button onClick={handleUpdate} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Update Center
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
