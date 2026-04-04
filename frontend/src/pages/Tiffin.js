import { useState, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import { MapPin, Phone, MessageCircle, Coffee, Package, AlertTriangle, Plus, Minus, Utensils } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

import centersData from '@/config/centers.json';
import tiffinConfig from '@/config/tiffin-config.json';
import bookingRules from '@/config/booking-rules.json';

const Tiffin = () => {
  const [selectedRegion, setSelectedRegion] = useState('');
  const [selectedCenter, setSelectedCenter] = useState('');
  const [name, setName] = useState('');
  const [mobile, setMobile] = useState('');
  const [selectedWeek, setSelectedWeek] = useState('');
  const [defaultPickupTime, setDefaultPickupTime] = useState('12:00');
  const [lunchSelections, setLunchSelections] = useState({});
  const [brunchSelections, setBrunchSelections] = useState({});
  const [unlimitedBreakfast, setUnlimitedBreakfast] = useState({ enabled: false, date: '', guests: 2 });
  const [showReview, setShowReview] = useState(false);

  const allCenters = useMemo(() => [...centersData.india, ...centersData.australia], []);
  const filteredCenters = useMemo(() => { if (!selectedRegion) return []; return selectedRegion === 'india' ? centersData.india : centersData.australia; }, [selectedRegion]);
  const currentCenter = useMemo(() => allCenters.find(c => c.id === selectedCenter), [selectedCenter, allCenters]);

  const isAustralia = currentCenter?.country === 'Australia';
  const pricing = isAustralia ? tiffinConfig.pricing.australia : tiffinConfig.pricing.india;
  const lunchBoxOptions = isAustralia ? tiffinConfig.lunchBoxOptions.australia : tiffinConfig.lunchBoxOptions.india;
  const heavyBrunchItems = isAustralia ? tiffinConfig.heavyBrunchItems.australia : tiffinConfig.heavyBrunchItems.india;
  const drinkAddons = isAustralia ? tiffinConfig.drinkAddons.australia : tiffinConfig.drinkAddons.india;
  const currencySymbol = isAustralia ? '$' : '₹';
  const breakfastPricing = tiffinConfig.unlimitedBreakfast.pricing[isAustralia ? 'australia' : 'india'];

  const isBlackoutPeriod = useMemo(() => {
    if (!isAustralia) return false;
    const today = new Date();
    return today >= new Date(tiffinConfig.blackoutDates.australia.start) && today <= new Date(tiffinConfig.blackoutDates.australia.end);
  }, [isAustralia]);

  const getWeekOptions = () => {
    const weeks = []; const today = new Date();
    for (let i = 0; i < bookingRules.tiffin.weeksToShow; i++) {
      const startDate = new Date(today); startDate.setDate(today.getDate() + (i * 7) - today.getDay() + 1);
      const endDate = new Date(startDate); endDate.setDate(startDate.getDate() + 4);
      const fmt = (d) => d.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
      weeks.push({ id: `week-${i + 1}`, label: `Week ${i + 1} (${fmt(startDate)} - ${fmt(endDate)} ${startDate.getFullYear()})`, startDate: startDate.toISOString().split('T')[0], endDate: endDate.toISOString().split('T')[0], days: getDaysOfWeek(startDate) });
    }
    return weeks;
  };
  const getDaysOfWeek = (startDate) => {
    const days = []; const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
    for (let i = 0; i < 5; i++) { const date = new Date(startDate); date.setDate(startDate.getDate() + i); days.push({ name: dayNames[i], date: date.toISOString().split('T')[0], displayDate: date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' }) }); }
    return days;
  };
  const weekOptions = useMemo(() => getWeekOptions(), []);
  const currentWeekData = weekOptions.find(w => w.id === selectedWeek);

  useEffect(() => { setLunchSelections({}); setBrunchSelections({}); }, [selectedCenter, selectedWeek]);

  const updateLunchSelection = (dayDate, field, value) => { setLunchSelections(prev => ({ ...prev, [dayDate]: { ...prev[dayDate], [field]: value } })); };
  const updateBrunchSelection = (dayDate, itemId, field, value) => { setBrunchSelections(prev => ({ ...prev, [dayDate]: { ...prev[dayDate], [itemId]: { ...prev[dayDate]?.[itemId], [field]: value } } })); };
  const formatPrice = (price) => `${currencySymbol}${price.toFixed(2)}`;

  const calculateTotals = useMemo(() => {
    let lunchTotal = 0, brunchTotal = 0, breakfastTotal = 0;
    Object.entries(lunchSelections).forEach(([date, sel]) => { if (sel?.included && sel?.lunchBox) { const lb = lunchBoxOptions.find(l => l.id === sel.lunchBox); if (lb) lunchTotal += lb.price; } });
    Object.entries(brunchSelections).forEach(([date, items]) => {
      Object.entries(items || {}).forEach(([itemId, sel]) => {
        if (sel?.qty > 0) {
          const item = heavyBrunchItems.find(h => h.id === itemId); if (item) brunchTotal += item.price * sel.qty;
          if (sel.buttermilk) { const a = drinkAddons.find(d => d.id === 'da-1'); if (a) brunchTotal += a.price * sel.qty; }
          if (sel.kokum) { const a = drinkAddons.find(d => d.id === 'da-2'); if (a) brunchTotal += a.price * sel.qty; }
        }
      });
    });
    if (unlimitedBreakfast.enabled && unlimitedBreakfast.guests > 0) breakfastTotal = breakfastPricing.perPerson * unlimitedBreakfast.guests;
    const subtotal = lunchTotal + brunchTotal + breakfastTotal;
    const gst = !isAustralia ? subtotal * (pricing.lunchBox.gstPercent / 100) : 0;
    return { lunchTotal, brunchTotal, breakfastTotal, subtotal, gst, grandTotal: subtotal + gst };
  }, [lunchSelections, brunchSelections, unlimitedBreakfast, lunchBoxOptions, heavyBrunchItems, drinkAddons, pricing, isAustralia, breakfastPricing]);

  const generateWhatsAppMessage = () => {
    let message = `*PURNABRAMHA TIFFIN*\n\n`;
    message += `*${name}* | ${mobile}\n${currentCenter?.displayName}\n${currentWeekData?.label}\n`;
    if (Object.keys(lunchSelections).length > 0) {
      message += `\n*Lunch Box:*\n`;
      currentWeekData?.days.forEach(day => { const sel = lunchSelections[day.date]; if (sel?.included && sel?.lunchBox) { const lb = lunchBoxOptions.find(l => l.id === sel.lunchBox); message += `${day.name} - ${lb?.name} @ ${sel.pickupTime || defaultPickupTime}\n`; } });
      message += `Lunch: ${formatPrice(calculateTotals.lunchTotal)}\n`;
    }
    const hasBrunch = Object.values(brunchSelections).some(items => Object.values(items || {}).some(s => s?.qty > 0));
    if (hasBrunch) {
      message += `\n*Brunch:*\n`;
      currentWeekData?.days.forEach(day => {
        const items = brunchSelections[day.date]; if (items) {
          const dayItems = Object.entries(items).filter(([_, s]) => s?.qty > 0).map(([itemId, s]) => { const item = heavyBrunchItems.find(h => h.id === itemId); let addons = []; if (s.buttermilk) addons.push('Buttermilk'); if (s.kokum) addons.push('Kokum'); return `${item?.name} x${s.qty}${addons.length ? ' +' + addons.join('+') : ''}`; });
          if (dayItems.length > 0) message += `${day.name} - ${dayItems.join(', ')}\n`;
        }
      });
      message += `Brunch: ${formatPrice(calculateTotals.brunchTotal)}\n`;
    }
    if (unlimitedBreakfast.enabled) { message += `\n*Breakfast:* ${unlimitedBreakfast.date} | ${unlimitedBreakfast.guests} guests\n${formatPrice(calculateTotals.breakfastTotal)}\n`; }
    message += `\n---\n`;
    if (!isAustralia && calculateTotals.gst > 0) message += `Subtotal: ${formatPrice(calculateTotals.subtotal)} + GST: ${formatPrice(calculateTotals.gst)}\n`;
    message += `*TOTAL: ${formatPrice(calculateTotals.grandTotal)}*\n\n_Powered by A.AI Technology_`;
    return encodeURIComponent(message);
  };

  const handleSubmit = () => {
    if (!selectedCenter || !name || !mobile || !selectedWeek) { toast.error('Please fill all required fields'); return; }
    if (calculateTotals.grandTotal === 0) { toast.error('Please select at least one item'); return; }
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
            <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-4">Daily Meals</p>
            <h1 className="font-heading text-5xl md:text-6xl font-medium text-[#2D1810] mb-4 tracking-tight" data-testid="tiffin-title">
              Tiffin & Heavy <span className="text-gold-shimmer">Brunch</span>
            </h1>
            <p className="text-lg text-[#5C4A3A] font-body">Weekly lunch box subscriptions & daily heavy brunch orders</p>
          </motion.div>
        </div>
      </section>

      <div className="container mx-auto px-6 lg:px-12 py-10">
        {isBlackoutPeriod && isAustralia && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
            <div className="bg-red-50 border border-red-200 p-4 flex gap-3 rounded-none">
              <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0" />
              <div className="text-red-700 font-body"><p className="font-semibold">Christmas & New Year Notice</p><p className="text-sm text-red-600">{tiffinConfig.blackoutDates.australia.message}</p></div>
            </div>
          </motion.div>
        )}

        {!showReview ? (
          <div className="grid lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-6">
              {/* Center & Basic Info */}
              <div className="pearl-surface overflow-hidden">
                <div className="bg-[#F8F5F0] border-b border-[#E8DFD0] p-4"><h3 className="flex items-center gap-2 text-[#B8962E] font-heading font-medium"><MapPin className="h-5 w-5" /> Center & Contact Details</h3></div>
                <div className="p-6 space-y-4 bg-white">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div><Label className={labelCls}>Region *</Label><Select value={selectedRegion} onValueChange={(v) => { setSelectedRegion(v); setSelectedCenter(''); }}><SelectTrigger className={inputCls} data-testid="tiffin-region-select"><SelectValue placeholder="Select Region" /></SelectTrigger><SelectContent className="bg-white border-[#E8DFD0]"><SelectItem value="india">India</SelectItem><SelectItem value="australia">Australia</SelectItem></SelectContent></Select></div>
                    <div><Label className={labelCls}>Center *</Label><Select value={selectedCenter} onValueChange={setSelectedCenter} disabled={!selectedRegion}><SelectTrigger className={inputCls} data-testid="tiffin-center-select"><SelectValue placeholder="Select Center" /></SelectTrigger><SelectContent className="bg-white border-[#E8DFD0]">{filteredCenters.map(c => <SelectItem key={c.id} value={c.id}>{c.displayName}</SelectItem>)}</SelectContent></Select></div>
                  </div>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div><Label className={labelCls}>Name *</Label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your full name" className={inputCls} data-testid="tiffin-name" /></div>
                    <div><Label className={labelCls}>Mobile *</Label><Input value={mobile} onChange={(e) => setMobile(e.target.value)} placeholder="Your mobile number" className={inputCls} data-testid="tiffin-mobile" /></div>
                  </div>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div><Label className={labelCls}>Select Week *</Label><Select value={selectedWeek} onValueChange={setSelectedWeek}><SelectTrigger className={inputCls} data-testid="tiffin-week-select"><SelectValue placeholder="Select Week" /></SelectTrigger><SelectContent className="bg-white border-[#E8DFD0]">{weekOptions.map(w => <SelectItem key={w.id} value={w.id}>{w.label}</SelectItem>)}</SelectContent></Select></div>
                    <div><Label className={labelCls}>Default Pickup Time</Label><Select value={defaultPickupTime} onValueChange={setDefaultPickupTime}><SelectTrigger className={inputCls}><SelectValue /></SelectTrigger><SelectContent className="bg-white border-[#E8DFD0]">{bookingRules.tiffin.pickupTimes.map(t => <SelectItem key={t.id} value={t.id}>{t.label}</SelectItem>)}</SelectContent></Select></div>
                  </div>
                </div>
              </div>

              {/* Unlimited Breakfast */}
              <div className="pearl-surface overflow-hidden border-[#B8962E]/20">
                <div className="bg-gradient-to-r from-[#B8962E]/10 to-[#B8962E]/5 border-b border-[#B8962E]/20 p-4">
                  <h3 className="flex items-center gap-2 text-[#B8962E] font-heading font-medium"><Coffee className="h-5 w-5" /> Unlimited Breakfast <Badge className="ml-2 bg-[#B8962E] text-white text-[10px]">Special</Badge></h3>
                  <p className="text-xs text-[#5C4A3A] mt-1 font-body">{tiffinConfig.unlimitedBreakfast.description} - {tiffinConfig.unlimitedBreakfast.timings}</p>
                </div>
                <div className="p-6 bg-white">
                  <div className="flex items-start gap-3 mb-4">
                    <Checkbox id="unlimited-breakfast" checked={unlimitedBreakfast.enabled} onCheckedChange={(checked) => setUnlimitedBreakfast(prev => ({ ...prev, enabled: checked }))} className="border-[#E8DFD0] data-[state=checked]:bg-[#B8962E] data-[state=checked]:border-[#B8962E]" data-testid="unlimited-breakfast-checkbox" />
                    <div><label htmlFor="unlimited-breakfast" className="font-body font-medium cursor-pointer text-[#2D1810]">Add Unlimited Breakfast</label><p className="text-sm text-[#5C4A3A] font-body">{breakfastPricing.symbol}{breakfastPricing.perPerson} per person - Available {tiffinConfig.unlimitedBreakfast.availableDays.join(' & ')}</p></div>
                  </div>
                  {unlimitedBreakfast.enabled && (
                    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="space-y-4 pl-7">
                      <div className="grid md:grid-cols-2 gap-4">
                        <div><Label className={labelCls}>Select Date</Label><Input type="date" value={unlimitedBreakfast.date} onChange={(e) => setUnlimitedBreakfast(prev => ({ ...prev, date: e.target.value }))} className={inputCls} data-testid="breakfast-date" /></div>
                        <div><Label className={labelCls}>Number of Guests</Label>
                          <div className="flex items-center gap-3">
                            <Button variant="outline" size="icon" className="border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] rounded-none" onClick={() => setUnlimitedBreakfast(prev => ({ ...prev, guests: Math.max(1, prev.guests - 1) }))}><Minus className="h-4 w-4" /></Button>
                            <span className="text-xl font-heading font-medium w-12 text-center text-[#2D1810]">{unlimitedBreakfast.guests}</span>
                            <Button variant="outline" size="icon" className="border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] rounded-none" onClick={() => setUnlimitedBreakfast(prev => ({ ...prev, guests: prev.guests + 1 }))}><Plus className="h-4 w-4" /></Button>
                          </div>
                        </div>
                      </div>
                      <div className="p-3 bg-[#F8F5F0] border border-[#E8DFD0]"><p className="text-sm font-body font-medium text-[#B8962E]">Includes:</p><p className="text-xs text-[#5C4A3A] font-body">{tiffinConfig.unlimitedBreakfast.includes.join(' - ')}</p></div>
                    </motion.div>
                  )}
                </div>
              </div>

              {/* Lunch Box */}
              {selectedWeek && currentWeekData && (
                <div className="pearl-surface overflow-hidden">
                  <div className="bg-[#F8F5F0] border-b border-[#E8DFD0] p-4"><h3 className="flex items-center gap-2 text-[#B8962E] font-heading font-medium"><Package className="h-5 w-5" /> Lunch Box (Mon-Fri)</h3></div>
                  <div className="p-6 space-y-4 bg-white">
                    {currentWeekData.days.map(day => (
                      <div key={day.date} className="p-4 border border-[#E8DFD0]">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <Checkbox checked={lunchSelections[day.date]?.included || false} onCheckedChange={(checked) => updateLunchSelection(day.date, 'included', checked)} className="border-[#E8DFD0] data-[state=checked]:bg-[#B8962E] data-[state=checked]:border-[#B8962E]" />
                            <span className="font-body font-semibold text-[#2D1810]">{day.name} ({day.displayDate})</span>
                          </div>
                        </div>
                        {lunchSelections[day.date]?.included && (
                          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid md:grid-cols-2 gap-4 pl-7">
                            <div>
                              <Label className={labelCls}>Lunch Box Type</Label>
                              <Select value={lunchSelections[day.date]?.lunchBox || ''} onValueChange={(v) => updateLunchSelection(day.date, 'lunchBox', v)}>
                                <SelectTrigger className={inputCls}><SelectValue placeholder="Select combo" /></SelectTrigger>
                                <SelectContent className="bg-white border-[#E8DFD0]">{lunchBoxOptions.map(opt => <SelectItem key={opt.id} value={opt.id}><span className="font-medium">{opt.name}</span> - {formatPrice(opt.price)}</SelectItem>)}</SelectContent>
                              </Select>
                              {lunchSelections[day.date]?.lunchBox && (
                                <div className="mt-2 p-2.5 bg-[#F8F5F0] border border-[#E8DFD0]">
                                  <p className="text-xs font-body font-semibold text-[#B8962E] mb-0.5">{lunchBoxOptions.find(o => o.id === lunchSelections[day.date]?.lunchBox)?.name}</p>
                                  <p className="text-xs text-[#5C4A3A] font-body">{lunchBoxOptions.find(o => o.id === lunchSelections[day.date]?.lunchBox)?.description}</p>
                                </div>
                              )}
                            </div>
                            <div>
                              <Label className={labelCls}>Pickup Time</Label>
                              <Select value={lunchSelections[day.date]?.pickupTime || defaultPickupTime} onValueChange={(v) => updateLunchSelection(day.date, 'pickupTime', v)}>
                                <SelectTrigger className={inputCls}><SelectValue /></SelectTrigger>
                                <SelectContent className="bg-white border-[#E8DFD0]">{bookingRules.tiffin.pickupTimes.map(t => <SelectItem key={t.id} value={t.id}>{t.label}</SelectItem>)}</SelectContent>
                              </Select>
                            </div>
                          </motion.div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Heavy Brunch */}
              {selectedWeek && currentWeekData && (
                <div className="pearl-surface overflow-hidden">
                  <div className="bg-[#F8F5F0] border-b border-[#E8DFD0] p-4">
                    <h3 className="flex items-center gap-2 text-[#B8962E] font-heading font-medium"><Utensils className="h-5 w-5" /> Heavy Brunch (Mon-Fri)</h3>
                    <p className="text-xs text-[#7A6F65] mt-1 font-body">Tiffin-exclusive pricing - save more than dine-in!</p>
                  </div>
                  <div className="p-6 space-y-6 bg-white">
                    {currentWeekData.days.map(day => (
                      <div key={day.date} className="border-b border-[#E8DFD0] pb-4 last:border-0">
                        <h4 className="font-heading font-medium text-[#2D1810] mb-3">{day.name} ({day.displayDate})</h4>
                        <div className="space-y-3">
                          {heavyBrunchItems.map(item => {
                            const saving = item.menuPrice ? (item.menuPrice - item.price) : 0;
                            return (
                              <div key={item.id} className="flex items-center gap-3 p-3 border border-transparent hover:border-[#E8DFD0] hover:bg-[#F8F5F0] transition-all">
                                <BrunchItemImage name={item.name} />
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span className="font-body font-semibold text-[#2D1810]">{item.name}</span>
                                    {saving > 0 && <Badge className="bg-green-100 text-green-700 border-green-200 text-[10px] px-1.5 py-0" variant="outline">Save {formatPrice(saving)}</Badge>}
                                  </div>
                                  {item.description && <p className="text-xs text-[#7A6F65] mt-0.5 truncate font-body">{item.description}</p>}
                                  <div className="flex items-center gap-2 mt-1">
                                    <span className="text-sm font-heading font-medium text-[#B8962E]">{formatPrice(item.price)}</span>
                                    {item.menuPrice && <span className="text-xs text-[#7A6F65] line-through font-body">{formatPrice(item.menuPrice)}</span>}
                                  </div>
                                </div>
                                <div className="flex items-center gap-3 flex-shrink-0">
                                  <div className="flex items-center gap-1">
                                    <Checkbox id={`${day.date}-${item.id}-buttermilk`} checked={brunchSelections[day.date]?.[item.id]?.buttermilk || false} onCheckedChange={(c) => updateBrunchSelection(day.date, item.id, 'buttermilk', c)} disabled={!brunchSelections[day.date]?.[item.id]?.qty} className="border-[#E8DFD0] data-[state=checked]:bg-[#B8962E] data-[state=checked]:border-[#B8962E]" />
                                    <label htmlFor={`${day.date}-${item.id}-buttermilk`} className="text-xs text-[#5C4A3A] font-body">+Buttermilk</label>
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <Checkbox id={`${day.date}-${item.id}-kokum`} checked={brunchSelections[day.date]?.[item.id]?.kokum || false} onCheckedChange={(c) => updateBrunchSelection(day.date, item.id, 'kokum', c)} disabled={!brunchSelections[day.date]?.[item.id]?.qty} className="border-[#E8DFD0] data-[state=checked]:bg-[#B8962E] data-[state=checked]:border-[#B8962E]" />
                                    <label htmlFor={`${day.date}-${item.id}-kokum`} className="text-xs text-[#5C4A3A] font-body">+Kokum</label>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <Button variant="outline" size="icon" className="h-7 w-7 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] rounded-none" onClick={() => updateBrunchSelection(day.date, item.id, 'qty', Math.max(0, (brunchSelections[day.date]?.[item.id]?.qty || 0) - 1))}><Minus className="h-3 w-3" /></Button>
                                    <span className="w-6 text-center font-body font-semibold text-[#2D1810]">{brunchSelections[day.date]?.[item.id]?.qty || 0}</span>
                                    <Button variant="outline" size="icon" className="h-7 w-7 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] rounded-none" onClick={() => updateBrunchSelection(day.date, item.id, 'qty', (brunchSelections[day.date]?.[item.id]?.qty || 0) + 1)}><Plus className="h-3 w-3" /></Button>
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Sidebar */}
            <div className="lg:col-span-1">
              <div className="sticky top-24 space-y-6">
                <div className="pearl-surface overflow-hidden">
                  <div className="bg-[#F8F5F0] border-b border-[#B8962E]/20 p-4"><h3 className="text-[#B8962E] font-heading font-medium">Order Summary</h3></div>
                  <div className="p-4 space-y-3 bg-white">
                    <div className="space-y-2 text-sm font-body">
                      <p className="text-[#5C4A3A]"><strong className="text-[#2D1810]">Center:</strong> {currentCenter?.displayName || '-'}</p>
                      <p className="text-[#5C4A3A]"><strong className="text-[#2D1810]">Name:</strong> {name || '-'}</p>
                      <p className="text-[#5C4A3A]"><strong className="text-[#2D1810]">Mobile:</strong> {mobile || '-'}</p>
                      <p className="text-[#5C4A3A]"><strong className="text-[#2D1810]">Week:</strong> {currentWeekData?.label || '-'}</p>
                    </div>
                    <div className="border-t border-[#E8DFD0] pt-3 space-y-2">
                      <div className="flex justify-between text-sm font-body"><span className="text-[#5C4A3A]">Lunch Total:</span><span className="text-[#2D1810]">{formatPrice(calculateTotals.lunchTotal)}</span></div>
                      <div className="flex justify-between text-sm font-body"><span className="text-[#5C4A3A]">Brunch Total:</span><span className="text-[#2D1810]">{formatPrice(calculateTotals.brunchTotal)}</span></div>
                      {unlimitedBreakfast.enabled && <div className="flex justify-between text-sm font-body"><span className="text-[#B8962E]">Unlimited Breakfast:</span><span className="text-[#B8962E]">{formatPrice(calculateTotals.breakfastTotal)}</span></div>}
                      {!isAustralia && calculateTotals.gst > 0 && <div className="flex justify-between text-sm font-body"><span className="text-[#7A6F65]">GST (5%):</span><span className="text-[#7A6F65]">{formatPrice(calculateTotals.gst)}</span></div>}
                      <div className="flex justify-between font-heading font-medium text-lg pt-2 border-t border-[#E8DFD0]"><span className="text-[#2D1810]">Grand Total:</span><span className="text-[#B8962E]">{formatPrice(calculateTotals.grandTotal)}</span></div>
                    </div>
                  </div>
                </div>
                <Button onClick={handleSubmit} className="w-full gold-glossy text-[#3D2314] font-bold py-6 text-sm rounded-none tracking-widest uppercase" disabled={!selectedCenter || !name || !mobile || calculateTotals.grandTotal === 0} data-testid="tiffin-submit-btn">
                  <MessageCircle className="h-5 w-5 mr-2" /> Send to WhatsApp
                </Button>
              </div>
            </div>
          </div>
        ) : (
          /* Review */
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="max-w-2xl mx-auto">
            <div className="pearl-surface overflow-hidden">
              <div className="bg-[#F8F5F0] border-b border-[#B8962E]/20 p-6 text-center">
                <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-1">Purnabramha</p>
                <h2 className="text-2xl font-heading font-medium text-[#2D1810] mb-1">Tiffin Service</h2>
                <p className="text-[#7A6F65] text-xs italic font-body">World's First Intelligent Restaurant Chain</p>
                <div className="w-16 h-0.5 bg-[#B8962E] mx-auto mt-3" />
              </div>
              <div className="p-6 space-y-5 bg-white">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3"><p className="text-[#B8962E] text-xs uppercase tracking-wider mb-1 font-body">Customer</p><p className="font-body font-medium text-[#2D1810]">{name}</p><p className="text-[#7A6F65] text-xs mt-0.5 font-body">{mobile}</p></div>
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3"><p className="text-[#B8962E] text-xs uppercase tracking-wider mb-1 font-body">Center</p><p className="font-body font-medium text-[#2D1810]">{currentCenter?.displayName}</p></div>
                  <div className="col-span-2 bg-[#F8F5F0] border border-[#E8DFD0] p-3"><p className="text-[#B8962E] text-xs uppercase tracking-wider mb-1 font-body">Week</p><p className="font-body font-medium text-[#2D1810]">{currentWeekData?.label}</p></div>
                </div>
                <div className="space-y-3">
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3"><div className="flex justify-between items-center"><span className="text-sm text-[#5C4A3A] font-body">Lunch Orders</span><span className="font-body font-semibold text-[#2D1810]">{formatPrice(calculateTotals.lunchTotal)}</span></div></div>
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3"><div className="flex justify-between items-center"><span className="text-sm text-[#5C4A3A] font-body">Brunch Orders</span><span className="font-body font-semibold text-[#2D1810]">{formatPrice(calculateTotals.brunchTotal)}</span></div></div>
                  {unlimitedBreakfast.enabled && <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3"><div className="flex justify-between items-center"><span className="text-sm text-[#5C4A3A] font-body">Unlimited Breakfast ({unlimitedBreakfast.guests} guests)</span><span className="font-body font-semibold text-[#B8962E]">{formatPrice(calculateTotals.breakfastTotal)}</span></div></div>}
                  {!isAustralia && calculateTotals.gst > 0 && <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3"><div className="flex justify-between items-center"><span className="text-sm text-[#7A6F65] font-body">GST (5%)</span><span className="text-[#7A6F65] font-body">{formatPrice(calculateTotals.gst)}</span></div></div>}
                </div>
                <div className="bg-gradient-to-r from-[#B8962E]/10 to-[#B8962E]/5 border border-[#B8962E]/20 p-4 text-center">
                  <p className="text-[#B8962E] text-xs uppercase tracking-wider mb-1 font-body">Grand Total</p>
                  <p className="text-3xl font-heading font-medium text-[#B8962E]">{formatPrice(calculateTotals.grandTotal)}</p>
                </div>
                <div className="flex gap-3 pt-2">
                  <Button variant="outline" onClick={() => setShowReview(false)} className="flex-1 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] hover:border-[#B8962E]/30 rounded-none">Edit Order</Button>
                  <Button onClick={confirmBooking} className="flex-1 bg-green-600 hover:bg-green-700 text-white rounded-none" data-testid="tiffin-confirm-btn"><MessageCircle className="h-5 w-5 mr-2" /> Send via WhatsApp</Button>
                </div>
                <p className="text-center text-[10px] text-[#7A6F65] italic font-body">Powered by A.AI Technology</p>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};

const BRUNCH_IMAGE_MAP = {
  'Thalipith': { fallbackColor: 'from-amber-100 to-amber-50', initials: 'TP' },
  'Misal Pav': { fallbackColor: 'from-red-100 to-red-50', initials: 'MP' },
  'Shrikhanda Puri Bhaji': { fallbackColor: 'from-yellow-100 to-amber-50', initials: 'SP' },
  'Aloo Paratha': { fallbackColor: 'from-amber-100 to-yellow-50', initials: 'AP' },
  'Sabudana Khichadi': { fallbackColor: 'from-green-100 to-green-50', initials: 'SK' }
};

const BrunchItemImage = ({ name }) => {
  const [menuImage, setMenuImage] = useState(null);
  const fallback = BRUNCH_IMAGE_MAP[name] || { fallbackColor: 'from-[#F8F5F0] to-[#FDFBF7]', initials: name.substring(0, 2).toUpperCase() };

  useEffect(() => {
    const API = process.env.REACT_APP_BACKEND_URL;
    fetch(`${API}/api/menu`).then(res => res.json()).then(items => { const match = items.find(i => i.name.toLowerCase().includes(name.toLowerCase()) && i.image_url); if (match) setMenuImage(match.image_url); }).catch(() => {});
  }, [name]);

  if (menuImage) return <img src={menuImage} alt={name} className="w-14 h-14 object-cover border border-[#E8DFD0] flex-shrink-0" onError={(e) => { e.target.style.display = 'none'; }} />;
  return (
    <div className={`w-14 h-14 bg-gradient-to-br ${fallback.fallbackColor} flex items-center justify-center flex-shrink-0 border border-[#E8DFD0]`}>
      <span className="text-[#B8962E] font-heading font-medium text-sm">{fallback.initials}</span>
    </div>
  );
};

export default Tiffin;
