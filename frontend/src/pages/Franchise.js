import { motion } from 'framer-motion';
import { Phone, Mail, MapPin, TrendingUp, Users, Award } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

const Franchise = () => {
  const benefits = [
    {
      icon: TrendingUp,
      title: "Proven Business Model",
      description: "Join India's largest Maharashtrian restaurant chain with 8+ locations"
    },
    {
      icon: Users,
      title: "Complete Support",
      description: "Training, operations, marketing, and ongoing support from our team"
    },
    {
      icon: Award,
      title: "Brand Recognition",
      description: "Leverage the trust and reputation of Purnabramha"
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-cream to-white">
      <div className="container mx-auto px-4 lg:px-8 py-12 lg:py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="font-playfair text-4xl lg:text-6xl font-bold text-foreground mb-4 tracking-tight" data-testid="franchise-title">
            Franchise Opportunities
          </h1>
          <p className="text-lg text-foreground/70 font-manrope max-w-2xl mx-auto">
            Partner with Purnabramha and bring authentic Maharashtrian flavors to your city
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center mb-16">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <img
              src="https://images.pexels.com/photos/19447626/pexels-photo-19447626.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
              alt="Purnabramha Restaurant"
              className="rounded-2xl shadow-2xl"
            />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-6"
          >
            <h2 className="font-playfair text-3xl lg:text-4xl font-bold text-foreground">
              Why Choose Purnabramha?
            </h2>
            <p className="text-foreground/70 font-manrope leading-relaxed">
              Purnabramha is not just a restaurant chain - it's a movement to preserve and celebrate authentic Maharashtrian cuisine. As the largest Maharashtrian restaurant chain run under women leadership, we've built a strong foundation of trust, quality, and tradition.
            </p>
            
            <div className="space-y-4">
              {benefits.map((benefit, index) => (
                <div key={index} className="flex items-start space-x-4">
                  <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <benefit.icon className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-manrope font-semibold text-foreground mb-1">{benefit.title}</h3>
                    <p className="text-sm text-foreground/70">{benefit.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-2xl p-8 lg:p-12 border border-orange-900/10 shadow-lg"
        >
          <div className="text-center mb-8">
            <h2 className="font-playfair text-3xl lg:text-4xl font-bold text-foreground mb-4">
              Get in Touch
            </h2>
            <p className="text-foreground/70 font-manrope">
              Connect with us to explore franchise opportunities
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">
            <Card className="border-orange-900/10 hover:shadow-lg transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-center space-x-4">
                  <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                    <Phone className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm text-foreground/70 font-manrope mb-1">Franchise Enquiry</p>
                    <a 
                      href="tel:+919741399190" 
                      className="font-manrope font-semibold text-lg text-primary hover:underline"
                      data-testid="franchise-phone"
                    >
                      +91 9741399190
                    </a>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-orange-900/10 hover:shadow-lg transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-center space-x-4">
                  <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                    <Phone className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm text-foreground/70 font-manrope mb-1">WhatsApp</p>
                    <a 
                      href="https://wa.me/919741399190" 
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-manrope font-semibold text-lg text-primary hover:underline"
                      data-testid="franchise-whatsapp"
                    >
                      Chat with Us
                    </a>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="mt-8 p-6 bg-cream rounded-xl">
            <h3 className="font-manrope font-semibold text-foreground mb-3">Contact Hours</h3>
            <p className="text-foreground/70 font-manrope">
              WhatsApp: 9 AM to 9 PM (Mon - Sun)
            </p>
            <p className="text-sm text-foreground/60 font-manrope mt-2">
              We typically respond within 24 hours
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Franchise;