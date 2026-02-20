import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Menu, X, ShoppingCart, User, MapPin, Phone } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import { useCart } from '@/contexts/CartContext';
import AuthDialog from '@/components/AuthDialog';
import InstallPrompt from '@/components/InstallPrompt';

const Layout = ({ children }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [authDialogOpen, setAuthDialogOpen] = useState(false);
  const { user, logout } = useAuth();
  const { getTotalItems } = useCart();
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

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-orange-900/10">
        <nav className="container mx-auto px-4 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <Link to="/" className="flex items-center gap-2" data-testid="logo-link">
              <img 
                src="/logo.png" 
                alt="Purnabramha" 
                className="h-12 w-auto object-contain"
              />
            </Link>

            <div className="hidden lg:flex items-center gap-1 xl:gap-2">
              {navLinks.map(link => (
                <Link
                  key={link.path}
                  to={link.path}
                  className="text-xs xl:text-sm font-manrope font-medium text-foreground hover:text-primary transition-colors px-2 py-1 rounded-md hover:bg-primary/5 whitespace-nowrap"
                  data-testid={`nav-${link.name.toLowerCase().replace(' ', '-')}`}
                >
                  {link.name}
                </Link>
              ))}
            </div>

            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                size="icon"
                className="relative"
                onClick={() => navigate('/pickup')}
                data-testid="cart-button"
              >
                <ShoppingCart className="h-5 w-5" />
                {getTotalItems() > 0 && (
                  <span className="cart-badge" data-testid="cart-count">{getTotalItems()}</span>
                )}
              </Button>

              {user ? (
                <div className="hidden lg:flex items-center space-x-2">
                  <Button
                    variant="ghost"
                    onClick={() => navigate('/profile')}
                    data-testid="profile-button"
                  >
                    <User className="h-5 w-5 mr-2" />
                    {user.name}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={logout}
                    className="rounded-full"
                    data-testid="logout-button"
                  >
                    Logout
                  </Button>
                </div>
              ) : (
                <Button
                  onClick={() => setAuthDialogOpen(true)}
                  className="hidden lg:inline-flex rounded-full bg-primary hover:bg-primary/90"
                  data-testid="login-button"
                >
                  Login / Sign Up
                </Button>
              )}

              <Button
                variant="ghost"
                size="icon"
                className="lg:hidden"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                data-testid="mobile-menu-button"
              >
                {mobileMenuOpen ? <X /> : <Menu />}
              </Button>
            </div>
          </div>

          {mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="lg:hidden py-4 border-t border-orange-900/10"
              data-testid="mobile-menu"
            >
              {navLinks.map(link => (
                <Link
                  key={link.path}
                  to={link.path}
                  className="block py-3 text-sm font-manrope font-medium text-foreground hover:text-primary"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  {link.name}
                </Link>
              ))}
              {user ? (
                <>
                  <button
                    onClick={() => {
                      navigate('/profile');
                      setMobileMenuOpen(false);
                    }}
                    className="block w-full text-left py-3 text-sm font-manrope font-medium text-foreground hover:text-primary"
                  >
                    Profile
                  </button>
                  <button
                    onClick={() => {
                      logout();
                      setMobileMenuOpen(false);
                    }}
                    className="block w-full text-left py-3 text-sm font-manrope font-medium text-foreground hover:text-primary"
                  >
                    Logout
                  </button>
                </>
              ) : (
                <Button
                  onClick={() => {
                    setAuthDialogOpen(true);
                    setMobileMenuOpen(false);
                  }}
                  className="w-full mt-3 rounded-full bg-primary"
                >
                  Login / Sign Up
                </Button>
              )}
            </motion.div>
          )}
        </nav>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="bg-[hsl(20,60%,15%)] text-[hsl(40,50%,85%)] mt-20">
        <div className="container mx-auto px-4 lg:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <img src="/logo.png" alt="Purnabramha" className="h-16 w-auto mb-4" />
              <p className="text-sm text-[hsl(40,30%,70%)] font-manrope">
                The Largest Maharashtrian Restaurant - Authentic cuisine across India, USA, Australia & Japan.
              </p>
            </div>
            <div>
              <h4 className="font-manrope font-semibold mb-4 text-[hsl(38,70%,55%)]">Quick Links</h4>
              <div className="space-y-2">
                <Link to="/menu" className="block text-sm text-[hsl(40,30%,70%)] hover:text-[hsl(38,70%,55%)] transition-colors">
                  Our Menu
                </Link>
                <Link to="/locations" className="block text-sm text-[hsl(40,30%,70%)] hover:text-[hsl(38,70%,55%)] transition-colors">
                  Locations
                </Link>
                <Link to="/catering" className="block text-sm text-[hsl(40,30%,70%)] hover:text-[hsl(38,70%,55%)] transition-colors">
                  Catering Services
                </Link>
                <Link to="/franchise" className="block text-sm text-[hsl(40,30%,70%)] hover:text-[hsl(38,70%,55%)] transition-colors">
                  Franchise
                </Link>
              </div>
            </div>
            <div>
              <h4 className="font-manrope font-semibold mb-4 text-[hsl(38,70%,55%)]">Contact</h4>
              <div className="space-y-2 text-sm text-[hsl(40,30%,70%)]">
                <div className="flex items-center">
                  <Phone className="h-4 w-4 mr-2 text-[hsl(38,70%,55%)]" />
                  +91 81056 45499
                </div>
                <div className="flex items-center">
                  <MapPin className="h-4 w-4 mr-2 text-[hsl(38,70%,55%)]" />
                  India | USA | Australia | Japan
                </div>
              </div>
            </div>
          </div>
          <div className="border-t border-[hsl(40,30%,25%)] mt-8 pt-8 text-center text-sm text-[hsl(40,20%,50%)]">
            <p>© 2025 Purnabramha. All rights reserved. Powered by Manaswini Foods Private Limited</p>
          </div>
        </div>
      </footer>

      <AuthDialog open={authDialogOpen} onOpenChange={setAuthDialogOpen} />
      <InstallPrompt />
    </div>
  );
};

export default Layout;