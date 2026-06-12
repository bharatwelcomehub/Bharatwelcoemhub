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
