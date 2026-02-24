import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Save, Calculator, Calendar, RefreshCw, ChevronLeft, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";

// Format currency for display
const formatNum = (num) => {
  if (num === null || num === undefined || isNaN(num)) return "0.00";
  return num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

// Get today's date in YYYY-MM-DD format
const getTodayStr = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
};

export default function SalesDataEntry({ session, selectedCenter }) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedDate, setSelectedDate] = useState(getTodayStr());
  const [existingRecord, setExistingRecord] = useState(null);
  
  // Form state - EDITABLE fields (white background)
  const [formData, setFormData] = useState({
    opening_balance: 0,
    petty_cash_opening: 0,
    deposited_in_bank: 0,
    cash_receipts: 0,
    sale_pbm: 0,
    sale_other: 0,
    card_idfc: 0,
    bharat_pay: 0,
    swiggy: 0,
    zomato: 0,
    online_other: 0,
    due_amount: 0,
    notes: ""
  });

  // Get center code
  const centerCode = selectedCenter || session?.center;

  // CALCULATED fields (gray background - auto-computed)
  const calculated = useMemo(() => {
    const total_sale = (parseFloat(formData.sale_pbm) || 0) + (parseFloat(formData.sale_other) || 0);
    const total_online_sale = (
      (parseFloat(formData.card_idfc) || 0) +
      (parseFloat(formData.bharat_pay) || 0) +
      (parseFloat(formData.swiggy) || 0) +
      (parseFloat(formData.zomato) || 0) +
      (parseFloat(formData.online_other) || 0)
    );
    const total_cash_sale = total_sale - total_online_sale;
    
    // Cash expense would come from expenses entered separately
    const cash_expense = existingRecord?.cash_expense || 0;
    
    const closing_balance = (
      (parseFloat(formData.opening_balance) || 0) +
      total_cash_sale +
      (parseFloat(formData.cash_receipts) || 0) -
      (parseFloat(formData.deposited_in_bank) || 0) -
      cash_expense
    );
    
    const petty_cash_closing = (
      (parseFloat(formData.petty_cash_opening) || 0) +
      (parseFloat(formData.cash_receipts) || 0) -
      cash_expense
    );
    
    const to_deposit_in_bank = closing_balance - petty_cash_closing;
    const difference_for_day = closing_balance - (existingRecord?.expected_balance || closing_balance);
    
    return {
      total_sale,
      total_online_sale,
      total_cash_sale,
      cash_expense,
      closing_balance,
      petty_cash_closing,
      to_deposit_in_bank,
      difference_for_day
    };
  }, [formData, existingRecord]);

  // Fetch existing record for selected date
  const fetchRecord = async () => {
    if (!selectedDate || !centerCode) return;
    
    setLoading(true);
    try {
      const res = await api.post("/sales/daily", {
        token: session?.token,
        center: centerCode,
        start_date: selectedDate,
        end_date: selectedDate
      });
      
      if (res.data.sales && res.data.sales.length > 0) {
        const record = res.data.sales[0];
        setExistingRecord(record);
        setFormData({
          opening_balance: record.opening_balance || 0,
          petty_cash_opening: record.petty_cash_opening || 0,
          deposited_in_bank: record.deposited_in_bank || 0,
          cash_receipts: record.cash_receipts || 0,
          sale_pbm: record.sale_pbm || 0,
          sale_other: record.sale_other || 0,
          card_idfc: record.card_idfc || 0,
          bharat_pay: record.bharat_pay || 0,
          swiggy: record.swiggy || 0,
          zomato: record.zomato || 0,
          online_other: record.online_other || 0,
          due_amount: record.due_amount || 0,
          notes: record.notes || ""
        });
      } else {
        setExistingRecord(null);
        // Try to get previous day's closing balance as opening
        const prevDate = new Date(selectedDate);
        prevDate.setDate(prevDate.getDate() - 1);
        const prevDateStr = prevDate.toISOString().split('T')[0];
        
        const prevRes = await api.post("/sales/daily", {
          token: session?.token,
          center: centerCode,
          start_date: prevDateStr,
          end_date: prevDateStr
        });
        
        const prevOpeningBal = prevRes.data.sales?.[0]?.closing_balance || 0;
        const prevPettyCash = prevRes.data.sales?.[0]?.petty_cash_closing || 0;
        
        setFormData({
          opening_balance: prevOpeningBal,
          petty_cash_opening: prevPettyCash,
          deposited_in_bank: 0,
          cash_receipts: 0,
          sale_pbm: 0,
          sale_other: 0,
          card_idfc: 0,
          bharat_pay: 0,
          swiggy: 0,
          zomato: 0,
          online_other: 0,
          due_amount: 0,
          notes: ""
        });
      }
    } catch (err) {
      console.error("Failed to fetch record:", err);
      toast.error("Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecord();
  }, [selectedDate, centerCode, session?.token]);

  // Handle form field change - using functional update to avoid stale closure
  const handleChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Save record
  const handleSave = async () => {
    if (!centerCode) {
      toast.error("Please select a center");
      return;
    }
    
    setSaving(true);
    try {
      const payload = {
        center: centerCode,
        date: selectedDate,
        ...formData,
        total_sale: calculated.total_sale,
        total_online_sale: calculated.total_online_sale,
        total_cash_sale: calculated.total_cash_sale,
        closing_balance: calculated.closing_balance,
        petty_cash_closing: calculated.petty_cash_closing,
        to_deposit_in_bank: calculated.to_deposit_in_bank,
        difference_for_day: calculated.difference_for_day
      };
      
      if (existingRecord) {
        // Update existing
        await api.put(`/sales/daily/${centerCode}/${selectedDate}?token=${session?.token}`, payload);
        toast.success("Record updated successfully");
      } else {
        // Create new
        await api.post(`/sales/daily/create?token=${session?.token}`, payload);
        toast.success("Record created successfully");
      }
      
      // Refresh
      fetchRecord();
    } catch (err) {
      console.error("Save error:", err);
      toast.error(err.response?.data?.detail || "Failed to save record");
    } finally {
      setSaving(false);
    }
  };

  // Navigate dates
  const goToDate = (days) => {
    const date = new Date(selectedDate);
    date.setDate(date.getDate() + days);
    setSelectedDate(date.toISOString().split('T')[0]);
  };

  // Editable input field - using controlled input with proper number handling
  const renderEditableField = (label, field) => (
    <div className="space-y-1" key={field}>
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <div className="relative">
        <span className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">₹</span>
        <Input
          type="text"
          inputMode="decimal"
          value={formData[field] === 0 ? "" : formData[field]}
          onChange={(e) => {
            const val = e.target.value;
            // Allow empty, numbers, and decimal point
            if (val === "" || /^[0-9]*\.?[0-9]*$/.test(val)) {
              handleChange(field, val === "" ? 0 : parseFloat(val) || 0);
            }
          }}
          onBlur={(e) => {
            // Ensure it's a valid number on blur
            const val = parseFloat(e.target.value) || 0;
            handleChange(field, val);
          }}
          className="pl-6 bg-white border-input text-right"
          placeholder="0"
          data-testid={`input-${field}`}
        />
      </div>
    </div>
  );

  // Calculated field - read-only (gray)
  const renderCalculatedField = (label, value, isGreen = false) => (
    <div className="space-y-1" key={label}>
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <div className={`px-3 py-2 rounded-md text-right font-medium ${
        isGreen ? 'bg-green-100 text-green-800 border border-green-300' : 'bg-gray-100 text-gray-700 border border-gray-300'
      }`}>
        ₹ {formatNum(value)}
      </div>
    </div>
  );

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Calculator className="w-5 h-5 text-primary" />
            Daily Sales Data Entry
          </CardTitle>
          
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={() => goToDate(-1)}>
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-40"
              data-testid="date-input"
            />
            <Button variant="outline" size="icon" onClick={() => goToDate(1)}>
              <ChevronRight className="w-4 h-4" />
            </Button>
            <Button variant="outline" size="icon" onClick={fetchRecord} disabled={loading}>
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
        
        <p className="text-sm text-muted-foreground mt-2">
          Center: <span className="font-medium text-foreground">{centerCode}</span>
          {existingRecord && <span className="ml-4 text-green-600">● Record exists</span>}
          {!existingRecord && !loading && <span className="ml-4 text-orange-500">● New record</span>}
        </p>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Legend */}
        <div className="flex items-center gap-6 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-white border border-input rounded"></div>
            <span>Editable</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-gray-100 border border-gray-300 rounded"></div>
            <span>Calculated (Auto)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-green-100 border border-green-300 rounded"></div>
            <span>Verification</span>
          </div>
        </div>

        {/* Opening Balances */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {renderEditableField("Opening Balance", "opening_balance")}
          {renderEditableField("Petty Cash Opening", "petty_cash_opening")}
          {renderEditableField("Deposited in Bank", "deposited_in_bank")}
          {renderEditableField("Cash Receipts", "cash_receipts")}
        </div>

        {/* Sales */}
        <div className="border-t pt-4">
          <h3 className="font-medium mb-3">Sales</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {renderEditableField("PBM Sale", "sale_pbm")}
            {renderEditableField("Other Products", "sale_other")}
            {renderCalculatedField("Total Sale of the Day", calculated.total_sale)}
          </div>
        </div>

        {/* Credit/Online Sales */}
        <div className="border-t pt-4">
          <h3 className="font-medium mb-3">Credit / Online Sales</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {renderEditableField("Card IDFC", "card_idfc")}
            {renderEditableField("Bharat Pay", "bharat_pay")}
            {renderEditableField("Swiggy", "swiggy")}
            {renderEditableField("Zomato", "zomato")}
            {renderEditableField("Online Other", "online_other")}
            {renderEditableField("Due Amount", "due_amount")}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-4">
            {renderCalculatedField("Total Online Sale", calculated.total_online_sale)}
            {renderCalculatedField("Total Cash Sale", calculated.total_cash_sale)}
          </div>
        </div>

        {/* Closing / Summary */}
        <div className="border-t pt-4">
          <h3 className="font-medium mb-3">Day End Summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {renderCalculatedField("Cash Expense (from Expenses)", calculated.cash_expense)}
            {renderCalculatedField("Closing Balance", calculated.closing_balance)}
            {renderCalculatedField("To Deposit in Bank", calculated.to_deposit_in_bank)}
            {renderCalculatedField("Petty Cash Closing", calculated.petty_cash_closing)}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-4">
            {renderCalculatedField("Difference for the Day", calculated.difference_for_day, true)}
          </div>
        </div>

        {/* Notes */}
        <div className="border-t pt-4">
          <Label className="text-xs text-muted-foreground">Notes</Label>
          <Input
            value={formData.notes}
            onChange={(e) => handleChange('notes', e.target.value)}
            placeholder="Any remarks for this day..."
            className="mt-1"
          />
        </div>

        {/* Save Button */}
        <div className="flex justify-end pt-4">
          <Button onClick={handleSave} disabled={saving || loading} className="gap-2" data-testid="save-btn">
            <Save className="w-4 h-4" />
            {saving ? "Saving..." : existingRecord ? "Update Record" : "Create Record"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
