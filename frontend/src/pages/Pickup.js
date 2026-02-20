import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Minus, Plus, Trash2, ShoppingBag } from 'lucide-react';
import { useCart } from '@/contexts/CartContext';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Pickup = () => {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const { cartItems, selectedLocation, setSelectedLocation, updateQuantity, removeFromCart, getTotalAmount, clearCart } = useCart();
  const [locations, setLocations] = useState([]);
  const [pickupTime, setPickupTime] = useState('');
  const [loading, setLoading] = useState(false);

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

  const handlePlaceOrder = async () => {
    if (!user) {
      toast.error('Please login to place an order');
      return;
    }

    if (!selectedLocation) {
      toast.error('Please select a pickup location');
      return;
    }

    if (!pickupTime) {
      toast.error('Please select a pickup time');
      return;
    }

    if (cartItems.length === 0) {
      toast.error('Your cart is empty');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(
        `${API}/orders/pickup`,
        {
          location_id: selectedLocation.id,
          items: cartItems,
          pickup_time: pickupTime,
          payment_method: 'cash'
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      toast.success('Order placed successfully!');
      clearCart();
      navigate('/profile');
    } catch (error) {
      console.error('Failed to place order:', error);
      toast.error(error.response?.data?.detail || 'Failed to place order');
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
          className="mb-12"
        >
          <h1 className="font-playfair text-4xl lg:text-6xl font-bold text-foreground mb-4 tracking-tight" data-testid="pickup-title">
            Pickup Order
          </h1>
          <p className="text-lg text-foreground/70 font-manrope">
            Order your favorite dishes and pick them up at your convenience
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white rounded-xl p-6 border border-orange-900/10">
              <h2 className="font-playfair text-2xl font-semibold mb-4">Your Cart</h2>
              
              {cartItems.length === 0 ? (
                <div className="text-center py-12" data-testid="empty-cart">
                  <ShoppingBag className="h-16 w-16 mx-auto text-foreground/20 mb-4" />
                  <p className="text-foreground/70 font-manrope mb-4">Your cart is empty</p>
                  <Button onClick={() => navigate('/menu')} className="rounded-full" data-testid="browse-menu-button">
                    Browse Menu
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  {cartItems.map((item, index) => (
                    <div key={item.menu_item_id} className="flex items-center justify-between border-b border-gray-100 pb-4" data-testid={`cart-item-${index}`}>
                      <div className="flex-1">
                        <h3 className="font-manrope font-semibold text-foreground">{item.name}</h3>
                        <p className="text-foreground/70 font-manrope">₹{item.price}</p>
                      </div>
                      <div className="flex items-center space-x-3">
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-8 w-8 rounded-full"
                          onClick={() => updateQuantity(item.menu_item_id, item.quantity - 1)}
                          data-testid={`decrease-quantity-${index}`}
                        >
                          <Minus className="h-4 w-4" />
                        </Button>
                        <span className="font-manrope font-semibold w-8 text-center" data-testid={`quantity-${index}`}>{item.quantity}</span>
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-8 w-8 rounded-full"
                          onClick={() => updateQuantity(item.menu_item_id, item.quantity + 1)}
                          data-testid={`increase-quantity-${index}`}
                        >
                          <Plus className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-destructive"
                          onClick={() => removeFromCart(item.menu_item_id)}
                          data-testid={`remove-item-${index}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-white rounded-xl p-6 border border-orange-900/10">
              <h2 className="font-playfair text-2xl font-semibold mb-4">Pickup Details</h2>
              
              <div className="space-y-4">
                <div>
                  <Label htmlFor="location">Pickup Location</Label>
                  <Select
                    value={selectedLocation?.id}
                    onValueChange={(value) => {
                      const location = locations.find(loc => loc.id === value);
                      setSelectedLocation(location);
                    }}
                  >
                    <SelectTrigger id="location" data-testid="location-select">
                      <SelectValue placeholder="Select a location" />
                    </SelectTrigger>
                    <SelectContent>
                      {locations.map(location => (
                        <SelectItem key={location.id} value={location.id} data-testid={`location-option-${location.name}`}>
                          {location.name}, {location.city}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="pickup-time">Pickup Time</Label>
                  <Input
                    id="pickup-time"
                    type="datetime-local"
                    value={pickupTime}
                    onChange={(e) => setPickupTime(e.target.value)}
                    data-testid="pickup-time-input"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl p-6 border border-orange-900/10 sticky top-24">
              <h2 className="font-playfair text-2xl font-semibold mb-6">Order Summary</h2>
              
              <div className="space-y-3 mb-6">
                <div className="flex justify-between font-manrope">
                  <span className="text-foreground/70">Subtotal</span>
                  <span className="font-semibold" data-testid="subtotal-amount">₹{getTotalAmount().toFixed(2)}</span>
                </div>
                <div className="flex justify-between font-manrope">
                  <span className="text-foreground/70">Taxes</span>
                  <span className="font-semibold">₹0.00</span>
                </div>
                <div className="border-t border-gray-200 pt-3">
                  <div className="flex justify-between font-manrope text-lg">
                    <span className="font-semibold">Total</span>
                    <span className="font-bold text-primary" data-testid="total-amount">₹{getTotalAmount().toFixed(2)}</span>
                  </div>
                </div>
              </div>

              <Button
                onClick={handlePlaceOrder}
                disabled={loading || cartItems.length === 0}
                className="w-full rounded-full bg-primary text-lg py-6"
                data-testid="place-order-button"
              >
                {loading ? 'Placing Order...' : 'Place Order'}
              </Button>

              <p className="text-xs text-foreground/60 text-center mt-4 font-manrope">
                Payment will be collected at pickup
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Pickup;