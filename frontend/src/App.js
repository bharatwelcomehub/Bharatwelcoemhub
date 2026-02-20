import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import { AuthProvider } from '@/contexts/AuthContext';
import { CartProvider } from '@/contexts/CartContext';
import Layout from '@/components/Layout';
import Home from '@/pages/Home';
import Menu from '@/pages/Menu';
import Pickup from '@/pages/Pickup';
import TableBooking from '@/pages/TableBooking';
import Tiffin from '@/pages/Tiffin';
import Catering from '@/pages/Catering';
import Locations from '@/pages/Locations';
import Profile from '@/pages/Profile';
import Admin from '@/pages/Admin';
import '@/App.css';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <CartProvider>
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
            </Routes>
          </Layout>
          <Toaster />
        </CartProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;