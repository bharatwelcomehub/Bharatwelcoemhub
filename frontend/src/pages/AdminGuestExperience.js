import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import {
  Heart, Star, Trash2, Plus, Search, CheckCircle2, XCircle, Filter, Download,
  TrendingUp, MessageSquare, MapPin, Loader2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

const API = process.env.REACT_APP_BACKEND_URL;

export default function AdminGuestExperience({ token, locations = [] }) {
  const [tab, setTab] = useState('dashboard'); // dashboard | feedback | offers
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState({ feedback: [], summary: {}, center_breakdown: [] });
  const [offers, setOffers] = useState([]);

  // Filters
  const [fCenter, setFCenter] = useState('');
  const [fRating, setFRating] = useState('');
  const [fRec, setFRec] = useState('');
  const [fVisit, setFVisit] = useState('');
  const [fFrom, setFFrom] = useState('');
  const [fTo, setFTo] = useState('');
  const [fSearch, setFSearch] = useState('');

  // Offer form
  const [editingOffer, setEditingOffer] = useState(null);

  const headers = { Authorization: `Bearer ${token}` };

  const loadFeedback = async () => {
    setLoading(true);
    try {
      const params = {};
      if (fCenter) params.center_id = fCenter;
      if (fRating) params.rating_min = fRating;
      if (fRec) params.recommend = fRec;
      if (fVisit) params.visit_type = fVisit;
      if (fFrom) params.date_from = fFrom;
      if (fTo) params.date_to = fTo;
      if (fSearch) params.search = fSearch;
      const r = await axios.get(`${API}/api/admin/guest-feedback`, { headers, params });
      setData(r.data);
    } catch { toast.error('Failed to load feedback'); }
    finally { setLoading(false); }
  };

  const loadOffers = async () => {
    try {
      const r = await axios.get(`${API}/api/admin/discount-offers`, { headers });
      setOffers(r.data.offers || []);
    } catch { toast.error('Failed to load offers'); }
  };

  useEffect(() => { loadFeedback(); loadOffers(); }, []); // eslint-disable-line

  const toggleApproved = async (fb) => {
    try {
      await axios.patch(`${API}/api/admin/guest-feedback/${fb.id}`, { public_approved: !fb.public_approved }, { headers });
      toast.success(fb.public_approved ? 'Hidden from public' : 'Published to public');
      loadFeedback();
    } catch { toast.error('Update failed'); }
  };

  const markStatus = async (fb, status) => {
    try {
      await axios.patch(`${API}/api/admin/guest-feedback/${fb.id}`, { status }, { headers });
      toast.success(`Coupon marked ${status}`);
      loadFeedback();
    } catch { toast.error('Update failed'); }
  };

  const saveOffer = async (offer) => {
    try {
      if (offer.id) {
        await axios.patch(`${API}/api/admin/discount-offers/${offer.id}`, offer, { headers });
      } else {
        await axios.post(`${API}/api/admin/discount-offers`, offer, { headers });
      }
      toast.success('Offer saved');
      setEditingOffer(null); loadOffers();
    } catch { toast.error('Save failed'); }
  };

  const deleteOffer = async (id) => {
    if (!window.confirm('Delete this offer?')) return;
    try {
      await axios.delete(`${API}/api/admin/discount-offers/${id}`, { headers });
      loadOffers();
    } catch { toast.error('Delete failed'); }
  };

  const exportCSV = () => {
    const rows = data.feedback.map(f => ({
      coupon: f.coupon_code, name: f.guest_name, mobile: f.mobile, email: f.email,
      center: f.center_name, visit_date: f.visit_date, visit_type: f.visit_type,
      overall: f.overall_rating, food: f.food_rating, service: f.service_rating, clean: f.cleanliness_rating,
      recommend: f.will_recommend, return: f.will_visit_again,
      liked: (f.liked_most || '').replace(/[\r\n,]/g, ' '),
      see_more: (f.see_more || '').replace(/[\r\n,]/g, ' '),
      changes: (f.three_changes || '').replace(/[\r\n,]/g, ' '),
      status: f.status, public_approved: f.public_approved, created_at: f.created_at,
    }));
    if (!rows.length) { toast.error('No rows to export'); return; }
    const headerLine = Object.keys(rows[0]).join(',');
    const body = rows.map(r => Object.values(r).map(v => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([headerLine + '\n' + body], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `guest-feedback-${Date.now()}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  const StatCard = ({ icon: Icon, label, value, suffix = '' }) => (
    <div className="bg-white border border-[#E8DFD0] p-4">
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-[#7A6F65] font-body">
        <Icon className="h-3.5 w-3.5 text-[#B8962E]" /> {label}
      </div>
      <p className="font-heading text-2xl text-[#3D2314] mt-1">{value}{suffix && <span className="text-sm text-[#7A6F65]">{suffix}</span>}</p>
    </div>
  );

  return (
    <div className="space-y-5" data-testid="admin-guest-experience">
      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-[#E8DFD0] pb-2">
        {['dashboard', 'feedback', 'offers'].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-body uppercase tracking-wider transition-colors ${tab === t ? 'text-[#B8962E] border-b-2 border-[#B8962E]' : 'text-[#7A6F65] hover:text-[#3D2314]'}`}
            data-testid={`ge-tab-${t}`}>
            {t === 'dashboard' && <TrendingUp className="h-3.5 w-3.5 inline mr-1.5" />}
            {t === 'feedback' && <MessageSquare className="h-3.5 w-3.5 inline mr-1.5" />}
            {t === 'offers' && <Heart className="h-3.5 w-3.5 inline mr-1.5" />}
            {t}
          </button>
        ))}
      </div>

      {/* DASHBOARD */}
      {tab === 'dashboard' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <StatCard icon={MessageSquare} label="Total Feedback" value={data.summary?.total || 0} />
            <StatCard icon={Star} label="Avg Overall" value={data.summary?.avg_overall || 0} suffix=" / 5" />
            <StatCard icon={Star} label="Food" value={data.summary?.avg_food || 0} suffix=" / 5" />
            <StatCard icon={Star} label="Service" value={data.summary?.avg_service || 0} suffix=" / 5" />
            <StatCard icon={Star} label="Cleanliness" value={data.summary?.avg_cleanliness || 0} suffix=" / 5" />
            <StatCard icon={TrendingUp} label="Recommend" value={data.summary?.recommend_yes_pct || 0} suffix="%" />
          </div>
          <Card className="border-[#E8DFD0]">
            <CardHeader><CardTitle className="text-base flex items-center gap-2"><MapPin className="h-4 w-4 text-[#B8962E]" /> Center-wise Comparison</CardTitle></CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-body min-w-[640px]">
                  <thead className="bg-[#F8F5F0] text-[#5C4A3A] uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="text-left px-3 py-2">Center</th>
                      <th className="px-3 py-2">Count</th>
                      <th className="px-3 py-2">Overall</th>
                      <th className="px-3 py-2">Food</th>
                      <th className="px-3 py-2">Service</th>
                      <th className="px-3 py-2">Clean</th>
                      <th className="px-3 py-2">Recommend %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.center_breakdown || []).map((c, i) => (
                      <tr key={i} className="border-t border-[#E8DFD0]">
                        <td className="px-3 py-2 text-[#3D2314] font-medium">{c.center_name || c.center_id}</td>
                        <td className="text-center px-3 py-2">{c.count}</td>
                        <td className="text-center px-3 py-2">{c.avg_overall}</td>
                        <td className="text-center px-3 py-2">{c.avg_food}</td>
                        <td className="text-center px-3 py-2">{c.avg_service}</td>
                        <td className="text-center px-3 py-2">{c.avg_clean}</td>
                        <td className="text-center px-3 py-2 text-[#B8962E] font-medium">{c.recommend_yes_pct}%</td>
                      </tr>
                    ))}
                    {(data.center_breakdown || []).length === 0 && (
                      <tr><td colSpan={7} className="text-center py-6 italic text-[#7A6F65]">No data yet.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* FEEDBACK LIST */}
      {tab === 'feedback' && (
        <div className="space-y-3">
          {/* Filters */}
          <Card className="border-[#E8DFD0]">
            <CardContent className="p-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-2">
              <div className="lg:col-span-2 flex items-center gap-1 border border-[#E8DFD0] px-2 bg-white">
                <Search className="h-3.5 w-3.5 text-[#7A6F65]" />
                <Input value={fSearch} onChange={e => setFSearch(e.target.value)} placeholder="Name / mobile / coupon" className="border-0 text-xs h-8 focus-visible:ring-0" data-testid="ge-search" />
              </div>
              <Select value={fCenter || 'all'} onValueChange={v => setFCenter(v === 'all' ? '' : v)}>
                <SelectTrigger className="text-xs h-8" data-testid="ge-filter-center"><SelectValue placeholder="Center" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All centers</SelectItem>
                  {locations.map(l => <SelectItem key={l.id} value={l.center_id || l.id}>{l.name}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={fRating || 'all'} onValueChange={v => setFRating(v === 'all' ? '' : v)}>
                <SelectTrigger className="text-xs h-8"><SelectValue placeholder="Min rating" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Any rating</SelectItem>
                  {[5, 4, 3, 2, 1].map(n => <SelectItem key={n} value={String(n)}>{n}+ stars</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={fRec || 'all'} onValueChange={v => setFRec(v === 'all' ? '' : v)}>
                <SelectTrigger className="text-xs h-8"><SelectValue placeholder="Recommend" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Any</SelectItem>
                  <SelectItem value="Yes">Yes</SelectItem>
                  <SelectItem value="Maybe">Maybe</SelectItem>
                  <SelectItem value="No">No</SelectItem>
                </SelectContent>
              </Select>
              <Select value={fVisit || 'all'} onValueChange={v => setFVisit(v === 'all' ? '' : v)}>
                <SelectTrigger className="text-xs h-8"><SelectValue placeholder="Visit type" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Any visit</SelectItem>
                  <SelectItem value="Dine-in">Dine-in</SelectItem>
                  <SelectItem value="Takeaway">Takeaway</SelectItem>
                  <SelectItem value="Delivery">Delivery</SelectItem>
                  <SelectItem value="Website Pickup">Website Pickup</SelectItem>
                </SelectContent>
              </Select>
              <Input type="date" value={fFrom} onChange={e => setFFrom(e.target.value)} className="text-xs h-8" placeholder="From" />
              <Input type="date" value={fTo} onChange={e => setFTo(e.target.value)} className="text-xs h-8" placeholder="To" />
              <div className="col-span-2 sm:col-span-3 lg:col-span-7 flex gap-2 pt-1">
                <Button size="sm" onClick={loadFeedback} className="bg-[#B8962E] text-white text-xs" data-testid="ge-apply"><Filter className="h-3 w-3 mr-1" /> Apply</Button>
                <Button size="sm" variant="outline" onClick={exportCSV} className="text-xs" data-testid="ge-export"><Download className="h-3 w-3 mr-1" /> Export CSV</Button>
              </div>
            </CardContent>
          </Card>

          {/* List */}
          {loading ? (
            <div className="text-center py-10"><Loader2 className="h-6 w-6 animate-spin text-[#B8962E] mx-auto" /></div>
          ) : (
            <div className="space-y-2">
              {data.feedback.map(f => (
                <div key={f.id} className="bg-white border border-[#E8DFD0] p-4 space-y-2" data-testid={`ge-feedback-${f.id}`}>
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-heading text-base text-[#3D2314]">{f.guest_name}</p>
                        <span className="text-xs text-[#7A6F65]">·</span>
                        <span className="text-xs font-body text-[#7A6F65]">{f.center_name}</span>
                        <span className="text-xs text-[#7A6F65]">·</span>
                        <span className="text-xs font-body text-[#7A6F65]">{f.visit_date} {f.visit_type && `· ${f.visit_type}`}</span>
                      </div>
                      <div className="flex items-center gap-1 mt-1">
                        {[1,2,3,4,5].map(n => <Star key={n} className={`h-3.5 w-3.5 ${(f.overall_rating || 0) >= n ? 'fill-[#D4AF37] text-[#D4AF37]' : 'text-[#E8DFD0]'}`} />)}
                        <span className="text-xs text-[#7A6F65] ml-2">F:{f.food_rating} S:{f.service_rating} C:{f.cleanliness_rating}</span>
                      </div>
                      <p className="text-xs font-body text-[#7A6F65] mt-1">{f.mobile} {f.email ? `· ${f.email}` : ''}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] uppercase tracking-wider text-[#7A6F65]">Coupon</p>
                      <p className="font-mono text-sm text-[#B8962E]">{f.coupon_code}</p>
                      <Badge className={
                        f.status === 'used' ? 'bg-red-100 text-red-700' :
                        f.status === 'expired' ? 'bg-orange-100 text-orange-700' :
                        'bg-green-100 text-green-700'
                      }>{f.status}</Badge>
                    </div>
                  </div>
                  {(f.liked_most || f.see_more || f.three_changes) && (
                    <div className="text-xs font-body text-[#3D2314] grid sm:grid-cols-3 gap-2 pt-2 border-t border-[#E8DFD0]">
                      {f.liked_most && <div><p className="text-[10px] uppercase tracking-wider text-[#7A6F65]">Liked</p><p>{f.liked_most}</p></div>}
                      {f.see_more && <div><p className="text-[10px] uppercase tracking-wider text-[#7A6F65]">See more</p><p>{f.see_more}</p></div>}
                      {f.three_changes && <div><p className="text-[10px] uppercase tracking-wider text-[#7A6F65]">3 changes</p><p>{f.three_changes}</p></div>}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-2 pt-2 border-t border-[#E8DFD0]">
                    <Button size="sm" variant="outline" onClick={() => toggleApproved(f)} className="text-xs" data-testid={`ge-approve-${f.id}`}>
                      {f.public_approved ? <><XCircle className="h-3 w-3 mr-1 text-red-600" /> Hide</> : <><CheckCircle2 className="h-3 w-3 mr-1 text-green-600" /> Publish</>}
                    </Button>
                    {f.status !== 'used' && <Button size="sm" variant="outline" onClick={() => markStatus(f, 'used')} className="text-xs" data-testid={`ge-mark-used-${f.id}`}>Mark Used</Button>}
                    {f.status !== 'expired' && <Button size="sm" variant="outline" onClick={() => markStatus(f, 'expired')} className="text-xs">Mark Expired</Button>}
                    {f.status !== 'pending' && <Button size="sm" variant="outline" onClick={() => markStatus(f, 'pending')} className="text-xs">Reset</Button>}
                  </div>
                </div>
              ))}
              {data.feedback.length === 0 && <p className="text-center py-10 italic text-[#7A6F65] text-sm">No feedback matches your filters.</p>}
            </div>
          )}
        </div>
      )}

      {/* OFFERS */}
      {tab === 'offers' && (
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <h3 className="font-heading text-base text-[#3D2314]">Discount Offers</h3>
            <Button size="sm" onClick={() => setEditingOffer({ title: '', discount_pct: 10, valid_from: '', valid_till: '', applicable_center_ids: [], is_active: true, terms: 'Discount valid as per center terms. One card per guest/visit.', background_image_url: '' })} className="bg-[#B8962E] text-white text-xs" data-testid="ge-add-offer">
              <Plus className="h-3 w-3 mr-1" /> New Offer
            </Button>
          </div>
          {editingOffer && <OfferEditor offer={editingOffer} setOffer={setEditingOffer} locations={locations} onSave={saveOffer} onCancel={() => setEditingOffer(null)} />}
          <div className="space-y-2">
            {offers.map(o => (
              <div key={o.id} className="bg-white border border-[#E8DFD0] p-4 flex items-start justify-between gap-3 flex-wrap" data-testid={`ge-offer-${o.id}`}>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-heading text-base text-[#3D2314]">{o.title}</p>
                    <Badge className="bg-[#B8962E] text-white">{o.discount_pct}% OFF</Badge>
                    {o.is_active ? <Badge className="bg-green-100 text-green-700">Active</Badge> : <Badge className="bg-gray-100 text-gray-700">Inactive</Badge>}
                  </div>
                  <p className="text-xs font-body text-[#7A6F65] mt-1">
                    {o.valid_from || '—'} → {o.valid_till || '—'} · {(o.applicable_center_ids || []).length ? `${o.applicable_center_ids.length} center(s)` : 'All centers'}
                  </p>
                  <p className="text-[11px] font-body text-[#5C4A3A] italic mt-1 line-clamp-2">{o.terms}</p>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => setEditingOffer({ ...o })} className="text-xs">Edit</Button>
                  <Button size="sm" variant="ghost" onClick={() => deleteOffer(o.id)} className="text-xs text-red-600 hover:bg-red-50"><Trash2 className="h-3 w-3" /></Button>
                </div>
              </div>
            ))}
            {offers.length === 0 && <p className="text-center py-10 italic text-[#7A6F65] text-sm">No discount offers yet. Create your first one.</p>}
          </div>
        </div>
      )}
    </div>
  );
}

function OfferEditor({ offer, setOffer, locations, onSave, onCancel }) {
  const toggleCenter = (id) => {
    const list = offer.applicable_center_ids || [];
    setOffer({ ...offer, applicable_center_ids: list.includes(id) ? list.filter(x => x !== id) : [...list, id] });
  };
  return (
    <Card className="border-[#B8962E]/40 bg-[#FDFBF7]" data-testid="ge-offer-editor">
      <CardHeader><CardTitle className="text-base">{offer.id ? 'Edit Offer' : 'New Offer'}</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <div className="grid sm:grid-cols-2 gap-3">
          <div>
            <Label className="text-xs">Title</Label>
            <Input value={offer.title} onChange={e => setOffer({ ...offer, title: e.target.value })} placeholder="e.g. 10% off Guest Card" data-testid="ge-offer-title" />
          </div>
          <div>
            <Label className="text-xs">Discount %</Label>
            <Input type="number" min={1} max={100} value={offer.discount_pct} onChange={e => setOffer({ ...offer, discount_pct: parseInt(e.target.value) || 0 })} data-testid="ge-offer-pct" />
          </div>
          <div>
            <Label className="text-xs">Valid from</Label>
            <Input type="date" value={offer.valid_from || ''} onChange={e => setOffer({ ...offer, valid_from: e.target.value })} />
          </div>
          <div>
            <Label className="text-xs">Valid till</Label>
            <Input type="date" value={offer.valid_till || ''} onChange={e => setOffer({ ...offer, valid_till: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <Label className="text-xs">Background image URL (optional)</Label>
            <Input value={offer.background_image_url || ''} onChange={e => setOffer({ ...offer, background_image_url: e.target.value })} placeholder="https://... (image URL) or Google Drive share link" />
            <p className="text-[10px] text-foreground/60 mt-1 leading-snug">
              ⚠️ If using Google Drive: open the file → <em>Share</em> → set "<strong>Anyone with the link can view</strong>", then paste the share URL here. We auto-convert it to a direct-image URL. Without public access guests will see only the gold gradient.
            </p>
            {offer.background_image_url && (
              <div className="mt-2 inline-block border border-[#E8DFD0] p-1 bg-white">
                <img
                  src={offer.background_image_url.includes('drive.google.com') || offer.background_image_url.includes('lh3.googleusercontent.com')
                    ? offer.background_image_url.replace(/drive\.google\.com\/file\/d\/([\w-]+).*/, 'https://drive.google.com/thumbnail?id=$1&sz=w400')
                                                  .replace(/drive\.google\.com\/(?:open|uc)\?(?:export=view&)?id=([\w-]+).*/, 'https://drive.google.com/thumbnail?id=$1&sz=w400')
                                                  .replace(/lh3\.googleusercontent\.com\/d\/([\w-]+).*/, 'https://drive.google.com/thumbnail?id=$1&sz=w400')
                    : offer.background_image_url}
                  alt="Preview"
                  className="h-24 w-auto object-cover"
                  onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'block'; }}
                />
                <p className="text-[10px] text-red-600 px-2 py-1 hidden">Preview failed — make sure the file is public.</p>
              </div>
            )}
          </div>
          <div className="sm:col-span-2">
            <Label className="text-xs">Terms & conditions</Label>
            <Textarea value={offer.terms || ''} rows={2} onChange={e => setOffer({ ...offer, terms: e.target.value })} />
          </div>
        </div>
        <div>
          <Label className="text-xs">Applicable centers (leave all unchecked = applies to ALL centers)</Label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 mt-1 max-h-40 overflow-y-auto">
            {locations.map(l => {
              const id = l.center_id || l.id;
              const checked = (offer.applicable_center_ids || []).includes(id);
              return (
                <label key={id} className="flex items-center gap-1.5 text-xs font-body cursor-pointer">
                  <input type="checkbox" checked={checked} onChange={() => toggleCenter(id)} />
                  <span className="truncate">{l.name}</span>
                </label>
              );
            })}
          </div>
        </div>
        <label className="flex items-center gap-2 text-xs">
          <input type="checkbox" checked={!!offer.is_active} onChange={e => setOffer({ ...offer, is_active: e.target.checked })} />
          Active
        </label>
        <div className="flex gap-2">
          <Button size="sm" onClick={() => onSave(offer)} className="bg-green-600 text-white text-xs" data-testid="ge-offer-save">Save Offer</Button>
          <Button size="sm" variant="outline" onClick={onCancel} className="text-xs">Cancel</Button>
        </div>
      </CardContent>
    </Card>
  );
}
