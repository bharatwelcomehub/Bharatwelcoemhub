/**
 * Customer Party Invitation Creator — second tab inside Center Manager Ad Creator.
 * Lets a center manager generate a branded invitation card on demand for
 * customer celebrations (Wedding, Birthday, Get-together, etc.).
 */
import React, { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { useAuth } from "@/App";
import { Loader2, Upload, PartyPopper, Download, Share2, RefreshCw } from "lucide-react";
import { toast } from "sonner";

const API = process.env.REACT_APP_BACKEND_URL;

const OCCASIONS = [
  "Wedding", "Engagement", "Anniversary",
  "Birthday", "Baby Shower / Godbharai",
  "Get-together", "Corporate Event",
  "Festival Celebration", "Other",
];
const LANGUAGES = ["Bilingual", "Marathi", "English"];
const FORMATS = [
  { value: "4:5",  label: "Poster (4:5)" },
  { value: "1:1",  label: "Square (1:1)" },
  { value: "9:16", label: "Story (9:16)" },
];

export default function InvitationCreator() {
  const { session } = useAuth();
  const token = session?.token;
  const [centers, setCenters] = useState([]);
  const [form, setForm] = useState({
    center: session?.center || "",
    host_name: "",
    occasion: "Wedding",
    occasion_other: "",
    event_date: "",
    event_time: "",
    center_address: "",
    menu_highlights: "",
    custom_message: "",
    language: "Bilingual",
    output_format: "4:5",
    photo_base64: "",
  });
  const [photoPreview, setPhotoPreview] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/sales/centers-list`).then(r => r.ok && r.json()).then(d => {
      if (d?.centers) setCenters(d.centers);
    });
  }, []);

  // Auto-fill address when center changes
  useEffect(() => {
    if (!form.center) return;
    const c = centers.find(x => x.code === form.center);
    if (c) setForm(f => ({ ...f, center_address: f.center_address || c.address || c.city || "" }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.center, centers]);

  const onPhoto = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) { toast.error("Photo too large (max 8 MB)"); return; }
    const reader = new FileReader();
    reader.onload = () => { setForm(f => ({ ...f, photo_base64: reader.result })); setPhotoPreview(reader.result); };
    reader.readAsDataURL(file);
  };

  const generate = async () => {
    if (!form.host_name.trim())  { toast.error("Host name is required"); return; }
    if (!form.event_date)        { toast.error("Event date is required"); return; }
    if (!form.event_time.trim()) { toast.error("Event time is required"); return; }
    if (!form.center)            { toast.error("Center is required"); return; }
    setGenerating(true);
    setResult(null);
    toast.info("Generating invitation card — 15-30 seconds");
    try {
      const res = await fetch(`${API}/api/marketing/ads/invitation/generate`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, ...form }),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.detail || "Generation failed");
      }
      setResult(await res.json());
      toast.success("Invitation ready!");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setGenerating(false);
    }
  };

  const downloadAsset = async () => {
    if (!result) return;
    try {
      const res = await fetch(`${API}/api/marketing/ads/asset`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, ad_id: result.ad_id }),
      });
      if (!res.ok) throw new Error("Asset fetch failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Invitation_${form.host_name.replace(/\W+/g, "_")}_${form.event_date}.png`;
      a.click();
      URL.revokeObjectURL(url);
      await fetch(`${API}/api/marketing/ads/track-download`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, ad_id: result.ad_id }),
      });
      toast.success("Downloaded");
    } catch (e) { toast.error(e.message); }
  };

  const shareWa = () => {
    if (!result) return;
    const occ = form.occasion === "Other" ? form.occasion_other : form.occasion;
    const text = encodeURIComponent(
      `🎉 *${occ}*\n\nHost: ${form.host_name}\n📅 ${form.event_date} · ${form.event_time}\n📍 ${form.center_address || ""}\n\nDownload card and share!\n— Purnabramha`
    );
    window.open(`https://wa.me/?text=${text}`, "_blank");
  };

  const reset = () => {
    setForm(f => ({
      ...f,
      host_name: "", occasion: "Wedding", occasion_other: "",
      event_date: "", event_time: "", menu_highlights: "",
      custom_message: "", photo_base64: "",
    }));
    setPhotoPreview(null);
    setResult(null);
  };

  return (
    <div className="space-y-4" data-testid="invitation-creator">
      <div className="grid lg:grid-cols-5 gap-4">
        {/* Form */}
        <Card className="lg:col-span-2" data-testid="invitation-form">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <PartyPopper className="w-4 h-4 text-amber-600" /> Customer Invitation
            </CardTitle>
            <CardDescription>
              Generate a branded invitation card for a customer's celebration at Purnabramha.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Optional host photo */}
            <div>
              <Label className="text-xs">
                Host Photo <span className="text-muted-foreground font-normal">(optional)</span>
              </Label>
              <div className="flex items-center gap-3 mt-1">
                {photoPreview ? (
                  <img src={photoPreview} alt="host" className="w-20 h-20 rounded-full object-cover border-2 border-amber-300" />
                ) : (
                  <div className="w-20 h-20 rounded-full border-2 border-dashed flex items-center justify-center text-muted-foreground text-[10px] text-center px-1">
                    No photo
                  </div>
                )}
                <div className="flex flex-col gap-1">
                  <label className="cursor-pointer">
                    <input type="file" accept="image/*" className="hidden" onChange={onPhoto} data-testid="invite-photo-input" />
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border bg-white hover:bg-amber-50 text-sm">
                      <Upload className="w-3.5 h-3.5" /> {photoPreview ? "Change" : "Upload"}
                    </span>
                  </label>
                  {photoPreview && (
                    <button className="text-[10px] text-rose-700 underline self-start"
                      onClick={() => { setPhotoPreview(null); setForm(f => ({ ...f, photo_base64: "" })); }}>
                      Remove
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div>
              <Label className="text-xs">Host Name *</Label>
              <Input value={form.host_name}
                onChange={e => setForm(f => ({ ...f, host_name: e.target.value }))}
                placeholder="e.g. Shri Mahesh & Sau. Pooja Kulkarni"
                data-testid="invite-host-name" />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs">Occasion *</Label>
                <Select value={form.occasion} onValueChange={v => setForm(f => ({ ...f, occasion: v }))}>
                  <SelectTrigger data-testid="invite-occasion"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {OCCASIONS.map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              {form.occasion === "Other" && (
                <div>
                  <Label className="text-xs">Specify</Label>
                  <Input value={form.occasion_other}
                    onChange={e => setForm(f => ({ ...f, occasion_other: e.target.value }))}
                    placeholder="e.g. Housewarming" />
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs">Date *</Label>
                <Input type="date" value={form.event_date}
                  onChange={e => setForm(f => ({ ...f, event_date: e.target.value }))}
                  data-testid="invite-date" />
              </div>
              <div>
                <Label className="text-xs">Time *</Label>
                <Input value={form.event_time}
                  onChange={e => setForm(f => ({ ...f, event_time: e.target.value }))}
                  placeholder="7:30 PM"
                  data-testid="invite-time" />
              </div>
            </div>

            <div>
              <Label className="text-xs">Center *</Label>
              <Select value={form.center} onValueChange={v => setForm(f => ({ ...f, center: v }))}>
                <SelectTrigger data-testid="invite-center"><SelectValue placeholder="Pick center..." /></SelectTrigger>
                <SelectContent>
                  {centers.map(c => <SelectItem key={c.code} value={c.code}>{c.code} — {c.name || c.city}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="text-xs">Center Address <span className="text-muted-foreground font-normal">(auto-filled, editable)</span></Label>
              <Textarea rows={2} value={form.center_address}
                onChange={e => setForm(f => ({ ...f, center_address: e.target.value }))}
                placeholder="Auto-filled from center master" />
            </div>

            <div>
              <Label className="text-xs">Menu Highlights <span className="text-muted-foreground font-normal">(optional)</span></Label>
              <Input value={form.menu_highlights}
                onChange={e => setForm(f => ({ ...f, menu_highlights: e.target.value }))}
                placeholder="e.g. Misal Pav, Puran Poli, Modak" />
            </div>

            <div>
              <Label className="text-xs">Host Note <span className="text-muted-foreground font-normal">(optional, appears verbatim)</span></Label>
              <Textarea rows={2} value={form.custom_message}
                onChange={e => setForm(f => ({ ...f, custom_message: e.target.value }))}
                placeholder="e.g. With love and gratitude, please join us..." />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs">Language</Label>
                <Select value={form.language} onValueChange={v => setForm(f => ({ ...f, language: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {LANGUAGES.map(l => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Format</Label>
                <Select value={form.output_format} onValueChange={v => setForm(f => ({ ...f, output_format: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {FORMATS.map(f => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <Button onClick={generate} disabled={generating} className="flex-1" data-testid="invite-generate-btn">
                {generating ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Generating</> : <><PartyPopper className="w-4 h-4 mr-2" />Generate Invitation</>}
              </Button>
              <Button variant="outline" onClick={reset} disabled={generating}>
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Preview */}
        <Card className="lg:col-span-3" data-testid="invitation-preview">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Preview</CardTitle>
            <CardDescription>
              {result ? "Invitation ready — download or share directly." : "Fill the form on the left and click Generate."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {generating ? (
              <div className="flex flex-col items-center justify-center py-16">
                <Loader2 className="w-10 h-10 animate-spin text-amber-600 mb-3" />
                <div className="text-sm text-muted-foreground">Composing invitation with brand logo + host details...</div>
              </div>
            ) : result ? (
              <div className="space-y-3">
                <img src={`data:${result.mime_type};base64,${result.image_base64}`}
                  alt="invitation"
                  className="w-full rounded-lg border shadow-sm"
                  data-testid="invitation-image" />
                <div className="flex gap-2 justify-between items-center flex-wrap">
                  <Badge variant="outline">{result.size_kb} KB · {result.mime_type}</Badge>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={downloadAsset} data-testid="invite-download-btn">
                      <Download className="w-4 h-4 mr-1" /> Download PNG
                    </Button>
                    <Button size="sm" variant="outline" onClick={shareWa} data-testid="invite-share-btn">
                      <Share2 className="w-4 h-4 mr-1" /> Share on WhatsApp
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">
                No invitation yet. Click Generate to create one.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
