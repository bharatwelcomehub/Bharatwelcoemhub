import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BookOpen, Lock, CheckCircle, Bookmark, ArrowRight, Headphones, CreditCard, Smartphone, X, Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';
import AuthDialog from '@/components/AuthDialog';
import BookPodcastPlayer from '@/components/BookPodcastPlayer';

const API = process.env.REACT_APP_BACKEND_URL;
const COVER_IMAGE = 'https://customer-assets.emergentagent.com/job_50886080-3950-4b54-8e6a-7e012eaffafc/artifacts/bdlxtuu4_Book_Restaurant_become_Human.png';
const UPI_QR_PART = '/upi_qr_50.png';
const UPI_QR_BUNDLE = '/upi_qr_bundle.png';

const BookLanding = () => {
  const [parts, setParts] = useState([]);
  const [bundle, setBundle] = useState(null);
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(null);
  const [authDialogOpen, setAuthDialogOpen] = useState(false);
  const [showUpiModal, setShowUpiModal] = useState(null); // {type, part_number, amount}
  const [upiPaymentId, setUpiPaymentId] = useState(null);
  const [upiRef, setUpiRef] = useState('');
  const [upiSubmitted, setUpiSubmitted] = useState(false);
  const [copiedUpi, setCopiedUpi] = useState(false);
  const [pendingPurchase, setPendingPurchase] = useState(null);
  const [showPodcast, setShowPodcast] = useState(false);
  const [listenEnabled, setListenEnabled] = useState(true);
  const { user, token } = useAuth();
  const navigate = useNavigate();

  const getRegion = () => localStorage.getItem('purnabramha_country') || 'India';
  const isAustralia = getRegion() === 'Australia';
  const currencySymbol = isAustralia ? '$' : '₹';

  useEffect(() => {
    fetchParts();
    if (user) fetchProgress();
    fetch(`${API}/api/book/settings`).then(r => r.json()).then(d => setListenEnabled(d.listen_enabled !== false)).catch(() => {});
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
      setParts(data.parts || data);
      if (data.bundle) setBundle(data.bundle);
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
    if (!user) {
      localStorage.setItem('auth_return_to', '/book');
      localStorage.setItem('pending_book_purchase', String(partNumber));
      setPendingPurchase(partNumber);
      setAuthDialogOpen(true);
      return;
    }
    if (getRegion() === 'Australia') {
      executePurchase(partNumber);
    } else {
      const price = parts.find(p => p.part_number === partNumber)?.price_inr || 50;
      setShowUpiModal({ type: 'part', part_number: partNumber, amount: price });
    }
  };

  const executePurchase = async (partNumber) => {
    setPurchasing(partNumber);
    try {
      const currentToken = localStorage.getItem('token') || token;
      const res = await fetch(`${API}/api/book/purchase`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${currentToken}` },
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

  const handleBundlePurchase = async () => {
    if (!user) {
      localStorage.setItem('auth_return_to', '/book');
      localStorage.setItem('pending_book_purchase', 'bundle');
      setPendingPurchase('bundle');
      setAuthDialogOpen(true);
      return;
    }
    if (getRegion() === 'Australia') {
      executeBundlePurchase();
    } else {
      setShowUpiModal({ type: 'bundle', part_number: null, amount: bundle?.price_inr || 50 });
    }
  };

  const executeBundlePurchase = async () => {
    setPurchasing('bundle');
    try {
      const currentToken = localStorage.getItem('token') || token;
      const res = await fetch(`${API}/api/book/purchase-bundle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${currentToken}` },
        body: JSON.stringify({
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

  // UPI Payment Flow
  const startUpiPayment = async () => {
    const currentToken = localStorage.getItem('token') || token;
    try {
      const res = await fetch(`${API}/api/book/upi-payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${currentToken}` },
        body: JSON.stringify({ type: showUpiModal.type, part_number: showUpiModal.part_number })
      });
      const data = await res.json();
      setUpiPaymentId(data.payment_id);
    } catch { toast.error('Failed to create payment'); }
  };

  useEffect(() => {
    if (showUpiModal && user) startUpiPayment();
  }, [showUpiModal]);

  const confirmUpiPayment = async () => {
    if (!upiPaymentId) return;
    const currentToken = localStorage.getItem('token') || token;
    try {
      await fetch(`${API}/api/book/upi-confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${currentToken}` },
        body: JSON.stringify({ payment_id: upiPaymentId, upi_ref: upiRef })
      });
      setUpiSubmitted(true);
      toast.success('Payment submitted! Access will be granted shortly.');
    } catch { toast.error('Failed to confirm payment'); }
  };

  const closeUpiModal = () => {
    setShowUpiModal(null); setUpiPaymentId(null); setUpiRef(''); setUpiSubmitted(false); setCopiedUpi(false);
  };

  const copyUpiId = () => {
    navigator.clipboard.writeText('jayanti.devashree-7@okaxis');
    setCopiedUpi(true);
    setTimeout(() => setCopiedUpi(false), 2000);
  };

  // After login, auto-trigger the pending purchase
  useEffect(() => {
    if (user) {
      const pending = pendingPurchase || localStorage.getItem('pending_book_purchase');
      if (pending) {
        setPendingPurchase(null);
        localStorage.removeItem('pending_book_purchase');
        if (pending === 'bundle') {
          setTimeout(() => executeBundlePurchase(), 500);
        } else {
          setTimeout(() => executePurchase(parseInt(pending)), 500);
        }
      }
    }
  }, [user]);

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

              {listenEnabled && (
                <Button
                  onClick={() => {
                    // Check if user has any purchased parts
                    const hasPurchased = parts.some(p => p.purchased);
                    if (hasPurchased) {
                      setShowPodcast(true);
                    } else {
                      // Scroll to purchase section
                      document.getElementById('book-parts')?.scrollIntoView({ behavior: 'smooth' });
                      toast('Purchase a part first to start listening', { icon: '🎧' });
                    }
                  }}
                  variant="outline"
                  className="border border-[#B8962E]/40 text-[#B8962E] hover:bg-[#B8962E]/10 rounded-none px-8 py-3 text-sm tracking-widest uppercase mb-4"
                  data-testid="listen-book-btn"
                >
                  <Headphones className="w-4 h-4 mr-2" />
                  Listen to the Book
                </Button>
              )}
            </motion.div>
          </div>
        </div>
      </section>

      {/* Parts Section */}
      <section id="book-parts" className="py-16 bg-white border-t border-b border-[#E8DFD0]">
        <div className="container mx-auto px-4 lg:px-8">
          <h2 className="text-center font-heading text-2xl text-[#3D2314] mb-2">Choose Your Reading Journey</h2>
          <p className="text-center text-sm text-[#7A6F65] font-body mb-8">Purchase individual parts or get the complete book at a discount.</p>

          {/* Bundle Card — Best Value */}
          {bundle && !bundle.all_purchased && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="max-w-lg mx-auto mb-10 border-2 border-[#D4AF37] rounded-xl overflow-hidden shadow-lg relative"
              data-testid="book-bundle"
            >
              <div className="absolute top-3 right-3 bg-[#D4AF37] text-[#3D2314] text-[10px] font-body font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                Best Value — Save {currencySymbol}{isAustralia ? (bundle.original_aud - bundle.price_aud).toFixed(2) : (bundle.original_inr - bundle.price_inr)}
              </div>
              <div className="bg-gradient-to-r from-[#3D2314] via-[#5A3520] to-[#3D2314] p-6 text-center">
                <h3 className="font-heading text-2xl text-[#D4AF37] mb-1">Complete Book</h3>
                <p className="text-[#D4AF37]/50 text-xs font-body">All 3 Parts — 152 Pages — Read + Listen</p>
              </div>
              <div className="p-6 bg-[#FDFBF7] flex items-center justify-between">
                <div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-heading text-[#B8962E]">
                      {currencySymbol}{isAustralia ? bundle.price_aud : bundle.price_inr}
                    </span>
                    <span className="text-lg font-body text-[#7A6F65] line-through">
                      {currencySymbol}{isAustralia ? bundle.original_aud : bundle.original_inr}
                    </span>
                  </div>
                  <p className="text-[10px] text-[#7A6F65] font-body mt-1">One-time payment for the complete book</p>
                </div>
                <Button
                  onClick={handleBundlePurchase}
                  disabled={purchasing === 'bundle'}
                  className="gold-glossy text-[#3D2314] font-bold rounded-none px-8 py-3 text-sm tracking-widest uppercase border-0"
                  data-testid="buy-bundle"
                >
                  {purchasing === 'bundle' ? 'Processing...' : 'Buy Complete Book'}
                </Button>
              </div>
            </motion.div>
          )}

          {/* Divider */}
          {bundle && !bundle.all_purchased && (
            <div className="flex items-center gap-4 max-w-4xl mx-auto mb-8">
              <div className="flex-1 border-t border-[#E8DFD0]" />
              <span className="text-xs text-[#7A6F65] font-body">or buy individual parts</span>
              <div className="flex-1 border-t border-[#E8DFD0]" />
            </div>
          )}

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
                      disabled={purchasing === part.part_number}
                      className="w-full bg-[#3D2314] text-[#D4AF37] hover:bg-[#5A3520] font-bold rounded-none text-xs tracking-widest uppercase"
                      data-testid={`buy-part-${part.part_number}`}
                    >
                      {purchasing === part.part_number ? 'Processing...' : `Buy for ${currencySymbol}${isAustralia ? part.price_aud : part.price_inr}`}
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

      {/* Auth Dialog for purchase flow */}
      <AuthDialog open={authDialogOpen} onOpenChange={setAuthDialogOpen} />

      {/* Podcast Player */}
      {listenEnabled && (
        <BookPodcastPlayer visible={showPodcast} onClose={() => setShowPodcast(false)} />
      )}

      {/* UPI Payment Modal */}
      {showUpiModal && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-[#FDFBF7] rounded-2xl max-w-md w-full overflow-hidden shadow-2xl"
            data-testid="upi-modal"
          >
            {/* Header */}
            <div className="bg-gradient-to-r from-[#3D2314] to-[#5A3520] p-5 flex items-center justify-between">
              <div>
                <h3 className="text-[#D4AF37] font-heading text-lg">Pay {currencySymbol}{showUpiModal.amount}</h3>
                <p className="text-[#D4AF37]/50 text-xs font-body">{showUpiModal.type === 'bundle' ? 'Complete Book' : `Part ${showUpiModal.part_number}`}</p>
              </div>
              <button onClick={closeUpiModal} className="text-[#D4AF37]/50 hover:text-[#D4AF37]">
                <X className="w-5 h-5" />
              </button>
            </div>

            {!upiSubmitted ? (
              <div className="p-6">
                {/* Payment Method Choice */}
                <p className="text-sm font-body text-[#7A6F65] mb-4 text-center">Choose payment method</p>

                {/* UPI Option */}
                <div className="border-2 border-[#D4AF37] rounded-xl p-4 mb-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Smartphone className="w-5 h-5 text-[#B8962E]" />
                    <span className="font-heading text-[#3D2314] text-sm">UPI / GPay / PhonePe</span>
                    <span className="ml-auto text-[8px] bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-body font-bold">RECOMMENDED</span>
                  </div>

                  {/* QR Code - Amount locked */}
                  <div className="flex justify-center mb-3">
                    <img
                      src={showUpiModal.type === 'bundle' ? UPI_QR_BUNDLE : UPI_QR_PART}
                      alt="UPI QR Code"
                      className="w-48 h-48 rounded-lg border border-[#E8DFD0]"
                    />
                  </div>
                  <p className="text-[9px] text-green-600 font-body text-center mb-2 font-semibold">Amount ₹{showUpiModal.amount} is locked in QR — cannot be changed</p>

                  {/* UPI ID */}
                  <div className="flex items-center gap-2 bg-[#F8F5F0] rounded-lg p-2 mb-3">
                    <span className="flex-1 text-xs font-body text-[#3D2314] font-mono">jayanti.devashree-7@okaxis</span>
                    <button onClick={copyUpiId} className="p-1.5 rounded text-[#B8962E] hover:bg-[#D4AF37]/10">
                      {copiedUpi ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>

                  <p className="text-[10px] text-[#7A6F65] font-body text-center mb-3">
                    Scan QR or pay {currencySymbol}{showUpiModal.amount} to the UPI ID above
                  </p>

                  {/* Confirmation */}
                  <input
                    type="text"
                    value={upiRef}
                    onChange={(e) => setUpiRef(e.target.value)}
                    placeholder="Enter UPI transaction reference (optional)"
                    className="w-full text-xs font-body bg-white border border-[#E8DFD0] rounded-lg px-3 py-2 mb-3 focus:outline-none focus:border-[#D4AF37]"
                    data-testid="upi-ref-input"
                  />

                  <Button
                    onClick={confirmUpiPayment}
                    className="w-full gold-glossy text-[#3D2314] font-bold rounded-lg text-xs tracking-widest uppercase border-0"
                    data-testid="upi-confirm-btn"
                  >
                    I've Paid — Verify My Payment
                  </Button>
                </div>

                {/* Card Option */}
                <button
                  onClick={() => {
                    closeUpiModal();
                    if (showUpiModal.type === 'bundle') executeBundlePurchase();
                    else executePurchase(showUpiModal.part_number);
                  }}
                  className="w-full flex items-center justify-center gap-2 py-3 border border-[#E8DFD0] rounded-xl text-xs font-body text-[#7A6F65] hover:border-[#B8962E] hover:text-[#B8962E] transition-all"
                  data-testid="card-pay-btn"
                >
                  <CreditCard className="w-4 h-4" />
                  Pay with Card (Stripe)
                </button>
              </div>
            ) : (
              /* Success State */
              <div className="p-8 text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-100 flex items-center justify-center">
                  <CheckCircle className="w-8 h-8 text-green-600" />
                </div>
                <h3 className="font-heading text-xl text-[#3D2314] mb-2">Payment Submitted</h3>
                <p className="text-sm text-[#7A6F65] font-body mb-1">Reference: {upiPaymentId}</p>
                <p className="text-xs text-[#7A6F65] font-body mb-6">Your access will be activated shortly after verification.</p>
                <Button onClick={closeUpiModal} className="bg-[#3D2314] text-[#D4AF37] hover:bg-[#5A3520] rounded-lg px-6">
                  Done
                </Button>
              </div>
            )}
          </motion.div>
        </div>
      )}
    </div>
  );
};

export default BookLanding;
