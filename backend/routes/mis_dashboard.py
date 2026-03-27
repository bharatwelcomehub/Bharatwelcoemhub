# =======================================
# MIS Dashboard Routes
# Centralized analytics for sales, expenses, and alerts
# =======================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
import logging

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
    """Check if user has MIS Dashboard access (Super Admin, Admin, or Accounts role)"""
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
    
    if not (is_super_admin or is_admin or has_accounting):
        raise HTTPException(403, "Only Admin or Accounts users can access MIS Dashboard")
    
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
    
    # GST calculation (5% of total sales)
    total_gst = round(total_sales * 0.05, 2)
    
    # Expenses
    total_expenses = sum(float(e.get("amount", 0) or 0) for e in expenses_data)
    
    # Profit calculation: Sales - Expenses - GST
    profit = total_sales - total_expenses - total_gst
    profit_margin = round((profit / total_sales * 100) if total_sales > 0 else 0, 2)
    
    # Calculate totals - Previous Period
    prev_total_sales = sum(float(s.get("total_sale", 0) or 0) for s in prev_sales_data)
    prev_total_expenses = sum(float(e.get("amount", 0) or 0) for e in prev_expenses_data)
    prev_gst = round(prev_total_sales * 0.05, 2)
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
            centers_data[c] = {"sales": 0, "guests": 0, "bills": 0, "expenses": 0}
        centers_data[c]["sales"] += float(s.get("total_sale", 0) or 0)
        centers_data[c]["guests"] += int(s.get("num_guests", 0) or 0)
        centers_data[c]["bills"] += int(s.get("num_bills", 0) or 0)
    
    for e in expenses_data:
        c = e.get("center", "Unknown")
        if c not in centers_data:
            centers_data[c] = {"sales": 0, "guests": 0, "bills": 0, "expenses": 0}
        centers_data[c]["expenses"] += float(e.get("amount", 0) or 0)
    
    # Calculate profit for each center
    for c in centers_data:
        center_sales = centers_data[c]["sales"]
        center_expenses = centers_data[c]["expenses"]
        center_gst = round(center_sales * 0.05, 2)
        centers_data[c]["gst"] = center_gst
        centers_data[c]["profit"] = center_sales - center_expenses - center_gst
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
                grouped[date] = {"date": date, "sales": 0, "expenses": 0, "guests": 0}
            grouped[date]["sales"] += float(s.get("total_sale", 0) or 0)
            grouped[date]["guests"] += int(s.get("num_guests", 0) or 0)
        
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
                grouped[week_start] = {"week": week_start, "sales": 0, "expenses": 0}
            grouped[week_start]["sales"] += float(s.get("total_sale", 0) or 0)
        
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
                grouped[month] = {"month": month, "sales": 0, "expenses": 0}
            grouped[month]["sales"] += float(s.get("total_sale", 0) or 0)
        
        expenses_data = await db.expenses.find(query, {"_id": 0}).to_list(10000)
        for e in expenses_data:
            month = e.get("date", "2025-01-01")[:7]
            if month in grouped:
                grouped[month]["expenses"] += float(e.get("amount", 0) or 0)
        
        trends = sorted(grouped.values(), key=lambda x: x["month"])
    
    # Calculate profit for each period
    for t in trends:
        sales = t.get("sales", 0)
        expenses = t.get("expenses", 0)
        gst = round(sales * 0.05, 2)
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
            centers[c] = {"center": c, "sales": 0, "expenses": 0, "prev_sales": 0, "prev_expenses": 0}
        centers[c]["sales"] += float(s.get("total_sale", 0) or 0)
    
    for e in expenses_data:
        c = e.get("center", "Unknown")
        if c not in centers:
            centers[c] = {"center": c, "sales": 0, "expenses": 0, "prev_sales": 0, "prev_expenses": 0}
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
        c["gst"] = round(c["sales"] * 0.05, 2)
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
        gst = round(total_sales * 0.05, 2)
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
    custom_start = data.get("custom_start")
    custom_end = data.get("custom_end")
    
    session = await check_mis_access(token)
    
    start_date, end_date = get_period_dates(period, custom_start, custom_end)
    query = {"date": {"$gte": start_date, "$lte": end_date}}
    
    sales = await db.daily_sales.find(query, {"_id": 0}).to_list(10000)
    expenses = await db.expenses.find(query, {"_id": 0}).to_list(10000)
    
    centers = {}
    for s in sales:
        c = s.get("center", "Unknown")
        if c not in centers:
            centers[c] = {"center": c, "sales": 0, "expenses": 0}
        centers[c]["sales"] += float(s.get("total_sale", 0) or 0)
    
    for e in expenses:
        c = e.get("center", "Unknown")
        if c in centers:
            centers[c]["expenses"] += float(e.get("amount", 0) or 0)
    
    for c in centers.values():
        c["gst"] = round(c["sales"] * 0.05, 2)
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
    """Get working capital remaining (cumulative Sales - Expenses - GST) over time"""
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
    
    sales_data = await db.daily_sales.find(query, {"_id": 0}).to_list(10000)
    expenses_data = await db.expenses.find(query, {"_id": 0}).to_list(10000)
    
    # Group by date
    daily = {}
    for s in sales_data:
        date = s.get("date", "")
        if date not in daily:
            daily[date] = {"date": date, "sales": 0, "expenses": 0}
        daily[date]["sales"] += float(s.get("total_sale", 0) or 0)
    
    for e in expenses_data:
        date = e.get("date", "")
        if date not in daily:
            daily[date] = {"date": date, "sales": 0, "expenses": 0}
        daily[date]["expenses"] += float(e.get("amount", 0) or 0)
    
    # Sort by date and compute cumulative working capital
    sorted_days = sorted(daily.values(), key=lambda x: x["date"])
    
    cumulative = 0
    result = []
    for d in sorted_days:
        sales = d["sales"]
        expenses = d["expenses"]
        gst = round(sales * 0.05, 2)
        net = sales - expenses - gst
        cumulative += net
        result.append({
            "date": d["date"],
            "daily_sales": round(sales, 2),
            "daily_expenses": round(expenses, 2),
            "daily_gst": gst,
            "daily_net": round(net, 2),
            "working_capital": round(cumulative, 2)
        })
    
    return {"data": result, "total_working_capital": round(cumulative, 2)}
