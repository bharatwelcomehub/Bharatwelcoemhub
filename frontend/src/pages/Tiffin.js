import { useState, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Calendar, Clock, MapPin, Phone, MessageCircle, Coffee, Package, AlertTriangle, CheckCircle, Plus, Minus, Utensils } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
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

  const filteredCenters = useMemo(() => {
    if (!selectedRegion) return [];
    return selectedRegion === 'india' ? centersData.india : centersData.australia;
  }, [selectedRegion]);

  const currentCenter = useMemo(() => {
    return allCenters.find(c => c.id === selectedCenter);
  }, [selectedCenter, allCenters]);

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
    const start = new Date(tiffinConfig.blackoutDates.australia.start);
    const end = new Date(tiffinConfig.blackoutDates.australia.end);
    return today >= start && today <= end;
  }, [isAustralia]);

  const getWeekOptions = () => {
    const weeks = [];
    const today = new Date();
    for (let i = 0; i < bookingRules.tiffin.weeksToShow; i++) {
      const startDate = new Date(today);
      startDate.setDate(today.getDate() + (i * 7) - today.getDay() + 1);
      const endDate = new Date(startDate);
      endDate.setDate(startDate.getDate() + 4);
      
      const formatDate = (d) => d.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
      weeks.push({
        id: `week-${i + 1}`,
        label: `Week ${i + 1} (${formatDate(startDate)} – ${formatDate(endDate)} ${startDate.getFullYear()})`,
        startDate: startDate.toISOString().split('T')[0],
        endDate: endDate.toISOString().split('T')[0],
        days: getDaysOfWeek(startDate)
      });
    }
    return weeks;
  };

  const getDaysOfWeek = (startDate) => {
    const days = [];
    const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
    for (let i = 0; i < 5; i++) {
      const date = new Date(startDate);
      date.setDate(startDate.getDate() + i);
      days.push({
        name: dayNames[i],
        date: date.toISOString().split('T')[0],
        displayDate: date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' })
      });
    }
    return days;
  };

  const weekOptions = useMemo(() => getWeekOptions(), []);
  const currentWeekData = weekOptions.find(w => w.id === selectedWeek);

  useEffect(() => {
    setLunchSelections({});
    setBrunchSelections({});
  }, [selectedCenter, selectedWeek]);

  const updateLunchSelection = (dayDate, field, value) => {
    setLunchSelections(prev => ({
      ...prev,
      [dayDate]: {
        ...prev[dayDate],
        [field]: value
      }
    }));
  };

  const updateBrunchSelection = (dayDate, itemId, field, value) => {
    setBrunchSelections(prev => ({
      ...prev,
      [dayDate]: {
        ...prev[dayDate],
        [itemId]: {
          ...prev[dayDate]?.[itemId],
          [field]: value
        }
      }
    }));
  };

  const formatPrice = (price) => `${currencySymbol}${price.toFixed(2)}`;

  const calculateTotals = useMemo(() => {
    let lunchTotal = 0;
    let brunchTotal = 0;
    let breakfastTotal = 0;

    Object.entries(lunchSelections).forEach(([date, selection]) => {
      if (selection?.included && selection?.lunchBox) {
        const lunchBox = lunchBoxOptions.find(l => l.id === selection.lunchBox);
        if (lunchBox) lunchTotal += lunchBox.price;
      }
    });

    Object.entries(brunchSelections).forEach(([date, items]) => {
      Object.entries(items || {}).forEach(([itemId, selection]) => {
        if (selection?.qty > 0) {
          const item = heavyBrunchItems.find(h => h.id === itemId);
          if (item) brunchTotal += item.price * selection.qty;
          
          if (selection.buttermilk) {
            const addon = drinkAddons.find(d => d.id === 'da-1');
            if (addon) brunchTotal += addon.price * selection.qty;
          }
          if (selection.kokum) {
            const addon = drinkAddons.find(d => d.id === 'da-2');
            if (addon) brunchTotal += addon.price * selection.qty;
          }
        }
      });
    });

    if (unlimitedBreakfast.enabled && unlimitedBreakfast.guests > 0) {
      breakfastTotal = breakfastPricing.perPerson * unlimitedBreakfast.guests;
    }

    const subtotal = lunchTotal + brunchTotal + breakfastTotal;
    const gst = !isAustralia ? subtotal * (pricing.lunchBox.gstPercent / 100) : 0;

    return { lunchTotal, brunchTotal, breakfastTotal, subtotal, gst, grandTotal: subtotal + gst };
  }, [lunchSelections, brunchSelections, unlimitedBreakfast, lunchBoxOptions, heavyBrunchItems, drinkAddons, pricing, isAustralia, breakfastPricing]);

  const generateWhatsAppMessage = () => {
    let message = ``;
    message += `═══════════════════════\n`;
    message += `     *P U R N A B R A M H A*\n`;
    message += `  _World's First Intelligent Restaurant_\n`;
    message += `    _Chain Powered by A.AI Technology_\n`;
    message += `═══════════════════════\n\n`;
    message += `✦  *TIFFIN SERVICE ORDER*  ✦\n\n`;
    message += `───── Customer Details ─────\n\n`;
    message += `  *Name:*    ${name}\n`;
    message += `  *Mobile:*  ${mobile}\n`;
    message += `  *Center:*  ${currentCenter?.displayName}\n`;
    message += `  *Week:*    ${currentWeekData?.label}\n\n`;

    if (Object.keys(lunchSelections).length > 0) {
      message += `───── Lunch Box Orders ─────\n\n`;
      currentWeekData?.days.forEach(day => {
        const selection = lunchSelections[day.date];
        if (selection?.included && selection?.lunchBox) {
          const lunchBox = lunchBoxOptions.find(l => l.id === selection.lunchBox);
          message += `  ${day.name} (${day.displayDate})\n`;
          message += `    • ${lunchBox?.name} @ ${selection.pickupTime || defaultPickupTime}\n`;
        }
      });
      message += `\n  Lunch Subtotal: ${formatPrice(calculateTotals.lunchTotal)}\n\n`;
    }

    const hasBrunch = Object.values(brunchSelections).some(items => 
      Object.values(items || {}).some(s => s?.qty > 0)
    );
    
    if (hasBrunch) {
      message += `───── Heavy Brunch Orders ─────\n\n`;
      currentWeekData?.days.forEach(day => {
        const items = brunchSelections[day.date];
        if (items) {
          const dayItems = Object.entries(items)
            .filter(([_, s]) => s?.qty > 0)
            .map(([itemId, s]) => {
              const item = heavyBrunchItems.find(h => h.id === itemId);
              let addons = [];
              if (s.buttermilk) addons.push('Buttermilk');
              if (s.kokum) addons.push('Kokum');
              return `${item?.name} × ${s.qty}${addons.length ? ` + ${addons.join(', ')}` : ''}`;
            });
          if (dayItems.length > 0) {
            message += `  ${day.name}\n`;
            dayItems.forEach(di => { message += `    • ${di}\n`; });
          }
        }
      });
      message += `\n  Brunch Subtotal: ${formatPrice(calculateTotals.brunchTotal)}\n\n`;
    }

    if (unlimitedBreakfast.enabled) {
      message += `───── Unlimited Breakfast ─────\n\n`;
      message += `  Date:    ${unlimitedBreakfast.date}\n`;
      message += `  Guests:  ${unlimitedBreakfast.guests}\n`;
      message += `  Price:   ${formatPrice(calculateTotals.breakfastTotal)}\n\n`;
    }

    message += `═══════════════════════\n`;
    message += `         *TOTAL*\n`;
    message += `═══════════════════════\n\n`;
    if (!isAustralia && calculateTotals.gst > 0) {
      message += `  Subtotal:  ${formatPrice(calculateTotals.subtotal)}\n`;
      message += `  GST (5%):  ${formatPrice(calculateTotals.gst)}\n\n`;
    }
    message += `  ✦ *GRAND TOTAL: ${formatPrice(calculateTotals.grandTotal)}* ✦\n`;
    message += `\n═══════════════════════\n`;
    message += `  _Purnabramha — Authentic Maharashtrian_\n`;
    message += `  _Cuisine Since 2012_\n`;

    return encodeURIComponent(message);
  };

  const handleSubmit = () => {
    if (!selectedCenter || !name || !mobile || !selectedWeek) {
      toast.error('Please fill all required fields');
      return;
    }
    if (calculateTotals.grandTotal === 0) {
      toast.error('Please select at least one item');
      return;
    }
    setShowReview(true);
  };

  const confirmBooking = () => {
    const message = generateWhatsAppMessage();
    const whatsappNumber = currentCenter?.whatsapp.replace(/[^0-9]/g, '');
    window.open(`https://wa.me/${whatsappNumber}?text=${message}`, '_blank');
    toast.success('Redirecting to WhatsApp...');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50 to-orange-50">
      {/* Hero Section */}
      <section className="relative py-16 bg-gradient-to-r from-[#5c1e1e] to-[#8b2c2c] text-white">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center max-w-3xl mx-auto"
          >
            <h1 className="text-4xl md:text-5xl font-bold mb-4" data-testid="tiffin-title">
              🍱 Tiffin & Heavy Brunch
            </h1>
            <p className="text-lg text-amber-200">
              Weekly lunch box subscriptions & daily heavy brunch orders
            </p>
          </motion.div>
        </div>
      </section>

      <div className="container mx-auto px-4 py-8">
        {isBlackoutPeriod && isAustralia && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6"
          >
            <Card className="border-red-300 bg-red-50">
              <CardContent className="pt-4 flex gap-3">
                <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0" />
                <div className="text-red-800">
                  <p className="font-semibold">🎄 Christmas & New Year Notice</p>
                  <p className="text-sm">{tiffinConfig.blackoutDates.australia.message}</p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {!showReview ? (
          <div className="grid lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-6">
              {/* Center & Basic Info */}
              <Card className="border-amber-200 shadow-lg">
                <CardHeader className="bg-gradient-to-r from-amber-100 to-orange-100 rounded-t-lg">
                  <CardTitle className="flex items-center gap-2 text-[#5c1e1e]">
                    <MapPin className="h-5 w-5" />
                    Center & Contact Details
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6 space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <Label>Region *</Label>
                      <Select value={selectedRegion} onValueChange={(v) => { setSelectedRegion(v); setSelectedCenter(''); }}>
                        <SelectTrigger data-testid="tiffin-region-select">
                          <SelectValue placeholder="Select Region" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="india">🇮🇳 India</SelectItem>
                          <SelectItem value="australia">🇦🇺 Australia</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>Center *</Label>
                      <Select value={selectedCenter} onValueChange={setSelectedCenter} disabled={!selectedRegion}>
                        <SelectTrigger data-testid="tiffin-center-select">
                          <SelectValue placeholder="Select Center" />
                        </SelectTrigger>
                        <SelectContent>
                          {filteredCenters.map(center => (
                            <SelectItem key={center.id} value={center.id}>
                              {center.displayName}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <Label>Name *</Label>
                      <Input
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Your full name"
                        className="border-amber-200"
                        data-testid="tiffin-name"
                      />
                    </div>
                    <div>
                      <Label>Mobile *</Label>
                      <Input
                        value={mobile}
                        onChange={(e) => setMobile(e.target.value)}
                        placeholder="Your mobile number"
                        className="border-amber-200"
                        data-testid="tiffin-mobile"
                      />
                    </div>
                  </div>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <Label>Select Week *</Label>
                      <Select value={selectedWeek} onValueChange={setSelectedWeek}>
                        <SelectTrigger data-testid="tiffin-week-select">
                          <SelectValue placeholder="Select Week" />
                        </SelectTrigger>
                        <SelectContent>
                          {weekOptions.map(week => (
                            <SelectItem key={week.id} value={week.id}>
                              {week.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>Default Pickup Time</Label>
                      <Select value={defaultPickupTime} onValueChange={setDefaultPickupTime}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {bookingRules.tiffin.pickupTimes.map(time => (
                            <SelectItem key={time.id} value={time.id}>
                              {time.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Unlimited Breakfast Section */}
              <Card className="border-amber-200 shadow-lg overflow-hidden">
                <CardHeader className="bg-gradient-to-r from-orange-400 to-amber-400 text-white">
                  <CardTitle className="flex items-center gap-2">
                    <Coffee className="h-5 w-5" />
                    ☀️ Unlimited Breakfast
                    <Badge className="ml-2 bg-white text-orange-600">Special</Badge>
                  </CardTitle>
                  <CardDescription className="text-white/90">
                    {tiffinConfig.unlimitedBreakfast.description} • {tiffinConfig.unlimitedBreakfast.timings}
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-6">
                  <div className="flex items-start gap-3 mb-4">
                    <Checkbox
                      id="unlimited-breakfast"
                      checked={unlimitedBreakfast.enabled}
                      onCheckedChange={(checked) => setUnlimitedBreakfast(prev => ({ ...prev, enabled: checked }))}
                      data-testid="unlimited-breakfast-checkbox"
                    />
                    <div>
                      <label htmlFor="unlimited-breakfast" className="font-medium cursor-pointer">
                        Add Unlimited Breakfast
                      </label>
                      <p className="text-sm text-gray-600">
                        {breakfastPricing.symbol}{breakfastPricing.perPerson} per person • Available {tiffinConfig.unlimitedBreakfast.availableDays.join(' & ')}
                      </p>
                    </div>
                  </div>

                  {unlimitedBreakfast.enabled && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="space-y-4 pl-7"
                    >
                      <div className="grid md:grid-cols-2 gap-4">
                        <div>
                          <Label>Select Date</Label>
                          <Input
                            type="date"
                            value={unlimitedBreakfast.date}
                            onChange={(e) => setUnlimitedBreakfast(prev => ({ ...prev, date: e.target.value }))}
                            className="border-amber-200"
                            data-testid="breakfast-date"
                          />
                        </div>
                        <div>
                          <Label>Number of Guests</Label>
                          <div className="flex items-center gap-3">
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() => setUnlimitedBreakfast(prev => ({ ...prev, guests: Math.max(1, prev.guests - 1) }))}
                            >
                              <Minus className="h-4 w-4" />
                            </Button>
                            <span className="text-xl font-semibold w-12 text-center">{unlimitedBreakfast.guests}</span>
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() => setUnlimitedBreakfast(prev => ({ ...prev, guests: prev.guests + 1 }))}
                            >
                              <Plus className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </div>
                      <div className="p-3 bg-amber-50 rounded-lg">
                        <p className="text-sm font-medium text-amber-800">Includes:</p>
                        <p className="text-xs text-amber-700">{tiffinConfig.unlimitedBreakfast.includes.join(' • ')}</p>
                      </div>
                    </motion.div>
                  )}
                </CardContent>
              </Card>

              {/* Lunch Box Section */}
              {selectedWeek && currentWeekData && (
                <Card className="border-amber-200 shadow-lg">
                  <CardHeader className="bg-gradient-to-r from-amber-100 to-orange-100 rounded-t-lg">
                    <CardTitle className="flex items-center gap-2 text-[#5c1e1e]">
                      <Package className="h-5 w-5" />
                      Lunch Box (Mon-Fri)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-6 space-y-4">
                    {currentWeekData.days.map(day => (
                      <div key={day.date} className="p-4 border border-amber-100 rounded-lg">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <Checkbox
                              checked={lunchSelections[day.date]?.included || false}
                              onCheckedChange={(checked) => updateLunchSelection(day.date, 'included', checked)}
                            />
                            <span className="font-semibold">{day.name} ({day.displayDate})</span>
                          </div>
                        </div>
                        
                        {lunchSelections[day.date]?.included && (
                          <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="grid md:grid-cols-2 gap-4 pl-7"
                          >
                            <div>
                              <Label>Lunch Box Type</Label>
                              <Select
                                value={lunchSelections[day.date]?.lunchBox || ''}
                                onValueChange={(v) => updateLunchSelection(day.date, 'lunchBox', v)}
                              >
                                <SelectTrigger>
                                  <SelectValue placeholder="Select combo" />
                                </SelectTrigger>
                                <SelectContent>
                                  {lunchBoxOptions.map(opt => (
                                    <SelectItem key={opt.id} value={opt.id}>
                                      <span className="font-medium">{opt.name}</span> — {formatPrice(opt.price)}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              {/* Show selected combo description */}
                              {lunchSelections[day.date]?.lunchBox && (
                                <div className="mt-2 p-2.5 bg-amber-50 rounded-lg border border-amber-100">
                                  <p className="text-xs font-semibold text-[#5c1e1e] mb-0.5">
                                    {lunchBoxOptions.find(o => o.id === lunchSelections[day.date]?.lunchBox)?.name}
                                  </p>
                                  <p className="text-xs text-amber-700">
                                    {lunchBoxOptions.find(o => o.id === lunchSelections[day.date]?.lunchBox)?.description}
                                  </p>
                                </div>
                              )}
                            </div>
                            <div>
                              <Label>Pickup Time</Label>
                              <Select
                                value={lunchSelections[day.date]?.pickupTime || defaultPickupTime}
                                onValueChange={(v) => updateLunchSelection(day.date, 'pickupTime', v)}
                              >
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  {bookingRules.tiffin.pickupTimes.map(time => (
                                    <SelectItem key={time.id} value={time.id}>
                                      {time.label}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                          </motion.div>
                        )}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              {/* Heavy Brunch Section */}
              {selectedWeek && currentWeekData && (
                <Card className="border-amber-200 shadow-lg">
                  <CardHeader className="bg-gradient-to-r from-amber-100 to-orange-100 rounded-t-lg">
                    <CardTitle className="flex items-center gap-2 text-[#5c1e1e]">
                      <Utensils className="h-5 w-5" />
                      Heavy Brunch (Mon-Fri)
                    </CardTitle>
                    <p className="text-xs text-amber-700 mt-1">Tiffin-exclusive pricing — save more than dine-in!</p>
                  </CardHeader>
                  <CardContent className="pt-6 space-y-6">
                    {currentWeekData.days.map(day => (
                      <div key={day.date} className="border-b border-amber-100 pb-4 last:border-0">
                        <h4 className="font-semibold text-[#5c1e1e] mb-3">{day.name} ({day.displayDate})</h4>
                        <div className="space-y-3">
                          {heavyBrunchItems.map(item => {
                            const saving = item.menuPrice ? (item.menuPrice - item.price) : 0;
                            const savingPct = item.menuPrice ? Math.round((saving / item.menuPrice) * 100) : 0;
                            return (
                              <div key={item.id} className="flex items-center gap-3 p-3 rounded-xl hover:bg-amber-50 border border-transparent hover:border-amber-200 transition-all">
                                {/* Item Image */}
                                <BrunchItemImage name={item.name} />
                                {/* Item Details */}
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span className="font-semibold text-[#5c1e1e]">{item.name}</span>
                                    {saving > 0 && (
                                      <Badge className="bg-green-100 text-green-700 border-green-300 text-[10px] px-1.5 py-0" variant="outline">
                                        Save {formatPrice(saving)}
                                      </Badge>
                                    )}
                                  </div>
                                  {item.description && (
                                    <p className="text-xs text-gray-500 mt-0.5 truncate">{item.description}</p>
                                  )}
                                  <div className="flex items-center gap-2 mt-1">
                                    <span className="text-sm font-bold text-[#5c1e1e]">{formatPrice(item.price)}</span>
                                    {item.menuPrice && (
                                      <span className="text-xs text-gray-400 line-through">{formatPrice(item.menuPrice)}</span>
                                    )}
                                  </div>
                                </div>
                                {/* Controls */}
                                <div className="flex items-center gap-3 flex-shrink-0">
                                  <div className="flex items-center gap-1">
                                    <Checkbox
                                      id={`${day.date}-${item.id}-buttermilk`}
                                      checked={brunchSelections[day.date]?.[item.id]?.buttermilk || false}
                                      onCheckedChange={(checked) => updateBrunchSelection(day.date, item.id, 'buttermilk', checked)}
                                      disabled={!brunchSelections[day.date]?.[item.id]?.qty}
                                    />
                                    <label htmlFor={`${day.date}-${item.id}-buttermilk`} className="text-xs">+Buttermilk</label>
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <Checkbox
                                      id={`${day.date}-${item.id}-kokum`}
                                      checked={brunchSelections[day.date]?.[item.id]?.kokum || false}
                                      onCheckedChange={(checked) => updateBrunchSelection(day.date, item.id, 'kokum', checked)}
                                      disabled={!brunchSelections[day.date]?.[item.id]?.qty}
                                    />
                                    <label htmlFor={`${day.date}-${item.id}-kokum`} className="text-xs">+Kokum</label>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <Button
                                      variant="outline"
                                      size="icon"
                                      className="h-7 w-7"
                                      onClick={() => updateBrunchSelection(day.date, item.id, 'qty', Math.max(0, (brunchSelections[day.date]?.[item.id]?.qty || 0) - 1))}
                                    >
                                      <Minus className="h-3 w-3" />
                                    </Button>
                                    <span className="w-6 text-center font-semibold">{brunchSelections[day.date]?.[item.id]?.qty || 0}</span>
                                    <Button
                                      variant="outline"
                                      size="icon"
                                      className="h-7 w-7"
                                      onClick={() => updateBrunchSelection(day.date, item.id, 'qty', (brunchSelections[day.date]?.[item.id]?.qty || 0) + 1)}
                                    >
                                      <Plus className="h-3 w-3" />
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </div>

            {/* Sidebar - Summary */}
            <div className="lg:col-span-1">
              <div className="sticky top-24 space-y-6">
                <Card className="border-amber-200 shadow-lg">
                  <CardHeader className="bg-gradient-to-r from-[#5c1e1e] to-[#8b2c2c] text-white rounded-t-lg">
                    <CardTitle>Order Summary</CardTitle>
                  </CardHeader>
                  <CardContent className="pt-4 space-y-3">
                    <div className="space-y-2 text-sm">
                      <p><strong>Center:</strong> {currentCenter?.displayName || '—'}</p>
                      <p><strong>Name:</strong> {name || '—'}</p>
                      <p><strong>Mobile:</strong> {mobile || '—'}</p>
                      <p><strong>Week:</strong> {currentWeekData?.label || '—'}</p>
                    </div>

                    <div className="border-t pt-3 space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Lunch Total:</span>
                        <span>{formatPrice(calculateTotals.lunchTotal)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Brunch Total:</span>
                        <span>{formatPrice(calculateTotals.brunchTotal)}</span>
                      </div>
                      {unlimitedBreakfast.enabled && (
                        <div className="flex justify-between text-sm text-orange-600">
                          <span>Unlimited Breakfast:</span>
                          <span>{formatPrice(calculateTotals.breakfastTotal)}</span>
                        </div>
                      )}
                      {!isAustralia && calculateTotals.gst > 0 && (
                        <div className="flex justify-between text-sm text-gray-500">
                          <span>GST (5%):</span>
                          <span>{formatPrice(calculateTotals.gst)}</span>
                        </div>
                      )}
                      <div className="flex justify-between font-bold text-lg pt-2 border-t">
                        <span>Grand Total:</span>
                        <span className="text-[#5c1e1e]">{formatPrice(calculateTotals.grandTotal)}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Button
                  onClick={handleSubmit}
                  className="w-full bg-[#5c1e1e] hover:bg-[#8b2c2c] text-white py-6 text-lg"
                  disabled={!selectedCenter || !name || !mobile || calculateTotals.grandTotal === 0}
                  data-testid="tiffin-submit-btn"
                >
                  <MessageCircle className="h-5 w-5 mr-2" />
                  Send to WhatsApp
                </Button>
              </div>
            </div>
          </div>
        ) : (
          /* Review Section - Premium */
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="max-w-2xl mx-auto"
          >
            <Card className="border-0 shadow-2xl overflow-hidden">
              {/* Premium Header */}
              <div className="bg-gradient-to-r from-[#3a0f0f] via-[#5c1e1e] to-[#3a0f0f] p-6 text-center">
                <p className="text-amber-400 text-xs tracking-[0.3em] uppercase mb-1">Purnabramha</p>
                <h2 className="text-2xl font-playfair font-bold text-white mb-1">Tiffin Service</h2>
                <p className="text-amber-300/70 text-xs italic">World's First Intelligent Restaurant Chain</p>
                <div className="w-16 h-0.5 bg-amber-400 mx-auto mt-3" />
              </div>

              <CardContent className="pt-6 space-y-5 bg-gradient-to-b from-amber-50/50 to-white">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="bg-white p-3 rounded-lg border border-amber-100 shadow-sm">
                    <p className="text-amber-600 text-xs uppercase tracking-wider mb-1">Customer</p>
                    <p className="font-semibold text-[#5c1e1e]">{name}</p>
                    <p className="text-gray-500 text-xs mt-0.5">{mobile}</p>
                  </div>
                  <div className="bg-white p-3 rounded-lg border border-amber-100 shadow-sm">
                    <p className="text-amber-600 text-xs uppercase tracking-wider mb-1">Center</p>
                    <p className="font-semibold text-[#5c1e1e]">{currentCenter?.displayName}</p>
                  </div>
                  <div className="col-span-2 bg-white p-3 rounded-lg border border-amber-100 shadow-sm">
                    <p className="text-amber-600 text-xs uppercase tracking-wider mb-1">Week</p>
                    <p className="font-semibold text-[#5c1e1e]">{currentWeekData?.label}</p>
                  </div>
                </div>

                {/* Order Breakdown */}
                <div className="space-y-3">
                  <div className="bg-white p-3 rounded-lg border border-amber-100 shadow-sm">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Lunch Orders</span>
                      <span className="font-semibold text-[#5c1e1e]">{formatPrice(calculateTotals.lunchTotal)}</span>
                    </div>
                  </div>
                  <div className="bg-white p-3 rounded-lg border border-amber-100 shadow-sm">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Brunch Orders</span>
                      <span className="font-semibold text-[#5c1e1e]">{formatPrice(calculateTotals.brunchTotal)}</span>
                    </div>
                  </div>
                  {unlimitedBreakfast.enabled && (
                    <div className="bg-white p-3 rounded-lg border border-amber-100 shadow-sm">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Unlimited Breakfast ({unlimitedBreakfast.guests} guests)</span>
                        <span className="font-semibold text-orange-600">{formatPrice(calculateTotals.breakfastTotal)}</span>
                      </div>
                    </div>
                  )}
                  {!isAustralia && calculateTotals.gst > 0 && (
                    <div className="bg-white p-3 rounded-lg border border-amber-100 shadow-sm">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-500">GST (5%)</span>
                        <span className="text-gray-500">{formatPrice(calculateTotals.gst)}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Grand Total */}
                <div className="bg-gradient-to-r from-[#5c1e1e] to-[#8b2c2c] rounded-xl p-4 text-center">
                  <p className="text-amber-300 text-xs uppercase tracking-wider mb-1">Grand Total</p>
                  <p className="text-3xl font-bold text-white">{formatPrice(calculateTotals.grandTotal)}</p>
                </div>

                <div className="flex gap-3 pt-2">
                  <Button
                    variant="outline"
                    onClick={() => setShowReview(false)}
                    className="flex-1 border-amber-300 text-[#5c1e1e] hover:bg-amber-50"
                  >
                    Edit Order
                  </Button>
                  <Button
                    onClick={confirmBooking}
                    className="flex-1 bg-green-600 hover:bg-green-700 shadow-lg"
                    data-testid="tiffin-confirm-btn"
                  >
                    <MessageCircle className="h-5 w-5 mr-2" />
                    Send via WhatsApp
                  </Button>
                </div>

                <p className="text-center text-[10px] text-gray-400 italic">Powered by A.AI Technology</p>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </div>
    </div>
  );
};

// Brunch Item Image with menu item matching
const BRUNCH_IMAGE_MAP = {
  'Thalipith': { fallbackColor: 'from-amber-200 to-amber-400', initials: 'TP' },
  'Misal Pav': { fallbackColor: 'from-red-200 to-red-400', initials: 'MP' },
  'Shrikhanda Puri Bhaji': { fallbackColor: 'from-yellow-200 to-amber-300', initials: 'SP' },
  'Aloo Paratha': { fallbackColor: 'from-amber-100 to-yellow-300', initials: 'AP' },
  'Sabudana Khichadi': { fallbackColor: 'from-green-100 to-green-300', initials: 'SK' }
};

const BrunchItemImage = ({ name }) => {
  const [menuImage, setMenuImage] = useState(null);
  const fallback = BRUNCH_IMAGE_MAP[name] || { fallbackColor: 'from-gray-200 to-gray-400', initials: name.substring(0, 2).toUpperCase() };

  useEffect(() => {
    const API = process.env.REACT_APP_BACKEND_URL;
    fetch(`${API}/api/menu`)
      .then(res => res.json())
      .then(items => {
        const match = items.find(i => i.name.toLowerCase().includes(name.toLowerCase()) && i.image_url);
        if (match) setMenuImage(match.image_url);
      })
      .catch(() => {});
  }, [name]);

  if (menuImage) {
    return (
      <img
        src={menuImage}
        alt={name}
        className="w-14 h-14 rounded-lg object-cover border-2 border-amber-100 flex-shrink-0"
        onError={(e) => { e.target.style.display = 'none'; }}
      />
    );
  }

  return (
    <div className={`w-14 h-14 rounded-lg bg-gradient-to-br ${fallback.fallbackColor} flex items-center justify-center flex-shrink-0 border-2 border-white shadow-sm`}>
      <span className="text-white font-bold text-sm drop-shadow">{fallback.initials}</span>
    </div>
  );
};

export default Tiffin;
