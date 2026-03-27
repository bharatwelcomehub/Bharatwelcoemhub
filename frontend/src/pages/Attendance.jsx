import { useState, useEffect } from "react";
import { useAuth } from "@/App";
import { api, STATUS_OPTIONS, ADVANCE_MODES, getTodayISO, getCurrentMonth, isAdminUser } from "@/lib/api";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { 
  Loader2, 
  Download, 
  Save, 
  RefreshCw, 
  Calendar,
  CalendarDays,
  Wallet,
  Lock,
  Users,
  ArrowRightLeft
} from "lucide-react";

export default function Attendance() {
  const { session } = useAuth();
  const isMGT = isAdminUser(session);
  
  // Daily state
  const [date, setDate] = useState(getTodayISO());
  const [dailyRows, setDailyRows] = useState([]);
  const [dailyLoading, setDailyLoading] = useState(false);
  
  // Monthly state
  const [month, setMonth] = useState(getCurrentMonth());
  const [monthlyGrid, setMonthlyGrid] = useState([]);
  const [daysInMonth, setDaysInMonth] = useState(30);
  const [monthlyLoading, setMonthlyLoading] = useState(false);
  const [payrollLocked, setPayrollLocked] = useState(false);
  
  // Advances state
  const [advances, setAdvances] = useState([]);
  const [advancesLoading, setAdvancesLoading] = useState(false);

  // Check payroll status
  const checkPayrollStatus = async () => {
    try {
      const res = await api.post("/payroll_status", {
        token: session.token,
        center: session.center,
        month: month
      });
      setPayrollLocked(res.data.locked);
    } catch (e) {
      console.error("Payroll status error:", e);
    }
  };

  useEffect(() => {
    checkPayrollStatus();
  }, [month]);

  // Load employees for daily attendance
  const loadEmployees = async () => {
    setDailyLoading(true);
    try {
      const res = await api.post("/employees", {
        token: session.token,
        center: session.center
      });
      const employees = res.data.employees || [];
      setDailyRows(employees.map(e => ({
        name: e.name,
        designation: e.designation || "",
        status: "P",
        notes: "",
        advanceAmount: 0,
        advanceMode: "CASH",
        transfer_tag: e.transfer_tag || "HOME",
        transfer_from: e.transfer_from || "",
        transfer_to: e.transfer_to || ""
      })));
      toast.success(`Loaded ${employees.length} employees`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to load employees");
    } finally {
      setDailyLoading(false);
    }
  };

  // Load saved attendance for date
  const loadSavedAttendance = async () => {
    setDailyLoading(true);
    try {
      const [attRes, advRes] = await Promise.all([
        api.post("/attendance_by_date", {
          token: session.token,
          center: session.center,
          date: date
        }),
        api.post("/advances_by_date", {
          token: session.token,
          center: session.center,
          date: date
        })
      ]);
      
      const attRows = attRes.data.rows || [];
      const advMap = {};
      (advRes.data.rows || []).forEach(a => {
        advMap[a.employeeName] = { amount: a.advanceAmount || 0, mode: a.mode || "CASH" };
      });
      
      if (attRows.length === 0) {
        toast.info("No saved attendance. Use Load Employees.");
        return;
      }
      
      setDailyRows(attRows.map(r => ({
        name: r.employeeName,
        designation: r.designation || "",
        status: r.status || "P",
        notes: r.notes || "",
        advanceAmount: advMap[r.employeeName]?.amount || 0,
        advanceMode: advMap[r.employeeName]?.mode || "CASH",
        transfer_tag: r.transfer_tag || "HOME",
        transfer_from: r.transfer_info?.from_center || "",
        transfer_to: r.transfer_info?.to_center || ""
      })));
      
      toast.success(`Loaded ${attRows.length} records`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to load attendance");
    } finally {
      setDailyLoading(false);
    }
  };

  // Save daily attendance
  const saveDailyAttendance = async () => {
    if (payrollLocked) {
      toast.error("Payroll is locked for this month");
      return;
    }
    if (dailyRows.length === 0) {
      toast.error("Load employees first");
      return;
    }
    
    setDailyLoading(true);
    try {
      // Save attendance
      const attRes = await api.post("/bulk_attendance", {
        token: session.token,
        center: session.center,
        date: date,
        rows: dailyRows.map(r => ({
          employeeName: r.name,
          designation: r.designation,
          status: r.status,
          notes: r.notes
        }))
      });
      
      // Save advances
      const advRows = dailyRows.filter(r => r.advanceAmount > 0);
      let advInserted = 0, advUpdated = 0;
      
      if (advRows.length > 0) {
        const advRes = await api.post("/bulk_advances", {
          token: session.token,
          center: session.center,
          date: date,
          rows: advRows.map(r => ({
            employeeName: r.name,
            advanceAmount: r.advanceAmount,
            mode: r.advanceMode,
            notes: ""
          }))
        });
        advInserted = advRes.data.inserted;
        advUpdated = advRes.data.updated;
      }
      
      toast.success(`Saved! Attendance: ${attRes.data.inserted} new, ${attRes.data.updated} updated. Advances: ${advInserted} new, ${advUpdated} updated.`);
      loadAdvances();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to save");
    } finally {
      setDailyLoading(false);
    }
  };

  // Update daily row
  const updateDailyRow = (index, field, value) => {
    setDailyRows(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  // Load monthly grid
  const loadMonthlyGrid = async () => {
    setMonthlyLoading(true);
    try {
      const res = await api.post("/attendance_month", {
        token: session.token,
        center: session.center,
        month: month
      });
      setMonthlyGrid(res.data.grid || []);
      setDaysInMonth(res.data.daysInMonth || 30);
      toast.success(`Loaded ${res.data.grid?.length || 0} employees`);
      checkPayrollStatus();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to load month");
    } finally {
      setMonthlyLoading(false);
    }
  };

  // Update monthly cell
  const updateMonthlyCell = (empIndex, dayIndex, status) => {
    setMonthlyGrid(prev => {
      const updated = [...prev];
      updated[empIndex] = {
        ...updated[empIndex],
        days: updated[empIndex].days.map((d, i) => 
          i === dayIndex ? { ...d, status } : d
        )
      };
      return updated;
    });
  };

  // Save monthly grid
  const saveMonthlyGrid = async () => {
    if (payrollLocked) {
      toast.error("Payroll is locked for this month");
      return;
    }
    
    setMonthlyLoading(true);
    try {
      const cells = [];
      monthlyGrid.forEach(emp => {
        emp.days.forEach(d => {
          cells.push({
            employeeName: emp.employeeName,
            day: d.day,
            status: d.status || "",
            notes: ""
          });
        });
      });
      
      const res = await api.post("/bulk_attendance_month", {
        token: session.token,
        center: session.center,
        month: month,
        cells
      });
      
      toast.success(`Saved! ${res.data.inserted} new, ${res.data.updated} updated`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to save");
    } finally {
      setMonthlyLoading(false);
    }
  };

  // Lock payroll (MGT only)
  const lockPayroll = async () => {
    if (!window.confirm(`Lock payroll for ALL centers for ${month}? This will stop edits.`)) return;
    
    try {
      await api.post("/lock_payroll", {
        token: session.token,
        center: session.center,
        month: month
      });
      toast.success("Payroll locked!");
      checkPayrollStatus();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to lock payroll");
    }
  };

  // Load advances for month
  const loadAdvances = async () => {
    setAdvancesLoading(true);
    try {
      const advMonth = date.slice(0, 7);
      const res = await api.post("/advances_by_month", {
        token: session.token,
        center: session.center,
        month: advMonth
      });
      setAdvances(res.data.rows || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to load advances");
    } finally {
      setAdvancesLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-primary">Attendance Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Daily + Monthly Attendance Management for {session?.center}
        </p>
      </div>

      {/* Payroll status banner */}
      {payrollLocked && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 flex items-center gap-3">
          <Lock className="w-5 h-5 text-destructive" />
          <div>
            <p className="font-bold text-destructive">Payroll Locked</p>
            <p className="text-sm text-destructive/80">
              Attendance for {month} is locked. View only mode.
            </p>
          </div>
        </div>
      )}

      <Tabs defaultValue="daily" className="space-y-6">
        <TabsList className="grid w-full max-w-md grid-cols-3">
          <TabsTrigger value="daily" className="gap-2">
            <Calendar className="w-4 h-4" />
            Daily
          </TabsTrigger>
          <TabsTrigger value="monthly" className="gap-2">
            <CalendarDays className="w-4 h-4" />
            Monthly
          </TabsTrigger>
          <TabsTrigger value="advances" className="gap-2">
            <Wallet className="w-4 h-4" />
            Advances
          </TabsTrigger>
        </TabsList>

        {/* Daily Tab */}
        <TabsContent value="daily" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Daily Attendance</CardTitle>
              <CardDescription>
                Mark attendance with status and advances for each employee
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Date and actions */}
              <div className="flex flex-wrap gap-4 items-end">
                <div className="space-y-2">
                  <Label>Date</Label>
                  <Input
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    className="w-44"
                    data-testid="attendance-date"
                  />
                </div>
                <Button
                  variant="outline"
                  onClick={loadEmployees}
                  disabled={dailyLoading}
                  data-testid="load-employees-btn"
                >
                  {dailyLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  <Users className="w-4 h-4 mr-2" />
                  Load Employees
                </Button>
                <Button
                  variant="outline"
                  onClick={loadSavedAttendance}
                  disabled={dailyLoading}
                  data-testid="load-saved-btn"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Load Saved
                </Button>
                <Button
                  onClick={saveDailyAttendance}
                  disabled={dailyLoading || payrollLocked}
                  data-testid="save-attendance-btn"
                >
                  {dailyLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  <Save className="w-4 h-4 mr-2" />
                  Save All
                </Button>
              </div>

              {/* Attendance table */}
              {dailyRows.length > 0 ? (
                <div className="border rounded-lg overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full attendance-table">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left p-3">Employee</th>
                          <th className="text-left p-3">Status</th>
                          <th className="text-left p-3">Advance</th>
                          <th className="text-left p-3">Notes</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dailyRows.map((row, idx) => {
                          const isTransferredOut = row.transfer_tag === "TRANSFERRED_OUT";
                          const isTransferredIn = row.transfer_tag === "TRANSFERRED_IN";
                          return (
                          <tr key={idx} className={cn("border-b hover:bg-muted/50", isTransferredOut && "opacity-50 bg-red-50/30")}>
                            <td className="p-3">
                              <div className="flex items-center gap-2">
                                <div>
                                  <p className="font-semibold">{row.name}</p>
                                  <p className="text-xs text-muted-foreground">{row.designation}</p>
                                </div>
                                {isTransferredIn && (
                                  <Badge variant="outline" className="text-[10px] border-blue-400 text-blue-600 bg-blue-50" data-testid={`transfer-in-badge-${idx}`}>
                                    <ArrowRightLeft className="w-3 h-3 mr-1" /> In from {row.transfer_from || "?"}
                                  </Badge>
                                )}
                                {isTransferredOut && (
                                  <Badge variant="outline" className="text-[10px] border-orange-400 text-orange-600 bg-orange-50" data-testid={`transfer-out-badge-${idx}`}>
                                    <ArrowRightLeft className="w-3 h-3 mr-1" /> Out to {row.transfer_to || "?"}
                                  </Badge>
                                )}
                              </div>
                            </td>
                            <td className="p-3">
                              <div className="flex gap-1 flex-wrap">
                                {STATUS_OPTIONS.map(s => (
                                  <button
                                    key={s.value}
                                    onClick={() => !isTransferredOut && updateDailyRow(idx, "status", s.value)}
                                    disabled={isTransferredOut}
                                    className={cn(
                                      "px-3 py-1.5 rounded-md text-xs font-bold border transition-all",
                                      row.status === s.value 
                                        ? s.color 
                                        : "bg-white border-border hover:border-primary/30",
                                      isTransferredOut && "cursor-not-allowed opacity-50"
                                    )}
                                  >
                                    {s.value}
                                  </button>
                                ))}
                              </div>
                            </td>
                            <td className="p-3">
                              <div className="flex items-center gap-2">
                                <Input
                                  type="number"
                                  min="0"
                                  value={row.advanceAmount || ""}
                                  onChange={(e) => updateDailyRow(idx, "advanceAmount", parseFloat(e.target.value) || 0)}
                                  placeholder="0"
                                  className="w-24 h-8"
                                />
                                <Select
                                  value={row.advanceMode}
                                  onValueChange={(v) => updateDailyRow(idx, "advanceMode", v)}
                                >
                                  <SelectTrigger className="w-24 h-8">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {ADVANCE_MODES.map(m => (
                                      <SelectItem key={m} value={m}>{m}</SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </div>
                            </td>
                            <td className="p-3">
                              <Input
                                value={row.notes}
                                onChange={(e) => updateDailyRow(idx, "notes", e.target.value)}
                                placeholder="Notes..."
                                className="h-8"
                                disabled={isTransferredOut}
                              />
                            </td>
                          </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No employees loaded</p>
                  <p className="text-sm">Click "Load Employees" to start</p>
                </div>
              )}

              {/* Status legend */}
              <div className="flex flex-wrap gap-4 pt-4 border-t">
                {STATUS_OPTIONS.map(s => (
                  <div key={s.value} className="flex items-center gap-2">
                    <Badge variant="outline" className={s.color}>{s.value}</Badge>
                    <span className="text-sm text-muted-foreground">{s.label}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Monthly Tab */}
        <TabsContent value="monthly" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Monthly Attendance Grid</CardTitle>
              <CardDescription>
                View and edit attendance for the entire month
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Month picker and actions */}
              <div className="flex flex-wrap gap-4 items-end">
                <div className="space-y-2">
                  <Label>Month</Label>
                  <Input
                    type="month"
                    value={month}
                    onChange={(e) => setMonth(e.target.value)}
                    className="w-44"
                    data-testid="month-picker"
                  />
                </div>
                <Button
                  variant="outline"
                  onClick={loadMonthlyGrid}
                  disabled={monthlyLoading}
                  data-testid="load-month-btn"
                >
                  {monthlyLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  <Download className="w-4 h-4 mr-2" />
                  Load Month
                </Button>
                <Button
                  onClick={saveMonthlyGrid}
                  disabled={monthlyLoading || payrollLocked}
                  data-testid="save-month-btn"
                >
                  <Save className="w-4 h-4 mr-2" />
                  Save Month
                </Button>
                {isMGT && (
                  <Button
                    variant="destructive"
                    onClick={lockPayroll}
                    disabled={payrollLocked}
                    data-testid="lock-payroll-btn"
                  >
                    <Lock className="w-4 h-4 mr-2" />
                    Lock Payroll
                  </Button>
                )}
              </div>

              {/* Monthly grid */}
              {monthlyGrid.length > 0 ? (
                <div className="border rounded-lg overflow-hidden">
                  <div className="overflow-x-auto max-h-[600px]">
                    <table className="w-max min-w-full">
                      <thead className="sticky top-0 z-10 bg-muted">
                        <tr>
                          <th className="text-left p-2 font-bold text-xs sticky left-0 bg-muted z-20 min-w-[150px]">
                            Employee
                          </th>
                          {Array.from({ length: daysInMonth }, (_, i) => (
                            <th key={i} className="p-2 text-center text-xs font-bold min-w-[50px]">
                              {i + 1}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {monthlyGrid.map((emp, empIdx) => {
                          const isOut = emp.transfer_tag === "TRANSFERRED_OUT";
                          const isIn = emp.transfer_tag === "TRANSFERRED_IN";
                          return (
                          <tr key={empIdx} className={cn("border-t hover:bg-muted/30", isOut && "opacity-50 bg-red-50/20")}>
                            <td className="p-2 sticky left-0 bg-card z-10 border-r">
                              <div className="flex items-center gap-1">
                                <div>
                                  <p className="font-semibold text-sm">{emp.employeeName}</p>
                                  <p className="text-xs text-muted-foreground">{emp.designation}</p>
                                </div>
                                {isIn && (
                                  <Badge variant="outline" className="text-[9px] px-1 border-blue-400 text-blue-600 bg-blue-50 whitespace-nowrap">IN</Badge>
                                )}
                                {isOut && (
                                  <Badge variant="outline" className="text-[9px] px-1 border-orange-400 text-orange-600 bg-orange-50 whitespace-nowrap">OUT</Badge>
                                )}
                              </div>
                            </td>
                            {emp.days.map((day, dayIdx) => (
                              <td key={dayIdx} className="p-1">
                                <select
                                  value={day.status || ""}
                                  onChange={(e) => updateMonthlyCell(empIdx, dayIdx, e.target.value)}
                                  disabled={payrollLocked || isOut}
                                  className={cn(
                                    "w-full h-8 text-xs font-bold text-center border rounded cursor-pointer",
                                    day.status === "P" && "bg-emerald-100 border-emerald-300",
                                    day.status === "A" && "bg-red-100 border-red-300",
                                    day.status === "HD" && "bg-amber-100 border-amber-300",
                                    day.status === "WO" && "bg-slate-100 border-slate-300",
                                    day.status === "L" && "bg-blue-100 border-blue-300",
                                    !day.status && "bg-white border-border",
                                    isOut && "cursor-not-allowed opacity-50"
                                  )}
                                >
                                  <option value="">-</option>
                                  <option value="P">P</option>
                                  <option value="A">A</option>
                                  <option value="HD">HD</option>
                                  <option value="WO">WO</option>
                                  <option value="L">L</option>
                                </select>
                              </td>
                            ))}
                          </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <CalendarDays className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No monthly data loaded</p>
                  <p className="text-sm">Select a month and click "Load Month"</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Advances Tab */}
        <TabsContent value="advances" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Advances This Month</CardTitle>
              <CardDescription>
                View all advances given to employees (based on daily date: {date.slice(0, 7)})
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <Button
                variant="outline"
                onClick={loadAdvances}
                disabled={advancesLoading}
              >
                {advancesLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                <RefreshCw className="w-4 h-4 mr-2" />
                Load Advances
              </Button>

              {advances.length > 0 ? (
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-muted">
                      <tr>
                        <th className="text-left p-3 text-xs font-bold">Date</th>
                        <th className="text-left p-3 text-xs font-bold">Employee</th>
                        <th className="text-left p-3 text-xs font-bold">Amount</th>
                        <th className="text-left p-3 text-xs font-bold">Mode</th>
                      </tr>
                    </thead>
                    <tbody>
                      {advances.map((adv, idx) => (
                        <tr key={idx} className="border-t hover:bg-muted/30">
                          <td className="p-3 text-sm">{adv.date}</td>
                          <td className="p-3 font-semibold">{adv.employeeName}</td>
                          <td className="p-3">
                            <Badge variant="secondary">₹{adv.advanceAmount}</Badge>
                          </td>
                          <td className="p-3 text-sm text-muted-foreground">{adv.mode}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <Wallet className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No advances for this month</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
