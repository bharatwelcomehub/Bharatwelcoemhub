"""Phase 3 - 5 gaps end-to-end HTTP integration tests.

Validates:
  A. /auto-convert-credits-to-sales creates daily_sales rows from AI-tagged credits
  B. /ai-categorize handles BOTH debits AND credits (debit_categorized, credit_categorized)
  C. /edit-transaction inline editing; preserves original_narration; logs changes
  D. (UI only — covered in playwright)
  E. original_narration immutable copy stored at upload; edited_by/edited_at on edit

Center: TEST-MGT-CREDIT, Month: 2026-02
Live Claude call is OPT-IN via CLAUDE_BUDGET=1 (uses ~3 transactions only).
"""
import io
import os
import uuid
import asyncio

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")

TEST_CENTER = "TEST-MGT-CREDIT"
TEST_MONTH = "2026-02"


@pytest.fixture(scope="module")
def token():
    requests.post(f"{BASE_URL}/api/send_otp",
                  json={"mobile": "9741399190", "center": "PB-MGT"}, timeout=20)
    r = requests.post(f"{BASE_URL}/api/verify_otp",
                      json={"mobile": "9741399190", "otp": "123456",
                            "center": "PB-MGT"}, timeout=20)
    assert r.status_code == 200, r.text
    tok = r.json().get("token")
    assert tok, f"no token: {r.json()}"
    return tok


@pytest.fixture(scope="module")
def db_loop():
    """Open Motor client + seed/teardown daily_sales dedupe row."""
    from motor.motor_asyncio import AsyncIOMotorClient
    loop = asyncio.new_event_loop()
    cli = AsyncIOMotorClient(MONGO_URL)
    db = cli[DB_NAME]

    async def seed():
        # Clean prior runs
        await db.daily_sales.delete_many({"center": TEST_CENTER})
        await db.bank_transactions.delete_many({"center": TEST_CENTER})
        await db.bank_statement_uploads.delete_many({"center": TEST_CENTER})
        await db.expense_reconciliation_log.delete_many({})
        # Seed a daily_sales row for 2026-02-15 to test dedupe path
        await db.daily_sales.insert_one({
            "id": f"ds-{uuid.uuid4().hex[:8]}",
            "center": TEST_CENTER,
            "date": "2026-02-15",
            "total_sale": 5000.0,
            "phonepe": 5000.0,
            "source": "manual",
        })

    loop.run_until_complete(seed())
    yield db, loop

    async def teardown():
        await db.daily_sales.delete_many({"center": TEST_CENTER})
        await db.bank_transactions.delete_many({"center": TEST_CENTER})
        await db.bank_statement_uploads.delete_many({"center": TEST_CENTER})
        await db.expense_reconciliation_log.delete_many({})
    loop.run_until_complete(teardown())
    loop.close()


def _csv_bytes():
    """CSV with several credit rows:
       - 2026-02-15 PhonePe credit (will be deduped against seeded daily_sales)
       - 2026-02-20 Razorpay credit (new row)
       - 2026-02-22 SWIGGY credit (new row)
       - 2026-02-23 Inter-account transfer (must be skipped)
       - 1 debit (so /ai-categorize handles both sides)
    """
    rows = [
        "Date,Narration,Debit,Credit,Balance",
        "15-02-2026,PHONEPE SETTLEMENT 15FEB,0,4000,104000",
        "20-02-2026,RAZORPAY PAYOUT REF111,0,2500,106500",
        "22-02-2026,SWIGGY SETTLEMENT REF222,0,1800,108300",
        "23-02-2026,NEFT SELF TRANSFER ACC9999,0,7000,115300",
        "18-02-2026,STAPLES PURCHASE BILL,300,0,115000",
    ]
    return "\n".join(rows).encode("utf-8")


# ───────── A. Upload + original_narration (Gap E) ──────────────────────
class TestUploadAndOriginalNarration:
    upload_id = None

    def test_upload_credits(self, token, db_loop):
        files = {"file": ("phase3.csv", _csv_bytes(), "text/csv")}
        data = {"center": TEST_CENTER, "month": TEST_MONTH,
                "bank_account": "MGT-IDFC-TEST", "token": token}
        r = requests.post(f"{BASE_URL}/api/bank-reconciliation/upload",
                          files=files, data=data, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("success") is True
        TestUploadAndOriginalNarration.upload_id = body["upload_id"]
        # Credits should be in unmatched_credits bucket (4 credits)
        assert len(body["unmatched_credits"]) >= 3

    def test_original_narration_populated_on_upload(self, db_loop):
        """Gap E: every bank_transactions doc must have original_narration set."""
        db, loop = db_loop

        async def check():
            txns = await db.bank_transactions.find(
                {"upload_id": TestUploadAndOriginalNarration.upload_id},
                {"_id": 0},
            ).to_list(100)
            assert len(txns) >= 5
            for t in txns:
                assert "original_narration" in t, f"missing on {t.get('narration')}"
                assert t["original_narration"], "original_narration is empty"
                # At upload time they must be identical
                assert t["original_narration"] == t.get("narration"), (
                    f"original_narration != narration: {t}"
                )
            return txns

        return loop.run_until_complete(check())


# ───────── C + E. Edit-transaction endpoint ────────────────────────────
class TestEditTransaction:
    """Inline edit: preserves original_narration, tracks edited_by/edited_at,
    logs change array."""

    def _pick_txn(self, db_loop, narration_filter):
        db, loop = db_loop

        async def find():
            return await db.bank_transactions.find_one(
                {"upload_id": TestUploadAndOriginalNarration.upload_id,
                 "narration": {"$regex": narration_filter}},
                {"_id": 0},
            )
        return loop.run_until_complete(find())

    def test_edit_narration_preserves_original(self, token, db_loop):
        assert TestUploadAndOriginalNarration.upload_id
        txn = self._pick_txn(db_loop, "RAZORPAY")
        assert txn, "Razorpay txn not found"
        old_narr = txn["narration"]
        old_orig = txn["original_narration"]

        r = requests.post(
            f"{BASE_URL}/api/bank-reconciliation/edit-transaction",
            json={
                "upload_id": TestUploadAndOriginalNarration.upload_id,
                "transaction_id": txn["transaction_id"],
                "token": token,
                "narration": "RAZORPAY (cleaned up)",
                "ai_suggested_category": "Razorpay Sale",
            },
            timeout=20,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("success") is True, body
        changes = body.get("changes", [])
        fields_changed = {c["field"] for c in changes}
        assert "narration" in fields_changed
        assert "ai_suggested_category" in fields_changed
        # Each change must contain field/old/new
        for c in changes:
            assert "field" in c and "old" in c and "new" in c

        # Verify DB state
        db, loop = db_loop

        async def verify():
            updated = await db.bank_transactions.find_one(
                {"transaction_id": txn["transaction_id"]}, {"_id": 0})
            # narration updated
            assert updated["narration"] == "RAZORPAY (cleaned up)"
            # original preserved
            assert updated["original_narration"] == old_orig == old_narr
            # ai_suggested_category set
            assert updated["ai_suggested_category"] == "Razorpay Sale"
            # edited_by + edited_at present
            assert updated.get("edited_by")
            assert updated.get("edited_at")
            # Log entry present with changes array
            log = await db.expense_reconciliation_log.find_one(
                {"bank_transaction_id": txn["transaction_id"],
                 "action": "edit_transaction"}, {"_id": 0})
            assert log, "edit_transaction log missing"
            assert isinstance(log.get("changes"), list) and len(log["changes"]) >= 2

        loop.run_until_complete(verify())

    def test_edit_no_changes_returns_empty(self, token, db_loop):
        txn = self._pick_txn(db_loop, "SWIGGY")
        assert txn
        r = requests.post(
            f"{BASE_URL}/api/bank-reconciliation/edit-transaction",
            json={"upload_id": TestUploadAndOriginalNarration.upload_id,
                  "transaction_id": txn["transaction_id"], "token": token},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("success") is True
        # No fields => no changes
        assert body.get("changes") == [] or body.get("message") == "No changes"

    def test_edit_missing_transaction(self, token):
        r = requests.post(
            f"{BASE_URL}/api/bank-reconciliation/edit-transaction",
            json={"upload_id": TestUploadAndOriginalNarration.upload_id,
                  "transaction_id": "does-not-exist-xyz", "token": token,
                  "narration": "x"},
            timeout=20,
        )
        # Endpoint returns 200 with success=False per current shape
        assert r.status_code == 200
        body = r.json()
        assert body.get("success") is False or body.get("detail")


# ───────── B. AI categorize handles BOTH sides ─────────────────────────
@pytest.mark.skipif(not os.environ.get("CLAUDE_BUDGET"),
                    reason="set CLAUDE_BUDGET=1 to allow live Claude call")
class TestAICategorize:
    def test_ai_categorize_returns_both_counts(self, token, db_loop):
        # Limit to 3 txns to keep budget small
        db, loop = db_loop

        async def pick_ids():
            txns = await db.bank_transactions.find(
                {"upload_id": TestUploadAndOriginalNarration.upload_id},
                {"_id": 0, "transaction_id": 1, "txn_type": 1, "narration": 1},
            ).to_list(50)
            # one debit + 2 credits
            debits = [t["transaction_id"] for t in txns if t.get("txn_type") == "debit"][:1]
            credits = [t["transaction_id"] for t in txns if t.get("txn_type") == "credit"][:2]
            return debits + credits

        ids = loop.run_until_complete(pick_ids())
        assert len(ids) >= 2

        r = requests.post(
            f"{BASE_URL}/api/bank-reconciliation/ai-categorize",
            json={"upload_id": TestUploadAndOriginalNarration.upload_id,
                  "token": token, "transaction_ids": ids},
            timeout=120,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("success") is True, body
        # New response keys
        assert "debit_categorized" in body, body
        assert "credit_categorized" in body, body
        # At least some categorized
        assert body.get("categorized", 0) >= 1


# ───────── A + dedupe. Auto-convert credits → daily_sales ──────────────
class TestAutoConvertCredits:
    """Force-tag credits without Claude so test is deterministic and free.

    Marks the seeded credits with ai_suggested_category + ai_confidence ≥ 0.7
    directly in Mongo, then calls /auto-convert-credits-to-sales.
    """

    def _force_tag(self, db_loop):
        db, loop = db_loop

        async def tag():
            tag_map = [
                ("PHONEPE", "PhonePe Sale", 0.95),
                ("RAZORPAY", "Razorpay Sale", 0.92),
                ("SWIGGY", "Swiggy Sale", 0.91),
                ("NEFT SELF", "Inter-Account Transfer", 0.90),
            ]
            for needle, cat, conf in tag_map:
                await db.bank_transactions.update_many(
                    {"upload_id": TestUploadAndOriginalNarration.upload_id,
                     "narration": {"$regex": needle}, "txn_type": "credit"},
                    {"$set": {"ai_suggested_category": cat,
                              "ai_confidence": conf,
                              "ai_categorized_at": "2026-02-28T00:00:00Z",
                              "ai_side": "credit"}}
                )
        loop.run_until_complete(tag())

    def test_auto_convert_dedupe_and_create(self, token, db_loop):
        assert TestUploadAndOriginalNarration.upload_id
        self._force_tag(db_loop)

        r = requests.post(
            f"{BASE_URL}/api/bank-reconciliation/auto-convert-credits-to-sales",
            json={"upload_id": TestUploadAndOriginalNarration.upload_id,
                  "token": token, "min_confidence": 0.7},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("success") is True
        # Required shape
        for k in ["created", "skipped_dupes", "skipped_transfers"]:
            assert k in body, f"missing {k}: {body}"

        # PHONEPE on 2026-02-15 must be deduped (we pre-seeded that day)
        assert body["skipped_dupes"] >= 1, body
        # NEFT SELF must be a skipped transfer
        assert body["skipped_transfers"] >= 1, body
        # RAZORPAY + SWIGGY are on distinct days with no existing daily_sales
        assert body["created"] >= 2, body

    def test_daily_sales_rows_created_with_source(self, db_loop):
        db, loop = db_loop

        async def check():
            # Razorpay → 2026-02-20
            rz = await db.daily_sales.find_one(
                {"center": TEST_CENTER, "date": "2026-02-20"}, {"_id": 0})
            assert rz, "Razorpay daily_sales row not created"
            assert rz.get("source") == "bank_reconciliation"
            assert rz.get("total_sale") == 2500.0
            assert rz.get("online_other") == 2500.0  # Razorpay Sale → online_other
            assert rz.get("bank_upload_id") == TestUploadAndOriginalNarration.upload_id
            assert isinstance(rz.get("ai_provenance"), list) and rz["ai_provenance"]
            # provenance preserves original_narration
            assert "original_narration" in rz["ai_provenance"][0]

            # Swiggy → 2026-02-22 → swiggy bucket
            sw = await db.daily_sales.find_one(
                {"center": TEST_CENTER, "date": "2026-02-22"}, {"_id": 0})
            assert sw, "Swiggy daily_sales row not created"
            assert sw.get("swiggy") == 1800.0
            assert sw.get("total_sale") == 1800.0

            # The PRE-EXISTING daily_sales on 2026-02-15 must be untouched
            seeded = await db.daily_sales.find_one(
                {"center": TEST_CENTER, "date": "2026-02-15"}, {"_id": 0})
            assert seeded
            assert seeded.get("source") == "manual"
            assert seeded.get("total_sale") == 5000.0  # NOT overwritten

        loop.run_until_complete(check())

    def test_dedupe_marks_bank_txn_as_matched(self, db_loop):
        db, loop = db_loop

        async def check():
            phonepe = await db.bank_transactions.find_one(
                {"upload_id": TestUploadAndOriginalNarration.upload_id,
                 "narration": {"$regex": "PHONEPE"}}, {"_id": 0})
            assert phonepe
            assert phonepe.get("match_status") == "matched"
            assert phonepe.get("match_method") == "auto_convert_dedupe_credit"
            assert phonepe.get("auto_converted") is True

        loop.run_until_complete(check())

    def test_neft_transfer_not_converted(self, db_loop):
        db, loop = db_loop

        async def check():
            # NEFT SELF on 2026-02-23 → no daily_sales row
            neft_day = await db.daily_sales.find_one(
                {"center": TEST_CENTER, "date": "2026-02-23"}, {"_id": 0})
            assert neft_day is None, (
                "Inter-Account Transfer should NOT create daily_sales"
            )

        loop.run_until_complete(check())
