"""Center Manager Advertisement Creator — Marketing / Creative Studio feature.

Provides:
  - POST /api/marketing/ads/generate        → generate AI creative (Nano Banana)
  - POST /api/marketing/ads/caption         → generate Marathi/English caption
  - POST /api/marketing/ads/history         → list past creations
  - POST /api/marketing/ads/asset           → fetch generated image bytes
  - POST /api/marketing/ads/track-download  → bump download counter
  - POST /api/marketing/ads/templates/list  → list caption templates (admin + viewer)
  - POST /api/marketing/ads/templates/save  → create / update caption template (admin)
  - POST /api/marketing/ads/templates/delete → delete template (admin)
  - POST /api/marketing/ads/usage-report    → admin-only usage report

Storage: generated images saved to /app/backend/raw_uploads/ad_creations/<center>/<id>.png
DB collections:
  - ad_creations         (history of every generated creative)
  - ad_caption_templates (admin-curated caption library)

Permissions:
  - Generate: Center Manager / Admin / Super Admin
  - Templates manage / Usage report: Admin / Super Admin only
"""

import base64
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from server import db  # type: ignore
from routes.center_accounts import check_access

load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/marketing/ads", tags=["marketing-ads"])

ASSET_DIR = "/app/backend/raw_uploads/ad_creations"
os.makedirs(ASSET_DIR, exist_ok=True)

# Brand constants — surfaced into the Gemini prompt so the AI always knows
# the colour palette + design language we want.
BRAND_COLORS = "deep maroon/dark brown (#8B0000 to #5C0000), warm gold (#D4A745), cream white (#FAF3E7)"
BRAND_DESIGN = (
    "premium Apple-style minimalism, clean composition, modern luxury "
    "Maharashtrian branding with subtle banana-leaf textures, copper utensils, "
    "elegant brass-rim plates, soft cream backdrop, premium food photography lighting"
)
BRAND_NAME = "Purnabramha — Authentic Maharashtrian Cuisine"

# Aspect-ratio hints sent to Nano Banana
ASPECT_PROMPT = {
    "1:1": "square Instagram post composition (1:1)",
    "9:16": "vertical story / reel composition (9:16, full-bleed)",
    "4:5": "portrait poster composition (4:5)",
}

# --- helpers --------------------------------------------------------------

def _is_admin(session: dict) -> bool:
    if session.get("is_super_admin") or session.get("is_admin"):
        return True
    roles = session.get("roles") or {}
    role_key = (session.get("role_key") or "").lower()
    return role_key in {"admin", "super_admin", "marketing"} or bool(
        roles.get("admin") or roles.get("super_admin") or roles.get("marketing")
    )


def _is_center_manager_or_above(session: dict) -> bool:
    if _is_admin(session):
        return True
    role_key = (session.get("role_key") or "").lower()
    return role_key in {"center_manager", "manager", "operations"} or bool(
        (session.get("roles") or {}).get("center_manager")
    )


# --- ad generation --------------------------------------------------------

class AdGenerateRequest(BaseModel):
    token: str
    manager_name: str
    center: str
    language: str               # 'Marathi' | 'English' | 'Bilingual'
    menu_item: str              # e.g. "Misal Pav"
    festival_theme: str         # e.g. "Mother's Day"
    output_format: str          # '1:1' | '9:16' | '4:5'
    photo_base64: Optional[str] = None  # data URL or raw base64
    caption_marathi: Optional[str] = None
    caption_english: Optional[str] = None
    # When true, return ONLY the caption (skip the image gen call) — used by
    # the "Regenerate caption" button.
    caption_only: bool = False


def _strip_data_url(b64: str) -> str:
    if b64.startswith("data:"):
        return b64.split(",", 1)[1]
    return b64


def _build_image_prompt(req: AdGenerateRequest) -> str:
    """Compose the Gemini prompt that drives the creative.

    The instruction is deliberately rich + opinionated to push the AI toward
    the Purnabramha brand language and away from generic AI-slop output.
    """
    aspect = ASPECT_PROMPT.get(req.output_format, ASPECT_PROMPT["1:1"])
    caption_line = req.caption_marathi or req.caption_english or ""
    return f"""You are designing a premium social-media advertisement for "{BRAND_NAME}".

Aspect ratio: {aspect}. The final image MUST honour this aspect ratio exactly.

USE THE PERSON'S FACE FROM THE REFERENCE IMAGE.
- Place a clean, professional cutout of THE EXACT PERSON in the reference photo.
- Keep their face recognisable. Soften the background; integrate them tastefully.
- Position the person on the LEFT third (or top third for 9:16), leaving the
  RIGHT/BOTTOM portion for the food showcase.
- Person should be smiling warmly, in welcoming Maharashtrian-host posture.

FOOD HERO:
- Showcase a beautifully plated portion of "{req.menu_item}".
- Authentic, traditional preparation (no fusion). Premium food photography:
  brass-rim plate or banana leaf, soft golden light, glistening textures,
  steam where appropriate. Garnish with fresh coriander / kothimbir.

BRAND VISUAL LANGUAGE:
- Colour palette: {BRAND_COLORS}.
- Design language: {BRAND_DESIGN}.
- Subtle cultural motifs: banana-leaf veins, faint paisley border, brass copper
  highlights. Keep them sparing and refined, never busy.
- Mood: {req.festival_theme}.

TYPOGRAPHY OVERLAY (PART OF THE IMAGE):
- Place the headline at the visual sweet-spot, large and confident:
    "{caption_line}"
- Below the headline, render the manager's name in bold elegant serif:
    "{req.manager_name}"
- Add a small footer line:
    "{BRAND_NAME}"
- Typography colours: warm gold and cream white on dark backgrounds, deep
  maroon on cream. High readability — never overlap food or face.

GENERAL RULES:
- Apple-style clean composition, no clutter, no stock-photo cliches.
- No fusion food, no Western plating.
- High dynamic range, natural lighting, premium-restaurant feel.
- Face and food must both be clearly visible and proportionate.
- Output a single finished image, NOT a sketch or wireframe.
"""


async def _generate_caption(req: AdGenerateRequest) -> dict:
    """Generate emotional Marathi + English caption via Claude."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(503, "EMERGENT_LLM_KEY not configured")

    system = (
        "You are a Marathi advertising copywriter for Purnabramha — a premium "
        "authentic Maharashtrian restaurant brand. Compose short, emotional, "
        "warm captions that honour Maharashtrian culture and Purnabramha's "
        "luxury brand dignity. Never use fusion or Western references."
    )

    user_prompt = f"""Write a social-media caption for an advertisement.

Inputs:
- Manager name (host): {req.manager_name}
- Center city: {req.center}
- Menu hero: {req.menu_item}
- Festival / theme: {req.festival_theme}
- Format: {req.output_format}
- Language wanted: {req.language}

Return STRICT JSON only, no markdown fence, with keys:
  - "marathi": 1 short emotional Marathi caption (2 lines max). Mention the
    manager naturally (e.g. "<Name> ताईंसोबत" or "<Name> कडून"). Use Devanagari.
  - "english": 1 short emotional English line (1-2 lines max). Keep it warm
    and luxurious, mention manager naturally.
  - "headline": the single best headline (Marathi if Bilingual/Marathi was
    requested, otherwise English). This is what we'll burn into the creative.

Example for Misal Pav + Mother's Day + manager "Sneha":
{{"marathi":"आज मातृ-दिनाचा खास आग्रह...\\nस्नेहा ताईंकडून मिसळ पावाचा अस्सल स्वाद!", "english":"Served with love, hosted proudly by Sneha Tai.","headline":"आज मातृ-दिनाचा खास आग्रह...\\nस्नेहा ताईंकडून मिसळ पावाचा अस्सल स्वाद!"}}
"""

    chat = LlmChat(
        api_key=api_key,
        session_id=f"ad-caption-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    raw = await chat.send_message(UserMessage(text=user_prompt))
    text = (raw or "").strip()
    # Clean code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
    import json
    try:
        data = json.loads(text)
    except Exception:
        # Fallback: pack the whole thing as marathi and headline
        data = {"marathi": text, "english": "", "headline": text}
    return {
        "marathi": data.get("marathi", ""),
        "english": data.get("english", ""),
        "headline": data.get("headline") or data.get("marathi") or data.get("english", ""),
    }


@router.post("/caption")
async def generate_caption(req: AdGenerateRequest):
    """Generate (or regenerate) just the caption — fast, no image gen."""
    session = await check_access(req.token)
    if not _is_center_manager_or_above(session):
        raise HTTPException(403, "Not permitted to create advertisements")
    caption = await _generate_caption(req)
    return {"caption": caption}


@router.post("/generate")
async def generate_ad(req: AdGenerateRequest):
    """Generate the full ad: caption (if missing) + image. Stores history."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

    session = await check_access(req.token)
    if not _is_center_manager_or_above(session):
        raise HTTPException(403, "Not permitted to create advertisements")
    if not req.photo_base64:
        raise HTTPException(400, "Manager photo is required")

    # 1) Caption
    if req.caption_marathi or req.caption_english:
        caption = {
            "marathi": req.caption_marathi or "",
            "english": req.caption_english or "",
            "headline": req.caption_marathi or req.caption_english or "",
        }
    else:
        try:
            caption = await _generate_caption(req)
            # Re-inject into req so the image prompt uses the new caption
            req.caption_marathi = caption["marathi"]
            req.caption_english = caption["english"]
        except Exception as e:
            logger.warning(f"caption generation failed, using fallback: {e}")
            caption = {
                "marathi": f"{req.manager_name} ताईंकडून प्रेमाने सादर",
                "english": f"Hosted with love by {req.manager_name}",
                "headline": f"{req.manager_name} ताईंकडून प्रेमाने सादर",
            }
            req.caption_marathi = caption["marathi"]

    if req.caption_only:
        return {"caption": caption}

    # 2) Image generation via Nano Banana
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(503, "EMERGENT_LLM_KEY not configured")

    photo_b64 = _strip_data_url(req.photo_base64)
    prompt = _build_image_prompt(req)

    chat = LlmChat(
        api_key=api_key,
        session_id=f"ad-image-{uuid.uuid4().hex[:8]}",
        system_message="You compose premium Maharashtrian restaurant advertisements with the user's face preserved exactly.",
    ).with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])

    try:
        _text, images = await chat.send_message_multimodal_response(
            UserMessage(text=prompt, file_contents=[ImageContent(photo_b64)])
        )
    except Exception as e:
        logger.error(f"Nano Banana failed: {e}", exc_info=True)
        raise HTTPException(502, f"AI image generation failed: {e}")

    if not images:
        raise HTTPException(502, "AI returned no image — please retry")

    img = images[0]
    image_bytes = base64.b64decode(img["data"])

    # 3) Persist to disk + history
    ad_id = str(uuid.uuid4())
    center_safe = (req.center or "UNKNOWN").replace("/", "_")
    sub = os.path.join(ASSET_DIR, center_safe)
    os.makedirs(sub, exist_ok=True)
    path = os.path.join(sub, f"{ad_id}.png")
    with open(path, "wb") as f:
        f.write(image_bytes)

    record = {
        "ad_id": ad_id,
        "center": req.center,
        "manager_name": req.manager_name,
        "menu_item": req.menu_item,
        "festival_theme": req.festival_theme,
        "language": req.language,
        "output_format": req.output_format,
        "caption_marathi": caption.get("marathi", ""),
        "caption_english": caption.get("english", ""),
        "headline": caption.get("headline", ""),
        "asset_path": path,
        "mime_type": img.get("mime_type", "image/png"),
        "size_bytes": len(image_bytes),
        "download_count": 0,
        "created_by": session.get("managerName") or session.get("mobile") or "Unknown",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
    await db.ad_creations.insert_one(record)

    return {
        "ad_id": ad_id,
        "image_base64": img["data"],
        "mime_type": img.get("mime_type", "image/png"),
        "caption": caption,
        "size_kb": round(len(image_bytes) / 1024.0, 1),
    }


# --- history / asset / tracking ------------------------------------------

class HistoryRequest(BaseModel):
    token: str
    center: Optional[str] = None
    limit: int = 50


@router.post("/history")
async def list_history(req: HistoryRequest):
    session = await check_access(req.token)
    if not _is_center_manager_or_above(session):
        raise HTTPException(403, "Not permitted")

    q = {}
    if req.center:
        q["center"] = req.center
    # Non-admin center managers can only see their own center's creations
    if not _is_admin(session):
        own = session.get("center")
        if own:
            q["center"] = own

    cur = db.ad_creations.find(q, {"_id": 0, "asset_path": 0}).sort("created_at", -1).limit(req.limit)
    rows = await cur.to_list(req.limit)
    return {"items": rows}


class AssetRequest(BaseModel):
    token: str
    ad_id: str


@router.post("/asset")
async def fetch_asset(req: AssetRequest):
    session = await check_access(req.token)
    if not _is_center_manager_or_above(session):
        raise HTTPException(403, "Not permitted")
    doc = await db.ad_creations.find_one({"ad_id": req.ad_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Ad not found")
    # Center-scope for non-admins
    if not _is_admin(session):
        if doc.get("center") and doc["center"] != session.get("center"):
            raise HTTPException(403, "Not your center's ad")
    path = doc.get("asset_path")
    if not path or not os.path.exists(path):
        raise HTTPException(404, "Asset file no longer exists")
    with open(path, "rb") as f:
        return Response(
            content=f.read(),
            media_type=doc.get("mime_type", "image/png"),
            headers={"Content-Disposition": f'inline; filename="ad_{req.ad_id}.png"'},
        )


@router.post("/track-download")
async def track_download(req: AssetRequest):
    session = await check_access(req.token)
    if not _is_center_manager_or_above(session):
        raise HTTPException(403, "Not permitted")
    result = await db.ad_creations.update_one(
        {"ad_id": req.ad_id}, {"$inc": {"download_count": 1}}
    )
    return {"updated": result.modified_count}


# --- caption templates (admin) -------------------------------------------

class TemplateListRequest(BaseModel):
    token: str
    festival_theme: Optional[str] = None
    language: Optional[str] = None


class TemplateSaveRequest(BaseModel):
    token: str
    template_id: Optional[str] = None
    festival_theme: str
    language: str
    text_marathi: str = ""
    text_english: str = ""


class TemplateDeleteRequest(BaseModel):
    token: str
    template_id: str


@router.post("/templates/list")
async def list_templates(req: TemplateListRequest):
    session = await check_access(req.token)
    if not _is_center_manager_or_above(session):
        raise HTTPException(403, "Not permitted")
    q = {}
    if req.festival_theme:
        q["festival_theme"] = req.festival_theme
    if req.language:
        q["language"] = req.language
    items = await db.ad_caption_templates.find(q, {"_id": 0}).sort("created_at", -1).to_list(300)
    return {"items": items}


@router.post("/templates/save")
async def save_template(req: TemplateSaveRequest):
    session = await check_access(req.token)
    if not _is_admin(session):
        raise HTTPException(403, "Admin only")
    tid = req.template_id or str(uuid.uuid4())
    doc = {
        "template_id": tid,
        "festival_theme": req.festival_theme,
        "language": req.language,
        "text_marathi": req.text_marathi,
        "text_english": req.text_english,
        "updated_by": session.get("managerName") or "Admin",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    existing = await db.ad_caption_templates.find_one({"template_id": tid})
    if existing:
        await db.ad_caption_templates.update_one({"template_id": tid}, {"$set": doc})
    else:
        doc["created_at"] = doc["updated_at"]
        await db.ad_caption_templates.insert_one(doc)
    return {"template_id": tid, "saved": True}


@router.post("/templates/delete")
async def delete_template(req: TemplateDeleteRequest):
    session = await check_access(req.token)
    if not _is_admin(session):
        raise HTTPException(403, "Admin only")
    r = await db.ad_caption_templates.delete_one({"template_id": req.template_id})
    if r.deleted_count == 0:
        raise HTTPException(404, "Template not found")
    return {"deleted": 1}


# --- masters list helpers (menu items + centers) -------------------------

@router.post("/masters")
async def get_masters(req: HistoryRequest):
    """Return the menu items + centers + festival/theme defaults for the Ad
    Creator form so the UI never hardcodes anything."""
    session = await check_access(req.token)
    if not _is_center_manager_or_above(session):
        raise HTTPException(403, "Not permitted")

    # Menu items — pull distinct names from existing master collection(s)
    menu_items = []
    try:
        for coll in ("menu_items", "menu", "menu_card"):
            names = await db[coll].distinct("name")
            if names:
                menu_items = sorted({n for n in names if n})
                break
    except Exception:
        menu_items = []
    if not menu_items:
        # Fallback (rare — only when master is empty)
        menu_items = [
            "Misal Pav", "Puran Poli", "Kothimbir Vadi", "Modak",
            "Sabudana Khichadi", "Basundi", "Maharashtrian Thali",
            "Vada Pav", "Solkadhi",
        ]

    # Centers — only those the user can see
    centers = []
    if _is_admin(session):
        cs = await db.centers.find({}, {"_id": 0, "code": 1, "name": 1}).to_list(200)
        centers = [c["code"] for c in cs if c.get("code")]
    elif session.get("center"):
        centers = [session["center"]]

    festivals = [
        "Weekend", "Adhik Maas", "Mother's Day", "Family Dining",
        "Corporate Lunch", "Traditional Maharashtrian",
        "Women-led Brand", "Healthy Food", "Festival Season",
        "Ganesh Chaturthi", "Diwali", "Gudi Padwa",
    ]
    return {
        "menu_items": menu_items,
        "centers": centers,
        "festivals": festivals,
        "languages": ["Marathi", "English", "Bilingual"],
        "output_formats": [
            {"id": "1:1", "label": "Instagram Post (1:1)"},
            {"id": "9:16", "label": "Story / Reel (9:16)"},
            {"id": "4:5", "label": "Poster (4:5)"},
        ],
    }


# --- usage report (admin) ------------------------------------------------

@router.post("/usage-report")
async def usage_report(req: HistoryRequest):
    session = await check_access(req.token)
    if not _is_admin(session):
        raise HTTPException(403, "Admin only")

    pipeline = [
        {"$group": {
            "_id": {"center": "$center", "manager_name": "$manager_name"},
            "creations": {"$sum": 1},
            "downloads": {"$sum": "$download_count"},
            "last_used": {"$max": "$created_at"},
        }},
        {"$sort": {"creations": -1}},
    ]
    rows = await db.ad_creations.aggregate(pipeline).to_list(500)
    cleaned = [
        {
            "center": (r["_id"] or {}).get("center"),
            "manager_name": (r["_id"] or {}).get("manager_name"),
            "creations": r.get("creations", 0),
            "downloads": r.get("downloads", 0),
            "last_used": r.get("last_used"),
        }
        for r in rows
    ]
    return {"rows": cleaned}
