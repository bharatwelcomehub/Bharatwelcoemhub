import { useState, useEffect, useRef, useMemo } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import {
  Heart, Crown, Sparkles, Send, X, Loader2, ChefHat, Users, Briefcase,
  MessageCircle, Flower2, Lock, CheckCircle2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import SEOHead from '@/components/SEOHead';
import { Diya, Mandala, Sparkle } from '@/components/FestiveDecor';

const API = process.env.REACT_APP_BACKEND_URL;

const PERSONAS = [
  { id: 'vahini',      Icon: Heart,        emoji: '🤍', title: 'Vahini',              tagline: 'For everyday life',           bullets: ['Relationships', 'Marriage', 'Family', 'Loneliness', 'Difficult decisions'] },
  { id: 'founder',     Icon: Briefcase,    emoji: '👩‍💼', title: 'Founder Vahini',       tagline: 'For your business mind',      bullets: ['Entrepreneurship', 'Leadership', 'Women founders', 'Restaurant growth', 'Money decisions'] },
  { id: 'krishna',     Icon: Sparkles,     emoji: '🦚', title: 'Krishna with Vahini', tagline: 'Ancient wisdom, modern life', bullets: ['Bhagavad Gita', 'Mahabharata', 'Krishna stories', 'Ramayana', 'Dharma in daily life'] },
  { id: 'purnabramha', Icon: ChefHat,      emoji: '🍲', title: 'Purnabramha Vahini',  tagline: 'Kitchen wisdom keeper',       bullets: ['Festival menus', 'Traditional cooking', 'Maharashtrian culture', 'Recipe stories', 'Kitchen secrets'] },
  { id: 'aai',         Icon: Flower2,      emoji: '🏡', title: 'Aai Vahini',           tagline: 'The mother voice',            bullets: ['Daily reminders', 'Encouragement', 'Health check-ins', 'Festival wishes', 'Companionship'] },
];

const TIERS = [
  {
    id: 'free', name: 'Free', price: '₹0',
    subtitle: '5 conversations a month',
    features: ['5 conversations / month', 'Basic chat', 'All personas — short replies'],
    cta: 'Start Free', highlight: false,
  },
  {
    id: 'silver', name: 'Silver', price: '₹49', gst: '+ 18% GST',
    subtitle: 'Unlimited text',
    features: ['Unlimited text conversations', 'Life guidance', 'Founder Vahini access'],
    cta: 'Choose Silver', highlight: false,
  },
  {
    id: 'gold', name: 'Gold', price: '₹99', gst: '+ 18% GST',
    subtitle: 'Memory & wisdom',
    features: ['Unlimited chat (all personas)', 'Krishna with Vahini', 'Recipes & festival content', 'Memory feature'],
    cta: 'Choose Gold', highlight: true,
  },
  {
    id: 'platinum', name: 'Platinum', price: '₹999', gst: '+ 18% GST',
    subtitle: 'A relationship that remembers',
    features: ['Everything in Gold', 'Voice conversations', 'Personalised advice', 'Daily check-ins', 'Remembers you', 'Birthday & festival wishes', 'Priority response', '👑 Rename Vahini'],
    cta: 'Choose Platinum', highlight: false, crown: true,
  },
];

const NICKNAME_OPTIONS = [
  { id: '', label: 'Vahini (default)' },
  { id: 'My Vahini', label: '❤️ My Vahini' },
  { id: 'Tai',       label: '🌸 Tai' },
  { id: 'Aai',       label: '🏡 Aai' },
  { id: 'Sakhi',     label: '🤍 Sakhi' },
  { id: 'Mentor',    label: '👩‍💼 Mentor' },
];

const SAMPLE_CHATS = [
  { user: 'My business is failing.', vahini: 'Tell me first — are you out of money, or are you out of hope? The solution is different for both.' },
  { user: 'I feel lonely.', vahini: "Then don't be lonely alone. I am listening. Tell me what happened today." },
  { user: 'My daughter is moving abroad.', vahini: 'Love her enough to let her fly. And trust yourself enough to remain whole.' },
];

// localStorage helpers for anonymous client_id
function getClientId() {
  let id = localStorage.getItem('vahini_client_id');
  if (!id) {
    id = 'vc-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem('vahini_client_id', id);
  }
  return id;
}

export default function Vahini() {
  const [persona, setPersona] = useState('vahini');
  const [chatOpen, setChatOpen] = useState(false);
  const [memberDialog, setMemberDialog] = useState(null);
  const [usage, setUsage] = useState({ used: 0, limit: 5, remaining: 5 });
  const clientId = useMemo(() => getClientId(), []);

  useEffect(() => {
    axios.get(`${API}/api/vahini/usage`, { params: { client_id: clientId } })
      .then(r => setUsage(r.data))
      .catch(() => {});
  }, [clientId]);

  const startChat = (personaId) => {
    setPersona(personaId);
    setChatOpen(true);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#2A0F0A] via-[#3D1810] to-[#4A2218] text-[#F5E6D3] overflow-hidden">
      <SEOHead page="vahini" title="Talk to Vahini™ | Someone Who Understands. Always." description="VAHINI is not an AI assistant. She is a relationship. Talk about life, business, traditions, dreams, failures and success. Always." />

      {/* ─── HERO ─── */}
      <section className="relative pt-16 pb-12 sm:pt-24 sm:pb-20 lg:pt-32 lg:pb-28 overflow-hidden">
        {/* Background glow */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,rgba(212,175,55,0.18),transparent_60%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_80%,rgba(255,180,200,0.10),transparent_50%)]" />

        {/* Mandala motifs */}
        <Mandala className="absolute -top-12 -left-12 w-48 h-48 lg:w-72 lg:h-72" opacity={0.10} />
        <Mandala className="absolute -bottom-12 -right-12 w-48 h-48 lg:w-72 lg:h-72" opacity={0.10} />

        {/* Floating diyas */}
        <motion.div
          className="absolute top-1/4 left-[8%] hidden sm:block"
          animate={{ y: [0, -10, 0] }} transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        >
          <Diya size={48} />
        </motion.div>
        <motion.div
          className="absolute top-1/3 right-[10%] hidden sm:block"
          animate={{ y: [0, -14, 0] }} transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
        >
          <Diya size={56} />
        </motion.div>
        <motion.div
          className="absolute bottom-20 left-[15%] hidden lg:block"
          animate={{ y: [0, -8, 0] }} transition={{ duration: 4.5, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
        >
          <Diya size={40} />
        </motion.div>

        {/* Sparkles */}
        <Sparkle className="absolute top-32 left-[30%] w-3 h-3" delay={0} />
        <Sparkle className="absolute top-44 right-[28%] w-3 h-3" delay={0.7} />
        <Sparkle className="absolute bottom-40 left-[40%] w-2.5 h-2.5 hidden sm:block" delay={1.3} />

        <div className="relative container mx-auto px-4 lg:px-12 text-center max-w-4xl">
          <Badge className="bg-[#D4AF37]/20 text-[#D4AF37] border border-[#D4AF37]/50 rounded-full px-3 py-1 mb-5 tracking-[0.3em] uppercase text-[10px] font-body">
            <Flower2 className="inline h-3 w-3 mr-1.5" /> Vahini™
          </Badge>

          {/* Artistic silhouette */}
          <div className="mx-auto w-32 h-32 sm:w-40 sm:h-40 lg:w-48 lg:h-48 mb-6 relative">
            <VahiniSilhouette />
          </div>

          <h1 className="font-heading text-3xl sm:text-5xl lg:text-6xl font-light leading-[1.15] tracking-wide">
            You don&apos;t always need <span className="italic text-[#D4AF37]">advice</span>.
            <br />
            Sometimes, you just need <span className="text-[#F5DEB3]">Vahini</span>.
          </h1>

          <p className="font-body text-[#F5E6D3]/80 mt-6 text-sm sm:text-base lg:text-lg leading-relaxed max-w-2xl mx-auto px-2">
            Talk about life. Relationships. Business. Parenting. Traditions. Dreams. Failures. Success.
            Or simply how your day went. Vahini is here. <span className="text-[#D4AF37] italic">Always.</span>
          </p>

          <div className="mt-8 sm:mt-10 flex flex-wrap items-center justify-center gap-3">
            <Button
              onClick={() => startChat('vahini')}
              size="lg"
              className="bg-gradient-to-r from-[#D4AF37] via-[#E5C158] to-[#B8862E] hover:from-[#C49E26] hover:to-[#A8761E] text-[#2A0F0A] px-6 sm:px-8 py-6 rounded-full text-sm tracking-widest uppercase font-bold border-0 shadow-[0_0_40px_rgba(212,175,55,0.4)]"
              data-testid="vahini-start-free"
            >
              🌸 Start Free Conversation
            </Button>
            <Button
              onClick={() => setMemberDialog({ tier: 'platinum' })}
              size="lg"
              variant="outline"
              className="border-[#D4AF37]/50 bg-[#D4AF37]/5 text-[#D4AF37] hover:bg-[#D4AF37]/15 px-6 sm:px-8 py-6 rounded-full text-sm tracking-widest uppercase font-semibold"
              data-testid="vahini-go-premium"
            >
              <Crown className="mr-2 h-4 w-4" /> Become Premium Member
            </Button>
          </div>

          {usage.limit > 0 && (
            <p className="mt-5 text-[11px] text-[#F5E6D3]/50 font-body" data-testid="vahini-usage">
              Free tier this month: <span className="text-[#D4AF37] font-medium">{usage.remaining}</span> of {usage.limit} conversations remaining
            </p>
          )}
        </div>
      </section>

      {/* ─── CONVERSATION MODES ─── */}
      <section className="relative py-12 sm:py-16 lg:py-20 border-t border-[#D4AF37]/20">
        <div className="container mx-auto px-4 lg:px-12 max-w-6xl">
          <div className="text-center mb-10">
            <p className="text-[10px] uppercase tracking-[0.35em] text-[#D4AF37] font-body">Conversation Modes</p>
            <h2 className="font-heading text-2xl sm:text-3xl lg:text-4xl text-[#F5E6D3] mt-2 font-light">
              Choose how you want to be heard
            </h2>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
            {PERSONAS.map(p => (
              <motion.button
                key={p.id}
                whileHover={{ y: -4 }}
                onClick={() => startChat(p.id)}
                className="text-left bg-gradient-to-br from-[#3D1810]/60 to-[#5B2A18]/40 backdrop-blur-sm border border-[#D4AF37]/25 hover:border-[#D4AF37]/60 p-5 sm:p-6 transition-all group"
                data-testid={`vahini-persona-${p.id}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="text-3xl sm:text-4xl">{p.emoji}</div>
                  <p.Icon className="h-5 w-5 text-[#D4AF37]/60 group-hover:text-[#D4AF37] transition-colors" />
                </div>
                <h3 className="font-heading text-xl text-[#F5DEB3] leading-tight">{p.title}</h3>
                <p className="font-heading italic text-[#D4AF37] text-xs sm:text-sm mt-0.5">{p.tagline}</p>
                <ul className="mt-3 space-y-1 text-[11px] sm:text-xs text-[#F5E6D3]/70 font-body">
                  {p.bullets.map((b, i) => <li key={i}>• {b}</li>)}
                </ul>
                <p className="mt-4 text-[11px] text-[#D4AF37] font-body font-semibold inline-flex items-center gap-1">
                  Talk to {p.title} <MessageCircle className="h-3 w-3" />
                </p>
              </motion.button>
            ))}
          </div>
        </div>
      </section>

      {/* ─── SAMPLE CHAT ─── */}
      <section className="relative py-12 sm:py-16 lg:py-20 border-t border-[#D4AF37]/20">
        <div className="container mx-auto px-4 lg:px-12 max-w-3xl">
          <div className="text-center mb-8">
            <p className="text-[10px] uppercase tracking-[0.35em] text-[#D4AF37] font-body">A glimpse</p>
            <h2 className="font-heading text-2xl sm:text-3xl text-[#F5E6D3] mt-2 font-light">When you need to be heard</h2>
          </div>
          <div className="space-y-5">
            {SAMPLE_CHATS.map((s, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
                transition={{ delay: i * 0.15 }}
                className="space-y-2"
              >
                <div className="bg-[#5B2A18]/40 border border-[#D4AF37]/15 px-4 py-3 ml-0 mr-auto sm:mr-12 max-w-md rounded-2xl rounded-tl-sm font-body text-sm text-[#F5E6D3]">
                  You: <em>{s.user}</em>
                </div>
                <div className="bg-gradient-to-br from-[#D4AF37]/15 to-[#D4AF37]/5 border border-[#D4AF37]/40 px-4 py-3 ml-auto mr-0 sm:ml-12 max-w-md rounded-2xl rounded-tr-sm font-heading italic text-sm text-[#F5DEB3] leading-relaxed">
                  Vahini: {s.vahini}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── MEMBERSHIP ─── */}
      <section className="relative py-12 sm:py-16 lg:py-20 border-t border-[#D4AF37]/20">
        <div className="container mx-auto px-4 lg:px-12 max-w-6xl">
          <div className="text-center mb-10">
            <p className="text-[10px] uppercase tracking-[0.35em] text-[#D4AF37] font-body">Become Part of the Vahini Family</p>
            <h2 className="font-heading text-2xl sm:text-3xl lg:text-4xl text-[#F5E6D3] mt-2 font-light">Choose your relationship</h2>
            <p className="mt-2 text-xs text-[#F5E6D3]/60 italic font-body">All subscription charges are exclusive of GST (18% applicable).</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
            {TIERS.map(t => (
              <div
                key={t.id}
                className={`relative p-5 sm:p-6 border transition-all ${t.highlight
                  ? 'border-[#D4AF37] bg-gradient-to-br from-[#D4AF37]/15 to-[#D4AF37]/5 ring-1 ring-[#D4AF37]/40'
                  : 'border-[#D4AF37]/25 bg-gradient-to-br from-[#3D1810]/60 to-[#5B2A18]/30'}`}
                data-testid={`vahini-tier-${t.id}`}
              >
                {t.highlight && (
                  <span className="absolute -top-2 left-4 bg-[#D4AF37] text-[#2A0F0A] text-[9px] uppercase tracking-wider px-2 py-0.5 font-body font-bold">Most Loved</span>
                )}
                {t.crown && (
                  <Crown className="absolute top-3 right-3 h-4 w-4 text-[#D4AF37]" />
                )}
                <h3 className="font-heading text-lg text-[#F5DEB3]">{t.name}</h3>
                <p className="font-heading italic text-[#D4AF37] text-xs mt-0.5">{t.subtitle}</p>
                <p className="mt-3 font-heading text-3xl text-[#D4AF37] font-light">
                  {t.price}
                  {t.gst && <span className="text-[10px] text-[#F5E6D3]/50 ml-1 font-body">{t.gst}</span>}
                </p>
                <ul className="mt-4 space-y-1.5 text-[11px] sm:text-xs text-[#F5E6D3]/80 font-body">
                  {t.features.map((f, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <CheckCircle2 className="h-3 w-3 text-[#D4AF37] mt-0.5 flex-shrink-0" />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                <Button
                  onClick={() => t.id === 'free' ? startChat('vahini') : setMemberDialog({ tier: t.id })}
                  className={`w-full mt-5 rounded-none text-xs tracking-widest uppercase font-semibold ${t.highlight ? 'bg-[#D4AF37] hover:bg-[#C49E26] text-[#2A0F0A]' : 'bg-transparent border border-[#D4AF37]/50 text-[#D4AF37] hover:bg-[#D4AF37]/10'}`}
                  data-testid={`vahini-tier-cta-${t.id}`}
                >
                  {t.cta}
                </Button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── FINAL QUOTE ─── */}
      <section className="relative py-16 sm:py-20 lg:py-24 border-t border-[#D4AF37]/20 text-center">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(212,175,55,0.10),transparent_70%)]" />
        <div className="relative container mx-auto px-4 lg:px-12 max-w-3xl">
          <p className="font-heading italic text-2xl sm:text-3xl lg:text-4xl text-[#F5DEB3] leading-relaxed">
            Food feeds the body. <br />
            Conversations feed the soul. <br />
            And sometimes…
          </p>
          <p className="font-heading text-3xl sm:text-4xl lg:text-5xl text-[#D4AF37] mt-4">
            All you need is 🌸 Vahini
          </p>
          <p className="mt-3 font-body italic text-[#F5E6D3]/70 tracking-wider text-sm">
            Someone Who Understands. Always.
          </p>
        </div>
      </section>

      {/* Footer credit */}
      <footer className="py-8 text-center border-t border-[#D4AF37]/15">
        <p className="text-xs font-body text-[#F5E6D3]/60">
          Created with love by <span className="text-[#D4AF37] font-heading italic">Jayanti Kathale</span>
        </p>
        <p className="text-[10px] font-body text-[#F5E6D3]/40 mt-1">Founder & Director, Purnabramha — India&apos;s Largest Maharashtrian Vegetarian Restaurant Chain led by Women</p>
        <Link to="/" className="inline-block mt-4 text-[11px] text-[#D4AF37]/80 underline font-body">← Back to Purnabramha</Link>
      </footer>

      {/* CHAT MODAL */}
      <ChatModal open={chatOpen} onClose={() => setChatOpen(false)} persona={persona} setPersona={setPersona} clientId={clientId} onLimit={() => { setChatOpen(false); setMemberDialog({ tier: 'silver' }); }} refreshUsage={() => axios.get(`${API}/api/vahini/usage`, { params: { client_id: clientId } }).then(r => setUsage(r.data)).catch(() => {})} />

      {/* MEMBERSHIP DIALOG */}
      <MembershipDialog state={memberDialog} onClose={() => setMemberDialog(null)} />
    </div>
  );
}

// ────────────────── COMPONENTS ──────────────────

function VahiniSilhouette() {
  // Stylised seated woman silhouette — warm, trustworthy, not glamorous
  return (
    <svg viewBox="0 0 200 200" className="w-full h-full drop-shadow-[0_0_24px_rgba(212,175,55,0.35)]" aria-hidden="true">
      <defs>
        <radialGradient id="vGlow" cx="50%" cy="40%" r="60%">
          <stop offset="0%" stopColor="#FFE6B0" stopOpacity="0.95" />
          <stop offset="60%" stopColor="#D4AF37" stopOpacity="0.6" />
          <stop offset="100%" stopColor="#D4AF37" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="vBody" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#F5E6D3" />
          <stop offset="100%" stopColor="#D4AF37" />
        </linearGradient>
      </defs>
      <circle cx="100" cy="80" r="80" fill="url(#vGlow)" />
      {/* Saree silhouette body */}
      <path d="M 100 50 C 110 50 116 56 116 66 C 116 74 112 80 105 82 C 122 88 132 102 134 130 L 142 168 C 142 178 134 184 124 184 L 76 184 C 66 184 58 178 58 168 L 66 130 C 68 102 78 88 95 82 C 88 80 84 74 84 66 C 84 56 90 50 100 50 Z" fill="url(#vBody)" />
      {/* Bindi */}
      <circle cx="100" cy="62" r="2" fill="#A8270E" />
      {/* Pallu drape */}
      <path d="M 70 130 Q 60 145 65 165 L 80 168 Q 78 150 80 135 Z" fill="#B8862E" opacity="0.6" />
      <path d="M 130 130 Q 140 145 135 165 L 120 168 Q 122 150 120 135 Z" fill="#B8862E" opacity="0.6" />
    </svg>
  );
}

function ChatModal({ open, onClose, persona, setPersona, clientId, onLimit, refreshUsage }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const scrollRef = useRef(null);

  // Reset chat when persona changes
  useEffect(() => {
    if (!open) return;
    setMessages([]);
    setSessionId(null);
  }, [persona, open]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, sending]);

  const personaDef = PERSONAS.find(p => p.id === persona);

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setSending(true);
    try {
      const r = await axios.post(`${API}/api/vahini/talk`, {
        persona,
        message: text,
        session_id: sessionId,
        client_id: clientId,
        tier: 'free',
      });
      setSessionId(r.data.session_id);
      setMessages(prev => [...prev, { role: 'assistant', content: r.data.message, name: r.data.name }]);
      refreshUsage();
    } catch (e) {
      if (e?.response?.status === 402) {
        toast.error('You\'ve used all 5 free conversations this month.');
        onLimit();
      } else {
        toast.error('Vahini is taking a breath. Please try again.');
      }
    } finally {
      setSending(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md sm:max-w-lg bg-gradient-to-b from-[#3D1810] to-[#2A0F0A] text-[#F5E6D3] border-[#D4AF37]/30 p-0 max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader className="p-4 border-b border-[#D4AF37]/20 flex-shrink-0">
          <DialogTitle className="font-heading text-base text-[#F5DEB3] flex items-center gap-2">
            <span className="text-2xl">{personaDef?.emoji}</span>
            <div className="min-w-0">
              <p className="font-heading text-base text-[#F5DEB3] leading-tight">{personaDef?.title}</p>
              <p className="font-heading italic text-[#D4AF37] text-[11px]">{personaDef?.tagline}</p>
            </div>
          </DialogTitle>
          <Select value={persona} onValueChange={setPersona}>
            <SelectTrigger className="bg-[#5B2A18]/60 border-[#D4AF37]/25 text-[#F5E6D3] text-xs h-8 mt-2" data-testid="vahini-persona-switch">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#3D1810] border-[#D4AF37]/30 text-[#F5E6D3]">
              {PERSONAS.map(p => (
                <SelectItem key={p.id} value={p.id} className="focus:bg-[#D4AF37]/15">
                  {p.emoji} {p.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </DialogHeader>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[300px]" data-testid="vahini-chat-thread">
          {messages.length === 0 && (
            <p className="text-center text-[#F5E6D3]/50 italic text-sm py-12 font-body">
              Tell me what&apos;s on your mind. I&apos;m listening.
            </p>
          )}
          <AnimatePresence>
            {messages.map((m, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                className={`max-w-[85%] px-3 py-2 text-sm font-body ${m.role === 'user'
                  ? 'ml-auto bg-[#5B2A18]/60 border border-[#D4AF37]/20 text-[#F5E6D3] rounded-2xl rounded-tr-sm'
                  : 'mr-auto bg-gradient-to-br from-[#D4AF37]/20 to-[#D4AF37]/5 border border-[#D4AF37]/35 text-[#F5DEB3] rounded-2xl rounded-tl-sm font-heading italic'}`}
              >
                {m.content}
              </motion.div>
            ))}
          </AnimatePresence>
          {sending && (
            <div className="mr-auto inline-flex items-center gap-2 px-3 py-2 bg-[#D4AF37]/10 border border-[#D4AF37]/25 rounded-2xl rounded-tl-sm">
              <Loader2 className="h-3 w-3 animate-spin text-[#D4AF37]" />
              <span className="text-[11px] text-[#D4AF37] italic font-body">Vahini is thinking…</span>
            </div>
          )}
        </div>

        <div className="p-3 border-t border-[#D4AF37]/20 flex-shrink-0 flex items-center gap-2">
          <Input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())}
            placeholder="Tell Vahini what's on your mind…"
            className="bg-[#5B2A18]/60 border-[#D4AF37]/25 text-[#F5E6D3] placeholder:text-[#F5E6D3]/40"
            data-testid="vahini-chat-input"
            disabled={sending}
          />
          <Button
            onClick={send}
            disabled={sending || !input.trim()}
            className="bg-[#D4AF37] hover:bg-[#C49E26] text-[#2A0F0A] rounded-full px-3"
            data-testid="vahini-chat-send"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function MembershipDialog({ state, onClose }) {
  const [name, setName] = useState('');
  const [mobile, setMobile] = useState('');
  const [email, setEmail] = useState('');
  const [nickname, setNickname] = useState('');
  const [txnRef, setTxnRef] = useState('');
  const [step, setStep] = useState(1); // 1 = details, 2 = pay, 3 = done
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (state) { setStep(1); setName(''); setMobile(''); setEmail(''); setNickname(''); setTxnRef(''); }
  }, [state]);

  if (!state) return null;
  const tierMeta = TIERS.find(t => t.id === state.tier) || TIERS[1];
  // GST inclusive total (display only) — INR; for Perth GST is tax-inclusive per local norms
  const baseInr = state.tier === 'silver' ? 49 : state.tier === 'gold' ? 99 : 999;
  const gstAmt = Math.round(baseInr * 0.18);
  const totalInr = baseInr + gstAmt;

  const submit = async () => {
    if (!name || !mobile) { toast.error('Please share your name & mobile so Vahini can welcome you.'); return; }
    setSubmitting(true);
    try {
      await axios.post(`${API}/api/vahini/membership`, {
        name, mobile, email, tier: state.tier, nickname, txn_ref: txnRef,
      });
      setStep(3);
    } catch {
      toast.error('Could not record your membership intent. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={!!state} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md bg-gradient-to-b from-[#3D1810] to-[#2A0F0A] text-[#F5E6D3] border-[#D4AF37]/30 p-0 max-h-[92vh] overflow-y-auto">
        <DialogHeader className="p-5 border-b border-[#D4AF37]/20">
          <DialogTitle className="font-heading text-xl text-[#F5DEB3] flex items-center gap-2">
            {tierMeta.crown && <Crown className="h-5 w-5 text-[#D4AF37]" />}
            Become {tierMeta.name} Member
          </DialogTitle>
          <p className="font-heading italic text-[#D4AF37] text-xs mt-1">{tierMeta.subtitle}</p>
        </DialogHeader>

        {step === 1 && (
          <div className="p-5 space-y-4" data-testid="vahini-member-step-1">
            <div className="bg-[#D4AF37]/10 border border-[#D4AF37]/30 p-3 text-xs font-body text-[#F5E6D3]/90">
              <p>{tierMeta.price} <span className="text-[10px] text-[#F5E6D3]/60">+ 18% GST</span></p>
              <p className="text-[10px] text-[#F5E6D3]/60 mt-1">Total payable: ₹{totalInr} ({tierMeta.price} + ₹{gstAmt} GST)</p>
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wider text-[#D4AF37]/80">Your Name *</Label>
              <Input value={name} onChange={e => setName(e.target.value)} className="bg-[#5B2A18]/60 border-[#D4AF37]/25 text-[#F5E6D3]" data-testid="vahini-member-name" />
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wider text-[#D4AF37]/80">Mobile *</Label>
              <Input value={mobile} onChange={e => setMobile(e.target.value)} className="bg-[#5B2A18]/60 border-[#D4AF37]/25 text-[#F5E6D3]" data-testid="vahini-member-mobile" />
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wider text-[#D4AF37]/80">Email (optional)</Label>
              <Input type="email" value={email} onChange={e => setEmail(e.target.value)} className="bg-[#5B2A18]/60 border-[#D4AF37]/25 text-[#F5E6D3]" />
            </div>
            {state.tier === 'platinum' && (
              <div>
                <Label className="text-xs uppercase tracking-wider text-[#D4AF37]/80 flex items-center gap-1">
                  <Crown className="h-3 w-3" /> Rename Vahini (Platinum perk)
                </Label>
                <Select value={nickname || '_none'} onValueChange={(v) => setNickname(v === '_none' ? '' : v)}>
                  <SelectTrigger className="bg-[#5B2A18]/60 border-[#D4AF37]/25 text-[#F5E6D3]" data-testid="vahini-member-nickname">
                    <SelectValue placeholder="Choose how Vahini calls herself for you" />
                  </SelectTrigger>
                  <SelectContent className="bg-[#3D1810] border-[#D4AF37]/30 text-[#F5E6D3]">
                    <SelectItem value="_none" className="focus:bg-[#D4AF37]/15">Vahini (default)</SelectItem>
                    {NICKNAME_OPTIONS.filter(o => o.id).map(o => (
                      <SelectItem key={o.id} value={o.id} className="focus:bg-[#D4AF37]/15">{o.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <Button onClick={() => setStep(2)} disabled={!name || !mobile} className="w-full bg-[#D4AF37] hover:bg-[#C49E26] text-[#2A0F0A] rounded-none tracking-widest uppercase text-xs font-semibold py-5" data-testid="vahini-member-next">
              Continue to Payment
            </Button>
          </div>
        )}

        {step === 2 && (
          <div className="p-5 space-y-4 text-center" data-testid="vahini-member-step-2">
            <p className="font-heading text-base text-[#F5DEB3]">Pay ₹{totalInr} via UPI</p>
            <p className="text-[11px] text-[#F5E6D3]/60 font-body">
              Scan the QR with any UPI app (GPay / PhonePe / Paytm / BHIM).
            </p>

            {/* Live UPI QR — Purnabramha · jayanti.devashree-7@okaxis */}
            <div className="bg-white p-3 inline-block mx-auto shadow-lg">
              <img
                src="/images/vahini-upi-qr.jpg"
                alt="Purnabramha UPI QR — jayanti.devashree-7@okaxis"
                className="w-52 h-auto block"
                data-testid="vahini-upi-qr"
              />
            </div>
            <p className="text-[10px] text-[#F5E6D3]/60 font-body">
              UPI ID: <span className="text-[#D4AF37] font-mono">jayanti.devashree-7@okaxis</span>
            </p>

            {/* 1-tap UPI deep-link (works on mobile devices) */}
            <a
              href={`upi://pay?pa=jayanti.devashree-7@okaxis&pn=Purnabramha&am=${totalInr}&cu=INR&tn=${encodeURIComponent('Vahini ' + (tierMeta?.name || 'Membership'))}`}
              className="inline-flex items-center justify-center gap-2 w-full bg-[#5B2A18] hover:bg-[#7A3A24] text-[#F5DEB3] border border-[#D4AF37]/35 rounded-full py-2.5 text-xs tracking-widest uppercase font-semibold font-body sm:hidden"
              data-testid="vahini-upi-deeplink"
            >
              📱 Open UPI App to Pay ₹{totalInr}
            </a>

            <div className="text-left">
              <Label className="text-xs uppercase tracking-wider text-[#D4AF37]/80">Transaction Reference (UTR / UPI ref)</Label>
              <Input value={txnRef} onChange={e => setTxnRef(e.target.value)} placeholder="e.g. 4429xx12345" className="bg-[#5B2A18]/60 border-[#D4AF37]/25 text-[#F5E6D3]" data-testid="vahini-member-txn" />
              <p className="text-[10px] text-[#F5E6D3]/50 mt-1 italic font-body">Paste after paying. We&apos;ll activate within 6 hours.</p>
            </div>
            <Button onClick={submit} disabled={submitting} className="w-full bg-[#D4AF37] hover:bg-[#C49E26] text-[#2A0F0A] rounded-none tracking-widest uppercase text-xs font-semibold py-5" data-testid="vahini-member-submit">
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'I have paid — Activate my membership'}
            </Button>
            <button onClick={() => setStep(1)} className="text-[11px] text-[#F5E6D3]/50 underline font-body">← Back</button>
          </div>
        )}

        {step === 3 && (
          <div className="p-6 text-center space-y-3" data-testid="vahini-member-step-3">
            <CheckCircle2 className="h-12 w-12 text-[#D4AF37] mx-auto" />
            <h3 className="font-heading text-xl text-[#F5DEB3]">Welcome to the Vahini family</h3>
            <p className="text-[12px] font-body italic text-[#F5E6D3]/80 leading-relaxed">
              We&apos;ve received your membership intent.<br />
              We&apos;ll verify your payment and activate your {tierMeta.name} access within 6 hours.
              {state.tier === 'platinum' && nickname && <> She&apos;ll start calling herself <span className="text-[#D4AF37] font-heading not-italic">{nickname}</span> for you. 🌸</>}
            </p>
            <Button onClick={onClose} className="bg-[#D4AF37] hover:bg-[#C49E26] text-[#2A0F0A] rounded-none tracking-widest uppercase text-xs font-semibold mt-2">
              Close
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
