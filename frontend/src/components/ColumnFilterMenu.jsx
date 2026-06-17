import React, { useMemo, useState } from "react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  ArrowUpAZ, ArrowDownZA, ArrowUp01, ArrowDown10,
  CalendarArrowDown, CalendarArrowUp, Filter, X,
} from "lucide-react";

/**
 * Excel-style column filter dropdown.
 *
 * Props:
 *   rows: full unfiltered data
 *   accessor: (row) => raw value to filter on
 *   formatLabel: (raw) => display string for the checkbox list (optional)
 *   variant: 'text' | 'date' | 'amount'
 *   filter: { selected: Set<string> | null, fromDate, toDate, minAmount, maxAmount }
 *   onApply: (newFilter) => void
 *   onClear: () => void
 *   onSort: (direction: 'asc' | 'desc') => void
 *   currentSort: 'asc' | 'desc' | null
 *   align: 'start' | 'end'
 *   testIdBase: prefix for data-testid
 */
export default function ColumnFilterMenu({
  rows,
  accessor,
  formatLabel = (v) => (v === null || v === undefined || v === "" ? "(Blanks)" : String(v)),
  variant = "text",
  filter,
  onApply,
  onClear,
  onSort,
  currentSort = null,
  align = "start",
  testIdBase = "col-filter",
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState(() => filter);

  // Reset draft to current filter when opening
  React.useEffect(() => {
    if (open) {
      setDraft(filter);
      setSearch("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Compute unique values from rows
  const uniques = useMemo(() => {
    const map = new Map();
    rows.forEach((r) => {
      const raw = accessor(r);
      const key = raw === null || raw === undefined || raw === "" ? "" : String(raw);
      const label = formatLabel(raw);
      map.set(key, label);
    });
    return Array.from(map.entries())
      .map(([key, label]) => ({ key, label }))
      .sort((a, b) => a.label.localeCompare(b.label));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows]);

  const visibleUniques = useMemo(() => {
    if (!search) return uniques;
    const q = search.toLowerCase();
    return uniques.filter((u) => u.label.toLowerCase().includes(q));
  }, [uniques, search]);

  const isActive =
    (filter?.selected && filter.selected instanceof Set && filter.selected.size > 0) ||
    !!(filter?.fromDate) || !!(filter?.toDate) ||
    filter?.minAmount !== "" && filter?.minAmount !== undefined && filter?.minAmount !== null ||
    filter?.maxAmount !== "" && filter?.maxAmount !== undefined && filter?.maxAmount !== null;

  const setSelectedKey = (key, on) => {
    setDraft((d) => {
      // If selected is null (no filter), initialise from full uniques list so
      // toggling individual items is intuitive (Excel behaviour: opening the
      // menu shows everything checked).
      const sel = new Set(d?.selected || uniques.map((u) => u.key));
      if (on) sel.add(key);
      else sel.delete(key);
      return { ...d, selected: sel };
    });
  };

  // Excel-style "Select all" — TOGGLES every value. If everything currently
  // checked, one click clears all; otherwise it selects all (visible) values.
  // Lets the user clear-then-pick-one instead of unchecking 14 items.
  const selectAll = () => {
    setDraft((d) => {
      const cur = d?.selected;
      const allKeys = new Set(visibleUniques.map((u) => u.key));
      const isAllSelected =
        !cur || cur.size === 0
          ? true                                   // null/empty draft => rendered as "all checked"
          : visibleUniques.every((u) => cur.has(u.key));
      if (isAllSelected) {
        // Toggle OFF — start with empty Set (rendered as "all unchecked").
        return { ...d, selected: new Set() };
      }
      // Toggle ON — select every visible value.
      return { ...d, selected: allKeys };
    });
  };
  const clearSelected = () => {
    setDraft((d) => ({ ...d, selected: new Set() }));
  };

  const apply = () => {
    onApply(draft);
    setOpen(false);
  };
  const clearAll = () => {
    onClear();
    setOpen(false);
  };

  const sortBtn = (dir, IconAsc, IconDesc, asc, desc) => (
    <div className="flex gap-1 mb-2">
      <Button
        size="sm" variant={currentSort === "asc" ? "default" : "outline"}
        className="flex-1 h-8 text-xs"
        onClick={() => { onSort("asc"); setOpen(false); }}
        data-testid={`${testIdBase}-sort-asc`}
      >
        <IconAsc className="w-3.5 h-3.5 mr-1" /> {asc}
      </Button>
      <Button
        size="sm" variant={currentSort === "desc" ? "default" : "outline"}
        className="flex-1 h-8 text-xs"
        onClick={() => { onSort("desc"); setOpen(false); }}
        data-testid={`${testIdBase}-sort-desc`}
      >
        <IconDesc className="w-3.5 h-3.5 mr-1" /> {desc}
      </Button>
    </div>
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label="Filter and sort column"
          onClick={(e) => e.stopPropagation()}
          className={`ml-1 inline-flex items-center justify-center w-5 h-5 rounded hover:bg-muted ${isActive ? "text-primary" : "text-muted-foreground/60 hover:text-foreground"}`}
          data-testid={`${testIdBase}-trigger`}
        >
          <Filter className={`w-3.5 h-3.5 ${isActive ? "fill-current" : ""}`} />
        </button>
      </PopoverTrigger>
      <PopoverContent
        align={align}
        side="bottom"
        className="w-72 p-3 z-50"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Sort row */}
        {variant === "date" && sortBtn(null, CalendarArrowUp, CalendarArrowDown, "Oldest→Newest", "Newest→Oldest")}
        {variant === "amount" && sortBtn(null, ArrowUp01, ArrowDown10, "Low→High", "High→Low")}
        {variant === "text" && sortBtn(null, ArrowUpAZ, ArrowDownZA, "A → Z", "Z → A")}

        {/* Date range (date variant only) */}
        {variant === "date" && (
          <div className="mb-2 grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-muted-foreground">From</label>
              <Input
                type="date"
                value={draft?.fromDate || ""}
                onChange={(e) => setDraft((d) => ({ ...d, fromDate: e.target.value }))}
                className="h-8 text-xs"
                data-testid={`${testIdBase}-from-date`}
              />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground">To</label>
              <Input
                type="date"
                value={draft?.toDate || ""}
                onChange={(e) => setDraft((d) => ({ ...d, toDate: e.target.value }))}
                className="h-8 text-xs"
                data-testid={`${testIdBase}-to-date`}
              />
            </div>
          </div>
        )}

        {/* Amount range (amount variant only) */}
        {variant === "amount" && (
          <div className="mb-2 grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-muted-foreground">Min</label>
              <Input
                type="number"
                value={draft?.minAmount ?? ""}
                onChange={(e) => setDraft((d) => ({ ...d, minAmount: e.target.value }))}
                className="h-8 text-xs"
                placeholder="0"
                data-testid={`${testIdBase}-min-amt`}
              />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground">Max</label>
              <Input
                type="number"
                value={draft?.maxAmount ?? ""}
                onChange={(e) => setDraft((d) => ({ ...d, maxAmount: e.target.value }))}
                className="h-8 text-xs"
                placeholder="∞"
                data-testid={`${testIdBase}-max-amt`}
              />
            </div>
          </div>
        )}

        {/* Search box */}
        <div className="mb-2 relative">
          <Input
            placeholder="Search values…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 text-xs pr-6"
            data-testid={`${testIdBase}-search`}
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch("")}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* Master "Select all" checkbox — Excel-style tri-state toggle.
            • All visible checked        → click → all uncheck
            • All visible unchecked      → click → all check
            • Some checked (indeterminate) → click → all check       */}
        <div className="flex items-center justify-between text-[11px] mb-1 px-1.5 py-1 bg-muted/40 rounded">
          <label className="flex items-center gap-2 cursor-pointer select-none flex-1">
            {(() => {
              const cur = draft?.selected;
              // Default state (null) = all checked
              const isAllChecked = !cur
                ? true
                : visibleUniques.length > 0 && visibleUniques.every((u) => cur.has(u.key));
              const isNoneChecked = cur && cur.size === 0;
              return (
                <Checkbox
                  checked={isAllChecked ? true : (isNoneChecked ? false : "indeterminate")}
                  onCheckedChange={selectAll}
                  data-testid={`${testIdBase}-select-all-checkbox`}
                />
              );
            })()}
            <span className="font-medium" onClick={(e) => { e.preventDefault(); selectAll(); }} data-testid={`${testIdBase}-select-all`}>
              (Select all){search ? " (filtered results)" : ""}
            </span>
          </label>
          <button type="button" onClick={clearSelected} className="text-muted-foreground hover:underline ml-2" data-testid={`${testIdBase}-clear-selected`}>
            Clear
          </button>
        </div>

        {/* Multi-select list */}
        <div className="max-h-40 overflow-y-auto border rounded p-1 mb-2 space-y-0.5" data-testid={`${testIdBase}-list`}>
          {visibleUniques.length === 0 && (
            <div className="text-[11px] text-muted-foreground text-center py-2">No values</div>
          )}
          {visibleUniques.map((u) => {
            const cur = draft?.selected;
            // null  → no filter applied yet → render as "all checked" (Excel default)
            // Set() → explicitly cleared    → render as unchecked
            // Set(items) → render based on membership
            const isChecked = !cur ? true : cur.has(u.key);
            return (
              <label key={u.key || "_blank_"} className="flex items-center gap-2 text-xs cursor-pointer hover:bg-muted px-1.5 py-1 rounded group">
                <Checkbox
                  checked={isChecked}
                  onCheckedChange={(v) => {
                    if (!draft?.selected) {
                      // First click on a "no filter" state -> initialise from full list,
                      // then apply the user's choice for THIS row.
                      const all = new Set(uniques.map((x) => x.key));
                      if (!v) all.delete(u.key);
                      setDraft((d) => ({ ...d, selected: all }));
                    } else {
                      setSelectedKey(u.key, !!v);
                    }
                  }}
                />
                <span className="truncate flex-1" title={u.label}>{u.label}</span>
                {/* "Only" shortcut — Excel power-user trick to keep just this one */}
                <button
                  type="button"
                  className="opacity-0 group-hover:opacity-100 text-[10px] text-primary hover:underline transition-opacity"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setDraft((d) => ({ ...d, selected: new Set([u.key]) }));
                  }}
                  data-testid={`${testIdBase}-only-${u.key || "_blank_"}`}
                >
                  Only
                </button>
              </label>
            );
          })}
        </div>

        {/* Actions */}
        <div className="flex gap-1.5">
          <Button size="sm" variant="outline" className="flex-1 h-8 text-xs" onClick={clearAll} data-testid={`${testIdBase}-clear-filter`}>
            Clear filter
          </Button>
          <Button size="sm" className="flex-1 h-8 text-xs" onClick={apply} data-testid={`${testIdBase}-apply`}>
            Apply
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
