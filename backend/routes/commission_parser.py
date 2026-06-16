# =======================================
# Commission Excel Parser
# Parses Zomato, Swiggy, DoorDash, PhonePe, Cards
# =======================================
# Return format (unified):
#   gross_amount:       Total customer-facing sale (incl taxes)
#   gst_tax_deductions: GST, TDS, TCS, tax on platform fees
#   other_deductions:   Platform fees, adjustments (non-tax)
#   net_payout:         What actually gets paid out
# =======================================

import pandas as pd
import openpyxl
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def safe_float(val) -> float:
    """Safely convert a value to float, returning 0.0 on failure."""
    if val is None or val == "-" or val == "":
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def find_col_ci(df: pd.DataFrame, *needles) -> Optional[str]:
    """Find first DataFrame column whose lowercased name contains any of the
    given case-insensitive needles. Returns the actual column name or None."""
    lc = {str(c).strip().lower(): c for c in df.columns}
    for needle in needles:
        n = needle.lower().strip()
        # exact match first
        if n in lc:
            return lc[n]
    # partial match fallback
    for needle in needles:
        n = needle.lower().strip()
        for k, orig in lc.items():
            if n in k:
                return orig
    return None


def col_sum_ci(df: pd.DataFrame, *needles) -> float:
    col = find_col_ci(df, *needles)
    if not col:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


# ── Bank statement loader (multi-bank) ────────────────────────────────────
def _load_bank_statement_normalized(bank_filepath: str) -> Dict[str, Any]:
    """Load an Excel bank statement and return a normalized representation
    with columns: ['date', 'particulars', 'debit', 'credit'].

    Supports:
      • HDFC India: explicit 'Transaction Date', 'Particulars', 'Debit', 'Credit' columns.
      • ANZ Australia (Business Essentials): merged 'Date  Transaction Details' in
        column A, 'Withdrawals' in another column, 'Deposits' in another.

    Returns a dict: {'df': normalized_df, 'format': 'hdfc'|'anz'}.
    Raises ValueError if no recognised header row is found.
    """
    import re

    raw = pd.read_excel(bank_filepath, header=None)

    header_row = None
    fmt = None
    for i in range(min(30, len(raw))):
        cells = [str(v) for v in raw.iloc[i].tolist() if str(v) != 'nan']
        joined = ' '.join(cells).lower()
        # ANZ Australia: header cell concatenates "date  transaction details"
        if ('date' in joined and 'transaction details' in joined
                and ('withdrawal' in joined or 'deposit' in joined)):
            header_row = i
            fmt = 'anz'
            break
        # Indian banks (HDFC / IDFC / ICICI / Axis / Kotak / SBI etc.) —
        # signal = a date-ish column + a narration/desc column + at least one
        # money column. Generic enough to catch HDFC, IDFC, ICICI variants.
        has_date = any(k in joined for k in ('transaction date', 'txn date', 'value date', 'tran date', 'posting date'))
        # Some statements have just "Date" as the column header
        if not has_date:
            # Be careful — many rows mention "date" in body text; require it to be a column header (short cell)
            has_date = any(str(c).strip().lower() in ('date',) for c in cells)
        has_narration = any(k in joined for k in ('particulars', 'description', 'narration', 'transaction details', 'remarks'))
        has_money = any(k in joined for k in ('debit', 'withdrawal', 'credit', 'deposit', 'dr ', 'cr ', 'withdrawal amt', 'deposit amt'))
        if has_date and has_narration and has_money:
            header_row = i
            fmt = 'hdfc'  # generic India layout (HDFC/IDFC/ICICI/Axis/Kotak…)
            break

    if header_row is None:
        raise ValueError(
            "Could not find transaction header in bank statement. "
            "Expected HDFC (Transaction Date, Particulars, Debit, Credit) or "
            "ANZ (Date, Transaction Details, Withdrawals, Deposits) layouts."
        )

    if fmt == 'hdfc':
        df_bank = pd.read_excel(bank_filepath, header=header_row)
        df_bank.columns = [str(c).strip() for c in df_bank.columns]
        date_col = find_col_ci(df_bank, 'transaction date', 'txn date', 'value date', 'tran date', 'posting date', 'date')
        part_col = find_col_ci(df_bank, 'particulars', 'description', 'narration', 'transaction details', 'remarks')
        debit_col = find_col_ci(df_bank, 'debit', 'withdrawal amt', 'withdrawal', 'dr amount', 'dr')
        credit_col = find_col_ci(df_bank, 'credit', 'deposit amt', 'deposit', 'cr amount', 'cr')
        if not (date_col and part_col):
            raise ValueError("Indian bank statement missing date or particulars column.")
        out = pd.DataFrame({
            'date': pd.to_datetime(df_bank[date_col], dayfirst=True, errors='coerce'),
            'particulars': df_bank[part_col].astype(str),
            'debit': pd.to_numeric(df_bank[debit_col], errors='coerce').fillna(0) if debit_col else 0,
            'credit': pd.to_numeric(df_bank[credit_col], errors='coerce').fillna(0) if credit_col else 0,
        })
        return {'df': out.dropna(subset=['date']).reset_index(drop=True), 'format': 'hdfc'}

    # ── ANZ format ────────────────────────────────────────────────────────
    # Header row has 'Date  Transaction Details' merged in one cell + separate
    # 'Withdrawals' and 'Deposits' cells (possibly with empty cells in between).
    header_cells = raw.iloc[header_row].tolist()
    # ANZ keeps "Date Transaction Details" merged in column 0 by default.
    # We don't currently use combo_idx because the row parser below reads
    # cells by fixed position (col 0 for date, col 1 for desc on Layout B,
    # col 2/3 for withdrawal, col 4 for deposit). Logic kept inline below.
    _ = header_cells  # noqa: F841 — header_cells is referenced for documentation

    # Year inference: from the file metadata block (first 5 rows often have "to 15 June 2026")
    inferred_year = None
    blob = ' '.join(str(v) for v in raw.iloc[:6].values.flatten() if str(v) != 'nan')
    m = re.search(r'(20\d{2})', blob)
    if m:
        inferred_year = int(m.group(1))

    MONTHS = {'JAN':1,'FEB':2,'MAR':3,'APR':4,'MAY':5,'JUN':6,'JUL':7,
              'AUG':8,'SEP':9,'OCT':10,'NOV':11,'DEC':12}

    rows = []
    last_date = None
    for i in range(header_row + 1, len(raw)):
        line = raw.iloc[i].tolist()
        cell_a = str(line[0]) if len(line) > 0 else ''
        cell_b = str(line[1]) if len(line) > 1 else ''
        if cell_a == 'nan' or cell_a.strip() == '':
            # Layout B rows still need processing if any amount columns are populated
            cell_a = ''
        # Skip section markers like "RECENT 1", "JUN 2026", "MAY 2026"
        stripped_a = cell_a.strip()
        if re.fullmatch(r'[A-Z]+ ?\d+', stripped_a) or re.fullmatch(r'[A-Za-z]{3,} 20\d{2}', stripped_a):
            continue
        # Parse "DD MMM    [optional details]" in cell A
        m = re.match(r'^\s*(\d{1,2})\s+([A-Za-z]{3})\b\s*(.*)$', cell_a)
        if m:
            day = int(m.group(1))
            mon = MONTHS.get(m.group(2).upper())
            details_inline = m.group(3).strip()
            if mon and inferred_year:
                try:
                    last_date = pd.Timestamp(year=inferred_year, month=mon, day=day)
                except Exception:
                    last_date = None
            # If details aren't inline (Layout B), use cell B
            if details_inline:
                details = details_inline
            elif cell_b and cell_b != 'nan':
                details = cell_b.strip()
            else:
                details = ''
            dt = last_date
        else:
            # Continuation line / header — try cell B for details
            if cell_b and cell_b != 'nan':
                details = cell_b.strip()
            else:
                details = stripped_a
            dt = last_date

        # Amount columns differ by layout:
        #   Layout A: withdrawal=col2, deposit=col4
        #   Layout B: withdrawal=col3, deposit=col4
        # Only one of (col2, col3) is populated per row, so take their max.
        debit_a = safe_float(line[2]) if len(line) > 2 else 0.0
        debit_b = safe_float(line[3]) if len(line) > 3 else 0.0
        debit = max(debit_a, debit_b)
        credit = safe_float(line[4]) if len(line) > 4 else 0.0

        # Skip rows with no money AND no description
        if debit == 0 and credit == 0 and not details:
            continue
        rows.append({'date': dt, 'particulars': details, 'debit': debit, 'credit': credit})

    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError("ANZ bank statement parsed 0 rows — file may be malformed.")
    # Drop rows with no date AND no money
    out = out[(out['date'].notna()) | (out['debit'] != 0) | (out['credit'] != 0)].reset_index(drop=True)
    return {'df': out, 'format': 'anz'}


def detect_platform(filepath: str, filename: str = "") -> Optional[str]:
    """Auto-detect which platform the Excel file is from based on content."""
    fn = filename.lower()
    if "zomato" in fn:
        return "zomato"
    if "swiggy" in fn:
        return "swiggy"
    if "door" in fn or "doordash" in fn:
        return "doordash"
    if "ph pe" in fn or "phonepe" in fn or "phone pe" in fn:
        return "phonepe"
    if "card" in fn:
        return "cards"

    # Fallback: inspect file content
    try:
        wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
        sheets = [s.lower() for s in wb.sheetnames]
        if "payout breakup" in sheets or "order level" in sheets:
            wb.close()
            return "zomato"
        wb.close()

        df = pd.read_excel(filepath, nrows=5)
        cols_lower = " ".join(df.columns).lower()
        if "swiggy" in cols_lower or "swiggy platform" in cols_lower:
            return "swiggy"
        if "doordash" in cols_lower or "delivery uuid" in cols_lower:
            return "doordash"
        if "phonepe" in cols_lower or "phonpe" in cols_lower or "merchant id" in cols_lower and "upi amount" in cols_lower:
            return "phonepe"
        if "card type" in cols_lower and "auth code" in cols_lower:
            return "cards"
    except Exception as e:
        logger.warning(f"Platform detection fallback failed: {e}")

    return None


def parse_zomato(filepath: str) -> Dict[str, Any]:
    """Parse Zomato Payout Breakup sheet.
    Gross Amount = Net order value
    GST/Tax Deductions = taxes on service fees + TDS + TCS + GST 9(5)
    Other Deductions = service fees (non-tax portion)
    Net Payout = Net Payout"""
    wb = openpyxl.load_workbook(filepath, data_only=True)

    target_sheet = None
    for name in wb.sheetnames:
        if "payout breakup" in name.lower():
            target_sheet = name
            break
    if not target_sheet:
        target_sheet = wb.sheetnames[0]

    ws = wb[target_sheet]

    # Build a label->value map from Column 3 (label) and Column 4 (value)
    label_map = {}
    for r in range(1, ws.max_row + 1):
        label = ws.cell(row=r, column=3).value
        value = ws.cell(row=r, column=4).value
        if label and value is not None:
            clean_label = str(label).strip().split("\n")[0].strip().lower()
            label_map[clean_label] = value

    # Extract values
    net_order_value = safe_float(label_map.get("net order value", 0))
    service_fees = safe_float(label_map.get("service fees & payment mechanism fees", 0))
    service_fee = safe_float(label_map.get("service fee", 0))
    payment_mech_fee = safe_float(label_map.get("payment mechanism fee", 0))
    taxes_on_service = safe_float(label_map.get("taxes on service & payment mechanism fees", 0))
    tds = safe_float(label_map.get("tds 194o amount", 0))
    tcs = safe_float(label_map.get("tax collected at source + tcs igst amount", 0))
    gst_section95 = safe_float(label_map.get("gst paid by zomato on behalf of restaurant - under section 9(5)", 0))
    net_payout = safe_float(label_map.get("net payout", 0))
    net_deductions = safe_float(label_map.get("net deductions", 0))
    subtotal_items = safe_float(label_map.get("subtotal (items total)", 0))

    # Order count
    order_count = 0
    for r in range(1, min(10, ws.max_row + 1)):
        label = ws.cell(row=r, column=3).value
        if label and "number of orders" in str(label).lower():
            order_count = int(safe_float(ws.cell(row=r, column=4).value))
            break

    wb.close()

    # Gross = Net order value (as user specified)
    gross_amount = net_order_value

    # GST/Tax deductions = taxes on service fees + TDS + TCS + GST 9(5)
    gst_tax_deductions = abs(taxes_on_service) + abs(tds) + abs(tcs) + abs(gst_section95)

    # Other deductions = service fees (non-tax portion)
    other_deductions = abs(service_fees)

    return {
        "platform": "zomato",
        "gross_amount": round(gross_amount, 2),
        "gst_tax_deductions": round(gst_tax_deductions, 2),
        "other_deductions": round(other_deductions, 2),
        "net_payout": round(net_payout, 2),
        "order_count": order_count,
        "tds": round(abs(tds), 2),
        "currency": "INR",
        "raw_summary": {
            "subtotal_items": round(subtotal_items, 2),
            "net_order_value": round(net_order_value, 2),
            "service_fees": round(service_fees, 2),
            "service_fee": round(service_fee, 2),
            "payment_mechanism_fee": round(payment_mech_fee, 2),
            "taxes_on_service_fees": round(taxes_on_service, 2),
            "tds_194o": round(tds, 2),
            "tcs": round(tcs, 2),
            "gst_section_9_5": round(gst_section95, 2),
            "net_deductions": round(net_deductions, 2),
            "net_payout": round(net_payout, 2),
        },
    }


def parse_swiggy(filepath: str) -> Dict[str, Any]:
    """Parse Swiggy order-level report — ALL orders (including cancelled).
    Gross Amount = Customer payable (F = D + E)
    GST/Tax = Taxes on Swiggy fee (R) + GST Deduction U2 + TCS (X1) + TDS (X2)
    Other Deductions = Platform fees (S - R) + Adjustments (V - U2)
    Net Payout = Net Payable Amount after TCS and TDS (Y)"""
    df = pd.read_excel(filepath)

    def find_col(keywords, exclude=None):
        for c in df.columns:
            cl = c.lower()
            if all(k in cl for k in keywords):
                if exclude and any(e in cl for e in exclude):
                    continue
                return c
        return None

    def find_exact(name):
        for c in df.columns:
            if c.strip() == name:
                return c
        return None

    def col_sum(col):
        if col is None:
            return 0.0
        return float(pd.to_numeric(df[col], errors="coerce").sum())

    # Column mapping
    F_col = find_col(["customer payable"])
    S_col = find_col(["total swiggy fee (including taxes)"])
    R_col = find_col(["taxes on swiggy fee"])
    V_col = find_col(["total of order level adjustments"])
    U2_col = find_col(["gst deduction"])
    X1_col = find_exact("TCS X1")
    X2_col = find_exact("TDS X2")
    Y_col = find_col(["net payable amount", "after tcs"])

    F = col_sum(F_col)
    S = col_sum(S_col)
    R = col_sum(R_col)
    V = col_sum(V_col)
    U2 = col_sum(U2_col)
    X1 = col_sum(X1_col)
    X2 = col_sum(X2_col)
    Y = col_sum(Y_col)

    # GST/Tax deductions = Taxes on Swiggy fee + GST 9(5) deduction + TCS + TDS
    gst_tax_deductions = abs(R) + abs(U2) + abs(X1) + abs(X2)

    # Other deductions = Platform fees (S without tax) + Adjustments (V without GST)
    other_deductions = (abs(S) - abs(R)) + (abs(V) - abs(U2))

    # Status breakdown
    status_col = [c for c in df.columns if "order status" in c.lower()]
    status_counts = {}
    if status_col:
        status_counts = df[status_col[0]].value_counts().to_dict()

    return {
        "platform": "swiggy",
        "gross_amount": round(F, 2),
        "gst_tax_deductions": round(gst_tax_deductions, 2),
        "other_deductions": round(other_deductions, 2),
        "net_payout": round(Y, 2),
        "order_count": int(len(df)),
        "tds": round(abs(X2), 2),
        "currency": "INR",
        "raw_summary": {
            "total_orders": int(len(df)),
            "status_breakdown": status_counts,
            "customer_payable_F": round(F, 2),
            "total_swiggy_fee_S": round(S, 2),
            "taxes_on_swiggy_R": round(R, 2),
            "order_adjustments_V": round(V, 2),
            "gst_deduction_U2": round(U2, 2),
            "tcs_X1": round(X1, 2),
            "tds_X2": round(X2, 2),
            "net_payable_Y": round(Y, 2),
        },
    }


def parse_doordash(filepath: str) -> Dict[str, Any]:
    """Parse DoorDash detailed transactions — ALL orders (including cancelled).
    Gross = Subtotal Including GST (case-insensitive)
    Other Deductions = Commission + Marketing fees + Customer discounts (funded
                      by you) + Error charges − Adjustments (net)
                      i.e. anything that reduced the payout
    Net Payout = Net total
    GST: AU DoorDash leaves GST embedded in Subtotal and remits it separately,
         so 'gst_tax_deductions' stays 0 (declared in raw_summary)."""
    df = pd.read_excel(filepath)

    subtotal = col_sum_ci(df, "subtotal including gst")
    commission = col_sum_ci(df, "commission")
    net_total = col_sum_ci(df, "net total")
    marketing = col_sum_ci(df, "marketing fees")
    cust_disc_self = col_sum_ci(df, "customer discounts from marketing | (funded by you)",
                                "customer discounts from marketing (funded by you)")
    error_charges = col_sum_ci(df, "error charges")
    adjustments = col_sum_ci(df, "adjustments")
    tax_remitted = col_sum_ci(df, "subtotal tax remitted by doordash")

    # All deductions sum (signs in source are negative, so use abs and flip)
    commission_abs = abs(commission)
    marketing_abs = abs(marketing)
    cust_disc_abs = abs(cust_disc_self)
    error_abs = abs(error_charges)

    # Net deductions = gross - net (always reconciles to the truth in the file)
    other_deductions = round(max(subtotal - net_total, 0), 2)

    status_col = find_col_ci(df, "final order status", "payout status")
    status_counts = {}
    if status_col:
        status_counts = df[status_col].value_counts().to_dict()

    return {
        "platform": "doordash",
        "gross_amount": round(subtotal, 2),
        "gst_tax_deductions": 0.0,
        "other_deductions": other_deductions,
        "net_payout": round(net_total, 2),
        "order_count": int(len(df)),
        "tds": 0.0,
        "currency": "AUD",
        "raw_summary": {
            "subtotal_including_gst": round(subtotal, 2),
            "commission": round(commission_abs, 2),
            "marketing_fees": round(marketing_abs, 2),
            "customer_discounts_funded_by_you": round(cust_disc_abs, 2),
            "error_charges": round(error_abs, 2),
            "adjustments": round(adjustments, 2),
            "tax_remitted_by_doordash": round(tax_remitted, 2),
            "net_total": round(net_total, 2),
            "total_orders": int(len(df)),
            "status_breakdown": status_counts,
        },
    }


def parse_phonepe(filepath: str, bank_filepath: str = None) -> Dict[str, Any]:
    """Parse PhonePe transaction report + optionally match with Bank Statement.
    PhonePe settles next-day: bank credit on day D is for EDC transactions on day D-1.
    If bank_filepath provided: matches and calculates PhonePe charges."""
    df = pd.read_excel(filepath)

    status_col = [c for c in df.columns if "transaction status" in c.lower()]
    if status_col:
        completed = df[df[status_col[0]].str.upper().str.strip() == "COMPLETED"]
    else:
        completed = df

    amt_col = [c for c in df.columns if "total transaction amount" in c.lower()]
    total_amount = float(pd.to_numeric(completed[amt_col[0]], errors="coerce").sum()) if amt_col else 0.0
    total_txns = int(len(df))
    completed_txns = int(len(completed))

    if not bank_filepath:
        return {
            "platform": "phonepe",
            "gross_amount": round(total_amount, 2),
            "gst_tax_deductions": 0.0,
            "other_deductions": 0.0,
            "net_payout": round(total_amount, 2),
            "order_count": completed_txns,
            "tds": 0.0,
            "currency": "INR",
            "raw_summary": {
                "total_transactions": total_txns,
                "completed_transactions": completed_txns,
                "total_collection": round(total_amount, 2),
                "bank_statement_uploaded": False,
            },
        }

    # ── MATCH WITH BANK STATEMENT ──
    from datetime import timedelta

    # Parse bank statement
    df_bank_raw = pd.read_excel(bank_filepath, header=None)
    header_row = None
    for i in range(min(30, len(df_bank_raw))):
        row_vals = [str(v).lower() for v in df_bank_raw.iloc[i].tolist() if str(v) != 'nan']
        joined = ' '.join(row_vals)
        if 'transaction date' in joined and ('particulars' in joined or 'description' in joined):
            header_row = i
            break
        if 'txn date' in joined and 'debit' in joined:
            header_row = i
            break

    if header_row is None:
        raise ValueError("Could not find transaction header in bank statement.")

    df_bank = pd.read_excel(bank_filepath, header=header_row)
    df_bank.columns = [str(c).strip() for c in df_bank.columns]

    # Find PhonePe rows
    particulars_col = None
    for c in df_bank.columns:
        if 'particular' in c.lower() or 'description' in c.lower() or 'narration' in c.lower():
            particulars_col = c
            break

    credit_col = None
    for c in df_bank.columns:
        if c.lower().strip() == 'credit':
            credit_col = c
            break

    txn_date_col = None
    for c in df_bank.columns:
        if 'transaction date' in c.lower() or 'txn date' in c.lower():
            txn_date_col = c
            break

    phonepe_rows = df_bank[df_bank[particulars_col].str.contains('PHONEPE', case=False, na=False)].copy()

    if phonepe_rows.empty:
        raise ValueError("No PhonePe settlement entries found in bank statement.")

    phonepe_rows['bank_credit'] = pd.to_numeric(phonepe_rows[credit_col], errors='coerce').fillna(0)
    phonepe_rows['bank_date'] = pd.to_datetime(phonepe_rows[txn_date_col], dayfirst=True, format='mixed', errors='coerce')
    # Drop rows where date couldn't be parsed (defensive — keeps the rest usable)
    phonepe_rows = phonepe_rows.dropna(subset=['bank_date'])
    # PhonePe settles next-day: bank credit date - 1 = EDC transaction date
    phonepe_rows['edc_date'] = (phonepe_rows['bank_date'] - timedelta(days=1)).dt.strftime('%Y-%m-%d')

    # Group EDC by date
    completed_copy = completed.copy()
    completed_copy['txn_date'] = pd.to_datetime(completed_copy['Transaction Date']).dt.strftime('%Y-%m-%d')
    edc_by_date = completed_copy.groupby('txn_date').agg(
        edc_amount=(amt_col[0], 'sum'),
        txn_count=(amt_col[0], 'count')
    ).reset_index()
    edc_by_date.columns = ['date', 'edc_amount', 'txn_count']

    # Group bank by EDC date (shifted)
    bank_by_edc_date = phonepe_rows.groupby('edc_date').agg(
        bank_credit=('bank_credit', 'sum')
    ).reset_index()
    bank_by_edc_date.columns = ['date', 'bank_credit']

    # Merge
    merged = pd.merge(edc_by_date, bank_by_edc_date, on='date', how='outer').sort_values('date').fillna(0)
    merged['charge'] = merged['edc_amount'] - merged['bank_credit']
    merged['charge_pct'] = merged.apply(
        lambda r: round((r['charge'] / r['edc_amount'] * 100), 2) if r['edc_amount'] > 0 else 0, axis=1
    )

    # Monthly totals: use EDC month range, filter bank settlements within it
    edc_dates_parsed = pd.to_datetime(completed_copy['txn_date'])
    edc_month_start = edc_dates_parsed.min().strftime('%Y-%m-%d')
    edc_month_end = edc_dates_parsed.max().strftime('%Y-%m-%d')

    bank_in_month = phonepe_rows[
        (phonepe_rows['edc_date'] >= edc_month_start) &
        (phonepe_rows['edc_date'] <= edc_month_end)
    ]
    total_bank_in_month = float(bank_in_month['bank_credit'].sum())
    # For PhonePe: the difference is NOT charges — it's sundry debtors
    # (last day's EDC settles in next month's bank statement)
    sundry_debtors = max(total_amount - total_bank_in_month, 0)

    # Daily breakdown
    daily_breakdown = []
    for _, r in merged.iterrows():
        daily_breakdown.append({
            "date": r['date'],
            "edc_amount": round(float(r['edc_amount']), 2),
            "bank_credit": round(float(r['bank_credit']), 2),
            "bank_charge": round(float(r['charge']), 2),
            "charge_pct": float(r['charge_pct']),
            "txn_count": int(r['txn_count']),
        })

    unmatched_edc = merged[(merged['edc_amount'] > 0) & (merged['bank_credit'] == 0)]
    unmatched_bank = merged[(merged['edc_amount'] == 0) & (merged['bank_credit'] > 0)]

    return {
        "platform": "phonepe",
        "gross_amount": round(total_amount, 2),
        "gst_tax_deductions": 0.0,
        "other_deductions": 0.0,
        "sundry_debtors": round(sundry_debtors, 2),
        "net_payout": round(total_bank_in_month, 2),
        "order_count": completed_txns,
        "tds": 0.0,
        "currency": "INR",
        "raw_summary": {
            "total_transactions": total_txns,
            "completed_transactions": completed_txns,
            "total_collection": round(total_amount, 2),
            "total_bank_credits_in_month": round(total_bank_in_month, 2),
            "sundry_debtors": round(sundry_debtors, 2),
            "bank_settlements_matched": int(len(bank_in_month)),
            "unmatched_edc_days": int(len(unmatched_edc)),
            "unmatched_bank_days": int(len(unmatched_bank)),
            "daily_breakdown": daily_breakdown,
            "bank_statement_uploaded": True,
        },
    }


def _load_cards_edc(filepath: str) -> Dict[str, Any]:
    """Load Cards EDC report supporting both:
      • HDFC India: header on row 0 with columns 'Date', 'Amount', 'Status'.
      • ANZ Worldline Australia: 4-5 metadata rows on top, then headers
        'Transaction date', 'Gross amount', 'Status', etc.
    Returns dict with {df, date_col, amount_col, status_col, format, currency}.
    """
    # Try header=0 first
    df0 = pd.read_excel(filepath)
    cols_lc = [str(c).strip().lower() for c in df0.columns]
    has_amt = any(c == 'amount' for c in cols_lc)
    has_status = any('status' in c for c in cols_lc)
    if has_amt and has_status and not all(str(c).startswith('Unnamed') for c in df0.columns[:5]):
        return {
            'df': df0,
            'date_col': find_col_ci(df0, 'transaction date', 'date'),
            'amount_col': find_col_ci(df0, 'amount'),
            'status_col': find_col_ci(df0, 'status'),
            'format': 'hdfc',
            'currency': 'INR',
        }

    # ANZ Worldline: scan first 20 rows for header
    raw = pd.read_excel(filepath, header=None)
    header_row = None
    for i in range(min(20, len(raw))):
        cells = [str(v).strip().lower() for v in raw.iloc[i].tolist() if str(v) != 'nan']
        if any('transaction date' in c for c in cells) and any('gross amount' in c for c in cells):
            header_row = i
            break
    if header_row is None:
        raise ValueError("Could not find EDC header row. Expected 'Transaction date' and 'Gross amount' (ANZ) or 'Date' and 'Amount' (HDFC).")

    df = pd.read_excel(filepath, header=header_row)
    df.columns = [str(c).strip() for c in df.columns]
    return {
        'df': df,
        'date_col': find_col_ci(df, 'transaction date', 'date'),
        'amount_col': find_col_ci(df, 'gross amount', 'amount'),
        'status_col': find_col_ci(df, 'status'),
        'format': 'anz',
        'currency': 'AUD',
    }


def parse_cards(filepath: str, bank_filepath: str = None) -> Dict[str, Any]:
    """Parse Card EDC report + optionally match with Bank Statement to calculate MDR charges.
    Supports HDFC (India) and ANZ Worldline (Australia) EDC formats.
    If bank_filepath is provided: matches EDC transactions to bank settlements by date.
    If not: returns EDC totals only (no commission calculation)."""
    edc = _load_cards_edc(filepath)
    df = edc['df']
    date_col = edc['date_col']
    amt_col = edc['amount_col']
    status_col = edc['status_col']
    currency = edc['currency']
    fmt = edc['format']

    if not amt_col:
        raise ValueError("EDC file is missing an Amount/Gross amount column.")

    if status_col:
        ok_statuses = {'SETTLED', 'CAPTURED'}
        settled = df[df[status_col].astype(str).str.upper().str.strip().isin(ok_statuses)]
    else:
        settled = df

    total_amount = float(pd.to_numeric(settled[amt_col], errors="coerce").fillna(0).sum())
    total_txns = int(len(df))
    settled_txns = int(len(settled))
    failed_txns = total_txns - settled_txns

    # For ANZ Worldline format the Surcharge column gives EXACT per-txn MDR
    surcharge_col = find_col_ci(settled, 'surcharge amount') if fmt == 'anz' else None
    edc_surcharge_total = 0.0
    if surcharge_col:
        edc_surcharge_total = float(pd.to_numeric(settled[surcharge_col], errors='coerce').fillna(0).sum())

    # If no bank statement, return EDC-only summary
    if not bank_filepath:
        # Use Surcharge column as MDR if present (ANZ Worldline)
        mdr = round(edc_surcharge_total, 2)
        return {
            "platform": "cards",
            "gross_amount": round(total_amount, 2),
            "gst_tax_deductions": 0.0,
            "other_deductions": mdr,
            "net_payout": round(total_amount - mdr, 2),
            "order_count": settled_txns,
            "tds": 0.0,
            "currency": currency,
            "raw_summary": {
                "edc_format": fmt,
                "total_transactions": total_txns,
                "settled_transactions": settled_txns,
                "failed_transactions": failed_txns,
                "total_settled_amount": round(total_amount, 2),
                "surcharge_total": mdr,
                "avg_surcharge_pct": round((mdr / total_amount * 100), 2) if total_amount > 0 else 0,
                "bank_statement_uploaded": False,
            },
        }

    # ── MATCH WITH BANK STATEMENT ──
    import re

    bank = _load_bank_statement_normalized(bank_filepath)
    df_bank = bank['df']
    bank_fmt = bank['format']

    # Identify card-settlement rows by particulars pattern
    if bank_fmt == 'anz':
        # ANZ: card settlements come in as "ANZ TRANSACTIVE DIRECT CREDIT ANZ WORLDLINE <ref>"
        # Amex separately as "ANZ TRANSACTIVE DIRECT CREDIT AMEX GR <amt> <ref>"
        mask = df_bank['particulars'].str.contains(
            r'ANZ\s*WORLDLINE|AMEX\s*GR', case=False, regex=True, na=False
        )
    else:
        # India banks: HDFC = "CARD PMT SETDT-DDMMYYYY"; IDFC = "POS SETT"/"EDC SETT";
        # ICICI = "POS REVERSAL"/"MERCH SETT"; Axis = "POS CR"/"CARD SETT"; etc.
        india_patterns = (
            r'CARD\s*PMT|POS\s*SETT|EDC\s*SETT|MERCH\s*SETT|POS\s*CR|CARD\s*SETT|'
            r'SETDT|CASHFREE\s*POS|EDC\s*SETTLEMENT|EZETAP|MSWIPE|PINELABS|RAZORPAY\s*POS'
        )
        mask = df_bank['particulars'].str.contains(india_patterns, case=False, regex=True, na=False)
    card_settlements = df_bank[mask].copy()
    if card_settlements.empty:
        raise ValueError(
            f"No card settlement entries found in bank statement (format={bank_fmt}). "
            f"Expected " + ('ANZ WORLDLINE / AMEX GR' if bank_fmt == 'anz'
                            else 'CARD PMT / POS SETT / EDC SETT / MERCH SETT / SETDT- patterns')
            + "."
        )

    # Settlement date
    if bank_fmt == 'anz':
        card_settlements['settle_date'] = card_settlements['date'].dt.strftime('%Y-%m-%d')
    else:
        def extract_setdt(desc):
            # HDFC format embeds the actual settle date as SETDT-DDMMYYYY
            m = re.search(r'SETDT-(\d{2})(\d{2})(\d{4})', str(desc))
            if m:
                return f'{m.group(3)}-{m.group(2)}-{m.group(1)}'
            return None
        card_settlements['settle_date'] = card_settlements['particulars'].apply(extract_setdt)
        # If no SETDT- pattern (IDFC / ICICI / Axis), fall back to bank credit date
        no_setdt = card_settlements['settle_date'].isna()
        if no_setdt.any():
            card_settlements.loc[no_setdt, 'settle_date'] = (
                card_settlements.loc[no_setdt, 'date'].dt.strftime('%Y-%m-%d')
            )

    card_settlements['bank_credit'] = card_settlements['credit'].astype(float)
    card_settlements = card_settlements.dropna(subset=['settle_date'])

    # ── CALCULATE MONTHLY TOTALS ──
    settled_copy = settled.copy()
    settled_copy[amt_col] = pd.to_numeric(settled_copy[amt_col], errors='coerce').fillna(0)
    settled_copy['txn_date'] = pd.to_datetime(settled_copy[date_col], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
    settled_copy = settled_copy.dropna(subset=['txn_date'])
    if settled_copy.empty:
        raise ValueError("Could not parse any EDC transaction dates.")
    edc_dates = pd.to_datetime(settled_copy['txn_date'])
    edc_month_start = edc_dates.min().strftime('%Y-%m-01')
    edc_month_end = edc_dates.max().strftime('%Y-%m-%d')

    if bank_fmt == 'anz':
        # ANZ Worldline settles T+1 to T+2 (T+3 over weekends). Catch all bank
        # credits whose date falls in (EDC month → EDC month end + 5 days).
        match_col = 'settle_date_in_window'
        settle_window_end = (edc_dates.max() + pd.Timedelta(days=5)).strftime('%Y-%m-%d')
        card_settlements[match_col] = card_settlements['date'].dt.strftime('%Y-%m-%d')
        # Use a slightly delayed start (T+1) so prior-month settlements don't leak in
        match_start = (edc_dates.min() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        match_end = settle_window_end
    else:
        match_col = 'settle_date'
        match_start = edc_month_start
        match_end = edc_month_end

    bank_in_month = card_settlements[
        (card_settlements[match_col] >= match_start) &
        (card_settlements[match_col] <= match_end)
    ]
    total_bank_in_month = float(bank_in_month['bank_credit'].sum())
    # Clamp net_payout to gross_amount (you cannot receive more than the EDC total)
    net_payout_clamped = min(total_bank_in_month, total_amount)
    bank_implied_charges = total_amount - net_payout_clamped
    # ANZ Worldline gives exact per-txn surcharge — trust that as MDR if present
    if edc_surcharge_total > 0:
        total_bank_charges = edc_surcharge_total
        net_payout_final = round(total_amount - edc_surcharge_total, 2)
    else:
        total_bank_charges = bank_implied_charges
        net_payout_final = round(net_payout_clamped, 2)
    avg_mdr = round((total_bank_charges / total_amount * 100), 2) if total_amount > 0 else 0

    # ── DAILY BREAKDOWN ──
    edc_by_date = settled_copy.groupby('txn_date').agg(
        edc_amount=(amt_col, 'sum'),
        txn_count=(amt_col, 'count')
    ).reset_index()
    edc_by_date.columns = ['date', 'edc_amount', 'txn_count']

    bank_by_date = card_settlements.groupby(match_col).agg(
        bank_credit=('bank_credit', 'sum')
    ).reset_index()
    bank_by_date.columns = ['date', 'bank_credit']

    merged = pd.merge(edc_by_date, bank_by_date, on='date', how='outer').sort_values('date').fillna(0)
    merged['charge'] = merged['edc_amount'] - merged['bank_credit']
    merged['charge_pct'] = merged.apply(
        lambda r: round((r['charge'] / r['edc_amount'] * 100), 2) if r['edc_amount'] > 0 else 0, axis=1
    )

    daily_breakdown = []
    for _, r in merged.iterrows():
        daily_breakdown.append({
            "date": r['date'],
            "edc_amount": round(float(r['edc_amount']), 2),
            "bank_credit": round(float(r['bank_credit']), 2),
            "bank_charge": round(float(r['charge']), 2),
            "charge_pct": float(r['charge_pct']),
            "txn_count": int(r['txn_count']),
        })

    unmatched_edc = merged[(merged['edc_amount'] > 0) & (merged['bank_credit'] == 0)]
    unmatched_bank = merged[(merged['edc_amount'] == 0) & (merged['bank_credit'] > 0)]

    return {
        "platform": "cards",
        "gross_amount": round(total_amount, 2),
        "gst_tax_deductions": 0.0,
        "other_deductions": round(max(total_bank_charges, 0), 2),
        "net_payout": net_payout_final,
        "order_count": settled_txns,
        "tds": 0.0,
        "currency": currency,
        "raw_summary": {
            "edc_format": fmt,
            "bank_format": bank_fmt,
            "total_transactions": total_txns,
            "settled_transactions": settled_txns,
            "failed_transactions": failed_txns,
            "total_edc_amount": round(total_amount, 2),
            "total_bank_credits_in_window": round(total_bank_in_month, 2),
            "edc_surcharge_total": round(edc_surcharge_total, 2),
            "mdr_source": "edc_surcharge_column" if edc_surcharge_total > 0 else "bank_diff",
            "total_bank_charges": round(max(total_bank_charges, 0), 2),
            "avg_mdr_rate": max(avg_mdr, 0),
            "bank_settlements_matched": int(len(bank_in_month)),
            "unmatched_edc_days": int(len(unmatched_edc)),
            "unmatched_bank_days": int(len(unmatched_bank)),
            "daily_breakdown": daily_breakdown,
            "bank_statement_uploaded": True,
        },
    }


# Master parser dispatcher
PARSERS = {
    "zomato": parse_zomato,
    "swiggy": parse_swiggy,
    "doordash": parse_doordash,
    "phonepe": parse_phonepe,
    "cards": parse_cards,
}


def parse_commission_file(filepath: str, platform: str = None, filename: str = "") -> Dict[str, Any]:
    """
    Parse a commission Excel file. Auto-detects platform if not provided.
    Returns parsed summary dict with keys:
      platform, gross_amount, gst_tax_deductions, other_deductions, net_payout,
      order_count, tds, currency, raw_summary
    """
    if not platform:
        platform = detect_platform(filepath, filename)

    if not platform:
        raise ValueError("Could not auto-detect platform. Please specify the platform manually.")

    platform = platform.lower().strip()
    parser = PARSERS.get(platform)
    if not parser:
        raise ValueError(f"No parser available for platform: {platform}")

    result = parser(filepath)
    result["platform"] = platform
    return result
