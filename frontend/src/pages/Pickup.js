import { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShoppingCart, MapPin, Phone, MessageCircle, Plus, Minus, Leaf, Search, X, ChefHat, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';
import axios from 'axios';

import centersData from '@/config/centers.json';
import indiaMenus from '@/config/menus-india.json';
import perthMenus from '@/config/menus-perth.json';
import bookingRules from '@/config/booking-rules.json';
import { evaluatePromotion } from '@/utils/promoEngine';
import PromoTimer from '@/components/PromoTimer';

const API = process.env.REACT_APP_BACKEND_URL;

const Pickup = () => {
  const [selectedRegion, setSelectedRegion] = useState('');
  const [selectedCenter, setSelectedCenter] = useState('');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [pickupDate, setPickupDate] = useState('');
  const [pickupTime, setPickupTime] = useState('');
  const [specialInstructions, setSpecialInstructions] = useState('');
  const [cart, setCart] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('');
  const [showCart, setShowCart] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [dbMenuItems, setDbMenuItems] = useState([]);
  const [menuLoading, setMenuLoading] = useState(false);
  const [promotions, setPromotions] = useState(null);
  const [nowTick, setNowTick] = useState(Date.now());

  // Fetch promotions on mount + tick every minute so window opens/closes auto-update
  useEffect(() => {
    axios.get(`${API}/api/promotions`).then(r => setPromotions(r.data)).catch(() => {});
    const t = setInterval(() => setNowTick(Date.now()), 60000);
    return () => clearInterval(t);
  }, []);

  const allCenters = useMemo(() => [...centersData.india, ...centersData.australia], []);
  const filteredCenters = useMemo(() => {
    if (!selectedRegion) return [];
    return selectedRegion === 'india' ? centersData.india : centersData.australia;
  }, [selectedRegion]);
  const currentCenter = useMemo(() => allCenters.find(c => c.id === selectedCenter), [selectedCenter, allCenters]);

  useEffect(() => {
    const fetchMenu = async () => {
      setMenuLoading(true);
      try {
        const response = await axios.get(`${API}/api/menu`);
        setDbMenuItems(response.data);
      } catch (err) {
        console.log('Using fallback JSON menu');
      } finally {
        setMenuLoading(false);
      }
    };
    fetchMenu();
  }, []);

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
        if (!categoryMap[item.category]) {
          categoryMap[item.category] = { id: item.category.toLowerCase().replace(/[^a-z0-9]/g, '-'), name: item.category, items: [] };
        }
        categoryMap[item.category].items.push({
          id: item.id, name: item.name, price, isVeg: item.is_veg ?? true,
          description: item.description, image_url: item.image_url,
          no_onion_garlic: item.no_onion_garlic || false, fasting_friendly: item.fasting_friendly || false
        });
      });
      const categories = Object.values(categoryMap);
      if (categories.length > 0) return { currency: isAustralia ? 'AUD' : 'INR', currencySymbol: isAustralia ? '$' : '₹', categories };
    }
    return jsonFallback;
  }, [currentCenter, dbMenuItems]);

  const isAustralia = currentCenter?.country === 'Australia';
  const currencySymbol = menuData?.currencySymbol || '₹';
  const minOrder = isAustralia ? bookingRules.pickup.minOrderAmount.australia : bookingRules.pickup.minOrderAmount.india;

  const filteredItems = useMemo(() => {
    if (!menuData) return [];
    let items = [];
    menuData.categories.forEach(cat => {
      cat.items.forEach(item => { items.push({ ...item, categoryId: cat.id, categoryName: cat.name }); });
    });
    if (searchQuery) items = items.filter(item => item.name.toLowerCase().includes(searchQuery.toLowerCase()));
    if (activeCategory) items = items.filter(item => item.categoryId === activeCategory);
    return items;
  }, [menuData, searchQuery, activeCategory]);

  const updateCart = (item, delta) => {
    setCart(prev => {
      const key = item.id;
      const current = prev[key] || { ...item, qty: 0 };
      const newQty = Math.max(0, current.qty + delta);
      if (newQty === 0) { const { [key]: _, ...rest } = prev; return rest; }
      // Persist categoryName/categoryId so promo engine can match
      return { ...prev, [key]: { ...current, ...item, qty: newQty } };
    });
  };

  const cartTotal = useMemo(() => Object.values(cart).reduce((sum, item) => sum + (item.price * item.qty), 0), [cart]);
  const cartItemCount = useMemo(() => Object.values(cart).reduce((sum, item) => sum + item.qty, 0), [cart]);

  // Evaluate active discount combo (recomputed on cart/promotions/time change)
  const promoResult = useMemo(() => {
    if (!promotions || !currentCenter) return { applied: null, discount: 0 };
    return evaluatePromotion({
      cart,
      promotions,
      country: currentCenter.country,
      now: new Date(nowTick),
    });
  }, [cart, promotions, currentCenter, nowTick]);

  const finalTotal = useMemo(() => Math.max(0, cartTotal - (promoResult.discount || 0)), [cartTotal, promoResult]);
  const formatPrice = (price) => `${currencySymbol}${price.toFixed(2)}`;
  const getMinDate = () => new Date().toISOString().split('T')[0];
  const getMaxDate = () => { const d = new Date(); d.setDate(d.getDate() + 30); return d.toISOString().split('T')[0]; };

  const pickupTimeSlots = ['11:00 AM', '11:30 AM', '12:00 PM', '12:30 PM', '1:00 PM', '1:30 PM', '2:00 PM', '2:30 PM', '6:00 PM', '6:30 PM', '7:00 PM', '7:30 PM', '8:00 PM', '8:30 PM', '9:00 PM'];

  const generateWhatsAppMessage = () => {
    let message = `🛒 *PURNABRAMHA PICKUP ORDER*\n\n`;
    message += `📍 *Center:* ${currentCenter?.displayName}\n`;
    message += `👤 *Name:* ${name}\n`;
    message += `📞 *Phone:* ${phone}\n`;
    message += `📅 *Pickup Date:* ${pickupDate}\n`;
    message += `⏰ *Pickup Time:* ${pickupTime}\n\n`;
    message += `*📋 ORDER ITEMS:*\n`;
    Object.values(cart).forEach(item => { message += `• ${item.name} x${item.qty} = ${formatPrice(item.price * item.qty)}\n`; });
    message += `\n━━━━━━━━━━━━━━━\n`;
    message += `Subtotal: ${formatPrice(cartTotal)}\n`;
    if (promoResult.applied) {
      message += `🎉 ${promoResult.label} (-${promoResult.pct}%): -${formatPrice(promoResult.discount)}\n`;
    }
    message += `*💰 ORDER TOTAL: ${formatPrice(finalTotal)}*\n`;
    if (specialInstructions) message += `\n📝 *Special Instructions:*\n${specialInstructions}\n`;
    message += `\n⚠️ _This is a pre-order request. Confirmation will be sent via WhatsApp from the center._`;
    return encodeURIComponent(message);
  };

  const handleSubmit = () => {
    if (!selectedCenter || !name || !phone || !pickupDate || !pickupTime) { toast.error('Please fill all required fields'); return; }
    if (cartItemCount === 0) { toast.error('Please add items to your cart'); return; }
    if (finalTotal < minOrder) { toast.error(`Minimum order amount is ${formatPrice(minOrder)}`); return; }
    setShowReview(true);
  };

  const confirmOrder = () => {
    const message = generateWhatsAppMessage();
    const whatsappNumber = currentCenter?.whatsapp.replace(/[^0-9]/g, '');
    window.open(`https://wa.me/${whatsappNumber}?text=${message}`, '_blank');
    toast.success('Redirecting to WhatsApp...');
  };

  const clearCart = () => { setCart({}); toast.info('Cart cleared'); };

  const inputCls = "bg-white border-[#E8DFD0] text-[#2D1810] rounded-none placeholder:text-[#7A6F65]/50 focus-visible:ring-[#B8962E]";
  const labelCls = "text-[#5C4A3A] font-body text-xs tracking-wider uppercase";

  return (
    <div className="min-h-screen bg-[#FDFBF7]">
      {/* Hero */}
      <section className="relative py-16 border-b border-[#E8DFD0]">
        <div className="absolute inset-0 bg-[#F8F5F0]" />
        <div className="relative container mx-auto px-6 lg:px-12">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center max-w-3xl mx-auto">
            <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-4">Order Ahead</p>
            <h1 className="font-heading text-5xl md:text-6xl font-medium text-[#2D1810] mb-4 tracking-tight" data-testid="pickup-title">
              Pickup <span className="text-gold-shimmer">Orders</span>
            </h1>
            <p className="text-lg text-[#5C4A3A] font-body">Order ahead and pick up at your convenience</p>
          </motion.div>
        </div>
      </section>

      {!showReview ? (
        <div className="container mx-auto px-6 lg:px-12 py-10">
          {/* Live combo promo timer */}
          <div className="mb-6">
            <PromoTimer variant="sticky" region={currentCenter?.country === 'Australia' ? 'Australia' : 'India'} />
          </div>
          <div className="grid lg:grid-cols-4 gap-6">
            {/* Sidebar - Order Details */}
            <div className="lg:col-span-1 space-y-6">
              <div className="sticky top-24 pearl-surface overflow-hidden">
                <div className="bg-[#F8F5F0] border-b border-[#E8DFD0] p-4">
                  <h3 className="flex items-center gap-2 text-[#B8962E] font-heading text-lg font-medium">
                    <MapPin className="h-5 w-5" /> Order Details
                  </h3>
                </div>
                <div className="p-4 space-y-4">
                  <div>
                    <Label className={labelCls}>Region *</Label>
                    <Select value={selectedRegion} onValueChange={(v) => { setSelectedRegion(v); setSelectedCenter(''); setCart({}); }}>
                      <SelectTrigger className={inputCls} data-testid="pickup-region-select"><SelectValue placeholder="Select Region" /></SelectTrigger>
                      <SelectContent className="bg-white border-[#E8DFD0]">
                        <SelectItem value="india">India</SelectItem>
                        <SelectItem value="australia">Australia</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className={labelCls}>Center *</Label>
                    <Select value={selectedCenter} onValueChange={(v) => { setSelectedCenter(v); setCart({}); }} disabled={!selectedRegion}>
                      <SelectTrigger className={inputCls} data-testid="pickup-center-select"><SelectValue placeholder="Select Center" /></SelectTrigger>
                      <SelectContent className="bg-white border-[#E8DFD0]">
                        {filteredCenters.map(center => (<SelectItem key={center.id} value={center.id}>{center.displayName}</SelectItem>))}
                      </SelectContent>
                    </Select>
                  </div>
                  {currentCenter && (
                    <div className="p-2 bg-[#F8F5F0] border border-[#E8DFD0] flex items-center gap-2 text-sm text-[#5C4A3A] font-body">
                      <Phone className="h-4 w-4 text-[#B8962E]/60" /><span>{currentCenter.phone}</span>
                    </div>
                  )}
                  <div>
                    <Label className={labelCls}>Your Name *</Label>
                    <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name" className={inputCls} data-testid="pickup-name" />
                  </div>
                  <div>
                    <Label className={labelCls}>Phone *</Label>
                    <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone number" className={inputCls} data-testid="pickup-phone" />
                  </div>
                  <div>
                    <Label className={labelCls}>Pickup Date *</Label>
                    <Input type="date" value={pickupDate} onChange={(e) => setPickupDate(e.target.value)} min={getMinDate()} max={getMaxDate()} className={inputCls} data-testid="pickup-date" />
                  </div>
                  <div>
                    <Label className={labelCls}>Pickup Time *</Label>
                    <Select value={pickupTime} onValueChange={setPickupTime}>
                      <SelectTrigger className={inputCls} data-testid="pickup-time-select"><SelectValue placeholder="Select time" /></SelectTrigger>
                      <SelectContent className="bg-white border-[#E8DFD0]">
                        {pickupTimeSlots.map(time => (<SelectItem key={time} value={time}>{time}</SelectItem>))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className={labelCls}>Special Instructions</Label>
                    <Textarea value={specialInstructions} onChange={(e) => setSpecialInstructions(e.target.value)} placeholder="Any special requests..." className={`${inputCls} min-h-[60px]`} />
                  </div>
                </div>
              </div>
            </div>

            {/* Main Content - Menu */}
            <div className="lg:col-span-2 space-y-4">
              <div className="sticky top-20 z-10 bg-[#FDFBF7]/95 backdrop-blur-sm py-4 space-y-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#7A6F65]" />
                  <Input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search menu items..."
                    className={`pl-10 ${inputCls}`} data-testid="menu-search" />
                  {searchQuery && (
                    <Button variant="ghost" size="icon" className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 text-[#5C4A3A] hover:text-[#2D1810]" onClick={() => setSearchQuery('')}>
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
                {menuData && (
                  <ScrollArea className="w-full whitespace-nowrap">
                    <div className="flex gap-2 pb-2">
                      <Badge variant={activeCategory === '' ? 'default' : 'outline'}
                        className={`cursor-pointer rounded-none font-body text-xs ${activeCategory === '' ? 'bg-[#B8962E] text-white border-[#B8962E]' : 'border-[#E8DFD0] text-[#5C4A3A] hover:border-[#B8962E]/30'}`}
                        onClick={() => setActiveCategory('')}>All</Badge>
                      {menuData.categories.map(cat => (
                        <Badge key={cat.id} variant={activeCategory === cat.id ? 'default' : 'outline'}
                          className={`cursor-pointer whitespace-nowrap rounded-none font-body text-xs ${activeCategory === cat.id ? 'bg-[#B8962E] text-white border-[#B8962E]' : 'border-[#E8DFD0] text-[#5C4A3A] hover:border-[#B8962E]/30'}`}
                          onClick={() => setActiveCategory(cat.id)}>{cat.name}</Badge>
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </div>

              {menuData ? (
                <div className="space-y-6">
                  {activeCategory ? (
                    <div className="grid gap-3">
                      {filteredItems.map(item => (<MenuItemCard key={item.id} item={item} cart={cart} updateCart={updateCart} formatPrice={formatPrice} />))}
                    </div>
                  ) : (
                    menuData.categories.map(category => {
                      const categoryItems = filteredItems.filter(i => i.categoryId === category.id);
                      if (categoryItems.length === 0) return null;
                      return (
                        <div key={category.id}>
                          <h3 className="font-heading font-medium text-lg text-[#B8962E] mb-3 flex items-center gap-2">
                            <ChefHat className="h-5 w-5" />{category.name}
                          </h3>
                          <div className="grid gap-3">
                            {categoryItems.map(item => (<MenuItemCard key={item.id} item={item} cart={cart} updateCart={updateCart} formatPrice={formatPrice} />))}
                          </div>
                        </div>
                      );
                    })
                  )}
                  {filteredItems.length === 0 && (
                    <div className="text-center py-12 text-[#5C4A3A] font-body"><p>No items found matching "{searchQuery}"</p></div>
                  )}
                </div>
              ) : (
                <div className="pearl-surface py-12 text-center text-[#5C4A3A]">
                  <ChefHat className="h-12 w-12 mx-auto mb-4 opacity-30 text-[#B8962E]" />
                  <p className="font-body">Select a center to view the menu</p>
                </div>
              )}
            </div>

            {/* Right Sidebar - Cart */}
            <div className="lg:col-span-1">
              <div className="sticky top-24 space-y-4">
                <div className="pearl-surface overflow-hidden">
                  <div className="bg-[#F8F5F0] border-b border-[#B8962E]/20 p-4 flex items-center justify-between">
                    <span className="flex items-center gap-2 text-[#B8962E] font-heading font-medium">
                      <ShoppingCart className="h-5 w-5" /> Cart ({cartItemCount})
                    </span>
                    {cartItemCount > 0 && (
                      <Button variant="ghost" size="sm" className="text-[#7A6F65] hover:text-[#B8962E] hover:bg-transparent" onClick={clearCart}>Clear</Button>
                    )}
                  </div>
                  <div className="p-4">
                    {cartItemCount > 0 ? (
                      <>
                        <div className="space-y-3 max-h-64 overflow-y-auto">
                          {Object.values(cart).map(item => (
                            <div key={item.id} className="flex items-center justify-between text-sm">
                              <div className="flex-1">
                                <p className="font-body font-medium text-[#2D1810] truncate">{item.name}</p>
                                <p className="text-[#7A6F65] font-body text-xs">{formatPrice(item.price)} x {item.qty}</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <Button variant="outline" size="icon" className="h-6 w-6 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] hover:border-[#B8962E]/30 rounded-none" onClick={() => updateCart(item, -1)}><Minus className="h-3 w-3" /></Button>
                                <span className="w-6 text-center text-[#2D1810] font-body">{item.qty}</span>
                                <Button variant="outline" size="icon" className="h-6 w-6 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] hover:border-[#B8962E]/30 rounded-none" onClick={() => updateCart(item, 1)}><Plus className="h-3 w-3" /></Button>
                              </div>
                            </div>
                          ))}
                        </div>
                        <div className="border-t border-[#E8DFD0] mt-4 pt-4 space-y-2">
                          <div className="flex justify-between text-sm font-body">
                            <span className="text-[#5C4A3A]">Subtotal:</span>
                            <span className="text-[#2D1810]">{formatPrice(cartTotal)}</span>
                          </div>
                          {promoResult.applied && (
                            <div className="flex justify-between text-sm font-body bg-[#F5FFF5] -mx-1 px-2 py-1 rounded border border-green-200" data-testid="promo-applied">
                              <span className="text-green-700 font-medium flex items-center gap-1">
                                <Leaf className="h-3 w-3" /> {promoResult.label} ({promoResult.pct}% off)
                              </span>
                              <span className="text-green-700 font-medium">-{formatPrice(promoResult.discount)}</span>
                            </div>
                          )}
                          <div className="flex justify-between font-heading font-medium text-lg">
                            <span className="text-[#2D1810]">Total:</span>
                            <span className="text-[#B8962E]">{formatPrice(finalTotal)}</span>
                          </div>
                          {!promoResult.applied && promoResult.hints?.some(h => h.in_window) && (
                            <p className="text-[10px] text-[#B8962E] italic font-body" data-testid="promo-hint">
                              {promoResult.hints.filter(h => h.in_window).map(h => `${h.label}: add the right combo & save ${h.pct}%`).join(' · ')}
                            </p>
                          )}
                          {finalTotal < minOrder && <p className="text-xs text-red-500 mt-1 font-body">Min order: {formatPrice(minOrder)}</p>}
                        </div>
                      </>
                    ) : (
                      <div className="text-center py-6 text-[#7A6F65]">
                        <ShoppingCart className="h-10 w-10 mx-auto mb-2 opacity-30" />
                        <p className="font-body text-sm">Your cart is empty</p>
                      </div>
                    )}
                  </div>
                </div>

                <div className="bg-[#F8F5F0] border border-[#B8962E]/10 p-4">
                  <div className="flex gap-2 text-sm text-[#B8962E]/60 font-body">
                    <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                    <p className="text-xs">{bookingRules.pickup.disclaimer}</p>
                  </div>
                </div>

                <Button onClick={handleSubmit}
                  className="w-full gold-glossy text-white py-6 text-sm rounded-none tracking-widest uppercase font-semibold border-0"
                  disabled={!selectedCenter || !name || !phone || !pickupDate || !pickupTime || cartItemCount === 0 || finalTotal < minOrder}
                  data-testid="pickup-submit-btn">
                  <MessageCircle className="h-5 w-5 mr-2" /> Place Order via WhatsApp
                </Button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Review Section */
        <div className="container mx-auto px-6 lg:px-12 py-10">
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="max-w-2xl mx-auto">
            <div className="bg-white border border-[#E8DFD0] overflow-hidden shadow-lg">
              <div className="bg-[#F8F5F0] border-b border-[#B8962E]/20 p-6 text-center">
                <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-1">Purnabramha</p>
                <h2 className="text-2xl font-heading font-medium text-[#2D1810] mb-1">Pickup Order Review</h2>
                <p className="text-[#7A6F65] text-xs italic font-body">World's First Intelligent Restaurant Chain</p>
                <div className="w-16 h-0.5 bg-[#B8962E] mx-auto mt-3" />
              </div>
              <div className="p-6 space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3">
                    <p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-1 font-body">Center</p>
                    <p className="font-body font-medium text-[#2D1810]">{currentCenter?.displayName}</p>
                  </div>
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3">
                    <p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-1 font-body">Pickup</p>
                    <p className="font-body font-medium text-[#2D1810]">{pickupDate} at {pickupTime}</p>
                  </div>
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3">
                    <p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-1 font-body">Name</p>
                    <p className="font-body font-medium text-[#2D1810]">{name}</p>
                  </div>
                  <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-3">
                    <p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-1 font-body">Phone</p>
                    <p className="font-body font-medium text-[#2D1810]">{phone}</p>
                  </div>
                </div>
                <div className="border-t border-[#E8DFD0] pt-4">
                  <p className="font-heading font-medium text-[#2D1810] mb-3">Order Items:</p>
                  <div className="space-y-2">
                    {Object.values(cart).map(item => (
                      <div key={item.id} className="flex justify-between text-sm font-body">
                        <span className="text-[#5C4A3A]">{item.name} x {item.qty}</span>
                        <span className="text-[#2D1810]">{formatPrice(item.price * item.qty)}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="bg-[#F8F5F0] border border-[#B8962E]/20 p-4 text-center">
                  <p className="text-[#B8962E]/60 text-xs uppercase tracking-wider mb-1 font-body">Order Total</p>
                  {promoResult.applied && (
                    <p className="text-xs text-green-700 font-body mb-1">
                      Subtotal: {formatPrice(cartTotal)} · {promoResult.label} -{formatPrice(promoResult.discount)}
                    </p>
                  )}
                  <p className="text-3xl font-heading font-medium text-[#B8962E]">{formatPrice(finalTotal)}</p>
                </div>
                {specialInstructions && (
                  <div className="border-t border-[#E8DFD0] pt-4">
                    <p className="text-[#7A6F65] text-sm font-body">Special Instructions:</p>
                    <p className="text-sm text-[#2D1810] font-body">{specialInstructions}</p>
                  </div>
                )}
                <div className="flex gap-4 pt-4">
                  <Button variant="outline" onClick={() => setShowReview(false)} className="flex-1 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] hover:border-[#B8962E]/30 rounded-none">Edit Order</Button>
                  <Button onClick={confirmOrder} className="flex-1 bg-green-600 hover:bg-green-700 text-white rounded-none" data-testid="pickup-confirm-btn">
                    <MessageCircle className="h-5 w-5 mr-2" /> Confirm & Send
                  </Button>
                </div>
                <p className="text-center text-[10px] text-[#7A6F65] italic font-body">© Purnabramha</p>
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {cartItemCount > 0 && !showReview && (
        <div className="fixed bottom-4 left-4 right-4 lg:hidden z-50">
          <Button onClick={() => setShowCart(!showCart)} className="w-full gold-glossy text-white py-4 rounded-none font-semibold tracking-wider border-0">
            <ShoppingCart className="h-5 w-5 mr-2" /> View Cart ({cartItemCount}) &bull; {formatPrice(finalTotal)}
          </Button>
        </div>
      )}
    </div>
  );
};

const MenuItemCard = ({ item, cart, updateCart, formatPrice }) => {
  const inCart = cart[item.id]?.qty || 0;
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className="flex items-center justify-between p-3 bg-white border border-[#E8DFD0] hover:border-[#B8962E]/30 transition-all hover:shadow-md">
      <div className="flex items-center gap-3 flex-1">
        {item.image_url ? (
          <img src={item.image_url} alt={item.name} className="w-12 h-12 object-cover flex-shrink-0 border border-[#E8DFD0]"
            onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }} />
        ) : null}
        <div className={`w-8 h-8 bg-[#F8F5F0] border border-[#E8DFD0] flex items-center justify-center flex-shrink-0 ${item.image_url ? 'hidden' : ''}`}>
          <Leaf className="h-4 w-4 text-[#B8962E]/40" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-body font-medium text-[#2D1810] truncate">{item.name}</p>
          {item.description && <p className="text-xs text-[#7A6F65] truncate font-body">{item.description}</p>}
          <div className="flex flex-wrap items-center gap-1 mt-1">
            <p className="text-sm font-heading font-medium text-[#B8962E]">{formatPrice(item.price)}</p>
            {item.no_onion_garlic && (
              <Badge className="bg-orange-100 text-orange-600 border-orange-200 text-[10px] font-bold px-1.5 py-0" data-testid="pickup-badge-no-onion-garlic">No Onion/Garlic</Badge>
            )}
            {item.fasting_friendly && (
              <Badge className="bg-purple-100 text-purple-600 border-purple-200 text-[10px] font-bold px-1.5 py-0" data-testid="pickup-badge-fasting">Fasting</Badge>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {inCart > 0 ? (
          <>
            <Button variant="outline" size="icon" className="h-8 w-8 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] hover:border-[#B8962E]/30 rounded-none" onClick={() => updateCart(item, -1)} data-testid={`pickup-decrement-${item.id}`}><Minus className="h-4 w-4" /></Button>
            <span className="w-8 text-center font-body font-semibold text-[#2D1810]" data-testid={`pickup-qty-${item.id}`}>{inCart}</span>
            <Button variant="outline" size="icon" className="h-8 w-8 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] hover:border-[#B8962E]/30 rounded-none" onClick={() => updateCart(item, 1)} data-testid={`pickup-increment-${item.id}`}><Plus className="h-4 w-4" /></Button>
          </>
        ) : (
          <Button variant="outline" size="sm" className="border-[#B8962E]/30 text-[#B8962E] hover:bg-[#B8962E] hover:text-white rounded-none text-xs tracking-wider" onClick={() => updateCart(item, 1)} data-testid={`pickup-add-${item.id}`}>
            <Plus className="h-4 w-4 mr-1" /> Add
          </Button>
        )}
      </div>
    </motion.div>
  );
};

export default Pickup;
