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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
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
  Eye,
  Edit,
  TrendingUp,
  BarChart3,
  FileSpreadsheet,
  Grid3X3,
  CalendarDays
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

// Status colors for grid cells
const STATUS_COLORS = {
  "P": "bg-green-500/30 text-green-300 border-green-500/50",
  "A": "bg-red-500/30 text-red-300 border-red-500/50",
  "HD": "bg-yellow-500/30 text-yellow-300 border-yellow-500/50",
  "WO": "bg-blue-500/30 text-blue-300 border-blue-500/50",
  "L": "bg-orange-500/30 text-orange-300 border-orange-500/50",
  "LATE": "bg-purple-500/30 text-purple-300 border-purple-500/50",
  "": "bg-gray-500/20 text-gray-400 border-gray-500/30"
};

const STATUS_LABELS = {
  "P": "Present",
  "A": "Absent", 
  "HD": "Half Day",
  "WO": "Week Off",
  "L": "Leave",
  "LATE": "Late",
  "": "Not Marked"
};

export default function AttendanceDashboard() {
  const { session } = useAuth();
  const token = session?.token;
  const isSuperAdmin = session?.is_super_admin === true;
  const isAdmin = session?.is_admin === true;

  // State
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState("monthly"); // monthly or daily
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split("T")[0]);
  const [selectedMonth, setSelectedMonth] = useState(new Date().toISOString().slice(0, 7));
  const [filterCenter, setFilterCenter] = useState("all");
  
  // Data
  const [summary, setSummary] = useState(null);
  const [monthlyGrid, setMonthlyGrid] = useState(null);
  const [dailyGrid, setDailyGrid] = useState(null);
  const [centers, setCenters] = useState([]);
  const [statusOptions, setStatusOptions] = useState([]);

  // Edit dialog (Super Admin only)
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingCell, setEditingCell] = useState(null);
  const [editStatus, setEditStatus] = useState("");
  const [editNotes, setEditNotes] = useState("");

  // Check access
  const hasAccess = isSuperAdmin || isAdmin;

  // Load initial data
  useEffect(() => {
    if (token && hasAccess) {
      fetchStatusOptions();
      fetchCenters();
    }
  }, [token, hasAccess]);

  // Fetch data when filters change
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

  const fetchStatusOptions = async () => {
    try {
      const res = await fetch(`${API}/api/attendance-dashboard/status-options`);
      if (res.ok) {
        const data = await res.json();
        setStatusOptions(data.statuses || []);
      }
    } catch (err) {
      console.error("Error fetching status options:", err);
    }
  };

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

  const handleExport = async (type) => {
    try {
      const endpoint = type === "monthly" 
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
        a.download = type === "monthly" 
          ? `Monthly_Attendance_${filterCenter !== "all" ? filterCenter : "ALL"}_${selectedMonth}.xlsx`
          : `Daily_Attendance_${filterCenter !== "all" ? filterCenter : "ALL"}_${selectedDate}.xlsx`;
        a.click();
        toast.success("Report downloaded!");
      }
    } catch (err) {
      toast.error("Export failed");
    }
  };

  const handleCellClick = (employee, date, currentStatus, center) => {
    if (!isSuperAdmin) {
      toast.error("Only Super Admin can edit attendance");
      return;
    }
    setEditingCell({ employee, date, center });
    setEditStatus(currentStatus || "");
    setEditNotes("");
    setShowEditDialog(true);
  };

  const handleSaveEdit = async () => {
    if (!editingCell) return;
    try {
      const res = await fetch(`${API}/api/attendance-dashboard/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          center: editingCell.center,
          date: editingCell.date,
          employee_name: editingCell.employee,
          status: editStatus,
          notes: editNotes
        })
      });
      if (res.ok) {
        toast.success("Attendance updated!");
        setShowEditDialog(false);
        if (viewMode === "monthly") {
          fetchMonthlyGrid();
        } else {
          fetchDailyGrid();
        }
        fetchSummary();
      } else {
        const err = await res.json();
        toast.error(err.detail || "Update failed");
      }
    } catch (err) {
      toast.error("Error updating attendance");
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

  return (
    <div className="space-y-4" data-testid="attendance-dashboard-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <BarChart3 className="w-7 h-7" />
            Attendance Dashboard
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {isSuperAdmin ? "Full Access (Click cell to edit)" : "Read-only View"}
          </p>
        </div>
        <Badge variant={isSuperAdmin ? "default" : "secondary"}>
          {isSuperAdmin ? "Super Admin" : "Admin (View Only)"}
        </Badge>
      </div>

      {/* Filters & Controls */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-end gap-4">
            {/* View Mode Toggle */}
            <div>
              <Label className="text-xs">View Mode</Label>
              <div className="flex gap-1 mt-1">
                <Button
                  variant={viewMode === "monthly" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setViewMode("monthly")}
                >
                  <CalendarDays className="w-4 h-4 mr-1" />
                  Monthly
                </Button>
                <Button
                  variant={viewMode === "daily" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setViewMode("daily")}
                >
                  <Calendar className="w-4 h-4 mr-1" />
                  Daily
                </Button>
              </div>
            </div>

            {/* Center Filter */}
            <div>
              <Label className="text-xs">Select Center</Label>
              <Select value={filterCenter} onValueChange={setFilterCenter}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="All Centers" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Centers</SelectItem>
                  {centers.map((c, idx) => (
                    <SelectItem key={`${c.code || c.center}-${idx}`} value={c.code || c.center}>
                      {c.name || c.code || c.center}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Date/Month Selector */}
            {viewMode === "monthly" ? (
              <div>
                <Label className="text-xs">Select Month</Label>
                <Input
                  type="month"
                  value={selectedMonth}
                  onChange={(e) => setSelectedMonth(e.target.value)}
                  className="w-40"
                />
              </div>
            ) : (
              <div>
                <Label className="text-xs">Select Date</Label>
                <Input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="w-40"
                />
              </div>
            )}

            {/* Refresh */}
            <Button variant="outline" onClick={() => {
              fetchSummary();
              viewMode === "monthly" ? fetchMonthlyGrid() : fetchDailyGrid();
            }}>
              <RefreshCw className="w-4 h-4 mr-1" />
              Refresh
            </Button>

            {/* Export */}
            <div className="flex gap-2 ml-auto">
              <Button variant="outline" onClick={() => handleExport(viewMode)}>
                <Download className="w-4 h-4 mr-1" />
                Export Excel
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards - Compact */}
      {summary && (
        <div className="grid grid-cols-4 md:grid-cols-8 gap-2">
          <Card className="p-2">
            <div className="text-xs text-muted-foreground">Total</div>
            <div className="text-lg font-bold">{summary.summary.total_employees}</div>
          </Card>
          <Card className="p-2">
            <div className="text-xs text-green-400">Present</div>
            <div className="text-lg font-bold text-green-400">{summary.summary.present}</div>
          </Card>
          <Card className="p-2">
            <div className="text-xs text-red-400">Absent</div>
            <div className="text-lg font-bold text-red-400">{summary.summary.absent}</div>
          </Card>
          <Card className="p-2">
            <div className="text-xs text-yellow-400">Half Day</div>
            <div className="text-lg font-bold text-yellow-400">{summary.summary.half_day}</div>
          </Card>
          <Card className="p-2">
            <div className="text-xs text-blue-400">Week Off</div>
            <div className="text-lg font-bold text-blue-400">{summary.summary.week_off}</div>
          </Card>
          <Card className="p-2">
            <div className="text-xs text-orange-400">Leave</div>
            <div className="text-lg font-bold text-orange-400">{summary.summary.leave}</div>
          </Card>
          <Card className="p-2">
            <div className="text-xs text-gray-400">Not Marked</div>
            <div className="text-lg font-bold text-gray-400">{summary.summary.not_marked}</div>
          </Card>
          <Card className="p-2 bg-primary/10">
            <div className="text-xs text-primary">Attendance %</div>
            <div className="text-lg font-bold text-primary">{summary.summary.attendance_percentage}%</div>
          </Card>
        </div>
      )}

      {/* Status Legend */}
      <div className="flex flex-wrap gap-2 text-xs">
        {Object.entries(STATUS_LABELS).filter(([k]) => k).map(([code, label]) => (
          <div key={code} className={`px-2 py-1 rounded border ${STATUS_COLORS[code]}`}>
            {code} = {label}
          </div>
        ))}
      </div>

      {/* Main Grid View */}
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Grid3X3 className="w-4 h-4" />
            {viewMode === "monthly" 
              ? `Monthly Attendance Grid - ${selectedMonth}` 
              : `Daily Attendance - ${selectedDate}`}
            {filterCenter !== "all" && <Badge variant="outline">{filterCenter}</Badge>}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
          ) : viewMode === "monthly" ? (
            /* Monthly Grid View */
            <div className="overflow-x-auto">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-muted/50">
                    <th className="border p-1 text-left sticky left-0 bg-muted/50 z-10 min-w-[120px]">Employee</th>
                    <th className="border p-1 text-left min-w-[80px]">Center</th>
                    {Array.from({ length: daysInMonth }, (_, i) => (
                      <th key={i} className="border p-1 text-center w-8">{i + 1}</th>
                    ))}
                    <th className="border p-1 text-center bg-green-900/20">P</th>
                    <th className="border p-1 text-center bg-red-900/20">A</th>
                    <th className="border p-1 text-center bg-yellow-900/20">HD</th>
                    <th className="border p-1 text-center bg-blue-900/20">WO</th>
                    <th className="border p-1 text-center bg-orange-900/20">L</th>
                    <th className="border p-1 text-center bg-primary/20">%</th>
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

                    return (
                      <tr key={`${emp.center}-${emp.name}-${empIdx}`} className="hover:bg-muted/30">
                        <td className="border p-1 font-medium sticky left-0 bg-background z-10 truncate max-w-[120px]" title={emp.name}>
                          {emp.name}
                        </td>
                        <td className="border p-1 text-muted-foreground">{emp.center}</td>
                        {emp.attendance.map((status, dayIdx) => (
                          <td 
                            key={dayIdx}
                            className={`border p-0 text-center cursor-pointer hover:opacity-80 ${STATUS_COLORS[status] || STATUS_COLORS[""]}`}
                            onClick={() => handleCellClick(
                              emp.name, 
                              `${selectedMonth}-${String(dayIdx + 1).padStart(2, '0')}`,
                              status,
                              emp.center
                            )}
                            title={`${emp.name} - Day ${dayIdx + 1}: ${STATUS_LABELS[status] || "Not Marked"}`}
                          >
                            {status || "-"}
                          </td>
                        ))}
                        <td className="border p-1 text-center font-medium text-green-400">{present}</td>
                        <td className="border p-1 text-center font-medium text-red-400">{counts.A}</td>
                        <td className="border p-1 text-center font-medium text-yellow-400">{counts.HD}</td>
                        <td className="border p-1 text-center font-medium text-blue-400">{counts.WO}</td>
                        <td className="border p-1 text-center font-medium text-orange-400">{counts.L}</td>
                        <td className={`border p-1 text-center font-bold ${pct >= 85 ? 'text-green-400' : pct >= 70 ? 'text-yellow-400' : 'text-red-400'}`}>
                          {pct}%
                        </td>
                      </tr>
                    );
                  })}
                  {(!monthlyGrid?.employees || monthlyGrid.employees.length === 0) && (
                    <tr>
                      <td colSpan={daysInMonth + 8} className="text-center py-8 text-muted-foreground">
                        No attendance data found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            /* Daily Grid View */
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="bg-muted/50">
                    <th className="border p-2 text-left">Employee</th>
                    <th className="border p-2 text-left">Center</th>
                    <th className="border p-2 text-left">Designation</th>
                    <th className="border p-2 text-center">Status</th>
                    <th className="border p-2 text-left">Notes</th>
                    {isSuperAdmin && <th className="border p-2 text-center">Action</th>}
                  </tr>
                </thead>
                <tbody>
                  {dailyGrid?.employees?.map((emp, idx) => (
                    <tr key={`${emp.center}-${emp.name}-${idx}`} className="hover:bg-muted/30">
                      <td className="border p-2 font-medium">{emp.name}</td>
                      <td className="border p-2 text-muted-foreground">{emp.center}</td>
                      <td className="border p-2">{emp.designation || "-"}</td>
                      <td className="border p-2 text-center">
                        <span className={`px-2 py-1 rounded text-xs ${STATUS_COLORS[emp.status] || STATUS_COLORS[""]}`}>
                          {emp.status || "-"} {emp.status && `(${STATUS_LABELS[emp.status]})`}
                        </span>
                      </td>
                      <td className="border p-2 text-sm text-muted-foreground">{emp.notes || "-"}</td>
                      {isSuperAdmin && (
                        <td className="border p-2 text-center">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleCellClick(emp.name, selectedDate, emp.status, emp.center)}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                        </td>
                      )}
                    </tr>
                  ))}
                  {(!dailyGrid?.employees || dailyGrid.employees.length === 0) && (
                    <tr>
                      <td colSpan={isSuperAdmin ? 6 : 5} className="text-center py-8 text-muted-foreground">
                        No attendance data found for {selectedDate}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Center-wise Summary (when viewing all centers) */}
      {filterCenter === "all" && monthlyGrid?.center_summary && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              Center-wise Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="bg-muted/50">
                    <th className="border p-2 text-left">Center</th>
                    <th className="border p-2 text-center">Staff</th>
                    <th className="border p-2 text-center text-green-400">Present</th>
                    <th className="border p-2 text-center text-red-400">Absent</th>
                    <th className="border p-2 text-center text-yellow-400">HD</th>
                    <th className="border p-2 text-center text-blue-400">WO</th>
                    <th className="border p-2 text-center text-orange-400">Leave</th>
                    <th className="border p-2 text-center">Attendance %</th>
                    <th className="border p-2 text-center">Alert</th>
                  </tr>
                </thead>
                <tbody>
                  {monthlyGrid.center_summary.map((center, idx) => (
                    <tr key={`${center.center}-${idx}`} className="hover:bg-muted/30">
                      <td className="border p-2 font-medium">{center.center}</td>
                      <td className="border p-2 text-center">{center.total_staff}</td>
                      <td className="border p-2 text-center text-green-400">{center.present}</td>
                      <td className="border p-2 text-center text-red-400">{center.absent}</td>
                      <td className="border p-2 text-center text-yellow-400">{center.half_day}</td>
                      <td className="border p-2 text-center text-blue-400">{center.week_off}</td>
                      <td className="border p-2 text-center text-orange-400">{center.leave}</td>
                      <td className="border p-2 text-center">
                        <span className={`font-bold ${center.attendance_pct >= 85 ? 'text-green-400' : center.attendance_pct >= 70 ? 'text-yellow-400' : 'text-red-400'}`}>
                          {center.attendance_pct}%
                        </span>
                      </td>
                      <td className="border p-2 text-center">
                        {center.attendance_pct < 70 ? (
                          <AlertTriangle className="w-4 h-4 text-red-500 mx-auto" />
                        ) : center.attendance_pct < 85 ? (
                          <AlertTriangle className="w-4 h-4 text-yellow-500 mx-auto" />
                        ) : (
                          <CheckCircle2 className="w-4 h-4 text-green-500 mx-auto" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Edit Dialog (Super Admin Only) */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Attendance</DialogTitle>
          </DialogHeader>
          {editingCell && (
            <div className="space-y-4">
              <div>
                <Label>Employee</Label>
                <Input value={editingCell.employee} disabled />
              </div>
              <div>
                <Label>Date</Label>
                <Input value={editingCell.date} disabled />
              </div>
              <div>
                <Label>Center</Label>
                <Input value={editingCell.center} disabled />
              </div>
              <div>
                <Label>Status</Label>
                <Select value={editStatus} onValueChange={setEditStatus}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select status..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Not Marked</SelectItem>
                    {statusOptions.map((s, idx) => (
                      <SelectItem key={`${s.code}-${idx}`} value={s.code}>{s.code} - {s.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Notes</Label>
                <Input
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="Optional notes..."
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>Cancel</Button>
            <Button onClick={handleSaveEdit}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
