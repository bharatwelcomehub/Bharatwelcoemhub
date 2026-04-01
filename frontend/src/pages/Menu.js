import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Globe, ShoppingBag, Leaf, X, ZoomIn } from 'lucide-react';
import { toast } from 'sonner';
import SEOHead from '@/components/SEOHead';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Menu = () => {
  const [menuItems, setMenuItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedItem, setSelectedItem] = useState(null); // For modal
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

  useEffect(() => {
    fetchMenu();
  }, []);

  useEffect(() => {
    localStorage.setItem('purnabramha_country', selectedCountry);
  }, [selectedCountry]);

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

  const getPrice = (item) => {
    if (selectedCountry === 'Australia') {
      return item.price_aud;
    }
    return item.price_inr;
  };

  const getCurrencySymbol = () => {
    return selectedCountry === 'Australia' ? '$' : '₹';
  };

  const filteredItems = (selectedCategory === 'all'
    ? menuItems
    : menuItems.filter(item => item.category === selectedCategory)
  ).filter(item => {
    const price = getPrice(item);
    return price && price > 0;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-cream to-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-foreground/70 font-manrope">Loading menu...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-cream to-white">
      <SEOHead page="menu" />
      <div className="container mx-auto px-4 lg:px-8 py-12 lg:py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <h1 className="font-playfair text-4xl lg:text-6xl font-bold text-foreground mb-4 tracking-tight">
            Our Menu
          </h1>
          <p className="text-lg text-foreground/70 font-manrope max-w-2xl mx-auto mb-6">
            Explore our authentic Maharashtrian delicacies
          </p>

          {/* Country Selector */}
          <div className="flex items-center justify-center gap-2 mb-4" data-testid="country-selector">
            <Globe className="h-5 w-5 text-primary" />
            <span className="text-sm text-foreground/70 font-manrope">Select Region:</span>
            <div className="flex gap-2">
              <Button
                variant={selectedCountry === 'India' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedCountry('India')}
                className={`rounded-full ${selectedCountry === 'India' ? 'bg-primary' : ''}`}
                data-testid="country-india-btn"
              >
                🇮🇳 India (₹)
              </Button>
              <Button
                variant={selectedCountry === 'Australia' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedCountry('Australia')}
                className={`rounded-full ${selectedCountry === 'Australia' ? 'bg-primary' : ''}`}
                data-testid="country-australia-btn"
              >
                🇦🇺 Australia ($)
              </Button>
            </div>
          </div>
        </motion.div>

        {/* Category Tabs */}
        <div className="mb-8 overflow-x-auto">
          <Tabs value={selectedCategory} onValueChange={setSelectedCategory}>
            <TabsList className="flex flex-wrap justify-center gap-2 h-auto bg-transparent p-0" data-testid="menu-category-tabs">
              {categories.map(cat => (
                <TabsTrigger
                  key={cat.value}
                  value={cat.value}
                  className="rounded-full px-4 py-2 text-sm data-[state=active]:bg-primary data-[state=active]:text-white whitespace-nowrap"
                  data-testid={`category-${cat.value.replace(/[^a-zA-Z0-9]/g, '-')}`}
                >
                  {cat.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>

        {/* Menu Items Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
          {filteredItems.map((item, index) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.03 }}
              className="bg-white rounded-xl overflow-hidden border border-orange-900/10 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
              data-testid={`menu-item-${index}`}
              onClick={() => setSelectedItem(item)}
            >
              <div className="h-48 overflow-hidden relative bg-gradient-to-br from-amber-50 to-orange-50">
                {item.image_url ? (
                  <>
                    <img
                      src={item.image_url}
                      alt={`${item.name} - Maharashtrian dish at Purnabramha`}
                      className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.nextSibling.style.display = 'flex';
                      }}
                    />
                    <div className="hidden w-full h-full items-center justify-center flex-col">
                      <Leaf className="h-12 w-12 text-green-300 mb-2" />
                      <span className="text-green-600 text-sm">Pure Veg</span>
                    </div>
                    <div className="absolute top-2 right-2 bg-black/50 text-white p-2 rounded-full opacity-0 hover:opacity-100 transition-opacity">
                      <ZoomIn className="h-4 w-4" />
                    </div>
                  </>
                ) : (
                  <div className="w-full h-full flex items-center justify-center flex-col">
                    <Leaf className="h-12 w-12 text-green-300 mb-2" />
                    <span className="text-green-600 text-sm font-medium">Pure Veg</span>
                  </div>
                )}
              </div>
              <div className="p-5">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h3 className="font-playfair text-lg font-semibold text-foreground mb-1 leading-tight">
                      {item.name}
                    </h3>
                    <div className="flex flex-wrap items-center gap-2">
                      {item.is_veg && (
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 text-xs">
                          Veg
                        </Badge>
                      )}
                      {item.no_onion_garlic && (
                        <Badge className="bg-orange-500 text-white text-xs font-bold px-2 py-0.5" data-testid="badge-no-onion-garlic">
                          No Onion/Garlic
                        </Badge>
                      )}
                      {item.fasting_friendly && (
                        <Badge className="bg-purple-600 text-white text-xs font-bold px-2 py-0.5" data-testid="badge-fasting-friendly">
                          Fasting Friendly
                        </Badge>
                      )}
                      <Badge variant="outline" className="text-xs text-foreground/50 border-foreground/20">
                        {item.category}
                      </Badge>
                    </div>
                  </div>
                  <div className="text-right ml-3">
                    <p className="font-manrope text-xl font-bold text-primary">
                      {getCurrencySymbol()}{getPrice(item)}
                    </p>
                  </div>
                </div>
                <p className="text-foreground/60 font-manrope text-sm mb-4 leading-relaxed line-clamp-2">
                  {item.description}
                </p>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1 text-green-600">
                    <Leaf className="h-4 w-4" />
                    <span className="text-xs">Pure Veg</span>
                  </div>
                  {!item.is_available && (
                    <Badge variant="outline" className="text-red-500 border-red-200">
                      Currently Unavailable
                    </Badge>
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
              className="fixed inset-0 z-[9999] bg-black/90 flex items-center justify-center p-4"
              onClick={() => setSelectedItem(null)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden shadow-2xl"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Close button */}
                <button
                  onClick={() => setSelectedItem(null)}
                  className="absolute top-4 right-4 z-10 bg-white/90 hover:bg-white text-gray-800 p-2 rounded-full shadow-lg"
                >
                  <X className="h-6 w-6" />
                </button>

                {/* Image */}
                <div className="h-64 md:h-80 bg-gradient-to-br from-amber-100 to-orange-100 relative">
                  {selectedItem.image_url ? (
                    <img
                      src={selectedItem.image_url}
                      alt={`${selectedItem.name} - Authentic Maharashtrian dish`}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center flex-col">
                      <Leaf className="h-20 w-20 text-green-300 mb-3" />
                      <span className="text-green-600 text-lg font-medium">Pure Vegetarian</span>
                    </div>
                  )}
                  {/* Veg badge overlay */}
                  <div className="absolute top-4 left-4 flex flex-wrap gap-2">
                    <div className="bg-green-500 text-white px-3 py-1 rounded-full text-sm font-medium flex items-center gap-1">
                      <Leaf className="h-4 w-4" />
                      Pure Veg
                    </div>
                    {selectedItem.no_onion_garlic && (
                      <div className="bg-orange-500 text-white px-3 py-1 rounded-full text-sm font-bold" data-testid="modal-badge-no-onion-garlic">
                        No Onion/Garlic
                      </div>
                    )}
                    {selectedItem.fasting_friendly && (
                      <div className="bg-purple-600 text-white px-3 py-1 rounded-full text-sm font-bold" data-testid="modal-badge-fasting">
                        Fasting Friendly
                      </div>
                    )}
                  </div>
                </div>

                {/* Content */}
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h2 className="font-playfair text-2xl md:text-3xl font-bold text-[#5c1e1e] mb-2">
                        {selectedItem.name}
                      </h2>
                      <Badge variant="outline" className="text-sm">
                        {selectedItem.category}
                      </Badge>
                      {selectedItem.no_onion_garlic && (
                        <Badge className="bg-orange-500 text-white text-sm font-bold ml-2">
                          No Onion/Garlic
                        </Badge>
                      )}
                      {selectedItem.fasting_friendly && (
                        <Badge className="bg-purple-600 text-white text-sm font-bold ml-2">
                          Fasting Friendly
                        </Badge>
                      )}
                    </div>
                    <div className="text-right">
                      <p className="text-3xl font-bold text-[#5c1e1e]">
                        {getCurrencySymbol()}{getPrice(selectedItem)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {selectedCountry === 'Australia' ? 'AUD' : 'INR'}
                      </p>
                    </div>
                  </div>

                  <p className="text-gray-600 text-base leading-relaxed mb-6">
                    {selectedItem.description || 'Authentic Maharashtrian delicacy prepared with traditional recipes and fresh ingredients.'}
                  </p>

                  <div className="flex gap-3">
                    <Link to="/pickup" className="flex-1">
                      <Button className="w-full bg-[#5c1e1e] hover:bg-[#8b2c2c] rounded-full py-6">
                        <ShoppingBag className="mr-2 h-5 w-5" />
                        Order for Pickup
                      </Button>
                    </Link>
                    <Button
                      variant="outline"
                      className="rounded-full py-6 px-6"
                      onClick={() => setSelectedItem(null)}
                    >
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
            <p className="text-lg text-foreground/70 font-manrope">
              No items found in this category for {selectedCountry}
            </p>
            <p className="text-sm text-foreground/50 font-manrope mt-2">
              Try switching to a different region or category
            </p>
          </div>
        )}

        {/* Order CTA */}
        <div className="text-center mt-12 p-8 bg-gradient-to-r from-amber-50 to-orange-50 rounded-2xl">
          <h3 className="text-2xl font-bold text-[#5c1e1e] mb-3">
            Ready to Order?
          </h3>
          <p className="text-gray-600 mb-6">
            Place your order via WhatsApp and pick up fresh from your nearest center
          </p>
          <Link to="/pickup">
            <Button className="bg-[#5c1e1e] hover:bg-[#8b2c2c] rounded-full px-8 py-6 text-lg">
              <ShoppingBag className="mr-2 h-5 w-5" />
              Order for Pickup
            </Button>
          </Link>
        </div>

        {/* Menu item count */}
        <div className="text-center mt-8 text-sm text-foreground/50 font-manrope">
          Showing {filteredItems.length} items {selectedCategory !== 'all' && `in ${selectedCategory}`}
        </div>
      </div>
    </div>
  );
};

export default Menu;
