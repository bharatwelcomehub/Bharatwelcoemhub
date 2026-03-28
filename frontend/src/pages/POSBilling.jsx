import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "@/App";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  ShoppingCart, Plus, Minus, Trash2, Printer, Receipt, X, Search,
  CreditCard, Banknote, Smartphone, UtensilsCrossed, ChefHat, Clock,
  Ban, Percent, Hash, Eye, FileText, Leaf, CircleDot, Settings,
  RefreshCw, ListOrdered, Wallet, Truck, Package, LayoutGrid,
  ArrowLeft, Users,
} from "lucide-react";

export default function POSBilling() {
  const { session } = useAuth();
  const [centersList, setCentersList] = useState([]);
  const [selectedCenter, setSelectedCenter] = useState("");
  const [menuItems, setMenuItems] = useState([]);
  const [categories, setCategories] = useState([]);
  const [activeCategory, setActiveCategory] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [billingConfig, setBillingConfig] = useState(null);

  // Order state
  const [currentOrder, setCurrentOrder] = useState(null);
  const [orderItems, setOrderItems] = useState([]);
  const [tableNo, setTableNo] = useState("");
  const [orderType, setOrderType] = useState("DINE-IN");

  // Tables & masters
  const [availableTables, setAvailableTables] = useState([]);
  const [selectedTableId, setSelectedTableId] = useState("");
  const [guestCount, setGuestCount] = useState(1);
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");

  // Active orders
  const [activeOrders, setActiveOrders] = useState([]);
  const [showActiveOrders, setShowActiveOrders] = useState(false);

  // Bill dialog
  const [showBillDialog, setShowBillDialog] = useState(false);
  const [discountType, setDiscountType] = useState("none");
  const [discountValue, setDiscountValue] = useState(0);
  const [paymentMode, setPaymentMode] = useState("CASH");
  const [billCustomerName, setBillCustomerName] = useState("");
  const [billCustomerPhone, setBillCustomerPhone] = useState("");

  // KOT / Receipt dialogs
  const [showKOTDialog, setShowKOTDialog] = useState(false);
  const [kotData, setKotData] = useState(null);
  const [showReceiptDialog, setShowReceiptDialog] = useState(false);
  const [receiptData, setReceiptData] = useState(null);

  // Config dialog
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [configForm, setConfigForm] = useState({});

  // Cancel dialog
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [cancelReasons, setCancelReasons] = useState([]);
  const [selectedCancelReasonId, setSelectedCancelReasonId] = useState("");
  const [cancelReasonText, setCancelReasonText] = useState("");

  // Customer details dialog (for Delivery/Pickup)
  const [showCustomerDialog, setShowCustomerDialog] = useState(false);

  // Guest count dialog (for Dine-In)
  const [showGuestDialog, setShowGuestDialog] = useState(false);

  // Master data
  const [masterPaymentModes, setMasterPaymentModes] = useState([]);
  const [masterOrderTypes, setMasterOrderTypes] = useState([]);
  const [masterDiscountTypes, setMasterDiscountTypes] = useState([]);

  // VIEW MODE: "tables" (landing) vs "order" (menu+panel)
  const [viewMode, setViewMode] = useState("tables");

  const [loading, setLoading] = useState(false);
  const searchRef = useRef(null);
  const isAdmin = session?.is_super_admin || session?.is_admin;

  // ── DATA FETCHING ──
  useEffect(() => {
    const fetchInitial = async () => {
      try {
        const [centersRes, payRes, orderRes, discRes] = await Promise.all([
          api.get("/centers"),
          api.get("/masters/payment_modes"),
          api.get("/masters/order_types"),
          api.get("/masters/discount_types"),
        ]);
        const centers = (centersRes.data.centers || []).filter(c => c.active !== false);
        setCentersList(centers);
        if (!selectedCenter && session?.center) setSelectedCenter(session.center);
        setMasterPaymentModes((payRes.data.items || []).filter(m => m.is_active !== false));
        setMasterOrderTypes((orderRes.data.items || []).filter(m => m.is_active !== false));
        setMasterDiscountTypes((discRes.data.items || []).filter(m => m.is_active !== false));
      } catch {}
    };
    fetchInitial();
  }, [session?.center, selectedCenter]);

  useEffect(() => {
    if (!selectedCenter || !session?.token) return;
    const fetchCenterData = async () => {
      try {
        const [menuRes, configRes, tablesRes, reasonsRes] = await Promise.all([
          api.post("/billing/menu", { token: session.token, center: selectedCenter }),
          api.post("/billing/config/get", { token: session.token, center: selectedCenter }),
          api.post("/billing-config/tables/list", { token: session.token, center: selectedCenter }),
          api.post("/billing-config/cancel-reasons/list", { token: session.token }),
        ]);
        setMenuItems(menuRes.data.items || []);
        setCategories(menuRes.data.categories || []);
        setBillingConfig(configRes.data.config || null);
        setAvailableTables((tablesRes.data.tables || []).filter(t => t.is_active !== false));
        setCancelReasons(reasonsRes.data.reasons || []);
      } catch { toast.error("Failed to load POS data"); }
    };
    fetchCenterData();
    fetchActiveOrders();
  }, [selectedCenter, session?.token]);

  const fetchActiveOrders = useCallback(async () => {
    if (!session?.token || !selectedCenter) return;
    try {
      const res = await api.post("/billing/orders/active", { token: session.token, center: selectedCenter });
      setActiveOrders(res.data.orders || []);
    } catch {}
  }, [session?.token, selectedCenter]);

  const refreshTables = async () => {
    if (!session?.token || !selectedCenter) return;
    try {
      const res = await api.post("/billing-config/tables/list", { token: session.token, center: selectedCenter });
      setAvailableTables((res.data.tables || []).filter(t => t.is_active !== false));
    } catch {}
    fetchActiveOrders();
  };

  // ── TABLE HELPERS ──
  const getTableOrder = (tbl) => activeOrders.find(o =>
    (o.table_id === tbl.table_id || o.table_no === tbl.table_no) && o.status === "active"
  );

  const getTableStatus = (tbl) => {
    const order = getTableOrder(tbl);
    if (!order) return "blank";
    if (order.status === "active" && order.kot_count > 0) return "running_kot";
    if (order.status === "active") return "running";
    return "blank";
  };

  const getElapsedMinutes = (createdAt) => {
    if (!createdAt) return 0;
    return Math.floor((Date.now() - new Date(createdAt).getTime()) / 60000);
  };

  const statusColors = {
    blank: "border-dashed border-2 border-gray-300 bg-gray-50 text-gray-500",
    running: "border-2 border-blue-400 bg-blue-50 text-blue-700",
    running_kot: "border-2 border-yellow-400 bg-yellow-50 text-yellow-700",
    printed: "border-2 border-green-400 bg-green-50 text-green-700",
    paid: "border-2 border-orange-400 bg-orange-50 text-orange-700",
  };

  // ── ORDER ACTIONS ──
  const handleTableClick = async (tbl) => {
    const existingOrder = getTableOrder(tbl);
    if (existingOrder) {
      loadOrder(existingOrder);
      setViewMode("order");
      return;
    }
    setSelectedTableId(tbl.table_id);
    setTableNo(tbl.table_no);
    setOrderType("DINE-IN");
    setGuestCount(1);
    setShowGuestDialog(true);
  };

  const startDineInOrder = async () => {
    if (!guestCount || guestCount < 1) { toast.error("Enter guest count"); return; }
    try {
      const res = await api.post("/billing/order/create", {
        token: session.token, center: selectedCenter,
        table_no: tableNo, table_id: selectedTableId,
        order_type: "DINE-IN", guest_count: guestCount,
        customer_name: "", customer_phone: "",
      });
      setCurrentOrder(res.data.order);
      setOrderItems([]);
      setBillCustomerName("");
      setBillCustomerPhone("");
      setShowGuestDialog(false);
      setViewMode("order");
      refreshTables();
      toast.success(`Table ${tableNo} — Order ${res.data.order.order_id} created`);
    } catch (err) { toast.error(err.response?.data?.detail || "Failed to create order"); }
  };

  const startDeliveryPickup = (type) => {
    setOrderType(type);
    setCustomerName("");
    setCustomerPhone("");
    setShowCustomerDialog(true);
  };

  const createDeliveryPickupOrder = async () => {
    if (!customerName.trim()) { toast.error("Customer name required"); return; }
    if (!customerPhone.trim()) { toast.error("Mobile number required"); return; }
    try {
      const res = await api.post("/billing/order/create", {
        token: session.token, center: selectedCenter,
        table_no: "", table_id: "",
        order_type: orderType, guest_count: 0,
        customer_name: customerName, customer_phone: customerPhone,
      });
      setCurrentOrder(res.data.order);
      setOrderItems([]);
      setBillCustomerName(customerName);
      setBillCustomerPhone(customerPhone);
      setShowCustomerDialog(false);
      setViewMode("order");
      fetchActiveOrders();
      toast.success(`${orderType} order ${res.data.order.order_id} created`);
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };

  const addItemToOrder = async (menuItem) => {
    if (!currentOrder) { toast.error("Create an order first"); return; }
    try {
      const res = await api.post("/billing/order/add-items", {
        token: session.token, order_id: currentOrder.order_id,
        items: [{ item_name: menuItem.name, category: menuItem.category, qty: 1, unit_price: menuItem.price, is_veg: menuItem.is_veg }]
      });
      setCurrentOrder(res.data.order);
      setOrderItems(res.data.order.items || []);
      toast.success(`${menuItem.name} added`);
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };

  const updateQty = async (itemIdx, delta) => {
    if (!currentOrder) return;
    const item = orderItems[itemIdx];
    const newQty = item.qty + delta;
    if (newQty < 1) return;
    try {
      const res = await api.post("/billing/order/update-item", {
        token: session.token, order_id: currentOrder.order_id,
        item_index: itemIdx, qty: newQty,
      });
      setCurrentOrder(res.data.order);
      setOrderItems(res.data.order.items || []);
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };

  const removeItem = async (itemIdx) => {
    if (!currentOrder) return;
    try {
      const res = await api.post("/billing/order/remove-item", {
        token: session.token, order_id: currentOrder.order_id, item_index: itemIdx,
      });
      setCurrentOrder(res.data.order);
      setOrderItems(res.data.order.items || []);
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };

  const sendKOT = async () => {
    if (!currentOrder || orderItems.length === 0) return;
    try {
      const res = await api.post("/billing/kot/generate", {
        token: session.token, order_id: currentOrder.order_id,
      });
      setKotData(res.data.kot);
      setShowKOTDialog(true);
      const orderRes = await api.post("/billing/order/get", { token: session.token, order_id: currentOrder.order_id });
      setCurrentOrder(orderRes.data.order);
      setOrderItems(orderRes.data.order.items || []);
      refreshTables();
      toast.success(`KOT ${res.data.kot.kot_no} sent to kitchen`);
    } catch (err) { toast.error(err.response?.data?.detail || "KOT failed"); }
  };

  const generateBill = async () => {
    if (!currentOrder) return;
    setLoading(true);
    try {
      const res = await api.post("/billing/bill/generate", {
        token: session.token, order_id: currentOrder.order_id,
        payment_mode: paymentMode, discount_type: discountType,
        discount_value: discountValue,
        customer_name: billCustomerName, customer_phone: billCustomerPhone,
      });
      setReceiptData(res.data.bill);
      setShowBillDialog(false);
      setShowReceiptDialog(true);
      setCurrentOrder(null);
      setOrderItems([]);
      setDiscountType("none");
      setDiscountValue(0);
      setBillCustomerName("");
      setBillCustomerPhone("");
      refreshTables();
      toast.success(`Bill ${res.data.bill.bill_no} generated`);
    } catch (err) { toast.error(err.response?.data?.detail || "Billing failed"); }
    finally { setLoading(false); }
  };

  const cancelOrder = async () => {
    if (!currentOrder) return;
    if (!selectedCancelReasonId && !cancelReasonText) { toast.error("Select a cancellation reason"); return; }
    try {
      await api.post("/billing/order/cancel", {
        token: session.token, order_id: currentOrder.order_id,
        reason_id: selectedCancelReasonId,
        reason: cancelReasonText || cancelReasons.find(r => r.reason_id === selectedCancelReasonId)?.reason || "",
      });
      toast.success("Order cancelled");
      setCurrentOrder(null);
      setOrderItems([]);
      setShowCancelDialog(false);
      setSelectedCancelReasonId("");
      setCancelReasonText("");
      setViewMode("tables");
      refreshTables();
    } catch (err) { toast.error(err.response?.data?.detail || "Cancel failed"); }
  };

  const loadOrder = (order) => {
    setCurrentOrder(order);
    setOrderItems(order.items || []);
    setTableNo(order.table_no || "");
    setOrderType(order.order_type || "DINE-IN");
    setShowActiveOrders(false);
  };

  const clearOrder = () => {
    setCurrentOrder(null);
    setOrderItems([]);
    setTableNo("");
  };

  const goBackToTables = () => {
    setViewMode("tables");
    refreshTables();
  };

  const saveConfig = async () => {
    try {
      await api.post("/billing/config/save", { token: session.token, ...configForm });
      toast.success("Billing config saved");
      setShowConfigDialog(false);
      const res = await api.post("/billing/config/get", { token: session.token, center: selectedCenter });
      setBillingConfig(res.data.config);
    } catch (err) { toast.error(err.response?.data?.detail || "Save failed"); }
  };

  // Filtered items
  const currSymbol = billingConfig?.currency_symbol || "₹";
  const filteredItems = menuItems.filter(item => {
    const matchCat = activeCategory === "ALL" || item.category === activeCategory;
    const matchSearch = !searchQuery || item.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchCat && matchSearch;
  });
  const itemTotal = orderItems.reduce((sum, i) => sum + (i.unit_price * i.qty), 0);
  const newItemsCount = orderItems.filter(i => !i.kot_printed).length;

  // ════════════════════════════════════════════
  // RENDER
  // ════════════════════════════════════════════
  return (
    <div className="flex flex-col h-[calc(100vh-80px)] overflow-hidden bg-white" data-testid="pos-billing">

      {/* ═══ TOP HEADER BAR ═══ */}
      <div className="flex items-center gap-3 px-4 py-2 bg-white border-b shadow-sm flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-red-600 to-red-700 flex items-center justify-center">
            <UtensilsCrossed className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-gray-800 text-lg tracking-tight">POS</span>
        </div>

        {viewMode === "tables" && (
          <Button onClick={() => { setOrderType("DINE-IN"); setViewMode("order"); }}
            className="bg-red-600 hover:bg-red-700 text-white font-semibold h-9 px-4 text-sm"
            data-testid="pos-new-order-btn">
            New Order
          </Button>
        )}
        {viewMode === "order" && (
          <Button variant="outline" onClick={goBackToTables}
            className="h-9 px-3 text-sm border-gray-300 text-gray-700 hover:bg-gray-50"
            data-testid="pos-back-tables-btn">
            <ArrowLeft className="w-4 h-4 mr-1" /> Table View
          </Button>
        )}

        <Select value={selectedCenter} onValueChange={setSelectedCenter}>
          <SelectTrigger className="w-[140px] h-9 text-sm border-gray-300" data-testid="pos-center-select">
            <SelectValue placeholder="Center" />
          </SelectTrigger>
          <SelectContent>
            {centersList.map(c => <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>)}
          </SelectContent>
        </Select>

        <div className="flex-1" />

        <Button variant="outline" size="sm"
          onClick={() => { setShowActiveOrders(true); fetchActiveOrders(); }}
          className="h-9 border-gray-300 text-gray-600 text-sm"
          data-testid="pos-active-orders-btn">
          <ListOrdered className="w-4 h-4 mr-1" />
          Orders ({activeOrders.length})
        </Button>

        {isAdmin && (
          <Button variant="ghost" size="icon"
            onClick={() => {
              setConfigForm({
                country: billingConfig?.country || "India",
                gst_percentage: billingConfig?.gst_percentage || 5,
                gst_type: billingConfig?.gst_type || "exclusive",
                service_charge_enabled: billingConfig?.service_charge_enabled || false,
                service_charge_type: billingConfig?.service_charge_type || "percentage",
                service_charge_value: billingConfig?.service_charge_value || 0,
              });
              setShowConfigDialog(true);
            }}
            className="h-9 w-9 text-gray-500 hover:text-gray-700"
            data-testid="pos-config-btn">
            <Settings className="w-4 h-4" />
          </Button>
        )}

        {currentOrder && (
          <Badge className="bg-red-600 text-white text-xs font-semibold">{currentOrder.order_id}</Badge>
        )}
      </div>

      {/* ════════════════════════════════════════════ */}
      {/* TABLE VIEW (Landing) */}
      {/* ════════════════════════════════════════════ */}
      {viewMode === "tables" && (
        <div className="flex-1 overflow-y-auto p-6">
          {/* Title + Action Buttons */}
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-xl font-bold text-gray-800" data-testid="table-view-title">Table View</h1>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="icon" onClick={refreshTables} className="h-9 w-9 text-gray-500">
                <RefreshCw className="w-4 h-4" />
              </Button>
              <Button onClick={() => startDeliveryPickup("DELIVERY")}
                className="bg-red-600 hover:bg-red-700 text-white font-semibold h-9 px-4 text-sm"
                data-testid="pos-delivery-btn">
                <Truck className="w-4 h-4 mr-1.5" /> Delivery
              </Button>
              <Button onClick={() => startDeliveryPickup("TAKEAWAY")}
                className="bg-red-600 hover:bg-red-700 text-white font-semibold h-9 px-4 text-sm"
                data-testid="pos-pickup-btn">
                <Package className="w-4 h-4 mr-1.5" /> Pick Up
              </Button>
            </div>
          </div>

          {/* Status Legend */}
          <div className="flex items-center justify-center gap-6 mb-6 py-3 bg-gray-50 rounded-lg border">
            <div className="flex items-center gap-1.5 text-xs text-gray-600">
              <span className="w-3 h-3 rounded-full bg-gray-300 border border-gray-400" /> Blank Table
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-600">
              <span className="w-3 h-3 rounded-full bg-blue-400" /> Running Table
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-600">
              <span className="w-3 h-3 rounded-full bg-green-500" /> Printed Table
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-600">
              <span className="w-3 h-3 rounded-full bg-orange-400" /> Paid Table
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-600">
              <span className="w-3 h-3 rounded-full bg-yellow-400" /> Running KOT
            </div>
          </div>

          {/* Table Grid */}
          {availableTables.length === 0 ? (
            <div className="text-center py-20 text-gray-400">
              <LayoutGrid className="w-12 h-12 mx-auto mb-3 opacity-40" />
              <p className="text-base font-medium">No tables configured for {selectedCenter || "this center"}</p>
              <p className="text-sm mt-1">Go to Billing Configuration to add tables</p>
            </div>
          ) : (
            <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 xl:grid-cols-12 gap-3" data-testid="table-grid">
              {availableTables.map(tbl => {
                const status = getTableStatus(tbl);
                const order = getTableOrder(tbl);
                const elapsed = order ? getElapsedMinutes(order.created_at) : 0;
                const amount = order ? (order.items || []).reduce((s, i) => s + i.unit_price * i.qty, 0) : 0;

                return (
                  <button
                    key={tbl.table_id}
                    onClick={() => handleTableClick(tbl)}
                    className={`relative rounded-lg p-3 min-h-[100px] flex flex-col items-center justify-center transition-all hover:shadow-md active:scale-95 cursor-pointer ${statusColors[status]}`}
                    data-testid={`table-card-${tbl.table_no}`}
                  >
                    {status !== "blank" && (
                      <span className="text-[10px] font-semibold mb-0.5">{elapsed} Min</span>
                    )}
                    <span className="text-base font-bold">{tbl.table_no}</span>
                    {status !== "blank" && (
                      <span className="text-xs font-semibold mt-0.5">{currSymbol}{amount.toFixed(2)}</span>
                    )}
                    {tbl.capacity && status === "blank" && (
                      <span className="text-[10px] text-gray-400 mt-0.5">{tbl.capacity} pax</span>
                    )}
                  </button>
                );
              })}
            </div>
          )}

          {/* Active Delivery/Pickup Orders */}
          {activeOrders.filter(o => !o.table_no && o.status === "active").length > 0 && (
            <div className="mt-8">
              <h2 className="text-base font-semibold text-gray-700 mb-3">Active Delivery / Pickup Orders</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {activeOrders.filter(o => !o.table_no && o.status === "active").map(o => (
                  <button key={o.order_id} onClick={() => { loadOrder(o); setViewMode("order"); }}
                    className="rounded-lg border-2 border-blue-300 bg-blue-50 p-3 text-left hover:shadow-md transition-all"
                    data-testid={`delivery-order-${o.order_id}`}>
                    <div className="flex items-center gap-1.5 mb-1">
                      {o.order_type?.toUpperCase().includes("DELIVER") ? <Truck className="w-3.5 h-3.5 text-blue-600" /> : <Package className="w-3.5 h-3.5 text-blue-600" />}
                      <span className="text-xs font-semibold text-blue-700">{o.order_type}</span>
                    </div>
                    <p className="text-sm font-bold text-gray-800">{o.order_id}</p>
                    <p className="text-xs text-gray-500 truncate">{o.customer_name || "—"} | {o.customer_phone || "—"}</p>
                    <p className="text-xs font-semibold text-blue-600 mt-1">
                      {currSymbol}{(o.items || []).reduce((s, i) => s + i.unit_price * i.qty, 0).toFixed(2)}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ════════════════════════════════════════════ */}
      {/* ORDER VIEW (Menu + Order Panel) */}
      {/* ════════════════════════════════════════════ */}
      {viewMode === "order" && (
        <>
          {/* Order Type Tabs */}
          <div className="flex border-b flex-shrink-0" data-testid="order-type-tabs">
            {(masterOrderTypes.length > 0
              ? masterOrderTypes.map(t => t.name)
              : ["DINE-IN", "DELIVERY", "TAKEAWAY"]
            ).map(t => (
              <button key={t}
                onClick={() => setOrderType(t)}
                className={`flex-1 py-3 text-sm font-semibold text-center transition-all ${
                  orderType === t
                    ? "bg-red-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
                data-testid={`tab-${t.toLowerCase().replace(/\s/g,'-')}`}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Main Layout: Categories | Menu | Order Panel */}
          <div className="flex flex-1 overflow-hidden">

            {/* LEFT: Categories */}
            <div className="w-[130px] bg-gray-900 overflow-y-auto flex-shrink-0">
              <button onClick={() => setActiveCategory("ALL")}
                className={`w-full text-left px-3 py-3 text-xs font-medium transition-colors ${
                  activeCategory === "ALL" ? "bg-red-600 text-white" : "text-gray-300 hover:bg-gray-800"
                }`} data-testid="pos-cat-all">
                All Items
              </button>
              {categories.map(cat => (
                <button key={cat} onClick={() => setActiveCategory(cat)}
                  className={`w-full text-left px-3 py-3 text-xs font-medium border-t border-gray-800 transition-colors ${
                    activeCategory === cat ? "bg-red-600 text-white" : "text-gray-300 hover:bg-gray-800"
                  }`}>
                  {cat}
                </button>
              ))}
            </div>

            {/* CENTER: Menu Grid */}
            <div className="flex-1 flex flex-col overflow-hidden bg-white">
              {/* Search */}
              <div className="px-3 py-2 border-b">
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-2.5 top-2 text-gray-400" />
                  <Input ref={searchRef} value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Search item"
                    className="pl-8 h-8 text-sm border-gray-300"
                    data-testid="pos-search" />
                  {searchQuery && (
                    <button onClick={() => setSearchQuery("")} className="absolute right-2 top-2 text-gray-400 hover:text-gray-700">
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* Items */}
              <div className="flex-1 overflow-y-auto p-3">
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
                  {filteredItems.map((item, idx) => (
                    <button key={idx} onClick={() => addItemToOrder(item)}
                      className="bg-white hover:bg-gray-50 border border-gray-200 hover:border-red-300 rounded-lg p-3 text-left transition-all active:scale-95"
                      data-testid={`pos-item-${idx}`}>
                      <div className="flex items-start justify-between mb-1">
                        <span className="text-[10px] text-gray-400 truncate max-w-[80%]">{item.category}</span>
                        {item.is_veg ? (
                          <span className="w-4 h-4 border border-green-500 rounded-sm flex items-center justify-center flex-shrink-0">
                            <CircleDot className="w-2.5 h-2.5 text-green-500" />
                          </span>
                        ) : (
                          <span className="w-4 h-4 border border-red-500 rounded-sm flex items-center justify-center flex-shrink-0">
                            <CircleDot className="w-2.5 h-2.5 text-red-500" />
                          </span>
                        )}
                      </div>
                      <p className="text-sm font-medium text-gray-800 leading-tight mb-2 line-clamp-2">{item.name}</p>
                      <p className="text-sm font-bold text-red-600">{currSymbol}{item.price.toFixed(2)}</p>
                    </button>
                  ))}
                  {filteredItems.length === 0 && (
                    <div className="col-span-full text-center py-12 text-gray-400">
                      <UtensilsCrossed className="w-10 h-10 mx-auto mb-2 opacity-40" />
                      <p className="text-sm">No items found</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* RIGHT: Order Panel */}
            <div className="w-[350px] bg-white border-l flex flex-col flex-shrink-0">
              {/* Order Header */}
              <div className="px-3 py-2 border-b flex items-center justify-between bg-gray-50">
                <div className="flex items-center gap-2">
                  <Receipt className="w-4 h-4 text-red-600" />
                  <span className="font-semibold text-gray-800 text-sm">
                    {currentOrder ? currentOrder.order_id : "No Order"}
                  </span>
                </div>
                {currentOrder && (
                  <Badge variant="outline" className="text-[10px] border-gray-300">
                    {currentOrder.table_no || currentOrder.order_type}
                    {currentOrder.guest_count ? ` (${currentOrder.guest_count} pax)` : ""}
                  </Badge>
                )}
              </div>

              {/* Items Header */}
              <div className="flex items-center justify-between px-3 py-1.5 bg-gray-100 text-xs font-semibold text-gray-600 border-b">
                <span>ITEMS</span>
                <div className="flex gap-6">
                  <span>QTY.</span>
                  <span>PRICE</span>
                </div>
              </div>

              {/* Order Items */}
              <div className="flex-1 overflow-y-auto">
                {orderItems.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-gray-300">
                    <ShoppingCart className="w-8 h-8 mb-2 opacity-40" />
                    <p className="text-xs">Select items from menu</p>
                  </div>
                ) : (
                  <div className="divide-y">
                    {orderItems.map((item, idx) => (
                      <div key={idx} className="flex items-center gap-2 px-3 py-2.5" data-testid={`order-item-${idx}`}>
                        <button onClick={() => removeItem(idx)} className="text-red-500 hover:text-red-700 flex-shrink-0">
                          <X className="w-4 h-4" />
                        </button>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-800 leading-tight truncate">{item.item_name}</p>
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          <button onClick={() => updateQty(idx, -1)} className="w-7 h-7 rounded border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-100">
                            <Minus className="w-3 h-3" />
                          </button>
                          <span className="w-7 text-center text-sm font-semibold">{item.qty}</span>
                          <button onClick={() => updateQty(idx, 1)} className="w-7 h-7 rounded border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-100">
                            <Plus className="w-3 h-3" />
                          </button>
                        </div>
                        <div className="text-right flex-shrink-0 w-16">
                          <p className="text-sm font-semibold text-gray-800">{(item.unit_price * item.qty).toFixed(2)}</p>
                          <p className="text-[10px] text-gray-400">{item.unit_price.toFixed(2)}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Total */}
              {orderItems.length > 0 && (
                <div className="border-t px-3 py-2 flex items-center justify-between bg-gray-50">
                  <span className="text-sm font-semibold text-gray-600">Total</span>
                  <span className="text-xl font-bold text-gray-900">{currSymbol}{itemTotal.toFixed(2)}</span>
                </div>
              )}

              {/* Payment Modes */}
              {orderItems.length > 0 && (
                <div className="border-t px-3 py-2">
                  <div className="flex gap-1.5 flex-wrap">
                    {(masterPaymentModes.length > 0
                      ? masterPaymentModes.slice(0, 5).map(m => m.name)
                      : ["CASH", "CARD", "UPI"]
                    ).map(pm => (
                      <button key={pm} onClick={() => setPaymentMode(pm)}
                        className={`px-3 py-1.5 rounded border text-xs font-medium transition-all ${
                          paymentMode === pm
                            ? "border-red-500 bg-red-50 text-red-600"
                            : "border-gray-300 bg-white text-gray-600 hover:border-gray-400"
                        }`}
                        data-testid={`pos-pay-${pm.toLowerCase()}`}>
                        {pm}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="border-t px-3 py-2 flex flex-wrap gap-1.5 bg-gray-50">
                {newItemsCount > 0 && (
                  <Button size="sm" onClick={sendKOT}
                    className="bg-red-600 hover:bg-red-700 text-white text-xs h-8 px-3"
                    data-testid="pos-kot-btn">
                    KOT ({newItemsCount})
                  </Button>
                )}
                {orderItems.length > 0 && (
                  <Button size="sm" onClick={() => setShowBillDialog(true)}
                    className="bg-red-600 hover:bg-red-700 text-white text-xs h-8 px-3"
                    data-testid="pos-bill-btn">
                    Save & Bill
                  </Button>
                )}
                {currentOrder && (
                  <Button size="sm" variant="outline"
                    onClick={() => { setSelectedCancelReasonId(""); setCancelReasonText(""); setShowCancelDialog(true); }}
                    className="text-xs h-8 px-3 border-gray-300 text-gray-600"
                    data-testid="pos-cancel-btn">
                    Cancel
                  </Button>
                )}
                <Button size="sm" variant="outline"
                  onClick={goBackToTables}
                  className="text-xs h-8 px-3 border-gray-300 text-gray-600 ml-auto">
                  Hold
                </Button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* ═══ ALL DIALOGS ═══ */}

      {/* Guest Count Dialog */}
      <Dialog open={showGuestDialog} onOpenChange={setShowGuestDialog}>
        <DialogContent className="max-w-xs">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Users className="w-5 h-5 text-red-600" /> Table {tableNo} — Guests
            </DialogTitle>
          </DialogHeader>
          <div className="flex items-center justify-center gap-4 py-4">
            <button onClick={() => setGuestCount(Math.max(1, guestCount - 1))}
              className="w-10 h-10 rounded-full bg-gray-200 hover:bg-gray-300 text-lg font-bold flex items-center justify-center">-</button>
            <span className="text-4xl font-bold text-red-600 w-16 text-center" data-testid="guest-count-display">{guestCount}</span>
            <button onClick={() => setGuestCount(guestCount + 1)}
              className="w-10 h-10 rounded-full bg-gray-200 hover:bg-gray-300 text-lg font-bold flex items-center justify-center">+</button>
          </div>
          <div className="grid grid-cols-5 gap-1">
            {[1,2,3,4,5,6,8,10,12,15].map(n => (
              <button key={n} onClick={() => setGuestCount(n)}
                className={`py-1.5 rounded text-sm font-medium ${guestCount === n ? "bg-red-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}>{n}</button>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowGuestDialog(false)}>Cancel</Button>
            <Button onClick={startDineInOrder} className="bg-red-600 hover:bg-red-700 text-white" data-testid="start-dinein-btn">Start Order</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Customer Details Dialog (Delivery/Pickup) */}
      <Dialog open={showCustomerDialog} onOpenChange={setShowCustomerDialog}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {orderType === "DELIVERY" ? <Truck className="w-5 h-5 text-red-600" /> : <Package className="w-5 h-5 text-red-600" />}
              {orderType} Order
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Customer Name *</label>
              <Input value={customerName} onChange={e => setCustomerName(e.target.value)}
                placeholder="Full name" data-testid="customer-name-input" />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Mobile Number *</label>
              <Input value={customerPhone} onChange={e => setCustomerPhone(e.target.value)}
                placeholder="10-digit mobile" data-testid="customer-phone-input" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCustomerDialog(false)}>Cancel</Button>
            <Button onClick={createDeliveryPickupOrder} className="bg-red-600 hover:bg-red-700 text-white" data-testid="start-delivery-btn">Start Order</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bill Dialog */}
      <Dialog open={showBillDialog} onOpenChange={setShowBillDialog}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <Receipt className="w-5 h-5" /> Generate Bill
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="text-center py-2 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500">Order Total</p>
              <p className="text-2xl font-bold">{currSymbol}{itemTotal.toFixed(2)}</p>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Discount</label>
              <div className="flex gap-2">
                <Select value={discountType} onValueChange={v => { setDiscountType(v); setDiscountValue(0); }}>
                  <SelectTrigger className="w-[140px] h-9 text-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No Discount</SelectItem>
                    {masterDiscountTypes.filter(d => d.name !== "NO DISCOUNT").map(d => (
                      <SelectItem key={d.name} value={d.name}>{d.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {discountType !== "none" && (
                  <Input type="number" value={discountValue} onChange={e => setDiscountValue(parseFloat(e.target.value) || 0)}
                    className="w-20 h-9 text-sm" placeholder="0" />
                )}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Name</label>
                <Input value={billCustomerName} onChange={e => setBillCustomerName(e.target.value)} placeholder="Optional" className="h-9 text-sm" />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Phone</label>
                <Input value={billCustomerPhone} onChange={e => setBillCustomerPhone(e.target.value)} placeholder="Optional" className="h-9 text-sm" />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBillDialog(false)}>Cancel</Button>
            <Button onClick={generateBill} disabled={loading} className="bg-red-600 hover:bg-red-700 text-white" data-testid="pos-generate-bill">
              {loading ? "Processing..." : "Generate Bill"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* KOT Dialog */}
      <Dialog open={showKOTDialog} onOpenChange={setShowKOTDialog}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle className="flex items-center gap-2"><ChefHat className="w-5 h-5 text-red-600" /> KOT Sent</DialogTitle></DialogHeader>
          {kotData && (
            <div className="space-y-2 text-sm">
              <p><strong>KOT:</strong> {kotData.kot_no}</p>
              <p><strong>Order:</strong> {kotData.order_id}</p>
              <div className="border rounded p-2 bg-gray-50">
                {(kotData.items || []).map((it, i) => (
                  <div key={i} className="flex justify-between py-0.5">
                    <span>{it.item_name}</span><span className="font-semibold">x{it.qty}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <DialogFooter><Button onClick={() => setShowKOTDialog(false)}>Close</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Receipt Dialog */}
      <Dialog open={showReceiptDialog} onOpenChange={setShowReceiptDialog}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle className="flex items-center gap-2"><FileText className="w-5 h-5 text-green-600" /> Bill Receipt</DialogTitle></DialogHeader>
          {receiptData && (
            <div className="space-y-2 text-sm border rounded p-3 bg-gray-50">
              <div className="text-center border-b pb-2">
                <p className="font-bold text-base">Purnabramha</p>
                <p className="text-xs text-gray-500">{receiptData.center}</p>
                <p className="text-xs text-gray-500">Bill: {receiptData.bill_no}</p>
              </div>
              {(receiptData.items || []).map((it, i) => (
                <div key={i} className="flex justify-between py-0.5">
                  <span>{it.item_name} x{it.qty}</span><span>{currSymbol}{(it.unit_price * it.qty).toFixed(2)}</span>
                </div>
              ))}
              <div className="border-t pt-2 space-y-1">
                <div className="flex justify-between"><span>Subtotal</span><span>{currSymbol}{receiptData.subtotal?.toFixed(2)}</span></div>
                {receiptData.gst_amount > 0 && <div className="flex justify-between"><span>GST</span><span>{currSymbol}{receiptData.gst_amount?.toFixed(2)}</span></div>}
                <div className="flex justify-between font-bold text-base border-t pt-1">
                  <span>Total</span><span>{currSymbol}{receiptData.grand_total?.toFixed(2)}</span>
                </div>
                <p className="text-xs text-gray-500 text-center">Paid: {receiptData.payment_mode}</p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => { setShowReceiptDialog(false); setViewMode("tables"); }}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Active Orders Dialog */}
      <Dialog open={showActiveOrders} onOpenChange={setShowActiveOrders}>
        <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Active Orders — {selectedCenter}</DialogTitle></DialogHeader>
          {activeOrders.length === 0 ? (
            <p className="text-center text-gray-500 py-8">No active orders</p>
          ) : (
            <div className="space-y-2">
              {activeOrders.map(o => (
                <button key={o.order_id} onClick={() => { loadOrder(o); setViewMode("order"); }}
                  className="w-full text-left p-3 rounded-lg border hover:border-red-300 hover:bg-red-50 transition-all">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-sm">{o.order_id}</span>
                    <Badge variant="outline" className="text-[10px]">{o.order_type}</Badge>
                  </div>
                  <div className="flex items-center justify-between mt-1 text-xs text-gray-500">
                    <span>{o.table_no || o.customer_name || "—"}</span>
                    <span>{(o.items || []).length} items • {currSymbol}{(o.items || []).reduce((s, i) => s + i.unit_price * i.qty, 0).toFixed(2)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Cancel Dialog */}
      <Dialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-red-600 flex items-center gap-2"><Ban className="w-5 h-5" /> Cancel Order</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <label className="text-xs text-gray-500 block">Reason for cancellation *</label>
            {cancelReasons.filter(r => r.type === "order" && r.is_active !== false).length > 0 ? (
              <Select value={selectedCancelReasonId} onValueChange={v => { setSelectedCancelReasonId(v); setCancelReasonText(""); }}>
                <SelectTrigger data-testid="cancel-reason-select"><SelectValue placeholder="Select reason..." /></SelectTrigger>
                <SelectContent>
                  {cancelReasons.filter(r => r.type === "order" && r.is_active !== false).map(r => (
                    <SelectItem key={r.reason_id} value={r.reason_id}>{r.reason}</SelectItem>
                  ))}
                  <SelectItem value="__other__">Other (specify)</SelectItem>
                </SelectContent>
              </Select>
            ) : null}
            {(selectedCancelReasonId === "__other__" || cancelReasons.filter(r => r.type === "order" && r.is_active !== false).length === 0) && (
              <Input value={cancelReasonText} onChange={e => setCancelReasonText(e.target.value)} placeholder="Enter reason..." data-testid="cancel-reason-text" />
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCancelDialog(false)}>Back</Button>
            <Button onClick={cancelOrder} className="bg-red-600 hover:bg-red-700 text-white" data-testid="confirm-cancel-btn">Confirm Cancel</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Config Dialog */}
      <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle className="flex items-center gap-2"><Settings className="w-5 h-5" /> Billing Configuration</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Country</label>
              <Select value={configForm.country} onValueChange={v => setConfigForm({...configForm, country: v})}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="India">India</SelectItem>
                  <SelectItem value="Australia">Australia</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">GST %</label>
                <Input type="number" value={configForm.gst_percentage} onChange={e => setConfigForm({...configForm, gst_percentage: parseFloat(e.target.value) || 0})} />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">GST Type</label>
                <Select value={configForm.gst_type} onValueChange={v => setConfigForm({...configForm, gst_type: v})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="exclusive">Exclusive</SelectItem>
                    <SelectItem value="inclusive">Inclusive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConfigDialog(false)}>Cancel</Button>
            <Button onClick={saveConfig} className="bg-red-600 hover:bg-red-700 text-white" data-testid="pos-save-config">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
