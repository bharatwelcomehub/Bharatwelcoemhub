import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { motion } from 'framer-motion';
import {
  Flower2, Calendar, Users, MapPin, Phone, Mail, MessageCircle, Share2,
  Copy, Check, Loader2, Sparkles, AlertTriangle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import SEOHead from '@/components/SEOHead';

const API = process.env.REACT_APP_BACKEND_URL;

export default function CelebrationQuote() {
  const { bookingId } = useParams();
  const [booking, setBooking] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        // No public booking endpoint exists by id alone, so we use the quotation endpoint
        // and a small "preview" fetch for booking summary fields. The quotation endpoint
        // returns the formatted text and booking_id; we'll also fetch /wedding/bookings/{id}
        const [qRes, cfgRes] = await Promise.all([
          axios.get(`${API}/api/wedding/quotation/${bookingId}`),
          axios.get(`${API}/api/wedding/config`),
        ]);
        setCfg(cfgRes.data);
        // Parse the plain-text quote for display (we already have estimate snapshot via separate endpoint below)
        // Fetch the booking record via public quote-detail endpoint
        const b = await axios.get(`${API}/api/wedding/bookings/${bookingId}`);
        setBooking({ ...b.data, _quote_text: qRes.data?.content || '' });
      } catch (e) {
        setError(e?.response?.status === 404 ? 'Quotation not found. The link may be invalid.' : 'Unable to load quotation. Please try again later.');
      } finally {
        setLoading(false);
      }
    };
    if (bookingId) fetchAll();
  }, [bookingId]);

  if (loading) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-[#B8962E]" /></div>;
  if (error || !booking) return (
    <div className="min-h-screen flex items-center justify-center p-6 text-center">
      <div>
        <AlertTriangle className="h-12 w-12 mx-auto text-[#B8962E] mb-3" />
        <p className="font-heading text-xl text-[#3D2314]">Quotation Unavailable</p>
        <p className="text-sm text-[#7A6F65] mt-2 max-w-md">{error}</p>
      </div>
    </div>
  );

  const sym = booking.country === 'Australia' ? '$' : '₹';
  const est = booking.estimate || {};
  const url = `${window.location.origin}/quote/${bookingId}`;

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      toast.success('Link copied to clipboard');
      setTimeout(() => setCopied(false), 2500);
    } catch {
      toast.error('Could not copy link');
    }
  };

  const shareWhatsApp = () => {
    const msg = encodeURIComponent(`*Celebration Quotation — Purnabramha*\n\n${booking.event_type} for ${booking.name}\n${booking.center_name}\n${booking.event_date}, ${booking.guest_count} guests\nTotal: ${sym}${(est.total || 0).toLocaleString('en-IN')} (incl. ${est.gst_pct || 0}% GST)\n\nView full quotation: ${url}`);
    window.open(`https://wa.me/?text=${msg}`, '_blank');
  };

  const nativeShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Purnabramha Celebration Quotation',
          text: `${booking.event_type} for ${booking.name} — ${sym}${(est.total || 0).toLocaleString('en-IN')}`,
          url,
        });
      } catch {}
    } else {
      copyLink();
    }
  };

  return (
    <div className="min-h-screen bg-[#FDFBF7]">
      <SEOHead page="quote" title="Celebration Quotation | Purnabramha" description="Personalized celebration quotation from Purnabramha." />

      {/* Hero header */}
      <section className="bg-gradient-to-b from-[#3D2314] to-[#5B3923] text-[#F5DEB3] py-10 lg:py-14">
        <div className="container mx-auto px-4 lg:px-12 text-center">
          <Badge className="bg-[#D4AF37]/20 text-[#D4AF37] border border-[#D4AF37]/40 rounded-full px-3 py-1 mb-3 tracking-widest uppercase text-[10px] font-body">
            <Flower2 className="inline h-3 w-3 mr-1" /> Celebration Quotation
          </Badge>
          <h1 className="font-heading text-3xl lg:text-4xl font-light tracking-wide">Quotation for {booking.name}</h1>
          <p className="font-body text-[#F5DEB3]/80 mt-2 text-sm">Enquiry ID: <span className="font-mono">{(booking.id || '').slice(0, 8).toUpperCase()}</span></p>
        </div>
      </section>

      <div className="container mx-auto px-4 lg:px-12 py-8 max-w-3xl">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-white border border-[#E8DFD0] shadow-sm">

          {/* Event Summary */}
          <div className="p-6 border-b border-[#E8DFD0]" data-testid="quote-summary">
            <div className="grid sm:grid-cols-2 gap-y-3 gap-x-6 text-sm font-body">
              <div className="flex items-start gap-2"><Sparkles className="h-4 w-4 text-[#B8962E] mt-0.5 shrink-0" /><div><p className="text-[10px] uppercase tracking-wider text-[#7A6F65]">Event Type</p><p className="text-[#2D1810] font-medium">{booking.event_type}</p></div></div>
              <div className="flex items-start gap-2"><MapPin className="h-4 w-4 text-[#B8962E] mt-0.5 shrink-0" /><div><p className="text-[10px] uppercase tracking-wider text-[#7A6F65]">Center</p><p className="text-[#2D1810] font-medium">{booking.center_name}</p></div></div>
              <div className="flex items-start gap-2"><Calendar className="h-4 w-4 text-[#B8962E] mt-0.5 shrink-0" /><div><p className="text-[10px] uppercase tracking-wider text-[#7A6F65]">Date</p><p className="text-[#2D1810] font-medium">{booking.event_date}</p></div></div>
              <div className="flex items-start gap-2"><Users className="h-4 w-4 text-[#B8962E] mt-0.5 shrink-0" /><div><p className="text-[10px] uppercase tracking-wider text-[#7A6F65]">Guests</p><p className="text-[#2D1810] font-medium">{booking.guest_count}</p></div></div>
              <div className="flex items-start gap-2"><Calendar className="h-4 w-4 text-[#B8962E] mt-0.5 shrink-0" /><div><p className="text-[10px] uppercase tracking-wider text-[#7A6F65]">Time Slot</p><p className="text-[#2D1810] font-medium">{booking.time_slot || '—'}</p></div></div>
              <div className="flex items-start gap-2"><Phone className="h-4 w-4 text-[#B8962E] mt-0.5 shrink-0" /><div><p className="text-[10px] uppercase tracking-wider text-[#7A6F65]">Contact</p><p className="text-[#2D1810] font-medium">{booking.mobile}</p></div></div>
            </div>

            {(booking.breakfast || booking.snacks || booking.drinks_mode || booking.decoration) && (
              <div className="mt-4 flex flex-wrap gap-2">
                {booking.breakfast && <Badge variant="outline" className="border-[#E8DFD0] text-[#5C4A3A]">Breakfast</Badge>}
                {booking.snacks && <Badge variant="outline" className="border-[#E8DFD0] text-[#5C4A3A]">Snacks</Badge>}
                {booking.drinks_mode === 'half_day' && <Badge variant="outline" className="border-[#E8DFD0] text-[#5C4A3A]">Drinks — Half Day</Badge>}
                {booking.drinks_mode === 'full_day' && <Badge variant="outline" className="border-[#E8DFD0] text-[#5C4A3A]">Drinks — Full Day</Badge>}
                {booking.drinks_mode === 'a_la_carte' && <Badge variant="outline" className="border-[#E8DFD0] text-[#5C4A3A]">Drinks — À la carte</Badge>}
                {booking.decoration && <Badge variant="outline" className="border-[#E8DFD0] text-[#5C4A3A]">Decoration</Badge>}
              </div>
            )}
          </div>

          {/* Line Items */}
          <div className="p-6" data-testid="quote-line-items">
            <h3 className="font-heading text-base text-[#3D2314] mb-3">Estimate</h3>
            {(est.line_items || []).length === 0 ? (
              <p className="text-sm text-[#7A6F65] italic">No line items yet — your dedicated event manager will reach out with details.</p>
            ) : (
              <div className="space-y-2 text-sm font-body">
                {(est.line_items || []).map((it, i) => (
                  <div key={i} className="flex justify-between text-[#5C4A3A]"><span>{it.label}</span><span className="text-[#2D1810]">{sym}{(it.amount || 0).toLocaleString('en-IN')}</span></div>
                ))}
                <div className="flex justify-between border-t border-[#E8DFD0] pt-2 mt-2"><span>Subtotal</span><span className="text-[#2D1810]">{sym}{(est.subtotal || 0).toLocaleString('en-IN')}</span></div>
                <div className="flex justify-between"><span>GST ({est.gst_pct || 0}%)</span><span className="text-[#2D1810]">{sym}{(est.gst_amount || 0).toLocaleString('en-IN')}</span></div>
                <div className="flex justify-between border-t-2 border-[#B8962E] pt-2 mt-2 font-heading text-lg"><span className="text-[#3D2314]">Total</span><span className="text-[#B8962E]" data-testid="quote-total">{sym}{(est.total || 0).toLocaleString('en-IN')}</span></div>
              </div>
            )}
            <p className="text-[10px] text-[#7A6F65] italic mt-3">Estimate is indicative. Final invoice will be issued by Purnabramha team after final menu confirmation.</p>
          </div>

          {/* Payment Status */}
          {(booking.advance_paid > 0 || booking.balance_due > 0 || booking.status) && (
            <div className="p-6 bg-[#FFFAED] border-t border-[#E8DFD0] text-sm font-body" data-testid="quote-payment">
              <div className="flex flex-wrap gap-x-6 gap-y-2">
                <div><span className="text-[10px] uppercase tracking-wider text-[#7A6F65]">Status</span><p className="text-[#3D2314] font-medium">{booking.status}</p></div>
                {booking.advance_paid > 0 && <div><span className="text-[10px] uppercase tracking-wider text-[#7A6F65]">Advance Paid</span><p className="text-green-700 font-medium">{sym}{booking.advance_paid.toLocaleString('en-IN')}</p></div>}
                {booking.balance_due > 0 && <div><span className="text-[10px] uppercase tracking-wider text-[#7A6F65]">Balance Due</span><p className="text-[#B8962E] font-medium">{sym}{booking.balance_due.toLocaleString('en-IN')}</p></div>}
              </div>
            </div>
          )}

          {/* Decoration rules (if customer agreed) */}
          {booking.decoration && cfg?.decoration_rules?.length > 0 && (
            <div className="p-6 border-t border-[#E8DFD0]">
              <h3 className="font-heading text-sm text-[#3D2314] mb-2 flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-[#B8962E]" /> Decoration & Property Safety Rules</h3>
              <ul className="text-xs font-body text-[#5C4A3A] space-y-1 list-disc pl-5">
                {cfg.decoration_rules.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          )}

          {/* Share Actions */}
          <div className="p-6 border-t border-[#E8DFD0] bg-[#F8F5F0] space-y-3" data-testid="quote-share">
            <p className="text-xs uppercase tracking-wider text-[#7A6F65] font-body">Share this quotation with your family</p>
            <div className="flex flex-wrap gap-2">
              <Button onClick={shareWhatsApp} className="bg-green-600 hover:bg-green-700 text-white rounded-none" data-testid="quote-share-wa">
                <MessageCircle className="h-4 w-4 mr-2" /> Share on WhatsApp
              </Button>
              <Button onClick={copyLink} variant="outline" className="border-[#B8962E]/40 text-[#B8962E] hover:bg-[#B8962E]/10 rounded-none" data-testid="quote-share-copy">
                {copied ? <Check className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}
                {copied ? 'Copied!' : 'Copy Link'}
              </Button>
              <Button onClick={nativeShare} variant="outline" className="border-[#E8DFD0] text-[#5C4A3A] hover:border-[#B8962E]/40 rounded-none" data-testid="quote-share-native">
                <Share2 className="h-4 w-4 mr-2" /> More…
              </Button>
            </div>
          </div>
        </motion.div>

        <p className="text-center mt-6 text-xs text-[#7A6F65] font-body">© Purnabramha • All celebrations crafted with love</p>
      </div>
    </div>
  );
}
