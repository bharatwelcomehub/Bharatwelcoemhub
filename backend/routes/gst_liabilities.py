"""GST Liability & Payment Tracking.

Business rule (Apr 2026):
- Month M: GST is *calculated* on eligible sales (Total − Swiggy − Zomato − DoorDash)
  and recorded as a LIABILITY for the center+month (no expense entry yet).
- Month M+1, before the 20th: GST is PAID; this creates an expense entry
  in Month M+1 with category "GST PAYMENT" and flags the liability as paid.
- Dashboards show GST PAYABLE (unpaid liabilities, FIFO by month) distinctly
  from GST PAID (the expense ledger row).

Collection: `gst_liabilities`
   keyed by (center, month)
   fields: center, month, country, rate, eligible_base, gst_amount,
           paid (bool), paid_date, paid_month, paid_expense_id,
           auto_computed (bool — recomputed from daily_sales on each call)
"""
from datetime import datetime, timezone
from typing import Optional
import logging
import os

from fastapi import APIRouter, HTTPException, Body
from motor.motor_asyncio import AsyncIOMotorClient

from .attendance_dashboard import get_session, check_super_admin
from .owner_reports import check_release_access
from utils.gst import compute_gst_from_rows, gst_rate_for

logger = logging.getLogger(__name__)

_mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _mongo[os.environ["DB_NAME"]]

router = APIRouter(prefix="/api/gst", tags=["gst"])


def _next_month(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    if m == 12:
        return f"{y + 1:04d}-01"
    return f"{y:04d}-{m + 1:02d}"


async def _recompute_liability(center: str, month: str) -> dict:
    """Compute GST from daily_sales and upsert (but don't mark paid)."""
    rows = await db.daily_sales.find(
        {"center": center, "date": {"$regex": f"^{month}"}}, {"_id": 0}
    ).to_list(1000)
    calc = compute_gst_from_rows(rows, None, center)
    now = datetime.now(timezone.utc).isoformat()
    doc_set = {
        "center": center, "month": month,
        "rate": calc["rate"],
        "eligible_base": calc["eligible_base"],
        "gst_amount": calc["gst_amount"],
        "total_sale": calc["total_sale"],
        "aggregator_sale": calc["aggregator_sale"],
        "auto_computed": True,
        "updated_at": now,
    }
    # Don't overwrite paid status if already recorded.
    existing = await db.gst_liabilities.find_one({"center": center, "month": month}, {"_id": 0})
    if not existing:
        doc_set["paid"] = False
        doc_set["created_at"] = now
    await db.gst_liabilities.update_one(
        {"center": center, "month": month},
        {"$set": doc_set},
        upsert=True,
    )
    return await db.gst_liabilities.find_one({"center": center, "month": month}, {"_id": 0})


@router.post("/recompute")
async def recompute(req: dict = Body(...)):
    """Recompute liabilities from daily_sales. Scope: {center, month} optional."""
    session = await get_session(req.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")
    center = req.get("center")
    month = req.get("month")
    if center and month:
        return {"success": True, "row": await _recompute_liability(center, month)}
    # All centers × all months where daily_sales exist
    pipeline = [{"$group": {"_id": {"center": "$center", "month": {"$substr": ["$date", 0, 7]}}}}]
    buckets = await db.daily_sales.aggregate(pipeline).to_list(5000)
    updated = 0
    for b in buckets:
        c = b["_id"].get("center")
        m = b["_id"].get("month")
        if not c or not m:
            continue
        await _recompute_liability(c, m)
        updated += 1
    return {"success": True, "recomputed": updated}


@router.post("/liabilities")
async def list_liabilities(req: dict = Body(...)):
    """List GST liabilities (optionally filtered by center, paid/unpaid, year)."""
    session = await get_session(req.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")
    q = {}
    if req.get("center") and req["center"] != "all":
        q["center"] = req["center"]
    if req.get("year"):
        q["month"] = {"$regex": f"^{int(req['year']):04d}-"}
    status = (req.get("status") or "").lower()  # 'paid' / 'unpaid' / '' (all)
    if status == "paid":
        q["paid"] = True
    elif status == "unpaid":
        q["paid"] = {"$ne": True}
    rows = await db.gst_liabilities.find(q, {"_id": 0}).sort("month", 1).to_list(5000)
    total_payable = sum(float(r.get("gst_amount", 0) or 0) for r in rows if not r.get("paid"))
    total_paid = sum(float(r.get("gst_amount", 0) or 0) for r in rows if r.get("paid"))
    return {
        "rows": rows,
        "total_payable": round(total_payable, 2),
        "total_paid": round(total_paid, 2),
    }


@router.post("/mark-paid")
async def mark_paid(req: dict = Body(...)):
    """Mark a GST liability as paid. Creates a corresponding expense row in the
    payment month (defaults to M+1) with category 'GST PAYMENT'."""
    session = await get_session(req.get("token"))
    if not session or not check_release_access(session):
        raise HTTPException(403, "Only Super Admin can record GST payments")
    center = req.get("center")
    month = req.get("month")          # liability month (M)
    paid_date = req.get("paid_date")  # YYYY-MM-DD; default: 20th of M+1
    paid_month = (paid_date or "")[:7] if paid_date else _next_month(month)
    if not paid_date:
        paid_date = f"{paid_month}-20"
    user = session.get("managerName", "Admin")
    now = datetime.now(timezone.utc).isoformat()
    
    liab = await db.gst_liabilities.find_one({"center": center, "month": month}, {"_id": 0})
    if not liab:
        raise HTTPException(404, f"No GST liability for {center} {month}")
    if liab.get("paid"):
        return {"success": True, "already_paid": True, "row": liab}
    amount = float(liab.get("gst_amount", 0))
    if amount <= 0:
        raise HTTPException(400, "Liability amount is zero — nothing to pay")
    
    # Create expense row in M+1
    expense_doc = {
        "center": center, "date": paid_date,
        "expense_type": "GST PAYMENT",
        "description": f"GST for {month} paid on {paid_date}",
        "amount": round(amount, 2),
        "payment_mode": req.get("payment_mode", "BANK"),
        "source": "gst_liability_payment",
        "gst_liability_month": month,
        "created_by": user, "created_at": now, "updated_at": now,
    }
    res = await db.expenses.insert_one(expense_doc)
    expense_id = str(res.inserted_id)
    
    await db.gst_liabilities.update_one(
        {"center": center, "month": month},
        {"$set": {
            "paid": True, "paid_date": paid_date, "paid_month": paid_month,
            "paid_expense_id": expense_id, "paid_by": user,
            "paid_at": now, "updated_at": now,
        }},
    )
    return {"success": True, "paid_date": paid_date, "paid_month": paid_month, "amount": round(amount, 2), "expense_id": expense_id}


@router.post("/unmark-paid")
async def unmark_paid(req: dict = Body(...)):
    """Reverse a GST payment: deletes the expense row and clears paid flags.
    Useful when an accounting mistake is made."""
    session = await get_session(req.get("token"))
    if not session or not check_release_access(session):
        raise HTTPException(403, "Only Super Admin can reverse GST payments")
    center = req.get("center")
    month = req.get("month")
    liab = await db.gst_liabilities.find_one({"center": center, "month": month}, {"_id": 0})
    if not liab or not liab.get("paid"):
        raise HTTPException(404, "Not paid or liability missing")
    exp_id = liab.get("paid_expense_id")
    if exp_id:
        from bson import ObjectId
        try:
            await db.expenses.delete_one({"_id": ObjectId(exp_id)})
        except Exception:
            pass
    await db.gst_liabilities.update_one(
        {"center": center, "month": month},
        {"$unset": {"paid": "", "paid_date": "", "paid_month": "", "paid_expense_id": "", "paid_by": "", "paid_at": ""},
         "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"success": True}
