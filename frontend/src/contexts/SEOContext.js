import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import centersData from '@/config/centers.json';

const SEOContext = createContext();

// Static data (computed ONCE at module load — NOT on every render)
const ALL_CENTERS = [...centersData.india, ...centersData.australia];

// Center coordinates for distance calculation
const centerCoordinates = {
  'pb-hsr': { lat: 12.9121, lng: 77.6446, city: 'Bangalore' },
  'pb-sambhajinagar': { lat: 19.8762, lng: 75.3433, city: 'Chhatrapati Sambhajinagar' },
  'pb-thane': { lat: 19.2183, lng: 72.9781, city: 'Thane' },
  'pb-dombivli': { lat: 19.2183, lng: 73.0867, city: 'Dombivli' },
  'pb-kharadi': { lat: 18.5530, lng: 73.9422, city: 'Pune' },
  'pb-hinjawadi': { lat: 18.5912, lng: 73.7380, city: 'Pune' },
  'pb-kalyan': { lat: 19.2437, lng: 73.1355, city: 'Kalyan' },
  'pb-perth': { lat: -31.9505, lng: 115.8605, city: 'Perth' }
};

// Haversine formula to calculate distance between two points
const calculateDistance = (lat1, lon1, lat2, lon2) => {
  const R = 6371; // Earth's radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
    Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
};

// Pure function — does not depend on component state
const findNearestCenterFn = (lat, lng) => {
  let nearest = null;
  let minDistance = Infinity;

  Object.entries(centerCoordinates).forEach(([centerId, coords]) => {
    const distance = calculateDistance(lat, lng, coords.lat, coords.lng);
    if (distance < minDistance) {
      minDistance = distance;
      nearest = {
        ...ALL_CENTERS.find(c => c.id === centerId),
        distance: Math.round(distance),
        coordinates: coords
      };
    }
  });

  return nearest;
};

export const SEOProvider = ({ children }) => {
  const [userLocation, setUserLocation] = useState(null);
  const [nearestCenter, setNearestCenter] = useState(null);
  const [currentCity, setCurrentCity] = useState('India & Australia');
  const [locationPermission, setLocationPermission] = useState('prompt'); // 'prompt', 'granted', 'denied'
  const [showLocationBanner, setShowLocationBanner] = useState(true);
  const [locationLoading, setLocationLoading] = useState(false);

  // Stable reference (no deps — uses module-level constants)
  const findNearestCenter = useCallback((lat, lng) => findNearestCenterFn(lat, lng), []);

  // Request location permission
  const requestLocationPermission = useCallback(() => {
    if (!navigator.geolocation) {
      setLocationPermission('denied');
      return;
    }

    setLocationLoading(true);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setUserLocation({ lat: latitude, lng: longitude });
        setLocationPermission('granted');
        
        const nearest = findNearestCenterFn(latitude, longitude);
        if (nearest) {
          setNearestCenter(nearest);
          setCurrentCity(nearest.city);
        }
        
        setLocationLoading(false);
        setShowLocationBanner(false);
        
        // Store in localStorage
        localStorage.setItem('purnabramha_location', JSON.stringify({
          lat: latitude,
          lng: longitude,
          timestamp: Date.now()
        }));
      },
      (error) => {
        console.log('Location permission denied:', error);
        setLocationPermission('denied');
        setLocationLoading(false);
      },
      {
        enableHighAccuracy: false,
        timeout: 10000,
        maximumAge: 600000 // 10 minutes
      }
    );
  }, []);

  // Check for stored location on mount (runs ONCE)
  useEffect(() => {
    const stored = localStorage.getItem('purnabramha_location');
    if (stored) {
      try {
        const { lat, lng, timestamp } = JSON.parse(stored);
        // Use stored location if less than 24 hours old
        if (Date.now() - timestamp < 24 * 60 * 60 * 1000) {
          setUserLocation({ lat, lng });
          setLocationPermission('granted');
          const nearest = findNearestCenterFn(lat, lng);
          if (nearest) {
            setNearestCenter(nearest);
            setCurrentCity(nearest.city);
          }
          setShowLocationBanner(false);
        }
      } catch (e) {
        console.error('Error parsing stored location:', e);
      }
    }
  }, []);  // ← empty deps so this only runs ONCE on mount, NOT on every render

  // Dismiss location banner
  const dismissLocationBanner = () => {
    setShowLocationBanner(false);
    localStorage.setItem('purnabramha_location_dismissed', 'true');
  };

  // Check if banner was previously dismissed
  useEffect(() => {
    const dismissed = localStorage.getItem('purnabramha_location_dismissed');
    if (dismissed === 'true') {
      setShowLocationBanner(false);
    }
  }, []);

  // Generate SEO-friendly city text
  const getSEOCity = () => {
    if (nearestCenter) {
      return nearestCenter.city;
    }
    return 'India & Australia';
  };

  // Get all unique cities for internal linking
  const getAllCities = () => {
    const cities = new Set();
    ALL_CENTERS.forEach(center => {
      cities.add(center.city);
    });
    return Array.from(cities);
  };

  const value = {
    userLocation,
    nearestCenter,
    currentCity,
    locationPermission,
    showLocationBanner,
    locationLoading,
    requestLocationPermission,
    dismissLocationBanner,
    getSEOCity,
    getAllCities,
    allCenters: ALL_CENTERS
  };

  return (
    <SEOContext.Provider value={value}>
      {children}
    </SEOContext.Provider>
  );
};

export const useSEO = () => {
  const context = useContext(SEOContext);
  if (!context) {
    throw new Error('useSEO must be used within SEOProvider');
  }
  return context;
};

export default SEOContext;
