import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/App";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  ChevronUp,
  ChevronDown,
  RotateCcw,
  Save,
  LayoutGrid,
  AlertTriangle,
} from "lucide-react";
import { MENU_DEFAULTS } from "@/lib/menuDefaults";

const API = process.env.REACT_APP_BACKEND_URL || "";

const ROLE_OPTIONS = [
  { key: "super_admin", label: "Super Admin", locked: true },
  { key: "admin", label: "Admin" },
  { key: "mgt", label: "Management" },
  { key: "accounting", label: "Accounts" },
  { key: "attendance", label: "Attendance" },
  { key: "sales_cash", label: "Sales & Cash" },
  { key: "hr", label: "HR" },
  { key: "operations", label: "Operations" },
  { key: "franchise", label: "Franchise" },
  { key: "billing", label: "Billing / POS" },
  { key: "international", label: "International" },
  { key: "center_manager", label: "Center Manager" },
  { key: "franchise_owner", label: "Franchise Owner" },
  { key: "staff", label: "Staff" },
];

// Build a working menu structure (categories with items and per-row roles)
// from defaults + saved overrides.
function buildState(overrides) {
  const itemOv = overrides?.items || {};
  const catOv = overrides?.categories || {};

  // Re-parent items by override.category_id
  const itemsByCat = {};
  MENU_DEFAULTS.forEach(c => { itemsByCat[c.id] = []; });
  MENU_DEFAULTS.forEach((cat, ci) => {
    cat.items.forEach((item, ii) => {
      const ov = itemOv[item.path] || {};
      const parent = ov.category_id && itemsByCat[ov.category_id] !== undefined ? ov.category_id : cat.id;
      const order = ov.order !== undefined && ov.order !== null ? ov.order : (ci * 1000 + ii);
      itemsByCat[parent].push({
        path: item.path,
        label: item.label,
        order,
        visible_roles: ov.visible_roles ?? null, // null = no override (uses defaults)
      });
    });
  });
  Object.keys(itemsByCat).forEach(cid => {
    itemsByCat[cid].sort((a, b) => a.order - b.order);
    itemsByCat[cid] = itemsByCat[cid].map((it, idx) => ({ ...it, order: idx }));
  });

  const cats = MENU_DEFAULTS.map((c, idx) => {
    const ov = catOv[c.id] || {};
    return {
      id: c.id,
      label: c.label,
      order: ov.order !== undefined && ov.order !== null ? ov.order : idx,
      visible_roles: ov.visible_roles ?? null,
      items: itemsByCat[c.id] || [],
    };
  });
  cats.sort((a, b) => a.order - b.order);
  cats.forEach((c, i) => { c.order = i; });
  return cats;
}

// Convert working state back to override doc (only persist diffs vs default order
// and explicit role-overrides). Simpler approach: persist EVERYTHING — it's a
// small JSON and keeps the model trivial.
function stateToOverrides(cats) {
  const categories = {};
  const items = {};
  cats.forEach((cat, ci) => {
    categories[cat.id] = {
      order: ci,
      ...(cat.visible_roles ? { visible_roles: cat.visible_roles } : {}),
    };
    cat.items.forEach((item, ii) => {
      items[item.path] = {
        category_id: cat.id,
        order: ii,
        ...(item.visible_roles ? { visible_roles: item.visible_roles } : {}),
      };
    });
  });
  return { categories, items };
}

export default function MenuConfig() {
  const { session } = useAuth();
  const isSuperAdmin = session?.is_super_admin === true;
  const [cats, setCats] = useState(() => buildState({}));
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [updatedBy, setUpdatedBy] = useState(null);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!session?.token || !isSuperAdmin) return;
    const load = async () => {
      try {
        const res = await fetch(`${API}/api/menu-config?token=${encodeURIComponent(session.token)}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setCats(buildState(data));
        setUpdatedAt(data.updated_at);
        setUpdatedBy(data.updated_by);
      } catch (e) {
        toast.error("Failed to load menu config");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [session?.token, isSuperAdmin]);

  const moveCategory = (idx, dir) => {
    const next = [...cats];
    const j = idx + dir;
    if (j < 0 || j >= next.length) return;
    [next[idx], next[j]] = [next[j], next[idx]];
    setCats(next);
    setDirty(true);
  };

  const moveItem = (catIdx, itemIdx, dir) => {
    const next = cats.map(c => ({ ...c, items: [...c.items] }));
    const arr = next[catIdx].items;
    const j = itemIdx + dir;
    if (j < 0 || j >= arr.length) return;
    [arr[itemIdx], arr[j]] = [arr[j], arr[itemIdx]];
    setCats(next);
    setDirty(true);
  };

  const moveItemBetweenCats = (fromCatIdx, itemIdx, toCatId) => {
    const next = cats.map(c => ({ ...c, items: [...c.items] }));
    const targetIdx = next.findIndex(c => c.id === toCatId);
    if (targetIdx < 0 || targetIdx === fromCatIdx) return;
    const [moved] = next[fromCatIdx].items.splice(itemIdx, 1);
    next[targetIdx].items.push(moved);
    setCats(next);
    setDirty(true);
  };

  const toggleItemRole = (catIdx, itemIdx, roleKey, checked) => {
    const next = cats.map(c => ({ ...c, items: [...c.items.map(i => ({ ...i })) ] }));
    const item = next[catIdx].items[itemIdx];
    const current = new Set(item.visible_roles || []);
    if (checked) current.add(roleKey); else current.delete(roleKey);
    item.visible_roles = Array.from(current);
    setCats(next);
    setDirty(true);
  };

  const clearItemRoleOverride = (catIdx, itemIdx) => {
    const next = cats.map(c => ({ ...c, items: [...c.items.map(i => ({ ...i })) ] }));
    next[catIdx].items[itemIdx].visible_roles = null;
    setCats(next);
    setDirty(true);
  };

  const toggleCategoryRole = (catIdx, roleKey, checked) => {
    const next = [...cats];
    const cat = { ...next[catIdx] };
    const current = new Set(cat.visible_roles || []);
    if (checked) current.add(roleKey); else current.delete(roleKey);
    cat.visible_roles = Array.from(current);
    next[catIdx] = cat;
    setCats(next);
    setDirty(true);
  };

  const clearCategoryRoleOverride = (catIdx) => {
    const next = [...cats];
    next[catIdx] = { ...next[catIdx], visible_roles: null };
    setCats(next);
    setDirty(true);
  };

  const saveAll = async () => {
    setSaving(true);
    try {
      const body = {
        token: session.token,
        ...stateToOverrides(cats),
      };
      const res = await fetch(`${API}/api/menu-config/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setUpdatedAt(data.updated_at);
      setDirty(false);
      toast.success("Menu configuration saved. Other users will see changes within a minute.");
    } catch (e) {
      toast.error("Save failed: " + (e.message || "unknown"));
    } finally {
      setSaving(false);
    }
  };

  const resetAll = async () => {
    if (!confirm("Reset menu configuration to defaults? This cannot be undone.")) return;
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/menu-config/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: session.token }),
      });
      if (!res.ok) throw new Error(await res.text());
      setCats(buildState({}));
      setUpdatedAt(null);
      setUpdatedBy(null);
      setDirty(false);
      toast.success("Menu reset to defaults");
    } catch (e) {
      toast.error("Reset failed");
    } finally {
      setSaving(false);
    }
  };

  const categoryOptions = useMemo(() => cats.map(c => ({ id: c.id, label: c.label })), [cats]);

  if (!isSuperAdmin) {
    return (
      <div className="p-6">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-6 flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-red-600" />
            <div>
              <p className="font-semibold text-red-700">Access denied</p>
              <p className="text-sm text-red-600">Only Super Admins can customize the menu.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (loading) return <div className="p-6 text-gray-500">Loading menu configuration…</div>;

  return (
    <div className="space-y-6" data-testid="menu-config-page">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <LayoutGrid className="w-6 h-6 text-[#7B1E2A]" /> Menu Customization
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Reorder sidebar categories &amp; items, move items between categories, and control which roles can see them.
            Super Admin always sees everything.
          </p>
          {updatedAt && (
            <p className="text-xs text-gray-400 mt-1">
              Last saved: {new Date(updatedAt).toLocaleString()} {updatedBy ? `by ${updatedBy}` : ""}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {dirty && (
            <Badge variant="outline" className="border-amber-400 text-amber-700 bg-amber-50">
              Unsaved changes
            </Badge>
          )}
          <Button
            variant="outline"
            onClick={resetAll}
            disabled={saving}
            data-testid="menu-reset-btn"
          >
            <RotateCcw className="w-4 h-4 mr-1.5" /> Reset to defaults
          </Button>
          <Button
            onClick={saveAll}
            disabled={saving || !dirty}
            className="bg-[#7B1E2A] hover:bg-[#5a1620] text-white"
            data-testid="menu-save-btn"
          >
            <Save className="w-4 h-4 mr-1.5" /> {saving ? "Saving…" : "Save Configuration"}
          </Button>
        </div>
      </div>

      <div className="space-y-4">
        {cats.map((cat, ci) => (
          <Card key={cat.id} className="border-gray-200" data-testid={`menu-cat-${cat.id}`}>
            <CardHeader className="bg-gray-50 border-b py-3">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-2">
                  <div className="flex flex-col">
                    <button
                      className="hover:bg-gray-200 rounded p-0.5"
                      onClick={() => moveCategory(ci, -1)}
                      disabled={ci === 0}
                      title="Move category up"
                      data-testid={`cat-up-${cat.id}`}
                    >
                      <ChevronUp className="w-4 h-4" />
                    </button>
                    <button
                      className="hover:bg-gray-200 rounded p-0.5"
                      onClick={() => moveCategory(ci, 1)}
                      disabled={ci === cats.length - 1}
                      title="Move category down"
                      data-testid={`cat-down-${cat.id}`}
                    >
                      <ChevronDown className="w-4 h-4" />
                    </button>
                  </div>
                  <CardTitle className="text-base font-bold text-[#7B1E2A]">
                    {cat.label}
                  </CardTitle>
                  <Badge variant="outline" className="text-xs text-gray-500">
                    {cat.items.length} item{cat.items.length === 1 ? "" : "s"}
                  </Badge>
                </div>
              </div>
              <div className="mt-2">
                <div className="flex items-center gap-2 flex-wrap text-xs">
                  <span className="text-gray-500 font-semibold">Category visible to:</span>
                  {cat.visible_roles === null ? (
                    <span className="text-gray-400 italic">using code defaults</span>
                  ) : (
                    <button
                      className="text-blue-600 hover:underline text-xs"
                      onClick={() => clearCategoryRoleOverride(ci)}
                    >
                      Clear override (use defaults)
                    </button>
                  )}
                </div>
                <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5">
                  {ROLE_OPTIONS.map(r => (
                    <label key={r.key} className="flex items-center gap-1.5 text-xs">
                      <Checkbox
                        checked={(cat.visible_roles || []).includes(r.key) || r.locked}
                        disabled={r.locked}
                        onCheckedChange={(checked) => toggleCategoryRole(ci, r.key, !!checked)}
                        data-testid={`cat-role-${cat.id}-${r.key}`}
                      />
                      <span className={r.locked ? "text-gray-400" : "text-gray-700"}>{r.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </CardHeader>

            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead className="bg-white border-b">
                  <tr>
                    <th className="text-left px-4 py-2 font-semibold text-gray-600 w-16">Order</th>
                    <th className="text-left px-4 py-2 font-semibold text-gray-600">Item</th>
                    <th className="text-left px-4 py-2 font-semibold text-gray-600 w-44">Move to category</th>
                    <th className="text-left px-4 py-2 font-semibold text-gray-600">Visible to roles</th>
                  </tr>
                </thead>
                <tbody>
                  {cat.items.map((item, ii) => (
                    <tr key={item.path} className="border-b last:border-b-0 hover:bg-gray-50/50" data-testid={`menu-item-${item.path}`}>
                      <td className="px-4 py-3 align-top">
                        <div className="flex flex-col">
                          <button
                            className="hover:bg-gray-200 rounded p-0.5"
                            onClick={() => moveItem(ci, ii, -1)}
                            disabled={ii === 0}
                            data-testid={`item-up-${item.path}`}
                          >
                            <ChevronUp className="w-4 h-4" />
                          </button>
                          <button
                            className="hover:bg-gray-200 rounded p-0.5"
                            onClick={() => moveItem(ci, ii, 1)}
                            disabled={ii === cat.items.length - 1}
                            data-testid={`item-down-${item.path}`}
                          >
                            <ChevronDown className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                      <td className="px-4 py-3 align-top">
                        <div className="font-medium text-gray-800">{item.label}</div>
                        <div className="text-xs text-gray-400 font-mono">{item.path}</div>
                      </td>
                      <td className="px-4 py-3 align-top">
                        <select
                          className="text-xs border rounded px-2 py-1 bg-white w-full"
                          value={cat.id}
                          onChange={(e) => moveItemBetweenCats(ci, ii, e.target.value)}
                          data-testid={`item-cat-${item.path}`}
                        >
                          {categoryOptions.map(opt => (
                            <option key={opt.id} value={opt.id}>{opt.label}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-4 py-3 align-top">
                        <div className="flex items-center gap-2 mb-1">
                          {item.visible_roles === null ? (
                            <span className="text-xs text-gray-400 italic">using code defaults</span>
                          ) : (
                            <button
                              className="text-xs text-blue-600 hover:underline"
                              onClick={() => clearItemRoleOverride(ci, ii)}
                            >
                              Clear override
                            </button>
                          )}
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-x-3 gap-y-1">
                          {ROLE_OPTIONS.map(r => (
                            <label key={r.key} className="flex items-center gap-1.5 text-xs">
                              <Checkbox
                                checked={(item.visible_roles || []).includes(r.key) || r.locked}
                                disabled={r.locked}
                                onCheckedChange={(checked) => toggleItemRole(ci, ii, r.key, !!checked)}
                                data-testid={`item-role-${item.path}-${r.key}`}
                              />
                              <span className={r.locked ? "text-gray-400" : "text-gray-700"}>{r.label}</span>
                            </label>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {cat.items.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-4 py-6 text-center text-sm text-gray-400 italic">
                        No items in this category
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-amber-200 bg-amber-50/40">
        <CardContent className="p-4 text-xs text-amber-900 space-y-1">
          <p className="font-semibold">How role overrides work</p>
          <p>• Leave all role checkboxes <strong>untouched</strong> (italic "using code defaults") to keep the existing visibility logic from the codebase.</p>
          <p>• Once you tick any role, the item is shown <strong>only</strong> to roles you tick (Super Admin always included).</p>
          <p>• Tick zero roles after enabling override → item is hidden from everyone except Super Admin.</p>
          <p>• Click <strong>Clear override</strong> to revert a single row to code defaults without resetting everything.</p>
        </CardContent>
      </Card>
    </div>
  );
}
