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
import { Plus, Edit, Trash2, Image as ImageIcon, LogIn, UtensilsCrossed, MapPin, Video, Lock, LogOut, Home, Check, Search, ChevronLeft, ChevronRight, Sparkles, Calendar, BookOpen, Music, Coffee, Headphones, Smartphone, Clock } from 'lucide-react';
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
  
  // Bulk Image Upload state
  const [bulkImageMode, setBulkImageMode] = useState(false);
  const [bulkImageData, setBulkImageData] = useState({});
  const [bulkSaving, setBulkSaving] = useState(false);
  // Bulk Nutrition Generation state
  const [nutritionGenerating, setNutritionGenerating] = useState(false);
  const [nutritionProgress, setNutritionProgress] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: '',
    price_inr: '',
    price_aud: '',
    image_url: '',
    is_veg: true,
    is_available: true,
    no_onion_garlic: false,
    fasting_friendly: false
  });

  // Locations state
  const [locations, setLocations] = useState([]);
  const [locationDialogOpen, setLocationDialogOpen] = useState(false);
  const [editingLocation, setEditingLocation] = useState(null);
  const [activeLocationTab, setActiveLocationTab] = useState({}); // { [locationId]: 'info' | 'slots' }
  const [locationForm, setLocationForm] = useState({
    name: '',
    city: '',
    country: 'India',
    address: '',
    phone: '',
    whatsapp: '',
    google_review_link: '',
    is_active: true,
    center_id: '',
    display_name: '',
    state: '',
    currency: 'INR',
    currency_symbol: '₹',
    services: ['dine-in', 'pickup', 'tiffin', 'catering', 'unlimited-breakfast']
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

  // Catering state
  const [cateringPackages, setCateringPackages] = useState([]);
  const [cateringMenuItems, setCateringMenuItems] = useState([]);
  const [cateringPackageDialogOpen, setCateringPackageDialogOpen] = useState(false);
  const [cateringItemDialogOpen, setCateringItemDialogOpen] = useState(false);
  const [editingCateringPackage, setEditingCateringPackage] = useState(null);
  const [editingCateringItem, setEditingCateringItem] = useState(null);
  const [cateringPackageForm, setCateringPackageForm] = useState({
    name: '',
    description: '',
    price_per_person_inr: '',
    price_per_person_aud: '',
    is_popular: false,
    requirements: { starters: 0, mains: 0, special: 0, roti: 0, rice: 0, side: 0, dessert: 0, drink: 0, chutney: 0 },
    is_active: true,
    display_order: 0
  });
  const [cateringItemForm, setCateringItemForm] = useState({
    name: '',
    description: '',
    category: 'starters',
    image_url: '',
    is_veg: true,
    is_available: true
  });

  const cateringCategories = [
    { id: 'starters', label: 'Starters' },
    { id: 'specialBhaji', label: 'Special Bhaji' },
    { id: 'simpleBhaji', label: 'Simple Bhaji / Mains' },
    { id: 'desserts', label: 'Desserts' },
    { id: 'roti', label: 'Roti / Breads' },
    { id: 'rice', label: 'Rice' },
    { id: 'drinks', label: 'Drinks' },
    { id: 'sides', label: 'Sides' },
    { id: 'chutney', label: 'Chutney' }
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

  // Book Settings state
  const [bookSettings, setBookSettings] = useState({ break_interval: 20, music_url: '', break_shayaris: [], listen_enabled: true });
  const [bookAnalytics, setBookAnalytics] = useState(null);
  const [newShayari, setNewShayari] = useState('');
  const [musicUploading, setMusicUploading] = useState(false);
  const [upiPayments, setUpiPayments] = useState([]);
  const [centerSlots, setCenterSlots] = useState({});
  const [editingSlots, setEditingSlots] = useState(null); // center_id being edited
  const [slotsForm, setSlotsForm] = useState([]);

  // Promotions state
  const [promotions, setPromotions] = useState(null);
  const [promoSaving, setPromoSaving] = useState(false);

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
      fetchCateringPackages();
      fetchCateringMenuItems();
      fetchBookSettings();
      fetchPromotions();
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
        fetchCateringPackages();
        fetchCateringMenuItems();
        fetchBookSettings();
        fetchPromotions();
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
      is_available: formData.is_available,
      no_onion_garlic: formData.no_onion_garlic,
      fasting_friendly: formData.fasting_friendly
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
      is_available: item.is_available,
      no_onion_garlic: item.no_onion_garlic || false,
      fasting_friendly: item.fasting_friendly || false
    });
    setDialogOpen(true);
  };

  const resetForm = () => {
    setEditingItem(null);
    setFormData({
      name: '', description: '', category: '',
      price_inr: '', price_aud: '', image_url: '',
      is_veg: true, is_available: true,
      no_onion_garlic: false, fasting_friendly: false
    });
  };

  // Bulk Image Upload Functions
  const itemsWithoutImages = useMemo(() => {
    return menuItems.filter(item => !item.image_url);
  }, [menuItems]);

  const initBulkImageMode = () => {
    const initialData = {};
    itemsWithoutImages.forEach(item => {
      initialData[item.id] = '';
    });
    setBulkImageData(initialData);
    setBulkImageMode(true);
  };

  const handleBulkImageChange = (itemId, imageUrl) => {
    setBulkImageData(prev => ({
      ...prev,
      [itemId]: imageUrl
    }));
  };

  const handleBulkImageSave = async () => {
    const currentToken = getToken();
    const itemsToUpdate = Object.entries(bulkImageData).filter(([_, url]) => url.trim() !== '');
    
    if (itemsToUpdate.length === 0) {
      toast.error('No images to save. Please paste at least one image URL.');
      return;
    }

    setBulkSaving(true);
    let successCount = 0;
    let errorCount = 0;

    for (const [itemId, imageUrl] of itemsToUpdate) {
      const item = menuItems.find(m => m.id === itemId);
      if (!item) continue;

      try {
        await axios.put(
          `${API}/admin/menu/${itemId}`,
          {
            name: item.name,
            description: item.description,
            category: item.category,
            price_inr: item.price_inr,
            price_aud: item.price_aud,
            image_url: imageUrl.trim(),
            is_veg: item.is_veg,
            is_available: item.is_available,
            no_onion_garlic: item.no_onion_garlic || false,
            fasting_friendly: item.fasting_friendly || false
          },
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        successCount++;
      } catch (error) {
        console.error(`Failed to update ${item.name}:`, error);
        errorCount++;
      }
    }

    setBulkSaving(false);
    
    if (successCount > 0) {
      toast.success(`✅ Updated ${successCount} items with images!`);
      fetchMenuItems();
      setBulkImageMode(false);
      setBulkImageData({});
    }
    
    if (errorCount > 0) {
      toast.error(`❌ Failed to update ${errorCount} items`);
    }
  };

  // Bulk Nutrition Generation
  const handleBulkNutritionGenerate = async () => {
    if (!window.confirm('Generate AI nutrition data for all menu items? This may take a few minutes.')) return;
    setNutritionGenerating(true);
    setNutritionProgress(null);
    try {
      const res = await axios.post(`${API}/admin/nutrition/generate-bulk`, { force: false }, {
        headers: { Authorization: `Bearer ${getToken()}` }
      });
      setNutritionProgress(res.data);
      toast.success(`Nutrition generated for ${res.data.generated} items (${res.data.skipped} already had data)`);
    } catch (error) {
      toast.error('Failed to generate nutrition data');
    } finally {
      setNutritionGenerating(false);
    }
  };

  // Location CRUD
  const handleLocationSubmit = async (e) => {
    e.preventDefault();
    const currentToken = getToken();
    try {
      // Auto-derive center_id from name if not provided, and currency from country
      const payload = { ...locationForm };
      if (!payload.center_id) payload.center_id = slugifyCenterId(payload.name);
      const isAus = (payload.country || '').toLowerCase() === 'australia';
      if (!payload.currency) payload.currency = isAus ? 'AUD' : 'INR';
      if (!payload.currency_symbol) payload.currency_symbol = isAus ? '$' : '₹';
      if (!payload.display_name) payload.display_name = payload.name;
      if (!payload.services || payload.services.length === 0) {
        payload.services = ['dine-in', 'pickup', 'tiffin', 'catering', 'unlimited-breakfast'];
      }

      if (editingLocation) {
        await axios.put(
          `${API}/admin/locations/${editingLocation.id}`,
          payload,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Location updated');
      } else {
        await axios.post(
          `${API}/admin/locations`,
          payload,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Location added — time slots will use defaults until configured');
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
      phone: '', whatsapp: '', google_review_link: '', is_active: true,
      center_id: '', display_name: '', state: '',
      currency: 'INR', currency_symbol: '₹',
      services: ['dine-in', 'pickup', 'tiffin', 'catering', 'unlimited-breakfast']
    });
  };

  const handleDeleteLocation = async (loc) => {
    if (!window.confirm(`Delete location "${loc.name}"? This cannot be undone. The center will disappear from Table Booking and its time slots will be removed.`)) return;
    const currentToken = getToken();
    try {
      await axios.delete(`${API}/admin/locations/${loc.id}`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      toast.success(`Deleted ${loc.name}`);
      fetchLocations();
    } catch {
      toast.error('Failed to delete location');
    }
  };

  // Auto-generate center_id slug from name (e.g. "PB-Mysore" -> "pb-mysore")
  const slugifyCenterId = (name) => {
    if (!name) return '';
    return name.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
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

  // ===================== CATERING CRUD FUNCTIONS =====================
  
  const fetchCateringPackages = async () => {
    const currentToken = getToken();
    if (!currentToken) return;
    try {
      const response = await axios.get(`${API}/admin/catering-packages`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      setCateringPackages(response.data);
    } catch (error) {
      console.error('Failed to fetch catering packages:', error);
    }
  };

  const fetchCateringMenuItems = async () => {
    const currentToken = getToken();
    if (!currentToken) return;
    try {
      const response = await axios.get(`${API}/admin/catering-menu`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      setCateringMenuItems(response.data);
    } catch (error) {
      console.error('Failed to fetch catering menu items:', error);
    }
  };

  const handleCateringPackageSubmit = async (e) => {
    e.preventDefault();
    const currentToken = getToken();
    try {
      const payload = {
        ...cateringPackageForm,
        price_per_person_inr: parseFloat(cateringPackageForm.price_per_person_inr) || 0,
        price_per_person_aud: parseFloat(cateringPackageForm.price_per_person_aud) || 0
      };
      
      if (editingCateringPackage) {
        await axios.put(
          `${API}/admin/catering-packages/${editingCateringPackage.id}`,
          payload,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Package updated!');
      } else {
        await axios.post(
          `${API}/admin/catering-packages`,
          payload,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Package created!');
      }
      setCateringPackageDialogOpen(false);
      resetCateringPackageForm();
      fetchCateringPackages();
    } catch (error) {
      toast.error('Operation failed');
    }
  };

  const handleDeleteCateringPackage = async (id) => {
    if (!window.confirm('Delete this package?')) return;
    const currentToken = getToken();
    try {
      await axios.delete(`${API}/admin/catering-packages/${id}`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      toast.success('Package deleted');
      fetchCateringPackages();
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  const resetCateringPackageForm = () => {
    setEditingCateringPackage(null);
    setCateringPackageForm({
      name: '',
      description: '',
      price_per_person_inr: '',
      price_per_person_aud: '',
      is_popular: false,
      requirements: { starters: 0, mains: 0, special: 0, roti: 0, rice: 0, side: 0, dessert: 0, drink: 0, chutney: 0 },
      is_active: true,
      display_order: 0
    });
  };

  const handleCateringItemSubmit = async (e) => {
    e.preventDefault();
    const currentToken = getToken();
    try {
      if (editingCateringItem) {
        await axios.put(
          `${API}/admin/catering-menu/${editingCateringItem.id}`,
          cateringItemForm,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Item updated!');
      } else {
        await axios.post(
          `${API}/admin/catering-menu`,
          cateringItemForm,
          { headers: { Authorization: `Bearer ${currentToken}` } }
        );
        toast.success('Item created!');
      }
      setCateringItemDialogOpen(false);
      resetCateringItemForm();
      fetchCateringMenuItems();
    } catch (error) {
      toast.error('Operation failed');
    }
  };

  const handleDeleteCateringItem = async (id) => {
    if (!window.confirm('Delete this item?')) return;
    const currentToken = getToken();
    try {
      await axios.delete(`${API}/admin/catering-menu/${id}`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      toast.success('Item deleted');
      fetchCateringMenuItems();
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  const resetCateringItemForm = () => {
    setEditingCateringItem(null);
    setCateringItemForm({
      name: '',
      description: '',
      category: 'starters',
      image_url: '',
      is_veg: true,
      is_available: true
    });
  };

  const handleSeedCateringData = async () => {
    const currentToken = getToken();
    try {
      const response = await axios.post(
        `${API}/admin/catering-seed`,
        {},
        { headers: { Authorization: `Bearer ${currentToken}` } }
      );
      toast.success(response.data.message);
      fetchCateringPackages();
      fetchCateringMenuItems();
    } catch (error) {
      toast.error('Failed to seed data');
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

  // Book Settings functions
  const fetchBookSettings = async () => {
    try {
      const res = await axios.get(`${API}/book/settings`);
      setBookSettings(res.data);
      const currentToken = getToken();
      if (currentToken) {
        const analytics = await axios.get(`${API}/admin/book/analytics`, {
          headers: { Authorization: `Bearer ${currentToken}` }
        });
        setBookAnalytics(analytics.data);
        const upi = await axios.get(`${API}/admin/upi-payments`, {
          headers: { Authorization: `Bearer ${currentToken}` }
        });
        setUpiPayments(upi.data || []);
        const slots = await axios.get(`${API}/admin/center-timeslots`, {
          headers: { Authorization: `Bearer ${currentToken}` }
        });
        const slotsMap = {};
        (slots.data || []).forEach(c => { slotsMap[c.center_id] = c.slots; });
        setCenterSlots(slotsMap);
      }
    } catch {}
  };

  const approveUpi = async (paymentId) => {
    const currentToken = getToken();
    try {
      await axios.post(`${API}/admin/upi-approve/${paymentId}`, {}, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      toast.success('Payment approved! Access granted.');
      fetchBookSettings();
    } catch { toast.error('Failed to approve'); }
  };

  const rejectUpi = async (paymentId) => {
    const currentToken = getToken();
    try {
      await axios.post(`${API}/admin/upi-reject/${paymentId}`, {}, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      toast.success('Payment rejected.');
      fetchBookSettings();
    } catch { toast.error('Failed to reject'); }
  };

  const saveCenterSlots = async (centerId) => {
    const currentToken = getToken();
    try {
      await axios.put(`${API}/admin/center-timeslots/${centerId}`, { slots: slotsForm }, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      toast.success(`Time slots saved for ${centerId}`);
      setEditingSlots(null);
      fetchBookSettings();
    } catch { toast.error('Failed to save'); }
  };

  const addSlotRow = () => {
    const id = `slot-${Date.now()}`;
    setSlotsForm(prev => [...prev, { id, label: '', start: '', end: '' }]);
  };

  const removeSlotRow = (idx) => {
    setSlotsForm(prev => prev.filter((_, i) => i !== idx));
  };

  const updateSlotRow = (idx, field, value) => {
    setSlotsForm(prev => prev.map((s, i) => {
      if (i !== idx) return s;
      const updated = { ...s, [field]: value };
      if (field === 'start' || field === 'end') {
        // Auto-generate label from start/end
        if (updated.start && updated.end) {
          const fmt = (t) => { const [h, m] = t.split(':'); const hr = parseInt(h); return `${hr > 12 ? hr - 12 : hr}:${m} ${hr >= 12 ? 'PM' : 'AM'}`; };
          updated.label = `${fmt(updated.start)} – ${fmt(updated.end)}`;
        }
      }
      return updated;
    }));
  };

  const startEditingSlots = (centerId) => {
    setEditingSlots(centerId);
    setSlotsForm(centerSlots[centerId] || [
      { id: 'slot-1', label: '12:00 PM – 1:00 PM', start: '12:00', end: '13:00' },
      { id: 'slot-2', label: '1:00 PM – 2:00 PM', start: '13:00', end: '14:00' },
      { id: 'slot-3', label: '7:00 PM – 8:00 PM', start: '19:00', end: '20:00' },
    ]);
  };

  // Promotions
  const fetchPromotions = async () => {
    try {
      const res = await axios.get(`${API}/promotions`);
      setPromotions(res.data);
    } catch {}
  };
  const updatePromoField = (key, field, value) => {
    setPromotions(prev => ({ ...prev, [key]: { ...prev[key], [field]: value } }));
  };
  const togglePromoRegion = (key, region) => {
    setPromotions(prev => {
      const cur = prev[key].regions || [];
      const next = cur.includes(region) ? cur.filter(r => r !== region) : [...cur, region];
      return { ...prev, [key]: { ...prev[key], regions: next } };
    });
  };
  const savePromotions = async () => {
    if (!promotions) return;
    setPromoSaving(true);
    const currentToken = getToken();
    try {
      await axios.put(`${API}/admin/promotions`, promotions, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      toast.success('Promotions saved — live for customers');
    } catch {
      toast.error('Failed to save promotions');
    } finally {
      setPromoSaving(false);
    }
  };

  const saveBookSettings = async () => {
    const currentToken = getToken();
    try {
      await axios.put(`${API}/admin/book/settings`, bookSettings, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      toast.success('Book settings saved!');
    } catch { toast.error('Failed to save settings'); }
  };

  const handleMusicUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) { toast.error('Max 10MB'); return; }
    setMusicUploading(true);
    const reader = new FileReader();
    reader.onload = async () => {
      const base64 = reader.result.split(',')[1];
      const currentToken = getToken();
      try {
        await axios.post(`${API}/admin/book/upload-music`, {
          audio_base64: base64,
          filename: file.name
        }, { headers: { Authorization: `Bearer ${currentToken}` } });
        toast.success('Music uploaded!');
      } catch { toast.error('Upload failed'); }
      setMusicUploading(false);
    };
    reader.readAsDataURL(file);
  };

  const addShayari = () => {
    if (!newShayari.trim()) return;
    setBookSettings(prev => ({
      ...prev,
      break_shayaris: [...(prev.break_shayaris || []), newShayari.trim()]
    }));
    setNewShayari('');
  };

  const removeShayari = (idx) => {
    setBookSettings(prev => ({
      ...prev,
      break_shayaris: prev.break_shayaris.filter((_, i) => i !== idx)
    }));
  };

  const handleFestivalSubmit = async (e) => {
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
      <div className="min-h-screen bg-[#FDFBF7] flex items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          <Card className="pearl-surface border-[#E8DFD0] rounded-none">
            <CardHeader className="text-center">
              <div className="mx-auto w-16 h-16 bg-[#B8962E]/10 rounded-full flex items-center justify-center mb-4 border border-[#B8962E]/20">
                <Lock className="h-8 w-8 text-[#B8962E]" />
              </div>
              <CardTitle className="font-heading text-2xl text-[#2D1810]">Admin Login</CardTitle>
              <p className="text-sm text-[#5C4A3A] font-body">
                Enter your credentials to access the admin panel
              </p>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <Label htmlFor="email" className="text-[#5C4A3A]">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={loginForm.email}
                    onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                    placeholder="admin@purnabramha.com"
                    required
                    className="rounded-none border-[#E8DFD0] focus-visible:ring-[#B8962E]"
                    data-testid="admin-email-input"
                  />
                </div>
                <div>
                  <Label htmlFor="password" className="text-[#5C4A3A]">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={loginForm.password}
                    onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                    placeholder="Enter password"
                    required
                    className="rounded-none border-[#E8DFD0] focus-visible:ring-[#B8962E]"
                    data-testid="admin-password-input"
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full rounded-none gold-glossy text-[#3D2314] font-bold"
                  disabled={loginLoading}
                  data-testid="admin-login-btn"
                >
                  <LogIn className="mr-2 h-4 w-4" />
                  {loginLoading ? 'Logging in...' : 'Login'}
                </Button>
              </form>
              <div className="mt-4 p-3 bg-[#F8F5F0] border border-[#E8DFD0] rounded-none">
                <p className="text-xs text-[#5C4A3A] font-body">
                  <strong className="text-[#2D1810]">Admin Credentials:</strong><br />
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
    <div className="min-h-screen bg-[#FDFBF7]">
      <div className="container mx-auto px-4 lg:px-8 py-8 lg:py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 flex items-center justify-between"
        >
          <div>
            <h1 className="font-heading text-3xl lg:text-4xl font-medium text-[#2D1810] mb-2">
              Admin Dashboard
            </h1>
            <p className="text-[#5C4A3A] font-body">
              Manage your restaurant menu, locations, and content
            </p>
          </div>
          <Button variant="outline" onClick={handleLogout} className="flex items-center gap-2 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] hover:border-[#B8962E]/30 rounded-none">
            <LogOut className="h-4 w-4" />
            Logout
          </Button>
        </motion.div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6 bg-white border border-[#E8DFD0] p-1 rounded-none flex flex-wrap gap-1 h-auto">
            <TabsTrigger value="banner" className="flex items-center gap-2 data-[state=active]:bg-[#B8962E] data-[state=active]:text-white rounded-none text-xs lg:text-sm px-2 lg:px-3">
              <Home className="h-4 w-4" />
              <span className="hidden sm:inline">Home Banner</span>
              <span className="sm:hidden">Banner</span>
            </TabsTrigger>
            <TabsTrigger value="festival" className="flex items-center gap-2 data-[state=active]:bg-[#B8962E] data-[state=active]:text-white rounded-none text-xs lg:text-sm px-2 lg:px-3">
              <Sparkles className="h-4 w-4" />
              Festivals
            </TabsTrigger>
            <TabsTrigger value="menu" className="flex items-center gap-2 data-[state=active]:bg-[#B8962E] data-[state=active]:text-white rounded-none text-xs lg:text-sm px-2 lg:px-3">
              <UtensilsCrossed className="h-4 w-4" />
              Menu ({menuItems.length})
            </TabsTrigger>
            <TabsTrigger value="tiffin" className="flex items-center gap-2 data-[state=active]:bg-[#B8962E] data-[state=active]:text-white rounded-none text-xs lg:text-sm px-2 lg:px-3" data-testid="tiffin-admin-tab">
              <UtensilsCrossed className="h-4 w-4" />
              Tiffin ({tiffinItems.length})
            </TabsTrigger>
            <TabsTrigger value="catering" className="flex items-center gap-2 data-[state=active]:bg-[#B8962E] data-[state=active]:text-white rounded-none text-xs lg:text-sm px-2 lg:px-3" data-testid="catering-admin-tab">
              <UtensilsCrossed className="h-4 w-4" />
              Catering ({cateringPackages.length})
            </TabsTrigger>
            <TabsTrigger value="locations" className="flex items-center gap-2 data-[state=active]:bg-[#B8962E] data-[state=active]:text-white rounded-none text-xs lg:text-sm px-2 lg:px-3" data-testid="locations-admin-tab">
              <MapPin className="h-4 w-4" />
              Locations ({locations.length})
            </TabsTrigger>
            <TabsTrigger value="videos" className="flex items-center gap-2 data-[state=active]:bg-[#B8962E] data-[state=active]:text-white rounded-none text-xs lg:text-sm px-2 lg:px-3">
              <Video className="h-4 w-4" />
              Videos ({videos.length})
            </TabsTrigger>
            <TabsTrigger value="book" className="flex items-center gap-2 data-[state=active]:bg-[#B8962E] data-[state=active]:text-white rounded-none text-xs lg:text-sm px-2 lg:px-3" data-testid="book-admin-tab">
              <BookOpen className="h-4 w-4" />
              Book
            </TabsTrigger>
            <TabsTrigger value="promotions" className="flex items-center gap-2 data-[state=active]:bg-[#B8962E] data-[state=active]:text-white rounded-none text-xs lg:text-sm px-2 lg:px-3" data-testid="promotions-admin-tab">
              <Sparkles className="h-4 w-4" />
              Promotions
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
              {itemsWithoutImages.length > 0 && !bulkImageMode && (
                <Button
                  onClick={initBulkImageMode}
                  variant="outline"
                  className="border-amber-500 text-amber-700 hover:bg-amber-50"
                >
                  <ImageIcon className="mr-2 h-4 w-4" />
                  Bulk Add Images ({itemsWithoutImages.length})
                </Button>
              )}
              <Button
                onClick={handleBulkNutritionGenerate}
                variant="outline"
                disabled={nutritionGenerating}
                className="border-green-500 text-green-700 hover:bg-green-50"
                data-testid="generate-nutrition-btn"
              >
                {nutritionGenerating ? (
                  <><span className="animate-spin mr-2">&#9881;</span>Generating...</>
                ) : (
                  <><span className="mr-2">&#9889;</span>Generate Nutrition AI</>
                )}
              </Button>
            </div>

            {/* Bulk Image Upload Panel */}
            {bulkImageMode && (
              <Card className="mb-6 border-2 border-amber-400 bg-amber-50">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <ImageIcon className="h-5 w-5 text-amber-600" />
                      Bulk Image Upload - {itemsWithoutImages.length} items need images
                    </CardTitle>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => { setBulkImageMode(false); setBulkImageData({}); }}
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        onClick={handleBulkImageSave}
                        disabled={bulkSaving}
                        className="bg-amber-600 hover:bg-amber-700"
                      >
                        {bulkSaving ? 'Saving...' : 'Save All Images'}
                      </Button>
                    </div>
                  </div>
                  <p className="text-sm text-amber-700 mt-1">
                    Paste Google Drive URLs below. Format: <code className="bg-amber-100 px-1 rounded">https://lh3.googleusercontent.com/d/FILE_ID</code>
                  </p>
                </CardHeader>
                <CardContent className="max-h-[500px] overflow-y-auto">
                  <div className="space-y-2">
                    {itemsWithoutImages.map(item => (
                      <div key={item.id} className="flex items-center gap-3 p-2 bg-white rounded-lg border">
                        <div className="w-10 h-10 rounded bg-gray-100 flex items-center justify-center flex-shrink-0">
                          {bulkImageData[item.id] ? (
                            <img 
                              src={bulkImageData[item.id]} 
                              alt="" 
                              className="w-10 h-10 object-cover rounded"
                              onError={(e) => { e.target.style.display = 'none'; }}
                            />
                          ) : (
                            <ImageIcon className="h-4 w-4 text-gray-400" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">{item.name}</p>
                          <p className="text-xs text-gray-500">{item.category}</p>
                        </div>
                        <Input
                          placeholder="Paste image URL..."
                          value={bulkImageData[item.id] || ''}
                          onChange={(e) => handleBulkImageChange(item.id, e.target.value)}
                          className="flex-1 max-w-md text-sm"
                        />
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

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
                            <div className="flex flex-wrap gap-1">
                              <Badge variant={item.is_available ? 'default' : 'secondary'} className="text-xs">
                                {item.is_available ? 'Active' : 'Inactive'}
                              </Badge>
                              {item.no_onion_garlic && (
                                <Badge className="text-xs bg-orange-500 hover:bg-orange-600">No Onion/Garlic</Badge>
                              )}
                              {item.fasting_friendly && (
                                <Badge className="text-xs bg-purple-500 hover:bg-purple-600">Fasting</Badge>
                              )}
                            </div>
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

          {/* CATERING TAB */}
          <TabsContent value="catering">
            <div className="space-y-6">
              {/* Seed Data Button */}
              {cateringPackages.length === 0 && cateringMenuItems.length === 0 && (
                <Card className="border-amber-200 bg-amber-50">
                  <CardContent className="p-6 text-center">
                    <p className="text-sm text-amber-800 mb-4">
                      No catering data found. Would you like to import from the default configuration?
                    </p>
                    <Button onClick={handleSeedCateringData} className="bg-amber-600 hover:bg-amber-700">
                      Import Default Catering Menu
                    </Button>
                  </CardContent>
                </Card>
              )}

              {/* Catering Packages */}
              <div className="flex justify-between items-center">
                <h2 className="font-heading text-xl font-semibold text-[#2D1810]">Catering Packages</h2>
                <Button
                  onClick={() => { resetCateringPackageForm(); setCateringPackageDialogOpen(true); }}
                  className="gold-glossy text-[#3D2314] font-bold rounded-none"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add Package
                </Button>
              </div>

              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {cateringPackages.map(pkg => (
                  <Card key={pkg.id} className="pearl-surface border-[#E8DFD0] rounded-none">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg flex items-center justify-between font-heading text-[#2D1810]">
                        {pkg.name}
                        {pkg.is_popular && <Badge className="bg-[#B8962E] text-white">Popular</Badge>}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm">
                      <p className="text-[#5C4A3A] mb-2">{pkg.description}</p>
                      <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                        <div className="bg-[#F8F5F0] p-2 rounded-none">
                          <span className="text-[#7A6F65]">₹ INR</span>
                          <p className="font-semibold text-[#B8962E]">₹{pkg.price_per_person_inr}/person</p>
                        </div>
                        <div className="bg-[#F8F5F0] p-2 rounded-none">
                          <span className="text-[#7A6F65]">$ AUD</span>
                          <p className="font-semibold text-[#B8962E]">${pkg.price_per_person_aud}/person</p>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1 border-[#E8DFD0] text-[#5C4A3A] hover:border-[#B8962E] rounded-none"
                          onClick={() => {
                            setEditingCateringPackage(pkg);
                            setCateringPackageForm({
                              ...pkg,
                              price_per_person_inr: pkg.price_per_person_inr?.toString() || '',
                              price_per_person_aud: pkg.price_per_person_aud?.toString() || ''
                            });
                            setCateringPackageDialogOpen(true);
                          }}
                        >
                          <Edit className="h-4 w-4 mr-1" /> Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-500 hover:text-red-700 rounded-none"
                          onClick={() => handleDeleteCateringPackage(pkg.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* Catering Menu Items */}
              <div className="flex justify-between items-center mt-8">
                <h2 className="font-heading text-xl font-semibold text-[#2D1810]">Catering Menu Items</h2>
                <Button
                  onClick={() => { resetCateringItemForm(); setCateringItemDialogOpen(true); }}
                  className="gold-glossy text-[#3D2314] font-bold rounded-none"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add Menu Item
                </Button>
              </div>

              {cateringCategories.map(cat => {
                const items = cateringMenuItems.filter(i => i.category === cat.id);
                return (
                  <Card key={cat.id} className="pearl-surface border-[#E8DFD0] rounded-none">
                    <CardHeader className="pb-2 bg-[#F8F5F0] border-b border-[#E8DFD0]">
                      <CardTitle className="text-lg font-heading text-[#2D1810]">{cat.label} ({items.length})</CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4">
                      {items.length === 0 ? (
                        <p className="text-sm text-[#7A6F65]">No items yet. Click "Add Menu Item" to add.</p>
                      ) : (
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="text-[#5C4A3A]">Image</TableHead>
                              <TableHead className="text-[#5C4A3A]">Name</TableHead>
                              <TableHead className="text-[#5C4A3A]">Description</TableHead>
                              <TableHead className="text-[#5C4A3A]">Status</TableHead>
                              <TableHead className="text-[#5C4A3A]">Actions</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {items.map(item => (
                              <TableRow key={item.id}>
                                <TableCell>
                                  {item.image_url ? (
                                    <img src={item.image_url} alt={item.name} className="w-10 h-10 object-cover rounded-none border border-[#E8DFD0]" />
                                  ) : (
                                    <div className="w-10 h-10 bg-[#F8F5F0] rounded-none flex items-center justify-center border border-[#E8DFD0]">
                                      <ImageIcon className="h-5 w-5 text-[#B8962E]/50" />
                                    </div>
                                  )}
                                </TableCell>
                                <TableCell className="font-medium text-[#2D1810]">{item.name}</TableCell>
                                <TableCell className="text-[#5C4A3A] max-w-xs truncate">{item.description || '-'}</TableCell>
                                <TableCell>
                                  <Badge variant={item.is_available ? 'default' : 'secondary'} className={item.is_available ? 'bg-green-100 text-green-800' : ''}>
                                    {item.is_available ? 'Active' : 'Inactive'}
                                  </Badge>
                                </TableCell>
                                <TableCell>
                                  <div className="flex gap-1">
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      onClick={() => {
                                        setEditingCateringItem(item);
                                        setCateringItemForm(item);
                                        setCateringItemDialogOpen(true);
                                      }}
                                    >
                                      <Edit className="h-4 w-4 text-[#5C4A3A]" />
                                    </Button>
                                    <Button variant="ghost" size="icon" onClick={() => handleDeleteCateringItem(item.id)} className="text-red-500">
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
              <div>
                <h2 className="font-playfair text-xl font-semibold">Locations & Centers</h2>
                <p className="text-xs text-foreground/60 mt-1">Each location is a bookable center. Edit info or configure time slots inside each card.</p>
              </div>
              <Button
                onClick={() => { resetLocationForm(); setLocationDialogOpen(true); }}
                className="rounded-full bg-primary"
                data-testid="add-location-btn"
              >
                <Plus className="mr-2 h-4 w-4" />
                Add Location
              </Button>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {locations.map((loc) => {
                const centerId = loc.center_id || loc.id;
                const currentTab = activeLocationTab[loc.id] || 'info';
                const slotsCount = centerSlots[centerId]?.length;
                return (
                  <Card key={loc.id} className="border-[#E8DFD0] overflow-hidden" data-testid={`location-card-${centerId}`}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg flex items-center justify-between gap-2">
                        <span className="truncate">{loc.name}</span>
                        <Badge variant={loc.is_active ? 'default' : 'secondary'} className="shrink-0">
                          {loc.country}
                        </Badge>
                      </CardTitle>
                      {loc.center_id && (
                        <p className="text-[10px] text-[#B8962E] font-mono mt-1">{loc.center_id}</p>
                      )}
                    </CardHeader>
                    <CardContent className="text-sm">
                      {/* In-card tabs */}
                      <div className="flex border-b border-[#E8DFD0] mb-3 -mx-1">
                        <button
                          type="button"
                          onClick={() => setActiveLocationTab(p => ({ ...p, [loc.id]: 'info' }))}
                          className={`px-3 py-1.5 text-xs font-heading border-b-2 transition-colors ${currentTab === 'info' ? 'border-[#B8962E] text-[#B8962E]' : 'border-transparent text-foreground/60 hover:text-foreground/80'}`}
                          data-testid={`location-info-tab-${centerId}`}
                        >
                          <MapPin className="inline w-3 h-3 mr-1" /> Location Info
                        </button>
                        <button
                          type="button"
                          onClick={() => setActiveLocationTab(p => ({ ...p, [loc.id]: 'slots' }))}
                          className={`px-3 py-1.5 text-xs font-heading border-b-2 transition-colors ${currentTab === 'slots' ? 'border-[#B8962E] text-[#B8962E]' : 'border-transparent text-foreground/60 hover:text-foreground/80'}`}
                          data-testid={`location-slots-tab-${centerId}`}
                        >
                          <Clock className="inline w-3 h-3 mr-1" /> Time Slots
                          {slotsCount > 0 && <span className="ml-1 text-[9px] bg-[#B8962E]/15 text-[#B8962E] px-1.5 py-0.5 rounded-full">{slotsCount}</span>}
                        </button>
                      </div>

                      {/* Info Tab */}
                      {currentTab === 'info' && (
                        <div className="text-foreground/70 space-y-1">
                          <p>{loc.city}{loc.state ? `, ${loc.state}` : ''}</p>
                          <p className="truncate" title={loc.address}>{loc.address}</p>
                          <p className="mt-2">{loc.phone}</p>
                          {loc.currency && (
                            <p className="text-[10px] text-foreground/50">Currency: {loc.currency_symbol || ''} {loc.currency}</p>
                          )}
                          <div className="flex gap-2 mt-4">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setEditingLocation(loc);
                                setLocationForm({
                                  ...loc,
                                  services: loc.services || ['dine-in', 'pickup', 'tiffin', 'catering', 'unlimited-breakfast']
                                });
                                setLocationDialogOpen(true);
                              }}
                              data-testid={`edit-location-${centerId}`}
                            >
                              <Edit className="h-4 w-4 mr-1" /> Edit
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700"
                              onClick={() => handleDeleteLocation(loc)}
                              data-testid={`delete-location-${centerId}`}
                            >
                              <Trash2 className="h-4 w-4 mr-1" /> Delete
                            </Button>
                          </div>
                        </div>
                      )}

                      {/* Time Slots Tab */}
                      {currentTab === 'slots' && (
                        <div data-testid={`location-slots-pane-${centerId}`}>
                          {!loc.center_id && (
                            <div className="mb-3 p-2 bg-[#FFF5E6] border border-[#B8962E]/30 rounded text-[11px] text-[#7A6F65]">
                              ⚠ This location has no <strong>Center ID</strong>. Click "Edit" on the Info tab to add one before configuring slots.
                            </div>
                          )}
                          <p className="text-[11px] text-foreground/60 mb-3">
                            {slotsCount ? `${slotsCount} custom slot${slotsCount === 1 ? '' : 's'} configured` : 'Using default slots (12pm–3pm, 7pm–10pm)'}
                          </p>

                          {editingSlots !== centerId ? (
                            <Button
                              size="sm"
                              disabled={!loc.center_id}
                              onClick={() => startEditingSlots(centerId)}
                              className="text-xs bg-[#B8962E] text-white hover:bg-[#D4AF37] h-7 px-3 disabled:opacity-50"
                              data-testid={`edit-slots-${centerId}`}
                            >
                              <Edit className="w-3 h-3 mr-1" /> Edit Time Slots
                            </Button>
                          ) : (
                            <div className="space-y-2 border-t border-[#E8DFD0] pt-3">
                              {slotsForm.map((slot, idx) => (
                                <div key={slot.id} className="flex items-center gap-2">
                                  <Input type="time" value={slot.start} onChange={(e) => updateSlotRow(idx, 'start', e.target.value)} className="w-24 text-xs" />
                                  <span className="text-xs text-[#7A6F65]">–</span>
                                  <Input type="time" value={slot.end} onChange={(e) => updateSlotRow(idx, 'end', e.target.value)} className="w-24 text-xs" />
                                  <button onClick={() => removeSlotRow(idx)} className="text-red-400 hover:text-red-600 p-1 ml-auto" data-testid={`remove-slot-${centerId}-${idx}`}><Trash2 className="w-3.5 h-3.5" /></button>
                                </div>
                              ))}
                              {slotsForm.length > 0 && (
                                <p className="text-[10px] text-[#B8962E]/80 font-body italic">
                                  {slotsForm.map(s => s.label).filter(Boolean).join(' · ')}
                                </p>
                              )}
                              <div className="flex gap-2 pt-2 flex-wrap">
                                <Button size="sm" onClick={addSlotRow} variant="outline" className="text-xs h-7 px-3 border-[#E8DFD0]" data-testid={`add-slot-${centerId}`}>
                                  <Plus className="w-3 h-3 mr-1" /> Add
                                </Button>
                                <Button size="sm" onClick={() => saveCenterSlots(centerId)} className="text-xs h-7 px-3 bg-[#2E7D32] text-white hover:bg-[#388E3C]" data-testid={`save-slots-${centerId}`}>
                                  Save
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => setEditingSlots(null)} className="text-xs h-7 px-3 border-[#E8DFD0]" data-testid={`cancel-slots-${centerId}`}>
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
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

          {/* BOOK SETTINGS TAB */}
          <TabsContent value="book">
            <div className="space-y-6">
              {/* Analytics Cards */}
              {bookAnalytics && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <Card><CardContent className="p-4 text-center">
                    <p className="text-2xl font-heading text-[#B8962E]">{bookAnalytics.total_readers}</p>
                    <p className="text-xs text-[#7A6F65] font-body">Total Readers</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4 text-center">
                    <p className="text-2xl font-heading text-[#B8962E]">{bookAnalytics.total_purchases}</p>
                    <p className="text-xs text-[#7A6F65] font-body">Parts Purchased</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4 text-center">
                    <p className="text-2xl font-heading text-[#B8962E]">{bookAnalytics.total_bookmarks}</p>
                    <p className="text-xs text-[#7A6F65] font-body">Bookmarks</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4 text-center">
                    <p className="text-lg font-body text-[#5C4A3A]">P1: {bookAnalytics.part_stats?.part_1 || 0} | P2: {bookAnalytics.part_stats?.part_2 || 0} | P3: {bookAnalytics.part_stats?.part_3 || 0}</p>
                    <p className="text-xs text-[#7A6F65] font-body">Per Part Sales</p>
                  </CardContent></Card>
                </div>
              )}

              {/* UPI Payments Queue */}
              {upiPayments.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-lg">
                      <Smartphone className="h-5 w-5 text-[#B8962E]" /> UPI Payments
                      {upiPayments.filter(p => p.status === 'submitted').length > 0 && (
                        <span className="ml-2 bg-orange-500 text-white text-[10px] px-2 py-0.5 rounded-full font-body">
                          {upiPayments.filter(p => p.status === 'submitted').length} pending
                        </span>
                      )}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {upiPayments.map((p) => (
                        <div key={p.payment_id} className={`flex items-center justify-between p-3 rounded-lg border ${
                          p.status === 'submitted' ? 'border-orange-300 bg-orange-50' :
                          p.status === 'approved' ? 'border-green-300 bg-green-50' :
                          p.status === 'rejected' ? 'border-red-300 bg-red-50' :
                          'border-[#E8DFD0] bg-[#F8F5F0]'
                        }`}>
                          <div>
                            <p className="text-sm font-body font-semibold text-[#3D2314]">{p.email}</p>
                            <p className="text-[10px] text-[#7A6F65] font-body">
                              {p.description} — ₹{p.amount} — ID: {p.payment_id}
                              {p.upi_ref && ` — Ref: ${p.upi_ref}`}
                            </p>
                            <p className="text-[10px] text-[#7A6F65]/60 font-body">{p.created_at?.split('T')[0]}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            {p.status === 'submitted' && (
                              <>
                                <Button size="sm" onClick={() => approveUpi(p.payment_id)} className="bg-green-600 text-white text-[10px] h-7 px-3 hover:bg-green-700" data-testid={`approve-${p.payment_id}`}>
                                  Approve
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => rejectUpi(p.payment_id)} className="text-red-600 border-red-300 text-[10px] h-7 px-3 hover:bg-red-50" data-testid={`reject-${p.payment_id}`}>
                                  Reject
                                </Button>
                              </>
                            )}
                            {p.status === 'approved' && <span className="text-xs text-green-600 font-body font-semibold">Approved</span>}
                            {p.status === 'rejected' && <span className="text-xs text-red-600 font-body font-semibold">Rejected</span>}
                            {p.status === 'pending' && <span className="text-xs text-[#7A6F65] font-body">Awaiting payment</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Listen Mode Toggle */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg"><Headphones className="h-5 w-5 text-[#B8962E]" /> Audio Listen Mode</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-[#7A6F65] font-body mb-3">Enable or disable the AI narration / listen feature for readers</p>
                  <div className="flex items-center gap-4">
                    <button
                      onClick={() => setBookSettings(prev => ({ ...prev, listen_enabled: true }))}
                      className={`px-6 py-2 rounded-lg text-sm font-body font-semibold transition-all ${
                        bookSettings.listen_enabled !== false
                          ? 'bg-green-600 text-white'
                          : 'bg-[#F8F5F0] text-[#5C4A3A] border border-[#E8DFD0] hover:border-green-400'
                      }`}
                      data-testid="listen-enabled-on"
                    >
                      ON — Readers can listen
                    </button>
                    <button
                      onClick={() => setBookSettings(prev => ({ ...prev, listen_enabled: false }))}
                      className={`px-6 py-2 rounded-lg text-sm font-body font-semibold transition-all ${
                        bookSettings.listen_enabled === false
                          ? 'bg-red-600 text-white'
                          : 'bg-[#F8F5F0] text-[#5C4A3A] border border-[#E8DFD0] hover:border-red-400'
                      }`}
                      data-testid="listen-enabled-off"
                    >
                      OFF — Disable listening
                    </button>
                  </div>
                </CardContent>
              </Card>

              {/* Break Interval Setting */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg"><Coffee className="h-5 w-5 text-[#B8962E]" /> Tea/Coffee Break Interval</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-[#7A6F65] font-body mb-3">Show break reminder after every X pages flipped</p>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      {[4, 10, 15, 20, 30].map(val => (
                        <button
                          key={val}
                          onClick={() => setBookSettings(prev => ({ ...prev, break_interval: val }))}
                          className={`px-4 py-2 rounded-lg text-sm font-body font-semibold transition-all ${
                            bookSettings.break_interval === val
                              ? 'bg-[#B8962E] text-white'
                              : 'bg-[#F8F5F0] text-[#5C4A3A] border border-[#E8DFD0] hover:border-[#B8962E]'
                          }`}
                          data-testid={`break-interval-${val}`}
                        >
                          {val} pages
                        </button>
                      ))}
                    </div>
                    <span className="text-xs text-[#7A6F65] font-body">or custom:</span>
                    <Input
                      type="number"
                      min={2}
                      max={50}
                      value={bookSettings.break_interval}
                      onChange={(e) => setBookSettings(prev => ({ ...prev, break_interval: parseInt(e.target.value) || 20 }))}
                      className="w-20"
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Music Upload */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg"><Music className="h-5 w-5 text-[#B8962E]" /> Background Music</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-[#7A6F65] font-body mb-3">Upload calm ambient music (MP3/WAV, max 10MB). Readers can toggle it ON/OFF.</p>
                  <div className="flex items-center gap-4">
                    <label className="cursor-pointer px-4 py-2 bg-[#3D2314] text-[#D4AF37] rounded-lg text-sm font-body font-semibold hover:bg-[#5A3520] transition-colors">
                      {musicUploading ? 'Uploading...' : 'Upload Music File'}
                      <input
                        type="file"
                        accept="audio/mp3,audio/wav,audio/mpeg,audio/*"
                        className="hidden"
                        onChange={handleMusicUpload}
                        disabled={musicUploading}
                        data-testid="music-upload-input"
                      />
                    </label>
                    <audio controls src={`${API}/book/ambient-music`} className="h-10" />
                  </div>
                </CardContent>
              </Card>

              {/* Shayari Management */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg"><Coffee className="h-5 w-5 text-[#B8962E]" /> Break Shayaris</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-[#7A6F65] font-body mb-3">Custom shayaris shown during tea/coffee breaks. Leave empty to use defaults.</p>

                  {/* Add new shayari */}
                  <div className="flex gap-2 mb-4">
                    <Textarea
                      value={newShayari}
                      onChange={(e) => setNewShayari(e.target.value)}
                      placeholder="Type a new shayari..."
                      className="flex-1 min-h-[60px]"
                      data-testid="new-shayari-input"
                    />
                    <Button onClick={addShayari} className="bg-[#B8962E] text-white hover:bg-[#D4AF37]" data-testid="add-shayari-btn">
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>

                  {/* Existing shayaris */}
                  <div className="space-y-2">
                    {(bookSettings.break_shayaris || []).map((s, i) => (
                      <div key={i} className="flex items-start gap-2 bg-[#F8F5F0] p-3 rounded-lg">
                        <p className="flex-1 text-sm font-body text-[#3D2314] italic whitespace-pre-wrap">{s}</p>
                        <button onClick={() => removeShayari(i)} className="text-red-400 hover:text-red-600 p-1">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                    {(!bookSettings.break_shayaris || bookSettings.break_shayaris.length === 0) && (
                      <p className="text-xs text-[#7A6F65]/60 italic font-body">No custom shayaris. Default ones will be shown.</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Save Button */}
              <Button
                onClick={saveBookSettings}
                className="w-full gold-glossy text-[#3D2314] font-bold rounded-none py-3 text-sm tracking-widest uppercase border-0"
                data-testid="save-book-settings"
              >
                Save Book Settings
              </Button>
            </div>
          </TabsContent>

          {/* PROMOTIONS TAB */}
          <TabsContent value="promotions">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h2 className="font-playfair text-xl font-semibold">Promotions & Discount Combos</h2>
                <p className="text-sm text-foreground/60 mt-1">Online-only auto-applied discounts. Customers see these on Pickup and Table Booking carts when conditions match.</p>
              </div>
              <Button
                onClick={savePromotions}
                disabled={promoSaving || !promotions}
                className="rounded-full bg-[#B8962E] text-white hover:bg-[#D4AF37]"
                data-testid="save-promotions-btn"
              >
                {promoSaving ? 'Saving...' : 'Save All Promotions'}
              </Button>
            </div>

            {!promotions ? (
              <p className="text-sm text-foreground/60 italic">Loading promotions…</p>
            ) : (
              <div className="grid gap-6 md:grid-cols-2">
                {/* Brunch Combo Card */}
                <Card className="border-[#E8DFD0]" data-testid="promo-brunch-card">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between text-lg">
                      <span className="flex items-center gap-2"><Coffee className="h-5 w-5 text-[#B8962E]" /> {promotions.brunch?.label || 'Brunch Combo'}</span>
                      <label className="flex items-center gap-2 cursor-pointer text-xs">
                        <input
                          type="checkbox"
                          checked={!!promotions.brunch?.enabled}
                          onChange={(e) => updatePromoField('brunch', 'enabled', e.target.checked)}
                          data-testid="promo-brunch-enabled"
                          className="w-4 h-4 accent-[#2E7D32]"
                        />
                        <span className={promotions.brunch?.enabled ? 'text-green-700' : 'text-foreground/50'}>
                          {promotions.brunch?.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </label>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-xs text-foreground/60 italic">{promotions.brunch?.description}</p>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs">Start Time</Label>
                        <Input type="time" value={promotions.brunch?.start_time || ''} onChange={(e) => updatePromoField('brunch', 'start_time', e.target.value)} data-testid="promo-brunch-start" />
                      </div>
                      <div>
                        <Label className="text-xs">End Time</Label>
                        <Input type="time" value={promotions.brunch?.end_time || ''} onChange={(e) => updatePromoField('brunch', 'end_time', e.target.value)} data-testid="promo-brunch-end" />
                      </div>
                    </div>

                    <div>
                      <Label className="text-xs">Discount %</Label>
                      <Input type="number" min="0" max="100" value={promotions.brunch?.discount_pct || 0} onChange={(e) => updatePromoField('brunch', 'discount_pct', parseInt(e.target.value || '0'))} data-testid="promo-brunch-pct" />
                    </div>

                    <div>
                      <Label className="text-xs">Eligible Regions</Label>
                      <div className="flex gap-2 mt-1">
                        {['India', 'Australia'].map(r => (
                          <label key={r} className="flex items-center gap-1.5 cursor-pointer text-xs px-2 py-1 border border-[#E8DFD0] rounded">
                            <input type="checkbox" checked={(promotions.brunch?.regions || []).includes(r)} onChange={() => togglePromoRegion('brunch', r)} data-testid={`promo-brunch-region-${r}`} className="w-3.5 h-3.5 accent-[#B8962E]" />
                            <span>{r}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div>
                      <Label className="text-xs">Combo Categories (comma-separated)</Label>
                      <Input value={(promotions.brunch?.combo_categories || []).join(', ')} onChange={(e) => updatePromoField('brunch', 'combo_categories', e.target.value.split(',').map(s => s.trim()).filter(Boolean))} placeholder="Heavy Brunch, Bhakar Combo" data-testid="promo-brunch-combo-cats" />
                      <p className="text-[10px] text-foreground/50 mt-1">Cart needs ≥{promotions.brunch?.min_combo_qty || 1} item from these</p>
                    </div>

                    <div>
                      <Label className="text-xs">Drink Categories (comma-separated)</Label>
                      <Input value={(promotions.brunch?.drink_categories || []).join(', ')} onChange={(e) => updatePromoField('brunch', 'drink_categories', e.target.value.split(',').map(s => s.trim()).filter(Boolean))} placeholder="Tea & Coffee, Drinks" data-testid="promo-brunch-drink-cats" />
                      <p className="text-[10px] text-foreground/50 mt-1">+ ≥{promotions.brunch?.min_drink_qty || 1} drink from these</p>
                    </div>
                  </CardContent>
                </Card>

                {/* Evening Snack Combo Card */}
                <Card className="border-[#E8DFD0]" data-testid="promo-evening-snack-card">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between text-lg">
                      <span className="flex items-center gap-2"><Coffee className="h-5 w-5 text-[#B8962E]" /> {promotions.evening_snack?.label || 'Evening Snack Combo'}</span>
                      <label className="flex items-center gap-2 cursor-pointer text-xs">
                        <input
                          type="checkbox"
                          checked={!!promotions.evening_snack?.enabled}
                          onChange={(e) => updatePromoField('evening_snack', 'enabled', e.target.checked)}
                          data-testid="promo-snack-enabled"
                          className="w-4 h-4 accent-[#2E7D32]"
                        />
                        <span className={promotions.evening_snack?.enabled ? 'text-green-700' : 'text-foreground/50'}>
                          {promotions.evening_snack?.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </label>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-xs text-foreground/60 italic">{promotions.evening_snack?.description}</p>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs">Start Time</Label>
                        <Input type="time" value={promotions.evening_snack?.start_time || ''} onChange={(e) => updatePromoField('evening_snack', 'start_time', e.target.value)} data-testid="promo-snack-start" />
                      </div>
                      <div>
                        <Label className="text-xs">End Time</Label>
                        <Input type="time" value={promotions.evening_snack?.end_time || ''} onChange={(e) => updatePromoField('evening_snack', 'end_time', e.target.value)} data-testid="promo-snack-end" />
                      </div>
                    </div>

                    <div>
                      <Label className="text-xs">Discount %</Label>
                      <Input type="number" min="0" max="100" value={promotions.evening_snack?.discount_pct || 0} onChange={(e) => updatePromoField('evening_snack', 'discount_pct', parseInt(e.target.value || '0'))} data-testid="promo-snack-pct" />
                    </div>

                    <div>
                      <Label className="text-xs">Eligible Regions</Label>
                      <div className="flex gap-2 mt-1">
                        {['India', 'Australia'].map(r => (
                          <label key={r} className="flex items-center gap-1.5 cursor-pointer text-xs px-2 py-1 border border-[#E8DFD0] rounded">
                            <input type="checkbox" checked={(promotions.evening_snack?.regions || []).includes(r)} onChange={() => togglePromoRegion('evening_snack', r)} data-testid={`promo-snack-region-${r}`} className="w-3.5 h-3.5 accent-[#B8962E]" />
                            <span>{r}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div>
                      <Label className="text-xs">Snack Categories (comma-separated)</Label>
                      <Input value={(promotions.evening_snack?.snack_categories || []).join(', ')} onChange={(e) => updatePromoField('evening_snack', 'snack_categories', e.target.value.split(',').map(s => s.trim()).filter(Boolean))} placeholder="Snacks" data-testid="promo-snack-cats" />
                      <p className="text-[10px] text-foreground/50 mt-1">Cart needs ≥{promotions.evening_snack?.min_snack_qty || 1} item from these</p>
                    </div>

                    <div>
                      <Label className="text-xs">Tea Match Keyword</Label>
                      <Input value={promotions.evening_snack?.tea_keyword || ''} onChange={(e) => updatePromoField('evening_snack', 'tea_keyword', e.target.value)} placeholder="masala" data-testid="promo-snack-tea-keyword" />
                      <p className="text-[10px] text-foreground/50 mt-1">+ ≥{promotions.evening_snack?.min_tea_qty || 1} item whose name contains this keyword (e.g. "masala" matches "Masala Tea")</p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>
        </Tabs>
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
              <div className="flex flex-wrap items-center gap-4">
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
                <label className="flex items-center gap-2 cursor-pointer" data-testid="no-onion-garlic-checkbox">
                  <input
                    type="checkbox"
                    checked={formData.no_onion_garlic}
                    onChange={(e) => setFormData({ ...formData, no_onion_garlic: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm font-medium text-orange-700">No Onion/Garlic</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer" data-testid="fasting-friendly-checkbox">
                  <input
                    type="checkbox"
                    checked={formData.fasting_friendly}
                    onChange={(e) => setFormData({ ...formData, fasting_friendly: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm font-medium text-purple-700">Fasting Friendly</span>
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
                    data-testid="location-name-input"
                  />
                </div>
                <div>
                  <Label>City *</Label>
                  <Input
                    value={locationForm.city}
                    onChange={(e) => setLocationForm({ ...locationForm, city: e.target.value })}
                    required
                    data-testid="location-city-input"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Center ID (slug) *</Label>
                  <Input
                    value={locationForm.center_id || ''}
                    onChange={(e) => setLocationForm({ ...locationForm, center_id: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') })}
                    placeholder={locationForm.name ? slugifyCenterId(locationForm.name) : 'pb-newcity'}
                    data-testid="location-center-id-input"
                  />
                  <p className="text-[10px] text-foreground/60 mt-1">Used by Table Booking & Time Slots. Auto-generated if empty.</p>
                </div>
                <div>
                  <Label>State</Label>
                  <Input
                    value={locationForm.state || ''}
                    onChange={(e) => setLocationForm({ ...locationForm, state: e.target.value })}
                    placeholder="e.g. Maharashtra"
                    data-testid="location-state-input"
                  />
                </div>
              </div>
              <div>
                <Label>Country</Label>
                <Select
                  value={locationForm.country}
                  onValueChange={(value) => {
                    const isAus = value === 'Australia';
                    setLocationForm({
                      ...locationForm,
                      country: value,
                      currency: isAus ? 'AUD' : 'INR',
                      currency_symbol: isAus ? '$' : '₹'
                    });
                  }}
                >
                  <SelectTrigger data-testid="location-country-select">
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

        {/* Catering Package Dialog */}
        <Dialog open={cateringPackageDialogOpen} onOpenChange={setCateringPackageDialogOpen}>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="font-heading text-[#2D1810]">
                {editingCateringPackage ? 'Edit Package' : 'Add Catering Package'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCateringPackageSubmit} className="space-y-4">
              <div>
                <Label className="text-[#5C4A3A]">Package Name *</Label>
                <Input
                  value={cateringPackageForm.name}
                  onChange={(e) => setCateringPackageForm({ ...cateringPackageForm, name: e.target.value })}
                  placeholder="e.g., Classic, Premium"
                  required
                  className="border-[#E8DFD0] rounded-none"
                />
              </div>
              <div>
                <Label className="text-[#5C4A3A]">Description</Label>
                <Textarea
                  value={cateringPackageForm.description}
                  onChange={(e) => setCateringPackageForm({ ...cateringPackageForm, description: e.target.value })}
                  placeholder="Brief description"
                  rows={2}
                  className="border-[#E8DFD0] rounded-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-[#5C4A3A]">Price per Person (₹ INR)</Label>
                  <Input
                    type="number"
                    value={cateringPackageForm.price_per_person_inr}
                    onChange={(e) => setCateringPackageForm({ ...cateringPackageForm, price_per_person_inr: e.target.value })}
                    placeholder="e.g., 450"
                    className="border-[#E8DFD0] rounded-none"
                  />
                </div>
                <div>
                  <Label className="text-[#5C4A3A]">Price per Person ($ AUD)</Label>
                  <Input
                    type="number"
                    value={cateringPackageForm.price_per_person_aud}
                    onChange={(e) => setCateringPackageForm({ ...cateringPackageForm, price_per_person_aud: e.target.value })}
                    placeholder="e.g., 35"
                    className="border-[#E8DFD0] rounded-none"
                  />
                </div>
              </div>
              <div className="bg-[#F8F5F0] p-4 rounded-none border border-[#E8DFD0]">
                <Label className="text-[#5C4A3A] text-sm mb-2 block">Menu Requirements (items per category)</Label>
                <div className="grid grid-cols-3 gap-2">
                  {Object.keys(cateringPackageForm.requirements || {}).map(key => (
                    <div key={key}>
                      <Label className="text-xs text-[#7A6F65] capitalize">{key}</Label>
                      <Input
                        type="number"
                        min="0"
                        value={cateringPackageForm.requirements[key]}
                        onChange={(e) => setCateringPackageForm({
                          ...cateringPackageForm,
                          requirements: { ...cateringPackageForm.requirements, [key]: parseInt(e.target.value) || 0 }
                        })}
                        className="border-[#E8DFD0] rounded-none h-8 text-sm"
                      />
                    </div>
                  ))}
                </div>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={cateringPackageForm.is_popular}
                  onChange={(e) => setCateringPackageForm({ ...cateringPackageForm, is_popular: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm text-[#5C4A3A]">Mark as Popular</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={cateringPackageForm.is_active}
                  onChange={(e) => setCateringPackageForm({ ...cateringPackageForm, is_active: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm text-[#5C4A3A]">Active</span>
              </label>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setCateringPackageDialogOpen(false)} className="rounded-none">
                  Cancel
                </Button>
                <Button type="submit" className="gold-glossy text-[#3D2314] font-bold rounded-none">
                  {editingCateringPackage ? 'Update' : 'Add Package'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Catering Menu Item Dialog */}
        <Dialog open={cateringItemDialogOpen} onOpenChange={setCateringItemDialogOpen}>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="font-heading text-[#2D1810]">
                {editingCateringItem ? 'Edit Menu Item' : 'Add Catering Menu Item'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCateringItemSubmit} className="space-y-4">
              <div>
                <Label className="text-[#5C4A3A]">Item Name *</Label>
                <Input
                  value={cateringItemForm.name}
                  onChange={(e) => setCateringItemForm({ ...cateringItemForm, name: e.target.value })}
                  placeholder="e.g., Kothimbir Vadi"
                  required
                  className="border-[#E8DFD0] rounded-none"
                />
              </div>
              <div>
                <Label className="text-[#5C4A3A]">Description</Label>
                <Textarea
                  value={cateringItemForm.description}
                  onChange={(e) => setCateringItemForm({ ...cateringItemForm, description: e.target.value })}
                  placeholder="Brief description (optional)"
                  rows={2}
                  className="border-[#E8DFD0] rounded-none"
                />
              </div>
              <div>
                <Label className="text-[#5C4A3A]">Category *</Label>
                <Select
                  value={cateringItemForm.category}
                  onValueChange={(value) => setCateringItemForm({ ...cateringItemForm, category: value })}
                >
                  <SelectTrigger className="border-[#E8DFD0] rounded-none">
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {cateringCategories.map((cat) => (
                      <SelectItem key={cat.id} value={cat.id}>{cat.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-[#5C4A3A]">Image URL (optional)</Label>
                <Input
                  type="url"
                  value={cateringItemForm.image_url}
                  onChange={(e) => setCateringItemForm({ ...cateringItemForm, image_url: e.target.value })}
                  placeholder="https://lh3.googleusercontent.com/d/..."
                  className="border-[#E8DFD0] rounded-none"
                />
              </div>
              {cateringItemForm.image_url && (
                <div className="rounded-none overflow-hidden border border-[#E8DFD0]">
                  <img 
                    src={cateringItemForm.image_url} 
                    alt="Preview" 
                    className="w-full h-24 object-cover"
                    onError={(e) => { e.target.src = 'https://via.placeholder.com/200x100?text=Invalid+URL'; }}
                  />
                </div>
              )}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={cateringItemForm.is_veg}
                  onChange={(e) => setCateringItemForm({ ...cateringItemForm, is_veg: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm text-[#5C4A3A]">Vegetarian</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={cateringItemForm.is_available}
                  onChange={(e) => setCateringItemForm({ ...cateringItemForm, is_available: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm text-[#5C4A3A]">Available for ordering</span>
              </label>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setCateringItemDialogOpen(false)} className="rounded-none">
                  Cancel
                </Button>
                <Button type="submit" className="gold-glossy text-[#3D2314] font-bold rounded-none">
                  {editingCateringItem ? 'Update' : 'Add Item'}
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
