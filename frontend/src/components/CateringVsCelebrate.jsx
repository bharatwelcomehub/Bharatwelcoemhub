import { Link } from 'react-router-dom';
import { Truck, Home, ArrowRight, CheckCircle2, Info } from 'lucide-react';

/**
 * CateringVsCelebrate
 * Shown at the top of both /catering and /wedding-booking so guests pick the right service.
 * Highlights the "current" choice and offers a one-tap switch to the other.
 *
 * Props:
 *  - current: 'catering' | 'celebrate'
 */
export default function CateringVsCelebrate({ current = 'catering' }) {
  const items = [
    {
      key: 'celebrate',
      title: 'Celebrate at Purnabramha',
      tagline: 'Host your event INSIDE our restaurant',
      bullets: [
        'Wedding, Birthday, Anniversary, Haldi, Munj at our venue',
        'We provide the hall + thali + service + decor',
        'You and your guests dine with us',
      ],
      Icon: Home,
      path: '/wedding-booking',
      cta: 'Plan my Celebration',
    },
    {
      key: 'catering',
      title: 'Catering at Your Venue',
      tagline: 'We cook & deliver to YOUR location',
      bullets: [
        'Food delivered to your home, society hall, office',
        'Optional crockery, staff & on-site service',
        'Perfect for housewarmings, pooja, corporate events',
      ],
      Icon: Truck,
      path: '/catering',
      cta: 'Plan my Catering',
    },
  ];

  return (
    <section
      className="bg-gradient-to-b from-[#FDFBF7] to-white border-y border-[#E8DFD0]"
      data-testid="catering-vs-celebrate"
    >
      <div className="container mx-auto px-4 sm:px-6 lg:px-12 py-6 sm:py-8">
        <div className="flex items-start gap-2 mb-4">
          <Info className="h-4 w-4 text-[#B8962E] flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-[10px] uppercase tracking-[0.25em] text-[#B8962E] font-body font-semibold">
              Not sure which to pick?
            </p>
            <h3 className="font-heading text-base sm:text-lg text-[#3D2314] leading-tight">
              Choose what matches your need
            </h3>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-3 sm:gap-4">
          {items.map(({ key, title, tagline, bullets, Icon, path, cta }) => {
            const isCurrent = key === current;
            return (
              <div
                key={key}
                className={`relative p-4 sm:p-5 border transition-all ${
                  isCurrent
                    ? 'border-[#B8962E] bg-[#B8962E]/5 ring-1 ring-[#B8962E]/30'
                    : 'border-[#E8DFD0] bg-white hover:border-[#B8962E]/40'
                }`}
                data-testid={`vs-card-${key}`}
              >
                {isCurrent && (
                  <span className="absolute -top-2 left-3 bg-[#B8962E] text-white text-[9px] uppercase tracking-wider px-2 py-0.5 font-body font-semibold">
                    You're here
                  </span>
                )}
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-full flex-shrink-0 ${isCurrent ? 'bg-[#B8962E] text-white' : 'bg-[#F8F5F0] text-[#B8962E]'}`}>
                    <Icon className="h-4 w-4 sm:h-5 sm:w-5" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-heading text-sm sm:text-base text-[#3D2314] leading-tight">{title}</p>
                    <p className="font-heading italic text-[#B8962E] text-[11px] sm:text-xs">{tagline}</p>
                  </div>
                </div>
                <ul className="mt-3 space-y-1.5 text-[11px] sm:text-xs text-[#5C4A3A] font-body">
                  {bullets.map((b, i) => (
                    <li key={i} className="flex items-start gap-1.5 leading-snug">
                      <CheckCircle2 className={`h-3 w-3 mt-0.5 flex-shrink-0 ${isCurrent ? 'text-[#B8962E]' : 'text-[#B8962E]/60'}`} />
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
                {!isCurrent && (
                  <Link
                    to={path}
                    className="mt-3 inline-flex items-center gap-1 text-[11px] sm:text-xs font-body font-semibold text-[#B8962E] hover:text-[#8A6E1F] transition-colors"
                    data-testid={`vs-switch-${key}`}
                  >
                    Switch to this <ArrowRight className="h-3 w-3" />
                  </Link>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
