import { useSEO } from '@/contexts/SEOContext';
import centersData from '@/config/centers.json';

// Local Business Schema for each center
const generateLocalBusinessSchema = (center, coordinates) => ({
  "@context": "https://schema.org",
  "@type": "Restaurant",
  "name": `Purnabramha ${center.displayName}`,
  "image": "https://purnabramha.com/logo.png",
  "url": "https://purnabramha.com",
  "@id": `https://purnabramha.com/locations#${center.id}`,
  "telephone": center.phone,
  "address": {
    "@type": "PostalAddress",
    "streetAddress": center.address,
    "addressLocality": center.city,
    "addressRegion": center.state,
    "addressCountry": center.country === 'India' ? 'IN' : 'AU'
  },
  "geo": coordinates ? {
    "@type": "GeoCoordinates",
    "latitude": coordinates.lat,
    "longitude": coordinates.lng
  } : undefined,
  "openingHoursSpecification": [
    {
      "@type": "OpeningHoursSpecification",
      "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
      "opens": "11:00",
      "closes": "22:00"
    }
  ],
  "servesCuisine": ["Maharashtrian", "Indian Vegetarian", "South Asian"],
  "priceRange": center.country === 'India' ? "₹₹" : "$$",
  "acceptsReservations": "True",
  "menu": "https://purnabramha.com/menu",
  "hasMenu": {
    "@type": "Menu",
    "name": "Purnabramha Menu",
    "description": "Authentic Maharashtrian vegetarian cuisine"
  },
  "areaServed": {
    "@type": "City",
    "name": center.city
  }
});

// Center coordinates
const centerCoordinates = {
  'pb-hsr': { lat: 12.9121, lng: 77.6446 },
  'pb-sambhajinagar': { lat: 19.8762, lng: 75.3433 },
  'pb-thane': { lat: 19.2183, lng: 72.9781 },
  'pb-dombivli': { lat: 19.2183, lng: 73.0867 },
  'pb-kharadi': { lat: 18.5530, lng: 73.9422 },
  'pb-hinjawadi': { lat: 18.5912, lng: 73.7380 },
  'pb-kalyan': { lat: 19.2437, lng: 73.1355 },
  'pb-perth': { lat: -31.9505, lng: 115.8605 }
};

// Organization Schema
const organizationSchema = {
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Purnabramha",
  "alternateName": "Purnabramha Maharashtrian Restaurant",
  "url": "https://purnabramha.com",
  "logo": "https://purnabramha.com/logo.png",
  "description": "The Largest Maharashtrian Restaurant Chain - Authentic cuisine across India, USA, Australia & Japan",
  "foundingDate": "2012",
  "sameAs": [
    "https://www.facebook.com/purnabramha",
    "https://www.instagram.com/purnabramha",
    "https://www.youtube.com/@purnabramha"
  ],
  "contactPoint": {
    "@type": "ContactPoint",
    "telephone": "+91-81056-45499",
    "contactType": "customer service",
    "areaServed": ["IN", "AU", "US", "JP"],
    "availableLanguage": ["English", "Hindi", "Marathi"]
  }
};

// FAQ Schema
const generateFAQSchema = (city) => ({
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Where can I find Maharashtrian food near me?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": `Visit Purnabramha in ${city} for authentic vegetarian Maharashtrian cuisine including Vada Pav, Misal Pav, Puran Poli, and traditional Thali.`
      }
    },
    {
      "@type": "Question",
      "name": "Does Purnabramha serve Vada Pav and Misal Pav?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes, Purnabramha serves authentic Vada Pav, Misal Pav, Thali, and over 150 traditional Maharashtrian dishes prepared with authentic recipes."
      }
    },
    {
      "@type": "Question",
      "name": "Where is Purnabramha located?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Purnabramha has multiple locations across India (Bangalore, Pune, Mumbai, Thane, Kalyan, Dombivli, Chhatrapati Sambhajinagar) and Australia (Perth). Visit our locations page to find the nearest center."
      }
    },
    {
      "@type": "Question",
      "name": "Is Purnabramha vegetarian?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes, Purnabramha is a 100% pure vegetarian restaurant serving authentic Maharashtrian cuisine. We do not serve any non-vegetarian items."
      }
    },
    {
      "@type": "Question",
      "name": "Does Purnabramha offer tiffin service?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes, we offer daily tiffin service with authentic Maharashtrian home-style meals. We also have an Unlimited Breakfast offer at select locations."
      }
    }
  ]
});

// Website Schema
const websiteSchema = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "Purnabramha",
  "url": "https://purnabramha.com",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://purnabramha.com/menu?search={search_term_string}",
    "query-input": "required name=search_term_string"
  }
};

const SEOSchema = () => {
  const { currentCity, nearestCenter } = useSEO();
  const allCenters = [...centersData.india, ...centersData.australia];

  // Generate schemas
  const schemas = [
    organizationSchema,
    websiteSchema,
    generateFAQSchema(currentCity)
  ];

  // Add local business schema for nearest center or all centers on locations page
  if (nearestCenter) {
    schemas.push(generateLocalBusinessSchema(nearestCenter, centerCoordinates[nearestCenter.id]));
  } else {
    // Add all centers on generic pages
    allCenters.forEach(center => {
      schemas.push(generateLocalBusinessSchema(center, centerCoordinates[center.id]));
    });
  }

  return (
    <>
      {schemas.map((schema, index) => (
        <script
          key={index}
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
        />
      ))}
    </>
  );
};

export default SEOSchema;
