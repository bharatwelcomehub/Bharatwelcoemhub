# =======================================
# Center Accounts Routes
# Financial Management, Commission Processing, PIB Generation
# =======================================

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from decimal import Decimal, ROUND_HALF_UP
import os
import io
import json
import logging
import tempfile
import pandas as pd

# PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/center-accounts", tags=["Center Accounts"])

# Database reference
db = None

def set_db(database):
    global db
    db = database

# Verify token function (will be set from main server)
verify_token = None
verify_token_async = None

def set_verify_token(func):
    global verify_token
    verify_token = func

def set_verify_token_async(func):
    global verify_token_async
    verify_token_async = func

# =======================================
# CONSTANTS & TAX RULES
# =======================================

# India Tax Rules
INDIA_GST_ON_SALES = 0.05  # 5% GST on food sales
INDIA_GST_ON_REVENUE_SHARE = 0.18  # 18% GST on revenue share invoice
INDIA_CGST = 0.09  # 9% CGST
INDIA_SGST = 0.09  # 9% SGST

# Australia Tax Rules
AUSTRALIA_GST_INCLUSIVE = 0.10  # 10% GST included in sale value
AUSTRALIA_GST_ON_PROFIT_SHARE = 0.10  # 10% GST on profit share

# MG (Minimum Guarantee) Calculation Constants
MG_INTEREST_RATE = 15  # 15% annual interest rate
MG_TENURE_YEARS = 7  # 7 years tenure

def calculate_mg(total_investment: float, setup_costs: dict, franchise_fee: float = 0, working_capital: float = 0) -> dict:
    """
    Calculate Minimum Guarantee (MG) based on Net Investment.
    
    Formula:
    - Net Investment = Total Investment - (Shop Rent Deposit + Staff Travel + 1st Salary + 1st Shop Rent + Working Capital + Franchise Fee)
    - MG = Monthly EMI based on Net Investment as loan amount @ 15% interest for 7 years
    
    EMI Formula: E = P × r × (1+r)^n / ((1+r)^n - 1)
    """
    if not total_investment or total_investment <= 0:
        return {
            "total_investment": 0,
            "deductions": {},
            "total_deductions": 0,
            "net_investment": 0,
            "monthly_mg": 0,
            "interest_rate": MG_INTEREST_RATE,
            "tenure_years": MG_TENURE_YEARS
        }
    
    shop_rent_deposit = float(setup_costs.get("shop_security_deposit", 0) or 0)
    staff_travel = float(setup_costs.get("staff_traveling_expense", 0) or 0)
    first_salary = float(setup_costs.get("initial_salary_fund", 0) or 0)
    first_shop_rent = float(setup_costs.get("first_month_rent", 0) or 0)
    
    # Include Franchise Fee and Working Capital as deductions
    franchise_fee_deduction = float(franchise_fee or 0)
    working_capital_deduction = float(working_capital or 0)
    
    deductions = {
        "shop_rent_deposit": shop_rent_deposit,
        "staff_traveling_expense": staff_travel,
        "first_salary": first_salary,
        "first_shop_rent": first_shop_rent,
        "working_capital": working_capital_deduction,
        "franchise_fee": franchise_fee_deduction
    }
    
    total_deductions = (shop_rent_deposit + staff_travel + first_salary + first_shop_rent +
                        working_capital_deduction + franchise_fee_deduction)
    net_investment = max(0, total_investment - total_deductions)
    
    # EMI calculation
    if net_investment <= 0:
        monthly_mg = 0
    else:
        P = net_investment
        annual_rate = MG_INTEREST_RATE / 100
        r = annual_rate / 12  # Monthly interest rate
        n = MG_TENURE_YEARS * 12  # Total months (84 months)
        
        if r > 0:
            monthly_mg = P * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
        else:
            monthly_mg = P / n
    
    return {
        "total_investment": round(total_investment, 2),
        "deductions": deductions,
        "total_deductions": round(total_deductions, 2),
        "net_investment": round(net_investment, 2),
        "monthly_mg": round(monthly_mg, 2),
        "interest_rate": MG_INTEREST_RATE,
        "tenure_years": MG_TENURE_YEARS
    }


async def calculate_working_capital_standing(db_ref, center_code: str, up_to_month: str, country: str = "India"):
    """
    Calculate Working Capital standing for the requested month.
    
    IMPORTANT: This function MUST produce the same Opening WC / Closing WC
    as `get_wc_table` for a given month so that the Standing card, MIS
    Dashboard, Owner Reports and the Month-by-Month Breakdown table all
    agree. We therefore use the same data sources and the same linear chain:
    
        closing_wc = opening_wc + pnl + wc_adj + topup
        pnl = sale - expenses - commission   (GST is M+1 expense, not Month-M P/L)
    
    Profit/loss restoration semantics:
        - Loss month → wc_used = abs(pnl)
        - Profit month with WC < base → wc_restored = min(pnl, base - opening_wc)
        - Profit month with WC ≥ base → distributable (revenue share path)
    """
    franchise = await get_franchise_for_center(center_code)
    base_wc = float(franchise.get("working_capital", 0) or 0) if franchise else 0
    
    # Check for initial WC override
    wc_override = await db_ref.wc_overrides.find_one(
        {"center": center_code, "month": {"$exists": False}},
        {"_id": 0}
    )
    if wc_override and wc_override.get("initial_wc") is not None:
        base_wc = float(wc_override["initial_wc"])
    
    # Get monthly sales
    sales_months = await db_ref.daily_sales.aggregate([
        {"$match": {"center": center_code, "date": {"$regex": r"^\d{4}-\d{2}"}}},
        {"$addFields": {"month": {"$substr": ["$date", 0, 7]}}},
        {"$group": {"_id": "$month", "total_sale": {"$sum": {"$ifNull": ["$total_sale", 0]}}}},
        {"$sort": {"_id": 1}}
    ]).to_list(200)
    
    # Get monthly expenses
    expense_months = await db_ref.expenses.aggregate([
        {"$match": {"center": center_code}},
        {"$addFields": {"month": {"$substr": ["$date", 0, 7]}}},
        {"$group": {"_id": "$month", "total_expense": {"$sum": {"$ifNull": ["$amount", 0]}}}},
        {"$sort": {"_id": 1}}
    ]).to_list(200)
    
    # Get monthly commissions — check multiple collections and field names
    # 1. monthly_commissions uses: other_deductions (platform commissions)
    commission_months_1 = await db_ref.monthly_commissions.aggregate([
        {"$match": {"center": center_code}},
        {"$group": {"_id": "$month", "total_commission": {"$sum": {
            "$add": [
                {"$ifNull": ["$commission_amount", 0]},
                {"$ifNull": ["$other_deductions", 0]},
                {"$ifNull": ["$gst_tax_deductions", 0]},
                {"$ifNull": ["$tds", 0]}
            ]
        }}}},
        {"$sort": {"_id": 1}}
    ]).to_list(200)
    
    # 2. commission_statements uses: commission_charged
    commission_months_2 = await db_ref.commission_statements.aggregate([
        {"$match": {"center": center_code}},
        {"$addFields": {"month": {"$substr": [{"$ifNull": ["$settlement_period_start", ""]}, 0, 7]}}},
        {"$group": {"_id": "$month", "total_commission": {"$sum": {"$ifNull": ["$commission_charged", 0]}}}},
        {"$sort": {"_id": 1}}
    ]).to_list(200)
    
    # Merge commission data from both sources
    commission_map = {}
    for c in commission_months_1:
        commission_map[c["_id"]] = commission_map.get(c["_id"], 0) + c["total_commission"]
    for c in commission_months_2:
        commission_map[c["_id"]] = commission_map.get(c["_id"], 0) + c["total_commission"]
    
    commission_months = [{"_id": m, "total_commission": v} for m, v in sorted(commission_map.items())]
    
    # Get monthly eligible base for GST (total - aggregators) and apply rate
    gst_months_raw = await db_ref.daily_sales.aggregate([
        {"$match": {"center": center_code, "date": {"$regex": r"^\d{4}-\d{2}"}}},
        {"$addFields": {
            "month": {"$substr": ["$date", 0, 7]},
            "_eligible": {
                "$max": [0, {"$subtract": [
                    {"$ifNull": ["$total_sale", 0]},
                    {"$add": [
                        {"$ifNull": ["$swiggy_sale", {"$ifNull": ["$swiggy", 0]}]},
                        {"$ifNull": ["$zomato_sale", {"$ifNull": ["$zomato", 0]}]},
                        {"$ifNull": ["$doordash_sale", {"$ifNull": ["$doordash", 0]}]},
                    ]}
                ]}]
            }
        }},
        {"$group": {"_id": "$month", "eligible_base": {"$sum": "$_eligible"}}},
        {"$sort": {"_id": 1}}
    ]).to_list(200)
    from utils.gst import gst_rate_for
    _rate_std = gst_rate_for(country, center_code)
    gst_months = [{"_id": g["_id"], "total_gst": round(float(g.get("eligible_base", 0)) * _rate_std, 2)} for g in gst_months_raw]
    
    # Get manual WC top-ups
    topups = await db_ref.wc_topups.find({"center": center_code}, {"_id": 0}).sort("date", 1).to_list(200)
    topup_by_month = {}
    for t in topups:
        m = t.get("month") or t.get("date", "")[:7]
        if m not in topup_by_month:
            topup_by_month[m] = 0
        topup_by_month[m] += float(t.get("amount", 0))
    
    # Other Income (memo) — non-operating cash inflow that adds to closing WC
    # so it flows into next month's opening balance. Stays OUT of P&L / Sales.
    try:
        from routes.other_income import get_other_income_by_month
        other_income_by_month = await get_other_income_by_month(center_code)
    except Exception:
        other_income_by_month = {}
    
    # Merge all months
    month_data = {}
    for s in sales_months:
        m = s["_id"]
        if m not in month_data:
            month_data[m] = {"sale": 0, "expenses": 0, "commission": 0, "gst": 0}
        month_data[m]["sale"] = s["total_sale"]
    for e in expense_months:
        m = e["_id"]
        if m not in month_data:
            month_data[m] = {"sale": 0, "expenses": 0, "commission": 0, "gst": 0}
        month_data[m]["expenses"] = e["total_expense"]
    for c in commission_months:
        m = c["_id"]
        if m not in month_data:
            month_data[m] = {"sale": 0, "expenses": 0, "commission": 0, "gst": 0}
        month_data[m]["commission"] = c["total_commission"]
    for g in gst_months:
        m = g["_id"]
        if m not in month_data:
            month_data[m] = {"sale": 0, "expenses": 0, "commission": 0, "gst": 0}
        month_data[m]["gst"] = g["total_gst"]
    
    # Per-month overrides (commission_target, gst_target, wc_adjustment)
    # — same precedence as get_wc_table.
    month_overrides_map = {}
    try:
        override_docs = await db_ref.wc_month_overrides.find(
            {"center": center_code}, {"_id": 0}
        ).to_list(500)
        for od in override_docs:
            om = od.get("month", "")
            if not om:
                continue
            month_overrides_map[om] = od
    except Exception:
        pass
    
    # Merge historical monthly summary (only months with no live data)
    try:
        hist_rows = await db_ref.historical_monthly_summary.find(
            {"center": center_code}, {"_id": 0}
        ).to_list(500)
        for h in hist_rows:
            m = h.get("month", "")
            if not m:
                continue
            has_live = m in month_data and (
                month_data[m].get("sale", 0) > 0 or month_data[m].get("expenses", 0) > 0
            )
            if has_live:
                continue
            month_data.setdefault(m, {"sale": 0, "expenses": 0, "commission": 0, "gst": 0})
            month_data[m]["sale"] = float(h.get("sale", 0) or 0)
            month_data[m]["expenses"] = float(h.get("expenses", 0) or 0)
    except Exception:
        pass
    
    # Merge historical_pib GST values (display only — does not change chain
    # since GST is not subtracted from P&L). Keep parity with get_wc_table.
    try:
        pib_rows = await db_ref.historical_pib.find(
            {"center": center_code}, {"_id": 0}
        ).to_list(500)
        for p in pib_rows:
            m = p.get("month", "")
            if not m:
                continue
            month_data.setdefault(m, {"sale": 0, "expenses": 0, "commission": 0, "gst": 0})
            gst_from_pib = float(p.get("total_gst_on_revenue", 0) or 0)
            if gst_from_pib > 0 and month_data[m].get("gst", 0) == 0:
                month_data[m]["gst"] = gst_from_pib
    except Exception:
        pass
    
    # Cap at franchise effective end (same as get_wc_table)
    try:
        effective_end = get_franchise_effective_end_month(franchise)
    except Exception:
        effective_end = up_to_month
    
    sorted_months = sorted(m for m in month_data.keys() if m <= effective_end)
    
    # Linear chain — IDENTICAL to get_wc_table semantics
    current_wc = base_wc
    cumulative_wc_used = 0.0
    cumulative_wc_restored = 0.0
    
    this_month_data = {
        "opening_wc": base_wc, "sales": 0, "expenses": 0, "commission": 0, "gst": 0,
        "operational_balance": 0, "wc_used": 0, "wc_restored": 0, "topup": 0,
        "closing_wc": base_wc, "revenue_share_blocked": False
    }
    
    WC_THRESHOLD = 50  # 50% protection threshold
    
    for month in sorted_months:
        d = month_data[month]
        sale = float(d.get("sale", 0) or 0)
        expenses = float(d.get("expenses", 0) or 0)
        commission_src = float(d.get("commission", 0) or 0)
        gst_src = float(d.get("gst", 0) or 0)
        
        override = month_overrides_map.get(month, {})
        commission = float(override["commission_target"]) if override.get("commission_target") is not None else commission_src
        gst = float(override["gst_target"]) if override.get("gst_target") is not None else gst_src
        wc_adj = float(override.get("wc_adjustment", 0) or 0)
        
        opening_wc_for_month = current_wc
        
        # P&L: sale - expenses - commission (GST excluded — paid as M+1 expense)
        pnl = sale - expenses - commission
        
        # Linear chain: closing = opening + pnl + wc_adj + topup + other_income
        # Other Income is non-operating cash IN (loan-taken auto, vendor refund,
        # franchisee repayment, etc.) — does NOT affect P&L / Sales / MG / Revenue
        # Share, but DOES boost closing WC so it carries to next month's opening.
        topup_amount = topup_by_month.get(month, 0)
        oi_amount = other_income_by_month.get(month, 0)
        closing_for_month = opening_wc_for_month + pnl + wc_adj + topup_amount + oi_amount
        
        # Tracking metrics for the requested month only
        month_wc_used = 0.0
        month_wc_restored = 0.0
        if pnl < 0:
            month_wc_used = abs(pnl)
        elif pnl > 0:
            if opening_wc_for_month < base_wc:
                month_wc_restored = min(pnl, base_wc - opening_wc_for_month)
        
        cumulative_wc_used += month_wc_used
        cumulative_wc_restored += month_wc_restored
        
        current_wc = closing_for_month
        
        if month == up_to_month:
            wc_pct = (closing_for_month / base_wc * 100) if base_wc > 0 else 100
            this_month_data = {
                "opening_wc": round(opening_wc_for_month, 2),
                "sales": round(sale, 2),
                "expenses": round(expenses, 2),
                "commission": round(commission, 2),
                "gst": round(gst, 2),
                "operational_balance": round(pnl, 2),
                "wc_used": round(month_wc_used, 2),
                "wc_restored": round(month_wc_restored, 2),
                "topup": round(topup_amount, 2),
                "other_income": round(oi_amount, 2),
                "wc_adjustment": round(wc_adj, 2),
                "closing_wc": round(closing_for_month, 2),
                "revenue_share_blocked": base_wc > 0 and wc_pct <= WC_THRESHOLD,
            }
    
    # Fallback: if requested month has no data row, use the running chain
    # value so the Opening WC matches what get_wc_table would show for the
    # next month (i.e. previous month's closing carries forward).
    if up_to_month not in sorted_months:
        wc_pct_fallback = (current_wc / base_wc * 100) if base_wc > 0 else 100
        this_month_data = {
            "opening_wc": round(current_wc, 2),
            "sales": 0, "expenses": 0, "commission": 0, "gst": 0,
            "operational_balance": 0, "wc_used": 0, "wc_restored": 0, "topup": 0,
            "wc_adjustment": 0,
            "closing_wc": round(current_wc, 2),
            "revenue_share_blocked": base_wc > 0 and wc_pct_fallback <= WC_THRESHOLD,
        }
    
    # Loans outstanding (cap at requested month, not effective_end)
    year, mo = map(int, up_to_month.split("-"))
    if mo == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{mo + 1:02d}-01"
    
    loan_entries = await db_ref.loan_entries.find(
        {"center": center_code, "status": {"$ne": "fully_repaid"}, "loan_date": {"$lte": end_date}},
        {"_id": 0}
    ).to_list(100)
    total_loans_outstanding = sum(
        (loan.get("amount", 0) - loan.get("total_repaid", 0))
        for loan in loan_entries
    )
    
    # WC Status Determination — based on the requested month's closing WC
    target_closing = this_month_data["closing_wc"]
    wc_percentage = (target_closing / base_wc * 100) if base_wc > 0 else 100
    revenue_share_active = True
    wc_status = "healthy"
    
    if base_wc > 0:
        if wc_percentage <= WC_THRESHOLD:
            revenue_share_active = False
            wc_status = "protection"
        elif target_closing < base_wc:
            revenue_share_active = False
            wc_status = "restoring"
    
    return {
        "base_wc": round(base_wc, 2),
        "initial_security_deposit": round(base_wc, 2),
        "opening_wc": this_month_data["opening_wc"],
        "this_month_sales": this_month_data["sales"],
        "this_month_expenses": this_month_data["expenses"],
        "this_month_commissions": this_month_data["commission"],
        "this_month_gst": this_month_data["gst"],
        "this_month_operational_balance": this_month_data["operational_balance"],
        "this_month_pnl": this_month_data["operational_balance"],
        "this_month_wc_used": this_month_data["wc_used"],
        "this_month_wc_restored": this_month_data["wc_restored"],
        "this_month_topup": this_month_data["topup"],
        "closing_wc": round(target_closing, 2),
        "diff_from_initial": round(target_closing - base_wc, 2),
        "cumulative_wc_used": round(cumulative_wc_used, 2),
        "cumulative_wc_restored": round(cumulative_wc_restored, 2),
        "loan_from_wc_deficit": 0,
        "loans_outstanding": round(total_loans_outstanding, 2),
        "total_effective_loans": round(total_loans_outstanding, 2),
        "available_capital": round(target_closing - total_loans_outstanding, 2),
        "wc_utilised": round(max(0, base_wc - target_closing), 2) if base_wc > 0 else 0,
        "wc_percentage": round(wc_percentage, 2),
        "wc_status": wc_status,
        "revenue_share_active": revenue_share_active,
        "wc_threshold": WC_THRESHOLD,
        "current_month_pnl": this_month_data["operational_balance"],
        "current_month_sales": this_month_data["sales"],
        "current_month_expenses": this_month_data["expenses"],
    }


# =======================================
# WC TABLE ENDPOINT - Simplified Working Capital Assessment
# P/L = Sales - (Expenses + Commission)
# Losses deduct from WC; Profits do NOT auto-add
# =======================================

@router.post("/wc-table")
async def get_wc_table(req: dict = Body(...)):
    """
    Working Capital Assessment:
    - P/L = Total Sales - (Total Expenses + Total Commission)
    - Closing WC = Opening WC + P/L (both profits and losses apply)
    - Manual top-ups increase WC (with audit trail)
    - Revenue Share stops if WC <= 50% of initial
    """
    token = req.get("token")
    center = req.get("center", "").upper()
    
    session = await check_access(token)
    
    # Get franchise for initial WC
    franchise = await get_franchise_for_center(center)
    initial_wc = float(franchise.get("working_capital", 0) or 0) if franchise else 0
    
    # Check for initial WC override
    wc_override = await db.wc_overrides.find_one(
        {"center": center, "month": {"$exists": False}},
        {"_id": 0}
    )
    if wc_override and wc_override.get("initial_wc") is not None:
        initial_wc = float(wc_override["initial_wc"])
    
    # Get monthly sales
    sales_months = await db.daily_sales.aggregate([
        {"$match": {"center": center, "date": {"$regex": r"^\d{4}-\d{2}"}}},
        {"$addFields": {"month": {"$substr": ["$date", 0, 7]}}},
        {"$group": {"_id": "$month", "total_sale": {"$sum": {"$ifNull": ["$total_sale", 0]}}}},
        {"$sort": {"_id": 1}}
    ]).to_list(200)
    
    # Get monthly expenses
    expense_months = await db.expenses.aggregate([
        {"$match": {"center": center}},
        {"$addFields": {"month": {"$substr": ["$date", 0, 7]}}},
        {"$group": {"_id": "$month", "total_expense": {"$sum": {"$ifNull": ["$amount", 0]}}}},
        {"$sort": {"_id": 1}}
    ]).to_list(200)
    
    # Get monthly commissions — check both collections with correct field names
    commission_months_1 = await db.monthly_commissions.aggregate([
        {"$match": {"center": center}},
        {"$group": {"_id": "$month", "total_commission": {"$sum": {
            "$add": [
                {"$ifNull": ["$commission_amount", 0]},
                {"$ifNull": ["$other_deductions", 0]},
                {"$ifNull": ["$gst_tax_deductions", 0]},
                {"$ifNull": ["$tds", 0]}
            ]
        }}}},
        {"$sort": {"_id": 1}}
    ]).to_list(200)
    
    commission_months_2 = await db.commission_statements.aggregate([
        {"$match": {"center": center}},
        {"$addFields": {"month": {"$substr": [{"$ifNull": ["$settlement_period_start", ""]}, 0, 7]}}},
        {"$group": {"_id": "$month", "total_commission": {"$sum": {"$ifNull": ["$commission_charged", 0]}}}},
        {"$sort": {"_id": 1}}
    ]).to_list(200)
    
    commission_map = {}
    for c in commission_months_1:
        commission_map[c["_id"]] = commission_map.get(c["_id"], 0) + c["total_commission"]
    for c in commission_months_2:
        commission_map[c["_id"]] = commission_map.get(c["_id"], 0) + c["total_commission"]
    commission_months = [{"_id": m, "total_commission": v} for m, v in sorted(commission_map.items())]
    
    # Get monthly eligible base for GST: (total_sale - swiggy - zomato - doordash)
    # Rate is applied below based on center country (India 5%, Perth 10%).
    gst_months_raw = await db.daily_sales.aggregate([
        {"$match": {"center": center, "date": {"$regex": r"^\d{4}-\d{2}"}}},
        {"$addFields": {
            "month": {"$substr": ["$date", 0, 7]},
            "_eligible": {
                "$max": [0, {"$subtract": [
                    {"$ifNull": ["$total_sale", 0]},
                    {"$add": [
                        {"$ifNull": ["$swiggy_sale", {"$ifNull": ["$swiggy", 0]}]},
                        {"$ifNull": ["$zomato_sale", {"$ifNull": ["$zomato", 0]}]},
                        {"$ifNull": ["$doordash_sale", {"$ifNull": ["$doordash", 0]}]},
                    ]}
                ]}]
            }
        }},
        {"$group": {"_id": "$month", "eligible_base": {"$sum": "$_eligible"}}},
        {"$sort": {"_id": 1}}
    ]).to_list(200)
    from utils.gst import gst_rate_for
    _rate = gst_rate_for(None, center)
    gst_months = [{"_id": g["_id"], "total_gst": round(float(g.get("eligible_base", 0)) * _rate, 2)} for g in gst_months_raw]
    
    # Get manual WC top-ups (audit log)
    topups = await db.wc_topups.find(
        {"center": center},
        {"_id": 0}
    ).sort("date", 1).to_list(200)
    
    # Index top-ups by month
    topup_by_month = {}
    for t in topups:
        m = t.get("month") or t.get("date", "")[:7]
        if m not in topup_by_month:
            topup_by_month[m] = 0
        topup_by_month[m] += float(t.get("amount", 0))
    
    # Other Income per month — non-operating cash that boosts closing WC
    try:
        from routes.other_income import get_other_income_by_month
        other_income_by_month = await get_other_income_by_month(center)
    except Exception:
        other_income_by_month = {}
    
    # Merge all months
    month_data = {}
    for s in sales_months:
        m = s["_id"]
        if m not in month_data:
            month_data[m] = {"sale": 0, "expenses": 0, "commission": 0, "gst": 0}
        month_data[m]["sale"] = s["total_sale"]
    
    for e in expense_months:
        m = e["_id"]
        if m not in month_data:
            month_data[m] = {"sale": 0, "expenses": 0, "commission": 0, "gst": 0}
        month_data[m]["expenses"] = e["total_expense"]
    
    for c in commission_months:
        m = c["_id"]
        if m not in month_data:
            month_data[m] = {"sale": 0, "expenses": 0, "commission": 0, "gst": 0}
        month_data[m]["commission"] = c["total_commission"]
    
    for g in gst_months:
        m = g["_id"]
        if m not in month_data:
            month_data[m] = {"sale": 0, "expenses": 0, "commission": 0, "gst": 0}
        month_data[m]["gst"] = g["total_gst"]
    
    # Merge historical monthly summary rows (from Excel imports). Only fill in
    # months that have no daily sale/expense in the database so we never
    # double-count live operational data.
    try:
        hist_rows = await db.historical_monthly_summary.find(
            {"center": center}, {"_id": 0}
        ).to_list(500)
        for h in hist_rows:
            m = h.get("month", "")
            if not m:
                continue
            has_live = m in month_data and (
                month_data[m].get("sale", 0) > 0 or month_data[m].get("expenses", 0) > 0
            )
            if has_live:
                continue
            month_data.setdefault(m, {"sale": 0, "expenses": 0, "commission": 0, "gst": 0})
            month_data[m]["sale"] = float(h.get("sale", 0) or 0)
            month_data[m]["expenses"] = float(h.get("expenses", 0) or 0)
            # historical rows don't carry separate commission/gst — already
            # netted into P/L in the source file. Keep commission/gst at 0 so
            # our P/L formula (sale - expenses - comm) matches the source.
            month_data[m]["_from_history"] = True
    except Exception as hx:
        logger.warning(f"WC history merge failed for {center}: {hx}")
    
    # Merge historical_pib rollups (from monthly Excel imports). If the month
    # has PIB data, use SGST+CGST as GST (source of truth for the month).
    # Do NOT overwrite existing non-zero gst (from daily_sales.gst_amount).
    try:
        pib_rows = await db.historical_pib.find(
            {"center": center}, {"_id": 0}
        ).to_list(500)
        for p in pib_rows:
            m = p.get("month", "")
            if not m:
                continue
            month_data.setdefault(m, {"sale": 0, "expenses": 0, "commission": 0, "gst": 0})
            gst_from_pib = float(p.get("total_gst_on_revenue", 0) or 0)
            if gst_from_pib > 0 and month_data[m].get("gst", 0) == 0:
                month_data[m]["gst"] = gst_from_pib
    except Exception as px:
        logger.warning(f"WC PIB merge failed for {center}: {px}")
    
    if not month_data:
        return {
            "success": True, "rows": [], "initial_wc": initial_wc, "center": center,
            "current_wc": initial_wc, "revenue_share_status": "active",
            "last_topup": None, "topup_log": topups
        }
    
    sorted_months = sorted(month_data.keys())
    
    # Cap months at franchise effective end date (prevent endless future months)
    effective_end = get_franchise_effective_end_month(franchise)
    sorted_months = [m for m in sorted_months if m <= effective_end]
    
    # Get per-month overrides (manual expense/WC adjustments)
    month_overrides = {}
    override_docs = await db.wc_month_overrides.find({"center": center}, {"_id": 0}).to_list(200)
    for od in override_docs:
        month_overrides[od.get("month", "")] = od
    
    if not sorted_months:
        return {
            "success": True, "rows": [], "initial_wc": initial_wc, "center": center,
            "current_wc": initial_wc, "revenue_share_status": "active",
            "last_topup": None, "topup_log": topups
        }
    
    # Build rows: Balance WC = Opening WC + P/L, chains forward
    rows = []
    current_balance_wc = initial_wc  # First month Opening WC = Base WC
    
    for month in sorted_months:
        d = month_data[month]
        sale = round(d["sale"], 2)
        expenses = round(d["expenses"], 2)
        commission_src = round(d["commission"], 2)
        gst_src = round(d.get("gst", 0), 2)
        
        # Apply manual expense adjustment if any (audit trail only — the
        # actual adjustment is represented by a real INTRA CENTER ADJUSTMENT
        # row in db.expenses which is already captured in `expenses` above,
        # so we MUST NOT add it again here or we will double-count.)
        override = month_overrides.get(month, {})
        expense_adj = round(float(override.get("expense_adjustment", 0)), 2)
        wc_adj = round(float(override.get("wc_adjustment", 0)), 2)
        
        # Final expenses = DB expenses (already includes any INTRA adjustment row)
        final_expenses = expenses
        # Non-INTRA portion of the DB expenses (what the user can edit against)
        real_expenses = round(expenses - expense_adj, 2) if expense_adj else expenses
        
        # Commission / GST: show override target if the user explicitly set one
        # for that month; otherwise fall back to the source aggregate.
        commission_override = override.get("commission_target")
        gst_override = override.get("gst_target")
        commission = round(float(commission_override), 2) if commission_override is not None else commission_src
        gst = round(float(gst_override), 2) if gst_override is not None else gst_src
        
        # P/L = Sale - Expenses - Commission
        # GST column is shown for visibility but NOT subtracted — GST liability
        # for Month M is paid as an expense in Month M+1 (see gst_liabilities
        # flow), so deducting it here would double-count it.
        pnl = round(sale - final_expenses - commission, 2)
        
        # Opening WC = previous month's Balance WC (first month = Base WC)
        opening_wc = round(current_balance_wc, 2)
        
        # Balance WC = Opening WC + P/L + any manual WC adjustment
        balance_wc = round(opening_wc + pnl + wc_adj, 2)
        
        # Apply top-ups
        topup_amount = round(topup_by_month.get(month, 0), 2)
        if topup_amount != 0:
            balance_wc = round(balance_wc + topup_amount, 2)
        
        # Apply Other Income (non-operating cash inflow — adds to closing WC,
        # carries forward as next month's opening balance, but stays OUT of P&L)
        oi_amount = round(other_income_by_month.get(month, 0), 2)
        if oi_amount != 0:
            balance_wc = round(balance_wc + oi_amount, 2)
        
        # Diff of WC = Balance WC - Base WC (or same as Balance WC per your sheet)
        diff_wc = round(balance_wc, 2)
        
        # Revenue share status based on balance_wc vs initial
        wc_pct = (balance_wc / initial_wc * 100) if initial_wc > 0 else 100
        
        if initial_wc > 0 and balance_wc < initial_wc:
            if balance_wc <= initial_wc * 0.5:
                rev_share_status = "blocked"
            else:
                rev_share_status = "restoring"
        else:
            rev_share_status = "active"
        
        rows.append({
            "month": month,
            "sale": sale,
            "expenses": final_expenses,
            "expenses_db": real_expenses,
            "expense_adjustment": expense_adj,
            "commission": commission,
            "gst": gst,
            "pnl": pnl,
            "operational_balance": pnl,
            "opening_wc": opening_wc,
            "wc_adjustment": wc_adj,
            "topup": topup_amount,
            "other_income": oi_amount,
            "balance_wc": balance_wc,
            "closing_wc": balance_wc,
            "diff_wc": diff_wc,
            "wc_percentage": round(wc_pct, 1),
            "rev_share_status": rev_share_status,
        })
        
        # Chain: next month's opening = this month's balance
        current_balance_wc = balance_wc
    
    # Get last topup for summary
    last_topup = topups[-1] if topups else None
    
    # Current overall revenue share status
    final_wc = rows[-1]["balance_wc"] if rows else initial_wc
    final_pct = (final_wc / initial_wc * 100) if initial_wc > 0 else 100
    if initial_wc > 0 and final_wc < initial_wc:
        final_status = "blocked" if final_pct <= 50 else "restoring"
    else:
        final_status = "active"
    
    return {
        "success": True,
        "rows": rows,
        "initial_wc": initial_wc,
        "base_wc": initial_wc,
        "current_wc": final_wc,
        "wc_percentage": round(final_pct, 1),
        "center": center,
        "revenue_share_status": final_status,
        "last_topup": last_topup,
        "topup_log": topups,
        "effective_end_month": effective_end
    }


@router.post("/wc-topup")
async def add_wc_topup(req: dict = Body(...)):
    """
    Manual WC top-up / reset with audit log.
    Used for fund infusions, adjustments, etc.
    """
    token = req.get("token")
    center = req.get("center", "").upper()
    amount = req.get("amount")
    reason = req.get("reason", "")
    month = req.get("month", "")  # YYYY-MM
    
    session = await check_access(token)
    
    if amount is None:
        raise HTTPException(400, "Amount is required")
    
    amount = float(amount)
    
    topup_record = {
        "center": center,
        "amount": amount,
        "reason": reason,
        "month": month or datetime.now(timezone.utc).strftime("%Y-%m"),
        "date": datetime.now(timezone.utc).isoformat(),
        "added_by": session.get("managerName", session.get("mobile", "unknown")),
        "mobile": session.get("mobile", ""),
    }
    
    await db.wc_topups.insert_one(topup_record)
    del topup_record["_id"]  # Remove ObjectId before response
    
    logger.info(f"WC top-up for {center}: {amount} ({reason}) by {topup_record['added_by']}")
    
    return {
        "success": True,
        "message": f"WC top-up of {amount} added for {center}",
        "topup": topup_record
    }


@router.post("/wc-override")
async def set_wc_override(req: dict = Body(...)):
    """Set/update initial WC value for a center."""
    token = req.get("token")
    center = req.get("center", "").upper()
    value = req.get("value")
    
    session = await check_access(token)
    
    if value is None:
        raise HTTPException(400, "Value is required")
    
    value = float(value)
    
    await db.wc_overrides.update_one(
        {"center": center, "month": {"$exists": False}},
        {"$set": {
            "center": center,
            "initial_wc": value,
            "updated_by": session.get("mobile", "unknown"),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    logger.info(f"Initial WC set for {center}: {value}")
    return {"success": True, "message": f"Initial WC set for {center}: {value}"}


@router.post("/wc-row-save")
async def save_wc_row_override(req: dict = Body(...)):
    """Save manual expense/WC adjustment for a specific month in the WC table.

    Accepted body (any combination):
      - target_expenses (float): user-entered absolute monthly total expense.
        Backend will compute the delta against real (non-INTRA) db.expenses
        for that center+month and create a single mirrored
        "INTRA CENTER ADJUSTMENT" row in db.expenses dated on the LAST day
        of the month. Existing INTRA row for that month (if any) is replaced.
      - expense_adjustment (float, legacy/direct): absolute delta to record.
      - wc_adjustment (float): manual WC override (no db.expenses side effect).
    """
    import calendar as _calendar
    token = req.get("token")
    center = req.get("center", "").upper()
    month = req.get("month", "")
    
    session = await check_access(token)
    
    if not month or not center:
        raise HTTPException(400, "center and month are required")
    
    now = datetime.now(timezone.utc).isoformat()
    user = session.get("managerName", "Unknown")
    intra_id = f"INTRA-{center}-{month}"
    
    # Resolve the delta (expense_adj). target_expenses (absolute) takes precedence.
    expense_adj = None
    if req.get("target_expenses") is not None:
        target = float(req["target_expenses"])
        # Compute REAL (non-INTRA) db.expenses total for that center+month
        agg = await db.expenses.aggregate([
            {"$match": {
                "center": center,
                "date": {"$regex": f"^{month}"},
                "$or": [
                    {"intra_entry_id": {"$exists": False}},
                    {"intra_entry_id": {"$ne": intra_id}}
                ]
            }},
            {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$amount", 0]}}}}
        ]).to_list(1)
        real_total = float(agg[0]["total"]) if agg else 0.0
        expense_adj = round(target - real_total, 2)
    elif req.get("expense_adjustment") is not None:
        expense_adj = float(req["expense_adjustment"])
    
    # Build override audit doc
    update = {
        "center": center,
        "month": month,
        "updated_by": user,
        "updated_at": now,
    }
    if expense_adj is not None:
        update["expense_adjustment"] = expense_adj
        if req.get("target_expenses") is not None:
            update["target_expenses"] = float(req["target_expenses"])
    if req.get("wc_adjustment") is not None:
        update["wc_adjustment"] = float(req["wc_adjustment"])
    if req.get("commission_target") is not None:
        update["commission_target"] = float(req["commission_target"])
    if req.get("gst_target") is not None:
        update["gst_target"] = float(req["gst_target"])
    
    await db.wc_month_overrides.update_one(
        {"center": center, "month": month},
        {"$set": update},
        upsert=True
    )
    
    # Replace INTRA expense row for this month. Dated LAST day of month.
    if expense_adj is not None:
        # Always delete the existing INTRA row to keep at most one per month
        await db.expenses.delete_many({
            "center": center,
            "expense_type": "INTRA CENTER ADJUSTMENT",
            "intra_entry_id": intra_id
        })
        
        # Only insert when the delta is non-zero. Negative allowed (target < real).
        if abs(expense_adj) > 0.01:
            try:
                yy, mm = int(month[:4]), int(month[5:7])
                last_day = _calendar.monthrange(yy, mm)[1]
                expense_date = f"{month}-{last_day:02d}"
            except Exception:
                expense_date = f"{month}-28"
            
            await db.expenses.insert_one({
                "center": center,
                "date": expense_date,
                "expense_type": "INTRA CENTER ADJUSTMENT",
                "description": f"WC Table adjustment for {month}",
                "amount": round(expense_adj, 2),
                "payment_mode": "ADJUSTMENT",
                "intra_entry_id": intra_id,
                "created_by": user,
                "created_at": now,
                "updated_at": now,
                "source": "wc_table"
            })
            logger.info(f"INTRA expense row {intra_id} amount={expense_adj} on {expense_date}")
        else:
            logger.info(f"INTRA expense row {intra_id} cleared (adjustment=0)")
    
    return {"success": True, "message": f"WC row saved for {center} {month}", "expense_adjustment": expense_adj}


@router.post("/wc-table/export-pdf")
async def export_wc_table_pdf(req: dict = Body(...)):
    """Export WC table as PDF with Purnabramha branding."""
    from utils.pdf_generator import build_wc_table_pdf
    token = req.get("token")
    session = await check_access(token)
    center = (req.get("center") or "").upper()
    if not center:
        raise HTTPException(400, "center required")

    wc_data = await get_wc_table(req)
    franchise = await get_franchise_for_center(center)
    try:
        center_doc = await db.centers.find_one({"code": center}, {"_id": 0})
        center_info = center_doc or {}
    except Exception:
        center_info = {}

    pdf_bytes = build_wc_table_pdf(
        center=center, center_info=center_info, franchise=franchise,
        wc_data=wc_data, manager_name=session.get("managerName", "System"),
    )
    filename = f"WC_Statement_{center}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/wc-table/export-excel")
async def export_wc_table_excel(req: dict = Body(...)):
    """Export WC table as Excel."""
    from utils.pdf_generator import build_wc_table_excel
    token = req.get("token")
    await check_access(token)
    center = (req.get("center") or "").upper()
    if not center:
        raise HTTPException(400, "center required")

    wc_data = await get_wc_table(req)
    franchise = await get_franchise_for_center(center)
    xlsx_bytes = build_wc_table_excel(center=center, franchise=franchise, wc_data=wc_data)
    filename = f"WC_Statement_{center}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Colors for PDF
BRAND_MAROON = colors.HexColor("#800020")
BRAND_GOLD = colors.HexColor("#C9A227")
BRAND_NAVY = colors.HexColor("#1a365d")
DARK_GRAY = colors.HexColor("#374151")
LIGHT_GRAY = colors.HexColor("#f3f4f6")

# =======================================
# PYDANTIC MODELS
# =======================================

class AccountPeriodRequest(BaseModel):
    token: str
    center: str
    month: str  # YYYY-MM format
    year: Optional[int] = None

class PIBGenerateRequest(BaseModel):
    token: str
    center: str
    month: str  # YYYY-MM format

# =======================================
# HELPER FUNCTIONS
# =======================================

async def check_access(token: str):
    """Verify token and return session"""
    if not token:
        raise HTTPException(401, "Authentication required")
    
    session = await db.sessions.find_one({"token": token}, {"_id": 0})
    if not session:
        raise HTTPException(401, "Invalid or expired session")
    
    return session


def _is_staff(session: dict) -> bool:
    """Staff = Super Admin, Admin, Accountant (all-centers access)."""
    if not session:
        return False
    if session.get("is_super_admin") or session.get("is_admin"):
        return True
    role_key = (session.get("role_key") or "").lower()
    if role_key in ("super_admin", "admin", "accountant"):
        return True
    roles = session.get("roles") or {}
    if roles.get("accounts") or roles.get("reports") or roles.get("mis") or roles.get("accounting"):
        return True
    return False


async def enforce_owner_visibility(session: dict, center: str, month: str):
    """Block report downloads for Franchise Owners unless the month has been
    released via /api/owner-reports/set-visibility.
    Staff (SA/Admin/Accountant) are never blocked."""
    if _is_staff(session):
        return
    vis = await db.owner_report_visibility.find_one(
        {"center": center, "month": month}, {"_id": 0}
    )
    if not (vis and vis.get("ready")):
        raise HTTPException(
            403,
            "This month has not yet been released by the Accounts team. "
            "Please contact the Accounts team to approve the month for viewing.",
        )

async def get_center_details(center_code: str):
    """Get center details with country info"""
    center = await db.centers.find_one({"code": center_code}, {"_id": 0})
    if not center:
        raise HTTPException(404, f"Center {center_code} not found")
    return center

async def get_franchise_for_center(center_code: str):
    """Get linked franchise for a center"""
    center = await db.centers.find_one({"code": center_code}, {"_id": 0})
    if not center:
        return None    
    # Check if center has franchise_code
    franchise_code = center.get("franchise_code")
    if franchise_code:
        franchise = await db.franchises.find_one({"franchise_code": franchise_code}, {"_id": 0})
        if franchise:
            return franchise
    
    # Fallback: Try to match by city/location from center code or center city
    city = center.get("city", "").lower()
    center_code_lower = center_code.lower()
    
    # Build search terms from center code (e.g., PB-TH → "th", PB-PERTH → "perth", PB-HSR → "hsr")
    code_suffix = center_code.split("-")[-1].lower() if "-" in center_code else center_code_lower
    
    # Try matching franchise by city field
    search_terms = [t for t in [city, code_suffix] if t and len(t) >= 2]
    for term in search_terms:
        franchise = await db.franchises.find_one(
            {"city": {"$regex": term, "$options": "i"}, "status": {"$ne": "Deleted"}},
            {"_id": 0}
        )
        if franchise:
            return franchise
    
    # Try matching by franchise_name containing the center code suffix
    for term in search_terms:
        franchise = await db.franchises.find_one(
            {"franchise_name": {"$regex": term, "$options": "i"}, "status": {"$ne": "Deleted"}},
            {"_id": 0}
        )
        if franchise:
            return franchise
    
    return None

def get_franchise_effective_end_month(franchise: dict) -> str:
    """
    Calculate the effective end month for a franchise.
    Returns YYYY-MM string representing the last valid month for data display.
    Rules:
    - Active franchise: cap at current month
    - Closed/exited franchise: cap at earliest of (closure_date, agreement_end_date)
    - Always cap at current month (never show future months)
    """
    now_month = datetime.now().strftime("%Y-%m")
    
    if not franchise:
        return now_month
    
    candidates = [now_month]
    
    # Check closure_date
    closure = franchise.get("closure_date")
    if closure:
        try:
            if "T" in str(closure):
                dt = datetime.fromisoformat(str(closure).replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(str(closure)[:10], "%Y-%m-%d")
            candidates.append(dt.strftime("%Y-%m"))
        except:
            pass
    
    # Check agreement_end_date
    end_date = franchise.get("agreement_end_date")
    if end_date:
        try:
            dt = datetime.strptime(str(end_date)[:10], "%Y-%m-%d")
            candidates.append(dt.strftime("%Y-%m"))
        except:
            pass
    
    # Return the earliest valid end month (never exceed current month)
    return min(candidates)


def get_country_from_center(center: dict) -> str:
    """Determine country from center data"""
    country = center.get("country", "").lower()
    if "australia" in country or not center.get("is_india_center", True):
        return "Australia"
    return "India"

def calculate_taxes(amount: float, country: str, tax_type: str = "sales") -> dict:
    """Calculate taxes based on country rules"""
    result = {
        "base_amount": amount,
        "gst_amount": 0,
        "cgst": 0,
        "sgst": 0,
        "total_with_gst": amount
    }
    
    if country == "Australia":
        if tax_type == "sales":
            # GST is inclusive in Australia - extract GST from total
            gst = amount * AUSTRALIA_GST_INCLUSIVE / (1 + AUSTRALIA_GST_INCLUSIVE)
            result["gst_amount"] = round(gst, 2)
            result["base_amount"] = round(amount - gst, 2)
            result["total_with_gst"] = amount
        elif tax_type == "profit_share":
            # Add 10% GST on profit share
            gst = amount * AUSTRALIA_GST_ON_PROFIT_SHARE
            result["gst_amount"] = round(gst, 2)
            result["total_with_gst"] = round(amount + gst, 2)
    else:  # India
        if tax_type == "sales":
            # 5% GST on food sales
            gst = amount * INDIA_GST_ON_SALES
            result["gst_amount"] = round(gst, 2)
            result["total_with_gst"] = round(amount + gst, 2)
        elif tax_type == "revenue_share":
            # 18% GST (9% CGST + 9% SGST) on revenue share
            cgst = amount * INDIA_CGST
            sgst = amount * INDIA_SGST
            result["cgst"] = round(cgst, 2)
            result["sgst"] = round(sgst, 2)
            result["gst_amount"] = round(cgst + sgst, 2)
            result["total_with_gst"] = round(amount + cgst + sgst, 2)
    
    return result

# =======================================
# ACCOUNT SUMMARY ENDPOINT
# =======================================

@router.post("/summary")
async def get_center_account_summary(req: AccountPeriodRequest):
    """Get comprehensive account summary for a center"""
    session = await check_access(req.token)
    
    center = await get_center_details(req.center)
    country = get_country_from_center(center)
    franchise = await get_franchise_for_center(req.center)
    
    # Store initial WC from franchise for gating logic
    initial_wc_from_franchise = float(franchise.get("working_capital", 0) or 0) if franchise else 0
    
    # Parse month
    try:
        year, month = req.month.split("-")
        year = int(year)
        month = int(month)
    except:
        raise HTTPException(400, "Invalid month format. Use YYYY-MM")
    
    # Date range for the month
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    # ==========================================
    # 1. Fetch Sales Data from daily_sales
    # ==========================================
    sales_query = {
        "center": req.center,
        "date": {"$gte": start_date, "$lt": end_date}
    }
    
    sales_records = await db.daily_sales.find(sales_query, {"_id": 0}).to_list(100)
    
    # DEBUG: Log sample records
    logger.info(f"Found {len(sales_records)} sales records for {req.center} in {req.month}")
    if sales_records:
        sample = sales_records[0]
        logger.info(f"Sample record fields: {list(sample.keys())}")
        logger.info(f"Sample doordash value: {sample.get('doordash')}")
    
    # Aggregate sales data
    total_sale = sum(r.get("total_sale", 0) or 0 for r in sales_records)
    direct_sale = sum((r.get("sale_pbm", 0) or 0) + (r.get("sale_other", 0) or 0) for r in sales_records)
    
    # Aggregator sales
    swiggy_sale = sum(r.get("swiggy", 0) or 0 for r in sales_records)
    zomato_sale = sum(r.get("zomato", 0) or 0 for r in sales_records)
    doordash_sale = sum(r.get("doordash", 0) or 0 for r in sales_records)
    aggregator_sale = swiggy_sale + zomato_sale + doordash_sale
    
    # Card/Online sales
    card_sale = sum(r.get("card_idfc", 0) or 0 for r in sales_records)
    bharat_pay = sum(r.get("bharat_pay", 0) or 0 for r in sales_records)
    online_other = sum(r.get("online_other", 0) or 0 for r in sales_records)
    
    total_online_sale = sum(r.get("total_online_sale", 0) or 0 for r in sales_records)
    total_cash_sale = sum(r.get("total_cash_sale", 0) or 0 for r in sales_records)
    
    # ==========================================
    # 2. Fetch Expenses Data
    # ==========================================
    expense_query = {
        "center": req.center,
        "date": {"$gte": start_date, "$lt": end_date}
    }
    
    expense_records = await db.expenses.find(expense_query, {"_id": 0}).to_list(500)
    total_expenses = sum(r.get("amount", 0) for r in expense_records)
    
    # Group expenses by type
    expense_by_type = {}
    for exp in expense_records:
        exp_type = exp.get("expense_type", "Other")
        expense_by_type[exp_type] = expense_by_type.get(exp_type, 0) + exp.get("amount", 0)
    
    # ==========================================
    # 3. Fetch Uploaded Commissions (monthly_commissions)
    # ==========================================
    month_str = req.month  # "YYYY-MM"
    commission_records = await db.monthly_commissions.find(
        {"center": req.center, "month": month_str}, {"_id": 0}
    ).to_list(100)

    # Aggregate commissions by platform
    # Total deduction = gst_tax_deductions + other_deductions (new schema)
    # Fallback to commission_amount for old records
    commission_by_platform = {
        "swiggy": {"gross": 0, "deduction": 0, "net": 0},
        "zomato": {"gross": 0, "deduction": 0, "net": 0},
        "doordash": {"gross": 0, "deduction": 0, "net": 0},
        "phonepe": {"gross": 0, "deduction": 0, "net": 0},
        "cards": {"gross": 0, "deduction": 0, "net": 0},
    }

    for comm in commission_records:
        platform = comm.get("platform", "").lower()
        if platform not in commission_by_platform:
            commission_by_platform[platform] = {"gross": 0, "deduction": 0, "net": 0}
        commission_by_platform[platform]["gross"] += comm.get("gross_amount", 0)
        # Total deduction = GST/Tax deductions + Other deductions (excludes sundry debtors)
        gst_ded = comm.get("gst_tax_deductions", 0)
        other_ded = comm.get("other_deductions", 0)
        # Fallback for old records that used commission_amount
        old_comm = comm.get("commission_amount", 0)
        total_ded = (gst_ded + other_ded) if (gst_ded or other_ded) else old_comm
        commission_by_platform[platform]["deduction"] += total_ded
        commission_by_platform[platform]["net"] += comm.get("net_payout", 0)

    total_aggregator_commission = (
        commission_by_platform["swiggy"]["deduction"] +
        commission_by_platform["zomato"]["deduction"] +
        commission_by_platform["doordash"]["deduction"]
    )
    card_commission = (
        commission_by_platform["phonepe"]["deduction"] +
        commission_by_platform["cards"]["deduction"]
    )
    
    # ==========================================
    # 4. Calculate Financial Summary with GST
    # ==========================================
    
    # Total commission
    total_commission = total_aggregator_commission + card_commission
    
    # Net Eligible Sales for GST = Total - Aggregators (Swiggy + Zomato + DoorDash).
    # Rate: 10% for Australia/Perth, 5% for India.
    # India: prices on receipts are GST-INCLUSIVE, so GST = eligible − eligible/1.05.
    # Australia: 10% GST is also inclusive, so same treatment with 1.10 divisor.
    eligible_base = max(0.0, total_sale - aggregator_sale)
    if country == "Australia":
        sales_gst_amount = round(eligible_base - eligible_base / 1.10, 2)
    else:
        # India: 5% inclusive on eligible (non-aggregator) sales
        sales_gst_amount = round(eligible_base - eligible_base / 1.05, 2)
    
    if country == "Australia":
        # Australia historically booked GST as inclusive; we still deduct it
        # from revenue for profit-share so downstream formula is unchanged.
        sales_ex_gst = total_sale - sales_gst_amount
        commission_gst = total_commission * 0.10
        total_commission_with_gst = total_commission + commission_gst
        net_revenue = sales_ex_gst - total_expenses - total_commission_with_gst
    else:
        # India: GST is INCLUSIVE in total_sale; remove it for accurate net revenue.
        sales_ex_gst = total_sale - sales_gst_amount
        commission_gst = 0
        total_commission_with_gst = total_commission
        net_revenue = sales_ex_gst - total_expenses - total_commission
    
    # Calculate share payable based on country
    # India: Revenue Share % from franchise settings (default 15% to Franchise Owner)
    # Outside India: Fixed 80/20 split (80% to Franchise Owner, 20% to Purnabramha) on Profit
    
    # Check if GST is applicable for India (from franchise settings)
    gst_applicable_india = franchise.get("gst_applicable", False) if franchise else False
    
    if country == "India":
        # India: Revenue share model
        # GST for Month M is booked as a liability (see gst_liabilities) and
        # paid in Month M+1 via the auto-created 'GST PAYMENT' expense row.
        # We compute GST INCLUSIVE on eligible (non-aggregator) sales:
        #   eligible = total_sale − (swiggy + zomato + doordash)
        #   GST = eligible − eligible / 1.05
        # Rationale: receipt prices already include 5% GST.

        gst_on_sales = round(max(0.0, total_sale - aggregator_sale) - max(0.0, total_sale - aggregator_sale) / 1.05, 2) if gst_applicable_india else 0

        # Net Revenue for India = Total Sales - Commissions - GST on Sales
        # (GST is removed because it's not the franchise's revenue — it's a pass-through to govt.)
        india_net_revenue = total_sale - total_commission - gst_on_sales

        # Uses revenue_share_percentage from franchise (default 15% to Franchise Owner)
        franchise_owner_percentage = float(franchise.get("revenue_share_percentage", 15) or 15) if franchise else 15
        purnabramha_percentage = 100 - franchise_owner_percentage
        # Calculate on Net Revenue (after commissions + GST)
        purnabramha_share = india_net_revenue * (purnabramha_percentage / 100)
        franchise_owner_share = india_net_revenue * (franchise_owner_percentage / 100)
        share_type = "revenue_share"
        # Store for display
        net_revenue_for_share = india_net_revenue
    else:
        # Outside India (Australia, etc.): Profit share model - FIXED 80/20 split
        # 80% to Franchise Owner, 20% to Purnabramha (on net profit after ALL deductions)
        franchise_owner_percentage = 80
        purnabramha_percentage = 20
        profit_before_share = net_revenue  # Uses full net_revenue (sales - expenses - commissions)
        purnabramha_share = profit_before_share * (purnabramha_percentage / 100)
        franchise_owner_share = profit_before_share * (franchise_owner_percentage / 100)
        share_type = "profit_share"
        net_revenue_for_share = net_revenue
    
    # Apply GST on Purnabramha's share (payable by franchise to Purnabramha)
    # For India: Calculate 18% GST for display/informational purposes but DO NOT add to total payable
    # For Outside India (Australia): Apply 10% GST on profit share (added to total)
    if country == "India":
        # Calculate 18% GST amounts for informational display only
        cgst_info = round(purnabramha_share * INDIA_CGST, 2)
        sgst_info = round(purnabramha_share * INDIA_SGST, 2)
        purnabramha_share_with_tax = {
            "base_amount": purnabramha_share,
            "gst_amount": round(cgst_info + sgst_info, 2),
            "cgst": cgst_info,
            "sgst": sgst_info,
            "total_with_gst": purnabramha_share  # GST NOT added to total for India
        }
    else:
        # Australia always applies profit share GST (10% added to total)
        purnabramha_share_with_tax = calculate_taxes(purnabramha_share, country, share_type)
    
    # ==========================================
    # Working Capital Standing (must be calculated BEFORE share/MG)
    # ==========================================
    wc_standing = await calculate_working_capital_standing(db, req.center, req.month, country)
    working_capital = wc_standing["initial_security_deposit"]
    total_loans_outstanding = wc_standing["loans_outstanding"]
    wc_revenue_share_active = wc_standing["revenue_share_active"]
    wc_status = wc_standing["wc_status"]
    
    # Other Income & Loans memo (Other Income adjusts WC chain — see calculate_working_capital_standing)
    try:
        from routes.other_income import (
            get_other_income_summary, get_loans_given_summary, get_loans_taken_summary
        )
        _other_income_memo = await get_other_income_summary(req.center, req.month)
        _loans_given_memo = await get_loans_given_summary(req.center, req.month)
        _loans_taken_memo = await get_loans_taken_summary(req.center, req.month)
    except Exception as _ex:
        logger.warning(f"Other income / loans memo failed for {req.center}: {_ex}")
        _other_income_memo = {"total": 0, "by_category": {}, "rows": []}
        _loans_given_memo = {"total": 0, "count": 0, "rows": [], "outstanding": 0, "repaid": 0}
        _loans_taken_memo = {"total": 0, "count": 0, "rows": [], "outstanding": 0, "repaid": 0}
    
    # ==========================================
    # OPERATIONAL SUSTAINABILITY CHECK (NEW)
    # ==========================================
    # Operational Balance = Total Sales - Total Expenses - Commissions
    # GST for Month M is booked as a liability and paid in Month M+1 via the
    # auto-created 'GST PAYMENT' expense row — so it naturally flows through
    # M+1 expenses. Subtracting it here would double-count the cash impact.
    gst_for_ops = gst_on_sales if country == "India" else sales_gst_amount  # kept for display only
    operational_balance = total_sale - total_expenses - total_commission
    
    operational_sustainability = {
        "total_sales": round(total_sale, 2),
        "total_expenses": round(total_expenses, 2),
        "total_commissions": round(total_commission, 2),
        "gst_on_sales": round(gst_for_ops, 2),
        "operational_balance": round(operational_balance, 2),
        "is_positive": operational_balance >= 0,
    }
    
    # ==========================================
    # WORKING CAPITAL STATUS
    # ==========================================
    wc_percentage = wc_standing.get("wc_percentage", 100)
    protection_mode = not wc_revenue_share_active and initial_wc_from_franchise > 0
    wc_status_label = "Protection Mode" if protection_mode else ("Restoring" if wc_status == "restoring" else "Healthy")
    
    working_capital_status = {
        "base_wc": round(initial_wc_from_franchise, 2),
        "initial_wc": round(initial_wc_from_franchise, 2),
        "opening_wc": wc_standing.get("opening_wc", 0),
        "current_wc": round(wc_standing.get("closing_wc", 0), 2),
        "wc_percentage": round(wc_percentage, 2),
        "wc_used": wc_standing.get("this_month_wc_used", 0),
        "wc_restored": wc_standing.get("this_month_wc_restored", 0),
        "cumulative_wc_used": wc_standing.get("cumulative_wc_used", 0),
        "cumulative_wc_restored": wc_standing.get("cumulative_wc_restored", 0),
        "status": wc_status_label,
        "protection_mode": protection_mode,
        "revenue_share_active": wc_revenue_share_active,
        "threshold": "50%",
    }
    
    # ==========================================
    # Apply Operational Sustainability Rules to Revenue Share
    # ==========================================
    # Store original calculated shares for display
    original_franchise_owner_share = franchise_owner_share
    
    wc_recovery_amount = 0
    payout_reason = ""
    
    if protection_mode:
        # PROTECTION MODE (WC < 50%)
        if operational_balance > 0:
            # Revenue Share = Operational Balance × Franchise %
            franchise_owner_share = operational_balance * (franchise_owner_percentage / 100)
            purnabramha_share = operational_balance * (purnabramha_percentage / 100)
            wc_recovery_amount = operational_balance - franchise_owner_share
            payout_reason = f"Protection Mode: Revenue Share on Operational Balance only. Rs. {wc_recovery_amount:,.2f} directed to WC recovery. MG blocked."
        else:
            # Negative operational balance: No payout, loss absorbed by WC
            franchise_owner_share = 0
            purnabramha_share = 0
            wc_recovery_amount = 0
            payout_reason = "Protection Mode: Operational Balance negative. No Revenue Share, No MG. Loss absorbed by Working Capital."
        
        # Recalculate tax on updated purnabramha share
        if country == "India":
            cgst_val = round(purnabramha_share * INDIA_CGST, 2)
            sgst_val = round(purnabramha_share * INDIA_SGST, 2)
            purnabramha_share_with_tax = {
                "base_amount": purnabramha_share,
                "gst_amount": round(cgst_val + sgst_val, 2),
                "cgst": cgst_val,
                "sgst": sgst_val,
                "total_with_gst": purnabramha_share
            }
        else:
            purnabramha_share_with_tax = calculate_taxes(purnabramha_share, country, share_type)
    
    # ==========================================
    # Calculate MG (Minimum Guarantee)
    # ==========================================
    mg_data = None
    payable_type = "revenue_share"  # Default
    franchise_owner_share_for_comparison = franchise_owner_share
    payable_amount = franchise_owner_share_for_comparison
    
    if franchise:
        total_investment = float(franchise.get("total_investment", 0) or 0)
        franchise_fee_val = float(franchise.get("franchise_fee", 0) or 0)
        working_capital_val = float(franchise.get("working_capital", 0) or 0)
        
        if total_investment <= 0:
            total_investment = franchise_fee_val + working_capital_val
        
        setup_costs = franchise.get("setup_costs", {})
        if not isinstance(setup_costs, dict):
            setup_costs = {}
        
        mg_data = calculate_mg(total_investment, setup_costs, franchise_fee_val, working_capital_val)
        monthly_mg = mg_data.get("monthly_mg", 0)
        
        if protection_mode:
            # In Protection Mode: MG is BLOCKED, only revenue share applies
            payable_type = "revenue_share_protection"
            payable_amount = franchise_owner_share
            if operational_balance <= 0:
                payable_type = "wc_protection_no_payout"
                payable_amount = 0
        else:
            # Normal Mode: MG vs Revenue Share comparison
            if monthly_mg > franchise_owner_share_for_comparison:
                payable_type = "minimum_guarantee"
                payable_amount = monthly_mg
                # In Normal Mode, if operational balance is negative, WC absorbs loss but MG still payable if WC >= 50%
            # Revenue Share >= MG: pay revenue share (default)
    
    if not payout_reason:
        if payable_type == "minimum_guarantee":
            payout_reason = f"MG ({round(mg_data.get('monthly_mg', 0) if mg_data else 0, 2)}) > Revenue Share ({round(franchise_owner_share, 2)})"
        else:
            payout_reason = f"Revenue Share ({round(franchise_owner_share, 2)}) >= MG ({round(mg_data.get('monthly_mg', 0) if mg_data else 0, 2)})"
    
    # ==========================================
    # 5. Build Response
    # ==========================================
    
    summary = {
        "center": req.center,
        "center_name": center.get("name", req.center),
        "country": country,
        "period": req.month,
        "franchise": {
            "code": franchise.get("franchise_code") if franchise else None,
            "name": franchise.get("franchise_name") if franchise else None,
            "legal_entity": franchise.get("legal_entity_name") if franchise else None,
            "linked": franchise is not None
        },
        "sales": {
            "total_sale": round(total_sale, 2),
            "direct_sale": round(direct_sale, 2),
            "aggregator_sale": round(aggregator_sale, 2),
            "swiggy": round(swiggy_sale, 2),
            "zomato": round(zomato_sale, 2),
            "doordash": round(doordash_sale, 2),
            "card_sale": round(card_sale, 2),
            "bharat_pay": round(bharat_pay, 2),
            "online_other": round(online_other, 2),
            "total_online_sale": round(total_online_sale, 2),
            "total_cash_sale": round(total_cash_sale, 2),
            "num_days": len(sales_records)
        },
        "expenses": {
            "total": round(total_expenses, 2),
            "by_category": expense_by_type
        },
        "commissions": {
            "aggregator_total": round(total_aggregator_commission, 2),
            "card_total": round(card_commission, 2),
            "total": round(total_commission, 2),
            "commission_gst": round(commission_gst, 2) if country == "Australia" else 0,
            "total_with_gst": round(total_commission_with_gst, 2) if country == "Australia" else round(total_commission, 2),
            "by_platform": commission_by_platform
        },
        "financial_summary": {
            "total_sales": round(total_sale, 2),
            "sales_gst": round(gst_on_sales if country == "India" else sales_gst_amount, 2),
            "sales_gst_rate": "5%" if country == "India" else "10%",
            "gst_applicable": gst_applicable_india if country == "India" else True,
            "sales_ex_gst": round(sales_ex_gst, 2),
            "total_expenses": round(total_expenses, 2),
            "total_commissions": round(total_commission, 2),
            "commission_gst": round(commission_gst, 2) if country == "Australia" else 0,
            "total_commissions_with_gst": round(total_commission_with_gst, 2) if country == "Australia" else round(total_commission, 2),
            "net_revenue": round(net_revenue_for_share, 2),
            "working_capital": round(working_capital, 2),
            "loans_outstanding": round(total_loans_outstanding, 2),
            "working_capital_available": wc_standing["closing_wc"],
            "wc_standing": wc_standing
        },
        "share_calculation": {
            "type": share_type,
            "net_profit_or_sales": round(net_revenue_for_share, 2),
            "total_sales": round(total_sale, 2),
            "total_deductions": round(total_commission + (gst_on_sales if country == "India" else total_expenses + total_commission), 2),
            "wc_gated": not wc_revenue_share_active,
            "wc_status": wc_status,
            "franchise_owner": {
                "percentage": franchise_owner_percentage,
                "amount": round(franchise_owner_share, 2)
            },
            "purnabramha": {
                "percentage": purnabramha_percentage,
                "base_amount": round(purnabramha_share, 2),
                "cgst": purnabramha_share_with_tax.get("cgst", 0),
                "sgst": purnabramha_share_with_tax.get("sgst", 0),
                "gst_amount": purnabramha_share_with_tax.get("gst_amount", 0),
                "total_payable": round(purnabramha_share_with_tax.get("total_with_gst", purnabramha_share), 2),
                "gst_applicable": gst_applicable_india if country == "India" else True
            }
        },
        # MG (Minimum Guarantee) calculation
        "mg_calculation": mg_data,
        # Operational Sustainability Check (NEW)
        "operational_sustainability": operational_sustainability,
        # Working Capital Status (NEW)
        "working_capital_status": working_capital_status,
        # Other Income — memo only (does NOT affect P&L / WC / MG / Revenue Share)
        "other_income": _other_income_memo,
        # Loans given to other centers — memo (no destination name)
        "loans_given": _loans_given_memo,
        # Loans taken by this center — memo with outstanding/repaid status
        "loans_taken": _loans_taken_memo,
        # Payout determination
        "payout": {
            "type": payable_type,
            "amount": round(payable_amount, 2),
            "mg_amount": round(mg_data.get("monthly_mg", 0), 2) if mg_data else 0,
            "revenue_share_amount": round(franchise_owner_share, 2),
            "original_revenue_share": round(original_franchise_owner_share, 2),
            "wc_gated": protection_mode,
            "protection_mode": protection_mode,
            "wc_recovery_amount": round(wc_recovery_amount, 2),
            "operational_balance": round(operational_balance, 2),
            "reason": payout_reason
        },
        "tax_rules": {
            "country": country,
            "sales_gst_rate": AUSTRALIA_GST_INCLUSIVE * 100 if country == "Australia" else INDIA_GST_ON_SALES * 100,
            "sales_gst_treatment": "inclusive" if country == "Australia" else "exclusive",
            "share_gst_rate": AUSTRALIA_GST_ON_PROFIT_SHARE * 100 if country == "Australia" else INDIA_GST_ON_REVENUE_SHARE * 100
        }
    }
    
    return {"success": True, "summary": summary}

# =======================================
# COMMISSION UPLOAD (EXCEL-DRIVEN)
# =======================================

@router.post("/upload-commission-excel")
async def upload_commission_excel(
    token: str = Form(...),
    platform: str = Form(""),
    center: str = Form(...),
    month: str = Form(...),
    file: UploadFile = File(...),
    bank_file: Optional[UploadFile] = File(None)
):
    """Parse a commission Excel file and return extracted summary for preview.
    For 'cards' platform, optionally accepts a bank_file to calculate MDR charges."""
    session = await check_access(token)

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "File must be Excel (.xlsx / .xls)")

    from routes.commission_parser import parse_commission_file, parse_cards, detect_platform
    import uuid

    content = await file.read()
    tmp_path = f"/tmp/comm_{uuid.uuid4().hex}.xlsx"
    with open(tmp_path, "wb") as f:
        f.write(content)

    bank_tmp_path = None
    if bank_file and bank_file.filename:
        if not bank_file.filename.endswith((".xlsx", ".xls")):
            import os; os.remove(tmp_path)
            raise HTTPException(400, "Bank statement must be Excel (.xlsx / .xls)")
        bank_content = await bank_file.read()
        bank_tmp_path = f"/tmp/bank_{uuid.uuid4().hex}.xlsx"
        with open(bank_tmp_path, "wb") as bf:
            bf.write(bank_content)

    try:
        detected = platform.strip().lower() if platform.strip() else None
        # For cards/phonepe with bank statement, use the two-file parser
        if detected == "cards" and bank_tmp_path:
            result = parse_cards(tmp_path, bank_tmp_path)
        elif detected == "phonepe" and bank_tmp_path:
            from routes.commission_parser import parse_phonepe
            result = parse_phonepe(tmp_path, bank_tmp_path)
        else:
            result = parse_commission_file(tmp_path, detected, file.filename)
    except Exception as e:
        logger.error(f"Commission parse error: {e}")
        import os
        os.remove(tmp_path)
        if bank_tmp_path:
            os.remove(bank_tmp_path)
        raise HTTPException(400, f"Failed to parse file: {str(e)}")

    import os
    os.remove(tmp_path)
    if bank_tmp_path:
        os.remove(bank_tmp_path)

    result["center"] = center
    result["month"] = month
    result["original_filename"] = file.filename
    if bank_file and bank_file.filename:
        result["bank_filename"] = bank_file.filename

    return {"success": True, "parsed": result}


@router.post("/save-commission")
async def save_parsed_commission(data: dict):
    """Save parsed commission data to monthly_commissions collection."""
    token = data.get("token")
    session = await check_access(token)
    import uuid

    center = data.get("center", "").upper().strip()
    month = data.get("month", "").strip()
    platform = data.get("platform", "").lower().strip()

    if not center or not month or not platform:
        raise HTTPException(400, "center, month, and platform are required")

    # Check for duplicate (same center + month + platform)
    existing = await db.monthly_commissions.find_one({
        "center": center, "month": month, "platform": platform
    })
    if existing:
        raise HTTPException(400, f"Commission for {platform.upper()} - {center} - {month} already exists. Delete the old record first.")

    doc = {
        "commission_id": str(uuid.uuid4()),
        "center": center,
        "month": month,
        "platform": platform,
        "original_filename": data.get("original_filename", ""),
        "gross_amount": float(data.get("gross_amount", 0)),
        "gst_tax_deductions": float(data.get("gst_tax_deductions", 0)),
        "other_deductions": float(data.get("other_deductions", 0)),
        "sundry_debtors": float(data.get("sundry_debtors", 0)),
        "tds": float(data.get("tds", 0)),
        "net_payout": float(data.get("net_payout", 0)),
        "order_count": int(data.get("order_count", 0)),
        "currency": data.get("currency", "INR"),
        "raw_summary": data.get("raw_summary", {}),
        "uploaded_by": session.get("managerName", "Unknown"),
        "upload_date": datetime.now(timezone.utc).isoformat(),
    }

    await db.monthly_commissions.insert_one(doc)
    logger.info(f"Commission saved: {platform} / {center} / {month} by {doc['uploaded_by']}")

    return {"success": True, "message": f"Commission saved for {platform.upper()} - {center} - {month}"}


@router.post("/list-commissions")
async def list_commissions(data: dict):
    """List uploaded commissions from monthly_commissions collection."""
    token = data.get("token")
    session = await check_access(token)

    center = data.get("center", "").upper().strip()
    month = data.get("month", "").strip()

    query = {"center": center}
    if month:
        query["month"] = month

    records = await db.monthly_commissions.find(query, {"_id": 0}).sort("upload_date", -1).to_list(200)

    return {"success": True, "statements": records, "total": len(records)}


@router.post("/delete-commission")
async def delete_commission(data: dict):
    """Delete a commission record by commission_id."""
    token = data.get("token")
    session = await check_access(token)

    commission_id = data.get("commission_id")
    if not commission_id:
        raise HTTPException(400, "commission_id is required")

    result = await db.monthly_commissions.delete_one({"commission_id": commission_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Commission record not found")

    logger.info(f"Commission deleted: {commission_id} by {session.get('managerName')}")
    return {"success": True, "message": "Commission record deleted"}

# =======================================
# PDF GENERATION - PIB REPORT
# =======================================

@router.post("/preview-pib")
async def preview_pib_report(req: PIBGenerateRequest):
    """Return the PIB data as JSON so the frontend can render a preview screen
    BEFORE the user clicks Download. Same computation as /generate-pib but
    without the PDF rendering step."""
    session = await check_access(req.token)
    summary_req = AccountPeriodRequest(
        token=req.token, center=req.center, month=req.month
    )
    summary_response = await get_center_account_summary(summary_req)
    summary = summary_response["summary"]
    if not summary["franchise"]["linked"]:
        raise HTTPException(400, "Center is not linked to a franchise. Cannot generate PIB.")
    return {
        "success": True,
        "center": req.center,
        "month": req.month,
        "summary": summary,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/generate-pib")
async def generate_pib_report(req: PIBGenerateRequest):
    """Generate PIB (Profit & Income Balance) Report PDF"""
    session = await check_access(req.token)
    await enforce_owner_visibility(session, req.center, req.month)
    
    # Get account summary
    summary_req = AccountPeriodRequest(
        token=req.token,
        center=req.center,
        month=req.month
    )
    summary_response = await get_center_account_summary(summary_req)
    summary = summary_response["summary"]
    
    # Validation
    if not summary["franchise"]["linked"]:
        raise HTTPException(400, "Center is not linked to a franchise. Cannot generate PIB.")

    from utils.pdf_generator import build_pib_pdf
    pdf_bytes = build_pib_pdf(summary)
    filename = f"PIB_{summary['center']}_{summary['period']}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# =======================================
# ADDITIONAL REPORT ENDPOINTS
# =======================================

@router.post("/generate-gst-summary")
async def generate_gst_summary(req: PIBGenerateRequest):
    """Generate GST Summary Report PDF"""
    session = await check_access(req.token)
    await enforce_owner_visibility(session, req.center, req.month)
    
    # Get account summary
    summary_req = AccountPeriodRequest(token=req.token, center=req.center, month=req.month)
    summary_response = await get_center_account_summary(summary_req)
    summary = summary_response["summary"]

    from utils.pdf_generator import build_gst_summary_pdf
    pdf_bytes = build_gst_summary_pdf(summary)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=GST_Summary_{summary['center']}_{summary['period']}.pdf"}
    )

@router.post("/generate-commission-summary")
async def generate_commission_summary(req: PIBGenerateRequest):
    """Generate Aggregator/Card Commission Summary PDF"""
    session = await check_access(req.token)
    await enforce_owner_visibility(session, req.center, req.month)
    summary_req = AccountPeriodRequest(token=req.token, center=req.center, month=req.month)
    summary_response = await get_center_account_summary(summary_req)
    summary = summary_response["summary"]

    from utils.pdf_generator import build_commission_summary_pdf
    pdf_bytes = build_commission_summary_pdf(summary)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Commission_Summary_{summary['center']}_{summary['period']}.pdf"}
    )


@router.post("/generate-bank-statement")
async def generate_bank_statement(req: PIBGenerateRequest):
    """Generate a monthly Bank Activity Statement (derived cash-flow).

    Credits: daily sales receipts split by Cash / Online+Card / Aggregator.
    Debits : monthly expense rows + commission deductions + GST-liability
             payment (if already booked in this month) + revenue share payout
             (if paid in this month).
    Opening/closing derived from the working-capital opening + net movement.
    """
    session = await check_access(req.token)
    await enforce_owner_visibility(session, req.center, req.month)

    start_date, end_date = _mk_month_range(req.month)
    center_info = await get_center_details(req.center)

    # ---- Credits: daily sales ------------------------------------------------
    sales = await db.daily_sales.find(
        {"center": req.center, "date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0},
    ).sort("date", 1).to_list(200)

    credits: list = []
    for s in sales:
        d = s.get("date")
        cash = float(s.get("total_cash_sale") or s.get("cash_sale") or 0)
        online_card = float(s.get("total_online_sale") or s.get("online_sale") or s.get("card_sale") or 0)
        swiggy = float(s.get("swiggy_sale") or s.get("swiggy") or 0)
        zomato = float(s.get("zomato_sale") or s.get("zomato") or 0)
        doordash = float(s.get("doordash_sale") or s.get("doordash") or 0)
        if cash:
            credits.append({"date": d, "description": "Cash sales", "amount": cash})
        if online_card:
            credits.append({"date": d, "description": "Online / Card sales", "amount": online_card})
        agg = swiggy + zomato + doordash
        if agg:
            credits.append({"date": d, "description": "Aggregator receipts (Swiggy+Zomato+DoorDash gross)", "amount": agg})

    # ---- Debits: expenses ----------------------------------------------------
    expenses = await db.expenses.find(
        {"center": req.center, "date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0},
    ).sort("date", 1).to_list(500)
    debits: list = []
    for e in expenses:
        amt = float(e.get("amount", 0) or 0)
        if amt <= 0:
            continue
        cat = e.get("expense_type") or e.get("category") or "Expense"
        debits.append({"date": e.get("date", ""), "description": cat, "amount": amt})

    # ---- Debits: aggregator commission deductions + payout ------------------
    summary: dict = {}
    try:
        summary_req = AccountPeriodRequest(token=req.token, center=req.center, month=req.month)
        summary_response = await get_center_account_summary(summary_req)
        summary = summary_response.get("summary", {})
        total_comm = float(summary.get("commissions", {}).get("total", 0) or 0)
        if total_comm > 0:
            debits.append({
                "date": end_date,
                "description": "Aggregator / Card commissions (Swiggy / Zomato / Card deductions)",
                "amount": total_comm,
            })
        payout = summary.get("payout") or {}
        if payout.get("amount") and payout.get("status") == "paid":
            debits.append({
                "date": end_date,
                "description": f"Revenue share payout ({payout.get('type', 'revenue_share').replace('_',' ').title()})",
                "amount": float(payout.get("amount") or 0),
            })
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"bank-statement: summary fetch failed for {req.center} {req.month}: {exc}")

    # Opening / closing
    wc_info = summary.get("working_capital_status", {}) or {}
    opening = float(wc_info.get("opening_wc", 0) or 0)
    total_credits = sum(float(r["amount"]) for r in credits)
    total_debits = sum(float(r["amount"]) for r in debits)
    closing = opening + total_credits - total_debits

    pdf_data = {
        "center": req.center,
        "center_name": center_info.get("name", req.center),
        "month": req.month,
        "period_label": f"Period: {start_date} to {end_date}",
        "opening_balance": opening,
        "closing_balance": closing,
        "credits": credits,
        "debits": debits,
        "totals": {
            "total_credits": total_credits,
            "total_debits": total_debits,
            "net_movement": total_credits - total_debits,
        },
    }

    from utils.pdf_generator import build_bank_statement_pdf
    pdf_bytes = build_bank_statement_pdf(pdf_data)
    filename = f"Bank_Statement_{req.center}_{req.month}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _mk_month_range(month: str) -> tuple[str, str]:
    """YYYY-MM → (YYYY-MM-01, YYYY-MM-lastday)."""
    from calendar import monthrange
    y, m = int(month[:4]), int(month[5:7])
    last = monthrange(y, m)[1]
    return f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{last:02d}"



# =======================================
# CENTER-FRANCHISE LINKING
# =======================================

@router.post("/link-franchise")
async def link_center_to_franchise(data: dict):
    """Link a center to a franchise"""
    token = data.get("token")
    session = await check_access(token)
    
    # Only Super Admin can link
    if not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin can link centers to franchises")
    
    center_code = data.get("center_code")
    franchise_code = data.get("franchise_code")
    
    # Validate center
    center = await db.centers.find_one({"code": center_code})
    if not center:
        raise HTTPException(404, f"Center {center_code} not found")
    
    # Validate franchise
    franchise = await db.franchises.find_one({"franchise_code": franchise_code})
    if not franchise:
        raise HTTPException(404, f"Franchise {franchise_code} not found")
    
    # Update center with franchise link
    await db.centers.update_one(
        {"code": center_code},
        {"$set": {
            "franchise_code": franchise_code,
            "country": franchise.get("country", "India"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": session.get("managerName", "Unknown")
        }}
    )
    
    return {"success": True, "message": f"Center {center_code} linked to franchise {franchise_code}"}

@router.post("/unlink-franchise")
async def unlink_center_from_franchise(data: dict):
    """Unlink a center from its franchise"""
    token = data.get("token")
    session = await check_access(token)
    
    if not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin can unlink centers from franchises")
    
    center_code = data.get("center_code")
    
    await db.centers.update_one(
        {"code": center_code},
        {"$unset": {"franchise_code": ""},
         "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"success": True, "message": f"Center {center_code} unlinked from franchise"}

@router.post("/get-linkage-status")
async def get_center_franchise_linkage(data: dict):
    """Get franchise linkage status for all centers"""
    token = data.get("token")
    session = await check_access(token)
    
    centers = await db.centers.find({}, {"_id": 0, "code": 1, "name": 1, "franchise_code": 1, "country": 1}).to_list(100)
    franchises = await db.franchises.find({"status": {"$ne": "Deleted"}}, {"_id": 0, "franchise_code": 1, "franchise_name": 1, "country": 1}).to_list(100)
    
    # Create franchise lookup
    franchise_lookup = {f["franchise_code"]: f for f in franchises}
    
    # Add franchise info to centers
    for center in centers:
        fc = center.get("franchise_code")
        if fc and fc in franchise_lookup:
            center["franchise"] = franchise_lookup[fc]
            center["linked"] = True
        else:
            center["franchise"] = None
            center["linked"] = False
    
    return {
        "success": True,
        "centers": centers,
        "franchises": franchises,
        "linked_count": sum(1 for c in centers if c.get("linked")),
        "unlinked_count": sum(1 for c in centers if not c.get("linked"))
    }


# =======================================
# PAYMENT TRACKING ENDPOINTS
# =======================================

class PaymentRecordRequest(BaseModel):
    token: str
    center: str
    month: str  # YYYY-MM format
    amount: float
    payment_type: Optional[str] = "payout"  # "revenue_share", "minimum_guarantee", or "payout"
    payment_date: str  # YYYY-MM-DD
    payment_method: Optional[str] = "Bank Transfer"
    reference: Optional[str] = ""
    notes: Optional[str] = ""

@router.post("/record-payment")
async def record_payment(req: PaymentRecordRequest):
    """Record a payment against monthly payout"""
    session = await check_access(req.token)
    
    # Verify center exists
    center = await get_center_details(req.center)
    
    # Create payment record
    payment = {
        "payment_id": f"PAY-{req.center}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "center": req.center.upper(),
        "month": req.month,
        "amount": round(req.amount, 2),
        "payment_type": req.payment_type,
        "payment_date": req.payment_date,
        "payment_method": req.payment_method,
        "reference": req.reference,
        "notes": req.notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": session.get("managerName", "Unknown")
    }
    
    await db.payout_payments.insert_one(payment)
    
    logger.info(f"Payment recorded: {payment['payment_id']} for {req.center} - {req.month}")
    
    return {
        "success": True,
        "payment_id": payment["payment_id"],
        "message": f"Payment of {req.amount} recorded for {req.center} - {req.month}"
    }

@router.post("/get-payments")
async def get_payments(data: dict = Body(...)):
    """Get payment history for a center"""
    token = data.get("token")
    center = data.get("center")
    month = data.get("month")  # Optional
    
    session = await check_access(token)
    
    query = {"center": center.upper()}
    if month:
        query["month"] = month
    
    payments = await db.payout_payments.find(
        query,
        {"_id": 0}
    ).sort("payment_date", -1).to_list(500)
    
    # Calculate totals
    total_paid = sum(p.get("amount", 0) for p in payments)
    
    return {
        "success": True,
        "payments": payments,
        "total_paid": round(total_paid, 2),
        "count": len(payments)
    }

@router.post("/update-payment")
async def update_payment(data: dict = Body(...)):
    """Update an existing payment record"""
    token = data.get("token")
    session = await check_access(token)

    payment_id = data.get("payment_id")
    if not payment_id:
        raise HTTPException(400, "payment_id is required")

    update_fields = {}
    if "amount" in data:
        update_fields["amount"] = round(float(data["amount"]), 2)
    if "payment_date" in data:
        update_fields["payment_date"] = data["payment_date"]
    if "notes" in data:
        update_fields["notes"] = data["notes"]

    if not update_fields:
        raise HTTPException(400, "No fields to update")

    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_fields["updated_by"] = session.get("managerName", "Unknown")

    result = await db.payout_payments.update_one(
        {"payment_id": payment_id},
        {"$set": update_fields}
    )

    if result.matched_count == 0:
        raise HTTPException(404, "Payment not found")

    return {"success": True, "message": f"Payment {payment_id} updated"}

@router.post("/delete-payment")
async def delete_payment(data: dict = Body(...)):
    """Delete a payment record"""
    token = data.get("token")
    session = await check_access(token)

    payment_id = data.get("payment_id")
    if not payment_id:
        raise HTTPException(400, "payment_id is required")

    result = await db.payout_payments.delete_one({"payment_id": payment_id})

    if result.deleted_count == 0:
        raise HTTPException(404, "Payment not found")

    logger.info(f"Payment deleted: {payment_id} by {session.get('managerName')}")
    return {"success": True, "message": f"Payment {payment_id} deleted"}

@router.post("/payout-summary")
async def get_payout_summary(data: dict = Body(...)):
    """Get comprehensive payout summary with paid/pending amounts"""
    token = data.get("token")
    center = data.get("center")
    from_month = data.get("from_month")  # Optional: Start month (YYYY-MM)
    to_month = data.get("to_month")  # Optional: End month (YYYY-MM)
    
    session = await check_access(token)
    
    # Get franchise info for MG calculation
    franchise = await get_franchise_for_center(center)
    
    # Calculate MG if franchise exists
    mg_amount = 0
    if franchise:
        # Use total_investment field if set, otherwise fallback to franchise_fee + working_capital
        total_investment = float(franchise.get("total_investment", 0) or 0)
        franchise_fee = float(franchise.get("franchise_fee", 0) or 0)
        working_capital = float(franchise.get("working_capital", 0) or 0)
        
        if total_investment <= 0:
            total_investment = franchise_fee + working_capital
        
        setup_costs = franchise.get("setup_costs", {})
        if not isinstance(setup_costs, dict):
            setup_costs = {}
        
        # Calculate MG (now includes franchise_fee and working_capital as deductions)
        mg_data = calculate_mg(total_investment, setup_costs, franchise_fee, working_capital)
        mg_amount = mg_data.get("monthly_mg", 0)
    
    # Get revenue start date from franchise - use revenue_share_start_date if set, fallback to operations_start_date
    revenue_start_date = None
    if franchise:
        rev_start = franchise.get("revenue_share_start_date") or franchise.get("operations_start_date") or franchise.get("agreement_start_date")
        if rev_start:
            try:
                revenue_start_date = datetime.strptime(rev_start, "%Y-%m-%d")
            except:
                pass
    
    # If no from_month provided, use revenue start date
    if not from_month and revenue_start_date:
        from_month = revenue_start_date.strftime("%Y-%m")
    elif not from_month:
        # Default to 6 months ago
        from_month = (datetime.now() - timedelta(days=180)).strftime("%Y-%m")
    
    if not to_month:
        to_month = datetime.now().strftime("%Y-%m")
    
    # Cap to_month at franchise effective end date (prevent endless future months)
    effective_end = get_franchise_effective_end_month(franchise)
    if to_month > effective_end:
        to_month = effective_end
    
    # Generate list of months
    months = []
    current = datetime.strptime(from_month + "-01", "%Y-%m-%d")
    end = datetime.strptime(to_month + "-01", "%Y-%m-%d")
    
    while current <= end:
        months.append(current.strftime("%Y-%m"))
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    # Get all payments for this center
    payments_cursor = db.payout_payments.find(
        {"center": center.upper()},
        {"_id": 0}
    )
    payments_list = await payments_cursor.to_list(1000)
    
    # Group payments by month
    payments_by_month = {}
    for p in payments_list:
        m = p.get("month")
        if m not in payments_by_month:
            payments_by_month[m] = []
        payments_by_month[m].append(p)
    
    # Build monthly summary
    monthly_data = []
    total_revenue_share = 0
    total_mg = 0
    total_payable = 0
    total_paid = 0
    total_pending = 0
    
    for month in months:
        # Get sales data for this month
        year, mon = month.split("-")
        start_date = f"{year}-{mon}-01"
        if int(mon) == 12:
            end_date = f"{int(year) + 1}-01-01"
        else:
            end_date = f"{year}-{int(mon) + 1:02d}-01"
        
        # Get total sales + aggregator breakdown (needed for eligible-GST base)
        sales_records = await db.daily_sales.find({
            "center": center,
            "date": {"$gte": start_date, "$lt": end_date}
        }, {"total_sale": 1, "swiggy_sale": 1, "zomato_sale": 1, "doordash_sale": 1,
            "swiggy": 1, "zomato": 1, "doordash": 1}).to_list(100)
        
        total_sale = sum(r.get("total_sale", 0) or 0 for r in sales_records)
        
        # Get expenses for this month
        expense_records = await db.expenses.find({
            "center": center,
            "date": {"$gte": start_date, "$lt": end_date}
        }, {"amount": 1}).to_list(500)
        total_expenses = sum(e.get("amount", 0) or 0 for e in expense_records)
        
        # Get commissions for this month - check both collections
        # 1. From commission_statements (legacy)
        commission_records = await db.commission_statements.find({
            "center": center,
            "settlement_period_start": {"$gte": start_date},
            "settlement_period_end": {"$lt": end_date}
        }, {"commission_charged": 1}).to_list(100)
        total_commission = sum(c.get("commission_charged", 0) or 0 for c in commission_records)
        
        # 2. From monthly_commissions (uploaded Excel data)
        monthly_comm_records = await db.monthly_commissions.find({
            "center": center,
            "month": month
        }, {"gst_tax_deductions": 1, "other_deductions": 1, "commission_amount": 1, "gst_on_commission": 1}).to_list(100)
        for mc in monthly_comm_records:
            new_val = (mc.get("gst_tax_deductions", 0) or 0) + (mc.get("other_deductions", 0) or 0)
            old_val = (mc.get("commission_amount", 0) or 0) + (mc.get("gst_on_commission", 0) or 0)
            total_commission += new_val if new_val > 0 else old_val
        
        # Calculate Net Revenue / Net Profit based on country
        # India: Net Revenue = Total Sales - Commissions (GST excluded, paid M+1)
        # Outside India: Net Profit = Total Sales - Expenses - Commissions
        franchise_country = franchise.get("country", "India") if franchise else "India"

        if franchise_country == "India":
            # India: Net Revenue = Total Sales - Commissions
            # GST is NOT deducted — it is booked as a liability in Month M and
            # paid as an expense in Month M+1 (see gst_liabilities flow).
            # Deducting it here would double-count.
            net_revenue_for_share = max(0, total_sale - total_commission)
        else:
            # Outside India: Net Profit = Sales - Expenses - Commissions
            net_revenue_for_share = max(0, total_sale - total_expenses - total_commission)
        
        # Calculate FRANCHISE OWNER's share (this is what gets compared with MG)
        # India: Use franchise's revenue_share_percentage (default 15% to Franchise Owner) on NET REVENUE
        # Outside India: Fixed 80% to Franchise Owner on profit
        
        if franchise_country == "India":
            franchise_owner_pct = float(franchise.get("revenue_share_percentage", 15) or 15) if franchise else 15
            revenue_share = net_revenue_for_share * (franchise_owner_pct / 100)  # Franchise Owner's share on NET revenue
        else:
            # Outside India: Fixed 80% to Franchise Owner on net profit
            revenue_share = net_revenue_for_share * 0.80
        
        # Determine payable amount (MG or Franchise Owner's Revenue Share)
        if mg_amount > revenue_share:
            payable = mg_amount
            payout_type = "mg"
        else:
            payable = revenue_share
            payout_type = "revenue_share"
        
        # Get payments for this month
        month_payments = payments_by_month.get(month, [])
        paid = sum(p.get("amount", 0) for p in month_payments)
        pending = max(0, payable - paid)
        
        monthly_data.append({
            "month": month,
            "total_sales": round(total_sale, 2),
            "revenue_share": round(revenue_share, 2),
            "mg_amount": round(mg_amount, 2),
            "payable_type": payout_type,
            "payable_amount": round(payable, 2),
            "paid": round(paid, 2),
            "pending": round(pending, 2),
            "status": "paid" if pending <= 0 else ("partial" if paid > 0 else "unpaid"),
            "payments": month_payments
        })
        
        total_revenue_share += revenue_share
        total_mg += mg_amount
        total_payable += payable
        total_paid += paid
        total_pending += pending
    
    return {
        "success": True,
        "center": center,
        "franchise": {
            "code": franchise.get("franchise_code") if franchise else None,
            "name": franchise.get("franchise_name") if franchise else None,
            "mg_amount": round(mg_amount, 2)
        },
        "period": {
            "from": from_month,
            "to": to_month,
            "revenue_start_date": revenue_start_date.strftime("%Y-%m-%d") if revenue_start_date else None
        },
        "totals": {
            "revenue_share": round(total_revenue_share, 2),
            "mg": round(total_mg * len(months), 2),  # Total MG for all months
            "payable": round(total_payable, 2),
            "paid": round(total_paid, 2),
            "pending": round(total_pending, 2)
        },
        "monthly_data": monthly_data
    }


@router.post("/export-mg-payout")
async def export_mg_payout(data: dict = Body(...)):
    """Export MG Payout summary as Excel or PDF"""
    token = data.get("token")
    center = data.get("center")
    fmt = data.get("format", "excel")  # "excel" or "pdf"
    from_month = data.get("from_month")
    to_month = data.get("to_month")

    session = await check_access(token)
    # Franchise Owners can only download released months — apply gate to the
    # "to_month" (latest) as the representative month.
    if from_month and to_month:
        await enforce_owner_visibility(session, center, to_month)

    # Reuse payout-summary logic
    summary_data = await get_payout_summary({
        "token": token,
        "center": center,
        "from_month": from_month,
        "to_month": to_month
    })

    monthly_data = summary_data.get("monthly_data", [])
    totals = summary_data.get("totals", {})
    period = summary_data.get("period", {})
    franchise_info = summary_data.get("franchise", {})

    if fmt == "excel":
        return _export_mg_excel(center, monthly_data, totals, period, franchise_info)
    else:
        return _export_mg_pdf(center, monthly_data, totals, period, franchise_info)


def _export_mg_excel(center, monthly_data, totals, period, franchise_info):
    """Generate MG Payout Excel export"""
    from utils.pdf_generator import build_mg_payout_excel
    xlsx_bytes = build_mg_payout_excel(center, monthly_data, totals, period, franchise_info)
    filename = f"MG_Payout_{center}_{period.get('from', 'start')}_to_{period.get('to', 'end')}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


def _export_mg_pdf(center, monthly_data, totals, period, franchise_info):
    """Generate MG Payout PDF export"""
    from utils.pdf_generator import build_mg_payout_pdf
    pdf_bytes = build_mg_payout_pdf(center, monthly_data, totals, period, franchise_info)
    filename = f"MG_Payout_{center}_{period.get('from', 'start')}_to_{period.get('to', 'end')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
