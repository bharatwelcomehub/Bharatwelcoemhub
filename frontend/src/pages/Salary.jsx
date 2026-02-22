import { useState, useEffect } from "react";
import { useAuth } from "@/App";
import { api, CENTERS, getCurrentMonth } from "@/lib/api";
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
  Calculator
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

  // All centers except MGT for selection
  const centerOptions = CENTERS.filter(c => c.code !== "PB-MGT");

  // Preview salary on screen
  const previewSalary = async () => {
    if (!targetCenter) {
      toast.error("Please select a center first");
      return;
    }
    
    setPreviewLoading(true);
    setSalaryData(null);
    try {
      const res = await api.post("/salary_preview", {
        token: session.token,
        month: month,
        targetCenter: targetCenter
      });
      
      setSalaryData(res.data);
      toast.success(`Loaded salary data for ${res.data.employeeCount} employees`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to load salary preview");
    } finally {
      setPreviewLoading(false);
    }
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
        center: "PB-MGT",
        month: month,
        mode: "single",
        targetCenter: targetCenter
      }, {
        responseType: 'blob'
      });
      
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
      toast.error(e.response?.data?.detail || "Failed to generate salary");
    } finally {
      setLoading(false);
    }
  };

  // Generate payslips
  const generatePayslips = async () => {
    if (!targetCenter) {
      toast.error("Please select a center first");
      return;
    }
    if (payslipMode === "single" && !employeeName) {
      toast.error("Enter employee name for single mode");
      return;
    }
    
    setLoading(true);
    try {
      const res = await api.post("/payslips_generate", {
        token: session.token,
        center: "PB-MGT",
        month: month,
        period: period,
        fmt: fmt,
        mode: payslipMode,
        targetCenter: targetCenter,
        employeeName: payslipMode === "single" ? employeeName.toUpperCase() : null
      }, {
        responseType: 'blob'
      });
      
      // Determine file type
      const isZip = res.headers['content-type']?.includes('zip');
      const blob = new Blob([res.data], { 
        type: isZip ? 'application/zip' : 'application/pdf' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = isZip 
        ? `Payslips_${targetCenter}_${month}.zip` 
        : `Payslip_${targetCenter}_${month}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success("Payslip(s) downloaded!");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to generate payslips");
    } finally {
      setLoading(false);
    }
  };

  // Format currency
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  if (session?.center !== "PB-MGT") {
    return (
      <div className="text-center py-20">
        <Lock className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
        <h2 className="text-2xl font-bold text-muted-foreground">Access Denied</h2>
        <p className="text-muted-foreground mt-2">Only PB-MGT can access salary & payslips</p>
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
              <Select value={targetCenter} onValueChange={(v) => {
                setTargetCenter(v);
                setSalaryData(null);
              }}>
                <SelectTrigger data-testid="center-select">
                  <Building2 className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Select center" />
                </SelectTrigger>
                <SelectContent>
                  {centerOptions.map(c => (
                    <SelectItem key={c.code} value={c.code}>{c.code} - {c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Payslips specific fields */}
            {isPayslips && (
              <>
                <div className="space-y-2">
                  <Label>Period</Label>
                  <Select value={period} onValueChange={setPeriod}>
                    <SelectTrigger>
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
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pdf">PDF</SelectItem>
                      <SelectItem value="docx">DOCX</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Mode</Label>
                  <Select value={payslipMode} onValueChange={setPayslipMode}>
                    <SelectTrigger>
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
                    <Label>Employee Name</Label>
                    <Input
                      value={employeeName}
                      onChange={(e) => setEmployeeName(e.target.value)}
                      placeholder="EMPLOYEE NAME (CAPS)"
                      data-testid="employee-name"
                    />
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
              disabled={loading || !targetCenter}
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
              <li>• Select center to generate payslips for all employees</li>
              <li>• Use "Single Employee" mode for individual payslip</li>
              <li>• PDF format recommended for printing</li>
            </ul>
          ) : (
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• <Badge variant="outline" className="status-P">P</Badge> Present = 1 day</li>
              <li>• <Badge variant="outline" className="status-HD">HD</Badge> Half Day = 0.5 day</li>
              <li>• <Badge variant="outline" className="status-WO">WO</Badge> Weekly Off = 1 day (paid)</li>
              <li>• <Badge variant="outline" className="status-L">L</Badge> Leave = 1 day (paid)</li>
              <li>• <Badge variant="outline" className="status-A">A</Badge> Absent = 0 days</li>
              <li>• <strong>Net = (Monthly Salary ÷ Days in Month × Present Days) - Advances</strong></li>
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
