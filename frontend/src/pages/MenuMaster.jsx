import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Plus, Trash2, UtensilsCrossed, Loader2 } from "lucide-react";
import { toast } from "sonner";

const API = process.env.REACT_APP_BACKEND_URL;

const CATEGORIES = [
  "Starters", "Main Course", "Roti / Bread", "Rice / Biryani",
  "Dal", "Vegetable", "Sweet / Dessert", "Beverage",
  "Snacks / Chaat", "Salad / Raita", "Tiffin Item", "Add-on", "Other"
];

export default function MenuMaster() {
  const { session } = useAuth();
  const token = session?.token;
  const canWrite = session?.is_super_admin || session?.is_admin || session?.roles?.mgt || session?.roles?.operations;

  const [byCat, setByCat] = useState({});
  const [loading, setLoading] = useState(false);
  const [showDlg, setShowDlg] = useState(false);
  const [form, setForm] = useState({ name: "", category: "Main Course", default_rate: 0, is_active: true });

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/bookings/ext/menu/list`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });
      if (res.ok) {
        const d = await res.json();
        setByCat(d.by_category || {});
      }
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const upsert = async () => {
    if (!form.name.trim()) { toast.error("Name required"); return; }
    const res = await fetch(`${API}/api/bookings/ext/menu/upsert`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, item: { ...form, default_rate: Number(form.default_rate) || 0 } }),
    });
    if (res.ok) {
      toast.success("Saved");
      setShowDlg(false);
      setForm({ name: "", category: "Main Course", default_rate: 0, is_active: true });
      load();
    } else {
      const e = await res.json().catch(() => ({}));
      toast.error(e.detail || "Failed");
    }
  };

  const del = async (item) => {
    if (!window.confirm(`Delete "${item.name}"?`)) return;
    const res = await fetch(`${API}/api/bookings/ext/menu/delete`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, id: `${item.name}|${item.category}` }),
    });
    if (res.ok) { toast.success("Deleted"); load(); }
  };

  const totalItems = Object.values(byCat).reduce((s, arr) => s + arr.length, 0);

  return (
    <div className="space-y-6" data-testid="menu-master-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <UtensilsCrossed className="w-7 h-7" />
            Menu Master
          </h1>
          <p className="text-muted-foreground text-sm">
            Master list for Tiffin / Catering / Event menu picking. {totalItems} items.
          </p>
        </div>
        {canWrite && (
          <Button onClick={() => setShowDlg(true)} data-testid="menu-master-new-btn">
            <Plus className="w-4 h-4 mr-2" /> New Item
          </Button>
        )}
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>
      ) : (
        Object.keys(byCat).length === 0 ? (
          <Card><CardContent className="py-12 text-center text-muted-foreground">
            No menu items yet. Add the first one to enable hybrid menu selection.
          </CardContent></Card>
        ) : (
          CATEGORIES.filter(c => byCat[c]?.length).map((cat) => (
            <Card key={cat}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  {cat} <Badge variant="outline">{byCat[cat].length}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Item</TableHead>
                      <TableHead className="text-right">Default Rate</TableHead>
                      <TableHead className="w-20"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {byCat[cat].map((it) => (
                      <TableRow key={`${it.name}|${it.category}`}>
                        <TableCell>{it.name}</TableCell>
                        <TableCell className="text-right">{Number(it.default_rate || 0).toFixed(2)}</TableCell>
                        <TableCell>
                          {canWrite && (
                            <Button variant="ghost" size="icon" onClick={() => del(it)}>
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ))
        )
      )}

      <Dialog open={showDlg} onOpenChange={setShowDlg}>
        <DialogContent>
          <DialogHeader><DialogTitle>New / Edit Menu Item</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>Item Name *</Label>
              <Input value={form.name}
                onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
                data-testid="menu-master-name-input" />
            </div>
            <div>
              <Label>Category</Label>
              <Select value={form.category} onValueChange={(v) => setForm(f => ({ ...f, category: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Default Rate</Label>
              <Input type="number" value={form.default_rate}
                onChange={(e) => setForm(f => ({ ...f, default_rate: e.target.value }))} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDlg(false)}>Cancel</Button>
            <Button onClick={upsert} data-testid="menu-master-save-btn">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
