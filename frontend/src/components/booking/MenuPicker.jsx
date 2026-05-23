/**
 * Hybrid menu picker — pick from menu_master OR add custom items.
 * Rows: [{ name, qty, rate, amount }]
 */
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Plus, Trash2 } from "lucide-react";

export default function MenuPicker({
  title,
  category,           // e.g. "Starters", "Main Course"
  rows,
  onChange,
  master = [],        // menu_master items for this category
  testIdPrefix = "menu",
}) {
  const [pickName, setPickName] = useState("");
  const [pickRate, setPickRate] = useState("");

  const recalc = (next) =>
    next.map((r) => ({ ...r, amount: round2((Number(r.qty) || 0) * (Number(r.rate) || 0)) }));

  const addPicked = () => {
    if (!pickName) return;
    const next = recalc([
      ...rows,
      { name: pickName, qty: 1, rate: Number(pickRate || 0), amount: 0 },
    ]);
    onChange(next);
    setPickName("");
    setPickRate("");
  };

  const addCustom = () => {
    onChange(recalc([...rows, { name: "", qty: 1, rate: 0, amount: 0 }]));
  };

  const update = (idx, field, value) => {
    const next = [...rows];
    next[idx] = { ...next[idx], [field]: value };
    onChange(recalc(next));
  };

  const remove = (idx) => onChange(rows.filter((_, i) => i !== idx));

  return (
    <div className="border rounded p-3 space-y-3" data-testid={`${testIdPrefix}-${category}`}>
      <div className="flex items-center justify-between">
        <div className="font-medium text-sm">{title || category}</div>
        <Button size="sm" variant="ghost" onClick={addCustom} data-testid={`${testIdPrefix}-add-custom`}>
          <Plus className="w-3 h-3 mr-1" /> Add Custom
        </Button>
      </div>

      {/* Master picker */}
      {master.length > 0 && (
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <Select value={pickName} onValueChange={(v) => {
              setPickName(v);
              const m = master.find(x => x.name === v);
              if (m) setPickRate(String(m.default_rate || ""));
            }}>
              <SelectTrigger className="h-8">
                <SelectValue placeholder="Pick from menu master..." />
              </SelectTrigger>
              <SelectContent>
                {master.map((m) => (
                  <SelectItem key={m.name} value={m.name}>{m.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Input className="h-8 w-24" placeholder="Rate" type="number"
            value={pickRate} onChange={(e) => setPickRate(e.target.value)} />
          <Button size="sm" onClick={addPicked} disabled={!pickName} data-testid={`${testIdPrefix}-add-picked`}>
            <Plus className="w-3 h-3" />
          </Button>
        </div>
      )}

      {/* Rows */}
      {rows.length === 0 ? (
        <div className="text-xs text-muted-foreground italic">No items added</div>
      ) : (
        <div className="space-y-1">
          {rows.map((r, idx) => (
            <div key={idx} className="grid grid-cols-12 gap-1 items-center">
              <Input className="h-8 col-span-5" placeholder="Item name"
                value={r.name} onChange={(e) => update(idx, "name", e.target.value)} />
              <Input className="h-8 col-span-2" type="number" placeholder="Qty"
                value={r.qty} onChange={(e) => update(idx, "qty", e.target.value)} />
              <Input className="h-8 col-span-2" type="number" placeholder="Rate"
                value={r.rate} onChange={(e) => update(idx, "rate", e.target.value)} />
              <Input className="h-8 col-span-2 text-right" readOnly value={(r.amount || 0).toFixed(2)} />
              <Button size="icon" variant="ghost" className="h-8 w-8 col-span-1"
                onClick={() => remove(idx)}>
                <Trash2 className="w-3 h-3 text-red-500" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function round2(n) {
  return Math.round((Number(n) || 0) * 100) / 100;
}
