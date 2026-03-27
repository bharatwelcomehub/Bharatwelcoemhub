import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Lock, Unlock, Calendar, Building2, AlertTriangle, CheckCircle } from "lucide-react";
import { api, fetchCentersFromDB, CENTERS } from "@/lib/api";

// Get current month in YYYY-MM format
const getCurrentMonth = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
};

// Get today's date in YYYY-MM-DD format
const getTodayStr = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
};

export default function FreezeControl({ session }) {
  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState("freeze"); // freeze or unfreeze
  const [scope, setScope] = useState("day"); // day or month
  const [selectedDate, setSelectedDate] = useState(getTodayStr());
  const [selectedMonth, setSelectedMonth] = useState(getCurrentMonth());
  const [selectedCenter, setSelectedCenter] = useState("all");
  const [freezeStatus, setFreezeStatus] = useState(null);
  const [centers, setCenters] = useState([{ code: "all", name: "All Centers" }]);
  
  // Fetch centers from database on mount
  useEffect(() => {
    const loadCenters = async () => {
      if (session?.token) {
        const dbCenters = await fetchCentersFromDB(session.token);
        // Add "All Centers" option (include all active centers)
        const centerList = [
          { code: "all", name: "All Centers" },
          ...dbCenters.filter(c => c.active !== false)
        ];
        setCenters(centerList);
      }
    };
    loadCenters();
  }, [session?.token]);
  
  // Fetch current freeze status
  const fetchFreezeStatus = async () => {
    if (!session?.token) return;
    
    try {
      const month = scope === "day" ? selectedDate.substring(0, 7) : selectedMonth;
      const res = await api.get(`/sales/admin/freeze-status?token=${session.token}&month=${month}&center=${selectedCenter}`);
      setFreezeStatus(res.data);
    } catch (err) {
      console.error("Failed to fetch freeze status:", err);
    }
  };
  
  useEffect(() => {
    fetchFreezeStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.token, selectedMonth, selectedCenter, scope, selectedDate]);
  
  // Execute freeze/unfreeze action
  const executeAction = async () => {
    if (!session?.token) {
      toast.error("Session expired. Please login again.");
      return;
    }
    
    const dateValue = scope === "day" ? selectedDate : selectedMonth;
    
    if (!dateValue) {
      toast.error("Please select a date or month");
      return;
    }
    
    // Confirmation
    const centerName = selectedCenter === "all" ? "ALL CENTERS" : selectedCenter;
    const scopeText = scope === "day" ? `date ${dateValue}` : `entire month ${dateValue}`;
    const actionText = action === "freeze" ? "FREEZE" : "UNFREEZE";
    
    if (!window.confirm(`Are you sure you want to ${actionText} sales & expenses for ${scopeText} for ${centerName}?\n\nThis will affect all data entry for the selected period.`)) {
      return;
    }
    
    setLoading(true);
    try {
      const res = await api.post("/sales/admin/freeze-control", {
        token: session.token,
        action: action,
        scope: scope,
        date: dateValue,
        center: selectedCenter
      });
      
      if (res.data.success) {
        toast.success(res.data.message);
        fetchFreezeStatus();
      }
    } catch (err) {
      console.error("Freeze control error:", err);
      toast.error(err.response?.data?.detail || `Failed to ${action} data`);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-3 rounded-lg bg-red-500/10">
          <Lock className="w-6 h-6 text-red-500" />
        </div>
        <div>
          <h2 className="text-xl font-semibold">Freeze Control</h2>
          <p className="text-sm text-muted-foreground">Super Admin: Manually freeze or unfreeze sales & expense data</p>
        </div>
      </div>
      
      {/* Warning Banner */}
      <div className="flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
        <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
        <div className="text-sm">
          <p className="font-medium text-amber-700">Important:</p>
          <ul className="list-disc list-inside text-amber-600 mt-1 space-y-1">
            <li><strong>Freeze:</strong> Prevents ALL users (including managers) from editing data for the selected period</li>
            <li><strong>Unfreeze:</strong> Allows editing for 30 days (or until manually frozen again)</li>
            <li>This affects both <strong>Sales Entry</strong> and <strong>Expense Entry</strong> forms</li>
          </ul>
        </div>
      </div>
      
      {/* Control Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Action Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Action</CardTitle>
            <CardDescription>Choose to freeze or unfreeze data</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Button
                variant={action === "freeze" ? "default" : "outline"}
                className={`h-20 flex flex-col gap-2 ${action === "freeze" ? "bg-red-500 hover:bg-red-600" : ""}`}
                onClick={() => setAction("freeze")}
                data-testid="action-freeze"
              >
                <Lock className="w-6 h-6" />
                <span>Freeze</span>
              </Button>
              <Button
                variant={action === "unfreeze" ? "default" : "outline"}
                className={`h-20 flex flex-col gap-2 ${action === "unfreeze" ? "bg-green-500 hover:bg-green-600" : ""}`}
                onClick={() => setAction("unfreeze")}
                data-testid="action-unfreeze"
              >
                <Unlock className="w-6 h-6" />
                <span>Unfreeze</span>
              </Button>
            </div>
          </CardContent>
        </Card>
        
        {/* Scope Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Scope</CardTitle>
            <CardDescription>Single day or entire month</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Button
                variant={scope === "day" ? "default" : "outline"}
                className="h-20 flex flex-col gap-2"
                onClick={() => setScope("day")}
                data-testid="scope-day"
              >
                <Calendar className="w-6 h-6" />
                <span>Single Day</span>
              </Button>
              <Button
                variant={scope === "month" ? "default" : "outline"}
                className="h-20 flex flex-col gap-2"
                onClick={() => setScope("month")}
                data-testid="scope-month"
              >
                <Calendar className="w-6 h-6" />
                <span>Full Month</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Date/Month and Center Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Selection</CardTitle>
          <CardDescription>Choose the {scope === "day" ? "date" : "month"} and center</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Date/Month Picker */}
            <div className="space-y-2">
              <Label>{scope === "day" ? "Select Date" : "Select Month"}</Label>
              {scope === "day" ? (
                <Input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="w-full"
                  data-testid="date-picker"
                />
              ) : (
                <Input
                  type="month"
                  value={selectedMonth}
                  onChange={(e) => setSelectedMonth(e.target.value)}
                  className="w-full"
                  data-testid="month-picker"
                />
              )}
            </div>
            
            {/* Center Picker */}
            <div className="space-y-2">
              <Label>Select Center</Label>
              <Select value={selectedCenter} onValueChange={setSelectedCenter}>
                <SelectTrigger data-testid="center-picker">
                  <SelectValue placeholder="Select center" />
                </SelectTrigger>
                <SelectContent>
                  {centers.map((c) => (
                    <SelectItem key={c.code} value={c.code}>
                      <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4" />
                        {c.code === "all" ? c.name : `${c.code} - ${c.name}`}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Current Status */}
      {freezeStatus && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Current Status</CardTitle>
            <CardDescription>
              Showing status for {freezeStatus.month} - {freezeStatus.center === "all" ? "All Centers" : freezeStatus.center}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Lock className="w-4 h-4 text-red-500" />
                  <span className="font-medium text-red-700 dark:text-red-400">Admin Frozen Dates</span>
                </div>
                <p className="text-2xl font-bold text-red-600">
                  {freezeStatus.admin_frozen_dates?.length || 0}
                </p>
                {freezeStatus.admin_frozen_dates?.length > 0 && (
                  <p className="text-xs text-red-500 mt-1">
                    {freezeStatus.admin_frozen_dates.slice(0, 5).join(", ")}
                    {freezeStatus.admin_frozen_dates.length > 5 && "..."}
                  </p>
                )}
              </div>
              
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Unlock className="w-4 h-4 text-green-500" />
                  <span className="font-medium text-green-700 dark:text-green-400">Unlocked Dates</span>
                </div>
                <p className="text-2xl font-bold text-green-600">
                  {freezeStatus.unlocked_dates?.length || 0}
                </p>
                {freezeStatus.unlocked_dates?.length > 0 && (
                  <p className="text-xs text-green-500 mt-1">
                    {freezeStatus.unlocked_dates.slice(0, 5).join(", ")}
                    {freezeStatus.unlocked_dates.length > 5 && "..."}
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Execute Button */}
      <Card className={action === "freeze" ? "border-red-500" : "border-green-500"}>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="text-center md:text-left">
              <p className="font-medium">
                {action === "freeze" ? "Freeze" : "Unfreeze"} {scope === "day" ? "Single Day" : "Full Month"}
              </p>
              <p className="text-sm text-muted-foreground">
                {scope === "day" ? selectedDate : selectedMonth} for {selectedCenter === "all" ? "All Centers" : selectedCenter}
              </p>
            </div>
            
            <Button
              size="lg"
              className={`min-w-[200px] ${action === "freeze" ? "bg-red-500 hover:bg-red-600" : "bg-green-500 hover:bg-green-600"}`}
              onClick={executeAction}
              disabled={loading}
              data-testid="execute-btn"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  Processing...
                </>
              ) : (
                <>
                  {action === "freeze" ? <Lock className="w-4 h-4 mr-2" /> : <Unlock className="w-4 h-4 mr-2" />}
                  {action === "freeze" ? "Freeze Data" : "Unfreeze Data"}
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
