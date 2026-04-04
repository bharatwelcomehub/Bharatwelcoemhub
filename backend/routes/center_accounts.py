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
    Calculate dynamic Working Capital standing as of a given month.
    
    WC Available = Initial Security Deposit + Cumulative P&L - Loans Outstanding
    where P&L = Sales - Expenses - Commissions - GST (from center opening to up_to_month)
    """
    # Get franchise for initial WC (security deposit)
    center = await db_ref.centers.find_one({"code": center_code}, {"_id": 0})
    franchise = None
    initial_wc = 0
    
    if center:
        fc = center.get("franchise_code")
        if fc:
            franchise = await db_ref.franchises.find_one({"franchise_code": fc}, {"_id": 0})
            if franchise:
                initial_wc = float(franchise.get("working_capital", 0) or 0)
    
    # Parse up_to_month → end_date for queries (include the full selected month)
    year, month = map(int, up_to_month.split("-"))
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    # 1. Cumulative Sales (from all time up to end of selected month)
    sales_pipeline = [
        {"$match": {"center": center_code, "date": {"$lt": end_date}}},
        {"$group": {
            "_id": None,
            "total_sale": {"$sum": {"$ifNull": ["$total_sale", 0]}},
        }}
    ]
    sales_agg = await db_ref.daily_sales.aggregate(sales_pipeline).to_list(1)
    cumulative_sales = sales_agg[0]["total_sale"] if sales_agg else 0
    
    # 2. Cumulative Expenses
    expenses_pipeline = [
        {"$match": {"center": center_code, "date": {"$lt": end_date}}},
        {"$group": {
            "_id": None,
            "total_expenses": {"$sum": {"$ifNull": ["$amount", 0]}}
        }}
    ]
    expenses_agg = await db_ref.expenses.aggregate(expenses_pipeline).to_list(1)
    cumulative_expenses = expenses_agg[0]["total_expenses"] if expenses_agg else 0
    
    # 3. Cumulative Commissions (from monthly_commissions)
    # All months up to and including selected month
    comm_pipeline = [
        {"$match": {"center": center_code, "month": {"$lte": up_to_month}}},
        {"$group": {
            "_id": None,
            "total_commission": {"$sum": {
                "$cond": [
                    {"$or": [
                        {"$gt": ["$gst_tax_deductions", 0]},
                        {"$gt": ["$other_deductions", 0]}
                    ]},
                    {"$add": [
                        {"$ifNull": ["$gst_tax_deductions", 0]},
                        {"$ifNull": ["$other_deductions", 0]}
                    ]},
                    {"$ifNull": ["$commission_amount", 0]}
                ]
            }}
        }}
    ]
    comm_agg = await db_ref.monthly_commissions.aggregate(comm_pipeline).to_list(1)
    cumulative_commissions = comm_agg[0]["total_commission"] if comm_agg else 0
    
    # 4. GST on Sales
    if country == "Australia":
        cumulative_gst = cumulative_sales * AUSTRALIA_GST_INCLUSIVE / (1 + AUSTRALIA_GST_INCLUSIVE)
    else:
        # India - check if GST is applicable
        gst_applicable = franchise.get("gst_applicable", False) if franchise else False
        cumulative_gst = cumulative_sales * INDIA_GST_ON_SALES if gst_applicable else 0
    
    # 5. Cumulative P&L
    cumulative_pnl = cumulative_sales - cumulative_expenses - cumulative_commissions - cumulative_gst
    
    # 6. Loans Outstanding (active loans as of selected month)
    loan_entries = await db_ref.loan_entries.find({
        "center": center_code,
        "status": {"$ne": "fully_repaid"}
    }, {"_id": 0}).to_list(100)
    
    total_loans_outstanding = sum(
        (loan.get("amount", 0) - loan.get("total_repaid", 0))
        for loan in loan_entries
    )
    
    # 7. Available Working Capital
    available_capital = initial_wc + cumulative_pnl - total_loans_outstanding
    
    # Monthly breakdown for current month's P&L only (for display)
    month_start = f"{year}-{month:02d}-01"
    current_month_sales_agg = await db_ref.daily_sales.aggregate([
        {"$match": {"center": center_code, "date": {"$gte": month_start, "$lt": end_date}}},
        {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$total_sale", 0]}}}}
    ]).to_list(1)
    current_month_expenses_agg = await db_ref.expenses.aggregate([
        {"$match": {"center": center_code, "date": {"$gte": month_start, "$lt": end_date}}},
        {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$amount", 0]}}}}
    ]).to_list(1)
    
    current_month_sales = current_month_sales_agg[0]["total"] if current_month_sales_agg else 0
    current_month_expenses = current_month_expenses_agg[0]["total"] if current_month_expenses_agg else 0
    current_month_pnl = current_month_sales - current_month_expenses
    
    return {
        "initial_security_deposit": round(initial_wc, 2),
        "cumulative_sales": round(cumulative_sales, 2),
        "cumulative_expenses": round(cumulative_expenses, 2),
        "cumulative_commissions": round(cumulative_commissions, 2),
        "cumulative_gst": round(cumulative_gst, 2),
        "cumulative_pnl": round(cumulative_pnl, 2),
        "loans_outstanding": round(total_loans_outstanding, 2),
        "available_capital": round(available_capital, 2),
        "current_month_pnl": round(current_month_pnl, 2),
        "current_month_sales": round(current_month_sales, 2),
        "current_month_expenses": round(current_month_expenses, 2),
    }


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

async def get_center_details(center_code: str):
    """Get center details with country info"""
    center = await db.centers.find_one({"code": center_code}, {"_id": 0})
    if not center:
        raise HTTPException(404, f"Center {center_code} not found")
    return center

async def get_franchise_for_center(center_code: str):
    """Get linked franchise for a center"""
    # Try to find franchise by center code mapping or name matching
    # First check if center has franchise_code field
    center = await db.centers.find_one({"code": center_code}, {"_id": 0})
    if not center:
        return None
    
    # Check if center has franchise_code
    franchise_code = center.get("franchise_code")
    if franchise_code:
        franchise = await db.franchises.find_one({"franchise_code": franchise_code}, {"_id": 0})
        if franchise:
            return franchise
    
    # Try to match by city/location
    city = center.get("city", "").lower()
    state = center.get("state", "").lower()
    
    # For Perth center, find Perth franchise
    if "perth" in center_code.lower() or "perth" in city:
        franchise = await db.franchises.find_one(
            {"city": {"$regex": "perth", "$options": "i"}, "status": {"$ne": "Deleted"}},
            {"_id": 0}
        )
        if franchise:
            return franchise
    
    return None

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
    
    # For Australia: Sales are GST inclusive (10%)
    # We need to extract GST from total sale
    if country == "Australia":
        # GST is 10% included in sale, so extract it
        gst_rate = 0.10
        sales_gst_amount = total_sale * gst_rate / (1 + gst_rate)
        sales_ex_gst = total_sale - sales_gst_amount
        
        # Commission GST (10% on commission)
        commission_gst = total_commission * gst_rate
        total_commission_with_gst = total_commission + commission_gst
        
        # Net Revenue for profit share calculation:
        # Sales (ex GST) - Expenses - Commission (with GST)
        net_revenue = sales_ex_gst - total_expenses - total_commission_with_gst
    else:
        # India: GST is added separately
        sales_gst_amount = total_sale * 0.05  # 5% GST on food
        sales_ex_gst = total_sale
        commission_gst = 0  # Commission GST handled differently in India
        total_commission_with_gst = total_commission
        net_revenue = total_sale - total_expenses - total_commission
    
    # Calculate share payable based on country
    # India: Revenue Share % from franchise settings (default 15% to Franchise Owner)
    # Outside India: Fixed 80/20 split (80% to Franchise Owner, 20% to Purnabramha) on Profit
    
    # Check if GST is applicable for India (from franchise settings)
    gst_applicable_india = franchise.get("gst_applicable", False) if franchise else False
    
    if country == "India":
        # India: Revenue share model
        # Net Revenue = Total Sales - Commissions (Swiggy, Zomato, Card) - GST on Sale (if gst_applicable is ON)
        # NOTE: Expenses are NOT deducted for India revenue share calculation
        
        # Calculate GST on sales (5% of total sales) - only deducted if gst_applicable is ON
        gst_on_sales = total_sale * INDIA_GST_ON_SALES if gst_applicable_india else 0
        
        # Net Revenue for India = Total Sales - Commissions - GST on Sales (if applicable)
        india_net_revenue = total_sale - total_commission - gst_on_sales
        
        # Uses revenue_share_percentage from franchise (default 15% to Franchise Owner)
        franchise_owner_percentage = float(franchise.get("revenue_share_percentage", 15) or 15) if franchise else 15
        purnabramha_percentage = 100 - franchise_owner_percentage
        # Calculate on Net Revenue (after commissions and GST if applicable)
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
    # Calculate MG (Minimum Guarantee)
    # ==========================================
    mg_data = None
    payable_type = "revenue_share"  # Default
    # The comparison is: MG vs Franchise Owner's Share (NOT Purnabramha's share)
    # If MG > Franchise Owner's Share → MG is payable to franchise owner
    # If Franchise Owner's Share >= MG → Revenue Share is payable to franchise owner
    franchise_owner_share_for_comparison = franchise_owner_share
    payable_amount = franchise_owner_share_for_comparison  # Default to franchise owner's revenue share
    
    if franchise:
        # Use total_investment field if set, otherwise fallback to franchise_fee + working_capital
        total_investment = float(franchise.get("total_investment", 0) or 0)
        franchise_fee_val = float(franchise.get("franchise_fee", 0) or 0)
        working_capital_val = float(franchise.get("working_capital", 0) or 0)
        
        if total_investment <= 0:
            # Fallback: calculate from franchise_fee + working_capital
            total_investment = franchise_fee_val + working_capital_val
        
        # Get setup costs
        setup_costs = franchise.get("setup_costs", {})
        if not isinstance(setup_costs, dict):
            setup_costs = {}
        
        # Calculate MG (now includes franchise_fee and working_capital as deductions)
        mg_data = calculate_mg(total_investment, setup_costs, franchise_fee_val, working_capital_val)
        
        # Determine payable: If MG > Franchise Owner's Revenue Share, MG is payable
        monthly_mg = mg_data.get("monthly_mg", 0)
        if monthly_mg > franchise_owner_share_for_comparison:
            payable_type = "minimum_guarantee"
            payable_amount = monthly_mg
    
    # Working Capital - Dynamic calculation based on cumulative P&L
    wc_standing = await calculate_working_capital_standing(db, req.center, req.month, country)
    working_capital = wc_standing["initial_security_deposit"]
    total_loans_outstanding = wc_standing["loans_outstanding"]
    
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
            "cumulative_pnl": wc_standing["cumulative_pnl"],
            "loans_outstanding": round(total_loans_outstanding, 2),
            "working_capital_available": wc_standing["available_capital"],
            "wc_standing": wc_standing
        },
        "share_calculation": {
            "type": share_type,
            "net_profit_or_sales": round(net_revenue_for_share, 2),  # India: Net Revenue (sales - commissions - GST), Australia: Net Profit (sales - expenses - commissions)
            "total_sales": round(total_sale, 2),  # Show total sales separately
            "total_deductions": round(total_commission + (gst_on_sales if country == "India" else total_expenses + total_commission), 2),  # India: Commissions + GST, Australia: Commissions + Expenses
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
        # Payout determination: MG vs Franchise Owner's Revenue Share
        # This shows what the FRANCHISE OWNER receives (either MG or their Revenue Share)
        "payout": {
            "type": payable_type,  # "minimum_guarantee" or "revenue_share"
            "amount": round(payable_amount, 2),
            "mg_amount": round(mg_data.get("monthly_mg", 0), 2) if mg_data else 0,
            "revenue_share_amount": round(franchise_owner_share, 2),  # Franchise Owner's share
            "reason": f"MG ({round(mg_data.get('monthly_mg', 0) if mg_data else 0, 2)}) > Revenue Share ({round(franchise_owner_share, 2)})" if payable_type == "minimum_guarantee" else f"Revenue Share ({round(franchise_owner_share, 2)}) >= MG ({round(mg_data.get('monthly_mg', 0) if mg_data else 0, 2)})"
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

@router.post("/generate-pib")
async def generate_pib_report(req: PIBGenerateRequest):
    """Generate PIB (Profit & Income Balance) Report PDF"""
    session = await check_access(req.token)
    
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
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=60,
        bottomMargin=50
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    styles.add(ParagraphStyle(
        'PIBTitle', fontSize=18, alignment=TA_CENTER, fontName='Helvetica-Bold',
        textColor=BRAND_MAROON, spaceAfter=10
    ))
    styles.add(ParagraphStyle(
        'PIBSubtitle', fontSize=12, alignment=TA_CENTER, fontName='Helvetica',
        textColor=DARK_GRAY, spaceAfter=20
    ))
    styles.add(ParagraphStyle(
        'PIBSection', fontSize=12, fontName='Helvetica-Bold',
        textColor=BRAND_NAVY, spaceBefore=15, spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        'PIBBody', fontSize=10, fontName='Helvetica',
        textColor=DARK_GRAY, spaceAfter=4, leading=14
    ))
    
    story = []
    
    # Title
    story.append(Paragraph("PURNABRAMHA", styles['PIBTitle']))
    story.append(Paragraph("Profit & Income Balance Report", styles['PIBSubtitle']))
    story.append(Spacer(1, 10))
    
    # Center & Period Info
    info_data = [
        ["Center:", summary["center_name"], "Period:", summary["period"]],
        ["Country:", summary["country"], "Report Date:", datetime.now().strftime("%d-%b-%Y")],
        ["Franchise:", summary["franchise"]["name"] or "N/A", "Legal Entity:", summary["franchise"]["legal_entity"] or "N/A"]
    ]
    
    info_table = Table(info_data, colWidths=[80, 150, 80, 150])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), BRAND_NAVY),
        ('TEXTCOLOR', (2, 0), (2, -1), BRAND_NAVY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # Sales Summary Section
    story.append(Paragraph("1. SALES SUMMARY", styles['PIBSection']))
    
    sales = summary["sales"]
    currency = "AUD" if summary["country"] == "Australia" else "Rs."
    
    sales_data = [
        ["Description", "Amount", "% of Total"],
        ["Total Sales", f"{currency} {sales['total_sale']:,.2f}", "100%"],
        ["Direct Sales", f"{currency} {sales['direct_sale']:,.2f}", f"{sales['direct_sale']/max(sales['total_sale'],1)*100:.1f}%"],
        ["Aggregator Sales", f"{currency} {sales['aggregator_sale']:,.2f}", f"{sales['aggregator_sale']/max(sales['total_sale'],1)*100:.1f}%"],
        ["  - Swiggy", f"{currency} {sales['swiggy']:,.2f}", ""],
        ["  - Zomato", f"{currency} {sales['zomato']:,.2f}", ""],
        ["  - DoorDash", f"{currency} {sales['doordash']:,.2f}", ""],
        ["Card Sales", f"{currency} {sales['card_sale']:,.2f}", f"{sales['card_sale']/max(sales['total_sale'],1)*100:.1f}%"],
        ["Cash Sales", f"{currency} {sales['total_cash_sale']:,.2f}", f"{sales['total_cash_sale']/max(sales['total_sale'],1)*100:.1f}%"],
    ]
    
    sales_table = Table(sales_data, colWidths=[200, 150, 100])
    sales_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, 1), LIGHT_GRAY),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(sales_table)
    story.append(Spacer(1, 15))
    
    # Expense Summary Section
    story.append(Paragraph("2. EXPENSE SUMMARY", styles['PIBSection']))
    
    expenses = summary["expenses"]
    expense_rows = [["Category", "Amount"]]
    for cat, amt in expenses["by_category"].items():
        expense_rows.append([cat, f"{currency} {amt:,.2f}"])
    expense_rows.append(["TOTAL EXPENSES", f"{currency} {expenses['total']:,.2f}"])
    
    expense_table = Table(expense_rows, colWidths=[280, 170])
    expense_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_GRAY),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(expense_table)
    story.append(Spacer(1, 15))
    
    # Commission Summary Section
    story.append(Paragraph("3. COMMISSION SUMMARY", styles['PIBSection']))
    
    commissions = summary["commissions"]
    commission_data = [
        ["Platform", "Gross Amount", "Total Deductions", "Net Payout"],
    ]
    
    for platform, data in commissions["by_platform"].items():
        ded = data.get("deduction", data.get("commission", 0))
        if data["gross"] > 0 or ded > 0:
            commission_data.append([
                platform.title().replace("_", " "),
                f"{currency} {data['gross']:,.2f}",
                f"{currency} {ded:,.2f}",
                f"{currency} {data['net']:,.2f}"
            ])
    
    commission_data.append([
        "TOTAL",
        "",
        f"{currency} {commissions['total']:,.2f}",
        ""
    ])
    
    commission_table = Table(commission_data, colWidths=[120, 110, 110, 110])
    commission_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_GRAY),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(commission_table)
    story.append(Spacer(1, 15))
    
    # Financial Summary Section
    story.append(Paragraph("4. FINANCIAL SUMMARY", styles['PIBSection']))
    
    fin = summary["financial_summary"]
    gst_applicable = summary.get("share_calculation", {}).get("purnabramha", {}).get("gst_applicable", False)
    gst_on_sales = fin.get("sales_gst", 0)
    
    fin_data = [
        ["Description", "Amount"],
        ["Total Sales", f"{currency} {fin['total_sales']:,.2f}"],
        ["Less: Total Expenses", f"({currency} {fin['total_expenses']:,.2f})"],
        ["Less: Total Commissions", f"({currency} {fin['total_commissions']:,.2f})"],
    ]
    
    # Show GST deduction line for India (5% on sales)
    if summary.get("country") == "India" and gst_on_sales > 0:
        fin_data.append(["Less: GST on Sales (5%)", f"({currency} {gst_on_sales:,.2f})"])
    elif summary.get("country") == "Australia":
        fin_data.append(["Less: GST on Sales (10%)", f"({currency} {gst_on_sales:,.2f})"])
    
    fin_data.append(["NET REVENUE", f"{currency} {fin['net_revenue']:,.2f}"])
    fin_data.append(["", ""])
    fin_data.append(["Working Capital (Security Deposit)", f"{currency} {fin['working_capital']:,.2f}"])
    wc_st = fin.get("wc_standing", {})
    if wc_st:
        if wc_st.get("cumulative_pnl", 0) != 0:
            pnl_label = "Cumulative P&L Impact" if wc_st["cumulative_pnl"] >= 0 else "Cumulative P&L Deficit"
            fin_data.append([pnl_label, f"{currency} {wc_st['cumulative_pnl']:,.2f}"])
        if wc_st.get("loans_outstanding", 0) > 0:
            fin_data.append(["Less: Loans Outstanding", f"({currency} {wc_st['loans_outstanding']:,.2f})"])
        fin_data.append(["Available Working Capital", f"{currency} {wc_st['available_capital']:,.2f}"])
    
    net_revenue_row_idx = len(fin_data) - 3  # NET REVENUE row index
    
    fin_table = Table(fin_data, colWidths=[280, 170])
    fin_style = [
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, net_revenue_row_idx), (-1, net_revenue_row_idx), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, net_revenue_row_idx), (-1, net_revenue_row_idx), BRAND_GOLD),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]
    fin_table.setStyle(TableStyle(fin_style))
    story.append(fin_table)
    story.append(Spacer(1, 15))
    
    # Revenue/Profit Share Calculation - 80/20 Split
    share = summary["share_calculation"]
    base_label = "Net Revenue" if share['type'] == 'profit_share' else "Total Sales"
    story.append(Paragraph(f"5. {share['type'].upper().replace('_', ' ')} CALCULATION (80/20 SPLIT)", styles['PIBSection']))
    
    share_data = [
        ["Description", "Percentage", "Amount"],
        [f"{base_label} (Base for Calculation)", "", f"{currency} {share['net_profit_or_sales']:,.2f}"],
        ["", "", ""],
        ["FRANCHISE OWNER SHARE", f"{share['franchise_owner']['percentage']}%", f"{currency} {share['franchise_owner']['amount']:,.2f}"],
        ["", "", ""],
        ["PURNABRAMHA LLC SHARE", f"{share['purnabramha']['percentage']}%", f"{currency} {share['purnabramha']['base_amount']:,.2f}"],
    ]
    
    if summary["country"] == "India":
        share_data.append(["  Add: CGST (9%)", "", f"{currency} {share['purnabramha']['cgst']:,.2f}"])
        share_data.append(["  Add: SGST (9%)", "", f"{currency} {share['purnabramha']['sgst']:,.2f}"])
    else:
        share_data.append([f"  Add: GST ({summary['tax_rules']['share_gst_rate']:.0f}%)", "", f"{currency} {share['purnabramha']['gst_amount']:,.2f}"])
    
    share_data.append(["PURNABRAMHA TOTAL (WITH GST)", "", f"{currency} {share['purnabramha']['total_payable']:,.2f}"])
    
    share_table = Table(share_data, colWidths=[220, 80, 150])
    share_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
        ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor("#e8f5e9")),  # Light green for franchise owner
        ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor("#fff3e0")),  # Light orange for Purnabramha
        ('BACKGROUND', (0, -1), (-1, -1), BRAND_MAROON),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(share_table)
    story.append(Spacer(1, 20))
    
    # Tax Rules Note
    story.append(Paragraph("6. TAX RULES APPLIED", styles['PIBSection']))
    
    tax_rules = summary["tax_rules"]
    if tax_rules["country"] == "Australia":
        tax_note = f"""
        <b>Country:</b> {tax_rules['country']}<br/>
        <b>Sales GST:</b> {tax_rules['sales_gst_rate']:.0f}% (GST Inclusive - already included in sale value)<br/>
        <b>Profit Share GST:</b> {tax_rules['share_gst_rate']:.0f}%
        """
    else:
        tax_note = f"""
        <b>Country:</b> {tax_rules['country']}<br/>
        <b>Sales GST:</b> {tax_rules['sales_gst_rate']:.0f}%<br/>
        <b>Revenue Share GST:</b> {tax_rules['share_gst_rate']:.0f}% (CGST 9% + SGST 9%)
        """
    
    story.append(Paragraph(tax_note, styles['PIBBody']))
    story.append(Spacer(1, 30))
    
    # Footer
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d-%b-%Y %H:%M')} | Purnabramha - Manaswini Foods Pvt. Ltd.",
        ParagraphStyle('Footer', fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
    ))
    
    # Build PDF
    doc.build(story)
    
    buffer.seek(0)
    filename = f"PIB_{summary['center']}_{summary['period']}.pdf"
    
    return Response(
        content=buffer.getvalue(),
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
    
    # Get account summary
    summary_req = AccountPeriodRequest(token=req.token, center=req.center, month=req.month)
    summary_response = await get_center_account_summary(summary_req)
    summary = summary_response["summary"]
    
    # Create simplified GST summary PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=60, bottomMargin=50)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('GSTTitle', fontSize=16, alignment=TA_CENTER, fontName='Helvetica-Bold', textColor=BRAND_NAVY, spaceAfter=20))
    styles.add(ParagraphStyle('GSTBody', fontSize=10, fontName='Helvetica', textColor=DARK_GRAY, spaceAfter=8))
    
    story = []
    story.append(Paragraph("PURNABRAMHA - GST SUMMARY REPORT", styles['GSTTitle']))
    story.append(Paragraph(f"Center: {summary['center_name']} | Period: {summary['period']} | Country: {summary['country']}", styles['GSTBody']))
    story.append(Spacer(1, 20))
    
    currency = "AUD" if summary["country"] == "Australia" else "Rs."
    tax_rules = summary["tax_rules"]
    
    # GST on Sales
    sales_gst = summary["sales"]["total_sale"] * (tax_rules["sales_gst_rate"] / 100)
    if summary["country"] == "Australia":
        # GST is inclusive
        sales_gst = summary["sales"]["total_sale"] * AUSTRALIA_GST_INCLUSIVE / (1 + AUSTRALIA_GST_INCLUSIVE)
    
    gst_data = [
        ["Description", "Taxable Amount", "GST Rate", "GST Amount"],
        ["Sales GST", f"{currency} {summary['sales']['total_sale']:,.2f}", f"{tax_rules['sales_gst_rate']:.0f}%", f"{currency} {sales_gst:,.2f}"],
        ["Revenue/Profit Share", f"{currency} {summary['share_calculation']['purnabramha']['base_amount']:,.2f}", f"{tax_rules['share_gst_rate']:.0f}%", f"{currency} {summary['share_calculation']['purnabramha']['gst_amount']:,.2f}"],
    ]
    
    if summary["country"] == "India":
        gst_data.append(["  - CGST (9%)", "", "", f"{currency} {summary['share_calculation']['purnabramha']['cgst']:,.2f}"])
        gst_data.append(["  - SGST (9%)", "", "", f"{currency} {summary['share_calculation']['purnabramha']['sgst']:,.2f}"])
    
    gst_table = Table(gst_data, colWidths=[150, 120, 80, 100])
    gst_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(gst_table)
    
    doc.build(story)
    buffer.seek(0)
    
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=GST_Summary_{summary['center']}_{summary['period']}.pdf"}
    )

@router.post("/generate-commission-summary")
async def generate_commission_summary(req: PIBGenerateRequest):
    """Generate Aggregator/Card Commission Summary PDF"""
    session = await check_access(req.token)
    
    summary_req = AccountPeriodRequest(token=req.token, center=req.center, month=req.month)
    summary_response = await get_center_account_summary(summary_req)
    summary = summary_response["summary"]
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=60, bottomMargin=50)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('CommTitle', fontSize=16, alignment=TA_CENTER, fontName='Helvetica-Bold', textColor=BRAND_NAVY, spaceAfter=20))
    
    story = []
    story.append(Paragraph("PURNABRAMHA - COMMISSION SUMMARY REPORT", styles['CommTitle']))
    story.append(Paragraph(f"Center: {summary['center_name']} | Period: {summary['period']}", getSampleStyleSheet()['Normal']))
    story.append(Spacer(1, 20))
    
    currency = "AUD" if summary["country"] == "Australia" else "Rs."
    commissions = summary["commissions"]
    
    comm_data = [["Platform", "Gross Orders", "Total Deductions", "Net Payout", "Deduction %"]]
    
    for platform, data in commissions["by_platform"].items():
        ded = data.get("deduction", data.get("commission", 0))
        comm_pct = (ded / data["gross"] * 100) if data["gross"] > 0 else 0
        comm_data.append([
            platform.title().replace("_", " "),
            f"{currency} {data['gross']:,.2f}",
            f"{currency} {ded:,.2f}",
            f"{currency} {data['net']:,.2f}",
            f"{comm_pct:.1f}%"
        ])
    
    comm_data.append(["TOTAL", "", f"{currency} {commissions['total']:,.2f}", "", ""])
    
    comm_table = Table(comm_data, colWidths=[100, 100, 100, 100, 70])
    comm_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_GRAY),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(comm_table)
    
    doc.build(story)
    buffer.seek(0)
    
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Commission_Summary_{summary['center']}_{summary['period']}.pdf"}
    )

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
        
        # Get total sales
        sales_records = await db.daily_sales.find({
            "center": center,
            "date": {"$gte": start_date, "$lt": end_date}
        }, {"total_sale": 1}).to_list(100)
        
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
        # India: Net Revenue = Total Sales - Commissions - GST (if applicable) - NO expense deduction
        # Outside India: Net Profit = Total Sales - Expenses - Commissions
        franchise_country = franchise.get("country", "India") if franchise else "India"
        gst_applicable_india = franchise.get("gst_applicable", False) if franchise else False
        
        if franchise_country == "India":
            # India: Net Revenue = Sales - Commissions - GST on sales (if applicable)
            # NOTE: Expenses are NOT deducted for India revenue share calculation
            gst_on_sales = total_sale * 0.05 if gst_applicable_india else 0  # 5% GST on food sales
            net_revenue_for_share = max(0, total_sale - total_commission - gst_on_sales)
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

    await check_access(token)

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
    buf = io.BytesIO()

    rows = []
    for m in monthly_data:
        month_label = datetime.strptime(m["month"] + "-01", "%Y-%m-%d").strftime("%b %Y")
        rows.append({
            "Month": month_label,
            "Total Sales": m.get("total_sales", 0),
            "Revenue Share": m.get("revenue_share", 0),
            "MG Amount": m.get("mg_amount", 0),
            "Type": "MG" if m.get("payable_type") == "mg" else "Revenue Share",
            "Payable": m.get("payable_amount", 0),
            "Paid": m.get("paid", 0),
            "Pending": m.get("pending", 0),
            "Status": m.get("status", "").capitalize()
        })

    # Add totals row
    rows.append({
        "Month": "TOTAL",
        "Total Sales": sum(m.get("total_sales", 0) for m in monthly_data),
        "Revenue Share": totals.get("revenue_share", 0),
        "MG Amount": totals.get("mg", 0),
        "Type": "",
        "Payable": totals.get("payable", 0),
        "Paid": totals.get("paid", 0),
        "Pending": totals.get("pending", 0),
        "Status": ""
    })

    df = pd.DataFrame(rows)

    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        # Write header info
        header_df = pd.DataFrame([
            ["MG Payout Report"],
            [f"Center: {center}"],
            [f"Franchise: {franchise_info.get('name', 'N/A')} ({franchise_info.get('code', 'N/A')})"],
            [f"Monthly MG: {franchise_info.get('mg_amount', 0)}"],
            [f"Period: {period.get('from', '')} to {period.get('to', '')}"],
            [""]
        ])
        header_df.to_excel(writer, sheet_name='MG Payout', index=False, header=False, startrow=0)
        df.to_excel(writer, sheet_name='MG Payout', index=False, startrow=7)

        # Auto-adjust column widths
        ws = writer.sheets['MG Payout']
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 20)

    buf.seek(0)
    filename = f"MG_Payout_{center}_{period.get('from', 'start')}_to_{period.get('to', 'end')}.xlsx"
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


def _export_mg_pdf(center, monthly_data, totals, period, franchise_info):
    """Generate MG Payout PDF export"""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    # Logo
    from pathlib import Path
    ROOT_DIR = Path(__file__).parent.parent
    logo_path = ROOT_DIR / "assets" / "pb_logo.png"
    if logo_path.exists():
        try:
            elements.append(Image(str(logo_path), width=1.2*inch, height=0.7*inch))
        except:
            pass

    # Title
    title_style = ParagraphStyle('MGTitle', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=6)
    elements.append(Paragraph("MG Payout Report", title_style))
    elements.append(Spacer(1, 6))

    # Sub-header info
    sub_style = ParagraphStyle('MGSub', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, textColor=colors.gray)
    elements.append(Paragraph(f"Center: {center} | Franchise: {franchise_info.get('name', 'N/A')} ({franchise_info.get('code', 'N/A')})", sub_style))
    elements.append(Paragraph(f"Monthly MG: Rs. {franchise_info.get('mg_amount', 0):,.2f} | Period: {period.get('from', '')} to {period.get('to', '')}", sub_style))
    elements.append(Spacer(1, 12))

    # Summary cards as a table
    summary_data_table = [
        ["Total Revenue Share", "Total MG", "Total Payable", "Total Paid", "Total Pending"],
        [
            f"Rs. {totals.get('revenue_share', 0):,.2f}",
            f"Rs. {totals.get('mg', 0):,.2f}",
            f"Rs. {totals.get('payable', 0):,.2f}",
            f"Rs. {totals.get('paid', 0):,.2f}",
            f"Rs. {totals.get('pending', 0):,.2f}"
        ]
    ]
    summary_table = Table(summary_data_table, colWidths=[105, 95, 95, 95, 95])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, 1), 9),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 16))

    # Monthly data table
    table_header = ["Month", "Total Sales", "Rev Share", "MG", "Type", "Payable", "Paid", "Pending", "Status"]
    table_rows = [table_header]

    for m in monthly_data:
        month_label = datetime.strptime(m["month"] + "-01", "%Y-%m-%d").strftime("%b %Y")
        ptype = "MG" if m.get("payable_type") == "mg" else "RS"
        table_rows.append([
            month_label,
            f'{m.get("total_sales", 0):,.0f}',
            f'{m.get("revenue_share", 0):,.0f}',
            f'{m.get("mg_amount", 0):,.0f}',
            ptype,
            f'{m.get("payable_amount", 0):,.0f}',
            f'{m.get("paid", 0):,.0f}',
            f'{m.get("pending", 0):,.0f}',
            m.get("status", "").capitalize()
        ])

    # Totals row
    table_rows.append([
        "TOTAL",
        f'{sum(m.get("total_sales", 0) for m in monthly_data):,.0f}',
        f'{totals.get("revenue_share", 0):,.0f}',
        f'{totals.get("mg", 0):,.0f}',
        "",
        f'{totals.get("payable", 0):,.0f}',
        f'{totals.get("paid", 0):,.0f}',
        f'{totals.get("pending", 0):,.0f}',
        ""
    ])

    col_widths = [55, 65, 60, 60, 35, 65, 60, 60, 45]
    data_table = Table(table_rows, colWidths=col_widths, repeatRows=1)

    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (4, 0), (4, -1), 'CENTER'),
        ('ALIGN', (-1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8fafc')]),
        # Totals row styling
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f1f5f9')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]

    # Color-code status column
    for i, m in enumerate(monthly_data, start=1):
        status = m.get("status", "")
        if status == "paid":
            table_style.append(('TEXTCOLOR', (-1, i), (-1, i), colors.HexColor('#166534')))
        elif status == "partial":
            table_style.append(('TEXTCOLOR', (-1, i), (-1, i), colors.HexColor('#92400e')))
        elif status == "unpaid":
            table_style.append(('TEXTCOLOR', (-1, i), (-1, i), colors.HexColor('#991b1b')))

    data_table.setStyle(TableStyle(table_style))
    elements.append(data_table)
    elements.append(Spacer(1, 20))

    # Footer
    footer_style = ParagraphStyle('MGFooter', parent=styles['Normal'], fontSize=7, textColor=colors.gray, alignment=TA_CENTER)
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')} | Purnabramha - MANASWINI FOODS PVT. LTD.", footer_style))

    doc.build(elements)
    buf.seek(0)
    filename = f"MG_Payout_{center}_{period.get('from', 'start')}_to_{period.get('to', 'end')}.pdf"
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
