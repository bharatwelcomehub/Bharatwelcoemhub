import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Calendar } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TableBooking = () => {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    location_id: '',
    booking_date: '',
    booking_time: '',
    party_size: 2,
    special_requests: ''
  });

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
      toast.error('Please login to book a table');
      return;
    }

    setLoading(true);
    try {
      await axios.post(
        `${API}/bookings/table`,
        formData,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      toast.success('Table booking request submitted successfully!');
      navigate('/profile');
    } catch (error) {
      console.error('Failed to book table:', error);
      toast.error(error.response?.data?.detail || 'Failed to book table');
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
          className="max-w-2xl mx-auto"
        >
          <div className="text-center mb-12">
            <Calendar className="h-16 w-16 mx-auto text-primary mb-4" />
            <h1 className="font-playfair text-4xl lg:text-6xl font-bold text-foreground mb-4 tracking-tight" data-testid="table-booking-title">
              Table Booking
            </h1>
            <p className="text-lg text-foreground/70 font-manrope">
              Reserve your table for a delightful dining experience
            </p>
          </div>

          <div className="bg-white rounded-xl p-8 border border-orange-900/10">
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <Label htmlFor="location">Location</Label>
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
                <Label htmlFor="booking-date">Booking Date</Label>
                <Input
                  id="booking-date"
                  type="date"
                  value={formData.booking_date}
                  onChange={(e) => setFormData({ ...formData, booking_date: e.target.value })}
                  required
                  data-testid="booking-date-input"
                />
              </div>

              <div>
                <Label htmlFor="booking-time">Booking Time</Label>
                <Input
                  id="booking-time"
                  type="time"
                  value={formData.booking_time}
                  onChange={(e) => setFormData({ ...formData, booking_time: e.target.value })}
                  required
                  data-testid="booking-time-input"
                />
              </div>

              <div>
                <Label htmlFor="party-size">Party Size</Label>
                <Input
                  id="party-size"
                  type="number"
                  min="1"
                  max="20"
                  value={formData.party_size}
                  onChange={(e) => setFormData({ ...formData, party_size: parseInt(e.target.value) })}
                  required
                  data-testid="party-size-input"
                />
              </div>

              <div>
                <Label htmlFor="special-requests">Special Requests (Optional)</Label>
                <Textarea
                  id="special-requests"
                  value={formData.special_requests}
                  onChange={(e) => setFormData({ ...formData, special_requests: e.target.value })}
                  placeholder="Any dietary restrictions, seating preferences, or special occasions?"
                  rows={4}
                  data-testid="special-requests-input"
                />
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="w-full rounded-full bg-primary text-lg py-6"
                data-testid="submit-booking-button"
              >
                {loading ? 'Booking...' : 'Book Table'}
              </Button>
            </form>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default TableBooking;