"""Signature block utility for accounts reports.

Renders a large, authoritative signatory card at the bottom of every Accounts
PDF report. The signature image sits between the entity header and the
signatory's name/title — giving a stamped, official feel.

Australian centers (PB-PERTH, etc.) are signed under Purnabramha LLC Pty Ltd;
all other centers are signed under Manaswini Foods Pvt Ltd.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle, HRFlowable

_SIG_PATH = Path(__file__).resolve().parent.parent / "assets" / "signature_kaka_cropped.png"


def _entity_for_country(country: Optional[str]) -> str:
    if country and str(country).strip().lower() != "india":
        return "Purnabramha LLC Pty Ltd"
    return "Manaswini Foods Pvt Ltd"


def signature_block(country: Optional[str] = "India",
                    label: str = "Authorised Signatory"):
    """Return a list of flowables to append at the bottom of any report PDF.

    Layout (single centered card, ~5.6 inches wide):

      ┌──────────────────────────────────────────────┐
      │             For <Entity>                     │
      │                                              │
      │           [  SIGNATURE IMAGE  ]              │   <-- centered, big
      │       ─────────────────────────────          │
      │           Shashikant Pande                   │   <-- bold, larger
      │           CFO (Head of Accounts)             │
      │           Purnabramha Accounts               │
      │           <Entity>                           │
      │           Authorised Signatory               │
      └──────────────────────────────────────────────┘
    """
    entity = _entity_for_country(country)

    entity_style = ParagraphStyle(
        "SigEntity", fontName="Helvetica-Bold", fontSize=11, leading=14,
        alignment=1,  # center
        textColor=colors.HexColor("#0F172A"),
    )
    name_style = ParagraphStyle(
        "SigName", fontName="Helvetica-Bold", fontSize=13, leading=16,
        alignment=1, textColor=colors.HexColor("#0B1E3F"),
    )
    role_style = ParagraphStyle(
        "SigRole", fontName="Helvetica", fontSize=10, leading=13,
        alignment=1, textColor=colors.HexColor("#1e293b"),
    )
    sub_style = ParagraphStyle(
        "SigSub", fontName="Helvetica-Oblique", fontSize=9, leading=12,
        alignment=1, textColor=colors.HexColor("#475569"),
    )

    # Signature image — large and centered. Cropped asset is 453×359 (1.26 ratio).
    if _SIG_PATH.exists():
        try:
            sig_w = 3.0 * inch
            sig_h = sig_w * (359.0 / 453.0)  # preserve aspect → ~2.38 inches tall
            sig_img = Image(str(_SIG_PATH), width=sig_w, height=sig_h)
            sig_img.hAlign = "CENTER"
        except Exception:
            sig_img = Paragraph("[signature unavailable]", sub_style)
    else:
        sig_img = Paragraph("[signature unavailable]", sub_style)

    inner = [
        Spacer(1, 6),
        Paragraph(f"For <b>{entity}</b>", entity_style),
        Spacer(1, 4),
        sig_img,
        HRFlowable(width="60%", thickness=0.6, color=colors.HexColor("#94a3b8"),
                   spaceBefore=0, spaceAfter=4, hAlign="CENTER"),
        Paragraph("Shashikant Pande", name_style),
        Paragraph("CFO (Head of Accounts)", role_style),
        Paragraph("Purnabramha Accounts", role_style),
        Paragraph(entity, role_style),
        Spacer(1, 2),
        Paragraph(f"<i>{label}</i>", sub_style),
        Spacer(1, 4),
    ]

    # Wrap inner stack inside a bordered table cell for a "stamped card" look
    card = Table([[inner]], colWidths=[5.6 * inch])
    card.hAlign = "CENTER"
    card.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafbfc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    return [Spacer(1, 22), card, Spacer(1, 8)]
