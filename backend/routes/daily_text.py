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

    # Fetch daily sales record
    sale = await db.daily_sales.find_one({"center": center, "date": req.date}, {"_id": 0})

    # Fetch expenses for the day
    expenses = await db.expenses.find({"center": center, "date": req.date}, {"_id": 0}).to_list(500)

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

    # Apply manual overrides
    if req.overrides:
        for key, val in req.overrides.items():
            if key in data:
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
