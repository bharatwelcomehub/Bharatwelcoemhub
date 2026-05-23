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
import { PartyPopper, Plus, Edit, Trash2, Download, Loader2, Mail, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import MenuPicker from "@/components/booking/MenuPicker";
import { isInternationalCenter } from "@/lib/api";

const API = process.env.REACT_APP_BACKEND_URL;

const EVENT_TYPES = [
  "Birthday", "Anniversary", "Engagement", "Wedding",
  "Baby Shower / Godbharai", "Kids Party", "Corporate Event",
  "Kitty Party", "Women's Meet", "Just Get-together", "Other",
];
const STATUSES = ["Quote", "Confirmed", "Cancelled", "Completed"];
const PAY_STATUSES = ["Pending", "Partial", "Paid"];
const MENU_CATS = ["Starters", "Main Course", "Roti / Bread", "Rice / Biryani", "Dal", "Vegetable", "Sweet / Dessert", "Salad / Raita"];
const DAL_OPTIONS = ["Dal Tadka", "Dal Fry", "Dal Makhani", "Yellow Dal", "Custom"];

const today = () => new Date().toISOString().split("T")[0];
const round2 = (n) => Math.round((Number(n) || 0) * 100) / 100;

const blankForm = {
  enquiry_id: "",
  customer_name: "", phone: "", email: "",
  event_type: "Birthday", event_date: today(), time_slot: "",
  guest_count: 20, package_name: "",
  dal_selection: "Dal Tadka",
  menu_categories: {},
  decoration: "", special_rules: "",
  estimated_total: 0, gst: 0, final_total: 0,
  advance_paid: 0, balance_due: 0,
  confirmation_status: "Quote", payment_status: "Pending",
  quotation_link: "", assigned_manager: "",
  center: "",
};

export default function EventBookings() {
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
      const res = await fetch(`${API}/api/bookings/ext/event/list`, {
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

  const recompute = (f) => {
    let lineTotal = 0;
    Object.values(f.menu_categories || {}).forEach((rows) => {
      rows.forEach((r) => { lineTotal += Number(r.amount) || 0; });
    });
    const finalTotal = round2(lineTotal);
    const isIntl = isInternationalCenter(f.center, centers);
    const rate = isIntl ? 0.10 : 0.05;
    const gst = round2(finalTotal - finalTotal / (1 + rate));
    const estimatedTotal = round2(finalTotal - gst);
    const balance_due = round2(finalTotal - (Number(f.advance_paid) || 0));
    return { ...f, estimated_total: estimatedTotal, gst, final_total: finalTotal, balance_due };
  };

  useEffect(() => {
    setForm((f) => recompute(f));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.menu_categories, form.advance_paid, form.center, centers]);

  const open = (row) => {
    if (row) { setEditing(row); setForm(recompute({ ...blankForm, ...row })); }
    else { setEditing(null); setForm(recompute({ ...blankForm, center: userCenter })); }
    setShowDlg(true);
  };

  const save = async () => {
    if (!form.customer_name || !form.phone) { toast.error("Customer name and phone required"); return; }
    if (!form.center) { toast.error("Center required"); return; }
    const url = editing
      ? `${API}/api/bookings/ext/event/update/${editing.id}`
      : `${API}/api/bookings/ext/event/create`;
    const payload = recompute(form);
    const res = await fetch(url, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, ...payload }),
    });
    if (res.ok) {
      toast.success(editing ? "Updated" : "Event booking created");
      setShowDlg(false); load();
    } else {
      const e = await res.json().catch(() => ({}));
      toast.error(e.detail || "Failed");
    }
  };

  const del = async (row) => {
    if (!window.confirm(`Delete event ${row.id}?`)) return;
    const res = await fetch(`${API}/api/bookings/ext/event/delete/${row.id}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }),
    });
    if (res.ok) { toast.success("Deleted"); load(); }
  };

  const downloadPdf = async (row) => {
    const res = await fetch(`${API}/api/bookings/ext/event/pdf/${row.id}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }),
    });
    if (!res.ok) { toast.error("PDF failed"); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `event_${row.id}.pdf`;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  };

  const sendQuote = async (row) => {
    if (!row.email) {
      const m = window.prompt("Customer email not set. Enter email to send to:");
      if (!m) return;
      row = { ...row, email: m };
    }
    const t = toast.loading(`Emailing quote to ${row.email}...`);
    try {
      const res = await fetch(`${API}/api/bookings/ext/event/send-quote/${row.id}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, to_email: row.email }),
      });
      if (res.ok) {
        const d = await res.json();
        toast.success(`Quote sent to ${d.to} (${d.size_kb} KB)`, { id: t });
        load();
      } else {
        const e = await res.json().catch(() => ({}));
        toast.error(e.detail || "Send failed", { id: t });
      }
    } catch (err) {
      toast.error("Network error", { id: t });
    }
  };

  const masterByCat = menuMaster.reduce((acc, m) => {
    (acc[m.category] = acc[m.category] || []).push(m); return acc;
  }, {});
  const isIntl = isInternationalCenter(form.center, centers);
  const currency = isIntl ? "$" : "₹";
  const gstLabel = isIntl ? "10% GST (incl.)" : "5% GST (incl.)";

  return (
    <div className="space-y-6" data-testid="event-bookings-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <PartyPopper className="w-7 h-7" />Event / Celebration Bookings
          </h1>
          <p className="text-muted-foreground text-sm">
            Birthdays, anniversaries, weddings, corporate. Hybrid menu + dal selector. GST = inclusive carve.
          </p>
        </div>
        <Button onClick={() => open(null)} data-testid="event-new-btn">
          <Plus className="w-4 h-4 mr-2" /> New Event Booking
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
          <div className="text-center py-12 text-muted-foreground">No event bookings.</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead><TableHead>Customer</TableHead>
                <TableHead>Event</TableHead><TableHead>Guests</TableHead>
                <TableHead>Final Total</TableHead><TableHead>Status</TableHead>
                <TableHead>Center</TableHead><TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.id} data-testid={`event-row-${r.id}`}>
                  <TableCell className="text-xs">{r.id}</TableCell>
                  <TableCell>
                    <div className="font-medium">{r.customer_name}</div>
                    <div className="text-xs text-muted-foreground">{r.phone}</div>
                  </TableCell>
                  <TableCell className="text-xs">{r.event_date}<br />{r.time_slot}<br />
                    <Badge variant="outline">{r.event_type}</Badge>
                  </TableCell>
                  <TableCell>{r.guest_count}</TableCell>
                  <TableCell>{Number(r.final_total || 0).toFixed(2)}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{r.confirmation_status}</Badge>
                    <div className="text-xs mt-1">{r.payment_status}</div>
                  </TableCell>
                  <TableCell className="text-xs">{r.center}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button size="icon" variant="ghost" onClick={() => open(r)} title="Edit"><Edit className="w-4 h-4" /></Button>
                      <Button size="icon" variant="ghost" onClick={() => downloadPdf(r)} title="Download PDF"><Download className="w-4 h-4" /></Button>
                      <Button size="icon" variant="ghost" onClick={() => sendQuote(r)} title="Send quote to customer" data-testid={`event-send-quote-${r.id}`}>
                        {r.quote_sent_at
                          ? <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                          : <Mail className="w-4 h-4 text-blue-500" />}
                      </Button>
                      {isAdmin && <Button size="icon" variant="ghost" onClick={() => del(r)}><Trash2 className="w-4 h-4 text-red-500" /></Button>}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent></Card>

      <Dialog open={showDlg} onOpenChange={setShowDlg}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editing ? `Edit ${editing.id}` : "New Event Booking"}</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Customer Name *</Label><Input value={form.customer_name} onChange={(e) => setForm(f => ({ ...f, customer_name: e.target.value }))} data-testid="event-customer-name" /></div>
              <div><Label>Phone *</Label><Input value={form.phone} onChange={(e) => setForm(f => ({ ...f, phone: e.target.value }))} /></div>
              <div><Label>Email</Label><Input value={form.email} onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))} /></div>
              <div><Label>Enquiry ID</Label><Input value={form.enquiry_id} onChange={(e) => setForm(f => ({ ...f, enquiry_id: e.target.value }))} /></div>
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

            <div className="grid grid-cols-4 gap-3">
              <div><Label>Event Type</Label>
                <Select value={form.event_type} onValueChange={(v) => setForm(f => ({ ...f, event_type: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{EVENT_TYPES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label>Event Date *</Label><Input type="date" value={form.event_date} onChange={(e) => setForm(f => ({ ...f, event_date: e.target.value }))} /></div>
              <div><Label>Time Slot</Label><Input value={form.time_slot} placeholder="7:00 PM - 11:00 PM" onChange={(e) => setForm(f => ({ ...f, time_slot: e.target.value }))} /></div>
              <div><Label>Guests</Label><Input type="number" value={form.guest_count} onChange={(e) => setForm(f => ({ ...f, guest_count: Number(e.target.value) || 0 }))} /></div>
              <div><Label>Package / Thali</Label><Input value={form.package_name} onChange={(e) => setForm(f => ({ ...f, package_name: e.target.value }))} placeholder="Celebration Thali Premium / Basic..." /></div>
              <div><Label>Dal Selection</Label>
                <Select value={form.dal_selection} onValueChange={(v) => setForm(f => ({ ...f, dal_selection: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{DAL_OPTIONS.map(d => <SelectItem key={d} value={d}>{d}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label>Assigned Manager</Label><Input value={form.assigned_manager} onChange={(e) => setForm(f => ({ ...f, assigned_manager: e.target.value }))} /></div>
              <div><Label>Quotation Link</Label><Input value={form.quotation_link} onChange={(e) => setForm(f => ({ ...f, quotation_link: e.target.value }))} /></div>
            </div>

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
                  testIdPrefix={`event-${cat.replace(/[^a-z]/gi, "")}`} />
              ))}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div><Label>Decoration</Label><Textarea rows={2} value={form.decoration} onChange={(e) => setForm(f => ({ ...f, decoration: e.target.value }))} /></div>
              <div><Label>Special Rules / Notes</Label><Textarea rows={2} value={form.special_rules} onChange={(e) => setForm(f => ({ ...f, special_rules: e.target.value }))} /></div>
            </div>

            <div className="grid grid-cols-3 gap-3 bg-muted/30 p-3 rounded">
              <div><Label className="text-xs">Estimated ({currency})</Label>
                <Input readOnly value={form.estimated_total.toFixed(2)} /></div>
              <div><Label className="text-xs">{gstLabel}</Label>
                <Input readOnly value={form.gst.toFixed(2)} /></div>
              <div><Label className="text-xs">Final Total ({currency})</Label>
                <Input readOnly className="font-bold" value={form.final_total.toFixed(2)} data-testid="event-final-total" /></div>
              <div><Label className="text-xs">Advance Paid</Label>
                <Input type="number" value={form.advance_paid}
                  onChange={(e) => setForm(f => ({ ...f, advance_paid: Number(e.target.value) || 0 }))} /></div>
              <div><Label className="text-xs">Balance Due ({currency})</Label>
                <Input readOnly value={form.balance_due.toFixed(2)} /></div>
              <div className="col-span-3 text-xs text-muted-foreground italic">
                GST = inclusive carve on Final Total. {isIntl ? "Australia 10%" : "India 5%"}.
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
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDlg(false)}>Cancel</Button>
            <Button onClick={save} data-testid="event-save-btn">{editing ? "Update" : "Create"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
