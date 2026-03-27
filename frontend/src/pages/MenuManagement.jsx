import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { api, fetchCentersFromDB, isAdminUser } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Lock, Search, ChevronDown, ChevronRight, Save, Download, RefreshCw, Eye, EyeOff, Plus } from "lucide-react";

export default function MenuManagement() {
  const { session } = useAuth();
  const [centers, setCenters] = useState([]);
  const [selectedCenter, setSelectedCenter] = useState("");
  const [menuData, setMenuData] = useState(null);
  const [categories, setCategories] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedCats, setExpandedCats] = useState(new Set());
  const [editedPrices, setEditedPrices] = useState({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [showUnavailable, setShowUnavailable] = useState(true);
  const [addItemOpen, setAddItemOpen] = useState(false);
  const [newItem, setNewItem] = useState({ name: "", category: "", base_price: 0, description: "", is_veg: true, serves: "" });

  useEffect(() => {
    if (session?.token) {
      fetchCentersFromDB(session.token).then(c => {
        setCenters(c);
        if (c.length > 0 && !selectedCenter) setSelectedCenter(c[0].code);
      });
      loadCategories();
    }
  }, [session?.token]);

  useEffect(() => {
    if (selectedCenter && session?.token) loadMenu();
  }, [selectedCenter]);

  const loadCategories = async () => {
    try {
      const res = await api.get(`/masters/menu_categories/list?token=${session.token}`);
      setCategories(res.data?.items || []);
    } catch { /* ignore */ }
  };

  const loadMenu = useCallback(async () => {
    if (!selectedCenter || !session?.token) return;
    setLoading(true);
    try {
      const res = await api.get(`/masters/menu-items/by-center/${selectedCenter}?token=${session.token}`);
      setMenuData(res.data);
      setEditedPrices({});
      // Auto-expand all categories
      const cats = new Set((res.data?.items || []).map(i => i.category));
      setExpandedCats(cats);
    } catch (err) {
      toast.error("Failed to load menu: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, [selectedCenter, session?.token]);

  const handlePriceChange = (itemName, field, value) => {
    setEditedPrices(prev => ({
      ...prev,
      [itemName]: { ...(prev[itemName] || {}), [field]: value }
    }));
  };

  const saveChanges = async () => {
    const items = Object.entries(editedPrices).map(([name, changes]) => ({
      name,
      price: changes.price !== undefined ? parseFloat(changes.price) : undefined,
      available: changes.available,
    })).filter(i => i.price !== undefined || i.available !== undefined);

    if (items.length === 0) { toast.info("No changes to save"); return; }
    setSaving(true);
    try {
      const res = await api.post("/masters/menu-items/bulk-set-center-prices", {
        token: session.token, center_code: selectedCenter, items
      });
      toast.success(`Updated ${res.data.updated} items for ${selectedCenter}`);
      setEditedPrices({});
      loadMenu();
    } catch (err) {
      toast.error("Save failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const seedMenuData = async () => {
    setSeeding(true);
    try {
      const res = await api.post("/masters/seed-menu-data", { token: session.token });
      toast.success(`Seeded: ${res.data.categories_created} categories, ${res.data.items_created} new items, ${res.data.items_updated} updated`);
      loadMenu();
      loadCategories();
    } catch (err) {
      toast.error("Seed failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setSeeding(false);
    }
  };

  const addNewItem = async () => {
    if (!newItem.name.trim() || !newItem.category) {
      toast.error("Name and Category are required");
      return;
    }
    try {
      await api.post("/masters/menu_items/create", {
        token: session.token,
        name: newItem.name.trim(),
        category: newItem.category,
        base_price: parseFloat(newItem.base_price) || 0,
        description: newItem.description,
        is_veg: newItem.is_veg,
        serves: newItem.serves,
        center_prices: {},
      });
      toast.success(`Item "${newItem.name}" created`);
      setNewItem({ name: "", category: "", base_price: 0, description: "", is_veg: true, serves: "" });
      setAddItemOpen(false);
      loadMenu();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create item");
    }
  };

  const toggleCat = (cat) => {
    setExpandedCats(prev => {
      const n = new Set(prev);
      n.has(cat) ? n.delete(cat) : n.add(cat);
      return n;
    });
  };

  if (!isAdminUser(session)) {
    return (
      <div className="text-center py-20" data-testid="menu-access-denied">
        <Lock className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
        <h2 className="text-2xl font-bold text-muted-foreground">Access Denied</h2>
        <p className="text-muted-foreground mt-2">Only Admin users can manage menus</p>
      </div>
    );
  }

  const items = menuData?.items || [];
  const filtered = items.filter(i => {
    if (!showUnavailable && !i.available) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      return i.name.toLowerCase().includes(q) || i.category.toLowerCase().includes(q);
    }
    return true;
  });

  // Group by category
  const grouped = {};
  filtered.forEach(i => {
    if (!grouped[i.category]) grouped[i.category] = [];
    grouped[i.category].push(i);
  });
  const catOrder = Object.keys(grouped).sort();

  const symbol = menuData?.symbol || "₹";
  const currency = menuData?.currency || "INR";
  const centerObj = centers.find(c => c.code === selectedCenter);
  const hasChanges = Object.keys(editedPrices).length > 0;

  return (
    <div className="space-y-4" data-testid="menu-management-page">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Menu Management</h1>
          <p className="text-sm text-slate-500">Center-specific menu items and pricing (Admin only)</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button variant="outline" size="sm" onClick={seedMenuData} disabled={seeding} data-testid="seed-menu-btn">
            <RefreshCw className={`w-4 h-4 mr-1 ${seeding ? "animate-spin" : ""}`} /> {seeding ? "Seeding..." : "Seed Menu Data"}
          </Button>
          <Button variant="outline" size="sm" onClick={() => setAddItemOpen(!addItemOpen)} data-testid="add-item-btn">
            <Plus className="w-4 h-4 mr-1" /> Add Item
          </Button>
          {hasChanges && (
            <Button size="sm" onClick={saveChanges} disabled={saving} className="bg-green-600 hover:bg-green-700" data-testid="save-prices-btn">
              <Save className="w-4 h-4 mr-1" /> {saving ? "Saving..." : `Save ${Object.keys(editedPrices).length} Changes`}
            </Button>
          )}
        </div>
      </div>

      {/* Add Item Form */}
      {addItemOpen && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3" data-testid="add-item-form">
          <h3 className="font-semibold text-blue-800">Add New Menu Item</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Input placeholder="Item Name" value={newItem.name} onChange={e => setNewItem(p => ({ ...p, name: e.target.value }))} data-testid="new-item-name" />
            <select className="border rounded px-3 py-2 text-sm" value={newItem.category} onChange={e => setNewItem(p => ({ ...p, category: e.target.value }))} data-testid="new-item-category">
              <option value="">Select Category</option>
              {categories.filter(c => c.is_active !== false).map(c => (
                <option key={c.name} value={c.name}>{c.name}</option>
              ))}
            </select>
            <Input type="number" placeholder="Base Price (INR)" value={newItem.base_price || ""} onChange={e => setNewItem(p => ({ ...p, base_price: e.target.value }))} data-testid="new-item-price" />
            <Input placeholder="Serves (e.g. 4 pcs)" value={newItem.serves} onChange={e => setNewItem(p => ({ ...p, serves: e.target.value }))} data-testid="new-item-serves" />
          </div>
          <div className="flex gap-2">
            <Button size="sm" onClick={addNewItem} data-testid="confirm-add-item">Create Item</Button>
            <Button size="sm" variant="ghost" onClick={() => setAddItemOpen(false)}>Cancel</Button>
          </div>
        </div>
      )}

      {/* Center Selector + Filters */}
      <div className="flex flex-wrap items-center gap-3 bg-white border rounded-lg p-3">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-slate-600">Center:</label>
          <select
            className="border rounded px-3 py-1.5 text-sm font-medium min-w-[220px]"
            value={selectedCenter}
            onChange={e => setSelectedCenter(e.target.value)}
            data-testid="menu-center-select"
          >
            {centers.map(c => (
              <option key={c.code} value={c.code}>{c.code} — {c.name}</option>
            ))}
          </select>
        </div>
        <Badge variant="outline" className="text-xs">
          {currency} ({symbol})
        </Badge>
        {menuData && (
          <Badge variant="secondary" className="text-xs">
            {items.filter(i => i.available).length} available / {items.length} total
          </Badge>
        )}
        <div className="flex-1" />
        <div className="relative">
          <Search className="absolute left-2 top-2 w-4 h-4 text-slate-400" />
          <Input
            placeholder="Search items..."
            className="pl-8 w-56 h-8 text-sm"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            data-testid="menu-search"
          />
        </div>
        <Button variant="ghost" size="sm" onClick={() => setShowUnavailable(!showUnavailable)} data-testid="toggle-unavailable">
          {showUnavailable ? <Eye className="w-4 h-4 mr-1" /> : <EyeOff className="w-4 h-4 mr-1" />}
          {showUnavailable ? "Hide" : "Show"} Unavailable
        </Button>
      </div>

      {/* Menu Items Table */}
      {loading ? (
        <div className="text-center py-12 text-slate-400">Loading menu...</div>
      ) : !menuData ? (
        <div className="text-center py-12 text-slate-400">Select a center to view menu</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-slate-400">No menu items found. Click "Seed Menu Data" to import.</div>
      ) : (
        <div className="bg-white border rounded-lg overflow-hidden" data-testid="menu-items-table">
          {catOrder.map(cat => (
            <div key={cat}>
              {/* Category Header */}
              <div
                className="flex items-center gap-2 px-4 py-2.5 bg-slate-50 border-b cursor-pointer hover:bg-slate-100 transition-colors"
                onClick={() => toggleCat(cat)}
                data-testid={`menu-cat-${cat.replace(/[^a-zA-Z0-9]/g, "-")}`}
              >
                {expandedCats.has(cat) ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronRight className="w-4 h-4 text-slate-500" />}
                <span className="font-semibold text-sm text-slate-700">{cat}</span>
                <Badge variant="outline" className="text-xs ml-1">{grouped[cat].length}</Badge>
              </div>

              {/* Items */}
              {expandedCats.has(cat) && (
                <div className="divide-y divide-slate-100">
                  {/* Column Headers */}
                  <div className="grid grid-cols-12 gap-2 px-4 py-1.5 text-xs font-medium text-slate-400 uppercase tracking-wide bg-slate-50/50">
                    <div className="col-span-4">Item Name</div>
                    <div className="col-span-2">Serves</div>
                    <div className="col-span-2 text-right">Base Price</div>
                    <div className="col-span-2 text-right">Center Price ({symbol})</div>
                    <div className="col-span-2 text-center">Available</div>
                  </div>
                  {grouped[cat].map(item => {
                    const edited = editedPrices[item.name] || {};
                    const currentPrice = edited.price !== undefined ? edited.price : item.center_price;
                    const currentAvail = edited.available !== undefined ? edited.available : item.available;
                    const isEdited = edited.price !== undefined || edited.available !== undefined;

                    return (
                      <div
                        key={item.name}
                        className={`grid grid-cols-12 gap-2 px-4 py-2 items-center text-sm ${!currentAvail ? "opacity-50 bg-red-50/30" : ""} ${isEdited ? "bg-yellow-50" : ""}`}
                        data-testid={`menu-item-${item.name.replace(/[^a-zA-Z0-9]/g, "-")}`}
                      >
                        <div className="col-span-4 flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${item.is_veg ? "bg-green-500" : "bg-red-500"}`} />
                          <span className="font-medium text-slate-700 truncate">{item.name}</span>
                        </div>
                        <div className="col-span-2 text-slate-500 text-xs">{item.serves || "-"}</div>
                        <div className="col-span-2 text-right text-slate-400 text-xs">
                          {currency === "INR" ? `₹${item.base_price}` : `₹${item.base_price}`}
                        </div>
                        <div className="col-span-2 text-right">
                          <Input
                            type="number"
                            step="0.01"
                            className={`h-7 text-right text-sm w-24 ml-auto ${isEdited ? "border-yellow-400 bg-yellow-50" : ""}`}
                            value={currentPrice}
                            onChange={e => handlePriceChange(item.name, "price", e.target.value)}
                            data-testid={`price-input-${item.name.replace(/[^a-zA-Z0-9]/g, "-")}`}
                          />
                        </div>
                        <div className="col-span-2 flex justify-center">
                          <button
                            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${currentAvail ? "bg-green-100 text-green-700 hover:bg-green-200" : "bg-red-100 text-red-700 hover:bg-red-200"}`}
                            onClick={() => handlePriceChange(item.name, "available", !currentAvail)}
                            data-testid={`avail-toggle-${item.name.replace(/[^a-zA-Z0-9]/g, "-")}`}
                          >
                            {currentAvail ? "Yes" : "No"}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
