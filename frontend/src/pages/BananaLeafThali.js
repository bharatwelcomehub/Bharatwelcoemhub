import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { MapPin, Clock, Calendar, Users, Car, Phone, Leaf, ArrowRight, Utensils } from 'lucide-react';
import { Button } from '@/components/ui/button';

const BANNER_IMG = 'https://customer-assets.emergentagent.com/job_50886080-3950-4b54-8e6a-7e012eaffafc/artifacts/leitfka5_banana%20leaf%20concept%20%281%29.pdf';
const CONCEPT_IMG = 'https://customer-assets.emergentagent.com/job_50886080-3950-4b54-8e6a-7e012eaffafc/artifacts/leitfka5_banana%20leaf%20concept%20%281%29.pdf';

const THALI_IMAGE = 'https://static.prod-images.emergentagent.com/jobs/50886080-3950-4b54-8e6a-7e012eaffafc/images/1312be33fab72a840c93a99a09e5dbdea5454e8e51ac81cd7c514e9c852776b6.png';

const THALI_ITEMS = [
  { name: 'Tak Vati', marathi: 'ताक वाटी', desc: 'Traditional buttermilk' },
  { name: 'Bharleli Vangi', marathi: 'भरलेली वांगी', desc: 'Stuffed brinjal with rich spice masala' },
  { name: 'Patal Bhaji', marathi: 'पातळ भाजी', desc: 'Thin aromatic vegetable curry' },
  { name: 'Dinvishesh Bhaji', marathi: 'दिनविशेष भाजी', desc: 'Special vegetable of the day' },
  { name: 'Phodniche Varan', marathi: 'फोडणीचे वरण', desc: 'Tempered lentils with ghee' },
  { name: 'Takachi Kadhi', marathi: 'ताकाची कढी', desc: 'Buttermilk curry with spices' },
  { name: 'Sadha Bhat', marathi: 'साधा भात', desc: 'Steamed plain rice' },
  { name: 'Masale Bhat', marathi: 'मसाले भात', desc: 'Fragrant spiced rice' },
  { name: 'Din Vishesh God', marathi: 'दिन विशेष गोड', desc: 'Sweet dish of the day' },
  { name: 'Accompaniments', marathi: 'चटणी, मेतकूट, ठेचा, लोणचं, पापड', desc: 'Metkut, Thecha, Pickle & Papad' }
];

const CENTERS = [
  { name: 'Hinjewadi, Pune', parking: '200+ FREE parking', highlight: true },
  { name: 'Kharadi, Pune', parking: '200+ FREE parking', highlight: true },
  { name: 'HSR Layout, Bangalore' },
  { name: 'Sambhajinagar' },
  { name: 'Dombivli' },
  { name: 'Kalyan' },
  { name: 'Perth, Australia', intl: true, price: '$40' }
];

const BananaLeafThali = () => {
  useEffect(() => {
    document.title = 'Banana Leaf Thali - Authentic Maharashtrian Unlimited Thali | Purnabramha';
    // SEO meta tags
    const setMeta = (name, content) => {
      let el = document.querySelector(`meta[name="${name}"]`) || document.querySelector(`meta[property="${name}"]`);
      if (!el) { el = document.createElement('meta'); el.setAttribute(name.startsWith('og:') ? 'property' : 'name', name); document.head.appendChild(el); }
      el.setAttribute('content', content);
    };
    setMeta('description', 'Enjoy unlimited authentic Maharashtrian Banana Leaf Thali at Purnabramha. ₹490/person, every Tuesday, Wednesday & Thursday. 10+ dishes including Bharleli Vangi, Masale Bhat, Kadhi. Available at all centers. Free parking at Hinjewadi & Kharadi.');
    setMeta('keywords', 'banana leaf thali, maharashtrian thali, unlimited thali pune, purnabramha banana leaf, banana leaf thali hinjewadi, banana leaf thali kharadi, maharashtrian thali bangalore, unlimited thali near me, veg thali pune, corporate lunch pune');
    setMeta('og:title', 'Banana Leaf Thali - Purnabramha | ₹490 Unlimited');
    setMeta('og:description', 'Authentic Maharashtrian Unlimited Banana Leaf Thali. Every Tue, Wed, Thu. 10+ dishes. Free parking at Hinjewadi & Kharadi.');
    setMeta('og:type', 'website');

    // JSON-LD Event Schema
    const script = document.createElement('script');
    script.type = 'application/ld+json';
    script.textContent = JSON.stringify({
      "@context": "https://schema.org",
      "@type": "FoodEvent",
      "name": "Purnabramha Banana Leaf Thali",
      "description": "Unlimited authentic Maharashtrian Banana Leaf Thali with 10+ traditional dishes. Pure vegetarian, wholesome, satisfying.",
      "startDate": "2026-05-02",
      "eventSchedule": {
        "@type": "Schedule",
        "byDay": ["Tuesday", "Wednesday", "Thursday"],
        "startTime": "12:00",
        "endTime": "15:00"
      },
      "offers": [
        { "@type": "Offer", "price": "490", "priceCurrency": "INR", "name": "India", "availability": "https://schema.org/InStock" },
        { "@type": "Offer", "price": "40", "priceCurrency": "AUD", "name": "Perth", "availability": "https://schema.org/PreOrder" }
      ],
      "location": [
        { "@type": "Restaurant", "name": "Purnabramha Hinjewadi", "address": "Hinjewadi, Pune" },
        { "@type": "Restaurant", "name": "Purnabramha Kharadi", "address": "Kharadi, Pune" },
        { "@type": "Restaurant", "name": "Purnabramha HSR", "address": "HSR Layout, Bangalore" },
        { "@type": "Restaurant", "name": "Purnabramha Sambhajinagar", "address": "Sambhajinagar" },
        { "@type": "Restaurant", "name": "Purnabramha Dombivli", "address": "Dombivli" },
        { "@type": "Restaurant", "name": "Purnabramha Kalyan", "address": "Kalyan" },
        { "@type": "Restaurant", "name": "Purnabramha Perth", "address": "Perth, Australia" }
      ],
      "organizer": { "@type": "Organization", "name": "Purnabramha", "url": "https://www.purnabramha.com" }
    });
    document.head.appendChild(script);
    return () => { document.head.removeChild(script); };
  }, []);

  return (
    <div className="min-h-screen bg-[#FDFBF7]">
      {/* Hero Section */}
      <section className="relative py-12 lg:py-20 bg-gradient-to-b from-[#3D2314] via-[#4A2A18] to-[#3D2314] overflow-hidden">
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle at 30% 50%, #2E7D32 0%, transparent 50%), radial-gradient(circle at 70% 50%, #D4AF37 0%, transparent 50%)' }} />
        <div className="container mx-auto px-4 lg:px-8 relative">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-16 items-center">
            {/* Image */}
            <motion.div initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.8 }} className="order-2 lg:order-1 flex justify-center">
              <div className="relative">
                <div className="absolute -inset-4 bg-gradient-to-br from-[#2E7D32]/20 to-[#D4AF37]/10 rounded-2xl blur-2xl" />
                <img
                  src={THALI_IMAGE}
                  alt="Purnabramha Banana Leaf Thali - Authentic Maharashtrian Unlimited Thali"
                  className="relative w-full max-w-[500px] rounded-xl shadow-[0_20px_60px_rgba(0,0,0,0.4)]"
                  data-testid="banana-leaf-hero-img"
                />
              </div>
            </motion.div>

            {/* Text */}
            <div className="order-1 lg:order-2 text-center lg:text-left">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
                <div className="inline-flex items-center gap-2 bg-[#2E7D32]/20 border border-[#2E7D32]/30 rounded-full px-4 py-1.5 mb-6">
                  <Leaf className="w-4 h-4 text-[#4CAF50]" />
                  <span className="text-xs font-body text-[#4CAF50] tracking-wider uppercase">Launching May 2nd, 2026</span>
                </div>
              </motion.div>

              <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="font-heading text-4xl lg:text-5xl text-[#D4AF37] mb-3">
                Banana Leaf Thali
              </motion.h1>
              <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="font-heading text-xl text-[#D4AF37]/60 italic mb-5">
                केळीच्या पानाची पंगत
              </motion.p>
              <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="text-sm text-[#D4AF37]/50 font-body leading-relaxed mb-6 max-w-md mx-auto lg:mx-0">
                Authentic Maharashtrian unlimited thali served on a traditional banana leaf.
                Pure vegetarian. Wholesome. Satisfying. Non-sharable.
              </motion.p>

              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="flex flex-wrap items-center justify-center lg:justify-start gap-6 mb-8">
                <div className="text-center">
                  <p className="text-3xl font-heading text-[#D4AF37]">&#8377;490</p>
                  <p className="text-[10px] text-[#D4AF37]/40 font-body">Per Person (India)</p>
                </div>
                <div className="w-px h-10 bg-[#D4AF37]/20" />
                <div className="text-center">
                  <p className="text-3xl font-heading text-[#D4AF37]">$40</p>
                  <p className="text-[10px] text-[#D4AF37]/40 font-body">Per Person (Perth)</p>
                </div>
                <div className="w-px h-10 bg-[#D4AF37]/20" />
                <div className="text-center">
                  <p className="text-3xl font-heading text-[#D4AF37]">Unlimited</p>
                  <p className="text-[10px] text-[#D4AF37]/40 font-body">All Dishes, All Servings</p>
                </div>
              </motion.div>

              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="flex flex-wrap items-center justify-center lg:justify-start gap-4">
                <Link to="/table-booking">
                  <Button className="gold-glossy text-[#3D2314] font-bold rounded-none px-8 py-3 text-sm tracking-widest uppercase border-0" data-testid="banana-leaf-book-btn">
                    <Calendar className="w-4 h-4 mr-2" /> Book Your Table
                  </Button>
                </Link>
                <a href="https://wa.me/919741399190?text=Hi%2C%20I%20want%20to%20book%20Banana%20Leaf%20Thali%20for%20our%20corporate%20group" target="_blank" rel="noopener noreferrer">
                  <Button variant="outline" className="border border-[#D4AF37]/30 text-[#D4AF37] hover:bg-[#D4AF37]/10 rounded-none px-8 py-3 text-sm tracking-widest uppercase" data-testid="banana-leaf-corporate-btn">
                    <Users className="w-4 h-4 mr-2" /> Corporate Group Booking
                  </Button>
                </a>
              </motion.div>
            </div>
          </div>
        </div>
      </section>

      {/* Schedule Bar */}
      <section className="bg-[#2E7D32] py-4">
        <div className="container mx-auto px-4 flex flex-wrap items-center justify-center gap-6 lg:gap-12">
          <div className="flex items-center gap-2 text-white">
            <Calendar className="w-4 h-4" />
            <span className="text-sm font-body">Every <strong>Tuesday, Wednesday, Thursday</strong></span>
          </div>
          <div className="flex items-center gap-2 text-white">
            <Clock className="w-4 h-4" />
            <span className="text-sm font-body"><strong>Lunch Only</strong></span>
          </div>
          <div className="flex items-center gap-2 text-white">
            <Utensils className="w-4 h-4" />
            <span className="text-sm font-body"><strong>Unlimited</strong> | Non-Sharable</span>
          </div>
          <div className="flex items-center gap-2 text-white">
            <Leaf className="w-4 h-4" />
            <span className="text-sm font-body"><strong>Pure Vegetarian</strong></span>
          </div>
        </div>
      </section>

      {/* Menu Items */}
      <section className="py-16 bg-white border-b border-[#E8DFD0]">
        <div className="container mx-auto px-4 lg:px-8">
          <h2 className="text-center font-heading text-2xl text-[#3D2314] mb-2">What's on the Banana Leaf</h2>
          <p className="text-center text-sm text-[#7A6F65] font-body mb-10">10+ traditional dishes, unlimited servings</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 max-w-5xl mx-auto">
            {THALI_ITEMS.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="bg-[#FDFBF7] border border-[#E8DFD0] rounded-xl p-4 text-center hover:border-[#2E7D32]/30 hover:shadow-sm transition-all"
              >
                <p className="font-heading text-sm text-[#3D2314] mb-1">{item.name}</p>
                <p className="text-xs text-[#B8962E] font-body mb-1">{item.marathi}</p>
                <p className="text-[10px] text-[#7A6F65] font-body">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Available Centers */}
      <section className="py-16 bg-[#FDFBF7]">
        <div className="container mx-auto px-4 lg:px-8">
          <h2 className="text-center font-heading text-2xl text-[#3D2314] mb-2">Available at All Centers</h2>
          <p className="text-center text-sm text-[#7A6F65] font-body mb-10">Preserving this culture from the core of our heart</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 max-w-4xl mx-auto">
            {CENTERS.map((center, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                className={`p-5 rounded-xl border ${center.highlight ? 'border-[#2E7D32]/40 bg-[#2E7D32]/5' : 'border-[#E8DFD0] bg-white'}`}
              >
                <div className="flex items-start gap-3">
                  <MapPin className={`w-5 h-5 flex-shrink-0 mt-0.5 ${center.highlight ? 'text-[#2E7D32]' : 'text-[#B8962E]'}`} />
                  <div>
                    <p className="font-heading text-base text-[#3D2314]">{center.name}</p>
                    {center.parking && (
                      <div className="flex items-center gap-1 mt-1">
                        <Car className="w-3.5 h-3.5 text-[#2E7D32]" />
                        <span className="text-xs font-body font-semibold text-[#2E7D32]">{center.parking}</span>
                      </div>
                    )}
                    {center.intl && (
                      <p className="text-xs font-body text-[#B8962E] mt-1">{center.price}/person | Pre-book only</p>
                    )}
                    {!center.intl && (
                      <p className="text-xs font-body text-[#7A6F65] mt-1">&#8377;490/person | Walk-in welcome</p>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Corporate Booking CTA */}
      <section className="py-16 bg-[#3D2314]">
        <div className="container mx-auto px-4 text-center">
          <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}>
            <Users className="w-10 h-10 text-[#D4AF37] mx-auto mb-4" />
            <h2 className="font-heading text-2xl lg:text-3xl text-[#D4AF37] mb-3">Corporate Group Bookings</h2>
            <p className="text-sm text-[#D4AF37]/50 font-body mb-6 max-w-md mx-auto">
              Planning a team lunch? Book the Banana Leaf Thali for your entire team.
              Special arrangements for groups of 20+ at Hinjewadi and Kharadi with 200+ free parking.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Link to="/table-booking">
                <Button className="gold-glossy text-[#3D2314] font-bold rounded-none px-8 py-3 text-sm tracking-widest uppercase border-0">
                  <Calendar className="w-4 h-4 mr-2" /> Reserve Table
                </Button>
              </Link>
              <a href="https://wa.me/919741399190?text=Hi%2C%20I%20want%20to%20book%20Banana%20Leaf%20Thali%20for%20corporate%20group%20of%20___%20people%20at%20___center" target="_blank" rel="noopener noreferrer">
                <Button variant="outline" className="border border-[#D4AF37]/30 text-[#D4AF37] hover:bg-[#D4AF37]/10 rounded-none px-8 py-3 text-sm tracking-widest uppercase">
                  <Phone className="w-4 h-4 mr-2" /> WhatsApp Us
                </Button>
              </a>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Philosophy */}
      <section className="py-16 text-center bg-[#FDFBF7]">
        <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}>
          <p className="font-heading text-xl lg:text-2xl text-[#3D2314] italic max-w-xl mx-auto leading-relaxed mb-4">
            "Asal Chav.. Manapasun Seva..!"
          </p>
          <p className="text-sm text-[#B8962E] font-body">Authentic Taste. Heartfelt Service.</p>
          <p className="text-xs text-[#7A6F65] font-body mt-1">— Purnabramha</p>
        </motion.div>
      </section>
    </div>
  );
};

export default BananaLeafThali;
