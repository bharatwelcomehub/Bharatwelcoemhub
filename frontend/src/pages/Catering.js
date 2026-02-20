import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import { UtensilsCrossed, Check, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Catering = () => {
  const navigate = useNavigate();
  const [locations, setLocations] = useState([]);
  const [step, setStep] = useState(1);
  
  // Form data
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    address: '',
    eventDate: '',
    eventTime: '',
    guests: 20,
    celebrationType: '',
    locationId: '',
    package: null,
    deliveryRequired: 'yes'
  });

  // Menu selections
  const [menuSelections, setMenuSelections] = useState({
    starter: [],
    main: [],
    spMain: [],
    dessert: [],
    roti: [],
    rice: [],
    drink: [],
    side: [],
    chutney: []
  });

  // Package rules
  const packageRules = {
    1: { starter: 1, main: 2, spMain: 0, roti: 1, rice: 1, side: 1, dessert: 1, chutney: 2, drink: 0 },
    2: { starter: 2, main: 2, spMain: 0, roti: 1, rice: 1, side: 1, dessert: 0, chutney: 1, drink: 1 },
    3: { starter: 2, main: 2, spMain: 1, roti: 1, rice: 2, side: 1, dessert: 2, chutney: 0, drink: 1 },
    4: { starter: 3, main: 2, spMain: 1, roti: 1, rice: 2, side: 1, dessert: 2, chutney: 0, drink: 2 }
  };

  // Pricing
  const pricing = {
    india: { 1: 540, 2: 550, 3: 650, 4: 750 },
    perth: { 1: 35, 2: 40, 3: 55, 4: 65 }
  };

  // Menu items
  const menuItems = {
    starter: ['Kothimbir Vadi', 'Batata Vada', 'Sabudana Vada', 'Mutter Kachori', 'Palak Bhaji'],
    spMain: ['Kaju Curry', 'Maswadi', 'Bharit', 'Palat Patal Bhaji', 'Bhedichi Bhaji'],
    main: ['Zhunka', 'Pithala', 'Ravan Pithala', 'Bharali Vangi', 'Matki Usal', 'Dry Aloo', 'Jeera Aloo', 'Shev Bhaji', 'Patwadi Rassa', 'Akkha Masur', 'Dubak Vadi', 'Barbati Usal', 'Aloo Gobi Mutter'],
    dessert: ['Basundi', 'Ukadiche Modak', 'Shirwale', 'Khawa Poli', 'Tilgul Poli', 'Shrikhanda', 'Rava Sheera', 'Shewaya Kheer', 'Puran Poli', 'Chirote', 'Gulshela'],
    roti: ['Chapati (1 pc)', 'Puri Set (3 pc)', 'Jowar Bhakari (1 pc)'],
    rice: ['Masala Bhat', 'Ravan Bhat', 'Bhaji Bhat', 'Tup Bhat', 'Dahi Bhat', 'Steam Rice'],
    drink: ['Buttermilk', 'Masala Lime', 'Masala Kokum', 'Piyush', 'Solkadhi'],
    side: ['Papad', 'Koshimbir', 'Salad'],
    chutney: ['Peanut', 'Til', 'Lasun', 'Metkut', 'Thecha']
  };

  const packages = [
    { id: 1, name: 'Classic', price: '₹540', desc: '1 starter • 2 mains • 1 roti • 1 rice • 1 side • 1 dessert • 2 chutneys' },
    { id: 2, name: 'Premium', price: '₹550', desc: '2 starters • 2 mains • 1 roti • 1 rice • 1 side • 1 chutney • 1 drink' },
    { id: 3, name: 'Special Feast', price: '₹650', desc: '2 starters • 2 mains • 1 special • 1 roti • 2 rice • 1 side • 2 desserts • 1 drink' },
    { id: 4, name: 'Royal Feast', price: '₹750', desc: '3 starters • 2 mains • 1 special • 1 roti • 2 rice • 1 side • 2 desserts • 2 drinks', recommended: true }
  ];

  useEffect(() => {
    fetchLocations();
  }, []);

  const fetchLocations = async () => {
    try {
      const response = await axios.get(`${API}/locations`);
      setLocations(response.data);
    } catch (error) {
      console.error('Failed to fetch locations:', error);
    }
  };

  const getSelectedLocation = () => {
    return locations.find(loc => loc.id === formData.locationId);
  };

  const isPerth = () => {
    const location = getSelectedLocation();
    return location?.country === 'Australia';
  };

  const calculateTotal = () => {
    if (!formData.package) return 0;
    const pricePerGuest = isPerth() ? pricing.perth[formData.package] : pricing.india[formData.package];
    return pricePerGuest * formData.guests;
  };

  const getCurrency = () => isPerth() ? '$' : '₹';

  const handleMenuToggle = (category, item) => {
    const current = menuSelections[category];
    const rules = packageRules[formData.package];
    const max = rules[category];

    if (current.includes(item)) {
      setMenuSelections({
        ...menuSelections,
        [category]: current.filter(i => i !== item)
      });
    } else {
      if (current.length >= max) {
        toast.error(`Maximum ${max} ${category} items allowed for this package`);
        return;
      }
      setMenuSelections({
        ...menuSelections,
        [category]: [...current, item]
      });
    }
  };

  const getSelectionStatus = (category) => {
    if (!formData.package) return null;
    const rules = packageRules[formData.package];
    const max = rules[category];
    const current = menuSelections[category].length;

    if (max === 0) return { type: 'disabled', message: 'Not included in this package' };
    if (current === max) return { type: 'complete', message: '✓ Complete' };
    if (current > max) return { type: 'error', message: `Remove ${current - max} items` };
    return { type: 'pending', message: `Select ${max - current} more` };
  };

  const canProceed = () => {
    if (step === 1) {
      return formData.name && formData.phone && formData.address && 
             formData.eventDate && formData.eventTime && 
             formData.guests >= 20 && formData.locationId;
    }
    if (step === 2) {
      return formData.package !== null;
    }
    if (step === 3) {
      // Check all menu selections meet requirements
      const rules = packageRules[formData.package];
      return Object.keys(rules).every(category => {
        const required = rules[category];
        const selected = menuSelections[category].length;
        return selected === required;
      });
    }
    return false;
  };

  const handleSubmit = () => {
    const location = getSelectedLocation();
    const pkg = packages.find(p => p.id === formData.package);
    
    // Build WhatsApp message
    const menuText = Object.keys(menuSelections).map(category => {
      const items = menuSelections[category];
      if (items.length === 0) return '';
      const label = category.charAt(0).toUpperCase() + category.slice(1);
      return `${label}: ${items.join(', ')}`;
    }).filter(Boolean).join('\n');

    const message = `CATERING ENQUIRY - Purnabramha

Event Details:
Name: ${formData.name}
Phone: ${formData.phone}
Email: ${formData.email}
Address: ${formData.address}
Event Date: ${formData.eventDate}
Event Time: ${formData.eventTime}
Guests: ${formData.guests}
${formData.celebrationType ? `Celebration: ${formData.celebrationType}` : ''}
Delivery Required: ${formData.deliveryRequired}

Location: ${location?.name}, ${location?.city}

Package Selected: ${pkg.name}
Total Cost: ${getCurrency()}${calculateTotal()}

Menu Selections:
${menuText}

Booking Date: ${new Date().toLocaleDateString()}
    `.trim();

    const whatsappUrl = `https://wa.me/${location?.whatsapp?.replace(/[^0-9]/g, '')}?text=${encodeURIComponent(message)}`;
    window.open(whatsappUrl, '_blank');
    toast.success('Opening WhatsApp...');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-cream to-white">
      <div className="container mx-auto px-4 lg:px-8 py-12 lg:py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <UtensilsCrossed className="h-16 w-16 mx-auto text-primary mb-4" />
          <h1 className="font-playfair text-4xl lg:text-6xl font-bold text-foreground mb-4 tracking-tight" data-testid=\"catering-title\">
            Catering Services
          </h1>
          <p className="text-lg text-foreground/70 font-manrope max-w-2xl mx-auto">
            Make your special occasions memorable with authentic Maharashtrian catering
          </p>
        </motion.div>

        {/* Progress Steps */}
        <div className="flex items-center justify-center mb-12">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center">
              <div className={`h-10 w-10 rounded-full flex items-center justify-center font-semibold ${
                step >= s ? 'bg-primary text-white' : 'bg-gray-200 text-gray-500'
              }`}>
                {s}
              </div>
              {s < 3 && <div className={`h-1 w-16 mx-2 ${step > s ? 'bg-primary' : 'bg-gray-200'}`} />}
            </div>
          ))}
        </div>

        {/* Step 1: Event Details */}
        {step === 1 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="max-w-2xl mx-auto"
          >
            <Card>
              <CardContent className="p-8">
                <h2 className="font-playfair text-2xl font-semibold mb-6">Event Details</h2>
                <div className="space-y-4">
                  <div>
                    <Label>Select Location *</Label>
                    <Select value={formData.locationId} onValueChange={(value) => setFormData({ ...formData, locationId: value })}>
                      <SelectTrigger>
                        <SelectValue placeholder=\"Choose location\" />
                      </SelectTrigger>
                      <SelectContent>
                        {locations.map(loc => (
                          <SelectItem key={loc.id} value={loc.id}>{loc.name}, {loc.city}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Your Name *</Label>
                      <Input
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        placeholder=\"Enter your name\"
                      />
                    </div>
                    <div>
                      <Label>Phone *</Label>
                      <Input
                        value={formData.phone}
                        onChange={(e) => setFormData({ ...formData, phone: e.target.value.replace(/\D/g, '') })}
                        placeholder=\"10 digit number\"
                      />
                    </div>
                  </div>

                  <div>
                    <Label>Email</Label>
                    <Input
                      type=\"email\"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder=\"your@email.com\"
                    />
                  </div>

                  <div>
                    <Label>Event Address *</Label>
                    <Textarea
                      value={formData.address}
                      onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                      placeholder=\"Enter complete address\"
                      rows={3}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Event Date *</Label>
                      <Input
                        type=\"date\"
                        value={formData.eventDate}
                        onChange={(e) => setFormData({ ...formData, eventDate: e.target.value })}
                        min={new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]}
                      />
                    </div>
                    <div>
                      <Label>Event Time *</Label>
                      <Input
                        type=\"time\"
                        value={formData.eventTime}
                        onChange={(e) => setFormData({ ...formData, eventTime: e.target.value })}
                      />
                    </div>
                  </div>

                  <div>
                    <Label>Number of Guests * (Min: 20)</Label>
                    <Input
                      type=\"number\"
                      min=\"20\"
                      value={formData.guests}
                      onChange={(e) => setFormData({ ...formData, guests: parseInt(e.target.value) || 20 })}
                    />
                  </div>

                  <div>
                    <Label>Celebration Type</Label>
                    <Select value={formData.celebrationType} onValueChange={(value) => setFormData({ ...formData, celebrationType: value })}>
                      <SelectTrigger>
                        <SelectValue placeholder=\"Optional\" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value=\"Birthday\">Birthday</SelectItem>
                        <SelectItem value=\"Anniversary\">Anniversary</SelectItem>
                        <SelectItem value=\"Wedding\">Wedding</SelectItem>
                        <SelectItem value=\"Corporate\">Corporate Event</SelectItem>
                        <SelectItem value=\"Other\">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <Button
                    onClick={() => setStep(2)}
                    disabled={!canProceed()}
                    className="w-full rounded-full bg-primary text-lg py-6"
                  >
                    Next: Select Package →
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Step 2: Package Selection */}
        {step === 2 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <h2 className="font-playfair text-3xl font-semibold text-center mb-8">Choose Your Package</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {packages.map((pkg) => (
                <Card
                  key={pkg.id}
                  className={`cursor-pointer transition-all ${
                    formData.package === pkg.id 
                      ? 'border-primary border-2 shadow-lg' 
                      : 'border-gray-200 hover:border-primary/50'
                  } ${pkg.recommended ? 'ring-2 ring-primary/20' : ''}`}
                  onClick={() => setFormData({ ...formData, package: pkg.id })}
                >
                  <CardContent className="p-6">
                    {pkg.recommended && (
                      <div className="bg-primary text-white text-xs font-bold px-2 py-1 rounded-full mb-2 inline-block">
                        Most Popular
                      </div>
                    )}
                    <h3 className="font-playfair text-xl font-semibold mb-2">{pkg.name}</h3>
                    <p className="text-2xl font-bold text-primary mb-3">{pkg.price}<span className="text-sm text-foreground/60">/guest</span></p>
                    <p className="text-sm text-foreground/70 font-manrope">{pkg.desc}</p>
                  </CardContent>
                </Card>
              ))}
            </div>

            {formData.package && (
              <Card className="max-w-md mx-auto">
                <CardContent className="p-6">
                  <h3 className="font-playfair text-xl font-semibold mb-4">Estimate</h3>
                  <div className="space-y-2 text-foreground/70 font-manrope">
                    <div className="flex justify-between">
                      <span>Package:</span>
                      <span className="font-semibold">{packages.find(p => p.id === formData.package)?.name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Guests:</span>
                      <span className="font-semibold">{formData.guests}</span>
                    </div>
                    <div className="border-t pt-2 flex justify-between text-lg">
                      <span className="font-semibold">Total:</span>
                      <span className="font-bold text-primary">{getCurrency()}{calculateTotal()}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="flex justify-center gap-4 mt-8">
              <Button variant=\"outline\" onClick={() => setStep(1)} className="rounded-full">
                ← Back
              </Button>
              <Button
                onClick={() => setStep(3)}
                disabled={!canProceed()}
                className="rounded-full bg-primary"
              >
                Next: Select Menu →
              </Button>
            </div>
          </motion.div>
        )}

        {/* Step 3: Menu Selection */}
        {step === 3 && formData.package && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <h2 className="font-playfair text-3xl font-semibold text-center mb-8">Customize Your Menu</h2>
            
            <div className="space-y-6">
              {Object.keys(menuItems).map((category) => {
                const status = getSelectionStatus(category);
                const rules = packageRules[formData.package];
                const max = rules[category];

                if (max === 0) return null;

                return (
                  <Card key={category}>
                    <CardContent className="p-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-playfair text-xl font-semibold capitalize">{category}</h3>
                        <div className="flex items-center gap-2">
                          <span className={`text-sm font-manrope ${
                            status.type === 'complete' ? 'text-green-600' :
                            status.type === 'error' ? 'text-red-600' :
                            'text-foreground/60'
                          }`}>
                            {status.message}
                          </span>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {menuItems[category].map((item) => {
                          const isSelected = menuSelections[category].includes(item);
                          return (
                            <label
                              key={item}
                              className={`flex items-center space-x-2 p-3 rounded-lg border cursor-pointer transition-all ${
                                isSelected ? 'border-primary bg-primary/5' : 'border-gray-200 hover:border-primary/50'
                              }`}
                            >
                              <Checkbox
                                checked={isSelected}
                                onCheckedChange={() => handleMenuToggle(category, item)}
                              />
                              <span className="text-sm font-manrope">{item}</span>
                            </label>
                          );
                        })}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            <div className="flex justify-center gap-4 mt-8">
              <Button variant=\"outline\" onClick={() => setStep(2)} className="rounded-full">
                ← Back
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!canProceed()}
                className="rounded-full bg-primary px-8"
              >
                Submit Enquiry via WhatsApp
              </Button>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default Catering;
