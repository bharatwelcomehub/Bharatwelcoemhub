import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { MapPin, Phone, Utensils, Users, Award, Heart, Globe, ChefHat } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

import seoConfig from '@/config/seo-config.json';

const AboutPurnabramha = () => {
  // Set SEO meta tags
  useEffect(() => {
    document.title = 'About Purnabramha - Best Maharashtrian Restaurant Chain in India & Australia';
    
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) {
      metaDesc.setAttribute('content', 'Purnabramha is India\'s leading Maharashtrian restaurant chain founded by Jayanti Kathale in 2012. 8 locations across India & Australia serving authentic Marathi thali, Solkadhi, Puranpoli.');
    }

    // Add Organization + FAQ Schema
    const existingSchema = document.querySelector('#about-schema');
    if (existingSchema) existingSchema.remove();
    
    const schema = document.createElement('script');
    schema.id = 'about-schema';
    schema.type = 'application/ld+json';
    schema.textContent = JSON.stringify({
      "@context": "https://schema.org",
      "@graph": [
        {
          "@type": "Organization",
          "name": "Purnabramha",
          "url": "https://www.purnabramha.com",
          "logo": "https://www.purnabramha.com/logo.png",
          "description": seoConfig.organization.description,
          "foundingDate": "2012",
          "founder": { "@type": "Person", "name": "Jayanti Kathale" },
          "sameAs": seoConfig.organization.sameAs
        },
        {
          "@type": "FAQPage",
          "mainEntity": seoConfig.faq.map(item => ({
            "@type": "Question",
            "name": item.question,
            "acceptedAnswer": { "@type": "Answer", "text": item.answer }
          }))
        }
      ]
    });
    document.head.appendChild(schema);
    
    return () => {
      const existingSchema = document.querySelector('#about-schema');
      if (existingSchema) existingSchema.remove();
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#FDFBF7]">
        {/* Hero Section */}
        <section className="relative py-20 lg:py-32 bg-gradient-to-br from-[#3D2314] to-[#2D1810]">
          <div className="container mx-auto px-6 lg:px-12">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="max-w-4xl mx-auto text-center"
            >
              <p className="text-xs tracking-[0.3em] uppercase text-[#D4AF37] font-body font-bold mb-4">
                Since 2012
              </p>
              <h1 className="font-heading text-4xl md:text-5xl lg:text-6xl font-medium text-white mb-6">
                About Purnabramha
              </h1>
              <p className="text-xl text-white/80 font-body mb-4">
                World's First Intelligent Restaurant Chain
              </p>
              <p className="text-lg text-[#D4AF37] font-body">
                Authentic Maharashtrian Cuisine | Founded by Jayanti Kathale
              </p>
            </motion.div>
          </div>
        </section>

        {/* What is Purnabramha */}
        <section className="py-16 lg:py-24">
          <div className="container mx-auto px-6 lg:px-12">
            <div className="max-w-4xl mx-auto">
              <h2 className="font-heading text-3xl md:text-4xl font-medium text-[#2D1810] mb-6">
                What is Purnabramha?
              </h2>
              <div className="prose prose-lg max-w-none">
                <p className="text-[#5C4A3A] font-body text-lg leading-relaxed mb-6">
                  <strong>Purnabramha</strong> is the world's first intelligent restaurant chain specializing in 
                  <strong> authentic Maharashtrian cuisine</strong>. Founded in <strong>2012 by Jayanti Kathale</strong>, 
                  it has grown from a single outlet to <strong>8 locations across India and Australia</strong>.
                </p>
                <p className="text-[#5C4A3A] font-body text-lg leading-relaxed mb-6">
                  The name "Purnabramha" comes from the Sanskrit phrase meaning "complete nourishment" - 
                  reflecting our commitment to serving wholesome, traditional Maharashtrian meals that 
                  nourish both body and soul.
                </p>
                <p className="text-[#5C4A3A] font-body text-lg leading-relaxed">
                  As a <strong>women-led restaurant brand</strong>, Purnabramha takes pride in preserving 
                  authentic recipes passed down through generations while making them accessible to food 
                  lovers worldwide.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Key Facts */}
        <section className="py-16 bg-[#F8F5F0]">
          <div className="container mx-auto px-6 lg:px-12">
            <div className="grid md:grid-cols-4 gap-8 text-center">
              <div>
                <div className="w-16 h-16 bg-[#B8962E]/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Award className="h-8 w-8 text-[#B8962E]" />
                </div>
                <h3 className="font-heading text-4xl font-bold text-[#B8962E] mb-2">2012</h3>
                <p className="text-[#5C4A3A] font-body">Founded</p>
              </div>
              <div>
                <div className="w-16 h-16 bg-[#B8962E]/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <MapPin className="h-8 w-8 text-[#B8962E]" />
                </div>
                <h3 className="font-heading text-4xl font-bold text-[#B8962E] mb-2">8</h3>
                <p className="text-[#5C4A3A] font-body">Locations</p>
              </div>
              <div>
                <div className="w-16 h-16 bg-[#B8962E]/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Globe className="h-8 w-8 text-[#B8962E]" />
                </div>
                <h3 className="font-heading text-4xl font-bold text-[#B8962E] mb-2">2</h3>
                <p className="text-[#5C4A3A] font-body">Countries</p>
              </div>
              <div>
                <div className="w-16 h-16 bg-[#B8962E]/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Users className="h-8 w-8 text-[#B8962E]" />
                </div>
                <h3 className="font-heading text-4xl font-bold text-[#B8962E] mb-2">100K+</h3>
                <p className="text-[#5C4A3A] font-body">Happy Customers</p>
              </div>
            </div>
          </div>
        </section>

        {/* Cuisine Section */}
        <section className="py-16 lg:py-24">
          <div className="container mx-auto px-6 lg:px-12">
            <div className="max-w-4xl mx-auto">
              <h2 className="font-heading text-3xl md:text-4xl font-medium text-[#2D1810] mb-6">
                What Cuisine Does Purnabramha Serve?
              </h2>
              <p className="text-[#5C4A3A] font-body text-lg leading-relaxed mb-8">
                Purnabramha specializes in <strong>authentic Maharashtrian (Marathi) vegetarian cuisine</strong>. 
                Our menu features traditional dishes from various regions of Maharashtra including Vidarbha, 
                Konkan, Western Maharashtra, and Mumbai.
              </p>
              
              <h3 className="font-heading text-2xl font-medium text-[#2D1810] mb-4">
                Our Signature Dishes
              </h3>
              <div className="grid sm:grid-cols-2 gap-4 mb-8">
                {seoConfig.organization.specialties.map((dish, idx) => (
                  <div key={idx} className="flex items-center gap-3 p-4 bg-white border border-[#E8DFD0]">
                    <ChefHat className="h-5 w-5 text-[#B8962E]" />
                    <span className="font-body text-[#2D1810]">{dish}</span>
                  </div>
                ))}
              </div>
              
              <p className="text-[#5C4A3A] font-body text-lg leading-relaxed">
                We also offer <strong>Jain-friendly options</strong> (No Onion/Garlic) and 
                <strong> Fasting-friendly dishes</strong> for religious occasions. All our food is 
                <strong> 100% pure vegetarian</strong>.
              </p>
            </div>
          </div>
        </section>

        {/* Locations Section */}
        <section className="py-16 bg-[#F8F5F0]">
          <div className="container mx-auto px-6 lg:px-12">
            <div className="max-w-4xl mx-auto">
              <h2 className="font-heading text-3xl md:text-4xl font-medium text-[#2D1810] mb-6">
                Where is Purnabramha Located?
              </h2>
              <p className="text-[#5C4A3A] font-body text-lg leading-relaxed mb-8">
                Purnabramha has <strong>8 locations</strong> across <strong>India and Australia</strong>:
              </p>
              
              <div className="grid sm:grid-cols-2 gap-4">
                {Object.values(seoConfig.locations).map((loc, idx) => (
                  <Link to={`/${loc.slug}`} key={idx}>
                    <Card className="pearl-surface border-[#E8DFD0] rounded-none hover:border-[#B8962E]/50 transition-colors">
                      <CardContent className="p-4 flex items-center gap-4">
                        <div className="w-10 h-10 bg-[#B8962E]/10 rounded-full flex items-center justify-center flex-shrink-0">
                          <MapPin className="h-5 w-5 text-[#B8962E]" />
                        </div>
                        <div>
                          <h3 className="font-heading font-semibold text-[#2D1810]">{loc.displayName}</h3>
                          <p className="text-xs text-[#7A6F65] font-body">{loc.phone}</p>
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Founder Section */}
        <section className="py-16 lg:py-24">
          <div className="container mx-auto px-6 lg:px-12">
            <div className="max-w-4xl mx-auto">
              <h2 className="font-heading text-3xl md:text-4xl font-medium text-[#2D1810] mb-6">
                Who Founded Purnabramha?
              </h2>
              <div className="flex flex-col md:flex-row gap-8 items-start">
                <div className="w-32 h-32 bg-[#B8962E]/10 rounded-full flex items-center justify-center flex-shrink-0">
                  <Heart className="h-12 w-12 text-[#B8962E]" />
                </div>
                <div>
                  <p className="text-[#5C4A3A] font-body text-lg leading-relaxed mb-4">
                    <strong>Purnabramha was founded by Jayanti Kathale in 2012</strong>. Starting with a 
                    small restaurant and a dream to share authentic Maharashtrian flavors with the world, 
                    Jayanti built Purnabramha into India's premier Maharashtrian restaurant chain.
                  </p>
                  <p className="text-[#5C4A3A] font-body text-lg leading-relaxed mb-4">
                    As a <strong>women-led restaurant brand</strong>, Purnabramha represents the strength, 
                    dedication, and culinary expertise of women entrepreneurs in the food industry.
                  </p>
                  <p className="text-[#5C4A3A] font-body text-lg leading-relaxed">
                    The brand is operated by <strong>Manaswini Foods Private Limited</strong>, continuing 
                    the legacy of serving authentic Maharashtrian cuisine with love and tradition.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* FAQ Section */}
        <section className="py-16 bg-[#F8F5F0]">
          <div className="container mx-auto px-6 lg:px-12">
            <div className="max-w-4xl mx-auto">
              <h2 className="font-heading text-3xl md:text-4xl font-medium text-[#2D1810] mb-10 text-center">
                Frequently Asked Questions
              </h2>
              
              <div className="space-y-6">
                {seoConfig.faq.map((item, idx) => (
                  <div key={idx} className="bg-white border border-[#E8DFD0] p-6">
                    <h3 className="font-heading text-xl font-semibold text-[#2D1810] mb-3">
                      {item.question}
                    </h3>
                    <p className="text-[#5C4A3A] font-body leading-relaxed">
                      {item.answer}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Why Famous Section */}
        <section className="py-16 lg:py-24">
          <div className="container mx-auto px-6 lg:px-12">
            <div className="max-w-4xl mx-auto">
              <h2 className="font-heading text-3xl md:text-4xl font-medium text-[#2D1810] mb-6">
                Why is Purnabramha Famous?
              </h2>
              <ul className="space-y-4 text-[#5C4A3A] font-body text-lg">
                <li className="flex items-start gap-3">
                  <span className="text-[#B8962E] mt-1">✓</span>
                  <span><strong>Authentic Recipes:</strong> Traditional Maharashtrian recipes passed down through generations</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-[#B8962E] mt-1">✓</span>
                  <span><strong>Quality Ingredients:</strong> Fresh, locally-sourced ingredients prepared with care</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-[#B8962E] mt-1">✓</span>
                  <span><strong>Women-Led Brand:</strong> Proud to be a women-led enterprise promoting culinary excellence</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-[#B8962E] mt-1">✓</span>
                  <span><strong>Multiple Services:</strong> Dine-in, pickup, tiffin service, and catering for all occasions</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-[#B8962E] mt-1">✓</span>
                  <span><strong>International Presence:</strong> Serving Maharashtrian food lovers in India and Australia</span>
                </li>
              </ul>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-16 bg-gradient-to-br from-[#3D2314] to-[#2D1810]">
          <div className="container mx-auto px-6 lg:px-12 text-center">
            <h2 className="font-heading text-3xl md:text-4xl font-medium text-white mb-4">
              Experience Authentic Maharashtrian Cuisine
            </h2>
            <p className="text-white/80 font-body mb-8 max-w-xl mx-auto">
              Visit any of our 8 locations or order online for an unforgettable taste of Maharashtra.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Link to="/locations">
                <Button className="gold-glossy text-[#3D2314] font-bold rounded-none px-10 py-6">
                  Find a Location
                </Button>
              </Link>
              <Link to="/menu">
                <Button variant="outline" className="border-white text-white hover:bg-white/10 rounded-none px-10 py-6">
                  View Menu
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </div>
  );
};

export default AboutPurnabramha;
