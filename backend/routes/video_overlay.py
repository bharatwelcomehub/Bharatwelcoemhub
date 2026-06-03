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
                  position: str = "bottom") -> str:
    """Compose the ffmpeg filter_complex chain for overlay."""
    parts = []

    # 1) Dark CHOCOLATE strip (Purnabramha brand 2026)
    if position == "top":
        parts.append(
            "drawbox=x=0:y=0:w=iw:h=ih*0.30:color=0x2B1810@0.85:t=fill"
        )
        # Antique gold border line at bottom of band
        parts.append(
            "drawbox=x=0:y=ih*0.30-4:w=iw:h=4:color=0xBF8C32@1.0:t=fill"
        )
        y_h = "20"
        y_s = "h*0.10"
        y_b = "h*0.20"
    else:
        parts.append(
            "drawbox=x=0:y=ih*0.70:w=iw:h=ih*0.30:color=0x2B1810@0.85:t=fill"
        )
        # Antique gold border line at top of band
        parts.append(
            "drawbox=x=0:y=ih*0.70:w=iw:h=4:color=0xBF8C32@1.0:t=fill"
        )
        y_h = "h*0.74"
        y_s = "h*0.82"
        y_b = "h*0.90"

    # 2) Headline (auto-pick font based on script) — Antique Gold, larger
    if headline:
        f = DEV_FONT if _has_devanagari(headline) else LATIN_FONT
        if os.path.exists(f):
            parts.append(
                f"drawtext=fontfile={f}:text='{_ffmpeg_escape(headline)}':"
                f"fontcolor=0xDCAE50:fontsize=h/12:"
                f"x=(w-text_w)/2:y={y_h}:"
                f"shadowcolor=black@0.8:shadowx=3:shadowy=3"
            )

    # 3) Sub-headline — Warm Cream
    if sub:
        f = DEV_FONT if _has_devanagari(sub) else LATIN_ITALIC
        if os.path.exists(f):
            parts.append(
                f"drawtext=fontfile={f}:text='{_ffmpeg_escape(sub)}':"
                f"fontcolor=0xFAF0DC:fontsize=h/22:"
                f"x=(w-text_w)/2:y={y_s}:"
                f"shadowcolor=black@0.6:shadowx=2:shadowy=2"
            )

    # 4) Byline — soft cream
    if byline:
        f = DEV_FONT if _has_devanagari(byline) else LATIN_ITALIC
        if os.path.exists(f):
            parts.append(
                f"drawtext=fontfile={f}:text='— {_ffmpeg_escape(byline)} —':"
                f"fontcolor=0xF0E4C8:fontsize=h/30:"
                f"x=(w-text_w)/2:y={y_b}"
            )

    chain = ",".join(parts)
    if has_logo:
        # Logo: overlay top-right small. Use the second input.
        # Full filter graph: [0:v]...[base];[1:v]scale=...[logo];[base][logo]overlay
        return (
            f"[0:v]{chain}[base];"
            f"[1:v]scale=ih*0.18:-1[logo];"
            f"[base][logo]overlay=x=W-w-20:y=20"
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
) -> dict:
    """Run ffmpeg with the composed filter, return {size_kb, duration_s}."""
    if not os.path.exists(src_path):
        raise HTTPException(500, "Uploaded file disappeared")
    has_logo = use_logo and os.path.exists(LOGO_PATH)
    filter_complex = _build_filter(headline, sub, byline, has_logo)
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

    try:
        meta = await _process_video(
            src_path, dst_path, headline, sub, byline, use_logo
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
