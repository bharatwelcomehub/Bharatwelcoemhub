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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
  XCircle,
  ArrowUp,
  ArrowDown,
  Eye,
  Edit,
  TrendingUp,
  BarChart3,
  PieChart,
  ChevronLeft,
  FileSpreadsheet
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart as RechartsPieChart,
  Pie,
  Cell
} from "recharts";

const API = process.env.REACT_APP_BACKEND_URL;

// Status configuration
const STATUS_CONFIG = {
  "P": { label: "Present", color: "bg-green-500/20 text-green-400 border-green-500/30", icon: UserCheck },
  "A": { label: "Absent", color: "bg-red-500/20 text-red-400 border-red-500/30", icon: UserX },
  "HD": { label: "Half Day", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30", icon: Clock },
  "WO": { label: "Week Off", color: "bg-blue-500/20 text-blue-400 border-blue-500/30", icon: Calendar },
  "L": { label: "Leave", color: "bg-orange-500/20 text-orange-400 border-orange-500/30", icon: Calendar },
  "LATE": { label: "Late", color: "bg-purple-500/20 text-purple-400 border-purple-500/30", icon: Clock },
  "": { label: "Not Marked", color: "bg-gray-500/20 text-gray-400 border-gray-500/30", icon: XCircle }
};

const CHART_COLORS = ["#22c55e", "#ef4444", "#eab308", "#3b82f6", "#f97316", "#a855f7"];

export default function AttendanceDashboard() {
  const { session } = useAuth();
  const token = session?.token;
  const isSuperAdmin = session?.is_super_admin === true;
  const isAdmin = session?.is_admin === true;

  // State
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split("T")[0]);
  const [selectedMonth, setSelectedMonth] = useState(new Date().toISOString().slice(0, 7));
  const [selectedCenter, setSelectedCenter] = useState(null);
  
  // Data
  const [summary, setSummary] = useState(null);
  const [centerBreakdown, setCenterBreakdown] = useState([]);
  const [centerDetail, setCenterDetail] = useState(null);
  const [monthlyTrend, setMonthlyTrend] = useState(null);
  const [centerComparison, setCenterComparison] = useState([]);
  const [statusOptions, setStatusOptions] = useState([]);
  const [centers, setCenters] = useState([]);

  // Edit dialog (Super Admin only)
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState(null);
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

  // Fetch data when tab/date changes
  useEffect(() => {
    if (token && hasAccess) {
      if (activeTab === "overview") {
        fetchSummary();
        fetchCenterBreakdown();
      } else if (activeTab === "trends") {
        fetchMonthlyTrend();
        fetchCenterComparison();
      }
    }
  }, [token, activeTab, selectedDate, selectedMonth, hasAccess]);

  // Fetch when center selected
  useEffect(() => {
    if (selectedCenter && token) {
      fetchCenterDetail();
    }
  }, [selectedCenter, selectedDate, token]);

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
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/attendance-dashboard/summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, date: selectedDate })
      });
      if (res.ok) {
        const data = await res.json();
        setSummary(data);
      }
    } catch (err) {
      toast.error("Failed to fetch summary");
    } finally {
      setLoading(false);
    }
  }, [token, selectedDate]);

  const fetchCenterBreakdown = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API}/api/attendance-dashboard/center-breakdown`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, date: selectedDate })
      });
      if (res.ok) {
        const data = await res.json();
        setCenterBreakdown(data.centers || []);
      }
    } catch (err) {
      console.error("Error fetching breakdown:", err);
    }
  }, [token, selectedDate]);

  const fetchCenterDetail = useCallback(async () => {
    if (!token || !selectedCenter) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/attendance-dashboard/center-detail`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, center: selectedCenter, date: selectedDate })
      });
      if (res.ok) {
        const data = await res.json();
        setCenterDetail(data);
      }
    } catch (err) {
      toast.error("Failed to fetch center details");
    } finally {
      setLoading(false);
    }
  }, [token, selectedCenter, selectedDate]);

  const fetchMonthlyTrend = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API}/api/attendance-dashboard/monthly-trend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, month: selectedMonth })
      });
      if (res.ok) {
        const data = await res.json();
        setMonthlyTrend(data);
      }
    } catch (err) {
      console.error("Error fetching trend:", err);
    }
  }, [token, selectedMonth]);

  const fetchCenterComparison = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API}/api/attendance-dashboard/center-comparison`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, month: selectedMonth })
      });
      if (res.ok) {
        const data = await res.json();
        setCenterComparison(data.comparison || []);
      }
    } catch (err) {
      console.error("Error fetching comparison:", err);
    }
  }, [token, selectedMonth]);

  const handleExportDaily = async () => {
    try {
      const res = await fetch(`${API}/api/attendance-dashboard/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          token, 
          date: selectedDate,
          center: selectedCenter || null
        })
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `Attendance_${selectedCenter || "ALL"}_${selectedDate}.xlsx`;
        a.click();
        toast.success("Report downloaded!");
      }
    } catch (err) {
      toast.error("Export failed");
    }
  };

  const handleExportMonthly = async () => {
    try {
      const res = await fetch(`${API}/api/attendance-dashboard/export-monthly`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          token, 
          month: selectedMonth,
          center: selectedCenter || null
        })
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `Monthly_Attendance_${selectedCenter || "ALL"}_${selectedMonth}.xlsx`;
        a.click();
        toast.success("Monthly report downloaded!");
      }
    } catch (err) {
      toast.error("Export failed");
    }
  };

  const handleEditClick = (employee) => {
    if (!isSuperAdmin) {
      toast.error("Only Super Admin can edit attendance");
      return;
    }
    setEditingEmployee(employee);
    setEditStatus(employee.status || "");
    setEditNotes(employee.notes || "");
    setShowEditDialog(true);
  };

  const handleSaveEdit = async () => {
    if (!editingEmployee || !selectedCenter) return;
    try {
      const res = await fetch(`${API}/api/attendance-dashboard/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          center: selectedCenter,
          date: selectedDate,
          employee_name: editingEmployee.name,
          status: editStatus,
          notes: editNotes
        })
      });
      if (res.ok) {
        toast.success("Attendance updated!");
        setShowEditDialog(false);
        fetchCenterDetail();
        fetchCenterBreakdown();
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

  // Pie chart data for summary
  const pieData = summary ? [
    { name: "Present", value: summary.summary.present, color: "#22c55e" },
    { name: "Absent", value: summary.summary.absent, color: "#ef4444" },
    { name: "Half Day", value: summary.summary.half_day, color: "#eab308" },
    { name: "Week Off", value: summary.summary.week_off, color: "#3b82f6" },
    { name: "Leave", value: summary.summary.leave, color: "#f97316" },
    { name: "Not Marked", value: summary.summary.not_marked, color: "#6b7280" }
  ].filter(d => d.value > 0) : [];

  return (
    <div className="space-y-6" data-testid="attendance-dashboard-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <BarChart3 className="w-7 h-7" />
            Attendance Dashboard
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {isSuperAdmin ? "Full Access" : "Read-only View"} • All Centers Overview
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={isSuperAdmin ? "default" : "secondary"}>
            {isSuperAdmin ? "Super Admin" : "Admin (View Only)"}
          </Badge>
        </div>
      </div>

      {/* Date/Month Selector */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <Label className="text-xs">Select Date</Label>
              <Input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="w-40"
              />
            </div>
            <div>
              <Label className="text-xs">Select Month</Label>
              <Input
                type="month"
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className="w-40"
              />
            </div>
            <Button variant="outline" onClick={() => {
              fetchSummary();
              fetchCenterBreakdown();
            }}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <div className="flex gap-2 ml-auto">
              <Button variant="outline" onClick={handleExportDaily}>
                <Download className="w-4 h-4 mr-2" />
                Daily Report
              </Button>
              <Button variant="outline" onClick={handleExportMonthly}>
                <FileSpreadsheet className="w-4 h-4 mr-2" />
                Monthly Report
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-2 w-full max-w-xs">
          <TabsTrigger value="overview" data-testid="tab-overview">
            <Eye className="w-4 h-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="trends" data-testid="tab-trends">
            <TrendingUp className="w-4 h-4 mr-2" />
            Trends
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          {/* Summary Cards */}
          {summary && (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-muted-foreground flex items-center gap-1">
                    <Users className="w-4 h-4" />
                    Total
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{summary.summary.total_employees}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-green-400 flex items-center gap-1">
                    <UserCheck className="w-4 h-4" />
                    Present
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-400">{summary.summary.present}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-red-400 flex items-center gap-1">
                    <UserX className="w-4 h-4" />
                    Absent
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-red-400">{summary.summary.absent}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-yellow-400 flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    Half Day
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-yellow-400">{summary.summary.half_day}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-blue-400 flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    Week Off
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-blue-400">{summary.summary.week_off}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-orange-400 flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    Leave
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-orange-400">{summary.summary.leave}</div>
                </CardContent>
              </Card>
              <Card className="bg-primary/10">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-primary flex items-center gap-1">
                    <TrendingUp className="w-4 h-4" />
                    Attendance %
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-primary">
                    {summary.summary.attendance_percentage}%
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Summary Pie Chart */}
          {pieData.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Attendance Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <RechartsPieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        paddingAngle={2}
                        dataKey="value"
                        label={({ name, value }) => `${name}: ${value}`}
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </RechartsPieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Center-wise Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <Building2 className="w-4 h-4" />
                Center-wise Breakdown
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin" />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Alert</TableHead>
                        <TableHead>Center</TableHead>
                        <TableHead className="text-center">Staff</TableHead>
                        <TableHead className="text-center text-green-400">Present</TableHead>
                        <TableHead className="text-center text-red-400">Absent</TableHead>
                        <TableHead className="text-center text-yellow-400">HD</TableHead>
                        <TableHead className="text-center text-blue-400">WO</TableHead>
                        <TableHead className="text-center text-orange-400">Leave</TableHead>
                        <TableHead className="text-center">Attendance %</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {centerBreakdown.map((center, index) => (
                        <TableRow 
                          key={`${center.center_code}-${index}`}
                          className={center.alert === "red" ? "bg-red-500/5" : center.alert === "yellow" ? "bg-yellow-500/5" : ""}
                        >
                          <TableCell>
                            {center.alert === "red" ? (
                              <AlertTriangle className="w-5 h-5 text-red-500" />
                            ) : center.alert === "yellow" ? (
                              <AlertTriangle className="w-5 h-5 text-yellow-500" />
                            ) : (
                              <CheckCircle2 className="w-5 h-5 text-green-500" />
                            )}
                          </TableCell>
                          <TableCell className="font-medium">{center.center_name || center.center_code}</TableCell>
                          <TableCell className="text-center">{center.total_staff}</TableCell>
                          <TableCell className="text-center text-green-400">{center.present}</TableCell>
                          <TableCell className="text-center text-red-400">{center.absent}</TableCell>
                          <TableCell className="text-center text-yellow-400">{center.half_day}</TableCell>
                          <TableCell className="text-center text-blue-400">{center.week_off}</TableCell>
                          <TableCell className="text-center text-orange-400">{center.leave}</TableCell>
                          <TableCell className="text-center">
                            <Badge className={
                              center.attendance_percentage >= 85 ? "bg-green-500/20 text-green-400" :
                              center.attendance_percentage >= 70 ? "bg-yellow-500/20 text-yellow-400" :
                              "bg-red-500/20 text-red-400"
                            }>
                              {center.attendance_percentage}%
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedCenter(center.center_code)}
                            >
                              <Eye className="w-4 h-4 mr-1" />
                              View
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Center Detail View */}
          {selectedCenter && centerDetail && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Building2 className="w-4 h-4" />
                    {selectedCenter} - Employee Details
                    <Badge variant="outline" className="ml-2">
                      {centerDetail.summary.total} employees
                    </Badge>
                  </CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => setSelectedCenter(null)}>
                    <ChevronLeft className="w-4 h-4 mr-1" />
                    Back
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Employee</TableHead>
                        <TableHead>Designation</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Notes</TableHead>
                        {isSuperAdmin && <TableHead>Actions</TableHead>}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {centerDetail.employees.map((emp) => {
                        const statusConfig = STATUS_CONFIG[emp.status] || STATUS_CONFIG[""];
                        return (
                          <TableRow key={emp.name}>
                            <TableCell className="font-medium">{emp.name}</TableCell>
                            <TableCell>{emp.designation}</TableCell>
                            <TableCell>
                              <Badge className={statusConfig.color}>
                                {statusConfig.label}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
                              {emp.notes || "-"}
                            </TableCell>
                            {isSuperAdmin && (
                              <TableCell>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleEditClick(emp)}
                                >
                                  <Edit className="w-4 h-4" />
                                </Button>
                              </TableCell>
                            )}
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Trends Tab */}
        <TabsContent value="trends" className="space-y-6">
          {/* Monthly Attendance Trend Chart */}
          {monthlyTrend && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Daily Attendance Trend - {selectedMonth}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={monthlyTrend.trend}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="day" stroke="#9ca3af" />
                      <YAxis stroke="#9ca3af" />
                      <Tooltip 
                        contentStyle={{ backgroundColor: "#1f2937", border: "none", borderRadius: "8px" }}
                        labelStyle={{ color: "#fff" }}
                      />
                      <Legend />
                      <Line type="monotone" dataKey="present" stroke="#22c55e" name="Present" strokeWidth={2} />
                      <Line type="monotone" dataKey="absent" stroke="#ef4444" name="Absent" strokeWidth={2} />
                      <Line type="monotone" dataKey="attendance_percentage" stroke="#3b82f6" name="Attendance %" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Center Comparison Bar Chart */}
          {centerComparison.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Center-wise Attendance Comparison - {selectedMonth}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={centerComparison} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis type="number" domain={[0, 100]} stroke="#9ca3af" />
                      <YAxis dataKey="center_code" type="category" width={80} stroke="#9ca3af" />
                      <Tooltip 
                        contentStyle={{ backgroundColor: "#1f2937", border: "none", borderRadius: "8px" }}
                        formatter={(value) => [`${value}%`, "Attendance"]}
                      />
                      <Bar 
                        dataKey="attendance_percentage" 
                        fill="#22c55e"
                        radius={[0, 4, 4, 0]}
                      >
                        {centerComparison.map((entry, index) => (
                          <Cell 
                            key={`cell-${index}`} 
                            fill={entry.attendance_percentage >= 85 ? "#22c55e" : entry.attendance_percentage >= 70 ? "#eab308" : "#ef4444"} 
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Alerts Section */}
          <div className="grid md:grid-cols-2 gap-4">
            {/* Low Attendance Alerts */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2 text-red-400">
                  <AlertTriangle className="w-4 h-4" />
                  Low Attendance Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                {centerComparison.filter(c => c.attendance_percentage < 70).length === 0 ? (
                  <p className="text-sm text-muted-foreground">No centers with low attendance</p>
                ) : (
                  <div className="space-y-2">
                    {centerComparison.filter(c => c.attendance_percentage < 70).map((c, idx) => (
                      <div key={`low-${c.center_code}-${idx}`} className="flex justify-between items-center p-2 bg-red-500/10 rounded">
                        <span className="font-medium">{c.center_code}</span>
                        <Badge className="bg-red-500/20 text-red-400">{c.attendance_percentage}%</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* High Attendance Highlights */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2 text-green-400">
                  <CheckCircle2 className="w-4 h-4" />
                  High Attendance Highlights
                </CardTitle>
              </CardHeader>
              <CardContent>
                {centerComparison.filter(c => c.attendance_percentage >= 90).length === 0 ? (
                  <p className="text-sm text-muted-foreground">No centers with 90%+ attendance</p>
                ) : (
                  <div className="space-y-2">
                    {centerComparison.filter(c => c.attendance_percentage >= 90).map((c, idx) => (
                      <div key={`high-${c.center_code}-${idx}`} className="flex justify-between items-center p-2 bg-green-500/10 rounded">
                        <span className="font-medium">{c.center_code}</span>
                        <Badge className="bg-green-500/20 text-green-400">{c.attendance_percentage}%</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Edit Dialog (Super Admin Only) */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Attendance</DialogTitle>
          </DialogHeader>
          {editingEmployee && (
            <div className="space-y-4">
              <div>
                <Label>Employee</Label>
                <Input value={editingEmployee.name} disabled />
              </div>
              <div>
                <Label>Date</Label>
                <Input value={selectedDate} disabled />
              </div>
              <div>
                <Label>Status</Label>
                <Select value={editStatus || "NOT_MARKED"} onValueChange={(val) => setEditStatus(val === "NOT_MARKED" ? "" : val)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select status..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="NOT_MARKED">Not Marked</SelectItem>
                    {statusOptions.map(s => (
                      <SelectItem key={s.code} value={s.code}>{s.label}</SelectItem>
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
