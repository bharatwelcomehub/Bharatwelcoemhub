"""One-shot migration — recompute `daily_sales.gst_amount` using the canonical
inclusive-carve formula.

Why
---
For months we wrote `gst_amount = eligible × 0.05` (5% on top) instead of the
correct inclusive carve `eligible − eligible/(1+rate)`. The dashboards compute
GST on the fly via ``utils/gst.compute_gst_from_rows`` so they already show the
right number — but the *stored* `gst_amount` field on every historical row is
over-stated by a small amount (~5% of stored value). Anything that reads
`gst_amount` directly (a future report, an export, a downstream consumer) gets
the wrong number.

What this does
--------------
For every row in ``daily_sales``:
  • Resolve the country/center → rate via ``gst_rate_for``.
  • Compute the canonical eligible base via ``eligible_base_from_daily_row``.
  • Compute the canonical GST via ``carve_inclusive_gst(base, rate)``.
  • If it diverges from stored ``gst_amount`` by more than ₹0.01, update the
    row and stamp ``_gst_recomputed_at`` + ``_gst_amount_legacy`` for audit.

Safety
------
* DRY-RUN by default. Pass ``--apply`` to actually write.
* No rows are deleted. Nothing else is touched.
* Audit field ``_gst_amount_legacy`` lets you reverse every update if needed.

Usage
-----
::
    cd /app/backend && python scripts/recompute_gst_amount.py            # dry-run
    cd /app/backend && python scripts/recompute_gst_amount.py --apply    # commit
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Add backend root to path so we can import utils.gst
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.gst import (  # noqa: E402  (after sys.path insert)
    carve_inclusive_gst,
    eligible_base_from_daily_row,
    gst_rate_for,
)


async def main(apply_changes: bool = False) -> None:
    load_dotenv("/app/backend/.env")
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    centers = {c["code"]: c.get("country") for c in await db.centers.find({}, {"_id": 0, "code": 1, "country": 1}).to_list(2000)}

    cursor = db.daily_sales.find({}, {})  # full rows so we have all aggregator field variants
    total = 0
    diverged = 0
    fixed = 0
    drift_total_old = 0.0
    drift_total_new = 0.0
    sample_diverged: list = []

    async for row in cursor:
        total += 1
        center = row.get("center", "")
        country = centers.get(center)
        rate = gst_rate_for(country, center)
        canon = carve_inclusive_gst(eligible_base_from_daily_row(row), rate)
        stored = float(row.get("gst_amount", 0) or 0)
        if abs(canon - stored) > 0.01:
            diverged += 1
            drift_total_old += stored
            drift_total_new += canon
            if len(sample_diverged) < 5:
                sample_diverged.append({
                    "_id": str(row.get("_id")),
                    "center": center,
                    "date": row.get("date"),
                    "stored": round(stored, 2),
                    "canonical": round(canon, 2),
                    "delta": round(canon - stored, 2),
                })
            if apply_changes:
                await db.daily_sales.update_one(
                    {"_id": row["_id"]},
                    {"$set": {
                        "gst_amount": canon,
                        "_gst_amount_legacy": stored,
                        "_gst_recomputed_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
                fixed += 1

    print("=== daily_sales.gst_amount canonical recompute ===")
    print(f"  rows scanned          : {total:>10,}")
    print(f"  rows diverged from canon: {diverged:>10,}")
    print(f"  Σ stored (legacy)     : {drift_total_old:>15,.2f}")
    print(f"  Σ canonical (correct) : {drift_total_new:>15,.2f}")
    print(f"  net drift             : {drift_total_new - drift_total_old:>+15,.2f}")
    print()
    print("  Sample of first 5 diverged rows:")
    for s in sample_diverged:
        print(f"    {s}")
    print()
    if apply_changes:
        print(f"  ✓ Applied {fixed:,} updates. Audit fields _gst_amount_legacy + _gst_recomputed_at set on each.")
    else:
        print("  DRY-RUN — no writes. Re-run with --apply to commit.")


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    asyncio.run(main(apply))
