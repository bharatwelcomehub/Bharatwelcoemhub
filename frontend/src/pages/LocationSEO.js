import { useEffect, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { MapPin, Phone, Clock, Utensils, Calendar, Navigation, Star, ChefHat } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

import seoConfig from '@/config/seo-config.json';

const LocationSEO = () => {
  const { locationSlug } = useParams();
  const navigate = useNavigate();
  
  // Get slug from URL path
  const currentPath = window.location.pathname.replace(/^\//, '').split('?')[0];

  // Find location data from slug
  const locationData = useMemo(() => {
    const locations = seoConfig.locations;
    const slugToFind = locationSlug || currentPath;
    for (const key in locations) {
      if (locations[key].slug === slugToFind) {
        return locations[key];
      }
    }
    return null;
  }, [locationSlug, currentPath]);

  // Set document title and meta tags
  useEffect(() => {
    if (locationData) {
      document.title = locationData.seoTitle;
      
      // Update meta description
      let metaDesc = document.querySelector('meta[name="description"]');
      if (metaDesc) metaDesc.setAttribute('content', locationData.metaDescription);
      
      // Update meta keywords
      let metaKeywords = document.querySelector('meta[name="keywords"]');
      if (!metaKeywords) {
        metaKeywords = document.createElement('meta');
        metaKeywords.name = 'keywords';
        document.head.appendChild(metaKeywords);
      }
      metaKeywords.setAttribute('content', locationData.localKeywords.join(', '));
      
      // Add JSON-LD schema
      const existingSchema = document.querySelector('#location-schema');
      if (existingSchema) existingSchema.remove();
      
      const schema = document.createElement('script');
      schema.id = 'location-schema';
      schema.type = 'application/ld+json';
      schema.textContent = JSON.stringify({
        "@context": "https://schema.org",
        "@type": "Restaurant",
        "name": locationData.name,
        "image": "https://www.purnabramha.com/logo.png",
        "url": `https://www.purnabramha.com/${locationData.slug}`,
        "telephone": locationData.phone,
        "servesCuisine": ["Maharashtrian", "Marathi", "Indian", "Vegetarian"],
        "address": {
          "@type": "PostalAddress",
          "streetAddress": locationData.fullAddress,
          "addressLocality": locationData.city,
          "addressRegion": locationData.state,
          "addressCountry": locationData.country
        },
        "geo": {
          "@type": "GeoCoordinates",
          "latitude": locationData.coordinates.lat,
          "longitude": locationData.coordinates.lng
        }
      });
      document.head.appendChild(schema);
    }
    
    return () => {
      // Cleanup schema on unmount
      const existingSchema = document.querySelector('#location-schema');
      if (existingSchema) existingSchema.remove();
    };
  }, [locationData]);

  useEffect(() => {
    if (!locationData) {
      navigate('/locations');
    }
  }, [locationData, navigate]);

  if (!locationData) {
    return (
      <div className="min-h-screen bg-[#FDFBF7] flex items-center justify-center">
        <p className="text-[#5C4A3A] font-body">Loading location...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FDFBF7]">
      {/* Hero Section */}
      <section className="relative py-16 lg:py-24 bg-gradient-to-br from-[#3D2314] to-[#2D1810] overflow-hidden">
        <div className="absolute inset-0 opacity-5">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_#D4AF37_1px,_transparent_1px)] bg-[length:24px_24px]" />
        </div>
        <div className="relative container mx-auto px-6 lg:px-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-4xl"
          >
            <p className="text-xs tracking-[0.3em] uppercase text-[#D4AF37] font-body font-bold mb-4">
              Purnabramha {locationData.city}
            </p>
            <h1 className="font-heading text-4xl md:text-5xl lg:text-6xl font-medium text-white mb-6 leading-tight" data-testid="location-h1">
              {locationData.h1}
            </h1>
            <p className="text-lg text-white/80 font-body mb-8 max-w-2xl">
              Experience authentic Maharashtrian cuisine at our {locationData.displayName} location. 
              Traditional recipes, fresh ingredients, and the taste of Maharashtra.
            </p>
            <div className="flex flex-wrap gap-4">
              <Button 
                onClick={() => navigate('/table-booking')}
                className="gold-glossy text-[#3D2314] font-bold rounded-none px-8 py-6 text-sm tracking-widest uppercase"
                data-testid="book-table-btn"
              >
                <Calendar className="h-5 w-5 mr-2" /> Book a Table
              </Button>
              <Button 
                onClick={() => window.open(`tel:${locationData.phone}`, '_self')}
                variant="outline"
                className="border-[#D4AF37] text-[#D4AF37] hover:bg-[#D4AF37]/10 rounded-none px-8 py-6 text-sm tracking-widest uppercase"
                data-testid="call-btn"
              >
                <Phone className="h-5 w-5 mr-2" /> Call Now
              </Button>
              <Button 
                onClick={() => navigate('/menu')}
                variant="outline"
                className="border-white/30 text-white hover:bg-white/10 rounded-none px-8 py-6 text-sm tracking-widest uppercase"
                data-testid="view-menu-btn"
              >
                <Utensils className="h-5 w-5 mr-2" /> View Menu
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Quick Info Cards */}
      <section className="py-12 -mt-8">
        <div className="container mx-auto px-6 lg:px-12">
          <div className="grid md:grid-cols-3 gap-6">
            <Card className="pearl-surface border-[#E8DFD0] rounded-none shadow-lg">
              <CardContent className="p-6 flex items-start gap-4">
                <div className="w-12 h-12 bg-[#B8962E]/10 rounded-full flex items-center justify-center flex-shrink-0">
                  <MapPin className="h-6 w-6 text-[#B8962E]" />
                </div>
                <div>
                  <h3 className="font-heading font-semibold text-[#2D1810] mb-1">Address</h3>
                  <p className="text-sm text-[#5C4A3A] font-body">{locationData.fullAddress}</p>
                  <a 
                    href={locationData.googleMapsUrl} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-xs text-[#B8962E] hover:underline mt-2 inline-flex items-center gap-1"
                  >
                    <Navigation className="h-3 w-3" /> Get Directions
                  </a>
                </div>
              </CardContent>
            </Card>

            <Card className="pearl-surface border-[#E8DFD0] rounded-none shadow-lg">
              <CardContent className="p-6 flex items-start gap-4">
                <div className="w-12 h-12 bg-[#B8962E]/10 rounded-full flex items-center justify-center flex-shrink-0">
                  <Clock className="h-6 w-6 text-[#B8962E]" />
                </div>
                <div>
                  <h3 className="font-heading font-semibold text-[#2D1810] mb-1">Opening Hours</h3>
                  {locationData.openingHours.map((oh, idx) => (
                    <p key={idx} className="text-sm text-[#5C4A3A] font-body">
                      {oh.day}: {oh.hours}
                    </p>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="pearl-surface border-[#E8DFD0] rounded-none shadow-lg">
              <CardContent className="p-6 flex items-start gap-4">
                <div className="w-12 h-12 bg-[#B8962E]/10 rounded-full flex items-center justify-center flex-shrink-0">
                  <Phone className="h-6 w-6 text-[#B8962E]" />
                </div>
                <div>
                  <h3 className="font-heading font-semibold text-[#2D1810] mb-1">Contact</h3>
                  <p className="text-sm text-[#5C4A3A] font-body">{locationData.phone}</p>
                  <a 
                    href={`https://wa.me/${locationData.whatsapp.replace(/[^0-9]/g, '')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-[#B8962E] hover:underline mt-2 inline-block"
                  >
                    WhatsApp for Reservations
                  </a>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Google Map */}
      <section className="py-12 bg-[#F8F5F0]">
        <div className="container mx-auto px-6 lg:px-12">
          <h2 className="font-heading text-3xl font-medium text-[#2D1810] mb-8 text-center">
            Find Us in {locationData.city}
          </h2>
          <div className="aspect-video rounded-none overflow-hidden border border-[#E8DFD0] shadow-lg">
            <iframe
              src={`https://www.google.com/maps/embed/v1/place?key=AIzaSyBFw0Qbyq9zTFTd-tUY6dZWTgaQzuU17R8&q=Purnabramha+${encodeURIComponent(locationData.city)}&zoom=15`}
              width="100%"
              height="100%"
              style={{ border: 0 }}
              allowFullScreen
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
              title={`Purnabramha ${locationData.city} Map`}
            />
          </div>
        </div>
      </section>

      {/* Nearby Areas SEO Section */}
      <section className="py-16">
        <div className="container mx-auto px-6 lg:px-12">
          <h2 className="font-heading text-3xl font-medium text-[#2D1810] mb-4 text-center">
            Serving Maharashtrian Food Near You
          </h2>
          <p className="text-center text-[#5C4A3A] font-body mb-10 max-w-2xl mx-auto">
            Purnabramha {locationData.city} serves authentic Maharashtrian cuisine to customers 
            from all nearby areas within 10 km radius.
          </p>
          
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-12">
            {locationData.nearbyAreas.map((area, idx) => (
              <div 
                key={idx}
                className="bg-white border border-[#E8DFD0] p-4 hover:border-[#B8962E]/30 transition-colors"
              >
                <h3 className="font-body font-semibold text-[#2D1810] mb-2">
                  Maharashtrian Food Near {area}
                </h3>
                <p className="text-xs text-[#7A6F65] font-body">
                  Looking for authentic Marathi thali, Solkadhi, or Puranpoli near {area}? 
                  Visit Purnabramha {locationData.city} for the best Maharashtrian cuisine.
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Signature Dishes */}
      <section className="py-16 bg-[#F8F5F0]">
        <div className="container mx-auto px-6 lg:px-12">
          <h2 className="font-heading text-3xl font-medium text-[#2D1810] mb-4 text-center">
            Our Signature Maharashtrian Dishes
          </h2>
          <p className="text-center text-[#5C4A3A] font-body mb-10 max-w-2xl mx-auto">
            Experience the authentic flavors of Maharashtra at Purnabramha {locationData.city}
          </p>
          
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { name: 'Maharashtrian Thali', desc: 'Complete traditional meal with dal, bhaji, rice, chapati, and more' },
              { name: 'Solkadhi', desc: 'Refreshing coconut milk drink with kokum, a Konkan specialty' },
              { name: 'Puranpoli', desc: 'Sweet flatbread stuffed with jaggery and chana dal' },
              { name: 'Vada Pav', desc: "Mumbai's iconic street food - spiced potato fritter in bread" },
              { name: 'Misal Pav', desc: 'Spicy sprouted moth beans curry served with bread' },
              { name: 'Thalipith', desc: 'Multi-grain savory pancake, a Maharashtrian breakfast staple' },
              { name: 'Sabudana Khichadi', desc: 'Tapioca pearls with peanuts, perfect for fasting days' },
              { name: 'Shrikhand', desc: 'Creamy sweetened yogurt dessert with cardamom and saffron' }
            ].map((dish, idx) => (
              <Card key={idx} className="pearl-surface border-[#E8DFD0] rounded-none overflow-hidden">
                <CardContent className="p-5">
                  <div className="w-10 h-10 bg-[#B8962E]/10 rounded-full flex items-center justify-center mb-3">
                    <ChefHat className="h-5 w-5 text-[#B8962E]" />
                  </div>
                  <h3 className="font-heading font-semibold text-[#2D1810] mb-2">{dish.name}</h3>
                  <p className="text-xs text-[#5C4A3A] font-body">{dish.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
          
          <div className="text-center mt-10">
            <Button 
              onClick={() => navigate('/menu')}
              className="gold-glossy text-[#3D2314] font-bold rounded-none px-8 py-4"
            >
              View Full Menu
            </Button>
          </div>
        </div>
      </section>

      {/* Services Available */}
      <section className="py-16">
        <div className="container mx-auto px-6 lg:px-12">
          <h2 className="font-heading text-3xl font-medium text-[#2D1810] mb-10 text-center">
            Services Available at {locationData.displayName}
          </h2>
          
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { title: 'Dine-In', desc: 'Enjoy authentic Maharashtrian meals in our comfortable restaurant', link: '/table-booking', icon: Utensils },
              { title: 'Pickup Order', desc: 'Order online and pick up fresh Maharashtrian food', link: '/pickup', icon: Star },
              { title: 'Tiffin Service', desc: 'Daily lunch box delivery with home-style Marathi meals', link: '/tiffin', icon: ChefHat },
              { title: 'Catering', desc: 'Maharashtrian catering for weddings, events & parties', link: '/catering', icon: Calendar }
            ].map((service, idx) => (
              <Link to={service.link} key={idx}>
                <Card className="pearl-surface border-[#E8DFD0] rounded-none h-full hover:border-[#B8962E]/50 transition-colors">
                  <CardContent className="p-6 text-center">
                    <div className="w-14 h-14 bg-[#B8962E]/10 rounded-full flex items-center justify-center mx-auto mb-4">
                      <service.icon className="h-7 w-7 text-[#B8962E]" />
                    </div>
                    <h3 className="font-heading font-semibold text-[#2D1810] mb-2">{service.title}</h3>
                    <p className="text-xs text-[#5C4A3A] font-body">{service.desc}</p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 bg-gradient-to-br from-[#3D2314] to-[#2D1810]">
        <div className="container mx-auto px-6 lg:px-12 text-center">
          <h2 className="font-heading text-3xl md:text-4xl font-medium text-white mb-4">
            Visit Purnabramha {locationData.city} Today
          </h2>
          <p className="text-white/80 font-body mb-8 max-w-xl mx-auto">
            Experience the best Maharashtrian restaurant in {locationData.city}. 
            Book your table now or call us for reservations.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Button 
              onClick={() => navigate('/table-booking')}
              className="gold-glossy text-[#3D2314] font-bold rounded-none px-10 py-6"
            >
              Book a Table
            </Button>
            <Button 
              onClick={() => window.open(`tel:${locationData.phone}`, '_self')}
              variant="outline"
              className="border-white text-white hover:bg-white/10 rounded-none px-10 py-6"
            >
              Call {locationData.phone}
            </Button>
          </div>
        </div>
      </section>

      {/* Other Locations */}
      <section className="py-16">
        <div className="container mx-auto px-6 lg:px-12">
          <h2 className="font-heading text-3xl font-medium text-[#2D1810] mb-10 text-center">
            Other Purnabramha Locations
          </h2>
          
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.values(seoConfig.locations)
              .filter(loc => loc.slug !== locationData.slug)
              .map((loc, idx) => (
                <Link to={`/${loc.slug}`} key={idx}>
                  <div className="bg-white border border-[#E8DFD0] p-4 hover:border-[#B8962E]/50 transition-colors">
                    <h3 className="font-heading font-semibold text-[#2D1810] mb-1">{loc.displayName}</h3>
                    <p className="text-xs text-[#7A6F65] font-body">{loc.phone}</p>
                  </div>
                </Link>
              ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default LocationSEO;
