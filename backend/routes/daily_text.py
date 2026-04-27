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

    # Center info (for doordash visibility)
    center_doc = await db.centers.find_one({"code": center}, {"_id": 0}) or \
                 await db.centers.find_one({"code": {"$regex": f"^{center}$", "$options": "i"}}, {"_id": 0})
    is_international = bool(center_doc and (center_doc.get("is_india_center") is False or
                                             (center_doc.get("country") and center_doc.get("country") != "India")))

    # Pull all sales + expenses for the week (case-insensitive center match)
    sales = await db.daily_sales.find(
        {"center": {"$regex": f"^{center}$", "$options": "i"}, "date": {"$in": date_strs}},
        {"_id": 0}
    ).to_list(20)
    expenses = await db.expenses.find(
        {"center": {"$regex": f"^{center}$", "$options": "i"}, "date": {"$in": date_strs}},
        {"_id": 0}
    ).to_list(2000)

    # Aggregate sales
    def fsum(field):
        return sum(float(s.get(field, 0) or 0) for s in sales)

    total_sale = fsum("total_sale")
    total_card = fsum("card_idfc")
    total_deposit = fsum("deposited_in_bank")
    total_withdrawal = fsum("cash_receipts")
    total_swiggy = fsum("swiggy")
    total_zomato = fsum("zomato")
    total_doordash = fsum("doordash")
    total_paytm = fsum("paytm")  # 0 if field absent
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

    # Aggregate expenses - split by mode + group by category
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
        # Category bucket - prefer expense_type, fall back to description
        cat = (exp.get("expense_type") or "").strip() or (exp.get("description") or "").strip() or "Other"
        # Title case the category for nicer display
        cat_clean = cat.title()
        by_category[cat_clean] = by_category.get(cat_clean, 0) + amt

    # Top categories (sorted by amount desc) - keep top 6
    top_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:6]

    # APC (Average per Cover) = total_sale / total_guests (across week)
    apc = round(total_sale / total_guests, 0) if total_guests > 0 else 0

    data = {
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end.strftime("%Y-%m-%d"),
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
    }

    # Apply overrides
    if req.overrides:
        for key, val in req.overrides.items():
            if key in data and val is not None:
                data[key] = val
            elif key == "expense_categories" and isinstance(val, list):
                data["expense_categories"] = val

    text = _format_weekly_whatsapp_text(data)

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


def _format_weekly_whatsapp_text(d: dict) -> str:
    """Format weekly aggregated data as WhatsApp text matching the requested format."""
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

    try:
        ws = _dt.strptime(d["week_start"], "%Y-%m-%d")
        we = _dt.strptime(d["week_end"], "%Y-%m-%d")
        range_str = f"{_ord(ws.day)} {ws.strftime('%B %Y')} to {_ord(we.day)} {we.strftime('%B %Y')}"
    except Exception:
        range_str = f"{d['week_start']} to {d['week_end']}"

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
    ]
    return "\n".join(lines)


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
    ]
    return "\n".join(lines)
