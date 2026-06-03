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
DEVANAGARI_BOLD = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
DEVANAGARI_REG = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
DEVANAGARI_SERIF_BOLD = "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Bold.ttf"
LATIN_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
LATIN_REG = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
LATIN_ITALIC = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"

# ── Brand palette ──────────────────────────────────────────────────────────
MAROON = (92, 0, 0)
GOLD = (176, 132, 49)
CREAM = (253, 246, 231)
WHITE = (255, 255, 255)
DARK_BG = (15, 8, 8, 200)        # rgba semi-transparent maroon


def composite_guest_photo(
    bg_bytes: bytes,
    guest_photo_bytes: bytes,
    aspect: str = "1:1",
    balgopal: bool = False,
) -> bytes:
    """Paste the actual guest photo on the LEFT side of the AI background.

    The AI is unreliable at face preservation, so we generate ONLY the brand
    backdrop + food via the LLM and then composite the real photo on the left.
    Faces are guaranteed to look exactly like the upload.

    For 9:16 / vertical formats, we use the TOP half instead of the LEFT half.
    Balgopal mode adds a gold star burst behind the photo.
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

    # Scale the guest photo to fit the available area (proportional cover-fit
    # so faces dominate the frame; we crop slightly if needed).
    gw, gh = guest.size
    scale = max(avail_w / gw, avail_h / gh)
    new_w, new_h = int(gw * scale), int(gh * scale)
    guest_scaled = guest.resize((new_w, new_h), Image.LANCZOS)
    # Center-crop to the available area
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


def _wrap_to_width(draw, text: str, font, max_w: int):
    """Word-wrap text to fit within max_w pixels. Returns list of lines."""
    if not text:
        return []
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        bb = draw.textbbox((0, 0), test, font=font)
        if bb[2] - bb[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


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
    """Overlay crisp text + logo on a pre-rendered visual.

    Returns PNG bytes. Idempotent — pass already-overlayed images and you get
    a re-rendered overlay; original visual is preserved underneath.
    """
    try:
        base = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    except Exception as e:
        logger.error(f"overlay: bad input image: {e}")
        return img_bytes

    W, H = base.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # ── Sizing relative to image dimensions ────────────────────────────────
    scale = min(W, H) / 1080.0
    fs_marathi = int(56 * scale)
    fs_english = int(34 * scale)
    fs_byline = int(26 * scale)
    fs_brand = int(28 * scale)
    side_pad = int(W * 0.05)
    inner_w = W - 2 * side_pad
    block_pad = int(28 * scale)

    # ── Compute block height to size the dark gradient band ────────────────
    f_m = _pick_font(headline_marathi, fs_marathi, bold=True)
    f_e = _pick_font(headline_english, fs_english, bold=False)
    f_b = _pick_font(byline, fs_byline, bold=False)
    f_brand = _font(LATIN_BOLD, fs_brand)

    lines_m = _wrap_to_width(draw, headline_marathi, f_m, inner_w - 2 * block_pad)
    lines_e = _wrap_to_width(draw, headline_english, f_e, inner_w - 2 * block_pad)
    line_h_m = f_m.size + 12
    line_h_e = f_e.size + 8
    needed = (len(lines_m) * line_h_m + (16 if lines_m and lines_e else 0)
              + len(lines_e) * line_h_e
              + (fs_byline + 12 if byline else 0)
              + 2 * block_pad + fs_brand + 24)
    band_h = max(needed, int(H * 0.22))
    band_h = min(band_h, int(H * 0.55))   # never cover more than 55%

    # ── Draw gradient band (dark maroon → transparent) ─────────────────────
    if position == "top":
        y0, y1 = 0, band_h
        steps = band_h
        for i in range(steps):
            alpha = int(210 * (1 - i / steps) ** 1.2)
            draw.rectangle([0, y0 + i, W, y0 + i + 1], fill=(15, 5, 5, alpha))
        text_y = block_pad
    else:
        y0, y1 = H - band_h, H
        steps = band_h
        for i in range(steps):
            alpha = int(210 * (i / steps) ** 1.2)
            draw.rectangle([0, y0 + i, W, y0 + i + 1], fill=(15, 5, 5, alpha))
        text_y = y0 + block_pad

    # ── Headline (Marathi first, bold gold) ────────────────────────────────
    for L in lines_m:
        bb = draw.textbbox((0, 0), L, font=f_m)
        tw = bb[2] - bb[0]
        tx = (W - tw) // 2
        # Soft drop-shadow
        draw.text((tx + 2, text_y + 2), L, font=f_m, fill=(0, 0, 0, 180))
        draw.text((tx, text_y), L, font=f_m, fill=GOLD)
        text_y += line_h_m
    if lines_m and lines_e:
        text_y += 12

    # ── Sub-headline (English, cream italic-ish) ──────────────────────────
    f_e_italic = _font(LATIN_ITALIC, fs_english)
    for L in lines_e:
        bb = draw.textbbox((0, 0), L, font=f_e_italic)
        tw = bb[2] - bb[0]
        tx = (W - tw) // 2
        draw.text((tx + 1, text_y + 1), L, font=f_e_italic, fill=(0, 0, 0, 150))
        draw.text((tx, text_y), L, font=f_e_italic, fill=CREAM)
        text_y += line_h_e

    # ── Byline (host / poster) ─────────────────────────────────────────────
    if byline:
        text_y += 6
        bb = draw.textbbox((0, 0), byline, font=f_b)
        tw = bb[2] - bb[0]
        draw.text(((W - tw) // 2, text_y), byline, font=f_b, fill=(220, 200, 160))
        text_y += fs_byline + 6

    # ── Brand line (always at the band's bottom edge) ─────────────────────
    brand_line = f"— {brand} —"
    bb = draw.textbbox((0, 0), brand_line, font=f_brand)
    bw = bb[2] - bb[0]
    bx = (W - bw) // 2
    if position == "top":
        by = band_h - fs_brand - 10
    else:
        by = y1 - fs_brand - 14
    draw.text((bx, by), brand_line, font=f_brand, fill=GOLD)

    # ── Logo (top-right small, transparent PNG) ──────────────────────────
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            target = int(min(W, H) * 0.10)
            logo.thumbnail((target, target))
            lx = W - logo.width - int(W * 0.04)
            ly = int(H * 0.04)
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
    """Overlay a crisp invitation info-panel on the lower portion of the AI background.

    Produces a wedding-card-style typography block with Devanagari support.
    The AI image should have a calm lower 45% (per the invitation prompt).
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
    side_pad = int(W * 0.06)
    inner_w = W - 2 * side_pad

    # Panel covers bottom ~50%
    panel_top = int(H * 0.50)
    # Semi-transparent cream panel with gold border
    panel = Image.new("RGBA", (inner_w, H - panel_top - side_pad), (253, 246, 231, 230))
    layer.paste(panel, (side_pad, panel_top), panel)
    draw.rounded_rectangle(
        [side_pad, panel_top, side_pad + inner_w, H - side_pad],
        radius=18, outline=GOLD, width=3,
    )
    # Inner double-line frame
    draw.rounded_rectangle(
        [side_pad + 12, panel_top + 12, side_pad + inner_w - 12, H - side_pad - 12],
        radius=12, outline=GOLD, width=1,
    )

    y = panel_top + int(36 * scale)
    # ── Occasion line (Bilingual) ───────────────────────────────────────────
    occ_line = (occasion_marathi + "  ·  " + occasion + " Celebration").strip(" ·")
    f_occ = _pick_font(occ_line, int(38 * scale), bold=True)
    for L in _wrap_to_width(draw, occ_line, f_occ, inner_w - 60):
        bb = draw.textbbox((0, 0), L, font=f_occ); tw = bb[2] - bb[0]
        draw.text(((W - tw) // 2, y), L, font=f_occ, fill=MAROON)
        y += f_occ.size + 6

    # ── Divider (paisley dots) ──────────────────────────────────────────────
    y += int(10 * scale)
    cx = W // 2
    for dx in range(-3, 4):
        draw.ellipse([cx + dx * 14 - 3, y, cx + dx * 14 + 3, y + 6], fill=GOLD)
    y += int(28 * scale)

    # ── Host name (largest, gold serif) ─────────────────────────────────────
    f_host = _pick_font(host_name, int(64 * scale), bold=True)
    for L in _wrap_to_width(draw, host_name, f_host, inner_w - 60):
        bb = draw.textbbox((0, 0), L, font=f_host); tw = bb[2] - bb[0]
        draw.text(((W - tw) // 2 + 2, y + 2), L, font=f_host, fill=(0, 0, 0, 70))
        draw.text(((W - tw) // 2, y), L, font=f_host, fill=GOLD)
        y += f_host.size + 6

    y += int(24 * scale)
    # ── Date / Time ────────────────────────────────────────────────────────
    dt_line = f"{event_date}    ·    {event_time}"
    f_dt = _font(LATIN_BOLD, int(34 * scale))
    bb = draw.textbbox((0, 0), dt_line, font=f_dt); tw = bb[2] - bb[0]
    draw.text(((W - tw) // 2, y), dt_line, font=f_dt, fill=MAROON)
    y += f_dt.size + int(20 * scale)

    # ── Venue ──────────────────────────────────────────────────────────────
    f_venue = _font(LATIN_BOLD, int(28 * scale))
    bb = draw.textbbox((0, 0), venue_name, font=f_venue); tw = bb[2] - bb[0]
    draw.text(((W - tw) // 2, y), venue_name, font=f_venue, fill=(80, 40, 0))
    y += f_venue.size + 4
    if venue_address:
        f_addr = _font(LATIN_REG, int(22 * scale))
        for L in _wrap_to_width(draw, venue_address, f_addr, inner_w - 60):
            bb = draw.textbbox((0, 0), L, font=f_addr); tw = bb[2] - bb[0]
            draw.text(((W - tw) // 2, y), L, font=f_addr, fill=(80, 40, 0))
            y += f_addr.size + 2

    # ── Menu (optional) ─────────────────────────────────────────────────────
    if menu_highlights:
        y += int(14 * scale)
        f_label = _font(LATIN_BOLD, int(22 * scale))
        label = "Featured Menu"
        bb = draw.textbbox((0, 0), label, font=f_label); tw = bb[2] - bb[0]
        draw.text(((W - tw) // 2, y), label, font=f_label, fill=MAROON)
        y += f_label.size + 4
        f_menu = _pick_font(menu_highlights, int(22 * scale), bold=False)
        for L in _wrap_to_width(draw, menu_highlights, f_menu, inner_w - 80):
            bb = draw.textbbox((0, 0), L, font=f_menu); tw = bb[2] - bb[0]
            draw.text(((W - tw) // 2, y), L, font=f_menu, fill=(80, 40, 0))
            y += f_menu.size + 2

    # ── Custom message (optional, italic) ──────────────────────────────────
    if custom_message:
        y += int(14 * scale)
        f_msg = _pick_font(custom_message, int(22 * scale), bold=False)
        for L in _wrap_to_width(draw, custom_message, f_msg, inner_w - 100):
            bb = draw.textbbox((0, 0), L, font=f_msg); tw = bb[2] - bb[0]
            draw.text(((W - tw) // 2, y), f'"{L}"', font=f_msg, fill=(120, 80, 0))
            y += f_msg.size + 2

    # ── Brand footer ───────────────────────────────────────────────────────
    f_brand = _font(LATIN_BOLD, int(22 * scale))
    brand_line = f"— With warm regards · {brand} · {venue_name} —"
    bb = draw.textbbox((0, 0), brand_line, font=f_brand); tw = bb[2] - bb[0]
    # Shrink to fit
    if tw > inner_w - 40:
        brand_line = f"— With warm regards · {brand} —"
        bb = draw.textbbox((0, 0), brand_line, font=f_brand); tw = bb[2] - bb[0]
    draw.text(((W - tw) // 2, H - side_pad - int(36 * scale)), brand_line, font=f_brand, fill=GOLD)

    # ── Small logo top-right (transparent PNG over AI image) ──────────────
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            target = int(W * 0.13)
            logo.thumbnail((target, target))
            lx = W - logo.width - int(W * 0.05)
            ly = int(H * 0.04)
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
