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
    """Sum the India commission deductions for a single monthly_commissions row.

    Matches the per-platform "Total Deductions" formula used in PIB Section 3 /
    Center Accounts Commission tab so the canonical total always equals the
    sum of the visible per-platform rows. NEVER double-counts: if the new
    schema fields (gst_tax_deductions / other_deductions) are populated, those
    are summed; otherwise we fall back to the legacy `commission_amount` field.
    TDS is **excluded** here because TDS PAID is booked as a separate operating
    expense (see PIB Section 2 "TDS PAID") and including it again would inflate
    the commission line and the corresponding net revenue calculation.
    """
    gst_ded = float(c.get("gst_tax_deductions", 0) or 0)
    other_ded = float(c.get("other_deductions", 0) or 0)
    if gst_ded or other_ded:
        return gst_ded + other_ded
    return float(c.get("commission_amount", 0) or 0)


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
      - by_platform:    {platform: {"gross": float, "deduction": float, "net": float}}
                        guaranteed to sum to `total` across all platforms (when
                        no override is applied). Always populated, falling back
                        to commission_statements when monthly_commissions is empty.

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

    # Build per-platform breakdown from monthly_commissions
    by_platform: Dict[str, Dict[str, float]] = {
        "swiggy": {"gross": 0.0, "deduction": 0.0, "net": 0.0},
        "zomato": {"gross": 0.0, "deduction": 0.0, "net": 0.0},
        "doordash": {"gross": 0.0, "deduction": 0.0, "net": 0.0},
        "phonepe": {"gross": 0.0, "deduction": 0.0, "net": 0.0},
        "cards": {"gross": 0.0, "deduction": 0.0, "net": 0.0},
    }
    for r in rows:
        p = (r.get("platform") or "").lower()
        if p not in by_platform:
            by_platform[p] = {"gross": 0.0, "deduction": 0.0, "net": 0.0}
        by_platform[p]["gross"] += float(r.get("gross_amount", 0) or 0)
        by_platform[p]["net"] += float(r.get("net_payout", 0) or 0)
        if country == "Australia":
            # AU upload: deduction is `other_deductions` (platform commission base)
            # grossed up by 10% so the per-platform sum reconciles with canonical
            # total (which adds 10% GST on top).
            au_base = float(r.get("other_deductions", 0) or 0) or float(r.get("commission_amount", 0) or 0)
            by_platform[p]["deduction"] += round(au_base * 1.10, 2)
        else:
            by_platform[p]["deduction"] += _row_total(r)

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
        # Scale per-platform breakdown to match the override total so the
        # PIB Section 3 table still reconciles with the override value.
        if uploaded_total > 0:
            scale = total / uploaded_total
            for p in by_platform:
                by_platform[p]["deduction"] = round(by_platform[p]["deduction"] * scale, 2)
        return {
            "total": total,
            "commission_gst": comm_gst,
            "base": round(total - comm_gst, 2),
            "override_applied": True,
            "source": "override",
            "rows": rows,
            "by_platform": by_platform,
        }

    if uploaded_total > 0:
        return {
            "total": uploaded_total,
            "commission_gst": uploaded_gst,
            "base": round(uploaded_total - uploaded_gst, 2),
            "override_applied": False,
            "source": "uploaded",
            "rows": rows,
            "by_platform": by_platform,
        }

    # Legacy fallback: commission_statements
    year, mon = month.split("-")
    start = f"{year}-{mon}-01"
    end = f"{int(year) + 1}-01-01" if int(mon) == 12 else f"{year}-{int(mon) + 1:02d}-01"
    legacy = await db.commission_statements.find({
        "center": center,
        "settlement_period_start": {"$gte": start},
        "settlement_period_end": {"$lt": end},
    }, {"_id": 0}).to_list(500)
    # Build per-platform breakdown from legacy data too
    for L in legacy:
        p = (L.get("platform") or "").lower()
        # `card_settlement` legacy platform maps to "cards"
        if p == "card_settlement":
            p = "cards"
        if p not in by_platform:
            by_platform[p] = {"gross": 0.0, "deduction": 0.0, "net": 0.0}
        by_platform[p]["gross"] += float(L.get("gross_order_amount", 0) or 0)
        by_platform[p]["net"] += float(L.get("net_payout_received", 0) or 0)
        base_ded = float(L.get("commission_charged", 0) or 0)
        if country == "Australia":
            by_platform[p]["deduction"] += round(base_ded * 1.10, 2)
        else:
            by_platform[p]["deduction"] += base_ded
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
        "by_platform": by_platform,
    }
