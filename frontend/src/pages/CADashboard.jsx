// Master CA Dashboard — single source of truth for the Accounts Team.
// Pulls from the Financial Engine exclusively. Surfaces the CA Bundle download.
import { useState, useEffect } from "react";
import { useAuth } from "@/App";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Download, Calculator, FileText, Wallet, Building2, Receipt, Loader2 } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function CADashboard() {
  const { session } = useAuth();
  const [centers, setCenters] = useState([]);
  const [center, setCenter] = useState("");
  const [period, setPeriod] = useState(new Date().toISOString().slice(0, 7));
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        // Bundles are per-center: load centers (not franchises) so the
        // bundle endpoint receives an actual `center_code`.
        const res = await axios.get(`${API}/centers`);
        const list = (res.data.centers || []).filter(c => c.active !== false);
        setCenters(list.map(c => ({ code: c.code, name: c.name, country: c.country })));
        if (list.length && !center) setCenter(list[0].code);
      } catch (e) {
        // graceful fallback — let user type center code manually
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const downloadBundle = async () => {
    if (!center || !period) {
      toast.error("Pick a center and period first.");
      return;
    }
    setDownloading(true);
    try {
      const url = `${API}/bundles/ca?token=${encodeURIComponent(session.token)}&center=${encodeURIComponent(center)}&period=${encodeURIComponent(period)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `CA_${center}_${period}.zip`;
      a.click();
      URL.revokeObjectURL(a.href);
      toast.success("CA Bundle downloaded");
    } catch (e) {
      toast.error(`Download failed: ${e.message}`);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-6 p-2" data-testid="ca-dashboard">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Calculator className="w-7 h-7 text-emerald-600" />
            CA Dashboard
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Single source of truth for the Accounts Team. All figures driven by the Financial Calculation Engine.
          </p>
        </div>
        <Button onClick={downloadBundle} disabled={downloading} data-testid="download-ca-bundle"
                className="bg-emerald-600 hover:bg-emerald-700">
          {downloading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
          Download CA Bundle (.zip)
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Filters</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <Label className="text-xs">Center</Label>
            <Select value={center} onValueChange={setCenter}>
              <SelectTrigger data-testid="ca-center-select"><SelectValue placeholder="Select center" /></SelectTrigger>
              <SelectContent>
                {centers.map(c => <SelectItem key={c.code} value={c.code}>{c.code} — {c.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Period (YYYY-MM)</Label>
            <Input type="month" value={period} onChange={e => setPeriod(e.target.value)} data-testid="ca-period-input" />
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <DeepLinkTile to="/center-accounts" icon={FileText} title="Financial Summary"
                      subtitle="Sales · GST · Commissions · Revenue/Profit Share Base · Expenses · Adjustments · PBT" />
        <DeepLinkTile to="/center-accounts" icon={Wallet} title="Cash & Banking"
                      subtitle="Cash Position · Bank Position · Reconciliation Status" />
        <DeepLinkTile to="/center-accounts" icon={Building2} title="Working Capital"
                      subtitle="Opening WC · Current WC · WC Recovery · Protection Status" />
        <DeepLinkTile to="/gst-paid-report" icon={Receipt} title="Compliance"
                      subtitle="GST Collected · GST Paid · GST Outstanding" />
      </div>

      <Card className="bg-muted/30">
        <CardContent className="p-4 text-xs text-muted-foreground">
          The CA Bundle consolidates: Executive Summary · P&amp;L · Cash Summary · Bank Summary ·
          Expense Summary · GST Summary · Reconciliation Summary · Compliance Summary — all from a single
          Financial Engine call. The included manifest file is the audit trail of which exact engine output
          produced every figure.
        </CardContent>
      </Card>
    </div>
  );
}

function DeepLinkTile({ to, icon: Icon, title, subtitle }) {
  return (
    <Link to={to} className="block">
      <Card className="hover:border-emerald-400 transition-colors h-full">
        <CardContent className="p-4">
          <Icon className="w-6 h-6 text-emerald-600 mb-2" />
          <div className="font-semibold text-sm">{title}</div>
          <div className="text-xs text-muted-foreground mt-1 leading-snug">{subtitle}</div>
        </CardContent>
      </Card>
    </Link>
  );
}
