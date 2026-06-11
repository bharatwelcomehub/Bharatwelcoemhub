"""Regression test — when a manager records an expense adjustment, it MUST
flow through to every place that shows total expenses or profit:
   • build_monthly_pnl (P&L PDF / ledger)
   • financial_health._snapshot (Financial Health module)
   • MIS Dashboard overview (cross-checked via API endpoint, deferred)
   • owner_reports (already uses adjusted; covered in test_owner_reports)

The test inserts a synthetic adjustment, asserts the downstream numbers
shift by exactly that amount, then cleans up.
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


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_adjustment_propagates_to_pnl_and_financial_health(db):
    """Insert a ₹50k adjustment for a real center/month with sales+expenses
    data, then confirm both build_monthly_pnl and _snapshot subtract it."""
    test_center = "PB-HSR"
    test_month = "2026-02"   # known to have expense rows in seed data
    test_id = f"TEST-{uuid.uuid4().hex[:6]}"
    adj_amount = 50000.0

    async def _go():
        import server
        server.db = db

        from routes.ledgers import build_monthly_pnl
        from routes.financial_health import _snapshot

        # ── Baseline (no adjustment) ────────────────────────────────────
        pnl_before = await build_monthly_pnl(test_center, [test_month])
        fh_before = await _snapshot(test_center,
                                     {"type": "month", "month": test_month})

        # ── Inject adjustment ──────────────────────────────────────────
        await db.expense_adjustments.insert_one({
            "adjustment_id": test_id,
            "center": test_center,
            "month": test_month,
            "expense_date": f"{test_month}-15",
            "expense_head": "GST PAID",
            "adjustment_amount": adj_amount,
            "reason": "regression test",
            "created_at": "2026-02-15T10:00:00Z",
            "created_by": "test-runner",
        })

        try:
            pnl_after = await build_monthly_pnl(test_center, [test_month])
            fh_after = await _snapshot(test_center,
                                        {"type": "month", "month": test_month})

            r_before = pnl_before["rows"][0]
            r_after = pnl_after["rows"][0]

            # P&L expenses must drop by adj_amount
            assert abs((r_before["expenses_raw"] - r_after["expenses_raw"])) < 0.5
            assert abs((r_after["expenses"] - (r_before["expenses"] - adj_amount))) < 0.5
            assert abs((r_after["adjustments"] - r_before.get("adjustments", 0)) - adj_amount) < 0.5
            # PBT must rise by exactly adj_amount
            assert abs((r_after["pbt"] - r_before["pbt"]) - adj_amount) < 0.5, \
                f"PBT delta wrong: {r_after['pbt'] - r_before['pbt']}"

            # Financial Health snapshot must mirror the same shift
            s_b = fh_before["summary"]
            s_a = fh_after["summary"]
            assert abs((s_a["adjustments"] - s_b.get("adjustments", 0)) - adj_amount) < 0.5
            assert abs((s_a["total_expenses_raw"] - s_b.get("total_expenses_raw", s_b["total_expenses"]))) < 0.5
            assert abs((s_a["net_profit"] - s_b["net_profit"]) - adj_amount) < 0.5, \
                f"FH net_profit delta wrong: {s_a['net_profit'] - s_b['net_profit']}"

        finally:
            await db.expense_adjustments.delete_one({"adjustment_id": test_id})

    _run(_go())
