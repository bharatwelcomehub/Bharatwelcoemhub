"""Regression tests for the Phase-3 bundle generator.

Confirms each of the three bundles produces a valid non-empty ZIP, that
the included PDF contains the engine-driven figures, and that the manifest
records every key engine field for audit purposes.
"""
from __future__ import annotations
import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from utils.financial_engine import compute_franchise_payout
from utils.bundle_generator import (
    build_ca_bundle_pdf,
    build_franchise_owner_bundle_pdf,
    build_franchisor_bundle_pdf,
    build_bundle_zip,
)


@pytest.fixture
def sample_ctx():
    engine = compute_franchise_payout(
        sales=1_088_002,
        commissions=26_656.96,
        gst_on_sales=48_197.67,
        expenses=900_000,
        payout_model="revenue_share",
        franchise_owner_pct=15,
        mg_applicable=False,
        country="India",
    )
    return {
        "center": "PB-DV",
        "period": "2026-05",
        "period_label": "May 2026",
        "country": "India",
        "currency": "Rs.",
        "financial_summary": {
            "total_sales": 1_088_002,
            "sales_gst": 48_197.67,
            "total_commissions": 26_656.96,
            "total_expenses": 900_000,
        },
        "engine": engine,
        "payout": {
            "amount": engine["payable"],
            "type": engine["payable_type"],
            "reason": engine["reason"],
            "paid_amount": 0,
            "pending_amount": engine["payable"],
            "release_status": "eligible",
        },
        "working_capital": {"opening_wc": 100000, "current_wc": 85000, "recovery_amount": 0, "protection_mode": False},
        "gst": {"paid": 0, "outstanding": 48_197.67},
    }


def test_ca_bundle_pdf_renders(sample_ctx):
    pdf = build_ca_bundle_pdf(sample_ctx)
    assert pdf and len(pdf) > 1000
    assert pdf[:4] == b"%PDF"


def test_franchise_owner_bundle_pdf_renders(sample_ctx):
    pdf = build_franchise_owner_bundle_pdf(sample_ctx)
    assert pdf[:4] == b"%PDF" and len(pdf) > 1000


def test_franchisor_bundle_pdf_renders(sample_ctx):
    pdf = build_franchisor_bundle_pdf(sample_ctx)
    assert pdf[:4] == b"%PDF" and len(pdf) > 1000


def test_zip_contains_pdf_and_manifest(sample_ctx):
    z = build_bundle_zip("ca", sample_ctx)
    with zipfile.ZipFile(io.BytesIO(z)) as zf:
        names = zf.namelist()
        assert any(n.endswith(".pdf") for n in names)
        assert any(n.endswith("_manifest.txt") for n in names)
        manifest = zf.read([n for n in names if n.endswith("_manifest.txt")][0]).decode()
        # Audit-trail must include selected base + owner share + entity label.
        assert "Selected Base:" in manifest
        assert "Owner Share:" in manifest
        assert "Company Entity:" in manifest
        # And reference the single source of truth file.
        assert "financial_engine.py" in manifest


def test_zip_each_kind(sample_ctx):
    for kind in ("ca", "owner", "franchisor"):
        z = build_bundle_zip(kind, sample_ctx)
        assert z and len(z) > 500


def test_zip_rejects_unknown_kind(sample_ctx):
    with pytest.raises(ValueError):
        build_bundle_zip("garbage", sample_ctx)


def test_pdf_text_contains_engine_figures(sample_ctx):
    """Pull text out of the CA bundle PDF and confirm the engine's
    selected_base + owner_share appear verbatim (formatted)."""
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            pytest.skip("pypdf / PyPDF2 not installed")

    pdf = build_ca_bundle_pdf(sample_ctx)
    reader = PdfReader(io.BytesIO(pdf))
    text = "".join((p.extract_text() or "") for p in reader.pages)

    # Engine-computed figures must appear in the PDF.
    eng = sample_ctx["engine"]
    assert f"{eng['revenue_share_base']:,.2f}" in text or f"{eng['revenue_share_base']:,.2f}".replace(",", "") in text
    assert f"{eng['owner_share']:,.2f}" in text or f"{eng['owner_share']:,.2f}".replace(",", "") in text
    # Entity label correctness — India should reference Manaswini.
    assert "Manaswini" in text
