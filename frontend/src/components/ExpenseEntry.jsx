import { useState, useEffect, useRef, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Plus, Save, Trash2, Receipt, Calendar, RefreshCw, Lock, Unlock, Check, X, Paperclip, FileText, Link2, Eye, Download, Upload, FolderOpen, AlertTriangle, CheckCircle2, Loader2, FilterX } from "lucide-react";
import { api, isInternationalCenter } from "@/lib/api";
import ColumnFilterMenu from "@/components/ColumnFilterMenu";

// Check if center is international (non-India) — DB-driven via centersList
const isIntl = (center, centersList = []) => isInternationalCenter(center, centersList);

// Format currency based on center
const formatCurrency = (amount, center, centersList = []) => {
  if (amount === null || amount === undefined) return isIntl(center, centersList) ? "$0" : "₹0";
  
  if (isIntl(center, centersList)) {
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

export default function ExpenseEntry({ session, selectedCenter, centersList = [] }) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedDate, setSelectedDate] = useState(getTodayStr());
  const [fromDate, setFromDate] = useState(getTodayStr());
  const [toDate, setToDate] = useState(getTodayStr());
  const [dateMode, setDateMode] = useState("single");  // "single" or "range"
  const [expenses, setExpenses] = useState([]);
  const [editedExpenses, setEditedExpenses] = useState({});  // Track edited rows by expense_id
  const [hasChanges, setHasChanges] = useState(false);
  const [expenseTypes, setExpenseTypes] = useState([]);
  const [paymentModes, setPaymentModes] = useState([]);
  const [frozenStatus, setFrozenStatus] = useState({ is_frozen: false, can_edit: true });
  
  // Attachment & Grouping state
  const [selectedExpenses, setSelectedExpenses] = useState([]);  // For bulk grouping
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [showGroupDetailModal, setShowGroupDetailModal] = useState(false);
  const [uploadingExpenseId, setUploadingExpenseId] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [invoiceGroups, setInvoiceGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [groupForm, setGroupForm] = useState({
    vendor_name: "",
    invoice_number: "",
    bill_date: getTodayStr(),
    total_bill_amount: "",
    notes: "",
    link_mode: "new"  // "new" or "existing"
  });
  const [existingGroupId, setExistingGroupId] = useState("");
  const fileInputRef = useRef(null);
  const groupFileInputRef = useRef(null);
  
  // Sorting state
  const [sortField, setSortField] = useState(null);
  const [sortDirection, setSortDirection] = useState("asc"); // "asc" or "desc"

  // Excel-style column filters — per column { selected: Set<string>, fromDate, toDate, minAmount, maxAmount }
  const emptyFilter = { selected: new Set(), fromDate: "", toDate: "", minAmount: "", maxAmount: "" };
  const [colFilters, setColFilters] = useState({
    date: { ...emptyFilter },
    description: { ...emptyFilter },
    expense_type: { ...emptyFilter },
    payment_mode: { ...emptyFilter },
    amount: { ...emptyFilter },
  });
  const setColumnFilter = (key, newF) => setColFilters((p) => ({ ...p, [key]: newF }));
  const clearColumnFilter = (key) => setColFilters((p) => ({ ...p, [key]: { ...emptyFilter } }));
  const clearAllColumnFilters = () => setColFilters({
    date: { ...emptyFilter },
    description: { ...emptyFilter },
    expense_type: { ...emptyFilter },
    payment_mode: { ...emptyFilter },
    amount: { ...emptyFilter },
  });
  const anyFilterActive = useMemo(() => Object.values(colFilters).some((f) => (
    (f.selected && f.selected.size > 0) || f.fromDate || f.toDate ||
    (f.minAmount !== "" && f.minAmount != null) ||
    (f.maxAmount !== "" && f.maxAmount != null)
  )), [colFilters]);
  
  // New expense form
  const [newExpense, setNewExpense] = useState({
    description: "",
    amount: "",
    expense_type: "",
    payment_mode: "CASH",
    gst_rate: 0,
    vendor_name: "",
    vendor_gstin: ""
  });
  
  // Multiple new expense rows for batch add
  const [batchExpenses, setBatchExpenses] = useState([]);
  
  // For freeze checks, use the user's actual center (not "all")
  const centerCode = selectedCenter === "all" ? session?.center : (selectedCenter || session?.center);
  const displayCenter = selectedCenter || session?.center;
  
  // Bound formatCurrency that auto-passes centersList
  const fmtCurrency = (amount, center = centerCode) => formatCurrency(amount, center, centersList);

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

  // Fetch expenses for selected date or date range
  const fetchExpenses = async () => {
    if (!centerCode || !session?.token) {
      console.log("ExpenseEntry: Skipping fetch - missing data", { centerCode, hasToken: !!session?.token });
      return;
    }
    
    setLoading(true);
    try {
      // Determine dates based on mode
      const startDate = dateMode === "range" ? fromDate : selectedDate;
      const endDate = dateMode === "range" ? toDate : selectedDate;
      
      // Check frozen status via API (using the start date for single mode)
      try {
        const frozenRes = await api.get(`/sales/check-frozen/${centerCode}/${startDate}?token=${session.token}`);
        setFrozenStatus({ 
          is_frozen: frozenRes.data.is_frozen, 
          is_admin_frozen: frozenRes.data.is_admin_frozen || false,
          can_edit: frozenRes.data.can_edit_expenses,  // Use expense-specific field
          reason: frozenRes.data.reason_expenses || frozenRes.data.reason || ""
        });
      } catch (err) {
        // Fallback to local check
        const frozen = isDateFrozen(startDate);
        const canEdit = !frozen || session?.is_super_admin;
        setFrozenStatus({ is_frozen: frozen, is_admin_frozen: false, can_edit: canEdit, reason: "" });
      }
      
      console.log("ExpenseEntry: Fetching expenses for", { centerCode, startDate, endDate, dateMode });
      const res = await api.post("/sales/expenses", {
        token: session.token,
        center: centerCode,
        start_date: startDate,
        end_date: endDate
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
      // In range mode, only fetch on explicit refresh button click (not on date picker change)
      // Exception: center change should still trigger a fresh fetch
      if (dateMode === "range") return;
      fetchExpenses();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate, dateMode, centerCode, session?.token]);

  // When center changes in range mode, still re-fetch
  useEffect(() => {
    if (session?.token && dateMode === "range") {
      fetchExpenses();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [centerCode]);

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
        payment_mode: newExpense.payment_mode || "CASH",
        gst_rate: parseFloat(newExpense.gst_rate) || 0,
        vendor_name: newExpense.vendor_name || "",
        vendor_gstin: newExpense.vendor_gstin || ""
      });
      
      console.log("ExpenseEntry: Expense added successfully", res.data);
      toast.success("Expense added successfully");
      setNewExpense({
        description: "",
        amount: "",
        expense_type: "",
        payment_mode: "CASH",
        gst_rate: 0,
        vendor_name: "",
        vendor_gstin: ""
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

  // Add 3 more blank batch rows
  const handleAddBatchRows = () => {
    const newRows = Array(3).fill(null).map((_, i) => ({
      id: Date.now() + i,
      description: "",
      amount: "",
      expense_type: "",
      payment_mode: "CASH"
    }));
    setBatchExpenses(prev => [...prev, ...newRows]);
  };

  // Update a batch row field
  const updateBatchRow = (id, field, value) => {
    setBatchExpenses(prev => prev.map(row => 
      row.id === id ? { ...row, [field]: value } : row
    ));
  };

  // Remove a batch row
  const removeBatchRow = (id) => {
    setBatchExpenses(prev => prev.filter(row => row.id !== id));
  };

  // Save all batch expenses
  const handleSaveBatch = async () => {
    const validRows = batchExpenses.filter(r => r.description.trim() && r.amount && parseFloat(r.amount) > 0 && r.expense_type);
    if (validRows.length === 0) {
      toast.error("No valid entries to save. Fill description, amount, and type.");
      return;
    }
    
    setSaving(true);
    let successCount = 0;
    let errorCount = 0;
    
    for (const row of validRows) {
      try {
        await api.post(`/sales/expenses/create?token=${session.token}`, {
          center: centerCode,
          date: selectedDate,
          description: row.description,
          amount: parseFloat(row.amount),
          expense_type: row.expense_type,
          payment_mode: row.payment_mode || "CASH"
        });
        successCount++;
      } catch (err) {
        errorCount++;
      }
    }
    
    if (successCount > 0) toast.success(`${successCount} expense(s) added successfully`);
    if (errorCount > 0) toast.error(`${errorCount} expense(s) failed`);
    
    setBatchExpenses([]);
    fetchExpenses();
    setSaving(false);
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

  // Handle inline edit for a single field
  const handleInlineEdit = (expenseId, field, value) => {
    setEditedExpenses(prev => ({
      ...prev,
      [expenseId]: {
        ...(prev[expenseId] || {}),
        [field]: value
      }
    }));
    setHasChanges(true);
  };

  // Get current value (edited or original)
  const getFieldValue = (expense, field) => {
    const edited = editedExpenses[expense.expense_id];
    if (edited && edited[field] !== undefined) {
      return edited[field];
    }
    return expense[field];
  };

  // Save all edited expenses
  const handleSaveAll = async () => {
    if (!hasChanges || Object.keys(editedExpenses).length === 0) {
      toast.info("No changes to save");
      return;
    }

    setSaving(true);
    let successCount = 0;
    let errorCount = 0;

    try {
      for (const [expenseId, changes] of Object.entries(editedExpenses)) {
        // Find original expense to merge
        const original = expenses.find(e => e.expense_id === expenseId);
        if (!original) continue;

        // Prepare update payload
        const updateData = {
          description: changes.description !== undefined ? changes.description : original.description,
          amount: changes.amount !== undefined ? parseFloat(changes.amount) : original.amount,
          expense_type: changes.expense_type !== undefined ? changes.expense_type : original.expense_type,
          payment_mode: changes.payment_mode !== undefined ? changes.payment_mode : original.payment_mode,
          date: changes.date !== undefined ? changes.date : original.date
        };

        try {
          await api.put(`/sales/expenses/${expenseId}?token=${session?.token}`, updateData);
          successCount++;
        } catch (err) {
          console.error(`Failed to update expense ${expenseId}:`, err);
          errorCount++;
        }
      }

      if (successCount > 0) {
        toast.success(`${successCount} expense(s) updated successfully`);
      }
      if (errorCount > 0) {
        toast.error(`${errorCount} expense(s) failed to update`);
      }

      // Clear edits and refresh
      setEditedExpenses({});
      setHasChanges(false);
      fetchExpenses();
    } catch (err) {
      toast.error("Failed to save changes");
    } finally {
      setSaving(false);
    }
  };

  // Cancel all edits
  const handleCancelEdits = () => {
    setEditedExpenses({});
    setHasChanges(false);
  };

  // Fetch invoice groups for current center
  const fetchInvoiceGroups = async () => {
    try {
      const res = await api.get(`/expense-attachments/invoice-groups?token=${session?.token}&center=${centerCode}`);
      if (res.data.groups) {
        setInvoiceGroups(res.data.groups);
      }
    } catch (err) {
      console.error("Failed to fetch invoice groups:", err);
    }
  };

  useEffect(() => {
    if (session?.token && centerCode) {
      fetchInvoiceGroups();
    }
  }, [session?.token, centerCode]);

  // Handle checkbox selection for bulk grouping
  const handleSelectExpense = (expenseId, checked) => {
    if (checked) {
      setSelectedExpenses(prev => [...prev, expenseId]);
    } else {
      setSelectedExpenses(prev => prev.filter(id => id !== expenseId));
    }
  };

  const handleSelectAll = (checked) => {
    if (checked) {
      setSelectedExpenses(expenses.map(e => e.expense_id));
    } else {
      setSelectedExpenses([]);
    }
  };

  // Upload attachment for a single expense
  const handleUploadAttachment = async (file, expenseId) => {
    if (!file) return;
    
    // Validate file type
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error("File type not allowed. Use PDF, JPG, PNG, or WEBP");
      return;
    }
    
    // Validate file size
    const maxSize = file.type === 'application/pdf' ? 10 * 1024 * 1024 : 5 * 1024 * 1024;
    if (file.size > maxSize) {
      toast.error(`File too large. Max: ${file.type === 'application/pdf' ? '10 MB' : '5 MB'}`);
      return;
    }
    
    setSaving(true);
    setUploadProgress(0);
    
    try {
      const formData = new FormData();
      formData.append('token', session?.token);
      formData.append('expense_id', expenseId);
      formData.append('center', centerCode);
      formData.append('file', file);
      
      const res = await api.post('/expense-attachments/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(progress);
        }
      });
      
      if (res.data.success) {
        toast.success("Attachment uploaded successfully");
        fetchExpenses();
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to upload attachment");
    } finally {
      setSaving(false);
      setUploadProgress(0);
      setShowUploadModal(false);
      setUploadingExpenseId(null);
    }
  };

  // Delete attachment
  const handleDeleteAttachment = async (attachmentId) => {
    if (!confirm("Are you sure you want to delete this attachment?")) return;
    
    setSaving(true);
    try {
      await api.delete(`/expense-attachments/attachment/${attachmentId}?token=${session?.token}`);
      toast.success("Attachment deleted");
      fetchExpenses();
    } catch (err) {
      toast.error("Failed to delete attachment");
    } finally {
      setSaving(false);
    }
  };

  // View attachment
  const viewAttachment = (attachmentId) => {
    window.open(`${api.defaults.baseURL}/expense-attachments/view/${attachmentId}?auth=${session?.token}`, '_blank');
  };

  // Download attachment
  const downloadAttachment = (attachmentId) => {
    window.open(`${api.defaults.baseURL}/expense-attachments/download/${attachmentId}?auth=${session?.token}`, '_blank');
  };

  // Create invoice group with selected expenses
  const handleCreateGroup = async () => {
    if (!groupForm.vendor_name || !groupForm.invoice_number) {
      toast.error("Vendor name and invoice number are required");
      return;
    }
    
    setSaving(true);
    try {
      const formData = new FormData();
      formData.append('token', session?.token);
      formData.append('center', centerCode);
      formData.append('vendor_name', groupForm.vendor_name);
      formData.append('invoice_number', groupForm.invoice_number);
      formData.append('bill_date', groupForm.bill_date);
      formData.append('total_bill_amount', groupForm.total_bill_amount || 0);
      formData.append('notes', groupForm.notes || '');
      formData.append('expense_ids', selectedExpenses.join(','));
      
      // If file is selected
      if (groupFileInputRef.current?.files?.[0]) {
        formData.append('file', groupFileInputRef.current.files[0]);
      }
      
      const res = await api.post('/expense-attachments/invoice-groups', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      if (res.data.success) {
        toast.success("Invoice group created successfully");
        if (res.data.warning) {
          toast.warning(res.data.warning);
        }
        setShowGroupModal(false);
        setSelectedExpenses([]);
        setGroupForm({
          vendor_name: "",
          invoice_number: "",
          bill_date: getTodayStr(),
          total_bill_amount: "",
          notes: "",
          link_mode: "new"
        });
        fetchExpenses();
        fetchInvoiceGroups();
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create invoice group");
    } finally {
      setSaving(false);
    }
  };

  // Link expenses to existing group
  const handleLinkToExistingGroup = async () => {
    if (!existingGroupId) {
      toast.error("Please select an invoice group");
      return;
    }
    
    setSaving(true);
    try {
      const res = await api.post('/expense-attachments/link-expenses', {
        token: session?.token,
        invoice_group_id: existingGroupId,
        expense_ids: selectedExpenses
      });
      
      if (res.data.success) {
        toast.success(`${res.data.linked_count} expenses linked to invoice group`);
        setShowGroupModal(false);
        setSelectedExpenses([]);
        setExistingGroupId("");
        fetchExpenses();
        fetchInvoiceGroups();
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to link expenses");
    } finally {
      setSaving(false);
    }
  };

  // Unlink expense from group
  const handleUnlinkExpense = async (expenseId) => {
    setSaving(true);
    try {
      const res = await api.post('/expense-attachments/unlink-expense', {
        token: session?.token,
        expense_id: expenseId
      });
      
      if (res.data.success) {
        toast.success("Expense unlinked from invoice group");
        fetchExpenses();
      }
    } catch (err) {
      toast.error("Failed to unlink expense");
    } finally {
      setSaving(false);
    }
  };

  // View group details
  const handleViewGroup = async (groupId) => {
    try {
      const res = await api.get(`/expense-attachments/invoice-groups/${groupId}?token=${session?.token}`);
      if (res.data.success) {
        setSelectedGroup(res.data.group);
        setShowGroupDetailModal(true);
      }
    } catch (err) {
      toast.error("Failed to load invoice group details");
    }
  };

  // Sorted expenses — first apply Excel-style column filters, then existing sort
  const filteredExpenses = useMemo(() => {
    return expenses.filter((e) => {
      // Date column
      const df = colFilters.date;
      if (df.fromDate && (e.date || "") < df.fromDate) return false;
      if (df.toDate && (e.date || "") > df.toDate) return false;
      if (df.selected.size > 0 && !df.selected.has(String(e.date || ""))) return false;
      // Description
      const f2 = colFilters.description;
      if (f2.selected.size > 0 && !f2.selected.has(String(e.description || ""))) return false;
      // Category
      const f3 = colFilters.expense_type;
      if (f3.selected.size > 0 && !f3.selected.has(String(e.expense_type || ""))) return false;
      // Mode
      const f4 = colFilters.payment_mode;
      if (f4.selected.size > 0 && !f4.selected.has(String(e.payment_mode || ""))) return false;
      // Amount
      const fa = colFilters.amount;
      const amt = Number(e.amount || 0);
      if (fa.minAmount !== "" && fa.minAmount != null && amt < Number(fa.minAmount)) return false;
      if (fa.maxAmount !== "" && fa.maxAmount != null && amt > Number(fa.maxAmount)) return false;
      if (fa.selected.size > 0 && !fa.selected.has(String(amt))) return false;
      return true;
    });
  }, [expenses, colFilters]);

  // Calculate total — uses filtered visible rows (Excel-style filters)
  const totalExpenses = useMemo(() => {
    return filteredExpenses.reduce((sum, exp) => sum + (exp.amount || 0), 0);
  }, [filteredExpenses]);

  // Group expenses by type — also based on filtered data
  const expensesByType = useMemo(() => {
    return filteredExpenses.reduce((acc, exp) => {
      const type = exp.expense_type || "OTHER";
      acc[type] = (acc[type] || 0) + (exp.amount || 0);
      return acc;
    }, {});
  }, [filteredExpenses]);

  // Merge master lists with custom values saved in existing expenses
  // This ensures saved category/mode values always appear in the dropdown
  const allExpenseTypes = useMemo(() => {
    const savedTypes = expenses.map(e => e.expense_type).filter(Boolean);
    const editedTypes = Object.values(editedExpenses).map(e => e.expense_type).filter(Boolean);
    return [...new Set([...expenseTypes, ...savedTypes, ...editedTypes])].sort();
  }, [expenseTypes, expenses, editedExpenses]);

  const allPaymentModes = useMemo(() => {
    const savedModes = expenses.map(e => e.payment_mode).filter(Boolean);
    const editedModes = Object.values(editedExpenses).map(e => e.payment_mode).filter(Boolean);
    return [...new Set([...paymentModes, ...savedModes, ...editedModes])].sort();
  }, [paymentModes, expenses, editedExpenses]);

  // Sort handler
  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(prev => prev === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  // Sorted expenses — apply existing sort to the filtered list
  const sortedExpenses = [...filteredExpenses].sort((a, b) => {
    if (!sortField) return 0;
    let aVal = a[sortField] ?? "";
    let bVal = b[sortField] ?? "";
    
    if (sortField === "amount") {
      aVal = parseFloat(aVal) || 0;
      bVal = parseFloat(bVal) || 0;
    } else if (sortField === "attachment_status") {
      // Sort by attachment status: attached > attached_via_group > none
      const order = { attached: 2, attached_via_group: 1 };
      aVal = order[aVal] || 0;
      bVal = order[bVal] || 0;
    } else if (sortField === "is_grouped") {
      aVal = a.is_grouped ? 1 : 0;
      bVal = b.is_grouped ? 1 : 0;
    } else {
      aVal = String(aVal).toLowerCase();
      bVal = String(bVal).toLowerCase();
    }
    
    if (aVal < bVal) return sortDirection === "asc" ? -1 : 1;
    if (aVal > bVal) return sortDirection === "asc" ? 1 : -1;
    return 0;
  });

  const SortIcon = ({ field }) => {
    if (sortField !== field) return <span className="text-muted-foreground/40 ml-1">↕</span>;
    return <span className="ml-1 text-primary">{sortDirection === "asc" ? "↑" : "↓"}</span>;
  };

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
            
            <div className="flex items-center gap-2 flex-wrap">
              {/* Date Mode Toggle */}
              <div className="flex items-center gap-1 bg-muted rounded-md p-1">
                <button
                  onClick={() => setDateMode("single")}
                  className={`px-3 py-1 text-sm rounded ${dateMode === "single" ? 'bg-background shadow-sm' : 'text-muted-foreground'}`}
                  data-testid="date-mode-single"
                >
                  Single
                </button>
                <button
                  onClick={() => setDateMode("range")}
                  className={`px-3 py-1 text-sm rounded ${dateMode === "range" ? 'bg-background shadow-sm' : 'text-muted-foreground'}`}
                  data-testid="date-mode-range"
                >
                  Range
                </button>
              </div>
              
              <Calendar className="w-4 h-4 text-muted-foreground" />
              
              {dateMode === "single" ? (
                <Input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="w-40"
                  data-testid="expense-date-input"
                />
              ) : (
                <>
                  <Input
                    type="date"
                    value={fromDate}
                    onChange={(e) => setFromDate(e.target.value)}
                    className="w-36"
                    data-testid="expense-from-date"
                  />
                  <span className="text-muted-foreground">to</span>
                  <Input
                    type="date"
                    value={toDate}
                    onChange={(e) => setToDate(e.target.value)}
                    className="w-36"
                    data-testid="expense-to-date"
                  />
                </>
              )}
              
              <Button variant="outline" size="icon" onClick={fetchExpenses} disabled={loading}>
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>
          
          <p className="text-sm text-muted-foreground">
            Center: <span className="font-medium text-foreground">{centerCode}</span>
            <span className="ml-4">Total: <span className="font-bold text-red-500">{fmtCurrency(totalExpenses, centerCode)}</span></span>
            {dateMode === "range" && (
              <span className="ml-4 text-xs">({expenses.length} records)</span>
            )}
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
            <div className="md:col-span-1 space-y-1">
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
                className="min-w-[140px] text-base"
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

          {/* GST / Vendor row — for ITC tagging (India). Optional but helps CA / GSTR-2 reconciliation. */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mt-3 pt-3 border-t border-dashed">
            <div className="md:col-span-2 space-y-1">
              <Label className="text-xs text-muted-foreground">Vendor Name (optional)</Label>
              <Input
                value={newExpense.vendor_name}
                onChange={(e) => setNewExpense({ ...newExpense, vendor_name: e.target.value })}
                placeholder="e.g., ABC Traders"
                data-testid="expense-vendor-name"
              />
            </div>
            <div className="md:col-span-1 space-y-1">
              <Label className="text-xs text-muted-foreground">Vendor GSTIN (optional)</Label>
              <Input
                value={newExpense.vendor_gstin}
                onChange={(e) => setNewExpense({ ...newExpense, vendor_gstin: e.target.value.toUpperCase() })}
                placeholder="29ABCDE1234F1Z5"
                maxLength={15}
                data-testid="expense-vendor-gstin"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">GST Rate</Label>
              <Select
                value={String(newExpense.gst_rate ?? 0)}
                onValueChange={(val) => setNewExpense({ ...newExpense, gst_rate: parseFloat(val) })}
              >
                <SelectTrigger data-testid="expense-gst-rate">
                  <SelectValue placeholder="0%" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">0% (No GST)</SelectItem>
                  <SelectItem value="5">5% (food / restaurants)</SelectItem>
                  <SelectItem value="12">12%</SelectItem>
                  <SelectItem value="18">18% (services / packaging)</SelectItem>
                  <SelectItem value="28">28%</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">GST Amount (auto)</Label>
              <Input
                disabled
                value={(() => {
                  const rate = parseFloat(newExpense.gst_rate) || 0;
                  const amt = parseFloat(newExpense.amount) || 0;
                  if (rate <= 0 || amt <= 0) return "0.00";
                  return ((amt * rate) / (100 + rate)).toFixed(2);
                })()}
                className="bg-muted text-muted-foreground"
                data-testid="expense-gst-amount-preview"
              />
            </div>
          </div>
          
          <div className="flex justify-end mt-4 gap-2">
            <Button
              variant="outline"
              onClick={handleAddBatchRows}
              disabled={frozenStatus.is_frozen && !frozenStatus.can_edit}
              className="gap-2"
              data-testid="add-3-more-btn"
            >
              <Plus className="w-4 h-4" /> Add 3 More Entries
            </Button>
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
          
          {/* Batch Entry Rows */}
          {batchExpenses.length > 0 && (
            <div className="mt-4 border-t pt-4 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-muted-foreground">Batch Entries ({batchExpenses.length} rows)</p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setBatchExpenses([])} className="gap-1">
                    <X className="w-3 h-3" /> Clear All
                  </Button>
                  <Button size="sm" onClick={handleSaveBatch} disabled={saving} className="gap-1 bg-green-600 hover:bg-green-700" data-testid="save-batch-btn">
                    <Save className="w-3 h-3" /> {saving ? "Saving..." : "Save All"}
                  </Button>
                </div>
              </div>
              {batchExpenses.map((row, idx) => (
                <div key={row.id} className="grid grid-cols-1 md:grid-cols-6 gap-2 items-end bg-muted/30 p-2 rounded">
                  <div className="md:col-span-2">
                    <Input
                      value={row.description}
                      onChange={(e) => updateBatchRow(row.id, 'description', e.target.value)}
                      placeholder="Description"
                      className="h-8 text-sm"
                      data-testid={`batch-desc-${idx}`}
                    />
                  </div>
                  <Input
                    type="text"
                    inputMode="decimal"
                    value={row.amount}
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val === "" || /^[0-9]*\.?[0-9]*$/.test(val)) {
                        updateBatchRow(row.id, 'amount', val);
                      }
                    }}
                    placeholder="Amount"
                    className="h-8 text-sm min-w-[120px]"
                    data-testid={`batch-amount-${idx}`}
                  />
                  <Select value={row.expense_type} onValueChange={(val) => updateBatchRow(row.id, 'expense_type', val)}>
                    <SelectTrigger className="h-8 text-xs" data-testid={`batch-type-${idx}`}>
                      <SelectValue placeholder="Type" />
                    </SelectTrigger>
                    <SelectContent>
                      {expenseTypes.map(type => (
                        <SelectItem key={type} value={type}>{type}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select value={row.payment_mode} onValueChange={(val) => updateBatchRow(row.id, 'payment_mode', val)}>
                    <SelectTrigger className="h-8 text-xs" data-testid={`batch-mode-${idx}`}>
                      <SelectValue placeholder="Mode" />
                    </SelectTrigger>
                    <SelectContent>
                      {paymentModes.map(mode => (
                        <SelectItem key={mode} value={mode}>{mode}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button variant="ghost" size="sm" onClick={() => removeBatchRow(row.id)} className="h-8 w-8 p-0 text-red-500">
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
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
                    <p className="text-lg font-bold text-foreground">{fmtCurrency(amount, centerCode)}</p>
                  </div>
                ))
              }
            </div>
          </CardContent>
        </Card>
      )}

      {/* Expenses List - Editable Table */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <CardTitle className="text-base">
              {dateMode === "single" 
                ? `Expenses for ${new Date(selectedDate).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}`
                : `Expenses from ${new Date(fromDate).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })} to ${new Date(toDate).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}`
              }
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                ({filteredExpenses.length}{anyFilterActive ? ` of ${expenses.length}` : ""} entries)
              </span>
            </CardTitle>
            
            <div className="flex items-center gap-2 flex-wrap">
              {/* Clear all column filters */}
              {anyFilterActive && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={clearAllColumnFilters}
                  className="gap-1 text-amber-700 border-amber-300 hover:bg-amber-50"
                  data-testid="clear-all-filters-btn"
                >
                  <FilterX className="w-4 h-4" /> Clear All Filters
                </Button>
              )}
              {/* Bulk Group Button */}
              {selectedExpenses.length > 0 && frozenStatus.can_edit && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowGroupModal(true)}
                  className="gap-1"
                  data-testid="group-selected-btn"
                >
                  <Link2 className="w-4 h-4" /> Group {selectedExpenses.length} Selected
                </Button>
              )}
              
              {/* Save All / Cancel Buttons */}
              {hasChanges && frozenStatus.can_edit && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCancelEdits}
                    className="gap-1"
                    data-testid="cancel-edits-btn"
                  >
                    <X className="w-4 h-4" /> Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleSaveAll}
                    disabled={saving}
                    className="gap-1 bg-green-600 hover:bg-green-700"
                    data-testid="save-all-btn"
                  >
                    <Save className="w-4 h-4" /> {saving ? "Saving..." : "Save All"}
                  </Button>
                </>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {frozenStatus.can_edit && (
                    <th className="text-center py-3 px-2 w-8">
                      <Checkbox 
                        checked={selectedExpenses.length === expenses.length && expenses.length > 0}
                        onCheckedChange={handleSelectAll}
                        data-testid="select-all-checkbox"
                      />
                    </th>
                  )}
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground w-10">#</th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground w-28">
                    <span className="inline-flex items-center cursor-pointer hover:text-foreground select-none" onClick={() => handleSort("date")} data-testid="sort-date">
                      Date<SortIcon field="date" />
                    </span>
                    <ColumnFilterMenu
                      rows={expenses}
                      accessor={(r) => r.date}
                      formatLabel={(v) => v ? new Date(v).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : "(Blanks)"}
                      variant="date"
                      filter={colFilters.date}
                      onApply={(f) => { setColumnFilter("date", f); }}
                      onClear={() => clearColumnFilter("date")}
                      onSort={(dir) => { setSortField("date"); setSortDirection(dir); }}
                      currentSort={sortField === "date" ? sortDirection : null}
                      testIdBase="col-filter-date"
                    />
                  </th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">
                    <span className="inline-flex items-center cursor-pointer hover:text-foreground select-none" onClick={() => handleSort("description")} data-testid="sort-description">
                      Description<SortIcon field="description" />
                    </span>
                    <ColumnFilterMenu
                      rows={expenses}
                      accessor={(r) => r.description}
                      variant="text"
                      filter={colFilters.description}
                      onApply={(f) => setColumnFilter("description", f)}
                      onClear={() => clearColumnFilter("description")}
                      onSort={(dir) => { setSortField("description"); setSortDirection(dir); }}
                      currentSort={sortField === "description" ? sortDirection : null}
                      testIdBase="col-filter-description"
                    />
                  </th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground w-36">
                    <span className="inline-flex items-center cursor-pointer hover:text-foreground select-none" onClick={() => handleSort("expense_type")} data-testid="sort-category">
                      Category<SortIcon field="expense_type" />
                    </span>
                    <ColumnFilterMenu
                      rows={expenses}
                      accessor={(r) => r.expense_type}
                      variant="text"
                      filter={colFilters.expense_type}
                      onApply={(f) => setColumnFilter("expense_type", f)}
                      onClear={() => clearColumnFilter("expense_type")}
                      onSort={(dir) => { setSortField("expense_type"); setSortDirection(dir); }}
                      currentSort={sortField === "expense_type" ? sortDirection : null}
                      testIdBase="col-filter-category"
                    />
                  </th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground w-32">
                    <span className="inline-flex items-center cursor-pointer hover:text-foreground select-none" onClick={() => handleSort("payment_mode")} data-testid="sort-mode">
                      Mode<SortIcon field="payment_mode" />
                    </span>
                    <ColumnFilterMenu
                      rows={expenses}
                      accessor={(r) => r.payment_mode}
                      variant="text"
                      filter={colFilters.payment_mode}
                      onApply={(f) => setColumnFilter("payment_mode", f)}
                      onClear={() => clearColumnFilter("payment_mode")}
                      onSort={(dir) => { setSortField("payment_mode"); setSortDirection(dir); }}
                      currentSort={sortField === "payment_mode" ? sortDirection : null}
                      testIdBase="col-filter-mode"
                    />
                  </th>
                  <th className="text-right py-3 px-2 font-medium text-muted-foreground w-40">
                    <span className="inline-flex items-center cursor-pointer hover:text-foreground select-none" onClick={() => handleSort("amount")} data-testid="sort-amount">
                      Amount<SortIcon field="amount" />
                    </span>
                    <ColumnFilterMenu
                      rows={expenses}
                      accessor={(r) => Number(r.amount || 0)}
                      formatLabel={(v) => fmtCurrency(Number(v || 0), centerCode)}
                      variant="amount"
                      filter={colFilters.amount}
                      onApply={(f) => setColumnFilter("amount", f)}
                      onClear={() => clearColumnFilter("amount")}
                      onSort={(dir) => { setSortField("amount"); setSortDirection(dir); }}
                      currentSort={sortField === "amount" ? sortDirection : null}
                      align="end"
                      testIdBase="col-filter-amount"
                    />
                  </th>
                  <th className="text-center py-3 px-2 font-medium text-muted-foreground w-24 cursor-pointer hover:text-foreground select-none" onClick={() => handleSort("is_grouped")} data-testid="sort-invoice">
                    Invoice<SortIcon field="is_grouped" />
                  </th>
                  <th className="text-center py-3 px-2 font-medium text-muted-foreground w-20 cursor-pointer hover:text-foreground select-none" onClick={() => handleSort("attachment_status")} data-testid="sort-bill">
                    Bill<SortIcon field="attachment_status" />
                  </th>
                  <th className="text-center py-3 px-2 font-medium text-muted-foreground w-16">
                    {frozenStatus.can_edit ? 'Actions' : ''}
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedExpenses.map((exp, idx) => (
                  <tr key={exp.expense_id || idx} className={`border-b border-border/50 ${editedExpenses[exp.expense_id] ? 'bg-amber-50/50' : 'hover:bg-muted/50'} ${selectedExpenses.includes(exp.expense_id) ? 'bg-blue-50/50' : ''}`}>
                    {/* Checkbox for selection */}
                    {frozenStatus.can_edit && (
                      <td className="text-center py-2 px-2">
                        <Checkbox 
                          checked={selectedExpenses.includes(exp.expense_id)}
                          onCheckedChange={(checked) => handleSelectExpense(exp.expense_id, checked)}
                          data-testid={`select-expense-${idx}`}
                        />
                      </td>
                    )}
                    
                    <td className="py-2 px-2 text-muted-foreground">{idx + 1}</td>
                    
                    {/* Date - Editable */}
                    <td className="py-2 px-2">
                      {frozenStatus.can_edit ? (
                        <Input
                          type="date"
                          value={getFieldValue(exp, 'date')?.substring(0, 10) || ''}
                          onChange={(e) => handleInlineEdit(exp.expense_id, 'date', e.target.value)}
                          className="h-8 text-xs"
                          data-testid={`edit-date-${idx}`}
                        />
                      ) : (
                        <span className="text-sm">
                          {exp.date ? new Date(exp.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) : '-'}
                        </span>
                      )}
                    </td>
                    
                    {/* Description - Editable */}
                    <td className="py-2 px-2">
                      {frozenStatus.can_edit ? (
                        <Input
                          type="text"
                          value={getFieldValue(exp, 'description') || ''}
                          onChange={(e) => handleInlineEdit(exp.expense_id, 'description', e.target.value)}
                          className="h-8 text-xs"
                          data-testid={`edit-description-${idx}`}
                        />
                      ) : (
                        <span>{exp.description}</span>
                      )}
                    </td>
                    
                    {/* Category - Editable */}
                    <td className="py-2 px-2">
                      {frozenStatus.can_edit ? (
                        <Select
                          value={getFieldValue(exp, 'expense_type') || ''}
                          onValueChange={(val) => handleInlineEdit(exp.expense_id, 'expense_type', val)}
                        >
                          <SelectTrigger className="h-8 text-xs" data-testid={`edit-category-${idx}`}>
                            <SelectValue placeholder="Category" />
                          </SelectTrigger>
                          <SelectContent>
                            {allExpenseTypes.map(type => (
                              <SelectItem key={type} value={type}>{type}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        <span className="px-2 py-1 rounded-full text-xs bg-muted">{exp.expense_type}</span>
                      )}
                    </td>
                    
                    {/* Payment Mode - Editable */}
                    <td className="py-2 px-2">
                      {frozenStatus.can_edit ? (
                        <Select
                          value={getFieldValue(exp, 'payment_mode') || ''}
                          onValueChange={(val) => handleInlineEdit(exp.expense_id, 'payment_mode', val)}
                        >
                          <SelectTrigger className="h-8 text-xs" data-testid={`edit-mode-${idx}`}>
                            <SelectValue placeholder="Mode" />
                          </SelectTrigger>
                          <SelectContent>
                            {allPaymentModes.map(mode => (
                              <SelectItem key={mode} value={mode}>{mode}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        <span className="text-xs">{exp.payment_mode}</span>
                      )}
                    </td>
                    
                    {/* Amount - Editable */}
                    <td className="py-2 px-2 text-right">
                      {frozenStatus.can_edit ? (
                        <Input
                          type="number"
                          value={getFieldValue(exp, 'amount') || ''}
                          onChange={(e) => handleInlineEdit(exp.expense_id, 'amount', e.target.value)}
                          className="h-8 text-sm text-right w-full min-w-[120px]"
                          data-testid={`edit-amount-${idx}`}
                        />
                      ) : (
                        <span className="font-medium">{fmtCurrency(exp.amount, centerCode)}</span>
                      )}
                    </td>
                    
                    {/* Invoice Group Column */}
                    <td className="py-2 px-2 text-center">
                      {exp.is_grouped ? (
                        <button
                          onClick={() => handleViewGroup(exp.invoice_group_id)}
                          className="text-xs text-blue-600 hover:underline flex items-center gap-1 mx-auto"
                          title={`${exp.group_info?.vendor_name} - ${exp.group_info?.invoice_number}`}
                        >
                          <FolderOpen className="w-3 h-3" />
                          <span className="truncate max-w-[60px]">{exp.group_info?.vendor_name?.substring(0,8) || 'Grouped'}</span>
                        </button>
                      ) : frozenStatus.can_edit ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedExpenses([exp.expense_id]);
                            setShowGroupModal(true);
                          }}
                          className="h-7 text-xs px-2"
                          title="Link to Invoice"
                        >
                          <Link2 className="w-3 h-3" />
                        </Button>
                      ) : (
                        <Badge variant="outline" className="text-xs">Ungrouped</Badge>
                      )}
                    </td>
                    
                    {/* Attachment Column — clickable to view */}
                    <td className="py-2 px-2 text-center">
                      {exp.attachment_status === 'attached' ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 gap-1 hover:bg-green-50"
                          title={`View ${exp.attachment_count || 1} attachment(s)`}
                          data-testid={`view-bill-${exp.expense_id}`}
                          onClick={() => {
                            const atts = exp.direct_attachments || [];
                            if (atts.length === 0) {
                              toast.error("No attachment to view");
                            } else if (atts.length === 1) {
                              viewAttachment(atts[0].attachment_id);
                            } else {
                              // Multiple: open all tabs
                              atts.forEach(a => viewAttachment(a.attachment_id));
                            }
                          }}
                        >
                          <Badge className="bg-green-100 text-green-800 text-xs gap-1 cursor-pointer hover:bg-green-200">
                            <Eye className="w-3 h-3" />
                            View ({exp.attachment_count || 1})
                          </Badge>
                        </Button>
                      ) : exp.attachment_status === 'attached_via_group' ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 gap-1 hover:bg-blue-50"
                          title={`Open invoice group (${exp.attachment_count || 0} bill)`}
                          data-testid={`view-group-${exp.expense_id}`}
                          onClick={() => {
                            const atts = exp.group_attachments || [];
                            if (atts.length === 0) {
                              // Fall back: open group detail modal
                              if (exp.invoice_group_id && typeof handleViewGroup === 'function') {
                                handleViewGroup(exp.invoice_group_id);
                              } else {
                                toast.info("Attachment in an invoice group");
                              }
                            } else if (atts.length === 1) {
                              viewAttachment(atts[0].attachment_id);
                            } else {
                              atts.forEach(a => viewAttachment(a.attachment_id));
                            }
                          }}
                        >
                          <Badge className="bg-blue-100 text-blue-800 text-xs gap-1 cursor-pointer hover:bg-blue-200" title="Attached via Invoice Group">
                            <FolderOpen className="w-3 h-3" />
                            Grp ({exp.attachment_count || ""})
                          </Badge>
                        </Button>
                      ) : (
                        <Badge variant="outline" className="text-xs text-red-600 border-red-300 gap-1">
                          <AlertTriangle className="w-3 h-3" />
                          None
                        </Badge>
                      )}
                    </td>
                    
                    {/* Actions */}
                    <td className="text-center py-2 px-2">
                      <div className="flex items-center justify-center gap-1">
                        {frozenStatus.can_edit && (
                          <>
                            {/* Upload attachment button */}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setUploadingExpenseId(exp.expense_id);
                                setShowUploadModal(true);
                              }}
                              className="h-7 w-7 p-0 text-blue-500 hover:text-blue-700 hover:bg-blue-50"
                              title="Attach Bill"
                            >
                              <Paperclip className="w-4 h-4" />
                            </Button>
                            
                            {/* Unlink from group (if grouped) */}
                            {exp.is_grouped && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleUnlinkExpense(exp.expense_id)}
                                className="h-7 w-7 p-0 text-amber-500 hover:text-amber-700 hover:bg-amber-50"
                                title="Unlink from Group"
                              >
                                <X className="w-4 h-4" />
                              </Button>
                            )}
                            
                            {/* Delete button */}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteExpense(exp.expense_id)}
                              className="h-7 w-7 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                              data-testid={`delete-expense-${idx}`}
                              disabled={saving}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </>
                        )}
                        
                        {!frozenStatus.can_edit && (
                          <Lock className="w-4 h-4 text-muted-foreground" title="Frozen - Cannot edit" />
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {expenses.length === 0 && (
                  <tr>
                    <td colSpan={frozenStatus.can_edit ? 10 : 9} className="text-center py-8 text-muted-foreground">
                      No expenses recorded for this {dateMode === "range" ? "period" : "date"}
                    </td>
                  </tr>
                )}
              </tbody>
              {expenses.length > 0 && (
                <tfoot>
                  <tr className="bg-muted/50">
                    <td colSpan={frozenStatus.can_edit ? 7 : 6} className="py-3 px-2 font-bold text-right">Total:</td>
                    <td className="py-3 px-2 font-bold text-right text-red-500">{fmtCurrency(totalExpenses, centerCode)}</td>
                    <td colSpan={2}></td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
          
          {/* Save All button at bottom for convenience */}
          {hasChanges && frozenStatus.can_edit && expenses.length > 5 && (
            <div className="flex justify-end gap-2 mt-4 pt-4 border-t">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCancelEdits}
                className="gap-1"
              >
                <X className="w-4 h-4" /> Cancel Changes
              </Button>
              <Button
                size="sm"
                onClick={handleSaveAll}
                disabled={saving}
                className="gap-1 bg-green-600 hover:bg-green-700"
              >
                <Save className="w-4 h-4" /> {saving ? "Saving..." : "Save All Changes"}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upload Attachment Modal */}
      <Dialog open={showUploadModal} onOpenChange={setShowUploadModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Upload className="w-5 h-5" /> Upload Bill / Invoice
            </DialogTitle>
            <DialogDescription>
              Attach a bill or invoice proof for this expense. Supported: PDF (max 10MB), Images (max 5MB)
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="border-2 border-dashed border-muted rounded-lg p-6 text-center">
              <input
                type="file"
                ref={fileInputRef}
                accept=".pdf,.jpg,.jpeg,.png,.webp"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) {
                    handleUploadAttachment(e.target.files[0], uploadingExpenseId);
                  }
                }}
              />
              <Button
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                disabled={saving}
                className="gap-2"
              >
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Uploading... {uploadProgress}%
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" /> Choose File
                  </>
                )}
              </Button>
              <p className="text-xs text-muted-foreground mt-2">
                PDF, JPG, PNG, WEBP
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUploadModal(false)}>Cancel</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Invoice Group Modal */}
      <Dialog open={showGroupModal} onOpenChange={setShowGroupModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Link2 className="w-5 h-5" /> Link Expenses to Invoice
            </DialogTitle>
            <DialogDescription>
              Group {selectedExpenses.length} expense(s) under one common invoice/bill
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {/* Link Mode Toggle */}
            <div className="flex items-center gap-2 bg-muted rounded-lg p-1">
              <button
                onClick={() => setGroupForm(p => ({ ...p, link_mode: 'new' }))}
                className={`flex-1 py-2 px-4 rounded text-sm font-medium ${groupForm.link_mode === 'new' ? 'bg-background shadow' : 'text-muted-foreground'}`}
              >
                Create New Invoice Group
              </button>
              <button
                onClick={() => setGroupForm(p => ({ ...p, link_mode: 'existing' }))}
                className={`flex-1 py-2 px-4 rounded text-sm font-medium ${groupForm.link_mode === 'existing' ? 'bg-background shadow' : 'text-muted-foreground'}`}
              >
                Link to Existing
              </button>
            </div>

            {groupForm.link_mode === 'new' ? (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <Label>Vendor Name *</Label>
                    <Input
                      value={groupForm.vendor_name}
                      onChange={(e) => setGroupForm(p => ({ ...p, vendor_name: e.target.value }))}
                      placeholder="e.g., Woolworths"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label>Invoice Number *</Label>
                    <Input
                      value={groupForm.invoice_number}
                      onChange={(e) => setGroupForm(p => ({ ...p, invoice_number: e.target.value }))}
                      placeholder="e.g., INV-12345"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <Label>Bill Date</Label>
                    <Input
                      type="date"
                      value={groupForm.bill_date}
                      onChange={(e) => setGroupForm(p => ({ ...p, bill_date: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label>Total Bill Amount</Label>
                    <Input
                      type="number"
                      value={groupForm.total_bill_amount}
                      onChange={(e) => setGroupForm(p => ({ ...p, total_bill_amount: e.target.value }))}
                      placeholder="0.00"
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <Label>Notes (Optional)</Label>
                  <Input
                    value={groupForm.notes}
                    onChange={(e) => setGroupForm(p => ({ ...p, notes: e.target.value }))}
                    placeholder="Additional notes..."
                  />
                </div>
                <div className="space-y-1">
                  <Label>Attach Invoice (Optional)</Label>
                  <input
                    type="file"
                    ref={groupFileInputRef}
                    accept=".pdf,.jpg,.jpeg,.png,.webp"
                    className="text-sm"
                  />
                </div>
                
                {/* Selected expenses summary */}
                <div className="p-3 bg-muted rounded-lg text-sm">
                  <p className="font-medium">Selected Expenses: {selectedExpenses.length}</p>
                  <p className="text-muted-foreground">
                    Total Amount: {fmtCurrency(
                      expenses.filter(e => selectedExpenses.includes(e.expense_id)).reduce((s, e) => s + (e.amount || 0), 0),
                      centerCode
                    )}
                  </p>
                </div>
              </>
            ) : (
              <>
                <div className="space-y-1">
                  <Label>Select Existing Invoice Group</Label>
                  <Select value={existingGroupId} onValueChange={setExistingGroupId}>
                    <SelectTrigger>
                      <SelectValue placeholder="Choose an invoice group" />
                    </SelectTrigger>
                    <SelectContent>
                      {invoiceGroups.map(g => (
                        <SelectItem key={g.group_id} value={g.group_id}>
                          {g.vendor_name} - {g.invoice_number} ({g.bill_date})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {existingGroupId && (
                  <div className="p-3 bg-muted rounded-lg text-sm">
                    {(() => {
                      const group = invoiceGroups.find(g => g.group_id === existingGroupId);
                      return group ? (
                        <>
                          <p><strong>Vendor:</strong> {group.vendor_name}</p>
                          <p><strong>Invoice #:</strong> {group.invoice_number}</p>
                          <p><strong>Bill Amount:</strong> {fmtCurrency(group.total_bill_amount, centerCode)}</p>
                          <p><strong>Already Linked:</strong> {group.linked_expense_count} expenses</p>
                        </>
                      ) : null;
                    })()}
                  </div>
                )}
              </>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setShowGroupModal(false);
              setSelectedExpenses([]);
            }}>Cancel</Button>
            <Button 
              onClick={groupForm.link_mode === 'new' ? handleCreateGroup : handleLinkToExistingGroup}
              disabled={saving}
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Link2 className="w-4 h-4 mr-2" />}
              {groupForm.link_mode === 'new' ? 'Create Group' : 'Link to Group'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Invoice Group Detail Modal */}
      <Dialog open={showGroupDetailModal} onOpenChange={setShowGroupDetailModal}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FolderOpen className="w-5 h-5" /> Invoice Group Details
            </DialogTitle>
          </DialogHeader>
          {selectedGroup && (
            <div className="space-y-4">
              {/* Group Info */}
              <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-lg">
                <div>
                  <p className="text-xs text-muted-foreground">Vendor</p>
                  <p className="font-medium">{selectedGroup.vendor_name}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Invoice Number</p>
                  <p className="font-medium">{selectedGroup.invoice_number}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Bill Date</p>
                  <p className="font-medium">{selectedGroup.bill_date}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Bill Amount</p>
                  <p className="font-medium">{fmtCurrency(selectedGroup.total_bill_amount, centerCode)}</p>
                </div>
              </div>

              {/* Amount Comparison */}
              <div className={`p-4 rounded-lg border ${selectedGroup.amount_match === 'exact' ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'}`}>
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-sm font-medium">Linked Expense Total</p>
                    <p className="text-lg font-bold">{fmtCurrency(selectedGroup.linked_expense_total, centerCode)}</p>
                  </div>
                  <div className="text-center">
                    {selectedGroup.amount_match === 'exact' ? (
                      <Badge className="bg-green-100 text-green-800">
                        <CheckCircle2 className="w-4 h-4 mr-1" /> Exact Match
                      </Badge>
                    ) : (
                      <Badge className="bg-amber-100 text-amber-800">
                        <AlertTriangle className="w-4 h-4 mr-1" /> Mismatch: {fmtCurrency(selectedGroup.amount_difference, centerCode)}
                      </Badge>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">Invoice Amount</p>
                    <p className="text-lg font-bold">{fmtCurrency(selectedGroup.total_bill_amount, centerCode)}</p>
                  </div>
                </div>
              </div>

              {/* Category Breakdown */}
              {selectedGroup.category_breakdown && Object.keys(selectedGroup.category_breakdown).length > 0 && (
                <div>
                  <p className="text-sm font-medium mb-2">Category Breakdown</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(selectedGroup.category_breakdown).map(([cat, amt]) => (
                      <Badge key={cat} variant="outline">
                        {cat}: {fmtCurrency(amt, centerCode)}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Linked Expenses */}
              <div>
                <p className="text-sm font-medium mb-2">Linked Expenses ({selectedGroup.linked_expenses?.length || 0})</p>
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-muted">
                      <tr>
                        <th className="text-left py-2 px-3">Date</th>
                        <th className="text-left py-2 px-3">Description</th>
                        <th className="text-left py-2 px-3">Category</th>
                        <th className="text-right py-2 px-3">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedGroup.linked_expenses?.map((exp, idx) => (
                        <tr key={exp.expense_id || idx} className="border-t">
                          <td className="py-2 px-3">{exp.date}</td>
                          <td className="py-2 px-3">{exp.description}</td>
                          <td className="py-2 px-3">{exp.expense_type}</td>
                          <td className="py-2 px-3 text-right">{fmtCurrency(exp.amount, centerCode)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Attachments */}
              {selectedGroup.attachment_details?.length > 0 && (
                <div>
                  <p className="text-sm font-medium mb-2">Attachments</p>
                  <div className="flex flex-wrap gap-2">
                    {selectedGroup.attachment_details.map(att => (
                      <Button
                        key={att.attachment_id}
                        variant="outline"
                        size="sm"
                        onClick={() => viewAttachment(att.attachment_id)}
                        className="gap-1"
                      >
                        <FileText className="w-4 h-4" />
                        {att.original_filename?.substring(0, 20)}
                      </Button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowGroupDetailModal(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
