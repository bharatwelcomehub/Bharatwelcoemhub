"""Single source of truth for monthly expense adjustments.

An adjustment represents prepaid / future-period expense that was recorded in
the current month but logically belongs to a different month. It is NEVER
allowed to modify the underlying expense row — adjustments only flow through
profitability + revenue-share math.
"""
from typing import Dict, List


async def get_total_adjustments(db, center: str, month: str) -> Dict:
    """Return total adjustment amount + list of adjustment rows for one
    (center, month). Safe to call when none exist — returns total=0, rows=[]."""
    if not center or not month:
        return {"total": 0.0, "rows": []}
    rows: List[Dict] = await db.expense_adjustments.find(
        {"center": center, "month": month},
        {"_id": 0},
    ).to_list(500)
    total = round(sum(float(r.get("adjustment_amount", 0) or 0) for r in rows), 2)
    return {"total": total, "rows": rows}
