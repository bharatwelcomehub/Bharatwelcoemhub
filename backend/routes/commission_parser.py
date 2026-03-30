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
    Gross = Subtotal including GST
    Other Deductions = abs(Commission) + abs(Marketing fees)
    Net Payout = Net total"""
    df = pd.read_excel(filepath)

    subtotal = float(pd.to_numeric(df.get("Subtotal including GST", pd.Series()), errors="coerce").sum())
    commission = float(pd.to_numeric(df.get("Commission", pd.Series()), errors="coerce").sum())
    net_total = float(pd.to_numeric(df.get("Net total", pd.Series()), errors="coerce").sum())
    marketing_fees = float(pd.to_numeric(
        df.get("Marketing fees | (including any applicable taxes)", pd.Series()),
        errors="coerce",
    ).sum())

    commission_abs = abs(commission)
    marketing_abs = abs(marketing_fees)

    # GST is embedded in subtotal for DoorDash (Australia) — not broken out separately
    # So gst_tax = 0 and other = all deductions
    other_deductions = commission_abs + marketing_abs

    status_col = [c for c in df.columns if "final order status" in c.lower()]
    status_counts = {}
    if status_col:
        status_counts = df[status_col[0]].value_counts().to_dict()

    return {
        "platform": "doordash",
        "gross_amount": round(subtotal, 2),
        "gst_tax_deductions": 0.0,
        "other_deductions": round(other_deductions, 2),
        "net_payout": round(net_total, 2),
        "order_count": int(len(df)),
        "tds": 0.0,
        "currency": "AUD",
        "raw_summary": {
            "subtotal_including_gst": round(subtotal, 2),
            "commission": round(commission, 2),
            "marketing_fees": round(marketing_fees, 2),
            "net_total": round(net_total, 2),
            "total_orders": int(len(df)),
            "status_breakdown": status_counts,
        },
    }


def parse_phonepe(filepath: str) -> Dict[str, Any]:
    """Parse PhonePe transaction report — payment collection only."""
    df = pd.read_excel(filepath)

    status_col = [c for c in df.columns if "transaction status" in c.lower()]
    if status_col:
        completed = df[df[status_col[0]].str.upper().str.strip() == "COMPLETED"]
    else:
        completed = df

    amt_col = [c for c in df.columns if "total transaction amount" in c.lower()]
    total_amount = float(pd.to_numeric(completed[amt_col[0]], errors="coerce").sum()) if amt_col else 0.0

    return {
        "platform": "phonepe",
        "gross_amount": round(total_amount, 2),
        "gst_tax_deductions": 0.0,
        "other_deductions": 0.0,
        "net_payout": round(total_amount, 2),
        "order_count": int(len(completed)),
        "tds": 0.0,
        "currency": "INR",
        "raw_summary": {
            "total_transactions": int(len(df)),
            "completed_transactions": int(len(completed)),
            "total_collection": round(total_amount, 2),
        },
    }


def parse_cards(filepath: str) -> Dict[str, Any]:
    """Parse Card settlement report — only SETTLED transactions."""
    df = pd.read_excel(filepath)

    status_col = [c for c in df.columns if c.lower() == "status"]
    if status_col:
        settled = df[df[status_col[0]].str.upper().str.strip() == "SETTLED"]
    else:
        settled = df

    amt_col = [c for c in df.columns if c.lower() == "amount"]
    total_amount = float(pd.to_numeric(settled[amt_col[0]], errors="coerce").sum()) if amt_col else 0.0

    return {
        "platform": "cards",
        "gross_amount": round(total_amount, 2),
        "gst_tax_deductions": 0.0,
        "other_deductions": 0.0,
        "net_payout": round(total_amount, 2),
        "order_count": int(len(settled)),
        "tds": 0.0,
        "currency": "INR",
        "raw_summary": {
            "total_transactions": int(len(df)),
            "settled_transactions": int(len(settled)),
            "total_settled_amount": round(total_amount, 2),
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
