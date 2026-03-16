import { useState, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Calendar, Clock, Users, MapPin, Phone, MessageCircle, ChefHat, Leaf, Plus, Minus, ShoppingCart, AlertCircle, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import axios from 'axios';

import centersData from '@/config/centers.json';
import bookingRules from '@/config/booking-rules.json';
import indiaMenus from '@/config/menus-india.json';
import perthMenus from '@/config/menus-perth.json';

const API = process.env.REACT_APP_BACKEND_URL;

const TableBooking = () => {
  const [selectedRegion, setSelectedRegion] = useState('');
  const [selectedCenter, setSelectedCenter] = useState('');
  const [bookingDate, setBookingDate] = useState('');
  const [selectedTimeSlot, setSelectedTimeSlot] = useState('');
  const [serviceType, setServiceType] = useState('');
  const [guestCount, setGuestCount] = useState('2');
  const [celebration, setCelebration] = useState('none');
  const [guestType, setGuestType] = useState('');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [specialRequests, setSpecialRequests] = useState('');
  const [cart, setCart] = useState({});
  const [showReview, setShowReview] = useState(false);
  const [dbMenuItems, setDbMenuItems] = useState([]);

  // Fetch menu from database
  useEffect(() => {
    const fetchMenu = async () => {
      try {
        const response = await axios.get(`${API}/api/menu`);
        setDbMenuItems(response.data);
      } catch (err) {
        console.log('Using fallback JSON menu');
      }
    };
    fetchMenu();
  }, []);

  const allCenters = useMemo(() => [...centersData.india, ...centersData.australia], []);

  const filteredCenters = useMemo(() => {
    if (!selectedRegion) return [];
    return selectedRegion === 'india' ? centersData.india : centersData.australia;
  }, [selectedRegion]);

  const currentCenter = useMemo(() => {
    return allCenters.find(c => c.id === selectedCenter);
  }, [selectedCenter, allCenters]);

  // Use database menu if available, otherwise fallback to JSON
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
          categoryMap[item.category] = {
            id: item.category.toLowerCase().replace(/[^a-z0-9]/g, '-'),
            name: item.category,
            items: []
          };
        }
        categoryMap[item.category].items.push({
          id: item.id,
          name: item.name,
          price: price,
          isVeg: item.is_veg ?? true,
          description: item.description,
          image_url: item.image_url
        });
      });

      const categories = Object.values(categoryMap);
      if (categories.length > 0) {
        return {
          currency: isAustralia ? 'AUD' : 'INR',
          currencySymbol: isAustralia ? '$' : '₹',
          categories
        };
      }
    }

    return jsonFallback;
  }, [currentCenter, dbMenuItems]);

  const showMenuSection = serviceType === 'pickup' || currentCenter?.country === 'Australia';

  const getMinDate = () => {
    const now = new Date();
    now.setHours(now.getHours() + bookingRules.tableBooking.minAdvanceHours);
    return now.toISOString().split('T')[0];
  };

  const getMaxDate = () => {
    const now = new Date();
    now.setDate(now.getDate() + bookingRules.tableBooking.maxAdvanceDays);
    return now.toISOString().split('T')[0];
  };

  const updateCart = (itemId, itemName, price, delta) => {
    setCart(prev => {
      const current = prev[itemId] || { name: itemName, price, qty: 0 };
      const newQty = Math.max(0, current.qty + delta);
      if (newQty === 0) {
        const { [itemId]: _, ...rest } = prev;
        return rest;
      }
      return { ...prev, [itemId]: { ...current, qty: newQty } };
    });
  };

  const cartTotal = useMemo(() => {
    return Object.values(cart).reduce((sum, item) => sum + (item.price * item.qty), 0);
  }, [cart]);

  const cartItemCount = useMemo(() => {
    return Object.values(cart).reduce((sum, item) => sum + item.qty, 0);
  }, [cart]);

  const formatPrice = (price) => {
    if (!menuData) return price;
    return `${menuData.currencySymbol}${price.toFixed(2)}`;
  };

  const generateWhatsAppMessage = () => {
    const timeSlotLabel = bookingRules.tableBooking.timeSlots.find(t => t.id === selectedTimeSlot)?.label || '';
    const celebrationLabel = bookingRules.tableBooking.celebrationOptions.find(c => c.id === celebration)?.label || '';
    
    let message = `🪔 *PURNABRAMHA TABLE BOOKING*\n\n`;
    message += `📍 *Center:* ${currentCenter?.displayName}\n`;
    message += `📅 *Date:* ${bookingDate}\n`;
    message += `⏰ *Time:* ${timeSlotLabel}\n`;
    message += `🍽️ *Service:* ${serviceType === 'dine-in' ? 'Dine In' : 'Pickup'}\n`;
    message += `👥 *Guests:* ${guestCount}\n`;
    message += `🎉 *Celebration:* ${celebrationLabel}\n\n`;
    message += `👤 *Name:* ${name}\n`;
    message += `📞 *Phone:* ${phone}\n`;
    if (email) message += `📧 *Email:* ${email}\n`;
    
    if (cartItemCount > 0) {
      message += `\n🛒 *Pre-Order Items:*\n`;
      Object.entries(cart).forEach(([id, item]) => {
        message += `• ${item.name} x${item.qty} = ${formatPrice(item.price * item.qty)}\n`;
      });
      message += `\n💰 *Order Total:* ${formatPrice(cartTotal)}\n`;
    }
    
    if (specialRequests) {
      message += `\n📝 *Special Requests:*\n${specialRequests}\n`;
    }
    
    message += `\n⚠️ _Booking confirmation pending Center Manager's reply._`;
    
    return encodeURIComponent(message);
  };

  const handleSubmit = () => {
    if (!selectedCenter || !bookingDate || !selectedTimeSlot || !serviceType || !name || !phone) {
      toast.error('Please fill all required fields');
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

  const resetForm = () => {
    setSelectedRegion('');
    setSelectedCenter('');
    setBookingDate('');
    setSelectedTimeSlot('');
    setServiceType('');
    setGuestCount('2');
    setCelebration('none');
    setGuestType('');
    setName('');
    setPhone('');
    setEmail('');
    setSpecialRequests('');
    setCart({});
    setShowReview(false);
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
            <h1 className="text-4xl md:text-5xl font-bold mb-4" data-testid="table-booking-title">
              🪔 Table Booking
            </h1>
            <p className="text-lg text-amber-200">
              Reserve your table at any Purnabramha center across India & Australia
            </p>
            <div className="mt-4 flex items-center justify-center gap-2 text-amber-300 text-sm">
              <Clock className="h-4 w-4" />
              <span>Minimum 2 hours advance booking required</span>
            </div>
          </motion.div>
        </div>
      </section>

      <div className="container mx-auto px-4 py-8">
        {!showReview ? (
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Main Form */}
            <div className="lg:col-span-2 space-y-6">
              {/* Step 1: Region & Center Selection */}
              <Card className="border-amber-200 shadow-lg">
                <CardHeader className="bg-gradient-to-r from-amber-100 to-orange-100 rounded-t-lg">
                  <CardTitle className="flex items-center gap-2 text-[#5c1e1e]">
                    <MapPin className="h-5 w-5" />
                    Step 1: Select Region & Center
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6 space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <Label>Region *</Label>
                      <Select value={selectedRegion} onValueChange={(v) => { setSelectedRegion(v); setSelectedCenter(''); }}>
                        <SelectTrigger data-testid="region-select">
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
                        <SelectTrigger data-testid="center-select">
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
                  {currentCenter && (
                    <div className="p-3 bg-amber-50 rounded-lg flex items-center gap-2 text-sm">
                      <Phone className="h-4 w-4 text-[#5c1e1e]" />
                      <span className="font-medium">{currentCenter.phone}</span>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Step 2: Date & Time */}
              <Card className="border-amber-200 shadow-lg">
                <CardHeader className="bg-gradient-to-r from-amber-100 to-orange-100 rounded-t-lg">
                  <CardTitle className="flex items-center gap-2 text-[#5c1e1e]">
                    <Calendar className="h-5 w-5" />
                    Step 2: Date & Time
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6 space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <Label>Date *</Label>
                      <Input
                        type="date"
                        value={bookingDate}
                        onChange={(e) => setBookingDate(e.target.value)}
                        min={getMinDate()}
                        max={getMaxDate()}
                        className="border-amber-200"
                        data-testid="booking-date"
                      />
                    </div>
                    <div>
                      <Label>Time Slot *</Label>
                      <Select value={selectedTimeSlot} onValueChange={setSelectedTimeSlot}>
                        <SelectTrigger data-testid="time-slot-select">
                          <SelectValue placeholder="Select Time" />
                        </SelectTrigger>
                        <SelectContent>
                          {bookingRules.tableBooking.timeSlots.map(slot => (
                            <SelectItem key={slot.id} value={slot.id}>
                              {slot.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <Label>Service Type *</Label>
                      <Select value={serviceType} onValueChange={setServiceType}>
                        <SelectTrigger data-testid="service-type-select">
                          <SelectValue placeholder="Select Service" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="dine-in">🍽️ Dine In</SelectItem>
                          <SelectItem value="pickup">📦 Pickup</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>Number of Guests *</Label>
                      <Select value={guestCount} onValueChange={setGuestCount}>
                        <SelectTrigger data-testid="guest-count-select">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {[1,2,3,4,5,6,7,8,9,10,15,20,25,30].map(n => (
                            <SelectItem key={n} value={n.toString()}>{n} {n === 1 ? 'Guest' : 'Guests'}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Step 3: Guest Details */}
              <Card className="border-amber-200 shadow-lg">
                <CardHeader className="bg-gradient-to-r from-amber-100 to-orange-100 rounded-t-lg">
                  <CardTitle className="flex items-center gap-2 text-[#5c1e1e]">
                    <Users className="h-5 w-5" />
                    Step 3: Guest Details
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6 space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <Label>Name *</Label>
                      <Input
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Your full name"
                        className="border-amber-200"
                        data-testid="guest-name"
                      />
                    </div>
                    <div>
                      <Label>Phone *</Label>
                      <Input
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                        placeholder="Your phone number"
                        className="border-amber-200"
                        data-testid="guest-phone"
                      />
                    </div>
                  </div>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <Label>Email (Optional)</Label>
                      <Input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="your@email.com"
                        className="border-amber-200"
                        data-testid="guest-email"
                      />
                    </div>
                    <div>
                      <Label>Celebrating?</Label>
                      <Select value={celebration} onValueChange={setCelebration}>
                        <SelectTrigger data-testid="celebration-select">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {bookingRules.tableBooking.celebrationOptions.map(opt => (
                            <SelectItem key={opt.id} value={opt.id}>{opt.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div>
                    <Label>Guest Type</Label>
                    <Select value={guestType} onValueChange={setGuestType}>
                      <SelectTrigger data-testid="guest-type-select">
                        <SelectValue placeholder="Select Type" />
                      </SelectTrigger>
                      <SelectContent>
                        {bookingRules.tableBooking.guestTypes.map(type => (
                          <SelectItem key={type.id} value={type.id}>{type.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>

              {/* Step 4: Menu Selection (for Pickup or Perth) */}
              {showMenuSection && menuData && (
                <Card className="border-amber-200 shadow-lg">
                  <CardHeader className="bg-gradient-to-r from-amber-100 to-orange-100 rounded-t-lg">
                    <CardTitle className="flex items-center gap-2 text-[#5c1e1e]">
                      <ChefHat className="h-5 w-5" />
                      Step 4: Pre-Order Menu (Optional)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-6">
                    <p className="text-sm text-gray-600 mb-4">
                      Select items + quantity. Pre-ordering helps us serve you faster!
                    </p>
                    <div className="space-y-6">
                      {menuData.categories.slice(0, 8).map(category => (
                        <div key={category.id}>
                          <h4 className="font-semibold text-[#5c1e1e] mb-3 pb-2 border-b border-amber-200">
                            {category.name}
                          </h4>
                          <div className="grid gap-2">
                            {category.items.slice(0, 6).map(item => (
                              <div key={item.id} className="flex items-center justify-between p-2 rounded-lg hover:bg-amber-50 transition-colors">
                                <div className="flex items-center gap-2">
                                  <Leaf className="h-4 w-4 text-green-600" />
                                  <span className="text-sm">{item.name}</span>
                                  <span className="text-sm font-medium text-[#5c1e1e]">
                                    {formatPrice(item.price)}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <Button
                                    variant="outline"
                                    size="icon"
                                    className="h-7 w-7"
                                    onClick={() => updateCart(item.id, item.name, item.price, -1)}
                                    disabled={!cart[item.id]?.qty}
                                  >
                                    <Minus className="h-3 w-3" />
                                  </Button>
                                  <span className="w-6 text-center text-sm font-medium">
                                    {cart[item.id]?.qty || 0}
                                  </span>
                                  <Button
                                    variant="outline"
                                    size="icon"
                                    className="h-7 w-7"
                                    onClick={() => updateCart(item.id, item.name, item.price, 1)}
                                  >
                                    <Plus className="h-3 w-3" />
                                  </Button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Special Requests */}
              <Card className="border-amber-200 shadow-lg">
                <CardHeader className="bg-gradient-to-r from-amber-100 to-orange-100 rounded-t-lg">
                  <CardTitle className="text-[#5c1e1e]">Special Requests / Notes</CardTitle>
                </CardHeader>
                <CardContent className="pt-6">
                  <Textarea
                    value={specialRequests}
                    onChange={(e) => setSpecialRequests(e.target.value)}
                    placeholder="Any special requests, dietary requirements, or notes..."
                    className="border-amber-200 min-h-[100px]"
                    data-testid="special-requests"
                  />
                </CardContent>
              </Card>
            </div>

            {/* Sidebar - Cart & Summary */}
            <div className="lg:col-span-1">
              <div className="sticky top-24 space-y-6">
                {/* Cart Summary */}
                {cartItemCount > 0 && (
                  <Card className="border-amber-200 shadow-lg">
                    <CardHeader className="bg-gradient-to-r from-[#5c1e1e] to-[#8b2c2c] text-white rounded-t-lg">
                      <CardTitle className="flex items-center gap-2">
                        <ShoppingCart className="h-5 w-5" />
                        Cart ({cartItemCount} items)
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4">
                      <div className="space-y-2 max-h-60 overflow-y-auto">
                        {Object.entries(cart).map(([id, item]) => (
                          <div key={id} className="flex justify-between text-sm">
                            <span>{item.name} x{item.qty}</span>
                            <span className="font-medium">{formatPrice(item.price * item.qty)}</span>
                          </div>
                        ))}
                      </div>
                      <div className="border-t border-amber-200 mt-4 pt-4 flex justify-between font-bold text-lg">
                        <span>Total:</span>
                        <span className="text-[#5c1e1e]">{formatPrice(cartTotal)}</span>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Disclaimer */}
                <Card className="border-amber-300 bg-amber-50">
                  <CardContent className="pt-4">
                    <div className="flex gap-3">
                      <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                      <div className="text-sm text-amber-800">
                        <p className="font-semibold mb-1">Important Note:</p>
                        <p>{bookingRules.tableBooking.disclaimer}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Submit Button */}
                <Button
                  onClick={handleSubmit}
                  className="w-full bg-[#5c1e1e] hover:bg-[#8b2c2c] text-white py-6 text-lg"
                  disabled={!selectedCenter || !bookingDate || !selectedTimeSlot || !serviceType || !name || !phone}
                  data-testid="review-booking-btn"
                >
                  <MessageCircle className="h-5 w-5 mr-2" />
                  Review & Send to WhatsApp
                </Button>
              </div>
            </div>
          </div>
        ) : (
          /* Review Section */
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="max-w-2xl mx-auto"
          >
            <Card className="border-amber-200 shadow-xl">
              <CardHeader className="bg-gradient-to-r from-[#5c1e1e] to-[#8b2c2c] text-white rounded-t-lg">
                <CardTitle className="flex items-center gap-2 text-xl">
                  <CheckCircle className="h-6 w-6" />
                  Review Your Booking
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-6 space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">Center</p>
                    <p className="font-semibold">{currentCenter?.displayName}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Date & Time</p>
                    <p className="font-semibold">
                      {bookingDate} • {bookingRules.tableBooking.timeSlots.find(t => t.id === selectedTimeSlot)?.label}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-500">Service</p>
                    <p className="font-semibold">{serviceType === 'dine-in' ? 'Dine In' : 'Pickup'}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Guests</p>
                    <p className="font-semibold">{guestCount}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Name</p>
                    <p className="font-semibold">{name}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Phone</p>
                    <p className="font-semibold">{phone}</p>
                  </div>
                </div>

                {cartItemCount > 0 && (
                  <div className="border-t border-amber-200 pt-4">
                    <p className="font-semibold mb-2">Pre-Order Items:</p>
                    <div className="space-y-1">
                      {Object.entries(cart).map(([id, item]) => (
                        <div key={id} className="flex justify-between text-sm">
                          <span>{item.name} x{item.qty}</span>
                          <span>{formatPrice(item.price * item.qty)}</span>
                        </div>
                      ))}
                      <div className="flex justify-between font-bold pt-2 border-t">
                        <span>Total:</span>
                        <span>{formatPrice(cartTotal)}</span>
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex gap-4 pt-4">
                  <Button
                    variant="outline"
                    onClick={() => setShowReview(false)}
                    className="flex-1"
                    data-testid="edit-booking-btn"
                  >
                    Edit Order
                  </Button>
                  <Button
                    onClick={confirmBooking}
                    className="flex-1 bg-green-600 hover:bg-green-700"
                    data-testid="confirm-booking-btn"
                  >
                    <MessageCircle className="h-5 w-5 mr-2" />
                    Confirm & Send
                  </Button>
                </div>

                <Button
                  variant="ghost"
                  onClick={resetForm}
                  className="w-full text-gray-500"
                >
                  Reset Form
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default TableBooking;
