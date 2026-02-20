import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Coffee, MessageCircle, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

const CENTERS = [
  { value: 'PB-HSR', label: 'PB-HSR', whatsapp: '919741399190', country: 'India', lunchPrice: 199, brunchAddon: 149 },
  { value: 'PB-Thane', label: 'PB-Thane', whatsapp: '919741399190', country: 'India', lunchPrice: 199, brunchAddon: 149 },
  { value: 'PB-SambhajiNagar', label: 'PB-SambhajiNagar', whatsapp: '919741399190', country: 'India', lunchPrice: 199, brunchAddon: 149 },
  { value: 'PB-Dombivli', label: 'PB-Dombivli', whatsapp: '919741399190', country: 'India', lunchPrice: 199, brunchAddon: 149 },
  { value: 'PB-Hinjawadi', label: 'PB-Hinjawadi', whatsapp: '919741399190', country: 'India', lunchPrice: 199, brunchAddon: 149 },
  { value: 'PB-Kalyan', label: 'PB-Kalyan', whatsapp: '919741399190', country: 'India', lunchPrice: 199, brunchAddon: 149 },
  { value: 'PB-Perth', label: 'PB-Perth', whatsapp: '61412345678', country: 'Australia', lunchPrice: 15.99, brunchAddon: 5.99 }
];

const PICKUP_TIMES = ['12:00 PM', '12:30 PM', '1:00 PM', '1:30 PM', '6:00 PM'];

const BRUNCH_ITEMS = [
  { name: 'Thalipith', priceInr: 199, priceAud: 8.99 },
  { name: 'Misal Pav', priceInr: 199, priceAud: 14.99 },
  { name: 'Shrikhanda Puri Bhaji', priceInr: 249, priceAud: 17.99 },
  { name: 'Aloo Paratha', priceInr: 149, priceAud: 7.99 },
  { name: 'Sabudana Khichadi', priceInr: 169, priceAud: 12.99 }
];

const DRINK_ADDONS = [
  { name: 'Buttermilk', priceInr: 149, priceAud: 7.99 },
  { name: 'Kokum', priceInr: 149, priceAud: 8.99 }
];

// Generate weeks
const generateWeeks = () => {
  const weeks = [];
  const today = new Date();
  const dayOfWeek = today.getDay();
  const daysUntilMonday = dayOfWeek === 0 ? 1 : (8 - dayOfWeek) % 7 || 7;
  
  let startDate = new Date(today);
  startDate.setDate(today.getDate() + daysUntilMonday);
  
  for (let i = 0; i < 3; i++) {
    const weekStart = new Date(startDate);
    weekStart.setDate(startDate.getDate() + (i * 7));
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 4); // Mon-Fri
    
    const days = [];
    for (let d = 0; d < 5; d++) {
      const day = new Date(weekStart);
      day.setDate(weekStart.getDate() + d);
      days.push({
        date: day,
        dayName: day.toLocaleDateString('en-US', { weekday: 'long' }),
        formatted: day.toLocaleDateString('en-US', { day: 'numeric', month: 'short' })
      });
    }
    
    weeks.push({
      label: `Week ${i + 1} (${weekStart.toLocaleDateString('en-US', { day: 'numeric', month: 'short' })} – ${weekEnd.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' })})`,
      days
    });
  }
  return weeks;
};

const Tiffin = () => {
  const [center, setCenter] = useState('');
  const [name, setName] = useState('');
  const [mobile, setMobile] = useState('');
  const [weekIndex, setWeekIndex] = useState(0);
  const [defaultPickupTime, setDefaultPickupTime] = useState('12:00 PM');
  const [lunchExpanded, setLunchExpanded] = useState(true);
  const [brunchExpanded, setBrunchExpanded] = useState(true);
  
  const weeks = useMemo(() => generateWeeks(), []);
  const selectedWeek = weeks[weekIndex];
  
  const selectedCenter = useMemo(() => 
    CENTERS.find(c => c.value === center), 
    [center]
  );
  
  const isPerth = center === 'PB-Perth';
  const currency = isPerth ? '$' : '₹';
  
  // Lunch days state
  const [lunchDays, setLunchDays] = useState(
    selectedWeek?.days.map(() => ({
      included: true,
      pickupTime: '12:00 PM'
    })) || []
  );
  
  // Brunch items state per day
  const [brunchDays, setBrunchDays] = useState(
    selectedWeek?.days.map(() => 
      BRUNCH_ITEMS.map(() => ({
        selected: false,
        addon: 'Buttermilk'
      }))
    ) || []
  );
  
  // Reset when week or center changes
  useEffect(() => {
    if (selectedWeek) {
      setLunchDays(selectedWeek.days.map(() => ({
        included: true,
        pickupTime: defaultPickupTime
      })));
      setBrunchDays(selectedWeek.days.map(() => 
        BRUNCH_ITEMS.map(() => ({
          selected: false,
          addon: 'Buttermilk'
        }))
      ));
    }
  }, [weekIndex, center, selectedWeek, defaultPickupTime]);
  
  // Calculate totals
  const calculations = useMemo(() => {
    if (!selectedCenter) return { lunchTotal: 0, brunchTotal: 0, grandTotal: 0 };
    
    const lunchPrice = selectedCenter.lunchPrice;
    const lunchDaysCount = lunchDays.filter(d => d.included).length;
    const lunchTotal = lunchDaysCount * lunchPrice;
    
    let brunchTotal = 0;
    brunchDays.forEach((dayItems, dayIndex) => {
      if (dayItems) {
        dayItems.forEach((item, itemIndex) => {
          if (item.selected) {
            const brunchItem = BRUNCH_ITEMS[itemIndex];
            const itemPrice = isPerth ? brunchItem.priceAud : brunchItem.priceInr;
            const addon = DRINK_ADDONS.find(a => a.name === item.addon);
            const addonPrice = addon ? (isPerth ? addon.priceAud : addon.priceInr) : 0;
            brunchTotal += itemPrice + addonPrice;
          }
        });
      }
    });
    
    return {
      lunchTotal,
      brunchTotal,
      grandTotal: lunchTotal + brunchTotal
    };
  }, [lunchDays, brunchDays, selectedCenter, isPerth]);
  
  const handleLunchDayChange = (dayIndex, field, value) => {
    setLunchDays(prev => {
      const updated = [...prev];
      updated[dayIndex] = { ...updated[dayIndex], [field]: value };
      return updated;
    });
  };
  
  const handleBrunchChange = (dayIndex, itemIndex, field, value) => {
    setBrunchDays(prev => {
      const updated = [...prev];
      if (!updated[dayIndex]) updated[dayIndex] = BRUNCH_ITEMS.map(() => ({ selected: false, addon: 'Buttermilk' }));
      updated[dayIndex][itemIndex] = { ...updated[dayIndex][itemIndex], [field]: value };
      return updated;
    });
  };
  
  const handleSubmit = () => {
    if (!center) {
      toast.error('Please select a center');
      return;
    }
    if (!name.trim()) {
      toast.error('Please enter your name');
      return;
    }
    if (!mobile.trim() || mobile.length < 10) {
      toast.error('Please enter a valid mobile number');
      return;
    }
    
    let message = `🍱 *PURNABRAMHA TIFFIN BOOKING*\n\n`;
    message += `📍 *Center:* ${selectedCenter.label}\n`;
    message += `👤 *Name:* ${name}\n`;
    message += `📱 *Mobile:* ${mobile}\n`;
    message += `📅 *Week:* ${selectedWeek.label}\n\n`;
    
    message += `*--- LUNCH BOX (Mon-Fri) ---*\n`;
    selectedWeek.days.forEach((day, i) => {
      if (lunchDays[i]?.included) {
        message += `${day.dayName} (${day.formatted}): Roti combo @ ${lunchDays[i].pickupTime}\n`;
      } else {
        message += `${day.dayName} (${day.formatted}): Skipped\n`;
      }
    });
    
    message += `\n*--- HEAVY BRUNCH ---*\n`;
    selectedWeek.days.forEach((day, i) => {
      const dayBrunchItems = brunchDays[i]?.filter((item, idx) => item.selected)
        .map((item, idx) => {
          const originalIdx = brunchDays[i].findIndex((bi, bidx) => bi === item || (bi.selected && bidx === idx));
          const brunchItem = BRUNCH_ITEMS.find((_, bidx) => brunchDays[i][bidx] === item) || BRUNCH_ITEMS[idx];
          return `${brunchItem?.name || 'Item'} + ${item.addon}`;
        });
      
      if (dayBrunchItems && dayBrunchItems.length > 0) {
        message += `${day.dayName}: ${dayBrunchItems.join(', ')}\n`;
      }
    });
    
    message += `\n*--- TOTALS ---*\n`;
    message += `Lunch Total: ${currency}${calculations.lunchTotal.toFixed(2)}\n`;
    message += `Brunch Total: ${currency}${calculations.brunchTotal.toFixed(2)}\n`;
    message += `*Grand Total: ${currency}${calculations.grandTotal.toFixed(2)}*\n`;
    message += `\n_Sent via Purnabramha App_`;
    
    const encodedMessage = encodeURIComponent(message);
    const whatsappUrl = `https://wa.me/${selectedCenter.whatsapp}?text=${encodedMessage}`;
    
    window.open(whatsappUrl, '_blank');
    toast.success('Opening WhatsApp to confirm your order');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[hsl(30,20%,97%)] to-white">
      <div className="container mx-auto px-4 lg:px-8 py-8 lg:py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <Coffee className="h-12 w-12 mx-auto text-primary mb-4" />
          <h1 className="font-playfair text-3xl lg:text-5xl font-bold text-foreground mb-3" data-testid="tiffin-title">
            Tiffin & Heavy Brunch Booking
          </h1>
          <p className="text-foreground/70 font-manrope">
            Weekly lunch box subscription with optional heavy brunch add-ons
          </p>
        </motion.div>

        {/* Perth Notice */}
        {isPerth && (
          <Card className="mb-6 border-amber-300 bg-amber-50 max-w-4xl mx-auto">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
                <p className="text-sm text-amber-800">
                  <strong>Christmas & New Year Notice:</strong> Tiffin service for PB-Perth is paused from 15 December to 10 January.
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {/* Left Column - Customer Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Customer Info Card */}
            <Card>
              <CardContent className="p-6 space-y-4">
                <div>
                  <Label htmlFor="center">Center</Label>
                  <Select value={center} onValueChange={setCenter}>
                    <SelectTrigger id="center" data-testid="center-select">
                      <SelectValue placeholder="Select Center" />
                    </SelectTrigger>
                    <SelectContent>
                      {CENTERS.map(c => (
                        <SelectItem key={c.value} value={c.value}>
                          {c.label} ({c.country})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="name">Name</Label>
                    <Input
                      id="name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Your name"
                      data-testid="name-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="mobile">Mobile</Label>
                    <Input
                      id="mobile"
                      type="tel"
                      value={mobile}
                      onChange={(e) => setMobile(e.target.value)}
                      placeholder="+91 / +61"
                      data-testid="mobile-input"
                    />
                  </div>
                </div>
                
                <div>
                  <Label htmlFor="week">Select Week</Label>
                  <Select value={weekIndex.toString()} onValueChange={(v) => setWeekIndex(parseInt(v))}>
                    <SelectTrigger id="week" data-testid="week-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {weeks.map((week, i) => (
                        <SelectItem key={i} value={i.toString()}>
                          {week.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {selectedCenter && (
                  <p className="text-sm text-primary font-medium">
                    Lunch Box: {currency}{selectedCenter.lunchPrice.toFixed(2)} per day
                  </p>
                )}
                
                <div>
                  <Label htmlFor="defaultPickup">Default Pickup Time</Label>
                  <Select value={defaultPickupTime} onValueChange={setDefaultPickupTime}>
                    <SelectTrigger id="defaultPickup">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PICKUP_TIMES.map(time => (
                        <SelectItem key={time} value={time}>{time}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <p className="text-xs text-red-600">
                  Changing center or week will clear selections (to apply correct pricing).
                </p>
              </CardContent>
            </Card>
            
            {/* Lunch Box Section */}
            <Card>
              <CardHeader 
                className="cursor-pointer flex flex-row items-center justify-between py-4"
                onClick={() => setLunchExpanded(!lunchExpanded)}
              >
                <CardTitle className="text-lg">Lunch Box (Mon–Fri)</CardTitle>
                {lunchExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
              </CardHeader>
              {lunchExpanded && (
                <CardContent className="pt-0">
                  <div className="space-y-4">
                    {selectedWeek?.days.map((day, i) => (
                      <div key={i} className="p-3 bg-muted/30 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <strong className="text-sm">{day.dayName} ({day.formatted})</strong>
                          <div className="flex items-center gap-2">
                            <Checkbox
                              id={`lunch-${i}`}
                              checked={lunchDays[i]?.included || false}
                              onCheckedChange={(checked) => handleLunchDayChange(i, 'included', checked)}
                            />
                            <Label htmlFor={`lunch-${i}`} className="text-xs">Include</Label>
                          </div>
                        </div>
                        {lunchDays[i]?.included && (
                          <Select
                            value={lunchDays[i]?.pickupTime || '12:00 PM'}
                            onValueChange={(v) => handleLunchDayChange(i, 'pickupTime', v)}
                          >
                            <SelectTrigger className="h-8 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {PICKUP_TIMES.map(time => (
                                <SelectItem key={time} value={time}>{time}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              )}
            </Card>
            
            {/* Heavy Brunch Section */}
            <Card>
              <CardHeader 
                className="cursor-pointer flex flex-row items-center justify-between py-4"
                onClick={() => setBrunchExpanded(!brunchExpanded)}
              >
                <CardTitle className="text-lg">Heavy Brunch (Mon–Fri)</CardTitle>
                {brunchExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
              </CardHeader>
              {brunchExpanded && selectedCenter && (
                <CardContent className="pt-0">
                  <div className="space-y-4">
                    {selectedWeek?.days.map((day, dayIndex) => (
                      <div key={dayIndex} className="p-3 bg-muted/30 rounded-lg">
                        <strong className="text-sm block mb-2">{day.dayName} ({day.formatted})</strong>
                        <div className="space-y-2">
                          {BRUNCH_ITEMS.map((item, itemIndex) => {
                            const price = isPerth ? item.priceAud : item.priceInr;
                            return (
                              <div key={itemIndex} className="flex items-center gap-2 flex-wrap">
                                <Checkbox
                                  id={`brunch-${dayIndex}-${itemIndex}`}
                                  checked={brunchDays[dayIndex]?.[itemIndex]?.selected || false}
                                  onCheckedChange={(checked) => handleBrunchChange(dayIndex, itemIndex, 'selected', checked)}
                                />
                                <Label htmlFor={`brunch-${dayIndex}-${itemIndex}`} className="text-xs flex-1">
                                  {item.name} - {currency}{price.toFixed(2)}
                                </Label>
                                {brunchDays[dayIndex]?.[itemIndex]?.selected && (
                                  <Select
                                    value={brunchDays[dayIndex]?.[itemIndex]?.addon || 'Buttermilk'}
                                    onValueChange={(v) => handleBrunchChange(dayIndex, itemIndex, 'addon', v)}
                                  >
                                    <SelectTrigger className="h-7 w-32 text-xs">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {DRINK_ADDONS.map(addon => (
                                        <SelectItem key={addon.name} value={addon.name}>
                                          {addon.name} +{currency}{(isPerth ? addon.priceAud : addon.priceInr).toFixed(0)}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              )}
            </Card>
          </div>
          
          {/* Right Column - Summary */}
          <div className="lg:col-span-1">
            <Card className="sticky top-24">
              <CardHeader>
                <CardTitle>Order Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p><strong>Center:</strong> {selectedCenter?.label || '—'}</p>
                <p><strong>Name:</strong> {name || '—'}</p>
                <p><strong>Mobile:</strong> {mobile || '—'}</p>
                <p><strong>Week:</strong> {selectedWeek?.label}</p>
                
                <hr className="my-3" />
                
                <div className="space-y-2">
                  {selectedWeek?.days.map((day, i) => (
                    <div key={i}>
                      <strong className="text-xs">{day.dayName}</strong>
                      <p className="text-xs text-muted-foreground">
                        Lunch: {lunchDays[i]?.included ? `Roti combo @ ${lunchDays[i]?.pickupTime}` : 'Skipped'}
                      </p>
                    </div>
                  ))}
                </div>
                
                <hr className="my-3" />
                
                <div className="space-y-1">
                  <p><strong>Lunch Total:</strong> {currency}{calculations.lunchTotal.toFixed(2)}</p>
                  <p><strong>Brunch Total:</strong> {currency}{calculations.brunchTotal.toFixed(2)}</p>
                  <p className="text-lg font-bold text-primary">
                    <strong>Grand Total:</strong> {currency}{calculations.grandTotal.toFixed(2)}
                  </p>
                </div>
                
                <div className="pt-4 space-y-2">
                  <Button
                    onClick={handleSubmit}
                    className="w-full rounded-full bg-[hsl(145,60%,40%)] hover:bg-[hsl(145,60%,35%)]"
                    data-testid="send-whatsapp-btn"
                  >
                    <MessageCircle className="mr-2 h-4 w-4" />
                    Send to WhatsApp
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => {
                      setCenter('');
                      setName('');
                      setMobile('');
                      setWeekIndex(0);
                    }}
                  >
                    Reset
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Tiffin;
