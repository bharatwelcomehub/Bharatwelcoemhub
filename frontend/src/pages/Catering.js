import { useState, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Calendar, MapPin, Phone, MessageCircle, Users, Star, AlertCircle, ChefHat, PartyPopper, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { toast } from 'sonner';
import axios from 'axios';

import centersFallback from '@/config/centers.json';
import cateringFallback from '@/config/catering-packages.json';
import CateringVsCelebrate from '@/components/CateringVsCelebrate';
import bookingRules from '@/config/booking-rules.json';

const API = process.env.REACT_APP_BACKEND_URL;

const Catering = () => {
  const [selectedRegion, setSelectedRegion] = useState('');
  const [selectedCenter, setSelectedCenter] = useState('');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [needsDelivery, setNeedsDelivery] = useState(false);
  const [eventDate, setEventDate] = useState('');
  const [eventTime, setEventTime] = useState('');
  const [guestCount, setGuestCount] = useState('20');
  const [celebrationType, setCelebrationType] = useState('');
  const [selectedPackage, setSelectedPackage] = useState('');
  const [menuSelections, setMenuSelections] = useState({});
  const [showReview, setShowReview] = useState(false);
  const [dbMenuItems, setDbMenuItems] = useState([]);
  const [needsCrockery, setNeedsCrockery] = useState(false);
  const [crockeryHours, setCrockeryHours] = useState(1);
  const [needsStaff, setNeedsStaff] = useState(false);
  const [staffCount, setStaffCount] = useState(2);
  const [staffHours, setStaffHours] = useState(2);

  // Live DB-backed data (with static fallback)
  const [centersData, setCentersData] = useState(centersFallback);
  const [dbPackages, setDbPackages] = useState([]); // raw array of all packages (both regions combined)
  const [dbCateringItems, setDbCateringItems] = useState([]); // raw array of all menu items

  useEffect(() => {
    const fetchAll = async () => {
      try { const r = await axios.get(`${API}/api/menu`); setDbMenuItems(r.data); } catch {}
      try {
        const r = await axios.get(`${API}/api/centers`);
        const d = r.data || {};
        if ((d.india?.length || 0) + (d.australia?.length || 0) > 0) setCentersData(d);
      } catch {}
      // /api/catering-packages returns { packages: {india:[], australia:[]}, menuOptions: {cat: [items]} }
      try {
        const r = await axios.get(`${API}/api/catering-packages`);
        const pkgs = r.data?.packages || {};
        // The backend currently returns identical arrays for india/australia; dedupe by id and rely on price fields
        const combined = [...(pkgs.india || []), ...(pkgs.australia || [])];
        const dedup = Array.from(new Map(combined.map(p => [p.id, p])).values());
        setDbPackages(dedup);
        // Flatten menuOptions dict into a list of items with category
        const mo = r.data?.menuOptions || {};
        const items = [];
        Object.entries(mo).forEach(([cat, arr]) => {
          (arr || []).forEach(it => items.push({ ...it, category: cat }));
        });
        setDbCateringItems(items);
      } catch {}
    };
    fetchAll();
  }, []);

  const allCenters = useMemo(() => [...(centersData.india || []), ...(centersData.australia || [])], [centersData]);
  const filteredCenters = useMemo(() => { if (!selectedRegion) return []; return selectedRegion === 'india' ? (centersData.india || []) : (centersData.australia || []); }, [selectedRegion, centersData]);
  const currentCenter = useMemo(() => allCenters.find(c => c.id === selectedCenter), [selectedCenter, allCenters]);

  const isAustralia = currentCenter?.country === 'Australia';
  const currencySymbol = isAustralia ? '$' : '₹';

  // Transform DB packages into per-region shape that the UI expects (id, name, description, pricePerPerson, isPopular, requirements)
  const packages = useMemo(() => {
    if (dbPackages && dbPackages.length > 0) {
      const filtered = dbPackages
        .filter(p => p.is_active !== false)
        .filter(p => isAustralia ? (p.price_per_person_aud || 0) > 0 : (p.price_per_person_inr || 0) > 0)
        .sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
        .map(p => ({
          id: p.id,
          name: p.name,
          description: p.description || '',
          pricePerPerson: isAustralia ? (p.price_per_person_aud || 0) : (p.price_per_person_inr || 0),
          isPopular: !!p.is_popular,
          requirements: p.requirements || { starters: 0, mains: 0, special: 0, roti: 0, rice: 0, side: 0, dessert: 0, drink: 0, chutney: 0 },
        }));
      if (filtered.length > 0) return filtered;
    }
    // Fallback to static JSON
    return isAustralia ? cateringFallback.packages.australia : cateringFallback.packages.india;
  }, [dbPackages, isAustralia]);

  // Transform DB menu items (category: starters/specialBhaji/simpleBhaji/desserts/roti/rice/drinks/sides/chutney)
  // into the dictionary shape that the UI expects.
  const menuOptions = useMemo(() => {
    if (dbCateringItems && dbCateringItems.length > 0) {
      const byCat = { starters: [], specialBhaji: [], simpleBhaji: [], desserts: [], roti: [], rice: [], drinks: [], sides: [], chutney: [] };
      dbCateringItems.forEach(it => {
        if (it.is_available === false) return;
        const cat = it.category;
        if (byCat[cat]) {
          byCat[cat].push({ id: it.id, name: it.name, isVeg: it.is_veg ?? true, description: it.description || '', image_url: it.image_url || '' });
        }
      });
      // Only use DB data if at least one category is populated
      const anyPopulated = Object.values(byCat).some(arr => arr.length > 0);
      if (anyPopulated) return byCat;
    }
    return cateringFallback.menuOptions;
  }, [dbCateringItems]);

  const addonPricing = { crockery: { india: 3000, australia: 200 }, staff: { india: 300, australia: 50 } };
  const currentPackage = packages.find(p => p.id === selectedPackage);

  const getMinDate = () => { const d = new Date(); d.setDate(d.getDate() + bookingRules.catering.minAdvanceDays); return d.toISOString().split('T')[0]; };
  const getMaxDate = () => { const d = new Date(); d.setDate(d.getDate() + bookingRules.catering.maxAdvanceDays); return d.toISOString().split('T')[0]; };
  const formatPrice = (price) => `${currencySymbol}${price.toFixed(2)}`;

  const crockeryTotal = useMemo(() => { if (!needsCrockery) return 0; return (isAustralia ? addonPricing.crockery.australia : addonPricing.crockery.india) * crockeryHours; }, [needsCrockery, crockeryHours, isAustralia]);
  const staffTotal = useMemo(() => { if (!needsStaff) return 0; return (isAustralia ? addonPricing.staff.australia : addonPricing.staff.india) * staffCount * staffHours; }, [needsStaff, staffCount, staffHours, isAustralia]);
  const foodTotal = useMemo(() => { if (!currentPackage || !guestCount) return 0; return currentPackage.pricePerPerson * parseInt(guestCount); }, [currentPackage, guestCount]);
  const estimatedTotal = useMemo(() => foodTotal + crockeryTotal + staffTotal, [foodTotal, crockeryTotal, staffTotal]);

  const toggleSelection = (category, itemId) => {
    setMenuSelections(prev => {
      const current = prev[category] || [];
      if (current.includes(itemId)) return { ...prev, [category]: current.filter(id => id !== itemId) };
      const requirementKeyMap = { desserts: 'dessert', drinks: 'drink', sides: 'side' };
      const reqKey = requirementKeyMap[category] || category;
      const maxAllowed = currentPackage?.requirements[reqKey] || 0;
      if (current.length >= maxAllowed) { toast.error(`Maximum ${maxAllowed} ${category} allowed for this package`); return prev; }
      return { ...prev, [category]: [...current, itemId] };
    });
  };
  const getSelectedCount = (category) => (menuSelections[category] || []).length;
  const generateGoogleMapsLink = () => { if (!address) return ''; return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`; };

  const validateSelections = () => {
    if (!currentPackage) return { valid: false, message: 'Please select a package' };
    const requirements = currentPackage.requirements;
    const errors = [];
    const categoryKeyMap = { dessert: 'desserts', drink: 'drinks', side: 'sides' };
    Object.entries(requirements).forEach(([reqKey, required]) => {
      if (required > 0) { const category = categoryKeyMap[reqKey] || reqKey; const selected = getSelectedCount(category); if (selected < required) errors.push(`${category}: ${selected}/${required}`); }
    });
    return errors.length > 0 ? { valid: false, message: `Please complete menu selection: ${errors.join(', ')}` } : { valid: true };
  };

  const generateWhatsAppMessage = () => {
    let message = `🪔 *PURNABRAMHA CATERING* 🪔\n━━━━━━━━━━━━━━━━\n\n`;
    message += `👤 *${name}* | 📞 ${phone}\n📍 ${currentCenter?.displayName}\n🏠 ${address}\n`;
    if (needsDelivery) message += `🚚 Delivery Required | 📍 ${generateGoogleMapsLink()}\n`;
    message += `\n📅 ${eventDate} ⏰ ${eventTime}\n👥 ${guestCount} guests | 🎉 ${bookingRules.catering.celebrationTypes.find(c => c.id === celebrationType)?.label || '-'}\n`;
    message += `\n🍽️ *${currentPackage?.name}* — ${formatPrice(currentPackage?.pricePerPerson || 0)}/person\n━━━━━━━━━━━━━━━━\n`;
    const emojis = { starters: '🥟', mains: '🍛', special: '⭐', desserts: '🍮', roti: '🫓', rice: '🍚', drinks: '🥤', sides: '🥗', chutney: '🌶️' };
    Object.entries(menuSelections).forEach(([category, items]) => {
      if (items.length > 0) {
        const opts = menuOptions[category === 'mains' ? 'simpleBhaji' : category === 'special' ? 'specialBhaji' : category];
        const names = items.map(id => opts?.find(o => o.id === id)?.name || id);
        message += `${emojis[category] || '•'} ${names.join(', ')}\n`;
      }
    });
    if (needsCrockery || needsStaff) {
      message += `\n🛎️ *Add-ons:*\n`;
      if (needsCrockery) message += `🍽️ Crockery ${crockeryHours}hr = ${formatPrice(crockeryTotal)}\n`;
      if (needsStaff) message += `👨‍🍳 Staff ${staffCount}×${staffHours}hr = ${formatPrice(staffTotal)}\n`;
    }
    message += `\n━━━━━━━━━━━━━━━━\n💰 Food: ${formatPrice(foodTotal)}\n`;
    if (needsCrockery) message += `🍽️ Crockery: ${formatPrice(crockeryTotal)}\n`;
    if (needsStaff) message += `👨‍🍳 Staff: ${formatPrice(staffTotal)}\n`;
    message += `\n✨ *TOTAL: ${formatPrice(estimatedTotal)}* ✨\n\n_Final quote after consultation_`;
    return encodeURIComponent(message);
  };

  const handleSubmit = () => {
    if (!selectedCenter || !name || !phone || !address || !eventDate || !eventTime || !guestCount || !selectedPackage) { toast.error('Please fill all required fields'); return; }
    if (parseInt(guestCount) < bookingRules.catering.minGuests) { toast.error(`Minimum ${bookingRules.catering.minGuests} guests required for catering`); return; }
    const v = validateSelections(); if (!v.valid) { toast.error(v.message); return; }
    setShowReview(true);
  };

  const confirmBooking = () => {
    const message = generateWhatsAppMessage();
    const whatsappNumber = currentCenter?.whatsapp.replace(/[^0-9]/g, '');
    window.open(`https://wa.me/${whatsappNumber}?text=${message}`, '_blank');
    toast.success('Redirecting to WhatsApp...');
  };

  const inputCls = "bg-white border-[#E8DFD0] text-[#2D1810] rounded-none placeholder:text-[#7A6F65]/50 focus-visible:ring-[#B8962E]";
  const labelCls = "text-[#5C4A3A] font-body text-xs tracking-wider uppercase";

  return (
    <div className="min-h-screen bg-[#FDFBF7]">
      {/* Hero */}
      <section className="relative py-16 border-b border-[#E8DFD0]">
        <div className="absolute inset-0 bg-[#F8F5F0]" />
        <div className="relative container mx-auto px-6 lg:px-12">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center max-w-3xl mx-auto">
            <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-4">Events & Celebrations</p>
            <h1 className="font-heading text-5xl md:text-6xl font-medium text-[#2D1810] mb-4 tracking-tight" data-testid="catering-title">
              Catering <span className="text-gold-shimmer">Services</span>
            </h1>
            <p className="text-lg text-[#5C4A3A] font-body">Authentic Maharashtrian cuisine for your special occasions</p>
            <div className="mt-4 flex items-center justify-center gap-4 text-[#B8962E]/60 text-sm font-body flex-wrap">
              <span className="flex items-center gap-1"><Users className="h-4 w-4" /> Min {bookingRules.catering.minGuests} guests</span>
              <span className="flex items-center gap-1"><Calendar className="h-4 w-4" /> Book {bookingRules.catering.minAdvanceDays}+ days ahead</span>
            </div>
          </motion.div>
        </div>
      </section>

      <CateringVsCelebrate current="catering" />

      <div className="container mx-auto px-6 lg:px-12 py-10">
        {!showReview ? (
          <div className="grid lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-6">
              {/* Step 1 */}
              <div className="pearl-surface overflow-hidden">
                <div className="bg-[#F8F5F0] border-b border-[#E8DFD0] p-4"><h3 className="flex items-center gap-2 text-[#B8962E] font-heading font-medium"><PartyPopper className="h-5 w-5" /> Step 1: Event & Contact Details</h3></div>
                <div className="p-6 space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div><Label className={labelCls}>Region *</Label><Select value={selectedRegion} onValueChange={(v) => { setSelectedRegion(v); setSelectedCenter(''); setSelectedPackage(''); setMenuSelections({}); }}><SelectTrigger className={inputCls} data-testid="catering-region-select"><SelectValue placeholder="Select Region" /></SelectTrigger><SelectContent className="bg-white border-[#E8DFD0]"><SelectItem value="india">India</SelectItem><SelectItem value="australia">Australia</SelectItem></SelectContent></Select></div>
                    <div><Label className={labelCls}>Center *</Label><Select value={selectedCenter} onValueChange={setSelectedCenter} disabled={!selectedRegion}><SelectTrigger className={inputCls} data-testid="catering-center-select"><SelectValue placeholder="Select Center" /></SelectTrigger><SelectContent className="bg-white border-[#E8DFD0]">{filteredCenters.map(c => <SelectItem key={c.id} value={c.id}>{c.displayName}</SelectItem>)}</SelectContent></Select></div>
                  </div>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div><Label className={labelCls}>Your Name *</Label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name" className={inputCls} data-testid="catering-name" /></div>
                    <div><Label className={labelCls}>Phone *</Label><Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone number" className={inputCls} data-testid="catering-phone" /></div>
                  </div>
                  <div>
                    <Label className={labelCls}>Event Address *</Label>
                    <Input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Full address of the venue" className={inputCls} data-testid="catering-address" />
                    {address && <a href={generateGoogleMapsLink()} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm text-[#B8962E]/60 mt-1 hover:text-[#B8962E] font-body"><ExternalLink className="h-3 w-3" /> Open in Google Maps</a>}
                  </div>
                  <div className="flex items-center gap-2">
                    <Checkbox id="delivery" checked={needsDelivery} onCheckedChange={setNeedsDelivery} className="border-[#E8DFD0] data-[state=checked]:bg-[#B8962E] data-[state=checked]:border-[#B8962E]" />
                    <label htmlFor="delivery" className="text-sm cursor-pointer text-[#5C4A3A] font-body">Delivery Required (to the event venue)</label>
                  </div>
                  <div className="grid md:grid-cols-3 gap-4">
                    <div><Label className={labelCls}>Event Date *</Label><Input type="date" value={eventDate} onChange={(e) => setEventDate(e.target.value)} min={getMinDate()} max={getMaxDate()} className={inputCls} data-testid="catering-date" /></div>
                    <div><Label className={labelCls}>Event Time *</Label><Input type="time" value={eventTime} onChange={(e) => setEventTime(e.target.value)} className={inputCls} data-testid="catering-time" /></div>
                    <div><Label className={labelCls}>Guests *</Label><Input type="number" value={guestCount} onChange={(e) => setGuestCount(e.target.value)} min={bookingRules.catering.minGuests} className={inputCls} data-testid="catering-guests" /></div>
                  </div>
                  <div><Label className={labelCls}>Celebration Type</Label><Select value={celebrationType} onValueChange={setCelebrationType}><SelectTrigger className={inputCls} data-testid="catering-celebration-select"><SelectValue placeholder="Select type" /></SelectTrigger><SelectContent className="bg-white border-[#E8DFD0]">{bookingRules.catering.celebrationTypes.map(t => <SelectItem key={t.id} value={t.id}>{t.label}</SelectItem>)}</SelectContent></Select></div>
                  {parseInt(guestCount) >= 50 && (
                    <div className="p-3 bg-[#B8962E]/10 border border-[#B8962E]/20 flex items-center gap-2">
                      <Star className="h-5 w-5 text-[#B8962E]" />
                      <span className="text-sm text-[#B8962E] font-body">For larger gatherings we recommend: <strong>Royal Feast (Option 4)</strong></span>
                    </div>
                  )}
                </div>
              </div>

              {/* Step 2 */}
              <div className="pearl-surface overflow-hidden">
                <div className="bg-[#F8F5F0] border-b border-[#E8DFD0] p-4"><h3 className="flex items-center gap-2 text-[#B8962E] font-heading font-medium"><ChefHat className="h-5 w-5" /> Step 2: Choose Package</h3></div>
                <div className="p-6">
                  <RadioGroup value={selectedPackage} onValueChange={(v) => { setSelectedPackage(v); setMenuSelections({}); }}>
                    <div className="grid md:grid-cols-2 gap-4">
                      {packages.map(pkg => (
                        <div key={pkg.id}>
                          <RadioGroupItem value={pkg.id} id={pkg.id} className="peer sr-only" />
                          <label htmlFor={pkg.id}
                            className={`block p-4 border cursor-pointer transition-all ${selectedPackage === pkg.id ? 'border-[#B8962E] bg-[#B8962E]/5' : 'border-[#E8DFD0] hover:border-[#B8962E]/30'}`}
                            data-testid={`package-${pkg.id}`}>
                            <div className="flex items-start justify-between mb-2">
                              <div>
                                <h4 className="font-heading font-medium text-[#2D1810]">{pkg.name}</h4>
                                {pkg.isPopular && <Badge className="bg-[#B8962E] text-white text-[10px] mt-1">Most Popular</Badge>}
                              </div>
                              <span className="font-heading font-medium text-lg text-[#B8962E]">{formatPrice(pkg.pricePerPerson)}/pp</span>
                            </div>
                            <p className="text-sm text-[#5C4A3A] font-body">{pkg.description}</p>
                            <div className="mt-2 text-xs text-[#7A6F65] font-body">
                              {Object.entries(pkg.requirements).filter(([_, v]) => v > 0).map(([k, v]) => `${v} ${k}`).join(' • ')}
                            </div>
                          </label>
                        </div>
                      ))}
                    </div>
                  </RadioGroup>
                </div>
              </div>

              {/* Step 3 */}
              {currentPackage && (
                <div className="pearl-surface overflow-hidden">
                  <div className="bg-[#F8F5F0] border-b border-[#E8DFD0] p-4">
                    <h3 className="flex items-center gap-2 text-[#B8962E] font-heading font-medium"><ChefHat className="h-5 w-5" /> Step 3: Menu Selection</h3>
                    <p className="text-xs text-[#7A6F65] mt-1 font-body">Select items based on your package requirements</p>
                  </div>
                  <div className="p-6 space-y-6">
                    {currentPackage.requirements.starters > 0 && <MenuSection title="Starters (2 pc each)" category="starters" options={menuOptions.starters} selections={menuSelections} required={currentPackage.requirements.starters} toggleSelection={toggleSelection} getSelectedCount={getSelectedCount} />}
                    {currentPackage.requirements.special > 0 && <MenuSection title="Special Bhaji (80 gms)" category="special" options={menuOptions.specialBhaji} selections={menuSelections} required={currentPackage.requirements.special} toggleSelection={toggleSelection} getSelectedCount={getSelectedCount} />}
                    {currentPackage.requirements.mains > 0 && <MenuSection title="Simple Bhaji (80 gms)" category="mains" options={menuOptions.simpleBhaji} selections={menuSelections} required={currentPackage.requirements.mains} toggleSelection={toggleSelection} getSelectedCount={getSelectedCount} />}
                    {currentPackage.requirements.dessert > 0 && <MenuSection title="Desserts (80 gms)" category="desserts" options={menuOptions.desserts} selections={menuSelections} required={currentPackage.requirements.dessert} toggleSelection={toggleSelection} getSelectedCount={getSelectedCount} />}
                    {currentPackage.requirements.roti > 0 && <MenuSection title="Roti / Bhakari" category="roti" options={menuOptions.roti} selections={menuSelections} required={currentPackage.requirements.roti} toggleSelection={toggleSelection} getSelectedCount={getSelectedCount} />}
                    {currentPackage.requirements.rice > 0 && <MenuSection title="Rice (150 gms)" category="rice" options={menuOptions.rice} selections={menuSelections} required={currentPackage.requirements.rice} toggleSelection={toggleSelection} getSelectedCount={getSelectedCount} />}
                    {currentPackage.requirements.drink > 0 && <MenuSection title="Drinks (200ml)" category="drinks" options={menuOptions.drinks} selections={menuSelections} required={currentPackage.requirements.drink} toggleSelection={toggleSelection} getSelectedCount={getSelectedCount} />}
                    {currentPackage.requirements.side > 0 && <MenuSection title="Sides" category="sides" options={menuOptions.sides} selections={menuSelections} required={currentPackage.requirements.side} toggleSelection={toggleSelection} getSelectedCount={getSelectedCount} />}
                    {currentPackage.requirements.chutney > 0 && <MenuSection title="Chutney" category="chutney" options={menuOptions.chutney} selections={menuSelections} required={currentPackage.requirements.chutney} toggleSelection={toggleSelection} getSelectedCount={getSelectedCount} />}
                  </div>
                </div>
              )}

              {/* Step 4 Addons */}
              {currentPackage && (
                <div className="pearl-surface overflow-hidden">
                  <div className="bg-[#F8F5F0] border-b border-[#E8DFD0] p-4">
                    <h3 className="text-[#B8962E] font-heading font-medium">Step 4: Addon Services (Optional)</h3>
                    <p className="text-xs text-[#7A6F65] mt-1 font-body">Need crockery, cutlery, or service staff? We've got you covered!</p>
                  </div>
                  <div className="p-6 space-y-6">
                    <div className="p-4 border border-[#E8DFD0]">
                      <div className="flex items-start gap-3 mb-4">
                        <Checkbox id="crockery" checked={needsCrockery} onCheckedChange={setNeedsCrockery} className="border-[#E8DFD0] data-[state=checked]:bg-[#B8962E] data-[state=checked]:border-[#B8962E]" data-testid="crockery-checkbox" />
                        <div className="flex-1">
                          <label htmlFor="crockery" className="font-body font-semibold cursor-pointer text-[#2D1810]">Crockery & Cutlery Rental</label>
                          <p className="text-sm text-[#5C4A3A] mt-1 font-body">Plates, Bowls, Spoons, Serving Dishes for all guests</p>
                          <p className="text-sm font-medium text-[#B8962E] mt-1 font-body">{isAustralia ? '$200' : '₹3,000'} per hour</p>
                          <p className="text-xs text-[#7A6F65] mt-1 font-body">Return by 9 AM next morning | No cleaning needed | Closed Tuesdays</p>
                        </div>
                      </div>
                      {needsCrockery && (
                        <div className="ml-7 p-3 bg-[#F8F5F0] border border-[#E8DFD0]">
                          <Label className="text-sm text-[#5C4A3A] font-body">Number of Hours</Label>
                          <div className="flex items-center gap-3 mt-2">
                            <Button variant="outline" size="icon" onClick={() => setCrockeryHours(Math.max(1, crockeryHours - 1))} className="h-8 w-8 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] rounded-none"><span className="text-lg">-</span></Button>
                            <span className="text-xl font-heading font-medium w-12 text-center text-[#2D1810]">{crockeryHours}</span>
                            <Button variant="outline" size="icon" onClick={() => setCrockeryHours(crockeryHours + 1)} className="h-8 w-8 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] rounded-none"><span className="text-lg">+</span></Button>
                            <span className="text-sm text-[#5C4A3A] ml-2 font-body">= <strong className="text-[#B8962E]">{formatPrice(crockeryTotal)}</strong></span>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="p-4 border border-[#E8DFD0]">
                      <div className="flex items-start gap-3 mb-4">
                        <Checkbox id="staff" checked={needsStaff} onCheckedChange={setNeedsStaff} className="border-[#E8DFD0] data-[state=checked]:bg-[#B8962E] data-[state=checked]:border-[#B8962E]" data-testid="staff-checkbox" />
                        <div className="flex-1">
                          <label htmlFor="staff" className="font-body font-semibold cursor-pointer text-[#2D1810]">Service Staff</label>
                          <p className="text-sm text-[#5C4A3A] mt-1 font-body">Professional servers to help with your event</p>
                          <p className="text-sm font-medium text-[#B8962E] mt-1 font-body">{isAustralia ? '$50 per person/hour' : '₹300 per person/hour'}</p>
                        </div>
                      </div>
                      {needsStaff && (
                        <div className="ml-7 p-3 bg-[#F8F5F0] border border-[#E8DFD0] space-y-3">
                          <div>
                            <Label className="text-sm text-[#5C4A3A] font-body">Number of Staff</Label>
                            <div className="flex items-center gap-3 mt-2">
                              <Button variant="outline" size="icon" onClick={() => setStaffCount(Math.max(1, staffCount - 1))} className="h-8 w-8 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] rounded-none"><span className="text-lg">-</span></Button>
                              <span className="text-xl font-heading font-medium w-12 text-center text-[#2D1810]">{staffCount}</span>
                              <Button variant="outline" size="icon" onClick={() => setStaffCount(staffCount + 1)} className="h-8 w-8 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] rounded-none"><span className="text-lg">+</span></Button>
                              <span className="text-sm text-[#5C4A3A] font-body">person(s)</span>
                            </div>
                          </div>
                          <div>
                            <Label className="text-sm text-[#5C4A3A] font-body">Number of Hours</Label>
                            <div className="flex items-center gap-3 mt-2">
                              <Button variant="outline" size="icon" onClick={() => setStaffHours(Math.max(1, staffHours - 1))} className="h-8 w-8 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] rounded-none"><span className="text-lg">-</span></Button>
                              <span className="text-xl font-heading font-medium w-12 text-center text-[#2D1810]">{staffHours}</span>
                              <Button variant="outline" size="icon" onClick={() => setStaffHours(staffHours + 1)} className="h-8 w-8 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] rounded-none"><span className="text-lg">+</span></Button>
                              <span className="text-sm text-[#5C4A3A] font-body">hour(s)</span>
                            </div>
                          </div>
                          <div className="pt-2 border-t border-[#E8DFD0]"><span className="text-sm text-[#5C4A3A] font-body">Staff Cost: <strong className="text-[#B8962E]">{formatPrice(staffTotal)}</strong></span></div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Sidebar */}
            <div className="lg:col-span-1">
              <div className="sticky top-24 space-y-6">
                <div className="pearl-surface overflow-hidden">
                  <div className="bg-[#F8F5F0] border-b border-[#B8962E]/20 p-4"><h3 className="text-[#B8962E] font-heading font-medium">Booking Summary</h3></div>
                  <div className="p-4 space-y-3">
                    <div className="space-y-2 text-sm font-body">
                      <p className="text-[#5C4A3A]"><strong className="text-[#2D1810]">Center:</strong> {currentCenter?.displayName || '—'}</p>
                      <p className="text-[#5C4A3A]"><strong className="text-[#2D1810]">Name:</strong> {name || '—'}</p>
                      <p className="text-[#5C4A3A]"><strong className="text-[#2D1810]">Phone:</strong> {phone || '—'}</p>
                      <p className="text-[#5C4A3A]"><strong className="text-[#2D1810]">Date:</strong> {eventDate || '—'}</p>
                      <p className="text-[#5C4A3A]"><strong className="text-[#2D1810]">Time:</strong> {eventTime || '—'}</p>
                      <p className="text-[#5C4A3A]"><strong className="text-[#2D1810]">Guests:</strong> {guestCount}</p>
                      <p className="text-[#5C4A3A]"><strong className="text-[#2D1810]">Package:</strong> {currentPackage?.name || '—'}</p>
                    </div>
                    {currentPackage && (
                      <div className="border-t border-[#E8DFD0] pt-3 space-y-2">
                        <div className="flex justify-between text-sm font-body"><span className="text-[#5C4A3A]">Food ({guestCount} guests):</span><span className="text-[#2D1810]">{formatPrice(foodTotal)}</span></div>
                        {needsCrockery && <div className="flex justify-between text-sm font-body"><span className="text-[#B8962E]/60">Crockery ({crockeryHours}hr):</span><span className="text-[#B8962E]">{formatPrice(crockeryTotal)}</span></div>}
                        {needsStaff && <div className="flex justify-between text-sm font-body"><span className="text-[#B8962E]/60">Staff ({staffCount}x{staffHours}hr):</span><span className="text-[#B8962E]">{formatPrice(staffTotal)}</span></div>}
                        <div className="flex justify-between font-heading font-medium text-lg pt-2 border-t border-[#E8DFD0]"><span className="text-[#2D1810]">Estimated Total:</span><span className="text-[#B8962E]">{formatPrice(estimatedTotal)}</span></div>
                      </div>
                    )}
                  </div>
                </div>
                <div className="bg-[#F8F5F0] border border-[#B8962E]/10 p-4">
                  <div className="flex gap-2 text-sm text-[#B8962E]/60 font-body"><AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" /><p className="text-xs">{bookingRules.catering.disclaimer}</p></div>
                </div>
                <Button onClick={handleSubmit} className="w-full gold-glossy text-white py-6 text-sm rounded-none tracking-widest uppercase font-semibold border-0" disabled={!selectedCenter || !name || !phone || !address || !eventDate || !eventTime || !selectedPackage} data-testid="catering-submit-btn">
                  <MessageCircle className="h-5 w-5 mr-2" /> Send Inquiry via WhatsApp
                </Button>
              </div>
            </div>
          </div>
        ) : (
          /* Review */
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="max-w-2xl mx-auto">
            <div className="bg-white border border-[#E8DFD0] overflow-hidden shadow-lg">
              <div className="bg-[#F8F5F0] border-b border-[#B8962E]/20 p-6 text-center">
                <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-1">Purnabramha</p>
                <h2 className="text-2xl font-heading font-medium text-[#2D1810] mb-1">Premium Catering</h2>
                <p className="text-[#7A6F65] text-xs italic font-body">World's First Intelligent Restaurant Chain</p>
                <div className="w-16 h-0.5 bg-[#B8962E] mx-auto mt-3" />
              </div>
              <div className="p-6 space-y-5">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3"><p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-1 font-body">Guest</p><p className="font-body font-medium text-[#2D1810]">{name}</p><p className="text-[#7A6F65] text-xs mt-0.5 font-body">{phone}</p></div>
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3"><p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-1 font-body">Event</p><p className="font-body font-medium text-[#2D1810]">{eventDate}</p><p className="text-[#7A6F65] text-xs mt-0.5 font-body">{eventTime} &bull; {guestCount} guests</p></div>
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3"><p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-1 font-body">Center</p><p className="font-body font-medium text-[#2D1810]">{currentCenter?.displayName}</p></div>
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3"><p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-1 font-body">Package</p><p className="font-body font-medium text-[#2D1810]">{currentPackage?.name}</p><p className="text-[#7A6F65] text-xs mt-0.5 font-body">{formatPrice(currentPackage?.pricePerPerson || 0)}/person</p></div>
                  <div className="col-span-2 bg-[#F8F5F0] border border-[#E8DFD0] p-3"><p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-1 font-body">Venue</p><p className="font-body font-medium text-[#2D1810]">{address}</p></div>
                </div>
                <div className="bg-[#F8F5F0] border border-[#B8962E]/20 p-4 text-center">
                  <p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-1 font-body">Estimated Total</p>
                  <p className="text-3xl font-heading font-medium text-[#B8962E]">{formatPrice(estimatedTotal)}</p>
                  <p className="text-[#7A6F65] text-xs mt-1 font-body">Final pricing after consultation</p>
                </div>
                <div className="flex gap-3 pt-2">
                  <Button variant="outline" onClick={() => setShowReview(false)} className="flex-1 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] hover:border-[#B8962E]/30 rounded-none">Edit Inquiry</Button>
                  <Button onClick={confirmBooking} className="flex-1 bg-green-600 hover:bg-green-700 text-white rounded-none" data-testid="catering-confirm-btn"><MessageCircle className="h-5 w-5 mr-2" /> Send via WhatsApp</Button>
                </div>
                <p className="text-center text-[10px] text-[#7A6F65] italic font-body">© Purnabramha</p>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};

const MenuSection = ({ title, category, options, selections, required, toggleSelection, getSelectedCount }) => {
  const selected = getSelectedCount(category);
  const isComplete = selected >= required;
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-heading font-medium text-[#2D1810]">{title}</h4>
        <Badge className={isComplete ? 'bg-green-100 text-green-600 border-green-200' : 'bg-[#F8F5F0] text-[#5C4A3A] border-[#E8DFD0]'}>
          {selected}/{required}
        </Badge>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {options.map(option => {
          const isSelected = (selections[category] || []).includes(option.id);
          return (
            <div key={option.id} onClick={() => toggleSelection(category, option.id)}
              className={`p-2 border cursor-pointer transition-all text-sm font-body ${isSelected ? 'border-[#B8962E] bg-[#B8962E]/5 text-[#B8962E] font-medium' : 'border-[#E8DFD0] text-[#5C4A3A] hover:border-[#B8962E]/30'}`}>
              <div className="flex items-center gap-2">
                <Checkbox checked={isSelected} className="pointer-events-none border-[#E8DFD0] data-[state=checked]:bg-[#B8962E] data-[state=checked]:border-[#B8962E]" />
                <span>{option.name}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Catering;
