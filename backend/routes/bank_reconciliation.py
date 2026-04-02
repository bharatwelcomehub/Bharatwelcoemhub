"""
Bank Statement vs Expense Reconciliation Module
- Parses bank statements (Excel/CSV)
- Matches against recorded expenses
- Identifies unrecorded (missing) expenses
- Suggests categories from Category Master
- Maintains full audit trail
"""

from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import logging
import io
import csv
import re
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bank-reconciliation", tags=["Bank Reconciliation"])
db = None

def init_db(database):
    global db
    db = database


# ── Models ──────────────────────────────────────────────────────────────

class ReconcileRequest(BaseModel):
    upload_id: str
    token: str

class AddExpenseRequest(BaseModel):
    transaction_id: str
    upload_id: str
    expense_type: str
    payment_mode: str
    description: Optional[str] = None
    token: str

class IgnoreRequest(BaseModel):
    transaction_id: str
    upload_id: str
    reason: Optional[str] = ""
    token: str

class ExportRequest(BaseModel):
    upload_id: str
    token: str


# ── Auth helper ─────────────────────────────────────────────────────────

async def _get_session(token: str):
    if not token:
        return None
    session = await db.sessions.find_one({"token": token})
    return session


# ── Category Suggestion Logic ───────────────────────────────────────────

KEYWORD_MAP = {
    "RENT": ["RENT PAID SHOP", "STAFF ROOM RENT"],
    "SHOP RENT": ["RENT PAID SHOP"],
    "ROOM RENT": ["STAFF ROOM RENT"],
    "ELECTRICITY": ["ELECTRICITY"],
    "ELECTRIC": ["ELECTRICITY"],
    "UTILITY": ["ELECTRICITY"],
    "WATER": ["WATER CAN / BOTTLE"],
    "FUEL": ["FUEL / TRANSPORT"],
    "PETROL": ["FUEL / TRANSPORT"],
    "DIESEL": ["FUEL / TRANSPORT"],
    "TRANSPORT": ["FUEL / TRANSPORT"],
    "BANK CHARGE": ["BANK CHARGES"],
    "BANK FEE": ["BANK CHARGES"],
    "SERVICE CHARGE": ["BANK CHARGES"],
    "SALARY": ["SALARY / WAGES"],
    "WAGES": ["SALARY / WAGES"],
    "STAFF": ["SALARY / WAGES"],
    "NEFT": ["SALARY / WAGES"],
    "GROCERY": ["GROCERY"],
    "VEGETABLE": ["FRUITS & VEGETABLE"],
    "FRUIT": ["FRUITS & VEGETABLE"],
    "MILK": ["DAIRY PRODUCTS"],
    "DAIRY": ["DAIRY PRODUCTS"],
    "PANEER": ["DAIRY PRODUCTS"],
    "CURD": ["DAIRY PRODUCTS"],
    "GAS": ["CYLINDER"],
    "CYLINDER": ["CYLINDER"],
    "LPG": ["CYLINDER"],
    "OIL": ["OIL"],
    "SWIGGY": ["AGGREGATOR COMMISSION"],
    "ZOMATO": ["AGGREGATOR COMMISSION"],
    "DOORDASH": ["AGGREGATOR COMMISSION"],
    "REPAIR": ["REPAIR & MAINTENANCE"],
    "MAINTENANCE": ["REPAIR & MAINTENANCE"],
    "PLUMBER": ["REPAIR & MAINTENANCE"],
    "INSURANCE": ["INSURANCE"],
    "EMI": ["EMI / LOAN INSTALMENT"],
    "LOAN": ["EMI / LOAN INSTALMENT"],
    "TDS": ["TDS PAID ON RENT PAID"],
    "TAX": ["TDS PAID ON RENT PAID"],
    "GST": ["GST PAYMENT"],
    "MOBILE": ["MOBILE RECHARGE"],
    "RECHARGE": ["MOBILE RECHARGE"],
    "STATIONERY": ["STATIONERY / PRINTING"],
    "PRINTING": ["STATIONERY / PRINTING"],
    "MISCELLANEOUS": ["MISCELLANEOUS"],
}


async def suggest_category(narration: str) -> Optional[str]:
    """Suggest expense category based on narration keywords matching Category Master"""
    if not narration:
        return None

    narration_upper = narration.upper()

    # Load active categories from master
    heads = await db.expense_heads.find({"is_active": {"$ne": False}}, {"_id": 0, "name": 1}).to_list(100)
    master_categories = {h["name"].upper(): h["name"] for h in heads}

    # Direct match with category name
    for cat_upper, cat_name in master_categories.items():
        if cat_upper in narration_upper:
            return cat_name

    # Keyword-based matching
    for keyword, candidates in KEYWORD_MAP.items():
        if keyword in narration_upper:
            for candidate in candidates:
                if candidate.upper() in master_categories:
                    return master_categories[candidate.upper()]

    return None


# ── Bank Statement Parser ───────────────────────────────────────────────

def parse_amount(val):
    """Parse amount string to float, handling commas and currency symbols"""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "").replace("₹", "").replace("$", "").replace("INR", "").strip()
    if not s or s == "-" or s.lower() == "nan":
        return 0.0
    try:
        return abs(float(s))
    except ValueError:
        return 0.0


def parse_date(val):
    """Parse date from various formats"""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
        "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y",
        "%Y/%m/%d", "%d.%m.%Y", "%m-%d-%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def detect_columns(headers):
    """Auto-detect column mappings from headers"""
    mapping = {"date": None, "narration": None, "debit": None, "credit": None, "reference": None, "balance": None}

    headers_upper = [str(h).upper().strip() for h in headers]

    date_keywords = ["DATE", "TXN DATE", "TRANSACTION DATE", "VALUE DATE", "POSTING DATE"]
    narr_keywords = ["NARRATION", "DESCRIPTION", "PARTICULARS", "REMARKS", "DETAILS", "TRANSACTION DETAILS"]
    debit_keywords = ["DEBIT", "WITHDRAWAL", "DR", "DEBIT AMOUNT", "WITHDRAWALS"]
    credit_keywords = ["CREDIT", "DEPOSIT", "CR", "CREDIT AMOUNT", "DEPOSITS"]
    ref_keywords = ["REFERENCE", "REF NO", "CHQ NO", "CHEQUE NO", "UTR", "REFERENCE NO"]
    bal_keywords = ["BALANCE", "CLOSING BALANCE", "RUNNING BALANCE"]

    for i, h in enumerate(headers_upper):
        if not mapping["date"] and any(k in h for k in date_keywords):
            mapping["date"] = i
        elif not mapping["narration"] and any(k in h for k in narr_keywords):
            mapping["narration"] = i
        elif not mapping["debit"] and any(k in h for k in debit_keywords):
            mapping["debit"] = i
        elif not mapping["credit"] and any(k in h for k in credit_keywords):
            mapping["credit"] = i
        elif not mapping["reference"] and any(k in h for k in ref_keywords):
            mapping["reference"] = i
        elif not mapping["balance"] and any(k in h for k in bal_keywords):
            mapping["balance"] = i

    return mapping


async def parse_bank_statement(file_content: bytes, filename: str):
    """Parse bank statement from Excel or CSV"""
    transactions = []

    if filename.lower().endswith((".xlsx", ".xls")):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True, data_only=True)
        ws = wb.active

        rows = []
        for row in ws.iter_rows(values_only=True):
            rows.append(list(row))
        wb.close()

        if len(rows) < 2:
            return transactions

        # Find header row (first row with date-like header)
        header_idx = 0
        for i, row in enumerate(rows[:10]):
            row_str = " ".join(str(c).upper() for c in row if c)
            if any(k in row_str for k in ["DATE", "NARRATION", "DESCRIPTION", "DEBIT", "WITHDRAWAL"]):
                header_idx = i
                break

        headers = rows[header_idx]
        mapping = detect_columns(headers)
        data_rows = rows[header_idx + 1:]

    elif filename.lower().endswith(".csv"):
        text = file_content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        if len(rows) < 2:
            return transactions

        header_idx = 0
        for i, row in enumerate(rows[:10]):
            row_str = " ".join(str(c).upper() for c in row if c)
            if any(k in row_str for k in ["DATE", "NARRATION", "DESCRIPTION", "DEBIT", "WITHDRAWAL"]):
                header_idx = i
                break

        headers = rows[header_idx]
        mapping = detect_columns(headers)
        data_rows = rows[header_idx + 1:]
    else:
        return transactions

    if mapping["date"] is None or (mapping["debit"] is None and mapping["credit"] is None):
        return transactions

    for row in data_rows:
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue

        try:
            date_val = row[mapping["date"]] if mapping["date"] is not None and mapping["date"] < len(row) else None
            narr_val = row[mapping["narration"]] if mapping["narration"] is not None and mapping["narration"] < len(row) else ""
            debit_val = row[mapping["debit"]] if mapping["debit"] is not None and mapping["debit"] < len(row) else 0
            credit_val = row[mapping["credit"]] if mapping["credit"] is not None and mapping["credit"] < len(row) else 0
            ref_val = row[mapping["reference"]] if mapping["reference"] is not None and mapping["reference"] < len(row) else ""
            bal_val = row[mapping["balance"]] if mapping["balance"] is not None and mapping["balance"] < len(row) else None

            parsed_date = parse_date(date_val)
            if not parsed_date:
                continue

            debit_amount = parse_amount(debit_val)
            credit_amount = parse_amount(credit_val)

            # Skip credit-only transactions (deposits)
            if debit_amount == 0 and credit_amount > 0:
                continue
            # Skip zero-amount rows
            if debit_amount == 0 and credit_amount == 0:
                continue

            transactions.append({
                "transaction_id": str(uuid.uuid4())[:12],
                "transaction_date": parsed_date,
                "narration": str(narr_val or "").strip(),
                "debit_amount": debit_amount,
                "credit_amount": credit_amount,
                "reference_number": str(ref_val or "").strip(),
                "balance": parse_amount(bal_val) if bal_val else None,
            })
        except (IndexError, TypeError):
            continue

    return transactions


# ── Matching Logic ──────────────────────────────────────────────────────

async def match_transactions(transactions: list, center: str, month: str):
    """Match bank transactions against recorded expenses"""
    # Parse month to get date range
    try:
        year, mon = month.split("-")
        start_date = f"{year}-{mon}-01"
        if int(mon) == 12:
            end_date = f"{int(year) + 1}-01-01"
        else:
            end_date = f"{year}-{int(mon) + 1:02d}-01"
    except Exception:
        return transactions

    # Load recorded expenses for the month/center
    expenses = await db.expenses.find({
        "center": center,
        "date": {"$gte": start_date, "$lt": end_date}
    }, {"_id": 0}).to_list(5000)

    # Build expense lookup: (date, amount) -> list of expenses
    expense_lookup = {}
    for exp in expenses:
        key = (exp.get("date", ""), round(exp.get("amount", 0), 2))
        if key not in expense_lookup:
            expense_lookup[key] = []
        expense_lookup[key].append(exp)

    # Also build amount-only lookup for fuzzy date matching
    amount_lookup = {}
    for exp in expenses:
        amt = round(exp.get("amount", 0), 2)
        if amt not in amount_lookup:
            amount_lookup[amt] = []
        amount_lookup[amt].append(exp)

    matched = []
    unrecorded = []

    for txn in transactions:
        txn_date = txn["transaction_date"]
        txn_amount = round(txn["debit_amount"], 2)
        found_match = False

        # Primary match: exact date + exact amount
        key = (txn_date, txn_amount)
        if key in expense_lookup and expense_lookup[key]:
            matched_exp = expense_lookup[key].pop(0)
            txn["match_status"] = "matched"
            txn["matched_expense"] = {
                "description": matched_exp.get("description", ""),
                "expense_type": matched_exp.get("expense_type", ""),
                "payment_mode": matched_exp.get("payment_mode", ""),
                "date": matched_exp.get("date", ""),
                "amount": matched_exp.get("amount", 0),
            }
            txn["match_method"] = "exact_date_amount"
            matched.append(txn)
            found_match = True
            continue

        # Secondary match: fuzzy date (+-2 days) + exact amount
        if not found_match and txn_amount in amount_lookup:
            try:
                txn_dt = datetime.strptime(txn_date, "%Y-%m-%d")
                for exp in amount_lookup[txn_amount]:
                    exp_date = exp.get("date", "")
                    try:
                        exp_dt = datetime.strptime(exp_date, "%Y-%m-%d")
                        if abs((txn_dt - exp_dt).days) <= 2:
                            txn["match_status"] = "matched"
                            txn["matched_expense"] = {
                                "description": exp.get("description", ""),
                                "expense_type": exp.get("expense_type", ""),
                                "payment_mode": exp.get("payment_mode", ""),
                                "date": exp.get("date", ""),
                                "amount": exp.get("amount", 0),
                            }
                            txn["match_method"] = "fuzzy_date_exact_amount"
                            matched.append(txn)
                            amount_lookup[txn_amount].remove(exp)
                            found_match = True
                            break
                    except ValueError:
                        continue
            except ValueError:
                pass

        if not found_match:
            txn["match_status"] = "unrecorded"
            txn["matched_expense"] = None
            txn["match_method"] = None
            unrecorded.append(txn)

    return matched, unrecorded


# ── API Endpoints ───────────────────────────────────────────────────────

@router.post("/upload")
async def upload_bank_statement(
    file: UploadFile = File(...),
    center: str = Form(...),
    month: str = Form(...),
    bank_account: str = Form(""),
    token: str = Form(...),
):
    """Upload and parse a bank statement, then run reconciliation"""
    session = await _get_session(token)
    if not session:
        return {"detail": "Authentication required"}

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        return {"detail": "File too large (max 10MB)"}

    # Parse bank statement
    transactions = await parse_bank_statement(content, file.filename)
    if not transactions:
        return {"detail": "Could not parse any transactions from the file. Ensure it has Date, Narration, and Debit columns."}

    # Run matching
    matched, unrecorded = await match_transactions(transactions, center, month)

    # Suggest categories for unrecorded transactions
    for txn in unrecorded:
        txn["suggested_category"] = await suggest_category(txn.get("narration", ""))

    # Create upload record
    upload_id = str(uuid.uuid4())[:16]
    upload_record = {
        "upload_id": upload_id,
        "filename": file.filename,
        "center": center,
        "month": month,
        "bank_account": bank_account,
        "total_transactions": len(transactions),
        "total_debit": round(sum(t["debit_amount"] for t in transactions), 2),
        "matched_count": len(matched),
        "unrecorded_count": len(unrecorded),
        "uploaded_by": session.get("name", session.get("mobile", "Unknown")),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "status": "reconciled",
    }
    await db.bank_statement_uploads.insert_one(upload_record)

    # Store transactions
    for txn in matched + unrecorded:
        txn["upload_id"] = upload_id
        txn["center"] = center
        txn["month"] = month
    if matched + unrecorded:
        await db.bank_transactions.insert_many(
            [{k: v for k, v in t.items()} for t in matched + unrecorded]
        )

    # Reconciliation log
    await db.expense_reconciliation_log.insert_one({
        "upload_id": upload_id,
        "action": "upload_and_reconcile",
        "center": center,
        "month": month,
        "matched_count": len(matched),
        "unrecorded_count": len(unrecorded),
        "action_taken_by": session.get("name", session.get("mobile", "")),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Calculate summary
    total_bank_debit = round(sum(t["debit_amount"] for t in transactions), 2)
    total_matched = round(sum(t["debit_amount"] for t in matched), 2)
    total_unrecorded = round(sum(t["debit_amount"] for t in unrecorded), 2)

    # Load expense total for comparison
    try:
        year, mon = month.split("-")
        start_date = f"{year}-{mon}-01"
        end_date = f"{year}-{int(mon) + 1:02d}-01" if int(mon) < 12 else f"{int(year) + 1}-01-01"
        pipeline = [
            {"$match": {"center": center, "date": {"$gte": start_date, "$lt": end_date}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}}
        ]
        agg = await db.expenses.aggregate(pipeline).to_list(1)
        recorded_total = round(agg[0]["total"], 2) if agg else 0
        recorded_count = agg[0]["count"] if agg else 0
    except Exception:
        recorded_total = 0
        recorded_count = 0

    return {
        "success": True,
        "upload_id": upload_id,
        "summary": {
            "total_bank_debits": total_bank_debit,
            "total_expenses_recorded": recorded_total,
            "total_bank_transactions": len(transactions),
            "recorded_expense_count": recorded_count,
            "matched_count": len(matched),
            "matched_amount": total_matched,
            "unrecorded_count": len(unrecorded),
            "unrecorded_amount": total_unrecorded,
        },
        "matched": [{k: v for k, v in t.items() if k != "_id"} for t in matched],
        "unrecorded": [{k: v for k, v in t.items() if k != "_id"} for t in unrecorded],
    }


@router.post("/add-expense")
async def add_expense_from_reconciliation(req: AddExpenseRequest):
    """Add an unrecorded bank transaction as an expense"""
    session = await _get_session(req.token)
    if not session:
        return {"detail": "Authentication required"}

    # Find the transaction
    txn = await db.bank_transactions.find_one(
        {"transaction_id": req.transaction_id, "upload_id": req.upload_id},
        {"_id": 0}
    )
    if not txn:
        return {"detail": "Transaction not found"}
    if txn.get("match_status") == "added":
        return {"detail": "Transaction already added as expense"}

    # Validate category exists in master
    cat_exists = await db.expense_heads.find_one({"name": req.expense_type, "is_active": {"$ne": False}})
    if not cat_exists:
        return {"detail": f"Category '{req.expense_type}' not found in Category Master"}

    # Create expense record
    expense_id = str(uuid.uuid4())[:16]
    expense = {
        "expense_id": expense_id,
        "center": txn["center"],
        "date": txn["transaction_date"],
        "description": req.description or txn.get("narration", ""),
        "amount": txn["debit_amount"],
        "expense_type": req.expense_type,
        "payment_mode": req.payment_mode,
        "reference_number": txn.get("reference_number", ""),
        "source": "bank_reconciliation",
        "bank_upload_id": req.upload_id,
        "bank_transaction_id": req.transaction_id,
        "created_by": session.get("name", session.get("mobile", "")),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.expenses.insert_one(expense)

    # Update transaction status
    await db.bank_transactions.update_one(
        {"transaction_id": req.transaction_id, "upload_id": req.upload_id},
        {"$set": {"match_status": "added", "added_expense_id": expense_id}}
    )

    # Audit log
    await db.expense_reconciliation_log.insert_one({
        "upload_id": req.upload_id,
        "bank_transaction_id": req.transaction_id,
        "matched_expense_id": expense_id,
        "suggested_category": txn.get("suggested_category"),
        "final_category": req.expense_type,
        "action": "add_expense",
        "reconciliation_status": "added",
        "action_taken_by": session.get("name", session.get("mobile", "")),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {"success": True, "expense_id": expense_id, "message": "Expense added successfully"}


@router.post("/ignore")
async def ignore_transaction(req: IgnoreRequest):
    """Mark a transaction as intentionally ignored"""
    session = await _get_session(req.token)
    if not session:
        return {"detail": "Authentication required"}

    result = await db.bank_transactions.update_one(
        {"transaction_id": req.transaction_id, "upload_id": req.upload_id},
        {"$set": {"match_status": "ignored", "ignore_reason": req.reason}}
    )

    if result.modified_count == 0:
        return {"detail": "Transaction not found"}

    # Audit log
    await db.expense_reconciliation_log.insert_one({
        "upload_id": req.upload_id,
        "bank_transaction_id": req.transaction_id,
        "action": "ignore",
        "reason": req.reason,
        "reconciliation_status": "ignored",
        "action_taken_by": session.get("name", session.get("mobile", "")),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {"success": True, "message": "Transaction ignored"}


@router.post("/summary")
async def get_reconciliation_summary(req: ReconcileRequest):
    """Get summary for a specific upload"""
    session = await _get_session(req.token)
    if not session:
        return {"detail": "Authentication required"}

    upload = await db.bank_statement_uploads.find_one(
        {"upload_id": req.upload_id}, {"_id": 0}
    )
    if not upload:
        return {"detail": "Upload not found"}

    transactions = await db.bank_transactions.find(
        {"upload_id": req.upload_id}, {"_id": 0}
    ).to_list(5000)

    matched = [t for t in transactions if t.get("match_status") == "matched"]
    unrecorded = [t for t in transactions if t.get("match_status") == "unrecorded"]
    added = [t for t in transactions if t.get("match_status") == "added"]
    ignored = [t for t in transactions if t.get("match_status") == "ignored"]

    return {
        "success": True,
        "upload": upload,
        "summary": {
            "total_transactions": len(transactions),
            "total_bank_debits": round(sum(t["debit_amount"] for t in transactions), 2),
            "matched_count": len(matched),
            "matched_amount": round(sum(t["debit_amount"] for t in matched), 2),
            "unrecorded_count": len(unrecorded),
            "unrecorded_amount": round(sum(t["debit_amount"] for t in unrecorded), 2),
            "added_count": len(added),
            "added_amount": round(sum(t["debit_amount"] for t in added), 2),
            "ignored_count": len(ignored),
            "ignored_amount": round(sum(t["debit_amount"] for t in ignored), 2),
        },
        "matched": matched,
        "unrecorded": unrecorded,
        "added": added,
        "ignored": ignored,
    }


@router.post("/export")
async def export_reconciliation(req: ExportRequest):
    """Export reconciliation report as JSON (frontend renders to Excel)"""
    session = await _get_session(req.token)
    if not session:
        return {"detail": "Authentication required"}

    transactions = await db.bank_transactions.find(
        {"upload_id": req.upload_id}, {"_id": 0}
    ).to_list(5000)

    upload = await db.bank_statement_uploads.find_one(
        {"upload_id": req.upload_id}, {"_id": 0}
    )

    rows = []
    for txn in transactions:
        rows.append({
            "Date": txn.get("transaction_date", ""),
            "Narration": txn.get("narration", ""),
            "Debit Amount": txn.get("debit_amount", 0),
            "Suggested Category": txn.get("suggested_category", ""),
            "Status": txn.get("match_status", "").upper(),
            "Match Method": txn.get("match_method", "") or "",
            "Reference": txn.get("reference_number", ""),
        })

    return {
        "success": True,
        "upload": upload,
        "rows": rows,
    }


@router.get("/uploads")
async def list_uploads(center: str = "", token: str = ""):
    """List recent bank statement uploads"""
    session = await _get_session(token)
    if not session:
        return {"detail": "Authentication required"}

    query = {}
    if center:
        query["center"] = center

    uploads = await db.bank_statement_uploads.find(
        query, {"_id": 0}
    ).sort("uploaded_at", -1).to_list(50)

    return {"success": True, "uploads": uploads}
