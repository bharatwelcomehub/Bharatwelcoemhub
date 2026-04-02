import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Globe, ShoppingBag, Leaf, X, ZoomIn, Flame, Dumbbell, Wheat, Droplets, AlertTriangle, Heart, Sparkles, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import SEOHead from '@/components/SEOHead';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Menu = () => {
  const [menuItems, setMenuItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedItem, setSelectedItem] = useState(null); // For modal
  const [nutritionData, setNutritionData] = useState(null);
  const [nutritionLoading, setNutritionLoading] = useState(false);
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
              onClick={() => handleItemClick(item)}
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
              onClick={() => { setSelectedItem(null); setNutritionData(null); }}
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
                  onClick={() => { setSelectedItem(null); setNutritionData(null); }}
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
                <div className="p-6 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 20rem)' }}>
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h2 className="font-playfair text-2xl md:text-3xl font-bold text-[#5c1e1e] mb-2">
                        {selectedItem.name}
                      </h2>
                      <div className="flex flex-wrap gap-1">
                        <Badge variant="outline" className="text-sm">
                          {selectedItem.category}
                        </Badge>
                        {selectedItem.no_onion_garlic && (
                          <Badge className="bg-orange-500 text-white text-sm font-bold">
                            No Onion/Garlic
                          </Badge>
                        )}
                        {selectedItem.fasting_friendly && (
                          <Badge className="bg-purple-600 text-white text-sm font-bold">
                            Fasting Friendly
                          </Badge>
                        )}
                      </div>
                    </div>
                    <div className="text-right ml-3">
                      <p className="text-3xl font-bold text-[#5c1e1e]">
                        {getCurrencySymbol()}{getPrice(selectedItem)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {selectedCountry === 'Australia' ? 'AUD' : 'INR'}
                      </p>
                    </div>
                  </div>

                  <p className="text-gray-600 text-base leading-relaxed mb-5">
                    {selectedItem.description || 'Authentic Maharashtrian delicacy prepared with traditional recipes and fresh ingredients.'}
                  </p>

                  {/* Nutrition Section */}
                  <NutritionPanel data={nutritionData} loading={nutritionLoading} />

                  <div className="flex gap-3 mt-5">
                    <Link to="/pickup" className="flex-1">
                      <Button className="w-full bg-[#5c1e1e] hover:bg-[#8b2c2c] rounded-full py-6">
                        <ShoppingBag className="mr-2 h-5 w-5" />
                        Order for Pickup
                      </Button>
                    </Link>
                    <Button
                      variant="outline"
                      className="rounded-full py-6 px-6"
                      onClick={() => { setSelectedItem(null); setNutritionData(null); }}
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

// Nutrition Panel Component
const NutritionPanel = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl p-5 border border-amber-200" data-testid="nutrition-loading">
        <div className="flex items-center justify-center gap-3 py-6">
          <Loader2 className="h-6 w-6 text-[#5c1e1e] animate-spin" />
          <span className="text-[#5c1e1e] font-medium">Analyzing nutrition...</span>
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
      {/* Macro Summary */}
      <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl p-5 border border-amber-200">
        <div className="flex items-center gap-2 mb-3">
          <Flame className="h-5 w-5 text-orange-600" />
          <h3 className="font-bold text-[#5c1e1e] text-lg">Nutrition Facts</h3>
          <span className="text-xs text-gray-500 ml-auto">{data.serving_size}</span>
        </div>

        {/* Calories Highlight */}
        <div className="text-center mb-4 py-3 bg-white/70 rounded-lg">
          <p className="text-4xl font-bold text-[#5c1e1e]">{data.calories}</p>
          <p className="text-sm text-gray-600 font-medium">Calories per serving</p>
        </div>

        {/* Macro Bars */}
        <div className="grid grid-cols-4 gap-3 mb-3">
          <MacroCard icon={<Dumbbell className="h-4 w-4" />} label="Protein" value={`${data.protein}g`} color="text-blue-700" bg="bg-blue-100" />
          <MacroCard icon={<Wheat className="h-4 w-4" />} label="Carbs" value={`${data.carbs}g`} color="text-amber-700" bg="bg-amber-100" />
          <MacroCard icon={<Droplets className="h-4 w-4" />} label="Fats" value={`${data.fats}g`} color="text-red-700" bg="bg-red-100" />
          <MacroCard icon={<Leaf className="h-4 w-4" />} label="Fiber" value={`${data.fiber}g`} color="text-green-700" bg="bg-green-100" />
        </div>

        {/* Visual Macro Bar */}
        <div className="h-3 rounded-full overflow-hidden flex bg-gray-200">
          <div className="bg-blue-500 transition-all" style={{ width: `${proteinPct}%` }} title={`Protein ${proteinPct.toFixed(0)}%`} />
          <div className="bg-amber-500 transition-all" style={{ width: `${carbsPct}%` }} title={`Carbs ${carbsPct.toFixed(0)}%`} />
          <div className="bg-red-400 transition-all" style={{ width: `${fatsPct}%` }} title={`Fats ${fatsPct.toFixed(0)}%`} />
        </div>
        <div className="flex justify-between text-[10px] text-gray-500 mt-1">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />Protein {proteinPct.toFixed(0)}%</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />Carbs {carbsPct.toFixed(0)}%</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400 inline-block" />Fats {fatsPct.toFixed(0)}%</span>
        </div>
      </div>

      {/* Health Benefits & Ayurvedic */}
      <div className="grid md:grid-cols-2 gap-3">
        {data.health_benefits?.length > 0 && (
          <div className="bg-green-50 rounded-xl p-4 border border-green-200">
            <div className="flex items-center gap-2 mb-2">
              <Heart className="h-4 w-4 text-green-600" />
              <h4 className="font-bold text-green-800 text-sm">Health Benefits</h4>
            </div>
            <ul className="space-y-1">
              {data.health_benefits.map((benefit, i) => (
                <li key={i} className="text-xs text-green-700 flex items-start gap-1.5">
                  <span className="text-green-500 mt-0.5">&#x2713;</span>
                  {benefit}
                </li>
              ))}
            </ul>
          </div>
        )}

        {data.ayurvedic_benefits && (
          <div className="bg-purple-50 rounded-xl p-4 border border-purple-200">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="h-4 w-4 text-purple-600" />
              <h4 className="font-bold text-purple-800 text-sm">Ayurvedic Wisdom</h4>
            </div>
            <p className="text-xs text-purple-700 leading-relaxed">{data.ayurvedic_benefits}</p>
          </div>
        )}
      </div>

      {/* Dietary Tags & Allergens */}
      <div className="flex flex-wrap gap-2">
        {data.dietary_tags?.map((tag, i) => (
          <Badge key={i} className="bg-teal-100 text-teal-800 border-teal-300 text-xs" variant="outline">
            {tag}
          </Badge>
        ))}
        {data.allergens?.length > 0 && data.allergens.map((allergen, i) => (
          <Badge key={`a-${i}`} className="bg-red-50 text-red-700 border-red-200 text-xs" variant="outline">
            <AlertTriangle className="h-3 w-3 mr-1" />
            {allergen}
          </Badge>
        ))}
      </div>

      {/* Disclaimer */}
      <p className="text-[10px] text-gray-400 italic text-center">
        * Nutritional values are AI-estimated for general guidance. Actual values may vary based on preparation.
      </p>
    </div>
  );
};

const MacroCard = ({ icon, label, value, color, bg }) => (
  <div className={`${bg} rounded-lg p-2 text-center`}>
    <div className={`${color} flex justify-center mb-1`}>{icon}</div>
    <p className={`text-lg font-bold ${color}`}>{value}</p>
    <p className="text-[10px] text-gray-600">{label}</p>
  </div>
);

export default Menu;
