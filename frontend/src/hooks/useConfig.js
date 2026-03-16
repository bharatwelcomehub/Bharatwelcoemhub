import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

// Static config imports (for non-menu data)
import centersData from '@/config/centers.json';
import bookingRulesData from '@/config/booking-rules.json';
import cateringPackagesData from '@/config/catering-packages.json';
import tiffinConfigData from '@/config/tiffin-config.json';

// Hook to get menu items from database with fallback to JSON
export const useMenuFromDatabase = (region) => {
  const [menuItems, setMenuItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchMenu = async () => {
      setLoading(true);
      try {
        const response = await axios.get(`${API}/api/menu`);
        setMenuItems(response.data);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch menu from database:', err);
        setError(err);
        // Menu will be empty, fallback handled in components
      } finally {
        setLoading(false);
      }
    };
    fetchMenu();
  }, []);

  // Transform database items into categorized format
  const categorizedMenu = useMemo(() => {
    if (!menuItems.length) return { currency: region === 'australia' ? 'AUD' : 'INR', currencySymbol: region === 'australia' ? '$' : '₹', categories: [] };

    const isAustralia = region === 'australia';
    const categoryMap = {};

    menuItems.forEach(item => {
      if (!item.is_available) return;
      
      const price = isAustralia ? (item.price_aud || 0) : (item.price_inr || item.price || 0);
      if (price <= 0) return;

      if (!categoryMap[item.category]) {
        categoryMap[item.category] = {
          id: item.category.toLowerCase().replace(/[^a-z0-9]/g, '-'),
          name: item.category,
          description: '',
          items: []
        };
      }

      categoryMap[item.category].items.push({
        id: item.id,
        name: item.name,
        price: price,
        isVeg: item.is_veg ?? true,
        description: item.description,
        image_url: item.image_url
      });
    });

    return {
      currency: isAustralia ? 'AUD' : 'INR',
      currencySymbol: isAustralia ? '$' : '₹',
      categories: Object.values(categoryMap)
    };
  }, [menuItems, region]);

  return { menuData: categorizedMenu, loading, error, rawItems: menuItems };
};

// Hook to get centers
export const useCenters = () => {
  return {
    india: centersData.india,
    australia: centersData.australia,
    all: [...centersData.india, ...centersData.australia]
  };
};

// Hook to get booking rules
export const useBookingRules = () => {
  return bookingRulesData;
};

// Hook to get catering packages
export const useCateringPackages = (region) => {
  const isAustralia = region === 'australia';
  return {
    packages: isAustralia ? cateringPackagesData.packages.australia : cateringPackagesData.packages.india,
    menuOptions: cateringPackagesData.menuOptions
  };
};

// Hook to get tiffin config
export const useTiffinConfig = (region) => {
  const isAustralia = region === 'australia';
  return {
    pricing: isAustralia ? tiffinConfigData.pricing.australia : tiffinConfigData.pricing.india,
    heavyBrunchItems: isAustralia ? tiffinConfigData.heavyBrunchItems.australia : tiffinConfigData.heavyBrunchItems.india,
    drinkAddons: isAustralia ? tiffinConfigData.drinkAddons.australia : tiffinConfigData.drinkAddons.india,
    lunchBoxOptions: isAustralia ? tiffinConfigData.lunchBoxOptions.australia : tiffinConfigData.lunchBoxOptions.india,
    unlimitedBreakfast: tiffinConfigData.unlimitedBreakfast,
    blackoutDates: tiffinConfigData.blackoutDates
  };
};

export default {
  useMenuFromDatabase,
  useCenters,
  useBookingRules,
  useCateringPackages,
  useTiffinConfig
};
