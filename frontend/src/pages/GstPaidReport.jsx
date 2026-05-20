import React, { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/App";
import { toast } from "sonner";
import {
  Activity, Download, FileSpreadsheet, FileText, Loader2, Package,
  Search, Calculator,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (n) => Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });

const monthOpts = () => {
  const out = [];
  const d = new Date();
  for (let i = 0; i < 24; i++) {
    const m = new Date(d.getFullYear(), d.getMonth() - i, 1);
    out.push({
      key: `${m.getFullYear()}-${String(m.getMonth() + 1).padStart(2, "0")}`,
      label: m.toLocaleString("en-US", { month: "short", year: "numeric" }),
    });
  }
  return out;
};
const fyOpts = () => {
  const out = [];
  const now = new Date();
  const curFy = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
  for (let i = 0; i < 4; i++) {
    const y = curFy - i;
    out.push(`FY ${y}-${String((y + 1) % 100).padStart(2, "0")}`);
  }
  return out;
};

export default function GstPaidReport() {
  const { session } = useAuth();
  const months = useMemo(monthOpts, []);
  const fys = useMemo(fyOpts, []);

  const [centers, setCenters] = useState([]);
  const [selectedCenters, setSelectedCenters] = useState([]);
  const [periodType, setPeriodType] = useState("month");
  const [month, setMonth] = useState(months[0]?.key);
  const [fromMonth, setFromMonth] = useState(months[5]?.key);
  const [toMonth, setToMonth] = useState(months[0]?.key);
  const [fy, setFy] = useState(fys[0]);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [vendor, setVendor] = useState("");
  const [category, setCategory] = useState("");
  const [currency, setCurrency] = useState("");
  const [minGst, setMinGst] = useState("");

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState("");

  useEffect(() => {
    if (!session?.token) return;
    (async () => {
      try {
        const r = await fetch(`${API}/api/health-dashboard/centers`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: session.token }),
        });
        if (r.ok) {
          const j = await r.json();
          const cs = (j.centers || []).filter((c) => c.code !== "PB-MGT");
          setCenters(cs);
        }
      } catch (e) { /* ignore */ }
    })();
  }, [session?.token]);

  const buildPayload = () => ({
    token: session.token,
    centers: selectedCenters,
    period_type: periodType,
    month: periodType === "month" ? month : undefined,
    from_month: periodType === "month_range" ? fromMonth : undefined,
    to_month: periodType === "month_range" ? toMonth : undefined,
    fy: periodType === "fy" ? fy : undefined,
    from_date: periodType === "custom" ? fromDate : undefined,
    to_date: periodType === "custom" ? toDate : undefined,
    vendor: vendor || undefined,
    category: category || undefined,
    currency: currency || undefined,
    min_gst: minGst === "" ? undefined : Number(minGst),
  });

  const loadReport = async () => {
    setLoading(true); setData(null);
    try {
      const r = await fetch(`${API}/api/gst-paid-report/summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildPayload()),
      });
      if (!r.ok) throw new Error(await r.text());
      setData(await r.json());
    } catch (e) {
      toast.error(`Failed: ${e.message || e}`);
    } finally { setLoading(false); }
  };

  const downloadFile = async (which) => {
    setDownloading(which);
    try {
      const r = await fetch(`${API}/api/gst-paid-report/${which}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildPayload()),
      });
      if (!r.ok) throw new Error(await r.text());
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const ext = which === "excel" ? "xlsx" : which;
      a.download = `gst_paid_report.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`${which.toUpperCase()} downloaded`);
    } catch (e) {
      toast.error(`Download failed: ${e.message || e}`);
    } finally { setDownloading(""); }
  };

  useEffect(() => {
    if (session?.token) loadReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.token]);

  const toggleCenter = (code) =>
    setSelectedCenters((prev) => (prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]));

  const rows = data?.rows || [];
  const totals = data?.aggregations?.totals || { base: 0, gst_paid: 0, total: 0 };
  const byVendor = data?.aggregations?.by_vendor || {};
  const byCenter = data?.aggregations?.by_center || {};
  const byCategory = data?.aggregations?.by_category || {};

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="gst-paid-report-page">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <Calculator className="w-6 h-6 text-amber-700" />
          GST Paid Report
        </h1>
        <p className="text-sm text-slate-500 mt-1">Vendor-/Center-wise GST printed on bills. Read directly from expense entries.</p>
      </div>

      {/* Filter bar */}
      <Card className="mb-4">
        <CardContent className="pt-4 pb-4">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
            <div className="md:col-span-2">
              <Label className="text-xs">Period Type</Label>
              <Select value={periodType} onValueChange={setPeriodType}>
                <SelectTrigger className="h-9" data-testid="gst-period-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="month">Single Month</SelectItem>
                  <SelectItem value="month_range">Month Range</SelectItem>
                  <SelectItem value="fy">Financial Year</SelectItem>
                  <SelectItem value="custom">Custom Dates</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {periodType === "month" && (
              <div className="md:col-span-2">
                <Label className="text-xs">Month</Label>
                <Select value={month} onValueChange={setMonth}>
                  <SelectTrigger className="h-9" data-testid="gst-month"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {months.map((m) => <SelectItem key={m.key} value={m.key}>{m.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            )}
            {periodType === "month_range" && (<>
              <div className="md:col-span-2">
                <Label className="text-xs">From</Label>
                <Select value={fromMonth} onValueChange={setFromMonth}>
                  <SelectTrigger className="h-9" data-testid="gst-from-month"><SelectValue /></SelectTrigger>
                  <SelectContent>{months.map((m) => <SelectItem key={m.key} value={m.key}>{m.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="md:col-span-2">
                <Label className="text-xs">To</Label>
                <Select value={toMonth} onValueChange={setToMonth}>
                  <SelectTrigger className="h-9" data-testid="gst-to-month"><SelectValue /></SelectTrigger>
                  <SelectContent>{months.map((m) => <SelectItem key={m.key} value={m.key}>{m.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </>)}
            {periodType === "fy" && (
              <div className="md:col-span-2">
                <Label className="text-xs">FY</Label>
                <Select value={fy} onValueChange={setFy}>
                  <SelectTrigger className="h-9" data-testid="gst-fy"><SelectValue /></SelectTrigger>
                  <SelectContent>{fys.map((f) => <SelectItem key={f} value={f}>{f}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            )}
            {periodType === "custom" && (<>
              <div className="md:col-span-2"><Label className="text-xs">From</Label><Input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="h-9" data-testid="gst-from-date" /></div>
              <div className="md:col-span-2"><Label className="text-xs">To</Label><Input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="h-9" data-testid="gst-to-date" /></div>
            </>)}

            <div className="md:col-span-2">
              <Label className="text-xs">Vendor (search)</Label>
              <Input value={vendor} onChange={(e) => setVendor(e.target.value)} placeholder="e.g. Reliance" className="h-9" data-testid="gst-vendor" />
            </div>
            <div className="md:col-span-2">
              <Label className="text-xs">Category</Label>
              <Input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g. GROCERY" className="h-9" data-testid="gst-category" />
            </div>
            <div className="md:col-span-1">
              <Label className="text-xs">Currency</Label>
              <Select value={currency || "ALL"} onValueChange={(v) => setCurrency(v === "ALL" ? "" : v)}>
                <SelectTrigger className="h-9" data-testid="gst-currency"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All</SelectItem>
                  <SelectItem value="INR">INR</SelectItem>
                  <SelectItem value="AUD">AUD</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="md:col-span-1">
              <Label className="text-xs">Min GST</Label>
              <Input type="number" value={minGst} onChange={(e) => setMinGst(e.target.value)} placeholder="0" className="h-9" data-testid="gst-min" />
            </div>
          </div>

          {/* Center pills */}
          <div className="mt-3">
            <Label className="text-xs">Centers ({selectedCenters.length || "All accessible"})</Label>
            <div className="flex flex-wrap gap-1.5 mt-1 p-1 border rounded max-h-24 overflow-auto" data-testid="gst-centers">
              {centers.map((c) => (
                <button
                  key={c.code}
                  type="button"
                  onClick={() => toggleCenter(c.code)}
                  className={`text-[11px] px-2 py-0.5 rounded-full border ${selectedCenters.includes(c.code) ? "bg-amber-700 text-white border-amber-700" : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"}`}
                  data-testid={`gst-center-${c.code}`}
                >
                  {c.code}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 mt-3">
            <Button onClick={loadReport} disabled={loading} className="bg-amber-700 hover:bg-amber-800 text-white" data-testid="gst-apply">
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Search className="w-4 h-4 mr-2" />}View Report
            </Button>
            <Button variant="outline" onClick={() => downloadFile("excel")} disabled={!data || downloading} data-testid="gst-download-xlsx">
              {downloading === "excel" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <FileSpreadsheet className="w-4 h-4 mr-2" />}Excel
            </Button>
            <Button variant="outline" onClick={() => downloadFile("pdf")} disabled={!data || downloading} data-testid="gst-download-pdf">
              {downloading === "pdf" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <FileText className="w-4 h-4 mr-2" />}PDF
            </Button>
            <Button variant="outline" onClick={() => downloadFile("zip")} disabled={!data || downloading} data-testid="gst-download-zip">
              {downloading === "zip" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Package className="w-4 h-4 mr-2" />}ZIP + Bills
            </Button>
          </div>
        </CardContent>
      </Card>

      {loading && (
        <div className="flex items-center justify-center py-12 text-slate-500"><Loader2 className="w-6 h-6 animate-spin mr-2" />Loading…</div>
      )}

      {data && !loading && (
        <>
          {/* Totals */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4" data-testid="gst-totals">
            <div className="rounded-xl border p-3 bg-blue-50">
              <div className="text-[11px] uppercase tracking-wider text-slate-600 font-semibold">Rows</div>
              <div className="text-xl font-bold mt-1">{rows.length}</div>
              <div className="text-[11px] text-slate-500">{data.period_label}</div>
            </div>
            <div className="rounded-xl border p-3 bg-white">
              <div className="text-[11px] uppercase tracking-wider text-slate-600 font-semibold">Base Amount</div>
              <div className="text-xl font-bold mt-1">{fmt(totals.base)}</div>
            </div>
            <div className="rounded-xl border p-3 bg-amber-50">
              <div className="text-[11px] uppercase tracking-wider text-amber-800 font-semibold">GST Paid</div>
              <div className="text-xl font-bold mt-1 text-amber-800">{fmt(totals.gst_paid)}</div>
            </div>
            <div className="rounded-xl border p-3 bg-emerald-50">
              <div className="text-[11px] uppercase tracking-wider text-emerald-800 font-semibold">Total Expense</div>
              <div className="text-xl font-bold mt-1 text-emerald-800">{fmt(totals.total)}</div>
            </div>
          </div>

          {/* Three summary tables */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
            <SummaryCard title="By Vendor" map={byVendor} testid="by-vendor" />
            <SummaryCard title="By Center" map={byCenter} testid="by-center" />
            <SummaryCard title="By Category" map={byCategory} testid="by-category" />
          </div>

          {/* Detail */}
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-base">Detail ({rows.length} rows)</CardTitle></CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm" data-testid="gst-detail-table">
                  <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                    <tr>
                      <th className="text-left p-2">Date</th>
                      <th className="text-left p-2">Center</th>
                      <th className="text-left p-2">Vendor</th>
                      <th className="text-left p-2">Category</th>
                      <th className="text-right p-2">Base</th>
                      <th className="text-right p-2">GST</th>
                      <th className="text-right p-2">Total</th>
                      <th className="text-left p-2">Mode</th>
                      <th className="text-left p-2">By</th>
                      <th className="text-left p-2">Bill</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.slice(0, 500).map((r, i) => (
                      <tr key={i} className="border-b border-slate-100">
                        <td className="p-2 whitespace-nowrap">{r.date}</td>
                        <td className="p-2 whitespace-nowrap">{r.center}</td>
                        <td className="p-2">{r.vendor_name}</td>
                        <td className="p-2">{r.expense_category}</td>
                        <td className="p-2 text-right">{fmt(r.base_amount)}</td>
                        <td className="p-2 text-right text-amber-700 font-semibold">{fmt(r.gst_paid)}</td>
                        <td className="p-2 text-right font-semibold">{fmt(r.total_expense)}</td>
                        <td className="p-2">{r.payment_mode}</td>
                        <td className="p-2 text-xs text-slate-500">{r.entered_by}</td>
                        <td className="p-2">
                          {r.bill_attachment_url ? (
                            <a href={r.bill_attachment_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline text-xs">View</a>
                          ) : <span className="text-xs text-slate-400">—</span>}
                        </td>
                      </tr>
                    ))}
                    {rows.length === 0 && (
                      <tr><td colSpan="10" className="p-6 text-center text-slate-500">No expenses match these filters.</td></tr>
                    )}
                  </tbody>
                </table>
                {rows.length > 500 && (
                  <div className="text-xs text-slate-500 text-center mt-2">Showing first 500 rows. Download Excel for full list.</div>
                )}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function SummaryCard({ title, map, testid }) {
  const items = Object.entries(map || {}).sort((a, b) => b[1].gst_paid - a[1].gst_paid);
  return (
    <Card data-testid={`gst-summary-${testid}`}>
      <CardHeader className="pb-2"><CardTitle className="text-base flex items-center gap-1"><Activity className="w-4 h-4 text-amber-700" />{title}</CardTitle></CardHeader>
      <CardContent>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-600">
            <tr>
              <th className="text-left p-2">Name</th>
              <th className="text-right p-2">GST</th>
              <th className="text-right p-2">Total</th>
            </tr>
          </thead>
          <tbody>
            {items.slice(0, 10).map(([name, d]) => (
              <tr key={name} className="border-b border-slate-100">
                <td className="p-2 truncate max-w-[150px]" title={name}>{name}</td>
                <td className="p-2 text-right text-amber-700 font-semibold">{fmt(d.gst_paid)}</td>
                <td className="p-2 text-right">{fmt(d.total)}</td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan="3" className="p-4 text-center text-slate-500 text-xs">No data</td></tr>
            )}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
