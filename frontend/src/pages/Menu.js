import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Plus } from 'lucide-react';
import { useCart } from '@/contexts/CartContext';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Menu = () => {
  const [menuItems, setMenuItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const { addToCart } = useCart();

  const categories = [
    { value: 'all', label: 'All Items' },
    { value: 'Breakfast', label: 'Breakfast' },
    { value: 'Thali', label: 'Thali' },
    { value: 'Snacks', label: 'Snacks' },
    { value: 'Main Course', label: 'Main Course' },
    { value: 'Desserts', label: 'Desserts' },
    { value: 'Beverages', label: 'Beverages' }
  ];

  useEffect(() => {
    fetchMenu();
  }, []);

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

  const handleAddToCart = (item) => {
    addToCart(item);
    toast.success(`${item.name} added to cart`);
  };

  const filteredItems = selectedCategory === 'all'
    ? menuItems
    : menuItems.filter(item => item.category === selectedCategory);

  if (loading) {
    return (
      <div className="container mx-auto px-4 lg:px-8 py-20">
        <div className="text-center">Loading menu...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-cream to-white">
      <div className="container mx-auto px-4 lg:px-8 py-12 lg:py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="font-playfair text-4xl lg:text-6xl font-bold text-foreground mb-4 tracking-tight">
            Our Menu
          </h1>
          <p className="text-lg text-foreground/70 font-manrope max-w-2xl mx-auto">
            Explore our authentic Maharashtrian delicacies
          </p>
        </motion.div>

        <Tabs value={selectedCategory} onValueChange={setSelectedCategory} className="mb-12">
          <TabsList className="flex flex-wrap justify-center gap-2 h-auto bg-transparent" data-testid="menu-category-tabs">
            {categories.map(cat => (
              <TabsTrigger
                key={cat.value}
                value={cat.value}
                className="rounded-full px-6 data-[state=active]:bg-primary data-[state=active]:text-white"
                data-testid={`category-${cat.value}`}
              >
                {cat.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
          {filteredItems.map((item, index) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="menu-card bg-white rounded-xl overflow-hidden"
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
              <div className="p-6">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-playfair text-xl font-semibold text-foreground mb-1">
                      {item.name}
                    </h3>
                    {item.is_veg && (
                      <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                        Veg
                      </Badge>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="font-manrope text-xl font-semibold text-primary">
                      ₹{item.price}
                    </p>
                  </div>
                </div>
                <p className="text-foreground/70 font-manrope mb-4 leading-relaxed">
                  {item.description}
                </p>
                <Button
                  onClick={() => handleAddToCart(item)}
                  className="w-full rounded-full bg-primary"
                  disabled={!item.is_available}
                  data-testid={`add-to-cart-${index}`}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  {item.is_available ? 'Add to Cart' : 'Not Available'}
                </Button>
              </div>
            </motion.div>
          ))}
        </div>

        {filteredItems.length === 0 && (
          <div className="text-center py-20">
            <p className="text-lg text-foreground/70 font-manrope">
              No items found in this category
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Menu;