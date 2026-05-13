"""Iteration 84 — Commission per-platform vs canonical-total parity.

Locks the contract that `get_total_commissions(...)`:
  - returns `by_platform` whose deduction-sum equals `total` to the paise.
  - never double-counts (commission_amount + new-schema fields).
  - excludes TDS from the canonical total (TDS is booked separately as expense).
"""

import asyncio
import os
import sys

import pytest
from motor.motor_asyncio import AsyncIOMotorClient

# Make `utils.commissions` importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.commissions import get_total_commissions, _row_total  # noqa: E402


_LOOP = asyncio.new_event_loop()


def _run(coro):
    """Run an async coro on a shared loop to avoid motor connection teardown issues."""
    return _LOOP.run_until_complete(coro)


def _get_db():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"], io_loop=_LOOP)
    return client[os.environ["DB_NAME"]]


def test_row_total_does_not_double_count_new_and_legacy_fields():
    """When new-schema fields are populated, _row_total uses ONLY them (no fallback
    to commission_amount), so totals never inflate by adding both schemas together.
    """
    row = {
        "commission_amount": 100.0,      # legacy field
        "gst_tax_deductions": 18.0,      # new schema
        "other_deductions": 50.0,        # new schema
        "tds": 5.0,                      # excluded
    }
    # Expected: 18 + 50 = 68 (NOT 100 + 18 + 50 + 5 = 173 like before fix)
    assert _row_total(row) == pytest.approx(68.0, abs=0.01)


def test_row_total_falls_back_to_commission_amount_only_when_new_fields_empty():
    row = {"commission_amount": 75.0, "gst_tax_deductions": 0, "other_deductions": 0, "tds": 100.0}
    assert _row_total(row) == pytest.approx(75.0, abs=0.01)


def test_row_total_excludes_tds_entirely():
    """TDS PAID is booked as a separate operating expense; including it in
    commission would double-charge the franchise center."""
    row = {"gst_tax_deductions": 10.0, "other_deductions": 20.0, "tds": 9999.0}
    assert _row_total(row) == pytest.approx(30.0, abs=0.01)


def test_canonical_total_equals_per_platform_sum_across_test_centers():
    cases = [
        ("PB-HSR", "2026-01"),
        ("PB-HSR", "2026-02"),
        ("PB-HSR", "2026-03"),
        ("PB-SN",  "2026-02"),
        ("PB-PERTH", "2026-01"),
        ("PB-PERTH", "2026-02"),
        ("PB-PERTH", "2026-03"),
    ]
    db = _get_db()
    for center, month in cases:
        result = _run(get_total_commissions(db, center, month))
        per_platform_sum = round(
            sum(p.get("deduction", 0) for p in (result.get("by_platform") or {}).values()),
            2,
        )
        total = round(result.get("total", 0), 2)
        assert abs(per_platform_sum - total) < 0.05, (
            f"{center} {month}: per-platform sum {per_platform_sum} != canonical "
            f"total {total} (source={result.get('source')})"
        )


def test_by_platform_always_present():
    db = _get_db()
    result = _run(get_total_commissions(db, "PB-NONEXISTENT", "2099-12"))
    assert "by_platform" in result
    assert isinstance(result["by_platform"], dict)
    s = sum(p.get("deduction", 0) for p in result["by_platform"].values())
    assert s == 0
