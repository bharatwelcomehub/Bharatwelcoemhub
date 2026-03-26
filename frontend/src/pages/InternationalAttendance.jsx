import { useState, useEffect } from "react";
import { useAuth } from "@/App";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { 
  Loader2, 
  Download, 
  Save, 
  RefreshCw, 
  Calendar,
  CalendarDays,
  Users,
  Clock,
  DollarSign,
  Globe,
  FileSpreadsheet,
  AlertTriangle,
  Pencil
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

// Get current year/month
const getCurrentYear = () => new Date().getFullYear();
const getCurrentMonth = () => new Date().getMonth() + 1;

// Month names
const MONTHS = [
  { value: 1, label: "January" },
  { value: 2, label: "February" },
  { value: 3, label: "March" },
  { value: 4, label: "April" },
  { value: 5, label: "May" },
  { value: 6, label: "June" },
  { value: 7, label: "July" },
  { value: 8, label: "August" },
  { value: 9, label: "September" },
  { value: 10, label: "October" },
  { value: 11, label: "November" },
  { value: 12, label: "December" }
];

// Day names
const DAY_NAMES = {
  mon: "Mon",
  tue: "Tue",
  wed: "Wed",
  thu: "Thu",
  fri: "Fri",
  sat: "Sat",
  sun: "Sun"
};

export default function InternationalAttendance() {
  const { session } = useAuth();
  const isMGT = session?.center === "PB-MGT";
  const isSuperAdmin = session?.is_super_admin === true;
  const isAdmin = session?.is_admin === true;
  const isAdminOrSuper = isSuperAdmin || isAdmin;
  
  // Center selection
  const [centers, setCenters] = useState([]);
  const [selectedCenter, setSelectedCenter] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [accessDenied, setAccessDenied] = useState(false);
  const [accessError, setAccessError] = useState("");
  
  // Week selection
  const [year, setYear] = useState(getCurrentYear());
  const [month, setMonth] = useState(getCurrentMonth());
  const [week, setWeek] = useState(1);
  const [weeksInMonth, setWeeksInMonth] = useState(5);
  
  // Attendance data
  const [employees, setEmployees] = useState([]);
  const [weekDates, setWeekDates] = useState([]);
  const [editedHours, setEditedHours] = useState({});
  const [hasChanges, setHasChanges] = useState(false);
  const [summary, setSummary] = useState({ total_staff: 0, total_hours: 0, total_payroll: 0 });
  
  // Monthly report
  const [monthlyReport, setMonthlyReport] = useState(null);
  
  // Loading states
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);
  
  // Edit rate modal state
  const [editRateOpen, setEditRateOpen] = useState(false);
  const [editRateEmployee, setEditRateEmployee] = useState(null);
  const [editRateValue, setEditRateValue] = useState("");
  const [editRateSaving, setEditRateSaving] = useState(false);

  // Fetch international centers with RBAC
  useEffect(() => {
    const fetchCenters = async () => {
      try {
        const res = await fetch(`${API}/api/international-attendance/centers?token=${session?.token}`);
        if (res.status === 403) {
          setAccessDenied(true);
          const err = await res.json();
          setAccessError(err.detail || "Access denied");
          return;
        }
        const data = await res.json();
        if (data.success && data.centers) {
          setCenters(data.centers);
          setShowDropdown(data.show_dropdown !== false);
          // Auto-select first center (or Perth for admin)
          if (data.show_dropdown) {
            const perth = data.centers.find(c => c.code === "PB-PERTH");
            setSelectedCenter(perth?.code || data.centers[0]?.code || "");
          } else {
            // Center manager — auto-select their center
            setSelectedCenter(data.centers[0]?.code || "");
          }
        }
      } catch (err) {
        console.error("Failed to fetch centers:", err);
      }
    };
    
    if (session?.token) {
      fetchCenters();
    }
  }, [session?.token]);

  // Calculate weeks in month when month changes
  useEffect(() => {
    const lastDay = new Date(year, month, 0).getDate();
    const weeks = Math.ceil(lastDay / 7);
    setWeeksInMonth(weeks);
    if (week > weeks) setWeek(1);
  }, [year, month]);

  // Fetch week attendance data
  const fetchWeekData = async () => {
    if (!selectedCenter || !session?.token) return;
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/international-attendance/week-data`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: session.token,
          center: selectedCenter,
          year,
          month,
          week
        })
      });
      const data = await res.json();
      
      if (data.success) {
        setEmployees(data.employees || []);
        setWeekDates(data.week_dates || []);
        setSummary(data.summary || { total_staff: 0, total_hours: 0, total_payroll: 0 });
        setEditedHours({});
        setHasChanges(false);
      } else {
        toast.error(data.detail || "Failed to load attendance");
      }
    } catch (err) {
      toast.error("Failed to load attendance data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedCenter) {
      fetchWeekData();
    }
  }, [selectedCenter, year, month, week]);

  // Handle hours change
  const handleHoursChange = (employeeId, day, value) => {
    // Parse value, allow decimals
    let hours = parseFloat(value) || 0;
    
    // Clamp between 0 and 16
    if (hours < 0) hours = 0;
    
    setEditedHours(prev => ({
      ...prev,
      [employeeId]: {
        ...(prev[employeeId] || {}),
        [day]: hours
      }
    }));
    setHasChanges(true);
  };

  // Get current hours value (edited or original)
  const getHours = (employee, day) => {
    if (editedHours[employee.employee_id]?.[day] !== undefined) {
      return editedHours[employee.employee_id][day];
    }
    return employee.hours?.[day] || 0;
  };

  // Calculate employee totals with edits
  const calculateEmployeeTotals = (employee) => {
    const days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
    let totalHours = 0;
    
    for (const day of days) {
      const hours = getHours(employee, day);
      if (hours !== null && hours !== undefined) {
        totalHours += hours;
      }
    }
    
    const weeklySalary = totalHours * employee.hourly_rate;
    return { totalHours: Math.round(totalHours * 100) / 100, weeklySalary: Math.round(weeklySalary * 100) / 100 };
  };

  // Calculate overall summary with edits
  const calculateSummary = () => {
    let totalHours = 0;
    let totalPayroll = 0;
    
    for (const emp of employees) {
      const { totalHours: empHours, weeklySalary } = calculateEmployeeTotals(emp);
      totalHours += empHours;
      totalPayroll += weeklySalary;
    }
    
    return {
      total_staff: employees.length,
      total_hours: Math.round(totalHours * 100) / 100,
      total_payroll: Math.round(totalPayroll * 100) / 100
    };
  };

  // Save attendance
  const handleSave = async () => {
    if (!hasChanges) {
      toast.info("No changes to save");
      return;
    }
    
    setSaving(true);
    try {
      // Build entries from edited hours
      const entries = employees.map(emp => ({
        employee_id: emp.employee_id,
        hours: {
          ...emp.hours,
          ...(editedHours[emp.employee_id] || {})
        }
      }));
      
      const res = await fetch(`${API}/api/international-attendance/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: session.token,
          center: selectedCenter,
          year,
          month,
          week,
          entries
        })
      });
      const data = await res.json();
      
      if (data.success) {
        toast.success("Attendance saved successfully");
        if (data.warnings?.length > 0) {
          data.warnings.forEach(w => toast.warning(w));
        }
        setHasChanges(false);
        fetchWeekData(); // Refresh
      } else {
        toast.error(data.detail || "Failed to save");
      }
    } catch (err) {
      toast.error("Failed to save attendance");
    } finally {
      setSaving(false);
    }
  };

  // Fetch monthly report
  const fetchMonthlyReport = async () => {
    if (!selectedCenter || !session?.token) return;
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/international-attendance/monthly-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: session.token,
          center: selectedCenter,
          year,
          month
        })
      });
      const data = await res.json();
      
      if (data.success) {
        setMonthlyReport(data);
      } else {
        toast.error(data.detail || "Failed to load monthly report");
      }
    } catch (err) {
      toast.error("Failed to load monthly report");
    } finally {
      setLoading(false);
    }
  };

  // Export functions
  const exportWeeklyExcel = async () => {
    setExporting(true);
    try {
      const res = await fetch(`${API}/api/international-attendance/export/weekly-excel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: session.token,
          center: selectedCenter,
          year,
          month,
          week
        })
      });
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${selectedCenter}_Weekly_Payroll_Week${week}_${MONTHS[month-1].label}_${year}.csv`;
      a.click();
      toast.success("Weekly report exported");
    } catch (err) {
      toast.error("Failed to export");
    } finally {
      setExporting(false);
    }
  };

  const exportMonthlyExcel = async () => {
    setExporting(true);
    try {
      const res = await fetch(`${API}/api/international-attendance/export/monthly-excel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: session.token,
          center: selectedCenter,
          year,
          month
        })
      });
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${selectedCenter}_Monthly_Payroll_${MONTHS[month-1].label}_${year}.csv`;
      a.click();
      toast.success("Monthly report exported");
    } catch (err) {
      toast.error("Failed to export");
    } finally {
      setExporting(false);
    }
  };

  const exportAttendanceSheet = async () => {
    setExporting(true);
    try {
      const res = await fetch(`${API}/api/international-attendance/export/attendance-sheet`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: session.token,
          center: selectedCenter,
          year,
          month
        })
      });
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${selectedCenter}_Attendance_${MONTHS[month-1].label}_${year}.csv`;
      a.click();
      toast.success("Attendance sheet exported");
    } catch (err) {
      toast.error("Failed to export");
    } finally {
      setExporting(false);
    }
  };

  // Open edit rate modal
  const openEditRate = (emp) => {
    setEditRateEmployee(emp);
    setEditRateValue(emp.hourly_rate?.toString() || "0");
    setEditRateOpen(true);
  };

  // Save updated rate
  const handleSaveRate = async () => {
    if (!editRateEmployee) return;
    const rate = parseFloat(editRateValue);
    if (isNaN(rate) || rate < 0) {
      toast.error("Please enter a valid rate");
      return;
    }
    
    setEditRateSaving(true);
    try {
      const res = await fetch(`${API}/api/international-attendance/update-rate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: session.token,
          center: selectedCenter,
          employee_id: editRateEmployee.employee_id,
          new_rate: rate
        })
      });
      const data = await res.json();
      if (data.success) {
        toast.success(data.message || "Rate updated");
        setEditRateOpen(false);
        fetchWeekData(); // Refresh to show new rate
      } else {
        toast.error(data.detail || "Failed to update rate");
      }
    } catch (err) {
      toast.error("Failed to update rate");
    } finally {
      setEditRateSaving(false);
    }
  };

  // Format currency
  const formatCurrency = (amount) => {
    const center = centers.find(c => c.code === selectedCenter);
    const currency = center?.country === "Australia" ? "AUD" : "USD";
    return `$${(amount || 0).toFixed(2)}`;
  };

  // Current summary (with edits)
  const currentSummary = hasChanges ? calculateSummary() : summary;

  // Access denied for India center managers
  if (accessDenied) {
    return (
      <div className="min-h-[400px] flex items-center justify-center">
        <div className="text-center space-y-3">
          <AlertTriangle className="w-12 h-12 mx-auto text-amber-500" />
          <h2 className="text-xl font-bold">Access Restricted</h2>
          <p className="text-muted-foreground">{accessError || "International Attendance is only available for international centers."}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-4 md:p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Globe className="w-6 h-6 text-purple-600" />
              International Attendance
            </h1>
            <p className="text-muted-foreground text-sm mt-1">
              Hours-based attendance for international centers
            </p>
          </div>
          
          {/* Center Selector - only for Admin/Super Admin */}
          {showDropdown ? (
            <div className="flex items-center gap-3">
              <Label className="text-sm font-medium">Center:</Label>
              <Select value={selectedCenter} onValueChange={setSelectedCenter}>
                <SelectTrigger className="w-56" data-testid="center-select">
                  <SelectValue placeholder="Select center" />
                </SelectTrigger>
                <SelectContent>
                  {centers.map(c => (
                    <SelectItem key={c.code} value={c.code}>
                      {c.code} - {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-sm font-mono">{selectedCenter}</Badge>
              <span className="text-sm text-muted-foreground">{centers[0]?.name}</span>
            </div>
          )}
        </div>

        {/* Main Tabs */}
        <Tabs defaultValue="weekly" className="space-y-4">
          <TabsList>
            <TabsTrigger value="weekly" className="gap-2">
              <CalendarDays className="w-4 h-4" /> Weekly Attendance
            </TabsTrigger>
            <TabsTrigger value="monthly" className="gap-2" onClick={fetchMonthlyReport}>
              <Calendar className="w-4 h-4" /> Monthly Summary
            </TabsTrigger>
            <TabsTrigger value="export" className="gap-2">
              <Download className="w-4 h-4" /> Export
            </TabsTrigger>
          </TabsList>

          {/* Weekly Attendance Tab */}
          <TabsContent value="weekly" className="space-y-4">
            {/* Week Selector */}
            <Card>
              <CardContent className="pt-4">
                <div className="flex flex-wrap items-end gap-4">
                  <div>
                    <Label className="text-xs">Year</Label>
                    <Select value={year.toString()} onValueChange={(v) => setYear(parseInt(v))}>
                      <SelectTrigger className="w-24">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {[2024, 2025, 2026, 2027].map(y => (
                          <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs">Month</Label>
                    <Select value={month.toString()} onValueChange={(v) => setMonth(parseInt(v))}>
                      <SelectTrigger className="w-36">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {MONTHS.map(m => (
                          <SelectItem key={m.value} value={m.value.toString()}>{m.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs">Week</Label>
                    <Select value={week.toString()} onValueChange={(v) => setWeek(parseInt(v))}>
                      <SelectTrigger className="w-28">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Array.from({ length: weeksInMonth }, (_, i) => i + 1).map(w => (
                          <SelectItem key={w} value={w.toString()}>Week {w}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <Button variant="outline" size="sm" onClick={fetchWeekData} disabled={loading}>
                    <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    Refresh
                  </Button>
                  
                  {hasChanges && (
                    <Button onClick={handleSave} disabled={saving} className="bg-green-600 hover:bg-green-700 gap-2">
                      {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                      Save Attendance
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Week Dates Header */}
            {weekDates.length > 0 && (
              <div className="flex gap-2 text-xs text-muted-foreground">
                <span>Week dates:</span>
                {weekDates.map((d, i) => (
                  <span key={i} className={d ? "" : "text-gray-300"}>
                    {d ? new Date(d).toLocaleDateString('en-AU', { day: '2-digit', month: 'short' }) : "-"}
                    {i < 6 && " |"}
                  </span>
                ))}
              </div>
            )}

            {/* Attendance Table */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">
                  Weekly Attendance - Week {week}, {MONTHS[month-1].label} {year}
                </CardTitle>
                <CardDescription>
                  Enter hours worked per day. Maximum 16 hours per day.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
                  </div>
                ) : employees.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground">
                    <Users className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                    <p>No employees found for {selectedCenter?.replace(/-$/, '')}</p>
                    <p className="text-sm mt-1">Please ensure employees are added to this center</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-muted">
                        <tr>
                          <th className="text-left py-3 px-2 font-medium min-w-[150px]">Employee</th>
                          <th className="text-center py-3 px-2 font-medium w-16">Mon</th>
                          <th className="text-center py-3 px-2 font-medium w-16">Tue</th>
                          <th className="text-center py-3 px-2 font-medium w-16">Wed</th>
                          <th className="text-center py-3 px-2 font-medium w-16">Thu</th>
                          <th className="text-center py-3 px-2 font-medium w-16">Fri</th>
                          <th className="text-center py-3 px-2 font-medium w-16 bg-blue-50">Sat</th>
                          <th className="text-center py-3 px-2 font-medium w-16 bg-blue-50">Sun</th>
                          <th className="text-right py-3 px-2 font-medium w-20">Total Hrs</th>
                          <th className="text-right py-3 px-2 font-medium w-20">Rate</th>
                          <th className="text-right py-3 px-2 font-medium w-24">Salary</th>
                        </tr>
                      </thead>
                      <tbody>
                        {employees.map((emp, idx) => {
                          const { totalHours, weeklySalary } = calculateEmployeeTotals(emp);
                          const isEdited = !!editedHours[emp.employee_id];
                          
                          return (
                            <tr key={emp.employee_id} className={`border-t ${idx % 2 === 0 ? '' : 'bg-gray-50/50'} ${isEdited ? 'bg-amber-50' : ''}`}>
                              <td className="py-2 px-2">
                                <div className="font-medium">{emp.employee_name}</div>
                                <div className="text-xs text-muted-foreground">{emp.category}</div>
                              </td>
                              {["mon", "tue", "wed", "thu", "fri", "sat", "sun"].map((day, dayIdx) => {
                                const dateForDay = weekDates[dayIdx];
                                const isWeekend = dayIdx >= 5;
                                const hours = getHours(emp, day);
                                const isOutOfMonth = dateForDay === null;
                                
                                return (
                                  <td key={day} className={`py-2 px-1 ${isWeekend ? 'bg-blue-50/50' : ''}`}>
                                    {isOutOfMonth ? (
                                      <span className="text-gray-300 text-center block">-</span>
                                    ) : (
                                      <Input
                                        type="number"
                                        min="0"
                                        max="16"
                                        step="0.5"
                                        value={hours || ""}
                                        onChange={(e) => handleHoursChange(emp.employee_id, day, e.target.value)}
                                        className={`h-8 w-14 text-center text-sm ${hours > 16 ? 'border-red-500 bg-red-50' : ''}`}
                                        placeholder="0"
                                        data-testid={`hours-${emp.employee_id}-${day}`}
                                      />
                                    )}
                                  </td>
                                );
                              })}
                              <td className="py-2 px-2 text-right font-medium">
                                {totalHours > 0 ? totalHours : "-"}
                              </td>
                              <td className="py-2 px-2 text-right text-muted-foreground">
                                <span className="inline-flex items-center gap-1">
                                  {formatCurrency(emp.hourly_rate)}/hr
                                  <button
                                    onClick={() => openEditRate(emp)}
                                    className="text-blue-500 hover:text-blue-700 hover:bg-blue-50 rounded p-0.5 transition-colors"
                                    title="Edit hourly rate"
                                    data-testid={`edit-rate-${emp.employee_id}`}
                                  >
                                    <Pencil className="w-3 h-3" />
                                  </button>
                                </span>
                              </td>
                              <td className="py-2 px-2 text-right font-bold text-green-600">
                                {weeklySalary > 0 ? formatCurrency(weeklySalary) : "-"}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Weekly Summary */}
            {employees.length > 0 && (
              <Card className="bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200">
                <CardContent className="pt-4">
                  <div className="grid grid-cols-3 gap-6 text-center">
                    <div>
                      <div className="text-3xl font-bold text-purple-700">{currentSummary.total_staff}</div>
                      <div className="text-sm text-purple-600 flex items-center justify-center gap-1">
                        <Users className="w-4 h-4" /> Total Staff
                      </div>
                    </div>
                    <div>
                      <div className="text-3xl font-bold text-blue-700">{currentSummary.total_hours}</div>
                      <div className="text-sm text-blue-600 flex items-center justify-center gap-1">
                        <Clock className="w-4 h-4" /> Total Hours
                      </div>
                    </div>
                    <div>
                      <div className="text-3xl font-bold text-green-700">{formatCurrency(currentSummary.total_payroll)}</div>
                      <div className="text-sm text-green-600 flex items-center justify-center gap-1">
                        <DollarSign className="w-4 h-4" /> Total Payroll
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Monthly Summary Tab */}
          <TabsContent value="monthly" className="space-y-4">
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-end gap-4">
                  <div>
                    <Label className="text-xs">Year</Label>
                    <Select value={year.toString()} onValueChange={(v) => setYear(parseInt(v))}>
                      <SelectTrigger className="w-24">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {[2024, 2025, 2026, 2027].map(y => (
                          <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs">Month</Label>
                    <Select value={month.toString()} onValueChange={(v) => setMonth(parseInt(v))}>
                      <SelectTrigger className="w-36">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {MONTHS.map(m => (
                          <SelectItem key={m.value} value={m.value.toString()}>{m.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button onClick={fetchMonthlyReport} disabled={loading}>
                    <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    Load Report
                  </Button>
                </div>
              </CardContent>
            </Card>

            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
              </div>
            ) : monthlyReport ? (
              <>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg">
                      Monthly Payroll - {monthlyReport.month_name} {monthlyReport.year}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-muted">
                          <tr>
                            <th className="text-left py-3 px-2 font-medium">Employee</th>
                            <th className="text-left py-3 px-2 font-medium">Category</th>
                            {Array.from({ length: monthlyReport.weeks_in_month }, (_, i) => (
                              <th key={i} className="text-center py-3 px-2 font-medium">Week {i + 1}</th>
                            ))}
                            <th className="text-right py-3 px-2 font-medium">Total Hours</th>
                            <th className="text-right py-3 px-2 font-medium">Rate</th>
                            <th className="text-right py-3 px-2 font-medium">Total Salary</th>
                          </tr>
                        </thead>
                        <tbody>
                          {monthlyReport.employees.map((emp, idx) => (
                            <tr key={emp.employee_id} className={`border-t ${idx % 2 === 0 ? '' : 'bg-gray-50/50'}`}>
                              <td className="py-2 px-2 font-medium">{emp.employee_name}</td>
                              <td className="py-2 px-2 text-sm text-muted-foreground">{emp.category}</td>
                              {Array.from({ length: monthlyReport.weeks_in_month }, (_, i) => (
                                <td key={i} className="py-2 px-2 text-center">
                                  {emp.weeks[i + 1] || "-"}
                                </td>
                              ))}
                              <td className="py-2 px-2 text-right font-medium">{emp.total_hours}</td>
                              <td className="py-2 px-2 text-right text-muted-foreground">{formatCurrency(emp.hourly_rate)}/hr</td>
                              <td className="py-2 px-2 text-right font-bold text-green-600">{formatCurrency(emp.total_salary)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>

                {/* Monthly Summary */}
                <Card className="bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
                  <CardContent className="pt-4">
                    <div className="grid grid-cols-3 gap-6 text-center">
                      <div>
                        <div className="text-3xl font-bold text-green-700">{monthlyReport.summary.total_staff}</div>
                        <div className="text-sm text-green-600 flex items-center justify-center gap-1">
                          <Users className="w-4 h-4" /> Total Staff
                        </div>
                      </div>
                      <div>
                        <div className="text-3xl font-bold text-emerald-700">{monthlyReport.summary.total_hours}</div>
                        <div className="text-sm text-emerald-600 flex items-center justify-center gap-1">
                          <Clock className="w-4 h-4" /> Total Hours
                        </div>
                      </div>
                      <div>
                        <div className="text-3xl font-bold text-teal-700">{formatCurrency(monthlyReport.summary.total_payroll)}</div>
                        <div className="text-sm text-teal-600 flex items-center justify-center gap-1">
                          <DollarSign className="w-4 h-4" /> Monthly Payroll
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <FileSpreadsheet className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                <p>Click "Load Report" to view monthly summary</p>
              </div>
            )}
          </TabsContent>

          {/* Export Tab */}
          <TabsContent value="export" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Download className="w-5 h-5 text-blue-600" />
                  Export Reports
                </CardTitle>
                <CardDescription>
                  Download payroll and attendance reports for accounting
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Current Period Info */}
                <div className="p-4 bg-muted rounded-lg">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Center:</span>
                      <span className="ml-2 font-medium">{selectedCenter}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Year:</span>
                      <span className="ml-2 font-medium">{year}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Month:</span>
                      <span className="ml-2 font-medium">{MONTHS[month-1].label}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Week:</span>
                      <span className="ml-2 font-medium">Week {week}</span>
                    </div>
                  </div>
                </div>

                {/* Export Buttons */}
                <div className="grid gap-4 md:grid-cols-3">
                  <Card className="border-2 hover:border-blue-300 transition-colors">
                    <CardContent className="pt-6 text-center space-y-3">
                      <CalendarDays className="w-10 h-10 mx-auto text-blue-600" />
                      <h3 className="font-medium">Weekly Payroll Report</h3>
                      <p className="text-xs text-muted-foreground">
                        Week {week}, {MONTHS[month-1].label} {year}
                      </p>
                      <Button 
                        onClick={exportWeeklyExcel} 
                        disabled={exporting}
                        className="w-full gap-2"
                      >
                        {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                        Export CSV
                      </Button>
                    </CardContent>
                  </Card>

                  <Card className="border-2 hover:border-green-300 transition-colors">
                    <CardContent className="pt-6 text-center space-y-3">
                      <Calendar className="w-10 h-10 mx-auto text-green-600" />
                      <h3 className="font-medium">Monthly Payroll Report</h3>
                      <p className="text-xs text-muted-foreground">
                        {MONTHS[month-1].label} {year}
                      </p>
                      <Button 
                        onClick={exportMonthlyExcel} 
                        disabled={exporting}
                        variant="outline"
                        className="w-full gap-2"
                      >
                        {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                        Export CSV
                      </Button>
                    </CardContent>
                  </Card>

                  <Card className="border-2 hover:border-purple-300 transition-colors">
                    <CardContent className="pt-6 text-center space-y-3">
                      <FileSpreadsheet className="w-10 h-10 mx-auto text-purple-600" />
                      <h3 className="font-medium">Full Attendance Sheet</h3>
                      <p className="text-xs text-muted-foreground">
                        Day-by-day hours for {MONTHS[month-1].label}
                      </p>
                      <Button 
                        onClick={exportAttendanceSheet} 
                        disabled={exporting}
                        variant="outline"
                        className="w-full gap-2"
                      >
                        {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                        Export CSV
                      </Button>
                    </CardContent>
                  </Card>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Edit Rate Dialog */}
        <Dialog open={editRateOpen} onOpenChange={setEditRateOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Update Hourly Rate</DialogTitle>
            </DialogHeader>
            {editRateEmployee && (
              <div className="space-y-4 py-2">
                <div className="text-sm space-y-1">
                  <div><span className="text-muted-foreground">Employee:</span> <span className="font-medium">{editRateEmployee.employee_name}</span></div>
                  <div><span className="text-muted-foreground">Category:</span> <span>{editRateEmployee.category}</span></div>
                  <div><span className="text-muted-foreground">Current Rate:</span> <span className="font-medium">{formatCurrency(editRateEmployee.hourly_rate)}/hr</span></div>
                </div>
                <div>
                  <Label htmlFor="new-rate" className="text-sm font-medium">New Hourly Rate ($)</Label>
                  <Input
                    id="new-rate"
                    type="number"
                    min="0"
                    step="0.5"
                    value={editRateValue}
                    onChange={(e) => setEditRateValue(e.target.value)}
                    className="mt-1"
                    data-testid="edit-rate-input"
                    autoFocus
                  />
                </div>
              </div>
            )}
            <DialogFooter className="gap-2">
              <Button variant="outline" onClick={() => setEditRateOpen(false)} data-testid="edit-rate-cancel">Cancel</Button>
              <Button onClick={handleSaveRate} disabled={editRateSaving} data-testid="edit-rate-save" className="gap-2">
                {editRateSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save Rate
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
