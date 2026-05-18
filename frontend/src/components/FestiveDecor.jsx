// Festive decorative SVGs — Toran (marigold garland), Tabla, Shehnai (Sanai), Diya, Mandala
// Pure SVG, no external deps. Designed to feel celebrative the moment the page loads.
import { motion } from 'framer-motion';

// ─── TORAN (Marigold + Mango leaf hanging garland) ─────────────────────────
// Renders as a flex row of repeating drops so marigolds stay big & proportional
// on any width. Uses an inline SVG drop motif. Auto-fills the row.
const TORAN_COUNT_MOBILE = 7;
const TORAN_COUNT_DESKTOP = 13;

const ToranDrop = ({ even }) => (
  <svg viewBox="0 0 60 90" className="block flex-shrink-0 w-[44px] sm:w-[60px] h-auto" aria-hidden="true">
    {/* Twine attach */}
    <line x1="30" y1="0" x2="30" y2={even ? 8 : 14} stroke="#7A4A1F" strokeWidth="1.4" opacity="0.7" />
    {/* Mango leaves pair */}
    <g transform={`translate(30, ${even ? 10 : 16})`}>
      <path d="M -10 0 Q -14 12 -4 18 Q 2 12 0 0 Z" fill="#3B7A2A" />
      <path d="M  10 0 Q  14 12   4 18 Q -2 12 0 0 Z" fill="#2F6321" />
      <path d="M -4 18 Q 0 24 4 18" fill="none" stroke="#1F4717" strokeWidth="0.7" />
    </g>
    {/* Marigold (multi-petal radial) */}
    <g transform={`translate(30, ${even ? 44 : 50})`}>
      {Array.from({ length: 12 }).map((_, p) => (
        <ellipse
          key={p}
          cx="0"
          cy="-10"
          rx="4.6"
          ry="8"
          fill={p % 2 === 0 ? '#F2870D' : '#E96A0A'}
          transform={`rotate(${p * 30})`}
        />
      ))}
      <circle r="5.2" fill="#F2C84B" />
      <circle r="2.4" fill="#A8550A" />
    </g>
    {/* Gold bell drop */}
    <g transform={`translate(30, ${even ? 70 : 76})`}>
      <path d="M -4 0 Q 0 -8 4 0 L 3 8 L -3 8 Z" fill="#D4AF37" stroke="#8A6420" strokeWidth="0.5" />
      <circle cx="0" cy="10" r="1.8" fill="#B8862A" />
    </g>
  </svg>
);

export const Toran = ({ className = '' }) => (
  <div
    className={`relative w-full h-[70px] sm:h-[100px] ${className}`}
    aria-hidden="true"
  >
    {/* Curved twine using SVG that stretches */}
    <svg
      viewBox="0 0 1000 30"
      preserveAspectRatio="none"
      className="absolute top-1 left-0 w-full h-3 sm:h-4"
      aria-hidden="true"
    >
      <path
        d="M 0 6 Q 125 24, 250 6 T 500 6 T 750 6 T 1000 6"
        fill="none"
        stroke="#7A4A1F"
        strokeWidth="2.2"
        opacity="0.75"
      />
    </svg>
    {/* Drop row */}
    <div className="absolute top-0 left-0 right-0 flex justify-around items-start px-1 sm:px-2">
      {Array.from({ length: TORAN_COUNT_DESKTOP }).map((_, i) => (
        <div
          key={i}
          className={i >= TORAN_COUNT_MOBILE ? 'hidden sm:block' : ''}
          style={{ transform: i % 2 === 0 ? 'translateY(2px)' : 'translateY(8px)' }}
        >
          <ToranDrop even={i % 2 === 0} />
        </div>
      ))}
    </div>
  </div>
);

// ─── TABLA (pair of Indian drums) ─────────────────────────────────────────
export const Tabla = ({ className = '', size = 56 }) => (
  <svg viewBox="0 0 120 90" width={size} height={(size * 90) / 120} className={className} aria-hidden="true">
    {/* Bigger drum (Bayan – metal, left) */}
    <ellipse cx="35" cy="78" rx="22" ry="5" fill="#1A0F08" opacity="0.4" />
    <path d="M 14 38 Q 14 78 35 78 Q 56 78 56 38 Z" fill="url(#tablaMetal)" />
    <ellipse cx="35" cy="38" rx="21" ry="7" fill="#EFE4D1" stroke="#7A4A1F" strokeWidth="1" />
    <circle cx="35" cy="38" r="6" fill="#3A1F0E" />

    {/* Smaller drum (Dayan – wood, right) */}
    <ellipse cx="88" cy="80" rx="18" ry="4" fill="#1A0F08" opacity="0.4" />
    <path d="M 71 44 Q 71 80 88 80 Q 105 80 105 44 Z" fill="url(#tablaWood)" />
    <ellipse cx="88" cy="44" rx="17" ry="6" fill="#EFE4D1" stroke="#7A4A1F" strokeWidth="1" />
    <circle cx="88" cy="44" r="5" fill="#3A1F0E" />

    {/* Lacing on Dayan */}
    {Array.from({ length: 8 }).map((_, i) => (
      <line
        key={i}
        x1={72 + i * 4.4}
        y1="44"
        x2={72 + i * 4.4}
        y2="78"
        stroke="#D4AF37"
        strokeWidth="0.7"
        opacity="0.85"
      />
    ))}
    {/* Lacing on Bayan */}
    {Array.from({ length: 9 }).map((_, i) => (
      <line
        key={`b${i}`}
        x1={16 + i * 4.6}
        y1="38"
        x2={16 + i * 4.6}
        y2="76"
        stroke="#D4AF37"
        strokeWidth="0.7"
        opacity="0.85"
      />
    ))}

    <defs>
      <linearGradient id="tablaMetal" x1="0" x2="1">
        <stop offset="0" stopColor="#B8862A" />
        <stop offset="0.5" stopColor="#D4AF37" />
        <stop offset="1" stopColor="#7A4A1F" />
      </linearGradient>
      <linearGradient id="tablaWood" x1="0" x2="1">
        <stop offset="0" stopColor="#7A4A1F" />
        <stop offset="0.5" stopColor="#A86A2A" />
        <stop offset="1" stopColor="#5B3923" />
      </linearGradient>
    </defs>
  </svg>
);

// ─── SHEHNAI / SANAI (conical wind instrument) ─────────────────────────────
export const Shehnai = ({ className = '', size = 60 }) => (
  <svg viewBox="0 0 60 160" width={size * 0.4} height={size * 1.06} className={className} aria-hidden="true">
    {/* Mouthpiece (reed) */}
    <rect x="27" y="2" width="6" height="10" rx="1.5" fill="#3A1F0E" />
    {/* Top neck */}
    <rect x="25" y="12" width="10" height="6" fill="#7A4A1F" />
    {/* Main tube tapering down */}
    <path
      d="M 25 18 L 35 18 L 38 110 L 22 110 Z"
      fill="url(#shehnaiBody)"
      stroke="#3A1F0E"
      strokeWidth="0.8"
    />
    {/* Finger holes */}
    {[28, 42, 56, 70, 84, 98].map((cy, i) => (
      <circle key={i} cx="30" cy={cy} r="1.6" fill="#1A0F08" />
    ))}
    {/* Gold rings */}
    {[22, 50, 78, 106].map((cy, i) => (
      <rect key={i} x="22" y={cy} width="16" height="2.4" fill="#D4AF37" opacity="0.9" />
    ))}
    {/* Bell/flare */}
    <path
      d="M 22 110 L 38 110 L 54 156 L 6 156 Z"
      fill="url(#shehnaiBell)"
      stroke="#3A1F0E"
      strokeWidth="0.8"
    />
    {/* Bell rim accent */}
    <rect x="6" y="152" width="48" height="4" fill="#D4AF37" />

    <defs>
      <linearGradient id="shehnaiBody" x1="0" x2="1">
        <stop offset="0" stopColor="#8A5A24" />
        <stop offset="0.5" stopColor="#C8902F" />
        <stop offset="1" stopColor="#6E4419" />
      </linearGradient>
      <linearGradient id="shehnaiBell" x1="0" x2="1">
        <stop offset="0" stopColor="#7A4A1F" />
        <stop offset="0.5" stopColor="#D4AF37" />
        <stop offset="1" stopColor="#7A4A1F" />
      </linearGradient>
    </defs>
  </svg>
);

// ─── DIYA (oil lamp) ──────────────────────────────────────────────────────
export const Diya = ({ className = '', size = 40, animate = true }) => (
  <svg viewBox="0 0 80 80" width={size} height={size} className={className} aria-hidden="true">
    {/* Glow halo */}
    <motion.circle
      cx="40"
      cy="24"
      r="14"
      fill="#FFD480"
      opacity="0.35"
      animate={animate ? { opacity: [0.25, 0.55, 0.25], scale: [1, 1.08, 1] } : {}}
      transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
    />
    {/* Flame */}
    <motion.path
      d="M 40 12 Q 33 22 36 30 Q 40 38 44 30 Q 47 22 40 12 Z"
      fill="#FF9B26"
      animate={animate ? { scaleY: [1, 1.12, 0.96, 1], transformOrigin: '40px 30px' } : {}}
      transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
    />
    <path d="M 40 18 Q 37 24 39 28 Q 40 32 41 28 Q 43 24 40 18 Z" fill="#FFE68A" />
    {/* Wick */}
    <rect x="39" y="30" width="2" height="4" fill="#3A1F0E" />
    {/* Bowl */}
    <path d="M 18 36 Q 40 60 62 36 L 58 50 Q 40 64 22 50 Z" fill="#A86A2A" />
    <path d="M 22 50 Q 40 64 58 50 L 56 56 Q 40 66 24 56 Z" fill="#7A4A1F" />
    {/* Decorations */}
    <circle cx="28" cy="46" r="1.4" fill="#D4AF37" />
    <circle cx="52" cy="46" r="1.4" fill="#D4AF37" />
    <circle cx="40" cy="58" r="1.6" fill="#D4AF37" />
  </svg>
);

// ─── MANDALA background motif (subtle, repeating) ─────────────────────────
export const Mandala = ({ className = '', opacity = 0.07 }) => (
  <svg
    viewBox="0 0 200 200"
    className={className}
    style={{ opacity }}
    aria-hidden="true"
  >
    <g transform="translate(100 100)" fill="none" stroke="#D4AF37" strokeWidth="0.9">
      <circle r="90" />
      <circle r="72" />
      <circle r="54" />
      <circle r="36" />
      <circle r="18" />
      {Array.from({ length: 16 }).map((_, i) => (
        <g key={i} transform={`rotate(${i * 22.5})`}>
          <path d="M 0 -90 Q 6 -70 0 -54 Q -6 -70 0 -90" />
          <circle cx="0" cy="-90" r="2.4" fill="#D4AF37" />
        </g>
      ))}
    </g>
  </svg>
);

// ─── Sparkle particle (used absolutely positioned) ─────────────────────────
export const Sparkle = ({ className = '', delay = 0 }) => (
  <motion.svg
    viewBox="0 0 20 20"
    className={className}
    aria-hidden="true"
    initial={{ opacity: 0, scale: 0.6 }}
    animate={{ opacity: [0, 1, 0], scale: [0.6, 1.1, 0.6] }}
    transition={{ duration: 2.6, repeat: Infinity, delay, ease: 'easeInOut' }}
  >
    <path d="M 10 0 L 12 8 L 20 10 L 12 12 L 10 20 L 8 12 L 0 10 L 8 8 Z" fill="#D4AF37" />
  </motion.svg>
);
