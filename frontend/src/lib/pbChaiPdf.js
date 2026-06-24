// PB Chai Café Franchise Brochure — client-side PDF generator
// Rebuilds the PDF every time using the LIVE admin config passed in,
// so any admin-side update is reflected in the next download.
import { jsPDF } from 'jspdf';

const fmtINR = (n) => `Rs. ${(Number(n) || 0).toLocaleString('en-IN')}`;

// Color palette — matches the on-page black & gold theme
const COLOR = {
  bg: [14, 10, 6],          // #0E0A06
  panel: [26, 18, 8],       // #1A1208
  panelLine: [122, 88, 36], // #7A5824
  gold: [212, 175, 55],     // #D4AF37
  goldBright: [242, 200, 122], // #F2C87A
  cream: [245, 230, 176],   // #F5E6B0
  body: [232, 213, 168],    // #E8D5A8
  bodyDim: [170, 152, 110],
  red: [220, 90, 70],
};

const PAGE_W = 210; // A4 mm
const PAGE_H = 297;
const M = 14;        // margin

function setFill(doc, rgb) { doc.setFillColor(rgb[0], rgb[1], rgb[2]); }
function setText(doc, rgb) { doc.setTextColor(rgb[0], rgb[1], rgb[2]); }
function setDraw(doc, rgb) { doc.setDrawColor(rgb[0], rgb[1], rgb[2]); }

function paintBackground(doc) {
  setFill(doc, COLOR.bg);
  doc.rect(0, 0, PAGE_W, PAGE_H, 'F');
}

// Shop-signage style page header band (mirrors the on-page SignageHeader)
function drawSignageHeader(doc, title, subtitle) {
  const x = M;
  const y = M;
  const w = PAGE_W - 2 * M;
  const h = 26;
  // Panel
  setFill(doc, [42, 24, 10]);
  doc.roundedRect(x, y, w, h, 2, 2, 'F');
  setDraw(doc, COLOR.panelLine);
  doc.setLineWidth(0.4);
  doc.roundedRect(x, y, w, h, 2, 2, 'S');
  // Top gold edge
  setDraw(doc, COLOR.goldBright);
  doc.setLineWidth(0.15);
  doc.line(x + 3, y + 0.6, x + w - 3, y + 0.6);

  // Curved PB cup logo circle (left)
  const cx = x + 13;
  const cy = y + h / 2;
  setDraw(doc, COLOR.goldBright);
  doc.setLineWidth(0.6);
  doc.circle(cx, cy, 7.5, 'S');
  // tiny cup glyph
  setFill(doc, [26, 15, 6]);
  doc.circle(cx, cy, 7.0, 'F');
  setText(doc, COLOR.goldBright);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.text('PB', cx, cy + 1, { align: 'center' });

  // Title
  setText(doc, COLOR.goldBright);
  doc.setFont('times', 'normal');
  doc.setFontSize(22);
  doc.text(title, PAGE_W / 2, y + 13, { align: 'center' });
  if (subtitle) {
    setText(doc, COLOR.gold);
    doc.setFont('times', 'italic');
    doc.setFontSize(10);
    doc.text(subtitle, PAGE_W / 2, y + 21, { align: 'center' });
  }
  return y + h + 6;
}

function ensureSpace(doc, cursor, needed) {
  if (cursor + needed > PAGE_H - M - 10) {
    drawFooter(doc);
    doc.addPage();
    paintBackground(doc);
    return drawSignageHeader(doc, 'PB Chai Cafe', 'Chaha. Goshti. Maharashtrian Comfort.');
  }
  return cursor;
}

function drawFooter(doc) {
  setText(doc, COLOR.bodyDim);
  doc.setFont('times', 'italic');
  doc.setFontSize(8);
  doc.text(
    'PB Chai Cafe - a Purnabramha franchise.  www.purnabramha.com',
    PAGE_W / 2,
    PAGE_H - 7,
    { align: 'center' }
  );
}

function drawSectionTitle(doc, y, title) {
  setText(doc, COLOR.gold);
  doc.setFont('times', 'normal');
  doc.setFontSize(14);
  doc.text(title.toUpperCase(), M, y);
  setDraw(doc, COLOR.gold);
  doc.setLineWidth(0.3);
  doc.line(M, y + 1.5, M + 60, y + 1.5);
  return y + 8;
}

function drawKV(doc, y, label, value) {
  setText(doc, COLOR.body);
  doc.setFont('times', 'normal');
  doc.setFontSize(10.5);
  doc.text(label, M + 2, y);
  setText(doc, COLOR.cream);
  doc.setFont('times', 'bold');
  doc.text(String(value || '-'), PAGE_W - M - 2, y, { align: 'right' });
  setDraw(doc, [50, 36, 18]);
  doc.setLineWidth(0.1);
  doc.line(M, y + 1.6, PAGE_W - M, y + 1.6);
  return y + 6;
}

function drawParagraph(doc, y, text, opts = {}) {
  const { color = COLOR.body, size = 10, italic = false } = opts;
  setText(doc, color);
  doc.setFont('times', italic ? 'italic' : 'normal');
  doc.setFontSize(size);
  const lines = doc.splitTextToSize(text, PAGE_W - 2 * M);
  doc.text(lines, M, y);
  return y + lines.length * (size * 0.42);
}

function drawBullets(doc, y, items, opts = {}) {
  const { color = COLOR.body, size = 10.5 } = opts;
  setText(doc, color);
  doc.setFont('times', 'normal');
  doc.setFontSize(size);
  items.forEach((it) => {
    const lines = doc.splitTextToSize('•  ' + it, PAGE_W - 2 * M - 4);
    doc.text(lines, M + 2, y);
    y += lines.length * (size * 0.42) + 1.5;
  });
  return y + 1;
}

export async function downloadFranchisePDF(cfg = {}) {
  const doc = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait' });

  // ── Page 1 — Cover / Vision / Promise ──
  paintBackground(doc);
  let y = drawSignageHeader(doc, 'PB Chai Cafe', 'Chaha. Goshti. Maharashtrian Comfort.');

  // Quote band
  setFill(doc, COLOR.panel);
  doc.roundedRect(M, y, PAGE_W - 2 * M, 22, 1.5, 1.5, 'F');
  setText(doc, COLOR.cream);
  doc.setFont('times', 'italic');
  doc.setFontSize(11);
  doc.text(
    '"Our cricket stands on the world stage. Our Maharashtrian food deserves to stand there too."',
    PAGE_W / 2, y + 9, { align: 'center', maxWidth: PAGE_W - 2 * M - 8 }
  );
  setText(doc, COLOR.gold);
  doc.setFont('times', 'normal');
  doc.setFontSize(9);
  doc.text('- Jayanti Kathale, Founder, Purnabramha', PAGE_W / 2, y + 17, { align: 'center' });
  y += 28;

  // Vision / Promise / Tagline / USPs
  y = drawSectionTitle(doc, y, 'Our Vision');
  y = drawParagraph(doc,
    y,
    "To become India's most loved Maharashtrian tea café brand, bringing everyday comfort food to every workspace and community."
  ) + 4;

  y = drawSectionTitle(doc, y, 'Our Promise');
  y = drawParagraph(doc, y,
    'Authentic Maharashtrian recipes, premium ingredients, consistent taste and a warm homely experience.'
  ) + 4;

  y = drawSectionTitle(doc, y, 'Our USP');
  y = drawBullets(doc, y, [
    '100% Maharashtrian flavours',
    'Premium quality ingredients',
    'Quick service · small footprint',
    'High repeat customers',
    'Low operational complexity',
  ]) + 2;

  // ── Hero Menu (admin-configurable items) ──
  const menu = (cfg.menu_items || []).filter(m => m.active !== false);
  if (menu.length) {
    y = ensureSpace(doc, y, 30);
    y = drawSectionTitle(doc, y, 'Hero Menu');
    menu.slice(0, 10).forEach(m => {
      y = ensureSpace(doc, y, 7);
      y = drawKV(doc, y, `${m.name}${m.category ? '  ·  ' + m.category : ''}`, fmtINR(m.price));
    });
    y += 4;
  }

  // ── Investment Breakdown ──
  y = ensureSpace(doc, y, 50);
  y = drawSectionTitle(doc, y, 'Franchise Investment');
  y = drawKV(doc, y, 'Franchise Fee (One Time)', fmtINR(cfg.franchise_fee_inr));
  y = drawKV(doc, y, `Security Deposit${cfg.deposit_refundable ? ' (Refundable)' : ''}`, fmtINR(cfg.security_deposit_inr));
  const feeTotal = (cfg.franchise_fee_inr || 0) + (cfg.security_deposit_inr || 0);
  y = drawKV(doc, y, 'TOTAL FRANCHISE OUTLAY', fmtINR(feeTotal));
  if (cfg.deposit_note) {
    y = drawParagraph(doc, y + 1, cfg.deposit_note, { italic: true, color: COLOR.bodyDim, size: 9 }) + 2;
  }

  // Setup heads
  const heads = cfg.setup_heads || [];
  if (heads.length) {
    y = ensureSpace(doc, y + 2, 10 + heads.length * 6);
    y = drawSectionTitle(doc, y + 2, 'Approximate Setup Cost');
    let setupTotal = 0;
    heads.forEach(h => {
      setupTotal += h.amount || 0;
      y = drawKV(doc, y, h.label || '-', fmtINR(h.amount));
    });
    y = drawKV(doc, y, 'TOTAL SETUP', fmtINR(setupTotal));
  }

  // ── Royalty + Marketing ──
  y = ensureSpace(doc, y + 4, 26);
  y = drawSectionTitle(doc, y, 'Royalty & Marketing');
  y = drawKV(doc, y, `Monthly Royalty${cfg.royalty_gst_applicable ? ' (excl. GST)' : ''}`, `${cfg.royalty_pct || 0}% of Gross Sales`);
  y = drawKV(doc, y, 'Marketing Fund', `${cfg.marketing_pct || 0}% of Gross Sales`);

  // ── Projections ──
  const p = cfg.projections || {};
  y = ensureSpace(doc, y + 4, 40);
  y = drawSectionTitle(doc, y, 'Financial Projections (Average)');
  y = drawKV(doc, y, 'Average Monthly Sale', fmtINR(p.avg_monthly_sale));
  y = drawKV(doc, y, `Average Gross Profit${p.gross_margin_pct ? ' (~' + p.gross_margin_pct + '%)' : ''}`, fmtINR(p.avg_gross_profit));
  y = drawKV(doc, y, 'Average Net Profit', `${fmtINR(p.net_profit_min)} - ${fmtINR(p.net_profit_max)}`);
  y = drawKV(doc, y, 'Break-even', `${p.breakeven_months || '-'} months`);
  y = drawKV(doc, y, 'Expected ROI', `${p.roi_months || '-'} months`);

  // ── Ideal Locations ──
  const locs = cfg.ideal_locations || [];
  if (locs.length) {
    y = ensureSpace(doc, y + 4, 14 + locs.length * 5);
    y = drawSectionTitle(doc, y, 'Ideal Locations');
    y = drawBullets(doc, y, locs, { size: 10 });
  }

  // ── Franchise Journey ──
  const journey = [
    'Submit Application',
    'Discussion & Evaluation',
    'Site Approval',
    'Franchise Fee Payment',
    'Agreement Generation',
    'Setup & Training',
    'Grand Launch',
    'Ongoing Support',
  ];
  y = ensureSpace(doc, y + 4, 14 + journey.length * 5);
  y = drawSectionTitle(doc, y, 'Franchise Journey');
  y = drawBullets(doc, y, journey.map((s, i) => `Step ${i + 1}. ${s}`), { size: 10 });

  // ── Contact ──
  const f = cfg.footer || {};
  if (f.phone || f.email || f.website) {
    y = ensureSpace(doc, y + 4, 26);
    y = drawSectionTitle(doc, y, 'Ready to Partner?');
    if (f.phone)   y = drawKV(doc, y, 'Phone',   f.phone);
    if (f.email)   y = drawKV(doc, y, 'Email',   f.email);
    if (f.website) y = drawKV(doc, y, 'Website', f.website);
  }

  // ── RISK DISCLOSURE — always on a fresh page so it stands out ──
  drawFooter(doc);
  doc.addPage();
  paintBackground(doc);
  y = drawSignageHeader(doc, 'Risk Disclosure', 'Please read carefully before applying');

  // Warning band
  setFill(doc, [60, 18, 14]);
  doc.roundedRect(M, y, PAGE_W - 2 * M, 14, 1.5, 1.5, 'F');
  setText(doc, [255, 220, 200]);
  doc.setFont('times', 'bold');
  doc.setFontSize(11);
  doc.text('IMPORTANT: This is a business investment. Please consider the risks.', PAGE_W / 2, y + 9, { align: 'center' });
  y += 20;

  const RISKS = [
    'All financial projections (average monthly sale, gross profit, net profit, break-even and ROI) are INDICATIVE estimates based on mature kiosks operating in favourable locations. They are NOT a guarantee of future performance for your specific franchise.',
    'Actual revenue depends on location footfall, local competition, weather, festivals, lease terms, manpower retention, operational discipline and a number of external factors that are outside Purnabramha\'s control.',
    'The franchise fee and security deposit components are payable as per the Franchise Agreement. Refund of the security deposit (where marked refundable) is subject to terms of the Agreement including notice period, dues clearance and asset hand-back conditions.',
    'Royalty (% of Gross Sales) and Marketing Fund contributions are payable from day one of operations regardless of profitability.',
    'Setup costs (interiors, equipment, branding, initial stock, working capital) are approximate and may vary by city, vendor availability and site condition. Working capital must be planned for a minimum of 3-6 months of operations.',
    'Statutory licences, GST registration, FSSAI, shop & establishment, fire/health NOC and any other location-specific permits are the responsibility of the franchise partner.',
    'Recipes, brand assets, SOPs and trade-secret know-how shared during onboarding are confidential. Any violation may lead to immediate termination of the franchise without refund.',
    'Past performance of any existing Purnabramha or PB Chai Café outlet does not assure similar results for a new franchise. Applicants are strongly advised to do their own due diligence and consult independent legal, tax and financial advisors before signing the Franchise Agreement.',
    'Force majeure events (pandemic, civic disruption, regulatory change, supply-chain disruption) can materially impact revenue and timelines. Such events are governed by the Franchise Agreement.',
    'This brochure is for informational purposes only and does not constitute a legally binding offer. The final terms are governed solely by the executed Franchise Agreement.',
  ];

  setText(doc, COLOR.body);
  doc.setFont('times', 'normal');
  doc.setFontSize(10);
  RISKS.forEach((r, i) => {
    y = ensureSpace(doc, y, 16);
    const tag = `${i + 1}.`;
    setText(doc, COLOR.gold);
    doc.setFont('times', 'bold');
    doc.text(tag, M, y);
    setText(doc, COLOR.body);
    doc.setFont('times', 'normal');
    const lines = doc.splitTextToSize(r, PAGE_W - 2 * M - 8);
    doc.text(lines, M + 8, y);
    y += lines.length * 4.4 + 2.5;
  });

  // Acknowledgement
  y = ensureSpace(doc, y + 2, 30);
  setFill(doc, COLOR.panel);
  doc.roundedRect(M, y, PAGE_W - 2 * M, 24, 1.5, 1.5, 'F');
  setText(doc, COLOR.cream);
  doc.setFont('times', 'italic');
  doc.setFontSize(10);
  doc.text(
    'By submitting the Franchise Application form, the applicant acknowledges having read and understood this Risk Disclosure, agrees that all projections are indicative, and confirms that the decision to apply is taken voluntarily after independent evaluation.',
    M + 4, y + 7, { maxWidth: PAGE_W - 2 * M - 8 }
  );
  drawFooter(doc);

  // Save with date stamp
  const date = new Date().toISOString().slice(0, 10);
  doc.save(`PB-Chai-Cafe-Franchise-Brochure-${date}.pdf`);
}
