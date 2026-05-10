#!/usr/bin/env python3
"""Migration: fix wrongly-tagged franchise documents.

Earlier the Franchise Management upload tagged the uploader's center (often
PB-MGT) on franchise-level docs instead of the franchise's home/operating
center. That made docs invisible when the Document Management page was
filtered by the franchise's actual center.

This script walks `db.documents` for level=franchise rows where the `center`
doesn't match the franchise's home_center, and updates them in-place.

Run:
  python /app/backend/scripts/fix_franchise_doc_centers.py            # dry-run
  python /app/backend/scripts/fix_franchise_doc_centers.py --apply    # commit

Output: list of (document_id, franchise_code, old_center → new_center).
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient


async def main(apply: bool):
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    docs = await db.documents.find(
        {"level": "franchise", "is_deleted": {"$ne": True}}, {"_id": 0}
    ).to_list(20000)

    fr_codes = list({d.get("franchise_code") for d in docs if d.get("franchise_code")})
    # Centers→franchise link: one franchise can have multiple centers; pick the
    # first non-MGT center as the home center.
    centers_for_fc = await db.centers.find(
        {"franchise_code": {"$in": fr_codes}},
        {"_id": 0, "code": 1, "franchise_code": 1},
    ).to_list(5000)
    home_map: dict = {}
    for c in centers_for_fc:
        fc = (c.get("franchise_code") or "").upper().strip()
        cc = (c.get("code") or "").upper().strip()
        if not fc or not cc:
            continue
        existing = home_map.get(fc)
        if not existing or (existing == "PB-MGT" and cc != "PB-MGT"):
            home_map[fc] = cc

    drift = []
    for d in docs:
        fc = (d.get("franchise_code") or "").upper().strip()
        if not fc:
            continue
        target = home_map.get(fc)
        if not target:
            continue
        current = (d.get("center") or "").upper().strip()
        if current != target:
            drift.append((d.get("document_id"), fc, current, target))

    print(f"Found {len(drift)} mis-tagged franchise document(s):")
    for doc_id, fc, old, new in drift:
        print(f"  - {doc_id}  franchise={fc}  {old} → {new}")

    if not drift:
        print("\n✅ Nothing to fix.")
        return

    if not apply:
        print("\nDRY-RUN. Re-run with --apply to commit.")
        return

    for doc_id, fc, old, new in drift:
        await db.documents.update_one({"document_id": doc_id}, {"$set": {"center": new}})
    print(f"\n✅ Updated {len(drift)} document(s).")


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    asyncio.run(main(apply))
