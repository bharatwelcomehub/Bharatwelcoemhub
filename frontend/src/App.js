import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import { AuthProvider } from '@/contexts/AuthContext';
import { CartProvider } from '@/contexts/CartContext';
import { SEOProvider } from '@/contexts/SEOContext';
import Layout from '@/components/Layout';
import AuthCallback from '@/components/AuthCallback';
import Home from '@/pages/Home';
import Menu from '@/pages/Menu';
import Pickup from '@/pages/Pickup';
import TableBooking from '@/pages/TableBooking';
import Tiffin from '@/pages/Tiffin';
import Catering from '@/pages/Catering';
import Locations from '@/pages/Locations';
import Profile from '@/pages/Profile';
import Admin from '@/pages/Admin';
import Franchise from '@/pages/Franchise';
import Videos from '@/pages/Videos';
import Inspiration from '@/pages/Inspiration';
import About from '@/pages/About';
import LocationSEO from '@/pages/LocationSEO';
import AboutPurnabramha from '@/pages/AboutPurnabramha';
import BookLanding from '@/pages/BookLanding';
import BookReader from '@/pages/BookReader';
import '@/App.css';

// Remove Emergent badge
const removeEmergentBadge = () => {
  const selectors = [
    '#emergent-badge',
    '[id*="emergent"]',
    'a[href*="emergent"]',
    '[class*="emergent"]'
  ];
  
  selectors.forEach(selector => {
    const elements = document.querySelectorAll(selector);
    elements.forEach(el => {
      if (el && el.parentNode) {
        el.parentNode.removeChild(el);
      }
    });
  });
};

function App() {
  // Remove Emergent badge on mount and periodically
  useEffect(() => {
    // Remove immediately
    removeEmergentBadge();
    
    // Remove after short delay (in case it's injected after load)
    const timeouts = [100, 500, 1000, 2000, 5000].map(delay => 
      setTimeout(removeEmergentBadge, delay)
    );
    
    // Also observe DOM changes to remove if added later
    const observer = new MutationObserver(() => {
      removeEmergentBadge();
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
    
    return () => {
      timeouts.forEach(clearTimeout);
      observer.disconnect();
    };
  }, []);

  return (
    <BrowserRouter>
      <AuthProvider>
        <CartProvider>
          <SEOProvider>
            <Routes>
              {/* Auth callback route - without Layout */}
              <Route path="/auth/callback" element={<AuthCallback />} />
              
              {/* Main routes with Layout */}
              <Route path="*" element={
                <Layout>
                  <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/menu" element={<Menu />} />
                    <Route path="/pickup" element={<Pickup />} />
                    <Route path="/table-booking" element={<TableBooking />} />
                    <Route path="/tiffin" element={<Tiffin />} />
                    <Route path="/catering" element={<Catering />} />
                    <Route path="/locations" element={<Locations />} />
                    <Route path="/profile" element={<Profile />} />
                    <Route path="/admin" element={<Admin />} />
                    <Route path="/franchise" element={<Franchise />} />
                    <Route path="/videos" element={<Videos />} />
                    <Route path="/inspiration" element={<Inspiration />} />
                    <Route path="/about" element={<About />} />
                    
                    {/* SEO Location Pages */}
                    <Route path="/maharashtrian-restaurant-hsr-layout-bangalore" element={<LocationSEO />} />
                    <Route path="/maharashtrian-restaurant-sambhajinagar" element={<LocationSEO />} />
                    <Route path="/maharashtrian-restaurant-hinjawadi-pune" element={<LocationSEO />} />
                    <Route path="/maharashtrian-restaurant-kharadi-pune" element={<LocationSEO />} />
                    <Route path="/maharashtrian-restaurant-dombivli" element={<LocationSEO />} />
                    <Route path="/maharashtrian-restaurant-kalyan" element={<LocationSEO />} />
                    <Route path="/maharashtrian-restaurant-thane" element={<LocationSEO />} />
                    <Route path="/maharashtrian-restaurant-perth" element={<LocationSEO />} />
                    
                    {/* AI Knowledge Page */}
                    <Route path="/about-purnabramha-maharashtrian-restaurant" element={<AboutPurnabramha />} />
                    
                    {/* Book Reading Platform */}
                    <Route path="/book" element={<BookLanding />} />
                    <Route path="/book/success" element={<BookLanding />} />
                  </Routes>
                </Layout>
              } />

              {/* Book Reader - Full screen without Layout */}
              <Route path="/book/read/:part" element={<BookReader />} />
            </Routes>
            <Toaster />
          </SEOProvider>
        </CartProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;