import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Globe, ShoppingBag, Leaf, X, ZoomIn, Flame, Dumbbell, Wheat, Droplets, AlertTriangle, Heart, Sparkles, Loader2, Camera, Upload, ScanLine } from 'lucide-react';
import { toast } from 'sonner';
import SEOHead from '@/components/SEOHead';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Menu = () => {
  const [menuItems, setMenuItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedItem, setSelectedItem] = useState(null);
  const [nutritionData, setNutritionData] = useState(null);
  const [nutritionLoading, setNutritionLoading] = useState(false);
  const [scanModalOpen, setScanModalOpen] = useState(false);
  const [scanLoading, setScanLoading] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [scanPreview, setScanPreview] = useState(null);
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const [selectedCountry, setSelectedCountry] = useState(() => {
    return localStorage.getItem('purnabramha_country') || 'India';
  });

  const categories = [
    { value: 'all', label: 'All Items' },
    { value: 'Balgopal (Kids)', label: 'Kids Menu' },
    { value: 'Tea & Coffee', label: 'Tea & Coffee' },
    { value: 'Drinks', label: 'Drinks' },
    { value: 'Soup & Saar', label: 'Soup & Saar' },
    { value: 'Snacks', label: 'Snacks' },
    { value: 'Fasting', label: 'Fasting' },
    { value: 'Heavy Brunch', label: 'Heavy Brunch' },
    { value: 'Bhakar Combo', label: 'Bhakar Combo' },
    { value: 'Bhaji', label: 'Bhaji' },
    { value: 'Dal', label: 'Dal' },
    { value: 'Rice', label: 'Rice' },
    { value: 'Roti', label: 'Roti' },
    { value: 'Sweets', label: 'Sweets' },
    { value: 'Special Thalis', label: 'Special Thalis' },
    { value: 'Sides', label: 'Sides' }
  ];

  useEffect(() => { fetchMenu(); }, []);
  useEffect(() => { localStorage.setItem('purnabramha_country', selectedCountry); }, [selectedCountry]);

  const fetchMenu = async () => {
    try {
      const response = await axios.get(`${API}/menu`);
      setMenuItems(response.data);
    } catch (error) {
      console.error('Failed to fetch menu:', error);
      toast.error('Failed to load menu');
    } finally {
      setLoading(false);
    }
  };

  const fetchNutrition = async (itemId) => {
    setNutritionLoading(true);
    setNutritionData(null);
    try {
      const response = await axios.get(`${API}/nutrition/${itemId}`);
      setNutritionData(response.data);
    } catch (error) {
      console.error('Failed to fetch nutrition:', error);
    } finally {
      setNutritionLoading(false);
    }
  };

  const handleItemClick = (item) => {
    setSelectedItem(item);
    fetchNutrition(item.id);
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setScanPreview(ev.target.result);
    reader.readAsDataURL(file);
    const base64Reader = new FileReader();
    base64Reader.onload = async (ev) => {
      const base64 = ev.target.result.split(',')[1];
      await scanDish(base64);
    };
    base64Reader.readAsDataURL(file);
  };

  const scanDish = async (imageBase64) => {
    setScanLoading(true);
    setScanResult(null);
    try {
      const response = await axios.post(`${API}/scan-dish`, { image_base64: imageBase64 });
      setScanResult(response.data);
      if (response.data.success) {
        toast.success(`Identified: ${response.data.matched_item.name}`);
      } else {
        toast.error(response.data.message || 'Could not identify dish');
      }
    } catch (error) {
      console.error('Scan failed:', error);
      toast.error('Failed to scan dish. Please try again.');
    } finally {
      setScanLoading(false);
    }
  };

  const closeScanModal = () => {
    setScanModalOpen(false);
    setScanResult(null);
    setScanPreview(null);
    setScanLoading(false);
  };

  const getPrice = (item) => selectedCountry === 'Australia' ? item.price_aud : item.price_inr;
  const getCurrencySymbol = () => selectedCountry === 'Australia' ? '$' : '₹';

  const filteredItems = (selectedCategory === 'all'
    ? menuItems
    : menuItems.filter(item => item.category === selectedCategory)
  ).filter(item => {
    const price = getPrice(item);
    return price && price > 0;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FDFBF7] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#B8962E] mx-auto mb-4"></div>
          <p className="text-[#7A6F65] font-body">Loading menu...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FDFBF7]">
      <SEOHead page="menu" />
      <div className="container mx-auto px-6 lg:px-12 py-16 lg:py-24">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-12">
          <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-4">Signature Menu</p>
          <h1 className="font-heading text-5xl md:text-6xl lg:text-7xl font-medium text-[#2D1810] mb-4 tracking-tight">
            Our <span className="text-gold-shimmer">Menu</span>
          </h1>
          <p className="text-lg text-[#5C4A3A] font-body max-w-2xl mx-auto mb-8">
            Explore our authentic Maharashtrian delicacies
          </p>

          {/* Country Selector */}
          <div className="flex items-center justify-center gap-3 mb-4" data-testid="country-selector">
            <Globe className="h-5 w-5 text-[#B8962E]/60" />
            <span className="text-sm text-[#5C4A3A] font-body">Region:</span>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => setSelectedCountry('India')}
                className={`rounded-none text-xs tracking-wider ${selectedCountry === 'India' ? 'bg-[#B8962E] text-white hover:bg-[#D4AF37]' : 'bg-white border border-[#E8DFD0] text-[#5C4A3A] hover:border-[#B8962E]/30 hover:text-[#B8962E]'}`}
                data-testid="country-india-btn"
              >
                India (₹)
              </Button>
              <Button
                size="sm"
                onClick={() => setSelectedCountry('Australia')}
                className={`rounded-none text-xs tracking-wider ${selectedCountry === 'Australia' ? 'bg-[#B8962E] text-white hover:bg-[#D4AF37]' : 'bg-white border border-[#E8DFD0] text-[#5C4A3A] hover:border-[#B8962E]/30 hover:text-[#B8962E]'}`}
                data-testid="country-australia-btn"
              >
                Australia ($)
              </Button>
            </div>
          </div>
        </motion.div>

        {/* Category Tabs */}
        <div className="mb-10 overflow-x-auto">
          <Tabs value={selectedCategory} onValueChange={setSelectedCategory}>
            <TabsList className="flex flex-wrap justify-center gap-2 h-auto bg-transparent p-0" data-testid="menu-category-tabs">
              {categories.map(cat => (
                <TabsTrigger
                  key={cat.value}
                  value={cat.value}
                  className="rounded-none px-4 py-2 text-xs tracking-wider font-body border border-[#E8DFD0] bg-white text-[#5C4A3A] data-[state=active]:bg-[#B8962E] data-[state=active]:text-white data-[state=active]:border-[#B8962E] whitespace-nowrap transition-all hover:border-[#B8962E]/30"
                  data-testid={`category-${cat.value.replace(/[^a-zA-Z0-9]/g, '-')}`}
                >
                  {cat.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>

        {/* Menu Items Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredItems.map((item, index) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.03 }}
              className="bg-white border border-[#E8DFD0] overflow-hidden hover:border-[#B8962E]/30 transition-all cursor-pointer group hover:shadow-lg"
              data-testid={`menu-item-${index}`}
              onClick={() => handleItemClick(item)}
            >
              <div className="h-48 overflow-hidden relative bg-[#F8F5F0]">
                {item.image_url ? (
                  <>
                    <img
                      src={item.image_url}
                      alt={`${item.name} - Maharashtrian dish at Purnabramha`}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                      onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
                    />
                    <div className="hidden w-full h-full items-center justify-center flex-col">
                      <Leaf className="h-12 w-12 text-[#B8962E]/30 mb-2" />
                      <span className="text-[#B8962E]/50 text-sm font-body">Pure Veg</span>
                    </div>
                    <div className="absolute inset-0 bg-gradient-to-t from-white via-transparent to-transparent" />
                  </>
                ) : (
                  <div className="w-full h-full flex items-center justify-center flex-col">
                    <Leaf className="h-12 w-12 text-[#B8962E]/30 mb-2" />
                    <span className="text-[#B8962E]/50 text-sm font-body font-medium">Pure Veg</span>
                  </div>
                )}
              </div>
              <div className="p-6">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h3 className="font-heading text-lg font-medium text-[#2D1810] mb-1 leading-tight">{item.name}</h3>
                    <div className="flex flex-wrap items-center gap-1.5">
                      {item.no_onion_garlic && (
                        <Badge className="bg-orange-100 text-orange-600 border border-orange-200 text-[10px] font-bold px-2 py-0" data-testid="badge-no-onion-garlic">
                          No Onion/Garlic
                        </Badge>
                      )}
                      {item.fasting_friendly && (
                        <Badge className="bg-purple-100 text-purple-600 border border-purple-200 text-[10px] font-bold px-2 py-0" data-testid="badge-fasting-friendly">
                          Fasting Friendly
                        </Badge>
                      )}
                      <span className="text-[10px] text-[#7A6F65] font-body tracking-wider uppercase">{item.category}</span>
                    </div>
                  </div>
                  <div className="text-right ml-3">
                    <p className="font-heading text-xl font-medium text-[#B8962E]">
                      {getCurrencySymbol()}{getPrice(item)}
                    </p>
                  </div>
                </div>
                <p className="text-[#5C4A3A]/70 font-body text-sm mb-3 leading-relaxed line-clamp-2">{item.description}</p>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1 text-[#B8962E]/40">
                    <Leaf className="h-3 w-3" />
                    <span className="text-[10px] font-body tracking-wider uppercase">Pure Veg</span>
                  </div>
                  {!item.is_available && (
                    <span className="text-[10px] text-red-500/70 font-body tracking-wider uppercase">Unavailable</span>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Menu Item Detail Modal */}
        <AnimatePresence>
          {selectedItem && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-[9999] bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
              onClick={() => { setSelectedItem(null); setNutritionData(null); }}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-white border border-[#E8DFD0] max-w-2xl w-full max-h-[90vh] overflow-hidden shadow-2xl"
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  onClick={() => { setSelectedItem(null); setNutritionData(null); }}
                  className="absolute top-4 right-4 z-10 bg-white border border-[#E8DFD0] text-[#5C4A3A] hover:text-[#2D1810] p-2"
                >
                  <X className="h-5 w-5" />
                </button>

                <div className="h-64 md:h-72 bg-[#F8F5F0] relative">
                  {selectedItem.image_url ? (
                    <img src={selectedItem.image_url} alt={selectedItem.name} className="w-full h-full object-cover" onError={(e) => { e.target.style.display = 'none'; }} />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center flex-col">
                      <Leaf className="h-20 w-20 text-[#B8962E]/20 mb-3" />
                      <span className="text-[#B8962E]/40 text-lg font-body font-medium">Pure Vegetarian</span>
                    </div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-white via-transparent to-transparent" />
                  <div className="absolute top-4 left-4 flex flex-wrap gap-2">
                    <span className="bg-[#B8962E] text-white px-3 py-1 text-[10px] tracking-wider uppercase font-semibold flex items-center gap-1">
                      <Leaf className="h-3 w-3" /> Pure Veg
                    </span>
                    {selectedItem.no_onion_garlic && (
                      <span className="bg-orange-500 text-white px-3 py-1 text-[10px] font-bold" data-testid="modal-badge-no-onion-garlic">No Onion/Garlic</span>
                    )}
                    {selectedItem.fasting_friendly && (
                      <span className="bg-purple-500 text-white px-3 py-1 text-[10px] font-bold" data-testid="modal-badge-fasting">Fasting Friendly</span>
                    )}
                  </div>
                </div>

                <div className="p-6 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 18rem)' }}>
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h2 className="font-heading text-2xl md:text-3xl font-medium text-[#2D1810] mb-2">{selectedItem.name}</h2>
                      <div className="flex flex-wrap gap-1">
                        <span className="text-xs text-[#7A6F65] border border-[#E8DFD0] px-2 py-0.5 font-body">{selectedItem.category}</span>
                      </div>
                    </div>
                    <div className="text-right ml-3">
                      <p className="text-3xl font-heading font-medium text-[#B8962E]">{getCurrencySymbol()}{getPrice(selectedItem)}</p>
                      <p className="text-xs text-[#7A6F65] font-body">{selectedCountry === 'Australia' ? 'AUD' : 'INR'}</p>
                    </div>
                  </div>
                  <p className="text-[#5C4A3A] text-sm font-body leading-relaxed mb-5">
                    {selectedItem.description || 'Authentic Maharashtrian delicacy prepared with traditional recipes and fresh ingredients.'}
                  </p>
                  <NutritionPanel data={nutritionData} loading={nutritionLoading} />
                  <div className="flex gap-3 mt-5">
                    <Link to="/pickup" className="flex-1">
                      <Button className="w-full gold-glossy text-white rounded-none py-6 text-xs tracking-widest uppercase font-semibold border-0" data-testid="modal-order-btn">
                        <ShoppingBag className="mr-2 h-4 w-4" /> Order for Pickup
                      </Button>
                    </Link>
                    <Button variant="outline" className="border-[#E8DFD0] text-[#5C4A3A] hover:text-[#2D1810] hover:border-[#B8962E]/30 rounded-none py-6 px-6" onClick={() => { setSelectedItem(null); setNutritionData(null); }}>
                      Close
                    </Button>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {filteredItems.length === 0 && (
          <div className="text-center py-20">
            <p className="text-lg text-[#5C4A3A] font-body">No items found in this category for {selectedCountry}</p>
            <p className="text-sm text-[#7A6F65] font-body mt-2">Try switching to a different region or category</p>
          </div>
        )}

        {/* Order CTA */}
        <div className="text-center mt-16 p-12 pearl-surface">
          <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-4">Ready to Order?</p>
          <h3 className="text-3xl md:text-4xl font-heading font-medium text-[#2D1810] mb-3 tracking-tight">
            Experience <span className="text-gold-shimmer">Authentic Flavor</span>
          </h3>
          <p className="text-[#5C4A3A] mb-8 font-body">
            Place your order via WhatsApp and pick up fresh from your nearest center
          </p>
          <Link to="/pickup">
            <Button className="gold-glossy text-white rounded-none px-8 py-6 text-xs tracking-widest uppercase font-semibold border-0">
              <ShoppingBag className="mr-2 h-4 w-4" /> Order for Pickup
            </Button>
          </Link>
        </div>

        <div className="text-center mt-8 text-sm text-[#7A6F65] font-body">
          Showing {filteredItems.length} items {selectedCategory !== 'all' && `in ${selectedCategory}`}
        </div>
      </div>

      {/* Floating Scan Dish Button (positioned above Ask Vahini FAB so they never overlap) */}
      <button
        onClick={() => setScanModalOpen(true)}
        className="fixed bottom-28 right-6 z-50 gold-glossy text-white p-4 transition-all hover:scale-110 active:scale-95 group shadow-lg rounded-full"
        data-testid="scan-dish-btn"
        title="Scan a dish photo"
        aria-label="Scan a dish photo"
      >
        <Camera className="h-6 w-6" />
        <span className="absolute right-full mr-3 top-1/2 -translate-y-1/2 bg-white border border-[#E8DFD0] text-[#2D1810] text-sm px-3 py-1.5 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none shadow-lg rounded">
          Scan Dish
        </span>
      </button>

      <input type="file" ref={fileInputRef} accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handleFileSelect} data-testid="scan-file-input" />
      <input type="file" ref={cameraInputRef} accept="image/jpeg,image/png,image/webp" capture="environment" className="hidden" onChange={handleFileSelect} data-testid="scan-camera-input" />

      {/* Scan Dish Modal */}
      <AnimatePresence>
        {scanModalOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[9999] bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
            onClick={(e) => { if (e.target === e.currentTarget) closeScanModal(); }}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white border border-[#E8DFD0] max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="bg-[#F8F5F0] border-b border-[#B8962E]/20 p-5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <ScanLine className="h-5 w-5 text-[#B8962E]" />
                  <h2 className="text-lg font-heading font-medium text-[#2D1810]">Scan Your Dish</h2>
                </div>
                <button onClick={closeScanModal} className="text-[#5C4A3A] hover:text-[#2D1810] p-1">
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="p-5">
                {!scanPreview && !scanLoading && !scanResult && (
                  <div className="space-y-4">
                    <p className="text-[#5C4A3A] text-sm text-center mb-4 font-body">
                      Take a photo or upload an image of any dish to get instant nutrition info
                    </p>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        onClick={() => cameraInputRef.current?.click()}
                        className="flex flex-col items-center gap-3 p-6 border border-dashed border-[#B8962E]/30 hover:border-[#B8962E] hover:bg-[#B8962E]/5 transition-all"
                        data-testid="scan-camera-btn"
                      >
                        <Camera className="h-10 w-10 text-[#B8962E]" />
                        <span className="text-sm font-body font-medium text-[#B8962E]">Take Photo</span>
                      </button>
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="flex flex-col items-center gap-3 p-6 border border-dashed border-[#B8962E]/30 hover:border-[#B8962E] hover:bg-[#B8962E]/5 transition-all"
                        data-testid="scan-upload-btn"
                      >
                        <Upload className="h-10 w-10 text-[#B8962E]" />
                        <span className="text-sm font-body font-medium text-[#B8962E]">Upload Image</span>
                      </button>
                    </div>
                  </div>
                )}

                {scanLoading && (
                  <div className="text-center py-8" data-testid="scan-loading">
                    {scanPreview && (
                      <img src={scanPreview} alt="Scanning..." className="w-48 h-48 object-cover mx-auto mb-4 border border-[#B8962E]/30" />
                    )}
                    <div className="flex items-center justify-center gap-3">
                      <Loader2 className="h-6 w-6 text-[#B8962E] animate-spin" />
                      <span className="text-[#B8962E] font-body font-medium">Identifying dish...</span>
                    </div>
                    <p className="text-xs text-[#7A6F65] mt-2 font-body">AI is analyzing your photo</p>
                  </div>
                )}

                {scanResult && !scanLoading && (
                  <ScanResultPanel
                    result={scanResult}
                    preview={scanPreview}
                    getCurrencySymbol={getCurrencySymbol}
                    getPrice={(item) => selectedCountry === 'Australia' ? item.price_aud : item.price_inr}
                    onRetry={() => { setScanResult(null); setScanPreview(null); }}
                    onClose={closeScanModal}
                  />
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const ScanResultPanel = ({ result, preview, getCurrencySymbol, getPrice, onRetry, onClose }) => {
  if (!result.success) {
    return (
      <div className="text-center py-4" data-testid="scan-no-match">
        {preview && <img src={preview} alt="Scanned" className="w-40 h-40 object-cover mx-auto mb-4 border border-[#E8DFD0]" />}
        <div className="bg-red-50 border border-red-200 p-4 mb-4">
          <p className="text-red-600 font-body font-medium">{result.message}</p>
          {result.ai_description && <p className="text-sm text-[#7A6F65] mt-2 font-body">AI saw: {result.ai_description}</p>}
        </div>
        <div className="flex gap-3">
          <Button onClick={onRetry} variant="outline" className="flex-1 border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] hover:border-[#B8962E]/30 rounded-none">
            <Camera className="mr-2 h-4 w-4" /> Try Again
          </Button>
          <Button onClick={onClose} variant="ghost" className="text-[#5C4A3A] hover:text-[#2D1810] rounded-none">Close</Button>
        </div>
      </div>
    );
  }

  const item = result.matched_item;
  const nutrition = result.nutrition;

  return (
    <div className="space-y-4" data-testid="scan-result-success">
      <div className="flex gap-4 items-start">
        {preview && <img src={preview} alt="Your photo" className="w-24 h-24 object-cover border border-[#B8962E]/30 flex-shrink-0" />}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Badge className={`text-[10px] ${result.confidence === 'high' ? 'bg-green-100 text-green-600 border-green-200' : result.confidence === 'medium' ? 'bg-amber-100 text-amber-600 border-amber-200' : 'bg-red-100 text-red-600 border-red-200'}`}>
              {result.confidence} match
            </Badge>
          </div>
          <h3 className="font-heading text-xl font-medium text-[#2D1810]">{item.name}</h3>
          <div className="flex flex-wrap gap-1 mt-1">
            <span className="text-[10px] text-[#7A6F65] border border-[#E8DFD0] px-2 py-0.5 font-body">{item.category}</span>
            {item.no_onion_garlic && <Badge className="bg-orange-100 text-orange-600 border-orange-200 text-[10px] font-bold">No Onion/Garlic</Badge>}
            {item.fasting_friendly && <Badge className="bg-purple-100 text-purple-600 border-purple-200 text-[10px] font-bold">Fasting Friendly</Badge>}
          </div>
          <p className="text-2xl font-heading font-medium text-[#B8962E] mt-2">{getCurrencySymbol()}{getPrice(item)}</p>
        </div>
      </div>
      {item.description && <p className="text-sm text-[#5C4A3A] font-body">{item.description}</p>}
      {result.ai_description && <p className="text-xs text-[#7A6F65] italic font-body">AI observation: {result.ai_description}</p>}
      {nutrition && <NutritionPanel data={nutrition} loading={false} />}
      <div className="flex gap-3 pt-2">
        <Link to="/pickup" className="flex-1">
          <Button className="w-full gold-glossy text-white rounded-none py-5 text-xs tracking-widest uppercase font-semibold border-0" data-testid="scan-order-btn">
            <ShoppingBag className="mr-2 h-4 w-4" /> Order for Pickup
          </Button>
        </Link>
        <Button onClick={onRetry} variant="outline" className="border-[#E8DFD0] text-[#5C4A3A] hover:text-[#B8962E] hover:border-[#B8962E]/30 rounded-none py-5" data-testid="scan-retry-btn">
          <Camera className="mr-2 h-4 w-4" /> Scan Another
        </Button>
      </div>
    </div>
  );
};

const NutritionPanel = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-5" data-testid="nutrition-loading">
        <div className="flex items-center justify-center gap-3 py-6">
          <Loader2 className="h-6 w-6 text-[#B8962E] animate-spin" />
          <span className="text-[#B8962E] font-body font-medium">Analyzing nutrition...</span>
        </div>
      </div>
    );
  }
  if (!data) return null;

  const totalMacros = data.protein + data.carbs + data.fats;
  const proteinPct = totalMacros > 0 ? (data.protein / totalMacros) * 100 : 0;
  const carbsPct = totalMacros > 0 ? (data.carbs / totalMacros) * 100 : 0;
  const fatsPct = totalMacros > 0 ? (data.fats / totalMacros) * 100 : 0;

  return (
    <div className="space-y-4" data-testid="nutrition-panel">
      <div className="bg-[#F8F5F0] border border-[#E8DFD0] p-5">
        <div className="flex items-center gap-2 mb-3">
          <Flame className="h-5 w-5 text-[#B8962E]" />
          <h3 className="font-heading font-medium text-[#2D1810] text-lg">Nutrition Facts</h3>
          <span className="text-xs text-[#7A6F65] ml-auto font-body">{data.serving_size}</span>
        </div>
        <div className="text-center mb-4 py-3 bg-white border border-[#E8DFD0]">
          <p className="text-4xl font-heading font-medium text-[#B8962E]">{data.calories}</p>
          <p className="text-sm text-[#5C4A3A] font-body">Calories per serving</p>
        </div>
        <div className="grid grid-cols-4 gap-3 mb-3">
          <MacroCard icon={<Dumbbell className="h-4 w-4" />} label="Protein" value={`${data.protein}g`} color="text-blue-600" bg="bg-blue-50 border border-blue-100" />
          <MacroCard icon={<Wheat className="h-4 w-4" />} label="Carbs" value={`${data.carbs}g`} color="text-amber-600" bg="bg-amber-50 border border-amber-100" />
          <MacroCard icon={<Droplets className="h-4 w-4" />} label="Fats" value={`${data.fats}g`} color="text-red-500" bg="bg-red-50 border border-red-100" />
          <MacroCard icon={<Leaf className="h-4 w-4" />} label="Fiber" value={`${data.fiber}g`} color="text-green-600" bg="bg-green-50 border border-green-100" />
        </div>
        <div className="h-2 overflow-hidden flex bg-white border border-[#E8DFD0]">
          <div className="bg-blue-500 transition-all" style={{ width: `${proteinPct}%` }} />
          <div className="bg-amber-500 transition-all" style={{ width: `${carbsPct}%` }} />
          <div className="bg-red-400 transition-all" style={{ width: `${fatsPct}%` }} />
        </div>
        <div className="flex justify-between text-[10px] text-[#7A6F65] mt-1 font-body">
          <span className="flex items-center gap-1"><span className="w-2 h-2 bg-blue-500 inline-block" />Protein {proteinPct.toFixed(0)}%</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 bg-amber-500 inline-block" />Carbs {carbsPct.toFixed(0)}%</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 bg-red-400 inline-block" />Fats {fatsPct.toFixed(0)}%</span>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-3">
        {data.health_benefits?.length > 0 && (
          <div className="bg-green-50 border border-green-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Heart className="h-4 w-4 text-green-600" />
              <h4 className="font-body font-semibold text-green-700 text-sm">Health Benefits</h4>
            </div>
            <ul className="space-y-1">
              {data.health_benefits.map((benefit, i) => (
                <li key={i} className="text-xs text-green-600 flex items-start gap-1.5 font-body">
                  <span className="text-green-600 mt-0.5">&#x2713;</span>{benefit}
                </li>
              ))}
            </ul>
          </div>
        )}
        {data.ayurvedic_benefits && (
          <div className="bg-purple-50 border border-purple-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="h-4 w-4 text-purple-600" />
              <h4 className="font-body font-semibold text-purple-700 text-sm">Ayurvedic Wisdom</h4>
            </div>
            <p className="text-xs text-purple-600 leading-relaxed font-body">{data.ayurvedic_benefits}</p>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {data.dietary_tags?.map((tag, i) => (
          <Badge key={i} className="bg-teal-50 text-teal-600 border-teal-200 text-xs font-body" variant="outline">{tag}</Badge>
        ))}
        {data.allergens?.length > 0 && data.allergens.map((allergen, i) => (
          <Badge key={`a-${i}`} className="bg-red-50 text-red-500 border-red-200 text-xs font-body" variant="outline">
            <AlertTriangle className="h-3 w-3 mr-1" />{allergen}
          </Badge>
        ))}
      </div>
      <p className="text-[10px] text-[#7A6F65] italic text-center font-body">* Nutritional values are AI-estimated for general guidance. Actual values may vary.</p>
    </div>
  );
};

const MacroCard = ({ icon, label, value, color, bg }) => (
  <div className={`${bg} p-2 text-center`}>
    <div className={`${color} flex justify-center mb-1`}>{icon}</div>
    <p className={`text-lg font-heading font-medium ${color}`}>{value}</p>
    <p className="text-[10px] text-[#7A6F65] font-body">{label}</p>
  </div>
);

export default Menu;
