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

const API = process.env.REACT_APP_BACKEND_URL;

const Pickup = () => {
  const [selectedRegion, setSelectedRegion] = useState('');
  const [selectedCenter, setSelectedCenter] = useState('');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [pickupTime, setPickupTime] = useState('');
  const [specialInstructions, setSpecialInstructions] = useState('');
  const [cart, setCart] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('');
  const [showCart, setShowCart] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [dbMenuItems, setDbMenuItems] = useState([]);
  const [menuLoading, setMenuLoading] = useState(false);

  const allCenters = useMemo(() => [...centersData.india, ...centersData.australia], []);

  const filteredCenters = useMemo(() => {
    if (!selectedRegion) return [];
    return selectedRegion === 'india' ? centersData.india : centersData.australia;
  }, [selectedRegion]);

  const currentCenter = useMemo(() => {
    return allCenters.find(c => c.id === selectedCenter);
  }, [selectedCenter, allCenters]);

  // Fetch menu from database
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

  // Use database menu if available, otherwise fallback to JSON
  const menuData = useMemo(() => {
    if (!currentCenter) return null;
    const isAustralia = currentCenter.country === 'Australia';
    const jsonFallback = isAustralia ? perthMenus : indiaMenus;

    // If we have database items, transform them
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

  const isAustralia = currentCenter?.country === 'Australia';
  const currencySymbol = menuData?.currencySymbol || '₹';
  const minOrder = isAustralia ? bookingRules.pickup.minOrderAmount.australia : bookingRules.pickup.minOrderAmount.india;

  const filteredItems = useMemo(() => {
    if (!menuData) return [];
    
    let items = [];
    menuData.categories.forEach(cat => {
      cat.items.forEach(item => {
        items.push({ ...item, categoryId: cat.id, categoryName: cat.name });
      });
    });

    if (searchQuery) {
      items = items.filter(item => 
        item.name.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    if (activeCategory) {
      items = items.filter(item => item.categoryId === activeCategory);
    }

    return items;
  }, [menuData, searchQuery, activeCategory]);

  const updateCart = (item, delta) => {
    setCart(prev => {
      const key = item.id;
      const current = prev[key] || { ...item, qty: 0 };
      const newQty = Math.max(0, current.qty + delta);
      
      if (newQty === 0) {
        const { [key]: _, ...rest } = prev;
        return rest;
      }
      
      return { ...prev, [key]: { ...current, qty: newQty } };
    });
  };

  const cartTotal = useMemo(() => {
    return Object.values(cart).reduce((sum, item) => sum + (item.price * item.qty), 0);
  }, [cart]);

  const cartItemCount = useMemo(() => {
    return Object.values(cart).reduce((sum, item) => sum + item.qty, 0);
  }, [cart]);

  const formatPrice = (price) => `${currencySymbol}${price.toFixed(2)}`;

  const pickupTimeSlots = [
    '11:00 AM', '11:30 AM', '12:00 PM', '12:30 PM', '1:00 PM', '1:30 PM',
    '2:00 PM', '2:30 PM', '6:00 PM', '6:30 PM', '7:00 PM', '7:30 PM',
    '8:00 PM', '8:30 PM', '9:00 PM'
  ];

  const generateWhatsAppMessage = () => {
    let message = `🛒 *PURNABRAMHA PICKUP ORDER*\n\n`;
    message += `📍 *Center:* ${currentCenter?.displayName}\n`;
    message += `👤 *Name:* ${name}\n`;
    message += `📞 *Phone:* ${phone}\n`;
    message += `⏰ *Pickup Time:* ${pickupTime}\n\n`;
    
    message += `*📋 ORDER ITEMS:*\n`;
    Object.values(cart).forEach(item => {
      message += `• ${item.name} x${item.qty} = ${formatPrice(item.price * item.qty)}\n`;
    });
    
    message += `\n━━━━━━━━━━━━━━━\n`;
    message += `*💰 ORDER TOTAL: ${formatPrice(cartTotal)}*\n`;
    
    if (specialInstructions) {
      message += `\n📝 *Special Instructions:*\n${specialInstructions}\n`;
    }
    
    message += `\n⚠️ _This is a pre-order request. Confirmation will be sent via WhatsApp from the center._`;
    
    return encodeURIComponent(message);
  };

  const handleSubmit = () => {
    if (!selectedCenter || !name || !phone || !pickupTime) {
      toast.error('Please fill all required fields');
      return;
    }
    if (cartItemCount === 0) {
      toast.error('Please add items to your cart');
      return;
    }
    if (cartTotal < minOrder) {
      toast.error(`Minimum order amount is ${formatPrice(minOrder)}`);
      return;
    }
    setShowReview(true);
  };

  const confirmOrder = () => {
    const message = generateWhatsAppMessage();
    const whatsappNumber = currentCenter?.whatsapp.replace(/[^0-9]/g, '');
    window.open(`https://wa.me/${whatsappNumber}?text=${message}`, '_blank');
    toast.success('Redirecting to WhatsApp...');
  };

  const clearCart = () => {
    setCart({});
    toast.info('Cart cleared');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50 to-orange-50">
      {/* Hero Section */}
      <section className="relative py-12 bg-gradient-to-r from-[#5c1e1e] to-[#8b2c2c] text-white">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center max-w-3xl mx-auto"
          >
            <h1 className="text-4xl md:text-5xl font-bold mb-4" data-testid="pickup-title">
              🛒 Pickup Orders
            </h1>
            <p className="text-lg text-amber-200">
              Order ahead and pick up at your convenience
            </p>
          </motion.div>
        </div>
      </section>

      {!showReview ? (
        <div className="container mx-auto px-4 py-8">
          <div className="grid lg:grid-cols-4 gap-6">
            {/* Left Sidebar - Center & Customer Info */}
            <div className="lg:col-span-1 space-y-6">
              <Card className="border-amber-200 shadow-lg sticky top-24">
                <CardHeader className="bg-gradient-to-r from-amber-100 to-orange-100 rounded-t-lg pb-4">
                  <CardTitle className="flex items-center gap-2 text-[#5c1e1e] text-lg">
                    <MapPin className="h-5 w-5" />
                    Order Details
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4 space-y-4">
                  <div>
                    <Label>Region *</Label>
                    <Select value={selectedRegion} onValueChange={(v) => { setSelectedRegion(v); setSelectedCenter(''); setCart({}); }}>
                      <SelectTrigger data-testid="pickup-region-select">
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
                    <Select value={selectedCenter} onValueChange={(v) => { setSelectedCenter(v); setCart({}); }} disabled={!selectedRegion}>
                      <SelectTrigger data-testid="pickup-center-select">
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

                  {currentCenter && (
                    <div className="p-2 bg-amber-50 rounded-lg flex items-center gap-2 text-sm">
                      <Phone className="h-4 w-4 text-[#5c1e1e]" />
                      <span>{currentCenter.phone}</span>
                    </div>
                  )}

                  <div>
                    <Label>Your Name *</Label>
                    <Input
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Full name"
                      className="border-amber-200"
                      data-testid="pickup-name"
                    />
                  </div>

                  <div>
                    <Label>Phone *</Label>
                    <Input
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="Phone number"
                      className="border-amber-200"
                      data-testid="pickup-phone"
                    />
                  </div>

                  <div>
                    <Label>Pickup Time *</Label>
                    <Select value={pickupTime} onValueChange={setPickupTime}>
                      <SelectTrigger data-testid="pickup-time-select">
                        <SelectValue placeholder="Select time" />
                      </SelectTrigger>
                      <SelectContent>
                        {pickupTimeSlots.map(time => (
                          <SelectItem key={time} value={time}>{time}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Special Instructions</Label>
                    <Textarea
                      value={specialInstructions}
                      onChange={(e) => setSpecialInstructions(e.target.value)}
                      placeholder="Any special requests..."
                      className="border-amber-200 min-h-[60px]"
                    />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Main Content - Menu */}
            <div className="lg:col-span-2 space-y-4">
              {/* Search & Category Filter */}
              <div className="sticky top-20 z-10 bg-amber-50/95 backdrop-blur-sm py-4 space-y-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search menu items..."
                    className="pl-10 border-amber-200"
                    data-testid="menu-search"
                  />
                  {searchQuery && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
                      onClick={() => setSearchQuery('')}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>

                {menuData && (
                  <ScrollArea className="w-full whitespace-nowrap">
                    <div className="flex gap-2 pb-2">
                      <Badge
                        variant={activeCategory === '' ? 'default' : 'outline'}
                        className={`cursor-pointer ${activeCategory === '' ? 'bg-[#5c1e1e]' : ''}`}
                        onClick={() => setActiveCategory('')}
                      >
                        All
                      </Badge>
                      {menuData.categories.map(cat => (
                        <Badge
                          key={cat.id}
                          variant={activeCategory === cat.id ? 'default' : 'outline'}
                          className={`cursor-pointer whitespace-nowrap ${activeCategory === cat.id ? 'bg-[#5c1e1e]' : ''}`}
                          onClick={() => setActiveCategory(cat.id)}
                        >
                          {cat.name}
                        </Badge>
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </div>

              {/* Menu Items */}
              {menuData ? (
                <div className="space-y-6">
                  {activeCategory ? (
                    <div className="grid gap-3">
                      {filteredItems.map(item => (
                        <MenuItemCard
                          key={item.id}
                          item={item}
                          cart={cart}
                          updateCart={updateCart}
                          formatPrice={formatPrice}
                        />
                      ))}
                    </div>
                  ) : (
                    menuData.categories.map(category => {
                      const categoryItems = filteredItems.filter(i => i.categoryId === category.id);
                      if (categoryItems.length === 0) return null;
                      
                      return (
                        <div key={category.id}>
                          <h3 className="font-bold text-lg text-[#5c1e1e] mb-3 flex items-center gap-2">
                            <ChefHat className="h-5 w-5" />
                            {category.name}
                          </h3>
                          <div className="grid gap-3">
                            {categoryItems.map(item => (
                              <MenuItemCard
                                key={item.id}
                                item={item}
                                cart={cart}
                                updateCart={updateCart}
                                formatPrice={formatPrice}
                              />
                            ))}
                          </div>
                        </div>
                      );
                    })
                  )}

                  {filteredItems.length === 0 && (
                    <div className="text-center py-12 text-gray-500">
                      <p>No items found matching "{searchQuery}"</p>
                    </div>
                  )}
                </div>
              ) : (
                <Card className="border-amber-200">
                  <CardContent className="py-12 text-center text-gray-500">
                    <ChefHat className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Select a center to view the menu</p>
                  </CardContent>
                </Card>
              )}
            </div>

            {/* Right Sidebar - Cart */}
            <div className="lg:col-span-1">
              <div className="sticky top-24 space-y-4">
                <Card className="border-amber-200 shadow-lg">
                  <CardHeader className="bg-gradient-to-r from-[#5c1e1e] to-[#8b2c2c] text-white rounded-t-lg">
                    <CardTitle className="flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <ShoppingCart className="h-5 w-5" />
                        Cart ({cartItemCount})
                      </span>
                      {cartItemCount > 0 && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-white/70 hover:text-white hover:bg-white/10"
                          onClick={clearCart}
                        >
                          Clear
                        </Button>
                      )}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-4">
                    {cartItemCount > 0 ? (
                      <>
                        <div className="space-y-3 max-h-64 overflow-y-auto">
                          {Object.values(cart).map(item => (
                            <div key={item.id} className="flex items-center justify-between text-sm">
                              <div className="flex-1">
                                <p className="font-medium truncate">{item.name}</p>
                                <p className="text-gray-500">{formatPrice(item.price)} × {item.qty}</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <Button
                                  variant="outline"
                                  size="icon"
                                  className="h-6 w-6"
                                  onClick={() => updateCart(item, -1)}
                                >
                                  <Minus className="h-3 w-3" />
                                </Button>
                                <span className="w-6 text-center">{item.qty}</span>
                                <Button
                                  variant="outline"
                                  size="icon"
                                  className="h-6 w-6"
                                  onClick={() => updateCart(item, 1)}
                                >
                                  <Plus className="h-3 w-3" />
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>

                        <div className="border-t mt-4 pt-4">
                          <div className="flex justify-between font-bold text-lg">
                            <span>Total:</span>
                            <span className="text-[#5c1e1e]">{formatPrice(cartTotal)}</span>
                          </div>
                          {cartTotal < minOrder && (
                            <p className="text-xs text-red-500 mt-1">
                              Min order: {formatPrice(minOrder)}
                            </p>
                          )}
                        </div>
                      </>
                    ) : (
                      <div className="text-center py-6 text-gray-500">
                        <ShoppingCart className="h-10 w-10 mx-auto mb-2 opacity-30" />
                        <p>Your cart is empty</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Disclaimer */}
                <Card className="border-amber-300 bg-amber-50">
                  <CardContent className="pt-4">
                    <div className="flex gap-2 text-sm text-amber-800">
                      <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                      <p>{bookingRules.pickup.disclaimer}</p>
                    </div>
                  </CardContent>
                </Card>

                <Button
                  onClick={handleSubmit}
                  className="w-full bg-[#5c1e1e] hover:bg-[#8b2c2c] text-white py-6 text-lg"
                  disabled={!selectedCenter || !name || !phone || !pickupTime || cartItemCount === 0 || cartTotal < minOrder}
                  data-testid="pickup-submit-btn"
                >
                  <MessageCircle className="h-5 w-5 mr-2" />
                  Place Order via WhatsApp
                </Button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Review Section */
        <div className="container mx-auto px-4 py-8">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="max-w-2xl mx-auto"
          >
            <Card className="border-amber-200 shadow-xl">
              <CardHeader className="bg-gradient-to-r from-[#5c1e1e] to-[#8b2c2c] text-white rounded-t-lg">
                <CardTitle className="text-xl">Review Your Order</CardTitle>
              </CardHeader>
              <CardContent className="pt-6 space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">Center</p>
                    <p className="font-semibold">{currentCenter?.displayName}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Pickup Time</p>
                    <p className="font-semibold">{pickupTime}</p>
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

                <div className="border-t pt-4">
                  <p className="font-semibold mb-3">Order Items:</p>
                  <div className="space-y-2">
                    {Object.values(cart).map(item => (
                      <div key={item.id} className="flex justify-between text-sm">
                        <span>{item.name} × {item.qty}</span>
                        <span>{formatPrice(item.price * item.qty)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="flex justify-between font-bold text-lg pt-3 border-t mt-3">
                    <span>Total:</span>
                    <span className="text-[#5c1e1e]">{formatPrice(cartTotal)}</span>
                  </div>
                </div>

                {specialInstructions && (
                  <div className="border-t pt-4">
                    <p className="text-gray-500 text-sm">Special Instructions:</p>
                    <p className="text-sm">{specialInstructions}</p>
                  </div>
                )}

                <div className="flex gap-4 pt-4">
                  <Button
                    variant="outline"
                    onClick={() => setShowReview(false)}
                    className="flex-1"
                  >
                    Edit Order
                  </Button>
                  <Button
                    onClick={confirmOrder}
                    className="flex-1 bg-green-600 hover:bg-green-700"
                    data-testid="pickup-confirm-btn"
                  >
                    <MessageCircle className="h-5 w-5 mr-2" />
                    Confirm & Send
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      )}

      {/* Mobile Cart Button */}
      {cartItemCount > 0 && !showReview && (
        <div className="fixed bottom-4 left-4 right-4 lg:hidden z-50">
          <Button
            onClick={() => setShowCart(!showCart)}
            className="w-full bg-[#5c1e1e] hover:bg-[#8b2c2c] text-white py-4"
          >
            <ShoppingCart className="h-5 w-5 mr-2" />
            View Cart ({cartItemCount}) • {formatPrice(cartTotal)}
          </Button>
        </div>
      )}
    </div>
  );
};

const MenuItemCard = ({ item, cart, updateCart, formatPrice }) => {
  const inCart = cart[item.id]?.qty || 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center justify-between p-3 bg-white rounded-lg border border-amber-100 hover:border-amber-300 hover:shadow-md transition-all"
    >
      <div className="flex items-center gap-3 flex-1">
        <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
          <Leaf className="h-4 w-4 text-green-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-900 truncate">{item.name}</p>
          <p className="text-sm font-semibold text-[#5c1e1e]">{formatPrice(item.price)}</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {inCart > 0 ? (
          <>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => updateCart(item, -1)}
            >
              <Minus className="h-4 w-4" />
            </Button>
            <span className="w-8 text-center font-semibold">{inCart}</span>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => updateCart(item, 1)}
            >
              <Plus className="h-4 w-4" />
            </Button>
          </>
        ) : (
          <Button
            variant="outline"
            size="sm"
            className="border-[#5c1e1e] text-[#5c1e1e] hover:bg-[#5c1e1e] hover:text-white"
            onClick={() => updateCart(item, 1)}
          >
            <Plus className="h-4 w-4 mr-1" />
            Add
          </Button>
        )}
      </div>
    </motion.div>
  );
};

export default Pickup;
