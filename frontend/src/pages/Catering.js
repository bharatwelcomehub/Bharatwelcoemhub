import { useState, useMemo, useEffect } from 'react';
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
import axios from 'axios';

import centersData from '@/config/centers.json';
import cateringPackages from '@/config/catering-packages.json';
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
  
  // Addon services state
  const [needsCrockery, setNeedsCrockery] = useState(false);
  const [crockeryHours, setCrockeryHours] = useState(1);
  const [needsStaff, setNeedsStaff] = useState(false);
  const [staffCount, setStaffCount] = useState(2);
  const [staffHours, setStaffHours] = useState(2);

  // Fetch menu from database for dynamic options
  useEffect(() => {
    const fetchMenu = async () => {
      try {
        const response = await axios.get(`${API}/api/menu`);
        setDbMenuItems(response.data);
      } catch (err) {
        console.log('Using fallback JSON menu options');
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

  const isAustralia = currentCenter?.country === 'Australia';
  const currencySymbol = isAustralia ? '$' : '₹';
  const packages = isAustralia ? cateringPackages.packages.australia : cateringPackages.packages.india;
  const menuOptions = cateringPackages.menuOptions;

  // Addon pricing
  const addonPricing = {
    crockery: {
      india: 3000, // per hour
      australia: 200 // per hour
    },
    staff: {
      india: 300, // per person per hour
      australia: 50 // per person per hour ($100 for 2 hours = $50/hr/person)
    }
  };

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

  // Calculate addon costs
  const crockeryTotal = useMemo(() => {
    if (!needsCrockery) return 0;
    const rate = isAustralia ? addonPricing.crockery.australia : addonPricing.crockery.india;
    return rate * crockeryHours;
  }, [needsCrockery, crockeryHours, isAustralia]);

  const staffTotal = useMemo(() => {
    if (!needsStaff) return 0;
    const rate = isAustralia ? addonPricing.staff.australia : addonPricing.staff.india;
    return rate * staffCount * staffHours;
  }, [needsStaff, staffCount, staffHours, isAustralia]);

  const foodTotal = useMemo(() => {
    if (!currentPackage || !guestCount) return 0;
    return currentPackage.pricePerPerson * parseInt(guestCount);
  }, [currentPackage, guestCount]);

  const estimatedTotal = useMemo(() => {
    return foodTotal + crockeryTotal + staffTotal;
  }, [foodTotal, crockeryTotal, staffTotal]);

  const toggleSelection = (category, itemId) => {
    setMenuSelections(prev => {
      const current = prev[category] || [];
      if (current.includes(itemId)) {
        return { ...prev, [category]: current.filter(id => id !== itemId) };
      }
      // Map plural category keys to singular requirement keys
      const requirementKeyMap = { desserts: 'dessert', drinks: 'drink', sides: 'side' };
      const reqKey = requirementKeyMap[category] || category;
      const maxAllowed = currentPackage?.requirements[reqKey] || 0;
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
    // Map singular requirement keys to plural category keys used in menuSelections
    const categoryKeyMap = { dessert: 'desserts', drink: 'drinks', side: 'sides' };

    Object.entries(requirements).forEach(([reqKey, required]) => {
      if (required > 0) {
        const category = categoryKeyMap[reqKey] || reqKey;
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
    let message = ``;
    message += `═══════════════════════\n`;
    message += `     *P U R N A B R A M H A*\n`;
    message += `  _World's First Intelligent Restaurant_\n`;
    message += `    _Chain Powered by A.AI Technology_\n`;
    message += `═══════════════════════\n\n`;
    message += `✦  *PREMIUM CATERING SERVICE*  ✦\n\n`;
    message += `───── Guest Details ─────\n`;
    message += `  *Name:*  ${name}\n`;
    message += `  *Phone:*  ${phone}\n`;
    message += `  *Venue:*  ${address}\n`;
    if (needsDelivery) {
      message += `  *Delivery:*  Required\n`;
      message += `  *Map:*  ${generateGoogleMapsLink()}\n`;
    }
    message += `\n───── Event Information ─────\n`;
    message += `  *Center:*  ${currentCenter?.displayName}\n`;
    message += `  *Date:*  ${eventDate}\n`;
    message += `  *Time:*  ${eventTime}\n`;
    message += `  *Guests:*  ${guestCount} persons\n`;
    message += `  *Occasion:*  ${bookingRules.catering.celebrationTypes.find(c => c.id === celebrationType)?.label || 'Not specified'}\n`;
    
    message += `\n═══════════════════════\n`;
    message += `  *${currentPackage?.name.toUpperCase()}*\n`;
    message += `  _${currentPackage?.description}_\n`;
    message += `  Rate: ${formatPrice(currentPackage?.pricePerPerson || 0)} per person\n`;
    message += `═══════════════════════\n\n`;

    message += `✦  *CURATED MENU*  ✦\n\n`;

    const categoryLabels = {
      starters: '  Starters',
      mains: '  Main Course',
      special: '  Special Bhaji',
      desserts: '  Desserts',
      roti: '  Roti & Bhakari',
      rice: '  Rice',
      drinks: '  Beverages',
      sides: '  Sides',
      chutney: '  Chutney'
    };

    Object.entries(menuSelections).forEach(([category, items]) => {
      if (items.length > 0) {
        const categoryOptions = menuOptions[category === 'mains' ? 'simpleBhaji' : category === 'special' ? 'specialBhaji' : category];
        const itemNames = items.map(id => categoryOptions?.find(opt => opt.id === id)?.name || id);
        message += `${categoryLabels[category] || category}\n`;
        itemNames.forEach(n => { message += `    • ${n}\n`; });
        message += `\n`;
      }
    });

    // Add addon services to message
    if (needsCrockery || needsStaff) {
      message += `───── Premium Add-ons ─────\n\n`;
      if (needsCrockery) {
        message += `  Crockery & Cutlery\n`;
        message += `    ${crockeryHours} hour(s) @ ${formatPrice(isAustralia ? addonPricing.crockery.australia : addonPricing.crockery.india)}/hr\n`;
        message += `    Total: ${formatPrice(crockeryTotal)}\n`;
        message += `    _Return by 9 AM next morning_\n\n`;
      }
      if (needsStaff) {
        message += `  Service Staff\n`;
        message += `    ${staffCount} person(s) × ${staffHours} hour(s)\n`;
        message += `    Total: ${formatPrice(staffTotal)}\n\n`;
      }
    }

    message += `═══════════════════════\n`;
    message += `       *COST SUMMARY*\n`;
    message += `═══════════════════════\n\n`;
    message += `  Food (${guestCount} × ${formatPrice(currentPackage?.pricePerPerson || 0)})\n`;
    message += `  ─────────────  ${formatPrice(foodTotal)}\n`;
    if (needsCrockery) {
      message += `  Crockery Rental\n`;
      message += `  ─────────────  ${formatPrice(crockeryTotal)}\n`;
    }
    if (needsStaff) {
      message += `  Service Staff\n`;
      message += `  ─────────────  ${formatPrice(staffTotal)}\n`;
    }
    message += `\n  ✦ *ESTIMATED TOTAL: ${formatPrice(estimatedTotal)}* ✦\n`;
    message += `\n═══════════════════════\n`;
    message += `  _Final pricing confirmed after_\n`;
    message += `  _personal consultation. Customization_\n`;
    message += `  _options available._\n`;
    message += `═══════════════════════\n`;
    message += `\n  _Purnabramha — Authentic Maharashtrian_\n`;
    message += `  _Cuisine Since 2012_\n`;

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

              {/* Step 4: Addon Services */}
              {currentPackage && (
                <Card className="border-amber-200 shadow-lg">
                  <CardHeader className="bg-gradient-to-r from-amber-100 to-orange-100 rounded-t-lg">
                    <CardTitle className="flex items-center gap-2 text-[#5c1e1e]">
                      🛎️ Step 4: Addon Services (Optional)
                    </CardTitle>
                    <CardDescription>
                      Need crockery, cutlery, or service staff? We've got you covered!
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-6 space-y-6">
                    {/* Crockery Rental */}
                    <div className="p-4 border border-amber-200 rounded-lg">
                      <div className="flex items-start gap-3 mb-4">
                        <Checkbox
                          id="crockery"
                          checked={needsCrockery}
                          onCheckedChange={setNeedsCrockery}
                          data-testid="crockery-checkbox"
                        />
                        <div className="flex-1">
                          <label htmlFor="crockery" className="font-semibold cursor-pointer text-[#5c1e1e]">
                            🍽️ Crockery & Cutlery Rental
                          </label>
                          <p className="text-sm text-gray-600 mt-1">
                            Plates, Bowls, Spoons, Serving Dishes for all guests
                          </p>
                          <p className="text-sm font-medium text-amber-700 mt-1">
                            {isAustralia ? '$200' : '₹3,000'} per hour
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            📦 Return by 9 AM next morning • No cleaning needed • (Closed Tuesdays)
                          </p>
                        </div>
                      </div>
                      
                      {needsCrockery && (
                        <div className="ml-7 p-3 bg-amber-50 rounded-lg">
                          <Label className="text-sm">Number of Hours</Label>
                          <div className="flex items-center gap-3 mt-2">
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() => setCrockeryHours(Math.max(1, crockeryHours - 1))}
                              className="h-8 w-8"
                            >
                              <span className="text-lg">-</span>
                            </Button>
                            <span className="text-xl font-bold w-12 text-center">{crockeryHours}</span>
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() => setCrockeryHours(crockeryHours + 1)}
                              className="h-8 w-8"
                            >
                              <span className="text-lg">+</span>
                            </Button>
                            <span className="text-sm text-gray-600 ml-2">
                              = <strong>{formatPrice(crockeryTotal)}</strong>
                            </span>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Service Staff */}
                    <div className="p-4 border border-amber-200 rounded-lg">
                      <div className="flex items-start gap-3 mb-4">
                        <Checkbox
                          id="staff"
                          checked={needsStaff}
                          onCheckedChange={setNeedsStaff}
                          data-testid="staff-checkbox"
                        />
                        <div className="flex-1">
                          <label htmlFor="staff" className="font-semibold cursor-pointer text-[#5c1e1e]">
                            👨‍🍳 Service Staff
                          </label>
                          <p className="text-sm text-gray-600 mt-1">
                            Professional servers to help with your event
                          </p>
                          <p className="text-sm font-medium text-amber-700 mt-1">
                            {isAustralia ? '$50 per person/hour' : '₹300 per person/hour'}
                          </p>
                        </div>
                      </div>
                      
                      {needsStaff && (
                        <div className="ml-7 p-3 bg-amber-50 rounded-lg space-y-3">
                          <div>
                            <Label className="text-sm">Number of Staff</Label>
                            <div className="flex items-center gap-3 mt-2">
                              <Button
                                variant="outline"
                                size="icon"
                                onClick={() => setStaffCount(Math.max(1, staffCount - 1))}
                                className="h-8 w-8"
                              >
                                <span className="text-lg">-</span>
                              </Button>
                              <span className="text-xl font-bold w-12 text-center">{staffCount}</span>
                              <Button
                                variant="outline"
                                size="icon"
                                onClick={() => setStaffCount(staffCount + 1)}
                                className="h-8 w-8"
                              >
                                <span className="text-lg">+</span>
                              </Button>
                              <span className="text-sm text-gray-600">person(s)</span>
                            </div>
                          </div>
                          <div>
                            <Label className="text-sm">Number of Hours</Label>
                            <div className="flex items-center gap-3 mt-2">
                              <Button
                                variant="outline"
                                size="icon"
                                onClick={() => setStaffHours(Math.max(1, staffHours - 1))}
                                className="h-8 w-8"
                              >
                                <span className="text-lg">-</span>
                              </Button>
                              <span className="text-xl font-bold w-12 text-center">{staffHours}</span>
                              <Button
                                variant="outline"
                                size="icon"
                                onClick={() => setStaffHours(staffHours + 1)}
                                className="h-8 w-8"
                              >
                                <span className="text-lg">+</span>
                              </Button>
                              <span className="text-sm text-gray-600">hour(s)</span>
                            </div>
                          </div>
                          <div className="pt-2 border-t">
                            <span className="text-sm">
                              Staff Cost: <strong>{formatPrice(staffTotal)}</strong>
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
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
                      <div className="border-t pt-3 space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Food ({guestCount} guests):</span>
                          <span>{formatPrice(foodTotal)}</span>
                        </div>
                        {needsCrockery && (
                          <div className="flex justify-between text-sm text-amber-700">
                            <span>Crockery ({crockeryHours}hr):</span>
                            <span>{formatPrice(crockeryTotal)}</span>
                          </div>
                        )}
                        {needsStaff && (
                          <div className="flex justify-between text-sm text-amber-700">
                            <span>Staff ({staffCount}×{staffHours}hr):</span>
                            <span>{formatPrice(staffTotal)}</span>
                          </div>
                        )}
                        <div className="flex justify-between font-bold text-lg pt-2 border-t">
                          <span>Estimated Total:</span>
                          <span className="text-[#5c1e1e]">{formatPrice(estimatedTotal)}</span>
                        </div>
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
                <h2 className="text-2xl font-playfair font-bold text-white mb-1">Premium Catering</h2>
                <p className="text-amber-300/70 text-xs italic">World's First Intelligent Restaurant Chain</p>
                <div className="w-16 h-0.5 bg-amber-400 mx-auto mt-3" />
              </div>

              <CardContent className="pt-6 space-y-5 bg-gradient-to-b from-amber-50/50 to-white">
                {/* Guest & Event Info */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="bg-white p-3 rounded-lg border border-amber-100 shadow-sm">
                    <p className="text-amber-600 text-xs uppercase tracking-wider mb-1">Guest</p>
                    <p className="font-semibold text-[#5c1e1e]">{name}</p>
                    <p className="text-gray-500 text-xs mt-0.5">{phone}</p>
                  </div>
                  <div className="bg-white p-3 rounded-lg border border-amber-100 shadow-sm">
                    <p className="text-amber-600 text-xs uppercase tracking-wider mb-1">Event</p>
                    <p className="font-semibold text-[#5c1e1e]">{eventDate}</p>
                    <p className="text-gray-500 text-xs mt-0.5">{eventTime} • {guestCount} guests</p>
                  </div>
                  <div className="bg-white p-3 rounded-lg border border-amber-100 shadow-sm">
                    <p className="text-amber-600 text-xs uppercase tracking-wider mb-1">Center</p>
                    <p className="font-semibold text-[#5c1e1e]">{currentCenter?.displayName}</p>
                  </div>
                  <div className="bg-white p-3 rounded-lg border border-amber-100 shadow-sm">
                    <p className="text-amber-600 text-xs uppercase tracking-wider mb-1">Package</p>
                    <p className="font-semibold text-[#5c1e1e]">{currentPackage?.name}</p>
                    <p className="text-gray-500 text-xs mt-0.5">{formatPrice(currentPackage?.pricePerPerson || 0)}/person</p>
                  </div>
                  <div className="col-span-2 bg-white p-3 rounded-lg border border-amber-100 shadow-sm">
                    <p className="text-amber-600 text-xs uppercase tracking-wider mb-1">Venue</p>
                    <p className="font-semibold text-[#5c1e1e]">{address}</p>
                  </div>
                </div>

                {/* Total */}
                <div className="bg-gradient-to-r from-[#5c1e1e] to-[#8b2c2c] rounded-xl p-4 text-center">
                  <p className="text-amber-300 text-xs uppercase tracking-wider mb-1">Estimated Total</p>
                  <p className="text-3xl font-bold text-white">{formatPrice(estimatedTotal)}</p>
                  <p className="text-amber-200/60 text-xs mt-1">Final pricing after consultation</p>
                </div>

                <div className="flex gap-3 pt-2">
                  <Button
                    variant="outline"
                    onClick={() => setShowReview(false)}
                    className="flex-1 border-amber-300 text-[#5c1e1e] hover:bg-amber-50"
                  >
                    Edit Inquiry
                  </Button>
                  <Button
                    onClick={confirmBooking}
                    className="flex-1 bg-green-600 hover:bg-green-700 shadow-lg"
                    data-testid="catering-confirm-btn"
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
