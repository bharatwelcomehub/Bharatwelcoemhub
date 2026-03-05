import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Save, Calculator, Calendar, RefreshCw, ChevronLeft, ChevronRight, Users, Receipt, Lock, Unlock } from "lucide-react";
import { api } from "@/lib/api";

// Check if center is Perth (Australia) - standardized to PB-PERTH
const isPerth = (center) => {
  if (!center) return false;
  const c = center.toUpperCase();
  return c === "PB-PERTH" || c === "PERTH";
};

// Get currency symbol based on center
const getCurrencySymbol = (center) => isPerth(center) ? "$" : "₹";

// Format currency for display
const formatCurrency = (num, center) => {
  if (num === null || num === undefined || isNaN(num)) return "0.00";
  const symbol = getCurrencySymbol(center);
  return `${symbol}${Math.abs(num).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

// Format number without currency
const formatNum = (num) => {
  if (num === null || num === undefined || isNaN(num)) return "0.00";
  return num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

// Get today's date in YYYY-MM-DD format
const getTodayStr = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
};

// Check if a date is frozen (previous day or older)
const isDateFrozen = (dateStr) => {
  if (!dateStr) return true;
  const recordDate = new Date(dateStr);
  recordDate.setHours(0, 0, 0, 0);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return recordDate < today;
};

// GST Calculation
// India: 5% GST ADDED to subtotal (excluding Swiggy/Zomato)
// Perth: 10% GST INCLUDED in total (extract from total)
const calculateGST = (totalSale, swiggy, zomato, center) => {
  // Exclude Swiggy and Zomato from GST calculation
  const gstApplicableSale = (parseFloat(totalSale) || 0) - (parseFloat(swiggy) || 0) - (parseFloat(zomato) || 0);
  
  if (isPerth(center)) {
    // Australia (Perth): 10% GST is INCLUDED in price
    // Formula: GST = Total / 11
    const gstAmount = gstApplicableSale / 11;
    const netSale = gstApplicableSale - gstAmount;
    return {
      gstRate: 10,
      gstAmount: gstAmount,
      netSale: netSale,
      isInclusive: true
    };
  } else {
    // India: 5% GST is ADDED to subtotal
    // Formula: GST = Subtotal * 0.05
    const gstAmount = gstApplicableSale * 0.05;
    return {
      gstRate: 5,
      gstAmount: gstAmount,
      netSale: gstApplicableSale,
      isInclusive: false
    };
  }
};

export default function SalesDataEntry({ session, selectedCenter }) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedDate, setSelectedDate] = useState(getTodayStr());
  const [existingRecord, setExistingRecord] = useState(null);
  const [previousDayData, setPreviousDayData] = useState(null);
  const [frozenStatus, setFrozenStatus] = useState({ is_frozen: false, can_edit: true, reason: "" });
  
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
    amazon: 0,               // Amazon (NEW)
    ecwid: 0,                // ECWID (NEW)
    paytm: 0,                // Paytm (NEW)
    pbm_online: 0,           // PBM Online (NEW)
    online_other: 0,         // Other online
    
    // Guest & Bill tracking
    num_guests: 0,           // Number of guests (pax)
    num_bills: 0,            // Number of bills (excluding Swiggy/Zomato)
    
    // Other fields
    deposited_in_bank: 0,
    cash_receipts: 0,        // Withdrawal from bank
    due_amount: 0,
    notes: ""
  });

  // Get center code - use session center if selectedCenter is "all" or not set
  const centerCode = (selectedCenter && selectedCenter !== "all") ? selectedCenter : session?.center;
  const currencySymbol = getCurrencySymbol(centerCode);
  const isPerthCenter = isPerth(centerCode);

  // CALCULATED fields (gray background - auto-computed)
  // Using CORRECT FORMULAS provided by user
  const calculated = useMemo(() => {
    // Total Online Sale = sum of ALL non-cash channels
    // Swiggy + Zomato + Amazon + ECWID + Card + Bharatpay + Paytm + PBM + Other
    const total_online_sale = (
      (parseFloat(formData.swiggy) || 0) +
      (parseFloat(formData.zomato) || 0) +
      (parseFloat(formData.amazon) || 0) +
      (parseFloat(formData.ecwid) || 0) +
      (parseFloat(formData.card_idfc) || 0) +
      (parseFloat(formData.bharat_pay) || 0) +
      (parseFloat(formData.paytm) || 0) +
      (parseFloat(formData.pbm_online) || 0) +
      (parseFloat(formData.online_other) || 0)
    );
    
    const total_sale = parseFloat(formData.total_sale) || 0;
    
    // CASH SALE = Total Sale - Total Online Sale
    const total_cash_sale = Math.max(0, total_sale - total_online_sale);
    
    // GST Calculation
    const gst = calculateGST(total_sale, formData.swiggy, formData.zomato, centerCode);
    
    // Average calculations
    const num_guests = parseInt(formData.num_guests) || 0;
    const num_bills = parseInt(formData.num_bills) || 0;
    const avg_per_pax = num_guests > 0 ? total_sale / num_guests : 0;
    const avg_per_bill = num_bills > 0 ? total_sale / num_bills : 0;
    
    // Cash expense would come from expenses entered separately
    const cash_expense = existingRecord?.cash_expense || 0;
    
    // Opening & Withdrawal
    const opening_balance = parseFloat(formData.opening_balance) || 0;
    const withdrawal = parseFloat(formData.cash_receipts) || 0;  // Withdrawal from bank
    const deposited_in_bank = parseFloat(formData.deposited_in_bank) || 0;
    const petty_cash_opening = parseFloat(formData.petty_cash_opening) || 0;
    
    // CASH IN HAND = Opening Balance + Withdrawal + Total Sale - (All Online + Expenses)
    // = Opening Balance + Withdrawal + Cash Sale - Expenses
    const cash_in_hand = opening_balance + withdrawal + total_cash_sale - cash_expense;
    
    // PETTY CASH = Last Day Petty Cash + Withdrawal - Expenses in Cash
    const petty_cash_closing = petty_cash_opening + withdrawal - cash_expense;
    
    // Closing Balance = Opening + Cash Sale + Withdrawal - Deposited - Cash Expenses
    const closing_balance = opening_balance + total_cash_sale + withdrawal - deposited_in_bank - cash_expense;
    
    // To Deposit = Closing Balance - Petty Cash Closing
    const to_deposit_in_bank = closing_balance - petty_cash_closing;
    
    return {
      total_sale,
      total_online_sale,
      total_cash_sale,
      cash_in_hand,       // NEW
      cash_expense,
      closing_balance,
      petty_cash_closing,
      to_deposit_in_bank,
      // GST
      gst_rate: gst.gstRate,
      gst_amount: gst.gstAmount,
      net_sale: gst.netSale,
      gst_inclusive: gst.isInclusive,
      // Averages
      avg_per_pax,
      avg_per_bill
    };
  }, [formData, existingRecord, centerCode]);

  // Fetch existing record for selected date
  const fetchRecord = async () => {
    if (!selectedDate || !centerCode || !session?.token) {
      console.log("SalesDataEntry: Skipping fetch - missing data", { selectedDate, centerCode, hasToken: !!session?.token });
      return;
    }
    
    setLoading(true);
    try {
      // Check frozen status first
      try {
        const frozenRes = await api.get(`/sales/check-frozen/${centerCode}/${selectedDate}?token=${session.token}`);
        setFrozenStatus({
          is_frozen: frozenRes.data.is_frozen,
          is_admin_frozen: frozenRes.data.is_admin_frozen || false,
          can_edit: frozenRes.data.can_edit_sales,  // Use sales-specific field
          reason: frozenRes.data.reason_sales || frozenRes.data.reason || ""
        });
      } catch (err) {
        // If endpoint doesn't exist, fall back to local check
        const frozen = isDateFrozen(selectedDate);
        setFrozenStatus({
          is_frozen: frozen,
          is_admin_frozen: false,
          can_edit: !frozen || session?.is_super_admin,
          reason: frozen ? "Date is frozen" : ""
        });
      }
      
      // Get previous day's data for opening balance
      const prevDate = new Date(selectedDate);
      prevDate.setDate(prevDate.getDate() - 1);
      const prevDateStr = prevDate.toISOString().split('T')[0];
      
      console.log("SalesDataEntry: Fetching previous day data", { prevDateStr, centerCode });
      const prevRes = await api.post("/sales/daily", {
        token: session.token,
        center: centerCode,
        start_date: prevDateStr,
        end_date: prevDateStr
      });
      
      const prevData = prevRes.data.sales?.[0] || null;
      setPreviousDayData(prevData);
      console.log("SalesDataEntry: Previous day data", prevData ? { closing: prevData.closing_balance, pettyCash: prevData.petty_cash_closing } : "none");
      
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
        
        // Get total_sale - prefer direct total_sale, fallback to sum of sale_pbm + sale_other
        const recordTotalSale = record.total_sale || ((record.sale_pbm || 0) + (record.sale_other || 0));
        
        setFormData({
          opening_balance: record.opening_balance || prevData?.closing_balance || 0,
          petty_cash_opening: record.petty_cash_opening || prevData?.petty_cash_closing || 0,
          total_sale: recordTotalSale || 0,
          card_idfc: record.card_idfc || 0,
          bharat_pay: record.bharat_pay || 0,
          swiggy: record.swiggy || 0,
          zomato: record.zomato || 0,
          amazon: record.amazon || 0,
          ecwid: record.ecwid || 0,
          paytm: record.paytm || 0,
          pbm_online: record.pbm_online || 0,
          online_other: record.online_other || 0,
          num_guests: record.num_guests || 0,
          num_bills: record.num_bills || 0,
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
          amazon: 0,
          ecwid: 0,
          paytm: 0,
          pbm_online: 0,
          online_other: 0,
          num_guests: 0,
          num_bills: 0,
          deposited_in_bank: 0,
          cash_receipts: 0,
          due_amount: 0,
          notes: ""
        });
      }
    } catch (err) {
      console.error("SalesDataEntry: Failed to fetch record:", err);
      if (err.response?.status === 401) {
        toast.error("Session expired. Please refresh and login again.");
      } else {
        toast.error("Failed to load data");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (session?.token) {
      console.log("SalesDataEntry: Session ready, fetching record...");
      fetchRecord();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate, centerCode, session?.token]);

  // Note: Removed retry useEffect that was causing flickering
  // Empty data for new dates/months is expected and shouldn't trigger retries

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
    if (!session?.token) {
      toast.error("Session expired. Please refresh and login again.");
      return;
    }
    if (!centerCode || !selectedDate) {
      toast.error("Please select center and date");
      return;
    }
    
    setSaving(true);
    try {
      const payload = {
        token: session.token,
        center: centerCode,
        date: selectedDate,
        opening_balance: parseFloat(formData.opening_balance) || 0,
        petty_cash_opening: parseFloat(formData.petty_cash_opening) || 0,
        deposited_in_bank: parseFloat(formData.deposited_in_bank) || 0,
        cash_receipts: parseFloat(formData.cash_receipts) || 0,
        // Store total_sale as sale_pbm for compatibility
        sale_pbm: parseFloat(formData.total_sale) || 0,
        sale_other: 0,
        // ALL non-cash payment channels
        card_idfc: parseFloat(formData.card_idfc) || 0,
        bharat_pay: parseFloat(formData.bharat_pay) || 0,
        swiggy: parseFloat(formData.swiggy) || 0,
        zomato: parseFloat(formData.zomato) || 0,
        amazon: parseFloat(formData.amazon) || 0,
        ecwid: parseFloat(formData.ecwid) || 0,
        paytm: parseFloat(formData.paytm) || 0,
        pbm_online: parseFloat(formData.pbm_online) || 0,
        online_other: parseFloat(formData.online_other) || 0,
        num_guests: parseInt(formData.num_guests) || 0,
        num_bills: parseInt(formData.num_bills) || 0,
        due_amount: parseFloat(formData.due_amount) || 0,
        notes: formData.notes || "",
        // Calculated fields
        total_sale: calculated.total_sale,
        total_online_sale: calculated.total_online_sale,
        total_cash_sale: calculated.total_cash_sale,
        cash_in_hand: calculated.cash_in_hand,
        closing_balance: calculated.closing_balance,
        petty_cash_closing: calculated.petty_cash_closing,
        gst_amount: calculated.gst_amount,
        avg_per_pax: calculated.avg_per_pax,
        avg_per_bill: calculated.avg_per_bill
      };
      
      console.log("SalesDataEntry: Saving record", { centerCode, selectedDate, existingRecord: !!existingRecord });
      
      if (existingRecord) {
        await api.put(`/sales/daily/${centerCode}/${selectedDate}?token=${session.token}`, payload);
        toast.success("Record updated successfully!");
      } else {
        await api.post(`/sales/daily/create?token=${session.token}`, payload);
        toast.success("Record created successfully!");
      }
      
      fetchRecord();
    } catch (err) {
      console.error("SalesDataEntry: Save error:", err);
      if (err.response?.status === 401) {
        toast.error("Session expired. Please refresh and login again.");
      } else if (err.response?.status === 403) {
        toast.error(err.response?.data?.detail || "You don't have permission to save this record.");
      } else {
        toast.error(err.response?.data?.detail || "Failed to save record");
      }
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

  // Check if form should be editable
  const isFormEditable = frozenStatus.can_edit;

  // Input field component - Editable (white) or Read-only for frozen dates
  const EditableField = ({ label, field, prefix, type = "number" }) => (
    <div className="space-y-1">
      <Label className="text-xs font-medium text-foreground">{label}</Label>
      <div className="relative">
        {prefix && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">{prefix}</span>
        )}
        <Input
          type={type}
          value={formData[field] || ""}
          onChange={(e) => handleChange(field, e.target.value)}
          disabled={!isFormEditable}
          className={`${prefix ? 'pl-8' : 'pl-3'} text-right ${
            isFormEditable 
              ? 'bg-white border-primary/30 focus:border-primary' 
              : 'bg-gray-100 text-gray-600 cursor-not-allowed'
          }`}
          placeholder="0"
        />
      </div>
    </div>
  );

  // Read-only field component (gray background)
  const ReadOnlyField = ({ label, value, prefix, highlight = false, info = "" }) => (
    <div className="space-y-1">
      <Label className="text-xs font-medium text-muted-foreground">{label}</Label>
      <div className={`px-3 py-2 rounded-md text-right font-mono ${
        highlight ? 'bg-primary/10 text-primary font-bold' : 'bg-gray-100 text-gray-600'
      }`}>
        {prefix}{formatNum(value)}
      </div>
      {info && <p className="text-xs text-muted-foreground">{info}</p>}
    </div>
  );

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <Calculator className="w-5 h-5" />
            Daily Sales Entry - {centerCode}
            {isPerthCenter && <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">AUD $</span>}
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
        {/* Frozen Date Warning */}
        {frozenStatus.is_frozen && (
          <div className={`p-4 rounded-lg border flex items-start gap-3 ${
            frozenStatus.can_edit 
              ? 'bg-green-50 border-green-200' 
              : frozenStatus.is_admin_frozen
                ? 'bg-red-50 border-red-200'
                : 'bg-amber-50 border-amber-200'
          }`}>
            {frozenStatus.can_edit ? (
              <Unlock className="w-5 h-5 text-green-600 mt-0.5" />
            ) : (
              <Lock className={`w-5 h-5 mt-0.5 ${frozenStatus.is_admin_frozen ? 'text-red-600' : 'text-amber-600'}`} />
            )}
            <div>
              <h4 className={`font-semibold ${
                frozenStatus.can_edit 
                  ? 'text-green-800' 
                  : frozenStatus.is_admin_frozen 
                    ? 'text-red-800' 
                    : 'text-amber-800'
              }`}>
                {frozenStatus.can_edit 
                  ? 'Unlocked by Super Admin' 
                  : frozenStatus.is_admin_frozen 
                    ? 'ADMIN FROZEN - Locked by Super Admin'
                    : 'This date is frozen'}
              </h4>
              <p className={`text-sm ${
                frozenStatus.can_edit 
                  ? 'text-green-600' 
                  : frozenStatus.is_admin_frozen 
                    ? 'text-red-600' 
                    : 'text-amber-600'
              }`}>
                {frozenStatus.can_edit 
                  ? 'You have temporary access to edit this date. Changes allowed for 24 hours.'
                  : frozenStatus.is_admin_frozen
                    ? 'This date has been manually frozen by Super Admin. Use Freeze Control to unfreeze.'
                    : 'Previous day data is automatically locked at midnight. Request unlock from Super Admin to make changes.'
                }
              </p>
            </div>
          </div>
        )}

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
                  prefix={currencySymbol}
                />
                <ReadOnlyField 
                  label="Petty Cash Opening" 
                  value={formData.petty_cash_opening}
                  prefix={currencySymbol}
                />
              </div>
              {previousDayData && (
                <p className="text-xs text-muted-foreground mt-2">
                  From previous day's closing balance
                </p>
              )}
            </div>

            {/* SECTION 2: Guest & Bill Count */}
            <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
              <h3 className="text-sm font-semibold text-purple-700 mb-3 flex items-center gap-2">
                <Users className="w-4 h-4" />
                Guest & Bill Count
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <EditableField label="Number of Guests (Pax)" field="num_guests" type="number" />
                <EditableField label="Number of Bills (excl. Swiggy/Zomato)" field="num_bills" type="number" />
                <ReadOnlyField 
                  label="Avg Per Pax" 
                  value={calculated.avg_per_pax}
                  prefix={currencySymbol}
                  highlight={true}
                />
                <ReadOnlyField 
                  label="Avg Per Bill" 
                  value={calculated.avg_per_bill}
                  prefix={currencySymbol}
                  highlight={true}
                />
              </div>
            </div>

            {/* SECTION 3: Sales Entry */}
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <h3 className="text-sm font-semibold text-blue-700 mb-3">Sales Entry</h3>
              
              {/* Total Sale - Main Entry */}
              <div className="mb-4">
                <Label className="text-sm font-bold text-blue-800">Total Sale of the Day *</Label>
                <div className="relative mt-1">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">{currencySymbol}</span>
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
                <Label className="text-sm font-medium text-blue-700 mb-2 block">Online/Non-Cash Sales Breakdown</Label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <EditableField label="Swiggy" field="swiggy" prefix={currencySymbol} />
                  <EditableField label="Zomato" field="zomato" prefix={currencySymbol} />
                  <EditableField label="Amazon" field="amazon" prefix={currencySymbol} />
                  <EditableField label="ECWID" field="ecwid" prefix={currencySymbol} />
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
                  <EditableField label="Card (Credit/Debit)" field="card_idfc" prefix={currencySymbol} />
                  <EditableField label="Bharat Pay" field="bharat_pay" prefix={currencySymbol} />
                  <EditableField label="Paytm" field="paytm" prefix={currencySymbol} />
                  <EditableField label="PBM Online" field="pbm_online" prefix={currencySymbol} />
                </div>
                <div className="mt-3">
                  <EditableField label="Other Online" field="online_other" prefix={currencySymbol} />
                </div>
              </div>
              
              {/* Auto-calculated fields */}
              <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-blue-200">
                <ReadOnlyField 
                  label="Total Online Sale (Auto)" 
                  value={calculated.total_online_sale}
                  prefix={currencySymbol}
                />
                <ReadOnlyField 
                  label="Cash Sale (Total - Online)" 
                  value={calculated.total_cash_sale}
                  prefix={currencySymbol}
                  highlight={true}
                />
                <ReadOnlyField 
                  label="Cash in Hand" 
                  value={calculated.cash_in_hand}
                  prefix={currencySymbol}
                  highlight={true}
                  info="Opening + Withdrawal + Cash Sale - Expenses"
                />
              </div>
            </div>

            {/* SECTION 4: GST Calculation */}
            <div className={`p-4 rounded-lg border ${isPerthCenter ? 'bg-yellow-50 border-yellow-200' : 'bg-amber-50 border-amber-200'}`}>
              <h3 className={`text-sm font-semibold mb-3 ${isPerthCenter ? 'text-yellow-700' : 'text-amber-700'}`}>
                GST Calculation ({isPerthCenter ? 'Australia - 10% Inclusive' : 'India - 5% Added'})
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <ReadOnlyField 
                  label={isPerthCenter ? "Net Sale (excl. GST)" : "Sale (before GST)"}
                  value={calculated.net_sale}
                  prefix={currencySymbol}
                />
                <ReadOnlyField 
                  label={`GST Payable (${calculated.gst_rate}%)`}
                  value={calculated.gst_amount}
                  prefix={currencySymbol}
                  highlight={true}
                  info={isPerthCenter ? "Extracted from total (GST inclusive)" : "Added on subtotal (excl. Swiggy/Zomato)"}
                />
                <ReadOnlyField 
                  label="Total (with GST)"
                  value={isPerthCenter ? calculated.total_sale : (calculated.net_sale + calculated.gst_amount)}
                  prefix={currencySymbol}
                  highlight={true}
                />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                * GST not applicable on Swiggy & Zomato orders
              </p>
            </div>

            {/* SECTION 5: Cash Flow */}
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <h3 className="text-sm font-semibold text-green-700 mb-3">Cash Flow</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <EditableField label="Deposited in Bank" field="deposited_in_bank" prefix={currencySymbol} />
                <EditableField label="Cash Receipts" field="cash_receipts" prefix={currencySymbol} />
                <EditableField label="Due Amount" field="due_amount" prefix={currencySymbol} />
              </div>
            </div>

            {/* SECTION 6: Closing Summary (Auto-calculated) */}
            <div className="p-4 bg-orange-50 rounded-lg border border-orange-200">
              <h3 className="text-sm font-semibold text-orange-700 mb-3">Closing Summary (Auto-calculated)</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <ReadOnlyField 
                  label="Cash Expense" 
                  value={calculated.cash_expense}
                  prefix={currencySymbol}
                />
                <ReadOnlyField 
                  label="Closing Balance" 
                  value={calculated.closing_balance}
                  prefix={currencySymbol}
                  highlight={true}
                />
                <ReadOnlyField 
                  label="Petty Cash Closing" 
                  value={calculated.petty_cash_closing}
                  prefix={currencySymbol}
                  highlight={true}
                />
              </div>
              <div className="grid grid-cols-1 gap-4 mt-3">
                <ReadOnlyField 
                  label="To Deposit in Bank" 
                  value={calculated.to_deposit_in_bank}
                  prefix={currencySymbol}
                />
              </div>
            </div>

            {/* Notes */}
            <div>
              <Label className="text-sm font-medium">Notes</Label>
              <textarea
                value={formData.notes}
                onChange={(e) => handleChange('notes', e.target.value)}
                disabled={!isFormEditable}
                className={`w-full mt-1 p-3 border rounded-md resize-none h-20 text-sm ${
                  !isFormEditable ? 'bg-gray-100 text-gray-600 cursor-not-allowed' : ''
                }`}
                placeholder="Any additional notes..."
              />
            </div>

            {/* Save Button */}
            <div className="flex justify-end pt-4 border-t">
              <Button 
                onClick={handleSave} 
                disabled={saving || (frozenStatus.is_frozen && !frozenStatus.can_edit)} 
                className="gap-2"
              >
                {frozenStatus.is_frozen && !frozenStatus.can_edit ? (
                  <>
                    <Lock className="w-4 h-4" />
                    Date Frozen
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    {saving ? "Saving..." : existingRecord ? "Update Record" : "Save Record"}
                  </>
                )}
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
