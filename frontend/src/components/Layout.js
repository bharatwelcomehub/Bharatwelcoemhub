import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Menu, X, User, MapPin, Phone } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import AuthDialog from '@/components/AuthDialog';
import InstallPrompt from '@/components/InstallPrompt';
import { LocationBanner, NearestCenterBanner } from '@/components/LocationBanner';
import { SEOFAQ, SEOInternalLinks } from '@/components/SEOFAQ';
import SEOSchema from '@/components/SEOSchema';

const Layout = ({ children }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [authDialogOpen, setAuthDialogOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const navLinks = [
    { name: 'Home', path: '/' },
    { name: 'Menu', path: '/menu' },
    { name: 'Pickup Order', path: '/pickup' },
    { name: 'Table Booking', path: '/table-booking' },
    { name: 'Tiffin', path: '/tiffin' },
    { name: 'Catering', path: '/catering' },
    { name: 'Locations', path: '/locations' },
    { name: 'Videos', path: '/videos' },
    { name: 'Inspiration', path: '/inspiration' },
    { name: 'Franchise', path: '/franchise' },
    { name: 'About', path: '/about' },
  ];

  const cityLinks = [
    { name: 'Perth', path: '/locations' },
    { name: 'Pune', path: '/locations' },
    { name: 'Thane', path: '/locations' },
    { name: 'Kalyan', path: '/locations' },
    { name: 'Bangalore', path: '/locations' },
    { name: 'Dombivli', path: '/locations' },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-[#0A0505]">
      <SEOSchema />
      <LocationBanner />
      <NearestCenterBanner />
      
      {/* Luxury Dark Header */}
      <header className="sticky top-0 z-50 bg-[#0A0505]/85 backdrop-blur-2xl border-b border-[#D4AF37]/10">
        <nav className="container mx-auto px-4 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <a
              href="/"
              className="flex items-center gap-3"
              data-testid="logo-link"
              onClick={(e) => { e.preventDefault(); navigate('/'); }}
            >
              <img src="/logo.png" alt="Purnabramha" className="h-12 w-auto object-contain" />
            </a>

            <div className="hidden lg:flex items-center gap-0.5">
              {navLinks.map(link => (
                <a
                  key={link.path}
                  href={link.path}
                  className="text-xs xl:text-sm font-body font-medium text-[#A89F95] hover:text-[#D4AF37] transition-colors px-2.5 py-1.5 whitespace-nowrap cursor-pointer tracking-wide"
                  data-testid={`nav-${link.name.toLowerCase().replace(' ', '-')}`}
                  onClick={(e) => { e.preventDefault(); navigate(link.path); }}
                >
                  {link.name}
                </a>
              ))}
            </div>

            <div className="flex items-center space-x-4">
              {user ? (
                <div className="hidden lg:flex items-center space-x-2">
                  <Button
                    variant="ghost"
                    onClick={() => navigate('/profile')}
                    className="text-[#A89F95] hover:text-[#D4AF37] hover:bg-[#D4AF37]/5"
                    data-testid="profile-button"
                  >
                    <User className="h-4 w-4 mr-2" />
                    {user.name}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={logout}
                    className="border-[#D4AF37]/30 text-[#D4AF37] hover:bg-[#D4AF37]/10 rounded-none text-xs tracking-widest uppercase"
                    data-testid="logout-button"
                  >
                    Logout
                  </Button>
                </div>
              ) : (
                <Button
                  onClick={() => setAuthDialogOpen(true)}
                  className="hidden lg:inline-flex bg-[#D4AF37] hover:bg-[#F3D060] text-black rounded-none px-6 text-xs tracking-widest uppercase font-semibold"
                  data-testid="login-button"
                >
                  Login
                </Button>
              )}

              <Button
                variant="ghost"
                size="icon"
                className="lg:hidden text-[#D4AF37]"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                data-testid="mobile-menu-button"
              >
                {mobileMenuOpen ? <X /> : <Menu />}
              </Button>
            </div>
          </div>

          {mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="lg:hidden py-4 border-t border-[#D4AF37]/10"
              data-testid="mobile-menu"
            >
              {navLinks.map(link => (
                <a
                  key={link.path}
                  href={link.path}
                  className="block py-3 text-sm font-body font-medium text-[#A89F95] hover:text-[#D4AF37] cursor-pointer tracking-wide"
                  onClick={(e) => {
                    e.preventDefault();
                    setMobileMenuOpen(false);
                    navigate(link.path);
                  }}
                >
                  {link.name}
                </a>
              ))}
              {user ? (
                <>
                  <button onClick={() => { navigate('/profile'); setMobileMenuOpen(false); }} className="block w-full text-left py-3 text-sm text-[#A89F95] hover:text-[#D4AF37]">Profile</button>
                  <button onClick={() => { logout(); setMobileMenuOpen(false); }} className="block w-full text-left py-3 text-sm text-[#A89F95] hover:text-[#D4AF37]">Logout</button>
                </>
              ) : (
                <Button onClick={() => { setAuthDialogOpen(true); setMobileMenuOpen(false); }} className="w-full mt-3 bg-[#D4AF37] hover:bg-[#F3D060] text-black rounded-none tracking-widest uppercase text-xs">
                  Login / Sign Up
                </Button>
              )}
            </motion.div>
          )}
        </nav>
      </header>

      <main className="flex-1">{children}</main>

      <SEOFAQ />

      {/* Luxury Dark Footer */}
      <footer className="bg-[#0A0505] border-t border-[#D4AF37]/10">
        {/* City Links */}
        <div className="bg-[#080404] py-4 border-b border-[#2A151A]">
          <div className="container mx-auto px-4 lg:px-8">
            <p className="text-xs text-[#A89F95]/50 mb-2 tracking-wider uppercase">Find Maharashtrian Food Near You</p>
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              {cityLinks.map((city) => (
                <Link key={city.name} to={city.path} className="text-xs text-[#D4AF37]/60 hover:text-[#D4AF37] transition-colors">
                  Maharashtrian Food in {city.name}
                </Link>
              ))}
            </div>
          </div>
        </div>
        
        <div className="container mx-auto px-4 lg:px-8 py-16">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            <div>
              <img src="/logo.png" alt="Purnabramha" className="h-14 w-auto mb-5" />
              <p className="text-sm text-[#A89F95]/70 font-body leading-relaxed mb-4">
                World's First Intelligent Restaurant Chain Powered by A.AI Technology
              </p>
              <p className="text-xs text-[#A89F95]/40 font-body">
                Authentic Maharashtrian cuisine across India, USA, Australia & Japan.
              </p>
            </div>
            <div>
              <h4 className="font-heading text-lg text-[#D4AF37] mb-6 tracking-wide">Quick Links</h4>
              <div className="space-y-3">
                {[{n:'Our Menu',p:'/menu'},{n:'Locations',p:'/locations'},{n:'Catering',p:'/catering'},{n:'Franchise',p:'/franchise'}].map(l => (
                  <Link key={l.p} to={l.p} className="block text-sm text-[#A89F95]/70 hover:text-[#D4AF37] transition-colors font-body">
                    {l.n}
                  </Link>
                ))}
              </div>
            </div>
            <div>
              <h4 className="font-heading text-lg text-[#D4AF37] mb-6 tracking-wide">Contact</h4>
              <div className="space-y-3 text-sm text-[#A89F95]/70 font-body">
                <div className="flex items-center">
                  <Phone className="h-4 w-4 mr-3 text-[#D4AF37]/60" />
                  +91 81056 45499
                </div>
                <div className="flex items-center">
                  <MapPin className="h-4 w-4 mr-3 text-[#D4AF37]/60" />
                  India | USA | Australia | Japan
                </div>
              </div>
            </div>
          </div>
          <div className="border-t border-[#2A151A] mt-12 pt-8 text-center">
            <p className="text-xs text-[#A89F95]/30 font-body tracking-wider">
              © 2025 Purnabramha. All rights reserved. Powered by Manaswini Foods Private Limited
            </p>
            <p className="text-[10px] text-[#D4AF37]/20 mt-2 tracking-[0.15em] uppercase">
              Powered by A.AI Technology
            </p>
          </div>
        </div>
      </footer>

      <AuthDialog open={authDialogOpen} onOpenChange={setAuthDialogOpen} />
      <InstallPrompt />
    </div>
  );
};

export default Layout;
