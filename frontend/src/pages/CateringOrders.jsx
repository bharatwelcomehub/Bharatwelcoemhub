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
  ChefHat, Plus, Edit, Trash2, Search, Download, Loader2,
} from "lucide-react";
import { toast } from "sonner";
import MenuPicker from "@/components/booking/MenuPicker";
import { isInternationalCenter } from "@/lib/api";

const API = process.env.REACT_APP_BACKEND_URL;

const STATUSES = ["Quote", "Confirmed", "Cancelled", "Completed"];
const PAY_STATUSES = ["Pending", "Partial", "Paid"];
const MENU_CATS = ["Starters", "Main Course", "Roti / Bread", "Rice / Biryani", "Dal", "Vegetable", "Sweet / Dessert", "Salad / Raita"];

const today = () => new Date().toISOString().split("T")[0];
const round2 = (n) => Math.round((Number(n) || 0) * 100) / 100;

const blankForm = {
  customer_name: "", phone: "", email: "",
  billing_address: "", delivery_address: "",
  order_date: today(), event_date: today(), event_time: "",
  guest_count: 50, occasion: "", package_name: "",
  per_person_rate: 0,
  menu_categories: {}, beverages: [], add_ons: [],
  crockery: "", staffing: "",
  transport_charges: 0,
  subtotal: 0, gst: 0, total: 0,
  advance_paid: 0, balance_due: 0,
  confirmation_status: "Quote", payment_status: "Pending",
  assigned_coordinator: "", quote_notes: "", remarks: "",
  center: "",
};

export default function CateringOrders() {
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
    from_date: "", to_date: "", status: "", search: "",
  });
  const [showDlg, setShowDlg] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ ...blankForm, center: userCenter });

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
      const res = await fetch(`${API}/api/bookings/ext/catering/list`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          centers: filters.center ? [filters.center] : [],
          from_date: filters.from_date || null,
          to_date: filters.to_date || null,
          status: filters.status || null,
          search: filters.search || null,
        }),
      });
      if (res.ok) setRows((await res.json()).rows || []);
    } finally { setLoading(false); }
  }, [token, filters]);

  useEffect(() => { load(); }, [load]);

  // Canonical inclusive-carve GST: India 5% / International 10%
  const recompute = (f) => {
    let lineTotal = 0;
    Object.values(f.menu_categories || {}).forEach((rows) => {
      rows.forEach((r) => { lineTotal += Number(r.amount) || 0; });
    });
    (f.beverages || []).forEach((r) => { lineTotal += Number(r.amount) || 0; });
    (f.add_ons || []).forEach((r) => { lineTotal += Number(r.amount) || 0; });
    // If line items absent, fall back to per_person × guest_count
    if (lineTotal === 0 && Number(f.per_person_rate) > 0) {
      lineTotal = Number(f.per_person_rate) * Number(f.guest_count || 0);
    }
    const transport = Number(f.transport_charges) || 0;
    const total = round2(lineTotal + transport);
    const isIntl = isInternationalCenter(f.center, centers);
    const rate = isIntl ? 0.10 : 0.05;
    const gst = round2(total - total / (1 + rate));
    const subtotal = round2(total - gst);
    const balance_due = round2(total - (Number(f.advance_paid) || 0));
    return { ...f, subtotal, gst, total, balance_due };
  };

  // Auto-recompute on key changes
  useEffect(() => {
    setForm((f) => recompute(f));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.menu_categories, form.beverages, form.add_ons,
      form.per_person_rate, form.guest_count, form.transport_charges,
      form.advance_paid, form.center, centers]);

  const open = (row) => {
    if (row) {
      setEditing(row);
      setForm(recompute({ ...blankForm, ...row }));
    } else {
      setEditing(null);
      setForm(recompute({ ...blankForm, center: userCenter }));
    }
    setShowDlg(true);
  };

  const save = async () => {
    if (!form.customer_name || !form.phone) { toast.error("Customer name and phone required"); return; }
    if (!form.center) { toast.error("Center required"); return; }
    const url = editing
      ? `${API}/api/bookings/ext/catering/update/${editing.id}`
      : `${API}/api/bookings/ext/catering/create`;
    const payload = recompute(form);
    const res = await fetch(url, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, ...payload }),
    });
    if (res.ok) {
      toast.success(editing ? "Updated" : "Catering order created");
      setShowDlg(false); load();
    } else {
      const e = await res.json().catch(() => ({}));
      toast.error(e.detail || "Failed");
    }
  };

  const del = async (row) => {
    if (!window.confirm(`Delete catering ${row.id}?`)) return;
    const res = await fetch(`${API}/api/bookings/ext/catering/delete/${row.id}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }),
    });
    if (res.ok) { toast.success("Deleted"); load(); }
  };

  const downloadPdf = async (row) => {
    const res = await fetch(`${API}/api/bookings/ext/catering/pdf/${row.id}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }),
    });
    if (!res.ok) { toast.error("PDF failed"); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `catering_${row.id}.pdf`;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  };

  const masterByCat = menuMaster.reduce((acc, m) => {
    (acc[m.category] = acc[m.category] || []).push(m); return acc;
  }, {});
  const isIntl = isInternationalCenter(form.center, centers);
  const currency = isIntl ? "$" : "₹";
  const gstLabel = isIntl ? "10% GST (incl.)" : "5% GST (incl.)";

  return (
    <div className="space-y-6" data-testid="catering-orders-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <ChefHat className="w-7 h-7" />Catering Orders
          </h1>
          <p className="text-muted-foreground text-sm">
            Quotes, confirmed orders, hybrid menu builder. GST = inclusive carve.
          </p>
        </div>
        <Button onClick={() => open(null)} data-testid="catering-new-btn">
          <Plus className="w-4 h-4 mr-2" /> New Catering Order
        </Button>
      </div>

      <Card><CardContent className="p-4 grid grid-cols-2 md:grid-cols-5 gap-3">
        {isAdmin && (
          <div><Label className="text-xs">Center</Label>
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
            onChange={(e) => setFilters(f => ({ ...f, from_date: e.target.value }))} /></div>
        <div><Label className="text-xs">To</Label>
          <Input className="h-9" type="date" value={filters.to_date}
            onChange={(e) => setFilters(f => ({ ...f, to_date: e.target.value }))} /></div>
        <div><Label className="text-xs">Status</Label>
          <Select value={filters.status || "all"} onValueChange={(v) => setFilters(f => ({ ...f, status: v === "all" ? "" : v }))}>
            <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              {STATUSES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div><Label className="text-xs">Search</Label>
          <Input className="h-9" placeholder="Name / Phone / ID..." value={filters.search}
            onChange={(e) => setFilters(f => ({ ...f, search: e.target.value }))} />
        </div>
      </CardContent></Card>

      <Card><CardContent className="p-0">
        {loading ? (
          <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>
        ) : rows.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">No catering orders.</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead><TableHead>Customer</TableHead>
                <TableHead>Event</TableHead><TableHead>Guests</TableHead>
                <TableHead>Total</TableHead><TableHead>Status</TableHead>
                <TableHead>Center</TableHead><TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.id} data-testid={`catering-row-${r.id}`}>
                  <TableCell className="text-xs">{r.id}</TableCell>
                  <TableCell>
                    <div className="font-medium">{r.customer_name}</div>
                    <div className="text-xs text-muted-foreground">{r.phone}</div>
                  </TableCell>
                  <TableCell className="text-xs">{r.event_date}<br />{r.event_time}<br />{r.occasion}</TableCell>
                  <TableCell>{r.guest_count}</TableCell>
                  <TableCell>{Number(r.total || 0).toFixed(2)}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{r.confirmation_status}</Badge>
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

      {/* Form */}
      <Dialog open={showDlg} onOpenChange={setShowDlg}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editing ? `Edit ${editing.id}` : "New Catering Order"}</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Customer Name *</Label><Input value={form.customer_name} onChange={(e) => setForm(f => ({ ...f, customer_name: e.target.value }))} data-testid="catering-customer-name" /></div>
              <div><Label>Phone *</Label><Input value={form.phone} onChange={(e) => setForm(f => ({ ...f, phone: e.target.value }))} /></div>
              <div><Label>Email</Label><Input value={form.email} onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))} /></div>
              {isAdmin && (
                <div>
                  <Label>Center *</Label>
                  <Select value={form.center} onValueChange={(v) => setForm(f => ({ ...f, center: v }))}>
                    <SelectTrigger><SelectValue placeholder="Pick center..." /></SelectTrigger>
                    <SelectContent>{centers.map(c => <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              )}
              <div className="col-span-2"><Label>Billing Address</Label><Textarea rows={2} value={form.billing_address} onChange={(e) => setForm(f => ({ ...f, billing_address: e.target.value }))} /></div>
              <div className="col-span-2"><Label>Delivery Address</Label><Textarea rows={2} value={form.delivery_address} onChange={(e) => setForm(f => ({ ...f, delivery_address: e.target.value }))} /></div>
            </div>

            <div className="grid grid-cols-4 gap-3">
              <div><Label>Order Date</Label><Input type="date" value={form.order_date} onChange={(e) => setForm(f => ({ ...f, order_date: e.target.value }))} /></div>
              <div><Label>Event Date *</Label><Input type="date" value={form.event_date} onChange={(e) => setForm(f => ({ ...f, event_date: e.target.value }))} /></div>
              <div><Label>Event Time</Label><Input value={form.event_time} placeholder="7:00 PM" onChange={(e) => setForm(f => ({ ...f, event_time: e.target.value }))} /></div>
              <div><Label>Guests</Label><Input type="number" value={form.guest_count} onChange={(e) => setForm(f => ({ ...f, guest_count: Number(e.target.value) || 0 }))} /></div>
              <div><Label>Occasion</Label><Input value={form.occasion} onChange={(e) => setForm(f => ({ ...f, occasion: e.target.value }))} placeholder="Wedding, Birthday..." /></div>
              <div><Label>Package</Label><Input value={form.package_name} onChange={(e) => setForm(f => ({ ...f, package_name: e.target.value }))} placeholder="Silver / Gold / Custom" /></div>
              <div><Label>Per-Person Rate</Label><Input type="number" value={form.per_person_rate} onChange={(e) => setForm(f => ({ ...f, per_person_rate: Number(e.target.value) || 0 }))} /></div>
              <div><Label>Coordinator</Label><Input value={form.assigned_coordinator} onChange={(e) => setForm(f => ({ ...f, assigned_coordinator: e.target.value }))} /></div>
            </div>

            {/* Hybrid menu picker per category */}
            <div className="space-y-3">
              <div className="font-medium text-sm">Menu (hybrid — pick from master OR type custom)</div>
              {MENU_CATS.map((cat) => (
                <MenuPicker key={cat}
                  category={cat}
                  rows={form.menu_categories[cat] || []}
                  onChange={(rows) => setForm(f => ({
                    ...f, menu_categories: { ...f.menu_categories, [cat]: rows },
                  }))}
                  master={masterByCat[cat] || []}
                  testIdPrefix={`catering-${cat.replace(/[^a-z]/gi, "")}`} />
              ))}
              <MenuPicker category="Beverages"
                rows={form.beverages}
                onChange={(rows) => setForm(f => ({ ...f, beverages: rows }))}
                master={masterByCat["Beverage"] || []}
                testIdPrefix="catering-bev" />
              <MenuPicker category="Add-ons"
                rows={form.add_ons}
                onChange={(rows) => setForm(f => ({ ...f, add_ons: rows }))}
                master={masterByCat["Add-on"] || []}
                testIdPrefix="catering-addon" />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div><Label>Crockery / Logistics</Label><Textarea rows={2} value={form.crockery} onChange={(e) => setForm(f => ({ ...f, crockery: e.target.value }))} /></div>
              <div><Label>Staffing / Service</Label><Textarea rows={2} value={form.staffing} onChange={(e) => setForm(f => ({ ...f, staffing: e.target.value }))} /></div>
            </div>

            {/* Totals — auto from canonical helper */}
            <div className="grid grid-cols-3 gap-3 bg-muted/30 p-3 rounded">
              <div><Label className="text-xs">Transport</Label>
                <Input type="number" value={form.transport_charges}
                  onChange={(e) => setForm(f => ({ ...f, transport_charges: Number(e.target.value) || 0 }))} /></div>
              <div><Label className="text-xs">Subtotal ({currency})</Label>
                <Input readOnly value={form.subtotal.toFixed(2)} /></div>
              <div><Label className="text-xs">{gstLabel}</Label>
                <Input readOnly value={form.gst.toFixed(2)} /></div>
              <div><Label className="text-xs">Advance Paid</Label>
                <Input type="number" value={form.advance_paid}
                  onChange={(e) => setForm(f => ({ ...f, advance_paid: Number(e.target.value) || 0 }))} /></div>
              <div><Label className="text-xs">Total ({currency})</Label>
                <Input readOnly className="font-bold" value={form.total.toFixed(2)} data-testid="catering-total" /></div>
              <div><Label className="text-xs">Balance Due ({currency})</Label>
                <Input readOnly value={form.balance_due.toFixed(2)} /></div>
              <div className="col-span-3 text-xs text-muted-foreground italic">
                GST = inclusive carve on Total. Single source of truth ({isIntl ? "Australia 10%" : "India 5%"}).
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div><Label>Confirmation Status</Label>
                <Select value={form.confirmation_status} onValueChange={(v) => setForm(f => ({ ...f, confirmation_status: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{STATUSES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label>Payment Status</Label>
                <Select value={form.payment_status} onValueChange={(v) => setForm(f => ({ ...f, payment_status: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{PAY_STATUSES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>

            <div><Label>Quote Notes</Label>
              <Textarea rows={2} value={form.quote_notes} onChange={(e) => setForm(f => ({ ...f, quote_notes: e.target.value }))} />
            </div>
            <div><Label>Internal Remarks</Label>
              <Textarea rows={2} value={form.remarks} onChange={(e) => setForm(f => ({ ...f, remarks: e.target.value }))} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDlg(false)}>Cancel</Button>
            <Button onClick={save} data-testid="catering-save-btn">{editing ? "Update" : "Create"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
