// Shared customer-facing Promo Timer / Advertisement widget
// Usage:
//   <PromoTimer variant="banner" region="India" />   (homepage strip)
//   <PromoTimer variant="sticky" region="India" />   (Pickup / TableBooking top bar)
import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { Clock, Sparkles, X } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const toMinutes = (hhmm) => {
  if (!hhmm) return 0;
  const [h, m] = hhmm.split(':').map(Number);
  return (h || 0) * 60 + (m || 0);
};

const fmtCountdown = (totalSeconds) => {
  if (totalSeconds <= 0) return '0s';
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${String(s).padStart(2, '0')}s`;
  return `${s}s`;
};

const fmtClock = (hhmm) => {
  if (!hhmm) return '';
  const [h, m] = hhmm.split(':').map(Number);
  const hr = h % 12 || 12;
  const ap = h >= 12 ? 'PM' : 'AM';
  return `${hr}:${String(m).padStart(2, '0')} ${ap}`;
};

export default function PromoTimer({ variant = 'banner', region = 'India', onDismiss }) {
  const [promotions, setPromotions] = useState(null);
  const [now, setNow] = useState(new Date());
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    axios.get(`${API}/api/promotions`).then(r => setPromotions(r.data)).catch(() => {});
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  // Pick the most relevant promo: live > starting-soon (within 3h) > null
  const status = useMemo(() => {
    if (!promotions) return null;
    const curMinutes = now.getHours() * 60 + now.getMinutes();
    const curSeconds = now.getSeconds();
    const candidates = ['brunch', 'evening_snack'].map(key => {
      const p = promotions[key];
      if (!p || !p.enabled || !(p.regions || []).includes(region)) return null;
      const startMin = toMinutes(p.start_time);
      const endMin = toMinutes(p.end_time);
      const isLive = curMinutes >= startMin && curMinutes < endMin;
      const secondsUntilEnd = (endMin - curMinutes) * 60 - curSeconds;
      const secondsUntilStart = (startMin - curMinutes) * 60 - curSeconds;
      return {
        key,
        promo: p,
        isLive,
        secondsUntilEnd: Math.max(0, secondsUntilEnd),
        secondsUntilStart: Math.max(0, secondsUntilStart),
        startsSoon: !isLive && secondsUntilStart > 0 && secondsUntilStart <= 3 * 3600,
      };
    }).filter(Boolean);

    // Prefer live over starts-soon
    const live = candidates.find(c => c.isLive);
    if (live) return live;
    const starting = candidates.find(c => c.startsSoon);
    if (starting) return starting;
    return null;
  }, [promotions, now, region]);

  if (!status || dismissed) return null;
  const { promo, isLive, secondsUntilEnd, secondsUntilStart, key } = status;
  const pct = promo.discount_pct || 0;
  const label = promo.label || (key === 'brunch' ? 'Brunch Combo' : 'Evening Snack Combo');

  // --- BANNER variant (homepage hero strip) ---
  if (variant === 'banner') {
    return (
      <div
        className={`relative overflow-hidden border-y ${isLive ? 'bg-gradient-to-r from-[#B8962E] via-[#D4AF37] to-[#B8962E] border-[#D4AF37]' : 'bg-[#FFF8E7] border-[#E8DFD0]'}`}
        data-testid="promo-banner-home"
      >
        {isLive && (
          <div className="absolute inset-0 opacity-20 pointer-events-none bg-[radial-gradient(circle_at_20%_50%,rgba(255,255,255,0.6),transparent_40%)]" />
        )}
        <div className="relative container mx-auto px-6 py-3 flex items-center gap-3 justify-between flex-wrap">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className={`flex items-center gap-2 px-2.5 py-1 rounded-full ${isLive ? 'bg-white/20 backdrop-blur-sm' : 'bg-[#B8962E]/10'}`}>
              <span className={`h-2 w-2 rounded-full ${isLive ? 'bg-white animate-pulse' : 'bg-[#B8962E]'}`} />
              <span className={`text-[10px] font-bold tracking-widest uppercase ${isLive ? 'text-white' : 'text-[#B8962E]'}`}>
                {isLive ? 'Live Now' : 'Coming Up'}
              </span>
            </div>
            <p className={`font-body text-sm md:text-base font-semibold truncate ${isLive ? 'text-white' : 'text-[#3D2314]'}`}>
              <Sparkles className="inline h-4 w-4 mr-1 -mt-0.5" />
              {label} — <span className="font-heading">{pct}% OFF</span>
              {isLive
                ? <span className={`ml-2 font-body text-xs md:text-sm opacity-90`}>ends in {fmtCountdown(secondsUntilEnd)}</span>
                : <span className={`ml-2 font-body text-xs md:text-sm opacity-80`}>starts in {fmtCountdown(secondsUntilStart)} ({fmtClock(promo.start_time)})</span>
              }
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <a
              href="/pickup"
              className={`text-xs md:text-sm font-body font-bold px-4 py-1.5 rounded-full tracking-wider uppercase transition-all ${isLive ? 'bg-[#3D2314] text-[#F5DEB3] hover:bg-[#2D1810]' : 'bg-[#B8962E] text-white hover:bg-[#D4AF37]'}`}
              data-testid="promo-banner-cta"
            >
              Order Now
            </a>
            <button
              onClick={() => { setDismissed(true); if (onDismiss) onDismiss(); }}
              className={`p-1 rounded-full transition-colors ${isLive ? 'text-white/70 hover:text-white hover:bg-white/10' : 'text-[#7A6F65] hover:text-[#3D2314] hover:bg-[#E8DFD0]'}`}
              aria-label="Dismiss promotion"
              data-testid="promo-banner-dismiss"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // --- STICKY variant (Pickup/TableBooking top bar) ---
  const comboHint = key === 'brunch'
    ? `Add 1 brunch combo + 1 tea/drink to unlock ${pct}% off`
    : `Add 1 snack + 1 masala tea to unlock ${pct}% off`;

  return (
    <div
      className={`relative border-2 rounded-lg p-3 md:p-4 ${isLive ? 'border-[#2E7D32] bg-gradient-to-r from-[#F0FFF0] to-[#F5FFF5]' : 'border-[#B8962E]/30 bg-[#FFFAED]'}`}
      data-testid="promo-timer-sticky"
    >
      <button
        onClick={() => setDismissed(true)}
        className="absolute top-2 right-2 text-[#7A6F65]/60 hover:text-[#3D2314] p-1"
        aria-label="Dismiss"
        data-testid="promo-timer-dismiss"
      >
        <X className="h-3.5 w-3.5" />
      </button>
      <div className="flex items-start gap-3 pr-6">
        <div className={`shrink-0 p-2 rounded-full ${isLive ? 'bg-[#2E7D32] text-white' : 'bg-[#B8962E]/15 text-[#B8962E]'}`}>
          {isLive ? <Sparkles className="h-5 w-5" /> : <Clock className="h-5 w-5" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className={`font-heading text-sm md:text-base font-semibold ${isLive ? 'text-[#2E7D32]' : 'text-[#3D2314]'}`}>
              {label} • {pct}% OFF
            </p>
            {isLive && (
              <span className="inline-flex items-center gap-1 text-[10px] font-bold tracking-widest uppercase bg-[#2E7D32] text-white px-2 py-0.5 rounded-full">
                <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" /> Live
              </span>
            )}
          </div>
          <p className="text-xs text-[#5C4A3A] font-body mt-1">{comboHint}</p>
          <div className={`mt-2 font-mono text-xs md:text-sm font-bold ${isLive ? 'text-[#2E7D32]' : 'text-[#B8962E]'}`} data-testid="promo-timer-countdown">
            {isLive
              ? <>⏱ Ends in {fmtCountdown(secondsUntilEnd)}</>
              : <>🕐 Starts in {fmtCountdown(secondsUntilStart)} ({fmtClock(promo.start_time)})</>
            }
          </div>
        </div>
      </div>
    </div>
  );
}
