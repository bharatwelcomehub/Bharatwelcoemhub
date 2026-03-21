import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { 
  UtensilsCrossed, MapPin, Phone, Clock, Star, ChevronRight, 
  Play, Award, Users, Heart, ArrowRight, Sparkles, Calendar, 
  ShoppingBag, PartyPopper, Coffee
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import SEOHead from '@/components/SEOHead';
import { useSEO } from '@/contexts/SEOContext';

const API = process.env.REACT_APP_BACKEND_URL;

const Home = () => {
  const [heroData, setHeroData] = useState(null);
  const [featuredItems, setFeaturedItems] = useState([]);
  const [locations, setLocations] = useState([]);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [festivalTheme, setFestivalTheme] = useState(null);
  const { currentCity } = useSEO();

  const featuredDishes = [
    {
      id: 1,
      name: "Kaju Curry",
      description: "Rich cashew curry with aromatic spices",
      price: "₹479",
      image: "https://lh3.googleusercontent.com/d/1rYkehXEPrE9I4jf1QnaICJscFd3Vso2v",
      tag: "Bestseller"
    },
    {
      id: 2,
      name: "Vangyacha Bharit",
      description: "Smoky roasted eggplant mash",
      price: "₹379",
      image: "https://lh3.googleusercontent.com/d/1RwL7pG0gZa6VlRY_hdPJAUfXNKCezU2V",
      tag: "Popular"
    },
    {
      id: 3,
      name: "Maswadi Rassa",
      description: "Traditional spicy curry with maswadi",
      price: "₹399",
      image: "https://lh3.googleusercontent.com/d/168pHmUxU4vyqA4DrplT0_9R_DDK9eK0c",
      tag: "Spicy"
    },
    {
      id: 4,
      name: "Patodi Rassa",
      description: "Gram flour dumplings in tangy curry",
      price: "₹399",
      image: "https://lh3.googleusercontent.com/d/1VYDK8vRc_hVR4jn1CsabdBL0fFF4EWaH",
      tag: "Chef's Special"
    }
  ];

  const stats = [
    { icon: MapPin, value: "8+", label: "Locations" },
    { icon: Users, value: "50K+", label: "Happy Customers" },
    { icon: UtensilsCrossed, value: "150+", label: "Menu Items" },
    { icon: Star, value: "4.8", label: "Average Rating" }
  ];

  const services = [
    {
      icon: UtensilsCrossed,
      title: "Dine In",
      description: "Experience authentic flavors in our premium ambiance",
      link: "/table-booking",
      cta: "Book Table",
      color: "from-amber-500 to-orange-600"
    },
    {
      icon: ShoppingBag,
      title: "Pickup Orders",
      description: "Order ahead, skip the queue, enjoy fresh food",
      link: "/pickup",
      cta: "Order Now",
      color: "from-emerald-500 to-teal-600"
    },
    {
      icon: Coffee,
      title: "Tiffin Service",
      description: "Daily home-style meals delivered to your doorstep",
      link: "/tiffin",
      cta: "Subscribe",
      color: "from-blue-500 to-indigo-600"
    },
    {
      icon: PartyPopper,
      title: "Catering",
      description: "Make your events memorable with our authentic cuisine",
      link: "/catering",
      cta: "Enquire",
      color: "from-purple-500 to-pink-600"
    }
  ];

  const testimonials = [
    {
      name: "Priya Sharma",
      location: "Bangalore",
      text: "Best Maharashtrian food outside Maharashtra! The thali reminds me of my grandmother's cooking.",
      rating: 5
    },
    {
      name: "Amit Patel",
      location: "Mumbai",
      text: "Finally found authentic Kolhapuri misal in the city. The spice level is perfect!",
      rating: 5
    },
    {
      name: "Sarah Mitchell",
      location: "Perth",
      text: "Amazing vegetarian options! The flavors are so authentic. Our go-to Indian restaurant.",
      rating: 5
    }
  ];

  useEffect(() => {
    fetchHeroData();
    fetchLocations();
    fetchFestivalTheme();
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % testimonials.length);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  const fetchHeroData = async () => {
    try {
      const response = await axios.get(`${API}/api/hero-image`);
      setHeroData(response.data);
    } catch (error) {
      console.error('Failed to fetch hero data');
    }
  };

  const fetchLocations = async () => {
    try {
      const response = await axios.get(`${API}/api/locations`);
      setLocations(response.data.slice(0, 4));
    } catch (error) {
      console.error('Failed to fetch locations');
    }
  };

  const fetchFestivalTheme = async () => {
    try {
      const response = await axios.get(`${API}/api/festival-theme`);
      if (response.data && response.data.is_active) {
        setFestivalTheme(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch festival theme');
    }
  };

  return (
    <div className="min-h-screen bg-[#faf8f5]">
      {/* SEO Head - Dynamic Meta Tags */}
      <SEOHead page="home" />
      
      {/* Festival Theme Banner */}
      {festivalTheme && festivalTheme.is_active && (
        <motion.div
          initial={{ y: -100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="relative overflow-hidden"
          style={{
            background: `linear-gradient(135deg, ${festivalTheme.primary_color}, ${festivalTheme.secondary_color}, ${festivalTheme.accent_color})`
          }}
        >
          {/* Decorative patterns */}
          <div className="absolute inset-0 opacity-20">
            <div className="absolute top-0 left-0 w-full h-full" 
              style={{
                backgroundImage: `repeating-linear-gradient(45deg, transparent, transparent 35px, rgba(255,255,255,0.1) 35px, rgba(255,255,255,0.1) 70px)`
              }}
            />
          </div>
          
          {/* Floating decorations */}
          <motion.div
            className="absolute left-10 top-1/2 -translate-y-1/2 text-4xl"
            animate={{ rotate: [0, 10, -10, 0], scale: [1, 1.1, 1] }}
            transition={{ duration: 3, repeat: Infinity }}
          >
            ✨
          </motion.div>
          <motion.div
            className="absolute right-10 top-1/2 -translate-y-1/2 text-4xl"
            animate={{ rotate: [0, -10, 10, 0], scale: [1, 1.1, 1] }}
            transition={{ duration: 3, repeat: Infinity, delay: 0.5 }}
          >
            🎊
          </motion.div>

          <div className="container mx-auto px-4 py-4 text-center relative z-10">
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.5 }}
              className="flex items-center justify-center gap-3 flex-wrap"
            >
              <span className="text-2xl md:text-3xl">🪔</span>
              <div>
                <h2 className="text-white font-bold text-lg md:text-xl tracking-wide drop-shadow-lg">
                  {festivalTheme.name}
                </h2>
                {festivalTheme.greeting_text && (
                  <p className="text-white/90 text-sm md:text-base font-medium">
                    {festivalTheme.greeting_text}
                  </p>
                )}
              </div>
              <span className="text-2xl md:text-3xl">🪔</span>
            </motion.div>
          </div>

          {/* Bottom wave decoration */}
          <svg className="absolute bottom-0 left-0 w-full" height="6" viewBox="0 0 1200 6" preserveAspectRatio="none">
            <path d="M0,6 C300,0 600,6 900,0 C1050,3 1200,6 1200,6 L0,6 Z" fill="rgba(250,248,245,0.3)" />
          </svg>
        </motion.div>
      )}

      {/* Hero Section - Full Screen with Video/Image Background */}
      <section className="relative h-screen min-h-[700px] overflow-hidden">
        {/* Background */}
        <div className="absolute inset-0">
          <div 
            className="absolute inset-0 bg-cover bg-center bg-no-repeat"
            style={{
              backgroundImage: `url(${heroData?.image_url || 'https://lh3.googleusercontent.com/d/1IiJw4VxwbygR2WXSymVgd9S7FoIfrdil'})`
            }}
          />
          <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/50 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/30" />
        </div>

        {/* Floating Decorative Elements */}
        <motion.div 
          className="absolute top-20 right-20 w-32 h-32 rounded-full bg-amber-500/10 blur-3xl"
          animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.5, 0.3] }}
          transition={{ duration: 4, repeat: Infinity }}
        />
        <motion.div 
          className="absolute bottom-40 left-20 w-48 h-48 rounded-full bg-orange-500/10 blur-3xl"
          animate={{ scale: [1.2, 1, 1.2], opacity: [0.5, 0.3, 0.5] }}
          transition={{ duration: 5, repeat: Infinity }}
        />

        {/* Content */}
        <div className="relative z-10 h-full flex items-center">
          <div className="container mx-auto px-4 lg:px-8">
            <div className="max-w-3xl">
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8 }}
              >
                <Badge className="mb-6 bg-amber-500/20 text-amber-300 border-amber-500/30 px-4 py-1.5 text-sm">
                  <Sparkles className="w-4 h-4 mr-2" />
                  India's Largest Maharashtrian Restaurant Chain
                </Badge>
              </motion.div>

              <motion.h1
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.2 }}
                className="text-5xl md:text-6xl lg:text-7xl font-bold text-white mb-6 leading-tight"
                data-testid="hero-title"
              >
                Authentic Maharashtrian Food in {currentCity}
              </motion.h1>

              <motion.h2
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.3 }}
                className="text-xl md:text-2xl text-amber-300 mb-4 font-semibold"
              >
                Best Vada Pav, Misal Pav & Thali in {currentCity}
              </motion.h2>

              <motion.p
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.4 }}
                className="text-lg md:text-xl text-white/80 mb-8 leading-relaxed"
              >
                {heroData?.description || "Experience the richness of traditional recipes passed down through generations. Pure vegetarian, pure love."}
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.6 }}
                className="flex flex-wrap gap-4"
              >
                <Link to="/table-booking">
                  <Button 
                    size="lg" 
                    className="bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white px-8 py-6 text-lg rounded-full shadow-lg shadow-amber-500/25 group"
                    data-testid="book-table-cta"
                  >
                    <Calendar className="mr-2 h-5 w-5" />
                    Book a Table
                    <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                  </Button>
                </Link>
                <Link to="/pickup">
                  <Button 
                    size="lg" 
                    variant="outline"
                    className="border-2 border-white/30 text-white hover:bg-white/10 px-8 py-6 text-lg rounded-full backdrop-blur-sm"
                    data-testid="order-now-cta"
                  >
                    <ShoppingBag className="mr-2 h-5 w-5" />
                    Order Pickup
                  </Button>
                </Link>
              </motion.div>

              {/* Quick Stats */}
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.8 }}
                className="mt-12 flex flex-wrap gap-8"
              >
                {stats.map((stat, index) => (
                  <div key={index} className="text-white/90">
                    <div className="flex items-center gap-2 mb-1">
                      <stat.icon className="h-5 w-5 text-amber-400" />
                      <span className="text-3xl font-bold">{stat.value}</span>
                    </div>
                    <span className="text-white/60 text-sm">{stat.label}</span>
                  </div>
                ))}
              </motion.div>
            </div>
          </div>
        </div>

        {/* Scroll Indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2 text-white/60"
        >
          <motion.div
            animate={{ y: [0, 10, 0] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="flex flex-col items-center"
          >
            <span className="text-xs mb-2">Scroll to explore</span>
            <ChevronRight className="h-6 w-6 rotate-90" />
          </motion.div>
        </motion.div>
      </section>

      {/* Services Section */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <Badge className="mb-4 bg-amber-100 text-amber-700">Our Services</Badge>
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              How Would You Like to <span className="text-amber-600">Enjoy?</span>
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Multiple ways to experience authentic Maharashtrian cuisine
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {services.map((service, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <Link to={service.link}>
                  <Card className="h-full group cursor-pointer border-0 shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden">
                    <CardContent className="p-6 relative">
                      <div className={`absolute inset-0 bg-gradient-to-br ${service.color} opacity-0 group-hover:opacity-100 transition-opacity duration-300`} />
                      <div className="relative z-10">
                        <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${service.color} flex items-center justify-center mb-4 group-hover:bg-white/20 transition-colors`}>
                          <service.icon className="h-7 w-7 text-white" />
                        </div>
                        <h3 className="text-xl font-bold mb-2 group-hover:text-white transition-colors">
                          {service.title}
                        </h3>
                        <p className="text-gray-600 mb-4 group-hover:text-white/80 transition-colors">
                          {service.description}
                        </p>
                        <div className="flex items-center text-amber-600 font-semibold group-hover:text-white transition-colors">
                          {service.cta}
                          <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-2 transition-transform" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Featured Dishes */}
      <section className="py-20 bg-gradient-to-b from-amber-50 to-white">
        <div className="container mx-auto px-4 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <Badge className="mb-4 bg-amber-100 text-amber-700">Featured Menu</Badge>
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Our <span className="text-amber-600">Signature Dishes</span>
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Handcrafted with love, served with tradition
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {featuredDishes.map((dish, index) => (
              <motion.div
                key={dish.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="group"
              >
                <Card className="overflow-hidden border-0 shadow-lg hover:shadow-2xl transition-all duration-300">
                  <div className="relative h-48 overflow-hidden">
                    <img 
                      src={dish.image} 
                      alt={dish.name}
                      className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                    <Badge className="absolute top-3 right-3 bg-amber-500 text-white">
                      {dish.tag}
                    </Badge>
                    <div className="absolute bottom-3 left-3 text-white">
                      <p className="text-2xl font-bold">{dish.price}</p>
                    </div>
                  </div>
                  <CardContent className="p-4">
                    <h3 className="text-lg font-bold text-gray-900 mb-1">{dish.name}</h3>
                    <p className="text-gray-600 text-sm">{dish.description}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          <div className="text-center mt-12">
            <Link to="/menu">
              <Button size="lg" className="bg-amber-600 hover:bg-amber-700 rounded-full px-8">
                View Full Menu
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Special Offer Banner */}
      <section className="py-12 bg-gradient-to-r from-[#5c1e1e] to-[#8b2c2c]">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="text-white">
              <Badge className="mb-3 bg-amber-500/20 text-amber-300 border-amber-500/30">
                <Sparkles className="w-4 h-4 mr-1" />
                Special Offer
              </Badge>
              <h3 className="text-3xl md:text-4xl font-bold mb-2">
                Unlimited Breakfast Buffet
              </h3>
              <p className="text-white/80 text-lg">
                Every Saturday & Sunday • 8 AM - 11 AM • Only ₹299/person
              </p>
            </div>
            <Link to="/tiffin">
              <Button size="lg" className="bg-white text-[#5c1e1e] hover:bg-amber-50 rounded-full px-8 py-6 text-lg">
                Book Now
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <Badge className="mb-4 bg-amber-100 text-amber-700">Testimonials</Badge>
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              What Our <span className="text-amber-600">Guests Say</span>
            </h2>
          </motion.div>

          <div className="max-w-4xl mx-auto relative">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentSlide}
                initial={{ opacity: 0, x: 50 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -50 }}
                transition={{ duration: 0.5 }}
                className="text-center"
              >
                <div className="flex justify-center mb-4">
                  {[...Array(testimonials[currentSlide].rating)].map((_, i) => (
                    <Star key={i} className="h-6 w-6 text-amber-500 fill-amber-500" />
                  ))}
                </div>
                <p className="text-2xl md:text-3xl text-gray-700 italic mb-6 leading-relaxed">
                  "{testimonials[currentSlide].text}"
                </p>
                <div>
                  <p className="font-bold text-xl text-gray-900">{testimonials[currentSlide].name}</p>
                  <p className="text-gray-500">{testimonials[currentSlide].location}</p>
                </div>
              </motion.div>
            </AnimatePresence>

            {/* Dots */}
            <div className="flex justify-center gap-2 mt-8">
              {testimonials.map((_, index) => (
                <button
                  key={index}
                  onClick={() => setCurrentSlide(index)}
                  className={`w-3 h-3 rounded-full transition-all ${
                    currentSlide === index ? 'bg-amber-600 w-8' : 'bg-amber-200'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Locations */}
      <section className="py-20 bg-gradient-to-b from-white to-amber-50">
        <div className="container mx-auto px-4 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <Badge className="mb-4 bg-amber-100 text-amber-700">Visit Us</Badge>
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Find Us <span className="text-amber-600">Near You</span>
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              8+ locations across India & Australia
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
            {[
              { city: "Bangalore", area: "HSR Layout", phone: "+91 85500 78515" },
              { city: "Mumbai", area: "Thane", phone: "+91 89047 49084" },
              { city: "Pune", area: "Kharadi", phone: "9900089803" },
              { city: "Perth", area: "Australia", phone: "+61 401 832 922" }
            ].map((loc, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="h-full border-0 shadow-lg hover:shadow-xl transition-shadow">
                  <CardContent className="p-6">
                    <div className="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center mb-4">
                      <MapPin className="h-6 w-6 text-amber-600" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-1">{loc.city}</h3>
                    <p className="text-gray-600 mb-3">{loc.area}</p>
                    <a href={`tel:${loc.phone.replace(/\s/g, '')}`} className="flex items-center text-amber-600 hover:text-amber-700">
                      <Phone className="h-4 w-4 mr-2" />
                      {loc.phone}
                    </a>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          <div className="text-center">
            <Link to="/locations">
              <Button variant="outline" size="lg" className="border-amber-600 text-amber-600 hover:bg-amber-50 rounded-full px-8">
                View All Locations
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 bg-gradient-to-r from-[#5c1e1e] to-[#8b2c2c] text-white">
        <div className="container mx-auto px-4 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6">
              Ready to Experience <br />
              <span className="text-amber-400">Authentic Maharashtra?</span>
            </h2>
            <p className="text-xl text-white/80 mb-8 max-w-2xl mx-auto">
              Book your table now or order for pickup. Your taste buds will thank you!
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Link to="/table-booking">
                <Button size="lg" className="bg-amber-500 hover:bg-amber-600 text-white rounded-full px-8 py-6 text-lg">
                  <Calendar className="mr-2 h-5 w-5" />
                  Reserve Table
                </Button>
              </Link>
              <Link to="/pickup">
                <Button size="lg" variant="outline" className="border-2 border-white text-white hover:bg-white/10 rounded-full px-8 py-6 text-lg">
                  <ShoppingBag className="mr-2 h-5 w-5" />
                  Order Pickup
                </Button>
              </Link>
              <Link to="/tiffin">
                <Button size="lg" variant="outline" className="border-2 border-amber-400 text-amber-400 hover:bg-amber-400/10 rounded-full px-8 py-6 text-lg">
                  <Coffee className="mr-2 h-5 w-5" />
                  Tiffin Service
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
};

export default Home;
