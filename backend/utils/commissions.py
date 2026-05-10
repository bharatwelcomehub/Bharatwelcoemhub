"""Canonical commission aggregator — single source of truth used by every
financial surface (Center Accounts, Owner Reports, MIS Dashboard, MG Payout).

WHY THIS EXISTS:
Before this helper, four surfaces each had their own commission summation logic:
  1. Owner Reports summed only `other_deductions`              → ₹15,900 base
  2. Owner Reports (post Apr-2026 fix) summed all 4 fields    → ₹21,588 inclusive
  3. MIS Dashboard summed `gst_tax_deductions + other_deductions OR
     commission_amount + gst_on_commission`, then applied WC overrides
  4. MG Payout summed both `commission_statements` (legacy) AND
     `monthly_commissions`, no overrides

This produced byte-level drift between dashboards for the same center+month.
The May-2026 audit (audit_financial_parity.py) caught it on PB-MGT 2026-01.

Now every surface MUST call `get_total_commissions(...)` so all reports
agree to the rupee.
"""

from typing import Tuple, Dict, Any, Optional


def _row_total(c: Dict[str, Any]) -> float:
    """Sum the four India commission fields for a single monthly_commissions row.
    Equivalent to the inclusive figure shown on the MG Payout report's Comm column."""
    return (
        float(c.get("commission_amount", 0) or 0)
        + float(c.get("other_deductions", 0) or 0)
        + float(c.get("gst_tax_deductions", 0) or 0)
        + float(c.get("tds", 0) or 0)
    )


def _row_gst(c: Dict[str, Any]) -> float:
    """Commission GST portion for a single row.
    Prefers the explicit `gst_tax_deductions` field; falls back to 18% of
    `commission_amount` so the documented "18% GST on commission" rule is
    honoured for India even when uploads omit the field."""
    gtd = float(c.get("gst_tax_deductions", 0) or 0)
    if gtd > 0:
        return gtd
    base = float(c.get("commission_amount", 0) or 0)
    return round(base * 0.18, 2) if base > 0 else 0.0


async def get_total_commissions(
    db,
    center: str,
    month: str,
) -> Dict[str, Any]:
    """Return canonical commission figures for {center, month}.

    Returns a dict with:
      - total:          inclusive commission (commission base + comm GST + TDS).
                        For Australia, the commission GST is applied as a 10%
                        grossup on the base since AU uploads typically don't
                        populate gst_tax_deductions explicitly.
      - commission_gst: portion of total that is commission GST
      - base:           total - commission_gst (commission excl. GST)
      - override_applied: True if a wc_overrides commission_target was applied
      - source:         one of "uploaded", "override", "empty"
      - rows:           the raw monthly_commissions docs (for breakdown UIs)

    Resolution order:
      1. If wc_overrides[(center, month)].commission_target is set,
         use it as the total (overrides win — Accounts team's authoritative entry).
      2. Otherwise, sum the 4 fields across all monthly_commissions rows
         (or apply AU 10% grossup if outside India).
      3. If neither has data, fall back to commission_statements (legacy).
    """
    # Country detection — drives the AU 10% grossup vs India inclusive path.
    center_doc = await db.centers.find_one({"code": center}, {"_id": 0, "country": 1})
    country = (center_doc or {}).get("country") or (
        "Australia" if str(center).upper().endswith("-PERTH") else "India"
    )

    rows = await db.monthly_commissions.find(
        {"center": center, "month": month}, {"_id": 0}
    ).to_list(500)

    if country == "Australia":
        # AU: commission upload usually carries only `other_deductions`
        # (the platform commission). GST is added on top as 10% grossup.
        au_base = round(sum(float(r.get("other_deductions", 0) or 0) for r in rows), 2)
        au_base = au_base or round(sum(float(r.get("commission_amount", 0) or 0) for r in rows), 2)
        uploaded_gst = round(au_base * 0.10, 2)
        uploaded_total = round(au_base + uploaded_gst, 2)
    else:
        uploaded_total = round(sum(_row_total(r) for r in rows), 2)
        uploaded_gst = round(sum(_row_gst(r) for r in rows), 2)

    # Check WC override (Accounts team's manual entry)
    override_doc = await db.wc_overrides.find_one(
        {"center": center, "month": month}, {"_id": 0, "commission_target": 1}
    )
    commission_target = (override_doc or {}).get("commission_target")

    if commission_target is not None:
        total = round(float(commission_target), 2)
        # When an override is set, the GST split isn't known — assume 18% on the
        # base portion if uploads gave us a hint, else 18% of the override value.
        if uploaded_gst > 0 and uploaded_total > 0:
            ratio = uploaded_gst / uploaded_total
            comm_gst = round(total * ratio, 2)
        else:
            comm_gst = round(total * 0.18 / 1.18, 2)
        return {
            "total": total,
            "commission_gst": comm_gst,
            "base": round(total - comm_gst, 2),
            "override_applied": True,
            "source": "override",
            "rows": rows,
        }

    if uploaded_total > 0:
        return {
            "total": uploaded_total,
            "commission_gst": uploaded_gst,
            "base": round(uploaded_total - uploaded_gst, 2),
            "override_applied": False,
            "source": "uploaded",
            "rows": rows,
        }

    # Legacy fallback: commission_statements
    year, mon = month.split("-")
    start = f"{year}-{mon}-01"
    end = f"{int(year) + 1}-01-01" if int(mon) == 12 else f"{year}-{int(mon) + 1:02d}-01"
    legacy = await db.commission_statements.find({
        "center": center,
        "settlement_period_start": {"$gte": start},
        "settlement_period_end": {"$lt": end},
    }, {"_id": 0, "commission_charged": 1}).to_list(100)
    legacy_base = round(sum(float(r.get("commission_charged", 0) or 0) for r in legacy), 2)
    if country == "Australia" and legacy_base > 0:
        legacy_gst = round(legacy_base * 0.10, 2)
        legacy_total = round(legacy_base + legacy_gst, 2)
    else:
        legacy_gst = 0.0
        legacy_total = legacy_base
    return {
        "total": legacy_total,
        "commission_gst": legacy_gst,
        "base": legacy_base,
        "override_applied": False,
        "source": "legacy" if legacy_total > 0 else "empty",
        "rows": rows,
    }
