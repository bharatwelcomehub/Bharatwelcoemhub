"""Payout Release Status helper — Feb-2026 owner directive.

Does NOT change any calculations. Just classifies whether the calculated
payout amount is currently approved for release.

Sources (priority order):
  1. Manual override stored in `center_settings.payout_release_status`
     Values: 'eligible' | 'review' | 'blocked' | 'auto'
     `auto` (default) falls through to step 2.
  2. Working Capital Protection Mode — if active for this center+month,
     status = 'blocked' with reason "WC Protection Mode active".
  3. Default = 'eligible'.

Returns:
    {
      "status": "eligible" | "review" | "blocked",
      "label": "Eligible For Release" | ...,
      "reason": short string,
      "color": "green" | "amber" | "red",
      "narrative": longer paragraph (for PDF/UI banner body),
      "source": "manual" | "auto_wc_protection" | "default",
      "override_active": bool,
    }
"""
from typing import Optional, Dict, Any


STATUS_LABELS = {
    "eligible": ("Eligible For Release", "green",
                 "The franchise owner payout has been approved and is eligible "
                 "for release as per current settlement rules."),
    "review": ("Management Review Required", "amber",
               "The franchise owner payout has been calculated correctly. "
               "However, final release is pending review by Accounts/Admin."),
    "blocked": ("Currently Blocked", "red",
                "The franchise owner payout has been calculated correctly for "
                "reporting purposes. However, payout release is currently "
                "blocked due to Working Capital Protection Mode, settlement "
                "review, adjustment requirements, contractual obligations or "
                "management decision. The displayed payout amount is "
                "informational only and does not represent an approved "
                "payment release."),
}


async def derive_payout_release_status(db, center: str, month: str,
                                       protection_mode: bool = False) -> Dict[str, Any]:
    """Compute the banner status. Reads optional center_settings override."""
    override = None
    try:
        # Per-month override (rare); falls back to per-center default
        s_month = await db.center_settings.find_one(
            {"center": center, "month": month, "key": "payout_release_status"},
            {"_id": 0, "value": 1},
        )
        if s_month and s_month.get("value"):
            override = s_month["value"]
        else:
            s_default = await db.center_settings.find_one(
                {"center": center, "key": "payout_release_status"},
                {"_id": 0, "value": 1},
            )
            if s_default and s_default.get("value"):
                override = s_default["value"]
    except Exception:
        override = None

    # Manual override wins (unless it's 'auto')
    if override and override in ("eligible", "review", "blocked"):
        label, color, narrative = STATUS_LABELS[override]
        return {
            "status": override,
            "label": label,
            "color": color,
            "narrative": narrative,
            "reason": "Set by Accounts/Admin",
            "source": "manual",
            "override_active": True,
        }

    # Auto: WC Protection Mode blocks release
    if protection_mode:
        label, color, narrative = STATUS_LABELS["blocked"]
        return {
            "status": "blocked",
            "label": label,
            "color": color,
            "narrative": narrative,
            "reason": "Working Capital Protection Mode active",
            "source": "auto_wc_protection",
            "override_active": False,
        }

    # Default — eligible
    label, color, narrative = STATUS_LABELS["eligible"]
    return {
        "status": "eligible",
        "label": label,
        "color": color,
        "narrative": narrative,
        "reason": "Default — no blockers",
        "source": "default",
        "override_active": False,
    }


async def set_payout_release_status(db, center: str, value: str,
                                    actor: str, month: Optional[str] = None) -> Dict[str, Any]:
    """Persist the manual override. value ∈ {eligible, review, blocked, auto}."""
    from datetime import datetime, timezone
    if value not in ("eligible", "review", "blocked", "auto"):
        return {"success": False, "detail": "Invalid value"}
    filt: Dict[str, Any] = {"center": center, "key": "payout_release_status"}
    if month:
        filt["month"] = month
    now_iso = datetime.now(timezone.utc).isoformat()
    if value == "auto":
        # Removing the override returns center to automatic logic
        await db.center_settings.delete_many(filt)
        await db.center_settings.insert_one({
            **filt, "value": "auto",
            "updated_by": actor, "updated_at": now_iso,
        })
        return {"success": True, "applied": "auto", "scope": "month" if month else "default"}
    await db.center_settings.update_one(
        filt,
        {"$set": {"value": value, "updated_by": actor, "updated_at": now_iso}},
        upsert=True,
    )
    return {"success": True, "applied": value, "scope": "month" if month else "default"}
