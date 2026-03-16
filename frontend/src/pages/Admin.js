import { useState, useEffect, useMemo } from 'react';
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
import { Plus, Edit, Trash2, Image as ImageIcon, LogIn, UtensilsCrossed, MapPin, Video, Lock, LogOut, Home, Check, Search, ChevronLeft, ChevronRight, Sparkles, Calendar } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Admin = () => {
  const { user, token, login, logout } = useAuth();
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [loginLoading, setLoginLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('banner');

  // Hero/Banner state
  const [heroImages, setHeroImages] = useState([]);
  const [heroDialogOpen, setHeroDialogOpen] = useState(false);
  const [editingHero, setEditingHero] = useState(null);
  const [heroForm, setHeroForm] = useState({
    title: '',
    description: '',
    image_url: '',
    is_active: true
  });

  // Menu state
  const [menuItems, setMenuItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [menuSearch, setMenuSearch] = useState('');
  const [menuCategoryFilter, setMenuCategoryFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 25;
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

  // Tiffin state
  const [tiffinItems, setTiffinItems] = useState([]);
  const [tiffinConfig, setTiffinConfigState] = useState({
    unlimited_breakfast_price_inr: 299,
    unlimited_breakfast_price_aud: 35,
    unlimited_breakfast_description: 'Unlimited traditional Maharashtrian breakfast buffet',
    unlimited_breakfast_timings: '8:00 AM - 11:00 AM',
    unlimited_breakfast_days: ['Saturday', 'Sunday']
  });
  const [tiffinDialogOpen, setTiffinDialogOpen] = useState(false);
  const [editingTiffinItem, setEditingTiffinItem] = useState(null);
  const [tiffinForm, setTiffinForm] = useState({
    name: '',
    description: '',
    price_inr: '',
    price_aud: '',
    category: 'lunch_box',
    is_available: true,
    image_url: ''
  });

  const tiffinCategories = [
    { id: 'lunch_box', label: 'Lunch Box Options' },
    { id: 'heavy_brunch', label: 'Heavy Brunch Items' },
    { id: 'drink_addon', label: 'Drink Add-ons' }
  ];

  // Festival themes state
  const [festivalThemes, setFestivalThemes] = useState([]);
  const [festivalDialogOpen, setFestivalDialogOpen] = useState(false);
  const [editingFestival, setEditingFestival] = useState(null);
  const [festivalForm, setFestivalForm] = useState({
    month: 1,
    name: '',
    description: '',
    primary_color: '#FF6B00',
    secondary_color: '#FFA500',
    accent_color: '#FFD700',
    greeting_text: '',
    banner_image_url: '',
    is_active: false
  });

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  // Get fresh token
  const getToken = () => localStorage.getItem('token') || token;

  const categories = [
    'Balgopal (Kids)', 'Tea & Coffee', 'Drinks', 'Soup & Saar', 'Snacks',
    'Fasting', 'Heavy Brunch', 'Bhakar Combo', 'Bhaji', 'Dal',
    'Rice', 'Roti', 'Sweets', 'Special Thalis', 'Sides'
  ];

  useEffect(() => {
    const currentToken = getToken();
    if (currentToken) {
      fetchHeroImages();
      fetchMenuItems();
      fetchLocations();
      fetchVideos();
      fetchTiffinItems();
      fetchTiffinConfig();
      fetchFestivalThemes();
    }
  }, [token]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginLoading(true);
    try {
      await login(loginForm.email, loginForm.password);
      toast.success('Logged in successfully');
      setTimeout(() => {
        fetchHeroImages();
        fetchMenuItems();
        fetchLocations();
        fetchVideos();
        fetchTiffinItems();
        fetchTiffinConfig();
        fetchFestivalThemes();
      }, 100);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    setMenuItems([]);
    setLocations([]);
    setVideos([]);
    setHeroImages([]);
    toast.success('Logged out');
  };

  // Hero Image functions
  const fetchHeroImages = async () => {
    const currentToken = getToken();
    if (!currentToken) return;
    try {
      const response = await axios.get(`${API}/admin/hero-images`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      setHeroImages(response.data);
    } catch (error) {
      console.error('Failed to fetch hero images:', error);
    }
  };

  const handleHeroSubmit = async (e) => {
    e.preventDefault();
    const currentToken = getToken();
    if (!currentToken) {
      toast.error('Please login again');
      return;
    }

    try {
      if (editingHero) {
        await axios.put(
          `${API}/admin/hero-images/${editingHero.id}`,
          heroForm,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Banner updated successfully!');
      } else {
        await axios.post(
          `${API}/admin/hero-images`,
          heroForm,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Banner added successfully!');
      }
      setHeroDialogOpen(false);
      resetHeroForm();
      fetchHeroImages();
    } catch (error) {
      toast.error('Operation failed');
    }
  };

  const handleSetActiveHero = async (heroId) => {
    const currentToken = getToken();
    try {
      await axios.put(
        `${API}/admin/hero-images/${heroId}`,
        { is_active: true },
        { headers: { Authorization: `Bearer ${currentToken}` } }
      );
      toast.success('Banner set as active!');
      fetchHeroImages();
    } catch (error) {
      toast.error('Failed to set active');
    }
  };

  const handleDeleteHero = async (id) => {
    if (!window.confirm('Delete this banner?')) return;
    const currentToken = getToken();
    try {
      await axios.delete(`${API}/admin/hero-images/${id}`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      toast.success('Banner deleted');
      fetchHeroImages();
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  const resetHeroForm = () => {
    setEditingHero(null);
    setHeroForm({ title: '', description: '', image_url: '', is_active: true });
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

  // Get unique categories for filter
  const menuCategories = useMemo(() => {
    const cats = [...new Set(menuItems.map(item => item.category))].filter(Boolean);
    return cats.sort();
  }, [menuItems]);

  // Filter and paginate menu items
  const filteredMenuItems = useMemo(() => {
    let filtered = menuItems;
    
    if (menuSearch) {
      const search = menuSearch.toLowerCase();
      filtered = filtered.filter(item => 
        item.name?.toLowerCase().includes(search) ||
        item.category?.toLowerCase().includes(search)
      );
    }
    
    if (menuCategoryFilter !== 'all') {
      filtered = filtered.filter(item => item.category === menuCategoryFilter);
    }
    
    return filtered;
  }, [menuItems, menuSearch, menuCategoryFilter]);

  // Paginated items
  const paginatedMenuItems = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredMenuItems.slice(start, start + itemsPerPage);
  }, [filteredMenuItems, currentPage]);

  const totalPages = Math.ceil(filteredMenuItems.length / itemsPerPage);

  // Reset page when filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [menuSearch, menuCategoryFilter]);

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
    
    const submitData = {
      name: formData.name,
      description: formData.description,
      category: formData.category,
      price_inr: formData.price_inr ? parseFloat(formData.price_inr) : null,
      price_aud: formData.price_aud ? parseFloat(formData.price_aud) : null,
      image_url: formData.image_url || null,
      is_veg: formData.is_veg,
      is_available: formData.is_available
    };
    
    try {
      if (editingItem) {
        await axios.put(
          `${API}/admin/menu/${editingItem.id}`,
          submitData,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Menu item updated successfully!');
      } else {
        await axios.post(
          `${API}/admin/menu`,
          submitData,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Menu item added successfully!');
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
    if (!window.confirm('Are you sure you want to delete this item?')) return;
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
      name: '', description: '', category: '',
      price_inr: '', price_aud: '', image_url: '',
      is_veg: true, is_available: true
    });
  };

  // Location CRUD
  const handleLocationSubmit = async (e) => {
    e.preventDefault();
    const currentToken = getToken();
    try {
      if (editingLocation) {
        await axios.put(
          `${API}/admin/locations/${editingLocation.id}`,
          locationForm,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Location updated');
      } else {
        await axios.post(
          `${API}/admin/locations`,
          locationForm,
          { headers: { Authorization: `Bearer ${currentToken}` } }
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
      name: '', city: '', country: 'India', address: '',
      phone: '', whatsapp: '', google_review_link: '', is_active: true
    });
  };

  // Video CRUD
  const handleVideoSubmit = async (e) => {
    e.preventDefault();
    const currentToken = getToken();
    try {
      await axios.post(
        `${API}/admin/videos`,
        { ...videoForm, is_active: true },
        { headers: { Authorization: `Bearer ${currentToken}` } }
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
    const currentToken = getToken();
    try {
      await axios.delete(`${API}/admin/videos/${id}`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      toast.success('Video deleted');
      fetchVideos();
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  // Tiffin CRUD functions
  const fetchTiffinItems = async () => {
    const currentToken = getToken();
    if (!currentToken) return;
    try {
      const response = await axios.get(`${API}/admin/tiffin-items`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      setTiffinItems(response.data);
    } catch (error) {
      console.error('Failed to fetch tiffin items:', error);
    }
  };

  const fetchTiffinConfig = async () => {
    try {
      const response = await axios.get(`${API}/tiffin-config`);
      setTiffinConfigState(response.data);
    } catch (error) {
      console.error('Failed to fetch tiffin config:', error);
    }
  };

  const handleTiffinSubmit = async (e) => {
    e.preventDefault();
    const currentToken = getToken();
    const submitData = {
      ...tiffinForm,
      price_inr: parseFloat(tiffinForm.price_inr) || 0,
      price_aud: parseFloat(tiffinForm.price_aud) || 0
    };

    try {
      if (editingTiffinItem) {
        await axios.put(
          `${API}/admin/tiffin-items/${editingTiffinItem.id}`,
          submitData,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Tiffin item updated!');
      } else {
        await axios.post(
          `${API}/admin/tiffin-items`,
          submitData,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Tiffin item added!');
      }
      setTiffinDialogOpen(false);
      resetTiffinForm();
      fetchTiffinItems();
    } catch (error) {
      toast.error('Operation failed');
    }
  };

  const handleDeleteTiffinItem = async (id) => {
    if (!window.confirm('Delete this tiffin item?')) return;
    const currentToken = getToken();
    try {
      await axios.delete(`${API}/admin/tiffin-items/${id}`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      toast.success('Item deleted');
      fetchTiffinItems();
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  const handleEditTiffinItem = (item) => {
    setEditingTiffinItem(item);
    setTiffinForm({
      name: item.name,
      description: item.description || '',
      price_inr: item.price_inr || '',
      price_aud: item.price_aud || '',
      category: item.category,
      is_available: item.is_available,
      image_url: item.image_url || ''
    });
    setTiffinDialogOpen(true);
  };

  const resetTiffinForm = () => {
    setEditingTiffinItem(null);
    setTiffinForm({
      name: '',
      description: '',
      price_inr: '',
      price_aud: '',
      category: 'lunch_box',
      is_available: true,
      image_url: ''
    });
  };

  const handleTiffinConfigSave = async () => {
    const currentToken = getToken();
    try {
      await axios.put(
        `${API}/admin/tiffin-config`,
        tiffinConfig,
        { headers: { Authorization: `Bearer ${currentToken}` } }
      );
      toast.success('Tiffin config saved!');
    } catch (error) {
      toast.error('Failed to save config');
    }
  };

  // Festival Theme CRUD functions
  const fetchFestivalThemes = async () => {
    const currentToken = getToken();
    if (!currentToken) return;
    try {
      const response = await axios.get(`${API}/admin/festival-themes`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      setFestivalThemes(response.data);
    } catch (error) {
      console.error('Failed to fetch festival themes:', error);
    }
  };

  const handleFestivalSubmit = async (e) => {
    e.preventDefault();
    const currentToken = getToken();
    try {
      if (editingFestival) {
        await axios.put(
          `${API}/admin/festival-themes/${editingFestival.id}`,
          festivalForm,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Festival theme updated!');
      } else {
        await axios.post(
          `${API}/admin/festival-themes`,
          festivalForm,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Festival theme created!');
      }
      setFestivalDialogOpen(false);
      resetFestivalForm();
      fetchFestivalThemes();
    } catch (error) {
      toast.error('Operation failed');
    }
  };

  const handleActivateFestival = async (themeId) => {
    const currentToken = getToken();
    try {
      await axios.put(
        `${API}/admin/festival-themes/${themeId}`,
        { is_active: true },
        { headers: { Authorization: `Bearer ${currentToken}` } }
      );
      toast.success('Festival theme activated! 🎉');
      fetchFestivalThemes();
    } catch (error) {
      toast.error('Failed to activate');
    }
  };

  const handleDeactivateFestival = async (themeId) => {
    const currentToken = getToken();
    try {
      await axios.put(
        `${API}/admin/festival-themes/${themeId}`,
        { is_active: false },
        { headers: { Authorization: `Bearer ${currentToken}` } }
      );
      toast.success('Festival theme deactivated');
      fetchFestivalThemes();
    } catch (error) {
      toast.error('Failed to deactivate');
    }
  };

  const handleEditFestival = (theme) => {
    setEditingFestival(theme);
    setFestivalForm({
      month: theme.month,
      name: theme.name,
      description: theme.description || '',
      primary_color: theme.primary_color || '#FF6B00',
      secondary_color: theme.secondary_color || '#FFA500',
      accent_color: theme.accent_color || '#FFD700',
      greeting_text: theme.greeting_text || '',
      banner_image_url: theme.banner_image_url || '',
      is_active: theme.is_active || false
    });
    setFestivalDialogOpen(true);
  };

  const resetFestivalForm = () => {
    setEditingFestival(null);
    setFestivalForm({
      month: 1,
      name: '',
      description: '',
      primary_color: '#FF6B00',
      secondary_color: '#FFA500',
      accent_color: '#FFD700',
      greeting_text: '',
      banner_image_url: '',
      is_active: false
    });
  };

  // Check if logged in
  const isLoggedIn = !!getToken();

  // Login Screen
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-[hsl(30,20%,97%)] to-white flex items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          <Card className="border-[hsl(30,30%,88%)]">
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
              <div className="mt-4 p-3 bg-[hsl(45,80%,95%)] rounded-lg">
                <p className="text-xs text-foreground/60 font-manrope">
                  <strong>Admin Credentials:</strong><br />
                  Email: PBadmin@purnabramha.com<br />
                  Password: PB22052012
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-[hsl(30,20%,97%)] to-white">
      <div className="container mx-auto px-4 lg:px-8 py-8 lg:py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 flex items-center justify-between"
        >
          <div>
            <h1 className="font-playfair text-3xl lg:text-4xl font-bold text-foreground mb-2">
              Admin Dashboard
            </h1>
            <p className="text-foreground/70 font-manrope">
              Manage your restaurant menu, locations, and content
            </p>
          </div>
          <Button variant="outline" onClick={handleLogout} className="flex items-center gap-2">
            <LogOut className="h-4 w-4" />
            Logout
          </Button>
        </motion.div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6 bg-white border border-[hsl(30,30%,88%)] flex-wrap">
            <TabsTrigger value="banner" className="flex items-center gap-2">
              <Home className="h-4 w-4" />
              Home Banner
            </TabsTrigger>
            <TabsTrigger value="festival" className="flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              Festivals
            </TabsTrigger>
            <TabsTrigger value="menu" className="flex items-center gap-2">
              <UtensilsCrossed className="h-4 w-4" />
              Menu ({menuItems.length})
            </TabsTrigger>
            <TabsTrigger value="tiffin" className="flex items-center gap-2">
              <UtensilsCrossed className="h-4 w-4" />
              Tiffin ({tiffinItems.length})
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

          {/* HOME BANNER TAB */}
          <TabsContent value="banner">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h2 className="font-playfair text-xl font-semibold">Home Page Banner</h2>
                <p className="text-sm text-foreground/60">Manage the hero image, title, and description shown on the homepage</p>
              </div>
              <Button
                onClick={() => { resetHeroForm(); setHeroDialogOpen(true); }}
                className="rounded-full bg-primary"
                data-testid="add-banner-btn"
              >
                <Plus className="mr-2 h-4 w-4" />
                Add Banner
              </Button>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {heroImages.length === 0 ? (
                <Card className="col-span-full border-dashed">
                  <CardContent className="p-8 text-center">
                    <ImageIcon className="h-12 w-12 mx-auto text-foreground/30 mb-4" />
                    <p className="text-foreground/60 mb-4">No banners added yet. Add your first home banner!</p>
                    <Button onClick={() => { resetHeroForm(); setHeroDialogOpen(true); }} className="bg-primary">
                      <Plus className="mr-2 h-4 w-4" /> Add Banner
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                heroImages.map((hero) => (
                  <Card key={hero.id} className={`border-[hsl(30,30%,88%)] overflow-hidden ${hero.is_active ? 'ring-2 ring-primary' : ''}`}>
                    <div className="h-40 overflow-hidden relative">
                      <img 
                        src={hero.image_url} 
                        alt={hero.title} 
                        className="w-full h-full object-cover"
                        onError={(e) => { e.target.src = 'https://via.placeholder.com/400x200?text=Image+Error'; }}
                      />
                      {hero.is_active && (
                        <Badge className="absolute top-2 right-2 bg-primary">
                          <Check className="h-3 w-3 mr-1" /> Active
                        </Badge>
                      )}
                    </div>
                    <CardContent className="p-4">
                      <h3 className="font-playfair text-lg font-semibold mb-1 line-clamp-1">{hero.title}</h3>
                      <p className="text-sm text-foreground/60 line-clamp-2 mb-3">{hero.description}</p>
                      <div className="flex gap-2">
                        {!hero.is_active && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleSetActiveHero(hero.id)}
                            className="text-primary"
                          >
                            <Check className="h-4 w-4 mr-1" /> Set Active
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setEditingHero(hero);
                            setHeroForm({
                              title: hero.title,
                              description: hero.description || '',
                              image_url: hero.image_url,
                              is_active: hero.is_active
                            });
                            setHeroDialogOpen(true);
                          }}
                        >
                          <Edit className="h-4 w-4 mr-1" /> Edit
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-red-500"
                          onClick={() => handleDeleteHero(hero.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>

            {/* Instructions */}
            <Card className="mt-6 bg-[hsl(45,80%,95%)] border-[hsl(38,70%,45%)]/30">
              <CardContent className="p-4">
                <h4 className="font-semibold text-sm mb-2">How to change the home banner:</h4>
                <ol className="text-sm text-foreground/70 space-y-1 list-decimal list-inside">
                  <li>Click <strong>"Add Banner"</strong> to create a new banner</li>
                  <li>Enter the title, description, and paste the image URL</li>
                  <li>Click <strong>"Set Active"</strong> on any banner to show it on the homepage</li>
                  <li>Only one banner can be active at a time</li>
                </ol>
              </CardContent>
            </Card>
          </TabsContent>

          {/* FESTIVAL THEMES TAB */}
          <TabsContent value="festival">
            <div className="space-y-6">
              {/* Info Banner */}
              <Card className="bg-gradient-to-r from-orange-50 to-amber-50 border-orange-200">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <Sparkles className="h-6 w-6 text-orange-500 mt-0.5" />
                    <div>
                      <h3 className="font-semibold text-orange-800">Festival Theme Management</h3>
                      <p className="text-sm text-orange-700 mt-1">
                        Set up festival themes for each month. The active theme will be displayed across your website with special colors, 
                        greetings, and decorations. <strong>Gudhi Padwa / Ugadi</strong> is set for March 21st - Maharashtra New Year!
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Festival Grid */}
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {festivalThemes.map((theme) => (
                  <Card 
                    key={theme.id} 
                    className={`border-2 overflow-hidden transition-all ${theme.is_active ? 'ring-2 ring-offset-2 ring-green-500 border-green-300' : 'border-gray-200'}`}
                  >
                    <div 
                      className="h-3"
                      style={{ background: `linear-gradient(90deg, ${theme.primary_color}, ${theme.secondary_color}, ${theme.accent_color})` }}
                    />
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-lg flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-gray-500" />
                          {monthNames[theme.month - 1]}
                        </CardTitle>
                        {theme.is_active && (
                          <Badge className="bg-green-500">Active</Badge>
                        )}
                      </div>
                      <p className="font-semibold text-primary">{theme.name}</p>
                    </CardHeader>
                    <CardContent className="pt-0">
                      {theme.greeting_text && (
                        <p className="text-sm text-gray-600 mb-3 italic">"{theme.greeting_text}"</p>
                      )}
                      <div className="flex gap-2 mb-3">
                        <div 
                          className="w-8 h-8 rounded-full border-2 border-white shadow"
                          style={{ backgroundColor: theme.primary_color }}
                          title="Primary Color"
                        />
                        <div 
                          className="w-8 h-8 rounded-full border-2 border-white shadow"
                          style={{ backgroundColor: theme.secondary_color }}
                          title="Secondary Color"
                        />
                        <div 
                          className="w-8 h-8 rounded-full border-2 border-white shadow"
                          style={{ backgroundColor: theme.accent_color }}
                          title="Accent Color"
                        />
                      </div>
                      <div className="flex gap-2 flex-wrap">
                        {theme.is_active ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDeactivateFestival(theme.id)}
                            className="text-gray-600"
                          >
                            Deactivate
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            onClick={() => handleActivateFestival(theme.id)}
                            className="bg-green-600 hover:bg-green-700"
                          >
                            <Check className="h-4 w-4 mr-1" /> Activate
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEditFestival(theme)}
                        >
                          <Edit className="h-4 w-4 mr-1" /> Edit
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {festivalThemes.length === 0 && (
                <Card className="border-dashed">
                  <CardContent className="p-8 text-center">
                    <Sparkles className="h-12 w-12 mx-auto text-gray-300 mb-4" />
                    <p className="text-gray-500 mb-4">Loading festival themes...</p>
                  </CardContent>
                </Card>
              )}

              {/* Instructions */}
              <Card className="bg-blue-50 border-blue-200">
                <CardContent className="p-4">
                  <h4 className="font-semibold text-sm mb-2 text-blue-800">How to use Festival Themes:</h4>
                  <ol className="text-sm text-blue-700 space-y-1 list-decimal list-inside">
                    <li>Each month has a pre-configured festival theme based on Maharashtrian calendar</li>
                    <li>Click <strong>"Edit"</strong> to customize colors, greeting text, and banner image</li>
                    <li>Click <strong>"Activate"</strong> to apply the theme to your website</li>
                    <li>Only one theme can be active at a time - it will show on the homepage</li>
                    <li>For Gudhi Padwa (March 21), activate the March theme!</li>
                  </ol>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

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

            {/* Search and Filter */}
            <div className="flex flex-wrap gap-4 mb-4">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search by name or category..."
                  value={menuSearch}
                  onChange={(e) => setMenuSearch(e.target.value)}
                  className="pl-10"
                  data-testid="menu-search"
                />
              </div>
              <Select value={menuCategoryFilter} onValueChange={setMenuCategoryFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Filter by category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {menuCategories.map(cat => (
                    <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="text-sm text-gray-500 flex items-center">
                {filteredMenuItems.length} of {menuItems.length} items
              </div>
            </div>

            <div className="bg-white rounded-xl border border-[hsl(30,30%,88%)] overflow-hidden">
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
                    ) : paginatedMenuItems.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-8">
                          {menuSearch || menuCategoryFilter !== 'all' ? 'No items match your search' : 'No menu items'}
                        </TableCell>
                      </TableRow>
                    ) : (
                      paginatedMenuItems.map((item) => (
                        <TableRow key={item.id} className={!item.image_url ? 'bg-amber-50' : ''}>
                          <TableCell>
                            {item.image_url ? (
                              <img src={item.image_url} alt={item.name} className="w-10 h-10 object-cover rounded" />
                            ) : (
                              <div className="w-10 h-10 bg-red-100 rounded flex items-center justify-center" title="No image">
                                <ImageIcon className="h-5 w-5 text-red-400" />
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
                              <Button variant="ghost" size="icon" onClick={() => handleEdit(item)} data-testid={`edit-${item.id}`}>
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
              
              {/* Pagination */}
              {totalPages > 1 && (
                <div className="p-4 flex items-center justify-between border-t">
                  <div className="text-sm text-gray-500">
                    Page {currentPage} of {totalPages} • Showing {paginatedMenuItems.length} items
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          {/* TIFFIN TAB */}
          <TabsContent value="tiffin">
            <div className="space-y-6">
              {/* Unlimited Breakfast Config */}
              <Card className="border-amber-200">
                <CardHeader className="bg-gradient-to-r from-amber-50 to-orange-50">
                  <CardTitle className="text-lg flex items-center gap-2">
                    ☀️ Unlimited Breakfast Settings
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4 space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <Label>Price (₹ INR)</Label>
                      <Input
                        type="number"
                        value={tiffinConfig.unlimited_breakfast_price_inr}
                        onChange={(e) => setTiffinConfigState({...tiffinConfig, unlimited_breakfast_price_inr: parseFloat(e.target.value) || 0})}
                      />
                    </div>
                    <div>
                      <Label>Price ($ AUD)</Label>
                      <Input
                        type="number"
                        value={tiffinConfig.unlimited_breakfast_price_aud}
                        onChange={(e) => setTiffinConfigState({...tiffinConfig, unlimited_breakfast_price_aud: parseFloat(e.target.value) || 0})}
                      />
                    </div>
                  </div>
                  <div>
                    <Label>Description</Label>
                    <Input
                      value={tiffinConfig.unlimited_breakfast_description}
                      onChange={(e) => setTiffinConfigState({...tiffinConfig, unlimited_breakfast_description: e.target.value})}
                    />
                  </div>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <Label>Timings</Label>
                      <Input
                        value={tiffinConfig.unlimited_breakfast_timings}
                        onChange={(e) => setTiffinConfigState({...tiffinConfig, unlimited_breakfast_timings: e.target.value})}
                      />
                    </div>
                    <div>
                      <Label>Available Days</Label>
                      <Input
                        value={tiffinConfig.unlimited_breakfast_days?.join(', ')}
                        onChange={(e) => setTiffinConfigState({...tiffinConfig, unlimited_breakfast_days: e.target.value.split(',').map(d => d.trim())})}
                        placeholder="Saturday, Sunday"
                      />
                    </div>
                  </div>
                  <Button onClick={handleTiffinConfigSave} className="bg-amber-600 hover:bg-amber-700">
                    Save Breakfast Config
                  </Button>
                </CardContent>
              </Card>

              {/* Tiffin Items Management */}
              <div className="flex justify-between items-center">
                <h2 className="font-playfair text-xl font-semibold">Tiffin Menu Items</h2>
                <Button
                  onClick={() => { resetTiffinForm(); setTiffinDialogOpen(true); }}
                  className="rounded-full bg-primary"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add Tiffin Item
                </Button>
              </div>

              {tiffinCategories.map(cat => {
                const items = tiffinItems.filter(i => i.category === cat.id);
                return (
                  <Card key={cat.id} className="border-[hsl(30,30%,88%)]">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg">{cat.label} ({items.length})</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {items.length === 0 ? (
                        <p className="text-sm text-gray-500">No items yet. Click "Add Tiffin Item" to add.</p>
                      ) : (
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Image</TableHead>
                              <TableHead>Name</TableHead>
                              <TableHead>₹ INR</TableHead>
                              <TableHead>$ AUD</TableHead>
                              <TableHead>Status</TableHead>
                              <TableHead>Actions</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {items.map(item => (
                              <TableRow key={item.id}>
                                <TableCell>
                                  {item.image_url ? (
                                    <img src={item.image_url} alt={item.name} className="w-10 h-10 object-cover rounded" />
                                  ) : (
                                    <div className="w-10 h-10 bg-red-100 rounded flex items-center justify-center">
                                      <ImageIcon className="h-5 w-5 text-red-400" />
                                    </div>
                                  )}
                                </TableCell>
                                <TableCell className="font-medium">{item.name}</TableCell>
                                <TableCell>₹{item.price_inr}</TableCell>
                                <TableCell>${item.price_aud}</TableCell>
                                <TableCell>
                                  <Badge variant={item.is_available ? 'default' : 'secondary'}>
                                    {item.is_available ? 'Active' : 'Inactive'}
                                  </Badge>
                                </TableCell>
                                <TableCell>
                                  <div className="flex gap-1">
                                    <Button variant="ghost" size="icon" onClick={() => handleEditTiffinItem(item)}>
                                      <Edit className="h-4 w-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon" onClick={() => handleDeleteTiffinItem(item.id)} className="text-red-500">
                                      <Trash2 className="h-4 w-4" />
                                    </Button>
                                  </div>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
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
                <Card key={loc.id} className="border-[hsl(30,30%,88%)]">
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
                <Card key={video.id} className="border-[hsl(30,30%,88%)]">
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
                  data-testid="menu-name-input"
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
                  <SelectTrigger data-testid="menu-category-select">
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
                    data-testid="menu-price-inr"
                  />
                </div>
                <div>
                  <Label>Price Australia ($)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={formData.price_aud}
                    onChange={(e) => setFormData({ ...formData, price_aud: e.target.value })}
                    data-testid="menu-price-aud"
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
                <p className="text-xs text-foreground/50 mt-1">
                  For Google Drive: Use https://lh3.googleusercontent.com/d/YOUR_FILE_ID
                </p>
              </div>
              {formData.image_url && (
                <div className="rounded-lg overflow-hidden border">
                  <img 
                    src={formData.image_url} 
                    alt="Preview" 
                    className="w-full h-24 object-cover"
                    onError={(e) => { e.target.src = 'https://via.placeholder.com/200x100?text=Invalid+URL'; }}
                  />
                  <p className="text-xs text-center py-1 bg-muted">Image Preview</p>
                </div>
              )}
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
                <Button type="submit" className="bg-primary" data-testid="save-menu-item-btn">
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

        {/* Hero/Banner Dialog */}
        <Dialog open={heroDialogOpen} onOpenChange={setHeroDialogOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-playfair">
                {editingHero ? 'Edit Home Banner' : 'Add Home Banner'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleHeroSubmit} className="space-y-4">
              <div>
                <Label>Title *</Label>
                <Input
                  value={heroForm.title}
                  onChange={(e) => setHeroForm({ ...heroForm, title: e.target.value })}
                  placeholder="e.g., Authentic Maharashtrian Flavors"
                  required
                  data-testid="hero-title-input"
                />
              </div>
              <div>
                <Label>Description</Label>
                <Textarea
                  value={heroForm.description}
                  onChange={(e) => setHeroForm({ ...heroForm, description: e.target.value })}
                  placeholder="e.g., Experience the richness of traditional recipes..."
                  rows={3}
                />
              </div>
              <div>
                <Label>Image URL *</Label>
                <Input
                  type="url"
                  value={heroForm.image_url}
                  onChange={(e) => setHeroForm({ ...heroForm, image_url: e.target.value })}
                  placeholder="https://..."
                  required
                  data-testid="hero-image-input"
                />
                <p className="text-xs text-foreground/50 mt-1">
                  Paste a direct image URL. Recommended size: 1920x1080 or similar wide format.
                </p>
              </div>
              {heroForm.image_url && (
                <div className="rounded-lg overflow-hidden border">
                  <img 
                    src={heroForm.image_url} 
                    alt="Preview" 
                    className="w-full h-32 object-cover"
                    onError={(e) => { e.target.src = 'https://via.placeholder.com/400x200?text=Invalid+URL'; }}
                  />
                  <p className="text-xs text-center py-1 bg-muted">Image Preview</p>
                </div>
              )}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={heroForm.is_active}
                  onChange={(e) => setHeroForm({ ...heroForm, is_active: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm">Set as active banner (will be shown on homepage)</span>
              </label>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setHeroDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" className="bg-primary" data-testid="save-hero-btn">
                  {editingHero ? 'Update' : 'Add Banner'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Festival Theme Dialog */}
        <Dialog open={festivalDialogOpen} onOpenChange={setFestivalDialogOpen}>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="font-playfair flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-orange-500" />
                {editingFestival ? 'Edit Festival Theme' : 'Add Festival Theme'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleFestivalSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Month *</Label>
                  <Select
                    value={String(festivalForm.month)}
                    onValueChange={(value) => setFestivalForm({ ...festivalForm, month: parseInt(value) })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {monthNames.map((month, idx) => (
                        <SelectItem key={idx + 1} value={String(idx + 1)}>{month}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Festival Name *</Label>
                  <Input
                    value={festivalForm.name}
                    onChange={(e) => setFestivalForm({ ...festivalForm, name: e.target.value })}
                    placeholder="e.g., Gudhi Padwa"
                    required
                  />
                </div>
              </div>
              <div>
                <Label>Greeting Text (Marathi/English)</Label>
                <Input
                  value={festivalForm.greeting_text}
                  onChange={(e) => setFestivalForm({ ...festivalForm, greeting_text: e.target.value })}
                  placeholder="e.g., गुढीपाडव्याच्या हार्दिक शुभेच्छा!"
                />
              </div>
              <div>
                <Label>Description</Label>
                <Textarea
                  value={festivalForm.description}
                  onChange={(e) => setFestivalForm({ ...festivalForm, description: e.target.value })}
                  rows={2}
                  placeholder="Brief description of the festival..."
                />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <Label>Primary Color</Label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={festivalForm.primary_color}
                      onChange={(e) => setFestivalForm({ ...festivalForm, primary_color: e.target.value })}
                      className="w-10 h-10 rounded cursor-pointer"
                    />
                    <Input
                      value={festivalForm.primary_color}
                      onChange={(e) => setFestivalForm({ ...festivalForm, primary_color: e.target.value })}
                      className="flex-1 text-xs"
                    />
                  </div>
                </div>
                <div>
                  <Label>Secondary Color</Label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={festivalForm.secondary_color}
                      onChange={(e) => setFestivalForm({ ...festivalForm, secondary_color: e.target.value })}
                      className="w-10 h-10 rounded cursor-pointer"
                    />
                    <Input
                      value={festivalForm.secondary_color}
                      onChange={(e) => setFestivalForm({ ...festivalForm, secondary_color: e.target.value })}
                      className="flex-1 text-xs"
                    />
                  </div>
                </div>
                <div>
                  <Label>Accent Color</Label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={festivalForm.accent_color}
                      onChange={(e) => setFestivalForm({ ...festivalForm, accent_color: e.target.value })}
                      className="w-10 h-10 rounded cursor-pointer"
                    />
                    <Input
                      value={festivalForm.accent_color}
                      onChange={(e) => setFestivalForm({ ...festivalForm, accent_color: e.target.value })}
                      className="flex-1 text-xs"
                    />
                  </div>
                </div>
              </div>
              <div 
                className="h-8 rounded-lg"
                style={{ background: `linear-gradient(90deg, ${festivalForm.primary_color}, ${festivalForm.secondary_color}, ${festivalForm.accent_color})` }}
              />
              <div>
                <Label>Banner Image URL (optional)</Label>
                <Input
                  type="url"
                  value={festivalForm.banner_image_url}
                  onChange={(e) => setFestivalForm({ ...festivalForm, banner_image_url: e.target.value })}
                  placeholder="https://..."
                />
              </div>
              {festivalForm.banner_image_url && (
                <div className="rounded-lg overflow-hidden border">
                  <img 
                    src={festivalForm.banner_image_url} 
                    alt="Preview" 
                    className="w-full h-24 object-cover"
                    onError={(e) => { e.target.src = 'https://via.placeholder.com/400x100?text=Invalid+URL'; }}
                  />
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setFestivalDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" className="bg-orange-600 hover:bg-orange-700">
                  {editingFestival ? 'Update Theme' : 'Create Theme'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Tiffin Item Dialog */}
        <Dialog open={tiffinDialogOpen} onOpenChange={setTiffinDialogOpen}>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="font-playfair">
                {editingTiffinItem ? 'Edit Tiffin Item' : 'Add Tiffin Item'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleTiffinSubmit} className="space-y-4">
              <div>
                <Label>Name *</Label>
                <Input
                  value={tiffinForm.name}
                  onChange={(e) => setTiffinForm({ ...tiffinForm, name: e.target.value })}
                  placeholder="e.g., Roti + Bhaji + Rice + Dal"
                  required
                  data-testid="tiffin-name-input"
                />
              </div>
              <div>
                <Label>Description</Label>
                <Textarea
                  value={tiffinForm.description}
                  onChange={(e) => setTiffinForm({ ...tiffinForm, description: e.target.value })}
                  placeholder="Brief description of the item"
                  rows={2}
                />
              </div>
              <div>
                <Label>Category *</Label>
                <Select
                  value={tiffinForm.category}
                  onValueChange={(value) => setTiffinForm({ ...tiffinForm, category: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {tiffinCategories.map((cat) => (
                      <SelectItem key={cat.id} value={cat.id}>{cat.label}</SelectItem>
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
                    value={tiffinForm.price_inr}
                    onChange={(e) => setTiffinForm({ ...tiffinForm, price_inr: e.target.value })}
                    placeholder="e.g., 150"
                  />
                </div>
                <div>
                  <Label>Price Australia ($)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={tiffinForm.price_aud}
                    onChange={(e) => setTiffinForm({ ...tiffinForm, price_aud: e.target.value })}
                    placeholder="e.g., 12"
                  />
                </div>
              </div>
              <div>
                <Label>Image URL (optional)</Label>
                <Input
                  type="url"
                  value={tiffinForm.image_url}
                  onChange={(e) => setTiffinForm({ ...tiffinForm, image_url: e.target.value })}
                  placeholder="https://..."
                />
              </div>
              {tiffinForm.image_url && (
                <div className="rounded-lg overflow-hidden border">
                  <img 
                    src={tiffinForm.image_url} 
                    alt="Preview" 
                    className="w-full h-24 object-cover"
                    onError={(e) => { e.target.src = 'https://via.placeholder.com/200x100?text=Invalid+URL'; }}
                  />
                </div>
              )}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={tiffinForm.is_available}
                  onChange={(e) => setTiffinForm({ ...tiffinForm, is_available: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm">Available for ordering</span>
              </label>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setTiffinDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" className="bg-amber-600 hover:bg-amber-700" data-testid="save-tiffin-btn">
                  {editingTiffinItem ? 'Update' : 'Add Item'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
};

export default Admin;
