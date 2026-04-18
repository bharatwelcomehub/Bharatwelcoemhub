import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { api, isAdminUser, fetchCentersFromDB } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Loader2, Plus, Save, Trash2, RefreshCw, Copy, Download, Send, CheckCircle,
  XCircle, Clock, Calendar, Users, FileSpreadsheet, MessageSquare, Eye,
  Lock, Unlock, ArrowRight, AlertTriangle, Settings, ChevronDown,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const STATUS_COLORS = {
  draft: "bg-yellow-100 text-yellow-800 border-yellow-300",
  sent: "bg-blue-100 text-blue-800 border-blue-300",
  confirmed: "bg-green-100 text-green-800 border-green-300",
  denied: "bg-red-100 text-red-800 border-red-300",
  replaced: "bg-orange-100 text-orange-800 border-orange-300",
  cancelled: "bg-gray-100 text-gray-600 border-gray-300",
  locked: "bg-purple-100 text-purple-800 border-purple-300",
  partially_confirmed: "bg-teal-100 text-teal-800 border-teal-300",
  fully_confirmed: "bg-emerald-100 text-emerald-800 border-emerald-300",
};

const DAY_COLORS = {
  Monday: "#3b82f6", Tuesday: "#8b5cf6", Wednesday: "#f59e0b",
  Thursday: "#10b981", Friday: "#ef4444", Saturday: "#ec4899", Sunday: "#6366f1",
};

export default function InternationalRoster() {
  const { session } = useAuth();
  const isAdmin = isAdminUser(session);
  const token = session?.token;

  const [loading, setLoading] = useState(false);
  const [centers, setCenters] = useState([]);
  const [selectedCenter, setSelectedCenter] = useState("");
  const [weekInfo, setWeekInfo] = useState(null);
  const [weekStart, setWeekStart] = useState("");
  const [roster, setRoster] = useState(null);
  const [lines, setLines] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [roles, setRoles] = useState([]);
  const [shifts, setShifts] = useState([]);
  const [stats, setStats] = useState(null);
  const [viewMode, setViewMode] = useState("grid"); // grid | list
  const [showMasters, setShowMasters] = useState(false);
  const [waLinks, setWaLinks] = useState([]);
  const [showWaDialog, setShowWaDialog] = useState(false);
  const [replaceDialog, setReplaceDialog] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [showAudit, setShowAudit] = useState(false);

  // Load international centers
  useEffect(() => {
    if (!token) return;
    fetchCentersFromDB(token).then(allCenters => {
      const intl = allCenters.filter(c => c.is_india_center === false);
      setCenters(intl);
      if (intl.length === 1) setSelectedCenter(intl[0].code);
      else if (!isAdmin && session?.center) {
        const match = intl.find(c => c.code === session.center);
        if (match) setSelectedCenter(match.code);
      }
    });
  }, [token]);

  // Load masters + employees when center changes
  useEffect(() => {
    if (!token || !selectedCenter) return;
    loadMasters();
    loadEmployees();
  }, [token, selectedCenter]);

  // Load week info on mount
  useEffect(() => {
    if (!token) return;
    api.post("/international-roster/week-info", { token }).then(res => {
      const next = res.data.next_week;
      setWeekInfo(res.data);
      if (!weekStart) setWeekStart(next.week_start);
    });
  }, [token]);

  // Load roster when week changes
  useEffect(() => {
    if (token && selectedCenter && weekStart) {
      loadRoster();
      loadDashboard();
    }
  }, [token, selectedCenter, weekStart]);

  const loadMasters = async () => {
    try {
      const [rolesRes, shiftsRes] = await Promise.all([
        api.post("/international-roster/masters/list", { token, center: selectedCenter, type: "role" }),
        api.post("/international-roster/masters/list", { token, center: selectedCenter, type: "shift" }),
      ]);
      setRoles((rolesRes.data.items || []).filter(i => i.active !== false));
      setShifts((shiftsRes.data.items || []).filter(i => i.active !== false));
    } catch { /* silent */ }
  };

  const loadEmployees = async () => {
    try {
      const res = await api.post("/international-roster/employees", { token, center: selectedCenter });
      setEmployees(res.data.employees || []);
    } catch { /* silent */ }
  };

  const loadRoster = async () => {
    setLoading(true);
    try {
      const res = await api.post("/international-roster/roster/get", { token, center: selectedCenter, week_start: weekStart });
      setRoster(res.data.roster);
      setLines(res.data.lines || []);
      if (!weekInfo || weekInfo.current_week?.week_start !== res.data.week_info?.week_start) {
        setWeekInfo(prev => ({ ...prev, selected: res.data.week_info }));
      }
    } catch (e) {
      toast.error("Failed to load roster");
    } finally { setLoading(false); }
  };

  const loadDashboard = async () => {
    try {
      const res = await api.post("/international-roster/roster/dashboard", { token, center: selectedCenter, week_start: weekStart });
      setStats(res.data.stats || {});
    } catch { /* silent */ }
  };

  const seedMasters = async () => {
    try {
      const res = await api.post("/international-roster/masters/seed", { token, center: selectedCenter });
      toast.success(res.data.message);
      loadMasters();
    } catch (e) { toast.error(e.response?.data?.detail || "Seed failed"); }
  };

  // ===== ROSTER LINE MANAGEMENT =====

  const addLine = (date = "") => {
    const defaultShift = shifts[0];
    setLines(prev => [...prev, {
      line_id: "", date, day: "", shift_type: defaultShift?.name || "",
      planned_in: defaultShift?.config?.default_in || "09:00",
      planned_out: defaultShift?.config?.default_out || "17:00",
      break_minutes: defaultShift?.config?.break_minutes || 0,
      working_hours: 0, employee_name: "", whatsapp: "", duty_role: roles[0]?.name || "",
      backup_employee: "", notes: "", status: "draft",
    }]);
  };

  const updateLine = (idx, field, value) => {
    setLines(prev => prev.map((l, i) => {
      if (i !== idx) return l;
      const updated = { ...l, [field]: value };

      // Auto-fill on employee select
      if (field === "employee_name") {
        const emp = employees.find(e => e.name === value);
        if (emp) updated.whatsapp = emp.whatsapp || emp.mobile || "";
      }

      // Auto-fill shift times
      if (field === "shift_type") {
        const shift = shifts.find(s => s.name === value);
        if (shift?.config) {
          updated.planned_in = shift.config.default_in || updated.planned_in;
          updated.planned_out = shift.config.default_out || updated.planned_out;
          updated.break_minutes = shift.config.break_minutes || 0;
        }
      }

      // Auto-calc hours
      if (["planned_in", "planned_out", "break_minutes"].includes(field)) {
        const inn = updated.planned_in;
        const out = updated.planned_out;
        if (inn && out) {
          const [h1, m1] = inn.split(":").map(Number);
          const [h2, m2] = out.split(":").map(Number);
          let diff = (h2 * 60 + m2) - (h1 * 60 + m1);
          if (diff < 0) diff += 24 * 60;
          updated.working_hours = Math.round((diff - (parseInt(updated.break_minutes) || 0)) / 60 * 100) / 100;
        }
      }
      return updated;
    }));
  };

  const removeLine = (idx) => {
    const line = lines[idx];
    if (line.line_id && line.status !== "draft") {
      api.post("/international-roster/roster/delete-line", { token, line_id: line.line_id })
        .then(() => { setLines(prev => prev.filter((_, i) => i !== idx)); toast.success("Line removed"); })
        .catch(e => toast.error(e.response?.data?.detail || "Cannot delete"));
    } else {
      setLines(prev => prev.filter((_, i) => i !== idx));
    }
  };

  const saveRoster = async () => {
    setLoading(true);
    try {
      const res = await api.post("/international-roster/roster/save", {
        token, center: selectedCenter, week_start: weekStart,
        roster_id: roster?.roster_id || "", lines,
      });
      toast.success(res.data.message);
      loadRoster();
      loadDashboard();
    } catch (e) { toast.error(e.response?.data?.detail || "Save failed"); }
    finally { setLoading(false); }
  };

  const copyLastWeek = async () => {
    try {
      const res = await api.post("/international-roster/roster/copy-week", { token, center: selectedCenter, week_start: weekStart });
      toast.success(res.data.message);
      loadRoster();
    } catch (e) { toast.error(e.response?.data?.detail || "Copy failed"); }
  };

  const sendConfirmation = async () => {
    if (!roster?.roster_id) { toast.error("Save roster first"); return; }
    try {
      const res = await api.post("/international-roster/roster/send-confirmation", { token, center: selectedCenter, roster_id: roster.roster_id });
      setWaLinks(res.data.links || []);
      setShowWaDialog(true);
      toast.success(`${res.data.count} WhatsApp links generated`);
      loadRoster();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };

  const updateResponse = async (lineId, response) => {
    try {
      await api.post("/international-roster/roster/update-response", { token, line_id: lineId, response });
      toast.success(`Marked as ${response}`);
      loadRoster();
      loadDashboard();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };

  const handleReplace = async () => {
    if (!replaceDialog) return;
    try {
      await api.post("/international-roster/roster/replace-employee", {
        token, line_id: replaceDialog.line_id,
        new_employee_name: replaceDialog.newEmployee,
        new_whatsapp: replaceDialog.newWhatsapp,
      });
      toast.success("Employee replaced");
      setReplaceDialog(null);
      loadRoster();
    } catch (e) { toast.error(e.response?.data?.detail || "Replace failed"); }
  };

  const syncAttendance = async () => {
    if (!roster?.roster_id) return;
    try {
      const res = await api.post("/international-roster/roster/sync-attendance", { token, roster_id: roster.roster_id });
      toast.success(res.data.message);
      loadRoster();
      loadDashboard();
    } catch (e) { toast.error(e.response?.data?.detail || "Sync failed"); }
  };

  const exportExcel = async () => {
    if (!roster?.roster_id) return;
    try {
      const res = await api.post("/international-roster/roster/export", { token, roster_id: roster.roster_id }, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a"); a.href = url;
      a.download = `Roster_${selectedCenter}_${weekStart}.xlsx`;
      document.body.appendChild(a); a.click(); a.remove();
      toast.success("Exported!");
    } catch { toast.error("Export failed"); }
  };

  const loadAudit = async () => {
    if (!roster?.roster_id) return;
    try {
      const res = await api.post("/international-roster/roster/audit", { token, roster_id: roster.roster_id });
      setAuditLogs(res.data.logs || []);
      setShowAudit(true);
    } catch { toast.error("Failed to load audit"); }
  };

  const weekDays = weekInfo?.selected?.days || weekInfo?.next_week?.days || [];
  const currentWeekLabel = weekInfo?.selected?.label || weekInfo?.next_week?.label || "";
  const isLocked = roster?.status === "locked";

  // Navigate weeks
  const navWeek = (dir) => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + (dir * 7));
    setWeekStart(d.toISOString().split("T")[0]);
  };

  return (
    <div className="space-y-5 pb-8" data-testid="international-roster-page">
      {/* Header */}
      <div className="bg-gradient-to-r from-[#1e3a5f] to-[#2563eb] rounded-xl p-5 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2" data-testid="roster-title">
              <Calendar className="w-6 h-6" /> International Weekly Roster
            </h1>
            <p className="text-white/70 text-sm mt-1">Plan, confirm & sync weekly duty roster</p>
          </div>
          <div className="flex gap-2">
            <select value={selectedCenter} onChange={e => setSelectedCenter(e.target.value)}
              className="h-10 px-3 rounded-lg bg-white/20 text-white border border-white/30 text-sm"
              data-testid="roster-center-select">
              <option value="" className="text-black">Select Center</option>
              {centers.map(c => <option key={c.code} value={c.code} className="text-black">{c.code} - {c.name}</option>)}
            </select>
            {isAdmin && (
              <Button onClick={seedMasters} variant="ghost" className="text-white border border-white/30 hover:bg-white/10" size="sm">
                <Settings className="w-4 h-4 mr-1" /> Seed Masters
              </Button>
            )}
          </div>
        </div>
      </div>

      {!selectedCenter ? (
        <Card><CardContent className="py-16 text-center text-muted-foreground">
          <Calendar className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="text-lg">Select an international center to manage roster</p>
        </CardContent></Card>
      ) : (
        <>
          {/* Week Navigation */}
          <Card>
            <CardContent className="py-3 flex items-center justify-between gap-3 flex-wrap">
              <Button variant="outline" size="sm" onClick={() => navWeek(-1)}>
                <ArrowRight className="w-4 h-4 rotate-180 mr-1" /> Prev Week
              </Button>
              <div className="text-center">
                <p className="text-lg font-bold text-primary" data-testid="week-label">{currentWeekLabel}</p>
                {roster && <Badge className={STATUS_COLORS[roster.status] || ""} data-testid="roster-status">{roster.status?.replace("_", " ").toUpperCase()}</Badge>}
              </div>
              <Button variant="outline" size="sm" onClick={() => navWeek(1)}>
                Next Week <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </CardContent>
          </Card>

          {/* Dashboard Stats */}
          {stats && stats.total_shifts > 0 && (
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
              {[
                { label: "Total Shifts", val: stats.total_shifts, icon: Calendar, color: "text-slate-700" },
                { label: "Confirmed", val: stats.confirmed, icon: CheckCircle, color: "text-green-600" },
                { label: "Pending", val: stats.pending, icon: Clock, color: "text-amber-600" },
                { label: "Denied", val: stats.denied, icon: XCircle, color: "text-red-600" },
                { label: "Hours", val: stats.total_hours, icon: Clock, color: "text-blue-600" },
                { label: "Staff", val: stats.unique_employees, icon: Users, color: "text-purple-600" },
              ].map((s, i) => (
                <Card key={i} className="bg-white">
                  <CardContent className="p-3 text-center">
                    <s.icon className={`w-5 h-5 mx-auto mb-1 ${s.color}`} />
                    <div className={`text-xl font-bold ${s.color}`}>{s.val}</div>
                    <div className="text-[10px] text-muted-foreground">{s.label}</div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Action Bar */}
          <div className="flex flex-wrap gap-2">
            <div className="flex gap-1 bg-muted p-1 rounded-lg">
              <Button size="sm" variant={viewMode === "grid" ? "default" : "ghost"} onClick={() => setViewMode("grid")}
                className={viewMode === "grid" ? "bg-[#1e3a5f]" : ""}>Grid</Button>
              <Button size="sm" variant={viewMode === "list" ? "default" : "ghost"} onClick={() => setViewMode("list")}
                className={viewMode === "list" ? "bg-[#1e3a5f]" : ""}>List</Button>
            </div>
            <Button onClick={saveRoster} disabled={loading || isLocked} className="bg-[#1e3a5f]" data-testid="save-roster-btn">
              {loading ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Save className="w-4 h-4 mr-1" />} Save
            </Button>
            <Button onClick={sendConfirmation} variant="outline" disabled={!roster?.roster_id || isLocked}
              className="border-green-500 text-green-700" data-testid="send-confirmation-btn">
              <Send className="w-4 h-4 mr-1" /> Send WhatsApp
            </Button>
            <Button onClick={syncAttendance} variant="outline" disabled={!roster?.roster_id}
              className="border-blue-500 text-blue-700" data-testid="sync-attendance-btn">
              <ArrowRight className="w-4 h-4 mr-1" /> Sync Attendance
            </Button>
            <Button onClick={copyLastWeek} variant="outline" disabled={isLocked}>
              <Copy className="w-4 h-4 mr-1" /> Copy Last Week
            </Button>
            <Button onClick={exportExcel} variant="outline" disabled={!roster?.roster_id}>
              <FileSpreadsheet className="w-4 h-4 mr-1" /> Export
            </Button>
            <Button onClick={loadAudit} variant="ghost" disabled={!roster?.roster_id}>
              <Eye className="w-4 h-4 mr-1" /> Audit
            </Button>
            <Button onClick={loadRoster} variant="ghost"><RefreshCw className="w-4 h-4" /></Button>
          </div>

          {/* ===== GRID VIEW — Weekly Calendar Grid ===== */}
          {viewMode === "grid" && (
            <div className="space-y-3">
              {/* Quick Add Row */}
              {!isLocked && (
                <Card className="border-dashed border-2">
                  <CardContent className="py-3 flex items-center gap-3 flex-wrap">
                    <span className="text-sm font-medium text-muted-foreground">Quick Add:</span>
                    {weekDays.map(dayInfo => (
                      <Button key={dayInfo.date} size="sm" variant="outline" onClick={() => addLine(dayInfo.date)}
                        className="text-xs h-8" style={{ borderColor: DAY_COLORS[dayInfo.day] || "#64748b", color: DAY_COLORS[dayInfo.day] || "#64748b" }}>
                        <Plus className="w-3 h-3 mr-1" /> {dayInfo.day_short} {dayInfo.date.slice(8)}
                      </Button>
                    ))}
                  </CardContent>
                </Card>
              )}

              {/* Day Cards */}
              {weekDays.map((dayInfo) => {
                const dayLines = lines.filter(l => l.date === dayInfo.date);
                const dayColor = DAY_COLORS[dayInfo.day] || "#64748b";
                if (dayLines.length === 0 && isLocked) return null;
                return (
                  <Card key={dayInfo.date} className="border-l-4 overflow-hidden" style={{ borderLeftColor: dayColor }}>
                    <CardHeader className="py-2.5 px-4 bg-muted/30">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-bold flex items-center gap-2" style={{ color: dayColor }}>
                          <Calendar className="w-4 h-4" />
                          {dayInfo.day} — {new Date(dayInfo.date + "T00:00:00").toLocaleDateString("en-AU", { day: "2-digit", month: "short", year: "numeric" })}
                        </CardTitle>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">{dayLines.length} shift{dayLines.length !== 1 ? "s" : ""}</Badge>
                          {!isLocked && (
                            <Button size="sm" variant="outline" onClick={() => addLine(dayInfo.date)} className="h-7 px-2 text-xs">
                              <Plus className="w-3 h-3 mr-1" /> Add Shift
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardHeader>
                    {dayLines.length > 0 ? (
                      <CardContent className="p-0">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b bg-muted/20 text-xs text-muted-foreground">
                              <th className="text-left p-2 font-medium w-28">Shift</th>
                              <th className="text-left p-2 font-medium w-20">In</th>
                              <th className="text-left p-2 font-medium w-20">Out</th>
                              <th className="text-center p-2 font-medium w-12">Hrs</th>
                              <th className="text-left p-2 font-medium">Employee</th>
                              <th className="text-left p-2 font-medium w-28">Role</th>
                              <th className="text-center p-2 font-medium w-20">Status</th>
                              <th className="text-center p-2 font-medium w-48">Action</th>
                            </tr>
                          </thead>
                          <tbody>
                            {dayLines.map((line) => {
                              const globalIdx = lines.indexOf(line);
                              const isSent = line.status === "sent";
                              const isDenied = line.status === "denied";
                              const isConfirmed = line.status === "confirmed";
                              return (
                                <tr key={globalIdx} className={`border-b last:border-b-0 ${
                                  isConfirmed ? "bg-green-50" : isDenied ? "bg-red-50" : isSent ? "bg-blue-50/50" : ""
                                }`} data-testid={`roster-line-${globalIdx}`}>
                                  <td className="p-2">
                                    <select value={line.shift_type} onChange={e => updateLine(globalIdx, "shift_type", e.target.value)}
                                      disabled={isLocked || isConfirmed} className="h-8 px-1.5 rounded border text-xs w-full bg-white">
                                      {shifts.map(s => <option key={s.name} value={s.name}>{s.name}</option>)}
                                    </select>
                                  </td>
                                  <td className="p-2">
                                    <Input type="time" value={line.planned_in} onChange={e => updateLine(globalIdx, "planned_in", e.target.value)}
                                      disabled={isLocked || isConfirmed} className="h-8 text-xs w-full" />
                                  </td>
                                  <td className="p-2">
                                    <Input type="time" value={line.planned_out} onChange={e => updateLine(globalIdx, "planned_out", e.target.value)}
                                      disabled={isLocked || isConfirmed} className="h-8 text-xs w-full" />
                                  </td>
                                  <td className="p-2 text-center font-mono text-xs font-bold">{line.working_hours}</td>
                                  <td className="p-2">
                                    <select value={line.employee_name} onChange={e => updateLine(globalIdx, "employee_name", e.target.value)}
                                      disabled={isLocked || isConfirmed} className="h-8 px-1.5 rounded border text-xs w-full bg-white font-medium">
                                      <option value="">Select Employee</option>
                                      {employees.map(emp => <option key={emp.name} value={emp.name}>{emp.name}</option>)}
                                    </select>
                                  </td>
                                  <td className="p-2">
                                    <select value={line.duty_role} onChange={e => updateLine(globalIdx, "duty_role", e.target.value)}
                                      disabled={isLocked || isConfirmed} className="h-8 px-1.5 rounded border text-xs w-full bg-white">
                                      {roles.map(r => <option key={r.name} value={r.name}>{r.name}</option>)}
                                    </select>
                                  </td>
                                  <td className="p-2 text-center">
                                    <Badge className={`text-[10px] ${STATUS_COLORS[line.status] || ""}`}>{line.status?.toUpperCase()}</Badge>
                                  </td>
                                  <td className="p-2">
                                    <div className="flex items-center justify-center gap-1.5">
                                      {/* SENT or DRAFT → Show Confirm / Deny */}
                                      {(isSent || line.status === "draft") && (
                                        <>
                                          <Button size="sm" onClick={() => {
                                            if (!line.line_id) { toast.error("Save the roster first before confirming"); return; }
                                            updateResponse(line.line_id, "confirmed");
                                          }}
                                            className="h-8 px-3 bg-green-600 hover:bg-green-700 text-white text-xs font-bold rounded-md"
                                            data-testid={`confirm-btn-${globalIdx}`}>
                                            <CheckCircle className="w-3.5 h-3.5 mr-1" /> Confirm
                                          </Button>
                                          <Button size="sm" onClick={() => {
                                            if (!line.line_id) { toast.error("Save the roster first"); return; }
                                            updateResponse(line.line_id, "denied");
                                          }}
                                            variant="destructive" className="h-8 px-3 text-xs font-bold rounded-md"
                                            data-testid={`deny-btn-${globalIdx}`}>
                                            <XCircle className="w-3.5 h-3.5 mr-1" /> Deny
                                          </Button>
                                        </>
                                      )}
                                      {/* DENIED → Show Replace */}
                                      {isDenied && (
                                        <Button size="sm" onClick={() => setReplaceDialog({ line_id: line.line_id, original: line.employee_name, newEmployee: "", newWhatsapp: "" })}
                                          className="h-8 px-3 bg-orange-500 hover:bg-orange-600 text-white text-xs font-bold rounded-md"
                                          data-testid={`replace-btn-${globalIdx}`}>
                                          <Users className="w-3.5 h-3.5 mr-1" /> Replace
                                        </Button>
                                      )}
                                      {/* CONFIRMED → Show check */}
                                      {isConfirmed && (
                                        <span className="flex items-center gap-1 text-green-700 text-xs font-bold">
                                          <CheckCircle className="w-4 h-4" /> Done
                                          {line.attendance_synced && <Badge className="bg-blue-100 text-blue-700 text-[9px] ml-1">Synced</Badge>}
                                        </span>
                                      )}
                                      {/* Delete — for draft/sent, not confirmed/locked */}
                                      {!isLocked && !isConfirmed && (
                                        <Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-red-400 hover:text-red-600" onClick={() => removeLine(globalIdx)}>
                                          <Trash2 className="w-4 h-4" />
                                        </Button>
                                      )}
                                    </div>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </CardContent>
                    ) : (
                      <CardContent className="py-4 text-center text-sm text-muted-foreground">
                        No shifts scheduled — <button onClick={() => addLine(dayInfo.date)} className="text-primary underline font-medium">Add one</button>
                      </CardContent>
                    )}
                  </Card>
                );
              })}
            </div>
          )}

          {/* ===== LIST VIEW ===== */}
          {viewMode === "list" && (
            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-[#1e3a5f] text-white">
                      <tr>
                        {["Date", "Day", "Shift", "In", "Out", "Hrs", "Employee", "WhatsApp", "Role", "Notes", "Status", ""].map(h => (
                          <th key={h} className="p-2 text-left font-medium text-xs">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {lines.map((line, idx) => (
                        <tr key={idx} className={`border-b hover:bg-muted/30 ${
                          line.status === "confirmed" ? "bg-green-50" :
                          line.status === "denied" ? "bg-red-50" : ""
                        }`} data-testid={`list-line-${idx}`}>
                          <td className="p-2">
                            <select value={line.date} onChange={e => updateLine(idx, "date", e.target.value)}
                              disabled={isLocked} className="h-8 px-1 rounded border text-xs bg-white">
                              <option value="">Date</option>
                              {weekDays.map(d => <option key={d.date} value={d.date}>{d.date.slice(5)}</option>)}
                            </select>
                          </td>
                          <td className="p-2 text-xs">{line.day || (line.date && weekDays.find(d => d.date === line.date)?.day_short) || ""}</td>
                          <td className="p-2">
                            <select value={line.shift_type} onChange={e => updateLine(idx, "shift_type", e.target.value)}
                              disabled={isLocked} className="h-8 px-1 rounded border text-xs bg-white w-20">
                              {shifts.map(s => <option key={s.name} value={s.name}>{s.name}</option>)}
                            </select>
                          </td>
                          <td className="p-2"><Input type="time" value={line.planned_in} onChange={e => updateLine(idx, "planned_in", e.target.value)} disabled={isLocked} className="h-8 text-xs w-20" /></td>
                          <td className="p-2"><Input type="time" value={line.planned_out} onChange={e => updateLine(idx, "planned_out", e.target.value)} disabled={isLocked} className="h-8 text-xs w-20" /></td>
                          <td className="p-2 text-xs font-mono">{line.working_hours}</td>
                          <td className="p-2">
                            <select value={line.employee_name} onChange={e => updateLine(idx, "employee_name", e.target.value)}
                              disabled={isLocked} className="h-8 px-1 rounded border text-xs bg-white w-32">
                              <option value="">Employee</option>
                              {employees.map(emp => <option key={emp.name} value={emp.name}>{emp.name}</option>)}
                            </select>
                          </td>
                          <td className="p-2 text-xs font-mono">{line.whatsapp}</td>
                          <td className="p-2">
                            <select value={line.duty_role} onChange={e => updateLine(idx, "duty_role", e.target.value)}
                              disabled={isLocked} className="h-8 px-1 rounded border text-xs bg-white w-24">
                              {roles.map(r => <option key={r.name} value={r.name}>{r.name}</option>)}
                            </select>
                          </td>
                          <td className="p-2"><Input value={line.notes || ""} onChange={e => updateLine(idx, "notes", e.target.value)} disabled={isLocked} className="h-8 text-xs w-24" placeholder="Notes" /></td>
                          <td className="p-2"><Badge className={`text-[10px] ${STATUS_COLORS[line.status] || ""}`}>{line.status}</Badge></td>
                          <td className="p-2">
                            <div className="flex gap-1">
                              {line.status === "sent" && <>
                                <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-green-600" onClick={() => updateResponse(line.line_id, "confirmed")}><CheckCircle className="w-3 h-3" /></Button>
                                <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-red-600" onClick={() => updateResponse(line.line_id, "denied")}><XCircle className="w-3 h-3" /></Button>
                              </>}
                              {!isLocked && <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-red-400" onClick={() => removeLine(idx)}><Trash2 className="w-3 h-3" /></Button>}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!isLocked && (
                  <div className="p-3 border-t">
                    <Button variant="outline" onClick={() => addLine(weekDays[0]?.date || "")} className="w-full border-dashed" data-testid="add-line-btn">
                      <Plus className="w-4 h-4 mr-1" /> Add Shift Entry
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {lines.length === 0 && !loading && (
            <Card><CardContent className="py-12 text-center text-muted-foreground">
              <Calendar className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-lg mb-2">No roster entries for this week</p>
              <div className="flex gap-2 justify-center">
                <Button onClick={() => addLine(weekDays[0]?.date || "")} data-testid="create-first-btn">
                  <Plus className="w-4 h-4 mr-1" /> Create Roster
                </Button>
                <Button variant="outline" onClick={copyLastWeek}>
                  <Copy className="w-4 h-4 mr-1" /> Copy Last Week
                </Button>
              </div>
            </CardContent></Card>
          )}
        </>
      )}

      {/* WhatsApp Links Dialog */}
      <Dialog open={showWaDialog} onOpenChange={setShowWaDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><MessageSquare className="w-5 h-5 text-green-600" /> WhatsApp Confirmation Links</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            <p className="text-sm text-muted-foreground">Click each link to open WhatsApp and send the confirmation message:</p>
            {waLinks.map((link, i) => (
              <a key={i} href={link.wa_link} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-3 p-3 rounded-lg border hover:bg-green-50 transition-colors" data-testid={`wa-link-${i}`}>
                <MessageSquare className="w-5 h-5 text-green-600 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold">{link.employee_name}</p>
                  <p className="text-xs text-muted-foreground">{link.date} — {link.shift}</p>
                </div>
                <Badge className="bg-green-100 text-green-700 text-xs">Open WhatsApp</Badge>
              </a>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowWaDialog(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Replace Employee Dialog */}
      <Dialog open={!!replaceDialog} onOpenChange={() => setReplaceDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Replace Employee</DialogTitle>
          </DialogHeader>
          {replaceDialog && (
            <div className="space-y-3">
              <p className="text-sm">Replacing <strong>{replaceDialog.original}</strong> who denied this shift.</p>
              <div className="space-y-1">
                <Label>New Employee</Label>
                <select value={replaceDialog.newEmployee} onChange={e => {
                  const emp = employees.find(em => em.name === e.target.value);
                  setReplaceDialog(prev => ({ ...prev, newEmployee: e.target.value, newWhatsapp: emp?.whatsapp || emp?.mobile || "" }));
                }} className="w-full h-10 px-3 rounded-md border text-sm">
                  <option value="">Select</option>
                  {employees.map(emp => <option key={emp.name} value={emp.name}>{emp.name}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <Label>WhatsApp</Label>
                <Input value={replaceDialog.newWhatsapp} onChange={e => setReplaceDialog(prev => ({ ...prev, newWhatsapp: e.target.value }))} />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setReplaceDialog(null)}>Cancel</Button>
            <Button onClick={handleReplace} disabled={!replaceDialog?.newEmployee}>Replace & Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Audit Dialog */}
      <Dialog open={showAudit} onOpenChange={setShowAudit}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Audit Trail</DialogTitle></DialogHeader>
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {auditLogs.map((log, i) => (
              <div key={i} className="p-2 border rounded text-xs">
                <div className="flex justify-between">
                  <Badge variant="outline" className="text-xs">{log.action}</Badge>
                  <span className="text-muted-foreground">{log.at?.slice(0, 16).replace("T", " ")}</span>
                </div>
                <p className="mt-1">{log.details}</p>
                <p className="text-muted-foreground">by {log.by}</p>
              </div>
            ))}
            {auditLogs.length === 0 && <p className="text-center text-muted-foreground py-4">No audit logs yet</p>}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
