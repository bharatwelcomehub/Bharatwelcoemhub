/**
 * Creative Studio Library (admin/super-admin only)
 *
 * Unified table of every creative produced across all centers + all 4 types:
 *   Memory Box · Ad · Invitation · Video
 *
 * Features:
 *   • Filter by type, center, manager search, date range, status
 *   • Multi-select with checkboxes
 *   • Bulk delete (soft) + restore
 *   • Bulk download → single ZIP grouped by center/type
 *   • Per-row open / download / delete
 */
import { useState, useEffect, useMemo } from 'react';
import { useAuth } from '@/App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import {
  Library, Trash2, Download, RotateCcw, Search, Eye, RefreshCw,
  Film, Wand2, PartyPopper, BookHeart, Loader2, CheckSquare, Square,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const TYPE_ICONS = {
  memory_box: BookHeart,
  ad: Wand2,
  invitation: PartyPopper,
  video: Film,
};

const TYPE_COLORS = {
  memory_box: 'bg-amber-100 text-amber-900 border-amber-300',
  ad: 'bg-rose-100 text-rose-900 border-rose-300',
  invitation: 'bg-violet-100 text-violet-900 border-violet-300',
  video: 'bg-sky-100 text-sky-900 border-sky-300',
};

export default function CreativeLibrary() {
  const { session } = useAuth();
  const isAdmin = session?.is_super_admin || session?.is_admin;

  const [filters, setFilters] = useState({
    types: ['memory_box', 'ad', 'invitation', 'video'],
    center: '',
    manager: '',
    from_date: '',
    to_date: '',
    status: 'active',
    limit: 200,
  });
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(new Set());
  const [counts, setCounts] = useState({});
  const [centers, setCenters] = useState([]);

  // Load centers list once
  useEffect(() => {
    fetch(`${API}/api/centers`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: session.token }),
    })
      .then(r => r.json())
      .then(d => setCenters(d?.centers || d?.items || []))
      .catch(() => {});
  }, [session.token]);

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/creative-library/list`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, ...filters }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Failed to load');
      setRows(d.items || []);
      setCounts(d.counts || {});
      setSelected(new Set());
    } catch (e) { toast.error(e.message); }
    setLoading(false);
  };

  useEffect(() => { if (isAdmin) load(); }, []);  // eslint-disable-line

  const toggleType = (t) => {
    setFilters(f => {
      const has = f.types.includes(t);
      return { ...f, types: has ? f.types.filter(x => x !== t) : [...f.types, t] };
    });
  };

  const toggleRow = (key) => {
    setSelected(s => {
      const n = new Set(s);
      if (n.has(key)) n.delete(key); else n.add(key);
      return n;
    });
  };

  const toggleAll = () => {
    if (selected.size === rows.length) setSelected(new Set());
    else setSelected(new Set(rows.map(r => `${r.type}:${r.id}`)));
  };

  const selectedItems = useMemo(() =>
    [...selected].map(k => {
      const [type, id] = k.split(':');
      return { type, id };
    }), [selected]);

  const bulkDelete = async () => {
    if (!selectedItems.length) return;
    if (!window.confirm(`Soft-delete ${selectedItems.length} creative(s)? Files stay on disk for 30 days and admins can restore.`)) return;
    try {
      const r = await fetch(`${API}/api/creative-library/bulk-delete`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, items: selectedItems }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Bulk delete failed');
      toast.success(`Deleted ${d.deleted} of ${d.total}`);
      load();
    } catch (e) { toast.error(e.message); }
  };

  const bulkRestore = async () => {
    if (!selectedItems.length) return;
    try {
      const r = await fetch(`${API}/api/creative-library/bulk-restore`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, items: selectedItems }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Bulk restore failed');
      toast.success(`Restored ${d.restored} of ${d.total}`);
      load();
    } catch (e) { toast.error(e.message); }
  };

  const bulkDownload = async () => {
    if (!selectedItems.length) return;
    if (selectedItems.length > 100) { toast.error('Max 100 items per ZIP'); return; }
    try {
      const r = await fetch(`${API}/api/creative-library/bulk-download`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, items: selectedItems }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.detail || 'Bulk download failed');
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `creative_library_${new Date().toISOString().slice(0, 10)}.zip`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Downloaded ZIP (${(blob.size / 1024 / 1024).toFixed(1)} MB)`);
    } catch (e) { toast.error(e.message); }
  };

  const openOne = (row) => {
    // Open the per-type viewer / asset
    if (row.type === 'memory_box') {
      window.open(`${API}/api/memory-box/view/${row.id}`, '_blank');
    } else if (row.type === 'video') {
      window.open(`${API}/api/marketing/videos/asset/${row.id}?token=${encodeURIComponent(session.token)}`, '_blank');
    } else {
      // ad / invitation — download asset
      fetch(`${API}/api/marketing/ads/asset`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, ad_id: row.id }),
      })
        .then(r => r.blob())
        .then(blob => {
          const url = URL.createObjectURL(blob);
          window.open(url, '_blank');
          setTimeout(() => URL.revokeObjectURL(url), 60000);
        })
        .catch(() => toast.error('Could not open asset'));
    }
  };

  const deleteOne = async (row) => {
    if (!window.confirm(`Delete this ${row.type_label}?`)) return;
    try {
      const r = await fetch(`${API}/api/creative-library/delete`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, type: row.type, id: row.id }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Delete failed');
      toast.success('Deleted');
      load();
    } catch (e) { toast.error(e.message); }
  };

  const restoreOne = async (row) => {
    try {
      const r = await fetch(`${API}/api/creative-library/restore`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, type: row.type, id: row.id }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Restore failed');
      toast.success('Restored');
      load();
    } catch (e) { toast.error(e.message); }
  };

  if (!isAdmin) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          🔒 The Creative Studio Library is available to Admins and Super-Admins only.
        </CardContent>
      </Card>
    );
  }

  const allSelected = rows.length > 0 && selected.size === rows.length;

  return (
    <div className="space-y-4" data-testid="creative-library">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-[#5C0000] flex items-center gap-2">
            <Library className="w-6 h-6 text-amber-600" /> Creative Studio Library
          </h2>
          <p className="text-sm text-muted-foreground">
            All centers · all creatives · admin oversight, restore &amp; bulk download.
          </p>
        </div>
        <Badge variant="secondary" className="text-xs">
          {Object.entries(counts).map(([t, c]) => `${t}:${c}`).join(' · ') || 'No data'}
        </Badge>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2"><Search className="w-4 h-4" />Filters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {[
              { k: 'memory_box', label: 'Memory Box', Icon: BookHeart },
              { k: 'ad', label: 'Ad', Icon: Wand2 },
              { k: 'invitation', label: 'Invitation', Icon: PartyPopper },
              { k: 'video', label: 'Video', Icon: Film },
            ].map(({ k, label, Icon }) => (
              <Button key={k} size="sm"
                variant={filters.types.includes(k) ? 'default' : 'outline'}
                onClick={() => toggleType(k)}
                className={filters.types.includes(k) ? 'bg-[#8B0000] hover:bg-[#5C0000]' : ''}
                data-testid={`lib-type-${k}`}>
                <Icon className="w-3.5 h-3.5 mr-1" />{label}
              </Button>
            ))}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            <div>
              <Label className="text-xs">Center</Label>
              <Select value={filters.center || 'all'}
                onValueChange={v => setFilters(f => ({ ...f, center: v === 'all' ? '' : v }))}>
                <SelectTrigger className="h-9" data-testid="lib-filter-center">
                  <SelectValue placeholder="All centers" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All centers</SelectItem>
                  {centers.map(c => (
                    <SelectItem key={c.code || c.id} value={(c.code || c.id || '').toUpperCase()}>
                      {c.code || c.id} · {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Manager / Title search</Label>
              <Input value={filters.manager}
                onChange={e => setFilters(f => ({ ...f, manager: e.target.value }))}
                placeholder="e.g. Jayanti, Pranav"
                className="h-9"
                data-testid="lib-filter-manager" />
            </div>
            <div>
              <Label className="text-xs">From</Label>
              <Input type="date" value={filters.from_date}
                onChange={e => setFilters(f => ({ ...f, from_date: e.target.value }))}
                className="h-9" data-testid="lib-filter-from" />
            </div>
            <div>
              <Label className="text-xs">To</Label>
              <Input type="date" value={filters.to_date}
                onChange={e => setFilters(f => ({ ...f, to_date: e.target.value }))}
                className="h-9" data-testid="lib-filter-to" />
            </div>
            <div>
              <Label className="text-xs">Status</Label>
              <Select value={filters.status}
                onValueChange={v => setFilters(f => ({ ...f, status: v }))}>
                <SelectTrigger className="h-9" data-testid="lib-filter-status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="deleted">Deleted (recycle bin)</SelectItem>
                  <SelectItem value="all">All</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 pt-1">
            <Button size="sm" onClick={load} className="bg-[#8B0000] hover:bg-[#5C0000]"
              data-testid="lib-refresh">
              {loading
                ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
                : <RefreshCw className="w-3.5 h-3.5 mr-1" />}
              Apply / Refresh
            </Button>

            {selected.size > 0 && (
              <>
                <Badge className="bg-amber-600 text-white py-1">
                  {selected.size} selected
                </Badge>
                <Button size="sm" variant="outline" onClick={bulkDownload}
                  data-testid="lib-bulk-download">
                  <Download className="w-3.5 h-3.5 mr-1" />Download ZIP
                </Button>
                {filters.status === 'deleted' ? (
                  <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700"
                    onClick={bulkRestore} data-testid="lib-bulk-restore">
                    <RotateCcw className="w-3.5 h-3.5 mr-1" />Restore
                  </Button>
                ) : (
                  <Button size="sm" variant="destructive"
                    onClick={bulkDelete} data-testid="lib-bulk-delete">
                    <Trash2 className="w-3.5 h-3.5 mr-1" />Delete
                  </Button>
                )}
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center justify-between">
            <span>{rows.length} creative(s)</span>
            <Button size="sm" variant="ghost" onClick={toggleAll}
              data-testid="lib-toggle-all">
              {allSelected
                ? <CheckSquare className="w-4 h-4 mr-1" />
                : <Square className="w-4 h-4 mr-1" />}
              {allSelected ? 'Unselect all' : 'Select all'}
            </Button>
          </CardTitle>
          <CardDescription className="text-xs">
            Tip: Deleted items stay recoverable for 30 days, then auto-purge.
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto p-0">
          {rows.length === 0 ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              {loading ? 'Loading…' : 'No creatives match your filters.'}
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-stone-100 text-stone-700">
                <tr>
                  <th className="px-3 py-2 w-8"></th>
                  <th className="px-3 py-2 text-left">Type</th>
                  <th className="px-3 py-2 text-left">Title</th>
                  <th className="px-3 py-2 text-left">Center</th>
                  <th className="px-3 py-2 text-left">Created</th>
                  <th className="px-3 py-2 text-left">By</th>
                  <th className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(r => {
                  const key = `${r.type}:${r.id}`;
                  const Icon = TYPE_ICONS[r.type] || Library;
                  const isDeleted = r.status === 'deleted';
                  return (
                    <tr key={key}
                      className={`border-t border-stone-100 hover:bg-amber-50/50 ${isDeleted ? 'opacity-60 bg-red-50/30' : ''}`}
                      data-testid={`lib-row-${r.id}`}>
                      <td className="px-3 py-2">
                        <input type="checkbox"
                          checked={selected.has(key)}
                          onChange={() => toggleRow(key)}
                          data-testid={`lib-check-${r.id}`}
                          className="cursor-pointer w-4 h-4" />
                      </td>
                      <td className="px-3 py-2">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 border rounded text-[11px] ${TYPE_COLORS[r.type] || ''}`}>
                          <Icon className="w-3 h-3" />{r.type_label}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-medium">
                        {r.title}
                        {r.extra?.occasion && (
                          <div className="text-[11px] text-muted-foreground">{r.extra.occasion}</div>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <span className="text-xs font-mono">{r.center}</span>
                        {r.center_name && (
                          <div className="text-[10px] text-muted-foreground">{r.center_name}</div>
                        )}
                      </td>
                      <td className="px-3 py-2 text-xs whitespace-nowrap">
                        {(r.created_at || '').slice(0, 10)}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        {r.created_by}
                        {isDeleted && r.deleted_by && (
                          <div className="text-[10px] text-red-700">
                            ✕ by {r.deleted_by}
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right">
                        <div className="inline-flex gap-1">
                          <Button size="sm" variant="ghost" onClick={() => openOne(r)}
                            title="Open / preview" data-testid={`lib-open-${r.id}`}>
                            <Eye className="w-4 h-4" />
                          </Button>
                          {isDeleted ? (
                            <Button size="sm" variant="ghost"
                              className="text-emerald-700 hover:bg-emerald-50"
                              onClick={() => restoreOne(r)}
                              title="Restore" data-testid={`lib-restore-${r.id}`}>
                              <RotateCcw className="w-4 h-4" />
                            </Button>
                          ) : (
                            <Button size="sm" variant="ghost"
                              className="text-red-700 hover:bg-red-50"
                              onClick={() => deleteOne(r)}
                              title="Delete" data-testid={`lib-delete-${r.id}`}>
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
