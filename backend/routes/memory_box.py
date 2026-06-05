"""Digital Memory Box Generator — Center Manager 4th tab.

Generates a personalised 7-page PDF memory book for a guest after an event,
catering, pickup, dine-in, or tiffin journey. Uses GPT-5.2 (Emergent LLM key)
for the event story + occasion-specific gratitude + blessings, ReportLab for
the layout, and the existing SMTP / WhatsApp plumbing for delivery.
"""
import base64
import io
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server import db                                       # type: ignore
from routes.center_accounts import check_access

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memory-box", tags=["memory-box"])

LOGO_PATH = "/app/backend/static/purnabramha_logo.png"
ASSET_DIR = "/app/backend/static/memory_boxes"
os.makedirs(ASSET_DIR, exist_ok=True)

OCCASIONS = [
    "Birthday", "Anniversary", "Catering Event", "Corporate Event",
    "Baby Shower", "Dohal Jevan", "Upanayan", "Naming Ceremony",
    "Retirement Function", "Family Gathering", "Dine-In Celebration",
    "Pickup Order", "Tiffin Customer", "Festival Order", "Other",
]
EMOTIONS = ["Joy", "Gratitude", "Family", "Friendship", "Tradition",
            "Celebration", "Achievement", "Blessings", "Togetherness", "Love"]


def _can_create(session: dict) -> bool:
    if session.get("is_super_admin") or session.get("is_admin"):
        return True
    role_key = (session.get("role_key") or "").lower()
    roles = session.get("roles") or {}
    if role_key in {"center_manager", "manager", "operations", "accountant", "admin"}:
        return True
    return bool(roles.get("operations") or roles.get("ops") or roles.get("manager")
                or roles.get("center_manager"))


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
class TeamMember(BaseModel):
    name: str
    role: str = "Service Associate"


class MemoryBoxRequest(BaseModel):
    token: str
    center: str
    # Step 1 — Guest
    guest_name: str
    mobile: str
    email: Optional[str] = ""
    event_date: str            # YYYY-MM-DD
    order_number: Optional[str] = ""
    # Step 2 — Occasion
    occasion: str
    occasion_other: Optional[str] = ""
    # Step 3 — Memory questions
    celebration_for: Optional[str] = ""          # "Father's 60th Birthday"
    special_moment: Optional[str] = ""
    organised_by: Optional[str] = ""
    host_message: Optional[str] = ""
    thank_family: Optional[str] = ""
    mention_guests: Optional[str] = ""
    emotion: str = "Joy"
    # Step 4 — Photos (data URLs / base64)
    photos: List[str] = []
    team_photo: Optional[str] = ""
    # Step 5 — Team
    team: List[TeamMember] = []
    # NEW (Feb 2026) — per-center branding embed
    instagram_url: Optional[str] = ""
    phone: Optional[str] = ""
    show_qr: bool = True
    # NEW (Feb 2026) — Memory Box personalisation
    language: str = "Bilingual"     # English | Marathi | Bilingual
    font_size: str = "M"             # S | M | L
    generate_summary_image: bool = True   # also return a 1-page shareable PNG
    # NEW (Feb 2026) — Animated Memory Box
    generate_video: bool = False     # produce shareable MP4 (30-45s)
    generate_web: bool = False       # produce shareable HTML web link
    delivery_mode: str = "function"  # "function" (hosted) or "home" (delivery)
    website: Optional[str] = ""      # center website (for QR fallback)
    music: bool = True               # add gentle tanpura drone to the MP4


class BaseReq(BaseModel):
    token: str


class ListReq(BaseReq):
    center: Optional[str] = None
    limit: int = 50


class RosterReq(BaseReq):
    center: str
    event_date: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _strip_data_url(b64: str) -> bytes:
    if not b64:
        return b""
    if "," in b64 and b64.startswith("data:"):
        b64 = b64.split(",", 1)[1]
    try:
        return base64.b64decode(b64)
    except Exception:
        return b""


def _initial_avatar_flowable(name: str, gold, chocolate, cream, size_in: float = 1.0):
    """Render a circular gold-on-chocolate medallion with the member's initials.

    Returns a ReportLab Flowable (a tiny Drawing).
    """
    from reportlab.graphics.shapes import Drawing, Circle, String
    from reportlab.lib.units import inch
    parts = [p for p in (name or "?").strip().split() if p]
    initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper() if parts else "?"
    size_pts = size_in * inch
    d = Drawing(size_pts, size_pts)
    r = size_pts / 2
    # Gold ring
    d.add(Circle(r, r, r, fillColor=gold, strokeColor=gold))
    # Chocolate disc
    d.add(Circle(r, r, r * 0.88, fillColor=chocolate, strokeColor=chocolate))
    # Initials in cream
    s = String(r, r - size_pts * 0.13, initials,
               fontName="Times-Bold", fontSize=size_pts * 0.40,
               fillColor=cream, textAnchor="middle")
    d.add(s)
    return d


def _render_artistic_collage(photos, *, w_in=6.4, h_in=7.4, dpi=200,
                              gold=(220, 175, 80), cream=(250, 240, 220),
                              chocolate=(43, 24, 16),
                              seed: int | None = None):
    """Render ONE artistic photo-collage page as a Pillow PNG image.

    Picks one of 4 creative templates based on photo count + seed:
      1. POLAROID SCATTER — rotated cards with tape strips on a cream paper
      2. MAGAZINE MOSAIC  — 1 hero + asymmetric tiles + paisley border
      3. FILMSTRIP        — vertical filmstrip + wide hero banner
      4. HEART / MANDALA  — centered hero + radial mini circles

    Returns: bytes (PNG)  or  None if there are no photos.
    """
    if not photos:
        return None
    import io as _io
    from PIL import Image as _PIL, ImageDraw as _ID, ImageFilter as _IF
    import random as _rnd
    import math as _m

    W = int(w_in * dpi)
    H = int(h_in * dpi)
    rng = _rnd.Random(seed if seed is not None else _rnd.randint(0, 10**9))

    # Cream paper texture
    canvas = _PIL.new("RGBA", (W, H), (*cream, 255))
    paper = _ID.Draw(canvas)
    # Faint paisley dots (low-alpha)
    for _ in range(W * H // 7000):
        x = rng.randint(0, W)
        y = rng.randint(0, H)
        r = rng.randint(3, 8)
        paper.ellipse([x - r, y - r, x + r, y + r],
                      fill=(*gold, rng.randint(8, 25)))

    # Decode photos into PIL Images (cap to 7 for collage density)
    pil_photos = []
    for p in photos[:7]:
        try:
            raw = p if isinstance(p, bytes) else _strip_data_url(p)
            if not raw:
                continue
            im = _PIL.open(_io.BytesIO(raw)).convert("RGBA")
            pil_photos.append(im)
        except Exception:
            continue
    if not pil_photos:
        return None

    def _frame(img, w, h, *, rotate=0, polaroid=False, tape=False, gold_ring=False):
        """Cover-fit + frame an image, return RGBA tile."""
        gw, gh = img.size
        scale = max(w / gw, h / gh)
        nw, nh = int(gw * scale), int(gh * scale)
        scaled = img.resize((nw, nh), _PIL.LANCZOS)
        left = (nw - w) // 2
        top = (nh - h) // 2
        cropped = scaled.crop((left, top, left + w, top + h))
        # Build the tile
        if polaroid:
            pad = max(12, int(min(w, h) * 0.06))
            pad_b = max(28, int(min(w, h) * 0.18))
            tile_w = w + 2 * pad
            tile_h = h + pad + pad_b
            tile = _PIL.new("RGBA", (tile_w, tile_h), (255, 252, 244, 255))
            tile.paste(cropped, (pad, pad))
            # subtle inner shadow line
            td = _ID.Draw(tile)
            td.rectangle([pad - 1, pad - 1, pad + w, pad + h], outline=(150, 130, 90, 90), width=1)
        else:
            border = 6
            tile = _PIL.new("RGBA", (w + border * 2, h + border * 2), (252, 244, 220, 255))
            tile.paste(cropped, (border, border))
            td = _ID.Draw(tile)
            td.rounded_rectangle(
                [border - 2, border - 2, border + w + 2, border + h + 2],
                radius=8, outline=(*gold, 255) if gold_ring else (200, 170, 100, 200),
                width=3 if gold_ring else 2,
            )
        if rotate:
            tile = tile.rotate(rotate, expand=True, resample=_PIL.BICUBIC)
        # Drop shadow
        sh = _PIL.new("RGBA", (tile.width + 30, tile.height + 30), (0, 0, 0, 0))
        sd = _ID.Draw(sh)
        sd.rectangle([15, 15, tile.width + 15, tile.height + 15], fill=(0, 0, 0, 90))
        try:
            sh = sh.filter(_IF.GaussianBlur(radius=8))
        except Exception:
            pass
        wrapper = _PIL.new("RGBA", (tile.width + 30, tile.height + 30), (0, 0, 0, 0))
        wrapper.paste(sh, (0, 0), sh)
        wrapper.paste(tile, (15, 15), tile)
        # Optional masking tape
        if tape:
            tape_w = int(tile.width * 0.30)
            tape_h = max(18, int(tile.height * 0.05))
            t = _PIL.new("RGBA", (tape_w, tape_h), (240, 215, 130, 180))
            t = t.rotate(rng.randint(-12, 12), expand=True, resample=_PIL.BICUBIC)
            tx = (wrapper.width - t.width) // 2
            ty = max(0, 15 - t.height // 2)
            wrapper.paste(t, (tx, ty), t)
        return wrapper

    template = rng.choice(["polaroid_scatter", "magazine_mosaic", "filmstrip", "mandala"])
    if len(pil_photos) == 1:
        template = "magazine_mosaic"

    if template == "polaroid_scatter":
        # 4-6 polaroids scattered, randomly rotated
        slots = [
            (int(W * 0.10), int(H * 0.06), 0.36, 0.30, -7),
            (int(W * 0.55), int(H * 0.08), 0.38, 0.32, 6),
            (int(W * 0.05), int(H * 0.42), 0.34, 0.30, 9),
            (int(W * 0.52), int(H * 0.40), 0.40, 0.34, -5),
            (int(W * 0.20), int(H * 0.68), 0.34, 0.28, -3),
            (int(W * 0.58), int(H * 0.72), 0.36, 0.26, 8),
        ]
        for i, (sx, sy, sw, sh, rot) in enumerate(slots):
            if i >= len(pil_photos):
                break
            tw = int(W * sw)
            th = int(H * sh)
            tile = _frame(pil_photos[i], tw, th, polaroid=True, tape=True,
                          rotate=rot + rng.randint(-3, 3))
            canvas.paste(tile, (sx - 15, sy - 15), tile)

    elif template == "magazine_mosaic":
        # 1 hero + asymmetric mosaic
        m = int(W * 0.04)
        if len(pil_photos) == 1:
            hero_w = W - 2 * m
            hero_h = int(H * 0.75)
            tile = _frame(pil_photos[0], hero_w, hero_h, gold_ring=True)
            canvas.paste(tile, (m - 15, int(H * 0.10) - 15), tile)
        else:
            hero_w = int(W * 0.62)
            hero_h = int(H * 0.46)
            tile = _frame(pil_photos[0], hero_w, hero_h, gold_ring=True)
            canvas.paste(tile, (m - 15, m - 15), tile)
            # Right column: 2 small tiles
            rx = int(W * 0.68)
            ry = m
            small_w = int(W * 0.28)
            small_h = int(H * 0.22)
            for i, p in enumerate(pil_photos[1:3], 1):
                t = _frame(p, small_w, small_h)
                canvas.paste(t, (rx - 15, ry - 15), t)
                ry += small_h + 20
            # Bottom row: 3 wide tiles
            bx = m
            by = m + hero_h + 30
            wide_w = int((W - 2 * m - 40) / 3)
            wide_h = int(H * 0.30)
            for i, p in enumerate(pil_photos[3:6], 0):
                t = _frame(p, wide_w, wide_h)
                canvas.paste(t, (bx + i * (wide_w + 20) - 15, by - 15), t)

    elif template == "filmstrip":
        # Wide hero banner on top + horizontal filmstrip below
        m = int(W * 0.05)
        hero_w = W - 2 * m
        hero_h = int(H * 0.42)
        tile = _frame(pil_photos[0], hero_w, hero_h, gold_ring=True)
        canvas.paste(tile, (m - 15, m - 15), tile)
        # Black filmstrip background with perforations
        strip_y = m + hero_h + 30
        strip_h = int(H * 0.42)
        strip = _PIL.new("RGBA", (W - 2 * m, strip_h), (chocolate[0], chocolate[1], chocolate[2], 255))
        sd2 = _ID.Draw(strip)
        # Perforations
        peri_r = 6
        peri_gap = 22
        for x in range(peri_gap, strip.width - peri_gap, peri_gap):
            sd2.ellipse([x - peri_r, 10, x + peri_r, 10 + 2 * peri_r], fill=cream)
            sd2.ellipse([x - peri_r, strip_h - 10 - 2 * peri_r, x + peri_r, strip_h - 10], fill=cream)
        canvas.paste(strip, (m, strip_y), strip)
        # Fit up to 4 tiles inside filmstrip
        inner = pil_photos[1:5]
        if inner:
            slot_w = (W - 2 * m - 80) // len(inner)
            slot_h = strip_h - 60
            for i, p in enumerate(inner):
                t = _frame(p, slot_w, slot_h)
                canvas.paste(
                    t,
                    (m + 40 + i * slot_w - 15, strip_y + 30 - 15),
                    t,
                )

    else:  # mandala
        # Center hero (circular) + 4-6 mini circles around it
        cx, cy = W // 2, H // 2
        hero_d = int(min(W, H) * 0.45)
        # Mask hero to a circle
        hero_img = pil_photos[0]
        gw, gh = hero_img.size
        s = max(hero_d / gw, hero_d / gh)
        nw, nh = int(gw * s), int(gh * s)
        resized = hero_img.resize((nw, nh), _PIL.LANCZOS)
        lft = (nw - hero_d) // 2
        tp = (nh - hero_d) // 2
        sq = resized.crop((lft, tp, lft + hero_d, tp + hero_d))
        m = _PIL.new("L", (hero_d, hero_d), 0)
        _ID.Draw(m).ellipse([0, 0, hero_d, hero_d], fill=255)
        # gold ring
        ring = _PIL.new("RGBA", (hero_d + 30, hero_d + 30), (0, 0, 0, 0))
        rd = _ID.Draw(ring)
        rd.ellipse([0, 0, hero_d + 30, hero_d + 30], fill=(*gold, 255))
        rd.ellipse([15, 15, hero_d + 15, hero_d + 15], fill=(0, 0, 0, 0))
        canvas.paste(ring, (cx - (hero_d + 30) // 2, cy - (hero_d + 30) // 2), ring)
        canvas.paste(sq, (cx - hero_d // 2, cy - hero_d // 2), m)
        # Surrounding mini circles
        radii_d = int(min(W, H) * 0.16)
        for i, p in enumerate(pil_photos[1:7], 0):
            angle = (_m.pi * 2) * i / max(6, len(pil_photos) - 1) - _m.pi / 2
            r = int(min(W, H) * 0.36)
            mx = cx + int(_m.cos(angle) * r) - radii_d // 2
            my = cy + int(_m.sin(angle) * r) - radii_d // 2
            gw, gh = p.size
            s = max(radii_d / gw, radii_d / gh)
            nw, nh = int(gw * s), int(gh * s)
            resized = p.resize((nw, nh), _PIL.LANCZOS)
            lft = (nw - radii_d) // 2
            tp = (nh - radii_d) // 2
            sq = resized.crop((lft, tp, lft + radii_d, tp + radii_d))
            m2 = _PIL.new("L", (radii_d, radii_d), 0)
            _ID.Draw(m2).ellipse([0, 0, radii_d, radii_d], fill=255)
            ring2 = _PIL.new("RGBA", (radii_d + 16, radii_d + 16), (0, 0, 0, 0))
            rd2 = _ID.Draw(ring2)
            rd2.ellipse([0, 0, radii_d + 16, radii_d + 16], fill=(*gold, 240))
            rd2.ellipse([8, 8, radii_d + 8, radii_d + 8], fill=(0, 0, 0, 0))
            canvas.paste(ring2, (mx - 8, my - 8), ring2)
            canvas.paste(sq, (mx, my), m2)

    # Decorative outer border (thin gold double-line)
    db = _ID.Draw(canvas)
    db.rectangle([8, 8, W - 8, H - 8], outline=(*gold, 220), width=3)
    db.rectangle([18, 18, W - 18, H - 18], outline=(*gold, 120), width=1)

    out = _io.BytesIO()
    canvas.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


def _build_scrapbook_pages(photos, img_fn, gold, gold_bright):
    """Compose photos onto a SINGLE artistic collage page.

    Replaces the old hero+grid layout with a true Pillow-rendered creative
    template (polaroid scatter / magazine mosaic / filmstrip / mandala). All
    photos fit on ONE page — no overflow grid.
    """
    from reportlab.platypus import Spacer
    from reportlab.lib.units import inch
    from reportlab.platypus import Image as RLImage
    import tempfile as _tempfile

    flowables = []
    if not photos:
        return flowables
    # Render the artistic collage (6.4"x7.4" @ 200 dpi)
    collage_bytes = _render_artistic_collage(
        photos, w_in=6.4, h_in=7.4, dpi=200,
    )
    if not collage_bytes:
        return flowables
    # Persist to a temp file so ReportLab can stream it
    tf = _tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tf.write(collage_bytes)
    tf.close()
    try:
        rl_img = RLImage(tf.name, width=6.4 * inch, height=7.4 * inch)
        flowables.append(rl_img)
        flowables.append(Spacer(1, 0.10 * inch))
    finally:
        # ReportLab reads the path lazily during build, so DON'T delete yet
        pass
    return flowables




async def _gpt_story(req: MemoryBoxRequest, center_name: str) -> dict:
    """Generate Event Story + Gratitude + Blessings via GPT-5.2.
    Returns dict with keys: story, gratitude, blessing, future_invitation.
    Falls back to deterministic templates if the LLM call fails.
    """
    occ = req.occasion if req.occasion != "Other" else (req.occasion_other or "Celebration")
    answers = {
        "Guest": req.guest_name,
        "Date": req.event_date,
        "Center": center_name,
        "Occasion": occ,
        "Celebration for": req.celebration_for,
        "Special moment": req.special_moment,
        "Organised by": req.organised_by,
        "Host message": req.host_message,
        "Family thanked": req.thank_family,
        "Guests mentioned": req.mention_guests,
        "Emotion": req.emotion,
    }
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY not set")
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        # Gold-standard blessing examples by occasion (user-approved Marathi).
        # We include 2-3 anchor templates per occasion so GPT mimics this exact
        # cadence and never invents broken Devanagari.
        BLESSING_EXAMPLES = {
            "Birthday": (
                "श्री स्वामी समर्थ.\n"
                "आयुष्य दीर्घ असो, आरोग्य उत्तम लाभो, सुख-समृद्धी नित्य वाढो.\n"
                "कुटुंबात प्रेम, ऐक्य आणि आनंद सदैव नांदो."
            ),
            "Anniversary": (
                "श्री स्वामी समर्थ.\n"
                "तुमचे सहजीवन प्रेम, विश्वास आणि आनंदाने बहरलेले राहो.\n"
                "एकमेकांची साथ, समजूत आणि आदर सदैव वाढत जावो."
            ),
            "Wedding": (
                "श्री स्वामी समर्थ.\n"
                "नवदाम्पत्याचे सहजीवन सुख, समाधान आणि स्नेहाने भरलेले राहो.\n"
                "दोन्ही घराण्यांना आशीर्वाद आणि एकोपा सदैव लाभो."
            ),
            "Naming": (
                "श्री स्वामी समर्थ.\n"
                "नवजात बाळास उत्तम आरोग्य, तेजस्वी बुद्धी आणि दीर्घायुष्य लाभो.\n"
                "आई-वडिलांच्या प्रेमळ छत्रछायेखाली बाळ आनंदाने वाढो."
            ),
            "Housewarming": (
                "श्री स्वामी समर्थ.\n"
                "नवीन घरात लक्ष्मीचे पाऊल पडो, सुख-समाधान सदैव नांदो.\n"
                "कुटुंबात प्रेम, ऐक्य आणि भरभराट कायम राहो."
            ),
            "default": (
                "श्री स्वामी समर्थ.\n"
                "आयुष्य दीर्घ असो, आरोग्य उत्तम लाभो, सुख-समृद्धी नित्य वाढो.\n"
                "कुटुंबात प्रेम, ऐक्य आणि आनंद सदैव नांदो."
            ),
        }
        anchor_blessing = BLESSING_EXAMPLES.get(occ, BLESSING_EXAMPLES["default"])
        # ── Language rules ───────────────────────────────────────────────
        lang = (getattr(req, "language", "Bilingual") or "Bilingual").strip()
        if lang.lower() in ("marathi", "मराठी"):
            lang_rules = (
                "LANGUAGE: All four sections (story, gratitude, blessing, "
                "future_invitation) MUST be written in PROPER MARATHI (Devanagari script). "
                "Use the same spelling-accuracy rules described below. "
                "Keep the cultural anchor 'श्री स्वामी समर्थ' on the blessing.\n"
            )
            lang_keys_note = (
                '"story" (Marathi), "gratitude" (Marathi), '
                '"blessing" (Marathi anchor style), "future_invitation" (Marathi)'
            )
        elif lang.lower() == "english":
            lang_rules = (
                "LANGUAGE: story / gratitude / future_invitation in ENGLISH. "
                "blessing — keep 1 short transliterated English line (e.g. "
                "'With Lord Swami Samarth's grace, may your life be long, healthy "
                "and joyful.'). DO NOT include Devanagari script for English mode.\n"
            )
            lang_keys_note = '"story" (English), "gratitude" (English), "blessing" (English transliteration), "future_invitation" (English)'
        else:
            lang_rules = (
                "LANGUAGE: Bilingual. story / gratitude / future_invitation in ENGLISH. "
                "blessing in PROPER MARATHI per rules below. Default mode.\n"
            )
            lang_keys_note = '"story" (English), "gratitude" (English), "blessing" (Marathi), "future_invitation" (English)'

        prompt = (
            "You are composing 4-section memory book copy for a Purnabramha "
            "(authentic Maharashtrian restaurant) guest. Tone: warm, sincere, "
            "dignified, slightly poetic — never salesy, never generic. 2-3 short "
            "paragraphs max per section.\n\n"
            + lang_rules + "\n"
            "Guest details:\n"
            + "\n".join(f"  {k}: {v}" for k, v in answers.items() if v) + "\n\n"
            "⚠️ MARATHI ACCURACY — CRITICAL ⚠️\n"
            "Whenever Marathi is used, it MUST be written in PERFECT, CULTURALLY-CORRECT Marathi.\n"
            "Rules:\n"
            "  1. Start the blessing with the traditional invocation \"श्री स्वामी समर्थ.\" on its own line.\n"
            "  2. Use ONLY proper Devanagari spelling. NEVER misspell common words:\n"
            "     • वाढदिवस  (NOT वाढदविस / वाढदविसाच्या)\n"
            "     • हार्दिक   (NOT हार्दकि)\n"
            "     • आशीर्वाद   (NOT आर्शीवाद)\n"
            "     • वर्धापनदिन (NOT वर्धापनदनि)\n"
            "  3. Use traditional, respectful blessing phrases — e.g.\n"
            "     'आयुष्य दीर्घ असो', 'आरोग्य उत्तम लाभो', 'सुख-समृद्धी नित्य वाढो',\n"
            "     'कुटुंबात प्रेम, ऐक्य आणि आनंद सदैव नांदो'.\n"
            "  4. Keep blessing to EXACTLY 3 short lines (one sentence per line).\n"
            "  5. Match the cadence and tone of this anchor example for the occasion '" + occ + "':\n"
            "     ───────────────────────────────\n     " + anchor_blessing.replace("\n", "\n     ") + "\n"
            "     ───────────────────────────────\n"
            "  6. You MAY personalise gently (use the guest's first name OR keep generic).\n\n"
            "Return STRICT JSON with these four keys (no markdown, no commentary):\n"
            "{\n"
            f'  "story": "warm 2-paragraph story – {lang_keys_note}",\n'
            '  "gratitude":  "1 short paragraph thank-you",\n'
            '  "blessing":   "3 lines per language rules above",\n'
            '  "future_invitation": "1 short warm line inviting back — NOT discount based."\n'
            "}"
        )
        chat = (LlmChat(api_key=api_key, session_id=f"mbox-{uuid.uuid4().hex[:8]}",
                       system_message=(
                           "You write warm, dignified memory-book copy for Indian "
                           "family celebrations. You are NATIVE-FLUENT in Marathi "
                           "and never produce a misspelled Devanagari word."))
                .with_model("openai", "gpt-5.2"))
        resp = await chat.send_message(UserMessage(text=prompt))
        import json
        import re
        cleaned = re.sub(r"^```json\s*|\s*```$", "", resp.strip(), flags=re.MULTILINE)
        data = json.loads(cleaned)
        # Sanity defaults
        for k in ("story", "gratitude", "blessing", "future_invitation"):
            data.setdefault(k, "")
        # ── Safety net: if the model emitted a known misspelling, replace
        # with the anchor blessing for this occasion. SKIP for English mode
        # because the anchor is in Devanagari.
        TYPO_FLAGS = ("वाढदविस", "हार्दकि", "वर्धापनदनि", "आर्शीवाद", "आर्शिवाद")
        b = (data.get("blessing") or "")
        if lang.lower() != "english":
            if not b.strip() or any(t in b for t in TYPO_FLAGS):
                data["blessing"] = anchor_blessing
        return data
    except Exception as e:
        logger.warning(f"Memory box GPT generation fell back: {e}")
        # Deterministic fallback so the feature still works without LLM.
        fallback_blessing = (
            "श्री स्वामी समर्थ.\n"
            "आयुष्य दीर्घ असो, आरोग्य उत्तम लाभो, सुख-समृद्धी नित्य वाढो.\n"
            "कुटुंबात प्रेम, ऐक्य आणि आनंद सदैव नांदो."
        )
        # Deterministic fallback so the feature still works without LLM.
        return {
            "story": (
                f"On {req.event_date}, {req.guest_name} chose to celebrate "
                f"{req.celebration_for or occ.lower()} with Purnabramha {center_name}. "
                f"{req.special_moment or 'The day was filled with shared food, laughter and meaningful moments.'} "
                f"{('Hosted with love by ' + req.organised_by + '. ') if req.organised_by else ''}"
                "We are humbled that our kitchen could be a small part of such a beautiful gathering."
            ),
            "gratitude": (
                f"Thank you, {req.guest_name}, for letting Purnabramha share this {occ.lower()} with you. "
                "Every plate we serve carries a wish that your family stays close and your memories stay warm."
            ),
            "blessing": fallback_blessing,
            "future_invitation": "A complimentary glass of fresh taak awaits you on your next visit — our small way of saying thank you.",
        }


def _build_pdf(req: MemoryBoxRequest, center_name: str, llm: dict, box_id: str) -> bytes:
    """7-page premium memory book PDF."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # ── Register Devanagari fonts so Marathi blessing renders correctly ──
    # Prefer bundled fonts (shipped with the repo) over system fonts so the
    # PDF renders correctly even on containers without /usr/share/fonts.
    _BUNDLED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "static", "fonts")
    def _ff(name: str, *fallbacks: str) -> str:
        for p in (os.path.join(_BUNDLED, name), *fallbacks):
            if p and os.path.exists(p):
                return p
        return ""
    DEV_REG_PATH = _ff("NotoSansDevanagari-Regular.ttf",
                       "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf")
    DEV_BOLD_PATH = _ff("NotoSansDevanagari-Bold.ttf",
                        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf")
    DEV_FONT = "Times-Italic"          # safe fallback
    DEV_BOLD_FONT = "Times-Bold"
    try:
        if DEV_REG_PATH:
            pdfmetrics.registerFont(TTFont("NotoDev", DEV_REG_PATH))
            DEV_FONT = "NotoDev"
        if DEV_BOLD_PATH:
            pdfmetrics.registerFont(TTFont("NotoDevBold", DEV_BOLD_PATH))
            DEV_BOLD_FONT = "NotoDevBold"
    except Exception as _e:
        logger.warning(f"Devanagari font registration failed: {_e}")

    occ = req.occasion if req.occasion != "Other" else (req.occasion_other or "Celebration")
    # Purnabramha 2026 brand palette
    GOLD = colors.HexColor("#BF8C32")             # rich antique gold
    GOLD_BRIGHT = colors.HexColor("#DCAE50")
    CREAM = colors.HexColor("#FAF0DC")            # warm cream
    CHOCOLATE = colors.HexColor("#2B1810")        # dark chocolate (primary)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                            title=f"Memory Box — {req.guest_name}")
    ss = getSampleStyleSheet()
    # Font-size scaling driven by req.font_size: S=0.85, M=1.0, L=1.18
    _fs_scale = {"S": 0.85, "M": 1.0, "L": 1.18}.get((req.font_size or "M").upper(), 1.0)
    def _fs(n):  # scaled font size
        return max(8, int(round(n * _fs_scale)))
    # All heading colours upgraded to ANTIQUE GOLD and font sizes increased
    H = ParagraphStyle("H", parent=ss["Heading1"], textColor=GOLD_BRIGHT,
                       alignment=TA_CENTER, fontSize=_fs(40), spaceAfter=18,
                       fontName="Times-Bold", leading=_fs(48))
    H2 = ParagraphStyle("H2", parent=ss["Heading2"], textColor=GOLD_BRIGHT,
                        alignment=TA_CENTER, fontSize=_fs(32), spaceAfter=14,
                        fontName="Times-Bold", leading=_fs(40))
    sub = ParagraphStyle("sub", parent=ss["Normal"], textColor=CREAM,
                         alignment=TA_CENTER, fontSize=_fs(20), fontName="Times-Italic",
                         spaceAfter=12, leading=_fs(26))
    body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=_fs(17), leading=_fs(26),
                          fontName="Times-Roman", textColor=CREAM,
                          spaceAfter=12, alignment=TA_LEFT)
    bodyDark = ParagraphStyle("bodyDark", parent=body, textColor=colors.HexColor("#3a2218"))  # noqa: F841
    centerBody = ParagraphStyle("cb", parent=body, alignment=TA_CENTER, fontSize=_fs(18), leading=_fs(28))
    small = ParagraphStyle("sm", parent=ss["BodyText"], fontSize=_fs(13),
                           textColor=CREAM, alignment=TA_CENTER, leading=_fs(18))

    def _img(b64_or_bytes, w=2.5, h=2.5):
        try:
            data = b64_or_bytes if isinstance(b64_or_bytes, bytes) else _strip_data_url(b64_or_bytes)
            if not data:
                return None
            return Image(io.BytesIO(data), width=w * inch, height=h * inch, kind="proportional")
        except Exception:
            return None

    story = []

    # ─── Page 1: Cover ───
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            logo = _img(f.read(), w=1.8, h=1.8)
            if logo:
                story.append(Spacer(1, 0.3 * inch))
                story.append(logo)
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph("Thank You<br/>For Making Us Part Of<br/>Your Celebration", H))
    story.append(Paragraph(
        "आमच्या सोबत आनंदाचे क्षण साजरे केल्याबद्दल धन्यवाद",
        ParagraphStyle("cover_mr", parent=sub, fontName=DEV_BOLD_FONT,
                       fontSize=18, textColor=GOLD_BRIGHT, leading=24)
    ))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("<i>— for —</i>", sub))
    story.append(Paragraph(f"<b>{req.guest_name}</b>", H2))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(f"{occ}", sub))
    story.append(Paragraph(f"{req.event_date}", sub))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(f"Purnabramha · {center_name}", small))
    # ── Per-center contact line on cover ──
    contact_bits = []
    if (req.phone or "").strip():
        contact_bits.append(req.phone.strip())
    if (req.instagram_url or "").strip():
        ig = req.instagram_url.strip()
        handle = ig.rstrip("/").split("/")[-1]
        if handle and not handle.startswith("@"):
            handle = "@" + handle
        contact_bits.append(handle)
    contact_bits.append("www.purnabramha.com")
    if contact_bits:
        story.append(Spacer(1, 0.05 * inch))
        story.append(Paragraph(
            "  ·  ".join(contact_bits),
            ParagraphStyle("cover_contact", parent=small,
                           fontSize=9, textColor=GOLD_BRIGHT, alignment=1),
        ))
    # ── Small QR badge on cover ──
    QR_PATH = "/app/backend/static/purnabramha_booking_qr.png"
    if req.show_qr and os.path.exists(QR_PATH):
        try:
            from reportlab.platypus import Image as RLImage
            qr_im = RLImage(QR_PATH, width=1.2 * inch, height=1.2 * inch)
            story.append(Spacer(1, 0.20 * inch))
            qr_wrap = Table([[qr_im], [Paragraph(
                "<para align='center'><font color='#DCAE50' size='8'><b>SCAN TO BOOK</b></font></para>",
                small)]],
                colWidths=[1.4 * inch], rowHeights=[1.25 * inch, 0.20 * inch])
            qr_wrap.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), CREAM),
                ("BOX", (0, 0), (-1, -1), 1.5, GOLD_BRIGHT),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(qr_wrap)
        except Exception as _e:
            logger.warning(f"cover QR paste failed: {_e}")
    story.append(PageBreak())

    # ─── Page 2: Event Story ───
    story.append(Paragraph("Your Story With Us", H))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(llm.get("story", "").replace("\n", "<br/><br/>"), body))
    if req.host_message:
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph(f'<i>"{req.host_message}"</i> — {req.organised_by or req.guest_name}', centerBody))
    story.append(PageBreak())

    # ─── Page 3: Gallery — creative scrapbook collage ───
    if req.photos:
        story.append(Paragraph("Moments Captured", H))
        story.append(Paragraph("A few favourite frames from the celebration.", sub))
        story.append(Spacer(1, 0.15 * inch))
        story.extend(_build_scrapbook_pages(req.photos, _img, GOLD, GOLD_BRIGHT))
        story.append(PageBreak())

    # ─── Page 4: Team — circular initial-avatars + gold-on-chocolate roster ───
    if req.team or req.team_photo:
        story.append(Paragraph("Meet The Team", H))
        story.append(Paragraph("The people behind your celebration.", sub))
        story.append(Spacer(1, 0.15 * inch))
        # If a team-group photo is provided, show it framed (smaller, polaroid-style)
        if req.team_photo:
            im = _img(req.team_photo, w=4.0, h=2.4)
            if im:
                wrap = Table([[im]], colWidths=[4.0 * inch], rowHeights=[2.4 * inch])
                wrap.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), CREAM),
                    ("BOX", (0, 0), (-1, -1), 2, GOLD_BRIGHT),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(wrap)
                story.append(Spacer(1, 0.20 * inch))
        if req.team:
            # Build a roster: circular GOLD-on-CHOCOLATE initial avatars + names
            # in CREAM on CHOCOLATE rows so the team page matches the brand.
            avatar_cells = []
            row = []
            for member in req.team[:12]:
                avatar = _initial_avatar_flowable(
                    member.name, GOLD_BRIGHT, CHOCOLATE, CREAM, size_in=0.95,
                )
                label = Paragraph(
                    f"<para align='center'><b><font color='#FAF0DC' size='10'>{member.name}</font></b><br/>"
                    f"<font color='#DCAE50' size='8'><i>{member.role}</i></font></para>",
                    body,
                )
                cell = Table([[avatar], [label]],
                             colWidths=[1.7 * inch],
                             rowHeights=[1.0 * inch, 0.65 * inch])
                cell.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), CHOCOLATE),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOX", (0, 0), (-1, -1), 1, GOLD),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]))
                row.append(cell)
                if len(row) == 3:
                    avatar_cells.append(row)
                    row = []
            if row:
                while len(row) < 3:
                    row.append("")
                avatar_cells.append(row)
            if avatar_cells:
                grid = Table(avatar_cells,
                             colWidths=[1.95 * inch] * 3,
                             rowHeights=[1.75 * inch] * len(avatar_cells))
                grid.setStyle(TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(grid)
        story.append(PageBreak())

    # ─── Page 5: Gratitude ───
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("With Gratitude", H))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(llm.get("gratitude", ""), centerBody))
    story.append(PageBreak())

    # ─── Page 6: Blessings ───
    story.append(Spacer(1, 1.8 * inch))
    story.append(Paragraph("Our Blessings For You", H))
    story.append(Spacer(1, 0.2 * inch))
    bl = llm.get("blessing", "")
    blessing_style = ParagraphStyle(
        "blessing", parent=centerBody,
        fontName=DEV_FONT, fontSize=22, leading=34, textColor=GOLD_BRIGHT,
    )
    story.append(Paragraph(bl.replace("\n", "<br/>"), blessing_style))
    story.append(PageBreak())

    # ─── Page 7: Future Memory Invitation ───
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("Until We Meet Again", H))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(llm.get("future_invitation", ""), centerBody))
    story.append(Spacer(1, 0.35 * inch))

    # ── Dedicated "Book Your Next Celebration" card ──
    QR_PATH = "/app/backend/static/purnabramha_booking_qr.png"
    if req.show_qr and os.path.exists(QR_PATH):
        try:
            from reportlab.platypus import Image as RLImage
            qr_im = RLImage(QR_PATH, width=1.8 * inch, height=1.8 * inch)
            # Right column: contact info
            contact_bits = []
            if (req.phone or "").strip():
                contact_bits.append(f"<b>{req.phone.strip()}</b>")
            if (req.instagram_url or "").strip():
                ig = req.instagram_url.strip()
                handle = ig.rstrip("/").split("/")[-1]
                if handle and not handle.startswith("@"):
                    handle = "@" + handle
                contact_bits.append(handle)
            contact_bits.append("www.purnabramha.com")
            right_html = (
                "<para align='left'>"
                "<font color='#DCAE50' size='14'><b>Book Your Next Celebration</b></font><br/><br/>"
                "<font color='#FAF0DC' size='10'>"
                + "<br/>".join(contact_bits) + "</font><br/><br/>"
                "<font color='#BF8C32' size='9'><i>Scan the QR — choose date, occasion, guests.</i></font>"
                "</para>"
            )
            right_par = Paragraph(right_html, body)
            booking_card = Table(
                [[qr_im, right_par]],
                colWidths=[2.0 * inch, 3.6 * inch],
                rowHeights=[2.0 * inch],
            )
            booking_card.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ("BACKGROUND", (0, 0), (-1, -1), CHOCOLATE),
                ("BOX", (0, 0), (-1, -1), 2, GOLD_BRIGHT),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]))
            story.append(booking_card)
        except Exception as _e:
            logger.warning(f"booking QR card failed: {_e}")

    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph(f"— The Purnabramha Family · {center_name} —", small))
    story.append(Paragraph(
        "<i>पुर्णब्रह्म परिवाराकडून प्रेमपूर्वक</i>",
        ParagraphStyle("brand_mr", parent=small, fontName=DEV_FONT,
                       fontSize=13, textColor=GOLD)
    ))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"Memory Box ID: {box_id}", small))

    # ─── PAGE BACKGROUND: full Dark Chocolate with antique-gold double border ──
    def _on_page(canv, _doc):
        canv.saveState()
        page_w, page_h = A4
        # Full chocolate background
        canv.setFillColor(CHOCOLATE)
        canv.rect(0, 0, page_w, page_h, fill=1, stroke=0)
        # Outer antique-gold border
        canv.setStrokeColor(GOLD_BRIGHT)
        canv.setLineWidth(3)
        canv.rect(0.35 * inch, 0.35 * inch,
                  page_w - 0.7 * inch, page_h - 0.7 * inch,
                  fill=0, stroke=1)
        # Inner thin gold border
        canv.setStrokeColor(GOLD)
        canv.setLineWidth(1)
        canv.rect(0.5 * inch, 0.5 * inch,
                  page_w - 1.0 * inch, page_h - 1.0 * inch,
                  fill=0, stroke=1)
        # Corner paisley ornaments
        for cx, cy in [(0.7 * inch, page_h - 0.7 * inch),
                       (page_w - 0.7 * inch, page_h - 0.7 * inch),
                       (0.7 * inch, 0.7 * inch),
                       (page_w - 0.7 * inch, 0.7 * inch)]:
            for r in [10, 6, 3]:
                canv.setStrokeColor(GOLD_BRIGHT)
                canv.setLineWidth(1.4)
                canv.circle(cx, cy, r, fill=0, stroke=1)
        canv.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()


def _render_cover_png(req: MemoryBoxRequest, center_name: str, box_id: str,
                      llm: dict | None = None) -> bytes:
    """Premium chocolate-and-gold summary IMAGE — one-page shareable.

    Replaces the old "thank-you cover" with a richer card that includes:
      • Guest name + occasion + date
      • Up to 3 photo thumbnails (artistic strip)
      • Marathi blessing snippet
      • Per-center contact + Scan-to-Book QR
      • Brand footer
    """
    try:
        from PIL import Image as PImage, ImageDraw, ImageFont
        W, H = 1080, 1620
        canvas = PImage.new("RGB", (W, H), (43, 24, 16))   # DARK CHOCOLATE
        draw = ImageDraw.Draw(canvas, "RGBA")
        # Outer antique-gold double border
        draw.rectangle([20, 20, W - 20, H - 20], outline=(220, 174, 80), width=5)
        draw.rectangle([42, 42, W - 42, H - 42], outline=(191, 140, 50), width=2)
        # Corner paisley ornaments
        for cx, cy in [(70, 70), (W - 70, 70), (70, H - 70), (W - 70, H - 70)]:
            for r in [16, 10, 5]:
                draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                             outline=(220, 174, 80), width=2)

        # Fonts (prefer bundled, fallback to system)
        _BF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "static", "fonts")
        def _ff(name, sys_path):
            return name if os.path.exists(name) else sys_path
        try:
            LBOLD = _ff(os.path.join(_BF, "LiberationSerif-Bold.ttf"),
                        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf")
            LREG = _ff(os.path.join(_BF, "LiberationSerif-Regular.ttf"),
                       "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf")
            LIT = _ff(os.path.join(_BF, "LiberationSerif-Italic.ttf"),
                      "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf")
            DBOLD = _ff(os.path.join(_BF, "NotoSansDevanagari-Bold.ttf"),
                        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf")
            f_brand = ImageFont.truetype(LBOLD, 36)
            f_host = ImageFont.truetype(LBOLD, 80)
            f_occ = ImageFont.truetype(LBOLD, 44)
            ImageFont.truetype(LIT, 36)
            ImageFont.truetype(LREG, 28)
            f_mr_big = ImageFont.truetype(DBOLD, 46)
            f_mr_sm = ImageFont.truetype(DBOLD, 26)
            f_sm = ImageFont.truetype(LBOLD, 26)
            f_label = ImageFont.truetype(LBOLD, 20)
        except Exception:
            f_brand = f_host = f_occ = f_mr_big = f_mr_sm = f_sm = f_label = ImageFont.load_default()

        def _center(y, text, font, fill):
            bb = draw.textbbox((0, 0), text, font=font)
            w = bb[2] - bb[0]
            draw.text(((W - w) // 2 + 2, y + 2), text, font=font, fill=(0, 0, 0, 200))
            draw.text(((W - w) // 2, y), text, font=font, fill=fill)
            return bb[3] - bb[1]

        # ── Top section: Logo + brand ───────────────────────────────────
        y = 70
        if os.path.exists(LOGO_PATH):
            try:
                logo = PImage.open(LOGO_PATH).convert("RGBA")
                logo.thumbnail((220, 220), PImage.LANCZOS)
                canvas.paste(logo, ((W - logo.width) // 2, y), logo)
                y += logo.height + 10
            except Exception:
                pass
        _center(y, "MEMORY BOX  ·  आठवणींची पेटी", f_mr_sm, (220, 174, 80))
        y += 50

        # ── Guest name ───────────────────────────────────────────────────
        gn = req.guest_name[:34]
        _center(y, gn, f_host, (220, 174, 80))
        y += 100

        # ── Occasion + date pill ────────────────────────────────────────
        occ = req.occasion if req.occasion != "Other" else (req.occasion_other or "Celebration")
        pill_text = f"{occ}  ·  {req.event_date}"
        bb = draw.textbbox((0, 0), pill_text, font=f_occ)
        pw = bb[2] - bb[0]
        ph = bb[3] - bb[1]
        px = (W - pw) // 2 - 24
        draw.rounded_rectangle([px, y - 8, px + pw + 48, y + ph + 12],
                               radius=22, outline=(220, 174, 80), width=2)
        _center(y, pill_text, f_occ, (250, 240, 220))
        y += ph + 35

        # ── Photo strip (up to 3 thumbs) ────────────────────────────────
        if req.photos:
            strip_y = y
            n = min(3, len(req.photos))
            thumb_w = 290
            thumb_h = 220
            gap = 18
            strip_w = n * thumb_w + (n - 1) * gap
            sx = (W - strip_w) // 2
            for i in range(n):
                try:
                    raw = _strip_data_url(req.photos[i])
                    if not raw:
                        continue
                    im = PImage.open(io.BytesIO(raw)).convert("RGBA")
                    gw, gh = im.size
                    s = max(thumb_w / gw, thumb_h / gh)
                    im2 = im.resize((int(gw * s), int(gh * s)), PImage.LANCZOS)
                    lft = (im2.width - thumb_w) // 2
                    tp = (im2.height - thumb_h) // 2
                    cropped = im2.crop((lft, tp, lft + thumb_w, tp + thumb_h))
                    # Frame
                    border = 8
                    frame = PImage.new("RGBA", (thumb_w + border * 2, thumb_h + border * 2),
                                       (250, 240, 220, 255))
                    frame.paste(cropped, (border, border))
                    fd = ImageDraw.Draw(frame)
                    fd.rectangle([border - 2, border - 2, border + thumb_w + 2, border + thumb_h + 2],
                                 outline=(220, 174, 80), width=3)
                    # Slight tilt for charm
                    tilt = (-3, 2, -2)[i % 3]
                    frame = frame.rotate(tilt, expand=True, resample=PImage.BICUBIC)
                    canvas.paste(frame, (sx + i * (thumb_w + gap) - 8, strip_y - 8), frame)
                except Exception as _e:
                    logger.warning(f"summary thumb {i} failed: {_e}")
            y += thumb_h + 50

        # ── Marathi blessing snippet ────────────────────────────────────
        blessing_text = (llm.get("blessing", "") if llm else "")
        if blessing_text:
            # Show 2nd line of blessing (after the "श्री स्वामी समर्थ" anchor)
            lines_b = [ln.strip() for ln in blessing_text.strip().split("\n") if ln.strip()]
            line = lines_b[1] if len(lines_b) > 1 else (lines_b[0] if lines_b else "")
            if line:
                # Auto-shrink font to fit width
                _fs = 46
                f_try = f_mr_big
                bb = draw.textbbox((0, 0), line, font=f_try)
                while (bb[2] - bb[0]) > W - 100 and _fs > 24:
                    _fs -= 2
                    try:
                        f_try = ImageFont.truetype(DBOLD, _fs)
                    except Exception:
                        break
                    bb = draw.textbbox((0, 0), line, font=f_try)
                bw = bb[2] - bb[0]
                draw.text(((W - bw) // 2 + 2, y + 2), line, font=f_try, fill=(0, 0, 0, 200))
                draw.text(((W - bw) // 2, y), line, font=f_try, fill=(220, 174, 80))
                y += (bb[3] - bb[1]) + 24

        # ── Booking QR + contact ────────────────────────────────────────
        qr_drawn_y = y
        QR_PATH = "/app/backend/static/purnabramha_booking_qr.png"
        if req.show_qr and os.path.exists(QR_PATH):
            try:
                qr = PImage.open(QR_PATH).convert("RGBA")
                qr_d = 190
                qr.thumbnail((qr_d, qr_d), PImage.LANCZOS)
                card_pad = 12
                card_w = qr.width + card_pad * 2
                card_h = qr.height + card_pad * 2 + 30
                qx = 120
                qy = y
                draw.rounded_rectangle([qx, qy, qx + card_w, qy + card_h],
                                       radius=14, fill=(252, 244, 220, 245),
                                       outline=(220, 174, 80), width=3)
                canvas.paste(qr, (qx + card_pad, qy + card_pad), qr)
                _lbl = "SCAN TO BOOK"
                bb = draw.textbbox((0, 0), _lbl, font=f_label)
                ltw = bb[2] - bb[0]
                draw.text((qx + (card_w - ltw) // 2, qy + card_pad + qr.height + 4),
                          _lbl, font=f_label, fill=(43, 24, 16))
            except Exception as _e:
                logger.warning(f"summary QR failed: {_e}")

        # Contact info on right of QR
        contact_x = 380
        c_y = y + 12
        contact_lines = []
        if (req.phone or "").strip():
            contact_lines.append(("☎ " + req.phone.strip(), f_sm, (250, 240, 220)))
        if (req.instagram_url or "").strip():
            handle = req.instagram_url.strip().rstrip("/").split("/")[-1]
            if handle and not handle.startswith("@"):
                handle = "@" + handle
            contact_lines.append((handle, f_sm, (220, 174, 80)))
        contact_lines.append(("www.purnabramha.com", f_sm, (250, 240, 220)))
        # Heading
        draw.text((contact_x, c_y), "BOOK YOUR NEXT CELEBRATION",
                  font=f_label, fill=(220, 174, 80))
        c_y += 32
        for txt, fnt, color in contact_lines:
            draw.text((contact_x, c_y), txt, font=fnt, fill=color)
            c_y += 38

        y = qr_drawn_y + 240

        # ── Brand footer ────────────────────────────────────────────────
        y = H - 130
        _center(y, f"Purnabramha · {center_name}", f_brand, (220, 174, 80))
        y += 50
        _center(y, "पुर्णब्रह्म परिवाराकडून प्रेमपूर्वक",
                f_mr_sm, (191, 140, 50))

        out = io.BytesIO()
        canvas.save(out, "PNG", optimize=True)
        return out.getvalue()
    except Exception as e:
        logger.warning(f"Memory box PNG fallback to blank: {e}")
        return b""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/types")
async def list_types(req: BaseReq):
    await check_access(req.token)
    return {"occasions": OCCASIONS, "emotions": EMOTIONS}


@router.post("/team-roster")
async def team_roster(req: RosterReq):
    """Auto-pull team members marked Present at this center on the event date.
    Returns [{name, role}] — manager edits before generation."""
    await check_access(req.token)
    rows = await db.attendance.find(
        {"center": req.center, "date": req.event_date, "status": "P"},
        {"_id": 0, "employeeName": 1, "designation": 1},
    ).to_list(50)
    team = [{"name": r.get("employeeName", "").strip(),
             "role": (r.get("designation") or "Service Associate").strip()}
            for r in rows if r.get("employeeName")]
    return {"team": team, "count": len(team), "date": req.event_date, "center": req.center}


@router.post("/generate")
async def generate(req: MemoryBoxRequest):
    session = await check_access(req.token)
    if not _can_create(session):
        raise HTTPException(403, "Not permitted to create memory boxes")
    if not req.guest_name.strip() or not req.event_date or not req.occasion:
        raise HTTPException(400, "Guest name, event date and occasion are required")
    if len(req.photos) > 10:
        raise HTTPException(400, "Maximum 10 photos allowed")

    # Resolve center friendly name
    cdoc = await db.centers.find_one({"code": (req.center or "").upper()}, {"_id": 0}) or {}
    center_name = cdoc.get("name") or req.center

    llm = await _gpt_story(req, center_name)

    box_id = str(uuid.uuid4())
    pdf_bytes = _build_pdf(req, center_name, llm, box_id)
    cover_png = _render_cover_png(req, center_name, box_id, llm=llm)

    # Save assets
    center_safe = (req.center or "UNKNOWN").replace("/", "_")
    sub = os.path.join(ASSET_DIR, center_safe)
    os.makedirs(sub, exist_ok=True)
    pdf_path = os.path.join(sub, f"{box_id}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
    png_path = os.path.join(sub, f"{box_id}.png")
    if cover_png:
        with open(png_path, "wb") as f:
            f.write(cover_png)

    occ = req.occasion if req.occasion != "Other" else (req.occasion_other or "Celebration")

    # ── Animated Memory Box (MP4 + Web link) — optional ─────────────────
    video_path = None
    video_size = 0
    web_path = None
    web_url = None
    video_meta: dict = {}
    ai_pick_count = 0
    if (req.generate_video or req.generate_web) and req.photos:
        try:
            from utils.memory_photo_rank import rank_photos, split_into_collage_sets
            top_idx, _scores = rank_photos(req.photos, top_n=9)
            ai_pick_count = len(top_idx)
            collage_idx_sets = split_into_collage_sets(top_idx)

            # Resolve center contact info for the closing scene
            center_info = {
                "name": center_name,
                "instagram_url": req.instagram_url or cdoc.get("instagram_url") or "",
                "website": req.website or cdoc.get("website") or "",
                "phone": req.phone or cdoc.get("phone") or "",
            }
            delivery_mode = (req.delivery_mode or "function").strip().lower()
            if delivery_mode not in {"function", "home"}:
                delivery_mode = "function"
        except Exception as e:
            logger.warning(f"memory-box: AI ranking failed: {e}")
            top_idx, collage_idx_sets, center_info = [], [[], [], []], {}
            delivery_mode = "function"

        # MP4
        if req.generate_video:
            try:
                from utils.memory_video import render_memory_video
                from PIL import Image as _PIL
                import io as _io
                # Decode ranked photos once (PIL)
                decoded: list = []
                for ix in top_idx:
                    raw = _strip_data_url(req.photos[ix])
                    if not raw:
                        decoded.append(None)
                        continue
                    try:
                        decoded.append(_PIL.open(_io.BytesIO(raw)).convert("RGB"))
                    except Exception:
                        decoded.append(None)
                # Re-index collage sets to match `decoded` positions
                pos_of = {orig: i for i, orig in enumerate(top_idx)}
                collage_sets = [[pos_of[ix] for ix in s if ix in pos_of]
                                for s in collage_idx_sets]
                team_pil = None
                if req.team_photo:
                    raw_t = _strip_data_url(req.team_photo)
                    if raw_t:
                        try:
                            team_pil = _PIL.open(_io.BytesIO(raw_t)).convert("RGB")
                        except Exception:
                            team_pil = None
                video_path = os.path.join(sub, f"{box_id}.mp4")
                video_meta = render_memory_video(
                    out_path=video_path,
                    center_name=center_name,
                    occasion=occ,
                    delivery_mode=delivery_mode,
                    ranked_photos=[d for d in decoded if d is not None],
                    collage_sets=collage_sets,
                    team_photo=team_pil,
                    team=[t.dict() for t in req.team],
                    story_text=llm.get("story", ""),
                    guest_name=req.guest_name,
                    center_info=center_info,
                    center_qr_path=None,
                    music=bool(req.music),
                )
                video_size = video_meta.get("size_bytes", 0)
            except Exception as e:
                logger.exception(f"memory-box video gen failed: {e}")
                video_path = None
                video_size = 0

        # Web link
        if req.generate_web:
            try:
                from utils.memory_web import render_memory_html
                # Build collage sets as data-URL strings
                photos_b64_by_set = [
                    [req.photos[ix] for ix in s if ix < len(req.photos)]
                    for s in collage_idx_sets
                ]
                web_path = os.path.join(sub, f"{box_id}.html")
                web_meta = render_memory_html(
                    out_path=web_path,
                    guest_name=req.guest_name,
                    center_name=center_name,
                    occasion=occ,
                    delivery_mode=delivery_mode,
                    photos_b64_by_set=photos_b64_by_set,
                    team_photo_b64=req.team_photo or None,
                    team=[t.dict() for t in req.team],
                    story_text=llm.get("story", ""),
                    center_info=center_info,
                )
                _ = web_meta.get("size_bytes", 0)
                # Build the public viewer URL using REACT_APP_BACKEND_URL if set,
                # else fall back to relative path which the frontend resolves.
                public_base = os.environ.get("PUBLIC_BACKEND_URL", "").rstrip("/")
                web_url = (f"{public_base}/api/memory-box/view/{box_id}"
                           if public_base else f"/api/memory-box/view/{box_id}")
            except Exception as e:
                logger.exception(f"memory-box web gen failed: {e}")
                web_path = None
                web_url = None

    doc = {
        "box_id": box_id,
        "center": req.center,
        "center_name": center_name,
        "guest_name": req.guest_name,
        "mobile": req.mobile,
        "email": req.email or "",
        "event_date": req.event_date,
        "order_number": req.order_number or "",
        "occasion": occ,
        "emotion": req.emotion,
        "celebration_for": req.celebration_for,
        "special_moment": req.special_moment,
        "organised_by": req.organised_by,
        "host_message": req.host_message,
        "team": [t.dict() for t in req.team],
        "photo_count": len(req.photos),
        "ai_picked_photo_count": ai_pick_count,
        "delivery_mode": (req.delivery_mode or "function"),
        "story_text": llm.get("story", ""),
        "gratitude_text": llm.get("gratitude", ""),
        "blessing_text": llm.get("blessing", ""),
        "future_invitation_text": llm.get("future_invitation", ""),
        "asset_pdf": pdf_path,
        "asset_png": png_path if cover_png else None,
        "asset_mp4": video_path,
        "asset_html": web_path,
        "video_size_bytes": video_size,
        "video_duration_sec": video_meta.get("duration_sec") if video_meta else None,
        "web_url": web_url,
        "size_bytes": len(pdf_bytes),
        "created_by": session.get("managerName") or session.get("mobile") or "Unknown",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "delivery": {"whatsapp": None, "email": None, "downloads": 0,
                     "video_downloads": 0, "web_views": 0},
        "status": "active",
    }
    await db.memory_boxes.insert_one(doc)
    return {
        "box_id": box_id,
        "pdf_size_kb": round(len(pdf_bytes) / 1024.0, 1),
        "cover_png_base64": base64.b64encode(cover_png).decode("ascii") if cover_png else "",
        "story_text": llm.get("story", ""),
        "gratitude_text": llm.get("gratitude", ""),
        "blessing_text": llm.get("blessing", ""),
        "future_invitation_text": llm.get("future_invitation", ""),
        "video_available": bool(video_path),
        "video_size_kb": round(video_size / 1024.0, 1) if video_size else 0,
        "video_duration_sec": video_meta.get("duration_sec") if video_meta else None,
        "web_url": web_url,
        "ai_picked_photo_count": ai_pick_count,
    }


@router.post("/asset/{box_id}")
async def asset(box_id: str, req: BaseReq):
    await check_access(req.token)
    box = await db.memory_boxes.find_one({"box_id": box_id}, {"_id": 0})
    if not box:
        raise HTTPException(404, "Memory box not found")
    p = box.get("asset_pdf")
    if not p or not os.path.exists(p):
        raise HTTPException(404, "PDF asset missing")
    await db.memory_boxes.update_one({"box_id": box_id}, {"$inc": {"delivery.downloads": 1}})
    return StreamingResponse(open(p, "rb"), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="MemoryBox_{box["guest_name"].replace(" ","_")}_{box["event_date"]}.pdf"'})


@router.post("/video/{box_id}")
async def asset_video(box_id: str, req: BaseReq):
    """Download the animated MP4 memory box (auth required)."""
    await check_access(req.token)
    box = await db.memory_boxes.find_one({"box_id": box_id}, {"_id": 0})
    if not box:
        raise HTTPException(404, "Memory box not found")
    p = box.get("asset_mp4")
    if not p or not os.path.exists(p):
        raise HTTPException(404, "Video asset missing — re-generate with video enabled")
    await db.memory_boxes.update_one({"box_id": box_id},
                                     {"$inc": {"delivery.video_downloads": 1}})
    fname = f'MemoryBox_{box["guest_name"].replace(" ","_")}_{box["event_date"]}.mp4'
    return StreamingResponse(open(p, "rb"), media_type="video/mp4",
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})


from fastapi.responses import HTMLResponse

@router.get("/view/{box_id}")
async def view_memory(box_id: str):
    """PUBLIC viewer for the animated web Memory Box. Customer-facing,
    shareable as a link — no token required."""
    box = await db.memory_boxes.find_one({"box_id": box_id}, {"_id": 0})
    if not box or box.get("status") == "deleted":
        raise HTTPException(404, "Memory box not found")
    p = box.get("asset_html")
    if not p or not os.path.exists(p):
        raise HTTPException(404, "Web view not generated for this Memory Box")
    try:
        with open(p, "r", encoding="utf-8") as f:
            html = f.read()
    except Exception as e:
        raise HTTPException(500, f"Failed to load Memory Box: {e}")
    # Best-effort view counter
    await db.memory_boxes.update_one({"box_id": box_id},
                                     {"$inc": {"delivery.web_views": 1}})
    return HTMLResponse(content=html)


@router.get("/view-video/{box_id}")
async def view_video(box_id: str):
    """PUBLIC stream of the animated MP4 — used by the inline player and
    by anyone holding the shareable link. No token required."""
    box = await db.memory_boxes.find_one({"box_id": box_id}, {"_id": 0})
    if not box or box.get("status") == "deleted":
        raise HTTPException(404, "Memory box not found")
    p = box.get("asset_mp4")
    if not p or not os.path.exists(p):
        raise HTTPException(404, "Video not generated for this Memory Box")
    return StreamingResponse(open(p, "rb"), media_type="video/mp4",
                             headers={"Accept-Ranges": "bytes"})


@router.post("/list")
async def list_boxes(req: ListReq):
    session = await check_access(req.token)
    q: dict = {"status": {"$ne": "deleted"}}
    if req.center:
        q["center"] = req.center.upper()
    elif not (session.get("is_super_admin") or session.get("is_admin")):
        own = (session.get("center") or "").upper()
        if own:
            q["center"] = own
    rows = await db.memory_boxes.find(
        q, {"_id": 0, "asset_pdf": 0, "asset_png": 0, "asset_mp4": 0, "asset_html": 0}
    ).sort("created_at", -1).limit(req.limit).to_list(req.limit)
    return {"items": rows, "count": len(rows)}


@router.post("/stats")
async def stats(req: ListReq):
    session = await check_access(req.token)
    q: dict = {"status": {"$ne": "deleted"}}
    if req.center:
        q["center"] = req.center.upper()
    elif not (session.get("is_super_admin") or session.get("is_admin")):
        own = (session.get("center") or "").upper()
        if own:
            q["center"] = own
    pipe = [
        {"$match": q},
        {"$group": {
            "_id": None,
            "created": {"$sum": 1},
            "shared_wa": {"$sum": {"$cond": [{"$ifNull": ["$delivery.whatsapp", False]}, 1, 0]}},
            "shared_email": {"$sum": {"$cond": [{"$ifNull": ["$delivery.email", False]}, 1, 0]}},
            "downloads": {"$sum": {"$ifNull": ["$delivery.downloads", 0]}},
        }},
    ]
    agg = await db.memory_boxes.aggregate(pipe).to_list(1)
    a = agg[0] if agg else {"created": 0, "shared_wa": 0, "shared_email": 0, "downloads": 0}
    return {
        "memory_boxes_created": a.get("created", 0),
        "memory_boxes_shared_whatsapp": a.get("shared_wa", 0),
        "memory_boxes_shared_email": a.get("shared_email", 0),
        "downloads": a.get("downloads", 0),
    }


@router.post("/whatsapp-preview/{box_id}")
async def whatsapp_preview(box_id: str, req: BaseReq):
    await check_access(req.token)
    box = await db.memory_boxes.find_one({"box_id": box_id}, {"_id": 0})
    if not box:
        raise HTTPException(404, "Not found")
    msg = (
        f"Namaste {box['guest_name']}! 🙏\n\n"
        f"Thank you for letting {box['center_name']} be part of your "
        f"*{box['occasion']}* on {box['event_date']}. 🎉\n\n"
        f"We have put together a small Memory Box for you — a few words and pictures "
        f"to help relive the day.\n\n"
        f"_{(box.get('gratitude_text') or '')[:240]}_\n\n"
        f"Reply to this message and we'll be delighted to host you again.\n"
        f"— The Purnabramha Family 🌿"
    )
    return {"message": msg, "phone": box.get("mobile", ""), "guest_name": box["guest_name"]}


@router.post("/mark-whatsapp-sent/{box_id}")
async def mark_whatsapp_sent(box_id: str, req: BaseReq):
    session = await check_access(req.token)
    sent_at = datetime.now(timezone.utc).isoformat()
    res = await db.memory_boxes.update_one(
        {"box_id": box_id},
        {"$set": {"delivery.whatsapp": {
            "sent_at": sent_at,
            "sent_by": session.get("managerName") or session.get("mobile") or "Unknown",
        }}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Not found")
    return {"success": True, "sent_at": sent_at}


class EmailReq(BaseReq):
    to_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None


@router.post("/send-email/{box_id}")
async def send_email(box_id: str, req: EmailReq):
    session = await check_access(req.token)
    box = await db.memory_boxes.find_one({"box_id": box_id}, {"_id": 0})
    if not box:
        raise HTTPException(404, "Not found")
    to_email = (req.to_email or box.get("email") or "").strip()
    if not to_email or "@" not in to_email:
        raise HTTPException(400, "Guest email missing — pass to_email or add one.")
    pdf_path = box.get("asset_pdf")
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(404, "PDF asset missing")
    from server import CFG                          # type: ignore
    email_cfg = (CFG or {}).get("email", {}) or {}
    if not email_cfg.get("enabled") or not email_cfg.get("smtp_user"):
        raise HTTPException(503, "SMTP not configured on server.")
    smtp_host = email_cfg.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(email_cfg.get("smtp_port", 587))
    smtp_user = email_cfg["smtp_user"]
    smtp_pass = email_cfg["smtp_pass"]
    from_name = email_cfg.get("from_name", "Purnabramha Team")
    from_email = email_cfg.get("from_email", smtp_user)

    subject = req.subject or f"A Memory Box from Purnabramha — {box['guest_name']}"
    body = req.body or (
        f"Dear {box['guest_name']},\n\n"
        f"Please find attached a small Memory Box from the Purnabramha {box['center_name']} family — "
        f"a keepsake from your {box['occasion']} on {box['event_date']}.\n\n"
        f"Thank you for letting us be part of this celebration.\n\n"
        f"With warm regards,\nThe Purnabramha Family"
    )
    try:
        import smtplib
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email
        msg.set_content(body)
        with open(pdf_path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="pdf",
                               filename=f"MemoryBox_{box['guest_name'].replace(' ','_')}.pdf")
        with smtplib.SMTP(smtp_host, smtp_port) as srv:
            srv.starttls()
            srv.login(smtp_user, smtp_pass)
            srv.send_message(msg)
    except Exception as e:
        logger.error(f"Memory box email failed: {e}", exc_info=True)
        raise HTTPException(500, f"Email send failed: {e}")

    sent_at = datetime.now(timezone.utc).isoformat()
    await db.memory_boxes.update_one(
        {"box_id": box_id},
        {"$set": {"delivery.email": {
            "to": to_email, "sent_at": sent_at,
            "sent_by": session.get("managerName") or session.get("mobile") or "Unknown",
        }}},
    )
    return {"success": True, "to": to_email, "sent_at": sent_at}
