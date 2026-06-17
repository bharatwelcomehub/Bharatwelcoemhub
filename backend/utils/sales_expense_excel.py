"""Sales + Expense Excel generator — matches the Sales Dashboard manager-side
download exactly so accounts + franchise owner see identical files.

Reference format (from /app/frontend/src/pages/SalesExpenses.jsx · downloadMonthlyExcel):
  Sheet 1 "Daily Sales": Date, Center, Sale PBM, Sale Other, Total Sale,
    Card/IDFC, Bharat Pay, Swiggy, Zomato, Online Other, Total Online,
    Total Cash Sale, Opening Balance, Cash Receipts, Deposited in Bank,
    Cash Expense, Closing Balance, Petty Cash Opening, Petty Cash Closing,
    No. of Guests, No. of Bills
  Sheet 2 "Expense Details": Date, Center, Description, Expense Type,
    Payment Mode, Amount
  Sheet 3 "Expense Summary": Expense Type, Total Amount (+ TOTAL row)

Used by:
  - Center Accounts → Sales tab "Download Excel"
  - Franchise Owner Dashboard → Reports → Sales/Expense Excel
  - Monthly Email Pack ZIP bundle

Pulls data live from `daily_sales` + `expenses` collections — never a frozen
copy, so every export reflects the latest entries.
"""

from io import BytesIO
from typing import Optional

from openpyxl import Workbook
from openpyxl.utils import get_column_letter


def _money(v) -> float:
    try:
        return round(float(v or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _write_headers(ws, headers, widths):
    ws.append(headers)
    from openpyxl.styles import Font, PatternFill, Alignment
    fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
    font = Font(bold=True)
    for col_idx in range(1, len(headers) + 1):
        c = ws.cell(row=ws.max_row, column=col_idx)
        c.fill = fill
        c.font = font
        c.alignment = Alignment(horizontal="center", vertical="center")
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


async def build_sales_expense_excel(
    db,
    center: str,
    start_date: str,
    end_date: str,
    title_suffix: Optional[str] = None,
) -> bytes:
    """Produce a 3-sheet workbook (Daily Sales + Expense Details + Expense Summary)
    matching exactly what the manager-side Sales Dashboard generates.

    Args:
        db: Motor Mongo handle.
        center: Center code e.g. "PB-HSR".
        start_date: ISO "YYYY-MM-DD" inclusive.
        end_date:   ISO "YYYY-MM-DD" inclusive.
        title_suffix: optional string (kept for backwards-compat; not used in
                      the new format since the manager-side Excel has no title
                      banner — just the headers row).
    """
    sales = await db.daily_sales.find(
        {"center": center, "date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0},
    ).sort("date", 1).to_list(500)

    expenses = await db.expenses.find(
        {"center": center, "date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0},
    ).sort("date", 1).to_list(5000)

    wb = Workbook()

    # ──────────────────────────── Sheet 1: Daily Sales ────────────────────
    ws = wb.active
    ws.title = "Daily Sales"

    sales_headers = [
        "Date", "Center", "Sale PBM", "Sale Other", "Total Sale",
        "Card/IDFC", "Bharat Pay", "Swiggy", "Zomato", "DoorDash", "Online Other",
        "Total Online", "Total Cash Sale", "Opening Balance", "Cash Receipts",
        "Deposited in Bank", "Cash Expense", "Closing Balance",
        "Petty Cash Opening", "Petty Cash Closing",
        "No. of Guests", "No. of Bills",
    ]
    sales_widths = [
        12, 10, 12, 12, 12,
        12, 12, 10, 10, 10, 12,
        12, 14, 14, 12,
        15, 12, 14,
        14, 14,
        12, 12,
    ]
    _write_headers(ws, sales_headers, sales_widths)

    for s in sales:
        ws.append([
            s.get("date") or "",
            s.get("center") or center,
            _money(s.get("sale_pbm")),
            _money(s.get("sale_other")),
            _money(s.get("total_sale")),
            _money(s.get("card_idfc")),
            _money(s.get("bharat_pay")),
            _money(s.get("swiggy_sale", s.get("swiggy"))),
            _money(s.get("zomato_sale", s.get("zomato"))),
            _money(s.get("doordash_sale", s.get("doordash"))),
            _money(s.get("online_other")),
            _money(s.get("total_online_sale")),
            _money(s.get("total_cash_sale")),
            _money(s.get("opening_balance")),
            _money(s.get("cash_receipts")),
            _money(s.get("deposited_in_bank")),
            _money(s.get("cash_expense")),
            _money(s.get("closing_balance")),
            _money(s.get("petty_cash_opening")),
            _money(s.get("petty_cash_closing")),
            int(s.get("num_guests") or 0),
            int(s.get("num_bills") or 0),
        ])
    # Number formatting on money columns (3..20) — extended by one column for DoorDash
    for r in range(2, ws.max_row + 1):
        for c in range(3, 21):
            ws.cell(row=r, column=c).number_format = "#,##0.00"

    # ──────────────────────────── Sheet 2: Expense Details ────────────────
    ws2 = wb.create_sheet("Expense Details")
    exp_headers = ["Date", "Center", "Description", "Expense Type", "Payment Mode", "Amount"]
    _write_headers(ws2, exp_headers, [12, 10, 30, 20, 15, 12])

    for e in expenses:
        ws2.append([
            e.get("date") or "",
            e.get("center") or center,
            (e.get("description") or "")[:200],
            e.get("expense_type") or "",
            e.get("payment_mode") or "",
            _money(e.get("amount")),
        ])
    for r in range(2, ws2.max_row + 1):
        ws2.cell(row=r, column=6).number_format = "#,##0.00"

    # ──────────────────────────── Sheet 3: Expense Summary ────────────────
    ws3 = wb.create_sheet("Expense Summary")
    _write_headers(ws3, ["Expense Type", "Total Amount"], [25, 15])

    summary = {}
    for e in expenses:
        t = e.get("expense_type") or "Unknown"
        summary[t] = summary.get(t, 0.0) + _money(e.get("amount"))

    # Sort by amount desc — same as manager-side sort
    for t, amt in sorted(summary.items(), key=lambda kv: -kv[1]):
        ws3.append([t, round(amt, 2)])
        ws3.cell(row=ws3.max_row, column=2).number_format = "#,##0.00"

    total_exp = round(sum(summary.values()), 2)
    ws3.append(["TOTAL", total_exp])
    last = ws3.max_row
    from openpyxl.styles import Font as _Font
    ws3.cell(row=last, column=1).font = _Font(bold=True)
    ws3.cell(row=last, column=2).font = _Font(bold=True)
    ws3.cell(row=last, column=2).number_format = "#,##0.00"

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
