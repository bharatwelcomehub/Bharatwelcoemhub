# =======================================
# Center Accounts Routes
# Financial Management, Commission Processing, PIB Generation
# =======================================

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
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

# Colors for PDF
BRAND_MAROON = colors.HexColor("#800020")
BRAND_GOLD = colors.HexColor("#C9A227")
BRAND_NAVY = colors.HexColor("#1a365d")
DARK_GRAY = colors.HexColor("#374151")
LIGHT_GRAY = colors.HexColor("#f3f4f6")

# =======================================
# PYDANTIC MODELS
# =======================================

class CommissionStatementUpload(BaseModel):
    platform: str  # swiggy, zomato, doordash, card_settlement
    center: str
    settlement_period_start: str  # YYYY-MM-DD
    settlement_period_end: str
    gross_order_amount: float
    commission_charged: float
    net_payout_received: float
    notes: Optional[str] = ""

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
    if "australia" in country or center.get("code", "").upper() == "PB-PERTH":
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
    
    # Aggregate sales data
    total_sale = sum(r.get("total_sale", 0) for r in sales_records)
    direct_sale = sum(r.get("sale_pbm", 0) + r.get("sale_other", 0) for r in sales_records)
    
    # Aggregator sales
    swiggy_sale = sum(r.get("swiggy", 0) for r in sales_records)
    zomato_sale = sum(r.get("zomato", 0) for r in sales_records)
    doordash_sale = sum(r.get("doordash", 0) for r in sales_records)
    aggregator_sale = swiggy_sale + zomato_sale + doordash_sale
    
    # Card/Online sales
    card_sale = sum(r.get("card_idfc", 0) for r in sales_records)
    bharat_pay = sum(r.get("bharat_pay", 0) for r in sales_records)
    online_other = sum(r.get("online_other", 0) for r in sales_records)
    
    total_online_sale = sum(r.get("total_online_sale", 0) for r in sales_records)
    total_cash_sale = sum(r.get("total_cash_sale", 0) for r in sales_records)
    
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
    # 3. Fetch Commission Statements
    # ==========================================
    commission_query = {
        "center": req.center,
        "settlement_period_start": {"$gte": start_date},
        "settlement_period_end": {"$lt": end_date}
    }
    
    commission_records = await db.commission_statements.find(commission_query, {"_id": 0}).to_list(100)
    
    # Aggregate commissions by platform
    commission_by_platform = {
        "swiggy": {"gross": 0, "commission": 0, "net": 0},
        "zomato": {"gross": 0, "commission": 0, "net": 0},
        "doordash": {"gross": 0, "commission": 0, "net": 0},
        "card_settlement": {"gross": 0, "commission": 0, "net": 0}
    }
    
    for comm in commission_records:
        platform = comm.get("platform", "").lower()
        if platform in commission_by_platform:
            commission_by_platform[platform]["gross"] += comm.get("gross_order_amount", 0)
            commission_by_platform[platform]["commission"] += comm.get("commission_charged", 0)
            commission_by_platform[platform]["net"] += comm.get("net_payout_received", 0)
    
    total_aggregator_commission = (
        commission_by_platform["swiggy"]["commission"] +
        commission_by_platform["zomato"]["commission"] +
        commission_by_platform["doordash"]["commission"]
    )
    card_commission = commission_by_platform["card_settlement"]["commission"]
    
    # ==========================================
    # 4. Calculate Financial Summary
    # ==========================================
    
    # Net Revenue = Total Sales - Expenses - Commissions
    total_commission = total_aggregator_commission + card_commission
    net_revenue = total_sale - total_expenses - total_commission
    
    # Calculate share payable based on country
    # 80% goes to Franchise Owner, 20% goes to Purnabramha LLC
    franchise_owner_percentage = 80
    purnabramha_percentage = 20
    
    if country == "Australia":
        # Australia: Profit share model (% of net profit)
        profit_before_share = net_revenue
        purnabramha_share = profit_before_share * (purnabramha_percentage / 100)
        franchise_owner_share = profit_before_share * (franchise_owner_percentage / 100)
        share_type = "profit_share"
    else:
        # India: Revenue share model (% of total sales)
        purnabramha_share = total_sale * (purnabramha_percentage / 100)
        franchise_owner_share = total_sale * (franchise_owner_percentage / 100)
        share_type = "revenue_share"
    
    # Apply GST on Purnabramha's share (payable by franchise to Purnabramha)
    purnabramha_share_with_tax = calculate_taxes(purnabramha_share, country, share_type)
    
    # Working Capital - DO NOT touch/calculate
    # Working capital is security deposit, only show initial amount
    # Usage will be handled as separate LOAN entries
    working_capital = franchise.get("working_capital", 0) if franchise else 0
    
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
            "by_platform": commission_by_platform
        },
        "financial_summary": {
            "total_sales": round(total_sale, 2),
            "total_expenses": round(total_expenses, 2),
            "total_commissions": round(total_commission, 2),
            "net_revenue": round(net_revenue, 2),
            "working_capital": round(working_capital, 2)  # Just show initial, no calculation
        },
        "share_calculation": {
            "type": share_type,
            "net_profit_or_sales": round(net_revenue if country == "Australia" else total_sale, 2),
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
                "total_payable": round(purnabramha_share_with_tax.get("total_with_gst", purnabramha_share), 2)
            }
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
# COMMISSION STATEMENT UPLOAD
# =======================================

@router.post("/upload-commission")
async def upload_commission_statement(
    token: str = Form(...),
    platform: str = Form(...),
    center: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload commission statement file (CSV/Excel) for parsing"""
    session = await check_access(token)
    
    # Validate platform
    valid_platforms = ["swiggy", "zomato", "doordash", "card_settlement"]
    if platform.lower() not in valid_platforms:
        raise HTTPException(400, f"Invalid platform. Must be one of: {valid_platforms}")
    
    # Validate center
    center_info = await get_center_details(center)
    country = get_country_from_center(center_info)
    
    # Validate platform for country
    if country == "Australia" and platform.lower() in ["swiggy", "zomato"]:
        raise HTTPException(400, f"{platform} is not available for Australia. Use DoorDash or Card Settlement.")
    if country == "India" and platform.lower() == "doordash":
        raise HTTPException(400, "DoorDash is not available for India. Use Swiggy or Zomato.")
    
    # Read file
    try:
        content = await file.read()
        
        # Parse based on file type
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif file.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(400, "File must be CSV or Excel (.xlsx/.xls)")
        
        # Basic parsing - try to find relevant columns
        # This is a simplified parser - real implementation would need platform-specific parsing
        parsed_data = {
            "platform": platform.lower(),
            "center": center,
            "rows_found": len(df),
            "columns": list(df.columns),
            "preview": df.head(5).to_dict(orient="records") if len(df) > 0 else []
        }
        
        return {
            "success": True,
            "message": f"File parsed successfully. Found {len(df)} rows.",
            "parsed_data": parsed_data,
            "instructions": "Review the data and submit commission details using /api/center-accounts/save-commission"
        }
        
    except Exception as e:
        logger.error(f"Error parsing commission file: {e}")
        raise HTTPException(400, f"Error parsing file: {str(e)}")

@router.post("/save-commission")
async def save_commission_statement(data: dict):
    """Save commission statement data"""
    token = data.get("token")
    session = await check_access(token)
    
    # Extract commission data
    commission = CommissionStatementUpload(
        platform=data.get("platform"),
        center=data.get("center"),
        settlement_period_start=data.get("settlement_period_start"),
        settlement_period_end=data.get("settlement_period_end"),
        gross_order_amount=data.get("gross_order_amount", 0),
        commission_charged=data.get("commission_charged", 0),
        net_payout_received=data.get("net_payout_received", 0),
        notes=data.get("notes", "")
    )
    
    # Check for duplicate
    existing = await db.commission_statements.find_one({
        "platform": commission.platform.lower(),
        "center": commission.center,
        "settlement_period_start": commission.settlement_period_start,
        "settlement_period_end": commission.settlement_period_end
    })
    
    if existing:
        raise HTTPException(400, "Commission statement for this period already exists")
    
    # Save to database
    doc = commission.dict()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    doc["created_by"] = session.get("managerName", "Unknown")
    doc["platform"] = doc["platform"].lower()
    
    await db.commission_statements.insert_one(doc)
    
    return {"success": True, "message": "Commission statement saved successfully"}

@router.post("/list-commissions")
async def list_commission_statements(data: dict):
    """List commission statements for a center"""
    token = data.get("token")
    session = await check_access(token)
    
    center = data.get("center")
    month = data.get("month")  # Optional YYYY-MM filter
    
    query = {"center": center}
    
    if month:
        try:
            year, m = month.split("-")
            start_date = f"{year}-{int(m):02d}-01"
            if int(m) == 12:
                end_date = f"{int(year) + 1}-01-01"
            else:
                end_date = f"{year}-{int(m) + 1:02d}-01"
            query["settlement_period_start"] = {"$gte": start_date, "$lt": end_date}
        except:
            pass
    
    statements = await db.commission_statements.find(query, {"_id": 0}).sort("settlement_period_start", -1).to_list(100)
    
    return {"success": True, "statements": statements, "total": len(statements)}

@router.post("/delete-commission/{commission_id}")
async def delete_commission_statement(commission_id: str, data: dict):
    """Delete a commission statement"""
    token = data.get("token")
    session = await check_access(token)
    
    result = await db.commission_statements.delete_one({"_id": commission_id})
    
    if result.deleted_count == 0:
        raise HTTPException(404, "Commission statement not found")
    
    return {"success": True, "message": "Commission statement deleted"}

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
        ["Platform", "Gross Amount", "Commission", "Net Payout"],
    ]
    
    for platform, data in commissions["by_platform"].items():
        if data["gross"] > 0 or data["commission"] > 0:
            commission_data.append([
                platform.title().replace("_", " "),
                f"{currency} {data['gross']:,.2f}",
                f"{currency} {data['commission']:,.2f}",
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
    fin_data = [
        ["Description", "Amount"],
        ["Total Sales", f"{currency} {fin['total_sales']:,.2f}"],
        ["Less: Total Expenses", f"({currency} {fin['total_expenses']:,.2f})"],
        ["Less: Total Commissions", f"({currency} {fin['total_commissions']:,.2f})"],
        ["NET REVENUE", f"{currency} {fin['net_revenue']:,.2f}"],
        ["", ""],
        ["Working Capital (Security Deposit)", f"{currency} {fin['working_capital']:,.2f}"],
    ]
    
    fin_table = Table(fin_data, colWidths=[280, 170])
    fin_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 4), (-1, 4), BRAND_GOLD),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
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
        ["Revenue/Profit Share", f"{currency} {summary['share_calculation']['base_amount']:,.2f}", f"{tax_rules['share_gst_rate']:.0f}%", f"{currency} {summary['share_calculation']['gst_amount']:,.2f}"],
    ]
    
    if summary["country"] == "India":
        gst_data.append(["  - CGST (9%)", "", "", f"{currency} {summary['share_calculation']['cgst']:,.2f}"])
        gst_data.append(["  - SGST (9%)", "", "", f"{currency} {summary['share_calculation']['sgst']:,.2f}"])
    
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
    
    comm_data = [["Platform", "Gross Orders", "Commission Charged", "Net Payout", "Commission %"]]
    
    for platform, data in commissions["by_platform"].items():
        comm_pct = (data["commission"] / data["gross"] * 100) if data["gross"] > 0 else 0
        comm_data.append([
            platform.title().replace("_", " "),
            f"{currency} {data['gross']:,.2f}",
            f"{currency} {data['commission']:,.2f}",
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
