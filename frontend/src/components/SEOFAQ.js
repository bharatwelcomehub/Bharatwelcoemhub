import { useSEO } from '@/contexts/SEOContext';
import { Link } from 'react-router-dom';

// SEO FAQ Section for Footer
const SEOFAQ = () => {
  const { currentCity } = useSEO();

  const faqs = [
    {
      question: "Where can I find Maharashtrian food near me?",
      answer: `Visit Purnabramha in ${currentCity} for authentic vegetarian Maharashtrian cuisine including Vada Pav, Misal Pav, and traditional Thali.`
    },
    {
      question: "Does Purnabramha serve Vada Pav and Misal Pav?",
      answer: "Yes, we serve authentic Vada Pav, Misal Pav, Thali and traditional Maharashtrian dishes prepared with authentic recipes."
    },
    {
      question: "Where is Purnabramha located?",
      answer: "Multiple locations across India (Bangalore, Pune, Mumbai, Thane) and Australia (Perth). Visit the nearest center."
    }
  ];

  return (
    <section className="bg-[#f5f0e8] py-8 border-t border-[#e0d5c5]" itemScope itemType="https://schema.org/FAQPage">
      <div className="container mx-auto px-4">
        <h2 className="text-xl font-playfair font-semibold text-[#5c1e1e] mb-4">
          Frequently Asked Questions
        </h2>
        <div className="grid md:grid-cols-3 gap-4">
          {faqs.map((faq, index) => (
            <div 
              key={index} 
              className="bg-white p-4 rounded-lg shadow-sm"
              itemScope 
              itemProp="mainEntity" 
              itemType="https://schema.org/Question"
            >
              <h3 
                className="font-semibold text-sm text-[#5c1e1e] mb-2"
                itemProp="name"
              >
                {faq.question}
              </h3>
              <div itemScope itemProp="acceptedAnswer" itemType="https://schema.org/Answer">
                <p 
                  className="text-xs text-gray-600"
                  itemProp="text"
                >
                  {faq.answer}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// SEO Internal Links for Footer
const SEOInternalLinks = () => {
  const cities = [
    { name: 'Perth', slug: 'perth' },
    { name: 'Pune', slug: 'pune' },
    { name: 'Thane', slug: 'thane' },
    { name: 'Kalyan', slug: 'kalyan' },
    { name: 'Bangalore', slug: 'bangalore' },
    { name: 'Dombivli', slug: 'dombivli' }
  ];

  return (
    <div className="py-4 border-t border-[#e0d5c5]">
      <div className="container mx-auto px-4">
        <p className="text-xs text-gray-500 mb-2">Find Maharashtrian Food Near You:</p>
        <div className="flex flex-wrap gap-2">
          {cities.map((city) => (
            <Link
              key={city.slug}
              to="/locations"
              className="text-xs text-[#5c1e1e] hover:underline"
              title={`Maharashtrian Food in ${city.name}`}
            >
              Maharashtrian Food in {city.name}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};

export { SEOFAQ, SEOInternalLinks };
