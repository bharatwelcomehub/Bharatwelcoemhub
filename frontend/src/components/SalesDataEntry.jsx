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
  const [previousDayData, setPreviousDayData] = useState(null);
  
  // Form state - User editable fields
  const [formData, setFormData] = useState({
    // AUTO-FILLED from previous day (read-only)
    opening_balance: 0,
    petty_cash_opening: 0,
    
    // USER ENTERS these
    total_sale: 0,           // Total sale of the day
    card_idfc: 0,            // Credit/Debit Card
    bharat_pay: 0,           // Bharat Pay
    swiggy: 0,               // Swiggy
    zomato: 0,               // Zomato
    online_other: 0,         // Other online
    
    // Other fields
    deposited_in_bank: 0,
    cash_receipts: 0,
    due_amount: 0,
    notes: ""
  });

  // Get center code
  const centerCode = selectedCenter || session?.center;

  // CALCULATED fields (gray background - auto-computed)
  const calculated = useMemo(() => {
    // Total Online Sale = Card + Bharat Pay + Swiggy + Zomato + Other
    const total_online_sale = (
      (parseFloat(formData.card_idfc) || 0) +
      (parseFloat(formData.bharat_pay) || 0) +
      (parseFloat(formData.swiggy) || 0) +
      (parseFloat(formData.zomato) || 0) +
      (parseFloat(formData.online_other) || 0)
    );
    
    // Cash Sale = Total Sale - Total Online Sale
    const total_cash_sale = Math.max(0, (parseFloat(formData.total_sale) || 0) - total_online_sale);
    
    // Cash expense would come from expenses entered separately
    const cash_expense = existingRecord?.cash_expense || 0;
    
    // Closing Balance calculation
    const closing_balance = (
      (parseFloat(formData.opening_balance) || 0) +
      total_cash_sale +
      (parseFloat(formData.cash_receipts) || 0) -
      (parseFloat(formData.deposited_in_bank) || 0) -
      cash_expense
    );
    
    // Petty Cash Closing
    const petty_cash_closing = (
      (parseFloat(formData.petty_cash_opening) || 0) +
      (parseFloat(formData.cash_receipts) || 0) -
      cash_expense
    );
    
    const to_deposit_in_bank = closing_balance - petty_cash_closing;
    
    return {
      total_sale: parseFloat(formData.total_sale) || 0,
      total_online_sale,
      total_cash_sale,
      cash_expense,
      closing_balance,
      petty_cash_closing,
      to_deposit_in_bank
    };
  }, [formData, existingRecord]);

  // Fetch existing record for selected date
  const fetchRecord = async () => {
    if (!selectedDate || !centerCode) return;
    
    setLoading(true);
    try {
      // Get previous day's data for opening balance
      const prevDate = new Date(selectedDate);
      prevDate.setDate(prevDate.getDate() - 1);
      const prevDateStr = prevDate.toISOString().split('T')[0];
      
      const prevRes = await api.post("/sales/daily", {
        token: session?.token,
        center: centerCode,
        start_date: prevDateStr,
        end_date: prevDateStr
      });
      
      const prevData = prevRes.data.sales?.[0] || null;
      setPreviousDayData(prevData);
      
      // Get today's record
      const res = await api.post("/sales/daily", {
        token: session?.token,
        center: centerCode,
        start_date: selectedDate,
        end_date: selectedDate
      });
      
      if (res.data.sales && res.data.sales.length > 0) {
        const record = res.data.sales[0];
        setExistingRecord(record);
        
        // Calculate total_sale from the record
        const recordTotalSale = (record.sale_pbm || 0) + (record.sale_other || 0);
        
        setFormData({
          opening_balance: record.opening_balance || prevData?.closing_balance || 0,
          petty_cash_opening: record.petty_cash_opening || prevData?.petty_cash_closing || 0,
          total_sale: recordTotalSale || record.total_sale || 0,
          card_idfc: record.card_idfc || 0,
          bharat_pay: record.bharat_pay || 0,
          swiggy: record.swiggy || 0,
          zomato: record.zomato || 0,
          online_other: record.online_other || 0,
          deposited_in_bank: record.deposited_in_bank || 0,
          cash_receipts: record.cash_receipts || 0,
          due_amount: record.due_amount || 0,
          notes: record.notes || ""
        });
      } else {
        setExistingRecord(null);
        // New entry - use previous day's closing as opening
        setFormData({
          opening_balance: prevData?.closing_balance || 0,
          petty_cash_opening: prevData?.petty_cash_closing || 0,
          total_sale: 0,
          card_idfc: 0,
          bharat_pay: 0,
          swiggy: 0,
          zomato: 0,
          online_other: 0,
          deposited_in_bank: 0,
          cash_receipts: 0,
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

  // Handle input change
  const handleChange = (field, value) => {
    // Prevent changing auto-calculated fields
    if (field === 'opening_balance' || field === 'petty_cash_opening') {
      return; // These are read-only
    }
    
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Save record
  const handleSave = async () => {
    if (!centerCode || !selectedDate) {
      toast.error("Please select center and date");
      return;
    }
    
    setSaving(true);
    try {
      const payload = {
        token: session?.token,
        center: centerCode,
        date: selectedDate,
        opening_balance: parseFloat(formData.opening_balance) || 0,
        petty_cash_opening: parseFloat(formData.petty_cash_opening) || 0,
        deposited_in_bank: parseFloat(formData.deposited_in_bank) || 0,
        cash_receipts: parseFloat(formData.cash_receipts) || 0,
        // Store total_sale as sale_pbm for compatibility
        sale_pbm: parseFloat(formData.total_sale) || 0,
        sale_other: 0,
        card_idfc: parseFloat(formData.card_idfc) || 0,
        bharat_pay: parseFloat(formData.bharat_pay) || 0,
        swiggy: parseFloat(formData.swiggy) || 0,
        zomato: parseFloat(formData.zomato) || 0,
        online_other: parseFloat(formData.online_other) || 0,
        due_amount: parseFloat(formData.due_amount) || 0,
        notes: formData.notes || "",
        // Calculated fields
        total_sale: calculated.total_sale,
        total_online_sale: calculated.total_online_sale,
        total_cash_sale: calculated.total_cash_sale,
        closing_balance: calculated.closing_balance,
        petty_cash_closing: calculated.petty_cash_closing
      };
      
      if (existingRecord) {
        await api.put(`/sales/daily/${centerCode}/${selectedDate}?token=${session?.token}`, payload);
        toast.success("Record updated successfully!");
      } else {
        await api.post(`/sales/daily/create?token=${session?.token}`, payload);
        toast.success("Record created successfully!");
      }
      
      fetchRecord();
    } catch (err) {
      console.error("Save error:", err);
      toast.error(err.response?.data?.detail || "Failed to save record");
    } finally {
      setSaving(false);
    }
  };

  // Navigate dates
  const goToPrevDay = () => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() - 1);
    setSelectedDate(d.toISOString().split('T')[0]);
  };
  
  const goToNextDay = () => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + 1);
    setSelectedDate(d.toISOString().split('T')[0]);
  };

  // Input field component - Editable (white)
  const EditableField = ({ label, field, prefix = "₹" }) => (
    <div className="space-y-1">
      <Label className="text-xs font-medium text-foreground">{label}</Label>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">{prefix}</span>
        <Input
          type="number"
          value={formData[field] || ""}
          onChange={(e) => handleChange(field, e.target.value)}
          className="pl-8 text-right bg-white border-primary/30 focus:border-primary"
          placeholder="0.00"
        />
      </div>
    </div>
  );

  // Read-only field component (gray background)
  const ReadOnlyField = ({ label, value, prefix = "₹", highlight = false }) => (
    <div className="space-y-1">
      <Label className="text-xs font-medium text-muted-foreground">{label}</Label>
      <div className={`px-3 py-2 rounded-md text-right font-mono ${
        highlight ? 'bg-primary/10 text-primary font-bold' : 'bg-gray-100 text-gray-600'
      }`}>
        {prefix}{formatNum(value)}
      </div>
    </div>
  );

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Calculator className="w-5 h-5" />
            Daily Sales Entry - {centerCode}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={goToPrevDay}>
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <div className="flex items-center gap-2 px-3 py-1 bg-muted rounded-md">
              <Calendar className="w-4 h-4 text-muted-foreground" />
              <Input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="w-36 border-0 bg-transparent p-0 focus:ring-0"
              />
            </div>
            <Button variant="outline" size="icon" onClick={goToNextDay}>
              <ChevronRight className="w-4 h-4" />
            </Button>
            <Button variant="outline" size="icon" onClick={fetchRecord} disabled={loading}>
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
        {existingRecord && (
          <p className="text-xs text-muted-foreground mt-1">
            Last updated: {new Date(existingRecord.updated_at || existingRecord.created_at).toLocaleString()}
          </p>
        )}
      </CardHeader>
      
      <CardContent className="space-y-6">
        {loading ? (
          <div className="text-center py-8 text-muted-foreground">Loading...</div>
        ) : (
          <>
            {/* SECTION 1: Opening Balances (Auto-filled, Read-only) */}
            <div className="p-4 bg-gray-50 rounded-lg border">
              <h3 className="text-sm font-semibold text-gray-600 mb-3">Opening Balances (Auto from Previous Day)</h3>
              <div className="grid grid-cols-2 gap-4">
                <ReadOnlyField 
                  label="Opening Balance" 
                  value={formData.opening_balance} 
                />
                <ReadOnlyField 
                  label="Petty Cash Opening" 
                  value={formData.petty_cash_opening} 
                />
              </div>
              {previousDayData && (
                <p className="text-xs text-muted-foreground mt-2">
                  From previous day's closing balance
                </p>
              )}
            </div>

            {/* SECTION 2: Sales Entry */}
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <h3 className="text-sm font-semibold text-blue-700 mb-3">Sales Entry</h3>
              
              {/* Total Sale - Main Entry */}
              <div className="mb-4">
                <Label className="text-sm font-bold text-blue-800">Total Sale of the Day *</Label>
                <div className="relative mt-1">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">₹</span>
                  <Input
                    type="number"
                    value={formData.total_sale || ""}
                    onChange={(e) => handleChange('total_sale', e.target.value)}
                    className="pl-8 text-right text-lg font-bold bg-white border-2 border-blue-300 focus:border-blue-500"
                    placeholder="Enter total sale"
                  />
                </div>
              </div>
              
              {/* Online Sales Bifurcation */}
              <div className="mt-4">
                <Label className="text-sm font-medium text-blue-700 mb-2 block">Online Sales Bifurcation</Label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <EditableField label="Card (Credit/Debit)" field="card_idfc" />
                  <EditableField label="Bharat Pay" field="bharat_pay" />
                  <EditableField label="Swiggy" field="swiggy" />
                  <EditableField label="Zomato" field="zomato" />
                </div>
                <div className="mt-3">
                  <EditableField label="Other Online" field="online_other" />
                </div>
              </div>
              
              {/* Auto-calculated fields */}
              <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-blue-200">
                <ReadOnlyField 
                  label="Total Online Sale (Auto)" 
                  value={calculated.total_online_sale}
                />
                <ReadOnlyField 
                  label="Cash Sale (Auto: Total - Online)" 
                  value={calculated.total_cash_sale}
                  highlight={true}
                />
              </div>
            </div>

            {/* SECTION 3: Cash Flow */}
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <h3 className="text-sm font-semibold text-green-700 mb-3">Cash Flow</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <EditableField label="Deposited in Bank" field="deposited_in_bank" />
                <EditableField label="Cash Receipts" field="cash_receipts" />
                <EditableField label="Due Amount" field="due_amount" />
              </div>
            </div>

            {/* SECTION 4: Closing Summary (Auto-calculated) */}
            <div className="p-4 bg-orange-50 rounded-lg border border-orange-200">
              <h3 className="text-sm font-semibold text-orange-700 mb-3">Closing Summary (Auto-calculated)</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <ReadOnlyField 
                  label="Cash Expense" 
                  value={calculated.cash_expense}
                />
                <ReadOnlyField 
                  label="Closing Balance" 
                  value={calculated.closing_balance}
                  highlight={true}
                />
                <ReadOnlyField 
                  label="Petty Cash Closing" 
                  value={calculated.petty_cash_closing}
                  highlight={true}
                />
              </div>
              <div className="grid grid-cols-1 gap-4 mt-3">
                <ReadOnlyField 
                  label="To Deposit in Bank" 
                  value={calculated.to_deposit_in_bank}
                />
              </div>
            </div>

            {/* Notes */}
            <div>
              <Label className="text-sm font-medium">Notes</Label>
              <textarea
                value={formData.notes}
                onChange={(e) => handleChange('notes', e.target.value)}
                className="w-full mt-1 p-3 border rounded-md resize-none h-20 text-sm"
                placeholder="Any additional notes..."
              />
            </div>

            {/* Save Button */}
            <div className="flex justify-end pt-4 border-t">
              <Button onClick={handleSave} disabled={saving} className="gap-2">
                <Save className="w-4 h-4" />
                {saving ? "Saving..." : existingRecord ? "Update Record" : "Save Record"}
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
