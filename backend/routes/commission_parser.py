# =======================================
# Commission Excel Parser
# Parses Zomato, Swiggy, DoorDash, PhonePe, Cards
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
    """Parse Zomato Payout Breakup sheet for summary financials."""
    wb = openpyxl.load_workbook(filepath, data_only=True)

    # Find the Payout Breakup sheet
    target_sheet = None
    for name in wb.sheetnames:
        if "payout breakup" in name.lower():
            target_sheet = name
            break
    if not target_sheet:
        # Fallback to first sheet
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

    # Extract key values
    gross_amount = safe_float(label_map.get("subtotal (items total)", 0))
    net_order_value = safe_float(label_map.get("net order value", 0))
    service_fees = safe_float(label_map.get("service fees & payment mechanism fees", 0))
    service_fee = safe_float(label_map.get("service fee", 0))
    payment_mech_fee = safe_float(label_map.get("payment mechanism fee", 0))
    taxes_on_service = safe_float(label_map.get("taxes on service & payment mechanism fees", 0))
    tds = safe_float(label_map.get("tds 194o amount", 0))
    tcs = safe_float(label_map.get("tax collected at source + tcs igst amount", 0))
    gst_section95 = safe_float(label_map.get("gst paid by zomato on behalf of restaurant - under section 9(5)", 0))
    net_payout = safe_float(label_map.get("net payout", 0))

    # Order count
    order_count = 0
    for r in range(1, min(10, ws.max_row + 1)):
        label = ws.cell(row=r, column=3).value
        if label and "number of orders" in str(label).lower():
            order_count = int(safe_float(ws.cell(row=r, column=4).value))
            break

    wb.close()

    return {
        "platform": "zomato",
        "gross_amount": round(gross_amount, 2),
        "commission_amount": round(service_fees, 2),
        "gst_on_commission": round(taxes_on_service, 2),
        "tds": round(tds, 2),
        "net_payout": round(net_payout, 2),
        "order_count": order_count,
        "currency": "INR",
        "raw_summary": {
            "subtotal_items": round(gross_amount, 2),
            "net_order_value": round(net_order_value, 2),
            "service_fee": round(service_fee, 2),
            "payment_mechanism_fee": round(payment_mech_fee, 2),
            "taxes_on_service_fees": round(taxes_on_service, 2),
            "tds_194o": round(tds, 2),
            "tcs": round(tcs, 2),
            "gst_section_9_5": round(gst_section95, 2),
            "net_payout": round(net_payout, 2),
        },
    }


def parse_swiggy(filepath: str) -> Dict[str, Any]:
    """Parse Swiggy order-level report and aggregate ALL orders (including cancelled)."""
    df = pd.read_excel(filepath)

    # Use ALL rows — cancelled orders also have financial impact (deductions)
    all_orders = df

    # Find columns by partial match
    def find_col(keywords):
        for c in df.columns:
            cl = c.lower()
            if all(k in cl for k in keywords):
                return c
        return None

    gross_col = find_col(["item", "total"])
    comm_col = find_col(["total swiggy service fee", "without taxes"])
    gst_col = find_col(["taxes on swiggy fee"])
    tds_col = find_col(["tds"])
    net_col = find_col(["net payable", "after tcs"])

    gross_amount = float(pd.to_numeric(all_orders[gross_col], errors="coerce").sum()) if gross_col else 0.0
    commission = float(pd.to_numeric(all_orders[comm_col], errors="coerce").sum()) if comm_col else 0.0
    gst_on_comm = float(pd.to_numeric(all_orders[gst_col], errors="coerce").sum()) if gst_col else 0.0
    tds = float(pd.to_numeric(all_orders[tds_col], errors="coerce").sum()) if tds_col else 0.0
    net_payout = float(pd.to_numeric(all_orders[net_col], errors="coerce").sum()) if net_col else 0.0

    # Count by status for reference
    status_col = [c for c in df.columns if "order status" in c.lower()]
    status_counts = {}
    if status_col:
        status_counts = df[status_col[0]].value_counts().to_dict()

    return {
        "platform": "swiggy",
        "gross_amount": round(gross_amount, 2),
        "commission_amount": round(commission, 2),
        "gst_on_commission": round(gst_on_comm, 2),
        "tds": round(tds, 2),
        "net_payout": round(net_payout, 2),
        "order_count": int(len(all_orders)),
        "currency": "INR",
        "raw_summary": {
            "total_orders": int(len(df)),
            "status_breakdown": status_counts,
            "gross_items_total": round(gross_amount, 2),
            "swiggy_service_fee": round(commission, 2),
            "taxes_on_swiggy_fee": round(gst_on_comm, 2),
            "tds": round(tds, 2),
            "net_payable": round(net_payout, 2),
        },
    }


def parse_doordash(filepath: str) -> Dict[str, Any]:
    """Parse DoorDash detailed transactions report — ALL orders (including cancelled)."""
    df = pd.read_excel(filepath)

    # Use ALL rows — cancelled orders also have financial impact
    all_orders = df

    subtotal = float(pd.to_numeric(all_orders.get("Subtotal including GST", pd.Series()), errors="coerce").sum())
    commission = float(pd.to_numeric(all_orders.get("Commission", pd.Series()), errors="coerce").sum())
    net_total = float(pd.to_numeric(all_orders.get("Net total", pd.Series()), errors="coerce").sum())
    marketing_fees = float(pd.to_numeric(
        all_orders.get("Marketing fees | (including any applicable taxes)", pd.Series()),
        errors="coerce",
    ).sum())

    # Commission from DoorDash is negative (it's a deduction); take absolute value
    commission_abs = abs(commission)

    # Count by status for reference
    status_col = [c for c in df.columns if "final order status" in c.lower()]
    status_counts = {}
    if status_col:
        status_counts = df[status_col[0]].value_counts().to_dict()

    return {
        "platform": "doordash",
        "gross_amount": round(subtotal, 2),
        "commission_amount": round(commission_abs, 2),
        "gst_on_commission": 0.0,
        "tds": 0.0,
        "net_payout": round(net_total, 2),
        "order_count": int(len(all_orders)),
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

    # Filter completed transactions
    status_col = [c for c in df.columns if "transaction status" in c.lower()]
    if status_col:
        completed = df[df[status_col[0]].str.upper().str.strip() == "COMPLETED"]
    else:
        completed = df

    amt_col = [c for c in df.columns if "total transaction amount" in c.lower()]
    if amt_col:
        total_amount = float(pd.to_numeric(completed[amt_col[0]], errors="coerce").sum())
    else:
        total_amount = 0.0

    return {
        "platform": "phonepe",
        "gross_amount": round(total_amount, 2),
        "commission_amount": 0.0,  # PhonePe report doesn't include MDR breakdown
        "gst_on_commission": 0.0,
        "tds": 0.0,
        "net_payout": round(total_amount, 2),
        "order_count": int(len(completed)),
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

    # Filter settled transactions
    status_col = [c for c in df.columns if c.lower() == "status"]
    if status_col:
        settled = df[df[status_col[0]].str.upper().str.strip() == "SETTLED"]
    else:
        settled = df

    amt_col = [c for c in df.columns if c.lower() == "amount"]
    if amt_col:
        total_amount = float(pd.to_numeric(settled[amt_col[0]], errors="coerce").sum())
    else:
        total_amount = 0.0

    return {
        "platform": "cards",
        "gross_amount": round(total_amount, 2),
        "commission_amount": 0.0,  # Card MDR not in this report
        "gst_on_commission": 0.0,
        "tds": 0.0,
        "net_payout": round(total_amount, 2),
        "order_count": int(len(settled)),
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
      platform, gross_amount, commission_amount, gst_on_commission, tds, net_payout, order_count, currency, raw_summary
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
