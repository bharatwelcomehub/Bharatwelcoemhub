import { useState } from "react";
import { useAuth } from "@/App";
import { api, CENTERS, getCurrentMonth } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { 
  Loader2, 
  Download, 
  FileSpreadsheet,
  FileText,
  Building2,
  Lock
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function Salary({ isPayslips = false }) {
  const { session } = useAuth();
  const [month, setMonth] = useState(getCurrentMonth());
  const [mode, setMode] = useState("all");
  const [targetCenter, setTargetCenter] = useState("");
  const [loading, setLoading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState("");
  
  // Payslips specific
  const [period, setPeriod] = useState("1");
  const [fmt, setFmt] = useState("pdf");
  const [employeeName, setEmployeeName] = useState("");

  const centerOptions = CENTERS.filter(c => c.code !== "PB-MGT");

  // Generate salary
  const generateSalary = async () => {
    if (mode === "single" && !targetCenter) {
      toast.error("Select a center for single mode");
      return;
    }
    
    setLoading(true);
    try {
      const res = await api.post("/generate_salary", {
        token: session.token,
        center: "PB-MGT",
        month: month,
        mode: mode,
        targetCenter: targetCenter || null
      });
      
      const url = `${BACKEND_URL}${res.data.downloadUrl}`;
      setDownloadUrl(url);
      toast.success("Salary file generated!");
      
      // Auto download
      window.open(url, "_blank");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to generate salary");
    } finally {
      setLoading(false);
    }
  };

  // Generate payslips
  const generatePayslips = async () => {
    if (mode === "single" && !employeeName) {
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
        mode: mode,
        targetCenter: targetCenter || null,
        employeeName: employeeName || null
      });
      
      const url = `${BACKEND_URL}${res.data.downloadUrl}`;
      setDownloadUrl(url);
      toast.success(`${res.data.count} payslip(s) generated!`);
      
      // Auto download
      window.open(url, "_blank");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to generate payslips");
    } finally {
      setLoading(false);
    }
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
        <h1 className="text-3xl font-bold text-primary">
          {isPayslips ? "Payslip Generation" : "Salary Generation"}
        </h1>
        <p className="text-muted-foreground mt-1">
          {isPayslips 
            ? "Generate PDF payslips for employees" 
            : "Generate salary Excel for ICICI bank upload"}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {isPayslips ? <FileText className="w-5 h-5" /> : <FileSpreadsheet className="w-5 h-5" />}
            {isPayslips ? "Generate Payslips" : "Generate Salary Excel"}
          </CardTitle>
          <CardDescription>
            {isPayslips 
              ? "Create individual payslip PDFs or a bulk ZIP file"
              : "Create ICICI bulk payment Excel file with attendance and advances"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Month */}
            <div className="space-y-2">
              <Label>Month</Label>
              <Input
                type="month"
                value={month}
                onChange={(e) => setMonth(e.target.value)}
                data-testid="salary-month"
              />
            </div>

            {/* Mode */}
            <div className="space-y-2">
              <Label>Mode</Label>
              <Select value={mode} onValueChange={setMode}>
                <SelectTrigger data-testid="salary-mode">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Centers</SelectItem>
                  <SelectItem value="single">Single Center/Employee</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Target Center (if single mode) */}
            {mode === "single" && (
              <div className="space-y-2">
                <Label>Target Center</Label>
                <Select value={targetCenter} onValueChange={setTargetCenter}>
                  <SelectTrigger data-testid="target-center">
                    <Building2 className="w-4 h-4 mr-2" />
                    <SelectValue placeholder="Select center" />
                  </SelectTrigger>
                  <SelectContent>
                    {centerOptions.map(c => (
                      <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Payslips specific fields */}
            {isPayslips && (
              <>
                <div className="space-y-2">
                  <Label>Period (Months)</Label>
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

                {mode === "single" && (
                  <div className="space-y-2">
                    <Label>Employee Name</Label>
                    <Input
                      value={employeeName}
                      onChange={(e) => setEmployeeName(e.target.value)}
                      placeholder="EMPLOYEE NAME (CAPS)"
                    />
                  </div>
                )}
              </>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap gap-4 pt-4">
            <Button
              onClick={isPayslips ? generatePayslips : generateSalary}
              disabled={loading}
              size="lg"
              data-testid="generate-btn"
            >
              {loading && <Loader2 className="w-5 h-5 mr-2 animate-spin" />}
              <Download className="w-5 h-5 mr-2" />
              Generate & Download
            </Button>

            {downloadUrl && (
              <Button
                variant="outline"
                size="lg"
                onClick={() => window.open(downloadUrl, "_blank")}
              >
                <Download className="w-5 h-5 mr-2" />
                Re-download Last File
              </Button>
            )}
          </div>

          {/* Info */}
          <div className="bg-muted rounded-lg p-4 space-y-2">
            <h4 className="font-bold text-sm">
              {isPayslips ? "Payslip Details" : "Salary Calculation Rules"}
            </h4>
            {isPayslips ? (
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• PDF payslips show gross salary, advances, and net salary</li>
                <li>• Bulk mode creates a ZIP file with all payslips</li>
                <li>• Period combines multiple months into one payslip</li>
              </ul>
            ) : (
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• <Badge variant="outline" className="status-P">P</Badge> Present = 1 day</li>
                <li>• <Badge variant="outline" className="status-HD">HD</Badge> Half Day = 0.5 day</li>
                <li>• <Badge variant="outline" className="status-WO">WO</Badge> Weekly Off = 1 day</li>
                <li>• <Badge variant="outline" className="status-L">L</Badge> Leave = 1 day</li>
                <li>• <Badge variant="outline" className="status-A">A</Badge> Absent = 0 days</li>
                <li>• Net = (Daily Rate × Working Days) - Advances</li>
              </ul>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
