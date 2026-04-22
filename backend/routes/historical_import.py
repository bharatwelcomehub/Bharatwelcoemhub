"""Historical Data Import

Admin endpoint for ingesting WC-rollup Excel files into a
`historical_monthly_summary` collection. The collection is read by the
WC-Breakdown aggregator and MIS overview as a fallback source of truth
for months that have no daily rows in `daily_sales` / `db.expenses`.
"""
import io
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from motor.motor_asyncio import AsyncIOMotorClient
import os
import openpyxl

from .attendance_dashboard import get_session, check_super_admin

logger = logging.getLogger(__name__)

_mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _mongo[os.environ["DB_NAME"]]

router = APIRouter(prefix="/api/historical", tags=["historical"])


# Center-name keyword → system center code (used for filename-based auto-detect
# AND sheet-name mapping in WC files).
FILENAME_CENTER_KEYWORDS = [
    ("HSR", "PB-HSR"),
    ("DOMBIVLI", "PB-DV"),
    ("DOMBVLI", "PB-DV"),
    ("THANE", "PB-TH"),
    ("S-NAGAR", "PB-SN"),
    ("SAMBHAJI", "PB-SN"),
    ("SN", "PB-SN"),
    ("KHARADI", "PB-KN"),
    ("KN", "PB-KN"),
    ("HINJAWADI", "PB-HW"),
    ("HINJAWADE", "PB-HW"),
    ("HW", "PB-HW"),
    ("MGT", "PB-MGT"),
    ("MFPL", "PB-MGT"),
    ("KALYAN", "PB-KAL"),
    ("KAL", "PB-KAL"),
    ("PERTH", "PB-PERTH"),
]

MONTH_NAMES = {
    "JAN": 1, "JANUARY": 1, "FEB": 2, "FEBRUARY": 2, "MAR": 3, "MARCH": 3,
    "APR": 4, "APRIL": 4, "MAY": 5, "JUN": 6, "JUNE": 6, "JUL": 7, "JULY": 7,
    "AUG": 8, "AUGUST": 8, "SEP": 9, "SEPT": 9, "SEPTEMBER": 9,
    "OCT": 10, "OCTOBER": 10, "NOV": 11, "NOVEMBER": 11, "DEC": 12, "DECEMBER": 12,
}


def _detect_center_from_filename(name: str) -> Optional[str]:
    import re as _re
    up = name.upper()
    # Separate tokens around non-alphanumerics so "HSR" doesn't match words like "THOSE"
    tokens = set(_re.findall(r"[A-Z0-9]+", up))
    for kw, code in FILENAME_CENTER_KEYWORDS:
        if kw in tokens:
            return code
    return None


def _detect_month_from_filename(name: str) -> Optional[str]:
    import re as _re
    up = name.upper()
    # Look for a month name followed (possibly) by a year
    # Patterns like "MARCH. 2026", "APRIL 2024", "MAR 26", "APR.18"
    m = _re.search(r"(JAN(?:UARY)?|FEB(?:RUARY)?|MAR(?:CH)?|APR(?:IL)?|MAY|JUN(?:E)?|JUL(?:Y)?|AUG(?:UST)?|SEP(?:T(?:EMBER)?)?|OCT(?:OBER)?|NOV(?:EMBER)?|DEC(?:EMBER)?)[.\s-]*((?:20)?\d{2})", up)
    if not m:
        return None
    mname = m.group(1)
    yraw = m.group(2)
    month_num = MONTH_NAMES.get(mname)
    if not month_num:
        return None
    year = int(yraw)
    if year < 100:
        year = 2000 + year
    return f"{year:04d}-{month_num:02d}"


# Sheet name (or uppercased keywords in it) → system center code.
# Matching is: if any key is a substring of the sheet name (upper) → map.
SHEET_TO_CENTER = {
    "S-NAGAR": "PB-SN",
    "SAMBHAJI": "PB-SN",
    "S NAGAR": "PB-SN",
    "DOMBIVLI": "PB-DV",
    "DOMBVLI": "PB-DV",
    "KHARADI": "PB-KN",
    "THANE": "PB-TH",
    "HSR": "PB-HSR",
    "HINJAWADI": "PB-HW",
    "HINJAWADE": "PB-HW",
    "BANER": "PB-MGT",  # TODO: confirm with user — using MGT as fallback
}


def _guess_center_from_sheet(sheet_name: str) -> Optional[str]:
    up = sheet_name.upper()
    for key, code in SHEET_TO_CENTER.items():
        if key in up:
            return code
    return None


# Canonical column aliases. Lowercased header → canonical key.
COLUMN_ALIASES = {
    "month": "month",
    "sale": "sale",
    "sales": "sale",
    "expenses": "expenses",
    "expense": "expenses",
    "p/l": "pnl",
    "pnl": "pnl",
    "profit/loss": "pnl",
    "working capital": "opening_wc",
    "bal. wc.": "closing_wc",
    "bal wc": "closing_wc",
    "balance wc": "closing_wc",
    "bal. wc": "closing_wc",
    "closing wc": "closing_wc",
    "diff.of wc.": "diff_wc",
    "diff of wc": "diff_wc",
    "diff wc": "diff_wc",
    "bank cl.bal.": "bank_balance",
    "bank cl bal": "bank_balance",
    "bank balance": "bank_balance",
    "bank bal": "bank_balance",
    "loan": "loan",
    "rev share": "rev_share",
}


def _parse_wc_sheet(ws) -> tuple[Optional[str], list[dict]]:
    """Return (center_code_guess, list_of_month_rows)."""
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return None, []
    
    center = _guess_center_from_sheet(ws.title)
    
    # Find header row (containing MONTH/SALE/EXPENSES)
    header_idx = None
    header_map = {}
    for ri, row in enumerate(rows[:15]):
        lowered = [str(c).strip().lower() if c is not None else "" for c in row]
        if any("month" == v for v in lowered) and any("sale" == v or "sales" == v for v in lowered):
            header_idx = ri
            for ci, v in enumerate(lowered):
                if v in COLUMN_ALIASES:
                    header_map[COLUMN_ALIASES[v]] = ci
            break
    
    if header_idx is None or "month" not in header_map:
        return center, []
    
    out = []
    for row in rows[header_idx + 1:]:
        mcell = row[header_map["month"]]
        if mcell is None:
            continue
        # Only accept actual datetime cells (skip stray text / totals)
        if not isinstance(mcell, datetime):
            continue
        month = mcell.strftime("%Y-%m")
        rec = {"month": month}
        for key, ci in header_map.items():
            if key == "month":
                continue
            val = row[ci] if ci < len(row) else None
            if isinstance(val, (int, float)):
                rec[key] = float(val)
            elif val in (None, ""):
                rec[key] = 0.0 if key in ("sale", "expenses", "pnl", "opening_wc", "closing_wc", "diff_wc", "bank_balance") else None
            else:
                try:
                    rec[key] = float(str(val).replace(",", ""))
                except (ValueError, TypeError):
                    rec[key] = None
        out.append(rec)
    return center, out


async def _upsert_rows(center: str, rows: list[dict], source: str, user: str):
    if not center or not rows:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    for r in rows:
        doc = {
            "center": center,
            "month": r["month"],
            "sale": r.get("sale", 0) or 0,
            "expenses": r.get("expenses", 0) or 0,
            "pnl": r.get("pnl", 0) or 0,
            "opening_wc": r.get("opening_wc", 0) or 0,
            "closing_wc": r.get("closing_wc", 0) or 0,
            "diff_wc": r.get("diff_wc", 0) or 0,
            "bank_balance": r.get("bank_balance", 0) or 0,
            "source": source,
            "updated_at": now,
            "updated_by": user,
        }
        await db.historical_monthly_summary.update_one(
            {"center": center, "month": r["month"]},
            {"$set": doc, "$setOnInsert": {"created_at": now, "created_by": user}},
            upsert=True,
        )
        inserted += 1
    return inserted


@router.post("/import-wc-file")
async def import_wc_file(file: UploadFile = File(...), token: str = Form(...)):
    """Upload a WC-Assessment Excel file. Each sheet whose name maps to a known
    center will be parsed (MONTH, SALE, EXPENSES, P/L, WORKING CAPITAL, BAL. WC., BANK CL.BAL.)
    and upserted into `historical_monthly_summary`.
    Loans sheets can be imported via /import-loans-file.
    """
    session = await get_session(token)
    if not session or not check_super_admin(session):
        raise HTTPException(403, "Only Super Admin can import historical data")
    
    user = session.get("managerName", "Admin")
    raw = await file.read()
    
    try:
        wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
    except Exception as exc:
        raise HTTPException(400, f"Could not read workbook: {exc}")
    
    summary = {
        "file": file.filename,
        "sheets_processed": 0,
        "sheets_skipped": [],
        "centers": {},
        "total_rows": 0,
    }
    for sn in wb.sheetnames:
        if "LOAN" in sn.upper():
            continue  # Loans handled separately
        ws = wb[sn]
        center, rows = _parse_wc_sheet(ws)
        if not center:
            summary["sheets_skipped"].append({"sheet": sn, "reason": "unknown center (no mapping)"})
            continue
        if not rows:
            summary["sheets_skipped"].append({"sheet": sn, "reason": "no parseable month rows"})
            continue
        n = await _upsert_rows(center, rows, source=f"wc_import:{file.filename}:{sn}", user=user)
        summary["sheets_processed"] += 1
        summary["centers"][center] = summary["centers"].get(center, 0) + n
        summary["total_rows"] += n
    
    logger.info(f"Historical WC import by {user}: {summary}")
    return {"success": True, **summary}


@router.post("/summary")
async def get_historical_summary(req: dict):
    """List imported historical data grouped by center."""
    token = req.get("token")
    session = await get_session(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    
    rows = await db.historical_monthly_summary.find({}, {"_id": 0}).to_list(5000)
    by_center: dict = {}
    for r in rows:
        c = r["center"]
        by_center.setdefault(c, {"center": c, "months": 0, "earliest": "", "latest": "", "total_sale": 0, "total_expenses": 0})
        by_center[c]["months"] += 1
        m = r["month"]
        if not by_center[c]["earliest"] or m < by_center[c]["earliest"]:
            by_center[c]["earliest"] = m
        if m > by_center[c]["latest"]:
            by_center[c]["latest"] = m
        by_center[c]["total_sale"] += float(r.get("sale", 0))
        by_center[c]["total_expenses"] += float(r.get("expenses", 0))
    
    return {"centers": list(by_center.values()), "total_rows": len(rows)}


# Counterparty-name keyword → system center code (for Loans sheet column groups)
COUNTERPARTY_TO_CENTER = {
    "MFPL": "PB-MGT",          # MFPL = central / HQ; map to PB-MGT by default
    "SAMBHAJI": "PB-SN",
    "S. NAGAR": "PB-SN",
    "S.NAGAR": "PB-SN",
    "S NAGAR": "PB-SN",
    "DOMBIVLI": "PB-DV",
    "KHARADI": "PB-KN",
    "THANE": "PB-TH",
    "HSR": "PB-HSR",
    "HINJAWADI": "PB-HW",
    "HINJAWADE": "PB-HW",
    "BANER": "PB-MGT",         # TODO confirm with user
}


def _guess_counterparty_from_header(text: str) -> Optional[str]:
    if not text:
        return None
    up = str(text).upper()
    for key, code in COUNTERPARTY_TO_CENTER.items():
        if key in up:
            return code
    return None


def _parse_loans_sheet(ws) -> tuple[Optional[str], list[dict]]:
    """Parse a LOANS sheet — sheet title identifies HOME center; counterparties
    appear in a row of headers above the repeated 4-column (DATE, AMOUNT GIVEN,
    AMOUNT RECD., BALANCE) groups. Returns (home_center, list_of_txns)."""
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return None, []
    
    # Home center: resolve from sheet title first (strip trailing account numbers)
    home = _guess_center_from_sheet(ws.title) or _guess_counterparty_from_header(ws.title)
    
    # Find header row (the one whose columns contain DATE + AMOUNT GIVEN + AMOUNT RECD)
    header_row_idx = None
    for ri, row in enumerate(rows[:20]):
        lowered = [str(c).strip().lower() if c is not None else "" for c in row]
        if lowered.count("date") >= 1 and any("amount given" in v for v in lowered) and any("amount recd" in v or "amount recd." in v for v in lowered):
            header_row_idx = ri
            break
    if header_row_idx is None:
        return home, []
    
    header = rows[header_row_idx]
    
    # Walk columns in groups of 4 starting where the first "DATE" appears
    first_date_ci = None
    for ci, v in enumerate(header):
        if str(v or "").strip().lower() == "date":
            first_date_ci = ci
            break
    if first_date_ci is None:
        return home, []
    
    # Counterparty names live in one of the rows above the header (within 3 rows)
    def _counterparty_for_col(ci: int) -> Optional[str]:
        # Scan up to 5 rows above the header for the nearest non-empty text in this column
        for up in range(1, 6):
            if header_row_idx - up < 0:
                break
            cell = rows[header_row_idx - up]
            if ci < len(cell) and cell[ci]:
                cc = _guess_counterparty_from_header(cell[ci])
                if cc:
                    return cc
            # Also scan +/- 1 columns (counterparty name often spans group)
            for off in (-1, 1, 2, 3):
                if 0 <= ci + off < len(cell) and cell[ci + off]:
                    cc = _guess_counterparty_from_header(cell[ci + off])
                    if cc:
                        return cc
        return None
    
    # Build list of (counterparty, date_ci, given_ci, recd_ci) column groups
    groups = []
    ci = first_date_ci
    ncols = len(header)
    while ci + 2 < ncols:
        # Confirm this position is a DATE header
        if str(header[ci] or "").strip().lower() != "date":
            ci += 1
            continue
        cp = _counterparty_for_col(ci)
        if cp and cp != home:
            groups.append({"cp": cp, "date_ci": ci, "given_ci": ci + 1, "recd_ci": ci + 2})
        ci += 4  # step past this group
    
    if not groups:
        return home, []
    
    txns = []
    for row in rows[header_row_idx + 1:]:
        for g in groups:
            dt = row[g["date_ci"]] if g["date_ci"] < len(row) else None
            if not isinstance(dt, datetime):
                continue
            given = row[g["given_ci"]] if g["given_ci"] < len(row) else None
            recd = row[g["recd_ci"]] if g["recd_ci"] < len(row) else None
            try:
                given_v = float(given) if isinstance(given, (int, float)) else 0.0
            except Exception:
                given_v = 0.0
            try:
                recd_v = float(recd) if isinstance(recd, (int, float)) else 0.0
            except Exception:
                recd_v = 0.0
            if given_v > 0:
                txns.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "counterparty": g["cp"],
                    "direction": "given",   # home gave money to counterparty
                    "amount": round(given_v, 2),
                })
            if recd_v > 0:
                txns.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "counterparty": g["cp"],
                    "direction": "taken",   # home received money from counterparty
                    "amount": round(recd_v, 2),
                })
    return home, txns


async def _upsert_loan_pairs(home: str, txns: list[dict], source: str, user: str):
    """Create/update mirror loan_entries pairs. Deterministic IDs = idempotent."""
    if not home or not txns:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    n_upserts = 0
    for t in txns:
        cp = t["counterparty"]
        date = t["date"]
        amount = t["amount"]
        direction = t["direction"]
        # Normalise ordering so that a given-taken pair has matching linked IDs.
        # If direction=given → home is GIVER, cp is TAKER
        # If direction=taken → cp is GIVER, home is TAKER
        giver, taker = (home, cp) if direction == "given" else (cp, home)
        # Key is sorted to dedupe regardless of which sheet originated the entry
        base_key = f"HIST-{giver}-{taker}-{date}-{int(round(amount))}"
        given_id = f"{base_key}-G"
        taken_id = f"{base_key}-T"
        
        given_doc = {
            "loan_id": given_id,
            "center": giver,
            "loan_type": "given",
            "source_center": taker,
            "linked_loan_id": taken_id,
            "amount": amount,
            "loan_date": date,
            "reason": "Historical inter-center transfer",
            "notes": f"Imported from {source}",
            "status": "partially_repaid",   # closing balance handled manually
            "total_repaid": 0,
            "repayments": [],
            "source": source,
            "updated_at": now,
            "updated_by": user,
        }
        taken_doc = {
            "loan_id": taken_id,
            "center": taker,
            "loan_type": "taken",
            "source_center": giver,
            "linked_loan_id": given_id,
            "amount": amount,
            "loan_date": date,
            "reason": "Historical inter-center transfer",
            "notes": f"Imported from {source}",
            "status": "partially_repaid",
            "total_repaid": 0,
            "repayments": [],
            "source": source,
            "updated_at": now,
            "updated_by": user,
        }
        await db.loan_entries.update_one(
            {"loan_id": given_id},
            {"$set": given_doc, "$setOnInsert": {"created_at": now, "created_by": user}},
            upsert=True,
        )
        await db.loan_entries.update_one(
            {"loan_id": taken_id},
            {"$set": taken_doc, "$setOnInsert": {"created_at": now, "created_by": user}},
            upsert=True,
        )
        n_upserts += 1
    return n_upserts


@router.post("/import-loans-file")
async def import_loans_file(file: UploadFile = File(...), token: str = Form(...)):
    """Upload the WC+Loans Excel. Parses every LOANS/LOAN sheet, extracts
    date-by-date transfers per counterparty column-group, and upserts mirror
    pairs in loan_entries (loan_type given/taken with linked_loan_id).
    Re-import is idempotent thanks to deterministic loan_id."""
    session = await get_session(token)
    if not session or not check_super_admin(session):
        raise HTTPException(403, "Only Super Admin can import historical data")
    
    user = session.get("managerName", "Admin")
    raw = await file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
    except Exception as exc:
        raise HTTPException(400, f"Could not read workbook: {exc}")
    
    summary = {
        "file": file.filename,
        "sheets_processed": 0,
        "sheets_skipped": [],
        "pairs_upserted": 0,
        "by_home_center": {},
    }
    for sn in wb.sheetnames:
        if "LOAN" not in sn.upper():
            continue
        ws = wb[sn]
        home, txns = _parse_loans_sheet(ws)
        if not home:
            summary["sheets_skipped"].append({"sheet": sn, "reason": "could not identify home center"})
            continue
        if not txns:
            summary["sheets_skipped"].append({"sheet": sn, "reason": "no parseable txns"})
            continue
        n = await _upsert_loan_pairs(home, txns, source=f"loans_import:{file.filename}:{sn}", user=user)
        summary["sheets_processed"] += 1
        summary["pairs_upserted"] += n
        summary["by_home_center"][home] = summary["by_home_center"].get(home, 0) + n
    
    logger.info(f"Historical Loans import by {user}: {summary}")
    return {"success": True, **summary}


@router.post("/loans-summary")
async def loans_summary(req: dict):
    """Per-center rollup of historically-imported loan_entries."""
    token = req.get("token")
    session = await get_session(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    rows = await db.loan_entries.find(
        {"loan_id": {"$regex": "^HIST-"}}, {"_id": 0}
    ).to_list(10000)
    by_center: dict = {}
    for r in rows:
        c = r.get("center", "")
        by_center.setdefault(c, {"center": c, "given": 0, "taken": 0, "count": 0})
        if r.get("loan_type") == "given":
            by_center[c]["given"] += float(r.get("amount", 0))
        else:
            by_center[c]["taken"] += float(r.get("amount", 0))
        by_center[c]["count"] += 1
    return {"centers": list(by_center.values()), "total_rows": len(rows)}


@router.post("/clear-loans")
async def clear_historical_loans(req: dict):
    """Delete all loan_entries originating from historical import. Super Admin only."""
    token = req.get("token")
    session = await get_session(token)
    if not session or not check_super_admin(session):
        raise HTTPException(403, "Only Super Admin can clear historical loans")
    home = req.get("center")
    q: dict = {"loan_id": {"$regex": "^HIST-"}}
    if home:
        q["center"] = home
    res = await db.loan_entries.delete_many(q)
    return {"success": True, "deleted": res.deleted_count}


@router.post("/clear")
async def clear_historical(req: dict):
    """Danger: wipe all historical_monthly_summary rows. Super Admin only."""
    token = req.get("token")
    session = await get_session(token)
    if not session or not check_super_admin(session):
        raise HTTPException(403, "Only Super Admin can clear historical data")
    center = req.get("center")
    if center:
        res = await db.historical_monthly_summary.delete_many({"center": center})
    else:
        res = await db.historical_monthly_summary.delete_many({})
    return {"success": True, "deleted": res.deleted_count}


# ============================================================
# MONTHLY FILE IMPORTER (Trial Balance + Daily Expenses + Daily Sales)
# ============================================================

def _parse_trial_balance_sheet(ws) -> dict:
    """Return {heads: {CATEGORY: amount}, total_sales: float}."""
    rows = list(ws.iter_rows(values_only=True))
    heads: dict[str, float] = {}
    total_sales = 0.0
    for row in rows:
        # pick first non-empty text cell as label
        label = None
        amount = None
        sales_amt = None
        for ci, v in enumerate(row):
            if v is None or v == "":
                continue
            if isinstance(v, str):
                s = v.strip()
                if not s:
                    continue
                if label is None:
                    label = s
                elif "SALES" in s.upper() or "RESTAURANT" in s.upper():
                    # next numeric is sales
                    for v2 in row[ci + 1:]:
                        if isinstance(v2, (int, float)) and v2 > 0:
                            sales_amt = float(v2)
                            break
            elif isinstance(v, (int, float)) and amount is None:
                amount = float(v)
        if sales_amt is not None:
            total_sales += sales_amt
        if label and amount is not None and amount > 0 and "SALES" not in label.upper() and "TOTAL" not in label.upper() and "PARTICULARS" not in label.upper() and "NARATION" not in label.upper():
            heads[label.upper()] = heads.get(label.upper(), 0) + amount
    return {"heads": heads, "total_sales": round(total_sales, 2)}


def _find_month_sheet(wb, target_month: str) -> Optional[str]:
    """Find a sheet whose name matches the target month (YYYY-MM)."""
    import re as _re
    try:
        year_full = int(target_month[:4])
        year_2d = year_full % 100
        month_num = int(target_month[5:7])
    except Exception:
        return None
    month_name = None
    for name, n in MONTH_NAMES.items():
        if n == month_num and len(name) <= 3:
            month_name = name
            break
    if not month_name:
        return None
    for sn in wb.sheetnames:
        up = sn.upper()
        tokens = set(_re.findall(r"[A-Z0-9]+", up))
        # Any form: "MARCH.26", "MAR 2026", "MAR.18", etc.
        if not any(t.startswith(month_name[:3]) for t in tokens):
            continue
        if str(year_2d) in tokens or str(year_full) in tokens:
            return sn
    return None


def _parse_daily_expense_sheet(ws) -> list[dict]:
    """Return list of {date, description, amount, category, payment_mode}."""
    rows = list(ws.iter_rows(values_only=True))
    out = []
    # Find header row containing DATE, EXPENCE, AMOUNT
    header_idx = None
    col_map = {}
    for ri, row in enumerate(rows[:12]):
        lowered = [str(c).strip().lower() if c else "" for c in row]
        if any("date" == v for v in lowered) and any("expen" in v for v in lowered) and any("amount" in v for v in lowered):
            header_idx = ri
            for ci, v in enumerate(lowered):
                if v == "date":
                    col_map["date"] = ci
                elif "expen" in v and "type" not in v:
                    col_map["desc"] = ci
                elif v == "amount":
                    col_map["amount"] = ci
                elif "expanse type" in v or "expense type" in v or "category" in v:
                    col_map["category"] = ci
                elif "payment" in v or "cash" == v:
                    col_map.setdefault("payment", ci)
            break
    if header_idx is None or "date" not in col_map:
        return []
    for row in rows[header_idx + 1:]:
        try:
            d = row[col_map["date"]]
            if not isinstance(d, datetime):
                continue
            desc = row[col_map.get("desc", -1)] if col_map.get("desc") is not None else ""
            amt = row[col_map.get("amount", -1)] if col_map.get("amount") is not None else None
            cat = row[col_map.get("category", -1)] if col_map.get("category") is not None else ""
            pay = row[col_map.get("payment", -1)] if col_map.get("payment") is not None else ""
            if not isinstance(amt, (int, float)) or amt <= 0:
                continue
            out.append({
                "date": d.strftime("%Y-%m-%d"),
                "description": (str(desc) if desc else "").strip(),
                "category": (str(cat) if cat else "").strip().upper(),
                "amount": float(amt),
                "payment_mode": (str(pay) if pay else "CASH").strip().upper(),
            })
        except Exception:
            continue
    return out


def _parse_pib_sheet(ws) -> dict:
    """Parse PIB sheet → {platforms: {swiggy/zomato/card: {gross, commission}},
    revenue_share, sgst, cgst, total_gst, gross_for_revenue, net_sale_for_revenue}.
    Works by scanning DESCRIPTION column for keywords."""
    rows = list(ws.iter_rows(values_only=True))
    platforms: dict = {}
    revenue_share = None
    sgst = None
    cgst = None
    gross_for_revenue = None
    net_sale_for_revenue = None
    gst_paid = None
    
    for row in rows:
        # Find the first text cell (description) and collect all numeric cells
        label = None
        nums = []
        for v in row:
            if v is None or v == "":
                continue
            if isinstance(v, str):
                s = v.strip()
                if s and label is None:
                    label = s.upper()
            elif isinstance(v, (int, float)):
                nums.append(float(v))
        if not label or not nums:
            continue
        
        def _pick_sale_commission():
            """Return (gross, commission_abs). Commission is the negative value
            (or last value if all positive, when labelled). Gross is the largest
            non-negative numeric excluding small SL.NO-looking integers."""
            neg = [n for n in nums if n < 0]
            # Non-negative candidates, excluding tiny serial-number-looking values
            positives = [n for n in nums if n >= 0 and n > 100]
            gross = max(positives) if positives else 0
            if neg:
                commission = abs(min(neg))
            else:
                # All positive — commission often sits after the gross
                # Pick the smaller positive (if there are 2+) as commission
                others = [n for n in positives if n != gross]
                commission = min(others) if others else 0
            return gross, commission
        
        if "SWIGGY" in label and "SALE" in label:
            g, c = _pick_sale_commission()
            platforms["swiggy"] = {"gross": g, "commission": c}
        elif "ZOMATO" in label and "SALE" in label:
            g, c = _pick_sale_commission()
            platforms["zomato"] = {"gross": g, "commission": c}
        elif "CARD" in label and "SALE" in label:
            g, c = _pick_sale_commission()
            platforms["card"] = {"gross": g, "commission": c}
        elif "PHONE" in label and ("PE" in label or "PAY" in label):
            g, c = _pick_sale_commission()
            platforms["phonepe"] = {"gross": g, "commission": c}
        elif "REVENUE SHARE" in label:
            revenue_share = nums[-1]
        elif ("S.GST" in label or "SGST" in label) and "CGST" not in label:
            sgst = nums[-1]
        elif "C.GST" in label or "CGST" in label:
            cgst = nums[-1]
        elif "GROSS SALE FOR REVENUE" in label:
            gross_for_revenue = nums[-1]
        elif "NET SALE CONSIDER" in label and "REVENUE" in label:
            net_sale_for_revenue = nums[-1]
        elif "GST PAID" in label and "REVENUE" not in label:
            gst_paid = nums[-1]
    
    total_gst = (sgst or 0) + (cgst or 0)
    return {
        "platforms": platforms,
        "revenue_share": revenue_share,
        "sgst": sgst,
        "cgst": cgst,
        "total_gst_on_revenue": total_gst,
        "gst_paid": gst_paid,
        "gross_for_revenue": gross_for_revenue,
        "net_sale_for_revenue": net_sale_for_revenue,
    }


def _parse_daily_sales_from_sheets(wb, month: str) -> dict:
    """Aggregate daily sales from CASH SALE + PHONE PE + CARD + SW + ZM sheets.
    Returns {YYYY-MM-DD: {cash, online, card, swiggy, zomato, total}}."""
    days: dict[str, dict] = {}
    
    def _rows(sname: str):
        if sname not in wb.sheetnames:
            return []
        return list(wb[sname].iter_rows(values_only=True))
    
    def _extract(sn: str, value_col_keywords: tuple):
        rows = _rows(sn)
        out = {}
        header_idx = None
        date_ci = None
        val_ci = None
        for ri, row in enumerate(rows[:6]):
            lowered = [str(c).strip().lower() if c else "" for c in row]
            if "date" in lowered:
                header_idx = ri
                date_ci = lowered.index("date")
                for ci, v in enumerate(lowered):
                    for kw in value_col_keywords:
                        if kw in v:
                            val_ci = ci
                            break
                    if val_ci is not None:
                        break
                break
        if header_idx is None or date_ci is None:
            return out
        if val_ci is None:
            val_ci = date_ci + 1
        for row in rows[header_idx + 1:]:
            try:
                d = row[date_ci]
                v = row[val_ci] if val_ci < len(row) else None
                if isinstance(d, datetime) and isinstance(v, (int, float)):
                    out[d.strftime("%Y-%m-%d")] = float(v)
            except Exception:
                continue
        return out
    
    cash_map = _extract("CASH SALE", ("cash sale", "cash"))
    pp_map = _extract("PHONE PE", ("pp sale", "as per data"))
    card_map = _extract("CARD", ("card",))
    sw_map = _extract("SW", ("swiggy",))
    zm_map = _extract("ZM", ("zomato",))
    
    all_dates = set(cash_map) | set(pp_map) | set(card_map) | set(sw_map) | set(zm_map)
    for d in all_dates:
        cash = cash_map.get(d, 0)
        pp = pp_map.get(d, 0)
        card = card_map.get(d, 0)
        sw = sw_map.get(d, 0)
        zm = zm_map.get(d, 0)
        online = pp + card + sw + zm
        days[d] = {
            "cash": round(cash, 2),
            "online": round(online, 2),
            "phone_pe": round(pp, 2),
            "card": round(card, 2),
            "swiggy": round(sw, 2),
            "zomato": round(zm, 2),
            "total": round(cash + online, 2),
        }
    return days




    """Aggregate daily sales from CASH SALE + PHONE PE + CARD + SW + ZM sheets.
    Returns {YYYY-MM-DD: {cash, online, card, swiggy, zomato, total}}."""
    days: dict[str, dict] = {}
    
    def _rows(sname: str):
        if sname not in wb.sheetnames:
            return []
        return list(wb[sname].iter_rows(values_only=True))
    
    def _extract(sn: str, value_col_keywords: tuple):
        """Find 2nd numeric after DATE column; returns dict {date: value}."""
        rows = _rows(sn)
        out = {}
        header_idx = None
        date_ci = None
        val_ci = None
        for ri, row in enumerate(rows[:6]):
            lowered = [str(c).strip().lower() if c else "" for c in row]
            if "date" in lowered:
                header_idx = ri
                date_ci = lowered.index("date")
                for ci, v in enumerate(lowered):
                    for kw in value_col_keywords:
                        if kw in v:
                            val_ci = ci
                            break
                    if val_ci is not None:
                        break
                break
        if header_idx is None or date_ci is None:
            return out
        if val_ci is None:
            # Default: first numeric column after DATE
            val_ci = date_ci + 1
        for row in rows[header_idx + 1:]:
            try:
                d = row[date_ci]
                v = row[val_ci] if val_ci < len(row) else None
                if isinstance(d, datetime) and isinstance(v, (int, float)):
                    out[d.strftime("%Y-%m-%d")] = float(v)
            except Exception:
                continue
        return out
    
    cash_map = _extract("CASH SALE", ("cash sale", "cash"))
    pp_map = _extract("PHONE PE", ("pp sale", "as per data"))
    card_map = _extract("CARD", ("card",))
    sw_map = _extract("SW", ("swiggy",))
    zm_map = _extract("ZM", ("zomato",))
    
    all_dates = set(cash_map) | set(pp_map) | set(card_map) | set(sw_map) | set(zm_map)
    for d in all_dates:
        cash = cash_map.get(d, 0)
        pp = pp_map.get(d, 0)
        card = card_map.get(d, 0)
        sw = sw_map.get(d, 0)
        zm = zm_map.get(d, 0)
        online = pp + card + sw + zm
        days[d] = {
            "cash": round(cash, 2),
            "online": round(online, 2),
            "phone_pe": round(pp, 2),
            "card": round(card, 2),
            "swiggy": round(sw, 2),
            "zomato": round(zm, 2),
            "total": round(cash + online, 2),
        }
    return days


@router.post("/import-monthly-file")
async def import_monthly_file(
    file: UploadFile = File(...),
    token: str = Form(...),
    center_override: Optional[str] = Form(None),
    month_override: Optional[str] = Form(None),
):
    """Upload a single monthly Excel (e.g. 'EXPENCE SHEET -HSR- MARCH. 2026.xlsx').
    Parses 4 data sources and ingests them:
      - TRIAL BAL. → historical_trial_balance (head-wise rollup)
      - Daily expense sheet (MARCH.26 etc.) → db.expenses rows (historical source)
      - CASH SALE + PHONE PE + CARD + SW + ZM → db.daily_sales (1 doc per date)
      - PIB → ingested into historical_pib collection for future reporting
    
    Center & month auto-detected from filename; override with form fields."""
    session = await get_session(token)
    if not session or not check_super_admin(session):
        raise HTTPException(403, "Only Super Admin can import historical data")
    
    user = session.get("managerName", "Admin")
    raw = await file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
    except Exception as exc:
        raise HTTPException(400, f"Could not read workbook: {exc}")
    
    center = (center_override or _detect_center_from_filename(file.filename or "")) or ""
    month = month_override or _detect_month_from_filename(file.filename or "") or ""
    if not center:
        raise HTTPException(400, "Could not detect center from filename — pass center_override.")
    if not month:
        raise HTTPException(400, "Could not detect month from filename — pass month_override (YYYY-MM).")
    
    now = datetime.now(timezone.utc).isoformat()
    result: dict = {
        "file": file.filename, "center": center, "month": month,
        "trial_balance": {"heads": 0, "total_expenses": 0, "total_sales": 0},
        "expenses": {"rows": 0},
        "daily_sales": {"days": 0, "total_sales": 0},
    }
    
    # 1. TRIAL BAL.
    tb_sheet = None
    for sn in wb.sheetnames:
        if "TRIAL" in sn.upper() and "BAL" in sn.upper():
            tb_sheet = sn
            break
    if tb_sheet:
        tb = _parse_trial_balance_sheet(wb[tb_sheet])
        if tb["heads"]:
            total_exp = round(sum(tb["heads"].values()), 2)
            doc = {
                "center": center, "month": month,
                "heads": tb["heads"], "total_expenses": total_exp,
                "total_sales": tb["total_sales"],
                "source": f"monthly_import:{file.filename}",
                "updated_at": now, "updated_by": user,
            }
            await db.historical_trial_balance.update_one(
                {"center": center, "month": month},
                {"$set": doc, "$setOnInsert": {"created_at": now, "created_by": user}},
                upsert=True,
            )
            result["trial_balance"] = {"heads": len(tb["heads"]), "total_expenses": total_exp, "total_sales": tb["total_sales"]}
    
    # 2. Daily expenses (month sheet)
    month_sheet = _find_month_sheet(wb, month)
    expenses_rows = 0
    if month_sheet:
        exps = _parse_daily_expense_sheet(wb[month_sheet])
        # Delete prior historical expenses for this center+month to keep re-imports clean
        await db.expenses.delete_many({
            "center": center, "date": {"$regex": f"^{month}"},
            "source": {"$regex": "^monthly_import:"},
        })
        for i, e in enumerate(exps):
            await db.expenses.insert_one({
                "center": center, "date": e["date"],
                "expense_type": e["category"] or "OTHER",
                "description": e["description"] or "",
                "amount": e["amount"],
                "payment_mode": e["payment_mode"] or "CASH",
                "source": f"monthly_import:{file.filename}",
                "historical_id": f"HIST-EXP-{center}-{month}-{i:04d}",
                "created_by": user, "created_at": now, "updated_at": now,
            })
            expenses_rows += 1
        result["expenses"] = {"rows": expenses_rows}
    
    # 3. Daily sales (cash + online from 5 sheets)
    daily = _parse_daily_sales_from_sheets(wb, month)
    total_sales_sum = 0
    # Clean prior monthly-import docs for this center+month so we can upsert
    # without tripping the existing unique {center,date} index. Live daily_sales
    # rows (created by operators) will block the insert — that's intentional
    # so we never silently overwrite real data.
    await db.daily_sales.delete_many({
        "center": center, "date": {"$regex": f"^{month}"},
        "source": {"$regex": "^monthly_import:"},
    })
    skipped_live = 0
    for d, v in daily.items():
        existing = await db.daily_sales.find_one({"center": center, "date": d}, {"_id": 0, "source": 1})
        if existing and not str(existing.get("source", "")).startswith("monthly_import:"):
            skipped_live += 1
            continue
        await db.daily_sales.update_one(
            {"center": center, "date": d},
            {"$set": {
                "center": center, "date": d,
                "total_cash_sale": v["cash"],
                "total_online_sale": v["online"],
                "total_sale": v["total"],
                "phone_pe_sale": v["phone_pe"],
                "card_sale": v["card"],
                "swiggy_sale": v["swiggy"],
                "zomato_sale": v["zomato"],
                "source": f"monthly_import:{file.filename}",
                "updated_at": now, "updated_by": user,
            }, "$setOnInsert": {"created_at": now, "created_by": user}},
            upsert=True,
        )
        total_sales_sum += v["total"]
    result["daily_sales"] = {"days": len(daily), "total_sales": round(total_sales_sum, 2), "skipped_live_days": skipped_live}
    
    # 4. PIB sheet — commissions per platform + revenue share + GST
    pib_sheet = None
    for sn in wb.sheetnames:
        if sn.upper().strip() == "PIB":
            pib_sheet = sn
            break
    pib_data = None
    commissions_created = 0
    if pib_sheet:
        pib_data = _parse_pib_sheet(wb[pib_sheet])
        # Upsert one monthly_commissions row per platform
        import uuid as _uuid
        for plat, v in pib_data["platforms"].items():
            comm_id_key = f"HIST-{center}-{month}-{plat.upper()}"
            doc = {
                "commission_id": comm_id_key,
                "center": center,
                "month": month,
                "platform": plat,
                "original_filename": file.filename,
                "gross_amount": round(v["gross"], 2),
                "gst_tax_deductions": 0,
                "other_deductions": round(v["commission"], 2),   # commission treated as deduction
                "sundry_debtors": 0,
                "tds": 0,
                "net_payout": round(v["gross"] - v["commission"], 2),
                "order_count": 0,
                "currency": "INR",
                "raw_summary": {"source": "pib", "commission": v["commission"]},
                "uploaded_by": user,
                "upload_date": now,
                "source": f"monthly_import:{file.filename}",
            }
            await db.monthly_commissions.update_one(
                {"commission_id": comm_id_key},
                {"$set": doc, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
            commissions_created += 1
        # Also upsert a rollup doc (revenue share, GST) into historical_pib collection
        if pib_data.get("revenue_share") is not None:
            await db.historical_pib.update_one(
                {"center": center, "month": month},
                {"$set": {
                    "center": center, "month": month,
                    "revenue_share": pib_data.get("revenue_share"),
                    "sgst": pib_data.get("sgst"),
                    "cgst": pib_data.get("cgst"),
                    "total_gst_on_revenue": pib_data.get("total_gst_on_revenue"),
                    "gst_paid": pib_data.get("gst_paid"),
                    "gross_for_revenue": pib_data.get("gross_for_revenue"),
                    "net_sale_for_revenue": pib_data.get("net_sale_for_revenue"),
                    "source": f"monthly_import:{file.filename}",
                    "updated_at": now, "updated_by": user,
                }, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
    result["commissions"] = {
        "rows": commissions_created,
        "platforms": list((pib_data or {}).get("platforms", {}).keys()),
        "revenue_share": (pib_data or {}).get("revenue_share"),
        "total_gst_on_revenue": (pib_data or {}).get("total_gst_on_revenue"),
    }
    
    logger.info(f"Monthly import {file.filename} → {center} {month}: {result}")
    return {"success": True, **result}


@router.post("/monthly-summary")
async def monthly_summary(req: dict):
    """Rollup of imported monthly files: trial_balance + daily sales + expense row counts."""
    token = req.get("token")
    session = await get_session(token)
    if not session:
        raise HTTPException(401, "Invalid token")
    
    tb = await db.historical_trial_balance.find({}, {"_id": 0}).to_list(5000)
    by = {}
    for r in tb:
        key = r["center"]
        by.setdefault(key, {"center": key, "months": [], "total_expenses": 0, "total_sales": 0})
        by[key]["months"].append(r["month"])
        by[key]["total_expenses"] += r.get("total_expenses", 0)
        by[key]["total_sales"] += r.get("total_sales", 0)
    for v in by.values():
        v["months"].sort()
        v["months_count"] = len(v["months"])
        v["earliest"] = v["months"][0] if v["months"] else ""
        v["latest"] = v["months"][-1] if v["months"] else ""
    
    return {"centers": list(by.values()), "total_files": len(tb)}


@router.post("/clear-monthly")
async def clear_monthly_imports(req: dict):
    """Wipe monthly-import expenses + sales + trial balance for a center/month.
    Super Admin only. If center+month not given, wipes ALL monthly imports."""
    token = req.get("token")
    session = await get_session(token)
    if not session or not check_super_admin(session):
        raise HTTPException(403, "Only Super Admin can clear historical data")
    
    center = req.get("center")
    month = req.get("month")
    
    exp_q = {"source": {"$regex": "^monthly_import:"}}
    sal_q = {"source": {"$regex": "^monthly_import:"}}
    tb_q: dict = {}
    if center:
        exp_q["center"] = center
        sal_q["center"] = center
        tb_q["center"] = center
    if month:
        exp_q["date"] = {"$regex": f"^{month}"}
        sal_q["date"] = {"$regex": f"^{month}"}
        tb_q["month"] = month
    
    exp_del = await db.expenses.delete_many(exp_q)
    sal_del = await db.daily_sales.delete_many(sal_q)
    tb_del = await db.historical_trial_balance.delete_many(tb_q)
    
    # Commissions & PIB
    comm_q: dict = {"source": {"$regex": "^monthly_import:"}}
    pib_q: dict = {"source": {"$regex": "^monthly_import:"}}
    if center:
        comm_q["center"] = center
        pib_q["center"] = center
    if month:
        comm_q["month"] = month
        pib_q["month"] = month
    comm_del = await db.monthly_commissions.delete_many(comm_q)
    pib_del = await db.historical_pib.delete_many(pib_q)
    
    return {
        "success": True,
        "expenses_deleted": exp_del.deleted_count,
        "sales_deleted": sal_del.deleted_count,
        "trial_balance_deleted": tb_del.deleted_count,
        "commissions_deleted": comm_del.deleted_count,
        "pib_deleted": pib_del.deleted_count,
    }

