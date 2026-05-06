import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Calendar, Save, Image as ImageIcon, Copy, Plus, Trash2, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/App";
import html2canvas from "html2canvas";

const API = process.env.REACT_APP_BACKEND_URL;
const STATUS_OPTIONS = [
  { value: "PRESENT", label: "Present (uses In Time)", color: "bg-emerald-100 text-emerald-800" },
  { value: "LEAVE", label: "Leave", color: "bg-blue-100 text-blue-800" },
  { value: "W", label: "Weekly Off (W)", color: "bg-slate-200 text-slate-700" },
  { value: "A", label: "Absent (A)", color: "bg-red-100 text-red-700" },
];
const GROUP_ORDER = ["Manager", "Service", "Kitchen", "Housekeeping", "Others"];

const fmtDDMMYY = (iso) => {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y.slice(2)}`;
};

const displayCell = (row, key) => {
  const status = (row.status || "").toUpperCase();
  if (status === "LEAVE") return "LEAVE";
  if (status === "W") return "W";
  if (status === "A") return "A";
  return row[key] || "—";
};

export default function DutyRoster() {
  const { session } = useAuth();
  const [centers, setCenters] = useState([]);
  const [center, setCenter] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [rows, setRows] = useState([]);
  const [savedAt, setSavedAt] = useState(null);
  const [savedBy, setSavedBy] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const previewRef = useRef(null);

  const isStaff = session?.is_super_admin || session?.is_admin || session?.roles?.accounting;

  // --- load center list (admin/SA gets all; manager gets locked to own)
  useEffect(() => {
    if (!session?.token) return;
    if (!isStaff && session.center) {
      setCenters([{ code: session.center }]);
      setCenter(session.center);
      return;
    }
    fetch(`${API}/api/mgt/centers`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: session.token }),
    }).then(r => r.json()).then(d => {
      const list = (d.centers || []).filter(c => c.code).sort((a, b) => a.code.localeCompare(b.code));
      setCenters(list);
      if (!center && list.length) setCenter(session.center || list[0].code);
    }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.token]);

  // --- load roster on center/date change
  const loadRoster = useCallback(async () => {
    if (!center || !date) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/duty-roster/get`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: session.token, center, date }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || "Failed to load roster");
      setRows(d.rows || []);
      setSavedAt(d.updated_at || null);
      setSavedBy(d.updated_by || "");
    } catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  }, [center, date, session?.token]);

  useEffect(() => { loadRoster(); }, [loadRoster]);

  const grouped = useMemo(() => {
    const out = {};
    GROUP_ORDER.forEach(g => { out[g] = []; });
    rows.forEach(r => {
      const g = r.group && out[r.group] ? r.group : "Others";
      out[g].push(r);
    });
    return out;
  }, [rows]);

  const updateRow = (idxAbs, patch) => {
    setRows(prev => prev.map((r, i) => (i === idxAbs ? { ...r, ...patch } : r)));
  };
  const addAdHoc = (group) => {
    setRows(prev => [...prev, {
      employee_id: "", name: "", designation: "", group,
      duty_time: "", in_time: "", status: "PRESENT", ad_hoc: true,
    }]);
  };
  const removeRow = (idxAbs) => setRows(prev => prev.filter((_, i) => i !== idxAbs));

  const saveRoster = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/duty-roster/save`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: session.token, center, date, rows }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || "Save failed");
      setSavedAt(d.updated_at);
      setSavedBy(d.updated_by);
      toast.success(`Roster saved (${d.saved} rows)`);
    } catch (e) { toast.error(e.message); }
    finally { setSaving(false); }
  };

  // --- WhatsApp text export (matches the printed roster line-for-line)
  const buildText = () => {
    const lines = [];
    lines.push("*PURNABRAMHA*");
    lines.push(`*${fmtDDMMYY(date)}* — ${center}`);
    lines.push("");
    GROUP_ORDER.forEach(g => {
      const items = grouped[g] || [];
      if (items.length === 0) return;
      lines.push(`*${g.toUpperCase()}*`);
      items.forEach((r, i) => {
        const dt = displayCell(r, "duty_time");
        const it = displayCell(r, "in_time");
        lines.push(`${i + 1}. ${r.name}  (${r.designation})  Duty: ${dt}  In: ${it}`);
      });
      lines.push("");
    });
    return lines.join("\n").trimEnd();
  };

  const copyText = async () => {
    try {
      await navigator.clipboard.writeText(buildText());
      toast.success("Roster text copied — paste in WhatsApp group");
    } catch { toast.error("Clipboard blocked"); }
  };

  // --- PNG export via html2canvas of the styled preview
  const downloadImage = async () => {
    if (!previewRef.current) return;
    try {
      const canvas = await html2canvas(previewRef.current, { scale: 2, backgroundColor: "#ffffff", useCORS: true });
      canvas.toBlob(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `Roster_${center}_${date}.png`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success("Image saved — share to WhatsApp from your gallery");
      }, "image/png");
    } catch (e) { toast.error("Image export failed"); }
  };

  const copyImageToClipboard = async () => {
    if (!previewRef.current) return;
    try {
      const canvas = await html2canvas(previewRef.current, { scale: 2, backgroundColor: "#ffffff", useCORS: true });
      canvas.toBlob(async (blob) => {
        try {
          await navigator.clipboard.write([new window.ClipboardItem({ "image/png": blob })]);
          toast.success("Image copied — paste directly into WhatsApp");
        } catch {
          toast.error("Direct image copy not supported in this browser — use Download instead");
        }
      }, "image/png");
    } catch { toast.error("Image copy failed"); }
  };

  const headerCell = "px-3 py-2 text-left text-[12px] font-bold uppercase tracking-wide";
  const bodyCell = "px-3 py-1.5 text-[13px] border-r border-slate-300 last:border-r-0";

  return (
    <div className="space-y-6" data-testid="duty-roster-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Daily Duty Roster</h1>
          <p className="text-xs text-slate-500 mt-0.5">Mark every staff member's duty time, in time and status. Share to your center WhatsApp group with one click.</p>
        </div>
        <Badge variant="outline" className="text-xs" data-testid="dr-saved-status">
          {savedAt ? `Last saved ${new Date(savedAt).toLocaleString()} by ${savedBy}` : "Not saved yet"}
        </Badge>
      </div>

      {/* Controls */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Center</Label>
              <Select value={center} onValueChange={setCenter} disabled={!isStaff && centers.length <= 1}>
                <SelectTrigger className="w-[160px]" data-testid="dr-center"><SelectValue /></SelectTrigger>
                <SelectContent>{centers.map(c => <SelectItem key={c.code} value={c.code}>{c.code}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Date</Label>
              <Input type="date" value={date} onChange={e => setDate(e.target.value)} className="w-[160px]" data-testid="dr-date" />
            </div>
            <Button variant="outline" onClick={loadRoster} disabled={loading} data-testid="dr-reload">
              <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} /> Reload
            </Button>
            <Button onClick={saveRoster} disabled={saving} className="bg-amber-700 hover:bg-amber-800 text-white" data-testid="dr-save">
              <Save className="w-4 h-4 mr-1" /> {saving ? "Saving…" : "Save Roster"}
            </Button>
            <div className="flex-1" />
            <Button variant="outline" onClick={copyText} data-testid="dr-copy-text">
              <Copy className="w-4 h-4 mr-1" /> Copy Text
            </Button>
            <Button variant="outline" onClick={copyImageToClipboard} data-testid="dr-copy-image">
              <ImageIcon className="w-4 h-4 mr-1" /> Copy Image
            </Button>
            <Button onClick={downloadImage} className="bg-emerald-700 hover:bg-emerald-800 text-white" data-testid="dr-download-image">
              <ImageIcon className="w-4 h-4 mr-1" /> Download PNG
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Editable table */}
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Edit Roster</CardTitle></CardHeader>
        <CardContent>
          {GROUP_ORDER.map(g => {
            const items = grouped[g] || [];
            if (items.length === 0 && g === "Others") return null;
            return (
              <div key={g} className="mb-5">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wide">{g}</h3>
                  <Button size="sm" variant="ghost" onClick={() => addAdHoc(g)} data-testid={`dr-add-${g}`}>
                    <Plus className="w-3.5 h-3.5 mr-1" /> Add ad-hoc
                  </Button>
                </div>
                {items.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No staff in this group.</p>
                ) : (
                  <div className="overflow-x-auto rounded-lg border border-slate-200">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50 text-slate-600">
                        <tr>
                          <th className="px-2 py-1.5 text-left w-10">#</th>
                          <th className="px-2 py-1.5 text-left">Name</th>
                          <th className="px-2 py-1.5 text-left">Designation</th>
                          <th className="px-2 py-1.5 text-left w-32">Duty Time</th>
                          <th className="px-2 py-1.5 text-left w-32">In Time</th>
                          <th className="px-2 py-1.5 text-left w-44">Status</th>
                          <th className="px-2 py-1.5 w-10"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {items.map((r, i) => {
                          const idxAbs = rows.indexOf(r);
                          return (
                            <tr key={`${g}-${i}`} className="border-t border-slate-100 hover:bg-slate-50/50">
                              <td className="px-2 py-1 text-xs text-slate-500">{i + 1}</td>
                              <td className="px-2 py-1">
                                {r.ad_hoc ? (
                                  <Input value={r.name} onChange={e => updateRow(idxAbs, { name: e.target.value.toUpperCase() })} className="h-8 text-xs" placeholder="Name" />
                                ) : (
                                  <span className="text-sm font-medium">{r.name}</span>
                                )}
                              </td>
                              <td className="px-2 py-1">
                                {r.ad_hoc ? (
                                  <Input value={r.designation} onChange={e => updateRow(idxAbs, { designation: e.target.value.toUpperCase() })} className="h-8 text-xs" placeholder="Designation" />
                                ) : (
                                  <span className="text-xs text-slate-600">{r.designation}</span>
                                )}
                              </td>
                              <td className="px-2 py-1">
                                <Input value={r.duty_time} onChange={e => updateRow(idxAbs, { duty_time: e.target.value })} placeholder="08:30" className="h-8 text-xs font-mono" data-testid={`dr-row-duty-${idxAbs}`} />
                              </td>
                              <td className="px-2 py-1">
                                <Input value={r.in_time} onChange={e => updateRow(idxAbs, { in_time: e.target.value })} placeholder="08:38" className="h-8 text-xs font-mono" data-testid={`dr-row-in-${idxAbs}`} />
                              </td>
                              <td className="px-2 py-1">
                                <Select value={r.status || "PRESENT"} onValueChange={v => updateRow(idxAbs, { status: v })}>
                                  <SelectTrigger className="h-8 text-xs" data-testid={`dr-row-status-${idxAbs}`}><SelectValue /></SelectTrigger>
                                  <SelectContent>
                                    {STATUS_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                                  </SelectContent>
                                </Select>
                              </td>
                              <td className="px-2 py-1 text-right">
                                {r.ad_hoc && (
                                  <Button size="sm" variant="ghost" onClick={() => removeRow(idxAbs)} className="h-7 w-7 p-0">
                                    <Trash2 className="w-3.5 h-3.5 text-red-600" />
                                  </Button>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* WhatsApp-styled preview (this is what gets exported as PNG) */}
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base flex items-center gap-2"><Calendar className="w-4 h-4" /> Roster Preview (this image gets shared)</CardTitle></CardHeader>
        <CardContent>
          <div ref={previewRef} className="bg-white inline-block min-w-full" style={{ fontFamily: "system-ui, -apple-system, sans-serif" }} data-testid="dr-preview">
            {/* Header */}
            <div className="bg-[#FFEB3B] text-center py-3 border-2 border-black">
              <div className="text-3xl font-extrabold tracking-wide">PURNABRAMHA</div>
              <div className="text-2xl font-bold mt-1">{fmtDDMMYY(date)}</div>
              <div className="text-sm text-slate-700 mt-0.5">{center}</div>
            </div>
            <table className="w-full border-2 border-black border-collapse">
              <thead>
                <tr className="bg-[#1f4e9d] text-white">
                  <th className={headerCell + " border-r border-white w-16"}>SR.NO</th>
                  <th className={headerCell + " border-r border-white"}>NAME</th>
                  <th className={headerCell + " border-r border-white"}>DESIGNATION</th>
                  <th className={headerCell + " border-r border-white w-32"}>DUTY TIME</th>
                  <th className={headerCell + " w-32"}>IN TIME</th>
                </tr>
              </thead>
              <tbody>
                {GROUP_ORDER.flatMap(g => {
                  const items = grouped[g] || [];
                  if (items.length === 0 && g === "Others") return [];
                  const out = [
                    <tr key={`band-${g}`} className="bg-[#1f4e9d] text-white">
                      <td colSpan={5} className="px-3 py-1.5 text-center font-bold uppercase text-[14px] tracking-wide">{g}</td>
                    </tr>,
                  ];
                  items.forEach((r, i) => {
                    const isOff = (r.status || "").toUpperCase() === "W";
                    out.push(
                      <tr key={`${g}-row-${i}`} className={`${isOff ? "bg-slate-100" : ""}`}>
                        <td className={bodyCell + " text-center w-16"}>{i + 1}</td>
                        <td className={bodyCell + " font-semibold uppercase"}>{r.name || "—"}</td>
                        <td className={bodyCell + " uppercase"}>{r.designation || "—"}</td>
                        <td className={bodyCell + " font-mono text-center"}>{displayCell(r, "duty_time")}</td>
                        <td className={bodyCell + " font-mono text-center"}>{displayCell(r, "in_time")}</td>
                      </tr>
                    );
                  });
                  return out;
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
