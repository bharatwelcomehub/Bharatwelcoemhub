"""Regression test for the Feb-2026 management-reporting directive:
PBT must be calculated on GROSS sales (GST is NOT subtracted).

Replicates the worked example from the user spec:
  Sales = ₹10,00,000  GST = ₹50,000  Expenses = ₹7,00,000  Commission = ₹50,000
  Required PBT = 10,00,000 − 7,00,000 − 50,000 = ₹2,50,000  (NOT 2,00,000)
"""
import asyncio
import os
import uuid

import pytest


@pytest.fixture(scope="module")
def db():
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    return cli[os.environ["DB_NAME"]]


def _run(c):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(c)
    finally:
        loop.close()


def test_pnl_uses_gross_sales_not_ex_gst(db):
    """Insert one isolated synthetic month and confirm PBT = Gross − Exp − Comm."""
    test_center = f"TEST-PL-{uuid.uuid4().hex[:5].upper()}"
    test_month = "2099-01"
    sales_id = f"sale-{uuid.uuid4().hex[:8]}"
    exp_id = f"exp-{uuid.uuid4().hex[:8]}"
    comm_id = f"comm-{uuid.uuid4().hex[:8]}"

    async def _go():
        import server
        server.db = db
        # Pre-create center so country lookup works
        await db.centers.update_one(
            {"code": test_center},
            {"$setOnInsert": {"code": test_center, "name": "Test PL Center", "country": "India"}},
            upsert=True,
        )
        # Inject one sale row, one expense row, one commission row
        await db.daily_sales.insert_one({
            "_id": sales_id, "center": test_center, "date": "2099-01-15",
            "total_sale": 1_000_000, "online_sale": 1_000_000,
        })
        await db.expenses.insert_one({
            "_id": exp_id, "center": test_center, "date": "2099-01-15",
            "amount": 700_000, "expense_type": "RENT",
        })
        await db.monthly_commissions.insert_one({
            "_id": comm_id, "center": test_center, "month": test_month,
            "platform": "zomato",
            "gross_amount": 0, "other_deductions": 50_000,
            "gst_tax_deductions": 0, "commission_amount": 0,
        })
        try:
            from routes.ledgers import build_monthly_pnl
            res = await build_monthly_pnl(test_center, [test_month])
            r = res["rows"][0]
            assert r["sales_gross"] == 1_000_000
            assert r["expenses"] == 700_000  # no adjustments
            assert r["commissions"] == 50_000
            # KEY: PBT should equal 2,50,000 — NOT 2,00,000
            assert r["pbt"] == 250_000, (
                f"Expected PBT 250,000 (Gross − Exp − Comm); got {r['pbt']}. "
                "If 200,000, the legacy Ex-GST formula is still in use."
            )
        finally:
            await db.daily_sales.delete_one({"_id": sales_id})
            await db.expenses.delete_one({"_id": exp_id})
            await db.monthly_commissions.delete_one({"_id": comm_id})
            await db.centers.delete_one({"code": test_center})

    _run(_go())
