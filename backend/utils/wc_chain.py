"""Canonical Working Capital chain — single source of truth.

This module is the sole place where the cumulative Working Capital chain
is computed. Both `calculate_working_capital_standing` (used by the WC
Status card, MIS Dashboard, FO Dashboard) and `get_wc_table` (used by the
WC Breakdown table) MUST call `compute_wc_chain()` so they cannot drift.

The chain semantics — these are the AUTHORITATIVE rules:

    For each month M in chronological order:
        opening_wc[M]  = closing_wc[M-1]   (or base_wc for the first month)
        pnl[M]         = sale[M] - expenses[M] - commission[M]
                         (GST is M+1 expense, NOT subtracted from M's P/L)
        closing_wc[M]  = opening_wc[M] + pnl[M] + wc_adjustment[M]
                         + topup[M]
                         (Other Income is MEMO-ONLY — NOT added to chain.
                          A loan taken is a liability, not real WC; auto-tagged
                          loan_taken entries on db.other_income would otherwise
                          mask negative WC as "Healthy".)

Override semantics:
    * `commission_target` (per-month wc_overrides): replaces the source
      commission for the month, affects pnl.
    * `gst_target`: tracked for display only; never subtracted from pnl.
    * `wc_adjustment`: explicit manual delta added to the chain.
    * `expense_adjustment`: audit-trail only (real expense row already
      exists in db.expenses), MUST NOT be added a second time.

The function returns a list of row dicts with all intermediate values so
both callers (status card + breakdown table) can pull whatever fields
they need without recomputing.
"""

from typing import Dict, List, Optional


async def compute_wc_chain(
    db,
    *,
    center: str,
    base_wc: float,
    sales_by_month: Dict[str, float],
    expenses_by_month: Dict[str, float],
    commission_by_month: Dict[str, float],
    gst_by_month: Dict[str, float],
    overrides_by_month: Dict[str, dict],
    topups_by_month: Dict[str, float],
    other_income_by_month: Dict[str, float],
    months_to_process: List[str],
    up_to_month: Optional[str] = None,
) -> dict:
    """Run the canonical WC chain.

    Args:
        months_to_process: ALL months that should be in the chain, in
            chronological order. The chain accumulates strictly through
            this list; pass only months <= effective_franchise_end.
        up_to_month: highlight this month's row in `target_row`.

    Returns:
        {
            "rows": [...],              # one entry per month in months_to_process
            "final_closing_wc": float,  # closing_wc of the last month
            "target_row": dict | None,  # row matching up_to_month (or None)
            "cumulative_wc_used": float,
            "cumulative_wc_restored": float,
        }

    Raises:
        Nothing — defensively coerces missing data to 0.0.
    """
    rows: List[dict] = []
    running = float(base_wc)
    cum_used = 0.0
    cum_restored = 0.0
    target_row: Optional[dict] = None

    for month in months_to_process:
        opening_wc = running

        sale = float(sales_by_month.get(month, 0) or 0)
        expenses_db = float(expenses_by_month.get(month, 0) or 0)
        commission_src = float(commission_by_month.get(month, 0) or 0)
        gst_src = float(gst_by_month.get(month, 0) or 0)

        ov = overrides_by_month.get(month, {}) or {}
        commission = (
            float(ov["commission_target"])
            if ov.get("commission_target") is not None
            else commission_src
        )
        gst = float(ov["gst_target"]) if ov.get("gst_target") is not None else gst_src
        wc_adj = float(ov.get("wc_adjustment", 0) or 0)
        # expense_adjustment is audit-trail only; the real expense row already
        # lives in db.expenses, do NOT subtract again.
        expense_adj = float(ov.get("expense_adjustment", 0) or 0)
        expenses_real = expenses_db - expense_adj  # informational

        pnl = sale - expenses_db - commission

        topup = float(topups_by_month.get(month, 0) or 0)
        oi = float(other_income_by_month.get(month, 0) or 0)

        # Other Income (esp. auto-tagged "loan_taken") is intentionally NOT
        # added to closing_wc. A loan is a liability, not real working capital.
        # Adding it would mask a negative WC as "Healthy" (e.g. base 9L, P/L
        # cumulative -46L, loan taken 16L → false 'Healthy 216%' instead of
        # true 'Critical -413%'). Surface it on the dashboard as memo only.
        closing_wc = opening_wc + pnl + wc_adj + topup

        # WC used / restored counters (used by Status card)
        month_used = abs(pnl) if pnl < 0 else 0.0
        month_restored = 0.0
        if pnl > 0 and opening_wc < base_wc:
            month_restored = min(pnl, base_wc - opening_wc)
        cum_used += month_used
        cum_restored += month_restored

        row = {
            "month": month,
            "sale": round(sale, 2),
            "expenses": round(expenses_db, 2),
            "expenses_db": round(expenses_real, 2),
            "expense_adjustment": round(expense_adj, 2),
            "commission": round(commission, 2),
            "commission_source": round(commission_src, 2),
            "gst": round(gst, 2),
            "pnl": round(pnl, 2),
            "operational_balance": round(pnl, 2),
            "opening_wc": round(opening_wc, 2),
            "wc_adjustment": round(wc_adj, 2),
            "topup": round(topup, 2),
            "other_income": round(oi, 2),
            "balance_wc": round(closing_wc, 2),
            "closing_wc": round(closing_wc, 2),
            "wc_used": round(month_used, 2),
            "wc_restored": round(month_restored, 2),
        }
        rows.append(row)
        if up_to_month and month == up_to_month:
            target_row = row

        running = closing_wc

    return {
        "rows": rows,
        "final_closing_wc": round(running, 2),
        "target_row": target_row,
        "cumulative_wc_used": round(cum_used, 2),
        "cumulative_wc_restored": round(cum_restored, 2),
    }
