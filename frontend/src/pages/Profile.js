import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { User, ShoppingBag, Calendar, Coffee, UtensilsCrossed } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Profile = () => {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [pickupOrders, setPickupOrders] = useState([]);
  const [tableBookings, setTableBookings] = useState([]);
  const [tiffinSubscriptions, setTiffinSubscriptions] = useState([]);
  const [cateringRequests, setCateringRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      navigate('/');
      return;
    }
    fetchData();
  }, [user, token]);

  const fetchData = async () => {
    try {
      const [ordersRes, bookingsRes, tiffinRes, cateringRes] = await Promise.all([
        axios.get(`${API}/orders/pickup`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/bookings/table`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/tiffin/subscriptions`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/catering/requests`, { headers: { Authorization: `Bearer ${token}` } })
      ]);

      setPickupOrders(ordersRes.data);
      setTableBookings(bookingsRes.data);
      setTiffinSubscriptions(tiffinRes.data);
      setCateringRequests(cateringRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load profile data');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'confirmed': return 'bg-green-100 text-green-800';
      case 'completed': return 'bg-blue-100 text-blue-800';
      case 'active': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 lg:px-8 py-20">
        <div className="text-center">Loading profile...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-cream to-white">
      <div className="container mx-auto px-4 lg:px-8 py-12 lg:py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <div className="flex items-center mb-4">
            <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mr-4">
              <User className="h-8 w-8 text-primary" />
            </div>
            <div>
              <h1 className="font-playfair text-3xl lg:text-5xl font-bold text-foreground" data-testid="profile-name">
                {user?.name}
              </h1>
              <p className="text-foreground/70 font-manrope">{user?.email}</p>
            </div>
          </div>
        </motion.div>

        <Tabs defaultValue="orders" className="w-full">
          <TabsList className="grid w-full grid-cols-2 lg:grid-cols-4 mb-8" data-testid="profile-tabs">
            <TabsTrigger value="orders" data-testid="orders-tab">
              <ShoppingBag className="h-4 w-4 mr-2" />
              Pickup Orders
            </TabsTrigger>
            <TabsTrigger value="bookings" data-testid="bookings-tab">
              <Calendar className="h-4 w-4 mr-2" />
              Table Bookings
            </TabsTrigger>
            <TabsTrigger value="tiffin" data-testid="tiffin-tab">
              <Coffee className="h-4 w-4 mr-2" />
              Tiffin
            </TabsTrigger>
            <TabsTrigger value="catering" data-testid="catering-tab">
              <UtensilsCrossed className="h-4 w-4 mr-2" />
              Catering
            </TabsTrigger>
          </TabsList>

          <TabsContent value="orders">
            <div className="space-y-4">
              {pickupOrders.length === 0 ? (
                <Card>
                  <CardContent className="py-12 text-center">
                    <p className="text-foreground/70 font-manrope" data-testid="no-orders">No pickup orders yet</p>
                  </CardContent>
                </Card>
              ) : (
                pickupOrders.map((order, index) => (
                  <Card key={order.id} data-testid={`order-${index}`}>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="font-playfair text-xl">Order #{order.id.slice(0, 8)}</CardTitle>
                        <Badge className={getStatusColor(order.status)}>{order.status}</Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <p className="font-manrope text-sm text-foreground/70">
                          Pickup Time: {order.pickup_time}
                        </p>
                        <p className="font-manrope text-sm text-foreground/70">
                          Items: {order.items.length}
                        </p>
                        <p className="font-manrope text-lg font-semibold text-primary">
                          Total: ₹{order.total_amount}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>

          <TabsContent value="bookings">
            <div className="space-y-4">
              {tableBookings.length === 0 ? (
                <Card>
                  <CardContent className="py-12 text-center">
                    <p className="text-foreground/70 font-manrope" data-testid="no-bookings">No table bookings yet</p>
                  </CardContent>
                </Card>
              ) : (
                tableBookings.map((booking, index) => (
                  <Card key={booking.id} data-testid={`booking-${index}`}>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="font-playfair text-xl">Booking #{booking.id.slice(0, 8)}</CardTitle>
                        <Badge className={getStatusColor(booking.status)}>{booking.status}</Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <p className="font-manrope text-sm text-foreground/70">
                          Date: {booking.booking_date} at {booking.booking_time}
                        </p>
                        <p className="font-manrope text-sm text-foreground/70">
                          Party Size: {booking.party_size} guests
                        </p>
                        {booking.special_requests && (
                          <p className="font-manrope text-sm text-foreground/70">
                            Special Requests: {booking.special_requests}
                          </p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>

          <TabsContent value="tiffin">
            <div className="space-y-4">
              {tiffinSubscriptions.length === 0 ? (
                <Card>
                  <CardContent className="py-12 text-center">
                    <p className="text-foreground/70 font-manrope" data-testid="no-tiffin">No tiffin subscriptions yet</p>
                  </CardContent>
                </Card>
              ) : (
                tiffinSubscriptions.map((sub, index) => (
                  <Card key={sub.id} data-testid={`tiffin-${index}`}>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="font-playfair text-xl">{sub.plan_type} Plan</CardTitle>
                        <Badge className={getStatusColor(sub.status)}>{sub.status}</Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <p className="font-manrope text-sm text-foreground/70">
                          Start Date: {sub.start_date}
                        </p>
                        <p className="font-manrope text-sm text-foreground/70">
                          Delivery Address: {sub.delivery_address}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>

          <TabsContent value="catering">
            <div className="space-y-4">
              {cateringRequests.length === 0 ? (
                <Card>
                  <CardContent className="py-12 text-center">
                    <p className="text-foreground/70 font-manrope" data-testid="no-catering">No catering requests yet</p>
                  </CardContent>
                </Card>
              ) : (
                cateringRequests.map((request, index) => (
                  <Card key={request.id} data-testid={`catering-${index}`}>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="font-playfair text-xl">{request.event_type}</CardTitle>
                        <Badge className={getStatusColor(request.status)}>{request.status}</Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <p className="font-manrope text-sm text-foreground/70">
                          Event Date: {request.event_date}
                        </p>
                        <p className="font-manrope text-sm text-foreground/70">
                          Guest Count: {request.guest_count}
                        </p>
                        <p className="font-manrope text-sm text-foreground/70">
                          Venue: {request.venue_address}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default Profile;