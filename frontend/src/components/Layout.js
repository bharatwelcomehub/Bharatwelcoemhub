import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Menu, X, ShoppingCart, User, MapPin, Phone } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import { useCart } from '@/contexts/CartContext';
import AuthDialog from '@/components/AuthDialog';

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
  ];

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-orange-900/10">
        <nav className="container mx-auto px-4 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <Link to="/" className="flex items-center" data-testid="logo-link">
              <h1 className="text-2xl lg:text-3xl font-playfair font-bold text-primary tracking-tight">
                Purnabramha
              </h1>
            </Link>

            <div className="hidden lg:flex items-center space-x-8">
              {navLinks.map(link => (
                <Link
                  key={link.path}
                  to={link.path}
                  className="text-sm font-manrope font-medium text-foreground hover:text-primary transition-colors"
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

      <footer className="bg-secondary text-white mt-20">
        <div className="container mx-auto px-4 lg:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <h3 className="text-2xl font-playfair font-bold mb-4">Purnabramha</h3>
              <p className="text-sm text-white/80 font-manrope">
                Authentic Maharashtrian cuisine across 8 locations in India and Australia.
              </p>
            </div>
            <div>
              <h4 className="font-manrope font-semibold mb-4">Quick Links</h4>
              <div className="space-y-2">
                <Link to="/menu" className="block text-sm text-white/80 hover:text-white transition-colors">
                  Our Menu
                </Link>
                <Link to="/locations" className="block text-sm text-white/80 hover:text-white transition-colors">
                  Locations
                </Link>
                <Link to="/catering" className="block text-sm text-white/80 hover:text-white transition-colors">
                  Catering Services
                </Link>
              </div>
            </div>
            <div>
              <h4 className="font-manrope font-semibold mb-4">Contact</h4>
              <div className="space-y-2 text-sm text-white/80">
                <div className="flex items-center">
                  <Phone className="h-4 w-4 mr-2" />
                  +91 81056 45499
                </div>
                <div className="flex items-center">
                  <MapPin className="h-4 w-4 mr-2" />
                  Multiple Locations
                </div>
              </div>
            </div>
          </div>
          <div className="border-t border-white/10 mt-8 pt-8 text-center text-sm text-white/60">
            <p>© 2025 Purnabramha. All rights reserved. Powered by Manaswini Foods Private Limited</p>
          </div>
        </div>
      </footer>

      <AuthDialog open={authDialogOpen} onOpenChange={setAuthDialogOpen} />
    </div>
  );
};

export default Layout;