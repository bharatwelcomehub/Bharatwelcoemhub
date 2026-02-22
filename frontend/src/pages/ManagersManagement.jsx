import { useState, useEffect } from "react";
import { useAuth } from "@/App";
import { api, CENTERS } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Loader2, 
  Users2, 
  Plus,
  Pencil,
  Trash2,
  Phone,
  Mail,
  Building2,
  Lock
} from "lucide-react";

export default function ManagersManagement() {
  const { session } = useAuth();
  const [managers, setManagers] = useState([]);
  const [centers, setCenters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Dialog states
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingManager, setEditingManager] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    center: "",
    managerName: "",
    mobile: "",
    email: "",
    active: true,
    otpChannel: "email"
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [managersRes, centersRes] = await Promise.all([
        api.post("/mgt/managers", { token: session.token }),
        api.post("/mgt/centers", { token: session.token })
      ]);
      setManagers(managersRes.data.managers || []);
      setCenters(centersRes.data.centers || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to fetch data");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      center: "",
      managerName: "",
      mobile: "",
      email: "",
      active: true,
      otpChannel: "email"
    });
  };

  const handleAdd = async () => {
    if (!formData.center || !formData.email) {
      toast.error("Center and Email are required");
      return;
    }
    
    setSaving(true);
    try {
      await api.post("/mgt/manager_create", {
        token: session.token,
        ...formData
      });
      toast.success("Manager created successfully!");
      setShowAddDialog(false);
      resetForm();
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to create manager");
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (manager) => {
    setEditingManager(manager);
    setFormData({
      center: manager.center || "",
      managerName: manager.managerName || "",
      mobile: manager.mobile || "",
      email: manager.email || "",
      active: manager.active !== false,
      otpChannel: manager.otpChannel || "email"
    });
    setShowEditDialog(true);
  };

  const handleUpdate = async () => {
    setSaving(true);
    try {
      await api.post("/mgt/manager_update", {
        token: session.token,
        ...formData
      });
      toast.success("Manager updated successfully!");
      setShowEditDialog(false);
      setEditingManager(null);
      resetForm();
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to update manager");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (email) => {
    if (!confirm(`Are you sure you want to delete manager "${email}"?`)) return;
    
    try {
      await api.post("/mgt/manager_delete", {
        token: session.token,
        email
      });
      toast.success("Manager deleted successfully!");
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to delete manager");
    }
  };

  // Group managers by center
  const managersByCenter = managers.reduce((acc, manager) => {
    const center = manager.center || "Unknown";
    if (!acc[center]) acc[center] = [];
    acc[center].push(manager);
    return acc;
  }, {});

  if (session?.center !== "PB-MGT") {
    return (
      <div className="text-center py-20">
        <Lock className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
        <h2 className="text-2xl font-bold text-muted-foreground">Access Denied</h2>
        <p className="text-muted-foreground mt-2">Only PB-MGT can manage managers</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-primary" data-testid="managers-page-title">
            Managers Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage all center managers and their login credentials
          </p>
        </div>
        
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button data-testid="add-manager-btn" onClick={() => { resetForm(); setShowAddDialog(true); }}>
              <Plus className="w-4 h-4 mr-2" />
              Add Manager
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Add New Manager</DialogTitle>
              <DialogDescription>Enter the details for the new manager</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Center *</Label>
                <Select value={formData.center} onValueChange={(v) => setFormData({...formData, center: v})}>
                  <SelectTrigger data-testid="manager-center-select">
                    <SelectValue placeholder="Select center" />
                  </SelectTrigger>
                  <SelectContent>
                    {centers.map(c => (
                      <SelectItem key={c.code} value={c.code}>
                        {c.code} - {c.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Manager Name</Label>
                <Input
                  data-testid="manager-name-input"
                  value={formData.managerName}
                  onChange={(e) => setFormData({...formData, managerName: e.target.value})}
                  placeholder="Full name"
                />
              </div>
              <div className="space-y-2">
                <Label>Mobile</Label>
                <Input
                  data-testid="manager-mobile-input"
                  value={formData.mobile}
                  onChange={(e) => setFormData({...formData, mobile: e.target.value})}
                  placeholder="91XXXXXXXXXX"
                />
              </div>
              <div className="space-y-2">
                <Label>Email *</Label>
                <Input
                  data-testid="manager-email-input"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  placeholder="manager@purnabramha.com"
                />
                <p className="text-xs text-muted-foreground">OTP will be sent to this email for login</p>
              </div>
              <div className="flex items-center justify-between">
                <Label>Active</Label>
                <Switch
                  checked={formData.active}
                  onCheckedChange={(checked) => setFormData({...formData, active: checked})}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowAddDialog(false)}>Cancel</Button>
              <Button onClick={handleAdd} disabled={saving} data-testid="save-manager-btn">
                {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                Create Manager
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                <Users2 className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Managers</p>
                <p className="text-2xl font-bold">{managers.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-green-500/10 flex items-center justify-center">
                <Users2 className="w-6 h-6 text-green-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Active Managers</p>
                <p className="text-2xl font-bold">{managers.filter(m => m.active !== false).length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-orange-500/10 flex items-center justify-center">
                <Building2 className="w-6 h-6 text-orange-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Centers with Managers</p>
                <p className="text-2xl font-bold">{Object.keys(managersByCenter).length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Managers Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users2 className="w-5 h-5" />
            All Managers
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
                    <TableHead>Center</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Contact</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {managers.map((manager, idx) => (
                    <TableRow key={`${manager.email}-${idx}`} data-testid={`manager-row-${idx}`}>
                      <TableCell>
                        <Badge variant="outline" className="font-mono">
                          {manager.center}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">{manager.managerName || "N/A"}</TableCell>
                      <TableCell>
                        <div className="space-y-1 text-sm">
                          {manager.mobile && (
                            <div className="flex items-center gap-1 text-muted-foreground">
                              <Phone className="w-3 h-3" />
                              {manager.mobile}
                            </div>
                          )}
                          {manager.email && (
                            <div className="flex items-center gap-1 text-muted-foreground">
                              <Mail className="w-3 h-3" />
                              {manager.email}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={manager.active !== false ? "default" : "secondary"}>
                          {manager.active !== false ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(manager)}
                            data-testid={`edit-manager-${idx}`}
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-destructive hover:text-destructive"
                            onClick={() => handleDelete(manager.email)}
                            data-testid={`delete-manager-${idx}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
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
            <DialogTitle>Edit Manager</DialogTitle>
            <DialogDescription>Update manager details</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Center</Label>
              <Select value={formData.center} onValueChange={(v) => setFormData({...formData, center: v})}>
                <SelectTrigger>
                  <SelectValue placeholder="Select center" />
                </SelectTrigger>
                <SelectContent>
                  {centers.map(c => (
                    <SelectItem key={c.code} value={c.code}>
                      {c.code} - {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Manager Name</Label>
              <Input
                value={formData.managerName}
                onChange={(e) => setFormData({...formData, managerName: e.target.value})}
                placeholder="Full name"
              />
            </div>
            <div className="space-y-2">
              <Label>Mobile</Label>
              <Input
                value={formData.mobile}
                onChange={(e) => setFormData({...formData, mobile: e.target.value})}
                placeholder="91XXXXXXXXXX"
              />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                type="email"
                value={formData.email}
                disabled
                className="bg-muted"
              />
              <p className="text-xs text-muted-foreground">Email cannot be changed (used for identification)</p>
            </div>
            <div className="flex items-center justify-between">
              <Label>Active</Label>
              <Switch
                checked={formData.active}
                onCheckedChange={(checked) => setFormData({...formData, active: checked})}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>Cancel</Button>
            <Button onClick={handleUpdate} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Update Manager
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
