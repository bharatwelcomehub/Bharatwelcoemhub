import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { MapPin, Phone, ExternalLink } from 'lucide-react';
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
      <div className="container mx-auto px-4 lg:px-8 py-20">
        <div className="text-center">Loading locations...</div>
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
          <MapPin className="h-16 w-16 mx-auto text-primary mb-4" />
          <h1 className="font-playfair text-4xl lg:text-6xl font-bold text-foreground mb-4 tracking-tight" data-testid="locations-title">
            Our Locations
          </h1>
          <p className="text-lg text-foreground/70 font-manrope max-w-2xl mx-auto">
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
              className="location-card bg-white rounded-xl p-6 border border-orange-900/10"
              data-testid={`location-card-${index}`}
            >
              <h3 className="font-playfair text-2xl font-semibold text-foreground mb-2">
                {location.name}
              </h3>
              <p className="text-lg text-primary font-manrope font-semibold mb-4">
                {location.city}
              </p>
              
              <div className="space-y-3 mb-6">
                <div className="flex items-start">
                  <MapPin className="h-5 w-5 text-foreground/60 mr-3 mt-0.5 flex-shrink-0" />
                  <p className="text-foreground/70 font-manrope text-sm">
                    {location.address}
                  </p>
                </div>
                
                <div className="flex items-center">
                  <Phone className="h-5 w-5 text-foreground/60 mr-3 flex-shrink-0" />
                  <a
                    href={`tel:${location.phone}`}
                    className="text-foreground/70 font-manrope text-sm hover:text-primary"
                  >
                    {location.phone}
                  </a>
                </div>
              </div>

              <Button
                asChild
                className="w-full rounded-full bg-primary"
                data-testid={`whatsapp-button-${index}`}
              >
                <a
                  href={`https://wa.me/${location.whatsapp.replace(/[^0-9]/g, '')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLink className="mr-2 h-4 w-4" />
                  Contact on WhatsApp
                </a>
              </Button>
            </motion.div>
          ))}
        </div>

        {locations.length === 0 && (
          <div className="text-center py-20">
            <p className="text-lg text-foreground/70 font-manrope">
              No locations available at the moment
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Locations;