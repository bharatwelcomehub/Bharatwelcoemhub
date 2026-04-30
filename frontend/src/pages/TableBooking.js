import { useState, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Calendar, Clock, Users, MapPin, Phone, MessageCircle, ChefHat, Leaf, Plus, Minus, ShoppingCart, AlertCircle, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import axios from 'axios';

import centersData from '@/config/centers.json';
import bookingRules from '@/config/booking-rules.json';
import indiaMenus from '@/config/menus-india.json';
import perthMenus from '@/config/menus-perth.json';

const API = process.env.REACT_APP_BACKEND_URL;

const TableBooking = () => {
  const [searchParams] = useSearchParams();
  const urlType = searchParams.get('type') || '';
  const [selectedRegion, setSelectedRegion] = useState('');
  const [selectedCenter, setSelectedCenter] = useState('');
  const [bookingDate, setBookingDate] = useState('');
  const [selectedTimeSlot, setSelectedTimeSlot] = useState('');
  const [serviceType, setServiceType] = useState('');
  const [guestCount, setGuestCount] = useState('2');
  const [celebration, setCelebration] = useState('none');
  const [guestType, setGuestType] = useState('');
  const [bookingType, setBookingType] = useState(urlType.includes('banana-leaf') ? 'banana-leaf' : 'regular');
  const [isCorporate, setIsCorporate] = useState(urlType === 'banana-leaf-corporate');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [specialRequests, setSpecialRequests] = useState('');
  const [cart, setCart] = useState({});
  const [showReview, setShowReview] = useState(false);
  const [dbMenuItems, setDbMenuItems] = useState([]);
  const [centerTimeSlots, setCenterTimeSlots] = useState(null);

  useEffect(() => {
    const fetchMenu = async () => {
      try { const response = await axios.get(`${API}/api/menu`); setDbMenuItems(response.data); } catch (err) { console.log('Using fallback JSON menu'); }
    };
    fetchMenu();
  }, []);

  // Fetch center-specific time slots when center changes
  useEffect(() => {
    if (!selectedCenter) { setCenterTimeSlots(null); return; }
    const fetchSlots = async () => {
      try {
        const res = await axios.get(`${API}/api/center-timeslots/${selectedCenter}`);
        setCenterTimeSlots(res.data.slots);
      } catch { setCenterTimeSlots(null); }
    };
    fetchSlots();
  }, [selectedCenter]);

  const allCenters = useMemo(() => [...centersData.india, ...centersData.australia], []);
  const filteredCenters = useMemo(() => { if (!selectedRegion) return []; return selectedRegion === 'india' ? centersData.india : centersData.australia; }, [selectedRegion]);
  const currentCenter = useMemo(() => allCenters.find(c => c.id === selectedCenter), [selectedCenter, allCenters]);

  const menuData = useMemo(() => {
    if (!currentCenter) return null;
    const isAustralia = currentCenter.country === 'Australia';
    const jsonFallback = isAustralia ? perthMenus : indiaMenus;
    if (dbMenuItems.length > 0) {
      const categoryMap = {};
      dbMenuItems.forEach(item => {
        if (!item.is_available) return;
        const price = isAustralia ? (item.price_aud || 0) : (item.price_inr || item.price || 0);
        if (price <= 0) return;
        if (!categoryMap[item.category]) { categoryMap[item.category] = { id: item.category.toLowerCase().replace(/[^a-z0-9]/g, '-'), name: item.category, items: [] }; }
        categoryMap[item.category].items.push({ id: item.id, name: item.name, price, isVeg: item.is_veg ?? true, description: item.description, image_url: item.image_url });
      });
      const categories = Object.values(categoryMap);
      if (categories.length > 0) return { currency: isAustralia ? 'AUD' : 'INR', currencySymbol: isAustralia ? '$' : '₹', categories };
    }
    return jsonFallback;
  }, [currentCenter, dbMenuItems]);

  const showMenuSection = serviceType === 'pickup' || currentCenter?.country === 'Australia';
  const getMinDate = () => { const now = new Date(); now.setHours(now.getHours() + bookingRules.tableBooking.minAdvanceHours); return now.toISOString().split('T')[0]; };
  const getMaxDate = () => { const now = new Date(); now.setDate(now.getDate() + bookingRules.tableBooking.maxAdvanceDays); return now.toISOString().split('T')[0]; };

  // Check if booking is less than 1 hour from now
  const isUrgentBooking = useMemo(() => {
    if (!bookingDate || !selectedTimeSlot) return false;
    const timeSlot = (centerTimeSlots || bookingRules.tableBooking.timeSlots).find(t => t.id === selectedTimeSlot);
    if (!timeSlot) return false;
    
    // Parse the time slot (e.g., "12:00 PM - 1:00 PM" or "12:00")
    const timeStr = timeSlot.label.split(' - ')[0] || timeSlot.id;
    const [hours, minutes] = timeStr.replace(/ (AM|PM)/i, '').split(':').map(Number);
    const isPM = timeStr.toUpperCase().includes('PM');
    
    let bookingHour = hours;
    if (isPM && hours !== 12) bookingHour += 12;
    if (!isPM && hours === 12) bookingHour = 0;
    
    const bookingDateTime = new Date(bookingDate);
    bookingDateTime.setHours(bookingHour, minutes || 0, 0, 0);
    
    const now = new Date();
    const diffMs = bookingDateTime - now;
    const diffHours = diffMs / (1000 * 60 * 60);
    
    return diffHours > 0 && diffHours < 1;
  }, [bookingDate, selectedTimeSlot]);

  const updateCart = (itemId, itemName, price, delta) => {
    setCart(prev => {
      const current = prev[itemId] || { name: itemName, price, qty: 0 };
      const newQty = Math.max(0, current.qty + delta);
      if (newQty === 0) { const { [itemId]: _, ...rest } = prev; return rest; }
      return { ...prev, [itemId]: { ...current, qty: newQty } };
    });
  };

  const cartTotal = useMemo(() => Object.values(cart).reduce((sum, item) => sum + (item.price * item.qty), 0), [cart]);
  const cartItemCount = useMemo(() => Object.values(cart).reduce((sum, item) => sum + item.qty, 0), [cart]);
  const formatPrice = (price) => { if (!menuData) return price; return `${menuData.currencySymbol}${price.toFixed(2)}`; };

  const generateWhatsAppMessage = () => {
    const timeSlotLabel = (centerTimeSlots || bookingRules.tableBooking.timeSlots).find(t => t.id === selectedTimeSlot)?.label || '';
    const celebrationLabel = bookingRules.tableBooking.celebrationOptions.find(c => c.id === celebration)?.label || '';
    let message = `🪔 *PURNABRAMHA TABLE BOOKING* 🪔\n━━━━━━━━━━━━━━━━\n\n`;
    if (bookingType === 'banana-leaf') {
      message = `🍌🪔 *BANANA LEAF THALI BOOKING* 🪔🍌\n━━━━━━━━━━━━━━━━\n\n`;
      message += `🍃 *Banana Leaf Thali — Unlimited*\n`;
      message += `💰 ${currentCenter?.country === 'Australia' ? '$40/person' : '₹490/person'}\n`;
      if (isCorporate) message += `🏢 *CORPORATE GROUP BOOKING*\n`;
      message += `\n`;
    }
    message += `📍 ${currentCenter?.displayName}\n📅 ${bookingDate} ⏰ ${timeSlotLabel}\n`;
    message += `🍽️ ${serviceType === 'dine-in' ? 'Dine In' : 'Pickup'} | 👥 ${guestCount} guests\n`;
    if (celebration !== 'none') message += `🎉 ${celebrationLabel}\n`;
    message += `\n👤 *${name}* | 📞 ${phone}\n`;
    if (email) message += `📧 ${email}\n`;
    if (bookingType !== 'banana-leaf' && cartItemCount > 0) {
      message += `\n🛒 *Pre-Order:*\n`;
      Object.entries(cart).forEach(([id, item]) => { message += `• ${item.name} ×${item.qty} — ${formatPrice(item.price * item.qty)}\n`; });
      message += `💰 *Total: ${formatPrice(cartTotal)}*\n`;
    }
    if (specialRequests) message += `\n📝 ${specialRequests}\n`;
    message += `\n_Confirmation pending manager's reply_`;
    return encodeURIComponent(message);
  };

  const handleSubmit = () => {
    if (!selectedCenter || !bookingDate || !selectedTimeSlot || !serviceType || !name || !phone) { toast.error('Please fill all required fields'); return; }
    setShowReview(true);
  };
  const confirmBooking = () => {
    const message = generateWhatsAppMessage();
    const whatsappNumber = currentCenter?.whatsapp.replace(/[^0-9]/g, '');
    window.open(`https://wa.me/${whatsappNumber}?text=${message}`, '_blank');
    toast.success('Redirecting to WhatsApp...');
  };
  const resetForm = () => {
    setSelectedRegion(''); setSelectedCenter(''); setBookingDate(''); setSelectedTimeSlot('');
    setServiceType(''); setGuestCount('2'); setCelebration('none'); setGuestType('');
    setName(''); setPhone(''); setEmail(''); setSpecialRequests(''); setCart({}); setShowReview(false);
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
            <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-4">Reserve Your Table</p>
            <h1 className="font-heading text-5xl md:text-6xl font-medium text-[#2D1810] mb-4 tracking-tight" data-testid="table-booking-title">
              Table <span className="text-gold-shimmer">Booking</span>
            </h1>
            <p className="text-lg text-[#5C4A3A] font-body">Reserve your table at any Purnabramha center across India & Australia</p>
            <div className="mt-4 flex items-center justify-center gap-2 text-[#B8962E]/60 text-sm font-body">
              <Clock className="h-4 w-4" /><span>Minimum 2 hours advance booking required</span>
            </div>
          </motion.div>
        </div>
      </section>

      <div className="container mx-auto px-6 lg:px-12 py-10">
        {/* Important Booking Alert - Always Visible */}
        <motion.div 
          initial={{ opacity: 0, y: -10 }} 
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <Alert className="bg-red-50 border-2 border-red-500 rounded-none">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            <AlertTitle className="text-red-700 font-heading font-semibold text-lg">
              Important Booking Information
            </AlertTitle>
            <AlertDescription className="text-red-700 font-body mt-2 space-y-2">
              <p className="font-semibold">
                ⚠️ Sending a WhatsApp message does NOT confirm your booking.
              </p>
              <p>
                Booking is confirmed <strong>ONLY</strong> after the Center Manager replies on WhatsApp. 
                If the restaurant is full house or the manager is busy, bookings may not be accepted.
              </p>
            </AlertDescription>
          </Alert>
        </motion.div>

        {/* Urgent Booking Alert - Only when booking is less than 1 hour away */}
        {isUrgentBooking && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }} 
            animate={{ opacity: 1, scale: 1 }}
            className="mb-6"
          >
            <Alert className="bg-orange-50 border-2 border-orange-500 rounded-none">
              <AlertCircle className="h-5 w-5 text-orange-600 animate-pulse" />
              <AlertTitle className="text-orange-700 font-heading font-semibold text-lg">
                ⏰ Urgent Booking - Less Than 1 Hour Away!
              </AlertTitle>
              <AlertDescription className="text-orange-700 font-body mt-2 space-y-2">
                <p className="font-semibold">
                  For bookings less than 1 hour from current time, confirmation from Center Manager is MANDATORY.
                </p>
                <p>
                  🚫 <strong>If you have NOT received a confirmation message, DO NOT visit the restaurant.</strong>
                </p>
                <p>
                  No reply means the booking is NOT available for that time slot.
                </p>
              </AlertDescription>
            </Alert>
          </motion.div>
        )}

        {!showReview ? (
          <div className="grid lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-6">
              {/* Step 1 */}
              <div className="pearl-surface overflow-hidden">
                <div className="bg-[#F8F5F0] border-b border-[#E8DFD0] p-4"><h3 className="flex items-center gap-2 text-[#B8962E] font-heading font-medium"><MapPin className="h-5 w-5" /> Step 1: Select Region & Center</h3></div>
                <div className="p-6 space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div><Label className={labelCls}>Region *</Label><Select value={selectedRegion} onValueChange={(v) => { setSelectedRegion(v); setSelectedCenter(''); }}><SelectTrigger className={inputCls} data-testid="region-select"><SelectValue placeholder="Select Region" /></SelectTrigger><SelectContent className="bg-white border-[#E8DFD0]"><SelectItem value="india">India</SelectItem><SelectItem value="australia">Australia</SelectItem></SelectContent></Select></div>
                    <div><Label className={labelCls}>Center *</Label><Select value={selectedCenter} onValueChange={setSelectedCenter} disabled={!selectedRegion}><SelectTrigger className={inputCls} data-testid="center-select"><SelectValue placeholder="Select Center" /></SelectTrigger><SelectContent className="bg-white border-[#E8DFD0]">{filteredCenters.map(c => <SelectItem key={c.id} value={c.id}>{c.displayName}</SelectItem>)}</SelectContent></Select></div>
                  </div>
                  {currentCenter && <div className="p-2 bg-[#F8F5F0] border border-[#E8DFD0] flex items-center gap-2 text-sm text-[#5C4A3A] font-body"><Phone className="h-4 w-4 text-[#B8962E]/60" /><span>{currentCenter.phone}</span></div>}
                </div>
              </div>

              {/* Booking Type — Banana Leaf Thali Option */}
              <div className="pearl-surface overflow-hidden" data-testid="booking-type-section">
                <div className="bg-[#F8F5F0] border-b border-[#E8DFD0] p-4"><h3 className="flex items-center gap-2 text-[#B8962E] font-heading font-medium"><Leaf className="h-5 w-5" /> Booking Type</h3></div>
                <div className="p-4">
                  <div className="grid md:grid-cols-2 gap-3">
                    <button
                      onClick={() => { setBookingType('regular'); setIsCorporate(false); }}
                      className={`p-4 rounded-lg border-2 text-left transition-all ${bookingType === 'regular' ? 'border-[#B8962E] bg-[#B8962E]/5' : 'border-[#E8DFD0] hover:border-[#B8962E]/30'}`}
                      data-testid="type-regular"
                    >
                      <p className="font-heading text-sm text-[#3D2314]">Regular Booking</p>
                      <p className="text-[10px] text-[#7A6F65] font-body mt-1">Dine-in or Pickup from our menu</p>
                    </button>
                    <button
                      onClick={() => { setBookingType('banana-leaf'); setServiceType('dine-in'); }}
                      className={`p-4 rounded-lg border-2 text-left transition-all relative ${bookingType === 'banana-leaf' ? 'border-[#2E7D32] bg-[#2E7D32]/5' : 'border-[#E8DFD0] hover:border-[#2E7D32]/30'}`}
                      data-testid="type-banana-leaf"
                    >
                      <span className="absolute -top-2 right-3 bg-[#2E7D32] text-white text-[8px] px-2 py-0.5 rounded-full font-body font-bold">NEW</span>
                      <p className="font-heading text-sm text-[#3D2314] flex items-center gap-1"><Leaf className="w-3.5 h-3.5 text-[#2E7D32]" /> Banana Leaf Thali</p>
                      <p className="text-[10px] text-[#7A6F65] font-body mt-1">Unlimited Maharashtrian thali | Tue, Wed, Thu | Lunch only</p>
                      <p className="text-xs text-[#2E7D32] font-body font-semibold mt-1">{selectedRegion === 'australia' ? '$40/person' : '₹490/person'}</p>
                    </button>
                  </div>
                  {bookingType === 'banana-leaf' && (
                    <div className="mt-3 flex items-center gap-3">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" checked={isCorporate} onChange={(e) => setIsCorporate(e.target.checked)} className="accent-[#2E7D32] w-4 h-4" />
                        <span className="text-xs font-body text-[#3D2314]">Corporate Group Booking (20+ guests)</span>
                      </label>
                    </div>
                  )}
                </div>
              </div>

              {/* Step 2 */}
              <div className="pearl-surface overflow-hidden">
                <div className="bg-[#F8F5F0] border-b border-[#E8DFD0] p-4"><h3 className="flex items-center gap-2 text-[#B8962E] font-heading font-medium"><Calendar className="h-5 w-5" /> Step 2: Date & Time</h3></div>
                <div className="p-6 space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div><Label className={labelCls}>Date *</Label><Input type="date" value={bookingDate} onChange={(e) => setBookingDate(e.target.value)} min={getMinDate()} max={getMaxDate()} className={inputCls} data-testid="booking-date" /></div>
                    <div><Label className={labelCls}>Time Slot *</Label><Select value={selectedTimeSlot} onValueChange={setSelectedTimeSlot}><SelectTrigger className={inputCls} data-testid="time-slot-select"><SelectValue placeholder="Select Time" /></SelectTrigger><SelectContent className="bg-white border-[#E8DFD0]">{(centerTimeSlots || bookingRules.tableBooking.timeSlots).map(s => <SelectItem key={s.id} value={s.id}>{s.label}</SelectItem>)}</SelectContent></Select></div>
                  </div>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div><Label className={labelCls}>Service Type *</Label><Select value={serviceType} onValueChange={setServiceType}><SelectTrigger className={inputCls} data-testid="service-type-select"><SelectValue placeholder="Select Service" /></SelectTrigger><SelectContent className="bg-white border-[#E8DFD0]"><SelectItem value="dine-in">Dine In</SelectItem><SelectItem value="pickup">Pickup</SelectItem></SelectContent></Select></div>
                    <div><Label className={labelCls}>Guests *</Label><Select value={guestCount} onValueChange={setGuestCount}><SelectTrigger className={inputCls} data-testid="guest-count-select"><SelectValue /></SelectTrigger><SelectContent className="bg-white border-[#E8DFD0]">{[1,2,3,4,5,6,7,8,9,10,15,20,25,30].map(n => <SelectItem key={n} value={n.toString()}>{n} {n===1?'Guest':'Guests'}</SelectItem>)}</SelectContent></Select></div>
                  </div>
                </div>
              </div>

              {/* Step 3 */}
              <div className="pearl-surface overflow-hidden">
                <div className="bg-[#F8F5F0] border-b border-[#E8DFD0] p-4"><h3 className="flex items-center gap-2 text-[#B8962E] font-heading font-medium"><Users className="h-5 w-5" /> Step 3: Guest Details</h3></div>
                <div className="p-6 space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div><Label className={labelCls}>Name *</Label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your full name" className={inputCls} data-testid="guest-name" /></div>
                    <div><Label className={labelCls}>Phone *</Label><Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Your phone number" className={inputCls} data-testid="guest-phone" /></div>
                  </div>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div><Label className={labelCls}>Email (Optional)</Label><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="your@email.com" className={inputCls} data-testid="guest-email" /></div>
                    <div><Label className={labelCls}>Celebrating?</Label><Select value={celebration} onValueChange={setCelebration}><SelectTrigger className={inputCls} data-testid="celebration-select"><SelectValue /></SelectTrigger><SelectContent className="bg-white border-[#E8DFD0]">{bookingRules.tableBooking.celebrationOptions.map(o => <SelectItem key={o.id} value={o.id}>{o.label}</SelectItem>)}</SelectContent></Select></div>
                  </div>
                  <div><Label className={labelCls}>Guest Type</Label><Select value={guestType} onValueChange={setGuestType}><SelectTrigger className={inputCls} data-testid="guest-type-select"><SelectValue placeholder="Select Type" /></SelectTrigger><SelectContent className="bg-white border-[#E8DFD0]">{bookingRules.tableBooking.guestTypes.map(t => <SelectItem key={t.id} value={t.id}>{t.label}</SelectItem>)}</SelectContent></Select></div>
                </div>
              </div>

              {/* Step 4 */}
              {showMenuSection && menuData && (
                <div className="pearl-surface overflow-hidden">
                  <div className="bg-[#F8F5F0] border-b border-[#E8DFD0] p-4"><h3 className="flex items-center gap-2 text-[#B8962E] font-heading font-medium"><ChefHat className="h-5 w-5" /> Step 4: Pre-Order Menu (Optional)</h3></div>
                  <div className="p-6">
                    <p className="text-sm text-[#5C4A3A] mb-4 font-body">Select items + quantity. Pre-ordering helps us serve you faster!</p>
                    <div className="space-y-6">
                      {menuData.categories.slice(0, 8).map(category => (
                        <div key={category.id}>
                          <h4 className="font-heading font-medium text-[#B8962E] mb-3 pb-2 border-b border-[#E8DFD0]">{category.name}</h4>
                          <div className="grid gap-2">
                            {category.items.slice(0, 6).map(item => (
                              <div key={item.id} className="flex items-center justify-between p-2 hover:bg-[#F8F5F0] transition-colors">
                                <div className="flex items-center gap-2">
                                  <Leaf className="h-4 w-4 text-[#B8962E]/40" />
                                  <span className="text-sm text-[#2D1810] font-body">{item.name}</span>
                                  <span className="text-sm font-heading font-medium text-[#B8962E]">{formatPrice(item.price)}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <Button variant="outline" size="icon" className="h-7 w-7 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] hover:border-[#B8962E]/30 rounded-none" onClick={() => updateCart(item.id, item.name, item.price, -1)} disabled={!cart[item.id]?.qty}><Minus className="h-3 w-3" /></Button>
                                  <span className="w-6 text-center text-sm font-body font-medium text-[#2D1810]">{cart[item.id]?.qty || 0}</span>
                                  <Button variant="outline" size="icon" className="h-7 w-7 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] hover:border-[#B8962E]/30 rounded-none" onClick={() => updateCart(item.id, item.name, item.price, 1)}><Plus className="h-3 w-3" /></Button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Special Requests */}
              <div className="pearl-surface overflow-hidden">
                <div className="bg-[#F8F5F0] border-b border-[#E8DFD0] p-4"><h3 className="text-[#B8962E] font-heading font-medium">Special Requests / Notes</h3></div>
                <div className="p-6">
                  <Textarea value={specialRequests} onChange={(e) => setSpecialRequests(e.target.value)} placeholder="Any special requests, dietary requirements, or notes..." className={`${inputCls} min-h-[100px]`} data-testid="special-requests" />
                </div>
              </div>
            </div>

            {/* Sidebar */}
            <div className="lg:col-span-1">
              <div className="sticky top-24 space-y-6">
                {cartItemCount > 0 && (
                  <div className="pearl-surface overflow-hidden">
                    <div className="bg-[#F8F5F0] border-b border-[#B8962E]/20 p-4">
                      <h3 className="flex items-center gap-2 text-[#B8962E] font-heading font-medium"><ShoppingCart className="h-5 w-5" /> Cart ({cartItemCount} items)</h3>
                    </div>
                    <div className="p-4">
                      <div className="space-y-2 max-h-60 overflow-y-auto">
                        {Object.entries(cart).map(([id, item]) => (
                          <div key={id} className="flex justify-between text-sm font-body">
                            <span className="text-[#5C4A3A]">{item.name} x{item.qty}</span>
                            <span className="font-medium text-[#2D1810]">{formatPrice(item.price * item.qty)}</span>
                          </div>
                        ))}
                      </div>
                      <div className="border-t border-[#E8DFD0] mt-4 pt-4 flex justify-between font-heading font-medium text-lg">
                        <span className="text-[#2D1810]">Total:</span>
                        <span className="text-[#B8962E]">{formatPrice(cartTotal)}</span>
                      </div>
                    </div>
                  </div>
                )}

                <div className="bg-[#F8F5F0] border border-[#B8962E]/10 p-4">
                  <div className="flex gap-3">
                    <AlertCircle className="h-5 w-5 text-[#B8962E]/40 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-[#7A6F65] font-body">
                      <p className="font-semibold text-[#B8962E]/60 mb-1">Important Note:</p>
                      <p className="text-xs">{bookingRules.tableBooking.disclaimer}</p>
                    </div>
                  </div>
                </div>

                <Button onClick={handleSubmit}
                  className="w-full gold-glossy text-white py-6 text-sm rounded-none tracking-widest uppercase font-semibold border-0"
                  disabled={!selectedCenter || !bookingDate || !selectedTimeSlot || !serviceType || !name || !phone}
                  data-testid="review-booking-btn">
                  <MessageCircle className="h-5 w-5 mr-2" /> Review & Send to WhatsApp
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
                <h2 className="text-2xl font-heading font-medium text-[#2D1810] mb-1">Table Reservation</h2>
                <p className="text-[#7A6F65] text-xs italic font-body">World's First Intelligent Restaurant Chain</p>
                <div className="w-16 h-0.5 bg-[#B8962E] mx-auto mt-3" />
              </div>
              <div className="p-6 space-y-5">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3"><p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-1 font-body">Center</p><p className="font-body font-medium text-[#2D1810]">{currentCenter?.displayName}</p></div>
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3"><p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-1 font-body">Date & Time</p><p className="font-body font-medium text-[#2D1810]">{bookingDate}</p><p className="text-[#7A6F65] text-xs mt-0.5 font-body">{(centerTimeSlots || bookingRules.tableBooking.timeSlots).find(t => t.id === selectedTimeSlot)?.label}</p></div>
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3"><p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-1 font-body">Service</p><p className="font-body font-medium text-[#2D1810]">{serviceType === 'dine-in' ? 'Dine In' : 'Pickup'}</p><p className="text-[#7A6F65] text-xs mt-0.5 font-body">{guestCount} guests</p></div>
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3"><p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-1 font-body">Guest</p><p className="font-body font-medium text-[#2D1810]">{name}</p><p className="text-[#7A6F65] text-xs mt-0.5 font-body">{phone}</p></div>
                </div>
                {cartItemCount > 0 && (
                  <div className="bg-[#F8F5F0] border border-[#B8962E]/20 p-4">
                    <p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-2 font-body">Pre-Order Items</p>
                    <div className="space-y-1">
                      {Object.entries(cart).map(([id, item]) => (
                        <div key={id} className="flex justify-between text-sm font-body"><span className="text-[#5C4A3A]">{item.name} x {item.qty}</span><span className="text-[#2D1810]">{formatPrice(item.price * item.qty)}</span></div>
                      ))}
                      <div className="flex justify-between font-heading font-medium text-lg pt-2 border-t border-[#E8DFD0]"><span className="text-[#2D1810]">Total</span><span className="text-[#B8962E]">{formatPrice(cartTotal)}</span></div>
                    </div>
                  </div>
                )}

                {/* Important Alert Before Sending */}
                <div className="bg-red-50 border-2 border-red-400 p-4">
                  <div className="flex gap-3">
                    <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-red-700 font-body">
                      <p className="font-bold mb-1">⚠️ Please Remember:</p>
                      <p className="text-xs">Booking is confirmed ONLY after Center Manager replies. If you don't receive a confirmation, the booking is not accepted.</p>
                    </div>
                  </div>
                </div>

                {/* Urgent Booking Warning in Review */}
                {isUrgentBooking && (
                  <div className="bg-orange-50 border-2 border-orange-400 p-4">
                    <div className="flex gap-3">
                      <AlertCircle className="h-5 w-5 text-orange-600 flex-shrink-0 mt-0.5 animate-pulse" />
                      <div className="text-sm text-orange-700 font-body">
                        <p className="font-bold mb-1">⏰ URGENT - Less than 1 hour!</p>
                        <p className="text-xs">Manager confirmation is MANDATORY. If no reply, DO NOT visit. No reply = booking NOT available.</p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex gap-3 pt-2">
                  <Button variant="outline" onClick={() => setShowReview(false)} className="flex-1 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] hover:border-[#B8962E]/30 rounded-none" data-testid="edit-booking-btn">Edit Booking</Button>
                  <Button onClick={confirmBooking} className="flex-1 bg-green-600 hover:bg-green-700 text-white rounded-none" data-testid="confirm-booking-btn"><MessageCircle className="h-5 w-5 mr-2" /> Send via WhatsApp</Button>
                </div>
                <Button variant="ghost" onClick={resetForm} className="w-full text-[#7A6F65] hover:text-[#5C4A3A]">Reset Form</Button>
                <p className="text-center text-[10px] text-[#7A6F65] italic font-body">© Purnabramha</p>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default TableBooking;
