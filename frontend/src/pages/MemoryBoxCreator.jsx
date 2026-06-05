import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import {
  Accordion, AccordionItem, AccordionTrigger, AccordionContent,
} from '../components/ui/accordion';
import { useAuth } from '@/App';
import {
  Loader2, BookHeart, Upload, Users, RefreshCcw, Plus, Trash2,
  Download, Send, Mail, MessageSquare, X, History,
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const ROLE_PRESETS = [
  'Center Manager', 'Head Chef', 'Sous Chef', 'Service Captain', 'Service Associate',
  'Hostess', 'Cashier', 'Kitchen Helper', 'Steward', 'Delivery Coordinator',
];

export default function MemoryBoxCreator() {
  const { session } = useAuth();
  const fileInput = useRef(null);

  const [occasions, setOccasions] = useState([]);
  const [emotions, setEmotions] = useState([]);
  const [centers, setCenters] = useState([]);
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);

  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    center: session?.center || '',
    guest_name: '',
    mobile: '',
    email: '',
    event_date: today,
    order_number: '',
    occasion: 'Birthday',
    occasion_other: '',
    celebration_for: '',
    special_moment: '',
    organised_by: '',
    host_message: '',
    thank_family: '',
    mention_guests: '',
    emotion: 'Joy',
    // Per-center branding (Feb 2026)
    instagram_url: '',
    phone: '',
    show_qr: true,
    // Personalisation (Feb 2026)
    language: 'Bilingual',
    font_size: 'M',
  });
  const [photos, setPhotos] = useState([]);          // [{ name, b64 }]
  const [teamPhoto, setTeamPhoto] = useState('');
  const [team, setTeam] = useState([]);              // [{ name, role }]

  const [busyRoster, setBusyRoster] = useState(false);
  const [busyGen, setBusyGen] = useState(false);
  const [busyEmail, setBusyEmail] = useState(false);
  const [result, setResult] = useState(null);

  // ── Load masters + history ────────────────────────────────────────────
  const loadMasters = useCallback(async () => {
    if (!session?.token) return;
    try {
      const res = await fetch(`${API}/api/memory-box/types`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token }),
      });
      if (res.ok) {
        const d = await res.json();
        setOccasions(d.occasions || []);
        setEmotions(d.emotions || []);
      }
      // centers come from marketing masters
      const cres = await fetch(`${API}/api/marketing/ads/masters`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token }),
      });
      if (cres.ok) {
        const cd = await cres.json();
        setCenters(cd.centers || []);
      }
    } catch (e) { /* ignore */ }
  }, [session?.token]);

  const loadHistory = useCallback(async () => {
    if (!session?.token) return;
    try {
      const res = await fetch(`${API}/api/memory-box/list`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, limit: 30 }),
      });
      if (res.ok) { const d = await res.json(); setHistory(d.items || []); }
      const sres = await fetch(`${API}/api/memory-box/stats`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token }),
      });
      if (sres.ok) setStats(await sres.json());
    } catch (e) { /* ignore */ }
  }, [session?.token]);

  useEffect(() => { loadMasters(); loadHistory(); }, [loadMasters, loadHistory]);

  // Auto-fill Instagram + phone from center config when center changes
  useEffect(() => {
    if (!session?.token || !form.center) return;
    fetch(`${API}/api/mgt/center_branding`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: session.token, code: form.center }),
    }).then(r => r.ok && r.json()).then(d => {
      if (!d) return;
      setForm(f => ({
        ...f,
        instagram_url: f.instagram_url || d.instagram_url || '',
        phone: f.phone || d.phone || '',
      }));
    }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.center, session?.token]);

  // ── Prefill from another module (e.g. Catering / Event Bookings) ──────
  useEffect(() => {
    try {
      const raw = localStorage.getItem('mbox_prefill');
      if (!raw) return;
      const p = JSON.parse(raw);
      localStorage.removeItem('mbox_prefill');
      setForm(f => ({
        ...f,
        center: p.center || f.center,
        guest_name: p.guest_name || f.guest_name,
        mobile: p.mobile || f.mobile,
        email: p.email || f.email,
        event_date: p.event_date || f.event_date,
        order_number: p.order_number || f.order_number,
        occasion: p.occasion || f.occasion,
        occasion_other: p.occasion_other || f.occasion_other,
        celebration_for: p.celebration_for || f.celebration_for,
        organised_by: p.organised_by || f.organised_by,
      }));
      if (p.source) {
        toast.success(`Prefilled from ${p.source} — answer the memory questions to make it personal`);
      }
    } catch (e) { /* ignore */ }
  }, []);

  // ── Auto-pull team roster from attendance ─────────────────────────────
  const fetchRoster = async () => {
    if (!form.center || !form.event_date) {
      toast.error('Pick center & event date first'); return;
    }
    setBusyRoster(true);
    try {
      const res = await fetch(`${API}/api/memory-box/team-roster`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, center: form.center, event_date: form.event_date }),
      });
      if (!res.ok) throw new Error('Roster fetch failed');
      const d = await res.json();
      if ((d.team || []).length === 0) {
        toast.info('No team members marked Present for this date. Add manually below.');
      } else {
        toast.success(`Loaded ${d.count} team member${d.count > 1 ? 's' : ''}`);
      }
      setTeam(d.team || []);
    } catch (e) { toast.error(e.message); }
    finally { setBusyRoster(false); }
  };

  // ── Photo handlers ────────────────────────────────────────────────────
  const onPhotosSelect = (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    const remaining = 10 - photos.length;
    if (remaining <= 0) { toast.error('Max 10 photos'); return; }
    const slice = files.slice(0, remaining);
    if (files.length > remaining) toast.info(`Only first ${remaining} added (10 max)`);
    Promise.all(slice.map(f => new Promise((resolve) => {
      if (f.size > 6 * 1024 * 1024) { toast.error(`${f.name} > 6MB — skipped`); resolve(null); return; }
      const r = new FileReader();
      r.onload = () => resolve({ name: f.name, b64: r.result });
      r.readAsDataURL(f);
    }))).then(arr => setPhotos(p => [...p, ...arr.filter(Boolean)]));
    if (fileInput.current) fileInput.current.value = '';
  };

  const onTeamPhotoSelect = (e) => {
    const f = e.target.files?.[0]; if (!f) return;
    if (f.size > 6 * 1024 * 1024) { toast.error('Team photo > 6 MB'); return; }
    const r = new FileReader(); r.onload = () => setTeamPhoto(r.result); r.readAsDataURL(f);
  };

  // ── Generate ──────────────────────────────────────────────────────────
  const generate = async () => {
    if (!form.guest_name.trim() || !form.event_date || !form.occasion || !form.center) {
      toast.error('Guest name, center, event date & occasion are required');
      return;
    }
    setBusyGen(true);
    setResult(null);
    try {
      toast.info('Composing memory book — GPT-5.2 is writing your story (15-30s)…');
      const res = await fetch(`${API}/api/memory-box/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: session.token,
          ...form,
          photos: photos.map(p => p.b64),
          team_photo: teamPhoto,
          team,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Generation failed');
      }
      const d = await res.json();
      setResult(d);
      toast.success('Memory Box ready!');
      loadHistory();
    } catch (e) { toast.error(e.message); }
    finally { setBusyGen(false); }
  };

  // ── Delivery actions ──────────────────────────────────────────────────
  const downloadPdf = async (box_id, guest_name) => {
    try {
      const res = await fetch(`${API}/api/memory-box/asset/${box_id}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token }),
      });
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `MemoryBox_${(guest_name || 'guest').replace(/\s+/g, '_')}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Downloaded PDF');
    } catch (e) { toast.error(e.message); }
  };

  const sendWhatsapp = async (box_id) => {
    try {
      const res = await fetch(`${API}/api/memory-box/whatsapp-preview/${box_id}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token }),
      });
      if (!res.ok) throw new Error('Preview failed');
      const d = await res.json();
      const cleanPhone = (d.phone || '').replace(/\D/g, '');
      const url = `https://wa.me/${cleanPhone}?text=${encodeURIComponent(d.message)}`;
      window.open(url, '_blank');
      // mark sent (best-effort)
      fetch(`${API}/api/memory-box/mark-whatsapp-sent/${box_id}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token }),
      }).then(() => loadHistory());
      toast.success('Opening WhatsApp — please attach the downloaded PDF in the chat.');
    } catch (e) { toast.error(e.message); }
  };

  const sendEmail = async (box_id, to_email) => {
    setBusyEmail(true);
    try {
      const target = to_email || prompt('Send Memory Box PDF to email:', form.email || '');
      if (!target) { setBusyEmail(false); return; }
      const res = await fetch(`${API}/api/memory-box/send-email/${box_id}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, to_email: target }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Email send failed');
      }
      const d = await res.json();
      toast.success(`Emailed to ${d.to}`);
      loadHistory();
    } catch (e) { toast.error(e.message); }
    finally { setBusyEmail(false); }
  };

  const resetForm = () => {
    setForm(f => ({
      ...f, guest_name: '', mobile: '', email: '', order_number: '',
      celebration_for: '', special_moment: '', organised_by: '',
      host_message: '', thank_family: '', mention_guests: '',
    }));
    setPhotos([]); setTeamPhoto(''); setTeam([]); setResult(null);
  };

  // ── Helpers ───────────────────────────────────────────────────────────
  const addTeamMember = () => setTeam(t => [...t, { name: '', role: 'Service Associate' }]);
  const updateTeam = (i, k, v) => setTeam(t => t.map((m, idx) => idx === i ? { ...m, [k]: v } : m));
  const removeTeam = (i) => setTeam(t => t.filter((_, idx) => idx !== i));

  // ── Render ────────────────────────────────────────────────────────────
  return (
    <div className="space-y-4" data-testid="memory-box-creator">
      {/* Stats strip */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <div className="rounded-lg border bg-white p-3" data-testid="mb-stat-created">
            <p className="text-xs text-muted-foreground">Memory Boxes Created</p>
            <p className="text-xl font-bold text-[#5C0000]">{stats.memory_boxes_created}</p>
          </div>
          <div className="rounded-lg border bg-white p-3">
            <p className="text-xs text-muted-foreground">Shared on WhatsApp</p>
            <p className="text-xl font-bold text-emerald-700">{stats.memory_boxes_shared_whatsapp}</p>
          </div>
          <div className="rounded-lg border bg-white p-3">
            <p className="text-xs text-muted-foreground">Sent via Email</p>
            <p className="text-xl font-bold text-sky-700">{stats.memory_boxes_shared_email}</p>
          </div>
          <div className="rounded-lg border bg-white p-3">
            <p className="text-xs text-muted-foreground">PDF Downloads</p>
            <p className="text-xl font-bold text-amber-700">{stats.downloads}</p>
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-5 gap-4">
        {/* ── Form (left) ──────────────────────────────────────────── */}
        <Card className="lg:col-span-3" data-testid="mb-form-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <BookHeart className="w-5 h-5 text-rose-700" />
              Build a Memory Box
            </CardTitle>
            <CardDescription>
              GPT-5.2 will weave the answers below into a heartfelt 7-page PDF — story, gratitude,
              blessing &amp; a future invitation. All sections except <em>Guest &amp; Occasion</em> are optional.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Accordion type="multiple" defaultValue={['guest', 'occasion']} className="w-full">
              {/* Guest */}
              <AccordionItem value="guest">
                <AccordionTrigger data-testid="mb-acc-guest">1. Guest &amp; Center</AccordionTrigger>
                <AccordionContent className="space-y-3 pt-2">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label className="text-xs">Guest Name *</Label>
                      <Input value={form.guest_name} onChange={e => setForm(f => ({ ...f, guest_name: e.target.value }))}
                        placeholder="e.g. Mr. & Mrs. Patil" data-testid="mb-guest-name" />
                    </div>
                    <div>
                      <Label className="text-xs">Center *</Label>
                      <Select value={form.center} onValueChange={v => setForm(f => ({ ...f, center: v }))}>
                        <SelectTrigger className="h-9" data-testid="mb-center"><SelectValue placeholder="Select" /></SelectTrigger>
                        <SelectContent>
                          {centers.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <Label className="text-xs">Mobile</Label>
                      <Input value={form.mobile} onChange={e => setForm(f => ({ ...f, mobile: e.target.value }))}
                        placeholder="91XXXXXXXXXX" data-testid="mb-mobile" />
                    </div>
                    <div>
                      <Label className="text-xs">Email</Label>
                      <Input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                        placeholder="guest@example.com" data-testid="mb-email" />
                    </div>
                    <div>
                      <Label className="text-xs">Order / Booking #</Label>
                      <Input value={form.order_number} onChange={e => setForm(f => ({ ...f, order_number: e.target.value }))}
                        placeholder="optional" data-testid="mb-order" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Event Date *</Label>
                    <Input type="date" value={form.event_date}
                      onChange={e => setForm(f => ({ ...f, event_date: e.target.value }))}
                      data-testid="mb-event-date" />
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Occasion */}
              <AccordionItem value="occasion">
                <AccordionTrigger data-testid="mb-acc-occasion">2. Occasion &amp; Emotion</AccordionTrigger>
                <AccordionContent className="space-y-3 pt-2">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label className="text-xs">Occasion *</Label>
                      <Select value={form.occasion} onValueChange={v => setForm(f => ({ ...f, occasion: v }))}>
                        <SelectTrigger className="h-9" data-testid="mb-occasion"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {occasions.map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-xs">Primary Emotion</Label>
                      <Select value={form.emotion} onValueChange={v => setForm(f => ({ ...f, emotion: v }))}>
                        <SelectTrigger className="h-9" data-testid="mb-emotion"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {emotions.map(e => <SelectItem key={e} value={e}>{e}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  {form.occasion === 'Other' && (
                    <div>
                      <Label className="text-xs">Custom occasion</Label>
                      <Input value={form.occasion_other}
                        onChange={e => setForm(f => ({ ...f, occasion_other: e.target.value }))}
                        placeholder="e.g. Promotion celebration" data-testid="mb-occasion-other" />
                    </div>
                  )}
                </AccordionContent>
              </AccordionItem>

              {/* Memory questions */}
              <AccordionItem value="memory">
                <AccordionTrigger data-testid="mb-acc-memory">3. Memory Questions (helps GPT-5.2 personalise)</AccordionTrigger>
                <AccordionContent className="space-y-3 pt-2">
                  <div>
                    <Label className="text-xs">What were they celebrating?</Label>
                    <Input value={form.celebration_for}
                      onChange={e => setForm(f => ({ ...f, celebration_for: e.target.value }))}
                      placeholder="e.g. Father's 60th Birthday" data-testid="mb-celeb-for" />
                  </div>
                  <div>
                    <Label className="text-xs">Most special moment of the day?</Label>
                    <Textarea rows={2} value={form.special_moment}
                      onChange={e => setForm(f => ({ ...f, special_moment: e.target.value }))}
                      placeholder="e.g. Aaji cut the modak with grandkids around her"
                      data-testid="mb-special-moment" />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label className="text-xs">Who organised it?</Label>
                      <Input value={form.organised_by}
                        onChange={e => setForm(f => ({ ...f, organised_by: e.target.value }))}
                        placeholder="e.g. Daughter Priya" data-testid="mb-organised-by" />
                    </div>
                    <div>
                      <Label className="text-xs">Family/Guests to mention</Label>
                      <Input value={form.mention_guests}
                        onChange={e => setForm(f => ({ ...f, mention_guests: e.target.value }))}
                        placeholder="e.g. The Kulkarni clan" data-testid="mb-mention" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Host's personal message (italic quote on page 2)</Label>
                    <Textarea rows={2} value={form.host_message}
                      onChange={e => setForm(f => ({ ...f, host_message: e.target.value }))}
                      placeholder="e.g. Thank you for making my mother smile like that."
                      data-testid="mb-host-msg" />
                  </div>
                  <div>
                    <Label className="text-xs">Family to thank (page 5)</Label>
                    <Input value={form.thank_family}
                      onChange={e => setForm(f => ({ ...f, thank_family: e.target.value }))}
                      placeholder="e.g. The entire Kulkarni family" data-testid="mb-thank" />
                  </div>
                  <div className="rounded-md border bg-amber-50/40 p-3 space-y-2 mt-2">
                    <div className="text-[11px] font-semibold uppercase tracking-wide text-amber-800">
                      Personalisation
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <Label className="text-xs">Language</Label>
                        <Select value={form.language}
                          onValueChange={v => setForm(f => ({ ...f, language: v }))}>
                          <SelectTrigger className="h-9" data-testid="mb-language">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="English">English</SelectItem>
                            <SelectItem value="Marathi">Marathi</SelectItem>
                            <SelectItem value="Bilingual">Bilingual (default)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-xs">Font Size</Label>
                        <Select value={form.font_size}
                          onValueChange={v => setForm(f => ({ ...f, font_size: v }))}>
                          <SelectTrigger className="h-9" data-testid="mb-font-size">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="S">Small (compact)</SelectItem>
                            <SelectItem value="M">Medium (default)</SelectItem>
                            <SelectItem value="L">Large (elder-friendly)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-md border bg-amber-50/40 p-3 space-y-2 mt-2">
                    <div className="text-[11px] font-semibold uppercase tracking-wide text-amber-800">
                      Center Branding & Booking QR
                    </div>
                    <div>
                      <Label className="text-xs">Instagram URL <span className="text-muted-foreground font-normal">(auto-filled, editable)</span></Label>
                      <Input value={form.instagram_url}
                        onChange={e => setForm(f => ({ ...f, instagram_url: e.target.value }))}
                        placeholder="https://instagram.com/purnabramha_hsr"
                        data-testid="mb-instagram" />
                    </div>
                    <div>
                      <Label className="text-xs">Center Phone</Label>
                      <Input value={form.phone}
                        onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                        placeholder="+91 98765 43210"
                        data-testid="mb-phone" />
                    </div>
                    <label className="flex items-center gap-2 text-xs cursor-pointer">
                      <input type="checkbox" checked={form.show_qr}
                        onChange={e => setForm(f => ({ ...f, show_qr: e.target.checked }))}
                        className="w-3.5 h-3.5"
                        data-testid="mb-show-qr" />
                      <span>Embed <strong>booking QR</strong> on cover + last page</span>
                    </label>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Photos */}
              <AccordionItem value="photos">
                <AccordionTrigger data-testid="mb-acc-photos">4. Photos (up to 10)</AccordionTrigger>
                <AccordionContent className="space-y-3 pt-2">
                  <div>
                    <Label className="text-xs">Event Photos</Label>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {photos.map((p, i) => (
                        <div key={i} className="relative w-20 h-20 rounded-lg overflow-hidden border-2 border-amber-300">
                          <img src={p.b64} alt={p.name} className="w-full h-full object-cover" />
                          <button type="button"
                            className="absolute top-0 right-0 bg-rose-700 text-white rounded-bl px-1"
                            onClick={() => setPhotos(arr => arr.filter((_, idx) => idx !== i))}
                            data-testid={`mb-photo-remove-${i}`}>
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      ))}
                      <label className="cursor-pointer w-20 h-20 rounded-lg border-2 border-dashed flex flex-col items-center justify-center text-[10px] text-muted-foreground hover:bg-amber-50">
                        <input ref={fileInput} type="file" accept="image/*" multiple className="hidden"
                          onChange={onPhotosSelect} data-testid="mb-photos-input" />
                        <Upload className="w-4 h-4 mb-0.5" />
                        Add ({photos.length}/10)
                      </label>
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Team Photo (single, optional — page 4)</Label>
                    <div className="flex items-center gap-2 mt-1">
                      {teamPhoto ? (
                        <div className="relative w-28 h-20 rounded-lg overflow-hidden border-2 border-amber-300">
                          <img src={teamPhoto} alt="team" className="w-full h-full object-cover" />
                          <button type="button"
                            className="absolute top-0 right-0 bg-rose-700 text-white rounded-bl px-1"
                            onClick={() => setTeamPhoto('')}>
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      ) : (
                        <label className="cursor-pointer w-28 h-20 rounded-lg border-2 border-dashed flex flex-col items-center justify-center text-[10px] text-muted-foreground hover:bg-amber-50">
                          <input type="file" accept="image/*" className="hidden"
                            onChange={onTeamPhotoSelect} data-testid="mb-team-photo-input" />
                          <Upload className="w-4 h-4 mb-0.5" />Team photo
                        </label>
                      )}
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Team */}
              <AccordionItem value="team">
                <AccordionTrigger data-testid="mb-acc-team">
                  5. Team Roster ({team.length} member{team.length !== 1 ? 's' : ''})
                </AccordionTrigger>
                <AccordionContent className="space-y-3 pt-2">
                  <div className="flex gap-2 flex-wrap">
                    <Button size="sm" variant="outline" onClick={fetchRoster} disabled={busyRoster}
                      data-testid="mb-pull-roster">
                      {busyRoster ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <Users className="w-3.5 h-3.5 mr-1" />}
                      Auto-pull from attendance
                    </Button>
                    <Button size="sm" variant="outline" onClick={addTeamMember} data-testid="mb-add-team">
                      <Plus className="w-3.5 h-3.5 mr-1" />Add manually
                    </Button>
                    {team.length > 0 && (
                      <Button size="sm" variant="ghost" onClick={() => setTeam([])} className="text-rose-700">
                        <RefreshCcw className="w-3.5 h-3.5 mr-1" />Clear
                      </Button>
                    )}
                  </div>
                  {team.length === 0 ? (
                    <p className="text-xs text-muted-foreground italic">
                      No team yet. Click <strong>Auto-pull</strong> to fetch members marked Present on the event date,
                      or <strong>Add manually</strong>.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {team.map((m, i) => (
                        <div key={i} className="grid grid-cols-12 gap-2" data-testid={`mb-team-row-${i}`}>
                          <Input className="col-span-5" placeholder="Name" value={m.name}
                            onChange={e => updateTeam(i, 'name', e.target.value)} />
                          <Select value={m.role} onValueChange={v => updateTeam(i, 'role', v)}>
                            <SelectTrigger className="col-span-6 h-9"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              {ROLE_PRESETS.includes(m.role) ? null : <SelectItem value={m.role}>{m.role}</SelectItem>}
                              {ROLE_PRESETS.map(r => <SelectItem key={r} value={r}>{r}</SelectItem>)}
                            </SelectContent>
                          </Select>
                          <Button size="sm" variant="ghost" className="col-span-1 text-rose-700"
                            onClick={() => removeTeam(i)}><Trash2 className="w-4 h-4" /></Button>
                        </div>
                      ))}
                    </div>
                  )}
                </AccordionContent>
              </AccordionItem>
            </Accordion>

            <div className="flex gap-2 mt-4">
              <Button onClick={generate} disabled={busyGen}
                className="flex-1 bg-[#8B0000] hover:bg-[#5C0000] text-white"
                size="lg" data-testid="mb-generate-btn">
                {busyGen
                  ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Composing memory book…</>
                  : <><BookHeart className="w-4 h-4 mr-2" />Generate Memory Box</>}
              </Button>
              <Button variant="outline" onClick={resetForm} disabled={busyGen} data-testid="mb-reset-btn">
                <RefreshCcw className="w-4 h-4 mr-1" />Reset
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* ── Preview (right) ──────────────────────────────────────── */}
        <Card className="lg:col-span-2" data-testid="mb-preview-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Preview &amp; Deliver</CardTitle>
            <CardDescription>Generated cover, full GPT-5.2 narrative &amp; one-click delivery.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {busyGen ? (
              <div className="aspect-[3/4] rounded-lg bg-gradient-to-br from-amber-50 to-rose-50 border-2 border-dashed border-amber-300 flex flex-col items-center justify-center gap-3">
                <Loader2 className="w-10 h-10 text-amber-700 animate-spin" />
                <p className="text-sm text-amber-900 text-center px-4">Weaving your guest's story with GPT-5.2…</p>
              </div>
            ) : result ? (
              <>
                {result.cover_png_base64 ? (
                  <img src={`data:image/png;base64,${result.cover_png_base64}`}
                    alt="Memory Box Cover" className="w-full rounded-lg shadow-lg border-2 border-amber-200"
                    data-testid="mb-cover-preview" />
                ) : (
                  <div className="rounded-lg border-2 border-amber-200 bg-amber-50 p-6 text-center text-sm text-amber-900">
                    Memory Book PDF ready ({result.pdf_size_kb} KB)
                  </div>
                )}
                <div className="rounded border bg-amber-50/50 p-3 space-y-2 max-h-72 overflow-auto" data-testid="mb-narrative">
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-amber-900">Your Story</p>
                    <p className="text-xs mt-0.5 whitespace-pre-line">{result.story_text}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-amber-900">Gratitude</p>
                    <p className="text-xs mt-0.5 whitespace-pre-line">{result.gratitude_text}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-amber-900">Blessing</p>
                    <p className="text-xs mt-0.5 italic whitespace-pre-line">{result.blessing_text}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-amber-900">Future Invitation</p>
                    <p className="text-xs mt-0.5 whitespace-pre-line">{result.future_invitation_text}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  <Button size="sm" className="bg-[#8B0000] hover:bg-[#5C0000] text-white"
                    onClick={() => downloadPdf(result.box_id, form.guest_name)} data-testid="mb-download-pdf">
                    <Download className="w-3.5 h-3.5 mr-1" />PDF
                  </Button>
                  {result.cover_png_base64 && (
                    <Button size="sm" variant="outline"
                      className="border-amber-500 text-amber-900 hover:bg-amber-50"
                      onClick={() => {
                        const link = document.createElement('a');
                        link.href = `data:image/png;base64,${result.cover_png_base64}`;
                        link.download = `MemoryBox_${(form.guest_name || 'guest').replace(/\s+/g, '_')}.png`;
                        document.body.appendChild(link); link.click(); link.remove();
                      }}
                      data-testid="mb-download-png">
                      <Download className="w-3.5 h-3.5 mr-1" />Summary Image
                    </Button>
                  )}
                  <Button size="sm" variant="outline" onClick={() => sendWhatsapp(result.box_id)}
                    disabled={!form.mobile} data-testid="mb-send-wa">
                    <MessageSquare className="w-3.5 h-3.5 mr-1" />WhatsApp
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => sendEmail(result.box_id, form.email)}
                    disabled={busyEmail} data-testid="mb-send-email">
                    {busyEmail
                      ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
                      : <Mail className="w-3.5 h-3.5 mr-1" />}
                    Email
                  </Button>
                </div>
                <p className="text-[10px] text-muted-foreground">
                  WhatsApp opens with a pre-filled message; please attach the downloaded PDF in the chat.
                </p>
              </>
            ) : (
              <div className="aspect-[3/4] rounded-lg bg-gradient-to-br from-amber-50 to-rose-50 border-2 border-dashed border-amber-300 flex items-center justify-center text-center p-6">
                <div>
                  <BookHeart className="w-12 h-12 text-rose-300 mx-auto mb-2" />
                  <p className="text-sm text-amber-900 max-w-xs">
                    Fill the sections on the left &amp; click <strong>Generate Memory Box</strong> to see your
                    guest's personalised 7-page memory book here.
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* History */}
      <Card data-testid="mb-history-card">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <History className="w-4 h-4" />Recent Memory Boxes
          </CardTitle>
          <CardDescription>Re-download, re-share or re-email any past box.</CardDescription>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground italic">No memory boxes generated yet.</p>
          ) : (
            <div className="overflow-auto">
              <table className="w-full text-xs">
                <thead className="bg-amber-50">
                  <tr className="text-left">
                    <th className="p-2">Date</th>
                    <th className="p-2">Guest</th>
                    <th className="p-2">Occasion</th>
                    <th className="p-2">Center</th>
                    <th className="p-2">Sent</th>
                    <th className="p-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map(h => (
                    <tr key={h.box_id} className="border-b" data-testid={`mb-history-${h.box_id}`}>
                      <td className="p-2">{h.event_date}</td>
                      <td className="p-2 font-medium">{h.guest_name}</td>
                      <td className="p-2">{h.occasion}</td>
                      <td className="p-2">{h.center}</td>
                      <td className="p-2 space-x-1">
                        {h.delivery?.whatsapp ? <Badge variant="secondary" className="bg-emerald-50 text-emerald-700">WA</Badge> : null}
                        {h.delivery?.email ? <Badge variant="secondary" className="bg-sky-50 text-sky-700">Email</Badge> : null}
                        {h.delivery?.downloads ? <Badge variant="outline">{h.delivery.downloads} dl</Badge> : null}
                      </td>
                      <td className="p-2 space-x-1">
                        <Button size="sm" variant="outline" className="h-7 text-[10px]"
                          onClick={() => downloadPdf(h.box_id, h.guest_name)}>
                          <Download className="w-3 h-3 mr-1" />PDF
                        </Button>
                        <Button size="sm" variant="outline" className="h-7 text-[10px]"
                          onClick={() => sendWhatsapp(h.box_id)}>
                          <Send className="w-3 h-3 mr-1" />WA
                        </Button>
                        <Button size="sm" variant="outline" className="h-7 text-[10px]"
                          onClick={() => sendEmail(h.box_id, h.email)}>
                          <Mail className="w-3 h-3 mr-1" />Email
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
