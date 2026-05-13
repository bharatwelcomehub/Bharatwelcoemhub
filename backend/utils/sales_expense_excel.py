"""Sales + Expense Excel generator — single source of truth.

Generates an .xlsx file in the same format as the manager-side Sales Dashboard
download, but parameterised by (center, date-range). Used by:
  - Center Accounts → Sales tab "Download Excel"
  - Franchise Owner Dashboard → Reports → Sales/Expense Excel
  - Monthly Email Pack ZIP bundle

Pulls data live from `daily_sales` + `expenses` collections — never a frozen
copy, so every export reflects the latest entries.
"""

from datetime import datetime, timedelta
from io import BytesIO
from typing import List, Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter


_HEADER_FILL = PatternFill(start_color="8B0000", end_color="8B0000", fill_type="solid")
_HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
_SUBHEAD_FILL = PatternFill(start_color="F3E5E5", end_color="F3E5E5", fill_type="solid")
_TOTAL_FILL = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
_BORDER = Border(
    left=Side(style="thin", color="DDDDDD"),
    right=Side(style="thin", color="DDDDDD"),
    top=Side(style="thin", color="DDDDDD"),
    bottom=Side(style="thin", color="DDDDDD"),
)


def _money(v) -> float:
    try:
        return round(float(v or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _set_col_widths(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


async def build_sales_expense_excel(
    db,
    center: str,
    start_date: str,
    end_date: str,
    title_suffix: Optional[str] = None,
) -> bytes:
    """Produce a 2-sheet workbook (Sales + Expenses) for [start_date, end_date] inclusive.

    Args:
        db: Motor Mongo handle.
        center: Center code e.g. "PB-HSR".
        start_date: ISO "YYYY-MM-DD" inclusive.
        end_date:   ISO "YYYY-MM-DD" inclusive.
        title_suffix: optional string appended to the workbook title row.
    """
    # Pull live data
    sales = await db.daily_sales.find(
        {"center": center, "date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0},
    ).sort("date", 1).to_list(500)

    expenses = await db.expenses.find(
        {"center": center, "date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0},
    ).sort("date", 1).to_list(2000)

    wb = Workbook()

    # ──────────────────────────── SALES SHEET ────────────────────────────
    ws = wb.active
    ws.title = "Sales"

    # Top title row
    ws.append([f"{center} — Sales ({start_date} to {end_date})" +
               (f" · {title_suffix}" if title_suffix else "")])
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=14)
    ws.cell(row=1, column=1).font = Font(size=14, bold=True, color="8B0000")
    ws.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 24

    headers = [
        "Date", "Day", "Cash Sale", "Card (IDFC)", "BharatPe / UPI",
        "Online Other", "Swiggy", "Zomato", "Doordash", "Other Sale",
        "Total Online", "Total Sale", "GST", "Notes",
    ]
    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=2, column=col_idx)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = _BORDER
    ws.row_dimensions[2].height = 28

    cash_t = card_t = bpay_t = online_t = swg_t = zom_t = ddash_t = other_t = tot_online_t = tot_t = gst_t = 0.0
    for s in sales:
        d = s.get("date") or ""
        try:
            day = datetime.strptime(d, "%Y-%m-%d").strftime("%a")
        except Exception:
            day = ""
        row = [
            d, day,
            _money(s.get("total_cash_sale")),
            _money(s.get("card_idfc")),
            _money(s.get("bharat_pay")),
            _money(s.get("online_other")),
            _money(s.get("swiggy_sale", s.get("swiggy"))),
            _money(s.get("zomato_sale", s.get("zomato"))),
            _money(s.get("doordash_sale", s.get("doordash"))),
            _money(s.get("sale_other")),
            _money(s.get("total_online_sale")),
            _money(s.get("total_sale")),
            _money(s.get("gst_amount")),
            (s.get("notes") or s.get("manager_remarks") or "")[:80],
        ]
        ws.append(row)
        cash_t += row[2]; card_t += row[3]; bpay_t += row[4]; online_t += row[5]
        swg_t += row[6]; zom_t += row[7]; ddash_t += row[8]; other_t += row[9]
        tot_online_t += row[10]; tot_t += row[11]; gst_t += row[12]

    # Totals row
    ws.append([
        "TOTAL", "",
        round(cash_t, 2), round(card_t, 2), round(bpay_t, 2),
        round(online_t, 2), round(swg_t, 2), round(zom_t, 2),
        round(ddash_t, 2), round(other_t, 2),
        round(tot_online_t, 2), round(tot_t, 2), round(gst_t, 2), "",
    ])
    last_row = ws.max_row
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=last_row, column=col_idx)
        cell.fill = _TOTAL_FILL
        cell.font = Font(bold=True)
        cell.border = _BORDER

    # Apply borders to all data rows + number format
    for r in range(2, last_row + 1):
        for c in range(1, len(headers) + 1):
            ws.cell(row=r, column=c).border = _BORDER
            if r > 2 and c >= 3 and c <= 13:
                ws.cell(row=r, column=c).number_format = "#,##0.00"

    _set_col_widths(ws, [12, 5, 11, 11, 13, 11, 11, 11, 11, 11, 13, 13, 11, 24])

    # ──────────────────────────── EXPENSES SHEET ─────────────────────────
    ws2 = wb.create_sheet("Expenses")
    ws2.append([f"{center} — Expenses ({start_date} to {end_date})"])
    ws2.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
    ws2.cell(row=1, column=1).font = Font(size=14, bold=True, color="8B0000")
    ws2.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[1].height = 24

    headers2 = ["Date", "Category", "Sub-category", "Vendor", "Description", "Amount", "Has Bill?"]
    ws2.append(headers2)
    for col_idx in range(1, len(headers2) + 1):
        cell = ws2.cell(row=2, column=col_idx)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = _BORDER
    ws2.row_dimensions[2].height = 28

    by_cat = {}
    grand_total = 0.0
    for e in expenses:
        amount = _money(e.get("amount"))
        grand_total += amount
        category = e.get("category") or e.get("head") or "Uncategorised"
        by_cat[category] = by_cat.get(category, 0.0) + amount
        bill_present = "Yes" if (e.get("attachment_url") or e.get("attachment_path") or e.get("bill_url")) else "No"
        row = [
            e.get("date") or "",
            category,
            e.get("sub_category") or e.get("sub_head") or "",
            e.get("vendor") or e.get("payee") or "",
            (e.get("description") or e.get("notes") or "")[:120],
            amount,
            bill_present,
        ]
        ws2.append(row)

    ws2.append(["TOTAL", "", "", "", "", round(grand_total, 2), ""])
    last_row2 = ws2.max_row
    for col_idx in range(1, len(headers2) + 1):
        cell = ws2.cell(row=last_row2, column=col_idx)
        cell.fill = _TOTAL_FILL
        cell.font = Font(bold=True)
        cell.border = _BORDER
    for r in range(2, last_row2 + 1):
        for c in range(1, len(headers2) + 1):
            ws2.cell(row=r, column=c).border = _BORDER
            if c == 6 and r > 2:
                ws2.cell(row=r, column=c).number_format = "#,##0.00"

    _set_col_widths(ws2, [12, 18, 18, 22, 40, 14, 10])

    # By-category summary on Expenses sheet
    ws2.append([])
    ws2.append(["Category Summary"])
    last = ws2.max_row
    ws2.cell(row=last, column=1).font = Font(size=12, bold=True, color="8B0000")
    ws2.append(["Category", "Amount"])
    for col_idx in (1, 2):
        cell = ws2.cell(row=ws2.max_row, column=col_idx)
        cell.fill = _SUBHEAD_FILL
        cell.font = Font(bold=True)
        cell.border = _BORDER
    for cat, amt in sorted(by_cat.items(), key=lambda kv: -kv[1]):
        ws2.append([cat, round(amt, 2)])
        ws2.cell(row=ws2.max_row, column=2).number_format = "#,##0.00"

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
