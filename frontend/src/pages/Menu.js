import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Globe, ShoppingBag, Leaf } from 'lucide-react';
import { toast } from 'sonner';
import SEOHead from '@/components/SEOHead';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Menu = () => {
  const [menuItems, setMenuItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('all');
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
              className="bg-white rounded-xl overflow-hidden border border-orange-900/10 shadow-sm hover:shadow-md transition-shadow"
              data-testid={`menu-item-${index}`}
            >
              {item.image_url && (
                <div className="h-48 overflow-hidden">
                  <img
                    src={item.image_url}
                    alt={item.name}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <div className="p-5">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h3 className="font-playfair text-lg font-semibold text-foreground mb-1 leading-tight">
                      {item.name}
                    </h3>
                    <div className="flex items-center gap-2">
                      {item.is_veg && (
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 text-xs">
                          Veg
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
