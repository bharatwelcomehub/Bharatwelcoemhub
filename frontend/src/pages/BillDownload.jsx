import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { api, fetchCentersFromDB, isAdminUser } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Loader2, Download, Search, RefreshCw, FileText, Archive, Eye, File,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function BillDownload() {
  const { session } = useAuth();
  const isAdmin = isAdminUser(session);
  const [loading, setLoading] = useState(false);
  const [zipLoading, setZipLoading] = useState(false);
  const [centersList, setCentersList] = useState([]);
  const [bills, setBills] = useState([]);
  const [docTypes, setDocTypes] = useState([]);
  const [selectedBills, setSelectedBills] = useState(new Set());
  const [search, setSearch] = useState("");

  // Filters
  const [filterCenter, setFilterCenter] = useState(session?.center || "");
  const [filterDocType, setFilterDocType] = useState("");
  const [filterMonth, setFilterMonth] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");

  useEffect(() => {
    if (session?.token) fetchCentersFromDB(session.token).then(setCentersList);
  }, [session?.token]);

  const loadBills = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.post("/bill-download/list", {
        token: session.token, center: filterCenter, doc_type: filterDocType,
        month: filterMonth, date_from: filterDateFrom, date_to: filterDateTo,
      });
      setBills(res.data.bills || []);
      if (res.data.doc_types) setDocTypes(res.data.doc_types);
      setSelectedBills(new Set());
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to load bills");
    } finally { setLoading(false); }
  }, [session?.token, filterCenter, filterDocType, filterMonth, filterDateFrom, filterDateTo]);

  useEffect(() => {
    if (session?.token) loadBills();
  }, [loadBills, session?.token]);

  const toggleBill = (billId) => {
    setSelectedBills(prev => {
      const next = new Set(prev);
      next.has(billId) ? next.delete(billId) : next.add(billId);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedBills.size === filteredBills.length) {
      setSelectedBills(new Set());
    } else {
      setSelectedBills(new Set(filteredBills.map(b => b.bill_id)));
    }
  };

  const downloadZip = async (params = {}) => {
    setZipLoading(true);
    try {
      const payload = {
        token: session.token, center: filterCenter || session?.center,
        ...params,
      };
      if (params.selectedOnly && selectedBills.size > 0) {
        payload.bill_ids = Array.from(selectedBills);
      }
      const res = await api.post("/bill-download/download-zip", payload, { responseType: "blob" });
      const ct = res.headers["content-type"] || "";
      if (ct.includes("application/json")) {
        const text = await res.data.text();
        toast.error(JSON.parse(text).detail || "No bills found");
        return;
      }
      const blob = new Blob([res.data], { type: "application/zip" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `Bills_${filterCenter || "ALL"}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success("ZIP downloaded!");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Download failed");
    } finally { setZipLoading(false); }
  };

  const viewBill = (url) => {
    if (url) window.open(url, "_blank");
    else toast.error("No file URL available");
  };

  const downloadSingle = (url, name) => {
    if (!url) { toast.error("No file URL"); return; }
    const link = document.createElement("a");
    link.href = url;
    link.download = name || "bill";
    link.target = "_blank";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredBills = bills.filter(b => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (b.description || "").toLowerCase().includes(q)
      || (b.doc_type || "").toLowerCase().includes(q)
      || (b.bill_id || "").toLowerCase().includes(q)
      || (b.expense_head || "").toLowerCase().includes(q);
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-primary" data-testid="bill-download-title">Bill Download</h1>
          <p className="text-muted-foreground mt-1">View and download bills, invoices, and documents</p>
        </div>
        <div className="flex gap-2">
          {selectedBills.size > 0 && (
            <Button onClick={() => downloadZip({ selectedOnly: true })} disabled={zipLoading}
              className="bg-blue-600 hover:bg-blue-700" data-testid="download-selected-btn">
              {zipLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Archive className="w-4 h-4 mr-2" />}
              Download Selected ({selectedBills.size})
            </Button>
          )}
          <Button onClick={() => downloadZip({ month: filterMonth })} disabled={zipLoading} variant="outline"
            data-testid="download-month-zip">
            <Archive className="w-4 h-4 mr-2" /> Month ZIP
          </Button>
          <Button onClick={() => downloadZip({ date_from: filterDateFrom, date_to: filterDateTo })} disabled={zipLoading} variant="outline"
            data-testid="download-range-zip">
            <Archive className="w-4 h-4 mr-2" /> Custom ZIP
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3 items-end">
            <div className="space-y-1">
              <Label className="text-xs">Center</Label>
              <select value={filterCenter} onChange={e => setFilterCenter(e.target.value)}
                className="w-full h-9 px-2 rounded-md border border-input bg-background text-xs"
                disabled={!isAdmin} data-testid="bill-center-filter">
                {!isAdmin && <option value={session?.center}>{session?.center}</option>}
                {isAdmin && <>
                  <option value="">All Centers</option>
                  {centersList.map(c => <option key={c.code} value={c.code}>{c.code}</option>)}
                </>}
              </select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Doc Type</Label>
              <select value={filterDocType} onChange={e => setFilterDocType(e.target.value)}
                className="w-full h-9 px-2 rounded-md border border-input bg-background text-xs">
                <option value="">All Types</option>
                {docTypes.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Month</Label>
              <Input type="month" value={filterMonth} onChange={e => setFilterMonth(e.target.value)} className="h-9 text-xs" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">From Date</Label>
              <Input type="date" value={filterDateFrom} onChange={e => setFilterDateFrom(e.target.value)} className="h-9 text-xs" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">To Date</Label>
              <Input type="date" value={filterDateTo} onChange={e => setFilterDateTo(e.target.value)} className="h-9 text-xs" />
            </div>
            <div className="flex gap-2">
              <Button onClick={loadBills} size="sm" disabled={loading}>
                {loading ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Search className="w-3 h-3 mr-1" />} Filter
              </Button>
              <Button onClick={loadBills} size="sm" variant="outline" disabled={loading}>
                <RefreshCw className="w-3 h-3" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Search */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="Search bills..." value={search} onChange={e => setSearch(e.target.value)}
            className="pl-9" data-testid="bill-search" />
        </div>
        <Badge variant="outline">{filteredBills.length} bills</Badge>
      </div>

      {/* Bills Table */}
      <div className="border rounded-lg overflow-hidden">
        <div className="overflow-x-auto max-h-[600px]">
          <table className="w-full text-sm">
            <thead className="bg-muted sticky top-0 z-10">
              <tr>
                <th className="p-3 w-10">
                  <Checkbox checked={selectedBills.size === filteredBills.length && filteredBills.length > 0}
                    onCheckedChange={selectAll} />
                </th>
                <th className="p-3 text-left font-bold">Bill ID</th>
                <th className="p-3 text-left font-bold">Center</th>
                <th className="p-3 text-left font-bold">Date</th>
                <th className="p-3 text-left font-bold">Type</th>
                <th className="p-3 text-left font-bold">Description</th>
                <th className="p-3 text-right font-bold">Amount</th>
                <th className="p-3 text-left font-bold">Uploaded By</th>
                <th className="p-3 text-center font-bold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredBills.map((bill, idx) => (
                <tr key={bill.bill_id || idx} className="border-t hover:bg-muted/30" data-testid={`bill-row-${idx}`}>
                  <td className="p-3">
                    <Checkbox checked={selectedBills.has(bill.bill_id)}
                      onCheckedChange={() => toggleBill(bill.bill_id)} />
                  </td>
                  <td className="p-3 font-mono text-xs">{bill.bill_id}</td>
                  <td className="p-3"><Badge variant="outline">{bill.center}</Badge></td>
                  <td className="p-3 text-xs">{bill.date}</td>
                  <td className="p-3"><Badge variant="secondary">{bill.doc_type}</Badge></td>
                  <td className="p-3 text-xs max-w-[200px] truncate">{bill.description || "-"}</td>
                  <td className="p-3 text-right font-mono">{bill.amount ? `${bill.amount.toLocaleString()}` : "-"}</td>
                  <td className="p-3 text-xs">{bill.uploaded_by || "-"}</td>
                  <td className="p-3 text-center">
                    <div className="flex gap-1 justify-center">
                      <Button size="sm" variant="ghost" onClick={() => viewBill(bill.file_url)} title="View">
                        <Eye className="w-3 h-3" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => downloadSingle(bill.file_url, bill.file_name)} title="Download">
                        <Download className="w-3 h-3" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredBills.length === 0 && (
                <tr><td colSpan={9} className="p-8 text-center text-muted-foreground">
                  <File className="w-12 h-12 mx-auto mb-3 opacity-40" />
                  <p>No bills found for the selected filters</p>
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
