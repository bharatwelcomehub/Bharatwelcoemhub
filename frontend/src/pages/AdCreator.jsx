import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { useAuth } from "@/App";
import { Loader2, Upload, Wand2, Download, Share2, History, Sparkles, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function AdCreator() {
  const { session } = useAuth();
  const [masters, setMasters] = useState({ menu_items: [], centers: [], festivals: [], languages: [], output_formats: [] });
  const [form, setForm] = useState({
    manager_name: session?.managerName || '',
    center: session?.center || '',
    language: 'Bilingual',
    menu_item: '',
    festival_theme: 'Weekend',
    output_format: '1:1',
    photo_base64: '',
  });
  const [photoPreview, setPhotoPreview] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [regenCaption, setRegenCaption] = useState(false);
  const [result, setResult] = useState(null);  // { ad_id, image_base64, caption, mime_type }
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (!session?.token) return;
    fetch(`${API}/api/marketing/ads/masters`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: session.token }),
    }).then(r => r.json()).then(setMasters).catch(() => {});
  }, [session?.token]);

  const loadHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/marketing/ads/history`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: session.token, limit: 24 }),
      });
      if (!res.ok) return;
      const d = await res.json();
      setHistory(d.items || []);
    } catch (e) { /* ignore */ }
  }, [session?.token]);
  useEffect(() => { if (session?.token) loadHistory(); }, [session?.token, loadHistory]);

  const onPhotoSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) { toast.error('Photo too large (max 8 MB)'); return; }
    const reader = new FileReader();
    reader.onload = () => {
      setForm(f => ({ ...f, photo_base64: reader.result }));
      setPhotoPreview(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const generate = async () => {
    if (!form.photo_base64) { toast.error('Upload your photo first'); return; }
    if (!form.manager_name || !form.menu_item) { toast.error('Name and menu item are required'); return; }
    setGenerating(true);
    setResult(null);
    try {
      toast.info('Generating creative — this takes 15-30 seconds');
      const res = await fetch(`${API}/api/marketing/ads/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: session.token, ...form }),
      });
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Generation failed'); }
      const data = await res.json();
      setResult(data);
      toast.success('Creative ready!');
      loadHistory();
    } catch (e) { toast.error(e.message); }
    finally { setGenerating(false); }
  };

  const regenerateCaption = async () => {
    setRegenCaption(true);
    try {
      const res = await fetch(`${API}/api/marketing/ads/caption`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: session.token, ...form }),
      });
      const data = await res.json();
      if (data.caption) {
        setResult(r => r ? { ...r, caption: data.caption } : r);
        setForm(f => ({ ...f, caption_marathi: data.caption.marathi, caption_english: data.caption.english }));
        toast.success('Caption regenerated');
      }
    } catch (e) { toast.error(e.message); }
    finally { setRegenCaption(false); }
  };

  const downloadAsset = async (ad_id, fmt = 'png') => {
    try {
      const res = await fetch(`${API}/api/marketing/ads/asset`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: session.token, ad_id }),
      });
      if (!res.ok) throw new Error('Asset fetch failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `Purnabramha_Ad_${ad_id}.${fmt}`;
      a.click(); URL.revokeObjectURL(url);
      // Track download
      await fetch(`${API}/api/marketing/ads/track-download`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: session.token, ad_id }),
      });
      toast.success(`Downloaded ${fmt.toUpperCase()}`);
    } catch (e) { toast.error(e.message); }
  };

  const shareToWhatsapp = (caption) => {
    const text = encodeURIComponent(`${caption.marathi || ''}\n\n${caption.english || ''}\n\n— Purnabramha`);
    window.open(`https://wa.me/?text=${text}`, '_blank');
  };

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold text-[#5C0000] flex items-center gap-2"><Sparkles className="w-7 h-7 text-amber-600" /> Center Manager Ad Creator</h1>
          <p className="text-muted-foreground mt-1">Create premium Purnabramha-style advertisements in under 2 minutes.</p>
        </div>
        <Badge variant="secondary" className="text-xs">Creative Studio · Marketing</Badge>
      </div>

      <Tabs defaultValue="create" className="w-full">
        <TabsList>
          <TabsTrigger value="create" data-testid="ad-tab-create"><Wand2 className="w-4 h-4 mr-1" />Create</TabsTrigger>
          <TabsTrigger value="history" data-testid="ad-tab-history"><History className="w-4 h-4 mr-1" />Marketing Gallery</TabsTrigger>
        </TabsList>

        <TabsContent value="create" className="space-y-4">
          <div className="grid lg:grid-cols-5 gap-4">
            {/* Form */}
            <Card className="lg:col-span-2" data-testid="ad-creator-form">
              <CardHeader className="pb-3"><CardTitle className="text-base">Your Inputs</CardTitle><CardDescription>Fill these — AI does the rest.</CardDescription></CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <Label className="text-xs">Your Photo</Label>
                  <div className="flex items-center gap-3 mt-1">
                    {photoPreview ? (
                      <img src={photoPreview} alt="manager" className="w-20 h-20 rounded-lg object-cover border-2 border-amber-300" data-testid="ad-photo-preview" />
                    ) : (
                      <div className="w-20 h-20 rounded-lg border-2 border-dashed flex items-center justify-center text-muted-foreground text-xs">No photo</div>
                    )}
                    <label className="cursor-pointer">
                      <input type="file" accept="image/*" className="hidden" onChange={onPhotoSelect} data-testid="ad-photo-input" />
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border bg-white hover:bg-amber-50 text-sm">
                        <Upload className="w-3.5 h-3.5" />{photoPreview ? 'Change' : 'Upload Photo'}
                      </span>
                    </label>
                  </div>
                </div>
                <div>
                  <Label className="text-xs">Full Name</Label>
                  <Input value={form.manager_name} onChange={e => setForm(f => ({ ...f, manager_name: e.target.value }))} placeholder="e.g. Sneha" data-testid="ad-name" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">Center</Label>
                    <Select value={form.center} onValueChange={v => setForm(f => ({ ...f, center: v }))}>
                      <SelectTrigger className="h-9" data-testid="ad-center"><SelectValue placeholder="Select center" /></SelectTrigger>
                      <SelectContent>
                        {masters.centers.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs">Language</Label>
                    <Select value={form.language} onValueChange={v => setForm(f => ({ ...f, language: v }))}>
                      <SelectTrigger className="h-9" data-testid="ad-language"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {(masters.languages || []).map(l => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div>
                  <Label className="text-xs">Menu Item</Label>
                  <Select value={form.menu_item} onValueChange={v => setForm(f => ({ ...f, menu_item: v }))}>
                    <SelectTrigger className="h-9" data-testid="ad-menu"><SelectValue placeholder="Pick a hero dish" /></SelectTrigger>
                    <SelectContent>
                      {masters.menu_items.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">Festival / Theme</Label>
                    <Select value={form.festival_theme} onValueChange={v => setForm(f => ({ ...f, festival_theme: v }))}>
                      <SelectTrigger className="h-9" data-testid="ad-theme"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {masters.festivals.map(f => <SelectItem key={f} value={f}>{f}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs">Format</Label>
                    <Select value={form.output_format} onValueChange={v => setForm(f => ({ ...f, output_format: v }))}>
                      <SelectTrigger className="h-9" data-testid="ad-format"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {(masters.output_formats || []).map(f => <SelectItem key={f.id} value={f.id}>{f.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <Button onClick={generate} disabled={generating} className="w-full bg-[#8B0000] hover:bg-[#5C0000] text-white" size="lg" data-testid="ad-generate-btn">
                  {generating ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Generating…</> : <><Wand2 className="w-4 h-4 mr-2" />Generate Creative</>}
                </Button>
              </CardContent>
            </Card>

            {/* Result */}
            <Card className="lg:col-span-3" data-testid="ad-result">
              <CardHeader className="pb-3"><CardTitle className="text-base">Preview</CardTitle><CardDescription>The face from your photo, your menu, your headline — generated in one shot.</CardDescription></CardHeader>
              <CardContent>
                {generating ? (
                  <div className="aspect-square rounded-lg bg-gradient-to-br from-amber-50 to-rose-50 border-2 border-dashed border-amber-300 flex flex-col items-center justify-center gap-3">
                    <Loader2 className="w-10 h-10 text-amber-700 animate-spin" />
                    <p className="text-sm text-amber-900">Composing your advertisement…</p>
                  </div>
                ) : result ? (
                  <div className="space-y-3">
                    <img src={`data:${result.mime_type};base64,${result.image_base64}`} alt="generated ad" className="w-full rounded-lg shadow-lg" data-testid="ad-generated-image" />
                    <div className="rounded border bg-amber-50/50 p-3 space-y-1">
                      <p className="text-xs font-semibold text-amber-900">Caption (auto-burned into creative)</p>
                      {result.caption?.marathi && <p className="text-sm">{result.caption.marathi}</p>}
                      {result.caption?.english && <p className="text-sm italic text-muted-foreground">{result.caption.english}</p>}
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      <Button size="sm" variant="outline" onClick={regenerateCaption} disabled={regenCaption} data-testid="ad-regen-caption">
                        {regenCaption ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <RefreshCw className="w-3.5 h-3.5 mr-1" />}Regenerate caption
                      </Button>
                      <Button size="sm" className="bg-[#8B0000] hover:bg-[#5C0000] text-white" onClick={() => downloadAsset(result.ad_id, 'png')} data-testid="ad-download-png">
                        <Download className="w-3.5 h-3.5 mr-1" />PNG
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => downloadAsset(result.ad_id, 'jpg')} data-testid="ad-download-jpg">
                        <Download className="w-3.5 h-3.5 mr-1" />JPG
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => shareToWhatsapp(result.caption)} data-testid="ad-share-wa">
                        <Share2 className="w-3.5 h-3.5 mr-1" />WhatsApp
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="aspect-square rounded-lg bg-gradient-to-br from-amber-50 to-rose-50 border-2 border-dashed border-amber-300 flex items-center justify-center text-center p-6">
                    <p className="text-sm text-amber-900 max-w-xs">Fill the form on the left and click <strong>Generate Creative</strong> to see your advertisement here.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card data-testid="ad-gallery">
            <CardHeader className="pb-3"><CardTitle className="text-base">Marketing Gallery</CardTitle><CardDescription>Past creatives by you & your center.</CardDescription></CardHeader>
            <CardContent>
              {history.length === 0 ? (
                <p className="text-sm text-muted-foreground italic">No advertisements created yet.</p>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {history.map(h => (
                    <div key={h.ad_id} className="rounded-lg border overflow-hidden bg-white" data-testid={`ad-history-${h.ad_id}`}>
                      <button type="button" className="w-full block" onClick={() => downloadAsset(h.ad_id, 'png')}>
                        <img src={`${API}/api/marketing/ads/asset?_=${h.ad_id}`} alt="" className="w-full aspect-square object-cover hidden" />
                      </button>
                      <div className="p-3 text-xs space-y-0.5">
                        <p className="font-semibold truncate">{h.menu_item} · {h.festival_theme}</p>
                        <p className="text-muted-foreground">{h.manager_name} · {h.center}</p>
                        <p className="text-muted-foreground">{(h.created_at || '').slice(0, 10)} · {h.download_count} dl</p>
                        <Button size="sm" variant="outline" className="w-full mt-1 h-7 text-xs" onClick={() => downloadAsset(h.ad_id, 'png')}>
                          <Download className="w-3 h-3 mr-1" />Download
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
