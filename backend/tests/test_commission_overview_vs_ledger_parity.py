"""Regression test for the May-2026 user-reported bug:

  "Commission OVERVIEW madhye Actual peksha JAST yet aahe LEDGER madhye correct
   aahe Zomato upload kelyavar HSR & S NAGAR"

Root cause: WC-table / Status-card aggregations in routes/center_accounts.py
summed `commission_amount + other_deductions + gst_tax_deductions + tds`. For
the new Zomato parser this double-counted (commission_amount is 0 when new
fields are present) AND included TDS — which utils/commissions._row_total
excludes because TDS PAID is booked as a separate operating expense.

Result: every dashboard reading the new aggregation showed a higher commission
than the Ledger / MIS Dashboard which use the canonical helper.

This test compares the two aggregation pipelines on synthetic Zomato rows and
asserts the new pipeline matches `_row_total` to the paisa.
"""
import asyncio
import os
import uuid

import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from utils.commissions import _row_total


def _build_pipeline(center):
    """The fixed aggregation pipeline (must mirror routes/center_accounts.py)."""
    return [
        {"$match": {"center": center}},
        {"$addFields": {
            "_new_sum": {"$add": [
                {"$ifNull": ["$other_deductions", 0]},
                {"$ifNull": ["$gst_tax_deductions", 0]},
            ]},
        }},
        {"$addFields": {
            "_row_total": {"$cond": [
                {"$gt": ["$_new_sum", 0]},
                "$_new_sum",
                {"$ifNull": ["$commission_amount", 0]},
            ]},
        }},
        {"$group": {"_id": "$month", "total_commission": {"$sum": "$_row_total"}}},
        {"$sort": {"_id": 1}},
    ]


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_overview_aggregation_matches_canonical_row_total():
    """Insert synthetic Zomato + Swiggy rows and confirm the WC-table style
    aggregation produces the exact same monthly total as the Python
    `_row_total` helper (which the Ledger uses)."""

    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    center = f"TEST-COMM-{uuid.uuid4().hex[:6].upper()}"

    docs = [
        # Zomato: new parser fields, no commission_amount, with TDS
        {
            "commission_id": str(uuid.uuid4()),
            "center": center, "month": "2025-05", "platform": "zomato",
            "gross_amount": 100000.0,
            "gst_tax_deductions": 3000.0,
            "other_deductions": 18000.0,
            "tds": 1000.0,  # MUST be excluded
            "commission_amount": None,
            "net_payout": 78000.0,
        },
        # Swiggy: same shape but smaller numbers
        {
            "commission_id": str(uuid.uuid4()),
            "center": center, "month": "2025-05", "platform": "swiggy",
            "gross_amount": 50000.0,
            "gst_tax_deductions": 1500.0,
            "other_deductions": 9000.0,
            "tds": 500.0,
            "commission_amount": None,
            "net_payout": 39500.0,
        },
        # Legacy row: only commission_amount populated (fallback path)
        {
            "commission_id": str(uuid.uuid4()),
            "center": center, "month": "2025-04", "platform": "zomato",
            "gross_amount": 80000.0,
            "gst_tax_deductions": 0,
            "other_deductions": 0,
            "tds": 0,
            "commission_amount": 16000.0,
            "net_payout": 64000.0,
        },
    ]

    async def _go():
        await db.monthly_commissions.insert_many(docs)
        try:
            agg = await db.monthly_commissions.aggregate(_build_pipeline(center)).to_list(20)
            agg_map = {r["_id"]: r["total_commission"] for r in agg}

            # Canonical Python computation
            rows = await db.monthly_commissions.find({"center": center}, {"_id": 0}).to_list(20)
            py_map = {}
            for r in rows:
                py_map[r["month"]] = py_map.get(r["month"], 0) + _row_total(r)

            # Expectations
            assert agg_map["2025-05"] == pytest.approx(3000 + 18000 + 1500 + 9000)  # 31500 (TDS excluded)
            assert agg_map["2025-04"] == pytest.approx(16000.0)  # legacy fallback
            # Aggregation MUST equal Python canonical
            for m, v in py_map.items():
                assert agg_map[m] == pytest.approx(v), f"month {m}: agg={agg_map[m]} canonical={v}"
        finally:
            await db.monthly_commissions.delete_many({"center": center})
            client.close()

    _run(_go())


def test_tds_is_excluded_from_overview():
    """Explicit invariant: a row with only TDS contributes 0 to the
    overview commission (matching the Ledger)."""
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    center = f"TEST-TDS-{uuid.uuid4().hex[:6].upper()}"

    docs = [{
        "commission_id": str(uuid.uuid4()),
        "center": center, "month": "2025-06", "platform": "zomato",
        "gst_tax_deductions": 0,
        "other_deductions": 0,
        "tds": 5000.0,
        "commission_amount": 0,
    }]

    async def _go():
        await db.monthly_commissions.insert_many(docs)
        try:
            agg = await db.monthly_commissions.aggregate(_build_pipeline(center)).to_list(5)
            agg_map = {r["_id"]: r["total_commission"] for r in agg}
            assert agg_map["2025-06"] == 0.0, f"TDS-only row leaked into overview: {agg_map}"
        finally:
            await db.monthly_commissions.delete_many({"center": center})
            client.close()

    _run(_go())
