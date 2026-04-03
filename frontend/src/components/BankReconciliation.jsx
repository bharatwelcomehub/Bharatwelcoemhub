import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  Upload, FileSpreadsheet, CheckCircle2, AlertTriangle, XCircle,
  Download, ArrowRightLeft, Eye, Plus, Ban, Search
} from "lucide-react";
import { api } from "@/lib/api";

const fmt = (n) => new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n || 0);

export default function BankReconciliation({ session, selectedCenter, centersList }) {
  const [file, setFile] = useState(null);
  const [month, setMonth] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
  const [center, setCenter] = useState(selectedCenter || "");
  const [bankAccount, setBankAccount] = useState("");
  const [uploading, setUploading] = useState(false);

  // Results
  const [uploadId, setUploadId] = useState(null);
  const [summary, setSummary] = useState(null);
  const [matched, setMatched] = useState([]);
  const [unrecorded, setUnrecorded] = useState([]);
  const [added, setAdded] = useState([]);
  const [ignored, setIgnored] = useState([]);
  const [resultTab, setResultTab] = useState("unrecorded");
  const [filterText, setFilterText] = useState("");

  // Master data
  const [expenseTypes, setExpenseTypes] = useState([]);
  const [paymentModes, setPaymentModes] = useState([]);

  // Editing state
  const [editingTxn, setEditingTxn] = useState(null);
  const [editCategory, setEditCategory] = useState("");
  const [editMode, setEditMode] = useState("BANK TRANSFER");
  const [editDesc, setEditDesc] = useState("");

  useEffect(() => {
    if (selectedCenter) setCenter(selectedCenter);
  }, [selectedCenter]);

  useEffect(() => {
    api.get("/sales/expense-types").then(r => {
      if (r.data.expense_types) setExpenseTypes(r.data.expense_types);
    }).catch(() => {});
    api.get("/sales/payment-modes").then(r => {
      if (r.data.payment_modes) setPaymentModes(r.data.payment_modes);
    }).catch(() => {});
  }, []);

  const handleUpload = async () => {
    if (!file) return toast.error("Please select a bank statement file");
    if (!center) return toast.error("Please select a center");
    if (!month) return toast.error("Please select a month");
    
    // Validate file size
    if (file.size === 0) {
      return toast.error("File appears to be empty. Please select a valid file.");
    }
    if (file.size > 10 * 1024 * 1024) {
      return toast.error("File too large. Maximum size is 10MB.");
    }
    
    console.log("Uploading file:", file.name, "size:", file.size, "bytes");

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("center", center);
      formData.append("month", month);
      formData.append("bank_account", bankAccount);
      formData.append("token", session?.token || "");
      
      console.log("Sending request with token:", session?.token ? "present" : "missing");

      const res = await api.post("/bank-reconciliation/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      
      console.log("Upload response:", res.data);

      if (res.data.success) {
        setUploadId(res.data.upload_id);
        setSummary(res.data.summary);
        setMatched(res.data.matched || []);
        setUnrecorded(res.data.unrecorded || []);
        setAdded([]);
        setIgnored([]);
        toast.success(`Reconciliation complete: ${res.data.summary.matched_count} matched, ${res.data.summary.unrecorded_count} unrecorded`);
      } else {
        toast.error(res.data.detail || "Upload failed");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleAddExpense = async (txn) => {
    if (!editCategory) return toast.error("Please select a category");
    try {
      const res = await api.post("/bank-reconciliation/add-expense", {
        transaction_id: txn.transaction_id,
        upload_id: uploadId,
        expense_type: editCategory,
        payment_mode: editMode,
        description: editDesc || txn.narration,
        token: session?.token || "",
      });
      if (res.data.success) {
        toast.success("Expense added successfully");
        const updatedTxn = { ...txn, match_status: "added" };
        setUnrecorded(prev => prev.filter(t => t.transaction_id !== txn.transaction_id));
        setAdded(prev => [...prev, updatedTxn]);
        setEditingTxn(null);
        setSummary(prev => prev ? {
          ...prev,
          unrecorded_count: prev.unrecorded_count - 1,
          unrecorded_amount: round2(prev.unrecorded_amount - txn.debit_amount),
          added_count: (prev.added_count || 0) + 1,
          added_amount: round2((prev.added_amount || 0) + txn.debit_amount),
        } : prev);
      } else {
        toast.error(res.data.detail || "Failed to add expense");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to add expense");
    }
  };

  const handleIgnore = async (txn) => {
    try {
      const res = await api.post("/bank-reconciliation/ignore", {
        transaction_id: txn.transaction_id,
        upload_id: uploadId,
        reason: "User ignored during reconciliation",
        token: session?.token || "",
      });
      if (res.data.success) {
        toast.success("Transaction ignored");
        setUnrecorded(prev => prev.filter(t => t.transaction_id !== txn.transaction_id));
        setIgnored(prev => [...prev, { ...txn, match_status: "ignored" }]);
        setSummary(prev => prev ? {
          ...prev,
          unrecorded_count: prev.unrecorded_count - 1,
          unrecorded_amount: round2(prev.unrecorded_amount - txn.debit_amount),
          ignored_count: (prev.ignored_count || 0) + 1,
          ignored_amount: round2((prev.ignored_amount || 0) + txn.debit_amount),
        } : prev);
      }
    } catch (err) {
      toast.error("Failed to ignore transaction");
    }
  };

  const handleExport = async () => {
    if (!uploadId) return;
    try {
      const res = await api.post("/bank-reconciliation/export", {
        upload_id: uploadId,
        token: session?.token || "",
      });
      if (res.data.success && res.data.rows) {
        const headers = Object.keys(res.data.rows[0] || {});
        let csv = headers.join(",") + "\n";
        for (const row of res.data.rows) {
          csv += headers.map(h => `"${String(row[h] || "").replace(/"/g, '""')}"`).join(",") + "\n";
        }
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `reconciliation_${center}_${month}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success("Report downloaded");
      }
    } catch (err) {
      toast.error("Export failed");
    }
  };

  const round2 = (n) => Math.round((n || 0) * 100) / 100;

  const startEdit = (txn) => {
    setEditingTxn(txn.transaction_id);
    setEditCategory(txn.suggested_category || "");
    setEditMode("BANK TRANSFER");
    setEditDesc(txn.narration || "");
  };

  const filteredUnrecorded = useMemo(() => {
    if (!filterText) return unrecorded;
    const q = filterText.toLowerCase();
    return unrecorded.filter(t =>
      (t.narration || "").toLowerCase().includes(q) ||
      (t.suggested_category || "").toLowerCase().includes(q) ||
      String(t.debit_amount).includes(q)
    );
  }, [unrecorded, filterText]);

  const filteredMatched = useMemo(() => {
    if (!filterText) return matched;
    const q = filterText.toLowerCase();
    return matched.filter(t =>
      (t.narration || "").toLowerCase().includes(q) ||
      String(t.debit_amount).includes(q)
    );
  }, [matched, filterText]);

  // ── Render ──

  return (
    <div className="space-y-5" data-testid="bank-reconciliation">
      {/* Upload Section */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <ArrowRightLeft className="w-4 h-4" />
            Bank Statement vs Expense Reconciliation
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Center</label>
              <Select value={center} onValueChange={setCenter}>
                <SelectTrigger className="h-9 text-sm" data-testid="recon-center"><SelectValue placeholder="Select Center" /></SelectTrigger>
                <SelectContent>
                  {(centersList || []).map(c => {
                    const code = typeof c === "string" ? c : c.code;
                    const name = typeof c === "string" ? c : c.name;
                    return <SelectItem key={code} value={code}>{code} - {name}</SelectItem>;
                  })}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Month</label>
              <Input type="month" value={month} onChange={e => setMonth(e.target.value)} className="h-9 text-sm" data-testid="recon-month" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Bank Account (Optional)</label>
              <Input value={bankAccount} onChange={e => setBankAccount(e.target.value)} placeholder="e.g., HDFC 1234" className="h-9 text-sm" data-testid="recon-bank" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Bank Statement (Excel/CSV/PDF)</label>
              <Input
                type="file"
                accept=".xlsx,.xls,.csv,.pdf"
                onChange={e => setFile(e.target.files?.[0] || null)}
                className="h-9 text-sm"
                data-testid="recon-file"
              />
            </div>
          </div>
          <Button onClick={handleUpload} disabled={uploading || !file || !center || !month} className="gap-2" data-testid="recon-upload-btn">
            {uploading ? <><span className="animate-spin">...</span> Processing...</> : <><Upload className="w-4 h-4" /> Upload &amp; Reconcile</>}
          </Button>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <SummaryCard icon={<FileSpreadsheet className="w-4 h-4 text-blue-600" />} label="Bank Debits" value={`Rs. ${fmt(summary.total_bank_debits)}`} sub={`${summary.total_bank_transactions} txns`} color="blue" />
          <SummaryCard icon={<CheckCircle2 className="w-4 h-4 text-green-600" />} label="Matched" value={`Rs. ${fmt(summary.matched_amount)}`} sub={`${summary.matched_count} txns`} color="green" />
          <SummaryCard icon={<AlertTriangle className="w-4 h-4 text-amber-600" />} label="Unrecorded" value={`Rs. ${fmt(summary.unrecorded_amount)}`} sub={`${summary.unrecorded_count} txns`} color="amber" />
          <SummaryCard icon={<Plus className="w-4 h-4 text-purple-600" />} label="Added" value={`Rs. ${fmt(summary.added_amount || 0)}`} sub={`${summary.added_count || 0} txns`} color="purple" />
          <SummaryCard icon={<Ban className="w-4 h-4 text-gray-500" />} label="Ignored" value={`Rs. ${fmt(summary.ignored_amount || 0)}`} sub={`${summary.ignored_count || 0} txns`} color="gray" />
        </div>
      )}

      {/* Results */}
      {uploadId && (
        <Card>
          <CardContent className="pt-5">
            <div className="flex justify-between items-center mb-4">
              <div className="relative flex-1 max-w-xs">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search narration, amount..."
                  value={filterText}
                  onChange={e => setFilterText(e.target.value)}
                  className="pl-9 h-9 text-sm"
                  data-testid="recon-search"
                />
              </div>
              <Button variant="outline" size="sm" onClick={handleExport} className="gap-1.5" data-testid="recon-export">
                <Download className="w-3.5 h-3.5" /> Export CSV
              </Button>
            </div>

            <Tabs value={resultTab} onValueChange={setResultTab}>
              <TabsList className="mb-3">
                <TabsTrigger value="unrecorded" className="gap-1.5 text-amber-700" data-testid="tab-unrecorded">
                  <AlertTriangle className="w-3.5 h-3.5" /> Unrecorded ({unrecorded.length})
                </TabsTrigger>
                <TabsTrigger value="matched" className="gap-1.5 text-green-700" data-testid="tab-matched">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Matched ({matched.length})
                </TabsTrigger>
                <TabsTrigger value="added" className="gap-1.5 text-purple-700" data-testid="tab-added">
                  <Plus className="w-3.5 h-3.5" /> Added ({added.length})
                </TabsTrigger>
                <TabsTrigger value="ignored" className="gap-1.5 text-gray-500" data-testid="tab-ignored">
                  <Ban className="w-3.5 h-3.5" /> Ignored ({ignored.length})
                </TabsTrigger>
              </TabsList>

              {/* Unrecorded Expenses */}
              <TabsContent value="unrecorded">
                {filteredUnrecorded.length === 0 ? (
                  <div className="text-center py-8 text-gray-400 text-sm">No unrecorded transactions found</div>
                ) : (
                  <div className="overflow-x-auto border rounded-lg">
                    <table className="w-full text-sm">
                      <thead className="bg-amber-50">
                        <tr>
                          <th className="text-left py-2.5 px-3 font-semibold text-xs text-amber-800">Date</th>
                          <th className="text-left py-2.5 px-3 font-semibold text-xs text-amber-800">Narration</th>
                          <th className="text-right py-2.5 px-3 font-semibold text-xs text-amber-800">Amount</th>
                          <th className="text-left py-2.5 px-3 font-semibold text-xs text-amber-800">Suggested Category</th>
                          <th className="text-left py-2.5 px-3 font-semibold text-xs text-amber-800">Ref</th>
                          <th className="text-center py-2.5 px-3 font-semibold text-xs text-amber-800">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {filteredUnrecorded.map((txn) => (
                          <tr key={txn.transaction_id} className="hover:bg-amber-50/40">
                            <td className="py-2 px-3 text-xs whitespace-nowrap">{txn.transaction_date}</td>
                            <td className="py-2 px-3 text-xs max-w-[250px] truncate" title={txn.narration}>{txn.narration}</td>
                            <td className="py-2 px-3 text-xs text-right font-semibold text-red-600">Rs. {fmt(txn.debit_amount)}</td>
                            <td className="py-2 px-3 text-xs">
                              {txn.suggested_category ? (
                                <Badge variant="secondary" className="text-xs">{txn.suggested_category}</Badge>
                              ) : (
                                <span className="text-gray-400 italic">No suggestion</span>
                              )}
                            </td>
                            <td className="py-2 px-3 text-xs text-gray-500 max-w-[80px] truncate">{txn.reference_number}</td>
                            <td className="py-2 px-3 text-center">
                              {editingTxn === txn.transaction_id ? (
                                <div className="flex flex-col gap-1.5 min-w-[280px]">
                                  <Select value={editCategory} onValueChange={setEditCategory}>
                                    <SelectTrigger className="h-7 text-xs"><SelectValue placeholder="Category *" /></SelectTrigger>
                                    <SelectContent>
                                      {expenseTypes.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                                    </SelectContent>
                                  </Select>
                                  <Select value={editMode} onValueChange={setEditMode}>
                                    <SelectTrigger className="h-7 text-xs"><SelectValue placeholder="Payment Mode" /></SelectTrigger>
                                    <SelectContent>
                                      {paymentModes.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                                    </SelectContent>
                                  </Select>
                                  <Input value={editDesc} onChange={e => setEditDesc(e.target.value)} placeholder="Description" className="h-7 text-xs" />
                                  <div className="flex gap-1">
                                    <Button size="sm" className="h-7 text-xs flex-1 bg-green-600 hover:bg-green-700" onClick={() => handleAddExpense(txn)} data-testid={`confirm-add-${txn.transaction_id}`}>
                                      <CheckCircle2 className="w-3 h-3 mr-1" /> Confirm
                                    </Button>
                                    <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setEditingTxn(null)}>Cancel</Button>
                                  </div>
                                </div>
                              ) : (
                                <div className="flex gap-1 justify-center">
                                  <Button size="sm" variant="outline" className="h-7 text-xs gap-1 text-green-700 hover:bg-green-50" onClick={() => startEdit(txn)} data-testid={`add-expense-${txn.transaction_id}`}>
                                    <Plus className="w-3 h-3" /> Add
                                  </Button>
                                  <Button size="sm" variant="ghost" className="h-7 text-xs gap-1 text-gray-400 hover:text-gray-600" onClick={() => handleIgnore(txn)} data-testid={`ignore-${txn.transaction_id}`}>
                                    <XCircle className="w-3 h-3" /> Ignore
                                  </Button>
                                </div>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </TabsContent>

              {/* Matched */}
              <TabsContent value="matched">
                {filteredMatched.length === 0 ? (
                  <div className="text-center py-8 text-gray-400 text-sm">No matched transactions</div>
                ) : (
                  <div className="overflow-x-auto border rounded-lg">
                    <table className="w-full text-sm">
                      <thead className="bg-green-50">
                        <tr>
                          <th className="text-left py-2.5 px-3 font-semibold text-xs text-green-800">Date</th>
                          <th className="text-left py-2.5 px-3 font-semibold text-xs text-green-800">Bank Narration</th>
                          <th className="text-right py-2.5 px-3 font-semibold text-xs text-green-800">Amount</th>
                          <th className="text-left py-2.5 px-3 font-semibold text-xs text-green-800">Matched Expense</th>
                          <th className="text-left py-2.5 px-3 font-semibold text-xs text-green-800">Category</th>
                          <th className="text-left py-2.5 px-3 font-semibold text-xs text-green-800">Match</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {filteredMatched.map(txn => (
                          <tr key={txn.transaction_id} className="hover:bg-green-50/40">
                            <td className="py-2 px-3 text-xs">{txn.transaction_date}</td>
                            <td className="py-2 px-3 text-xs max-w-[200px] truncate" title={txn.narration}>{txn.narration}</td>
                            <td className="py-2 px-3 text-xs text-right font-medium">Rs. {fmt(txn.debit_amount)}</td>
                            <td className="py-2 px-3 text-xs max-w-[200px] truncate">{txn.matched_expense?.description}</td>
                            <td className="py-2 px-3 text-xs"><Badge variant="outline" className="text-xs">{txn.matched_expense?.expense_type}</Badge></td>
                            <td className="py-2 px-3 text-xs"><Badge className="text-xs bg-green-100 text-green-800">{txn.match_method === "exact_date_amount" ? "Exact" : "Fuzzy"}</Badge></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </TabsContent>

              {/* Added */}
              <TabsContent value="added">
                {added.length === 0 ? (
                  <div className="text-center py-8 text-gray-400 text-sm">No expenses added yet</div>
                ) : (
                  <div className="overflow-x-auto border rounded-lg">
                    <table className="w-full text-sm">
                      <thead className="bg-purple-50">
                        <tr>
                          <th className="text-left py-2.5 px-3 font-semibold text-xs text-purple-800">Date</th>
                          <th className="text-left py-2.5 px-3 font-semibold text-xs text-purple-800">Narration</th>
                          <th className="text-right py-2.5 px-3 font-semibold text-xs text-purple-800">Amount</th>
                          <th className="text-left py-2.5 px-3 font-semibold text-xs text-purple-800">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {added.map(txn => (
                          <tr key={txn.transaction_id} className="hover:bg-purple-50/40">
                            <td className="py-2 px-3 text-xs">{txn.transaction_date}</td>
                            <td className="py-2 px-3 text-xs max-w-[300px] truncate">{txn.narration}</td>
                            <td className="py-2 px-3 text-xs text-right font-medium">Rs. {fmt(txn.debit_amount)}</td>
                            <td className="py-2 px-3"><Badge className="text-xs bg-purple-100 text-purple-800">Added as Expense</Badge></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </TabsContent>

              {/* Ignored */}
              <TabsContent value="ignored">
                {ignored.length === 0 ? (
                  <div className="text-center py-8 text-gray-400 text-sm">No ignored transactions</div>
                ) : (
                  <div className="overflow-x-auto border rounded-lg">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="text-left py-2.5 px-3 font-semibold text-xs">Date</th>
                          <th className="text-left py-2.5 px-3 font-semibold text-xs">Narration</th>
                          <th className="text-right py-2.5 px-3 font-semibold text-xs">Amount</th>
                          <th className="text-left py-2.5 px-3 font-semibold text-xs">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {ignored.map(txn => (
                          <tr key={txn.transaction_id} className="hover:bg-gray-50/40 opacity-60">
                            <td className="py-2 px-3 text-xs">{txn.transaction_date}</td>
                            <td className="py-2 px-3 text-xs max-w-[300px] truncate">{txn.narration}</td>
                            <td className="py-2 px-3 text-xs text-right">{fmt(txn.debit_amount)}</td>
                            <td className="py-2 px-3"><Badge variant="secondary" className="text-xs">Ignored</Badge></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function SummaryCard({ icon, label, value, sub, color }) {
  const bgMap = { blue: "bg-blue-50", green: "bg-green-50", amber: "bg-amber-50", purple: "bg-purple-50", gray: "bg-gray-50" };
  return (
    <div className={`${bgMap[color] || "bg-gray-50"} rounded-xl p-3.5 border`} data-testid={`summary-${color}`}>
      <div className="flex items-center gap-2 mb-1">{icon}<span className="text-xs font-medium text-gray-500">{label}</span></div>
      <div className="text-sm font-bold text-gray-900">{value}</div>
      <div className="text-xs text-gray-400">{sub}</div>
    </div>
  );
}
