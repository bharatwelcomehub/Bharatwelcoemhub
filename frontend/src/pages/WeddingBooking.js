import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  MapPin, Phone, MessageCircle, Calendar, Users, Clock, Flower2, Sparkles,
  CheckCircle2, AlertTriangle, Mail, Coffee, Utensils, Wine, Loader2, Crown, Soup
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import SEOHead from '@/components/SEOHead';
import { Toran, Tabla, Shehnai, Diya, Mandala, Sparkle } from '@/components/FestiveDecor';

import centersFallback from '@/config/centers.json';

const API = process.env.REACT_APP_BACKEND_URL;

export default function WeddingBooking() {
  const [cfg, setCfg] = useState(null);
  const [centersData, setCentersData] = useState(centersFallback);
  const [blockedDates, setBlockedDates] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [submittedBookingId, setSubmittedBookingId] = useState('');

  // Form state
  const [name, setName] = useState('');
  const [mobile, setMobile] = useState('');
  const [email, setEmail] = useState('');
  const [eventType, setEventType] = useState('');
  const [centerRegion, setCenterRegion] = useState('india');
  const [centerId, setCenterId] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [guestCount, setGuestCount] = useState(30);
  const [timeSlot, setTimeSlot] = useState('');
  const [thaliPackageId, setThaliPackageId] = useState('');
  const [dalOptionId, setDalOptionId] = useState('');
  const [breakfast, setBreakfast] = useState(false);
  const [snacks, setSnacks] = useState(false);
  const [drinksMode, setDrinksMode] = useState(''); // '', 'half_day', 'full_day', 'a_la_carte'
  const [drinksItems, setDrinksItems] = useState([]);
  const [decoration, setDecoration] = useState(false);
  const [decoAgreed, setDecoAgreed] = useState(false);
  const [notes, setNotes] = useState('');

  useEffect(() => {
    axios.get(`${API}/api/wedding/config`).then(r => setCfg(r.data)).catch(() => {});
    axios.get(`${API}/api/centers`).then(r => {
      const d = r.data || {};
      if ((d.india?.length || 0) + (d.australia?.length || 0) > 0) setCentersData(d);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!centerId) { setBlockedDates([]); return; }
    axios.get(`${API}/api/wedding/blocked-dates/${centerId}`)
      .then(r => setBlockedDates(r.data?.dates || []))
      .catch(() => setBlockedDates([]));
  }, [centerId]);

  const allCenters = useMemo(
    () => [...(centersData.india || []), ...(centersData.australia || [])],
    [centersData]
  );
  const filteredCenters = useMemo(
    () => centerRegion === 'india' ? (centersData.india || []) : (centersData.australia || []),
    [centerRegion, centersData]
  );
  const currentCenter = useMemo(() => allCenters.find(c => c.id === centerId), [centerId, allCenters]);
  const isAus = currentCenter?.country === 'Australia';
  const sym = isAus ? '$' : '₹';

  // Selected thali package (if enabled & chosen overrides cfg.thali_price_*)
  const selectedThaliPkg = useMemo(() => {
    if (!cfg?.thali_packages_enabled) return null;
    return (cfg?.thali_packages || []).find(p => p.id === thaliPackageId && p.enabled !== false) || null;
  }, [cfg, thaliPackageId]);

  // Dal/Varan/Amti options filtered by current center country
  const dalOptions = useMemo(() => {
    if (!cfg?.dal_options_enabled) return [];
    const country = currentCenter?.country === 'Australia' ? 'perth' : 'india';
    const flag = country === 'perth' ? 'perth_available' : 'india_available';
    return (cfg?.dal_options || []).filter(d => d.enabled !== false && d[flag] !== false);
  }, [cfg, currentCenter]);

  const selectedDal = useMemo(
    () => (cfg?.dal_options || []).find(d => d.id === dalOptionId) || null,
    [cfg, dalOptionId]
  );

  // Reset dal selection if it becomes unavailable for the selected center
  useEffect(() => {
    if (dalOptionId && dalOptions.length && !dalOptions.find(d => d.id === dalOptionId)) {
      setDalOptionId('');
    }
  }, [dalOptions, dalOptionId]);

  // Live estimate
  const estimate = useMemo(() => {
    if (!cfg) return null;
    const hallC = isAus ? cfg.hall_charges_aud : cfg.hall_charges_inr;
    // If a thali package is selected, use its price; otherwise fall back to flat thali price.
    const thaliP = selectedThaliPkg
      ? (isAus ? selectedThaliPkg.price_aud : selectedThaliPkg.price_inr)
      : (isAus ? cfg.thali_price_aud : cfg.thali_price_inr);
    const thaliLabel = selectedThaliPkg
      ? `${selectedThaliPkg.name} × ${Math.max(parseInt(guestCount || 0) || 0, 0)} guests`
      : `Thali × ${Math.max(parseInt(guestCount || 0) || 0, 0)} guests`;
    const bkfP = isAus ? cfg.breakfast_price_per_person_aud : cfg.breakfast_price_per_person_inr;
    const snkP = isAus ? cfg.snacks_price_per_person_aud : cfg.snacks_price_per_person_inr;
    const drinksHalf = isAus ? cfg.drinks_half_day_aud : cfg.drinks_half_day_inr;
    const drinksFull = isAus ? cfg.drinks_full_day_aud : cfg.drinks_full_day_inr;
    const decoC = isAus ? cfg.decoration_charges_aud : cfg.decoration_charges_inr;

    const g = Math.max(parseInt(guestCount || 0) || 0, 0);
    const items = [];
    items.push({ label: 'Hall Charges', amount: hallC });
    items.push({ label: thaliLabel, amount: thaliP * g });
    if (breakfast) items.push({ label: `Breakfast × ${g}`, amount: bkfP * g });
    if (snacks) items.push({ label: `Snacks × ${g}`, amount: snkP * g });
    if (drinksMode === 'half_day') items.push({ label: 'Drinks — Half Day', amount: drinksHalf });
    if (drinksMode === 'full_day') items.push({ label: 'Drinks — Full Day', amount: drinksFull });
    if (drinksMode === 'a_la_carte') {
      drinksItems.forEach(did => {
        const d = (cfg.drinks_options || []).find(x => x.id === did);
        if (d) items.push({ label: `${d.name} × ${g}`, amount: (isAus ? d.price_aud : d.price_inr) * g });
      });
    }
    if (decoration && decoC > 0) items.push({ label: 'Decoration', amount: decoC });
    const subtotal = items.reduce((s, i) => s + i.amount, 0);
    const gstPct = selectedThaliPkg?.gst_pct ?? cfg.gst_pct ?? 0;
    const gstAmount = Math.round(subtotal * gstPct / 100);
    const total = subtotal + gstAmount;
    return { line_items: items, subtotal, gst_pct: gstPct, gst_amount: gstAmount, total };
  }, [cfg, isAus, guestCount, breakfast, snacks, drinksMode, drinksItems, decoration, selectedThaliPkg]);

  const minDate = useMemo(() => {
    const d = new Date(); d.setDate(d.getDate() + 1);
    return d.toISOString().slice(0, 10);
  }, []);

  const dateIsBlocked = blockedDates.includes(eventDate);

  const buildWhatsApp = (bookingId) => {
    if (!cfg || !currentCenter || !estimate) return '';
    const quoteLink = `${window.location.origin}/quote/${bookingId}`;
    let m = `*PURNABRAMHA — CELEBRATION ENQUIRY*\n`;
    m += `━━━━━━━━━━━━━━━━━━━\n\n`;
    m += `*Enquiry ID:* ${bookingId.slice(0, 8).toUpperCase()}\n`;
    m += `*Customer:* ${name} (${mobile})\n`;
    if (email) m += `*Email:* ${email}\n`;
    m += `*Event:* ${eventType}\n`;
    m += `*Center:* ${currentCenter.displayName}\n`;
    m += `*Date:* ${eventDate}\n`;
    m += `*Guests:* ${guestCount}\n`;
    m += `*Time Slot:* ${timeSlot}\n\n`;
    if (selectedThaliPkg) m += `*Thali Package:* ${selectedThaliPkg.name}\n`;
    if (selectedDal) m += `*Dal / Varan / Amti:* ${selectedDal.name}\n`;
    m += `*Selections:*\n`;
    if (breakfast) m += `• Breakfast (${cfg.breakfast_time})\n`;
    if (snacks) m += `• Snacks (${cfg.snacks_time})\n`;
    if (drinksMode === 'half_day') m += `• Drinks — Half Day\n`;
    if (drinksMode === 'full_day') m += `• Drinks — Full Day\n`;
    if (drinksMode === 'a_la_carte') {
      const names = drinksItems.map(id => (cfg.drinks_options || []).find(x => x.id === id)?.name).filter(Boolean);
      if (names.length) m += `• Drinks (à la carte): ${names.join(', ')}\n`;
    }
    if (decoration) m += `• Decoration ${decoAgreed ? '(rules agreed)' : ''}\n`;
    m += `\n*Estimated Total: ${sym}${estimate.total.toLocaleString('en-IN')}* (incl. ${estimate.gst_pct}% GST)\n`;
    m += `\n*Shareable Quotation:* ${quoteLink}\n`;
    if (notes) m += `\n*Notes:* ${notes}\n`;
    m += `\n_Awaiting confirmation from your team._`;
    return encodeURIComponent(m);
  };

  const submit = async () => {
    if (!name || !mobile || !eventType || !centerId || !eventDate || !timeSlot) {
      toast.error('Please fill all required fields'); return;
    }
    if (cfg?.thali_packages_enabled && (cfg?.thali_packages || []).some(p => p.enabled !== false) && !thaliPackageId) {
      toast.error('Please select a Thali Package'); return;
    }
    if (cfg?.dal_options_enabled && dalOptions.length > 0 && !dalOptionId) {
      toast.error('Please select a Dal / Varan / Amti option'); return;
    }
    if (guestCount < (cfg?.min_guests || 30)) {
      toast.error(`Minimum ${cfg?.min_guests || 30} guests required`); return;
    }
    if (dateIsBlocked) { toast.error('Selected date is unavailable for this center'); return; }
    if (decoration && !decoAgreed) { toast.error('Please agree to decoration rules'); return; }

    setSubmitting(true);
    try {
      const body = {
        name, mobile, email,
        event_type: eventType,
        center_id: centerId, center_name: currentCenter?.displayName || '',
        country: currentCenter?.country || 'India',
        event_date: eventDate, guest_count: guestCount, time_slot: timeSlot,
        thali_package_id: thaliPackageId,
        thali_package_name: selectedThaliPkg?.name || '',
        dal_option_id: dalOptionId,
        dal_option_name: selectedDal?.name || '',
        breakfast, snacks, drinks_mode: drinksMode, drinks_items: drinksItems,
        decoration, decoration_agreed: decoAgreed, notes, estimate
      };
      const res = await axios.post(`${API}/api/wedding/bookings`, body);
      const bookingId = res.data.id;
      setSubmittedBookingId(bookingId);
      toast.success('Enquiry submitted — opening WhatsApp...');
      const msg = buildWhatsApp(bookingId);
      const wa = (currentCenter?.whatsapp || currentCenter?.phone || '').replace(/[^0-9]/g, '');
      if (wa) window.open(`https://wa.me/${wa}?text=${msg}`, '_blank');
    } catch (e) {
      toast.error('Failed to submit. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!cfg) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-[#B8962E]" /></div>;
  if (!cfg.enabled) return (
    <div className="min-h-screen flex items-center justify-center text-center p-6">
      <div>
        <Flower2 className="h-12 w-12 mx-auto text-[#B8962E] mb-3" />
        <p className="font-heading text-2xl text-[#3D2314]">Lagna Booking</p>
        <p className="text-[#7A6F65] mt-2">This service is currently disabled. Please call us.</p>
      </div>
    </div>
  );

  const card = "bg-white border border-[#E8DFD0] p-5 lg:p-6 rounded-none shadow-sm";

  return (
    <div className="min-h-screen bg-[#FDFBF7]">
      <SEOHead page="celebrate" title="Celebrate at Purnabramha — Weddings, Anniversaries, Ceremonies" description="Book traditional Maharashtrian celebrations at Purnabramha — wedding, engagement, haldi, munj, naming, birthday, anniversary. ₹15,000 hall + ₹599/person thali." />

      {/* Hero — festive themed */}
      <section
        className="relative pt-16 pb-12 sm:pt-20 sm:pb-14 lg:pt-24 lg:pb-20 bg-gradient-to-b from-[#3D2314] via-[#4A2A18] to-[#5B3923] text-[#F5DEB3] overflow-hidden"
        data-testid="wedding-hero"
      >
        {/* Subtle radial glow */}
        <div className="absolute inset-0 opacity-30 pointer-events-none bg-[radial-gradient(circle_at_50%_30%,rgba(212,175,55,0.25),transparent_55%)]" />

        {/* Mandala motif corners */}
        <Mandala className="absolute -top-10 -left-10 w-44 h-44 lg:w-64 lg:h-64 pointer-events-none" opacity={0.08} />
        <Mandala className="absolute -bottom-12 -right-10 w-44 h-44 lg:w-64 lg:h-64 pointer-events-none" opacity={0.08} />

        {/* TORAN — hanging marigold garland at the very top */}
        <div className="absolute top-0 left-0 right-0 pointer-events-none z-10">
          <Toran className="opacity-95 drop-shadow-[0_2px_4px_rgba(0,0,0,0.4)]" />
        </div>

        {/* Tabla — bottom-left corner */}
        <motion.div
          className="absolute left-2 bottom-2 sm:left-6 sm:bottom-6 lg:left-12 lg:bottom-8 pointer-events-none z-[5]"
          initial={{ opacity: 0, x: -20, rotate: -8 }}
          animate={{ opacity: 0.95, x: 0, rotate: 0 }}
          transition={{ duration: 0.9, delay: 0.4 }}
        >
          <Tabla size={56} className="drop-shadow-[0_4px_6px_rgba(0,0,0,0.45)] sm:!w-[90px] sm:!h-auto lg:!w-[120px]" />
        </motion.div>

        {/* Shehnai — bottom-right corner */}
        <motion.div
          className="absolute right-2 bottom-1 sm:right-8 sm:bottom-3 lg:right-16 lg:bottom-2 pointer-events-none z-[5]"
          initial={{ opacity: 0, x: 20, rotate: 12 }}
          animate={{ opacity: 0.95, x: 0, rotate: 6 }}
          transition={{ duration: 0.9, delay: 0.5 }}
        >
          <Shehnai size={56} className="drop-shadow-[0_4px_6px_rgba(0,0,0,0.45)] sm:!h-[110px] lg:!h-[140px]" />
        </motion.div>

        {/* Diyas flanking title (mobile-friendly) */}
        <div className="absolute left-2 top-20 sm:left-6 sm:top-24 lg:left-20 lg:top-28 pointer-events-none z-[6]">
          <Diya size={36} className="sm:!w-[48px] sm:!h-[48px] lg:!w-[60px] lg:!h-[60px]" />
        </div>
        <div className="absolute right-2 top-20 sm:right-6 sm:top-24 lg:right-20 lg:top-28 pointer-events-none z-[6]">
          <Diya size={36} className="sm:!w-[48px] sm:!h-[48px] lg:!w-[60px] lg:!h-[60px]" />
        </div>

        {/* Floating sparkles */}
        <Sparkle className="absolute top-24 left-[20%] w-3 h-3 sm:w-4 sm:h-4" delay={0} />
        <Sparkle className="absolute top-32 right-[18%] w-3 h-3 sm:w-4 sm:h-4" delay={0.6} />
        <Sparkle className="absolute top-44 left-[35%] w-2.5 h-2.5 sm:w-3 sm:h-3" delay={1.2} />
        <Sparkle className="absolute top-40 right-[32%] w-2.5 h-2.5 sm:w-3 sm:h-3" delay={1.8} />
        <Sparkle className="absolute bottom-24 left-[28%] w-3 h-3 hidden sm:block" delay={0.4} />
        <Sparkle className="absolute bottom-28 right-[28%] w-3 h-3 hidden sm:block" delay={1.0} />

        {/* Content */}
        <div className="container mx-auto px-4 lg:px-12 relative text-center z-[7] pt-10 sm:pt-12 lg:pt-14">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <Badge className="bg-[#D4AF37]/20 text-[#D4AF37] border border-[#D4AF37]/40 rounded-full px-3 py-1 mb-4 tracking-widest uppercase text-[10px] font-body">
              <Flower2 className="inline h-3 w-3 mr-1" /> Weddings • Birthdays • Anniversaries • Ceremonies
            </Badge>
            <h1 className="font-heading text-3xl sm:text-5xl lg:text-6xl font-light tracking-wide leading-tight">
              Celebrate at <span className="text-[#F5DEB3]">Purnabramha</span>
            </h1>
            <p className="font-heading italic text-[#D4AF37] text-base sm:text-xl mt-2 px-2">
              Lagna • Sakharpuda • Haldi • Munj • Birthday • Anniversary
            </p>
            <p className="font-body text-[#F5DEB3]/85 mt-3 sm:mt-4 max-w-2xl mx-auto text-xs sm:text-sm lg:text-base px-2 leading-relaxed">
              Host every special moment with us — weddings, engagements, haldi, naming ceremonies, birthdays, anniversaries, and family gatherings.
              Authentic Maharashtrian thali, banana-leaf seating, and a touch of cultural elegance.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3 mt-5 sm:mt-6 text-[11px] sm:text-xs font-body">
              <span className="bg-white/10 border border-[#D4AF37]/40 px-3 py-1.5 rounded-full backdrop-blur-sm">Hall {sym}{(isAus ? cfg.hall_charges_aud : cfg.hall_charges_inr).toLocaleString()}</span>
              <span className="bg-white/10 border border-[#D4AF37]/40 px-3 py-1.5 rounded-full backdrop-blur-sm">Thali {sym}{isAus ? cfg.thali_price_aud : cfg.thali_price_inr}/person</span>
              <span className="bg-white/10 border border-[#D4AF37]/40 px-3 py-1.5 rounded-full backdrop-blur-sm">Min {cfg.min_guests} guests</span>
              <span className="bg-white/10 border border-[#D4AF37]/40 px-3 py-1.5 rounded-full backdrop-blur-sm">+ {cfg.gst_pct}% GST</span>
            </div>
          </motion.div>
        </div>
      </section>

      <div className="container mx-auto px-4 lg:px-12 py-8 lg:py-12">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* LEFT: Form */}
          <div className="lg:col-span-2 space-y-5">
            <div className={card} data-testid="wedding-form-contact">
              <h2 className="font-heading text-lg text-[#3D2314] flex items-center gap-2 mb-4"><Users className="h-4 w-4 text-[#B8962E]" /> Your Details</h2>
              <div className="grid sm:grid-cols-2 gap-3">
                <div><Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Name *</Label><Input value={name} onChange={e => setName(e.target.value)} data-testid="wedding-name" /></div>
                <div><Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Mobile *</Label><Input value={mobile} onChange={e => setMobile(e.target.value)} data-testid="wedding-mobile" /></div>
                <div className="sm:col-span-2"><Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Email</Label><Input type="email" value={email} onChange={e => setEmail(e.target.value)} data-testid="wedding-email" /></div>
              </div>
            </div>

            <div className={card} data-testid="wedding-form-event">
              <h2 className="font-heading text-lg text-[#3D2314] flex items-center gap-2 mb-4"><Calendar className="h-4 w-4 text-[#B8962E]" /> Event Details</h2>
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Event Type *</Label>
                  <Select value={eventType} onValueChange={setEventType}>
                    <SelectTrigger data-testid="wedding-event-type"><SelectValue placeholder="Select event" /></SelectTrigger>
                    <SelectContent>
                      {(cfg.event_types || []).map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Region *</Label>
                  <Select value={centerRegion} onValueChange={v => { setCenterRegion(v); setCenterId(''); }}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="india">India</SelectItem>
                      <SelectItem value="australia">Australia</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="sm:col-span-2">
                  <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Preferred Center *</Label>
                  <Select value={centerId} onValueChange={setCenterId}>
                    <SelectTrigger data-testid="wedding-center"><SelectValue placeholder="Select center" /></SelectTrigger>
                    <SelectContent>
                      {filteredCenters.map(c => <SelectItem key={c.id} value={c.id}>{c.displayName || c.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Event Date *</Label>
                  <Input type="date" min={minDate} value={eventDate} onChange={e => setEventDate(e.target.value)} data-testid="wedding-date" />
                  {dateIsBlocked && <p className="text-xs text-red-600 mt-1">⚠ Date unavailable for this center</p>}
                </div>
                <div>
                  <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Guest Count *</Label>
                  <Input type="number" min={cfg.min_guests} value={guestCount} onChange={e => setGuestCount(parseInt(e.target.value) || 0)} data-testid="wedding-guests" />
                  <p className="text-[10px] text-[#7A6F65] mt-1">Min {cfg.min_guests} guests</p>
                </div>
                <div className="sm:col-span-2">
                  <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Preferred Time Slot *</Label>
                  <Input value={timeSlot} onChange={e => setTimeSlot(e.target.value)} placeholder={`Any slot within ${cfg.thali_time_start}–${cfg.thali_time_end}`} data-testid="wedding-slot" />
                  <p className="text-[10px] text-[#7A6F65] mt-1">Thali served between {cfg.thali_time_start} – {cfg.thali_time_end}</p>
                </div>
              </div>
            </div>

            {/* THALI PACKAGE SELECTOR (Celebration-only) — matches Catering card style */}
            {cfg.thali_packages_enabled && (cfg.thali_packages || []).some(p => p.enabled !== false) && (
              <div className={card} data-testid="wedding-form-thali">
                <h2 className="font-heading text-lg text-[#3D2314] flex items-center gap-2 mb-1">
                  <Crown className="h-4 w-4 text-[#B8962E]" /> Choose Thali Package *
                </h2>
                <p className="text-xs text-[#7A6F65] font-body mb-4">Pick a celebration thali. This replaces the standard per-person thali charge.</p>
                <div className="grid md:grid-cols-2 gap-3 sm:gap-4">
                  {(cfg.thali_packages || []).filter(p => p.enabled !== false).map(pkg => {
                    const price = isAus ? pkg.price_aud : pkg.price_inr;
                    const isSelected = thaliPackageId === pkg.id;
                    return (
                      <button
                        key={pkg.id}
                        type="button"
                        onClick={() => setThaliPackageId(pkg.id)}
                        className={`text-left p-4 border transition-all rounded-none ${isSelected ? 'border-[#B8962E] bg-[#B8962E]/5 ring-1 ring-[#B8962E]/30' : 'border-[#E8DFD0] hover:border-[#B8962E]/40 bg-white'}`}
                        data-testid={`thali-package-${pkg.id}`}
                      >
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <div className="min-w-0">
                            <h4 className="font-heading font-medium text-[#2D1810] text-base sm:text-lg leading-snug">{pkg.name}</h4>
                            {pkg.is_popular && <Badge className="bg-[#B8962E] text-white text-[10px] mt-1 rounded-none">Most Popular</Badge>}
                          </div>
                          <span className="font-heading font-medium text-base sm:text-lg text-[#B8962E] whitespace-nowrap">
                            {sym}{(price || 0).toLocaleString('en-IN')}<span className="text-[10px] font-body text-[#7A6F65]">/pp</span>
                          </span>
                        </div>
                        <p className="text-xs sm:text-sm text-[#5C4A3A] font-body leading-relaxed">{pkg.description}</p>
                        {isSelected && (
                          <p className="mt-2 text-[11px] text-[#B8962E] font-body inline-flex items-center gap-1">
                            <CheckCircle2 className="h-3 w-3" /> Selected
                          </p>
                        )}
                      </button>
                    );
                  })}
                </div>

                {/* DAL / VARAN / AMTI selector — shows when a package is selected */}
                {thaliPackageId && cfg.dal_options_enabled && (
                  <div className="mt-5 pt-5 border-t border-[#E8DFD0]">
                    <h3 className="font-heading text-base text-[#3D2314] flex items-center gap-2 mb-1">
                      <Soup className="h-4 w-4 text-[#B8962E]" /> Dal / Varan / Amti *
                    </h3>
                    <p className="text-[11px] text-[#7A6F65] font-body mb-3">
                      Pick one Maharashtrian dal preparation for your thali.
                      {currentCenter?.country === 'Australia' && <span className="ml-1 italic">(Perth center)</span>}
                    </p>
                    {dalOptions.length === 0 ? (
                      <p className="text-xs italic text-[#7A6F65]">No dal options available for this center yet. Please contact us.</p>
                    ) : (
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {dalOptions.map(d => {
                          const isSelected = dalOptionId === d.id;
                          return (
                            <button
                              key={d.id}
                              type="button"
                              onClick={() => setDalOptionId(d.id)}
                              className={`text-xs sm:text-sm px-2 py-2.5 border rounded-none font-body transition-all ${isSelected ? 'border-[#B8962E] bg-[#B8962E]/10 text-[#B8962E] font-medium' : 'border-[#E8DFD0] text-[#5C4A3A] hover:border-[#B8962E]/40 bg-white'}`}
                              data-testid={`dal-option-${d.id}`}
                            >
                              {d.name}
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}


            <div className={card} data-testid="wedding-form-addons">
              <h2 className="font-heading text-lg text-[#3D2314] flex items-center gap-2 mb-4"><Sparkles className="h-4 w-4 text-[#B8962E]" /> Food & Service Add-ons</h2>
              <div className="space-y-3">
                {cfg.breakfast_enabled && (
                  <label className="flex items-start gap-3 p-3 border border-[#E8DFD0] rounded-none cursor-pointer hover:border-[#B8962E]/40">
                    <Checkbox checked={breakfast} onCheckedChange={setBreakfast} data-testid="wedding-breakfast" />
                    <div className="flex-1">
                      <p className="font-body font-medium text-[#2D1810] flex items-center gap-2"><Coffee className="h-4 w-4 text-[#B8962E]" /> Breakfast</p>
                      <p className="text-xs text-[#7A6F65]">Served {cfg.breakfast_time} • {sym}{isAus ? cfg.breakfast_price_per_person_aud : cfg.breakfast_price_per_person_inr}/person</p>
                    </div>
                  </label>
                )}
                {cfg.snacks_enabled && (
                  <label className="flex items-start gap-3 p-3 border border-[#E8DFD0] rounded-none cursor-pointer hover:border-[#B8962E]/40">
                    <Checkbox checked={snacks} onCheckedChange={setSnacks} data-testid="wedding-snacks" />
                    <div className="flex-1">
                      <p className="font-body font-medium text-[#2D1810] flex items-center gap-2"><Utensils className="h-4 w-4 text-[#B8962E]" /> Evening Snacks</p>
                      <p className="text-xs text-[#7A6F65]">Served {cfg.snacks_time} • {sym}{isAus ? cfg.snacks_price_per_person_aud : cfg.snacks_price_per_person_inr}/person</p>
                    </div>
                  </label>
                )}
                {cfg.drinks_enabled && (
                  <div className="p-3 border border-[#E8DFD0] rounded-none">
                    <p className="font-body font-medium text-[#2D1810] flex items-center gap-2"><Wine className="h-4 w-4 text-[#B8962E]" /> Drinks Service</p>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-3">
                      {[
                        { id: 'half_day', label: 'Half Day', price: isAus ? cfg.drinks_half_day_aud : cfg.drinks_half_day_inr },
                        { id: 'full_day', label: 'Full Day', price: isAus ? cfg.drinks_full_day_aud : cfg.drinks_full_day_inr },
                        { id: 'a_la_carte', label: 'À la carte', price: null },
                      ].map(opt => (
                        <button
                          key={opt.id}
                          type="button"
                          onClick={() => setDrinksMode(drinksMode === opt.id ? '' : opt.id)}
                          className={`text-xs px-3 py-2 border ${drinksMode === opt.id ? 'border-[#B8962E] bg-[#B8962E]/10 text-[#B8962E]' : 'border-[#E8DFD0] text-[#5C4A3A]'} rounded-none transition-colors`}
                          data-testid={`wedding-drinks-${opt.id}`}
                        >
                          <p className="font-medium">{opt.label}</p>
                          {opt.price !== null && <p className="text-[10px] text-[#7A6F65]">{sym}{opt.price.toLocaleString()}</p>}
                        </button>
                      ))}
                    </div>
                    {drinksMode === 'a_la_carte' && (
                      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {(cfg.drinks_options || []).map(d => (
                          <label key={d.id} className="flex items-center gap-2 text-xs p-2 border border-[#E8DFD0] cursor-pointer hover:border-[#B8962E]/40">
                            <Checkbox
                              checked={drinksItems.includes(d.id)}
                              onCheckedChange={(v) => setDrinksItems(p => v ? [...p, d.id] : p.filter(x => x !== d.id))}
                              data-testid={`wedding-drink-${d.id}`}
                            />
                            <span className="flex-1 text-[#2D1810]">{d.name}</span>
                            <span className="text-[#B8962E] font-body">{sym}{isAus ? d.price_aud : d.price_inr}</span>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                {cfg.decoration_enabled && (
                  <label className="flex items-start gap-3 p-3 border border-[#E8DFD0] rounded-none cursor-pointer hover:border-[#B8962E]/40">
                    <Checkbox checked={decoration} onCheckedChange={setDecoration} data-testid="wedding-decoration" />
                    <div className="flex-1">
                      <p className="font-body font-medium text-[#2D1810] flex items-center gap-2"><Flower2 className="h-4 w-4 text-[#B8962E]" /> Decoration</p>
                      <p className="text-xs text-[#7A6F65]">{(isAus ? cfg.decoration_charges_aud : cfg.decoration_charges_inr) > 0 ? `${sym}${(isAus ? cfg.decoration_charges_aud : cfg.decoration_charges_inr).toLocaleString()} (base)` : 'Pricing on enquiry — bring your own decorator allowed.'}</p>
                    </div>
                  </label>
                )}
              </div>
            </div>

            {decoration && (
              <div className="bg-[#FFF8E7] border-2 border-[#D4AF37]/40 p-5 rounded-none" data-testid="wedding-decoration-rules">
                <h3 className="font-heading text-base text-[#3D2314] flex items-center gap-2 mb-3"><AlertTriangle className="h-4 w-4 text-[#B8962E]" /> Decoration & Property Safety Rules</h3>
                <ul className="text-xs font-body text-[#5C4A3A] space-y-1 list-disc pl-5 mb-3">
                  {(cfg.decoration_rules || []).map((r, i) => <li key={i}>{r}</li>)}
                </ul>
                <label className="flex items-start gap-2 cursor-pointer">
                  <Checkbox checked={decoAgreed} onCheckedChange={setDecoAgreed} data-testid="wedding-deco-agree" />
                  <span className="text-xs font-body text-[#3D2314]"><strong>I Agree</strong> to Decoration & Property Safety Rules</span>
                </label>
              </div>
            )}

            <div className={card}>
              <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Additional Notes</Label>
              <Textarea value={notes} onChange={e => setNotes(e.target.value)} placeholder="Special preferences, allergies, cultural rituals, etc." className="mt-1" data-testid="wedding-notes" />
            </div>
          </div>

          {/* RIGHT: Live Estimate */}
          <div className="lg:col-span-1">
            <div className="lg:sticky lg:top-24 space-y-4">
              <div className={card} data-testid="wedding-estimate">
                <h3 className="font-heading text-lg text-[#3D2314] flex items-center gap-2 mb-3"><Sparkles className="h-4 w-4 text-[#B8962E]" /> Estimate</h3>
                {(selectedThaliPkg || selectedDal || currentCenter || eventType) && (
                  <div className="mb-3 pb-3 border-b border-[#E8DFD0] space-y-1 text-[11px] font-body">
                    {currentCenter && (
                      <div className="flex justify-between gap-2 text-[#5C4A3A]"><span>Center</span><span className="text-[#2D1810] text-right truncate">{currentCenter.displayName || currentCenter.name}</span></div>
                    )}
                    {eventType && (
                      <div className="flex justify-between gap-2 text-[#5C4A3A]"><span>Event</span><span className="text-[#2D1810] text-right truncate">{eventType}</span></div>
                    )}
                    {selectedThaliPkg && (
                      <div className="flex justify-between gap-2 text-[#5C4A3A]"><span>Thali Package</span><span className="text-[#B8962E] font-medium text-right">{selectedThaliPkg.name}</span></div>
                    )}
                    {selectedDal && (
                      <div className="flex justify-between gap-2 text-[#5C4A3A]"><span>Dal / Varan</span><span className="text-[#2D1810] text-right">{selectedDal.name}</span></div>
                    )}
                    <div className="flex justify-between gap-2 text-[#5C4A3A]"><span>Guests</span><span className="text-[#2D1810]">{guestCount}</span></div>
                  </div>
                )}
                {estimate && (
                  <div className="space-y-1.5 text-xs font-body">
                    {estimate.line_items.map((it, i) => (
                      <div key={i} className="flex justify-between text-[#5C4A3A]">
                        <span className="flex-1 pr-2">{it.label}</span>
                        <span className="text-[#2D1810]">{sym}{it.amount.toLocaleString('en-IN')}</span>
                      </div>
                    ))}
                    <div className="flex justify-between border-t border-[#E8DFD0] pt-2 mt-2">
                      <span>Subtotal</span><span className="text-[#2D1810]">{sym}{estimate.subtotal.toLocaleString('en-IN')}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>GST ({estimate.gst_pct}%)</span><span className="text-[#2D1810]">{sym}{estimate.gst_amount.toLocaleString('en-IN')}</span>
                    </div>
                    <div className="flex justify-between border-t-2 border-[#B8962E] pt-2 mt-2 font-heading text-base">
                      <span className="text-[#3D2314]">Total</span>
                      <span className="text-[#B8962E]" data-testid="wedding-total">{sym}{estimate.total.toLocaleString('en-IN')}</span>
                    </div>
                  </div>
                )}
                <p className="text-[10px] text-[#7A6F65] italic mt-3">Estimate is indicative. Final quotation will be shared by our team.</p>
              </div>

              <Button
                onClick={submit}
                disabled={submitting}
                className="w-full bg-green-600 hover:bg-green-700 text-white py-5 rounded-none font-semibold tracking-wider"
                data-testid="wedding-submit"
              >
                {submitting ? <Loader2 className="h-5 w-5 mr-2 animate-spin" /> : <MessageCircle className="h-5 w-5 mr-2" />}
                {submitting ? 'Sending...' : 'Send Enquiry via WhatsApp'}
              </Button>

              {submittedBookingId && (
                <div className="bg-[#F0FFF0] border-2 border-green-300 p-4 text-center space-y-2" data-testid="wedding-share-callout">
                  <p className="text-sm font-heading text-green-800">Enquiry sent! Share with your family for approval:</p>
                  <a
                    href={`/quote/${submittedBookingId}`}
                    target="_blank"
                    rel="noreferrer"
                    className="block bg-white border border-green-400 py-2.5 text-sm font-body text-green-700 hover:bg-green-50"
                    data-testid="wedding-share-link"
                  >
                    🔗 Open Shareable Quotation
                  </a>
                  <button
                    onClick={async () => {
                      const url = `${window.location.origin}/quote/${submittedBookingId}`;
                      try { await navigator.clipboard.writeText(url); toast.success('Link copied!'); } catch { toast.error('Could not copy'); }
                    }}
                    className="w-full text-xs text-green-700 underline font-body"
                    data-testid="wedding-share-copy"
                  >
                    Copy link to clipboard
                  </button>
                </div>
              )}

              {currentCenter?.phone && (
                <a href={`tel:${currentCenter.phone}`} className="block w-full text-center bg-white border border-[#E8DFD0] py-3 text-sm font-body text-[#5C4A3A] hover:border-[#B8962E]/40">
                  <Phone className="inline h-4 w-4 mr-1 text-[#B8962E]" /> Call {currentCenter.displayName}
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
