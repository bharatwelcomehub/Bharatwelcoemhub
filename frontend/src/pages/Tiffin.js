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
import { Coffee, Check } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Tiffin = () => {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    location_id: '',
    plan_type: '',
    delivery_address: '',
    start_date: ''
  });

  const plans = [
    {
      name: 'Daily Tiffin',
      description: 'Fresh home-cooked meal delivered daily',
      price: '150/day',
      features: ['1 time delivery', 'Lunch or Dinner', 'Rotating menu', 'Weekend included']
    },
    {
      name: 'Weekly Plan',
      description: 'Save with our weekly subscription',
      price: '₹900/week',
      features: ['6 days delivery', 'Flexible timing', 'Special requests', 'Quality assured']
    },
    {
      name: 'Monthly Plan',
      description: 'Best value for regular subscribers',
      price: '₹3,500/month',
      features: ['26 days delivery', 'Priority support', 'Custom menu', 'Free festival thali']
    }
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

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!user) {
      toast.error('Please login to subscribe to tiffin service');
      return;
    }

    setLoading(true);
    try {
      await axios.post(
        `${API}/tiffin/subscribe`,
        formData,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      toast.success('Tiffin subscription created successfully!');
      navigate('/profile');
    } catch (error) {
      console.error('Failed to subscribe:', error);
      toast.error(error.response?.data?.detail || 'Failed to subscribe');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-cream to-white">
      <div className="container mx-auto px-4 lg:px-8 py-12 lg:py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <Coffee className="h-16 w-16 mx-auto text-primary mb-4" />
          <h1 className="font-playfair text-4xl lg:text-6xl font-bold text-foreground mb-4 tracking-tight" data-testid="tiffin-title">
            Tiffin Service
          </h1>
          <p className="text-lg text-foreground/70 font-manrope max-w-2xl mx-auto">
            Enjoy wholesome home-cooked Maharashtrian meals delivered daily
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {plans.map((plan, index) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              data-testid={`plan-card-${index}`}
            >
              <Card className="h-full hover:shadow-lg transition-shadow border-orange-900/10">
                <CardContent className="p-6">
                  <h3 className="font-playfair text-2xl font-semibold mb-2">{plan.name}</h3>
                  <p className="text-foreground/70 font-manrope mb-4">{plan.description}</p>
                  <p className="text-3xl font-bold text-primary mb-6">{plan.price}</p>
                  <ul className="space-y-3">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-center font-manrope text-sm">
                        <Check className="h-4 w-4 text-green-600 mr-2 flex-shrink-0" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="max-w-2xl mx-auto"
        >
          <div className="bg-white rounded-xl p-8 border border-orange-900/10">
            <h2 className="font-playfair text-2xl font-semibold mb-6">Subscribe Now</h2>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <Label htmlFor="plan-type">Select Plan</Label>
                <Select
                  value={formData.plan_type}
                  onValueChange={(value) => setFormData({ ...formData, plan_type: value })}
                  required
                >
                  <SelectTrigger id="plan-type" data-testid="plan-type-select">
                    <SelectValue placeholder="Choose a plan" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daily">Daily Tiffin</SelectItem>
                    <SelectItem value="weekly">Weekly Plan</SelectItem>
                    <SelectItem value="monthly">Monthly Plan</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="location">Nearest Location</Label>
                <Select
                  value={formData.location_id}
                  onValueChange={(value) => setFormData({ ...formData, location_id: value })}
                  required
                >
                  <SelectTrigger id="location" data-testid="location-select">
                    <SelectValue placeholder="Select a location" />
                  </SelectTrigger>
                  <SelectContent>
                    {locations.map(location => (
                      <SelectItem key={location.id} value={location.id}>
                        {location.name}, {location.city}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="delivery-address">Delivery Address</Label>
                <Textarea
                  id="delivery-address"
                  value={formData.delivery_address}
                  onChange={(e) => setFormData({ ...formData, delivery_address: e.target.value })}
                  placeholder="Enter your complete delivery address"
                  rows={4}
                  required
                  data-testid="delivery-address-input"
                />
              </div>

              <div>
                <Label htmlFor="start-date">Start Date</Label>
                <Input
                  id="start-date"
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  required
                  data-testid="start-date-input"
                />
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="w-full rounded-full bg-primary text-lg py-6"
                data-testid="subscribe-button"
              >
                {loading ? 'Subscribing...' : 'Subscribe Now'}
              </Button>
            </form>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Tiffin;