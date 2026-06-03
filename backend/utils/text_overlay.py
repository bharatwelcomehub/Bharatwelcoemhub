"""Server-side text overlay for AI-generated creatives.

The image LLM (Nano Banana) frequently mangles Devanagari/Marathi script when
asked to burn text into the image. Solution: prompt the LLM to leave a clean
top/bottom band, then overlay crisp text using Pillow + Noto Sans Devanagari.
"""
import io
import logging
import os
import textwrap
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ── Font discovery ─────────────────────────────────────────────────────────
# Production containers sometimes lack /usr/share/fonts/* (Devanagari renders
# as tofu boxes ☐☐☐). We ship the fonts inside the repo to guarantee they
# are present in EVERY environment. System paths are kept as fallbacks.
_BUNDLED_FONTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static", "fonts",
)


def _font_path(*candidates: str) -> str:
    """Return the first candidate path that exists, else the last candidate."""
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return candidates[-1] if candidates else ""


DEVANAGARI_BOLD = _font_path(
    os.path.join(_BUNDLED_FONTS_DIR, "NotoSansDevanagari-Bold.ttf"),
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
)
DEVANAGARI_REG = _font_path(
    os.path.join(_BUNDLED_FONTS_DIR, "NotoSansDevanagari-Regular.ttf"),
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
)
DEVANAGARI_SERIF_BOLD = _font_path(
    os.path.join(_BUNDLED_FONTS_DIR, "NotoSerifDevanagari-Bold.ttf"),
    "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Bold.ttf",
)
LATIN_BOLD = _font_path(
    os.path.join(_BUNDLED_FONTS_DIR, "LiberationSerif-Bold.ttf"),
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
)
LATIN_REG = _font_path(
    os.path.join(_BUNDLED_FONTS_DIR, "LiberationSerif-Regular.ttf"),
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
)
LATIN_ITALIC = _font_path(
    os.path.join(_BUNDLED_FONTS_DIR, "LiberationSerif-Italic.ttf"),
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
)

# ── Brand palette (PURNABRAMHA OFFICIAL — 2026) ───────────────────────────
# Dark Chocolate Brown — primary background
DARK_CHOCOLATE = (43, 24, 16)
DARK_CHOCOLATE_RGBA = (43, 24, 16, 245)
# Rich Antique Gold — headings, borders, accents
ANTIQUE_GOLD = (191, 140, 50)
ANTIQUE_GOLD_BRIGHT = (220, 175, 80)
# Deep Maroon — festive / celebration elements
DEEP_MAROON = (102, 14, 14)
# Warm Cream / Off White — readability text
WARM_CREAM = (250, 240, 220)
WARM_CREAM_SOFT = (240, 228, 200)
# Back-compat aliases (old code uses these names)
MAROON = DEEP_MAROON
GOLD = ANTIQUE_GOLD
CREAM = WARM_CREAM
WHITE = (255, 255, 255)
DARK_BG = (43, 24, 16, 230)        # rgba dark chocolate band


def composite_guest_photo(
    bg_bytes: bytes,
    guest_photo_bytes: bytes,
    aspect: str = "1:1",
    balgopal: bool = False,
    is_group: bool = False,
) -> bytes:
    """Paste the actual guest photo on the LEFT side of the AI background.

    The AI is unreliable at face preservation, so we generate ONLY the brand
    backdrop + food via the LLM and then composite the real photo on the left.
    Faces are guaranteed to look exactly like the upload.

    For 9:16 / vertical formats, we use the TOP half instead of the LEFT half.
    Balgopal mode adds a gold star burst behind the photo.

    Fit mode:
    - is_group=True → contain-fit (whole photo visible, may have cream bars on
      sides). This preserves EVERY face in a wide group photo.
    - is_group=False → cover-fit (faces dominate; outer edges may crop). Good
      for single-person portraits.
    """
    try:
        bg = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
        guest = Image.open(io.BytesIO(guest_photo_bytes)).convert("RGBA")
    except Exception as e:
        logger.error(f"composite_guest_photo: bad input: {e}")
        return bg_bytes

    W, H = bg.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # ── Place the photo on the LEFT (or TOP for portrait/story) ───────────
    if aspect == "9:16":
        # Vertical: photo on top half
        pad = int(min(W, H) * 0.06)
        avail_w = W - 2 * pad
        avail_h = int(H * 0.45) - pad
    else:
        # Square / portrait poster: photo on left
        pad = int(min(W, H) * 0.05)
        avail_w = int(W * 0.45) - pad
        avail_h = H - 2 * pad - int(H * 0.18)   # leave bottom band for text

    # Scale the guest photo
    gw, gh = guest.size
    if is_group:
        # CONTAIN-FIT — entire photo visible, no cropping
        scale = min(avail_w / gw, avail_h / gh)
        new_w, new_h = int(gw * scale), int(gh * scale)
        guest_scaled = guest.resize((new_w, new_h), Image.LANCZOS)
        # Center inside the available rectangle
        canvas = Image.new("RGBA", (avail_w, avail_h), (253, 246, 231, 255))  # cream backdrop
        cx_off = (avail_w - new_w) // 2
        cy_off = (avail_h - new_h) // 2
        canvas.paste(guest_scaled, (cx_off, cy_off), guest_scaled)
        guest_cropped = canvas
    else:
        # COVER-FIT — fills the rectangle, may slightly crop edges
        scale = max(avail_w / gw, avail_h / gh)
        new_w, new_h = int(gw * scale), int(gh * scale)
        guest_scaled = guest.resize((new_w, new_h), Image.LANCZOS)
        cx, cy = new_w // 2, new_h // 2
        left = cx - avail_w // 2
        top = cy - avail_h // 2
        guest_cropped = guest_scaled.crop((left, top, left + avail_w, top + avail_h))

    # ── Decorative frame ───────────────────────────────────────────────────
    if aspect == "9:16":
        photo_x = pad
        photo_y = pad
    else:
        photo_x = pad
        photo_y = (H - avail_h) // 2

    # Gold star burst behind photo (Balgopal mode)
    if balgopal:
        star = Image.new("RGBA", (avail_w + 80, avail_h + 80), (0, 0, 0, 0))
        sd = ImageDraw.Draw(star)
        cx, cy = star.width // 2, star.height // 2
        # 8-point star rays
        import math
        for i in range(16):
            ang = (math.pi / 8) * i
            outer = (cx + int(math.cos(ang) * (star.width // 2 + 20)),
                     cy + int(math.sin(ang) * (star.height // 2 + 20)))
            sd.line([cx, cy, outer[0], outer[1]],
                    fill=(220, 175, 60, 90 if i % 2 else 140), width=14 if i % 2 else 22)
        # Soft glow ellipse
        glow = Image.new("RGBA", star.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse([10, 10, star.width - 10, star.height - 10],
                   fill=(255, 220, 140, 120))
        try:
            from PIL import ImageFilter
            glow = glow.filter(ImageFilter.GaussianBlur(radius=24))
            star = star.filter(ImageFilter.GaussianBlur(radius=6))
        except Exception:
            pass
        layer.paste(glow, (photo_x - 40, photo_y - 40), glow)
        layer.paste(star, (photo_x - 40, photo_y - 40), star)

    # White card frame behind the photo (subtle, 8px padding)
    frame_pad = 8
    frame_rect = [photo_x - frame_pad, photo_y - frame_pad,
                  photo_x + avail_w + frame_pad, photo_y + avail_h + frame_pad]
    # Drop shadow
    shadow = Image.new("RGBA", (avail_w + 24, avail_h + 24), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([6, 6, avail_w + 18, avail_h + 18],
                         radius=14, fill=(0, 0, 0, 110))
    try:
        from PIL import ImageFilter
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=8))
    except Exception:
        pass
    layer.paste(shadow, (photo_x - 6, photo_y - 6), shadow)
    # Cream card
    draw.rounded_rectangle(frame_rect, radius=14, fill=(253, 246, 231, 255))
    # Photo
    # Round the corners of the photo to match the frame
    mask = Image.new("L", (avail_w, avail_h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, avail_w, avail_h], radius=10, fill=255)
    layer.paste(guest_cropped, (photo_x, photo_y), mask)
    # Gold inner border
    draw.rounded_rectangle(
        [photo_x - 1, photo_y - 1, photo_x + avail_w + 1, photo_y + avail_h + 1],
        radius=11, outline=GOLD, width=3,
    )

    out = Image.alpha_composite(bg, layer).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()

GOLD_BG = (176, 132, 49, 220)


def _font(path: str, size: int):
    """Load font with graceful fallback to default."""
    try:
        return ImageFont.truetype(path, size)
    except Exception as e:
        logger.warning(f"font load failed {path}: {e}")
        return ImageFont.load_default()


def _has_devanagari(text: str) -> bool:
    return any('\u0900' <= c <= '\u097F' for c in (text or ""))


def _pick_font(text: str, size: int, bold: bool = True):
    if _has_devanagari(text):
        return _font(DEVANAGARI_BOLD if bold else DEVANAGARI_REG, size)
    return _font(LATIN_BOLD if bold else LATIN_REG, size)


def _segment_by_script(text: str):
    """Split text into runs of (text, is_devanagari). Devanagari = `\\u0900-\\u097F`.
    ASCII / punctuation flows with the preceding segment to keep spacing natural.
    """
    if not text:
        return []
    runs = []
    cur_text = ""
    cur_dev = None
    for ch in text:
        is_dev = '\u0900' <= ch <= '\u097F'
        if cur_dev is None:
            cur_dev = is_dev
        if is_dev != cur_dev:
            if cur_text:
                runs.append((cur_text, cur_dev))
            cur_text = ch
            cur_dev = is_dev
        else:
            cur_text += ch
    if cur_text:
        runs.append((cur_text, cur_dev))
    return runs


def _draw_text_mixed(draw, x, y, text, size, fill, bold=True, shadow=None):
    """Draw a string that may contain BOTH Devanagari and Latin, using the
    correct font for each run. Returns the total width drawn."""
    runs = _segment_by_script(text)
    cx = x
    for run_text, is_dev in runs:
        if is_dev:
            f = _font(DEVANAGARI_BOLD if bold else DEVANAGARI_REG, size)
        else:
            f = _font(LATIN_BOLD if bold else LATIN_REG, size)
        if shadow:
            draw.text((cx + shadow[0], y + shadow[1]), run_text, font=f, fill=shadow[2])
        draw.text((cx, y), run_text, font=f, fill=fill)
        bb = draw.textbbox((0, 0), run_text, font=f)
        cx += (bb[2] - bb[0])
    return cx - x


def _measure_mixed(draw, text, size, bold=True):
    """Total width of a mixed-script string using per-run font."""
    runs = _segment_by_script(text)
    w = 0
    for run_text, is_dev in runs:
        if is_dev:
            f = _font(DEVANAGARI_BOLD if bold else DEVANAGARI_REG, size)
        else:
            f = _font(LATIN_BOLD if bold else LATIN_REG, size)
        bb = draw.textbbox((0, 0), run_text, font=f)
        w += (bb[2] - bb[0])
    return w


def _wrap_to_width(draw, text: str, font, max_w: int):
    """Word-wrap text to fit within max_w pixels. Returns list of lines.
    Falls back to mixed-script measurement if the text contains Devanagari
    so wrapping is accurate when scripts are mixed.
    """
    if not text:
        return []
    words = text.split()
    lines, cur = [], ""
    mixed = _has_devanagari(text)
    # Defensive: font.path can be a str OR a BytesIO (for default fonts).
    # Only call .lower() / .endswith() when it's actually a string.
    _path = getattr(font, "path", "")
    is_bold = (_path.lower().endswith("-bold.ttf")
               if isinstance(_path, str) and _path else True)
    size = font.size

    def _measure(s: str) -> int:
        if mixed:
            return _measure_mixed(draw, s, size, bold=is_bold)
        bb = draw.textbbox((0, 0), s, font=font)
        return bb[2] - bb[0]

    for w in words:
        test = (cur + " " + w).strip()
        if _measure(test) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _truncate_to_chars(text: str, max_chars: int = 60) -> str:
    """Hard-truncate a long string so it never overflows the canvas band."""
    if not text or len(text) <= max_chars:
        return text or ""
    cut = text[:max_chars].rstrip()
    # Trim trailing partial word
    if " " in cut[-12:]:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"


def _draw_pill_text(draw, text: str, font, x: int, y: int, w_max: int,
                    fg=WHITE, bg=DARK_BG, pad_x: int = 24, pad_y: int = 12,
                    radius: int = 14) -> int:
    """Draw a rounded pill behind a single line of text, return next y."""
    lines = _wrap_to_width(draw, text, font, w_max - 2 * pad_x)
    if not lines:
        return y
    line_h = font.size + 8
    block_h = line_h * len(lines) + 2 * pad_y
    # Estimate widest line for pill background sizing
    widest = max((draw.textbbox((0, 0), L, font=font)[2] for L in lines), default=0)
    bg_w = min(w_max, widest + 2 * pad_x)
    bg_x = x + (w_max - bg_w) // 2
    draw.rounded_rectangle(
        [bg_x, y, bg_x + bg_w, y + block_h],
        radius=radius, fill=bg,
    )
    cy = y + pad_y
    for L in lines:
        bb = draw.textbbox((0, 0), L, font=font)
        tw = bb[2] - bb[0]
        tx = bg_x + (bg_w - tw) // 2
        draw.text((tx, cy), L, font=font, fill=fg)
        cy += line_h
    return y + block_h + 8


def apply_overlay(
    img_bytes: bytes,
    headline_marathi: str = "",
    headline_english: str = "",
    byline: str = "",
    brand: str = "Purnabramha",
    logo_path: Optional[str] = None,
    position: str = "bottom",   # 'top' | 'bottom'
) -> bytes:
    """Overlay crisp text + logo on a pre-rendered visual using the official
    Purnabramha 2026 brand system.

    - Dark chocolate band with deep-maroon gradient (premium wedding-invitation feel)
    - Rich antique gold headings (large, serif)
    - Warm cream subtitle text
    - When BOTH Marathi + English provided, both are rendered (bilingual mode)
    """
    try:
        base = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    except Exception as e:
        logger.error(f"overlay: bad input image: {e}")
        return img_bytes

    W, H = base.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # ── Sanitise inputs — cap length so band cannot overflow the canvas ──
    headline_marathi = _truncate_to_chars(headline_marathi or "", 70)
    headline_english = _truncate_to_chars(headline_english or "", 110)
    byline = _truncate_to_chars(byline or "", 50)

    # If the same text appears in both fields (Claude returns identical text
    # for Bilingual without proper Marathi), drop the duplicate.
    if (headline_marathi.strip().lower() == headline_english.strip().lower()
            and not _has_devanagari(headline_marathi)):
        headline_marathi = ""

    # ── Sizing relative to image dimensions ───────────────────────────────
    scale = min(W, H) / 1080.0
    fs_marathi = int(82 * scale)        # large hero
    fs_english = int(40 * scale)        # subtitle scale (sentence-friendly)
    fs_byline = int(34 * scale)
    fs_brand = int(38 * scale)
    side_pad = int(W * 0.05)
    inner_w = W - 2 * side_pad
    block_pad = int(36 * scale)

    # ── Adaptive sizing — shrink fonts until everything fits 55% band ────
    MAX_BAND_RATIO = 0.55
    max_band_h = int(H * MAX_BAND_RATIO)
    MAX_LINES_M = 3
    MAX_LINES_E = 3

    def _layout(fs_m, fs_e):
        f_m = _pick_font(headline_marathi, fs_m, bold=True)
        f_e = _font(LATIN_ITALIC, fs_e)
        lines_m = _wrap_to_width(draw, headline_marathi, f_m,
                                 inner_w - 2 * block_pad)[:MAX_LINES_M]
        lines_e = _wrap_to_width(draw, headline_english, f_e,
                                 inner_w - 2 * block_pad)[:MAX_LINES_E]
        line_h_m = fs_m + 16
        line_h_e = fs_e + 12
        needed = (len(lines_m) * line_h_m
                  + (24 if lines_m and lines_e else 0)
                  + len(lines_e) * line_h_e
                  + (fs_byline + 18 if byline else 0)
                  + 2 * block_pad + fs_brand + 28)
        return f_m, f_e, lines_m, lines_e, line_h_m, line_h_e, needed

    f_m, f_e_italic, lines_m, lines_e, line_h_m, line_h_e, needed = _layout(
        fs_marathi, fs_english)
    # Shrink if overflow (up to 4 passes)
    shrink_pass = 0
    while needed > max_band_h and shrink_pass < 4:
        fs_marathi = int(fs_marathi * 0.88)
        fs_english = int(fs_english * 0.88)
        f_m, f_e_italic, lines_m, lines_e, line_h_m, line_h_e, needed = _layout(
            fs_marathi, fs_english)
        shrink_pass += 1
    band_h = min(max(needed, int(H * 0.22)), max_band_h)
    f_b = _pick_font(byline, fs_byline, bold=False)
    f_brand = _font(LATIN_BOLD, fs_brand)

    # ── Draw dark CHOCOLATE band with soft fade ───────────────────────────
    if position == "top":
        y0, y1 = 0, band_h
        steps = band_h
        for i in range(steps):
            alpha = int(235 * (1 - i / steps) ** 1.1)
            draw.rectangle([0, y0 + i, W, y0 + i + 1],
                           fill=(DARK_CHOCOLATE[0], DARK_CHOCOLATE[1], DARK_CHOCOLATE[2], alpha))
        text_y = block_pad + int(8 * scale)
    else:
        y0, y1 = H - band_h, H
        steps = band_h
        for i in range(steps):
            alpha = int(235 * (i / steps) ** 1.1)
            draw.rectangle([0, y0 + i, W, y0 + i + 1],
                           fill=(DARK_CHOCOLATE[0], DARK_CHOCOLATE[1], DARK_CHOCOLATE[2], alpha))
        text_y = y0 + block_pad + int(8 * scale)

    # ── Gold top-border + corner ornaments on the band ───────────────────
    border_y = y0 if position == "bottom" else y1
    draw.rectangle([0, border_y - 4 if position == "bottom" else border_y, W,
                    border_y if position == "bottom" else border_y + 4],
                   fill=ANTIQUE_GOLD)
    # Small paisley dots row centered just inside the band
    cx = W // 2
    dot_y = (y0 + int(20 * scale)) if position == "bottom" else (y1 - int(20 * scale))
    for dx in range(-4, 5):
        if dx == 0:
            draw.ellipse([cx - 6, dot_y - 6, cx + 6, dot_y + 6], fill=ANTIQUE_GOLD_BRIGHT)
        else:
            r = 3
            draw.ellipse([cx + dx * 22 - r, dot_y - r, cx + dx * 22 + r, dot_y + r],
                         fill=ANTIQUE_GOLD)
    if position == "bottom":
        text_y += int(20 * scale)

    # ── Headline (Marathi first, bold antique gold) ───────────────────────
    for L in lines_m:
        tw = _measure_mixed(draw, L, fs_marathi, bold=True)
        _draw_text_mixed(draw, (W - tw) // 2, text_y, L, fs_marathi,
                         ANTIQUE_GOLD_BRIGHT, bold=True,
                         shadow=(3, 3, (0, 0, 0, 200)))
        text_y += line_h_m
    if lines_m and lines_e:
        # Decorative thin divider between scripts
        text_y += 8
        dx0 = W // 2 - int(80 * scale)
        dx1 = W // 2 + int(80 * scale)
        dy = text_y
        draw.line([dx0, dy, dx1, dy], fill=ANTIQUE_GOLD, width=2)
        text_y += 16

    # ── Sub-headline (English, cream italic) ─────────────────────────────
    for L in lines_e:
        bb = draw.textbbox((0, 0), L, font=f_e_italic)
        tw = bb[2] - bb[0]
        tx = (W - tw) // 2
        draw.text((tx + 2, text_y + 2), L, font=f_e_italic, fill=(0, 0, 0, 170))
        draw.text((tx, text_y), L, font=f_e_italic, fill=WARM_CREAM)
        text_y += line_h_e

    # ── Byline ───────────────────────────────────────────────────────────
    if byline:
        text_y += 10
        bb = draw.textbbox((0, 0), byline, font=f_b)
        tw = bb[2] - bb[0]
        draw.text(((W - tw) // 2, text_y), byline, font=f_b, fill=WARM_CREAM_SOFT)
        text_y += fs_byline + 10

    # ── Brand line at the band's lower edge ──────────────────────────────
    brand_line = f"— {brand} —"
    bb = draw.textbbox((0, 0), brand_line, font=f_brand)
    bw = bb[2] - bb[0]
    bx = (W - bw) // 2
    if position == "top":
        by = band_h - fs_brand - 14
    else:
        by = y1 - fs_brand - 18
    draw.text((bx, by), brand_line, font=f_brand, fill=ANTIQUE_GOLD_BRIGHT)

    # ── Logo (top-right, transparent PNG — BIGGER for brand prominence) ──
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            target = int(min(W, H) * 0.18)
            logo.thumbnail((target, target), Image.LANCZOS)
            lx = W - logo.width - int(W * 0.035)
            ly = int(H * 0.035)
            layer.paste(logo, (lx, ly), logo)
        except Exception as e:
            logger.warning(f"logo paste failed: {e}")

    out = Image.alpha_composite(base, layer).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def apply_invitation_overlay(
    img_bytes: bytes,
    occasion: str,
    occasion_marathi: str,
    host_name: str,
    event_date: str,
    event_time: str,
    venue_name: str,
    venue_address: str = "",
    menu_highlights: str = "",
    custom_message: str = "",
    logo_path: Optional[str] = None,
    brand: str = "Purnabramha",
) -> bytes:
    """Render a PREMIUM wedding-invitation style info panel on the lower half
    of the AI background.

    Purnabramha 2026 brand system:
    - Dark chocolate full panel (luxurious card feel)
    - Antique gold double-frame border with corner ornaments
    - Cream typography, large + readable on mobile
    - Bilingual occasion line (Marathi + English)
    - Host name 96pt+ — the visual hero
    """
    try:
        base = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    except Exception as e:
        logger.error(f"invitation overlay: bad input: {e}")
        return img_bytes

    W, H = base.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    scale = min(W, H) / 1080.0
    side_pad = int(W * 0.05)
    inner_w = W - 2 * side_pad

    # ── Panel covers bottom ~55% (premium wedding-card feel) ───────────────
    panel_top = int(H * 0.45)
    panel_h = H - panel_top - side_pad
    # Solid DARK CHOCOLATE panel (no transparency — luxe card)
    panel = Image.new("RGBA", (inner_w, panel_h), DARK_CHOCOLATE_RGBA)
    layer.paste(panel, (side_pad, panel_top), panel)

    # ── Double ANTIQUE GOLD border ────────────────────────────────────────
    draw.rounded_rectangle(
        [side_pad, panel_top, side_pad + inner_w, H - side_pad],
        radius=20, outline=ANTIQUE_GOLD_BRIGHT, width=4,
    )
    draw.rounded_rectangle(
        [side_pad + 14, panel_top + 14, side_pad + inner_w - 14, H - side_pad - 14],
        radius=14, outline=ANTIQUE_GOLD, width=2,
    )

    # ── Decorative corner ornaments (paisley dots) ────────────────────────
    for cx, cy in [(side_pad + 30, panel_top + 30),
                   (side_pad + inner_w - 30, panel_top + 30),
                   (side_pad + 30, H - side_pad - 30),
                   (side_pad + inner_w - 30, H - side_pad - 30)]:
        for r in [10, 6, 3]:
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                         outline=ANTIQUE_GOLD_BRIGHT, width=2)

    y = panel_top + int(54 * scale)

    # ── Occasion line (Bilingual: Marathi + English) ──────────────────────
    occ_marathi = (occasion_marathi or "").strip()
    occ_english = (occasion or "").strip()
    if occ_marathi:
        f_occ_m = _pick_font(occ_marathi, int(64 * scale), bold=True)
        for L in _wrap_to_width(draw, occ_marathi, f_occ_m, inner_w - 80):
            bb = draw.textbbox((0, 0), L, font=f_occ_m); tw = bb[2] - bb[0]
            draw.text(((W - tw) // 2 + 2, y + 2), L, font=f_occ_m, fill=(0, 0, 0, 130))
            draw.text(((W - tw) // 2, y), L, font=f_occ_m, fill=ANTIQUE_GOLD_BRIGHT)
            y += f_occ_m.size + 10
    if occ_english:
        f_occ_e = _font(LATIN_ITALIC, int(42 * scale))
        line = f"{occ_english} Celebration"
        bb = draw.textbbox((0, 0), line, font=f_occ_e); tw = bb[2] - bb[0]
        draw.text(((W - tw) // 2, y), line, font=f_occ_e, fill=WARM_CREAM)
        y += f_occ_e.size + 10

    # ── Paisley divider ───────────────────────────────────────────────────
    y += int(14 * scale)
    cx = W // 2
    for dx in range(-3, 4):
        r = 5 if dx == 0 else 3
        draw.ellipse([cx + dx * 18 - r, y, cx + dx * 18 + r, y + 2 * r], fill=ANTIQUE_GOLD_BRIGHT)
    y += int(34 * scale)

    # ── Host name (LARGEST text — visual hero) ────────────────────────────
    f_host = _pick_font(host_name, int(112 * scale), bold=True)
    for L in _wrap_to_width(draw, host_name, f_host, inner_w - 80):
        bb = draw.textbbox((0, 0), L, font=f_host); tw = bb[2] - bb[0]
        # Triple-shadow for depth
        draw.text(((W - tw) // 2 + 4, y + 4), L, font=f_host, fill=(0, 0, 0, 220))
        draw.text(((W - tw) // 2, y), L, font=f_host, fill=ANTIQUE_GOLD_BRIGHT)
        y += f_host.size + 10

    y += int(34 * scale)
    # ── Date / Time (premium serif, cream) ────────────────────────────────
    dt_line = f"{event_date}    ·    {event_time}"
    f_dt = _font(LATIN_BOLD, int(54 * scale))
    bb = draw.textbbox((0, 0), dt_line, font=f_dt); tw = bb[2] - bb[0]
    draw.text(((W - tw) // 2, y), dt_line, font=f_dt, fill=WARM_CREAM)
    y += f_dt.size + int(28 * scale)

    # ── Venue ─────────────────────────────────────────────────────────────
    f_venue = _font(LATIN_BOLD, int(44 * scale))
    bb = draw.textbbox((0, 0), venue_name, font=f_venue); tw = bb[2] - bb[0]
    draw.text(((W - tw) // 2, y), venue_name, font=f_venue, fill=ANTIQUE_GOLD_BRIGHT)
    y += f_venue.size + 8
    if venue_address:
        f_addr = _font(LATIN_REG, int(32 * scale))
        for L in _wrap_to_width(draw, venue_address, f_addr, inner_w - 100):
            bb = draw.textbbox((0, 0), L, font=f_addr); tw = bb[2] - bb[0]
            draw.text(((W - tw) // 2, y), L, font=f_addr, fill=WARM_CREAM_SOFT)
            y += f_addr.size + 6

    # ── Menu highlights ───────────────────────────────────────────────────
    if menu_highlights:
        y += int(22 * scale)
        label = "Featured Menu · विशेष पंगत"
        label_size = int(32 * scale)
        tw = _measure_mixed(draw, label, label_size, bold=True)
        _draw_text_mixed(draw, (W - tw) // 2, y, label, label_size,
                         ANTIQUE_GOLD, bold=True)
        y += label_size + 10
        f_menu = _pick_font(menu_highlights, int(32 * scale), bold=False)
        for L in _wrap_to_width(draw, menu_highlights, f_menu, inner_w - 120):
            bb = draw.textbbox((0, 0), L, font=f_menu); tw = bb[2] - bb[0]
            draw.text(((W - tw) // 2, y), L, font=f_menu, fill=WARM_CREAM)
            y += f_menu.size + 4

    # ── Custom message (italic) ───────────────────────────────────────────
    if custom_message:
        y += int(22 * scale)
        f_msg = _pick_font(custom_message, int(34 * scale), bold=False)
        for L in _wrap_to_width(draw, custom_message, f_msg, inner_w - 140):
            bb = draw.textbbox((0, 0), L, font=f_msg); tw = bb[2] - bb[0]
            draw.text(((W - tw) // 2, y), f'"{L}"', font=f_msg, fill=WARM_CREAM_SOFT)
            y += f_msg.size + 4

    # ── Brand footer (bilingual — separate lines, no overlap) ─────────────
    brand_size = int(32 * scale)
    brand_line_en = f"— With warm regards · {brand} —"
    brand_line_mr = "— पुर्णब्रह्म परिवाराकडून प्रेमपूर्वक —"

    # Total height: Marathi line + gap + English line
    line_gap = int(brand_size * 1.45)
    block_h = line_gap * 2
    # Anchor block at the bottom of the panel, above the inner gold border
    block_top = H - side_pad - 30 - block_h

    # Marathi first (gold-bright, larger emphasis)
    twm = _measure_mixed(draw, brand_line_mr, brand_size, bold=True)
    _draw_text_mixed(draw, (W - twm) // 2, block_top, brand_line_mr,
                     brand_size, ANTIQUE_GOLD_BRIGHT, bold=True,
                     shadow=(2, 2, (0, 0, 0, 150)))
    # English below
    tw = _measure_mixed(draw, brand_line_en, brand_size, bold=True)
    _draw_text_mixed(draw, (W - tw) // 2, block_top + line_gap, brand_line_en,
                     brand_size, ANTIQUE_GOLD, bold=True)

    # ── Big top-right logo (transparent PNG, prominent brand mark) ────────
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            target = int(W * 0.24)
            logo.thumbnail((target, target), Image.LANCZOS)
            lx = W - logo.width - int(W * 0.04)
            ly = int(H * 0.035)
            layer.paste(logo, (lx, ly), logo)
        except Exception:
            pass

    out = Image.alpha_composite(base, layer).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# Marathi labels for common occasions — used by apply_invitation_overlay
OCCASION_MARATHI = {
    "Wedding": "लग्न सोहळा",
    "Engagement": "साखरपुडा",
    "Anniversary": "वर्धापन दिन",
    "Birthday": "वाढदिवस",
    "Baby Shower": "डोहाळेजेवण",
    "Get-together": "स्नेहसंमेलन",
    "Corporate": "कॉर्पोरेट सोहळा",
    "Festival": "उत्सव",
    "Dohal Jevan": "डोहाळेजेवण",
    "Upanayan": "मुंज सोहळा",
    "Naming Ceremony": "बारसे",
    "Retirement Function": "निवृत्ती सोहळा",
    "Family Gathering": "कुटुंब मेळावा",
}


def render_text_only_card(
    headline_marathi: str = "",
    headline_english: str = "",
    byline: str = "",
    brand: str = "Purnabramha",
    logo_path: Optional[str] = None,
    size: Tuple[int, int] = (1080, 1080),
    bg_color: Tuple[int, int, int] = CREAM,
) -> bytes:
    """Fallback poster — solid brand background + crisp text. Used when the
    AI image generation fails."""
    W, H = size
    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img, "RGBA")
    # Decorative border
    draw.rectangle([20, 20, W - 20, H - 20], outline=GOLD, width=4)
    draw.rectangle([40, 40, W - 40, H - 40], outline=GOLD, width=1)
    scale = min(W, H) / 1080.0
    f_m = _pick_font(headline_marathi, int(64 * scale), bold=True)
    f_e = _font(LATIN_ITALIC, int(38 * scale))
    f_b = _font(LATIN_BOLD, int(28 * scale))

    y = int(H * 0.42)
    for L in _wrap_to_width(draw, headline_marathi, f_m, int(W * 0.85)):
        bb = draw.textbbox((0, 0), L, font=f_m); tw = bb[2] - bb[0]
        draw.text(((W - tw) // 2, y), L, font=f_m, fill=MAROON)
        y += f_m.size + 14
    y += 10
    for L in _wrap_to_width(draw, headline_english, f_e, int(W * 0.85)):
        bb = draw.textbbox((0, 0), L, font=f_e); tw = bb[2] - bb[0]
        draw.text(((W - tw) // 2, y), L, font=f_e, fill=GOLD)
        y += f_e.size + 8
    if byline:
        y += 12
        bb = draw.textbbox((0, 0), byline, font=f_b); tw = bb[2] - bb[0]
        draw.text(((W - tw) // 2, y), byline, font=f_b, fill=(120, 80, 0))

    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo.thumbnail((int(W * 0.22), int(W * 0.22)))
            img.paste(logo, ((W - logo.width) // 2, int(H * 0.10)), logo if logo.mode == "RGBA" else None)
        except Exception:
            pass
    brand_line = f"— {brand} —"
    bb = draw.textbbox((0, 0), brand_line, font=f_b); tw = bb[2] - bb[0]
    draw.text(((W - tw) // 2, H - 80), brand_line, font=f_b, fill=GOLD)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()



# ═════════════════════════════════════════════════════════════════════════════
# PREMIUM AD COMPOSER  (golden-reference layout — deterministic + reliable)
# ═════════════════════════════════════════════════════════════════════════════
# Produces ads that mirror the user's golden references:
#   • Deep maroon (or chocolate / cream) LEFT vertical panel
#     - Real guest photo at top (cream frame, gold inner border, NO cropping)
#     - Circular Purnabramha logo below the photo
#   • RIGHT 60% = AI-generated full-bleed food photo (varied each generation)
#   • TOP-RIGHT corner = Marathi heading (gold serif) + English subtitle (cream
#     italic) + " — BYLINE —" small caps — drawn on a soft cream pill so it
#     reads on any background.
#   • Thin chocolate strip at the very bottom: "Purnabramha — Authentic
#     Maharashtrian Cuisine"
#
# Variation is achieved via SCENE_ARCHETYPES — the left panel rotates between
# deep-maroon / chocolate / paisley-cream styles for fresh feel each ad.
# ═════════════════════════════════════════════════════════════════════════════

import random as _random
import math as _math

SCENE_ARCHETYPES = [
    # (panel_fill, accent, text_pill_fill, text_pill_alpha)
    ("maroon_paisley",  DEEP_MAROON,    ANTIQUE_GOLD_BRIGHT, WARM_CREAM,   235),
    ("chocolate_solid", DARK_CHOCOLATE, ANTIQUE_GOLD_BRIGHT, WARM_CREAM,   235),
    ("maroon_solid",    DEEP_MAROON,    ANTIQUE_GOLD,        WARM_CREAM,   240),
    ("chocolate_warm",  (60, 30, 22),   ANTIQUE_GOLD_BRIGHT, WARM_CREAM,   230),
]


def _draw_paisley_pattern(draw: ImageDraw.ImageDraw, x0, y0, x1, y1, color, alpha=40):
    """Sprinkle faint paisley/dot motif inside the rectangle (subtle texture)."""
    import random as _rnd
    rng = _rnd.Random(42)  # deterministic per call
    w = x1 - x0
    h = y1 - y0
    for _ in range(int(w * h / 9000)):
        cx = rng.randint(x0, x1)
        cy = rng.randint(y0, y1)
        r = rng.randint(3, 8)
        a = rng.randint(30, alpha)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     fill=(color[0], color[1], color[2], a))


def _draw_circle_logo(layer: Image.Image, logo_path: str, cx: int, cy: int,
                      diameter: int) -> None:
    """Paste the Purnabramha logo as a circular medallion centered at (cx, cy)."""
    if not (logo_path and os.path.exists(logo_path)):
        return
    try:
        logo = Image.open(logo_path).convert("RGBA")
        # Fit logo inside a square; then mask to circle
        logo.thumbnail((diameter, diameter), Image.LANCZOS)
        # Square canvas with cream backdrop, then circular crop
        sq = Image.new("RGBA", (diameter, diameter), (250, 240, 220, 255))
        sq.paste(logo, ((diameter - logo.width) // 2,
                        (diameter - logo.height) // 2), logo)
        mask = Image.new("L", (diameter, diameter), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, diameter, diameter], fill=255)
        # Gold ring around the circle
        ring = Image.new("RGBA", (diameter + 16, diameter + 16), (0, 0, 0, 0))
        rd = ImageDraw.Draw(ring)
        rd.ellipse([0, 0, diameter + 16, diameter + 16], fill=ANTIQUE_GOLD_BRIGHT)
        rd.ellipse([8, 8, diameter + 8, diameter + 8], fill=(0, 0, 0, 0))
        # Compose: ring under, then masked logo on top
        layer.paste(ring, (cx - (diameter + 16) // 2, cy - (diameter + 16) // 2), ring)
        layer.paste(sq, (cx - diameter // 2, cy - diameter // 2), mask)
    except Exception as e:
        logger.warning(f"_draw_circle_logo failed: {e}")


def _draw_text_block(
    layer: Image.Image,
    box: tuple,                # (x0, y0, x1, y1) bounding box
    marathi: str,
    english: str,
    byline: str,
    pill_fill: tuple,           # rgba
) -> None:
    """Draw the Marathi heading + English subtitle + small-caps byline inside
    `box`. Adds a soft semi-transparent pill behind the text so it reads on
    ANY background. Auto-shrinks fonts to fit."""
    x0, y0, x1, y1 = box
    W = x1 - x0
    H = y1 - y0
    if W < 100 or H < 80:
        return
    pad_x = int(W * 0.06)
    pad_y = int(H * 0.10)
    inner_w = W - 2 * pad_x
    inner_h = H - 2 * pad_y

    draw = ImageDraw.Draw(layer)

    # Sanitise lengths — shorter to fit the compact pill
    marathi = _truncate_to_chars((marathi or "").strip(), 50)
    english = _truncate_to_chars((english or "").strip(), 70)
    byline = _truncate_to_chars((byline or "").strip(), 26)

    # Initial sizes (relative to box height)
    fs_m = int(H * 0.18)
    fs_e = int(H * 0.085)
    fs_b = int(H * 0.07)

    # Iteratively shrink until everything fits inner_w / inner_h
    for _ in range(8):
        f_m = _pick_font(marathi, fs_m, bold=True)
        f_e = _font(LATIN_ITALIC, fs_e)
        f_b = _font(LATIN_BOLD, fs_b)
        lines_m = _wrap_to_width(draw, marathi, f_m, inner_w)[:3] if marathi else []
        lines_e = _wrap_to_width(draw, english, f_e, inner_w)[:2] if english else []
        line_h_m = int(fs_m * 1.18)
        line_h_e = int(fs_e * 1.25)
        total_h = (
            len(lines_m) * line_h_m
            + (int(fs_m * 0.25) if lines_m and lines_e else 0)
            + len(lines_e) * line_h_e
            + (fs_b + int(fs_b * 0.6) if byline else 0)
        )
        max_line_w = 0
        for L in lines_m:
            max_line_w = max(max_line_w, _measure_mixed(draw, L, fs_m, bold=True))
        for L in lines_e:
            bb = draw.textbbox((0, 0), L, font=f_e)
            max_line_w = max(max_line_w, bb[2] - bb[0])
        if total_h <= inner_h and max_line_w <= inner_w:
            break
        fs_m = int(fs_m * 0.9)
        fs_e = int(fs_e * 0.9)
        fs_b = int(fs_b * 0.9)
        if fs_m < 22:
            break

    # Soft cream pill background (semi-transparent so AI bg colors show through)
    pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pill)
    pd.rounded_rectangle([0, 0, W, H], radius=int(min(W, H) * 0.08), fill=pill_fill)
    layer.paste(pill, (x0, y0), pill)

    # Render text on top
    text_y = y0 + pad_y
    for L in lines_m:
        tw = _measure_mixed(draw, L, fs_m, bold=True)
        tx = x0 + (W - tw) // 2
        # Subtle shadow
        _draw_text_mixed(draw, tx, text_y, L, fs_m,
                         DEEP_MAROON, bold=True,
                         shadow=(2, 2, (0, 0, 0, 60)))
        text_y += line_h_m
    if lines_m and lines_e:
        text_y += int(fs_m * 0.18)
        # Thin gold divider
        cx = x0 + W // 2
        draw.line([cx - int(W * 0.12), text_y, cx + int(W * 0.12), text_y],
                  fill=ANTIQUE_GOLD, width=2)
        text_y += int(fs_m * 0.12)
    for L in lines_e:
        f_e = _font(LATIN_ITALIC, fs_e)
        bb = draw.textbbox((0, 0), L, font=f_e)
        tw = bb[2] - bb[0]
        tx = x0 + (W - tw) // 2
        draw.text((tx, text_y), L, font=f_e, fill=DARK_CHOCOLATE)
        text_y += line_h_e
    if byline:
        text_y += int(fs_b * 0.4)
        bline = f"— {byline.upper()} —"
        f_b = _font(LATIN_BOLD, fs_b)
        bb = draw.textbbox((0, 0), bline, font=f_b)
        tw = bb[2] - bb[0]
        tx = x0 + (W - tw) // 2
        draw.text((tx, text_y), bline, font=f_b, fill=ANTIQUE_GOLD)


def _paste_guest_photo_framed(
    layer: Image.Image,
    photo_bytes: bytes,
    box: tuple,                # (x0, y0, x1, y1)
    is_group: bool = False,
    balgopal: bool = False,
) -> None:
    """Paste the guest photo inside `box` with a cream card frame and gold
    inner border. Contain-fit (no cropping) when is_group, otherwise cover-fit."""
    x0, y0, x1, y1 = box
    box_w = x1 - x0
    box_h = y1 - y0
    if box_w < 50 or box_h < 50:
        return
    photo = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
    gw, gh = photo.size
    if is_group or (gw / max(gh, 1)) >= 1.3:
        scale = min(box_w / gw, box_h / gh)
        new_w, new_h = int(gw * scale), int(gh * scale)
        photo_scaled = photo.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new("RGBA", (box_w, box_h), (253, 246, 231, 255))
        canvas.paste(photo_scaled,
                     ((box_w - new_w) // 2, (box_h - new_h) // 2),
                     photo_scaled)
        photo_fit = canvas
    else:
        scale = max(box_w / gw, box_h / gh)
        new_w, new_h = int(gw * scale), int(gh * scale)
        photo_scaled = photo.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - box_w) // 2
        top = (new_h - box_h) // 2
        photo_fit = photo_scaled.crop((left, top, left + box_w, top + box_h))

    # Drop shadow
    shadow = Image.new("RGBA", (box_w + 24, box_h + 24), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([6, 6, box_w + 18, box_h + 18],
                         radius=14, fill=(0, 0, 0, 130))
    try:
        from PIL import ImageFilter
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))
    except Exception:
        pass
    layer.paste(shadow, (x0 - 6, y0 - 6), shadow)

    # Balgopal gold burst
    if balgopal:
        try:
            star = Image.new("RGBA", (box_w + 100, box_h + 100), (0, 0, 0, 0))
            sd2 = ImageDraw.Draw(star)
            cx, cy = star.width // 2, star.height // 2
            for i in range(16):
                ang = (_math.pi / 8) * i
                outer = (cx + int(_math.cos(ang) * (star.width // 2 + 20)),
                         cy + int(_math.sin(ang) * (star.height // 2 + 20)))
                sd2.line([cx, cy, outer[0], outer[1]],
                         fill=(220, 175, 60, 100 if i % 2 else 160),
                         width=14 if i % 2 else 22)
            from PIL import ImageFilter
            star = star.filter(ImageFilter.GaussianBlur(radius=5))
            layer.paste(star, (x0 - 50, y0 - 50), star)
        except Exception:
            pass

    # Cream card frame
    draw = ImageDraw.Draw(layer)
    frame_pad = 10
    draw.rounded_rectangle(
        [x0 - frame_pad, y0 - frame_pad, x1 + frame_pad, y1 + frame_pad],
        radius=18, fill=(253, 246, 231, 255),
    )
    # Mask the photo with rounded corners
    mask = Image.new("L", (box_w, box_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, box_w, box_h],
                                           radius=12, fill=255)
    layer.paste(photo_fit, (x0, y0), mask)
    # Gold inner border
    draw.rounded_rectangle([x0 - 2, y0 - 2, x1 + 2, y1 + 2],
                           radius=14, outline=ANTIQUE_GOLD_BRIGHT, width=4)
    draw.rounded_rectangle([x0 + 2, y0 + 2, x1 - 2, y1 - 2],
                           radius=10, outline=ANTIQUE_GOLD, width=1)


def compose_premium_ad(
    food_bg_bytes: bytes,
    guest_photo_bytes: Optional[bytes],
    *,
    aspect: str = "1:1",
    headline_marathi: str = "",
    headline_english: str = "",
    byline: str = "",
    brand: str = "Purnabramha — Authentic Maharashtrian Cuisine",
    logo_path: Optional[str] = None,
    is_group: bool = False,
    balgopal: bool = False,
    scene_seed: Optional[int] = None,
) -> bytes:
    """Compose the FINAL premium ad — golden-reference layout.

    The AI food image (`food_bg_bytes`) is treated as a building block; the
    layout is built deterministically in Pillow so the photo, logo, text and
    brand strip are ALWAYS present and correctly placed.

    Raises:
        ValueError if `food_bg_bytes` cannot be opened.
    """
    food = Image.open(io.BytesIO(food_bg_bytes)).convert("RGBA")
    food_w, food_h = food.size

    # ── Decide final canvas size based on aspect ──────────────────────────
    aspect_map = {"1:1": (1600, 1600), "4:5": (1280, 1600), "9:16": (1080, 1920)}
    W, H = aspect_map.get(aspect, aspect_map["1:1"])
    canvas = Image.new("RGBA", (W, H), (250, 240, 220, 255))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # ── Pick scene archetype (variety per generation) ──────────────────────
    rng = _random.Random(scene_seed if scene_seed is not None else _random.randint(0, 10**9))
    scene = rng.choice(SCENE_ARCHETYPES)
    _scene_name, panel_color, accent, pill_color, pill_alpha = scene
    pill_fill = (pill_color[0], pill_color[1], pill_color[2], pill_alpha)

    # ── Layout regions per aspect ─────────────────────────────────────────
    BRAND_STRIP_H = max(64, int(H * 0.045))

    if aspect == "9:16":
        # Vertical: TOP 50% = brand panel (photo + logo on side), BOTTOM 50% = food
        panel_h = int(H * 0.50)
        panel_box = (0, 0, W, panel_h)
        food_box = (0, panel_h, W, H - BRAND_STRIP_H)
        # Guest photo: top-left of panel
        ph_pad = int(W * 0.05)
        ph_w = int(W * 0.45)
        ph_h = int(panel_h * 0.70)
        photo_box = (ph_pad, ph_pad, ph_pad + ph_w, ph_pad + ph_h)
        # Logo: right of photo
        logo_d = int(panel_h * 0.42)
        logo_center = (W - ph_pad - logo_d // 2 - 10, ph_pad + ph_h // 2)
        # Text block: bottom of panel, full width
        text_box = (ph_pad, ph_pad + ph_h + 24, W - ph_pad, panel_h - 24)
    else:
        # 1:1 / 4:5: LEFT 38% = panel, RIGHT 62% = food
        panel_w = int(W * 0.38)
        panel_box = (0, 0, panel_w, H - BRAND_STRIP_H)
        food_box = (panel_w, 0, W, H - BRAND_STRIP_H)
        # Photo: top half of panel
        ph_pad = int(panel_w * 0.10)
        ph_top = int(H * 0.06)
        ph_w = panel_w - 2 * ph_pad
        ph_h = int(H * 0.42)
        photo_box = (ph_pad, ph_top, ph_pad + ph_w, ph_top + ph_h)
        # Logo: centered below the photo
        logo_d = int(panel_w * 0.50)
        logo_center = (panel_w // 2, ph_top + ph_h + int(H * 0.04) + logo_d // 2)
        # Text block: top-right corner over the food image
        text_pad = int(W * 0.03)
        text_w = int((W - panel_w) * 0.86)
        text_h = int(H * 0.34)
        text_box = (panel_w + text_pad,
                    int(H * 0.05),
                    panel_w + text_pad + text_w,
                    int(H * 0.05) + text_h)

    # ── 1) FOOD background (right / bottom) ───────────────────────────────
    fb_x0, fb_y0, fb_x1, fb_y1 = food_box
    fb_w = fb_x1 - fb_x0
    fb_h = fb_y1 - fb_y0
    # Cover-fit the AI food image into food_box
    fscale = max(fb_w / food_w, fb_h / food_h)
    nw, nh = int(food_w * fscale), int(food_h * fscale)
    food_scaled = food.resize((nw, nh), Image.LANCZOS)
    left = (nw - fb_w) // 2
    top = (nh - fb_h) // 2
    food_fit = food_scaled.crop((left, top, left + fb_w, top + fb_h))
    canvas.paste(food_fit, (fb_x0, fb_y0))

    # ── 2) LEFT panel (solid maroon/chocolate with subtle paisley) ────────
    pb_x0, pb_y0, pb_x1, pb_y1 = panel_box
    panel_layer = Image.new("RGBA", (pb_x1 - pb_x0, pb_y1 - pb_y0),
                            (panel_color[0], panel_color[1], panel_color[2], 255))
    pd = ImageDraw.Draw(panel_layer)
    # Faint paisley
    _draw_paisley_pattern(pd, 0, 0, pb_x1 - pb_x0, pb_y1 - pb_y0,
                          accent, alpha=42)
    # Soft right-edge gold divider (only when panel is on the LEFT)
    if aspect != "9:16":
        pd.rectangle([pb_x1 - pb_x0 - 4, 0, pb_x1 - pb_x0, pb_y1 - pb_y0],
                     fill=ANTIQUE_GOLD)
    else:
        pd.rectangle([0, pb_y1 - pb_y0 - 4, pb_x1 - pb_x0, pb_y1 - pb_y0],
                     fill=ANTIQUE_GOLD)
    canvas.paste(panel_layer, (pb_x0, pb_y0), panel_layer)

    # ── 3) Guest photo on panel ───────────────────────────────────────────
    if guest_photo_bytes:
        try:
            _paste_guest_photo_framed(
                layer, guest_photo_bytes, photo_box,
                is_group=is_group, balgopal=balgopal,
            )
        except Exception as e:
            logger.error(f"compose_premium_ad: guest photo failed: {e}", exc_info=True)
            # Hard fallback: draw a cream "Guest" tile so we never have a gap
            x0, y0, x1, y1 = photo_box
            draw.rounded_rectangle([x0, y0, x1, y1], radius=14,
                                   fill=(253, 246, 231, 255),
                                   outline=ANTIQUE_GOLD_BRIGHT, width=4)
            f = _font(LATIN_BOLD, int((y1 - y0) * 0.18))
            txt = "Guest"
            bb = draw.textbbox((0, 0), txt, font=f)
            tw = bb[2] - bb[0]; th = bb[3] - bb[1]
            draw.text((x0 + ((x1 - x0) - tw) // 2,
                       y0 + ((y1 - y0) - th) // 2),
                      txt, font=f, fill=DEEP_MAROON)
    else:
        # No photo provided — leave a decorative emblem in its place
        x0, y0, x1, y1 = photo_box
        cx = (x0 + x1) // 2; cy = (y0 + y1) // 2
        r = min(x1 - x0, y1 - y0) // 3
        for rr in [r, int(r * 0.75), int(r * 0.5)]:
            draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                         outline=ANTIQUE_GOLD_BRIGHT, width=3)

    # ── 4) Circular logo medallion ────────────────────────────────────────
    if logo_path:
        _draw_circle_logo(layer, logo_path, logo_center[0], logo_center[1],
                          logo_d)

    # ── 5) Marathi + English text block on cream pill ─────────────────────
    _draw_text_block(layer, text_box, headline_marathi, headline_english,
                     byline, pill_fill)

    # ── 6) Thin brand strip at the bottom ─────────────────────────────────
    strip_y0 = H - BRAND_STRIP_H
    draw.rectangle([0, strip_y0, W, H], fill=DARK_CHOCOLATE)
    draw.rectangle([0, strip_y0, W, strip_y0 + 3], fill=ANTIQUE_GOLD_BRIGHT)
    f_brand = _font(LATIN_BOLD, int(BRAND_STRIP_H * 0.42))
    line = "Purnabramha  —  Authentic Maharashtrian Cuisine"
    bb = draw.textbbox((0, 0), line, font=f_brand)
    tw = bb[2] - bb[0]; th = bb[3] - bb[1]
    # Shrink if too wide
    fb_size = int(BRAND_STRIP_H * 0.42)
    while tw > W - 40 and fb_size > 14:
        fb_size = int(fb_size * 0.92)
        f_brand = _font(LATIN_BOLD, fb_size)
        bb = draw.textbbox((0, 0), line, font=f_brand)
        tw = bb[2] - bb[0]; th = bb[3] - bb[1]
    tx = (W - tw) // 2
    ty = strip_y0 + (BRAND_STRIP_H - th) // 2 - 4
    draw.text((tx, ty), line, font=f_brand, fill=WARM_CREAM)

    out = Image.alpha_composite(canvas, layer).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()



# ═════════════════════════════════════════════════════════════════════════════
# SMART BRAND OVERLAY  (free-flow AI creative + RELIABLE text/logo/brand strip)
# ═════════════════════════════════════════════════════════════════════════════
# Philosophy: Nano Banana composes the FULL creative however it wants — varied
# layouts, framing, panels, motifs each generation. We only add three things
# on top, intelligently positioned:
#   1) The bilingual caption on a soft cream pill in the CALMEST corner
#   2) The circular Purnabramha logo medallion in the OPPOSITE calm corner
#   3) A thin chocolate brand strip at the very bottom: "Purnabramha — …"
# Both #1 and #2 are tested-for-visibility against the underlying pixels and
# placed where they pop the most. Never silent-fails.
# ═════════════════════════════════════════════════════════════════════════════


def _corner_calmness(img: Image.Image, region: tuple) -> float:
    """Score how "calm" a rectangular region is for overlay placement.

    Calm = high uniformity (low edge density) + medium luminance + low
    saturation (avoid decorative gold paisley areas). Lower score = calmer.
    """
    x0, y0, x1, y1 = region
    crop = img.crop((x0, y0, x1, y1))
    thumb_rgb = crop.resize((48, 48), Image.LANCZOS).convert("RGB")
    thumb_l = thumb_rgb.convert("L")
    lum = list(thumb_l.getdata())
    if not lum:
        return 9_999.0
    mean_l = sum(lum) / len(lum)
    var_l = sum((p - mean_l) ** 2 for p in lum) / len(lum)
    # Saturation proxy: average (max(r,g,b) - min(r,g,b)) on the RGB thumb
    rgb_pixels = list(thumb_rgb.getdata())
    sat = sum(max(r, g, b) - min(r, g, b) for r, g, b in rgb_pixels) / len(rgb_pixels)
    # Prefer mid-tones, low variance, low saturation
    extreme = min(abs(mean_l - 80), abs(mean_l - 200))
    return var_l + extreme * 0.3 + sat * 1.8


def _pick_corners(img: Image.Image, aspect: str) -> dict:
    """Return rectangles (x0,y0,x1,y1) for the BEST text and logo corners.

    Strategy:
    - Text pill is SMALL (≤ 36% width × ≤ 14% height) — never extends into the
      center where people/food usually live.
    - We evaluate ALL FOUR corner candidates and pick the calmest for text;
      the logo lands in the geometrically opposite corner (visual balance).
    - Excludes the bottom band (brand strip lives there).
    """
    W, H = img.size
    pad = int(min(W, H) * 0.025)

    if aspect == "9:16":
        text_w = int(W * 0.58)
        text_h = int(H * 0.14)
        logo_d = int(min(W, H) * 0.18)
    else:
        text_w = int(W * 0.38)
        text_h = int(H * 0.17)
        logo_d = int(min(W, H) * 0.14)

    # Text-pill candidates — four corners
    bottom_anchor = int(H * 0.86)   # above the brand strip
    text_candidates = {
        "TR": (W - text_w - pad, pad, W - pad, pad + text_h),
        "TL": (pad, pad, pad + text_w, pad + text_h),
        "BR": (W - text_w - pad, bottom_anchor - text_h, W - pad, bottom_anchor),
        "BL": (pad, bottom_anchor - text_h, pad + text_w, bottom_anchor),
    }

    # Score each
    scores = {k: _corner_calmness(img, v) for k, v in text_candidates.items()}
    best_text_key = min(scores, key=scores.get)
    text_box = text_candidates[best_text_key]

    # Logo goes in the OPPOSITE corner (diagonal)
    opposite = {"TR": "BL", "TL": "BR", "BR": "TL", "BL": "TR"}
    logo_key = opposite[best_text_key]
    logo_anchor_map = {
        "TR": (W - logo_d - pad, pad, W - pad, pad + logo_d),
        "TL": (pad, pad, pad + logo_d, pad + logo_d),
        "BR": (W - logo_d - pad, bottom_anchor - logo_d, W - pad, bottom_anchor),
        "BL": (pad, bottom_anchor - logo_d, pad + logo_d, bottom_anchor),
    }
    logo_box = logo_anchor_map[logo_key]

    return {"text": text_box, "logo": logo_box,
            "text_corner": best_text_key, "logo_corner": logo_key}


def apply_smart_brand_overlay(
    img_bytes: bytes,
    *,
    headline_marathi: str = "",
    headline_english: str = "",
    byline: str = "",
    brand: str = "Purnabramha — Authentic Maharashtrian Cuisine",
    logo_path: Optional[str] = None,
) -> bytes:
    """Add bilingual caption + circular logo + thin brand strip on top of
    a FREE-FLOW AI advertisement. Layout untouched — we only overlay.

    - The bilingual caption goes on a soft semi-transparent CREAM PILL in the
      calmest top corner (auto-detected).
    - The circular Purnabramha logo medallion goes in the opposite corner.
    - A thin chocolate brand strip runs along the very bottom (~5% of height).

    Raises:
        ValueError if `img_bytes` cannot be opened.
    """
    base = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    W, H = base.size

    # Aspect heuristic
    if H >= W * 1.5:
        aspect = "9:16"
    elif W * 1.1 >= H >= W * 0.95:
        aspect = "1:1"
    else:
        aspect = "4:5"

    # Reserve bottom 5% for brand strip — exclude that band from corner scoring
    BRAND_STRIP_H = max(56, int(H * 0.05))
    scoring_img = base.crop((0, 0, W, H - BRAND_STRIP_H))
    corners = _pick_corners(scoring_img, aspect)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # ── 1) Bilingual caption on cream pill ───────────────────────────────
    pill_fill = (250, 240, 220, 235)  # warm cream, semi-transparent
    _draw_text_block(
        layer, corners["text"],
        headline_marathi, headline_english, byline, pill_fill,
    )

    # ── 2) Circular Purnabramha logo medallion ────────────────────────────
    if logo_path and os.path.exists(logo_path):
        lx0, ly0, lx1, ly1 = corners["logo"]
        diameter = min(lx1 - lx0, ly1 - ly0)
        cx = (lx0 + lx1) // 2
        cy = (ly0 + ly1) // 2
        _draw_circle_logo(layer, logo_path, cx, cy, diameter)

    # ── 3) Thin chocolate brand strip at the bottom ──────────────────────
    strip_y0 = H - BRAND_STRIP_H
    draw.rectangle([0, strip_y0, W, H], fill=DARK_CHOCOLATE)
    draw.rectangle([0, strip_y0, W, strip_y0 + 3], fill=ANTIQUE_GOLD_BRIGHT)
    fs = int(BRAND_STRIP_H * 0.42)
    f_brand = _font(LATIN_BOLD, fs)
    line = brand if brand else "Purnabramha — Authentic Maharashtrian Cuisine"
    bb = draw.textbbox((0, 0), line, font=f_brand)
    tw = bb[2] - bb[0]; th = bb[3] - bb[1]
    while tw > W - 60 and fs > 14:
        fs = int(fs * 0.92)
        f_brand = _font(LATIN_BOLD, fs)
        bb = draw.textbbox((0, 0), line, font=f_brand)
        tw = bb[2] - bb[0]; th = bb[3] - bb[1]
    tx = (W - tw) // 2
    ty = strip_y0 + (BRAND_STRIP_H - th) // 2 - 4
    draw.text((tx, ty), line, font=f_brand, fill=WARM_CREAM)

    out = Image.alpha_composite(base, layer).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
