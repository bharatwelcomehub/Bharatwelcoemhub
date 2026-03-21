import { useEffect } from 'react';
import { useSEO } from '@/contexts/SEOContext';

// SEO Head Component - Manages meta tags dynamically
const SEOHead = ({ 
  page = 'home',
  customTitle,
  customDescription,
  customKeywords
}) => {
  const { currentCity, nearestCenter, allCenters } = useSEO();

  // Page-specific SEO configurations
  const pageConfigs = {
    home: {
      title: `Purnabramha – Authentic Maharashtrian Restaurant in ${currentCity} | Vada Pav, Misal, Thali`,
      description: `Experience authentic Maharashtrian vegetarian food at Purnabramha ${currentCity}. Enjoy Vada Pav, Misal Pav, Puran Poli, Thali and more. Find Purnabramha near you.`,
      keywords: `Maharashtrian food near me, Vada Pav near me, Misal Pav, Indian veg restaurant, Purnabramha ${currentCity}, authentic Maharashtrian cuisine`
    },
    menu: {
      title: `Maharashtrian Food Menu | Purnabramha ${currentCity} - Vada Pav, Misal, Thali`,
      description: `Explore our authentic Maharashtrian menu at Purnabramha ${currentCity}. Traditional Vada Pav, Misal Pav, Puran Poli, vegetarian Thali and more Maharashtra delicacies.`,
      keywords: `Maharashtrian menu, Vada Pav, Misal Pav, Puran Poli, vegetarian Thali, Purnabramha menu ${currentCity}`
    },
    pickup: {
      title: `Order Maharashtrian Food Pickup | Purnabramha ${currentCity}`,
      description: `Order authentic Maharashtrian food for pickup at Purnabramha ${currentCity}. Fresh Vada Pav, Misal Pav, Thali ready for collection.`,
      keywords: `Maharashtrian food pickup, order Vada Pav, Misal Pav takeaway, Purnabramha pickup ${currentCity}`
    },
    tiffin: {
      title: `Maharashtrian Tiffin Service | Purnabramha ${currentCity} - Daily Meals`,
      description: `Subscribe to Purnabramha's authentic Maharashtrian tiffin service in ${currentCity}. Daily home-style vegetarian meals delivered fresh.`,
      keywords: `Maharashtrian tiffin service, daily meals, tiffin subscription ${currentCity}, Purnabramha tiffin`
    },
    catering: {
      title: `Maharashtrian Catering Services | Purnabramha ${currentCity}`,
      description: `Premium Maharashtrian catering by Purnabramha in ${currentCity}. Authentic vegetarian food for weddings, parties, and corporate events.`,
      keywords: `Maharashtrian catering, wedding catering ${currentCity}, vegetarian catering, Purnabramha catering`
    },
    tableBooking: {
      title: `Book a Table | Purnabramha ${currentCity} - Maharashtrian Restaurant`,
      description: `Reserve your table at Purnabramha ${currentCity}. Experience authentic Maharashtrian dining with Vada Pav, Misal Pav, and traditional Thali.`,
      keywords: `book table Maharashtrian restaurant, Purnabramha reservation, dining ${currentCity}`
    },
    locations: {
      title: `Purnabramha Locations | Find Maharashtrian Restaurant Near You`,
      description: `Find your nearest Purnabramha restaurant in India and Australia. Authentic Maharashtrian food in Pune, Mumbai, Bangalore, Perth and more.`,
      keywords: `Purnabramha locations, Maharashtrian restaurant near me, Purnabramha India, Purnabramha Australia`
    },
    about: {
      title: `About Purnabramha | Authentic Maharashtrian Restaurant Chain`,
      description: `Learn about Purnabramha - the largest Maharashtrian restaurant chain serving authentic vegetarian cuisine across India and Australia since our humble beginnings.`,
      keywords: `about Purnabramha, Maharashtrian restaurant history, authentic Maharashtra cuisine`
    },
    videos: {
      title: `Purnabramha Videos | Maharashtrian Food & Culture`,
      description: `Watch videos of authentic Maharashtrian cooking, restaurant ambience, and food culture at Purnabramha.`,
      keywords: `Maharashtrian food videos, Purnabramha videos, cooking videos Maharashtra`
    },
    franchise: {
      title: `Purnabramha Franchise Opportunity | Open a Maharashtrian Restaurant`,
      description: `Partner with Purnabramha - India's leading Maharashtrian restaurant chain. Franchise opportunities available across India and internationally.`,
      keywords: `Purnabramha franchise, Maharashtrian restaurant franchise, food business opportunity`
    }
  };

  const config = pageConfigs[page] || pageConfigs.home;
  const title = customTitle || config.title;
  const description = customDescription || config.description;
  const keywords = customKeywords || config.keywords;

  useEffect(() => {
    // Update document title
    document.title = title;

    // Helper function to update or create meta tag
    const updateMetaTag = (name, content, property = false) => {
      const attr = property ? 'property' : 'name';
      let tag = document.querySelector(`meta[${attr}="${name}"]`);
      if (tag) {
        tag.setAttribute('content', content);
      } else {
        tag = document.createElement('meta');
        tag.setAttribute(attr, name);
        tag.setAttribute('content', content);
        document.head.appendChild(tag);
      }
    };

    // Basic meta tags
    updateMetaTag('description', description);
    updateMetaTag('keywords', keywords);

    // OpenGraph tags for social sharing
    updateMetaTag('og:title', title, true);
    updateMetaTag('og:description', description, true);
    updateMetaTag('og:type', 'website', true);
    updateMetaTag('og:site_name', 'Purnabramha', true);
    updateMetaTag('og:locale', 'en_IN', true);
    updateMetaTag('og:image', 'https://purnabramha.com/og-image.jpg', true);

    // Twitter Card tags
    updateMetaTag('twitter:card', 'summary_large_image');
    updateMetaTag('twitter:title', title);
    updateMetaTag('twitter:description', description);

    // Canonical URL
    let canonical = document.querySelector('link[rel="canonical"]');
    if (!canonical) {
      canonical = document.createElement('link');
      canonical.setAttribute('rel', 'canonical');
      document.head.appendChild(canonical);
    }
    canonical.setAttribute('href', window.location.href.split('?')[0]);

    // Geo meta tags if we have location
    if (nearestCenter) {
      updateMetaTag('geo.region', nearestCenter.country === 'India' ? 'IN' : 'AU');
      updateMetaTag('geo.placename', nearestCenter.city);
    }

  }, [title, description, keywords, nearestCenter]);

  return null; // This component only manages head tags
};

export default SEOHead;
