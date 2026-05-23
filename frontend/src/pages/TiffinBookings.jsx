import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Utensils, Plus, Edit, Trash2, Search, Download, Loader2, RefreshCw,
} from "lucide-react";
import { toast } from "sonner";
import MenuPicker from "@/components/booking/MenuPicker";

const API = process.env.REACT_APP_BACKEND_URL;

const MEAL_TYPES = ["Lunch", "Dinner", "Both"];
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const DELIVERY_MODES = ["Delivery", "Pickup"];
const PAYMENT_STATUSES = ["Pending", "Partial", "Paid"];
const BOOKING_STATUSES = ["Confirmed", "Active", "Paused", "Completed", "Cancelled"];

const today = () => new Date().toISOString().split("T")[0];
const plusDays = (n) => { const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().split("T")[0]; };

const blankForm = {
  customer_name: "", phone: "", email: "", customer_code: "",
  start_date: today(), end_date: plusDays(30),
  meal_type: "Both", selected_days: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
  selected_items: [], delivery_mode: "Delivery", delivery_time: "", delivery_address: "",
  subtotal: 0, gst: 0, total: 0,
  notes: "", payment_status: "Pending", booking_status: "Confirmed", assigned_staff: "",
  center: "",
};

export default function TiffinBookings() {
  const { session } = useAuth();
  const token = session?.token;
  const isAdmin = session?.is_super_admin || session?.is_admin;
  const userCenter = session?.center || "";

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [centers, setCenters] = useState([]);
  const [menuMaster, setMenuMaster] = useState([]);
  const [filters, setFilters] = useState({
    center: isAdmin ? "" : userCenter,
    from_date: plusDays(-30), to_date: plusDays(60),
    status: "", search: "",
  });
  const [showDlg, setShowDlg] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ ...blankForm, center: userCenter });

  // Load centers + menu master
  useEffect(() => {
    if (!token) return;
    fetch(`${API}/api/sales/centers-list`).then(r => r.ok && r.json()).then((d) => {
      if (d?.centers) setCenters(d.centers);
    });
    fetch(`${API}/api/bookings/ext/menu/list`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    }).then(r => r.ok && r.json()).then((d) => {
      if (d?.items) setMenuMaster(d.items);
    });
  }, [token]);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const body = {
        token,
        centers: filters.center ? [filters.center] : [],
        from_date: filters.from_date || null,
        to_date: filters.to_date || null,
        status: filters.status || null,
        search: filters.search || null,
      };
      const res = await fetch(`${API}/api/bookings/ext/tiffin/list`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      if (res.ok) setRows((await res.json()).rows || []);
    } finally { setLoading(false); }
  }, [token, filters]);

  useEffect(() => { load(); }, [load]);

  const open = (row) => {
    if (row) { setEditing(row); setForm({ ...blankForm, ...row }); }
    else { setEditing(null); setForm({ ...blankForm, center: userCenter }); }
    setShowDlg(true);
  };

  const save = async () => {
    if (!form.customer_name || !form.phone) { toast.error("Customer name and phone required"); return; }
    if (!form.center) { toast.error("Center required"); return; }
    const url = editing
      ? `${API}/api/bookings/ext/tiffin/update/${editing.id}`
      : `${API}/api/bookings/ext/tiffin/create`;
    const res = await fetch(url, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, ...form }),
    });
    if (res.ok) {
      toast.success(editing ? "Updated" : "Tiffin booking created");
      setShowDlg(false); load();
    } else {
      const e = await res.json().catch(() => ({}));
      toast.error(e.detail || "Failed");
    }
  };

  const del = async (row) => {
    if (!window.confirm(`Delete tiffin booking ${row.id}?`)) return;
    const res = await fetch(`${API}/api/bookings/ext/tiffin/delete/${row.id}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }),
    });
    if (res.ok) { toast.success("Deleted"); load(); }
  };

  const downloadPdf = async (row) => {
    const res = await fetch(`${API}/api/bookings/ext/tiffin/pdf/${row.id}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }),
    });
    if (!res.ok) { toast.error("PDF failed"); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `tiffin_${row.id}.pdf`;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  };

  const masterByCat = menuMaster.reduce((acc, m) => {
    (acc[m.category] = acc[m.category] || []).push(m); return acc;
  }, {});

  return (
    <div className="space-y-6" data-testid="tiffin-bookings-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <Utensils className="w-7 h-7" />Tiffin Bookings
          </h1>
          <p className="text-muted-foreground text-sm">
            Subscriptions, daily tiffins, customer-managed pricing.
          </p>
        </div>
        <Button onClick={() => open(null)} data-testid="tiffin-new-btn">
          <Plus className="w-4 h-4 mr-2" /> New Tiffin Booking
        </Button>
      </div>

      <Card><CardContent className="p-4 grid grid-cols-2 md:grid-cols-5 gap-3">
        {isAdmin && (
          <div>
            <Label className="text-xs">Center</Label>
            <Select value={filters.center || "all"} onValueChange={(v) => setFilters(f => ({ ...f, center: v === "all" ? "" : v }))}>
              <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Centers</SelectItem>
                {centers.map(c => <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        )}
        <div><Label className="text-xs">From</Label>
          <Input className="h-9" type="date" value={filters.from_date}
            onChange={(e) => setFilters(f => ({ ...f, from_date: e.target.value }))} />
        </div>
        <div><Label className="text-xs">To</Label>
          <Input className="h-9" type="date" value={filters.to_date}
            onChange={(e) => setFilters(f => ({ ...f, to_date: e.target.value }))} />
        </div>
        <div><Label className="text-xs">Status</Label>
          <Select value={filters.status || "all"} onValueChange={(v) => setFilters(f => ({ ...f, status: v === "all" ? "" : v }))}>
            <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              {BOOKING_STATUSES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div><Label className="text-xs">Search</Label>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-2 top-2.5 text-muted-foreground" />
            <Input className="h-9 pl-8" placeholder="Name / Phone / ID..." value={filters.search}
              onChange={(e) => setFilters(f => ({ ...f, search: e.target.value }))} />
          </div>
        </div>
      </CardContent></Card>

      <Card><CardContent className="p-0">
        {loading ? (
          <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>
        ) : rows.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">No tiffin bookings.</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Period</TableHead>
                <TableHead>Meal</TableHead>
                <TableHead>Total</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Center</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.id} data-testid={`tiffin-row-${r.id}`}>
                  <TableCell className="text-xs">{r.id}</TableCell>
                  <TableCell>
                    <div className="font-medium">{r.customer_name}</div>
                    <div className="text-xs text-muted-foreground">{r.phone}</div>
                  </TableCell>
                  <TableCell className="text-xs">{r.start_date}<br />→ {r.end_date}</TableCell>
                  <TableCell><Badge variant="outline">{r.meal_type}</Badge></TableCell>
                  <TableCell>{Number(r.total || 0).toFixed(2)}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{r.booking_status}</Badge>
                    <div className="text-xs mt-1">{r.payment_status}</div>
                  </TableCell>
                  <TableCell className="text-xs">{r.center}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button size="icon" variant="ghost" onClick={() => open(r)}><Edit className="w-4 h-4" /></Button>
                      <Button size="icon" variant="ghost" onClick={() => downloadPdf(r)}><Download className="w-4 h-4" /></Button>
                      {isAdmin && <Button size="icon" variant="ghost" onClick={() => del(r)}><Trash2 className="w-4 h-4 text-red-500" /></Button>}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent></Card>

      {/* Form Dialog */}
      <Dialog open={showDlg} onOpenChange={setShowDlg}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editing ? `Edit ${editing.id}` : "New Tiffin Booking"}</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Customer Name *</Label><Input value={form.customer_name} onChange={(e) => setForm(f => ({ ...f, customer_name: e.target.value }))} data-testid="tiffin-customer-name" /></div>
              <div><Label>Phone *</Label><Input value={form.phone} onChange={(e) => setForm(f => ({ ...f, phone: e.target.value }))} /></div>
              <div><Label>Email</Label><Input value={form.email} onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))} /></div>
              <div><Label>Customer Code</Label><Input value={form.customer_code} onChange={(e) => setForm(f => ({ ...f, customer_code: e.target.value }))} /></div>
              {isAdmin && (
                <div className="col-span-2">
                  <Label>Center *</Label>
                  <Select value={form.center} onValueChange={(v) => setForm(f => ({ ...f, center: v }))}>
                    <SelectTrigger><SelectValue placeholder="Pick center..." /></SelectTrigger>
                    <SelectContent>{centers.map(c => <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              )}
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div><Label>Start Date</Label><Input type="date" value={form.start_date} onChange={(e) => setForm(f => ({ ...f, start_date: e.target.value }))} /></div>
              <div><Label>End Date</Label><Input type="date" value={form.end_date} onChange={(e) => setForm(f => ({ ...f, end_date: e.target.value }))} /></div>
              <div><Label>Meal Type</Label>
                <Select value={form.meal_type} onValueChange={(v) => setForm(f => ({ ...f, meal_type: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{MEAL_TYPES.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label>Days of Week</Label>
              <div className="flex gap-2 flex-wrap mt-1">
                {DAYS.map(d => (
                  <Badge key={d}
                    variant={form.selected_days.includes(d) ? "default" : "outline"}
                    className="cursor-pointer"
                    onClick={() => setForm(f => ({
                      ...f,
                      selected_days: f.selected_days.includes(d)
                        ? f.selected_days.filter(x => x !== d)
                        : [...f.selected_days, d],
                    }))}>{d}</Badge>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div><Label>Delivery Mode</Label>
                <Select value={form.delivery_mode} onValueChange={(v) => setForm(f => ({ ...f, delivery_mode: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{DELIVERY_MODES.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label>Delivery Time</Label><Input value={form.delivery_time} placeholder="12:30 PM" onChange={(e) => setForm(f => ({ ...f, delivery_time: e.target.value }))} /></div>
              <div><Label>Assigned Staff</Label><Input value={form.assigned_staff} onChange={(e) => setForm(f => ({ ...f, assigned_staff: e.target.value }))} /></div>
            </div>

            <div>
              <Label>Delivery Address</Label>
              <Textarea rows={2} value={form.delivery_address} onChange={(e) => setForm(f => ({ ...f, delivery_address: e.target.value }))} />
            </div>

            <MenuPicker
              title="Tiffin Items (hybrid pick + custom)"
              category="Tiffin Item"
              rows={form.selected_items}
              onChange={(rows) => setForm(f => ({ ...f, selected_items: rows }))}
              master={[...(masterByCat["Tiffin Item"] || []), ...(masterByCat["Main Course"] || [])]}
              testIdPrefix="tiffin-items"
            />

            <div className="grid grid-cols-3 gap-3 bg-muted/30 p-3 rounded">
              <div><Label className="text-xs">Subtotal</Label>
                <Input type="number" value={form.subtotal}
                  onChange={(e) => setForm(f => ({ ...f, subtotal: Number(e.target.value) || 0 }))}
                  data-testid="tiffin-subtotal" /></div>
              <div><Label className="text-xs">GST</Label>
                <Input type="number" value={form.gst}
                  onChange={(e) => setForm(f => ({ ...f, gst: Number(e.target.value) || 0 }))} /></div>
              <div><Label className="text-xs">Total</Label>
                <Input type="number" value={form.total}
                  onChange={(e) => setForm(f => ({ ...f, total: Number(e.target.value) || 0 }))}
                  data-testid="tiffin-total" /></div>
              <div className="col-span-3 text-xs text-muted-foreground italic">
                Free-form pricing — type Subtotal / GST / Total manually as per agreed plan.
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div><Label>Booking Status</Label>
                <Select value={form.booking_status} onValueChange={(v) => setForm(f => ({ ...f, booking_status: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{BOOKING_STATUSES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label>Payment Status</Label>
                <Select value={form.payment_status} onValueChange={(v) => setForm(f => ({ ...f, payment_status: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{PAYMENT_STATUSES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>

            <div><Label>Notes</Label>
              <Textarea rows={2} value={form.notes} onChange={(e) => setForm(f => ({ ...f, notes: e.target.value }))} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDlg(false)}>Cancel</Button>
            <Button onClick={save} data-testid="tiffin-save-btn">{editing ? "Update" : "Create"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
