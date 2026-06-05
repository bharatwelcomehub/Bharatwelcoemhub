"""Video Overlay — Brand any short video with Purnabramha logo + caption.

The center manager records a short clip on their phone (≤ 60s, ≤ 50 MB),
uploads it, and we burn the logo + custom caption + brand bar using ffmpeg.
"""
import logging
import os
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server import db                                    # type: ignore
from routes.center_accounts import check_access

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/marketing/videos", tags=["marketing-videos"])

LOGO_PATH = "/app/backend/static/purnabramha_logo.png"
ASSET_DIR = "/app/backend/static/marketing_videos"
os.makedirs(ASSET_DIR, exist_ok=True)

DEV_FONT = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
LATIN_FONT = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
LATIN_ITALIC = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"

MAX_BYTES = 60 * 1024 * 1024     # 60 MB hard limit
MAX_DURATION_S = 90              # processed clips capped at 90s


def _has_devanagari(text: str) -> bool:
    return any('\u0900' <= c <= '\u097F' for c in (text or ""))


def _can_create(session: dict) -> bool:
    if session.get("is_super_admin") or session.get("is_admin"):
        return True
    role_key = (session.get("role_key") or "").lower()
    roles = session.get("roles") or {}
    if role_key in {"center_manager", "manager", "operations", "accountant"}:
        return True
    return bool(roles.get("operations") or roles.get("ops") or roles.get("manager")
                or roles.get("center_manager"))


def _ffmpeg_escape(text: str) -> str:
    """Escape characters that have special meaning in ffmpeg drawtext."""
    return (text or "").replace("\\", "\\\\").replace(":", "\\:").replace("'", "\u2019")


def _build_filter(headline: str, sub: str, byline: str, has_logo: bool,
                  position: str = "bottom",
                  show_footer: bool = True,
                  headline_size: str = "M",
                  subline_size: str = "M") -> str:
    """Compose the ffmpeg filter_complex chain for overlay.

    Sizes (S/M/L) drive `fontsize=h/N`:
      headline: S=h/11, M=h/9, L=h/7
      sub:      S=h/20, M=h/16, L=h/13
    `show_footer=False` skips both the cream sub-line AND the byline so the
    chocolate strip is shorter and the headline reads as the only call-out.
    """
    parts = []

    h_size_map = {"S": "h/11", "M": "h/9", "L": "h/7"}
    s_size_map = {"S": "h/20", "M": "h/16", "L": "h/13"}
    h_font = h_size_map.get((headline_size or "M").upper(), "h/9")
    s_font = s_size_map.get((subline_size or "M").upper(), "h/16")

    # Numeric ratios for dynamic stacking
    h_ratio = {"S": 1 / 11, "M": 1 / 9, "L": 1 / 7}.get(
        (headline_size or "M").upper(), 1 / 9)
    s_ratio = {"S": 1 / 20, "M": 1 / 16, "L": 1 / 13}.get(
        (subline_size or "M").upper(), 1 / 16)
    b_ratio = 1 / 24
    gap = 0.012  # vertical gap between stacked lines

    # The brand strip auto-shrinks when the footer is hidden (no sub, no byline)
    strip_h_ratio = 0.30 if show_footer else 0.20

    # 1) Dark CHOCOLATE strip
    if position == "top":
        strip_top = 0.0
        parts.append(
            f"drawbox=x=0:y=0:w=iw:h=ih*{strip_h_ratio}:color=0x2B1810@0.85:t=fill"
        )
        parts.append(
            f"drawbox=x=0:y=ih*{strip_h_ratio}-4:w=iw:h=4:color=0xBF8C32@1.0:t=fill"
        )
    else:
        strip_top = 1.0 - strip_h_ratio
        parts.append(
            f"drawbox=x=0:y=ih*{strip_top}:w=iw:h=ih*{strip_h_ratio}:color=0x2B1810@0.85:t=fill"
        )
        parts.append(
            f"drawbox=x=0:y=ih*{strip_top}:w=iw:h=4:color=0xBF8C32@1.0:t=fill"
        )

    # 2) Compute y positions dynamically so headline + sub + byline never collide
    if show_footer:
        pad = 0.018
        y_h_r = strip_top + pad
        y_s_r = y_h_r + h_ratio + gap
        y_b_r = y_s_r + s_ratio + gap
    else:
        # Minimal strip — center the headline vertically
        y_h_r = strip_top + (strip_h_ratio - h_ratio) / 2
        y_s_r = 0  # unused
        y_b_r = 0  # unused

    y_h = f"h*{y_h_r:.4f}"
    y_s = f"h*{y_s_r:.4f}"
    y_b = f"h*{y_b_r:.4f}"

    # 3) Headline — Antique Gold
    if headline:
        f = DEV_FONT if _has_devanagari(headline) else LATIN_FONT
        if os.path.exists(f):
            parts.append(
                f"drawtext=fontfile={f}:text='{_ffmpeg_escape(headline)}':"
                f"fontcolor=0xDCAE50:fontsize={h_font}:"
                f"x=(w-text_w)/2:y={y_h}:"
                f"shadowcolor=black@0.8:shadowx=3:shadowy=3"
            )

    # 4) Sub-headline — Warm Cream (only when footer shown)
    if sub and show_footer:
        f = DEV_FONT if _has_devanagari(sub) else LATIN_ITALIC
        if os.path.exists(f):
            parts.append(
                f"drawtext=fontfile={f}:text='{_ffmpeg_escape(sub)}':"
                f"fontcolor=0xFAF0DC:fontsize={s_font}:"
                f"x=(w-text_w)/2:y={y_s}:"
                f"shadowcolor=black@0.6:shadowx=2:shadowy=2"
            )

    # 5) Byline (only when footer shown)
    if byline and show_footer:
        f = DEV_FONT if _has_devanagari(byline) else LATIN_ITALIC
        if os.path.exists(f):
            parts.append(
                f"drawtext=fontfile={f}:text='— {_ffmpeg_escape(byline)} —':"
                f"fontcolor=0xF0E4C8:fontsize=h/24:"
                f"x=(w-text_w)/2:y={y_b}"
            )

    chain = ",".join(parts)
    if has_logo:
        return (
            f"[0:v]{chain}[base];"
            f"[1:v]scale=ih*0.28:-1[logo];"
            f"[base][logo]overlay=x=W-w-30:y=30"
        )
    return f"[0:v]{chain}"


async def _process_video(
    src_path: str,
    dst_path: str,
    headline: str,
    sub: str,
    byline: str,
    use_logo: bool,
    duration_limit: int = MAX_DURATION_S,
    *,
    position: str = "bottom",
    show_footer: bool = True,
    headline_size: str = "M",
    subline_size: str = "M",
) -> dict:
    """Run ffmpeg with the composed filter, return {size_kb, duration_s}."""
    if not os.path.exists(src_path):
        raise HTTPException(500, "Uploaded file disappeared")
    has_logo = use_logo and os.path.exists(LOGO_PATH)
    filter_complex = _build_filter(
        headline, sub, byline, has_logo,
        position=position, show_footer=show_footer,
        headline_size=headline_size, subline_size=subline_size,
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", src_path,
    ]
    if has_logo:
        cmd += ["-i", LOGO_PATH]
    cmd += [
        "-filter_complex", filter_complex,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration_limit),
        "-movflags", "+faststart",
        dst_path,
    ]
    logger.info(f"ffmpeg cmd: {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=180)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Video processing timed out (90s budget)")
    if proc.returncode != 0:
        logger.error(f"ffmpeg stderr: {proc.stderr.decode(errors='ignore')[-2000:]}")
        raise HTTPException(500, "Video processing failed — try a shorter / simpler clip")

    size_kb = round(os.path.getsize(dst_path) / 1024.0, 1)
    # Probe duration
    try:
        pr = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", dst_path],
            capture_output=True, timeout=15,
        )
        duration_s = float(pr.stdout.strip() or 0)
    except Exception:
        duration_s = 0
    return {"size_kb": size_kb, "duration_s": round(duration_s, 1)}


# ─────────────────────────── Routes ──────────────────────────────────────
@router.post("/overlay")
async def overlay_video(
    token: str = Form(...),
    center: str = Form(...),
    headline: str = Form(""),
    sub: str = Form(""),
    byline: str = Form(""),
    use_logo: bool = Form(True),
    position: str = Form("bottom"),
    show_footer: bool = Form(True),
    headline_size: str = Form("M"),     # S | M | L
    subline_size: str = Form("M"),      # S | M | L
    instagram_url: str = Form(""),       # NEW per-center social handle
    phone: str = Form(""),               # NEW per-center phone
    video: UploadFile = File(...),
):
    session = await check_access(token)
    if not _can_create(session):
        raise HTTPException(403, "Not permitted to create branded videos")
    if not video.filename:
        raise HTTPException(400, "No video uploaded")
    if not video.content_type or "video" not in video.content_type:
        # Be lenient — some browsers don't set content_type
        pass

    video_id = str(uuid.uuid4())
    center_safe = (center or "UNKNOWN").replace("/", "_")
    sub_dir = os.path.join(ASSET_DIR, center_safe)
    os.makedirs(sub_dir, exist_ok=True)
    src_path = os.path.join(sub_dir, f"{video_id}__src")
    dst_path = os.path.join(sub_dir, f"{video_id}.mp4")

    # Stream upload to disk with size guard
    written = 0
    with open(src_path, "wb") as f:
        while True:
            chunk = await video.read(1024 * 256)
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_BYTES:
                f.close()
                try: os.remove(src_path)
                except Exception: pass
                raise HTTPException(413, f"Video too large (max {MAX_BYTES // (1024*1024)} MB)")
            f.write(chunk)
    if written == 0:
        raise HTTPException(400, "Empty upload")

    # Augment sub-line with per-center contact info (single line, ' · ' separated)
    extras = []
    if instagram_url.strip():
        handle = instagram_url.strip().rstrip("/").split("/")[-1]
        if handle and not handle.startswith("@"):
            handle = "@" + handle
        if handle:
            extras.append(handle)
    if phone.strip():
        extras.append(phone.strip())
    extras.append("www.purnabramha.com")
    extra_line = "  ·  ".join(extras)
    final_sub = sub.strip()
    if extra_line:
        final_sub = (final_sub + "  ·  " + extra_line) if final_sub else extra_line

    try:
        meta = await _process_video(
            src_path, dst_path, headline, final_sub, byline, use_logo,
            position=position, show_footer=show_footer,
            headline_size=headline_size, subline_size=subline_size,
        )
    finally:
        try: os.remove(src_path)
        except Exception: pass

    doc = {
        "video_id": video_id,
        "center": center,
        "headline": headline,
        "sub": sub,
        "byline": byline,
        "use_logo": bool(use_logo),
        "position": position,
        "show_footer": bool(show_footer),
        "headline_size": headline_size,
        "subline_size": subline_size,
        "asset_path": dst_path,
        "size_kb": meta["size_kb"],
        "duration_s": meta["duration_s"],
        "created_by": session.get("managerName") or session.get("mobile") or "Unknown",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
        "download_count": 0,
    }
    await db.marketing_videos.insert_one(doc)
    return {
        "video_id": video_id,
        "size_kb": meta["size_kb"],
        "duration_s": meta["duration_s"],
        "url": f"/api/marketing/videos/asset/{video_id}",
    }


class BaseReq(BaseModel):
    token: str


class ListReq(BaseReq):
    center: Optional[str] = None
    limit: int = 30


@router.post("/list")
async def list_videos(req: ListReq):
    session = await check_access(req.token)
    q: dict = {"status": {"$ne": "deleted"}}
    if req.center:
        q["center"] = req.center.upper()
    elif not (session.get("is_super_admin") or session.get("is_admin")):
        own = (session.get("center") or "").upper()
        if own:
            q["center"] = own
    rows = await db.marketing_videos.find(
        q, {"_id": 0, "asset_path": 0}
    ).sort("created_at", -1).limit(req.limit).to_list(req.limit)
    return {"items": rows, "count": len(rows)}


@router.post("/asset/{video_id}")
async def asset(video_id: str, req: BaseReq):
    await check_access(req.token)
    doc = await db.marketing_videos.find_one({"video_id": video_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Video not found")
    p = doc.get("asset_path")
    if not p or not os.path.exists(p):
        raise HTTPException(404, "Asset missing")
    await db.marketing_videos.update_one(
        {"video_id": video_id}, {"$inc": {"download_count": 1}}
    )
    return StreamingResponse(
        open(p, "rb"), media_type="video/mp4",
        headers={"Content-Disposition": f'attachment; filename="Purnabramha_{video_id}.mp4"'},
    )


@router.get("/asset/{video_id}")
async def asset_get(video_id: str, token: str):
    """Convenience GET wrapper so plain <video src=...> tags can stream the file."""
    await check_access(token)
    doc = await db.marketing_videos.find_one({"video_id": video_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Video not found")
    p = doc.get("asset_path")
    if not p or not os.path.exists(p):
        raise HTTPException(404, "Asset missing")
    return StreamingResponse(open(p, "rb"), media_type="video/mp4")


# ─────────────────── Instagram Audio Suggestions ─────────────────────────
class MusicReq(BaseReq):
    headline: str = ""
    sub: str = ""
    occasion: Optional[str] = None       # e.g. "Wedding", "Anniversary", "Festival"
    mood: Optional[str] = None           # e.g. "Joyful", "Devotional", "Energetic"


@router.post("/music-suggestions")
async def music_suggestions(req: MusicReq):
    """Suggest 4-6 Instagram Reels audio tracks that pair well with the video.

    Uses Claude via the Emergent Universal Key. Tracks are chosen from the
    royalty-free / trending-Reels-safe pool so managers can search them by
    name inside Instagram's audio library.
    """
    await check_access(req.token)
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as e:
        raise HTTPException(503, f"LLM library not available: {e}")
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(503, "EMERGENT_LLM_KEY not configured")

    system = (
        "You are a Maharashtrian-restaurant social-media specialist who curates "
        "Instagram Reels audio. Suggest 5 trending audio tracks (royalty-free "
        "OR widely-available on Instagram's own audio library) that fit the "
        "Purnabramha brand: authentic, premium, joyful, traditional. Favour "
        "Maharashtrian folk, devotional lavani, dhol-tasha, soft sitar, "
        "instrumental Marathi covers, OR safe Bollywood instrumental cuts. "
        "AVOID copyrighted lyrics-heavy modern Bollywood that can mute the post."
    )
    user_prompt = f"""Suggest 5 Instagram Reels audio tracks for this branded restaurant video.

Headline / caption: "{req.headline}"
Sub-line: "{req.sub}"
Occasion (optional): "{req.occasion or 'general showcase'}"
Mood (optional): "{req.mood or 'warm, premium, Maharashtrian'}"

Return STRICT JSON only, no preamble, no markdown:
{{
  "tracks": [
    {{
      "name": "exact searchable track name as it appears in Instagram audio",
      "artist": "composer / performer (or 'Traditional' if folk)",
      "vibe": "ONE short phrase describing why this fits, e.g. 'Soft sitar + tabla — calm pride'",
      "why_fits": "ONE sentence justifying the pairing with the headline above"
    }}
  ]
}}

Constraints:
- Provide exactly 5 tracks, ordered best→good.
- Track names must be ACTUAL searchable Instagram audio (no fictional names).
- Mix moods: 1 devotional, 1 folk-energetic, 1 cinematic-instrumental, 1 nostalgic-Marathi, 1 modern-uplifting.
"""
    chat = LlmChat(
        api_key=api_key,
        session_id=f"video-music-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    raw = await chat.send_message(UserMessage(text=user_prompt))
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    import json
    try:
        data = json.loads(text)
        tracks = data.get("tracks") or []
    except Exception:
        logger.warning(f"music suggestions parse failed: {text[:200]}")
        tracks = []
    # Attach a deep-search link for each
    for t in tracks:
        q = f"{t.get('name','')} {t.get('artist','')}".strip()
        if q:
            t["instagram_search_url"] = (
                f"https://www.instagram.com/reels/audio/?q={q.replace(' ', '+')}"
            )
    return {"tracks": tracks, "count": len(tracks)}
