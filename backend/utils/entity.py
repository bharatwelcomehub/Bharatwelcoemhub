"""Legal entity name resolver based on a center's country.

Single source of truth for the legal entity name shown on financial reports,
PDFs, dashboards and agreements.

  • India     → Manaswini Foods Pvt Ltd
  • Australia → Purnabramha LLC Pty Ltd
  • (other)   → Purnabramha International LLC

The "Share" suffix variant is exposed via :func:`entity_share_label` so that
callers can render labels like "Manaswini Foods Pvt Ltd Share (20%)".
"""
from __future__ import annotations
from typing import Optional


def entity_for_country(country: Optional[str]) -> str:
    """Return the formal legal entity name for the given country."""
    c = (country or "India").strip().lower()
    if c == "india":
        return "Manaswini Foods Pvt Ltd"
    if c == "australia":
        return "Purnabramha LLC Pty Ltd"
    return "Purnabramha International LLC"


def entity_share_label(country: Optional[str], suffix: str = "Share") -> str:
    """Return "<Entity> Share" (or any custom suffix) for the given country."""
    return f"{entity_for_country(country)} {suffix}".strip()


def model_share_phrase(model: Optional[str]) -> str:
    """Return "Profit Share" or "Revenue Share" based on the active payout model.

    Used everywhere we render a label tied to the share split (UI cards, PDF
    section headers, payout rows). The Single Financial Engine emits the
    canonical model string ("profit_share" / "revenue_share") on every summary
    payload — this helper translates it into the human-readable phrase so the
    rest of the app NEVER hard-codes the wrong word.
    """
    return "Profit Share" if (model or "").strip().lower() == "profit_share" else "Revenue Share"


def entity_model_share_label(country: Optional[str], model: Optional[str]) -> str:
    """Return "<Entity> Revenue Share" or "<Entity> Profit Share" by model."""
    return f"{entity_for_country(country)} {model_share_phrase(model)}".strip()


def owner_model_share_label(model: Optional[str]) -> str:
    """Return "Franchise Owner Revenue Share" / "... Profit Share" by model."""
    return f"Franchise Owner {model_share_phrase(model)}"
