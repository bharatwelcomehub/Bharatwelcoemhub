import { motion } from 'framer-motion';
import { Award, Users, MapPin, Heart } from 'lucide-react';

const About = () => {
  const milestones = [
    {
      icon: MapPin,
      title: "8 Locations",
      description: "Across India and Australia"
    },
    {
      icon: Users,
      title: "Women Leadership",
      description: "India's largest women-led Maharashtrian chain"
    },
    {
      icon: Heart,
      title: "Authentic Recipes",
      description: "Traditional flavors preserved for generations"
    },
    {
      icon: Award,
      title: "Community Impact",
      description: "Empowering local communities"
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-cream to-white">
      <div className="container mx-auto px-4 lg:px-8 py-12 lg:py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12">
          <h1 className="font-playfair text-4xl lg:text-6xl font-bold text-foreground mb-4 tracking-tight" data-testid="about-title">
            About Purnabramha
          </h1>
          <p className="text-lg text-foreground/70 font-manrope max-w-2xl mx-auto">
            India's Largest Maharashtrian Restaurant Chain
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center mb-16">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <img
              src="https://images.pexels.com/photos/19447626/pexels-photo-19447626.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
              alt="Purnabramha Interior"
              className="rounded-2xl shadow-2xl"
            />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-6"
          >
            <h2 className="font-playfair text-3xl lg:text-4xl font-bold text-foreground">
              Our Story
            </h2>
            <p className="text-foreground/70 font-manrope leading-relaxed">
              Purnabramha was born from a passion to preserve and celebrate the rich culinary heritage of Maharashtra. What started as a dream has grown into India's largest Maharashtrian restaurant chain, proudly run under women leadership.
            </p>
            <p className="text-foreground/70 font-manrope leading-relaxed">
              Founded by Jayanti Kathale, a renowned speaker and entrepreneur, Purnabramha represents more than just food - it's a movement to empower communities, preserve traditions, and create opportunities for women in the culinary industry.
            </p>
            <p className="text-foreground/70 font-manrope leading-relaxed">
              With 8 locations across India and Australia, we continue to grow while staying true to our roots - serving authentic, home-style Maharashtrian cuisine prepared with love, care, and the finest ingredients.
            </p>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mb-16"
        >
          <h2 className="font-playfair text-3xl lg:text-4xl font-bold text-foreground text-center mb-12">
            Our Journey
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {milestones.map((milestone, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * index }}
                className="bg-white rounded-xl p-6 border border-orange-900/10 hover:shadow-lg transition-shadow text-center"
              >
                <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <milestone.icon className="h-8 w-8 text-primary" />
                </div>
                <h3 className="font-playfair text-xl font-semibold text-foreground mb-2">
                  {milestone.title}
                </h3>
                <p className="text-foreground/70 font-manrope text-sm">
                  {milestone.description}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-white rounded-2xl p-8 lg:p-12 border border-orange-900/10 shadow-lg"
        >
          <h2 className="font-playfair text-3xl lg:text-4xl font-bold text-foreground text-center mb-8">
            Our Philosophy
          </h2>
          <div className="max-w-3xl mx-auto space-y-6">
            <p className="text-foreground/70 font-manrope leading-relaxed text-center">
              At Purnabramha, food is more than a meal — it is a celebration of tradition, culture, and connection. Rooted in Maharashtrian values, we believe in serving honest, soulful food prepared with care, purity, and respect for age-old recipes.
            </p>
            <p className="text-foreground/70 font-manrope leading-relaxed text-center">
              Every dish reflects our commitment to authenticity, balance, and warmth, creating an experience that feels like home for every guest, across generations.
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default About;