import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import {
  ArrowRightLeft, UserCheck, UserX, Clock, CheckCircle, XCircle, 
  Send, Bell, History, Filter, Loader2, AlertTriangle, FileText,
  ArrowRight, Building2, Calendar, ChevronDown
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
import { isAdminUser } from "@/lib/api";

const STATUS_COLORS = {
  DRAFT: "secondary",
  PENDING_APPROVAL: "outline",
  PENDING_ACCEPTANCE: "default",
  ACCEPTED: "default",
  REJECTED: "destructive",
  COMPLETED: "secondary",
  CANCELLED: "secondary"
};

const STATUS_LABELS = {
  DRAFT: "Draft",
  PENDING_APPROVAL: "Pending Approval",
  PENDING_ACCEPTANCE: "Pending Acceptance",
  ACCEPTED: "Active",
  REJECTED: "Rejected",
  COMPLETED: "Completed",
  CANCELLED: "Cancelled"
};

export default function EmployeeTransfers() {
  const { session } = useAuth();
  const isMGT = isAdminUser(session);
  const isAdmin = session?.is_super_admin || session?.is_admin;
  const userCenter = session?.center || "";

  // State
  const [activeTab, setActiveTab] = useState("dashboard");
  const [loading, setLoading] = useState(false);
  const [centers, setCenters] = useState([]);
  const [employees, setEmployees] = useState([]);
  
  // Transfer list state
  const [incoming, setIncoming] = useState([]);
  const [outgoing, setOutgoing] = useState([]);
  const [activeShifts, setActiveShifts] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  
  // Create transfer form
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [createForm, setCreateForm] = useState({
    employee_name: "",
    from_center: userCenter,
    to_center: "",
    transfer_type: "TEMPORARY",
    start_date: new Date().toISOString().split("T")[0],
    end_date: "",
    reason: "",
    notes: ""
  });
  const [creating, setCreating] = useState(false);
  
  // Action dialog
  const [showActionDialog, setShowActionDialog] = useState(false);
  const [actionTransfer, setActionTransfer] = useState(null);
  const [actionType, setActionType] = useState("");
  const [actionNotes, setActionNotes] = useState("");
  const [actioning, setActioning] = useState(false);
  
  // History
  const [history, setHistory] = useState([]);
  const [historyFilters, setHistoryFilters] = useState({
    center: "", status: "", transfer_type: "", start_date: "", end_date: ""
  });
  
  // Reports
  const [reportSummary, setReportSummary] = useState([]);

  // Notifications
  const [notifications, setNotifications] = useState([]);

  // Fetch centers
  useEffect(() => {
    const fetchCenters = async () => {
      try {
        const res = await fetch(`${API}/api/sales/centers-list`);
        const data = await res.json();
        if (data.centers) setCenters(data.centers);
      } catch (err) { console.error(err); }
    };
    fetchCenters();
  }, []);

  // Fetch employees for selected from_center
  useEffect(() => {
    const fetchEmployees = async () => {
      if (!createForm.from_center || !session?.token) return;
      try {
        const res = await fetch(`${API}/api/employees`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: session.token, center: createForm.from_center })
        });
        const data = await res.json();
        setEmployees(data.employees || []);
      } catch (err) { console.error(err); }
    };
    fetchEmployees();
  }, [createForm.from_center, session?.token]);

  // Fetch transfer dashboard data
  const fetchDashboard = useCallback(async () => {
    if (!session?.token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/transfers/list`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: session.token, center: isAdmin ? "" : userCenter })
      });
      const data = await res.json();
      if (data.success) {
        setIncoming(data.incoming || []);
        setOutgoing(data.outgoing || []);
        setActiveShifts(data.active || []);
        setUnreadCount(data.unread_notifications || 0);
      }
    } catch (err) { console.error(err); }
    setLoading(false);
  }, [session?.token, isAdmin, userCenter]);

  useEffect(() => { fetchDashboard(); }, [fetchDashboard]);

  // Create transfer
  const handleCreate = async () => {
    if (!createForm.employee_name) return toast.error("Select an employee");
    if (!createForm.to_center) return toast.error("Select destination center");
    if (!createForm.reason) return toast.error("Enter reason for transfer");
    if (createForm.transfer_type === "TEMPORARY" && !createForm.end_date)
      return toast.error("End date is required for temporary transfers");

    setCreating(true);
    try {
      const res = await fetch(`${API}/api/transfers/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: session.token, ...createForm })
      });
      const data = await res.json();
      if (data.success) {
        toast.success(data.message);
        setShowCreateDialog(false);
        setCreateForm(prev => ({ ...prev, employee_name: "", to_center: "", reason: "", notes: "", end_date: "" }));
        fetchDashboard();
      } else {
        toast.error(data.detail || "Failed to create transfer");
      }
    } catch (err) {
      toast.error("Failed to create transfer request");
    }
    setCreating(false);
  };

  // Transfer action (accept/reject/cancel)
  const handleAction = async () => {
    if (!actionTransfer) return;
    setActioning(true);
    try {
      const res = await fetch(`${API}/api/transfers/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: session.token,
          transfer_id: actionTransfer.id,
          action: actionType,
          notes: actionNotes
        })
      });
      const data = await res.json();
      if (data.success) {
        toast.success(data.message);
        setShowActionDialog(false);
        setActionTransfer(null);
        setActionNotes("");
        fetchDashboard();
      } else {
        toast.error(data.detail || `Failed to ${actionType} transfer`);
      }
    } catch (err) {
      toast.error(`Failed to ${actionType} transfer`);
    }
    setActioning(false);
  };

  // Fetch history
  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/transfers/history`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: session.token, ...historyFilters })
      });
      const data = await res.json();
      if (data.success) setHistory(data.history || []);
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  // Fetch reports
  const fetchReports = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/transfers/reports/summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: session.token })
      });
      const data = await res.json();
      if (data.success) setReportSummary(data.summary || []);
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  // Fetch notifications
  const fetchNotifications = async () => {
    try {
      const res = await fetch(`${API}/api/transfers/notifications`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: session.token })
      });
      const data = await res.json();
      if (data.success) setNotifications(data.notifications || []);
    } catch (err) { console.error(err); }
  };

  const openAction = (transfer, type) => {
    setActionTransfer(transfer);
    setActionType(type);
    setActionNotes("");
    setShowActionDialog(true);
  };

  // Transfer card component
  const TransferCard = ({ transfer, showActions = false, direction = "in" }) => (
    <Card className="border-l-4" style={{ borderLeftColor: transfer.transfer_type === "PERMANENT" ? "#ef4444" : "#3b82f6" }}>
      <CardContent className="p-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-base" data-testid="transfer-employee-name">{transfer.employee_name}</span>
              <Badge variant={STATUS_COLORS[transfer.status] || "secondary"} data-testid="transfer-status">
                {STATUS_LABELS[transfer.status] || transfer.status}
              </Badge>
              <Badge variant={transfer.transfer_type === "PERMANENT" ? "destructive" : "outline"} className="text-xs">
                {transfer.transfer_type}
              </Badge>
            </div>
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <Building2 className="w-3.5 h-3.5" />
              <span>{transfer.from_center}</span>
              <ArrowRight className="w-3.5 h-3.5 mx-1" />
              <span className="font-medium">{transfer.to_center}</span>
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{transfer.start_date}{transfer.end_date ? ` to ${transfer.end_date}` : ""}</span>
              <span>By: {transfer.requested_by}</span>
            </div>
            {transfer.reason && <p className="text-xs text-muted-foreground mt-1">Reason: {transfer.reason}</p>}
          </div>
          
          {showActions && transfer.status === "PENDING_ACCEPTANCE" && (
            <div className="flex gap-2 shrink-0">
              {(isAdmin || userCenter === transfer.to_center) && (
                <>
                  <Button size="sm" onClick={() => openAction(transfer, "accept")} className="gap-1" data-testid="accept-transfer-btn">
                    <CheckCircle className="w-3.5 h-3.5" /> Accept
                  </Button>
                  <Button size="sm" variant="destructive" onClick={() => openAction(transfer, "reject")} className="gap-1" data-testid="reject-transfer-btn">
                    <XCircle className="w-3.5 h-3.5" /> Reject
                  </Button>
                </>
              )}
              {(isAdmin || userCenter === transfer.from_center) && (
                <Button size="sm" variant="outline" onClick={() => openAction(transfer, "cancel")} className="gap-1">
                  Cancel
                </Button>
              )}
            </div>
          )}
          
          {transfer.status === "ACCEPTED" && (isAdmin || userCenter === transfer.from_center) && (
            <Button size="sm" variant="outline" onClick={() => openAction(transfer, "cancel")} className="gap-1">
              Cancel Transfer
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="min-h-screen bg-background p-4 md:p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <ArrowRightLeft className="w-6 h-6 text-blue-600" />
              Employee Transfers
            </h1>
            <p className="text-muted-foreground text-sm mt-1">
              Manage employee transfers between centers
            </p>
          </div>
          <div className="flex items-center gap-3">
            {unreadCount > 0 && (
              <Badge variant="destructive" className="text-xs">
                {unreadCount} new
              </Badge>
            )}
            <Button onClick={() => { setShowCreateDialog(true); setCreateForm(prev => ({ ...prev, from_center: userCenter })); }} className="gap-2" data-testid="new-transfer-btn">
              <Send className="w-4 h-4" /> New Transfer
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={(v) => {
          setActiveTab(v);
          if (v === "history") fetchHistory();
          if (v === "reports") fetchReports();
          if (v === "notifications") fetchNotifications();
        }}>
          <TabsList className="grid grid-cols-4 w-full max-w-lg">
            <TabsTrigger value="dashboard" className="gap-1"><ArrowRightLeft className="w-3.5 h-3.5" /> Dashboard</TabsTrigger>
            <TabsTrigger value="history" className="gap-1"><History className="w-3.5 h-3.5" /> History</TabsTrigger>
            <TabsTrigger value="reports" className="gap-1"><FileText className="w-3.5 h-3.5" /> Reports</TabsTrigger>
            <TabsTrigger value="notifications" className="gap-1 relative">
              <Bell className="w-3.5 h-3.5" /> Alerts
              {unreadCount > 0 && <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-[10px] rounded-full flex items-center justify-center">{unreadCount}</span>}
            </TabsTrigger>
          </TabsList>

          {/* DASHBOARD TAB */}
          <TabsContent value="dashboard" className="space-y-6">
            {loading ? (
              <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>
            ) : (
              <>
                {/* Incoming Requests */}
                <div>
                  <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    <UserCheck className="w-5 h-5 text-green-600" />
                    Incoming Transfer Requests
                    {incoming.length > 0 && <Badge variant="default">{incoming.length}</Badge>}
                  </h2>
                  {incoming.length === 0 ? (
                    <Card><CardContent className="p-6 text-center text-muted-foreground">No incoming transfer requests</CardContent></Card>
                  ) : (
                    <div className="space-y-3" data-testid="incoming-transfers">
                      {incoming.map(t => <TransferCard key={t.id} transfer={t} showActions direction="in" />)}
                    </div>
                  )}
                </div>

                {/* Outgoing Requests */}
                <div>
                  <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    <Send className="w-5 h-5 text-blue-600" />
                    Outgoing Transfer Requests
                    {outgoing.length > 0 && <Badge variant="outline">{outgoing.length}</Badge>}
                  </h2>
                  {outgoing.length === 0 ? (
                    <Card><CardContent className="p-6 text-center text-muted-foreground">No outgoing transfer requests</CardContent></Card>
                  ) : (
                    <div className="space-y-3" data-testid="outgoing-transfers">
                      {outgoing.map(t => <TransferCard key={t.id} transfer={t} showActions direction="out" />)}
                    </div>
                  )}
                </div>

                {/* Active Shifts */}
                <div>
                  <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    <Clock className="w-5 h-5 text-amber-600" />
                    Active Shifted Employees
                    {activeShifts.length > 0 && <Badge variant="secondary">{activeShifts.length}</Badge>}
                  </h2>
                  {activeShifts.length === 0 ? (
                    <Card><CardContent className="p-6 text-center text-muted-foreground">No active shifts</CardContent></Card>
                  ) : (
                    <div className="space-y-3" data-testid="active-shifts">
                      {activeShifts.map(t => <TransferCard key={t.id} transfer={t} showActions />)}
                    </div>
                  )}
                </div>
              </>
            )}
          </TabsContent>

          {/* HISTORY TAB */}
          <TabsContent value="history" className="space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2"><Filter className="w-4 h-4" /> Filters</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <Select value={historyFilters.center} onValueChange={v => setHistoryFilters(p => ({...p, center: v === "all" ? "" : v}))}>
                    <SelectTrigger><SelectValue placeholder="All Centers" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Centers</SelectItem>
                      {centers.map(c => <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <Select value={historyFilters.status} onValueChange={v => setHistoryFilters(p => ({...p, status: v === "all" ? "" : v}))}>
                    <SelectTrigger><SelectValue placeholder="All Status" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Status</SelectItem>
                      {VALID_STATUSES.map(s => <SelectItem key={s} value={s}>{STATUS_LABELS[s]}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <Select value={historyFilters.transfer_type} onValueChange={v => setHistoryFilters(p => ({...p, transfer_type: v === "all" ? "" : v}))}>
                    <SelectTrigger><SelectValue placeholder="All Types" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Types</SelectItem>
                      <SelectItem value="TEMPORARY">Temporary</SelectItem>
                      <SelectItem value="PERMANENT">Permanent</SelectItem>
                    </SelectContent>
                  </Select>
                  <Input type="date" value={historyFilters.start_date} onChange={e => setHistoryFilters(p => ({...p, start_date: e.target.value}))} placeholder="From" />
                  <Button onClick={fetchHistory} className="gap-1"><Filter className="w-4 h-4" /> Apply</Button>
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Employee</TableHead>
                      <TableHead>From</TableHead>
                      <TableHead>To</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Dates</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Requested By</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {history.length === 0 ? (
                      <TableRow><TableCell colSpan={7} className="text-center py-8 text-muted-foreground">No transfer history found</TableCell></TableRow>
                    ) : history.map(h => (
                      <TableRow key={h.id}>
                        <TableCell className="font-medium">{h.employee_name}</TableCell>
                        <TableCell>{h.from_center}</TableCell>
                        <TableCell>{h.to_center}</TableCell>
                        <TableCell><Badge variant={h.transfer_type === "PERMANENT" ? "destructive" : "outline"} className="text-xs">{h.transfer_type}</Badge></TableCell>
                        <TableCell className="text-xs">{h.start_date}{h.end_date ? ` - ${h.end_date}` : ""}</TableCell>
                        <TableCell><Badge variant={STATUS_COLORS[h.status]}>{STATUS_LABELS[h.status]}</Badge></TableCell>
                        <TableCell className="text-xs">{h.requested_by}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* REPORTS TAB */}
          <TabsContent value="reports" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Center-wise Transfer Summary</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Center</TableHead>
                      <TableHead className="text-center">Transfers In</TableHead>
                      <TableHead className="text-center">Transfers Out</TableHead>
                      <TableHead className="text-center">Active In</TableHead>
                      <TableHead className="text-center">Active Out</TableHead>
                      <TableHead className="text-center">Pending</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {reportSummary.length === 0 ? (
                      <TableRow><TableCell colSpan={6} className="text-center py-8 text-muted-foreground">No data</TableCell></TableRow>
                    ) : reportSummary.map(r => (
                      <TableRow key={r.center_code}>
                        <TableCell className="font-medium">{r.center_code}<span className="text-xs text-muted-foreground ml-1">{r.center_name}</span></TableCell>
                        <TableCell className="text-center">{r.total_transfers_in}</TableCell>
                        <TableCell className="text-center">{r.total_transfers_out}</TableCell>
                        <TableCell className="text-center font-medium text-green-600">{r.active_transfers_in}</TableCell>
                        <TableCell className="text-center font-medium text-amber-600">{r.active_transfers_out}</TableCell>
                        <TableCell className="text-center">{r.pending_requests > 0 ? <Badge variant="default">{r.pending_requests}</Badge> : "0"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* NOTIFICATIONS TAB */}
          <TabsContent value="notifications" className="space-y-3">
            <div className="flex justify-end">
              <Button variant="outline" size="sm" onClick={async () => {
                await fetch(`${API}/api/transfers/notifications/mark-read`, {
                  method: "POST", headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ token: session.token })
                });
                setUnreadCount(0);
                fetchNotifications();
                toast.success("All notifications marked as read");
              }}>Mark All Read</Button>
            </div>
            {notifications.length === 0 ? (
              <Card><CardContent className="p-8 text-center text-muted-foreground">No notifications</CardContent></Card>
            ) : notifications.map(n => (
              <Card key={n.id} className={`transition-all ${!n.read ? "border-blue-300 bg-blue-50/50" : ""}`}>
                <CardContent className="p-3 flex items-start gap-3">
                  <Bell className={`w-4 h-4 mt-0.5 shrink-0 ${!n.read ? "text-blue-600" : "text-muted-foreground"}`} />
                  <div>
                    <p className={`text-sm ${!n.read ? "font-medium" : ""}`}>{n.message}</p>
                    <p className="text-xs text-muted-foreground mt-1">{n.created_at?.split("T")[0]} {n.created_at?.split("T")[1]?.slice(0,5)}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>
        </Tabs>

        {/* CREATE TRANSFER DIALOG */}
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2"><ArrowRightLeft className="w-5 h-5" /> New Transfer Request</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>From Center</Label>
                  <Select value={createForm.from_center} onValueChange={v => setCreateForm(p => ({...p, from_center: v, employee_name: ""}))}>
                    <SelectTrigger data-testid="from-center-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {centers.map(c => <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>To Center</Label>
                  <Select value={createForm.to_center} onValueChange={v => setCreateForm(p => ({...p, to_center: v}))}>
                    <SelectTrigger data-testid="to-center-select"><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                      {centers.filter(c => c.code !== createForm.from_center).map(c => <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div>
                <Label>Employee</Label>
                <Select value={createForm.employee_name} onValueChange={v => setCreateForm(p => ({...p, employee_name: v}))}>
                  <SelectTrigger data-testid="employee-select"><SelectValue placeholder="Select employee" /></SelectTrigger>
                  <SelectContent>
                    {employees.map(e => <SelectItem key={e.name} value={e.name}>{e.name} — {e.designation || "Staff"}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <Label>Transfer Type</Label>
                <Select value={createForm.transfer_type} onValueChange={v => setCreateForm(p => ({...p, transfer_type: v}))}>
                  <SelectTrigger data-testid="transfer-type-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="TEMPORARY">Temporary Shift</SelectItem>
                    <SelectItem value="PERMANENT">Permanent Transfer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Start Date</Label>
                  <Input type="date" value={createForm.start_date} onChange={e => setCreateForm(p => ({...p, start_date: e.target.value}))} data-testid="start-date-input" />
                </div>
                {createForm.transfer_type === "TEMPORARY" && (
                  <div>
                    <Label>End Date</Label>
                    <Input type="date" value={createForm.end_date} onChange={e => setCreateForm(p => ({...p, end_date: e.target.value}))} data-testid="end-date-input" />
                  </div>
                )}
              </div>
              
              <div>
                <Label>Reason</Label>
                <Textarea value={createForm.reason} onChange={e => setCreateForm(p => ({...p, reason: e.target.value}))} placeholder="Reason for transfer" data-testid="reason-input" />
              </div>
              
              <div>
                <Label>Notes (optional)</Label>
                <Input value={createForm.notes} onChange={e => setCreateForm(p => ({...p, notes: e.target.value}))} placeholder="Additional notes" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
              <Button onClick={handleCreate} disabled={creating} className="gap-2" data-testid="submit-transfer-btn">
                {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Submit Transfer
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ACTION DIALOG (Accept/Reject/Cancel) */}
        <Dialog open={showActionDialog} onOpenChange={setShowActionDialog}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="capitalize">{actionType} Transfer</DialogTitle>
            </DialogHeader>
            {actionTransfer && (
              <div className="space-y-3 py-2">
                <div className="text-sm space-y-1 p-3 bg-muted/50 rounded-lg">
                  <p><span className="text-muted-foreground">Employee:</span> <span className="font-medium">{actionTransfer.employee_name}</span></p>
                  <p><span className="text-muted-foreground">Transfer:</span> {actionTransfer.from_center} <ArrowRight className="w-3 h-3 inline mx-1" /> {actionTransfer.to_center}</p>
                  <p><span className="text-muted-foreground">Type:</span> {actionTransfer.transfer_type}</p>
                  <p><span className="text-muted-foreground">Dates:</span> {actionTransfer.start_date}{actionTransfer.end_date ? ` to ${actionTransfer.end_date}` : ""}</p>
                </div>
                <div>
                  <Label>Notes</Label>
                  <Textarea value={actionNotes} onChange={e => setActionNotes(e.target.value)} placeholder={`Reason for ${actionType}ing...`} data-testid="action-notes" />
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowActionDialog(false)}>Cancel</Button>
              <Button
                onClick={handleAction}
                disabled={actioning}
                variant={actionType === "reject" || actionType === "cancel" ? "destructive" : "default"}
                className="gap-2 capitalize"
                data-testid="confirm-action-btn"
              >
                {actioning ? <Loader2 className="w-4 h-4 animate-spin" /> : actionType === "accept" ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                {actionType}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}

const VALID_STATUSES = ["DRAFT", "PENDING_APPROVAL", "PENDING_ACCEPTANCE", "ACCEPTED", "REJECTED", "COMPLETED", "CANCELLED"];
