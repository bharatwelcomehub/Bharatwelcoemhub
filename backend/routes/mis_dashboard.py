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
    
    # GST from actual data (gst_amount field in daily_sales)
    total_gst = round(sum(float(s.get("gst_amount", 0) or 0) for s in sales_data), 2)
    
    # Expenses
    total_expenses = sum(float(e.get("amount", 0) or 0) for e in expenses_data)
    
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
    
    # Profit calculation: Sales - Expenses - GST - Commissions
    profit = total_sales - total_expenses - total_gst - total_commissions
    profit_margin = round((profit / total_sales * 100) if total_sales > 0 else 0, 2)
    
    # Calculate totals - Previous Period
    prev_total_sales = sum(float(s.get("total_sale", 0) or 0) for s in prev_sales_data)
    prev_total_expenses = sum(float(e.get("amount", 0) or 0) for e in prev_expenses_data)
    prev_gst = round(sum(float(s.get("gst_amount", 0) or 0) for s in prev_sales_data), 2)
    prev_profit = prev_total_sales - prev_total_expenses - prev_gst
    
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
            centers_data[c] = {"sales": 0, "guests": 0, "bills": 0, "expenses": 0, "commissions": 0, "gst": 0}
        centers_data[c]["sales"] += float(s.get("total_sale", 0) or 0)
        centers_data[c]["guests"] += int(s.get("num_guests", 0) or 0)
        centers_data[c]["bills"] += int(s.get("num_bills", 0) or 0)
        centers_data[c]["gst"] += float(s.get("gst_amount", 0) or 0)
    
    for e in expenses_data:
        c = e.get("center", "Unknown")
        if c not in centers_data:
            centers_data[c] = {"sales": 0, "guests": 0, "bills": 0, "expenses": 0, "commissions": 0, "gst": 0}
        centers_data[c]["expenses"] += float(e.get("amount", 0) or 0)
    
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
    
    return {
        "period": {
            "type": period,
            "start": start_date,
            "end": end_date,
            "prev_start": prev_start,
            "prev_end": prev_end
        },
        "summary": {
            "total_sales": round(total_sales, 2),
            "total_cash_sales": round(total_cash_sales, 2),
            "total_online_sales": round(total_online_sales, 2),
            "total_expenses": round(total_expenses, 2),
            "total_gst": total_gst,
            "total_commissions": total_commissions,
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
        t["profit"] = round(sales - expenses - gst, 2)
    
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
        profit = total_sales - total_expenses - gst
        
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
    
    return {
        "initial_working_capital": round(total_initial_wc, 2),
        "available_working_capital": round(total_current_wc, 2),
        "total_loans": round(total_loans, 2),
        "total_repaid": round(total_repaid, 2),
        "total_outstanding": round(total_outstanding, 2),
        "up_to_month": up_to_month,
        "centers": centers_summary,
        "loan_timeline": loan_timeline,
        "data": loan_timeline,
        "total_working_capital": round(total_current_wc, 2)
    }


# =======================================
# PDF REPORT GENERATION
# =======================================

def _build_mis_pdf(overview_data, trends_data, expense_data, wc_data, quarterly_data, center_label, is_intl=False):
    """Generate a professional branded MIS PDF report using ReportLab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm, inch
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
        PageBreak, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=14*mm, bottomMargin=18*mm,
        title="Purnabramha MIS Report"
    )

    styles = getSampleStyleSheet()
    # Brand colours
    SAFFRON = colors.HexColor("#D97706")
    DARK_BG = colors.HexColor("#1E293B")
    HEADER_BG = colors.HexColor("#0F172A")
    GREEN = colors.HexColor("#059669")
    RED = colors.HexColor("#DC2626")
    LIGHT_GRAY = colors.HexColor("#F1F5F9")
    MID_GRAY = colors.HexColor("#94A3B8")

    # Custom styles
    title_style = ParagraphStyle("BrandTitle", parent=styles["Title"], fontSize=20,
        textColor=DARK_BG, spaceAfter=2, fontName="Helvetica-Bold")
    subtitle_style = ParagraphStyle("SubTitle", parent=styles["Normal"], fontSize=10,
        textColor=MID_GRAY, spaceAfter=6, fontName="Helvetica")
    section_style = ParagraphStyle("SectionHead", parent=styles["Heading2"], fontSize=13,
        textColor=DARK_BG, spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold",
        borderPadding=(0, 0, 4, 0))
    normal_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9,
        textColor=colors.HexColor("#334155"), fontName="Helvetica")
    small_style = ParagraphStyle("Small", parent=styles["Normal"], fontSize=7.5,
        textColor=MID_GRAY, fontName="Helvetica")

    sym = "$" if is_intl else "\u20b9"  # ₹ or $

    def fmt(val):
        if val is None:
            return f"{sym}0"
        sign = "-" if val < 0 else ""
        return f"{sign}{sym}{abs(val):,.2f}"

    def fmt_short(val):
        if val is None:
            return f"{sym}0"
        sign = "-" if val < 0 else ""
        av = abs(val)
        if av >= 10000000:
            return f"{sign}{sym}{av/10000000:.2f}Cr"
        if av >= 100000:
            return f"{sign}{sym}{av/100000:.2f}L"
        if av >= 1000:
            return f"{sign}{sym}{av/1000:.1f}K"
        return f"{sign}{sym}{av:,.0f}"

    elements = []

    # ── HEADER WITH LOGO ──
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pb_logo.png")
    header_data = []
    if os.path.exists(logo_path):
        logo_img = Image(logo_path, width=50, height=50)
        header_data = [[
            logo_img,
            Paragraph("Purnabramha", title_style),
            ""
        ]]
    else:
        header_data = [[
            "",
            Paragraph("Purnabramha", title_style),
            ""
        ]]

    header_table = Table(header_data, colWidths=[60, 340, 100])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
    ]))
    elements.append(header_table)

    # Subtitle line
    period = overview_data.get("period", {})
    elements.append(Paragraph(
        f"MIS Report &mdash; {center_label} &nbsp;|&nbsp; {period.get('start', '')} to {period.get('end', '')}",
        subtitle_style
    ))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=SAFFRON, spaceAfter=10))

    # ── SUMMARY SECTION ──
    s = overview_data.get("summary", {})
    changes = overview_data.get("changes", {})

    elements.append(Paragraph("Financial Summary", section_style))

    summary_rows = [
        [Paragraph("<b>Metric</b>", normal_style), Paragraph("<b>Value</b>", normal_style), Paragraph("<b>vs Prev Period</b>", normal_style)],
        ["Total Sales", fmt(s.get("total_sales")), f"{changes.get('sales_change', 0):+.1f}%"],
        ["Cash Sales", fmt(s.get("total_cash_sales")), ""],
        ["Online Sales", fmt(s.get("total_online_sales")), ""],
        ["Total Expenses", fmt(s.get("total_expenses")), f"{changes.get('expenses_change', 0):+.1f}%"],
        ["Commissions", fmt(s.get("total_commissions")), ""],
        ["GST", fmt(s.get("total_gst")), ""],
        ["Net Profit", fmt(s.get("profit")), f"{changes.get('profit_change', 0):+.1f}%"],
        ["Working Capital", fmt(wc_data.get("available_working_capital", 0) if wc_data else 0), f"as of {wc_data.get('up_to_month', '')}"],
        ["Total Guests", f"{s.get('total_guests', 0):,}", ""],
        ["Total Bills", f"{s.get('total_bills', 0):,}", ""],
        ["Avg per Guest", fmt(s.get("avg_per_guest")), ""],
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

    # ── CENTER PERFORMANCE ──
    centers = overview_data.get("centers", [])
    if centers:
        elements.append(Paragraph("Center Performance", section_style))
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

        ct = Table(center_rows, colWidths=[80, 90, 90, 80, 80, 80])
        ct_style = [
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
        ]
        ct.setStyle(TableStyle(ct_style))
        elements.append(ct)
        elements.append(Spacer(1, 10))

    # ── EXPENSE ANALYSIS ──
    exp_types = expense_data.get("by_type", []) if expense_data else []
    if exp_types:
        elements.append(Paragraph("Expense Analysis", section_style))
        exp_header = ["Expense Head", "Amount", "% of Total", "Count", "Prev Period", "Change %", "Status"]
        exp_rows = [exp_header]
        for e in exp_types:
            alert = e.get("alert", "normal")
            status = "Alert" if alert == "high" else ("Watch" if alert == "medium" else "Normal")
            exp_rows.append([
                e.get("type", ""),
                fmt(e.get("amount")),
                f"{e.get('percentage', 0)}%",
                str(e.get("count", 0)),
                fmt(e.get("prev_amount")),
                f"{e.get('change', 0):+.1f}%",
                status
            ])

        et = Table(exp_rows, colWidths=[90, 75, 55, 40, 75, 55, 50])
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
        for idx, e in enumerate(exp_types, start=1):
            alert = e.get("alert", "normal")
            if alert == "high":
                et_style.append(('BACKGROUND', (6, idx), (6, idx), colors.HexColor("#FEE2E2")))
                et_style.append(('TEXTCOLOR', (6, idx), (6, idx), RED))
            elif alert == "medium":
                et_style.append(('BACKGROUND', (6, idx), (6, idx), colors.HexColor("#FEF3C7")))
                et_style.append(('TEXTCOLOR', (6, idx), (6, idx), SAFFRON))
        et.setStyle(TableStyle(et_style))
        elements.append(et)
        elements.append(Spacer(1, 10))

    # ── WORKING CAPITAL ──
    elements.append(Paragraph("Working Capital", section_style))
    
    initial_wc = wc_data.get("initial_working_capital", 0) if wc_data else 0
    available_wc = wc_data.get("available_working_capital", 0) if wc_data else 0
    total_loans_val = wc_data.get("total_outstanding", 0) if wc_data else 0
    up_to_month = wc_data.get("up_to_month", "") if wc_data else ""
    
    elements.append(Paragraph(
        f"Initial WC: <b>{fmt(initial_wc)}</b> &nbsp;|&nbsp; "
        f"Current WC: <b>{fmt(available_wc)}</b> &nbsp;|&nbsp; "
        f"Loans Outstanding: <b>{fmt(total_loans_val)}</b> &nbsp;|&nbsp; "
        f"As of: <b>{up_to_month}</b>",
        normal_style
    ))
    elements.append(Spacer(1, 6))

    wc_centers = wc_data.get("centers", []) if wc_data else []
    if wc_centers:
        wc_header = ["Center", "Franchise", "Initial WC", "Current WC", "This Month P/L", "Loans", "Status"]
        wc_rows = [wc_header]
        for c in wc_centers:
            wc_rows.append([
                c.get("center", ""),
                c.get("franchise_name", ""),
                fmt(c.get("initial_wc")),
                fmt(c.get("current_wc", c.get("available_wc"))),
                fmt(c.get("this_month_pnl", 0)),
                fmt(c.get("loans_outstanding", 0)),
                c.get("wc_status", "healthy").capitalize(),
            ])

        wt = Table(wc_rows, colWidths=[60, 90, 65, 65, 65, 65, 65])
        wt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(wt)
    elif available_wc >= initial_wc and initial_wc > 0:
        elements.append(Paragraph(
            "Working capital is healthy and above initial deposit.",
            normal_style
        ))
    elements.append(Spacer(1, 10))

    # ── QUARTERLY COMPARISON ──
    quarters = quarterly_data.get("quarters", []) if quarterly_data else []
    if quarters:
        elements.append(Paragraph("Quarterly Comparison", section_style))
        q_header = ["Quarter", "Sales", "Expenses", "GST"]
        q_rows = [q_header]
        for q in quarters:
            q_rows.append([
                q.get("label", ""),
                fmt(q.get("sales")),
                fmt(q.get("expenses")),
                fmt(q.get("gst")),
            ])

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
        f"Generated on {generated_at} &nbsp;|&nbsp; Purnabramha Franchise Management System",
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
    """Generate a branded Franchise Dashboard PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=14*mm, bottomMargin=18*mm, title="Franchise Report")

    styles = getSampleStyleSheet()
    SAFFRON = colors.HexColor("#D97706")
    DARK_BG = colors.HexColor("#1E293B")
    HEADER_BG = colors.HexColor("#0F172A")
    GREEN = colors.HexColor("#059669")
    RED = colors.HexColor("#DC2626")
    LIGHT_GRAY = colors.HexColor("#F1F5F9")
    MID_GRAY = colors.HexColor("#94A3B8")

    title_style = ParagraphStyle("BrandTitle", parent=styles["Title"], fontSize=20,
        textColor=DARK_BG, spaceAfter=2, fontName="Helvetica-Bold")
    subtitle_style = ParagraphStyle("SubTitle", parent=styles["Normal"], fontSize=10,
        textColor=MID_GRAY, spaceAfter=6, fontName="Helvetica")
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

    elements = []

    # Header
    elements.append(Paragraph("Purnabramha - Franchise Dashboard", title_style))
    period = overview_data.get("period", {})
    franchise_name = franchise_info.get("franchise_name", center_code)
    owner = franchise_info.get("owner_name", "")
    elements.append(Paragraph(
        f"{franchise_name} &nbsp;|&nbsp; {center_code} &nbsp;|&nbsp; {period.get('start', '')} to {period.get('end', '')}",
        subtitle_style
    ))
    if owner:
        elements.append(Paragraph(f"Franchise Owner: {owner} &nbsp;|&nbsp; Revenue Share: {revenue_share_pct}%", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=SAFFRON, spaceAfter=10))

    # Financial Summary
    s = overview_data.get("summary", {})
    changes = overview_data.get("changes", {})
    profit = s.get("profit", 0)
    net_revenue = profit * (revenue_share_pct / 100) if revenue_share_pct else 0
    available_wc = wc_data.get("available_working_capital", 0) if wc_data else 0

    elements.append(Paragraph("Financial Summary", section_style))
    summary_rows = [
        [Paragraph("<b>Metric</b>", normal_style), Paragraph("<b>Value</b>", normal_style), Paragraph("<b>vs Prev</b>", normal_style)],
        ["Total Sales", fmt(s.get("total_sales")), f"{changes.get('sales_change', 0):+.1f}%"],
        ["Total Expenses", fmt(s.get("total_expenses")), f"{changes.get('expenses_change', 0):+.1f}%"],
        ["Commissions", fmt(s.get("total_commissions")), ""],
        ["GST", fmt(s.get("total_gst")), ""],
        ["Net Profit", fmt(profit), f"{changes.get('profit_change', 0):+.1f}%"],
        ["Working Capital", fmt(available_wc), f"as of {wc_data.get('up_to_month', '')}"],
        [f"Revenue Share ({revenue_share_pct}%)", fmt(net_revenue), ""],
        ["Avg per Bill", fmt(s.get("avg_per_bill")), ""],
        ["Total Guests", f"{s.get('total_guests', 0):,}", ""],
        ["Total Bills", f"{s.get('total_bills', 0):,}", ""],
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

    # Expense Breakdown
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

    # Working Capital Standing
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
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(wt)
        elements.append(Spacer(1, 10))

    # Footer
    elements.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY, spaceBefore=16))
    generated_at = datetime.now().strftime("%d %b %Y, %I:%M %p")
    elements.append(Paragraph(
        f"Generated on {generated_at} &nbsp;|&nbsp; Purnabramha Franchise Management System",
        small_style
    ))

    doc.build(elements)
    buf.seek(0)
    return buf
