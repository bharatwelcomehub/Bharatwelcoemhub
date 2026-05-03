// Shared discount/promo evaluator for Pickup + Table Booking carts.
// Inputs:
//  - cart: { [id]: { id, name, qty, price, categoryName? } }
//  - promotions: { brunch: {...}, evening_snack: {...} }   (from /api/promotions)
//  - country: 'India' | 'Australia'
//  - now: Date (optional override; defaults to current time)
// Returns: { applied: 'brunch' | 'evening_snack' | null, discount: number, label, message, eligible_pct }

const toMinutes = (hhmm) => {
  if (!hhmm) return 0;
  const [h, m] = hhmm.split(':').map(Number);
  return (h || 0) * 60 + (m || 0);
};

const inWindow = (now, start, end) => {
  const cur = now.getHours() * 60 + now.getMinutes();
  return cur >= toMinutes(start) && cur < toMinutes(end);
};

const cartItems = (cart) => Object.values(cart || {});

const matchesAnyCategory = (item, categories) => {
  const cat = (item.categoryName || item.category || '').toLowerCase();
  return (categories || []).some(c => cat === c.toLowerCase());
};

const subtotal = (cart) => cartItems(cart).reduce((s, it) => s + (it.price || 0) * (it.qty || 0), 0);

export function evaluatePromotion({ cart, promotions, country, now }) {
  if (!promotions) return { applied: null, discount: 0 };
  const _now = now || new Date();
  const items = cartItems(cart);
  if (items.length === 0) return { applied: null, discount: 0 };
  const total = subtotal(cart);

  // ---------- Brunch combo ----------
  const b = promotions.brunch;
  if (b && b.enabled && (b.regions || []).includes(country) && inWindow(_now, b.start_time, b.end_time)) {
    const comboQty = items.filter(i => matchesAnyCategory(i, b.combo_categories)).reduce((s, i) => s + (i.qty || 0), 0);
    const drinkQty = items.filter(i => matchesAnyCategory(i, b.drink_categories)).reduce((s, i) => s + (i.qty || 0), 0);
    if (comboQty >= (b.min_combo_qty || 1) && drinkQty >= (b.min_drink_qty || 1)) {
      const pct = b.discount_pct || 0;
      return {
        applied: 'brunch',
        label: b.label || 'Brunch Combo',
        discount: +(total * pct / 100).toFixed(2),
        pct,
        message: `${b.label || 'Brunch Combo'} applied — ${pct}% off`,
      };
    }
  }

  // ---------- Evening snack combo ----------
  const s = promotions.evening_snack;
  if (s && s.enabled && (s.regions || []).includes(country) && inWindow(_now, s.start_time, s.end_time)) {
    const snackQty = items.filter(i => matchesAnyCategory(i, s.snack_categories)).reduce((s2, i) => s2 + (i.qty || 0), 0);
    const teaKw = (s.tea_keyword || 'masala').toLowerCase();
    const teaQty = items.filter(i => (i.name || '').toLowerCase().includes(teaKw)).reduce((s2, i) => s2 + (i.qty || 0), 0);
    if (snackQty >= (s.min_snack_qty || 1) && teaQty >= (s.min_tea_qty || 1)) {
      const pct = s.discount_pct || 0;
      return {
        applied: 'evening_snack',
        label: s.label || 'Evening Snack Combo',
        discount: +(total * pct / 100).toFixed(2),
        pct,
        message: `${s.label || 'Evening Snack Combo'} applied — ${pct}% off`,
      };
    }
  }

  // ---------- Hint: nothing applied — provide context for UI hint ----------
  // Tell user about active windows so they know the offer exists
  const hints = [];
  if (b && b.enabled && (b.regions || []).includes(country)) {
    hints.push({ key: 'brunch', label: b.label || 'Brunch Combo', start: b.start_time, end: b.end_time, pct: b.discount_pct || 0, in_window: inWindow(_now, b.start_time, b.end_time) });
  }
  if (s && s.enabled && (s.regions || []).includes(country)) {
    hints.push({ key: 'evening_snack', label: s.label || 'Evening Snack Combo', start: s.start_time, end: s.end_time, pct: s.discount_pct || 0, in_window: inWindow(_now, s.start_time, s.end_time) });
  }
  return { applied: null, discount: 0, hints };
}
