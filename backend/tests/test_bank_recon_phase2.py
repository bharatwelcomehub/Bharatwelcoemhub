"""Phase 2 — Bank Reconciliation upgrade regression tests.

Verifies:
- Cash-withdrawal auto-ignore
- Debit exact + partial (fuzzy date / fuzzy amount) matching
- Credit-side reconciliation against PhonePe settlement (PG commission carried through)
- Unmatched credit gets a source hint
- High-value unmatched routes to manual_review
"""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Module-level event loop so Motor's connection stays alive across tests
_LOOP = asyncio.new_event_loop()


def _run(coro):
    return _LOOP.run_until_complete(coro)


@pytest.fixture(scope="module")
def setup_and_db():
    from motor.motor_asyncio import AsyncIOMotorClient
    from routes import bank_reconciliation as br

    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    br.init_db(db)

    test_center = "TEST-BR-PHASE2"
    test_month = "2026-02"

    async def seed():
        await db.expenses.delete_many({"center": test_center})
        await db.daily_sales.delete_many({"center": test_center})
        await db.monthly_commissions.delete_many({"center": test_center})
        await db.expenses.insert_many([
            {"expense_id": "tbr-1", "center": test_center, "date": "2026-02-05",
             "amount": 15000.0, "expense_type": "RENT PAID SHOP", "payment_mode": "Bank Transfer"},
            {"expense_id": "tbr-2", "center": test_center, "date": "2026-02-10",
             "amount": 1003.0, "expense_type": "ELECTRICITY", "payment_mode": "Bank Transfer"},
        ])
        await db.daily_sales.insert_one({
            "center": test_center, "date": "2026-02-15",
            "total_cash_sale": 8000.0,
            "total_online_sale": 12500.0,
        })
        await db.monthly_commissions.insert_one({
            "center": test_center, "month": test_month,
            "platform": "phonepe",
            "net_settlement_amount": 33000.0,
            "settlement_date": "2026-02-28",
            "sundry_debtors": 1700.0,
            "gst_tax_deductions": 306.0,
        })
    _run(seed())

    yield db, test_center, test_month, br

    async def teardown():
        await db.expenses.delete_many({"center": test_center})
        await db.daily_sales.delete_many({"center": test_center})
        await db.monthly_commissions.delete_many({"center": test_center})
    _run(teardown())


def test_cash_withdrawal_auto_ignored(setup_and_db):
    _, center, month, br = setup_and_db
    txns = [{
        "transaction_id": "t-atm",
        "transaction_date": "2026-02-07",
        "narration": "ATM CASH WDL XYZ123",
        "debit_amount": 5000.0, "credit_amount": 0.0, "txn_type": "debit",
    }]
    buckets = _run(br.match_transactions(txns, center, month))
    assert len(buckets["ignored"]) == 1
    assert buckets["ignored"][0]["match_status"] == "ignored"
    assert buckets["ignored"][0]["auto_ignored"] is True
    assert "Cash Withdrawal" in buckets["ignored"][0]["ignore_reason"]


def test_debit_exact_match(setup_and_db):
    _, center, month, br = setup_and_db
    txns = [{
        "transaction_id": "t-rent",
        "transaction_date": "2026-02-05",
        "narration": "RENT PAID SHOP FEB 2026",
        "debit_amount": 15000.0, "credit_amount": 0.0, "txn_type": "debit",
    }]
    buckets = _run(br.match_transactions(txns, center, month))
    assert len(buckets["matched"]) == 1
    assert buckets["matched"][0]["match_method"] == "exact_date_amount"


def test_debit_partial_match_fuzzy_amount(setup_and_db):
    _, center, month, br = setup_and_db
    txns = [{
        "transaction_id": "t-elec",
        "transaction_date": "2026-02-10",
        "narration": "ELECTRICITY BILL FEB",
        "debit_amount": 1000.0,   # 0.3% drift from booked 1003
        "credit_amount": 0.0, "txn_type": "debit",
    }]
    buckets = _run(br.match_transactions(txns, center, month))
    assert len(buckets["partially_matched"]) == 1
    method = buckets["partially_matched"][0]["match_method"]
    assert "fuzzy_amount" in method


def test_credit_phonepe_settlement_matched(setup_and_db):
    _, center, month, br = setup_and_db
    txns = [{
        "transaction_id": "t-pp",
        "transaction_date": "2026-02-28",
        "narration": "PHONEPE NEFT SETTLEMENT",
        "debit_amount": 0.0, "credit_amount": 33000.0, "txn_type": "credit",
    }]
    buckets = _run(br.match_transactions(txns, center, month))
    assert len(buckets["matched"]) == 1
    m = buckets["matched"][0]
    assert m["matched_credit"]["source"] == "phonepe"
    # PG Commission carried through so the UI can show it on the matched row
    assert m["matched_credit"]["pg_commission"] == 1700.0


def test_credit_unmatched_with_source_hint(setup_and_db):
    _, center, month, br = setup_and_db
    txns = [{
        "transaction_id": "t-rzp",
        "transaction_date": "2026-02-20",
        "narration": "RAZORPAY SETTLEMENT XYZ",
        "debit_amount": 0.0, "credit_amount": 999.0, "txn_type": "credit",
    }]
    buckets = _run(br.match_transactions(txns, center, month))
    assert len(buckets["unmatched_credits"]) == 1
    assert buckets["unmatched_credits"][0]["credit_source_hint"] == "razorpay"


def test_high_value_debit_routed_to_manual_review(setup_and_db):
    _, center, month, br = setup_and_db
    txns = [{
        "transaction_id": "t-big",
        "transaction_date": "2026-02-12",
        "narration": "UNKNOWN VENDOR PAYMENT",
        "debit_amount": 75000.0, "credit_amount": 0.0, "txn_type": "debit",
    }]
    buckets = _run(br.match_transactions(txns, center, month))
    assert len(buckets["manual_review"]) == 1
    assert buckets["manual_review"][0]["match_status"] == "manual_review"
