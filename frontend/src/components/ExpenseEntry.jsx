import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Plus, Save, Trash2, Receipt, Calendar, RefreshCw, Lock, Unlock } from "lucide-react";
import { api } from "@/lib/api";

// Check if center is Perth (Australia) - standardized to PB-PERTH
const isPerth = (center) => {
  if (!center) return false;
  const c = center.toUpperCase();
  return c === "PB-PERTH" || c === "PERTH";
};

// Format currency based on center
const formatCurrency = (amount, center) => {
  if (amount === null || amount === undefined) return isPerth(center) ? "$0" : "₹0";
  
  if (isPerth(center)) {
    return new Intl.NumberFormat('en-AU', {
      style: 'currency',
      currency: 'AUD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  }
  
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount);
};

// Get today's date
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

export default function ExpenseEntry({ session, selectedCenter }) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedDate, setSelectedDate] = useState(getTodayStr());
  const [expenses, setExpenses] = useState([]);
  const [expenseTypes, setExpenseTypes] = useState([]);
  const [paymentModes, setPaymentModes] = useState([]);
  const [frozenStatus, setFrozenStatus] = useState({ is_frozen: false, can_edit: true });
  
  // New expense form
  const [newExpense, setNewExpense] = useState({
    description: "",
    amount: "",
    expense_type: "",
    payment_mode: "CASH"
  });
  
  const centerCode = selectedCenter || session?.center;

  // Fetch expense types and payment modes
  useEffect(() => {
    const fetchMasters = async () => {
      try {
        console.log("ExpenseEntry: Fetching expense types and payment modes...");
        const [typesRes, modesRes] = await Promise.all([
          api.get("/sales/expense-types"),
          api.get("/sales/payment-modes")
        ]);
        
        if (typesRes.data.expense_types) {
          setExpenseTypes(typesRes.data.expense_types);
          console.log("ExpenseEntry: Loaded expense types:", typesRes.data.expense_types.length);
        }
        if (modesRes.data.payment_modes) {
          setPaymentModes(modesRes.data.payment_modes);
          console.log("ExpenseEntry: Loaded payment modes:", modesRes.data.payment_modes.length);
        }
      } catch (err) {
        console.error("ExpenseEntry: Failed to fetch masters:", err);
        toast.error("Failed to load expense types. Please refresh.");
      }
    };
    fetchMasters();
  }, []);

  // Fetch expenses for selected date
  const fetchExpenses = async () => {
    if (!selectedDate || !centerCode || !session?.token) {
      console.log("ExpenseEntry: Skipping fetch - missing data", { selectedDate, centerCode, hasToken: !!session?.token });
      return;
    }
    
    setLoading(true);
    try {
      // Check frozen status via API
      try {
        const frozenRes = await api.get(`/sales/check-frozen/${centerCode}/${selectedDate}?token=${session.token}`);
        setFrozenStatus({ 
          is_frozen: frozenRes.data.is_frozen, 
          is_admin_frozen: frozenRes.data.is_admin_frozen || false,
          can_edit: frozenRes.data.can_edit,
          reason: frozenRes.data.reason || ""
        });
      } catch (err) {
        // Fallback to local check
        const frozen = isDateFrozen(selectedDate);
        const canEdit = !frozen || session?.is_super_admin;
        setFrozenStatus({ is_frozen: frozen, is_admin_frozen: false, can_edit: canEdit, reason: "" });
      }
      
      console.log("ExpenseEntry: Fetching expenses for", { centerCode, selectedDate });
      const res = await api.post("/sales/expenses", {
        token: session.token,
        center: centerCode,
        start_date: selectedDate,
        end_date: selectedDate
      });
      
      if (res.data.expenses) {
        setExpenses(res.data.expenses);
        console.log("ExpenseEntry: Loaded", res.data.expenses.length, "expenses");
      }
    } catch (err) {
      console.error("ExpenseEntry: Failed to fetch expenses:", err);
      if (err.response?.status === 401) {
        toast.error("Session expired. Please refresh the page and login again.");
      } else {
        toast.error("Failed to load expenses");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (session?.token) {
      console.log("ExpenseEntry: Session ready, fetching expenses...");
      fetchExpenses();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate, centerCode, session?.token]);

  // Note: Removed retry useEffect that was causing flickering
  // Empty expenses for new dates is expected

  // Add new expense
  const handleAddExpense = async () => {
    if (!session?.token) {
      toast.error("Session expired. Please refresh and login again.");
      return;
    }
    if (!centerCode) {
      toast.error("Center not identified. Please refresh and try again.");
      return;
    }
    if (!newExpense.description.trim()) {
      toast.error("Description is required");
      return;
    }
    if (!newExpense.amount || parseFloat(newExpense.amount) <= 0) {
      toast.error("Valid amount is required");
      return;
    }
    if (!newExpense.expense_type) {
      toast.error("Expense type is required");
      return;
    }
    
    setSaving(true);
    try {
      console.log("ExpenseEntry: Adding expense", { centerCode, selectedDate, ...newExpense, token: session.token?.substring(0, 10) + "..." });
      const res = await api.post(`/sales/expenses/create?token=${session.token}`, {
        center: centerCode,
        date: selectedDate,
        description: newExpense.description,
        amount: parseFloat(newExpense.amount),
        expense_type: newExpense.expense_type,
        payment_mode: newExpense.payment_mode || "CASH"
      });
      
      console.log("ExpenseEntry: Expense added successfully", res.data);
      toast.success("Expense added successfully");
      setNewExpense({
        description: "",
        amount: "",
        expense_type: "",
        payment_mode: "CASH"
      });
      fetchExpenses();
    } catch (err) {
      console.error("ExpenseEntry: Failed to add expense:", err.response?.data || err.message);
      if (err.response?.status === 401) {
        toast.error("Session expired. Please refresh the page and login again.");
      } else if (err.response?.status === 403) {
        toast.error(err.response?.data?.detail || "You don't have permission to add expenses for this center.");
      } else {
        toast.error(err.response?.data?.detail || "Failed to add expense. Please try again.");
      }
    } finally {
      setSaving(false);
    }
  };

  // Delete expense
  const handleDeleteExpense = async (expenseId) => {
    if (!confirm("Are you sure you want to delete this expense?")) return;
    
    setSaving(true);
    try {
      await api.delete(`/sales/expenses/${expenseId}?token=${session?.token}`);
      toast.success("Expense deleted");
      fetchExpenses();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to delete expense");
    } finally {
      setSaving(false);
    }
  };

  // Calculate total
  const totalExpenses = expenses.reduce((sum, exp) => sum + (exp.amount || 0), 0);

  // Group expenses by type
  const expensesByType = expenses.reduce((acc, exp) => {
    const type = exp.expense_type || "OTHER";
    acc[type] = (acc[type] || 0) + (exp.amount || 0);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Header with date selector */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <CardTitle className="text-lg flex items-center gap-2">
              <Receipt className="w-5 h-5 text-primary" />
              Daily Expense Entry
              {frozenStatus.is_frozen && (
                <span className={`ml-2 flex items-center gap-1 text-sm font-normal ${frozenStatus.can_edit ? 'text-green-600' : 'text-amber-600'}`}>
                  {frozenStatus.can_edit ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                  {frozenStatus.can_edit ? '(Unlocked)' : '(Frozen)'}
                </span>
              )}
            </CardTitle>
            
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-muted-foreground" />
              <Input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="w-40"
                data-testid="expense-date-input"
              />
              <Button variant="outline" size="icon" onClick={fetchExpenses} disabled={loading}>
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>
          
          <p className="text-sm text-muted-foreground">
            Center: <span className="font-medium text-foreground">{centerCode}</span>
            <span className="ml-4">Total: <span className="font-bold text-red-500">{formatCurrency(totalExpenses, centerCode)}</span></span>
          </p>
        </CardHeader>
      </Card>

      {/* Frozen Warning */}
      {frozenStatus.is_frozen && !frozenStatus.can_edit && (
        <div className={`p-4 rounded-lg border flex items-start gap-3 ${
          frozenStatus.is_admin_frozen 
            ? 'border-red-200 bg-red-50' 
            : 'border-amber-200 bg-amber-50'
        }`}>
          <Lock className={`w-5 h-5 mt-0.5 ${frozenStatus.is_admin_frozen ? 'text-red-600' : 'text-amber-600'}`} />
          <div>
            <h4 className={`font-semibold ${frozenStatus.is_admin_frozen ? 'text-red-800' : 'text-amber-800'}`}>
              {frozenStatus.is_admin_frozen 
                ? 'ADMIN FROZEN - Expenses Locked by Super Admin'
                : `Expenses Frozen for ${selectedDate}`}
            </h4>
            <p className={`text-sm ${frozenStatus.is_admin_frozen ? 'text-red-600' : 'text-amber-600'}`}>
              {frozenStatus.is_admin_frozen
                ? 'This date has been manually frozen by Super Admin. Use Freeze Control to unfreeze.'
                : "Previous day's expenses are automatically locked. Contact Super Admin to unlock for corrections."}
            </p>
          </div>
        </div>
      )}

      {/* Add New Expense Form */}
      <Card className={`bg-card border-border border-2 border-dashed ${frozenStatus.is_frozen && !frozenStatus.can_edit ? 'opacity-60' : ''}`}>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Plus className="w-4 h-4" /> Add New Expense
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="md:col-span-2 space-y-1">
              <Label className="text-xs text-muted-foreground">Description *</Label>
              <Input
                value={newExpense.description}
                onChange={(e) => setNewExpense({ ...newExpense, description: e.target.value })}
                placeholder="e.g., Vegetables from vendor"
                data-testid="expense-description"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Amount *</Label>
              <Input
                type="text"
                inputMode="decimal"
                value={newExpense.amount}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === "" || /^[0-9]*\.?[0-9]*$/.test(val)) {
                    setNewExpense({ ...newExpense, amount: val });
                  }
                }}
                placeholder="0.00"
                data-testid="expense-amount"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Expense Type *</Label>
              <Select 
                value={newExpense.expense_type} 
                onValueChange={(val) => setNewExpense({ ...newExpense, expense_type: val })}
              >
                <SelectTrigger data-testid="expense-type-select">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {expenseTypes.map(type => (
                    <SelectItem key={type} value={type}>{type}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Payment Mode</Label>
              <Select 
                value={newExpense.payment_mode} 
                onValueChange={(val) => setNewExpense({ ...newExpense, payment_mode: val })}
              >
                <SelectTrigger data-testid="payment-mode-select">
                  <SelectValue placeholder="Select mode" />
                </SelectTrigger>
                <SelectContent>
                  {paymentModes.map(mode => (
                    <SelectItem key={mode} value={mode}>{mode}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <div className="flex justify-end mt-4">
            <Button 
              onClick={handleAddExpense} 
              disabled={saving || (frozenStatus.is_frozen && !frozenStatus.can_edit)} 
              className="gap-2" 
              data-testid="add-expense-btn"
            >
              {frozenStatus.is_frozen && !frozenStatus.can_edit ? (
                <>
                  <Lock className="w-4 h-4" /> Date Frozen
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" /> {saving ? "Saving..." : "Add Expense"}
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Expense Summary by Type */}
      {Object.keys(expensesByType).length > 0 && (
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Expense Summary by Type</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(expensesByType)
                .sort((a, b) => b[1] - a[1])
                .map(([type, amount]) => (
                  <div key={type} className="p-3 rounded-lg bg-muted/50 border border-border">
                    <p className="text-xs text-muted-foreground truncate">{type}</p>
                    <p className="text-lg font-bold text-foreground">{formatCurrency(amount, centerCode)}</p>
                  </div>
                ))
              }
            </div>
          </CardContent>
        </Card>
      )}

      {/* Expenses List */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            Expenses for {new Date(selectedDate).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
            <span className="ml-2 text-sm font-normal text-muted-foreground">({expenses.length} entries)</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">#</th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">Description</th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">Type</th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">Mode</th>
                  <th className="text-right py-3 px-2 font-medium text-muted-foreground">Amount</th>
                  <th className="text-right py-3 px-2 font-medium text-muted-foreground">Action</th>
                </tr>
              </thead>
              <tbody>
                {expenses.map((exp, idx) => (
                  <tr key={exp.expense_id || idx} className="border-b border-border/50 hover:bg-muted/50">
                    <td className="py-3 px-2 text-muted-foreground">{idx + 1}</td>
                    <td className="py-3 px-2">{exp.description}</td>
                    <td className="py-3 px-2">
                      <span className="px-2 py-1 rounded-full text-xs bg-muted">{exp.expense_type}</span>
                    </td>
                    <td className="py-3 px-2 text-xs">{exp.payment_mode}</td>
                    <td className="text-right py-3 px-2 font-medium">{formatCurrency(exp.amount, centerCode)}</td>
                    <td className="text-right py-3 px-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteExpense(exp.expense_id)}
                        className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                        data-testid={`delete-expense-${idx}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
                {expenses.length === 0 && (
                  <tr>
                    <td colSpan={6} className="text-center py-8 text-muted-foreground">
                      No expenses recorded for this date
                    </td>
                  </tr>
                )}
              </tbody>
              {expenses.length > 0 && (
                <tfoot>
                  <tr className="bg-muted/50">
                    <td colSpan={4} className="py-3 px-2 font-bold text-right">Total:</td>
                    <td className="py-3 px-2 font-bold text-right text-red-500">{formatCurrency(totalExpenses, centerCode)}</td>
                    <td></td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
