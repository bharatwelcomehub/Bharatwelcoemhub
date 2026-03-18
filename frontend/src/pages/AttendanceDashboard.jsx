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
  Eye
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
  "": { bg: "#e5e7eb", text: "#6b7280", label: "-" }
};

export default function AttendanceDashboard() {
  const { session } = useAuth();
  const token = session?.token;
  const isSuperAdmin = session?.is_super_admin === true;
  const isAdmin = session?.is_admin === true;

  // State
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState("monthly");
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split("T")[0]);
  const [selectedMonth, setSelectedMonth] = useState(new Date().toISOString().slice(0, 7));
  const [filterCenter, setFilterCenter] = useState("all");
  
  // Data
  const [summary, setSummary] = useState(null);
  const [monthlyGrid, setMonthlyGrid] = useState(null);
  const [dailyGrid, setDailyGrid] = useState(null);
  const [centers, setCenters] = useState([]);

  const hasAccess = isSuperAdmin || isAdmin;

  useEffect(() => {
    if (token && hasAccess) {
      fetchCenters();
    }
  }, [token, hasAccess]);

  useEffect(() => {
    if (token && hasAccess) {
      fetchSummary();
      if (viewMode === "monthly") {
        fetchMonthlyGrid();
      } else {
        fetchDailyGrid();
      }
    }
  }, [token, viewMode, selectedDate, selectedMonth, filterCenter, hasAccess]);

  const fetchCenters = async () => {
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
          <p className="text-muted-foreground mt-2">Admin or Super Admin access required</p>
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
              View Only Mode • Changes via Center Manager Login
            </p>
          </div>
          <Badge className="bg-white/20 text-white border-white/30 self-start">
            {isSuperAdmin ? "Super Admin" : "Admin"} View
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
              <Select value={filterCenter} onValueChange={setFilterCenter}>
                <SelectTrigger className="w-56 mt-1">
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
                      <tr key={`${emp.center}-${emp.name}-${empIdx}`} className={isEven ? "bg-white dark:bg-slate-950" : "bg-gray-50 dark:bg-slate-900"}>
                        <td className={`border border-gray-200 dark:border-gray-700 p-1.5 font-medium sticky left-0 z-10 ${isEven ? "bg-white dark:bg-slate-950" : "bg-gray-50 dark:bg-slate-900"}`}>
                          <span className="truncate block max-w-[140px]" title={emp.name}>{emp.name}</span>
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
                      </tr>
                    );
                  })}
                  {(!monthlyGrid?.employees || monthlyGrid.employees.length === 0) && (
                    <tr>
                      <td colSpan={daysInMonth + 8} className="text-center py-12 text-muted-foreground">
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
    </div>
  );
}
