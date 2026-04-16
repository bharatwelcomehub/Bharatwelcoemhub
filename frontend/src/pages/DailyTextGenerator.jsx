import { useState, useEffect } from "react";
import { useAuth } from "@/App";
import { api, fetchCentersFromDB, isAdminUser } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Loader2, RefreshCw, Copy, FileText, MessageSquare, Check,
} from "lucide-react";

export default function DailyTextGenerator() {
  const { session } = useAuth();
  const isAdmin = isAdminUser(session);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [centersList, setCentersList] = useState([]);
  const [selectedCenter, setSelectedCenter] = useState(session?.center || "");
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split("T")[0]);
  const [textData, setTextData] = useState(null);
  const [editableData, setEditableData] = useState({});
  const [generatedText, setGeneratedText] = useState("");

  const isFranchiseOwner = session?.role_key === "franchise_owner";
  const canEdit = isAdmin || !isFranchiseOwner;

  useEffect(() => {
    if (session?.token) {
      fetchCentersFromDB(session.token).then(setCentersList);
    }
  }, [session?.token]);

  const generateText = async () => {
    if (!selectedCenter) { toast.error("Select a center"); return; }
    setLoading(true);
    setCopied(false);
    try {
      const overrides = Object.keys(editableData).length > 0 ? editableData : undefined;
      const res = await api.post("/daily-text/generate", {
        token: session.token, center: selectedCenter, date: selectedDate,
        overrides,
      });
      setTextData(res.data);
      setEditableData(res.data.data || {});
      setGeneratedText(res.data.text || "");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to generate text");
    } finally {
      setLoading(false);
    }
  };

  const refreshFromData = async () => {
    if (!selectedCenter) { toast.error("Select a center"); return; }
    setLoading(true);
    setCopied(false);
    try {
      // Force fresh pull from DB by NOT sending overrides
      const res = await api.post("/daily-text/generate", {
        token: session.token, center: selectedCenter, date: selectedDate,
      });
      setTextData(res.data);
      setEditableData(res.data.data || {});
      setGeneratedText(res.data.text || "");
      toast.success("Refreshed from stored data");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to refresh");
    } finally {
      setLoading(false);
    }
  };

  // Regenerate text from editable data
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
  }, [editableData]);

  const copyText = () => {
    navigator.clipboard.writeText(generatedText).then(() => {
      setCopied(true);
      toast.success("Copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const updateField = (key, value) => {
    setEditableData(prev => ({ ...prev, [key]: value }));
  };

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
      <div>
        <h1 className="text-3xl font-bold text-primary" data-testid="daily-text-title">Daily Text Generator</h1>
        <p className="text-muted-foreground mt-1">Generate WhatsApp-style daily sales summary</p>
      </div>

      {/* Controls */}
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
          {/* Editable Fields */}
          {canEdit && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <MessageSquare className="w-4 h-4" /> Edit Values
                </CardTitle>
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

          {/* Generated Text Preview */}
          <Card className="border-2 border-green-300">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2 text-green-700">
                <MessageSquare className="w-4 h-4" /> WhatsApp Preview
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="whitespace-pre-wrap text-sm bg-green-50 p-4 rounded-lg font-mono leading-relaxed border"
                data-testid="text-preview">
                {generatedText}
              </pre>
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
