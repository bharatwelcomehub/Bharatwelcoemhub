import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Calendar, MapPin, Phone, MessageCircle, Users, Star, AlertCircle, CheckCircle, ChefHat, PartyPopper, Clock, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { toast } from 'sonner';

import centersData from '@/config/centers.json';
import cateringPackages from '@/config/catering-packages.json';
import bookingRules from '@/config/booking-rules.json';

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

  const allCenters = useMemo(() => [...centersData.india, ...centersData.australia], []);

  const filteredCenters = useMemo(() => {
    if (!selectedRegion) return [];
    return selectedRegion === 'india' ? centersData.india : centersData.australia;
  }, [selectedRegion]);

  const currentCenter = useMemo(() => {
    return allCenters.find(c => c.id === selectedCenter);
  }, [selectedCenter, allCenters]);

  const isAustralia = currentCenter?.country === 'Australia';
  const currencySymbol = isAustralia ? '$' : '₹';
  const packages = isAustralia ? cateringPackages.packages.australia : cateringPackages.packages.india;
  const menuOptions = cateringPackages.menuOptions;

  const currentPackage = packages.find(p => p.id === selectedPackage);

  const getMinDate = () => {
    const date = new Date();
    date.setDate(date.getDate() + bookingRules.catering.minAdvanceDays);
    return date.toISOString().split('T')[0];
  };

  const getMaxDate = () => {
    const date = new Date();
    date.setDate(date.getDate() + bookingRules.catering.maxAdvanceDays);
    return date.toISOString().split('T')[0];
  };

  const formatPrice = (price) => `${currencySymbol}${price.toFixed(2)}`;

  const estimatedTotal = useMemo(() => {
    if (!currentPackage || !guestCount) return 0;
    return currentPackage.pricePerPerson * parseInt(guestCount);
  }, [currentPackage, guestCount]);

  const toggleSelection = (category, itemId) => {
    setMenuSelections(prev => {
      const current = prev[category] || [];
      if (current.includes(itemId)) {
        return { ...prev, [category]: current.filter(id => id !== itemId) };
      }
      const maxAllowed = currentPackage?.requirements[category] || 0;
      if (current.length >= maxAllowed) {
        toast.error(`Maximum ${maxAllowed} ${category} allowed for this package`);
        return prev;
      }
      return { ...prev, [category]: [...current, itemId] };
    });
  };

  const getSelectedCount = (category) => {
    return (menuSelections[category] || []).length;
  };

  const generateGoogleMapsLink = () => {
    if (!address) return '';
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;
  };

  const validateSelections = () => {
    if (!currentPackage) return { valid: false, message: 'Please select a package' };
    
    const requirements = currentPackage.requirements;
    const errors = [];

    Object.entries(requirements).forEach(([category, required]) => {
      if (required > 0) {
        const selected = getSelectedCount(category);
        if (selected < required) {
          errors.push(`${category}: ${selected}/${required}`);
        }
      }
    });

    if (errors.length > 0) {
      return { valid: false, message: `Please complete menu selection: ${errors.join(', ')}` };
    }

    return { valid: true };
  };

  const generateWhatsAppMessage = () => {
    let message = `🎊 *PURNABRAMHA CATERING INQUIRY*\n\n`;
    message += `📍 *Center:* ${currentCenter?.displayName}\n`;
    message += `👤 *Name:* ${name}\n`;
    message += `📞 *Phone:* ${phone}\n`;
    message += `🏠 *Address:* ${address}\n`;
    if (needsDelivery) {
      message += `🚚 *Delivery:* Required\n`;
      message += `📍 *Maps:* ${generateGoogleMapsLink()}\n`;
    }
    message += `\n📅 *Event Date:* ${eventDate}\n`;
    message += `⏰ *Event Time:* ${eventTime}\n`;
    message += `👥 *Guests:* ${guestCount}\n`;
    message += `🎉 *Celebration:* ${bookingRules.catering.celebrationTypes.find(c => c.id === celebrationType)?.label || 'Not specified'}\n`;
    
    message += `\n━━━━━━━━━━━━━━━\n`;
    message += `*📋 PACKAGE: ${currentPackage?.name}*\n`;
    message += `_${currentPackage?.description}_\n`;
    message += `💰 Rate: ${formatPrice(currentPackage?.pricePerPerson || 0)}/person\n\n`;

    message += `*🍽️ MENU SELECTIONS:*\n`;

    const categoryLabels = {
      starters: '🥟 Starters',
      mains: '🍲 Main Course',
      special: '⭐ Special Bhaji',
      desserts: '🍮 Desserts',
      roti: '🫓 Roti/Bhakari',
      rice: '🍚 Rice',
      drinks: '🥤 Drinks',
      sides: '🥗 Sides',
      chutney: '🌶️ Chutney'
    };

    Object.entries(menuSelections).forEach(([category, items]) => {
      if (items.length > 0) {
        const categoryOptions = menuOptions[category === 'mains' ? 'simpleBhaji' : category === 'special' ? 'specialBhaji' : category];
        const itemNames = items.map(id => categoryOptions?.find(opt => opt.id === id)?.name || id);
        message += `${categoryLabels[category] || category}: ${itemNames.join(', ')}\n`;
      }
    });

    message += `\n━━━━━━━━━━━━━━━\n`;
    message += `*💰 ESTIMATED TOTAL: ${formatPrice(estimatedTotal)}*\n`;
    message += `_(${guestCount} guests × ${formatPrice(currentPackage?.pricePerPerson || 0)})_\n`;
    message += `\n⚠️ _Final quote will be confirmed after discussion. Prices may vary based on customization._`;

    return encodeURIComponent(message);
  };

  const handleSubmit = () => {
    if (!selectedCenter || !name || !phone || !address || !eventDate || !eventTime || !guestCount || !selectedPackage) {
      toast.error('Please fill all required fields');
      return;
    }
    if (parseInt(guestCount) < bookingRules.catering.minGuests) {
      toast.error(`Minimum ${bookingRules.catering.minGuests} guests required for catering`);
      return;
    }
    const validation = validateSelections();
    if (!validation.valid) {
      toast.error(validation.message);
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
            <h1 className="text-4xl md:text-5xl font-bold mb-4" data-testid="catering-title">
              🎊 Catering Services
            </h1>
            <p className="text-lg text-amber-200">
              Authentic Maharashtrian cuisine for your special occasions
            </p>
            <div className="mt-4 flex items-center justify-center gap-4 text-amber-300 text-sm flex-wrap">
              <span className="flex items-center gap-1">
                <Users className="h-4 w-4" />
                Min {bookingRules.catering.minGuests} guests
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                Book {bookingRules.catering.minAdvanceDays}+ days ahead
              </span>
            </div>
          </motion.div>
        </div>
      </section>

      <div className="container mx-auto px-4 py-8">
        {!showReview ? (
          <div className="grid lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-6">
              {/* Step 1: Event Details */}
              <Card className="border-amber-200 shadow-lg">
                <CardHeader className="bg-gradient-to-r from-amber-100 to-orange-100 rounded-t-lg">
                  <CardTitle className="flex items-center gap-2 text-[#5c1e1e]">
                    <PartyPopper className="h-5 w-5" />
                    Step 1: Event & Contact Details
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6 space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <Label>Region *</Label>
                      <Select value={selectedRegion} onValueChange={(v) => { setSelectedRegion(v); setSelectedCenter(''); setSelectedPackage(''); setMenuSelections({}); }}>
                        <SelectTrigger data-testid="catering-region-select">
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
                        <SelectTrigger data-testid="catering-center-select">
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
                      <Label>Your Name *</Label>
                      <Input
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Full name"
                        className="border-amber-200"
                        data-testid="catering-name"
                      />
                    </div>
                    <div>
                      <Label>Phone *</Label>
                      <Input
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                        placeholder="Phone number"
                        className="border-amber-200"
                        data-testid="catering-phone"
                      />
                    </div>
                  </div>

                  <div>
                    <Label>Event Address *</Label>
                    <Input
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      placeholder="Full address of the venue"
                      className="border-amber-200"
                      data-testid="catering-address"
                    />
                    {address && (
                      <a
                        href={generateGoogleMapsLink()}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-sm text-blue-600 mt-1 hover:underline"
                      >
                        <ExternalLink className="h-3 w-3" />
                        Open in Google Maps
                      </a>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="delivery"
                      checked={needsDelivery}
                      onCheckedChange={setNeedsDelivery}
                    />
                    <label htmlFor="delivery" className="text-sm cursor-pointer">
                      Delivery Required (to the event venue)
                    </label>
                  </div>

                  <div className="grid md:grid-cols-3 gap-4">
                    <div>
                      <Label>Event Date *</Label>
                      <Input
                        type="date"
                        value={eventDate}
                        onChange={(e) => setEventDate(e.target.value)}
                        min={getMinDate()}
                        max={getMaxDate()}
                        className="border-amber-200"
                        data-testid="catering-date"
                      />
                    </div>
                    <div>
                      <Label>Event Time *</Label>
                      <Input
                        type="time"
                        value={eventTime}
                        onChange={(e) => setEventTime(e.target.value)}
                        className="border-amber-200"
                        data-testid="catering-time"
                      />
                    </div>
                    <div>
                      <Label>Number of Guests *</Label>
                      <Input
                        type="number"
                        value={guestCount}
                        onChange={(e) => setGuestCount(e.target.value)}
                        min={bookingRules.catering.minGuests}
                        className="border-amber-200"
                        data-testid="catering-guests"
                      />
                    </div>
                  </div>

                  <div>
                    <Label>Celebration Type</Label>
                    <Select value={celebrationType} onValueChange={setCelebrationType}>
                      <SelectTrigger data-testid="catering-celebration-select">
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        {bookingRules.catering.celebrationTypes.map(type => (
                          <SelectItem key={type.id} value={type.id}>{type.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {parseInt(guestCount) >= 50 && (
                    <div className="p-3 bg-amber-100 rounded-lg flex items-center gap-2">
                      <Star className="h-5 w-5 text-amber-600" />
                      <span className="text-sm text-amber-800">
                        🎉 For larger gatherings we recommend: <strong>Royal Feast (Option 4)</strong>
                      </span>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Step 2: Choose Package */}
              <Card className="border-amber-200 shadow-lg">
                <CardHeader className="bg-gradient-to-r from-amber-100 to-orange-100 rounded-t-lg">
                  <CardTitle className="flex items-center gap-2 text-[#5c1e1e]">
                    <ChefHat className="h-5 w-5" />
                    Step 2: Choose Package
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6">
                  <RadioGroup value={selectedPackage} onValueChange={(v) => { setSelectedPackage(v); setMenuSelections({}); }}>
                    <div className="grid md:grid-cols-2 gap-4">
                      {packages.map(pkg => (
                        <div key={pkg.id}>
                          <RadioGroupItem value={pkg.id} id={pkg.id} className="peer sr-only" />
                          <label
                            htmlFor={pkg.id}
                            className={`block p-4 rounded-lg border-2 cursor-pointer transition-all ${
                              selectedPackage === pkg.id
                                ? 'border-[#5c1e1e] bg-amber-50'
                                : 'border-gray-200 hover:border-amber-300'
                            }`}
                            data-testid={`package-${pkg.id}`}
                          >
                            <div className="flex items-start justify-between mb-2">
                              <div>
                                <h4 className="font-bold text-[#5c1e1e]">{pkg.name}</h4>
                                {pkg.isPopular && (
                                  <Badge className="bg-amber-500 text-xs">Most Popular</Badge>
                                )}
                              </div>
                              <span className="font-bold text-lg text-[#5c1e1e]">
                                {formatPrice(pkg.pricePerPerson)}/pp
                              </span>
                            </div>
                            <p className="text-sm text-gray-600">{pkg.description}</p>
                            <div className="mt-2 text-xs text-gray-500">
                              {Object.entries(pkg.requirements)
                                .filter(([_, v]) => v > 0)
                                .map(([k, v]) => `${v} ${k}`)
                                .join(' • ')}
                            </div>
                          </label>
                        </div>
                      ))}
                    </div>
                  </RadioGroup>
                </CardContent>
              </Card>

              {/* Step 3: Menu Selection */}
              {currentPackage && (
                <Card className="border-amber-200 shadow-lg">
                  <CardHeader className="bg-gradient-to-r from-amber-100 to-orange-100 rounded-t-lg">
                    <CardTitle className="flex items-center gap-2 text-[#5c1e1e]">
                      <ChefHat className="h-5 w-5" />
                      Step 3: Menu Selection
                    </CardTitle>
                    <CardDescription>
                      Select items based on your package requirements
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-6 space-y-6">
                    {/* Starters */}
                    {currentPackage.requirements.starters > 0 && (
                      <MenuSection
                        title="🥟 Starters (2 pc each)"
                        category="starters"
                        options={menuOptions.starters}
                        selections={menuSelections}
                        required={currentPackage.requirements.starters}
                        toggleSelection={toggleSelection}
                        getSelectedCount={getSelectedCount}
                      />
                    )}

                    {/* Special Bhaji */}
                    {currentPackage.requirements.special > 0 && (
                      <MenuSection
                        title="⭐ Special Bhaji (80 gms)"
                        category="special"
                        options={menuOptions.specialBhaji}
                        selections={menuSelections}
                        required={currentPackage.requirements.special}
                        toggleSelection={toggleSelection}
                        getSelectedCount={getSelectedCount}
                      />
                    )}

                    {/* Main Course */}
                    {currentPackage.requirements.mains > 0 && (
                      <MenuSection
                        title="🍲 Simple Bhaji (80 gms)"
                        category="mains"
                        options={menuOptions.simpleBhaji}
                        selections={menuSelections}
                        required={currentPackage.requirements.mains}
                        toggleSelection={toggleSelection}
                        getSelectedCount={getSelectedCount}
                      />
                    )}

                    {/* Desserts */}
                    {currentPackage.requirements.dessert > 0 && (
                      <MenuSection
                        title="🍮 Desserts (80 gms)"
                        category="desserts"
                        options={menuOptions.desserts}
                        selections={menuSelections}
                        required={currentPackage.requirements.dessert}
                        toggleSelection={toggleSelection}
                        getSelectedCount={getSelectedCount}
                      />
                    )}

                    {/* Roti */}
                    {currentPackage.requirements.roti > 0 && (
                      <MenuSection
                        title="🫓 Roti / Bhakari"
                        category="roti"
                        options={menuOptions.roti}
                        selections={menuSelections}
                        required={currentPackage.requirements.roti}
                        toggleSelection={toggleSelection}
                        getSelectedCount={getSelectedCount}
                      />
                    )}

                    {/* Rice */}
                    {currentPackage.requirements.rice > 0 && (
                      <MenuSection
                        title="🍚 Rice (150 gms)"
                        category="rice"
                        options={menuOptions.rice}
                        selections={menuSelections}
                        required={currentPackage.requirements.rice}
                        toggleSelection={toggleSelection}
                        getSelectedCount={getSelectedCount}
                      />
                    )}

                    {/* Drinks */}
                    {currentPackage.requirements.drink > 0 && (
                      <MenuSection
                        title="🥤 Drinks (200ml)"
                        category="drinks"
                        options={menuOptions.drinks}
                        selections={menuSelections}
                        required={currentPackage.requirements.drink}
                        toggleSelection={toggleSelection}
                        getSelectedCount={getSelectedCount}
                      />
                    )}

                    {/* Sides */}
                    {currentPackage.requirements.side > 0 && (
                      <MenuSection
                        title="🥗 Sides"
                        category="sides"
                        options={menuOptions.sides}
                        selections={menuSelections}
                        required={currentPackage.requirements.side}
                        toggleSelection={toggleSelection}
                        getSelectedCount={getSelectedCount}
                      />
                    )}

                    {/* Chutney */}
                    {currentPackage.requirements.chutney > 0 && (
                      <MenuSection
                        title="🌶️ Chutney"
                        category="chutney"
                        options={menuOptions.chutney}
                        selections={menuSelections}
                        required={currentPackage.requirements.chutney}
                        toggleSelection={toggleSelection}
                        getSelectedCount={getSelectedCount}
                      />
                    )}
                  </CardContent>
                </Card>
              )}
            </div>

            {/* Sidebar - Summary */}
            <div className="lg:col-span-1">
              <div className="sticky top-24 space-y-6">
                <Card className="border-amber-200 shadow-lg">
                  <CardHeader className="bg-gradient-to-r from-[#5c1e1e] to-[#8b2c2c] text-white rounded-t-lg">
                    <CardTitle>Booking Summary</CardTitle>
                  </CardHeader>
                  <CardContent className="pt-4 space-y-3">
                    <div className="space-y-2 text-sm">
                      <p><strong>Center:</strong> {currentCenter?.displayName || '—'}</p>
                      <p><strong>Name:</strong> {name || '—'}</p>
                      <p><strong>Phone:</strong> {phone || '—'}</p>
                      <p><strong>Date:</strong> {eventDate || '—'}</p>
                      <p><strong>Time:</strong> {eventTime || '—'}</p>
                      <p><strong>Guests:</strong> {guestCount}</p>
                      <p><strong>Package:</strong> {currentPackage?.name || '—'}</p>
                    </div>

                    {currentPackage && (
                      <div className="border-t pt-3">
                        <div className="flex justify-between text-sm mb-1">
                          <span>Rate per person:</span>
                          <span>{formatPrice(currentPackage.pricePerPerson)}</span>
                        </div>
                        <div className="flex justify-between font-bold text-lg pt-2 border-t">
                          <span>Estimated Total:</span>
                          <span className="text-[#5c1e1e]">{formatPrice(estimatedTotal)}</span>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          ({guestCount} guests × {formatPrice(currentPackage.pricePerPerson)})
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Disclaimer */}
                <Card className="border-amber-300 bg-amber-50">
                  <CardContent className="pt-4">
                    <div className="flex gap-2 text-sm text-amber-800">
                      <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                      <p>{bookingRules.catering.disclaimer}</p>
                    </div>
                  </CardContent>
                </Card>

                <Button
                  onClick={handleSubmit}
                  className="w-full bg-[#5c1e1e] hover:bg-[#8b2c2c] text-white py-6 text-lg"
                  disabled={!selectedCenter || !name || !phone || !address || !eventDate || !eventTime || !selectedPackage}
                  data-testid="catering-submit-btn"
                >
                  <MessageCircle className="h-5 w-5 mr-2" />
                  Send Inquiry via WhatsApp
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
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="h-6 w-6" />
                  Review Your Inquiry
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-6 space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">Center</p>
                    <p className="font-semibold">{currentCenter?.displayName}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Event Date</p>
                    <p className="font-semibold">{eventDate} at {eventTime}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Name</p>
                    <p className="font-semibold">{name}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Guests</p>
                    <p className="font-semibold">{guestCount}</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-gray-500">Address</p>
                    <p className="font-semibold">{address}</p>
                  </div>
                </div>

                <div className="border-t pt-4">
                  <p className="font-semibold mb-2">Package: {currentPackage?.name}</p>
                  <div className="flex justify-between font-bold text-lg">
                    <span>Estimated Total:</span>
                    <span className="text-[#5c1e1e]">{formatPrice(estimatedTotal)}</span>
                  </div>
                </div>

                <div className="flex gap-4 pt-4">
                  <Button
                    variant="outline"
                    onClick={() => setShowReview(false)}
                    className="flex-1"
                  >
                    Edit Inquiry
                  </Button>
                  <Button
                    onClick={confirmBooking}
                    className="flex-1 bg-green-600 hover:bg-green-700"
                    data-testid="catering-confirm-btn"
                  >
                    <MessageCircle className="h-5 w-5 mr-2" />
                    Confirm & Send
                  </Button>
                </div>
              </CardContent>
            </Card>
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
        <h4 className="font-semibold text-[#5c1e1e]">{title}</h4>
        <Badge variant={isComplete ? 'default' : 'outline'} className={isComplete ? 'bg-green-600' : ''}>
          {selected}/{required}
        </Badge>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {options.map(option => {
          const isSelected = (selections[category] || []).includes(option.id);
          return (
            <div
              key={option.id}
              onClick={() => toggleSelection(category, option.id)}
              className={`p-2 rounded-lg border cursor-pointer transition-all text-sm ${
                isSelected
                  ? 'border-[#5c1e1e] bg-amber-50 text-[#5c1e1e] font-medium'
                  : 'border-gray-200 hover:border-amber-300'
              }`}
            >
              <div className="flex items-center gap-2">
                <Checkbox checked={isSelected} className="pointer-events-none" />
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
