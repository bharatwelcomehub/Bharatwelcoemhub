import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "@/App";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  ShoppingCart,
  Plus,
  Minus,
  Trash2,
  Printer,
  Receipt,
  X,
  Search,
  CreditCard,
  Banknote,
  Smartphone,
  UtensilsCrossed,
  ChefHat,
  Clock,
  Ban,
  Percent,
  Hash,
  Eye,
  FileText,
  Leaf,
  CircleDot,
  Settings,
  RefreshCw,
  ListOrdered,
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
  const [orderType, setOrderType] = useState("Dine-In");

  // NEW: Pre-order flow state
  const [availableTables, setAvailableTables] = useState([]);
  const [selectedTableId, setSelectedTableId] = useState("");
  const [guestCount, setGuestCount] = useState(1);
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [showPreOrderDialog, setShowPreOrderDialog] = useState(false);
  const [preOrderStep, setPreOrderStep] = useState("type"); // "type" | "table" | "guest" | "customer"

  // Active orders
  const [activeOrders, setActiveOrders] = useState([]);
  const [showActiveOrders, setShowActiveOrders] = useState(false);

  // Bill dialog
  const [showBillDialog, setShowBillDialog] = useState(false);
  const [billPreview, setBillPreview] = useState(null);
  const [discountType, setDiscountType] = useState("none");
  const [discountValue, setDiscountValue] = useState(0);
  const [paymentMode, setPaymentMode] = useState("Cash");
  const [billCustomerName, setBillCustomerName] = useState("");
  const [billCustomerPhone, setBillCustomerPhone] = useState("");

  // KOT print dialog
  const [showKOTDialog, setShowKOTDialog] = useState(false);
  const [kotData, setKotData] = useState(null);

  // Bill receipt dialog
  const [showReceiptDialog, setShowReceiptDialog] = useState(false);
  const [receiptData, setReceiptData] = useState(null);

  // Config dialog
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [configForm, setConfigForm] = useState({});

  // Cancel dialog - now with master reasons
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [cancelReasons, setCancelReasons] = useState([]);
  const [selectedCancelReasonId, setSelectedCancelReasonId] = useState("");
  const [cancelReasonText, setCancelReasonText] = useState("");

  const [loading, setLoading] = useState(false);
  const searchRef = useRef(null);

  const isAdmin = session?.is_super_admin || session?.is_admin;

  // Fetch centers
  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await api.get("/centers");
        const centers = (res.data.centers || []).filter(c => c.active !== false);
        setCentersList(centers);
        if (!selectedCenter && session?.center) {
          setSelectedCenter(session.center);
        }
      } catch {}
    };
    fetch();
  }, [session?.center, selectedCenter]);

  // Fetch menu & config when center changes
  useEffect(() => {
    if (!selectedCenter || !session?.token) return;
    const fetchMenu = async () => {
      try {
        const [menuRes, configRes, tablesRes, reasonsRes] = await Promise.all([
          api.post("/billing/menu", { token: session.token, center: selectedCenter }),
          api.post("/billing/config/get", { token: session.token, center: selectedCenter }),
          api.post("/billing-config/tables/list", { token: session.token, center: selectedCenter }),
          api.post("/billing-config/cancel-reasons/list", { token: session.token, type: "order" }),
        ]);
        setMenuItems(menuRes.data.items || []);
        setCategories(menuRes.data.categories || []);
        setBillingConfig(configRes.data.config || null);
        setAvailableTables((tablesRes.data.tables || []).filter(t => t.is_active !== false));
        setCancelReasons(reasonsRes.data.reasons || []);
      } catch (err) {
        toast.error("Failed to load menu");
      }
    };
    fetchMenu();
    fetchActiveOrders();
  }, [selectedCenter, session?.token]);

  const fetchActiveOrders = useCallback(async () => {
    if (!selectedCenter || !session?.token) return;
    try {
      const res = await api.post("/billing/orders/active", { token: session.token, center: selectedCenter });
      setActiveOrders(res.data.orders || []);
    } catch {}
  }, [selectedCenter, session?.token]);

  // Filter menu items
  const filteredItems = menuItems.filter(item => {
    const matchCat = activeCategory === "ALL" || item.category === activeCategory;
    const matchSearch = !searchQuery || item.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchCat && matchSearch;
  });

  const currSymbol = billingConfig?.currency_symbol || "\u20b9";

  // ── ORDER ACTIONS ──

  const openNewOrderFlow = () => {
    if (!selectedCenter) { toast.error("Select a center first"); return; }
    setOrderType("Dine-In");
    setSelectedTableId("");
    setTableNo("");
    setGuestCount(1);
    setCustomerName("");
    setCustomerPhone("");
    setPreOrderStep("type");
    setShowPreOrderDialog(true);
  };

  const proceedPreOrder = () => {
    if (preOrderStep === "type") {
      if (orderType === "Dine-In") {
        setPreOrderStep("table");
      } else {
        setPreOrderStep("customer");
      }
    } else if (preOrderStep === "table") {
      if (!selectedTableId && !tableNo) {
        toast.error("Please select a table");
        return;
      }
      setPreOrderStep("guest");
    } else if (preOrderStep === "guest") {
      if (!guestCount || guestCount < 1) {
        toast.error("Please enter guest count");
        return;
      }
      createOrderFromFlow();
    } else if (preOrderStep === "customer") {
      if (!customerName.trim()) {
        toast.error("Customer name is required");
        return;
      }
      if (!customerPhone.trim()) {
        toast.error("Customer phone is required");
        return;
      }
      createOrderFromFlow();
    }
  };

  const createOrderFromFlow = async () => {
    try {
      const selectedTable = availableTables.find(t => t.table_id === selectedTableId);
      const res = await api.post("/billing/order/create", {
        token: session.token,
        center: selectedCenter,
        table_no: selectedTable?.table_no || tableNo,
        table_id: selectedTableId || "",
        order_type: orderType,
        guest_count: orderType === "Dine-In" ? guestCount : 0,
        customer_name: customerName,
        customer_phone: customerPhone,
      });
      setCurrentOrder(res.data.order);
      setOrderItems([]);
      setBillCustomerName(customerName);
      setBillCustomerPhone(customerPhone);
      setShowPreOrderDialog(false);
      // Refresh tables to update occupied status
      const tablesRes = await api.post("/billing-config/tables/list", { token: session.token, center: selectedCenter });
      setAvailableTables((tablesRes.data.tables || []).filter(t => t.is_active !== false));
      toast.success(`Order ${res.data.order.order_id} created`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create order");
    }
  };

  const startNewOrder = () => {
    openNewOrderFlow();
  };

  const addItemToOrder = async (menuItem) => {
    if (!currentOrder) {
      // Must go through pre-order flow
      openNewOrderFlow();
      return;
    }

    // Check if item already exists - increment qty
    const existingIdx = orderItems.findIndex(
      i => i.item_name === menuItem.name && !i.kot_printed
    );

    if (existingIdx >= 0) {
      try {
        const newQty = orderItems[existingIdx].qty + 1;
        const res = await api.post("/billing/order/update-item-qty", {
          token: session.token,
          order_id: currentOrder.order_id,
          item_index: existingIdx,
          qty: newQty,
        });
        setCurrentOrder(res.data.order);
        setOrderItems(res.data.order.items || []);
      } catch (err) {
        toast.error(err.response?.data?.detail || "Failed to update qty");
      }
      return;
    }

    // Add new item
    try {
      const res = await api.post("/billing/order/add-items", {
        token: session.token,
        order_id: currentOrder.order_id,
        items: [{
          item_name: menuItem.name,
          category: menuItem.category,
          qty: 1,
          unit_price: menuItem.price,
          is_veg: menuItem.is_veg,
        }]
      });
      setCurrentOrder(res.data.order);
      setOrderItems(res.data.order.items || []);
      toast.success(`${menuItem.name} added`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to add item");
    }
  };

  const updateQty = async (index, delta) => {
    if (!currentOrder) return;
    const item = orderItems[index];
    const newQty = item.qty + delta;
    try {
      const res = await api.post("/billing/order/update-item-qty", {
        token: session.token,
        order_id: currentOrder.order_id,
        item_index: index,
        qty: newQty,
      });
      setCurrentOrder(res.data.order);
      setOrderItems(res.data.order.items || []);
      if (newQty <= 0) toast.info("Item removed");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed");
    }
  };

  const sendKOT = async () => {
    if (!currentOrder) return;
    const newItems = orderItems.filter(i => !i.kot_printed);
    if (newItems.length === 0) {
      toast.info("No new items to send to kitchen");
      return;
    }
    try {
      const res = await api.post("/billing/kot/generate", {
        token: session.token,
        order_id: currentOrder.order_id,
      });
      setKotData(res.data.kot);
      setShowKOTDialog(true);
      // Refresh order
      const orderRes = await api.post("/billing/order/get", {
        token: session.token,
        order_id: currentOrder.order_id,
      });
      setCurrentOrder(orderRes.data.order);
      setOrderItems(orderRes.data.order.items || []);
      fetchActiveOrders();
      toast.success(`KOT ${res.data.kot.kot_no} sent to kitchen`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "KOT failed");
    }
  };

  const openBillDialog = async () => {
    if (!currentOrder || orderItems.length === 0) {
      toast.error("No items in order");
      return;
    }
    try {
      const res = await api.post("/billing/bill/preview", {
        token: session.token,
        order_id: currentOrder.order_id,
        center: selectedCenter,
        discount_type: discountType,
        discount_value: discountValue,
      });
      setBillPreview(res.data.calculation);
      setShowBillDialog(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Preview failed");
    }
  };

  const refreshBillPreview = async () => {
    if (!currentOrder) return;
    try {
      const res = await api.post("/billing/bill/preview", {
        token: session.token,
        order_id: currentOrder.order_id,
        center: selectedCenter,
        discount_type: discountType,
        discount_value: discountValue,
      });
      setBillPreview(res.data.calculation);
    } catch {}
  };

  const generateBill = async () => {
    if (!currentOrder) return;
    setLoading(true);
    try {
      const res = await api.post("/billing/bill/generate", {
        token: session.token,
        order_id: currentOrder.order_id,
        payment_mode: paymentMode,
        discount_type: discountType,
        discount_value: discountValue,
        customer_name: billCustomerName,
        customer_phone: billCustomerPhone,
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
      // Refresh tables
      const tablesRes = await api.post("/billing-config/tables/list", { token: session.token, center: selectedCenter });
      setAvailableTables((tablesRes.data.tables || []).filter(t => t.is_active !== false));
      fetchActiveOrders();
      toast.success(`Bill ${res.data.bill.bill_no} generated`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Billing failed");
    } finally {
      setLoading(false);
    }
  };

  const cancelOrder = async () => {
    if (!currentOrder) return;
    if (!selectedCancelReasonId && !cancelReasonText) {
      toast.error("Please select a cancellation reason");
      return;
    }
    try {
      await api.post("/billing/order/cancel", {
        token: session.token,
        order_id: currentOrder.order_id,
        reason_id: selectedCancelReasonId,
        reason: cancelReasonText || cancelReasons.find(r => r.reason_id === selectedCancelReasonId)?.reason || "",
      });
      toast.success("Order cancelled");
      setCurrentOrder(null);
      setOrderItems([]);
      setShowCancelDialog(false);
      setSelectedCancelReasonId("");
      setCancelReasonText("");
      // Refresh tables
      const tablesRes = await api.post("/billing-config/tables/list", { token: session.token, center: selectedCenter });
      setAvailableTables((tablesRes.data.tables || []).filter(t => t.is_active !== false));
      fetchActiveOrders();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Cancel failed");
    }
  };

  const loadOrder = async (order) => {
    setCurrentOrder(order);
    setOrderItems(order.items || []);
    setTableNo(order.table_no || "");
    setOrderType(order.order_type || "Dine-In");
    setShowActiveOrders(false);
  };

  const clearOrder = () => {
    setCurrentOrder(null);
    setOrderItems([]);
    setTableNo("");
  };

  const saveConfig = async () => {
    try {
      await api.post("/billing/config/save", {
        token: session.token,
        ...configForm,
      });
      toast.success("Billing config saved");
      setShowConfigDialog(false);
      // Refresh config
      const res = await api.post("/billing/config/get", { token: session.token, center: selectedCenter });
      setBillingConfig(res.data.config);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Save failed");
    }
  };

  const itemTotal = orderItems.reduce((sum, i) => sum + (i.unit_price * i.qty), 0);
  const newItemsCount = orderItems.filter(i => !i.kot_printed).length;

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] overflow-hidden" data-testid="pos-billing">
      {/* ── TOP BAR ── */}
      <div className="flex items-center gap-3 px-4 py-2 bg-slate-900 border-b border-slate-700 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
            <UtensilsCrossed className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-white text-lg">POS</span>
        </div>

        <Select value={selectedCenter} onValueChange={setSelectedCenter}>
          <SelectTrigger className="w-[130px] bg-slate-800 border-slate-600 text-white text-sm h-8" data-testid="pos-center-select">
            <SelectValue placeholder="Center" />
          </SelectTrigger>
          <SelectContent>
            {centersList.map(c => (
              <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={orderType} onValueChange={setOrderType}>
          <SelectTrigger className="w-[110px] bg-slate-800 border-slate-600 text-white text-sm h-8" data-testid="pos-order-type-select">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="Dine-In">Dine-In</SelectItem>
            <SelectItem value="Takeaway">Takeaway</SelectItem>
            <SelectItem value="Delivery">Delivery</SelectItem>
          </SelectContent>
        </Select>

        <Button
          size="sm"
          onClick={openNewOrderFlow}
          disabled={!!currentOrder}
          className="h-8 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
          data-testid="pos-new-order-btn"
        >
          <Plus className="w-3.5 h-3.5 mr-1" />
          New Order
        </Button>

        <div className="flex-1" />

        <Button
          variant="outline"
          size="sm"
          onClick={() => { setShowActiveOrders(true); fetchActiveOrders(); }}
          className="h-8 border-slate-600 text-slate-300 hover:text-white hover:bg-slate-700 text-xs"
          data-testid="pos-active-orders-btn"
        >
          <ListOrdered className="w-3.5 h-3.5 mr-1" />
          Orders ({activeOrders.length})
        </Button>

        {isAdmin && (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => {
              setConfigForm({
                country: billingConfig?.country || "India",
                gst_percentage: billingConfig?.gst_percentage || 5,
                gst_type: billingConfig?.gst_type || "exclusive",
                service_charge_enabled: billingConfig?.service_charge_enabled || false,
                service_charge_type: billingConfig?.service_charge_type || "percentage",
                service_charge_value: billingConfig?.service_charge_value || 0,
                currency_symbol: billingConfig?.currency_symbol || "\u20b9",
                currency_code: billingConfig?.currency_code || "INR",
              });
              setShowConfigDialog(true);
            }}
            className="h-8 w-8 text-slate-400 hover:text-white"
            data-testid="pos-config-btn"
          >
            <Settings className="w-4 h-4" />
          </Button>
        )}

        {currentOrder && (
          <Badge className="bg-emerald-600 text-white text-xs">
            {currentOrder.order_id}
          </Badge>
        )}
      </div>

      {/* ── MAIN LAYOUT: Categories | Menu Grid | Order Panel ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* LEFT: Categories */}
        <div className="w-[120px] bg-slate-800 border-r border-slate-700 overflow-y-auto flex-shrink-0">
          <button
            onClick={() => setActiveCategory("ALL")}
            className={`w-full text-left px-3 py-2.5 text-xs font-medium transition-colors ${
              activeCategory === "ALL"
                ? "bg-amber-600 text-white"
                : "text-slate-300 hover:bg-slate-700"
            }`}
            data-testid="pos-cat-all"
          >
            All Items
          </button>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`w-full text-left px-3 py-2.5 text-xs font-medium transition-colors border-t border-slate-700/50 ${
                activeCategory === cat
                  ? "bg-amber-600 text-white"
                  : "text-slate-300 hover:bg-slate-700"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* CENTER: Menu Grid */}
        <div className="flex-1 flex flex-col overflow-hidden bg-slate-900/50">
          {/* Search */}
          <div className="px-3 py-2 border-b border-slate-700/50">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-2.5 top-2 text-slate-500" />
              <Input
                ref={searchRef}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search menu..."
                className="pl-8 bg-slate-800 border-slate-600 text-white text-sm h-8"
                data-testid="pos-search"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery("")} className="absolute right-2 top-2 text-slate-500 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {/* Items Grid */}
          <div className="flex-1 overflow-y-auto p-3">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
              {filteredItems.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => addItemToOrder(item)}
                  className="group relative bg-slate-800 hover:bg-slate-700 border border-slate-700/50 hover:border-amber-500/50 rounded-lg p-3 text-left transition-all active:scale-95"
                  data-testid={`pos-item-${idx}`}
                >
                  <div className="flex items-start justify-between mb-1">
                    <span className="text-[11px] text-slate-400 truncate max-w-[80%]">{item.category}</span>
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
                  <p className="text-sm font-medium text-slate-200 leading-tight mb-2 line-clamp-2">
                    {item.name}
                  </p>
                  <p className="text-sm font-bold text-amber-400">
                    {currSymbol}{item.price.toFixed(2)}
                  </p>
                  <div className="absolute inset-0 rounded-lg border-2 border-amber-500 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                </button>
              ))}
              {filteredItems.length === 0 && (
                <div className="col-span-full text-center py-12 text-slate-500">
                  <UtensilsCrossed className="w-10 h-10 mx-auto mb-2 opacity-40" />
                  <p className="text-sm">No items found</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT: Order Panel */}
        <div className="w-[320px] bg-slate-900 border-l border-slate-700 flex flex-col flex-shrink-0">
          {/* Order Header */}
          <div className="px-3 py-2 border-b border-slate-700 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShoppingCart className="w-4 h-4 text-amber-400" />
              <span className="font-semibold text-white text-sm">
                {currentOrder ? `Order` : "New Order"}
              </span>
            </div>
            {currentOrder && (
              <div className="flex items-center gap-1">
                <Badge variant="outline" className="text-[10px] border-slate-600 text-slate-400">
                  {currentOrder.table_no || "No Table"}
                  {currentOrder.guest_count ? ` (${currentOrder.guest_count} pax)` : ""}
                </Badge>
                <Button variant="ghost" size="icon" onClick={clearOrder} className="h-6 w-6 text-slate-500 hover:text-red-400">
                  <X className="w-3.5 h-3.5" />
                </Button>
              </div>
            )}
          </div>

          {/* Order Items */}
          <div className="flex-1 overflow-y-auto">
            {orderItems.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-500">
                <ShoppingCart className="w-10 h-10 mb-2 opacity-30" />
                <p className="text-sm">Tap items to add</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-800">
                {orderItems.map((item, idx) => (
                  <div key={idx} className={`px-3 py-2 ${item.kot_printed ? "bg-slate-800/30" : ""}`}>
                    <div className="flex items-start justify-between mb-1">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-200 truncate">
                          {item.item_name}
                        </p>
                        <p className="text-[11px] text-slate-500">
                          {currSymbol}{item.unit_price.toFixed(2)} each
                          {item.kot_printed && (
                            <span className="ml-1 text-emerald-400">(KOT sent)</span>
                          )}
                        </p>
                      </div>
                      <p className="text-sm font-bold text-amber-400 ml-2">
                        {currSymbol}{(item.unit_price * item.qty).toFixed(2)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => updateQty(idx, -1)}
                        disabled={item.kot_printed}
                        className="w-6 h-6 rounded bg-slate-700 hover:bg-red-600 flex items-center justify-center text-white disabled:opacity-30 disabled:hover:bg-slate-700 transition-colors"
                      >
                        {item.qty === 1 ? <Trash2 className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                      </button>
                      <span className="text-sm font-bold text-white w-6 text-center">{item.qty}</span>
                      <button
                        onClick={() => updateQty(idx, 1)}
                        disabled={item.kot_printed}
                        className="w-6 h-6 rounded bg-slate-700 hover:bg-emerald-600 flex items-center justify-center text-white disabled:opacity-30 disabled:hover:bg-slate-700 transition-colors"
                      >
                        <Plus className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Order Summary */}
          {orderItems.length > 0 && (
            <div className="border-t border-slate-700 px-3 py-2 bg-slate-800/50">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-400">Items Total</span>
                <span className="font-bold text-white">{currSymbol}{itemTotal.toFixed(2)}</span>
              </div>
              {billingConfig && (
                <div className="flex justify-between text-xs mb-2">
                  <span className="text-slate-500">
                    GST {billingConfig.gst_percentage}% ({billingConfig.gst_type})
                  </span>
                  <span className="text-slate-400">
                    {billingConfig.gst_type === "inclusive" ? "incl." : `+${currSymbol}${(itemTotal * billingConfig.gst_percentage / 100).toFixed(2)}`}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="border-t border-slate-700 p-2 space-y-1.5 bg-slate-900">
            <div className="grid grid-cols-2 gap-1.5">
              <Button
                onClick={sendKOT}
                disabled={!currentOrder || newItemsCount === 0}
                className="h-10 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold"
                data-testid="pos-kot-btn"
              >
                <ChefHat className="w-4 h-4 mr-1" />
                KOT ({newItemsCount})
              </Button>
              <Button
                onClick={() => setShowCancelDialog(true)}
                disabled={!currentOrder}
                variant="outline"
                className="h-10 border-red-600/50 text-red-400 hover:bg-red-600/20 text-xs font-semibold"
                data-testid="pos-cancel-btn"
              >
                <Ban className="w-4 h-4 mr-1" />
                Cancel
              </Button>
            </div>
            <Button
              onClick={openBillDialog}
              disabled={!currentOrder || orderItems.length === 0}
              className="w-full h-12 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-bold text-sm shadow-lg shadow-amber-600/20"
              data-testid="pos-bill-btn"
            >
              <Receipt className="w-5 h-5 mr-2" />
              Generate Bill &middot; {currSymbol}{itemTotal.toFixed(2)}
            </Button>
          </div>
        </div>
      </div>

      {/* ═══ BILL DIALOG ═══ */}
      <Dialog open={showBillDialog} onOpenChange={setShowBillDialog}>
        <DialogContent className="max-w-md bg-slate-900 border-slate-700 text-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-400">
              <Receipt className="w-5 h-5" /> Generate Bill
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {/* Discount */}
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Discount</label>
              <div className="flex gap-2">
                <Select value={discountType} onValueChange={(v) => { setDiscountType(v); setDiscountValue(0); }}>
                  <SelectTrigger className="w-[120px] bg-slate-800 border-slate-600 text-white text-sm h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    <SelectItem value="percentage">% Discount</SelectItem>
                    <SelectItem value="fixed">Fixed Amount</SelectItem>
                  </SelectContent>
                </Select>
                {discountType !== "none" && (
                  <Input
                    type="number"
                    value={discountValue}
                    onChange={(e) => setDiscountValue(parseFloat(e.target.value) || 0)}
                    onBlur={refreshBillPreview}
                    placeholder={discountType === "percentage" ? "%" : currSymbol}
                    className="flex-1 bg-slate-800 border-slate-600 text-white h-9"
                    data-testid="pos-discount-input"
                  />
                )}
              </div>
            </div>

            {/* Payment Mode */}
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Payment Mode</label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { value: "Cash", icon: Banknote, label: "Cash" },
                  { value: "UPI", icon: Smartphone, label: "UPI" },
                  { value: "Card", icon: CreditCard, label: "Card" },
                ].map(pm => (
                  <button
                    key={pm.value}
                    onClick={() => setPaymentMode(pm.value)}
                    className={`flex flex-col items-center gap-1 p-3 rounded-lg border transition-all ${
                      paymentMode === pm.value
                        ? "border-amber-500 bg-amber-500/10 text-amber-400"
                        : "border-slate-700 bg-slate-800 text-slate-400 hover:border-slate-600"
                    }`}
                    data-testid={`pos-pay-${pm.value.toLowerCase()}`}
                  >
                    <pm.icon className="w-5 h-5" />
                    <span className="text-xs font-medium">{pm.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Customer Info */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-slate-400 mb-1 block">Customer Name</label>
                <Input value={billCustomerName} onChange={e => setBillCustomerName(e.target.value)} placeholder="Optional" className="bg-slate-800 border-slate-600 text-white h-8 text-sm" />
              </div>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">Phone</label>
                <Input value={billCustomerPhone} onChange={e => setBillCustomerPhone(e.target.value)} placeholder="Optional" className="bg-slate-800 border-slate-600 text-white h-8 text-sm" />
              </div>
            </div>

            {/* Bill Preview */}
            {billPreview && (
              <div className="bg-slate-800 rounded-lg p-3 space-y-1.5 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Subtotal</span>
                  <span className="text-white">{currSymbol}{billPreview.subtotal?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">GST ({billPreview.gst_percentage}% {billPreview.gst_type})</span>
                  <span className="text-white">{currSymbol}{billPreview.gst_amount?.toFixed(2)}</span>
                </div>
                {billPreview.service_charge_amount > 0 && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Service Charge</span>
                    <span className="text-white">{currSymbol}{billPreview.service_charge_amount?.toFixed(2)}</span>
                  </div>
                )}
                {billPreview.discount_amount > 0 && (
                  <div className="flex justify-between text-emerald-400">
                    <span>Discount ({billPreview.discount_type === "percentage" ? `${billPreview.discount_value}%` : "Fixed"})</span>
                    <span>-{currSymbol}{billPreview.discount_amount?.toFixed(2)}</span>
                  </div>
                )}
                <div className="border-t border-slate-700 pt-1.5 flex justify-between">
                  <span className="font-bold text-amber-400 text-base">Grand Total</span>
                  <span className="font-bold text-amber-400 text-base">{currSymbol}{billPreview.grand_total?.toFixed(2)}</span>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBillDialog(false)} className="border-slate-600 text-slate-300">Cancel</Button>
            <Button onClick={generateBill} disabled={loading} className="bg-amber-600 hover:bg-amber-500 text-white" data-testid="pos-confirm-bill">
              {loading ? "Processing..." : "Confirm & Print Bill"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ═══ KOT PRINT DIALOG ═══ */}
      <Dialog open={showKOTDialog} onOpenChange={setShowKOTDialog}>
        <DialogContent className="max-w-[350px] bg-white text-black p-0">
          <div className="p-4" id="kot-print" data-testid="kot-print-view">
            {kotData && (
              <div className="font-mono text-center">
                <p className="text-lg font-bold border-b-2 border-dashed border-black pb-1 mb-2">KITCHEN ORDER</p>
                <p className="text-base font-bold">{kotData.kot_no}</p>
                <div className="flex justify-between text-sm mt-1 mb-2">
                  <span>Table: {kotData.table_no || "-"}</span>
                  <span>{kotData.order_type}</span>
                </div>
                <p className="text-xs text-gray-600 mb-2">
                  {new Date(kotData.printed_at).toLocaleString()}
                </p>
                <div className="border-t border-dashed border-black pt-2">
                  <div className="flex justify-between text-sm font-bold mb-1">
                    <span>Item</span>
                    <span>Qty</span>
                  </div>
                  {kotData.items?.map((item, i) => (
                    <div key={i} className="flex justify-between text-sm py-1 border-b border-dotted border-gray-300">
                      <span className="flex items-center gap-1 text-left flex-1">
                        {item.is_veg ? (
                          <span className="w-3 h-3 border border-green-600 rounded-sm inline-flex items-center justify-center flex-shrink-0">
                            <span className="w-1.5 h-1.5 rounded-full bg-green-600"></span>
                          </span>
                        ) : (
                          <span className="w-3 h-3 border border-red-600 rounded-sm inline-flex items-center justify-center flex-shrink-0">
                            <span className="w-1.5 h-1.5 rounded-full bg-red-600"></span>
                          </span>
                        )}
                        {item.item_name}
                        {item.notes && <span className="text-xs text-gray-500 ml-1">({item.notes})</span>}
                      </span>
                      <span className="font-bold text-lg ml-2">{item.qty}</span>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-3">Order: {kotData.order_id}</p>
                <p className="text-xs text-gray-500">By: {kotData.printed_by}</p>
              </div>
            )}
          </div>
          <div className="p-3 border-t flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowKOTDialog(false)} size="sm">Close</Button>
            <Button onClick={() => window.print()} size="sm" className="bg-sky-600 hover:bg-sky-500 text-white">
              <Printer className="w-4 h-4 mr-1" /> Print KOT
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ═══ RECEIPT DIALOG ═══ */}
      <Dialog open={showReceiptDialog} onOpenChange={setShowReceiptDialog}>
        <DialogContent className="max-w-[380px] bg-white text-black p-0">
          <div className="p-4" id="receipt-print" data-testid="receipt-print-view">
            {receiptData && (
              <div className="font-mono text-center">
                <p className="text-xl font-bold">Purnabramha</p>
                <p className="text-xs text-gray-500 mb-1">Tax Invoice</p>
                <div className="border-t-2 border-dashed border-black my-2" />
                <p className="text-sm font-bold">{receiptData.bill_no}</p>
                <div className="flex justify-between text-xs mt-1">
                  <span>Table: {receiptData.table_no || "-"}</span>
                  <span>{receiptData.order_type}</span>
                </div>
                <p className="text-xs text-gray-500">
                  {new Date(receiptData.created_at).toLocaleString()}
                </p>
                {receiptData.customer_name && (
                  <p className="text-xs mt-1">Customer: {receiptData.customer_name}</p>
                )}
                <div className="border-t border-dashed border-black my-2" />
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-gray-300">
                      <th className="text-left py-1">Item</th>
                      <th className="text-center">Qty</th>
                      <th className="text-right">Amt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {receiptData.items?.map((item, i) => (
                      <tr key={i} className="border-b border-dotted border-gray-200">
                        <td className="text-left py-1 pr-1">{item.item_name}</td>
                        <td className="text-center">{item.qty}</td>
                        <td className="text-right">{receiptData.currency_symbol}{(item.unit_price * item.qty).toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="border-t border-dashed border-black my-2" />
                <div className="text-xs space-y-0.5">
                  <div className="flex justify-between">
                    <span>Subtotal</span>
                    <span>{receiptData.currency_symbol}{receiptData.subtotal?.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>GST ({receiptData.gst_percentage}% {receiptData.gst_type})</span>
                    <span>{receiptData.currency_symbol}{receiptData.gst_amount?.toFixed(2)}</span>
                  </div>
                  {receiptData.service_charge_amount > 0 && (
                    <div className="flex justify-between">
                      <span>Service Charge</span>
                      <span>{receiptData.currency_symbol}{receiptData.service_charge_amount?.toFixed(2)}</span>
                    </div>
                  )}
                  {receiptData.discount_amount > 0 && (
                    <div className="flex justify-between text-green-700">
                      <span>Discount</span>
                      <span>-{receiptData.currency_symbol}{receiptData.discount_amount?.toFixed(2)}</span>
                    </div>
                  )}
                </div>
                <div className="border-t-2 border-black my-2" />
                <div className="flex justify-between text-base font-bold">
                  <span>TOTAL</span>
                  <span>{receiptData.currency_symbol}{receiptData.grand_total?.toFixed(2)}</span>
                </div>
                <div className="border-t border-dashed border-black my-2" />
                <p className="text-xs">Paid via: {receiptData.payment_mode}</p>
                <p className="text-xs text-gray-400 mt-2">Thank you for dining with us!</p>
                <p className="text-[10px] text-gray-400">{receiptData.center}</p>
              </div>
            )}
          </div>
          <div className="p-3 border-t flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowReceiptDialog(false)} size="sm">Close</Button>
            <Button onClick={() => window.print()} size="sm" className="bg-amber-600 hover:bg-amber-500 text-white">
              <Printer className="w-4 h-4 mr-1" /> Print Receipt
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ═══ ACTIVE ORDERS DIALOG ═══ */}
      <Dialog open={showActiveOrders} onOpenChange={setShowActiveOrders}>
        <DialogContent className="max-w-lg bg-slate-900 border-slate-700 text-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ListOrdered className="w-5 h-5 text-amber-400" /> Active Orders
              <Button variant="ghost" size="icon" onClick={fetchActiveOrders} className="h-7 w-7 ml-auto text-slate-400">
                <RefreshCw className="w-4 h-4" />
              </Button>
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {activeOrders.length === 0 ? (
              <p className="text-center text-slate-500 py-6">No active orders</p>
            ) : activeOrders.map(order => (
              <div
                key={order.order_id}
                className="flex items-center justify-between p-3 rounded-lg bg-slate-800 border border-slate-700 hover:border-amber-500/50 cursor-pointer transition-colors"
                onClick={() => loadOrder(order)}
                data-testid={`active-order-${order.order_id}`}
              >
                <div>
                  <p className="text-sm font-semibold text-white">{order.order_id}</p>
                  <p className="text-xs text-slate-400">
                    Table: {order.table_no || "-"} &middot; {order.items?.length || 0} items &middot; {order.order_type}
                  </p>
                </div>
                <div className="text-right">
                  <Badge className={order.status === "kot_printed" ? "bg-sky-600" : "bg-emerald-600"}>
                    {order.status === "kot_printed" ? "KOT Sent" : "Active"}
                  </Badge>
                  <p className="text-xs text-slate-500 mt-1">
                    {new Date(order.created_at).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {/* ═══ CANCEL ORDER DIALOG ═══ */}
      <Dialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <DialogContent className="max-w-sm bg-slate-900 border-slate-700 text-white">
          <DialogHeader>
            <DialogTitle className="text-red-400 flex items-center gap-2">
              <Ban className="w-5 h-5" /> Cancel Order
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <label className="text-xs text-slate-400 mb-1 block">Reason for cancellation *</label>
            {cancelReasons.filter(r => r.type === "order" && r.is_active !== false).length > 0 ? (
              <Select value={selectedCancelReasonId} onValueChange={(v) => { setSelectedCancelReasonId(v); setCancelReasonText(""); }}>
                <SelectTrigger className="bg-slate-800 border-slate-600 text-white" data-testid="pos-cancel-reason-select">
                  <SelectValue placeholder="Select reason..." />
                </SelectTrigger>
                <SelectContent>
                  {cancelReasons.filter(r => r.type === "order" && r.is_active !== false).map(r => (
                    <SelectItem key={r.reason_id} value={r.reason_id}>{r.reason}</SelectItem>
                  ))}
                  <SelectItem value="__other__">Other (specify)</SelectItem>
                </SelectContent>
              </Select>
            ) : null}
            {(selectedCancelReasonId === "__other__" || cancelReasons.filter(r => r.type === "order" && r.is_active !== false).length === 0) && (
              <Input
                value={cancelReasonText}
                onChange={e => setCancelReasonText(e.target.value)}
                placeholder="Enter reason..."
                className="bg-slate-800 border-slate-600 text-white"
                data-testid="pos-cancel-reason-text"
              />
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCancelDialog(false)} className="border-slate-600 text-slate-300">Back</Button>
            <Button onClick={cancelOrder} className="bg-red-600 hover:bg-red-500 text-white" data-testid="pos-confirm-cancel">
              Confirm Cancel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ═══ BILLING CONFIG DIALOG ═══ */}
      <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
        <DialogContent className="max-w-md bg-slate-900 border-slate-700 text-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-400">
              <Settings className="w-5 h-5" /> Billing Configuration
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Country</label>
              <Select value={configForm.country} onValueChange={v => setConfigForm({...configForm, country: v})}>
                <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="India">India</SelectItem>
                  <SelectItem value="Australia">Australia</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 mb-1 block">GST %</label>
                <Input
                  type="number"
                  value={configForm.gst_percentage}
                  onChange={e => setConfigForm({...configForm, gst_percentage: parseFloat(e.target.value) || 0})}
                  className="bg-slate-800 border-slate-600 text-white"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">GST Type</label>
                <Select value={configForm.gst_type} onValueChange={v => setConfigForm({...configForm, gst_type: v})}>
                  <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="exclusive">Exclusive (add on top)</SelectItem>
                    <SelectItem value="inclusive">Inclusive (in price)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <label className="text-sm text-slate-300">Service Charge</label>
              <input
                type="checkbox"
                checked={configForm.service_charge_enabled || false}
                onChange={e => setConfigForm({...configForm, service_charge_enabled: e.target.checked})}
                className="accent-amber-500"
              />
            </div>
            {configForm.service_charge_enabled && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Type</label>
                  <Select value={configForm.service_charge_type} onValueChange={v => setConfigForm({...configForm, service_charge_type: v})}>
                    <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="percentage">Percentage %</SelectItem>
                      <SelectItem value="fixed">Fixed Amount</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Value</label>
                  <Input
                    type="number"
                    value={configForm.service_charge_value}
                    onChange={e => setConfigForm({...configForm, service_charge_value: parseFloat(e.target.value) || 0})}
                    className="bg-slate-800 border-slate-600 text-white"
                  />
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConfigDialog(false)} className="border-slate-600 text-slate-300">Cancel</Button>
            <Button onClick={saveConfig} className="bg-amber-600 hover:bg-amber-500 text-white" data-testid="pos-save-config">
              Save Configuration
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ═══ PRE-ORDER FLOW DIALOG ═══ */}
      <Dialog open={showPreOrderDialog} onOpenChange={setShowPreOrderDialog}>
        <DialogContent className="max-w-md bg-slate-900 border-slate-700 text-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-400">
              <Receipt className="w-5 h-5" /> New Order — {
                preOrderStep === "type" ? "Select Type" :
                preOrderStep === "table" ? "Select Table" :
                preOrderStep === "guest" ? "Guest Count" :
                "Customer Details"
              }
            </DialogTitle>
          </DialogHeader>

          {/* Step: Order Type */}
          {preOrderStep === "type" && (
            <div className="space-y-3" data-testid="pre-order-step-type">
              <p className="text-sm text-slate-400">What type of order?</p>
              <div className="grid grid-cols-3 gap-3">
                {["Dine-In", "Takeaway", "Delivery"].map(t => (
                  <button
                    key={t}
                    onClick={() => setOrderType(t)}
                    className={`p-4 rounded-lg border-2 text-center transition-all ${
                      orderType === t
                        ? "border-amber-500 bg-amber-500/10 text-amber-400"
                        : "border-slate-700 bg-slate-800 text-slate-400 hover:border-slate-600"
                    }`}
                    data-testid={`pre-order-type-${t.toLowerCase()}`}
                  >
                    <div className="text-2xl mb-1">
                      {t === "Dine-In" ? "🍽" : t === "Takeaway" ? "📦" : "🛵"}
                    </div>
                    <span className="text-sm font-medium">{t}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step: Table Selection (Dine-In only) */}
          {preOrderStep === "table" && (
            <div className="space-y-3" data-testid="pre-order-step-table">
              <p className="text-sm text-slate-400">Select a table for Dine-In</p>
              {availableTables.filter(t => t.status === "available").length > 0 ? (
                <div className="grid grid-cols-3 gap-2 max-h-[300px] overflow-y-auto">
                  {availableTables.filter(t => t.status === "available").map(t => (
                    <button
                      key={t.table_id}
                      onClick={() => { setSelectedTableId(t.table_id); setTableNo(t.table_no); }}
                      className={`p-3 rounded-lg border-2 text-center transition-all ${
                        selectedTableId === t.table_id
                          ? "border-amber-500 bg-amber-500/10"
                          : "border-slate-700 bg-slate-800 hover:border-slate-600"
                      }`}
                      data-testid={`pre-order-table-${t.table_no}`}
                    >
                      <p className="font-bold text-white text-lg">{t.table_no}</p>
                      <p className="text-[11px] text-slate-400">{t.capacity} pax</p>
                      <p className="text-[10px] text-slate-500">{t.floor}{t.section ? ` / ${t.section}` : ""}</p>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="py-6 text-center">
                  <p className="text-slate-500 text-sm mb-2">No tables configured or all occupied</p>
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Enter table manually</label>
                    <Input
                      value={tableNo}
                      onChange={e => { setTableNo(e.target.value); setSelectedTableId(""); }}
                      placeholder="e.g. T1"
                      className="bg-slate-800 border-slate-600 text-white text-center"
                      data-testid="pre-order-manual-table"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step: Guest Count (Dine-In only) */}
          {preOrderStep === "guest" && (
            <div className="space-y-3" data-testid="pre-order-step-guest">
              <p className="text-sm text-slate-400">
                Table: <span className="text-white font-semibold">{tableNo || selectedTableId}</span> — How many guests?
              </p>
              <div className="flex items-center justify-center gap-4 py-4">
                <button
                  onClick={() => setGuestCount(Math.max(1, guestCount - 1))}
                  className="w-12 h-12 rounded-full bg-slate-700 hover:bg-slate-600 text-white text-xl font-bold flex items-center justify-center"
                >
                  -
                </button>
                <span className="text-5xl font-bold text-amber-400 w-20 text-center" data-testid="pre-order-guest-count">{guestCount}</span>
                <button
                  onClick={() => setGuestCount(guestCount + 1)}
                  className="w-12 h-12 rounded-full bg-slate-700 hover:bg-slate-600 text-white text-xl font-bold flex items-center justify-center"
                >
                  +
                </button>
              </div>
              <div className="grid grid-cols-5 gap-1.5">
                {[1,2,3,4,5,6,7,8,10,12].map(n => (
                  <button
                    key={n}
                    onClick={() => setGuestCount(n)}
                    className={`py-2 rounded text-sm font-medium transition-all ${
                      guestCount === n ? "bg-amber-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step: Customer Details (Takeaway/Delivery) */}
          {preOrderStep === "customer" && (
            <div className="space-y-3" data-testid="pre-order-step-customer">
              <p className="text-sm text-slate-400">Customer details for {orderType}</p>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">Customer Name *</label>
                <Input
                  value={customerName}
                  onChange={e => setCustomerName(e.target.value)}
                  placeholder="Full name"
                  className="bg-slate-800 border-slate-600 text-white"
                  data-testid="pre-order-customer-name"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">Mobile Number *</label>
                <Input
                  value={customerPhone}
                  onChange={e => setCustomerPhone(e.target.value)}
                  placeholder="10-digit mobile"
                  className="bg-slate-800 border-slate-600 text-white"
                  data-testid="pre-order-customer-phone"
                />
              </div>
            </div>
          )}

          <DialogFooter>
            {preOrderStep !== "type" && (
              <Button
                variant="outline"
                onClick={() => {
                  if (preOrderStep === "table") setPreOrderStep("type");
                  else if (preOrderStep === "guest") setPreOrderStep("table");
                  else if (preOrderStep === "customer") setPreOrderStep("type");
                }}
                className="border-slate-600 text-slate-300"
              >
                Back
              </Button>
            )}
            <Button
              onClick={proceedPreOrder}
              className="bg-amber-600 hover:bg-amber-500 text-white"
              data-testid="pre-order-proceed-btn"
            >
              {(preOrderStep === "guest" || preOrderStep === "customer") ? "Start Order" : "Next"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
