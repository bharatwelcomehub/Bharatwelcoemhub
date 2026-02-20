import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { UtensilsCrossed } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Catering = () => {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    event_date: '',
    event_type: '',
    guest_count: '',
    venue_address: '',
    requirements: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!user) {
      toast.error('Please login to submit a catering request');
      return;
    }

    setLoading(true);
    try {
      await axios.post(
        `${API}/catering/request`,
        {
          ...formData,
          guest_count: parseInt(formData.guest_count)
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      toast.success('Catering request submitted successfully! We will contact you soon.');
      navigate('/profile');
    } catch (error) {
      console.error('Failed to submit catering request:', error);
      toast.error(error.response?.data?.detail || 'Failed to submit request');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-cream to-white">
      <div className="container mx-auto px-4 lg:px-8 py-12 lg:py-20">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <UtensilsCrossed className="h-16 w-16 text-primary mb-6" />
            <h1 className="font-playfair text-4xl lg:text-6xl font-bold text-foreground mb-6 tracking-tight" data-testid="catering-title">
              Catering Services
            </h1>
            <p className="text-lg text-foreground/70 font-manrope mb-8 leading-relaxed">
              Make your special occasions memorable with Purnabramha's authentic Maharashtrian catering. From intimate gatherings to large celebrations, we bring the taste of tradition to your events.
            </p>
            
            <div className="space-y-6">
              <div>
                <h3 className="font-playfair text-xl font-semibold mb-2">Perfect For:</h3>
                <ul className="space-y-2 text-foreground/70 font-manrope">
                  <li>• Weddings & Receptions</li>
                  <li>• Corporate Events</li>
                  <li>• Birthday Parties</li>
                  <li>• Family Gatherings</li>
                  <li>• Festivals & Celebrations</li>
                </ul>
              </div>

              <div>
                <h3 className="font-playfair text-xl font-semibold mb-2">We Provide:</h3>
                <ul className="space-y-2 text-foreground/70 font-manrope">
                  <li>• Customizable Menus</li>
                  <li>• Professional Service Staff</li>
                  <li>• Serving Equipment</li>
                  <li>• On-time Delivery</li>
                  <li>• Quality Assurance</li>
                </ul>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <div className="bg-white rounded-xl p-8 border border-orange-900/10">
              <h2 className="font-playfair text-2xl font-semibold mb-6">Request a Quote</h2>
              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <Label htmlFor="event-type">Event Type</Label>
                  <Input
                    id="event-type"
                    value={formData.event_type}
                    onChange={(e) => setFormData({ ...formData, event_type: e.target.value })}
                    placeholder="e.g., Wedding, Corporate Event, Birthday"
                    required
                    data-testid="event-type-input"
                  />
                </div>

                <div>
                  <Label htmlFor="event-date">Event Date</Label>
                  <Input
                    id="event-date"
                    type="date"
                    value={formData.event_date}
                    onChange={(e) => setFormData({ ...formData, event_date: e.target.value })}
                    required
                    data-testid="event-date-input"
                  />
                </div>

                <div>
                  <Label htmlFor="guest-count">Expected Guest Count</Label>
                  <Input
                    id="guest-count"
                    type="number"
                    min="10"
                    value={formData.guest_count}
                    onChange={(e) => setFormData({ ...formData, guest_count: e.target.value })}
                    placeholder="Number of guests"
                    required
                    data-testid="guest-count-input"
                  />
                </div>

                <div>
                  <Label htmlFor="venue-address">Venue Address</Label>
                  <Textarea
                    id="venue-address"
                    value={formData.venue_address}
                    onChange={(e) => setFormData({ ...formData, venue_address: e.target.value })}
                    placeholder="Enter the complete venue address"
                    rows={3}
                    required
                    data-testid="venue-address-input"
                  />
                </div>

                <div>
                  <Label htmlFor="requirements">Additional Requirements</Label>
                  <Textarea
                    id="requirements"
                    value={formData.requirements}
                    onChange={(e) => setFormData({ ...formData, requirements: e.target.value })}
                    placeholder="Menu preferences, dietary restrictions, service requirements, etc."
                    rows={4}
                    required
                    data-testid="requirements-input"
                  />
                </div>

                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-full bg-primary text-lg py-6"
                  data-testid="submit-catering-button"
                >
                  {loading ? 'Submitting...' : 'Submit Request'}
                </Button>

                <p className="text-xs text-foreground/60 text-center font-manrope">
                  Our team will contact you within 24 hours to discuss your requirements
                </p>
              </form>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Catering;