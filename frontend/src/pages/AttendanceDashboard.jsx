import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  Users,
  UserCheck,
  UserX,
  Clock,
  Calendar,
  Building2,
  RefreshCw,
  Loader2,
  Download,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  BarChart3,
  CalendarDays,
  Eye,
  Lock,
  Unlock,
  ShieldAlert,
  Wallet
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

// Professional color scheme for status cells
const STATUS_STYLES = {
  "P": { bg: "#059669", text: "#fff", label: "Present" },
  "A": { bg: "#dc2626", text: "#fff", label: "Absent" },
  "HD": { bg: "#d97706", text: "#fff", label: "Half Day" },
  "WO": { bg: "#2563eb", text: "#fff", label: "Week Off" },
  "L": { bg: "#7c3aed", text: "#fff", label: "Leave" },
  "LATE": { bg: "#be185d", text: "#fff", label: "Late" },
  // Transfer-aware: "OUT" = employee is at another center on this date due
  // to an active inter-center transfer. Shown as a neutral grey pill so
  // the user understands it is NOT an absence (Feb-2026 transfer fix).
  "OUT": { bg: "#9ca3af", text: "#fff", label: "Shifted Out" },
  "": { bg: "#e5e7eb", text: "#6b7280", label: "-" }
};

export default function AttendanceDashboard() {
  const { session } = useAuth();
  const token = session?.token;
  const isSuperAdmin = session?.is_super_admin === true;
  const isAdmin = session?.is_admin === true;
  const isCenterManager = !isSuperAdmin && !isAdmin && !!session?.center;

  // State
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState("monthly");
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split("T")[0]);
  const [selectedMonth, setSelectedMonth] = useState(new Date().toISOString().slice(0, 7));
  const [filterCenter, setFilterCenter] = useState(
    (isSuperAdmin || isAdmin) ? "all" : (session?.center || "all")
  );
  
  // Data
  const [summary, setSummary] = useState(null);
  const [monthlyGrid, setMonthlyGrid] = useState(null);
  const [dailyGrid, setDailyGrid] = useState(null);
  const [centers, setCenters] = useState([]);
  
  // Lock state
  const [lockStatus, setLockStatus] = useState({ locked: false });
  const [showLockDialog, setShowLockDialog] = useState(false);
  const [lockAction, setLockAction] = useState("lock");

  const hasAccess = isSuperAdmin || isAdmin || isCenterManager;

  useEffect(() => {
    if (token && hasAccess) {
      fetchCenters();
    }
  }, [token, hasAccess]);

  useEffect(() => {
    if (token && hasAccess) {
      fetchSummary();
      fetchLockStatus();
      if (viewMode === "monthly") {
        fetchMonthlyGrid();
      } else {
        fetchDailyGrid();
      }
    }
  }, [token, viewMode, selectedDate, selectedMonth, filterCenter, hasAccess]);

  const fetchCenters = async () => {
    if (isCenterManager) {
      // Center Manager only sees their own center
      setCenters([{ code: session?.center, name: session?.center }]);
      return;
    }
    try {
      const res = await fetch(`${API}/api/sales/centers-list`);
      if (res.ok) {
        const data = await res.json();
        setCenters(data.centers || []);
      }
    } catch (err) {
      console.error("Error fetching centers:", err);
    }
  };

  const fetchLockStatus = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API}/api/attendance-dashboard/lock-status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, month: selectedMonth, center: filterCenter && filterCenter !== "all" ? filterCenter : "" })
      });
      if (res.ok) {
        const data = await res.json();
        setLockStatus(data);
      }
    } catch (err) {
      console.error("Error fetching lock status:", err);
    }
  }, [token, selectedMonth, filterCenter]);

  const handleLockToggle = async () => {
    try {
      const res = await fetch(`${API}/api/attendance-dashboard/lock`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          token, 
          month: selectedMonth,
          action: lockAction,
          center: filterCenter && filterCenter !== "all" ? filterCenter : ""
        })
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(data.message);
        setShowLockDialog(false);
        fetchLockStatus();
      } else {
        const err = await res.json();
        toast.error(err.detail || "Failed to update lock status");
      }
    } catch (err) {
      toast.error("Error updating lock status");
    }
  };

  const fetchSummary = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API}/api/attendance-dashboard/summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          token, 
          date: selectedDate,
          center: filterCenter !== "all" ? filterCenter : null
        })
      });
      if (res.ok) {
        const data = await res.json();
        setSummary(data);
      }
    } catch (err) {
      console.error("Error fetching summary:", err);
    }
  }, [token, selectedDate, filterCenter]);

  const fetchMonthlyGrid = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/attendance-dashboard/monthly-grid`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          token, 
          month: selectedMonth,
          center: filterCenter !== "all" ? filterCenter : null
        })
      });
      if (res.ok) {
        const data = await res.json();
        setMonthlyGrid(data);
      }
    } catch (err) {
      console.error("Error fetching monthly grid:", err);
    } finally {
      setLoading(false);
    }
  }, [token, selectedMonth, filterCenter]);

  const fetchDailyGrid = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/attendance-dashboard/daily-grid`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          token, 
          date: selectedDate,
          center: filterCenter !== "all" ? filterCenter : null
        })
      });
      if (res.ok) {
        const data = await res.json();
        setDailyGrid(data);
      }
    } catch (err) {
      console.error("Error fetching daily grid:", err);
    } finally {
      setLoading(false);
    }
  }, [token, selectedDate, filterCenter]);

  const handleExport = async () => {
    try {
      const endpoint = viewMode === "monthly" 
        ? `${API}/api/attendance-dashboard/export-monthly`
        : `${API}/api/attendance-dashboard/export`;
      
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          token, 
          month: selectedMonth,
          date: selectedDate,
          center: filterCenter !== "all" ? filterCenter : null
        })
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = viewMode === "monthly" 
          ? `Attendance_${filterCenter !== "all" ? filterCenter : "ALL"}_${selectedMonth}.xlsx`
          : `Attendance_${filterCenter !== "all" ? filterCenter : "ALL"}_${selectedDate}.xlsx`;
        a.click();
        toast.success("Report downloaded!");
      }
    } catch (err) {
      toast.error("Export failed");
    }
  };

  if (!hasAccess) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 mx-auto text-yellow-500 mb-4" />
          <h2 className="text-xl font-bold">Access Denied</h2>
          <p className="text-muted-foreground mt-2">Please log in to view attendance</p>
        </div>
      </div>
    );
  }

  const daysInMonth = monthlyGrid?.days_in_month || 31;

  // Get month name for display
  const monthNames = ["January", "February", "March", "April", "May", "June", 
                      "July", "August", "September", "October", "November", "December"];
  const [year, month] = selectedMonth.split("-");
  const monthName = monthNames[parseInt(month) - 1];

  return (
    <div className="space-y-4" data-testid="attendance-dashboard-page">
      {/* Professional Header */}
      <div className="bg-gradient-to-r from-[#8B0000] to-[#B22222] rounded-lg p-4 text-white">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <BarChart3 className="w-7 h-7" />
              Attendance Dashboard
            </h1>
            <p className="text-white/80 text-sm mt-1 flex items-center gap-2">
              <Eye className="w-4 h-4" />
              {isCenterManager ? `${session?.center} Center View` : "View Only Mode • Changes via Center Manager Login"}
            </p>
          </div>
          <Badge className="bg-white/20 text-white border-white/30 self-start">
            {isSuperAdmin ? "Super Admin" : isAdmin ? "Admin" : "Center Manager"} View
          </Badge>
        </div>
      </div>

      {/* Filters Card */}
      <Card className="border-2">
        <CardContent className="p-4">
          <div className="flex flex-wrap items-end gap-4">
            {/* View Mode */}
            <div>
              <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">View</Label>
              <div className="flex gap-1 mt-1">
                <Button
                  variant={viewMode === "monthly" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setViewMode("monthly")}
                  className={viewMode === "monthly" ? "bg-[#8B0000] hover:bg-[#6B0000]" : ""}
                >
                  <CalendarDays className="w-4 h-4 mr-1" />
                  Monthly
                </Button>
                <Button
                  variant={viewMode === "daily" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setViewMode("daily")}
                  className={viewMode === "daily" ? "bg-[#8B0000] hover:bg-[#6B0000]" : ""}
                >
                  <Calendar className="w-4 h-4 mr-1" />
                  Daily
                </Button>
              </div>
            </div>

            {/* Center */}
            <div>
              <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Center</Label>
              {isCenterManager ? (
                <div className="mt-1 h-9 flex items-center px-3 bg-muted rounded-md border text-sm font-medium">
                  <Building2 className="w-4 h-4 mr-2 text-muted-foreground" />
                  {session?.center}
                </div>
              ) : (
                <Select value={filterCenter} onValueChange={setFilterCenter}>
                  <SelectTrigger className="w-56 mt-1" data-testid="center-filter">
                    <SelectValue placeholder="All Centers" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Centers</SelectItem>
                    {centers.map((c, idx) => (
                    <SelectItem key={`${c.code || c.center}-${idx}`} value={c.code || c.center}>
                      {c.code || c.center} - {c.name || ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              )}
            </div>

            {/* Date/Month */}
            <div>
              <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                {viewMode === "monthly" ? "Month" : "Date"}
              </Label>
              {viewMode === "monthly" ? (
                <Input
                  type="month"
                  value={selectedMonth}
                  onChange={(e) => setSelectedMonth(e.target.value)}
                  className="w-40 mt-1"
                />
              ) : (
                <Input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="w-40 mt-1"
                />
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-2 ml-auto">
              <Button variant="outline" onClick={() => {
                fetchSummary();
                fetchLockStatus();
                viewMode === "monthly" ? fetchMonthlyGrid() : fetchDailyGrid();
              }}>
                <RefreshCw className="w-4 h-4 mr-1" />
                Refresh
              </Button>
              <Button onClick={handleExport} className="bg-[#059669] hover:bg-[#047857]">
                <Download className="w-4 h-4 mr-1" />
                Export Excel
              </Button>
            </div>
          </div>
          
          {/* Lock Status & Controls */}
          {viewMode === "monthly" && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t" data-testid="attendance-lock-controls">
              <div className="flex items-center gap-3">
                {lockStatus.locked ? (
                  <Badge className="bg-red-100 text-red-700 border-red-300 flex items-center gap-1 px-3 py-1" data-testid="lock-status-badge-locked">
                    <Lock className="w-4 h-4" />
                    LOCKED - {selectedMonth}
                    {lockStatus.scope === "global" ? " (ALL CENTERS)" : (lockStatus.center ? ` (${lockStatus.center})` : "")}
                  </Badge>
                ) : (
                  <Badge className="bg-green-100 text-green-700 border-green-300 flex items-center gap-1 px-3 py-1" data-testid="lock-status-badge-open">
                    <Unlock className="w-4 h-4" />
                    OPEN - {selectedMonth}
                    {filterCenter && filterCenter !== "all" ? ` (${filterCenter})` : " (ALL CENTERS)"}
                  </Badge>
                )}
                {lockStatus.locked && lockStatus.locked_by && (
                  <span className="text-xs text-muted-foreground">
                    Locked by {lockStatus.locked_by} on {new Date(lockStatus.locked_at).toLocaleDateString()}
                  </span>
                )}
              </div>
              
              {(isSuperAdmin || isAdmin) && (
              <div className="flex items-center gap-2">
                {!lockStatus.locked ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-red-600 border-red-300 hover:bg-red-50"
                    data-testid="lock-month-button"
                    onClick={() => {
                      setLockAction("lock");
                      setShowLockDialog(true);
                    }}
                  >
                    <Lock className="w-4 h-4 mr-1" />
                    {filterCenter && filterCenter !== "all" ? `Lock ${filterCenter}` : "Lock Month (ALL)"}
                  </Button>
                ) : isSuperAdmin ? (
                  // If a global lock is active, user MUST select a specific center to unlock that center,
                  // or leave filter as ALL to unlock the global lock itself.
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-green-600 border-green-300 hover:bg-green-50"
                    data-testid="unlock-month-button"
                    onClick={() => {
                      setLockAction("unlock");
                      setShowLockDialog(true);
                    }}
                  >
                    <Unlock className="w-4 h-4 mr-1" />
                    {filterCenter && filterCenter !== "all" ? `Unlock ${filterCenter}` : "Unlock Month (ALL)"}
                  </Button>
                ) : (
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <ShieldAlert className="w-4 h-4" />
                    Only Super Admin can unlock
                  </span>
                )}
              </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Summary Stats */}
      {summary && (
        <div className="grid grid-cols-4 md:grid-cols-8 gap-2">
          <Card className="bg-slate-50 dark:bg-slate-900">
            <CardContent className="p-3 text-center">
              <Users className="w-5 h-5 mx-auto text-slate-600 mb-1" />
              <div className="text-2xl font-bold">{summary.summary.total_employees}</div>
              <div className="text-xs text-muted-foreground">Total Staff</div>
            </CardContent>
          </Card>
          <Card className="bg-green-50 dark:bg-green-900/20">
            <CardContent className="p-3 text-center">
              <UserCheck className="w-5 h-5 mx-auto text-green-600 mb-1" />
              <div className="text-2xl font-bold text-green-600">{summary.summary.present}</div>
              <div className="text-xs text-green-600/70">Present</div>
            </CardContent>
          </Card>
          <Card className="bg-red-50 dark:bg-red-900/20">
            <CardContent className="p-3 text-center">
              <UserX className="w-5 h-5 mx-auto text-red-600 mb-1" />
              <div className="text-2xl font-bold text-red-600">{summary.summary.absent}</div>
              <div className="text-xs text-red-600/70">Absent</div>
            </CardContent>
          </Card>
          <Card className="bg-amber-50 dark:bg-amber-900/20">
            <CardContent className="p-3 text-center">
              <Clock className="w-5 h-5 mx-auto text-amber-600 mb-1" />
              <div className="text-2xl font-bold text-amber-600">{summary.summary.half_day}</div>
              <div className="text-xs text-amber-600/70">Half Day</div>
            </CardContent>
          </Card>
          <Card className="bg-blue-50 dark:bg-blue-900/20">
            <CardContent className="p-3 text-center">
              <Calendar className="w-5 h-5 mx-auto text-blue-600 mb-1" />
              <div className="text-2xl font-bold text-blue-600">{summary.summary.week_off}</div>
              <div className="text-xs text-blue-600/70">Week Off</div>
            </CardContent>
          </Card>
          <Card className="bg-purple-50 dark:bg-purple-900/20">
            <CardContent className="p-3 text-center">
              <Calendar className="w-5 h-5 mx-auto text-purple-600 mb-1" />
              <div className="text-2xl font-bold text-purple-600">{summary.summary.leave}</div>
              <div className="text-xs text-purple-600/70">Leave</div>
            </CardContent>
          </Card>
          <Card className="bg-gray-50 dark:bg-gray-900/20">
            <CardContent className="p-3 text-center">
              <AlertTriangle className="w-5 h-5 mx-auto text-gray-500 mb-1" />
              <div className="text-2xl font-bold text-gray-500">{summary.summary.not_marked}</div>
              <div className="text-xs text-gray-500/70">Not Marked</div>
            </CardContent>
          </Card>
          <Card className="bg-[#8B0000]/10 border-[#8B0000]/30">
            <CardContent className="p-3 text-center">
              <TrendingUp className="w-5 h-5 mx-auto text-[#8B0000] mb-1" />
              <div className="text-2xl font-bold text-[#8B0000]">{summary.summary.attendance_percentage}%</div>
              <div className="text-xs text-[#8B0000]/70">Attendance</div>
            </CardContent>
          </Card>
          <Card className="bg-orange-50 dark:bg-orange-900/20 border-orange-200" data-testid="advance-summary-card">
            <CardContent className="p-3 text-center">
              <Wallet className="w-5 h-5 mx-auto text-orange-600 mb-1" />
              <div className="text-2xl font-bold text-orange-600">
                {summary.summary.total_advance ? `${Math.round(summary.summary.total_advance).toLocaleString()}` : "0"}
              </div>
              <div className="text-xs text-orange-600/70">Advance ({summary.summary.advance_count || 0})</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-2 px-1">
        {Object.entries(STATUS_STYLES).filter(([k]) => k).map(([code, style]) => (
          <div 
            key={code} 
            className="flex items-center gap-1.5 text-xs"
          >
            <span 
              className="w-6 h-5 rounded text-center font-bold flex items-center justify-center"
              style={{ backgroundColor: style.bg, color: style.text }}
            >
              {code}
            </span>
            <span className="text-muted-foreground">{style.label}</span>
          </div>
        ))}
      </div>

      {/* Main Grid */}
      <Card className="border-2 overflow-hidden">
        <CardHeader className="py-3 bg-muted/30 border-b">
          <CardTitle className="text-sm flex items-center gap-2">
            <Building2 className="w-4 h-4" />
            {viewMode === "monthly" 
              ? `${monthName} ${year} Attendance Register` 
              : `Attendance Register - ${selectedDate}`}
            {filterCenter !== "all" && (
              <Badge variant="outline" className="ml-2">{filterCenter}</Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-8 h-8 animate-spin text-[#8B0000]" />
            </div>
          ) : viewMode === "monthly" ? (
            /* Monthly Grid */
            <div className="overflow-x-auto">
              <table className="w-full text-xs border-collapse min-w-max">
                <thead>
                  <tr className="bg-[#8B0000] text-white">
                    <th className="border border-[#6B0000] p-2 text-left font-semibold sticky left-0 bg-[#8B0000] z-20 min-w-[150px]">
                      Employee Name
                    </th>
                    <th className="border border-[#6B0000] p-2 text-left font-semibold min-w-[70px]">Center</th>
                    {Array.from({ length: daysInMonth }, (_, i) => (
                      <th key={i} className="border border-[#6B0000] p-1 text-center font-semibold w-7">
                        {i + 1}
                      </th>
                    ))}
                    <th className="border border-[#6B0000] p-1 text-center font-semibold bg-green-700 w-8">P</th>
                    <th className="border border-[#6B0000] p-1 text-center font-semibold bg-red-700 w-8">A</th>
                    <th className="border border-[#6B0000] p-1 text-center font-semibold bg-amber-600 w-8">HD</th>
                    <th className="border border-[#6B0000] p-1 text-center font-semibold bg-blue-700 w-8">WO</th>
                    <th className="border border-[#6B0000] p-1 text-center font-semibold bg-purple-700 w-8">L</th>
                    <th className="border border-[#6B0000] p-1 text-center font-semibold bg-slate-700 w-10">%</th>
                    <th className="border border-[#6B0000] p-1 text-center font-semibold bg-orange-700 w-16">Adv</th>
                  </tr>
                </thead>
                <tbody>
                  {monthlyGrid?.employees?.map((emp, empIdx) => {
                    const counts = { P: 0, A: 0, HD: 0, WO: 0, L: 0, LATE: 0 };
                    emp.attendance.forEach(status => {
                      if (status && counts.hasOwnProperty(status)) counts[status]++;
                    });
                    const present = counts.P + counts.LATE;
                    const working = daysInMonth - counts.WO - counts.L;
                    const pct = working > 0 ? Math.round((present + counts.HD * 0.5) / working * 100) : 0;
                    const isEven = empIdx % 2 === 0;

                    return (
                      <tr key={`${emp.center}-${emp.name}-${empIdx}`} className={`${isEven ? "bg-white dark:bg-slate-950" : "bg-gray-50 dark:bg-slate-900"} ${emp.transfer_tag === "TRANSFERRED_OUT" ? "opacity-80" : ""}`}>
                        <td className={`border border-gray-200 dark:border-gray-700 p-1.5 font-medium sticky left-0 z-10 ${isEven ? "bg-white dark:bg-slate-950" : "bg-gray-50 dark:bg-slate-900"}`}>
                          <div className="flex items-center gap-1">
                            <span className="truncate block max-w-[120px]" title={emp.name}>{emp.name}</span>
                            {emp.transfer_tag === "TRANSFERRED_OUT" && (
                              <span className="text-[8px] px-1 py-0.5 bg-orange-100 text-orange-700 border border-orange-300 rounded whitespace-nowrap" title={`Transferred to ${emp.transfer_info?.to_center || "?"} on ${emp.transfer_info?.transfer_start || "?"}`}>
                                OUT
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="border border-gray-200 dark:border-gray-700 p-1.5 text-muted-foreground font-mono">
                          {emp.center}
                        </td>
                        {emp.attendance.map((status, dayIdx) => {
                          const style = STATUS_STYLES[status] || STATUS_STYLES[""];
                          return (
                            <td 
                              key={dayIdx}
                              className="border border-gray-200 dark:border-gray-700 p-0 text-center"
                              title={`Day ${dayIdx + 1}: ${style.label}`}
                            >
                              <span 
                                className="block w-full py-0.5 font-bold text-[10px]"
                                style={{ backgroundColor: style.bg, color: style.text }}
                              >
                                {status || "-"}
                              </span>
                            </td>
                          );
                        })}
                        <td className="border border-gray-200 dark:border-gray-700 p-1 text-center font-bold text-green-600 bg-green-50 dark:bg-green-900/20">{present}</td>
                        <td className="border border-gray-200 dark:border-gray-700 p-1 text-center font-bold text-red-600 bg-red-50 dark:bg-red-900/20">{counts.A}</td>
                        <td className="border border-gray-200 dark:border-gray-700 p-1 text-center font-bold text-amber-600 bg-amber-50 dark:bg-amber-900/20">{counts.HD}</td>
                        <td className="border border-gray-200 dark:border-gray-700 p-1 text-center font-bold text-blue-600 bg-blue-50 dark:bg-blue-900/20">{counts.WO}</td>
                        <td className="border border-gray-200 dark:border-gray-700 p-1 text-center font-bold text-purple-600 bg-purple-50 dark:bg-purple-900/20">{counts.L}</td>
                        <td className={`border border-gray-200 dark:border-gray-700 p-1 text-center font-bold ${
                          pct >= 85 ? 'text-green-600 bg-green-50 dark:bg-green-900/20' : 
                          pct >= 70 ? 'text-amber-600 bg-amber-50 dark:bg-amber-900/20' : 
                          'text-red-600 bg-red-50 dark:bg-red-900/20'
                        }`}>
                          {pct}%
                        </td>
                        <td className={`border border-gray-200 dark:border-gray-700 p-1 text-center font-bold text-[10px] ${
                          emp.advance > 0 ? 'text-orange-700 bg-orange-50 dark:bg-orange-900/20' : 'text-gray-400'
                        }`} data-testid={`advance-${emp.name}`}>
                          {emp.advance > 0 ? Math.round(emp.advance).toLocaleString() : "-"}
                        </td>
                      </tr>
                    );
                  })}
                  {(!monthlyGrid?.employees || monthlyGrid.employees.length === 0) && (
                    <tr>
                      <td colSpan={daysInMonth + 9} className="text-center py-12 text-muted-foreground">
                        <Calendar className="w-12 h-12 mx-auto mb-3 opacity-30" />
                        <p>No attendance data found for selected filters</p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            /* Daily Grid */
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="bg-[#8B0000] text-white">
                    <th className="border border-[#6B0000] p-2 text-left font-semibold">Employee Name</th>
                    <th className="border border-[#6B0000] p-2 text-left font-semibold">Center</th>
                    <th className="border border-[#6B0000] p-2 text-left font-semibold">Designation</th>
                    <th className="border border-[#6B0000] p-2 text-center font-semibold w-32">Status</th>
                    <th className="border border-[#6B0000] p-2 text-left font-semibold">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {dailyGrid?.employees?.map((emp, idx) => {
                    const style = STATUS_STYLES[emp.status] || STATUS_STYLES[""];
                    const isEven = idx % 2 === 0;
                    return (
                      <tr key={`${emp.center}-${emp.name}-${idx}`} className={isEven ? "bg-white dark:bg-slate-950" : "bg-gray-50 dark:bg-slate-900"}>
                        <td className="border border-gray-200 dark:border-gray-700 p-2 font-medium">{emp.name}</td>
                        <td className="border border-gray-200 dark:border-gray-700 p-2 text-muted-foreground font-mono">{emp.center}</td>
                        <td className="border border-gray-200 dark:border-gray-700 p-2">{emp.designation || "-"}</td>
                        <td className="border border-gray-200 dark:border-gray-700 p-2 text-center">
                          <span 
                            className="inline-block px-3 py-1 rounded font-bold text-xs"
                            style={{ backgroundColor: style.bg, color: style.text }}
                          >
                            {emp.status || "-"} {emp.status && `(${style.label})`}
                          </span>
                        </td>
                        <td className="border border-gray-200 dark:border-gray-700 p-2 text-muted-foreground">{emp.notes || "-"}</td>
                      </tr>
                    );
                  })}
                  {(!dailyGrid?.employees || dailyGrid.employees.length === 0) && (
                    <tr>
                      <td colSpan={5} className="text-center py-12 text-muted-foreground">
                        <Calendar className="w-12 h-12 mx-auto mb-3 opacity-30" />
                        <p>No attendance data found for {selectedDate}</p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Center-wise Summary */}
      {filterCenter === "all" && monthlyGrid?.center_summary && monthlyGrid.center_summary.length > 0 && (
        <Card className="border-2">
          <CardHeader className="py-3 bg-muted/30 border-b">
            <CardTitle className="text-sm flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              Center-wise Performance Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="bg-slate-100 dark:bg-slate-800">
                    <th className="border border-gray-200 dark:border-gray-700 p-2 text-left font-semibold">Center</th>
                    <th className="border border-gray-200 dark:border-gray-700 p-2 text-center font-semibold">Staff</th>
                    <th className="border border-gray-200 dark:border-gray-700 p-2 text-center font-semibold text-green-600">Present</th>
                    <th className="border border-gray-200 dark:border-gray-700 p-2 text-center font-semibold text-red-600">Absent</th>
                    <th className="border border-gray-200 dark:border-gray-700 p-2 text-center font-semibold text-amber-600">Half Day</th>
                    <th className="border border-gray-200 dark:border-gray-700 p-2 text-center font-semibold text-blue-600">Week Off</th>
                    <th className="border border-gray-200 dark:border-gray-700 p-2 text-center font-semibold text-purple-600">Leave</th>
                    <th className="border border-gray-200 dark:border-gray-700 p-2 text-center font-semibold">Attendance %</th>
                    <th className="border border-gray-200 dark:border-gray-700 p-2 text-center font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {monthlyGrid.center_summary.map((center, idx) => {
                    const isEven = idx % 2 === 0;
                    return (
                      <tr key={`${center.center}-${idx}`} className={isEven ? "bg-white dark:bg-slate-950" : "bg-gray-50 dark:bg-slate-900"}>
                        <td className="border border-gray-200 dark:border-gray-700 p-2 font-semibold">{center.center}</td>
                        <td className="border border-gray-200 dark:border-gray-700 p-2 text-center">{center.total_staff}</td>
                        <td className="border border-gray-200 dark:border-gray-700 p-2 text-center text-green-600 font-medium">{center.present}</td>
                        <td className="border border-gray-200 dark:border-gray-700 p-2 text-center text-red-600 font-medium">{center.absent}</td>
                        <td className="border border-gray-200 dark:border-gray-700 p-2 text-center text-amber-600 font-medium">{center.half_day}</td>
                        <td className="border border-gray-200 dark:border-gray-700 p-2 text-center text-blue-600 font-medium">{center.week_off}</td>
                        <td className="border border-gray-200 dark:border-gray-700 p-2 text-center text-purple-600 font-medium">{center.leave}</td>
                        <td className="border border-gray-200 dark:border-gray-700 p-2 text-center">
                          <span className={`font-bold ${
                            center.attendance_pct >= 85 ? 'text-green-600' : 
                            center.attendance_pct >= 70 ? 'text-amber-600' : 
                            'text-red-600'
                          }`}>
                            {center.attendance_pct}%
                          </span>
                        </td>
                        <td className="border border-gray-200 dark:border-gray-700 p-2 text-center">
                          {center.attendance_pct < 70 ? (
                            <span className="inline-flex items-center gap-1 text-red-600 text-xs font-medium">
                              <AlertTriangle className="w-4 h-4" /> Low
                            </span>
                          ) : center.attendance_pct < 85 ? (
                            <span className="inline-flex items-center gap-1 text-amber-600 text-xs font-medium">
                              <AlertTriangle className="w-4 h-4" /> Medium
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-green-600 text-xs font-medium">
                              <CheckCircle2 className="w-4 h-4" /> Good
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Footer Note */}
      <div className="text-center text-xs text-muted-foreground py-2">
        <p>This is a read-only dashboard. To modify attendance, please use the Daily Attendance page via Center Manager login.</p>
      </div>

      {/* Lock Confirmation Dialog */}
      <Dialog open={showLockDialog} onOpenChange={setShowLockDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {lockAction === "lock" ? (
                <>
                  <Lock className="w-5 h-5 text-red-600" />
                  Lock Attendance for {selectedMonth}
                  {filterCenter && filterCenter !== "all" ? ` — ${filterCenter}` : " — ALL CENTERS"}
                </>
              ) : (
                <>
                  <Unlock className="w-5 h-5 text-green-600" />
                  Unlock Attendance for {selectedMonth}
                  {filterCenter && filterCenter !== "all" ? ` — ${filterCenter}` : " — ALL CENTERS"}
                </>
              )}
            </DialogTitle>
          </DialogHeader>
          
          <div className="py-4">
            {lockAction === "lock" ? (
              <div className="space-y-3">
                <p className="text-sm">
                  Are you sure you want to <strong className="text-red-600">lock</strong> attendance for <strong>{selectedMonth}</strong>
                  {filterCenter && filterCenter !== "all" ? <> at <strong>{filterCenter}</strong></> : <> across <strong>ALL CENTERS</strong></>}?
                </p>
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 rounded-lg p-3">
                  <p className="text-sm text-amber-800 dark:text-amber-200 flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <span>
                      Once locked, <strong>no one</strong> (including center managers) will be able to edit attendance for
                      {filterCenter && filterCenter !== "all" ? <> <strong>{filterCenter}</strong></> : <> <strong>any center</strong></>} this month. 
                      Only Super Admin can unlock.
                    </span>
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm">
                  Are you sure you want to <strong className="text-green-600">unlock</strong> attendance for <strong>{selectedMonth}</strong>
                  {filterCenter && filterCenter !== "all" ? <> at <strong>{filterCenter}</strong></> : <> across <strong>ALL CENTERS</strong></>}?
                </p>
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 rounded-lg p-3">
                  <p className="text-sm text-blue-800 dark:text-blue-200 flex items-start gap-2">
                    <ShieldAlert className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <span>
                      After unlocking, center managers will be able to edit attendance for 
                      {filterCenter && filterCenter !== "all" ? <> <strong>{filterCenter}</strong></> : <> <strong>this month globally</strong></>}.
                      Other centers' locks are <strong>not</strong> affected.
                    </span>
                  </p>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLockDialog(false)} data-testid="lock-dialog-cancel">
              Cancel
            </Button>
            <Button 
              onClick={handleLockToggle}
              data-testid="lock-dialog-confirm"
              className={lockAction === "lock" ? "bg-red-600 hover:bg-red-700" : "bg-green-600 hover:bg-green-700"}
            >
              {lockAction === "lock" ? (
                <>
                  <Lock className="w-4 h-4 mr-1" />
                  Yes, Lock {filterCenter && filterCenter !== "all" ? filterCenter : "All Centers"}
                </>
              ) : (
                <>
                  <Unlock className="w-4 h-4 mr-1" />
                  Yes, Unlock {filterCenter && filterCenter !== "all" ? filterCenter : "All Centers"}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
