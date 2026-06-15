// Master Franchisor Dashboard — Founder / Director / Super Admin view.
// Single source of truth: Financial Calculation Engine. Surfaces the
// Franchisor Bundle download. Deep-links to the deep MIS Dashboard for
// multi-center analysis.
import { useState, useEffect } from "react";
import { useAuth } from "@/App";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Download, Crown, TrendingUp, AlertTriangle, Activity, BarChart3, Loader2 } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function FranchisorDashboard() {
  const { session } = useAuth();
  const [centers, setCenters] = useState([]);
  const [center, setCenter] = useState("");
  const [period, setPeriod] = useState(new Date().toISOString().slice(0, 7));
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await axios.post(`${API}/franchises/list`, { token: session.token });
        const list = res.data.franchises || [];
        setCenters(list.map(f => ({ code: f.franchise_code, name: f.franchise_name, country: f.country })));
        if (list.length && !center) setCenter(list[0].franchise_code);
      } catch (e) {}
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
      const url = `${API}/bundles/franchisor?token=${encodeURIComponent(session.token)}&center=${encodeURIComponent(center)}&period=${encodeURIComponent(period)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `FRANCHISOR_${center}_${period}.zip`;
      a.click();
      URL.revokeObjectURL(a.href);
      toast.success("Franchisor Bundle downloaded");
    } catch (e) {
      toast.error(`Download failed: ${e.message}`);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-6 p-2" data-testid="franchisor-dashboard">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Crown className="w-7 h-7 text-amber-500" />
            Franchisor Dashboard
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Executive overview for Founders / Directors / Super Admin. Same Financial Engine across every screen.
          </p>
        </div>
        <Button onClick={downloadBundle} disabled={downloading} data-testid="download-franchisor-bundle"
                className="bg-amber-600 hover:bg-amber-700">
          {downloading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
          Download Franchisor Bundle (.zip)
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-sm font-medium">Filters</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <Label className="text-xs">Center</Label>
            <Select value={center} onValueChange={setCenter}>
              <SelectTrigger data-testid="franchisor-center-select"><SelectValue placeholder="Select center" /></SelectTrigger>
              <SelectContent>
                {centers.map(c => <SelectItem key={c.code} value={c.code}>{c.code} — {c.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Period (YYYY-MM)</Label>
            <Input type="month" value={period} onChange={e => setPeriod(e.target.value)} data-testid="franchisor-period-input" />
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <DeepLinkTile to="/mis-dashboard" icon={TrendingUp} title="Executive Summary"
                      subtitle="Sales · Expenses · PBT · Revenue Share · Profit Share · Working Capital · Loan · GST" />
        <DeepLinkTile to="/mis-dashboard" icon={BarChart3} title="Franchise Performance"
                      subtitle="Center Ranking · Revenue / Profit Share Analysis · Payout Status" />
        <DeepLinkTile to="/mis-dashboard" icon={AlertTriangle} title="Risk Management"
                      subtitle="WC Recovery · Blocked Settlements · Outstanding Balances · GST Exposure" />
        <DeepLinkTile to="/center-health" icon={Activity} title="Operational Insights"
                      subtitle="Center Health · Food Cost · Labour Cost · Expense Variance" />
      </div>

      <Card className="bg-muted/30">
        <CardContent className="p-4 text-xs text-muted-foreground">
          The Franchisor Bundle consolidates: Executive Summary · Financial Summary · Center Performance ·
          Working Capital Summary · Risk Analysis · Settlement Summary · Operational Summary — every figure
          sourced from the single Financial Engine.
        </CardContent>
      </Card>
    </div>
  );
}

function DeepLinkTile({ to, icon: Icon, title, subtitle }) {
  return (
    <Link to={to} className="block">
      <Card className="hover:border-amber-400 transition-colors h-full">
        <CardContent className="p-4">
          <Icon className="w-6 h-6 text-amber-600 mb-2" />
          <div className="font-semibold text-sm">{title}</div>
          <div className="text-xs text-muted-foreground mt-1 leading-snug">{subtitle}</div>
        </CardContent>
      </Card>
    </Link>
  );
}
