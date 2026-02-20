import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ShoppingBag, Calendar, Coffee, UtensilsCrossed, MapPin } from 'lucide-react';

const Home = () => {
  const services = [
    {
      icon: ShoppingBag,
      title: 'Pickup Orders',
      description: 'Order ahead and pick up your favorite Maharashtrian dishes',
      link: '/pickup',
      color: 'text-orange-600'
    },
    {
      icon: Calendar,
      title: 'Table Booking',
      description: 'Reserve your table for a delightful dining experience',
      link: '/table-booking',
      color: 'text-maroon'
    },
    {
      icon: Coffee,
      title: 'Tiffin Service',
      description: 'Subscribe to daily home-cooked meals delivered to you',
      link: '/tiffin',
      color: 'text-orange-600'
    },
    {
      icon: UtensilsCrossed,
      title: 'Catering',
      description: 'Make your events special with authentic Maharashtrian cuisine',
      link: '/catering',
      color: 'text-maroon'
    }
  ];

  return (
    <div>
      <section className="hero-section" data-testid="hero-section">
        <img
          src="https://images.pexels.com/photos/30769679/pexels-photo-30769679.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
          alt="Authentic Maharashtrian Misal Pav"
          className="hero-image"
        />
        <div className="hero-overlay" />
        <div className="hero-content container mx-auto px-4 lg:px-8 h-full flex items-end pb-16 lg:pb-24">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="max-w-3xl"
          >
            <h1 className="font-playfair text-5xl lg:text-7xl font-bold text-white mb-6 tracking-tight leading-none">
              Authentic Maharashtrian Flavors
            </h1>
            <p className="text-xl lg:text-2xl text-white/90 mb-8 font-manrope leading-relaxed">
              Experience the richness of traditional recipes at India's largest Maharashtrian restaurant chain
            </p>
            <div className="flex flex-wrap gap-4">
              <Button
                asChild
                size="lg"
                className="rounded-full bg-primary hover:bg-primary/90 text-lg px-8"
                data-testid="order-now-button"
              >
                <Link to="/pickup">Order Now</Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="rounded-full border-white text-white hover:bg-white/10 text-lg px-8"
                data-testid="view-menu-button"
              >
                <Link to="/menu">View Menu</Link>
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      <section className="py-20 lg:py-32 bg-gradient-to-b from-cream to-white">
        <div className="container mx-auto px-4 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="font-playfair text-4xl lg:text-5xl font-bold text-foreground mb-4 tracking-tight">
              Our Services
            </h2>
            <p className="text-lg text-foreground/70 font-manrope max-w-2xl mx-auto">
              From quick pickups to grand celebrations, we serve you with love and tradition
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 lg:gap-8">
            {services.map((service, index) => (
              <motion.div
                key={service.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                data-testid={`service-card-${index}`}
              >
                <Link to={service.link}>
                  <div className="bg-white rounded-xl p-8 border border-orange-900/10 hover:shadow-lg hover:-translate-y-1 transition-all duration-300 h-full">
                    <service.icon className={`h-12 w-12 ${service.color} mb-6`} />
                    <h3 className="font-playfair text-xl font-semibold mb-3 text-foreground">
                      {service.title}
                    </h3>
                    <p className="text-foreground/70 font-manrope leading-relaxed">
                      {service.description}
                    </p>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 lg:py-32">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <img
                src="https://images.pexels.com/photos/19447626/pexels-photo-19447626.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
                alt="Purnabramha Restaurant Interior"
                className="rounded-2xl shadow-2xl"
              />
            </motion.div>
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <h2 className="font-playfair text-4xl lg:text-5xl font-bold mb-6 tracking-tight">
                8 Locations Across India & Australia
              </h2>
              <p className="text-lg text-foreground/70 font-manrope mb-8 leading-relaxed">
                From Bangalore to Perth, we bring the authentic taste of Maharashtra to communities worldwide. Each location maintains the same commitment to quality, tradition, and heartfelt hospitality.
              </p>
              <Button
                asChild
                size="lg"
                className="rounded-full bg-primary"
                data-testid="find-location-button"
              >
                <Link to="/locations">
                  <MapPin className="mr-2 h-5 w-5" />
                  Find a Location Near You
                </Link>
              </Button>
            </motion.div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Home;