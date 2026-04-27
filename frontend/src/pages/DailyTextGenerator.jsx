import { useState, useEffect } from "react";
import { useAuth } from "@/App";
import { api, fetchCentersFromDB, isAdminUser } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Loader2, RefreshCw, Copy, FileText, MessageSquare, Check, CalendarRange, CalendarDays,
} from "lucide-react";

// =======================================
// DAILY TAB
// =======================================
function DailyTab({ session, centersList, isAdmin, isFranchiseOwner, canEdit }) {
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [selectedCenter, setSelectedCenter] = useState(session?.center || "");
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split("T")[0]);
  const [textData, setTextData] = useState(null);
  const [editableData, setEditableData] = useState({});
  const [generatedText, setGeneratedText] = useState("");

  const generateText = async () => {
    if (!selectedCenter) { toast.error("Select a center"); return; }
    setLoading(true);
    setCopied(false);
    try {
      const overrides = Object.keys(editableData).length > 0 ? editableData : undefined;
      const res = await api.post("/daily-text/generate", {
        token: session.token, center: selectedCenter, date: selectedDate, overrides,
      });
      setTextData(res.data);
      setEditableData(res.data.data || {});
      setGeneratedText(res.data.text || "");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to generate text");
    } finally { setLoading(false); }
  };

  const refreshFromData = async () => {
    if (!selectedCenter) { toast.error("Select a center"); return; }
    setLoading(true); setCopied(false);
    try {
      const res = await api.post("/daily-text/generate", {
        token: session.token, center: selectedCenter, date: selectedDate,
      });
      setTextData(res.data);
      setEditableData(res.data.data || {});
      setGeneratedText(res.data.text || "");
      toast.success("Refreshed from stored data");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to refresh");
    } finally { setLoading(false); }
  };

  const regenerateFromEdits = () => {
    const d = editableData;
    const fmt = (v) => `${Math.round(Number(v) || 0)}/-`;
    const dt = selectedDate.split("-");
    const displayDate = dt.length === 3 ? `${dt[2]}/${dt[1]}/${dt[0]}` : selectedDate;
    const lines = [
      "Jai Hind Namskar 🙏", "",
      `Date ${displayDate}`, "",
      `1. Opening Bal = ${fmt(d.opening_balance)}`,
      `2. Deposit = ${fmt(d.deposit)}`,
      `3. Withdrawl = ${fmt(d.withdrawal)}`,
      `4. Total Sale = ${fmt(d.total_sale)}`,
      `5. Card = ${fmt(d.card)}`,
      `6. Phone Pay = ${fmt(d.phone_pay)}`,
      `7. SWIGGY = ${fmt(d.swiggy)}`,
      `8. ZOMATO = ${fmt(d.zomato)}`,
      `9. Due Amount = ${fmt(d.due_amount)}`,
      `10. Cash sale = ${fmt(d.cash_sale)}`,
      `11. Online Expense = ${fmt(d.online_expense)}`,
      `12. Cash Expense = ${fmt(d.cash_expense)}`,
      `13. Cash In Hand = ${fmt(d.cash_in_hand)}`,
      `14. Bal. Petty cash = ${fmt(d.petty_cash_balance)}`,
      `15. Total No. of guest = ${Math.round(Number(d.total_guests) || 0)}`,
      `16. APC = ${Math.round(Number(d.apc) || 0)}`,
      `17. No. Of Drinks = ${Math.round(Number(d.num_drinks) || 0)}`,
      `18. No of sides sold = ${Math.round(Number(d.num_sides) || 0)}`,
      `    Cancelled Zomato Order = ${Math.round(Number(d.cancelled_zomato) || 0)}`,
      `19. Cancelled Swiggy Order = ${Math.round(Number(d.cancelled_swiggy) || 0)}`,
    ];
    setGeneratedText(lines.join("\n"));
  };

  useEffect(() => {
    if (Object.keys(editableData).length > 0) regenerateFromEdits();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editableData]);

  const copyText = () => {
    navigator.clipboard.writeText(generatedText).then(() => {
      setCopied(true);
      toast.success("Copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const updateField = (key, value) => setEditableData(p => ({ ...p, [key]: value }));

  const fields = [
    { key: "opening_balance", label: "Opening Bal" },
    { key: "deposit", label: "Deposit" },
    { key: "withdrawal", label: "Withdrawal" },
    { key: "total_sale", label: "Total Sale" },
    { key: "card", label: "Card" },
    { key: "phone_pay", label: "Phone Pay / UPI" },
    { key: "swiggy", label: "Swiggy" },
    { key: "zomato", label: "Zomato" },
    { key: "due_amount", label: "Due Amount" },
    { key: "cash_sale", label: "Cash Sale" },
    { key: "online_expense", label: "Online Expense" },
    { key: "cash_expense", label: "Cash Expense" },
    { key: "cash_in_hand", label: "Cash In Hand" },
    { key: "petty_cash_balance", label: "Petty Cash Bal" },
    { key: "total_guests", label: "Total Guests" },
    { key: "apc", label: "APC" },
    { key: "num_drinks", label: "No. of Drinks" },
    { key: "num_sides", label: "No. of Sides Sold" },
    { key: "cancelled_zomato", label: "Cancelled Zomato" },
    { key: "cancelled_swiggy", label: "Cancelled Swiggy" },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="space-y-1">
              <Label className="text-xs">Center</Label>
              <select value={selectedCenter} onChange={e => setSelectedCenter(e.target.value)}
                className="h-10 px-3 rounded-md border border-input bg-background text-sm min-w-[160px]"
                data-testid="text-center-select" disabled={!isAdmin && !isFranchiseOwner}>
                {!isAdmin && <option value={session?.center}>{session?.center}</option>}
                {isAdmin && centersList.map(c => <option key={c.code} value={c.code}>{c.code}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Date</Label>
              <Input type="date" value={selectedDate} onChange={e => setSelectedDate(e.target.value)}
                className="w-[160px]" data-testid="text-date" />
            </div>
            <Button onClick={generateText} disabled={loading} data-testid="generate-btn">
              {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileText className="w-4 h-4 mr-2" />}
              Generate Text
            </Button>
            <Button onClick={refreshFromData} variant="outline" disabled={loading}>
              <RefreshCw className="w-4 h-4 mr-2" /> Refresh from Data
            </Button>
            {generatedText && (
              <Button onClick={copyText} variant={copied ? "default" : "outline"}
                className={copied ? "bg-green-600 hover:bg-green-700" : "border-green-500 text-green-600"}
                data-testid="copy-btn">
                {copied ? <Check className="w-4 h-4 mr-2" /> : <Copy className="w-4 h-4 mr-2" />}
                {copied ? "Copied!" : "Copy Text"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {textData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {canEdit && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2"><MessageSquare className="w-4 h-4" /> Edit Values</CardTitle>
                <CardDescription className="text-xs">
                  {textData.has_sales_data ? (
                    <Badge className="bg-green-100 text-green-800">Auto-filled from sales data</Badge>
                  ) : (
                    <Badge className="bg-amber-100 text-amber-800">No sales data — enter manually</Badge>
                  )}
                  {textData.expense_count > 0 && (
                    <Badge className="bg-blue-100 text-blue-800 ml-2">{textData.expense_count} expenses found</Badge>
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-2">
                  {fields.map(f => (
                    <div key={f.key} className="flex items-center gap-2">
                      <Label className="text-[11px] w-28 text-right text-muted-foreground shrink-0">{f.label}</Label>
                      <Input type="number" value={editableData[f.key] ?? ""} className="h-8 text-xs"
                        onChange={e => updateField(f.key, parseFloat(e.target.value) || 0)}
                        data-testid={`field-${f.key}`} />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
          <Card className="border-2 border-green-300">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2 text-green-700">
                <MessageSquare className="w-4 h-4" /> WhatsApp Preview
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="whitespace-pre-wrap text-sm bg-green-50 p-4 rounded-lg font-mono leading-relaxed border"
                data-testid="text-preview">{generatedText}</pre>
              <Button onClick={copyText} className="mt-3 w-full" variant={copied ? "default" : "outline"}
                data-testid="copy-btn-bottom">
                {copied ? <Check className="w-4 h-4 mr-2" /> : <Copy className="w-4 h-4 mr-2" />}
                {copied ? "Copied to Clipboard!" : "Copy to Clipboard"}
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// =======================================
// WEEKLY TAB
// =======================================
function WeeklyTab({ session, centersList, isAdmin, isFranchiseOwner, canEdit }) {
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [selectedCenter, setSelectedCenter] = useState(session?.center || "");
  // Default to current Monday
  const today = new Date();
  const day = today.getDay() || 7; // Sun=0 -> 7
  const monday = new Date(today);
  monday.setDate(today.getDate() - (day - 1));
  const [weekDate, setWeekDate] = useState(monday.toISOString().split("T")[0]);

  const [textData, setTextData] = useState(null);
  const [editableData, setEditableData] = useState({});
  const [editableCategories, setEditableCategories] = useState([]);
  const [generatedText, setGeneratedText] = useState("");

  const generate = async () => {
    if (!selectedCenter) { toast.error("Select a center"); return; }
    setLoading(true); setCopied(false);
    try {
      const res = await api.post("/daily-text/generate-weekly", {
        token: session.token, center: selectedCenter, week_date: weekDate,
      });
      setTextData(res.data);
      setEditableData(res.data.data || {});
      setEditableCategories(res.data.data?.expense_categories || []);
      setGeneratedText(res.data.text || "");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to generate weekly text");
    } finally { setLoading(false); }
  };

  const refresh = async () => {
    if (!selectedCenter) { toast.error("Select a center"); return; }
    setLoading(true); setCopied(false);
    try {
      const res = await api.post("/daily-text/generate-weekly", {
        token: session.token, center: selectedCenter, week_date: weekDate,
      });
      setTextData(res.data);
      setEditableData(res.data.data || {});
      setEditableCategories(res.data.data?.expense_categories || []);
      setGeneratedText(res.data.text || "");
      toast.success("Refreshed from stored data");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to refresh");
    } finally { setLoading(false); }
  };

  // Regenerate locally from edits (mirror of backend formatter)
  const regenerate = () => {
    const d = { ...editableData, expense_categories: editableCategories };
    const fmt = (v) => `${Math.round(Number(v) || 0)}/-`;
    const ord = (n) => {
      if (n >= 11 && n <= 13) return `${n}th`;
      const last = n % 10;
      return `${n}${last === 1 ? "st" : last === 2 ? "nd" : last === 3 ? "rd" : "th"}`;
    };
    const monthNames = ["January","February","March","April","May","June","July","August","September","October","November","December"];
    let rangeStr = `${d.week_start} to ${d.week_end}`;
    try {
      const ws = new Date(d.week_start + "T00:00:00");
      const we = new Date(d.week_end + "T00:00:00");
      rangeStr = `${ord(ws.getDate())} ${monthNames[ws.getMonth()]} ${ws.getFullYear()} to ${ord(we.getDate())} ${monthNames[we.getMonth()]} ${we.getFullYear()}`;
    } catch { /* keep fallback */ }

    const lines = [
      "Jai Hind Namskar 🙏", "",
      rangeStr, "",
      `↪️ Total Sale = ${fmt(d.total_sale)}`,
      `↪️ Total Card = ${fmt(d.total_card)}`,
      `↪️ Total Deposit = ${fmt(d.total_deposit)}`,
      `↪️ Total Withdrawl = ${fmt(d.total_withdrawal)}`,
      "",
      "DESCRIPTION Expenses",
    ];
    const letters = "abcdefghij";
    if ((d.expense_categories || []).length > 0) {
      d.expense_categories.forEach((c, i) => {
        const letter = i < letters.length ? letters[i] : `${i + 1}`;
        lines.push(`${letter}) ${c.name} = ${fmt(c.amount)}`);
      });
    } else {
      lines.push("(No expenses recorded)");
    }
    lines.push("",
      `↪️ Total Swiggy = ${fmt(d.total_swiggy)}`,
      `↪️ Total Zomato = ${fmt(d.total_zomato)}`,
    );
    if (d.is_international) lines.push(`↪️ Total Doordash = ${fmt(d.total_doordash)}`);
    lines.push(
      `↪️ Total Paytm = ${fmt(d.total_paytm)}`,
      `↪️ Total Bharat Pay = ${fmt(d.total_bharat_pay)}`,
      `↪️ Total Cash Sale = ${fmt(d.total_cash_sale)}`,
      `↪️ Total Cash Expenses = ${fmt(d.total_cash_expenses)}`,
      `↪️ Total Cash In Hand = ${fmt(d.total_cash_in_hand)}`,
      `↪️ Total Online Expenses = ${fmt(d.total_online_expenses)}`,
      `↪️ APC = ${Math.round(Number(d.apc) || 0)}`,
      `↪️ Total No. Of Guest = ${Math.round(Number(d.total_guests) || 0)}`,
    );
    setGeneratedText(lines.join("\n"));
  };

  useEffect(() => {
    if (Object.keys(editableData).length > 0) regenerate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editableData, editableCategories]);

  const copyText = () => {
    navigator.clipboard.writeText(generatedText).then(() => {
      setCopied(true);
      toast.success("Copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const updateField = (key, value) => setEditableData(p => ({ ...p, [key]: value }));
  const updateCategory = (idx, key, value) => {
    setEditableCategories(prev => prev.map((c, i) => i === idx ? { ...c, [key]: key === "amount" ? (parseFloat(value) || 0) : value } : c));
  };
  const addCategory = () => setEditableCategories(p => [...p, { name: "New", amount: 0 }]);
  const removeCategory = (idx) => setEditableCategories(p => p.filter((_, i) => i !== idx));

  const editFields = [
    { key: "total_sale", label: "Total Sale" },
    { key: "total_card", label: "Total Card" },
    { key: "total_deposit", label: "Total Deposit" },
    { key: "total_withdrawal", label: "Total Withdrawl" },
    { key: "total_swiggy", label: "Total Swiggy" },
    { key: "total_zomato", label: "Total Zomato" },
    { key: "total_doordash", label: "Total Doordash" },
    { key: "total_paytm", label: "Total Paytm" },
    { key: "total_bharat_pay", label: "Total Bharat Pay" },
    { key: "total_cash_sale", label: "Total Cash Sale" },
    { key: "total_cash_expenses", label: "Total Cash Expenses" },
    { key: "total_online_expenses", label: "Total Online Expenses" },
    { key: "total_cash_in_hand", label: "Total Cash In Hand" },
    { key: "total_guests", label: "Total No. Of Guest" },
    { key: "apc", label: "APC" },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="space-y-1">
              <Label className="text-xs">Center</Label>
              <select value={selectedCenter} onChange={e => setSelectedCenter(e.target.value)}
                className="h-10 px-3 rounded-md border border-input bg-background text-sm min-w-[160px]"
                data-testid="weekly-center-select" disabled={!isAdmin && !isFranchiseOwner}>
                {!isAdmin && <option value={session?.center}>{session?.center}</option>}
                {isAdmin && centersList.map(c => <option key={c.code} value={c.code}>{c.code}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Pick any date in the week (Mon-Sun snap)</Label>
              <Input type="date" value={weekDate} onChange={e => setWeekDate(e.target.value)}
                className="w-[180px]" data-testid="weekly-date" />
            </div>
            <Button onClick={generate} disabled={loading} data-testid="weekly-generate-btn">
              {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CalendarRange className="w-4 h-4 mr-2" />}
              Generate Weekly Text
            </Button>
            <Button onClick={refresh} variant="outline" disabled={loading} data-testid="weekly-refresh-btn">
              <RefreshCw className="w-4 h-4 mr-2" /> Refresh from Data
            </Button>
            {generatedText && (
              <Button onClick={copyText} variant={copied ? "default" : "outline"}
                className={copied ? "bg-green-600 hover:bg-green-700" : "border-green-500 text-green-600"}
                data-testid="weekly-copy-btn">
                {copied ? <Check className="w-4 h-4 mr-2" /> : <Copy className="w-4 h-4 mr-2" />}
                {copied ? "Copied!" : "Copy Text"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {textData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {canEdit && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2"><MessageSquare className="w-4 h-4" /> Edit Values</CardTitle>
                <CardDescription className="text-xs">
                  {textData.has_sales_data ? (
                    <Badge className="bg-green-100 text-green-800">Aggregated from {textData.sales_days} day(s)</Badge>
                  ) : (
                    <Badge className="bg-amber-100 text-amber-800">No sales data this week</Badge>
                  )}
                  {textData.expense_count > 0 && (
                    <Badge className="bg-blue-100 text-blue-800 ml-2">{textData.expense_count} expenses</Badge>
                  )}
                  {textData.is_international && (
                    <Badge className="bg-purple-100 text-purple-800 ml-2">International (DoorDash shown)</Badge>
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-2">
                  {editFields
                    .filter(f => f.key !== "total_doordash" || textData.is_international)
                    .map(f => (
                      <div key={f.key} className="flex items-center gap-2">
                        <Label className="text-[11px] w-32 text-right text-muted-foreground shrink-0">{f.label}</Label>
                        <Input type="number" value={editableData[f.key] ?? ""} className="h-8 text-xs"
                          onChange={e => updateField(f.key, parseFloat(e.target.value) || 0)}
                          data-testid={`weekly-field-${f.key}`} />
                      </div>
                    ))}
                </div>
                {/* Editable expense categories */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-xs font-medium">Expense Categories (Description Expenses)</Label>
                    <Button size="sm" variant="outline" className="h-7 text-xs" onClick={addCategory} data-testid="weekly-add-cat-btn">
                      + Add
                    </Button>
                  </div>
                  <div className="space-y-1.5">
                    {editableCategories.length === 0 && (
                      <p className="text-xs text-muted-foreground italic">No expense categories</p>
                    )}
                    {editableCategories.map((c, idx) => (
                      <div key={idx} className="flex items-center gap-2" data-testid={`weekly-cat-row-${idx}`}>
                        <span className="text-xs text-muted-foreground w-4">{String.fromCharCode(97 + idx)})</span>
                        <Input value={c.name} className="h-8 text-xs flex-1"
                          onChange={e => updateCategory(idx, "name", e.target.value)} />
                        <Input type="number" value={c.amount} className="h-8 text-xs w-28"
                          onChange={e => updateCategory(idx, "amount", e.target.value)} />
                        <Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-red-500"
                          onClick={() => removeCategory(idx)} data-testid={`weekly-cat-remove-${idx}`}>×</Button>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
          <Card className="border-2 border-green-300">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2 text-green-700">
                <MessageSquare className="w-4 h-4" /> WhatsApp Preview
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="whitespace-pre-wrap text-sm bg-green-50 p-4 rounded-lg font-mono leading-relaxed border"
                data-testid="weekly-text-preview">{generatedText}</pre>
              <Button onClick={copyText} className="mt-3 w-full" variant={copied ? "default" : "outline"}
                data-testid="weekly-copy-btn-bottom">
                {copied ? <Check className="w-4 h-4 mr-2" /> : <Copy className="w-4 h-4 mr-2" />}
                {copied ? "Copied to Clipboard!" : "Copy to Clipboard"}
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// =======================================
// MONTHLY TAB
// =======================================
function MonthlyTab({ session, centersList, isAdmin, isFranchiseOwner, canEdit }) {
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [selectedCenter, setSelectedCenter] = useState(session?.center || "");
  // Default to current month
  const today = new Date();
  const ym = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
  const [monthValue, setMonthValue] = useState(ym);

  const [textData, setTextData] = useState(null);
  const [editableData, setEditableData] = useState({});
  const [editableCategories, setEditableCategories] = useState([]);
  const [generatedText, setGeneratedText] = useState("");

  const generate = async () => {
    if (!selectedCenter) { toast.error("Select a center"); return; }
    if (!monthValue) { toast.error("Pick a month"); return; }
    setLoading(true); setCopied(false);
    try {
      const res = await api.post("/daily-text/generate-monthly", {
        token: session.token, center: selectedCenter, month: monthValue,
      });
      setTextData(res.data);
      setEditableData(res.data.data || {});
      setEditableCategories(res.data.data?.expense_categories || []);
      setGeneratedText(res.data.text || "");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to generate monthly text");
    } finally { setLoading(false); }
  };

  const refresh = async () => {
    if (!selectedCenter) { toast.error("Select a center"); return; }
    setLoading(true); setCopied(false);
    try {
      const res = await api.post("/daily-text/generate-monthly", {
        token: session.token, center: selectedCenter, month: monthValue,
      });
      setTextData(res.data);
      setEditableData(res.data.data || {});
      setEditableCategories(res.data.data?.expense_categories || []);
      setGeneratedText(res.data.text || "");
      toast.success("Refreshed from stored data");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to refresh");
    } finally { setLoading(false); }
  };

  const regenerate = () => {
    const d = { ...editableData, expense_categories: editableCategories };
    const fmt = (v) => `${Math.round(Number(v) || 0)}/-`;
    const monthNames = ["January","February","March","April","May","June","July","August","September","October","November","December"];
    let rangeStr = `${d.month || monthValue} (Monthly Summary)`;
    try {
      if (d.month_start) {
        const ms = new Date(d.month_start + "T00:00:00");
        rangeStr = `${monthNames[ms.getMonth()]} ${ms.getFullYear()} (Monthly Summary)`;
      }
    } catch { /* keep fallback */ }

    const lines = [
      "Jai Hind Namskar 🙏", "",
      rangeStr, "",
      `↪️ Total Sale = ${fmt(d.total_sale)}`,
      `↪️ Total Card = ${fmt(d.total_card)}`,
      `↪️ Total Deposit = ${fmt(d.total_deposit)}`,
      `↪️ Total Withdrawl = ${fmt(d.total_withdrawal)}`,
      "",
      "DESCRIPTION Expenses",
    ];
    const letters = "abcdefghij";
    if ((d.expense_categories || []).length > 0) {
      d.expense_categories.forEach((c, i) => {
        const letter = i < letters.length ? letters[i] : `${i + 1}`;
        lines.push(`${letter}) ${c.name} = ${fmt(c.amount)}`);
      });
    } else {
      lines.push("(No expenses recorded)");
    }
    lines.push("",
      `↪️ Total Swiggy = ${fmt(d.total_swiggy)}`,
      `↪️ Total Zomato = ${fmt(d.total_zomato)}`,
    );
    if (d.is_international) lines.push(`↪️ Total Doordash = ${fmt(d.total_doordash)}`);
    lines.push(
      `↪️ Total Paytm = ${fmt(d.total_paytm)}`,
      `↪️ Total Bharat Pay = ${fmt(d.total_bharat_pay)}`,
      `↪️ Total Cash Sale = ${fmt(d.total_cash_sale)}`,
      `↪️ Total Cash Expenses = ${fmt(d.total_cash_expenses)}`,
      `↪️ Total Cash In Hand = ${fmt(d.total_cash_in_hand)}`,
      `↪️ Total Online Expenses = ${fmt(d.total_online_expenses)}`,
      `↪️ APC = ${Math.round(Number(d.apc) || 0)}`,
      `↪️ Total No. Of Guest = ${Math.round(Number(d.total_guests) || 0)}`,
    );
    setGeneratedText(lines.join("\n"));
  };

  useEffect(() => {
    if (Object.keys(editableData).length > 0) regenerate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editableData, editableCategories]);

  const copyText = () => {
    navigator.clipboard.writeText(generatedText).then(() => {
      setCopied(true);
      toast.success("Copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const updateField = (key, value) => setEditableData(p => ({ ...p, [key]: value }));
  const updateCategory = (idx, key, value) => {
    setEditableCategories(prev => prev.map((c, i) => i === idx ? { ...c, [key]: key === "amount" ? (parseFloat(value) || 0) : value } : c));
  };
  const addCategory = () => setEditableCategories(p => [...p, { name: "New", amount: 0 }]);
  const removeCategory = (idx) => setEditableCategories(p => p.filter((_, i) => i !== idx));

  const editFields = [
    { key: "total_sale", label: "Total Sale" },
    { key: "total_card", label: "Total Card" },
    { key: "total_deposit", label: "Total Deposit" },
    { key: "total_withdrawal", label: "Total Withdrawl" },
    { key: "total_swiggy", label: "Total Swiggy" },
    { key: "total_zomato", label: "Total Zomato" },
    { key: "total_doordash", label: "Total Doordash" },
    { key: "total_paytm", label: "Total Paytm" },
    { key: "total_bharat_pay", label: "Total Bharat Pay" },
    { key: "total_cash_sale", label: "Total Cash Sale" },
    { key: "total_cash_expenses", label: "Total Cash Expenses" },
    { key: "total_online_expenses", label: "Total Online Expenses" },
    { key: "total_cash_in_hand", label: "Total Cash In Hand" },
    { key: "total_guests", label: "Total No. Of Guest" },
    { key: "apc", label: "APC" },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="space-y-1">
              <Label className="text-xs">Center</Label>
              <select value={selectedCenter} onChange={e => setSelectedCenter(e.target.value)}
                className="h-10 px-3 rounded-md border border-input bg-background text-sm min-w-[160px]"
                data-testid="monthly-center-select" disabled={!isAdmin && !isFranchiseOwner}>
                {!isAdmin && <option value={session?.center}>{session?.center}</option>}
                {isAdmin && centersList.map(c => <option key={c.code} value={c.code}>{c.code}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Month</Label>
              <Input type="month" value={monthValue} onChange={e => setMonthValue(e.target.value)}
                className="w-[180px]" data-testid="monthly-date" />
            </div>
            <Button onClick={generate} disabled={loading} data-testid="monthly-generate-btn">
              {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CalendarDays className="w-4 h-4 mr-2" />}
              Generate Monthly Text
            </Button>
            <Button onClick={refresh} variant="outline" disabled={loading} data-testid="monthly-refresh-btn">
              <RefreshCw className="w-4 h-4 mr-2" /> Refresh from Data
            </Button>
            {generatedText && (
              <Button onClick={copyText} variant={copied ? "default" : "outline"}
                className={copied ? "bg-green-600 hover:bg-green-700" : "border-green-500 text-green-600"}
                data-testid="monthly-copy-btn">
                {copied ? <Check className="w-4 h-4 mr-2" /> : <Copy className="w-4 h-4 mr-2" />}
                {copied ? "Copied!" : "Copy Text"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {textData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {canEdit && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2"><MessageSquare className="w-4 h-4" /> Edit Values</CardTitle>
                <CardDescription className="text-xs">
                  {textData.has_sales_data ? (
                    <Badge className="bg-green-100 text-green-800">Aggregated from {textData.sales_days} day(s)</Badge>
                  ) : (
                    <Badge className="bg-amber-100 text-amber-800">No sales data this month</Badge>
                  )}
                  {textData.expense_count > 0 && (
                    <Badge className="bg-blue-100 text-blue-800 ml-2">{textData.expense_count} expenses</Badge>
                  )}
                  {textData.is_international && (
                    <Badge className="bg-purple-100 text-purple-800 ml-2">International (DoorDash shown)</Badge>
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-2">
                  {editFields
                    .filter(f => f.key !== "total_doordash" || textData.is_international)
                    .map(f => (
                      <div key={f.key} className="flex items-center gap-2">
                        <Label className="text-[11px] w-32 text-right text-muted-foreground shrink-0">{f.label}</Label>
                        <Input type="number" value={editableData[f.key] ?? ""} className="h-8 text-xs"
                          onChange={e => updateField(f.key, parseFloat(e.target.value) || 0)}
                          data-testid={`monthly-field-${f.key}`} />
                      </div>
                    ))}
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-xs font-medium">Expense Categories (Description Expenses)</Label>
                    <Button size="sm" variant="outline" className="h-7 text-xs" onClick={addCategory} data-testid="monthly-add-cat-btn">
                      + Add
                    </Button>
                  </div>
                  <div className="space-y-1.5">
                    {editableCategories.length === 0 && (
                      <p className="text-xs text-muted-foreground italic">No expense categories</p>
                    )}
                    {editableCategories.map((c, idx) => (
                      <div key={idx} className="flex items-center gap-2" data-testid={`monthly-cat-row-${idx}`}>
                        <span className="text-xs text-muted-foreground w-4">{String.fromCharCode(97 + idx)})</span>
                        <Input value={c.name} className="h-8 text-xs flex-1"
                          onChange={e => updateCategory(idx, "name", e.target.value)} />
                        <Input type="number" value={c.amount} className="h-8 text-xs w-28"
                          onChange={e => updateCategory(idx, "amount", e.target.value)} />
                        <Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-red-500"
                          onClick={() => removeCategory(idx)} data-testid={`monthly-cat-remove-${idx}`}>×</Button>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
          <Card className="border-2 border-green-300">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2 text-green-700">
                <MessageSquare className="w-4 h-4" /> WhatsApp Preview
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="whitespace-pre-wrap text-sm bg-green-50 p-4 rounded-lg font-mono leading-relaxed border"
                data-testid="monthly-text-preview">{generatedText}</pre>
              <Button onClick={copyText} className="mt-3 w-full" variant={copied ? "default" : "outline"}
                data-testid="monthly-copy-btn-bottom">
                {copied ? <Check className="w-4 h-4 mr-2" /> : <Copy className="w-4 h-4 mr-2" />}
                {copied ? "Copied to Clipboard!" : "Copy to Clipboard"}
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// =======================================
// PAGE
// =======================================
export default function DailyTextGenerator() {
  const { session } = useAuth();
  const isAdmin = isAdminUser(session);
  const [centersList, setCentersList] = useState([]);
  const isFranchiseOwner = session?.role_key === "franchise_owner";
  const canEdit = isAdmin || !isFranchiseOwner;

  useEffect(() => {
    if (session?.token) fetchCentersFromDB(session.token).then(setCentersList);
  }, [session?.token]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-primary" data-testid="daily-text-title">Sales Text Generator</h1>
        <p className="text-muted-foreground mt-1">Generate WhatsApp-style daily or weekly sales summaries</p>
      </div>

      <Tabs defaultValue="daily" className="w-full">
        <TabsList className="grid w-full max-w-md grid-cols-3">
          <TabsTrigger value="daily" data-testid="tab-daily">
            <FileText className="w-4 h-4 mr-2" /> Daily
          </TabsTrigger>
          <TabsTrigger value="weekly" data-testid="tab-weekly">
            <CalendarRange className="w-4 h-4 mr-2" /> Weekly
          </TabsTrigger>
          <TabsTrigger value="monthly" data-testid="tab-monthly">
            <CalendarDays className="w-4 h-4 mr-2" /> Monthly
          </TabsTrigger>
        </TabsList>
        <TabsContent value="daily" className="mt-4">
          <DailyTab session={session} centersList={centersList} isAdmin={isAdmin}
            isFranchiseOwner={isFranchiseOwner} canEdit={canEdit} />
        </TabsContent>
        <TabsContent value="weekly" className="mt-4">
          <WeeklyTab session={session} centersList={centersList} isAdmin={isAdmin}
            isFranchiseOwner={isFranchiseOwner} canEdit={canEdit} />
        </TabsContent>
        <TabsContent value="monthly" className="mt-4">
          <MonthlyTab session={session} centersList={centersList} isAdmin={isAdmin}
            isFranchiseOwner={isFranchiseOwner} canEdit={canEdit} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
