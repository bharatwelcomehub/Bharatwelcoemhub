import { useState, useEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { motion } from 'framer-motion';
import { QRCodeCanvas } from 'qrcode.react';
import {
  Star, Loader2, MessageCircle, Download, MapPin, Calendar as CalendarIcon,
  Sparkles, Phone, Mail, CheckCircle2, Heart, Utensils
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import SEOHead from '@/components/SEOHead';
import { Toran, Diya, Mandala } from '@/components/FestiveDecor';

const API = process.env.REACT_APP_BACKEND_URL;

const RATING_LABELS = ['Poor', 'Fair', 'Good', 'Very Good', 'Excellent'];

function StarRating({ value, onChange, testId }) {
  return (
    <div className="flex items-center gap-1.5" data-testid={testId}>
      {[1, 2, 3, 4, 5].map(n => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          className={`p-1 transition-transform ${value >= n ? 'scale-105' : 'opacity-40 hover:opacity-70'}`}
          data-testid={`${testId}-${n}`}
        >
          <Star className={`h-6 w-6 ${value >= n ? 'fill-[#D4AF37] text-[#D4AF37]' : 'text-[#7A6F65]'}`} />
        </button>
      ))}
      {value > 0 && <span className="ml-2 text-xs text-[#7A6F65] font-body">{RATING_LABELS[value - 1]}</span>}
    </div>
  );
}

export default function GuestCard() {
  const [params] = useSearchParams();
  const preCenter = params.get('center') || '';
  const [centers, setCenters] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [publicFeedback, setPublicFeedback] = useState([]);

  // Form fields
  const [guestName, setGuestName] = useState('');
  const [mobile, setMobile] = useState('');
  const [email, setEmail] = useState('');
  const [centerId, setCenterId] = useState(preCenter);
  const [visitDate, setVisitDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [visitType, setVisitType] = useState('');
  const [likedMost, setLikedMost] = useState('');
  const [seeMore, setSeeMore] = useState('');
  const [willRecommend, setWillRecommend] = useState('');
  const [willVisitAgain, setWillVisitAgain] = useState('');
  const [threeChanges, setThreeChanges] = useState('');
  const [overallRating, setOverallRating] = useState(0);
  const [foodRating, setFoodRating] = useState(0);
  const [serviceRating, setServiceRating] = useState(0);
  const [cleanlinessRating, setCleanlinessRating] = useState(0);

  useEffect(() => {
    axios.get(`${API}/api/centers`).then(r => {
      const all = [...(r.data?.india || []), ...(r.data?.australia || [])];
      setCenters(all);
    }).catch(() => {});
    axios.get(`${API}/api/guest-feedback/public?limit=6`).then(r => setPublicFeedback(r.data?.feedback || [])).catch(() => {});
  }, []);

  const currentCenter = useMemo(() => centers.find(c => c.id === centerId), [centers, centerId]);

  const submit = async () => {
    if (!guestName || !mobile || !centerId || !visitType || !overallRating) {
      toast.error('Please fill name, mobile, center, visit type and overall rating'); return;
    }
    setSubmitting(true);
    try {
      const body = {
        guest_name: guestName, mobile, email,
        center_id: centerId, center_name: currentCenter?.displayName || currentCenter?.name || '',
        visit_date: visitDate, visit_type: visitType,
        liked_most: likedMost, see_more: seeMore,
        will_recommend: willRecommend, will_visit_again: willVisitAgain,
        three_changes: threeChanges,
        overall_rating: overallRating, food_rating: foodRating || overallRating,
        service_rating: serviceRating || overallRating, cleanliness_rating: cleanlinessRating || overallRating,
      };
      const r = await axios.post(`${API}/api/guest-feedback`, body);
      setResult(r.data);
      toast.success('Thank you for sharing your feedback!');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch {
      toast.error('Could not submit. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return <DiscountCardView result={result} />;
  }

  return (
    <div className="min-h-screen bg-[#FDFBF7]">
      <SEOHead page="guest-card" title="Guest Experience Card | Purnabramha" description="Share your honest feedback and receive an instant Purnabramha discount card to use on your next visit." />

      {/* Hero — festive */}
      <section className="relative bg-gradient-to-b from-[#3D2314] via-[#4A2A18] to-[#5B3923] text-[#F5DEB3] pt-12 pb-10 sm:pt-14 sm:pb-12 overflow-hidden">
        <div className="absolute inset-0 opacity-25 pointer-events-none bg-[radial-gradient(circle_at_50%_30%,rgba(212,175,55,0.3),transparent_55%)]" />
        <Mandala className="absolute -top-8 -left-8 w-32 h-32 lg:w-44 lg:h-44 pointer-events-none" opacity={0.08} />
        <Mandala className="absolute -bottom-10 -right-8 w-32 h-32 lg:w-44 lg:h-44 pointer-events-none" opacity={0.08} />
        <div className="absolute top-0 left-0 right-0 pointer-events-none z-10">
          <Toran className="opacity-90" />
        </div>
        <div className="absolute left-3 top-14 sm:left-6 sm:top-16 pointer-events-none z-[6]">
          <Diya size={32} />
        </div>
        <div className="absolute right-3 top-14 sm:right-6 sm:top-16 pointer-events-none z-[6]">
          <Diya size={32} />
        </div>
        <div className="container mx-auto px-4 lg:px-12 text-center relative z-[7] pt-8 sm:pt-10">
          <Badge className="bg-[#D4AF37]/20 text-[#D4AF37] border border-[#D4AF37]/40 rounded-full px-3 py-1 mb-3 tracking-widest uppercase text-[10px] font-body">
            <Heart className="inline h-3 w-3 mr-1" /> Atithi Devo Bhava
          </Badge>
          <h1 className="font-heading text-2xl sm:text-3xl lg:text-4xl font-light tracking-wide px-2 leading-tight">
            Guest Experience Card
          </h1>
          <p className="font-heading italic text-[#D4AF37] text-sm sm:text-base mt-2 px-2">
            Your feedback builds our culture
          </p>
          <p className="font-body text-[#F5DEB3]/80 mt-2 text-xs sm:text-sm px-2 max-w-lg mx-auto">
            Share your honest experience and receive an instant Purnabramha discount card for your next visit.
          </p>
        </div>
      </section>

      <div className="container mx-auto px-4 lg:px-12 py-8 max-w-3xl">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
          {/* Section: about you */}
          <div className="bg-white border border-[#E8DFD0] p-5 sm:p-6 rounded-none">
            <h2 className="font-heading text-lg text-[#3D2314] flex items-center gap-2 mb-4">
              <Phone className="h-4 w-4 text-[#B8962E]" /> About You
            </h2>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Guest Name *</Label>
                <Input value={guestName} onChange={e => setGuestName(e.target.value)} data-testid="gc-name" />
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Mobile *</Label>
                <Input value={mobile} onChange={e => setMobile(e.target.value)} data-testid="gc-mobile" />
              </div>
              <div className="sm:col-span-2">
                <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Email (optional)</Label>
                <Input type="email" value={email} onChange={e => setEmail(e.target.value)} data-testid="gc-email" />
              </div>
            </div>
          </div>

          {/* Section: visit */}
          <div className="bg-white border border-[#E8DFD0] p-5 sm:p-6 rounded-none">
            <h2 className="font-heading text-lg text-[#3D2314] flex items-center gap-2 mb-4">
              <MapPin className="h-4 w-4 text-[#B8962E]" /> Your Visit
            </h2>
            <div className="grid sm:grid-cols-2 gap-3">
              <div className="sm:col-span-2">
                <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Center Visited *</Label>
                <Select value={centerId} onValueChange={setCenterId}>
                  <SelectTrigger data-testid="gc-center"><SelectValue placeholder="Select center" /></SelectTrigger>
                  <SelectContent>
                    {centers.map(c => <SelectItem key={c.id} value={c.id}>{c.displayName || c.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Date of Visit *</Label>
                <Input type="date" value={visitDate} max={new Date().toISOString().slice(0, 10)} onChange={e => setVisitDate(e.target.value)} data-testid="gc-date" />
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Visit Type *</Label>
                <Select value={visitType} onValueChange={setVisitType}>
                  <SelectTrigger data-testid="gc-visit-type"><SelectValue placeholder="How did you order?" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Dine-in">Dine-in</SelectItem>
                    <SelectItem value="Takeaway">Takeaway</SelectItem>
                    <SelectItem value="Delivery">Delivery</SelectItem>
                    <SelectItem value="Website Pickup">Website Pickup</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Section: ratings */}
          <div className="bg-white border border-[#E8DFD0] p-5 sm:p-6 rounded-none">
            <h2 className="font-heading text-lg text-[#3D2314] flex items-center gap-2 mb-4">
              <Star className="h-4 w-4 text-[#B8962E]" /> Rate Your Experience
            </h2>
            <div className="space-y-4">
              <div>
                <Label className="text-xs uppercase tracking-wider text-[#5C4A3A] block mb-1">Overall *</Label>
                <StarRating value={overallRating} onChange={setOverallRating} testId="gc-rate-overall" />
              </div>
              <div className="grid sm:grid-cols-3 gap-4">
                <div>
                  <Label className="text-xs uppercase tracking-wider text-[#5C4A3A] block mb-1">Food</Label>
                  <StarRating value={foodRating} onChange={setFoodRating} testId="gc-rate-food" />
                </div>
                <div>
                  <Label className="text-xs uppercase tracking-wider text-[#5C4A3A] block mb-1">Service</Label>
                  <StarRating value={serviceRating} onChange={setServiceRating} testId="gc-rate-service" />
                </div>
                <div>
                  <Label className="text-xs uppercase tracking-wider text-[#5C4A3A] block mb-1">Cleanliness</Label>
                  <StarRating value={cleanlinessRating} onChange={setCleanlinessRating} testId="gc-rate-clean" />
                </div>
              </div>
            </div>
          </div>

          {/* Section: tell us more */}
          <div className="bg-white border border-[#E8DFD0] p-5 sm:p-6 rounded-none">
            <h2 className="font-heading text-lg text-[#3D2314] flex items-center gap-2 mb-4">
              <Sparkles className="h-4 w-4 text-[#B8962E]" /> Tell Us More
            </h2>
            <div className="space-y-3">
              <div>
                <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">What did you like most?</Label>
                <Textarea value={likedMost} onChange={e => setLikedMost(e.target.value)} rows={2} placeholder="e.g. Authentic taste, warm hospitality, ambience…" data-testid="gc-liked" />
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">What would you love to see more?</Label>
                <Textarea value={seeMore} onChange={e => setSeeMore(e.target.value)} rows={2} placeholder="e.g. Seasonal specials, faster service, kids activities…" data-testid="gc-see-more" />
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Will you recommend us?</Label>
                  <Select value={willRecommend} onValueChange={setWillRecommend}>
                    <SelectTrigger data-testid="gc-recommend"><SelectValue placeholder="Pick one" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Yes">Yes, definitely</SelectItem>
                      <SelectItem value="Maybe">Maybe</SelectItem>
                      <SelectItem value="No">No</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">Will you come back?</Label>
                  <Select value={willVisitAgain} onValueChange={setWillVisitAgain}>
                    <SelectTrigger data-testid="gc-return"><SelectValue placeholder="Pick one" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Yes">Yes, very soon</SelectItem>
                      <SelectItem value="Maybe">Maybe</SelectItem>
                      <SelectItem value="Special">Only for special occasions</SelectItem>
                      <SelectItem value="No">No</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wider text-[#5C4A3A]">3 changes you'd love next visit</Label>
                <Textarea value={threeChanges} onChange={e => setThreeChanges(e.target.value)} rows={3} placeholder="1. …  2. …  3. …" data-testid="gc-changes" />
              </div>
            </div>
          </div>

          <Button
            onClick={submit}
            disabled={submitting}
            className="w-full bg-gradient-to-r from-[#D4AF37] to-[#B8962E] hover:from-[#C49E26] hover:to-[#A8861E] text-white py-6 rounded-none font-semibold tracking-wider text-base shadow-lg"
            data-testid="gc-submit"
          >
            {submitting ? <Loader2 className="h-5 w-5 mr-2 animate-spin" /> : <CheckCircle2 className="h-5 w-5 mr-2" />}
            {submitting ? 'Submitting…' : 'Submit & Get My Discount Card'}
          </Button>
          <p className="text-center text-[11px] text-[#7A6F65] italic font-body">
            We respect your privacy. Mobile & email are never displayed publicly.
          </p>

          {/* Public testimonials (only approved ones) */}
          {publicFeedback.length > 0 && (
            <div className="mt-8 pt-8 border-t border-[#E8DFD0]" data-testid="gc-public-feedback">
              <h3 className="font-heading text-base text-[#3D2314] flex items-center gap-2 mb-3">
                <Utensils className="h-4 w-4 text-[#B8962E]" /> Recent Guest Voices
              </h3>
              <div className="grid sm:grid-cols-2 gap-3">
                {publicFeedback.slice(0, 4).map((f, i) => (
                  <div key={i} className="bg-[#F8F5F0] border border-[#E8DFD0] p-3 text-xs font-body">
                    <div className="flex items-center gap-1 mb-1">
                      {[1,2,3,4,5].map(n => <Star key={n} className={`h-3 w-3 ${(f.overall_rating || 0) >= n ? 'fill-[#D4AF37] text-[#D4AF37]' : 'text-[#E8DFD0]'}`} />)}
                    </div>
                    <p className="text-[#3D2314] italic leading-relaxed line-clamp-3">"{f.liked_most || f.see_more || 'A truly heartwarming meal.'}"</p>
                    <p className="text-[10px] text-[#7A6F65] mt-1.5">— {f.guest_name}, {f.center_name}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}

function DiscountCardView({ result }) {
  const cardRef = useRef(null);
  const couponUrl = `${window.location.origin}/guest-card-claim/${result.coupon_code}`;
  const sym = (result.center_name || '').toLowerCase().includes('perth') ? '$' : '₹';

  const shareWA = () => {
    const msg = encodeURIComponent(
      `*Purnabramha Guest Discount Card*\n\n${result.discount_pct}% OFF at ${result.center_name}\n` +
      `Coupon: ${result.coupon_code}\n` +
      `Valid till: ${result.expiry_date || 'as per offer'}\n\n` +
      `Show this card on your next visit. ${couponUrl}`
    );
    window.open(`https://wa.me/?text=${msg}`, '_blank');
  };

  const downloadCard = async () => {
    try {
      // Use the html-to-canvas trick via html-to-image is too heavy. Use simple SVG screenshot fallback:
      // Print dialog gives best image. For now, advise user to screenshot.
      window.print();
    } catch {}
  };

  return (
    <div className="min-h-screen bg-[#FDFBF7] py-10 px-4">
      <SEOHead page="guest-card-thanks" title="Thank you — Your Purnabramha Discount Card" description="Show this card at any Purnabramha center to claim your discount." />
      <div className="max-w-md mx-auto">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          ref={cardRef}
          className="relative bg-gradient-to-br from-[#3D2314] via-[#5B3923] to-[#3D2314] text-[#F5DEB3] p-6 sm:p-8 shadow-2xl overflow-hidden"
          data-testid="discount-card"
        >
          <Mandala className="absolute -top-6 -right-6 w-32 h-32 pointer-events-none" opacity={0.12} />
          <Mandala className="absolute -bottom-6 -left-6 w-32 h-32 pointer-events-none" opacity={0.12} />

          <Badge className="bg-[#D4AF37]/20 text-[#D4AF37] border border-[#D4AF37]/40 rounded-none px-2.5 py-0.5 text-[10px] uppercase tracking-widest font-body">
            Purnabramha Guest Card
          </Badge>
          <h2 className="font-heading text-2xl sm:text-3xl text-[#F5DEB3] mt-3 leading-tight">Thank You{result.guest_name ? `, ${result.guest_name.split(' ')[0]}` : ''}!</h2>
          <p className="font-heading italic text-[#D4AF37] text-sm mt-1">for sharing your honest feedback</p>

          {result.discount_pct > 0 ? (
            <div className="mt-5 pt-5 border-t border-[#D4AF37]/30">
              <p className="text-[10px] uppercase tracking-widest text-[#D4AF37]/70 font-body">Your reward</p>
              <p className="font-heading text-5xl sm:text-6xl text-[#D4AF37] font-light mt-1" data-testid="discount-pct">{result.discount_pct}% <span className="text-2xl">OFF</span></p>
              <p className="font-heading italic text-[#F5DEB3]/80 text-sm mt-1">{result.offer_title || 'on your next visit'}</p>
            </div>
          ) : (
            <div className="mt-5 pt-5 border-t border-[#D4AF37]/30">
              <p className="font-heading text-lg text-[#D4AF37]">Your feedback is our greatest reward.</p>
              <p className="text-xs font-body text-[#F5DEB3]/70 mt-1">A center associate may offer you a special token at your next visit.</p>
            </div>
          )}

          <div className="mt-5 grid grid-cols-2 gap-3 text-xs font-body">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#D4AF37]/70">Coupon</p>
              <p className="font-mono text-base text-[#F5DEB3] tracking-widest">{result.coupon_code}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#D4AF37]/70">Center</p>
              <p className="text-[#F5DEB3]">{result.center_name}</p>
            </div>
            {result.expiry_date && (
              <div>
                <p className="text-[10px] uppercase tracking-wider text-[#D4AF37]/70">Valid Till</p>
                <p className="text-[#F5DEB3]">{result.expiry_date}</p>
              </div>
            )}
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#D4AF37]/70">Issued</p>
              <p className="text-[#F5DEB3]">{(result.created_at || '').slice(0, 10)}</p>
            </div>
          </div>

          <div className="mt-5 pt-5 border-t border-[#D4AF37]/30 flex items-end justify-between gap-3">
            <div className="flex-1">
              <p className="text-[10px] uppercase tracking-widest text-[#D4AF37]/70 font-body mb-1">Show this card at counter</p>
              <p className="text-[11px] italic text-[#F5DEB3]/70 leading-snug">
                {result.terms || 'Discount valid as per center terms. One card per guest/visit.'}
              </p>
            </div>
            <div className="bg-white p-2 rounded-md flex-shrink-0" data-testid="discount-qr">
              <QRCodeCanvas value={`${result.coupon_code}|${couponUrl}`} size={84} bgColor="#FFFFFF" fgColor="#3D2314" level="M" />
            </div>
          </div>

          <p className="text-center text-[9px] text-[#D4AF37]/50 mt-4 tracking-widest uppercase">Atithi Devo Bhava • {sym}Purnabramha</p>
        </motion.div>

        {/* Actions */}
        <div className="mt-5 grid grid-cols-2 gap-3 print:hidden">
          <Button onClick={shareWA} className="bg-green-600 hover:bg-green-700 text-white rounded-none py-5" data-testid="discount-share-wa">
            <MessageCircle className="h-4 w-4 mr-2" /> Share on WhatsApp
          </Button>
          <Button onClick={downloadCard} variant="outline" className="border-[#B8962E]/40 text-[#B8962E] hover:bg-[#B8962E]/10 rounded-none py-5" data-testid="discount-download">
            <Download className="h-4 w-4 mr-2" /> Save / Print
          </Button>
        </div>

        <a href="/guest-card" className="block mt-4 text-center text-xs text-[#7A6F65] underline font-body print:hidden">Submit another feedback</a>
      </div>
    </div>
  );
}
