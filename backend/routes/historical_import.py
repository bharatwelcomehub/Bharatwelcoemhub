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

