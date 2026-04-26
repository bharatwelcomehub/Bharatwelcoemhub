import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { 
  UtensilsCrossed, MapPin, Phone, Star, ChevronRight, 
  Play, Users, ArrowRight, Calendar, 
  ShoppingBag, PartyPopper, Coffee, BookOpen, Leaf
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import SEOHead from '@/components/SEOHead';
import { useSEO } from '@/contexts/SEOContext';

const API = process.env.REACT_APP_BACKEND_URL;

const Home = () => {
  const [festivalTheme, setFestivalTheme] = useState(null);
  const [heroImage, setHeroImage] = useState(null);
  const [currentSlide, setCurrentSlide] = useState(0);
  const { currentCity } = useSEO();
  
  // Default hero image fallback
  const defaultHeroImage = "https://images.pexels.com/photos/958545/pexels-photo-958545.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=750&w=1260";

  const featuredDishes = [
    { id: 1, name: "Kaju Curry", description: "Rich cashew curry with aromatic spices", price: "479", image: "https://lh3.googleusercontent.com/d/1rYkehXEPrE9I4jf1QnaICJscFd3Vso2v", tag: "Bestseller" },
    { id: 2, name: "Vangyacha Bharit", description: "Smoky roasted eggplant mash", price: "379", image: "https://lh3.googleusercontent.com/d/1RwL7pG0gZa6VlRY_hdPJAUfXNKCezU2V", tag: "Popular" },
    { id: 3, name: "Maswadi Rassa", description: "Traditional spicy curry with maswadi", price: "399", image: "https://lh3.googleusercontent.com/d/168pHmUxU4vyqA4DrplT0_9R_DDK9eK0c", tag: "Spicy" },
    { id: 4, name: "Patodi Rassa", description: "Gram flour dumplings in tangy curry", price: "399", image: "https://lh3.googleusercontent.com/d/1VYDK8vRc_hVR4jn1CsabdBL0fFF4EWaH", tag: "Chef's Special" }
  ];

  const stats = [
    { icon: MapPin, value: "8+", label: "Locations" },
    { icon: Users, value: "50K+", label: "Happy Customers" },
    { icon: UtensilsCrossed, value: "150+", label: "Menu Items" },
    { icon: Star, value: "4.8", label: "Rating" }
  ];

  const services = [
    { icon: UtensilsCrossed, title: "Dine In", description: "Premium ambiance, authentic flavors", link: "/table-booking", cta: "Reserve" },
    { icon: ShoppingBag, title: "Pickup", description: "Order ahead, skip the queue", link: "/pickup", cta: "Order" },
    { icon: Coffee, title: "Tiffin", description: "Daily home-style meals delivered", link: "/tiffin", cta: "Subscribe" },
    { icon: PartyPopper, title: "Catering", description: "Events made memorable", link: "/catering", cta: "Enquire" }
  ];

  const testimonials = [
    { name: "Priya Sharma", location: "Bangalore", text: "Best Maharashtrian food outside Maharashtra! The thali reminds me of my grandmother's cooking.", rating: 5 },
    { name: "Amit Patel", location: "Mumbai", text: "Finally found authentic Kolhapuri misal in the city. The spice level is perfect!", rating: 5 },
    { name: "Sarah Mitchell", location: "Perth", text: "Amazing vegetarian options! The flavors are so authentic. Our go-to Indian restaurant.", rating: 5 }
  ];

  useEffect(() => {
    const fetchFestival = async () => {
      try {
        const res = await axios.get(`${API}/api/festival-theme`);
        if (res.data?.is_active) setFestivalTheme(res.data);
      } catch (e) {}
    };
    fetchFestival();
  }, []);

  // Fetch active hero image from database
  useEffect(() => {
    const fetchHeroImage = async () => {
      try {
        const res = await axios.get(`${API}/api/hero-image`);
        if (res.data) setHeroImage(res.data);
      } catch (e) {
        console.log('Using default hero image');
      }
    };
    fetchHeroImage();
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setCurrentSlide((p) => (p + 1) % testimonials.length), 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen bg-[#FDFBF7]">
      <SEOHead page="home" />
      
      {/* Festival Banner */}
      {festivalTheme?.is_active && (
        <motion.div
          initial={{ y: -50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="relative overflow-hidden py-3"
          style={{ background: `linear-gradient(135deg, ${festivalTheme.primary_color}15, ${festivalTheme.secondary_color}20, ${festivalTheme.accent_color}15)` }}
        >
          <div className="container mx-auto px-4 text-center">
            <span className="font-heading text-lg text-[#B8962E] tracking-wide">{festivalTheme.name}</span>
            {festivalTheme.greeting_text && <span className="text-[#5C4A3A]/70 mx-3">|</span>}
            {festivalTheme.greeting_text && <span className="text-[#5C4A3A]/70 text-sm">{festivalTheme.greeting_text}</span>}
          </div>
        </motion.div>
      )}

      {/* HERO — Elegant Light Theme */}
      <section className="relative min-h-[90vh] overflow-hidden" data-testid="hero-section">
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: `url(${heroImage?.image_url || defaultHeroImage})` }} />
          <div className="absolute inset-0 bg-gradient-to-r from-white/95 via-white/80 to-white/60" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#FDFBF7] via-transparent to-transparent" />
        </div>

        {/* Subtle gold ambient */}
        <motion.div className="absolute top-1/3 right-1/4 w-96 h-96 rounded-full bg-[#D4AF37]/5 blur-[100px]" animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.5, 0.3] }} transition={{ duration: 8, repeat: Infinity }} />

        <div className="relative z-10 h-full flex items-center min-h-[90vh]">
          <div className="container mx-auto px-6 lg:px-12">
            <div className="max-w-3xl">
              <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}
                className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-6">
                World's First Intelligent Restaurant Chain
              </motion.p>

              <motion.h1 initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.2 }}
                className="text-5xl md:text-6xl lg:text-7xl font-heading font-medium text-[#2D1810] mb-6 tracking-tight leading-[0.95]"
                data-testid="hero-title">
                Authentic<br />
                <span className="text-gold-shimmer">Maharashtrian</span><br />
                Cuisine
              </motion.h1>

              <motion.p initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.4 }}
                className="text-lg text-[#5C4A3A] mb-10 font-body leading-relaxed max-w-xl">
                Experience the richness of traditional recipes passed down through generations. Pure vegetarian, pure love.
              </motion.p>

              <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.6 }} className="flex flex-wrap gap-4">
                <Link to="/table-booking">
                  <Button size="lg" className="gold-glossy text-white px-8 py-6 text-sm rounded-none tracking-widest uppercase font-semibold group border-0" data-testid="book-table-cta">
                    <Calendar className="mr-2 h-4 w-4" /> Reserve Table <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
                  </Button>
                </Link>
                <Link to="/pickup">
                  <Button size="lg" variant="outline" className="border border-[#B8962E]/40 text-[#B8962E] hover:bg-[#B8962E]/10 px-8 py-6 text-sm rounded-none tracking-widest uppercase" data-testid="order-now-cta">
                    <ShoppingBag className="mr-2 h-4 w-4" /> Order Pickup
                  </Button>
                </Link>
                <Link to="/book">
                  <Button size="lg" variant="outline" className="border border-[#B8962E]/40 text-[#B8962E] hover:bg-[#B8962E]/10 px-8 py-6 text-sm rounded-none tracking-widest uppercase" data-testid="read-book-cta">
                    <BookOpen className="mr-2 h-4 w-4" /> Read Book
                  </Button>
                </Link>
              </motion.div>

              {/* Stats Row */}
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1 }} className="mt-16 flex flex-wrap gap-10">
                {stats.map((s, i) => (
                  <div key={i}>
                    <div className="flex items-center gap-2 mb-1">
                      <s.icon className="h-4 w-4 text-[#B8962E]/60" />
                      <span className="text-3xl font-heading font-medium text-[#2D1810]">{s.value}</span>
                    </div>
                    <span className="text-[#7A6F65] text-xs tracking-wider uppercase font-body">{s.label}</span>
                  </div>
                ))}
              </motion.div>
            </div>
          </div>
        </div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.5 }} className="absolute bottom-8 left-1/2 -translate-x-1/2">
          <motion.div animate={{ y: [0, 8, 0] }} transition={{ duration: 2, repeat: Infinity }} className="flex flex-col items-center text-[#7A6F65]/60">
            <span className="text-[10px] tracking-[0.2em] uppercase mb-2">Scroll</span>
            <ChevronRight className="h-4 w-4 rotate-90" />
          </motion.div>
        </motion.div>
      </section>

      {/* Banana Leaf Thali Launch — Top of page */}
      <section className="py-12 bg-gradient-to-r from-[#1B5E20] via-[#2E7D32] to-[#1B5E20] relative overflow-hidden">
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle at 20% 50%, #fff 0%, transparent 40%)' }} />
        <div className="container mx-auto px-6 lg:px-12 relative">
          <div className="text-center max-w-2xl mx-auto">
            <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
              <div className="inline-flex items-center gap-2 bg-white/10 border border-white/20 rounded-full px-4 py-1 mb-4">
                <Leaf className="w-3.5 h-3.5 text-[#A5D6A7]" />
                <span className="text-[10px] font-body text-[#A5D6A7] tracking-wider uppercase">New — Launching May 2nd</span>
              </div>
              <h2 className="font-heading text-2xl lg:text-3xl text-white mb-2">Banana Leaf Thali</h2>
              <p className="font-heading text-base text-white/60 italic mb-3">केळीच्या पानाची पंगत</p>
              <p className="text-sm text-white/50 font-body mb-5">
                Unlimited authentic Maharashtrian thali on banana leaf. Every Tue, Wed, Thu — Lunch only. ₹490/person | $40 in Perth
              </p>
              <div className="flex flex-wrap justify-center gap-4">
                <Link to="/banana-leaf-thali">
                  <Button className="bg-white text-[#1B5E20] hover:bg-white/90 font-bold rounded-none px-8 py-3 text-sm tracking-widest uppercase" data-testid="home-banana-leaf-cta">
                    <ArrowRight className="w-4 h-4 mr-2" /> Explore Menu
                  </Button>
                </Link>
                <Link to="/table-booking?type=banana-leaf">
                  <Button variant="outline" className="border border-white/30 text-white hover:bg-white/10 rounded-none px-8 py-3 text-sm tracking-widest uppercase">
                    <Calendar className="w-4 h-4 mr-2" /> Book Table
                  </Button>
                </Link>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Services */}
      <section className="py-24 bg-[#FDFBF7]">
        <div className="container mx-auto px-6 lg:px-12">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-16">
            <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-4">Our Services</p>
            <h2 className="text-4xl md:text-5xl font-heading font-medium text-[#2D1810] tracking-tight">
              How Would You Like to <span className="text-gold-shimmer">Dine?</span>
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {services.map((s, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}>
                <Link to={s.link}>
                  <div className="group p-8 pearl-surface hover:border-[#B8962E]/30 transition-all duration-300 hover:-translate-y-1 cursor-pointer h-full">
                    <s.icon className="h-8 w-8 text-[#B8962E] mb-6 group-hover:scale-110 transition-transform" />
                    <h3 className="text-xl font-heading font-medium text-[#2D1810] mb-2">{s.title}</h3>
                    <p className="text-sm text-[#5C4A3A] mb-6 font-body">{s.description}</p>
                    <span className="text-xs tracking-[0.2em] uppercase text-[#B8962E] font-body font-semibold group-hover:tracking-[0.3em] transition-all">
                      {s.cta} <ArrowRight className="inline h-3 w-3 ml-1 group-hover:translate-x-1 transition-transform" />
                    </span>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Featured Dishes */}
      <section className="py-24 bg-[#F8F5F0]">
        <div className="container mx-auto px-6 lg:px-12">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-16">
            <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-4">Signature Menu</p>
            <h2 className="text-4xl md:text-5xl font-heading font-medium text-[#2D1810] tracking-tight">
              Crafted with <span className="text-gold-shimmer">Heritage</span>
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {featuredDishes.map((dish, i) => (
              <motion.div key={dish.id} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }} className="group">
                <div className="bg-white border border-[#E8DFD0] overflow-hidden hover:border-[#B8962E]/30 transition-all hover:shadow-lg">
                  <div className="relative h-52 overflow-hidden">
                    <img src={dish.image} alt={dish.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
                    <div className="absolute inset-0 bg-gradient-to-t from-white via-transparent to-transparent" />
                    <span className="absolute top-4 right-4 text-[10px] tracking-[0.15em] uppercase bg-[#B8962E] text-white px-3 py-1 font-semibold">{dish.tag}</span>
                  </div>
                  <div className="p-6">
                    <h3 className="text-lg font-heading font-medium text-[#2D1810] mb-1">{dish.name}</h3>
                    <p className="text-xs text-[#7A6F65] mb-3 font-body">{dish.description}</p>
                    <p className="text-xl font-heading font-medium text-[#B8962E]">&#8377;{dish.price}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          <div className="text-center mt-12">
            <Link to="/menu">
              <Button size="lg" className="gold-glossy text-white rounded-none px-8 py-6 text-xs tracking-widest uppercase font-semibold border-0">
                View Full Menu <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Special Offer Banner */}
      <section className="py-16 bg-gradient-to-r from-[#B8962E]/5 via-[#D4AF37]/10 to-[#B8962E]/5 border-y border-[#B8962E]/10">
        <div className="container mx-auto px-6 lg:px-12 flex flex-col md:flex-row items-center justify-between gap-6">
          <div>
            <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-3">Exclusive Offer</p>
            <h3 className="text-3xl md:text-4xl font-heading font-medium text-[#2D1810] mb-2">Unlimited Breakfast Buffet</h3>
            <p className="text-[#5C4A3A] font-body">Every Saturday & Sunday &bull; 8 AM - 11 AM &bull; Only &#8377;299/person</p>
          </div>
          <Link to="/tiffin">
            <Button size="lg" className="gold-glossy text-white rounded-none px-8 py-6 text-xs tracking-widest uppercase font-semibold border-0">
              Book Now <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-24 bg-[#FDFBF7]">
        <div className="container mx-auto px-6 lg:px-12">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-16">
            <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-4">Testimonials</p>
            <h2 className="text-4xl md:text-5xl font-heading font-medium text-[#2D1810] tracking-tight">
              What Our <span className="text-gold-shimmer">Guests</span> Say
            </h2>
          </motion.div>

          <div className="max-w-3xl mx-auto">
            <AnimatePresence mode="wait">
              <motion.div key={currentSlide} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="text-center">
                <div className="flex justify-center mb-4">
                  {[...Array(testimonials[currentSlide].rating)].map((_, i) => <Star key={i} className="h-5 w-5 text-[#D4AF37] fill-[#D4AF37]" />)}
                </div>
                <p className="text-2xl md:text-3xl text-[#2D1810]/80 font-heading font-light italic mb-6 leading-relaxed">
                  "{testimonials[currentSlide].text}"
                </p>
                <p className="font-body font-semibold text-[#B8962E] text-sm tracking-wider">{testimonials[currentSlide].name}</p>
                <p className="text-xs text-[#7A6F65] font-body">{testimonials[currentSlide].location}</p>
              </motion.div>
            </AnimatePresence>

            <div className="flex justify-center gap-2 mt-8">
              {testimonials.map((_, i) => (
                <button key={i} onClick={() => setCurrentSlide(i)} className={`h-1 transition-all ${currentSlide === i ? 'bg-[#B8962E] w-8' : 'bg-[#E8DFD0] w-4'}`} />
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Book Promotion */}
      <section className="py-20 bg-[#3D2314] relative overflow-hidden">
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle at 20% 50%, #D4AF37 0%, transparent 50%), radial-gradient(circle at 80% 50%, #D4AF37 0%, transparent 50%)' }} />
        <div className="container mx-auto px-6 lg:px-12 relative">
          <div className="flex flex-col md:flex-row items-center gap-10 lg:gap-16">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="flex-shrink-0"
            >
              <img
                src="https://customer-assets.emergentagent.com/job_50886080-3950-4b54-8e6a-7e012eaffafc/artifacts/bdlxtuu4_Book_Restaurant_become_Human.png"
                alt="Purnabramha – When a Restaurant Becomes Human"
                className="w-[180px] lg:w-[220px] rounded-lg shadow-[0_15px_50px_rgba(0,0,0,0.5)]"
                style={{ aspectRatio: '2/3', objectFit: 'cover' }}
                data-testid="home-book-cover"
              />
            </motion.div>
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="text-center md:text-left"
            >
              <p className="text-xs tracking-[0.3em] uppercase text-[#D4AF37]/60 font-body mb-3">New Book by Jayanti Pranav Kathale</p>
              <h2 className="text-3xl lg:text-4xl font-heading text-[#D4AF37] mb-2">When a Restaurant</h2>
              <h2 className="text-3xl lg:text-4xl font-heading text-[#D4AF37]/70 italic mb-4">Becomes Human</h2>
              <p className="text-sm text-[#D4AF37]/50 font-body leading-relaxed mb-6 max-w-md">
                152 pages of wisdom, love, and the journey of Purnabramha. Read online with page-flip animation, calm music, and tea break reminders.
              </p>
              <div className="flex flex-col sm:flex-row items-center gap-4">
                <Link to="/book">
                  <Button className="gold-glossy text-[#3D2314] font-bold rounded-none px-8 py-3 text-sm tracking-widest uppercase border-0" data-testid="home-book-cta">
                    <ArrowRight className="w-4 h-4 mr-2" />
                    Read Now
                  </Button>
                </Link>
                <span className="text-[#D4AF37]/40 text-xs font-body">First pages free — no login needed</span>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Locations */}
      <section className="py-24 bg-[#F8F5F0]">
        <div className="container mx-auto px-6 lg:px-12">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-16">
            <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-4">Visit Us</p>
            <h2 className="text-4xl md:text-5xl font-heading font-medium text-[#2D1810] tracking-tight">
              Find Us <span className="text-gold-shimmer">Near You</span>
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { city: "Bangalore", area: "HSR Layout", phone: "+91 85500 78515" },
              { city: "Mumbai", area: "Thane", phone: "+91 89047 49084" },
              { city: "Pune", area: "Kharadi", phone: "9900089803" },
              { city: "Perth", area: "Australia", phone: "+61 401 832 922" }
            ].map((loc, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}>
                <div className="p-8 pearl-surface hover:border-[#B8962E]/30 transition-all">
                  <MapPin className="h-6 w-6 text-[#B8962E] mb-4" />
                  <h3 className="text-xl font-heading font-medium text-[#2D1810] mb-1">{loc.city}</h3>
                  <p className="text-sm text-[#5C4A3A] mb-3 font-body">{loc.area}</p>
                  <a href={`tel:${loc.phone.replace(/\s/g, '')}`} className="flex items-center text-[#B8962E]/70 hover:text-[#B8962E] text-sm font-body">
                    <Phone className="h-3 w-3 mr-2" /> {loc.phone}
                  </a>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-24 bg-gradient-to-b from-[#F8F5F0] to-[#FDFBF7] border-t border-[#B8962E]/10">
        <div className="container mx-auto px-6 lg:px-12 text-center">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
            <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-6">Experience Purnabramha</p>
            <h2 className="text-4xl md:text-5xl lg:text-6xl font-heading font-medium text-[#2D1810] mb-8 tracking-tight leading-tight">
              Ready to Experience<br /><span className="text-gold-shimmer">Authentic Maharashtra?</span>
            </h2>
            <div className="flex flex-wrap justify-center gap-4">
              <Link to="/table-booking">
                <Button size="lg" className="gold-glossy text-white rounded-none px-8 py-6 text-xs tracking-widest uppercase font-semibold border-0">
                  <Calendar className="mr-2 h-4 w-4" /> Reserve Table
                </Button>
              </Link>
              <Link to="/pickup">
                <Button size="lg" variant="outline" className="border border-[#B8962E]/40 text-[#B8962E] hover:bg-[#B8962E]/10 rounded-none px-8 py-6 text-xs tracking-widest uppercase">
                  <ShoppingBag className="mr-2 h-4 w-4" /> Order Pickup
                </Button>
              </Link>
              <Link to="/tiffin">
                <Button size="lg" variant="outline" className="border border-[#B8962E]/20 text-[#B8962E]/70 hover:bg-[#B8962E]/10 rounded-none px-8 py-6 text-xs tracking-widest uppercase">
                  <Coffee className="mr-2 h-4 w-4" /> Tiffin Service
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
