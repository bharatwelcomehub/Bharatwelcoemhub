import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BookOpen, Lock, CheckCircle, Bookmark, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const COVER_IMAGE = 'https://customer-assets.emergentagent.com/job_50886080-3950-4b54-8e6a-7e012eaffafc/artifacts/bdlxtuu4_Book_Restaurant_become_Human.png';

const BookLanding = () => {
  const [parts, setParts] = useState([]);
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(null);
  const { user, token } = useAuth();
  const navigate = useNavigate();

  const getRegion = () => localStorage.getItem('purnabramha_country') || 'India';
  const isAustralia = getRegion() === 'Australia';
  const currencySymbol = isAustralia ? '$' : '₹';

  useEffect(() => {
    fetchParts();
    if (user) fetchProgress();
  }, [user]);

  // Check for payment success redirect
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session_id');
    if (sessionId && user) {
      pollPaymentStatus(sessionId);
      window.history.replaceState({}, '', '/book');
    }
  }, [user]);

  const fetchParts = async () => {
    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${API}/api/book/parts`, { headers });
      const data = await res.json();
      setParts(data);
    } catch { /* ignore */ }
    setLoading(false);
  };

  const fetchProgress = async () => {
    try {
      const res = await fetch(`${API}/api/book/progress`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) setProgress(await res.json());
    } catch { /* ignore */ }
  };

  const pollPaymentStatus = async (sessionId, attempts = 0) => {
    if (attempts >= 8) { toast.error('Payment verification timed out. Please refresh.'); return; }
    try {
      const res = await fetch(`${API}/api/book/purchase/status/${sessionId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.payment_status === 'paid') {
        toast.success('Payment successful! Enjoy reading.');
        fetchParts();
        return;
      }
      if (data.status === 'expired') { toast.error('Payment expired. Please try again.'); return; }
      setTimeout(() => pollPaymentStatus(sessionId, attempts + 1), 2000);
    } catch {
      setTimeout(() => pollPaymentStatus(sessionId, attempts + 1), 2000);
    }
  };

  const handlePurchase = async (partNumber) => {
    if (!user) { toast.error('Please login to purchase'); return; }
    setPurchasing(partNumber);
    try {
      const res = await fetch(`${API}/api/book/purchase`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          part_number: partNumber,
          origin_url: window.location.origin,
          region: getRegion()
        })
      });
      const data = await res.json();
      if (data.url) window.location.href = data.url;
      else toast.error(data.detail || 'Payment error');
    } catch { toast.error('Payment failed. Please try again.'); }
    setPurchasing(null);
  };

  const handleRead = (partNumber) => {
    navigate(`/book/read/${partNumber}`);
  };

  // Set page title
  useEffect(() => {
    document.title = 'Purnabramha – When a Restaurant Becomes Human | Book';
  }, []);

  return (
    <div className="min-h-screen bg-[#FDFBF7]">
      {/* Hero Section */}
      <section className="relative py-16 lg:py-24 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-[#3D2314]/5 to-transparent" />
        <div className="container mx-auto px-4 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 items-center">
            {/* Book Cover */}
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8 }}
              className="flex justify-center"
            >
              <div className="relative" data-testid="book-cover">
                <div className="absolute -inset-4 bg-gradient-to-br from-[#D4AF37]/20 to-transparent rounded-2xl blur-2xl" />
                <img
                  src={COVER_IMAGE}
                  alt="Purnabramha – When a Restaurant Becomes Human"
                  className="relative w-[300px] lg:w-[380px] rounded-lg shadow-[0_20px_60px_rgba(61,35,20,0.3)]"
                  style={{ aspectRatio: '2/3', objectFit: 'cover' }}
                />
              </div>
            </motion.div>

            {/* Book Info */}
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body mb-4">A Book by Jayanti Pranav Kathale</p>
              <h1 className="font-heading text-4xl lg:text-5xl text-[#3D2314] mb-3 leading-tight">
                Purnabramha
              </h1>
              <p className="font-heading text-xl lg:text-2xl text-[#B8962E] mb-6 italic">
                When a Restaurant Becomes Human
              </p>
              <p className="text-base text-[#5C4A3A] font-body leading-relaxed mb-8">
                The story of how a small Maharashtrian kitchen became a movement.
                How tradition met technology. How food became philosophy.
                152 pages of wisdom, love, and the journey of Purnabramha.
              </p>

              <div className="flex items-center gap-6 mb-8">
                <div className="text-center">
                  <p className="text-2xl font-heading text-[#B8962E]">152</p>
                  <p className="text-xs text-[#7A6F65] font-body">Pages</p>
                </div>
                <div className="w-px h-10 bg-[#E8DFD0]" />
                <div className="text-center">
                  <p className="text-2xl font-heading text-[#B8962E]">3</p>
                  <p className="text-xs text-[#7A6F65] font-body">Parts</p>
                </div>
                <div className="w-px h-10 bg-[#E8DFD0]" />
                <div className="text-center">
                  <p className="text-2xl font-heading text-[#B8962E]">{currencySymbol}{parts.length > 0 ? (isAustralia ? parts[0].price_aud : parts[0].price_inr) : '50'}</p>
                  <p className="text-xs text-[#7A6F65] font-body">Per Part</p>
                </div>
              </div>

              {progress && progress.last_page > 1 && (
                <Button
                  onClick={() => handleRead(progress.last_part)}
                  className="gold-glossy text-[#3D2314] font-bold rounded-none px-8 py-3 text-sm tracking-widest uppercase border-0 mb-4"
                  data-testid="continue-reading-btn"
                >
                  <BookOpen className="w-4 h-4 mr-2" />
                  Continue Reading (Page {progress.last_page})
                </Button>
              )}
            </motion.div>
          </div>
        </div>
      </section>

      {/* Parts Section */}
      <section className="py-16 bg-white border-t border-b border-[#E8DFD0]">
        <div className="container mx-auto px-4 lg:px-8">
          <h2 className="text-center font-heading text-2xl text-[#3D2314] mb-2">Choose Your Reading Journey</h2>
          <p className="text-center text-sm text-[#7A6F65] font-body mb-12">Purchase each part separately. Read at your own pace.</p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            {parts.map((part) => (
              <motion.div
                key={part.part_number}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: part.part_number * 0.15 }}
                className="border border-[#E8DFD0] rounded-xl overflow-hidden hover:shadow-lg transition-shadow"
                data-testid={`book-part-${part.part_number}`}
              >
                <div className="bg-gradient-to-br from-[#3D2314] to-[#5A3520] p-6 text-center">
                  <BookOpen className="w-8 h-8 text-[#D4AF37] mx-auto mb-3" />
                  <h3 className="font-heading text-xl text-[#D4AF37]">{part.name}</h3>
                  <p className="text-[#D4AF37]/60 text-xs font-body mt-1">Pages {part.pages}</p>
                </div>

                <div className="p-6 bg-[#FDFBF7]">
                  <div className="flex items-center justify-between mb-6">
                    <span className="text-2xl font-heading text-[#B8962E]">
                      {currencySymbol}{isAustralia ? part.price_aud : part.price_inr}
                    </span>
                    {part.purchased ? (
                      <span className="flex items-center gap-1 text-green-600 text-xs font-body">
                        <CheckCircle className="w-4 h-4" /> Purchased
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-[#7A6F65] text-xs font-body">
                        <Lock className="w-3.5 h-3.5" /> Locked
                      </span>
                    )}
                  </div>

                  {part.purchased ? (
                    <Button
                      onClick={() => handleRead(part.part_number)}
                      className="w-full gold-glossy text-[#3D2314] font-bold rounded-none text-xs tracking-widest uppercase border-0"
                      data-testid={`read-part-${part.part_number}`}
                    >
                      <BookOpen className="w-4 h-4 mr-2" />
                      Read Now
                    </Button>
                  ) : (
                    <Button
                      onClick={() => handlePurchase(part.part_number)}
                      disabled={purchasing === part.part_number || !user}
                      className="w-full bg-[#3D2314] text-[#D4AF37] hover:bg-[#5A3520] font-bold rounded-none text-xs tracking-widest uppercase"
                      data-testid={`buy-part-${part.part_number}`}
                    >
                      {purchasing === part.part_number ? 'Processing...' : !user ? 'Login to Purchase' : `Buy for ${currencySymbol}${isAustralia ? part.price_aud : part.price_inr}`}
                    </Button>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Philosophy Quote */}
      <section className="py-20 text-center">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 1 }}
          >
            <p className="font-heading text-2xl lg:text-3xl text-[#3D2314] italic leading-relaxed max-w-2xl mx-auto mb-6">
              "Food is not just eating.<br />It is wisdom."
            </p>
            <p className="text-sm text-[#B8962E] font-body tracking-wider">— Vahini | Purnabramha</p>
          </motion.div>
        </div>
      </section>

      {/* Reading Features */}
      <section className="py-16 bg-[#F8F5F0] border-t border-[#E8DFD0]">
        <div className="container mx-auto px-4 lg:px-8">
          <h2 className="text-center font-heading text-xl text-[#3D2314] mb-10">A Premium Reading Experience</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl mx-auto">
            {[
              { icon: '📖', title: 'Page Flip', desc: 'Realistic book feel' },
              { icon: '🔖', title: 'Bookmarks', desc: 'Save your place' },
              { icon: '🎵', title: 'Calm Music', desc: 'Optional ambience' },
              { icon: '🔒', title: 'Protected', desc: 'Secure reading' }
            ].map((f, i) => (
              <div key={i} className="text-center p-4">
                <span className="text-2xl mb-2 block">{f.icon}</span>
                <p className="text-sm font-heading text-[#3D2314]">{f.title}</p>
                <p className="text-[10px] text-[#7A6F65] font-body mt-1">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default BookLanding;
