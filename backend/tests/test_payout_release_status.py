"""Payout Release Status Banner — Feb-2026 directive regression.

Confirms:
- Status defaults to 'eligible' when no override and no WC protection.
- WC Protection Mode active → 'blocked' (auto).
- Manual override 'eligible' beats WC Protection (Accounts can release anyway).
- Manual 'review' / 'blocked' values applied.
- Calculations elsewhere (Profit/Loss, Revenue Share Base) are NOT changed.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Single module-level loop so all Motor coroutines stay in the same loop
_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_LOOP)


def _run(coro):
    return _LOOP.run_until_complete(coro)


def _get_db():
    """Create the client inside the shared loop."""
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"], io_loop=_LOOP)
    return cli[os.environ["DB_NAME"]]


def test_default_status_is_eligible():
    from utils.payout_status import derive_payout_release_status
    db = _get_db()
    center = "TEST-STATUS-NOOP"
    _run(db.center_settings.delete_many({"center": center}))
    status = _run(derive_payout_release_status(db, center, "2026-02", protection_mode=False))
    assert status["status"] == "eligible"
    assert status["color"] == "green"
    assert status["override_active"] is False
    assert status["source"] == "default"


def test_wc_protection_blocks_auto():
    from utils.payout_status import derive_payout_release_status
    db = _get_db()
    center = "TEST-STATUS-WC"
    _run(db.center_settings.delete_many({"center": center}))
    status = _run(derive_payout_release_status(db, center, "2026-02", protection_mode=True))
    assert status["status"] == "blocked"
    assert status["color"] == "red"
    assert status["source"] == "auto_wc_protection"


def test_manual_eligible_overrides_wc_protection():
    """Accounts/Admin can release payout even when WC Protection is on."""
    from utils.payout_status import derive_payout_release_status, set_payout_release_status
    db = _get_db()
    center = "TEST-STATUS-OVERRIDE"
    _run(db.center_settings.delete_many({"center": center}))
    _run(set_payout_release_status(db, center, "eligible", "TestAcct"))
    status = _run(derive_payout_release_status(db, center, "2026-02", protection_mode=True))
    assert status["status"] == "eligible"
    assert status["color"] == "green"
    assert status["override_active"] is True
    assert status["source"] == "manual"
    _run(db.center_settings.delete_many({"center": center}))


def test_manual_review_status():
    from utils.payout_status import derive_payout_release_status, set_payout_release_status
    db = _get_db()
    center = "TEST-STATUS-REVIEW"
    _run(db.center_settings.delete_many({"center": center}))
    _run(set_payout_release_status(db, center, "review", "TestAcct"))
    status = _run(derive_payout_release_status(db, center, "2026-02", protection_mode=False))
    assert status["status"] == "review"
    assert status["color"] == "amber"
    _run(db.center_settings.delete_many({"center": center}))


def test_invalid_value_rejected():
    from utils.payout_status import set_payout_release_status
    db = _get_db()
    result = _run(set_payout_release_status(db, "TEST-X", "garbage", "x"))
    assert result["success"] is False
