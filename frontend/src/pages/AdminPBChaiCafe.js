import { useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Save, Plus, Trash2, Loader2, ChefHat, FileText, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const API = process.env.REACT_APP_BACKEND_URL;

export default function AdminPBChaiCafe({ token }) {
  const [tab, setTab] = useState('settings');
  const [cfg, setCfg] = useState(null);
  const [apps, setApps] = useState([]);
  const [saving, setSaving] = useState(false);
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    axios.get(`${API}/api/pb-chai/config`).then(r => setCfg(r.data)).catch(() => {});
    axios.get(`${API}/api/admin/pb-chai/franchise-applications`, { headers })
      .then(r => setApps(r.data.applications || [])).catch(() => {});
  }, []);

  if (!cfg) return <div className="py-10 text-center"><Loader2 className="h-6 w-6 animate-spin text-[#B8962E] mx-auto" /></div>;

  const save = async () => {
    setSaving(true);
    try {
      const r = await axios.put(`${API}/api/admin/pb-chai/config`, cfg, { headers });
      setCfg(r.data);
      toast.success('PB Chai Café settings saved');
    } catch { toast.error('Save failed'); }
    finally { setSaving(false); }
  };

  const set = (path, value) => {
    setCfg(prev => {
      const next = { ...prev };
      const keys = path.split('.');
      let cur = next;
      for (let i = 0; i < keys.length - 1; i++) {
        cur[keys[i]] = { ...(cur[keys[i]] || {}) };
        cur = cur[keys[i]];
      }
      cur[keys[keys.length - 1]] = value;
      return next;
    });
  };

  const updateMenuItem = (i, k, v) => {
    const items = [...(cfg.menu_items || [])];
    items[i] = { ...items[i], [k]: v };
    set('menu_items', items);
  };
  const addMenuItem = () => set('menu_items', [...(cfg.menu_items || []), { id: `m-${Date.now()}`, name: '', category: 'Chai', price: 0, description: '', image_url: '', active: true }]);
  const deleteMenuItem = (i) => set('menu_items', (cfg.menu_items || []).filter((_, j) => j !== i));

  const updateSetupHead = (i, k, v) => {
    const heads = [...(cfg.setup_heads || [])];
    heads[i] = { ...heads[i], [k]: v };
    set('setup_heads', heads);
  };
  const addSetupHead = () => set('setup_heads', [...(cfg.setup_heads || []), { id: `h-${Date.now()}`, label: '', amount: 0, remarks: '' }]);
  const deleteSetupHead = (i) => set('setup_heads', (cfg.setup_heads || []).filter((_, j) => j !== i));

  const updateApp = async (id, status) => {
    try {
      await axios.patch(`${API}/api/admin/pb-chai/franchise-applications/${id}`, { status }, { headers });
      const r = await axios.get(`${API}/api/admin/pb-chai/franchise-applications`, { headers });
      setApps(r.data.applications || []);
    } catch { toast.error('Failed'); }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2 border-b border-[#E8DFD0] pb-2">
        {[['settings', 'Settings'], ['applications', `Applications (${apps.length})`]].map(([t, l]) => (
          <button key={t} onClick={() => setTab(t)} className={`px-4 py-2 text-sm font-body uppercase tracking-wider ${tab === t ? 'text-[#B8962E] border-b-2 border-[#B8962E]' : 'text-[#7A6F65]'}`} data-testid={`pbchai-tab-${t}`}>{l}</button>
        ))}
      </div>

      {tab === 'settings' && (
        <div className="space-y-4">
          {/* Branding */}
          <Card className="border-[#E8DFD0]">
            <CardHeader><CardTitle className="text-base">Branding & Assets</CardTitle></CardHeader>
            <CardContent className="grid sm:grid-cols-2 gap-3">
              <UrlField label="Logo URL" value={cfg.logo_url} onChange={v => set('logo_url', v)} testId="pbchai-logo" />
              <UrlField label="Kiosk Image URL" value={cfg.kiosk_image_url} onChange={v => set('kiosk_image_url', v)} testId="pbchai-kiosk" />
              <UrlField label="Brochure URL (PDF)" value={cfg.brochure_url} onChange={v => set('brochure_url', v)} testId="pbchai-brochure" />
            </CardContent>
          </Card>

          {/* Menu */}
          <Card className="border-[#E8DFD0]">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2"><ChefHat className="h-4 w-4 text-[#B8962E]" /> Menu Items</CardTitle>
              <Button size="sm" onClick={addMenuItem} className="bg-[#B8962E] text-white text-xs" data-testid="pbchai-add-menu"><Plus className="h-3 w-3 mr-1" /> Add</Button>
            </CardHeader>
            <CardContent className="space-y-2">
              {(cfg.menu_items || []).map((m, i) => (
                <div key={m.id || i} className="grid grid-cols-12 gap-2 items-center text-xs">
                  <Input placeholder="Name" value={m.name} onChange={e => updateMenuItem(i, 'name', e.target.value)} className="col-span-3 h-8 text-xs" />
                  <Input placeholder="Category" value={m.category} onChange={e => updateMenuItem(i, 'category', e.target.value)} className="col-span-2 h-8 text-xs" />
                  <Input type="number" placeholder="Price" value={m.price} onChange={e => updateMenuItem(i, 'price', parseFloat(e.target.value) || 0)} className="col-span-1 h-8 text-xs" />
                  <Input placeholder="Description" value={m.description} onChange={e => updateMenuItem(i, 'description', e.target.value)} className="col-span-3 h-8 text-xs" />
                  <Input placeholder="Image URL" value={m.image_url} onChange={e => updateMenuItem(i, 'image_url', e.target.value)} className="col-span-2 h-8 text-xs" />
                  <label className="col-span-1 flex items-center justify-center text-[10px]">
                    <input type="checkbox" checked={m.active !== false} onChange={e => updateMenuItem(i, 'active', e.target.checked)} />
                  </label>
                  <Button size="sm" variant="ghost" onClick={() => deleteMenuItem(i)} className="col-span-12 sm:col-span-1 text-red-600 hover:bg-red-50 p-1 justify-self-end"><Trash2 className="h-3 w-3" /></Button>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Fees */}
          <Card className="border-[#E8DFD0]">
            <CardHeader><CardTitle className="text-base">Franchise Fee Settings</CardTitle></CardHeader>
            <CardContent className="grid sm:grid-cols-2 gap-3">
              <NumField label="Franchise Fee (₹)" value={cfg.franchise_fee_inr} onChange={v => set('franchise_fee_inr', v)} testId="pbchai-fee" />
              <NumField label="Security Deposit (₹)" value={cfg.security_deposit_inr} onChange={v => set('security_deposit_inr', v)} testId="pbchai-deposit" />
              <label className="flex items-center gap-2 text-xs col-span-2">
                <input type="checkbox" checked={!!cfg.deposit_refundable} onChange={e => set('deposit_refundable', e.target.checked)} /> Security deposit is refundable
              </label>
              <div className="col-span-2">
                <Label className="text-xs">Deposit note</Label>
                <Input value={cfg.deposit_note || ''} onChange={e => set('deposit_note', e.target.value)} className="text-xs" />
              </div>
            </CardContent>
          </Card>

          {/* Setup heads */}
          <Card className="border-[#E8DFD0]">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Setup Investment Heads</CardTitle>
              <Button size="sm" onClick={addSetupHead} className="bg-[#B8962E] text-white text-xs"><Plus className="h-3 w-3 mr-1" /> Add Head</Button>
            </CardHeader>
            <CardContent className="space-y-2">
              {(cfg.setup_heads || []).map((h, i) => (
                <div key={h.id || i} className="grid grid-cols-12 gap-2 items-center text-xs">
                  <Input placeholder="Label" value={h.label} onChange={e => updateSetupHead(i, 'label', e.target.value)} className="col-span-5 h-8 text-xs" />
                  <Input type="number" placeholder="Amount" value={h.amount} onChange={e => updateSetupHead(i, 'amount', parseFloat(e.target.value) || 0)} className="col-span-2 h-8 text-xs" />
                  <Input placeholder="Remarks" value={h.remarks || ''} onChange={e => updateSetupHead(i, 'remarks', e.target.value)} className="col-span-4 h-8 text-xs" />
                  <Button size="sm" variant="ghost" onClick={() => deleteSetupHead(i)} className="col-span-1 text-red-600 p-1"><Trash2 className="h-3 w-3" /></Button>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Royalty */}
          <Card className="border-[#E8DFD0]">
            <CardHeader><CardTitle className="text-base">Royalty & Marketing</CardTitle></CardHeader>
            <CardContent className="grid sm:grid-cols-3 gap-3">
              <NumField label="Royalty %" value={cfg.royalty_pct} step={0.5} onChange={v => set('royalty_pct', v)} />
              <NumField label="Marketing Fund %" value={cfg.marketing_pct} step={0.5} onChange={v => set('marketing_pct', v)} />
              <label className="flex items-center gap-2 text-xs">
                <input type="checkbox" checked={!!cfg.royalty_gst_applicable} onChange={e => set('royalty_gst_applicable', e.target.checked)} /> GST applicable on royalty
              </label>
            </CardContent>
          </Card>

          {/* Projections */}
          <Card className="border-[#E8DFD0]">
            <CardHeader><CardTitle className="text-base">Financial Projections</CardTitle></CardHeader>
            <CardContent className="grid sm:grid-cols-3 gap-3">
              <NumField label="Avg Monthly Sale" value={cfg.projections?.avg_monthly_sale} onChange={v => set('projections.avg_monthly_sale', v)} />
              <NumField label="Avg Gross Profit" value={cfg.projections?.avg_gross_profit} onChange={v => set('projections.avg_gross_profit', v)} />
              <NumField label="Gross Margin %" value={cfg.projections?.gross_margin_pct} onChange={v => set('projections.gross_margin_pct', v)} />
              <NumField label="Net Profit Min" value={cfg.projections?.net_profit_min} onChange={v => set('projections.net_profit_min', v)} />
              <NumField label="Net Profit Max" value={cfg.projections?.net_profit_max} onChange={v => set('projections.net_profit_max', v)} />
              <TextField label="Break-even Months" value={cfg.projections?.breakeven_months} onChange={v => set('projections.breakeven_months', v)} />
              <TextField label="ROI Months" value={cfg.projections?.roi_months} onChange={v => set('projections.roi_months', v)} />
              <NumField label="Food Cost %" value={cfg.projections?.food_cost_pct} onChange={v => set('projections.food_cost_pct', v)} />
              <NumField label="Packaging Cost %" value={cfg.projections?.packaging_cost_pct} onChange={v => set('projections.packaging_cost_pct', v)} />
              <NumField label="Employee Cost %" value={cfg.projections?.employee_cost_pct} onChange={v => set('projections.employee_cost_pct', v)} />
              <NumField label="Rent & Utilities %" value={cfg.projections?.rent_utilities_pct} onChange={v => set('projections.rent_utilities_pct', v)} />
              <NumField label="Other Expenses %" value={cfg.projections?.other_expenses_pct} onChange={v => set('projections.other_expenses_pct', v)} />
            </CardContent>
          </Card>

          {/* Locations & vendors */}
          <Card className="border-[#E8DFD0]">
            <CardHeader><CardTitle className="text-base">Lists</CardTitle></CardHeader>
            <CardContent className="grid sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Ideal Locations (one per line)</Label>
                <Textarea rows={6} value={(cfg.ideal_locations || []).join('\n')} onChange={e => set('ideal_locations', e.target.value.split('\n').map(s => s.trim()).filter(Boolean))} className="text-xs" />
              </div>
              <div>
                <Label className="text-xs">Approved Vendors (one per line)</Label>
                <Textarea rows={6} value={(cfg.vendors || []).join('\n')} onChange={e => set('vendors', e.target.value.split('\n').map(s => s.trim()).filter(Boolean))} className="text-xs" />
              </div>
            </CardContent>
          </Card>

          {/* Footer */}
          <Card className="border-[#E8DFD0]">
            <CardHeader><CardTitle className="text-base">Contact / Footer</CardTitle></CardHeader>
            <CardContent className="grid sm:grid-cols-3 gap-3">
              <TextField label="Phone" value={cfg.footer?.phone} onChange={v => set('footer.phone', v)} />
              <TextField label="Email" value={cfg.footer?.email} onChange={v => set('footer.email', v)} />
              <TextField label="Website" value={cfg.footer?.website} onChange={v => set('footer.website', v)} />
            </CardContent>
          </Card>

          {/* Visibility */}
          <Card className="border-[#E8DFD0]">
            <CardHeader><CardTitle className="text-base">Section Visibility</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {['menu', 'model', 'vendors', 'investment', 'royalty', 'projections', 'locations', 'journey', 'application'].map(k => (
                <label key={k} className="flex items-center gap-2 text-xs capitalize">
                  <input type="checkbox" checked={cfg.sections_visible?.[k] !== false} onChange={e => set(`sections_visible.${k}`, e.target.checked)} /> {k}
                </label>
              ))}
            </CardContent>
          </Card>

          <Button onClick={save} disabled={saving} className="w-full bg-[#B8962E] text-white py-5 rounded-none tracking-widest uppercase text-xs font-semibold" data-testid="pbchai-save">
            {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
            Save PB Chai Café Settings
          </Button>
        </div>
      )}

      {tab === 'applications' && (
        <div className="space-y-2">
          {apps.length === 0 && <p className="text-center py-10 italic text-[#7A6F65] text-sm">No franchise applications yet.</p>}
          {apps.map(a => (
            <div key={a.id} className="bg-white border border-[#E8DFD0] p-4 space-y-2" data-testid={`pbchai-app-${a.id}`}>
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="min-w-0">
                  <p className="font-heading text-base text-[#3D2314]">{a.full_name}</p>
                  <p className="text-xs font-body text-[#7A6F65]">{a.mobile} {a.email && `· ${a.email}`}</p>
                  <p className="text-xs font-body text-[#7A6F65]">{a.city}, {a.state}, {a.country}</p>
                </div>
                <div className="text-right">
                  <Badge className={a.status === 'launched' ? 'bg-green-100 text-green-700' : a.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}>{a.status}</Badge>
                  <p className="text-[10px] text-[#7A6F65] mt-1">{(a.created_at || '').slice(0,10)}</p>
                </div>
              </div>
              <div className="grid sm:grid-cols-3 gap-2 text-xs font-body pt-2 border-t border-[#E8DFD0]">
                <div><p className="text-[10px] uppercase text-[#7A6F65]">Investment</p><p>{a.investment_capacity || '—'}</p></div>
                <div><p className="text-[10px] uppercase text-[#7A6F65]">Preferred Location</p><p>{a.preferred_location || '—'}</p></div>
                <div><p className="text-[10px] uppercase text-[#7A6F65]">Available Area</p><p>{a.available_area || '—'}</p></div>
              </div>
              {a.message && <p className="text-xs italic text-[#5C4A3A] pt-1">&ldquo;{a.message}&rdquo;</p>}
              <div className="flex flex-wrap gap-1.5 pt-2">
                {['submitted','discussion','approved','fee_paid','agreement','training','launched','rejected'].map(s => (
                  <Button key={s} size="sm" variant="outline" onClick={() => updateApp(a.id, s)} className={`text-[10px] py-1 px-2 h-auto ${a.status === s ? 'bg-[#B8962E] text-white border-[#B8962E]' : ''}`}>{s}</Button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NumField({ label, value, onChange, step = 1, testId }) {
  return (
    <div>
      <Label className="text-xs">{label}</Label>
      <Input type="number" step={step} value={value ?? ''} onChange={e => onChange(parseFloat(e.target.value) || 0)} className="text-xs" data-testid={testId} />
    </div>
  );
}
function TextField({ label, value, onChange, testId }) {
  return (
    <div>
      <Label className="text-xs">{label}</Label>
      <Input value={value || ''} onChange={e => onChange(e.target.value)} className="text-xs" data-testid={testId} />
    </div>
  );
}
function UrlField({ label, value, onChange, testId }) {
  return (
    <div>
      <Label className="text-xs">{label}</Label>
      <Input value={value || ''} onChange={e => onChange(e.target.value)} placeholder="https://..." className="text-xs" data-testid={testId} />
      {value && /(image|png|jpg|jpeg|webp|drive\.google\.com|googleusercontent\.com)/i.test(value) && (
        <img src={value} alt="" className="h-16 w-auto mt-1 border border-[#E8DFD0]" onError={(e) => { e.target.style.display = 'none'; }} />
      )}
    </div>
  );
}
