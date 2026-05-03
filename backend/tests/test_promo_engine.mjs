// Standalone Node test of promoEngine — verifies discount math without needing browser time
import { evaluatePromotion } from '/app/frontend/src/utils/promoEngine.js';

const PROMOTIONS = {
  brunch: {
    enabled: true,
    label: 'Everyday Brunch Combo',
    start_time: '11:00',
    end_time: '12:00',
    discount_pct: 10,
    regions: ['India', 'Australia'],
    combo_categories: ['Heavy Brunch', 'Bhakar Combo'],
    drink_categories: ['Tea & Coffee', 'Drinks'],
    min_combo_qty: 1,
    min_drink_qty: 1,
  },
  evening_snack: {
    enabled: true,
    label: 'Evening Snack Combo',
    start_time: '16:00',
    end_time: '17:00',
    discount_pct: 10,
    regions: ['India'],
    snack_categories: ['Snacks'],
    tea_keyword: 'masala',
    min_snack_qty: 1,
    min_tea_qty: 1,
  },
};

let pass = 0, fail = 0;
const t = (name, cond, extra='') => { if (cond) { pass++; console.log('PASS:', name); } else { fail++; console.log('FAIL:', name, extra); } };

const at = (h, m=0) => { const d = new Date(); d.setHours(h, m, 0, 0); return d; };

// 1. Brunch eligible at 11:30 IN India
{
  const cart = {
    a: { id:'a', name:'Poha Plate', qty:1, price:200, categoryName:'Heavy Brunch' },
    b: { id:'b', name:'Masala Chai', qty:1, price:50, categoryName:'Tea & Coffee' },
  };
  const r = evaluatePromotion({ cart, promotions: PROMOTIONS, country:'India', now: at(11,30) });
  t('Brunch applies at 11:30 India HSR with brunch+drink', r.applied === 'brunch' && r.discount === 25);
}

// 2. Brunch eligible Perth (Australia) too
{
  const cart = {
    a: { id:'a', name:'Bhakar', qty:1, price:300, categoryName:'Bhakar Combo' },
    b: { id:'b', name:'Lassi', qty:1, price:100, categoryName:'Drinks' },
  };
  const r = evaluatePromotion({ cart, promotions: PROMOTIONS, country:'Australia', now: at(11,30) });
  t('Brunch applies in Australia/Perth', r.applied === 'brunch' && Math.abs(r.discount - 40) < 0.01);
}

// 3. Brunch outside window (10 AM) - not applied
{
  const cart = {
    a: { id:'a', name:'Poha Plate', qty:1, price:200, categoryName:'Heavy Brunch' },
    b: { id:'b', name:'Masala Chai', qty:1, price:50, categoryName:'Tea & Coffee' },
  };
  const r = evaluatePromotion({ cart, promotions: PROMOTIONS, country:'India', now: at(10,0) });
  t('Brunch NOT applied at 10 AM (outside window)', r.applied === null);
}

// 4. Brunch only one item (combo only, no drink) — not applied
{
  const cart = {
    a: { id:'a', name:'Poha Plate', qty:1, price:200, categoryName:'Heavy Brunch' },
  };
  const r = evaluatePromotion({ cart, promotions: PROMOTIONS, country:'India', now: at(11,30) });
  t('Brunch NOT applied without drink', r.applied === null);
}

// 5. Evening snack at 4:30 PM in India: snack + masala tea
{
  const cart = {
    a: { id:'a', name:'Bhel Puri', qty:1, price:80, categoryName:'Snacks' },
    b: { id:'b', name:'Masala Chai', qty:1, price:40, categoryName:'Tea & Coffee' },
  };
  const r = evaluatePromotion({ cart, promotions: PROMOTIONS, country:'India', now: at(16,30) });
  t('Evening Snack applies at 4:30 PM India', r.applied === 'evening_snack' && Math.abs(r.discount - 12) < 0.01);
}

// 6. Evening snack NOT in Australia
{
  const cart = {
    a: { id:'a', name:'Bhel Puri', qty:1, price:80, categoryName:'Snacks' },
    b: { id:'b', name:'Masala Chai', qty:1, price:40, categoryName:'Tea & Coffee' },
  };
  const r = evaluatePromotion({ cart, promotions: PROMOTIONS, country:'Australia', now: at(16,30) });
  t('Evening Snack NOT applied in Australia (regions=India only)', r.applied === null);
}

// 7. Evening snack: only snack, no masala tea
{
  const cart = {
    a: { id:'a', name:'Bhel Puri', qty:1, price:80, categoryName:'Snacks' },
    b: { id:'b', name:'Coffee', qty:1, price:40, categoryName:'Tea & Coffee' },
  };
  const r = evaluatePromotion({ cart, promotions: PROMOTIONS, country:'India', now: at(16,30) });
  t('Evening Snack NOT applied without masala in name', r.applied === null);
}

// 8. Snack at 11 AM (outside evening window, but brunch window — but no brunch eligibility)
{
  const cart = {
    a: { id:'a', name:'Bhel Puri', qty:1, price:80, categoryName:'Snacks' },
    b: { id:'b', name:'Masala Chai', qty:1, price:40, categoryName:'Tea & Coffee' },
  };
  const r = evaluatePromotion({ cart, promotions: PROMOTIONS, country:'India', now: at(11,15) });
  // At 11 AM, the masala chai is in Tea & Coffee category — but Bhel Puri is "Snacks", not Heavy Brunch / Bhakar Combo
  // So brunch combo should NOT apply, and evening_snack window not active.
  t('Snack+chai at 11 AM does NOT trigger any promo (no brunch combo item)', r.applied === null);
}

// 9. Disabled brunch — no application
{
  const promo2 = JSON.parse(JSON.stringify(PROMOTIONS));
  promo2.brunch.enabled = false;
  const cart = {
    a: { id:'a', name:'Poha', qty:1, price:200, categoryName:'Heavy Brunch' },
    b: { id:'b', name:'Tea', qty:1, price:50, categoryName:'Tea & Coffee' },
  };
  const r = evaluatePromotion({ cart, promotions: promo2, country:'India', now: at(11,30) });
  t('Disabled brunch -> no promo', r.applied === null);
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
