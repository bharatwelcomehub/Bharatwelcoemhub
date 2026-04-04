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
      case 'pending': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'confirmed': return 'bg-green-100 text-green-800 border-green-200';
      case 'completed': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'active': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FDFBF7] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-[#B8962E] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-[#5C4A3A] font-body">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FDFBF7]">
      <div className="container mx-auto px-4 lg:px-8 py-12 lg:py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <div className="flex items-center mb-4">
            <div className="h-16 w-16 rounded-full bg-gradient-to-br from-[#B8962E]/20 to-[#D4AF37]/10 flex items-center justify-center mr-4 border border-[#B8962E]/20">
              <User className="h-8 w-8 text-[#B8962E]" />
            </div>
            <div>
              <h1 className="font-heading text-3xl lg:text-5xl font-medium text-[#2D1810]" data-testid="profile-name">
                {user?.name}
              </h1>
              <p className="text-[#5C4A3A] font-body">{user?.email}</p>
            </div>
          </div>
        </motion.div>

        <Tabs defaultValue="orders" className="w-full">
          <TabsList className="grid w-full grid-cols-2 lg:grid-cols-4 mb-8 bg-white border border-[#E8DFD0] p-1 rounded-none" data-testid="profile-tabs">
            <TabsTrigger value="orders" className="data-[state=active]:bg-[#B8962E] data-[state=active]:text-white rounded-none font-body" data-testid="orders-tab">
              <ShoppingBag className="h-4 w-4 mr-2" />
              Pickup Orders
            </TabsTrigger>
            <TabsTrigger value="bookings" className="data-[state=active]:bg-[#B8962E] data-[state=active]:text-white rounded-none font-body" data-testid="bookings-tab">
              <Calendar className="h-4 w-4 mr-2" />
              Table Bookings
            </TabsTrigger>
            <TabsTrigger value="tiffin" className="data-[state=active]:bg-[#B8962E] data-[state=active]:text-white rounded-none font-body" data-testid="tiffin-tab">
              <Coffee className="h-4 w-4 mr-2" />
              Tiffin
            </TabsTrigger>
            <TabsTrigger value="catering" className="data-[state=active]:bg-[#B8962E] data-[state=active]:text-white rounded-none font-body" data-testid="catering-tab">
              <UtensilsCrossed className="h-4 w-4 mr-2" />
              Catering
            </TabsTrigger>
          </TabsList>

          <TabsContent value="orders">
            <div className="space-y-4">
              {pickupOrders.length === 0 ? (
                <Card className="pearl-surface border-[#E8DFD0] rounded-none">
                  <CardContent className="py-12 text-center">
                    <ShoppingBag className="h-12 w-12 mx-auto text-[#B8962E]/30 mb-4" />
                    <p className="text-[#5C4A3A] font-body" data-testid="no-orders">No pickup orders yet</p>
                    <p className="text-[#7A6F65] font-body text-sm mt-1">Your pickup orders will appear here</p>
                  </CardContent>
                </Card>
              ) : (
                pickupOrders.map((order, index) => (
                  <Card key={order.id} className="pearl-surface border-[#E8DFD0] rounded-none" data-testid={`order-${index}`}>
                    <CardHeader className="border-b border-[#E8DFD0]">
                      <div className="flex items-center justify-between">
                        <CardTitle className="font-heading text-xl text-[#2D1810]">Order #{order.id.slice(0, 8)}</CardTitle>
                        <Badge className={`${getStatusColor(order.status)} rounded-none`}>{order.status}</Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-4">
                      <div className="space-y-2">
                        <p className="font-body text-sm text-[#5C4A3A]">
                          Pickup Time: <span className="text-[#2D1810] font-medium">{order.pickup_time}</span>
                        </p>
                        <p className="font-body text-sm text-[#5C4A3A]">
                          Items: <span className="text-[#2D1810] font-medium">{order.items.length}</span>
                        </p>
                        <p className="font-heading text-lg font-medium text-[#B8962E]">
                          Total: {order.total_amount}
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
                <Card className="pearl-surface border-[#E8DFD0] rounded-none">
                  <CardContent className="py-12 text-center">
                    <Calendar className="h-12 w-12 mx-auto text-[#B8962E]/30 mb-4" />
                    <p className="text-[#5C4A3A] font-body" data-testid="no-bookings">No table bookings yet</p>
                    <p className="text-[#7A6F65] font-body text-sm mt-1">Your table reservations will appear here</p>
                  </CardContent>
                </Card>
              ) : (
                tableBookings.map((booking, index) => (
                  <Card key={booking.id} className="pearl-surface border-[#E8DFD0] rounded-none" data-testid={`booking-${index}`}>
                    <CardHeader className="border-b border-[#E8DFD0]">
                      <div className="flex items-center justify-between">
                        <CardTitle className="font-heading text-xl text-[#2D1810]">Booking #{booking.id.slice(0, 8)}</CardTitle>
                        <Badge className={`${getStatusColor(booking.status)} rounded-none`}>{booking.status}</Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-4">
                      <div className="space-y-2">
                        <p className="font-body text-sm text-[#5C4A3A]">
                          Date: <span className="text-[#2D1810] font-medium">{booking.booking_date} at {booking.booking_time}</span>
                        </p>
                        <p className="font-body text-sm text-[#5C4A3A]">
                          Party Size: <span className="text-[#2D1810] font-medium">{booking.party_size} guests</span>
                        </p>
                        {booking.special_requests && (
                          <p className="font-body text-sm text-[#5C4A3A]">
                            Special Requests: <span className="text-[#2D1810]">{booking.special_requests}</span>
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
                <Card className="pearl-surface border-[#E8DFD0] rounded-none">
                  <CardContent className="py-12 text-center">
                    <Coffee className="h-12 w-12 mx-auto text-[#B8962E]/30 mb-4" />
                    <p className="text-[#5C4A3A] font-body" data-testid="no-tiffin">No tiffin subscriptions yet</p>
                    <p className="text-[#7A6F65] font-body text-sm mt-1">Your tiffin subscriptions will appear here</p>
                  </CardContent>
                </Card>
              ) : (
                tiffinSubscriptions.map((sub, index) => (
                  <Card key={sub.id} className="pearl-surface border-[#E8DFD0] rounded-none" data-testid={`tiffin-${index}`}>
                    <CardHeader className="border-b border-[#E8DFD0]">
                      <div className="flex items-center justify-between">
                        <CardTitle className="font-heading text-xl text-[#2D1810]">{sub.plan_type} Plan</CardTitle>
                        <Badge className={`${getStatusColor(sub.status)} rounded-none`}>{sub.status}</Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-4">
                      <div className="space-y-2">
                        <p className="font-body text-sm text-[#5C4A3A]">
                          Start Date: <span className="text-[#2D1810] font-medium">{sub.start_date}</span>
                        </p>
                        <p className="font-body text-sm text-[#5C4A3A]">
                          Delivery Address: <span className="text-[#2D1810]">{sub.delivery_address}</span>
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
                <Card className="pearl-surface border-[#E8DFD0] rounded-none">
                  <CardContent className="py-12 text-center">
                    <UtensilsCrossed className="h-12 w-12 mx-auto text-[#B8962E]/30 mb-4" />
                    <p className="text-[#5C4A3A] font-body" data-testid="no-catering">No catering requests yet</p>
                    <p className="text-[#7A6F65] font-body text-sm mt-1">Your catering requests will appear here</p>
                  </CardContent>
                </Card>
              ) : (
                cateringRequests.map((request, index) => (
                  <Card key={request.id} className="pearl-surface border-[#E8DFD0] rounded-none" data-testid={`catering-${index}`}>
                    <CardHeader className="border-b border-[#E8DFD0]">
                      <div className="flex items-center justify-between">
                        <CardTitle className="font-heading text-xl text-[#2D1810]">{request.event_type}</CardTitle>
                        <Badge className={`${getStatusColor(request.status)} rounded-none`}>{request.status}</Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-4">
                      <div className="space-y-2">
                        <p className="font-body text-sm text-[#5C4A3A]">
                          Event Date: <span className="text-[#2D1810] font-medium">{request.event_date}</span>
                        </p>
                        <p className="font-body text-sm text-[#5C4A3A]">
                          Guest Count: <span className="text-[#2D1810] font-medium">{request.guest_count}</span>
                        </p>
                        <p className="font-body text-sm text-[#5C4A3A]">
                          Venue: <span className="text-[#2D1810]">{request.venue_address}</span>
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
