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
BRAND_COLORS = (
    "Dark Chocolate Brown (#2B1810) as primary background, "
    "Rich Antique Gold (#BF8C32) for headings/borders/accents, "
    "Deep Maroon (#660E0E) for festive/celebration elements, "
    "Warm Cream / Off-White (#FAF0DC) for readability text. "
    "Avoid neon, bright corporate blue, fluorescent green, cartoonish palettes."
)
BRAND_DESIGN = (
    "Premium Maharashtrian heritage aesthetic — feels like a luxury wedding "
    "invitation or hospitality brand. Traditional decorative motifs: paisley, "
    "rangoli, warli art, temple bells, diyas, marigold garlands, banana-leaf "
    "veins, brass-copper utensils, brass-rim plates, traditional textile "
    "patterns. Premium serif-style typography vibes. Soft cream-on-chocolate "
    "contrast. Warm, emotional, culturally rich — NEVER modern-corporate, "
    "NEVER cartoonish, NEVER generic Canva-template look."
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
    roles = session.get("roles") or {}
    if role_key in {"center_manager", "manager", "operations"}:
        return True
    # Honor any role flag commonly granted to center managers
    return bool(
        roles.get("center_manager")
        or roles.get("operations")
        or roles.get("ops")
        or roles.get("manager")
    )


# --- ad generation --------------------------------------------------------

class AdGenerateRequest(BaseModel):
    token: str
    manager_name: str
    center: str
    language: str               # 'Marathi' | 'English' | 'Bilingual'
    menu_item: str              # e.g. "Misal Pav"
    festival_theme: str         # e.g. "Mother's Day" — kept for back-compat; "subject_text" preferred
    output_format: str          # '1:1' | '9:16' | '4:5'
    photo_base64: Optional[str] = None  # data URL or raw base64 — NOW OPTIONAL
    caption_marathi: Optional[str] = None
    caption_english: Optional[str] = None
    # When true, return ONLY the caption (skip the image gen call) — used by
    # the "Regenerate caption" button.
    caption_only: bool = False
    # NEW — guest testimonial mode
    guest_name: Optional[str] = None     # e.g. "Balgopal"
    subject_text: Optional[str] = None   # e.g. "Loved the Thali", "First-time visit"
    # NEW — group photo support (manager-toggled, also auto-prompted)
    is_group_photo: bool = False
    # NEW — optional menu/dish reference image uploaded by the center manager
    menu_item_image_base64: Optional[str] = None


def _is_balgopal(guest_name: Optional[str], subject_text: Optional[str] = None) -> bool:
    """Detect Balgopal (kids) mode from guest name or subject text.

    Balgopal = young Krishna; used by Purnabramha as a loving term for kid
    customers. When set, the creative celebrates the child as a young food
    champion (super hero / super queen / star eater / farmer friend) instead
    of a regular guest testimonial.
    """
    blob = f"{guest_name or ''} {subject_text or ''}".lower()
    return "balgopal" in blob or "बालगोपाळ" in (guest_name or "") + (subject_text or "")


def _strip_data_url(b64: str) -> str:
    if b64.startswith("data:"):
        return b64.split(",", 1)[1]
    return b64


def _build_image_prompt(req: AdGenerateRequest) -> str:
    """Compose the Gemini prompt that drives the creative.

    IMPORTANT: This prompt instructs the LLM to produce a **clean visual ONLY**
    — no text, no caption, no headline, AND no person/face. The actual guest
    photo is composited onto the LEFT panel server-side via Pillow so faces are
    always EXACTLY the uploaded image. Text is overlaid crisply via Pillow +
    Noto Sans Devanagari so Marathi script always renders perfectly.

    Modes:
    - BALGOPAL (kids) mode: special motifs around the photo area (star burst
      added server-side around the actual photo).
    - GUEST mode (photo provided): AI generates ONLY the brand backdrop + food
      on the RIGHT half; the LEFT half MUST stay clean for the real photo.
    - PRODUCT mode (no photo): pure dish-led advertisement (no person).
    """
    aspect = ASPECT_PROMPT.get(req.output_format, ASPECT_PROMPT["1:1"])
    has_photo = bool(req.photo_base64)
    has_menu_img = bool(req.menu_item_image_base64)
    subject = (req.subject_text or req.festival_theme or "").strip()
    balgopal = _is_balgopal(req.guest_name, req.subject_text)

    # ── Person block: when a guest photo is provided we explicitly tell the
    # AI NOT to draw any person at all — the real photo is composited later.
    if has_photo:
        if req.output_format == "9:16":
            safe_area = "Leave the TOP 50% of the canvas COMPLETELY clean (cream/gold soft texture, NO food, NO person, NO objects) — the real guest photo will be pasted there."
        else:
            safe_area = "Leave the LEFT 45% of the canvas COMPLETELY clean (cream/gold soft texture, NO food, NO person, NO objects) — the real guest photo will be pasted there."
        person_block = f"""NO HUMAN FIGURE IN THIS GENERATION.
- DO NOT add any human face, head, body, hand, silhouette, child, or person.
- DO NOT redraw, stylise, or interpret any guest.
- {safe_area}
- The real photo (with the real faces of the real guests) will be composited
  on top of that clean area by our server. Your job is ONLY the brand backdrop
  + food showcase on the OTHER half.
"""
    else:
        person_block = """NO PERSON IN THIS ADVERTISEMENT.
- This is a PRODUCT-LED creative. Do NOT add any human figure, face, hand, or silhouette.
- Use the full canvas to celebrate the food itself with rich, premium composition.
"""

    # Menu reference image (if uploaded) is authoritative
    if has_menu_img:
        menu_directive = f"""DISH REFERENCE IMAGE — FOOD-ONLY EXTRACTION.
- A reference image is provided. It MAY contain people, faces, decorative
  text, marketing layouts, or other clutter — IGNORE ALL OF THAT.
- Extract ONLY the FOOD content from the reference: the dish "{req.menu_item}",
  its plating, vessel, garnish, colour, portion size, side accompaniments.
- DO NOT copy any human face, child, person, model, hand, body part, text
  letter, logo, or watermark from the reference image.
- Re-photograph the EXTRACTED dish only in premium food-photography style —
  brass-rim plate or banana leaf, soft golden light, glistening textures,
  steam where appropriate. Garnish with fresh coriander / kothimbir.
- Place the food on the RIGHT half (or BOTTOM half for 9:16). Otherwise centred.
"""
    elif balgopal:
        menu_directive = f"""FOOD HERO — BALGOPAL FINISHED PLATE.
- Show a clean / nearly-empty plate of "{req.menu_item}" with just a few crumbs,
  curry smear, or one grain left — proof the child finished with love.
- Authentic Maharashtrian vessel (brass-rim plate or banana leaf).
- Place the plate on the RIGHT half (or BOTTOM half for 9:16), well away from the
  clean photo zone.
"""
    else:
        menu_directive = f"""FOOD HERO:
- Showcase a beautifully plated portion of "{req.menu_item}".
- Authentic, traditional preparation (no fusion). Premium food photography:
  brass-rim plate or banana leaf, soft golden light, glistening textures,
  steam where appropriate. Garnish with fresh coriander / kothimbir.
- Place the food on the RIGHT half (or BOTTOM half for 9:16) when a guest photo
  is being composited. Otherwise centred / full-canvas.
"""

    # Critical: where to leave clean text-safe area for our crisp overlay
    safe_zone_block = """TEXT-SAFE / LOGO-SAFE ZONE — CRITICAL:
- DO NOT render ANY text, letters, words, captions, headlines, slogans, hashtags,
  numbers, dates, prices, watermarks, or stamps INSIDE the image.
- DO NOT draw any logo, brand-mark, mandala-with-text, or wordmark. Specifically
  DO NOT render the word "Purnabramha", "पूर्णब्रम्ह", "Manaswini Foods", or any
  variant — the real Purnabramha logo is composited afterwards by our server.
- Leave the BOTTOM 25% of the canvas visually calm — soft gradient, low-detail
  background — so crisp studio typography can be overlaid afterwards.
- Leave the TOP-RIGHT corner calm too (no decoration, no food) — room for the
  real brand logo.
"""

    mood_line = "young food champion · joyful pride · gentle storybook warmth" if balgopal \
        else (subject or "warm hospitality")

    return f"""You are designing a premium social-media advertisement for "{BRAND_NAME}".

Aspect ratio: {aspect}. The final image MUST honour this aspect ratio exactly.

{person_block}
{menu_directive}
BRAND VISUAL LANGUAGE:
- Colour palette: {BRAND_COLORS}.
- Design language: {BRAND_DESIGN}.
- Subtle cultural motifs: banana-leaf veins, faint paisley border, brass copper
  highlights. Keep them sparing and refined, never busy.
- Subject / mood (use as creative direction, NOT as literal headline): {mood_line}.

{safe_zone_block}
GENERAL RULES:
- Apple-style clean composition, no clutter, no stock-photo cliches.
- No fusion food, no Western plating.
- High dynamic range, natural lighting, premium-restaurant feel.
- Output a single finished image, NOT a sketch or wireframe.
- If ANY reference image contains a person/child/face, do NOT carry that person
  into the output. Reference images are food references only — use them for
  plating cues, never for human likeness.
"""


async def _generate_caption(req: AdGenerateRequest) -> dict:
    """Generate emotional Marathi + English caption via Claude.

    New testimonial-first mode: if guest_name + subject_text are provided, the
    caption celebrates the guest's experience. Otherwise falls back to a
    product / occasion caption.
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(503, "EMERGENT_LLM_KEY not configured")

    system = (
        "You are a Marathi advertising copywriter for Purnabramha — a premium "
        "authentic Maharashtrian restaurant brand. Compose short, emotional, "
        "warm captions that honour Maharashtrian culture and Purnabramha's "
        "luxury brand dignity. Never use fusion or Western references. "
        "CRITICAL: NEVER use the forced/templated phrases "
        "'आठवड्याच्या शेवटी', 'एक आठवण', 'घरची आठवण', 'weekend memory', or any "
        "similar weekly-memory cliche. Write fresh, original copy specific to "
        "the inputs."
    )

    guest_name = (req.guest_name or "").strip()
    subject_text = (req.subject_text or "").strip()
    poster = (req.manager_name or "").strip()
    balgopal = _is_balgopal(req.guest_name, req.subject_text)
    mode = "balgopal_kid" if balgopal else ("testimonial" if (guest_name or subject_text) else "product")

    balgopal_brief = ""
    if balgopal:
        balgopal_brief = """
BALGOPAL (KIDS) MODE — IMPORTANT:
- The guest is a CHILD ("Balgopal" = young Krishna = Purnabramha's loving term for kid customers).
- The caption celebrates the kid as a young food champion who CLEANED THEIR PLATE.
- Pick ONE archetype that fits the child's mood / subject:
    a) "Star Eater" — they earned a गोल्डन तारा (gold star) for finishing the plate
    b) "Super Hero / Super Queen" — कापडी cape / dupatta of a food champion
    c) "Farmer Friend" — they honoured every grain (no food wasted), अन्नदात्याचा मित्र
- Use playful but dignified language. Never patronising, never baby-talk.
- Examples:
    "बालगोपाळ {gname}जींना ⭐ स्टार खाद्यवीराचं नाव!"
    "{gname}जींनी पूर्ण ताट संपवली — आता आहेत 'पूर्णब्रह्माचे शूरवीर'!"
    "{gname} → Today's Super Hero who left no grain behind. 🌾"
""".replace("{gname}", guest_name or "बालगोपाळ")

    user_prompt = f"""Write a social-media caption for an advertisement.

Mode: {mode}
{balgopal_brief}
Inputs:
- Guest name (subject of the testimonial): {guest_name or "(none — product/occasion ad)"}
- Subject / message (what to convey): {subject_text or req.festival_theme}
- Posted by (host / center manager): {poster or "(unspecified)"}
- Center city: {req.center}
- Menu hero: {req.menu_item}
- Format: {req.output_format}
- Language wanted: {req.language}

Rules:
- If mode is balgopal_kid, follow the BALGOPAL brief above — celebrate the child finishing their plate as a young food champion.
- If guest_name is present (non-Balgopal), the caption is FROM THE BRAND celebrating the guest's
  visit/testimonial. Mention the guest naturally (e.g. "{guest_name}जींना आवडलं",
  "{guest_name} sir/madam loved...").
- If guest_name is empty, write a clean product/occasion caption around the menu hero.
- The "subject" tells you the emotional angle — interpret it, don't quote it verbatim.
- Keep it 1–2 short lines. Do NOT start with any templated weekly-memory phrase.
- Do NOT mention "आठवड्याच्या शेवटी" or "घरची आठवण" anywhere.

Return STRICT JSON only, no markdown fence, with keys:
  - "marathi": 1 short emotional Marathi caption (2 lines max). Use Devanagari.
  - "english": 1 short emotional English line (1-2 lines max). Warm, luxurious.
  - "headline": the single best headline that will be burned into the image
    (Marathi if Bilingual/Marathi was requested, otherwise English).

BILINGUAL ENFORCEMENT (CRITICAL):
- If language is "Bilingual", BOTH "marathi" and "english" MUST be filled with
  substantive, non-empty content. Do NOT leave either blank. Do NOT transliterate
  English into Marathi — write natural, idiomatic Marathi.
- If language is "Marathi", "marathi" MUST be filled (English may be empty).
- If language is "English", "english" MUST be filled (Marathi may be empty).

Example A (testimonial mode — guest "Balgopal" loved Thali):
{{"marathi":"बालगोपाळजींच्या ताटात पूर्णब्रह्म — हसरा क्षण, अस्सल चव!","english":"Balgopal ji loved every bite of our authentic Thali.","headline":"बालगोपाळजींच्या ताटात पूर्णब्रह्म — हसरा क्षण, अस्सल चव!"}}

Example B (product mode — Misal Pav, no guest):
{{"marathi":"तिखट, गरमा-गरम मिसळ — कोल्हापुरी थाटात!","english":"Fiery, fresh, and unapologetically Maharashtrian.","headline":"तिखट, गरमा-गरम मिसळ — कोल्हापुरी थाटात!"}}

Example C (BALGOPAL kid mode — guest Balgopal Riya finished her Puran Poli):
{{"marathi":"बालगोपाळ रियाजींनी ⭐ स्टार खाद्यवीराचं नाव — पुरणपोळी संपवली अगदी अन्न-वाया-न-घालता!","english":"Balgopal Riya earned today's Star Plate — finished every bite of her Puran Poli! 🌾","headline":"बालगोपाळ रिया → आजची स्टार खाद्यवीर ⭐"}}
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
    # Photo is OPTIONAL — when absent, we generate a product-only creative.

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
            who = req.guest_name or req.manager_name or "आमचे"
            caption = {
                "marathi": f"{who} ची आवडती चव — पूर्णब्रह्म",
                "english": f"A favourite at Purnabramha — featuring {req.menu_item}",
                "headline": f"{who} ची आवडती चव — पूर्णब्रह्म",
            }
            req.caption_marathi = caption["marathi"]

    if req.caption_only:
        return {"caption": caption}

    # 2) Image generation via Nano Banana
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(503, "EMERGENT_LLM_KEY not configured")

    prompt = _build_image_prompt(req)

    chat = LlmChat(
        api_key=api_key,
        session_id=f"ad-image-{uuid.uuid4().hex[:8]}",
        system_message="You compose premium Maharashtrian restaurant advertisements with the user's face preserved exactly.",
    ).with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])

    try:
        # Build reference image list for Nano Banana.
        # IMPORTANT: We deliberately do NOT pass the guest photo any more.
        # Nano Banana is unreliable at preserving real faces — so we tell it
        # to leave a clean panel for the photo, and Pillow composites the real
        # photo on top server-side. Only the dish image (if uploaded) is sent
        # as an authoritative reference.
        refs: list = []
        if req.menu_item_image_base64:
            refs.append(ImageContent(_strip_data_url(req.menu_item_image_base64)))
        if refs:
            _text, images = await chat.send_message_multimodal_response(
                UserMessage(text=prompt, file_contents=refs)
            )
        else:
            _text, images = await chat.send_message_multimodal_response(
                UserMessage(text=prompt)
            )
    except Exception as e:
        logger.error(f"Nano Banana failed: {e}", exc_info=True)
        raise HTTPException(502, f"AI image generation failed: {e}")

    if not images:
        raise HTTPException(502, "AI returned no image — please retry")

    img = images[0]
    raw_bytes = base64.b64decode(img["data"])

    # ── Composite the ACTUAL guest photo onto the LEFT panel (Pillow) ────
    # AI is told NOT to draw any person — we paste the real photo so the
    # guest's face is always 100% recognisable.
    if req.photo_base64:
        try:
            from utils.text_overlay import composite_guest_photo
            from PIL import Image as _PIL
            import io as _io
            guest_bytes = base64.b64decode(_strip_data_url(req.photo_base64))
            # Auto-detect "group" from manual checkbox OR wide aspect (>1.3:1)
            is_group_auto = req.is_group_photo
            try:
                _im = _PIL.open(_io.BytesIO(guest_bytes))
                if _im.width / max(_im.height, 1) >= 1.3:
                    is_group_auto = True
            except Exception:
                pass
            raw_bytes = composite_guest_photo(
                raw_bytes, guest_bytes,
                aspect=req.output_format,
                balgopal=_is_balgopal(req.guest_name, req.subject_text),
                is_group=is_group_auto,
            )
        except Exception as e:
            logger.warning(f"guest photo composite failed (keeping AI image): {e}")

    # ── Crisp text overlay (Pillow + Noto Sans Devanagari) ───────────────
    # The image LLM is instructed NOT to render text. We overlay caption +
    # logo + brand line server-side so Marathi script is pixel-perfect.
    try:
        from utils.text_overlay import apply_overlay
        image_bytes = apply_overlay(
            raw_bytes,
            headline_marathi=caption.get("marathi", ""),
            headline_english=caption.get("english", ""),
            byline=(req.guest_name or req.manager_name or ""),
            brand=BRAND_NAME,
            logo_path=LOGO_PATH if os.path.exists(LOGO_PATH) else None,
            position="bottom",
        )
    except Exception as e:
        logger.warning(f"text overlay failed, using raw AI image: {e}")
        image_bytes = raw_bytes

    # Refresh base64 (response carries the overlayed image)
    img["data"] = base64.b64encode(image_bytes).decode("ascii")

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
        "guest_name": req.guest_name or "",
        "subject_text": req.subject_text or "",
        "has_photo": bool(req.photo_base64),
        "has_menu_image": bool(req.menu_item_image_base64),
        "is_balgopal": _is_balgopal(req.guest_name, req.subject_text),
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


# --- Customer Party Invitation Generator ---------------------------------
# Used when a customer books their wedding / birthday / get-together at a
# Purnabramha center and wants a custom invitation card with the brand logo,
# center name, host name, occasion, date/time, and address.

LOGO_PATH = "/app/backend/static/purnabramha_logo.png"


class InvitationRequest(BaseModel):
    token: str
    center: str                              # PB-MGT etc — auto-resolves address
    host_name: str                           # required — name on the invite
    occasion: str                            # Wedding / Birthday / Get-together / Anniversary / Engagement
    occasion_other: Optional[str] = None     # if occasion == 'Other'
    event_date: str                          # YYYY-MM-DD
    event_time: str                          # e.g. "7:30 PM"
    center_address: Optional[str] = None     # if blank, auto-fill from centers collection
    menu_highlights: Optional[str] = None    # optional comma list, e.g. "Misal Pav, Puran Poli"
    language: str = "Bilingual"              # Marathi / English / Bilingual
    output_format: str = "4:5"               # 4:5 (poster) / 1:1 / 9:16
    photo_base64: Optional[str] = None       # optional host photo (data URL or raw b64)
    custom_message: Optional[str] = None     # optional "warm host note"
    is_group_photo: bool = False             # NEW — host photo is a family/couple/group


def _build_invitation_prompt(req: InvitationRequest, center_name: str, address_line: str) -> str:
    occ = req.occasion if req.occasion != "Other" else (req.occasion_other or "Celebration")
    if req.photo_base64:
        # Invitations are almost always hosted by a couple / family / team, so we
        # default to MULTI-PERSON-AWARE behaviour. The is_group_photo checkbox
        # only adds extra emphasis — it never relaxes the "preserve every face"
        # rule.
        if req.is_group_photo:
            photo_directive = (
                "FIRST reference image is a GROUP PHOTO of the hosts/family/team. Place ALL "
                "faces from that photo together as a soft-edged elegant group portrait at the "
                "TOP-CENTER inside a gold ornate rectangular frame (NOT a circle — circles "
                "crop people out). Preserve EVERY face exactly — do not crop anyone, do not "
                "alter features, do not add anyone new. Arrange the people warmly side-by-side, "
                "close together, smiling. "
            )
        else:
            photo_directive = (
                "FIRST reference image contains the host(s). Examine it carefully — it may be "
                "a SINGLE person, a COUPLE, a FAMILY, or a TEAM. Whatever the count, preserve "
                "EVERY face you see — do NOT crop anyone out, do NOT remove people, do NOT "
                "replace any face. Place the host(s) at the TOP-CENTER inside a gold ornate "
                "frame: if exactly one person, use a circular gold-rim portrait; if two or "
                "more people, use a ROUNDED RECTANGULAR frame that accommodates all faces "
                "side-by-side. Preserve features, age, skin tone, and expression EXACTLY. "
            )
    else:
        photo_directive = (
            "No host photo provided — use a tasteful decorative emblem (brass diya, marigold "
            "garland or mandala motif) where the portrait would have gone. "
        )

    return f"""Compose a PREMIUM Maharashtrian celebration invitation BACKGROUND for Purnabramha.

DESIGN BRIEF
- Aspect: {ASPECT_PROMPT.get(req.output_format, ASPECT_PROMPT['4:5'])}
- Brand palette: {BRAND_COLORS}
- Brand language: {BRAND_DESIGN}
- Overall feel: elegant, dignified, festive, luxurious — like a high-end wedding card.
  Use Maharashtrian motifs (paisley, peacock feather, marigold border, brass diya,
  mandala, banana-leaf veins) richly on edges/corners.

REQUIRED LAYOUT (top → bottom)
1. DO NOT draw any logo. The brand logo is rendered crisply on top of your
   image by our server — leave the TOP-RIGHT corner visually CLEAN (cream/gold
   soft texture, no text, no decoration) so our real logo can be pasted there.
2. {photo_directive}
3. Decorative ornate band suggesting an occasion of "{occ}" (paisley line / dotted gold).
4. Bottom 55% of the canvas — leave VISUALLY CALM with rich decorative texture
   (subtle marigold border, brass corner ornaments) but **NO TEXT** — clean
   negative space for the host name, date, time and venue to be overlaid afterwards.

CRITICAL TEXT-FREE / LOGO-FREE ZONE
- DO NOT render the host name, date, time, venue, address, menu, custom message
  or any other text content (Devanagari or English) anywhere in the image.
- DO NOT render the word "Purnabramha", "पूर्णब्रम्ह", "Manaswini Foods", or any
  variant. DO NOT draw a logo, mandala-with-text, or wordmark — the real logo
  is composited afterwards.
- All real event details + the brand logo will be rendered crisply by us on top.

PEOPLE PRESERVATION — CRITICAL
- Whatever number of people appear in the host reference photo, EVERY ONE of them
  MUST appear in the final invitation. Never crop, never remove, never substitute.
- If you cannot fit everyone gracefully in a circular frame, switch to a wider
  oval or rectangular ornate frame — never sacrifice a face.

STRICT RULES
- Host face(s) MUST be reproduced exactly from the reference images.
  No artistic reinterpretation.
- Avoid stock-photo people. Avoid clipart. Avoid emoji.
- Output must look print-ready — refined kerning, balanced negative space.
"""


@router.post("/invitation/generate")
async def generate_invitation(req: InvitationRequest):
    """Generate a customer celebration invitation poster. Uses Nano Banana
    with the Purnabramha logo + optional host photo as reference images."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

    session = await check_access(req.token)
    if not _is_center_manager_or_above(session):
        raise HTTPException(403, "Not permitted to create invitations")
    if not req.host_name.strip():
        raise HTTPException(400, "Host name is required")
    if not req.event_date or not req.event_time:
        raise HTTPException(400, "Event date and time are required")

    # Resolve center name + address from centers collection (unless caller overrides)
    center_doc = await db.centers.find_one({"code": (req.center or "").upper()}, {"_id": 0}) or {}
    center_name = center_doc.get("name") or req.center
    address_line = req.center_address or center_doc.get("address") or center_doc.get("city") or ""

    # Sanity check the logo exists (used by the Pillow overlay later)
    if not os.path.exists(LOGO_PATH):
        raise HTTPException(503, "Brand logo asset missing on server")

    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(503, "EMERGENT_LLM_KEY not configured")

    prompt = _build_invitation_prompt(req, center_name, address_line)

    chat = LlmChat(
        api_key=api_key,
        session_id=f"invite-{uuid.uuid4().hex[:8]}",
        system_message=(
            "You compose premium Maharashtrian celebration invitations for Purnabramha. "
            "The brand logo and host face (if provided) MUST be reproduced exactly from the "
            "reference images — never redraw or restyle them."
        ),
    ).with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])

    # Only the host photo (if any) is passed. Logo is rendered server-side by
    # Pillow on top of the AI output — we no longer ask Nano Banana to draw
    # a logo (it was producing duplicates).
    files: List = []
    if req.photo_base64:
        files.append(ImageContent(_strip_data_url(req.photo_base64)))

    try:
        if files:
            _text, images = await chat.send_message_multimodal_response(
                UserMessage(text=prompt, file_contents=files)
            )
        else:
            _text, images = await chat.send_message_multimodal_response(
                UserMessage(text=prompt)
            )
    except Exception as e:
        logger.error(f"Nano Banana invitation failed: {e}", exc_info=True)
        raise HTTPException(502, f"AI image generation failed: {e}")

    if not images:
        raise HTTPException(502, "AI returned no image — please retry")

    img = images[0]
    raw_bytes = base64.b64decode(img["data"])

    # ── Crisp invitation overlay (Pillow + Noto Sans Devanagari) ─────────
    # The AI image is purely a decorative background — we render every text
    # field crisply on top so Devanagari + names + dates are pixel-perfect.
    try:
        from utils.text_overlay import apply_invitation_overlay, OCCASION_MARATHI
        occ_label = req.occasion if req.occasion != "Other" else (req.occasion_other or "Celebration")
        occ_marathi = OCCASION_MARATHI.get(occ_label, "सोहळा")
        image_bytes = apply_invitation_overlay(
            raw_bytes,
            occasion=occ_label,
            occasion_marathi=occ_marathi,
            host_name=req.host_name,
            event_date=req.event_date,
            event_time=req.event_time,
            venue_name=center_name,
            venue_address=address_line,
            menu_highlights=req.menu_highlights or "",
            custom_message=req.custom_message or "",
            logo_path=LOGO_PATH if os.path.exists(LOGO_PATH) else None,
            brand=BRAND_NAME,
        )
    except Exception as e:
        logger.warning(f"invitation overlay failed, using raw AI image: {e}")
        image_bytes = raw_bytes

    img["data"] = base64.b64encode(image_bytes).decode("ascii")

    ad_id = str(uuid.uuid4())
    center_safe = (req.center or "UNKNOWN").replace("/", "_")
    sub = os.path.join(ASSET_DIR, center_safe, "invitations")
    os.makedirs(sub, exist_ok=True)
    path = os.path.join(sub, f"{ad_id}.png")
    with open(path, "wb") as f:
        f.write(image_bytes)

    record = {
        "ad_id": ad_id,
        "kind": "invitation",
        "center": req.center,
        "center_name": center_name,
        "host_name": req.host_name,
        "occasion": req.occasion if req.occasion != "Other" else (req.occasion_other or "Celebration"),
        "event_date": req.event_date,
        "event_time": req.event_time,
        "center_address": address_line,
        "menu_highlights": req.menu_highlights or "",
        "custom_message": req.custom_message or "",
        "language": req.language,
        "output_format": req.output_format,
        "has_photo": bool(req.photo_base64),
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
        "size_kb": round(len(image_bytes) / 1024.0, 1),
    }


# --- history / asset / tracking ------------------------------------------

class HistoryRequest(BaseModel):
    token: str
    center: Optional[str] = None
    limit: int = 50
    kind: Optional[str] = None     # 'invitation' to filter only invitations; default = all


@router.post("/history")
async def list_history(req: HistoryRequest):
    session = await check_access(req.token)
    if not _is_center_manager_or_above(session):
        raise HTTPException(403, "Not permitted")

    q: dict = {}
    if req.center:
        q["center"] = req.center
    # Non-admin center managers can only see their own center's creations
    if not _is_admin(session):
        own = session.get("center")
        if own:
            q["center"] = own
    if req.kind == "invitation":
        q["kind"] = "invitation"
    elif req.kind == "ad":
        # Marketing ads = anything that isn't an invitation (legacy rows have no kind field)
        q["kind"] = {"$ne": "invitation"}

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
