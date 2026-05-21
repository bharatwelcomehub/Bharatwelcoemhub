import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { MapPin, Phone, ExternalLink, Heart } from 'lucide-react';
import { Button } from '@/components/ui/button';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Locations = () => {
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLocations();
  }, []);

  const fetchLocations = async () => {
    try {
      const response = await axios.get(`${API}/locations`);
      setLocations(response.data);
    } catch (error) {
      console.error('Failed to fetch locations:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FDFBF7] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#B8962E] mx-auto mb-4"></div>
          <p className="text-[#7A6F65] font-body">Loading locations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FDFBF7]">
      <div className="container mx-auto px-6 lg:px-12 py-16 lg:py-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-16"
        >
          <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-4">Visit Us</p>
          <h1 className="font-heading text-5xl md:text-6xl lg:text-7xl font-medium text-[#2D1810] mb-4 tracking-tight" data-testid="locations-title">
            Our <span className="text-gold-shimmer">Locations</span>
          </h1>
          <p className="text-lg text-[#5C4A3A] font-body max-w-2xl mx-auto">
            Find a Purnabramha restaurant near you across India and Australia
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {locations.map((location, index) => (
            <motion.div
              key={location.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="pearl-surface p-8 hover:border-[#B8962E]/30 transition-all hover:-translate-y-1 hover:shadow-lg"
              data-testid={`location-card-${index}`}
            >
              <MapPin className="h-6 w-6 text-[#B8962E] mb-4" />
              <h3 className="font-heading text-2xl font-medium text-[#2D1810] mb-1">{location.name}</h3>
              <p className="text-[#B8962E] font-body font-semibold mb-4">{location.city}</p>

              <div className="space-y-3 mb-6">
                <div className="flex items-start">
                  <MapPin className="h-4 w-4 text-[#7A6F65] mr-3 mt-0.5 flex-shrink-0" />
                  <p className="text-[#5C4A3A] font-body text-sm">{location.address}</p>
                </div>
                <div className="flex items-center">
                  <Phone className="h-4 w-4 text-[#7A6F65] mr-3 flex-shrink-0" />
                  <a href={`tel:${location.phone}`} className="text-[#5C4A3A] font-body text-sm hover:text-[#B8962E] transition-colors">
                    {location.phone}
                  </a>
                </div>
              </div>

              <div className="space-y-2">
                <Button asChild className="w-full gold-glossy text-white rounded-none text-xs tracking-widest uppercase font-semibold border-0" data-testid={`whatsapp-button-${index}`}>
                  <a href={`https://wa.me/${location.whatsapp.replace(/[^0-9]/g, '')}`} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="mr-2 h-4 w-4" /> Contact on WhatsApp
                  </a>
                </Button>
                {location.google_review_link && (
                  <Button asChild variant="outline" className="w-full border-[#B8962E]/30 text-[#B8962E] hover:bg-[#B8962E]/10 rounded-none text-xs tracking-widest uppercase" data-testid={`review-button-${index}`}>
                    <a href={location.google_review_link} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="mr-2 h-4 w-4" /> Leave a Google Review
                    </a>
                  </Button>
                )}
                <Button asChild variant="outline" className="w-full border-[#B8962E]/30 text-[#B8962E] hover:bg-[#B8962E]/10 rounded-none text-xs tracking-widest uppercase" data-testid={`feedback-button-${index}`}>
                  <Link to={`/guest-card?center=${location.center_id || location.id}`}>
                    <Heart className="mr-2 h-4 w-4" /> Share Feedback & Get Discount
                  </Link>
                </Button>
              </div>
            </motion.div>
          ))}
        </div>

        {locations.length === 0 && (
          <div className="text-center py-20">
            <p className="text-lg text-[#5C4A3A] font-body">No locations available at the moment</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Locations;
