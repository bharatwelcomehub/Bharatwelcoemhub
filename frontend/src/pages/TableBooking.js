import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { Calendar, MessageCircle, Users, Clock, MapPin, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

const CENTERS = [
  { value: 'PB-HSR', label: 'PB-HSR', whatsapp: '919741399190', country: 'India' },
  { value: 'PB-Thane', label: 'PB-Thane', whatsapp: '919741399190', country: 'India' },
  { value: 'PB-SambhajiNagar', label: 'PB-SambhajiNagar', whatsapp: '919741399190', country: 'India' },
  { value: 'PB-Dombivli', label: 'PB-Dombivli', whatsapp: '919741399190', country: 'India' },
  { value: 'PB-Hinjawadi', label: 'PB-Hinjawadi', whatsapp: '919741399190', country: 'India' },
  { value: 'PB-Kalyan', label: 'PB-Kalyan', whatsapp: '919741399190', country: 'India' },
  { value: 'PB-KharadiNyati', label: 'PB-Kharadi Nyati', whatsapp: '919741399190', country: 'India' },
  { value: 'PB-Perth', label: 'PB-Perth', whatsapp: '61412345678', country: 'Australia' }
];

const TIME_SLOTS = [
  { value: '12:00-13:00', label: '12:00 PM – 1:00 PM' },
  { value: '13:00-14:00', label: '1:00 PM – 2:00 PM' },
  { value: '14:00-15:00', label: '2:00 PM – 3:00 PM' },
  { value: '19:00-20:00', label: '7:00 PM – 8:00 PM' },
  { value: '20:00-21:00', label: '8:00 PM – 9:00 PM' },
  { value: '21:00-22:00', label: '9:00 PM – 10:00 PM' }
];

const CELEBRATIONS = [
  { value: '', label: 'None' },
  { value: 'birthday', label: 'Birthday 🎂' },
  { value: 'anniversary', label: 'Anniversary 💑' },
  { value: 'family', label: 'Family Gathering 👨‍👩‍👧‍👦' },
  { value: 'friends', label: 'Friends Get-together 🎉' },
  { value: 'kitty', label: 'Kitty Party 👯‍♀️' },
  { value: 'women', label: "Women's Meet 👩‍👩‍👧" },
  { value: 'gudhipadwa', label: 'Gudi Padwa 🪔' },
  { value: 'fasting', label: 'Fasting / Upvas 🙏' }
];

const GUEST_TYPES = [
  { value: '', label: 'Select' },
  { value: 'repeat', label: 'Repeat Guest' },
  { value: 'new', label: 'New Entry' },
  { value: 'party', label: 'Party Guest' },
  { value: 'group', label: 'Group Guest' }
];

const SERVICE_TYPES = [
  { value: '', label: 'Select' },
  { value: 'dine-in', label: 'Dine In 🍽️' },
  { value: 'pickup', label: 'Pickup 🥡' }
];

const TableBooking = () => {
  const [formData, setFormData] = useState({
    center: '',
    date: '',
    time: '',
    name: '',
    phone: '',
    email: '',
    guests: 2,
    celebration: '',
    guestType: '',
    serviceType: '',
    specialRequest: ''
  });

  const selectedCenter = useMemo(() => 
    CENTERS.find(c => c.value === formData.center), 
    [formData.center]
  );

  const minDate = useMemo(() => {
    const today = new Date();
    return today.toISOString().split('T')[0];
  }, []);

  const validateForm = () => {
    if (!formData.center) {
      toast.error('Please select a center');
      return false;
    }
    if (!formData.date) {
      toast.error('Please select a date');
      return false;
    }
    if (!formData.time) {
      toast.error('Please select a time slot');
      return false;
    }
    if (!formData.name.trim()) {
      toast.error('Please enter your name');
      return false;
    }
    if (!formData.phone.trim() || formData.phone.length < 10) {
      toast.error('Please enter a valid phone number');
      return false;
    }
    if (!formData.serviceType) {
      toast.error('Please select Dine-In or Pickup');
      return false;
    }
    return true;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    const center = selectedCenter;
    const celebrationLabel = CELEBRATIONS.find(c => c.value === formData.celebration)?.label || 'None';
    const serviceLabel = SERVICE_TYPES.find(s => s.value === formData.serviceType)?.label || '';
    const timeLabel = TIME_SLOTS.find(t => t.value === formData.time)?.label || formData.time;

    let message = `🪔 *PURNABRAMHA BOOKING REQUEST*\n\n`;
    message += `📍 *Center:* ${center.label}\n`;
    message += `📅 *Date:* ${formData.date}\n`;
    message += `🕐 *Time:* ${timeLabel}\n`;
    message += `👤 *Name:* ${formData.name}\n`;
    message += `📱 *Phone:* ${formData.phone}\n`;
    if (formData.email) message += `📧 *Email:* ${formData.email}\n`;
    message += `👥 *Guests:* ${formData.guests}\n`;
    message += `🍽️ *Service:* ${serviceLabel}\n`;
    if (formData.celebration) message += `🎉 *Celebration:* ${celebrationLabel}\n`;
    if (formData.guestType) message += `👤 *Guest Type:* ${formData.guestType}\n`;
    if (formData.specialRequest) message += `\n📝 *Special Request:*\n${formData.specialRequest}\n`;
    message += `\n_Sent via Purnabramha App_`;

    const encodedMessage = encodeURIComponent(message);
    const whatsappUrl = `https://wa.me/${center.whatsapp}?text=${encodedMessage}`;
    
    window.open(whatsappUrl, '_blank');
    toast.success('Opening WhatsApp to confirm your booking');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[hsl(30,20%,97%)] to-white">
      {/* Festival Banner */}
      <div className="bg-[hsl(20,60%,15%)] text-[hsl(40,50%,85%)] py-3 px-4">
        <div className="container mx-auto text-center">
          <p className="text-sm font-medium">
            <span className="mr-2">🪔</span>
            Select your <strong>Center</strong> • Choose <strong>Date & Time</strong> • Dine-In or Pickup
            <span className="ml-2 px-2 py-0.5 bg-[hsl(38,70%,45%)] text-white text-xs rounded-full">Pure Veg</span>
          </p>
        </div>
      </div>

      <div className="container mx-auto px-4 lg:px-8 py-8 lg:py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-2xl mx-auto"
        >
          <div className="text-center mb-8">
            <Calendar className="h-12 w-12 mx-auto text-primary mb-4" />
            <h1 className="font-playfair text-3xl lg:text-5xl font-bold text-foreground mb-3" data-testid="table-booking-title">
              Purnabramha Booking
            </h1>
            <p className="text-foreground/70 font-manrope">
              Reserve your table for a delightful dining experience
            </p>
          </div>

          {/* Notice */}
          <Card className="mb-6 border-[hsl(38,70%,45%)]/30 bg-[hsl(45,80%,95%)]">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <Clock className="h-5 w-5 text-[hsl(38,70%,40%)] mt-0.5 flex-shrink-0" />
                <p className="text-sm text-[hsl(20,60%,25%)]">
                  <strong>Booking requests</strong> are accepted minimum <strong>2 hours before</strong> your visit.
                  This helps our team prepare better and serve you peacefully.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="border-[hsl(30,30%,88%)]">
            <CardContent className="p-6 lg:p-8">
              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Center Selection */}
                <div>
                  <Label htmlFor="center" className="flex items-center gap-2 mb-2">
                    <MapPin className="h-4 w-4" /> Select Center
                  </Label>
                  <Select
                    value={formData.center}
                    onValueChange={(value) => setFormData({ ...formData, center: value })}
                  >
                    <SelectTrigger id="center" data-testid="center-select">
                      <SelectValue placeholder="Select Center" />
                    </SelectTrigger>
                    <SelectContent>
                      {CENTERS.map(center => (
                        <SelectItem key={center.value} value={center.value}>
                          {center.label} ({center.country})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Date & Time */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="date">Date</Label>
                    <Input
                      id="date"
                      type="date"
                      min={minDate}
                      value={formData.date}
                      onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                      data-testid="booking-date-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="time">Time Slot</Label>
                    <Select
                      value={formData.time}
                      onValueChange={(value) => setFormData({ ...formData, time: value })}
                    >
                      <SelectTrigger id="time" data-testid="time-select">
                        <SelectValue placeholder="Select Time" />
                      </SelectTrigger>
                      <SelectContent>
                        {TIME_SLOTS.map(slot => (
                          <SelectItem key={slot.value} value={slot.value}>
                            {slot.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Name & Phone */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="name">Name</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="Your name"
                      data-testid="name-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="phone">Phone</Label>
                    <Input
                      id="phone"
                      type="tel"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      placeholder="+91 / +61"
                      data-testid="phone-input"
                    />
                  </div>
                </div>

                {/* Email */}
                <div>
                  <Label htmlFor="email">Email (optional)</Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="your@email.com"
                  />
                </div>

                {/* Guests */}
                <div>
                  <Label htmlFor="guests" className="flex items-center gap-2">
                    <Users className="h-4 w-4" /> Number of Guests
                  </Label>
                  <Input
                    id="guests"
                    type="number"
                    min="1"
                    max="200"
                    value={formData.guests}
                    onChange={(e) => setFormData({ ...formData, guests: parseInt(e.target.value) || 2 })}
                    data-testid="guests-input"
                  />
                </div>

                {/* Service Type */}
                <div>
                  <Label htmlFor="serviceType">Select Dine-In / Pickup</Label>
                  <Select
                    value={formData.serviceType}
                    onValueChange={(value) => setFormData({ ...formData, serviceType: value })}
                  >
                    <SelectTrigger id="serviceType" data-testid="service-type-select">
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      {SERVICE_TYPES.filter(s => s.value).map(service => (
                        <SelectItem key={service.value} value={service.value}>
                          {service.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Celebration */}
                <div>
                  <Label htmlFor="celebration">Are you celebrating anything?</Label>
                  <Select
                    value={formData.celebration}
                    onValueChange={(value) => setFormData({ ...formData, celebration: value })}
                  >
                    <SelectTrigger id="celebration">
                      <SelectValue placeholder="None" />
                    </SelectTrigger>
                    <SelectContent>
                      {CELEBRATIONS.map(cel => (
                        <SelectItem key={cel.value || 'none'} value={cel.value || 'none'}>
                          {cel.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Guest Type */}
                <div>
                  <Label htmlFor="guestType">Guest Type</Label>
                  <Select
                    value={formData.guestType}
                    onValueChange={(value) => setFormData({ ...formData, guestType: value })}
                  >
                    <SelectTrigger id="guestType">
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      {GUEST_TYPES.filter(g => g.value).map(guest => (
                        <SelectItem key={guest.value} value={guest.value}>
                          {guest.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Special Request */}
                <div>
                  <Label htmlFor="specialRequest">Special Requests / Notes</Label>
                  <Textarea
                    id="specialRequest"
                    value={formData.specialRequest}
                    onChange={(e) => setFormData({ ...formData, specialRequest: e.target.value })}
                    placeholder="Write any special requests..."
                    rows={3}
                    data-testid="special-request-input"
                  />
                </div>

                {/* Important Notice */}
                <Card className="border-[hsl(45,80%,50%)]/50 bg-[hsl(45,80%,95%)]">
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="h-5 w-5 text-[hsl(30,80%,40%)] mt-0.5 flex-shrink-0" />
                      <div className="text-sm text-[hsl(30,50%,25%)]">
                        <p className="font-semibold mb-1">⚠️ Important Booking Note:</p>
                        <p>Sending a WhatsApp message does <strong>not</strong> confirm your booking.</p>
                        <p>Booking is confirmed <strong>only after Center Manager replies on WhatsApp</strong>.</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Submit Button */}
                <Button
                  type="submit"
                  className="w-full rounded-full bg-[hsl(145,60%,40%)] hover:bg-[hsl(145,60%,35%)] text-white text-lg py-6"
                  data-testid="send-whatsapp-btn"
                >
                  <MessageCircle className="mr-2 h-5 w-5" />
                  Send to WhatsApp
                </Button>

                <p className="text-center text-sm text-foreground/60">
                  Booking will be confirmed by WhatsApp from the centre.
                </p>
              </form>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
};

export default TableBooking;
