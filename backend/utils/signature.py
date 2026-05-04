"""Signature block utility for accounts reports.

Returns a reportlab Table that renders the company stamp + signature image
alongside the signatory's name / title / entity. Used at the end of every
ledger PDF (CA bundle, franchise-owner copy, individual ledgers).

Australian centers (PB-PERTH, etc.) are signed under Purnabramha LLC Pty Ltd;
all other centers are signed under Manaswini Foods Pvt Ltd.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle

_SIG_PATH = Path(__file__).resolve().parent.parent / "assets" / "signature_kaka.png"


def _entity_for_country(country: Optional[str]) -> str:
    if country and str(country).strip().lower() != "india":
        return "Purnabramha LLC Pty Ltd"
    return "Manaswini Foods Pvt Ltd"


def signature_block(country: Optional[str] = "India",
                    label: str = "Authorised Signatory",
                    width_inch: float = 2.0):
    """Return a list of flowables to append at the bottom of any report PDF.

    Layout (single row, two columns):
      [ small caption "For <Entity>"     ]   [ signature image ]
      [ "Shashikant Pande"               ]
      [ "CFO (Head of Accounts)"         ]
      [ "Purnabramha Accounts"           ]
      [ "<Entity>"                       ]
    """
    entity = _entity_for_country(country)
    caption = ParagraphStyle(
        "SigCaption", fontName="Helvetica", fontSize=8, leading=11,
        textColor=colors.HexColor("#475569"),
    )
    name = ParagraphStyle(
        "SigName", fontName="Helvetica-Bold", fontSize=10, leading=13,
        textColor=colors.HexColor("#1e293b"),
    )
    role = ParagraphStyle(
        "SigRole", fontName="Helvetica", fontSize=9, leading=12,
        textColor=colors.HexColor("#334155"),
    )

    text_cell = [
        Paragraph(f"For <b>{entity}</b>", caption),
        Spacer(1, 26),
        Paragraph("Shashikant Pande", name),
        Paragraph("CFO (Head of Accounts)", role),
        Paragraph("Purnabramha Accounts", role),
        Paragraph(entity, role),
        Paragraph(f"<i>{label}</i>", caption),
    ]

    if _SIG_PATH.exists():
        try:
            img = Image(str(_SIG_PATH), width=width_inch * inch, height=width_inch * 0.78 * inch)
            img.hAlign = "RIGHT"
            sig_cell = img
        except Exception:
            sig_cell = Paragraph("[signature]", caption)
    else:
        sig_cell = Paragraph("[signature]", caption)

    tbl = Table(
        [[text_cell, sig_cell]],
        colWidths=[3.2 * inch, 2.6 * inch],
    )
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [Spacer(1, 18), tbl, Spacer(1, 6)]
