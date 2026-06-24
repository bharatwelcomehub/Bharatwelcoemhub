import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import {
  Coffee, Phone, Mail, Globe, MapPin, ChefHat, Sparkles, Loader2,
  CheckCircle2, ArrowDown, Building2, Send, Download, Star, TrendingUp, Calendar as CalendarIcon
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import SEOHead from '@/components/SEOHead';
import { downloadFranchisePDF } from '@/lib/pbChaiPdf';

const API = process.env.REACT_APP_BACKEND_URL;

// Attached customer assets — storefront signage + one-page disclosure brochure
const STOREFRONT_IMG = 'https://customer-assets.emergentagent.com/job_50886080-3950-4b54-8e6a-7e012eaffafc/artifacts/tpkygoj1_DD7F478D-6272-416F-8E7A-4E9F734F534C.png';
const BROCHURE_IMG = 'https://customer-assets.emergentagent.com/job_50886080-3950-4b54-8e6a-7e012eaffafc/artifacts/4kzpseer_E26A6617-96D5-4EFB-833C-0D12F09E7838.png';

// Black & gold theme constants — match the brochure exactly
const C = {
  bg: 'bg-[#0E0A06]',
  panel: 'bg-[#1A1208]/90',
  panel2: 'bg-[#241808]/70',
  border: 'border-[#A87A2A]/30',
  borderStrong: 'border-[#D4AF37]/60',
  gold: 'text-[#D4AF37]',
  goldLight: 'text-[#F2C84B]',
  cream: 'text-[#F5E6B0]',
  body: 'text-[#E8D5A8]',
  bodyDim: 'text-[#E8D5A8]/70',
};

const fmtINR = (n) => `₹${(n || 0).toLocaleString('en-IN')}`;

export default function PBChaiCafe() {
  const [cfg, setCfg] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    axios.get(`${API}/api/pb-chai/config`).then(r => setCfg(r.data)).catch(() => setCfg({}));
  }, []);

  const setupTotal = useMemo(() => (cfg?.setup_heads || []).reduce((s, h) => s + (h.amount || 0), 0), [cfg]);
  const feeTotal = useMemo(() => (cfg?.franchise_fee_inr || 0) + (cfg?.security_deposit_inr || 0), [cfg]);

  if (!cfg) {
    return <div className={`min-h-screen ${C.bg} flex items-center justify-center`}><Loader2 className={`h-8 w-8 animate-spin ${C.gold}`} /></div>;
  }

  const visible = cfg.sections_visible || {};

  return (
    <div className={`min-h-screen ${C.bg} ${C.body}`}>
      <SEOHead page="pb-chai-cafe" title="PB Chai Café Franchise | Purnabramha" description="Own a PB Chai Café — Bring Maharashtrian Tea Culture to Your City. FOFO franchise model with strong returns and brand support." />

      {/* ── HERO ── */}
      <section className="relative pt-12 pb-10 sm:pt-20 sm:pb-16 lg:pt-24 lg:pb-20 overflow-hidden border-b border-[#A87A2A]/20">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,rgba(212,175,55,0.16),transparent_60%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_85%_70%,rgba(168,122,42,0.10),transparent_50%)]" />

        <div className="relative container mx-auto px-4 lg:px-12 max-w-6xl">
          <div className="grid lg:grid-cols-[1fr_1.1fr] gap-8 lg:gap-12 items-center">
            {/* Logo + tagline */}
            <div>
              {cfg.logo_url ? (
                <img src={cfg.logo_url} alt="PB Chai Café" className="h-20 sm:h-24 mb-4" />
              ) : (
                <div className="inline-flex items-center justify-center w-20 h-20 sm:w-24 sm:h-24 rounded-full border-2 border-[#D4AF37]/70 bg-[#1A1208] mb-4 shadow-[0_0_30px_rgba(212,175,55,0.3)]">
                  <Coffee className="h-9 w-9 sm:h-11 sm:w-11 text-[#D4AF37]" />
                </div>
              )}
              <Badge className="bg-[#D4AF37]/15 text-[#D4AF37] border border-[#D4AF37]/40 rounded-full px-3 py-1 tracking-[0.3em] uppercase text-[10px] font-body">
                Franchise Opportunity
              </Badge>
              <h1 className={`font-heading text-4xl sm:text-5xl lg:text-6xl font-light leading-[1.05] tracking-wide mt-3 ${C.gold}`}>
                PB Chai Café
              </h1>
              <p className={`font-heading italic ${C.cream} text-base sm:text-lg mt-2`}>
                Chaha. Goshti. Maharashtrian Comfort.
              </p>
              <p className={`mt-5 font-body text-sm sm:text-base leading-relaxed ${C.bodyDim} max-w-md`}>
                A compact café model with authentic flavours, quick service, and strong repeat customers.
                Bring Maharashtrian Tea Culture to Your City.
              </p>

              {/* Founder quote */}
              <div className={`mt-6 p-4 sm:p-5 border-l-2 border-[#D4AF37] ${C.panel} max-w-md`}>
                <p className={`font-heading italic ${C.cream} text-sm sm:text-base leading-relaxed`}>
                  &ldquo;Our Maharashtrian food deserves to stand on the world platform.&rdquo;
                </p>
                <p className={`text-[11px] tracking-wider uppercase ${C.gold} mt-2 font-body`}>
                  — Jayanti Kathale, Founder, Purnabramha
                </p>
              </div>

              <div className="mt-6 flex flex-wrap gap-3">
                <Button
                  onClick={() => document.getElementById('apply')?.scrollIntoView({ behavior: 'smooth' })}
                  className="bg-gradient-to-r from-[#D4AF37] via-[#E5C158] to-[#B8862E] hover:from-[#C49E26] hover:to-[#A8761E] text-[#0E0A06] px-6 py-5 rounded-full text-xs tracking-[0.25em] uppercase font-bold border-0 shadow-[0_0_30px_rgba(212,175,55,0.4)]"
                  data-testid="pbchai-apply-cta"
                >
                  Apply for Franchise <ArrowDown className="ml-2 h-4 w-4" />
                </Button>
                <DownloadPdfButton />
              </div>
            </div>

            {/* Kiosk image */}
            <div className={`relative ${C.panel} border ${C.borderStrong} aspect-[5/4] sm:aspect-[6/5] overflow-hidden shadow-[0_20px_60px_rgba(0,0,0,0.5)]`}>
              <img
                src={cfg.kiosk_image_url || STOREFRONT_IMG}
                alt="PB Chai Café storefront signage"
                className="w-full h-full object-cover"
                data-testid="pbchai-hero-storefront"
              />
            </div>
          </div>
        </div>
      </section>

      {/* ── WHY PB CHAI CAFÉ ── */}
      <Section title="Why PB Chai Café" subtitle="Six reasons partners choose us">
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
          {[
            ['Authentic Maharashtrian Flavours', Star],
            ['Premium Ingredients', Sparkles],
            ['Quick Service', TrendingUp],
            ['Low Operational Complexity', ChefHat],
            ['High Repeat Customers', Star],
            ['Strong Brand Trust', CheckCircle2],
          ].map(([t, Icon]) => (
            <div key={t} className={`p-5 ${C.panel} border ${C.border} hover:border-[#D4AF37]/50 transition-colors`}>
              <Icon className="h-6 w-6 text-[#D4AF37] mb-3" />
              <p className={`font-heading ${C.cream} text-sm sm:text-base leading-tight`}>{t}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* ── HERO MENU ── */}
      {visible.menu !== false && (cfg.menu_items || []).length > 0 && (
        <Section title="Hero Menu" subtitle="Loved by thousands · made fresh daily">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
            {cfg.menu_items.filter(m => m.active !== false).map(m => (
              <div key={m.id} className={`${C.panel} border ${C.border} p-4 transition-all hover:border-[#D4AF37]/50`} data-testid={`pbchai-menu-${m.id}`}>
                <div className="aspect-square bg-[#0E0A06] mb-3 overflow-hidden flex items-center justify-center">
                  {m.image_url
                    ? <img src={m.image_url} alt={m.name} className="w-full h-full object-cover" />
                    : <Coffee className="h-10 w-10 text-[#D4AF37]/30" />}
                </div>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className={`font-heading ${C.cream} text-sm leading-tight`}>{m.name}</p>
                    <p className={`text-[10px] uppercase tracking-wider ${C.bodyDim} mt-0.5`}>{m.category}</p>
                  </div>
                  <p className={`font-heading text-base ${C.gold} whitespace-nowrap`}>{fmtINR(m.price)}</p>
                </div>
                {m.description && <p className={`text-[11px] ${C.bodyDim} mt-2 leading-snug font-body line-clamp-2`}>{m.description}</p>}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* ── FRANCHISE MODEL ── */}
      {visible.model !== false && (
        <Section title="Franchise Model" subtitle="FOFO · Franchise Owned · Franchise Operated">
          <div className="grid lg:grid-cols-2 gap-4 sm:gap-5">
            <div className={`p-5 sm:p-6 ${C.panel} border ${C.border}`}>
              <p className={`text-[10px] uppercase tracking-[0.3em] ${C.gold} font-body`}>Franchise Partner</p>
              <h3 className={`font-heading text-lg ${C.cream} mt-1`}>You own & operate</h3>
              <ul className="mt-4 space-y-2 text-sm font-body">
                {['Owns business', 'Invests in setup', 'Operates café day-to-day'].map(b => (
                  <li key={b} className="flex items-start gap-2"><CheckCircle2 className="h-4 w-4 text-[#D4AF37] flex-shrink-0 mt-0.5" /><span>{b}</span></li>
                ))}
              </ul>
            </div>
            <div className={`p-5 sm:p-6 ${C.panel2} border ${C.borderStrong}`}>
              <p className={`text-[10px] uppercase tracking-[0.3em] ${C.gold} font-body`}>Purnabramha Provides</p>
              <h3 className={`font-heading text-lg ${C.cream} mt-1`}>Full brand backing</h3>
              <ul className="mt-4 grid sm:grid-cols-2 gap-y-2 gap-x-3 text-sm font-body">
                {['Brand License', 'Setup Guidance', 'Product Support', 'SOPs', 'Vendor Network', 'Staff Training', 'Marketing Support', 'New Product Development'].map(b => (
                  <li key={b} className="flex items-start gap-2"><CheckCircle2 className="h-4 w-4 text-[#D4AF37] flex-shrink-0 mt-0.5" /><span>{b}</span></li>
                ))}
              </ul>
            </div>
          </div>
        </Section>
      )}

      {/* ── SETUP VENDORS ── */}
      {visible.vendors !== false && (cfg.vendors || []).length > 0 && (
        <Section title="Setup Support" subtitle="Approved Setup Vendors provided by Purnabramha">
          <div className={`p-4 ${C.panel2} border ${C.borderStrong} mb-4 text-center`}>
            <p className={`font-heading italic text-base sm:text-lg ${C.cream}`}>
              All vendors are pre-vetted by Purnabramha for quality and price consistency.
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2 sm:gap-3">
            {cfg.vendors.map(v => (
              <div key={v} className={`px-3 py-3 ${C.panel} border ${C.border} text-center text-xs sm:text-sm font-body ${C.cream}`}>
                <Building2 className="h-4 w-4 text-[#D4AF37] inline mr-1.5" />{v}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* ── INVESTMENT ── */}
      {visible.investment !== false && (
        <Section title="Franchise Investment" subtitle="Transparent. One-time + setup capex.">
          <div className="grid lg:grid-cols-2 gap-5">
            {/* Fees */}
            <div className={`p-5 sm:p-6 ${C.panel} border ${C.border}`}>
              <h3 className={`font-heading text-lg ${C.cream} mb-4`}>Franchise Fees</h3>
              <Row label="Franchise Fee (One Time)" value={fmtINR(cfg.franchise_fee_inr)} />
              <Row label={`Security Deposit${cfg.deposit_refundable ? ' (Refundable)' : ''}`} value={fmtINR(cfg.security_deposit_inr)} />
              <div className={`mt-3 pt-3 border-t border-[#D4AF37]/30 flex justify-between items-center`}>
                <span className={`font-heading text-base ${C.gold}`}>Total</span>
                <span className={`font-heading text-xl ${C.gold}`}>{fmtINR(feeTotal)}</span>
              </div>
              {cfg.deposit_note && <p className={`text-[11px] ${C.bodyDim} italic mt-3 font-body`}>{cfg.deposit_note}</p>}
            </div>

            {/* Setup cost */}
            <div className={`p-5 sm:p-6 ${C.panel2} border ${C.borderStrong}`}>
              <h3 className={`font-heading text-lg ${C.cream} mb-4`}>Approximate Setup Cost</h3>
              {(cfg.setup_heads || []).map(h => (
                <Row key={h.id} label={h.label} value={fmtINR(h.amount)} />
              ))}
              <div className={`mt-3 pt-3 border-t border-[#D4AF37]/30 flex justify-between items-center`}>
                <span className={`font-heading text-base ${C.gold}`}>Total Setup</span>
                <span className={`font-heading text-xl ${C.gold}`}>{fmtINR(setupTotal)}</span>
              </div>
            </div>
          </div>
        </Section>
      )}

      {/* ── ROYALTY ── */}
      {visible.royalty !== false && (
        <Section title="Royalty & Marketing" subtitle="Simple percentage model · paid monthly">
          <div className="grid sm:grid-cols-2 gap-5 max-w-3xl mx-auto">
            <BigStat label="Monthly Royalty" value={`${cfg.royalty_pct}%`} sub={`of Gross Sales${cfg.royalty_gst_applicable ? ' (excluding GST)' : ''}`} />
            <BigStat label="Marketing Fund" value={`${cfg.marketing_pct}%`} sub="of Gross Sales" />
          </div>
        </Section>
      )}

      {/* ── PROJECTIONS ── */}
      {visible.projections !== false && (
        <Section title="Financial Projections" subtitle="Average performance across mature kiosks">
          <div className="grid sm:grid-cols-3 gap-4">
            <BigStat label="Average Monthly Sale" value={fmtINR(cfg.projections?.avg_monthly_sale)} />
            <BigStat label="Average Gross Profit" value={fmtINR(cfg.projections?.avg_gross_profit)} sub={`Approx ${cfg.projections?.gross_margin_pct}% margin`} />
            <BigStat label="Average Net Profit" value={`${fmtINR(cfg.projections?.net_profit_min)} – ${fmtINR(cfg.projections?.net_profit_max)}`} />
          </div>
          <div className="grid sm:grid-cols-2 gap-4 mt-4 max-w-3xl mx-auto">
            <BigStat label="Break-even" value={`${cfg.projections?.breakeven_months} Months`} icon={CalendarIcon} />
            <BigStat label="ROI" value={`${cfg.projections?.roi_months} Months`} icon={TrendingUp} />
          </div>
        </Section>
      )}

      {/* ── IDEAL LOCATIONS ── */}
      {visible.locations !== false && (
        <Section title="Ideal Locations" subtitle="Where PB Chai Café thrives">
          <div className="flex flex-wrap justify-center gap-2 sm:gap-3">
            {(cfg.ideal_locations || []).map(l => (
              <span key={l} className={`px-4 py-2 ${C.panel} border ${C.border} text-xs sm:text-sm font-body ${C.cream}`}>
                <MapPin className="inline h-3 w-3 mr-1 text-[#D4AF37]" />{l}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* ── BROCHURE PREVIEW ── */}
      <Section title="Franchise Brochure" subtitle="Tap below to download the full one-page disclosure as PDF">
        <div className="grid lg:grid-cols-[1.1fr_1fr] gap-6 lg:gap-10 items-center max-w-5xl mx-auto">
          <a
            href={BROCHURE_IMG}
            target="_blank"
            rel="noopener noreferrer"
            className={`block relative ${C.panel} border ${C.borderStrong} overflow-hidden shadow-[0_20px_60px_rgba(0,0,0,0.6)] hover:shadow-[0_25px_70px_rgba(212,175,55,0.25)] transition-shadow group`}
            data-testid="pbchai-brochure-preview-image"
          >
            <img
              src={BROCHURE_IMG}
              alt="PB Chai Café — One Page Franchise Disclosure"
              className="w-full h-auto block group-hover:scale-[1.02] transition-transform duration-700"
            />
            <span className="absolute top-3 right-3 text-[10px] uppercase tracking-[0.3em] px-2.5 py-1 rounded-full bg-[#0E0A06]/80 text-[#D4AF37] border border-[#D4AF37]/40 font-body">
              One Page Disclosure
            </span>
          </a>
          <div>
            <p className={`text-[10px] uppercase tracking-[0.35em] ${C.gold} font-body`}>What&apos;s inside the PDF</p>
            <h3 className={`font-heading text-2xl sm:text-3xl ${C.cream} mt-2 font-light leading-tight`}>
              Everything an aspiring franchise partner needs — in one printable file.
            </h3>
            <ul className="mt-5 space-y-2.5 text-sm font-body">
              {[
                'Hero menu with current prices',
                'Investment breakup & total setup cost',
                'Franchise fee, royalty and marketing share',
                'Financial projections, break-even & ROI window',
                'Ideal locations and the 6-step franchise journey',
                'Risk Disclosure — what every applicant must read',
              ].map(t => (
                <li key={t} className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-[#D4AF37] flex-shrink-0 mt-0.5" />
                  <span className={C.cream}>{t}</span>
                </li>
              ))}
            </ul>
            <p className={`mt-4 text-[11px] italic ${C.bodyDim} font-body`}>
              PDF reflects the latest configuration set by Purnabramha — pricing and details update automatically.
            </p>
            <div className="mt-5">
              <DownloadPdfButton variant="primary" />
            </div>
          </div>
        </div>
      </Section>

      {/* ── JOURNEY ── */}
      {visible.journey !== false && (
        <Section title="Franchise Journey" subtitle="From application to grand launch in 8 simple steps">
          <div className="space-y-2 max-w-2xl mx-auto">
            {[
              'Submit Application', 'Discussion & Evaluation', 'Site Approval',
              'Franchise Fee Payment', 'Agreement Generation', 'Setup & Training',
              'Grand Launch', 'Ongoing Support'
            ].map((step, i) => (
              <div key={i} className={`flex items-start gap-3 p-3 ${C.panel} border ${C.border}`}>
                <span className={`flex-shrink-0 w-8 h-8 rounded-full bg-[#D4AF37] text-[#0E0A06] font-heading font-bold text-sm flex items-center justify-center`}>{i + 1}</span>
                <p className={`font-heading text-sm sm:text-base ${C.cream} pt-1`}>{step}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* ── APPLICATION FORM ── */}
      {visible.application !== false && (
        <Section id="apply" title="Franchise Application Form" subtitle="Submit your interest · We'll contact within 48 hours">
          {submitted ? (
            <ThankYou onReset={() => setSubmitted(false)} />
          ) : (
            <ApplicationForm onSubmitted={() => setSubmitted(true)} />
          )}
        </Section>
      )}

      {/* ── FOOTER CTA ── */}
      <section className="relative py-14 sm:py-20 border-t border-[#D4AF37]/30 bg-gradient-to-b from-[#0E0A06] to-[#1A1208] text-center overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(212,175,55,0.12),transparent_70%)]" />
        <div className="relative container mx-auto px-4 max-w-3xl">
          <p className={`text-[10px] uppercase tracking-[0.4em] ${C.gold} font-body`}>Ready to Partner?</p>
          <h2 className={`font-heading text-3xl sm:text-4xl lg:text-5xl ${C.gold} mt-3 font-light`}>PB Chai Café</h2>
          <p className={`font-heading italic ${C.cream} mt-2 text-sm sm:text-base`}>
            From Maharashtra&apos;s Heart to India&apos;s Workspaces.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Button
              onClick={() => document.getElementById('apply')?.scrollIntoView({ behavior: 'smooth' })}
              className="bg-gradient-to-r from-[#D4AF37] via-[#E5C158] to-[#B8862E] text-[#0E0A06] px-6 py-5 rounded-full text-xs tracking-[0.25em] uppercase font-bold border-0"
              data-testid="pbchai-apply-footer"
            >
              Apply for Franchise
            </Button>
            <DownloadPdfButton variant="footer" />
          </div>

          <div className="mt-8 grid sm:grid-cols-3 gap-3 text-xs sm:text-sm font-body">
            {cfg.footer?.phone && (
              <a href={`tel:${cfg.footer.phone}`} className={`flex items-center justify-center gap-2 p-3 ${C.panel} border ${C.border} hover:border-[#D4AF37]/60 transition-colors`}>
                <Phone className="h-4 w-4 text-[#D4AF37]" /> <span className={C.cream}>{cfg.footer.phone}</span>
              </a>
            )}
            {cfg.footer?.email && (
              <a href={`mailto:${cfg.footer.email}`} className={`flex items-center justify-center gap-2 p-3 ${C.panel} border ${C.border} hover:border-[#D4AF37]/60 transition-colors`}>
                <Mail className="h-4 w-4 text-[#D4AF37]" /> <span className={C.cream}>{cfg.footer.email}</span>
              </a>
            )}
            {cfg.footer?.website && (
              <a href={`https://${cfg.footer.website}`} target="_blank" rel="noopener noreferrer" className={`flex items-center justify-center gap-2 p-3 ${C.panel} border ${C.border} hover:border-[#D4AF37]/60 transition-colors`}>
                <Globe className="h-4 w-4 text-[#D4AF37]" /> <span className={C.cream}>{cfg.footer.website}</span>
              </a>
            )}
          </div>
          <Link to="/" className={`inline-block mt-6 text-[11px] ${C.gold} underline font-body opacity-70`}>← Back to Purnabramha</Link>
        </div>
      </section>
    </div>
  );
}

// ────────── Components ──────────
// Shop-signage style section header — mimics the PB Chai Café storefront signage:
// dark brown wood-tone panel, soft golden spotlights from top, curved-cup PB logo, gold serif title.
function SignageHeader({ title, subtitle }) {
  return (
    <div className="relative mb-8 sm:mb-10 mx-auto max-w-5xl">
      {/* Overhead spotlights */}
      <div className="absolute -top-3 left-1/4 w-24 h-6 bg-[radial-gradient(ellipse_at_center,rgba(245,222,140,0.55),transparent_70%)] blur-md pointer-events-none" />
      <div className="absolute -top-3 right-1/4 w-24 h-6 bg-[radial-gradient(ellipse_at_center,rgba(245,222,140,0.55),transparent_70%)] blur-md pointer-events-none" />
      <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-28 h-7 bg-[radial-gradient(ellipse_at_center,rgba(245,222,140,0.65),transparent_70%)] blur-md pointer-events-none" />

      <div
        className="relative rounded-md border border-[#7A5824]/60 px-5 sm:px-8 py-5 sm:py-6 shadow-[inset_0_0_40px_rgba(0,0,0,0.6),0_18px_50px_rgba(0,0,0,0.5)] overflow-hidden"
        style={{
          background:
            'linear-gradient(180deg, #3A2410 0%, #2A180A 45%, #1E1108 100%)',
        }}
      >
        {/* Subtle wood grain */}
        <div className="absolute inset-0 opacity-[0.08] pointer-events-none mix-blend-overlay"
             style={{
               backgroundImage:
                 'repeating-linear-gradient(90deg, rgba(255,200,120,0.5) 0px, rgba(255,200,120,0.5) 1px, transparent 1px, transparent 6px)',
             }} />
        {/* Top edge highlight */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#E8C16A]/40 to-transparent" />
        {/* Bottom edge shadow */}
        <div className="absolute bottom-0 left-0 right-0 h-px bg-black/60" />

        <div className="relative flex items-center justify-center gap-4 sm:gap-6">
          {/* PB curved cup logo */}
          <div className="hidden sm:flex flex-shrink-0 items-center justify-center w-16 h-16 lg:w-20 lg:h-20 rounded-full border-2 border-[#E8C16A]/70 bg-[#1A0F06] shadow-[0_0_25px_rgba(232,193,106,0.35),inset_0_0_10px_rgba(232,193,106,0.15)]">
            <Coffee className="h-7 w-7 lg:h-9 lg:w-9 text-[#E8C16A]" strokeWidth={1.5} />
          </div>

          <div className="text-center min-w-0">
            <h2
              className="font-heading font-light tracking-wide leading-[1.05] text-2xl sm:text-3xl lg:text-[2.6rem]"
              style={{
                color: '#F2D27A',
                textShadow:
                  '0 0 18px rgba(232,193,106,0.5), 0 0 2px rgba(255,230,160,0.6)',
              }}
            >
              {title}
            </h2>
            {subtitle && (
              <p
                className="mt-2 font-heading italic text-xs sm:text-sm lg:text-base"
                style={{ color: '#E8C16A', textShadow: '0 0 8px rgba(232,193,106,0.3)' }}
              >
                {subtitle}
              </p>
            )}
          </div>

          {/* Mirror cup logo (desktop only for balance) */}
          <div className="hidden lg:flex flex-shrink-0 items-center justify-center w-16 h-16 lg:w-20 lg:h-20 rounded-full border-2 border-[#E8C16A]/70 bg-[#1A0F06] shadow-[0_0_25px_rgba(232,193,106,0.35),inset_0_0_10px_rgba(232,193,106,0.15)]">
            <Coffee className="h-7 w-7 lg:h-9 lg:w-9 text-[#E8C16A]" strokeWidth={1.5} />
          </div>
        </div>
      </div>
    </div>
  );
}

function Section({ id, title, subtitle, children }) {
  return (
    <section id={id} className="relative py-12 sm:py-16 lg:py-20 border-t border-[#A87A2A]/20">
      <div className="container mx-auto px-4 lg:px-12 max-w-6xl">
        <SignageHeader title={title} subtitle={subtitle} />
        {children}
      </div>
    </section>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between items-center py-2 text-sm font-body">
      <span className="text-[#E8D5A8]/85">{label}</span>
      <span className="text-[#F5E6B0] font-medium">{value}</span>
    </div>
  );
}

function BigStat({ label, value, sub, icon: Icon }) {
  return (
    <div className="p-5 sm:p-6 bg-[#1A1208]/90 border border-[#D4AF37]/40 text-center">
      {Icon && <Icon className="h-5 w-5 text-[#D4AF37] mx-auto mb-2" />}
      <p className="text-[10px] uppercase tracking-[0.3em] text-[#D4AF37] font-body">{label}</p>
      <p className="font-heading text-2xl sm:text-3xl lg:text-4xl text-[#F2C84B] mt-2 font-light leading-tight">{value}</p>
      {sub && <p className="text-[11px] text-[#E8D5A8]/70 mt-1 italic font-body">{sub}</p>}
    </div>
  );
}

function ApplicationForm({ onSubmitted }) {
  const [f, setF] = useState({
    full_name: '', mobile: '', email: '', city: '', state: '', country: 'India',
    occupation: '', business_experience: '', investment_capacity: '',
    preferred_location: '', available_area: '', expected_launch: '', message: '',
    agreed_disclosure: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const setVal = (k, v) => setF(prev => ({ ...prev, [k]: v }));

  const submit = async () => {
    if (!f.full_name || !f.mobile) { toast.error('Name & mobile are required'); return; }
    if (!f.agreed_disclosure) { toast.error('Please agree to the Franchise Disclosure'); return; }
    setSubmitting(true);
    try {
      await axios.post(`${API}/api/pb-chai/franchise-application`, f);
      onSubmitted();
    } catch {
      toast.error('Could not submit. Please try again.');
    } finally { setSubmitting(false); }
  };

  const FIELDS = [
    ['full_name', 'Full Name *', 'text'],
    ['mobile', 'Mobile *', 'tel'],
    ['email', 'Email', 'email'],
    ['city', 'City', 'text'],
    ['state', 'State', 'text'],
    ['country', 'Country', 'text'],
    ['occupation', 'Occupation', 'text'],
    ['business_experience', 'Business Experience', 'text'],
    ['investment_capacity', 'Investment Capacity', 'text'],
    ['preferred_location', 'Preferred Location', 'text'],
    ['available_area', 'Available Area (sq.ft.)', 'text'],
    ['expected_launch', 'Expected Launch Date', 'date'],
  ];

  return (
    <div className="max-w-3xl mx-auto bg-[#1A1208]/90 border border-[#A87A2A]/30 p-5 sm:p-7">
      <div className="grid sm:grid-cols-2 gap-3 sm:gap-4">
        {FIELDS.map(([key, label, type]) => (
          <div key={key} className={key === 'message' ? 'sm:col-span-2' : ''}>
            <Label className="text-[10px] uppercase tracking-wider text-[#D4AF37]/80">{label}</Label>
            <Input
              type={type}
              value={f[key]}
              onChange={e => setVal(key, e.target.value)}
              className="bg-[#0E0A06] border-[#A87A2A]/30 text-[#F5E6B0] focus-visible:ring-[#D4AF37]/40"
              data-testid={`pbchai-app-${key}`}
            />
          </div>
        ))}
        <div className="sm:col-span-2">
          <Label className="text-[10px] uppercase tracking-wider text-[#D4AF37]/80">Message</Label>
          <Textarea
            value={f.message}
            onChange={e => setVal('message', e.target.value)}
            rows={3}
            className="bg-[#0E0A06] border-[#A87A2A]/30 text-[#F5E6B0]"
            data-testid="pbchai-app-message"
          />
        </div>
      </div>
      <label className="flex items-start gap-2 mt-5 cursor-pointer text-xs sm:text-sm text-[#E8D5A8] font-body">
        <Checkbox
          checked={f.agreed_disclosure}
          onCheckedChange={(v) => setVal('agreed_disclosure', !!v)}
          className="border-[#D4AF37]/40 data-[state=checked]:bg-[#D4AF37] data-[state=checked]:border-[#D4AF37] mt-0.5"
          data-testid="pbchai-app-agree"
        />
        I agree to the Franchise Disclosure. I understand the franchise fee, royalty structure and ongoing commitments.
      </label>
      <Button
        onClick={submit}
        disabled={submitting}
        className="w-full mt-5 bg-gradient-to-r from-[#D4AF37] via-[#E5C158] to-[#B8862E] hover:from-[#C49E26] hover:to-[#A8761E] text-[#0E0A06] py-5 rounded-full text-xs tracking-[0.25em] uppercase font-bold border-0"
        data-testid="pbchai-app-submit"
      >
        {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Send className="h-4 w-4 mr-2" /> Submit Franchise Interest</>}
      </Button>
    </div>
  );
}

function ThankYou({ onReset }) {
  return (
    <div className="max-w-xl mx-auto text-center bg-[#1A1208]/90 border border-[#D4AF37]/40 p-7 sm:p-9" data-testid="pbchai-app-thanks">
      <CheckCircle2 className="h-12 w-12 text-[#D4AF37] mx-auto mb-3" />
      <h3 className="font-heading text-2xl text-[#F5E6B0]">Thank you for your interest.</h3>
      <p className="font-body italic text-sm text-[#E8D5A8]/85 mt-3 leading-relaxed">
        Our franchise team will contact you shortly.<br />
        Once approved and Franchise Fee is paid,<br />
        the Franchise Agreement will be generated<br />
        and the onboarding process will begin.
      </p>
      <button onClick={onReset} className="mt-4 text-[11px] text-[#D4AF37] underline font-body">Submit another application</button>
    </div>
  );
}

function DownloadPdfButton({ variant = 'primary' }) {
  const [busy, setBusy] = useState(false);
  const onClick = async () => {
    setBusy(true);
    try {
      // Always fetch the latest config so admin updates reflect in the PDF
      const { data: liveCfg } = await axios.get(`${API}/api/pb-chai/config`);
      await downloadFranchisePDF(liveCfg);
      toast.success('Brochure downloaded');
    } catch (e) {
      console.error(e);
      toast.error('Could not generate PDF. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const base = 'rounded-full text-xs tracking-[0.25em] uppercase font-bold border-0 shadow-[0_0_30px_rgba(212,175,55,0.4)] bg-gradient-to-r from-[#D4AF37] via-[#E5C158] to-[#B8862E] hover:from-[#C49E26] hover:to-[#A8761E] text-[#0E0A06]';
  const outlined = 'border border-[#D4AF37]/50 bg-transparent text-[#D4AF37] hover:bg-[#D4AF37]/10 rounded-full text-xs tracking-[0.25em] uppercase font-semibold';
  return (
    <Button
      onClick={onClick}
      disabled={busy}
      className={`${variant === 'footer' ? outlined : base} px-6 py-5`}
      data-testid="pbchai-download-pdf-btn"
    >
      {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
      {busy ? 'Generating…' : 'Download Brochure (PDF)'}
    </Button>
  );
}
