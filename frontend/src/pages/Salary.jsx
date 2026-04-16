import { useState, useEffect } from "react";
import { useAuth } from "@/App";
import { api, fetchCentersFromDB, isAdminUser, getCurrentMonth } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  Loader2, 
  Download, 
  FileSpreadsheet,
  FileText,
  Building2,
  Lock,
  Eye,
  Users,
  IndianRupee,
  Calculator,
  Globe
} from "lucide-react";

export default function Salary({ isPayslips = false }) {
  const { session } = useAuth();
  const [month, setMonth] = useState(getCurrentMonth());
  const [targetCenter, setTargetCenter] = useState("");
  const [loading, setLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [salaryData, setSalaryData] = useState(null);
  
  // Payslips specific
  const [period, setPeriod] = useState("1");
  const [fmt, setFmt] = useState("pdf");
  const [employeeName, setEmployeeName] = useState("");
  const [payslipMode, setPayslipMode] = useState("bulk");
  const [signatory, setSignatory] = useState("sandeep");
  const [employeeList, setEmployeeList] = useState([]);
  const [employeeListLoading, setEmployeeListLoading] = useState(false);
  const [centerCountry, setCenterCountry] = useState("India");

  const [centersList, setCentersList] = useState([]);

  // Fetch centers from DB on mount
  useEffect(() => {
    if (session?.token) {
      fetchCentersFromDB(session.token).then(setCentersList);
    }
  }, [session?.token]);

  // Fetch employee list when center changes (for payslip employee dropdown)
  useEffect(() => {
    if (isPayslips && targetCenter && targetCenter !== "ALL" && session?.token) {
      setEmployeeListLoading(true);
      setEmployeeName("");
      api.post("/payslip_employees", { token: session.token, center: targetCenter })
        .then(res => {
          setEmployeeList(res.data.employees || []);
          setCenterCountry(res.data.country || "India");
        })
        .catch(() => {
          setEmployeeList([]);
          setCenterCountry("India");
        })
        .finally(() => setEmployeeListLoading(false));
    } else {
      setEmployeeList([]);
      if (!targetCenter) setCenterCountry("India");
    }
  }, [isPayslips, targetCenter, session?.token]);

  // All centers for selection + "ALL" option
  const centerOptions = [
    { code: "ALL", name: "All Centers (Combined)" },
    ...centersList
  ];

  // Preview salary on screen
  const previewSalary = async () => {
    if (!targetCenter) {
      toast.error("Please select a center first");
      return;
    }
    
    setPreviewLoading(true);
    setSalaryData(null);
    try {
      // Single backend call handles both ALL and individual centers
      const res = await api.post("/salary_preview", {
        token: session.token,
        month: month,
        targetCenter: targetCenter
      });
      
      setSalaryData(res.data);
      toast.success(`Loaded salary data for ${res.data.employeeCount} employees`);
    } catch (e) {
      const errorMsg = await parseErrorFromBlob(e);
      toast.error(errorMsg || "Failed to load salary preview");
    } finally {
      setPreviewLoading(false);
    }
  };

  // Helper to parse error from blob response
  const parseErrorFromBlob = async (error) => {
    if (error.response?.data instanceof Blob) {
      try {
        const text = await error.response.data.text();
        const json = JSON.parse(text);
        return json.detail || "An error occurred";
      } catch {
        return "An error occurred";
      }
    }
    return error.response?.data?.detail || error.message || "An error occurred";
  };

  // Generate and download salary Excel
  const generateSalary = async () => {
    if (!targetCenter) {
      toast.error("Please select a center first");
      return;
    }
    
    setLoading(true);
    try {
      const res = await api.post("/generate_salary", {
        token: session.token,
        center: session.center,
        month: month,
        mode: targetCenter === "ALL" ? "all" : "single",
        targetCenter: targetCenter === "ALL" ? null : targetCenter
      }, {
        responseType: 'blob'
      });
      
      // Check if response is an error (JSON) instead of file
      if (res.data.type === 'application/json') {
        const text = await res.data.text();
        const json = JSON.parse(text);
        toast.error(json.detail || "Failed to generate salary");
        return;
      }
      
      // Create download link
      const blob = new Blob([res.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Salary_${targetCenter}_${month}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success("Salary Excel downloaded!");
    } catch (e) {
      const errorMsg = await parseErrorFromBlob(e);
      toast.error(errorMsg || "Failed to generate salary");
    } finally {
      setLoading(false);
    }
  };

  // Generate payslips
  const generatePayslips = async () => {
    if (!targetCenter || targetCenter === "ALL") {
      toast.error("Please select a specific center (not ALL)");
      return;
    }
    if (payslipMode === "single" && !employeeName.trim()) {
      toast.error("Enter employee name for single mode");
      return;
    }
    
    setLoading(true);
    try {
      const res = await api.post("/payslips_generate", {
        token: session.token,
        center: session.center,
        month: month,
        period: period,
        fmt: fmt,
        mode: payslipMode,
        targetCenter: targetCenter,
        employeeName: payslipMode === "single" ? employeeName.trim().toUpperCase() : null,
        signatory: signatory
      }, {
        responseType: 'blob'
      });
      
      // Check if response is an error (JSON) instead of file
      const contentType = res.headers['content-type'] || '';
      if (contentType.includes('application/json')) {
        const text = await res.data.text();
        const json = JSON.parse(text);
        toast.error(json.detail || "Failed to generate payslips");
        return;
      }
      
      // Determine file type
      const isZip = contentType.includes('zip');
      const blob = new Blob([res.data], { 
        type: isZip ? 'application/zip' : 'application/pdf' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = isZip 
        ? `Payslips_${targetCenter}_${month}.zip` 
        : `Payslip_${payslipMode === "single" ? employeeName.trim().toUpperCase() : targetCenter}_${month}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success("Payslip(s) downloaded!");
    } catch (e) {
      const errorMsg = await parseErrorFromBlob(e);
      toast.error(errorMsg || "Failed to generate payslips");
    } finally {
      setLoading(false);
    }
  };

  // Format currency - location-aware
  const formatCurrency = (amount) => {
    if (centerCountry !== "India") {
      return new Intl.NumberFormat('en-AU', {
        style: 'currency',
        currency: 'AUD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(amount);
    }
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const isIntlCenter = centerCountry !== "India";

  if (!isAdminUser(session)) {
    return (
      <div className="text-center py-20">
        <Lock className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
        <h2 className="text-2xl font-bold text-muted-foreground">Access Denied</h2>
        <p className="text-muted-foreground mt-2">Only Admin users can access salary & payslips</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-primary" data-testid="salary-page-title">
          {isPayslips ? "Payslip Generation" : "Salary Generation"}
        </h1>
        <p className="text-muted-foreground mt-1">
          {isPayslips 
            ? "Generate PDF payslips for employees" 
            : "View and generate salary for ICICI bank upload"}
        </p>
        {isPayslips && isIntlCenter && (
          <Badge className="mt-2 bg-blue-100 text-blue-800 hover:bg-blue-100" data-testid="intl-payroll-badge">
            <Globe className="w-3 h-3 mr-1" /> {centerCountry} - Hourly Payroll (WA Format)
          </Badge>
        )}
      </div>

      {/* Controls Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {isPayslips ? <FileText className="w-5 h-5" /> : <Calculator className="w-5 h-5" />}
            {isPayslips ? "Payslip Options" : "Salary Options"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Month */}
            <div className="space-y-2">
              <Label>Month</Label>
              <Input
                type="month"
                value={month}
                onChange={(e) => {
                  setMonth(e.target.value);
                  setSalaryData(null);
                }}
                data-testid="salary-month"
              />
            </div>

            {/* Center Selection */}
            <div className="space-y-2">
              <Label>Select Center</Label>
              <div className="flex items-center gap-2">
                <Select value={targetCenter} onValueChange={(v) => {
                  setTargetCenter(v);
                  setSalaryData(null);
                }}>
                  <SelectTrigger data-testid="center-select" className="flex-1">
                    <Building2 className="w-4 h-4 mr-2" />
                    <SelectValue placeholder="Select center" />
                  </SelectTrigger>
                  <SelectContent>
                    {centerOptions.map(c => (
                      <SelectItem key={c.code} value={c.code}>
                        {c.code === "ALL" ? "ALL CENTERS (Combined)" : `${c.code} - ${c.name}`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {targetCenter && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-10 w-10 shrink-0 text-muted-foreground hover:text-destructive"
                    onClick={() => { setTargetCenter(""); setSalaryData(null); }}
                    title="Clear selection"
                    data-testid="clear-center-btn"
                  >
                    <span className="text-lg font-bold">&times;</span>
                  </Button>
                )}
              </div>
            </div>

            {/* Payslips specific fields */}
            {isPayslips && (
              <>
                <div className="space-y-2">
                  <Label>Period</Label>
                  <Select value={period} onValueChange={setPeriod}>
                    <SelectTrigger data-testid="period-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1 Month</SelectItem>
                      <SelectItem value="3">3 Months</SelectItem>
                      <SelectItem value="6">6 Months</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Format</Label>
                  <Select value={fmt} onValueChange={setFmt}>
                    <SelectTrigger data-testid="format-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pdf">PDF</SelectItem>
                      <SelectItem value="docx">DOCX</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Signatory</Label>
                  <Select value={signatory} onValueChange={setSignatory}>
                    <SelectTrigger data-testid="signatory-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="sandeep">Sandeep Gadhwal</SelectItem>
                      <SelectItem value="jayanti">Jayanti Kathale (with Seal)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Mode</Label>
                  <Select value={payslipMode} onValueChange={(v) => {
                    setPayslipMode(v);
                    setEmployeeName("");
                  }}>
                    <SelectTrigger data-testid="mode-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="bulk">All Employees</SelectItem>
                      <SelectItem value="single">Single Employee</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {payslipMode === "single" && (
                  <div className="space-y-2">
                    <Label>Select Employee</Label>
                    {employeeListLoading ? (
                      <div className="flex items-center gap-2 h-10 px-3 border rounded-md text-sm text-muted-foreground">
                        <Loader2 className="w-4 h-4 animate-spin" /> Loading employees...
                      </div>
                    ) : employeeList.length > 0 ? (
                      <Select value={employeeName} onValueChange={setEmployeeName}>
                        <SelectTrigger data-testid="employee-select">
                          <Users className="w-4 h-4 mr-2" />
                          <SelectValue placeholder="Select employee" />
                        </SelectTrigger>
                        <SelectContent>
                          {employeeList.map((emp) => (
                            <SelectItem key={emp.name} value={emp.name}>
                              {emp.name} {emp.designation ? `(${emp.designation})` : ""}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <div className="h-10 flex items-center px-3 border rounded-md text-sm text-muted-foreground">
                        {targetCenter ? "No employees found for this center" : "Select a center first"}
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-3 pt-4 border-t">
            {!isPayslips && (
              <Button
                onClick={previewSalary}
                disabled={previewLoading || !targetCenter}
                variant="secondary"
                data-testid="preview-btn"
              >
                {previewLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Eye className="w-4 h-4 mr-2" />
                )}
                Preview Salary
              </Button>
            )}
            
            <Button
              onClick={isPayslips ? generatePayslips : generateSalary}
              disabled={loading || !targetCenter || (isPayslips && targetCenter === "ALL")}
              data-testid="generate-btn"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Download className="w-4 h-4 mr-2" />
              )}
              {isPayslips ? "Generate Payslips" : "Download Excel"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Salary Preview Table (only for salary page) */}
      {!isPayslips && salaryData && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Users className="w-5 h-5" />
                Salary for {salaryData.center} - {salaryData.month}
              </span>
              <Badge variant="secondary">
                {salaryData.employeeCount} Employees • {salaryData.daysInMonth} Days
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {/* Totals Summary */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <Card className="bg-green-50 dark:bg-green-950">
                <CardContent className="pt-4 text-center">
                  <p className="text-sm text-muted-foreground">Total Gross</p>
                  <p className="text-2xl font-bold text-green-600">
                    {formatCurrency(salaryData.totals.gross)}
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-orange-50 dark:bg-orange-950">
                <CardContent className="pt-4 text-center">
                  <p className="text-sm text-muted-foreground">Total Advance</p>
                  <p className="text-2xl font-bold text-orange-600">
                    {formatCurrency(salaryData.totals.advance)}
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-primary/10">
                <CardContent className="pt-4 text-center">
                  <p className="text-sm text-muted-foreground">Total Net</p>
                  <p className="text-2xl font-bold text-primary">
                    {formatCurrency(salaryData.totals.net)}
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Employee Table */}
            <ScrollArea className="h-[500px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[200px]">Employee</TableHead>
                    <TableHead>Designation</TableHead>
                    <TableHead>Center</TableHead>
                    <TableHead className="text-right">Monthly</TableHead>
                    <TableHead className="text-right">Days</TableHead>
                    <TableHead className="text-right">Gross</TableHead>
                    <TableHead className="text-right">Advance</TableHead>
                    <TableHead className="text-right">Net Salary</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {salaryData.salaryData.map((emp, idx) => (
                    <TableRow key={idx} data-testid={`salary-row-${idx}`}>
                      <TableCell className="font-medium">{emp.employeeName}</TableCell>
                      <TableCell>{emp.designation}</TableCell>
                      <TableCell><Badge variant="outline">{emp.center}</Badge></TableCell>
                      <TableCell className="text-right">{formatCurrency(emp.monthlySalary)}</TableCell>
                      <TableCell className="text-right">
                        <Badge variant="outline">{emp.presentDays}/{emp.daysInMonth}</Badge>
                      </TableCell>
                      <TableCell className="text-right text-green-600">
                        {formatCurrency(emp.grossSalary)}
                      </TableCell>
                      <TableCell className="text-right text-orange-600">
                        {emp.advance > 0 ? `-${formatCurrency(emp.advance)}` : "-"}
                      </TableCell>
                      <TableCell className="text-right font-bold">
                        {formatCurrency(emp.netSalary)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* Help Info */}
      <Card className="bg-muted/50">
        <CardContent className="pt-4">
          <h4 className="font-bold text-sm mb-2">
            {isPayslips ? "Payslip Information" : "Salary Calculation Rules"}
          </h4>
          {isPayslips ? (
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>Select a specific center to generate payslips</li>
              {isIntlCenter ? (
                <>
                  <li>Payslips use <strong>Australian WA payroll format</strong> (hourly rate, PAYG, Medicare, Super)</li>
                  <li>Hours are pulled from International Attendance records</li>
                  <li>Take-home rate is reverse-calculated to Gross using PAYG tax brackets</li>
                  <li>Super (12%) is on top of Gross, not deducted from Net</li>
                </>
              ) : (
                <>
                  <li>Use "Single Employee" mode for individual payslip</li>
                  <li>Enter FULL employee name in CAPS (e.g., EKTA SURESHKUMAR RAVAL)</li>
                  <li>PDF format recommended for printing</li>
                </>
              )}
            </ul>
          ) : (
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Select "ALL CENTERS" to view combined salary for all locations</li>
              <li>• <Badge variant="outline" className="status-P">P</Badge> Present = 1 day</li>
              <li>• <Badge variant="outline" className="status-HD">HD</Badge> Half Day = 0.5 day</li>
              <li>• <Badge variant="outline" className="status-WO">WO</Badge> Weekly Off = 1 day (paid)</li>
              <li>• <Badge variant="outline" className="status-L">L</Badge> Leave = 0 days (unpaid)</li>
              <li>• <Badge variant="outline" className="status-A">A</Badge> Absent = 0 days</li>
              <li>• <strong>Net = (Monthly Salary ÷ Days in Month × Present Days) - Advances</strong></li>
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
