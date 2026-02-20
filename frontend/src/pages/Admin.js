import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, Edit, Trash2, Image as ImageIcon, LogIn, UtensilsCrossed, MapPin, Video, Lock } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Admin = () => {
  const { user, token, login, logout } = useAuth();
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [loginLoading, setLoginLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('menu');

  // Menu state
  const [menuItems, setMenuItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: '',
    price_inr: '',
    price_aud: '',
    image_url: '',
    is_veg: true,
    is_available: true
  });

  // Locations state
  const [locations, setLocations] = useState([]);
  const [locationDialogOpen, setLocationDialogOpen] = useState(false);
  const [editingLocation, setEditingLocation] = useState(null);
  const [locationForm, setLocationForm] = useState({
    name: '',
    city: '',
    country: 'India',
    address: '',
    phone: '',
    whatsapp: '',
    google_review_link: '',
    is_active: true
  });

  // Videos state
  const [videos, setVideos] = useState([]);
  const [videoDialogOpen, setVideoDialogOpen] = useState(false);
  const [videoForm, setVideoForm] = useState({
    title: '',
    video_url: '',
    thumbnail_url: '',
    description: '',
    category: 'reels'
  });

  // Get fresh token from localStorage
  const getToken = () => localStorage.getItem('token') || token;

  const categories = [
    'Balgopal (Kids)',
    'Tea & Coffee',
    'Drinks',
    'Soup & Saar',
    'Snacks',
    'Fasting',
    'Heavy Brunch',
    'Bhakar Combo',
    'Bhaji',
    'Dal',
    'Rice',
    'Roti',
    'Sweets',
    'Special Thalis',
    'Sides'
  ];

  useEffect(() => {
    const currentToken = getToken();
    if (currentToken) {
      fetchMenuItems();
      fetchLocations();
      fetchVideos();
    }
  }, [token]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginLoading(true);
    try {
      await login(loginForm.email, loginForm.password);
      toast.success('Logged in successfully');
      // Fetch data after login
      setTimeout(() => {
        fetchMenuItems();
        fetchLocations();
        fetchVideos();
      }, 100);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoginLoading(false);
    }
  };

  const fetchMenuItems = async () => {
    const currentToken = getToken();
    if (!currentToken) return;
    setLoading(true);
    try {
      const response = await axios.get(`${API}/admin/menu`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      setMenuItems(response.data);
    } catch (error) {
      console.error('Failed to fetch menu:', error);
      if (error.response?.status === 401) {
        logout();
        toast.error('Session expired. Please login again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchLocations = async () => {
    const currentToken = getToken();
    if (!currentToken) return;
    try {
      const response = await axios.get(`${API}/admin/locations`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      setLocations(response.data);
    } catch (error) {
      console.error('Failed to fetch locations:', error);
    }
  };

  const fetchVideos = async () => {
    try {
      const response = await axios.get(`${API}/videos`);
      setVideos(response.data);
    } catch (error) {
      console.error('Failed to fetch videos:', error);
    }
  };

  // Menu CRUD
  const handleSubmit = async (e) => {
    e.preventDefault();
    const currentToken = getToken();
    if (!currentToken) {
      toast.error('Please login again');
      return;
    }
    
    // Convert price fields to numbers
    const submitData = {
      ...formData,
      price_inr: formData.price_inr ? parseFloat(formData.price_inr) : null,
      price_aud: formData.price_aud ? parseFloat(formData.price_aud) : null
    };
    
    try {
      if (editingItem) {
        await axios.put(
          `${API}/admin/menu/${editingItem.id}`,
          submitData,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Menu item updated');
      } else {
        await axios.post(
          `${API}/admin/menu`,
          submitData,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Menu item added');
      }
      setDialogOpen(false);
      resetForm();
      fetchMenuItems();
    } catch (error) {
      console.error('Operation failed:', error);
      toast.error(error.response?.data?.detail || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this item?')) return;
    const currentToken = getToken();
    try {
      await axios.delete(`${API}/admin/menu/${id}`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      toast.success('Menu item deleted');
      fetchMenuItems();
    } catch (error) {
      toast.error('Failed to delete');
    }
  };
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        toast.success('Menu item added');
      }
      setDialogOpen(false);
      resetForm();
      fetchMenuItems();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this item?')) return;
    try {
      await axios.delete(`${API}/admin/menu/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Menu item deleted');
      fetchMenuItems();
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setFormData({
      name: item.name,
      description: item.description,
      category: item.category,
      price_inr: item.price_inr || '',
      price_aud: item.price_aud || '',
      image_url: item.image_url || '',
      is_veg: item.is_veg,
      is_available: item.is_available
    });
    setDialogOpen(true);
  };

  const resetForm = () => {
    setEditingItem(null);
    setFormData({
      name: '',
      description: '',
      category: '',
      price_inr: '',
      price_aud: '',
      image_url: '',
      is_veg: true,
      is_available: true
    });
  };

  // Location CRUD
  const handleLocationSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingLocation) {
        await axios.put(
          `${API}/admin/locations/${editingLocation.id}`,
          locationForm,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        toast.success('Location updated');
      } else {
        await axios.post(
          `${API}/admin/locations`,
          locationForm,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        toast.success('Location added');
      }
      setLocationDialogOpen(false);
      resetLocationForm();
      fetchLocations();
    } catch (error) {
      toast.error('Operation failed');
    }
  };

  const resetLocationForm = () => {
    setEditingLocation(null);
    setLocationForm({
      name: '',
      city: '',
      country: 'India',
      address: '',
      phone: '',
      whatsapp: '',
      google_review_link: '',
      is_active: true
    });
  };

  // Video CRUD
  const handleVideoSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(
        `${API}/admin/videos`,
        { ...videoForm, is_active: true },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Video added');
      setVideoDialogOpen(false);
      setVideoForm({ title: '', video_url: '', thumbnail_url: '', description: '', category: 'reels' });
      fetchVideos();
    } catch (error) {
      toast.error('Failed to add video');
    }
  };

  const handleDeleteVideo = async (id) => {
    if (!window.confirm('Delete this video?')) return;
    try {
      await axios.delete(`${API}/admin/videos/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Video deleted');
      fetchVideos();
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  // Login Screen
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-cream to-white flex items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          <Card className="border-orange-900/10">
            <CardHeader className="text-center">
              <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-4">
                <Lock className="h-8 w-8 text-primary" />
              </div>
              <CardTitle className="font-playfair text-2xl">Admin Login</CardTitle>
              <p className="text-sm text-foreground/60 font-manrope">
                Enter your credentials to access the admin panel
              </p>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={loginForm.email}
                    onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                    placeholder="admin@purnabramha.com"
                    required
                    data-testid="admin-email-input"
                  />
                </div>
                <div>
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={loginForm.password}
                    onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                    placeholder="Enter password"
                    required
                    data-testid="admin-password-input"
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full rounded-full bg-primary"
                  disabled={loginLoading}
                  data-testid="admin-login-btn"
                >
                  <LogIn className="mr-2 h-4 w-4" />
                  {loginLoading ? 'Logging in...' : 'Login'}
                </Button>
              </form>
              <div className="mt-4 p-3 bg-orange-50 rounded-lg">
                <p className="text-xs text-foreground/60 font-manrope">
                  <strong>Demo Credentials:</strong><br />
                  Email: admin@purnabramha.com<br />
                  Password: admin123
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-cream to-white">
      <div className="container mx-auto px-4 lg:px-8 py-8 lg:py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <h1 className="font-playfair text-3xl lg:text-4xl font-bold text-foreground mb-2">
            Admin Dashboard
          </h1>
          <p className="text-foreground/70 font-manrope">
            Manage your restaurant menu, locations, and content
          </p>
        </motion.div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6 bg-white border border-orange-900/10">
            <TabsTrigger value="menu" className="flex items-center gap-2">
              <UtensilsCrossed className="h-4 w-4" />
              Menu ({menuItems.length})
            </TabsTrigger>
            <TabsTrigger value="locations" className="flex items-center gap-2">
              <MapPin className="h-4 w-4" />
              Locations ({locations.length})
            </TabsTrigger>
            <TabsTrigger value="videos" className="flex items-center gap-2">
              <Video className="h-4 w-4" />
              Videos ({videos.length})
            </TabsTrigger>
          </TabsList>

          {/* MENU TAB */}
          <TabsContent value="menu">
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-playfair text-xl font-semibold">Menu Items</h2>
              <Button
                onClick={() => { resetForm(); setDialogOpen(true); }}
                className="rounded-full bg-primary"
                data-testid="add-menu-item-btn"
              >
                <Plus className="mr-2 h-4 w-4" />
                Add Item
              </Button>
            </div>

            <div className="bg-white rounded-xl border border-orange-900/10 overflow-hidden">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-16">Image</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>₹ INR</TableHead>
                      <TableHead>$ AUD</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="w-24">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loading ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-8">Loading...</TableCell>
                      </TableRow>
                    ) : menuItems.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-8">No menu items</TableCell>
                      </TableRow>
                    ) : (
                      menuItems.slice(0, 50).map((item) => (
                        <TableRow key={item.id}>
                          <TableCell>
                            {item.image_url ? (
                              <img src={item.image_url} alt={item.name} className="w-10 h-10 object-cover rounded" />
                            ) : (
                              <div className="w-10 h-10 bg-gray-100 rounded flex items-center justify-center">
                                <ImageIcon className="h-5 w-5 text-gray-400" />
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="font-medium max-w-[200px] truncate">{item.name}</TableCell>
                          <TableCell className="text-sm">{item.category}</TableCell>
                          <TableCell>{item.price_inr || '-'}</TableCell>
                          <TableCell>{item.price_aud || '-'}</TableCell>
                          <TableCell>
                            <Badge variant={item.is_available ? 'default' : 'secondary'} className="text-xs">
                              {item.is_available ? 'Active' : 'Inactive'}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-1">
                              <Button variant="ghost" size="icon" onClick={() => handleEdit(item)}>
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button variant="ghost" size="icon" onClick={() => handleDelete(item.id)} className="text-red-500">
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
              {menuItems.length > 50 && (
                <div className="p-4 text-center text-sm text-foreground/60">
                  Showing 50 of {menuItems.length} items
                </div>
              )}
            </div>
          </TabsContent>

          {/* LOCATIONS TAB */}
          <TabsContent value="locations">
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-playfair text-xl font-semibold">Locations</h2>
              <Button
                onClick={() => { resetLocationForm(); setLocationDialogOpen(true); }}
                className="rounded-full bg-primary"
              >
                <Plus className="mr-2 h-4 w-4" />
                Add Location
              </Button>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {locations.map((loc) => (
                <Card key={loc.id} className="border-orange-900/10">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg flex items-center justify-between">
                      {loc.name}
                      <Badge variant={loc.is_active ? 'default' : 'secondary'}>
                        {loc.country}
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-foreground/70">
                    <p>{loc.city}</p>
                    <p className="truncate">{loc.address}</p>
                    <p className="mt-2">{loc.phone}</p>
                    <div className="flex gap-2 mt-4">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setEditingLocation(loc);
                          setLocationForm(loc);
                          setLocationDialogOpen(true);
                        }}
                      >
                        <Edit className="h-4 w-4 mr-1" /> Edit
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* VIDEOS TAB */}
          <TabsContent value="videos">
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-playfair text-xl font-semibold">Videos & Reels</h2>
              <Button
                onClick={() => setVideoDialogOpen(true)}
                className="rounded-full bg-primary"
              >
                <Plus className="mr-2 h-4 w-4" />
                Add Video
              </Button>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {videos.map((video) => (
                <Card key={video.id} className="border-orange-900/10">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg flex items-center justify-between">
                      {video.title}
                      <Badge variant="outline">{video.category}</Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-foreground/70">
                    <p className="truncate text-xs text-primary">{video.video_url}</p>
                    <p className="mt-2">{video.description}</p>
                    <div className="flex gap-2 mt-4">
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-red-500"
                        onClick={() => handleDeleteVideo(video.id)}
                      >
                        <Trash2 className="h-4 w-4 mr-1" /> Delete
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {videos.length === 0 && (
                <p className="text-foreground/60 col-span-full text-center py-8">
                  No videos added yet
                </p>
              )}
            </div>
          </TabsContent>
        </Tabs>

        {/* Menu Item Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="font-playfair">
                {editingItem ? 'Edit Menu Item' : 'Add Menu Item'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label>Name *</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label>Description *</Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={2}
                  required
                />
              </div>
              <div>
                <Label>Category *</Label>
                <Select
                  value={formData.category}
                  onValueChange={(value) => setFormData({ ...formData, category: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((cat) => (
                      <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Price India (₹)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={formData.price_inr}
                    onChange={(e) => setFormData({ ...formData, price_inr: e.target.value })}
                  />
                </div>
                <div>
                  <Label>Price Australia ($)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={formData.price_aud}
                    onChange={(e) => setFormData({ ...formData, price_aud: e.target.value })}
                  />
                </div>
              </div>
              <div>
                <Label>Image URL</Label>
                <Input
                  type="url"
                  value={formData.image_url}
                  onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
                  placeholder="https://..."
                />
              </div>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_veg}
                    onChange={(e) => setFormData({ ...formData, is_veg: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm">Vegetarian</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_available}
                    onChange={(e) => setFormData({ ...formData, is_available: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm">Available</span>
                </label>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" className="bg-primary">
                  {editingItem ? 'Update' : 'Add'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Location Dialog */}
        <Dialog open={locationDialogOpen} onOpenChange={setLocationDialogOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-playfair">
                {editingLocation ? 'Edit Location' : 'Add Location'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleLocationSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Name *</Label>
                  <Input
                    value={locationForm.name}
                    onChange={(e) => setLocationForm({ ...locationForm, name: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <Label>City *</Label>
                  <Input
                    value={locationForm.city}
                    onChange={(e) => setLocationForm({ ...locationForm, city: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div>
                <Label>Country</Label>
                <Select
                  value={locationForm.country}
                  onValueChange={(value) => setLocationForm({ ...locationForm, country: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="India">India</SelectItem>
                    <SelectItem value="Australia">Australia</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Address *</Label>
                <Textarea
                  value={locationForm.address}
                  onChange={(e) => setLocationForm({ ...locationForm, address: e.target.value })}
                  rows={2}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Phone</Label>
                  <Input
                    value={locationForm.phone}
                    onChange={(e) => setLocationForm({ ...locationForm, phone: e.target.value })}
                  />
                </div>
                <div>
                  <Label>WhatsApp</Label>
                  <Input
                    value={locationForm.whatsapp}
                    onChange={(e) => setLocationForm({ ...locationForm, whatsapp: e.target.value })}
                  />
                </div>
              </div>
              <div>
                <Label>Google Review Link</Label>
                <Input
                  value={locationForm.google_review_link}
                  onChange={(e) => setLocationForm({ ...locationForm, google_review_link: e.target.value })}
                  placeholder="https://g.page/..."
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setLocationDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" className="bg-primary">
                  {editingLocation ? 'Update' : 'Add'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Video Dialog */}
        <Dialog open={videoDialogOpen} onOpenChange={setVideoDialogOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-playfair">Add Video</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleVideoSubmit} className="space-y-4">
              <div>
                <Label>Title *</Label>
                <Input
                  value={videoForm.title}
                  onChange={(e) => setVideoForm({ ...videoForm, title: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label>Video URL *</Label>
                <Input
                  value={videoForm.video_url}
                  onChange={(e) => setVideoForm({ ...videoForm, video_url: e.target.value })}
                  placeholder="YouTube or video URL"
                  required
                />
              </div>
              <div>
                <Label>Thumbnail URL</Label>
                <Input
                  value={videoForm.thumbnail_url}
                  onChange={(e) => setVideoForm({ ...videoForm, thumbnail_url: e.target.value })}
                />
              </div>
              <div>
                <Label>Category</Label>
                <Select
                  value={videoForm.category}
                  onValueChange={(value) => setVideoForm({ ...videoForm, category: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="reels">Reels</SelectItem>
                    <SelectItem value="inspiration">Inspiration</SelectItem>
                    <SelectItem value="recipe">Recipe</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Description</Label>
                <Textarea
                  value={videoForm.description}
                  onChange={(e) => setVideoForm({ ...videoForm, description: e.target.value })}
                  rows={2}
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setVideoDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" className="bg-primary">Add Video</Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
};

export default Admin;
