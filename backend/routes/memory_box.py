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
        prompt = (
            "You are composing a heartfelt 4-section memory book copy for a Purnabramha "
            "(Maharashtrian restaurant) guest. Tone: warm, sincere, dignified, slightly "
            "poetic — never salesy, never generic. 2-3 short paragraphs max per section.\n\n"
            "Guest details:\n"
            + "\n".join(f"  {k}: {v}" for k, v in answers.items() if v) + "\n\n"
            "Return STRICT JSON with these four keys (no markdown, no commentary):\n"
            '{\n'
            '  "story":      "Warm 2-paragraph story of the event, woven from the guest answers above. Reference the family/organiser/special moment naturally.",\n'
            '  "gratitude":  "Occasion-specific thank-you message from Purnabramha to the guest. 1 short paragraph.",\n'
            '  "blessing":   "A traditional Maharashtrian blessing fitting the occasion. 2-3 lines.",\n'
            '  "future_invitation": "A 1-line warm invitation back — NOT discount-based — e.g. complimentary taak / sweet / priority booking / chef special."\n'
            "}"
        )
        chat = (LlmChat(api_key=api_key, session_id=f"mbox-{uuid.uuid4().hex[:8]}",
                       system_message="You write warm, dignified memory book copy for Indian family celebrations.")
                .with_model("openai", "gpt-5.2"))
        resp = await chat.send_message(UserMessage(text=prompt))
        import json, re
        cleaned = re.sub(r"^```json\s*|\s*```$", "", resp.strip(), flags=re.MULTILINE)
        data = json.loads(cleaned)
        # Sanity defaults
        for k in ("story", "gratitude", "blessing", "future_invitation"):
            data.setdefault(k, "")
        return data
    except Exception as e:
        logger.warning(f"Memory box GPT generation fell back: {e}")
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
            "blessing": "May the year ahead bring you health, joy, and meaningful moments shared at the family table.",
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
        KeepTogether,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # ── Register Devanagari fonts so Marathi blessing renders correctly ──
    DEV_REG_PATH = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
    DEV_BOLD_PATH = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
    DEV_FONT = "Times-Italic"          # safe fallback
    DEV_BOLD_FONT = "Times-Bold"
    try:
        if os.path.exists(DEV_REG_PATH):
            pdfmetrics.registerFont(TTFont("NotoDev", DEV_REG_PATH))
            DEV_FONT = "NotoDev"
        if os.path.exists(DEV_BOLD_PATH):
            pdfmetrics.registerFont(TTFont("NotoDevBold", DEV_BOLD_PATH))
            DEV_BOLD_FONT = "NotoDevBold"
    except Exception as _e:
        logger.warning(f"Devanagari font registration failed: {_e}")

    occ = req.occasion if req.occasion != "Other" else (req.occasion_other or "Celebration")
    # Purnabramha 2026 brand palette
    GOLD = colors.HexColor("#BF8C32")             # rich antique gold
    GOLD_BRIGHT = colors.HexColor("#DCAE50")
    MAROON = colors.HexColor("#660E0E")           # deep maroon (festive)
    CREAM = colors.HexColor("#FAF0DC")            # warm cream
    CHOCOLATE = colors.HexColor("#2B1810")        # dark chocolate (primary)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                            title=f"Memory Box — {req.guest_name}")
    ss = getSampleStyleSheet()
    # All heading colours upgraded to ANTIQUE GOLD and font sizes increased
    H = ParagraphStyle("H", parent=ss["Heading1"], textColor=GOLD_BRIGHT,
                       alignment=TA_CENTER, fontSize=40, spaceAfter=18,
                       fontName="Times-Bold", leading=48)
    H2 = ParagraphStyle("H2", parent=ss["Heading2"], textColor=GOLD_BRIGHT,
                        alignment=TA_CENTER, fontSize=32, spaceAfter=14,
                        fontName="Times-Bold", leading=40)
    sub = ParagraphStyle("sub", parent=ss["Normal"], textColor=CREAM,
                         alignment=TA_CENTER, fontSize=20, fontName="Times-Italic",
                         spaceAfter=12, leading=26)
    body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=17, leading=26,
                          fontName="Times-Roman", textColor=CREAM,
                          spaceAfter=12, alignment=TA_LEFT)
    bodyDark = ParagraphStyle("bodyDark", parent=body, textColor=colors.HexColor("#3a2218"))  # noqa: F841
    centerBody = ParagraphStyle("cb", parent=body, alignment=TA_CENTER, fontSize=18, leading=28)
    small = ParagraphStyle("sm", parent=ss["BodyText"], fontSize=13,
                           textColor=CREAM, alignment=TA_CENTER, leading=18)

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
    story.append(PageBreak())

    # ─── Page 2: Event Story ───
    story.append(Paragraph("Your Story With Us", H))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(llm.get("story", "").replace("\n", "<br/><br/>"), body))
    if req.host_message:
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph(f'<i>"{req.host_message}"</i> — {req.organised_by or req.guest_name}', centerBody))
    story.append(PageBreak())

    # ─── Page 3: Gallery ───
    if req.photos:
        story.append(Paragraph("Moments Captured", H))
        story.append(Spacer(1, 0.1 * inch))
        cells = []
        row = []
        for p in req.photos[:9]:                 # 3×3 grid max
            im = _img(p, w=2.0, h=2.0)
            if im:
                row.append(im)
            if len(row) == 3:
                cells.append(row); row = []
        if row:
            while len(row) < 3:
                row.append("")
            cells.append(row)
        if cells:
            t = Table(cells, colWidths=[2.2 * inch] * 3, rowHeights=[2.2 * inch] * len(cells))
            t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                   ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 4),
                                   ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                                   ("TOPPADDING", (0, 0), (-1, -1), 4),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
            story.append(t)
        story.append(PageBreak())

    # ─── Page 4: Team ───
    if req.team or req.team_photo:
        story.append(Paragraph("Meet The Team", H))
        story.append(Paragraph("The people behind your celebration.", sub))
        story.append(Spacer(1, 0.15 * inch))
        if req.team_photo:
            im = _img(req.team_photo, w=4.5, h=3.0)
            if im:
                story.append(im)
                story.append(Spacer(1, 0.15 * inch))
        if req.team:
            data = [["Name", "Role"]] + [[t.name, t.role] for t in req.team[:15]]
            tbl = Table(data, colWidths=[3.0 * inch, 3.0 * inch])
            tbl.setStyle(TableStyle([
                ("FONT", (0, 0), (-1, 0), "Times-Bold", 11),
                ("FONT", (0, 1), (-1, -1), "Times-Roman", 11),
                ("TEXTCOLOR", (0, 0), (-1, 0), MAROON),
                ("BACKGROUND", (0, 0), (-1, 0), CREAM),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, GOLD),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(tbl)
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
    story.append(Spacer(1, 0.5 * inch))
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


def _render_cover_png(req: MemoryBoxRequest, center_name: str, box_id: str) -> bytes:
    """Premium chocolate-and-gold PNG cover (WhatsApp preview / Memory Box hero)."""
    try:
        from PIL import Image as PImage, ImageDraw, ImageFont
        W, H = 1080, 1350
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
        # Paisley divider just under logo space
        midx = W // 2
        for dy in [510, 870]:
            for dx in range(-4, 5):
                r = 5 if dx == 0 else 3
                draw.ellipse([midx + dx * 18 - r, dy, midx + dx * 18 + r, dy + 2 * r],
                             fill=(220, 174, 80))

        # Logo
        if os.path.exists(LOGO_PATH):
            logo = PImage.open(LOGO_PATH).convert("RGBA")
            logo.thumbnail((420, 420))
            canvas.paste(logo, ((W - logo.width) // 2, 80), logo if logo.mode == "RGBA" else None)

        # Fonts — XL sizes + premium serif + Devanagari for Marathi
        try:
            f_big = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf", 108)
            f_host = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf", 92)
            f_med = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", 56)
            f_sm  = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf", 42)
            f_mr  = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf", 52)
        except Exception:
            f_big = f_host = f_med = f_sm = f_mr = ImageFont.load_default()

        def _center_text(y, text, font, fill):
            bb = draw.textbbox((0, 0), text, font=font)
            w = bb[2] - bb[0]
            # Soft drop shadow
            draw.text(((W - w) // 2 + 2, y + 2), text, font=font, fill=(0, 0, 0, 200))
            draw.text(((W - w) // 2, y), text, font=font, fill=fill)

        # English headline (large gold)
        _center_text(560, "Thank You", f_big, (220, 174, 80))
        _center_text(660, "for making us part of your celebration",
                     f_med, (250, 240, 220))
        # Marathi bilingual subtitle
        _center_text(740, "आमच्या सोबत आनंदाचे क्षण साजरे केल्याबद्दल धन्यवाद",
                     f_mr, (220, 174, 80))

        # Guest name — BIGGEST
        _center_text(910, req.guest_name[:34], f_host, (220, 174, 80))
        occ = req.occasion if req.occasion != "Other" else (req.occasion_other or "Celebration")
        _center_text(1020, occ, f_sm, (250, 240, 220))
        _center_text(1075, req.event_date, f_sm, (250, 240, 220))

        # Footer brand
        _center_text(1220, f"Purnabramha · {center_name}", f_sm, (220, 174, 80))
        _center_text(1268, "पुर्णब्रह्म परिवाराकडून प्रेमपूर्वक",
                     f_mr, (191, 140, 50))

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
    cover_png = _render_cover_png(req, center_name, box_id)

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
        "story_text": llm.get("story", ""),
        "gratitude_text": llm.get("gratitude", ""),
        "blessing_text": llm.get("blessing", ""),
        "future_invitation_text": llm.get("future_invitation", ""),
        "asset_pdf": pdf_path,
        "asset_png": png_path if cover_png else None,
        "size_bytes": len(pdf_bytes),
        "created_by": session.get("managerName") or session.get("mobile") or "Unknown",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "delivery": {"whatsapp": None, "email": None, "downloads": 0},
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
        q, {"_id": 0, "asset_pdf": 0, "asset_png": 0}
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
