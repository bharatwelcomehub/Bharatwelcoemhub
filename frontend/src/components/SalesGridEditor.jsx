import { useState, useEffect, useCallback, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { 
  Save, 
  Table2, 
  RefreshCw, 
  ClipboardPaste, 
  Download,
  Upload,
  Lock,
  Unlock,
  AlertCircle,
  Check,
  X
} from "lucide-react";
import { api, isInternationalCenter } from "@/lib/api";

// Check if center is international (non-India) — DB-driven via centersList
const isIntl = (center, centersList = []) => isInternationalCenter(center, centersList);

// Get currency symbol based on center data
const getCurrencySymbol = (center, centersList = []) => isIntl(center, centersList) ? "$" : "₹";

// Format date for display
const formatDateDisplay = (dateStr) => {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
};

// Get days in month
const getDaysInMonth = (year, month) => {
  return new Date(year, month, 0).getDate();
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

// Editable fields configuration - matches Excel "Sale's Cash Summery" columns
const EDITABLE_FIELDS = [
  { key: 'deposited_in_bank', label: 'Deposited', type: 'number' },
  { key: 'cash_receipts', label: 'Cash Rcpt', type: 'number' },
  { key: 'total_sale', label: 'Total Sale', type: 'number' },
  { key: 'card_idfc', label: 'Card', type: 'number' },
  { key: 'bharat_pay', label: 'UPI', type: 'number' },
  { key: 'swiggy', label: 'Swiggy', type: 'number' },
  { key: 'zomato', label: 'Zomato', type: 'number' },
  { key: 'doordash', label: 'Doordash', type: 'number' },
  { key: 'online_other', label: 'Online', type: 'number' },
  { key: 'due_amount', label: 'Due', type: 'number' },
  { key: 'cash_expense', label: 'Cash Exp', type: 'number', readOnly: true },
  { key: 'num_guests', label: 'Guests', type: 'integer' },
  { key: 'num_bills', label: 'Bills', type: 'integer' },
];

// Special fields: editable ONLY for day 1 of the month (green bg)
const DAY1_FIELDS = [
  { key: 'opening_balance', label: 'Opening Bal', type: 'number' },
  { key: 'petty_cash_opening', label: 'Petty Open', type: 'number' },
];

// Calculated fields (auto-computed, shown in grid as gray/locked)
const CALCULATED_FIELDS = [
  { key: 'total_online_sale', label: 'Online Total', computed: true },
  { key: 'total_cash_sale', label: 'Cash Sale', computed: true },
  { key: 'closing_balance', label: 'Closing Bal', computed: true },
  { key: 'to_deposit_in_bank', label: 'To Deposit', computed: true },
  { key: 'petty_cash_closing', label: 'Petty Close', computed: true },
];

export default function SalesGridEditor({ session, selectedCenter, selectedMonth, centersList = [] }) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [gridData, setGridData] = useState([]);
  const [modifiedRows, setModifiedRows] = useState(new Set());
  const [editingCell, setEditingCell] = useState(null); // { row: index, field: key }
  const [frozenStatus, setFrozenStatus] = useState({});
  const [editValue, setEditValue] = useState(''); // Local edit value to prevent re-renders
  const inputRef = useRef(null);

  // Get center code - use session center if selectedCenter is "all" or not set
  const centerCode = (selectedCenter && selectedCenter !== "all") ? selectedCenter : session?.center;
  const currencySymbol = getCurrencySymbol(centerCode, centersList);

  // Generate all dates for the month
  const generateMonthDates = useCallback(() => {
    if (!selectedMonth) return [];
    const [year, month] = selectedMonth.split('-').map(Number);
    const daysInMonth = getDaysInMonth(year, month);
    const dates = [];
    for (let day = 1; day <= daysInMonth; day++) {
      dates.push(`${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`);
    }
    return dates;
  }, [selectedMonth]);

  // Fetch all sales data for the month
  const fetchGridData = async () => {
    if (!selectedMonth || !centerCode || !session?.token) {
      console.log("SalesGridEditor: Skipping fetch - missing data");
      return;
    }

    setLoading(true);
    try {
      // Fetch sales data for the month
      const res = await api.post("/sales/daily", {
        token: session.token,
        center: centerCode,
        month: selectedMonth
      });

      // Also fetch previous month's last day for opening balance carry-forward
      const [yr, mo] = selectedMonth.split("-").map(Number);
      const prevMonth = mo === 1 ? `${yr - 1}-12` : `${yr}-${String(mo - 1).padStart(2, "0")}`;
      let prevMonthClosing = 0;
      let prevMonthPettyCashClosing = 0;
      try {
        const prevRes = await api.post("/sales/daily", {
          token: session.token,
          center: centerCode,
          month: prevMonth
        });
        const prevSales = (prevRes.data.sales || []).sort((a, b) => b.date.localeCompare(a.date));
        if (prevSales.length > 0) {
          prevMonthClosing = prevSales[0].closing_balance || 0;
          prevMonthPettyCashClosing = prevSales[0].petty_cash_closing || 0;
        }
      } catch (e) {
        console.log("Could not fetch previous month data for opening balance");
      }

      const salesData = res.data.sales || [];
      const allDates = generateMonthDates();
      
      // Fetch CASH expenses per date to auto-fill Cash Exp column
      let cashExpByDate = {};
      try {
        const expRes = await api.post("/sales/expenses-by-date", {
          token: session.token,
          center: centerCode,
          month: selectedMonth,
          payment_mode: "CASH"
        });
        cashExpByDate = expRes.data.expenses_by_date || {};
      } catch (e) {
        console.log("Could not fetch cash expenses for grid");
      }
      
      // Create a map of existing data
      const salesMap = {};
      salesData.forEach(sale => {
        salesMap[sale.date] = sale;
      });

      // Optimize: Check frozen status locally first, only API call for Super Admin unlock status
      // This reduces 31 API calls to just checking unlock_grants
      const frozenMap = {};
      const isSuperAdmin = session?.is_super_admin;
      
      // Build frozen status based on date comparison (fast local check)
      allDates.forEach(date => {
        const frozen = isDateFrozen(date);
        frozenMap[date] = {
          is_frozen: frozen,
          can_edit: !frozen || isSuperAdmin,  // Super Admin can always edit
          is_admin_frozen: false
        };
      });
      
      // For non-super admin users, check if any frozen dates have unlock grants
      if (!isSuperAdmin) {
        try {
          // Single API call to check frozen status for the month
          const frozenRes = await api.get(`/sales/admin/freeze-status?token=${session.token}&month=${selectedMonth}&center=${centerCode}`);
          const adminFrozenDates = new Set(frozenRes.data.admin_frozen_dates || []);
          const unlockedDates = new Set(frozenRes.data.unlocked_dates || []);
          
          allDates.forEach(date => {
            const frozen = isDateFrozen(date);
            frozenMap[date] = {
              is_frozen: frozen || adminFrozenDates.has(date),
              can_edit: !frozen || unlockedDates.has(date),
              is_admin_frozen: adminFrozenDates.has(date)
            };
          });
        } catch (err) {
          console.log("Could not fetch admin freeze status, using local check");
        }
      }
      
      setFrozenStatus(frozenMap);

      // Build grid data with all dates
      const grid = allDates.map(date => {
        const existing = salesMap[date] || {};
        // Override cash_expense with actual CASH expenses from expense entries
        const actualCashExp = cashExpByDate[date] !== undefined ? cashExpByDate[date] : (existing.cash_expense || 0);
        return {
          date,
          ...getDefaultRow(),
          ...existing,
          cash_expense: actualCashExp,
          _isNew: !salesMap[date],
          _original: { ...existing }
        };
      });

      // Chain opening balances: first row uses DB value or previous month's closing
      // Only apply previous month's closing if first row has NO saved opening_balance
      if (grid.length > 0) {
        const firstRow = grid[0];
        const hasDbOpening = firstRow.opening_balance !== undefined && firstRow.opening_balance !== null && firstRow.opening_balance !== 0 && !firstRow._isNew;
        if (!hasDbOpening && prevMonthClosing !== undefined) {
          grid[0].opening_balance = prevMonthClosing;
        }
        if (firstRow._isNew && prevMonthPettyCashClosing !== undefined) {
          grid[0].petty_cash_opening = prevMonthPettyCashClosing;
        } else if (!firstRow.petty_cash_opening && prevMonthPettyCashClosing !== undefined) {
          grid[0].petty_cash_opening = prevMonthPettyCashClosing;
        }
        grid[0] = { ...calculateRow(grid[0]), _isNew: grid[0]._isNew, _original: grid[0]._original };
      }
      for (let i = 1; i < grid.length; i++) {
        const prevRow = grid[i - 1];
        if (prevRow.closing_balance !== undefined && prevRow.closing_balance !== null) {
          grid[i].opening_balance = prevRow.closing_balance;
        }
        if (prevRow.petty_cash_closing !== undefined && prevRow.petty_cash_closing !== null) {
          grid[i].petty_cash_opening = prevRow.petty_cash_closing;
        }
        // Recalculate this row with corrected opening
        grid[i] = { ...calculateRow(grid[i]), _isNew: grid[i]._isNew, _original: grid[i]._original };
      }

      setGridData(grid);
      setModifiedRows(new Set());
    } catch (err) {
      console.error("SalesGridEditor: Failed to fetch data:", err);
      toast.error("Failed to load grid data");
    } finally {
      setLoading(false);
    }
  };

  // Get default row values
  const getDefaultRow = () => ({
    total_sale: 0,
    swiggy: 0,
    zomato: 0,
    doordash: 0,
    card_idfc: 0,
    bharat_pay: 0,
    online_other: 0,
    due_amount: 0,
    num_guests: 0,
    num_bills: 0,
    opening_balance: 0,
    petty_cash_opening: 0,
    deposited_in_bank: 0,
    cash_receipts: 0,
    cash_expense: 0
  });

  // Calculate derived fields for a row — TWO SEPARATE TRACKS
  // Track A (To Deposit): Closing = Opening + Cash Sale - Deposited
  // Track B (Petty Cash): Petty Closing = Petty Opening + Cash Receipts - Cash Expenses
  const calculateRow = (row) => {
    const total_sale = parseFloat(row.total_sale) || 0;
    const swiggy = parseFloat(row.swiggy) || 0;
    const zomato = parseFloat(row.zomato) || 0;
    const doordash = parseFloat(row.doordash) || 0;
    const card_idfc = parseFloat(row.card_idfc) || 0;
    const bharat_pay = parseFloat(row.bharat_pay) || 0;
    const online_other = parseFloat(row.online_other) || 0;
    const opening_balance = parseFloat(row.opening_balance) || 0;
    const cash_receipts = parseFloat(row.cash_receipts) || 0;
    const deposited_in_bank = parseFloat(row.deposited_in_bank) || 0;
    const cash_expense = parseFloat(row.cash_expense) || 0;
    const petty_cash_opening = parseFloat(row.petty_cash_opening) || 0;

    const total_online_sale = card_idfc + bharat_pay + swiggy + zomato + doordash + online_other;
    const total_cash_sale = Math.max(0, total_sale - total_online_sale);
    
    // Track A: Closing Balance = Opening + Cash Sale - Deposited
    const closing_balance = opening_balance + total_cash_sale - deposited_in_bank;
    const to_deposit_in_bank = closing_balance;
    
    // Track B: Petty Cash Closing = Petty Opening + Cash Withdrawal (Receipts) - Cash Expenses
    const petty_cash_closing = petty_cash_opening + cash_receipts - cash_expense;

    return {
      ...row,
      total_online_sale,
      total_cash_sale,
      closing_balance,
      petty_cash_closing,
      to_deposit_in_bank,
    };
  };

  useEffect(() => {
    if (session?.token && centerCode && selectedMonth) {
      fetchGridData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMonth, centerCode, session?.token]);

  // Handle cell click to start editing - set local edit value
  const handleCellClick = (rowIndex, field) => {
    const row = gridData[rowIndex];
    const status = frozenStatus[row.date];
    
    if (status && !status.can_edit) {
      toast.error(`Cannot edit frozen date. ${status.is_admin_frozen ? 'Admin frozen.' : 'Request unlock from Super Admin.'}`);
      return;
    }

    // Set the local edit value to current cell value
    setEditValue(row[field] || '');
    setEditingCell({ row: rowIndex, field });
  };

  // Handle LOCAL input change - doesn't update grid until blur
  const handleInputChange = (value) => {
    setEditValue(value);
  };

  // Handle cell blur (finish editing) - NOW update the grid
  const handleCellBlur = () => {
    if (editingCell) {
      const { row: rowIndex, field } = editingCell;
      const fieldConfig = EDITABLE_FIELDS.find(f => f.key === field);
      
      // Parse value based on type
      let parsedValue = editValue;
      if (fieldConfig?.type === 'integer') {
        parsedValue = parseInt(editValue) || 0;
      } else if (fieldConfig?.type === 'number') {
        parsedValue = parseFloat(editValue) || 0;
      }

      // Update grid data and cascade balances if needed
      setGridData(prev => {
        const newData = [...prev];
        newData[rowIndex] = calculateRow({
          ...newData[rowIndex],
          [field]: parsedValue
        });
        
        // Cascade opening/closing balances to subsequent rows
        const cascadeFields = ['opening_balance', 'total_sale', 'deposited_in_bank', 'card_idfc', 
          'bharat_pay', 'swiggy', 'zomato', 'doordash', 'online_other', 'cash_receipts', 'cash_expense', 'petty_cash_opening'];
        if (cascadeFields.includes(field)) {
          for (let i = rowIndex + 1; i < newData.length; i++) {
            const prevRow = newData[i - 1];
            newData[i] = calculateRow({
              ...newData[i],
              opening_balance: prevRow.closing_balance,
              petty_cash_opening: prevRow.petty_cash_closing,
            });
          }
        }
        
        return newData;
      });

      // Mark row as modified (and all subsequent rows if cascading)
      const cascadeFields = ['opening_balance', 'total_sale', 'deposited_in_bank', 'card_idfc',
        'bharat_pay', 'swiggy', 'zomato', 'doordash', 'online_other', 'cash_receipts', 'cash_expense', 'petty_cash_opening'];
      setModifiedRows(prev => {
        const newSet = new Set([...prev, rowIndex]);
        if (cascadeFields.includes(field)) {
          for (let i = rowIndex + 1; i < gridData.length; i++) {
            newSet.add(i);
          }
        }
        return newSet;
      });
    }
    
    setEditingCell(null);
    setEditValue('');
  };

  // Handle keyboard navigation - save current cell before moving
  const handleKeyDown = (e, rowIndex, fieldIndex) => {
    if (e.key === 'Tab' || e.key === 'Enter') {
      e.preventDefault();
      
      // First, save current cell value
      const fieldConfig = EDITABLE_FIELDS.find(f => f.key === editingCell?.field);
      let parsedValue = editValue;
      if (fieldConfig?.type === 'integer') {
        parsedValue = parseInt(editValue) || 0;
      } else if (fieldConfig?.type === 'number') {
        parsedValue = parseFloat(editValue) || 0;
      }

      // Update grid data for current cell + cascade
      setGridData(prev => {
        const newData = [...prev];
        newData[rowIndex] = calculateRow({
          ...newData[rowIndex],
          [editingCell.field]: parsedValue
        });
        // Cascade to subsequent rows
        const cascadeFields = ['opening_balance', 'total_sale', 'deposited_in_bank', 'card_idfc',
          'bharat_pay', 'swiggy', 'zomato', 'doordash', 'online_other', 'cash_receipts', 'cash_expense', 'petty_cash_opening'];
        if (cascadeFields.includes(editingCell.field)) {
          for (let i = rowIndex + 1; i < newData.length; i++) {
            const prevRow = newData[i - 1];
            newData[i] = calculateRow({ ...newData[i], opening_balance: prevRow.closing_balance, petty_cash_opening: prevRow.petty_cash_closing });
          }
        }
        return newData;
      });
      setModifiedRows(prev => {
        const newSet = new Set([...prev, rowIndex]);
        const cascadeFields = ['opening_balance', 'total_sale', 'deposited_in_bank', 'card_idfc',
          'bharat_pay', 'swiggy', 'zomato', 'doordash', 'online_other', 'cash_receipts', 'cash_expense', 'petty_cash_opening'];
        if (cascadeFields.includes(editingCell.field)) {
          for (let i = rowIndex + 1; i < gridData.length; i++) newSet.add(i);
        }
        return newSet;
      });
      
      // Move to next cell
      const nextFieldIndex = e.shiftKey ? fieldIndex - 1 : fieldIndex + 1;
      
      if (nextFieldIndex >= 0 && nextFieldIndex < EDITABLE_FIELDS.length) {
        const nextField = EDITABLE_FIELDS[nextFieldIndex].key;
        const nextValue = gridData[rowIndex][nextField] || '';
        setEditValue(nextValue);
        setEditingCell({ row: rowIndex, field: nextField });
      } else if (nextFieldIndex >= EDITABLE_FIELDS.length) {
        // Move to next row
        const nextRowIndex = rowIndex + 1;
        if (nextRowIndex < gridData.length) {
          const nextRow = gridData[nextRowIndex];
          const status = frozenStatus[nextRow.date];
          if (status?.can_edit) {
            const nextField = EDITABLE_FIELDS[0].key;
            setEditValue(nextRow[nextField] || '');
            setEditingCell({ row: nextRowIndex, field: nextField });
          } else {
            setEditingCell(null);
            setEditValue('');
          }
        } else {
          setEditingCell(null);
          setEditValue('');
        }
      } else {
        setEditingCell(null);
        setEditValue('');
      }
    } else if (e.key === 'Escape') {
      setEditingCell(null);
      setEditValue('');
    }
  };

  // Handle paste from clipboard (Excel)
  const handlePaste = async (e) => {
    e.preventDefault();
    const clipboardData = e.clipboardData.getData('text');
    
    if (!clipboardData) {
      toast.error("No data in clipboard");
      return;
    }

    try {
      // Parse clipboard data (tab-separated values from Excel)
      const rows = clipboardData.trim().split('\n');
      const parsedData = rows.map(row => row.split('\t').map(cell => cell.trim()));

      if (parsedData.length === 0) {
        toast.error("No valid data to paste");
        return;
      }

      // Check if first row is header
      const firstRow = parsedData[0];
      let dataStartIndex = 0;
      let fieldMapping = [];

      // Try to detect if first row is a header
      const possibleHeaders = ['date', 'total', 'sale', 'card', 'swiggy', 'zomato', 'guests', 'bills'];
      const isHeader = firstRow.some(cell => 
        possibleHeaders.some(h => cell.toLowerCase().includes(h))
      );

      if (isHeader) {
        // Map headers to fields
        fieldMapping = firstRow.map(header => {
          const h = header.toLowerCase();
          if (h.includes('total') && h.includes('sale')) return 'total_sale';
          if (h.includes('card') || h.includes('idfc')) return 'card_idfc';
          if (h.includes('bharat')) return 'bharat_pay';
          if (h.includes('swiggy')) return 'swiggy';
          if (h.includes('zomato')) return 'zomato';
          if (h.includes('online') && h.includes('other')) return 'online_other';
          if (h.includes('guest') || h.includes('pax')) return 'num_guests';
          if (h.includes('bill')) return 'num_bills';
          if (h.includes('date')) return 'date';
          return null;
        });
        dataStartIndex = 1;
      } else {
        // Default field order matching EDITABLE_FIELDS
        fieldMapping = EDITABLE_FIELDS.map(f => f.key);
      }

      // Apply pasted data to grid
      let updatedCount = 0;
      let skippedCount = 0;
      const newModified = new Set(modifiedRows);

      setGridData(prev => {
        const newData = [...prev];
        
        for (let i = dataStartIndex; i < parsedData.length; i++) {
          const rowData = parsedData[i];
          
          // Find matching row by date if date column exists
          let targetRowIndex = -1;
          const dateColIndex = fieldMapping.indexOf('date');
          
          if (dateColIndex !== -1 && rowData[dateColIndex]) {
            // Try to match by date
            const pastedDate = rowData[dateColIndex];
            targetRowIndex = newData.findIndex(r => {
              const rowDate = r.date;
              return rowDate.includes(pastedDate) || pastedDate.includes(rowDate.split('-')[2]);
            });
          }

          // If no date match, use sequential row index
          if (targetRowIndex === -1) {
            const dataRowIndex = i - dataStartIndex;
            // Find next editable row
            for (let j = dataRowIndex; j < newData.length; j++) {
              const status = frozenStatus[newData[j].date];
              if (status?.can_edit) {
                targetRowIndex = j;
                break;
              }
            }
          }

          if (targetRowIndex === -1 || targetRowIndex >= newData.length) continue;

          const targetRow = newData[targetRowIndex];
          const status = frozenStatus[targetRow.date];

          if (!status?.can_edit) {
            skippedCount++;
            continue;
          }

          // Update row with pasted data
          const updatedRow = { ...targetRow };
          fieldMapping.forEach((field, colIndex) => {
            if (field && field !== 'date' && rowData[colIndex] !== undefined) {
              const value = rowData[colIndex].replace(/[,$₹]/g, ''); // Remove currency symbols
              const fieldConfig = EDITABLE_FIELDS.find(f => f.key === field);
              if (fieldConfig?.type === 'integer') {
                updatedRow[field] = parseInt(value) || 0;
              } else {
                updatedRow[field] = parseFloat(value) || 0;
              }
            }
          });

          newData[targetRowIndex] = calculateRow(updatedRow);
          newModified.add(targetRowIndex);
          updatedCount++;
        }

        return newData;
      });

      setModifiedRows(newModified);

      if (updatedCount > 0) {
        toast.success(`Pasted ${updatedCount} rows. ${skippedCount > 0 ? `${skippedCount} frozen rows skipped.` : ''}`);
      } else {
        toast.error("No rows could be updated. Check if dates are frozen.");
      }
    } catch (err) {
      console.error("Paste error:", err);
      toast.error("Failed to parse clipboard data");
    }
  };

  // Save all modified rows
  const handleSaveAll = async () => {
    if (modifiedRows.size === 0) {
      toast.info("No changes to save");
      return;
    }

    setSaving(true);
    let savedCount = 0;
    let errorCount = 0;

    try {
      for (const rowIndex of modifiedRows) {
        const row = gridData[rowIndex];
        const status = frozenStatus[row.date];

        if (!status?.can_edit) {
          errorCount++;
          continue;
        }

        try {
          const payload = {
            center: centerCode,
            date: row.date,
            opening_balance: parseFloat(row.opening_balance) || 0,
            petty_cash_opening: parseFloat(row.petty_cash_opening) || 0,
            deposited_in_bank: parseFloat(row.deposited_in_bank) || 0,
            cash_receipts: parseFloat(row.cash_receipts) || 0,
            sale_pbm: parseFloat(row.total_sale) || 0,
            sale_other: 0,
            total_sale: parseFloat(row.total_sale) || 0,
            swiggy: parseFloat(row.swiggy) || 0,
            zomato: parseFloat(row.zomato) || 0,
            doordash: parseFloat(row.doordash) || 0,
            card_idfc: parseFloat(row.card_idfc) || 0,
            bharat_pay: parseFloat(row.bharat_pay) || 0,
            online_other: parseFloat(row.online_other) || 0,
            due_amount: parseFloat(row.due_amount) || 0,
            cash_expense: parseFloat(row.cash_expense) || 0,
            num_guests: parseInt(row.num_guests) || 0,
            num_bills: parseInt(row.num_bills) || 0,
            total_online_sale: row.total_online_sale || 0,
            total_cash_sale: row.total_cash_sale || 0,
            closing_balance: row.closing_balance || 0,
            petty_cash_closing: row.petty_cash_closing || 0,
            to_deposit_in_bank: row.to_deposit_in_bank || 0,
          };

          if (row._isNew) {
            await api.post(`/sales/daily/create?token=${session.token}`, payload);
          } else {
            await api.put(`/sales/daily/${centerCode}/${row.date}?token=${session.token}`, payload);
          }
          savedCount++;
        } catch (err) {
          console.error(`Failed to save ${row.date}:`, err);
          errorCount++;
        }
      }

      if (savedCount > 0) {
        // After all saves, trigger a single server-side recalculate to fix cascading balances
        try {
          await api.post(`/sales/recalculate-balances?token=${session.token}`, {
            center: centerCode,
            month: selectedMonth
          });
        } catch (e) {
          console.log("Recalculate after save:", e);
        }
        toast.success(`Saved ${savedCount} records successfully!`);
        setModifiedRows(new Set());
        fetchGridData(); // Refresh data
      }
      if (errorCount > 0) {
        toast.error(`Failed to save ${errorCount} records`);
      }
    } catch (err) {
      console.error("Save error:", err);
      toast.error("Failed to save changes");
    } finally {
      setSaving(false);
    }
  };

  // Render cell
  const renderCell = (row, field, rowIndex, fieldIndex) => {
    const isEditing = editingCell?.row === rowIndex && editingCell?.field === field.key;
    const isModified = modifiedRows.has(rowIndex);
    const status = frozenStatus[row.date];
    const canEdit = status?.can_edit;
    const value = row[field.key];

    // Calculated field (read-only)
    if (field.computed) {
      const displayValue = typeof value === 'number' ? Math.round(value).toLocaleString() : value || 0;
      
      return (
        <td 
          key={field.key} 
          className="px-2 py-1 text-right bg-gray-50 text-gray-600 font-mono text-xs"
        >
          {displayValue}
        </td>
      );
    }

    // Read-only field (auto-fetched, like cash_expense from expense entries)
    if (field.readOnly) {
      const displayValue = typeof value === 'number' ? Math.round(value).toLocaleString() : value || 0;
      return (
        <td 
          key={field.key} 
          className="px-2 py-1 text-right bg-amber-50 text-amber-800 font-mono text-xs font-medium"
          title="Auto-filled from Expense Entries (CASH mode)"
        >
          {displayValue}
        </td>
      );
    }

    // Editable cell - WHEN EDITING, use local editValue to prevent focus loss
    if (isEditing) {
      return (
        <td key={field.key} className="px-0 py-0">
          <input
            ref={inputRef}
            type="number"
            value={editValue}
            onChange={(e) => handleInputChange(e.target.value)}
            onBlur={handleCellBlur}
            onKeyDown={(e) => handleKeyDown(e, rowIndex, fieldIndex)}
            autoFocus
            className="w-full h-7 px-2 text-xs text-right border-2 border-blue-500 outline-none"
            style={{ minWidth: '60px' }}
          />
        </td>
      );
    }

    return (
      <td 
        key={field.key}
        onClick={() => handleCellClick(rowIndex, field.key)}
        className={`px-2 py-1 text-right font-mono text-xs cursor-pointer transition-colors
          ${canEdit ? 'hover:bg-blue-50' : 'bg-gray-100 cursor-not-allowed'}
          ${isModified ? 'bg-yellow-50 font-semibold' : ''}
        `}
      >
        {typeof value === 'number' ? value.toLocaleString() : value || 0}
      </td>
    );
  };

  // Focus input when editing starts
  useEffect(() => {
    if (editingCell && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingCell]);

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <Table2 className="w-5 h-5" />
            Grid Bulk Update - {centerCode}
            {modifiedRows.size > 0 && (
              <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-0.5 rounded-full">
                {modifiedRows.size} modified
              </span>
            )}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchGridData}
              disabled={loading}
              className="gap-1"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const textarea = document.createElement('textarea');
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.focus();
                textarea.addEventListener('paste', handlePaste);
                document.execCommand('paste');
                document.body.removeChild(textarea);
              }}
              className="gap-1"
              data-testid="paste-from-excel-btn"
            >
              <ClipboardPaste className="w-4 h-4" />
              Paste from Excel
            </Button>
            <Button
              onClick={handleSaveAll}
              disabled={saving || modifiedRows.size === 0}
              className="gap-1"
              data-testid="save-all-btn"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : `Save All (${modifiedRows.size})`}
            </Button>
          </div>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Click any cell to edit. Press Tab to move to next cell. Ctrl+V to paste from Excel.
        </p>
      </CardHeader>

      <CardContent className="p-0" onPaste={handlePaste}>
        {loading ? (
          <div className="text-center py-8 text-muted-foreground">Loading grid data...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse" data-testid="sales-grid-table">
              <thead className="bg-muted sticky top-0">
                <tr>
                  <th className="px-2 py-2 text-left font-medium text-muted-foreground border-b w-24">Date</th>
                  <th className="px-2 py-2 text-center font-medium text-muted-foreground border-b w-10">Status</th>
                  {DAY1_FIELDS.map(field => (
                    <th 
                      key={field.key} 
                      className="px-2 py-2 text-right font-medium text-muted-foreground border-b bg-green-50"
                      title="Editable on 1st day only"
                    >
                      {field.label}
                    </th>
                  ))}
                  {EDITABLE_FIELDS.map(field => (
                    <th 
                      key={field.key} 
                      className="px-2 py-2 text-right font-medium text-muted-foreground border-b bg-blue-50"
                      title="Editable"
                    >
                      {field.label}
                    </th>
                  ))}
                  {CALCULATED_FIELDS.map(field => (
                    <th 
                      key={field.key} 
                      className="px-2 py-2 text-right font-medium text-muted-foreground border-b bg-gray-100"
                      title="Auto-calculated"
                    >
                      {field.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {gridData.map((row, rowIndex) => {
                  const status = frozenStatus[row.date];
                  const isModified = modifiedRows.has(rowIndex);
                  const isFirstDay = rowIndex === 0;
                  
                  return (
                    <tr 
                      key={row.date} 
                      className={`border-b hover:bg-muted/30 ${isModified ? 'bg-yellow-50/50' : ''}`}
                      data-testid={`grid-row-${row.date}`}
                    >
                      <td className="px-2 py-1 font-medium text-xs">
                        {formatDateDisplay(row.date)}
                        {isModified && <span className="ml-1 text-yellow-600">*</span>}
                      </td>
                      <td className="px-2 py-1 text-center">
                        {status?.can_edit ? (
                          <Unlock className="w-3 h-3 text-green-500 inline" title="Editable" />
                        ) : status?.is_admin_frozen ? (
                          <Lock className="w-3 h-3 text-red-500 inline" title="Admin Frozen" />
                        ) : (
                          <Lock className="w-3 h-3 text-amber-500 inline" title="Frozen" />
                        )}
                      </td>
                      {/* Day 1 fields: editable for 1st day, read-only for rest */}
                      {DAY1_FIELDS.map((field) => (
                        isFirstDay ? (
                          renderCell(row, field, rowIndex, -1)
                        ) : (
                          <td key={field.key} className="px-2 py-1 text-right bg-gray-50 text-gray-600 font-mono text-xs">
                            {typeof row[field.key] === 'number' ? Math.round(row[field.key]).toLocaleString() : row[field.key] || 0}
                          </td>
                        )
                      ))}
                      {EDITABLE_FIELDS.map((field, fieldIndex) => 
                        renderCell(row, field, rowIndex, fieldIndex)
                      )}
                      {CALCULATED_FIELDS.map((field, fieldIndex) => 
                        renderCell(row, field, rowIndex, EDITABLE_FIELDS.length + fieldIndex)
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Legend */}
        <div className="p-3 bg-muted/50 border-t flex items-center gap-6 text-xs flex-wrap">
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-green-50 border"></div>
            <span>Opening Bal (1st day editable)</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-blue-50 border"></div>
            <span>Editable</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-gray-100 border"></div>
            <span>Auto-calculated</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-yellow-50 border"></div>
            <span>Modified (unsaved)</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
