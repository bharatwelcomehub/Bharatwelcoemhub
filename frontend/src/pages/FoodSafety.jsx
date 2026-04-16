import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "@/App";
import { api, isAdminUser, fetchCentersFromDB } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Loader2, Plus, Save, Trash2, Search, X, RefreshCw, Edit, Download,
  FileText, ClipboardCheck, Thermometer, Clock, Sparkles, Shield,
  AlertTriangle, CheckCircle, FileSpreadsheet, Eye, ChevronDown, Filter,
  UtensilsCrossed, Truck, Flame, SnowflakeIcon, SprayCan, ClipboardList,
} from "lucide-react";

// Template type visual config — color + icon per type
const TYPE_CONFIG = {
  supplier_details:    { icon: Truck,           color: "#2563eb", bg: "#eff6ff", label: "Supplier Details" },
  food_receipt:        { icon: ClipboardList,   color: "#d97706", bg: "#fffbeb", label: "Food Receipt" },
  cooking_cooling:     { icon: Flame,           color: "#ea580c", bg: "#fff7ed", label: "Cooking & Cooling" },
  food_temp_record:    { icon: Thermometer,     color: "#dc2626", bg: "#fef2f2", label: "Food Temp Record" },
  two_four_hour_rule:  { icon: Clock,           color: "#7c3aed", bg: "#f5f3ff", label: "2hr / 4hr Rule" },
  cleaning_procedure:  { icon: SprayCan,        color: "#0d9488", bg: "#f0fdfa", label: "Cleaning Procedure" },
  cleaning_record:     { icon: Sparkles,        color: "#059669", bg: "#ecfdf5", label: "Cleaning Record" },
  general_temp_record: { icon: Thermometer,     color: "#e11d48", bg: "#fff1f2", label: "General Temp Record" },
  food_items:          { icon: UtensilsCrossed, color: "#8B0000", bg: "#fef2f2", label: "Food Items (Master)" },
};

const STATUS_COLORS = {
  draft: "bg-yellow-100 text-yellow-800 border-yellow-300",
  submitted: "bg-blue-100 text-blue-800 border-blue-300",
  approved: "bg-green-100 text-green-800 border-green-300",
  locked: "bg-gray-200 text-gray-700 border-gray-400",
  overdue: "bg-red-100 text-red-800 border-red-300",
};

export default function FoodSafety() {
  const { session } = useAuth();
  const isAdmin = isAdminUser(session);

  const [activeTab, setActiveTab] = useState("dashboard");
  const [templateTypes, setTemplateTypes] = useState([]);
  const [templateColumns, setTemplateColumns] = useState({});
  const [loading, setLoading] = useState(false);
  const columnsRef = useRef({});

  const [dashboard, setDashboard] = useState(null);
  const [dashCenter, setDashCenter] = useState(session?.center || "PB-PERTH");
  const [centersList, setCentersList] = useState([]);

  const [templateItems, setTemplateItems] = useState([]);
  const [selectedType, setSelectedType] = useState("supplier_details");
  const [itemForm, setItemForm] = useState(null);

  const [records, setRecords] = useState([]);
  const [recordFilter, setRecordFilter] = useState({ template_type: "", status: "", date_from: "", date_to: "" });
  const [recordForm, setRecordForm] = useState(null);
  const [recordEntries, setRecordEntries] = useState([]);
  const [entryItemOptions, setEntryItemOptions] = useState({});
  const [approvalSettings, setApprovalSettings] = useState({});
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    if (session?.token) {
      fetchCentersFromDB(session.token).then(centers => {
        const nonIndia = centers.filter(c => c.is_india_center === false || c.code === dashCenter);
        setCentersList(nonIndia.length > 0 ? nonIndia : centers);
      });
    }
  }, [session?.token]);

  const FALLBACK_TYPES = [
    {key: "food_items", label: "Food Items (Master List)", order: 0},
    {key: "supplier_details", label: "Supplier Details", order: 1},
    {key: "food_receipt", label: "Food Receipt", order: 2},
    {key: "cooking_cooling", label: "Cooking and Cooling Food", order: 3},
    {key: "food_temp_record", label: "Food Temperature Record", order: 4},
    {key: "two_four_hour_rule", label: "2-Hour / 4-Hour Rule Log", order: 5},
    {key: "cleaning_procedure", label: "Cleaning and Sanitising Procedure", order: 6},
    {key: "cleaning_record", label: "Cleaning and Sanitising Record", order: 7},
    {key: "general_temp_record", label: "General Temperature Record", order: 8},
  ];
  const FALLBACK_COLUMNS = {
    food_items: [{key:"food_name",label:"Food Item Name",type:"text",required:true},{key:"category",label:"Category",type:"select",options:["Thali Item","Bhaji/Sabji","Dal/Amti","Rice","Drink/Beverage","Chutney/Condiment","Sweet/Dessert","Bread/Roti","Prep Item","Display/Counter","Takeaway","Other"]},{key:"notes",label:"Notes",type:"text"}],
    supplier_details: [{key:"supplier_name",label:"Supplier Name",type:"text",required:true},{key:"contact",label:"Contact Details",type:"text"},{key:"address",label:"Address",type:"text"},{key:"foods_supplied",label:"Foods Supplied",type:"text"},{key:"notes",label:"Notes",type:"text"}],
    food_receipt: [{key:"date",label:"Date",type:"date",required:true},{key:"time",label:"Time",type:"time",required:true},{key:"supplier",label:"Supplier",type:"text",required:true},{key:"product",label:"Product (Name & Lot)",type:"text",required:true},{key:"condition_temp",label:"Condition / Temp",type:"text"},{key:"corrective_action",label:"Corrective Action / Notes",type:"text"},{key:"checked_by",label:"Checked By",type:"text",required:true}],
    cooking_cooling: [{key:"date",label:"Date",type:"date",required:true},{key:"food",label:"Food",type:"text",required:true},{key:"core_temp",label:"Core Temp (>=75C)",type:"number"},{key:"cooling_start_time",label:"Cooling Start Time",type:"time"},{key:"cooling_start_temp",label:"Cooling Start Temp",type:"number"},{key:"time_2hr",label:"Time at 2hr Check",type:"time"},{key:"temp_2hr",label:"Temp at 2hr (<=21C?)",type:"number"},{key:"temp_2hr_ok",label:"<=21C?",type:"select",options:["Yes","No"]},{key:"time_4hr",label:"Time at 4hr Check",type:"time"},{key:"temp_4hr",label:"Temp at 4hr (<=5C?)",type:"number"},{key:"temp_within_4hrs",label:"5\u00b0C or below within 4 hrs? (6 hrs after start)",type:"select",options:["Yes","No"]},{key:"corrective_action",label:"Corrective Action / Note",type:"text"},{key:"staff_initials",label:"Staff Initials",type:"text",required:true}],
    food_temp_record: [{key:"date",label:"Date",type:"date",required:true},{key:"food",label:"Food Item",type:"text",required:true},{key:"time",label:"Time",type:"time",required:true},{key:"cold_unit_1",label:"Walkin Fridge",type:"number"},{key:"cold_unit_2",label:"Cold Bain Marie",type:"number"},{key:"cold_unit_3",label:"Prep Fridge",type:"number"},{key:"hot_unit_1",label:"Hot Unit 1 (Bain Marie)",type:"number"},{key:"cold_unit_4",label:"Deep Fridge",type:"number"},{key:"cold_unit_5",label:"Drink Fridge",type:"number"},{key:"notes",label:"Notes",type:"text"},{key:"corrective_action",label:"Corrective Action",type:"text"},{key:"staff_initials",label:"Staff Initials",type:"text",required:true}],
    two_four_hour_rule: [{key:"date",label:"Date",type:"date",required:true},{key:"food",label:"Food",type:"text",required:true},{key:"time_out",label:"Time Out of Fridge (>5C)",type:"time",required:true},{key:"activity",label:"Activity (prep/display/transport)",type:"text"},{key:"time_back",label:"Time Back in Temp Control (<=5C)",type:"time"},{key:"total_time_out",label:"Total Time Out",type:"calculated"},{key:"action",label:"Action",type:"select",options:["Re-refrigerate","Use immediately","Discard"]},{key:"remark",label:"Remark",type:"text"},{key:"staff_initials",label:"Staff Initials",type:"text",required:true}],
    cleaning_procedure: [{key:"item_equipment",label:"Item / Equipment",type:"text",required:true},{key:"how_often",label:"How Often",type:"select",options:["After each use","Daily","Weekly","Monthly","As needed"]},{key:"cleaning_method",label:"Cleaning Method",type:"textarea"},{key:"sanitising_method",label:"Sanitising Method",type:"textarea"},{key:"responsibility",label:"Responsibility",type:"text"},{key:"comments",label:"Comments",type:"text"}],
    cleaning_record: [{key:"area_equipment",label:"Area / Equipment",type:"text",required:true},{key:"frequency",label:"Frequency",type:"text"},{key:"person_responsible",label:"Person Responsible",type:"text"},{key:"sun",label:"Sun",type:"check"},{key:"mon",label:"Mon",type:"check"},{key:"tue",label:"Tue",type:"check"},{key:"wed",label:"Wed",type:"check"},{key:"thu",label:"Thu",type:"check"},{key:"fri",label:"Fri",type:"check"},{key:"sat",label:"Sat",type:"check"},{key:"supervisor_initials",label:"Supervisor Initials",type:"text"}],
    general_temp_record: [{key:"date",label:"Date",type:"date",required:true},{key:"time",label:"Time",type:"time",required:true},{key:"activity_food",label:"Activity / Food / Appliance",type:"text",required:true},{key:"food_temp",label:"Food Temp (C)",type:"number"},{key:"corrective_action",label:"Corrective Action / Notes",type:"text"},{key:"checked_by",label:"Checked By",type:"text",required:true}],
  };

  // ===== ALL API/LOGIC FUNCTIONS (unchanged) =====

  useEffect(() => {
    if (session?.token) {
      api.post("/food-safety/template-types", { token: session.token })
        .then(res => {
          setTemplateTypes(res.data.types || FALLBACK_TYPES);
          const cols = res.data.columns || FALLBACK_COLUMNS;
          setTemplateColumns(cols);
          columnsRef.current = cols;
        })
        .catch(() => {
          setTemplateTypes(FALLBACK_TYPES);
          setTemplateColumns(FALLBACK_COLUMNS);
          columnsRef.current = FALLBACK_COLUMNS;
        });
    }
  }, [session?.token]);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.post("/food-safety/dashboard", { token: session.token, center: dashCenter });
      setDashboard(res.data);
    } catch {
      setDashboard({ status_counts: {}, recent_records: [], overdue: [], template_types: FALLBACK_TYPES });
    } finally { setLoading(false); }
  }, [session?.token, dashCenter]);

  useEffect(() => {
    if (activeTab === "dashboard" && session?.token) { loadDashboard(); loadApprovalSettings(); }
  }, [activeTab, loadDashboard, session?.token]);

  const seedTemplates = async () => {
    try {
      const res = await api.post("/food-safety/seed", { token: session.token, center: dashCenter, force_food: true });
      toast.success(res.data.message);
      loadTemplateItems();
    } catch (e) { toast.error(e.response?.data?.detail || "Seed failed"); }
  };

  const loadTemplateItems = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.post("/food-safety/template-items/list", { token: session.token, template_type: selectedType, center: dashCenter });
      setTemplateItems(res.data.items || []);
    } catch { toast.error("Failed to load items"); }
    finally { setLoading(false); }
  }, [session?.token, selectedType, dashCenter]);

  useEffect(() => {
    if (activeTab === "templates" && session?.token) { loadTemplateItems(); loadApprovalSettings(); }
  }, [activeTab, loadTemplateItems, session?.token]);

  const loadApprovalSettings = async () => {
    try {
      const res = await api.post("/food-safety/template-settings/get", { token: session.token, center: dashCenter });
      setApprovalSettings(res.data.settings || {});
    } catch { setApprovalSettings({}); }
  };

  const toggleApproval = async (templateType, currentValue) => {
    try {
      await api.post("/food-safety/template-settings/save", { token: session.token, template_type: templateType, center: dashCenter, requires_approval: !currentValue });
      setApprovalSettings(prev => ({ ...prev, [templateType]: !currentValue }));
      toast.success(!currentValue ? "Approval now required" : "Auto-approve enabled");
    } catch (e) { toast.error(e.response?.data?.detail || "Failed to update setting"); }
  };

  const saveTemplateItem = async () => {
    if (!itemForm) return;
    try {
      await api.post("/food-safety/template-items/save", {
        token: session.token, template_type: selectedType, center: dashCenter,
        name: itemForm.name, fields: itemForm.fields, active: itemForm.active !== false,
        order: itemForm.order || 0, item_id: itemForm.item_id || "",
      });
      toast.success("Item saved");
      setItemForm(null);
      loadTemplateItems();
    } catch (e) { toast.error(e.response?.data?.detail || "Save failed"); }
  };

  const deleteTemplateItem = async (item_id) => {
    if (!window.confirm("Delete this template item?")) return;
    try {
      await api.post("/food-safety/template-items/delete", { token: session.token, item_id });
      toast.success("Deleted"); loadTemplateItems();
    } catch { toast.error("Delete failed"); }
  };

  const toggleTemplateItem = async (item_id, active) => {
    try {
      await api.post("/food-safety/template-items/toggle", { token: session.token, item_id, active: !active });
      loadTemplateItems();
    } catch { toast.error("Toggle failed"); }
  };

  const loadRecords = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.post("/food-safety/records/list", { token: session.token, center: dashCenter, ...recordFilter });
      setRecords(res.data.records || []);
    } catch { toast.error("Failed to load records"); }
    finally { setLoading(false); }
  }, [session?.token, dashCenter, recordFilter]);

  useEffect(() => {
    if (activeTab === "records" && session?.token) loadRecords();
  }, [activeTab, loadRecords, session?.token]);

  const loadEntryItemOptions = async () => {
    if (!session?.token) return;
    try {
      const fetchItems = async (tt) => {
        try {
          const res = await api.post("/food-safety/template-items/list", { token: session.token, template_type: tt, center: dashCenter });
          const items = (res.data.items || []).filter(i => i.active !== false);
          if (items.length > 0) return items;
          const res2 = await api.post("/food-safety/template-items/list", { token: session.token, template_type: tt, center: "" });
          return (res2.data.items || []).filter(i => i.active !== false);
        } catch { return []; }
      };
      const foodItemsRaw = await fetchItems("food_items");
      const supplierItemsFull = await fetchItems("supplier_details");
      const cleanItemsFull = await fetchItems("cleaning_procedure");
      const cleanRecItemsRaw = await fetchItems("cleaning_record");
      setEntryItemOptions({
        food: foodItemsRaw.map(i => i.name),
        supplier: supplierItemsFull.map(i => i.name),
        supplierFull: supplierItemsFull,
        cleaning: cleanItemsFull.map(i => i.name),
        cleaningFull: cleanItemsFull,
        cleaningRec: cleanRecItemsRaw.map(i => i.name),
      });
    } catch { /* options stay empty */ }
  };

  const startNewRecord = (templateType) => {
    const cols = columnsRef.current[templateType] || templateColumns[templateType] || [];
    setRecordForm({ template_type: templateType, record_date: new Date().toISOString().split("T")[0], period: "daily", notes: "", status: "draft" });
    const emptyRow = {};
    cols.forEach(col => { emptyRow[col.key] = ""; });
    setRecordEntries([emptyRow]);
    setActiveTab("record-entry");
    loadEntryItemOptions();
  };

  const addEntryRow = () => {
    const cols = columnsRef.current[recordForm?.template_type] || templateColumns[recordForm?.template_type] || [];
    const emptyRow = {};
    cols.forEach(col => { emptyRow[col.key] = ""; });
    setRecordEntries(prev => [...prev, emptyRow]);
  };

  const updateEntry = (rowIdx, key, value) => {
    setRecordEntries(prev => prev.map((row, i) => {
      if (i !== rowIdx) return row;
      const updated = { ...row, [key]: value };
      if (recordForm?.template_type === "two_four_hour_rule" && (key === "time_out" || key === "time_back")) {
        const tout = updated.time_out || "";
        const tback = updated.time_back || "";
        if (tout && tback) {
          const [h1, m1] = tout.split(":").map(Number);
          const [h2, m2] = tback.split(":").map(Number);
          if (!isNaN(h1) && !isNaN(m1) && !isNaN(h2) && !isNaN(m2)) {
            let diffMin = (h2 * 60 + m2) - (h1 * 60 + m1);
            if (diffMin < 0) diffMin += 24 * 60;
            updated.total_time_out = `${Math.floor(diffMin / 60)}h ${diffMin % 60}m`;
          }
        } else { updated.total_time_out = ""; }
      }
      if (recordForm?.template_type === "cleaning_procedure" && key === "item_equipment") {
        const match = (entryItemOptions?.cleaningFull || []).find(it => it.name === value);
        if (match?.fields) { updated.how_often = match.fields.how_often || ""; updated.cleaning_method = match.fields.cleaning_method || ""; updated.sanitising_method = match.fields.sanitising_method || ""; }
      }
      if (recordForm?.template_type === "supplier_details" && key === "supplier_name") {
        const match = (entryItemOptions?.supplierFull || []).find(it => it.name === value);
        if (match?.fields) { updated.contact = match.fields.contact || ""; updated.address = match.fields.address || ""; updated.foods_supplied = match.fields.foods_supplied || ""; updated.notes = match.fields.notes || ""; }
      }
      return updated;
    }));
  };

  const removeEntryRow = (rowIdx) => { setRecordEntries(prev => prev.filter((_, i) => i !== rowIdx)); };

  const saveRecord = async (submitStatus = "draft") => {
    if (!recordForm) return;
    setLoading(true);
    try {
      const res = await api.post("/food-safety/records/save", {
        token: session.token, center: dashCenter, template_type: recordForm.template_type,
        record_date: recordForm.record_date, period: recordForm.period, notes: recordForm.notes,
        entries: recordEntries, status: submitStatus, record_id: recordForm.record_id || "",
      });
      toast.success(res.data.message);
      setRecordForm(null); setRecordEntries([]); setActiveTab("records"); loadRecords();
    } catch (e) { toast.error(e.response?.data?.detail || "Save failed"); }
    finally { setLoading(false); }
  };

  const approveRecord = async (record_id) => {
    try {
      await api.post("/food-safety/records/approve", { token: session.token, record_id });
      toast.success("Record approved"); loadRecords(); loadDashboard();
    } catch (e) { toast.error(e.response?.data?.detail || "Approve failed"); }
  };

  const editRecord = (rec) => {
    if (rec.status === "locked") { toast.error("Cannot edit locked records"); return; }
    setRecordForm({
      template_type: rec.template_type, record_date: rec.record_date, period: rec.period || "daily",
      notes: rec.notes || "", status: rec.status, record_id: rec.record_id,
      submittedBy: rec.submittedBy, submittedAt: rec.submittedAt, approvedBy: rec.approvedBy, approvedAt: rec.approvedAt,
    });
    setRecordEntries(rec.entries || []);
    setActiveTab("record-entry");
    loadEntryItemOptions();
  };

  const deleteRecord = async (record_id) => {
    if (!window.confirm("Delete this record permanently?")) return;
    try {
      await api.post("/food-safety/records/delete", { token: session.token, record_id });
      toast.success("Record deleted"); loadRecords(); loadDashboard();
    } catch (e) { toast.error(e.response?.data?.detail || "Delete failed"); }
  };

  const downloadReport = async (format) => {
    setLoading(true);
    try {
      const endpoint = format === "pdf" ? "/food-safety/report/pdf" : "/food-safety/report/excel";
      const res = await api.post(endpoint, {
        token: session.token, center: dashCenter, template_type: recordFilter.template_type,
        status: recordFilter.status, date_from: recordFilter.date_from, date_to: recordFilter.date_to,
      }, { responseType: "blob" });
      const ct = res.headers["content-type"] || "";
      if (ct.includes("application/json")) { const text = await res.data.text(); toast.error(JSON.parse(text).detail || "No records found"); return; }
      const blob = new Blob([res.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `FoodSafety_Report.${format === "pdf" ? "pdf" : "xlsx"}`;
      document.body.appendChild(link); link.click(); document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success(`${format.toUpperCase()} downloaded`);
    } catch (e) {
      try {
        const errBlob = e.response?.data;
        if (errBlob && typeof errBlob.text === "function") { const text = await errBlob.text(); toast.error(JSON.parse(text).detail || "No records found"); }
        else { toast.error("No records found. Adjust filters and try again."); }
      } catch { toast.error("No records found. Adjust filters and try again."); }
    } finally { setLoading(false); }
  };

  const typeLabel = (key) => TYPE_CONFIG[key]?.label || templateTypes.find(t => t.key === key)?.label || key;
  const recordTypes = templateTypes.filter(t => t.key !== "food_items");

  // ===== Helper: get dropdown options for a column =====
  const getDropdownList = (col) => {
    const opts = entryItemOptions || {};
    const foodFields = ["food", "activity_food"];
    const supplierFields = ["supplier", "supplier_name"];
    const cleanAreaFields = ["area_equipment"];
    const isCleanProcItem = col.key === "item_equipment" && recordForm?.template_type === "cleaning_procedure";
    const isFreqDropdown = col.key === "frequency" && recordForm?.template_type === "cleaning_record";
    const freqOptions = ["After each use", "Daily", "Weekly", "Monthly", "As needed"];
    if (isCleanProcItem && opts.cleaning?.length > 0) return opts.cleaning;
    if (foodFields.includes(col.key) && opts.food?.length > 0) return opts.food;
    if (supplierFields.includes(col.key) && opts.supplier?.length > 0) return opts.supplier;
    if (cleanAreaFields.includes(col.key) && opts.cleaningRec?.length > 0) return opts.cleaningRec;
    if (col.key === "item_equipment" && opts.cleaningRec?.length > 0) return opts.cleaningRec;
    if (isFreqDropdown) return freqOptions;
    return null;
  };

  const isAutoFilledField = (col) => {
    return (recordForm?.template_type === "cleaning_procedure" && ["how_often", "cleaning_method", "sanitising_method"].includes(col.key))
      || (recordForm?.template_type === "supplier_details" && ["contact", "address", "foods_supplied", "notes"].includes(col.key));
  };

  // ===== RENDER =====

  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: Shield },
    { id: "records", label: "Records", icon: FileText },
    { id: "templates", label: "Master", icon: ClipboardCheck },
  ];

  return (
    <div className="space-y-5 pb-8" data-testid="food-safety-page">
      {/* ===== HEADER ===== */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-stone-900" data-testid="food-safety-title">
            Food Safety
          </h1>
          <p className="text-base text-stone-500 mt-0.5">{dashCenter}</p>
        </div>
        <div className="flex gap-2 items-center">
          <select value={dashCenter} onChange={e => setDashCenter(e.target.value)}
            className="h-12 px-4 rounded-xl border-2 border-stone-200 bg-white text-base font-medium min-w-[120px]"
            data-testid="fs-center-select">
            {centersList.length > 0 ? centersList.map(c => (
              <option key={c.code} value={c.code}>{c.code}</option>
            )) : <option value={dashCenter}>{dashCenter}</option>}
          </select>
          {isAdmin && (
            <Button onClick={seedTemplates} variant="outline" className="h-12 px-4 text-base rounded-xl" data-testid="seed-btn">
              <Sparkles className="w-5 h-5 mr-1.5" /> Seed
            </Button>
          )}
        </div>
      </div>

      {/* ===== TAB NAVIGATION — Large Touch Targets ===== */}
      <div className="flex gap-2 bg-stone-100 p-1.5 rounded-2xl" data-testid="fs-tabs">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-2 py-3.5 px-4 text-base font-semibold rounded-xl transition-all ${
              activeTab === tab.id
                ? "bg-white text-[#8B0000] shadow-md"
                : "text-stone-500 hover:text-stone-700"
            }`} data-testid={`tab-${tab.id}`}>
            <tab.icon className="w-5 h-5" /> {tab.label}
          </button>
        ))}
        {activeTab === "record-entry" && (
          <button className="flex-1 flex items-center justify-center gap-2 py-3.5 px-4 text-base font-semibold rounded-xl bg-white text-[#8B0000] shadow-md">
            <Edit className="w-5 h-5" /> Entry
          </button>
        )}
      </div>

      {/* ===== DASHBOARD TAB ===== */}
      {activeTab === "dashboard" && (
        <div className="space-y-5">
          {/* Overdue alerts */}
          {dashboard?.overdue?.length > 0 && (
            <div className="bg-red-50 border-l-4 border-red-500 rounded-xl p-5" data-testid="overdue-alerts">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-6 h-6 text-red-600" />
                <span className="text-lg font-bold text-red-800">Missing Today's Records</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {dashboard.overdue.map((o, i) => (
                  <button key={i} onClick={() => startNewRecord(o.template_type)}
                    className="px-4 py-2.5 bg-red-100 hover:bg-red-200 text-red-900 rounded-xl text-base font-medium transition-colors"
                    data-testid={`overdue-${o.template_type}`}>
                    {o.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Template Cards — 2-col grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {recordTypes.map(tt => {
              const config = TYPE_CONFIG[tt.key] || { icon: FileText, color: "#8B0000", bg: "#fef2f2" };
              const Icon = config.icon;
              const counts = dashboard?.status_counts?.[tt.key] || { draft: 0, submitted: 0, approved: 0, locked: 0 };
              const total = counts.draft + counts.submitted + counts.approved + counts.locked;
              return (
                <button key={tt.key} onClick={() => startNewRecord(tt.key)}
                  className="text-left rounded-2xl border-2 border-stone-200 hover:border-stone-300 bg-white p-5 transition-all hover:shadow-lg active:scale-[0.98] group"
                  style={{ borderLeftWidth: "5px", borderLeftColor: config.color }}
                  data-testid={`dash-card-${tt.key}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ backgroundColor: config.bg }}>
                      <Icon className="w-6 h-6" style={{ color: config.color }} />
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-2xl font-bold text-stone-800">{total}</span>
                      <Plus className="w-5 h-5 text-stone-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </div>
                  <h3 className="text-lg font-bold text-stone-800 mb-2">{config.label}</h3>
                  <div className="flex gap-2 flex-wrap">
                    {counts.draft > 0 && <Badge className="bg-yellow-100 text-yellow-800 border-yellow-300 text-sm px-2.5 py-1">{counts.draft} Draft</Badge>}
                    {counts.submitted > 0 && <Badge className="bg-blue-100 text-blue-800 border-blue-300 text-sm px-2.5 py-1">{counts.submitted} Pending</Badge>}
                    {counts.approved > 0 && <Badge className="bg-green-100 text-green-800 border-green-300 text-sm px-2.5 py-1">{counts.approved} Done</Badge>}
                    {total === 0 && <span className="text-base text-stone-400">Tap to create first record</span>}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Recent records */}
          {dashboard?.recent_records?.length > 0 && (
            <div>
              <h2 className="text-lg font-bold text-stone-800 mb-3">Recent Records</h2>
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {dashboard.recent_records.slice(0, 10).map((rec, i) => {
                  const config = TYPE_CONFIG[rec.template_type] || { color: "#8B0000" };
                  return (
                    <button key={i} onClick={() => editRecord(rec)}
                      className="w-full flex items-center gap-4 p-4 bg-white border-2 border-stone-200 rounded-xl hover:border-stone-300 transition-all text-left"
                      style={{ borderLeftWidth: "4px", borderLeftColor: config.color }}
                      data-testid={`recent-rec-${i}`}>
                      <Badge className={`${STATUS_COLORS[rec.status] || ""} text-sm px-3 py-1`}>{rec.status}</Badge>
                      <div className="flex-1 min-w-0">
                        <p className="text-base font-semibold text-stone-800 truncate">{typeLabel(rec.template_type)}</p>
                        <p className="text-sm text-stone-500">{rec.record_date}</p>
                      </div>
                      <ChevronDown className="w-5 h-5 text-stone-400 -rotate-90" />
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===== TEMPLATE MASTER TAB ===== */}
      {activeTab === "templates" && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 flex-wrap">
            <select value={selectedType} onChange={e => setSelectedType(e.target.value)}
              className="h-12 px-4 rounded-xl border-2 border-stone-200 bg-white text-base font-medium flex-1 min-w-[200px]"
              data-testid="template-type-select">
              {templateTypes.map(tt => <option key={tt.key} value={tt.key}>{tt.label}</option>)}
            </select>
            <Button onClick={loadTemplateItems} variant="outline" className="h-12 px-4 rounded-xl text-base" disabled={loading}>
              <RefreshCw className={`w-5 h-5 mr-1.5 ${loading ? "animate-spin" : ""}`} /> Refresh
            </Button>
            {isAdmin && (
              <Button onClick={() => setItemForm({ name: "", fields: {}, active: true, order: templateItems.length })}
                className="h-12 px-5 rounded-xl text-base bg-[#8B0000] hover:bg-[#6B0000]" data-testid="add-item-btn">
                <Plus className="w-5 h-5 mr-1.5" /> Add Item
              </Button>
            )}
          </div>

          {/* Approval Settings */}
          {isAdmin && (
            <Card className="border-2 border-dashed border-stone-300 rounded-2xl" data-testid="approval-settings">
              <CardContent className="p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Shield className="w-5 h-5 text-stone-500" />
                  <span className="text-base font-bold text-stone-600">Approval Settings</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {templateTypes.map(tt => {
                    const needsApproval = approvalSettings[tt.key] || false;
                    return (
                      <div key={tt.key} className="flex items-center gap-3 p-3 border-2 border-stone-200 rounded-xl"
                        data-testid={`approval-${tt.key}`}>
                        <Checkbox checked={needsApproval} onCheckedChange={() => toggleApproval(tt.key, needsApproval)}
                          className="w-6 h-6" />
                        <div>
                          <p className="text-base font-medium text-stone-800">{tt.label}</p>
                          <p className={`text-sm font-medium ${needsApproval ? "text-amber-600" : "text-green-600"}`}>
                            {needsApproval ? "Requires Approval" : "Auto-Approved"}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Item form */}
          {itemForm && (
            <Card className="border-2 border-[#8B0000] rounded-2xl">
              <CardHeader className="pb-2 px-5 pt-5">
                <CardTitle className="text-lg flex items-center justify-between">
                  {itemForm.item_id ? "Edit Item" : "Add New Item"}
                  <Button variant="ghost" onClick={() => setItemForm(null)} className="h-10 w-10 rounded-full"><X className="w-5 h-5" /></Button>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 px-5 pb-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label className="text-base font-semibold">Name</Label>
                    <Input value={itemForm.name} onChange={e => setItemForm(p => ({ ...p, name: e.target.value }))}
                      placeholder="Item name" className="h-12 text-base rounded-xl" data-testid="item-name" />
                  </div>
                  <div className="flex gap-4 items-end">
                    <div className="space-y-1.5 flex-1">
                      <Label className="text-base font-semibold">Order</Label>
                      <Input type="number" value={itemForm.order} onChange={e => setItemForm(p => ({ ...p, order: parseInt(e.target.value) || 0 }))}
                        className="h-12 text-base rounded-xl" />
                    </div>
                    <div className="flex items-center gap-2 pb-2">
                      <Checkbox checked={itemForm.active !== false} onCheckedChange={v => setItemForm(p => ({ ...p, active: v }))} className="w-6 h-6" />
                      <Label className="text-base">Active</Label>
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {(templateColumns[selectedType] || []).map(col => (
                    <div key={col.key} className="space-y-1.5">
                      <Label className="text-base font-semibold">{col.label}</Label>
                      {col.type === "textarea" ? (
                        <Textarea value={itemForm.fields?.[col.key] || ""}
                          onChange={e => setItemForm(p => ({ ...p, fields: { ...p.fields, [col.key]: e.target.value } }))}
                          rows={2} className="text-base rounded-xl" />
                      ) : col.type === "select" ? (
                        <select value={itemForm.fields?.[col.key] || ""}
                          onChange={e => setItemForm(p => ({ ...p, fields: { ...p.fields, [col.key]: e.target.value } }))}
                          className="w-full h-12 px-3 rounded-xl border-2 border-stone-200 bg-white text-base">
                          <option value="">Select</option>
                          {(col.options || []).map(o => <option key={o} value={o}>{o}</option>)}
                        </select>
                      ) : (
                        <Input value={itemForm.fields?.[col.key] || ""}
                          onChange={e => setItemForm(p => ({ ...p, fields: { ...p.fields, [col.key]: e.target.value } }))}
                          type={col.type === "number" ? "number" : "text"} className="h-12 text-base rounded-xl" />
                      )}
                    </div>
                  ))}
                </div>
                <Button onClick={saveTemplateItem} className="h-12 px-6 text-base rounded-xl bg-[#8B0000] hover:bg-[#6B0000]" data-testid="save-item-btn">
                  <Save className="w-5 h-5 mr-1.5" /> Save Item
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Items list — card-based for tablet */}
          <div className="space-y-2">
            {templateItems.map((item, idx) => (
              <div key={item.item_id || idx}
                className="flex items-center gap-4 p-4 bg-white border-2 border-stone-200 rounded-xl"
                data-testid={`template-item-${idx}`}>
                <div className="flex-1 min-w-0">
                  <p className="text-base font-bold text-stone-800">{item.name}</p>
                  <div className="flex gap-3 mt-1 flex-wrap">
                    {(templateColumns[selectedType] || []).slice(0, 3).map(col => (
                      <span key={col.key} className="text-sm text-stone-500">
                        {col.label}: <span className="text-stone-700 font-medium">{item.fields?.[col.key] || "-"}</span>
                      </span>
                    ))}
                  </div>
                </div>
                <Badge variant={item.active !== false ? "default" : "secondary"} className="text-sm px-3 py-1">
                  {item.active !== false ? "Active" : "Off"}
                </Badge>
                {isAdmin && (
                  <div className="flex gap-1">
                    <Button variant="ghost" onClick={() => setItemForm({ ...item })} className="h-10 w-10 rounded-full">
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" onClick={() => toggleTemplateItem(item.item_id, item.active !== false)} className="h-10 w-10 rounded-full">
                      {item.active !== false ? <X className="w-4 h-4 text-red-500" /> : <CheckCircle className="w-4 h-4 text-green-500" />}
                    </Button>
                    <Button variant="ghost" onClick={() => deleteTemplateItem(item.item_id)} className="h-10 w-10 rounded-full">
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </Button>
                  </div>
                )}
              </div>
            ))}
            {templateItems.length === 0 && (
              <div className="p-10 text-center text-stone-400 bg-white border-2 border-dashed border-stone-200 rounded-2xl">
                <FileText className="w-10 h-10 mx-auto mb-3 opacity-40" />
                <p className="text-lg">No template items</p>
                {isAdmin && <p className="text-base mt-1">Click "Seed Templates" or "Add Item" to start</p>}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===== RECORDS TAB ===== */}
      {activeTab === "records" && (
        <div className="space-y-4">
          {/* Filters — collapsible */}
          <div className="flex gap-2 items-center">
            <Button onClick={() => setShowFilters(!showFilters)} variant="outline"
              className="h-12 px-5 rounded-xl text-base border-2" data-testid="filter-sheet-trigger">
              <Filter className="w-5 h-5 mr-1.5" />
              Filters {(recordFilter.template_type || recordFilter.status || recordFilter.date_from) && (
                <span className="ml-1.5 w-2.5 h-2.5 bg-[#8B0000] rounded-full" />
              )}
            </Button>
            <Button onClick={() => downloadReport("pdf")} variant="outline" className="h-12 px-4 rounded-xl text-base border-2" disabled={loading}>
              <Download className="w-5 h-5 mr-1.5" /> PDF
            </Button>
            <Button onClick={() => downloadReport("excel")} variant="outline" className="h-12 px-4 rounded-xl text-base border-2" disabled={loading}>
              <FileSpreadsheet className="w-5 h-5 mr-1.5" /> Excel
            </Button>
          </div>

          {showFilters && (
            <Card className="border-2 border-stone-200 rounded-2xl">
              <CardContent className="p-5 space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label className="text-base font-semibold">Template Type</Label>
                    <select value={recordFilter.template_type}
                      onChange={e => setRecordFilter(p => ({ ...p, template_type: e.target.value }))}
                      className="w-full h-12 px-3 rounded-xl border-2 border-stone-200 bg-white text-base" data-testid="rec-type-filter">
                      <option value="">All Types</option>
                      {recordTypes.map(tt => <option key={tt.key} value={tt.key}>{tt.label}</option>)}
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-base font-semibold">Status</Label>
                    <select value={recordFilter.status}
                      onChange={e => setRecordFilter(p => ({ ...p, status: e.target.value }))}
                      className="w-full h-12 px-3 rounded-xl border-2 border-stone-200 bg-white text-base" data-testid="rec-status-filter">
                      <option value="">All</option>
                      <option value="draft">Draft</option>
                      <option value="submitted">Submitted</option>
                      <option value="approved">Approved</option>
                      <option value="locked">Locked</option>
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-base font-semibold">From Date</Label>
                    <Input type="date" value={recordFilter.date_from} className="h-12 text-base rounded-xl"
                      onChange={e => setRecordFilter(p => ({ ...p, date_from: e.target.value }))} />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-base font-semibold">To Date</Label>
                    <Input type="date" value={recordFilter.date_to} className="h-12 text-base rounded-xl"
                      onChange={e => setRecordFilter(p => ({ ...p, date_to: e.target.value }))} />
                  </div>
                </div>
                <Button onClick={() => { loadRecords(); setShowFilters(false); }}
                  className="h-12 px-6 text-base rounded-xl bg-[#8B0000] hover:bg-[#6B0000] w-full sm:w-auto">
                  <Search className="w-5 h-5 mr-1.5" /> Apply Filters
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Quick add strip */}
          <div className="overflow-x-auto pb-1 -mx-1 px-1">
            <div className="flex gap-2" style={{ minWidth: "max-content" }}>
              {recordTypes.map(tt => {
                const config = TYPE_CONFIG[tt.key] || { icon: FileText, color: "#8B0000", bg: "#fef2f2" };
                const Icon = config.icon;
                return (
                  <button key={tt.key} onClick={() => startNewRecord(tt.key)}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl border-2 border-stone-200 bg-white hover:shadow-md transition-all whitespace-nowrap active:scale-95"
                    data-testid={`new-rec-${tt.key}`}>
                    <Icon className="w-5 h-5" style={{ color: config.color }} />
                    <span className="text-sm font-semibold text-stone-700">{config.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Records list — card-based */}
          <div className="space-y-2">
            {records.map((rec, idx) => {
              const config = TYPE_CONFIG[rec.template_type] || { icon: FileText, color: "#8B0000" };
              const Icon = config.icon;
              return (
                <div key={rec.record_id || idx}
                  className="bg-white border-2 border-stone-200 rounded-xl p-4"
                  style={{ borderLeftWidth: "4px", borderLeftColor: config.color }}
                  data-testid={`record-row-${idx}`}>
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                      style={{ backgroundColor: config.bg || "#f5f5f4" }}>
                      <Icon className="w-5 h-5" style={{ color: config.color }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-base font-bold text-stone-800">{typeLabel(rec.template_type)}</span>
                        <Badge className={`${STATUS_COLORS[rec.status] || ""} text-xs px-2 py-0.5`}>{rec.status}</Badge>
                      </div>
                      <div className="flex gap-4 text-sm text-stone-500 flex-wrap">
                        <span>{rec.record_date}</span>
                        <span>{rec.entries?.length || 0} entries</span>
                        <span>{rec.submittedBy || rec.createdBy || ""}</span>
                      </div>
                    </div>
                    <div className="flex gap-1 shrink-0">
                      {(rec.status === "draft" || rec.status === "submitted") && (
                        <Button variant="ghost" onClick={() => editRecord(rec)} className="h-10 w-10 rounded-full" title="Edit">
                          <Edit className="w-4 h-4" />
                        </Button>
                      )}
                      {rec.status === "submitted" && isAdmin && (
                        <Button variant="ghost" onClick={() => approveRecord(rec.record_id)}
                          className="h-10 w-10 rounded-full text-green-600" title="Approve" data-testid={`approve-${rec.record_id}`}>
                          <CheckCircle className="w-5 h-5" />
                        </Button>
                      )}
                      {(rec.status === "approved" || rec.status === "locked") && (
                        <Button variant="ghost" onClick={() => editRecord(rec)} className="h-10 w-10 rounded-full" title="View">
                          <Eye className="w-4 h-4" />
                        </Button>
                      )}
                      {isAdmin && (
                        <Button variant="ghost" onClick={() => deleteRecord(rec.record_id)}
                          className="h-10 w-10 rounded-full text-red-500" title="Delete" data-testid={`delete-${rec.record_id}`}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
            {records.length === 0 && (
              <div className="p-10 text-center text-stone-400 bg-white border-2 border-dashed border-stone-200 rounded-2xl">
                <FileText className="w-10 h-10 mx-auto mb-3 opacity-40" />
                <p className="text-lg">No records found</p>
                <p className="text-base mt-1">Use the buttons above to create new records</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===== RECORD ENTRY TAB — Card-Based Layout ===== */}
      {activeTab === "record-entry" && recordForm && (() => {
        const entryCols = templateColumns[recordForm.template_type] || columnsRef.current[recordForm.template_type] || [];
        const isReadOnly = recordForm.status === "locked" || recordForm.status === "approved";
        const config = TYPE_CONFIG[recordForm.template_type] || { icon: FileText, color: "#8B0000", bg: "#fef2f2", label: recordForm.template_type };
        const Icon = config.icon;

        return (
          <div className="space-y-4">
            {/* Record header */}
            <div className="flex items-center gap-3 p-4 rounded-2xl border-2"
              style={{ borderColor: config.color, backgroundColor: config.bg }}>
              <div className="w-12 h-12 rounded-xl flex items-center justify-center bg-white shadow-sm">
                <Icon className="w-6 h-6" style={{ color: config.color }} />
              </div>
              <div className="flex-1">
                <h2 className="text-lg font-bold text-stone-800">
                  {recordForm.record_id ? `Edit: ${recordForm.record_id.slice(-8)}` : `New ${config.label}`}
                </h2>
                {isReadOnly && <Badge className={`${STATUS_COLORS[recordForm.status]} mt-1`}>{recordForm.status.toUpperCase()}</Badge>}
              </div>
              <Button variant="ghost" onClick={() => { setRecordForm(null); setActiveTab("records"); }}
                className="h-10 w-10 rounded-full">
                <X className="w-5 h-5" />
              </Button>
            </div>

            {/* Record metadata */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-base font-semibold text-stone-700">Date</Label>
                <Input type="date" value={recordForm.record_date} className="h-14 text-lg rounded-xl border-2"
                  onChange={e => setRecordForm(p => ({ ...p, record_date: e.target.value }))}
                  disabled={isReadOnly} data-testid="record-date" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-base font-semibold text-stone-700">Period</Label>
                <select value={recordForm.period}
                  onChange={e => setRecordForm(p => ({ ...p, period: e.target.value }))}
                  disabled={isReadOnly}
                  className="w-full h-14 px-4 rounded-xl border-2 border-stone-200 bg-white text-lg">
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
            </div>

            {/* Entry cards */}
            {entryCols.length === 0 ? (
              <div className="p-8 text-center border-2 rounded-2xl bg-white">
                <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-stone-400" />
                <p className="text-lg text-stone-500">Loading template...</p>
              </div>
            ) : (
              <div className="space-y-4">
                {recordEntries.map((entry, rowIdx) => (
                  <div key={rowIdx}
                    className="bg-white border-2 border-stone-200 rounded-2xl overflow-hidden"
                    data-testid={`entry-row-${rowIdx}`}>
                    {/* Card header */}
                    <div className="flex items-center justify-between px-5 py-3 border-b border-stone-100"
                      style={{ backgroundColor: config.bg }}>
                      <span className="text-base font-bold" style={{ color: config.color }}>
                        Entry #{rowIdx + 1}
                      </span>
                      {!isReadOnly && recordEntries.length > 1 && (
                        <Button variant="ghost" onClick={() => removeEntryRow(rowIdx)}
                          className="h-9 w-9 rounded-full text-red-500 hover:bg-red-50">
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>

                    {/* Card fields — 2-column grid */}
                    <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {entryCols.map(col => {
                        const dropdownList = getDropdownList(col);
                        const autoFilled = isAutoFilledField(col);
                        const isCalc = col.type === "calculated";
                        // Check fields span full width
                        const isFullWidth = col.type === "textarea" || col.key === "corrective_action" || col.key === "notes" || col.key === "remark";

                        return (
                          <div key={col.key} className={`space-y-1.5 ${isFullWidth ? "sm:col-span-2" : ""}`}>
                            <Label className="text-base font-semibold text-stone-700">
                              {col.label} {col.required && <span className="text-red-500">*</span>}
                            </Label>

                            {/* Check type — special big checkboxes for cleaning record */}
                            {col.type === "check" ? (
                              <div className="flex items-center h-14 px-4 border-2 border-stone-200 rounded-xl bg-white">
                                <Checkbox
                                  checked={entry[col.key] === true || entry[col.key] === "true"}
                                  onCheckedChange={v => updateEntry(rowIdx, col.key, v)}
                                  disabled={isReadOnly}
                                  className="w-7 h-7"
                                />
                                <span className="ml-3 text-lg text-stone-700">{col.label}</span>
                              </div>
                            ) : dropdownList ? (
                              <select value={entry[col.key] || ""}
                                onChange={e => updateEntry(rowIdx, col.key, e.target.value)}
                                disabled={isReadOnly}
                                className="w-full h-14 px-4 rounded-xl border-2 border-stone-200 bg-white text-lg">
                                <option value="">Select...</option>
                                {dropdownList.map((opt, oi) => <option key={oi} value={opt}>{opt}</option>)}
                              </select>
                            ) : autoFilled ? (
                              <Input value={entry[col.key] || ""} readOnly disabled
                                placeholder="Auto from master"
                                className="h-14 text-lg rounded-xl bg-amber-50 border-2 border-amber-200" />
                            ) : isCalc ? (
                              <Input value={entry[col.key] || ""} readOnly disabled
                                placeholder="Auto-calculated"
                                className="h-14 text-lg rounded-xl bg-stone-100 border-2 border-stone-200 font-bold" />
                            ) : col.type === "textarea" ? (
                              <Textarea value={entry[col.key] || ""} rows={2}
                                className="text-lg rounded-xl border-2 min-h-[80px]"
                                onChange={e => updateEntry(rowIdx, col.key, e.target.value)}
                                disabled={isReadOnly} />
                            ) : col.type === "select" ? (
                              <select value={entry[col.key] || ""}
                                onChange={e => updateEntry(rowIdx, col.key, e.target.value)}
                                disabled={isReadOnly}
                                className="w-full h-14 px-4 rounded-xl border-2 border-stone-200 bg-white text-lg">
                                <option value="">Select</option>
                                {(col.options || []).map(o => <option key={o} value={o}>{o}</option>)}
                              </select>
                            ) : (
                              <Input value={entry[col.key] || ""}
                                className="h-14 text-lg rounded-xl border-2"
                                type={col.type === "number" ? "number" : col.type === "date" ? "date" : col.type === "time" ? "time" : "text"}
                                onChange={e => updateEntry(rowIdx, col.key, e.target.value)}
                                disabled={isReadOnly} />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Add row */}
            {!isReadOnly && (
              <Button onClick={addEntryRow} variant="outline"
                className="w-full h-14 text-lg rounded-xl border-2 border-dashed border-stone-300 hover:border-stone-400"
                data-testid="add-entry-row">
                <Plus className="w-5 h-5 mr-2" /> Add Another Entry
              </Button>
            )}

            {/* Notes */}
            {!isReadOnly && (
              <div className="space-y-1.5">
                <Label className="text-base font-semibold text-stone-700">Notes (optional)</Label>
                <Input value={recordForm.notes} onChange={e => setRecordForm(p => ({ ...p, notes: e.target.value }))}
                  placeholder="Any additional notes..." className="h-14 text-lg rounded-xl border-2" />
              </div>
            )}

            {/* Action buttons */}
            {!isReadOnly && (() => {
              const needsApproval = approvalSettings[recordForm.template_type] || false;
              return (
                <div className="space-y-3 pt-2">
                  <div className="grid grid-cols-2 gap-3">
                    <Button onClick={() => saveRecord("draft")} variant="outline" disabled={loading}
                      className="h-14 text-lg rounded-xl border-2" data-testid="save-draft-btn">
                      {loading && <Loader2 className="w-5 h-5 mr-2 animate-spin" />}
                      <Save className="w-5 h-5 mr-2" /> Save Draft
                    </Button>
                    <Button onClick={() => saveRecord("submitted")} disabled={loading}
                      className={`h-14 text-lg rounded-xl font-bold ${needsApproval ? "bg-[#8B0000] hover:bg-[#6B0000]" : "bg-green-600 hover:bg-green-700"}`}
                      data-testid="submit-record-btn">
                      {loading && <Loader2 className="w-5 h-5 mr-2 animate-spin" />}
                      <CheckCircle className="w-5 h-5 mr-2" />
                      {needsApproval ? "Submit" : "Submit"}
                    </Button>
                  </div>
                  <p className="text-base text-stone-500 text-center">
                    {needsApproval ? "Will be sent for admin approval" : "Will be auto-approved on submit"}
                  </p>
                </div>
              );
            })()}

            {/* Read-only info */}
            {isReadOnly && (
              <div className="p-5 bg-green-50 border-2 border-green-200 rounded-2xl">
                <p className="text-base"><strong>Submitted By:</strong> {recordForm.submittedBy || "N/A"} on {recordForm.submittedAt?.split("T")[0] || "N/A"}</p>
                <p className="text-base mt-1"><strong>Approved By:</strong> {recordForm.approvedBy || "N/A"} on {recordForm.approvedAt?.split("T")[0] || "N/A"}</p>
                <Badge className={`${STATUS_COLORS[recordForm.status]} mt-2 text-sm px-3 py-1`}>{recordForm.status.toUpperCase()}</Badge>
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}
