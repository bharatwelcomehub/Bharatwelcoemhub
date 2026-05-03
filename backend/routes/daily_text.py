# =======================================
# Daily Sales Text Generator
# WhatsApp-style daily summary from sales + expense data
# =======================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/daily-text", tags=["Daily Text Generator"])

db = None
verify_token = None
has_admin_access = None

def set_db(database):
    global db
    db = database

def set_verify_token(func):
    global verify_token
    verify_token = func

def set_has_admin_access(func):
    global has_admin_access
    has_admin_access = func


class TextGenRequest(BaseModel):
    token: str
    center: str
    date: str  # YYYY-MM-DD
    overrides: Optional[dict] = None  # Manual overrides for any field


class WeeklyTextRequest(BaseModel):
    token: str
    center: str
    week_date: str  # any YYYY-MM-DD inside the desired week; backend snaps to Mon-Sun
    overrides: Optional[dict] = None


class MonthlyTextRequest(BaseModel):
    token: str
    center: str
    month: str  # YYYY-MM
    overrides: Optional[dict] = None


class YearlyTextRequest(BaseModel):
    token: str
    center: str
    year: int  # India: FY starting year (2026 = Apr 2026 → Mar 2027). International: calendar year.
    overrides: Optional[dict] = None


class PdfDownloadRequest(BaseModel):
    token: str
    center: str
    period_type: str  # "daily" | "weekly" | "monthly" | "yearly"
    # One of these depending on period_type:
    date: Optional[str] = None       # for daily (YYYY-MM-DD)
    week_date: Optional[str] = None  # for weekly (any date in the week)
    month: Optional[str] = None      # for monthly (YYYY-MM)
    year: Optional[int] = None       # for yearly
    include_chart: bool = False      # opt-in graphical representation


@router.post("/generate-weekly")
async def generate_weekly_text(req: WeeklyTextRequest):
    """Generate WhatsApp-style WEEKLY summary text aggregated from daily sales + expenses.
    Week is Monday → Sunday containing the supplied date.
    """
    from datetime import timedelta
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    center = req.center.upper()
    is_admin = has_admin_access(session)
    is_franchise_owner = session.get("role_key") == "franchise_owner"

    if not is_admin:
        user_center = session.get("center", "")
        if user_center != center:
            raise HTTPException(403, "You can only generate text for your own center")

    # Snap to Mon-Sun
    try:
        anchor = datetime.strptime(req.week_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "week_date must be YYYY-MM-DD")
    
    week_start = anchor - timedelta(days=anchor.weekday())  # Monday
    week_end = week_start + timedelta(days=6)  # Sunday
    date_strs = [(week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    data, sales, expenses, is_international = await _aggregate_period(center, date_strs)
    data["week_start"] = week_start.strftime("%Y-%m-%d")
    data["week_end"] = week_end.strftime("%Y-%m-%d")

    # Apply overrides
    if req.overrides:
        for key, val in req.overrides.items():
            if key in data and val is not None:
                data[key] = val
            elif key == "expense_categories" and isinstance(val, list):
                data["expense_categories"] = val

    text = _format_period_whatsapp_text(data, period_type="week")

    return {
        "success": True,
        "text": text,
        "data": data,
        "has_sales_data": len(sales) > 0,
        "expense_count": len(expenses),
        "sales_days": len(sales),
        "center": center,
        "week_start": data["week_start"],
        "week_end": data["week_end"],
        "is_international": is_international,
        "can_edit": is_admin or not is_franchise_owner,
    }


@router.post("/generate-monthly")
async def generate_monthly_text(req: MonthlyTextRequest):
    """Generate WhatsApp-style MONTHLY summary text aggregated from daily sales + expenses.
    """
    from datetime import timedelta
    import calendar
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    center = req.center.upper()
    is_admin = has_admin_access(session)
    is_franchise_owner = session.get("role_key") == "franchise_owner"

    if not is_admin:
        user_center = session.get("center", "")
        if user_center != center:
            raise HTTPException(403, "You can only generate text for your own center")

    # Validate YYYY-MM
    try:
        year, month = req.month.split("-")
        year_i, month_i = int(year), int(month)
        first_day = datetime(year_i, month_i, 1).date()
        last_day_num = calendar.monthrange(year_i, month_i)[1]
        last_day = datetime(year_i, month_i, last_day_num).date()
    except (ValueError, AttributeError):
        raise HTTPException(400, "month must be YYYY-MM")
    
    date_strs = [(first_day + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(last_day_num)]

    data, sales, expenses, is_international = await _aggregate_period(center, date_strs)
    data["month_start"] = first_day.strftime("%Y-%m-%d")
    data["month_end"] = last_day.strftime("%Y-%m-%d")
    data["month"] = req.month

    if req.overrides:
        for key, val in req.overrides.items():
            if key in data and val is not None:
                data[key] = val
            elif key == "expense_categories" and isinstance(val, list):
                data["expense_categories"] = val

    text = _format_period_whatsapp_text(data, period_type="month")

    return {
        "success": True,
        "text": text,
        "data": data,
        "has_sales_data": len(sales) > 0,
        "expense_count": len(expenses),
        "sales_days": len(sales),
        "center": center,
        "month": req.month,
        "month_start": data["month_start"],
        "month_end": data["month_end"],
        "is_international": is_international,
        "can_edit": is_admin or not is_franchise_owner,
    }


async def _resolve_is_international(center: str) -> bool:
    """Look up if a center is international (non-India)."""
    center_doc = await db.centers.find_one({"code": center}, {"_id": 0}) or \
                 await db.centers.find_one({"code": {"$regex": f"^{center}$", "$options": "i"}}, {"_id": 0})
    return bool(center_doc and (center_doc.get("is_india_center") is False or
                                 (center_doc.get("country") and center_doc.get("country") != "India")))


@router.post("/generate-yearly")
async def generate_yearly_text(req: YearlyTextRequest):
    """Generate WhatsApp-style YEARLY summary aggregated from daily sales + expenses.
    
    Year period is determined by center country:
      - India centers: Financial Year — Apr 1 (req.year) to Mar 31 (req.year + 1).
        e.g. year=2026 → FY 2026-27 = 01 Apr 2026 → 31 Mar 2027.
      - International centers (e.g. PB-PERTH): Calendar Year — Jan 1 to Dec 31.
    """
    from datetime import timedelta
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    center = req.center.upper()
    is_admin = has_admin_access(session)
    is_franchise_owner = session.get("role_key") == "franchise_owner"

    if not is_admin:
        user_center = session.get("center", "")
        if user_center != center:
            raise HTTPException(403, "You can only generate text for your own center")

    if not isinstance(req.year, int) or req.year < 2015 or req.year > 2100:
        raise HTTPException(400, "year must be a valid integer between 2015 and 2100")

    is_international = await _resolve_is_international(center)
    
    if is_international:
        # Calendar Year
        first_day = datetime(req.year, 1, 1).date()
        last_day = datetime(req.year, 12, 31).date()
        period_label = f"CY {req.year} (Jan-Dec {req.year})"
    else:
        # Indian Financial Year: Apr 1 (year) → Mar 31 (year + 1)
        first_day = datetime(req.year, 4, 1).date()
        last_day = datetime(req.year + 1, 3, 31).date()
        period_label = f"FY {req.year}-{str(req.year + 1)[-2:]} (Apr {req.year} - Mar {req.year + 1})"

    total_days = (last_day - first_day).days + 1
    date_strs = [(first_day + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(total_days)]

    data, sales, expenses, _ = await _aggregate_period(center, date_strs)
    data["year_start"] = first_day.strftime("%Y-%m-%d")
    data["year_end"] = last_day.strftime("%Y-%m-%d")
    data["year_label"] = period_label
    data["fy_start_year"] = req.year
    data["is_international"] = is_international

    if req.overrides:
        for key, val in req.overrides.items():
            if key in data and val is not None:
                data[key] = val
            elif key == "expense_categories" and isinstance(val, list):
                data["expense_categories"] = val

    text = _format_period_whatsapp_text(data, period_type="year")

    return {
        "success": True,
        "text": text,
        "data": data,
        "has_sales_data": len(sales) > 0,
        "expense_count": len(expenses),
        "sales_days": len(sales),
        "center": center,
        "year_start": data["year_start"],
        "year_end": data["year_end"],
        "year_label": period_label,
        "is_international": is_international,
        "can_edit": is_admin or not is_franchise_owner,
    }


@router.post("/download-pdf")
async def download_text_pdf(req: PdfDownloadRequest):
    """Download a branded PDF of the daily/weekly/monthly/yearly summary text.
    
    Available to all roles (Super Admin, Admin, Accountant, Center Manager, Franchise Owner)
    — Franchise Owners are restricted to their own center.
    """
    from datetime import timedelta
    import calendar
    from fastapi.responses import Response
    
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    center = req.center.upper()
    is_admin = has_admin_access(session)
    
    if not is_admin:
        user_center = session.get("center", "")
        if user_center != center:
            raise HTTPException(403, "You can only download PDFs for your own center")

    period_type = (req.period_type or "").lower()
    if period_type not in ("daily", "weekly", "monthly", "yearly"):
        raise HTTPException(400, "period_type must be one of: daily, weekly, monthly, yearly")

    # Compute the data for the requested period
    is_international = await _resolve_is_international(center)
    
    text_body = ""
    period_label = ""
    chart_series = []
    
    if period_type == "daily":
        if not req.date:
            raise HTTPException(400, "date (YYYY-MM-DD) is required for daily PDF")
        # Reuse the daily generation logic
        sale = await db.daily_sales.find_one(
            {"center": {"$regex": f"^{center}$", "$options": "i"}, "date": req.date}, {"_id": 0}
        )
        expenses = await db.expenses.find(
            {"center": {"$regex": f"^{center}$", "$options": "i"}, "date": req.date}, {"_id": 0}
        ).to_list(500)
        online_expense = sum(float(e.get("amount", 0) or 0) for e in expenses
                             if (e.get("payment_mode") or "CASH").upper() in ("ONLINE", "BANK", "UPI", "TRANSFER", "NEFT", "IMPS"))
        cash_expense_total = sum(float(e.get("amount", 0) or 0) for e in expenses) - online_expense
        d_data = {
            "date": req.date, "opening_balance": 0, "deposit": 0, "withdrawal": 0,
            "total_sale": 0, "card": 0, "phone_pay": 0, "swiggy": 0, "zomato": 0,
            "due_amount": 0, "cash_sale": 0, "online_expense": round(online_expense, 2),
            "cash_expense": round(cash_expense_total, 2), "cash_in_hand": 0,
            "petty_cash_balance": 0, "total_guests": 0, "apc": 0,
            "num_drinks": 0, "num_sides": 0, "cancelled_zomato": 0, "cancelled_swiggy": 0,
        }
        if sale:
            d_data["opening_balance"] = float(sale.get("opening_balance", 0))
            d_data["deposit"] = float(sale.get("deposited_in_bank", 0))
            d_data["withdrawal"] = float(sale.get("cash_receipts", 0))
            d_data["total_sale"] = float(sale.get("total_sale", 0))
            d_data["card"] = float(sale.get("card_idfc", 0))
            d_data["phone_pay"] = float(sale.get("bharat_pay", 0))
            d_data["swiggy"] = float(sale.get("swiggy", 0))
            d_data["zomato"] = float(sale.get("zomato", 0))
            d_data["due_amount"] = float(sale.get("due_amount", 0))
            d_data["cash_sale"] = float(sale.get("total_cash_sale", 0))
            d_data["cash_in_hand"] = float(sale.get("closing_balance", 0))
            d_data["petty_cash_balance"] = float(sale.get("petty_cash_closing", 0))
            d_data["total_guests"] = int(sale.get("num_guests", 0))
            d_data["apc"] = round(float(sale.get("avg_per_pax", 0)), 0)
        try:
            display_date = datetime.strptime(req.date, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            display_date = req.date
        text_body = _format_whatsapp_text(d_data, display_date)
        period_label = f"Daily Report — {display_date}"
        # Single-day chart with one bar pair
        chart_series = [{
            "label": display_date,
            "date": req.date,
            "sales": round(float(d_data["total_sale"]), 2),
            "expenses": round(online_expense + cash_expense_total, 2),
        }]
    
    elif period_type == "weekly":
        if not req.week_date:
            raise HTTPException(400, "week_date (YYYY-MM-DD) is required for weekly PDF")
        try:
            anchor = datetime.strptime(req.week_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "week_date must be YYYY-MM-DD")
        week_start = anchor - timedelta(days=anchor.weekday())
        week_end = week_start + timedelta(days=6)
        date_strs = [(week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        data, _, _, _ = await _aggregate_period(center, date_strs)
        data["week_start"] = week_start.strftime("%Y-%m-%d")
        data["week_end"] = week_end.strftime("%Y-%m-%d")
        text_body = _format_period_whatsapp_text(data, period_type="week")
        period_label = f"Weekly Report — {week_start.strftime('%d %b %Y')} to {week_end.strftime('%d %b %Y')}"
        chart_series = data.get("chart_series", [])
    
    elif period_type == "monthly":
        if not req.month:
            raise HTTPException(400, "month (YYYY-MM) is required for monthly PDF")
        try:
            yr, mo = req.month.split("-")
            yr_i, mo_i = int(yr), int(mo)
            first_day = datetime(yr_i, mo_i, 1).date()
            last_day_num = calendar.monthrange(yr_i, mo_i)[1]
            last_day = datetime(yr_i, mo_i, last_day_num).date()
        except (ValueError, AttributeError):
            raise HTTPException(400, "month must be YYYY-MM")
        date_strs = [(first_day + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(last_day_num)]
        data, _, _, _ = await _aggregate_period(center, date_strs)
        data["month_start"] = first_day.strftime("%Y-%m-%d")
        data["month_end"] = last_day.strftime("%Y-%m-%d")
        data["month"] = req.month
        text_body = _format_period_whatsapp_text(data, period_type="month")
        period_label = f"Monthly Report — {first_day.strftime('%B %Y')}"
        chart_series = data.get("chart_series", [])
    
    else:  # yearly
        if not req.year or not isinstance(req.year, int):
            raise HTTPException(400, "year (int) is required for yearly PDF")
        if is_international:
            first_day = datetime(req.year, 1, 1).date()
            last_day = datetime(req.year, 12, 31).date()
            period_label_inner = f"CY {req.year} (Jan-Dec {req.year})"
        else:
            first_day = datetime(req.year, 4, 1).date()
            last_day = datetime(req.year + 1, 3, 31).date()
            period_label_inner = f"FY {req.year}-{str(req.year + 1)[-2:]} (Apr {req.year} - Mar {req.year + 1})"
        total_days = (last_day - first_day).days + 1
        date_strs = [(first_day + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(total_days)]
        data, _, _, _ = await _aggregate_period(center, date_strs)
        data["year_start"] = first_day.strftime("%Y-%m-%d")
        data["year_end"] = last_day.strftime("%Y-%m-%d")
        data["year_label"] = period_label_inner
        data["is_international"] = is_international
        text_body = _format_period_whatsapp_text(data, period_type="year")
        period_label = f"Yearly Report — {period_label_inner}"
        chart_series = data.get("chart_series", [])

    # Look up center info for header
    center_doc = await db.centers.find_one({"code": center}, {"_id": 0}) or \
                 await db.centers.find_one({"code": {"$regex": f"^{center}$", "$options": "i"}}, {"_id": 0}) or {}
    center_name = center_doc.get("name", center)

    # Build branded PDF
    pdf_bytes = _build_text_summary_pdf(
        title="Sales Text Report",
        period_label=period_label,
        center_code=center,
        center_name=center_name,
        text_body=text_body,
        manager_name=session.get("managerName", ""),
        chart_series=chart_series if req.include_chart else None,
    )
    
    safe_label = period_label.replace(" ", "_").replace("/", "-").replace("—", "-")
    filename = f"{center}_{period_type}_{safe_label}.pdf"[:120] + ".pdf" if not f"{center}_{period_type}_{safe_label}".endswith(".pdf") else f"{center}_{period_type}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_text_summary_pdf(title: str, period_label: str, center_code: str,
                             center_name: str, text_body: str, manager_name: str,
                             chart_series: list = None) -> bytes:
    """Render a branded Purnabramha PDF containing the WhatsApp-style summary text."""
    import io as _io
    from pathlib import Path as _Path
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Preformatted
    )
    
    BRAND_MAROON = colors.HexColor("#800020")
    BRAND_GOLD = colors.HexColor("#C9A227")
    BRAND_NAVY = colors.HexColor("#1a365d")
    LIGHT_GRAY = colors.HexColor("#f3f4f6")
    
    buf = _io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=15 * mm, bottomMargin=15 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BrandTitle", fontSize=22, textColor=BRAND_MAROON,
                              fontName="Helvetica-Bold", alignment=1, spaceAfter=2 * mm))
    styles.add(ParagraphStyle(name="BrandSub", fontSize=10, textColor=BRAND_NAVY,
                              fontName="Helvetica", alignment=1, spaceAfter=4 * mm))
    styles.add(ParagraphStyle(name="ReportTitle", fontSize=14, textColor=BRAND_NAVY,
                              fontName="Helvetica-Bold", spaceBefore=4 * mm, spaceAfter=2 * mm))
    styles.add(ParagraphStyle(name="MetaLabel", fontSize=9, textColor=colors.gray,
                              fontName="Helvetica"))
    styles.add(ParagraphStyle(name="Body", fontSize=10, fontName="Courier",
                              leading=14, textColor=colors.black))
    styles.add(ParagraphStyle(name="Footer", fontSize=8, textColor=colors.gray,
                              fontName="Helvetica-Oblique", alignment=1))

    story = []
    
    # Header band: logo + brand name
    logo_path = _Path("/app/backend/assets/pb_logo.png")
    header_cells = []
    if logo_path.exists():
        try:
            logo_img = Image(str(logo_path), width=20 * mm, height=20 * mm)
            header_cells.append(logo_img)
        except Exception:
            header_cells.append(Paragraph("", styles["Normal"]))
    else:
        header_cells.append(Paragraph("", styles["Normal"]))

    brand_block = [
        Paragraph("Purnabramha", styles["BrandTitle"]),
        Paragraph("Authentic Maharashtrian Cuisine | IntraPB Sales Report",
                  styles["BrandSub"]),
    ]
    
    header_tbl = Table(
        [[header_cells[0], brand_block]],
        colWidths=[28 * mm, 140 * mm],
    )
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 0), (-1, -1), 1.5, BRAND_GOLD),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 4 * mm))
    
    # Report title
    story.append(Paragraph(title, styles["ReportTitle"]))
    
    # Meta info table
    meta = [
        ["Center:", f"{center_code} — {center_name}"],
        ["Period:", period_label],
        ["Generated:", datetime.now().strftime("%d %b %Y, %H:%M")],
    ]
    if manager_name:
        meta.append(["Generated by:", manager_name])
    meta_tbl = Table(meta, colWidths=[28 * mm, 140 * mm])
    meta_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_MAROON),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 4 * mm))
    
    # Sales vs Expenses chart (PNG generated with matplotlib)
    if chart_series:
        chart_png = _build_sales_vs_expenses_chart_png(chart_series, period_label)
        if chart_png:
            try:
                chart_buf = _io.BytesIO(chart_png)
                chart_img = Image(chart_buf, width=170 * mm, height=62 * mm)
                story.append(chart_img)
                story.append(Spacer(1, 4 * mm))
            except Exception as _e:
                logger.warning(f"Embedding chart image failed: {_e}")
    
    # Body — preserve formatting & emoji
    # Use Preformatted to maintain alignment of WhatsApp text
    body_box = Preformatted(text_body, ParagraphStyle(
        name="BodyPre", fontSize=10, fontName="Helvetica",
        leading=14, textColor=colors.black,
    ))
    body_tbl = Table([[body_box]], colWidths=[170 * mm])
    body_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, BRAND_NAVY),
    ]))
    story.append(body_tbl)
    
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        "This is a computer-generated report from the Purnabramha IntraPB platform. "
        "All values are derived from the Sales Dashboard at the time of generation.",
        styles["Footer"]
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


async def _aggregate_period(center: str, date_strs: list):
    """Shared aggregation for any list of dates (weekly/monthly/yearly).
    Returns (data_dict, sales_list, expenses_list, is_international_bool).
    """
    # Center info (for doordash visibility)
    center_doc = await db.centers.find_one({"code": center}, {"_id": 0}) or \
                 await db.centers.find_one({"code": {"$regex": f"^{center}$", "$options": "i"}}, {"_id": 0})
    is_international = bool(center_doc and (center_doc.get("is_india_center") is False or
                                             (center_doc.get("country") and center_doc.get("country") != "India")))

    sales = await db.daily_sales.find(
        {"center": {"$regex": f"^{center}$", "$options": "i"}, "date": {"$in": date_strs}},
        {"_id": 0}
    ).to_list(50)
    expenses = await db.expenses.find(
        {"center": {"$regex": f"^{center}$", "$options": "i"}, "date": {"$in": date_strs}},
        {"_id": 0}
    ).to_list(5000)

    def fsum(field):
        return sum(float(s.get(field, 0) or 0) for s in sales)

    total_sale = fsum("total_sale")
    total_card = fsum("card_idfc")
    total_deposit = fsum("deposited_in_bank")
    total_withdrawal = fsum("cash_receipts")
    total_swiggy = fsum("swiggy")
    total_zomato = fsum("zomato")
    total_doordash = fsum("doordash")
    total_paytm = fsum("paytm")
    total_bharat_pay = fsum("bharat_pay")
    total_cash_sale = fsum("total_cash_sale")
    total_guests = sum(int(s.get("num_guests", 0) or 0) for s in sales)

    # Cash In Hand = closing balance on the LAST day with a record
    cash_in_hand = 0.0
    for d in reversed(date_strs):
        match = next((s for s in sales if s.get("date") == d), None)
        if match:
            cash_in_hand = float(match.get("closing_balance", 0) or 0)
            break

    online_expense_total = 0.0
    cash_expense_total = 0.0
    by_category: dict = {}
    for exp in expenses:
        mode = (exp.get("payment_mode") or "CASH").upper()
        amt = float(exp.get("amount", 0) or 0)
        if mode in ("ONLINE", "BANK", "UPI", "TRANSFER", "NEFT", "IMPS", "CARD"):
            online_expense_total += amt
        else:
            cash_expense_total += amt
        cat = (exp.get("expense_type") or "").strip() or (exp.get("description") or "").strip() or "Other"
        cat_clean = cat.title()
        by_category[cat_clean] = by_category.get(cat_clean, 0) + amt

    top_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:6]

    apc = round(total_sale / total_guests, 0) if total_guests > 0 else 0

    # GST + Net Revenue (single source of truth — applies to all periods)
    from utils.gst import compute_gst_from_rows
    gst_calc = compute_gst_from_rows(sales, country=None, center=center)
    total_gst = gst_calc["gst_amount"]
    total_aggregator = gst_calc["aggregator_sale"]
    total_eligible = gst_calc["eligible_base"]
    total_commission = sum(float(s.get("card_idfc_commission", 0) or 0) for s in sales)  # placeholder: monthly commissions reside in monthly_commissions
    net_revenue = round(total_sale - total_commission - total_gst, 2)

    # Build chart series: sales vs expenses per bucket
    # Daily aggregations -> per-day series; long ranges -> auto-bucket by month
    chart_series = _build_chart_series(date_strs, sales, expenses)

    data = {
        "total_sale": round(total_sale, 2),
        "total_card": round(total_card, 2),
        "total_deposit": round(total_deposit, 2),
        "total_withdrawal": round(total_withdrawal, 2),
        "total_swiggy": round(total_swiggy, 2),
        "total_zomato": round(total_zomato, 2),
        "total_doordash": round(total_doordash, 2),
        "total_paytm": round(total_paytm, 2),
        "total_bharat_pay": round(total_bharat_pay, 2),
        "total_cash_sale": round(total_cash_sale, 2),
        "total_cash_expenses": round(cash_expense_total, 2),
        "total_online_expenses": round(online_expense_total, 2),
        "total_cash_in_hand": round(cash_in_hand, 2),
        "total_guests": int(total_guests),
        "apc": int(apc),
        "expense_categories": [{"name": k, "amount": round(v, 2)} for k, v in top_categories],
        "is_international": is_international,
        "chart_series": chart_series,
        "total_expenses": round(online_expense_total + cash_expense_total, 2),
        # New fields: surface GST chain so summaries everywhere stay consistent
        "total_gst": round(total_gst, 2),
        "total_aggregator_sale": round(total_aggregator, 2),
        "total_eligible_sale": round(total_eligible, 2),
        "total_commissions": round(total_commission, 2),
        "net_revenue": net_revenue,
    }
    return data, sales, expenses, is_international


def _build_chart_series(date_strs: list, sales: list, expenses: list) -> list:
    """Return a list of {label, sales, expenses} buckets.
    - For periods <= 31 days: one bucket per day.
    - For periods > 31 days: auto-bucket by YYYY-MM month label.
    """
    n = len(date_strs)
    if n <= 31:
        # Per-day buckets in date order
        sale_by_day = {s.get("date"): float(s.get("total_sale", 0) or 0) for s in sales}
        exp_by_day: dict = {}
        for e in expenses:
            d = e.get("date")
            if not d:
                continue
            exp_by_day[d] = exp_by_day.get(d, 0) + float(e.get("amount", 0) or 0)
        from datetime import datetime as _dt
        out = []
        for d in date_strs:
            try:
                lbl = _dt.strptime(d, "%Y-%m-%d").strftime("%d %b") if n > 7 else _dt.strptime(d, "%Y-%m-%d").strftime("%a %d")
            except ValueError:
                lbl = d
            out.append({
                "label": lbl,
                "date": d,
                "sales": round(sale_by_day.get(d, 0), 2),
                "expenses": round(exp_by_day.get(d, 0), 2),
            })
        return out
    else:
        # Bucket by year-month
        from datetime import datetime as _dt
        buckets: dict = {}
        for s in sales:
            d = s.get("date") or ""
            ym = d[:7]
            if not ym:
                continue
            buckets.setdefault(ym, {"sales": 0.0, "expenses": 0.0})
            buckets[ym]["sales"] += float(s.get("total_sale", 0) or 0)
        for e in expenses:
            d = e.get("date") or ""
            ym = d[:7]
            if not ym:
                continue
            buckets.setdefault(ym, {"sales": 0.0, "expenses": 0.0})
            buckets[ym]["expenses"] += float(e.get("amount", 0) or 0)
        # Walk through unique months in date_strs in chronological order
        seen = []
        for d in date_strs:
            ym = d[:7]
            if ym and ym not in seen:
                seen.append(ym)
        out = []
        for ym in seen:
            try:
                lbl = _dt.strptime(ym + "-01", "%Y-%m-%d").strftime("%b %y")
            except ValueError:
                lbl = ym
            b = buckets.get(ym, {"sales": 0, "expenses": 0})
            out.append({
                "label": lbl,
                "date": ym,
                "sales": round(b["sales"], 2),
                "expenses": round(b["expenses"], 2),
            })
        return out


def _build_sales_vs_expenses_chart_png(chart_series: list, period_label: str) -> bytes | None:
    """Render a Sales vs Expenses bar chart as PNG bytes using matplotlib."""
    if not chart_series:
        return None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import io as _io

        labels = [b["label"] for b in chart_series]
        sales = [b["sales"] for b in chart_series]
        expenses = [b["expenses"] for b in chart_series]

        fig, ax = plt.subplots(figsize=(9.5, 3.5), dpi=150)
        x = range(len(labels))
        width = 0.4
        bars1 = ax.bar([i - width / 2 for i in x], sales, width=width,
                       label="Sales", color="#800020", edgecolor="#5c0017")
        bars2 = ax.bar([i + width / 2 for i in x], expenses, width=width,
                       label="Expenses", color="#C9A227", edgecolor="#8a6f1b")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=45 if len(labels) > 8 else 0,
                           ha="right" if len(labels) > 8 else "center", fontsize=8)
        ax.set_ylabel("Amount", fontsize=9)
        ax.set_title(f"Sales vs Expenses — {period_label}", fontsize=11,
                     color="#1a365d", fontweight="bold")
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(True, axis="y", alpha=0.3, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        # Auto-hide value labels if too many bars
        if len(labels) <= 12:
            for bars in (bars1, bars2):
                for bar in bars:
                    h = bar.get_height()
                    if h > 0:
                        ax.text(bar.get_x() + bar.get_width() / 2, h,
                                f"{int(round(h)):,}", ha="center", va="bottom", fontsize=7,
                                color="#374151")
        plt.tight_layout()
        buf = _io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        logger.warning(f"Chart render failed: {e}")
        return None


def _format_period_whatsapp_text(d: dict, period_type: str = "week") -> str:
    """Format weekly/monthly aggregated data as WhatsApp text."""
    from datetime import datetime as _dt
    
    def fmt(val):
        try:
            v = int(round(float(val)))
        except (TypeError, ValueError):
            v = 0
        return f"{v}/-"

    def _ord(n: int) -> str:
        if 11 <= (n % 100) <= 13:
            return f"{n}th"
        return f"{n}{ {1:'st',2:'nd',3:'rd'}.get(n % 10, 'th') }"

    if period_type == "month":
        try:
            ms = _dt.strptime(d.get("month_start"), "%Y-%m-%d")
            range_str = f"{ms.strftime('%B %Y')} (Monthly Summary)"
        except Exception:
            range_str = f"{d.get('month','')} (Monthly Summary)"
    elif period_type == "year":
        range_str = d.get("year_label") or f"{d.get('year_start','')} to {d.get('year_end','')} (Yearly Summary)"
    else:
        try:
            ws = _dt.strptime(d["week_start"], "%Y-%m-%d")
            we = _dt.strptime(d["week_end"], "%Y-%m-%d")
            range_str = f"{_ord(ws.day)} {ws.strftime('%B %Y')} to {_ord(we.day)} {we.strftime('%B %Y')}"
        except Exception:
            range_str = f"{d.get('week_start','')} to {d.get('week_end','')}"

    lines = [
        "Jai Hind Namskar 🙏",
        "",
        range_str,
        "",
        f"↪️ Total Sale = {fmt(d['total_sale'])}",
        f"↪️ Total Card = {fmt(d['total_card'])}",
        f"↪️ Total Deposit = {fmt(d['total_deposit'])}",
        f"↪️ Total Withdrawl = {fmt(d['total_withdrawal'])}",
        "",
        "DESCRIPTION Expenses",
    ]
    cats = d.get("expense_categories") or []
    letters = "abcdefghij"
    if cats:
        for i, c in enumerate(cats):
            name = c.get("name") if isinstance(c, dict) else c[0]
            amount = c.get("amount") if isinstance(c, dict) else c[1]
            letter = letters[i] if i < len(letters) else f"{i+1}"
            lines.append(f"{letter}) {name} = {fmt(amount)}")
    else:
        lines.append("(No expenses recorded)")
    
    lines += [
        "",
        f"↪️ Total Swiggy = {fmt(d['total_swiggy'])}",
        f"↪️ Total Zomato = {fmt(d['total_zomato'])}",
    ]
    if d.get("is_international"):
        lines.append(f"↪️ Total Doordash = {fmt(d['total_doordash'])}")
    lines += [
        f"↪️ Total Paytm = {fmt(d['total_paytm'])}",
        f"↪️ Total Bharat Pay = {fmt(d['total_bharat_pay'])}",
        f"↪️ Total Cash Sale = {fmt(d['total_cash_sale'])}",
        f"↪️ Total Cash Expenses = {fmt(d['total_cash_expenses'])}",
        f"↪️ Total Cash In Hand = {fmt(d['total_cash_in_hand'])}",
        f"↪️ Total Online Expenses = {fmt(d['total_online_expenses'])}",
        f"↪️ APC = {int(d.get('apc') or 0)}",
        f"↪️ Total No. Of Guest = {int(d.get('total_guests') or 0)}",
        "",
        "💰 Net Revenue Calculation",
        f"↪️ Aggregator Sales (excl. from GST) = {fmt(d.get('total_aggregator_sale', 0))}",
        f"↪️ Eligible Sales for GST = {fmt(d.get('total_eligible_sale', 0))}",
        f"↪️ GST on Eligible Sales = {fmt(d.get('total_gst', 0))}",
        f"↪️ Total Commissions = {fmt(d.get('total_commissions', 0))}",
        f"➡️ NET REVENUE = {fmt(d.get('net_revenue', 0))}",
    ]
    return "\n".join(lines)


# Backwards-compat alias for old name
_format_weekly_whatsapp_text = _format_period_whatsapp_text


@router.post("/generate")
async def generate_daily_text(req: TextGenRequest):
    """Generate WhatsApp-style daily summary text from sales + expense data."""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    center = req.center.upper()
    is_admin = has_admin_access(session)
    is_franchise_owner = session.get("role_key") == "franchise_owner"

    # Access check: manager = own center, admin = all, franchise owner = own center
    if not is_admin:
        user_center = session.get("center", "")
        if user_center != center:
            raise HTTPException(403, "You can only generate text for your own center")

    # Fetch daily sales record - try exact match, then case-insensitive
    sale = await db.daily_sales.find_one({"center": center, "date": req.date}, {"_id": 0})
    if not sale:
        sale = await db.daily_sales.find_one(
            {"center": {"$regex": f"^{center}$", "$options": "i"}, "date": req.date}, {"_id": 0}
        )

    # Fetch expenses for the day - same approach
    expenses = await db.expenses.find({"center": center, "date": req.date}, {"_id": 0}).to_list(500)
    if not expenses:
        expenses = await db.expenses.find(
            {"center": {"$regex": f"^{center}$", "$options": "i"}, "date": req.date}, {"_id": 0}
        ).to_list(500)

    # Calculate expense totals by payment mode
    online_expense = 0
    cash_expense_total = 0
    for exp in expenses:
        mode = (exp.get("payment_mode") or "CASH").upper()
        amount = float(exp.get("amount", 0))
        if mode in ("ONLINE", "BANK", "UPI", "TRANSFER", "NEFT", "IMPS"):
            online_expense += amount
        else:
            cash_expense_total += amount

    # Build data dict with defaults
    data = {
        "date": req.date,
        "opening_balance": 0,
        "deposit": 0,
        "withdrawal": 0,
        "total_sale": 0,
        "card": 0,
        "phone_pay": 0,
        "swiggy": 0,
        "zomato": 0,
        "due_amount": 0,
        "cash_sale": 0,
        "online_expense": round(online_expense, 2),
        "cash_expense": round(cash_expense_total, 2),
        "cash_in_hand": 0,
        "petty_cash_balance": 0,
        "total_guests": 0,
        "apc": 0,
        "num_drinks": 0,
        "num_sides": 0,
        "cancelled_zomato": 0,
        "cancelled_swiggy": 0,
    }

    # Auto-fill from daily sales record
    if sale:
        data["opening_balance"] = float(sale.get("opening_balance", 0))
        data["deposit"] = float(sale.get("deposited_in_bank", 0))
        data["withdrawal"] = float(sale.get("cash_receipts", 0))
        data["total_sale"] = float(sale.get("total_sale", 0))
        data["card"] = float(sale.get("card_idfc", 0))
        data["phone_pay"] = float(sale.get("bharat_pay", 0))
        data["swiggy"] = float(sale.get("swiggy", 0))
        data["zomato"] = float(sale.get("zomato", 0))
        data["due_amount"] = float(sale.get("due_amount", 0))
        data["cash_sale"] = float(sale.get("total_cash_sale", 0))
        data["cash_expense"] = float(sale.get("cash_expense", 0)) or round(cash_expense_total, 2)
        data["cash_in_hand"] = float(sale.get("closing_balance", 0))
        data["petty_cash_balance"] = float(sale.get("petty_cash_closing", 0))
        data["total_guests"] = int(sale.get("num_guests", 0))
        data["apc"] = round(float(sale.get("avg_per_pax", 0)), 0)
        data["online_expense"] = round(online_expense, 2) or 0
        # GST + Net Revenue (single source of truth, inclusive carve-out)
        from utils.gst import compute_gst_from_rows
        gst_calc = compute_gst_from_rows([sale], country=None, center=center)
        data["gst"] = gst_calc["gst_amount"]
        data["aggregator_sale"] = gst_calc["aggregator_sale"]
        data["eligible_sale"] = gst_calc["eligible_base"]
        data["net_revenue"] = round(data["total_sale"] - gst_calc["gst_amount"], 2)

    # Apply manual overrides (only non-zero overrides, to prevent reset)
    if req.overrides:
        for key, val in req.overrides.items():
            if key in data and val is not None:
                data[key] = val

    # Format date for display
    try:
        dt = datetime.strptime(req.date, "%Y-%m-%d")
        display_date = dt.strftime("%d/%m/%Y")
    except ValueError:
        display_date = req.date

    # Generate the WhatsApp text
    text = _format_whatsapp_text(data, display_date)

    return {
        "success": True,
        "text": text,
        "data": data,
        "has_sales_data": sale is not None,
        "expense_count": len(expenses),
        "center": center,
        "date": req.date,
        "can_edit": is_admin or not is_franchise_owner,
    }


def _format_whatsapp_text(data: dict, display_date: str) -> str:
    """Format the data into WhatsApp-ready text."""
    def fmt(val):
        """Format number with /- suffix."""
        if isinstance(val, float):
            return f"{int(val)}/-" if val == int(val) else f"{val}/-"
        return f"{int(val)}/-"

    lines = [
        "Jai Hind Namskar 🙏",
        "",
        f"Date {display_date}",
        "",
        f"1. Opening Bal = {fmt(data['opening_balance'])}",
        f"2. Deposit = {fmt(data['deposit'])}",
        f"3. Withdrawl = {fmt(data['withdrawal'])}",
        f"4. Total Sale = {fmt(data['total_sale'])}",
        f"5. Card = {fmt(data['card'])}",
        f"6. Phone Pay = {fmt(data['phone_pay'])}",
        f"7. SWIGGY = {fmt(data['swiggy'])}",
        f"8. ZOMATO = {fmt(data['zomato'])}",
        f"9. Due Amount = {fmt(data['due_amount'])}",
        f"10. Cash sale = {fmt(data['cash_sale'])}",
        f"11. Online Expense = {fmt(data['online_expense'])}",
        f"12. Cash Expense = {fmt(data['cash_expense'])}",
        f"13. Cash In Hand = {fmt(data['cash_in_hand'])}",
        f"14. Bal. Petty cash = {fmt(data['petty_cash_balance'])}",
        f"15. Total No. of guest = {int(data['total_guests'])}",
        f"16. APC = {int(data['apc'])}",
        f"17. No. Of Drinks = {int(data['num_drinks'])}",
        f"18. No of sides sold = {int(data['num_sides'])}",
        f"    Cancelled Zomato Order = {int(data['cancelled_zomato'])}",
        f"19. Cancelled Swiggy Order = {int(data['cancelled_swiggy'])}",
        "",
        "💰 Net Revenue Calculation",
        f"   Aggregator Sales (Swiggy+Zomato+DoorDash) = {fmt(data.get('aggregator_sale', 0))}",
        f"   Eligible Sales (excl. aggregators) = {fmt(data.get('eligible_sale', 0))}",
        f"   GST on Eligible Sales (5% incl.) = {fmt(data.get('gst', 0))}",
        f"   ➡️ NET REVENUE = {fmt(data.get('net_revenue', 0))}",
    ]
    return "\n".join(lines)
