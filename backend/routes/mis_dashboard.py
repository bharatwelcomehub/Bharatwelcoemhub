# =======================================
# MIS Dashboard Routes
# Centralized analytics for sales, expenses, and alerts
# =======================================

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
import logging
import io
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mis", tags=["MIS Dashboard"])

# Get DB reference (will be set from main server)
db = None
verify_token = None
verify_token_async_func = None

def set_db(database):
    global db
    db = database

def set_verify_token(func):
    global verify_token
    verify_token = func

def set_verify_token_async(func):
    global verify_token_async_func
    verify_token_async_func = func

# =======================================
# ACCESS CHECK
# =======================================

async def fetch_wc_overrides(center, start_date, end_date):
    """Fetch wc_month_overrides for a center (or all centers if 'all') within a
    date range. Returns a dict: {(center, month): {'commission_target': ..., 'gst_target': ...}}
    Used by MIS/Franchise dashboards so that commission & GST overrides entered
    in the WC table (Center Accounts) flow through to the dashboard summaries.
    """
    # Derive month set from date range
    from datetime import datetime as _dt
    months = set()
    try:
        s = _dt.strptime(start_date, "%Y-%m-%d").replace(day=1)
        e = _dt.strptime(end_date, "%Y-%m-%d")
        cur = s
        while cur <= e:
            months.add(cur.strftime("%Y-%m"))
            if cur.month == 12:
                cur = cur.replace(year=cur.year + 1, month=1)
            else:
                cur = cur.replace(month=cur.month + 1)
    except Exception:
        return {}
    
    q = {"month": {"$in": list(months)}}
    if center and center != "all":
        q["center"] = center
    docs = await db.wc_month_overrides.find(q, {"_id": 0}).to_list(2000)
    result = {}
    for d in docs:
        key = (d.get("center", ""), d.get("month", ""))
        result[key] = {
            "commission_target": d.get("commission_target"),
            "gst_target": d.get("gst_target"),
        }
    return result


async def check_mis_access(token: str) -> dict:
    """Check if user has MIS Dashboard access (Super Admin, Admin, Accounts, or Franchise Owner)"""
    # Try async verification first (checks MongoDB)
    session = None
    if verify_token_async_func:
        session = await verify_token_async_func(token)
    if not session:
        session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    is_super_admin = session.get("is_super_admin", False)
    is_admin = session.get("is_admin", False)
    roles = session.get("roles", {})
    has_accounting = roles.get("accounting", False)
    is_franchise_owner = session.get("role_key") == "franchise_owner"
    has_franchise_role = roles.get("franchise", False)
    
    if not (is_super_admin or is_admin or has_accounting or is_franchise_owner or has_franchise_role):
        raise HTTPException(403, "Only Admin, Accounts, or Franchise Owner users can access MIS Dashboard")
    
    return session

# =======================================
# HELPER FUNCTIONS
# =======================================

def get_period_dates(period: str, custom_start: str = None, custom_end: str = None):
    """Get start and end dates based on period selection"""
    today = datetime.now()
    
    if period == "current_month":
        start = today.replace(day=1)
        end = today
    elif period == "last_month":
        last = today.replace(day=1) - timedelta(days=1)
        start = last.replace(day=1)
        end = last
    elif period == "last_6_months":
        start = today - relativedelta(months=6)
        end = today
    elif period == "current_quarter":
        quarter = (today.month - 1) // 3
        start = today.replace(month=quarter * 3 + 1, day=1)
        end = today
    elif period == "last_3_months":
        start = today - relativedelta(months=3)
        end = today
    elif period == "ytd":
        start = today.replace(month=1, day=1)
        end = today
    elif period == "last_quarter":
        quarter = (today.month - 1) // 3
        if quarter == 0:
            start = today.replace(year=today.year - 1, month=10, day=1)
            end = today.replace(year=today.year - 1, month=12, day=31)
        else:
            start = today.replace(month=(quarter - 1) * 3 + 1, day=1)
            end = today.replace(month=quarter * 3, day=1) - timedelta(days=1)
    elif period == "custom" and custom_start and custom_end:
        start = datetime.strptime(custom_start, "%Y-%m-%d")
        end = datetime.strptime(custom_end, "%Y-%m-%d")
    else:
        # Default to current month
        start = today.replace(day=1)
        end = today
    
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

def get_previous_period_dates(period: str, start_date: str, end_date: str):
    """Get previous period dates for comparison"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    duration = (end - start).days + 1
    
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=duration - 1)
    
    return prev_start.strftime("%Y-%m-%d"), prev_end.strftime("%Y-%m-%d")

# =======================================
# DASHBOARD OVERVIEW ENDPOINT
# =======================================

@router.post("/overview")
async def get_mis_overview(data: dict):
    """Get MIS Dashboard overview with all key metrics"""
    token = data.get("token")
    period = data.get("period", "current_month")
    center = data.get("center", "all")  # "all" or specific center code
    custom_start = data.get("custom_start")
    custom_end = data.get("custom_end")
    
    session = await check_mis_access(token)
    
    # Get period dates
    start_date, end_date = get_period_dates(period, custom_start, custom_end)
    prev_start, prev_end = get_previous_period_dates(period, start_date, end_date)
    
    # Build query
    query = {"date": {"$gte": start_date, "$lte": end_date}}
    prev_query = {"date": {"$gte": prev_start, "$lte": prev_end}}
    
    if center != "all":
        query["center"] = center
        prev_query["center"] = center
    
    # Fetch sales data
    sales_data = await db.daily_sales.find(query, {"_id": 0}).to_list(10000)
    prev_sales_data = await db.daily_sales.find(prev_query, {"_id": 0}).to_list(10000)
    
    # Fetch expenses data
    expenses_data = await db.expenses.find(query, {"_id": 0}).to_list(10000)
    prev_expenses_data = await db.expenses.find(prev_query, {"_id": 0}).to_list(10000)
    
    # Calculate totals - Current Period
    total_sales = sum(float(s.get("total_sale", 0) or 0) for s in sales_data)
    total_cash_sales = sum(float(s.get("total_cash_sale", 0) or 0) for s in sales_data)
    total_online_sales = sum(float(s.get("total_online_sale", 0) or 0) for s in sales_data)
    total_guests = sum(int(s.get("num_guests", 0) or 0) for s in sales_data)
    total_bills = sum(int(s.get("num_bills", 0) or 0) for s in sales_data)
    
    # GST using eligible-sales formula: (total_sale - swiggy - zomato - doordash) * rate
    # India: 5%, Perth/outside-India: 10%. This replaces the legacy sum of
    # daily_sales.gst_amount which incorrectly treated GST as % of gross.
    from utils.gst import compute_gst_from_rows
    _gst_calc = compute_gst_from_rows(sales_data, country=None, center=(center if center and center != "all" else None))
    total_gst = _gst_calc["gst_amount"]
    # Legacy field still available as _gst_calc["stored_gst_sum"] if ever needed
    
    # Merge PIB-derived GST (from monthly Excel imports): adds SGST+CGST for
    # months where the daily_sales don't already carry gst_amount. Scoped by
    # center + month range.
    try:
        from datetime import datetime as _dt2
        _s2 = _dt2.strptime(start_date, "%Y-%m-%d").replace(day=1)
        _e2 = _dt2.strptime(end_date, "%Y-%m-%d")
        _ms2 = []
        _cur2 = _s2
        while _cur2 <= _e2:
            _ms2.append(_cur2.strftime("%Y-%m"))
            _cur2 = _cur2.replace(year=_cur2.year + 1, month=1) if _cur2.month == 12 else _cur2.replace(month=_cur2.month + 1)
        _pq = {"month": {"$in": _ms2}}
        if center and center != "all":
            _pq["center"] = center
        pib_rows = await db.historical_pib.find(_pq, {"_id": 0}).to_list(1000)
        # Live-data dedupe: a month is "covered by live data" whenever the
        # daily_sales rows for that (center, month) have ANY eligible base —
        # because compute_gst_from_rows() already carved 5%/10% inclusive GST
        # out of those rows. The legacy `gst_amount > 0` check missed this,
        # which double-counted GST for centers that don't manually store
        # gst_amount on each row (e.g. PB-DV April 2026: live formula = ₹46,133
        # AND historical_pib added another ₹9,851 → ₹55,984 wrong total).
        live_gst_months: set = set()
        for s in sales_data:
            cm = (s.get("center", ""), (s.get("date") or "")[:7])
            base = (
                float(s.get("total_sale", 0) or 0)
                - float(s.get("swiggy_sale", s.get("swiggy", 0)) or 0)
                - float(s.get("zomato_sale", s.get("zomato", 0)) or 0)
                - float(s.get("doordash_sale", s.get("doordash", 0)) or 0)
            )
            if base > 0 or float(s.get("gst_amount", 0) or 0) > 0:
                live_gst_months.add(cm)
        pib_gst_add = 0.0
        pib_gst_by_center: dict = {}
        for p in pib_rows:
            key = (p.get("center", ""), p.get("month", ""))
            if key in live_gst_months:
                continue
            g = float(p.get("total_gst_on_revenue", 0) or 0)
            if g <= 0:
                continue
            pib_gst_add += g
            pib_gst_by_center[p.get("center", "")] = pib_gst_by_center.get(p.get("center", ""), 0) + g
        total_gst = round(total_gst + pib_gst_add, 2)
    except Exception as pgx:
        logger.warning(f"MIS: PIB GST merge failed: {pgx}")
        pib_gst_by_center = {}
    
    # Expenses
    total_expenses = sum(float(e.get("amount", 0) or 0) for e in expenses_data)
    
    # Historical monthly summary merge — fills months that have no live daily
    # data from imported Excel rollups. Scoped by center (if center != "all")
    # and the date range's months. Does NOT overwrite live data.
    try:
        from datetime import datetime as _dt
        _s = _dt.strptime(start_date, "%Y-%m-%d").replace(day=1)
        _e = _dt.strptime(end_date, "%Y-%m-%d")
        _ms = set()
        _cur = _s
        while _cur <= _e:
            _ms.add(_cur.strftime("%Y-%m"))
            _cur = _cur.replace(year=_cur.year + 1, month=1) if _cur.month == 12 else _cur.replace(month=_cur.month + 1)
        # Live-month set per (center, month): any row with non-zero sale/expense
        _live = set()
        for s in sales_data:
            _c = s.get("center", "")
            _m = (s.get("date") or "")[:7]
            if _c and _m and (float(s.get("total_sale", 0) or 0) > 0):
                _live.add((_c, _m))
        for e in expenses_data:
            _c = e.get("center", "")
            _m = (e.get("date") or "")[:7]
            if _c and _m and (float(e.get("amount", 0) or 0) > 0):
                _live.add((_c, _m))
        _q = {"month": {"$in": list(_ms)}}
        if center and center != "all":
            _q["center"] = center
        _hist = await db.historical_monthly_summary.find(_q, {"_id": 0}).to_list(5000)
        hist_sale_add = 0.0
        hist_exp_add = 0.0
        hist_by_center: dict = {}
        for h in _hist:
            key = (h.get("center", ""), h.get("month", ""))
            if key in _live:
                continue
            s_v = float(h.get("sale", 0) or 0)
            e_v = float(h.get("expenses", 0) or 0)
            hist_sale_add += s_v
            hist_exp_add += e_v
            cc = h.get("center", "")
            hist_by_center.setdefault(cc, {"sale": 0, "expenses": 0})
            hist_by_center[cc]["sale"] += s_v
            hist_by_center[cc]["expenses"] += e_v
        total_sales += hist_sale_add
        total_expenses += hist_exp_add
    except Exception as hx:
        logger.warning(f"MIS: historical merge failed: {hx}")
        hist_by_center = {}
    
    # Commission calculation (from monthly_commissions uploads)
    total_commissions = 0.0
    try:
        # Derive month strings from the period
        from datetime import datetime as dt_cls
        period_start = dt_cls.strptime(start_date, "%Y-%m-%d")
        period_end = dt_cls.strptime(end_date, "%Y-%m-%d")
        # Collect all months in the range
        months_in_range = set()
        cur = period_start.replace(day=1)
        while cur <= period_end:
            months_in_range.add(cur.strftime("%Y-%m"))
            if cur.month == 12:
                cur = cur.replace(year=cur.year + 1, month=1)
            else:
                cur = cur.replace(month=cur.month + 1)

        if center != "all":
            comm_records = await db.monthly_commissions.find(
                {"center": center, "month": {"$in": list(months_in_range)}},
                {"_id": 0, "center": 1, "gst_tax_deductions": 1, "other_deductions": 1, "commission_amount": 1, "gst_on_commission": 1},
            ).to_list(500)
            total_commissions = sum(
                r.get("gst_tax_deductions", 0) + r.get("other_deductions", 0)
                or (r.get("commission_amount", 0) + r.get("gst_on_commission", 0))
                for r in comm_records
            )
        else:
            comm_records = await db.monthly_commissions.find(
                {"month": {"$in": list(months_in_range)}},
                {"_id": 0, "center": 1, "gst_tax_deductions": 1, "other_deductions": 1, "commission_amount": 1, "gst_on_commission": 1},
            ).to_list(5000)
            total_commissions = sum(
                r.get("gst_tax_deductions", 0) + r.get("other_deductions", 0)
                or (r.get("commission_amount", 0) + r.get("gst_on_commission", 0))
                for r in comm_records
            )
        total_commissions = round(total_commissions, 2)
    except Exception as comm_err:
        logger.warning(f"MIS: commission calc failed: {comm_err}")
    
    # Apply WC table overrides (commission_target only) so Commission summaries
    # match the Center Accounts WC table. GST is intentionally NOT overridable
    # — it must always equal the formula `eligible_base × rate / (1+rate)` so
    # the dashboards stay byte-identical to the PIB / GST Summary report. A
    # legacy `gst_target` value stored against a (center, month) used to be
    # added on top of the formula here (because the source bucket read the
    # blank `gst_amount` field), causing PB-DV Apr-2026 to show ₹55,984.74 on
    # the dashboard while the GST Summary correctly showed ₹46,133.14.
    try:
        ov_map = await fetch_wc_overrides(center, start_date, end_date)
        # Per-month source aggregates (center, month) for the current period
        # so we can subtract the source value and add the override value.
        def _month_bucket(rows, value_key, center_key="center"):
            buckets = {}
            for r in rows:
                c = r.get(center_key, "") or ""
                d = r.get("date", "") or ""
                m = d[:7] if d else ""
                if not m:
                    continue
                buckets[(c, m)] = buckets.get((c, m), 0) + float(r.get(value_key, 0) or 0)
            return buckets

        # Commission source bucket: from comm_records grouped by (center, month)
        comm_src_buckets = {}
        try:
            for r in comm_records:
                cc = r.get("center", "") or ""
                mm = r.get("month", "") or ""
                if not mm:
                    continue
                v = (
                    r.get("gst_tax_deductions", 0) + r.get("other_deductions", 0)
                    or (r.get("commission_amount", 0) + r.get("gst_on_commission", 0))
                )
                comm_src_buckets[(cc, mm)] = comm_src_buckets.get((cc, mm), 0) + v
        except Exception:
            pass

        def _apply_commission_overrides(ov, comm_total, comm_buckets):
            new_comm = comm_total
            for (cc, mm), o in ov.items():
                ct = o.get("commission_target")
                if ct is not None:
                    new_comm = new_comm - comm_buckets.get((cc, mm), 0) + float(ct)
            return round(new_comm, 2)

        total_commissions = _apply_commission_overrides(
            ov_map, total_commissions, comm_src_buckets
        )
    except Exception as ov_err:
        logger.warning(f"MIS: WC override application failed: {ov_err}")
    
    # Net Revenue & Profit calculation (per user requirement Apr-2026):
    #   Net Revenue = Total Sale − Commissions − GST on Sale
    #   Profit (op) = Net Revenue − Expenses
    # GST is INCLUSIVE in receipt totals (carved out via shared utility),
    # and is treated as a govt pass-through, NOT center revenue.
    net_revenue = total_sales - total_commissions - total_gst
    profit = net_revenue - total_expenses
    profit_margin = round((profit / total_sales * 100) if total_sales > 0 else 0, 2)
    
    # Calculate totals - Previous Period
    prev_total_sales = sum(float(s.get("total_sale", 0) or 0) for s in prev_sales_data)
    prev_total_expenses = sum(float(e.get("amount", 0) or 0) for e in prev_expenses_data)
    prev_gst_calc = compute_gst_from_rows(prev_sales_data, country=None, center=(center if center and center != "all" else None))
    prev_gst = prev_gst_calc["gst_amount"]
    prev_net_revenue = prev_total_sales - prev_gst  # commissions assumed 0 for prev (matches existing baseline)
    prev_profit = prev_net_revenue - prev_total_expenses
    
    # Calculate changes
    def calc_change(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 2)
    
    sales_change = calc_change(total_sales, prev_total_sales)
    expenses_change = calc_change(total_expenses, prev_total_expenses)
    profit_change = calc_change(profit, prev_profit)
    
    # Center-wise breakdown
    centers_data = {}
    for s in sales_data:
        c = s.get("center", "Unknown")
        if c not in centers_data:
            centers_data[c] = {"sales": 0, "guests": 0, "bills": 0, "expenses": 0, "commissions": 0, "gst": 0, "_eligible_base": 0}
        centers_data[c]["sales"] += float(s.get("total_sale", 0) or 0)
        centers_data[c]["guests"] += int(s.get("num_guests", 0) or 0)
        centers_data[c]["bills"] += int(s.get("num_bills", 0) or 0)
        # Accumulate the eligible base (total - swiggy - zomato - doordash) per center;
        # GST applied in one go below using per-center rate.
        from utils.gst import eligible_base_from_daily_row as _eb
        centers_data[c]["_eligible_base"] = centers_data[c].get("_eligible_base", 0) + _eb(s)
    
    for e in expenses_data:
        c = e.get("center", "Unknown")
        if c not in centers_data:
            centers_data[c] = {"sales": 0, "guests": 0, "bills": 0, "expenses": 0, "commissions": 0, "gst": 0}
        centers_data[c]["expenses"] += float(e.get("amount", 0) or 0)
    
    # Inject historical (Excel-imported) totals per center — only for months
    # where this center has no live data (already filtered into hist_by_center).
    try:
        for cc, v in (hist_by_center or {}).items():
            if cc not in centers_data:
                centers_data[cc] = {"sales": 0, "guests": 0, "bills": 0, "expenses": 0, "commissions": 0, "gst": 0}
            centers_data[cc]["sales"] += v.get("sale", 0)
            centers_data[cc]["expenses"] += v.get("expenses", 0)
    except Exception:
        pass
    
    # Inject PIB-derived GST per center (when not already covered by live)
    try:
        for cc, g in (pib_gst_by_center or {}).items():
            if cc not in centers_data:
                centers_data[cc] = {"sales": 0, "guests": 0, "bills": 0, "expenses": 0, "commissions": 0, "gst": 0}
            centers_data[cc]["gst"] = round(centers_data[cc].get("gst", 0) + g, 2)
    except Exception:
        pass
    
    # Add commissions per center from monthly_commissions
    try:
        # Build center->commission map from the records we already fetched
        center_comm_map = {}
        for r in comm_records:
            cc = r.get("center", "")
            if cc:
                comm_val = (
                    r.get("gst_tax_deductions", 0) + r.get("other_deductions", 0)
                    or (r.get("commission_amount", 0) + r.get("gst_on_commission", 0))
                )
                center_comm_map[cc] = center_comm_map.get(cc, 0) + comm_val
        for c in centers_data:
            if c and c != "Unknown":
                centers_data[c]["commissions"] = round(center_comm_map.get(c, 0), 2)
    except Exception as comm_err:
        logger.error(f"MIS center commission calc failed: {comm_err}", exc_info=True)
    
    # Apply per-center GST using the SAME inclusive formula as the top-level
    # `total_gst` and the PIB / GST Summary report:
    #   gst = eligible_base − eligible_base / (1 + rate)
    # The previous `eligible × rate` was a non-inclusive 5% which gave
    # ₹48,439.80 instead of the correct ₹46,133.14 — a silent ₹2,306 over-
    # statement per center that broke parity with the rest of the dashboard.
    try:
        from utils.gst import gst_rate_for as _gst_rate_for, carve_inclusive_gst as _carve
        for cc, cd in centers_data.items():
            rate = _gst_rate_for(None, cc)
            cd["gst"] = _carve(cd.get("_eligible_base", 0), rate)
    except Exception:
        pass
    
    # Apply WC-table per-center overrides to centers_data — commissions only.
    # GST is intentionally NOT overridden here (formula is single source of
    # truth — see comment above on the global merge).
    try:
        for (cc, mm), o in ov_map.items():
            if cc not in centers_data:
                continue
            ct = o.get("commission_target")
            if ct is not None:
                centers_data[cc]["commissions"] = round(
                    centers_data[cc].get("commissions", 0) - comm_src_buckets.get((cc, mm), 0) + float(ct), 2
                )
    except Exception as ov2_err:
        logger.warning(f"MIS: per-center WC override application failed: {ov2_err}")
    
    # Calculate profit for each center
    for c in centers_data:
        center_sales = centers_data[c]["sales"]
        center_expenses = centers_data[c]["expenses"]
        center_gst = round(centers_data[c]["gst"], 2)
        center_comm = centers_data[c].get("commissions", 0)
        centers_data[c]["gst"] = center_gst
        centers_data[c]["profit"] = round(center_sales - center_expenses - center_gst - center_comm, 2)
        centers_data[c]["profit_margin"] = round(
            (centers_data[c]["profit"] / center_sales * 100) if center_sales > 0 else 0, 2
        )
    
    # Sort centers by sales
    centers_list = [
        {"center": c, **data} 
        for c, data in sorted(centers_data.items(), key=lambda x: x[1]["sales"], reverse=True)
    ]
    
    # Earliest-available data across all sources (live + historical imports).
    # Used by frontend to show "Data available from {month} onwards" banner
    # when the user picks a date range before any data exists.
    earliest_month = None
    try:
        _q = {"center": center} if center and center != "all" else {}
        # Scan min(date) across daily_sales + historical_monthly_summary + historical_trial_balance
        candidates = []
        ds_min = await db.daily_sales.find(_q, {"date": 1, "_id": 0}).sort("date", 1).limit(1).to_list(1)
        if ds_min and ds_min[0].get("date"):
            candidates.append(str(ds_min[0]["date"])[:7])
        hq = {"center": center} if center and center != "all" else {}
        h_min = await db.historical_monthly_summary.find(hq, {"month": 1, "_id": 0}).sort("month", 1).limit(1).to_list(1)
        if h_min and h_min[0].get("month"):
            candidates.append(h_min[0]["month"])
        tb_min = await db.historical_trial_balance.find(hq, {"month": 1, "_id": 0}).sort("month", 1).limit(1).to_list(1)
        if tb_min and tb_min[0].get("month"):
            candidates.append(tb_min[0]["month"])
        if candidates:
            earliest_month = min(candidates)
    except Exception:
        pass
    has_any_data = (total_sales > 0) or (total_expenses > 0)
    
    return {
        "period": {
            "type": period,
            "start": start_date,
            "end": end_date,
            "prev_start": prev_start,
            "prev_end": prev_end
        },
        "data_availability": {
            "has_data_in_range": bool(has_any_data),
            "earliest_month": earliest_month,
        },
        "summary": {
            "total_sales": round(total_sales, 2),
            "total_cash_sales": round(total_cash_sales, 2),
            "total_online_sales": round(total_online_sales, 2),
            "total_expenses": round(total_expenses, 2),
            "total_gst": total_gst,
            "total_commissions": total_commissions,
            "total_deductions": round(total_commissions + total_gst, 2),
            "net_revenue": round(net_revenue, 2),
            "profit": round(profit, 2),
            "profit_margin": profit_margin,
            "total_guests": total_guests,
            "total_bills": total_bills,
            "avg_per_guest": round(total_sales / total_guests, 2) if total_guests > 0 else 0,
            "avg_per_bill": round(total_sales / total_bills, 2) if total_bills > 0 else 0
        },
        "changes": {
            "sales_change": sales_change,
            "expenses_change": expenses_change,
            "profit_change": profit_change
        },
        "previous_period": {
            "total_sales": round(prev_total_sales, 2),
            "total_expenses": round(prev_total_expenses, 2),
            "profit": round(prev_profit, 2)
        },
        "centers": centers_list,
        "record_counts": {
            "sales_records": len(sales_data),
            "expense_records": len(expenses_data)
        }
    }

# =======================================
# SALES TRENDS ENDPOINT
# =======================================

@router.post("/sales-trends")
async def get_sales_trends(data: dict):
    """Get daily/weekly sales trends for charts"""
    token = data.get("token")
    period = data.get("period", "current_month")
    center = data.get("center", "all")
    group_by = data.get("group_by", "daily")  # daily, weekly, monthly
    custom_start = data.get("custom_start")
    custom_end = data.get("custom_end")
    
    session = await check_mis_access(token)
    
    start_date, end_date = get_period_dates(period, custom_start, custom_end)
    
    query = {"date": {"$gte": start_date, "$lte": end_date}}
    if center != "all":
        query["center"] = center
    
    sales_data = await db.daily_sales.find(query, {"_id": 0}).to_list(10000)
    
    # Group data by date
    if group_by == "daily":
        grouped = {}
        for s in sales_data:
            date = s.get("date", "")
            if date not in grouped:
                grouped[date] = {"date": date, "sales": 0, "expenses": 0, "guests": 0, "gst": 0}
            grouped[date]["sales"] += float(s.get("total_sale", 0) or 0)
            grouped[date]["guests"] += int(s.get("num_guests", 0) or 0)
            grouped[date]["gst"] += float(s.get("gst_amount", 0) or 0)
        
        # Get expenses for same dates
        expenses_data = await db.expenses.find(query, {"_id": 0}).to_list(10000)
        for e in expenses_data:
            date = e.get("date", "")
            if date in grouped:
                grouped[date]["expenses"] += float(e.get("amount", 0) or 0)
        
        trends = sorted(grouped.values(), key=lambda x: x["date"])
    
    elif group_by == "weekly":
        grouped = {}
        for s in sales_data:
            date = datetime.strptime(s.get("date", "2025-01-01"), "%Y-%m-%d")
            week_start = (date - timedelta(days=date.weekday())).strftime("%Y-%m-%d")
            if week_start not in grouped:
                grouped[week_start] = {"week": week_start, "sales": 0, "expenses": 0, "gst": 0}
            grouped[week_start]["sales"] += float(s.get("total_sale", 0) or 0)
            grouped[week_start]["gst"] += float(s.get("gst_amount", 0) or 0)
        
        expenses_data = await db.expenses.find(query, {"_id": 0}).to_list(10000)
        for e in expenses_data:
            date = datetime.strptime(e.get("date", "2025-01-01"), "%Y-%m-%d")
            week_start = (date - timedelta(days=date.weekday())).strftime("%Y-%m-%d")
            if week_start in grouped:
                grouped[week_start]["expenses"] += float(e.get("amount", 0) or 0)
        
        trends = sorted(grouped.values(), key=lambda x: x["week"])
    
    else:  # monthly
        grouped = {}
        for s in sales_data:
            month = s.get("date", "2025-01-01")[:7]  # YYYY-MM
            if month not in grouped:
                grouped[month] = {"month": month, "sales": 0, "expenses": 0, "gst": 0}
            grouped[month]["sales"] += float(s.get("total_sale", 0) or 0)
            grouped[month]["gst"] += float(s.get("gst_amount", 0) or 0)
        
        expenses_data = await db.expenses.find(query, {"_id": 0}).to_list(10000)
        for e in expenses_data:
            month = e.get("date", "2025-01-01")[:7]
            if month in grouped:
                grouped[month]["expenses"] += float(e.get("amount", 0) or 0)
        
        trends = sorted(grouped.values(), key=lambda x: x["month"])
    
    # Calculate profit for each period (GST from actual data, not 5%)
    for t in trends:
        sales = t.get("sales", 0)
        expenses = t.get("expenses", 0)
        gst = round(t.get("gst", 0), 2)
        t["gst"] = gst
        # GST is not deducted — it's paid as an expense in M+1 (see gst_liabilities flow)
        t["profit"] = round(sales - expenses, 2)
    
    return {"trends": trends, "group_by": group_by}

# =======================================
# CENTER COMPARISON ENDPOINT
# =======================================

@router.post("/center-comparison")
async def get_center_comparison(data: dict):
    """Get center-wise comparison data for charts"""
    token = data.get("token")
    period = data.get("period", "current_month")
    center = data.get("center", "all")
    custom_start = data.get("custom_start")
    custom_end = data.get("custom_end")
    
    session = await check_mis_access(token)
    
    start_date, end_date = get_period_dates(period, custom_start, custom_end)
    prev_start, prev_end = get_previous_period_dates(period, start_date, end_date)
    
    query = {"date": {"$gte": start_date, "$lte": end_date}}
    prev_query = {"date": {"$gte": prev_start, "$lte": prev_end}}
    
    if center != "all":
        query["center"] = center
        prev_query["center"] = center
    
    # Current period data
    sales_data = await db.daily_sales.find(query, {"_id": 0}).to_list(10000)
    expenses_data = await db.expenses.find(query, {"_id": 0}).to_list(10000)
    
    # Previous period data
    if center != "all":
        prev_query["center"] = center
    prev_sales = await db.daily_sales.find(prev_query, {"_id": 0}).to_list(10000)
    prev_expenses = await db.expenses.find(prev_query, {"_id": 0}).to_list(10000)
    
    # Aggregate by center
    centers = {}
    for s in sales_data:
        c = s.get("center", "Unknown")
        if c not in centers:
            centers[c] = {"center": c, "sales": 0, "expenses": 0, "prev_sales": 0, "prev_expenses": 0, "gst": 0}
        centers[c]["sales"] += float(s.get("total_sale", 0) or 0)
        centers[c]["gst"] += float(s.get("gst_amount", 0) or 0)
    
    for e in expenses_data:
        c = e.get("center", "Unknown")
        if c not in centers:
            centers[c] = {"center": c, "sales": 0, "expenses": 0, "prev_sales": 0, "prev_expenses": 0, "gst": 0}
        centers[c]["expenses"] += float(e.get("amount", 0) or 0)
    
    for s in prev_sales:
        c = s.get("center", "Unknown")
        if c in centers:
            centers[c]["prev_sales"] += float(s.get("total_sale", 0) or 0)
    
    for e in prev_expenses:
        c = e.get("center", "Unknown")
        if c in centers:
            centers[c]["prev_expenses"] += float(e.get("amount", 0) or 0)
    
    # Calculate metrics for each center
    for c in centers.values():
        c["gst"] = round(c.get("gst", 0), 2)
        c["profit"] = round(c["sales"] - c["expenses"] - c["gst"], 2)
        c["profit_margin"] = round((c["profit"] / c["sales"] * 100) if c["sales"] > 0 else 0, 2)
        
        # Changes
        if c["prev_sales"] > 0:
            c["sales_change"] = round(((c["sales"] - c["prev_sales"]) / c["prev_sales"]) * 100, 2)
        else:
            c["sales_change"] = 100 if c["sales"] > 0 else 0
            
        if c["prev_expenses"] > 0:
            c["expenses_change"] = round(((c["expenses"] - c["prev_expenses"]) / c["prev_expenses"]) * 100, 2)
        else:
            c["expenses_change"] = 100 if c["expenses"] > 0 else 0
    
    # Sort by sales
    centers_list = sorted(centers.values(), key=lambda x: x["sales"], reverse=True)
    
    return {"centers": centers_list}

# =======================================
# EXPENSE ANALYSIS ENDPOINT
# =======================================

@router.post("/expense-analysis")
async def get_expense_analysis(data: dict):
    """Get detailed expense analysis by category/head"""
    token = data.get("token")
    period = data.get("period", "current_month")
    center = data.get("center", "all")
    custom_start = data.get("custom_start")
    custom_end = data.get("custom_end")
    
    session = await check_mis_access(token)
    
    start_date, end_date = get_period_dates(period, custom_start, custom_end)
    prev_start, prev_end = get_previous_period_dates(period, start_date, end_date)
    
    query = {"date": {"$gte": start_date, "$lte": end_date}}
    prev_query = {"date": {"$gte": prev_start, "$lte": prev_end}}
    
    if center != "all":
        query["center"] = center
        prev_query["center"] = center
    
    expenses = await db.expenses.find(query, {"_id": 0}).to_list(10000)
    prev_expenses = await db.expenses.find(prev_query, {"_id": 0}).to_list(10000)
    
    # Aggregate by expense type/head
    by_type = {}
    for e in expenses:
        exp_type = e.get("expense_type", "OTHER") or "OTHER"
        if exp_type not in by_type:
            by_type[exp_type] = {"type": exp_type, "amount": 0, "count": 0, "prev_amount": 0}
        by_type[exp_type]["amount"] += float(e.get("amount", 0) or 0)
        by_type[exp_type]["count"] += 1
    
    for e in prev_expenses:
        exp_type = e.get("expense_type", "OTHER") or "OTHER"
        if exp_type in by_type:
            by_type[exp_type]["prev_amount"] += float(e.get("amount", 0) or 0)
    
    # Calculate changes and alerts
    total_expenses = sum(t["amount"] for t in by_type.values())
    
    for t in by_type.values():
        t["percentage"] = round((t["amount"] / total_expenses * 100) if total_expenses > 0 else 0, 2)
        
        if t["prev_amount"] > 0:
            t["change"] = round(((t["amount"] - t["prev_amount"]) / t["prev_amount"]) * 100, 2)
        else:
            t["change"] = 100 if t["amount"] > 0 else 0
        
        # Alert status based on change
        if t["change"] > 25:
            t["alert"] = "high"
        elif t["change"] > 10:
            t["alert"] = "medium"
        else:
            t["alert"] = "normal"
    
    # Sort by amount
    expense_types = sorted(by_type.values(), key=lambda x: x["amount"], reverse=True)
    
    # Monthly trend by expense type
    monthly_trend = {}
    for e in expenses:
        month = e.get("date", "2025-01")[:7]
        exp_type = e.get("expense_type", "OTHER")
        key = f"{month}_{exp_type}"
        if key not in monthly_trend:
            monthly_trend[key] = {"month": month, "type": exp_type, "amount": 0}
        monthly_trend[key]["amount"] += float(e.get("amount", 0) or 0)
    
    return {
        "by_type": expense_types,
        "total_expenses": round(total_expenses, 2),
        "monthly_breakdown": sorted(monthly_trend.values(), key=lambda x: (x["month"], x["type"]))
    }

# =======================================
# ALERTS ENDPOINT
# =======================================

@router.post("/alerts")
async def get_alerts(data: dict):
    """Get expense alerts and warnings"""
    token = data.get("token")
    center = data.get("center", "all")
    alert_threshold = data.get("alert_threshold", 20)  # Configurable threshold
    
    session = await check_mis_access(token)
    
    # Get current quarter vs last quarter comparison
    today = datetime.now()
    current_quarter = (today.month - 1) // 3
    
    # Current quarter dates
    cq_start = today.replace(month=current_quarter * 3 + 1, day=1)
    cq_end = today
    
    # Previous quarter dates
    if current_quarter == 0:
        pq_start = today.replace(year=today.year - 1, month=10, day=1)
        pq_end = today.replace(year=today.year - 1, month=12, day=31)
    else:
        pq_start = today.replace(month=(current_quarter - 1) * 3 + 1, day=1)
        pq_end = cq_start - timedelta(days=1)
    
    cq_query = {"date": {"$gte": cq_start.strftime("%Y-%m-%d"), "$lte": cq_end.strftime("%Y-%m-%d")}}
    pq_query = {"date": {"$gte": pq_start.strftime("%Y-%m-%d"), "$lte": pq_end.strftime("%Y-%m-%d")}}
    
    # Apply center filter
    if center != "all":
        cq_query["center"] = center
        pq_query["center"] = center
    
    # Expenses by center
    cq_expenses = await db.expenses.find(cq_query, {"_id": 0}).to_list(10000)
    pq_expenses = await db.expenses.find(pq_query, {"_id": 0}).to_list(10000)
    
    # Aggregate by center
    center_expenses = {}
    for e in cq_expenses:
        c = e.get("center", "Unknown")
        if c not in center_expenses:
            center_expenses[c] = {"center": c, "current": 0, "previous": 0}
        center_expenses[c]["current"] += float(e.get("amount", 0) or 0)
    
    for e in pq_expenses:
        c = e.get("center", "Unknown")
        if c in center_expenses:
            center_expenses[c]["previous"] += float(e.get("amount", 0) or 0)
    
    # Aggregate by expense type
    type_expenses = {}
    for e in cq_expenses:
        t = e.get("expense_type", "OTHER")
        if t not in type_expenses:
            type_expenses[t] = {"type": t, "current": 0, "previous": 0}
        type_expenses[t]["current"] += float(e.get("amount", 0) or 0)
    
    for e in pq_expenses:
        t = e.get("expense_type", "OTHER")
        if t in type_expenses:
            type_expenses[t]["previous"] += float(e.get("amount", 0) or 0)
    
    # Generate alerts
    alerts = []
    
    # Center alerts
    for c, data in center_expenses.items():
        if data["previous"] > 0:
            change = ((data["current"] - data["previous"]) / data["previous"]) * 100
            if change > alert_threshold:
                alerts.append({
                    "type": "center",
                    "entity": c,
                    "message": f"{c} expenses increased by {change:.1f}%",
                    "severity": "high" if change > 50 else "medium",
                    "current": data["current"],
                    "previous": data["previous"],
                    "change": round(change, 2)
                })
    
    # Expense type alerts
    for t, data in type_expenses.items():
        if data["previous"] > 0:
            change = ((data["current"] - data["previous"]) / data["previous"]) * 100
            if change > alert_threshold:
                alerts.append({
                    "type": "expense_head",
                    "entity": t,
                    "message": f"{t} expenses increased by {change:.1f}%",
                    "severity": "high" if change > 50 else "medium",
                    "current": data["current"],
                    "previous": data["previous"],
                    "change": round(change, 2)
                })
    
    # Sort by severity and change
    alerts.sort(key=lambda x: (-1 if x["severity"] == "high" else 0, -x["change"]))
    
    return {
        "alerts": alerts,
        "threshold": alert_threshold,
        "current_quarter": f"Q{current_quarter + 1} {today.year}",
        "previous_quarter": f"Q{current_quarter if current_quarter > 0 else 4} {today.year if current_quarter > 0 else today.year - 1}"
    }

# =======================================
# QUARTERLY COMPARISON ENDPOINT
# =======================================

@router.post("/quarterly-comparison")
async def get_quarterly_comparison(data: dict):
    """Get quarter-over-quarter comparison"""
    token = data.get("token")
    center = data.get("center", "all")
    
    session = await check_mis_access(token)
    
    today = datetime.now()
    quarters = []
    
    # Get last 4 quarters
    for i in range(4):
        q_date = today - relativedelta(months=i * 3)
        q_num = (q_date.month - 1) // 3
        q_year = q_date.year
        
        q_start = datetime(q_year, q_num * 3 + 1, 1)
        if q_num == 3:
            q_end = datetime(q_year, 12, 31)
        else:
            q_end = datetime(q_year, (q_num + 1) * 3 + 1, 1) - timedelta(days=1)
        
        # Adjust end date if it's current quarter
        if i == 0:
            q_end = today
        
        query = {"date": {"$gte": q_start.strftime("%Y-%m-%d"), "$lte": q_end.strftime("%Y-%m-%d")}}
        if center != "all":
            query["center"] = center
        
        sales = await db.daily_sales.find(query, {"_id": 0}).to_list(10000)
        expenses = await db.expenses.find(query, {"_id": 0}).to_list(10000)
        
        total_sales = sum(float(s.get("total_sale", 0) or 0) for s in sales)
        total_expenses = sum(float(e.get("amount", 0) or 0) for e in expenses)
        gst = round(sum(float(s.get("gst_amount", 0) or 0) for s in sales), 2)
        # GST is not deducted — it's paid as an expense in M+1 (see gst_liabilities flow)
        profit = total_sales - total_expenses
        
        quarters.append({
            "quarter": f"Q{q_num + 1}",
            "year": q_year,
            "label": f"Q{q_num + 1} {q_year}",
            "sales": round(total_sales, 2),
            "expenses": round(total_expenses, 2),
            "gst": gst,
            "profit": round(profit, 2),
            "profit_margin": round((profit / total_sales * 100) if total_sales > 0 else 0, 2)
        })
    
    quarters.reverse()
    
    return {"quarters": quarters}

# =======================================
# TOP PERFORMERS ENDPOINT
# =======================================

@router.post("/top-performers")
async def get_top_performers(data: dict):
    """Get top and bottom performing centers"""
    token = data.get("token")
    period = data.get("period", "current_month")
    center = data.get("center", "all")
    custom_start = data.get("custom_start")
    custom_end = data.get("custom_end")
    
    session = await check_mis_access(token)
    
    start_date, end_date = get_period_dates(period, custom_start, custom_end)
    query = {"date": {"$gte": start_date, "$lte": end_date}}
    if center != "all":
        query["center"] = center
    
    sales = await db.daily_sales.find(query, {"_id": 0}).to_list(10000)
    expenses = await db.expenses.find(query, {"_id": 0}).to_list(10000)
    
    centers = {}
    for s in sales:
        c = s.get("center", "Unknown")
        if c not in centers:
            centers[c] = {"center": c, "sales": 0, "expenses": 0, "gst": 0}
        centers[c]["sales"] += float(s.get("total_sale", 0) or 0)
        centers[c]["gst"] += float(s.get("gst_amount", 0) or 0)
    
    for e in expenses:
        c = e.get("center", "Unknown")
        if c in centers:
            centers[c]["expenses"] += float(e.get("amount", 0) or 0)
    
    for c in centers.values():
        c["gst"] = round(c.get("gst", 0), 2)
        c["profit"] = round(c["sales"] - c["expenses"] - c["gst"], 2)
        c["profit_margin"] = round((c["profit"] / c["sales"] * 100) if c["sales"] > 0 else 0, 2)
    
    centers_list = list(centers.values())
    
    # Sort for top/bottom
    by_sales = sorted(centers_list, key=lambda x: x["sales"], reverse=True)
    by_profit = sorted(centers_list, key=lambda x: x["profit"], reverse=True)
    by_margin = sorted(centers_list, key=lambda x: x["profit_margin"], reverse=True)
    
    return {
        "top_by_sales": by_sales[:5],
        "bottom_by_sales": by_sales[-5:][::-1] if len(by_sales) > 5 else [],
        "top_by_profit": by_profit[:5],
        "bottom_by_profit": by_profit[-5:][::-1] if len(by_profit) > 5 else [],
        "top_by_margin": by_margin[:5],
        "bottom_by_margin": by_margin[-5:][::-1] if len(by_margin) > 5 else []
    }

# =======================================
# ALERT SETTINGS ENDPOINT
# =======================================

@router.post("/save-alert-settings")
async def save_alert_settings(data: dict):
    """Save alert threshold settings"""
    token = data.get("token")
    threshold = data.get("threshold", 20)
    
    session = await check_mis_access(token)
    
    if not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin can change alert settings")
    
    await db.settings.update_one(
        {"key": "mis_alert_threshold"},
        {"$set": {"key": "mis_alert_threshold", "value": threshold}},
        upsert=True
    )
    
    return {"success": True, "threshold": threshold}

@router.post("/get-alert-settings")
async def get_alert_settings(data: dict):
    """Get current alert threshold setting"""
    token = data.get("token")
    session = await check_mis_access(token)
    
    setting = await db.settings.find_one({"key": "mis_alert_threshold"}, {"_id": 0})
    threshold = setting.get("value", 20) if setting else 20
    
    return {"threshold": threshold}

# =======================================
# WORKING CAPITAL REMAINING ENDPOINT
# =======================================

@router.post("/working-capital")
async def get_working_capital(data: dict):
    """Get working capital using the same P/L logic as the WC Assessment table.
    WC = Initial WC + cumulative (Sales - Expenses - Commissions) + Topups.
    Center-wise: each center shows WC from the franchise mapped to it."""
    token = data.get("token")
    center = data.get("center", "all")
    period = data.get("period", "current_month")
    custom_start = data.get("custom_start")
    custom_end = data.get("custom_end")
    
    session = await check_mis_access(token)
    
    # Get the end date to determine which month to calculate WC up to
    start_date, end_date = get_period_dates(period, custom_start, custom_end)
    up_to_month = end_date[:7]  # "YYYY-MM"
    
    # Build list of centers to check
    if center == "all":
        centers_list = await db.centers.find(
            {"active": True}, {"_id": 0, "code": 1, "name": 1}
        ).to_list(100)
        center_codes = [c["code"] for c in centers_list]
    else:
        center_codes = [center]
    
    # Import the shared WC logic
    from routes.center_accounts import calculate_working_capital_standing, get_franchise_for_center
    
    # Calculate WC for each center using the same logic as the WC table
    centers_summary = []
    total_initial_wc = 0
    total_current_wc = 0
    total_loans = 0
    total_repaid = 0
    
    for cc in center_codes:
        try:
            wc_data = await calculate_working_capital_standing(db, cc, up_to_month)
            initial_wc = wc_data.get("initial_security_deposit", 0)
            closing_wc = wc_data.get("closing_wc", 0)
            loans_outstanding = wc_data.get("loans_outstanding", 0)
            
            # Get franchise info for display
            franchise = await get_franchise_for_center(cc)
            franchise_name = franchise.get("franchise_name", franchise.get("name", "")) if franchise else ""
            owner_name = franchise.get("owner_name", "") if franchise else ""
            
            total_initial_wc += initial_wc
            total_current_wc += closing_wc
            total_loans += wc_data.get("total_effective_loans", 0)
            
            # Other Income + Loans taken/given memos (non-operating cash view)
            try:
                from routes.other_income import (
                    get_other_income_summary, get_loans_taken_summary, get_loans_given_summary
                )
                oi_memo = await get_other_income_summary(cc, up_to_month)
                lt_memo = await get_loans_taken_summary(cc, up_to_month)
                lg_memo = await get_loans_given_summary(cc, up_to_month)
            except Exception:
                oi_memo = {"total": 0, "by_category": {}}
                lt_memo = {"total": 0, "outstanding": 0, "repaid": 0}
                lg_memo = {"total": 0, "outstanding": 0, "repaid": 0}
            
            centers_summary.append({
                "center": cc,
                "franchise_name": franchise_name,
                "owner_name": owner_name,
                "initial_wc": round(initial_wc, 2),
                "current_wc": round(closing_wc, 2),
                "this_month_pnl": round(wc_data.get("this_month_pnl", 0), 2),
                "wc_percentage": round(wc_data.get("wc_percentage", 100), 2),
                "wc_status": wc_data.get("wc_status", "healthy"),
                "revenue_share_active": wc_data.get("revenue_share_active", True),
                "loans_outstanding": round(loans_outstanding, 2),
                "available_wc": round(closing_wc, 2),
                # Non-operating cash inflow memos
                "other_income_total": round(float(oi_memo.get("total", 0) or 0), 2),
                "other_income_by_category": oi_memo.get("by_category", {}),
                "loans_taken_total": round(float(lt_memo.get("total", 0) or 0), 2),
                "loans_taken_outstanding": round(float(lt_memo.get("outstanding", 0) or 0), 2),
                "loans_given_total": round(float(lg_memo.get("total", 0) or 0), 2),
                "loans_given_outstanding": round(float(lg_memo.get("outstanding", 0) or 0), 2),
                # Legacy fields for backward compat
                "total_loans": round(wc_data.get("total_effective_loans", 0), 2),
                "total_repaid": 0,
                "outstanding": round(loans_outstanding, 2),
            })
        except Exception as e:
            logger.warning(f"MIS WC calc failed for {cc}: {e}")
    
    # Get loan timeline for reference
    loan_query = {"center": {"$in": center_codes}} if center != "all" else {}
    loan_entries = await db.loan_entries.find(
        loan_query, {"_id": 0}
    ).sort("created_at", 1).to_list(500)
    
    loan_timeline = []
    for le in loan_entries:
        c = le.get("center", "")
        amt = float(le.get("amount", 0) or 0)
        repaid = float(le.get("total_repaid", 0) or 0)
        total_repaid += repaid
        
        loan_timeline.append({
            "date": le.get("loan_date", le.get("created_at", "")[:10] if le.get("created_at") else ""),
            "center": c,
            "loan_id": le.get("loan_id", ""),
            "type": "loan",
            "description": le.get("reason", "Loan"),
            "amount": amt,
            "repaid": repaid,
            "outstanding": round(amt - repaid, 2),
            "status": le.get("status", "active")
        })
        
        for rep in le.get("repayments", []):
            loan_timeline.append({
                "date": rep.get("repayment_date", ""),
                "center": c,
                "loan_id": le.get("loan_id", ""),
                "type": "repayment",
                "description": f"Repayment - {rep.get('notes', '')}",
                "amount": float(rep.get("amount", 0)),
                "repaid": 0,
                "outstanding": 0,
                "status": "repaid"
            })
    
    loan_timeline.sort(key=lambda x: x.get("date", ""))
    
    total_outstanding = total_loans
    
    # Aggregate top-level Other Income / Loans Taken / Loans Given totals
    total_other_income = round(sum(c.get("other_income_total", 0) for c in centers_summary), 2)
    total_loans_taken = round(sum(c.get("loans_taken_total", 0) for c in centers_summary), 2)
    total_loans_taken_out = round(sum(c.get("loans_taken_outstanding", 0) for c in centers_summary), 2)
    total_loans_given = round(sum(c.get("loans_given_total", 0) for c in centers_summary), 2)
    total_loans_given_out = round(sum(c.get("loans_given_outstanding", 0) for c in centers_summary), 2)
    
    return {
        "initial_working_capital": round(total_initial_wc, 2),
        "available_working_capital": round(total_current_wc, 2),
        "total_loans": round(total_loans, 2),
        "total_repaid": round(total_repaid, 2),
        "total_outstanding": round(total_outstanding, 2),
        # Non-operating cash-flow totals (across selected centers, for selected month)
        "total_other_income": total_other_income,
        "total_loans_taken": total_loans_taken,
        "total_loans_taken_outstanding": total_loans_taken_out,
        "total_loans_given": total_loans_given,
        "total_loans_given_outstanding": total_loans_given_out,
        "up_to_month": up_to_month,
        "centers": centers_summary,
        "loan_timeline": loan_timeline,
        "data": loan_timeline,
        "total_working_capital": round(total_current_wc, 2)
    }


# =======================================
# PDF REPORT GENERATION
# =======================================

def _generate_trend_chart(trends_data, is_intl=False):
    """Generate Sales vs Expenses trend chart as image bytes."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

    trends = trends_data.get("trends", []) if trends_data else []
    if not trends or len(trends) < 2:
        return None

    dates = [t.get("date", t.get("week_start", ""))[:10] for t in trends]
    sales = [float(t.get("sales", 0)) for t in trends]
    expenses = [float(t.get("expenses", 0)) for t in trends]

    fig, ax = plt.subplots(figsize=(6.5, 2.5))
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FAFBFC')

    ax.fill_between(dates, sales, alpha=0.15, color='#059669')
    ax.plot(dates, sales, color='#059669', linewidth=2, label='Sales', marker='o', markersize=3)
    ax.fill_between(dates, expenses, alpha=0.1, color='#DC2626')
    ax.plot(dates, expenses, color='#DC2626', linewidth=2, label='Expenses', marker='o', markersize=3)

    ax.legend(loc='upper right', fontsize=7, frameon=False)
    ax.set_title('Sales vs Expenses Trend', fontsize=10, fontweight='bold', color='#1E293B', pad=8)
    ax.tick_params(axis='both', labelsize=6, colors='#64748B')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#E2E8F0')
    ax.spines['bottom'].set_color('#E2E8F0')
    ax.grid(axis='y', alpha=0.3, color='#CBD5E1')

    sym = "$" if is_intl else "\u20b9"
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f"{sym}{x/100000:.1f}L" if x >= 100000 else f"{sym}{x/1000:.0f}K" if x >= 1000 else f"{sym}{x:.0f}"
    ))

    if len(dates) > 8:
        for i, label in enumerate(ax.xaxis.get_ticklabels()):
            if i % max(1, len(dates) // 6) != 0:
                label.set_visible(False)

    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf


def _generate_pie_chart(centers_data, is_intl=False):
    """Generate Sales by Center pie chart as image bytes."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    centers = centers_data or []
    if not centers:
        return None

    labels = [c.get("center", "?") for c in centers[:8]]
    sizes = [float(c.get("sales", 0)) for c in centers[:8]]
    if sum(sizes) == 0:
        return None

    pie_colors = ['#D97706', '#059669', '#7C3AED', '#DC2626', '#2563EB', '#F59E0B', '#10B981', '#8B5CF6']

    fig, ax = plt.subplots(figsize=(3.2, 2.5))
    fig.patch.set_facecolor('#FFFFFF')

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=pie_colors[:len(labels)],
        autopct='%1.0f%%', startangle=90,
        textprops={'fontsize': 7, 'color': '#334155'},
        pctdistance=0.75, wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2)
    )
    for t in autotexts:
        t.set_fontsize(6)
        t.set_color('white')
        t.set_fontweight('bold')

    ax.set_title('Sales by Center', fontsize=10, fontweight='bold', color='#1E293B', pad=8)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf


def _build_kpi_cards_table(kpi_list, sym="₹"):
    """Build a colorful KPI cards row using ReportLab Table with gradient-like backgrounds."""
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle

    CARD_COLORS = {
        "Total Sales": colors.HexColor("#059669"),
        "Total Expenses": colors.HexColor("#DC2626"),
        "Commissions": colors.HexColor("#7C3AED"),
        "GST on Sales": colors.HexColor("#9333EA"),
        "Net Revenue": colors.HexColor("#0E7490"),
        "Net Profit": colors.HexColor("#047857"),
        "Net Profit (Loss)": colors.HexColor("#B91C1C"),
        "Working Capital": colors.HexColor("#D97706"),
        "Avg / Bill": colors.HexColor("#0D9488"),
        "Revenue Share": colors.HexColor("#2563EB"),
    }

    label_style = ParagraphStyle("KPILabel", fontSize=7, textColor=colors.HexColor("#FFFFFFCC"),
                                  fontName="Helvetica", leading=9)
    value_style = ParagraphStyle("KPIValue", fontSize=11, textColor=colors.white,
                                  fontName="Helvetica-Bold", leading=14)
    change_style = ParagraphStyle("KPIChange", fontSize=6, textColor=colors.HexColor("#FFFFFFAA"),
                                   fontName="Helvetica", leading=8)

    cards_data = []
    card_colors = []

    for kpi in kpi_list:
        label = kpi.get("label", "")
        value = kpi.get("value", "")
        change = kpi.get("change", "")

        bg = CARD_COLORS.get(label, colors.HexColor("#475569"))
        if "Profit" in label and "loss" in str(value).lower() or (isinstance(kpi.get("raw_value"), (int, float)) and kpi["raw_value"] < 0 and "Profit" in label):
            bg = colors.HexColor("#B91C1C")

        card_colors.append(bg)
        cards_data.append([
            Paragraph(f"{label}", label_style),
            Paragraph(f"{value}", value_style),
            Paragraph(f"{change}", change_style) if change else Paragraph("", change_style),
        ])

    if not cards_data:
        return None

    # Build rows of 3-4 cards each
    rows_of_cards = []
    cards_per_row = min(4, len(cards_data))

    for start in range(0, len(cards_data), cards_per_row):
        chunk = cards_data[start:start + cards_per_row]
        chunk_colors = card_colors[start:start + cards_per_row]

        row_data = []
        for card in chunk:
            inner = Table([[card[0]], [card[1]], [card[2]]], colWidths=[120])
            inner.setStyle(TableStyle([
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ]))
            row_data.append(inner)

        # Pad with empty cells if less than cards_per_row
        while len(row_data) < cards_per_row:
            row_data.append("")

        col_w = 500 // cards_per_row
        t = Table([row_data], colWidths=[col_w] * cards_per_row)

        style_commands = [
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ]
        for i, bg in enumerate(chunk_colors):
            style_commands.append(('BACKGROUND', (i, 0), (i, 0), bg))

        t.setStyle(TableStyle(style_commands))
        rows_of_cards.append(t)

    return rows_of_cards


def _build_mis_pdf(overview_data, trends_data, expense_data, wc_data, quarterly_data, center_label, is_intl=False):
    """Generate a professional branded MIS PDF report with colorful KPI cards and charts."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
        HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=14*mm, rightMargin=14*mm,
        topMargin=12*mm, bottomMargin=14*mm,
        title="Purnabramha MIS Report"
    )

    styles = getSampleStyleSheet()
    SAFFRON = colors.HexColor("#D97706")
    DARK_BG = colors.HexColor("#1E293B")
    HEADER_BG = colors.HexColor("#0F172A")
    GREEN = colors.HexColor("#059669")
    RED = colors.HexColor("#DC2626")
    LIGHT_GRAY = colors.HexColor("#F1F5F9")
    MID_GRAY = colors.HexColor("#94A3B8")

    title_style = ParagraphStyle("BrandTitle", parent=styles["Title"], fontSize=20,
        textColor=colors.white, spaceAfter=2, fontName="Helvetica-Bold")
    subtitle_style = ParagraphStyle("SubTitle", parent=styles["Normal"], fontSize=10,
        textColor=colors.HexColor("#94A3B8"), spaceAfter=4, fontName="Helvetica")
    section_style = ParagraphStyle("SectionHead", parent=styles["Heading2"], fontSize=13,
        textColor=DARK_BG, spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold")
    normal_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9,
        textColor=colors.HexColor("#334155"), fontName="Helvetica")
    small_style = ParagraphStyle("Small", parent=styles["Normal"], fontSize=7.5,
        textColor=MID_GRAY, fontName="Helvetica")

    sym = "$" if is_intl else "\u20b9"

    def fmt(val):
        if val is None: return f"{sym}0"
        sign = "-" if val < 0 else ""
        return f"{sign}{sym}{abs(val):,.2f}"

    def fmt_short(val):
        if val is None: return f"{sym}0"
        sign = "-" if val < 0 else ""
        av = abs(val)
        if av >= 10000000: return f"{sign}{sym}{av/10000000:.2f}Cr"
        if av >= 100000: return f"{sign}{sym}{av/100000:.2f}L"
        if av >= 1000: return f"{sign}{sym}{av/1000:.1f}K"
        return f"{sign}{sym}{av:,.0f}"

    elements = []

    # ── DARK HEADER BANNER ──
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pb_logo.png")
    period = overview_data.get("period", {})
    period_text = f"{center_label} &nbsp;|&nbsp; {period.get('start', '')} to {period.get('end', '')}"

    header_cells = []
    if os.path.exists(logo_path):
        logo_img = Image(logo_path, width=44, height=44)
        header_cells = [[logo_img, Paragraph("MIS Dashboard", title_style), ""]]
    else:
        header_cells = [["", Paragraph("MIS Dashboard", title_style), ""]]

    header_table = Table(header_cells, colWidths=[55, 350, 100])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_BG),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    elements.append(header_table)

    # Period subtitle
    elements.append(Paragraph(period_text, subtitle_style))
    elements.append(Spacer(1, 6))

    # ── COLORFUL KPI CARDS ──
    s = overview_data.get("summary", {})
    changes = overview_data.get("changes", {})
    profit = s.get("profit", 0)
    available_wc = wc_data.get("available_working_capital", 0) if wc_data else 0

    kpi_list = [
        {"label": "Total Sales", "value": fmt_short(s.get("total_sales")),
         "change": f"{changes.get('sales_change', 0):+.1f}% vs prev"},
        {"label": "Total Expenses", "value": fmt_short(s.get("total_expenses")),
         "change": f"{changes.get('expenses_change', 0):+.1f}% vs prev"},
        {"label": "Commissions", "value": fmt_short(s.get("total_commissions")), "change": ""},
        {"label": "Net Profit" if profit >= 0 else "Net Profit (Loss)", "value": fmt_short(profit),
         "change": f"{changes.get('profit_change', 0):+.1f}% vs prev", "raw_value": profit},
        {"label": "Working Capital", "value": fmt_short(available_wc), "change": ""},
        {"label": "Avg / Bill", "value": fmt_short(s.get("avg_per_bill")), "change": ""},
    ]

    card_tables = _build_kpi_cards_table(kpi_list, sym)
    if card_tables:
        for ct in card_tables:
            elements.append(ct)
            elements.append(Spacer(1, 6))

    elements.append(Spacer(1, 4))

    # ── CHARTS SIDE BY SIDE ──
    trend_img_buf = _generate_trend_chart(trends_data, is_intl)
    pie_img_buf = _generate_pie_chart(overview_data.get("centers", []), is_intl)

    chart_row = []
    if trend_img_buf:
        chart_row.append(Image(trend_img_buf, width=280, height=110))
    if pie_img_buf:
        chart_row.append(Image(pie_img_buf, width=180, height=110))

    if chart_row:
        if len(chart_row) == 2:
            chart_table = Table([chart_row], colWidths=[300, 200])
        else:
            chart_table = Table([chart_row], colWidths=[500])
        chart_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ]))
        elements.append(chart_table)
        elements.append(Spacer(1, 10))

    # ── CENTER PERFORMANCE TABLE ──
    centers = overview_data.get("centers", [])
    if centers:
        elements.append(Paragraph("Center Performance Summary", section_style))
        center_header = ["Center", "Sales", "Expenses", "GST", "Commission", "Profit"]
        center_rows = [center_header]
        for c in centers:
            center_rows.append([
                c.get("center", ""),
                fmt(c.get("sales")),
                fmt(c.get("expenses")),
                fmt(c.get("gst")),
                fmt(c.get("commissions", 0)),
                fmt(c.get("profit", 0)),
            ])

        ct = Table(center_rows, colWidths=[80, 85, 85, 75, 80, 80])
        ct.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(ct)
        elements.append(Spacer(1, 10))

    # ── EXPENSE ANALYSIS ──
    exp_types = expense_data.get("by_type", []) if expense_data else []
    if exp_types:
        elements.append(Paragraph("Expense Analysis", section_style))
        exp_header = ["Expense Head", "Amount", "% of Total", "Count", "Prev Period", "Change %"]
        exp_rows = [exp_header]
        for e in exp_types:
            exp_rows.append([
                e.get("type", ""),
                fmt(e.get("amount")),
                f"{e.get('percentage', 0)}%",
                str(e.get("count", 0)),
                fmt(e.get("prev_amount")),
                f"{e.get('change', 0):+.1f}%",
            ])

        et = Table(exp_rows, colWidths=[100, 80, 60, 40, 80, 60])
        et_style = [
            ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ]
        et.setStyle(TableStyle(et_style))
        elements.append(et)
        elements.append(Spacer(1, 10))

    # ── WORKING CAPITAL ──
    elements.append(Paragraph("Working Capital", section_style))
    initial_wc = wc_data.get("initial_working_capital", 0) if wc_data else 0
    up_to_month = wc_data.get("up_to_month", "") if wc_data else ""
    total_loans_val = wc_data.get("total_outstanding", 0) if wc_data else 0

    # WC summary as colored mini-cards
    wc_summary_data = [[
        Paragraph(f"<b>Initial WC</b><br/>{fmt(initial_wc)}", normal_style),
        Paragraph(f"<b>Current WC</b><br/>{fmt(available_wc)}", normal_style),
        Paragraph(f"<b>Loans Outstanding</b><br/>{fmt(total_loans_val)}", normal_style),
        Paragraph(f"<b>As of</b><br/>{up_to_month}", normal_style),
    ]]
    wc_summary_t = Table(wc_summary_data, colWidths=[125, 125, 125, 100])
    wc_summary_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#E0F2FE")),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#D1FAE5") if available_wc >= initial_wc else colors.HexColor("#FEE2E2")),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor("#FEF3C7")),
        ('BACKGROUND', (3, 0), (3, 0), colors.HexColor("#F1F5F9")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    elements.append(wc_summary_t)
    elements.append(Spacer(1, 6))

    # ── CASH INFLOWS (Non-Operating) ──
    total_oi = float(wc_data.get("total_other_income", 0) or 0) if wc_data else 0
    total_lt = float(wc_data.get("total_loans_taken", 0) or 0) if wc_data else 0
    total_lt_out = float(wc_data.get("total_loans_taken_outstanding", 0) or 0) if wc_data else 0
    total_lg = float(wc_data.get("total_loans_given", 0) or 0) if wc_data else 0
    total_lg_out = float(wc_data.get("total_loans_given_outstanding", 0) or 0) if wc_data else 0

    if total_oi > 0 or total_lt > 0 or total_lg > 0:
        elements.append(Paragraph("Cash Inflows (Non-Operating) & Inter-Center Loans", section_style))
        elements.append(Paragraph(
            "<font size=7 color='#64748B'>These do NOT affect P&L / Sales / Revenue Share. "
            "Other Income adjusts next-month Opening Working Capital.</font>",
            normal_style,
        ))
        elements.append(Spacer(1, 4))
        inflow_data = [[
            Paragraph(f"<b>Other Income</b><br/>{fmt(total_oi)}", normal_style),
            Paragraph(f"<b>Loans Taken</b><br/>{fmt(total_lt)}<br/><font size=7>Outstanding: {fmt(total_lt_out)}</font>", normal_style),
            Paragraph(f"<b>Loans Given</b><br/>{fmt(total_lg)}<br/><font size=7>Outstanding: {fmt(total_lg_out)}</font>", normal_style),
        ]]
        inflow_t = Table(inflow_data, colWidths=[155, 155, 165])
        inflow_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#DCFCE7")),   # emerald
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#FEF3C7")),   # amber
            ('BACKGROUND', (2, 0), (2, 0), colors.HexColor("#FFE4E6")),   # rose
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(inflow_t)
        elements.append(Spacer(1, 8))

    wc_centers = wc_data.get("centers", []) if wc_data else []
    if wc_centers:
        wc_header = ["Center", "Franchise", "Initial WC", "Current WC", "This Month P/L", "Loans", "Status"]
        wc_rows = [wc_header]
        for c in wc_centers:
            wc_rows.append([
                c.get("center", ""),
                c.get("franchise_name", "")[:20],
                fmt(c.get("initial_wc")),
                fmt(c.get("current_wc", c.get("available_wc"))),
                fmt(c.get("this_month_pnl", 0)),
                fmt(c.get("loans_outstanding", 0)),
                c.get("wc_status", "healthy").capitalize(),
            ])

        wt = Table(wc_rows, colWidths=[55, 85, 65, 70, 70, 65, 55])
        wt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(wt)
    elements.append(Spacer(1, 10))

    # ── QUARTERLY COMPARISON ──
    quarters = quarterly_data.get("quarters", []) if quarterly_data else []
    if quarters:
        elements.append(Paragraph("Quarterly Comparison", section_style))
        q_header = ["Quarter", "Sales", "Expenses", "GST"]
        q_rows = [q_header]
        for q in quarters:
            q_rows.append([q.get("label", ""), fmt(q.get("sales")), fmt(q.get("expenses")), fmt(q.get("gst"))])

        qt = Table(q_rows, colWidths=[120, 120, 120, 100])
        qt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(qt)
        elements.append(Spacer(1, 10))

    # ── FOOTER ──
    elements.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY, spaceBefore=16))
    generated_at = datetime.now().strftime("%d %b %Y, %I:%M %p")
    elements.append(Paragraph(
        f"Generated on {generated_at} &nbsp;|&nbsp; Purnabramha Franchise Management System &nbsp;|&nbsp; Confidential",
        small_style
    ))

    doc.build(elements)
    buf.seek(0)
    return buf


@router.post("/download-pdf")
async def download_mis_pdf(data: dict):
    """Generate and return a branded MIS PDF report."""
    token = data.get("token")
    period = data.get("period", "current_month")
    center = data.get("center", "all")
    custom_start = data.get("custom_start")
    custom_end = data.get("custom_end")

    session = await check_mis_access(token)

    # Determine if international center
    is_intl = False
    if center != "all":
        center_doc = await db.centers.find_one({"code": center}, {"_id": 0})
        if center_doc and center_doc.get("is_india_center") is False:
            is_intl = True

    center_label = "All Centers" if center == "all" else center

    # Reuse existing endpoint logic by calling internal helpers
    base_params = {"token": token, "period": period, "center": center,
                   "custom_start": custom_start, "custom_end": custom_end}

    # Fetch data from existing endpoints (call them internally)
    overview_data = await get_mis_overview({**base_params})
    expense_data = await get_expense_analysis({**base_params})
    wc_data = await get_working_capital({**base_params})
    quarterly_data = await get_quarterly_comparison({"token": token, "center": center})

    # Trends data
    group_by = "daily" if period == "current_month" else "weekly"
    trends_data = await get_sales_trends({**base_params, "group_by": group_by})

    pdf_buf = _build_mis_pdf(overview_data, trends_data, expense_data, wc_data, quarterly_data, center_label, is_intl)

    filename = f"MIS_Report_{center_label}_{overview_data['period']['start']}_to_{overview_data['period']['end']}.pdf"

    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("/franchise-pdf")
async def download_franchise_pdf(data: dict):
    """Generate and return a branded Franchise Dashboard PDF report."""
    token = data.get("token")
    period = data.get("period", "current_month")
    center = data.get("center", "all")
    custom_start = data.get("custom_start")
    custom_end = data.get("custom_end")
    franchise_info = data.get("franchise_info", {})
    revenue_share_pct = float(data.get("revenue_share_pct", 0))

    session = await check_mis_access(token)

    is_intl = False
    if center != "all":
        center_doc = await db.centers.find_one({"code": center}, {"_id": 0})
        if center_doc and center_doc.get("is_india_center") is False:
            is_intl = True

    base_params = {"token": token, "period": period, "center": center,
                   "custom_start": custom_start, "custom_end": custom_end}

    overview_data = await get_mis_overview({**base_params})
    expense_data = await get_expense_analysis({**base_params})
    wc_data = await get_working_capital({**base_params})
    
    # Get trends data for chart
    try:
        trends_data = await get_sales_trends({**base_params})
    except:
        trends_data = None
    
    # Attach trends to overview for chart generation
    overview_data["_trends_data"] = trends_data

    # Build Franchise PDF using the shared builder but with franchise branding
    pdf_buf = _build_franchise_pdf(overview_data, expense_data, wc_data, center,
                                    franchise_info, revenue_share_pct, is_intl)

    period_data = overview_data.get("period", {})
    filename = f"Franchise_Report_{center}_{period_data.get('start', '')}_to_{period_data.get('end', '')}.pdf"

    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


def _build_franchise_pdf(overview_data, expense_data, wc_data, center_code, franchise_info, revenue_share_pct, is_intl=False):
    """Generate a branded Franchise Dashboard PDF with colorful KPI cards and charts."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14*mm, rightMargin=14*mm,
                            topMargin=12*mm, bottomMargin=14*mm, title="Franchise Report")

    styles = getSampleStyleSheet()
    DARK_BG = colors.HexColor("#1E293B")
    HEADER_BG = colors.HexColor("#0F172A")
    SAFFRON = colors.HexColor("#D97706")
    LIGHT_GRAY = colors.HexColor("#F1F5F9")
    MID_GRAY = colors.HexColor("#94A3B8")

    title_style = ParagraphStyle("BrandTitle", parent=styles["Title"], fontSize=20,
        textColor=colors.white, spaceAfter=2, fontName="Helvetica-Bold")
    subtitle_style = ParagraphStyle("SubTitle", parent=styles["Normal"], fontSize=10,
        textColor=colors.HexColor("#94A3B8"), spaceAfter=4, fontName="Helvetica")
    section_style = ParagraphStyle("SectionHead", parent=styles["Heading2"], fontSize=13,
        textColor=DARK_BG, spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold")
    normal_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9,
        textColor=colors.HexColor("#334155"), fontName="Helvetica")
    small_style = ParagraphStyle("Small", parent=styles["Normal"], fontSize=7.5,
        textColor=MID_GRAY, fontName="Helvetica")

    sym = "$" if is_intl else "\u20b9"

    def fmt(val):
        if val is None: return f"{sym}0"
        sign = "-" if val < 0 else ""
        return f"{sign}{sym}{abs(val):,.2f}"

    def fmt_short(val):
        if val is None: return f"{sym}0"
        sign = "-" if val < 0 else ""
        av = abs(val)
        if av >= 10000000: return f"{sign}{sym}{av/10000000:.2f}Cr"
        if av >= 100000: return f"{sign}{sym}{av/100000:.2f}L"
        if av >= 1000: return f"{sign}{sym}{av/1000:.1f}K"
        return f"{sign}{sym}{av:,.0f}"

    elements = []

    # ── DARK HEADER BANNER with Logo ──
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pb_logo.png")
    period = overview_data.get("period", {})
    franchise_name = franchise_info.get("franchise_name", center_code)
    owner = franchise_info.get("owner_name", "")

    header_cells = []
    if os.path.exists(logo_path):
        logo_img = Image(logo_path, width=44, height=44)
        header_cells = [[logo_img, Paragraph("Franchise Dashboard", title_style), ""]]
    else:
        header_cells = [["", Paragraph("Franchise Dashboard", title_style), ""]]

    header_table = Table(header_cells, colWidths=[55, 350, 100])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_BG),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    elements.append(header_table)

    # Franchise info subtitle
    period_text = f"{franchise_name} &nbsp;|&nbsp; {center_code} &nbsp;|&nbsp; {period.get('start', '')} to {period.get('end', '')}"
    elements.append(Paragraph(period_text, subtitle_style))
    if owner:
        elements.append(Paragraph(f"Franchise Owner: {owner} &nbsp;|&nbsp; Revenue Share: {revenue_share_pct}%", subtitle_style))
    elements.append(Spacer(1, 6))

    # ── COLORFUL KPI CARDS ──
    s = overview_data.get("summary", {})
    changes = overview_data.get("changes", {})
    profit = s.get("profit", 0)
    available_wc = wc_data.get("available_working_capital", 0) if wc_data else 0
    # Net Revenue = Total Sales − Commissions − GST (per Apr-2026 rule).
    # Revenue Share is computed on Net Revenue (NOT profit).
    net_revenue_base = s.get("net_revenue", 0)
    revenue_share_amount = net_revenue_base * (revenue_share_pct / 100) if revenue_share_pct else 0

    kpi_list = [
        {"label": "Total Sales", "value": fmt_short(s.get("total_sales")),
         "change": f"{changes.get('sales_change', 0):+.1f}% vs prev"},
        {"label": "Total Expenses", "value": fmt_short(s.get("total_expenses")),
         "change": f"{changes.get('expenses_change', 0):+.1f}% vs prev"},
        {"label": "Commissions", "value": fmt_short(s.get("total_commissions")), "change": ""},
        {"label": "GST (Eligible Sales 5% incl.)", "value": fmt_short(s.get("total_gst")), "change": "Govt pass-through"},
        {"label": "Net Revenue", "value": fmt_short(net_revenue_base), "change": "Sales − Comm − GST"},
        {"label": "Net Profit" if profit >= 0 else "Net Profit (Loss)", "value": fmt_short(profit),
         "change": f"{changes.get('profit_change', 0):+.1f}% vs prev", "raw_value": profit},
        {"label": "Working Capital", "value": fmt_short(available_wc), "change": ""},
        {"label": "Avg / Bill", "value": fmt_short(s.get("avg_per_bill")), "change": ""},
        {"label": "Revenue Share", "value": fmt_short(revenue_share_amount),
         "change": f"{revenue_share_pct}% of Net Revenue"},
    ]

    card_tables = _build_kpi_cards_table(kpi_list, sym)
    if card_tables:
        for ct in card_tables:
            elements.append(ct)
            elements.append(Spacer(1, 6))

    elements.append(Spacer(1, 4))

    # ── CHARTS ──
    trends_data = overview_data.get("_trends_data")
    trend_img_buf = _generate_trend_chart(trends_data, is_intl) if trends_data else None

    if trend_img_buf:
        chart_table = Table([[Image(trend_img_buf, width=440, height=160)]], colWidths=[460])
        chart_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ]))
        elements.append(chart_table)
        elements.append(Spacer(1, 10))

    # ── FINANCIAL SUMMARY TABLE ──
    elements.append(Paragraph("Financial Summary", section_style))
    summary_rows = [
        [Paragraph("<b>Metric</b>", normal_style), Paragraph("<b>Value</b>", normal_style), Paragraph("<b>vs Prev / Note</b>", normal_style)],
        ["Total Sales", fmt(s.get("total_sales")), f"{changes.get('sales_change', 0):+.1f}%"],
        ["Less: Total Commissions", fmt(s.get("total_commissions")), ""],
        ["Less: GST on Eligible Sales (5% incl.)", fmt(s.get("total_gst")), "Govt pass-through"],
        ["= Net Revenue", fmt(net_revenue_base), "Sales − Comm − GST"],
        ["Eligible Rev Share Base", fmt(net_revenue_base), "Sales − Comm − Comm GST − GST"],
        ["Less: Total Expenses", fmt(s.get("total_expenses")), f"{changes.get('expenses_change', 0):+.1f}%"],
        ["= Net Profit", fmt(profit), f"{changes.get('profit_change', 0):+.1f}%"],
        ["Working Capital", fmt(available_wc), f"as of {wc_data.get('up_to_month', '')}"],
        [f"Revenue Share Payable ({revenue_share_pct}% × Net Revenue)", fmt(revenue_share_amount), ""],
        ["Avg per Bill", fmt(s.get("avg_per_bill")), ""],
    ]

    t = Table(summary_rows, colWidths=[180, 160, 120])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))

    # ── FINAL PAYOUT (Payout × GST) ──
    # Payout = MAX(Revenue Share, Monthly Guarantee). GST is then applied on
    # that payout amount, NOT on the bare revenue share. Mirrors the new "8B.
    # FINAL PAYOUT" block on the PIB so the gross-of-tax figure stays
    # consistent across PIB, MIS Franchise PDF and Owner Ledger.
    monthly_guarantee = float(franchise_info.get("monthly_guarantee", 0) or 0)
    payout_base = max(revenue_share_amount or 0, monthly_guarantee)
    if payout_base > 0:
        is_mg_payout = monthly_guarantee > (revenue_share_amount or 0)
        if is_intl:
            share_gst_rate = 10.0
            payout_rows = [
                [Paragraph("<b>Description</b>", normal_style), Paragraph("<b>Amount</b>", normal_style)],
                [f"{'Monthly Guarantee (paid — higher than Profit Share)' if is_mg_payout else 'Profit Share Payable'}", fmt(payout_base)],
                [f"Add: GST @ {share_gst_rate:.0f}%", fmt(payout_base * share_gst_rate / 100)],
                [f"Total Final Payout (incl. {share_gst_rate:.0f}% GST)",
                 fmt(payout_base * (1 + share_gst_rate / 100))],
            ]
        else:
            half = 9.0
            cgst = payout_base * half / 100
            sgst = payout_base * half / 100
            payout_rows = [
                [Paragraph("<b>Description</b>", normal_style), Paragraph("<b>Amount</b>", normal_style)],
                [f"{'Monthly Guarantee (paid — higher than Revenue Share)' if is_mg_payout else 'Revenue Share Payable'}", fmt(payout_base)],
                [f"Add: CGST @ {half:.0f}%", fmt(cgst)],
                [f"Add: SGST @ {half:.0f}%", fmt(sgst)],
                ["Total Final Payout (incl. 18% GST)", fmt(payout_base + cgst + sgst)],
            ]
        elements.append(Paragraph("Final Payout (Payout × GST)", section_style))
        pt = Table(payout_rows, colWidths=[280, 180])
        pt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), SAFFRON),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(pt)
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(
            "<i>Payout = MAX(Revenue Share, Monthly Guarantee). GST is computed on this payout amount.</i>",
            small_style))
        elements.append(Spacer(1, 10))

    # ── EXPENSE BREAKDOWN ──
    exp_types = expense_data.get("by_type", []) if expense_data else []
    if exp_types:
        elements.append(Paragraph("Expense Breakdown", section_style))
        exp_rows = [[Paragraph("<b>Expense Head</b>", normal_style), Paragraph("<b>Amount</b>", normal_style),
                     Paragraph("<b>% of Total</b>", normal_style), Paragraph("<b>Count</b>", normal_style)]]
        for e in exp_types:
            exp_rows.append([e.get("type", ""), fmt(e.get("amount")), f"{e.get('percentage', 0)}%", str(e.get("count", 0))])

        et = Table(exp_rows, colWidths=[150, 120, 80, 60])
        et.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(et)
        elements.append(Spacer(1, 10))

    # ── WORKING CAPITAL STANDING ──
    wc_centers = wc_data.get("centers", []) if wc_data else []
    if wc_centers:
        elements.append(Paragraph("Working Capital Standing", section_style))
        wc_rows = [["Center", "Initial WC", "Current WC", "This Month P/L", "Status"]]
        for c in wc_centers:
            wc_rows.append([
                c.get("center", ""),
                fmt(c.get("initial_wc")),
                fmt(c.get("current_wc", c.get("available_wc"))),
                fmt(c.get("this_month_pnl", 0)),
                c.get("wc_status", "healthy").capitalize(),
            ])
        wt = Table(wc_rows, colWidths=[80, 100, 100, 100, 80])
        wt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(wt)
        elements.append(Spacer(1, 10))

    # ── CASH INFLOWS (Non-Operating) ──
    _total_oi = float(wc_data.get("total_other_income", 0) or 0) if wc_data else 0
    _total_lt = float(wc_data.get("total_loans_taken", 0) or 0) if wc_data else 0
    _total_lt_out = float(wc_data.get("total_loans_taken_outstanding", 0) or 0) if wc_data else 0
    _total_lg = float(wc_data.get("total_loans_given", 0) or 0) if wc_data else 0
    _total_lg_out = float(wc_data.get("total_loans_given_outstanding", 0) or 0) if wc_data else 0
    if _total_oi > 0 or _total_lt > 0 or _total_lg > 0:
        elements.append(Paragraph("Cash Inflows (Non-Operating) & Inter-Center Loans", section_style))
        elements.append(Paragraph(
            "<font size=7 color='#64748B'>Does NOT affect P&L / Sales / Revenue Share. "
            "Other Income adjusts next-month Opening Working Capital.</font>",
            normal_style,
        ))
        elements.append(Spacer(1, 4))
        inflow_rows = [
            [Paragraph(f"<b>Other Income</b><br/>{fmt(_total_oi)}", normal_style),
             Paragraph(f"<b>Loans Taken</b><br/>{fmt(_total_lt)}<br/><font size=7>Outstanding: {fmt(_total_lt_out)}</font>", normal_style),
             Paragraph(f"<b>Loans Given</b><br/>{fmt(_total_lg)}<br/><font size=7>Outstanding: {fmt(_total_lg_out)}</font>", normal_style)],
        ]
        inflow_t = Table(inflow_rows, colWidths=[150, 150, 160])
        inflow_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#DCFCE7")),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#FEF3C7")),
            ('BACKGROUND', (2, 0), (2, 0), colors.HexColor("#FFE4E6")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(inflow_t)
        elements.append(Spacer(1, 10))

    # ── AUTHORISED SIGNATORY ──
    try:
        from utils.signature import signature_block
        center_country = "Australia" if is_intl else "India"
        elements.extend(signature_block(country=center_country, label="Authorised Signatory · Accounts"))
    except Exception:
        pass

    # ── FOOTER ──
    elements.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY, spaceBefore=16))
    generated_at = datetime.now().strftime("%d %b %Y, %I:%M %p")
    elements.append(Paragraph(
        f"Generated on {generated_at} &nbsp;|&nbsp; Purnabramha Franchise Management System &nbsp;|&nbsp; Confidential",
        small_style
    ))

    doc.build(elements)
    buf.seek(0)
    return buf
