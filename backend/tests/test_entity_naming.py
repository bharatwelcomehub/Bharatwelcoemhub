"""Regression: legal entity name shown on payout/share labels must be
country-aware across PDF reports.

  • India     → "Manaswini Foods Pvt Ltd Share"
  • Australia → "Purnabramha LLC Pty Ltd Share"
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from utils.entity import entity_for_country, entity_share_label


def test_entity_for_country_india():
    assert entity_for_country("India") == "Manaswini Foods Pvt Ltd"
    assert entity_for_country("india") == "Manaswini Foods Pvt Ltd"
    assert entity_for_country(None) == "Manaswini Foods Pvt Ltd"
    assert entity_for_country("") == "Manaswini Foods Pvt Ltd"


def test_entity_for_country_australia():
    assert entity_for_country("Australia") == "Purnabramha LLC Pty Ltd"
    assert entity_for_country("australia") == "Purnabramha LLC Pty Ltd"


def test_entity_share_label():
    assert entity_share_label("India") == "Manaswini Foods Pvt Ltd Share"
    assert entity_share_label("Australia") == "Purnabramha LLC Pty Ltd Share"


@pytest.mark.parametrize("country,expected_label", [
    ("Australia", "Purnabramha LLC Pty Ltd Share"),
    ("India", "Manaswini Foods Pvt Ltd Share"),
])
def test_entity_share_label_drives_payout_pdf_string(country, expected_label):
    """Smoke-test the helper that the PDF generator uses to render
    the franchisor-share row in section 8 of the PIB PDF."""
    assert entity_share_label(country) == expected_label


def test_pdf_generator_no_longer_uses_legacy_label():
    """Hard regression — the legacy 'Purnabramha LLC Share' constant must
    not exist anywhere in pdf_generator.py (any case). All payout labels
    must be derived via entity_share_label(country)."""
    src = (Path(__file__).resolve().parent.parent / "utils" / "pdf_generator.py").read_text()
    lower = src.lower()
    assert "purnabramha llc share" not in lower, (
        "pdf_generator.py still hardcodes 'Purnabramha LLC Share' (any case); "
        "use entity_share_label(country) instead."
    )
    assert "purnabramha total (with gst)" not in lower, (
        "pdf_generator.py still hardcodes 'PURNABRAMHA TOTAL (WITH GST)'; "
        "use entity_for_country(country) instead."
    )
    assert "entity_share_label" in src, (
        "pdf_generator.py should import and use entity_share_label."
    )


def test_frontend_center_accounts_no_legacy_label():
    """Hard regression — the CenterAccounts dashboard must not hardcode
    'Purnabramha LLC Share' anymore. All five places should derive the
    legal entity name via the entityName(country) helper."""
    src = (
        Path(__file__).resolve().parent.parent.parent
        / "frontend" / "src" / "pages" / "CenterAccounts.jsx"
    ).read_text()
    # Strip the helper definition and its docstring comments before scanning
    lines = [l for l in src.splitlines()
             if "Purnabramha LLC Pty Ltd" not in l
             and "// " not in l]
    rendered = "\n".join(lines)
    assert "Purnabramha LLC Share" not in rendered, (
        "CenterAccounts.jsx still hardcodes 'Purnabramha LLC Share' "
        "outside the entityName helper."
    )
    assert "entityName(accountSummary.country)" in src, (
        "CenterAccounts.jsx should call entityName(accountSummary.country)."
    )
