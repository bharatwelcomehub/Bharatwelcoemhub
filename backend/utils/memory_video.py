"""Memory Box animated video generator.

Builds a 30-45 sec MP4 with 6 scenes:
    1. Box opens     — "Thank you for [hosting/ordering] at Purnabramha <Center>"
    2. Photo collages — 3 sets of 2-3 best photos with sparkle fade-in
    3. Team         — group photo + each member name appearing
    4. Your Story With Us — narrative recap (uses LLM story text)
    5. Discount     — "Get 10% off — code MEMORY10" + Purnabramha QR
    6. Center       — Center QR + Instagram + Website + phone

Each scene renders as a single 1080×1080 PNG (square = WhatsApp/IG friendly).
ffmpeg (bundled via imageio-ffmpeg) stitches the scenes with crossfades and
adds a subtle Ken-Burns zoom-pan to keep frames "alive".

No external network calls — all rendering happens locally with Pillow + ffmpeg.
"""
from __future__ import annotations

import base64
import io
import math
import os
import random
import subprocess
import tempfile
from typing import Dict, List, Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------------------
# Constants & palette
# ---------------------------------------------------------------------------
SQ = 1080                       # canvas size for each scene PNG
CHOCOLATE = (43, 24, 16)
GOLD = (220, 175, 80)
CREAM = (250, 240, 220)
DEEP_GOLD = (180, 140, 60)
WHITE = (255, 255, 255)
SCENE_DURATION = {              # seconds per scene
    "intro": 5.0,
    "photos": 7.0,              # × 3 collage scenes → 21s total
    "team": 5.0,
    "story": 6.0,
    "discount": 5.0,
    "center": 5.0,
}
XFADE = 0.7                     # crossfade duration between scenes
FPS = 25

LOGO_PATH = "/app/backend/static/purnabramha_logo.png"
STATIC_QR_BOOKING = "/app/backend/static/purnabramha_booking_qr.png"
FONT_REG = "/app/backend/static/fonts/LiberationSerif-Regular.ttf"
FONT_BOLD = "/app/backend/static/fonts/LiberationSerif-Bold.ttf"
FONT_ITALIC = "/app/backend/static/fonts/LiberationSerif-Italic.ttf"
FONT_DEV_BOLD = "/app/backend/static/fonts/NotoSansDevanagari-Bold.ttf"
FONT_DEV_REG = "/app/backend/static/fonts/NotoSansDevanagari-Regular.ttf"


def _ff() -> str:
    """Locate the bundled ffmpeg binary."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _font(size: int, bold: bool = False, devanagari: bool = False) -> ImageFont.FreeTypeFont:
    paths = []
    if devanagari and os.path.exists(FONT_DEV_BOLD):
        paths.append(FONT_DEV_BOLD)
    if bold and os.path.exists(FONT_BOLD):
        paths.append(FONT_BOLD)
    if os.path.exists(FONT_REG):
        paths.append(FONT_REG)
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()
    paths = []
    if devanagari and os.path.exists(FONT_DEV_BOLD):
        paths.append(FONT_DEV_BOLD)
    if bold and os.path.exists(FONT_BOLD):
        paths.append(FONT_BOLD)
    if os.path.exists(FONT_REG):
        paths.append(FONT_REG)
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _strip_data_url(b64: str) -> bytes:
    if not b64:
        return b""
    if "," in b64 and b64.startswith("data:"):
        b64 = b64.split(",", 1)[1]
    try:
        return base64.b64decode(b64)
    except Exception:
        return b""


def _open_b64(b64: str) -> Optional[Image.Image]:
    raw = _strip_data_url(b64) if isinstance(b64, str) else b64
    if not raw:
        return None
    try:
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        im.load()
        return im
    except Exception:
        return None


def _draw_centered_text(draw: ImageDraw.ImageDraw, xy, text: str, font, fill,
                        max_w: Optional[int] = None):
    """Draw multiline text horizontally centered on xy (x_center, y_top).
    If max_w given, auto-wraps."""
    lines = _wrap(text, font, max_w) if max_w else [text]
    cx, y = xy
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((cx - tw // 2, y), ln, font=font, fill=fill)
        y += th + 8
    return y


def _wrap(text: str, font, max_w: int) -> List[str]:
    if not text:
        return [""]
    words = text.split()
    lines: List[str] = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        bbox = font.getbbox(test)
        if (bbox[2] - bbox[0]) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _bg_paisley(seed: int = 7) -> Image.Image:
    """Build a deep-chocolate canvas with faint gold paisley dots — used as
    the base for most scenes so the Maharashtrian aesthetic carries through."""
    rng = random.Random(seed)
    canvas = Image.new("RGB", (SQ, SQ), CHOCOLATE)
    draw = ImageDraw.Draw(canvas, "RGBA")
    # Sparse gold dust
    for _ in range(420):
        x, y = rng.randint(0, SQ), rng.randint(0, SQ)
        r = rng.randint(2, 6)
        a = rng.randint(20, 70)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(*GOLD, a))
    # Soft gold corner glow
    glow = Image.new("RGBA", (SQ, SQ), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    for r, a in [(420, 40), (340, 50), (240, 60), (150, 70)]:
        g.ellipse([SQ // 2 - r, SQ // 2 - r, SQ // 2 + r, SQ // 2 + r],
                  fill=(*GOLD, a))
    glow = glow.filter(ImageFilter.GaussianBlur(110))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), glow).convert("RGB")
    return canvas


# ---------------------------------------------------------------------------
# Scene renderers — each returns a (1080×1080) PIL.Image (RGB).
# ---------------------------------------------------------------------------

def render_intro(center_name: str, occasion: str, mode_text: str) -> Image.Image:
    """Scene 1: open-the-box thank-you card.

    mode_text decides the phrasing: 'function' (hosted) or 'home' (delivery).
    """
    canvas = _bg_paisley(seed=11)
    d = ImageDraw.Draw(canvas, "RGBA")

    # Decorative gold border
    d.rounded_rectangle([40, 40, SQ - 40, SQ - 40], radius=24,
                        outline=GOLD, width=4)
    d.rounded_rectangle([60, 60, SQ - 60, SQ - 60], radius=20,
                        outline=(*GOLD, 120), width=1)

    # Open-box pictogram — gold semi-open lid
    box_top = 180
    d.polygon([(SQ // 2 - 200, box_top + 80), (SQ // 2 + 200, box_top + 80),
               (SQ // 2 + 240, box_top), (SQ // 2 - 240, box_top)],
              fill=GOLD, outline=DEEP_GOLD)
    d.rectangle([SQ // 2 - 200, box_top + 80, SQ // 2 + 200, box_top + 260],
                fill=(60, 36, 22), outline=GOLD, width=3)
    # gold ribbon
    d.rectangle([SQ // 2 - 30, box_top, SQ // 2 + 30, box_top + 260], fill=DEEP_GOLD)
    # Sparkle accents
    for sx, sy, sr in [(SQ // 2 - 280, box_top + 20, 6),
                       (SQ // 2 + 280, box_top + 60, 5),
                       (SQ // 2 - 250, box_top + 220, 4),
                       (SQ // 2 + 250, box_top + 240, 6)]:
        d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=CREAM)

    # Greeting
    f_title = _font(58, bold=True)
    f_sub = _font(36)
    f_center = _font(46, bold=True)
    f_occ = _font(32)

    cx = SQ // 2
    _draw_centered_text(d, (cx, 540), "Dhanyavad!", f_title, GOLD)
    line = (f"Thank you for hosting your {occasion} with us."
            if mode_text == "function"
            else f"Thank you for choosing Purnabramha for your {occasion}.")
    _draw_centered_text(d, (cx, 620), line, f_sub, CREAM, max_w=SQ - 240)
    _draw_centered_text(d, (cx, 800), center_name or "Purnabramha", f_center, GOLD)
    f_dev = _font(34, bold=True, devanagari=True)
    _draw_centered_text(d, (cx, 870), "— एक छोटीशी आठवण —", f_dev, CREAM)
    return canvas


def render_collage(photo_imgs: List[Image.Image], title: str, accent_idx: int) -> Image.Image:
    """Scene 2 (×3): polaroid-style collage of 2-3 photos."""
    canvas = _bg_paisley(seed=23 + accent_idx)
    d = ImageDraw.Draw(canvas, "RGBA")

    f_title = _font(38, bold=True)
    f_count = _font(22)

    # Top label band
    d.rounded_rectangle([SQ // 2 - 240, 60, SQ // 2 + 240, 130], radius=30,
                        fill=(*CREAM, 240))
    _draw_centered_text(d, (SQ // 2, 78), title, f_title, CHOCOLATE)
    _draw_centered_text(d, (SQ // 2, SQ - 110), f"Memory {accent_idx + 1} of 3",
                        f_count, GOLD)

    if not photo_imgs:
        return canvas

    n = min(len(photo_imgs), 3)
    # Polaroid sizes
    if n == 1:
        positions = [(SQ // 2, 540, 580, 640, -3)]
    elif n == 2:
        positions = [(SQ // 2 - 220, 540, 440, 500, -7),
                     (SQ // 2 + 220, 540, 440, 500, 6)]
    else:
        positions = [(SQ // 2 - 290, 480, 360, 420, -9),
                     (SQ // 2,       560, 400, 460, 3),
                     (SQ // 2 + 290, 480, 360, 420, 9)]

    for (cx, cy, pw, ph, rot), photo in zip(positions, photo_imgs[:n]):
        polaroid = _make_polaroid(photo, pw, ph, rotation=rot)
        canvas.paste(polaroid, (cx - polaroid.width // 2, cy - polaroid.height // 2),
                     polaroid)

    # Sparkle dots overlay
    rng = random.Random(31 + accent_idx)
    for _ in range(28):
        x, y = rng.randint(60, SQ - 60), rng.randint(60, SQ - 60)
        r = rng.randint(2, 4)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*CREAM, 220))
    return canvas


def _make_polaroid(im: Image.Image, w: int, h: int, rotation: int = 0) -> Image.Image:
    """Cover-fit `im` into w×h, add cream polaroid border, return rotated RGBA."""
    gw, gh = im.size
    scale = max(w / gw, h / gh)
    nw, nh = int(gw * scale), int(gh * scale)
    im2 = im.resize((nw, nh), Image.LANCZOS)
    left = (nw - w) // 2
    top = (nh - h) // 2
    photo = im2.crop((left, top, left + w, top + h))

    # Polaroid frame: cream margin
    pad_top = pad_lr = 22
    pad_bot = 64
    frame = Image.new("RGBA", (w + pad_lr * 2, h + pad_top + pad_bot), (*CREAM, 255))
    frame.paste(photo, (pad_lr, pad_top))
    # gold inner edge
    d = ImageDraw.Draw(frame)
    d.rectangle([pad_lr - 2, pad_top - 2, pad_lr + w + 1, pad_top + h + 1],
                outline=GOLD, width=2)
    # subtle drop shadow
    shadow = Image.new("RGBA", (frame.width + 30, frame.height + 30), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rectangle([15, 15, shadow.width - 15, shadow.height - 15], fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    shadow.paste(frame, (15, 15), frame)
    if rotation:
        shadow = shadow.rotate(rotation, resample=Image.BICUBIC, expand=True)
    return shadow


def render_team(team_photo: Optional[Image.Image], team: List[Dict[str, str]],
                center_name: str) -> Image.Image:
    """Scene 3: team photo + each member name as a tag."""
    canvas = _bg_paisley(seed=47)
    d = ImageDraw.Draw(canvas, "RGBA")

    f_title = _font(48, bold=True)
    f_name = _font(28, bold=True)
    f_role = _font(22)
    f_sub = _font(30)

    _draw_centered_text(d, (SQ // 2, 60), "Our Team Who Cared for You",
                        f_title, GOLD)

    if team_photo:
        tp = _make_polaroid(team_photo, 720, 420, rotation=-2)
        canvas.paste(tp, (SQ // 2 - tp.width // 2, 150), tp)
        list_y = 620
    else:
        list_y = 200

    members = [t for t in (team or []) if t.get("name")][:8]
    if not members:
        _draw_centered_text(d, (SQ // 2, list_y + 80),
                            "Crafted with love by our entire team", f_sub, CREAM)
    else:
        # Two columns
        col_w = 420
        for i, m in enumerate(members):
            col = i % 2
            row = i // 2
            x = SQ // 2 - col_w + col * col_w + col_w // 2
            y = list_y + row * 64
            # Gold pill background
            pill_w = 360
            d.rounded_rectangle([x - pill_w // 2, y - 4, x + pill_w // 2, y + 50],
                                radius=24, fill=(*CHOCOLATE, 230),
                                outline=GOLD, width=2)
            _draw_centered_text(d, (x, y), m.get("name", "")[:24], f_name, GOLD)
            _draw_centered_text(d, (x, y + 28),
                                m.get("role", "Service Associate")[:30],
                                f_role, CREAM)

    _draw_centered_text(d, (SQ // 2, SQ - 80), center_name or "Purnabramha",
                        f_sub, GOLD)
    return canvas


def render_story(story_text: str, guest_name: str) -> Image.Image:
    """Scene 4: 'Your Story With Us' — narrative text."""
    canvas = _bg_paisley(seed=59)
    d = ImageDraw.Draw(canvas, "RGBA")

    f_title = _font(54, bold=True)
    f_body = _font(30)
    f_sig = _font(28)

    _draw_centered_text(d, (SQ // 2, 80), "Your Story With Us", f_title, GOLD)

    # Cream parchment panel
    px, py, pw, ph = 100, 200, SQ - 200, 620
    d.rounded_rectangle([px, py, px + pw, py + ph], radius=24,
                        fill=(*CREAM, 245), outline=GOLD, width=3)

    # Body text — wrap inside parchment
    if not story_text or len(story_text.strip()) < 5:
        story_text = (f"Dear {guest_name or 'Friend'}, your celebration brought "
                      "warmth, laughter and the comforting taste of home to "
                      "every plate we served. Thank you for letting Purnabramha "
                      "be part of this beautiful chapter — your story is now "
                      "part of ours.")

    # Limit to ~700 chars for readability
    if len(story_text) > 760:
        story_text = story_text[:740].rsplit(" ", 1)[0] + "…"

    lines = _wrap(story_text, f_body, pw - 80)
    y = py + 40
    for ln in lines[:14]:
        bbox = d.textbbox((0, 0), ln, font=f_body)
        tw = bbox[2] - bbox[0]
        d.text((SQ // 2 - tw // 2, y), ln, font=f_body, fill=CHOCOLATE)
        y += (bbox[3] - bbox[1]) + 12

    _draw_centered_text(d, (SQ // 2, SQ - 90),
                        "— with love, Team Purnabramha", f_sig, GOLD)
    return canvas


def render_discount(qr_path: Optional[str] = None) -> Image.Image:
    """Scene 5: 10% off + MEMORY10 + QR."""
    from .memory_qr import make_qr_png  # local import; avoids cyc

    canvas = _bg_paisley(seed=71)
    d = ImageDraw.Draw(canvas, "RGBA")

    f_big = _font(96, bold=True)
    f_mid = _font(48, bold=True)
    f_small = _font(28)
    f_code = _font(60, bold=True)

    _draw_centered_text(d, (SQ // 2, 80), "A Little Thank-You Gift",
                        f_small, CREAM)
    _draw_centered_text(d, (SQ // 2, 140), "10% OFF", f_big, GOLD)
    _draw_centered_text(d, (SQ // 2, 280), "your next order", f_mid, CREAM)

    # Code chip
    chip_y = 380
    d.rounded_rectangle([SQ // 2 - 220, chip_y, SQ // 2 + 220, chip_y + 100],
                        radius=18, fill=(*CREAM, 245), outline=GOLD, width=4)
    _draw_centered_text(d, (SQ // 2, chip_y + 16), "MEMORY10", f_code, CHOCOLATE)

    # Generate (or load) the discount QR — encodes the promo code text
    qr_img = None
    try:
        qr_bytes = make_qr_png("MEMORY10", size=560)
        qr_img = Image.open(io.BytesIO(qr_bytes)).convert("RGBA")
    except Exception:
        if qr_path and os.path.exists(qr_path):
            qr_img = Image.open(qr_path).convert("RGBA")

    if qr_img is not None:
        qr_img.thumbnail((380, 380), Image.LANCZOS)
        # White card behind QR for scannability
        card_pad = 22
        card_w = qr_img.width + card_pad * 2
        card_h = qr_img.height + card_pad * 2
        cx = (SQ - card_w) // 2
        cy = 540
        d.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=18,
                            fill=WHITE, outline=GOLD, width=3)
        canvas.paste(qr_img, (cx + card_pad, cy + card_pad), qr_img)
        _draw_centered_text(d, (SQ // 2, cy + card_h + 18),
                            "Scan or use code at checkout", f_small, CREAM)
    return canvas


def render_center_contact(center: Dict[str, str], qr_path: Optional[str]) -> Image.Image:
    """Scene 6: center QR + Instagram + Website + phone."""
    from .memory_qr import make_qr_png

    canvas = _bg_paisley(seed=83)
    d = ImageDraw.Draw(canvas, "RGBA")

    f_title = _font(46, bold=True)
    f_info = _font(28)
    f_small = _font(26)

    _draw_centered_text(d, (SQ // 2, 70), "Stay Connected", f_title, GOLD)
    _draw_centered_text(d, (SQ // 2, 130),
                        center.get("name", "Purnabramha") or "Purnabramha",
                        f_info, CREAM)

    # Build center QR. Prefer center-supplied URL; else use generic Purnabramha booking QR file.
    url = (center.get("instagram_url") or center.get("website")
           or "https://www.purnabramha.com")
    qr_img = None
    try:
        qr_bytes = make_qr_png(url, size=520)
        qr_img = Image.open(io.BytesIO(qr_bytes)).convert("RGBA")
    except Exception:
        path = qr_path or STATIC_QR_BOOKING
        if os.path.exists(path):
            qr_img = Image.open(path).convert("RGBA")

    if qr_img is not None:
        qr_img.thumbnail((460, 460), Image.LANCZOS)
        pad = 24
        card_w = qr_img.width + pad * 2
        card_h = qr_img.height + pad * 2
        cx = (SQ - card_w) // 2
        cy = 200
        d.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=18,
                            fill=WHITE, outline=GOLD, width=3)
        canvas.paste(qr_img, (cx + pad, cy + pad), qr_img)

    # Info rows
    y = 750
    rows = []
    if center.get("instagram_url"):
        ig = center["instagram_url"].rstrip("/")
        handle = ig.split("/")[-1] or ig
        if not handle.startswith("@"):
            handle = "@" + handle
        rows.append(("Instagram", handle))
    if center.get("website"):
        rows.append(("Website", center["website"]))
    if center.get("phone"):
        rows.append(("Call", center["phone"]))
    if not rows:
        rows = [("Website", "www.purnabramha.com")]

    for label, value in rows:
        _draw_centered_text(d, (SQ // 2, y),
                            f"{label}: {value}", f_info, CREAM,
                            max_w=SQ - 200)
        y += 50

    _draw_centered_text(d, (SQ // 2, SQ - 60),
                        "Until we feed your family again — Dhanyavad",
                        f_small, GOLD)
    return canvas


# ---------------------------------------------------------------------------
# ffmpeg stitching
# ---------------------------------------------------------------------------


def build_video(scene_images: List[Image.Image], durations: List[float],
                out_path: str) -> None:
    """Stitch scenes into an MP4 with xfade transitions.

    Implementation note: We feed each scene as a single still PNG, looped at
    `-framerate 1 -loop 1 -t dur` so only one input frame is materialised
    (avoids the zoompan output-frame explosion). The xfade filter handles the
    crossfade between consecutive scenes. libx264 + tune=stillimage keeps the
    file size tiny for our mostly-static content (~1-3 MB for 30-45 sec).
    """
    assert len(scene_images) == len(durations) and scene_images, "scenes/durations mismatch"
    ff = _ff()

    with tempfile.TemporaryDirectory() as tmp:
        # Write each scene PNG
        png_paths: List[str] = []
        for i, im in enumerate(scene_images):
            p = os.path.join(tmp, f"scene_{i:02d}.png")
            im.convert("RGB").save(p, format="PNG", optimize=True)
            png_paths.append(p)

        # Build ffmpeg cmd: each PNG looped for its duration as 1-FPS input,
        # then upsampled to FPS via fps filter so xfade sees real motion frames.
        cmd: List[str] = [ff, "-y"]
        for p, dur in zip(png_paths, durations):
            cmd += ["-framerate", "1", "-loop", "1", "-t", f"{dur:.3f}", "-i", p]

        # Build filter graph
        # Step 1: normalise each input to FPS + format=yuv420p + label as [vN]
        filter_parts: List[str] = []
        for i, _dur in enumerate(durations):
            filter_parts.append(
                f"[{i}:v]scale={SQ}:{SQ}:flags=lanczos,"
                f"fps={FPS},format=yuv420p,setsar=1[v{i}]"
            )

        # Step 2: xfade chain. The output length after xfade(in1, in2, offset, dur)
        # is `offset + length(in2)`, so the next offset is `prev_out_len - XFADE`.
        if len(durations) == 1:
            filter_parts.append("[v0]copy[vout]")
        else:
            prev_out_len = durations[0]
            offset = prev_out_len - XFADE
            prev_label = "v0"
            for i in range(1, len(durations)):
                out_label = f"vx{i}" if i < len(durations) - 1 else "vout"
                filter_parts.append(
                    f"[{prev_label}][v{i}]xfade=transition=fade:"
                    f"duration={XFADE}:offset={offset:.3f}[{out_label}]"
                )
                prev_out_len = offset + durations[i]
                offset = prev_out_len - XFADE
                prev_label = out_label

        filter_complex = ";".join(filter_parts)

        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-tune", "stillimage",
            "-crf", "26",
            "-movflags", "+faststart",
            "-r", str(FPS),
            out_path,
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {proc.stderr[-1500:]}")


# ---------------------------------------------------------------------------
# High-level orchestrator
# ---------------------------------------------------------------------------

def render_memory_video(
    *,
    out_path: str,
    center_name: str,
    occasion: str,
    delivery_mode: str,            # "function" | "home"
    ranked_photos: List[Image.Image],     # already AI-ranked & decoded
    collage_sets: List[List[int]],        # 3 lists of indices into ranked_photos
    team_photo: Optional[Image.Image],
    team: List[Dict[str, str]],
    story_text: str,
    guest_name: str,
    center_info: Dict[str, str],
    center_qr_path: Optional[str] = None,
) -> Dict[str, float]:
    """Render the full Memory Box MP4. Returns metadata."""

    scenes: List[Image.Image] = []
    durations: List[float] = []

    # Scene 1
    scenes.append(render_intro(center_name, occasion, delivery_mode))
    durations.append(SCENE_DURATION["intro"])

    # Scene 2 (×3 collages) — even if some sets are empty, render at least
    # the first to keep the video coherent
    rendered_collage = 0
    for i, set_indices in enumerate(collage_sets[:3]):
        if not set_indices:
            continue
        imgs = [ranked_photos[ix] for ix in set_indices if ix < len(ranked_photos)]
        if not imgs:
            continue
        scenes.append(render_collage(imgs, "A Beautiful Moment", rendered_collage))
        durations.append(SCENE_DURATION["photos"])
        rendered_collage += 1

    # Scene 3
    scenes.append(render_team(team_photo, team, center_name))
    durations.append(SCENE_DURATION["team"])

    # Scene 4
    scenes.append(render_story(story_text, guest_name))
    durations.append(SCENE_DURATION["story"])

    # Scene 5
    scenes.append(render_discount())
    durations.append(SCENE_DURATION["discount"])

    # Scene 6
    scenes.append(render_center_contact(center_info, center_qr_path))
    durations.append(SCENE_DURATION["center"])

    build_video(scenes, durations, out_path)

    return {
        "scenes": len(scenes),
        "duration_sec": round(sum(durations) - XFADE * max(0, len(scenes) - 1), 2),
        "size_bytes": os.path.getsize(out_path) if os.path.exists(out_path) else 0,
    }
