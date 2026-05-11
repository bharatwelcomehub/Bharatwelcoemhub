"""Overseas (non-India) profit-share & MFPL royalty — single source of truth.

Used by every surface that displays overseas franchise economics:
  - Center Accounts (summary endpoint + MG&Payout tab)
  - Owner Reports (PIB)
  - Ledgers (Franchise Owner ledger PDF)
  - MIS Dashboard
  - Bundle / Center PDFs

Rules (per user spec, Feb-2026):
  - **No Minimum Guarantee** (MG) for overseas centers.
  - **Eligible Profit** = Sales − GST − Commission − Commission GST − Expenses
        (this is the existing `profitability` figure for AU; canonical).
  - **Profit Share split**:
        Franchise Owner    = 80% × Eligible Profit
        Purnabramha LLC    = 20% × Eligible Profit
  - **MFPL Royalty (accrued liability)**:
        Eligible Revenue = Net Sales = Sales − GST on Sales
        MFPL Royalty     = 5% × Eligible Revenue
        Currently NOT paid out → accrued as a payable liability of the center.

The cumulative MFPL liability is computed by summing the per-month royalty
across every month the center has activity (from `daily_sales`).
"""

from typing import Dict, Any, Optional

# Constants
OWNER_PCT = 80.0
FRANCHISOR_PCT = 20.0
MFPL_ROYALTY_PCT = 5.0


def is_overseas(country: Optional[str]) -> bool:
    """A center is overseas if its country is anything other than India."""
    return bool(country) and country.strip().lower() != "india"


def compute_overseas_share(eligible_profit: float, net_sales: float) -> Dict[str, Any]:
    """Compute the canonical overseas distribution for one month.

    Args:
        eligible_profit: Sales − GST − Commission − CommGST − Expenses
        net_sales: Sales − GST (i.e. eligible revenue for royalty)

    Returns dict with: owner_share, franchisor_share, mfpl_royalty, ratios.
    """
    ep = max(0.0, float(eligible_profit or 0))
    ns = max(0.0, float(net_sales or 0))
    owner = round(ep * OWNER_PCT / 100.0, 2)
    franchisor = round(ep * FRANCHISOR_PCT / 100.0, 2)
    mfpl = round(ns * MFPL_ROYALTY_PCT / 100.0, 2)
    return {
        "eligible_profit": round(ep, 2),
        "eligible_revenue": round(ns, 2),
        "owner_share": owner,
        "franchisor_share": franchisor,
        "owner_pct": OWNER_PCT,
        "franchisor_pct": FRANCHISOR_PCT,
        "mfpl_royalty": mfpl,
        "mfpl_royalty_pct": MFPL_ROYALTY_PCT,
    }


async def compute_cumulative_mfpl(db, center_code: str, up_to_month: Optional[str] = None) -> Dict[str, Any]:
    """Sum the accrued MFPL royalty liability for an overseas center up to a month (inclusive).

    Walks every month that has daily_sales entries for the center, computes
    per-month net sales (sales − GST), applies 5%, and accumulates.

    Args:
        db: Mongo database handle.
        center_code: center code (e.g. "PB-MGT").
        up_to_month: "YYYY-MM" upper bound (inclusive). None ⇒ all-time.

    Returns:
        { "monthly": [ {"month": "2026-01", "net_sales": ..., "mfpl": ...}, ... ],
          "cumulative_mfpl": <float>, "cumulative_net_sales": <float>,
          "paid_mfpl": 0.0, "outstanding_mfpl": <float> }
    """
    from utils.gst import compute_gst_from_rows

    # Get the center country to verify
    center = await db.centers.find_one({"code": center_code}, {"_id": 0})
    country = (center.get("country") if center else None) or "India"
    if not is_overseas(country):
        return {
            "monthly": [], "cumulative_mfpl": 0.0, "cumulative_net_sales": 0.0,
            "paid_mfpl": 0.0, "outstanding_mfpl": 0.0,
            "applicable": False,
        }

    # Pull all daily_sales rows for this center
    cursor = db.daily_sales.find({"center": center_code}, {"_id": 0})
    rows_by_month: Dict[str, list] = {}
    async for r in cursor:
        d = (r.get("date") or "")[:7]
        if not d:
            continue
        if up_to_month and d > up_to_month:
            continue
        rows_by_month.setdefault(d, []).append(r)

    monthly = []
    cum_mfpl = 0.0
    cum_net = 0.0
    for m in sorted(rows_by_month.keys()):
        rows = rows_by_month[m]
        total_sales = sum(float(r.get("total_sale") or 0) for r in rows)
        gst_calc = compute_gst_from_rows(rows, country=country, center=center_code)
        gst_amt = float(gst_calc.get("gst_amount") or 0)
        net_sales = max(0.0, total_sales - gst_amt)
        mfpl = round(net_sales * MFPL_ROYALTY_PCT / 100.0, 2)
        cum_net += net_sales
        cum_mfpl += mfpl
        monthly.append({
            "month": m,
            "net_sales": round(net_sales, 2),
            "mfpl": mfpl,
        })

    # Future: subtract any MFPL payments tracked in a dedicated collection
    paid = 0.0
    outstanding = round(cum_mfpl - paid, 2)

    return {
        "monthly": monthly,
        "cumulative_mfpl": round(cum_mfpl, 2),
        "cumulative_net_sales": round(cum_net, 2),
        "paid_mfpl": round(paid, 2),
        "outstanding_mfpl": outstanding,
        "applicable": True,
        "pct": MFPL_ROYALTY_PCT,
    }
