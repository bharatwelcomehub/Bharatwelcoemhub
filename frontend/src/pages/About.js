import { motion } from 'framer-motion';
import { Award, Users, MapPin, Heart } from 'lucide-react';

const About = () => {
  const milestones = [
    { icon: MapPin, title: "8 Locations", description: "Across India and Australia" },
    { icon: Users, title: "Women Leadership", description: "India's largest women-led Maharashtrian chain" },
    { icon: Heart, title: "Authentic Recipes", description: "Traditional flavors preserved for generations" },
    { icon: Award, title: "Community Impact", description: "Empowering local communities" }
  ];

  return (
    <div className="min-h-screen bg-[#FDFBF7]">
      <div className="container mx-auto px-6 lg:px-12 py-16 lg:py-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-16"
        >
          <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-4">Our Story</p>
          <h1 className="font-heading text-5xl md:text-6xl lg:text-7xl font-medium text-[#2D1810] mb-4 tracking-tight" data-testid="about-title">
            About <span className="text-gold-shimmer">Purnabramha</span>
          </h1>
          <p className="text-lg text-[#5C4A3A] font-body max-w-2xl mx-auto">
            India's Largest Maharashtrian Restaurant Chain
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center mb-24">
          <motion.div initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }}>
            <div className="overflow-hidden border border-[#E8DFD0] shadow-lg">
              <img
                src="https://images.pexels.com/photos/19447626/pexels-photo-19447626.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
                alt="Purnabramha Interior"
                className="w-full h-auto"
              />
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
            <h2 className="font-heading text-3xl md:text-4xl font-medium text-[#2D1810] tracking-tight">
              A Legacy of <span className="text-gold-shimmer">Flavor</span>
            </h2>
            <p className="text-[#5C4A3A] font-body leading-relaxed">
              Purnabramha was born from a passion to preserve and celebrate the rich culinary heritage of Maharashtra. What started as a dream has grown into India's largest Maharashtrian restaurant chain, proudly run under women leadership.
            </p>
            <p className="text-[#5C4A3A] font-body leading-relaxed">
              Founded by Jayanti Kathale, a renowned speaker and entrepreneur, Purnabramha represents more than just food - it's a movement to empower communities, preserve traditions, and create opportunities for women in the culinary industry.
            </p>
            <p className="text-[#5C4A3A] font-body leading-relaxed">
              With 8 locations across India and Australia, we continue to grow while staying true to our roots - serving authentic, home-style Maharashtrian cuisine prepared with love, care, and the finest ingredients.
            </p>
          </motion.div>
        </div>

        <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="mb-24">
          <div className="text-center mb-16">
            <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-4">Milestones</p>
            <h2 className="font-heading text-4xl md:text-5xl font-medium text-[#2D1810] tracking-tight">
              Our <span className="text-gold-shimmer">Journey</span>
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {milestones.map((milestone, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.1 * index }}
                className="pearl-surface p-8 hover:border-[#B8962E]/30 transition-all hover:-translate-y-1"
              >
                <milestone.icon className="h-8 w-8 text-[#B8962E] mb-6" />
                <h3 className="font-heading text-xl font-medium text-[#2D1810] mb-2">{milestone.title}</h3>
                <p className="text-[#5C4A3A] font-body text-sm">{milestone.description}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="pearl-surface p-8 lg:p-16"
        >
          <div className="text-center mb-8">
            <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-4">Philosophy</p>
            <h2 className="font-heading text-3xl md:text-4xl font-medium text-[#2D1810] tracking-tight">
              Our <span className="text-gold-shimmer">Values</span>
            </h2>
          </div>
          <div className="max-w-3xl mx-auto space-y-6">
            <p className="text-[#5C4A3A] font-body leading-relaxed text-center">
              At Purnabramha, food is more than a meal — it is a celebration of tradition, culture, and connection. Rooted in Maharashtrian values, we believe in serving honest, soulful food prepared with care, purity, and respect for age-old recipes.
            </p>
            <p className="text-[#5C4A3A] font-body leading-relaxed text-center">
              Every dish reflects our commitment to authenticity, balance, and warmth, creating an experience that feels like home for every guest, across generations.
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default About;
